from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rag_mia_data.io_utils import read_jsonl


def load_run_manifest(project_root: Path, run_id: str) -> dict[str, Any]:
    path = project_root / "data" / "runs" / run_id / "run_manifest.json"
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"Invalid run manifest: {path}")
    return value


def load_run_documents(project_root: Path, run_id: str, dataset_id: str) -> list[dict[str, Any]]:
    manifest = load_run_manifest(project_root, run_id)
    try:
        relative_path = manifest["dataset_runs"][dataset_id]["target_docs_path"]
    except KeyError as error:
        raise ValueError(f"Dataset {dataset_id!r} is not part of run {run_id!r}") from error
    path = project_root / "data" / "runs" / run_id / relative_path
    return list(read_jsonl(path))


def load_attack_documents(
    project_root: Path,
    run_id: str,
    dataset_id: str,
    attack: str,
    limit_per_class: int | None = None,
) -> list[dict[str, Any]]:
    manifest = load_run_manifest(project_root, run_id)
    try:
        selection = manifest["dataset_runs"][dataset_id]["attacks"][attack]
    except KeyError as error:
        raise ValueError(
            f"Attack {attack!r} is not prepared for dataset {dataset_id!r}"
        ) from error
    documents = {row["doc_id"]: row for row in load_run_documents(project_root, run_id, dataset_id)}
    member_ids = list(selection["member_ids"])
    nonmember_ids = list(selection["nonmember_ids"])
    if limit_per_class is not None:
        if limit_per_class <= 0:
            raise ValueError("limit_per_class must be positive")
        member_ids = member_ids[:limit_per_class]
        nonmember_ids = nonmember_ids[:limit_per_class]
    requested = member_ids + nonmember_ids
    missing = [doc_id for doc_id in requested if doc_id not in documents]
    if missing:
        raise ValueError(f"Run candidate documents are missing IDs: {missing[:3]}")
    return [documents[doc_id] for doc_id in requested]


def vector_store_path(project_root: Path, run_id: str, dataset_id: str) -> Path:
    return project_root / "data" / "vector_stores" / run_id / dataset_id


def attack_result_path(project_root: Path, run_id: str, dataset_id: str, attack: str) -> Path:
    return project_root / "data" / "attack_results" / run_id / dataset_id / attack


def resume_attack_results(
    output: Path,
    documents: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    results_path = output / "results.jsonl"
    if not results_path.exists():
        return [], documents
    rows = list(read_jsonl(results_path))
    completed_ids = [str(row.get("doc_id", "")) for row in rows]
    requested_ids = [str(document["doc_id"]) for document in documents]
    if completed_ids != requested_ids[: len(completed_ids)]:
        raise ValueError(
            "Existing attack results are not a prefix of the requested documents"
        )
    return rows, documents[len(rows) :]


__all__ = [
    "attack_result_path",
    "load_attack_documents",
    "load_run_documents",
    "load_run_manifest",
    "resume_attack_results",
    "vector_store_path",
]
