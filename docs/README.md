# MIAGuard 文档索引

更新于 2026-11-18。本索引用于按主题找资料；实验结论以实际执行记录和对应数据产物为准。逐文件目录见[文档总目录](文档总目录_ZH.md)，归档材料按主题见[历史资料导读](归档资料/同主题资料导读.md)。

## 新会话快速接手

查找源码、运行配置、复算入口和目录整理记录时，先看[工程目录与整理记录](PROJECT_STRUCTURE_ZH.md)。

按顺序阅读：[当前开发状态](PROJECT_STATUS_ZH.md) → [正式数据与产物目录](DATA_CATALOG_ZH.md) → [实验索引](EXPERIMENT_INDEX_ZH.md)。进入访问控制开发时，读取[防御进度台账](DEFENSE_PROGRESS_ZH.md)及其指定的规格/计划/协议，再参考[攻击识别阶段交接](ATTACK_DETECTION_STAGE_HANDOVER_ZH.md)。根目录的 [AGENTS.md](../AGENTS.md) 记录了阅读顺序和持续记录规则。

**选择版本的集中入口：[当前版本总表](CURRENT_VERSIONS_ZH.md)。** 在上述入口阅读后、选择实际文件前核对；总表区分最新查询库、已有实验来源、候选/诊断、开发文档和源码身份。

当前有效规格、主计划和协议为原路径的 **v1.1**。截至 2026-11-17，T10-D 的 48 题正常效用开发配对已完成，当前仍需推进独立来源、人工审核、攻击校准和受控过滤对照；具体顺序以[进度台账](DEFENSE_PROGRESS_ZH.md)最新 `next_task` 和追加记录为准。正式数据与人工 gold 尚未验收。

| 开发时要确认的问题 | 对应文件及职责 |
|---|---|
| 当前应使用哪个数据/实验/框架版本 | [当前版本总表](CURRENT_VERSIONS_ZH.md)，按用途选择并回查原始 manifest/摘要 |
| 当前任务、完成证据、下一步 | [进度台账](DEFENSE_PROGRESS_ZH.md)，唯一状态入口 |
| 具体改什么、如何验收 | [主实施计划 v1.1](superpowers/plans/2026-10-22-defense-framework-implementation.md)，T10 已细化 A–E |
| 接口和组件必须满足什么 | [开发规格 v1.1](superpowers/specs/2026-10-22-defense-framework-design.md) |
| 数据、指标、审核和实验规则 | [实验协议 v1.1](DEFENSE_EXPERIMENT_PROTOCOL_ZH.md) |
| 使用哪个数据版本、结果在哪里 | [数据目录](DATA_CATALOG_ZH.md)、[实验索引](EXPERIMENT_INDEX_ZH.md)，数值/身份回查原始 JSON |
| 已完成的实验指标与汇报结果 | [实验结果汇总](EXPERIMENT_RESULTS_ZH.md)，提供指标表、限制和原始记录入口 |

文献综述、初始研究建议、旧路线图和审核报告提供背景及历史依据；与最新执行文件冲突时先核对原始产物，在台账追加纠错，再同步有效文档。计划勾选代表有证据的子步骤完成，不代表整项研究目标已达成。

## 当前 Judge 实验：先读这里

| 文件 | 内容 |
|---|---|
| [Progressive Judge v3：二分类 Logprob 实验](PROGRESSIVE_JUDGE_V3_BINARY_LOGPROB_EXPERIMENT_ZH.md) | 当前实验的评分定义、训练与验证流程、rubric 和二分类 logprob 的最终测试对比、产物路径。 |
| [LLM-as-Judge 防御与攻击模式库](LLM_AS_JUDGE_DEFENSE_ZH.md) | Judge 和攻击模式库的整体说明。 |

本轮 rubric/logprob 对比的设计和实施记录见 [设计说明](superpowers/specs/2026-10-15-rubric-logprob-frozen-comparison-design.md) 与 [实施计划](superpowers/plans/2026-10-15-rubric-logprob-frozen-comparison.md)。这两份记录解释实现选择；结果以 v3 实验文档为准。

## 项目使用与攻击背景

| 文件 | 内容 |
|---|---|
| [使用手册](USAGE_GUIDE_ZH.md) | 项目运行和使用入口。 |
| [Direct RAG-MIA 与 S²-MIA](baseline_rag_mia_attacks.md) | 基线攻击说明。 |
| [Masked MIA 与 IA 本地迁移](attack_migration.md) | 其他两类攻击的迁移说明。 |
| [老师实验模型本地部署](teacher_models.md) | 教师模型部署。 |
| [老师模型本地调用](teacher_local_runtime.md) | 教师模型调用方式。 |

## 查询库与数据

| 文件 | 内容 |
|---|---|
| [离线 Query Bank 使用说明](QUERY_BANK_ZH.md) | 查询库的使用。 |
| [第一阶段数据在防御实验中的复用规则](DEFENSE_DATA_REUSE_ZH.md) | 最新 v2 train、历史 v1 结果、开发补充与新保留数据的用途；已有字段和缺口；先复用后补建的待办。 |
| [Query Bank 构建指南](QUERY_BANK_BUILD_GUIDE_ZH.md) | 数据集构建与多数据集使用。 |
| [统一查询数据字典](data_dictionary.md) | 查询记录字段定义；标题沿用历史项目名 MIAFence。 |
| [AG News 当前提示词](AG_NEWS_CURRENT_PROMPTS_ZH.md) | AG News 单阈值实验所用提示词说明。 |

## 防御框架与其他评测

| 文件 | 内容 |
|---|---|
| [成员推断防御的访问控制文献调研](ACCESS_CONTROL_DEFENSE_LITERATURE_REVIEW_ZH.md) | 访问控制、目标证据隐藏、按风险选择动作及隐私与正常问答质量的联合评估；属于研究建议，尚非已完成实验。 |
| [防御开发与实验进度台账](DEFENSE_PROGRESS_ZH.md) | 本阶段任务状态、next_task、门禁、实际运行与追加式进度记录。后续开发先读此页。 |
| [T10 D-dev 模型预审接收与修订决策](../reports/defense_v1/T10/REVIEW_TRIAGE_20261030_ZH.md) | 首轮 86 条审核的独立结构核验、源码对应缺陷、修订试点与下一步；[第二轮审核指南](../reports/defense_v1/T10/pilot_revision_20261030_01/REVIEW_GUIDE_ZH.md)随新包提供。 |
| [T10 第二轮模型预审接收与开发决策](../reports/defense_v1/T10/REVIEW_TRIAGE_REV2_20261030_ZH.md) | 第二轮 86 条的独立核验、三条跨文档证据修复、D-dev 开发试点身份及短文会话质量阻塞。 |
| [T10-C 会话试点阶段记录](../reports/defense_v1/T10/session_length_pilot_20261031_01/DECISION_ZH.md) | 同源 2/3 轮、扩展文档草稿与未完成事项；[独立审核交接](../reports/defense_v1/T10/session_length_pilot_20261031_01/REVIEW_GUIDE_ZH.md)可交给外部审核者。 |
| [T10-C 模型审核处理与修订决定](../reports/defense_v1/T10/REVIEW_TRIAGE_T10C_20261102_ZH.md) | 70 条模型预审核验、四个版本修订、来源相似性诊断与待裁决事项；模型审核不是人工 gold。 |
| [T10-C D-dev 选择与对照](../reports/defense_v1/T10/session_length_dev_cohort_20261102_01/DECISION_ZH.md) | 28 个两轮基础会话、2 个共享来源的三轮诊断及本地模型对照；仅为开发设计。 |
| [防御框架开发规格 v1.1](superpowers/specs/2026-10-22-defense-framework-design.md) | 组件职责、接口契约、风险/动作/会话规则及需求追踪；包含查询版本与审核边界。 |
| [防御框架详细实施计划](superpowers/plans/2026-10-22-defense-framework-implementation.md) | P0–P5 共 18 个任务的文件、步骤、测试、产物和验收。 |
| [防御实验协议 v1.1](DEFENSE_EXPERIMENT_PROTOCOL_ZH.md) | E00–E07 的数据划分、对照/消融、变长会话统计、审核、冻结与恢复规则。 |
| [下一阶段防御开发与实验建议](DEFENSE_DEVELOPMENT_EXPERIMENT_RECOMMENDATIONS_ZH.md) | 2026-10-22 初始研究取舍；部分工程已由主计划实施，本文不作为当前状态或独立执行指令。 |
| [历史防御路线图](DEFENSE_ROADMAP_ZH.md) | 旧 Rule-only/阶段二路线及验收背景；当前执行按 T01–T18 主计划。 |
| [攻击识别阶段交接](ATTACK_DETECTION_STAGE_HANDOVER_ZH.md) | 阶段交接说明。 |
| [两阶段风险框架基础](TWO_STAGE_FOUNDATION_ZH.md) | 两阶段防御的基础定义。 |
| [两阶段 Direct Scoring](TWO_STAGE_DIRECT_SCORING_ZH.md) | Direct Scoring 的使用与实验。 |
| [Rule-only 防御](RULE_BASED_DEFENSE_ZH.md) | 规则防御方法。 |
| [AG News 单阈值监督校准](AG_NEWS_SUPERVISED_THRESHOLD_EXPERIMENT_ZH.md) | 单阈值实验框架。 |
| [阶段二 IA 访问动作评测](STAGE2_IA_POLICY_EVALUATION_ZH.md) | IA 访问策略评测。 |
| [大样本与困难查询实验](LARGE_AND_HARD_QUERY_EVALUATION_ZH.md) | 扩展样本与困难查询评估。 |

## Judge v2 历史资料

这些文件记录 v2 的提示词、分数分布和融合分析；当前 rubric/logprob 最终对比请读上面的 v3 实验文档。

| 文件 | 内容 |
|---|---|
| [Progressive Judge v2 实验](PROGRESSIVE_JUDGE_V2_EXPERIMENT_ZH.md) | v2 实验过程。 |
| [AG News Judge v2 提示词](AG_NEWS_PROGRESSIVE_JUDGE_V2_PROMPTS_ZH.md) | v2 提示词中文说明。 |
| [v2 分数分布分析](JUDGE_SCORE_SEPARABILITY_V2_ANALYSIS_ZH.md) | v2 的 x1/x2 分布。 |
| [v2 融合模型与图表](JUDGE_SCORE_FUSION_V2_MODEL_AND_FIGURES_ZH.md) | v2 融合模型和图表。 |

## 维护与过程记录

- [Git 版本管理与同步](GIT_WORKFLOW_ZH.md)提供提交范围、日常同步、回滚和新机器恢复说明。
- [文件清理审计](CLEANUP_AUDIT_ZH.md)：历史清理审计。
- `superpowers/specs/`：按日期命名的设计规格；当前有效防御规格由[进度台账](DEFENSE_PROGRESS_ZH.md)指定。
- `superpowers/plans/`：对应的实施计划和修复计划；计划复选框与台账同步，完成结论还须有实际验收产物。
- `reports/`：2 份阶段汇报材料：[AG News 32+32 实验](reports/2026-08-08-ag-news-32x32-report-materials.md)、[教师汇报提纲](reports/2026-08-10-teacher-presentation-outline.md)。
- `assets/`：3 张流程图：[两阶段防御](assets/miaguard-two-stage-defense-flow.png)、[两阶段攻击分类](assets/miaguard-two-stage-attack-classification-flow.png)、[AG News 查询库构建](assets/ag-news-query-bank-construction-flow.png)。

最新正常效用开发对照：[48题 B0/V2 配对报告](../reports/defense_v1/T10/UTILITY48_REUSE_RESULTS_20261117_ZH.md)，96/96 完成；V2 在该批全部放行，评审为 agent，结果适用于这批开发样本。数据和模型身份见[版本总表](CURRENT_VERSIONS_ZH.md)。其他攻防开发对照及历史结果见[实验索引](EXPERIMENT_INDEX_ZH.md)。
