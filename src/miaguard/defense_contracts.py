"""Online-only values passed through the defense pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True)
class OnlineRequest:
    request_id: str
    session_id: str
    query: str
    allowed_doc_ids: frozenset[str] | None = None

    def __post_init__(self) -> None:
        for name in ("request_id", "session_id", "query"):
            if not getattr(self, name).strip():
                raise ValueError(f"{name} must not be blank")
        if self.allowed_doc_ids is not None:
            if not isinstance(self.allowed_doc_ids, frozenset):
                raise ValueError("allowed_doc_ids must be a frozenset or None")
            if any(not isinstance(value, str) or not value.strip() for value in self.allowed_doc_ids):
                raise ValueError("allowed_doc_ids must contain non-blank strings")


@dataclass(frozen=True)
class RiskEstimate:
    x1: float | None
    x2: float | None
    fused_score: float | None
    risk_source: str
    status: str


@dataclass(frozen=True)
class Evidence:
    doc_id: str
    parent_doc_id: str
    text: str
    score: float
    kind: str = "raw"

    def __post_init__(self) -> None:
        if not self.doc_id.strip() or not self.parent_doc_id.strip():
            raise ValueError("Evidence document IDs must not be blank")
        if not isfinite(self.score):
            raise ValueError("Evidence score must be finite")
        if self.kind not in {"raw", "summary"}:
            raise ValueError("Evidence kind must be raw or summary")


__all__ = ["Evidence", "OnlineRequest", "RiskEstimate"]
