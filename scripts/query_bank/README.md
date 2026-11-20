# Query Bank 构建脚本使用指南

本目录中的脚本用于提前生成、校验和检查 MIAGuard 的离线查询数据集
（Query Bank）。正式实验可以直接从完整的 Query Bank 抽取查询，避免重复调用
本地大模型生成 IA 问题、Masked MIA 掩码和正常查询。

更完整的构建原理、数据格式、跨数据集适配方法和命令模板见：
[Query Bank 数据集构建与多数据集使用指南](../../docs/QUERY_BANK_BUILD_GUIDE_ZH.md)。

## 1. 脚本说明

| 脚本 | 用途 |
|---|---|
| `build_query_bank.py` | 创建、断点续建或复用一个 Query Bank |
| `validate_query_bank.py` | 校验 Query Bank 的文件哈希、文档哈希、查询数量和 IA 答案 |
| `inspect_query_bank.py` | 查看查询总量、攻击类型、变体、IA 答案和 benign 类别统计 |

每个目标文档最终包含 50 条查询：

| 类型 | 每文档数量 |
|---|---:|
| Direct RAG-MIA | 1 条 canonical + 4 条 paraphrase |
| S²-MIA | 1 条 canonical + 4 条 paraphrase |
| Masked MIA | 1 条 canonical + 4 条 paraphrase |
| IA | 30 条，ground truth 允许 yes、no、unknown |
| benign | 5 条，覆盖 topic、entity、event、summary、follow_up |

## 2. 运行前准备

所有命令建议从项目根目录执行：

```powershell
Set-Location D:\Project\MIAGuard
```

使用项目指定的 Conda 环境：

```powershell
conda run -n MIAGuard python --version
```

构建查询库会实际加载本地生成模型和 Embedding 模型。开始前应确认：

- `configs/query_banks/*.yaml` 引用的攻击配置存在；
- 攻击配置引用的本地模型文件完整；
- `source_run_id` 对应的 `data/runs/<run_id>/` 已经存在；
- 显存中没有同时运行其他大型模型任务。

可以先执行模型自检：

```powershell
conda run -n MIAGuard python -m miaguard.cli doctor `
  --config configs/attacks/ag_news_calibrated_int8.yaml
```

## 3. 推荐执行顺序

建议依次执行：

1. 使用 smoke 配置构建 1+1 文档的查询库；
2. 校验 smoke 查询库；
3. 查看数量与类别统计；
4. 用 smoke 查询库执行一次小实验；
5. 确认结果后再构建正式候选池。

## 4. 构建 Query Bank

### 4.1 小规模 smoke

`ag_news_smoke.yaml` 选择 1 个成员文档和 1 个非成员文档，共生成 100 条查询：

```powershell
conda run -n MIAGuard python scripts/query_bank/build_query_bank.py `
  --config configs/query_banks/ag_news_smoke.yaml `
  --bank-id ag_news_queries_smoke_v1 `
  --dataset ag_news
```

### 4.2 正式候选池

`ag_news_v1.yaml` 选择 50 个成员文档和 50 个非成员文档，共生成 5000 条查询：

```powershell
conda run -n MIAGuard python scripts/query_bank/build_query_bank.py `
  --config configs/query_banks/ag_news_v1.yaml `
  --bank-id ag_news_queries_v1 `
  --dataset ag_news
```

### 4.3 构建参数

| 参数 | 必填 | 含义 |
|---|---|---|
| `--config` | 是 | Query Bank YAML 配置路径 |
| `--bank-id` | 是 | 查询库唯一标识，同时也是输出目录名 |
| `--dataset` | 是 | 数据集 ID，例如 `ag_news` |
| `--project-root` | 否 | 项目根目录，默认是当前目录 |
| `--force-unlock` | 否 | 删除已确认失效的构建锁后继续 |

如果不是从项目根目录执行，可以显式指定：

```powershell
conda run -n MIAGuard python scripts/query_bank/build_query_bank.py `
  --config D:\Project\MIAGuard\configs\query_banks\ag_news_smoke.yaml `
  --bank-id ag_news_queries_smoke_v1 `
  --dataset ag_news `
  --project-root D:\Project\MIAGuard
```

## 5. 配置文件字段

配置示例：

```yaml
source_run_id: 20260717-ag-news-four-medium
attack_config: configs/attacks/ag_news_calibrated_int8.yaml
seed: 20260725
pool:
  members: 1
  nonmembers: 1
queries:
  paraphrases_per_attack: 4
  ia_questions_per_document: 30
  ia_batch_size: 6
  ia_max_attempts: 20
  benign_categories:
    - topic
    - entity
    - event
    - summary
    - follow_up
```

字段含义：

| 字段 | 含义 |
|---|---|
| `source_run_id` | 提供目标文档和成员标签的已准备运行 |
| `attack_config` | 本地生成模型、Embedding 模型和攻击参数配置 |
| `seed` | 文档选择与生成记录使用的固定随机种子 |
| `pool.members` | 候选池中的成员文档数 |
| `pool.nonmembers` | 候选池中的非成员文档数 |
| `paraphrases_per_attack` | 三种单轮攻击各自的改写数，当前必须为 4 |
| `ia_questions_per_document` | 每文档 IA 问题总数，当前必须为 30 |
| `ia_batch_size` | 每轮请求模型生成的 IA 候选数量上限 |
| `ia_max_attempts` | 单文档补齐 IA 问题的最大尝试轮数 |
| `benign_categories` | 五种合法查询类别，当前必须保持配置中的固定顺序 |

修改以下任一内容后，应使用新的 `bank-id`：

- `source_run_id`；
- 构建随机种子；
- 生成模型或 Embedding 模型；
- 提示词或核心生成参数。

程序会拒绝使用同一个 `bank-id` 混合不同生成条件的数据。

## 6. 断点续建

构建器按文档写入独立分片：

```text
data/query_banks/<bank_id>/<dataset_id>/.work/
```

一个文档的 50 条查询全部通过校验后，该文档分片才会被保存。进程中断后，重新执行
完全相同的构建命令即可：

```powershell
conda run -n MIAGuard python scripts/query_bank/build_query_bank.py `
  --config configs/query_banks/ag_news_v1.yaml `
  --bank-id ag_news_queries_v1 `
  --dataset ag_news
```

恢复时：

- 完整且文档哈希匹配的分片会显示 `status=reused`；
- 不完整或校验失败的分片会重新生成；
- 已经处于 `complete` 状态的 Query Bank 会直接返回，不重新加载模型。

### 6.1 处理遗留锁

构建期间会创建：

```text
data/query_banks/<bank_id>/<dataset_id>/.build.lock
```

只有在确认没有 Query Bank 构建进程运行时，才能使用：

```powershell
conda run -n MIAGuard python scripts/query_bank/build_query_bank.py `
  --config configs/query_banks/ag_news_v1.yaml `
  --bank-id ag_news_queries_v1 `
  --dataset ag_news `
  --force-unlock
```

不要在仍有构建进程运行时强制解锁，否则两个进程可能同时写入同一个查询库。

## 7. 校验 Query Bank

构建完成后执行：

```powershell
conda run -n MIAGuard python scripts/query_bank/validate_query_bank.py `
  --bank-id ag_news_queries_smoke_v1 `
  --dataset ag_news
```

校验内容包括：

- `manifest.json` 状态是否为 `complete`；
- `queries.jsonl` 文件哈希是否匹配；
- Query Bank 文档是否仍存在于源运行；
- 源文档内容哈希和成员标签是否变化；
- 每个文档是否正好包含 50 条查询；
- IA 是否正好包含 30 条 ground truth 为 yes、no 或 unknown 的问题；
- IA 是否包含规范化文本重复；
- 三种单轮攻击是否各有 1 canonical + 4 paraphrase；
- benign 是否覆盖五种类别。

正常输出示例：

```json
{
  "bank_id": "ag_news_queries_smoke_v1",
  "dataset_id": "ag_news",
  "document_count": 2,
  "query_count": 100,
  "status": "valid",
  "validated_documents": 2
}
```

## 8. 查看统计

```powershell
conda run -n MIAGuard python scripts/query_bank/inspect_query_bank.py `
  --bank-id ag_news_queries_smoke_v1 `
  --dataset ag_news
```

输出会包含：

- 文档数和查询总数；
- 各攻击类型查询数；
- canonical、paraphrase、generated 数量；
- IA yes/no/unknown 实际数量；
- benign 五类别数量；
- Query Bank SHA-256。

smoke 查询库的预期总量为：

```text
documents: 2
queries: 100
IA total: 60
IA answers: 以 inspect 输出的实际 yes/no/unknown 分布为准
```

## 9. 在实验中使用

完整 Query Bank 可以传给两阶段攻击对比脚本：

```powershell
conda run -n MIAGuard python scripts/run_two_stage_attack_comparison.py `
  --config configs/attacks/ag_news_calibrated_int8.yaml `
  --gateway-config configs/defense/two_stage_direct_enforce_calibrated_010.yaml `
  --source-run-id 20260717-ag-news-four-medium `
  --dataset ag_news `
  --output-run-id 20260725-ag-news-frozen-smoke-v1 `
  --limit-per-class 1 `
  --benign-count 2 `
  --ia-turn-count 3 `
  --query-bank-id ag_news_queries_smoke_v1 `
  --query-seed 20260725 `
  --variant-mode canonical
```

`--variant-mode` 支持：

| 模式 | 含义 |
|---|---|
| `canonical` | 使用严格复现攻击算法的查询，推荐用于攻击基线 |
| `paraphrase` | 从四条模型改写中按 seed 抽取 |
| `mixed` | 在 canonical 和 paraphrase 之间按固定逻辑抽取 |

冻结实验会生成：

```text
query_selection_manifest.json
```

该文件记录实际抽取的文档和 query ID。`run_manifest.json` 中应出现：

```json
{
  "online_query_generation": false,
  "query_bank_id": "ag_news_queries_smoke_v1"
}
```

这表示实验没有在线生成攻击或 benign 查询。目标 RAG 回答、防御判断和攻击评分仍会
正常执行模型推理。

## 10. 输出目录

```text
data/query_banks/<bank_id>/<dataset_id>/
├── .work/
│   └── <document-hash>.jsonl
├── documents.jsonl
├── generation_failures.jsonl
├── manifest.json
└── queries.jsonl
```

文件说明：

| 文件 | 内容 |
|---|---|
| `.work/*.jsonl` | 可用于断点恢复的逐文档完整分片 |
| `documents.jsonl` | 文档 ID、成员标签和源文档哈希 |
| `generation_failures.jsonl` | 生成失败的文档、错误类型和错误信息 |
| `manifest.json` | Query Bank 身份、状态、模型、数量和文件哈希 |
| `queries.jsonl` | 最终合并并稳定排序的查询数据 |

## 11. 常见问题

### `Query Bank is locked`

另一个进程正在构建，或者上次异常退出留下了锁文件。先检查是否仍有 Python/模型进程，
确认没有后再使用 `--force-unlock`。

### `use a new bank_id`

当前配置与已有 Query Bank 的源运行、seed 或模型不一致。不要覆盖旧库，请更换
`--bank-id`。

### `Query Bank is incomplete`

至少一个文档没有生成出完整的 50 条有效查询。查看：

```text
data/query_banks/<bank_id>/<dataset_id>/generation_failures.jsonl
```

修正模型输出问题或适当调整 `ia_max_attempts` 后，使用相同命令继续。

### IA 无法补齐 30 条

可能原因包括：

- 文档太短，可构造的明确事实有限；
- 模型没有返回完整的问题数组；
- 独立答案判定没有返回合法的 yes、no 或 unknown；
- 问题与已经接受的问题在规范化后完全相同；
- 问题使用了“本文”“这段文字”等模糊指代。

构建时会逐轮输出 `generated`、`duplicate`、`unverified` 和累计接受数量。
先使用 smoke 配置观察这些统计，不建议直接增加尝试次数后运行正式实验。

### 找不到模型或 CUDA 显存不足

先执行模型自检，并确认没有同时运行其他攻击或 Query Bank 构建进程：

```powershell
nvidia-smi
```

### 系统默认 Python 报 `_ssl` 错误

本项目应使用 Conda `MIAGuard` 环境，不要直接调用系统默认的 `python`：

```powershell
conda run -n MIAGuard python scripts/query_bank/build_query_bank.py --help
```
