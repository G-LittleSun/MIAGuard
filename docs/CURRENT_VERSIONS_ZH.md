# MIAGuard 当前版本总表

2026-11-18：四类对照延续 v2 train、原 AG News 索引与冻结的 B_TYPE_V2。使用[单轮题单](../data/defense_datasets/four_type40_single_v2_train_20261118_01/manifest.json)、[IA 三轮题单](../data/defense_datasets/four_type40_ia_v2_train_20261118_01/manifest.json)及[预登记评分口径](../reports/defense_v1/T10/FOUR_TYPE40_SCORING_ZH.md)，两批共完成 480 次请求，结果于[实验结果汇总](EXPERIMENT_RESULTS_ZH.md)合表。IA 的参考组合和前缀标记在题单的离线审计文件中。

2026-11-17：48题效用配对以[复用新版](../data/defense_datasets/utility48_reuse_v2_train_20261117_01/manifest.json)及[已完成运行](../data/defense_v1_runs/utility48-reuse-paired-20261117-01/run_manifest.json)为当前开发结果，旧版保留历史。

2026-11-17：[48题复用新版](../data/defense_datasets/utility48_reuse_v2_train_20261117_01/manifest.json)已冻结，B0/V2主配对运行中；前版结果保留历史。

2026-11-17：48题效用开发题单使用[utility48_v2_train_20261117_01](../data/defense_datasets/utility48_v2_train_20261117_01/manifest.json)；真实运行进行中，身份以run manifest为准，非人工gold或正式测试。

2026-11-17：[真实机制消融题单](../data/defense_datasets/next_goal_ablation_v2_train_20261117_01/manifest.json)固定8题。仅线索、仅IA方法已实现并通过相关回归，[消融运行32/32完成](../data/defense_v1_runs/next-goal-ablation-20261117-01/run_manifest.json)。主配对生产源码快照及对应SHA见[台账L264](DEFENSE_PROGRESS_ZH.md#l264--2026-11-17--t10-d--ablation_implemented)。

2026-11-17：新增[IA格式正常对照题单](../data/defense_datasets/next_goal_ia_style_normal_20261117_01/manifest.json)，4题/4方法[运行16/16完成](../data/defense_v1_runs/next-goal-ia-style-20261117-01/run_manifest.json)；模型及原索引复用主配对身份。

2026-11-17：下一轮开发题单为[next_goal_v2_train_20261117_01](../data/defense_datasets/next_goal_v2_train_20261117_01/manifest.json)，绑定v2 train、冻结Judge和原索引。`B_NEXT_GOAL` 已接入并通过相关回归，主[运行manifest](../data/defense_v1_runs/next-goal-paired-20261117-01/run_manifest.json)记录实际代码身份。因正常阅读退化，候选未被选作替换V2。

2026-11-17：候选对照增加[来源扩展题单](../data/defense_datasets/multi_action_sources_v2_train_20261117_01/manifest.json)，[运行](../data/defense_v1_runs/multi-action-sources-20261117-01/run_manifest.json)95/95完成；5条Masked原文核验见[预检](../reports/defense_v1/T10/multi_action_sources_preflight_20261117.json)。该结果未选出全面优胜候选，V2保持开发对照，候选身份保留。

2026-11-17：多动作候选采用[开发题单](../data/defense_datasets/multi_action_v2_train_20261117_01/manifest.json)，运行身份见[manifest](../data/defense_v1_runs/multi-action-candidates-20261117-01/run_manifest.json)。新增 B_MULTI_SUMMARY/B_MULTI_NO_CONTEXT 分支，基线冻结模型与原索引身份不变。运行源码以manifest中摘要为准。

2026-11-17：两小时配对实验使用[冻结题单](../data/defense_datasets/two_hour_paired_v2_train_20261117_01/manifest.json)，[运行](../data/defense_v1_runs/two-hour-paired-20261117-01/run_manifest.json)已完成123/123，Judge v3及原索引、v2 train身份以清单和摘要为准。[结果](../reports/defense_v1/T10/TWO_HOUR_PAIRED_REPORT_20261117_ZH.md)

2026-11-16：续跑新增[重置会话运行](../data/defense_v1_runs/multiturn-ia-reset-20261116-01/run_manifest.json)与[问法对照运行](../data/defense_v1_runs/benign-style-pair-20261116-01/run_manifest.json)，均completed，输入身份以各运行清单为准。连续主运行54/54已完成。汇总见[报告](../reports/defense_v1/T10/SUPPLEMENT_RESULTS_20261116_ZH.md)。

2026-11-13 40分钟补充登记：最新开发题单为[multiturn_ia_session](../data/defense_datasets/multiturn_ia_session_v2_train_20261113_01/manifest.json)、[multiturn_ia_reset](../data/defense_datasets/multiturn_ia_reset_v2_train_20261113_01/manifest.json)及[benign_style_pair](../data/defense_datasets/benign_style_pair_v2_train_20261113_01/manifest.json)，均绑定v2 train和原索引。16个生产源码摘要与上一轮一致，见[预检](../reports/defense_v1/T10/multiturn_ia_preflight_20261113.json)。不改变B_TYPE_V2、Judge、冻结阈值或正式文档版本；运行完成状态另见进度台账。历史内容含义的[追加勘误](../reports/defense_v1/T10/multiturn_ia_metadata_erratum_20261113.json)绑定未改变的题单摘要。

2026-11-13 开发登记：[困难正常题单](../data/defense_datasets/benign_pair_v2_train_20261113_01/manifest.json)、[42 次实跑身份](../data/defense_v1_runs/benign-triggered-pair-20261113-01/run_manifest.json)。复用上一轮代码指纹、B_TYPE_V2、冻结 Judge、阈值和原索引。v2 train 题单身份由新 manifest 单独登记。

2026-11-13 开发登记：[类型驱动题单](../data/defense_datasets/type_policy_v2_train_20261113_01/manifest.json)采用 v2 train，复用冻结 Judge 和原索引。B_TYPE_V1 与 B_TYPE_V2 的当前开发身份以[首轮](../data/defense_v1_runs/type-policy-v1-20261113-01/run_manifest.json)和[配对复跑](../data/defense_v1_runs/type-policy-v2-paired-20261113-01/run_manifest.json)各自实际代码与输入摘要为准。

核对日期：2026-11-09（北京时间）。登记修订号：`2026-11-09-r06`。

**本页是按用途选择版本的统一入口。** 开始任务时，在按项目入口读取状态、数据目录和实验索引后，先核对本页再选择实际文件；数据/结果身份仍以原始 manifest 和文件摘要为准。不要把“最新查询库”“已有实验使用的数据”“开发规格版本”和“代码版本”理解为同一个版本号。

本次核对的路径、完整 SHA256、原始 manifest 摘要及代码文件指纹见[版本快照 JSON](../reports/defense_v1/planning/current_versions_snapshot_20261109_06.json)。本页持续维护，日期快照保留历史；它是身份记录，不是运行器已经执行或自动读取的配置。

## 1. 当前任务直接用什么

当前开发任务为 **T10-D**。四类各 40 目标开发配对已完成 480/480，正常效用及困难正常题结果见实验索引。后续按进度台账核对具体开发缺口、独立来源、人工 gold 和攻击校准。[当前结果](EXPERIMENT_RESULTS_ZH.md) · [进度台账](DEFENSE_PROGRESS_ZH.md)

| 用途 | 当前指定版本 | 文件与核对依据 | 使用状态 |
|---|---|---|---|
| 最新完整查询库 | `ag_news_queries_v2` | [queries.jsonl](../data/query_banks/ag_news_queries_v2/ag_news/queries.jsonl)、[manifest.json](../data/query_banks/ag_news_queries_v2/ag_news/manifest.json) | 100 篇、7,632 查询，正常 2,176、攻击 5,456；最新可用库，正常审核仍 pending。 |
| 后续防御开发的查询/划分 | **v2 bank + `ag_news_threshold_v2`，只取 train** | [split](../data/query_bank_splits/ag_news_threshold_v2.json)、[复用选择清单](../reports/defense_v1/T10/legacy_reuse_selection_20261104.json) | 60 篇、4,579 查询；[逐条自动结构审计](../reports/defense_v1/T10/v2_train_reuse_audit_20261105_01/REUSE_REPORT_ZH.md)完成；语义/gold/运行适配仍待完成，不是正式放行。 |
| 上述查询绑定的原文及索引 | `source_run_id=20260717-ag-news-four-medium` | [上游目标原文](../data/runs/20260717-ag-news-four-medium/ag_news/target_docs.jsonl)、[原索引 manifest](../data/vector_stores/20260717-ag-news-four-medium/ag_news/manifest.json) | 原索引 1,000 篇；不可把该成员身份直接用于 candidate06 新索引。 |
| 防御新保留数据的父候选 | `defense_access_v1_candidate06` | [候选 manifest](../data/defense_datasets/defense_access_v1_candidate06/manifest.json)、[分区索引根目录](../data/vector_stores/defense_access_v1_candidate06/) | 3,600 目标、900 共享背景；模板草稿，`formal_effect_eligible=false`，不是最新查询库 v2 的替代品或正式终测。 |
| 选定正常会话开发队列 | `session_length_dev_cohort_20261102_01` | [队列清单](../reports/defense_v1/T10/session_length_dev_cohort_20261102_01/manifest.json)、[结构化导出](../reports/defense_v1/T10/dev_cohort_export_20261104_01/manifest.json) | 30 会话、62 问；pending，两个三轮诊断同源，不是人类 gold。 |
| 历史单 mask 规则调试材料 | `masked_selected_pilot_20261104_01` | [清单](../reports/defense_v1/T10/masked_selected_pilot_20261104_01/manifest.json)、[内容核查](../reports/defense_v1/T10/masked_selected_pilot_20261104_01/AGENT_REVIEW_ZH.md) | 四篇候选词清单、两条新草稿，另两篇未选词；仅调试，不作为正式攻击效果数据。 |
| 本轮外部模型预审及接收 | `v2_reuse_deepseek-v4.1-flash_20261105_01` | [外部 manifest](../reports/defense_v1/T10/external_review/v2_reuse_deepseek-v4.1-flash_20261105_01/review_manifest.json)、[接收处理](../reports/defense_v1/T10/v2_reuse_review_integration_20261105_01/INTEGRATION_REPORT_ZH.md) | 206 IA +60 Masked方案已审并通过结构核验，局部Codex修订/暂缓；不是真人gold。 |
| 当前针对性待审攻击叠加层 | `legacy_v2_reuse_overlay_20261105_01` | [候选 manifest](../data/defense_datasets/legacy_v2_reuse_overlay_20261105_01/manifest.json)、[核验](../data/defense_datasets/legacy_v2_reuse_overlay_20261105_01/validation.json) | 362新请求（62 IA +300 Masked），144 IA暂缓；全局pending、不可正式回放，不替换原v2库或代表完整数据验收。 |
| 当前快速工程试跑材料 | `legacy_v2_fast_pilot_20261105_01` | [固定manifest](../data/defense_datasets/legacy_v2_fast_pilot_20261105_01/manifest.json)、[spec](../data/defense_datasets/legacy_v2_fast_pilot_20261105_01/experiment_spec.json) | v2 train的12独立单轮（4正常/8攻击）；仅此小批工程资格，无真人gold、不代表全量放行。 |
| 正式防御 gold、最终新 T | **尚未验收/冻结** | [进度台账](DEFENSE_PROGRESS_ZH.md)、[实验协议](DEFENSE_EXPERIMENT_PROTOCOL_ZH.md) | T10-E、T16 等门禁未完成；没有可直接引用的新正式防御版本号。 |

v2 继承 v1 的文档表、文档分区和全部攻击记录，主要扩充正常查询。**版本更新不等于新独立测试集**；[版本核验](../reports/defense_v1/T10/query_bank_version_audit_20261104.json)已记录这一点。v1 train 的 3,575 与 v2 train 的 4,579 是不同库的数量，不可混用。

## 2. 已有实验结果属于哪个版本

| 实验或产物 | 当前应引用的版本/身份 | 原始结果入口 | 结论范围 |
|---|---|---|---|
| 当前已完成攻击识别对照 | **Progressive Judge v3**，二分类 logprob / rubric；数据 **`ag_news_queries_v1` + `ag_news_threshold_v1`** | [统一 test 对比](../data/judge_score_comparison_v3_20261015/final_test_comparison.json)、[实验索引](EXPERIMENT_INDEX_ZH.md) | 已完成的识别结果；不能把数据名改成 v2，也不是访问控制后的泄露下降。 |
| v3 正式 train 评分 | `20260916_retry1` | [run_manifest](../data/progressive_judge_v3_binary_logprob_train_qwen2_5_7b_bf16_20260916_retry1/train/run_manifest.json)、[summary](../data/progressive_judge_v3_binary_logprob_train_qwen2_5_7b_bf16_20260916_retry1/train/benchmark_summary.json) | 3,575 查询、734 会话；不使用同日期未带 retry1 的失败目录。 |
| v3 validation / test 评分 | validation `20260918`，test `20260920` | [validation manifest](../data/progressive_judge_v3_binary_logprob_validation_qwen2_5_7b_bf16_20260918/validation/run_manifest.json)、[test manifest](../data/progressive_judge_v3_binary_logprob_test_qwen2_5_7b_bf16_20260920/test/run_manifest.json) | 仍绑定 v1。终测对照中 Query/Session 同时可用的记录为 699 条、20 文档。 |
| 真实 observe 工程核对 | `e00-observe-20261022-01`，v1 train | [run_manifest](../data/defense_v1_runs/e00-observe-20261022-01/run_manifest.json) | 2 会话、10 请求；观察风险和检索，未生成防御回答。 |
| 访问动作/回放工程核对 | `t09-fake-20261022-05` | [run_manifest](../data/defense_v1_runs/t09-fake-20261022-05/run_manifest.json)、[metrics](../data/defense_v1_runs/t09-fake-20261022-05/metrics.json) | synthetic fake，20/20；非真实成员推断/回答质量效果。 |
| 本地会话文本理解诊断 | `t10c-history-ablation-20261102-01`、`t10c-context-focus-20261102-01` | [历史对照 manifest](../data/defense_v1_runs/t10c-history-ablation-20261102-01/run_manifest.json)、[焦点对照 manifest](../data/defense_v1_runs/t10c-context-focus-20261102-01/run_manifest.json) | Q4 小样本诊断，不是冻结 BF16 Judge、真实 RAG 或防御效果。 |
| 最新真实工程回答对照 | `fast-v2-b0-b2-20261105-01`，v2 train | [manifest](../data/defense_v1_runs/fast-v2-b0-b2-20261105-01/run_manifest.json)、[报告](../reports/defense_v1/T10/fast_live_pilot_20261105_01/FAST_PILOT_REPORT_ZH.md) | 原BF16、24/24 complete/valid；正常4对一致，B2攻击拒答6/8；仅案例观察，Masked严格分数存在格式混淆，非正式E01。 |
| 新增过滤/摘要真实工程对照 | `fast-v2-b5-b6-20261105-01`，同一v2 train小批 | [manifest](../data/defense_v1_runs/fast-v2-b5-b6-20261105-01/run_manifest.json)、[报告](../reports/defense_v1/T10/fast_live_pilot_20261105_01/COMPARISON_B5_B6_ZH.md) | B5/B6各12次完成，engineering_only；运行身份以manifest为准，r04快照为运行前基线。 |
| 排名压力测试 | `rank-stress-v2-b0-b5-b6-20261109-01`，v2 train 六题 | [输入](../data/defense_datasets/legacy_v2_rank_stress_20261109_01/manifest.json)、[运行](../data/defense_v1_runs/rank-stress-v2-b0-b5-b6-20261109-01/run_manifest.json)、[报告](../reports/defense_v1/T10/rank_stress_20261109_01/REPORT_ZH.md) | B0/B5/B6，18/18完成，工程诊断。运行时引用历史r05。 |
| 新版真实防御主实验 | **E01–E07 尚未运行** | [实验协议](DEFENSE_EXPERIMENT_PROTOCOL_ZH.md)、[进度台账](DEFENSE_PROGRESS_ZH.md) | 不存在可替换上述识别结果的正式防御效果版本。 |

`progressive_judge_v2_three_class...20260929` 虽然目录日期晚于部分 v3 结果，但属于历史三分类中断重跑，不是应取代 v3 的最新有效对照。判断有效版本要看任务用途、manifest、summary 和验收，不能只按修改时间、日期或编号排序。

## 3. 模型、评分头与开发框架分别是什么版本

| 层级 | 当前身份 | 文件与限制 |
|---|---|---|
| 当前已有识别实验的 Judge 模型 | `LLM/Qwen2.5-7B-Instruct`，transformers BF16 | 以 v3 run manifest 的 `model_configuration` 为准；不等于 Ollama `qwen2.5:latest` Q4。 |
| 优先接入的融合评分头 | v3 binary logprob，`logistic_l2`，冻结于 `20260920` | [冻结 JSON](../data/judge_score_frozen_v3_binary_logprob_20260920/logistic_l2.json)，SHA256 `b24b81b88a4ce9579e81eb51cb4e0cc940972dc22499fce77ef80c60f587d188`；仍由 v1 训练。 |
| 稳健性对照评分头 | v3 rubric，`logistic_l2`，`20261015` | [冻结 JSON](../data/judge_score_frozen_v3_rubric_20261015/logistic_l2.json)；不与 logprob 系数/阈值互换。 |
| 前两轮 Query-only 工作点 | T04 旧 v1 train 经验阈值 | [阈值 JSON](../reports/defense_v1/T04/query_only_thresholds.json)，经验工作点未因 v2 入口切换自动重校准。 |
| Judge prompt | `progressive_v3_binary_logprob_strict_validated_attack_evidence` | [配置](../configs/defense/progressive_judge_v3_binary_logprob_qwen2_5_7b.yaml)及原 run manifest；旧运行以当时身份为准。 |
| 攻击模式库 | `1.7.0` | [manifest.yaml](../attack_pattern_library/manifest.yaml)；各攻击自身版本也在 manifest 中，不等于查询库 v2。 |
| 网关工程接入 | `defense_v1_observe_frozen_logprob` | [observe 配置](../configs/defense/defense_v1_observe.yaml)；T06–T09动作工程已有验证，首轮真实B0/B2小批已完成；正式效用/泄露尚未评估。 |
| 防御开发规格 / 主计划 / 实验协议 | **v1.1**，2026-10-31 基线，含 11 月 2 日和 4 日补记 | [规格](superpowers/specs/2026-10-22-defense-framework-design.md)、[主计划](superpowers/plans/2026-10-22-defense-framework-implementation.md)、[协议](DEFENSE_EXPERIMENT_PROTOCOL_ZH.md)；是文档版本，不是代码发布号。 |
| Python 包声明 | **miaguard 0.1.0** | [pyproject.toml](../pyproject.toml)、[包内声明](../src/miaguard/__init__.py)一致；不能凭这个号判断当前源码是否等于某次历史运行。 |
| 当前工作区源码 | 无 Git commit；按[本次快照](../reports/defense_v1/planning/current_versions_snapshot_20261109_06.json)的文件列表及 `code_snapshot.sha256` 标识 | 快照覆盖 `src/**/*.py`、`scripts/**/*.py`、configs 下 JSON/YAML 及 pyproject。指纹只能识别内容是否变化，不能恢复旧代码，也不包含依赖环境或模型权重。实际运行另存 commit/源码快照和环境身份。 |

## 4. 后续如何更新和核对

1. **选择时说清用途。** 开发复用用 v2 train；复现已完成 Judge v3 用其原 v1；新的最终效果遵循新保留集门禁。库名、split 名、索引和模型组合须同时记录。
2. **核对实际输入。** 读取所选 bank manifest 和 split 的 bank/摘要，比较 queries 文件 SHA256；再核对索引、模型和运行配置。若脚本仍默认 v1，显式配置 v2 bank + v2 split；不能仅改文档名称或误改历史复现配置。
3. **本页不是自动拦截器。** 现有运行器未自动加载本表；本次已完成 v2 逐条自动结构覆盖，全量语义/gold未完成；固定12题已显式绑定v2完成真实工程运行。因此不得根据本表存在就声称全量已验收。以后实际执行需在 run manifest 保存本表修订号、所用选择清单和全部实际输入摘要。
4. **切换版本同步登记。** 新版本先核对 manifest、用途、质量/完成状态和与旧版的关系，再更新本页、数据目录/实验索引及选择清单，在台账追加 CHANGE 和下一步；新增有日期的版本快照保留旧身份。不静默覆盖冻结数据、评分模型或旧结果。
5. **区分完成程度。** `complete` 的生成库、`accepted` 查询、模型预审、代码测试与正式效果实验是不同状态；pending 数据不自动升级为人类 gold。文档改动也不代表功能/实验完成。

维护者为后续执行开发或实验的 agent/人员。只更新实际核对到的内容；找不到 manifest、摘要不一致或发生角色冲突时，先记录问题并核查来源，不能凭“最新”二字猜版本。

## 5. 维护记录

| 日期 / 修订号 | 变化 | 证据与任务状态 |
|---|---|---|
| 2026-11-05 / r01 | 建立统一版本角色入口，集中登记数据、实验、模型/配置、文档及源码身份 | [本次快照](../reports/defense_v1/planning/current_versions_snapshot_20261105_01.json)与[台账](DEFENSE_PROGRESS_ZH.md) L103 起；T10-D 继续进行，本次未启动防御实验。 |
| 2026-11-05 / r02 | 更新 v2 train 全量自动结构覆盖的证据与接续任务，数据/模型选择不变 | [审计报告](../reports/defense_v1/T10/v2_train_reuse_audit_20261105_01/REUSE_REPORT_ZH.md)、[版本快照](../reports/defense_v1/planning/current_versions_snapshot_20261105_02.json)；语义/gold/真实运行仍未完成。 |
| 2026-11-05 / r03 | 接收266单元预审，新增362条待审攻击叠加层及144暂缓记录；选择仍为v2 train | [接收报告](../reports/defense_v1/T10/v2_reuse_review_integration_20261105_01/INTEGRATION_REPORT_ZH.md)、[身份快照](../reports/defense_v1/planning/current_versions_snapshot_20261105_03.json)；未完成真人gold或运行适配。 |
| 2026-11-05 / r04 | 登记固定12题v2 train及24/24真实B0/B2，按用户加速要求先做评分诊断与同批动作比较 | [真实报告](../reports/defense_v1/T10/fast_live_pilot_20261105_01/FAST_PILOT_REPORT_ZH.md)、[身份快照](../reports/defense_v1/planning/current_versions_snapshot_20261105_04.json)；原库/阈值/业务代码未变，非正式gold/效果验收。 |

本次核验见[版本总表验证报告](../reports/defense_v1/planning/current_versions_registry_validation_20261109_r06.json)：角色、原始文件/源码指纹和导航链接通过；不构成数据 gold、自动运行门禁或防御效果验收。

2026-11-05 / r05：新增[B5/B6真实小批对照](../reports/defense_v1/T10/fast_live_pilot_20261105_01/COMPARISON_B5_B6_ZH.md)及独立Masked诊断；新运行引用历史r04快照，当前身份见r05。

2026-11-09 / r06 登记排名压力测试、旧B5/B6逐条复核与当前工作入口。

2026-11-11：新增工程小批 `forced_normal_diagnostic_20261111_01` 与运行 `forced-normal-b0-b5f-20261111-01`，沿用登记快照r06的模型和v2 train原索引；仅4条正常题强制动作诊断，[数据身份](../data/defense_datasets/forced_normal_diagnostic_20261111_01/manifest.json)、[运行身份](../data/defense_v1_runs/forced-normal-b0-b5f-20261111-01/run_manifest.json)、[报告](../reports/defense_v1/T10/forced_normal_diagnostic_20261111_01/REPORT_ZH.md)。不取代原v2查询库或构成正式E01。

2026-11-11：新增工程运行 `rank-stress-v2-b2-b3-20261111-01`，复用 `legacy_v2_rank_stress_20261109_01` 的6题及快照r06，方法B2/B3；[运行身份](../data/defense_v1_runs/rank-stress-v2-b2-b3-20261111-01/run_manifest.json)、[结果说明](../reports/defense_v1/T10/rank_stress_20261109_01/CONSERVATIVE_B2_B3_20261111_ZH.md)。不改变正式版本或E01状态。

2026-11-11 文档补记：T10-D 定位、回退、摘要和评估顺序见[主计划](superpowers/plans/2026-10-22-defense-framework-implementation.md)；本次未切换数据、模型或源码版本，r06仍为已有身份快照，后续新运行须另行登记实际身份。

2026-11-11：新增候选源码 `src/miaguard/evidence_locator.py`，版本 `contiguous_trigrams_v1`，接入实验方法 `B5_LOCATED`。真实运行 `rank-stress-v2-locator-20261111-01` 的[运行清单](../data/defense_v1_runs/rank-stress-v2-locator-20261111-01/run_manifest.json)包含实际源码摘要；源码已不同于r06，不以r06单独证明当前源码身份。输入依然引用原v2 train与原索引，正式gold和E01未完成。

2026-11-11：新增工程数据 `locator_new_sources_20261111_01` 与运行 `locator-new-sources-20261111-01`；实际源码和输入摘要见[manifest](../data/defense_v1_runs/locator-new-sources-20261111-01/run_manifest.json)，[结果说明](../reports/defense_v1/T10/LOCATOR_NEW_SOURCES_20261111_ZH.md)。仅开发诊断，未替换v2 bank或正式数据。

2026-11-11：新增实验规则 `query_cue_v1` 与实验方法 `B5_CUE`，不替代Judge或旧B5；数据 `query_cue_pilot_20261111_01`，运行 `query-cue-pilot-20261111-01`，实际代码与输入摘要见[运行manifest](../data/defense_v1_runs/query-cue-pilot-20261111-01/run_manifest.json)。已见开发样本，非正式E01。

2026-11-11：新增工程诊断数据 `cue_utility_nonmember_20261111_01` 与运行 `cue-utility-nonmember-20261111-01`，身份以[运行manifest](../data/defense_v1_runs/cue-utility-nonmember-20261111-01/run_manifest.json)和[数据manifest](../data/defense_datasets/cue_utility_nonmember_20261111_01/manifest.json)为准；4正常/4非成员，非正式E01。

2026-11-11 用户确认类型驱动策略方向；现有Judge、数据、阈值和已完成运行身份未切换。类型选择策略尚待设计实现，按[主计划T10-D及T14](superpowers/plans/2026-10-22-defense-framework-implementation.md)记录新版本。
