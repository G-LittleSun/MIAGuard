from __future__ import annotations

from pathlib import Path
import hashlib
import json

import pytest

from miaguard.query_bank.threshold_comparison import compare_test_conditions
from miaguard.supervised_threshold import ATTACK_TYPES
from rag_mia_data.io_utils import sha256_file, write_json_atomic, write_jsonl_atomic


def _records() -> list[dict]:
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
                "total_risk_score": 0.2,
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
                    "total_risk_score": 0.8,
                }
            )
    return rows


def _inputs(tmp_path: Path, *, validation_status: str = "passed", version: int = 1):
    records = tmp_path / "risk_records.jsonl"
    manifest = tmp_path / "run_manifest.json"
    validation = tmp_path / "validation.json"
    identity = {
        "partition": "test",
        "split_id": "split-v1",
        "query_bank_sha256": "a" * 64,
        "scorer_version": version,
    }
    identity_sha256 = hashlib.sha256(
        json.dumps(identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    write_jsonl_atomic(
        records,
        [
            {
                **row,
                "partition": "test",
                "scoring_identity_sha256": identity_sha256,
            }
            for row in _records()
        ],
    )
    write_json_atomic(
        manifest,
        {"identity": identity, "identity_sha256": identity_sha256},
    )
    write_json_atomic(
        records.parent / "score_summary.json",
        {"risk_records_sha256": sha256_file(records)},
    )
    write_json_atomic(
        validation,
        {
            "status": validation_status,
            "threshold": 0.7,
            "source_identity": {**identity, "partition": "validation"},
        },
    )
    return records, manifest, validation


def test_comparison_uses_fixed_conditions_without_threshold_search(tmp_path: Path) -> None:
    records, manifest, validation = _inputs(tmp_path)

    result = compare_test_conditions(
        records,
        manifest,
        validation,
        tmp_path / "comparison.json",
        level_thresholds=(0.2, 0.4, 0.65, 0.85),
        bootstrap_replicates=0,
    )

    assert list(result["conditions"]) == [
        "disabled",
        "fixed_0_10",
        "learned",
    ]
    assert result["conditions"]["fixed_0_10"]["threshold"] == 0.1
    assert result["conditions"]["learned"]["threshold"] == 0.7
    assert result["conditions"]["disabled"]["applied_level_counts"] == {"L0": 25}
    assert result["conditions"]["learned"]["detection_metrics"][
        "benign_query_fpr"
    ] == 0.0
    assert result["query_order"] == [row["query_id"] for row in _records()]


def test_comparison_rejects_failed_validation_or_identity_mismatch(
    tmp_path: Path,
) -> None:
    records, manifest, failed = _inputs(tmp_path / "failed", validation_status="failed")
    with pytest.raises(ValueError, match="passed"):
        compare_test_conditions(
            records,
            manifest,
            failed,
            tmp_path / "failed-output.json",
            level_thresholds=(0.2, 0.4, 0.65, 0.85),
            bootstrap_replicates=0,
        )

    records, manifest, validation = _inputs(tmp_path / "mismatch")
    value = json.loads(validation.read_text(encoding="utf-8"))
    value["source_identity"]["scorer_version"] = 2
    write_json_atomic(validation, value)
    with pytest.raises(ValueError, match="identity"):
        compare_test_conditions(
            records,
            manifest,
            validation,
            tmp_path / "mismatch-output.json",
            level_thresholds=(0.2, 0.4, 0.65, 0.85),
            bootstrap_replicates=0,
        )
