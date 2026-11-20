from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


RISK_CLASSES = {"NONE", "WEAK", "STRONG"}


@dataclass(frozen=True)
class RiskResult:
    stage: str
    score: float
    risk_class: str
    scoring_method: str
    suspected_attack_types: tuple[str, ...] = ()
    evidence_codes: tuple[str, ...] = ()
    status: str = "ok"
    latency_ms: float = 0.0

    def __post_init__(self) -> None:
        if self.stage not in {"query", "session"}:
            raise ValueError("Risk stage must be query or session")
        if not 0.0 <= self.score <= 1.0:
            raise ValueError("Risk score must be between 0 and 1")
        if self.risk_class not in RISK_CLASSES:
            raise ValueError(f"Unsupported risk class: {self.risk_class}")
        if not self.scoring_method.strip() or not self.status.strip():
            raise ValueError("Risk scoring_method and status must not be blank")
        if self.latency_ms < 0:
            raise ValueError("Risk latency must not be negative")

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["suspected_attack_types"] = list(self.suspected_attack_types)
        value["evidence_codes"] = list(self.evidence_codes)
        return value


@dataclass(frozen=True)
class AggregatedRisk:
    query_risk: float
    session_risk: float
    total_risk: float
    query_weight: float
    session_weight: float
    window_coverage: float
    method: str
    critical_sources: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["critical_sources"] = list(self.critical_sources)
        return value


@dataclass(frozen=True)
class PolicyDecision:
    recommended_level: str
    applied_level: str
    recommended_actions: tuple[str, ...]
    applied_actions: tuple[str, ...]
    access_action: str
    mode: str

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["recommended_actions"] = list(self.recommended_actions)
        value["applied_actions"] = list(self.applied_actions)
        return value


@dataclass(frozen=True)
class SessionTurn:
    turn_id: int
    timestamp: float
    query: str
    query_risk_score: float
    query_risk_class: str
    retrieved_doc_ids: tuple[str, ...]
    retrieval_scores: tuple[float, ...]
    recommended_level: str
    applied_level: str


__all__ = [
    "AggregatedRisk",
    "PolicyDecision",
    "RISK_CLASSES",
    "RiskResult",
    "SessionTurn",
]
