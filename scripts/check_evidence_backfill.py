"""Read-only backfill example on the frozen FAISS index."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from miaguard.evidence_access import parent_doc_id
from miaguard.vector_store import UnifiedVectorStore


class FixedEmbedding:
    def __init__(self, vector):
        self.vector = vector

    def embed(self, model, queries):
        return [self.vector.tolist() for _ in queries]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vector-store", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    inputs = {name: sha(args.vector_store / name) for name in ("index.faiss", "documents.jsonl", "manifest.json")}
    store = UnifiedVectorStore.load(args.vector_store, FixedEmbedding([]))
    store.client = FixedEmbedding(store.index.reconstruct(0))
    first = store.search("fixed-vector-probe", 1)[0]
    excluded_parent = parent_doc_id(first["document"])
    after, audit = store.search_with_audit("fixed-vector-probe", 4, excluded_parent_ids=frozenset({excluded_parent}))
    current = {name: sha(args.vector_store / name) for name in inputs}
    if current != inputs:
        raise RuntimeError("Frozen index content changed during search")
    result = {
        "schema_version": 1,
        "vector_store": str(args.vector_store.resolve()),
        "index_sha256_before_and_after": inputs,
        "excluded_parent_ids": [excluded_parent],
        "audit": audit,
        "returned_doc_ids": [str(hit["document"]["doc_id"]) for hit in after],
        "status": "complete",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
