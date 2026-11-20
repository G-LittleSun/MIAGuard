# Deterministic IA `no` Queries Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construct IA `no` questions from extracted factual claims with program-owned negation, so every accepted candidate is a deterministic single-polarity contradiction before independent verification.

**Architecture:** Keep the model only for extracting atomic factual claims. Replace free-form `no` question generation with fixed question templates that negate each extracted claim; use the existing verifier and duplicate filter unchanged. The repair checkpoint continues to preserve completed labels and primary Query Bank files are published only after whole-bank validation.

**Tech Stack:** Python, pytest, existing Query Bank builder/validator/repair modules.

---

### Task 1: Specify deterministic `no` construction in tests

**Files:**
- Modify: `tests/test_query_bank_builder.py`
- Test: `tests/test_query_bank_builder.py`

- [ ] **Step 1: Write the failing test**

```python
def test_ia_no_candidates_are_programmatically_negated_facts() -> None:
    summary, candidates = _ia_candidates(..., required_answer="no")
    assert len(candidates) == 4
    assert {row["ground_truth"] for row in candidates} == {"no"}
    assert all(question.startswith(("Is it false that", "Is it untrue that"))
               for question in (row["question"] for row in candidates))
    assert not any("[IA_NO_CONTRADICTIONS]" in prompt for prompt in client.prompts)
```

- [ ] **Step 2: Run the focused test and verify it fails**

Run: `conda run -n rag_env python -m pytest tests/test_query_bank_builder.py::test_ia_no_candidates_are_programmatically_negated_facts -q`

Expected: FAIL because the current implementation delegates `no` question wording to `[IA_NO_CONTRADICTIONS]`.

### Task 2: Construct `no` candidates without free-form generation

**Files:**
- Modify: `src/miaguard/query_bank/builder.py`
- Test: `tests/test_query_bank_builder.py`

- [ ] **Step 1: Extract atomic facts with a declarative `statement`**

```python
{"facts":[{"subject":"...","attribute":"...","value":"...",
           "statement":"atomic fact stated by the source"}]}
```

- [ ] **Step 2: Add fixed negated-question templates**

```python
_IA_NO_QUESTION_TEMPLATES = (
    "Is it false that {statement}?",
    "Is it untrue that {statement}?",
    "Does the claim that {statement} fail to hold?",
    "Is the claim that {statement} incorrect?",
)
```

- [ ] **Step 3: Route `required_answer="no"` through the fixed templates, then the existing verifier and duplicate filter**

```python
if required_answer == "no":
    return _ia_no_candidates_from_facts(...)
```

- [ ] **Step 4: Run focused builder tests**

Run: `conda run -n rag_env python -m pytest tests/test_query_bank_builder.py -q`

Expected: PASS.

### Task 3: Verify repair recovery and resume execution

**Files:**
- Test: `tests/test_query_bank_repair.py`
- Run: `scripts/query_bank/repair_ia_query_bank.py`

- [ ] **Step 1: Run all Query Bank tests**

Run: `conda run -n rag_env python -m pytest tests/test_query_bank_builder.py tests/test_query_bank_repair.py tests/test_query_bank.py tests/test_query_bank_scripts.py -q`

Expected: PASS.

- [ ] **Step 2: Start exactly one real-time repair worker**

Run: `conda run --no-capture-output -n MIAGuard python -u scripts/query_bank/repair_ia_query_bank.py --bank-id ag_news_queries_v1 --dataset ag_news --attack-config configs/attacks/ag_news_calibrated_int8.yaml --project-root . --seed 20260813`

- [ ] **Step 3: Verify the worker resumes `ag_news_teacher_00000027` from its saved four `yes` records**

Read: `data/query_banks/ag_news_queries_v1/ag_news/.work/ia_repair_progress.jsonl` and the new worker log.

Expected: pending document remains `ag_news_teacher_00000027`, completed answers contain `yes`, and generated `no` candidates are independently verified before acceptance.
