from __future__ import annotations

import re
import time
from collections import Counter
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any, Callable

import numpy as np
import yaml
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score

from rag_mia_data.io_utils import utc_now_iso

from .defense_contracts import Evidence
from .evidence_access import ActionExecution, evidence_from_hit, execute_action


@dataclass(frozen=True)
class DefenseConfig:
    medium_threshold: float
    high_threshold: float
    history_size: int
    restrict_context_chars: int
    medium_action: str
    high_action: str


@dataclass(frozen=True)
class DefenseDecision:
    query_risk: float
    session_risk: float
    total_risk: float
    risk_level: str
    reason_codes: tuple[str, ...]
    access_action: str
    detector_type: str = "rule"
    predicted_attack_type: str = "none"
    judge_verdict: str = "not_applicable"
    judge_confidence: str = "not_applicable"
    judge_verification: str = "not_applicable"
    loaded_pattern_ids: tuple[str, ...] = ()
    pattern_library_version: str = ""
    query_risk_class: str = "not_applicable"
    session_risk_class: str = "not_applicable"
    access_level: str = ""
    applied_access_level: str = ""
    policy_action_codes: tuple[str, ...] = ()
    applied_policy_action_codes: tuple[str, ...] = ()
    defense_mode: str = ""
    aggregation_method: str = ""
    window_size_actual: int = 0
    window_coverage: float = 0.0
    two_stage_assessment: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["reason_codes"] = list(self.reason_codes)
        value["loaded_pattern_ids"] = list(self.loaded_pattern_ids)
        value["policy_action_codes"] = list(self.policy_action_codes)
        value["applied_policy_action_codes"] = list(
            self.applied_policy_action_codes
        )
        return value


@dataclass(frozen=True)
class PreparedRAGRequest:
    contexts: list[str]
    retrieved_doc_ids: list[str]
    retrieval_scores: list[float]
    decision: DefenseDecision
    decision_latency_ms: float
    action_execution: ActionExecution | None = None


def _mapping(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"Missing or invalid configuration section: {name}")
    return value


def load_defense_config(path: str | Path) -> DefenseConfig:
    with Path(path).open("r", encoding="utf-8") as handle:
        raw = _mapping(yaml.safe_load(handle), "defense configuration")
    risk = _mapping(raw.get("risk"), "risk")
    session = _mapping(raw.get("session"), "session")
    access = _mapping(raw.get("access_control"), "access_control")
    config = DefenseConfig(
        medium_threshold=float(risk["medium_threshold"]),
        high_threshold=float(risk["high_threshold"]),
        history_size=int(session["history_size"]),
        restrict_context_chars=int(access["restrict_context_chars"]),
        medium_action=str(access.get("medium_action", "restrict_context")),
        high_action=str(access.get("high_action", "deny_sensitive_answer")),
    )
    if not 0 < config.medium_threshold < config.high_threshold <= 1:
        raise ValueError("Defense thresholds must satisfy 0 < medium < high <= 1")
    if config.history_size < 3:
        raise ValueError("Defense history_size must be at least 3")
    if config.restrict_context_chars <= 0:
        raise ValueError("restrict_context_chars must be positive")
    valid_actions = {
        "restrict_context",
        "no_context_answer",
        "summarize_context",
        "deny_sensitive_answer",
    }
    if config.medium_action not in valid_actions:
        raise ValueError(f"Unsupported medium_action: {config.medium_action}")
    if config.high_action not in valid_actions:
        raise ValueError(f"Unsupported high_action: {config.high_action}")
    return config


class RuleDefense:
    def __init__(self, config: DefenseConfig) -> None:
        self.config = config
        self._history: dict[str, list[str | None]] = {}

    @staticmethod
    def detector_input_fields() -> tuple[str, ...]:
        return "query", "session_id", "retrieved_doc_ids"

    @staticmethod
    def _query_signals(query: str) -> tuple[float, list[str]]:
        text = query.casefold()
        score = 0.0
        reasons: list[str] = []
        membership_terms = re.search(
            r"\b(appear|present|exist|included|stored|contain(?:s|ed)?)\b",
            text,
        )
        storage_terms = re.search(
            r"\b(context|knowledge\s*base|retrieval|database|corpus)\b",
            text,
        )
        if membership_terms and storage_terms:
            score = max(score, 0.95)
            reasons.append("EXPLICIT_MEMBERSHIP_QUERY")
        if re.search(r"\[\s*mask[_\s-]*\d+\s*\]|\bfill (?:in|every) (?:the )?(?:mask|blank)", text):
            score = max(score, 0.95)
            reasons.append("MASKED_CONTENT_RECOVERY")
        if re.search(
            r"\bcomplete this sentence\b|\bcontinue (?:this|the)\b|"
            r"\breproduce (?:the|this|exact)\b|\brestore (?:the )?(?:exact|original)\b",
            text,
        ):
            score = max(score, 0.85)
            reasons.append("SEMANTIC_REPRODUCTION_REQUEST")
        if "i am inquiring about" in text:
            score = max(score, 0.5)
            reasons.append("FACT_PROBE_TEMPLATE")
        return score, reasons

    def decide(
        self,
        query: str,
        session_id: str,
        retrieved_doc_ids: list[str],
        retrieved_snippets: list[str] | None = None,
    ) -> DefenseDecision:
        if not query.strip() or not session_id.strip():
            raise ValueError("query and session_id must not be blank")
        query_risk, reasons = self._query_signals(query)
        top_document = retrieved_doc_ids[0] if retrieved_doc_ids else None
        history = self._history.setdefault(session_id, [])
        recent = (history + [top_document])[-self.config.history_size :]
        session_risk = 0.0
        observed = [doc_id for doc_id in recent if doc_id is not None]
        if len(recent) >= 3 and observed:
            concentration = max(Counter(observed).values()) / len(recent)
            if concentration >= 0.8:
                session_risk = 0.85
                reasons.append("REPEATED_RETRIEVAL_TARGET")
        history.append(top_document)
        del history[: -self.config.history_size]

        total_risk = max(query_risk, session_risk)
        if total_risk >= self.config.high_threshold:
            level = "high"
            action = self.config.high_action
        elif total_risk >= self.config.medium_threshold:
            level = "medium"
            action = self.config.medium_action
        else:
            level = "low"
            action = "allow"
        return DefenseDecision(
            query_risk=query_risk,
            session_risk=session_risk,
            total_risk=total_risk,
            risk_level=level,
            reason_codes=tuple(dict.fromkeys(reasons)),
            access_action=action,
        )


class GuardedRAG:
    def __init__(
        self,
        store: Any,
        detector: Any,
        top_k: int,
        *,
        action_selector: Callable[[DefenseDecision, tuple[Evidence, ...]], tuple[str, frozenset[str]]] | None = None,
        summarizer: Callable[[tuple[Evidence, ...]], str] | None = None,
        refill_failure_action: str = "no_context_answer",
    ) -> None:
        self.store = store
        self.detector = detector
        self.top_k = top_k
        self.action_selector = action_selector
        self.summarizer = summarizer
        self.refill_failure_action = refill_failure_action

    def prepare(
        self,
        query: str,
        session_id: str,
        *,
        risk_query: str | None = None,
        allowed_doc_ids: frozenset[str] | None = None,
    ) -> PreparedRAGRequest:
        started = time.perf_counter()
        visible_query = risk_query or query
        query_result = (
            self.detector.evaluate_query(visible_query, session_id)
            if hasattr(self.detector, "evaluate_query")
            else None
        )
        hits = (self.store.search(query, self.top_k) if allowed_doc_ids is None
                else self.store.search(query, self.top_k, allowed_doc_ids=allowed_doc_ids))
        retrieved_ids = [str(hit["document"]["doc_id"]) for hit in hits]
        scores = [float(hit["score"]) for hit in hits]
        retrieved_snippets = [str(hit["document"]["text"]) for hit in hits]
        if hasattr(self.detector, "finalize"):
            decision = self.detector.finalize(
                visible_query,
                session_id,
                retrieved_ids,
                scores,
                retrieved_snippets,
                query_result,
            )
        else:
            decision = self.detector.decide(
                visible_query,
                session_id,
                retrieved_ids,
                retrieved_snippets,
            )
        execution: ActionExecution | None = None
        if self.action_selector is not None:
            candidates = tuple(evidence_from_hit(hit) for hit in hits)
            chosen_action, target_ids = self.action_selector(decision, candidates)
            refill_audit: dict[str, Any] | None = None

            def retrieve(excluded: frozenset[str]) -> tuple[Evidence, ...]:
                nonlocal refill_audit
                if hasattr(self.store, "search_with_audit"):
                    found, refill_audit = self.store.search_with_audit(
                        query, self.top_k, allowed_doc_ids=allowed_doc_ids,
                        excluded_parent_ids=excluded,
                    )
                else:
                    found = self.store.search(
                        query, self.top_k, allowed_doc_ids=allowed_doc_ids,
                        excluded_parent_ids=excluded,
                    )
                return tuple(evidence_from_hit(hit) for hit in found)

            execution = execute_action(
                chosen_action, candidates, frozenset(target_ids), retrieve, self.summarizer,
                refill_failure_action=self.refill_failure_action,
            )
            assessment = dict(decision.two_stage_assessment or {})
            assessment["execution"] = {
                "recommended_action": execution.recommended_action,
                "applied_action": execution.applied_action,
                "status": execution.status,
                "reason_codes": list(execution.reason_codes),
                "candidate_doc_ids": list(execution.source_doc_ids),
                "delivered_doc_ids": [item.doc_id for item in execution.evidence],
                "excluded_parent_ids": sorted(execution.excluded_parent_ids),
                "summary_template_version": execution.summary_template_version,
                "refill_audit": refill_audit,
            }
            decision = replace(
                decision,
                access_action=execution.applied_action,
                applied_policy_action_codes=(execution.applied_action.upper(),),
                two_stage_assessment=assessment,
            )
            contexts = [item.text for item in execution.evidence]
        elif decision.access_action == "allow":
            contexts = [str(hit["document"]["text"]) for hit in hits]
        elif decision.access_action == "restrict_context":
            contexts = [
                str(hits[0]["document"]["text"])[
                    : self.detector.config.restrict_context_chars
                ]
            ] if hits else []
        elif decision.access_action == "summarize_context":
            contexts = [str(hits[0]["document"]["text"])] if hits else []
        else:
            contexts = []
        latency_ms = (time.perf_counter() - started) * 1000
        return PreparedRAGRequest(
            contexts=contexts,
            retrieved_doc_ids=retrieved_ids,
            retrieval_scores=scores,
            decision=decision,
            decision_latency_ms=latency_ms,
            action_execution=execution,
        )


def build_query_event(
    *,
    event_id: str,
    source_record_id: str,
    source_framework: str,
    run_id: str,
    dataset_id: str,
    session_id: str,
    turn_id: int,
    query: str,
    attack_type: str,
    intent_label: int,
    membership_label: int | None,
    target_doc_id: str | None,
    attack_metadata: dict[str, Any],
) -> dict[str, Any]:
    required_strings = {
        "event_id": event_id,
        "source_record_id": source_record_id,
        "source_framework": source_framework,
        "run_id": run_id,
        "dataset_id": dataset_id,
        "session_id": session_id,
        "query": query,
        "attack_type": attack_type,
    }
    blank = [name for name, value in required_strings.items() if not value.strip()]
    if blank:
        raise ValueError(f"Unified event fields must not be blank: {blank}")
    if turn_id <= 0 or intent_label not in {0, 1}:
        raise ValueError("turn_id must be positive and intent_label must be 0 or 1")
    if membership_label not in {None, 0, 1}:
        raise ValueError("membership_label must be null, 0, or 1")
    return {
        **required_strings,
        "turn_id": turn_id,
        "created_at": utc_now_iso(),
        "intent_label": intent_label,
        "membership_label": membership_label,
        "target_doc_id": target_doc_id,
        "retrieved_doc_ids": [],
        "retrieval_scores": [],
        "attack_metadata": dict(attack_metadata),
    }


def evaluate_defense_decisions(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        raise ValueError("Defense evaluation requires at least one decision")
    labels = np.asarray([int(row["intent_label"]) for row in rows], dtype=int)
    predictions = np.asarray(
        [0 if row["risk_level"] == "low" else 1 for row in rows], dtype=int
    )
    benign = labels == 0
    benign_count = int(np.sum(benign))
    false_positives = int(np.sum(predictions[benign] == 1)) if benign_count else 0
    actions = Counter(str(row["access_action"]) for row in rows)
    return {
        "sample_count": len(rows),
        "attack_query_count": int(np.sum(labels == 1)),
        "benign_query_count": benign_count,
        "accuracy": float(accuracy_score(labels, predictions)),
        "precision": float(precision_score(labels, predictions, zero_division=0)),
        "recall": float(recall_score(labels, predictions, zero_division=0)),
        "f1": float(f1_score(labels, predictions, zero_division=0)),
        "benign_false_positive_rate": (
            false_positives / benign_count if benign_count else 0.0
        ),
        "benign_allow_rate": (
            int(np.sum(predictions[benign] == 0)) / benign_count if benign_count else 0.0
        ),
        "action_counts": dict(sorted(actions.items())),
        "average_decision_latency_ms": float(
            np.mean([float(row["decision_latency_ms"]) for row in rows])
        ),
    }


__all__ = [
    "DefenseConfig",
    "DefenseDecision",
    "GuardedRAG",
    "PreparedRAGRequest",
    "RuleDefense",
    "build_query_event",
    "evaluate_defense_decisions",
    "load_defense_config",
]
