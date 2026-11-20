from __future__ import annotations

from collections import Counter
from pathlib import Path

import pytest

from miaguard.query_bank.sampler import sample_query_bank
from miaguard.query_bank.schema import (
    document_sha256,
    load_query_bank_config,
    make_query_id,
    validate_query_record,
)
from miaguard.query_bank.storage import (
    QueryBank,
    QueryBankPaths,
    compact_query_bank,
    write_document_shard,
)
from miaguard.query_bank.validator import (
    inspect_query_bank,
    validate_document_records,
)
from rag_mia_data.io_utils import write_json_atomic


def _record(
    doc_id: str,
    membership_label: int,
    attack_type: str,
    variant_type: str,
    query_index: int,
    *,
    answer: str | None = None,
    category: str | None = None,
) -> dict:
    payload: dict = {}
    query_text = f"{attack_type} query {query_index} for {doc_id}"
    if attack_type == "direct_rag_mia":
        payload = {"target_text": f"source {doc_id}"}
    elif attack_type == "s2_mia":
        payload = {"prefix": f"prefix {doc_id}"}
    elif attack_type == "masked_mia":
        payload = {
            "masked_text": f"source [Mask_1] {doc_id}",
            "answers": ["answer"],
            "selection_sources": ["model"],
        }
        query_text = f"Fill [Mask_1] for {doc_id}"
    elif attack_type == "ia":
        payload = {
            "question": f"Is fact {query_index} true for {doc_id}?",
            "ground_truth": answer,
            "summary": f"topic {doc_id}",
        }
    elif attack_type == "benign":
        payload = {"category": category}
    record = {
        "query_id": make_query_id(
            "ag_news", doc_id, attack_type, variant_type, query_index
        ),
        "dataset_id": "ag_news",
        "doc_id": doc_id,
        "membership_label": membership_label,
        "source_document_sha256": document_sha256(f"source {doc_id}"),
        "traffic_type": "benign" if attack_type == "benign" else "attack",
        "attack_type": attack_type,
        "variant_type": variant_type,
        "query_index": query_index,
        "query_text": query_text,
        "payload": payload,
        "generation": {
            "backend": "test",
            "model": "test-model",
            "prompt_version": "test-v1",
            "temperature": 0.0,
            "seed": 17,
        },
        "validation": {
            "status": "accepted",
            "answer_verified": True,
            "duplicate_checked": True,
        },
        "created_at": "2026-07-25T00:00:00+00:00",
    }
    validate_query_record(record)
    return record


def _document_records(doc_id: str, membership_label: int) -> list[dict]:
    rows: list[dict] = []
    for attack in ("direct_rag_mia", "s2_mia", "masked_mia"):
        rows.append(_record(doc_id, membership_label, attack, "canonical", 1))
        rows.extend(
            _record(doc_id, membership_label, attack, "paraphrase", index)
            for index in range(1, 5)
        )
    rows.extend(
        _record(
            doc_id,
            membership_label,
            "ia",
            "generated",
            index,
            answer="yes" if index <= 15 else "no",
        )
        for index in range(1, 31)
    )
    categories = ("topic", "entity", "event", "summary", "follow_up")
    rows.extend(
        _record(
            doc_id,
            membership_label,
            "benign",
            "generated",
            index,
            category=category,
        )
        for index, category in enumerate(categories, start=1)
    )
    return rows


def _replace_ia_answers(rows: list[dict], answers: tuple[str, ...]) -> None:
    ia_rows = [row for row in rows if row["attack_type"] == "ia"]
    for index, row in enumerate(ia_rows):
        row["payload"]["ground_truth"] = answers[index % len(answers)]


def _bank_with_ia_answers(
    tmp_path: Path,
    documents_with_answers: list[tuple[str, int, tuple[str, ...]]],
) -> QueryBank:
    paths = QueryBankPaths(tmp_path, "bank-1", "ag_news")
    documents = []
    for doc_id, membership_label, answers in documents_with_answers:
        documents.append(
            {
                "dataset_id": "ag_news",
                "doc_id": doc_id,
                "membership_label": membership_label,
                "source_document_sha256": document_sha256(f"source {doc_id}"),
            }
        )
        rows = _document_records(doc_id, membership_label)
        _replace_ia_answers(rows, answers)
        write_document_shard(paths, doc_id, rows)
    digest = compact_query_bank(paths, documents)
    write_json_atomic(
        paths.manifest,
        {
            "bank_id": "bank-1",
            "dataset_id": "ag_news",
            "status": "complete",
            "queries_sha256": digest,
        },
    )
    return QueryBank.load(paths)


def test_config_requires_30_teacher_aligned_ia_queries(tmp_path: Path) -> None:
    config_path = tmp_path / "bank.yaml"
    config_path.write_text(
        """
source_run_id: run-1
attack_config: configs/attacks/ag_news_calibrated_int8.yaml
seed: 17
pool:
  members: 10
  nonmembers: 10
queries:
  paraphrases_per_attack: 4
  ia_questions_per_document: 30
  ia_batch_size: 6
  ia_max_attempts: 20
  benign_categories: [topic, entity, event, summary, follow_up]
""".strip(),
        encoding="utf-8",
    )

    config = load_query_bank_config(config_path)

    assert config.ia_questions_per_document == 30
    assert config.ia_total == 30
    assert config.member_count == 10


def test_ia_record_accepts_unknown_ground_truth() -> None:
    record = _record(
        "doc-1",
        1,
        "ia",
        "generated",
        1,
        answer="unknown",
    )

    validate_query_record(record)


def test_v2_benign_payload_requires_consistent_difficulty_metadata() -> None:
    hard = _record(
        "doc-1", 1, "benign", "generated", 1, category="topic"
    )
    hard["payload"].update(
        {
            "difficulty": "hard",
            "hard_scenario": "quoted_context_interpretation",
            "benign_intent": "ordinary information-seeking intent",
        }
    )
    validate_query_record(hard)

    missing_scenario = dict(hard)
    missing_scenario["payload"] = dict(hard["payload"])
    missing_scenario["payload"]["hard_scenario"] = None
    with pytest.raises(ValueError, match="hard_scenario"):
        validate_query_record(missing_scenario)

    standard_with_scenario = dict(hard)
    standard_with_scenario["payload"] = dict(hard["payload"])
    standard_with_scenario["payload"]["difficulty"] = "standard"
    with pytest.raises(ValueError, match="standard"):
        validate_query_record(standard_with_scenario)

    unknown_scenario = dict(hard)
    unknown_scenario["payload"] = dict(hard["payload"])
    unknown_scenario["payload"]["hard_scenario"] = "unapproved_scenario"
    with pytest.raises(ValueError, match="hard_scenario"):
        validate_query_record(unknown_scenario)


def test_document_validation_accepts_flexible_v2_benign_policy() -> None:
    rows = [row for row in _document_records("doc-1", 1) if row["attack_type"] != "benign"]
    categories = ("topic", "entity", "event", "summary", "follow_up")
    for index, category in enumerate(categories, start=1):
        row = _record("doc-1", 1, "benign", "generated", index, category=category)
        row["payload"].update(
            {
                "difficulty": "standard",
                "hard_scenario": None,
                "benign_intent": "ordinary information-seeking intent",
            }
        )
        rows.append(row)
    extra = _record("doc-1", 1, "benign", "generated", 6, category="topic")
    extra["query_text"] = "additional ordinary topic question"
    extra["payload"].update(
        {
            "difficulty": "standard",
            "hard_scenario": None,
            "benign_intent": "ordinary information-seeking intent",
        }
    )
    rows.append(extra)

    report = validate_document_records(
        rows,
        {
            "dataset_id": "ag_news",
            "doc_id": "doc-1",
            "membership_label": 1,
            "source_document_sha256": document_sha256("source doc-1"),
        },
        benign_policy={
            "minimum_per_document": 5,
            "soft_target_per_document": 20,
            "optional_hard_per_document": 2,
        },
    )

    assert report["benign_difficulty_counts"] == {"standard": 6}


def test_document_validation_accepts_balanced_pool_with_unknowns() -> None:
    rows = _document_records("doc-1", 1)
    rows.extend(
        _record(
            "doc-1",
            1,
            "ia",
            "generated",
            index,
            answer="unknown",
        )
        for index in range(31, 41)
    )

    report = validate_document_records(
        rows,
        {
            "dataset_id": "ag_news",
            "doc_id": "doc-1",
            "membership_label": 1,
            "source_document_sha256": document_sha256("source doc-1"),
        },
    )

    assert report["query_count"] == 60
    assert report["ia_answers"] == {
        "yes": 15,
        "no": 15,
        "unknown": 10,
    }
    assert report["counts"]["benign"] == 5


def test_document_validation_requires_ten_yes_and_no_ia_answers() -> None:
    rows = _document_records("doc-1", 1)
    for row in [
        row
        for row in rows
        if row["attack_type"] == "ia" and row["payload"]["ground_truth"] == "yes"
    ][:6]:
        row["payload"]["ground_truth"] = "unknown"

    with pytest.raises(ValueError, match="at least 10 yes and 10 no"):
        validate_document_records(
            rows,
            {
                "dataset_id": "ag_news",
                "doc_id": "doc-1",
                "membership_label": 1,
                "source_document_sha256": document_sha256("source doc-1"),
            },
        )


def test_document_validation_can_read_legacy_three_label_distribution() -> None:
    rows = _document_records("doc-1", 1)
    for row in [
        row
        for row in rows
        if row["attack_type"] == "ia" and row["payload"]["ground_truth"] == "yes"
    ][:5]:
        row["payload"]["ground_truth"] = "unknown"

    report = validate_document_records(
        rows,
        {
            "dataset_id": "ag_news",
            "doc_id": "doc-1",
            "membership_label": 1,
            "source_document_sha256": document_sha256("source doc-1"),
        },
        require_balanced_ia=False,
    )

    assert report["ia_answers"] == {"no": 15, "unknown": 5, "yes": 10}


def test_document_validation_rejects_duplicate_ia_question() -> None:
    rows = _document_records("doc-1", 1)
    ia_rows = [row for row in rows if row["attack_type"] == "ia"]
    ia_rows[1]["payload"]["question"] = ia_rows[0]["payload"]["question"]

    with pytest.raises(ValueError, match="duplicate IA"):
        validate_document_records(
            rows,
            {
                "dataset_id": "ag_news",
                "doc_id": "doc-1",
                "membership_label": 1,
                "source_document_sha256": document_sha256("source doc-1"),
            },
        )


def test_compact_and_load_query_bank(tmp_path: Path) -> None:
    paths = QueryBankPaths(tmp_path, "bank-1", "ag_news")
    documents = [
        {
            "dataset_id": "ag_news",
            "doc_id": "doc-1",
            "membership_label": 1,
            "source_document_sha256": document_sha256("source doc-1"),
        },
        {
            "dataset_id": "ag_news",
            "doc_id": "doc-2",
            "membership_label": 0,
            "source_document_sha256": document_sha256("source doc-2"),
        },
    ]
    write_document_shard(paths, "doc-2", _document_records("doc-2", 0))
    write_document_shard(paths, "doc-1", _document_records("doc-1", 1))
    digest = compact_query_bank(paths, documents)
    write_json_atomic(
        paths.manifest,
        {
            "bank_id": "bank-1",
            "dataset_id": "ag_news",
            "status": "complete",
            "queries_sha256": digest,
            "ia_answer_counts": {
                "yes": 30,
                "no": 30,
            },
        },
    )

    bank = QueryBank.load(paths)
    report = inspect_query_bank(tmp_path, "bank-1", "ag_news")

    assert len(bank.records) == 100
    assert bank.sha256 == digest
    assert bank.records[0]["doc_id"] == "doc-1"
    assert report["ia_answers"] == {
        "no": 30,
        "yes": 30,
    }


def test_inspection_rejects_manifest_ia_answer_count_mismatch(
    tmp_path: Path,
) -> None:
    paths = QueryBankPaths(tmp_path, "bank-1", "ag_news")
    documents = [
        {
            "dataset_id": "ag_news",
            "doc_id": "doc-1",
            "membership_label": 1,
            "source_document_sha256": document_sha256("source doc-1"),
        }
    ]
    write_document_shard(paths, "doc-1", _document_records("doc-1", 1))
    digest = compact_query_bank(paths, documents)
    write_json_atomic(
        paths.manifest,
        {
            "bank_id": "bank-1",
            "dataset_id": "ag_news",
            "status": "complete",
            "queries_sha256": digest,
            "ia_answer_counts": {"yes": 30},
        },
    )

    with pytest.raises(ValueError, match="IA answer counts"):
        inspect_query_bank(tmp_path, "bank-1", "ag_news")


def test_sampling_is_reproducible_and_uses_one_common_cohort(tmp_path: Path) -> None:
    paths = QueryBankPaths(tmp_path, "bank-1", "ag_news")
    documents = []
    for membership_label, prefix in ((1, "member"), (0, "nonmember")):
        for index in range(4):
            doc_id = f"{prefix}-{index}"
            documents.append(
                {
                    "dataset_id": "ag_news",
                    "doc_id": doc_id,
                    "membership_label": membership_label,
                    "source_document_sha256": document_sha256(f"source {doc_id}"),
                }
            )
            write_document_shard(
                paths,
                doc_id,
                _document_records(doc_id, membership_label),
            )
    digest = compact_query_bank(paths, documents)
    write_json_atomic(
        paths.manifest,
        {
            "bank_id": "bank-1",
            "dataset_id": "ag_news",
            "status": "complete",
            "queries_sha256": digest,
        },
    )
    bank = QueryBank.load(paths)

    first = sample_query_bank(
        bank,
        limit_per_class=2,
        benign_count=4,
        ia_turn_count=3,
        seed=17,
        variant_mode="canonical",
    )
    second = sample_query_bank(
        bank,
        limit_per_class=2,
        benign_count=4,
        ia_turn_count=3,
        seed=17,
        variant_mode="canonical",
    )

    assert first == second
    assert first["online_query_generation"] is False
    assert first["selected_doc_ids"]["direct_rag_mia"] == first[
        "selected_doc_ids"
    ]["ia"]
    assert all(len(row["queries"]) == 3 for row in first["attacks"]["ia"])
    selected_answers = Counter(
        query["ground_truth"]
        for query in first["attacks"]["ia"][0]["queries"]
    )
    assert sorted(selected_answers.values()) == [1, 2]

    balanced = sample_query_bank(
        bank,
        limit_per_class=2,
        benign_count=4,
        ia_turn_count=3,
        seed=2,
        variant_mode="canonical",
    )
    assert Counter(
        row["membership_label"] for row in balanced["benign"]
    ) == {1: 2, 0: 2}


def test_sampling_filters_documents_without_balanced_ia_capacity(
    tmp_path: Path,
) -> None:
    bank = _bank_with_ia_answers(
        tmp_path,
        [
            ("member-ineligible", 1, ("yes", "unknown")),
            ("member-0", 1, ("yes", "no", "unknown")),
            ("member-1", 1, ("yes", "no", "unknown")),
            ("nonmember-ineligible", 0, ("yes", "unknown")),
            ("nonmember-0", 0, ("yes", "no", "unknown")),
            ("nonmember-1", 0, ("yes", "no", "unknown")),
        ],
    )

    selection = sample_query_bank(
        bank,
        limit_per_class=2,
        benign_count=4,
        ia_turn_count=3,
        seed=17,
        variant_mode="canonical",
    )

    selected = selection["selected_doc_ids"]["ia"]
    assert "member-ineligible" not in selected
    assert "nonmember-ineligible" not in selected


def test_sampling_reports_insufficient_ia_eligible_members(
    tmp_path: Path,
) -> None:
    bank = _bank_with_ia_answers(
        tmp_path,
        [
            ("member-ineligible", 1, ("yes", "unknown")),
            ("member-eligible", 1, ("yes", "no", "unknown")),
            ("nonmember-0", 0, ("yes", "no", "unknown")),
            ("nonmember-1", 0, ("yes", "no", "unknown")),
        ],
    )

    with pytest.raises(ValueError, match="enough member documents"):
        sample_query_bank(
            bank,
            limit_per_class=2,
            benign_count=4,
            ia_turn_count=3,
            seed=17,
            variant_mode="canonical",
        )
