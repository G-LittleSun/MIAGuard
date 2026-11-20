# MIAGuard

MIAGuard 用于本地 RAG 成员推理风险与访问控制研究。[工程目录与整理记录](docs/PROJECT_STRUCTURE_ZH.md)提供目录树、代码调用关系、运行入口和整理前后的路径。

项目代码和文档通过 GitHub 记录版本，日常提交、同步与回滚见 [Git 版本管理与同步](docs/GIT_WORKFLOW_ZH.md)。本地模型、原始数据和索引的管理范围见根目录 `.gitignore`。

- 新成员先看[当前开发状态](docs/PROJECT_STATUS_ZH.md)、[数据目录](docs/DATA_CATALOG_ZH.md)和[实验索引](docs/EXPERIMENT_INDEX_ZH.md)。开发任务、规格与下一步见[防御进度台账](docs/DEFENSE_PROGRESS_ZH.md)。
- 选择查询库、模型和配置前核对[统一版本总表](docs/CURRENT_VERSIONS_ZH.md)。防御开发采用 v2 查询库与划分的 train，既有 Judge v3 识别对照和 E00 使用 v1。防御规格版本为 v1.1，Python 包版本为 0.1.0。
- 四类 B0/V2 开发对照的指标、案例和原始清单集中在[实验结果汇总](docs/EXPERIMENT_RESULTS_ZH.md)。按主题查阅已有资料时使用[文档索引](docs/README.md)。

## 研究范围

- Masked MIA
- IA
- Direct RAG-MIA
- S²-MIA（当前为 all-MiniLM 余弦相似度版本）
- Rule-only 最小防御闭环与 allow/restrict/deny 三档访问控制

项目环境为 Conda `MIAGuard`。历史模型检查示例 `configs/attacks/teacher_local_smoke.yaml` 使用本地 Mistral、all-MiniLM 和 FAISS。当前防御配对的模型、索引、阈值和配置由对应实验规格指定。[工程入口与运行说明](docs/PROJECT_STRUCTURE_ZH.md)

离线预生成攻击与正常查询、断点续建 Query Bank，以及在实验中禁止在线查询生成的用法，
见 `docs/QUERY_BANK_ZH.md`。

详细操作请阅读：

- [完整中文使用手册](docs/USAGE_GUIDE_ZH.md)
- [防御框架递进路线与阶段一验收标准](docs/DEFENSE_ROADMAP_ZH.md)
- [Rule-only 防御方法详细说明](docs/RULE_BASED_DEFENSE_ZH.md)
- [阶段二 IA 访问动作评测](docs/STAGE2_IA_POLICY_EVALUATION_ZH.md)
- [大样本与困难查询实验](docs/LARGE_AND_HARD_QUERY_EVALUATION_ZH.md)
- [文件清理审计](docs/CLEANUP_AUDIT_ZH.md)
- [攻击迁移说明](docs/attack_migration.md)
- [Direct RAG-MIA 与 S²-MIA 说明](docs/baseline_rag_mia_attacks.md)
- [数据字段字典](docs/data_dictionary.md)

## 检查命令入口

```powershell
Set-Location D:\Project\MIAGuard
conda activate MIAGuard
python -m miaguard.cli --help
python scripts/run_defense_v1_benchmark.py --help
python -m pytest -q -p no:cacheprovider
```

## 历史结果入口

已验证的四攻击扩容运行

```text
run_id: 20260717-ag-news-four-medium
results: data/attack_results/20260717-ag-news-four-medium/ag_news/
```

已验证的阶段一防御 MVP

```text
run_id: 20260720-ag-news-defense-mvp-calibrated
results: data/defense_results/20260720-ag-news-defense-mvp-calibrated/ag_news/
threshold report: reports/ag_news_attack_threshold_calibration.json
```

已验证的阶段二留出评测

```text
run_id: 20260720-ag-news-defense-stage2-holdout
results: data/defense_results/20260720-ag-news-defense-stage2-holdout/ag_news/
IA policy validation: data/defense_policy_results/20260720-ag-news-ia-policy-validation/ag_news/
```

历史大样本与困难查询结果

```text
large defense: data/defense_results/20260720-ag-news-defense-large/ag_news/
hard queries: data/hard_query_results/20260720-ag-news-hard-queries/ag_news/
```
