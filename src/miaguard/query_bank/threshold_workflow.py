from __future__ import annotations

import json
import hashlib
from pathlib import Path
from typing import Any, Mapping

import yaml

from rag_mia_data.io_utils import (
    read_jsonl,
    sha256_file,
    write_json_atomic,
    write_yaml_atomic,
)

from miaguard.supervised_threshold import (
    evaluate_locked_attack_threshold,
    select_document_balanced_threshold,
)


def _load_mapping(path: Path, description: str) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{description} must be a mapping")
    return value


def _canonical_sha256(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def load_verified_scoring_records(
    risk_records_path: Path,
    run_manifest_path: Path,
    expected_partition: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    manifest = _load_mapping(run_manifest_path, "Scoring run manifest")
    identity = manifest.get("identity")
    if not isinstance(identity, dict):
        raise ValueError("Scoring run manifest requires an identity mapping")
    if identity.get("partition") != expected_partition:
        raise ValueError(
            f"Scoring identity partition must be {expected_partition}"
        )
    identity_sha256 = str(manifest.get("identity_sha256", ""))
    if identity_sha256 != _canonical_sha256(identity):
        raise ValueError("Scoring identity SHA256 is inconsistent")
    summary_path = risk_records_path.parent / "score_summary.json"
    summary = _load_mapping(summary_path, "Scoring summary")
    if summary.get("risk_records_sha256") != sha256_file(risk_records_path):
        raise ValueError("Risk records SHA256 does not match scoring summary")
    records = list(read_jsonl(risk_records_path))
    for row in records:
        if row.get("partition") != expected_partition:
            raise ValueError("Risk record partition does not match run identity")
        if row.get("scoring_identity_sha256") != identity_sha256:
            raise ValueError("Risk record scoring identity does not match run manifest")
    return records, identity


def _identity_core(identity: Mapping[str, Any]) -> dict[str, Any]:
    return {str(key): value for key, value in identity.items() if key != "partition"}


def _refuse_output(path: Path) -> None:
    if path.exists():
        raise FileExistsError(f"Output already exists: {path}")


def calibrate_train_partition(
    risk_records_path: Path,
    run_manifest_path: Path,
    output_path: Path,
    *,
    max_benign_fpr: float = 0.05,
) -> dict[str, Any]:
    _refuse_output(output_path)
    records, identity = load_verified_scoring_records(
        risk_records_path,
        run_manifest_path,
        "train",
    )
    result = select_document_balanced_threshold(
        records,
        max_benign_fpr=max_benign_fpr,
    )
    output = {
        **result,
        "schema_version": 1,
        "partition": "train",
        "source_identity": identity,
        "risk_records_sha256": sha256_file(risk_records_path),
    }
    write_json_atomic(output_path, output)
    return output


def validate_locked_threshold(
    risk_records_path: Path,
    run_manifest_path: Path,
    threshold_selection_path: Path,
    output_path: Path,
    *,
    max_validation_benign_fpr: float = 0.10,
    bootstrap_seed: int = 20260818,
    bootstrap_replicates: int = 2000,
) -> dict[str, Any]:
    _refuse_output(output_path)
    records, identity = load_verified_scoring_records(
        risk_records_path,
        run_manifest_path,
        "validation",
    )
    selection = _load_mapping(threshold_selection_path, "Threshold selection")
    if selection.get("status") != "selected" or "threshold" not in selection:
        raise ValueError("Validation requires a selected train threshold")
    source_identity = selection.get("source_identity")
    if not isinstance(source_identity, Mapping):
        raise ValueError("Threshold selection has no source identity")
    if _identity_core(source_identity) != _identity_core(identity):
        raise ValueError("Validation scoring identity does not match train identity")

    threshold = float(selection["threshold"])
    metrics = evaluate_locked_attack_threshold(
        records,
        threshold,
        bootstrap_seed=bootstrap_seed,
        bootstrap_replicates=bootstrap_replicates,
    )
    recalls = metrics["attack_document_balanced_query_recall"]
    passed = (
        metrics["benign_query_fpr"] <= max_validation_benign_fpr
        and all(float(value) > 0.0 for value in recalls.values())
    )
    output = {
        "schema_version": 1,
        "status": "passed" if passed else "failed",
        "partition": "validation",
        "threshold": threshold,
        "pass_criteria": {
            "max_benign_query_fpr": max_validation_benign_fpr,
            "require_nonzero_recall_for_every_attack": True,
        },
        "metrics": metrics,
        "source_identity": identity,
        "train_selection_sha256": sha256_file(threshold_selection_path),
        "risk_records_sha256": sha256_file(risk_records_path),
    }
    write_json_atomic(output_path, output)
    return output


def export_enforce_config(
    base_config_path: Path,
    validation_result_path: Path,
    output_path: Path,
) -> None:
    _refuse_output(output_path)
    validation = _load_mapping(validation_result_path, "Validation result")
    if validation.get("status") != "passed":
        raise ValueError("Enforce config export requires a passed validation result")
    threshold = float(validation["threshold"])
    if not 0.0 <= threshold <= 1.0:
        raise ValueError("Validated attack threshold must be in [0, 1]")
    raw = yaml.safe_load(base_config_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or not isinstance(raw.get("policy"), dict):
        raise ValueError("Base config requires a policy mapping")
    raw["mode"] = "enforce"
    raw["policy"]["attack_detection_threshold"] = threshold
    write_yaml_atomic(output_path, raw)


__all__ = [
    "calibrate_train_partition",
    "export_enforce_config",
    "validate_locked_threshold",
    "load_verified_scoring_records",
]
