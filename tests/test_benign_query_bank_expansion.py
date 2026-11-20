from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from miaguard.query_bank.benign_expansion import (
    BenignExpansionConfig,
    BenignSlot,
    _default_generator,
    expand_benign_query_bank,
)
from miaguard.query_bank.schema import document_sha256, make_query_id
from miaguard.query_bank.storage import (
    QueryBank,
    QueryBankPaths,
    compact_query_bank,
    write_document_shard,
)
from miaguard.query_bank.validator import normalize_query
from miaguard.query_bank.threshold_split import (
    build_threshold_split,
    freeze_threshold_split,
)
from rag_mia_data.io_utils import write_json_atomic, write_jsonl_atomic


def _record(
    document: dict,
    attack_type: str,
    variant_type: str,
    query_index: int,
    *,
    category: str | None = None,
    answer: str | None = None,
) -> dict:
    payload: dict = {}
    if attack_type == "direct_rag_mia":
        payload = {"target_text": document["text"]}
    elif attack_type == "s2_mia":
        payload = {"prefix": "source opening"}
    elif attack_type == "masked_mia":
        payload = {"masked_text": "[Mask_1]", "answers": ["answer"]}
    elif attack_type == "ia":
        payload = {
            "question": f"Is statement {query_index} correct?",
            "ground_truth": answer,
            "summary": "source summary",
        }
    elif attack_type == "benign":
        payload = {"category": category}
    return {
        "query_id": make_query_id(
            "ag_news", str(document["doc_id"]), attack_type, variant_type, query_index
        ),
        "dataset_id": "ag_news",
        "doc_id": str(document["doc_id"]),
        "membership_label": int(document["membership_label"]),
        "source_document_sha256": document_sha256(str(document["text"])),
        "traffic_type": "benign" if attack_type == "benign" else "attack",
        "attack_type": attack_type,
        "variant_type": variant_type,
        "query_index": query_index,
        "query_text": f"{attack_type} query {query_index} for {document['doc_id']}",
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
        "created_at": "2026-08-30T00:00:00+00:00",
    }


def _document_records(document: dict) -> list[dict]:
    rows = []
    for attack in ("direct_rag_mia", "s2_mia", "masked_mia"):
        rows.append(_record(document, attack, "canonical", 1))
        rows.extend(
            _record(document, attack, "paraphrase", index)
            for index in range(1, 5)
        )
    rows.extend(
        _record(
            document,
            "ia",
            "generated",
            index,
            answer="yes" if index <= 15 else "no",
        )
        for index in range(1, 31)
    )
    rows.extend(
        _record(document, "benign", "generated", index, category=category)
        for index, category in enumerate(
            ("topic", "entity", "event", "summary", "follow_up"), start=1
        )
    )
    return rows


def _parent_bank(tmp_path: Path) -> tuple[QueryBank, Path]:
    run_id = "source-run"
    documents = [
        {
            "dataset_id": "ag_news",
            "doc_id": f"{prefix}-{index:03d}",
            "membership_label": label,
            "text": f"Source text for {prefix} document {index}.",
        }
        for label, prefix in ((1, "member"), (0, "nonmember"))
        for index in range(50)
    ]
    run_root = tmp_path / "data" / "runs" / run_id
    write_jsonl_atomic(run_root / "target_docs.jsonl", documents)
    write_json_atomic(
        run_root / "run_manifest.json",
        {"dataset_runs": {"ag_news": {"target_docs_path": "target_docs.jsonl"}}},
    )

    paths = QueryBankPaths(tmp_path, "ag_news_queries_v1", "ag_news")
    document_manifest = []
    for document in documents:
        document_manifest.append(
            {
                "dataset_id": "ag_news",
                "doc_id": document["doc_id"],
                "membership_label": document["membership_label"],
                "source_document_sha256": document_sha256(document["text"]),
            }
        )
        write_document_shard(paths, document["doc_id"], _document_records(document))
    digest = compact_query_bank(paths, document_manifest)
    write_json_atomic(
        paths.manifest,
        {
            "bank_id": "ag_news_queries_v1",
            "dataset_id": "ag_news",
            "source_run_id": run_id,
            "status": "complete",
            "queries_sha256": digest,
        },
    )
    bank = QueryBank.load(paths)
    split_path = tmp_path / "parent_split.json"
    freeze_threshold_split(
        build_threshold_split(bank, split_id="ag_news_threshold_v1", seed=17),
        split_path,
    )
    return bank, split_path


def _attack_config(path: Path) -> Path:
    path.write_text(
        """
models:
  generation: {backend: transformers, model: test-model, load_mode: bf16}
  embedding: {backend: sentence_transformers, model: test-embedding}
vector_store: {backend: faiss}
masked_mia: {mask_count: 1}
ia: {questions_per_document: 1}
""".strip(),
        encoding="utf-8",
    )
    return path


def test_standard_generator_uses_one_distinct_question_set_per_category() -> None:
    class FakeClient:
        def __init__(self) -> None:
            self.json_calls = 0

        def generate_json(self, *_args, **_kwargs) -> dict:
            self.json_calls += 1
            return {
                "questions": [
                    "Who is the focal person?",
                    "What did that person do?",
                    "How is that person related to the team?",
                    "Which person is tied to the outcome?",
                ]
            }

    client = FakeClient()
    generator = _default_generator(
        client,
        SimpleNamespace(generation_model="test-model", ia_generation_max_tokens=128),
    )
    slots = [
        BenignSlot("doc-1", "entity", "standard", None, index)
        for index in range(6, 10)
    ]

    questions = [generator("source text", slot, 1) for slot in slots]

    assert client.json_calls == 1
    assert len(set(questions)) == 4


def test_standard_generator_uses_a_batch_position_not_the_global_query_index() -> None:
    class FakeClient:
        def generate_json(self, *_args, **_kwargs) -> dict:
            return {
                "questions": [
                    "Who is the focal person?",
                    "What did that person do?",
                    "How is that person related to the team?",
                    "Which person is tied to the outcome?",
                ]
            }

    generator = _default_generator(
        FakeClient(),
        SimpleNamespace(generation_model="test-model", ia_generation_max_tokens=128),
    )
    slots = [
        BenignSlot("doc-1", "entity", "standard", None, index)
        for index in (9, 10, 11)
    ]

    questions = [generator("source text", slot, 1) for slot in slots]

    assert questions == [
        "Who is the focal person?",
        "What did that person do?",
        "How is that person related to the team?",
    ]


def test_expansion_keeps_parent_benign_floor_when_all_supplements_fail(
    tmp_path: Path,
) -> None:
    _parent, parent_split = _parent_bank(tmp_path)

    result = expand_benign_query_bank(
        project_root=tmp_path,
        bank_id="ag_news_queries_v2",
        dataset_id="ag_news",
        config=BenignExpansionConfig(
            source_run_id="source-run",
            parent_bank_id="ag_news_queries_v1",
            parent_split_path=parent_split,
            attack_config_path=_attack_config(tmp_path / "attack.yaml"),
            seed=20260830,
            max_attempts_per_slot=1,
            audit_seed=91,
        ),
        split_id="ag_news_threshold_v2",
        split_output=tmp_path / "ag_news_threshold_v2.json",
        generator=lambda _text, _slot, _attempt: "Is this in the training data?",
        verifier=lambda _text, _candidate, _slot: {
            "accepted": True,
            "reason_code": "ordinary_information_request",
            "observed_scenario": None,
        },
    )

    bank = QueryBank.load(QueryBankPaths(tmp_path, "ag_news_queries_v2", "ag_news"))
    benign = [row for row in bank.records if row["attack_type"] == "benign"]
    assert result["status"] == "complete"
    assert len(benign) == 500


def test_expansion_deduplicates_parent_benign_before_generating_replacements(
    tmp_path: Path,
) -> None:
    parent, parent_split = _parent_bank(tmp_path)
    paths = QueryBankPaths(tmp_path, "ag_news_queries_v1", "ag_news")
    doc_id = "member-000"
    rows = [dict(row) for row in parent.records if row["doc_id"] == doc_id]
    parent_benign = [row for row in rows if row["attack_type"] == "benign"]
    parent_benign[1]["query_text"] = parent_benign[0]["query_text"]
    write_document_shard(paths, doc_id, rows)
    digest = compact_query_bank(paths, list(parent.documents))
    parent_manifest = json.loads(paths.manifest.read_text(encoding="utf-8"))
    parent_manifest["queries_sha256"] = digest
    write_json_atomic(paths.manifest, parent_manifest)
    parent = QueryBank.load(paths)
    parent_split.unlink()
    freeze_threshold_split(
        build_threshold_split(parent, split_id="ag_news_threshold_v1", seed=17),
        parent_split,
    )

    result = expand_benign_query_bank(
        project_root=tmp_path,
        bank_id="ag_news_queries_v2",
        dataset_id="ag_news",
        config=BenignExpansionConfig(
            source_run_id="source-run",
            parent_bank_id="ag_news_queries_v1",
            parent_split_path=parent_split,
            attack_config_path=_attack_config(tmp_path / "attack.yaml"),
            seed=20260830,
            max_attempts_per_slot=1,
            audit_seed=91,
        ),
        split_id="ag_news_threshold_v2",
        split_output=tmp_path / "ag_news_threshold_v2.json",
        generator=lambda _text, slot, _attempt: (
            f"replacement ordinary question {slot.doc_id} {slot.query_index}"
        ),
        verifier=lambda _text, _candidate, slot: {
            "accepted": True,
            "reason_code": "ordinary_information_request",
            "observed_scenario": slot.hard_scenario,
        },
    )

    bank = QueryBank.load(QueryBankPaths(tmp_path, "ag_news_queries_v2", "ag_news"))
    benign = [
        row for row in bank.records
        if row["doc_id"] == doc_id and row["attack_type"] == "benign"
    ]
    assert result["status"] == "complete"
    assert len(benign) >= 5
    assert len({normalize_query(row["query_text"]) for row in benign}) == len(benign)


def test_expansion_copies_attacks_retries_duplicates_and_writes_audit(
    tmp_path: Path,
) -> None:
    parent, parent_split = _parent_bank(tmp_path)
    generator_calls: list[tuple[str, int, int]] = []

    def generator(_text: str, slot, attempt: int) -> str:
        generator_calls.append((slot.doc_id, slot.query_index, attempt))
        if slot.query_index == 6:
            return f"shared legitimate question for {slot.doc_id}"
        if slot.query_index == 7 and attempt == 1:
            return f"shared legitimate question for {slot.doc_id}"
        return f"legitimate question {slot.doc_id} {slot.query_index} attempt {attempt}"

    def verifier(_text: str, _candidate: str, slot) -> dict:
        return {
            "accepted": slot.query_index != 6,
            "reason_code": (
                "membership" if slot.query_index == 6 else "ordinary_information_request"
            ),
            "observed_scenario": slot.hard_scenario,
        }

    result = expand_benign_query_bank(
        project_root=tmp_path,
        bank_id="ag_news_queries_v2",
        dataset_id="ag_news",
        config=BenignExpansionConfig(
            source_run_id="source-run",
            parent_bank_id="ag_news_queries_v1",
            parent_split_path=parent_split,
            attack_config_path=_attack_config(tmp_path / "attack.yaml"),
            seed=20260830,
            max_attempts_per_slot=2,
            audit_seed=91,
        ),
        split_id="ag_news_threshold_v2",
        split_output=tmp_path / "ag_news_threshold_v2.json",
        generator=generator,
        verifier=verifier,
    )

    v2 = QueryBank.load(QueryBankPaths(tmp_path, "ag_news_queries_v2", "ag_news"))
    parent_attacks = [row for row in parent.records if row["attack_type"] != "benign"]
    v2_attacks = [row for row in v2.records if row["attack_type"] != "benign"]
    assert v2_attacks == parent_attacks
    assert len([row for row in v2.records if row["attack_type"] == "benign"]) == 2200
    assert result["source_attack_records_sha256"] == v2.manifest[
        "source_attack_records_sha256"
    ]
    assert any(query_index == 7 and attempt == 2 for _, query_index, attempt in generator_calls)
    audit_rows = [
        json.loads(line)
        for line in (Path(result["output_path"]) / "benign_audit_sample.jsonl").read_text(
            encoding="utf-8"
        ).splitlines()
    ]
    assert audit_rows
    assert {row["review_status"] for row in audit_rows} == {"pending"}


def test_expansion_archives_an_incomplete_build_before_a_clean_restart(
    tmp_path: Path,
) -> None:
    _parent, parent_split = _parent_bank(tmp_path)
    config = BenignExpansionConfig(
        source_run_id="source-run",
        parent_bank_id="ag_news_queries_v1",
        parent_split_path=parent_split,
        attack_config_path=_attack_config(tmp_path / "attack.yaml"),
        seed=20260830,
        minimum_benign_per_document=6,
        max_attempts_per_slot=1,
        audit_seed=91,
    )

    def generator(_text: str, slot, _attempt: int) -> str:
        if slot.doc_id == "member-001":
            return "Is this in the training data?"
        return f"legitimate question {slot.doc_id} {slot.query_index}"

    def verifier(_text: str, _candidate: str, slot) -> dict:
        return {
            "accepted": True,
            "reason_code": "ordinary_information_request",
            "observed_scenario": slot.hard_scenario,
        }

    arguments = {
        "project_root": tmp_path,
        "bank_id": "ag_news_queries_v2",
        "dataset_id": "ag_news",
        "config": config,
        "split_id": "ag_news_threshold_v2",
        "split_output": tmp_path / "ag_news_threshold_v2.json",
        "verifier": verifier,
    }
    with pytest.raises(RuntimeError, match="below the required floor"):
        expand_benign_query_bank(**arguments, generator=generator)

    destination = QueryBankPaths(tmp_path, "ag_news_queries_v2", "ag_news")
    first_shard = destination.shard("member-000")
    first_shard_bytes = first_shard.read_bytes()

    result = expand_benign_query_bank(
        **arguments,
        generator=lambda _text, slot, _attempt: (
            f"replacement question {slot.doc_id} {slot.query_index}"
        ),
    )

    assert result["status"] == "complete"
    archived_shard = (
        destination.root.with_name("ag_news.incomplete_attempt_1")
        / ".work"
        / first_shard.name
    )
    assert archived_shard.read_bytes() == first_shard_bytes
    assert first_shard.read_bytes() != first_shard_bytes
