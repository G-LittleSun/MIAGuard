"""Defense evaluation primitives with explicit target and task denominators."""

from __future__ import annotations

import math
import json
import hashlib
import random
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

from sklearn.metrics import roc_auc_score
import numpy as np


def _rate(numerator: int, denominator: int) -> dict[str, Any]:
    return {"numerator": numerator, "denominator": denominator,
            "rate": numerator / denominator if denominator else None}


def _validate_attack_cohort(rows: Sequence[Mapping[str, Any]]) -> None:
    for key in ("method", "attack_type", "budget"):
        values = {row[key] for row in rows if key in row}
        if len(values) > 1:
            raise ValueError(f"mixed {key} in one attack metric cohort")


def attack_auc(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Average repeated seeds within a target, then compute raw AUC."""
    _validate_attack_cohort(rows)
    by_doc: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        by_doc[str(row["doc_id"])].append(row)
    labels: list[int] = []
    scores: list[float] = []
    missing = 0
    for doc_id, items in by_doc.items():
        values = {item["membership_label"] for item in items}
        if len(values) != 1 or not values <= {0, 1}:
            raise ValueError(f"Inconsistent membership label for target {doc_id}")
        available = [float(item["score"]) for item in items if item.get("score") is not None]
        if not available:
            missing += 1
            continue
        if any(not math.isfinite(value) for value in available):
            raise ValueError("Attack score must be finite")
        labels.append(next(iter(values)))
        scores.append(sum(available) / len(available))
    result = {"target_count": len(by_doc), "observed_target_count": len(scores),
              "missing_target_count": missing, "auc": None,
              "flipped_auc_diagnostic": None, "reason": None}
    if len(set(labels)) < 2:
        result["reason"] = "single_class"
        return result
    auc = float(roc_auc_score(labels, scores))
    result["auc"] = auc
    result["flipped_auc_diagnostic"] = max(auc, 1 - auc)
    return result


def _target_scores(rows: Sequence[Mapping[str, Any]]) -> tuple[list[tuple[int, float]], int]:
    _validate_attack_cohort(rows)
    by_doc: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        by_doc[str(row["doc_id"])].append(row)
    observed = []
    for doc_id, items in by_doc.items():
        labels = {item["membership_label"] for item in items}
        if len(labels) != 1 or not labels <= {0, 1}:
            raise ValueError(f"Inconsistent membership label for target {doc_id}")
        values = [float(item["score"]) for item in items if item.get("score") is not None]
        if any(not math.isfinite(value) for value in values):
            raise ValueError("Attack score must be finite")
        if values:
            observed.append((next(iter(labels)), sum(values) / len(values)))
    return observed, len(by_doc)


def calibrate_attack_operating_points(rows: Sequence[Mapping[str, Any]], *,
                                      fpr_caps: tuple[float, ...] = (.01, .05)) -> dict[str, Any]:
    """Choose direction and fixed thresholds on A-cal target scores only."""
    observed, total = _target_scores(rows)
    if not observed or len({label for label, _ in observed}) < 2:
        raise ValueError("Calibration requires both membership classes")
    if any(not math.isfinite(cap) or not 0 <= cap < 1 for cap in fpr_caps):
        raise ValueError("Invalid FPR cap")
    raw_auc = float(roc_auc_score([label for label, _ in observed], [score for _, score in observed]))
    direction = 1 if raw_auc >= .5 else -1
    transformed = [(label, direction * score) for label, score in observed]
    scores = {score for _, score in transformed}
    candidates = sorted(scores | {math.nextafter(max(scores), math.inf)}, reverse=True)
    member_count = sum(label for label, _ in transformed)
    nonmember_count = len(transformed) - member_count
    points = {}
    for cap in fpr_caps:
        valid = []
        for threshold in candidates:
            tp = sum(label == 1 and score >= threshold for label, score in transformed)
            fp = sum(label == 0 and score >= threshold for label, score in transformed)
            tpr, fpr = tp / member_count, fp / nonmember_count
            if fpr <= cap:
                valid.append((tpr, -fpr, threshold, tp, fp))
        _, _, threshold, tp, fp = max(valid)
        points[str(cap)] = {"calibrated_on": "A-cal", "direction": direction,
                            "fpr_cap": cap, "threshold": threshold,
                            "calibration_tpr": tp / member_count,
                            "calibration_fpr": fp / nonmember_count,
                            "calibration_member_count": member_count,
                            "calibration_nonmember_count": nonmember_count}
    return {"direction": direction, "raw_calibration_auc": raw_auc,
            "target_count": total, "observed_target_count": len(observed), "points": points}


def apply_frozen_attack_point(rows: Sequence[Mapping[str, Any]], point: Mapping[str, Any]) -> dict[str, Any]:
    if point.get("calibrated_on") != "A-cal" or point.get("direction") not in (-1, 1):
        raise ValueError("Attack point must be frozen on A-cal")
    observed, total = _target_scores(rows)
    threshold = float(point["threshold"])
    direction = int(point["direction"])
    member = [(label, score) for label, score in observed if label == 1]
    nonmember = [(label, score) for label, score in observed if label == 0]
    tp = sum(direction * score >= threshold for _, score in member)
    fp = sum(direction * score >= threshold for _, score in nonmember)
    tpr = tp / len(member) if member else None
    fpr = fp / len(nonmember) if nonmember else None
    return {"threshold": threshold, "direction": direction, "target_count": total,
            "observed_target_count": len(observed), "missing_target_count": total - len(observed),
            "member_count": len(member), "nonmember_count": len(nonmember),
            "tpr": tpr, "fpr": fpr, "attack_advantage": tpr - fpr if tpr is not None and fpr is not None else None,
            "reason": "single_class" if tpr is None or fpr is None else None}


def _abstains(response: str | None) -> bool:
    if response is None:
        return False
    value = response.strip().casefold()
    return value in {"unknown", "i don't know", "i do not know", "cannot answer", "i cannot answer"} or value.startswith("i cannot confirm")


def score_normal_quality(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Score all expected normal requests; failures and denials retain their denominator."""
    ids = [str(row["request_id"]) for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("Normal quality rows must have unique request IDs")
    answerable = [row for row in rows if row["answerable"] is True]
    unanswerable = [row for row in rows if row["answerable"] is False]
    if len(answerable) + len(unanswerable) != len(rows):
        raise ValueError("answerable must be boolean")
    correct = sum(row.get("status") == "complete" and isinstance(row.get("response"), str)
                  and row["response"].strip().casefold() == str(row["reference_answer"]).strip().casefold()
                  for row in answerable)
    abstain = sum(row.get("status") == "complete" and _abstains(row.get("response")) for row in unanswerable)
    claim_count = 0
    supported_count = 0
    empty_count = 0
    for row in rows:
        claims = row.get("claims")
        supported = row.get("supported_claims")
        if claims is None or supported is None:
            raise ValueError("Faithfulness requires explicit claims and supported_claims")
        if not claims:
            empty_count += 1
        if not set(supported) <= set(claims):
            raise ValueError("supported_claims must be a subset of claims")
        claim_count += len(claims)
        supported_count += len(supported)
    restricted = {"hide_target_refill", "sanitized_context", "no_context_answer", "deny"}
    false_intervention = sum(row.get("action") in restricted for row in rows)
    unavailable = sum(row.get("action") == "unavailable" or row.get("status") == "failed" for row in rows)
    return {"expected_request_count": len(rows),
            "answerable_correctness": _rate(correct, len(answerable)),
            "unanswerable_appropriate_abstention": _rate(abstain, len(unanswerable)),
            "empty_answer_count": empty_count,
            "faithfulness": _rate(supported_count, claim_count),
            "false_intervention": _rate(false_intervention, len(rows)),
            "unavailable_or_failed": _rate(unavailable, len(rows))}


def score_retrieval_recall(retrieved_doc_ids: Sequence[str], gold_evidence_ids: Sequence[str] | None) -> dict[str, Any]:
    if gold_evidence_ids is None:
        return {"numerator": 0, "denominator": 0, "rate": None, "reason": "gold_evidence_missing"}
    gold = set(gold_evidence_ids)
    if not gold:
        return {"numerator": 0, "denominator": 0, "rate": None, "reason": "no_required_evidence"}
    result = _rate(len(gold & set(retrieved_doc_ids)), len(gold))
    result["reason"] = None
    return result


def paired_cluster_bootstrap(rows: Sequence[Mapping[str, Any]], *, replicates: int = 2000,
                             seed: int = 20261022, cluster_key: str = "doc_id") -> list[list[Mapping[str, Any]]]:
    if replicates <= 0:
        raise ValueError("replicates must be positive")
    clusters: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        key = str(row.get(cluster_key, ""))
        if not key:
            raise ValueError("All rows need a nonblank cluster ID")
        clusters[key].append(row)
    if not clusters:
        raise ValueError("Bootstrap needs at least one cluster")
    keys = sorted(clusters)
    rng = random.Random(seed)
    return [[row for key in rng.choices(keys, k=len(keys)) for row in clusters[key]] for _ in range(replicates)]


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def evaluate_run(run_dir: str | Path, evaluator_spec: Mapping[str, Any]) -> dict[str, Any]:
    """Evaluate the T09 engineering fixture; formal evaluation requires reviewed gold."""
    root = Path(run_dir)
    manifest = json.loads((root / "run_manifest.json").read_text(encoding="utf-8"))
    run_metrics = json.loads((root / "metrics.json").read_text(encoding="utf-8"))
    if manifest.get("status") != "completed" or manifest.get("outcome") != "valid":
        raise ValueError("Cannot evaluate an incomplete or invalid run")
    if run_metrics.get("analysis_role") != "engineering_only" or evaluator_spec.get("analysis_role") != "engineering_only":
        raise ValueError("Formal evaluation requires reviewed gold and a frozen evaluator; engineering evaluator cannot be used")
    events = _read_jsonl(root / "events.jsonl")
    if len(events) != run_metrics["expected"]:
        raise ValueError("Run event count differs from expected denominator")
    scores = _read_jsonl(root / "attack_scores.jsonl")
    normal = _read_jsonl(root / "benign_quality.jsonl")
    methods: dict[str, Any] = {}
    for method in manifest["methods"]:
        method_events = [row for row in events if row["method"] == method]
        method_normal = [row for row in normal if row["method"] == method]
        method_scores = [row for row in scores if row["method"] == method]
        latencies = [float(row["latency_ms"]) for row in method_events if isinstance(row.get("latency_ms"), (float, int)) and math.isfinite(float(row["latency_ms"]))]
        attacks = {}
        for attack in sorted({row["attack_type"] for row in method_scores}):
            attacks[attack] = attack_auc([row for row in method_scores if row["attack_type"] == attack])
        methods[method] = {
            "attacks": attacks,
            "normal_exact_match": _rate(sum(row.get("status") == "complete" and row.get("exact_match") is True for row in method_normal), len(method_normal)),
            "normal_failed": _rate(sum(row.get("status") != "complete" for row in method_normal), len(method_normal)),
            "normal_quality_gold_status": "engineering_fixture_only",
            "faithfulness": {"rate": None, "reason": "no_reviewed_claim_annotations"},
            "cost": {"request_count": len(method_events), "measured_latency_count": len(latencies),
                     "p50_ms": float(np.percentile(latencies, 50)) if latencies else None,
                     "p95_ms": float(np.percentile(latencies, 95)) if latencies else None},
        }
    return {"schema_version": 1, "run_id": manifest["run_id"], "run_identity_sha256": manifest["identity_sha256"],
            "analysis_role": "engineering_only", "formal_effect_eligible": False,
            "evaluator_code_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "methods": methods}


__all__ = ["attack_auc", "calibrate_attack_operating_points", "apply_frozen_attack_point",
           "score_normal_quality", "score_retrieval_recall", "paired_cluster_bootstrap", "evaluate_run"]
