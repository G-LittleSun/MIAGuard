from __future__ import annotations

from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any
import warnings

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    precision_recall_curve,
    roc_auc_score,
    roc_curve,
)
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.neural_network import MLPClassifier

from .judge_score_dataset import ATTACK_TYPES


FPR_CAPS = (0.01, 0.05)
MODEL_NAMES = (
    "x1_only",
    "x2_only",
    "legacy_0.4x1_0.6x2",
    "logistic_l2",
    "logistic_l2_interaction",
    "mlp_2_8_1",
)
_MODEL_LABELS = {
    "x1_only": "x1 only",
    "x2_only": "x2 only",
    "legacy_0.4x1_0.6x2": "Legacy 0.4x1 + 0.6x2",
    "logistic_l2": "L2 logistic",
    "logistic_l2_interaction": "L2 logistic + interaction",
    "mlp_2_8_1": "MLP 2→8→1",
}
_MODEL_COLORS = {
    "x1_only": "#0072B2",
    "x2_only": "#56B4E9",
    "legacy_0.4x1_0.6x2": "#999999",
    "logistic_l2": "#009E73",
    "logistic_l2_interaction": "#CC79A7",
    "mlp_2_8_1": "#D55E00",
}
_PLOT_STYLE = {
    "font.size": 8,
    "axes.labelsize": 8,
    "axes.titlesize": 9,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.color": "#D1D5DB",
    "grid.linewidth": 0.45,
    "grid.alpha": 0.7,
    "legend.fontsize": 6.4,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
    "savefig.dpi": 300,
}


def _session_available_rows(table: pd.DataFrame, head: str) -> pd.DataFrame:
    required = {
        "query_id",
        "doc_id",
        "session_key",
        "attack_type",
        "label",
        "head",
        "x1",
        "x2_observed",
        "session_score_available",
    }
    missing = required.difference(table.columns)
    if missing:
        raise ValueError(f"Fusion table is missing columns: {sorted(missing)}")
    rows = table.loc[
        (table["head"] == head) & table["session_score_available"].astype(bool)
    ].copy()
    if rows.empty:
        raise ValueError(f"No available session scores for head: {head}")
    if rows["x2_observed"].isna().any():
        raise ValueError("Available session score rows contain missing x2")
    if not rows["label"].isin((0, 1)).all():
        raise ValueError("Fusion labels must be binary")
    if rows["doc_id"].nunique() < 2:
        raise ValueError("Fusion requires at least two documents")
    return rows.reset_index(drop=True)


def build_grouped_folds(
    table: pd.DataFrame,
    *,
    n_splits: int,
    seed: int,
) -> list[tuple[np.ndarray, np.ndarray]]:
    if n_splits < 2:
        raise ValueError("n_splits must be at least two")
    if table["doc_id"].nunique() < n_splits:
        raise ValueError("n_splits exceeds the number of documents")
    splitter = StratifiedGroupKFold(
        n_splits=n_splits,
        shuffle=True,
        random_state=seed,
    )
    folds = list(
        splitter.split(
            table,
            table["label"].to_numpy(int),
            groups=table["doc_id"].to_numpy(str),
        )
    )
    for train_index, test_index in folds:
        train_docs = set(table.iloc[train_index]["doc_id"])
        test_docs = set(table.iloc[test_index]["doc_id"])
        if not train_docs.isdisjoint(test_docs):
            raise RuntimeError("Document leakage detected in grouped folds")
    return folds


def compute_training_weights(table: pd.DataFrame) -> np.ndarray:
    """Give benign half the loss mass and each attack type one eighth.

    Within every traffic stratum, documents share the stratum mass equally and
    records within a document split that document mass.  The result sums to one
    and is computed fold-locally by the caller.
    """

    required = {"doc_id", "attack_type", "label"}
    missing = required.difference(table.columns)
    if missing:
        raise ValueError(f"Weight table is missing columns: {sorted(missing)}")
    target_mass = {"benign": 0.5, **{attack: 0.125 for attack in ATTACK_TYPES}}
    unknown = set(table["attack_type"].unique()).difference(target_mass)
    if unknown:
        raise ValueError(f"Unsupported traffic strata: {sorted(unknown)}")
    present = set(table["attack_type"].unique())
    if set(target_mass).difference(present):
        raise ValueError("Each fold must contain benign and all attack types")

    weights = np.zeros(len(table), dtype=float)
    for attack_type, mass in target_mass.items():
        mask = table["attack_type"].to_numpy(str) == attack_type
        stratum = table.loc[mask]
        documents = list(stratum["doc_id"].unique())
        for document in documents:
            local_index = np.flatnonzero(
                mask & (table["doc_id"].to_numpy(str) == str(document))
            )
            weights[local_index] = mass / len(documents) / len(local_index)
    if not np.isclose(weights.sum(), 1.0):
        raise RuntimeError("Training weights do not sum to one")
    return weights


def _attack_recalls(rows: pd.DataFrame, predictions: np.ndarray) -> dict[str, float]:
    recalls: dict[str, float] = {}
    for attack_type in ATTACK_TYPES:
        mask = rows["attack_type"].to_numpy(str) == attack_type
        if not mask.any():
            continue
        recalls[attack_type] = float(predictions[mask].mean())
    return recalls


def select_threshold_at_fpr(
    rows: pd.DataFrame,
    *,
    fpr_cap: float,
) -> dict[str, Any]:
    if not 0.0 <= fpr_cap <= 1.0:
        raise ValueError("fpr_cap must be in [0, 1]")
    required = {"label", "attack_type", "score"}
    missing = required.difference(rows.columns)
    if missing:
        raise ValueError(f"Threshold rows are missing columns: {sorted(missing)}")
    if rows.empty or rows["score"].isna().any():
        raise ValueError("Threshold selection requires finite scores")
    scores = rows["score"].to_numpy(float)
    if not np.isfinite(scores).all():
        raise ValueError("Threshold selection requires finite scores")
    candidates = np.unique(np.r_[scores, np.nextafter(scores.max(), np.inf)])
    label = rows["label"].to_numpy(int)
    benign = label == 0
    if not benign.any() or not (~benign).any():
        raise ValueError("Threshold selection requires benign and attack rows")

    best: dict[str, Any] | None = None
    for threshold in candidates:
        predicted = scores >= threshold
        benign_fpr = float(predicted[benign].mean())
        if benign_fpr > fpr_cap + 1e-12:
            continue
        recalls = _attack_recalls(rows, predicted)
        if set(recalls) != set(ATTACK_TYPES):
            raise ValueError("Threshold selection requires all attack types")
        macro = float(np.mean(list(recalls.values())))
        minimum = float(min(recalls.values()))
        candidate = {
            "threshold": float(threshold),
            "benign_fpr": benign_fpr,
            "attack_recalls": recalls,
            "attack_macro_recall": macro,
            "weakest_attack_recall": minimum,
        }
        if best is None or (
            macro,
            minimum,
            -benign_fpr,
            -threshold,
        ) > (
            best["attack_macro_recall"],
            best["weakest_attack_recall"],
            -best["benign_fpr"],
            -best["threshold"],
        ):
            best = candidate
    if best is None:
        raise RuntimeError("No threshold satisfied the FPR constraint")
    return best


def _features(rows: pd.DataFrame, model: str) -> np.ndarray:
    x1 = rows["x1"].to_numpy(float)
    x2 = rows["x2_observed"].to_numpy(float)
    if model == "x1_only":
        return x1[:, None]
    if model == "x2_only":
        return x2[:, None]
    if model == "logistic_l2":
        return np.column_stack((x1, x2))
    if model == "logistic_l2_interaction":
        return np.column_stack((x1, x2, x1 * x2))
    if model == "mlp_2_8_1":
        return np.column_stack((x1, x2))
    raise ValueError(f"No learned features for model: {model}")


def _fit_predict_model(
    train_rows: pd.DataFrame,
    test_rows: pd.DataFrame,
    *,
    model: str,
    random_state: int,
) -> np.ndarray:
    if model == "legacy_0.4x1_0.6x2":
        return 0.4 * test_rows["x1"].to_numpy(float) + 0.6 * test_rows[
            "x2_observed"
        ].to_numpy(float)
    weights = compute_training_weights(train_rows)
    target = train_rows["label"].to_numpy(int)
    if model == "mlp_2_8_1":
        estimator: Any = MLPClassifier(
            hidden_layer_sizes=(8,),
            activation="relu",
            solver="lbfgs",
            alpha=0.01,
            max_iter=1000,
            random_state=random_state,
        )
    else:
        estimator = LogisticRegression(
            penalty="l2",
            C=1.0,
            solver="lbfgs",
            max_iter=1000,
            random_state=random_state,
        )
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=ConvergenceWarning)
        estimator.fit(_features(train_rows, model), target, sample_weight=weights)
    return estimator.predict_proba(_features(test_rows, model))[:, 1]


def run_head_grouped_oof(
    table: pd.DataFrame,
    *,
    head: str,
    n_splits: int = 5,
    seed: int = 20260903,
    models: Sequence[str] = MODEL_NAMES,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    unknown = set(models).difference(MODEL_NAMES)
    if unknown:
        raise ValueError(f"Unsupported fusion models: {sorted(unknown)}")
    rows = _session_available_rows(table, head)
    folds = build_grouped_folds(rows, n_splits=n_splits, seed=seed)
    outputs: list[pd.DataFrame] = []
    fold_manifest: list[dict[str, Any]] = []
    for fold_number, (train_index, test_index) in enumerate(folds):
        train_rows = rows.iloc[train_index].reset_index(drop=True)
        test_rows = rows.iloc[test_index].reset_index(drop=True)
        fold_manifest.append(
            {
                "fold": fold_number,
                "train_documents": sorted(train_rows["doc_id"].unique().tolist()),
                "test_documents": sorted(test_rows["doc_id"].unique().tolist()),
            }
        )
        for model in models:
            predicted = _fit_predict_model(
                train_rows,
                test_rows,
                model=model,
                random_state=seed + fold_number,
            )
            output = test_rows[
                [
                    "query_id",
                    "doc_id",
                    "session_key",
                    "attack_type",
                    "label",
                    "x1",
                    "x2_observed",
                ]
            ].copy()
            output["head"] = head
            output["model"] = model
            output["fold"] = fold_number
            output["score"] = predicted
            outputs.append(output)
    predictions = pd.concat(outputs, ignore_index=True)
    if predictions.groupby(["model", "query_id"], sort=False).size().ne(1).any():
        raise RuntimeError("OOF predictions are not one-to-one with query IDs")
    metadata = {
        "head": head,
        "cohort": "session_score_available",
        "eligible_rows": int(len(rows)),
        "eligible_documents": int(rows["doc_id"].nunique()),
        "folds": fold_manifest,
    }
    return predictions, metadata


def _percentile_interval(values: Iterable[float]) -> dict[str, float] | None:
    array = np.asarray(list(values), dtype=float)
    array = array[np.isfinite(array)]
    if not len(array):
        return None
    return {
        "p025": float(np.quantile(array, 0.025)),
        "p50": float(np.quantile(array, 0.50)),
        "p975": float(np.quantile(array, 0.975)),
    }


def _basic_metrics(rows: pd.DataFrame) -> dict[str, float]:
    target = rows["label"].to_numpy(int)
    score = rows["score"].to_numpy(float)
    if len(np.unique(target)) != 2:
        raise ValueError("OOF metrics require benign and attack rows")
    return {
        "auroc": float(roc_auc_score(target, score)),
        "pr_auc": float(average_precision_score(target, score)),
        "brier": float(brier_score_loss(target, score)),
    }


def _bootstrap_summary(
    rows: pd.DataFrame,
    *,
    threshold: float,
    replicates: int,
    seed: int,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "unit": "doc_id",
        "replicates": replicates,
        "seed": seed,
        "threshold_fixed_from_full_oof": float(threshold),
    }
    if replicates <= 0:
        result["auroc"] = None
        result["primary_threshold_metrics"] = None
        return result
    documents = np.asarray(sorted(rows["doc_id"].unique()), dtype=object)
    by_document = {
        document: rows.loc[rows["doc_id"] == document] for document in documents
    }
    rng = np.random.default_rng(seed)
    aurocs: list[float] = []
    macro_recalls: list[float] = []
    weakest_recalls: list[float] = []
    fprs: list[float] = []
    for _ in range(replicates):
        sampled = rng.choice(documents, size=len(documents), replace=True)
        draw = pd.concat([by_document[document] for document in sampled], ignore_index=True)
        metrics = _basic_metrics(draw)
        predicted = draw["score"].to_numpy(float) >= threshold
        benign = draw["label"].to_numpy(int) == 0
        recalls = _attack_recalls(draw, predicted)
        aurocs.append(metrics["auroc"])
        fprs.append(float(predicted[benign].mean()))
        macro_recalls.append(float(np.mean(list(recalls.values()))))
        weakest_recalls.append(float(min(recalls.values())))
    result["auroc"] = _percentile_interval(aurocs)
    result["primary_threshold_metrics"] = {
        "benign_fpr": _percentile_interval(fprs),
        "attack_macro_recall": _percentile_interval(macro_recalls),
        "weakest_attack_recall": _percentile_interval(weakest_recalls),
    }
    return result


def summarize_oof_predictions(
    predictions: pd.DataFrame,
    *,
    fpr_caps: Sequence[float] = FPR_CAPS,
    bootstrap_replicates: int = 1000,
    bootstrap_seed: int = 20260903,
) -> dict[str, Any]:
    required = {"head", "model", "doc_id", "attack_type", "label", "score"}
    missing = required.difference(predictions.columns)
    if missing:
        raise ValueError(f"OOF predictions are missing columns: {sorted(missing)}")
    report: dict[str, Any] = {
        "schema_version": 1,
        "cohort": "session_score_available",
        "fpr_caps": [float(cap) for cap in fpr_caps],
        "bootstrap": {
            "unit": "doc_id",
            "replicates": bootstrap_replicates,
            "seed": bootstrap_seed,
            "threshold_policy": "fixed_from_full_oof",
        },
        "heads": {},
    }
    for head in sorted(predictions["head"].unique()):
        head_rows = predictions.loc[predictions["head"] == head]
        models: dict[str, Any] = {}
        for model in MODEL_NAMES:
            rows = head_rows.loc[head_rows["model"] == model].copy()
            if rows.empty:
                continue
            thresholds = {
                f"{cap:.2f}": select_threshold_at_fpr(rows, fpr_cap=float(cap))
                for cap in fpr_caps
            }
            primary = thresholds.get("0.05") or next(iter(thresholds.values()))
            models[model] = {
                "label": _MODEL_LABELS[model],
                "rows": int(len(rows)),
                "documents": int(rows["doc_id"].nunique()),
                "metrics": _basic_metrics(rows),
                "thresholds": thresholds,
                "bootstrap": _bootstrap_summary(
                    rows,
                    threshold=float(primary["threshold"]),
                    replicates=bootstrap_replicates,
                    seed=bootstrap_seed,
                ),
            }
        report["heads"][head] = {"models": models}
    return report


def _save_figure(figure: Any, output_dir: Path, key: str) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    png = output_dir / f"{key}.png"
    pdf = output_dir / f"{key}.pdf"
    figure.savefig(png, bbox_inches="tight", facecolor="white")
    figure.savefig(
        pdf,
        bbox_inches="tight",
        facecolor="white",
        metadata={"Creator": "MIAGuard", "Subject": "Judge score fusion"},
    )
    plt.close(figure)
    return {
        "png": str(png.resolve()),
        "pdf": str(pdf.resolve()),
        "dpi": 300,
        "style": "publication_v2",
        "label_source": "frozen_ground_truth",
    }


def _roc_figure(predictions: pd.DataFrame) -> Any:
    heads = sorted(predictions["head"].unique())
    figure, axes = plt.subplots(1, len(heads), figsize=(3.55 * len(heads), 3.0), constrained_layout=True)
    axes_array = np.atleast_1d(axes)
    for axis, head in zip(axes_array, heads):
        rows = predictions.loc[predictions["head"] == head]
        for model in MODEL_NAMES:
            group = rows.loc[rows["model"] == model]
            if group.empty:
                continue
            fpr, tpr, _ = roc_curve(group["label"], group["score"])
            auc = roc_auc_score(group["label"], group["score"])
            axis.plot(
                fpr,
                tpr,
                label=f"{_MODEL_LABELS[model]} ({auc:.3f})",
                color=_MODEL_COLORS[model],
                linewidth=1.15,
            )
        axis.plot([0, 1], [0, 1], color="#6B7280", linestyle="--", linewidth=0.7)
        axis.set(
            title=f"{head}: ROC (OOF)",
            xlabel="Benign false-positive rate",
            ylabel="Attack true-positive rate",
            xlim=(0, 1),
            ylim=(0, 1),
        )
        axis.legend(loc="lower right", frameon=False)
    return figure


def _pr_figure(predictions: pd.DataFrame) -> Any:
    heads = sorted(predictions["head"].unique())
    figure, axes = plt.subplots(1, len(heads), figsize=(3.55 * len(heads), 3.0), constrained_layout=True)
    axes_array = np.atleast_1d(axes)
    for axis, head in zip(axes_array, heads):
        rows = predictions.loc[predictions["head"] == head]
        for model in MODEL_NAMES:
            group = rows.loc[rows["model"] == model]
            if group.empty:
                continue
            precision, recall, _ = precision_recall_curve(group["label"], group["score"])
            ap = average_precision_score(group["label"], group["score"])
            axis.plot(
                recall,
                precision,
                label=f"{_MODEL_LABELS[model]} ({ap:.3f})",
                color=_MODEL_COLORS[model],
                linewidth=1.15,
            )
        baseline = rows["label"].mean()
        axis.axhline(baseline, color="#6B7280", linestyle="--", linewidth=0.7)
        axis.set(
            title=f"{head}: precision–recall (OOF)",
            xlabel="Attack recall",
            ylabel="Precision",
            xlim=(0, 1),
            ylim=(0, 1),
        )
        axis.legend(loc="lower left", frameon=False)
    return figure


def _low_fpr_frontier_figure(summary: dict[str, Any]) -> Any:
    heads = sorted(summary["heads"])
    figure, axes = plt.subplots(1, len(heads), figsize=(3.55 * len(heads), 2.85), constrained_layout=True)
    axes_array = np.atleast_1d(axes)
    caps = [float(cap) for cap in summary["fpr_caps"]]
    for axis, head in zip(axes_array, heads):
        for model in MODEL_NAMES:
            details = summary["heads"][head]["models"].get(model)
            if details is None:
                continue
            recalls = [
                details["thresholds"][f"{cap:.2f}"]["attack_macro_recall"]
                for cap in caps
            ]
            axis.plot(
                np.asarray(caps) * 100,
                recalls,
                marker="o",
                markersize=3.2,
                color=_MODEL_COLORS[model],
                linewidth=1.15,
                label=_MODEL_LABELS[model],
            )
        axis.set(
            title=f"{head}: constrained recall",
            xlabel="Benign FPR cap (%)",
            ylabel="Macro attack recall",
            xlim=(min(caps) * 100 - 0.3, max(caps) * 100 + 0.3),
            ylim=(0, 1),
            xticks=np.asarray(caps) * 100,
        )
        axis.legend(loc="lower right", frameon=False)
    return figure


def _calibration_figure(predictions: pd.DataFrame) -> Any:
    heads = sorted(predictions["head"].unique())
    figure, axes = plt.subplots(1, len(heads), figsize=(3.55 * len(heads), 3.0), constrained_layout=True)
    axes_array = np.atleast_1d(axes)
    for axis, head in zip(axes_array, heads):
        rows = predictions.loc[predictions["head"] == head]
        for model in MODEL_NAMES:
            group = rows.loc[rows["model"] == model]
            if group.empty:
                continue
            bins = pd.cut(group["score"], bins=np.linspace(0, 1, 11), include_lowest=True)
            binned = group.assign(bin=bins).groupby("bin", observed=True).agg(
                predicted=("score", "mean"), observed=("label", "mean"), count=("label", "size")
            )
            binned = binned.loc[binned["count"] >= 5]
            if binned.empty:
                continue
            axis.plot(
                binned["predicted"],
                binned["observed"],
                marker="o",
                markersize=3.1,
                linewidth=1.0,
                color=_MODEL_COLORS[model],
                label=_MODEL_LABELS[model],
            )
        axis.plot([0, 1], [0, 1], color="#6B7280", linestyle="--", linewidth=0.7)
        axis.set(
            title=f"{head}: calibration (OOF)",
            xlabel="Mean predicted attack risk",
            ylabel="Observed attack frequency",
            xlim=(0, 1),
            ylim=(0, 1),
        )
        axis.legend(loc="lower right", frameon=False)
    return figure


def render_fusion_figures(
    predictions: pd.DataFrame,
    summary: dict[str, Any],
    output_dir: Path,
) -> dict[str, dict[str, Any]]:
    if output_dir.exists():
        raise FileExistsError(f"Fusion figure output already exists: {output_dir}")
    with plt.rc_context(_PLOT_STYLE):
        return {
            "roc_curves": _save_figure(_roc_figure(predictions), output_dir, "roc_curves"),
            "precision_recall_curves": _save_figure(
                _pr_figure(predictions), output_dir, "precision_recall_curves"
            ),
            "low_fpr_recall_frontier": _save_figure(
                _low_fpr_frontier_figure(summary), output_dir, "low_fpr_recall_frontier"
            ),
            "calibration_curves": _save_figure(
                _calibration_figure(predictions), output_dir, "calibration_curves"
            ),
        }


__all__ = [
    "FPR_CAPS",
    "MODEL_NAMES",
    "build_grouped_folds",
    "compute_training_weights",
    "render_fusion_figures",
    "run_head_grouped_oof",
    "select_threshold_at_fpr",
    "summarize_oof_predictions",
]
