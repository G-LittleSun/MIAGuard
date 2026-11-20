from __future__ import annotations

from pathlib import Path
from typing import Any

from rag_mia_data.io_utils import utc_now_iso, write_json_atomic, write_jsonl_atomic

from .config import AttackConfig
from .data import (
    attack_result_path,
    load_attack_documents,
    resume_attack_results,
    vector_store_path,
)
from .metrics import evaluate_scores, extract_yes_no_unknown
from .model_client import ModelClient, create_model_client
from .vector_store import UnifiedVectorStore


def _string_list(value: Any, key: str) -> list[str]:
    if isinstance(value, dict):
        value = value.get(key, [])
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _generate_json_with_retry(
    client: ModelClient,
    model: str,
    prompt: str,
    max_tokens: int,
    temperature: float,
) -> Any:
    try:
        return client.generate_json(
            model,
            prompt,
            max_tokens=max_tokens,
            temperature=temperature,
        )
    except (RuntimeError, ValueError):
        retry_prompt = (
            f"{prompt}\n\nReturn one compact, valid JSON object. Escape every double "
            "quote inside JSON strings and include no commentary."
        )
        return client.generate_json(
            model,
            retry_prompt,
            max_tokens=max_tokens * 2,
            temperature=0.0,
        )


def _generate_questions(
    text: str,
    count: int,
    client: ModelClient,
    model: str,
    max_tokens: int,
) -> tuple[str, list[str]]:
    prompt_text = text.replace('"', "'")
    balance_instruction = (
        "Include both questions whose answer is yes and questions whose answer is no."
        if count >= 2
        else "Generate one question with a definite yes or no answer."
    )
    prompt = f"""Based only on the corpus below, generate exactly {count} specific and diverse
yes/no questions that contain distinctive keywords from the corpus. Do not refer to "the text",
"the passage", or "the study". {balance_instruction}
Also provide a short noun phrase describing the corpus topic. Return only JSON:
{{"summary":"short topic","questions":["question 1","question 2"]}}
Do not put double quote characters inside the summary or question values.

Corpus:
{prompt_text}
"""
    value = _generate_json_with_retry(
        client,
        model,
        prompt,
        max_tokens,
        0.2,
    )
    summary = str(value.get("summary", "document topic")).strip() if isinstance(value, dict) else "document topic"
    questions = _string_list(value, "questions")[:count]
    if not questions:
        raise RuntimeError("IA query generation returned no questions")
    return summary, questions


def _generate_ground_truth(
    text: str,
    questions: list[str],
    client: ModelClient,
    model: str,
    max_tokens: int,
) -> list[str]:
    numbered = "\n".join(f"{index + 1}. {question}" for index, question in enumerate(questions))
    prompt = f"""Answer each question using only the supplied corpus. For every question, answer
exactly yes, no, or unknown. Return only JSON with answers in the same order:
{{"answers":["yes","no","unknown"]}}

Corpus:
{text}

Questions:
{numbered}
"""
    value = _generate_json_with_retry(
        client,
        model,
        prompt,
        max_tokens,
        0.0,
    )
    answers = [extract_yes_no_unknown(item) for item in _string_list(value, "answers")]
    return (answers + ["unknown"] * len(questions))[: len(questions)]


def _query_target_rag(
    query: str,
    store: UnifiedVectorStore,
    top_k: int,
    client: ModelClient,
    model: str,
) -> tuple[str, list[str]]:
    hits = store.search(query, top_k)
    context = "\n".join(f'"{hit["document"]["text"]}"' for hit in hits)
    prompt = f"""Please answer the question using only the Context provided.
Context:
{context}

Question: {query}
Answer only Yes, No, or Unknown.
"""
    answer = client.generate(model, prompt, max_tokens=12, temperature=0.0)
    return extract_yes_no_unknown(answer), [hit["document"]["doc_id"] for hit in hits]


def run_ia(
    project_root: Path,
    run_id: str,
    dataset_id: str,
    config: AttackConfig,
    limit_per_class: int | None = None,
) -> dict[str, Any]:
    client = create_model_client(config, project_root)
    store = UnifiedVectorStore.load(vector_store_path(project_root, run_id, dataset_id), client)
    documents = load_attack_documents(project_root, run_id, dataset_id, "ia", limit_per_class)
    output = attack_result_path(project_root, run_id, dataset_id, "ia")
    rows, pending_documents = resume_attack_results(output, documents)
    for document in pending_documents:
        text = str(document["text"])
        summary, questions = _generate_questions(
            text,
            config.questions_per_document,
            client,
            config.generation_model,
            config.ia_generation_max_tokens,
        )
        ground_truth = _generate_ground_truth(
            text,
            questions,
            client,
            config.generation_model,
            config.ia_generation_max_tokens,
        )
        query_rows: list[dict[str, Any]] = []
        point_values: list[float] = []
        for question, expected in zip(questions, ground_truth):
            adversarial_query = (
                f"I am inquiring about a {summary}. {question} "
                "Please answer with Yes, No, or Unknown."
            )
            predicted, retrieved_ids = _query_target_rag(
                adversarial_query,
                store,
                config.top_k,
                client,
                config.generation_model,
            )
            if predicted == expected:
                point = 1.0
            elif predicted == "unknown":
                point = -config.ia_unknown_penalty
            else:
                point = 0.0
            point_values.append(point)
            query_rows.append(
                {
                    "adversarial_query": adversarial_query,
                    "ground_truth": expected,
                    "point": point,
                    "predicted_answer": predicted,
                    "question": question,
                    "retrieved_doc_ids": retrieved_ids,
                }
            )
        rows.append(
            {
                "doc_id": document["doc_id"],
                "membership_label": int(document["membership_label"]),
                "membership_score": sum(point_values) / len(point_values),
                "queries": query_rows,
                "summary": summary,
            }
        )
        write_jsonl_atomic(output / "results.jsonl", rows)

    metrics = evaluate_scores(
        [row["membership_label"] for row in rows],
        [row["membership_score"] for row in rows],
        config.ia_threshold,
        config.ia_threshold_source,
    )
    manifest = {
        "attack": "ia",
        "completed_at": utc_now_iso(),
        "dataset_id": dataset_id,
        "generation_model": config.generation_model,
        "generation_backend": config.generation_backend,
        "questions_per_document": config.questions_per_document,
        "run_id": run_id,
        "sample_count": len(rows),
        "shadow_data_used": False,
        "teacher_reference": [
            "IAplusBigLLM/IA_QueryGeneration.py",
            "IAplusBigLLM/IA_GroundTruthAnswerGen.py",
            "IAplusBigLLM/IA_extract_summary.py",
            "IAplusBigLLM/IA_ConstructAdversarialQuery.py",
            "IAplusBigLLM/IA_QueryRAG.py",
            "IAplusBigLLM/IA_Attack.py",
        ],
    }
    write_json_atomic(output / "metrics.json", metrics)
    write_json_atomic(output / "attack_manifest.json", manifest)
    return {"manifest": manifest, "metrics": metrics, "output_path": str(output)}


__all__ = ["run_ia"]
