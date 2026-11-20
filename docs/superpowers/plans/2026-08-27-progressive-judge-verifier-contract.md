# Progressive Judge Verifier Contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent invalid Verifier evidence combinations and make the full progressive-Judge benchmark restartable with one consistent scoring version.

**Architecture:** Replace the combined evidence response with one constrained response per selected candidate. Attack cards provide a closed missing-condition vocabulary; the Judge composes individually parsed assessments into the existing EvidencePacket so downstream scoring stays unchanged.

**Tech Stack:** Python 3.10, pytest, JSON Schema, lm-format-enforcer, Transformers.

---

### Task 1: Define closed missing-condition vocabularies

**Files:**
- Modify: `attack_pattern_library/patterns/direct_rag_mia/PATTERN.md`
- Modify: `attack_pattern_library/patterns/s2_mia/PATTERN.md`
- Modify: `attack_pattern_library/patterns/masked_mia/PATTERN.md`
- Modify: `attack_pattern_library/patterns/ia/PATTERN.md`
- Modify: `tests/test_progressive_judge.py`

- [ ] **Step 1: Write failing parser test**

```python
def test_parse_evidence_rejects_missing_code_outside_candidate_vocabulary() -> None:
    with pytest.raises(ValueError, match="unknown missing condition code"):
        parse_evidence_assessment(
            {"attack_type": "s2_mia", "verdict": "POSSIBLE", ...
             "missing_condition_codes": ["INVENTED_CODE"]},
            candidate_attack_type="s2_mia", library=library,
        )
```

- [ ] **Step 2: Run the test and verify it fails because the new parser is absent.**

- [ ] **Step 3: Add `# Missing condition codes` sections to every attack card and implement the parser helper that reads them.**

- [ ] **Step 4: Run the focused test and verify it passes.**

### Task 2: Constrain one-candidate Verifier outputs

**Files:**
- Modify: `src/miaguard/progressive_judge.py`
- Modify: `tests/test_progressive_judge.py`

- [ ] **Step 1: Write failing schema tests for the invalid S2 combination and legal POSSIBLE/UNLIKELY combinations.**

```python
with pytest.raises(ValidationError):
    validate({"attack_type": "s2_mia", "verdict": "POSSIBLE",
              "required_conditions_met": False, "exclusion_applies": False,
              "missing_condition_codes": [], ...}, evidence_assessment_json_schema(...))
```

- [ ] **Step 2: Run those tests and verify they fail because the schema helper is absent.**

- [ ] **Step 3: Implement the single-candidate prompt, schema and assessment parser.**

- [ ] **Step 4: Run focused schema/parser tests and verify they pass.**

### Task 3: Compose independent assessments in the Judge

**Files:**
- Modify: `src/miaguard/progressive_judge.py`
- Modify: `tests/test_progressive_judge.py`

- [ ] **Step 1: Write failing trace test asserting two candidates cause two single-candidate verifier calls and preserve candidate order.**
- [ ] **Step 2: Run it and verify it fails against the combined verifier path.**
- [ ] **Step 3: Replace the combined detailed-review call with an ordered loop of constrained single-candidate calls, then create EvidencePacket from returned assessments.**
- [ ] **Step 4: Run focused Judge tests and verify they pass.**

### Task 4: Version, validate and rerun

**Files:**
- Modify: `attack_pattern_library/manifest.yaml`
- Modify: `configs/defense/progressive_judge_v2.yaml`
- Modify: `configs/defense/progressive_judge_v2_qwen2_5_7b.yaml`
- Modify: `tests/test_attack_pattern_library.py`

- [ ] **Step 1: Bump the pattern-library and Judge prompt versions; update expected-version tests.**
- [ ] **Step 2: Run all tests with `D:\\ProgramData\\Anaconda3\\envs\\MIAGuard\\python.exe -m pytest -q`.**
- [ ] **Step 3: Run the actual failing S2 session as a smoke test in a fresh output directory.**
- [ ] **Step 4: If smoke completes, start a fresh full development benchmark in a new output directory and retain the earlier 519-session run only as diagnostic output.**
