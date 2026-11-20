from __future__ import annotations

import pytest

from miaguard.supervised_threshold import (
    ATTACK_TYPES,
    evaluate_locked_attack_threshold,
    select_document_balanced_threshold,
)


def _rows(
    doc_id: str,
    attack_type: str,
    scores: list[float],
    *,
    session_size: int = 5,
) -> list[dict]:
    traffic_type = "benign" if attack_type == "benign" else "attack"
    return [
        {
            "query_id": f"{doc_id}-{attack_type}-{index}",
            "doc_id": doc_id,
            "membership_label": 1,
            "traffic_type": traffic_type,
            "attack_type": attack_type,
            "session_key": f"{doc_id}-{attack_type}-{(index - 1) // session_size}",
            "turn_index": ((index - 1) % session_size) + 1,
            "total_risk_score": score,
        }
        for index, score in enumerate(scores, start=1)
    ]


def _feasible_records() -> list[dict]:
    records = []
    records.extend(_rows("benign-1", "benign", [0.1] * 5))
    for attack in ATTACK_TYPES:
        if attack == "ia":
            records.extend(_rows("ia-short", attack, [0.9] * 30))
            records.extend(_rows("ia-long", attack, [0.1] * 60))
        else:
            records.extend(_rows(f"{attack}-1", attack, [0.9] * 5))
    return records


def test_selection_uses_equal_document_weight_for_long_ia_sessions() -> None:
    result = select_document_balanced_threshold(
        _feasible_records(), max_benign_fpr=0.05
    )

    assert result["status"] == "selected"
    assert result["threshold"] == pytest.approx(0.9)
    recalls = result["selected_metrics"][
        "attack_document_balanced_query_recall"
    ]
    assert recalls["ia"] == pytest.approx(0.5)
    assert result["selected_metrics"]["minimum_attack_recall"] == pytest.approx(0.5)
    assert len(result["candidate_table"]) == 3


def test_benign_fpr_constraint_controls_candidate_selection() -> None:
    records = _feasible_records()
    records.extend(_rows("benign-high", "benign", [0.6] * 5))

    result = select_document_balanced_threshold(records, max_benign_fpr=0.0)

    assert result["status"] == "selected"
    assert result["threshold"] > 0.6
    assert result["selected_metrics"]["benign_query_fpr"] == 0.0


def test_selection_requires_all_four_attack_types() -> None:
    records = [row for row in _feasible_records() if row["attack_type"] != "ia"]

    with pytest.raises(ValueError, match="ia"):
        select_document_balanced_threshold(records)


def test_infeasible_data_does_not_fall_back_to_a_magic_threshold() -> None:
    records = _feasible_records()
    for row in records:
        if row["attack_type"] == "masked_mia":
            row["total_risk_score"] = 0.0
        if row["traffic_type"] == "benign":
            row["total_risk_score"] = 0.0

    result = select_document_balanced_threshold(records, max_benign_fpr=0.0)

    assert result["status"] == "infeasible"
    assert "threshold" not in result
    assert result["reason"] == "no_feasible_threshold_with_nonzero_recall_for_every_attack"


def test_locked_evaluation_keeps_threshold_and_bootstrap_is_reproducible() -> None:
    records = _feasible_records()

    first = evaluate_locked_attack_threshold(
        records,
        0.7,
        bootstrap_seed=17,
        bootstrap_replicates=50,
    )
    second = evaluate_locked_attack_threshold(
        records,
        0.7,
        bootstrap_seed=17,
        bootstrap_replicates=50,
    )

    assert first == second
    assert first["threshold"] == 0.7
    assert first["bootstrap"]["unit"] == "doc_id"
    assert first["bootstrap"]["replicates"] == 50
    assert first["attack_document_balanced_query_recall"]["ia"] == pytest.approx(0.5)
    assert first["attack_document_balanced_session_recall"]["ia"] == pytest.approx(0.5)
    assert first["attack_document_balanced_turn_3_detection_rate"]["ia"] == pytest.approx(0.5)
    assert first["attack_document_balanced_final_turn_detection_rate"]["ia"] == pytest.approx(0.5)
    assert first["first_detection_turn_histogram"]["1"] == 9
