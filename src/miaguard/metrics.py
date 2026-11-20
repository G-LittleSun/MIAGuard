from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Sequence

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)

from rag_mia_data.io_utils import read_jsonl, write_json_atomic


def extract_yes_no_unknown(value: str) -> str:
    text = value.casefold()
    if re.search(r"\b(yes|y|true)\b|(?<!\w)是(?!\w)", text):
        return "yes"
    if re.search(r"\b(no|n|false)\b|(?<!\w)(否|不是)(?!\w)", text):
        return "no"
    return "unknown"


def evaluate_scores(
    labels: Sequence[int],
    scores: Sequence[float],
    threshold: float,
    threshold_source: str = "fixed_config_no_shadow",
) -> dict[str, Any]:
    if len(labels) != len(scores) or not labels:
        raise ValueError("labels and scores must have the same non-zero length")
    y_true = np.asarray(labels, dtype=int)
    y_score = np.asarray(scores, dtype=float)
    if set(y_true.tolist()) != {0, 1}:
        raise ValueError("Evaluation requires both member and nonmember labels")
    y_pred = (y_score >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    fpr, tpr, _ = roc_curve(y_true, y_score)

    def tpr_at(max_fpr: float) -> float:
        eligible = tpr[fpr <= max_fpr]
        return float(np.max(eligible)) if len(eligible) else 0.0

    return {
        "sample_count": int(len(y_true)),
        "member_count": int(np.sum(y_true == 1)),
        "nonmember_count": int(np.sum(y_true == 0)),
        "threshold": float(threshold),
        "threshold_source": threshold_source,
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_true, y_score)),
        "tpr_at_fpr_0.001": tpr_at(0.001),
        "tpr_at_fpr_0.01": tpr_at(0.01),
        "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
        "member_score_mean": float(np.mean(y_score[y_true == 1])),
        "nonmember_score_mean": float(np.mean(y_score[y_true == 0])),
    }


def compute_metrics_file(results_path: Path, output_path: Path, threshold: float) -> dict[str, Any]:
    rows = list(read_jsonl(results_path))
    metrics = evaluate_scores(
        [int(row["membership_label"]) for row in rows],
        [float(row["membership_score"]) for row in rows],
        threshold,
    )
    write_json_atomic(output_path, metrics)
    return metrics


__all__ = ["compute_metrics_file", "evaluate_scores", "extract_yes_no_unknown"]
