# Progressive Judge v3 Binary Logprob Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an immutable v3 binary-logprob Judge contract and produce grouped OOF reports at 1% and 5% benign-FPR constraints.

**Architecture:** Keep the progressive evidence pipeline and rubric head intact. A v3 config selects two semantic labels; `ProgressiveJudge` derives the normalized attack probability directly from them. Existing score analysis/fusion remains head-agnostic, with the v3 workflow publishing the two required operating points and provenance.

**Tech Stack:** Python 3.10+, Pytest, pandas, NumPy, scikit-learn, YAML.

---

### Task 1: Versioned binary Judge configuration

**Files:**
- Create: `configs/defense/progressive_judge_v3_binary_logprob.yaml`
- Create: `configs/defense/progressive_judge_v3_binary_logprob_qwen2_5_7b.yaml`
- Modify: `tests/test_progressive_judge.py`

- [x] Write tests that load v3, assert `("BENIGN", "ATTACK")`, and assert v2 still loads `("A", "B", "C")`.
- [x] Run the focused tests and observe the v3-config test fail because the files/config validation do not support two labels.
- [x] Implement the two immutable YAML configs and version their prompt identity.
- [x] Run the focused test command and observe PASS.

### Task 2: Binary conditional scoring contract

**Files:**
- Modify: `src/miaguard/progressive_judge.py`
- Modify: `tests/test_progressive_judge.py`

- [x] Write a failing test whose v3 client returns `{BENIGN: 0.2, ATTACK: 0.8}` and expects score `0.8`, two requested labels, and a prompt that defines strict `ATTACK` evidence.
- [x] Run that focused test and observe failure under the three-label-only config/parser.
- [x] Generalize config validation and `LogprobScore` to a label-to-score mapping; preserve three-label anchor scoring for v2 and use the normalized ATTACK probability for v3.
- [x] Make the early-session synthetic trace use the configured benign score, for either contract.
- [x] Run the focused Judge tests and observe PASS.

### Task 3: Pre-registered two-point OOF reporting

**Files:**
- Modify: `src/miaguard/judge_score_fusion.py`
- Modify: `tests/test_judge_score_fusion.py`
- Modify: `tests/test_judge_score_workflow.py`

- [x] Write a failing test asserting fusion reports only the 0.01 and 0.05 FPR constraints and records each threshold's macro and weakest attack recall.
- [x] Run focused fusion tests and observe the expected assertion failure.
- [x] Replace the unconstrained/default operating-point list with the pre-registered pair, preserving document-grouped folds and bootstrap behavior.
- [x] Run the focused fusion test command and observe PASS.

### Task 4: v3 reproducibility documentation and regression verification

**Files:**
- Create: `docs/PROGRESSIVE_JUDGE_V3_BINARY_LOGPROB_EXPERIMENT_ZH.md`
- Modify: `README.md` only if it contains the Judge experiment entry point.

- [x] Document frozen-train generation, analysis, OOF fusion, the required human review gate, and later locked validation without giving test data to selection.
- [x] Run the full project test suite and observe PASS.
- [x] Run `conda run -n MIAGuard python -m compileall -q src scripts` and observe exit code 0.
