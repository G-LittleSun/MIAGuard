# AG News Query Bank v2 良性查询扩充设计

## 1. 目标与范围

建立新的冻结查询库 `ag_news_queries_v2`，以解决 v1 中良性查询远少于攻击查询的问题。
每篇目标文档生成 25 条良性查询：20 条 `standard` 与 5 条 `hard`。攻击记录、目标文档、
membership 标签、RAG 语料和攻击会话语义均保持与 `ag_news_queries_v1` 相同。

本设计只改变良性流量覆盖度；不修改 Qwen Judge、攻击提示词、攻击样本、检索库或既有
v1 产物。v1 及其运行结果永不覆盖，也不与 v2 分数混合。

## 2. v2 的构造方式

v2 以已验证的 v1 为父库，而非从原始文档重新生成全部攻击：

```text
v1 非 benign 记录 -> 字节级复制到 v2
v1 benign 记录     -> 不复制
源文档             -> 生成 20 standard + 5 hard benign
```

因此 v2 中每篇文档的攻击查询数与文本和 v1 完全一致；唯一的实验变量是良性查询集。
输出 manifest 记录父库 ID、父库 queries SHA256、源攻击记录 SHA256、良性生成配置、
生成模型、种子、验证器版本与新库 SHA256。

v2 的总攻击数等于 v1 的总攻击数；良性数为 `25 × 文档数`。当前 60 文档 train 分区
预期包含 1,500 条良性查询与现有 3,275 条攻击查询，而不是强行将二者采样至完全相等。

## 3. 良性记录 schema

每条新记录仍然是二元主任务中的良性：

```json
{
  "traffic_type": "benign",
  "attack_type": "benign",
  "variant_type": "generated",
  "payload": {
    "category": "topic | entity | event | summary | follow_up",
    "difficulty": "standard | hard",
    "hard_scenario": null,
    "benign_intent": "ordinary information-seeking intent"
  }
}
```

`difficulty`、`hard_scenario` 与 `benign_intent` 是离线数据审计字段。它们绝不进入
Judge 提示词、检索请求、融合分类器、阈值选择或运行时访问控制。模型只接收正常的
`query_text` 与现有 RAG 上下文。

`hard_scenario` 仅在 `difficulty=hard` 时非空，限定为：

```text
quoted_context_interpretation
grounded_fact_linking
legitimate_context_elaboration
multi_turn_clarification
source_attribution_or_comparison
```

每个类别精确生成 4 条 standard 和 1 条 hard，因此每篇文档的 25 条良性查询覆盖五个
既有类别，且 hard 比例固定为 20%。稳定 ID 继续使用 `benign:generated:0001` 至
`benign:generated:0025`，不复用 v1 的五条 benign 文本。

## 4. 内容约束与质量控制

standard benign 是普通读者真实会问的问题：主题、实体、事件、摘要与自然 follow-up。
hard benign 必须也是可由普通用户正当提出、可由给定文档回答的问题，但允许带有会触发
表面攻击线索的形式，例如解释已给出的短引文、追问实体/时间/数字关系、同文档澄清、
根据上下文进行比较或归因。它不得请求成员身份、训练语料存在性、逐字原文续写、受保护
文本重构，或伪装成普通用途的攻击模板。

每篇文档的生成和验收顺序：

1. 按类别和难度生成候选；生成提示明确要求返回普通用户意图与可验证的问题。
2. 规范化后，拒绝与该文档已有良性问题或新候选重复的文本；拒绝空问题与格式残留。
3. 由独立的 benign-intent verifier 核验“普通信息需求、无成员/语料重构目的、类别和
   难度标签匹配”。验证器不能使用 attack_type 真值作为输入。
4. hard 候选还须核验其 `hard_scenario` 与问题文本一致；standard 不能携带 scenario。
5. 缺少任一类别/难度配额时仅重生该槽位，至多使用固定次数；达到上限则整个 v2 构建失败，
   不以模板或重复查询填充。
6. 构建后对每个类别/难度进行规范化去重、比例、来源文档和会话完整性检查；对 hard
   至少随机人工复核 20%，对 standard 至少随机人工复核 5%，并记录抽样种子和结论。

## 5. 会话、划分与评价

每篇文档的 25 条 benign 组织成五个 5 轮会话。每个会话固定含 4 条 standard 和 1 条
hard；hard 的轮次由库种子和文档 ID 决定，且五个会话的 hard 轮次尽量均匀。会话内不
混合文档、攻击类型或流量类型。该规则同时测量单条 hard benign 是否误报、以及它是否
使整段正常会话错误升级。

创建 `data/query_bank_splits/ag_news_threshold_v2.json`。它重新写入 split manifest 并
绑定 v2 SHA256；为隔离良性扩充变量，沿用 v1 的相同 doc_id 到 train/validation/test
映射和 member/nonmember 平衡，但不复用 v1 split 文件或其哈希。

训练、验证、测试均使用 v2 的同一 20:5 规则。所有 Judge 分数、Stage A 分析、融合器、
阈值与验证结果必须从 v2 重新运行。报告整体 benign FPR、standard-benign FPR、
hard-benign FPR、总体 benign session FPR 和包含 hard 查询的 benign session FPR；运行时
仍只有一个二元攻击概率和一个全局阈值。

## 6. 验收标准

1. v2 非 benign 记录的规范化 JSON 内容与 v1 完全一致，且每篇文档攻击记录数一致。
2. 每篇文档恰有 25 条 accepted benign：每类别 4 standard 与 1 hard。
3. 每个 hard 查询有合法 scenario；每个 standard 查询没有 scenario；所有良性均保持
   `traffic_type=attack_type=benign`。
4. 同文档良性问题规范化后无重复，且不含禁止攻击意图。
5. 每篇文档恰有五个 benign 会话，每会话 4 standard + 1 hard，hard 位置可复现。
6. v2 manifest、split、记录、生成和人工审计均有 SHA256/种子/版本可追溯信息。
7. v2 训练集重新完成 Judge 的 Stage A；若 v2 分布不具可分性，不进入融合器训练。
