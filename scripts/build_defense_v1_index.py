"""Build an isolated FAISS index containing only new RAG member documents."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=root / "data/defense_datasets/defense_access_v1_candidate06")
    parser.add_argument("--partition", choices=("D-dev", "A-cal", "V", "T"), required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    dataset = args.dataset.resolve()
    output = (args.output or root / "data/vector_stores/defense_access_v1_candidate06" / args.partition / "ag_news").resolve()
    if output.exists():
        raise FileExistsError(output)
    manifest = json.loads((dataset / "manifest.json").read_text(encoding="utf-8"))
    member_path = dataset / "index_members.jsonl"
    background_path = dataset / "background_members.jsonl"
    for path in (member_path, background_path):
        if _sha(path) != manifest["artifact_sha256"][path.name]:
            raise ValueError("Index source has changed")
    targets = [json.loads(line) for line in member_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    background = [json.loads(line) for line in background_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    targets = [row for row in targets if row["partition"] == args.partition]
    documents = targets + background[:manifest["index_size_per_partition"] - len(targets)]
    if len(documents) != manifest["index_size_per_partition"] or any(row["membership_label"] != 1 for row in documents):
        raise ValueError("Index source must contain the partition targets and shared background")
    if len({row["doc_id"] for row in documents}) != len(documents):
        raise ValueError("Index source contains duplicate documents")
    model_rel = "EmbeddingModel/sentence-transformers/all_minilm_l6_v2"
    model_path = root / model_rel
    model = SentenceTransformer(str(model_path), device="cuda")
    chunks = []
    for start in range(0, len(documents), 64):
        chunks.append(model.encode([row["text"] for row in documents[start:start + 64]],
                                   normalize_embeddings=True, convert_to_numpy=True))
    matrix = np.asarray(np.concatenate(chunks), dtype="float32")
    if matrix.shape != (len(documents), 384):
        raise ValueError(f"Unexpected embedding shape: {matrix.shape}")
    faiss.normalize_L2(matrix)
    index = faiss.IndexFlatIP(matrix.shape[1])
    index.add(matrix)
    output.mkdir(parents=True)
    faiss.write_index(index, str(output / "index.faiss"))
    (output / "documents.jsonl").write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in documents), encoding="utf-8")
    result = {"schema_version": 1, "backend": "faiss.IndexFlatIP", "dataset_id": "ag_news",
              "run_id": "defense_access_v1_candidate06", "partition": args.partition,
              "target_member_count": len(targets), "shared_background_count": len(documents) - len(targets),
              "document_count": len(documents),
              "dimension": int(matrix.shape[1]), "embedding_backend": "sentence_transformers",
              "embedding_model": model_rel, "source_membership_label": 1,
              "source_dataset_manifest_sha256": _sha(dataset / "manifest.json"),
              "index_builder_code_sha256": _sha(Path(__file__)),
              "index_sha256": _sha(output / "index.faiss"),
              "documents_sha256": _sha(output / "documents.jsonl")}
    (output / "manifest.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
