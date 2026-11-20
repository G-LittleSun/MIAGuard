"""Real Judge/RAG backend for the shared defense benchmark service."""

from __future__ import annotations

import time
import hashlib
import json
import re
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any

from .attack_pattern_library import AttackPatternLibrary
from .config import load_attack_config
from .data import vector_store_path
from .defense import GuardedRAG
from .defense_contracts import Evidence, OnlineRequest
from .defense_experiment import _context_prompt, _text_response, summarize_for_defense_v1
from .evidence_locator import LOCATOR_VERSION, locate_evidence
from .exposure_store import ExposureStore, run_guarded_request
from .model_client import create_model_client
from .progressive_judge import ProgressiveJudge, load_progressive_judge_config
from .query_cue import QUERY_CUE_VERSION, query_cues
from .two_stage_gateway import TwoStageGateway, load_defense_v1_observe_config
from .vector_store import UnifiedVectorStore


ANSWER_TEMPLATE_VERSION = "defense_v1_shared_answer_20261022"
ANSWER_INSTRUCTION = "Answer the question using only the supplied Context. If the Context does not support an answer, say that the evidence is insufficient."
TYPE_POLICY_METHODS = frozenset({"B_TYPE_V1", "B_TYPE_V2", "B_MULTI_SUMMARY", "B_MULTI_NO_CONTEXT", "B_NEXT_GOAL"})
KNOWN_ATTACK_TYPES = frozenset({"direct_rag_mia", "s2_mia", "masked_mia", "ia"})


class LiveBackend:
    def __init__(self, method: str, session_id: str, store: UnifiedVectorStore, judge: ProgressiveJudge,
                 bound: Any, client: Any, attack_config: Any, top_k: int, max_answer_tokens: int) -> None:
        if method not in {"B0", "B2", "B3", "B5", "B6", "B5_LOCATED", "B5_CUE"} | TYPE_POLICY_METHODS:
            raise ValueError("Unsupported live defense method")
        self.method = method
        self.session_id = session_id
        self.client = client
        self.attack_config = attack_config
        self.max_answer_tokens = max_answer_tokens
        self._traces = []
        self._active_query = ""
        self._localization = None
        self._query_cue = None
        self._type_policy = None
        config = replace(bound.gateway, mode="disabled" if method == "B0" else "observe")
        gateway = TwoStageGateway(config, query_detector=judge, session_detector=judge,
                                  frozen_scorer=None if method == "B0" else bound.scorer,
                                  query_only_threshold=None if method == "B0" else bound.query_only_threshold,
                                  fused_threshold=None if method == "B0" else bound.fused_threshold,
                                  trace_sink=self._traces.append, defer_session_commit=True)

        def select(decision, candidates):
            if method == "B0":
                return "allow", frozenset()
            if method in TYPE_POLICY_METHODS:
                return self._select_by_type(decision.two_stage_assessment or {}, candidates)
            risk = (decision.two_stage_assessment or {}).get("frozen_risk", {})
            if risk.get("risk_source") == "error":
                return "unavailable", frozenset()
            if method == "B5_CUE":
                cues = query_cues(self._active_query)
                self._query_cue = {"version": QUERY_CUE_VERSION, "cues": list(cues)}
                if cues and not risk.get("triggered", False):
                    return "deny", frozenset()
            if not risk.get("triggered", False):
                return "allow", frozenset()
            if method == "B2":
                return "deny", frozenset()
            if method == "B3":
                return "no_context_answer", frozenset()
            if method == "B5":
                return ("hide_target_refill", frozenset({candidates[0].parent_doc_id})) if candidates else ("no_context_answer", frozenset())
            if method in {"B5_LOCATED", "B5_CUE"}:
                return self._select_by_location(candidates)
            return "sanitized_context", frozenset()

        self.guard = GuardedRAG(
            store, gateway, top_k, action_selector=select,
            summarizer=lambda items: summarize_for_defense_v1(items, client, attack_config),
            refill_failure_action="deny" if method in TYPE_POLICY_METHODS else "no_context_answer",
        )
        self.ledger = ExposureStore(timeout_seconds=config.session_timeout_seconds)

    def _select_by_location(self, candidates: tuple[Evidence, ...]) -> tuple[str, frozenset[str]]:
        result = locate_evidence(self._active_query, candidates)
        self._localization = {"version": LOCATOR_VERSION, "status": result.status,
                              "parent_ids": sorted(result.parent_ids),
                              "matching_trigrams": result.matching_trigrams}
        return ("hide_target_refill", result.parent_ids) if result.status == "located" else ("deny", frozenset())

    def _select_by_type(
        self, assessment: dict[str, Any], candidates: tuple[Evidence, ...],
    ) -> tuple[str, frozenset[str]]:
        risk = assessment.get("frozen_risk", {})
        query = assessment.get("query_detection", {})
        session = assessment.get("session_detection", {})
        query_types = set(query.get("suspected_attack_types", ())) if query.get("status") == "ok" else set()
        session_types = set(session.get("suspected_attack_types", ())) if session.get("status") == "ok" else set()
        predicted = query_types | session_types
        prior_raw = sum(event.delivered_exposure == "raw" for event in self.ledger.history(self.session_id))
        self._type_policy = {"version": self.method, "suspected_attack_types": sorted(predicted),
                             "prior_raw_delivery_requests": prior_raw}
        recovery_cue = False
        if self.method in {"B_TYPE_V2", "B_MULTI_SUMMARY", "B_MULTI_NO_CONTEXT", "B_NEXT_GOAL"}:
            cues = query_cues(self._active_query)
            recovery_cue = "masked_recovery" in cues
            self._type_policy["query_cues"] = {"version": QUERY_CUE_VERSION, "cues": list(cues)}
        action, parents = "deny", frozenset()
        if risk.get("status") != "ok":
            action, reason = "unavailable", "judge_failure"
        elif not risk["triggered"]:
            if self.method == "B_NEXT_GOAL" and "quoted_context_check" in cues:
                reason = "cue_direct"
            elif self.method == "B_NEXT_GOAL" and recovery_cue:
                reason = "cue_masked"
            elif (self.method == "B_NEXT_GOAL"
                  and re.search(r'\b(?:article|report)\b', self._active_query, re.I)
                  and re.search(r'\b(?:yes\s*,\s*no\s*,?\s*or\s*unknown)\b', self._active_query, re.I)):
                action, reason = ("deny", "cue_ia_prior_raw") if prior_raw else ("no_context_answer", "cue_ia_first")
            else:
                action, reason = "allow", "low_risk"
        elif len(predicted) > 1:
            reason = "multiple_types"
        elif not predicted or not predicted <= KNOWN_ATTACK_TYPES:
            reason = "unknown_type"
        elif predicted == {"direct_rag_mia"}:
            reason = "direct"
        elif predicted == {"masked_mia"} and recovery_cue:
            reason = "masked_recovery"
        elif predicted == {"s2_mia"} and self.method == "B_MULTI_SUMMARY":
            action, reason = "sanitized_context", "s2_summary"
        elif predicted == {"s2_mia"} and self.method == "B_MULTI_NO_CONTEXT":
            action, reason = "no_context_answer", "s2_no_context"
        elif predicted == {"ia"}:
            if "ia" in session_types:
                reason = "ia_session"
            elif prior_raw:
                reason = "ia_prior_raw_delivery"
            else:
                action, reason = "no_context_answer", "ia_query_only"
        else:
            action, parents = self._select_by_location(candidates)
            reason = self._localization["status"]
        self._type_policy.update({"reason": reason, "selected_action": action})
        return action, parents

    def run(self, request: OnlineRequest) -> dict[str, Any]:
        if request.session_id != self.session_id:
            raise ValueError("Live backend session isolation violation")
        self._active_query = request.query
        self._localization = None
        self._query_cue = None
        self._type_policy = None
        trace_start = len(self._traces)
        captured: dict[str, Any] = {}

        def answer(prepared):
            captured["prepared"] = prepared
            captured["generation_input"] = {
                "query": request.query,
                "contexts": list(prepared.contexts),
                "prompt": None if prepared.decision.access_action in {"deny", "unavailable"}
                else _context_prompt(prepared.contexts, request.query, ANSWER_INSTRUCTION),
                "template_version": ANSWER_TEMPLATE_VERSION,
                "summary_template_version": prepared.action_execution.summary_template_version if prepared.action_execution else None,
            }
            return _text_response(prepared, self.client, self.attack_config, request.query,
                                  instruction=ANSWER_INSTRUCTION, max_tokens=self.max_answer_tokens)

        started = time.perf_counter()
        try:
            outcome = run_guarded_request(request, self.guard, self.ledger, answer)
            event = outcome.event
            status = "complete"
            reason = None
            response = outcome.response
        except Exception as exc:
            history = self.ledger.history(request.session_id)
            event = history[-1] if history else None
            status = "failed"
            reason = f"{type(exc).__name__}: {exc}"
            response = None
        prepared = captured.get("prepared")
        risk = dict(prepared.decision.two_stage_assessment or {}) if prepared else None
        if risk is not None and self._localization is not None:
            risk["localization"] = self._localization
        if risk is not None and self._query_cue is not None:
            risk["query_cue"] = self._query_cue
        if risk is not None and self._type_policy is not None:
            risk["type_policy"] = self._type_policy
        return {
            "status": status, "reason": reason, "response": response,
            "retrieved_doc_ids": event.retrieved_doc_ids if event else (),
            "delivered_doc_ids": event.delivered_doc_ids if event else (),
            "ledger_event": event.to_dict() if event else None,
            "generation_input": captured.get("generation_input", {}),
            "judge_traces": [{"trace_ref": item.trace_ref, "risk": item.risk.to_dict(),
                              "trace": asdict(item.trace)} for item in self._traces[trace_start:]],
            "risk": risk,
            "action": prepared.decision.access_action if prepared else None,
            "latency_ms": (time.perf_counter() - started) * 1000,
        }


def make_live_backend_factory(spec: dict[str, Any]):
    root = Path(__file__).resolve().parents[2]
    files = {name: Path(path).resolve() for name, path in spec["identity_files"].items()}
    bound = load_defense_v1_observe_config(files["gateway_config"], root)
    judge_config = load_progressive_judge_config(files["judge_config"], root)
    judge_config.validate_partition(str(spec.get("judge_partition", spec["partition"])))
    if files["pattern_manifest"] != judge_config.manifest_path.resolve():
        raise ValueError("Pattern library identity path does not match Judge config")
    if hashlib.sha256(files["frozen_model"].read_bytes()).hexdigest() != bound.scorer.sha256:
        raise ValueError("Frozen model identity does not match gateway config")
    if hashlib.sha256(files["query_only_threshold"].read_bytes()).hexdigest() != bound.query_only_sha256:
        raise ValueError("Query-only identity does not match gateway config")
    source_manifest = json.loads(files["source_train_manifest"].read_text(encoding="utf-8"))
    if source_manifest.get("identity", {}).get("partition") != "train":
        raise ValueError("Frozen scorer source must be formal train")
    attack_config = load_attack_config(files["attack_config"])
    source_run_id = str(spec["source_run_id"])
    vector_path = vector_store_path(root, source_run_id, str(spec["dataset_id"]))
    if files["vector_index"] != vector_path / "index.faiss":
        raise ValueError("Live vector index identity path does not match source_run_id")
    client = create_model_client(attack_config, root)
    client.validate_models()
    store = UnifiedVectorStore.load(vector_path, client)
    library = AttackPatternLibrary.load(judge_config.manifest_path)
    judge = ProgressiveJudge(judge_config, client, attack_config.generation_model, library)

    def factory(method: str, seed: int, session_id: str) -> LiveBackend:
        return LiveBackend(method, session_id, store, judge, bound, client, attack_config,
                           int(spec.get("top_k", attack_config.top_k)), int(spec.get("max_answer_tokens", 128)))

    return factory, client


__all__ = ["ANSWER_TEMPLATE_VERSION", "LiveBackend", "make_live_backend_factory"]
