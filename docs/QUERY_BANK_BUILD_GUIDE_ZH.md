# Query Bank 数据集构建与多数据集使用指南

本文档总结 MIAGuard 当前离线查询数据集（Query Bank）的完整构建流程，并说明如何将同一套脚本用于 AG News 之外的数据集。

## 1. 结论

当前脚本支持为其他数据集生成查询数据，不仅限于 AG News。构建器通过命令行参数 `--dataset` 和源运行的 `run_manifest.json` 查找目标文档，核心代码中没有写死 AG News 的文档内容或文档 ID。

不过需要区分两种“支持”：

- **接口支持**：只要数据集满足本文的数据格式和数量要求，就可以调用现有脚本构建 Query Bank。
- **已经验证**：目前只有 AG News 完成了正式的 50 个成员文档、50 个非成员文档构建及完整校验。其他数据集在正式构建前必须先执行 1+1 smoke test。

截至 2026-08-03，AG News 正式 Query Bank 的状态为：

| 项目 | 结果 |
|---|---:|
| Bank ID | `ag_news_queries_v1` |
| 数据集 | `ag_news` |
| 文档数 | 100（50 member + 50 nonmember） |
| 查询数 | 5000 |
| Direct RAG-MIA | 500 |
| S²-MIA | 500 |
| Masked MIA | 500 |
| IA | 3000 |
| benign | 500 |
| IA yes / no / unknown | 1143 / 352 / 1505 |
| 状态 | `complete`，校验结果为 `valid` |
| `queries.jsonl` SHA-256 | `46b32cdba568badd465a25016e0ab0c2d7f60950904d98207015cb2b84621e4b` |

## 2. 为什么要预先构建 Query Bank

原实验流程在每次运行时调用本地大模型生成攻击查询和正常查询。即使目标文档数量很少，模型加载、IA 多轮生成、答案验证和失败重试也会占用大量时间。

Query Bank 将这部分工作前移：

```text
源运行中的目标文档
    ↓
离线生成并校验每个文档的 50 条查询
    ↓
保存为带版本、哈希和成员标签的 Query Bank
    ↓
正式实验按 seed 抽取已有查询
```

正式实验不再在线生成 IA 问题、Masked MIA 掩码、攻击改写或 benign 查询，但以下推理仍然正常执行：

- 目标 RAG 根据查询检索并回答；
- 防御模型判断查询或会话；
- 攻击算法计算得分和成员推断结果。

因此，Query Bank 消除的是“重复构造查询”的时间，而不是整个实验中的模型推理时间。

## 3. 每个目标文档生成的数据

当前 schema 固定要求每个目标文档恰好生成 50 条查询：

| 查询类型 | canonical | paraphrase/generated | 每文档合计 |
|---|---:|---:|---:|
| Direct RAG-MIA | 1 | 4 | 5 |
| S²-MIA | 1 | 4 | 5 |
| Masked MIA | 1 | 4 | 5 |
| IA | 0 | 30 | 30 |
| benign | 0 | 5 | 5 |
| **合计** | **3** | **47** | **50** |

### 3.1 Direct RAG-MIA

- canonical 查询由程序根据目标文档确定性构造；
- 模型只生成 4 条简短的等价攻击指令；
- 程序再把完整目标文本拼接到每条指令后。

这样无需让模型把一篇长新闻或长文档重复输出 4 次，也避免因为输出 token 限制导致正文被截断。

### 3.2 S²-MIA

- 程序从目标文档提取固定词数的开头 `prefix`；
- canonical 查询要求根据 Context 续写该开头；
- 模型只生成 4 条等价的续写指令；
- 程序把同一个 `prefix` 拼接到 4 条指令后。

`prefix` 的词数来自攻击配置中的 `s2_mia.prefix_words`。

### 3.3 Masked MIA

- 构建器只为文档生成一次 masked passage 和标准答案；
- canonical 查询使用该 masked passage；
- 模型只生成 4 条简短的等价恢复指令；
- 程序把同一个 masked passage 拼接到 4 条指令后。

掩码数量来自攻击配置中的 `masked_mia.mask_count`。完整 masked passage 不再要求模型重复输出 4 次。

### 3.4 IA

每个目标文档必须得到 30 条互不重复、可独立判定的问题。流程为：

1. 模型根据源文档分批生成候选问题和简短主题摘要；
2. 程序过滤空问题、模糊指代和规范化后完全重复的问题；
3. 使用源文档对候选问题进行独立答案验证；
4. 只接受答案为 `yes`、`no` 或 `unknown` 的问题；
5. 不足 30 条时继续生成，并轮换问题角度；
6. 达到 30 条后立即截断，不允许超额写入；
7. 达到 `ia_max_attempts` 仍不足 30 条时，该文档构建失败。

IA 不再强制 yes/no 比例平衡。`unknown` 是合法 ground truth，实际分布由文档内容和生成结果决定。

构建日志示例中的字段含义：

| 字段 | 含义 |
|---|---|
| `requested` | 本轮要求生成的问题数 |
| `generated` | 本轮解析出的候选数 |
| `invalid` | 空内容、模糊指代等无效问题数 |
| `duplicate` | 与已接受问题或本轮问题完全重复的数量 |
| `unverified` | 未得到合法 yes/no/unknown 标签的数量 |
| `accepted` | 本轮接受数量 |
| `total` | 当前累计接受数量，目标为 30 |
| `generation_fallback` | JSON 失败后是否使用纯文本回退 |
| `novelty_repair` | 重复严重时是否进行了新角度修复 |

### 3.5 benign

每个文档生成 5 条正常查询，类别固定为：

- `topic`
- `entity`
- `event`
- `summary`
- `follow_up`

模型首次 JSON 输出缺少某个类别时，程序会单独补生成该类别。五个类别未全部得到有效问题时，文档构建失败。

## 4. 完整构建流程

### 4.1 读取并选择目标文档

Query Bank YAML 中的 `source_run_id` 指向：

```text
data/runs/<source_run_id>/run_manifest.json
```

构建器从以下字段获取数据集文档路径：

```text
dataset_runs.<dataset_id>.target_docs_path
```

随后按 `membership_label` 分为 member 和 nonmember，并使用固定 seed 分别打乱后抽取指定数量。源运行中任一类别数量不足都会立即报错。

### 4.2 校验模型和 Query Bank 身份

构建器加载 Query Bank YAML 引用的攻击配置，并检查本地生成模型和 Embedding 模型路径。已有 `bank_id` 会绑定：

- `source_run_id`
- `seed`
- `generation_model`
- `embedding_model`

这些身份字段发生变化时必须使用新的 `bank_id`，程序会拒绝把不同生成条件的分片混在同一个库中。

攻击配置中的生成模型、掩码数量、Masked 输出长度、S² prefix 长度和 IA 生成长度会影响查询构造。攻击判定 threshold 不参与 Query Bank 查询生成，但建议为每个数据集保留独立攻击配置，以保证实验来源清晰。

### 4.3 按文档生成和校验

构建器依次为每个文档构建 50 条记录，并执行以下校验：

- `dataset_id`、`doc_id`、成员标签和源文档 SHA-256 一致；
- 三种单轮攻击各有 1 条 canonical 和 4 条 paraphrase；
- IA 恰好 30 条，ground truth 只能为 yes/no/unknown；
- IA 不包含规范化文本完全相同的问题；
- benign 恰好覆盖五种类别；
- 所有记录状态均为 `accepted`；
- 每条查询的稳定 `query_id` 与字段一致。

只有一个文档的 50 条查询全部通过校验后，才写入该文档的 `.work` 分片。

### 4.4 断点续建和失败记录

中断后重新执行完全相同的命令时：

- 已完成且文档哈希匹配的分片显示 `status=reused`；
- 不完整或失效的分片会被重新生成；
- 失败信息追加到 `generation_failures.jsonl`；
- 所有文档成功前，`manifest.json` 状态保持 `incomplete`；
- 已经完整的 Query Bank 会直接复用，不重新加载模型。

构建期间存在 `.build.lock`，用于避免两个进程同时写入同一个 Bank。只有确认原进程已经退出时才可使用 `--force-unlock`。

### 4.5 合并并完成

所有文档成功后，构建器合并分片，生成稳定排序的 `documents.jsonl` 和 `queries.jsonl`，计算文件 SHA-256，并把 `manifest.json` 状态改为 `complete`。

## 5. 运行前的数据要求

目标数据集必须已经存在于某个源运行中。最低文档字段要求为：

| 字段 | 要求 |
|---|---|
| `dataset_id` | 与命令行 `--dataset` 一致 |
| `doc_id` | 数据集内唯一且稳定 |
| `text` | 非空目标文档正文 |
| `membership_label` | 只能为 `0` 或 `1` |

项目当前规范化目标文档还通常包含 `language`、`metadata`、`source_index` 和 `source_partition`。

源运行 manifest 示例：

```json
{
  "dataset_runs": {
    "healthcare_magic": {
      "target_docs_path": "healthcare_magic/target_docs.jsonl"
    }
  }
}
```

对应文件位置：

```text
data/runs/<source_run_id>/healthcare_magic/target_docs.jsonl
```

如果要构建 50+50 正式候选池，源文件必须至少包含 50 个 member 和 50 个 nonmember。

## 6. AG News 当前使用方法

所有命令均从项目根目录执行：

```powershell
Set-Location D:\Project\MIAGuard
```

### 6.1 Smoke 构建

```powershell
conda run -n MIAGuard python scripts/query_bank/build_query_bank.py `
  --config configs/query_banks/ag_news_smoke.yaml `
  --bank-id ag_news_queries_smoke_v1 `
  --dataset ag_news
```

### 6.2 正式 50+50 构建

```powershell
conda run -n MIAGuard python scripts/query_bank/build_query_bank.py `
  --config configs/query_banks/ag_news_v1.yaml `
  --bank-id ag_news_queries_v1 `
  --dataset ag_news
```

### 6.3 校验

```powershell
conda run -n MIAGuard python scripts/query_bank/validate_query_bank.py `
  --bank-id ag_news_queries_v1 `
  --dataset ag_news
```

成功结果应包含：

```json
{
  "document_count": 100,
  "query_count": 5000,
  "status": "valid",
  "validated_documents": 100
}
```

### 6.4 查看分布统计

```powershell
conda run -n MIAGuard python scripts/query_bank/inspect_query_bank.py `
  --bank-id ag_news_queries_v1 `
  --dataset ag_news
```

## 7. 为其他数据集构建 Query Bank

### 7.1 当前可直接用于 smoke 的源运行

项目中的 `20260715-all-smoke` 源运行已经登记以下数据集：

| `dataset_id` | member | nonmember | 备注 |
|---|---:|---:|---|
| `ag_news` | 10 | 10 | 英文新闻 |
| `healthcare_magic` | 10 | 10 | 英文医疗对话/文本 |
| `ms_marco` | 10 | 10 | 英文检索文本 |
| `nq` | 10 | 10 | 英文问答/检索文本 |
| `t2ranking` | 10 | 10 | 中文检索文本 |

该运行最多支持每个数据集构建 10+10，不能用于 50+50 正式候选池。正式构建前需要准备包含足够文档的新源运行。

### 7.2 新建 Query Bank YAML

建议每个数据集建立独立配置，例如：

```text
configs/query_banks/healthcare_magic_smoke.yaml
```

内容模板：

```yaml
source_run_id: 20260715-all-smoke
attack_config: configs/attacks/teacher_local_smoke.yaml
seed: 20260803
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

注意：

- `paraphrases_per_attack` 当前必须为 `4`；
- `ia_questions_per_document` 当前必须为 `30`；
- `benign_categories` 必须保留这五项及其顺序；
- `teacher_local_smoke.yaml` 是可用的通用本地模型配置示例；如果显存有限，建议复制现有 int8 配置形成数据集专用版本，并去除或更新 AG News 专属的阈值来源说明；
- 调整模型、seed 或核心生成参数后使用新的 `bank_id`。

### 7.3 构建 healthcare_magic 示例

```powershell
conda run -n MIAGuard python scripts/query_bank/build_query_bank.py `
  --config configs/query_banks/healthcare_magic_smoke.yaml `
  --bank-id healthcare_magic_queries_smoke_v1 `
  --dataset healthcare_magic
```

校验：

```powershell
conda run -n MIAGuard python scripts/query_bank/validate_query_bank.py `
  --bank-id healthcare_magic_queries_smoke_v1 `
  --dataset healthcare_magic
```

查看统计：

```powershell
conda run -n MIAGuard python scripts/query_bank/inspect_query_bank.py `
  --bank-id healthcare_magic_queries_smoke_v1 `
  --dataset healthcare_magic
```

### 7.4 构建其他现有数据集

对 `ms_marco`、`nq` 和 `t2ranking`，复制同一个 YAML 模板并同时替换：

1. YAML 文件名；
2. 命令中的 `--config`；
3. `--bank-id`；
4. `--dataset`。

例如 NQ：

```powershell
conda run -n MIAGuard python scripts/query_bank/build_query_bank.py `
  --config configs/query_banks/nq_smoke.yaml `
  --bank-id nq_queries_smoke_v1 `
  --dataset nq
```

### 7.5 正式构建模板

在新的源运行已经提供至少 50+50 文档后，将配置改为：

```yaml
source_run_id: <formal_source_run_id>
attack_config: configs/attacks/<dataset_specific_attack_config>.yaml
seed: 20260803
pool:
  members: 50
  nonmembers: 50
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

执行：

```powershell
conda run -n MIAGuard python scripts/query_bank/build_query_bank.py `
  --config configs/query_banks/<dataset>_v1.yaml `
  --bank-id <dataset>_queries_v1 `
  --dataset <dataset>
```

### 7.6 多数据集适配注意事项

- 当前生成提示词为英文。英文数据集可以直接 smoke；中文 `t2ranking` 虽然数据接口兼容，但必须检查问题语言、掩码效果和 yes/no/unknown 验证质量。
- 医疗等领域文本应人工抽查生成问题是否准确，Query Bank 校验通过只代表结构与数量合法，不等于事实语义绝对正确。
- 极短或事实稀疏的文档可能难以产生 30 条不重复 IA 问题；先查看每轮日志，不应直接无限提高 `ia_max_attempts`。
- `doc_id` 和源文档正文必须保持稳定。正文改变会导致 SHA-256 不匹配，已有分片不能复用。
- 正式实验使用的 `source_run_id`、数据集和目标文档必须与 Query Bank 对应，不能跨数据集或跨源文档混用。

## 8. 后台运行和进度检查

在 PowerShell 中后台启动并把输出写入日志：

```powershell
New-Item -ItemType Directory -Force -Path logs | Out-Null
$logPath = "logs/query_bank_healthcare_magic_v1.log"
$process = Start-Process `
  -FilePath "conda" `
  -ArgumentList @(
    "run", "-n", "MIAGuard", "python",
    "scripts/query_bank/build_query_bank.py",
    "--config", "configs/query_banks/healthcare_magic_v1.yaml",
    "--bank-id", "healthcare_magic_queries_v1",
    "--dataset", "healthcare_magic"
  ) `
  -RedirectStandardOutput $logPath `
  -RedirectStandardError "logs/query_bank_healthcare_magic_v1.err.log" `
  -WindowStyle Hidden `
  -PassThru
$process.Id
```

查看最新日志：

```powershell
Get-Content logs/query_bank_healthcare_magic_v1.log -Tail 50
Get-Content logs/query_bank_healthcare_magic_v1.err.log -Tail 50
```

检查进程：

```powershell
Get-Process -Id <PID>
```

## 9. 输出目录和文件

```text
data/query_banks/<bank_id>/<dataset_id>/
├── .work/
│   └── <document-hash>.jsonl
├── .build.lock
├── documents.jsonl
├── generation_failures.jsonl
├── manifest.json
└── queries.jsonl
```

| 文件 | 作用 |
|---|---|
| `.work/*.jsonl` | 每个文档的完整分片，用于断点恢复 |
| `.build.lock` | 构建锁，仅构建期间存在 |
| `documents.jsonl` | 被选中的文档 ID、成员标签和源文档哈希 |
| `generation_failures.jsonl` | 历史生成失败信息 |
| `manifest.json` | Bank 身份、模型、状态、数量和 SHA-256 |
| `queries.jsonl` | 最终合并的查询数据 |

只有 `manifest.json` 为 `complete` 且完整校验通过后，才应在正式实验中使用该 Query Bank。

## 10. 常见问题与处理

### 10.1 `Source run does not contain enough member/nonmember documents`

YAML 中 `pool.members` 或 `pool.nonmembers` 超过源运行实际数量。减小 smoke 数量，或者重新准备包含足够目标文档的正式源运行。

### 10.2 `Query Bank is incomplete`

至少一个文档未得到完整的 50 条有效查询。先查看：

```text
data/query_banks/<bank_id>/<dataset_id>/generation_failures.jsonl
```

修复问题后重新执行相同命令，成功分片会自动复用。

### 10.3 IA 仍不足 30 条

常见原因包括文档过短、候选重复、模型输出无法解析或答案未通过验证。应先根据日志判断主要损耗发生在 `invalid`、`duplicate` 还是 `unverified`，再决定是否调整模型或 `ia_max_attempts`。

### 10.4 `Existing Query Bank identity differs`

当前配置与已有 Bank 的源运行、seed 或模型不一致。保留旧库并使用新的 `bank_id`，不要覆盖或手动混合分片。

### 10.5 `Query Bank is locked`

先确认没有仍在运行的构建进程。确认锁为异常退出遗留后才执行：

```powershell
conda run -n MIAGuard python scripts/query_bank/build_query_bank.py `
  --config configs/query_banks/<dataset>_v1.yaml `
  --bank-id <dataset>_queries_v1 `
  --dataset <dataset> `
  --force-unlock
```

### 10.6 模型找不到或显存不足

先运行模型自检：

```powershell
conda run -n MIAGuard python -m miaguard.cli doctor `
  --config configs/attacks/<attack_config>.yaml
```

并检查：

```powershell
nvidia-smi
```

## 11. 推荐操作顺序

为任意新数据集构建 Query Bank 时，推荐严格按以下顺序执行：

1. 确认源运行 manifest 已登记该数据集；
2. 检查目标文档字段、成员标签和两类数量；
3. 新建该数据集专用的 Query Bank YAML；
4. 先构建 1+1 smoke Bank；
5. 运行 `validate_query_bank.py`；
6. 运行 `inspect_query_bank.py` 并人工抽查各攻击类型；
7. 准备足够规模的正式源运行；
8. 使用新的正式 `bank_id` 构建候选池；
9. 完整校验后再交给实验脚本抽取查询。

脚本参数的简明说明见 [`scripts/query_bank/README.md`](../scripts/query_bank/README.md)。
