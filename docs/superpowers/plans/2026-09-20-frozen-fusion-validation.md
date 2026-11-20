# Frozen Fusion Validation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement task-by-task.

**Goal:** Persist the train-selected logistic fusion model and evaluate it unchanged on validation.

**Architecture:** JSON stores the fitted logistic parameters and thresholds. Validation reconstructs scores from `x1,x2`, never calls model fitting or threshold selection.

**Tech Stack:** Python, NumPy, pandas, scikit-learn, Pytest.

---

### Task 1: Frozen model and locked evaluator

**Files:**
- Create: `src/miaguard/judge_score_frozen.py`
- Create: `tests/test_judge_score_frozen.py`
- Create: `scripts/validate_judge_score_fusion.py`

- [ ] Write tests for train fitting, fixed-threshold validation, and rejection of a non-validation source.
- [ ] Run the focused test and observe import failure.
- [ ] Implement JSON freeze/evaluation functions and the CLI.
- [ ] Run focused tests and the existing score-workflow tests.
