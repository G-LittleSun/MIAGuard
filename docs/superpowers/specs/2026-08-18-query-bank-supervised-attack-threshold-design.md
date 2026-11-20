# AG News 查询库监督式攻击阈值校准设计

## 1. 背景与目标

MIAGuard 当前根据两阶段检测器输出的 `total_risk_score` 执行访问控制，但是否启动有效防御的阈值来自人工配置。旧校准流程还存在数据来源、会话组织和数据划分与当前冻结查询库不一致的问题，导致旧阈值不能直接用于正式实验。

本设计只学习一个攻击判定阈值：

```text
total_risk_score >= t_attack
```

满足条件时启动至少 L2 的有效防御；否则不启动有效防御。现有 L0-L4 其他严重程度阈值保持不变，本阶段不训练新的分类器，也不修改 LLM 风险评分模型。

核心目标如下：

1. 为当前 100 个目标文档建立查询库专用的 train/validation/test 划分。
2. 使用冻结查询库中的全部合格攻击和良性查询。
3. 为所有攻击类型和良性流量建立统一、无跨文档污染的会话规则。
4. 仅使用 train 分区监督选择 `t_attack`。
5. 使用 validation 固定阈值验证，使用 test 进行一次最终报告。
6. 保证阈值选择与正式有/无防御实验使用相同的数据和会话分布。

## 2. 实验边界与方案选择

采用固定 60/20/20 文档级划分和受良性误报约束的离线阈值搜索。该方案比两分法多保留一个最终测试集，比交叉验证更容易复现，也严格对应“训练集找阈值、验证集检查、测试集最终报告”的实验目标。

本阶段不采用以下方案：

- 不使用 validation 或 test 重新搜索阈值。
- 不训练逻辑回归、树模型或神经网络分类器。
- 不为四种攻击分别设置运行时阈值。
- 不同时学习全部 L0-L4 边界。
- 不继续用 `offset_per_class` 代表实验分区。

## 3. 模块与数据流设计

### 3.1 总体原则

新的阈值实验必须满足：

- 使用冻结查询库中的全部合格查询；
- 不在线生成攻击或良性查询；
- 按 `doc_id` 划分 train、validation 和 test；
- 同一文档的全部查询只能属于一个分区；
- 所有攻击类型采用统一的会话构造标准；
- 不同文档、不同攻击类型不能共享会话；
- train 选择阈值，validation 只验证，test 只做最终报告。

数据流如下：

```text
冻结查询库
    -> 按 doc_id 生成 60/20/20 划分
    -> 读取指定分区的全部查询
    -> 统一构造 4-5 轮会话
    -> Observe 模式生成风险分数
    -> train 监督学习 t_attack
    -> validation 固定阈值验证
    -> test 最终有/无防御对比
```

### 3.2 模块一：查询库专用划分器

划分器从查询库提取 100 个唯一文档，并按照 `membership_label` 分层划分。

| 分区 | member | nonmember | 合计 |
|---|---:|---:|---:|
| train | 30 | 30 | 60 |
| validation | 10 | 10 | 20 |
| test | 10 | 10 | 20 |

输出文件为：

```text
data/query_bank_splits/ag_news_threshold_v1.json
```

划分文件保存三部分完整 `doc_id`、member/nonmember 数量、查询库 ID 与 SHA256、固定随机种子、创建时间、划分版本和每个分区的查询计数。

强制检查：

- 100 个文档全部分配；
- 三个分区完全无交集；
- 每个文档只出现一次；
- member/nonmember 数量符合表格；
- 同一文档的全部查询进入同一分区；
- 当前查询库 SHA256 与划分文件记录一致。

划分文件生成后禁止覆盖。调整划分时创建新的 split ID 和输出文件。

### 3.3 模块二：全量查询读取器

每个分区使用所属文档的全部合格查询。查询必须满足：

```text
validation.status == accepted
```

读取范围包括全部良性查询、四种攻击、canonical、paraphrase 和 IA generated 查询。当前冻结查询库共包含：

| 类型 | 查询数 |
|---|---:|
| benign | 500 |
| direct_rag_mia | 500 |
| s2_mia | 500 |
| masked_mia | 500 |
| ia | 3956 |

总计 5956 条。查询排序固定为：

```text
variant_type 优先级 -> query_index -> query_id
```

阈值实验不再通过 `variant_mode=canonical` 丢弃 paraphrase，也不再临时构造良性模板。

### 3.4 模块三：统一会话构造器

所有流量按以下键分组：

```text
partition + doc_id + traffic_type + attack_type
```

统一目标会话长度为 5：

```text
target_session_turns = 5
```

一个会话只能包含一个 `doc_id`、一种 `attack_type` 和一种 `traffic_type`，不能跨文档、跨攻击类型或混合攻击与良性流量。会话完成后清除状态。

#### Direct、S² 和 Masked

每个文档、每种攻击均有 1 条 canonical 和 4 条 paraphrase，正好组成一个 5 轮会话。该会话表示攻击者围绕同一目标文档连续使用不同表述进行探测。

#### IA

每个文档有 30-60 条合格 IA 查询，全部使用，但不能串成一个超长会话。设查询数为 `N`：

```text
K = ceil(N / 5)
```

将 `N` 条查询尽量平均分配到 `K` 个会话。当前数据会形成 4-5 轮 IA 会话，全部 3956 条 IA 查询预计形成 826 个会话。例如：

```text
30 条 -> 6 个 5 轮会话
31 条 -> 3 个 5 轮 + 4 个 4 轮会话
38 条 -> 6 个 5 轮 + 2 个 4 轮会话
60 条 -> 12 个 5 轮会话
```

该规则使用全部查询，并防止 IA 因超长历史或更多检测机会而获得不公平条件。

#### 良性流量

同一文档的 topic、entity、event、summary 和 follow_up 组成一个 5 轮良性会话。攻击和良性流量因此具有一致的目标会话长度。

#### 会话检测器

统一配置为：

```yaml
session:
  window_size: 5
  min_session_queries: 3
  evaluation_interval: 1
```

会话检测器从第 3 轮开始工作，并在第 3、4、5 轮更新风险。会话 ID 格式为：

```text
run_id:partition:traffic_type:attack_type:doc_id:session_index
```

程序必须验证一个 `session_id` 只对应一个文档、一种攻击类型和一种流量类型。

### 3.5 模块四：Observe 风险评分器

评分器按照统一会话顺序执行全部查询，固定使用 `mode=observe`，只收集原始风险分数，不让访问动作改变上下文和后续评分。

训练、验证和测试分别输出：

```text
train/risk_records.jsonl
validation/risk_records.jsonl
test/risk_records.jsonl
```

每条记录至少包含：

```text
query_id, doc_id, session_id, session_index, turn_index, session_length,
traffic_type, attack_type, variant_type, membership_label,
query_risk_score, session_risk_score, total_risk_score
```

由于需要处理全部 5956 条查询，评分器必须逐查询原子落盘，按 `query_id + session_id + turn_index` 去重，支持断点续跑。已开始但未完整落盘的会话整段重跑，避免恢复时缺少会话历史。

运行清单保存查询库、划分、模型、提示词、攻击模式库、聚合配置和会话规则的版本或哈希。任一字段不一致时拒绝续跑或复用旧分数。

### 3.6 模块五：文档平衡的离线阈值学习器

阈值学习器只读取 train 风险记录，不调用 LLM。

监督定义为：

```text
特征：total_risk_score
标签：traffic_type == attack 为 1；traffic_type == benign 为 0
```

`membership_label` 不作为攻击识别标签。

由于 IA 每个文档查询数不同，攻击召回率先按文档计算，再跨文档平均：

```text
Recall_doc = 该文档检测出的攻击查询数 / 该文档全部攻击查询数
Recall_attack = 同一攻击类型所有 Recall_doc 的平均值
```

阈值选择顺序为：

1. 保留良性查询 FPR 不超过 5% 的候选阈值；
2. 最大化四种攻击中最低的文档平衡 Recall；
3. 最大化四种攻击的宏平均 Recall；
4. 选择良性 FPR 更低的候选；
5. 其余指标相同时采用确定性的阈值决胜规则。

输出 `train/threshold_selection.json`，保存最终 `t_attack`、候选表、四类攻击指标、良性指标及完整数据版本。

如果不存在满足 FPR 约束且能够检测攻击的阈值，输出：

```json
{
  "status": "infeasible",
  "reason": "no_nontrivial_threshold_satisfies_fpr_constraint"
}
```

此时不生成正式配置，也不回退到 0.10。

### 3.7 模块六：验证、配置生成与最终测试

validation 只能加载 train 选择出的 `t_attack`，不能搜索新阈值。验证指标包括良性查询 FPR、良性会话误报率、四类攻击的查询级和会话级 Recall、最弱攻击 Recall、宏平均 Recall、Precision、F1、Balanced Accuracy、AUROC、AUPRC、混淆矩阵和按文档分组的 Bootstrap 置信区间。

验证通过标准在运行前固定为：

```text
良性查询 FPR <= 10%
四种攻击中不存在 Recall == 0 的攻击类型
```

验证通过后生成独立配置字段：

```yaml
policy:
  attack_detection_threshold: <t_attack>
  thresholds: [0.05, 0.10, 0.65, 0.85]
```

`total_risk_score < t_attack` 时不启动有效防御；达到阈值时至少启动 L2，再由现有严重程度规则决定是否提升到 L3/L4。独立字段避免学习阈值破坏原数组的单调顺序。

test 只运行一次，比较无防御、固定 0.10 和监督学习阈值三种条件。test 结果不能用于修改阈值、提示词、模型或会话规则。

### 3.8 查询级与会话级评价

查询级报告每条访问决策，包括良性查询 FPR、四类攻击的文档平衡 Recall、Precision、F1、AUROC 和 AUPRC。训练阈值的主要约束是良性查询 FPR 不超过 5%。

会话级报告一个攻击会话是否至少一轮被检测、一个良性会话是否至少一轮误报、首次检测轮次、第 3 轮检测率和最终轮检测率。会话级良性误报率必须单独报告，避免单查询误报较低但多轮会话几乎必然误报。

### 3.9 一致性校验

进入 validation 或 test 前必须匹配：

```text
query_bank_sha256, split_id, model_version, prompt_version,
pattern_library_version, query_selection_rule, target_session_turns,
window_size, min_session_queries, query_seed, aggregation_config
```

任一项不同，旧风险记录和旧阈值不得复用。

## 4. 异常处理

- 查询库或划分哈希不匹配：立即失败。
- 文档缺失、重复或跨分区：立即失败。
- 会话混合文档、攻击类型或流量类型：立即失败。
- validation/test 请求阈值搜索：立即失败。
- 查询评分失败：记录错误；会话未完整完成时整段重试。
- 查询库存在未分配文档或合格查询未被使用：立即失败。
- 阈值不可行：写出诊断结果，不生成 enforce 配置。
- 已存在冻结划分或完整结果目录：禁止静默覆盖。

## 5. 验收与测试

### 5.1 单元测试

- 60/20/20 文档划分的数量、平衡性和互斥性。
- 查询库全部 5956 条合格查询恰好属于一个分区。
- Direct、S²、Masked 和 benign 每个文档生成一个 5 轮会话。
- IA 的全部查询被拆为均衡的 4-5 轮会话，无遗漏、重复和跨文档。
- 会话 ID 唯一并严格隔离文档、攻击类型和流量类型。
- 文档平衡 Recall 不受 IA 查询数量差异影响。
- 阈值选择满足 FPR 约束和确定性排序规则。
- 不可行数据返回 `infeasible`，不生成正式配置。
- validation/test 不能调用阈值搜索。

### 5.2 集成测试

- 使用小型查询库完成 split -> score -> calibrate -> validate 全链路。
- 中断一个会话后恢复，最终记录与一次完整运行一致。
- 修改查询库、提示词或会话配置后拒绝复用旧结果。
- observe 模式不改变实际 RAG 上下文和回答策略。
- 生成的 `attack_detection_threshold` 能被访问控制读取，并在阈值边界正确启动至少 L2。

### 5.3 完成标准

实现完成必须满足：

1. 冻结查询库专用 split 通过 schema 和互斥检查。
2. 全量查询会话计划无遗漏、无重复、无跨文档污染。
3. train 风险记录可断点续跑并通过版本一致性检查。
4. 阈值只由 train 选择。
5. validation 使用锁定阈值输出完整查询级和会话级指标。
6. validation 通过时才能生成正式配置和运行 test。
7. 全部自动化测试通过。

## 6. 实验解释边界

该流程学习的是固定风险评分器的运行阈值，不等同于训练新的攻击检测模型。如果不存在满足低良性误报和非零四类攻击检测率的单一阈值，应将其解释为当前风险分数不可充分分离攻击与良性流量，而不是继续使用 validation/test 调参。
