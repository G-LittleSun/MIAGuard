import pytest

from miaguard.access_policy import LevelMapper


@pytest.mark.parametrize(
    ("score", "level"),
    [(0.0, "L0"), (0.2, "L1"), (0.4, "L2"), (0.65, "L3"), (0.85, "L4")],
)
def test_l0_l4_threshold_boundaries(score: float, level: str) -> None:
    mapper = LevelMapper((0.2, 0.4, 0.65, 0.85))

    assert mapper.level(score) == level


def test_observe_recommends_policy_but_does_not_apply_it() -> None:
    mapper = LevelMapper((0.2, 0.4, 0.65, 0.85))

    decision = mapper.decide(0.9, "observe")

    assert decision.recommended_level == "L4"
    assert decision.applied_level == "L0"
    assert decision.access_action == "allow"


def test_enforce_applies_recommended_policy() -> None:
    mapper = LevelMapper((0.2, 0.4, 0.65, 0.85))

    decision = mapper.decide(0.7, "enforce")

    assert decision.recommended_level == "L3"
    assert decision.applied_level == "L3"
    assert decision.access_action == "summarize_context"


def test_attack_threshold_demotes_below_and_promotes_at_boundary() -> None:
    mapper = LevelMapper(
        (0.05, 0.10, 0.65, 0.85),
        attack_detection_threshold=0.50,
    )

    assert mapper.level(0.04) == "L0"
    assert mapper.level(0.40) == "L1"
    assert mapper.level(0.50) == "L2"
    assert mapper.level(0.70) == "L3"
    assert mapper.level(0.90) == "L4"


@pytest.mark.parametrize("threshold", (-0.01, 1.01))
def test_attack_threshold_must_be_in_unit_interval(threshold: float) -> None:
    with pytest.raises(ValueError, match="attack detection threshold"):
        LevelMapper(
            (0.05, 0.10, 0.65, 0.85),
            attack_detection_threshold=threshold,
        )
