from __future__ import annotations

from collections import Counter

import pytest

from miaguard.query_bank.sessions import (
    balanced_session_sizes,
    plan_partition_sessions,
    session_plan_summary,
)
from miaguard.query_bank.storage import QueryBank


def _record(
    query_id: str,
    attack_type: str,
    index: int,
    *,
    status: str = "accepted",
) -> dict:
    return {
        "query_id": query_id,
        "dataset_id": "ag_news",
        "doc_id": "doc-1",
        "membership_label": 1,
        "traffic_type": "benign" if attack_type == "benign" else "attack",
        "attack_type": attack_type,
        "variant_type": (
            "canonical" if index == 1 and attack_type != "ia" else "generated"
        ),
        "query_index": index,
        "query_text": query_id,
        "validation": {"status": status},
    }


def _bank(*, ia_count: int = 31) -> QueryBank:
    records = []
    for attack_type in ("benign", "direct_rag_mia", "s2_mia", "masked_mia"):
        records.extend(
            _record(f"{attack_type}-{index}", attack_type, index)
            for index in range(1, 6)
        )
    records.extend(
        _record(f"ia-{index}", "ia", index) for index in range(1, ia_count + 1)
    )
    records.append(_record("rejected", "ia", ia_count + 1, status="rejected"))
    return QueryBank(
        bank_id="bank-v1",
        dataset_id="ag_news",
        sha256="b" * 64,
        records=tuple(records),
        documents=(
            {
                "dataset_id": "ag_news",
                "doc_id": "doc-1",
                "membership_label": 1,
            },
        ),
        manifest={"status": "complete"},
    )


def _split(bank: QueryBank) -> dict:
    return {
        "schema_version": 1,
        "split_id": "split-v1",
        "query_bank": {
            "bank_id": bank.bank_id,
            "dataset_id": bank.dataset_id,
            "queries_sha256": bank.sha256,
        },
        "partitions": {
            "train": {"doc_ids": ["doc-1"]},
            "validation": {"doc_ids": []},
            "test": {"doc_ids": []},
        },
    }


@pytest.mark.parametrize(
    ("count", "expected"),
    (
        (30, (5, 5, 5, 5, 5, 5)),
        (31, (5, 5, 5, 4, 4, 4, 4)),
        (38, (5, 5, 5, 5, 5, 5, 4, 4)),
        (60, (5,) * 12),
    ),
)
def test_balanced_ia_session_sizes_use_every_query(
    count: int, expected: tuple[int, ...]
) -> None:
    assert balanced_session_sizes(count, target_turns=5) == expected


def test_partition_plan_uses_all_accepted_queries_once_without_mixing() -> None:
    bank = _bank(ia_count=31)

    sessions = plan_partition_sessions(bank, _split(bank), "train")

    planned = [query for session in sessions for query in session.queries]
    planned_ids = [str(query["query_id"]) for query in planned]
    accepted_ids = {
        str(record["query_id"])
        for record in bank.records
        if record["validation"]["status"] == "accepted"
    }
    assert set(planned_ids) == accepted_ids
    assert len(planned_ids) == len(set(planned_ids))
    assert "rejected" not in planned_ids
    for session in sessions:
        assert {row["doc_id"] for row in session.queries} == {session.doc_id}
        assert {row["attack_type"] for row in session.queries} == {
            session.attack_type
        }
        assert {row["traffic_type"] for row in session.queries} == {
            session.traffic_type
        }
        assert 3 <= len(session.queries) <= 5

    sizes_by_attack = {
        attack: [len(session.queries) for session in sessions if session.attack_type == attack]
        for attack in ("benign", "direct_rag_mia", "s2_mia", "masked_mia", "ia")
    }
    assert sizes_by_attack["benign"] == [5]
    assert sizes_by_attack["direct_rag_mia"] == [5]
    assert sizes_by_attack["s2_mia"] == [5]
    assert sizes_by_attack["masked_mia"] == [5]
    assert sizes_by_attack["ia"] == [5, 5, 5, 4, 4, 4, 4]


def test_session_plan_is_deterministic_and_reports_audit_counts() -> None:
    bank = _bank(ia_count=38)

    first = plan_partition_sessions(bank, _split(bank), "train")
    second = plan_partition_sessions(bank, _split(bank), "train")
    summary = session_plan_summary(first)

    assert first == second
    assert summary["query_count"] == 58
    assert summary["session_count"] == 12
    assert summary["session_length_counts"] == {"4": 2, "5": 10}
    assert Counter(session.session_key for session in first).most_common(1)[0][1] == 1
    assert all(session.session_key.startswith("split-v1:") for session in first)


def test_v2_benign_sessions_use_generic_grouping_with_optional_hard_queries() -> None:
    source = _bank()
    records = [row for row in source.records if row["attack_type"] != "benign"]
    for index in range(1, 8):
        row = _record(f"benign-{index}", "benign", index)
        row["payload"] = {
            "category": "topic",
            "difficulty": "hard" if index == 7 else "standard",
            "hard_scenario": "quoted_context_interpretation" if index == 7 else None,
        }
        records.append(row)
    bank = QueryBank(
        bank_id=source.bank_id,
        dataset_id=source.dataset_id,
        sha256=source.sha256,
        records=tuple(records),
        documents=source.documents,
        manifest={
            "status": "complete",
            "benign_policy": {
                "minimum_per_document": 5,
                "soft_target_per_document": 20,
                "optional_hard_per_document": 2,
            },
        },
    )

    first = plan_partition_sessions(bank, _split(bank), "train")
    second = plan_partition_sessions(bank, _split(bank), "train")
    benign_sessions = [session for session in first if session.attack_type == "benign"]
    summary = session_plan_summary(first)

    assert first == second
    assert len(benign_sessions) == 2
    assert [len(session.queries) for session in benign_sessions] == [4, 3]
    assert sum(len(session.queries) for session in benign_sessions) == 7
    assert summary["benign_session_layout_counts"] == {
        "standard=4,hard=0": 1,
        "standard=2,hard=1": 1,
    }
