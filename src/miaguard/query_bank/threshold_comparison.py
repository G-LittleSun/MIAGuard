from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Mapping

from miaguard.access_policy import LevelMapper
from miaguard.supervised_threshold import (
    ATTACK_TYPES,
    evaluate_locked_attack_threshold,
)
from rag_mia_data.io_utils import sha256_file, write_json_atomic

from .threshold_workflow import load_verified_scoring_records


def _mapping(path: Path, description: str) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{description} must be a mapping")
    return value


def _identity_core(value: Mapping[str, Any]) -> dict[str, Any]:
    return {str(key): item for key, item in value.items() if key != "partition"}


def _disabled_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    attack_count = sum(row["traffic_type"] == "attack" for row in rows)
    benign_count = len(rows) - attack_count
    return {
        "threshold": None,
        "benign_query_fpr": 0.0,
        "attack_document_balanced_query_recall": {
            attack_type: 0.0 for attack_type in ATTACK_TYPES
        },
        "macro_attack_recall": 0.0,
        "minimum_attack_recall": 0.0,
        "precision": 0.0,
        "recall": 0.0,
        "f1": 0.0,
        "confusion_matrix": {
            "tp": 0,
            "fp": 0,
            "tn": benign_count,
            "fn": attack_count,
        },
    }


def _condition(
    rows: list[dict[str, Any]],
    *,
    mode: str,
    level_thresholds: tuple[float, float, float, float],
    attack_threshold: float | None,
    bootstrap_seed: int,
    bootstrap_replicates: int,
) -> dict[str, Any]:
    mapper = LevelMapper(
        level_thresholds,
        attack_detection_threshold=attack_threshold,
    )
    decisions = [
        mapper.decide(float(row["total_risk_score"]), mode) for row in rows
    ]
    metrics = (
        _disabled_metrics(rows)
        if mode == "disabled"
        else evaluate_locked_attack_threshold(
            rows,
            float(attack_threshold),
            bootstrap_seed=bootstrap_seed,
            bootstrap_replicates=bootstrap_replicates,
        )
    )
    return {
        "mode": mode,
        "threshold": attack_threshold,
        "detection_metrics": metrics,
        "recommended_level_counts": dict(
            sorted(Counter(value.recommended_level for value in decisions).items())
        ),
        "applied_level_counts": dict(
            sorted(Counter(value.applied_level for value in decisions).items())
        ),
        "access_action_counts": dict(
            sorted(Counter(value.access_action for value in decisions).items())
        ),
    }


def compare_test_conditions(
    risk_records_path: Path,
    run_manifest_path: Path,
    validation_result_path: Path,
    output_path: Path,
    *,
    level_thresholds: tuple[float, float, float, float],
    bootstrap_seed: int = 20260818,
    bootstrap_replicates: int = 2000,
) -> dict[str, Any]:
    if output_path.exists():
        raise FileExistsError(f"Comparison output already exists: {output_path}")
    rows, identity = load_verified_scoring_records(
        risk_records_path,
        run_manifest_path,
        "test",
    )
    validation = _mapping(validation_result_path, "Validation result")
    if validation.get("status") != "passed":
        raise ValueError("Three-condition comparison requires passed validation")
    validation_identity = validation.get("source_identity")
    if not isinstance(validation_identity, Mapping) or (
        _identity_core(validation_identity) != _identity_core(identity)
    ):
        raise ValueError("Test scoring identity does not match validation identity")
    learned_threshold = float(validation["threshold"])
    conditions = {
        "disabled": _condition(
            rows,
            mode="disabled",
            level_thresholds=level_thresholds,
            attack_threshold=None,
            bootstrap_seed=bootstrap_seed,
            bootstrap_replicates=bootstrap_replicates,
        ),
        "fixed_0_10": _condition(
            rows,
            mode="enforce",
            level_thresholds=level_thresholds,
            attack_threshold=0.10,
            bootstrap_seed=bootstrap_seed,
            bootstrap_replicates=bootstrap_replicates,
        ),
        "learned": _condition(
            rows,
            mode="enforce",
            level_thresholds=level_thresholds,
            attack_threshold=learned_threshold,
            bootstrap_seed=bootstrap_seed,
            bootstrap_replicates=bootstrap_replicates,
        ),
    }
    output = {
        "schema_version": 1,
        "partition": "test",
        "query_order": [str(row["query_id"]) for row in rows],
        "risk_records_sha256": sha256_file(risk_records_path),
        "validation_result_sha256": sha256_file(validation_result_path),
        "conditions": conditions,
    }
    write_json_atomic(output_path, output)
    return output


__all__ = ["compare_test_conditions"]
