"""Screen benign utility cases and freeze a local paired experiment before answering."""

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path

from miaguard.defense_benchmark_live import make_live_backend_factory


ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
PRIOR = ROOT / "data/defense_v1_runs/type-policy-v2-paired-20261113-01"
SCREEN = HERE / "benign_pair_screen_20261113_01"
OUT = ROOT / "data/defense_datasets/benign_pair_v2_train_20261113_01"
DESIGN = HERE / "benign_pair_candidates_20261113.json"


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def rows(path):
    with Path(path).open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_rows(path, entries):
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in entries), encoding="utf-8")


def main():
    previous = read(PRIOR / "run_manifest.json")
    spec = read(PRIOR / "experiment_spec.json")
    design = read(DESIGN)
    assert previous["status"] == "completed"
    assert digest(PRIOR / "metrics.json") == previous["metrics_sha256"]
    for key, path in spec["identity_files"].items():
        assert digest(path) == previous["files_sha256"]["identity:" + key], key
    for key, value in previous["files_sha256"].items():
        if key.startswith("code:"):
            code_paths = [ROOT / folder / key[5:] for folder in ("src/miaguard", "scripts")]
            assert digest(next(p for p in code_paths if p.is_file())) == value, key
    selection = read(spec["identity_files"]["selection_manifest"])
    assert (selection["bank_id"], selection["split_id"], selection["partition"]) == (
        "ag_news_queries_v2", "ag_news_threshold_v2", "train",
    )
    for record in selection["input_files"].values():
        assert digest(ROOT / record["path"]) == record["sha256"]
    assert digest(spec["labels_path"]) == previous["files_sha256"]["labels"]
    prior_ids = {row["doc_id"] for row in rows(Path(spec["labels_path"]))}
    train = set(read(spec["identity_files"]["split"])["partitions"]["train"]["doc_ids"])
    index = {row["doc_id"]: row["text"] for row in rows(spec["identity_files"]["index_documents"])}
    bank = {
        (row["doc_id"], row["query_index"]): row for row in rows(spec["identity_files"]["query_bank_queries"])
        if row["doc_id"] in train and row["attack_type"] == "benign" and row["validation"]["status"] == "accepted"
    }
    candidates = []
    for session in design["sessions"]:
        doc = "ag_news_teacher_000" + session["source"]
        assert doc in train and doc in index and doc not in prior_ids, doc
        for turn, item in enumerate(session["items"], start=1):
            assert item["quote"] in index[doc], (doc, item["quote"])
            rid = f"bp_{session['id']}_{turn}"
            source_row = bank[doc, item["bank_index"]] if "bank_index" in item else None
            candidates.append({
                "request_id": rid, "session_id": "bp_" + session["id"], "turn": turn,
                "doc_id": doc, "category": item.get("category", "fact_or_close_reading"),
                "query": source_row["query_text"] if source_row else item["query"],
                "source_query_id": source_row["query_id"] if source_row else None,
                "reference_answer": item["answer"], "evidence_quote": item["quote"],
            })

    SCREEN.mkdir(exist_ok=False)
    write_rows(SCREEN / "candidate_inputs.jsonl", candidates)
    screen_manifest = {
        "status": "running", "completed": 0, "expected": len(candidates),
        "scope": "Frozen Judge and original top-4 retrieval. Answer generation is never called.",
        "selection": design["selection"], "grading": design["grading"],
        "limitations": design["limitations"],
        "input_sha256": {str(p.relative_to(ROOT)): digest(p) for p in (DESIGN, Path(__file__), PRIOR / "run_manifest.json")},
        "candidate_sha256": digest(SCREEN / "candidate_inputs.jsonl"),
    }
    write(SCREEN / "manifest.json", screen_manifest)
    screened = []
    try:
        factory, _ = make_live_backend_factory(spec)
        backends = {}
        with (SCREEN / "screen.jsonl").open("x", encoding="utf-8") as handle:
            for row in candidates:
                session_id = row["session_id"]
                if session_id not in backends:
                    backends[session_id] = factory("B2", spec["seed"], session_id)
                guard = backends[session_id].guard
                prepared = guard.prepare(row["query"], session_id)
                guard.detector.commit_session(session_id)
                assessment = prepared.decision.two_stage_assessment
                result = row | {
                    "risk": assessment["frozen_risk"],
                    "query_detection": assessment["query_detection"],
                    "session_detection": assessment["session_detection"],
                    "retrieved_doc_ids": prepared.retrieved_doc_ids,
                    "reference_retrieved": row["doc_id"] in prepared.retrieved_doc_ids,
                    "screen_action": prepared.decision.access_action,
                }
                screened.append(result)
                handle.write(json.dumps(result, ensure_ascii=False) + "\n")
                handle.flush()
                print(row["request_id"], result["screen_action"], result["reference_retrieved"],
                      result["risk"]["risk_source"], flush=True)
        screen_manifest.update(status="completed", screen_sha256=digest(SCREEN / "screen.jsonl"))
    except BaseException as exc:
        screen_manifest.update(status="interrupted" if isinstance(exc, KeyboardInterrupt) else "failed", error=repr(exc))
        raise
    finally:
        screen_manifest["completed"] = len(screened)
        write(SCREEN / "manifest.json", screen_manifest)

    sizes = Counter(row["session_id"] for row in screened)
    singles = [row for row in screened if sizes[row["session_id"]] == 1]
    singles.sort(key=lambda row: (not row["reference_retrieved"], row["screen_action"] != "deny"))
    selection_ids = {row["request_id"] for row in singles[:8]}
    selected = [row for row in screened if row["request_id"] in selection_ids or sizes[row["session_id"]] > 1]
    assert len(selected) == 14 and len({row["doc_id"] for row in selected}) == 10
    OUT.mkdir(exist_ok=False)
    write_rows(OUT / "requests.jsonl", [
        {key: row[key] for key in ("request_id", "session_id", "query")} for row in selected
    ])
    write_rows(OUT / "labels.jsonl", [{
        "request_id": row["request_id"], "doc_id": row["doc_id"], "traffic_type": "benign",
        "attack_type": "benign", "answerable": True, "reference_answer": row["reference_answer"],
        "gold_evidence_ids": [row["doc_id"]], "human_reviewed": False, "formal_effect_eligible": False,
    } for row in selected])
    write_rows(OUT / "normal_rubric.jsonl", [{
        key: row[key] for key in ("request_id", "reference_answer", "evidence_quote", "category")
    } | {"reviewer_kind": "llm_agent", "human_reviewed": False} for row in selected])
    write_rows(OUT / "lineage.jsonl", [{
        key: row[key] for key in ("request_id", "turn", "doc_id", "source_query_id", "reference_retrieved")
    } | {
        "selected_with_screen_trigger": row["screen_action"] == "deny",
        "selection_role": "predeclared_multiturn" if sizes[row["session_id"]] > 1 else (
            "screen_trigger_priority" if row["screen_action"] == "deny" and row["reference_retrieved"]
            else "singleton_comparison"
        ),
    } for row in selected])
    spec.update(experiment_id="T10D-benign-triggered-pair", methods=["B0", "B2", "B_TYPE_V2"],
                requests_path=str(OUT / "requests.jsonl"), labels_path=str(OUT / "labels.jsonl"))
    spec["identity_files"].update(normal_rubric=str(OUT / "normal_rubric.jsonl"), lineage=str(OUT / "lineage.jsonl"),
                                  cohort_manifest=str(OUT / "manifest.json"), screen_manifest=str(SCREEN / "manifest.json"))
    write(OUT / "experiment_spec.json", spec)
    write(OUT / "manifest.json", {
        "version_id": OUT.name, "partition": "train", "analysis_role": "engineering_only",
        "formal_effect_eligible": False, "human_gold_complete": False,
        "bank_id": selection["bank_id"], "split_id": selection["split_id"],
        "source_run_id": spec["source_run_id"], "requests": len(selected), "sessions": 10,
        "selected_screen_denies": sum(row["screen_action"] == "deny" for row in selected),
        "selection": design["selection"], "grading": design["grading"], "limitations": design["limitations"],
        "expected_events": len(selected) * len(spec["methods"]),
        "input_sha256": {
            str(p.relative_to(ROOT)): digest(p) for p in (DESIGN, Path(__file__), SCREEN / "manifest.json", SCREEN / "screen.jsonl")
        },
        "output_sha256": {path.name: digest(path) for path in OUT.iterdir()},
    })
    print(OUT.name, len(selected), "frozen", flush=True)


if __name__ == "__main__":
    main()
