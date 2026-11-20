from __future__ import annotations

from .risk_types import AggregatedRisk, RiskResult


class RiskAggregator:
    def __init__(
        self,
        *,
        method: str,
        query_weight: float,
        session_weight: float,
        query_critical_threshold: float,
        session_critical_threshold: float,
        window_size: int,
    ) -> None:
        if method not in {"fixed", "dynamic_window_coverage"}:
            raise ValueError(f"Unsupported aggregation method: {method}")
        if query_weight < 0 or session_weight < 0 or query_weight + session_weight <= 0:
            raise ValueError("Risk weights must be non-negative and not both zero")
        if not 0 <= query_critical_threshold <= 1:
            raise ValueError("query_critical_threshold must be between 0 and 1")
        if not 0 <= session_critical_threshold <= 1:
            raise ValueError("session_critical_threshold must be between 0 and 1")
        if window_size <= 0:
            raise ValueError("window_size must be positive")
        self.method = method
        self.query_weight = query_weight
        self.session_weight = session_weight
        self.query_critical_threshold = query_critical_threshold
        self.session_critical_threshold = session_critical_threshold
        self.window_size = window_size

    def aggregate(
        self,
        query_result: RiskResult,
        session_result: RiskResult,
        actual_window_size: int,
    ) -> AggregatedRisk:
        if query_result.stage != "query" or session_result.stage != "session":
            raise ValueError("Risk results were supplied to the wrong aggregation stage")
        if actual_window_size < 0:
            raise ValueError("actual_window_size must not be negative")
        coverage = (
            1.0
            if self.method == "fixed"
            else min(1.0, actual_window_size / self.window_size)
        )
        effective_session_weight = self.session_weight * coverage
        denominator = self.query_weight + effective_session_weight
        base = (
            (
                self.query_weight * query_result.score
                + effective_session_weight * session_result.score
            )
            / denominator
            if denominator > 0
            else 0.0
        )
        # Session evidence may amplify a risky query, but missing or weak session
        # evidence must not erase risk already visible in the current query.
        total = max(query_result.score, base)
        critical_sources = []
        if query_result.score >= self.query_critical_threshold:
            total = max(total, query_result.score)
            critical_sources.append("query")
        if session_result.score >= self.session_critical_threshold:
            total = max(total, session_result.score)
            critical_sources.append("session")
        return AggregatedRisk(
            query_risk=query_result.score,
            session_risk=session_result.score,
            total_risk=min(1.0, max(0.0, total)),
            query_weight=self.query_weight,
            session_weight=self.session_weight,
            window_coverage=coverage,
            method=self.method,
            critical_sources=tuple(critical_sources),
        )


__all__ = ["RiskAggregator"]
