from dataclasses import fields, replace
from math import nan

import pytest

from miaguard.progressive_judge import (
    EvidencePacket,
    LogprobScore,
    ProgressiveJudgeTrace,
    RubricScore,
    ScreeningResult,
)


def _trace(stage="query", status="ok", rubric=0.8, logprob=0.2):
    return ProgressiveJudgeTrace(
        stage=stage,
        screening=ScreeningResult("NO_ATTACK", (), (), False),
        evidence=EvidencePacket(()),
        rubric=RubricScore(rubric, 80, "HIGH", ("ia",), ("EV",)),
        logprob=LogprobScore(logprob, {"A": 0.8, "B": 0.2}, (0.1, 0.5, 0.9)),
        statuses={"overall": status},
        latencies_ms={"total": 12.5},
    )


def test_online_request_excludes_evaluation_labels():
    from miaguard.defense_contracts import OnlineRequest

    request = OnlineRequest("r1", "s1", "What happened?", frozenset({"d1"}))
    assert request.allowed_doc_ids == frozenset({"d1"})
    assert {field.name for field in fields(OnlineRequest)}.isdisjoint(
        {"intent_label", "membership_label", "attack_type", "target_doc_id"}
    )
    with pytest.raises(ValueError, match="request_id"):
        OnlineRequest("", "s1", "question")


def test_trace_adapter_uses_selected_head_and_preserves_evidence():
    from miaguard.online_judge_adapter import adapt_trace, trace_to_risk

    trace = _trace()
    logprob = trace_to_risk(trace, "logprob")
    rubric = trace_to_risk(trace, "rubric")

    assert logprob.score == 0.2
    assert rubric.score == 0.8
    assert logprob.stage == "query"
    assert logprob.suspected_attack_types == ("ia",)
    assert logprob.evidence_codes == ("EV",)
    assert logprob.latency_ms == 12.5
    adapted = adapt_trace(trace, "logprob")
    assert adapted.risk == logprob
    assert adapted.trace == trace
    assert adapted.trace_ref == adapt_trace(trace, "logprob").trace_ref


def test_insufficient_history_is_not_reported_as_valid_low_risk():
    from miaguard.online_judge_adapter import trace_to_risk

    result = trace_to_risk(_trace(stage="session", status="insufficient_history"), "logprob")
    assert result.stage == "session"
    assert result.status == "insufficient_history"
    assert result.risk_class == "NONE"


@pytest.mark.parametrize("head", ["unknown", "", "LOGPROB"])
def test_trace_adapter_rejects_unknown_head(head):
    from miaguard.online_judge_adapter import trace_to_risk

    with pytest.raises(ValueError, match="head"):
        trace_to_risk(_trace(), head)


@pytest.mark.parametrize("bad", [nan, -0.01, 1.01])
def test_trace_adapter_rejects_invalid_score(bad):
    from miaguard.online_judge_adapter import trace_to_risk

    with pytest.raises(ValueError, match="score"):
        trace_to_risk(_trace(logprob=bad), "logprob")


def test_trace_adapter_rejects_missing_status_or_invalid_latency():
    from miaguard.online_judge_adapter import trace_to_risk

    with pytest.raises(ValueError, match="status"):
        trace_to_risk(replace(_trace(), statuses={}), "logprob")
    with pytest.raises(ValueError, match="latency"):
        trace_to_risk(replace(_trace(), latencies_ms={"total": -1}), "logprob")
