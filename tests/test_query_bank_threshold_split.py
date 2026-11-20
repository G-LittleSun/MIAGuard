from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from miaguard.query_bank.storage import QueryBank
from miaguard.query_bank.threshold_split import (
    build_threshold_split,
    derive_threshold_split_from_parent,
    freeze_threshold_split,
    validate_threshold_split,
)


def _bank(*, per_class: int = 50) -> QueryBank:
    documents = []
    records = []
    for membership_label, prefix in ((1, "member"), (0, "nonmember")):
        for index in range(per_class):
            doc_id = f"{prefix}-{index:03d}"
            documents.append(
                {
                    "dataset_id": "ag_news",
                    "doc_id": doc_id,
                    "membership_label": membership_label,
                    "source_document_sha256": f"sha-{doc_id}",
                }
            )
            records.append(
                {
                    "query_id": f"query-{doc_id}",
                    "dataset_id": "ag_news",
                    "doc_id": doc_id,
                    "membership_label": membership_label,
                    "traffic_type": "benign",
                    "attack_type": "benign",
                    "validation": {"status": "accepted"},
                }
            )
    return QueryBank(
        bank_id="ag_news_queries_v1",
        dataset_id="ag_news",
        sha256="a" * 64,
        records=tuple(records),
        documents=tuple(documents),
        manifest={"status": "complete"},
    )


def test_build_split_is_deterministic_balanced_and_disjoint() -> None:
    bank = _bank()

    first = build_threshold_split(bank, split_id="threshold-v1", seed=20260818)
    second = build_threshold_split(bank, split_id="threshold-v1", seed=20260818)

    assert first == second
    expected_per_class = {"train": 30, "validation": 10, "test": 10}
    seen: set[str] = set()
    for partition, count in expected_per_class.items():
        row = first["partitions"][partition]
        assert len(row["member_doc_ids"]) == count
        assert len(row["nonmember_doc_ids"]) == count
        assert row["document_count"] == count * 2
        current = set(row["doc_ids"])
        assert not seen.intersection(current)
        seen.update(current)
    assert len(seen) == 100
    validate_threshold_split(first, bank)


def test_split_rejects_record_membership_that_disagrees_with_document() -> None:
    bank = _bank()
    bad_record = dict(bank.records[0])
    bad_record["membership_label"] = 0
    bad_bank = QueryBank(
        bank_id=bank.bank_id,
        dataset_id=bank.dataset_id,
        sha256=bank.sha256,
        records=(bad_record, *bank.records[1:]),
        documents=bank.documents,
        manifest=bank.manifest,
    )

    with pytest.raises(ValueError, match="membership_label"):
        build_threshold_split(bad_bank, split_id="threshold-v1", seed=17)


def test_freeze_split_matches_schema_and_refuses_overwrite(tmp_path: Path) -> None:
    bank = _bank()
    split = build_threshold_split(bank, split_id="threshold-v1", seed=17)
    output = tmp_path / "threshold-v1.json"

    freeze_threshold_split(split, output)

    frozen = json.loads(output.read_text(encoding="utf-8"))
    schema_path = Path("schemas/query_bank_threshold_split.schema.json")
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(frozen)
    with pytest.raises(FileExistsError, match="already exists"):
        freeze_threshold_split(split, output)


def test_validation_enforces_fixed_counts_and_accepted_query_counts() -> None:
    bank = _bank()
    split = build_threshold_split(bank, split_id="threshold-v1", seed=17)
    split["partitions"]["train"]["accepted_query_count"] += 1
    with pytest.raises(ValueError, match="accepted_query_count"):
        validate_threshold_split(split, bank)

    split = build_threshold_split(bank, split_id="threshold-v1", seed=17)
    moved_member = split["partitions"]["train"]["member_doc_ids"].pop()
    split["partitions"]["train"]["doc_ids"].remove(moved_member)
    split["partitions"]["train"]["document_count"] -= 1
    split["partitions"]["validation"]["member_doc_ids"].append(moved_member)
    split["partitions"]["validation"]["doc_ids"].append(moved_member)
    split["partitions"]["validation"]["document_count"] += 1
    with pytest.raises(ValueError, match="30 member"):
        validate_threshold_split(split, bank)


def test_derive_v2_split_preserves_parent_document_assignments() -> None:
    parent_bank = _bank()
    parent_split = build_threshold_split(
        parent_bank,
        split_id="ag_news_threshold_v1",
        seed=20260818,
    )
    v2_bank = QueryBank(
        bank_id="ag_news_queries_v2",
        dataset_id=parent_bank.dataset_id,
        sha256="b" * 64,
        records=parent_bank.records,
        documents=parent_bank.documents,
        manifest={"status": "complete"},
    )

    derived = derive_threshold_split_from_parent(
        v2_bank,
        parent_split,
        split_id="ag_news_threshold_v2",
    )

    assert derived["query_bank"]["bank_id"] == "ag_news_queries_v2"
    assert derived["query_bank"]["queries_sha256"] == "b" * 64
    assert derived["derived_from_split_id"] == "ag_news_threshold_v1"
    for partition in ("train", "validation", "test"):
        assert derived["partitions"][partition]["doc_ids"] == parent_split[
            "partitions"
        ][partition]["doc_ids"]
        assert derived["partitions"][partition]["member_doc_ids"] == parent_split[
            "partitions"
        ][partition]["member_doc_ids"]
        assert derived["partitions"][partition]["nonmember_doc_ids"] == parent_split[
            "partitions"
        ][partition]["nonmember_doc_ids"]
    validate_threshold_split(derived, v2_bank)
