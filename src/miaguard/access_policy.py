from __future__ import annotations

from .risk_types import PolicyDecision


LEVEL_ACTIONS = {
    "L0": ("FULL_ACCESS",),
    "L1": ("AUDIT_ONLY",),
    "L2": ("REDUCE_TOP_K", "LIMIT_CONTEXT_DETAIL"),
    "L3": ("SANITIZE_CONTEXT", "ENABLE_RATE_LIMIT"),
    "L4": ("DENY_SENSITIVE_REQUEST", "FULL_AUDIT"),
}

ACCESS_ACTIONS = {
    "L0": "allow",
    "L1": "allow",
    "L2": "restrict_context",
    "L3": "summarize_context",
    "L4": "deny_sensitive_answer",
}


class LevelMapper:
    def __init__(
        self,
        thresholds: tuple[float, float, float, float],
        *,
        attack_detection_threshold: float | None = None,
    ) -> None:
        if len(thresholds) != 4 or not (
            0 <= thresholds[0] < thresholds[1] < thresholds[2] < thresholds[3] <= 1
        ):
            raise ValueError("L0-L4 thresholds must be strictly ordered in [0, 1]")
        if attack_detection_threshold is not None and not (
            0 <= attack_detection_threshold <= 1
        ):
            raise ValueError("attack detection threshold must be in [0, 1]")
        self.thresholds = thresholds
        self.attack_detection_threshold = attack_detection_threshold

    def level(self, score: float) -> str:
        if not 0 <= score <= 1:
            raise ValueError("Policy score must be between 0 and 1")
        t1, t2, t3, t4 = self.thresholds
        if score < t1:
            legacy_level = "L0"
        elif score < t2:
            legacy_level = "L1"
        elif score < t3:
            legacy_level = "L2"
        elif score < t4:
            legacy_level = "L3"
        else:
            legacy_level = "L4"
        if self.attack_detection_threshold is None:
            return legacy_level
        if score < self.attack_detection_threshold:
            return "L0" if score < t1 else "L1"
        if legacy_level in {"L0", "L1"}:
            return "L2"
        return legacy_level

    def decide(self, score: float, mode: str) -> PolicyDecision:
        if mode not in {"disabled", "observe", "enforce"}:
            raise ValueError(f"Unsupported defense mode: {mode}")
        recommended = self.level(score)
        applied = recommended if mode == "enforce" else "L0"
        return PolicyDecision(
            recommended_level=recommended,
            applied_level=applied,
            recommended_actions=LEVEL_ACTIONS[recommended],
            applied_actions=LEVEL_ACTIONS[applied],
            access_action=ACCESS_ACTIONS[applied],
            mode=mode,
        )


__all__ = ["ACCESS_ACTIONS", "LEVEL_ACTIONS", "LevelMapper"]
