"""Minimal evidence values crossing from retrieval into access decisions."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Callable

from .defense_contracts import Evidence


SUMMARY_TEMPLATE_VERSION = "defense_v1_topic_summary_20261022"


@dataclass(frozen=True)
class ActionExecution:
    recommended_action: str
    applied_action: str
    evidence: tuple[Evidence, ...]
    status: str
    reason_codes: tuple[str, ...] = ()
    source_doc_ids: tuple[str, ...] = ()
    excluded_parent_ids: frozenset[str] = frozenset()
    summary_template_version: str | None = None
    transform_input_evidence: tuple[Evidence, ...] = ()


def parent_doc_id(document: Mapping[str, Any]) -> str:
    value = document.get("parent_doc_id") or document.get("doc_id")
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Document requires doc_id or parent_doc_id")
    return value


def evidence_from_hit(hit: Mapping[str, Any]) -> Evidence:
    """Whitelist only source ID, text and score; never copy offline labels."""
    document = hit["document"]
    if not isinstance(document, Mapping):
        raise ValueError("Hit document must be a mapping")
    return Evidence(
        doc_id=str(document["doc_id"]),
        parent_doc_id=parent_doc_id(document),
        text=str(document["text"]),
        score=float(hit["score"]),
    )


def execute_action(
    action: str,
    candidates: tuple[Evidence, ...],
    target_parent_ids: frozenset[str],
    retrieve: Callable[[frozenset[str]], tuple[Evidence, ...]] | None,
    summarize: Callable[[tuple[Evidence, ...]], str] | None,
    *,
    refill_failure_action: str = "no_context_answer",
) -> ActionExecution:
    """The sole transformation from retrieved candidates to delivered evidence."""
    normalized = "sanitized_context" if action == "summarize_context" else action
    if normalized not in {"allow", "hide_target_refill", "sanitized_context", "no_context_answer", "deny", "unavailable"}:
        raise ValueError(f"Unsupported evidence action: {action}")
    source_ids = tuple(item.doc_id for item in candidates)
    if normalized == "allow":
        return ActionExecution(normalized, normalized, candidates, "ok" if candidates else "empty_evidence", source_doc_ids=source_ids)
    if normalized in {"no_context_answer", "deny", "unavailable"}:
        return ActionExecution(normalized, normalized, (), "ok" if normalized != "unavailable" else "error", source_doc_ids=source_ids)
    if normalized == "hide_target_refill":
        if refill_failure_action not in {"no_context_answer", "deny"}:
            raise ValueError("Unsupported refill failure action")
        if not target_parent_ids or retrieve is None:
            return ActionExecution(normalized, refill_failure_action, (), "missing_target", ("MISSING_TARGET_PARENT",), source_ids, target_parent_ids)
        try:
            replacement = retrieve(target_parent_ids)
        except Exception:
            return ActionExecution(normalized, refill_failure_action, (), "retrieval_failed", ("REFILL_FAILED",), source_ids, target_parent_ids)
        if any(item.parent_doc_id in target_parent_ids for item in replacement):
            return ActionExecution(normalized, refill_failure_action, (), "retrieval_failed", ("EXCLUDED_PARENT_RETURNED",), source_ids, target_parent_ids)
        if not replacement:
            return ActionExecution(normalized, refill_failure_action, (), "empty_evidence", ("NO_ALLOWED_EVIDENCE",), source_ids, target_parent_ids)
        return ActionExecution(normalized, normalized, replacement, "ok", source_doc_ids=source_ids, excluded_parent_ids=target_parent_ids)
    if not candidates or summarize is None:
        return ActionExecution(normalized, "no_context_answer", (), "empty_evidence" if not candidates else "summary_unavailable", ("SUMMARY_UNAVAILABLE",), source_ids, summary_template_version=SUMMARY_TEMPLATE_VERSION)
    try:
        text = summarize(candidates)
        if not isinstance(text, str) or not text.strip():
            raise ValueError("Empty summary")
    except Exception:
        return ActionExecution(normalized, "no_context_answer", (), "summary_failed", ("SUMMARY_FAILED",), source_ids, summary_template_version=SUMMARY_TEMPLATE_VERSION, transform_input_evidence=candidates)
    identifier = hashlib.sha256("|".join(source_ids).encode("utf-8")).hexdigest()[:16]
    summary = Evidence(f"summary:{identifier}", "aggregate", text.strip(), max(item.score for item in candidates), "summary")
    return ActionExecution(normalized, normalized, (summary,), "ok", source_doc_ids=source_ids, summary_template_version=SUMMARY_TEMPLATE_VERSION, transform_input_evidence=candidates)


__all__ = ["ActionExecution", "SUMMARY_TEMPLATE_VERSION", "evidence_from_hit", "execute_action", "parent_doc_id"]
