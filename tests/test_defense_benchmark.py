from __future__ import annotations

import json
from dataclasses import replace
from dataclasses import fields
from pathlib import Path
from types import SimpleNamespace

import pytest

from miaguard.defense_benchmark import run_benchmark
from miaguard.defense_contracts import OnlineRequest
from miaguard.frozen_risk_scorer import FrozenRiskScorer
from miaguard.risk_types import RiskResult
from miaguard.two_stage_gateway import load_two_stage_config


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def inputs(tmp_path: Path, methods=("B0", "B2"), skip=()) -> Path:
    requests = tmp_path / "requests.jsonl"
    labels = tmp_path / "labels.jsonl"
    write_jsonl(requests, [
        {"request_id": "q1", "session_id": "s1", "query": "question 1"},
        {"request_id": "q2", "session_id": "s1", "query": "question 2"},
        {"request_id": "q3", "session_id": "s2", "query": "question 3"},
    ])
    write_jsonl(labels, [
        {"request_id": "q1", "attack_type": "direct_rag_mia", "membership_label": 1, "doc_id": "d1"},
        {"request_id": "q2", "attack_type": "ia", "membership_label": 1, "doc_id": "d1", "ground_truth": "yes"},
        {"request_id": "q3", "attack_type": "benign", "reference_answer": "Yes", "doc_id": "d2"},
    ])
    spec = tmp_path / "spec.json"
    spec.write_text(json.dumps({"schema_version": 1, "experiment_id": "T09-fake", "backend": "fake",
                                "dataset_id": "synthetic", "partition": "engineering_smoke", "seed": 7,
                                "methods": list(methods), "requests_path": str(requests),
                                "labels_path": str(labels), "skip_request_ids": list(skip)}), encoding="utf-8")
    return spec


class Backend:
    def __init__(self, calls, method, session):
        self.calls = calls
        self.method = method
        self.session = session
        self.turn = 0

    def run(self, request: OnlineRequest) -> dict:
        assert {field.name for field in fields(OnlineRequest)}.isdisjoint(
            {"membership_label", "attack_type", "target_doc_id", "intent_label"})
        self.turn += 1
        self.calls.append((self.method, self.session, request.request_id, self.turn))
        return {"response": "Yes", "status": "complete", "retrieved_doc_ids": ["d1"],
                "delivered_doc_ids": ["d1"], "generation_input": {"query": request.query, "contexts": ["context"]}}


def test_resume_skips_complete_shards_and_methods_have_fresh_state(tmp_path: Path) -> None:
    spec = inputs(tmp_path)
    calls = []
    factory = lambda method, seed, session: Backend(calls, method, session)
    root = tmp_path / "run"
    result = run_benchmark(spec, root, backend_factory=factory)
    assert (result["expected"], result["completed"], result["failed"], result["skipped"]) == (6, 6, 0, 0)
    assert result["status"] == "completed" and result["outcome"] == "valid"
    assert len(calls) == 6
    assert sorted(turn for _, _, _, turn in calls if turn == 1) == [1, 1, 1, 1]
    resumed = run_benchmark(spec, root, resume=True, backend_factory=factory)
    assert resumed == result
    assert len(calls) == 6
    events = [json.loads(line) for line in (root / "events.jsonl").read_text(encoding="utf-8").splitlines()]
    assert all("membership_label" not in row for row in events)
    assert (root / "attack_scores.jsonl").exists()
    assert (root / "benign_quality.jsonl").exists()


def test_resume_rejects_changed_identity(tmp_path: Path) -> None:
    spec = inputs(tmp_path)
    root = tmp_path / "run"
    run_benchmark(spec, root, backend_factory=lambda m, s, session: Backend([], m, session))
    raw = json.loads(spec.read_text(encoding="utf-8"))
    raw["seed"] = 8
    spec.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(ValueError, match="identity"):
        run_benchmark(spec, root, resume=True, backend_factory=lambda m, s, session: Backend([], m, session))


def test_interrupted_shard_reruns_from_start(tmp_path: Path) -> None:
    spec = inputs(tmp_path, methods=("B0",))
    root = tmp_path / "run"
    calls = []

    class Interrupted(Backend):
        def run(self, request):
            if request.request_id == "q2":
                raise KeyboardInterrupt()
            return super().run(request)

    with pytest.raises(KeyboardInterrupt):
        run_benchmark(spec, root, backend_factory=lambda m, s, session: Interrupted(calls, m, session))
    manifest = json.loads((root / "run_manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "interrupted"
    result = run_benchmark(spec, root, resume=True,
                           backend_factory=lambda m, s, session: Backend(calls, m, session))
    assert result["completed"] == 3
    assert [item[2] for item in calls].count("q1") == 2


def test_failed_and_skipped_requests_remain_in_denominator(tmp_path: Path) -> None:
    spec = inputs(tmp_path, methods=("B0",), skip=("q3",))

    class Fails(Backend):
        def run(self, request):
            if request.request_id == "q2":
                raise RuntimeError("fake model failed")
            return super().run(request)

    result = run_benchmark(spec, tmp_path / "run", backend_factory=lambda m, s, session: Fails([], m, session))
    assert result["expected"] == result["completed"] + result["failed"] + result["skipped"]
    assert (result["completed"], result["failed"], result["skipped"]) == (1, 1, 1)
    assert result["status"] != "completed" and result["outcome"] == "invalid"
    failures = [json.loads(line) for line in (tmp_path / "run/failures.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(failures) == 1 and failures[0]["request_id"] == "q2"
    attack_scores = [json.loads(line) for line in (tmp_path / "run/attack_scores.jsonl").read_text(encoding="utf-8").splitlines()]
    ia = [row for row in attack_scores if row["attack_type"] == "ia"][0]
    assert ia["score"] is None and ia["reason"] == "missing_query_score"
    benign = json.loads((tmp_path / "run/benign_quality.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert benign["status"] == "skipped" and benign["exact_match"] is False


def test_generation_input_is_a_controlled_artifact(tmp_path: Path) -> None:
    spec = inputs(tmp_path, methods=("B0",))
    root = tmp_path / "run"
    run_benchmark(spec, root, backend_factory=lambda m, s, session: Backend([], m, session))
    event = json.loads((root / "events.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert "generation_input" not in event
    artifact = root / event["generation_input_ref"]
    assert artifact.is_file()
    assert json.loads(artifact.read_text(encoding="utf-8"))["generation_input"]["query"] == "question 1"


def test_completed_run_rejects_missing_artifact_on_resume(tmp_path: Path) -> None:
    spec = inputs(tmp_path, methods=("B0",))
    root = tmp_path / "run"
    run_benchmark(spec, root, backend_factory=lambda m, s, session: Backend([], m, session))
    event = json.loads((root / "events.jsonl").read_text(encoding="utf-8").splitlines()[0])
    (root / event["generation_input_ref"]).unlink()
    with pytest.raises(ValueError, match="artifact"):
        run_benchmark(spec, root, resume=True, backend_factory=lambda m, s, session: Backend([], m, session))


def test_live_backend_requires_complete_identity_before_start(tmp_path: Path) -> None:
    spec = inputs(tmp_path)
    raw = json.loads(spec.read_text(encoding="utf-8"))
    raw["backend"] = "live"
    spec.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(ValueError, match="identity_files"):
        run_benchmark(spec, tmp_path / "run")
    assert not (tmp_path / "run").exists()


def test_backend_reported_failure_keeps_attempt_metadata(tmp_path: Path) -> None:
    spec = inputs(tmp_path, methods=("B0",))

    class FailedResult(Backend):
        def run(self, request):
            if request.request_id == "q2":
                return {"status": "failed", "reason": "generation_error", "response": None,
                        "retrieved_doc_ids": ["target"], "delivered_doc_ids": ["target"],
                        "ledger_event": {"delivery_attempted": True}}
            return super().run(request)

    root = tmp_path / "run"
    result = run_benchmark(spec, root, backend_factory=lambda m, s, session: FailedResult([], m, session))
    assert result["failed"] == 1
    failed = [json.loads(line) for line in (root / "events.jsonl").read_text(encoding="utf-8").splitlines() if '"failed"' in line][0]
    assert failed["ledger_event"]["delivery_attempted"] is True


def test_live_backend_methods_share_request_contract_without_gpu() -> None:
    from miaguard.defense_benchmark_live import LiveBackend

    class Store:
        def search(self, query, top_k, *, allowed_doc_ids=None, excluded_parent_ids=frozenset()):
            docs = [{"doc_id": "target", "text": "target story has three supporting facts"}, {"doc_id": "safe", "text": "safe background"}]
            return [{"score": 1 - i / 10, "document": doc} for i, doc in enumerate(docs)
                    if doc["doc_id"] not in excluded_parent_ids][:top_k]

    class Judge:
        def evaluate_query(self, **kwargs):
            return RiskResult("query", .9, "STRONG", "fake")

        def evaluate_session(self, **kwargs):
            return RiskResult("session", .9, "STRONG", "fake")

    class Client:
        def generate(self, model, prompt, **kwargs):
            return "Yes" if "target story" in prompt else "Unknown"

    root = Path(__file__).resolve().parents[1]
    base = load_two_stage_config(root / "configs/defense/two_stage_disabled.yaml")
    bound = SimpleNamespace(gateway=replace(base, mode="observe", window_size=5, min_session_queries=3),
                            scorer=FrozenRiskScorer("logprob", "fake", (2, 2), -1, {"0.01": .5, "0.05": .5}),
                            query_only_threshold=.5, fused_threshold=.5)
    outputs = {}
    for method in ("B0", "B2", "B3", "B5", "B5_LOCATED"):
        backend = LiveBackend(method, "s", Store(), Judge(), bound, Client(),
                              SimpleNamespace(generation_model="fake"), 2, 20)
        outputs[method] = backend.run(OnlineRequest("r", "s", "target story has three supporting facts"))
    assert [outputs[method]["action"] for method in ("B0", "B2", "B3", "B5")] == ["allow", "deny", "no_context_answer", "hide_target_refill"]
    assert outputs["B5"]["retrieved_doc_ids"] == ("target", "safe")
    assert outputs["B5"]["delivered_doc_ids"] == ("safe",)
    assert outputs["B5_LOCATED"]["action"] == "hide_target_refill"
    assert outputs["B5_LOCATED"]["delivered_doc_ids"] == ("safe",)
    assert outputs["B5_LOCATED"]["risk"]["localization"]["status"] == "located"
    fallback = LiveBackend("B5_LOCATED", "s2", Store(), Judge(), bound, Client(),
                           SimpleNamespace(generation_model="fake"), 2, 20)
    result = fallback.run(OnlineRequest("r2", "s2", "question"))
    assert result["action"] == "deny"
    assert result["risk"]["localization"]["status"] == "unresolved"
    quiet_bound = SimpleNamespace(gateway=bound.gateway, scorer=bound.scorer,
                                  query_only_threshold=.999999, fused_threshold=.999999)
    guarded = LiveBackend("B5_CUE", "s3", Store(), Judge(), quiet_bound, Client(),
                          SimpleNamespace(generation_model="fake"), 2, 20)
    query = 'Does this: "the report describes a company whose recent changes affect customers around the world today" appear in the context?'
    flagged = guarded.run(OnlineRequest("r3", "s3", query))
    assert flagged["risk"]["frozen_risk"]["triggered"] is False
    assert flagged["risk"]["query_cue"]["cues"] == ["quoted_context_check"]
    assert flagged["action"] == "deny"
    clean = LiveBackend("B5_CUE", "s4", Store(), Judge(), quiet_bound, Client(),
                        SimpleNamespace(generation_model="fake"), 2, 20)
    assert clean.run(OnlineRequest("r4", "s4", "What happened?"))["action"] == "allow"
    assert outputs["B2"]["ledger_event"]["delivery_attempted"] is False
    assert all(output["status"] == "complete" for output in outputs.values())


@pytest.mark.parametrize(
    "types,session_types,high,refill_fails,expected,reason,method,query",
    [
        (("direct_rag_mia",), (), True, False, "deny", "direct", "B_TYPE_V1", ""),
        (("s2_mia",), (), True, False, "hide_target_refill", "located", "B_TYPE_V1", ""),
        (("masked_mia",), (), True, True, "deny", "located", "B_TYPE_V1", ""),
        (("ia",), (), True, False, "no_context_answer", "ia_query_only", "B_TYPE_V1", ""),
        ((), ("ia",), True, False, "deny", "ia_session", "B_TYPE_V1", ""),
        (("s2_mia",), ("masked_mia",), True, False, "deny", "multiple_types", "B_TYPE_V1", ""),
        ((), (), True, False, "deny", "unknown_type", "B_TYPE_V1", ""),
        (("ia",), (), False, False, "allow", "low_risk", "B_TYPE_V1", ""),
        (("ia",), (), True, False, "deny", "ia_prior_raw_delivery", "B_TYPE_V1", ""),
        (("error",), (), True, False, "unavailable", "judge_failure", "B_TYPE_V1", ""),
        ((), ("error",), True, False, "unavailable", "judge_failure", "B_TYPE_V1", ""),
        (("masked_mia",), (), True, False, "deny", "masked_recovery", "B_TYPE_V2",
         "Recover original words [Mask_1] [Mask_2] [Mask_3]."),
        (("masked_mia",), (), True, False, "hide_target_refill", "located", "B_TYPE_V2", ""),
        (("masked_mia",), (), False, False, "allow", "low_risk", "B_TYPE_V2",
         "Recover original words [Mask_1] [Mask_2] [Mask_3]."),
        (("s2_mia",), (), True, False, "sanitized_context", "s2_summary", "B_MULTI_SUMMARY", ""),
        (("s2_mia",), (), True, False, "no_context_answer", "s2_no_context", "B_MULTI_NO_CONTEXT", ""),
        (("direct_rag_mia",), (), True, False, "deny", "direct", "B_MULTI_SUMMARY", ""),
        (("ia",), (), True, False, "deny", "ia_prior_raw_delivery", "B_MULTI_SUMMARY", ""),
        (("s2_mia",), ("masked_mia",), True, False, "deny", "multiple_types", "B_MULTI_SUMMARY", ""),
        (("error",), (), True, False, "unavailable", "judge_failure", "B_MULTI_SUMMARY", ""),
        (("masked_mia",), (), True, False, "deny", "masked_recovery", "B_MULTI_SUMMARY",
         "Recover original words [Mask_1] [Mask_2] [Mask_3]."),
        (("masked_mia",), (), True, True, "deny", "located", "B_MULTI_SUMMARY", ""),
        (("s2_mia",), (), False, False, "allow", "low_risk", "B_MULTI_SUMMARY", ""),
          ((), (), False, False, "deny", "cue_direct", "B_NEXT_GOAL",
           'Does "one two three four five six seven eight nine ten eleven twelve" appear in the context?'),
          ((), (), False, False, "deny", "cue_masked", "B_NEXT_GOAL",
           "Recover original words [Mask_1] [Mask_2] [Mask_3]."),
          ((), (), False, False, "no_context_answer", "cue_ia_first", "B_NEXT_GOAL",
           "Does the report say this happened? Answer Yes, No, or Unknown."),
          ((), (), False, False, "deny", "cue_ia_prior_raw", "B_NEXT_GOAL",
           "Does the report say this happened? Answer Yes, No, or Unknown."),
          (("error",), (), True, False, "unavailable", "judge_failure", "B_NEXT_GOAL", ""),
          ((), (), False, False, "allow", "low_risk", "B_NEXT_GOAL", "What does the report say?"),
          ((), (), False, False, "deny", "cue_direct", "B_NEXT_CUE_ONLY",
           'Does "one two three four five six seven eight nine ten eleven twelve" appear in the context?'),
          ((), (), False, False, "deny", "cue_masked", "B_NEXT_CUE_ONLY",
           "Recover original words [Mask_1] [Mask_2] [Mask_3]."),
          ((), (), False, False, "allow", "low_risk", "B_NEXT_CUE_ONLY",
           "Does the report say this happened? Answer Yes, No, or Unknown."),
          ((), (), False, False, "allow", "low_risk", "B_NEXT_IA_ONLY",
           "Recover original words [Mask_1] [Mask_2] [Mask_3]."),
          ((), (), False, False, "no_context_answer", "cue_ia_first", "B_NEXT_IA_ONLY",
           "Does the report say this happened? Answer Yes, No, or Unknown."),
          ((), (), False, False, "deny", "cue_ia_prior_raw", "B_NEXT_IA_ONLY",
           "Does the report say this happened? Answer Yes, No, or Unknown."),
          (("direct_rag_mia",), (), True, False, "deny", "direct", "B_NEXT_CUE_ONLY", ""),
          (("direct_rag_mia",), (), True, False, "deny", "direct", "B_NEXT_IA_ONLY", ""),
          (("error",), (), True, False, "unavailable", "judge_failure", "B_NEXT_CUE_ONLY", ""),
          (("error",), (), True, False, "unavailable", "judge_failure", "B_NEXT_IA_ONLY", ""),
    ],
)
def test_type_policy_uses_online_types_and_actual_session_delivery(
    types, session_types, high, refill_fails, expected, reason, method, query,
):
    from miaguard.defense_benchmark_live import LiveBackend

    class Store:
        def search(self, query, top_k, *, allowed_doc_ids=None, excluded_parent_ids=frozenset()):
            if refill_fails and excluded_parent_ids:
                raise RuntimeError("refill failed")
            docs = [
                {"doc_id": "safe", "text": "safe background"},
                {"doc_id": "target", "text": "target story has three supporting facts"},
                {"doc_id": "outside_scope", "text": "access not authorized"},
            ]
            return [
                {"score": 1 - i / 10, "document": doc} for i, doc in enumerate(docs)
                if doc["doc_id"] not in excluded_parent_ids and doc["doc_id"] in allowed_doc_ids
            ][:top_k]

    class Judge:
        def evaluate_query(self, *, query, **kwargs):
            if query.startswith("Previous"):
                return RiskResult("query", .1, "NONE", "fake")
            if types == ("error",):
                raise RuntimeError("query judge failed")
            return RiskResult("query", .9 if high else .1, "STRONG", "fake", types, ("QUERY",))

        def evaluate_session(self, **kwargs):
            if session_types == ("error",):
                raise RuntimeError("session judge failed")
            return RiskResult("session", .9, "STRONG", "fake", session_types, ("SESSION",))

    class Client:
        def generate(self, model, prompt, **kwargs):
            assert "access not authorized" not in prompt
            return "answer"

    root = Path(__file__).resolve().parents[1]
    base = load_two_stage_config(root / "configs/defense/two_stage_disabled.yaml")
    bound = SimpleNamespace(gateway=replace(base, mode="observe", window_size=5, min_session_queries=3),
                            scorer=FrozenRiskScorer("logprob", "fake", (2, 2), -1, {"0.01": .5, "0.05": .5}),
                            query_only_threshold=.5, fused_threshold=.5)
    backend = LiveBackend(method, "s", Store(), Judge(), bound, Client(),
                          SimpleNamespace(generation_model="fake"), 3, 20)
    allowed = frozenset({"safe", "target"})
    previous = 2 if session_types else int(reason in {"ia_prior_raw_delivery", "cue_ia_prior_raw"})
    for i in range(previous):
        assert backend.run(OnlineRequest(f"p{i}", "s", f"Previous turn {i}", allowed))["action"] == "allow"
    output = backend.run(OnlineRequest("r", "s", f"target story has three supporting facts {query}".strip(), allowed))
    assert output["action"] == expected
    assert output["risk"]["type_policy"]["reason"] == reason
    if types != ("error",):
        assert output["risk"]["query_detection"]["suspected_attack_types"] == list(types)
    if session_types and session_types != ("error",):
        assert output["risk"]["session_detection"]["suspected_attack_types"] == list(session_types)
    if expected in {"deny", "unavailable"}:
        assert output["ledger_event"]["delivery_attempted"] is False
        assert output["generation_input"]["prompt"] is None
    if expected == "hide_target_refill":
        assert output["delivered_doc_ids"] == ("safe",)
    if expected == "sanitized_context":
        assert {row["doc_id"] for row in output["ledger_event"]["transform_input_evidence"]} == {"safe", "target"}
        assert output["ledger_event"]["delivered_exposure"] == "transformed"
        assert "access not authorized" not in output["generation_input"]["prompt"]
    if refill_fails:
        assert output["risk"]["execution"]["reason_codes"] == ["REFILL_FAILED"]
