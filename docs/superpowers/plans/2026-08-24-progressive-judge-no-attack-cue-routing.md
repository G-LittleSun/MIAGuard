# Progressive Judge No-Attack-Cue Routing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a validated router outcome for ordinary queries with no observable attack cue without weakening explicit-benign or review rules.

**Architecture:** Extend the existing screening protocol and parser with `SKIP_NO_ATTACK_CUE`, empty candidates, and empty observed features. Provide mechanically derived surface observations to prevent references to a report from being mistaken for supplied source text, while preserving the downstream pipeline and distinct trace status.

**Tech Stack:** Python 3, pytest, YAML configuration, existing `ProgressiveJudge` pipeline.

---

### Task 1: Lock parser semantics with failing tests

**Files:**
- Modify: `tests/test_progressive_judge.py`
- Test: `tests/test_progressive_judge.py`

- [x] Add a test that calls `parse_screening` with `SKIP_NO_ATTACK_CUE`, no candidates, and no observed features, then asserts the result is accepted.
- [x] Add parameterized invalid cases for a non-empty candidate list or non-empty observed features.
- [x] Run the focused tests and verify they fail because the new decision and code are not yet supported.

### Task 2: Implement the minimal router extension

**Files:**
- Modify: `src/miaguard/progressive_judge.py`
- Test: `tests/test_progressive_judge.py`

- [x] Add trusted mechanical surface observations to `build_screening_prompt` and distinguish report references from supplied source text.
- [x] Update `_ROUTER_PROTOCOL` and `build_screening_prompt` to describe all three outcomes and require `REVIEW` for ambiguous or suspicious input.
- [x] Update `parse_screening` to accept `SKIP_NO_ATTACK_CUE` only with empty candidates and empty observed features.
- [x] Run the parser tests and verify they pass while existing routing tests stay green.

### Task 3: Preserve downstream scoring and distinguish status

**Files:**
- Modify: `tests/test_progressive_judge.py`
- Modify: `src/miaguard/progressive_judge.py`
- Modify: `tests/test_query_bank_judge_benchmark.py`
- Modify: `src/miaguard/query_bank/judge_benchmark.py`

- [x] Add a failing end-to-end unit test asserting that `SKIP_NO_ATTACK_CUE` skips detail, records `skipped_no_attack_cue`, and still calls both scoring heads.
- [x] Replace the shared skip status assignment with a decision-to-status mapping.
- [x] Extend benchmark shard validation so the new strict routing schema can be written and resumed.
- [x] Run the focused Progressive Judge tests and verify all pass.

### Task 4: Version configuration and documentation

**Files:**
- Modify: `configs/defense/progressive_judge_v2.yaml`
- Modify: `configs/defense/progressive_judge_v2_qwen2_5_7b.yaml`
- Modify: `docs/PROGRESSIVE_JUDGE_V2_EXPERIMENT_ZH.md`
- Modify: `docs/superpowers/specs/2026-08-23-progressive-judge-v2-design.md`

- [x] Append `_no_attack_cue` to both prompt versions and the test default.
- [x] Document the three-way router and the high-recall safety boundary.
- [x] Run configuration tests and verify both model configs share the new prompt version.

### Task 5: Verify and rerun paired experiment

**Files:**
- No source changes expected.

- [x] Run the focused test files, then the complete test suite.
- [x] Run Python compilation checks for modified Python files.
- [x] Start a new paired Qwen BF16 experiment in a new output directory because the prompt identity changed.
- [x] Inspect logs and outputs for completion, malformed JSON, wrong skips, and score availability.
- [x] Summarize attack and benign results, explicitly reporting attack wrong-skip behavior.
