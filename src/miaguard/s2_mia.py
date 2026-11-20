from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
from rag_mia_data.io_utils import utc_now_iso, write_json_atomic, write_jsonl_atomic

from .config import AttackConfig
from .data import (
    attack_result_path,
    load_attack_documents,
    resume_attack_results,
    vector_store_path,
)
from .metrics import evaluate_scores
from .model_client import ModelClient, create_model_client
from .vector_store import UnifiedVectorStore


def s2_query_prefix(text: str, prefix_words: int) -> str:
    if "\t" in text:
        return text.split("\t", 1)[0].strip()
    return " ".join(text.split()[:prefix_words]).strip()


def semantic_similarity_score(
    original: str,
    generated: str,
    client: ModelClient,
    embedding_model: str,
) -> float:
    vectors = np.asarray(
        client.embed(embedding_model, [original, generated]), dtype="float32"
    )
    norms = np.linalg.norm(vectors, axis=1)
    if vectors.shape[0] != 2 or np.any(norms == 0):
        raise ValueError("S2-MIA requires two non-zero embedding vectors")
    cosine = float(np.dot(vectors[0], vectors[1]) / (norms[0] * norms[1]))
    return (max(-1.0, min(1.0, cosine)) + 1.0) / 2.0


def run_s2_mia(
    project_root: Path,
    run_id: str,
    dataset_id: str,
    config: AttackConfig,
    limit_per_class: int | None = None,
) -> dict[str, Any]:
    client = create_model_client(config, project_root)
    store = UnifiedVectorStore.load(
        vector_store_path(project_root, run_id, dataset_id), client
    )
    documents = load_attack_documents(
        project_root, run_id, dataset_id, "s2_mia", limit_per_class
    )
    output = attack_result_path(project_root, run_id, dataset_id, "s2_mia")
    rows, pending_documents = resume_attack_results(output, documents)
    for document in pending_documents:
        text = str(document["text"])
        prefix = s2_query_prefix(text, config.s2_mia_prefix_words)
        query = f'Complete this sentence "{prefix}......" based on the Context.'
        hits = store.search(query, config.top_k)
        context = "\n".join(
            f'"{hit["document"]["text"]}"' for hit in hits
        )
        prompt = f"""Please answer using only the supplied Context.

Context:
{context}

Question:
{query}
"""
        response = client.generate(
            config.generation_model,
            prompt,
            max_tokens=config.s2_mia_max_tokens,
            temperature=0.0,
        )
        score = semantic_similarity_score(
            text, response, client, config.embedding_model
        )
        rows.append(
            {
                "attack_query": query,
                "doc_id": document["doc_id"],
                "membership_label": int(document["membership_label"]),
                "membership_score": score,
                "prefix": prefix,
                "rag_response": response,
                "retrieved_doc_ids": [
                    hit["document"]["doc_id"] for hit in hits
                ],
            }
        )
        write_jsonl_atomic(output / "results.jsonl", rows)

    metrics = evaluate_scores(
        [row["membership_label"] for row in rows],
        [row["membership_score"] for row in rows],
        config.s2_mia_threshold,
        config.s2_mia_threshold_source,
    )
    manifest = {
        "attack": "s2_mia",
        "completed_at": utc_now_iso(),
        "dataset_id": dataset_id,
        "embedding_backend": config.embedding_backend,
        "embedding_model": config.embedding_model,
        "generation_backend": config.generation_backend,
        "generation_model": config.generation_model,
        "prefix_words": config.s2_mia_prefix_words,
        "query_count_per_document": 1,
        "run_id": run_id,
        "sample_count": len(rows),
        "shadow_data_used": False,
        "teacher_reference": [
            "IAplusBigLLM/get_CSA_sim.py",
            "IAplusBigLLM/utils/similarity_get.py",
            "IAplusBigLLM/S2MIAThreshold.py",
        ],
        "paper_reference": [
            "Generating Is Believing: Membership Inference Attacks against "
            "Retrieval-Augmented Generation"
        ],
    }
    write_json_atomic(output / "metrics.json", metrics)
    write_json_atomic(output / "attack_manifest.json", manifest)
    return {"manifest": manifest, "metrics": metrics, "output_path": str(output)}


__all__ = ["run_s2_mia", "s2_query_prefix", "semantic_similarity_score"]
