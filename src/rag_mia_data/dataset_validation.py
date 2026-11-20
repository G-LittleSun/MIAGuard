from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .dataset_catalog import CatalogEntry
from .io_utils import read_jsonl, write_json_atomic


_TEACHER_ADAPTER = "teacher_json_array"
_T2_ADAPTER = "t2ranking_existing_jsonl"
_NORMALIZED_KEYS = {
    "doc_id",
    "dataset_id",
    "text",
    "language",
    "membership_label",
    "source_partition",
    "source_index",
    "metadata",
}


def _resolve_project_path(
    project_root: Path, configured_path: str | Path, label: str
) -> Path:
    root = Path(project_root).resolve()
    if not isinstance(configured_path, (str, Path)) or not str(configured_path):
        raise ValueError(f"{label} must be a nonempty project path")
    path = Path(configured_path)
    resolved = (path if path.is_absolute() else root / path).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as error:
        raise ValueError(f"{label} must resolve inside the project root") from error
    return resolved


def _resolve_normalized_file(
    project_root: Path, output_dir: Path, file_name: str, dataset_id: str
) -> Path:
    path = output_dir / file_name
    if path.is_symlink():
        raise ValueError(f"{dataset_id} normalized file must not be a symlink: {path}")
    return _resolve_project_path(
        project_root, path, f"{dataset_id} normalized {file_name}"
    )


def load_string_array(path: Path) -> list[str]:
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"Missing JSON string array: {path}")
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, list):
        raise ValueError(f"JSON value must be a top-level array: {path}")
    if any(not isinstance(item, str) for item in value):
        raise ValueError(f"JSON array values must all be strings: {path}")
    return value


def _summary(
    entry: CatalogEntry, corpus_count: int, member_count: int, nonmember_count: int
) -> dict[str, Any]:
    return {
        "dataset_id": entry.dataset_id,
        "status": "valid",
        "corpus_count": corpus_count,
        "member_count": member_count,
        "nonmember_count": nonmember_count,
    }


def _validate_teacher_raw(
    entry: CatalogEntry, project_root: Path
) -> dict[str, Any]:
    files = entry.descriptor["files"]
    corpus = load_string_array(
        _resolve_project_path(
            project_root,
            files["processed_corpus"]["path"],
            f"{entry.dataset_id} processed_corpus",
        )
    )
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

    corpus_count = files["processed_corpus"]["record_count"]
    member_count = files["target_member"]["record_count"]
    nonmember_count = files["target_nonmember"]["record_count"]
    for name, rows, expected in (
        ("processed_corpus", corpus, corpus_count),
        ("target_member", members, member_count),
        ("target_nonmember", nonmembers, nonmember_count),
    ):
        if len(rows) != expected:
            raise ValueError(
                f"{entry.dataset_id} {name} count {len(rows)} does not match "
                f"descriptor count {expected}"
            )
    if members != corpus[:member_count]:
        raise ValueError(
            f"{entry.dataset_id} target_member must equal the corpus prefix"
        )
    if nonmembers != corpus[member_count : member_count + nonmember_count]:
        raise ValueError(
            f"{entry.dataset_id} target_nonmember must equal the immediately "
            "following corpus slice"
        )
    if set(members) & set(nonmembers):
        raise ValueError(f"{entry.dataset_id} member and nonmember texts must be disjoint")
    return _summary(entry, corpus_count, member_count, nonmember_count)


def _validate_t2_partition(
    entry: CatalogEntry,
    rows: list[dict[str, Any]],
    partition: str,
    expected_count: int,
    expected_label: int,
) -> set[str]:
    if len(rows) != expected_count:
        raise ValueError(
            f"{entry.dataset_id} {partition} count {len(rows)} does not match "
            f"descriptor count {expected_count}"
        )
    doc_ids: set[str] = set()
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError(
                f"{entry.dataset_id} {partition} row {index} must be an object"
            )
        label = row.get("membership_label")
        if type(label) is not int or label != expected_label:
            raise ValueError(
                f"{entry.dataset_id} {partition} row {index} has wrong membership_label"
            )
        doc_id = row.get("doc_id")
        if not isinstance(doc_id, str) or not doc_id.strip():
            raise ValueError(
                f"{entry.dataset_id} {partition} row {index} has an empty doc_id"
            )
        if doc_id in doc_ids:
            raise ValueError(
                f"{entry.dataset_id} {partition} contains duplicate doc_id {doc_id!r}"
            )
        doc_ids.add(doc_id)
    return doc_ids


def _validate_t2_raw(entry: CatalogEntry, project_root: Path) -> dict[str, Any]:
    files = entry.descriptor["files"]
    _resolve_project_path(
        project_root,
        files["processed_corpus"]["path"],
        f"{entry.dataset_id} processed_corpus",
    )
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
    members = list(read_jsonl(member_path))
    nonmembers = list(read_jsonl(nonmember_path))
    member_count = files["target_member"]["record_count"]
    nonmember_count = files["target_nonmember"]["record_count"]
    member_ids = _validate_t2_partition(
        entry, members, "target_member", member_count, 1
    )
    nonmember_ids = _validate_t2_partition(
        entry, nonmembers, "target_nonmember", nonmember_count, 0
    )
    if member_ids & nonmember_ids:
        raise ValueError(f"{entry.dataset_id} member and nonmember IDs must be disjoint")
    return _summary(
        entry,
        files["processed_corpus"]["record_count"],
        member_count,
        nonmember_count,
    )


def validate_raw_dataset(
    entry: CatalogEntry, project_root: Path
) -> dict[str, Any]:
    adapter = entry.config["adapter"]
    if adapter == _TEACHER_ADAPTER:
        return _validate_teacher_raw(entry, project_root)
    if adapter == _T2_ADAPTER:
        return _validate_t2_raw(entry, project_root)
    raise ValueError(f"Unsupported dataset adapter: {adapter!r}")


def _validate_normalized_partition(
    entry: CatalogEntry,
    rows: list[dict[str, Any]],
    partition: str,
    expected_count: int,
    expected_label: int,
) -> set[str]:
    if len(rows) != expected_count:
        raise ValueError(
            f"{entry.dataset_id} normalized {partition} count {len(rows)} does not "
            f"match descriptor count {expected_count}"
        )
    doc_ids: set[str] = set()
    for index, row in enumerate(rows):
        actual_keys = set(row)
        if actual_keys != _NORMALIZED_KEYS:
            missing = sorted(_NORMALIZED_KEYS - actual_keys)
            unexpected = sorted(str(key) for key in actual_keys - _NORMALIZED_KEYS)
            raise ValueError(
                f"{entry.dataset_id} normalized {partition} row {index} has invalid "
                f"keys: missing={missing}, unexpected={unexpected}"
            )
        doc_id = row["doc_id"]
        if not isinstance(doc_id, str) or not doc_id.strip():
            raise ValueError(
                f"{entry.dataset_id} normalized {partition} row {index} has an empty doc_id"
            )
        if doc_id in doc_ids:
            raise ValueError(
                f"{entry.dataset_id} normalized {partition} contains duplicate "
                f"doc_id {doc_id!r}"
            )
        doc_ids.add(doc_id)
        if row["dataset_id"] != entry.dataset_id:
            raise ValueError(
                f"{entry.dataset_id} normalized {partition} row {index} has wrong dataset_id"
            )
        if not isinstance(row["text"], str) or not row["text"].strip():
            raise ValueError(
                f"{entry.dataset_id} normalized {partition} row {index} has empty text"
            )
        label = row["membership_label"]
        if type(label) is not int or label != expected_label:
            raise ValueError(
                f"{entry.dataset_id} normalized {partition} row {index} has wrong "
                "membership_label"
            )
        if row["source_partition"] != partition:
            raise ValueError(
                f"{entry.dataset_id} normalized {partition} row {index} has wrong "
                "source_partition"
            )
        source_index = row["source_index"]
        if isinstance(source_index, bool) or not isinstance(source_index, int) or source_index < 0:
            raise ValueError(
                f"{entry.dataset_id} normalized {partition} row {index} has invalid "
                "source_index"
            )
        if not isinstance(row["metadata"], dict):
            raise ValueError(
                f"{entry.dataset_id} normalized {partition} row {index} metadata "
                "must be an object"
            )
    return doc_ids


def validate_normalized_dataset(
    entry: CatalogEntry, project_root: Path
) -> dict[str, Any]:
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
    members = list(read_jsonl(member_path))
    nonmembers = list(read_jsonl(nonmember_path))
    files = entry.descriptor["files"]
    member_count = files["target_member"]["record_count"]
    nonmember_count = files["target_nonmember"]["record_count"]
    member_ids = _validate_normalized_partition(
        entry, members, "target_member", member_count, 1
    )
    nonmember_ids = _validate_normalized_partition(
        entry, nonmembers, "target_nonmember", nonmember_count, 0
    )
    if member_ids & nonmember_ids:
        raise ValueError(
            f"{entry.dataset_id} normalized member and nonmember IDs must be disjoint"
        )
    return {
        "dataset_id": entry.dataset_id,
        "status": "valid",
        "member_count": member_count,
        "nonmember_count": nonmember_count,
    }


def validate_and_record(entry: CatalogEntry, project_root: Path) -> dict[str, Any]:
    raw_summary = validate_raw_dataset(entry, project_root)
    validate_normalized_dataset(entry, project_root)
    manifest_path = _resolve_project_path(
        project_root,
        f"data/manifests/datasets/{entry.dataset_id}.validation.json",
        f"{entry.dataset_id} validation manifest",
    )
    write_json_atomic(manifest_path, raw_summary)
    return raw_summary


__all__ = [
    "load_string_array",
    "validate_and_record",
    "validate_normalized_dataset",
    "validate_raw_dataset",
]
