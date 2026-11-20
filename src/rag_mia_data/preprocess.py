from __future__ import annotations

import hashlib
import heapq
import re
import unicodedata
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from .config import PipelineConfig
from .io_utils import iter_tsv, utc_now_iso, write_json_atomic, write_jsonl_atomic


_BLOCK_TAG_RE = re.compile(r"</?(?:br|p|div|li|tr|h[1-6])\b[^>]*>", re.IGNORECASE)
_TAG_RE = re.compile(r"<[^>]+>")
_SPACE_RE = re.compile(r"\s+")


def normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text)
    normalized = "".join(
        " " if unicodedata.category(char) in {"Cc", "Cf"} else char
        for char in normalized
    )
    normalized = _BLOCK_TAG_RE.sub(" ", normalized)
    normalized = _TAG_RE.sub("", normalized)
    return _SPACE_RE.sub(" ", normalized).strip()


def make_doc_id(source_doc_id: str) -> str:
    value = source_doc_id.strip()
    if value.isdecimal():
        return f"t2rank_{int(value):08d}"
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]
    return f"t2rank_h{digest}"


def _source_sort_key(source_doc_id: str) -> tuple[int, int | str]:
    value = source_doc_id.strip()
    return (0, int(value)) if value.isdecimal() else (1, value)


def _build_record(source_doc_id: str, raw_text: str, text: str) -> dict[str, Any]:
    raw_hash = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()
    normalized_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return {
        "doc_id": make_doc_id(source_doc_id),
        "source_doc_id": source_doc_id,
        "source_dataset": "T2Ranking",
        "title": "",
        "text": text,
        "raw_text_sha256": raw_hash,
        "normalized_text_sha256": normalized_hash,
        "char_length": len(text),
        "language": "zh",
        "duplicate_group_id": f"dup_{normalized_hash[:12]}",
        "membership_label": None,
        "target_split": None,
    }


def _select_candidates(
    rows: Iterable[dict[str, str]],
    count: int,
    seed: int,
    min_chars: int,
    max_chars: int,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    if count <= 0:
        raise ValueError("count must be positive")

    heap: list[tuple[int, str]] = []
    selected: dict[str, tuple[str, tuple[int, int | str], dict[str, Any]]] = {}
    seen_hashes: set[str] = set()
    stats = {
        "input_records": 0,
        "empty_id_or_text": 0,
        "outside_length_range": 0,
        "exact_duplicates": 0,
        "eligible_unique": 0,
    }

    for row in rows:
        stats["input_records"] += 1
        source_doc_id = (row.get("pid") or "").strip()
        raw_text = row.get("text") or ""
        if not source_doc_id or not raw_text.strip():
            stats["empty_id_or_text"] += 1
            continue
        text = normalize_text(raw_text)
        if len(text) < min_chars or len(text) > max_chars:
            stats["outside_length_range"] += 1
            continue

        normalized_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        source_key = _source_sort_key(source_doc_id)
        if normalized_hash in seen_hashes:
            stats["exact_duplicates"] += 1
            current = selected.get(normalized_hash)
            if current is not None and source_key < current[1]:
                selected[normalized_hash] = (
                    current[0],
                    source_key,
                    _build_record(source_doc_id, raw_text, text),
                )
            continue

        seen_hashes.add(normalized_hash)
        stats["eligible_unique"] += 1
        selection_key = hashlib.sha256(
            f"{seed}:{normalized_hash}".encode("utf-8")
        ).hexdigest()
        selection_value = int(selection_key, 16)
        record = _build_record(source_doc_id, raw_text, text)
        entry = (-selection_value, normalized_hash)
        if len(heap) < count:
            heapq.heappush(heap, entry)
            selected[normalized_hash] = (selection_key, source_key, record)
        elif selection_value < -heap[0][0]:
            _, removed_hash = heapq.heapreplace(heap, entry)
            selected.pop(removed_hash)
            selected[normalized_hash] = (selection_key, source_key, record)

    ordered = sorted(selected.values(), key=lambda item: (item[0], item[2]["doc_id"]))
    return [item[2] for item in ordered], stats


def select_candidates(
    rows: Iterable[dict[str, str]],
    count: int,
    seed: int,
    min_chars: int,
    max_chars: int,
) -> list[dict[str, Any]]:
    candidates, _ = _select_candidates(rows, count, seed, min_chars, max_chars)
    return candidates


def preprocess_dataset(config: PipelineConfig) -> dict[str, Any]:
    collection_path = config.dataset_path / "collection.tsv"
    if not collection_path.is_file():
        raise FileNotFoundError(f"Missing source corpus: {collection_path}")

    candidates, stats = _select_candidates(
        iter_tsv(collection_path),
        count=config.candidate_doc_count,
        seed=config.seed,
        min_chars=config.min_doc_chars,
        max_chars=config.max_doc_chars,
    )
    if len(candidates) != config.candidate_doc_count:
        raise ValueError(
            f"Eligible unique documents {len(candidates)} are fewer than required "
            f"{config.candidate_doc_count}"
        )

    output_path = config.documents_dir / "candidate_docs.jsonl"
    write_jsonl_atomic(output_path, candidates)
    run_id = f"{config.run_name}-{utc_now_iso().replace(':', '').replace('+00:00', 'Z')}"
    manifest = {
        "run_id": run_id,
        "stage": "preprocess",
        "config": config.config_path.relative_to(config.project_root).as_posix(),
        "dataset": config.dataset_name,
        "source": collection_path.relative_to(config.project_root).as_posix(),
        "output": output_path.relative_to(config.project_root).as_posix(),
        "output_records": len(candidates),
        "statistics": stats,
        "created_at": utc_now_iso(),
    }
    write_json_atomic(config.manifests_dir / "runs" / run_id / "preprocess.json", manifest)
    return manifest
