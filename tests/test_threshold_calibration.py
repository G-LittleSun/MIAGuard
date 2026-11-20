import pytest

from miaguard.threshold_calibration import calibrate_threshold


def test_calibrate_threshold_finds_separating_boundary() -> None:
    result = calibrate_threshold(
        labels=[0, 0, 1, 1],
        scores=[0.1, 0.4, 0.6, 0.9],
    )

    assert result["threshold"] == pytest.approx(0.6)
    assert result["metrics"]["accuracy"] == 1.0
    assert result["selection_objective"] == "accuracy_then_f1_precision_threshold"


def test_calibrate_threshold_requires_both_membership_classes() -> None:
    with pytest.raises(ValueError, match="both member and nonmember"):
        calibrate_threshold(labels=[1, 1], scores=[0.2, 0.8])
