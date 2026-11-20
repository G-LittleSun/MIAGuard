from __future__ import annotations

import math
from collections import Counter
from copy import deepcopy
from statistics import mean
from typing import Any, Mapping, Sequence

import numpy as np
from sklearn.metrics import roc_auc_score


_QUERY_PRIMARY_ATTACKS = ("direct_rag_mia", "masked_mia", "s2_mia")
_PRIMARY_METRIC_KEYS = (
    "direct_rag_mia_query",
    "masked_mia_query",
    "s2_mia_query",
    "ia_session",
)


def _binary_values(labels: Sequence[int], scores: Sequence[float]) -> tuple[list[int], list[float]]:
    if len(labels) != len(scores) or not labels:
        raise ValueError("labels and scores must be non-empty and have equal length")
    normalized_labels = [int(value) for value in labels]
    normalized_scores = [float(value) for value in scores]
    if set(normalized_labels) != {0, 1}:
        raise ValueError("Binary metrics require both label classes")
    if any(not math.isfinite(value) for value in normalized_scores):
        raise ValueError("Scores must be finite")
    return normalized_labels, normalized_scores


def fixed_fpr_operating_point(
    labels: Sequence[int], scores: Sequence[float], *, max_fpr: float
) -> dict[str, Any]:
    labels, scores = _binary_values(labels, scores)
    if not 0 <= max_fpr <= 1:
        raise ValueError("max_fpr must be in [0, 1]")
    thresholds = [math.inf, *sorted(set(scores), reverse=True)]
    candidates: list[dict[str, float]] = []
    positives = sum(labels)
    negatives = len(labels) - positives
    for threshold in thresholds:
        predictions = [score >= threshold for score in scores]
        true_positives = sum(prediction and label == 1 for prediction, label in zip(predictions, labels))
        false_positives = sum(prediction and label == 0 for prediction, label in zip(predictions, labels))
        recall = true_positives / positives
        fpr = false_positives / negatives
        if fpr <= max_fpr + 1e-12:
            candidates.append({"threshold": threshold, "recall": recall, "fpr": fpr})
    best = max(
        candidates,
        key=lambda item: (item["recall"], -item["fpr"], -item["threshold"]),
    )
    return {
        **{**best, "threshold": None if math.isinf(best["threshold"]) else best["threshold"]},
        "max_fpr": max_fpr,
        "threshold_kind": "diagnostic_only",
        "deployable": False,
    }


def _pair_metrics(labels: Sequence[int], scores: Sequence[float]) -> dict[str, Any]:
    labels, scores = _binary_values(labels, scores)
    return {
        "count": len(labels),
        "positive_count": sum(labels),
        "negative_count": len(labels) - sum(labels),
        "auroc": float(roc_auc_score(labels, scores)),
        "operating_points": {
            str(int(cap * 100)): fixed_fpr_operating_point(labels, scores, max_fpr=cap)
            for cap in (0.01, 0.05, 0.10)
        },
    }


def _score(row: Mapping[str, Any], stage: str, head: str) -> float:
    try:
        value = float(row[f"{stage}_trace"][head]["score"])
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError(f"Record has invalid {stage}/{head} score") from error
    if not math.isfinite(value) or not 0 <= value <= 1:
        raise ValueError(f"Record {stage}/{head} score must be finite and in [0, 1]")
    return value


def _pair_rows(
    records: Sequence[Mapping[str, Any]], attack_type: str
) -> tuple[list[Mapping[str, Any]], list[int]]:
    selected = [
        row for row in records if str(row["attack_type"]) in {"benign", attack_type}
    ]
    labels = [0 if str(row["attack_type"]) == "benign" else 1 for row in selected]
    return selected, labels


def _maximum_score_mass(scores: Sequence[float]) -> float:
    if not scores:
        return 0.0
    counts = Counter(scores)
    return max(counts.values()) / len(scores)


def _status_rate(records: Sequence[Mapping[str, Any]], stage: str) -> float:
    if not records:
        return 0.0
    ok = sum(
        str(row[f"{stage}_trace"].get("statuses", {}).get("overall")) == "ok"
        for row in records
    )
    return ok / len(records)


def _latency_mean(records: Sequence[Mapping[str, Any]], stage: str) -> float:
    values = [
        float(row[f"{stage}_trace"].get("latencies_ms", {}).get("total", 0.0))
        for row in records
    ]
    if any(not math.isfinite(value) or value < 0 for value in values):
        raise ValueError("Judge latency values must be finite and non-negative")
    return mean(values) if values else 0.0


def _routing_metrics(
    records: Sequence[Mapping[str, Any]], stage: str
) -> dict[str, Any]:
    selected = list(records)
    if stage == "session":
        selected = [
            row
            for row in selected
            if int(row["turn_index"]) == int(row["session_length"])
        ]
    attack_rows = [row for row in selected if str(row["attack_type"]) != "benign"]
    benign_rows = [row for row in selected if str(row["attack_type"]) == "benign"]

    def screening(row: Mapping[str, Any]) -> Mapping[str, Any]:
        value = row[f"{stage}_trace"].get("screening")
        if not isinstance(value, Mapping):
            raise ValueError(f"Record has invalid {stage} screening trace")
        return value

    def candidates(row: Mapping[str, Any]) -> list[str]:
        raw = screening(row).get("candidate_attack_types")
        if not isinstance(raw, list) or any(not isinstance(item, str) for item in raw):
            raise ValueError(f"Record has invalid {stage} candidate_attack_types")
        return raw

    per_attack: dict[str, Any] = {}
    for attack_type in sorted({str(row["attack_type"]) for row in attack_rows}):
        rows = [row for row in attack_rows if str(row["attack_type"]) == attack_type]
        top1_hits = sum(bool(candidates(row)) and candidates(row)[0] == attack_type for row in rows)
        top2_hits = sum(attack_type in candidates(row) for row in rows)
        per_attack[attack_type] = {
            "count": len(rows),
            "top1_candidate_accuracy": top1_hits / len(rows),
            "top2_candidate_coverage": top2_hits / len(rows),
        }
    attack_skips = sum(
        screening(row).get("routing_decision") != "REVIEW" for row in attack_rows
    )
    benign_reviews = sum(
        screening(row).get("routing_decision") == "REVIEW" for row in benign_rows
    )
    top2_hits = sum(str(row["attack_type"]) in candidates(row) for row in attack_rows)
    return {
        "record_count": len(selected),
        "attack_count": len(attack_rows),
        "benign_count": len(benign_rows),
        "overall_top2_candidate_coverage": (
            top2_hits / len(attack_rows) if attack_rows else 0.0
        ),
        "attack_erroneous_skip_rate": (
            attack_skips / len(attack_rows) if attack_rows else 0.0
        ),
        "benign_review_rate": (
            benign_reviews / len(benign_rows) if benign_rows else 0.0
        ),
        "candidate_ambiguity_rate": (
            sum(bool(screening(row).get("candidate_ambiguity")) for row in selected)
            / len(selected)
            if selected
            else 0.0
        ),
        "per_attack": per_attack,
    }


def _evaluate_head(records: Sequence[Mapping[str, Any]], head: str) -> dict[str, Any]:
    final_rows = [
        row for row in records if int(row["turn_index"]) == int(row["session_length"])
    ]
    groups: dict[str, Any] = {}
    for attack_type in _QUERY_PRIMARY_ATTACKS:
        pair_rows, labels = _pair_rows(records, attack_type)
        groups[f"{attack_type}_query"] = _pair_metrics(
            labels, [_score(row, "query", head) for row in pair_rows]
        )
    ia_query_rows, ia_query_labels = _pair_rows(records, "ia")
    groups["ia_query"] = _pair_metrics(
        ia_query_labels, [_score(row, "query", head) for row in ia_query_rows]
    )
    ia_session_rows, ia_session_labels = _pair_rows(final_rows, "ia")
    groups["ia_session"] = _pair_metrics(
        ia_session_labels, [_score(row, "session", head) for row in ia_session_rows]
    )

    primary_recalls = [
        groups[key]["operating_points"]["5"]["recall"]
        for key in _PRIMARY_METRIC_KEYS
    ]
    all_scores = [_score(row, "query", head) for row in records]
    all_scores.extend(_score(row, "session", head) for row in final_rows)
    return {
        "query_count": len(records),
        "final_session_count": len(final_rows),
        "groups": groups,
        "score_distribution": {
            "unique_score_count": len(set(all_scores)),
            "maximum_score_mass": _maximum_score_mass(all_scores),
        },
        "status_rates": {
            "query_ok": _status_rate(records, "query"),
            "session_ok": _status_rate(records, "session"),
        },
        "latency_ms": {
            "query_mean": _latency_mean(records, "query"),
            "session_mean": _latency_mean(records, "session"),
            "total_mean": _latency_mean(records, "query")
            + _latency_mean(records, "session"),
        },
        "selection_metrics": {
            "minimum_primary_recall_at_5pct_fpr": min(primary_recalls),
            "macro_primary_recall_at_5pct_fpr": mean(primary_recalls),
            "ia_session_auroc": groups["ia_session"]["auroc"],
            "maximum_score_mass": _maximum_score_mass(all_scores),
            "mean_total_latency_ms": _latency_mean(records, "query")
            + _latency_mean(records, "session"),
        },
    }


def _validate_records(records: Sequence[Mapping[str, Any]]) -> None:
    if not records:
        raise ValueError("Judge evaluation requires at least one record")
    required = {
        "query_id",
        "doc_id",
        "session_key",
        "turn_index",
        "session_length",
        "traffic_type",
        "attack_type",
        "query_trace",
        "session_trace",
    }
    for row in records:
        missing = required - set(row)
        if missing:
            raise ValueError(f"Judge record is missing fields: {sorted(missing)}")
        attack_type = str(row["attack_type"])
        traffic_type = str(row["traffic_type"])
        if (attack_type == "benign") != (traffic_type == "benign"):
            raise ValueError("Judge record traffic_type and attack_type disagree")
        for stage in ("query", "session"):
            for head in ("rubric", "logprob"):
                _score(row, stage, head)


def _bootstrap_intervals(
    records: Sequence[Mapping[str, Any]], *, seed: int, replicates: int
) -> dict[str, Any]:
    if replicates <= 0:
        return {}
    doc_ids = sorted({str(row["doc_id"]) for row in records})
    rng = np.random.default_rng(seed)
    values: dict[str, dict[str, list[float]]] = {
        head: {key: [] for key in _evaluate_head(records, head)["selection_metrics"]}
        for head in ("rubric", "logprob")
    }
    by_doc = {
        doc_id: [row for row in records if str(row["doc_id"]) == doc_id]
        for doc_id in doc_ids
    }
    for _ in range(replicates):
        sampled: list[dict[str, Any]] = []
        for draw_index, doc_id in enumerate(rng.choice(doc_ids, size=len(doc_ids), replace=True)):
            for source in by_doc[str(doc_id)]:
                row = deepcopy(dict(source))
                suffix = f"#bootstrap-{draw_index}"
                row["doc_id"] = f"{doc_id}{suffix}"
                row["session_key"] = f"{row['session_key']}{suffix}"
                sampled.append(row)
        try:
            for head in ("rubric", "logprob"):
                metrics = _evaluate_head(sampled, head)["selection_metrics"]
                for key, value in metrics.items():
                    values[head][key].append(float(value))
        except ValueError:
            continue
    return {
        head: {
            key: {
                "low_95": float(np.quantile(samples, 0.025)),
                "high_95": float(np.quantile(samples, 0.975)),
                "valid_replicates": len(samples),
            }
            for key, samples in metrics.items()
            if samples
        }
        for head, metrics in values.items()
    }


def evaluate_judge_records(
    records: Sequence[Mapping[str, Any]], *, bootstrap_seed: int = 20260823,
    bootstrap_replicates: int = 1000,
) -> dict[str, Any]:
    rows = list(records)
    _validate_records(rows)
    if bootstrap_replicates < 0:
        raise ValueError("bootstrap_replicates must be non-negative")
    report = {
        "schema_version": 1,
        "metric_roles": {
            "direct_rag_mia_query": "primary",
            "masked_mia_query": "primary",
            "s2_mia_query": "primary",
            "ia_query": "diagnostic",
            "ia_session": "primary",
        },
        "heads": {
            head: _evaluate_head(rows, head) for head in ("rubric", "logprob")
        },
        "routing": {
            "query": _routing_metrics(rows, "query"),
            "session": _routing_metrics(rows, "session"),
            "primary_requirement": "maximize_top2_candidate_coverage_before_scoring_head_selection",
        },
        "bootstrap": {
            "unit": "doc_id",
            "seed": bootstrap_seed,
            "requested_replicates": bootstrap_replicates,
            "intervals": _bootstrap_intervals(
                rows, seed=bootstrap_seed, replicates=bootstrap_replicates
            ),
        },
        "access_threshold_selected": False,
    }
    report["selection"] = compare_judge_heads(report)
    return report


def compare_judge_heads(report: Mapping[str, Any]) -> dict[str, Any]:
    objective = [
        "maximize_minimum_primary_recall_at_5pct_fpr",
        "maximize_macro_primary_recall_at_5pct_fpr",
        "maximize_ia_session_auroc",
        "minimize_maximum_score_mass",
        "minimize_mean_total_latency_ms",
    ]

    def rank(head: str) -> tuple[float, ...]:
        metrics = report["heads"][head]["selection_metrics"]
        return (
            float(metrics["minimum_primary_recall_at_5pct_fpr"]),
            float(metrics["macro_primary_recall_at_5pct_fpr"]),
            float(metrics["ia_session_auroc"]),
            -float(metrics["maximum_score_mass"]),
            -float(metrics["mean_total_latency_ms"]),
        )

    recommended = max(("rubric", "logprob"), key=lambda head: (rank(head), head))
    return {
        "recommended_head": recommended,
        "selection_objective": objective,
        "head_ranks": {head: list(rank(head)) for head in ("rubric", "logprob")},
        "does_not_select_access_threshold": True,
    }


__all__ = [
    "compare_judge_heads",
    "evaluate_judge_records",
    "fixed_fpr_operating_point",
]
