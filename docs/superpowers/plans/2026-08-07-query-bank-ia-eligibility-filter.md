# Query Bank IA Eligibility Filter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent frozen-query experiments from selecting documents whose IA records cannot support the sampler's balanced `yes`/`no` turn allocation, then run and validate 10+10 before a larger experiment.

**Architecture:** Add one private IA-capacity predicate in `sampler.py` and include it in the existing document eligibility filter before seeded shuffling. Keep `_choose_ia`, query-bank validation, record formats, and seeded selection unchanged. Exercise the behavior through the public `sample_query_bank` API.

**Tech Stack:** Python 3.10, pytest, existing MIAGuard query-bank storage and sampling modules, PowerShell experiment launcher.

---

### Task 1: Add IA eligibility regression coverage

**Files:**
- Modify: `tests/test_query_bank.py`
- Test: `tests/test_query_bank.py`

- [ ] **Step 1: Add test helpers for replacing IA labels and building a bank**

```python
def _replace_ia_answers(rows: list[dict], answers: tuple[str, ...]) -> None:
    ia_rows = [row for row in rows if row["attack_type"] == "ia"]
    for index, row in enumerate(ia_rows):
        row["payload"]["ground_truth"] = answers[index % len(answers)]


def _bank_with_ia_answers(
    tmp_path: Path,
    documents_with_answers: list[tuple[str, int, tuple[str, ...]]],
) -> QueryBank:
    paths = QueryBankPaths(tmp_path, "bank-1", "ag_news")
    documents = []
    for doc_id, membership_label, answers in documents_with_answers:
        documents.append(
            {
                "dataset_id": "ag_news",
                "doc_id": doc_id,
                "membership_label": membership_label,
                "source_document_sha256": document_sha256(f"source {doc_id}"),
            }
        )
        rows = _document_records(doc_id, membership_label)
        _replace_ia_answers(rows, answers)
        write_document_shard(paths, doc_id, rows)
    digest = compact_query_bank(paths, documents)
    write_json_atomic(
        paths.manifest,
        {
            "bank_id": "bank-1",
            "dataset_id": "ag_news",
            "status": "complete",
            "queries_sha256": digest,
        },
    )
    return QueryBank.load(paths)
```

- [ ] **Step 2: Add a failing test that requires ineligible documents to be skipped**

```python
def test_sampling_filters_documents_without_balanced_ia_capacity(tmp_path: Path) -> None:
    bank = _bank_with_ia_answers(
        tmp_path,
        [
            ("member-ineligible", 1, ("yes", "unknown")),
            ("member-0", 1, ("yes", "no", "unknown")),
            ("member-1", 1, ("yes", "no", "unknown")),
            ("nonmember-ineligible", 0, ("yes", "unknown")),
            ("nonmember-0", 0, ("yes", "no", "unknown")),
            ("nonmember-1", 0, ("yes", "no", "unknown")),
        ],
    )
    selection = sample_query_bank(
        bank,
        limit_per_class=2,
        benign_count=4,
        ia_turn_count=3,
        seed=17,
        variant_mode="canonical",
    )
    selected = selection["selected_doc_ids"]["ia"]
    assert "member-ineligible" not in selected
    assert "nonmember-ineligible" not in selected
```

- [ ] **Step 3: Add a failing test for insufficient eligible members**

```python
def test_sampling_reports_insufficient_ia_eligible_members(tmp_path: Path) -> None:
    bank = _bank_with_ia_answers(
        tmp_path,
        [
            ("member-ineligible", 1, ("yes", "unknown")),
            ("member-eligible", 1, ("yes", "no", "unknown")),
            ("nonmember-0", 0, ("yes", "no", "unknown")),
            ("nonmember-1", 0, ("yes", "no", "unknown")),
        ],
    )
    with pytest.raises(ValueError, match="enough member documents"):
        sample_query_bank(
            bank,
            limit_per_class=2,
            benign_count=4,
            ia_turn_count=3,
            seed=17,
            variant_mode="canonical",
        )
```

- [ ] **Step 4: Run the focused tests and confirm RED**

Run:

```powershell
conda run -n MIAGuard python -m pytest tests/test_query_bank.py -q
```

Expected: the new filtering tests fail because current eligibility checks only attack-type presence.

### Task 2: Implement strict pre-sampling IA filtering

**Files:**
- Modify: `src/miaguard/query_bank/sampler.py`
- Test: `tests/test_query_bank.py`

- [ ] **Step 1: Add the minimal capacity predicate**

```python
def _has_balanced_ia_capacity(
    records: list[dict[str, Any]], turn_count: int
) -> bool:
    lower = turn_count // 2
    upper = turn_count - lower
    counts = Counter(
        str(row["payload"]["ground_truth"])
        for row in records
    )
    return counts["yes"] >= upper and counts["no"] >= upper
```

Import `Counter` from `collections`. Requiring `upper` of each label guarantees that either allocation chosen by `_choose_ia` is feasible.

- [ ] **Step 2: Include IA capacity in the existing eligibility filter**

```python
eligible = [
    document
    for document in bank.documents
    if set(records_by_doc[str(document["doc_id"])]) >= {*ATTACKS, "benign"}
    and _has_balanced_ia_capacity(
        records_by_doc[str(document["doc_id"])]["ia"], ia_turn_count
    )
]
```

- [ ] **Step 3: Run focused tests and confirm GREEN**

Run:

```powershell
conda run -n MIAGuard python -m pytest tests/test_query_bank.py -q
```

Expected: all query-bank tests pass.

- [ ] **Step 4: Run the full suite**

Run:

```powershell
conda run -n MIAGuard python -m pytest -q
```

Expected: 0 failures.

### Task 3: Verify the real bank and default 10+10 selection

**Files:**
- Read: `data/query_banks/ag_news_queries_v1/ag_news/manifest.json`
- Read: `scripts/run_full_10x10.ps1`

- [ ] **Step 1: Revalidate the frozen bank**

Run:

```powershell
conda run -n MIAGuard python scripts/query_bank/validate_query_bank.py --bank-id ag_news_queries_v1 --dataset ag_news
```

Expected: `status` is `valid`, `document_count` is 100, and `query_count` is 5000.

- [ ] **Step 2: Run a model-free default selection check**

Load `QueryBank`, call `sample_query_bank` with `limit_per_class=10`, `benign_count=20`, `ia_turn_count=3`, `seed=20260725`, and `variant_mode="canonical"`, then assert ten selected member and ten selected nonmember IA documents.

Expected: selection succeeds without `Query Bank does not have enough balanced IA queries`.

### Task 4: Run and validate the 10+10 experiment

**Files:**
- Execute: `scripts/run_full_10x10.ps1`
- Create at runtime: `data/two_stage_attack_results/20260807-ag-news-query-bank-10x10-filtered-v1/ag_news/`
- Create at runtime: `data/experiment_logs/20260807-ag-news-query-bank-10x10-filtered-v1.log`

- [ ] **Step 1: Start the official launcher with an unused output ID**

Run:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_full_10x10.ps1 `
  -OutputRunId 20260807-ag-news-query-bank-10x10-filtered-v1 `
  -QueryBankId ag_news_queries_v1 `
  -QuerySeed 20260725
```

- [ ] **Step 2: Wait for completion and check the process exit code**

Expected: launcher prints `Experiment completed successfully` and exits 0.

- [ ] **Step 3: Validate result artifacts**

Check `run_manifest.json`, `query_selection_manifest.json`, and metrics files. Assert `status="completed"`, `query_bank_id="ag_news_queries_v1"`, `online_query_generation=false`, 10 members plus 10 nonmembers per attack, and finite metric values.

### Task 5: Define and run the larger experiment

**Files:**
- Read: 10+10 result artifacts from Task 4
- Create at runtime: a new result directory with a distinct run ID

- [ ] **Step 1: Derive the safe cohort ceiling**

Count eligible member and nonmember documents with the same predicate used by the sampler. For the current bank and three IA turns, the observed strict-filter pools are expected to be 33 members and 32 nonmembers.

- [ ] **Step 2: Select the large-run size**

Use the largest balanced cohort supported by both classes (`limit_per_class=32`) unless the user specifies a smaller operational cap after reviewing the 10+10 duration and metrics. Set `benign_count=64`, `ia_turn_count=3`, `query_seed=20260725`, and `variant_mode=canonical`.

- [ ] **Step 3: Run only after Task 4 passes**

Invoke `scripts/run_two_stage_attack_comparison.py` with output ID `20260807-ag-news-query-bank-32x32-filtered-v1` and the parameters above.

- [ ] **Step 4: Validate the large-run artifacts using the same checks as Task 4**

Expected: completed manifest, frozen query-bank identity, offline query generation, 32 members plus 32 nonmembers per attack, and finite metrics.
