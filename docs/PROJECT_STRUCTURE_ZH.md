# MIAGuard 工程目录与整理记录

2026-11-20。这里记录工程入口、目录用途和本次整理的恢复依据。数据与模型版本以版本总表及运行清单为准，实验进展以项目状态和实验索引为准。[当前版本总表](CURRENT_VERSIONS_ZH.md) · [项目状态](PROJECT_STATUS_ZH.md) · [实验索引](EXPERIMENT_INDEX_ZH.md)

项目于同日建立本地 Git 仓库并关联 `G-LittleSun/MIAGuard`。提交范围、模型和数据的本地备份范围以及同步方式见 [Git 版本管理与同步](GIT_WORKFLOW_ZH.md)。

## 工程目录

```text
MIAGuard/
├── src/
│   ├── miaguard/          RAG、查询库、Judge、访问控制与评测
│   └── rag_mia_data/      数据导入、标准化、划分和运行样本准备
├── scripts/               命令行入口和实验驱动
│   └── query_bank/        查询库工具
├── configs/               数据、模型、实验和防御配置
├── schemas/               数据、查询、划分和风险事件的 JSON Schema
├── tests/                 自动测试及用于验证行为的小型样例
├── attack_pattern_library/  有独立版本与清单的实验配套资源
├── DataSet/               外部原始数据及数据集说明
├── data/                  查询库、划分、索引、冻结评分和运行产物
├── reports/               汇总、校准结果、专项复算及审核材料
├── LLM/                   本地语言模型权重
├── EmbeddingModel/        本地向量模型权重
├── models/                文件级模型下载清单
├── docs/                  当前文档、设计计划与历史资料
├── output/                对外阅读的导出文件
└── tmp/                   旧测试日志及报告渲染工作文件
```

| 路径 | 本次盘点依据 | 处理方式与移动影响 |
|---|---|---|
| `src/`、`scripts/`、`tests/` | Python 包从 `src` 查找，`miaguard` 入口指向 `miaguard.cli:main`，pytest 从 `tests` 收集。运行清单绑定脚本和核心源码 SHA256 | 保留位置。在下方登记调用关系和入口。移动会影响导入、命令、测试及历史源码核验 |
| `configs/`、`schemas/`、`attack_pattern_library/` | 配置、Schema 和模式库清单由运行脚本、代码加载器、测试以及部分运行身份引用 | 保留位置。配置变更或路径移动可能改变加载结果或校验身份 |
| `DataSet/`、`data/` | 数据注册表、查询库、划分、FAISS 索引与冻结题单通过配置、实验规格和 manifest 绑定；涵盖当前输入及历史产物 | 保留位置。当前开发与历史结果按[数据目录](DATA_CATALOG_ZH.md)追溯 |
| `reports/` | 包含 `defense_v1/T04` 阈值、`T10` 选样清单、复算脚本、审核记录及结果 | 保留位置。部分文件是运行输入，移动可能影响打分、核验和引用 |
| `LLM/`、`EmbeddingModel/`、`models/` | 前两处是本地权重，由实验配置引用。第三处实查包含 `teacher_model_download_manifest.json` | 保留位置。权重路径或下载清单变动会影响加载检查及历史来源追溯 |
| `output/`、`tmp/` | 包含最终 PDF、初版 PDF、渲染图、导出 Python 脚本及有内容的测试日志 | 保留工作产物。已清理其中一份零字节旧测试错误日志 |
| `.codex_tmp/` 既有内容 | 含 `build_agnews_threshold_report.py`、`agnews_threshold_report/` 与 `doc_deps/`，混有报告工作文件和本地依赖 | 保留原件。若要缩减占用，先核对生成流程和依赖后再按项处理 |
| `.pytest_cache`、34 个 `.pytest-tmp-*` 及 `.pytest-tmp` | Cache 标签和节点缓存可识别。可读取的测试目录内是 pytest 测试子目录和测试构造的 JSON、JSONL 与 YAML。较早的目录也核对了 `bank-1/run-1` 测试数据 | `.pytest_cache` 与 33 个已核实目录先归档，后清理。历史计划把相关路径用作 pytest 的临时输出目录。其余两处见待确认项 |

## 从代码到原始结果

1. **入口与编排**。包入口和参数定义在 [cli.py](../src/miaguard/cli.py)。当前防御开发配对从 [run_defense_v1_benchmark.py](../scripts/run_defense_v1_benchmark.py) 进入 [defense_benchmark.py](../src/miaguard/defense_benchmark.py)，按实验规格编排方法、会话、输出及断点续跑。真实后端和类型策略在 [defense_benchmark_live.py](../src/miaguard/defense_benchmark_live.py)，测试后端在 [defense_benchmark_fake.py](../src/miaguard/defense_benchmark_fake.py)。
2. **查询识别、访问控制与生成**。[defense.py](../src/miaguard/defense.py) 的 `GuardedRAG.prepare` 先做查询判断，再经 [vector_store.py](../src/miaguard/vector_store.py) 执行检索。[two_stage_gateway.py](../src/miaguard/two_stage_gateway.py) 调用 [progressive_judge.py](../src/miaguard/progressive_judge.py) 获取风险证据，在条件满足时结合会话，使用 [frozen_risk_scorer.py](../src/miaguard/frozen_risk_scorer.py) 定分并选择工作点。真实后端根据方法和风险决定动作，[evidence_access.py](../src/miaguard/evidence_access.py) 决定实际交付的材料，生成由 [model_client.py](../src/miaguard/model_client.py) 承接，暴露记录由 [exposure_store.py](../src/miaguard/exposure_store.py) 保存。
3. **输入和版本**。防御开发使用 `ag_news_queries_v2` 和 `ag_news_threshold_v2` 的 train。既有 Judge v3 独立识别对照和 E00 使用 v1。Python 包版本为 0.1.0，防御规格与实验协议版本为 v1.1。具体身份从选样清单和实验规格读取，四类配对规格中的绝对路径和 SHA256 用于追溯原配置、评分头、阈值和对照索引。[复用选择清单](../reports/defense_v1/T10/legacy_reuse_selection_20261104.json) · [单轮规格](../data/defense_datasets/four_type40_single_v2_train_20261118_01/experiment_spec.json) · [IA 规格](../data/defense_datasets/four_type40_ia_v2_train_20261118_01/experiment_spec.json)
4. **结果和复算**。先从实验汇总找指标和案例，再读对应 `run_manifest.json`、逐请求事件及评分。T10 专项脚本依赖相关归档和工作目录，按实验名定位。历史识别、阶段二和规则防御入口见实验索引。[汇报主表](EXPERIMENT_RESULTS_ZH.md) · [单轮运行](../data/defense_v1_runs/four-type40-single-paired-20261118-01/run_manifest.json) · [IA 运行](../data/defense_v1_runs/four-type40-ia-paired-20261118-01/run_manifest.json) · [复算脚本](../reports/defense_v1/T10/publish_four_type40_results_20261118.py)

四类配对的模型与检索参数、Judge 和网关配置从对应规格中的 `identity_files` 定位。B0/V2 的策略选择由真实后端按实验方法决定。[模型与检索配置](../configs/attacks/ag_news_progressive_judge_qwen2_5_7b_bf16.yaml) · [Judge 配置](../configs/defense/progressive_judge_v3_binary_logprob_qwen2_5_7b.yaml) · [网关配置](../configs/defense/defense_v1_observe.yaml) · [冻结评分](../data/judge_score_frozen_v3_binary_logprob_20260920/logistic_l2.json) · [Query-only 阈值](../reports/defense_v1/T04/query_only_thresholds.json)

数据准备从 `rag_mia_data` 的命令入口开始，查询库的构建、校验和检查从 `scripts/query_bank/` 开始。历史命令对应的配置和输入按所属实验查询。[数据准备入口](../src/rag_mia_data/cli.py) · [查询库工具](../scripts/query_bank/README.md)

## 常用命令

从项目根目录执行。已配置的 Conda 环境使用 Python 3.10，项目依赖与可选的测试、模型和分析依赖记录在 [pyproject.toml](../pyproject.toml) 和 [environment.yml](../environment.yml)。

```powershell
Set-Location D:\Project\MIAGuard
conda activate MIAGuard
python -m miaguard.cli --help
python scripts/run_defense_v1_benchmark.py --help
python -m pytest -q -p no:cacheprovider
python -X utf8 reports/defense_v1/T10/publish_four_type40_results_20261118.py --include-ia
```

最后一条从现存两批运行清单、事件及评分复算并在终端打印四类对照表。实验环境、数据和模型准备见使用手册。当前实验按规格绑定模型和索引，`teacher_local_smoke.yaml` 对应旧环境示例，其 `doctor` 命令会实际调用生成模型和向量模型。[使用手册](USAGE_GUIDE_ZH.md) · [查询库入口](../scripts/query_bank/README.md) · [防御实验协议](DEFENSE_EXPERIMENT_PROTOCOL_ZH.md)

## 2026-11-20 整理清单和恢复方式

- 开始盘点时，`git rev-parse --show-toplevel` 返回该路径不在 Git 工作树中。磁盘上的已有内容作为基线，待改的四份导航文档已逐份备份。原始散列、逐目录的旧路径和计划新路径、文件数与文件级 SHA256 均已登记。[盘点与计划清单](../.codex_tmp/project-organization-20261120/inventory.json) · [整理前文档](../.codex_tmp/project-organization-20261120/docs-before/)
- 执行 `Move-Item -LiteralPath`，将 34 个确认的测试产物目录移入项目内的 `.codex_tmp/project-organization-20261120/pytest-archive/`，共 1,165 个文件、29,983,979 字节。归档保留每个目录的原名称。在扫描的代码、配置、测试、文档和产物中，两份历史计划记录了以 `.pytest-tmp` 系列路径为输出的旧测试命令，复现时可指定新的临时路径。[实际移动清单](../.codex_tmp/project-organization-20261120/moves.jsonl)
- 后续按用户指示清理已确认可再生成的文件。复核归档内 1,165 个文件的 SHA256 和验证目录内 183 个测试样例后，使用 PowerShell 调用 Windows 回收站接口处理 `pytest-archive/`、`verification-pytest/` 及零字节的 `tmp/full_test_20260903_1725.stderr.log`，共 1,349 个文件、30,667,316 字节。核对三个原路径均已移出，回收站内确认有验证目录和空日志，未找到 `pytest-archive/` 的可恢复记录。
- 根目录的 `.pytest-tmp`、`.pytest-tmp-full` 仍返回 Windows 拒绝读取，容量、内容及用途待确认。
- 需要这些临时样例时，可按整理记录重新运行对应测试。原移动清单、散列和 `docs-before/` 文档备份仍可查阅。
- 盘点采用 `Get-ChildItem -Force`、`rg --hidden -l -F '.pytest-tmp'` 和 `python -B -X utf8 -` 对目录、配置引用及哈希做只读核对。整理前，两个命令行入口的 `--help` 可加载，原有四类配对的两批运行核验器各确认 240 次有效请求及 240 个生成证据归档。
- 整理后用 `python -B -X utf8 -` 逐文件核对 34 条移动记录、1,165 个归档文件、282 个源码与配置等基线文件、4 份文档备份和新增本地链接。两批实验再次各核验 240 次请求和归档证据。两个 `--help` 命令通过，`publish_four_type40_results_20261118.py --include-ia` 输出与已发布的对照表一致。
- 在 Conda `MIAGuard` 中执行 `python -B -m pytest -q -p no:cacheprovider --basetemp D:/Project/MIAGuard/.codex_tmp/project-organization-20261120/verification-pytest tests/test_cli.py tests/test_two_stage_gateway.py tests/test_defense_v1_observe.py tests/test_frozen_risk_scorer.py tests/test_defense_action_executor.py tests/test_defense_benchmark.py tests/test_query_bank_repair.py`，**85 项通过**，3 条来自底层 SWIG 类型的弃用警告。全量测试和大模型推理未执行。
