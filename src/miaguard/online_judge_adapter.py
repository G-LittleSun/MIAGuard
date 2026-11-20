"""Translate v3 Judge traces without losing their audit identity."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from math import isfinite

from .progressive_judge import ProgressiveJudgeTrace
from .risk_types import RiskResult


@dataclass(frozen=True)
class AdaptedTrace:
    risk: RiskResult
    trace_ref: str
    trace: ProgressiveJudgeTrace


def trace_to_risk(trace: ProgressiveJudgeTrace, head: str) -> RiskResult:
    if head not in {"logprob", "rubric"}:
        raise ValueError(f"Unsupported Judge head: {head}")
    status = trace.statuses.get("overall")
    if not isinstance(status, str) or not status.strip():
        raise ValueError("Judge trace must contain an overall status")
    score = float(getattr(trace, head).score)
    if not isfinite(score) or not 0.0 <= score <= 1.0:
        raise ValueError("Judge score must be finite and within [0, 1]")
    latency_ms = float(trace.latencies_ms.get("total", 0.0))
    if not isfinite(latency_ms) or latency_ms < 0:
        raise ValueError("Judge latency must be finite and non-negative")
    if status != "ok":
        # RiskResult requires a numeric score. Consumers must check status before
        # using this placeholder for fusion or policy decisions.
        score = 0.0
    risk_class = "NONE" if score < 0.5 else "WEAK" if score < 0.85 else "STRONG"
    return RiskResult(
        stage=trace.stage,
        score=score,
        risk_class=risk_class,
        scoring_method=f"progressive_judge_v3_{head}",
        suspected_attack_types=trace.rubric.suspected_attack_types,
        evidence_codes=trace.rubric.evidence_codes,
        status=status,
        latency_ms=latency_ms,
    )


def adapt_trace(trace: ProgressiveJudgeTrace, head: str) -> AdaptedTrace:
    risk = trace_to_risk(trace, head)
    encoded = json.dumps(asdict(trace), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    trace_ref = "sha256:" + hashlib.sha256(encoded.encode("utf-8")).hexdigest()
    return AdaptedTrace(risk=risk, trace_ref=trace_ref, trace=trace)


__all__ = ["AdaptedTrace", "adapt_trace", "trace_to_risk"]
