from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


ATTACK_TYPES = ("direct_rag_mia", "s2_mia", "masked_mia", "ia", "benign")
VARIANT_TYPES = ("canonical", "paraphrase", "generated")
BENIGN_CATEGORIES = ("topic", "entity", "event", "summary", "follow_up")
HARD_BENIGN_SCENARIOS = (
    "quoted_context_interpretation",
    "grounded_fact_linking",
    "legitimate_context_elaboration",
    "multi_turn_clarification",
    "source_attribution_or_comparison",
)


@dataclass(frozen=True)
class QueryBankBuildConfig:
    source_run_id: str
    attack_config_path: Path
    seed: int
    member_count: int
    nonmember_count: int
    paraphrases_per_attack: int
    ia_questions_per_document: int
    ia_batch_size: int
    ia_max_attempts: int
    benign_categories: tuple[str, ...]

    @property
    def ia_total(self) -> int:
        return self.ia_questions_per_document


def document_sha256(text: str) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def make_query_id(
    dataset_id: str,
    doc_id: str,
    attack_type: str,
    variant_type: str,
    query_index: int,
) -> str:
    if query_index <= 0:
        raise ValueError("query_index must be positive")
    return (
        f"{dataset_id}:{doc_id}:{attack_type}:{variant_type}:"
        f"{query_index:04d}"
    )


def _mapping(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{field} must be a mapping")
    return value


def validate_query_record(record: dict[str, Any]) -> None:
    required = {
        "query_id",
        "dataset_id",
        "doc_id",
        "membership_label",
        "source_document_sha256",
        "traffic_type",
        "attack_type",
        "variant_type",
        "query_index",
        "query_text",
        "payload",
        "generation",
        "validation",
        "created_at",
    }
    missing = sorted(required - record.keys())
    if missing:
        raise ValueError(f"Query record is missing fields: {missing}")
    attack_type = str(record["attack_type"])
    variant_type = str(record["variant_type"])
    if attack_type not in ATTACK_TYPES:
        raise ValueError(f"Unsupported attack_type: {attack_type}")
    if variant_type not in VARIANT_TYPES:
        raise ValueError(f"Unsupported variant_type: {variant_type}")
    if int(record["membership_label"]) not in {0, 1}:
        raise ValueError("membership_label must be 0 or 1")
    expected_traffic = "benign" if attack_type == "benign" else "attack"
    if record["traffic_type"] != expected_traffic:
        raise ValueError("traffic_type does not match attack_type")
    if not str(record["query_text"]).strip():
        raise ValueError("query_text must not be blank")
    payload = _mapping(record["payload"], "payload")
    _mapping(record["generation"], "generation")
    validation = _mapping(record["validation"], "validation")
    if validation.get("status") != "accepted":
        raise ValueError("Only accepted records belong in queries.jsonl")
    if attack_type == "ia":
        if payload.get("ground_truth") not in {"yes", "no", "unknown"}:
            raise ValueError("IA ground_truth must be yes, no, or unknown")
        if not str(payload.get("question", "")).strip():
            raise ValueError("IA question must not be blank")
        if not str(payload.get("summary", "")).strip():
            raise ValueError("IA summary must not be blank")
    elif attack_type == "masked_mia":
        if not str(payload.get("masked_text", "")).strip():
            raise ValueError("Masked payload masked_text must not be blank")
        answers = payload.get("answers")
        if not isinstance(answers, list) or not answers:
            raise ValueError("Masked payload answers must be a non-empty list")
    elif attack_type == "s2_mia":
        if not str(payload.get("prefix", "")).strip():
            raise ValueError("S2 payload prefix must not be blank")
    elif attack_type == "benign":
        if payload.get("category") not in BENIGN_CATEGORIES:
            raise ValueError("Unknown benign category")
        audit_fields = {"difficulty", "hard_scenario", "benign_intent"}
        present_audit_fields = audit_fields.intersection(payload)
        if present_audit_fields and present_audit_fields != audit_fields:
            raise ValueError("v2 benign payload must include all audit fields")
        if present_audit_fields:
            difficulty = payload["difficulty"]
            scenario = payload["hard_scenario"]
            if difficulty not in {"standard", "hard"}:
                raise ValueError("Unknown benign difficulty")
            if not str(payload["benign_intent"]).strip():
                raise ValueError("benign_intent must not be blank")
            if difficulty == "standard" and scenario is not None:
                raise ValueError("standard benign queries must not have hard_scenario")
            if difficulty == "hard" and scenario not in HARD_BENIGN_SCENARIOS:
                raise ValueError("hard benign queries require an approved hard_scenario")
    expected_id = make_query_id(
        str(record["dataset_id"]),
        str(record["doc_id"]),
        attack_type,
        variant_type,
        int(record["query_index"]),
    )
    if record["query_id"] != expected_id:
        raise ValueError("query_id does not match stable record fields")


def load_query_bank_config(path: str | Path) -> QueryBankBuildConfig:
    config_path = Path(path)
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("Query Bank configuration must be a mapping")
    pool = _mapping(raw.get("pool"), "pool")
    queries = _mapping(raw.get("queries"), "queries")
    config = QueryBankBuildConfig(
        source_run_id=str(raw["source_run_id"]),
        attack_config_path=Path(str(raw["attack_config"])),
        seed=int(raw.get("seed", 20260724)),
        member_count=int(pool["members"]),
        nonmember_count=int(pool["nonmembers"]),
        paraphrases_per_attack=int(queries.get("paraphrases_per_attack", 4)),
        ia_questions_per_document=int(
            queries.get("ia_questions_per_document", 30)
        ),
        ia_batch_size=int(queries.get("ia_batch_size", 6)),
        ia_max_attempts=int(queries.get("ia_max_attempts", 20)),
        benign_categories=tuple(
            str(item)
            for item in queries.get("benign_categories", BENIGN_CATEGORIES)
        ),
    )
    counts = (
        config.member_count,
        config.nonmember_count,
        config.paraphrases_per_attack,
        config.ia_questions_per_document,
        config.ia_batch_size,
        config.ia_max_attempts,
    )
    if any(value <= 0 for value in counts):
        raise ValueError("Query Bank counts must be positive")
    if config.ia_questions_per_document != 30:
        raise ValueError(
            "IA Query Bank requires exactly 30 questions per document"
        )
    if config.paraphrases_per_attack != 4:
        raise ValueError("Each single-turn attack requires four paraphrases")
    if config.benign_categories != BENIGN_CATEGORIES:
        raise ValueError("benign_categories must match the five approved categories")
    return config
