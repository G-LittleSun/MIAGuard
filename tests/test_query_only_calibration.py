from __future__ import annotations

import pytest

from miaguard.frozen_risk_scorer import classify_source, error_action, resolve_risk
from miaguard.query_only_calibration import calibrate_query_only


def row(doc: str, attack: str, score: float, partition: str = "train") -> dict:
    return {"doc_id": doc, "attack_type": attack, "traffic_type": "benign" if attack == "benign" else "attack", "x1": score, "query_status": "ok", "partition": partition, "turn_index": 1, "head": "logprob"}


def sample() -> list[dict]:
    return [row("d1", "benign", .1), row("d2", "benign", .3),
            row("d1", "direct_rag_mia", .8), row("d2", "direct_rag_mia", .9),
            row("d1", "s2_mia", .8), row("d2", "s2_mia", .9),
            row("d1", "masked_mia", .8), row("d2", "masked_mia", .9),
            row("d1", "ia", .8), row("d2", "ia", .9)]


@pytest.mark.parametrize("partition", ["validation", "test"])
def test_rejects_non_train(partition: str) -> None:
    rows = sample()
    rows[0]["partition"] = partition
    with pytest.raises(ValueError, match="train"):
        calibrate_query_only(rows, caps=(.01,), bootstrap_replicates=20)


def test_no_trigger_candidate_and_ties() -> None:
    result = calibrate_query_only(sample(), caps=(.01,), bootstrap_replicates=20)
    assert any(item["name"] == "no_trigger" for item in result["candidates"])
    chosen = result["working_points"]["0.01"]
    assert chosen["threshold"] == .8
    assert chosen["attack_macro_recall"] == 1.0
    assert chosen["benign_fpr"] == 0.0


def test_rejects_missing_benign_and_invalid_scores() -> None:
    with pytest.raises(ValueError, match="benign"):
        calibrate_query_only([r for r in sample() if r["attack_type"] != "benign"], bootstrap_replicates=20)
    rows = sample()
    rows[0]["x1"] = float("nan")
    with pytest.raises(ValueError, match="x1"):
        calibrate_query_only(rows, bootstrap_replicates=20)


def test_only_first_two_ok_queries_and_document_counts() -> None:
    rows = sample() + [dict(row("d1", "benign", 1), turn_index=3), dict(row("d2", "benign", 1), query_status="error")]
    result = calibrate_query_only(rows, caps=(.05,), bootstrap_replicates=20)
    assert result["sample_counts"]["benign_queries"] == 2
    assert result["sample_counts"]["benign_documents"] == 2
    assert result["working_points"]["0.05"]["empirical_only"] is True


def test_failure_branches() -> None:
    assert classify_source(x1_ok=True, x2_ok=False) == "query_only"
    assert classify_source(x1_ok=False, x2_ok=True) == "error"
    assert classify_source(x1_ok=True, x2_ok=True) == "fusion"
    assert resolve_risk(.7, None, "ok", "missing", scorer=None).risk_source == "query_only"
    result = resolve_risk(.7, None, "ok", "error", scorer=None)
    assert (result.risk_source, result.status) == ("query_only", "session_error")
    assert resolve_risk(None, .8, "error", "ok", scorer=None).risk_source == "error"
    assert error_action("enforce") == "unavailable"
    assert error_action("observe") == "allow"
