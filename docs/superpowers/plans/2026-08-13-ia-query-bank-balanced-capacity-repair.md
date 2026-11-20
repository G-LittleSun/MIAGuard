# IA Query Bank 平衡容量增量修复 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 `ag_news_queries_v1/ag_news` 的每篇文档都拥有至少 15 条已验证的 `yes` IA 查询和至少 15 条已验证的 `no` IA 查询，同时保留所有既有查询（包括 `unknown`）。

**Architecture:** 在构建器中抽出可按目标标签生成和验证 IA 候选的最小接口；新建库以 15 条 `yes` 加 15 条 `no` 的固定池构建，修复器则只为现有文档缺失的标签生成记录。修复器在内存中完成全部校验后，使用原子写入更新 `queries.jsonl`、按文档分片、清单和追加审计日志；任一文档不能修复则不发布任何数据文件。

**Tech Stack:** Python 3.10、pytest、现有 `ModelClient`、JSONL 原子写入工具、Query Bank storage/validator。

---

## 文件结构

- 修改 `src/miaguard/query_bank/builder.py`：让 IA 候选生成可指定 `yes` 或 `no` 目标标签，并将新建文档的 30 条 IA 查询固定为 15+15。
- 新建 `src/miaguard/query_bank/repair.py`：只生成缺口标签、建立追加记录、全量预校验、原子发布及审计数据。
- 修改 `src/miaguard/query_bank/validator.py`：允许 IA 总数大于 30，要求每篇至少 15 条 `yes` 和 15 条 `no`。
- 新建 `scripts/query_bank/repair_ia_query_bank.py`：参数化调用修复器；默认不支持删除或覆盖原查询。
- 修改 `tests/test_query_bank_builder.py`：覆盖新建池的 15+15 合约和按标签生成的拒收行为。
- 修改 `tests/test_query_bank.py`：覆盖“追加后通过验证、旧记录字节语义保持、30 轮严格 15+15 抽样”。
- 新建 `tests/test_query_bank_repair.py`：用确定性假模型覆盖仅补缺口、审计日志、失败不发布、修复后可采样。
- 修改 `tests/test_query_bank_scripts.py`：将 repair CLI 纳入 `--help` 合约。

### Task 1: 写入并验证平衡容量的文档合约

**Files:**
- Modify: `tests/test_query_bank.py`
- Modify: `src/miaguard/query_bank/validator.py`

- [ ] **Step 1: 写失败测试，说明 15+15 是每篇文档的最小 IA 合约**

```python
def test_document_validation_requires_fifteen_yes_and_no_ia_answers() -> None:
    rows = _document_records("doc-1", 1)

    with pytest.raises(ValueError, match="at least 15 yes and 15 no"):
        validate_document_records(
            rows,
            {
                "dataset_id": "ag_news",
                "doc_id": "doc-1",
                "membership_label": 1,
                "source_document_sha256": document_sha256("source doc-1"),
            },
        )
```

- [ ] **Step 2: 运行测试确认它因旧的三标签 10+10+10 规则而失败**

Run: `conda run -n rag_env python -m pytest tests/test_query_bank.py::test_document_validation_requires_fifteen_yes_and_no_ia_answers -v`

Expected: FAIL，因为 `validate_document_records()` 接受旧的 10/10/10 分布。

- [ ] **Step 3: 实现最小验证规则**

```python
IA_MIN_ANSWER_COUNTS = {"yes": 15, "no": 15}

# validate_document_records() 中，保留非 IA 攻击的固定计数校验，
# IA 攻击改为至少 30 条；随后逐项检查 IA_MIN_ANSWER_COUNTS。
if len(ia_rows) < sum(IA_MIN_ANSWER_COUNTS.values()):
    raise ValueError("Document must contain at least 30 IA answers")
if any(ia_answers[label] < required
       for label, required in IA_MIN_ANSWER_COUNTS.items()):
    raise ValueError("Document must contain at least 15 yes and 15 no IA answers")
```

同时将总数比较改为：先从 `counts` 取出 IA，再验证 `direct_rag_mia`、`s2_mia`、`masked_mia`、`benign` 仍分别等于 5，IA 至少 30。

- [ ] **Step 4: 运行测试确认通过**

Run: `conda run -n rag_env python -m pytest tests/test_query_bank.py::test_document_validation_requires_fifteen_yes_and_no_ia_answers -v`

Expected: PASS。

### Task 2: 让新建 Query Bank 也产生 15+15

**Files:**
- Modify: `tests/test_query_bank_builder.py`
- Modify: `src/miaguard/query_bank/builder.py`

- [ ] **Step 1: 写失败测试，声明新建文档的 IA 标签池固定为 15+15**

```python
assert Counter(
    row["payload"]["ground_truth"]
    for row in records if row["attack_type"] == "ia"
) == {"yes": 15, "no": 15}
```

并在假客户端中记录 `[IA_CANDIDATES]` 提示词，断言其中分别出现
`correct answer must be yes` 和 `correct answer must be no`。

- [ ] **Step 2: 运行构建器单测并确认失败**

Run: `conda run -n rag_env python -m pytest tests/test_query_bank_builder.py::test_build_document_records_creates_complete_teacher_aligned_pool -v`

Expected: FAIL，现有生成器接受 `unknown` 且结果为 10/10/10。

- [ ] **Step 3: 为 `_ia_candidates` 增加标签和既有问题参数**

```python
def _ia_candidates(
    text: str, build_config: QueryBankBuildConfig,
    attack_config: AttackConfig, client: ModelClient, *,
    target_count: int | None = None,
    required_answer: str | None = None,
    existing_questions: tuple[str, ...] = (),
) -> tuple[str, list[dict[str, str]]]:
```

初始化 `normalized` 时纳入 `existing_questions`。当 `required_answer` 是 `yes` 或 `no` 时，提示词加入 `The correct source-grounded answer must be {required_answer}.`，且只接受验证结果等于目标标签的候选；其他标签记入 `wrong_label_count`，不写入 `accepted`。`target_count` 缺省时仍使用 `build_config.ia_questions_per_document`。

- [ ] **Step 4: 在 `build_document_records()` 中连续获取两个标签池**

```python
yes_summary, yes_candidates = _ia_candidates(
    text, build_config, attack_config, client,
    target_count=15, required_answer="yes",
)
no_summary, no_candidates = _ia_candidates(
    text, build_config, attack_config, client,
    target_count=15, required_answer="no",
    existing_questions=tuple(item["question"] for item in yes_candidates),
)
summary = yes_summary or no_summary
ia_candidates = [*yes_candidates, *no_candidates]
```

保留既有 `_record()` 与稳定编号，最终编号 1–30；测试假客户端的验证输出调整为可为两种目标各提供 15 个对应标签。

- [ ] **Step 5: 运行构建器相关测试**

Run: `conda run -n rag_env python -m pytest tests/test_query_bank_builder.py -v`

Expected: PASS。

### Task 3: 测试先行实现只追加的修复器

**Files:**
- Create: `tests/test_query_bank_repair.py`
- Create: `src/miaguard/query_bank/repair.py`

- [ ] **Step 1: 写失败测试，覆盖只补缺失标签和不改既有记录**

```python
result = repair_ia_query_bank(
    tmp_path, "bank-1", "ag_news", attack_config_path,
    client=_DeterministicRepairClient(), seed=17,
)
after = list(read_jsonl(paths.queries))
assert result["repaired_document_count"] == 1
assert after[:len(before)] == before
assert Counter(
    row["payload"]["ground_truth"]
    for row in after if row["doc_id"] == "doc-1" and row["attack_type"] == "ia"
) == {"yes": 15, "no": 15, "unknown": 10}
```

另写两个独立测试：`test_repair_writes_audit_log_for_each_changed_document` 断言 audit 具有旧/新计数、追加 ID、目标、seed、time；`test_repair_failure_leaves_queries_and_manifest_unchanged` 令模型不能获得目标标签，比较修复前后 `queries.jsonl` 与 `manifest.json` 的原始字节。

- [ ] **Step 2: 运行修复器单测确认模块缺失而失败**

Run: `conda run -n rag_env python -m pytest tests/test_query_bank_repair.py -v`

Expected: FAIL，导入 `miaguard.query_bank.repair` 失败。

- [ ] **Step 3: 实现可预览且可原子发布的修复器**

```python
def repair_ia_query_bank(
    project_root: Path, bank_id: str, dataset_id: str,
    attack_config_path: Path, *, seed: int,
    client: ModelClient | None = None,
) -> dict[str, Any]:
```

实现顺序固定如下：

1. `QueryBank.load(paths)` 读取完成态银行，`load_run_documents()` 建立 `doc_id -> text` 映射；按文档分组并计算 `yes`、`no` 缺口。
2. 对每个有缺口的文档先在内存生成 `yes`，再生成 `no`；`existing_questions` 同时包含旧问题和已生成问题，下一索引为该文档现有 IA `query_index` 的最大值加一。
3. 用 builder 的 `_record()` 生成 `attack_type="ia"`、`variant_type="generated"`、`prompt_version="ia-query-repair-v1"` 的新记录，且 `generation.seed=seed`。只将验证标签等于当前缺口标签的记录加入待发布集合。
4. 将旧行和待追加行合并后，对每篇文档调用 `validate_document_records()`；同时检查 ID 唯一、问题规范化唯一，并验证每篇 `yes >= 15`、`no >= 15`。在此之前不得写正式文件。
5. 在 `QueryBankLock(paths)` 内将每篇完整记录写入其原 `.work` 分片，调用 `compact_query_bank(paths, documents)`，计算新 SHA；最后原子写 `manifest.json`，更新 `query_count`、`queries_sha256`、`counts_by_attack`、`ia_answer_counts`、`ia_questions_per_document: "at_least_30"`、`updated_at`。
6. 追加写入 `ia_repair_log.jsonl`。每行包含 `doc_id`、`old_ia_answer_counts`、`new_ia_answer_counts`、`added_query_ids`、`requested_answers`、`seed`、`repaired_at`、`generation_model`。仅在主数据与清单成功发布后写此日志；日志失败应显式报错，保留已发布数据而不伪造成功。

- [ ] **Step 4: 运行修复器单测确认通过**

Run: `conda run -n rag_env python -m pytest tests/test_query_bank_repair.py -v`

Expected: PASS。

### Task 4: 暴露 CLI、抽样验收与真实数据修复

**Files:**
- Create: `scripts/query_bank/repair_ia_query_bank.py`
- Modify: `tests/test_query_bank_scripts.py`
- Modify: `tests/test_query_bank.py`

- [ ] **Step 1: 写失败的 CLI 帮助与 30 轮抽样测试**

```python
@pytest.mark.parametrize("script", (
    "scripts/query_bank/repair_ia_query_bank.py",
))
def test_query_bank_script_help(script: str) -> None:
    ...

selection = sample_query_bank(
    repaired_bank, limit_per_class=1, benign_count=1,
    ia_turn_count=30, seed=17, variant_mode="canonical",
)
assert all(Counter(q["ground_truth"] for q in row["queries"]) ==
           {"yes": 15, "no": 15}
           for row in selection["attacks"]["ia"])
```

- [ ] **Step 2: 运行两个测试确认失败**

Run: `conda run -n rag_env python -m pytest tests/test_query_bank_scripts.py tests/test_query_bank.py::test_sampling_uses_fifteen_yes_and_no_for_thirty_turns -v`

Expected: FAIL，repair CLI 不存在且修复测试夹具尚未满足新验证合约。

- [ ] **Step 3: 实现 CLI**

```python
parser.add_argument("--bank-id", required=True)
parser.add_argument("--dataset", required=True)
parser.add_argument("--attack-config", required=True)
parser.add_argument("--project-root", default=".")
parser.add_argument("--seed", type=int, default=20260813)
```

调用 `repair_ia_query_bank()` 并以 UTF-8 JSON 打印结果；不提供删除、替换、缩减或覆盖旧查询的参数。

- [ ] **Step 4: 执行定向回归**

Run: `conda run -n rag_env python -m pytest tests/test_query_bank.py tests/test_query_bank_builder.py tests/test_query_bank_repair.py tests/test_query_bank_scripts.py -v`

Expected: PASS。

- [ ] **Step 5: 审计真实数据，再执行修复**

Run: `conda run -n rag_env python scripts/query_bank/inspect_query_bank.py --bank-id ag_news_queries_v1 --dataset ag_news --project-root .`

记录修复前 SHA 与每篇 IA 标签分布。

Run: `conda run -n rag_env python scripts/query_bank/repair_ia_query_bank.py --bank-id ag_news_queries_v1 --dataset ag_news --attack-config configs/attacks/ag_news_calibrated_int8.yaml --project-root . --seed 20260813`

Expected: 输出已修复文档数、追加条数、新 SHA 和审计日志路径；旧记录不被删除。

- [ ] **Step 6: 验证修复后的真实数据及完整 15+15 抽样**

Run: `conda run -n rag_env python scripts/query_bank/validate_query_bank.py --bank-id ag_news_queries_v1 --dataset ag_news --project-root .`

Run: `conda run -n rag_env python -c "from pathlib import Path; from miaguard.query_bank.storage import QueryBank, QueryBankPaths; from miaguard.query_bank.sampler import sample_query_bank; from collections import Counter; b=QueryBank.load(QueryBankPaths(Path('.').resolve(),'ag_news_queries_v1','ag_news')); s=sample_query_bank(b,limit_per_class=50,benign_count=100,ia_turn_count=30,seed=20260813,variant_mode='canonical'); assert all(Counter(q['ground_truth'] for q in r['queries'])=={'yes':15,'no':15} for r in s['attacks']['ia']); print('100 docs sampled, every IA turn set is 15 yes + 15 no')"`

Expected: 验证器返回 `status: valid`；抽样输出确认 100 篇文档均能生成 15+15 轮次集合。

### Task 5: 最终回归与交付检查

**Files:**
- Verify only: `data/query_banks/ag_news_queries_v1/ag_news/queries.jsonl`
- Verify only: `data/query_banks/ag_news_queries_v1/ag_news/manifest.json`
- Verify only: `data/query_banks/ag_news_queries_v1/ag_news/ia_repair_log.jsonl`

- [ ] **Step 1: 运行完整测试套件**

Run: `conda run -n rag_env python -m pytest`

Expected: PASS；若沙盒阻止临时目录写入，则在已获授权的环境中重跑同一命令，并记录真实结果。

- [ ] **Step 2: 验证不修改实验产物**

Run: `Get-FileHash data/two_stage_attack_results/20260807-ag-news-query-bank-10x10-filtered-v1/ag_news/summary.json; Get-FileHash data/two_stage_attack_results/20260807-ag-news-query-bank-32x32-filtered-v1/ag_news/summary.json`

Expected: 两份历史实验结果仍在原路径；修复不运行实验、不写入这些目录。

- [ ] **Step 3: 检查审计完整性**

Run: `conda run -n rag_env python -c "from pathlib import Path; import json; p=Path('data/query_banks/ag_news_queries_v1/ag_news/ia_repair_log.jsonl'); rows=[json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x]; assert rows; assert all(set(('doc_id','old_ia_answer_counts','new_ia_answer_counts','added_query_ids','requested_answers','seed','repaired_at')) <= set(r) for r in rows); print(len(rows), 'repair audit rows verified')"`

Expected: 审计记录数量等于实际被修复的文档数，且每条都有可复现字段。

## 自检

- 规格覆盖：Task 1/2 统一未来构建与验证合约；Task 3 只追加、未知标签保留、原子发布和审计；Task 4 真实数据修复与 30 轮 15+15 抽样；Task 5 回归及历史实验不变检查。
- 占位符扫描：本文不含 `TBD`、`TODO`、`implement later` 或未展开的“适当处理”。
- 一致性：全程使用 `repair_ia_query_bank`、`IA_MIN_ANSWER_COUNTS`、`ia_repair_log.jsonl` 和 `ia-query-repair-v1` 这四个统一名称。

> 当前工作区不是 Git 仓库，因此本计划不含提交步骤；所有修改和数据发布均由定向测试与原子写入验证替代。
