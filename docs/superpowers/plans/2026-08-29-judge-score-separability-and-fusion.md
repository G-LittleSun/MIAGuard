# Judge Score Separability and Fusion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a reproducible train-only analysis and grouped-OOF model-comparison pipeline for the Progressive Judge `rubric` and `logprob` query/session scores, then freeze one binary attack detector and its global access threshold for independent validation.

**Architecture:** Extend the verified Judge-record loader, normalize both score heads into one long-form table, and keep descriptive analysis separate from supervised fusion. Stage A produces auditable distributions and stops for review. Stage B uses fixed `doc_id`-grouped folds to compare query-only, session-only, legacy fusion, L2 logistic regression, a depth-2 tree, and a fixed shallow MLP. Stage C serializes the train-selected model and threshold and applies them to validation without refitting or retuning.

**Tech Stack:** Python 3.10, NumPy, pandas, SciPy, scikit-learn, Matplotlib, PyArrow, joblib, pytest.

---

## Scope and file map

Create or modify these focused units:

- Modify `pyproject.toml`: declare reproducible analysis dependencies.
- Modify `src/miaguard/query_bank/judge_benchmark.py`: expose verified Judge-record loading currently duplicated in a script.
- Modify `scripts/evaluate_query_bank_judge_benchmark.py`: consume the public verified loader.
- Create `src/miaguard/judge_score_dataset.py`: audit records and build the two-head long-form dataset.
- Create `src/miaguard/judge_score_analysis.py`: descriptive statistics, correlations, and figures only.
- Create `src/miaguard/judge_score_fusion.py`: grouped folds, fixed model candidates, OOF predictions, metrics, bootstrap, and threshold selection.
- Create `src/miaguard/query_bank/judge_score_workflow.py`: artifact I/O, hashes, manifests, train freeze, and locked validation.
- Create `scripts/analyze_judge_scores.py`: Stage A command.
- Create `scripts/train_judge_score_fusion.py`: Stage B command; requires an explicit reviewed Stage A report hash.
- Create `scripts/validate_judge_score_fusion.py`: Stage C validation command; cannot fit or select.
- Create tests matching each module.
- Create `docs/JUDGE_SCORE_SEPARABILITY_EXPERIMENT_ZH.md`: exact experiment protocol and commands.

The workspace currently has no `.git` directory. The implementation therefore uses test/manifest checkpoints below; commit commands should only be run after this directory is restored inside a Git repository.

## Fixed experimental constants

Use these constants everywhere rather than accepting silent defaults from separate scripts:

```python
SCORE_HEADS = ("rubric", "logprob")
ATTACK_TYPES = ("direct_rag_mia", "s2_mia", "masked_mia", "ia")
FPR_CAPS = (0.01, 0.02, 0.05, 0.10)
PRIMARY_FPR_CAP = 0.05
CV_SPLITS = 5
CV_SEED = 20260829
BOOTSTRAP_REPLICATES = 1000
BOOTSTRAP_SEED = 20260829
LEGACY_QUERY_WEIGHT = 0.4
LEGACY_SESSION_WEIGHT = 0.6
LEGACY_WINDOW_SIZE = 5
```

The binary label is `traffic_type == "attack"`. `attack_type` is retained only for stratified diagnostics and macro/minimum recall. No model receives attack type, membership label, query text, router output, retrieval score, document ID, session ID, or turn index as a predictive feature.

### Task 1: Declare and verify analysis dependencies

**Files:**
- Modify: `pyproject.toml`
- Create: `tests/test_analysis_dependencies.py`

- [ ] **Step 1: Write the failing dependency-declaration test**

```python
from pathlib import Path


def test_analysis_extra_declares_reproducible_stack() -> None:
    root = Path(__file__).resolve().parents[1]
    text = (root / "pyproject.toml").read_text(encoding="utf-8")
    assert "analysis = [" in text
    assert '"pandas>=2.3,<3"' in text
    assert '"scipy>=1.15,<2"' in text
    assert '"matplotlib>=3.10,<4"' in text
    assert '"pyarrow>=20,<22"' in text
```

- [ ] **Step 2: Run the test and verify it fails because the extra is absent**

Run: `conda run -n MIAGuard python -m pytest tests/test_analysis_dependencies.py -q`

Expected: one assertion failure because the analysis extra is absent.

- [ ] **Step 3: Add the analysis extra**

Add under `[project.optional-dependencies]`:

```toml
analysis = [
  "pandas>=2.3,<3",
  "scipy>=1.15,<2",
  "matplotlib>=3.10,<4",
  "pyarrow>=20,<22",
]
```

`scikit-learn` and NumPy remain in the core dependency set. `joblib` is installed as a scikit-learn dependency and must be imported through its normal package name.

- [ ] **Step 4: Run the dependency test**

Run: `conda run -n MIAGuard python -m pytest tests/test_analysis_dependencies.py -q`

Expected: `1 passed`.

### Task 2: Expose one verified Judge-record loader

**Files:**
- Modify: `src/miaguard/query_bank/judge_benchmark.py`
- Modify: `scripts/evaluate_query_bank_judge_benchmark.py`
- Modify: `tests/test_query_bank_judge_benchmark.py`

- [ ] **Step 1: Add failing tests for valid and tampered artifacts**

Add tests that create a temporary `run_manifest.json`, `benchmark_summary.json`, and `judge_records.jsonl`, then assert:

```python
records, source = load_verified_judge_records(run_dir)
assert records[0]["query_id"] == "q-1"
assert source["scoring_identity_sha256"] == identity_sha256
assert source["judge_records_sha256"] == sha256_file(records_path)
```

Tamper with the record file after writing the summary and assert:

```python
with pytest.raises(ValueError, match="record hash"):
    load_verified_judge_records(run_dir)
```

Also change one row's `scoring_identity_sha256` and assert a `mixed scoring identity` error.

- [ ] **Step 2: Run the focused tests and verify failure**

Run: `conda run -n MIAGuard python -m pytest tests/test_query_bank_judge_benchmark.py -q`

Expected: failures because `load_verified_judge_records` is not exported.

- [ ] **Step 3: Move the existing verification contract into the library**

Add this public signature to `judge_benchmark.py` and reuse existing JSONL/hash helpers:

```python
def load_verified_judge_records(run_dir: Path) -> tuple[list[dict[str, Any]], dict[str, str]]:
    manifest_path = run_dir / "run_manifest.json"
    records_path = run_dir / "judge_records.jsonl"
    summary_path = run_dir / "benchmark_summary.json"
    manifest = _load_manifest(manifest_path)
    summary = _load_manifest(summary_path)
    identity_sha256 = canonical_identity_sha256(manifest["identity"])
    if manifest.get("identity_sha256") != identity_sha256:
        raise ValueError("Judge benchmark manifest identity hash does not match")
    if summary.get("scoring_identity_sha256") != identity_sha256:
        raise ValueError("Judge benchmark summary identity hash does not match")
    records_sha256 = sha256_file(records_path)
    if summary.get("judge_records_sha256") != records_sha256:
        raise ValueError("Judge benchmark record hash does not match")
    records = list(read_jsonl(records_path))
    if any(row.get("scoring_identity_sha256") != identity_sha256 for row in records):
        raise ValueError("Judge benchmark contains a mixed scoring identity")
    return records, {
        "scoring_identity_sha256": identity_sha256,
        "judge_records_sha256": records_sha256,
    }
```

Export it in `__all__`. Remove the private duplicate from `evaluate_query_bank_judge_benchmark.py` and import this function instead.

- [ ] **Step 4: Run loader and existing evaluation tests**

Run: `conda run -n MIAGuard python -m pytest tests/test_query_bank_judge_benchmark.py tests/test_judge_evaluation.py -q`

Expected: all tests pass.

### Task 3: Build the audited long-form score dataset

**Files:**
- Create: `src/miaguard/judge_score_dataset.py`
- Create: `tests/test_judge_score_dataset.py`

- [ ] **Step 1: Write failing tests for head expansion and unavailable session scores**

Construct one five-turn benign session and one five-turn IA session. Give turns 1–2 session status `insufficient_history` with logprob `0.1` and rubric `0.0`; give turns 3–5 status `ok`.

```python
table, audit = build_score_table(records)
assert len(table) == len(records) * 2
assert set(table["head"]) == {"rubric", "logprob"}
early = table[table["turn_index"].isin([1, 2])]
assert early["session_score_available"].eq(False).all()
assert early["x2_observed"].isna().all()
assert early["x2_raw"].notna().all()
late = table[table["turn_index"].isin([3, 4, 5])]
assert late["session_score_available"].eq(True).all()
assert audit["default_session_scores_excluded"] == 8
```

Add negative tests for duplicate `(query_id, session_key, turn_index)`, noncontiguous turns, mixed partition, mixed scoring identity, invalid attack/traffic pairing, nonfinite/out-of-range scores, and a session mixing document IDs.

- [ ] **Step 2: Run and verify import failure**

Run: `conda run -n MIAGuard python -m pytest tests/test_judge_score_dataset.py -q`

Expected: collection fails because `miaguard.judge_score_dataset` does not exist.

- [ ] **Step 3: Implement validation and expansion**

Expose:

```python
SCORE_HEADS = ("rubric", "logprob")
ATTACK_TYPES = ("direct_rag_mia", "s2_mia", "masked_mia", "ia")


def build_score_table(
    records: Sequence[Mapping[str, Any]],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Validate one partition and return two rows per query, one per score head."""
```

Each table row must contain exactly these analysis fields:

```text
query_id, doc_id, session_key, turn_index, session_length, partition,
traffic_type, attack_type, label, membership_label, head,
x1, x2_raw, x2_observed, x2_filled, session_score_available,
query_status, session_status, scoring_identity_sha256
```

Use `session_trace.statuses.overall == "ok"` as the sole availability definition. Set `x2_observed=np.nan` and `x2_filled=0.0` when unavailable. Do not infer availability from numeric score values.

The audit must include record/head counts, unique docs/sessions/queries, class and attack counts, per-turn availability, per-head unavailable raw-score frequencies, duplicate checks, and the single source identity.

- [ ] **Step 4: Run dataset tests**

Run: `conda run -n MIAGuard python -m pytest tests/test_judge_score_dataset.py -q`

Expected: all tests pass.

### Task 4: Produce descriptive statistics and complementarity diagnostics

**Files:**
- Create: `src/miaguard/judge_score_analysis.py`
- Create: `tests/test_judge_score_analysis.py`

- [ ] **Step 1: Write failing tests for summaries**

Use a deterministic table where logprob x1/x2 are monotonically related and rubric scores contain ties.

```python
report = summarize_score_table(table, bootstrap_seed=17, bootstrap_replicates=20)
assert set(report["heads"]) == {"rubric", "logprob"}
assert report["heads"]["logprob"]["availability"]["turn_1"] == 0.0
assert report["heads"]["logprob"]["availability"]["turn_3"] == 1.0
assert report["heads"]["logprob"]["correlation"]["all"]["spearman"] == pytest.approx(1.0)
assert report["bootstrap"]["unit"] == "doc_id"
assert report["bootstrap"]["replicates"] == 20
```

Assert that each of benign, all-attack, and four attack types has count, missing rate, mean, standard deviation, median, IQR, and 5/25/75/95 percentiles for x1 and available x2.

- [ ] **Step 2: Run and verify failure**

Run: `conda run -n MIAGuard python -m pytest tests/test_judge_score_analysis.py -q`

Expected: collection fails because the module does not exist.

- [ ] **Step 3: Implement empirical summaries without Gaussian fitting**

Expose the exact API `summarize_score_table(table: pd.DataFrame, *, bootstrap_seed: int = 20260829, bootstrap_replicates: int = 1000) -> dict[str, Any]`.

Calculate Spearman with `scipy.stats.spearmanr` only on rows with available x2. If either vector is constant, emit `correlation=None` plus `reason="constant_input"`; do not emit NaN JSON. Bootstrap by sampling unique `doc_id` values with replacement and assigning draw suffixes before recomputing statistics.

- [ ] **Step 4: Run summary tests**

Run: `conda run -n MIAGuard python -m pytest tests/test_judge_score_analysis.py -q`

Expected: all tests pass.

### Task 5: Render the Stage A figures

**Files:**
- Modify: `src/miaguard/judge_score_analysis.py`
- Modify: `tests/test_judge_score_analysis.py`

- [ ] **Step 1: Add a failing figure-manifest test**

```python
manifest = render_score_figures(table, tmp_path / "figures")
expected = {
    "rubric_joint_density_triptych", "rubric_attack_enrichment_small_multiples",
    "rubric_marginal_frequency_map", "rubric_temporal_availability",
    "logprob_joint_density_triptych", "logprob_attack_enrichment_small_multiples",
    "logprob_marginal_frequency_map", "logprob_temporal_availability",
}
assert set(manifest) == expected
assert all(Path(item["png"]).is_file() for item in manifest.values())
assert all(Path(item["pdf"]).is_file() for item in manifest.values())
```

- [ ] **Step 2: Run and verify the missing-function failure**

Run: `conda run -n MIAGuard python -m pytest tests/test_judge_score_analysis.py::test_render_score_figures -q`

Expected: failure because `render_score_figures` is absent.

- [ ] **Step 3: Implement fixed, publication-readable figures**

Use Matplotlib's noninteractive `Agg` backend, 300 DPI PNG plus embedded-font vector PDF, fixed single/double-column dimensions, fixed axis limits `[0,1]`, identical bin edges across labels and heads, Okabe–Ito colorblind-safe colors, restrained gridlines, and no top/right spines. The result must remain readable at paper column size and must not use 3D or decorative effects. Required figures per head:

```text
joint_density_triptych              benign density / macro-balanced attack density / log2 ratio
attack_enrichment_small_multiples   four log2 ratios: each ground-truth attack vs benign
marginal_frequency_map              x1 and available-x2 group-normalized mass by traffic type
temporal_availability               x1/x2 summaries and x2 availability at turns 1..5
```

Use `doc_id`-balanced weights for benign and attack type → doc_id balanced weights for attack. Do not plot unavailable x2 at zero. For the density-ratio panels, hatch cells with fewer than five pooled observations and clip log2 ratios to a fixed range; do not interpret unsupported sparse cells.

- [ ] **Step 4: Run all analysis tests**

Run: `conda run -n MIAGuard python -m pytest tests/test_judge_score_analysis.py -q`

Expected: all tests pass and temporary figures are nonempty.

### Task 6: Add the Stage A workflow and hard review gate

**Files:**
- Create: `src/miaguard/query_bank/judge_score_workflow.py`
- Create: `scripts/analyze_judge_scores.py`
- Create: `tests/test_judge_score_workflow.py`

- [ ] **Step 1: Write failing workflow tests**

Test that `run_train_score_analysis`:

```python
result = run_train_score_analysis(run_dir, output_dir, bootstrap_replicates=20)
assert result["partition"] == "train"
assert (output_dir / "separability_dataset.parquet").is_file()
assert (output_dir / "score_audit.json").is_file()
assert (output_dir / "separability_report.json").is_file()
assert (output_dir / "figure_manifest.json").is_file()
assert (output_dir / "run_manifest.json").is_file()
assert result["stage_a_status"] == "awaiting_human_review"
```

Assert a non-train input fails, an existing output directory fails without overwrite, and a tampered source record fails hash verification.

- [ ] **Step 2: Run and verify failure**

Run: `conda run -n MIAGuard python -m pytest tests/test_judge_score_workflow.py -q`

Expected: collection fails because the workflow module does not exist.

- [ ] **Step 3: Implement atomic artifact generation**

Expose the exact API `run_train_score_analysis(run_dir: Path, output_dir: Path, *, bootstrap_seed: int = 20260829, bootstrap_replicates: int = 1000) -> dict[str, Any]`.

Load with `load_verified_judge_records`, require manifest partition `train`, write to a sibling temporary directory, hash every final artifact, write the manifest last, and atomically rename the directory. The manifest must set:

```json
{
  "schema_version": 1,
  "stage": "score_separability",
  "stage_a_status": "awaiting_human_review",
  "classifier_training_authorized": false
}
```

The CLI accepts only `--run-dir`, `--output-dir`, `--bootstrap-seed`, and `--bootstrap-replicates`; it has no validation/test option.

- [ ] **Step 4: Run workflow and parser tests**

Run: `conda run -n MIAGuard python -m pytest tests/test_judge_score_workflow.py -q`

Expected: all tests pass.

- [ ] **Step 5: Run Stage A on the completed training Judge output**

Run:

```powershell
$judgeRun = 'D:\Project\MIAGuard\data\progressive_judge_v2_verifier_contract_development_all_queries_qwen2_5_7b_bf16_20260827\train'
$analysisOut = 'D:\Project\MIAGuard\data\judge_score_analysis_20260829\train'
conda run -n MIAGuard python scripts\analyze_judge_scores.py --run-dir $judgeRun --output-dir $analysisOut --bootstrap-seed 20260829 --bootstrap-replicates 1000
```

Expected: 3,575 source queries, 7,150 long-form head rows, 60 unique documents, both heads present, zero invalid rows, and status `awaiting_human_review`. Treat these counts as assertions derived from the frozen run, not values to silently repair.

- [ ] **Step 6: Stop and review Stage A before Task 7**

Review the binary plots first, then the four attack panels, availability by turn, score ties, Spearman intervals, and whether attacks occupy regions not occupied by benign traffic. Record a signed-off decision file `stage_a_review.json` containing the Stage A manifest SHA256 and exactly one decision:

```json
{"decision": "proceed", "reason": "Both heads show measurable train-only separation; grouped OOF comparison is warranted."}
```

or:

```json
{"decision": "stop", "reason": "The existing Judge scores do not provide enough separation to justify a fusion classifier."}
```

Task 7 must refuse to run unless the decision is `proceed` and its manifest hash matches.

### Task 7: Create deterministic document-grouped folds and fixed model candidates

**Files:**
- Create: `src/miaguard/judge_score_fusion.py`
- Create: `tests/test_judge_score_fusion.py`

- [ ] **Step 1: Write failing fold-isolation tests**

```python
folds = make_grouped_folds(table, n_splits=5, seed=20260829)
assert sorted(folds["fold"].unique()) == [0, 1, 2, 3, 4]
assert folds.groupby("doc_id")["fold"].nunique().max() == 1
for fold in range(5):
    held_out = table.merge(folds[folds["fold"] == fold], on="doc_id")
    assert set(held_out["label"]) == {0, 1}
    assert set(held_out.loc[held_out["label"] == 1, "attack_type"]) == set(ATTACK_TYPES)
```

Run: `conda run -n MIAGuard python -m pytest tests/test_judge_score_fusion.py::test_grouped_folds -q`

Expected: import failure.

- [ ] **Step 2: Implement and persist the folds**

Use `StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=20260829)` with `groups=doc_id`. Because each document contains mixed traffic, validate each resulting fold explicitly rather than assuming stratification succeeded. Return one row per doc with `fold`; the workflow will persist it as `fold_assignments.json`.

- [ ] **Step 3: Write failing candidate-definition tests**

```python
models = build_candidate_models(seed=20260829)
assert set(models) == {"x1_logistic", "x2_available_logistic", "legacy_0_4_0_6", "fusion_logistic", "depth2_tree", "shallow_mlp"}
assert models["depth2_tree"].max_depth == 2
assert models["shallow_mlp"].hidden_layer_sizes == (4,)
assert models["shallow_mlp"].activation == "relu"
```

- [ ] **Step 4: Implement fixed candidates**

Use these predeclared estimators:

```python
Pipeline([("scale", StandardScaler()),
          ("model", LogisticRegression(C=1.0, penalty="l2", solver="lbfgs", max_iter=2000,
                                       random_state=seed))])

DecisionTreeClassifier(max_depth=2, min_samples_leaf=20,
                       random_state=seed)

Pipeline([("scale", StandardScaler()),
          ("model", MLPClassifier(hidden_layer_sizes=(4,), activation="relu", solver="lbfgs",
                                  alpha=1.0, max_iter=2000, random_state=seed))])
```

`fusion_logistic`, tree, and MLP use `[x1, x2_filled, session_score_available]`. `x1_logistic` uses `[x1]`. `x2_available_logistic` uses `[x2_observed]` and only available rows, so it is diagnostic and never a global deployment candidate.

For every learned candidate, compute fold-local hierarchical sample weights with total mass 0.5 for benign and 0.125 for each of the four attacks; within a traffic/attack group divide mass equally across documents, then equally across that document's rows. Normalize weights to mean 1 before fitting. Pass them as `model__sample_weight` for pipelines and `sample_weight` for the tree. Add tests proving IA row count does not change its total training weight and no held-out label contributes to weights.

Implement `legacy_0_4_0_6` exactly from `RiskAggregator`: coverage is `min(1, turn_index/5)`, effective session weight is `0.6*coverage`, base is the normalized weighted average using raw x2, and output is `max(x1, base)`. It is a fixed score baseline, not a fitted model.

- [ ] **Step 5: Run model-definition tests**

Run: `conda run -n MIAGuard python -m pytest tests/test_judge_score_fusion.py -q`

Expected: fold and candidate tests pass.

### Task 8: Generate OOF predictions for both score heads

**Files:**
- Modify: `src/miaguard/judge_score_fusion.py`
- Modify: `tests/test_judge_score_fusion.py`

- [ ] **Step 1: Add failing OOF tests**

```python
oof = generate_oof_predictions(table, folds, seed=20260829)
global_rows = oof[oof["model_id"] != "x2_available_logistic"]
expected = len(table[table["head"] == "rubric"]) * 2 * 5
assert len(global_rows) == expected
assert not global_rows.duplicated(["query_id", "session_key", "head", "model_id"]).any()
assert global_rows["probability"].between(0, 1).all()
assert set(oof["head"]) == {"rubric", "logprob"}
assert oof.groupby(["head", "model_id"])["held_out_fold"].nunique().min() == 5
```

The factor is two heads times five global candidates (`x1`, legacy, logistic fusion, tree, MLP). Add a spy estimator test proving every prediction came from a model not fitted on the row's doc.

- [ ] **Step 2: Run and verify failure**

Run: `conda run -n MIAGuard python -m pytest tests/test_judge_score_fusion.py::test_oof_predictions_are_complete_and_group_isolated -q`

Expected: failure because `generate_oof_predictions` is absent.

- [ ] **Step 3: Implement fold-local fitting**

For each head, model, and held-out fold, fit on all other documents and predict the held-out documents. Never rebalance by duplicating rows. Compute the fixed hierarchical sample weights from the training fold only. Persist these fields:

```text
query_id, doc_id, session_key, turn_index, traffic_type, attack_type, label,
head, model_id, held_out_fold, probability, session_score_available
```

For a non-probabilistic baseline, store its continuous score as `probability` but mark `score_kind="uncalibrated_risk"`; learned classifiers use `score_kind="predicted_probability"`.

- [ ] **Step 4: Run all fusion tests**

Run: `conda run -n MIAGuard python -m pytest tests/test_judge_score_fusion.py -q`

Expected: all current tests pass.

### Task 9: Compare models and select one OOF threshold

**Files:**
- Modify: `src/miaguard/judge_score_fusion.py`
- Modify: `tests/test_judge_score_fusion.py`

- [ ] **Step 1: Write failing metric and selection tests**

Use synthetic OOF predictions where one model is superior at 5% FPR but not necessarily in accuracy.

```python
report = compare_oof_candidates(oof, fpr_caps=(0.01, 0.02, 0.05, 0.10), primary_fpr_cap=0.05)
assert report["selection"]["fpr_cap"] == 0.05
assert report["selection"]["objective"] == [
    "maximize_macro_document_balanced_attack_recall",
    "maximize_minimum_document_balanced_attack_recall",
    "minimize_benign_query_fpr",
    "prefer_simpler_model",
]
assert report["selection"]["threshold_source"] == "train_grouped_oof"
assert set(report["models"]["logprob"]["fusion_logistic"]["operating_points"]) == {"1", "2", "5", "10"}
```

Add a tie test proving `fusion_logistic` is preferred to tree/MLP when metrics are equal, and a test proving no candidate is selected if every nontrivial threshold violates the cap or gives zero recall to one attack type.

- [ ] **Step 2: Run and verify failure**

Run: `conda run -n MIAGuard python -m pytest tests/test_judge_score_fusion.py::test_oof_selection_uses_low_fpr_macro_objective -q`

Expected: failure because the comparison function is absent.

- [ ] **Step 3: Implement metrics and threshold search**

For every head/model compute AUROC, PR-AUC, ROC arrays, PR arrays, score cardinality/tie mass, and operating points at all four caps. At an operating point:

1. enumerate `+inf`, every unique score descending, and `nextafter(min_score, -inf)`;
2. keep thresholds with benign query FPR at or below the cap;
3. compute query recall within each `(attack_type, doc_id)`, average documents within attack type, then compute macro and minimum across four attacks;
4. rank by macro recall, minimum recall, negative FPR, and higher threshold;
5. label the all-negative point infeasible if every attack recall is zero.

Use a predeclared simplicity rank: `x1_logistic`, `fusion_logistic`, `depth2_tree`, `shallow_mlp`. `fusion_logistic` is eligible over x1-only only when its paired doc-bootstrap macro-recall improvement at the primary FPR cap has a lower 95% bound above zero without reducing minimum attack recall. Tree/MLP are eligible over fusion logistic only under the same stable-improvement rule. `legacy_0_4_0_6` remains a baseline and cannot win deployment selection. `x2_available_logistic` is subset-only and cannot win.

Generate OOF ROC, low-FPR zoomed ROC, and PR curves for both heads, plus available-session 2D decision-boundary panels for logistic, depth-2 tree, and MLP. Decision-boundary figures must state that they are descriptive full-train refits; all reported selection metrics remain OOF.

Bootstrap paired model differences by resampling doc IDs 1,000 times and recomputing metrics at each model's fixed OOF-selected threshold. Report percentile 95% intervals for differences; do not retrain models inside the bootstrap.

- [ ] **Step 4: Run fusion tests**

Run: `conda run -n MIAGuard python -m pytest tests/test_judge_score_fusion.py -q`

Expected: all tests pass.

### Task 10: Add the train-only fusion workflow and freeze artifact

**Files:**
- Modify: `src/miaguard/query_bank/judge_score_workflow.py`
- Create: `scripts/train_judge_score_fusion.py`
- Modify: `tests/test_judge_score_workflow.py`

- [ ] **Step 1: Write failing authorization and output tests**

Assert training refuses a missing/mismatched Stage A review, a `stop` decision, and any source partition other than train. For a valid review:

```python
result = train_and_freeze_score_fusion(analysis_dir, review_path, output_dir, bootstrap_replicates=20)
assert result["partition"] == "train"
assert result["threshold_source"] == "train_grouped_oof"
assert (output_dir / "fold_assignments.json").is_file()
assert (output_dir / "oof_predictions.parquet").is_file()
assert (output_dir / "model_comparison.json").is_file()
assert (output_dir / "selected_model.joblib").is_file()
assert (output_dir / "threshold_selection.json").is_file()
assert (output_dir / "frozen_manifest.json").is_file()
```

- [ ] **Step 2: Run and verify failure**

Run: `conda run -n MIAGuard python -m pytest tests/test_judge_score_workflow.py -q`

Expected: failure because training workflow is absent.

- [ ] **Step 3: Implement training and freezing**

Run OOF comparison first. If selection is infeasible, write a diagnostic report with `status="infeasible"` and do not write a model or threshold. If feasible, refit only the selected head/model on every train document and serialize with `joblib.dump`.

The frozen manifest must include hashes for source Judge records, Stage A manifest/review, fold assignments, OOF predictions, model comparison, serialized model, and threshold selection; it must also include exact feature order, fill rule, estimator parameters, scikit-learn version, Python version, seeds, selected head/model, and threshold.

The CLI must require `--analysis-dir`, `--stage-a-review`, and a new `--output-dir`. It may expose bootstrap counts/seeds, but not a flag that changes candidate architecture, primary FPR cap, model ranking, or legacy weights.

- [ ] **Step 4: Run workflow tests**

Run: `conda run -n MIAGuard python -m pytest tests/test_judge_score_workflow.py tests/test_judge_score_fusion.py -q`

Expected: all tests pass.

- [ ] **Step 5: Run Stage B only after Stage A review**

Run:

```powershell
$analysisDir = 'D:\Project\MIAGuard\data\judge_score_analysis_20260829\train'
$reviewPath = Join-Path $analysisDir 'stage_a_review.json'
$fusionOut = 'D:\Project\MIAGuard\data\judge_score_fusion_20260829\train'
conda run -n MIAGuard python scripts\train_judge_score_fusion.py --analysis-dir $analysisDir --stage-a-review $reviewPath --output-dir $fusionOut --bootstrap-seed 20260829 --bootstrap-replicates 1000
```

Expected: one train-selected scoring head, one train-selected model, one OOF-selected global threshold, and a fully hashed frozen manifest. If status is infeasible, stop; do not modify the FPR cap after looking at validation.

### Task 11: Apply the frozen detector to validation without refitting

**Files:**
- Modify: `src/miaguard/query_bank/judge_score_workflow.py`
- Create: `scripts/validate_judge_score_fusion.py`
- Modify: `tests/test_judge_score_workflow.py`

- [ ] **Step 1: Write failing locked-validation tests**

```python
result = validate_frozen_score_fusion(validation_run_dir, frozen_dir, output_dir, bootstrap_replicates=20)
assert result["partition"] == "validation"
assert result["selected_head"] == frozen_manifest["selected_head"]
assert result["selected_model"] == frozen_manifest["selected_model"]
assert result["threshold"] == frozen_manifest["threshold"]
assert result["model_refit"] is False
assert result["threshold_reselected"] is False
```

Assert failure for identity-core mismatch, record hash mismatch, missing attack type, test partition, changed feature order, changed sklearn version without explicit compatibility handling, and an output directory that already exists.

- [ ] **Step 2: Run and verify failure**

Run: `conda run -n MIAGuard python -m pytest tests/test_judge_score_workflow.py::test_validation_uses_frozen_model_and_threshold -q`

Expected: failure because validation workflow is absent.

- [ ] **Step 3: Implement locked validation**

Load and hash-check the frozen artifacts, verify train/validation identity cores match except partition, build exactly the selected head's feature matrix, call only `model.predict_proba`, and apply the frozen threshold. Report:

```text
benign query FPR, benign session FPR, AUROC, PR-AUC, precision, F1,
per-attack document-balanced query recall, macro recall, minimum recall,
per-attack session recall, first detection turn, and doc-bootstrap intervals
```

Also report both scoring heads' predeclared score-only descriptive metrics as an ablation, but do not fit them or select from them on validation.

The CLI parser must accept only `validation` through the verified run manifest and explicitly reject test. Final test execution remains locked until validation has been reviewed and a separate test-only plan is approved.

- [ ] **Step 4: Run locked-validation tests**

Run: `conda run -n MIAGuard python -m pytest tests/test_judge_score_workflow.py -q`

Expected: all tests pass.

### Task 12: Document the experiment and run full verification

**Files:**
- Create: `docs/JUDGE_SCORE_SEPARABILITY_EXPERIMENT_ZH.md`
- Modify: `README.md`

- [ ] **Step 1: Write the Chinese protocol document**

Document the binary task, two parallel score heads, x2 availability semantics, Stage A figures, attack-type diagnostic role, grouped OOF, all six candidates, no-Gaussian assumption, no-accuracy threshold rule, 1/2/5/10% operating points, Stage A human gate, validation lock, output schemas, and exact PowerShell commands.

- [ ] **Step 2: Add one README link**

Add `LLM-as-Judge 双分数可分性、学习融合与阈值实验` under the existing detailed-document list, linking to the new protocol.

- [ ] **Step 3: Run focused tests**

Run:

```powershell
conda run -n MIAGuard python -m pytest tests\test_analysis_dependencies.py tests\test_query_bank_judge_benchmark.py tests\test_judge_score_dataset.py tests\test_judge_score_analysis.py tests\test_judge_score_fusion.py tests\test_judge_score_workflow.py -q
```

Expected: all focused tests pass.

- [ ] **Step 4: Run the full suite**

Run: `conda run -n MIAGuard python -m pytest -q`

Expected: the existing baseline of `362 passed, 1 skipped` plus the newly added tests, with zero failures.

- [ ] **Step 5: Verify the CLI contracts without writing experiment outputs**

Run:

```powershell
conda run -n MIAGuard python scripts\analyze_judge_scores.py --help
conda run -n MIAGuard python scripts\train_judge_score_fusion.py --help
conda run -n MIAGuard python scripts\validate_judge_score_fusion.py --help
```

Expected: each exits 0; only the analysis command accepts train inputs, only the validation command accepts validation artifacts, and none offers a test-partition or overwrite flag.

## Execution checkpoints

1. Tasks 1–6 produce Stage A only. Stop and inspect the real distributions.
2. A matching `stage_a_review.json` with `decision=proceed` authorizes Tasks 7–10.
3. Stage B must end with either an immutable frozen artifact or an explicit infeasible result.
4. Task 11 evaluates validation once without modifying the frozen artifact.
5. Test remains inaccessible in this plan. A later plan may unlock it only after the validation report and frozen-manifest hashes are accepted.
