# MIAGuard 文档总目录

更新：2026-11-17。按书籍目录方式查找文档，先看“常用入口与现行执行依据”，再按主题查阅。当前任务以防御进度台账为准，指标及版本身份以运行 manifest 和原始结果为准。

“历史”表示记录当时的设计、实验或规划，并不表示文件内容已被逐项证伪；不能把当时的下一步直接作为现在的任务。归档正文保存在 `归档资料/`，原路径的短文件为兼容入口。

[历史资料主题导读](归档资料/同主题资料导读.md) 将相似材料集中导航；[本目录](文档总目录_ZH.md)负责逐文件检索。

## 常用入口与现行执行依据

| 文档 | 路径 | 性质 | 内容与用途 |
|---|---|---|---|
| [MIAGuard 工程目录与整理记录](PROJECT_STRUCTURE_ZH.md) | `PROJECT_STRUCTURE_ZH.md` | 当前入口 | 目录用途、代码调用关系、常用命令、整理清单与恢复方式 |
| [MIAGuard Git 版本管理与同步](GIT_WORKFLOW_ZH.md) | `GIT_WORKFLOW_ZH.md` | 维护入口 | Git 跟踪范围、同步、回滚及本地数据恢复 |
| [MIAGuard 当前版本总表](CURRENT_VERSIONS_ZH.md) | `CURRENT_VERSIONS_ZH.md` | 当前入口 | 数据、模型、代码和实验版本总表 |
| [MIAGuard 数据与正式产物目录](DATA_CATALOG_ZH.md) | `DATA_CATALOG_ZH.md` | 当前入口 | 数据集、划分与产物入口 |
| [MIAGuard 防御实验协议 v1.1](DEFENSE_EXPERIMENT_PROTOCOL_ZH.md) | `DEFENSE_EXPERIMENT_PROTOCOL_ZH.md` | 当前入口 | 防御实验分组、指标和验收协议 |
| [MIAGuard 防御开发与实验进度台账](DEFENSE_PROGRESS_ZH.md) | `DEFENSE_PROGRESS_ZH.md` | 当前入口 | 防御开发进度、实际命令与 next_task 台账 |
| [MIAGuard 实验索引](EXPERIMENT_INDEX_ZH.md) | `EXPERIMENT_INDEX_ZH.md` | 当前入口 | 实验结果及原始运行记录索引 |
| [MIAGuard 实验结果汇总](EXPERIMENT_RESULTS_ZH.md) | `EXPERIMENT_RESULTS_ZH.md` | 当前入口 | 当前实验指标表、限制及详细结果入口 |
| [MIAGuard 当前开发状态](PROJECT_STATUS_ZH.md) | `PROJECT_STATUS_ZH.md` | 当前入口 | 项目当前完成状态和下一步 |
| [MIAGuard 文档索引](README.md) | `README.md` | 当前入口 | 现有文档导航及项目入口 |
| [MIAGuard Defense Framework Implementation Plan](superpowers/plans/2026-10-22-defense-framework-implementation.md) | `superpowers/plans/2026-10-22-defense-framework-implementation.md` | 当前入口 | 当前防御框架实施计划及任务清单 |
| [MIAGuard 防御框架开发规格 v1.1](superpowers/specs/2026-10-22-defense-framework-design.md) | `superpowers/specs/2026-10-22-defense-framework-design.md` | 当前入口 | 当前防御框架规格 v1.1 |

## 专题资料与使用说明

| 文档 | 路径 | 性质 | 内容与用途 |
|---|---|---|---|
| [MIAGuard：面向 RAG 成员推断的访问控制防御文献综述与实验设计](ACCESS_CONTROL_DEFENSE_LITERATURE_REVIEW_ZH.md) | `ACCESS_CONTROL_DEFENSE_LITERATURE_REVIEW_ZH.md` | 专题参考 | 访问控制、目标证据隐藏、按风险选择动作及隐私与正常问答质量的联合评估；属于研究建议，尚非已完成实验 |
| [AG News 单阈值实验：当前提示词中文说明](AG_NEWS_CURRENT_PROMPTS_ZH.md) | `AG_NEWS_CURRENT_PROMPTS_ZH.md` | 专题参考 | AG News 单阈值实验所用提示词说明 |
| [AG News 单阈值监督校准实验框架](AG_NEWS_SUPERVISED_THRESHOLD_EXPERIMENT_ZH.md) | `AG_NEWS_SUPERVISED_THRESHOLD_EXPERIMENT_ZH.md` | 专题参考 | 单阈值实验框架 |
| [MIAGuard 攻击识别阶段交接文档](ATTACK_DETECTION_STAGE_HANDOVER_ZH.md) | `ATTACK_DETECTION_STAGE_HANDOVER_ZH.md` | 专题参考 | 阶段交接说明 |
| [Masked MIA 与 IA 的本地迁移说明](attack_migration.md) | `attack_migration.md` | 专题参考 | 其他两类攻击的迁移说明 |
| [Direct RAG-MIA 与 S²-MIA](baseline_rag_mia_attacks.md) | `baseline_rag_mia_attacks.md` | 专题参考 | 基线攻击说明 |
| [MIAFence 统一查询数据字典](data_dictionary.md) | `data_dictionary.md` | 专题参考 | 查询记录字段定义；标题沿用历史项目名 MIAFence |
| [第一阶段数据在防御实验中的复用规则](DEFENSE_DATA_REUSE_ZH.md) | `DEFENSE_DATA_REUSE_ZH.md` | 专题参考 | 最新 v2 train、历史 v1 结果、开发补充与新保留数据的用途；已有字段和缺口；先复用后补建的待办 |
| [MIAGuard 下一阶段防御开发与实验建议](DEFENSE_DEVELOPMENT_EXPERIMENT_RECOMMENDATIONS_ZH.md) | `DEFENSE_DEVELOPMENT_EXPERIMENT_RECOMMENDATIONS_ZH.md` | 专题参考 | 2026-10-22 初始研究取舍；部分工程已由主计划实施，本文不作为当前状态或独立执行指令 |
| [大样本与困难查询实验](LARGE_AND_HARD_QUERY_EVALUATION_ZH.md) | `LARGE_AND_HARD_QUERY_EVALUATION_ZH.md` | 专题参考 | 扩展样本与困难查询评估 |
| [LLM-as-Judge 防御与攻击模式库](LLM_AS_JUDGE_DEFENSE_ZH.md) | `LLM_AS_JUDGE_DEFENSE_ZH.md` | 专题参考 | Judge 和攻击模式库的整体说明 |
| [Progressive Judge v3：二分类归一化 Logprob 实验](PROGRESSIVE_JUDGE_V3_BINARY_LOGPROB_EXPERIMENT_ZH.md) | `PROGRESSIVE_JUDGE_V3_BINARY_LOGPROB_EXPERIMENT_ZH.md` | 专题参考 | 当前实验的评分定义、训练与验证流程、rubric 和二分类 logprob 的最终测试对比、产物路径 |
| [Query Bank 数据集构建与多数据集使用指南](QUERY_BANK_BUILD_GUIDE_ZH.md) | `QUERY_BANK_BUILD_GUIDE_ZH.md` | 专题参考 | 数据集构建与多数据集使用 |
| [离线 Query Bank 使用说明](QUERY_BANK_ZH.md) | `QUERY_BANK_ZH.md` | 专题参考 | 查询库的使用 |
| [MIAGuard 当前 Rule-only 防御方法](RULE_BASED_DEFENSE_ZH.md) | `RULE_BASED_DEFENSE_ZH.md` | 专题参考 | 规则防御方法 |
| [阶段二：IA 访问动作安全校正评测](STAGE2_IA_POLICY_EVALUATION_ZH.md) | `STAGE2_IA_POLICY_EVALUATION_ZH.md` | 专题参考 | IA 访问策略评测 |
| [老师模型的本地直接调用](teacher_local_runtime.md) | `teacher_local_runtime.md` | 专题参考 | 教师模型调用方式 |
| [老师实验模型的本地部署](teacher_models.md) | `teacher_models.md` | 专题参考 | 教师模型部署 |
| [MIAGuard 两阶段 LLM Direct Scoring 使用与实验说明](TWO_STAGE_DIRECT_SCORING_ZH.md) | `TWO_STAGE_DIRECT_SCORING_ZH.md` | 专题参考 | Direct Scoring 的使用与实验 |
| [MIAGuard 两阶段风险框架：基础阶段说明](TWO_STAGE_FOUNDATION_ZH.md) | `TWO_STAGE_FOUNDATION_ZH.md` | 专题参考 | 两阶段防御的基础定义 |
| [MIAGuard RAG 成员推理攻击使用手册](USAGE_GUIDE_ZH.md) | `USAGE_GUIDE_ZH.md` | 专题参考 | 项目运行和使用入口 |

## 历史归档与兼容入口

| 文档 | 路径 | 性质 | 内容与用途 |
|---|---|---|---|
| [历史文档入口](AG_NEWS_PROGRESSIVE_JUDGE_V2_PROMPTS_ZH.md) | `AG_NEWS_PROGRESSIVE_JUDGE_V2_PROMPTS_ZH.md` | 原路径入口 | 兼容历史链接的归档跳转 |
| [历史文档入口](CLEANUP_AUDIT_ZH.md) | `CLEANUP_AUDIT_ZH.md` | 原路径入口 | 兼容历史链接的归档跳转 |
| [历史文档入口](DEFENSE_ROADMAP_ZH.md) | `DEFENSE_ROADMAP_ZH.md` | 原路径入口 | 兼容历史链接的归档跳转 |
| [历史文档入口](JUDGE_SCORE_FUSION_V2_MODEL_AND_FIGURES_ZH.md) | `JUDGE_SCORE_FUSION_V2_MODEL_AND_FIGURES_ZH.md` | 原路径入口 | 兼容历史链接的归档跳转 |
| [历史文档入口](JUDGE_SCORE_SEPARABILITY_V2_ANALYSIS_ZH.md) | `JUDGE_SCORE_SEPARABILITY_V2_ANALYSIS_ZH.md` | 原路径入口 | 兼容历史链接的归档跳转 |
| [历史文档入口](PROGRESSIVE_JUDGE_V2_EXPERIMENT_ZH.md) | `PROGRESSIVE_JUDGE_V2_EXPERIMENT_ZH.md` | 原路径入口 | 兼容历史链接的归档跳转 |
| [AG News：LLM-as-Judge v2 当前提示词中文说明](归档资料/AG_NEWS_PROGRESSIVE_JUDGE_V2_PROMPTS_ZH.md) | `归档资料/AG_NEWS_PROGRESSIVE_JUDGE_V2_PROMPTS_ZH.md` | 历史归档 | 旧版正文与历史背景 |
| [MIAGuard 文件清理审计](归档资料/CLEANUP_AUDIT_ZH.md) | `归档资料/CLEANUP_AUDIT_ZH.md` | 历史归档 | 旧版正文与历史背景 |
| [MIAGuard 防御框架递进实施路线](归档资料/DEFENSE_ROADMAP_ZH.md) | `归档资料/DEFENSE_ROADMAP_ZH.md` | 历史归档 | 旧版正文与历史背景 |
| [AG News v2：Judge 双风险分数融合模型与图表说明](归档资料/JUDGE_SCORE_FUSION_V2_MODEL_AND_FIGURES_ZH.md) | `归档资料/JUDGE_SCORE_FUSION_V2_MODEL_AND_FIGURES_ZH.md` | 历史归档 | 旧版正文与历史背景 |
| [AG News v2：LLM-as-Judge 双风险分数分布分析报告](归档资料/JUDGE_SCORE_SEPARABILITY_V2_ANALYSIS_ZH.md) | `归档资料/JUDGE_SCORE_SEPARABILITY_V2_ANALYSIS_ZH.md` | 历史归档 | 旧版正文与历史背景 |
| [Progressive Judge v2 实验说明](归档资料/PROGRESSIVE_JUDGE_V2_EXPERIMENT_ZH.md) | `归档资料/PROGRESSIVE_JUDGE_V2_EXPERIMENT_ZH.md` | 历史归档 | 旧版正文与历史背景 |
| [历史资料主题导读](归档资料/同主题资料导读.md) | `归档资料/同主题资料导读.md` | 历史归档 | 旧版正文与历史背景 |

## 设计规格记录

| 文档 | 路径 | 性质 | 内容与用途 |
|---|---|---|---|
| [MIAGuard 版本化离线查询库设计](superpowers/specs/2026-07-24-versioned-query-bank-design.md) | `superpowers/specs/2026-07-24-versioned-query-bank-design.md` | 历史设计记录 | 设计背景与约束：MIAGuard 版本化离线查询库设计 |
| [IA Query Bank 教师流程对齐设计](superpowers/specs/2026-07-26-ia-query-bank-teacher-aligned-design.md) | `superpowers/specs/2026-07-26-ia-query-bank-teacher-aligned-design.md` | 历史设计记录 | 设计背景与约束：IA Query Bank 教师流程对齐设计 |
| [Query Bank IA Eligibility Filter Design](superpowers/specs/2026-08-07-query-bank-ia-eligibility-filter-design.md) | `superpowers/specs/2026-08-07-query-bank-ia-eligibility-filter-design.md` | 历史设计记录 | 设计背景与约束：Query Bank IA Eligibility Filter Design |
| [IA Query Bank 平衡容量增量修复设计](superpowers/specs/2026-08-12-ia-query-bank-balanced-capacity-repair-design.md) | `superpowers/specs/2026-08-12-ia-query-bank-balanced-capacity-repair-design.md` | 历史设计记录 | 设计背景与约束：IA Query Bank 平衡容量增量修复设计 |
| [IA `no` 标签修复韧性设计](superpowers/specs/2026-08-17-ia-no-label-repair-resilience-design.md) | `superpowers/specs/2026-08-17-ia-no-label-repair-resilience-design.md` | 历史设计记录 | 设计背景与约束：IA `no` 标签修复韧性设计 |
| [IA Query Bank 10+10 锚点配对补全设计](superpowers/specs/2026-08-17-ia-query-bank-10x10-anchor-pair-repair-design.md) | `superpowers/specs/2026-08-17-ia-query-bank-10x10-anchor-pair-repair-design.md` | 历史设计记录 | 设计背景与约束：IA Query Bank 10+10 锚点配对补全设计 |
| [AG News 查询库监督式攻击阈值校准设计](superpowers/specs/2026-08-18-query-bank-supervised-attack-threshold-design.md) | `superpowers/specs/2026-08-18-query-bank-supervised-attack-threshold-design.md` | 历史设计记录 | 设计背景与约束：AG News 查询库监督式攻击阈值校准设计 |
| [MIAGuard Progressive LLM-as-Judge v2 设计规格](superpowers/specs/2026-08-23-progressive-judge-v2-design.md) | `superpowers/specs/2026-08-23-progressive-judge-v2-design.md` | 历史设计记录 | 设计背景与约束：MIAGuard Progressive LLM-as-Judge v2 设计规格 |
| [Direct RAG-MIA 客观观察增强与训练对照验证设计](superpowers/specs/2026-08-24-direct-rag-observation-fix-design.md) | `superpowers/specs/2026-08-24-direct-rag-observation-fix-design.md` | 历史设计记录 | 设计背景与约束：Direct RAG-MIA 客观观察增强与训练对照验证设计 |
| [Progressive Judge 普通无攻击线索路由设计](superpowers/specs/2026-08-24-progressive-judge-no-attack-cue-routing-design.md) | `superpowers/specs/2026-08-24-progressive-judge-no-attack-cue-routing-design.md` | 历史设计记录 | 设计背景与约束：Progressive Judge 普通无攻击线索路由设计 |
| [Progressive Judge 闭集证据码定向修复设计](superpowers/specs/2026-08-25-progressive-judge-evidence-code-repair-design.md) | `superpowers/specs/2026-08-25-progressive-judge-evidence-code-repair-design.md` | 历史设计记录 | 设计背景与约束：Progressive Judge 闭集证据码定向修复设计 |
| [Progressive Judge IA 会话判定与评分一致性设计](superpowers/specs/2026-08-25-progressive-judge-ia-session-consistency-design.md) | `superpowers/specs/2026-08-25-progressive-judge-ia-session-consistency-design.md` | 历史设计记录 | 设计背景与约束：Progressive Judge IA 会话判定与评分一致性设计 |
| [Progressive Judge 结构化 Router 修复设计](superpowers/specs/2026-08-26-progressive-judge-structured-router-design.md) | `superpowers/specs/2026-08-26-progressive-judge-structured-router-design.md` | 历史设计记录 | 设计背景与约束：Progressive Judge 结构化 Router 修复设计 |
| [Progressive Judge Verifier Contract 修复设计](superpowers/specs/2026-08-27-progressive-judge-verifier-contract-design.md) | `superpowers/specs/2026-08-27-progressive-judge-verifier-contract-design.md` | 历史设计记录 | 设计背景与约束：Progressive Judge Verifier Contract 修复设计 |
| [LLM-as-Judge 双风险分数可分性与融合实验设计](superpowers/specs/2026-08-29-judge-score-separability-and-fusion-design.md) | `superpowers/specs/2026-08-29-judge-score-separability-and-fusion-design.md` | 历史设计记录 | 设计背景与约束：LLM-as-Judge 双风险分数可分性与融合实验设计 |
| [AG News Query Bank v2 良性查询扩充设计](superpowers/specs/2026-08-30-ag-news-query-bank-v2-benign-expansion-design.md) | `superpowers/specs/2026-08-30-ag-news-query-bank-v2-benign-expansion-design.md` | 历史设计记录 | 设计背景与约束：AG News Query Bank v2 良性查询扩充设计 |
| [AG News Query Bank v2: 弹性良性查询扩充设计](superpowers/specs/2026-08-31-flexible-benign-expansion-design.md) | `superpowers/specs/2026-08-31-flexible-benign-expansion-design.md` | 历史设计记录 | 设计背景与约束：AG News Query Bank v2: 弹性良性查询扩充设计 |
| [Progressive Judge v3 Binary Logprob Design](superpowers/specs/2026-09-16-progressive-judge-v3-binary-logprob-design.md) | `superpowers/specs/2026-09-16-progressive-judge-v3-binary-logprob-design.md` | 历史设计记录 | 设计背景与约束：Progressive Judge v3 Binary Logprob Design |
| [Frozen Fusion Validation Design](superpowers/specs/2026-09-20-frozen-fusion-validation-design.md) | `superpowers/specs/2026-09-20-frozen-fusion-validation-design.md` | 历史设计记录 | 设计背景与约束：Frozen Fusion Validation Design |
| [Rubric 与二分类 Logprob 对等测试设计](superpowers/specs/2026-10-15-rubric-logprob-frozen-comparison-design.md) | `superpowers/specs/2026-10-15-rubric-logprob-frozen-comparison-design.md` | 历史设计记录 | 设计背景与约束：Rubric 与二分类 Logprob 对等测试设计 |

## 实施计划记录

| 文档 | 路径 | 性质 | 内容与用途 |
|---|---|---|---|
| [Versioned Offline Query Bank Implementation Plan](superpowers/plans/2026-07-24-versioned-query-bank.md) | `superpowers/plans/2026-07-24-versioned-query-bank.md` | 历史计划记录 | 当时的实施步骤：Versioned Offline Query Bank Implementation Plan |
| [IA Query Bank Teacher-Aligned Implementation Plan](superpowers/plans/2026-07-26-ia-query-bank-teacher-aligned.md) | `superpowers/plans/2026-07-26-ia-query-bank-teacher-aligned.md` | 历史计划记录 | 当时的实施步骤：IA Query Bank Teacher-Aligned Implementation Plan |
| [Query Bank IA Eligibility Filter Implementation Plan](superpowers/plans/2026-08-07-query-bank-ia-eligibility-filter.md) | `superpowers/plans/2026-08-07-query-bank-ia-eligibility-filter.md` | 历史计划记录 | 当时的实施步骤：Query Bank IA Eligibility Filter Implementation Plan |
| [IA Query Bank 平衡容量增量修复 Implementation Plan](superpowers/plans/2026-08-13-ia-query-bank-balanced-capacity-repair.md) | `superpowers/plans/2026-08-13-ia-query-bank-balanced-capacity-repair.md` | 历史计划记录 | 当时的实施步骤：IA Query Bank 平衡容量增量修复 Implementation Plan |
| [Deterministic IA `no` Queries Implementation Plan](superpowers/plans/2026-08-17-deterministic-ia-no-queries.md) | `superpowers/plans/2026-08-17-deterministic-ia-no-queries.md` | 历史计划记录 | 当时的实施步骤：Deterministic IA `no` Queries Implementation Plan |
| [IA `no` 标签修复韧性 Implementation Plan](superpowers/plans/2026-08-17-ia-no-label-repair-resilience.md) | `superpowers/plans/2026-08-17-ia-no-label-repair-resilience.md` | 历史计划记录 | 当时的实施步骤：IA `no` 标签修复韧性 Implementation Plan |
| [IA Query Bank 10+10 Anchor-Pair Repair Implementation Plan](superpowers/plans/2026-08-17-ia-query-bank-10x10-anchor-pair-repair.md) | `superpowers/plans/2026-08-17-ia-query-bank-10x10-anchor-pair-repair.md` | 历史计划记录 | 当时的实施步骤：IA Query Bank 10+10 Anchor-Pair Repair Implementation Plan |
| [Query Bank Supervised Attack Threshold Implementation Plan](superpowers/plans/2026-08-18-query-bank-supervised-attack-threshold.md) | `superpowers/plans/2026-08-18-query-bank-supervised-attack-threshold.md` | 历史计划记录 | 当时的实施步骤：Query Bank Supervised Attack Threshold Implementation Plan |
| [Progressive LLM-as-Judge v2 Implementation Plan](superpowers/plans/2026-08-23-progressive-judge-v2.md) | `superpowers/plans/2026-08-23-progressive-judge-v2.md` | 历史计划记录 | 当时的实施步骤：Progressive LLM-as-Judge v2 Implementation Plan |
| [Direct RAG-MIA Observation Fix Implementation Plan](superpowers/plans/2026-08-24-direct-rag-observation-fix.md) | `superpowers/plans/2026-08-24-direct-rag-observation-fix.md` | 历史计划记录 | 当时的实施步骤：Direct RAG-MIA Observation Fix Implementation Plan |
| [Progressive Judge No-Attack-Cue Routing Implementation Plan](superpowers/plans/2026-08-24-progressive-judge-no-attack-cue-routing.md) | `superpowers/plans/2026-08-24-progressive-judge-no-attack-cue-routing.md` | 历史计划记录 | 当时的实施步骤：Progressive Judge No-Attack-Cue Routing Implementation Plan |
| [Progressive Judge IA Session Consistency Implementation Plan](superpowers/plans/2026-08-25-progressive-judge-ia-session-consistency.md) | `superpowers/plans/2026-08-25-progressive-judge-ia-session-consistency.md` | 历史计划记录 | 当时的实施步骤：Progressive Judge IA Session Consistency Implementation Plan |
| [Progressive Judge 闭集证据码定向修复 Implementation Plan](superpowers/plans/2026-08-26-progressive-judge-evidence-code-repair.md) | `superpowers/plans/2026-08-26-progressive-judge-evidence-code-repair.md` | 历史计划记录 | 当时的实施步骤：Progressive Judge 闭集证据码定向修复 Implementation Plan |
| [Progressive Judge 结构化 Router 实施计划](superpowers/plans/2026-08-26-progressive-judge-structured-router.md) | `superpowers/plans/2026-08-26-progressive-judge-structured-router.md` | 历史计划记录 | 当时的实施步骤：Progressive Judge 结构化 Router 实施计划 |
| [Progressive Judge Verifier Contract Implementation Plan](superpowers/plans/2026-08-27-progressive-judge-verifier-contract.md) | `superpowers/plans/2026-08-27-progressive-judge-verifier-contract.md` | 历史计划记录 | 当时的实施步骤：Progressive Judge Verifier Contract Implementation Plan |
| [Judge Score Separability and Fusion Implementation Plan](superpowers/plans/2026-08-29-judge-score-separability-and-fusion.md) | `superpowers/plans/2026-08-29-judge-score-separability-and-fusion.md` | 历史计划记录 | 当时的实施步骤：Judge Score Separability and Fusion Implementation Plan |
| [AG News Query Bank v2 Benign Expansion Implementation Plan](superpowers/plans/2026-08-30-ag-news-query-bank-v2-benign-expansion.md) | `superpowers/plans/2026-08-30-ag-news-query-bank-v2-benign-expansion.md` | 历史计划记录 | 当时的实施步骤：AG News Query Bank v2 Benign Expansion Implementation Plan |
| [Flexible Benign Expansion Implementation Plan](superpowers/plans/2026-08-31-flexible-benign-expansion.md) | `superpowers/plans/2026-08-31-flexible-benign-expansion.md` | 历史计划记录 | 当时的实施步骤：Flexible Benign Expansion Implementation Plan |
| [AG News v2 Judge Score Fusion Training Implementation Plan](superpowers/plans/2026-09-03-v2-judge-score-fusion-training.md) | `superpowers/plans/2026-09-03-v2-judge-score-fusion-training.md` | 历史计划记录 | 当时的实施步骤：AG News v2 Judge Score Fusion Training Implementation Plan |
| [Progressive Judge v3 Binary Logprob Implementation Plan](superpowers/plans/2026-09-16-progressive-judge-v3-binary-logprob.md) | `superpowers/plans/2026-09-16-progressive-judge-v3-binary-logprob.md` | 历史计划记录 | 当时的实施步骤：Progressive Judge v3 Binary Logprob Implementation Plan |
| [Frozen Fusion Validation Implementation Plan](superpowers/plans/2026-09-20-frozen-fusion-validation.md) | `superpowers/plans/2026-09-20-frozen-fusion-validation.md` | 历史计划记录 | 当时的实施步骤：Frozen Fusion Validation Implementation Plan |
| [Rubric 与二分类 Logprob 对等测试 Implementation Plan](superpowers/plans/2026-10-15-rubric-logprob-frozen-comparison.md) | `superpowers/plans/2026-10-15-rubric-logprob-frozen-comparison.md` | 历史计划记录 | 当时的实施步骤：Rubric 与二分类 Logprob 对等测试 Implementation Plan |

## 历史汇报材料

| 文档 | 路径 | 性质 | 内容与用途 |
|---|---|---|---|
| [AG News Query Bank 32+32 最大平衡规模实验汇报材料](reports/2026-08-08-ag-news-32x32-report-materials.md) | `reports/2026-08-08-ag-news-32x32-report-materials.md` | 历史汇报 | 当时的报告或汇报提纲：AG News Query Bank 32+32 最大平衡规模实验汇报材料 |
| [MIAGuard 阶段性汇报讲稿与 PPT 提纲](reports/2026-08-10-teacher-presentation-outline.md) | `reports/2026-08-10-teacher-presentation-outline.md` | 历史汇报 | 当时的报告或汇报提纲：MIAGuard 阶段性汇报讲稿与 PPT 提纲 |

## 图像与其他资源

| 文档 | 路径 | 性质 | 内容与用途 |
|---|---|---|---|
| [ag-news-query-bank-construction-flow](assets/ag-news-query-bank-construction-flow.png) | `assets/ag-news-query-bank-construction-flow.png` | 配图 | 项目流程或构建图：ag-news-query-bank-construction-flow |
| [miaguard-two-stage-attack-classification-flow](assets/miaguard-two-stage-attack-classification-flow.png) | `assets/miaguard-two-stage-attack-classification-flow.png` | 配图 | 项目流程或构建图：miaguard-two-stage-attack-classification-flow |
| [miaguard-two-stage-defense-flow](assets/miaguard-two-stage-defense-flow.png) | `assets/miaguard-two-stage-defense-flow.png` | 配图 | 项目流程或构建图：miaguard-two-stage-defense-flow |

## 本目录自身

| 文档 | 路径 | 性质 | 内容与用途 |
|---|---|---|---|
| 文档总目录 | `文档总目录_ZH.md` | 导航 | 按路径逐一说明 docs 下文档和资源。 |
