# MIAGuard 防御框架递进实施路线

历史资料定位（2026-11-02 更新）：本文保留旧 Rule-only 与阶段二工作的路线和验收背景。当前访问控制开发以[进度台账](../DEFENSE_PROGRESS_ZH.md)指定的[主计划 v1.1](../superpowers/plans/2026-10-22-defense-framework-implementation.md)和[实验协议 v1.1](../DEFENSE_EXPERIMENT_PROTOCOL_ZH.md)执行，当前恢复点为 T10-D；下文旧阶段名称和待办不覆盖最新任务状态。

## 1. 融合后的阶段划分

原阶段 0“冻结攻击基线”、阶段 1“最小防御闭环”和阶段 2“统一事件与数据”合并为新的阶段一：

```text
阶段一：可追溯最小防御闭环
  → 阶段二：查询级检测增强
  → 阶段三：会话级检测增强
  → 阶段四：动态访问控制优化
  → 阶段五：多数据集正式评估
```

阶段一的目标不是得到最佳检测指标，而是使用同一批攻击样本完成下面的闭环：

```text
冻结攻击查询
  → 转换为统一事件
  → 加入正常查询
  → Rule-only 风险判断
  → allow/restrict/deny 访问动作
  → 重新执行 RAG 回答
  → 计算防御前后攻击指标和防御指标
```

## 2. 阶段一执行过程

### 2.1 冻结无防御基线

阶段一不重新生成四种攻击查询，而是读取现有攻击结果：

```text
data/attack_results/<source_run_id>/<dataset>/<attack>/results.jsonl
```

从每种攻击中按相同数量选择成员与非成员记录，并保存被选中的 `doc_id`。防御前后的实验使用完全相同的目标、查询、成员标签、模型和向量库。

当前默认基线为：

```text
source_run_id: 20260717-ag-news-four-medium
dataset: ag_news
```

### 2.2 生成统一查询事件

每条攻击查询和正常查询转换为 `schemas/defense_event.schema.json` 定义的事件，主要字段包括：

```text
event_id
source_record_id
source_framework
run_id / dataset_id
session_id / turn_id
query
attack_type
intent_label
membership_label
target_doc_id
retrieved_doc_ids / retrieval_scores
attack_metadata
```

`source_record_id` 可以映射回冻结的攻击结果。原始成员标签和攻击类型只用于评测，Rule-only 检测器的输入严格限制为：

```text
query
session_id
retrieved_doc_ids
```

### 2.3 加入正常查询

阶段一从同一次运行的成员和非成员文档中均衡抽取文档，生成确定性的主题概括问题。它们用于验证正常查询是否被误拦截。

这些正常查询只是 MVP 数据，不作为最终 benign 数据集。后续阶段还要补充自然问答、多轮正常会话和 hard negative。

### 2.4 Rule-only 风险识别

第一版只识别四类明显信号：

- 显式询问内容是否存在于 context、knowledge base 或 database；
- `[Mask_n]` 和局部内容恢复；
- 完成句子、续写或原文复现；
- IA 查询模板及同一会话反复命中同一检索文档。

总风险暂时使用：

```text
R_total = max(R_query, R_session)
```

阈值配置位于 `configs/defense/mvp.yaml`。

### 2.5 三档访问控制

| 风险级别 | MVP 动作 | 当前行为 |
|---|---|---|
| low | `allow` | 使用完整 top-k 上下文正常回答 |
| medium | `restrict_context` | 只保留第一个检索结果并截短上下文 |
| high | `deny_sensitive_answer` | 不向 LLM 提供检索上下文，返回安全模板 |

这些动作只用于打通接口。后续需要通过安全性和可用性实验决定是否保留。

### 2.6 防御前后回放评测

四种攻击使用各自原有的成员性评分方式：

- Direct：Yes/No；
- S²-MIA：语义相似度；
- Masked MIA：恢复词匹配率；
- IA：问题回答得分聚合。

同时计算攻击意图检测、正常查询误报率、访问动作分布和检索/决策延迟。

## 3. 阶段一运行命令

### 3.1 技术烟雾验证

每种攻击选择 1 个成员和 1 个非成员，并加入 2 条正常查询：

```powershell
conda activate MIAGuard
python scripts/run_defense_experiment.py `
  --config configs/attacks/ag_news_calibrated.yaml `
  --defense-config configs/defense/mvp.yaml `
  --source-run-id 20260717-ag-news-four-medium `
  --dataset ag_news `
  --output-run-id <new-smoke-run-id> `
  --limit-per-class 1 `
  --benign-count 2
```

### 3.2 阶段一标准 MVP

每种攻击选择 10 个成员和 10 个非成员，并加入 40 条正常查询：

```powershell
python scripts/run_defense_experiment.py `
  --config configs/attacks/teacher_local_smoke.yaml `
  --defense-config configs/defense/mvp.yaml `
  --source-run-id 20260717-ag-news-four-medium `
  --dataset ag_news `
  --output-run-id <new-mvp-run-id> `
  --limit-per-class 10 `
  --benign-count 40 `
  --offset-per-class 100
```

阈值校准使用每类第 1～100 条样本，标准 MVP 使用每类第 101～110 条样本，因此 `--offset-per-class 100` 不能省略。校准报告位于 `reports/ag_news_attack_threshold_calibration.json`。`output-run-id` 必须是新名称，已有目录不会被覆盖。

## 4. 输出文件

```text
data/defense_results/<output_run_id>/<dataset>/
├── run_manifest.json
├── query_events.jsonl
├── defense_decisions.jsonl
├── attack_metrics_before.json
├── attack_metrics_after.json
├── defense_metrics.json
└── summary.json
```

其中：

- `run_manifest.json`：基线运行、模型、样本 ID 和检测器版本；
- `query_events.jsonl`：统一查询事件和评测真值；
- `defense_decisions.jsonl`：风险、原因、动作、检索结果、回答和防御后分数；
- `attack_metrics_before/after.json`：同批样本的防御前后攻击指标；
- `defense_metrics.json`：攻击检测、正常误报、动作分布和前后对比；
- `summary.json`：本次运行的核心摘要。

## 5. 阶段一验收标准

### 5.1 工程闭环

- 四种攻击都经过同一个防御入口；
- 正常查询经过相同的检索、检测和访问控制流程；
- 一条命令可以生成全部七个输出文件；
- 防御关闭时的基线来自冻结结果，没有重新选择目标；
- 已存在的老师攻击代码和原始数据没有被覆盖。

### 5.2 数据完整性

- 每种攻击成员与非成员数量相等；
- 所有事件通过 `defense_event.schema.json`；
- 每条事件可以通过 `source_record_id` 或 `target_doc_id` 追溯；
- `attack_type` 和 `membership_label` 不进入检测器；
- 防御前后使用相同 `doc_id` 和攻击查询。

### 5.3 防御行为

- 每条查询都产生 `query_risk`、`session_risk` 和 `total_risk`；
- 每条查询都产生 low、medium 或 high 风险等级；
- 每条查询都执行 allow、restrict 或 deny 动作之一；
- 高风险查询不会获得原始检索上下文；
- 正常查询能够走完整的 allow 和回答流程；
- 防御前后攻击指标、benign 误报率和动作次数均可计算。

### 5.4 测试和运行

- 项目完整 pytest 通过；
- `pip check` 无损坏依赖；
- 固定源运行和样本数量后，选择的文档 ID 稳定；
- 技术烟雾运行成功不代表论文效果，只代表闭环可用；
- 只有完成 10+10 与 40 benign 的标准 MVP 后，才进入检测细节优化。

## 6. 当前验收记录

已完成技术烟雾运行：

```text
output_run_id: 20260720-ag-news-defense-mvp-smoke
attack events: 8
benign events: 2
benign allow rate: 1.0
macro attack accuracy before: 0.75
macro attack accuracy after: 0.625
pytest: 115 passed, 1 skipped
```

样本数太小，上述数值不能作为论文结论。它只能证明统一事件、风险判断、三档访问控制、本地模型回答和防御前后指标已经端到端运行成功。

第一次未校准的标准 MVP 保留为历史诊断运行：

```text
output_run_id: 20260720-ag-news-defense-mvp
问题: S²-MIA 和 Masked MIA 沿用固定阈值 0.7 / 0.5，防御前 Accuracy 偏低
状态: 已由独立校准版本取代，不再作为当前对照结果
```

当前有效的阶段一标准 MVP 使用独立阈值校准：

```text
output_run_id: 20260720-ag-news-defense-mvp-calibrated
threshold calibration: 前 100 member + 100 nonmember
evaluation offset: 100
attack events: 80（每种攻击 10 member + 10 nonmember）
benign events: 40（20 member + 20 nonmember）
schema-valid events: 120 / 120
calibration/evaluation overlap: 0
benign allow rate: 1.0
benign false positive rate: 0.0
macro attack accuracy before: 0.80
macro attack accuracy after: 0.6125
pytest: 119 passed, 1 skipped
pip check: no broken requirements
```

校准阈值：

```text
S²-MIA: 0.7 → 0.915322333574295
Masked MIA: 0.5 → 0.2
```

各攻击的准确率变化为：

| 攻击 | 防御前 | 防御后 | 当前结论 |
|---|---:|---:|---|
| Direct RAG-MIA | 0.95 | 0.50 | 固定拒绝使攻击降到随机水平 |
| S²-MIA | 0.65 | 0.50 | 校准后基线可用，防御降低 0.15；防御前 ROC-AUC 为 0.82 |
| Masked MIA | 0.70 | 0.50 | 校准后基线可用，防御降低 0.20；防御前 ROC-AUC 为 0.79 |
| IA | 0.90 | 0.95 | `restrict_context` 仍然轻微增强攻击，需要优先修正 |

IA 结果说明只保留 top-1 上下文可能让回答更集中、更容易与标准答案一致。该结果是阶段一闭环发现的问题，不应隐藏，也不应通过事后修改本次结果。下一阶段应将 IA 的访问动作作为第一个优化对象，并在独立验证集上比较无上下文回答、摘要化、延迟响应和会话升级后的拒绝策略。

## 7. 后续阶段

### 阶段二：IA 访问动作安全校正（已完成 MVP）

先固定当前 Rule-only 检测器，只比较 IA 的访问动作：top-1 截短、无检索上下文、摘要化上下文，以及会话风险升级后拒绝。使用新的独立验证样本选择策略，不能在当前 10+10 结果上事后挑选。验收要求 IA 攻击 Accuracy 不再高于无防御基线，同时记录 benign 通过率与回答质量。

当前验证集选择 `deny_sensitive_answer`。在独立留出集上 IA Accuracy 从0.80降至0.40，40条 benign 全部放行，策略验证集与留出集交集为0。详细结果见 `docs/STAGE2_IA_POLICY_EVALUATION_ZH.md`。当前阶段只完成MVP安全校正；IA-like合法查询的可用性评估并入阶段三。

### 阶段三：查询级检测增强（下一阶段）

依次比较 Rule-only、Embedding-only、Rule+Embedding 和按需 LLM Judge。验收重点是验证集上的 F1、AUROC、低 FPR 检测率和 hard negative 误报率。

当前困难查询基准已经证明 Rule-only 对关键词规避攻击的 Recall 为0，对 hard benign 的误报率为1.0。阶段三应以 `data/hard_query_results/20260720-ag-news-hard-queries/` 作为必须改进的基线，详细结果见 `docs/LARGE_AND_HARD_QUERY_EVALUATION_ZH.md`。

### 阶段四：会话级检测增强

构建多轮 IA 与 benign session，比较 `k = 3, 5, 10, 20`，加入主题一致性、检索集中度和跨目标重复结构。验收重点是 IA 检测增益与正常多轮会话误报。

### 阶段五：动态访问控制优化

比较拒绝、上下文截短、摘要化、隐藏来源和按模式选择动作。验收重点是攻击成功率下降、正常回答质量损失和额外延迟之间的平衡。

### 阶段六：正式评估

扩展到五个数据集、完整 baselines、消融、多随机种子、安全性、可用性和效率性评测，最终形成论文表格、图和错误案例分析。
