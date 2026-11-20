"""Deterministic fake RAG and Judge for replay contract smoke tests only."""

from __future__ import annotations

import time
from dataclasses import replace
from pathlib import Path

from .defense import GuardedRAG
from .defense_contracts import OnlineRequest
from .defense_experiment import _text_response
from .exposure_store import ExposureStore, run_guarded_request
from .risk_types import RiskResult
from .two_stage_gateway import TwoStageGateway, load_two_stage_config


class _Store:
    def search(self, query, top_k, *, allowed_doc_ids=None, excluded_parent_ids=frozenset()):
        documents = [
            {"doc_id": "target", "parent_doc_id": "target", "text": "target story"},
            {"doc_id": "safe", "parent_doc_id": "safe", "text": "safe background"},
        ]
        return [
            {"document": document, "score": 1.0 - index / 10}
            for index, document in enumerate(documents)
            if document["doc_id"] not in excluded_parent_ids
            and (allowed_doc_ids is None or document["doc_id"] in allowed_doc_ids)
        ][:top_k]


class _Detector:
    def __init__(self, stage):
        self.stage = stage

    def evaluate(self, **kwargs):
        return RiskResult(self.stage, .95 if self.stage == "query" else .5, "STRONG" if self.stage == "query" else "WEAK", "fake_judge")


class _Client:
    def __init__(self):
        self.prompts = []

    def generate(self, model, prompt, **kwargs):
        self.prompts.append(prompt)
        return "Yes" if "target story" in prompt else "Unknown"


class FakeScoreClient:
    def embed(self, model, texts):
        return [[float(len(text) + 1), float(sum(char.casefold() in "aeiou" for char in text) + 1)] for text in texts]


class FakeBackend:
    def __init__(self, method: str, seed: int, session_id: str) -> None:
        if method not in {"B0", "B2", "B3", "B5"}:
            raise ValueError("Fake backend supports B0/B2/B3/B5")
        self.method = method
        self.seed = seed
        self.session_id = session_id
        root = Path(__file__).resolve().parents[2]
        base = load_two_stage_config(root / "configs/defense/two_stage_disabled.yaml")
        mode = "disabled" if method == "B0" else "observe"
        gateway = TwoStageGateway(replace(base, mode=mode), query_detector=_Detector("query"),
                                  session_detector=_Detector("session"), defer_session_commit=True)

        def select(decision, candidates):
            if method == "B0" or decision.access_level != "L4":
                return "allow", frozenset()
            return {
                "B2": ("deny", frozenset()),
                "B3": ("no_context_answer", frozenset()),
                "B5": ("hide_target_refill", frozenset({candidates[0].parent_doc_id}) if candidates else frozenset()),
            }[method]

        self.guard = GuardedRAG(_Store(), gateway, 2, action_selector=select)
        self.ledger = ExposureStore()
        self.client = _Client()
        self.config = type("FakeConfig", (), {"generation_model": "fake"})()

    def run(self, request: OnlineRequest) -> dict:
        if request.session_id != self.session_id:
            raise ValueError("Backend session isolation violation")
        captured = {}

        def answer(prepared):
            captured["prepared"] = prepared
            return _text_response(prepared, self.client, self.config, request.query,
                                  instruction="Answer using only the supplied Context.", max_tokens=24)

        before = time.perf_counter()
        outcome = run_guarded_request(request, self.guard, self.ledger, answer)
        prepared = captured["prepared"]
        event = outcome.event
        return {
            "response": outcome.response,
            "status": outcome.status,
            "retrieved_doc_ids": event.retrieved_doc_ids,
            "delivered_doc_ids": event.delivered_doc_ids,
            "generation_input": {"query": request.query, "contexts": list(prepared.contexts),
                                 "prompt": self.client.prompts[-1] if self.client.prompts else None,
                                 "template_version": "fake_rag_answer_v1"},
            "risk": prepared.decision.two_stage_assessment,
            "action": prepared.decision.access_action,
            "latency_ms": (time.perf_counter() - before) * 1000,
        }


def fake_backend_factory(method: str, seed: int, session_id: str) -> FakeBackend:
    return FakeBackend(method, seed, session_id)


__all__ = ["FakeBackend", "FakeScoreClient", "fake_backend_factory"]
