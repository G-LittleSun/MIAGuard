import json
from pathlib import Path

import pandas as pd
import pytest

from miaguard.query_bank.judge_benchmark import canonical_identity_sha256
from miaguard.query_bank.judge_score_workflow import (
    run_train_score_analysis,
    run_train_score_fusion,
)
from rag_mia_data.io_utils import sha256_file, write_json_atomic, write_jsonl_atomic


def _trace(score: float, status: str) -> dict:
    return {
        "rubric": {"score": score},
        "logprob": {"score": score},
        "statuses": {"overall": status},
        "screening": {"routing_decision": "REVIEW"},
    }


def _run_dir(tmp_path: Path, *, partition: str = "train") -> Path:
    run_dir = tmp_path / "judge" / partition
    identity = {"partition": partition, "prompt_version": "test"}
    identity_sha256 = canonical_identity_sha256(identity)
    records = []
    for doc_id, traffic_type, attack_type in (
        ("doc-benign", "benign", "benign"),
        ("doc-ia", "attack", "ia"),
    ):
        for turn in range(1, 6):
            available = turn >= 3
            records.append(
                {
                    "query_id": f"{doc_id}-q{turn}",
                    "doc_id": doc_id,
                    "session_key": f"session-{doc_id}",
                    "turn_index": turn,
                    "session_length": 5,
                    "partition": partition,
                    "traffic_type": traffic_type,
                    "attack_type": attack_type,
                    "membership_label": 1,
                    "scoring_identity_sha256": identity_sha256,
                    "query_trace": _trace(0.1 * turn, "ok"),
                    "session_trace": _trace(
                        0.1 * turn if available else 0.1,
                        "ok" if available else "insufficient_history",
                    ),
                }
            )
    records_path = run_dir / "judge_records.jsonl"
    write_jsonl_atomic(records_path, records)
    write_json_atomic(
        run_dir / "run_manifest.json",
        {
            "schema_version": 1,
            "identity": identity,
            "identity_sha256": identity_sha256,
        },
    )
    write_json_atomic(
        run_dir / "benchmark_summary.json",
        {
            "schema_version": 1,
            "partition": partition,
            "scoring_identity_sha256": identity_sha256,
            "judge_records_sha256": sha256_file(records_path),
        },
    )
    return run_dir


def test_train_analysis_writes_hashed_stage_a_artifacts(tmp_path: Path) -> None:
    run_dir = _run_dir(tmp_path)
    output_dir = tmp_path / "analysis" / "train"

    result = run_train_score_analysis(
        run_dir, output_dir, bootstrap_seed=17, bootstrap_replicates=5
    )

    assert result["partition"] == "train"
    assert result["stage_a_status"] == "awaiting_human_review"
    for name in (
        "separability_dataset.parquet",
        "score_audit.json",
        "separability_report.json",
        "figure_manifest.json",
        "run_manifest.json",
    ):
        assert (output_dir / name).is_file()
    manifest = json.loads(
        (output_dir / "run_manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["classifier_training_authorized"] is False
    assert manifest["source"]["judge_records_sha256"] == sha256_file(
        run_dir / "judge_records.jsonl"
    )
    assert len(manifest["artifacts"]) >= 17


def test_train_analysis_refuses_non_train_partition(tmp_path: Path) -> None:
    run_dir = _run_dir(tmp_path, partition="validation")

    with pytest.raises(ValueError, match="train partition"):
        run_train_score_analysis(run_dir, tmp_path / "analysis")


def test_train_analysis_refuses_existing_output(tmp_path: Path) -> None:
    run_dir = _run_dir(tmp_path)
    output_dir = tmp_path / "analysis"
    output_dir.mkdir()

    with pytest.raises(FileExistsError, match="already exists"):
        run_train_score_analysis(run_dir, output_dir)


def _fusion_stage_a_dir(tmp_path: Path) -> Path:
    output_dir = tmp_path / "score-analysis" / "train"
    rows = []
    for doc_number in range(10):
        for attack_type, label, x1, x2 in (
            ("benign", 0, 0.08, 0.10),
            ("direct_rag_mia", 1, 0.86, 0.88),
            ("s2_mia", 1, 0.46, 0.62),
            ("masked_mia", 1, 0.76, 0.76),
            ("ia", 1, 0.12, 0.56),
        ):
            for head in ("rubric", "logprob"):
                rows.append(
                    {
                        "query_id": f"{head}-{doc_number}-{attack_type}",
                        "doc_id": f"doc-{doc_number}",
                        "session_key": f"session-{doc_number}-{attack_type}",
                        "turn_index": 3,
                        "attack_type": attack_type,
                        "label": label,
                        "head": head,
                        "x1": x1 + doc_number * 0.001,
                        "x2_observed": x2 + doc_number * 0.001,
                        "session_score_available": True,
                    }
                )
    output_dir.mkdir(parents=True)
    pd.DataFrame(rows).to_parquet(output_dir / "separability_dataset.parquet", index=False)
    write_json_atomic(
        output_dir / "run_manifest.json",
        {
            "stage": "score_separability",
            "partition": "train",
            "stage_a_status": "awaiting_human_review",
            "classifier_training_authorized": False,
            "source": {"judge_records_sha256": "test-source"},
        },
    )
    return output_dir


def test_train_fusion_requires_review_and_writes_train_only_artifacts(tmp_path: Path) -> None:
    analysis_dir = _fusion_stage_a_dir(tmp_path)
    output_dir = tmp_path / "fusion" / "train"

    with pytest.raises(ValueError, match="review authorization"):
        run_train_score_fusion(analysis_dir, output_dir, stage_a_reviewed=False)

    result = run_train_score_fusion(
        analysis_dir,
        output_dir,
        stage_a_reviewed=True,
        bootstrap_replicates=0,
        cv_seed=43,
    )

    assert result["partition"] == "train"
    assert result["stage"] == "score_fusion_oof"
    for name in (
        "oof_predictions.parquet",
        "model_comparison.json",
        "threshold_selection.json",
        "figure_manifest.json",
        "run_manifest.json",
    ):
        assert (output_dir / name).is_file()
    manifest = json.loads((output_dir / "run_manifest.json").read_text(encoding="utf-8"))
    assert manifest["stage_a_reviewed"] is True
    assert manifest["source_stage_a"]["path"] == str(analysis_dir.resolve())
