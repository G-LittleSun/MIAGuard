# AG News v2 Judge Score Fusion Training Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Train and compare train-only, document-grouped binary fusion classifiers for the two frozen Judge score heads, select thresholds from OOF predictions, and export publication-quality diagnostic figures.

**Architecture:** Stage B consumes only the verified v2 Stage A parquet table. It trains each head independently and writes one self-contained artifact directory containing OOF predictions, model/threshold reports, figures, and an input-hash manifest. The primary model is L2 logistic regression over x1/x2; a fixed interaction model and shallow ReLU MLP are sensitivity comparisons.

**Tech Stack:** Python 3.10, pandas, NumPy, scikit-learn, SciPy, Matplotlib, PyArrow, pytest.

---

### Task 1: Define and test deterministic fusion primitives

**Files:**
- Create: `src/miaguard/judge_score_fusion.py`
- Create: `tests/test_judge_score_fusion.py`

- [ ] Add failing tests for document-grouped folds, attack-type-balanced fold-local weights, available-x2 filtering, and constrained threshold selection.
- [ ] Verify each test fails because the fusion module does not exist.
- [ ] Implement the smallest pure functions needed to satisfy the tests.
- [ ] Run the focused tests.

### Task 2: Add grouped-OOF models and reporting

**Files:**
- Modify: `src/miaguard/judge_score_fusion.py`
- Modify: `tests/test_judge_score_fusion.py`

- [ ] Add failing tests that require all predefined models and both score heads to emit one OOF score per eligible row, without group overlap.
- [ ] Implement L2 logistic baselines, legacy weighted score, x1+x2 logistic regression, interaction logistic regression, and fixed 2→8→1 ReLU MLP.
- [ ] Add ROC/PR/calibration metrics, 1/2/5/10% FPR threshold selection, and document-level bootstrap intervals.
- [ ] Run focused tests.

### Task 3: Add reproducible Stage B workflow and figures

**Files:**
- Modify: `src/miaguard/query_bank/judge_score_workflow.py`
- Create: `scripts/train_judge_score_fusion.py`
- Modify: `tests/test_judge_score_workflow.py`

- [ ] Add failing workflow tests for Stage-A provenance checks, train-only enforcement, non-overwriting output, and required artifacts.
- [ ] Implement the artifact workflow and run manifest.
- [ ] Render fixed-style ROC, PR, calibration, decision-surface, and attack-type recall figures.
- [ ] Run focused workflow tests.

### Task 4: Execute and verify v2 train-only experiment

**Files:**
- Create: `data/judge_score_fusion_v2_20260903/train/` (generated artifacts)

- [ ] Run the focused unit tests and then the full test suite.
- [ ] Execute Stage B only on `data/judge_score_analysis_v2_20260902/train`.
- [ ] Inspect generated figures and verify the manifest, counts, score ranges, and threshold constraints.
- [ ] Report results without training on or inspecting validation/test scores.
