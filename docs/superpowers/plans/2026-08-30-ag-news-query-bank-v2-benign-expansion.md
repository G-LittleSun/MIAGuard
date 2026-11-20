# AG News Query Bank v2 Benign Expansion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a frozen `ag_news_queries_v2` from the complete v1 bank while preserving every non-benign record and replacing each document's five benign records with 20 standard and five explicitly audited hard-benign queries.

**Architecture:** Add a narrowly scoped benign-expansion module and command that loads v1, copies non-benign records without mutation, generates and independently verifies benign queries by document/category/difficulty slot, then freezes a self-describing v2 manifest. Extend record/document/session/split validation only where the v2 schema requires it; v1 remains valid and byte-stable. The v2 split derives the v1 document assignments but binds the new v2 query hash.

**Tech Stack:** Python 3.10, PyYAML, existing `ModelClient`, JSONL storage, pytest, existing query-bank schemas and session planner.

---

## File Structure

- Create: `configs/query_banks/ag_news_v2_benign_expansion.yaml` — immutable v2 construction parameters: parent bank, model/attack config, 20:5 quota, seed, retry limit, audit rates and scenarios.
- Create: `src/miaguard/query_bank/benign_expansion.py` — configuration loader, generation/verifier prompts, slot retry loop, v1-copy/v2-freeze workflow, audit sampling and manifest construction.
- Create: `scripts/query_bank/expand_benign_query_bank.py` — explicit command-line entry point for creating v2 without altering v1.
- Modify: `src/miaguard/query_bank/schema.py` — validate optional v2 benign audit fields while retaining v1’s minimal benign payload.
- Modify: `src/miaguard/query_bank/validator.py` — validate 25-query v2 benign quotas and report difficulty counts when a bank declares the v2 benign policy.
- Modify: `src/miaguard/query_bank/sessions.py` — deterministically turn 25 v2 benign records into five sessions of four standard plus one hard query; preserve prior planning for all other traffic.
- Modify: `src/miaguard/query_bank/threshold_split.py` — derive a fresh v2 split from an existing valid parent split, preserving doc assignments and rebinding source metadata.
- Modify: `src/miaguard/query_bank/__init__.py` — expose the expansion workflow’s public configuration and builder entry point.
- Modify: `tests/test_query_bank.py` — cover v2 benign record schema and per-document quota validation.
- Modify: `tests/test_query_bank_sessions.py` — cover deterministic 4-standard/1-hard v2 benign sessions and hard position balancing.
- Modify: `tests/test_query_bank_threshold_split.py` — cover v1-assignment-preserving v2 split derivation.
- Modify: `tests/test_query_bank_scripts.py` — make the new expansion command part of the command-help contract.
- Create: `tests/test_benign_query_bank_expansion.py` — cover copy invariance, slot acceptance/retry rules, audit sampling and output manifest with a deterministic fake model client.

### Task 1: Lock the v2 benign record contract

**Files:**
- Modify: `src/miaguard/query_bank/schema.py`
- Modify: `src/miaguard/query_bank/validator.py`
- Modify: `tests/test_query_bank.py`

- [ ] **Step 1: Write failing schema tests**

Add a v2 benign fixture whose payload includes `difficulty`, `hard_scenario`, and `benign_intent`, then assert that one `standard` row with `hard_scenario=None` and one `hard` row with `hard_scenario="quoted_context_interpretation"` are accepted. Add rejection tests for a hard row without scenario, a standard row with scenario, and an unknown scenario.

```python
def test_v2_benign_payload_requires_consistent_difficulty_metadata() -> None:
    hard = _record("doc-1", 1, "benign", "generated", 1, category="topic")
    hard["payload"].update({
        "difficulty": "hard",
        "hard_scenario": "quoted_context_interpretation",
        "benign_intent": "ordinary information-seeking intent",
    })
    validate_query_record(hard)
```

- [ ] **Step 2: Run the schema tests and confirm they fail for missing v2 validation**

Run: `conda run -n MIAGuard pytest tests/test_query_bank.py -k v2_benign -v`

Expected: FAIL because the intended validation behavior does not exist.

- [ ] **Step 3: Add minimal schema constants and validation**

In `schema.py`, define the fixed `HARD_BENIGN_SCENARIOS` tuple. When any v2 audit key is present, require all three audit keys; enforce `difficulty in {"standard", "hard"}`, nonempty `benign_intent`, null scenario for standard, and one approved scenario for hard. Do not require audit keys for v1 benign records.

- [ ] **Step 4: Add the failing document-quota test**

Create 25 benign rows for one document with exactly four standard and one hard row per existing category. Call `validate_document_records(..., benign_policy={"standard_per_category": 4, "hard_per_category": 1})`; assert it accepts the rows and returns `benign_difficulty_counts == {"hard": 5, "standard": 20}`. Alter one hard row to standard and assert rejection.

- [ ] **Step 5: Implement policy-aware document validation**

Give `validate_document_records` a keyword-only optional `benign_policy: Mapping[str, int] | None = None`. Keep the exact old count requirement when it is `None`; otherwise require exactly `(standard_per_category + hard_per_category) × len(BENIGN_CATEGORIES)` benign rows, every category’s difficulty counter exactly equals the policy, and normalized benign `query_text` values are unique. Return the difficulty counts for audit use.

- [ ] **Step 6: Run focused tests**

Run: `conda run -n MIAGuard pytest tests/test_query_bank.py -k "v2_benign or document_validation" -v`

Expected: PASS.

### Task 2: Make v2 benign session planning causal and reproducible

**Files:**
- Modify: `src/miaguard/query_bank/sessions.py`
- Modify: `tests/test_query_bank_sessions.py`

- [ ] **Step 1: Write a failing v2 session-layout test**

Create 25 accepted v2 benign records with the v2 payload fields and a bank manifest containing `benign_policy`. Plan its train sessions twice. Assert five 5-turn benign sessions; each has `Counter(payload["difficulty"]) == {"standard": 4, "hard": 1}`, every query is used once, and the two plans match exactly.

- [ ] **Step 2: Run the focused test and confirm failure**

Run: `conda run -n MIAGuard pytest tests/test_query_bank_sessions.py -k v2_benign -v`

Expected: FAIL because generic query-index chunks do not guarantee the 4:1 layout.

- [ ] **Step 3: Implement a dedicated benign-session planner**

Add a private helper that detects `bank.manifest["benign_policy"]`. For each benign document, sort standard queries by category then index, place four standards in each of five sessions, sort hard queries by category then index, and insert one hard query at positions generated by a SHA256 seed of `bank.manifest["seed"]`, document ID, and session index. Ensure the five positions are a deterministic permutation of positions 0–4. Leave non-v2 and non-benign logic untouched.

- [ ] **Step 4: Add rejection coverage**

Assert a v2-marked bank with 24 benign records, or a session layout that cannot allocate five hard rows, raises a `ValueError` naming the deficient benign quota.

- [ ] **Step 5: Run session tests**

Run: `conda run -n MIAGuard pytest tests/test_query_bank_sessions.py -v`

Expected: PASS.

### Task 3: Derive the v2 split without re-randomizing documents

**Files:**
- Modify: `src/miaguard/query_bank/threshold_split.py`
- Modify: `tests/test_query_bank_threshold_split.py`

- [ ] **Step 1: Write a failing derivation test**

Build a valid v1-style split and a v2-style bank with the same documents but a different hash. Call `derive_threshold_split_from_parent(v2_bank, parent_split, split_id="ag-news-threshold-v2")`; assert the `doc_ids`, member lists and nonmember lists are byte-for-byte equal to v1 while `query_bank` contains v2 identity and accepted query counts are recalculated.

- [ ] **Step 2: Run the test and confirm failure**

Run: `conda run -n MIAGuard pytest tests/test_query_bank_threshold_split.py -k derive -v`

Expected: FAIL because the derivation function is absent.

- [ ] **Step 3: Implement split derivation**

Add `derive_threshold_split_from_parent`. Validate the parent’s partition structure against the v2 bank document labels, preserve only its document assignments, recompute per-partition accepted query counts from v2, and emit schema version 1 with fields `split_id`, `seed`, `assignment_unit`, `query_bank`, `derived_from_split_id`, and `parent_query_bank`. Call `validate_threshold_split` before returning.

- [ ] **Step 4: Add mismatch rejection test**

Assert that a parent split which references a document missing from v2 raises a clear `ValueError` and cannot produce an output.

- [ ] **Step 5: Run split tests**

Run: `conda run -n MIAGuard pytest tests/test_query_bank_threshold_split.py -v`

Expected: PASS.

### Task 4: Implement the parent-preserving benign expansion workflow

**Files:**
- Create: `src/miaguard/query_bank/benign_expansion.py`
- Create: `tests/test_benign_query_bank_expansion.py`
- Modify: `src/miaguard/query_bank/__init__.py`

- [ ] **Step 1: Write the failing pure-workflow tests**

Write tests around dependency-injected generation and verification callables:

```python
def test_expansion_copies_nonbenign_records_and_replaces_only_benign(tmp_path: Path) -> None:
    result = expand_benign_query_bank(
        project_root=tmp_path,
        bank_id="ag_news_queries_v2",
        dataset_id="ag_news",
        config=_config(),
        generator=_generator_returning_valid_slots,
        verifier=_verifier_accepting_all,
    )
    assert result["attack_records_sha256"] == _source_attack_digest(tmp_path)
```

Also test that a duplicate candidate is rejected then the same slot is retried, that an invalid verifier response consumes an attempt, and that exhausted attempts fail the whole build without a complete manifest.

- [ ] **Step 2: Run the new workflow tests and confirm failure**

Run: `conda run -n MIAGuard pytest tests/test_benign_query_bank_expansion.py -v`

Expected: FAIL because the module is absent.

- [ ] **Step 3: Add immutable expansion configuration**

Define frozen `BenignExpansionConfig` with: `parent_bank_id`, `parent_split_path`, `attack_config_path`, `seed`, `standard_per_category=4`, `hard_per_category=1`, `max_attempts_per_slot`, `audit_seed`, `hard_audit_fraction=0.20`, `standard_audit_fraction=0.05`, and `hard_scenarios`. Add a YAML loader that rejects any quota or category/scenario set differing from the approved v2 specification.

- [ ] **Step 4: Implement generation, verification and slot retries**

For each `(document, category, difficulty, ordinal)` slot, issue a generation prompt that contains only the document text plus category/difficulty requirements. Independently issue a verifier prompt with document text, candidate text, category/difficulty/scenario and policy requirements; it returns compact JSON containing `accepted`, `reason_code`, and `observed_scenario`. Reject blank/normalized duplicate/attack-intent candidates locally before verifier acceptance. On acceptance, produce a `builder._record` compatible benign record with stable index 1–25, audit metadata, model provenance, and only normal `query_text` as the runnable query.

- [ ] **Step 5: Implement the freeze workflow and audit output**

Load the complete v1 `QueryBank`; reject wrong parent identity or an existing v2 manifest. For every v1 document, copy its non-benign dicts unchanged into a new shard and append 25 accepted generated benign rows. Validate each document with the v2 policy, compact records, verify canonical JSON equality of parent/v2 non-benign records, derive/freeze the new split, and write an immutable manifest including parent SHA, source attack SHA, model settings, quotas, verifier version, audit seed/rates, audit sample counts, and new query SHA. Write `benign_audit_sample.jsonl` containing deterministic samples with `review_status: "pending"`; do not claim manual review has occurred.

- [ ] **Step 6: Run focused workflow tests**

Run: `conda run -n MIAGuard pytest tests/test_benign_query_bank_expansion.py tests/test_query_bank.py -k "expansion or v2_benign" -v`

Expected: PASS.

### Task 5: Add the explicit v2 config and safe command interface

**Files:**
- Create: `configs/query_banks/ag_news_v2_benign_expansion.yaml`
- Create: `scripts/query_bank/expand_benign_query_bank.py`
- Modify: `tests/test_query_bank_scripts.py`

- [ ] **Step 1: Write the failing command-help test**

Add `scripts/query_bank/expand_benign_query_bank.py` to `test_query_bank_script_help`.

- [ ] **Step 2: Run it and confirm failure**

Run: `conda run -n MIAGuard pytest tests/test_query_bank_scripts.py -k script_help -v`

Expected: FAIL because the command does not exist.

- [ ] **Step 3: Create the immutable config**

Set `parent_bank_id: ag_news_queries_v1`, `parent_split_path: data/query_bank_splits/ag_news_threshold_v1.json`, `attack_config: configs/attacks/ag_news_calibrated_int8.yaml`, seed values, 4 standard/1 hard quotas, fixed scenario list, a bounded retry count, and 0.20/0.05 audit fractions. Keep the v1 source-run/dataset identity in config so the command can reject accidental cross-dataset construction.

- [ ] **Step 4: Implement the command**

Require `--config`, `--bank-id`, `--dataset`, `--project-root`, `--split-id`, and `--split-output`. Load config, call `expand_benign_query_bank`, print only its JSON result, and never expose a force-overwrite flag. Existing v2 output must cause a clear failure rather than mutation.

- [ ] **Step 5: Run script contract tests**

Run: `conda run -n MIAGuard pytest tests/test_query_bank_scripts.py -k script_help -v`

Expected: PASS.

### Task 6: Verify the implementation and execute the frozen v2 build

**Files:**
- Modify: `docs/superpowers/specs/2026-08-30-ag-news-query-bank-v2-benign-expansion-design.md` — append the actual reproducible invocation and generated artifact locations after successful build.

- [ ] **Step 1: Run the complete test suite**

Run: `conda run -n MIAGuard pytest -q`

Expected: all existing and new tests pass; existing non-fatal baseline warnings may remain documented.

- [ ] **Step 2: Verify source v1 and destination absence**

Run: `conda run -n MIAGuard python scripts/query_bank/validate_query_bank.py --bank-id ag_news_queries_v1 --dataset ag_news --project-root .`

Expected: v1 validates successfully. Confirm `data/query_banks/ag_news_queries_v2/ag_news/manifest.json` and `data/query_bank_splits/ag_news_threshold_v2.json` do not exist before starting.

- [ ] **Step 3: Execute the v2 expansion once**

Run: `conda run -n MIAGuard python scripts/query_bank/expand_benign_query_bank.py --config configs/query_banks/ag_news_v2_benign_expansion.yaml --bank-id ag_news_queries_v2 --dataset ag_news --project-root . --split-id ag_news_threshold_v2 --split-output data/query_bank_splits/ag_news_threshold_v2.json`

Expected: a complete manifest, a v2-bound split, 25 benign queries per document, unchanged attack digest, and pending audit sample records.

- [ ] **Step 4: Independently validate bank, split and session layout**

Run:

```powershell
conda run -n MIAGuard python scripts/query_bank/validate_query_bank.py --bank-id ag_news_queries_v2 --dataset ag_news --project-root .
conda run -n MIAGuard python scripts/audit_query_bank_threshold_sessions.py --bank-id ag_news_queries_v2 --dataset ag_news --split data/query_bank_splits/ag_news_threshold_v2.json --project-root . --output data/query_banks/ag_news_queries_v2/ag_news/session_audit.json
```

Expected: no missing/duplicate query IDs, all benign sessions have five turns, and the session audit reports the v2 benign 4:1 layout.

- [ ] **Step 5: Append reproducibility details to the approved design**

Record the exact command, v2 query SHA, split path, manifest path, audit-sample path, and that review status is `pending`; do not mark human auditing complete until a human has performed it.

## Self-review

- Spec coverage: Tasks 1–2 implement v2 record/quota/session requirements; Task 3 binds an independently frozen v2 split while preserving document assignments; Task 4 provides copy invariance, generation, verification, retries, manifest and pending audit; Task 5 prevents unsafe CLI overwrite; Task 6 runs the required frozen build and independent validations.
- Placeholder scan: no `TODO`, `TBD`, or unspecified implementation/testing steps remain.
- Type consistency: `BenignExpansionConfig`, `expand_benign_query_bank`, `derive_threshold_split_from_parent`, and `benign_policy` use the same names throughout.
