from __future__ import annotations

import faiss
import numpy as np

from miaguard.vector_store import UnifiedVectorStore


class Embedder:
    def __init__(self) -> None:
        self.calls = 0

    def embed(self, model: str, texts: list[str]):
        self.calls += 1
        return [[1.0, 0.0]]


def store() -> tuple[UnifiedVectorStore, Embedder]:
    values = np.asarray([[1, 0], [.98, .2], [.9, .3], [.8, .4], [.7, .5]], dtype="float32")
    faiss.normalize_L2(values)
    index = faiss.IndexFlatIP(2)
    index.add(values)
    documents = [
        {"doc_id": "a1", "parent_doc_id": "a", "text": "first", "membership_label": 1},
        {"doc_id": "a2", "parent_doc_id": "a", "text": "second", "membership_label": 1},
        {"doc_id": "b", "parent_doc_id": "b", "text": "third"},
        {"doc_id": "c", "parent_doc_id": "c", "text": "fourth"},
        {"doc_id": "d", "parent_doc_id": "d", "text": "fifth"},
    ]
    client = Embedder()
    return UnifiedVectorStore(index, documents, "fake", client), client


def ids(hits):
    return [hit["document"]["doc_id"] for hit in hits]


def test_excluded_parent_filters_every_chunk_and_refills() -> None:
    index, client = store()
    hits, audit = index.search_with_audit("q", 2, allowed_doc_ids={"a1", "a2", "b", "c"}, excluded_parent_ids=frozenset({"a"}))
    assert ids(hits) == ["b", "c"]
    assert audit["candidate_before_ids"] == ["a1", "a2"]
    assert audit["returned_doc_ids"] == ["b", "c"]
    assert audit["refill_rounds"] >= 1
    assert audit["shortage_reason"] is None
    assert client.calls == 1


def test_empty_scope_returns_without_embedding() -> None:
    index, client = store()
    assert index.search("q", 2, allowed_doc_ids=set()) == []
    assert client.calls == 0


def test_none_scope_preserves_legacy_order() -> None:
    index, _ = store()
    assert ids(index.search("q", 2)) == ["a1", "a2"]
    assert ids(index.search("q", 2, allowed_doc_ids=None)) == ["a1", "a2"]


def test_allowed_scope_and_shortage_are_explicit() -> None:
    index, _ = store()
    hits, audit = index.search_with_audit("q", 3, allowed_doc_ids={"c", "d"})
    assert ids(hits) == ["c", "d"]
    assert audit["shortage_reason"] == "insufficient_allowed_documents"
    assert audit["returned_doc_ids"] == ["c", "d"]


def test_whitelisted_evidence_strips_hidden_labels() -> None:
    from miaguard.evidence_access import evidence_from_hit

    index, _ = store()
    item = evidence_from_hit(index.search("q", 1)[0])
    assert item.doc_id == "a1" and item.parent_doc_id == "a"
    assert "membership_label" not in vars(item)
