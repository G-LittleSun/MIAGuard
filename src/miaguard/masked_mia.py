from __future__ import annotations

import re
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
from .metrics import evaluate_scores
from .model_client import ModelClient, create_model_client
from .vector_store import UnifiedVectorStore


_WORD = re.compile(r"[^\W_]+(?:['’-][^\W_]+)*", re.UNICODE)
_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "in",
    "is", "it", "of", "on", "or", "that", "the", "this", "to", "was", "were", "with",
}


def _groups(items: list[Any], count: int) -> list[list[Any]]:
    count = min(count, len(items))
    base, remainder = divmod(len(items), count)
    groups: list[list[Any]] = []
    start = 0
    for index in range(count):
        end = start + base + (1 if index < remainder else 0)
        groups.append(items[start:end])
        start = end
    return groups


def _strings(value: Any, key: str) -> list[str]:
    if isinstance(value, dict):
        value = value.get(key, [])
    if not isinstance(value, list):
        return []
    return [str(item).strip().strip('"\'') for item in value]


def _fallback_word(group: list[re.Match[str]]) -> re.Match[str]:
    content = [
        match
        for match in group
        if match.group().casefold() not in _STOPWORDS and len(match.group()) > 2
    ]
    return max(content or group, key=lambda match: len(match.group()))


def mask_document(
    text: str,
    mask_count: int,
    client: ModelClient,
    model: str,
    max_tokens: int,
) -> dict[str, Any]:
    words = list(_WORD.finditer(text))
    if not words:
        raise ValueError("Masked MIA cannot mask a document with no words")
    groups = _groups(words, mask_count)
    segments = [text[group[0].start() : group[-1].end()] for group in groups]
    prompt = (
        "Select exactly one contextually difficult-to-predict word from each numbered text "
        "segment. Every selected value must be copied exactly from its segment. Avoid articles, "
        "prepositions, numbers and punctuation. Return only JSON in this form: "
        '{"words":["word from segment 1","word from segment 2"]}.\n\n'
        + "\n".join(f"Segment {index + 1}: {segment}" for index, segment in enumerate(segments))
    )
    try:
        selected = _strings(
            client.generate_json(
                model,
                prompt,
                max_tokens=max_tokens,
                temperature=0.0,
            ),
            "words",
        )
    except (RuntimeError, ValueError):
        selected = []

    replacements: list[tuple[int, int, str, str]] = []
    selection_sources: list[str] = []
    for index, group in enumerate(groups):
        candidate = selected[index] if index < len(selected) else ""
        match = next(
            (word for word in group if word.group().casefold() == candidate.casefold()),
            None,
        )
        if match is None:
            match = _fallback_word(group)
            selection_sources.append("deterministic_fallback")
        else:
            selection_sources.append(f"{client.config.generation_backend}_proxy")
        replacements.append((match.start(), match.end(), f"[Mask_{index + 1}]", match.group()))

    masked_text = text
    for start, end, placeholder, _ in reversed(replacements):
        masked_text = masked_text[:start] + placeholder + masked_text[end:]
    return {
        "masked_text": masked_text,
        "answers": [answer for _, _, _, answer in replacements],
        "selection_sources": selection_sources,
    }


def _recover_masks(
    masked_text: str,
    mask_count: int,
    context: list[str],
    client: ModelClient,
    model: str,
    max_tokens: int,
) -> list[str]:
    prompt = f"""Please answer using only the supplied RAG context.

Context:
{chr(10).join(context)}

The text below contains placeholders [Mask_1] through [Mask_{mask_count}]. Fill every
placeholder with the exact missing word or phrase. Return only JSON with one answer per
placeholder in order, for example {{"answers":["first","second"]}}.

Masked text:
{masked_text}
"""
    try:
        value = client.generate_json(
            model,
            prompt,
            max_tokens=max_tokens,
            temperature=0.0,
        )
    except (RuntimeError, ValueError):
        value = {}
    answers = _strings(value, "answers")
    return (answers + [""] * mask_count)[:mask_count]


def _normalize_answer(value: str) -> str:
    return re.sub(r"^[\W_]+|[\W_]+$", "", value, flags=re.UNICODE).casefold().strip()


def run_masked_mia(
    project_root: Path,
    run_id: str,
    dataset_id: str,
    config: AttackConfig,
    limit_per_class: int | None = None,
) -> dict[str, Any]:
    client = create_model_client(config, project_root)
    store = UnifiedVectorStore.load(vector_store_path(project_root, run_id, dataset_id), client)
    documents = load_attack_documents(
        project_root, run_id, dataset_id, "masked_mia", limit_per_class
    )
    output = attack_result_path(project_root, run_id, dataset_id, "masked_mia")
    rows, pending_documents = resume_attack_results(output, documents)
    for document in pending_documents:
        masked = mask_document(
            str(document["text"]),
            config.mask_count,
            client,
            config.generation_model,
            config.masked_max_tokens,
        )
        hits = store.search(masked["masked_text"], config.top_k)
        recovered = _recover_masks(
            masked["masked_text"],
            len(masked["answers"]),
            [str(hit["document"]["text"]) for hit in hits],
            client,
            config.generation_model,
            config.masked_max_tokens,
        )
        matches = [
            _normalize_answer(expected) == _normalize_answer(predicted)
            for expected, predicted in zip(masked["answers"], recovered)
        ]
        rows.append(
            {
                "answers": masked["answers"],
                "doc_id": document["doc_id"],
                "masked_text": masked["masked_text"],
                "membership_label": int(document["membership_label"]),
                "membership_score": sum(matches) / len(matches),
                "predicted_answers": recovered,
                "retrieved_doc_ids": [hit["document"]["doc_id"] for hit in hits],
                "selection_sources": masked["selection_sources"],
            }
        )
        write_jsonl_atomic(output / "results.jsonl", rows)

    metrics = evaluate_scores(
        [row["membership_label"] for row in rows],
        [row["membership_score"] for row in rows],
        config.masked_threshold,
        config.masked_threshold_source,
    )
    manifest = {
        "attack": "masked_mia",
        "completed_at": utc_now_iso(),
        "dataset_id": dataset_id,
        "generation_model": config.generation_model,
        "generation_backend": config.generation_backend,
        "mask_count": config.mask_count,
        "run_id": run_id,
        "sample_count": len(rows),
        "shadow_data_used": False,
        "teacher_reference": [
            "MaskBasedMIA/MaskDocsWithProxyLLMv8.py",
            "MaskBasedMIA/QueryRAG_Target.py",
            "MaskBasedMIA/Attack.py",
        ],
    }
    write_json_atomic(output / "metrics.json", metrics)
    write_json_atomic(output / "attack_manifest.json", manifest)
    return {"manifest": manifest, "metrics": metrics, "output_path": str(output)}


__all__ = ["mask_document", "run_masked_mia"]
