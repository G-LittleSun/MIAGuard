# MIAGuard 版本化离线查询库设计

## 1. 背景

当前 MIAGuard 实验即使采用小规模数据，也会运行一个小时左右。历史日志显示，一次
AG News 四攻击 `10 member + 10 nonmember`、20 条 benign 查询、IA 三轮查询的两阶段
对比实验从 22:10:48 运行至 23:20:01。

现有实现已经在 `data/attack_results/` 中保存部分攻击结果，并能在防御实验中复用这些
结果，但查询构造仍未与攻击执行彻底分离：

- Direct RAG-MIA 和 S²-MIA 的查询由确定性模板现场构造。
- Masked MIA 使用本地模型选择掩码词，再让目标 RAG 恢复掩码。
- IA 使用本地模型生成问题和 ground truth；两阶段对比实验还可能在线补齐 IA 多轮问题。
- benign 查询主要由简单模板现场构造。

因此，不同实验可能重复进行相同的查询构造，也难以严格保证不同防御方案使用完全
相同的查询输入。

## 2. 目标

建立与目标文档绑定、可增量扩展、可审计且可复现的离线 Query Bank。正式实验只从
Query Bank 抽取查询，不再调用模型构造查询、生成 IA ground truth 或选择 Masked MIA
掩码词。

设计的成功标准如下：

1. Query Bank 与攻击执行、RAG 回答和防御结果完全分离。
2. 每条查询绑定具体的 `dataset_id`、`doc_id` 和源文档哈希。
3. Query Bank 可以中断后继续构建，不重复生成已完成文档。
4. 同一 Query Bank 和随机种子得到完全相同的查询选择。
5. 无防御与有防御实验复用同一份冻结查询选择。
6. frozen 实验中在线查询生成次数严格为零。
7. 查询不足、文档变化或 Query Bank 不完整时明确失败，不静默回退在线生成。

## 3. 非目标

本设计不缓存目标 RAG 的回答，也不缓存防御模型的评分。正式实验仍需执行向量检索、
目标 RAG 回答、攻击评分和防御检测。Query Bank 消除的是查询构造阶段，不保证消除
实验的全部模型推理时间。

本设计也不引入 SQLite，不改变现有向量库格式，不重构与 Query Bank 无关的项目模块。

## 4. 总体架构

流程拆分为离线构建与在线实验两个阶段。

离线构建阶段：

```text
目标文档
  -> 按攻击类型生成候选查询
  -> 格式、语义和数量校验
  -> 去重与增量补齐
  -> 写入版本化 Query Bank
```

在线实验阶段：

```text
加载完整 Query Bank
  -> 校验版本和文档哈希
  -> 按成员标签、攻击类型和 seed 分层抽样
  -> 冻结 query selection manifest
  -> 执行检索、RAG 回答和防御检测
  -> 计算并保存指标
```

核心组件及职责：

- `QueryBankBuilder`：调用本地模型并增量补齐查询。
- `QueryValidator`：校验 schema、数量、哈希、答案平衡和重复项。
- `QueryBank`：读取、索引和按条件查询已冻结数据。
- `QuerySampler`：根据实验配置和 seed 分层抽样，不依赖生成模型。

这些组件位于 `src/miaguard/query_bank/`，脚本仅负责命令行参数解析和调用。

## 5. 目录结构

### 5.1 脚本和实现

```text
scripts/
└── query_bank/
    ├── build_query_bank.py
    ├── validate_query_bank.py
    └── inspect_query_bank.py

src/miaguard/query_bank/
├── builder.py
├── schema.py
├── validator.py
├── storage.py
└── sampler.py

configs/query_banks/
└── ag_news_v1.yaml
```

脚本职责：

- `build_query_bank.py`：创建、断点续建和增量补齐 Query Bank。
- `validate_query_bank.py`：执行独立的完整性和质量校验。
- `inspect_query_bank.py`：显示各攻击、成员类别、变体和失败原因的统计摘要。

### 5.2 数据

```text
data/query_banks/<bank_id>/<dataset_id>/
├── .work/
│   └── <doc_id>.jsonl
├── manifest.json
├── documents.jsonl
├── queries.jsonl
└── generation_failures.jsonl
```

`.work/` 是构建阶段的逐文档分片目录。只有所有必需分片通过校验并成功合并后，Query
Bank 才可标记为 `complete`。

## 6. Query Bank 容量

Query Bank 采用候选池模式。构建配置为计划最大实验规模准备 2 至 5 倍的目标文档，
并允许后续增量补充新文档。

每个目标文档的查询数量固定为：

| 流量或攻击类型 | 每文档数量 | 组成 |
|---|---:|---|
| Direct RAG-MIA | 5 | 1 canonical + 4 paraphrase |
| S²-MIA | 5 | 1 canonical + 4 paraphrase |
| Masked MIA | 5 | 1 canonical + 4 paraphrase |
| IA | 30 | 15 个 yes + 15 个 no |
| benign | 5 | 五种固定合法查询类别各 1 条 |

benign 的五种类别为：

1. 主题概括；
2. 关键实体；
3. 主要事件；
4. 高层摘要；
5. 合法后续研究问题。

## 7. 数据格式

### 7.1 `queries.jsonl`

`queries.jsonl` 采用一行一条查询。统一 envelope 示例：

```json
{
  "query_id": "ag_news:doc-001:ia:0007",
  "dataset_id": "ag_news",
  "doc_id": "doc-001",
  "membership_label": 1,
  "source_document_sha256": "hex-encoded-sha256",
  "traffic_type": "attack",
  "attack_type": "ia",
  "variant_type": "generated",
  "query_index": 7,
  "query_text": "I am inquiring about ...",
  "payload": {
    "question": "Did ...?",
    "ground_truth": "yes",
    "summary": "..."
  },
  "generation": {
    "backend": "transformers",
    "model": "LLM/mistralai/mistral-7b-instruct-v0-2",
    "prompt_version": "ia-query-v1",
    "temperature": 0.2,
    "seed": 20260724
  },
  "validation": {
    "status": "accepted",
    "answer_verified": true,
    "duplicate_checked": true
  },
  "created_at": "ISO-8601 timestamp"
}
```

`query_id` 由稳定字段生成，同一文档、攻击类型、变体类型和 query index 在相同 Query
Bank 中必须得到相同 ID。

不同类型的 `payload`：

- Direct：目标引用文本和 yes/no 回答约束。
- S²：原文前缀和续写参数。
- Masked：`masked_text`、`answers`、掩码位置和选择来源。
- IA：`summary`、原始问题、`ground_truth` 和最终攻击查询。
- benign：正常查询类别和必要的主题元数据。

`variant_type` 的允许值至少包括：

- `canonical`：严格复现当前攻击算法；
- `paraphrase`：保持攻击目标不变的模型改写；
- `generated`：IA 或 benign 的离线生成查询。

### 7.2 `documents.jsonl`

该文件记录参与构建的文档身份、成员标签和源文档哈希，不重复保存文档全文。构建器和
实验加载器都必须用当前源文档重新计算哈希并核对。

### 7.3 `manifest.json`

manifest 至少记录：

- `bank_id`、schema 版本、状态和时间；
- 数据集 ID 与源文档快照哈希；
- 生成模型、后端、参数和提示词版本；
- 每类成员与非成员文档数量；
- 每文档期望查询数量；
- IA 的 `15 yes + 15 no` 约束；
- accepted、rejected 和 failed 数量；
- 最终 `queries.jsonl` 的 SHA-256；
- Query Bank 的整体内容哈希。

状态包括 `building`、`incomplete` 和 `complete`。正式 frozen 实验只接受 `complete`。

### 7.4 `generation_failures.jsonl`

失败记录包含 `dataset_id`、`doc_id`、攻击类型、失败阶段、错误类型、重试次数和发生
时间。失败数据不得进入最终 `queries.jsonl`。

## 8. 离线生成流程

建议入口：

```powershell
python scripts/query_bank/build_query_bank.py `
  --config configs/query_banks/ag_news_v1.yaml `
  --bank-id ag_news_queries_v1 `
  --dataset ag_news
```

构建器一次加载本地模型，逐文档处理并写入独立分片。

### 8.1 Direct RAG-MIA

使用现有确定性逻辑生成一条 canonical 查询。本地模型另外生成四条语义等价
paraphrase。校验器必须确认改写仍然要求判断特定目标内容是否存在，并保留 yes/no
回答约束。

### 8.2 S²-MIA

使用现有前缀截取逻辑生成一条 canonical 查询。本地模型生成四条仍然要求续写原文的
paraphrase。改写不能变成摘要、解释或开放式创作。

### 8.3 Masked MIA

离线完成难词选择、掩码位置和正确答案生成。canonical 查询使用现有恢复掩码要求；
四条 paraphrase 必须复用同一个 `masked_text` 和同一组 `answers`，只改变指令表达。

### 8.4 IA

IA 按小批次生成，不要求模型一次输出 30 条。每个文档持续生成并校验，直到 accepted
集合严格包含 15 条 yes 和 15 条 no。

每个候选问题依次通过：

1. JSON 和字段完整性检查；
2. 明确指代检查，禁止依赖“本文”“这段文字”等模糊指代；
3. ground truth 只能为 `yes` 或 `no`；
4. 独立第二次答案判定必须与生成答案一致；
5. 规范化文本去重；
6. 语义相似度去重；
7. yes/no 数量约束检查。

### 8.5 benign

每个文档按五个固定类别各生成一条查询。查询必须是合法内容请求，不得询问数据库
成员性、要求复现受保护文本或伪装成攻击目标。

### 8.6 防止标签泄漏

查询生成提示词只接收目标文档内容和查询类型约束，不接收向量检索结果，也不把
`membership_label` 告诉生成模型。成员标签仅用于 Query Bank 统计和后续分层抽样。

## 9. 增量构建和故障处理

增量构建遵循以下规则：

1. 文档分片已完整且文档哈希一致时跳过。
2. 只补充缺少的攻击类型、答案类别或变体。
3. 不完整分片在恢复时重新生成，不能作为部分成功结果复用。
4. 模型、提示词版本或关键参数变化时创建新的 `bank_id`。
5. 达到最大重试次数仍无法补齐时记录失败，并将 Query Bank 标记为 `incomplete`。
6. 同一 `bank_id` 同时只允许一个构建进程，通过锁文件防止并发写入。

所有文档完成后，构建器按以下稳定顺序合并：

```text
dataset_id, doc_id, attack_type, variant_type, query_index
```

合并结果先写入临时文件，通过全量校验后原子替换最终 `queries.jsonl`，随后计算内容
哈希并将 manifest 更新为 `complete`。

## 10. 实验抽样

实验配置示例：

```yaml
query_bank:
  bank_id: ag_news_queries_v1
  mode: frozen
  seed: 20260724

sampling:
  members_per_attack: 10
  nonmembers_per_attack: 10
  benign_count: 20
  ia_questions_per_document: 3
  variant_mode: canonical
```

抽样规则：

1. 按成员标签分层抽取成员和非成员文档。
2. 四种攻击默认使用同一批目标文档。
3. IA 从每个文档的 30 条 accepted 查询中分层抽取。
4. IA 抽取偶数条时 yes/no 数量相同；奇数条时两类相差最多一条，额外类别由 seed
   决定。
5. benign 默认每个文档抽取一条，并尽量平衡五种查询类别。
6. 抽样结果写入 `query_selection_manifest.json`。
7. 无防御和有防御阶段必须读取同一份 selection manifest。

`variant_mode` 支持：

- `canonical`：仅使用 canonical，适合攻击基线；
- `paraphrase`：仅使用 paraphrase，适合防御鲁棒性实验；
- `mixed`：按显式比例混合，并按变体分别报告指标。

数据不足、查询库不完整或哈希不匹配时，frozen 模式直接失败。frozen 模式不存在在线
生成 fallback。

## 11. 现有流程接入

`run_two_stage_attack_comparison.py` 改为加载 Query Bank，不再调用
`expand_ia_rows()`。四种基础攻击入口增加 Query Bank 参数并读取对应 payload：

- Direct 读取冻结的 `query_text`。
- S² 读取冻结的 `query_text` 和 `prefix`。
- Masked 读取 `masked_text` 和 `answers`，不再在线选择掩码。
- IA 读取 `summary`、`question`、`ground_truth` 和 `query_text`。
- benign 从五类正常查询池抽取。

每次实验 manifest 至少增加：

```json
{
  "query_bank_id": "ag_news_queries_v1",
  "query_bank_sha256": "hex-encoded-sha256",
  "query_seed": 20260724,
  "selection_manifest": "query_selection_manifest.json",
  "online_query_generation": false
}
```

现有 `data/attack_results/` 保留为历史实验结果，不再承担新 Query Bank 的存储职责。

## 12. 校验与检查

验证入口：

```powershell
python scripts/query_bank/validate_query_bank.py `
  --bank-id ag_news_queries_v1 `
  --dataset ag_news
```

检查入口：

```powershell
python scripts/query_bank/inspect_query_bank.py `
  --bank-id ag_news_queries_v1 `
  --dataset ag_news
```

检查输出至少包括：

- 成员与非成员文档数；
- 各攻击 accepted 查询数；
- canonical、paraphrase 和 generated 数量；
- IA yes/no 数量与每文档分布；
- benign 五类别数量；
- 重复、拒绝和失败原因统计；
- Query Bank 状态和哈希。

## 13. 测试

自动化测试覆盖：

1. Schema 接受五类合法查询并拒绝缺失字段。
2. 相同 seed 得到完全相同的 query ID 列表。
3. 不同 seed 能从容量足够的候选池得到不同选择。
4. 成员与非成员抽样数量严格平衡。
5. IA 每文档正好 30 条并满足 `15 yes + 15 no`。
6. IA 抽取后 yes/no 尽可能平衡。
7. 每文档包含五种 benign 类别。
8. Direct、S² 和 Masked 各包含 `1 canonical + 4 paraphrase`。
9. 文档哈希不匹配、查询不足或 Query Bank 不完整时立即失败。
10. 无防御和有防御阶段使用完全相同的 query ID。
11. frozen 实验中查询生成器调用次数严格为零。
12. 改用 Query Bank 后，现有攻击评分逻辑保持一致。
13. 构建进程中断后可以从完整文档分片继续。
14. 两个构建进程不能同时写入同一 Query Bank。

## 14. 验收

实现完成需满足：

- Query Bank 能够从空目录构建、增量补齐、断点恢复并完成全量校验。
- IA 对每个目标文档保留 30 条 accepted 查询，严格保持 15/15。
- 每个文档具有规定数量的三类单轮攻击和 benign 查询。
- 小规模 frozen 实验不出现 IA 问题生成或 Masked 掩码生成日志。
- 实验 manifest 明确记录 `online_query_generation: false`。
- 同一 Query Bank 和 seed 多次运行的 selection manifest 完全一致。
- 基线与防御实验复用相同 query ID。
- 独立校验脚本在篡改查询、文档哈希或 manifest 后能够检测并拒绝数据。

## 15. 已知限制

- Query Bank 提前承担了较大的单次生成成本，尤其是每文档 30 条 IA 查询及二次答案
  验证。
- 使用同一个本地模型生成和复核答案仍可能存在相关性偏差；后续可以增加人工抽检或
  独立验证模型，但不属于本次首版范围。
- Query Bank 与源文档快照绑定；源文档内容变化时必须新建或重建对应数据。
- 预生成查询可以缩短重复实验时间，但在线 RAG 回答和 LLM 防御评分仍可能成为主要
  耗时。
