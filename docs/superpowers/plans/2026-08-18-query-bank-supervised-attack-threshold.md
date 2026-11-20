# Query Bank Supervised Attack Threshold Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a reproducible AG News Query Bank workflow that freezes a 60/20/20 document split, constructs uniform 4-5 turn sessions from all 5,956 accepted queries, collects observe-mode risk scores, learns one document-balanced `t_attack`, validates it without reselection, and applies it as an independent access-control threshold.

**Architecture:** Add focused modules for frozen splits, deterministic session planning, offline threshold metrics, and resumable observe-mode scoring. Keep the existing risk detectors and aggregation unchanged. Extend `TwoStageConfig` and `LevelMapper` with an optional independent attack threshold while preserving legacy behavior when the field is absent.

**Tech Stack:** Python 3.10, dataclasses, PyYAML, NumPy, scikit-learn, jsonschema, pytest, existing MIAGuard QueryBank and two-stage gateway APIs.

**Repository note:** `D:\Project\MIAGuard` is not a Git repository. Execute the test and checkpoint steps below, but Git commit commands are intentionally omitted because they cannot succeed in this workspace.

---

## File Structure

- Create `src/miaguard/query_bank_threshold_split.py`: split schema model, builder, loader, validator, freezer.
- Create `src/miaguard/query_bank_sessions.py`: accepted-query filtering, deterministic ordering, balanced 4-5 turn session planning, audit summary.
- Create `src/miaguard/supervised_threshold.py`: document-balanced candidate search, locked-threshold evaluation, query/session metrics.
- Create `src/miaguard/query_bank_threshold_scoring.py`: observe-mode scorer and resumable per-session shards.
- Create `src/miaguard/query_bank_threshold_workflow.py`: calibration, validation, configuration export orchestration.
- Create `schemas/query_bank_threshold_split.schema.json`: frozen split contract.
- Create `scripts/freeze_query_bank_threshold_split.py`: split CLI.
- Create `scripts/run_query_bank_threshold_scoring.py`: partition scoring CLI.
- Create `scripts/calibrate_query_bank_attack_threshold.py`: train-only offline selection CLI.
- Create `scripts/validate_query_bank_attack_threshold.py`: validation-only evaluation and optional config export CLI.
- Create `configs/defense/two_stage_direct_observe_threshold.yaml`: five-turn observe scoring configuration.
- Modify `src/miaguard/access_policy.py`: optional independent attack threshold policy.
- Modify `src/miaguard/two_stage_gateway.py`: parse and pass the optional threshold.
- Modify `configs/defense/two_stage_direct_enforce.yaml`: document the optional field only after validation output exists; do not hard-code an unlearned value.
- Create `tests/test_query_bank_threshold_split.py`.
- Create `tests/test_query_bank_sessions.py`.
- Create `tests/test_supervised_threshold.py`.
- Create `tests/test_query_bank_threshold_scoring.py`.
- Modify `tests/test_access_policy.py`.
- Modify `tests/test_two_stage_gateway.py`.

### Task 1: Frozen Query Bank Split

**Files:**
- Create: `src/miaguard/query_bank_threshold_split.py`
- Create: `schemas/query_bank_threshold_split.schema.json`
- Create: `scripts/freeze_query_bank_threshold_split.py`
- Test: `tests/test_query_bank_threshold_split.py`

- [ ] **Step 1: Write failing split tests**

Create synthetic `QueryBank` data with 50 member and 50 nonmember documents. Test exact 30/10/10 per label counts, disjoint IDs, deterministic output, all documents assigned, query-bank hash retention, overwrite refusal, and rejection when a document has inconsistent membership labels.

```python
def test_build_split_is_balanced_disjoint_and_deterministic(bank):
    first = build_query_bank_threshold_split(bank, split_id="split-v1", seed=17)
    second = build_query_bank_threshold_split(bank, split_id="split-v1", seed=17)
    assert first["partitions"] == second["partitions"]
    assert first["partitions"]["train"]["member_count"] == 30
    assert first["partitions"]["validation"]["member_count"] == 10
    assert first["partitions"]["test"]["member_count"] == 10
    ids = [partition_doc_ids(value) for value in first["partitions"].values()]
    assert ids[0].isdisjoint(ids[1])
    assert ids[0].isdisjoint(ids[2])
    assert ids[1].isdisjoint(ids[2])
    assert set.union(*ids) == {row["doc_id"] for row in bank.documents}
```

- [ ] **Step 2: Run the split tests and verify failure**

Run: `python -m pytest -p no:cacheprovider tests/test_query_bank_threshold_split.py -q`

Expected: collection fails because `miaguard.query_bank_threshold_split` does not exist.

- [ ] **Step 3: Implement the split builder and loader**

Expose these stable interfaces:

```python
PARTITIONS = ("train", "validation", "test")

def build_query_bank_threshold_split(
    bank: QueryBank,
    *,
    split_id: str,
    seed: int,
    counts_per_label: tuple[int, int, int] = (30, 10, 10),
) -> dict[str, Any]: ...

def validate_query_bank_threshold_split(
    manifest: dict[str, Any], bank: QueryBank | None = None
) -> None: ...

def load_query_bank_threshold_split(path: str | Path) -> dict[str, Any]: ...

def freeze_query_bank_threshold_split(
    bank: QueryBank, output: Path, *, split_id: str, seed: int
) -> dict[str, Any]: ...

def partition_doc_ids(
    manifest: dict[str, Any], partition: str
) -> frozenset[str]: ...
```

Use a SHA256-derived per-label seed so Python process hash randomization cannot alter the split. Sort source documents before deterministic shuffling. Validate that each Query Bank document has one stable `membership_label` and that the requested counts consume all 50 documents per label.

- [ ] **Step 4: Add schema and CLI**

The JSON Schema must require `schema_version`, `split_id`, `query_bank_id`, `query_bank_sha256`, `dataset_id`, `seed`, `grouping_unit="doc_id"`, and train/validation/test member and nonmember ID arrays plus counts. The CLI loads `QueryBankPaths`, refuses an existing output, freezes the split, and prints the manifest.

- [ ] **Step 5: Run split tests**

Run: `python -m pytest -p no:cacheprovider tests/test_query_bank_threshold_split.py -q`

Expected: all split tests pass.

### Task 2: Deterministic Full-Query Session Planner

**Files:**
- Create: `src/miaguard/query_bank_sessions.py`
- Test: `tests/test_query_bank_sessions.py`

- [ ] **Step 1: Write failing session-planner tests**

Test one document with five benign queries, five queries for each non-IA attack, and IA counts 30, 31, 38, and 60. Assert that all accepted query IDs appear exactly once, rejected queries never appear, non-IA/benign sessions contain five turns, IA session sizes match `[5] * 6`, `[5,5,5,4,4,4,4]`, `[5,5,5,5,5,5,4,4]`, and `[5] * 12`, and no session mixes a document, attack type, or traffic type.

```python
def test_ia_31_queries_are_balanced_without_loss():
    sessions = plan_group_sessions(records_for("doc-1", "ia", count=31), target_turns=5)
    assert [len(value["queries"]) for value in sessions] == [5, 5, 5, 4, 4, 4, 4]
    assert len({q["query_id"] for s in sessions for q in s["queries"]}) == 31
```

- [ ] **Step 2: Run tests and verify failure**

Run: `python -m pytest -p no:cacheprovider tests/test_query_bank_sessions.py -q`

Expected: module import fails.

- [ ] **Step 3: Implement accepted-query selection and ordering**

Expose:

```python
@dataclass(frozen=True)
class PlannedSession:
    session_key: str
    partition: str
    doc_id: str
    membership_label: int
    traffic_type: str
    attack_type: str
    session_index: int
    queries: tuple[dict[str, Any], ...]

def balanced_session_sizes(count: int, target_turns: int = 5) -> tuple[int, ...]: ...

def plan_partition_sessions(
    bank: QueryBank,
    split: dict[str, Any],
    partition: str,
    *,
    target_turns: int = 5,
) -> tuple[PlannedSession, ...]: ...

def session_plan_summary(sessions: Sequence[PlannedSession]) -> dict[str, Any]: ...
```

Filter only `validation.status == "accepted"`. Order records by variant priority `canonical < paraphrase < generated`, then `query_index`, then `query_id`. For every grouped record list calculate `K = ceil(N / target_turns)`, `base = N // K`, and assign `N % K` leading sessions `base + 1` records. Validate that all current groups produce at least three turns and at most five turns.

- [ ] **Step 4: Add global audit validation**

Verify the plan uses every accepted query whose `doc_id` belongs to the partition exactly once, includes no query from another partition, and keeps stable membership labels. Session keys must include partition, traffic type, attack type, document, and zero-padded session index.

- [ ] **Step 5: Run session tests**

Run: `python -m pytest -p no:cacheprovider tests/test_query_bank_sessions.py -q`

Expected: all session-planner tests pass.

### Task 3: Document-Balanced Threshold Selection and Locked Evaluation

**Files:**
- Create: `src/miaguard/supervised_threshold.py`
- Test: `tests/test_supervised_threshold.py`

- [ ] **Step 1: Write failing threshold tests**

Test that IA documents with 30 and 60 events have equal document weight, all four attack types are required, benign FPR constrains candidates, a nontrivial feasible threshold is selected deterministically, infeasible data returns `status="infeasible"`, and locked validation never searches or changes the input threshold.

```python
def test_document_balancing_prevents_long_ia_document_from_dominating():
    result = select_document_balanced_threshold(records, max_benign_fpr=0.05)
    assert result["status"] == "selected"
    assert result["selected_metrics"]["attack_document_balanced_recall"]["ia"] == pytest.approx(0.5)
```

- [ ] **Step 2: Run tests and verify failure**

Run: `python -m pytest -p no:cacheprovider tests/test_supervised_threshold.py -q`

Expected: module import fails.

- [ ] **Step 3: Implement query and session metrics**

Expose:

```python
def evaluate_locked_attack_threshold(
    records: Sequence[dict[str, Any]], threshold: float, *,
    bootstrap_seed: int = 20260818,
    bootstrap_replicates: int = 2000,
) -> dict[str, Any]: ...

def select_document_balanced_threshold(
    records: Sequence[dict[str, Any]], *, max_benign_fpr: float = 0.05
) -> dict[str, Any]: ...
```

For each attack and document compute mean query detection, then average documents. Compute benign query FPR directly because every document has five benign queries. Session detection is `any(total_risk_score >= threshold)` and first-detection turn is the minimum detected `turn_index`. Report per-attack document-balanced query recall, per-attack session recall, benign query FPR, benign session FPR, precision, recall, F1, balanced accuracy, AUROC, AUPRC, confusion matrix, and first-turn histogram. Bootstrap by resampling document IDs with replacement, never individual queries, using the fixed seed and 2,000 replicates; report percentile 95% intervals for benign query FPR, macro attack recall, minimum attack recall, precision, and F1.

- [ ] **Step 4: Implement candidate ranking and infeasible result**

Candidates are every unique score plus `nextafter(max_score, +inf)`. Feasible candidates satisfy benign query FPR <= the configured bound. Exclude a selected result whose minimum attack document-balanced recall is zero; return `infeasible` with the best diagnostic candidates instead. Rank selected candidates by minimum attack recall, macro attack recall, lower benign FPR, then higher threshold.

- [ ] **Step 5: Run threshold tests**

Run: `python -m pytest -p no:cacheprovider tests/test_supervised_threshold.py -q`

Expected: all threshold tests pass.

### Task 4: Resumable Observe-Mode Risk Scoring

**Files:**
- Create: `src/miaguard/query_bank_threshold_scoring.py`
- Create: `scripts/run_query_bank_threshold_scoring.py`
- Create: `configs/defense/two_stage_direct_observe_threshold.yaml`
- Test: `tests/test_query_bank_threshold_scoring.py`

- [ ] **Step 1: Write failing scorer tests with fake client/store/detectors**

Test that scoring refuses non-observe config, writes only completed session shards, resumes by skipping complete shards, reruns a missing/invalid shard, clears gateway session state after each session, and compacts records in deterministic session/turn order.

```python
def test_resume_skips_complete_session_shard(tmp_path, scorer_fixture):
    first = score_planned_sessions(...)
    second = score_planned_sessions(...)
    assert first["completed_session_count"] == 1
    assert second["skipped_session_count"] == 1
    assert scorer_fixture.guard.calls == expected_first_run_calls
```

- [ ] **Step 2: Run tests and verify failure**

Run: `python -m pytest -p no:cacheprovider tests/test_query_bank_threshold_scoring.py -q`

Expected: module import fails.

- [ ] **Step 3: Implement shard paths, identity manifest, and record construction**

Expose:

```python
@dataclass(frozen=True)
class ThresholdScoringPaths:
    root: Path
    partition: str
    # .work, risk_records.jsonl, run_manifest.json, score_summary.json

def scoring_identity(
    bank: QueryBank,
    split: dict[str, Any],
    partition: str,
    gateway_config: TwoStageConfig,
    scorer_config: DirectScorerConfig,
    pattern_library_version: str,
) -> dict[str, Any]: ...

def score_planned_sessions(
    sessions: Sequence[PlannedSession],
    guard: GuardedRAG,
    gateway: TwoStageGateway,
    paths: ThresholdScoringPaths,
    identity: dict[str, Any],
) -> dict[str, Any]: ...
```

Write one atomic JSONL shard only after an entire session completes. Include `query_id`, document/session/turn fields, labels, three risk scores, risk classes/statuses, retrieved IDs/scores, and detector latency. Clear `gateway.session_store` and the corresponding cached session risk after each complete session through a new public `clear_session(session_id)` method on `TwoStageGateway`.

- [ ] **Step 4: Implement production runner and CLI**

The runner loads QueryBank, frozen split, direct scorer config, observe gateway, model client, vector store, attack pattern library, and planned sessions. It validates identity against an existing run manifest before resuming, writes progress per session, compacts valid shards, and outputs counts/hashes. The five-turn observe config uses `window_size: 5`, `min_session_queries: 3`, and `evaluation_interval: 1` while retaining the current aggregation and scorer prompt.

- [ ] **Step 5: Run scorer tests**

Run: `python -m pytest -p no:cacheprovider tests/test_query_bank_threshold_scoring.py tests/test_two_stage_gateway.py -q`

Expected: all scorer and gateway tests pass.

### Task 5: Independent Attack Detection Threshold in Access Control

**Files:**
- Modify: `src/miaguard/access_policy.py`
- Modify: `src/miaguard/two_stage_gateway.py`
- Modify: `tests/test_access_policy.py`
- Modify: `tests/test_two_stage_gateway.py`

- [ ] **Step 1: Add failing backward-compatibility and threshold-policy tests**

Test legacy `LevelMapper(thresholds)` behavior unchanged. Test optional threshold demotes scores below `t_attack` to at most L1, promotes scores at/above `t_attack` to at least L2, retains L3/L4 severity above existing boundaries, observe never applies enforcement, and config rejects thresholds outside `[0,1]`.

```python
def test_attack_threshold_promotes_to_l2_without_changing_l3_l4():
    mapper = LevelMapper((0.05, 0.10, 0.65, 0.85), attack_detection_threshold=0.50)
    assert mapper.level(0.40) == "L1"
    assert mapper.level(0.50) == "L2"
    assert mapper.level(0.70) == "L3"
    assert mapper.level(0.90) == "L4"
```

- [ ] **Step 2: Run focused tests and verify failure**

Run: `python -m pytest -p no:cacheprovider tests/test_access_policy.py tests/test_two_stage_gateway.py -q`

Expected: new constructor/config assertions fail.

- [ ] **Step 3: Implement optional policy threshold**

Add `attack_detection_threshold: float | None` to `TwoStageConfig`. Parse `policy.attack_detection_threshold` when present. Pass it to `LevelMapper`. In `LevelMapper.level`, first compute legacy severity, then when the optional threshold exists:

```python
if score < attack_detection_threshold:
    return "L0" if score < thresholds[0] else "L1"
if legacy_level in {"L0", "L1"}:
    return "L2"
return legacy_level
```

Do not alter behavior when the field is absent.

- [ ] **Step 4: Add public session clearing**

Add `TwoStageGateway.clear_session(session_id)` to clear both `SessionStore` state and `_session_risk_cache`, and test both are empty afterward.

- [ ] **Step 5: Run policy/gateway tests**

Run: `python -m pytest -p no:cacheprovider tests/test_access_policy.py tests/test_two_stage_gateway.py -q`

Expected: all policy and gateway tests pass.

### Task 6: Calibration, Validation, and Config Export Workflow

**Files:**
- Create: `src/miaguard/query_bank_threshold_workflow.py`
- Create: `scripts/calibrate_query_bank_attack_threshold.py`
- Create: `scripts/validate_query_bank_attack_threshold.py`
- Test: `tests/test_query_bank_threshold_workflow.py`

- [ ] **Step 1: Write failing workflow tests**

Test train-only calibration permission, validation refusing threshold reselection, identity mismatch rejection, infeasible selection blocking config export, validation pass/fail gating, and generated YAML preserving existing severity thresholds while inserting only `attack_detection_threshold`.

- [ ] **Step 2: Run tests and verify failure**

Run: `python -m pytest -p no:cacheprovider tests/test_query_bank_threshold_workflow.py -q`

Expected: module import fails.

- [ ] **Step 3: Implement workflow functions**

Expose:

```python
def calibrate_train_partition(
    risk_records_path: Path,
    run_manifest_path: Path,
    output_path: Path,
    *,
    max_benign_fpr: float = 0.05,
) -> dict[str, Any]: ...

def validate_locked_threshold(
    risk_records_path: Path,
    run_manifest_path: Path,
    threshold_selection_path: Path,
    output_path: Path,
    *,
    max_validation_benign_fpr: float = 0.10,
) -> dict[str, Any]: ...

def export_enforce_config(
    base_config_path: Path,
    validation_result_path: Path,
    output_path: Path,
) -> None: ...
```

Require `partition == "train"` for calibration and `partition == "validation"` for validation. Compare all identity fields from the specification. Mark validation passed only when benign query FPR <= 0.10 and every attack has nonzero document-balanced recall.

- [ ] **Step 4: Implement CLIs**

Calibration CLI takes train run directory and FPR bound. Validation CLI takes validation run directory, train selection, and optional base/output configs. Both refuse overwrite and print structured JSON summaries.

- [ ] **Step 5: Run workflow tests**

Run: `python -m pytest -p no:cacheprovider tests/test_query_bank_threshold_workflow.py -q`

Expected: all workflow tests pass.

### Task 7: Full Test-Partition Three-Condition Comparison

**Files:**
- Create: `src/miaguard/query_bank_threshold_comparison.py`
- Create: `scripts/run_query_bank_threshold_test_comparison.py`
- Test: `tests/test_query_bank_threshold_comparison.py`

- [ ] **Step 1: Write failing comparison-adapter tests**

Use fake guards and model clients to verify that the adapter consumes the exact frozen test sessions, runs `disabled`, legacy `0.10`, and learned-threshold conditions with identical query/session ordering, never searches a threshold, and rejects a failed validation result or any identity mismatch.

- [ ] **Step 2: Run tests and verify failure**

Run: `python -m pytest -p no:cacheprovider tests/test_query_bank_threshold_comparison.py -q`

Expected: module import fails.

- [ ] **Step 3: Implement Query Bank record adapters**

Expose deterministic adapters from a `PlannedSession` to the row shapes already accepted by `_replay_direct`, `_replay_s2`, `_replay_masked`, `_replay_ia`, and `_run_benign_queries`. Non-IA sessions pass their five rows through one session ID. Each IA planned session becomes one IA row whose `queries` array preserves the planned turn order. Benign rows preserve their five-turn session ID.

- [ ] **Step 4: Implement the three-condition runner**

Expose:

```python
def run_query_bank_threshold_test_comparison(
    project_root: Path,
    source_run_id: str,
    dataset_id: str,
    output_run_id: str,
    attack_config: AttackConfig,
    base_gateway_config: TwoStageConfig,
    scorer_config: DirectScorerConfig,
    *,
    query_bank_id: str,
    split_path: Path,
    validation_result_path: Path,
) -> dict[str, Any]: ...
```

Require the frozen partition to be `test` and the validation result to be passed. Build three gateways from the same base config: disabled, enforce with `attack_detection_threshold=0.10`, and enforce with the learned threshold. Load the model, vector store, pattern library, planned sessions, and baseline attack scoring machinery once. Execute identical sessions in each condition, clearing session state between sessions and conditions. Write condition-specific events/decisions, query-level and document-balanced attack metrics, detector metrics, session metrics, and a comparison summary.

- [ ] **Step 5: Implement CLI and run tests**

Run: `python -m pytest -p no:cacheprovider tests/test_query_bank_threshold_comparison.py tests/test_two_stage_attack_comparison.py -q`

Expected: all comparison tests pass.

### Task 8: Freeze the Real AG News Split and Audit the Full Session Plan

**Files:**
- Create: `data/query_bank_splits/ag_news_threshold_v1.json`
- Create: `reports/ag_news_threshold_session_plan_audit.json`

- [ ] **Step 1: Freeze the real split**

Run:

```powershell
python scripts/freeze_query_bank_threshold_split.py `
  --query-bank-id ag_news_queries_v1 `
  --dataset ag_news `
  --split-id ag_news_threshold_v1 `
  --seed 20260818 `
  --output data/query_bank_splits/ag_news_threshold_v1.json `
  --project-root .
```

Expected: 60/20/20 documents with 30/10/10 member and nonmember counts.

- [ ] **Step 2: Generate a read-only full session-plan audit**

Use the session planner for all three partitions without loading the LLM. Write counts by partition, traffic/attack type, session length, query count, and duplicate/missing counts to `reports/ag_news_threshold_session_plan_audit.json`.

Expected totals: 5,956 accepted queries, 500 each benign/direct/s2/masked, 3,956 IA, no missing or duplicate query IDs, non-IA and benign sessions of length five, IA sessions of length four or five.

- [ ] **Step 3: Validate frozen artifacts**

Run:

```powershell
python -m pytest -p no:cacheprovider `
  tests/test_query_bank_threshold_split.py `
  tests/test_query_bank_sessions.py -q
```

Expected: all tests pass and checked-in split validates against the current Query Bank hash.

### Task 9: Regression and End-to-End Verification

**Files:**
- Modify: `docs/TWO_STAGE_DIRECT_SCORING_ZH.md`
- Modify: `docs/USAGE_GUIDE_ZH.md`

- [ ] **Step 1: Document the new workflow**

Add exact commands for split freezing, partition scoring, train calibration, locked validation, config export, and final test prerequisites. Explicitly state that full scoring is a long GPU job and that test must not run before validation passes.

- [ ] **Step 2: Run focused workflow tests**

Run:

```powershell
python -m pytest -p no:cacheprovider `
  tests/test_query_bank_threshold_split.py `
  tests/test_query_bank_sessions.py `
  tests/test_supervised_threshold.py `
  tests/test_query_bank_threshold_scoring.py `
  tests/test_query_bank_threshold_workflow.py `
  tests/test_query_bank_threshold_comparison.py `
  tests/test_access_policy.py `
  tests/test_two_stage_gateway.py -q
```

Expected: all focused tests pass.

- [ ] **Step 3: Run the full regression suite**

Run: `python -m pytest -p no:cacheprovider -q`

Expected: all tests pass.

- [ ] **Step 4: Verify dependency health**

Run: `python -m pip check`

Expected: `No broken requirements found.`

- [ ] **Step 5: Do not start full LLM scoring automatically**

The implementation handoff includes the exact train command, estimated workload, frozen split, and session audit. Full 5,956-query GPU scoring begins only as an explicit experiment run because it is long-running and produces material experimental artifacts.
