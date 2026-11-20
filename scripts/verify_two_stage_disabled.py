from __future__ import annotations

import argparse
import json
from pathlib import Path

from rag_mia_data.io_utils import write_json_atomic

from miaguard.config import load_attack_config
from miaguard.data import vector_store_path
from miaguard.defense import GuardedRAG
from miaguard.model_client import create_model_client
from miaguard.two_stage_gateway import TwoStageGateway, load_two_stage_config
from miaguard.vector_store import UnifiedVectorStore


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--gateway-config", required=True)
    parser.add_argument("--source-run-id", required=True)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--query", default="What is the main topic of this news?")
    parser.add_argument("--project-root", default=".")
    args = parser.parse_args()

    root = Path(args.project_root).resolve()
    attack_config = load_attack_config(args.config)
    gateway_config = load_two_stage_config(args.gateway_config)
    if gateway_config.mode != "disabled":
        raise ValueError("Disabled parity verification requires mode: disabled")
    client = create_model_client(attack_config, root)
    client.validate_models()
    store = UnifiedVectorStore.load(
        vector_store_path(root, args.source_run_id, args.dataset), client
    )
    baseline_hits = store.search(args.query, attack_config.top_k)
    gateway = TwoStageGateway(gateway_config)
    prepared = GuardedRAG(store, gateway, attack_config.top_k).prepare(
        args.query,
        "disabled-parity-session",
    )
    baseline_ids = [str(hit["document"]["doc_id"]) for hit in baseline_hits]
    baseline_scores = [float(hit["score"]) for hit in baseline_hits]
    baseline_contexts = [str(hit["document"]["text"]) for hit in baseline_hits]
    report = {
        "status": "passed",
        "source_run_id": args.source_run_id,
        "dataset_id": args.dataset,
        "query": args.query,
        "document_ids_equal": prepared.retrieved_doc_ids == baseline_ids,
        "retrieval_scores_equal": prepared.retrieval_scores == baseline_scores,
        "contexts_equal": prepared.contexts == baseline_contexts,
        "access_action": prepared.decision.access_action,
        "access_level": prepared.decision.access_level,
        "session_state_empty": gateway.session_store.window(
            "disabled-parity-session"
        ) == (),
    }
    if not all(
        (
            report["document_ids_equal"],
            report["retrieval_scores_equal"],
            report["contexts_equal"],
            report["access_action"] == "allow",
            report["access_level"] == "L0",
            report["session_state_empty"],
        )
    ):
        report["status"] = "failed"
    write_json_atomic(Path(args.output), report)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
