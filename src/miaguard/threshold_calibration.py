from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import numpy as np
from sklearn.metrics import accuracy_score, f1_score, precision_score

from .metrics import evaluate_scores


def calibrate_threshold(
    labels: Sequence[int],
    scores: Sequence[float],
) -> dict[str, Any]:
    if len(labels) != len(scores) or not labels:
        raise ValueError("labels and scores must have the same non-zero length")
    y_true = np.asarray(labels, dtype=int)
    y_score = np.asarray(scores, dtype=float)
    if set(y_true.tolist()) != {0, 1}:
        raise ValueError("Threshold calibration requires both member and nonmember labels")

    candidates = np.unique(
        np.append(y_score, np.nextafter(float(np.max(y_score)), np.inf))
    )
    ranked: list[tuple[float, float, float, float]] = []
    for threshold in candidates:
        prediction = (y_score >= threshold).astype(int)
        ranked.append(
            (
                float(accuracy_score(y_true, prediction)),
                float(f1_score(y_true, prediction, zero_division=0)),
                float(precision_score(y_true, prediction, zero_division=0)),
                float(threshold),
            )
        )
    threshold = max(ranked)[3]
    metrics = evaluate_scores(y_true.tolist(), y_score.tolist(), threshold)
    metrics["threshold_source"] = "calibration_split_optimized_accuracy"
    return {
        "threshold": threshold,
        "selection_objective": "accuracy_then_f1_precision_threshold",
        "metrics": metrics,
    }


__all__ = ["calibrate_threshold"]
