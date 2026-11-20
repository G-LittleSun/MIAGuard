# Versioned Offline Query Bank Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a versioned, document-bound offline Query Bank so frozen experiments sample reproducible benign and attack queries without invoking online query generation.

**Architecture:** Add a focused `miaguard.query_bank` package for schema/configuration, staging storage, validation, sampling, and offline generation. Construction writes one atomic shard per document, validates the complete bank, and compacts it into stable JSONL files. Existing attack and two-stage experiment entry points consume a frozen selection manifest and continue to call the model only for target RAG answers and defense scoring.

**Tech Stack:** Python 3.10, dataclasses, pathlib, hashlib, JSON/JSONL, PyYAML, NumPy, existing `ModelClient`, pytest.

**Design reference:** `docs/superpowers/specs/2026-07-24-versioned-query-bank-design.md`

**Repository note:** `D:\Project\MIAGuard` is not currently a Git worktree. Every task contains a version-control checkpoint. Run the commit command only if `git rev-parse --is-inside-work-tree` succeeds; otherwise retain the tested filesystem changes and record the checkpoint in the task log.

---

## File map

### New production files

- `src/miaguard/query_bank/__init__.py`: public Query Bank API.
- `src/miaguard/query_bank/schema.py`: configuration dataclasses, record enums, stable IDs, document hashes, and record validation.
- `src/miaguard/query_bank/storage.py`: paths, lock lifecycle, per-document shards, final compaction, and frozen bank loading.
- `src/miaguard/query_bank/validator.py`: per-record and whole-bank invariants, duplicate detection, IA balance, and reports.
- `src/miaguard/query_bank/sampler.py`: deterministic stratified document/query sampling and selection manifests.
- `src/miaguard/query_bank/builder.py`: attack-specific offline generation and incremental build orchestration.
- `scripts/query_bank/build_query_bank.py`: build/resume CLI.
- `scripts/query_bank/validate_query_bank.py`: independent validation CLI.
- `scripts/query_bank/inspect_query_bank.py`: human-readable statistics CLI.
- `configs/query_banks/ag_news_v1.yaml`: first Query Bank build profile.
- `configs/query_banks/ag_news_smoke.yaml`: two-document end-to-end verification profile.
- `tests/test_query_bank_schema.py`
- `tests/test_query_bank_storage.py`
- `tests/test_query_bank_validator.py`
- `tests/test_query_bank_sampler.py`
- `tests/test_query_bank_builder.py`
- `tests/test_query_bank_cli.py`
- `tests/test_query_bank_attack_integration.py`

### Existing files to modify

- `src/miaguard/cli.py`: accept frozen Query Bank arguments for four base attacks.
- `src/miaguard/direct_rag_mia.py`: consume preselected Direct queries.
- `src/miaguard/s2_mia.py`: consume preselected S² queries.
- `src/miaguard/masked_mia.py`: consume frozen masks and answers.
- `src/miaguard/ia_attack.py`: consume frozen IA sessions and ground truth.
- `src/miaguard/defense_experiment.py`: replay frozen benign queries.
- `src/miaguard/two_stage_attack_comparison.py`: replace baseline-row/IA-expansion preparation with Query Bank sampling.
- `scripts/run_two_stage_attack_comparison.py`: expose Query Bank ID, seed, and variant mode.
- `scripts/run_full_10x10.ps1`: pass the frozen Query Bank arguments.
- `tests/test_cli.py`
- `tests/test_two_stage_attack_comparison.py`
- `docs/USAGE_GUIDE_ZH.md`: document build, validate, inspect, and frozen experiment commands.

## Task 1: Query Bank schema and build configuration

**Files:**
- Create: `src/miaguard/query_bank/__init__.py`
- Create: `src/miaguard/query_bank/schema.py`
- Create: `tests/test_query_bank_schema.py`

- [ ] **Step 1: Write failing schema tests**

Create `tests/test_query_bank_schema.py`:

```python
from pathlib import Path

import pytest

from miaguard.query_bank.schema import (
    QueryBankBuildConfig,
    document_sha256,
    load_query_bank_config,
    make_query_id,
    validate_query_record,
)


def _ia_record() -> dict:
    return {
        "query_id": "ag_news:doc-1:ia:generated:0001",
        "dataset_id": "ag_news",
        "doc_id": "doc-1",
        "membership_label": 1,
        "source_document_sha256": document_sha256("source text"),
        "traffic_type": "attack",
        "attack_type": "ia",
        "variant_type": "generated",
        "query_index": 1,
        "query_text": "Regarding the event, did it happen? Answer yes or no.",
        "payload": {
            "question": "Did the event happen?",
            "ground_truth": "yes",
            "summary": "target event",
        },
        "generation": {
            "backend": "transformers",
            "model": "local-model",
            "prompt_version": "ia-query-v1",
            "temperature": 0.2,
            "seed": 7,
        },
        "validation": {
            "status": "accepted",
            "answer_verified": True,
            "duplicate_checked": True,
        },
        "created_at": "2026-07-24T00:00:00+00:00",
    }


def test_stable_query_id_and_document_hash() -> None:
    first = make_query_id("ag_news", "doc-1", "ia", "generated", 1)
    second = make_query_id("ag_news", "doc-1", "ia", "generated", 1)
    assert first == second == "ag_news:doc-1:ia:generated:0001"
    assert document_sha256("a\r\nb") == document_sha256("a\nb")


def test_validate_query_record_accepts_valid_ia() -> None:
    validate_query_record(_ia_record())


def test_validate_query_record_rejects_wrong_ia_answer() -> None:
    record = _ia_record()
    record["payload"]["ground_truth"] = "unknown"
    with pytest.raises(ValueError, match="ground_truth"):
        validate_query_record(record)


def test_load_query_bank_config_requires_exact_ia_balance(tmp_path: Path) -> None:
    path = tmp_path / "bank.yaml"
    path.write_text(
        """
source_run_id: run-1
attack_config: configs/attacks/ag_news_calibrated_int8.yaml
seed: 7
pool:
  members: 20
  nonmembers: 20
queries:
  paraphrases_per_attack: 4
  ia_yes: 15
  ia_no: 15
  ia_batch_size: 6
  ia_max_attempts: 20
  semantic_duplicate_threshold: 0.92
  benign_categories: [topic, entity, event, summary, follow_up]
""".strip(),
        encoding="utf-8",
    )
    config = load_query_bank_config(path)
    assert isinstance(config, QueryBankBuildConfig)
    assert config.ia_total == 30
    assert config.benign_categories == (
        "topic",
        "entity",
        "event",
        "summary",
        "follow_up",
    )
```

- [ ] **Step 2: Run schema tests and verify failure**

Run:

```powershell
python -m pytest -q tests/test_query_bank_schema.py
```

Expected: collection fails with `ModuleNotFoundError: No module named 'miaguard.query_bank'`.

- [ ] **Step 3: Implement schema/configuration API**

Create `src/miaguard/query_bank/schema.py` with:

```python
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

ATTACK_TYPES = ("direct_rag_mia", "s2_mia", "masked_mia", "ia", "benign")
VARIANT_TYPES = ("canonical", "paraphrase", "generated")
BENIGN_CATEGORIES = ("topic", "entity", "event", "summary", "follow_up")


@dataclass(frozen=True)
class QueryBankBuildConfig:
    source_run_id: str
    attack_config_path: Path
    seed: int
    member_count: int
    nonmember_count: int
    paraphrases_per_attack: int
    ia_yes: int
    ia_no: int
    ia_batch_size: int
    ia_max_attempts: int
    semantic_duplicate_threshold: float
    benign_categories: tuple[str, ...]

    @property
    def ia_total(self) -> int:
        return self.ia_yes + self.ia_no


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
    attack = str(record["attack_type"])
    variant = str(record["variant_type"])
    if attack not in ATTACK_TYPES:
        raise ValueError(f"Unsupported attack_type: {attack}")
    if variant not in VARIANT_TYPES:
        raise ValueError(f"Unsupported variant_type: {variant}")
    if int(record["membership_label"]) not in {0, 1}:
        raise ValueError("membership_label must be 0 or 1")
    expected_traffic = "benign" if attack == "benign" else "attack"
    if record["traffic_type"] != expected_traffic:
        raise ValueError("traffic_type does not match attack_type")
    payload = _mapping(record["payload"], "payload")
    _mapping(record["generation"], "generation")
    validation = _mapping(record["validation"], "validation")
    if not str(record["query_text"]).strip():
        raise ValueError("query_text must not be blank")
    if validation.get("status") != "accepted":
        raise ValueError("Only accepted records belong in queries.jsonl")
    if attack == "ia":
        if payload.get("ground_truth") not in {"yes", "no"}:
            raise ValueError("IA ground_truth must be yes or no")
        for field in ("question", "summary"):
            if not str(payload.get(field, "")).strip():
                raise ValueError(f"IA payload field is blank: {field}")
    if attack == "masked_mia":
        answers = payload.get("answers")
        if not isinstance(answers, list) or not answers:
            raise ValueError("Masked payload answers must be a non-empty list")
        if not str(payload.get("masked_text", "")).strip():
            raise ValueError("Masked payload masked_text must not be blank")
    if attack == "s2_mia" and not str(payload.get("prefix", "")).strip():
        raise ValueError("S2 payload prefix must not be blank")
    if attack == "benign" and payload.get("category") not in BENIGN_CATEGORIES:
        raise ValueError("Unknown benign category")
    expected_id = make_query_id(
        str(record["dataset_id"]),
        str(record["doc_id"]),
        attack,
        variant,
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
        ia_yes=int(queries.get("ia_yes", 15)),
        ia_no=int(queries.get("ia_no", 15)),
        ia_batch_size=int(queries.get("ia_batch_size", 6)),
        ia_max_attempts=int(queries.get("ia_max_attempts", 20)),
        semantic_duplicate_threshold=float(
            queries.get("semantic_duplicate_threshold", 0.92)
        ),
        benign_categories=tuple(
            str(item) for item in queries.get("benign_categories", BENIGN_CATEGORIES)
        ),
    )
    positive = (
        config.member_count,
        config.nonmember_count,
        config.paraphrases_per_attack,
        config.ia_yes,
        config.ia_no,
        config.ia_batch_size,
        config.ia_max_attempts,
    )
    if any(value <= 0 for value in positive):
        raise ValueError("Query Bank counts must be positive")
    if config.ia_yes != 15 or config.ia_no != 15:
        raise ValueError("IA Query Bank requires exactly 15 yes and 15 no")
    if config.paraphrases_per_attack != 4:
        raise ValueError("Each single-turn attack requires four paraphrases")
    if config.benign_categories != BENIGN_CATEGORIES:
        raise ValueError("benign_categories must match the five approved categories")
    if not 0.0 < config.semantic_duplicate_threshold < 1.0:
        raise ValueError("semantic_duplicate_threshold must be between 0 and 1")
    return config
```

Create `src/miaguard/query_bank/__init__.py`:

```python
from .schema import (
    QueryBankBuildConfig,
    document_sha256,
    load_query_bank_config,
    make_query_id,
    validate_query_record,
)

__all__ = [
    "QueryBankBuildConfig",
    "document_sha256",
    "load_query_bank_config",
    "make_query_id",
    "validate_query_record",
]
```

- [ ] **Step 4: Run schema tests**

Run:

```powershell
python -m pytest -q tests/test_query_bank_schema.py
```

Expected: `4 passed`.

- [ ] **Step 5: Version-control checkpoint**

Run:

```powershell
git rev-parse --is-inside-work-tree
```

If it succeeds:

```powershell
git add src/miaguard/query_bank/__init__.py src/miaguard/query_bank/schema.py tests/test_query_bank_schema.py
git commit -m "feat: add query bank schema"
```

If it fails with `not a git repository`, do not initialize Git implicitly; continue with the tested files in place.

## Task 2: Atomic staging storage and frozen loading

**Files:**
- Create: `src/miaguard/query_bank/storage.py`
- Create: `tests/test_query_bank_storage.py`
- Modify: `src/miaguard/query_bank/__init__.py`

- [ ] **Step 1: Write failing storage tests**

Create tests that prove shard resume, locking, stable compaction, and complete-only loading:

```python
from pathlib import Path

import pytest

from miaguard.query_bank.storage import (
    QueryBank,
    QueryBankLock,
    QueryBankPaths,
    compact_query_bank,
    write_document_shard,
)
from rag_mia_data.io_utils import write_json_atomic


def _record(doc_id: str, index: int) -> dict:
    return {
        "query_id": f"ag_news:{doc_id}:direct_rag_mia:canonical:{index:04d}",
        "dataset_id": "ag_news",
        "doc_id": doc_id,
        "membership_label": 1,
        "source_document_sha256": "a" * 64,
        "traffic_type": "attack",
        "attack_type": "direct_rag_mia",
        "variant_type": "canonical",
        "query_index": index,
        "query_text": "Does the quotation appear? Answer yes or no.",
        "payload": {"target_text": "quotation"},
        "generation": {
            "backend": "deterministic",
            "model": "none",
            "prompt_version": "direct-canonical-v1",
            "temperature": 0.0,
            "seed": 7,
        },
        "validation": {
            "status": "accepted",
            "answer_verified": True,
            "duplicate_checked": True,
        },
        "created_at": "2026-07-24T00:00:00+00:00",
    }


def test_lock_rejects_second_writer(tmp_path: Path) -> None:
    paths = QueryBankPaths(tmp_path, "bank-1", "ag_news")
    with QueryBankLock(paths):
        with pytest.raises(FileExistsError, match="locked"):
            QueryBankLock(paths).acquire()


def test_compaction_is_stable_and_frozen_loader_requires_complete(tmp_path: Path) -> None:
    paths = QueryBankPaths(tmp_path, "bank-1", "ag_news")
    write_document_shard(paths, "doc-b", [_record("doc-b", 1)])
    write_document_shard(paths, "doc-a", [_record("doc-a", 1)])
    documents = [
        {
            "dataset_id": "ag_news",
            "doc_id": "doc-a",
            "membership_label": 1,
            "source_document_sha256": "a" * 64,
        },
        {
            "dataset_id": "ag_news",
            "doc_id": "doc-b",
            "membership_label": 1,
            "source_document_sha256": "a" * 64,
        },
    ]
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
    assert [row["doc_id"] for row in bank.records] == ["doc-a", "doc-b"]
    assert bank.sha256 == digest

    write_json_atomic(
        paths.manifest,
        {
            "bank_id": "bank-1",
            "dataset_id": "ag_news",
            "status": "incomplete",
            "queries_sha256": digest,
        },
    )
    with pytest.raises(ValueError, match="complete"):
        QueryBank.load(paths)
```

- [ ] **Step 2: Run storage tests and verify failure**

Run:

```powershell
python -m pytest -q tests/test_query_bank_storage.py
```

Expected: import failure for `miaguard.query_bank.storage`.

- [ ] **Step 3: Implement storage**

Implement the following public API in `storage.py`:

```python
@dataclass(frozen=True)
class QueryBankPaths:
    project_root: Path
    bank_id: str
    dataset_id: str

    @property
    def root(self) -> Path:
        return self.project_root / "data" / "query_banks" / self.bank_id / self.dataset_id

    @property
    def work(self) -> Path:
        return self.root / ".work"

    @property
    def manifest(self) -> Path:
        return self.root / "manifest.json"

    @property
    def documents(self) -> Path:
        return self.root / "documents.jsonl"

    @property
    def queries(self) -> Path:
        return self.root / "queries.jsonl"

    @property
    def failures(self) -> Path:
        return self.root / "generation_failures.jsonl"

    @property
    def lock(self) -> Path:
        return self.root / ".build.lock"

    def shard(self, doc_id: str) -> Path:
        safe = hashlib.sha256(doc_id.encode("utf-8")).hexdigest()
        return self.work / f"{safe}.jsonl"
```

`QueryBankLock.acquire()` must create `.build.lock` with mode `"x"`, write PID and UTC time, and raise `FileExistsError(f"Query Bank is locked: {paths.lock}")` if present. `release()` unlinks only that exact lock path. Support context-manager methods. Add `QueryBankLock.force_remove(paths)` to remove only `paths.lock`; call it only when the CLI receives `--force-unlock`.

`write_document_shard()` must call `validate_query_record()` on every row, require one `doc_id`, then use `write_jsonl_atomic()`.

`compact_query_bank()` must:

1. read every `.work/*.jsonl`;
2. validate every record;
3. sort by `(dataset_id, doc_id, attack_type, variant_type, query_index)`;
4. reject duplicate `query_id`;
5. atomically write `documents.jsonl` and `queries.jsonl`;
6. return `sha256_file(paths.queries)`.

`QueryBank.load()` must:

1. read `manifest.json`;
2. require `status == "complete"`;
3. verify `sha256_file(queries.jsonl) == manifest["queries_sha256"]`;
4. validate every record;
5. expose immutable tuples `records` and `documents`, plus `bank_id`, `dataset_id`, and `sha256`.

- [ ] **Step 4: Run storage tests**

Run:

```powershell
python -m pytest -q tests/test_query_bank_storage.py tests/test_query_bank_schema.py
```

Expected: all tests pass.

- [ ] **Step 5: Export storage API and checkpoint**

Export `QueryBank`, `QueryBankPaths`, and `QueryBankLock` from `__init__.py`, rerun the two test files, then conditionally commit:

```powershell
git add src/miaguard/query_bank tests/test_query_bank_storage.py
git commit -m "feat: add atomic query bank storage"
```

## Task 3: Whole-bank validation and duplicate control

**Files:**
- Create: `src/miaguard/query_bank/validator.py`
- Create: `tests/test_query_bank_validator.py`

- [ ] **Step 1: Write failing validator tests**

Tests must construct complete per-document records and assert:

```python
report = validate_document_records(records, expected_document)
assert report["query_count"] == 50
assert report["counts"] == {
    "direct_rag_mia": 5,
    "s2_mia": 5,
    "masked_mia": 5,
    "ia": 30,
    "benign": 5,
}
assert report["ia_answers"] == {"yes": 15, "no": 15}
```

Add explicit failing cases for:

- source document hash mismatch;
- duplicate normalized IA question;
- missing benign category;
- Direct/S²/Masked not having exactly one canonical and four paraphrases.

Add a fake embedding client:

```python
class _EmbeddingClient:
    def embed(self, model, texts):
        table = {
            "first question": [1.0, 0.0],
            "same meaning": [0.99, 0.01],
            "different": [0.0, 1.0],
        }
        return [table[text] for text in texts]
```

Assert `is_semantic_duplicate("same meaning", ["first question"], client, "embed", 0.92)` is true and `"different"` is false.

- [ ] **Step 2: Run validator tests and verify failure**

Run:

```powershell
python -m pytest -q tests/test_query_bank_validator.py
```

Expected: import failure for `miaguard.query_bank.validator`.

- [ ] **Step 3: Implement validator**

Implement:

```python
EXPECTED_COUNTS = {
    "direct_rag_mia": 5,
    "s2_mia": 5,
    "masked_mia": 5,
    "ia": 30,
    "benign": 5,
}


def normalize_query(value: str) -> str:
    return " ".join(
        re.sub(r"[^\w\s]", " ", value.casefold(), flags=re.UNICODE).split()
    )


def is_semantic_duplicate(
    candidate: str,
    accepted: list[str],
    client: Any,
    embedding_model: str,
    threshold: float,
) -> bool:
    if not accepted:
        return False
    vectors = np.asarray(
        client.embed(embedding_model, [candidate, *accepted]),
        dtype="float32",
    )
    norms = np.linalg.norm(vectors, axis=1)
    if np.any(norms == 0):
        raise ValueError("Duplicate detection received a zero embedding")
    similarities = vectors[1:] @ vectors[0] / (norms[1:] * norms[0])
    return bool(np.any(similarities >= threshold))
```

`validate_document_records(records, expected_document)` must validate all records, require one document identity/hash/label, enforce `EXPECTED_COUNTS`, enforce the single-turn variant mix, enforce exact IA 15/15, enforce five unique benign categories, and reject duplicate normalized IA questions.

`validate_complete_bank(bank, current_documents)` must:

- index current documents by `doc_id`;
- recalculate each document hash;
- reject missing or changed documents;
- group records by `doc_id`;
- call `validate_document_records()` for every document;
- return aggregate counts and per-document reports.

- [ ] **Step 4: Run validator tests**

Run:

```powershell
python -m pytest -q tests/test_query_bank_validator.py tests/test_query_bank_storage.py
```

Expected: all tests pass.

- [ ] **Step 5: Checkpoint**

Conditionally commit:

```powershell
git add src/miaguard/query_bank/validator.py tests/test_query_bank_validator.py
git commit -m "feat: validate query bank quality"
```

## Task 4: Deterministic stratified sampler

**Files:**
- Create: `src/miaguard/query_bank/sampler.py`
- Create: `tests/test_query_bank_sampler.py`

- [ ] **Step 1: Write failing sampler tests**

Build an in-memory fake bank with six member and six nonmember documents, complete records for all five types, then assert:

```python
first = sample_query_bank(
    bank,
    members_per_attack=2,
    nonmembers_per_attack=2,
    benign_count=4,
    ia_turn_count=3,
    seed=17,
    variant_mode="canonical",
    canonical_fraction=1.0,
)
second = sample_query_bank(
    bank,
    members_per_attack=2,
    nonmembers_per_attack=2,
    benign_count=4,
    ia_turn_count=3,
    seed=17,
    variant_mode="canonical",
    canonical_fraction=1.0,
)
assert first == second
assert first["online_query_generation"] is False
assert len(first["attacks"]["ia"]) == 4
assert all(len(row["queries"]) == 3 for row in first["attacks"]["ia"])
assert first["selected_doc_ids"]["direct_rag_mia"] == first["selected_doc_ids"]["ia"]
```

Also assert:

- a different seed changes at least one query ID;
- IA three-turn selection has a 2/1 or 1/2 yes/no split;
- `variant_mode="paraphrase"` never selects canonical records;
- `variant_mode="mixed"` with `canonical_fraction=0.25` records the ratio and selects both variant families when the cohort is large enough;
- insufficient members raises `ValueError("not enough member documents")`;
- the selection manifest contains `query_bank_id`, `query_bank_sha256`, `query_seed`, and exact query IDs.

- [ ] **Step 2: Run sampler tests and verify failure**

Run:

```powershell
python -m pytest -q tests/test_query_bank_sampler.py
```

Expected: import failure for `miaguard.query_bank.sampler`.

- [ ] **Step 3: Implement sampler**

Use only `random.Random`; never use global random state. Derive independent deterministic streams:

```python
def derived_seed(seed: int, namespace: str) -> int:
    digest = hashlib.sha256(f"{seed}:{namespace}".encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big")
```

Implement:

```python
def sample_query_bank(
    bank: QueryBank,
    *,
    members_per_attack: int,
    nonmembers_per_attack: int,
    benign_count: int,
    ia_turn_count: int,
    seed: int,
    variant_mode: str,
    canonical_fraction: float,
) -> dict[str, Any]:
```

Use these rules:

1. eligible documents must contain complete records for all five types;
2. sample one common member/nonmember document cohort;
3. select one Direct/S²/Masked query per document according to `variant_mode`;
4. group IA records into one row per document with `queries`;
5. IA uses independent yes/no shuffles and alternates the extra class for odd turn counts using the derived seed;
6. benign sampling uses distinct documents when capacity permits and cycles categories in seed-shuffled order;
7. return both replay-compatible rows and an audit section with exact query IDs.

For `mixed`, validate `0.0 <= canonical_fraction <= 1.0` and use a derived per-document random stream to choose canonical versus paraphrase. Record `canonical_fraction` in the selection manifest. For `canonical` and `paraphrase`, ignore the ratio and choose only the requested family.

Also implement the base-attack helper:

```python
def sample_attack_rows(
    bank: QueryBank,
    *,
    attack_type: str,
    limit_per_class: int,
    ia_turn_count: int,
    seed: int,
    variant_mode: str,
    canonical_fraction: float,
) -> dict[str, Any]:
```

It applies the same document, variant, and IA-answer rules for one attack and returns replay rows plus its exact query IDs.

Replay-compatible shapes:

```python
direct_row = {
    "doc_id": record["doc_id"],
    "membership_label": record["membership_label"],
    "attack_query": record["query_text"],
    "query_id": record["query_id"],
}

masked_row = {
    "doc_id": record["doc_id"],
    "membership_label": record["membership_label"],
    "masked_text": record["payload"]["masked_text"],
    "answers": record["payload"]["answers"],
    "query_id": record["query_id"],
}

ia_row = {
    "doc_id": doc_id,
    "membership_label": membership_label,
    "summary": selected[0]["payload"]["summary"],
    "queries": [
        {
            "adversarial_query": row["query_text"],
            "ground_truth": row["payload"]["ground_truth"],
            "question": row["payload"]["question"],
            "query_id": row["query_id"],
        }
        for row in selected
    ],
}
```

- [ ] **Step 4: Run sampler tests**

Run:

```powershell
python -m pytest -q tests/test_query_bank_sampler.py
```

Expected: all tests pass.

- [ ] **Step 5: Checkpoint**

Conditionally commit:

```powershell
git add src/miaguard/query_bank/sampler.py tests/test_query_bank_sampler.py
git commit -m "feat: sample frozen query bank"
```

## Task 5: Offline attack-query generation

**Files:**
- Create: `src/miaguard/query_bank/builder.py`
- Create: `tests/test_query_bank_builder.py`

- [ ] **Step 1: Write builder tests with a fake model client**

The fake client must return deterministic JSON for paraphrase, IA, verification, and benign prompts. Tests must assert:

```python
records = build_document_records(
    dataset_id="ag_news",
    document={
        "doc_id": "doc-1",
        "membership_label": 1,
        "text": "Alpha Corp acquired Beta Labs in Paris on Monday.",
    },
    build_config=config,
    attack_config=attack_config,
    client=fake_client,
)
assert len(records) == 50
assert Counter(row["attack_type"] for row in records) == {
    "direct_rag_mia": 5,
    "s2_mia": 5,
    "masked_mia": 5,
    "ia": 30,
    "benign": 5,
}
assert Counter(
    row["payload"]["ground_truth"]
    for row in records
    if row["attack_type"] == "ia"
) == {"yes": 15, "no": 15}
```

Add tests that:

- rejected IA verification causes another generation batch;
- a duplicate IA question is rejected;
- exhausting `ia_max_attempts` raises `RuntimeError` and returns no partial document result;
- membership label never appears in a captured generation prompt;
- all five Masked variants reuse identical `masked_text` and `answers`.

- [ ] **Step 2: Run builder tests and verify failure**

Run:

```powershell
python -m pytest -q tests/test_query_bank_builder.py
```

Expected: import failure for `miaguard.query_bank.builder`.

- [ ] **Step 3: Implement record construction helpers**

In `builder.py`, implement one envelope factory:

```python
def query_record(
    *,
    dataset_id: str,
    document: dict[str, Any],
    attack_type: str,
    variant_type: str,
    query_index: int,
    query_text: str,
    payload: dict[str, Any],
    backend: str,
    model: str,
    prompt_version: str,
    temperature: float,
    seed: int,
    answer_verified: bool,
) -> dict[str, Any]:
    record = {
        "query_id": make_query_id(
            dataset_id,
            str(document["doc_id"]),
            attack_type,
            variant_type,
            query_index,
        ),
        "dataset_id": dataset_id,
        "doc_id": str(document["doc_id"]),
        "membership_label": int(document["membership_label"]),
        "source_document_sha256": document_sha256(str(document["text"])),
        "traffic_type": "benign" if attack_type == "benign" else "attack",
        "attack_type": attack_type,
        "variant_type": variant_type,
        "query_index": query_index,
        "query_text": query_text.strip(),
        "payload": payload,
        "generation": {
            "backend": backend,
            "model": model,
            "prompt_version": prompt_version,
            "temperature": temperature,
            "seed": seed,
        },
        "validation": {
            "status": "accepted",
            "answer_verified": answer_verified,
            "duplicate_checked": True,
        },
        "created_at": utc_now_iso(),
    }
    validate_query_record(record)
    return record
```

Use existing canonical helpers:

- `direct_attack_query(text)`;
- `s2_query_prefix(text, attack_config.s2_mia_prefix_words)`;
- `mask_document(text, attack_config.mask_count, client, attack_config.generation_model, attack_config.masked_max_tokens)`.

Paraphrase prompts must request exactly four JSON strings and preserve attack-specific invariants. Reject blank, duplicate, or wrong-count output; do not insert deterministic fallback paraphrases.

- [ ] **Step 4: Implement IA and benign generation**

IA candidate generation must request a compact JSON object:

```json
{
  "summary": "short noun phrase",
  "candidates": [
    {"question": "Did Alpha acquire Beta?", "ground_truth": "yes"},
    {"question": "Did Gamma acquire Beta?", "ground_truth": "no"}
  ]
}
```

For each batch:

1. normalize and reject duplicate questions;
2. reject `ground_truth` outside yes/no;
3. reject ambiguous references matching `the text|the passage|the corpus|this document`;
4. call a separate verification prompt for the batch;
5. accept only candidates whose verification answer matches;
6. call `is_semantic_duplicate()` before accepting;
7. stop only at 15 accepted yes and 15 accepted no.

Benign generation requests one query for each approved category in one JSON object and rejects missing or blank categories.

`build_document_records()` must return records only after `validate_document_records()` succeeds. No partial list may escape on failure.

- [ ] **Step 5: Run builder tests**

Run:

```powershell
python -m pytest -q tests/test_query_bank_builder.py tests/test_query_bank_validator.py
```

Expected: all tests pass.

- [ ] **Step 6: Implement bank-level build orchestration**

Add:

```python
def build_query_bank(
    project_root: Path,
    bank_id: str,
    dataset_id: str,
    build_config: QueryBankBuildConfig,
    attack_config: AttackConfig,
    *,
    force_unlock: bool = False,
) -> dict[str, Any]:
```

Behavior:

- load source-run documents with `load_run_documents()`;
- deterministically sample configured member/nonmember pool using build seed;
- create `building` manifest before generation;
- acquire `QueryBankLock`;
- if `force_unlock` is true, call `QueryBankLock.force_remove(paths)` immediately before acquiring the lock;
- skip only complete, valid, hash-matching document shards;
- write one atomic shard after a document fully validates;
- append structured failures atomically by rewriting the small failure list;
- mark `incomplete` and raise if any document fails;
- compact, run complete-bank validation, write hashes/counts, and mark `complete`;
- return status, output path, document count, query count, and digest.

- [ ] **Step 7: Checkpoint**

Conditionally commit:

```powershell
git add src/miaguard/query_bank/builder.py tests/test_query_bank_builder.py
git commit -m "feat: build offline attack query bank"
```

## Task 6: Build, validate, and inspect scripts

**Files:**
- Create: `scripts/query_bank/build_query_bank.py`
- Create: `scripts/query_bank/validate_query_bank.py`
- Create: `scripts/query_bank/inspect_query_bank.py`
- Create: `configs/query_banks/ag_news_v1.yaml`
- Create: `tests/test_query_bank_cli.py`

- [ ] **Step 1: Write CLI tests**

Use `monkeypatch` to replace builder/validator functions and assert exact argument conversion. Include subprocess-style parser checks for required fields and `--force-unlock`.

Test `inspect_query_bank.py` against a temporary complete bank and assert printed JSON contains:

```json
{
  "status": "complete",
  "counts_by_attack": {
    "direct_rag_mia": 5,
    "s2_mia": 5,
    "masked_mia": 5,
    "ia": 30,
    "benign": 5
  },
  "ia_answers": {"yes": 15, "no": 15}
}
```

- [ ] **Step 2: Run CLI tests and verify failure**

Run:

```powershell
python -m pytest -q tests/test_query_bank_cli.py
```

Expected: scripts do not exist or imports fail.

- [ ] **Step 3: Implement thin scripts**

Each script must define `main() -> int`, use `argparse`, print sorted UTF-8 JSON, and return non-zero through an uncaught validation exception or explicit error handling consistent with `miaguard.cli`.

Build arguments:

```text
--config
--bank-id
--dataset
--project-root
--force-unlock
```

Validate/inspect arguments:

```text
--bank-id
--dataset
--project-root
```

The scripts must insert no dynamic source path; they rely on the editable package like existing project scripts.

- [ ] **Step 4: Add AG News configuration**

Create:

```yaml
source_run_id: 20260717-ag-news-four-medium
attack_config: configs/attacks/ag_news_calibrated_int8.yaml
seed: 20260724
pool:
  members: 50
  nonmembers: 50
queries:
  paraphrases_per_attack: 4
  ia_yes: 15
  ia_no: 15
  ia_batch_size: 6
  ia_max_attempts: 20
  semantic_duplicate_threshold: 0.92
  benign_categories:
    - topic
    - entity
    - event
    - summary
    - follow_up
```

This provides a five-times-larger document pool for a 10+10 experiment.

- [ ] **Step 5: Run CLI tests and help commands**

Run:

```powershell
python -m pytest -q tests/test_query_bank_cli.py
python scripts/query_bank/build_query_bank.py --help
python scripts/query_bank/validate_query_bank.py --help
python scripts/query_bank/inspect_query_bank.py --help
```

Expected: tests pass and all help commands exit 0.

- [ ] **Step 6: Checkpoint**

Conditionally commit:

```powershell
git add scripts/query_bank configs/query_banks tests/test_query_bank_cli.py
git commit -m "feat: add query bank command line tools"
```

## Task 7: Four base attacks consume frozen Query Bank rows

**Files:**
- Modify: `src/miaguard/cli.py`
- Modify: `src/miaguard/direct_rag_mia.py`
- Modify: `src/miaguard/s2_mia.py`
- Modify: `src/miaguard/masked_mia.py`
- Modify: `src/miaguard/ia_attack.py`
- Create: `tests/test_query_bank_attack_integration.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Write failing integration tests**

For each attack, monkeypatch:

- `QueryBank.load()` to return a complete fake bank;
- `sample_attack_rows()` to return one selected row;
- model client generation used for target answers;
- the online query constructor to raise `AssertionError("online query generation called")`.

Assert each attack completes without triggering the constructor and writes:

```json
{
  "query_bank_id": "bank-1",
  "query_bank_sha256": "digest",
  "query_seed": 17,
  "variant_mode": "canonical",
  "canonical_fraction": 1.0,
  "online_query_generation": false
}
```

Also assert selected `query_id` appears in its `results.jsonl`.

- [ ] **Step 2: Run integration tests and verify failure**

Run:

```powershell
python -m pytest -q tests/test_query_bank_attack_integration.py tests/test_cli.py
```

Expected: function signatures or CLI arguments do not yet accept Query Bank options.

- [ ] **Step 3: Add explicit frozen-input parameters**

Extend each base runner with keyword-only arguments:

```python
*,
query_bank_id: str | None = None,
query_seed: int = 20260724,
variant_mode: str = "canonical",
canonical_fraction: float = 1.0,
```

When `query_bank_id` is present:

1. load `QueryBankPaths(project_root, query_bank_id, dataset_id)`;
2. call `QueryBank.load()`;
3. call `sample_attack_rows()` for the requested class limit;
4. persist `query_selection_manifest.json` before target-RAG execution;
5. use the selected rows instead of `load_attack_documents()` query construction;
6. include Query Bank provenance in `attack_manifest.json`.

Keep the existing online behavior only when `query_bank_id is None` for backward compatibility. Frozen mode must contain no try/except fallback to online constructors.

- [ ] **Step 4: Wire CLI options**

For `masked-mia`, `ia`, `direct-rag-mia`, and `s2-mia`, add:

```python
child.add_argument("--query-bank-id")
child.add_argument("--query-seed", type=int, default=20260724)
child.add_argument(
    "--variant-mode",
    choices=("canonical", "paraphrase", "mixed"),
    default="canonical",
)
child.add_argument("--canonical-fraction", type=float, default=1.0)
```

Pass them to the runner functions. Update `tests/test_cli.py` to assert the values reach a monkeypatched runner.

- [ ] **Step 5: Run attack integration tests**

Run:

```powershell
python -m pytest -q tests/test_query_bank_attack_integration.py tests/test_cli.py
```

Expected: all tests pass.

- [ ] **Step 6: Run existing attack tests**

Run:

```powershell
python -m pytest -q tests/test_attack_resume.py tests/test_baseline_attacks.py tests/test_masked_mia_resilience.py tests/test_ia_resilience.py
```

Expected: all existing online/backward-compatibility tests pass.

- [ ] **Step 7: Checkpoint**

Conditionally commit:

```powershell
git add src/miaguard/cli.py src/miaguard/direct_rag_mia.py src/miaguard/s2_mia.py src/miaguard/masked_mia.py src/miaguard/ia_attack.py tests
git commit -m "feat: run attacks from frozen query bank"
```

## Task 8: Frozen benign replay and two-stage comparison

**Files:**
- Modify: `src/miaguard/defense_experiment.py`
- Modify: `src/miaguard/two_stage_attack_comparison.py`
- Modify: `scripts/run_two_stage_attack_comparison.py`
- Modify: `scripts/run_full_10x10.ps1`
- Modify: `tests/test_two_stage_attack_comparison.py`

- [ ] **Step 1: Replace IA expansion tests with frozen-selection tests**

Remove tests that require `expand_ia_rows()` to generate missing turns. Add tests that monkeypatch `_generate_questions` and `_generate_ground_truth` to raise if called, provide a frozen selection with three IA turns, and assert:

```python
assert no_defense_query_ids == with_defense_query_ids
assert result_manifest["online_query_generation"] is False
assert result_manifest["query_bank_id"] == "bank-1"
assert result_manifest["query_seed"] == 17
```

Add a benign replay test that passes a frozen benign record and asserts its exact `query_text` reaches `guard.prepare()`.

- [ ] **Step 2: Run focused tests and verify failure**

Run:

```powershell
python -m pytest -q tests/test_two_stage_attack_comparison.py
```

Expected: current comparison still calls baseline `_attack_rows()`, `expand_ia_rows()`, and deterministic benign construction.

- [ ] **Step 3: Add frozen benign replay**

Add `_replay_benign_queries()` to `defense_experiment.py`:

```python
def _replay_benign_queries(
    rows: list[dict[str, Any]],
    guard: GuardedRAG,
    client: ModelClient,
    config: AttackConfig,
    source_run_id: str,
    dataset_id: str,
    session_id_override: str | None = None,
    progress_label: str | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
```

It must use `row["query_text"]`, `row["query_id"]`, `row["doc_id"]`, and
`row["membership_label"]`; it must not derive a prefix from document text. Preserve the existing
target RAG answer behavior and progress output.

- [ ] **Step 4: Refactor two-stage preparation**

Extend `run_two_stage_attack_comparison()` with required frozen arguments:

```python
query_bank_id: str,
query_seed: int = 20260724,
variant_mode: str = "canonical",
canonical_fraction: float = 1.0,
```

Preparation must:

1. load the complete Query Bank;
2. call `sample_query_bank()` exactly once;
3. atomically write `query_selection_manifest.json`;
4. set `selected_rows = selection["attacks"]`;
5. run both defense arms with those same row objects;
6. replay `selection["benign"]`;
7. remove production use of `expand_ia_rows()`;
8. record Query Bank ID, digest, seed, variant mode, selection path, and `online_query_generation: false`.

Update `_replay_direct()`, `_replay_s2()`, `_replay_masked()`, and `_replay_ia()` so Query Bank rows do not require historical `membership_score` or `retrieved_doc_ids`. Each replay event must always include `query_id`; add baseline score/retrieval metadata only when those optional fields exist. This keeps legacy `data/attack_results` replay compatible while allowing pure Query Bank inputs.

Retain `expand_ia_rows()` only if another legacy experiment imports it; otherwise delete it and remove obsolete imports. Do not leave a frozen-mode fallback path.

- [ ] **Step 5: Update script and PowerShell entry**

Add required script argument:

```python
parser.add_argument("--query-bank-id", required=True)
parser.add_argument("--query-seed", type=int, default=20260724)
parser.add_argument(
    "--variant-mode",
    choices=("canonical", "paraphrase", "mixed"),
    default="canonical",
)
parser.add_argument("--canonical-fraction", type=float, default=1.0)
```

Update `scripts/run_full_10x10.ps1` parameters:

```powershell
param(
    [string]$OutputRunId = "20260724-ag-news-query-bank-10x10-v1",
    [string]$QueryBankId = "ag_news_queries_v1",
    [int]$QuerySeed = 20260724
)
```

Pass `--query-bank-id`, `--query-seed`, `--variant-mode canonical`, and `--canonical-fraction 1.0`. Remove `OffsetPerClass` because the Query Bank sampler replaces offset-based selection.

- [ ] **Step 6: Run comparison tests**

Run:

```powershell
python -m pytest -q tests/test_two_stage_attack_comparison.py tests/test_defense.py
```

Expected: all tests pass and no online IA query generation is called.

- [ ] **Step 7: Checkpoint**

Conditionally commit:

```powershell
git add src/miaguard/defense_experiment.py src/miaguard/two_stage_attack_comparison.py scripts/run_two_stage_attack_comparison.py scripts/run_full_10x10.ps1 tests/test_two_stage_attack_comparison.py
git commit -m "feat: use frozen queries in two-stage comparison"
```

## Task 9: Independent validation, documentation, and full verification

**Files:**
- Modify: `docs/USAGE_GUIDE_ZH.md`
- Modify: `README.md`
- Create: `configs/query_banks/ag_news_smoke.yaml`
- Modify: tests from prior tasks if full-suite regressions expose contract mismatches

- [ ] **Step 1: Document the offline-first workflow**

Add a Query Bank section to `docs/USAGE_GUIDE_ZH.md` with exact commands:

```powershell
python scripts/query_bank/build_query_bank.py `
  --config configs/query_banks/ag_news_v1.yaml `
  --bank-id ag_news_queries_v1 `
  --dataset ag_news

python scripts/query_bank/validate_query_bank.py `
  --bank-id ag_news_queries_v1 `
  --dataset ag_news

python scripts/query_bank/inspect_query_bank.py `
  --bank-id ag_news_queries_v1 `
  --dataset ag_news

python scripts/run_two_stage_attack_comparison.py `
  --config configs/attacks/ag_news_calibrated_int8.yaml `
  --gateway-config configs/defense/two_stage_direct_enforce_calibrated_010.yaml `
  --source-run-id 20260717-ag-news-four-medium `
  --dataset ag_news `
  --output-run-id 20260724-ag-news-frozen-smoke-v1 `
  --query-bank-id ag_news_queries_v1 `
  --query-seed 20260724 `
  --variant-mode canonical `
  --limit-per-class 1 `
  --benign-count 2 `
  --ia-turn-count 3
```

Explicitly explain:

- build cost is paid once;
- frozen experiments still call the target RAG and defense models;
- changing source documents, generation model, or prompt version requires a new bank ID;
- `incomplete` banks cannot run formal experiments;
- `--force-unlock` is only for a verified stale lock after no builder process is running.

Add a short README link to the new guide section.

- [ ] **Step 2: Run Query Bank test group**

Run:

```powershell
python -m pytest -q tests/test_query_bank_schema.py tests/test_query_bank_storage.py tests/test_query_bank_validator.py tests/test_query_bank_sampler.py tests/test_query_bank_builder.py tests/test_query_bank_cli.py tests/test_query_bank_attack_integration.py tests/test_two_stage_attack_comparison.py
```

Expected: all Query Bank and comparison tests pass.

- [ ] **Step 3: Run full test suite**

Run:

```powershell
python -m pytest -q
```

Expected: no failures. Record the exact passed/skipped counts in the implementation handoff.

- [ ] **Step 4: Run dependency check**

Run:

```powershell
python -m pip check
```

Expected: `No broken requirements found.`

- [ ] **Step 5: Run no-model CLI smoke checks**

Run:

```powershell
python scripts/query_bank/build_query_bank.py --help
python scripts/query_bank/validate_query_bank.py --help
python scripts/query_bank/inspect_query_bank.py --help
python scripts/run_two_stage_attack_comparison.py --help
```

Expected: every command exits 0.

- [ ] **Step 6: Run one real offline build smoke**

Create `configs/query_banks/ag_news_smoke.yaml`:

```yaml
source_run_id: 20260717-ag-news-four-medium
attack_config: configs/attacks/ag_news_calibrated_int8.yaml
seed: 20260724
pool:
  members: 1
  nonmembers: 1
queries:
  paraphrases_per_attack: 4
  ia_yes: 15
  ia_no: 15
  ia_batch_size: 6
  ia_max_attempts: 20
  semantic_duplicate_threshold: 0.92
  benign_categories:
    - topic
    - entity
    - event
    - summary
    - follow_up
```

Run:

```powershell
python scripts/query_bank/build_query_bank.py `
  --config configs/query_banks/ag_news_smoke.yaml `
  --bank-id ag_news_queries_smoke_v1 `
  --dataset ag_news
```

Expected:

- status `complete`;
- 2 documents;
- 100 accepted queries;
- each document has IA 15 yes/15 no and all other approved counts;
- `online_query_generation` is not an experiment field because this is the offline build phase.

- [ ] **Step 7: Run one real frozen experiment smoke**

Run the two-stage command with `limit-per-class=1`, `benign-count=2`, and the smoke bank.

Expected:

- output manifest contains `online_query_generation: false`;
- no log line containing both `phase=prepare attack=ia` and `source=generated`;
- the same IA query IDs appear in no-defense and with-defense event streams;
- experiment completes and writes all existing comparison outputs.

- [ ] **Step 8: Final checkpoint**

If Git is available:

```powershell
git add docs README.md configs scripts src tests
git commit -m "docs: document offline query bank workflow"
git status --short
```

Expected: clean status after commit. If Git remains unavailable, report that implementation is verified but uncommitted because the workspace is not a repository.
