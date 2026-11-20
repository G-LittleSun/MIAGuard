from __future__ import annotations

from pathlib import Path
from typing import Any

from .dataset_catalog import CatalogEntry
from .dataset_validation import (
    _resolve_normalized_file,
    _resolve_project_path,
    load_string_array,
    validate_normalized_dataset,
    validate_raw_dataset,
)
from .io_utils import read_jsonl, write_jsonl_atomic


_TEACHER_ADAPTER = "teacher_json_array"
_T2_ADAPTER = "t2ranking_existing_jsonl"


def _teacher_row(
    entry: CatalogEntry,
    text: str,
    language: str,
    label: int,
    partition: str,
    source_index: int,
) -> dict[str, Any]:
    return {
        "doc_id": f"{entry.dataset_id}_teacher_{source_index:08d}",
        "dataset_id": entry.dataset_id,
        "text": text,
        "language": language,
        "membership_label": label,
        "source_partition": partition,
        "source_index": source_index,
        "metadata": {},
    }


def _normalize_teacher(
    entry: CatalogEntry, project_root: Path
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    files = entry.descriptor["files"]
    members = load_string_array(
        _resolve_project_path(
            project_root,
            files["target_member"]["path"],
            f"{entry.dataset_id} target_member",
        )
    )
    nonmembers = load_string_array(
        _resolve_project_path(
            project_root,
            files["target_nonmember"]["path"],
            f"{entry.dataset_id} target_nonmember",
        )
    )
    language = entry.descriptor["language"][0]
    member_rows = [
        _teacher_row(entry, text, language, 1, "target_member", index)
        for index, text in enumerate(members)
    ]
    nonmember_rows = [
        _teacher_row(
            entry,
            text,
            language,
            0,
            "target_nonmember",
            len(members) + index,
        )
        for index, text in enumerate(nonmembers)
    ]
    return member_rows, nonmember_rows


def _project_t2_row(
    entry: CatalogEntry, row: dict[str, Any], label: int, partition: str
) -> dict[str, Any]:
    source_doc_id = row["source_doc_id"]
    return {
        "doc_id": row["doc_id"],
        "dataset_id": entry.dataset_id,
        "text": row["text"],
        "language": "zh",
        "membership_label": label,
        "source_partition": partition,
        "source_index": int(source_doc_id),
        "metadata": {
            "source_doc_id": source_doc_id,
            "duplicate_group_id": row["duplicate_group_id"],
        },
    }


def _normalize_t2(
    entry: CatalogEntry, project_root: Path
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    member_path = _resolve_project_path(
        project_root,
        entry.config["source_files"]["target_member"],
        f"{entry.dataset_id} target_member source",
    )
    nonmember_path = _resolve_project_path(
        project_root,
        entry.config["source_files"]["target_nonmember"],
        f"{entry.dataset_id} target_nonmember source",
    )
    members = sorted(read_jsonl(member_path), key=lambda row: row["doc_id"])
    nonmembers = sorted(read_jsonl(nonmember_path), key=lambda row: row["doc_id"])
    return (
        [_project_t2_row(entry, row, 1, "target_member") for row in members],
        [
            _project_t2_row(entry, row, 0, "target_nonmember")
            for row in nonmembers
        ],
    )


def normalize_dataset(
    entry: CatalogEntry, project_root: Path
) -> dict[str, int]:
    validate_raw_dataset(entry, project_root)
    adapter = entry.config["adapter"]
    if adapter == _TEACHER_ADAPTER:
        members, nonmembers = _normalize_teacher(entry, project_root)
    elif adapter == _T2_ADAPTER:
        members, nonmembers = _normalize_t2(entry, project_root)
    else:
        raise ValueError(f"Unsupported dataset adapter: {adapter!r}")

    output_dir = _resolve_project_path(
        project_root,
        entry.config["normalized_documents_dir"],
        f"{entry.dataset_id} normalized_documents_dir",
    )
    member_path = _resolve_normalized_file(
        project_root, output_dir, "member_docs.jsonl", entry.dataset_id
    )
    nonmember_path = _resolve_normalized_file(
        project_root, output_dir, "nonmember_docs.jsonl", entry.dataset_id
    )
    write_jsonl_atomic(member_path, members)
    write_jsonl_atomic(nonmember_path, nonmembers)
    summary = validate_normalized_dataset(entry, project_root)
    return {
        "member_count": summary["member_count"],
        "nonmember_count": summary["nonmember_count"],
    }


__all__ = ["normalize_dataset"]
