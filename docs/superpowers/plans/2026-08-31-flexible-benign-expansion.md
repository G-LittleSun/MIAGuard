# Flexible Benign Expansion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace fixed per-category benign quotas with a five-query floor, a twenty-query soft target, and optional hard-benign additions.

**Architecture:** Retain the five validated v1 benign records for every document, generate additional ordinary questions as best-effort candidates, and only require the retained floor. The manifest stores the flexible policy; validation and session planning consume that policy instead of assuming a 20:5 layout.

**Tech Stack:** Python 3, pytest, YAML query-bank configuration.

---

### Task 1: Flexible generation policy

**Files:** `tests/test_benign_query_bank_expansion.py`, `src/miaguard/query_bank/benign_expansion.py`

- [ ] Write failing tests showing the five retained parent queries complete a build when supplemental candidates fail, and accepted supplemental candidates are retained without a category quota.
- [ ] Run `conda run -n MIAGuard python -m pytest tests/test_benign_query_bank_expansion.py -q` and observe the expected failures.
- [ ] Implement retained parent benign rows, best-effort standard generation to a soft target, and optional hard generation.
- [ ] Re-run the focused tests.

### Task 2: Downstream policy changes

**Files:** `src/miaguard/query_bank/validator.py`, `src/miaguard/query_bank/sessions.py`, `tests/test_benign_query_bank_expansion.py`

- [ ] Write failing tests for validating six benign rows and grouping flexible benign traffic with the generic 3--5 turn session planner.
- [ ] Run the focused tests and observe the expected failures.
- [ ] Require a benign floor instead of an exact count and remove fixed 4+1 session construction.
- [ ] Re-run the focused tests.

### Task 3: Configuration and run

**Files:** `configs/query_banks/ag_news_v2_benign_expansion.yaml`, `docs/superpowers/specs/2026-08-30-ag-news-query-bank-v2-benign-expansion-design.md`

- [ ] Configure floor=5, soft target=20, optional hard=2, then run all Query Bank tests.
- [ ] Start a clean v2 build; validate the output Query Bank and the complete session plan after it finishes.
