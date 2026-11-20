from __future__ import annotations

import math
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np
from sklearn.metrics import average_precision_score, roc_auc_score


ATTACK_TYPES = ("direct_rag_mia", "s2_mia", "masked_mia", "ia")


def _validated_records(records: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    if not records:
        raise ValueError("Threshold evaluation requires risk records")
    validated: list[dict[str, Any]] = []
    query_ids: set[str] = set()
    present_attacks: set[str] = set()
    benign_count = 0
    for source in records:
        row = dict(source)
        query_id = str(row["query_id"])
        if query_id in query_ids:
            raise ValueError(f"Duplicate risk record query_id: {query_id}")
        query_ids.add(query_id)
        traffic_type = str(row["traffic_type"])
        attack_type = str(row["attack_type"])
        if traffic_type not in {"attack", "benign"}:
            raise ValueError(f"Invalid traffic_type for {query_id}")
        if traffic_type == "attack":
            if attack_type not in ATTACK_TYPES:
                raise ValueError(f"Unsupported attack_type: {attack_type}")
            present_attacks.add(attack_type)
        elif attack_type != "benign":
            raise ValueError(f"Benign record has attack_type {attack_type}")
        else:
            benign_count += 1
        score = float(row["total_risk_score"])
        if not math.isfinite(score) or not 0.0 <= score <= 1.0:
            raise ValueError(f"Invalid total_risk_score for {query_id}")
        if int(row["turn_index"]) <= 0:
            raise ValueError(f"Invalid turn_index for {query_id}")
        if not str(row["session_key"]):
            raise ValueError(f"Missing session_key for {query_id}")
        row["total_risk_score"] = score
        validated.append(row)
    missing = set(ATTACK_TYPES).difference(present_attacks)
    if missing:
        raise ValueError(
            "Threshold evaluation is missing attack types: "
            + ", ".join(sorted(missing))
        )
    if benign_count == 0:
        raise ValueError("Threshold evaluation requires benign records")
    return validated


def _safe_ratio(numerator: int | float, denominator: int | float) -> float:
    return float(numerator / denominator) if denominator else 0.0


def _document_balanced_query_recalls(
    rows: Sequence[dict[str, Any]], predictions: Sequence[bool]
) -> dict[str, float]:
    detected: dict[tuple[str, str], list[bool]] = defaultdict(list)
    for row, prediction in zip(rows, predictions):
        if row["traffic_type"] == "attack":
            detected[(str(row["attack_type"]), str(row["doc_id"]))].append(
                prediction
            )
    result: dict[str, float] = {}
    for attack_type in ATTACK_TYPES:
        document_rates = [
            _safe_ratio(sum(values), len(values))
            for (attack, _doc_id), values in detected.items()
            if attack == attack_type
        ]
        result[attack_type] = (
            float(np.mean(document_rates)) if document_rates else 0.0
        )
    return result


def _point_metrics(
    rows: Sequence[dict[str, Any]], threshold: float
) -> dict[str, Any]:
    scores = np.asarray([float(row["total_risk_score"]) for row in rows])
    labels = np.asarray([row["traffic_type"] == "attack" for row in rows])
    predictions = scores >= threshold
    tp = int(np.sum(labels & predictions))
    fp = int(np.sum(~labels & predictions))
    tn = int(np.sum(~labels & ~predictions))
    fn = int(np.sum(labels & ~predictions))
    precision = _safe_ratio(tp, tp + fp)
    recall = _safe_ratio(tp, tp + fn)
    f1 = _safe_ratio(2 * precision * recall, precision + recall)
    true_negative_rate = _safe_ratio(tn, tn + fp)

    attack_recalls = _document_balanced_query_recalls(rows, predictions.tolist())
    recall_values = list(attack_recalls.values())

    sessions: dict[tuple[str, str, str], list[tuple[int, bool]]] = defaultdict(list)
    for row, prediction in zip(rows, predictions.tolist()):
        sessions[
            (
                str(row["attack_type"]),
                str(row["doc_id"]),
                str(row["session_key"]),
            )
        ].append((int(row["turn_index"]), prediction))

    session_by_doc: dict[tuple[str, str], list[bool]] = defaultdict(list)
    turn_3_by_doc: dict[tuple[str, str], list[bool]] = defaultdict(list)
    first_turns: Counter[str] = Counter()
    for (attack_type, doc_id, _session_key), turns in sessions.items():
        detected_turns = [turn for turn, detected in turns if detected]
        session_detected = bool(detected_turns)
        session_by_doc[(attack_type, doc_id)].append(session_detected)
        turn_3_by_doc[(attack_type, doc_id)].append(
            any(detected and turn <= 3 for turn, detected in turns)
        )
        if attack_type != "benign":
            key = str(min(detected_turns)) if detected_turns else "undetected"
            first_turns[key] += 1

    attack_session_recalls: dict[str, float] = {}
    attack_turn_3_rates: dict[str, float] = {}
    for attack_type in ATTACK_TYPES:
        per_doc = [
            _safe_ratio(sum(values), len(values))
            for (attack, _doc_id), values in session_by_doc.items()
            if attack == attack_type
        ]
        attack_session_recalls[attack_type] = float(np.mean(per_doc))
        per_doc_turn_3 = [
            _safe_ratio(sum(values), len(values))
            for (attack, _doc_id), values in turn_3_by_doc.items()
            if attack == attack_type
        ]
        attack_turn_3_rates[attack_type] = float(np.mean(per_doc_turn_3))
    benign_session_rates = [
        _safe_ratio(sum(values), len(values))
        for (attack, _doc_id), values in session_by_doc.items()
        if attack == "benign"
    ]

    return {
        "threshold": float(threshold),
        "benign_query_fpr": _safe_ratio(fp, fp + tn),
        "benign_document_balanced_session_fpr": float(
            np.mean(benign_session_rates)
        ),
        "attack_document_balanced_query_recall": attack_recalls,
        "attack_document_balanced_session_recall": attack_session_recalls,
        "attack_document_balanced_turn_3_detection_rate": attack_turn_3_rates,
        "attack_document_balanced_final_turn_detection_rate": dict(
            attack_session_recalls
        ),
        "macro_attack_recall": float(np.mean(recall_values)),
        "minimum_attack_recall": float(min(recall_values)),
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "balanced_accuracy": float((recall + true_negative_rate) / 2),
        "auroc": float(roc_auc_score(labels, scores)),
        "auprc": float(average_precision_score(labels, scores)),
        "confusion_matrix": {"tp": tp, "fp": fp, "tn": tn, "fn": fn},
        "first_detection_turn_histogram": dict(
            sorted(first_turns.items(), key=lambda item: (item[0] == "undetected", item[0]))
        ),
    }


def _bootstrap_values(
    rows: Sequence[dict[str, Any]],
    threshold: float,
    *,
    seed: int,
    replicates: int,
) -> dict[str, list[float]]:
    by_doc: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_doc[str(row["doc_id"])].append(row)
    doc_ids = sorted(by_doc)
    rng = np.random.default_rng(seed)
    values = {
        "benign_query_fpr": [],
        "macro_attack_recall": [],
        "minimum_attack_recall": [],
        "precision": [],
        "f1": [],
    }
    for _ in range(replicates):
        sampled_ids = rng.choice(doc_ids, size=len(doc_ids), replace=True)
        sample = []
        for draw_index, doc_id in enumerate(sampled_ids):
            for source in by_doc[str(doc_id)]:
                row = dict(source)
                row["doc_id"] = f"{doc_id}#bootstrap-{draw_index}"
                sample.append(row)
        scores = [float(row["total_risk_score"]) for row in sample]
        predictions = [score >= threshold for score in scores]
        labels = [row["traffic_type"] == "attack" for row in sample]
        tp = sum(label and prediction for label, prediction in zip(labels, predictions))
        fp = sum(not label and prediction for label, prediction in zip(labels, predictions))
        tn = sum(not label and not prediction for label, prediction in zip(labels, predictions))
        recalls = _document_balanced_query_recalls(sample, predictions)
        recall_values = list(recalls.values())
        precision = _safe_ratio(tp, tp + fp)
        recall = _safe_ratio(tp, sum(labels))
        values["benign_query_fpr"].append(_safe_ratio(fp, fp + tn))
        values["macro_attack_recall"].append(float(np.mean(recall_values)))
        values["minimum_attack_recall"].append(float(min(recall_values)))
        values["precision"].append(precision)
        values["f1"].append(_safe_ratio(2 * precision * recall, precision + recall))
    return values


def evaluate_locked_attack_threshold(
    records: Sequence[dict[str, Any]],
    threshold: float,
    *,
    bootstrap_seed: int = 20260818,
    bootstrap_replicates: int = 2000,
) -> dict[str, Any]:
    if not math.isfinite(threshold) or not 0.0 <= threshold <= 1.0:
        raise ValueError("threshold must be between 0 and 1")
    if bootstrap_replicates < 0:
        raise ValueError("bootstrap_replicates must not be negative")
    rows = _validated_records(records)
    result = _point_metrics(rows, threshold)
    intervals: dict[str, dict[str, float]] = {}
    if bootstrap_replicates:
        samples = _bootstrap_values(
            rows,
            threshold,
            seed=bootstrap_seed,
            replicates=bootstrap_replicates,
        )
        intervals = {
            name: {
                "lower": float(np.percentile(values, 2.5)),
                "upper": float(np.percentile(values, 97.5)),
            }
            for name, values in samples.items()
        }
    result["bootstrap"] = {
        "unit": "doc_id",
        "seed": bootstrap_seed,
        "replicates": bootstrap_replicates,
        "confidence_level": 0.95,
        "intervals": intervals,
    }
    return result


def select_document_balanced_threshold(
    records: Sequence[dict[str, Any]],
    *,
    max_benign_fpr: float = 0.05,
) -> dict[str, Any]:
    if not 0.0 <= max_benign_fpr <= 1.0:
        raise ValueError("max_benign_fpr must be between 0 and 1")
    rows = _validated_records(records)
    scores = sorted({float(row["total_risk_score"]) for row in rows})
    candidates = [*scores, float(np.nextafter(scores[-1], math.inf))]
    feasible: list[dict[str, Any]] = []
    for threshold in candidates:
        metrics = _point_metrics(rows, threshold)
        if metrics["benign_query_fpr"] <= max_benign_fpr:
            feasible.append(metrics)

    ranked = sorted(
        feasible,
        key=lambda metrics: (
            metrics["minimum_attack_recall"],
            metrics["macro_attack_recall"],
            -metrics["benign_query_fpr"],
            metrics["threshold"],
        ),
        reverse=True,
    )
    selected = next(
        (row for row in ranked if row["minimum_attack_recall"] > 0.0),
        None,
    )
    candidate_table = [
        {
            "threshold": metrics["threshold"],
            "feasible": metrics["benign_query_fpr"] <= max_benign_fpr,
            "benign_query_fpr": metrics["benign_query_fpr"],
            "attack_document_balanced_query_recall": metrics[
                "attack_document_balanced_query_recall"
            ],
            "macro_attack_recall": metrics["macro_attack_recall"],
            "minimum_attack_recall": metrics["minimum_attack_recall"],
        }
        for metrics in (_point_metrics(rows, threshold) for threshold in candidates)
    ]
    if selected is None:
        return {
            "status": "infeasible",
            "reason": "no_feasible_threshold_with_nonzero_recall_for_every_attack",
            "max_benign_fpr": max_benign_fpr,
            "candidate_count": len(candidates),
            "feasible_candidate_count": len(feasible),
            "best_diagnostic_candidates": ranked[:5],
            "candidate_table": candidate_table,
        }
    return {
        "status": "selected",
        "threshold": selected["threshold"],
        "max_benign_fpr": max_benign_fpr,
        "candidate_count": len(candidates),
        "feasible_candidate_count": len(feasible),
        "selection_objective": [
            "maximize_minimum_attack_document_balanced_query_recall",
            "maximize_macro_attack_document_balanced_query_recall",
            "minimize_benign_query_fpr",
            "maximize_threshold",
        ],
        "selected_metrics": selected,
        "candidate_table": candidate_table,
    }
