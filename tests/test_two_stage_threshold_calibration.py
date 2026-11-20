import pytest

from miaguard.two_stage_threshold_calibration import (
    interleave_balanced_rows,
    select_balanced_detection_threshold,
)


def test_interleave_balanced_rows_alternates_membership() -> None:
    rows = [
        {"membership_label": 1, "id": "m1"},
        {"membership_label": 1, "id": "m2"},
        {"membership_label": 0, "id": "n1"},
        {"membership_label": 0, "id": "n2"},
    ]

    result = interleave_balanced_rows(rows)

    assert [row["id"] for row in result] == ["m1", "n1", "m2", "n2"]


def test_balanced_threshold_maximizes_worst_attack_rate_under_fpr_limit() -> None:
    records = []
    scores = {
        "direct_rag_mia": [0.8, 0.7],
        "s2_mia": [0.6, 0.5],
        "masked_mia": [0.9, 0.4],
        "ia": [0.7, 0.3],
    }
    for attack, values in scores.items():
        records.extend(
            {
                "traffic_type": "attack",
                "attack_type": attack,
                "total_risk_score": value,
            }
            for value in values
        )
    records.extend(
        {
            "traffic_type": "benign",
            "attack_type": "benign",
            "total_risk_score": value,
        }
        for value in [0.1, 0.2]
    )

    result = select_balanced_detection_threshold(records, max_benign_fpr=0.0)

    assert result["selected_threshold"] == pytest.approx(0.3)
    assert result["selected_metrics"]["min_attack_detection_rate"] == 1.0
    assert result["selected_metrics"]["benign_false_positive_rate"] == 0.0
