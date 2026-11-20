# IA Query Bank 10+10 Anchor-Pair Repair Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Repair `ag_news_queries_v1` so every document has at least 10 independently verified IA `yes` and 10 independently verified IA `no` queries, using verified positive-question anchors instead of atomic-fact extraction.

**Architecture:** Treat the published Query Bank as the only baseline. Build or reuse safe auxiliary-led `yes` questions, derive one `no` per anchor through a constrained single-slot counterfactual, and fall back to deterministic polarity inversion only after counterfactual verification fails. Preserve the old progress file in an archive, checkpoint every accepted record, and publish only after whole-bank validation.

**Tech Stack:** Python 3, pytest, existing `ModelClient`, Query Bank schema/storage/validator modules.

**Repository note:** `D:\Project\MIAGuard` is not a Git worktree, so the commit steps required by the generic workflow are not available. Each task ends with a focused test checkpoint instead.

---

### Task 1: Change the minimum IA threshold to 10+10

**Files:**
- Modify: `src/miaguard/query_bank/validator.py`
- Modify: `src/miaguard/query_bank/repair.py`
- Modify: `scripts/query_bank/repair_ia_query_bank.py`
- Modify: `tests/test_query_bank.py`
- Modify: `tests/test_query_bank_repair.py`

- [ ] **Step 1: Change tests to require 10+10 and reject 9+10**

```python
def test_document_requires_ten_yes_and_ten_no_ia_records() -> None:
    records = ia_records(yes=10, no=10)
    validate_document_records(records, document)
    with pytest.raises(ValueError, match="at least 10 yes and 10 no"):
        validate_document_records(ia_records(yes=9, no=10), document)
```

- [ ] **Step 2: Run the focused tests and confirm they fail against the current 15+15 constant**

Run: `conda run -n rag_env python -m pytest tests/test_query_bank.py tests/test_query_bank_repair.py -q --basetemp D:\Project\MIAGuard\.pytest-tmp-10x10-red`

Expected: FAIL because `IA_MIN_ANSWER_COUNTS` is still `{"yes": 15, "no": 15}`.

- [ ] **Step 3: Change the production threshold and user-facing descriptions**

```python
IA_MIN_ANSWER_COUNTS = {"yes": 10, "no": 10}
```

Update validator errors, repair docstrings, and CLI description to say “10 yes and 10 no”. Do not change existing record contents.

- [ ] **Step 4: Re-run the focused tests**

Expected: PASS.

### Task 2: Add safe `yes` anchor classification and polarity inversion

**Files:**
- Modify: `src/miaguard/query_bank/builder.py`
- Modify: `tests/test_query_bank_builder.py`

- [ ] **Step 1: Write failing tests for supported and unsupported anchors**

```python
@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ("Did Newman dominate Dover?", True),
        ("Was Gordon the points leader?", True),
        ("Who took the points lead?", False),
        ("What happened at Dover?", False),
    ],
)
def test_safe_yes_anchor_detection(question: str, expected: bool) -> None:
    assert _is_safe_yes_anchor(question) is expected


def test_polarity_flip_inserts_not_after_auxiliary() -> None:
    assert _flip_question_polarity("Did Newman dominate Dover?") == (
        "Did Newman not dominate Dover?"
    )
```

- [ ] **Step 2: Run the focused tests and confirm missing helpers fail**

Run: `conda run -n rag_env python -m pytest tests/test_query_bank_builder.py -k "safe_yes_anchor or polarity_flip" -q`

- [ ] **Step 3: Implement the minimal grammar helpers**

```python
_IA_SAFE_AUXILIARIES = {
    "is", "are", "was", "were", "do", "does", "did",
    "has", "have", "had", "can", "could", "will", "would", "should",
}


def _is_safe_yes_anchor(question: str) -> bool:
    match = re.match(r"^([A-Za-z]+)\b", question.strip())
    return bool(match and match.group(1).casefold() in _IA_SAFE_AUXILIARIES)


def _flip_question_polarity(question: str) -> str:
    if not _is_safe_yes_anchor(question):
        raise ValueError("IA anchor is not safe for polarity inversion")
    return re.sub(r"^([A-Za-z]+)\s+", r"\1 not ", question.strip(), count=1)
```

Also normalize an existing immediate `not` by removing it, so polarity inversion remains symmetric.

- [ ] **Step 4: Re-run builder tests**

Expected: PASS.

### Task 3: Generate additional verified safe `yes` anchors

**Files:**
- Modify: `src/miaguard/query_bank/builder.py`
- Modify: `tests/test_query_bank_builder.py`

- [ ] **Step 1: Write a failing test for restricted positive-anchor generation**

```python
def test_yes_anchor_generation_accepts_only_safe_verified_yes_questions() -> None:
    summary, anchors = _ia_yes_anchor_candidates(
        text="Ryan Newman dominated Dover.",
        target_count=2,
        existing_questions=(),
        attack_config=config,
        client=client,
    )
    assert [row["ground_truth"] for row in anchors] == ["yes", "yes"]
    assert all(_is_safe_yes_anchor(row["question"]) for row in anchors)
```

- [ ] **Step 2: Verify the test fails because `_ia_yes_anchor_candidates` does not exist**

- [ ] **Step 3: Implement restricted generation and existing-verifier filtering**

The prompt must require one positive, single-fact, self-contained question per item and require every question to start with one of the supported auxiliaries. Generate batches using the existing JSON/plain fallback utilities, reject unsafe syntax and normalized duplicates, call `_verify_ia_answers`, and accept only label `yes` until `target_count` is reached.

```python
def _ia_yes_anchor_candidates(
    text: str,
    build_config: QueryBankBuildConfig,
    attack_config: AttackConfig,
    client: ModelClient,
    *,
    target_count: int,
    existing_questions: tuple[str, ...] = (),
) -> tuple[str, list[dict[str, str]]]:
    accepted: list[dict[str, str]] = []
    normalized = {normalize_query(q) for q in existing_questions}
    summary = ""
    for attempt in range(build_config.ia_max_attempts):
        prompt = _yes_anchor_prompt(text, build_config.ia_batch_size, existing_questions)
        value = _generate_json_object_with_retry(
            client,
            attack_config.generation_model,
            prompt,
            max(768, attack_config.ia_generation_max_tokens),
            0.2,
        )
        summary = summary or str(value.get("summary", "")).strip()
        questions = [q for q in _strings(value, "questions") if _is_safe_yes_anchor(q)]
        questions = [q for q in questions if normalize_query(q) not in normalized]
        labels = _verify_ia_answers(text, questions, attack_config, client)
        for question, label in zip(questions, labels):
            if label == "yes" and normalize_query(question) not in normalized:
                normalized.add(normalize_query(question))
                accepted.append({"question": question, "ground_truth": "yes"})
                if len(accepted) == target_count:
                    return summary or "reported fact", accepted
    raise RuntimeError(
        f"IA anchor generation accepted {len(accepted)} of {target_count} required yes questions"
    )
```

- [ ] **Step 4: Run builder tests and confirm exact-count, duplicate, and wrong-label cases pass**

### Task 4: Generate one verified `no` from each `yes` anchor

**Files:**
- Modify: `src/miaguard/query_bank/builder.py`
- Modify: `tests/test_query_bank_builder.py`

- [ ] **Step 1: Write failing tests for the two-stage path**

```python
def test_counterfactual_no_uses_one_anchor_once() -> None:
    rows = _ia_no_candidates_from_anchors(
        text="Ryan Newman dominated Dover while Jeff Gordon led the standings.",
        anchors=("Did Ryan Newman dominate Dover?", "Did Jeff Gordon lead the standings?"),
        target_count=2,
        existing_questions=(),
        attack_config=config,
        client=client,
    )
    assert len(rows) == 2
    assert len({row["anchor_question"] for row in rows}) == 2
    assert {row["ground_truth"] for row in rows} == {"no"}


def test_polarity_fallback_runs_only_after_counterfactual_rejection() -> None:
    rows = _ia_no_candidates_from_anchors(
        text="Ryan Newman dominated Dover.",
        anchors=("Did Ryan Newman dominate Dover?",),
        target_count=1,
        existing_questions=(),
        attack_config=config,
        client=client,
    )
    assert rows[0]["construction"] == "polarity_flip"
    assert rows[0]["question"] == "Did Newman not dominate Dover?"
```

- [ ] **Step 2: Verify both tests fail before implementation**

- [ ] **Step 3: Implement constrained counterfactual generation**

For each unused anchor, ask for up to three variants that change exactly one named entity, location, date, number, relationship, or outcome. Reject unchanged text, unsafe/non-question output, normalized duplicates, and ambiguous references. Verify the batch and select the first strict `no`.

```python
{
    "question": counterfactual,
    "ground_truth": "no",
    "anchor_question": anchor,
    "construction": "counterfactual",
}
```

- [ ] **Step 4: Implement verified polarity fallback**

If no counterfactual for the anchor verifies as `no`, call `_flip_question_polarity(anchor)`, independently verify the result, and accept it only if the result is `no`. Never emit more than one final `no` per anchor.

- [ ] **Step 5: Run builder tests**

Expected: PASS, including tests proving fallback order and one-anchor/one-`no` behavior.

### Task 5: Replace the repair orchestration and isolate old progress

**Files:**
- Modify: `src/miaguard/query_bank/repair.py`
- Modify: `src/miaguard/query_bank/storage.py`
- Modify: `tests/test_query_bank_repair.py`

- [ ] **Step 1: Write failing tests for old-progress archival and a fresh baseline**

```python
def test_anchor_pair_repair_archives_legacy_progress_without_reusing_rows(tmp_path: Path) -> None:
    paths.repair_progress.write_text(legacy_state, encoding="utf-8")
    repair_ia_query_bank(
        tmp_path,
        "bank-1",
        "ag_news",
        config_path,
        seed=17,
        client=client,
    )
    archives = list(paths.repair_progress_archive.glob("*.jsonl"))
    assert len(archives) == 1
    assert legacy_query_id not in read_jsonl(paths.queries)
```

- [ ] **Step 2: Add a dedicated archive directory and ensure compaction reads only shard filenames**

```python
@property
def repair_progress_archive(self) -> Path:
    return self.work / "repair-progress-archive"
```

`compact_query_bank` must accept only filenames matching `[0-9a-f]{64}.jsonl`; progress and archive data must never be interpreted as query shards.

- [ ] **Step 3: Version and archive incompatible progress**

Use scheme version `anchor-pair-10x10-v1`. When the current progress is absent or has another version, move it into the archive directory under a timestamped filename and start from the published bank. Never delete the archived state.

- [ ] **Step 4: Compute anchor requirements per document**

```python
yes_gap = max(0, 10 - counts["yes"])
no_gap = max(0, 10 - counts["no"])
safe_existing = [q for q in verified_yes if _is_safe_yes_anchor(q)]
yes_to_generate = max(yes_gap, no_gap - len(safe_existing))
```

Generate `yes_to_generate` safe verified anchors, append only the number required, then derive exactly `no_gap` verified `no` records from distinct safe anchors.

- [ ] **Step 5: Store anchor provenance in new `no` payloads**

```python
payload={
    "summary": summary,
    "question": question,
    "ground_truth": "no",
    "anchor_question": anchor_question,
    "construction": construction,
}
```

- [ ] **Step 6: Checkpoint after every accepted record**

The state must contain scheme version, thresholds, completed documents, current document, accepted rows, used anchors, rejection counts, model identity, seed, and timestamp. Resume from these fields without regenerating saved records.

- [ ] **Step 7: Run repair tests**

Expected: old Query Bank rows remain unchanged, archived progress remains readable, interrupted runs do not publish, resumed runs do not duplicate rows, and completed fixtures satisfy 10+10.

### Task 6: Verify publication and deterministic 10+10 sampling

**Files:**
- Modify: `tests/test_query_bank.py`
- Modify: `tests/test_query_bank_repair.py`
- Modify only if necessary: experiment sampling code located by `rg "ground_truth.*yes|ia_min_answer_counts" src scripts`

- [ ] **Step 1: Add a test that a repaired bank validates with 10+10 and preserves `unknown`**

```python
assert counts == {"yes": 10, "no": 10, "unknown": original_unknown}
```

- [ ] **Step 2: Add or update a deterministic sampling test**

For a document containing more than 10 rows of a label, the same experiment seed must select the same 10 query IDs on repeated runs; another valid seed may select a different subset. `unknown` IDs must never appear.

- [ ] **Step 3: Run all Query Bank and sampling tests**

Run: `conda run -n rag_env python -m pytest tests/test_query_bank_builder.py tests/test_query_bank_repair.py tests/test_query_bank.py tests/test_query_bank_scripts.py -q --basetemp D:\Project\MIAGuard\.pytest-tmp-10x10-final`

Expected: all tests pass with zero failures.

### Task 7: Run a real checkpointed repair

**Files:**
- Run: `scripts/query_bank/repair_ia_query_bank.py`
- Inspect: `data/query_banks/ag_news_queries_v1/ag_news/.work/ia_repair_progress.jsonl`
- Inspect: `data/logs/ia_query_bank_repair_20260817_anchor_pair.stdout.log`
- Inspect: `data/logs/ia_query_bank_repair_20260817_anchor_pair.stderr.log`

- [ ] **Step 1: Confirm no repair worker or Query Bank lock exists**

Use read-only process and lock checks. Do not start a second worker.

- [ ] **Step 2: Record the published query SHA-256 before launch**

Expected baseline SHA-256: `46B32CDBA568BADD465A25016E0AB0C2D7F60950904D98207015CB2B84621E4B`, unless the published bank has legitimately changed since design approval.

- [ ] **Step 3: Start one unbuffered GPU worker with separate stdout/stderr logs**

Run in the `MIAGuard` environment with `conda run --no-capture-output` and `python -u`.

- [ ] **Step 4: Verify the first repaired document reaches 10+10 and progress advances**

Check process liveness, log timestamps, current/completed document count, rejection distribution, and that the published SHA remains unchanged before whole-bank completion.
