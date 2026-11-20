from __future__ import annotations

import hashlib
import math
import random
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from .storage import QueryBank
from .threshold_split import PARTITIONS


@dataclass(frozen=True)
class PlannedSession:
    session_key: str
    partition: str
    doc_id: str
    membership_label: int
    traffic_type: str
    attack_type: str
    session_index: int
    queries: tuple[dict[str, Any], ...]


def balanced_session_sizes(
    count: int,
    target_turns: int = 5,
) -> tuple[int, ...]:
    if count <= 0:
        raise ValueError("count must be positive")
    if target_turns <= 0:
        raise ValueError("target_turns must be positive")
    session_count = math.ceil(count / target_turns)
    base, extra = divmod(count, session_count)
    return tuple(
        base + (1 if index < extra else 0)
        for index in range(session_count)
    )


def _variant_sort_key(record: Mapping[str, Any]) -> tuple[int, int, str]:
    priority = {"canonical": 0, "paraphrase": 1, "generated": 2}
    return (
        priority.get(str(record.get("variant_type")), 3),
        int(record.get("query_index", 0)),
        str(record["query_id"]),
    )


def _partition_doc_ids(split: Mapping[str, Any], partition: str) -> set[str]:
    if partition not in PARTITIONS:
        raise ValueError(f"Unsupported partition: {partition}")
    partitions = split.get("partitions")
    if not isinstance(partitions, Mapping):
        raise ValueError("split partitions must be a mapping")
    row = partitions.get(partition)
    if not isinstance(row, Mapping):
        raise ValueError(f"Missing split partition: {partition}")
    doc_ids = [str(value) for value in row.get("doc_ids", [])]
    if len(doc_ids) != len(set(doc_ids)):
        raise ValueError(f"Split partition {partition} contains duplicate doc_id values")
    return set(doc_ids)


def _v2_benign_session_queries(
    records: Sequence[dict[str, Any]],
    *,
    seed: int,
    doc_id: str,
    target_turns: int,
) -> tuple[tuple[dict[str, Any], ...], ...]:
    if target_turns != 5:
        raise ValueError("v2 benign sessions require target_turns=5")
    standard = sorted(
        (
            row
            for row in records
            if row.get("payload", {}).get("difficulty") == "standard"
        ),
        key=_variant_sort_key,
    )
    hard = sorted(
        (
            row
            for row in records
            if row.get("payload", {}).get("difficulty") == "hard"
        ),
        key=_variant_sort_key,
    )
    if len(standard) != 20 or len(hard) != 5:
        raise ValueError(
            f"v2 benign quota is incomplete for {doc_id}: "
            f"standard={len(standard)} hard={len(hard)}"
        )
    digest = hashlib.sha256(f"{seed}|{doc_id}|v2-benign".encode("utf-8")).digest()
    hard_positions = list(range(target_turns))
    random.Random(int.from_bytes(digest[:8], "big")).shuffle(hard_positions)
    sessions: list[tuple[dict[str, Any], ...]] = []
    for index in range(target_turns):
        queries = list(standard[index * 4 : (index + 1) * 4])
        queries.insert(hard_positions[index], hard[index])
        sessions.append(tuple(queries))
    return tuple(sessions)


def plan_partition_sessions(
    bank: QueryBank,
    split: Mapping[str, Any],
    partition: str,
    *,
    target_turns: int = 5,
) -> tuple[PlannedSession, ...]:
    source = split.get("query_bank")
    expected_source = {
        "bank_id": bank.bank_id,
        "dataset_id": bank.dataset_id,
        "queries_sha256": bank.sha256,
    }
    if not isinstance(source, Mapping) or dict(source) != expected_source:
        raise ValueError("Session split does not match the loaded Query Bank")
    selected_doc_ids = _partition_doc_ids(split, partition)

    labels: dict[str, int] = {}
    for document in bank.documents:
        doc_id = str(document["doc_id"])
        label = int(document["membership_label"])
        if doc_id in labels or label not in (0, 1):
            raise ValueError(f"Invalid document membership_label for {doc_id}")
        labels[doc_id] = label
    if not selected_doc_ids.issubset(labels):
        raise ValueError("Split partition references an unknown Query Bank document")

    groups: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    accepted_ids: list[str] = []
    for record in bank.records:
        doc_id = str(record["doc_id"])
        if doc_id not in selected_doc_ids:
            continue
        if record.get("validation", {}).get("status") != "accepted":
            continue
        if int(record["membership_label"]) != labels[doc_id]:
            raise ValueError(f"Query membership_label mismatch for {doc_id}")
        traffic_type = str(record["traffic_type"])
        attack_type = str(record["attack_type"])
        expected_traffic = "benign" if attack_type == "benign" else "attack"
        if traffic_type != expected_traffic:
            raise ValueError(f"Query traffic_type mismatch for {record['query_id']}")
        groups[(doc_id, traffic_type, attack_type)].append(record)
        accepted_ids.append(str(record["query_id"]))
    if len(accepted_ids) != len(set(accepted_ids)):
        raise ValueError("Accepted Query Bank records contain duplicate query_id values")

    sessions: list[PlannedSession] = []
    for doc_id, traffic_type, attack_type in sorted(groups):
        records = sorted(groups[(doc_id, traffic_type, attack_type)], key=_variant_sort_key)
        sizes = balanced_session_sizes(len(records), target_turns)
        if min(sizes) < 3 or max(sizes) > target_turns:
            raise ValueError(
                f"Group {doc_id}/{attack_type} cannot form 3-{target_turns} turn sessions"
            )
        offset = 0
        query_groups = []
        for size in sizes:
            query_groups.append(tuple(records[offset : offset + size]))
            offset += size
        for session_index, queries in enumerate(query_groups, start=1):
            session_key = (
                f"{split['split_id']}:{partition}:{traffic_type}:"
                f"{attack_type}:{doc_id}:"
                f"{session_index:03d}"
            )
            sessions.append(
                PlannedSession(
                    session_key=session_key,
                    partition=partition,
                    doc_id=doc_id,
                    membership_label=labels[doc_id],
                    traffic_type=traffic_type,
                    attack_type=attack_type,
                    session_index=session_index,
                    queries=queries,
                )
            )

    planned_ids = [
        str(query["query_id"])
        for session in sessions
        for query in session.queries
    ]
    if len(planned_ids) != len(set(planned_ids)):
        raise ValueError("Session plan uses a query more than once")
    if set(planned_ids) != set(accepted_ids):
        raise ValueError("Session plan does not use every accepted partition query")
    return tuple(sessions)


def session_plan_summary(
    sessions: Sequence[PlannedSession],
) -> dict[str, Any]:
    query_count = sum(len(session.queries) for session in sessions)
    benign_layouts = Counter(
        "standard="
        + str(
            sum(
                query.get("payload", {}).get("difficulty") == "standard"
                for query in session.queries
            )
        )
        + ",hard="
        + str(
            sum(
                query.get("payload", {}).get("difficulty") == "hard"
                for query in session.queries
            )
        )
        for session in sessions
        if session.attack_type == "benign"
        and any("difficulty" in query.get("payload", {}) for query in session.queries)
    )
    return {
        "partition": sessions[0].partition if sessions else None,
        "document_count": len({session.doc_id for session in sessions}),
        "session_count": len(sessions),
        "query_count": query_count,
        "session_length_counts": {
            str(key): value
            for key, value in sorted(
                Counter(len(session.queries) for session in sessions).items()
            )
        },
        "query_counts_by_attack_type": dict(
            sorted(
                Counter(
                    session.attack_type
                    for session in sessions
                    for _query in session.queries
                ).items()
            )
        ),
        "session_counts_by_attack_type": dict(
            sorted(Counter(session.attack_type for session in sessions).items())
        ),
        "benign_session_layout_counts": dict(sorted(benign_layouts.items())),
    }


def audit_full_session_plan(
    bank: QueryBank,
    split: Mapping[str, Any],
    *,
    target_turns: int = 5,
) -> dict[str, Any]:
    partition_summaries: dict[str, Any] = {}
    all_sessions: list[PlannedSession] = []
    for partition in PARTITIONS:
        planned = plan_partition_sessions(
            bank,
            split,
            partition,
            target_turns=target_turns,
        )
        partition_summaries[partition] = session_plan_summary(planned)
        all_sessions.extend(planned)
    planned_ids = [
        str(query["query_id"])
        for session in all_sessions
        for query in session.queries
    ]
    accepted_ids = [
        str(record["query_id"])
        for record in bank.records
        if record.get("validation", {}).get("status") == "accepted"
    ]
    duplicates = sorted(
        query_id
        for query_id, count in Counter(planned_ids).items()
        if count > 1
    )
    return {
        "schema_version": 1,
        "query_bank": {
            "bank_id": bank.bank_id,
            "dataset_id": bank.dataset_id,
            "queries_sha256": bank.sha256,
        },
        "split_id": str(split["split_id"]),
        "target_turns": target_turns,
        "partitions": partition_summaries,
        "totals": {
            "document_count": len({session.doc_id for session in all_sessions}),
            "session_count": len(all_sessions),
            "query_count": len(planned_ids),
            "accepted_query_count": len(accepted_ids),
            "query_counts_by_attack_type": dict(
                sorted(
                    Counter(
                        session.attack_type
                        for session in all_sessions
                        for _query in session.queries
                    ).items()
                )
            ),
            "session_length_counts": {
                str(key): value
                for key, value in sorted(
                    Counter(len(session.queries) for session in all_sessions).items()
                )
            },
        },
        "missing_query_ids": sorted(set(accepted_ids).difference(planned_ids)),
        "unexpected_query_ids": sorted(set(planned_ids).difference(accepted_ids)),
        "duplicate_query_ids": duplicates,
    }
