from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from rag_mia_data.io_utils import write_json_atomic

from .storage import QueryBank


PARTITIONS = ("train", "validation", "test")
DEFAULT_COUNTS: Mapping[str, int] = {
    "train": 30,
    "validation": 10,
    "test": 10,
}


def _ordered_doc_ids(doc_ids: list[str], *, seed: int, label: int) -> list[str]:
    def key(doc_id: str) -> tuple[str, str]:
        digest = hashlib.sha256(
            f"{seed}|{label}|{doc_id}".encode("utf-8")
        ).hexdigest()
        return digest, doc_id

    return sorted(doc_ids, key=key)


def _document_labels(bank: QueryBank) -> dict[str, int]:
    labels: dict[str, int] = {}
    for document in bank.documents:
        doc_id = str(document["doc_id"])
        label = int(document["membership_label"])
        if label not in (0, 1):
            raise ValueError(f"Invalid membership_label for document {doc_id}")
        if doc_id in labels:
            raise ValueError(f"Duplicate document doc_id: {doc_id}")
        if str(document.get("dataset_id")) != bank.dataset_id:
            raise ValueError(f"Document dataset_id mismatch for {doc_id}")
        labels[doc_id] = label

    for record in bank.records:
        doc_id = str(record["doc_id"])
        if doc_id not in labels:
            raise ValueError(f"Query record references unknown doc_id: {doc_id}")
        if int(record["membership_label"]) != labels[doc_id]:
            raise ValueError(
                f"Query record membership_label disagrees with document {doc_id}"
            )
    return labels


def build_threshold_split(
    bank: QueryBank,
    *,
    split_id: str,
    seed: int,
    counts_per_class: Mapping[str, int] = DEFAULT_COUNTS,
) -> dict[str, Any]:
    """Build a deterministic, document-level split for threshold experiments."""
    if not split_id.strip():
        raise ValueError("split_id must not be empty")
    if set(counts_per_class) != set(PARTITIONS):
        raise ValueError(f"counts_per_class must contain exactly {PARTITIONS}")
    if any(int(counts_per_class[name]) <= 0 for name in PARTITIONS):
        raise ValueError("Every partition count must be positive")

    labels = _document_labels(bank)
    required = sum(int(counts_per_class[name]) for name in PARTITIONS)
    by_label = {
        label: _ordered_doc_ids(
            [doc_id for doc_id, value in labels.items() if value == label],
            seed=seed,
            label=label,
        )
        for label in (0, 1)
    }
    for label, doc_ids in by_label.items():
        if len(doc_ids) != required:
            name = "member" if label == 1 else "nonmember"
            raise ValueError(
                f"Expected exactly {required} {name} documents, found {len(doc_ids)}"
            )

    accepted_by_doc: dict[str, int] = {doc_id: 0 for doc_id in labels}
    for record in bank.records:
        if record.get("validation", {}).get("status") == "accepted":
            accepted_by_doc[str(record["doc_id"])] += 1

    partitions: dict[str, Any] = {}
    offset = 0
    for name in PARTITIONS:
        count = int(counts_per_class[name])
        members = by_label[1][offset : offset + count]
        nonmembers = by_label[0][offset : offset + count]
        doc_ids = sorted([*members, *nonmembers])
        partitions[name] = {
            "doc_ids": doc_ids,
            "member_doc_ids": sorted(members),
            "nonmember_doc_ids": sorted(nonmembers),
            "document_count": len(doc_ids),
            "accepted_query_count": sum(accepted_by_doc[doc_id] for doc_id in doc_ids),
        }
        offset += count

    split = {
        "schema_version": 1,
        "split_id": split_id,
        "seed": int(seed),
        "query_bank": {
            "bank_id": bank.bank_id,
            "dataset_id": bank.dataset_id,
            "queries_sha256": bank.sha256,
        },
        "assignment_unit": "doc_id",
        "partitions": partitions,
    }
    validate_threshold_split(split, bank)
    return split


def derive_threshold_split_from_parent(
    bank: QueryBank,
    parent_split: Mapping[str, Any],
    *,
    split_id: str,
) -> dict[str, Any]:
    """Rebind a valid document assignment to a derived Query Bank."""
    if not split_id.strip():
        raise ValueError("split_id must not be empty")
    parent_partitions = parent_split.get("partitions")
    if not isinstance(parent_partitions, Mapping) or set(parent_partitions) != set(PARTITIONS):
        raise ValueError("Parent threshold split must contain every partition")
    parent_source = parent_split.get("query_bank")
    if not isinstance(parent_source, Mapping):
        raise ValueError("Parent threshold split query_bank must be a mapping")

    labels = _document_labels(bank)
    accepted_by_doc: dict[str, int] = {doc_id: 0 for doc_id in labels}
    for record in bank.records:
        if record.get("validation", {}).get("status") == "accepted":
            accepted_by_doc[str(record["doc_id"])] += 1

    partitions: dict[str, Any] = {}
    for partition in PARTITIONS:
        parent_row = parent_partitions[partition]
        if not isinstance(parent_row, Mapping):
            raise ValueError(f"Parent partition {partition} must be a mapping")
        doc_ids = [str(value) for value in parent_row.get("doc_ids", [])]
        members = [str(value) for value in parent_row.get("member_doc_ids", [])]
        nonmembers = [str(value) for value in parent_row.get("nonmember_doc_ids", [])]
        if set(doc_ids) != set(members).union(nonmembers):
            raise ValueError(f"Parent partition {partition} doc_id lists disagree")
        if not set(doc_ids).issubset(labels):
            raise ValueError(f"Parent partition {partition} references a document missing from v2")
        partitions[partition] = {
            "doc_ids": doc_ids,
            "member_doc_ids": members,
            "nonmember_doc_ids": nonmembers,
            "document_count": len(doc_ids),
            "accepted_query_count": sum(accepted_by_doc[doc_id] for doc_id in doc_ids),
        }

    split = {
        "schema_version": 1,
        "split_id": split_id,
        "seed": int(parent_split.get("seed", 0)),
        "query_bank": {
            "bank_id": bank.bank_id,
            "dataset_id": bank.dataset_id,
            "queries_sha256": bank.sha256,
        },
        "assignment_unit": "doc_id",
        "derived_from_split_id": str(parent_split.get("split_id", "")),
        "parent_query_bank": dict(parent_source),
        "partitions": partitions,
    }
    validate_threshold_split(split, bank)
    return split


def validate_threshold_split(split: Mapping[str, Any], bank: QueryBank) -> None:
    if int(split.get("schema_version", -1)) != 1:
        raise ValueError("Unsupported threshold split schema_version")
    source = split.get("query_bank")
    if not isinstance(source, Mapping):
        raise ValueError("threshold split query_bank must be a mapping")
    expected_source = {
        "bank_id": bank.bank_id,
        "dataset_id": bank.dataset_id,
        "queries_sha256": bank.sha256,
    }
    if dict(source) != expected_source:
        raise ValueError("Threshold split does not match the loaded Query Bank")
    if split.get("assignment_unit") != "doc_id":
        raise ValueError("Threshold split assignment_unit must be doc_id")

    labels = _document_labels(bank)
    partitions = split.get("partitions")
    if not isinstance(partitions, Mapping) or set(partitions) != set(PARTITIONS):
        raise ValueError(f"Threshold split must contain exactly {PARTITIONS}")

    seen: set[str] = set()
    accepted_by_doc: dict[str, int] = {doc_id: 0 for doc_id in labels}
    for record in bank.records:
        if record.get("validation", {}).get("status") == "accepted":
            accepted_by_doc[str(record["doc_id"])] += 1
    for name in PARTITIONS:
        row = partitions[name]
        if not isinstance(row, Mapping):
            raise ValueError(f"Partition {name} must be a mapping")
        doc_ids = [str(value) for value in row.get("doc_ids", [])]
        members = [str(value) for value in row.get("member_doc_ids", [])]
        nonmembers = [str(value) for value in row.get("nonmember_doc_ids", [])]
        if len(doc_ids) != len(set(doc_ids)):
            raise ValueError(f"Partition {name} contains duplicate doc_id values")
        if seen.intersection(doc_ids):
            raise ValueError("Threshold split partitions overlap")
        if set(doc_ids) != set(members).union(nonmembers):
            raise ValueError(f"Partition {name} doc_id lists disagree")
        if set(members).intersection(nonmembers):
            raise ValueError(f"Partition {name} member classes overlap")
        if any(labels.get(doc_id) != 1 for doc_id in members):
            raise ValueError(f"Partition {name} has an invalid member doc_id")
        if any(labels.get(doc_id) != 0 for doc_id in nonmembers):
            raise ValueError(f"Partition {name} has an invalid nonmember doc_id")
        expected_count = int(DEFAULT_COUNTS[name])
        if len(members) != expected_count:
            raise ValueError(
                f"Partition {name} must contain exactly {expected_count} member documents"
            )
        if len(nonmembers) != expected_count:
            raise ValueError(
                f"Partition {name} must contain exactly {expected_count} nonmember documents"
            )
        if len(members) != len(nonmembers):
            raise ValueError(f"Partition {name} is not membership balanced")
        if int(row.get("document_count", -1)) != len(doc_ids):
            raise ValueError(f"Partition {name} document_count is inconsistent")
        expected_queries = sum(accepted_by_doc[doc_id] for doc_id in doc_ids)
        if int(row.get("accepted_query_count", -1)) != expected_queries:
            raise ValueError(
                f"Partition {name} accepted_query_count is inconsistent"
            )
        seen.update(doc_ids)
    if seen != set(labels):
        raise ValueError("Threshold split does not cover every Query Bank document")


def freeze_threshold_split(split: Mapping[str, Any], output_path: Path) -> None:
    if output_path.exists():
        raise FileExistsError(f"Threshold split already exists: {output_path}")
    write_json_atomic(output_path, dict(split))


def load_threshold_split(path: str | Path, bank: QueryBank | None = None) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("Threshold split must be a mapping")
    if bank is not None:
        validate_threshold_split(value, bank)
    return value


def partition_doc_ids(
    split: Mapping[str, Any], partition: str
) -> frozenset[str]:
    if partition not in PARTITIONS:
        raise ValueError(f"Unsupported partition: {partition}")
    partitions = split.get("partitions")
    if not isinstance(partitions, Mapping) or not isinstance(
        partitions.get(partition), Mapping
    ):
        raise ValueError(f"Missing threshold split partition: {partition}")
    return frozenset(str(value) for value in partitions[partition].get("doc_ids", []))
