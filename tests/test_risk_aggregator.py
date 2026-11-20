import pytest

from miaguard.risk_aggregator import RiskAggregator
from miaguard.risk_types import RiskResult


def _risk(stage: str, score: float) -> RiskResult:
    return RiskResult(
        stage=stage,
        score=score,
        risk_class="STRONG" if score >= 0.7 else "WEAK",
        scoring_method="test",
    )


def test_dynamic_aggregation_uses_window_coverage() -> None:
    aggregator = RiskAggregator(
        method="dynamic_window_coverage",
        query_weight=0.4,
        session_weight=0.6,
        query_critical_threshold=0.9,
        session_critical_threshold=0.9,
        window_size=8,
    )

    result = aggregator.aggregate(_risk("query", 0.8), _risk("session", 0.2), 4)

    assert result.window_coverage == 0.5
    assert result.total_risk == 0.8


def test_session_evidence_can_raise_but_not_lower_query_risk() -> None:
    aggregator = RiskAggregator(
        method="fixed",
        query_weight=0.4,
        session_weight=0.6,
        query_critical_threshold=0.85,
        session_critical_threshold=0.85,
        window_size=8,
    )

    raised = aggregator.aggregate(_risk("query", 0.2), _risk("session", 0.8), 8)
    preserved = aggregator.aggregate(_risk("query", 0.45), _risk("session", 0.0), 8)

    assert raised.total_risk == pytest.approx(0.56)
    assert preserved.total_risk == 0.45


def test_critical_query_risk_is_not_diluted_by_session_score() -> None:
    aggregator = RiskAggregator(
        method="fixed",
        query_weight=0.4,
        session_weight=0.6,
        query_critical_threshold=0.85,
        session_critical_threshold=0.85,
        window_size=8,
    )

    result = aggregator.aggregate(_risk("query", 0.95), _risk("session", 0.1), 8)

    assert result.total_risk == 0.95
    assert result.critical_sources == ("query",)


def test_aggregated_risk_is_monotonic_when_query_risk_increases() -> None:
    aggregator = RiskAggregator(
        method="fixed",
        query_weight=0.5,
        session_weight=0.5,
        query_critical_threshold=1.0,
        session_critical_threshold=1.0,
        window_size=8,
    )

    low = aggregator.aggregate(_risk("query", 0.2), _risk("session", 0.4), 8)
    high = aggregator.aggregate(_risk("query", 0.6), _risk("session", 0.4), 8)

    assert high.total_risk >= low.total_risk
