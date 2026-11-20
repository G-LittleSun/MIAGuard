from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

import pytest

from miaguard.query_bank.builder import build_document_records
from miaguard.query_bank.repair import repair_ia_query_bank
from miaguard.query_bank.schema import QueryBankBuildConfig, document_sha256
from miaguard.query_bank.storage import QueryBankPaths, compact_query_bank, write_document_shard
from rag_mia_data.io_utils import read_jsonl, write_json_atomic, write_jsonl_atomic


class _RepairClient:
    def __init__(self, start_index: int = 0) -> None:
        self.index = start_index
        self.config = SimpleNamespace(generation_backend="transformers")

    def generate_json(self, model, prompt, **kwargs):
        if "IA_ANCHOR_COUNTERFACTUAL" in prompt:
            self.index += 1
            return {
                "questions": [
                    f"Does counterfactual repair fact {self.index} hold?"
                ]
            }
        if "IA_NO_FACTS" in prompt:
            return {
                "facts": [
                    {
                        "subject": "Alpha Corp",
                        "attribute": "acquisition target",
                        "value": "Beta Labs",
                    }
                ]
            }
        if "IA_NO_CONTRADICTIONS" in prompt:
            prompt = prompt.replace("[IA_NO_CONTRADICTIONS]", "[IA_CANDIDATES]")
        if "Select exactly one contextually difficult-to-predict word" in prompt:
            return {"words": ["Alpha"]}
        if "PARAPHRASE" in prompt:
            return {"queries": [f"Equivalent query {index}" for index in range(1, 5)]}
        if "IA_CANDIDATES" in prompt:
            target = "yes" if "answer must be yes" in prompt else "no"
            count = int(re.search(r"generate exactly (\d+) new", prompt).group(1))
            questions = []
            for _ in range(count):
                self.index += 1
                questions.append(f"Does {target} repair fact {self.index} hold?")
            return {"summary": "alpha repair", "questions": questions}
        if "IA_VERIFY" in prompt:
            answer = "yes" if "yes repair fact" in prompt else "no"
            questions = re.findall(r"^\d+\. (.+)$", prompt, flags=re.MULTILINE)
            return {"answers": [answer] * len(questions)}
        if "BENIGN_QUERIES" in prompt:
            return {
                "topic": "What is the topic?",
                "entity": "Which entity is named?",
                "event": "What event occurred?",
                "summary": "What is the summary?",
                "follow_up": "What can be researched next?",
            }
        raise AssertionError(prompt[:120])

    def generate(self, model, prompt, **kwargs):
        if "IA_VERIFY_PLAIN" in prompt:
            return "yes"
        for marker in ("DIRECT_PARAPHRASE", "S2_PARAPHRASE", "MASKED_PARAPHRASE"):
            if marker in prompt:
                return json.dumps(
                    {"queries": [f"{marker} query {index}" for index in range(1, 5)]}
                )
        raise AssertionError(prompt[:120])

    def embed(self, model, texts):
        raise AssertionError("repair must not embed")


class _WrongLabelRepairClient(_RepairClient):
    def generate_json(self, model, prompt, **kwargs):
        if "IA_VERIFY" in prompt:
            questions = re.findall(r"^\d+\. (.+)$", prompt, flags=re.MULTILINE)
            return {"answers": ["no"] * len(questions)}
        return super().generate_json(model, prompt, **kwargs)


class _OneThenWrongLabelRepairClient(_RepairClient):
    def __init__(self) -> None:
        super().__init__()
        self.yes_verification_batches = 0

    def generate_json(self, model, prompt, **kwargs):
        if "IA_VERIFY" in prompt and "yes repair fact" in prompt:
            self.yes_verification_batches += 1
            questions = re.findall(r"^\d+\. (.+)$", prompt, flags=re.MULTILINE)
            if self.yes_verification_batches == 1:
                return {"answers": ["yes", *(["no"] * (len(questions) - 1))]}
            return {"answers": ["no"] * len(questions)}
        return super().generate_json(model, prompt, **kwargs)


class _RejectingAnchorRepairClient(_RepairClient):
    def __init__(self, rejected_anchor_count: int) -> None:
        super().__init__()
        self.rejected_anchor_count = rejected_anchor_count
        self.anchor_attempts = 0
        self.rejected_verifications_remaining = 0

    def generate_json(self, model, prompt, **kwargs):
        if "IA_ANCHOR_COUNTERFACTUAL" in prompt:
            self.anchor_attempts += 1
            if self.anchor_attempts <= self.rejected_anchor_count:
                self.rejected_verifications_remaining = 2
                return {
                    "questions": [
                        f"Did rejected counterfactual {self.anchor_attempts} occur?"
                    ]
                }
        if "IA_VERIFY" in prompt and self.rejected_verifications_remaining:
            self.rejected_verifications_remaining -= 1
            questions = re.findall(r"^\d+\. (.+)$", prompt, flags=re.MULTILINE)
            return {"answers": ["yes"] * len(questions)}
        return super().generate_json(model, prompt, **kwargs)


def _attack_config(path: Path) -> Path:
    path.write_text(
        """
seed: 17
models:
  generation: {backend: transformers, model: local-model, load_mode: int8}
  embedding: {backend: sentence_transformers, model: local-embedding}
vector_store: {embedding_batch_size: 1, top_k: 1}
masked_mia: {mask_count: 1, max_tokens: 32}
ia: {questions_per_document: 1, generation_max_tokens: 128}
direct_rag_mia: {max_tokens: 12}
s2_mia: {max_tokens: 32, prefix_words: 2}
""".strip(),
        encoding="utf-8",
    )
    return path


def _build_deficient_bank(tmp_path: Path) -> tuple[QueryBankPaths, Path]:
    config_path = _attack_config(tmp_path / "attack.yaml")
    build_config = QueryBankBuildConfig(
        source_run_id="run-1",
        attack_config_path=config_path,
        seed=17,
        member_count=1,
        nonmember_count=1,
        paraphrases_per_attack=4,
        ia_questions_per_document=30,
        ia_batch_size=6,
        ia_max_attempts=10,
        benign_categories=("topic", "entity", "event", "summary", "follow_up"),
    )
    attack_config = SimpleNamespace(
        generation_backend="transformers",
        generation_model="local-model",
        embedding_model="local-embedding",
        s2_mia_prefix_words=2,
        mask_count=1,
        masked_max_tokens=32,
        ia_generation_max_tokens=128,
    )
    document = {
        "doc_id": "doc-1",
        "membership_label": 1,
        "text": "Alpha Corp acquired Beta Labs in Paris.",
    }
    rows = build_document_records(
        dataset_id="ag_news",
        document=document,
        build_config=build_config,
        attack_config=attack_config,
        client=_RepairClient(start_index=100),
    )
    yes_rows = [
        row for row in rows
        if row["attack_type"] == "ia" and row["payload"]["ground_truth"] == "yes"
    ]
    for row in yes_rows[:10]:
        row["payload"]["ground_truth"] = "unknown"
    no_rows = [
        row for row in rows
        if row["attack_type"] == "ia" and row["payload"]["ground_truth"] == "no"
    ]
    for row in no_rows[:10]:
        row["payload"]["ground_truth"] = "unknown"

    paths = QueryBankPaths(tmp_path, "bank-1", "ag_news")
    document_manifest = {
        "dataset_id": "ag_news",
        "doc_id": "doc-1",
        "membership_label": 1,
        "source_document_sha256": document_sha256(document["text"]),
    }
    write_document_shard(paths, "doc-1", rows)
    digest = compact_query_bank(paths, [document_manifest])
    write_json_atomic(
        paths.manifest,
        {
            "bank_id": "bank-1",
            "dataset_id": "ag_news",
            "status": "complete",
            "source_run_id": "run-1",
            "seed": 17,
            "generation_model": "local-model",
            "embedding_model": "local-embedding",
            "queries_sha256": digest,
        },
    )
    run_root = tmp_path / "data" / "runs" / "run-1"
    write_jsonl_atomic(run_root / "ag_news" / "target_docs.jsonl", [document])
    write_json_atomic(
        run_root / "run_manifest.json",
        {"dataset_runs": {"ag_news": {"target_docs_path": "ag_news/target_docs.jsonl"}}},
    )
    return paths, config_path


def test_repair_appends_only_missing_ia_label_and_records_audit(tmp_path: Path) -> None:
    paths, config_path = _build_deficient_bank(tmp_path)
    before = {row["query_id"]: row for row in read_jsonl(paths.queries)}

    result = repair_ia_query_bank(
        tmp_path,
        "bank-1",
        "ag_news",
        config_path,
        seed=17,
        client=_RepairClient(),
    )

    after = list(read_jsonl(paths.queries))
    assert result["repaired_document_count"] == 1
    assert result["added_query_count"] == 10
    assert {row["query_id"]: row for row in after if row["query_id"] in before} == before
    assert Counter(
        row["payload"]["ground_truth"]
        for row in after
        if row["doc_id"] == "doc-1" and row["attack_type"] == "ia"
    ) == {"yes": 10, "no": 10, "unknown": 20}
    new_no_rows = [
        row for row in after
        if row["query_id"] not in before
        and row["attack_type"] == "ia"
        and row["payload"]["ground_truth"] == "no"
    ]
    assert {row["payload"]["construction"] for row in new_no_rows} == {
        "counterfactual"
    }
    audit = [json.loads(line) for line in paths.repair_log.read_text(encoding="utf-8").splitlines()]
    assert len(audit) == 1
    assert audit[0]["old_ia_answer_counts"] == {"no": 5, "unknown": 20, "yes": 5}
    assert audit[0]["new_ia_answer_counts"] == {"no": 10, "unknown": 20, "yes": 10}
    assert len(audit[0]["added_query_ids"]) == 10


def test_repair_fills_no_gap_after_some_anchors_are_rejected(
    tmp_path: Path,
) -> None:
    paths, config_path = _build_deficient_bank(tmp_path)

    result = repair_ia_query_bank(
        tmp_path,
        "bank-1",
        "ag_news",
        config_path,
        seed=17,
        client=_RejectingAnchorRepairClient(rejected_anchor_count=6),
    )

    counts = Counter(
        row["payload"]["ground_truth"]
        for row in read_jsonl(paths.queries)
        if row["doc_id"] == "doc-1" and row["attack_type"] == "ia"
    )
    assert result["status"] == "complete"
    assert counts == {"yes": 10, "no": 10, "unknown": 20}


def test_repair_uses_verified_fact_negations_when_all_anchors_are_rejected(
    tmp_path: Path,
) -> None:
    paths, config_path = _build_deficient_bank(tmp_path)
    before_ids = {row["query_id"] for row in read_jsonl(paths.queries)}

    result = repair_ia_query_bank(
        tmp_path,
        "bank-1",
        "ag_news",
        config_path,
        seed=17,
        client=_RejectingAnchorRepairClient(rejected_anchor_count=1000),
    )

    new_no_rows = [
        row
        for row in read_jsonl(paths.queries)
        if row["query_id"] not in before_ids
        and row["attack_type"] == "ia"
        and row["payload"]["ground_truth"] == "no"
    ]
    assert result["status"] == "complete"
    assert len(new_no_rows) == 5
    assert {row["payload"]["construction"] for row in new_no_rows} == {
        "verified_fact_negation"
    }


def test_repair_failure_leaves_query_bank_files_unchanged(tmp_path: Path) -> None:
    paths, config_path = _build_deficient_bank(tmp_path)
    queries_before = paths.queries.read_bytes()
    manifest_before = paths.manifest.read_bytes()

    with pytest.raises(RuntimeError, match="required_answer=yes"):
        repair_ia_query_bank(
            tmp_path,
            "bank-1",
            "ag_news",
            config_path,
            seed=17,
            client=_WrongLabelRepairClient(start_index=1000),
        )

    assert paths.queries.read_bytes() == queries_before
    assert paths.manifest.read_bytes() == manifest_before
    assert not paths.repair_log.exists()
    progress = list(read_jsonl(paths.repair_progress))
    assert progress[-1]["last_failure"]["doc_id"] == "doc-1"
    assert progress[-1]["last_failure"]["answer"] == "yes"

    result = repair_ia_query_bank(
        tmp_path,
        "bank-1",
        "ag_news",
        config_path,
        seed=17,
        client=_RepairClient(start_index=2000),
    )

    assert result["status"] == "complete"
    assert not paths.repair_progress.exists()


def test_repair_checkpoints_each_verified_yes_before_later_failure(
    tmp_path: Path,
) -> None:
    paths, config_path = _build_deficient_bank(tmp_path)
    queries_before = paths.queries.read_bytes()

    with pytest.raises(RuntimeError, match="required_answer=yes"):
        repair_ia_query_bank(
            tmp_path,
            "bank-1",
            "ag_news",
            config_path,
            seed=17,
            client=_OneThenWrongLabelRepairClient(),
        )

    progress = list(read_jsonl(paths.repair_progress))[-1]
    added_rows = progress["pending_document"]["added_rows"]
    assert paths.queries.read_bytes() == queries_before
    assert Counter(
        row["payload"]["ground_truth"] for row in added_rows
    ) == {"yes": 1}

    result = repair_ia_query_bank(
        tmp_path,
        "bank-1",
        "ag_news",
        config_path,
        seed=17,
        client=_RepairClient(start_index=4000),
    )

    assert result["status"] == "complete"
    assert not paths.repair_progress.exists()


def test_repair_archives_incompatible_progress_before_starting(tmp_path: Path) -> None:
    paths, config_path = _build_deficient_bank(tmp_path)
    write_jsonl_atomic(
        paths.repair_progress,
        [
            {
                "bank_id": "bank-1",
                "dataset_id": "ag_news",
                "completed_documents": {},
                "pending_document": None,
            }
        ],
    )

    result = repair_ia_query_bank(
        tmp_path,
        "bank-1",
        "ag_news",
        config_path,
        seed=17,
        client=_RepairClient(start_index=3000),
    )

    archives = list((paths.work / "repair-progress-archive").glob("*.jsonl"))
    assert result["status"] == "complete"
    assert len(archives) == 1
    assert list(read_jsonl(archives[0]))[0]["bank_id"] == "bank-1"
