from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from rag_mia_data.io_utils import utc_now_iso, write_json_atomic

from .data import load_run_documents


def load_split_spec(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        value = yaml.safe_load(handle)
    if not isinstance(value, dict):
        raise ValueError("Two-stage split specification must be a YAML mapping")
    required = {"split_id", "source_run_id", "dataset_id", "partitions"}
    if not required.issubset(value):
        raise ValueError(f"Split specification is missing: {sorted(required - set(value))}")
    return value


def build_split_manifest(
    project_root: Path,
    spec: dict[str, Any],
) -> dict[str, Any]:
    partitions = spec["partitions"]
    if not isinstance(partitions, dict) or set(partitions) != {
        "development",
        "validation",
        "test",
    }:
        raise ValueError("Split partitions must be development, validation, and test")
    documents = load_run_documents(
        project_root,
        str(spec["source_run_id"]),
        str(spec["dataset_id"]),
    )
    by_label = {
        label: [row for row in documents if int(row["membership_label"]) == label]
        for label in (0, 1)
    }
    output_partitions: dict[str, Any] = {}
    all_ids: list[str] = []
    for name in ("development", "validation", "test"):
        selection = partitions[name]
        if not isinstance(selection, dict):
            raise ValueError(f"Invalid split partition: {name}")
        start = int(selection["start_per_class"])
        count = int(selection["count_per_class"])
        if start < 0 or count <= 0:
            raise ValueError("Split starts must be non-negative and counts positive")
        member_ids = [
            str(row["doc_id"]) for row in by_label[1][start : start + count]
        ]
        nonmember_ids = [
            str(row["doc_id"]) for row in by_label[0][start : start + count]
        ]
        if len(member_ids) != count or len(nonmember_ids) != count:
            raise ValueError(f"Not enough documents for split partition: {name}")
        partition_ids = member_ids + nonmember_ids
        overlap = set(all_ids).intersection(partition_ids)
        if overlap:
            raise ValueError(f"Split partitions overlap: {sorted(overlap)[:3]}")
        all_ids.extend(partition_ids)
        output_partitions[name] = {
            "member_doc_ids": member_ids,
            "nonmember_doc_ids": nonmember_ids,
            "member_count": len(member_ids),
            "nonmember_count": len(nonmember_ids),
        }
    return {
        "schema_version": 1,
        "split_id": str(spec["split_id"]),
        "created_at": utc_now_iso(),
        "source_run_id": str(spec["source_run_id"]),
        "dataset_id": str(spec["dataset_id"]),
        "grouping_unit": "target_document",
        "current_development_scope": str(spec.get("current_development_scope", "")),
        "label_semantics": {
            "traffic_origin": "attack_generated or benign_generated",
            "observable_intent": "benign, ambiguous, or explicit_attack",
            "session_label": "benign or attack type",
        },
        "partitions": output_partitions,
    }


def freeze_split(
    project_root: Path,
    spec_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    if output_path.exists():
        raise FileExistsError(f"Frozen split already exists: {output_path}")
    manifest = build_split_manifest(project_root, load_split_spec(spec_path))
    write_json_atomic(output_path, manifest)
    return manifest


__all__ = ["build_split_manifest", "freeze_split", "load_split_spec"]
