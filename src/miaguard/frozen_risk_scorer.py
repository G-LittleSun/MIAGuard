"""Read-only application of a verified v3 logistic fusion artifact."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from math import exp, isfinite
from pathlib import Path

from miaguard.defense_contracts import RiskEstimate


@dataclass(frozen=True)
class FrozenRiskScorer:
    head: str
    sha256: str
    coefficient: tuple[float, float]
    intercept: float
    thresholds: dict[str, float]

    @classmethod
    def from_file(
        cls, path: str | Path, expected_head: str, expected_sha256: str
    ) -> "FrozenRiskScorer":
        raw = Path(path).read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        if digest != expected_sha256:
            raise ValueError("Frozen model SHA256 does not match the expected artifact")
        artifact = json.loads(raw)
        if not isinstance(artifact, dict) or artifact.get("schema_version") != 1:
            raise ValueError("Unsupported frozen model schema_version")
        if artifact.get("model") != "logistic_l2":
            raise ValueError("Unsupported frozen model type")
        head = artifact.get("head")
        if expected_head not in {"logprob", "rubric"} or head != expected_head:
            raise ValueError("Frozen model head does not match the requested head")
        if artifact.get("feature_order") != ["x1", "x2_observed"]:
            raise ValueError("Frozen model feature_order must be [x1, x2_observed]")
        coefficient = artifact.get("coefficient")
        if not isinstance(coefficient, list) or len(coefficient) != 2:
            raise ValueError("Frozen model coefficient must have two values")
        try:
            weights = tuple(float(value) for value in coefficient)
        except (TypeError, ValueError) as exc:
            raise ValueError("Frozen model coefficient must be numeric") from exc
        if not all(isfinite(value) for value in weights):
            raise ValueError("Frozen model coefficient must be finite")
        try:
            intercept = float(artifact["intercept"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("Frozen model intercept must be numeric") from exc
        if not isfinite(intercept):
            raise ValueError("Frozen model intercept must be finite")
        raw_thresholds = artifact.get("thresholds")
        if not isinstance(raw_thresholds, dict) or set(raw_thresholds) != {"0.01", "0.05"}:
            raise ValueError("Frozen model thresholds must contain 0.01 and 0.05")
        thresholds: dict[str, float] = {}
        for cap, entry in raw_thresholds.items():
            try:
                value = float(entry["threshold"])
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError(f"Frozen model thresholds[{cap}] is invalid") from exc
            if not isfinite(value) or not 0.0 <= value <= 1.0:
                raise ValueError(f"Frozen model thresholds[{cap}] must be in [0, 1]")
            thresholds[cap] = value
        return cls(
            head=head,
            sha256=digest,
            coefficient=(weights[0], weights[1]),
            intercept=intercept,
            thresholds=thresholds,
        )

    def score(self, x1: float, x2: float | None) -> float:
        for name, value in (("x1", x1), ("x2", x2)):
            if value is None or not isinstance(value, (int, float)) or not isfinite(value) or not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be finite and within [0, 1]")
        assert x2 is not None  # Checked above; keeps the type narrow for arithmetic.
        logit = self.coefficient[0] * x1 + self.coefficient[1] * x2 + self.intercept
        if logit >= 0:
            return 1.0 / (1.0 + exp(-logit))
        scaled = exp(logit)
        return scaled / (1.0 + scaled)


def classify_source(*, x1_ok: bool, x2_ok: bool) -> str:
    """Choose the only score source available at decision time."""
    if not x1_ok:
        return "error"
    return "fusion" if x2_ok else "query_only"


def error_action(mode: str) -> str:
    if mode == "enforce":
        return "unavailable"
    if mode == "observe":
        return "allow"
    raise ValueError("mode must be observe or enforce")


def resolve_risk(
    x1: float | None,
    x2: float | None,
    query_status: str,
    session_status: str,
    scorer: FrozenRiskScorer | None,
) -> RiskEstimate:
    """Treat failed stages as unavailable, never as a numeric low-risk score."""
    x1_ok = query_status == "ok" and x1 is not None
    x2_ok = session_status == "ok" and x2 is not None
    source = classify_source(x1_ok=x1_ok, x2_ok=x2_ok)
    if source == "error":
        return RiskEstimate(None, None, None, source, "query_error")
    assert x1 is not None
    if not isfinite(x1) or not 0.0 <= x1 <= 1.0:
        raise ValueError("x1 must be finite and within [0, 1]")
    if source == "query_only":
        status = "session_error" if session_status not in {"ok", "missing"} else "ok"
        return RiskEstimate(x1, None, None, source, status)
    if scorer is None:
        raise ValueError("Frozen scorer is required for fusion")
    assert x2 is not None
    return RiskEstimate(x1, x2, scorer.score(x1, x2), source, "ok")


__all__ = ["FrozenRiskScorer", "classify_source", "error_action", "resolve_risk"]
