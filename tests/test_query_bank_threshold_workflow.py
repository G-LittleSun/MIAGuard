from __future__ import annotations

import json
import hashlib
from pathlib import Path

import pytest
import yaml

from miaguard.query_bank.threshold_workflow import (
    calibrate_train_partition,
    export_enforce_config,
    validate_locked_threshold,
)
from miaguard.supervised_threshold import ATTACK_TYPES
from rag_mia_data.io_utils import (
    read_jsonl,
    sha256_file,
    write_json_atomic,
    write_jsonl_atomic,
)


def _records(*, benign_score: float = 0.1, attack_score: float = 0.9) -> list[dict]:
    rows = []
    for index in range(5):
        rows.append(
            {
                "query_id": f"benign-{index}",
                "doc_id": "doc-benign",
                "traffic_type": "benign",
                "attack_type": "benign",
                "session_key": "benign-session",
                "turn_index": index + 1,
                "total_risk_score": benign_score,
            }
        )
    for attack in ATTACK_TYPES:
        for index in range(5):
            rows.append(
                {
                    "query_id": f"{attack}-{index}",
                    "doc_id": f"doc-{attack}",
                    "traffic_type": "attack",
                    "attack_type": attack,
                    "session_key": f"{attack}-session",
                    "turn_index": index + 1,
                    "total_risk_score": attack_score,
                }
            )
    return rows


def _run(tmp_path: Path, partition: str, *, version: int = 1) -> tuple[Path, Path]:
    root = tmp_path / partition
    records_path = root / "risk_records.jsonl"
    manifest_path = root / "run_manifest.json"
    identity = {
        "partition": partition,
        "query_bank_sha256": "a" * 64,
        "split_id": "split-v1",
        "scorer_version": version,
    }
    identity_sha256 = hashlib.sha256(
        json.dumps(identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    rows = [
        {
            **row,
            "partition": partition,
            "scoring_identity_sha256": identity_sha256,
        }
        for row in _records()
    ]
    write_jsonl_atomic(records_path, rows)
    write_json_atomic(
        manifest_path,
        {
            "schema_version": 1,
            "identity": identity,
            "identity_sha256": identity_sha256,
        },
    )
    write_json_atomic(
        root / "score_summary.json",
        {"risk_records_sha256": sha256_file(records_path)},
    )
    return records_path, manifest_path


def test_train_calibration_and_locked_validation(tmp_path: Path) -> None:
    train_records, train_manifest = _run(tmp_path, "train")
    selection_path = tmp_path / "selection.json"
    selection = calibrate_train_partition(
        train_records, train_manifest, selection_path
    )
    validation_records, validation_manifest = _run(tmp_path, "validation")
    validation_path = tmp_path / "validation.json"

    result = validate_locked_threshold(
        validation_records,
        validation_manifest,
        selection_path,
        validation_path,
        bootstrap_replicates=20,
    )

    assert selection["status"] == "selected"
    assert result["status"] == "passed"
    assert result["threshold"] == selection["threshold"]
    assert result["metrics"]["benign_query_fpr"] == 0.0


def test_workflow_enforces_partition_and_identity(tmp_path: Path) -> None:
    validation_records, validation_manifest = _run(tmp_path, "validation")
    with pytest.raises(ValueError, match="train"):
        calibrate_train_partition(
            validation_records,
            validation_manifest,
            tmp_path / "bad.json",
        )


def test_workflow_rejects_risk_rows_from_another_partition(tmp_path: Path) -> None:
    records, manifest = _run(tmp_path, "train")
    rows = list(read_jsonl(records))
    rows[0]["partition"] = "validation"
    write_jsonl_atomic(records, rows)
    write_json_atomic(
        records.parent / "score_summary.json",
        {"risk_records_sha256": sha256_file(records)},
    )

    with pytest.raises(ValueError, match="partition"):
        calibrate_train_partition(records, manifest, tmp_path / "selection.json")

    train_records, train_manifest = _run(tmp_path, "train")
    selection_path = tmp_path / "selection.json"
    calibrate_train_partition(train_records, train_manifest, selection_path)
    mismatch_records, mismatch_manifest = _run(
        tmp_path / "mismatch", "validation", version=2
    )
    with pytest.raises(ValueError, match="identity"):
        validate_locked_threshold(
            mismatch_records,
            mismatch_manifest,
            selection_path,
            tmp_path / "mismatch-result.json",
            bootstrap_replicates=0,
        )


def test_failed_validation_blocks_config_export(tmp_path: Path) -> None:
    validation_path = tmp_path / "failed.json"
    write_json_atomic(
        validation_path,
        {"status": "failed", "threshold": 0.7},
    )
    base = tmp_path / "base.yaml"
    base.write_text(
        yaml.safe_dump(
            {
                "mode": "enforce",
                "policy": {"thresholds": [0.2, 0.4, 0.65, 0.85]},
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="passed"):
        export_enforce_config(base, validation_path, tmp_path / "output.yaml")


def test_export_preserves_severity_thresholds_and_adds_learned_threshold(
    tmp_path: Path,
) -> None:
    validation_path = tmp_path / "passed.json"
    write_json_atomic(
        validation_path,
        {"status": "passed", "threshold": 0.73},
    )
    base = tmp_path / "base.yaml"
    base.write_text(
        yaml.safe_dump(
            {
                "mode": "observe",
                "policy": {"thresholds": [0.2, 0.4, 0.65, 0.85]},
                "versions": {"policy": "v1"},
            }
        ),
        encoding="utf-8",
    )
    output = tmp_path / "output.yaml"

    export_enforce_config(base, validation_path, output)

    exported = yaml.safe_load(output.read_text(encoding="utf-8"))
    assert exported["mode"] == "enforce"
    assert exported["policy"]["thresholds"] == [0.2, 0.4, 0.65, 0.85]
    assert exported["policy"]["attack_detection_threshold"] == 0.73
