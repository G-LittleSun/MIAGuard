from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, average_precision_score, brier_score_loss, f1_score, precision_score, recall_score, roc_auc_score

from rag_mia_data.io_utils import write_json_atomic
from .judge_score_dataset import ATTACK_TYPES
from .judge_score_fusion import compute_training_weights


def _rows(table: pd.DataFrame, partition: str, head: str) -> pd.DataFrame:
    rows = table.loc[(table["head"] == head) & table["session_score_available"].astype(bool)].copy()
    if rows.empty or set(rows["partition"]) != {partition}:
        raise ValueError(f"Expected available {head} rows from {partition}")
    return rows.reset_index(drop=True)


def freeze_logistic_l2(
    table: pd.DataFrame,
    thresholds: Mapping[str, Mapping[str, Any]],
    output_path: Path,
    *,
    head: str = "logprob",
) -> dict[str, Any]:
    if output_path.exists():
        raise FileExistsError(f"Frozen fusion output already exists: {output_path}")
    rows = _rows(table, "train", head)
    if set(thresholds) != {"0.01", "0.05"}:
        raise ValueError("Frozen fusion requires 0.01 and 0.05 thresholds")
    model = LogisticRegression(penalty="l2", C=1.0, solver="lbfgs", max_iter=1000, random_state=20260918)
    features = rows[["x1", "x2_observed"]].to_numpy(float)
    model.fit(features, rows["label"].to_numpy(int), sample_weight=compute_training_weights(rows))
    result = {
        "schema_version": 1,
        "model": "logistic_l2",
        "head": head,
        "feature_order": ["x1", "x2_observed"],
        "coefficient": [float(value) for value in model.coef_[0]],
        "intercept": float(model.intercept_[0]),
        "train_rows": int(len(rows)),
        "train_documents": int(rows["doc_id"].nunique()),
        "thresholds": {cap: {"threshold": float(values["threshold"])} for cap, values in thresholds.items()},
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    write_json_atomic(output_path, result)
    return result


def evaluate_frozen_fusion(
    table: pd.DataFrame, frozen: Mapping[str, Any], *, partition: str = "validation"
) -> dict[str, Any]:
    if partition not in {"validation", "test"}:
        raise ValueError("Frozen evaluation supports validation or test only")
    if frozen.get("model") != "logistic_l2" or frozen.get("feature_order") != ["x1", "x2_observed"]:
        raise ValueError("Unsupported frozen fusion artifact")
    head = str(frozen.get("head", "logprob"))
    rows = _rows(table, partition, head)
    coefficients = np.asarray(frozen["coefficient"], dtype=float)
    intercept = float(frozen["intercept"])
    logits = rows[["x1", "x2_observed"]].to_numpy(float) @ coefficients + intercept
    scores = 1.0 / (1.0 + np.exp(-logits))
    labels = rows["label"].to_numpy(int)
    result: dict[str, Any] = {
        "schema_version": 1,
        "partition": partition,
        "rows": int(len(rows)),
        "documents": int(rows["doc_id"].nunique()),
        "probability_metrics": {"auroc": float(roc_auc_score(labels, scores)), "pr_auc": float(average_precision_score(labels, scores)), "brier": float(brier_score_loss(labels, scores))},
        "operating_points": {},
    }
    for cap, details in frozen["thresholds"].items():
        threshold = float(details["threshold"])
        predicted = scores >= threshold
        benign = labels == 0
        recalls = {attack: float(predicted[rows["attack_type"].to_numpy(str) == attack].mean()) for attack in ATTACK_TYPES}
        result["operating_points"][cap] = {
            "threshold": threshold,
            "benign_fpr": float(predicted[benign].mean()),
            "accuracy": float(accuracy_score(labels, predicted)),
            "precision": float(precision_score(labels, predicted, zero_division=0)),
            "recall": float(recall_score(labels, predicted, zero_division=0)),
            "f1": float(f1_score(labels, predicted, zero_division=0)),
            "attack_recalls": recalls,
            "attack_macro_recall": float(np.mean(list(recalls.values()))),
            "weakest_attack_recall": float(min(recalls.values())),
        }
    return result
