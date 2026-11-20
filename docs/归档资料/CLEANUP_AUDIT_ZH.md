# MIAGuard 文件清理审计

审计时间：2026-07-17。保守清理执行时间：2026-07-20。

本文档同时记录清理候选和实际执行结果。2026-07-20 已删除明确可再生或已经失效的非数据文件；`DataSet/`、`data/`、数据描述、向量库和攻击结果均未清理。

## 1. 结论摘要

最明确、最安全的文档清理项是：

```text
docs/superpowers/
```

该目录只有历史设计稿和执行计划，共 4 个 Markdown 文件，约 100KB。已经检查代码、测试和配置，没有任何运行路径引用 `docs/superpowers`；除本文的清理说明外，其它现行文档也不依赖它。运行数据准备、模型加载、FAISS 和四种攻击都不会读取它，可以整体删除。

空间占用最大的可选清理项不是文档，而是三个未下载完整的模型目录，共约 12.89GB。它们当前不可运行，也没有被活动攻击配置引用；但删除后未来继续下载时需要重新下载已完成的首个分片。

## 2. 已清理的安全生成物

以下内容都是缓存、生成元数据、失效日志或空目录，不影响源代码和已有实验结果，已于 2026-07-20 清理。

### 2.1 历史 Superpowers 文档

```text
docs/superpowers/plans/2026-07-14-miafence-foundation-through-query-schema.md
docs/superpowers/plans/2026-07-15-teacher-mia-dataset-onboarding.md
docs/superpowers/specs/2026-07-14-miafence-foundation-through-query-schema-design.md
docs/superpowers/specs/2026-07-15-teacher-mia-dataset-import-design.md
```

用途只是记录当时的设计和实施步骤。当前实现已经落在 `src/`、`configs/`、`schemas/` 和正式使用手册中。

### 2.2 Python 和 pytest 缓存

```text
.pytest_cache/
scripts/__pycache__/
src/miaguard/__pycache__/
src/rag_mia_data/__pycache__/
tests/__pycache__/
src/miaguard.egg-info/
src/rag_mia_data.egg-info/
```

这些目录会被 pytest、Python 或 `pip install -e .` 自动重新生成。项目 `.gitignore` 已忽略其中大部分内容。

### 2.3 空目录

```text
models/downloads/
```

该空目录已删除。以下空目录属于数据处理约定，本轮按“保留全部数据集相关内容”的要求保留：

```text
data/processed/benign/
data/processed/attacks/direct_ask/
data/processed/attacks/ia/
data/processed/attacks/mask_based/
data/processed/attacks/s2mia/
```

当前四种攻击不使用这些空目录，但保留它们不会影响运行。

### 2.4 模型下载过程日志

`reports/` 下列模式的文件只记录已经结束的下载尝试，可删除：

```text
reports/download_*.stdout.log
reports/download_*.stderr.log
reports/model_download*.stdout.log
reports/model_download*.stderr.log
reports/chunked_*.stdout.log
reports/chunked_*.stderr.log
reports/teacher_models_public_pipeline*.stdout.log
reports/teacher_models_public_pipeline*.stderr.log
```

这些日志已全部删除。它们总占用很小，清理的主要价值是减少目录噪声，不是释放大量磁盘。

建议保留：

```text
reports/teacher_model_inventory.active.json
reports/teacher_model_inventory.json
```

这两个文件记录模型完整性状态。

### 2.5 重算指标副本

以下模式是验证过程中生成的重复指标：

```text
data/attack_results/**/metrics.recomputed.json
```

已经确认它们与对应的 `metrics.json` 一致。若不需要保留“独立重算通过”的证据，可以删除；保留它们也只占很小空间。

## 3. 可以删除，但会丢失历史验证记录

### 3.1 旧 smoke 运行

当前最有价值的完整扩容运行是：

```text
20260717-ag-news-four-medium
```

建议保留它在以下三个位置的配套目录：

```text
data/runs/20260717-ag-news-four-medium/
data/vector_stores/20260717-ag-news-four-medium/
data/attack_results/20260717-ag-news-four-medium/
```

以下是早期小规模或旧 Ollama 验证，可在不需要历史对照时删除：

```text
data/runs/20260715-ag-news-smoke/
data/vector_stores/20260715-ag-news-smoke/
data/attack_results/20260715-ag-news-smoke/

data/runs/20260716-ag-news-baseline-smoke/
data/vector_stores/20260716-ag-news-baseline-smoke/
data/attack_results/20260716-ag-news-baseline-smoke/

data/runs/20260716-ag-news-teacher-local-smoke/
data/vector_stores/20260716-ag-news-teacher-local-smoke/
data/attack_results/20260716-ag-news-teacher-local-smoke/

data/runs/20260715-all-smoke/
data/runs/20260715-all-smoke-repeat/
```

删除某次运行时，应同时检查 `runs`、`vector_stores` 和 `attack_results` 三个位置，避免留下孤立文件。

### 3.2 历史迁移报告

```text
reports/attack_migration_verification.json
```

它记录旧 Ollama 迁移检查，不是当前 Transformers 扩容实验的结果。若不需要迁移历史，可以删除。

## 4. 已过时或当前不推荐使用的文件

这些文件不一定要删除，但不应作为当前主要入口。

### 4.1 两个旧 PowerShell 脚本

```text
scripts/run_pipeline.ps1
scripts/prepare_datasets.ps1
```

它们内部仍调用 Conda 环境 `rag_env`，而当前统一环境是 `MIAGuard`。当前使用手册已经给出等价的显式命令。如果不打算修正旧脚本，可以删除；如果保留，应先把环境名更新后再使用。

### 4.2 旧 Ollama 验证入口

```text
scripts/verify_migration.py
configs/attacks/ollama_smoke.yaml
configs/attacks/ollama_formal.yaml
```

当前活动配置是：

```text
configs/attacks/teacher_local_smoke.yaml
```

如果以后完全不再使用 Ollama，可以删除旧 Ollama 配置和旧验证脚本。核心攻击实现仍支持 Ollama 后端，因此删除这些配置不会删除 Ollama 功能代码。

### 4.3 README 状态

根目录原 `README.md` 包含旧环境、Ollama 和两攻击阶段的信息，而且部分中文已经乱码。本次已经将它替换为简短入口 README。当前新的 `README.md` 应保留，并以 `docs/USAGE_GUIDE_ZH.md` 作为权威操作手册。

### 4.4 早期专题文档

以下文档不参与运行：

```text
docs/attack_migration.md
docs/baseline_rag_mia_attacks.md
docs/teacher_local_runtime.md
docs/teacher_models.md
```

分类建议：

- `attack_migration.md`：保留，记录 Masked MIA/IA 与老师代码的对应关系。
- `baseline_rag_mia_attacks.md`：保留，记录 Direct/S² 的论文与实现依据。
- `teacher_models.md`：如果未来仍管理或下载老师模型，保留。
- `teacher_local_runtime.md`：操作命令已被新手册覆盖，可以归档或删除，但其中的模型替代限制仍有参考价值。

`docs/data_dictionary.md` 描述数据字段和 JSON Schema，建议保留。

## 5. 大空间清理候选：未完成模型

以下三个目录不是完整模型，当前不能加载，也没有被 `teacher_local_smoke.yaml` 引用：

| 目录 | 当前大小 | 状态 |
|---|---:|---|
| `LLM/glm-4-9b-chat/` | 约 4.66GB | 只有部分分片/首分片 |
| `LLM/phi-4/` | 约 4.60GB | 只有部分分片/首分片 |
| `LLM/Qwen2.5-14B-Instruct-1M/` | 约 3.63GB | 只有部分分片/首分片 |

合计约 12.89GB。

如果近期不会继续下载，可以删除以释放空间。如果网络流量仍然紧张并且未来可能续传，建议保留，因为删除会导致这些已下载分片重新消耗流量。

必须保留当前攻击所需模型：

```text
LLM/mistralai/mistral-7b-instruct-v0-2/
EmbeddingModel/sentence-transformers/all_minilm_l6_v2/
```

## 6. 大空间清理候选：T2Ranking 非攻击文件

T2Ranking 源目录约 12.07GB，其中：

| 文件 | 大小 | 当前攻击是否使用 |
|---|---:|---|
| `DataSet/T2Ranking/train.mined.tsv` | 约 5.20GB | 不使用 |
| `DataSet/T2Ranking/train.bm25.tsv` | 约 3.40GB | 不使用 |
| `DataSet/T2Ranking/collection.tsv` | 约 3.41GB | 数据描述文件引用，需保留 |

当前攻击只读取标准化后的：

```text
data/processed/documents/member_docs.jsonl
data/processed/documents/nonmember_docs.jsonl
```

`train.mined.tsv` 和 `train.bm25.tsv` 不被当前攻击、数据集注册表或标准化配置引用。早期的 `rag_mia_data.cli inspect` 源数据探查代码能够识别这两个文件，历史 `reports/data_profile.json` 和 `reports/source_dataset_profile.md` 也记录过它们；删除后不能完整重现当时的原始文件清单，但不会影响已经标准化的数据池和四种攻击。如果不计划重新做完整源数据探查、训练排序器或复用 mined/BM25 训练样本，可以删除这两个文件，释放约 8.60GB。

不要删除 `collection.tsv`。`DataSet/T2Ranking/dataset.json` 将它登记为 `processed_corpus`，数据集校验依赖该文件。

## 7. 建议保留的核心内容

```text
environment.yml
pyproject.toml
requirements.txt
configs/attacks/teacher_local_smoke.yaml
configs/datasets/
configs/experiments/
DataSet/registry.json
DataSet/*/dataset.json
DataSet/*/teacher_snapshot/
data/processed/
data/manifests/
data/runs/20260717-ag-news-four-medium/
data/vector_stores/20260717-ag-news-four-medium/
data/attack_results/20260717-ag-news-four-medium/
EmbeddingModel/sentence-transformers/all_minilm_l6_v2/
LLM/mistralai/mistral-7b-instruct-v0-2/
schemas/
scripts/build_vector_db.py
scripts/run_direct_rag_mia.py
scripts/run_s2_mia.py
scripts/run_masked_mia.py
scripts/run_ia.py
scripts/compute_attack_metrics.py
src/
tests/
docs/USAGE_GUIDE_ZH.md
docs/CLEANUP_AUDIT_ZH.md
```

老师数据集的 `teacher_snapshot` 文件仍被数据集描述和校验流程引用。即使已有 `data/processed`，也建议保留它们以保证可复现和可重新标准化。

## 8. 清理执行情况与后续可选项

1. `docs/superpowers/`：已删除。
2. Python、pytest 缓存和 `*.egg-info`：已删除。
3. `models/downloads/` 和历史模型下载日志：已删除。
4. 旧 smoke 结果：属于实验数据，本轮保留。
5. 旧 Ollama 配置与验证脚本：仍可作为备用后端，本轮保留。
6. 约 12.89GB 未完成模型：为避免未来续传重新消耗流量，本轮保留。
7. 约 8.60GB T2Ranking mined/BM25 文件：属于数据集，本轮保留。

本次清理主要减少目录噪声。未完成模型和 T2Ranking 文件只有在用户明确确认后才应删除。
