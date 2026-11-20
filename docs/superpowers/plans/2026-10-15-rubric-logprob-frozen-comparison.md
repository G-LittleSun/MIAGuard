# Rubric 与二分类 Logprob 对等测试 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让冻结融合评估支持 rubric 与 logprob，并输出两者可并列的验证/测试结果。

**Architecture:** 在 `judge_score_frozen.py` 的行筛选和模型冻结接口中加入显式评分头；冻结产物保存该字段，评估按该字段选择记录。CLI 增加 `--head`，默认值为 logprob，保持历史命令兼容。

**Tech Stack:** Python、pandas、scikit-learn、pytest。

---

### Task 1: 为 rubric 冻结行为建立回归测试

**Files:**
- Modify: `tests/test_judge_score_frozen.py`

- [ ] **Step 1: 写失败测试**

```python
def test_frozen_rubric_evaluation_uses_rubric_rows(tmp_path: Path) -> None:
    frozen = freeze_logistic_l2(
        _table("train", head="rubric"),
        {"0.01": {"threshold": 0.5}, "0.05": {"threshold": 0.4}},
        tmp_path / "rubric.json",
        head="rubric",
    )
    result = evaluate_frozen_fusion(_table("validation", head="rubric"), frozen)
    assert frozen["head"] == "rubric"
    assert result["partition"] == "validation"
```

- [ ] **Step 2: 运行并确认失败**

Run: `D:\ProgramData\Anaconda3\envs\MIAGuard\python.exe -m pytest tests/test_judge_score_frozen.py -q`

Expected: 失败，因为测试辅助函数和冻结接口尚不支持 rubric。

- [ ] **Step 3: 写评分头不匹配的失败测试**

```python
def test_frozen_evaluation_rejects_mismatched_score_head(tmp_path: Path) -> None:
    frozen = freeze_logistic_l2(_table("train"), _thresholds(), tmp_path / "frozen.json")
    with pytest.raises(ValueError, match="rubric"):
        evaluate_frozen_fusion(_table("validation", head="rubric"), frozen)
```

- [ ] **Step 4: 运行并确认失败**

Run: `D:\ProgramData\Anaconda3\envs\MIAGuard\python.exe -m pytest tests/test_judge_score_frozen.py -q`

Expected: 第二个测试失败，因为当前评估器未验证评分头一致性。

### Task 2: 最小化扩展冻结评估器

**Files:**
- Modify: `src/miaguard/judge_score_frozen.py`
- Test: `tests/test_judge_score_frozen.py`

- [ ] **Step 1: 将 `_rows` 增加 `head` 参数**

```python
def _rows(table: pd.DataFrame, partition: str, head: str) -> pd.DataFrame:
    rows = table.loc[(table["head"] == head) & table["session_score_available"].astype(bool)].copy()
    if rows.empty or set(rows["partition"]) != {partition}:
        raise ValueError(f"Expected available {head} rows from {partition}")
    return rows.reset_index(drop=True)
```

- [ ] **Step 2: 冻结与评估接口传递评分头**

```python
def freeze_logistic_l2(..., *, head: str = "logprob") -> dict[str, Any]:
    rows = _rows(table, "train", head)
    ...
    result["head"] = head

def evaluate_frozen_fusion(...):
    head = str(frozen.get("head", ""))
    rows = _rows(table, partition, head)
```

- [ ] **Step 3: 运行冻结评估测试**

Run: `D:\ProgramData\Anaconda3\envs\MIAGuard\python.exe -m pytest tests/test_judge_score_frozen.py -q`

Expected: 所有冻结评估测试通过。

### Task 3: 扩展命令行并生成 rubric 产物

**Files:**
- Modify: `scripts/validate_judge_score_fusion.py`
- Modify: `scripts/evaluate_frozen_test_judge_fusion.py`

- [ ] **Step 1: 增加 `--head` 参数，候选为 `rubric` 和 `logprob`，默认 logprob**

```python
parser.add_argument("--head", choices=("rubric", "logprob"), default="logprob")
```

- [ ] **Step 2: 用 `args.head` 选择阈值和冻结调用**

```python
frozen = freeze_logistic_l2(train, selections[args.head]["logistic_l2"], Path(args.frozen_output), head=args.head)
```

- [ ] **Step 3: 运行完整相关测试**

Run: `D:\ProgramData\Anaconda3\envs\MIAGuard\python.exe -m pytest tests/test_judge_score_frozen.py tests/test_judge_score_dataset.py -q`

Expected: 通过。

- [ ] **Step 4: 使用现有记录生成 rubric validation 和 test JSON**

Run validation 命令和 test 评估命令，均指定 `--head rubric`，输出到新的 `data/judge_score_*_v3_rubric_20261015/` 目录。

### Task 4: 汇总最终对比

**Files:**
- Create: `data/judge_score_comparison_v3_20261015/final_test_comparison.json`

- [ ] **Step 1: 从两份 test JSON 汇总共同指标**

将两个方案的概率指标、0.01 与 0.05 工作点、四类攻击召回和样本量写入同一 JSON；不得重新选择阈值。

- [ ] **Step 2: 核对可比性**

确认两种结果的 `documents`、`rows`、partition 均相同，再向用户给出最终对比表。
