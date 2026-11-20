# MIAGuard 实验索引

最新指标表和汇报入口见[实验结果汇总](EXPERIMENT_RESULTS_ZH.md)，详细身份与结果以各运行产物为准。

2026-11-18：为[含困难正常题的 11 月 17 日配对](../reports/defense_v1/T10/NEXT_GOAL_RESULTS_20261117_ZH.md#主配对初步结果)补评必要事实完整性、忠实度及检索和交付的标注证据覆盖率。[逐题补评与汇总](../reports/defense_v1/T10/difficult_normal_paired_offline_scores_20261118.json)基于原回答、初次检索与交付上下文，为开发集的事后模型辅助评分。

2026-11-18：四类各 40 目标开发对照已完成并核验 480/480，0 失败、0 跳过。[三类单轮主批](../data/defense_v1_runs/four-type40-single-paired-20261118-01/run_manifest.json) 240 次，[IA 三轮主批](../data/defense_v1_runs/four-type40-ia-paired-20261118-01/run_manifest.json) 240 次。[分子分母及案例](EXPERIMENT_RESULTS_ZH.md)、[单轮评分](../reports/defense_v1/T10/four_type40_single_paired_20261118_01_summary.json)与[IA 评分](../reports/defense_v1/T10/four_type40_ia_paired_20261118_01_summary.json)已同步。[链路试跑](../reports/defense_v1/T10/four_type40_smoke_20261118_01_verification.json) 24/24 单列。正式防御效果仍待独立评估。

2026-11-17：[48题复用新版结果](../reports/defense_v1/T10/UTILITY48_REUSE_RESULTS_20261117_ZH.md)及逐题评分已完成，V2全部allow，指标和限制见报告。

2026-11-17：[48题复用新版配对](../data/defense_v1_runs/utility48-reuse-paired-20261117-01/run_manifest.json)进行中，预期96次。

2026-11-17：[48题效用报告](../reports/defense_v1/T10/UTILITY48_RESULTS_20261117_ZH.md)，B0/V2 96/96，逐题评分与原始事件可复算；V2全allow，无法评估实际过滤效用。

2026-11-17：[48题B0/V2主配对](../data/defense_v1_runs/utility48-paired-20261117-01/run_manifest.json)进行中，预期96次；当前不报告效果指标。

2026-11-17：[真实机制消融](../data/defense_v1_runs/next-goal-ablation-20261117-01/run_manifest.json)32/32完成，[汇总](../reports/defense_v1/T10/next_goal_ablation_summary_20261117.json)显示仅IA格式分支对应正常对照的两次新增退化；为已见漏检和精选正常题，限单轮开发诊断。

2026-11-17：[IA格式正常对照](../data/defense_v1_runs/next-goal-ia-style-20261117-01/run_manifest.json)16/16完成，[agent复核](../reports/defense_v1/T10/next_goal_ia_style_agent_review_20261117.json)为B0 4/4、B2/V2 2/4、新候选0/4。受控[替代证据实验](../data/defense_v1_runs/next-goal-alternate-20261117-01/run_manifest.json)2/2完成。

2026-11-17：[下一轮主配对](../data/defense_v1_runs/next-goal-paired-20261117-01/run_manifest.json)188/188完成、零失败，[结果报告](../reports/defense_v1/T10/NEXT_GOAL_RESULTS_20261117_ZH.md)链接风险、攻击、正常复核和真实消融；正常对照显示候选违背预先设定的不降低V2正确率条件，保留V2。

2026-11-17：下一轮 T10-D 主配对和真实机制消融已完成，三张开发结果表已登记。结果以相应 manifest 和逐请求评分为准。见[执行清单](superpowers/plans/2026-10-22-defense-framework-implementation.md#t10-d-下一轮-goal)。

2026-11-17：[多动作主对照](../data/defense_v1_runs/multi-action-candidates-20261117-01/run_manifest.json)301/301和[来源扩展](../data/defense_v1_runs/multi-action-sources-20261117-01/run_manifest.json)95/95完成，均0失败；[结果报告](../reports/defense_v1/T10/MULTI_ACTION_REPORT_20261117_ZH.md)链接两批审计、按攻击和身份分组的指标及agent复核。均为已见来源的开发实验，无法证明总体泄露显著下降。

2026-11-17：[两小时配对运行](../data/defense_v1_runs/two-hour-paired-20261117-01/run_manifest.json)123/123完成，四类攻击与正常题见[报告](../reports/defense_v1/T10/TWO_HOUR_PAIRED_REPORT_20261117_ZH.md)，各指标的分母及限制以原始审计为准。

2026-11-16：多轮连续54/54、重置18/18及问法对照18/18完成，结果和身份见[补充报告](../reports/defense_v1/T10/SUPPLEMENT_RESULTS_20261116_ZH.md)。均为v2 train engineering_only，无真人gold或正式成员泄露结论。

2026-11-13 历史检查点：`multiturn-ia-session-20261113-01` 当时正在运行，预期18题×3方法=54个请求事件，身份见[run manifest](../data/defense_v1_runs/multiturn-ia-session-20261113-01/run_manifest.json)。同题重置和普通问句/填空问句条件已冻结，尚未登记完成。三案[证据复核](../reports/defense_v1/T10/benign_failure_audit_20261113_01/REPORT_ZH.md)是只读agent审核，不是新效果运行。

2026-11-13：困难正常题 B0/B2/B_TYPE_V2 配对 42/42，0 失败、0 跳过。三道 B2 拒答题中，V2 拒答两道、过滤一题的参考原文，正确且有证据 0/3。[运行清单](../data/defense_v1_runs/benign-triggered-pair-20261113-01/run_manifest.json)、[复核](../reports/defense_v1/T10/benign_pair_review_20261113.json)和[汇报](../reports/defense_v1/T10/TYPE_POLICY_PAIRED_20261113_ZH.md)。本批有目的地筛选，仅供开发诊断。

2026-11-13：类型驱动首轮四方法 108/108、V1/V2 同题复跑 54/54 完成，0 失败、0 跳过。见[中文汇报](../reports/defense_v1/T10/TYPE_POLICY_PAIRED_20261113_ZH.md)、[首轮运行](../data/defense_v1_runs/type-policy-v1-20261113-01/run_manifest.json)、[复跑](../data/defense_v1_runs/type-policy-v2-paired-20261113-01/run_manifest.json)与[配对差异](../reports/defense_v1/T10/type_policy_v2_retest_comparison_20261113.json)。两轮均为 engineering_only。

当前接续以[防御进度台账](DEFENSE_PROGRESS_ZH.md)及[主计划 T10-D 清单](superpowers/plans/2026-10-22-defense-framework-implementation.md)为准。2026-11-17 确认先复核多轮首次交付与首次限制、正常题证据与回答失败原因，再准备独立来源和真人审核。B0、B2、B_TYPE_V2 为后续主对照。下方各日期条目保留当时状态。

2026-11-09 同一 v2 train 排名压力测试18/18完成。3条库内填空攻击的目标分别排在第2–4位。B5三次都过滤第一篇并交付真正目标原文。B6最终只交付摘要，2份摘要含有待填词。3条困难正常题均放行且回答与B0相同。当前用途为工程诊断。详见[报告](../reports/defense_v1/T10/rank_stress_20261109_01/REPORT_ZH.md)与[运行清单](../data/defense_v1_runs/rank-stress-v2-b0-b5-b6-20261109-01/run_manifest.json)。

2026-11-05：B5过滤回填/B6摘要真实小批已完成24/24，见[对照报告](../reports/defense_v1/T10/fast_live_pilot_20261105_01/COMPARISON_B5_B6_ZH.md)及[运行清单](../data/defense_v1_runs/fast-v2-b5-b6-20261105-01/run_manifest.json)。四个正常回答与B0一致；B6摘要处理器实际接触原文。单轮、小样本、engineering_only，正式效果未验收。后续排名压力测试见上方11月9日条目。

核对日期：2026-11-09（北京时间）。状态用“已完成 / 下一阶段 / 历史中断”明确标记。指标摘要便于定位；复核时读取链接的结果 JSON，不从本文重新推导阈值。

跨数据、模型和框架的版本选择见[当前版本总表](CURRENT_VERSIONS_ZH.md)。最新查询库 v2 不改变下文已完成 Judge v3 实验使用 v1 的事实；未生成的新防御主实验没有可引用的正式版本。

当前接续：T10-D 以最新 `ag_news_queries_v2` / `ag_news_threshold_v2` train 做逐类型复用覆盖审计，再按缺口补标/改写/新增；[选择清单](../reports/defense_v1/T10/legacy_reuse_selection_20261104.json)和[版本核验](../reports/defense_v1/T10/query_bank_version_audit_20261104.json)已验证身份/字段；自动结构覆盖已完成，逐条语义/gold/适配未验收。已有 Judge v3 对照和 E00 使用 v1，不能改标为 v2；v2已有4正常+8攻击的真实B0/B2工程比较（见本页快速试跑），尚无正式效果运行。正式 E01–E07、T10-E、T11 和终测门禁不变，下文带日期条目为历史记录。

2026-11-05 预审工程更新：[接收与362条待审攻击草稿](../reports/defense_v1/T10/v2_reuse_review_integration_20261105_01/INTEGRATION_REPORT_ZH.md)已核验，含6条本地IA修订及144暂缓保留；没有真实模型/防御调用，不作为泄露下降或质量改善证据。

2026-11-05 数据工程更新：[v2 train 复用结构审计](../reports/defense_v1/T10/v2_train_reuse_audit_20261105_01/REUSE_REPORT_ZH.md)完成，覆盖 4,579 查询。Masked 解析契约用合成输出核对，不是模型攻击成功率；没有新增真实防御效果运行。

2026-10-22 进展更新：[防御实验协议](DEFENSE_EXPERIMENT_PROTOCOL_ZH.md)定义 E00–E07 的顺序、数据、基线、冻结和报告规则；E00 旧 train 小样本 observe 核对已完成，其余 E01–E07 尚未运行。逐任务/逐运行状态见[防御进度台账](DEFENSE_PROGRESS_ZH.md)。

2026-10-31 历史文档基线更新：规格/主计划/协议修订为 v1.1；当时 next_task 为 T10-C，会话轮数与文档选择试点已生成[开发草稿及中间统计](../reports/defense_v1/T10/session_length_pilot_20261031_01/DECISION_ZH.md)，结构核验通过，内容独立复核和最终选择尚未完成，没有新增防御效果数字。后续依次完成 T10-D 新候选、T10-E 人工 gold、T11 正式指标和 T12/E01 动作比较；正式终测仍须 T16 冻结。协议新增的变长会话汇总、Session 覆盖和 IA/Masked 诊断属于待实现评估要求。

2026-11-02 T10-C 进展：独立模型预审 70 条已[核验](../reports/defense_v1/T10/review_validation_t10c_20261102.json)，在[新修订试点](../reports/defense_v1/T10/session_length_pilot_rev2_20261102_01/manifest.json)处理四个版本；[处理决定](../reports/defense_v1/T10/REVIEW_TRIAGE_T10C_20261102_ZH.md)记录未决争议。31 篇的[SimHash 诊断](../reports/defense_v1/T10/near_duplicate_audit_t10c_20261102.json)无匹配，但事件语义独立性未证明。模型审核和文档处理不构成防御实验，最终轮数、T10-E 人工 gold 及 E01–E07 均未完成。

2026-11-02 T10-C 开发选择完成：[选择报告](../reports/defense_v1/T10/session_length_dev_cohort_20261102_01/selection_report.json)为七类各 4 个两轮基础会话，另加两个共享来源的三轮焦点诊断。固定来源的[七组历史对照](../data/defense_v1_runs/t10c-history-ablation-20261102-01/agent_diagnostic_summary.json)中，Codex agent 判断两条件各 7/7 答案受原文支持；[一组焦点对照](../data/defense_v1_runs/t10c-context-focus-20261102-01/agent_diagnostic_summary.json)有历史时两个焦点各自答对，无历史的两个重复请求都未说明歧义。均为本地 Qwen2.5 Q4、教师给定历史、小样本工程诊断，无真人 gold、无实际 Session/fusion 或防御效果。下一步 T10-D 先补历史来源审计与背景校验。

工程进展：T01–T09 完成，T10 数据候选及 T11 指标预研进行中，G0/G1 通过；证据见[防御进度台账](DEFENSE_PROGRESS_ZH.md)、[T04 阈值 JSON](../reports/defense_v1/T04/query_only_thresholds.json)、[E00 manifest](../data/defense_v1_runs/e00-observe-20261022-01/run_manifest.json)、[T08 G1 核验](../reports/defense_v1/T08/g1_validation.json)、[T09 fake 回放](../data/defense_v1_runs/t09-fake-20261022-05/metrics.json)、[T10 候选隔离核验](../reports/defense_v1/T10/validation.json)及[T11 fake 指标 v3](../reports/defense_v1/T11/fake_evaluation_v3.json)。T04 首两轮训练正常查询 120 条、60 个文档；1%/5% 经验 FPR cap 均选阈值 0.006692850924284855，文档级 95% 报警率上界约 6.02%，所以两个点均标 `empirical_only`。E00 只验证在线 observe 运行、原 trace 复算和成本；T06–T11 是工程验证，都不是成员泄露下降结果。

T10 `defense_access_v1_candidate06`：候选目标 3,600 篇，D-dev/A-cal/V/T 每类成员/非成员为 100/500/200/1000；每分区 1,000 篇独立索引；七类正常请求 1,750、四攻击请求 14,400，均为 `review_status=pending` 自动模板草稿。[候选 manifest](../data/defense_datasets/defense_access_v1_candidate06/manifest.json)、[隔离及重叠核验](../reports/defense_v1/T10/validation.json)。该候选尚无正式效果运行或有效的正常质量 gold；v2 train 已有真实开发对照，但 E01–E07 仍未运行。

T10 的 [D-dev 首轮试点包](../reports/defense_v1/T10/review_packet_manifest.json)含 70 条正常与 16 条攻击；首轮外部 DeepSeek 模型预审[结构核验](../reports/defense_v1/T10/review_validation_20261030.json)无错误，正常 60 rewrite/10 reject，攻击 10 accept/6 rewrite。第二轮预审[核验](../reports/defense_v1/T10/review_validation_rev2_20261030.json)为正常 61 accept/9 rewrite、攻击 15 accept/1 rewrite，但发现三条跨文档漏列第二篇证据。新的[D-dev 工程 overlay](../data/defense_datasets/defense_access_v1_pilot_overlay_rev2_20261030/manifest.json)与[独立验证](../data/defense_datasets/defense_access_v1_pilot_overlay_rev2_20261030/validation.json)同步了 70/16 在线问题与离线答案/标签；五轮短文会话仍重复，全部 pending，无人工 gold，原 candidate06 全量仍未正式复核；没有任何新版真实防御效果运行。T11 对 T09 的 synthetic fake 回放生成[工程评估 JSON v3](../reports/defense_v1/T11/fake_evaluation_v3.json)：四攻击每个方法都仅有一个 member 目标，AUC 因单类别写 `null`；正常 exact match 只按 fake 样本计，不代表真实效用。A-cal 方向/阈值仅有合成单测，正式 A-cal/T 阈值、质量和区间尚无结果。

T09 的 synthetic fake 链路 `run_id=t09-fake-20261022-05`：B0/B2/B3/B5 × 5 请求 = 20/20 完成，`analysis_role=engineering_only`；四攻击离线分数、正常请求行、请求/标签分离和 20 个受控生成输入 artifact 已核对。[运行清单](../data/defense_v1_runs/t09-fake-20261022-05/run_manifest.json)、[metrics](../data/defense_v1_runs/t09-fake-20261022-05/metrics.json)、[测试](../reports/defense_v1/T09/full-regression.txt)。`outcome=valid` 仅指工程运行完整，无论文防御效果数值。

## E00-observe（已完成，旧 train 小样本）

`run_id=e00-observe-20261022-01`；旧正式 train 1 条正常与 1 条 Direct 会话，10 次请求。Query/Session Judge 调用 10/6 次；Query-only/融合 4/6 次；10 次完整上下文与 allow；同 trace 在线/离线分数最大差 `0.0`。网关请求 p50/p95 `29.81/61.30` 秒。原始[manifest](../data/defense_v1_runs/e00-observe-20261022-01/run_manifest.json)、[comparison.json](../data/defense_v1_runs/e00-observe-20261022-01/comparison.json)、[live 与旧 train 对照](../reports/defense_v1/T05/live_rerun_comparison.json)及[101 项回归](../reports/defense_v1/T05/full-regression.txt)。未生成回答，不能推断防御效用或泄露变化。

## 当前 Judge v3：同口径评分头对照（已完成）

两种方案共享 `ag_news_queries_v1`、`ag_news_threshold_v1`、Qwen BF16 Judge 评分记录和 20 个 test 文档；各自使用 train 上拟合的 `logistic_l2` 与 train OOF 选定的阈值。test 比较 cohort 为 699 条可用 x1+x2 的记录。1% 与 5% 良性 FPR 目标各自选到同一阈值，因此两工作点的 test 指标相同。

| 指标（test） | LLM 直接评分 rubric | 二分类 logprob |
|---|---:|---:|
| AUROC | 0.8795 | 0.8615 |
| AUPRC | 0.9793 | 0.9788 |
| Brier（越低越好） | 0.2421 | 0.2411 |
| Accuracy / Precision | 0.7754 / 1.0000 | 0.7797 / 1.0000 |
| Recall / F1 | 0.7543 / 0.8599 | 0.7590 / 0.8630 |
| 良性 FPR | 0.0000 | 0.0000 |
| 四类攻击宏平均 Recall | 0.9036 | 0.9053 |
| Direct / IA / Masked / S² Recall | 0.9500 / 0.6645 / 1.0000 / 1.0000 | 0.9500 / 0.6710 / 1.0000 / 1.0000 |

| 方案 | 冻结模型 | validation | test |
|---|---|---|---|
| rubric | [logistic_l2.json](../data/judge_score_frozen_v3_rubric_20261015/logistic_l2.json) | [validation.json](../data/judge_score_validation_v3_rubric_20261015/validation.json) | [test.json](../data/judge_score_test_v3_rubric_20261015/test.json) |
| 二分类 logprob | [logistic_l2.json](../data/judge_score_frozen_v3_binary_logprob_20260920/logistic_l2.json) | [validation.json](../data/judge_score_validation_v3_binary_logprob_20260920/validation.json) | [test.json](../data/judge_score_test_v3_binary_logprob_20260920/test.json) |

统一对比：[final_test_comparison.json](../data/judge_score_comparison_v3_20261015/final_test_comparison.json)。训练分析和阈值来源：[分布分析](../data/judge_score_analysis_v3_binary_logprob_20260918/train/separability_report.json)、[模型比较](../data/judge_score_fusion_v3_binary_logprob_20260918/train/model_comparison.json)、[阈值选择](../data/judge_score_fusion_v3_binary_logprob_20260918/train/threshold_selection.json)。详细方法、限制和解释见[v3 实验文档](PROGRESSIVE_JUDGE_V3_BINARY_LOGPROB_EXPERIMENT_ZH.md)。

这份表比较的是“评分头 + 各自融合模型”，不是单独原始分数。test 正常样本较少且同会话记录相关，观测 FPR 为 0 不保证线上 FPR 为 0。logprob test 先于 rubric 补充评估被查看；未来改模型或访问策略须注明 test 复用情况。

## 其他实验状态

| 实验 | 状态 | 入口 |
|---|---|---|
| Rule-only 阶段一防御 MVP | 已完成的历史阶段 | [路线图与验收](DEFENSE_ROADMAP_ZH.md)、[项目 README](../README.md) |
| 阶段二 IA 策略留出评测 | 已完成的历史阶段 | [阶段二评测](STAGE2_IA_POLICY_EVALUATION_ZH.md) |
| Progressive Judge v2 三分类及旧分布/融合分析 | 历史实验，数据版本与本次不同 | [v2 实验](PROGRESSIVE_JUDGE_V2_EXPERIMENT_ZH.md)、[v2 融合](JUDGE_SCORE_FUSION_V2_MODEL_AND_FIGURES_ZH.md) |
| 2026-09-29 发起的旧三分类重跑 | 历史中断；仅 26 个会话分片，无可比最终指标 | [交接记录](ATTACK_DETECTION_STAGE_HANDOVER_ZH.md) |
| 新版 Judge 接入在线访问控制及防御效果评估 | T05 observe 与 E00 完成；T06–T09 工程实现完成，T10 候选数据/T11 指标预研进行中；已有真实开发对照，正式防御效果实验未开始 | [进度台账](DEFENSE_PROGRESS_ZH.md)、[详细计划](superpowers/plans/2026-10-22-defense-framework-implementation.md)、[实验协议](DEFENSE_EXPERIMENT_PROTOCOL_ZH.md) |

新实验登记时至少写明：实验 ID、目标、状态、数据与划分版本、模型/Prompt、训练/验证/测试产物、所用阈值、指标口径和限制。只有完整运行且有可核对产物时标“已完成”；失败或部分运行单独标注，不混入最终对比。

2026-11-04：T10-D 完成[保守开发来源清单及结构核验](../reports/defense_v1/T10/dev_source_inventory_20261104_01/validation.json)和来源关联信息缺失时拒绝的单元测试；这是数据准备与工程验证，没有新增防御效果实验。当前 next_task 仍为 T10-D，见[台账](DEFENSE_PROGRESS_ZH.md)。

2026-11-04：完成 [D-dev 开发导出结构验证](../reports/defense_v1/T10/dev_cohort_export_20261104_01/validation.json)，属于数据工程检查，不是攻击或防御效果实验。

2026-11-04：对两次已有 D-dev 文本理解对照完成[来源记录审计](../reports/defense_v1/T10/dev_run_source_audit_20261104.json)，并准备[文章事件关联预审包](../reports/defense_v1/T10/event_pair_review_packet_20261104_01/manifest.json)；没有新增攻击/防御效果实验。

2026-11-04：事件模型预审的[处理与敏感性分组](../reports/defense_v1/T10/EVENT_REVIEW_TRIAGE_20261104_ZH.md)已记录；会话组数是开发诊断假设，尚未执行重采样或防御效果实验。

2026-11-04：新增 E00 [检索来源工程审计](../reports/defense_v1/T10/e00_retrieved_source_audit_20261104.json)和 Masked 草稿规则单元测试；没有运行新的攻击或防御效果实验。

2026-11-04：Masked 规则[四篇小批结构验证和内容核查](../reports/defense_v1/T10/masked_rule_pilot_20261104_01/AGENT_REVIEW_ZH.md)及[指定词试点](../reports/defense_v1/T10/masked_selected_pilot_20261104_01/AGENT_REVIEW_ZH.md)完成；未测试模型填空、攻击成功或防御效果。

2026-11-05 快速真实试跑已完成：[结果报告](../reports/defense_v1/T10/fast_live_pilot_20261105_01/FAST_PILOT_REPORT_ZH.md)、[run manifest](../data/defense_v1_runs/fast-v2-b0-b2-20261105-01/run_manifest.json)。12题×B0/B2共24/24成功，原BF16；4组正常回答逐字一致，agent按必要事实各判4/4正确；B2拒答6/8攻击，非攻击成功率下降。Masked原严格分数有格式混淆，保留原分数并另列5/5与2/5恢复诊断。单轮、2攻击来源、非真人gold、engineering_only，正式E01–E07未放行。下一优先：先补齐现有回答的格式/语义评分诊断，再复用同一小批比较过滤回填/摘要等动作；仅按结果暴露的缺口增加少量困难正常题和三轮来源，不先扩建全库。

2026-11-11：五日计划输入预检完成，已有18条案例的[索引](../reports/defense_v1/T10/five_day_existing_cohort_20261111_01.json)仅用于开发，尚需补齐触发限制的正常题与独立多轮；[摘要核验](../reports/defense_v1/T10/five_day_preflight_20261111_01.json)26项通过。无新增模型运行，E01–E07状态不变。

2026-11-11：历史train正常查询复用评分[离线筛查](../reports/defense_v1/T10/reusable_normal_scores_20261111.json)：与v2同ID同文本294条单查询分数均低于T04阈值；不是线上动作实验，不覆盖新增v2正常题。

2026-11-11：v2新增正常题Query Judge[工程筛查](../reports/defense_v1/T10/new_benign_screen_20261111_01/summary.json)完成8/8，全部低于单查询阈值；未运行网关动作/生成或验证可答性，不作为误报率或正式效果。

2026-11-11：[正常题强制过滤诊断](../reports/defense_v1/T10/forced_normal_diagnostic_20261111_01/REPORT_ZH.md) 8/8完成；四次均移除参考来源并回答证据不足，Judge自然触发0/4。工程干预，不是自然误拦率或E01。

2026-11-11：排名压力小批新增[B2/B3对照](../reports/defense_v1/T10/rank_stress_20261109_01/CONSERVATIVE_B2_B3_20261111_ZH.md)，12/12完成；B3三条攻击零检索文档交付但各恢复1/5词，非总体泄露结论。E01仍未运行。

2026-11-11：[定位候选工程试跑](../reports/defense_v1/T10/rank_stress_20261109_01/LOCATOR_PILOT_20261111_ZH.md)6/6完成；已使用过的3个排名2–4目标排除3/3，逐词恢复5/15，仅开发诊断。新源码与定位版本以运行manifest为准。

2026-11-11：[新来源对照](../reports/defense_v1/T10/LOCATOR_NEW_SOURCES_20261111_ZH.md)24/24完成；6个成员目标均排名第一、无正常或非成员。三题未触发风险导致放行，另三题新旧定位均排除目标。仅工程诊断。

2026-11-11：[未触发trace核验](../reports/defense_v1/T10/locator_new_sources_untriggered_audit_20261111.json)确认3条均在初筛跳过细查，题面仍需正式审核；结果属于开发诊断。

2026-11-11：新增[查询线索候选对照](../reports/defense_v1/T10/QUERY_CUE_PILOT_20261111_ZH.md)，10/10工程试跑完成；规则覆盖盘点及原Judge分数分别记录，已见样本不能估计正式效果。

2026-11-11：[非成员/正常阅读对照](../reports/defense_v1/T10/CUE_UTILITY_NONMEMBER_20261111_ZH.md)24/24完成，发现1个新增规则拒答、旧方法可答的构造阅读练习；人工审核和总体效用仍待完成。
