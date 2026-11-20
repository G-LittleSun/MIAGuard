"""Produce a deterministic fake full-request evidence chain for G1."""

from __future__ import annotations

import argparse
import json
from dataclasses import replace
from pathlib import Path

from miaguard.defense import GuardedRAG
from miaguard.defense_contracts import OnlineRequest
from miaguard.exposure_store import ExposureStore, run_guarded_request
from miaguard.risk_types import RiskResult
from miaguard.two_stage_gateway import TwoStageGateway, load_two_stage_config


class Store:
    def search(self, query, top_k, *, allowed_doc_ids=None, excluded_parent_ids=frozenset()):
        documents = [{"doc_id": "target", "text": "target text"}, {"doc_id": "safe", "text": "safe text"}]
        return [{"score": 1.0 - index / 10, "document": document}
                for index, document in enumerate(documents)
                if document["doc_id"] not in excluded_parent_ids
                and (allowed_doc_ids is None or document["doc_id"] in allowed_doc_ids)][:top_k]


class Detector:
    def __init__(self, stage):
        self.stage = stage
        self.calls = []

    def evaluate(self, **kwargs):
        self.calls.append(kwargs)
        return RiskResult(self.stage, .8, "WEAK", "g1_fake")


def make_guard(root: Path, action: str):
    base = load_two_stage_config(root / "configs/defense/two_stage_disabled.yaml")
    query_detector, session_detector = Detector("query"), Detector("session")
    gateway = TwoStageGateway(replace(base, mode="observe"), query_detector=query_detector,
                              session_detector=session_detector, defer_session_commit=True)
    selector = lambda decision, candidates: (action, frozenset({"target"}) if action == "hide_target_refill" else frozenset())
    return GuardedRAG(Store(), gateway, 2, action_selector=selector,
                      summarizer=lambda items: "general topic"), query_detector, session_detector


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    root = Path(__file__).resolve().parents[1]
    ledger = ExposureStore()
    hide_guard, hide_q, hide_s = make_guard(root, "hide_target_refill")
    hidden = run_guarded_request(OnlineRequest("r-hide", "s-hide", "question"), hide_guard, ledger, lambda prepared: "safe answer")
    cached = run_guarded_request(OnlineRequest("r-hide", "s-hide", "question"), hide_guard, ledger, lambda prepared: "unexpected")
    summary_guard, _, _ = make_guard(root, "sanitized_context")
    run_guarded_request(OnlineRequest("r-summary", "s-summary", "question"), summary_guard, ledger, lambda prepared: "general answer")
    failed_guard, _, _ = make_guard(root, "allow")
    try:
        run_guarded_request(OnlineRequest("r-failed", "s-failed", "question"), failed_guard, ledger,
                            lambda prepared: (_ for _ in ()).throw(RuntimeError("fake generation failure")))
    except RuntimeError:
        pass
    result = {
        "schema_version": 1,
        "status": "complete",
        "hide": ledger.history("s-hide")[0].to_dict(),
        "summary": ledger.history("s-summary")[0].to_dict(),
        "failed": ledger.history("s-failed")[0].to_dict(),
        "hide_retry_cached": cached.cached,
        "hide_new_requests": ledger.counters("s-hide")["new_requests"],
        "hide_retries": ledger.counters("s-hide")["retries"],
        "hide_gateway_turns": hide_guard.detector.session_store.turn_count("s-hide"),
        "judge_precontrol_doc_ids": list(hide_s.calls[0]["retrieved_doc_ids"]),
        "query_judge_calls_after_retry": len(hide_q.calls),
        "limitations": "Fake components only; no answer-quality or membership-leakage estimate.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "hidden_delivered": result["hide"]["delivered_evidence"],
                      "summary_transform_input": result["summary"]["transform_input_evidence"],
                      "failure_status": result["failed"]["status"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
