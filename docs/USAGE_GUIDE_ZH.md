# MIAGuard RAG 成员推理攻击使用手册

本文档是当前项目的主要操作手册，适用于以下四种攻击：

- `masked_mia`：Masked MIA。
- `ia`：老师项目中的 IA。
- `direct_rag_mia`：Direct RAG-MIA。
- `s2_mia`：当前实现的语义相似度版本 S²-MIA。

当前推荐运行方式是直接使用本地 Transformers 模型，不需要 Ollama，也不连接外部模型 API：

- LLM：`LLM/mistralai/mistral-7b-instruct-v0-2`。
- Embedding：`EmbeddingModel/sentence-transformers/all_minilm_l6_v2`。
- 向量数据库：FAISS `IndexFlatIP`。
- LLM 和 Embedding 使用 GPU；当前安装的 `faiss-cpu` 在 CPU 上检索。

## 1. 项目目录约定

所有命令都应从项目根目录执行：

```powershell
Set-Location D:\Project\MIAGuard
```

主要目录如下：

```text
MIAGuard/
├── configs/                 配置文件
│   ├── attacks/             模型、检索器和攻击参数
│   ├── datasets/            数据集导入与标准化配置
│   ├── experiments/         数据集选择和攻击评测规模
│   └── models/              老师模型目录配置
├── DataSet/                 数据集描述文件和只读源数据快照
├── data/
│   ├── processed/           统一格式的成员/非成员数据池
│   ├── runs/                每次实验固定下来的目标样本
│   ├── vector_stores/       FAISS 索引
│   ├── attack_results/      四种攻击的逐样本结果和指标
│   └── manifests/           数据集校验清单
├── EmbeddingModel/          本地 Embedding 模型
├── LLM/                     本地 LLM 权重
├── scripts/                 命令入口脚本
├── src/miaguard/            攻击、模型和向量库实现
├── src/rag_mia_data/        数据集与实验运行准备实现
├── tests/                   自动测试
└── reports/                 数据分析、模型下载和历史验证报告
```

不要从其它目录直接运行相对路径命令。若必须从其它目录调用，可在攻击 CLI 中显式传入 `--project-root D:\Project\MIAGuard`，但推荐先切换到项目根目录。

## 2. 创建和激活 Conda 环境

### 2.1 第一次创建环境

```powershell
Set-Location D:\Project\MIAGuard
conda env create -f environment.yml
```

该环境固定使用 Python 3.10，并安装 CUDA 12.4 对应的 PyTorch、Transformers、Sentence Transformers、FAISS CPU、测试依赖和当前项目的 editable package。

### 2.2 激活现有环境

```powershell
conda activate MIAGuard
```

如果 PowerShell 提示不能使用 `conda activate`，先执行：

```powershell
conda init powershell
```

关闭并重新打开 PowerShell，然后再次激活环境。

不想激活环境时，也可以把后续命令中的 `python` 替换成：

```powershell
conda run -n MIAGuard python
```

例如：

```powershell
conda run -n MIAGuard python -m pytest -q
```

### 2.3 检查 Python、CUDA 和依赖

```powershell
python --version
python -c "import torch; print(torch.__version__); print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0))"
python -m pip check
```

当前机器的预期结果包括：

- Python 3.10。
- PyTorch `2.6.0+cu124`。
- `torch.cuda.is_available()` 为 `True`。
- GPU 为 NVIDIA RTX A5000。

## 3. 检查本地模型

当前四种攻击统一使用：

```text
configs/attacks/teacher_local_smoke.yaml
```

虽然文件名包含 `smoke`，但它也可以配合 pilot、medium 和 formal 实验配置使用。攻击样本数由 `configs/experiments/*.yaml` 控制，而不是由这个模型配置文件名控制。

执行模型自检：

```powershell
python -m miaguard.cli doctor `
  --config configs/attacks/teacher_local_smoke.yaml
```

该命令会实际执行一次 Embedding 和一次 Mistral 生成。正常输出应包含：

```json
{
  "embedding_backend": "sentence_transformers",
  "embedding_dimension": 384,
  "generation_backend": "transformers",
  "generation_response": "OK.",
  "status": "ok"
}
```

如果模型目录缺失，命令会明确报告缺失路径。当前攻击不要求启动 Ollama。

## 4. 当前可用数据集

数据集 ID 必须使用以下小写名称：

| 数据集 ID | 语言 | 成员池 | 非成员池 | 最大平衡评测规模 |
|---|---|---:|---:|---:|
| `ag_news` | 英文 | 8000 | 1000 | 1000+1000 |
| `healthcare_magic` | 英文 | 8000 | 1000 | 1000+1000 |
| `ms_marco` | 英文 | 8000 | 1000 | 1000+1000 |
| `nq` | 英文 | 8000 | 1000 | 1000+1000 |
| `t2ranking` | 中文 | 5000 | 5000 | 5000+5000 |

当前本地 Mistral 主要适合英文。T2Ranking 可以运行，但中文结果不能直接假设与英文模型同样可靠。

每个数据集的说明位于：

```text
DataSet/<数据集名称>/README.md
DataSet/<数据集名称>/dataset.json
```

数据集总注册表是：

```text
DataSet/registry.json
```

## 5. 数据集导入、标准化和校验

当前工作区已经完成导入和标准化。如果数据文件仍然存在，可以直接从第 6 节开始。

### 5.1 校验单个数据集

```powershell
python -m rag_mia_data.cli dataset-validate `
  --mode single `
  --include ag_news
```

### 5.2 校验多个指定数据集

`--include` 需要重复书写：

```powershell
python -m rag_mia_data.cli dataset-validate `
  --mode selected `
  --include ag_news `
  --include nq `
  --include ms_marco
```

### 5.3 校验全部数据集

```powershell
python -m rag_mia_data.cli dataset-validate --mode all
```

### 5.4 从老师项目重新导入

只有在 `DataSet/*/teacher_snapshot` 或 `data/processed/<dataset>/documents` 缺失时才需要重新执行：

```powershell
python -m rag_mia_data.cli dataset-import `
  --source-root D:\Project\MIA-lihao\IAplusBigLLM

python -m rag_mia_data.cli dataset-normalize --mode all
python -m rag_mia_data.cli dataset-validate --mode all
```

旧脚本 `scripts/prepare_datasets.ps1` 仍写着已经废弃的 `rag_env` 环境名，当前不要直接使用它。以上三个显式命令是可靠入口。

## 6. 实验配置与样本规模

实验配置位于 `configs/experiments/`。配置同时决定：

- 选择哪些数据集。
- 执行哪些攻击。
- 每种攻击使用多少成员和非成员样本。
- 运行准备结果写到哪里。

四攻击中等规模配置示例：

```yaml
profile: formal
dataset_selection:
  mode: single
  include:
    - ag_news
attacks:
  - direct_rag_mia
  - s2_mia
  - masked_mia
  - ia
target_counts:
  direct_rag_mia:
    members: 1000
    nonmembers: 1000
  s2_mia:
    members: 1000
    nonmembers: 1000
  masked_mia:
    members: 500
    nonmembers: 500
  ia:
    members: 200
    nonmembers: 200
runs_dir: data/runs
```

对应文件为：

```text
configs/experiments/four_attacks_medium.yaml
```

### 6.1 配置规则

- `profile` 只能是 `smoke`、`pilot` 或 `formal`。它是实验标签，不会自动改变样本数。
- `attacks` 只允许 `masked_mia`、`ia`、`direct_rag_mia`、`s2_mia`。
- `target_counts` 的键必须与 `attacks` 完全一致。
- 每种攻击的 `members` 和 `nonmembers` 都必须是正整数。
- 当前实现要求每种攻击成员数与非成员数相等。
- 同一个配置中的样本数会应用到所有选中的数据集。
- 数据按照 `source_index, doc_id` 排序后取前 N 条，当前不是随机抽样。

### 6.2 样本数与向量库大小的关系

当前运行准备会取四种攻击中最大的成员数作为该次运行的成员文档数，向量数据库只包含这些成员文档。

例如：

- Direct：1000 个成员。
- S²：1000 个成员。
- Masked：500 个成员。
- IA：200 个成员。

最终统一 FAISS 向量库包含 1000 条成员文档。当前实现还没有把“向量库总规模”和“攻击评测样本数”拆成两个独立配置项。

### 6.3 推荐规模

| 用途 | 推荐规模 |
|---|---|
| 快速链路检查 | 每种攻击 10+10 |
| Pilot | 每种攻击 100+100，或按成本降低 IA |
| 当前中等规模 | Direct/S² 1000+1000，Masked 500+500，IA 200+200 |
| 多数据集初测 | 每个数据集 100+100，先串行运行 |

四个攻击不要并行启动。每个进程都会加载约 13.5GB 的 Mistral BF16 权重，A5000 24GB 同时运行多个进程容易显存不足。

## 7. 选择单个、多个或全部数据集

数据集可以写入 YAML，也可以在 `prepare-run` 命令中覆盖。

### 7.1 单个数据集

```powershell
$RunId = "20260717-ag-news-example"

python -m rag_mia_data.cli prepare-run `
  --config configs/experiments/four_attacks_medium.yaml `
  --run-id $RunId `
  --mode single `
  --include ag_news
```

### 7.2 多个指定数据集

```powershell
$RunId = "20260717-selected-english"

python -m rag_mia_data.cli prepare-run `
  --config configs/experiments/four_attacks_medium.yaml `
  --run-id $RunId `
  --mode selected `
  --include ag_news `
  --include nq `
  --include ms_marco
```

### 7.3 全部数据集

```powershell
$RunId = "20260717-all-datasets"

python -m rag_mia_data.cli prepare-run `
  --config configs/experiments/four_attacks_medium.yaml `
  --run-id $RunId `
  --mode all
```

全部模式会选择所有 `enabled=true` 且 `experiment_eligible=true` 的数据集。目前是五个数据集。

由于除 T2Ranking 外的非成员池都是 1000 条，包含全部数据集时，任何单项攻击最大只能配置为 1000+1000。

### 7.4 `run_id` 规则

- 每次新实验必须使用新的 `run_id`。
- 只允许字母、数字、下划线和连字符。
- 不能覆盖已经存在的 `data/runs/<run_id>`。
- 推荐包含日期、数据集和规模，例如 `20260717-ag-news-four-medium`。

运行准备成功后会生成：

```text
data/runs/<run_id>/run_manifest.json
data/runs/<run_id>/resolved_config.yaml
data/runs/<run_id>/<dataset_id>/target_docs.jsonl
```

## 8. 构建统一 FAISS 向量数据库

每个数据集都需要单独构建一次索引：

```powershell
python scripts/build_vector_db.py `
  --config configs/attacks/teacher_local_smoke.yaml `
  --run-id $RunId `
  --dataset ag_news
```

输出目录：

```text
data/vector_stores/<run_id>/<dataset_id>/
├── index.faiss
├── documents.jsonl
└── manifest.json
```

`manifest.json` 会记录：

- 索引类型。
- 文档数量。
- 向量维度。
- Embedding 模型和后端。
- 数据集和运行 ID。

## 9. 执行四种攻击

以下命令必须在索引构建成功后执行。

### 9.1 Direct RAG-MIA

```powershell
python scripts/run_direct_rag_mia.py `
  --config configs/attacks/teacher_local_smoke.yaml `
  --run-id $RunId `
  --dataset ag_news
```

### 9.2 S²-MIA

```powershell
python scripts/run_s2_mia.py `
  --config configs/attacks/teacher_local_smoke.yaml `
  --run-id $RunId `
  --dataset ag_news
```

### 9.3 Masked MIA

```powershell
python scripts/run_masked_mia.py `
  --config configs/attacks/teacher_local_smoke.yaml `
  --run-id $RunId `
  --dataset ag_news
```

### 9.4 IA

```powershell
python scripts/run_ia.py `
  --config configs/attacks/teacher_local_smoke.yaml `
  --run-id $RunId `
  --dataset ag_news
```

### 9.5 临时限制样本数

攻击命令支持：

```powershell
--limit-per-class 10
```

它表示只执行前 10 个成员和前 10 个非成员。不要在同一个 `run_id` 中先用 `--limit-per-class`，随后又去掉限制执行全量，因为受限结果的文档顺序不是全量结果的严格前缀，断点校验会拒绝混用。快速检查应使用单独的 smoke `run_id`。

## 10. 多数据集批量执行

`prepare-run` 可以一次准备多个数据集，但索引和攻击命令仍按数据集逐个执行。

以下示例串行运行三个英文数据集：

```powershell
$RunId = "20260717-selected-english"
$Config = "configs/attacks/teacher_local_smoke.yaml"
$Datasets = @("ag_news", "nq", "ms_marco")

foreach ($Dataset in $Datasets) {
    python scripts/build_vector_db.py `
      --config $Config `
      --run-id $RunId `
      --dataset $Dataset
    if ($LASTEXITCODE -ne 0) { throw "Index failed: $Dataset" }

    foreach ($Script in @(
        "scripts/run_direct_rag_mia.py",
        "scripts/run_s2_mia.py",
        "scripts/run_masked_mia.py",
        "scripts/run_ia.py"
    )) {
        python $Script `
          --config $Config `
          --run-id $RunId `
          --dataset $Dataset
        if ($LASTEXITCODE -ne 0) {
            throw "Attack failed: $Dataset / $Script"
        }
    }
}
```

此循环是串行的，不会同时把多个 Mistral 实例加载到显存。

## 11. 输出目录和文件格式

每种攻击输出到：

```text
data/attack_results/<run_id>/<dataset_id>/<attack>/
├── results.jsonl
├── metrics.json
└── attack_manifest.json
```

某些已经执行过独立指标核验的目录还会有：

```text
metrics.recomputed.json
```

### 11.1 `results.jsonl`

每行是一个被攻击文档的 JSON 对象，主要字段包括：

- `doc_id`：文档 ID。
- `membership_label`：真实成员标签，成员为 1，非成员为 0。
- `membership_score`：攻击连续或离散分数。
- `retrieved_doc_ids`：向量库检索结果。
- 攻击特有的查询、回答、掩码或相似度信息。

### 11.2 `metrics.json`

统一指标包括：

- `sample_count`、`member_count`、`nonmember_count`。
- `threshold` 和 `threshold_source`。
- `accuracy`、`precision`、`recall`、`f1`。
- `roc_auc`。
- `tpr_at_fpr_0.001`。
- `tpr_at_fpr_0.01`。
- `confusion_matrix`。
- `member_score_mean` 和 `nonmember_score_mean`。

S²-MIA 当前固定阈值 0.7 未经过独立校准。评价它时应优先查看 ROC-AUC、低 FPR TPR 和成员/非成员分数分布，不应只看固定阈值 Accuracy。

### 11.3 `attack_manifest.json`

它是攻击审计记录，包含：

- 攻击名称。
- 数据集和运行 ID。
- LLM/Embedding 模型及后端。
- 样本数量。
- 攻击关键参数。
- 是否使用 Shadow 数据。
- 完成时间和参考实现。

## 12. 重新计算攻击指标

例如重新计算 S²-MIA：

```powershell
$ResultDir = "data/attack_results/$RunId/ag_news/s2_mia"

python scripts/compute_attack_metrics.py `
  --results "$ResultDir/results.jsonl" `
  --output "$ResultDir/metrics.recomputed.json" `
  --threshold 0.7
```

其它攻击当前阈值通常是 0.5：

```powershell
python scripts/compute_attack_metrics.py `
  --results "data/attack_results/$RunId/ag_news/masked_mia/results.jsonl" `
  --output "data/attack_results/$RunId/ag_news/masked_mia/metrics.recomputed.json" `
  --threshold 0.5
```

## 13. 汇总查看多个攻击指标

```powershell
$Base = "data/attack_results/$RunId/ag_news"

Get-ChildItem -LiteralPath $Base -Recurse -Filter metrics.json | ForEach-Object {
    $Metric = Get-Content -LiteralPath $_.FullName -Raw | ConvertFrom-Json
    [pscustomobject]@{
        Attack = $_.Directory.Name
        Samples = $Metric.sample_count
        Accuracy = $Metric.accuracy
        F1 = $Metric.f1
        ROC_AUC = $Metric.roc_auc
        TPR_001 = $Metric.tpr_at_fpr_0.01
    }
} | Format-Table -AutoSize
```

## 14. 攻击日志在哪里

当前项目没有自动创建独立的 `attack.log`。日志分成三类：

1. 终端输出：模型加载进度、错误信息和最终指标 JSON。
2. `results.jsonl`：逐样本结构化攻击记录。
3. `attack_manifest.json`：最终运行审计信息。

如果希望保存终端日志，运行攻击前创建日志目录并使用 `Tee-Object`：

```powershell
$LogDir = "data/logs/$RunId/ag_news"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

python scripts/run_s2_mia.py `
  --config configs/attacks/teacher_local_smoke.yaml `
  --run-id $RunId `
  --dataset ag_news `
  2>&1 | Tee-Object -FilePath "$LogDir/s2_mia.log"

if ($LASTEXITCODE -ne 0) {
    throw "S2-MIA failed"
}
```

建议每个攻击分别保存：

```text
data/logs/<run_id>/<dataset_id>/build_index.log
data/logs/<run_id>/<dataset_id>/direct_rag_mia.log
data/logs/<run_id>/<dataset_id>/s2_mia.log
data/logs/<run_id>/<dataset_id>/masked_mia.log
data/logs/<run_id>/<dataset_id>/ia.log
```

Windows 下攻击运行时不要用编辑器持续打开或轮询正在写入的 `results.jsonl`。程序使用原子替换保存断点，并发读取可能导致 Windows 文件共享锁冲突。运行进度优先通过终端、保存的日志和 `nvidia-smi` 查看。

```powershell
nvidia-smi
```

## 15. 断点续跑

四种攻击都支持从已经完整写入的文档前缀继续：

```powershell
python scripts/run_s2_mia.py `
  --config configs/attacks/teacher_local_smoke.yaml `
  --run-id $RunId `
  --dataset ag_news
```

如果上一次中断，重复完全相同的命令即可。断点续跑会检查：

- 已有结果中的文档 ID 顺序必须与本次请求一致。
- 已有结果必须是本次目标文档序列的严格前缀。
- 不允许把其它数据集、其它 `run_id` 或不同限制规模的结果混入。

如果攻击已经全部完成，再执行相同命令会复用结果并重新生成最终指标和清单，不会重复推理。

## 16. 当前已完成的中等规模结果

当前完整运行 ID：

```text
20260717-ag-news-four-medium
```

结果位置：

```text
data/attack_results/20260717-ag-news-four-medium/ag_news/
```

| 攻击 | 样本数 | Accuracy | ROC-AUC |
|---|---:|---:|---:|
| Direct RAG-MIA | 2000 | 0.9795 | 0.9795 |
| S²-MIA | 2000 | 0.5105 | 0.7986 |
| Masked MIA | 1000 | 0.6040 | 0.7696 |
| IA | 400 | 0.7975 | 0.8290 |

这些结果证明攻击链路能够执行，但不等于完整复现所有原论文设置。特别是当前 S²-MIA 是 all-MiniLM 余弦相似度版本，没有实现原论文完整的 BLEU+困惑度双特征。

## 17. 常见错误

### `run_id already exists`

同一个运行 ID 不能重复准备。为新实验换一个新的 `run_id`。如果只是恢复已有攻击，不要再次执行 `prepare-run`，直接重复攻击命令。

### `Vector index ...` 或找不到索引

先为对应 `run_id + dataset_id` 执行 `build_vector_db.py`。

### `Existing attack results are not a prefix`

已有断点结果与本次请求的文档序列不一致。常见原因是同一运行中先使用了 `--limit-per-class`，随后改成全量。使用新的 smoke `run_id` 做小规模检查。

### CUDA out of memory

- 确认没有同时运行多个攻击。
- 用 `nvidia-smi` 检查其它 GPU 进程。
- 当前 Mistral BF16 单进程约使用 14～16GB 显存。

### `Model returned incomplete JSON`

Masked MIA 和 IA 已针对常见不完整 JSON、内部引号及 `\$` 转义增加有限容错或重试。若仍然退出，直接重复同一命令从断点继续，并保留终端日志用于定位具体文档。

### `member capacity ... is below required count`

配置样本数超过了该数据集池容量。参照第 4 节容量表降低样本数。

### 中文 T2Ranking 效果异常

当前 Mistral 主要面向英文。运行链路成功不代表中文攻击性能可信。正式中文实验应使用经过验证的中文模型，并创建独立攻击配置。

## 18. 完整验证命令

代码或环境发生变化后执行：

```powershell
python -m pytest -q
python -m pip check
python -m miaguard.cli doctor `
  --config configs/attacks/teacher_local_smoke.yaml
```

当前基线为：

- `105 passed, 1 skipped`。
- `pip check` 无依赖冲突。
- Mistral 生成和 all-MiniLM CUDA Embedding 正常。

