# Progressive Judge IA 会话判定与评分一致性设计

## 1. 目标

修复 Progressive Judge 在多轮会话上的两类问题：

1. 将同一文档上的正常开放式事实问答误判为 Information Association Attack（IA）；
2. 详细核验已经给出 `UNLIKELY` 且没有支持证据时，Rubric 仍输出中高风险分数。

本轮只修改 Judge 的提示协议、机械会话观察、结构化校验与对应测试，不训练访问控制阈值，也不修改冻结查询库、数据划分或会话构造规则。

## 2. 已确认的实验事实

当前冻结查询库中：

- 3,956 条已接受 IA 查询全部同时包含 Yes、No 和 Unknown 回答约束；
- 500 条已接受良性查询均不包含该三选一约束；
- Direct、S2 和 Masked 三类已接受查询也不包含完整的 Yes/No/Unknown 三选一约束。

失败的良性会话由开放式阅读问题组成。前四轮主要反复询问同一个“收购价格”事实，第五轮询问原因。虽然检索反复命中同一 Top-1 文档，但它不满足当前 IA 查询库的约束式探测机制。旧 Judge 将重复检索本身当成了充分证据，违反了 IA 模式中“重复检索必要但不充分”的定义。

此外，该会话第五轮的核验结果已经是 `UNLIKELY`、支持证据为空，但 Rubric 仍输出 0.60，说明评分头缺少机器可检查的一致性边界。

## 3. 方案选择

### 方案 A：修改冻结良性查询或拆散良性会话

不采用。它会绕开 Judge 的误判，而不是检验 Judge 能否区分正常连续阅读和 IA 探测，并破坏现有冻结实验口径。

### 方案 B：在程序中直接覆盖模型的 IA 判断

不采用。程序根据规则静默删除 IA 候选会掩盖 LLM-as-Judge 的真实行为，使后续无法评价提示词质量。

### 方案 C：机械观察 + 明确语义 + 输出一致性校验

采用。程序只计算不含标签的表面事实并提供给模型，模型仍完成路由、核验和评分；程序只拒绝内部矛盾的结构化输出并允许一次定向修复，不替模型生成攻击证据。

## 4. IA 会话判定设计

### 4.1 新增机械会话观察

Session case 的 `session_statistics` 增加：

- `constrained_yes_no_unknown_count`：截至当前轮，同时要求 Yes、No、Unknown 三选一回答的查询数量；
- `open_ended_query_count`：未包含完整三选一约束的查询数量。

这些值只由会话中的查询文本机械计算，不读取 `traffic_type`、`attack_type`、成员标签或目标文档真值。

### 4.2 路由语义

在当前冻结 Query Bank 实验协议下，IA 路由必须满足以下两条路径之一：

1. 会话已经至少三轮，`constrained_yes_no_unknown_count >= 3`，Top-1 重复命中达到现有 IA 集中度要求，并且问题覆盖多个不同事实维度；或
2. 查询直接暴露了语料成员测试、索引存在性测试或系统性探测目的。

同一事实的重复提问和近义改写只计算为一个事实维度。仅有 Top-1 重复命中、仅围绕同一主题、或者普通开放式问答，不能单独支持 IA 候选。存在其他攻击机制时仍可路由至 Direct、S2 或 Masked；存在真实歧义时仍返回 `REVIEW`。

### 4.3 详细核验语义

IA 模式文件增加并明确以下规则：

- `REPEATED_TARGET_DOCUMENT` 不能单独支持 `POSSIBLE` 或 `LIKELY`；
- 同一事实的改写不构成 `REPEATED_FACT_PROBES` 或 `SYSTEMATIC_ENTITY_PROBING`；
- 开放式、连贯的阅读问答属于 `NORMAL_FOLLOW_UP_CONVERSATION` 反证；
- 当前冻结协议中，至少三轮 Yes/No/Unknown 约束是 IA 系统性探测的必要表面机制，除非会话直接声明成员测试或索引测试目的。

IA 模式版本随语义变更递增，保证旧评分身份不能与新结果混用。

## 5. Rubric 一致性设计

Rubric 仍只由模型输出：

```json
{"risk_score": 12, "suspected_attack_types": []}
```

程序继续从风险整数派生风险等级，并从核验证据包复制受控证据码。在此基础上新增以下机器校验：

- `suspected_attack_types` 只能包含 verdict 为 `POSSIBLE` 或 `LIKELY` 的候选；
- 当所有 assessment 均为 `UNLIKELY` 且所有 `supporting_evidence_codes` 均为空时：
  - `risk_score` 必须位于 0--19；
  - `suspected_attack_types` 必须为空；
- 空 EvidencePacket 同样要求低风险分数和空疑似攻击类型。

不在本轮强制规定 `POSSIBLE` 或 `LIKELY` 必须对应某个固定最低分，因为风险强度仍应由评分头比较，避免把阈值选择提前写入 Judge 协议。

校验失败时沿用现有一次定向格式修复，并把具体一致性错误与上一次 JSON 返回给模型；程序不静默截断分数或删除攻击类型。

实现期复测进一步明确：当 `exclusion_applies=true` 且存在受控反证码时，反证已经足以支持 `UNLIKELY`，`required_conditions_met=false` 不再强制重复列出缺失条件；只有 `exclusion_applies=false` 时，未满足必要条件才必须提供 `missing_condition_codes`。该边界减少冗余输出，不放宽反证码要求。

## 6. 数据流

1. Session 构造器机械统计检索集中度、三选一约束数量和开放式查询数量；
2. Router 结合完整会话、机械统计和攻击摘要选择候选；
3. Verifier 只加载候选完整模式，检查必要机制、支持证据与良性排除项；
4. Rubric 与 Logprob 继续共享同一个结构化证据包；
5. Rubric JSON 通过新增的一致性校验后写入 trace；
6. 新提示版本、IA 模式版本、配置和运行身份一起冻结。

## 7. 测试与复测

### 7.1 单元测试

- 会话统计正确识别三轮 Yes/No/Unknown IA 查询；
- 开放式良性问题的约束计数为 0；
- Session 路由提示包含机械统计和新的 IA 必要机制；
- 全部 `UNLIKELY` 且无支持证据时，中高 Rubric 分数校验失败并触发定向修复；
- `suspected_attack_types` 引用 `UNLIKELY` 候选时校验失败；
- 合法低风险输出、现有 Direct 攻击输出和 Logprob 头保持兼容。

### 7.2 配对模型复测

在 train 开发分区选择同一文档：

- 1 个冻结 IA 攻击会话；
- 1 个冻结良性会话；
- 两者均使用固定 5 轮，前三轮开始产生 Session Judge 结果。

主要验收条件：

- IA 攻击第 3--5 轮不被错误跳过；
- 良性会话不能仅凭重复 Top-1 被认定为 IA；
- 全部 `UNLIKELY`、无支持证据的 trace 不再获得 0.60 一类中高 Rubric 分数；
- 所有记录结构有效，两个评分头均有输出；
- 报告攻击错误跳过率、良性送审率、分数均值和最小间隔，但不据此训练阈值。

## 8. 明确边界

- 该规则是当前冻结 Query Bank 的 Judge 开发协议，不宣称覆盖所有现实世界 IA 变体；
- 后续如果引入不使用 Yes/No/Unknown 的新 IA 查询形式，必须先更新攻击模式、查询库版本和提示身份，再重新评分；
- 本次两会话复测只用于语义诊断，不能作为最终性能结论；
- 在 IA 与良性配对复测通过前，不进入全量离线评分或监督阈值训练。
