from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from miaguard.defense import GuardedRAG
from miaguard.defense_contracts import Evidence, OnlineRequest
from miaguard.exposure_store import ExposureStore, run_guarded_request
from miaguard.risk_types import RiskResult
from miaguard.two_stage_gateway import TwoStageGateway, load_two_stage_config


def request(identifier: str = "r1", session: str = "s1", query: str = "question") -> OnlineRequest:
    return OnlineRequest(identifier, session, query)


def ev(identifier: str, kind: str = "raw") -> Evidence:
    return Evidence(identifier, identifier, identifier + " text", .9, kind)


def test_retry_is_idempotent_and_different_input_rejected() -> None:
    ledger = ExposureStore(timeout_seconds=1800)
    first = ledger.begin(request(), now=0)
    assert first.kind == "new"
    ledger.record_retrieved("r1", ("target", "safe"))
    ledger.record_attempt("r1", (ev("safe"),))
    ledger.complete("r1", "answer", referenced_parent_ids=("safe",), now=1)
    repeated = ledger.begin(request(), now=2)
    assert repeated.kind == "cached" and repeated.event.response == "answer"
    assert len(ledger.history("s1", now=2)) == 1
    assert ledger.history("s1", now=2)[0].referenced_parent_ids == ("safe",)
    assert ledger.history("s1", now=2)[0].to_dict()["delivered_evidence"][0]["text_sha256"]
    assert ledger.counters("s1", now=2) == {"new_requests": 1, "retries": 1}
    with pytest.raises(ValueError, match="different input"):
        ledger.begin(request(query="other"), now=3)


def test_sessions_are_isolated_and_expire() -> None:
    ledger = ExposureStore(timeout_seconds=10)
    ledger.begin(request("a", "s1"), now=0)
    with pytest.raises(RuntimeError, match="pending"):
        ledger.begin(request("b", "s1"), now=1)
    ledger.begin(request("b", "s2"), now=1)
    ledger.fail("a", "generation_error", now=2)
    assert len(ledger.history("s1", now=2)) == 1
    assert len(ledger.history("s2", now=2)) == 1
    assert ledger.history("s1", now=12) == ()
    assert ledger.history("s2", now=2) != ()
    assert ledger.reset_events[-1]["session_id"] == "s1"


def test_generation_failure_preserves_attempt_and_transformed_exposure() -> None:
    ledger = ExposureStore()
    ledger.begin(request(), now=0)
    ledger.record_retrieved("r1", ("target", "safe"))
    ledger.record_transform_attempt("r1", (ev("target"),))
    ledger.record_attempt("r1", (ev("summary", "summary"),))
    ledger.fail("r1", "generation_error", now=1)
    event = ledger.history("s1", now=1)[0]
    assert event.status == "failed"
    assert event.retrieved_doc_ids == ("target", "safe")
    assert event.delivered_doc_ids == ("summary",)
    assert event.delivered_exposure == "transformed"
    assert event.transform_input_doc_ids == ("target",)
    assert event.delivery_attempted is True
    assert event.response is None


class Store:
    def search(self, query, top_k, *, allowed_doc_ids=None, excluded_parent_ids=frozenset()):
        docs = [{"doc_id": "target", "text": "secret"}, {"doc_id": "safe", "text": "safe"}]
        return [{"score": 1.0 - i / 10, "document": doc} for i, doc in enumerate(docs)
                if doc["doc_id"] not in excluded_parent_ids][:top_k]


class Detector:
    def __init__(self, stage):
        self.stage = stage
        self.calls = []

    def evaluate(self, **kwargs):
        self.calls.append(kwargs)
        return RiskResult(self.stage, .8, "WEAK", "fake")


def gateway(query_detector, session_detector):
    config = load_two_stage_config(Path(__file__).resolve().parents[1] / "configs/defense/two_stage_disabled.yaml")
    return TwoStageGateway(replace(config, mode="observe"), query_detector=query_detector,
                           session_detector=session_detector, defer_session_commit=True)


def test_full_request_commits_once_and_judge_sees_precontrol_retrieval() -> None:
    query_detector, session_detector = Detector("query"), Detector("session")
    active = gateway(query_detector, session_detector)
    guard = GuardedRAG(Store(), active, 2,
                       action_selector=lambda decision, candidates: ("hide_target_refill", frozenset({"target"})))
    ledger = ExposureStore()
    outcome = run_guarded_request(request(), guard, ledger, lambda prepared: "safe answer")
    assert outcome.response == "safe answer"
    assert active.session_store.turn_count("s1") == 1
    assert session_detector.calls[0]["retrieved_doc_ids"] == ("target", "safe")
    event = ledger.history("s1")[0]
    assert event.retrieved_doc_ids == ("target", "safe")
    assert event.delivered_doc_ids == ("safe",)
    assert event.delivered_exposure == "raw"
    again = run_guarded_request(request(), guard, ledger, lambda prepared: "changed")
    assert again.cached is True and again.response == "safe answer"
    assert active.session_store.turn_count("s1") == 1
    assert len(query_detector.calls) == 1


def test_failed_answer_charges_budget_after_evidence_attempt() -> None:
    active = gateway(Detector("query"), Detector("session"))
    guard = GuardedRAG(Store(), active, 2,
                       action_selector=lambda decision, candidates: ("allow", frozenset()))
    ledger = ExposureStore()

    def fails(prepared):
        raise RuntimeError("generation failed")

    with pytest.raises(RuntimeError, match="generation failed"):
        run_guarded_request(request(), guard, ledger, fails)
    event = ledger.history("s1")[0]
    assert event.status == "failed" and event.delivered_doc_ids == ("target", "safe")
    assert active.session_store.turn_count("s1") == 1
    assert ledger.counters("s1")["new_requests"] == 1


def test_summary_model_input_and_deny_are_accounted_separately() -> None:
    active = gateway(Detector("query"), Detector("session"))
    guard = GuardedRAG(Store(), active, 2,
                       action_selector=lambda decision, candidates: ("sanitized_context", frozenset()),
                       summarizer=lambda items: "broad topic")
    ledger = ExposureStore()
    run_guarded_request(request(), guard, ledger, lambda prepared: "answer")
    event = ledger.history("s1")[0]
    assert event.transform_input_doc_ids == ("target", "safe")
    assert event.delivered_exposure == "transformed"
    assert event.delivered_doc_ids[0].startswith("summary:")

    deny_gateway = gateway(Detector("query"), Detector("session"))
    deny_guard = GuardedRAG(Store(), deny_gateway, 2,
                            action_selector=lambda decision, candidates: ("deny", frozenset()))
    run_guarded_request(request("r2", "s2"), deny_guard, ledger, lambda prepared: "declined")
    denied = ledger.history("s2")[0]
    assert denied.delivery_attempted is False
    assert denied.delivered_exposure == "none"
