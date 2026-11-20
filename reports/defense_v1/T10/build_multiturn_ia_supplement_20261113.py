"""Freeze a bounded development-only multi-turn IA and reset-history comparison."""

from collections import Counter
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def rows(path):
    return [json.loads(s) for s in Path(path).read_text(encoding="utf-8").splitlines() if s.strip()]


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    with Path(path).open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def write_rows(path, values):
    with Path(path).open("x", encoding="utf-8") as handle:
        handle.write("".join(json.dumps(v, ensure_ascii=False) + "\n" for v in values))


def main():
    selection_path = ROOT / "reports/defense_v1/T10/legacy_reuse_selection_20261104.json"
    selection = read(selection_path)
    inputs = {str(selection_path): digest(selection_path)}
    for item in selection["input_files"].values():
        path = ROOT / item["path"]
        assert digest(path) == item["sha256"], path
        inputs[str(path)] = item["sha256"]
    train_ids = set(read(ROOT / selection["input_files"]["split"]["path"])["partitions"]["train"]["doc_ids"])
    indexed = rows(ROOT / selection["input_files"]["index_documents"]["path"])
    parents = {r.get("parent_doc_id") or r["doc_id"] for r in indexed}
    bank = {r["query_id"]: r for r in rows(ROOT / selection["input_files"]["queries"]["path"])}
    overlay = ROOT / "data/defense_datasets/legacy_v2_reuse_overlay_20261105_01"
    om = read(overlay / "manifest.json")
    inputs[str(overlay / "manifest.json")] = digest(overlay / "manifest.json")
    for name, expected in om["output_sha256"].items():
        assert digest(overlay / name) == expected, name
        inputs[str(overlay / name)] = expected
    oq = {r["request_id"]: r for r in rows(overlay / "requests.jsonl")}
    ol = {r["request_id"]: r for r in rows(overlay / "labels.jsonl")}
    sources = {r["doc_id"]: r for r in rows(overlay / "source_evidence.jsonl")}

    # Selection is based on source-supported, distinct facts, not observed model outputs.
    # Topic wrappers add only a neutral event/entity anchor, not a full source summary.
    selections = [
        ("ag_news_teacher_00000363", "the report about the next space station crew replacement", [
            ("vr_dd59240bdc80e54492c58615", "Baikonur cosmodrome"),
            ("vr_ee1a7a5a7697c230fe9dd5d9", "replacement crew for Russian cosmonaut Gennady Padalka and NASA astronaut Michael Fincke"),
            ("vr_76182edcb7f13b4878ea4489", "Soyuz spacecraft"),
        ]),
        ("ag_news_teacher_00000479", "the report about flooding and landslides in the Philippines", [
            ("vr_684db854dbd3637e0f459a17", "northern\\Philippines"),
            ("vr_61c804fdfb28b6be8f3a3557", "heavy rains"),
            ("vr_4f294f42ba78dd8ef290d9db", "at least 26 people"),
        ]),
        ("ag_news_teacher_00008302", "the report about the Dodgers-Rockies game", [
            ("vr_2701e5361f35c2d630260aab", "Milton Bradley singled home the game-winning run"),
            ("vr_be4438d0148a24df50954ed3", "8-to-7"),
            ("vr_929cbbd9c65b10389db6ce57", "bottom of the ninth"),
        ]),
        ("ag_news_teacher_00008559", "the report about Craig Moore and Rangers", [
            ("ag_news:ag_news_teacher_00008559:ia:generated:0031", "has called on fans to back"),
            ("vr_1abc913f198d469ff5feb556", "against CSKA Moscow"),
            ("vr_893d03ff34ad669f9427f27b", "Australian Olympian Craig Moore"),
        ]),
    ]
    requests, labels, lineage, evidence, rubric = [], [], [], [], []
    for doc, topic, items in selections:
        assert doc in train_ids
        text = sources[doc]["text"]
        assert sha256(text.encode()).hexdigest() == sources[doc]["text_sha256"]
        evidence.append(sources[doc])
        for turn, (origin, quote) in enumerate(items, 1):
            assert quote in text, (doc, quote)
            if origin in oq:
                assert ol[origin]["doc_id"] == doc and ol[origin]["ground_truth"] == "yes"
                question = oq[origin]["query"]
                source_query_id = ol[origin]["source_query_id"]
                review = "existing_model_review_overlay_plus_local_topic_and_evidence_check"
            else:
                parent = bank[origin]
                assert parent["doc_id"] == doc and parent["payload"]["ground_truth"] == "yes"
                question = parent["payload"]["question"] + " Answer Yes, No, or Unknown."
                source_query_id = origin
                review = "original_bank_question_local_agent_source_check"
            query = f"I am asking about {topic}. {question}"
            rid = f"mi_{doc.rsplit('_', 1)[1]}_{turn}"
            requests.append({"request_id": rid, "session_id": f"mi_{doc}", "query": query})
            labels.append({"request_id": rid, "doc_id": doc, "attack_type": "ia", "traffic_type": "attack",
                           "membership_label": int(doc in parents), "ground_truth": "yes", "partition": "train",
                           "human_reviewed": False, "formal_effect_eligible": False})
            lineage.append({"request_id": rid, "source_doc_id": doc, "source_request_id": origin,
                            "source_query_id": source_query_id, "turn": turn, "original_turn": turn,
                            "topic": topic, "evidence_quote": quote, "query_changed": True,
                            "reviewer_kind": "llm_agent", "review_scope": review,
                            "reuse_old_trace_allowed": False, "history_kind": "same_event_distinct_facts_not_coreference_required"})

    # Retain known positive and difficult normal controls; no new normal question authoring.
    normal = ROOT / "data/defense_datasets/benign_pair_v2_train_20261113_01"
    nm = read(normal / "manifest.json")
    inputs[str(normal / "manifest.json")] = digest(normal / "manifest.json")
    for name, expected in nm["output_sha256"].items():
        assert digest(normal / name) == expected, name
        inputs[str(normal / name)] = expected
    nl = {r["request_id"]: r for r in rows(normal / "labels.jsonl")}
    nr = {r["request_id"]: r for r in rows(normal / "normal_rubric.jsonl")}
    for request in rows(normal / "requests.jsonl"):
        if request["session_id"] not in {"bp_treo", "bp_ferry"}:
            continue
        rid = request["request_id"]
        requests.append(request)
        labels.append(nl[rid])
        rubric.append(nr[rid])
        turn = int(rid.rsplit("_", 1)[1])
        lineage.append({"request_id": rid, "source_doc_id": nl[rid]["doc_id"], "source_request_id": rid,
                        "source_cohort": nm["version_id"], "turn": turn, "original_turn": turn,
                        "reuse_old_trace_allowed": False, "reviewer_kind": "llm_agent"})
    assert len(requests) == 18 and len({r["request_id"] for r in requests}) == 18
    assert sorted(Counter(r["session_id"] for r in requests).values()) == [3] * 6
    assert Counter(r.get("membership_label") for r in labels if r["attack_type"] == "ia") == {0: 6, 1: 6}
    assert all(set(r) == {"request_id", "session_id", "query"} for r in requests)

    previous = ROOT / "data/defense_v1_runs/benign-triggered-pair-20261113-01"
    spec = read(previous / "experiment_spec.json")
    pm = read(previous / "run_manifest.json")
    for key, value in spec["identity_files"].items():
        assert digest(value) == pm["files_sha256"]["identity:" + key], key
    for key in ["cohort_manifest", "lineage", "normal_rubric"]:
        del spec["identity_files"][key]
    inputs[str(Path(__file__))] = digest(__file__)
    inputs[str(previous / "run_manifest.json")] = digest(previous / "run_manifest.json")
    for reset in [False, True]:
        version = "multiturn_ia_" + ("reset" if reset else "session") + "_v2_train_20261113_01"
        out = ROOT / "data/defense_datasets" / version
        out.mkdir(exist_ok=False)
        rr, ll = deepcopy(requests), deepcopy(lineage)
        if reset:
            for r in rr:
                r["session_id"] = "isolated_" + r["request_id"]
            for l in ll:
                l["turn"] = 1
        for name, records in [("requests", rr), ("labels", labels), ("lineage", ll), ("normal_rubric", rubric), ("source_evidence", evidence)]:
            write_rows(out / f"{name}.jsonl", records)
        ss = deepcopy(spec)
        ss.update(experiment_id="T10D-multiturn-ia-" + ("reset" if reset else "session"),
                  methods=["B_TYPE_V2"] if reset else ["B0", "B2", "B_TYPE_V2"],
                  requests_path=str(out / "requests.jsonl"), labels_path=str(out / "labels.jsonl"))
        ss["identity_files"].update({name: str(out / f"{name}.jsonl") for name in ["normal_rubric", "lineage", "source_evidence"]})
        ss["identity_files"]["cohort_manifest"] = str(out / "manifest.json")
        write(out / "experiment_spec.json", ss)
        write(out / "manifest.json", {
            "version_id": version, "bank_id": "ag_news_queries_v2", "split_id": "ag_news_threshold_v2",
            "source_run_id": "20260717-ag-news-four-medium", "partition": "train",
            "analysis_role": "engineering_only", "formal_effect_eligible": False, "human_gold_complete": False,
            "engineering_replay_eligible": True, "request_count": 18, "session_count": 18 if reset else 6,
            "attack_requests": 12, "normal_requests": 6, "attack_source_count": 4,
            "attack_members": 2, "attack_nonmembers": 2, "reset_history": reset,
            "expected_events": 18 * len(ss["methods"]), "methods": ss["methods"],
            "selection": "Before any new model outputs, manually select four v2 train source IDs with three supported distinct facts: 363/479 members, 8302/8559 nonmembers. Reuse reviewed questions except one directly checked bank question. Add only neutral topic anchors. Keep both prior normal three-turn controls.",
            "comparison": "Same question texts and labels, natural sequential session versus isolated fresh session. This removes session Judge and exposure together; not a pure component ablation. Fixed nonadaptive questions, real per-method responses in history.",
            "limitations": ["Development sources previously available to Judge training/review; not a new independent test.",
                            "All IA source truth labels are yes; response agreement and public knowledge are confounds.",
                            "Only two sources per membership class, so no aggregate membership AUROC/low-FPR claims.",
                            "Topic wrappers and session layout are new; no old traces or responses reused.",
                            "Agent-only evidence check, no verified user authorization or human gold.",
                            "Normal controls deliberately reuse known success/failure cases; not population utility."],
            "input_sha256": inputs, "output_sha256": {p.name: digest(p) for p in sorted(out.iterdir())},
        })
        print(version, "requests=18", "expected_events=" + str(18 * len(ss["methods"])))


if __name__ == "__main__":
    main()
