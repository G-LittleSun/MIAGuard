from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from rag_mia_data.io_utils import (
    read_jsonl,
    sha256_file,
    utc_now_iso,
    write_jsonl_atomic,
)

from .schema import validate_query_record


@dataclass(frozen=True)
class QueryBankPaths:
    project_root: Path
    bank_id: str
    dataset_id: str

    @property
    def root(self) -> Path:
        return (
            self.project_root
            / "data"
            / "query_banks"
            / self.bank_id
            / self.dataset_id
        )

    @property
    def work(self) -> Path:
        return self.root / ".work"

    @property
    def manifest(self) -> Path:
        return self.root / "manifest.json"

    @property
    def documents(self) -> Path:
        return self.root / "documents.jsonl"

    @property
    def queries(self) -> Path:
        return self.root / "queries.jsonl"

    @property
    def failures(self) -> Path:
        return self.root / "generation_failures.jsonl"

    @property
    def repair_log(self) -> Path:
        return self.root / "ia_repair_log.jsonl"

    @property
    def repair_progress(self) -> Path:
        return self.work / "ia_repair_progress.jsonl"

    @property
    def repair_progress_archive(self) -> Path:
        return self.work / "repair-progress-archive"

    @property
    def lock(self) -> Path:
        return self.root / ".build.lock"

    def shard(self, doc_id: str) -> Path:
        name = hashlib.sha256(doc_id.encode("utf-8")).hexdigest()
        return self.work / f"{name}.jsonl"


class QueryBankLock:
    def __init__(self, paths: QueryBankPaths) -> None:
        self.paths = paths
        self.acquired = False

    def acquire(self) -> None:
        self.paths.root.mkdir(parents=True, exist_ok=True)
        try:
            with self.paths.lock.open("x", encoding="utf-8") as handle:
                json.dump(
                    {"pid": os.getpid(), "created_at": utc_now_iso()},
                    handle,
                    sort_keys=True,
                )
                handle.write("\n")
        except FileExistsError as error:
            raise FileExistsError(
                f"Query Bank is locked: {self.paths.lock}"
            ) from error
        self.acquired = True

    def release(self) -> None:
        if self.acquired and self.paths.lock.exists():
            self.paths.lock.unlink()
        self.acquired = False

    @staticmethod
    def force_remove(paths: QueryBankPaths) -> None:
        if paths.lock.exists():
            paths.lock.unlink()

    def __enter__(self) -> QueryBankLock:
        self.acquire()
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        self.release()


def write_document_shard(
    paths: QueryBankPaths,
    doc_id: str,
    rows: list[dict[str, Any]],
) -> None:
    if not rows:
        raise ValueError("Document shard must not be empty")
    if {str(row["doc_id"]) for row in rows} != {doc_id}:
        raise ValueError("Document shard contains a different doc_id")
    for row in rows:
        validate_query_record(row)
    write_jsonl_atomic(paths.shard(doc_id), rows)


def compact_query_bank(
    paths: QueryBankPaths,
    documents: list[dict[str, Any]],
) -> str:
    rows: list[dict[str, Any]] = []
    for shard in sorted(paths.work.glob("*.jsonl")):
        if re.fullmatch(r"[0-9a-f]{64}\.jsonl", shard.name) is None:
            continue
        rows.extend(read_jsonl(shard))
    for row in rows:
        validate_query_record(row)
    rows.sort(
        key=lambda row: (
            str(row["dataset_id"]),
            str(row["doc_id"]),
            str(row["attack_type"]),
            str(row["variant_type"]),
            int(row["query_index"]),
        )
    )
    query_ids = [str(row["query_id"]) for row in rows]
    if len(query_ids) != len(set(query_ids)):
        raise ValueError("Query Bank contains duplicate query_id values")
    ordered_documents = sorted(documents, key=lambda row: str(row["doc_id"]))
    write_jsonl_atomic(paths.documents, ordered_documents)
    write_jsonl_atomic(paths.queries, rows)
    return sha256_file(paths.queries)


@dataclass(frozen=True)
class QueryBank:
    bank_id: str
    dataset_id: str
    sha256: str
    records: tuple[dict[str, Any], ...]
    documents: tuple[dict[str, Any], ...]
    manifest: dict[str, Any]

    @classmethod
    def load(cls, paths: QueryBankPaths) -> QueryBank:
        with paths.manifest.open("r", encoding="utf-8") as handle:
            manifest = json.load(handle)
        if not isinstance(manifest, dict):
            raise ValueError("Query Bank manifest must be a mapping")
        if manifest.get("status") != "complete":
            raise ValueError("Frozen experiments require a complete Query Bank")
        digest = sha256_file(paths.queries)
        if digest != manifest.get("queries_sha256"):
            raise ValueError("Query Bank queries_sha256 does not match queries.jsonl")
        records = tuple(read_jsonl(paths.queries))
        for record in records:
            validate_query_record(record)
        documents = tuple(read_jsonl(paths.documents))
        return cls(
            bank_id=str(manifest["bank_id"]),
            dataset_id=str(manifest["dataset_id"]),
            sha256=digest,
            records=records,
            documents=documents,
            manifest=manifest,
        )
