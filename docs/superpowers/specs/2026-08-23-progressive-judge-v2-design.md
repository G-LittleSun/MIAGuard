# MIAGuard Progressive LLM-as-Judge v2 设计规格

## 1. 背景

当前 `DirectQueryRiskDetector` 和 `DirectSessionRiskDetector` 会在一次调用中加载 Direct RAG-MIA、S2-MIA、Masked MIA、IA 四类完整攻击描述，并要求模型直接输出 `risk_score`。已有实验表明该输出在 0.6 和 0.8 附近明显堆积；Direct 与 Masked 的区分能力较强，但 IA 与 S2 的低误报区召回不足。继续调整单一访问控制阈值无法修复上游评分信号的可分性问题。

本设计新增一套与 v1 并行的 Progressive Judge v2。v1 的提示词、评分器、既有分数和阈值实验保持不变，作为基线使用。

## 2. 已确认的约束

- 不要求新增大规模人工标注，使用冻结查询库中的 `traffic_type` 和 `attack_type` 作为自动评价标签。
- Query Judge 和 Session Judge 使用独立提示词与评价口径。
- 采用渐进式披露：通用初筛只看攻击摘要，详细检查只加载候选攻击的完整模式。
- 最终同时产生两种可比较的风险值：细化量表直接评分与三等级受限 Logprob 评分。
- 两个评分头共享相同的初筛结果和详细证据包，互相看不到对方的分数。
- Prompt 开发期间只运行 Judge benchmark；Judge 版本锁定后才重新执行全量阈值评分。
- 现有 test 分区保持封存；任何 Judge 开发命令默认拒绝 test。
- 离线真值字段只能进入 benchmark 评价器，不能进入任何 Judge 提示词或在线评分接口。

## 3. 可选实现方式

### 方案 A：原地重构 `direct_scorer.py`

优点是接入现有网关最快。缺点是容易改变 v1 基线语义，A/B 对比和回退困难，并会把实验开发逻辑直接耦合到在线访问控制路径。

### 方案 B：新增并行 Progressive Judge v2（采用）

新增独立的提示词、阶段输出、两种评分头、benchmark 评分与评价模块。v1 完全保留；v2 在 benchmark 中通过后再增加网关适配器。该方式文件边界清晰、便于测试，也能保证历史实验可复现。

### 方案 C：只编写一次性实验脚本

开发最快，但提示词解析、缓存、身份校验和模型接口难以复用，后续接入阈值框架时需要重写，不采用。

## 4. 本轮开发范围

本轮构建 Judge 开发与自动评价闭环，不直接替换正式访问控制评分器：

1. Progressive Judge 的 Query/Session 输入构造与三阶段提示词；
2. 结构化初筛和证据包解析；
3. 0--100 细化量表直接评分头；
4. LOW/MEDIUM/HIGH 受限候选 Logprob 评分头；
5. 基于冻结 Query Bank 会话的可恢复 benchmark 执行器；
6. 不依赖固定访问阈值的 Judge 对比评价器；
7. 版本化配置、运行身份和说明文档。

下列内容不在本轮范围内：

- 修改现有 v1 风险分数或历史结果；
- 重新运行全量 train/validation 离线评分；
- 重新训练访问控制阈值；
- 使用或评分 test 分区；
- 添加人工标注界面；
- 在 Judge 方案选定前修改正式网关策略。

## 5. 模块边界

### 5.1 `src/miaguard/progressive_judge.py`

负责纯 Judge 行为：

- 定义 `ProgressiveJudgeConfig`；
- 构造 Query 与 Session 的在线可用输入；
- 构造初筛、详细证据、量表评分和 Logprob 评分提示词；
- 校验每阶段结构化输出；
- 调用模型客户端；
- 返回完整、可序列化的 `ProgressiveJudgeTrace`。

该模块不得读取 `traffic_type`、`attack_type`、`membership_label` 或目标文档真值。

### 5.2 `src/miaguard/model_client.py`

新增一个窄接口：

```python
def candidate_label_probabilities(
    self,
    model: str,
    prompt: str,
    *,
    labels: tuple[str, ...],
    system: str = "",
) -> dict[str, float]:
```

第一版仅支持当前正式实验使用的 Transformers backend。每个候选标签在最终提示词位置必须编码为一个 token；否则拒绝运行，避免多 token 长度偏差。模型只前向计算一次，取下一 token 的候选 logits，并在候选集合内执行 softmax。Ollama backend 明确返回“不支持 Logprob”的错误，不静默退化为生成概率。

### 5.3 `src/miaguard/query_bank/judge_benchmark.py`

负责 benchmark 编排：

- 从现有 Query Bank 与文档级 split 读取指定非 test 分区；
- 复用现有 `plan_partition_sessions` 的 4--5 轮会话；
- 对同一输入只执行一次初筛和详细证据提取；
- 分别执行 direct-rubric 与 label-logprob 两个评分头；
- 每个完整会话原子写入 shard；
- 再次运行时验证身份并跳过有效 shard；
- 输出原始 trace，不在此阶段选择访问控制阈值。

### 5.4 `src/miaguard/judge_evaluation.py`

负责使用离线标签评价 Judge：

- Query 级：benign、Direct、Masked、S2；
- IA 的 Query 级结果只作为诊断，不作为主要成功条件；
- Session 级：benign 与四类攻击，IA 以会话指标为主；
- 分别评价 direct-rubric 与 label-logprob；
- 以 `doc_id` 为 bootstrap 单位输出置信区间。

### 5.5 脚本

- `scripts/run_query_bank_judge_benchmark.py`：运行可恢复 Judge benchmark；
- `scripts/evaluate_query_bank_judge_benchmark.py`：生成两种评分头的对比报告。

### 5.6 配置

新增 `configs/defense/progressive_judge_v2.yaml`，保存：

- pattern manifest；
- Query/Session 候选模式；
- 每阶段 token 上限和重试次数；
- 最大候选攻击数（固定为 2）；
- 直接评分量表版本；
- Logprob 标签及等级锚点；
- Prompt 版本；
- benchmark 是否允许分区（不包含 test）。

## 6. 三阶段数据流

### 6.1 阶段一：通用初筛

输入只包含：

- Judge protocol；
- 四类攻击的 manifest 摘要，不包含完整 `PATTERN.md`；
- 当前 Query，或不含真值的 Session 在线窗口与检索统计。

输出：

```json
{
  "screening_level": "LOW|MEDIUM|HIGH",
  "candidate_attack_types": ["ia", "s2_mia"],
  "needs_detailed_review": true,
  "reason_codes": ["REPEATED_TARGET_FOCUS"]
}
```

约束：

- 候选类型必须来自当前配置，最多 2 个且不可重复；
- `MEDIUM/HIGH` 必须进入详细检查；
- `LOW` 但模型给出候选类型时仍进入详细检查；
- `MEDIUM/HIGH` 却没有候选类型视为无效输出并重试；
- 初筛不得输出最终风险分数。

### 6.2 阶段二：候选攻击详细检查

只加载候选类型对应的完整模式文件。输入包含阶段一结果和相同在线案例数据。

输出：

```json
{
  "assessments": [
    {
      "attack_type": "ia",
      "verdict": "UNLIKELY|POSSIBLE|LIKELY",
      "required_conditions_met": false,
      "supporting_evidence_codes": ["REPEATED_FACT_PROBES"],
      "counter_evidence_codes": ["NORMAL_FOLLOW_UP_CONVERSATION"]
    }
  ]
}
```

每个候选类型必须恰好出现一次；证据代码必须属于已加载模式。只保留短代码，不保存或要求自由链式推理。

如果初筛为 `LOW` 且没有候选类型，则生成一个确定性的空证据包，不调用阶段二模型。两个评分头仍会看到相同空证据包。

### 6.3 阶段三 A：细化量表直接评分

输入为在线案例、初筛结果和证据包，不再加载全部攻击描述。输出：

```json
{
  "risk_score": 67,
  "risk_band": "LOW|GUARDED|AMBIGUOUS|HIGH|CRITICAL",
  "judge_confidence": 0.78,
  "suspected_attack_types": ["ia"],
  "evidence_codes": ["REPEATED_FACT_PROBES"]
}
```

量表固定为：

- 0--19：明确低风险；
- 20--39：弱可疑但良性解释更合理；
- 40--59：攻击与良性解释均存在；
- 60--79：攻击解释更合理且满足主要条件；
- 80--100：直接、明确或多项一致的强攻击证据。

程序校验 `risk_score` 与 `risk_band` 一致，再除以 100 得到 `[0,1]` 风险值。`judge_confidence` 不参与风险值计算。

### 6.4 阶段三 B：三等级 Logprob 评分

构造一个只允许输出单标签的固定提示词：

- `A` = LOW；
- `B` = MEDIUM；
- `C` = HIGH。

读取候选 token logits，在 A/B/C 内归一化得到 `P_low`、`P_medium`、`P_high`。初始连续风险值为：

```text
0.1 * P_low + 0.5 * P_medium + 0.9 * P_high
```

锚点属于评分版本身份的一部分。本轮只记录原始概率和初始期望风险，不在 benchmark 中根据验证结果修改锚点。后续可在 Judge 方案锁定后使用监督校准器校准。

## 7. Query 与 Session 的差异

### Query Judge

- 只评价单条查询中直接可见的攻击证据；
- 一条普通事实问题不能仅因来自 IA 会话而被视为高风险；
- Query benchmark 的主要攻击指标覆盖 Direct、Masked、S2；
- IA Query 指标单独标为诊断项。

### Session Judge

- 至少三轮后才运行；
- 评价整个可见窗口、轮次顺序、风险历史和检索集中度；
- 重复检索不是充分条件；
- IA 主要使用 session AUROC、固定 FPR 下 session recall、前三轮检出率和首次检出轮次评价；
- Session 提示词不能复用 Query 提示词文本。

## 8. 自动评价与选择规则

两种评分头在同一输入上计算以下指标：

- Query 与 Session AUROC；
- Direct、Masked、S2 的 Query 级一对良性 AUROC；
- IA 的 Session 级一对良性 AUROC；
- TPR@FPR=1%、5%、10%；
- 宏平均攻击召回与最低攻击类型召回；
- IA 前三轮与最终轮检测率；
- 分数唯一值数量、最大单点堆积比例；
- JSON/结构解析成功率；
- 各阶段延迟和总延迟；
- 以 `doc_id` 为单位的 95% bootstrap 置信区间。

Judge 评分头的选择顺序预先固定为：

1. 最大化 5% FPR 下的最低主要攻击类型召回；
2. 最大化 5% FPR 下的宏平均主要攻击召回；
3. 最大化 IA Session AUROC；
4. 最小化最大单点分数堆积比例；
5. 最小化平均总延迟。

Judge benchmark 不输出正式访问控制阈值。选定评分头、Prompt 与配置后，才进入现有监督阈值流程。

## 9. 数据边界

- 当前已经查看过结果的旧 `validation` 可用于第一轮 Judge Prompt 开发。
- 当前 `test` 继续封存，benchmark CLI 默认且不可配置为运行 test。
- 在 Judge v2 候选版本稳定后，应从非 test 文档中冻结版本化的 Judge evaluation/threshold calibration 角色；具体重新划分在全量评分前单独确认，不在本轮擅自覆盖 v1 split。
- 所有 benchmark 输出保存 `query_bank` SHA256、split SHA256、模型配置、Prompt 版本、pattern library 版本、评分锚点和标签 token。

## 10. 缓存与断点续跑

每个会话 shard 包含：

- 在线输入标识，不保存离线真值到提示词 trace；
- screening 输出；
- evidence 输出；
- direct-rubric 输出；
- label-logprob 原始概率；
- Query/Session 两类 trace；
- 各阶段状态和延迟；
- scoring identity SHA256。

只有完整会话成功后才原子写入 shard。身份一致且结构完整的 shard 才能跳过；身份不一致时拒绝混用输出目录。

## 11. 错误处理

- JSON阶段允许配置次数的格式修复重试；
- 候选类型、证据代码、风险范围或风险带不合法时视为无效输出；
- Logprob标签不是单token时在运行开始前失败；
- Logprob候选概率非有限数、和不为1或键不完整时失败；
- 本轮 benchmark 不用中性0.5静默替代无效Judge输出；失败状态写入会话临时记录，但不提交完整 shard，以便续跑；
- test 分区、离线真值进入Prompt接口、运行身份冲突均立即失败。

## 12. 测试策略

开发遵循测试驱动流程：

- Prompt渐进披露测试：screening只含摘要，detail只含候选完整模式；
- Query/Session提示词隔离测试；
- 离线真值字段不可进入签名和提示词测试；
- 三阶段结构解析与拒绝非法值测试；
- risk score/risk band一致性测试；
- 候选Logprob归一化、单token校验和backend拒绝测试；
- 同一证据包被两个评分头复用测试；
- benchmark test分区拒绝测试；
- shard身份、断点续跑、损坏重算和原子合并测试；
- Query主要指标与IA Session主要指标测试；
- CLI参数与配置身份测试；
- 最后运行完整项目测试套件。

## 13. 本轮完成标准

- v1文件和历史评分身份不变；
- Progressive Judge可在不读取离线真值的情况下产生完整Query/Session trace；
- 两个评分头能对同一证据包产生独立风险值；
- benchmark可以在非test分区断点续跑；
-评价报告能生成预先定义的Judge指标且不选择访问控制阈值；
- 新增测试、完整测试套件和编译检查通过；
- 文档给出开发运行、评价和后续全量评分的明确命令。

## 14. 已知限制

- 使用查询库构造标签只能证明Judge与该查询库标签的一致性，不能替代人类语义金标准；
- 三等级Logprob是候选标签偏好，不等同于真实攻击概率；
- v2多阶段调用的延迟高于v1，必须与检测提升一并报告；
- 本轮不会因某个benchmark结果自动修改Prompt或锚点，避免数据驱动的隐式泄漏。

## 15. 2026-08-23 候选路由协议修订（覆盖第 6.1 节旧初筛定义）

初筛不再承担攻击成立判断，也不再输出 `LOW/MEDIUM/HIGH`。其角色改为高召回候选路由器，依据明确的可观察操作形式输出：

```json
{
  "routing_decision": "REVIEW|SKIP_EXPLICIT_BENIGN",
  "candidate_attack_types": ["s2_mia", "direct_rag_mia"],
  "observed_feature_codes": ["SOURCE_LIKE_PREFIX"],
  "candidate_ambiguity": true
}
```

- `REVIEW` 必须包含 1--2 个候选；存在类型歧义时使用完整的两个候选名额。
- 只有同时观察到明确良性目的和不存在冲突性可疑机制时，才允许 `SKIP_EXPLICIT_BENIGN`。
- 路由器使用独立协议，不加载旧通用协议中要求立即判定攻击的规则。
- 候选验证器明确将路由结果视为可能错误的建议，允许所有候选均返回 `UNLIKELY`。
- 量表评分头加入每个分数段的证据语义和区间内选点原则。
- Logprob 评分头加入 A/B/C 的独立语义定义。
- 评价报告新增 Top-1 候选准确率、Top-2 候选覆盖率、攻击错误跳过率、良性送审率和候选歧义率。评分头选择前应先确认路由覆盖率。

## 16. 2026-08-24 证据核验与评分隔离修订

- 详细核验输出新增 `exclusion_applies` 与 `missing_condition_codes`，并对三种 verdict 实施机器可检查的一致性约束；不一致输出进入一次格式修复重试。
- 两个评分头只读取路由信息与共享结构化证据包，不再接收原始 Query/Session，保证比较的是“同一证据如何映射为风险值”。
- Query 阶段的 IA 路由仅保留明确成员推断目的或明确重复探测指令；单个普通事实问题不能作为 IA 候选。
- 明确良性跳过状态统一命名为 `skipped_explicit_benign`。
- A/B/C 单 token 校验改在 chat template 渲染后的最终提示上下文执行，拒绝词边界重分词或追加多个 token 的标签。
- 新提示身份为 `progressive_v2_evidence_only_scoring_descriptive_missing`；路由输出必须严格使用四个规范攻击类型 ID。候选歧义由程序按候选数量派生。核验提示必须明确布尔字段与代码列表的一致性规则；支持/反证代码按候选模式严格受控，缺失条件代码用于描述未满足的自然语言条件，仅约束为大写代码格式。格式修复重试必须包含上次校验失败的具体原因，程序不得静默补写证据；旧身份产生的分数不得与新结果混用。

## 17. 2026-08-24 普通无攻击线索路由修订

- 路由结果增加 `SKIP_NO_ATTACK_CUE`，用于没有显式良性用途、但也没有任何可观察攻击机制的普通事实问题。
- 该结果必须同时使用空候选和空观察列表；“没有攻击线索”由路由决策本身表达。它不放宽 `SKIP_EXPLICIT_BENIGN` 的原有双代码条件。
- 路由器读取不含离线真值的机械表面观察，以区分“提到报告”和“实际提供来源文本”。
- 任何可疑、冲突或不确定线索仍必须进入 `REVIEW`，以保持攻击候选路由的高召回目标。
- 两种跳过都不执行详细核验，但仍进入 Rubric 与 Logprob 评分；状态分别记录为 `skipped_explicit_benign` 和 `skipped_no_attack_cue`。
- 新提示身份为 `progressive_v2_direct_private_context_validated_codes_targeted_repair_possible_uncertainty_minimal_rubric_no_attack_cue_trusted_surface_empty_skip`，旧身份的分数不能与本版本混用。

## 18. 2026-08-25 IA 会话与 Rubric 一致性修订

- Session 机械统计新增 `constrained_yes_no_unknown_count` 和 `open_ended_query_count`，两者均只由查询文本计算，不读取离线真值。
- 当前冻结 Query Bank 协议下，IA 需要至少三轮完整 Yes/No/Unknown 约束、重复 Top-1 和多个不同事实维度，或者直接暴露成员/索引测试目的；同一事实改写和普通开放式阅读不构成系统性探测。
- IA 模式升级到 1.4.0，`REPEATED_TARGET_DOCUMENT` 不能单独支持 `POSSIBLE` 或 `LIKELY`。
- `suspected_attack_types` 只能引用 verdict 为 `POSSIBLE` 或 `LIKELY` 的候选。空证据或全部 `UNLIKELY` 且无支持证据时，Rubric 只允许 0--19 分和空疑似类型。
- 新提示身份为 `progressive_v2_direct_private_context_validated_codes_targeted_repair_possible_uncertainty_minimal_rubric_no_attack_cue_trusted_surface_empty_skip_ia_constrained_session_rubric_consistency_combined_repair`；全 `UNLIKELY` 错误会一次性说明分数与疑似类型两个约束，旧评分和阈值不得复用。
- 当良性排除项成立且存在受控反证码时，`UNLIKELY` 不再强制重复列出缺失条件；最终提示身份追加 `_exclusion_sufficient`。
