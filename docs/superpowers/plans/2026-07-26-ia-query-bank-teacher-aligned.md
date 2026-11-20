# IA Query Bank Teacher-Aligned Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build exactly 30 independently answered IA questions per document without a fixed yes/no balance or semantic-similarity rejection, while allowing `unknown`.

**Architecture:** Replace the balanced IA configuration with a single target count. Generate question strings in batches, remove only invalid and exact-normalized duplicates, then assign `yes/no/unknown` using a separate verification call. Keep the existing 50-record document boundary and expose actual IA answer distributions through validation, manifest, and inspection output.

**Tech Stack:** Python 3.10+, pytest, PyYAML, local Transformers ModelClient, JSONL Query Bank storage.

---

The workspace does not contain a `.git` directory, so commit steps are intentionally omitted. All edits remain local and are verified through tests and generated artifacts.

### Task 1: Change the IA configuration and record contract

**Files:**
- Modify: `tests/test_query_bank.py`
- Modify: `src/miaguard/query_bank/schema.py`
- Modify: `configs/query_banks/ag_news_smoke.yaml`
- Modify: `configs/query_banks/ag_news_v1.yaml`

- [ ] **Step 1: Write failing configuration and ground-truth tests**

Replace the balanced configuration test with:

```python
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
```

Add:

```python
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
```

- [ ] **Step 2: Run the tests and verify RED**

Run:

```powershell
D:\ProgramData\Anaconda3\envs\MIAGuard\python.exe -m pytest `
  tests/test_query_bank.py::test_config_requires_30_teacher_aligned_ia_queries `
  tests/test_query_bank.py::test_ia_record_accepts_unknown_ground_truth -q
```

Expected: failures because `QueryBankBuildConfig` has no
`ia_questions_per_document` and `unknown` is rejected.

- [ ] **Step 3: Implement the minimal schema change**

Change the dataclass IA fields to:

```python
ia_questions_per_document: int
ia_batch_size: int
ia_max_attempts: int
```

Keep the compatibility property:

```python
@property
def ia_total(self) -> int:
    return self.ia_questions_per_document
```

Load and validate:

```python
ia_questions_per_document=int(
    queries.get("ia_questions_per_document", 30)
),
```

Include it in the positive counts and enforce:

```python
if config.ia_questions_per_document != 30:
    raise ValueError("IA Query Bank requires exactly 30 questions per document")
```

Remove `ia_yes`, `ia_no`, and `semantic_duplicate_threshold` from the dataclass,
loader, and validation. Change the IA record condition to:

```python
if payload.get("ground_truth") not in {"yes", "no", "unknown"}:
    raise ValueError("IA ground_truth must be yes, no, or unknown")
```

Update both YAML files to:

```yaml
  ia_questions_per_document: 30
  ia_batch_size: 6
  ia_max_attempts: 20
```

- [ ] **Step 4: Run the focused tests and verify GREEN**

Run the same two-test command. Expected: `2 passed`.

### Task 2: Replace balanced IA generation with independent three-label verification

**Files:**
- Modify: `tests/test_query_bank_builder.py`
- Modify: `src/miaguard/query_bank/builder.py`

- [ ] **Step 1: Change the fake model to return questions without self-reported labels**

For `IA_CANDIDATES`, derive the requested count from the prompt and return:

```python
match = re.search(r"generate exactly (\d+) new", prompt, flags=re.IGNORECASE)
count = int(match.group(1))
offset = sum("Previously accepted questions:" in item for item in self.prompts)
return {
    "summary": "Alpha acquisition",
    "questions": [
        f"Did documented fact {offset * count + index} happen?"
        for index in range(1, count + 1)
    ],
}
```

For `IA_VERIFY`, return a deliberately unbalanced distribution including unknown:

```python
questions = re.findall(r"^\d+\. (.+)$", prompt, flags=re.MULTILINE)
answers = ("yes", "no", "unknown")
return {
    "answers": [
        answers[(index - 1) % len(answers)]
        for index, _question in enumerate(questions, start=1)
    ]
}
```

Make `embed()` fail if the IA builder calls it:

```python
def embed(self, model, texts):
    if any("documented fact" in text for text in texts):
        raise AssertionError("IA generation must not use semantic embeddings")
    ...
```

- [ ] **Step 2: Write failing generator assertions**

Construct `QueryBankBuildConfig` with:

```python
ia_questions_per_document=30,
ia_batch_size=6,
ia_max_attempts=6,
```

Rename the complete-pool test and assert:

```python
assert Counter(
    row["payload"]["ground_truth"]
    for row in records
    if row["attack_type"] == "ia"
) == {"yes": 10, "no": 10, "unknown": 10}
```

Add a client that returns a duplicate in the second batch, then assert:

```python
summary, candidates = _ia_candidates(
    "Alpha Corp acquired Beta Labs.",
    build_config,
    attack_config,
    client,
)

assert len(candidates) == 30
assert len(
    {normalize_query(item["question"]) for item in candidates}
) == 30
assert any(
    "Previously accepted questions:" in prompt
    for prompt in client.prompts
    if "IA_CANDIDATES" in prompt
)
```

- [ ] **Step 3: Run the builder tests and verify RED**

Run:

```powershell
D:\ProgramData\Anaconda3\envs\MIAGuard\python.exe -m pytest `
  tests/test_query_bank_builder.py -q
```

Expected: failures from removed config fields, old candidate schema, balance
requirements, and semantic embedding use.

- [ ] **Step 4: Implement the new `_ia_candidates` flow**

Use one accepted list:

```python
accepted: list[dict[str, str]] = []
normalized: set[str] = set()
summary = ""
```

At each attempt:

```python
missing = build_config.ia_questions_per_document - len(accepted)
if missing == 0:
    break
request_count = min(missing, build_config.ia_batch_size)
```

The generation prompt must request only strings:

```text
[IA_CANDIDATES]
Using only the source document, generate exactly {request_count} new, specific,
self-contained questions. The questions should be answerable as yes, no, or unknown
from the source document. Do not say the text, the passage, the corpus, or this
document. Return only JSON:
{"summary":"short noun phrase","questions":["question 1","question 2"]}
```

When accepted questions exist, append:

```text
Previously accepted questions:
1. ...

Do not repeat any previously accepted question.
```

Filter candidates only for blank text, ambiguous references, and
`normalize_query(question) in normalized`. Verify the filtered batch with
`[IA_VERIFY]`, accepting only answers in `{"yes", "no", "unknown"}`. Add verified
items until the target count is reached.

Remove `_cosine_duplicate` and all `client.embed()` calls from the IA construction
path. Print one diagnostic line per attempt using the exact counters
`requested`, `generated`, `invalid`, `duplicate`, `unverified`, `accepted`,
`total`, and current answer counts.

On exhaustion raise:

```python
answer_counts = Counter(item["ground_truth"] for item in accepted)
raise RuntimeError(
    "IA generation could not produce exactly "
    f"{build_config.ia_questions_per_document} verified questions; "
    f"accepted={len(accepted)} answers={answer_counts}"
)
```

- [ ] **Step 5: Run the builder tests and verify GREEN**

Run the Task 2 test command. Expected: all tests in
`tests/test_query_bank_builder.py` pass.

### Task 3: Update validation, manifest, and inspection statistics

**Files:**
- Modify: `tests/test_query_bank.py`
- Modify: `src/miaguard/query_bank/validator.py`
- Modify: `src/miaguard/query_bank/builder.py`

- [ ] **Step 1: Make the document fixture include unknown answers**

Change `_document_records()` to produce:

```python
answers = ("yes", "no", "unknown")
rows.extend(
    _record(
        doc_id,
        membership_label,
        "ia",
        "generated",
        index,
        answer=answers[(index - 1) % len(answers)],
    )
    for index in range(1, 31)
)
```

Rename the validator test and assert:

```python
assert report["query_count"] == 50
assert report["ia_answers"] == {
    "yes": 10,
    "no": 10,
    "unknown": 10,
}
```

Add a test that writes a complete two-document bank and verifies:

```python
report = inspect_query_bank(tmp_path, "bank-1", "ag_news")
assert report["ia_answers"] == {
    "no": 20,
    "unknown": 20,
    "yes": 20,
}
```

- [ ] **Step 2: Run focused validator tests and verify RED**

Run:

```powershell
D:\ProgramData\Anaconda3\envs\MIAGuard\python.exe -m pytest `
  tests/test_query_bank.py -q
```

Expected: the old validator rejects unknown and requires 15/15.

- [ ] **Step 3: Remove the fixed balance check**

In `validate_document_records()`, keep the answer count for reporting but replace
the 15/15 condition with:

```python
if sum(ia_answers.values()) != EXPECTED_COUNTS["ia"]:
    raise ValueError("Document must contain exactly 30 IA answers")
```

The existing normalized exact-duplicate check remains unchanged.

- [ ] **Step 4: Add manifest answer statistics**

Use:

```python
def _ia_answer_counts(records: list[dict[str, Any]]) -> dict[str, int]:
    return dict(
        sorted(
            Counter(
                str(row["payload"]["ground_truth"])
                for row in records
                if row["attack_type"] == "ia"
            ).items()
        )
    )
```

Create building manifests with:

```python
"schema_version": "1.1.0",
"ia_questions_per_document": build_config.ia_questions_per_document,
```

Remove `ia_balance`. When completing the bank, add:

```python
"ia_answer_counts": _ia_answer_counts(records),
```

In `inspect_query_bank()`, compute the record counts and reject a manifest mismatch
when `ia_answer_counts` is present:

```python
if "ia_answer_counts" in bank.manifest:
    if dict(bank.manifest["ia_answer_counts"]) != ia_answers:
        raise ValueError("Query Bank manifest IA answer counts do not match records")
```

- [ ] **Step 5: Run Query Bank tests and verify GREEN**

Run:

```powershell
D:\ProgramData\Anaconda3\envs\MIAGuard\python.exe -m pytest `
  tests/test_query_bank.py tests/test_query_bank_builder.py `
  tests/test_query_bank_scripts.py `
  tests/test_query_bank_two_stage_integration.py -q
```

Expected: all Query Bank tests pass.

### Task 4: Update user documentation

**Files:**
- Modify: `scripts/query_bank/README.md`
- Modify: `docs/QUERY_BANK_ZH.md`

- [ ] **Step 1: Replace balanced-field examples**

All configuration examples must show:

```yaml
ia_questions_per_document: 30
ia_batch_size: 6
ia_max_attempts: 20
```

Remove `ia_yes`, `ia_no`, and `semantic_duplicate_threshold` from active
configuration tables and troubleshooting advice.

- [ ] **Step 2: Document teacher-aligned IA semantics**

State explicitly:

```text
每个目标文档保存 30 条 IA 问题。问题的独立标准答案允许 yes、no、unknown，
不要求固定类别比例。构建器只删除规范化文本完全相同的问题，不执行语义相似度硬去重。
```

Document the per-attempt diagnostic log and explain that a non-balanced answer
distribution is valid.

- [ ] **Step 3: Check documentation for stale requirements**

Run:

```powershell
rg -n "ia_yes|ia_no|semantic_duplicate_threshold|15.*yes|15.*no" `
  scripts/query_bank/README.md docs/QUERY_BANK_ZH.md `
  configs/query_banks
```

Expected: no matches.

### Task 5: Verify code and run the gated builds

**Files:**
- Verify: all project tests
- Generate: `data/query_banks/ag_news_queries_smoke_v1/ag_news/`
- Generate: `data/query_banks/ag_news_queries_v1/ag_news/`

- [ ] **Step 1: Run the complete automated suite**

Run:

```powershell
D:\ProgramData\Anaconda3\envs\MIAGuard\python.exe -m pytest -q
```

Expected: all tests pass, with only the existing optional skip and SWIG warnings.

- [ ] **Step 2: Rebuild the smoke Bank and clear only its stale lock**

Run:

```powershell
conda run -n MIAGuard python scripts/query_bank/build_query_bank.py `
  --config configs/query_banks/ag_news_smoke.yaml `
  --bank-id ag_news_queries_smoke_v1 `
  --dataset ag_news `
  --force-unlock
```

Expected: both documents report `status=completed queries=50` and the final status
is `complete`.

- [ ] **Step 3: Validate and inspect smoke**

Run:

```powershell
conda run -n MIAGuard python scripts/query_bank/validate_query_bank.py `
  --bank-id ag_news_queries_smoke_v1 `
  --dataset ag_news

conda run -n MIAGuard python scripts/query_bank/inspect_query_bank.py `
  --bank-id ag_news_queries_smoke_v1 `
  --dataset ag_news
```

Expected: validation status `valid`, document count `2`, query count `100`, IA
count `60`, and any valid `yes/no/unknown` distribution.

- [ ] **Step 4: Start formal construction only after Step 3 succeeds**

Run:

```powershell
conda run -n MIAGuard python scripts/query_bank/build_query_bank.py `
  --config configs/query_banks/ag_news_v1.yaml `
  --bank-id ag_news_queries_v1 `
  --dataset ag_news
```

Expected: completed documents are persisted under `.work` and reused after an
interruption. Do not run formal validation until construction reports `complete`.
