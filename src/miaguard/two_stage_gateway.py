from __future__ import annotations

import time
import hashlib
import json
from dataclasses import dataclass, replace
from math import isfinite
from pathlib import Path
from typing import Any, Callable

import yaml

from .access_policy import LevelMapper
from .defense import DefenseDecision
from .frozen_risk_scorer import FrozenRiskScorer, resolve_risk
from .online_judge_adapter import AdaptedTrace, adapt_trace
from .progressive_judge import ProgressiveJudgeTrace
from .risk_aggregator import RiskAggregator
from .risk_types import RiskResult, SessionTurn
from .session_store import SessionStore
from rag_mia_data.io_utils import utc_now_iso


@dataclass(frozen=True)
class TwoStageConfig:
    mode: str
    window_size: int
    session_timeout_seconds: int
    min_session_queries: int
    session_evaluation_interval: int
    aggregation_method: str
    query_weight: float
    session_weight: float
    query_critical_threshold: float
    session_critical_threshold: float
    level_thresholds: tuple[float, float, float, float]
    restrict_context_chars: int
    l2_attack_actions: dict[str, str]
    policy_version: str
    attack_detection_threshold: float | None = None


@dataclass(frozen=True)
class FrozenObserveConfig:
    gateway: TwoStageConfig
    scorer: FrozenRiskScorer
    query_only_threshold: float
    fused_threshold: float
    query_only_sha256: str
    fpr_cap: str


def load_defense_v1_observe_config(path: str | Path, project_root: str | Path) -> FrozenObserveConfig:
    gateway = load_two_stage_config(path)
    if (gateway.mode, gateway.window_size, gateway.min_session_queries, gateway.session_evaluation_interval) != ("observe", 5, 3, 1):
        raise ValueError("Defense v1 observe requires mode=observe, window=5, min_session_queries=3 and every-turn evaluation")
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    frozen = raw.get("frozen") if isinstance(raw, dict) else None
    if not isinstance(frozen, dict):
        raise ValueError("Missing frozen artifact binding")
    root = Path(project_root).resolve()
    model_path = root / str(frozen["model_path"])
    query_only_path = root / str(frozen["query_only_path"])
    scorer = FrozenRiskScorer.from_file(model_path, str(frozen["head"]), str(frozen["model_sha256"]))
    raw_query = query_only_path.read_bytes()
    query_sha = hashlib.sha256(raw_query).hexdigest()
    if query_sha != frozen["query_only_sha256"]:
        raise ValueError("Query-only threshold SHA256 does not match")
    artifact = json.loads(raw_query)
    if artifact.get("partition") != "train" or artifact.get("head") != scorer.head:
        raise ValueError("Query-only threshold source must be logprob formal train")
    cap = str(frozen["fpr_cap"])
    point = artifact["working_points"].get(cap)
    if not isinstance(point, dict) or point.get("fpr_cap") != float(cap):
        raise ValueError("Query-only FPR cap is absent or invalid")
    threshold = float(point["threshold"])
    if not isfinite(threshold) or threshold < 0 or threshold > 1.0000000000000002:
        raise ValueError("Invalid Query-only threshold")
    return FrozenObserveConfig(gateway, scorer, threshold, scorer.thresholds[cap], query_sha, cap)


def load_two_stage_config(path: str | Path) -> TwoStageConfig:
    with Path(path).open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    if not isinstance(raw, dict):
        raise ValueError("Two-stage configuration must be a YAML mapping")
    session = raw.get("session")
    aggregation = raw.get("aggregation")
    policy = raw.get("policy")
    access = raw.get("access_control")
    versions = raw.get("versions", {})
    if not all(isinstance(value, dict) for value in (session, aggregation, policy, access, versions)):
        raise ValueError("Invalid two-stage configuration section")
    thresholds = tuple(float(value) for value in policy.get("thresholds", []))
    if len(thresholds) != 4:
        raise ValueError("Two-stage policy requires four L0-L4 thresholds")
    raw_attack_threshold = policy.get("attack_detection_threshold")
    attack_detection_threshold = (
        None if raw_attack_threshold is None else float(raw_attack_threshold)
    )
    config = TwoStageConfig(
        mode=str(raw.get("mode", "disabled")),
        window_size=int(session["window_size"]),
        session_timeout_seconds=int(session["timeout_seconds"]),
        min_session_queries=int(session["min_session_queries"]),
        session_evaluation_interval=int(session.get("evaluation_interval", 1)),
        aggregation_method=str(aggregation["method"]),
        query_weight=float(aggregation["query_weight"]),
        session_weight=float(aggregation["session_weight"]),
        query_critical_threshold=float(aggregation["query_critical_threshold"]),
        session_critical_threshold=float(aggregation["session_critical_threshold"]),
        level_thresholds=thresholds,  # type: ignore[arg-type]
        restrict_context_chars=int(access["restrict_context_chars"]),
        l2_attack_actions={
            str(key): str(value)
            for key, value in access.get("l2_attack_actions", {}).items()
        },
        policy_version=str(versions.get("policy", "two_stage_policy_v1")),
        attack_detection_threshold=attack_detection_threshold,
    )
    if config.mode not in {"disabled", "observe", "enforce"}:
        raise ValueError(f"Unsupported two-stage mode: {config.mode}")
    if config.window_size <= 0 or config.session_timeout_seconds <= 0:
        raise ValueError("Session window and timeout must be positive")
    if not 1 <= config.min_session_queries <= config.window_size:
        raise ValueError("min_session_queries must be within the session window")
    if config.session_evaluation_interval <= 0:
        raise ValueError("session evaluation_interval must be positive")
    if config.restrict_context_chars <= 0 or not config.policy_version.strip():
        raise ValueError("Invalid access-control size or policy version")
    if config.attack_detection_threshold is not None and not (
        0 <= config.attack_detection_threshold <= 1
    ):
        raise ValueError("attack detection threshold must be in [0, 1]")
    valid_actions = {
        "restrict_context",
        "no_context_answer",
        "summarize_context",
        "deny_sensitive_answer",
    }
    if any(action not in valid_actions for action in config.l2_attack_actions.values()):
        raise ValueError("Unsupported attack-aware L2 access action")
    return config


class NoOpRiskDetector:
    def __init__(self, stage: str) -> None:
        if stage not in {"query", "session"}:
            raise ValueError("No-op detector stage must be query or session")
        self.stage = stage

    def evaluate(self, **_: Any) -> RiskResult:
        return RiskResult(
            stage=self.stage,
            score=0.0,
            risk_class="NONE",
            scoring_method="noop",
        )


class TwoStageGateway:
    def __init__(
        self,
        config: TwoStageConfig,
        *,
        query_detector: Any | None = None,
        session_detector: Any | None = None,
        session_store: SessionStore | None = None,
        frozen_scorer: FrozenRiskScorer | None = None,
        query_only_threshold: float | None = None,
        fused_threshold: float | None = None,
        trace_sink: Callable[[AdaptedTrace], None] | None = None,
        defer_session_commit: bool = False,
    ) -> None:
        if frozen_scorer is not None:
            if query_only_threshold is None or fused_threshold is None:
                raise ValueError("Frozen scorer requires Query-only and fusion thresholds")
            if config.session_evaluation_interval != 1:
                raise ValueError("Frozen scorer requires session evaluation each turn")
            for value in (query_only_threshold, fused_threshold):
                if not isfinite(value) or not 0 <= value <= 1.0000000000000002:
                    raise ValueError("Frozen thresholds must be finite and within score range")
        self.config = config
        self.frozen_scorer = frozen_scorer
        self.query_only_threshold = query_only_threshold
        self.fused_threshold = fused_threshold
        self.trace_sink = trace_sink
        self.defer_session_commit = defer_session_commit
        self._pending_turns: dict[str, SessionTurn] = {}
        self.query_detector = query_detector or NoOpRiskDetector("query")
        self.session_detector = session_detector or NoOpRiskDetector("session")
        self.session_store = session_store or SessionStore(
            config.window_size,
            config.session_timeout_seconds,
        )
        self.aggregator = RiskAggregator(
            method=config.aggregation_method,
            query_weight=config.query_weight,
            session_weight=config.session_weight,
            query_critical_threshold=config.query_critical_threshold,
            session_critical_threshold=config.session_critical_threshold,
            window_size=config.window_size,
        )
        self.level_mapper = LevelMapper(
            config.level_thresholds,
            attack_detection_threshold=config.attack_detection_threshold,
        )
        self._session_risk_cache: dict[str, RiskResult] = {}

    def clear_session(self, session_id: str) -> None:
        if not session_id.strip():
            raise ValueError("session_id must not be blank")
        self.session_store.clear(session_id)
        self._session_risk_cache.pop(session_id, None)
        self._pending_turns.pop(session_id, None)

    def _append_or_defer(self, session_id: str, turn: SessionTurn) -> None:
        if self.defer_session_commit:
            if session_id in self._pending_turns:
                raise RuntimeError("A session turn is pending commit")
            self._pending_turns[session_id] = turn
        else:
            self.session_store.append(session_id, turn, now=time.time())

    def commit_session(self, session_id: str) -> SessionTurn | None:
        """Commit a staged turn after the answer or an explicit failed attempt."""
        turn = self._pending_turns.pop(session_id, None)
        return self.session_store.append(session_id, turn, now=time.time()) if turn is not None else None

    @staticmethod
    def detector_input_fields() -> tuple[str, ...]:
        return (
            "query",
            "session_id",
            "recent_turns",
            "retrieved_doc_ids",
            "retrieval_scores",
        )

    def evaluate_query(self, query: str, session_id: str) -> RiskResult | AdaptedTrace:
        if not query.strip() or not session_id.strip():
            raise ValueError("query and session_id must not be blank")
        if self.defer_session_commit and session_id in self._pending_turns:
            raise RuntimeError("A session turn is pending commit")
        if self.config.mode == "disabled":
            return NoOpRiskDetector("query").evaluate()
        if self.frozen_scorer is not None:
            try:
                detector = self.query_detector
                raw = (detector.evaluate_query(query=query, session_id=session_id)
                       if hasattr(detector, "evaluate_query") else detector.evaluate(query=query, session_id=session_id))
                adapted = self._adapt(raw, "query")
                if isinstance(adapted, AdaptedTrace) and self.trace_sink is not None:
                    self.trace_sink(adapted)
                return adapted
            except Exception:
                return RiskResult("query", 0.0, "NONE", "progressive_judge_v3_error", status="error")
        return self.query_detector.evaluate(query=query, session_id=session_id)

    def _adapt(self, raw: Any, stage: str) -> RiskResult | AdaptedTrace:
        if isinstance(raw, ProgressiveJudgeTrace):
            if raw.stage != stage:
                raise ValueError("Judge trace stage mismatch")
            assert self.frozen_scorer is not None
            return adapt_trace(raw, self.frozen_scorer.head)
        if isinstance(raw, RiskResult) and raw.stage == stage:
            return raw
        raise ValueError("Judge result stage or type mismatch")

    def finalize(
        self,
        query: str,
        session_id: str,
        retrieved_doc_ids: list[str],
        retrieval_scores: list[float],
        retrieved_snippets: list[str],
        query_result: RiskResult | AdaptedTrace,
    ) -> DefenseDecision:
        del retrieved_snippets
        if self.frozen_scorer is not None and self.config.mode != "disabled":
            return self._finalize_frozen(query, session_id, retrieved_doc_ids, retrieval_scores, query_result)
        if isinstance(query_result, AdaptedTrace):
            query_result = query_result.risk
        if self.config.mode == "disabled":
            session_result = NoOpRiskDetector("session").evaluate()
            actual_window_size = 0
        else:
            recent_turns = self.session_store.window(session_id)
            total_previous_turns = self.session_store.turn_count(session_id)
            actual_window_size = min(
                self.config.window_size,
                len(recent_turns) + 1,
            )
            turn_number = total_previous_turns + 1
            should_evaluate = (
                turn_number < self.config.min_session_queries
                or session_id not in self._session_risk_cache
                or (
                    turn_number - self.config.min_session_queries
                )
                % self.config.session_evaluation_interval
                == 0
            )
            if should_evaluate:
                session_result = self.session_detector.evaluate(
                    query=query,
                    session_id=session_id,
                    recent_turns=recent_turns,
                    retrieved_doc_ids=tuple(retrieved_doc_ids),
                    retrieval_scores=tuple(retrieval_scores),
                    min_session_queries=self.config.min_session_queries,
                )
                if session_result.status != "insufficient_history":
                    self._session_risk_cache[session_id] = session_result
            else:
                session_result = replace(
                    self._session_risk_cache[session_id],
                    status="cached_recent_assessment",
                    latency_ms=0.0,
                )
        aggregation_window_size = (
            0
            if session_result.status == "insufficient_history"
            else actual_window_size
        )
        aggregated = self.aggregator.aggregate(
            query_result,
            session_result,
            aggregation_window_size,
        )
        policy = self.level_mapper.decide(aggregated.total_risk, self.config.mode)
        predicted_attack_type = (
            query_result.suspected_attack_types[0]
            if query_result.suspected_attack_types
            else session_result.suspected_attack_types[0]
            if session_result.suspected_attack_types
            else "none"
        )
        if policy.applied_level == "L2" and predicted_attack_type in self.config.l2_attack_actions:
            action = self.config.l2_attack_actions[predicted_attack_type]
            policy = replace(
                policy,
                access_action=action,
                applied_actions=policy.applied_actions
                + (f"ATTACK_AWARE_{action.upper()}",),
            )

        if self.config.mode != "disabled":
            self._append_or_defer(
                session_id,
                SessionTurn(
                    turn_id=0,
                    timestamp=0.0,
                    query=query,
                    query_risk_score=query_result.score,
                    query_risk_class=query_result.risk_class,
                    retrieved_doc_ids=tuple(retrieved_doc_ids),
                    retrieval_scores=tuple(retrieval_scores),
                    recommended_level=policy.recommended_level,
                    applied_level=policy.applied_level,
                ),
            )

        risk_level = {
            "L0": "low",
            "L1": "low",
            "L2": "medium",
            "L3": "medium",
            "L4": "high",
        }[policy.recommended_level]
        reasons = tuple(
            dict.fromkeys(query_result.evidence_codes + session_result.evidence_codes)
        )
        return DefenseDecision(
            query_risk=query_result.score,
            session_risk=session_result.score,
            total_risk=aggregated.total_risk,
            risk_level=risk_level,
            reason_codes=reasons,
            access_action=policy.access_action,
            detector_type="two_stage_gateway",
            predicted_attack_type=predicted_attack_type,
            query_risk_class=query_result.risk_class,
            session_risk_class=session_result.risk_class,
            access_level=policy.recommended_level,
            applied_access_level=policy.applied_level,
            policy_action_codes=policy.recommended_actions,
            applied_policy_action_codes=policy.applied_actions,
            defense_mode=self.config.mode,
            aggregation_method=aggregated.method,
            window_size_actual=actual_window_size,
            window_coverage=aggregated.window_coverage,
            two_stage_assessment={
                "query_detection": {
                    "stage": "query",
                    "risk_score": query_result.score,
                    "risk_class": query_result.risk_class,
                    "scoring_method": query_result.scoring_method,
                    "suspected_attack_types": list(
                        query_result.suspected_attack_types
                    ),
                    "evidence_codes": list(query_result.evidence_codes),
                    "status": query_result.status,
                },
                "session_detection": {
                    "stage": "session",
                    "risk_score": session_result.score,
                    "risk_class": session_result.risk_class,
                    "scoring_method": session_result.scoring_method,
                    "suspected_attack_types": list(
                        session_result.suspected_attack_types
                    ),
                    "evidence_codes": list(session_result.evidence_codes),
                    "status": session_result.status,
                },
                "aggregation": {
                    "method": aggregated.method,
                    "query_weight": aggregated.query_weight,
                    "session_weight": aggregated.session_weight,
                    "window_coverage": aggregated.window_coverage,
                    "total_risk_score": aggregated.total_risk,
                },
                "access_control": {
                    "mode": policy.mode,
                    "recommended_level": policy.recommended_level,
                    "applied_level": policy.applied_level,
                    "recommended_actions": list(policy.recommended_actions),
                    "applied_actions": list(policy.applied_actions),
                    "access_action": policy.access_action,
                },
                "latency_ms": {
                    "query_detector": query_result.latency_ms,
                    "session_detector": session_result.latency_ms,
                    "total_defense": query_result.latency_ms + session_result.latency_ms,
                },
                "versions": {
                    "query_scorer": query_result.scoring_method,
                    "session_scorer": session_result.scoring_method,
                    "policy": self.config.policy_version,
                },
            },
        )

    def _finalize_frozen(
        self,
        query: str,
        session_id: str,
        retrieved_doc_ids: list[str],
        retrieval_scores: list[float],
        query_result: RiskResult | AdaptedTrace,
    ) -> DefenseDecision:
        assert self.frozen_scorer is not None
        query_ref = query_result.trace_ref if isinstance(query_result, AdaptedTrace) else None
        query_risk = query_result.risk if isinstance(query_result, AdaptedTrace) else query_result
        recent_turns = self.session_store.window(session_id)
        turn_number = self.session_store.turn_count(session_id) + 1
        session_ref = None
        if turn_number < self.config.min_session_queries:
            session_risk = RiskResult("session", 0.0, "NONE", "not_called", status="insufficient_history")
        else:
            try:
                detector = self.session_detector
                arguments = dict(query=query, session_id=session_id, recent_turns=recent_turns,
                                 retrieved_doc_ids=tuple(retrieved_doc_ids), retrieval_scores=tuple(retrieval_scores),
                                 min_session_queries=self.config.min_session_queries)
                raw = (detector.evaluate_session(**arguments) if hasattr(detector, "evaluate_session")
                       else detector.evaluate(**arguments))
                adapted = self._adapt(raw, "session")
                if isinstance(adapted, AdaptedTrace) and self.trace_sink is not None:
                    self.trace_sink(adapted)
                session_ref = adapted.trace_ref if isinstance(adapted, AdaptedTrace) else None
                session_risk = adapted.risk if isinstance(adapted, AdaptedTrace) else adapted
            except Exception:
                session_risk = RiskResult("session", 0.0, "NONE", "progressive_judge_v3_error", status="error")
        estimate = resolve_risk(
            query_risk.score if query_risk.status == "ok" else None,
            session_risk.score if session_risk.status == "ok" else None,
            query_risk.status,
            "missing" if session_risk.status == "insufficient_history" else session_risk.status,
            self.frozen_scorer,
        )
        threshold = self.fused_threshold if estimate.risk_source == "fusion" else self.query_only_threshold
        score = estimate.fused_score if estimate.risk_source == "fusion" else estimate.x1
        trigger = score is None or (threshold is not None and score >= threshold)
        policy = self.level_mapper.decide(float(trigger), self.config.mode)
        if estimate.risk_source == "error" and self.config.mode == "enforce":
            policy = replace(policy, access_action="unavailable")
        self._append_or_defer(
            session_id,
            SessionTurn(turn_id=0, timestamp=0.0, query=query, query_risk_score=query_risk.score,
                        query_risk_class=query_risk.risk_class, retrieved_doc_ids=tuple(retrieved_doc_ids),
                        retrieval_scores=tuple(retrieval_scores), recommended_level=policy.recommended_level,
                        applied_level=policy.applied_level),
        )
        effective_score = 1.0 if score is None else score
        assessment = {
            "frozen_risk": {
                "risk_source": estimate.risk_source,
                "status": estimate.status,
                "x1": estimate.x1,
                "x2": estimate.x2,
                "score": score,
                "threshold": threshold,
                "triggered": trigger,
                "head": self.frozen_scorer.head,
                "frozen_model_sha256": self.frozen_scorer.sha256,
                "query_trace_ref": query_ref,
                "session_trace_ref": session_ref,
            },
            "query_detection": {
                "status": query_risk.status, "risk_score": query_risk.score, "scoring_method": query_risk.scoring_method,
                "suspected_attack_types": list(query_risk.suspected_attack_types), "evidence_codes": list(query_risk.evidence_codes),
            },
            "session_detection": {
                "status": session_risk.status, "risk_score": session_risk.score, "scoring_method": session_risk.scoring_method,
                "suspected_attack_types": list(session_risk.suspected_attack_types), "evidence_codes": list(session_risk.evidence_codes),
            },
            "access_control": {"mode": policy.mode, "recommended_level": policy.recommended_level,
                               "applied_level": policy.applied_level, "access_action": policy.access_action},
            "latency_ms": {"query_detector": query_risk.latency_ms, "session_detector": session_risk.latency_ms,
                           "total_defense": query_risk.latency_ms + session_risk.latency_ms},
        }
        return DefenseDecision(
            query_risk=query_risk.score,
            session_risk=session_risk.score,
            total_risk=effective_score,
            risk_level="high" if trigger else "low",
            reason_codes=tuple(dict.fromkeys(query_risk.evidence_codes + session_risk.evidence_codes)),
            access_action=policy.access_action,
            detector_type="frozen_progressive_judge_v3",
            predicted_attack_type=(query_risk.suspected_attack_types or session_risk.suspected_attack_types or ("none",))[0],
            query_risk_class=query_risk.risk_class,
            session_risk_class=session_risk.risk_class,
            access_level=policy.recommended_level,
            applied_access_level=policy.applied_level,
            policy_action_codes=policy.recommended_actions,
            applied_policy_action_codes=policy.applied_actions,
            defense_mode=self.config.mode,
            aggregation_method=estimate.risk_source,
            window_size_actual=min(self.config.window_size, len(recent_turns) + 1),
            window_coverage=min(1.0, (len(recent_turns) + 1) / self.config.window_size),
            two_stage_assessment=assessment,
        )


def build_two_stage_risk_event(
    *,
    event_id: str,
    session_id: str,
    turn_id: int,
    query_text: str,
    retrieved_doc_ids: list[str],
    retrieval_scores: list[float],
    decision: DefenseDecision,
) -> dict[str, Any]:
    required = (event_id, session_id, query_text)
    if any(not value.strip() for value in required) or turn_id <= 0:
        raise ValueError("Event identifiers and query must be non-blank; turn_id must be positive")
    if decision.two_stage_assessment is None:
        raise ValueError("Defense decision has no two-stage assessment")
    return {
        "event_id": event_id,
        "session_id": session_id,
        "turn_id": turn_id,
        "timestamp": utc_now_iso(),
        "query_text": query_text,
        "retrieved_doc_ids": list(retrieved_doc_ids),
        "retrieval_scores": list(retrieval_scores),
        **decision.two_stage_assessment,
    }


__all__ = [
    "FrozenObserveConfig",
    "NoOpRiskDetector",
    "TwoStageConfig",
    "TwoStageGateway",
    "build_two_stage_risk_event",
    "load_two_stage_config",
    "load_defense_v1_observe_config",
]
