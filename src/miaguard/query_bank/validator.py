from __future__ import annotations

import re
from collections import Counter
from pathlib import Path
from typing import Any, Mapping

from miaguard.data import load_run_documents

from .schema import BENIGN_CATEGORIES, document_sha256, validate_query_record
from .storage import QueryBank, QueryBankPaths


EXPECTED_COUNTS = {
    "direct_rag_mia": 5,
    "s2_mia": 5,
    "masked_mia": 5,
    "benign": 5,
}
IA_MIN_ANSWER_COUNTS = {"yes": 10, "no": 10}


def normalize_query(value: str) -> str:
    return " ".join(
        re.sub(r"[^\w\s]", " ", value.casefold(), flags=re.UNICODE).split()
    )


def validate_document_records(
    records: list[dict[str, Any]],
    expected_document: dict[str, Any],
    *,
    require_balanced_ia: bool = True,
    benign_policy: Mapping[str, int] | None = None,
) -> dict[str, Any]:
    if not records:
        raise ValueError("Document has no Query Bank records")
    for record in records:
        validate_query_record(record)
        for field in (
            "dataset_id",
            "doc_id",
            "membership_label",
            "source_document_sha256",
        ):
            if record[field] != expected_document[field]:
                raise ValueError(f"Query record {field} does not match document")
    counts = Counter(str(row["attack_type"]) for row in records)
    fixed_counts = {
        attack: count
        for attack, count in counts.items()
        if attack != "ia"
    }
    if benign_policy is not None:
        minimum_per_document = int(benign_policy.get("minimum_per_document", 0))
        if minimum_per_document < len(BENIGN_CATEGORIES):
            raise ValueError("benign policy minimum must preserve the five-query floor")
        expected_fixed_counts = {
            attack: count
            for attack, count in EXPECTED_COUNTS.items()
            if attack != "benign"
        }
        actual_fixed_counts = {
            attack: count
            for attack, count in fixed_counts.items()
            if attack != "benign"
        }
        if actual_fixed_counts != expected_fixed_counts:
            raise ValueError(
                f"Query counts do not match requirements: {dict(counts)}"
            )
        if counts.get("benign", 0) < minimum_per_document:
            raise ValueError(
                f"Document benign count is below the required floor: {dict(counts)}"
            )
    else:
        expected_fixed_counts = dict(EXPECTED_COUNTS)
        if fixed_counts != expected_fixed_counts:
            raise ValueError(
                f"Query counts do not match requirements: {dict(counts)}"
            )
    for attack in ("direct_rag_mia", "s2_mia", "masked_mia"):
        variants = Counter(
            str(row["variant_type"])
            for row in records
            if row["attack_type"] == attack
        )
        if variants != {"canonical": 1, "paraphrase": 4}:
            raise ValueError(f"{attack} must have 1 canonical and 4 paraphrases")
    ia_rows = [row for row in records if row["attack_type"] == "ia"]
    ia_answers = Counter(str(row["payload"]["ground_truth"]) for row in ia_rows)
    if len(ia_rows) < 30:
        raise ValueError("Document must contain at least 30 IA answers")
    if require_balanced_ia and any(
        ia_answers[answer] < required
        for answer, required in IA_MIN_ANSWER_COUNTS.items()
    ):
        raise ValueError(
            "Document must contain at least 10 yes and 10 no IA answers"
        )
    normalized = [
        normalize_query(str(row["payload"]["question"])) for row in ia_rows
    ]
    if len(normalized) != len(set(normalized)):
        raise ValueError("Document contains a duplicate IA question")
    benign_rows = [row for row in records if row["attack_type"] == "benign"]
    benign_categories = {str(row["payload"]["category"]) for row in benign_rows}
    if benign_categories != set(BENIGN_CATEGORIES):
        raise ValueError("Document must contain all five benign categories")
    report = {
        "doc_id": str(expected_document["doc_id"]),
        "query_count": len(records),
        "counts": dict(counts),
        "ia_answers": dict(ia_answers),
    }
    if benign_policy is not None:
        normalized_benign = [normalize_query(str(row["query_text"])) for row in benign_rows]
        if len(normalized_benign) != len(set(normalized_benign)):
            raise ValueError("Document contains a duplicate benign query")
        report["benign_difficulty_counts"] = dict(
            sorted(Counter(str(row["payload"]["difficulty"]) for row in benign_rows).items())
        )
    return report


def _validated_ia_answer_counts(bank: QueryBank) -> dict[str, int]:
    counts = dict(
        sorted(
            Counter(
                str(row["payload"]["ground_truth"])
                for row in bank.records
                if row["attack_type"] == "ia"
            ).items()
        )
    )
    manifest_counts = bank.manifest.get("ia_answer_counts")
    if manifest_counts is not None and manifest_counts != counts:
        raise ValueError(
            "Query Bank manifest IA answer counts do not match records"
        )
    return counts


def validate_query_bank(
    project_root: Path,
    bank_id: str,
    dataset_id: str,
) -> dict[str, Any]:
    paths = QueryBankPaths(project_root.resolve(), bank_id, dataset_id)
    bank = QueryBank.load(paths)
    source_run_id = str(bank.manifest["source_run_id"])
    current_rows = load_run_documents(
        project_root.resolve(), source_run_id, dataset_id
    )
    current = {str(row["doc_id"]): row for row in current_rows}
    grouped: dict[str, list[dict[str, Any]]] = {}
    for record in bank.records:
        grouped.setdefault(str(record["doc_id"]), []).append(record)
    reports = []
    manifest_benign_policy = bank.manifest.get("benign_policy")
    if manifest_benign_policy is not None and not isinstance(manifest_benign_policy, Mapping):
        raise ValueError("Query Bank benign_policy must be a mapping")
    require_balanced_ia = "ia_min_answer_counts" in bank.manifest
    for document in bank.documents:
        doc_id = str(document["doc_id"])
        if doc_id not in current:
            raise ValueError(f"Query Bank document is missing from source run: {doc_id}")
        current_hash = document_sha256(str(current[doc_id]["text"]))
        if current_hash != document["source_document_sha256"]:
            raise ValueError(f"Source document hash changed: {doc_id}")
        reports.append(
            validate_document_records(
                grouped.get(doc_id, []),
                document,
                require_balanced_ia=require_balanced_ia,
                benign_policy=manifest_benign_policy,
            )
        )
    _validated_ia_answer_counts(bank)
    return {
        "status": "valid",
        "bank_id": bank.bank_id,
        "dataset_id": bank.dataset_id,
        "queries_sha256": bank.sha256,
        "document_count": len(bank.documents),
        "query_count": len(bank.records),
        "validated_documents": len(reports),
    }


def inspect_query_bank(
    project_root: Path,
    bank_id: str,
    dataset_id: str,
) -> dict[str, Any]:
    bank = QueryBank.load(
        QueryBankPaths(project_root.resolve(), bank_id, dataset_id)
    )
    ia_answers = _validated_ia_answer_counts(bank)
    return {
        "status": str(bank.manifest["status"]),
        "bank_id": bank.bank_id,
        "dataset_id": bank.dataset_id,
        "queries_sha256": bank.sha256,
        "document_count": len(bank.documents),
        "query_count": len(bank.records),
        "counts_by_attack": dict(
            sorted(Counter(row["attack_type"] for row in bank.records).items())
        ),
        "counts_by_variant": dict(
            sorted(Counter(row["variant_type"] for row in bank.records).items())
        ),
        "ia_answers": ia_answers,
        "benign_categories": dict(
            sorted(
                Counter(
                    row["payload"]["category"]
                    for row in bank.records
                    if row["attack_type"] == "benign"
                ).items()
            )
        ),
    }
