from __future__ import annotations

import hashlib
import random
from collections import Counter, defaultdict
from typing import Any

from .storage import QueryBank


ATTACKS = ("direct_rag_mia", "s2_mia", "masked_mia", "ia")


def _seed(seed: int, namespace: str) -> int:
    digest = hashlib.sha256(f"{seed}:{namespace}".encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big")


def _has_balanced_ia_capacity(
    records: list[dict[str, Any]], turn_count: int
) -> bool:
    required_per_answer = (turn_count + 1) // 2
    counts = Counter(
        str(row["payload"]["ground_truth"])
        for row in records
    )
    return (
        counts["yes"] >= required_per_answer
        and counts["no"] >= required_per_answer
    )


def _single_attack_row(record: dict[str, Any]) -> dict[str, Any]:
    row = {
        "doc_id": str(record["doc_id"]),
        "membership_label": int(record["membership_label"]),
        "query_id": str(record["query_id"]),
        "attack_query": str(record["query_text"]),
    }
    if record["attack_type"] == "s2_mia":
        row["prefix"] = str(record["payload"]["prefix"])
    if record["attack_type"] == "masked_mia":
        row["masked_text"] = str(record["payload"]["masked_text"])
        row["answers"] = [str(value) for value in record["payload"]["answers"]]
    return row


def _choose_single(
    records: list[dict[str, Any]],
    variant_mode: str,
    rng: random.Random,
) -> dict[str, Any]:
    if variant_mode == "canonical":
        candidates = [row for row in records if row["variant_type"] == "canonical"]
    elif variant_mode == "paraphrase":
        candidates = [row for row in records if row["variant_type"] == "paraphrase"]
    elif variant_mode == "mixed":
        chosen = "canonical" if rng.random() < 0.5 else "paraphrase"
        candidates = [row for row in records if row["variant_type"] == chosen]
    else:
        raise ValueError(f"Unsupported variant mode: {variant_mode}")
    if not candidates:
        raise ValueError(f"No {variant_mode} query is available")
    return candidates[rng.randrange(len(candidates))]


def _choose_ia(
    records: list[dict[str, Any]],
    turn_count: int,
    rng: random.Random,
) -> list[dict[str, Any]]:
    if not 1 <= turn_count <= 30:
        raise ValueError("IA turn count must be between 1 and 30")
    by_answer = {
        answer: [
            row
            for row in records
            if row["payload"]["ground_truth"] == answer
        ]
        for answer in ("yes", "no")
    }
    rng.shuffle(by_answer["yes"])
    rng.shuffle(by_answer["no"])
    yes_count = turn_count // 2
    no_count = turn_count // 2
    if turn_count % 2:
        if rng.randrange(2) == 0:
            yes_count += 1
        else:
            no_count += 1
    selected = by_answer["yes"][:yes_count] + by_answer["no"][:no_count]
    if len(selected) != turn_count:
        raise ValueError("Query Bank does not have enough balanced IA queries")
    rng.shuffle(selected)
    return selected


def sample_query_bank(
    bank: QueryBank,
    *,
    limit_per_class: int,
    benign_count: int,
    ia_turn_count: int,
    seed: int,
    variant_mode: str,
) -> dict[str, Any]:
    if limit_per_class <= 0 or benign_count <= 0:
        raise ValueError("Sample counts must be positive")
    records_by_doc: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for record in bank.records:
        records_by_doc[str(record["doc_id"])][str(record["attack_type"])].append(
            record
        )
    eligible = [
        document
        for document in bank.documents
        if set(records_by_doc[str(document["doc_id"])]) >= {*ATTACKS, "benign"}
        and _has_balanced_ia_capacity(
            records_by_doc[str(document["doc_id"])]["ia"], ia_turn_count
        )
    ]
    members = [row for row in eligible if int(row["membership_label"]) == 1]
    nonmembers = [row for row in eligible if int(row["membership_label"]) == 0]
    member_rng = random.Random(_seed(seed, "member-documents"))
    nonmember_rng = random.Random(_seed(seed, "nonmember-documents"))
    member_rng.shuffle(members)
    nonmember_rng.shuffle(nonmembers)
    if len(members) < limit_per_class:
        raise ValueError("Query Bank does not have enough member documents")
    if len(nonmembers) < limit_per_class:
        raise ValueError("Query Bank does not have enough nonmember documents")
    cohort = members[:limit_per_class] + nonmembers[:limit_per_class]
    attacks: dict[str, list[dict[str, Any]]] = {attack: [] for attack in ATTACKS}
    audit_ids: dict[str, list[str]] = {attack: [] for attack in ATTACKS}
    for attack in ATTACKS:
        for document in cohort:
            doc_id = str(document["doc_id"])
            rng = random.Random(_seed(seed, f"{attack}:{doc_id}"))
            candidates = records_by_doc[doc_id][attack]
            if attack == "ia":
                selected = _choose_ia(candidates, ia_turn_count, rng)
                attacks[attack].append(
                    {
                        "doc_id": doc_id,
                        "membership_label": int(document["membership_label"]),
                        "summary": str(selected[0]["payload"]["summary"]),
                        "queries": [
                            {
                                "adversarial_query": str(row["query_text"]),
                                "ground_truth": str(
                                    row["payload"]["ground_truth"]
                                ),
                                "question": str(row["payload"]["question"]),
                                "query_id": str(row["query_id"]),
                            }
                            for row in selected
                        ],
                    }
                )
                audit_ids[attack].extend(
                    str(row["query_id"]) for row in selected
                )
            else:
                selected = _choose_single(candidates, variant_mode, rng)
                attacks[attack].append(_single_attack_row(selected))
                audit_ids[attack].append(str(selected["query_id"]))
    benign_member_count = (benign_count + 1) // 2
    benign_nonmember_count = benign_count // 2
    if len(members) < benign_member_count or len(nonmembers) < benign_nonmember_count:
        raise ValueError("Query Bank does not have enough balanced benign documents")
    benign_pool = (
        members[:benign_member_count]
        + nonmembers[:benign_nonmember_count]
    )
    benign_rng = random.Random(_seed(seed, "benign"))
    benign_rng.shuffle(benign_pool)
    benign_rows: list[dict[str, Any]] = []
    benign_ids: list[str] = []
    categories = ("topic", "entity", "event", "summary", "follow_up")
    for index, document in enumerate(benign_pool[:benign_count]):
        doc_id = str(document["doc_id"])
        category = categories[index % len(categories)]
        candidates = [
            row
            for row in records_by_doc[doc_id]["benign"]
            if row["payload"]["category"] == category
        ]
        selected = candidates[0]
        benign_rows.append(
            {
                "doc_id": doc_id,
                "membership_label": int(document["membership_label"]),
                "query_id": str(selected["query_id"]),
                "query_text": str(selected["query_text"]),
                "category": category,
            }
        )
        benign_ids.append(str(selected["query_id"]))
    selected_doc_ids = {
        attack: [str(row["doc_id"]) for row in cohort] for attack in ATTACKS
    }
    return {
        "query_bank_id": bank.bank_id,
        "query_bank_sha256": bank.sha256,
        "query_seed": seed,
        "variant_mode": variant_mode,
        "online_query_generation": False,
        "attacks": attacks,
        "benign": benign_rows,
        "selected_doc_ids": selected_doc_ids,
        "selected_query_ids": {**audit_ids, "benign": benign_ids},
    }
