"""Train-only, document-balanced Query-only working point calibration."""

from __future__ import annotations

import math
import random
from collections import defaultdict
from collections.abc import Mapping, Sequence
from typing import Any

from miaguard.judge_score_dataset import ATTACK_TYPES


def _mean(values: Sequence[float]) -> float:
    return sum(values) / len(values)


def _quantile(values: list[float], fraction: float) -> float:
    values = sorted(values)
    position = (len(values) - 1) * fraction
    lower = int(position)
    upper = min(lower + 1, len(values) - 1)
    return values[lower] * (upper - position) + values[upper] * (position - lower)


def _wilson_upper(successes: int, total: int) -> float:
    z = 1.959963984540054
    rate = successes / total
    denominator = 1 + z * z / total
    centre = rate + z * z / (2 * total)
    radius = z * math.sqrt(rate * (1 - rate) / total + z * z / (4 * total * total))
    return min(1.0, (centre + radius) / denominator)


def _rates(groups: dict[str, dict[str, list[float]]], docs: Sequence[str], threshold: float) -> tuple[float, dict[str, float]]:
    by_type: dict[str, list[float]] = defaultdict(list)
    for doc in docs:
        for attack, scores in groups[doc].items():
            by_type[attack].append(_mean([float(score >= threshold) for score in scores]))
    return _mean(by_type["benign"]), {attack: _mean(by_type[attack]) for attack in ATTACK_TYPES}


def calibrate_query_only(
    rows: Sequence[Mapping[str, Any]],
    *,
    caps: tuple[float, ...] = (.01, .05),
    bootstrap_replicates: int = 1000,
    seed: int = 20261022,
) -> dict[str, Any]:
    """Select threshold by train benign FPR, then four-attack macro recall.

    Every document receives equal weight within each traffic group. A score tied
    with the threshold triggers (`>=`). The no-trigger candidate is above 1.
    """
    if not rows or any(row.get("partition") != "train" for row in rows):
        raise ValueError("Query-only calibration accepts train partition only")
    if not caps or any(not math.isfinite(cap) or not 0 <= cap < 1 for cap in caps):
        raise ValueError("FPR caps must be finite in [0, 1)")
    if bootstrap_replicates < 1:
        raise ValueError("bootstrap_replicates must be positive")
    groups: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    excluded = 0
    for row in rows:
        if row.get("head") != "logprob":
            raise ValueError("Query-only v1 expects the logprob head")
        if row.get("attack_type") not in ("benign", *ATTACK_TYPES):
            raise ValueError("Unknown attack_type")
        if (row.get("traffic_type") == "benign") != (row.get("attack_type") == "benign"):
            raise ValueError("Traffic and attack labels disagree")
        if row.get("turn_index") not in (1, 2) or row.get("query_status") != "ok":
            excluded += 1
            continue
        score = row.get("x1")
        if not isinstance(score, (int, float)) or not math.isfinite(score) or not 0 <= score <= 1:
            raise ValueError("x1 must be finite and within [0, 1]")
        doc = str(row.get("doc_id", ""))
        if not doc:
            raise ValueError("doc_id is required")
        groups[doc][str(row["attack_type"])].append(float(score))
    if not any("benign" in value for value in groups.values()):
        raise ValueError("No valid benign train query")
    for attack in ATTACK_TYPES:
        if not any(attack in value for value in groups.values()):
            raise ValueError(f"No valid train query for {attack}")
    docs = sorted(groups)
    scores = {score for types in groups.values() for values in types.values() for score in values}
    no_trigger = math.nextafter(max(scores), math.inf)
    candidates = [{"threshold": threshold, "name": "no_trigger" if threshold == no_trigger else "observed_score"}
                  for threshold in sorted(scores | {no_trigger})]
    evaluated = []
    for candidate in candidates:
        threshold = candidate["threshold"]
        fpr, recall = _rates(groups, docs, threshold)
        evaluated.append({**candidate, "benign_fpr": fpr, "attack_macro_recall": _mean(list(recall.values())), "attack_recall": recall})
    rng = random.Random(seed)
    working_points = {}
    benign_docs = [doc for doc in docs if "benign" in groups[doc]]
    for cap in caps:
        eligible = [entry for entry in evaluated if entry["benign_fpr"] <= cap + 1e-15]
        chosen = max(eligible, key=lambda entry: (entry["attack_macro_recall"], entry["threshold"]))
        threshold = chosen["threshold"]
        alarms = sum(any(score >= threshold for score in groups[doc]["benign"]) for doc in benign_docs)
        upper = _wilson_upper(alarms, len(benign_docs))
        bootstrap_fpr = []
        bootstrap_recall = []
        for _ in range(bootstrap_replicates):
            sampled = rng.choices(docs, k=len(docs))
            if not all(any(attack in groups[doc] for doc in sampled) for attack in ("benign", *ATTACK_TYPES)):
                continue
            fpr, recalls = _rates(groups, sampled, threshold)
            bootstrap_fpr.append(fpr)
            bootstrap_recall.append(_mean(list(recalls.values())))
        if not bootstrap_fpr:
            raise ValueError("Document bootstrap could not cover all traffic groups")
        working_points[f"{cap:g}"] = {
            **chosen,
            "fpr_cap": cap,
            "benign_document_any_alarm": alarms / len(benign_docs),
            "benign_document_any_alarm_wilson_upper_95": upper,
            "document_bootstrap_95": {
                "benign_fpr": [_quantile(bootstrap_fpr, .025), _quantile(bootstrap_fpr, .975)],
                "attack_macro_recall": [_quantile(bootstrap_recall, .025), _quantile(bootstrap_recall, .975)],
                "valid_replicates": len(bootstrap_fpr),
            },
            "empirical_only": upper > cap,
        }
    counts = {attack: sum(len(types.get(attack, [])) for types in groups.values()) for attack in ("benign", *ATTACK_TYPES)}
    return {
        "schema_version": 1,
        "partition": "train",
        "head": "logprob",
        "selection_rule": "max four-attack document-balanced macro recall subject to train benign FPR cap; tie: higher threshold; trigger: score >= threshold",
        "sample_counts": {"benign_queries": counts["benign"], "benign_documents": len(benign_docs), "attack_queries": {attack: counts[attack] for attack in ATTACK_TYPES}, "documents": len(docs), "excluded_rows": excluded},
        "candidates": evaluated,
        "working_points": working_points,
        "bootstrap_seed": seed,
        "bootstrap_replicates": bootstrap_replicates,
    }


__all__ = ["calibrate_query_only"]
