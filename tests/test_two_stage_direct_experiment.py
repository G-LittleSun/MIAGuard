import json
from pathlib import Path

import pytest

from miaguard.two_stage_direct_experiment import binary_detection_metrics


def test_binary_detection_metrics_reports_security_metrics() -> None:
    metrics = binary_detection_metrics(
        [1, 1, 0, 0],
        [0.9, 0.8, 0.2, 0.1],
        0.4,
    )

    assert metrics["accuracy"] == 1.0
    assert metrics["f1"] == 1.0
    assert metrics["auroc"] == 1.0
    assert metrics["auprc"] == 1.0
    assert metrics["false_positive_rate"] == 0.0
    assert metrics["confusion_matrix"] == {"tn": 2, "fp": 0, "fn": 0, "tp": 2}


def test_binary_detection_metrics_requires_both_classes() -> None:
    with pytest.raises(ValueError, match="attack and benign"):
        binary_detection_metrics([1, 1], [0.9, 0.8], 0.4)


def test_checked_in_online_schema_has_no_ground_truth_field() -> None:
    root = Path(__file__).resolve().parents[1]
    schema = json.loads(
        (root / "schemas/two_stage_risk_event.schema.json").read_text(encoding="utf-8")
    )

    assert "ground_truth" not in schema["properties"]
    assert schema["additionalProperties"] is False
