from copy import deepcopy

import pytest

from miaguard.judge_score_dataset import build_score_table


def _trace(
    *,
    rubric: float,
    logprob: float,
    status: str,
) -> dict:
    return {
        "rubric": {"score": rubric},
        "logprob": {"score": logprob},
        "statuses": {"overall": status},
        "screening": {
            "routing_decision": (
                "DEFER_INSUFFICIENT_HISTORY"
                if status == "insufficient_history"
                else "REVIEW"
            )
        },
    }


def _records() -> list[dict]:
    rows = []
    for doc_id, traffic_type, attack_type in (
        ("doc-benign", "benign", "benign"),
        ("doc-ia", "attack", "ia"),
    ):
        for turn in range(1, 6):
            available = turn >= 3
            rows.append(
                {
                    "query_id": f"{doc_id}-q{turn}",
                    "doc_id": doc_id,
                    "session_key": f"session-{doc_id}",
                    "turn_index": turn,
                    "session_length": 5,
                    "partition": "train",
                    "traffic_type": traffic_type,
                    "attack_type": attack_type,
                    "membership_label": 1,
                    "scoring_identity_sha256": "identity",
                    "query_trace": _trace(
                        rubric=0.1 * turn,
                        logprob=0.1 * turn,
                        status="ok",
                    ),
                    "session_trace": _trace(
                        rubric=0.1 * turn if available else 0.0,
                        logprob=0.1 * turn if available else 0.1,
                        status="ok" if available else "insufficient_history",
                    ),
                }
            )
    return rows


def test_build_score_table_expands_heads_and_excludes_default_session_scores() -> None:
    records = _records()

    table, audit = build_score_table(records)

    assert len(table) == len(records) * 2
    assert set(table["head"]) == {"rubric", "logprob"}
    early = table[table["turn_index"].isin([1, 2])]
    assert early["session_score_available"].eq(False).all()
    assert early["x2_observed"].isna().all()
    assert early["x2_raw"].notna().all()
    late = table[table["turn_index"].isin([3, 4, 5])]
    assert late["session_score_available"].eq(True).all()
    assert late["x2_observed"].notna().all()
    assert audit["default_session_scores_excluded"] == 8
    assert audit["unique_query_count"] == 10
    assert audit["unique_document_count"] == 2


def test_build_score_table_rejects_noncontiguous_session_turns() -> None:
    records = [row for row in _records() if row["query_id"] != "doc-ia-q2"]

    with pytest.raises(ValueError, match="contiguous"):
        build_score_table(records)


def test_build_score_table_rejects_session_mixing_documents() -> None:
    records = _records()
    records[-1]["session_key"] = "session-doc-benign"

    with pytest.raises(ValueError, match="mixes document"):
        build_score_table(records)


def test_build_score_table_rejects_mixed_identity() -> None:
    records = _records()
    records[-1]["scoring_identity_sha256"] = "other"

    with pytest.raises(ValueError, match="scoring identity"):
        build_score_table(records)


def test_build_score_table_rejects_invalid_score() -> None:
    records = deepcopy(_records())
    records[0]["query_trace"]["logprob"]["score"] = float("nan")

    with pytest.raises(ValueError, match="score"):
        build_score_table(records)
