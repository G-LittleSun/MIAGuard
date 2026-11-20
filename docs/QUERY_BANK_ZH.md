# 离线 Query Bank 使用说明

2026-11-04 版本提示：项目最新完整查询库为 `ag_news_queries_v2`（7,632 条），配套 `ag_news_threshold_v2`；后续防御数据复用显式使用其 train，见[数据复用规则](DEFENSE_DATA_REUSE_ZH.md)。已完成 Judge v3 对照与 E00 使用 v1（5,956 条），保留原身份。v2 继承 v1 的全部攻击与文档分配，扩充正常查询且审核 pending；下列 benign 每文档 5 条及旧命令说明属于基础/v1 构建规则，不能当 v2 实际数量。不能仅改命令的 bank_id 而混用另一个 split 或旧 trace。

Query Bank 会提前为每个目标文档生成并冻结以下查询：

- Direct RAG-MIA：1 条 canonical + 4 条 paraphrase；
- S²-MIA：1 条 canonical + 4 条 paraphrase；
- Masked MIA：1 条 canonical + 4 条 paraphrase；
- IA：30 条，独立 ground truth 允许 yes、no、unknown，不要求固定比例；
- benign：topic、entity、event、summary、follow_up 各 1 条。

正式实验读取冻结查询，不再生成 IA 问题、IA ground truth、Masked 掩码或 benign 查询。
目标 RAG 回答和防御模型判断仍会正常调用本地模型。

IA 构建按小批次生成问题，再根据源文档独立判定 ground truth。构建器只删除规范化
文本完全相同的问题，不使用 embedding 语义相似度作为硬淘汰条件。每轮日志会显示
生成、重复、未验证和累计接受数量；非平衡的 yes/no/unknown 分布属于合法结果。

## 1. 小规模手动验证

从项目根目录执行：

```powershell
conda run -n MIAGuard python scripts/query_bank/build_query_bank.py `
  --config configs/query_banks/ag_news_smoke.yaml `
  --bank-id ag_news_queries_smoke_v1 `
  --dataset ag_news
```

该命令会实际加载本地模型，为 1 个成员文档和 1 个非成员文档各生成 50 条查询。
中途退出后，重新执行相同命令会复用已经完整写入的文档分片。

校验：

```powershell
conda run -n MIAGuard python scripts/query_bank/validate_query_bank.py `
  --bank-id ag_news_queries_smoke_v1 `
  --dataset ag_news
```

查看统计：

```powershell
conda run -n MIAGuard python scripts/query_bank/inspect_query_bank.py `
  --bank-id ag_news_queries_smoke_v1 `
  --dataset ag_news
```

## 2. 构建 50+50 候选池

```powershell
conda run -n MIAGuard python scripts/query_bank/build_query_bank.py `
  --config configs/query_banks/ag_news_v1.yaml `
  --bank-id ag_news_queries_v1 `
  --dataset ag_news
```

同一个 `bank_id` 绑定源运行、随机种子、生成模型和嵌入模型。修改这些配置后必须使用
新的 `bank_id`，程序不会把不同生成条件的分片混合。

如果进程异常退出并遗留锁文件，先确认没有 Query Bank 构建进程正在运行，再使用：

```powershell
conda run -n MIAGuard python scripts/query_bank/build_query_bank.py `
  --config configs/query_banks/ag_news_v1.yaml `
  --bank-id ag_news_queries_v1 `
  --dataset ag_news `
  --force-unlock
```

## 3. 使用冻结查询运行两阶段实验

先完成并校验 Query Bank，然后执行：

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

正式 10+10 实验也可以运行：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_full_10x10.ps1 `
  -QueryBankId ag_news_queries_v1 `
  -QuerySeed 20260725
```

结果目录中的 `query_selection_manifest.json` 会记录精确的文档和 query ID。
`run_manifest.json` 中的 `online_query_generation` 应为 `false`。

## 4. 文件位置

```text
data/query_banks/<bank_id>/<dataset_id>/
├── .work/
├── documents.jsonl
├── generation_failures.jsonl
├── manifest.json
└── queries.jsonl
```

只有 `manifest.json` 状态为 `complete` 且文件哈希匹配时，冻结实验才允许启动。
