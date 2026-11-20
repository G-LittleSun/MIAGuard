from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import faiss
import numpy as np

from rag_mia_data.io_utils import read_jsonl, utc_now_iso, write_json_atomic, write_jsonl_atomic

from .config import AttackConfig
from .data import load_run_documents, vector_store_path
from .evidence_access import parent_doc_id
from .model_client import ModelClient, create_model_client


class UnifiedVectorStore:
    def __init__(
        self,
        index: faiss.Index,
        documents: list[dict[str, Any]],
        embedding_model: str,
        client: ModelClient,
    ) -> None:
        self.index = index
        self.documents = documents
        self.embedding_model = embedding_model
        self.client = client

    @classmethod
    def load(cls, path: Path, client: ModelClient) -> "UnifiedVectorStore":
        with (path / "manifest.json").open("r", encoding="utf-8") as handle:
            manifest = json.load(handle)
        documents = list(read_jsonl(path / "documents.jsonl"))
        index = faiss.read_index(str(path / "index.faiss"))
        if index.ntotal != len(documents) or manifest["document_count"] != len(documents):
            raise ValueError("Vector index and document metadata counts differ")
        return cls(index, documents, str(manifest["embedding_model"]), client)

    def search(
        self,
        query: str,
        top_k: int,
        *,
        allowed_doc_ids: set[str] | frozenset[str] | None = None,
        excluded_parent_ids: frozenset[str] = frozenset(),
    ) -> list[dict[str, Any]]:
        hits, _ = self.search_with_audit(
            query, top_k, allowed_doc_ids=allowed_doc_ids,
            excluded_parent_ids=excluded_parent_ids,
        )
        return hits

    def search_with_audit(
        self,
        query: str,
        top_k: int,
        *,
        allowed_doc_ids: set[str] | frozenset[str] | None = None,
        excluded_parent_ids: frozenset[str] = frozenset(),
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        if not query.strip():
            raise ValueError("Search query must not be blank")
        if top_k <= 0:
            raise ValueError("top_k must be positive")
        if allowed_doc_ids is not None and any(not isinstance(item, str) or not item for item in allowed_doc_ids):
            raise ValueError("allowed_doc_ids must contain non-blank strings")
        if any(not isinstance(item, str) or not item for item in excluded_parent_ids):
            raise ValueError("excluded_parent_ids must contain non-blank strings")
        eligible = sum(
            (allowed_doc_ids is None or str(document["doc_id"]) in allowed_doc_ids)
            and parent_doc_id(document) not in excluded_parent_ids
            for document in self.documents
        )
        audit: dict[str, Any] = {
            "requested_top_k": top_k,
            "allowed_scope_size": None if allowed_doc_ids is None else len(allowed_doc_ids),
            "excluded_parent_count": len(excluded_parent_ids),
            "eligible_document_count": eligible,
            "candidate_before_ids": [],
            "returned_doc_ids": [],
            "candidate_search_counts": [],
            "refill_rounds": 0,
            "shortage_reason": None,
        }
        if eligible == 0:
            audit["shortage_reason"] = "no_allowed_evidence"
            return [], audit
        vector = np.asarray(self.client.embed(self.embedding_model, [query]), dtype="float32")
        faiss.normalize_L2(vector)
        count = min(top_k, len(self.documents))
        while True:
            scores, positions = self.index.search(vector, count)
            audit["candidate_search_counts"].append(count)
            if len(audit["candidate_search_counts"]) == 1:
                audit["candidate_before_ids"] = [
                    str(self.documents[int(position)]["doc_id"])
                    for position in positions[0] if position >= 0
                ]
            hits: list[dict[str, Any]] = []
            seen: set[str] = set()
            for score, position in zip(scores[0], positions[0]):
                if position < 0:
                    continue
                document = self.documents[int(position)]
                doc_id = str(document["doc_id"])
                if allowed_doc_ids is not None and doc_id not in allowed_doc_ids:
                    continue
                if parent_doc_id(document) in excluded_parent_ids or doc_id in seen:
                    continue
                seen.add(doc_id)
                hits.append({"score": float(score), "document": document})
                if len(hits) == top_k:
                    break
            if len(hits) == top_k or count == len(self.documents):
                break
            count = min(len(self.documents), max(count + 1, count * 2))
            audit["refill_rounds"] += 1
        audit["returned_doc_ids"] = [str(hit["document"]["doc_id"]) for hit in hits]
        if len(hits) < top_k:
            audit["shortage_reason"] = (
                "insufficient_allowed_documents" if eligible < top_k else "index_shortfall"
            )
        return hits, audit


def build_vector_store(
    project_root: Path,
    run_id: str,
    dataset_id: str,
    config: AttackConfig,
) -> dict[str, Any]:
    documents = [
        row
        for row in load_run_documents(project_root, run_id, dataset_id)
        if int(row["membership_label"]) == 1
    ]
    if not documents:
        raise ValueError("A Target vector store requires at least one member document")
    client = create_model_client(config, project_root)
    vectors: list[list[float]] = []
    for start in range(0, len(documents), config.embedding_batch_size):
        batch = documents[start : start + config.embedding_batch_size]
        vectors.extend(client.embed(config.embedding_model, [str(row["text"]) for row in batch]))
    matrix = np.asarray(vectors, dtype="float32")
    if matrix.ndim != 2 or matrix.shape[0] != len(documents):
        raise ValueError("Embedding matrix has an invalid shape")
    faiss.normalize_L2(matrix)
    index = faiss.IndexFlatIP(int(matrix.shape[1]))
    index.add(matrix)

    output = vector_store_path(project_root, run_id, dataset_id)
    output.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(output / "index.faiss"))
    write_jsonl_atomic(output / "documents.jsonl", documents)
    manifest = {
        "backend": "faiss.IndexFlatIP",
        "created_at": utc_now_iso(),
        "dataset_id": dataset_id,
        "dimension": int(matrix.shape[1]),
        "document_count": len(documents),
        "embedding_model": config.embedding_model,
        "embedding_backend": config.embedding_backend,
        "run_id": run_id,
        "source_membership_label": 1,
    }
    write_json_atomic(output / "manifest.json", manifest)
    return {**manifest, "path": str(output)}


__all__ = ["UnifiedVectorStore", "build_vector_store"]
