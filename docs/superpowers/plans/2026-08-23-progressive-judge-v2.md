# Progressive LLM-as-Judge v2 Implementation Plan

> **Protocol amendment:** The original `screening_level` schema in this historical plan was superseded on 2026-08-23 by the approved high-recall candidate-router schema documented in design specification section 15.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a side-by-side Progressive Judge v2 benchmark that performs summary-only screening, candidate-only evidence review, and independent rubric/logprob scoring without changing the existing v1 scorer or touching the frozen test partition.

**Architecture:** Add a new pure Judge module and a narrow Transformers candidate-logprob interface, then orchestrate them through a resumable Query Bank benchmark. Keep offline truth only in benchmark records and evaluation, never in the Judge API or prompts. Compare both scoring heads with threshold-free and fixed-FPR metrics; defer formal access-control threshold calibration until the Judge is selected and frozen.

**Tech Stack:** Python 3.10, dataclasses, PyYAML, NumPy, scikit-learn, Transformers/PyTorch, pytest, existing Query Bank/session/shard utilities.

---

## Environment note

`D:\Project\MIAGuard` is not a Git repository. The normal commit steps required by the planning skill are replaced below by explicit test checkpoints and changed-file inventories. Do not initialize Git or modify unrelated files.

## File map

- Create `src/miaguard/progressive_judge.py`: configuration, stage schemas, prompt builders, parsers, Query/Session progressive execution.
- Modify `src/miaguard/model_client.py`: restricted candidate-label probability interface for Transformers.
- Create `src/miaguard/query_bank/judge_benchmark.py`: identity-bound resumable benchmark shards and compaction.
- Create `src/miaguard/judge_evaluation.py`: rubric/logprob Judge metrics and selection diagnostics.
- Create `scripts/run_query_bank_judge_benchmark.py`: benchmark CLI.
- Create `scripts/evaluate_query_bank_judge_benchmark.py`: evaluation CLI.
- Create `configs/defense/progressive_judge_v2.yaml`: immutable v2 experiment configuration.
- Create `tests/test_progressive_judge.py`: staged prompts, schemas, Query/Session behavior.
- Modify `tests/test_model_client.py`: logprob helpers and backend constraints.
- Create `tests/test_query_bank_judge_benchmark.py`: test rejection, identity, resume, corruption handling.
- Create `tests/test_judge_evaluation.py`: metric roles and scoring-head comparison.
- Modify `tests/test_query_bank_scripts.py`: CLI help/import smoke coverage.
- Create `docs/PROGRESSIVE_JUDGE_V2_EXPERIMENT_ZH.md`: usage, outputs, data boundaries, next-stage gate.

### Task 1: Configuration, schemas, and progressive prompt builders

**Files:**
- Create: `src/miaguard/progressive_judge.py`
- Create: `tests/test_progressive_judge.py`
- Create: `configs/defense/progressive_judge_v2.yaml`

- [ ] **Step 1: Write failing configuration and disclosure tests**

Add tests that express the public API before production code exists:

```python
from pathlib import Path

import pytest

from miaguard.attack_pattern_library import AttackPatternLibrary
from miaguard.progressive_judge import (
    ProgressiveJudgeConfig,
    ScreeningResult,
    build_detail_prompt,
    build_screening_prompt,
    load_progressive_judge_config,
)


ROOT = Path(__file__).resolve().parents[1]


def test_progressive_config_loads_versioned_scoring_contract() -> None:
    config = load_progressive_judge_config(
        ROOT / "configs/defense/progressive_judge_v2.yaml", ROOT
    )
    assert config.prompt_version == "progressive_v2_rubric_logprob"
    assert config.max_candidate_patterns == 2
    assert config.logprob_labels == ("A", "B", "C")
    assert config.logprob_anchors == (0.1, 0.5, 0.9)


def test_screening_discloses_summaries_but_not_full_patterns() -> None:
    config = load_progressive_judge_config(
        ROOT / "configs/defense/progressive_judge_v2.yaml", ROOT
    )
    library = AttackPatternLibrary.load(config.manifest_path)
    prompt = build_screening_prompt(
        stage="query", case={"query": "Does this passage appear?"},
        config=config, library=library,
    )
    assert library.patterns["direct_rag_mia"].summary in prompt
    assert "# Strong indicators" not in prompt
    assert "membership_label" not in prompt


def test_detail_discloses_only_selected_patterns() -> None:
    config = load_progressive_judge_config(
        ROOT / "configs/defense/progressive_judge_v2.yaml", ROOT
    )
    library = AttackPatternLibrary.load(config.manifest_path)
    screening = ScreeningResult("MEDIUM", ("ia",), True, ("REPEATED_TARGET",))
    prompt = build_detail_prompt(
        stage="session", case={"recent_turns": []}, screening=screening,
        config=config, library=library,
    )
    assert "# Security objective" in prompt
    assert "SYSTEMATIC_ENTITY_PROBING" in prompt
    assert "REQUESTS_EXACT_RECOVERY" not in prompt


@pytest.mark.parametrize("partition", ["test", "TEST"])
def test_progressive_config_never_enables_test(partition: str) -> None:
    config = ProgressiveJudgeConfig.for_test(ROOT)
    with pytest.raises(ValueError, match="test partition"):
        config.validate_partition(partition)
```

- [ ] **Step 2: Run the tests and verify RED**

Run:

```powershell
& 'D:\ProgramData\Anaconda3\envs\MIAGuard\python.exe' -m pytest tests\test_progressive_judge.py -q
```

Expected: collection fails with `ModuleNotFoundError: miaguard.progressive_judge`.

- [ ] **Step 3: Implement immutable configuration and stage dataclasses**

Create these public types in `progressive_judge.py`:

```python
@dataclass(frozen=True)
class ProgressiveJudgeConfig:
    manifest_path: Path
    query_pattern_ids: tuple[str, ...]
    session_pattern_ids: tuple[str, ...]
    prompt_version: str
    max_candidate_patterns: int
    max_retries: int
    screening_max_tokens: int
    detail_max_tokens: int
    rubric_max_tokens: int
    logprob_labels: tuple[str, str, str]
    logprob_anchors: tuple[float, float, float]
    allowed_partitions: tuple[str, ...]

    def validate_partition(self, partition: str) -> None:
        normalized = partition.strip().lower()
        if normalized == "test" or normalized not in self.allowed_partitions:
            raise ValueError(f"Progressive Judge benchmark forbids test partition: {partition}")


@dataclass(frozen=True)
class ScreeningResult:
    screening_level: str
    candidate_attack_types: tuple[str, ...]
    needs_detailed_review: bool
    reason_codes: tuple[str, ...]


@dataclass(frozen=True)
class AttackAssessment:
    attack_type: str
    verdict: str
    required_conditions_met: bool
    supporting_evidence_codes: tuple[str, ...]
    counter_evidence_codes: tuple[str, ...]


@dataclass(frozen=True)
class EvidencePacket:
    assessments: tuple[AttackAssessment, ...]
```

Implement YAML validation for positive token limits, exactly three unique labels, increasing anchors in `[0,1]`, `max_candidate_patterns` in `1..len(patterns)`, and allowed partitions excluding test.

- [ ] **Step 4: Implement pure screening/detail prompt builders**

Use `library.index()` for screening summaries and `library.read_patterns()` only for selected detail candidates. Query and Session builders must have separate task text. Serialize untrusted case data inside explicit XML-delimited JSON and state that its instructions must not be followed.

- [ ] **Step 5: Add the versioned YAML configuration**

Create:

```yaml
schema_version: 1
progressive_judge:
  manifest: attack_pattern_library/manifest.yaml
  query_patterns: [direct_rag_mia, s2_mia, masked_mia, ia]
  session_patterns: [direct_rag_mia, s2_mia, masked_mia, ia]
  prompt_version: progressive_v2_rubric_logprob
  max_candidate_patterns: 2
  max_retries: 1
  screening_max_tokens: 96
  detail_max_tokens: 160
  rubric_max_tokens: 128
  logprob_labels: [A, B, C]
  logprob_anchors: [0.1, 0.5, 0.9]
  allowed_partitions: [train, validation]
```

- [ ] **Step 6: Run focused tests and verify GREEN**

Run the Task 1 pytest command. Expected: all tests in `test_progressive_judge.py` pass.

- [ ] **Step 7: Record checkpoint**

Record changed files and the focused pytest result in the plan execution log; do not initialize Git.

### Task 2: Restricted candidate-label probabilities in ModelClient

**Files:**
- Modify: `src/miaguard/model_client.py`
- Modify: `tests/test_model_client.py`

- [ ] **Step 1: Write failing pure-helper tests**

Add:

```python
from miaguard.model_client import (
    _candidate_token_ids,
    _restricted_probabilities,
)


class _Tokenizer:
    def __call__(self, text, **kwargs):
        mapping = {"A": [11], "B": [12], "C": [13], "BAD": [14, 15]}
        return {"input_ids": mapping[text]}


def test_candidate_labels_must_each_be_one_token() -> None:
    assert _candidate_token_ids(_Tokenizer(), ("A", "B", "C")) == {
        "A": 11, "B": 12, "C": 13
    }
    with pytest.raises(ValueError, match="single token"):
        _candidate_token_ids(_Tokenizer(), ("A", "BAD", "C"))


def test_restricted_probabilities_normalize_only_candidates() -> None:
    result = _restricted_probabilities({"A": 0.0, "B": 1.0, "C": 2.0})
    assert set(result) == {"A", "B", "C"}
    assert sum(result.values()) == pytest.approx(1.0)
    assert result["C"] > result["B"] > result["A"]
```

- [ ] **Step 2: Run the focused tests and verify RED**

Run:

```powershell
& 'D:\ProgramData\Anaconda3\envs\MIAGuard\python.exe' -m pytest tests\test_model_client.py -q
```

Expected: imports fail because the helpers do not exist.

- [ ] **Step 3: Implement pure candidate validation and stable softmax**

Implement single-token validation with `add_special_tokens=False` and a max-shifted softmax. Reject booleans, non-finite logits, duplicate labels, missing labels, and fewer than two candidates.

- [ ] **Step 4: Add `candidate_label_probabilities`**

For Transformers:

1. Apply the same system/chat-template rendering as `generate`.
2. Tokenize the complete prompt.
3. Run one inference forward pass.
4. Read `outputs.logits[0, -1, candidate_token_id]`.
5. Return candidate-restricted probabilities in input label order.

For Ollama, raise `RuntimeError("Candidate label probabilities require transformers backend")`.

- [ ] **Step 5: Add a fake-model method test**

Use an object created with `object.__new__(ModelClient)`, a fake config with `generation_backend="transformers"`, and monkeypatch `_load_generation` to return a minimal fake tokenizer/model. Assert that the method forwards system text, returns three finite probabilities, and calls the model once.

- [ ] **Step 6: Verify GREEN and regression safety**

Run:

```powershell
& 'D:\ProgramData\Anaconda3\envs\MIAGuard\python.exe' -m pytest tests\test_model_client.py -q
```

Expected: all ModelClient tests pass without loading CUDA models.

### Task 3: Progressive Query/Session execution and independent scoring heads

**Files:**
- Modify: `src/miaguard/progressive_judge.py`
- Modify: `tests/test_progressive_judge.py`

- [ ] **Step 1: Write failing execution tests with a real fake client**

Define a fake client that records calls and returns screening, evidence, rubric, and logprob responses. Add tests asserting:

```python
def test_query_trace_reuses_one_evidence_packet_for_both_heads() -> None:
    client = _ProgressiveClient(
        json_responses=[
            {"screening_level": "MEDIUM", "candidate_attack_types": ["s2_mia"],
             "needs_detailed_review": True, "reason_codes": ["SOURCE_PREFIX"]},
            {"assessments": [{"attack_type": "s2_mia", "verdict": "LIKELY",
             "required_conditions_met": True,
             "supporting_evidence_codes": ["SOURCE_PREFIX_PROVIDED"],
             "counter_evidence_codes": []}]},
            {"risk_score": 72, "risk_band": "HIGH", "judge_confidence": 0.81,
             "suspected_attack_types": ["s2_mia"],
             "evidence_codes": ["SOURCE_PREFIX_PROVIDED"]},
        ],
        label_probabilities={"A": 0.05, "B": 0.25, "C": 0.70},
    )
    trace = _judge(client).evaluate_query(query="Complete this source prefix", session_id="s1")
    assert trace.rubric.score == pytest.approx(0.72)
    assert trace.logprob.score == pytest.approx(0.755)
    assert trace.evidence.assessments[0].attack_type == "s2_mia"
    assert len(client.json_prompts) == 3
    assert len(client.logprob_prompts) == 1
    assert "risk_score" not in client.logprob_prompts[0]


def test_low_screening_skips_detail_but_scores_both_heads() -> None:
    # LOW + no candidates creates an empty EvidencePacket and makes only
    # screening, rubric, and logprob calls.


def test_session_requires_three_turns_and_uses_session_specific_prompt() -> None:
    # Before turn 3 return insufficient_history without any model call.
    # At turn 3 include ordered turns and retrieval concentration, but no truth fields.


def test_offline_truth_is_not_accepted_by_public_judge_signatures() -> None:
    forbidden = {"traffic_type", "attack_type", "membership_label", "target_doc_id"}
    # Inspect both evaluate_query and evaluate_session signatures.
```

- [ ] **Step 2: Run tests and verify RED**

Expected failures: missing `ProgressiveJudge`, trace/scoring dataclasses, and execution methods.

- [ ] **Step 3: Implement strict parsers and repair retries**

Add `parse_screening`, `parse_evidence`, and `parse_rubric` pure functions. Risk bands must match integer ranges exactly. Medium/high screening without candidates, unknown evidence codes, missing candidate assessments, duplicate types, or score/band mismatches must return invalid and trigger a format-repair retry.

- [ ] **Step 4: Implement trace and score dataclasses**

```python
@dataclass(frozen=True)
class RubricScore:
    score: float
    score_100: int
    risk_band: str
    judge_confidence: float
    suspected_attack_types: tuple[str, ...]
    evidence_codes: tuple[str, ...]


@dataclass(frozen=True)
class LogprobScore:
    score: float
    probabilities: dict[str, float]
    anchors: tuple[float, float, float]


@dataclass(frozen=True)
class ProgressiveJudgeTrace:
    stage: str
    screening: ScreeningResult
    evidence: EvidencePacket
    rubric: RubricScore
    logprob: LogprobScore
    statuses: dict[str, str]
    latencies_ms: dict[str, float]
```

- [ ] **Step 5: Implement Query and Session evaluation**

Use one screening result and one evidence packet, then invoke the two scoring heads independently. For Session, accept only online fields matching `DirectSessionRiskDetector`, return `insufficient_history` before turn 3, and use a separate session prompt family.

- [ ] **Step 6: Verify GREEN**

Run all `test_progressive_judge.py` tests. Expected: pass with no model/CUDA access.

### Task 4: Identity-bound resumable Query Bank benchmark

**Files:**
- Create: `src/miaguard/query_bank/judge_benchmark.py`
- Create: `tests/test_query_bank_judge_benchmark.py`

- [ ] **Step 1: Write failing path, partition, and resume tests**

Build two small `PlannedSession` fixtures directly. Use a fake Judge returning deterministic traces. Tests must assert:

```python
def test_benchmark_rejects_test_before_any_model_call(tmp_path: Path) -> None:
    paths = JudgeBenchmarkPaths(tmp_path / "runs", "test")
    with pytest.raises(ValueError, match="forbids test"):
        run_judge_benchmark(
            sessions=(),
            judge=fake_judge,
            store=fake_store,
            top_k=4,
            paths=paths,
            identity={"partition": "test", "prompt_version": "v2"},
            allowed_partitions=("train", "validation"),
        )
    assert fake_judge.calls == []


def test_benchmark_resumes_complete_session_shards(tmp_path: Path) -> None:
    kwargs = {
        "sessions": sessions,
        "judge": fake_judge,
        "store": fake_store,
        "top_k": 4,
        "paths": JudgeBenchmarkPaths(tmp_path / "runs", "validation"),
        "identity": {"partition": "validation", "prompt_version": "v2"},
        "allowed_partitions": ("train", "validation"),
    }
    first = run_judge_benchmark(**kwargs)
    second = run_judge_benchmark(**kwargs)
    assert first["completed_session_count"] == 2
    assert second["skipped_session_count"] == 2
    assert len(fake_judge.calls) == expected_first_run_calls


def test_benchmark_recomputes_invalid_shard(tmp_path: Path) -> None:
    # Corrupt one shard, rerun, assert invalid_session_count == 1 and only it reruns.


def test_benchmark_refuses_identity_mismatch(tmp_path: Path) -> None:
    # Change prompt_version while reusing output directory; expect ValueError.
```

- [ ] **Step 2: Run tests and verify RED**

Expected: module import failure.

- [ ] **Step 3: Implement benchmark paths and canonical identity**

Mirror `ThresholdScoringPaths`: partition root, `.work`, `run_manifest.json`, `judge_records.jsonl`, and `benchmark_summary.json`. Identity includes query-bank/split hashes, partition, model configuration, Progressive Judge configuration, pattern versions, labels, anchors, and session-planning version.

- [ ] **Step 4: Implement per-session atomic execution**

For every turn, call `store.search(query_text, top_k)`, build retrieval IDs/scores, and save both Query trace and the Session trace/status. Maintain an in-memory raw Session history containing only prior queries and retrieval results; do not feed either scoring head's prior score into the common Session evidence path. Offline labels may appear in the outer benchmark row for later evaluation, but construct them outside the case passed to the Judge. Discard the local history after each planned session. Only write a shard after every turn completes.

- [ ] **Step 5: Implement validation and deterministic compaction**

Validate session key, query IDs/order, scoring identity hash, required trace fields, finite scores, and probability sums. Compact shards in the frozen planned-session/turn order and write hashes to summary.

- [ ] **Step 6: Verify GREEN**

Run:

```powershell
& 'D:\ProgramData\Anaconda3\envs\MIAGuard\python.exe' -m pytest tests\test_query_bank_judge_benchmark.py -q
```

Expected: all benchmark tests pass.

### Task 5: Judge evaluation without a formal access threshold

**Files:**
- Create: `src/miaguard/judge_evaluation.py`
- Create: `tests/test_judge_evaluation.py`

- [ ] **Step 1: Write failing synthetic-metric tests**

Create records for benign plus four attacks across multiple docs/sessions. Assert:

```python
def test_evaluation_treats_ia_query_metrics_as_diagnostic() -> None:
    report = evaluate_judge_records(records, bootstrap_replicates=0)
    assert report["metric_roles"]["ia_query"] == "diagnostic"
    assert report["metric_roles"]["ia_session"] == "primary"


def test_fixed_fpr_operating_point_maximizes_recall_under_cap() -> None:
    point = fixed_fpr_operating_point(labels, scores, max_fpr=0.05)
    assert point["fpr"] <= 0.05
    assert point["threshold_kind"] == "diagnostic_only"


def test_both_heads_are_evaluated_on_identical_rows() -> None:
    report = evaluate_judge_records(records, bootstrap_replicates=0)
    assert set(report["heads"]) == {"rubric", "logprob"}
    assert report["heads"]["rubric"]["query_count"] == report["heads"]["logprob"]["query_count"]


def test_selection_uses_predeclared_lexicographic_objective() -> None:
    selection = compare_judge_heads(report)
    assert selection["selection_objective"][0] == "maximize_minimum_primary_recall_at_5pct_fpr"
```

- [ ] **Step 2: Run tests and verify RED**

Expected: module import failure.

- [ ] **Step 3: Implement validated records and point metrics**

Compute Query metrics for benign/Direct/Masked/S2 and diagnostic IA Query metrics. Build Session records from final-turn Session scores; compute primary IA Session metrics. Implement AUROC, fixed-FPR recall at 1/5/10%, macro/minimum primary recall, unique score count, maximum score mass, parse/status rates, and latency summaries.

- [ ] **Step 4: Implement document bootstrap**

Resample `doc_id` with replacement and rename drawn IDs to preserve duplicate draws. Return 95% intervals for the primary selection metrics. Keep bootstrap seed and replicate count in the report.

- [ ] **Step 5: Implement deterministic scoring-head comparison**

Rank rubric/logprob lexicographically using the frozen design objective. Output a recommendation with metric values, but explicitly mark every diagnostic operating-point threshold as non-deployable.

- [ ] **Step 6: Verify GREEN**

Run:

```powershell
& 'D:\ProgramData\Anaconda3\envs\MIAGuard\python.exe' -m pytest tests\test_judge_evaluation.py -q
```

Expected: all evaluation tests pass.

### Task 6: CLIs, documentation, and identity smoke tests

**Files:**
- Create: `scripts/run_query_bank_judge_benchmark.py`
- Create: `scripts/evaluate_query_bank_judge_benchmark.py`
- Modify: `tests/test_query_bank_scripts.py`
- Create: `docs/PROGRESSIVE_JUDGE_V2_EXPERIMENT_ZH.md`

- [ ] **Step 1: Write failing CLI help/import tests**

Extend the existing script test pattern to assert both scripts return exit code 0 for `--help`, and that run-script parser defaults cannot name test. Add a unit test that the evaluation CLI refuses to overwrite an existing report.

- [ ] **Step 2: Run tests and verify RED**

Expected: missing script failures.

- [ ] **Step 3: Implement the benchmark CLI**

Required arguments: attack config, Progressive Judge config, source run ID, query bank ID, dataset, frozen split, partition, output root, and project root. Construct Query Bank sessions through existing loaders. Validate partition before loading the generation model.

- [ ] **Step 4: Implement the evaluation CLI**

Required arguments: benchmark run directory and output report. Optional arguments: bootstrap seed/replicates. Verify manifest/record hashes and refuse existing output.

- [ ] **Step 5: Write the Chinese experiment guide**

Document:

- v1 remains the baseline;
- development commands use validation only in this first prompt-development round;
- test is forbidden;
- output files and resume behavior;
- direct-rubric versus label-logprob metrics;
- no formal threshold is learned here;
- the gate for moving to full train/validation scoring.

- [ ] **Step 6: Verify scripts and focused integration tests**

Run:

```powershell
& 'D:\ProgramData\Anaconda3\envs\MIAGuard\python.exe' -m pytest `
  tests\test_progressive_judge.py `
  tests\test_model_client.py `
  tests\test_query_bank_judge_benchmark.py `
  tests\test_judge_evaluation.py `
  tests\test_query_bank_scripts.py -q
```

Expected: all focused tests pass.

### Task 7: Full verification and readiness gate

**Files:**
- Verify all changed files from Tasks 1--6.

- [ ] **Step 1: Run compile checks**

```powershell
& 'D:\ProgramData\Anaconda3\envs\MIAGuard\python.exe' -m compileall -q src scripts tests
```

Expected: exit code 0.

- [ ] **Step 2: Run the entire project test suite**

```powershell
& 'D:\ProgramData\Anaconda3\envs\MIAGuard\python.exe' -m pytest -q
```

Expected: zero failures; pre-existing skips/warnings may remain and must be reported exactly.

- [ ] **Step 3: Run dependency consistency check**

```powershell
& 'D:\ProgramData\Anaconda3\envs\MIAGuard\python.exe' -m pip check
```

Expected: `No broken requirements found.`

- [ ] **Step 4: Perform a no-GPU benchmark smoke test**

Use the fake-Judge fixture path exercised by tests to write, resume, validate, compact, and evaluate a two-session benchmark in a temporary directory. Verify test rejection occurs before any client call.

- [ ] **Step 5: Audit requirements against the written specification**

Confirm:

- v1 scorer/config/history unchanged;
- screening prompts contain summaries only;
- detail prompts contain selected full patterns only;
- Query/Session prompt families are distinct;
- truth fields do not enter Judge interfaces/prompts;
- both heads share evidence and remain independent;
- test is rejected;
- benchmark is resumable and identity-bound;
- evaluation does not export an access threshold.

- [ ] **Step 6: Report verified status and next action**

Report exact test counts and any limitations. Do not start the long GPU benchmark until the user explicitly requests execution after reviewing the completed implementation.

---

## Execution log (2026-08-23)

- Baseline before implementation: `287 passed, 1 skipped, 3 warnings`.
- Tasks 1--6 implemented with failing-test-first checkpoints.
- Focused Progressive Judge suite after implementation: `48 passed, 3 warnings`.
- Full project verification: `315 passed, 1 skipped, 3 warnings`.
- `compileall` exited successfully and `pip check` reported `No broken requirements found.`
- No Git repository was present, so no worktree, branch, or commits were created.
- The long GPU benchmark was intentionally not started; it requires explicit user approval after implementation review.

### Candidate-router amendment verification

- Replaced risk-level screening with `REVIEW|SKIP_EXPLICIT_BENIGN` candidate routing.
- Split router, candidate-verifier, and evidence-scoring protocols.
- Added semantic rubric bands, semantic A/B/C labels, and routing-quality metrics.
- Bumped prompt identity to `progressive_v2_router_verifier_rubric_logprob`.
- Focused verification: `52 passed, 3 warnings`.
- Full project verification: `319 passed, 1 skipped, 3 warnings`.
- Compile check and dependency consistency check passed.

### Evidence-only scoring amendment (2026-08-24)

- Added verifier consistency fields and exact verdict constraints.
- Removed raw Query/Session data from both scoring heads.
- Restricted Query-stage IA routing and renamed explicit-benign skip status.
- Validated A/B/C token IDs in the final rendered prompt context.
- Bumped prompt identity to `progressive_v2_evidence_only_scoring_descriptive_missing` after real-model smoke showed that unmet natural-language conditions and controlled evidence reason codes are different vocabularies.
