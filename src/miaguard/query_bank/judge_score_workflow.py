from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

import pandas as pd

from rag_mia_data.io_utils import (
    file_manifest_entry,
    utc_now_iso,
    write_json_atomic,
)

from miaguard.judge_score_analysis import (
    render_score_figures,
    summarize_score_table,
)
from miaguard.judge_score_dataset import build_score_table
from miaguard.judge_score_fusion import (
    FPR_CAPS,
    render_fusion_figures,
    run_head_grouped_oof,
    summarize_oof_predictions,
)

from .judge_benchmark import load_verified_judge_records


def _load_mapping(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return value


def _portable_figure_manifest(
    manifest: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    portable: dict[str, dict[str, Any]] = {}
    for key, value in manifest.items():
        portable[key] = {
            **value,
            "png": f"figures/{Path(str(value['png'])).name}",
            "pdf": f"figures/{Path(str(value['pdf'])).name}",
        }
    return portable


def run_train_score_analysis(
    run_dir: Path,
    output_dir: Path,
    *,
    bootstrap_seed: int = 20260829,
    bootstrap_replicates: int = 1000,
) -> dict[str, Any]:
    run_dir = run_dir.resolve()
    output_dir = output_dir.resolve()
    if output_dir.exists():
        raise FileExistsError(f"Analysis output already exists: {output_dir}")
    source_manifest = _load_mapping(run_dir / "run_manifest.json")
    identity = source_manifest.get("identity")
    if not isinstance(identity, dict) or identity.get("partition") != "train":
        raise ValueError("Judge score analysis requires the train partition")
    records, source = load_verified_judge_records(run_dir)
    table, audit = build_score_table(records)
    if audit["partition"] != "train":
        raise ValueError("Judge score analysis requires the train partition")
    report = summarize_score_table(
        table,
        bootstrap_seed=bootstrap_seed,
        bootstrap_replicates=bootstrap_replicates,
    )

    output_dir.parent.mkdir(parents=True, exist_ok=True)
    prefix = f".{output_dir.name}.tmp-"
    with tempfile.TemporaryDirectory(prefix=prefix, dir=output_dir.parent) as name:
        temporary = Path(name)
        table.to_parquet(
            temporary / "separability_dataset.parquet",
            index=False,
        )
        write_json_atomic(temporary / "score_audit.json", audit)
        write_json_atomic(temporary / "separability_report.json", report)
        figures = render_score_figures(table, temporary / "figures")
        write_json_atomic(
            temporary / "figure_manifest.json",
            _portable_figure_manifest(figures),
        )
        artifacts = [
            file_manifest_entry(path, temporary)
            for path in sorted(temporary.rglob("*"))
            if path.is_file() and path.name != "run_manifest.json"
        ]
        manifest = {
            "schema_version": 1,
            "stage": "score_separability",
            "partition": "train",
            "stage_a_status": "awaiting_human_review",
            "classifier_training_authorized": False,
            "created_at": utc_now_iso(),
            "source": source,
            "source_identity": identity,
            "bootstrap": {
                "unit": "doc_id",
                "seed": bootstrap_seed,
                "replicates": bootstrap_replicates,
            },
            "counts": {
                "source_records": int(audit["source_record_count"]),
                "long_form_rows": int(audit["long_form_row_count"]),
                "documents": int(audit["unique_document_count"]),
                "sessions": int(audit["unique_session_count"]),
            },
            "artifacts": artifacts,
        }
        write_json_atomic(temporary / "run_manifest.json", manifest)
        temporary.replace(output_dir)
    return manifest


def run_train_score_fusion(
    analysis_dir: Path,
    output_dir: Path,
    *,
    stage_a_reviewed: bool,
    cv_splits: int = 5,
    cv_seed: int = 20260903,
    bootstrap_replicates: int = 1000,
    bootstrap_seed: int = 20260903,
) -> dict[str, Any]:
    """Run Stage B only from a reviewed, train-only Stage A artifact directory."""

    analysis_dir = analysis_dir.resolve()
    output_dir = output_dir.resolve()
    if output_dir.exists():
        raise FileExistsError(f"Fusion output already exists: {output_dir}")
    if not stage_a_reviewed:
        raise ValueError("Fusion training requires explicit Stage A review authorization")
    source_manifest = _load_mapping(analysis_dir / "run_manifest.json")
    if source_manifest.get("stage") != "score_separability":
        raise ValueError("Fusion source must be a score separability artifact")
    if source_manifest.get("partition") != "train":
        raise ValueError("Fusion training requires the train partition")
    table_path = analysis_dir / "separability_dataset.parquet"
    if not table_path.is_file():
        raise FileNotFoundError(f"Missing Stage A score table: {table_path}")
    table = pd.read_parquet(table_path)
    heads = tuple(sorted(str(value) for value in table["head"].unique()))
    if heads != ("logprob", "rubric"):
        raise ValueError("Fusion source must contain exactly logprob and rubric heads")

    all_predictions: list[pd.DataFrame] = []
    fold_metadata: dict[str, Any] = {}
    for head in heads:
        predictions, metadata = run_head_grouped_oof(
            table,
            head=head,
            n_splits=cv_splits,
            seed=cv_seed,
        )
        all_predictions.append(predictions)
        fold_metadata[head] = metadata
    oof_predictions = pd.concat(all_predictions, ignore_index=True)
    comparison = summarize_oof_predictions(
        oof_predictions,
        fpr_caps=FPR_CAPS,
        bootstrap_replicates=bootstrap_replicates,
        bootstrap_seed=bootstrap_seed,
    )
    threshold_selection = {
        head: {
            model: details["thresholds"]
            for model, details in head_report["models"].items()
        }
        for head, head_report in comparison["heads"].items()
    }

    output_dir.parent.mkdir(parents=True, exist_ok=True)
    prefix = f".{output_dir.name}.tmp-"
    with tempfile.TemporaryDirectory(prefix=prefix, dir=output_dir.parent) as name:
        temporary = Path(name)
        oof_predictions.to_parquet(temporary / "oof_predictions.parquet", index=False)
        write_json_atomic(temporary / "model_comparison.json", comparison)
        write_json_atomic(temporary / "threshold_selection.json", threshold_selection)
        figures = render_fusion_figures(
            oof_predictions,
            comparison,
            temporary / "figures",
        )
        write_json_atomic(
            temporary / "figure_manifest.json",
            _portable_figure_manifest(figures),
        )
        artifacts = [
            file_manifest_entry(path, temporary)
            for path in sorted(temporary.rglob("*"))
            if path.is_file() and path.name != "run_manifest.json"
        ]
        manifest = {
            "schema_version": 1,
            "stage": "score_fusion_oof",
            "partition": "train",
            "stage_a_reviewed": True,
            "created_at": utc_now_iso(),
            "source_stage_a": {
                "path": str(analysis_dir),
                "score_table": file_manifest_entry(table_path, analysis_dir),
                "run_manifest": file_manifest_entry(
                    analysis_dir / "run_manifest.json", analysis_dir
                ),
                "source": source_manifest.get("source"),
            },
            "cohort": "session_score_available",
            "features": {
                "x1": "query risk",
                "x2": "observed session risk",
                "early_turn_policy": "excluded_from_fusion_cohort",
            },
            "cross_validation": {
                "unit": "doc_id",
                "splits": cv_splits,
                "seed": cv_seed,
                "heads": fold_metadata,
            },
            "bootstrap": {
                "unit": "doc_id",
                "replicates": bootstrap_replicates,
                "seed": bootstrap_seed,
            },
            "artifacts": artifacts,
        }
        write_json_atomic(temporary / "run_manifest.json", manifest)
        temporary.replace(output_dir)
    return manifest


__all__ = ["run_train_score_analysis", "run_train_score_fusion"]
