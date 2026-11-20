from __future__ import annotations

import argparse
from pathlib import Path

from rag_mia_data.io_utils import utc_now_iso, write_json_atomic

from miaguard.cli import doctor
from miaguard.config import load_attack_config
from miaguard.data import load_attack_documents, vector_store_path
from miaguard.ia_attack import run_ia
from miaguard.masked_mia import run_masked_mia
from miaguard.ollama_client import OllamaClient
from miaguard.vector_store import UnifiedVectorStore, build_vector_store


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/attacks/ollama_smoke.yaml")
    parser.add_argument("--run-id", default="20260715-ag-news-smoke")
    parser.add_argument("--dataset", default="ag_news")
    parser.add_argument("--limit-per-class", type=int, default=1)
    args = parser.parse_args()

    root = Path.cwd().resolve()
    config = load_attack_config(args.config)
    doctor_result = doctor(args.config)
    index_result = build_vector_store(root, args.run_id, args.dataset, config)

    client = OllamaClient(
        config.base_url,
        config.timeout_seconds,
        config.keep_alive,
        config.seed,
    )
    store = UnifiedVectorStore.load(vector_store_path(root, args.run_id, args.dataset), client)
    member = load_attack_documents(root, args.run_id, args.dataset, "masked_mia", 1)[0]
    hits = store.search(str(member["text"]), 1)
    if not hits or hits[0]["document"]["doc_id"] != member["doc_id"]:
        raise RuntimeError("Persisted vector store failed exact-document retrieval check")

    masked = run_masked_mia(
        root, args.run_id, args.dataset, config, args.limit_per_class
    )
    ia = run_ia(root, args.run_id, args.dataset, config, args.limit_per_class)
    report = {
        "completed_at": utc_now_iso(),
        "conda_environment": "MIAGuard",
        "dataset_id": args.dataset,
        "doctor": doctor_result,
        "ia": ia,
        "limit_per_class": args.limit_per_class,
        "masked_mia": masked,
        "run_id": args.run_id,
        "status": "passed",
        "vector_store": {
            **index_result,
            "exact_retrieval_doc_id": hits[0]["document"]["doc_id"],
            "exact_retrieval_score": hits[0]["score"],
        },
    }
    report_path = root / "reports" / "attack_migration_verification.json"
    write_json_atomic(report_path, report)
    print(report_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

