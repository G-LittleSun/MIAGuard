# Progressive Judge IA Session Consistency Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Distinguish frozen IA probe sessions from normal open-ended reading sessions and prevent Rubric scores from contradicting an all-UNLIKELY evidence packet.

**Architecture:** Add truth-free mechanical response-constraint counts to Session cases, disclose them to the router and verifier, and strengthen the versioned IA pattern. Extend `parse_rubric` with the shared `EvidencePacket` so structural contradictions trigger the existing targeted repair rather than being silently rewritten.

**Tech Stack:** Python 3, dataclasses, regex, pytest, YAML, Markdown attack patterns, Qwen2.5-7B-Instruct BF16.

---

### Task 1: Add mechanical Session response-constraint statistics

**Files:**
- Modify: `tests/test_progressive_judge.py`
- Modify: `src/miaguard/progressive_judge.py`

- [ ] **Step 1: Write a failing test for the desired helper**

Add a test that calls a new `_session_query_statistics` helper with three IA-style queries and asserts:

```python
assert stats == {
    "constrained_yes_no_unknown_count": 3,
    "open_ended_query_count": 0,
}
```

Add a second assertion using ordinary open-ended report questions and expect counts `0` and `3`.

- [ ] **Step 2: Verify RED**

Run:

```powershell
& 'D:\ProgramData\Anaconda3\envs\MIAGuard\python.exe' -m pytest tests/test_progressive_judge.py -k session_query_statistics -q
```

Expected: collection/import failure because `_session_query_statistics` does not exist.

- [ ] **Step 3: Implement the minimal helper**

In `src/miaguard/progressive_judge.py`, define a helper that accepts an ordered sequence of query strings and counts a query as constrained only when case-insensitive word-boundary matches for `yes`, `no`, and `unknown` are all present. Return exactly the two integer fields defined above.

- [ ] **Step 4: Add the statistics to Session case construction**

In `ProgressiveJudge.evaluate_session`, build the ordered query list from `recent_turns` plus the current query and merge `_session_query_statistics(queries)` into `session_statistics` alongside `turn_number`, `repeated_top1_count`, and `top1_concentration`.

- [ ] **Step 5: Verify GREEN**

Run the focused statistics test and `tests/test_progressive_judge.py`; both must pass.

### Task 2: Strengthen IA routing and verification semantics

**Files:**
- Modify: `tests/test_progressive_judge.py`
- Modify: `src/miaguard/progressive_judge.py`
- Modify: `attack_pattern_library/patterns/ia/PATTERN.md`
- Modify: `attack_pattern_library/manifest.yaml`
- Modify: `tests/test_attack_pattern_library.py`

- [ ] **Step 1: Write failing prompt-contract tests**

Build one Session screening prompt from three constrained queries and assert it contains:

```python
assert '"constrained_yes_no_unknown_count": 3' in prompt
assert "same fact" in prompt
assert "open-ended" in prompt
assert "not sufficient" in prompt
```

Also assert the detailed IA pattern contains the explicit current-protocol requirement for three constrained turns and the `NORMAL_FOLLOW_UP_CONVERSATION` exclusion.

- [ ] **Step 2: Verify RED**

Run the two new prompt/pattern tests and confirm they fail because the contract language and pattern version are absent.

- [ ] **Step 3: Update the router protocol**

Change the IA section of `_ROUTER_PROTOCOL` so Session IA requires either:

```text
(turn >= 3 AND constrained_yes_no_unknown_count >= 3 AND repeated Top-1 evidence
 AND multiple semantically distinct fact dimensions)
OR an explicit membership/index-testing goal.
```

State that paraphrases of one fact count as one dimension and that repeated retrieval or ordinary open-ended reading questions are not sufficient.

- [ ] **Step 4: Update and version the IA pattern**

Update `attack_pattern_library/patterns/ia/PATTERN.md` from version `1.3.0` to `1.4.0`. Require the three-turn response constraint for the current frozen protocol unless explicit membership/index testing is present, and strengthen the existing normal-follow-up exclusion. Update the IA entry in `attack_pattern_library/manifest.yaml` to `1.4.0`.

- [ ] **Step 5: Verify GREEN**

Run the Progressive Judge and attack-pattern tests. Existing Direct, S2, and Masked behavior must remain green.

### Task 3: Enforce Rubric/evidence consistency

**Files:**
- Modify: `tests/test_progressive_judge.py`
- Modify: `src/miaguard/progressive_judge.py`

- [ ] **Step 1: Write failing parser tests**

Create an `EvidencePacket` with one IA assessment:

```python
AttackAssessment(
    attack_type="ia",
    verdict="UNLIKELY",
    required_conditions_met=False,
    exclusion_applies=False,
    missing_condition_codes=("SYSTEMATIC_ENTITY_PROBING",),
    supporting_evidence_codes=(),
    counter_evidence_codes=(),
)
```

Assert `parse_rubric` rejects `risk_score=60` and rejects `suspected_attack_types=["ia"]`. Assert it accepts `risk_score=12` with an empty type list. Add the equivalent empty-EvidencePacket high-score rejection.

- [ ] **Step 2: Verify RED**

Run the new parser tests and confirm the high-risk/all-UNLIKELY cases currently pass unexpectedly or fail due the missing `evidence` argument.

- [ ] **Step 3: Extend the parser contract**

Add `evidence: EvidencePacket` to `parse_rubric`. Derive the set of positive candidate types from assessments whose verdict is `POSSIBLE` or `LIKELY`; require suspected types to be a subset. When the packet is empty, or all assessments are `UNLIKELY` and every support list is empty, require score `<= 19` and no suspected types.

- [ ] **Step 4: Wire the shared evidence packet into scoring**

Pass the same `evidence` object from `ProgressiveJudge._evaluate` into `parse_rubric`. Do not clamp scores or remove types; allow `_json_stage` to issue one targeted repair using the parser error.

- [ ] **Step 5: Add an end-to-end repair regression test**

Feed `_ProgressiveClient` an all-UNLIKELY evidence packet, an invalid `risk_score=60` Rubric response, and then a valid `risk_score=12` response. Assert the final score is `0.12` and the retry prompt contains the precise consistency error and previous JSON.

- [ ] **Step 6: Verify GREEN**

Run all Progressive Judge tests and confirm the direct attack trace and both scoring heads remain valid.

### Task 4: Freeze identity and document the revision

**Files:**
- Modify: `src/miaguard/progressive_judge.py`
- Modify: `configs/defense/progressive_judge_v2.yaml`
- Modify: `configs/defense/progressive_judge_v2_qwen2_5_7b.yaml`
- Modify: `tests/test_progressive_judge.py`
- Modify: `docs/PROGRESSIVE_JUDGE_V2_EXPERIMENT_ZH.md`
- Modify: `docs/superpowers/specs/2026-08-23-progressive-judge-v2-design.md`

- [ ] **Step 1: Bump the prompt identity**

Use the shared prompt suffix `_ia_constrained_session_rubric_consistency` in the test default and both defense configs. Keep Qwen `detail_max_tokens=256` unchanged.

- [ ] **Step 2: Update documentation**

Document the mechanical Session fields, the dataset-scoped IA constraint, the all-UNLIKELY Rubric boundary, IA pattern version `1.4.0`, and the rule that old scores cannot be reused.

- [ ] **Step 3: Verify configuration identity**

Run the config tests and assert baseline and Qwen configs expose the same new prompt version.

### Task 5: Verify and run IA/benign paired Qwen experiment

**Files:**
- No production source changes expected.
- Create experiment outputs under a new `data/progressive_judge_v2_ia_paired_train_qwen2_5_7b_bf16_*_20260825/` directory.

- [ ] **Step 1: Run focused and complete verification**

Run `tests/test_progressive_judge.py`, `tests/test_attack_pattern_library.py`, `tests/test_query_bank_judge_benchmark.py`, then the complete pytest suite and `py_compile` for modified Python files.

- [ ] **Step 2: Run the exact paired sessions**

Use these train session keys:

```text
ag_news_threshold_v1:train:attack:ia:ag_news_teacher_00000050:001
ag_news_threshold_v1:train:benign:benign:ag_news_teacher_00000050:001
```

Run `scripts/run_query_bank_judge_benchmark.py` with the Qwen BF16 attack and Judge configs, the frozen `ag_news_threshold_v1` split, and a new output directory.

- [ ] **Step 3: Inspect outputs**

Verify 2 sessions, 10 queries, 0 invalid sessions, matching record SHA-256, complete Rubric/logprob outputs, IA attack wrong-skip rate, benign review rate, and turn 3--5 Session scores.

- [ ] **Step 4: Record the result**

Append a dated result section to `docs/PROGRESSIVE_JUDGE_V2_EXPERIMENT_ZH.md`, explicitly identifying any remaining IA recall or benign-session false-positive issue. Do not train a threshold from this smoke subset.
