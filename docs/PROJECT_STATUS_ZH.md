# MIAGuard 当前开发状态

2026-11-20 已核对新会话导航，补齐[代码文件索引](CODE_FILE_INDEX_ZH.md)，更新 AGENTS 与进度首页的当前恢复摘要。项目目录和代码职责见[工程目录](PROJECT_STRUCTURE_ZH.md)，开发下一步继续从 T10-D 接续。

2026-11-20 已建立 `main` 分支并成功同步到 `G-LittleSun/MIAGuard`，首次提交为 `9a74ec0`。Git 的提交范围、同步与回滚操作见[版本管理说明](GIT_WORKFLOW_ZH.md)。

2026-11-20 完成工程入口整理，已清理可核实的 pytest 临时产物和一份空测试日志。回收站核验及两处读取受限的目录见整理记录。[工程目录与整理记录](PROJECT_STRUCTURE_ZH.md)

2026-11-18：含困难正常题的既有配对已补评完整性、忠实度及标注证据覆盖率，适用于中期报告的开发对照。见[逐题补评与汇总](../reports/defense_v1/T10/difficult_normal_paired_offline_scores_20261118.json)。

2026-11-18：四类各 40 目标的 B0/V2 开发对照已完成并核验 480/480 次，0 失败、0 跳过。库内 Direct 的 Yes 从 20/20 降到 11/20，S² 目标原文交付从 20/20 降到 0/20，Masked 原词恢复从 93/100 降到 10/100，IA 至少一轮回答 Yes 的会话从 18/20 降到 9/20。正式独立防御效果评估仍待完成。详见[实验结果汇总](EXPERIMENT_RESULTS_ZH.md)与[进度台账](DEFENSE_PROGRESS_ZH.md)。

2026-11-17：[48题复用新版效用配对](../reports/defense_v1/T10/UTILITY48_REUSE_RESULTS_20261117_ZH.md)96/96完成，B0/V2有据正确35/36、完整性39/40、faithfulness已判60/62；V2全部allow，agent评分非真人gold。

2026-11-17：48题复用新版含13条直接复用，B0/V2重跑进行中；前版为开发中间结果。见[进度台账](DEFENSE_PROGRESS_ZH.md)。

2026-11-17：48题正常开发对照B0/V2 96/96完成，V2全部放行。正确且有证据35/36、必要事实39/40、agent评分faithfulness 53/55；局限和来源见[报告](../reports/defense_v1/T10/UTILITY48_RESULTS_20261117_ZH.md)。

2026-11-17：48题正常效用开发集已冻结，B0/V2主配对运行中；评分和结果未完成。见[进度台账](DEFENSE_PROGRESS_ZH.md)。

2026-11-17：下一轮主配对188/188、IA格式正常对照16/16、受控替代证据2/2、真实机制消融32/32完成，93项相关回归通过。[报告](../reports/defense_v1/T10/NEXT_GOAL_RESULTS_20261117_ZH.md)含三张表与消融。正常IA格式对照中V2原本正确的2题被新候选无上下文处理，未满足候选选择约束，保留V2作为开发对照。见[台账](DEFENSE_PROGRESS_ZH.md)。

2026-11-17：下一轮主配对、两项补充实验和真实机制消融完成；三张开发结果表及候选正常任务退化已记录。见 [T10-D 下一轮 Goal](superpowers/plans/2026-10-22-defense-framework-implementation.md#t10-d-下一轮-goal)。

2026-11-17：多动作候选在 T10-D 开发中，新增高风险 S² 摘要和无上下文两个候选，77项相关回归通过；43问×7方法301/301、19问×5方法95/95完成并工程审计。[开发结果报告](../reports/defense_v1/T10/MULTI_ACTION_REPORT_20261117_ZH.md)及agent复核已保存；两个候选未证明全面优于V2。正式gold、独立来源和攻击校准仍待完成；详见[台账](DEFENSE_PROGRESS_ZH.md)。

2026-11-17：两小时配对运行123/123完成，含四类攻击与14正常题。B0/B2/V2正常正确且证据交付为14/11/11。目标数和评分适用范围见[报告](../reports/defense_v1/T10/TWO_HOUR_PAIRED_REPORT_20261117_ZH.md)。正式终测与真人审核待完成。

2026-11-17：两小时真实配对实验已完成，41请求×B0/B2/B_TYPE_V2，运行记录见[台账](DEFENSE_PROGRESS_ZH.md)。当前运行基于已见开发来源，正式指标和真人审核仍待完成。

2026-11-17：用户确认后续沿用 B0、B2 和类型策略 V2 做主比较。当前从 T10-D 接续，先核查多轮 IA 在哪一轮首次交付原文和首次触发限制，以及正常题在哪个环节失去正确答案。随后补独立来源和真人审核，再推进正式防御与效用评估。[进度台账](DEFENSE_PROGRESS_ZH.md)

2026-11-16：多轮主实验54/54、重置18/18及问法对照18/18均完成，无失败跳过。连续会话IA 12请求中V2拒答5次，重置后全部放行；三组普通问句均可答，同事实填空均受限。均为开发诊断，详见[补充报告](../reports/defense_v1/T10/SUPPLEMENT_RESULTS_20261116_ZH.md)，next_task=T10-D。

2026-11-13 历史检查点（最终结果见上方2026-11-16记录）：4个IA来源的三轮序列与两组正常控制已冻结，B0/B2/V2预期54请求当时运行中；同题逐次重置18请求及问法配对18请求已准备。三道既有正常失败的[独立agent复核](../reports/defense_v1/T10/benign_failure_audit_20261113_01/REPORT_ZH.md)发现Treo所问容量已在前两轮暴露，授权边界仍未知。实际状态以[台账L181起](DEFENSE_PROGRESS_ZH.md)为准，next_task=T10-D。

2026-11-13 困难正常题补试：真实配对 42/42 完成。B2 拒答的三题中，V2 保留证据并答对 0/3，B0/B2/V2 在全批的正常正确且有证据数为 14/11/11。两组三轮在防御方法下均实测融合。[汇报材料](../reports/defense_v1/T10/TYPE_POLICY_PAIRED_20261113_ZH.md)。研究继续从 T10-D 补来源、多轮 IA 与实际人员审核。

2026-11-13：T10-D 类型驱动候选已完成真实模型首轮 108/108 和同题复跑 54/54，均无失败或跳过。V2 对四个库内 Masked 请求由过滤改为拒答，原词恢复 6/35 → 0/35，12 个正常回答与 V1 一致。全项目回归 513 通过、1 跳过。见[汇报材料](../reports/defense_v1/T10/TYPE_POLICY_PAIRED_20261113_ZH.md)。下一步补独立来源、多轮 IA 与正常人工审核，正式 T14、T10-E 和独立终测依赖待验收。

2026-11-11 用户确认后续方向：先根据请求及会话识别风险和可能攻击类型，再按类型、定位与会话暴露选择访问动作。当时固定动作和规则为工程对照，类型驱动动态策略尚未实现。先按主计划T10-D盘点在线类型与数据并验证候选，T14实现完整策略。详见[进度台账](DEFENSE_PROGRESS_ZH.md)。

2026-11-09 同一 v2 train 排名压力测试18/18完成。3条库内填空攻击的目标分别排在第2–4位。B5三次都过滤第一篇并交付真正目标原文。B6最终只交付摘要，2份摘要含有待填词。3条困难正常题均放行且回答与B0相同。当前用途为工程诊断。详见[报告](../reports/defense_v1/T10/rank_stress_20261109_01/REPORT_ZH.md)与[运行清单](../data/defense_v1_runs/rank-stress-v2-b0-b5-b6-20261109-01/run_manifest.json)。

2026-11-05：B5过滤回填/B6摘要真实小批已完成24/24，见[对照报告](../reports/defense_v1/T10/fast_live_pilot_20261105_01/COMPARISON_B5_B6_ZH.md)及[运行清单](../data/defense_v1_runs/fast-v2-b5-b6-20261105-01/run_manifest.json)。四个正常回答与B0一致；B6摘要处理器实际接触原文。单轮、小样本、engineering_only，正式效果未验收。后续排名压力测试见上方11月9日条目。

核对日期：2026-11-09（北京时间）。本页是新会话的短入口；身份和数值以链接的运行清单、冻结模型与结果 JSON 为准。

版本选择先核对[当前版本总表](CURRENT_VERSIONS_ZH.md)：最新数据复用用 v2 train；已有 Judge v3/E00 数据为 v1；开发文档基线 v1.1，包声明 0.1.0，源码身份另按快照记录。总表与原始 manifest 是版本导航，本次新增总表不表示 T10-D 或正式实验已完成。

执行文档更新：2026-10-31，统一为 v1.1。[开发规格](superpowers/specs/2026-10-22-defense-framework-design.md)、[详细实施计划](superpowers/plans/2026-10-22-defense-framework-implementation.md)、[实验协议](DEFENSE_EXPERIMENT_PROTOCOL_ZH.md)继续使用原路径，[进度台账](DEFENSE_PROGRESS_ZH.md)指定当前唯一 next_task。T01–T09 已完成、G0/G1 已通过。**T10-C 的 D-dev 开发设计选择已完成**：28 个两轮基础会话和两个共享来源的三轮诊断，均非人工 gold；正式长度和规模尚未确定。当前 T10-D 已开展多动作候选的真实开发对照，须完成运行与逐题评估，再处理真人 gold 和来源审核；T10 整体与 T11 正式指标仍进行中，T12–T18 未开始。访问动作已有工程验证，E00 只完成 observe 核对，E01–E07 仍未运行。

## 已完成

| 模块 | 状态与证据入口 |
|---|---|
| 四类成员推断攻击 | Direct RAG-MIA、S²-MIA、Masked MIA、IA 的本地实现和基线运行已存在；见 [项目 README](../README.md) 与 [攻击背景](baseline_rag_mia_attacks.md)。 |
| 离线 Query Bank | 最新为 `ag_news_queries_v2`：100 篇、7,632 查询，train 为 4,579 条；v2 正常审核 pending。已完成 Judge v3 对照使用 v1（5,956 条），保留原身份。详见[数据目录](DATA_CATALOG_ZH.md)。 |
| 早期防御阶段 | Rule-only MVP 与阶段二 IA 策略评测已有运行产物；见[防御路线图](DEFENSE_ROADMAP_ZH.md)和[阶段二评测](STAGE2_IA_POLICY_EVALUATION_ZH.md)。它们不是新版 Judge 在线接入的证明。 |
| 证据化 Progressive Judge v3 | Query/Session 检测、四类攻击模式、rubric 直接评分与二分类 logprob 评分均已实现；正式 train/validation/test 评分完成。 |
| 双分数融合与阈值 | 两种评分头都完成按文档分组的训练 OOF、L2 Logistic 冻结、1%/5% FPR 目标阈值及独立 validation/test 评估。完整方法和结果见 [v3 实验文档](PROGRESSIVE_JUDGE_V3_BINARY_LOGPROB_EXPERIMENT_ZH.md)。 |
| 防御阶段 T02 trace 适配 | 在线请求契约与 v3 trace → RiskResult 转换已完成，56 项相关/回归测试通过；见[进度台账](DEFENSE_PROGRESS_ZH.md)与[测试输出](../reports/defense_v1/T02/tests.txt)。后续 T05 已将适配器接入网关 observe 路径。 |
| 防御阶段 T03 冻结模型 scorer | 只读加载 logprob/rubric 冻结 JSON，校验身份及 `[x1, x2_observed]` 顺序并计算分数；9 项相关/回归测试通过，见[进度台账](DEFENSE_PROGRESS_ZH.md)与[测试输出](../reports/defense_v1/T03/tests.txt)。后续 T05 已在线核对分数，尚无真实回答级防御效果。 |
| 防御阶段 T04 Query-only 工作点 | 仅用正式 train 首两轮评分得到经验工作点及错误分支；15 项相关/回归测试通过。阈值和样本限制见[原始 JSON](../reports/defense_v1/T04/query_only_thresholds.json)与[进度台账](DEFENSE_PROGRESS_ZH.md)。已作为 T05 observe 的早期轮次路径。 |
| 防御阶段 T05 在线 observe | 冻结模型已作为可选路径接入网关，旧路径保持兼容；E00 旧 train 两条会话、10 次请求完成，完整上下文和 allow 均保持，同 trace 离线复算最大差为 0；101 项相关全回归通过。见[E00 原始 JSON](../data/defense_v1_runs/e00-observe-20261022-01/comparison.json)和[进度台账](DEFENSE_PROGRESS_ZH.md)。 |
| 防御阶段 T06 允许范围与回填 | FAISS 检索增加 doc_id 允许集、parent 排除与候选倍增回填；正式索引只读示例和修改前后哈希见[回填 JSON](../reports/defense_v1/T06/backfill_example.json)，33 项相关测试通过。后续 T07–T09 已用 fake 生成器验证动作和回放，真实生成效果尚未评估。 |
| 防御阶段 T07 单一动作执行器 | 新路径可选接入 allow、目标过滤回填、摘要、无上下文回答与拒答；fake 生成器检查实际 prompt 与失败回退，116 项相关全回归通过。见[动作工程 manifest](../reports/defense_v1/T07/action_manifest.json)。尚未有回答级防御效果评估。 |
| 防御阶段 T08 暴露账本 | 检索、摘要器输入、回答生成器交付与答复引用分层记录；同请求重试幂等，会话在回答或失败后提交。122 项相关全回归和[G1 fake 证据链](../reports/defense_v1/T08/g1_validation.json)通过；尚无真实模型防御效果结果。 |
| 防御阶段 T09 统一回放 | 运行身份、会话分片、resume、失败分母和受控生成输入 artifact 已实现；B0/B2/B3/B5 fake 运行 20/20 完成，134 项相关全回归通过，见[工程运行 JSON](../data/defense_v1_runs/t09-fake-20261022-05/metrics.json)。T09当时未跑真实后端；最新B0/B2小批见本页试跑报告。 |

最终 test 对比使用相同的 20 个文档、699 条 Query 与 Session 分数均可用的记录。rubric / 二分类 logprob 的 AUROC 为 `0.8795 / 0.8615`，F1 为 `0.8599 / 0.8630`，观测良性 FPR 均为 `0`。精确值和四类攻击召回见[实验索引](EXPERIMENT_INDEX_ZH.md)及[对比 JSON](../data/judge_score_comparison_v3_20261015/final_test_comparison.json)。

## 尚未完成

- 新版 Judge 与冻结融合模型已进入在线网关 observe 路径；改变证据或答案的动作已完成 fake 工程验证，已有24请求真实工程试跑，正式RAG效用/泄露评估仍未完成，不能据此证明总体成员信息泄露下降。
- 前两轮没有可用 Session 分数，当前主融合 test 指标只覆盖第 3 轮起的 699 条记录；Query-only train 工作点已进入 T05 在线路径，仍需独立效用/泄露评估。新正常会话若缩为两轮，只能检验 Query-only 阶段，因此 T10-C 必须明确三轮以上正常组的材料与覆盖。
- 基于新版识别器的B0/B2真实小批回放已有结果；正式正常效用、攻击成功率、动作比较及稳定延迟评估尚未完成。
- 正式动作比较还需 T12 补齐 live B1 适配，并明确当前 B5 的 Top-1 工程定位与正式目标定位的区别；T09 fake 回放不能证明真实目标定位准确。CLI 的预检查/冻结参数和正式评估模式也仍在后续任务中。
- 当前 test 已被查看。若后续根据这些结果修改模型或策略，须说明测试复用；需要严格的新最终结论时应准备新的保留数据。

## 下一开发入口

从[防御进度台账](DEFENSE_PROGRESS_ZH.md)的 `next_task=T10-D` 接续：**定位候选已完成初步试跑，先固定独立来源、库外与正常题样本验证定位和回退，随后补摘要检查及独立三轮。** [选择清单](../reports/defense_v1/T10/legacy_reuse_selection_20261104.json)绑定 v2 查询及 v2 划分；原始索引、成员身份和会话必须匹配。旧 validation/test 已查看，v2 继承其文章和攻击记录，不作为新的独立终测。既有 v1 Judge/E00 结果保持历史身份，具体执行边界见[数据复用规则](DEFENSE_DATA_REUSE_ZH.md)。

[版本与字段核验](../reports/defense_v1/T10/query_bank_version_audit_20261104.json)确认 v2 train 为 60 篇、4,579 条 accepted 查询，正常 1,304 条；有意图/难度字段，但无第二阶段标准答案、证据和可回答性字段。651 条正常查询的目标源不在旧索引，需要逐题判断其他来源是否支持。此前 v1 的 3,575 条盘点仍保留为历史依据。[4,579 条自动结构审计](../reports/defense_v1/T10/v2_train_reuse_audit_20261105_01/REUSE_REPORT_ZH.md)初次审计已完成：原文/索引身份无错误；当时发现1,304正常需补标，300 Masked需格式修订（130 条/26 篇泄漏），IA 206 条问答形式疑点待审。全量语义/gold/适配仍未完成；固定12题已做真实B0/B2比较。

### 现有第二阶段开发产物

- [T10-C 开发选择](../reports/defense_v1/T10/session_length_dev_cohort_20261102_01/selection_report.json)：28 个两轮基础会话与 2 个同源三轮诊断，共 30 会话、62 问；[开发导出](../reports/defense_v1/T10/dev_cohort_export_20261104_01/manifest.json)已接入写前来源检查，仍 pending、不可正式回放。
- [保守开发来源清单](../reports/defense_v1/T10/dev_source_inventory_20261104_01/manifest.json)216 篇（200 D-dev 候选目标、16 共享背景），不是逐篇审核或完整隔离证明。[事件预审处理](../reports/defense_v1/T10/EVENT_REVIEW_TRIAGE_20261104_ZH.md)覆盖 31 篇，三组能源关系只作敏感性分析；[E00 检索源审计](../reports/defense_v1/T10/e00_retrieved_source_audit_20261104.json)只排查全文/近重复，不排除事件/片段关联。
- [Masked 四篇试点](../reports/defense_v1/T10/masked_rule_pilot_20261104_01/AGENT_REVIEW_ZH.md)暴露标题选词风险；[显式选词试点](../reports/defense_v1/T10/masked_selected_pilot_20261104_01/AGENT_REVIEW_ZH.md)有 2 条新草稿、2 篇未选词。相关测试最近为 27 passed；仍待语义审核，无模型填空或防御效果测量。

已有候选、索引和审核记录继续用于补缺；不必为了联调先把四类攻击全量重做。先前[小批预算](../reports/defense_v1/T10/PILOT_SCOPE_AND_REVIEW_BUDGET_20261104_ZH.md)是新题需要时的备选方案，正式规模须根据复用覆盖、指标精度和审核资源另定。

T11 可继续不依赖真人 gold 的工程工作。正式接续仍为 **T10-D 数据复用/补缺与新候选 → T10-E 真实人员 gold → T11 正式指标 → T12/E01 动作比较**，再按 T13–T18 推进。旧 train 的 engineering_only 小运行不放行 G2，不替代 E01。模型预审不是 T10-E 或 E07 人评。2026-11-04 本次仅调整执行文档并完成字段盘点，未改变数据/模型、任务完成状态或正式实验门禁。

2026-11-05 [针对性预审接收与修订](../reports/defense_v1/T10/v2_reuse_review_integration_20261105_01/INTEGRATION_REPORT_ZH.md)完成：266单元文件结构核验通过；IA 6条本地修订、5条改写暂缓，115 reject/24 uncertain保留待裁决；Masked 60方案还原/无泄漏通过并补记错误修订理由及质量警告。[新待审攻击层](../data/defense_datasets/legacy_v2_reuse_overlay_20261105_01/manifest.json)含362请求（62 IA/300 Masked）及144暂缓IA，新身份、临时单查询会话、不可正式回放，无正常gold，不是完整数据放行。

2026-11-05 快速真实试跑已完成：[结果报告](../reports/defense_v1/T10/fast_live_pilot_20261105_01/FAST_PILOT_REPORT_ZH.md)、[run manifest](../data/defense_v1_runs/fast-v2-b0-b2-20261105-01/run_manifest.json)。12题×B0/B2共24/24成功，原BF16；4组正常回答逐字一致，agent按必要事实各判4/4正确；B2拒答6/8攻击，非攻击成功率下降。Masked原严格分数有格式混淆，保留原分数并另列5/5与2/5恢复诊断。单轮、2攻击来源、非真人gold、engineering_only，正式E01–E07未放行。下一优先：先补齐现有回答的格式/语义评分诊断，再复用同一小批比较过滤回填/摘要等动作；仅按结果暴露的缺口增加少量困难正常题和三轮来源，不先扩建全库。

2026-11-11：五日工程对照已开始输入预检，[26项摘要核验](../reports/defense_v1/T10/five_day_preflight_20261111_01.json)通过，汇总[18条已有案例索引](../reports/defense_v1/T10/five_day_existing_cohort_20261111_01.json)。此索引不是完整新题单；触发限制的正常题及独立三轮仍待准备，未新增模型实验。详见进度台账 L130–L131。

2026-11-11 补充：历史train正常评分与v2同ID同文本匹配294条，单查询得分均低于T04阈值；详见[离线筛查](../reports/defense_v1/T10/reusable_normal_scores_20261111.json)。该筛查不能证明实际动作或第三轮融合表现；v2新增正常题仍需筛查。

2026-11-11：新增正常题Query Judge筛查8/8完成，8条分数均低于当前单查询阈值；未观察在线动作和回答质量，见[运行摘要](../reports/defense_v1/T10/new_benign_screen_20261111_01/summary.json)及进度台账L133–L134。下一步准备单独标记的强制动作质量诊断。

2026-11-11：4条正常题进行B0与强制过滤真实模型配对，8/8完成。4次过滤均移除参考来源，回答均变为证据不足；Judge实际触发0/4，这是人为强制动作诊断，非自然误拦率。见[报告](../reports/defense_v1/T10/forced_normal_diagnostic_20261111_01/REPORT_ZH.md)。

2026-11-11：对同一排名压力小批补跑B2/B3，12/12完成。3条攻击B3都未交付检索原文，但各恢复1/5待填词；B2均拒答。仅工程诊断，详见[报告](../reports/defense_v1/T10/rank_stress_20261109_01/CONSERVATIVE_B2_B3_20261111_ZH.md)。

2026-11-11：新增连续词片段定位候选及真实模型小批[诊断](../reports/defense_v1/T10/rank_stress_20261109_01/LOCATOR_PILOT_20261111_ZH.md)，6/6完成；已看过的3个排名2–4目标均被排除，回答仍恢复5/15词。候选需独立来源验证，见台账 L140–L143。

2026-11-11：新增6篇来源的四方法工程对照24/24，Direct两题和Masked一题风险未触发，旧B5与新定位均放行；其余三题触发后均排除第一名目标。[运行报告](../reports/defense_v1/T10/LOCATOR_NEW_SOURCES_20261111_ZH.md)，下一步先核查未触发trace与题目质量。

2026-11-11：新来源对照中三条未触发请求经artifact核验，均在Judge初筛标记 `SKIP_NO_ATTACK_CUE` 并跳过细查，题面/来源核验和限制见[报告](../reports/defense_v1/T10/LOCATOR_NEW_SOURCES_20261111_ZH.md)。下一步先诊断初筛路径并评估候选修复的正常题代价。

2026-11-11：[查询线索候选试跑](../reports/defense_v1/T10/QUERY_CUE_PILOT_20261111_ZH.md)10/10完成，原Judge漏触发的3题因规则线索拒答，另3题过滤目标；4条已见正常题放行。规则静态覆盖与工程小样本有明确限制，需独立来源和困难正常题验证。

2026-11-11：[非成员与正常阅读对照](../reports/defense_v1/T10/CUE_UTILITY_NONMEMBER_20261111_ZH.md)24/24完成。B5_CUE对1道构造的公开引文阅读题拒答，B0与B5_LOCATED答Yes；另一道填空练习的参考来源在B0中未检索到。题目正常性待人工确认，仅为工程案例。
