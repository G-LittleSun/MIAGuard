# MIAGuard 防御开发与实验进度台账

更新时间：2026-11-20（北京时间）。这是本阶段**唯一任务状态与下一步入口**；项目总状态仍见 [PROJECT_STATUS_ZH.md](PROJECT_STATUS_ZH.md)，实验数字以原始 JSON 为准。

## 当前执行依据

- [当前版本总表](CURRENT_VERSIONS_ZH.md)：按用途选择最新数据、已有实验、模型/配置、开发文档及源码身份；不替代本台账的任务状态。
- [开发规格 v1.1](superpowers/specs/2026-10-22-defense-framework-design.md)
- [详细实施计划 v1.1：T01–T18](superpowers/plans/2026-10-22-defense-framework-implementation.md)
- [实验协议 v1.1](DEFENSE_EXPERIMENT_PROTOCOL_ZH.md)
- [研究建议](DEFENSE_DEVELOPMENT_EXPERIMENT_RECOMMENDATIONS_ZH.md)与[文献综述](ACCESS_CONTROL_DEFENSE_LITERATURE_REVIEW_ZH.md)：背景来源；执行细节以以上规格/计划/协议及修订记录为准。

**2026-11-17 当前恢复点为 T10-D。** 下一轮[主配对](../data/defense_v1_runs/next-goal-paired-20261117-01/run_manifest.json)188/188、[正常IA格式对照](../data/defense_v1_runs/next-goal-ia-style-20261117-01/run_manifest.json)16/16、[受控替代证据](../data/defense_v1_runs/next-goal-alternate-20261117-01/run_manifest.json)2/2和[真实机制消融](../data/defense_v1_runs/next-goal-ablation-20261117-01/run_manifest.json)32/32完成。正常对照中候选使V2原本正确的2题失去证据，按预设规则保留V2；相关回归93 passed。详见 L258–L269。真人gold、正式校准和终测仍待验收。

**当前阶段：T10-A 数据基础、T10-B 两轮模型预审及 T10-C 的 D-dev 会话设计选择已完成；T10 整体仍 IN_PROGRESS，数据复用验收、跨分区来源审计和人工 gold 尚未完成。T11 指标工程预研进行中；G0/G1 已通过。next_task=T10-D（IN_PROGRESS）：在新固定的开发集上研究风险识别漏检、正常题误触发和多轮早期交付，并补独立来源、人工审核和攻击校准。** [数据复用规则](DEFENSE_DATA_REUSE_ZH.md)与[选择清单](../reports/defense_v1/T10/legacy_reuse_selection_20261104.json)固定最新 v2 bank/split；v1 Judge/E00 保留原身份。v2 train 可用于条件满足后的 engineering_only 联调；字段盘点不是逐条验收，旧 validation/test 不作新终测。D-dev 选定 28 个两轮基础会话与两个共用来源的三轮诊断；正式长度/规模未冻结，正式防御效果实验未启动。

## 任务状态

| ID | 阶段 / 任务 | 依赖 | 状态 | 验收证据 / 下一步 |
|---|---|---|---|---|
| DOC-00 | 建立规格、计划、协议与台账 | 用户 2026-10-22 要求 | DONE | 本页链接的四份文档；入口及链接核验见 L002 |
| DOC-01 | 对齐当前进展与后续执行文档 v1.1 | 用户 2026-10-31 要求 | DONE | [文档审计](../reports/defense_v1/planning/document-audit-20261031.json)；12 份入口/执行文档同步，T10-C 为下一开发任务；见 L042–L044 |
| DOC-02 | 统一版本总表与入口 | 用户 2026-11-05 要求 | DONE | [版本总表](CURRENT_VERSIONS_ZH.md)、[身份快照](../reports/defense_v1/planning/current_versions_snapshot_20261105_01.json)、[核验](../reports/defense_v1/planning/current_versions_registry_validation_20261105.json)；仅完成版本导航和身份记录，next_task 仍为 T10-D |
| T01 | P0 环境与身份基线 | DOC-00 | DONE | [环境](../reports/defense_v1/T01/environment.json)、[测试输出](../reports/defense_v1/T01/baseline-tests.txt)、[哈希](../reports/defense_v1/T01/input_hashes.json)；next=T02 |
| T02 | P0 契约与 trace 适配 | T01 | DONE | [代码/测试哈希](../reports/defense_v1/T02/artifacts.json)、[测试输出](../reports/defense_v1/T02/tests.txt)；next=T03 |
| T03 | P0 冻结融合 | T02 | DONE | [代码/模型哈希](../reports/defense_v1/T03/artifacts.json)、[测试输出](../reports/defense_v1/T03/tests.txt)；next=T04 |
| T04 | P0 Query-only 与失败分支 | T03 | DONE | [train 工作点](../reports/defense_v1/T04/query_only_thresholds.json)、[测试](../reports/defense_v1/T04/tests.txt)；next=T05 |
| T05 | P0 observe 接入 | T04 | DONE | [E00 manifest](../data/defense_v1_runs/e00-observe-20261022-01/run_manifest.json)、[比较结果](../data/defense_v1_runs/e00-observe-20261022-01/comparison.json)、[测试](../reports/defense_v1/T05/full-regression.txt)；G0 通过 |
| T06 | P1 过滤与回填 | T05 | DONE | [测试](../reports/defense_v1/T06/tests.txt)、[正式索引回填示例](../reports/defense_v1/T06/backfill_example.json)；next=T07 |
| T07 | P1 单一动作执行器 | T06 | DONE | [动作工程 manifest](../reports/defense_v1/T07/action_manifest.json)、[116 项回归](../reports/defense_v1/T07/full-regression.txt)；next=T08 |
| T08 | P1 暴露与会话提交 | T07 | DONE | [G1 核验](../reports/defense_v1/T08/g1_validation.json)、[fake 证据链](../reports/defense_v1/T08/g1_fake_chain.json)、[122 项回归](../reports/defense_v1/T08/full-regression.txt) |
| T09 | P2 统一回放与恢复 | T08 | DONE | [fake run manifest](../data/defense_v1_runs/t09-fake-20261022-05/run_manifest.json)、[分母/覆盖 JSON](../data/defense_v1_runs/t09-fake-20261022-05/metrics.json)、[134 项回归](../reports/defense_v1/T09/full-regression.txt)；next=T10 |
| T10 | P2 数据与困难正常集 | T09 | IN_PROGRESS | [候选数据 manifest](../data/defense_datasets/defense_access_v1_candidate06/manifest.json)、[分区索引与重叠核验](../reports/defense_v1/T10/validation.json)、[第二轮预审核验](../reports/defense_v1/T10/review_validation_rev2_20261030.json)、[D-dev 开发试点](../data/defense_datasets/defense_access_v1_pilot_overlay_rev2_20261030/manifest.json)；已有 1750 正常/14400 攻击草稿仍未正式验收；先评估旧 train 复用再确定补建与审核范围，不可用于正式效果 |
| T11 | P2 指标与统计 | T10 | IN_PROGRESS | T10 人工 gold 尚未完成；[工程 fake 评估 v3](../reports/defense_v1/T11/fake_evaluation_v3.json)和 6 项指标单测已完成，正式阈值/区间/质量评估未完成 |
| T12 | P2 开发动作筛选 | T11 | NOT_STARTED | G2 未执行 |
| T13 | P3 Mirabel 基线 | T12 | NOT_STARTED | 尚未复现 |
| T14 | P3 动态策略 | T13 | NOT_STARTED | 参数尚未选择 |
| T15 | P3 自适应攻击 | T14 | NOT_STARTED | 攻击校准器尚未训练 |
| T16 | P4 实验冻结包 | T15 | NOT_STARTED | G3 未执行 |
| T17 | P4 独立终测 | T16 | NOT_STARTED | G4 未执行 |
| T18 | P5 泛化、人评、论文材料 | T17 | NOT_STARTED | 无新结果 |

状态枚举：NOT_STARTED、IN_PROGRESS、DONE、BLOCKED、INTERRUPTED、DEFERRED。BLOCKED 要写具体依赖、解决动作和继续条件；DEFERRED 要写移出范围原因与对结论影响；失败运行在事件日志标 FAILED，任务保留 IN_PROGRESS/BLOCKED/INTERRUPTED，不能勾选完成。

DONE 表示任务交付和验证完成，不表示实验一定得到正结果。每个任务只计算一次，复开时撤销 DONE 并记录原因，不用伪精确的百分比掩盖不同任务工作量。

### T10 当前子步骤与接续顺序

| 子步骤 | 状态 | 已有证据或下一交付 |
|---|---|---|
| T10-A 数据与隔离索引 | DONE | [candidate06 核验](../reports/defense_v1/T10/validation.json)；只证明数据工程基础 |
| T10-B 两轮预审及 overlay 同步 | DONE | [第二轮核验](../reports/defense_v1/T10/review_validation_rev2_20261030.json)、[overlay 验证](../data/defense_datasets/defense_access_v1_pilot_overlay_rev2_20261030/validation.json)；模型预审，不是人工 gold |
| T10-C 会话轮数与文档选择 | DONE（D-dev 设计） | [开发选择报告](../reports/defense_v1/T10/session_length_dev_cohort_20261102_01/selection_report.json)、[两次历史对照](../data/defense_v1_runs/t10c-context-focus-20261102-01/agent_diagnostic_summary.json)；未完成正式 gold 或跨来源泛化 |
| T10-D 复用覆盖、缺口补齐与新候选 | IN_PROGRESS | next_task；[两批多动作开发结果](../reports/defense_v1/T10/MULTI_ACTION_REPORT_20261117_ZH.md)完成；针对漏检和正常题损失继续开发；全量 gold、来源审计与独立终测仍待完成 |
| T10-E 人工 gold 与数据验收 | NOT_STARTED | 依赖 D；实际人员核对、排除未审项、正式 cohort 身份 |

A–E 为 T10 的内部步骤，完整操作、计划文件和验收写在[主实施计划](superpowers/plans/2026-10-22-defense-framework-implementation.md)。T11 合成/工程开发可继续；正式评估须等待 T10-E。之后按 T12 动作比较 → T13 基线 → T14 策略 → T15 自适应攻击 → T16 冻结 → T17 终测 → T18 泛化/人评顺序推进。

## 门禁状态

| 门禁 | 当前状态 | 证据要求 |
|---|---|---|
| G0 冻结分数与 observe | PASSED | T01–T05 结果、E00 身份及同 trace 零差异；见 L013 |
| G1 动作工程执行 | PASSED | T06–T08 标签隔离、fake 全请求证据链与会话行为；见 L019；不代表真实模型效果 |
| G2 数据与动作评估 | NOT_RUN | T10-E 正式 gold、T11 正式评估器、T12 安全/效用/成本及配对案例 |
| G3 终测冻结 | NOT_RUN | T16 全部身份、隔离审计与选择报告 |
| G4 终测有效 | NOT_RUN | T17 完整覆盖、分母、区间与无调参记录 |

## 实验运行登记

本轮主配对及补充运行已结束。E00–E07 是实验协议中的计划类型，不是已创建 run_id；下列开发诊断不属于正式防御效果实验：

| run_id | 实验/任务 | 数据分区与身份 | 状态 | 日志与产物 | 下一步 |
|---|---|---|---|---|---|
| next-goal-paired-20261117-01 | 四方法候选配对 | v2 train，47请求×4方法 | completed，188/188、无失败 | [manifest](../data/defense_v1_runs/next-goal-paired-20261117-01/run_manifest.json) / [审计](../reports/defense_v1/T10/next_goal_paired_audit_20261117.json) | 已完成agent正常题复核，继续补充对照 |
| next-goal-ia-style-20261117-01 | IA格式正常阅读对照 | v2 train，4请求×4方法 | completed，16/16、无失败 | [manifest](../data/defense_v1_runs/next-goal-ia-style-20261117-01/run_manifest.json) / [agent复核](../reports/defense_v1/T10/next_goal_ia_style_agent_review_20261117.json) | 正式正常数据与真人审核待完成 |
| next-goal-alternate-20261117-01 | 受控替代证据 | 原索引、模拟允许集合，2动作 | completed，2/2、无失败 | [manifest](../data/defense_v1_runs/next-goal-alternate-20261117-01/run_manifest.json) | 单例不代表在线定位准确性 |
| next-goal-ablation-20261117-01 | 真实机制消融 | v2 train，8请求×4方法 | completed，32/32、无失败 | [manifest](../data/defense_v1_runs/next-goal-ablation-20261117-01/run_manifest.json) / [汇总](../reports/defense_v1/T10/next_goal_ablation_summary_20261117.json) | 扩大不同来源并审核正常意图 |
| multi-action-candidates-20261117-01 | 七方法多动作配对 | v2 train 开发集，43 请求、七方法 | completed，301/301、0失败 | [manifest](../data/defense_v1_runs/multi-action-candidates-20261117-01/run_manifest.json) / [审计](../reports/defense_v1/T10/multi_action_candidates_audit_20261117.json) | 逐题审查质量与摘要内容 |
| multi-action-sources-20261117-01 | 四攻击来源扩展 | v2 train 开发集，19 请求、五方法 | completed，95/95、0失败 | [manifest](../data/defense_v1_runs/multi-action-sources-20261117-01/run_manifest.json) / [审计](../reports/defense_v1/T10/multi_action_sources_audit_20261117.json) | 补独立来源及真人审核 |
| fast-v2-b0-b2-20261105-01 | T10-D快速真实回答对照 | v2 train、12独立单轮、原BF16；engineering_only | completed/valid，24/24、无失败 | [run](../data/defense_v1_runs/fast-v2-b0-b2-20261105-01/run_manifest.json) / [报告](../reports/defense_v1/T10/fast_live_pilot_20261105_01/FAST_PILOT_REPORT_ZH.md) | 先修评分诊断，再复用本批比较过滤/摘要；非正式E01 |
| t10c-history-ablation-20261102-01 | 7 组有/无历史文本理解对照 | D-dev、本地 Q4、固定建议历史 | 完成；agent 判读 | [run](../data/defense_v1_runs/t10c-history-ablation-20261102-01/run_manifest.json) / [摘要](../data/defense_v1_runs/t10c-history-ablation-20261102-01/agent_diagnostic_summary.json) | 不外推、不作人工 gold |
| t10c-context-focus-20261102-01 | 两个焦点版本对照 | D-dev、同一来源组、本地 Q4 | 完成；agent 判读 | [run](../data/defense_v1_runs/t10c-context-focus-20261102-01/run_manifest.json) / [摘要](../data/defense_v1_runs/t10c-context-focus-20261102-01/agent_diagnostic_summary.json) | 同一无历史输入不算两个独立问题 |

## 每次推进的记录规则

1. 开始：将任务改 IN_PROGRESS，追加 BEGIN 事件，写本次子步骤、基线与目标；检查依赖门禁。
2. 推进：每个可验证子步骤完成、决策改变、测试失败、实验启动/停止或产生新产物时追加事件。记录北京时间、任务 ID、实际修改、命令/退出码、证据、限制、下一步。无需逐条记录普通文件阅读。
3. 结束：同步计划复选框、任务表与 next_task；未完成写恢复位置和命令，不能只写“继续开发”。启动后台运行要记录 PID/日志/run_id，不能仅写“正在跑”。
4. 功能或实验完成：同步 PROJECT_STATUS_ZH.md 和 EXPERIMENT_INDEX_ZH.md；新数据版本另同步 DATA_CATALOG_ZH.md。没有新数据不改数据身份表。
5. 规格变化：先追加 CHANGE 事件，写原因、影响的任务/参数/数据和是否使既有结果失效，再更新规格/计划/协议版本。避免修改已完成历史记录制造一直正确的假象。

统一事件字段：`event_id/time/task/type/changes/commands/results/artifacts/limitations/next`。日志追加不覆盖；纠错通过新事件指向旧编号。文件路径应可点击，命令输出放 reports 或 run/logs；单独记录预期与实测。若尚无测试，写“未运行”，不可写“通过”。

## 进度事件（按发生顺序追加）

### L001 — 2026-10-22 — DOC-00 — PLAN_CREATED

- 用户要求：按上一轮建议制定开发与详细实施文档，后续按文档开发并持续记录进度。
- 已完成：核对项目入口、建议稿、现有网关/trace/冻结融合/测试结构；建立四份执行文档，划分 18 个任务与 5 个门禁。
- 环境观察：解释器 `D:\ProgramData\Anaconda3\envs\MIAGuard\python.exe` 存在；`git rev-parse --show-toplevel` 退出 1，当前目录非 Git 仓库。没有初始化 Git，没有执行代码测试、安装依赖或启动实验。
- 关键决定：初版沿用冻结 logprob，保持旧路径兼容；先 observe 和真实动作，再新数据/策略/自适应攻击；原 test 不用于调参。
- 产物：本页“当前执行依据”四份文档；未生成任何新模型、阈值或数据。
- 下一步：完成入口链接与文档一致性核验后，后续开发从 T01 开始。

### L002 — 2026-10-22 — DOC-00 — DOCUMENT_VERIFICATION

- 核验范围：四份新文档的相对链接、T01–T18 唯一性与台账覆盖、G0–G4、Markdown 围栏、入口链接及无占位标记。
- 实际结果：使用项目 Python 执行文档结构检查，退出码 0；9 份文件、18 个唯一实施任务、82 个未勾选实施步骤一致，相对链接和代码围栏检查无错误。完整核验命令及结果见[文档审计 JSON](../reports/defense_v1/planning/document-audit-20261022.json)。
- 已同步：AGENTS.md、项目状态、实验索引、文档索引及原建议稿均指向本阶段执行入口；没有把新实验登记为已完成。任务 T01–T18 全部 NOT_STARTED，G0–G4 全部 NOT_RUN。
- 业务验证：未运行业务测试或 GPU 实验，本次不宣称功能通过。
- 下一步：T01 环境与身份基线。

### L003 — 2026-10-22 21:57（北京时间）— T01 — BEGIN

- 已检查进度台账与 T01 实施步骤，开始环境、既有回归和冻结身份基线核验。
- 本次使用 `D:\ProgramData\Anaconda3\envs\MIAGuard\python.exe`；计划输出 `reports/defense_v1/T01/environment.json`、`baseline-tests.txt`、`input_hashes.json`。
- 当前尚未运行测试或修改业务代码。下一步：检查解释器/依赖并执行 T01 指定的五组测试。

### L004 — 2026-10-22 — T01 — DONE

- `python --version` 退出 0，Python 3.10.20；`python -m pip check` 退出 0，无损坏依赖。
- `python -m pytest tests/test_progressive_judge.py tests/test_judge_score_frozen.py tests/test_two_stage_gateway.py tests/test_defense.py tests/test_session_store.py -q` 退出 0，74 passed，3 条来自 FAISS/SWIG 的 DeprecationWarning；完整输出见[baseline-tests.txt](../reports/defense_v1/T01/baseline-tests.txt)。
- 用同一环境的 Python hashlib 记录 12 个只读输入 SHA256，见[input_hashes.json](../reports/defense_v1/T01/input_hashes.json)。logprob 冻结模型哈希 `b24b81b88a4ce9579e81eb51cb4e0cc940972dc22499fce77ef80c60f587d188`、划分哈希 `c7f42950276f787bbc38862fad219b7c2436c8e562a9447c52388b0b809d8a93` 与数据目录一致。
- 限制：这仅是环境与旧回归基线，不是新防御已有效的证据。下一步 T02：先写 trace 适配测试并观察预期失败。

### L005 — 2026-10-22 21:59（北京时间）— T02 — BEGIN

- 依赖 T01 已完成。计划新增 `defense_contracts.py`、`online_judge_adapter.py` 和行为测试。
- 本轮先验证 logprob/rubric 分数不混、状态/证据/时延保留、在线 DTO 不含真值；测试确认因缺少能力失败后再写实现。

### L006 — 2026-10-22 — T02 — DONE

- 先运行 `python -m pytest tests/test_online_judge_adapter.py -q`：10 个测试按预期因两个新模块缺失而失败。随后新增在线 DTO 与 trace 适配器。
- 重新运行 `python -m pytest tests/test_online_judge_adapter.py tests/test_progressive_judge.py -q` 退出 0，56 passed；`compileall` 退出 0。原始测试输出见[tests.txt](../reports/defense_v1/T02/tests.txt)，代码与测试 SHA256 见[artifacts.json](../reports/defense_v1/T02/artifacts.json)。
- 适配保留整体 status、选定评分头分数、证据/疑似机制、时延和确定性 trace 哈希。非 ok 状态仅为兼容 RiskResult 带数值占位，后续融合器必须先检查 status。
- 限制：尚未接入在线网关，没有新防御效果数据。下一步 T03 冻结模型数值和身份核验。

### L007 — 2026-10-22 22:01（北京时间）— T03 — BEGIN

- 依赖 T02 已完成。读取正式冻结 JSON 的身份、特征顺序、系数与阈值；先写预期失败测试，随后实现只读 scorer。

### L008 — 2026-10-22 — T03 — DONE

- 先运行 `python -m pytest tests/test_frozen_risk_scorer.py -q`，6 个用例因 scorer 模块缺失按预期失败。新增只读模型加载和身份/特征/系数/阈值验证，使用稳定 sigmoid；未修改冻结模型。
- `python -m pytest tests/test_frozen_risk_scorer.py tests/test_judge_score_frozen.py -q` 退出 0，9 passed；与独立公式及既有评估器的 Brier 结果差异均≤1e-12。见[测试输出](../reports/defense_v1/T03/tests.txt)与[哈希](../reports/defense_v1/T03/artifacts.json)。
- 下一步 T04：仅用正式 train 校准 Query-only 启动轮次工作点，并明确错误分支。

### L009 — 2026-10-22 22:04（北京时间）— T04 — BEGIN

- 依赖 T03 已完成。以正式 train 的首两轮 Query 分数选 1%/5% 经验 FPR 工作点；先写失败测试，再实现分支与校准。
- 已核对正式训练评分表含 120 条首两轮正常查询（60 个文档）。独立文档数有限，置信区间不支持把经验工作点当部署保证。
- 下一步：写候选阈值、分文档统计及错误处理测试。

### L010 — 2026-10-22 22:07（北京时间）— T04 — DONE

- 先运行新测试，因缺少 `classify_source` 收到预期导入错误；实现 Query-only 训练校准器、正式 train 脚本及 `resolve_risk` 失败分支后，`python -m pytest tests/test_query_only_calibration.py tests/test_frozen_risk_scorer.py tests/test_judge_score_frozen.py -q` 退出 0，15 passed；`compileall` 退出 0。见[测试输出](../reports/defense_v1/T04/tests.txt)与[产物哈希](../reports/defense_v1/T04/artifacts.json)。
- 仅从已验证正式 train 评分记录生成[Query-only 工作点](../reports/defense_v1/T04/query_only_thresholds.json)：首两轮正常查询 120 条、60 个文档；四攻击 Query 数量 Direct/S²/Masked/IA 为 120/120/120/988。24 个候选（含不触发），x1 范围 0.0001233946–0.9998415638。1% 和 5% 经验 FPR cap 均选阈值 `0.006692850924284855`，按 `score >= threshold`；训练文档平衡良性 FPR 为 0，四攻击宏召回约 0.7771，其中 IA 约 0.2000。这些是检测工作点，不是防御后泄露结果。
- 两个工作点均标记 `empirical_only=true`：60 个正常文档零报警的文档级 Wilson 95% 上界仍约 0.0602，高于 1%/5% 上限。报告含文档 bootstrap 区间、来源身份及逐候选结果；原冻结模型 SHA256 仍为 `b24b81b88a4ce9579e81eb51cb4e0cc940972dc22499fce77ef80c60f587d188`。
- 失败分支：x1 有效、x2 缺失/失败时仍保留 Query-only；x1 失败为 error，observe 允许、enforce 返回 unavailable。下一步 T05：接入 observe 网关并验证不改变用户响应。

### L011 — 2026-10-22 22:08（北京时间）— T05 — BEGIN

- 依赖 T04 已完成。开始为旧 `TwoStageGateway` 加可选冻结 scorer 路径，保持默认构造与 GuardedRAG 输出兼容；先补 disabled、observe、早期 Query-only、后续融合和故障分支集成测试。
- 后续按计划建立仅 train 代表性会话的 `observe_spec.json` 和单独运行目录，再记录 live Judge 调用数/时延。当前 G0 未通过。

### L012 — 2026-10-22 22:13（北京时间）— T05 — COMPONENTS_READY / LIVE_START

- 已新增冻结 scorer 可选注入与 trace 保存回调、[observe 配置](../configs/defense/defense_v1_observe.yaml)、[train 会话规格](../reports/defense_v1/T05/observe_spec.json)和独立运行 CLI。新旧网关 28 项测试通过；曾出现变量名接线错误，已定位修正并重跑通过，输出见[T05 测试](../reports/defense_v1/T05/tests.txt)。
- 准备启动 `e00-observe-20261022-01`，仅旧正式 train 的 1 条正常和 1 条 Direct 会话；输出目录 `data/defense_v1_runs/e00-observe-20261022-01/`，日志 `reports/defense_v1/T05/live-run.log`。启动前 G0 仍 NOT_RUN；若中断须保留 manifest 并登记。

### L013 — 2026-10-22 22:20（北京时间）— T05 — DONE / G0_PASSED

- 运行 `e00-observe-20261022-01` 的[manifest](../data/defense_v1_runs/e00-observe-20261022-01/run_manifest.json)状态 `complete`。旧正式 train 2 条会话、10 次请求，保存 16 份 Judge trace；Query Judge 调用 10 次、Session Judge 调用 6 次；风险来源 Query-only 4 次、融合 6 次，状态 10 次 `ok`。见[原始比较 JSON](../data/defense_v1_runs/e00-observe-20261022-01/comparison.json)。
- 所有 10 次 applied_action 为 allow，10 次完整检索上下文均传给生成入口；同一保存 trace 的在线/离线分数最大绝对差 `0.0`。每请求网关延迟 p50 `29807.05 ms`、p95 `61301.71 ms`、最大 `61432.11 ms`；这只是两条开发会话的成本观测。
- [独立重跑对照](../reports/defense_v1/T05/live_rerun_comparison.json)与旧正式 train 相同 10 个 query_id 匹配，Query/Session 分数差均为 0、状态相同；这是本次重跑的描述值，正确性判据仍为同一保存 trace 的离线复算。
- `python -m pytest` 覆盖 T01–T05 相关测试退出 0，101 passed，3 条既有 SWIG 警告；见[全回归输出](../reports/defense_v1/T05/full-regression.txt)。G0 要求的契约、模型身份、observe 输入保持及复算一致均有证据，故 G0 标 PASSED。
- 限制：E00 为旧 train 小样本在线核对，未生成回答，也未测成员泄露下降或答案质量。下步 T06 证据允许范围、目标排除和回填。

### L014 — 2026-10-22 22:22（北京时间）— T06 — BEGIN

- 依赖 T05/G0 已通过。开始扩展 FAISS 检索调用，保留旧二参数签名；先测试空允许集、doc_id 白名单、parent 排除、排名回填和候选短缺。
- 正式向量索引/文档/manifest 的修改前 SHA256 已存[基线哈希](../reports/defense_v1/T06/index_hashes_before.json)。计划只读检索，不重建或覆盖索引。

### L015 — 2026-10-22 22:24（北京时间）— T06 — DONE

- 5 项新测试先因缺少过滤 API/模块而失败；实现只读候选倍增、doc_id 允许集、parent 排除、去重和短缺原因。`python -m pytest tests/test_evidence_access.py tests/test_defense.py tests/test_two_stage_gateway.py tests/test_defense_v1_observe.py -q` 退出 0，33 passed，3 条既有 SWIG 警告；见[测试输出](../reports/defense_v1/T06/tests.txt)及[代码/示例哈希](../reports/defense_v1/T06/artifacts.json)。
- 正式 FAISS 索引只读示例排除原第 1 名 parent 后，候选搜索 `4→8`、回填 1 次，返回原第 2–5 名共 4 条；检索前后 ID、回填和短缺原因见[backfill_example.json](../reports/defense_v1/T06/backfill_example.json)。索引、文档、manifest 的 SHA256 与[修改前记录](../reports/defense_v1/T06/index_hashes_before.json)相同。
- 旧 `search(query, top_k)` 仍兼容；新 `Evidence` 只携带 doc/parent/text/score，不携带离线成员标签。限制：现有正式语料目前无多片段 parent 结构，跨片段保护由合成测试验证，不能称正式数据已有跨片段效果。下一步 T07 单一实际动作执行器。

### L016 — 2026-10-22 22:26（北京时间）— T07 — BEGIN

- 依赖 T06 已完成。开发 `execute_action` 唯一证据变换点：allow、目标排除回填、摘要、无上下文回答、拒答及失败回退；先写实际送入生成器的 prompt 检查。
- 旧 GuardedRAG 默认路径保持，新增动作选择器才进入新执行器；执行记录须区分推荐动作、实际动作和交付 Evidence。

### L017 — 2026-10-22 22:29（北京时间）— T07 — DONE

- 新测试先因缺少 `execute_action` 导入失败；新增单一证据变换函数，并在 GuardedRAG 通过可选动作选择器接入。支持 allow、hide_target_refill、sanitized_context、no_context_answer、deny、unavailable；旧 `summarize_context` 仅在新路径显式映射。输出记录推荐/实际动作、交付 Evidence、parent 排除、回填 audit 与摘要模板版本。
- fake 生成器核对实际完整 prompt：allow 含原文，hide 后不含目标原文，sanitized 只含摘要且不二次摘要，no_context 保留同一问题但无检索文本，deny 跳过生成器；摘要超时回退 no_context。`python -m pytest` 覆盖 T01–T07 相关测试退出 0，116 passed，3 条既有 SWIG 警告，见[全回归](../reports/defense_v1/T07/full-regression.txt)。[动作工程 manifest](../reports/defense_v1/T07/action_manifest.json)记录模板版本和源码哈希。
- 限制：本任务是 fake 生成器/检索器集成验证，还没有统一回放或回答级质量、泄露结果；真实运行的模板版本仍须在后续 run manifest 绑定。下一步 T08 暴露账本与请求提交/幂等。

### L018 — 2026-10-22 22:30（北京时间）— T08 — BEGIN

- 依赖 T07 已完成。建立按 request_id+输入哈希的幂等账本，分开记录检索候选、生成器交付尝试与完成/失败回答；同 session 单请求顺序处理。
- 新服务提交点在回答完成或明确失败后，旧网关默认即时提交保持兼容；先写会话过期、重复请求和交付层次测试。G1 尚未执行。

### L019 — 2026-10-22 22:35（北京时间）— T08 — DONE / G1_PASSED

- 新测试先因缺少 `exposure_store` 模块失败。实现 `begin/record_retrieved/record_transform_attempt/record_attempt/complete/fail/history`、输入哈希幂等、1800 秒默认过期与单 session 待提交锁；新请求与重试单独计数。新服务在回答或明确失败后提交 Judge 会话轮次，旧网关默认行为不变。
- 暴露账本分开检索命中、摘要器收到的原文、回答生成器交付证据与显式答复引用；摘要交付标 transformed，但摘要器原文输入仍留痕。失败生成保留交付尝试，同 ID 重试不增加新请求数或 Judge 调用。`python -m pytest` 覆盖 T01–T08 相关测试退出 0，122 passed、3 条既有 SWIG 警告；见[回归输出](../reports/defense_v1/T08/full-regression.txt)。
- [G1 fake 全请求链](../reports/defense_v1/T08/g1_fake_chain.json)及[8 项门禁核对](../reports/defense_v1/T08/g1_validation.json)均通过：隐藏目标的检索层仍可见目标，但交付层仅有安全证据；摘要输入原文与变换后交付分离；生成失败保留尝试；重试只提交一次；Judge 接收控制前检索轨迹；在线链无评估真值字段。源码与产物 SHA256 见[artifacts.json](../reports/defense_v1/T08/artifacts.json)。故 G1 标 PASSED。
- 限制：G1 是 fake 组件与工程证据链验证，不含真实模型回答质量或成员泄露结果；答复引用由后续评估器显式给出，不由账本臆测。下一步 T09 统一回放与身份/恢复。

### L020 — 2026-10-22 22:36（北京时间）— T09 — BEGIN

- 依赖 T08/G1 已通过。统一回放器按 method/session/seed 分片，运行身份覆盖输入、模型/阈值/Prompt/策略/代码；resume 仅接受完全同一身份和完整分片。
- 先写中断续跑、身份拒绝、失败分母、标签只在离线评分层出现、不同方法会话隔离的测试，再实现 CLI 和 B0/B2/B3/B5 fake smoke。

### L021 — 2026-10-22 — T09 — DESIGN_DECISION

- 统一服务只接收 `OnlineRequest`；四攻击评分在请求完成后读取独立 `labels.jsonl`。Masked 以统一服务回答中的 JSON `answers` 按既有标准化逐词比较；不能再额外调用旧 `_recover_masks` 绕过服务。T10 构建 Masked 在线问题时须显式要求同一 JSON 格式，并在开发集核验解析成功率。这是输入协议选择，尚无真实效果结果。
- 运行分片以 `method/seed/session` 为单位，未完成分片恢复时整会话重跑；完成分片与受控生成输入 artifact 校验哈希后复用。`status` 表执行结束，`outcome` 表结果可比性，`analysis_role=engineering_only` 的 fake 结果不作论文效果证据。

### L022 — 2026-10-22 22:48（北京时间）— T09 — DONE

- 新测试先因缺少 `defense_benchmark` 模块失败。完成原子 manifest、身份哈希、method/session/seed 分片、完成分片复用、异常中断后整会话重跑、缺失 artifact 拒绝完成运行 resume、请求/离线标签物理分离。失败攻击目标仍输出 null 分数与原因，失败/跳过正常请求仍留在正常分母。真实后端工厂绑定冻结模型、阈值、索引、Prompt/模式库和代码身份；目前只在 fake 依赖下验证其 B0/B2/B3/B5 动作接线，尚未启动真实防御运行。
- 最终工程 smoke `t09-fake-20261022-05` 的[manifest](../data/defense_v1_runs/t09-fake-20261022-05/run_manifest.json)为 `completed`，`analysis_role=engineering_only`；[metrics](../data/defense_v1_runs/t09-fake-20261022-05/metrics.json)为 `expected=20, completed=20, failed=0, skipped=0, coverage=1.0`。B0/B2/B3/B5 各 5 次，分别执行 allow/deny/no_context_answer/hide_target_refill；四攻击类型各 4 条离线分数，20 个实际生成输入 artifact 均可追溯，在线 events 无评估标签。旧 fake run `-01` 至 `-04` 均完成但由后续代码版本替代，保留历史产物，不合并比较。
- `python -m pytest` 覆盖 T01–T09 相关测试退出 0，134 passed，3 条既有 SWIG 警告；见[全回归](../reports/defense_v1/T09/full-regression.txt)及[产物哈希](../reports/defense_v1/T09/artifacts.json)。限制：仅合成 fake 请求与 1 个合成目标，`outcome=valid` 仅表示该工程运行无执行缺失，不表示防御有效。下一步 T10 新数据契约与独立划分。

### L023 — 2026-10-22 — T10 — BEGIN / 数据身份决策

- 已核对原正式索引 1,000 篇 member、原 `target_nonmember` 1,000 篇；四攻击上游运行的 Direct/S² 各覆盖原 2,000 个目标，因此不能把它们随机重分配后称为新独立终测。原计划四分区合计每类 1,800 篇，原索引与旧非成员池也不足。
- 新数据候选改从同一冻结 AG News 120,000 篇 processed corpus 选：member 候选只取原 `target_member` 中未进入旧 1,000 篇索引的文章，新索引须单独构建；nonmember 候选从 source_index>=9,000 且不进入新索引的 processed corpus 选。这里的 0/1 是**新 RAG 索引成员身份**，不能解释为来源 teacher 训练集成员身份；source_partition、source_index 和索引身份分开记录。先做所有历史目标及 Prompt 示例重叠审计，再冻结候选与实际规模。新索引建立、人工复核、独立性审计完成前，T10 保持 IN_PROGRESS，数据不得作正式效果结论。

### L024 — 2026-10-22 23:04（北京时间）— T10 — 工程候选已核验 / IN_PROGRESS

- 新测试先因缺少 `defense_dataset` 模块失败，随后 8 项单测通过：跨分区 parent/近重复组、空答案/缺证据/不可回答矛盾、成员标签混淆、跨分区证据、虚报人工复核等均拒绝。构建器按规范化词三元组 SimHash64、Hamming≤3 分组，SHA256 种子排序选目标；[v05 manifest](../data/defense_datasets/defense_access_v1_candidate05/manifest.json)记录源文件/代码/产物哈希、算法与阈值。
- 候选 v05：D-dev/A-cal/V/T 每类目标 `100/500/200/1000`，共 3,600；900 篇共享背景。四个分区 FAISS 索引各 1,000 篇，仅本分区目标与共享背景；当时的独立性核验断言其他分区目标不入本分区索引、旧目标 ID/全文近重复/整篇 Prompt 包含关系均为 0。31 份历史目标文件、32 份模式文件纳入哈希审计；片段级/语义级 Prompt 重叠尚未人工排除。
- 请求与离线标签/答案分文件。生成七类正常 1,750 条、四类攻击 14,400 条**未复核模板草稿**，所有 `review_status=pending`、`reviewed_by=null`；抽样发现正常会话重复提问、原文 HTML 痕迹、提取式答案和攻击语义不足，不能宣称正常质量或攻击有效性。`candidate01`–`candidate04` 是无效果运行的工程迭代，v05 当时取代；T10 不勾选完成。

### L025 — 2026-10-22 — T10 — 候选 v06 / IN_PROGRESS

- 增加自动查询五轮非完全重复与编码 HTML 清理，新增单测先失败后修复；T10 9 项单测通过。v06 [候选 manifest](../data/defense_datasets/defense_access_v1_candidate06/manifest.json)与四个分区索引已重建，[核验 JSON](../reports/defense_v1/T10/validation.json)通过：3,600 目标、900 共享背景、1,750 正常及 14,400 攻击草稿，在线 ID 为不含 doc_id 的不透明哈希；目标隔离和已定义的历史重叠审计仍为 0。v05 及更早候选由 v06 取代，留档不合并。
- 多轮正常问题虽然文字已不同，仍以相同文章和提取式答案为主；跨文档配对、Masked/IA 攻击问题语义与参考答案需人工评判。`formal_effect_eligible=false`，T10 维持 IN_PROGRESS。下一步制作人工复核包与可执行审核规则，再考虑 T11 指标工程。

### L026 — 2026-10-22 — T10 — 人工复核试点包已准备 / IN_PROGRESS

- 从 v06 的 D-dev 生成[试点包 manifest](../reports/defense_v1/T10/review_packet_manifest.json)、[70 条正常问题](../reports/defense_v1/T10/review_packet_d_dev_normal.jsonl)、[16 条攻击问题](../reports/defense_v1/T10/review_packet_d_dev_attack.jsonl)及[复核规则](../reports/defense_v1/T10/REVIEW_GUIDE_ZH.md)。攻击包不包含 membership 标签或可直接反推标签的目标 doc_id；复核者须填写真实身份、决定与修订，原包保持只读。当前仍为 `pending`，无人工复核结果。已向用户询问复核安排，等待答复期间继续独立的指标工程。

### L027 — 2026-10-22 — T11 — 指标工程预研 / IN_PROGRESS

- `defense_metrics.py` 与 5 项单测覆盖原始/翻转诊断 AUC、单类别 null、失败/拒答正常分母、无事实回答的 faithfulness null、缺 gold 的 Recall@k null、按目标簇成对重采样；先写测试并观察模块缺失/入口缺失失败。`evaluate_run` 当前只接受 `engineering_only`，拒绝正式口径，故不会把 T09 fake 数据包装成效果结论。[fake_evaluation.json](../reports/defense_v1/T11/fake_evaluation.json)按 B0/B2/B3/B5 输出显式分母，四攻击均仅 1 个 member 目标、AUC=`null`、`reason=single_class`。A-cal 固定阈值、正式 gold/faithfulness、区间汇总与完整成本拆分未完成；依赖 T10 人工复核结果，T11 不勾选完成。

### L028 — 2026-10-22 — T11 — A-cal 阈值算法预研 / IN_PROGRESS

- 新增先失败后通过的第 6 项指标测试：仅用 A-cal 两类独立目标确定攻击分数方向和满足经验 FPR cap 的固定阈值；测试集只应用冻结方向/阈值，绝不重新选择。单目标多 seed 先平均，再计算原始 AUC；测试同时覆盖反向分数。当前是合成手算 fixture，没有真实 A-cal 校准或 test 结果。[fake 评估 v2](../reports/defense_v1/T11/fake_evaluation_v2.json)增加评估器源码 SHA256；旧 v1 保留工程历史。正式 1% FPR 需要置信区间与攻击失败敏感性分析，尚未实现。

### L029 — 2026-10-22 — T10/T11 — 本轮核验与恢复入口

- 指标单测补充混合预算拒绝，避免把 1/5/10 次查询预算的目标分数混为一个 AUC；`pytest tests/test_defense_metrics.py tests/test_defense_dataset.py -q` 为 15 passed。[fake 评估 v3](../reports/defense_v1/T11/fake_evaluation_v3.json)绑定此版评估器源码哈希。T10 数据/四索引身份仍以[候选核验](../reports/defense_v1/T10/validation.json)为准；人工复核仍 pending，正式效果无新增结果。
- 最终 `python -m pytest -q` 退出 0，为 **476 passed、1 skipped、3 条既有 SWIG 警告**；见[全量回归输出](../reports/defense_v1/T11/full-regression-verified.txt)。其后重跑 `python scripts/verify_defense_v1_dataset.py` 退出 0，候选仍为 3,600 目标、1,750 正常/14,400 攻击草稿、四分区索引各 1,000。测试通过不改变 `formal_effect_eligible=false`。
- 恢复位置：先阅读[人工复核指南](../reports/defense_v1/T10/REVIEW_GUIDE_ZH.md)与[试点包 manifest](../reports/defense_v1/T10/review_packet_manifest.json)，获取真实复核结果后另建修订数据版本，不覆盖 v06。独立工程可运行 `python -m pytest tests/test_defense_dataset.py tests/test_defense_metrics.py -q`、`python scripts/verify_defense_v1_dataset.py`；T11 正式评估在 T10 gold 冻结前保持关闭。T12/E01 仍未开始。

### L030 — 2026-10-23 16:40（北京时间）— T10 — BEGIN / REVIEW_WORKFLOW_CHANGE

- 用户决定使用其自行安排的 DeepSeek V4.1 Flash agent 代做首轮审核，并要求明确输入、判定、结果格式与保存位置；本轮只准备交接材料，不虚报已有审核结果。
- 复核现有 D-dev 试点包，确认 70 条正常问题、16 条攻击问题均为 `pending`；七类正常各 10 条、四类攻击各 4 条。发现跨文档题包内只带第一篇 `source_text`，第二篇需从候选文档补齐；Masked 样例存在遮蔽词在同题其他位置出现的明显风险。
- 设计变化：新增不含成员标签的补充证据和独立 agent 输出契约。agent 输出标记为模型预审，不写入原包的 `reviewed_by` 或伪称人工复核；T10 正式 gold 放行标准与协议如需改为纯模型审核，须在使用结果前另记 CHANGE 并修订协议。
- 实际读取命令：`Get-Content docs/PROJECT_STATUS_ZH.md`、`docs/DATA_CATALOG_ZH.md`、`docs/EXPERIMENT_INDEX_ZH.md`、`docs/README.md`、`docs/DEFENSE_PROGRESS_ZH.md`、现有 `REVIEW_GUIDE_ZH.md` 与 `review_packet_manifest.json`；使用项目 Python 读取两份 JSONL、`documents.jsonl` 检查字段、计数和证据可得性。退出码均为 0；15 篇所需原文均在 D-dev。
- 下一步：生成去标签证据文件、agent 交接说明和空结果目录说明，核验输入 SHA256 与行数；保持 T10 `IN_PROGRESS`、下一开发任务仍为 T10 审核与修订。

### L031 — 2026-10-29（北京时间）— T10 — RESUME / AGENT_REVIEW_HANDOFF_READY

- 恢复原因：上次回复因远程上下文压缩报错中断；一段用于补充哈希的补丁未执行成功。本次先读取实际文件并修正交接单中的 `accept` 规则，未把中断或未产生的审核输出记为完成。
- 实际产物：[外部 agent 交接单](../reports/defense_v1/T10/AGENT_REVIEW_HANDOFF_ZH.md)、[70 条正常题的去标签原文补充包](../reports/defense_v1/T10/review_packet_d_dev_normal_evidence.jsonl)、[外部结果目录说明](../reports/defense_v1/T10/external_review/README.md)；原[正常试点包](../reports/defense_v1/T10/review_packet_d_dev_normal.jsonl)和[攻击试点包](../reports/defense_v1/T10/review_packet_d_dev_attack.jsonl)保持只读。文档入口和项目状态已链接交接单。
- 实际命令与结果：`Get-Content` 核对交接单、原指南、台账及 manifest；项目 `python -` 脚本生成并检查去标签证据文件，退出码 0；本次再以项目 `python -` 脚本逐个计算四份输入 SHA256，核对 manifest 与交接单、70/70/16 行、14 个正常会话、ID/证据对应关系、文档链接及结果目录，退出码 0，输出 `PASS input hashes=4; normal=70; evidence=70; attack=16; sessions=14; links=valid; external review results=0`。补充证据 SHA256 为 `ef5948da23e80f742a442397bbe25f88bf40651d361fe4f39f830ea79184511d`。
- 状态与限制：这只是审核交接材料，尚无 DeepSeek agent 实际输出，更无真人复核。T10 及计划中的七类正常/四类攻击复核步骤仍为 `IN_PROGRESS`/未勾选；`candidate06` 的 `formal_effect_eligible=false`、G2 `NOT_RUN`、T11 正式指标未完成。模型预审可指导 D-dev 查询修订，不能直接称为人工 gold 或防御有效性证据。
- 下一步：用户安排 agent 按交接单审 86 条并保存 `reports/defense_v1/T10/external_review/<run_id>/`；收到后先核对输入身份、完整性与字段，再抽查语义，另建候选版本修订。若拟以纯模型审核替代协议要求的人工复核，须先记录 CHANGE 并修订实验协议与论文口径。

### L032 — 2026-10-29（北京时间）— T10 — BEGIN / REVIEW_CONTEXT_CLARIFICATION

- 用户指出 WorkBuddy 新会话不了解 MIAGuard，原提示词可能只说明操作而未解释研究目标；开始补充项目背景、审核目的与边界，保持既有 86 条输入及输出契约不变。
- 已读取 `docs/PROJECT_STATUS_ZH.md`、`docs/DATA_CATALOG_ZH.md`、`docs/EXPERIMENT_INDEX_ZH.md`、`docs/README.md`、本台账、开发规格、实验协议与现有交接单；读取命令为 `Get-Content -LiteralPath <路径> -TotalCount <行数>`，退出码均为 0。确认成员性指新 RAG 索引成员，检测指标不等于防御效果，T10 仍为未审候选。
- 下一步：在交接单增加简明项目导读和项目理解自检，给 WorkBuddy 提供完整的新会话提示词；核对链接和输入身份后追加完成事件。

### L033 — 2026-10-29（北京时间）— T10 — REVIEW_CONTEXT_HANDOFF_UPDATED

- [外部 agent 交接单](../reports/defense_v1/T10/AGENT_REVIEW_HANDOFF_ZH.md)新增第 0 节，说明本研究的 RAG 索引成员定义、四类攻击、风险识别与访问控制防御的关系、正常问答质量目标，以及本轮 D-dev 试点只做问题和 gold 质量预审；要求 agent 先读项目状态/规格/协议相关节，并在 `review_summary.md` 写 4–6 句项目理解。交接单末尾的可复制指令同步指向新导读。
- 实际命令与结果：`Get-Content -LiteralPath` 读取规格、协议及交接单，退出码均为 0；项目 `python -` 核对新增背景段落、相对链接、原正常/攻击包 SHA256、70 条补充证据及结果目录，退出码 0，输出 `PASS context, links, original input hashes, 70 evidence rows; review results still absent`。没有运行代码测试或防御实验。
- 限制与状态：本次只是改进审核说明，未改变数据、试点包、评审 schema、T10 未勾选步骤或门禁。T10 保持 `IN_PROGRESS`；外部 agent 尚未提交结果，人工复核仍未完成，`candidate06` 仍不可用于正式效果。
- 下一步：用户在 WorkBuddy 新会话中选定实际 DeepSeek 模型并交给 agent 完成 86 条预审；收到运行目录后先验证，再在 D-dev 修订查询。

### L034 — 2026-10-30（北京时间）— T10 — BEGIN / AGENT_REVIEW_RECEIVED

- 用户提供 DeepSeek agent 已完成 86 条 D-dev 试点预审的消息，输出目录为 `reports/defense_v1/T10/external_review/pilot_deepseek_20261029_01/`。本次目标是独立核验四份输出与原包、抽查语义后修订候选生成方案；不把外部报告直接当成正式 gold。
- 开始时读取项目状态、数据目录、实验索引、文档索引、T10 台账、开发规格/计划/实验协议及外部审核文件。T09 依赖已完成；T10 仍 `IN_PROGRESS`，G2 未运行。
- 下一步：持久化独立结构核验与语义抽查，逐项判断建议是否适用于现有生成器，再决定新候选版本修改。

### L035 — 2026-10-30（北京时间）— T10 — MODEL_REVIEW_VALIDATED / IN_PROGRESS

- 独立核对外部[审核 manifest](../reports/defense_v1/T10/external_review/pilot_deepseek_20261029_01/review_manifest.json)与两份 JSONL；项目 Python 从原试点包及补充证据重算 4 份输入 SHA256、prompt SHA256，检查 70/16 行、ID 顺序、字段契约、证据 ID 和判定分布。退出码 0，得到正常 rewrite 60/reject 10、攻击 accept 10/rewrite 6、0 个结构错误；[核验 JSON](../reports/defense_v1/T10/review_validation_20261030.json)保存输入/输出哈希、范围与限制。
- 源码和样本抽查确认：生成器固定句尾导致五轮重复、偏移 71 导致跨文档随机配对、固定第四词可能产生 Masked 泄漏、IA 把原文首句塞入问题。首轮模型改写仍可能过度推断截断文本；模型 ID 是运行环境自报标识，非供应商完整快照证明。结构通过不能等同事实正确或真人复核。[逐项决策](../reports/defense_v1/T10/REVIEW_TRIAGE_20261030_ZH.md)记录采纳与保留意见。
- T10 仍 IN_PROGRESS；修订仅用 D-dev，未读取 V/T 效果、未运行防御实验。下一步建立新的修订试点，保留原始审核与 candidate06 不动。

### L036 — 2026-10-30（北京时间）— T10 — REVISED_PILOT_CREATED / IN_PROGRESS

- 从首轮审核生成[第二轮试点清单](../reports/defense_v1/T10/pilot_revision_20261030_01/revision_manifest.json)：70 正常（60 条首轮改写、10 条重新配对的跨文档草稿）及 16 攻击（10 保留、5 首轮改写、1 条 Masked 由 Codex 再改）；[两组跨文档起草依据](../reports/defense_v1/T10/cross_document_revision_suggestions_20261030.json)与[第二轮审核指南](../reports/defense_v1/T10/pilot_revision_20261030_01/REVIEW_GUIDE_ZH.md)已保存。新配对为 Bigley 同一事件、油价影响家庭与股市；原始请求和审核输出未覆盖。
- 首次生成命令使用系统 `python -`（3.9.13）遇到 `zip(..., strict=True)` 不兼容，退出码 1，输出目录尚未创建。改用项目解释器 `& 'D:\ProgramData\Anaconda3\envs\MIAGuard\python.exe' -`（3.10.20）运行生成脚本，退出码 0，输出 `normal 70 attack 16 cross_doc 10`。一次后续临时核查脚本有括号笔误，退出码 1；修正后重跑退出码 0。
- 本地核查 `& 'D:\ProgramData\Anaconda3\envs\MIAGuard\python.exe' -` 退出码 0：70/70/16 行、七类正常各 10、10 条跨文档都有两篇证据、ID 与原包逐条对应、无成员标签字段、所有状态 pending、文件哈希和文档链接一致。进一步按[Masked 实现](../src/miaguard/masked_mia.py)核查发现首轮建议用数字 64 作缺词，与其“避开数字”的选词契约冲突；在**新试点**改成唯一字母词 sparkling，保留首轮原始建议。四条 Masked 新缺词均为唯一字母词；原离线 gold 有两条已过期（Clement→sparkling、coaches→Belichick）。
- 限制：新试点的答案均为模型建议；跨文档原离线证据与 Masked 原离线答案未同步，manifest 明确 `replay_eligible=false`、`formal_effect_eligible=false`。T10 计划中的正式复核复选框不勾选，T11 正式评估与 G2 不启动。下一步对修订试点做第二轮独立审核，再修改全量生成器并新建完整候选版本。

### L037 — 2026-10-30（北京时间）— T10 — REVISION_VERIFIED / DOCUMENTS_SYNCED

- 项目解释器运行 `& 'D:\ProgramData\Anaconda3\envs\MIAGuard\python.exe' -` 完成最终结构与规则核验，退出码 0；[修订验证 JSON](../reports/defense_v1/T10/pilot_revision_20261030_01/validation.json)为 `status=passed`、0 错误、0 失效相对链接。核对原包/审核/修订文件哈希，70 正常、16 攻击、七类各 10、跨文档 10 条各两证据、四 Masked 缺词均为正文唯一字母词、IA 不再直接包含整篇目标原文；所有新题仍 pending、禁止回放与正式效果。
- 已同步[项目状态](PROJECT_STATUS_ZH.md)、[数据目录](DATA_CATALOG_ZH.md)、[实验索引](EXPERIMENT_INDEX_ZH.md)、[文档索引](README.md)和[实施计划 T10 未勾选项](superpowers/plans/2026-10-22-defense-framework-implementation.md)。未改业务代码和冻结模型，故本次没有运行代码回归、真实 RAG 或防御效果实验；上述核验不证明问答质量或攻击效果。
- 恢复入口：[第二轮审核指南](../reports/defense_v1/T10/pilot_revision_20261030_01/REVIEW_GUIDE_ZH.md)及[修订清单](../reports/defense_v1/T10/pilot_revision_20261030_01/revision_manifest.json)。next_task=T10 第二轮审核修订试点；收到结果后核对并修复剩余语义问题，再重做全量生成器与离线 gold。T10 保持 IN_PROGRESS，T11 仅指标预研，G2 NOT_RUN。

### L038 — 2026-10-30（北京时间）— T10 — BEGIN / SECOND_MODEL_REVIEW_RECEIVED

- 用户提供第二轮 DeepSeek V4.1 Flash 预审目录 `reports/defense_v1/T10/external_review/pilot_deepseek_rev2_20261030_01/`，报告 70 条正常题中 61 accept / 9 rewrite，16 条攻击题中 15 accept / 1 rewrite。开始独立核对输入哈希、输出契约和原文语义，再处理剩余问题。
- 本次已按项目入口读取 `docs/PROJECT_STATUS_ZH.md`、`docs/DATA_CATALOG_ZH.md`、`docs/EXPERIMENT_INDEX_ZH.md`、`docs/README.md` 和本台账；`Get-Content docs/DEFENSE_PROGRESS_ZH.md -Tail 75` 退出码 0，确认上一事件为 L037。模型预审仍不替代人工 gold，T10 保持 `IN_PROGRESS`。

### L039 — 2026-10-30（北京时间）— T10 — SECOND_REVIEW_VALIDATED / DESIGN_CHANGE_PENDING

- 项目解释器以 `python -` 重算第二轮审核四份输入 SHA256、指南和交接单哈希，检查 70/16 行、ID/顺序/字段契约及证据范围，退出码 0；[核验 JSON](../reports/defense_v1/T10/review_validation_rev2_20261030.json)为 `contract_passed_with_semantic_blockers`，正常 61 accept/9 rewrite、攻击 15 accept/1 rewrite。发现 3 条 Bigley 跨文档改写答案只列一篇证据，具体 ID 见[第二轮决策](../reports/defense_v1/T10/REVIEW_TRIAGE_REV2_20261030_ZH.md)。这些错误未被外部摘要的结构检查捕获。
- 抽查全部 9 条正常改写及其原文、全部 10 条跨文档证据，并检查部分 accept 的整段会话；Mystics 和 Calpers 的五轮仍有语义重复。读候选文档的长度分布：D-dev 成员 100 篇中位 234 字符、句末标点中位 1，V/T 分别约 228/229 字符。**设计方向改变：**先在 D-dev 验证短片段至多 2–3 轮、扩大文档覆盖；再按可用材料决定 `multi_turn_reading` 的轮数与规模，并在查看新 T 效果前更新实验协议。当前只记录方案，尚未完成生成器或正式样本量变更。

### L040 — 2026-10-30（北京时间）— T10 — ENGINEERING_OVERLAY_CREATED / IN_PROGRESS

- 新增 `scripts/build_t10_review_overlay.py`，从 `candidate06` 与第二轮审核生成[独立 D-dev 开发试点](../data/defense_datasets/defense_access_v1_pilot_overlay_rev2_20261030/manifest.json)：70 正常在线请求/70 离线任务、16 攻击在线请求/16 离线标签。三条 Bigley 题补齐双篇证据；两条 Masked 的离线答案同步为 `sparkling`、`Belichick`。原 candidate06、两轮审核文件和索引不变，全部任务仍 `pending`、`reviewed_by=null`、`formal_effect_eligible=false`。
- 首次执行 `& 'D:\ProgramData\Anaconda3\envs\MIAGuard\python.exe' scripts/build_t10_review_overlay.py --output data/defense_datasets/defense_access_v1_pilot_overlay_rev2_20261030` 退出码 1：校验误将提示模板和正文中的两个 `[MASK]` 都算作正文遮蔽；修正为只检查 JSON 契约后面的正文，并用词边界检查缺词泄漏。重跑退出码 0。后续对生成脚本补充候选哈希复核；现有输出另行独立核验，未冒称脚本在补充检查后重新生成。
- 独立 `python -` 核验生成[validation.json](../data/defense_datasets/defense_access_v1_pilot_overlay_rev2_20261030/validation.json)，退出码 0、`status=passed`：四文件行数/哈希、ID 对齐、在线无成员标签、跨文档双证据、Masked 唯一遮蔽、正常任务 `validate_dataset` 均通过。`python -m py_compile scripts/build_t10_review_overlay.py` 退出 0，`python -m pytest tests/test_defense_dataset.py -q` 为 9 passed。此验证仅属数据工程，不是问答质量或防御效果。
- 下一步：按[第二轮决策](../reports/defense_v1/T10/REVIEW_TRIAGE_REV2_20261030_ZH.md)做 D-dev 轮数/文档选择试点，完成后更新协议和全量生成器；真人 gold、G2、E01–E07 均未放行。

### L041 — 2026-10-30（北京时间）— T10 — DOCUMENTS_SYNCED / NEXT_TASK_SET

- 已同步[项目状态](PROJECT_STATUS_ZH.md)、[数据目录](DATA_CATALOG_ZH.md)、[实验索引](EXPERIMENT_INDEX_ZH.md)、[文档索引](README.md)及[实施计划 T10 未勾选项](superpowers/plans/2026-10-22-defense-framework-implementation.md)；第二轮审核来源、三条证据遗漏、开发 overlay 身份与剩余质量问题均有入口。T10 仍 `IN_PROGRESS`；计划复选框未误勾，T11 正式评估、G2、E01–E07 仍未运行。
- 后续尝试用 `Remove-Item -LiteralPath <已校验的开发 overlay 路径> -Recurse -Force` 清除一次生成目录以重跑带新增源哈希检查的脚本，自动执行审查拒绝该删除，**没有文件被删**；改为保留已生成产物并用独立 `python -` 全量核验。新增源哈希检查在当前 overlay 建成后加入构建脚本，未声称对已有目录完成重新构建。`git status --short` 退出码 128，当前工作目录不是 Git 仓库，不影响文件核验。
- 实际核验命令：`& 'D:\ProgramData\Anaconda3\envs\MIAGuard\python.exe' -m py_compile scripts/build_t10_review_overlay.py` 退出 0；`& 'D:\ProgramData\Anaconda3\envs\MIAGuard\python.exe' -m pytest tests/test_defense_dataset.py -q` 为 9 passed；项目 Python 单独重算候选 5 份源文件与原 manifest 的哈希为 PASS，并检查 7 份更新文档的本地相对链接为 0 失效。限制：这些只核对结构/回归和文档入口，未验证 RAG 答案质量、IA 假阳性或防御泄露下降。
- `next_task=T10`：先基于 D-dev 短新闻片段做 2–3 轮会话与更广文档覆盖试点，核查多轮/跨文档/证据不足家族的真实可用性和样本量；根据结果记录协议 CHANGE，再改全量生成器与新数据版本。保留人工 gold 门禁。

### L042 — 2026-10-31（北京时间）— DOC-01 — BEGIN / DEVELOPMENT_DOCUMENT_RECONCILIATION

- 用户要求结合已完成进展及未来规划调整开发文档，后续继续按文档实施。本轮范围为文档状态、执行顺序、T10 子步骤、实验口径与入口一致性；不把文档更新记为新功能或实验完成。
- 实际命令：按顺序 `Get-Content docs/PROJECT_STATUS_ZH.md`、`docs/DATA_CATALOG_ZH.md`、`docs/EXPERIMENT_INDEX_ZH.md`，随后读取台账、当前规格/计划/协议、`docs/README.md` 与 `AGENTS.md`，退出码均为 0。发现计划开头仍称 T01–T18 全部未开始，项目入口仍含“尚未在线接入”等旧措辞，协议仍把固定五轮写作默认资源配置。
- 下一步：核对已存在 JSON 产物，修订原有有效文档并细化 T10 恢复入口；明确短会话对第三轮 Session 分数覆盖的影响、模型预审与人工 gold 的边界。修改后校验文档链接、状态与产物引用，保存审计记录。

### L043 — 2026-10-31（北京时间）— DOC-01 / T10–T11 — CHANGE / EXECUTION_BASELINE_V1_1

- 决定：沿用原规格/实施计划/协议路径，修订为执行基线 v1.1，不新增竞争主计划。T01–T09 与 G0/G1 保持已完成；T10 拆分 A–E，A 数据基础、B 两轮模型预审与开发 overlay 为已完成子步骤，C 轮数/文档选择试点为下一任务，D 全量生成、E 人工 gold 为未完成。T11 只允许不依赖正式 gold 的工程工作继续。
- 依据：已读取 E00 `comparison.json`（10 请求、4 query_only/6 fusion）、G1 fake 核验、T10 候选验证、第二轮预审核验及 overlay manifest/validation、T11 fake 评估，确认状态边界。读取两份 CLI 源码确认 benchmark 尚无 `--validate-only`/`--freeze-manifest`，评估器要求 `--output` 且仅支持 `engineering_only`。实际命令为 `Get-Content -LiteralPath <上述文件>`，退出 0。
- 协议变更：固定五轮降为旧 candidate06 配置；新正常会话长度必须由 D-dev 内容质量试点决定，2–3 轮只是候选，不能直接指定为已采用方案。第三轮起才有 Session 融合，须记录可用性并保留至少三轮有信息递进的独立正常会话组；不能用更短会话的低误干预或低成本冒充策略收益。IA nonmember Yes 率与 Masked 精确恢复诊断在正式运行前明确口径。
- 影响：新增开发/验收要求，不改冻结模型、历史结果、现有数据或实际规模；现有工程证据继续有效，不能用来放行正式效果。下一步修订文档并做一致性审计；本次不运行 D-dev 轮数试验或 E01–E07。

### L044 — 2026-10-31（北京时间）— DOC-01 — DONE / DOCUMENTS_VERIFIED

- 已调整 12 份文档：根 `AGENTS.md`/`README.md`、`docs/README.md`、项目状态、数据目录、实验索引、本台账、原主计划/规格/实验协议、研究建议入口和历史路线图入口。规格/计划/协议统一 v1.1，沿用原路径；修正“全部任务未开始”“尚未在线接入”“目录尚未创建”等旧描述，保留历史事件与原实验产物。
- 主计划细化 T10-A–E：A/B 已完成工程子步骤，C/D/E 尚未启动；C 的材料、同源 2/3 轮试验、扩文档 cohort、至少三轮正常组、审核记录/选择报告和验收条件已定义。T11 区分已完成 fake 工程与尚缺正式指标，协议补充变长会话的会话/家族汇总、Session 覆盖、IA Yes 倾向及 Masked 精确恢复诊断。两轮只是候选，没有宣称已改变实际样本规模。
- 源码核对还发现统一 live 尚不支持 B1、B5 当前只选 Top-1 parent；已在 T12 增加适配/定位身份验收，未改实现。文末 CLI 已区分已支持接口和待 T16 实现的预检查/冻结参数，工程评估示例补齐必填 `--output`。
- 实际命令：`& 'D:\ProgramData\Anaconda3\envs\MIAGuard\python.exe' scripts/run_defense_v1_benchmark.py --help`、同解释器执行 `scripts/evaluate_defense_v1.py --help` 和 `scripts/build_defense_v1_dataset.py --help`，均退出 0；项目 `python -` 执行文档审计，验证 12 份文档本地链接、代码围栏、18 个唯一主任务、A–E 子步骤、任务/门禁状态和版本。候选 10 个 artifact、overlay 4 个文件及第二轮审核 4 个文件哈希与各自 manifest/核验一致；E00、G1 与 T11 工程状态核对一致。结果为 `passed`、0 错误，完整清单与哈希见[文档审计 JSON](../reports/defense_v1/planning/document-audit-20261031.json)。
- 限制：仅完成文档维护及身份/接口核验，没有新增业务代码、数据版本或防御运行；未运行代码回归，本次不宣称新的功能测试通过。T10 仍 IN_PROGRESS、T11 仅工程阶段，G2–G4 与 E01–E07 未运行。后续按 **next_task=T10-C** 从主计划的材料清点/试点身份开始，完成可验证步骤后继续追加记录。

### L045 — 2026-10-31（北京时间）— T10-C — BEGIN / SESSION_PILOT

- 用户要求按记录继续，T10-C 从 NOT_STARTED 改为 IN_PROGRESS。先读取项目状态、数据目录、实验索引、文档索引、台账、v1.1 规格/计划/协议及第二轮处理决定，确认 T10-A/B 已完成工程子步骤、G0/G1 已通过，G2 仍未运行。
- 本轮从原 14 个开发集正常会话及其原文清点开始，只使用 D-dev 内容决定试点，记录 2/3 轮与旧 5 轮的同源比较、扩文档组和三轮会话覆盖。逐轮判断为 agent 的开发审阅，不冒称真实人员 gold。命令为 `Get-Content` / `rg` 读取上述文件，退出码均为 0。
- 下一步：核对原文件哈希、创建独立试点目录和原文清点；生成与检查可追溯的会话候选。不得覆盖旧审核或已冻结数据，不启动正式效果实验。

### L046 — 2026-10-31（北京时间）— T10-C — SOURCE_INVENTORY / IN_PROGRESS

- 项目解释器 `& 'D:\ProgramData\Anaconda3\envs\MIAGuard\python.exe' -` 读取修订清单及第二轮审核，先重算三份输入和四份审核文件 SHA256，再生成[试点清单](../reports/defense_v1/T10/session_length_pilot_20261031_01/pilot_manifest.json)、[14 个原会话清点](../reports/defense_v1/T10/session_length_pilot_20261031_01/session_inventory.jsonl)和[逐篇原文](../reports/defense_v1/T10/session_length_pilot_20261031_01/source_evidence.jsonl)，退出码 0。14 个会话、70 轮，按全部补充证据去重为 **15 篇**原文；外部摘要称 13 篇，不能复用该数作为双文证据的实际去重数量。
- 每个来源记录文本哈希、标题边界是否有结构标识、可见截断及 Codex 根据原文列出的候选事实；第二轮结果原样保留，不将模型 accept 当作真人审核。下一步比较同源 2/3 轮，并筛选 D-dev 额外文档；现仅完成清点，尚无长度选择或实际 RAG 运行。

### L047 — 2026-10-31（北京时间）— T10-C — VARIANTS_DRAFTED / IN_PROGRESS

- 项目解释器分别运行 `reports/defense_v1/T10/session_length_pilot_20261031_01/draft_same_source.py`、`draft_expanded.py` 和 `review_baseline.py`，退出码均为 0。同源 14 会话生成 14 个两轮草稿、12 个三轮草稿，2 个三轮方案因缺少可区分事实而排除；扩文档组从 D-dev 索引另选 16 篇，覆盖七家族各 2 个会话，起草 28 个两轮/三轮方案。实际分别写入 `normal_variants.jsonl`、`expanded_variants.jsonl` 与对应证据、来源选择文件。
- 对旧五轮生成 14 条 Codex 自检记录（12 建议重写、2 有争议）；新草稿暂标需独立内容审核，含不答类连续缺失问题与一组仅相关能源主题、没有已证明因果联系的跨文档配对。该结果不是模型或人工通过率，也不能据此确定全量会话长度。
- 下一步：独立核验版本/文档身份、同源前缀、必需证据、事实及会话连续性，形成可审核的试点汇总与限制；若内容审核不完，明确保留 IN_PROGRESS 和恢复入口。

### L048 — 2026-10-31（北京时间）— T10-C — STRUCTURE_VERIFIED / CONTENT_REVIEW_PENDING

- `& 'D:\ProgramData\Anaconda3\envs\MIAGuard\python.exe' reports/defense_v1/T10/session_length_pilot_20261031_01/verify_and_summarize.py` 退出 0，生成[结构验证](../reports/defense_v1/T10/session_length_pilot_20261031_01/validation.json)与[中间统计](../reports/defense_v1/T10/session_length_pilot_20261031_01/selection_report.json)，更新[试点 manifest](../reports/defense_v1/T10/session_length_pilot_20261031_01/pilot_manifest.json)。核对 D-dev 索引哈希、31 篇原文身份、2/3 轮前缀配对、134 个版本化请求 ID、双篇题证据 ID 和审核 ID；无结构错误。同一 `doc_id` 连通后为 27 组，尚未做跨 ID 近重复审计。
- 产出[阶段记录](../reports/defense_v1/T10/session_length_pilot_20261031_01/DECISION_ZH.md)及[独立内容审核交接](../reports/defense_v1/T10/session_length_pilot_20261031_01/REVIEW_GUIDE_ZH.md)，审核范围为 54 个有内容版本、2 个排除版本和 14 个旧五轮参考。所有候选是 Codex 自拟/自检，`uncertain`，结构通过不等于事实、证据蕴含或会话质量通过；无真人 gold。
- 已同步主计划复选框、项目状态、数据目录、实验索引及文档索引。下一步：收集独立逐会话审核输出并核验其输入哈希、70 个 ID、逐轮问题与原文支持；修订/排除后形成真正的轮数和覆盖选择报告，再按协议更新实际方案。若尚无审核输出，恢复于审核指南，不得勾选 T10-C 完成或启动 T10-D 全量生成。
- 本次未执行 Judge/live RAG、防御效果或代码回归；没有修改 candidate06、外部审核和原始索引。T10 IN_PROGRESS，T11 正式评估、G2 及 E01–E07 均未运行。

### L049 — 2026-10-31（北京时间）— T10-C — HANDOFF_VERIFIED / RESUME_POINT

- 最终以 `& 'D:\ProgramData\Anaconda3\envs\MIAGuard\python.exe' -` 重算试点 manifest 中 17 份文件 SHA256，检查 56 个版本 ID、14 个旧五轮参考、54 个草稿/2 个排除项和 134 个问题身份，并核对 9 份当前文档的 312 处本地链接；退出 0，0 错误。结构核验的永久产物为[validation.json](../reports/defense_v1/T10/session_length_pilot_20261031_01/validation.json)，其内容质量限制不变。
- 恢复点：独立审核者按[审核指南](../reports/defense_v1/T10/session_length_pilot_20261031_01/REVIEW_GUIDE_ZH.md)生成新目录的 70 条逐会话意见；接收后先核对 SHA256 与完整 ID，复核争议后再确定 T10-C 轮数方案。主计划的扩文档合格性、三轮真实递进、独立内容审核、最终选择项均保持未勾选。
- 限制：这次校验不验证事实蕴含、近重复或人工 gold；没有运行 RAG、防御实验或正式指标，T10-C 保持 IN_PROGRESS。

### L050 — 2026-11-02（北京时间）— T10-C — BEGIN / INDEPENDENT_MODEL_REVIEW_RECEIVED

- 用户提交 `reports/defense_v1/T10/external_review/pilot_t10c_deepseek_20261102_01/`，报告 70 个版本已审完、模型自报 `deepseek-v4.1-flash`。本轮依次读取项目状态、数据目录、实验索引、台账、T10 实施步骤及外部 manifest/摘要，`Get-Content` 等读取命令退出 0；G2 未运行，T10-C 仍 IN_PROGRESS。
- 接收原则：先重算试点和审核输出身份、70 个 ID 与逐轮证据，再查原文和上下文依赖的判定；模型建议只作开发证据，不自动转成人工 gold。两轮默认和四事实门槛均先核验其论据及样本限制。
- 下一步：保存独立核验结果与审核决策，修正可确认缺陷并更新试点选择/执行文档；不运行或声称正式防御效果。

### L051 — 2026-11-02（北京时间）— T10-C — VALIDATION_FAILED / RETRY

- 项目解释器以 `python -` 对试点与外部审核做首次结构核验，输出 `reports/defense_v1/T10/review_validation_t10c_20261102.json`，退出码 1。70 行、204 轮、55 个建议轮和总体 50/18/2 已读取；两组 expanded 计数比较失败。
- 原因定位：本地核验代码误将已包含 `expanded_sources_` 的分组名再次替换，属于核验脚本映射错误，不能据此认定审核输出分组错误。下一步修正映射并完整重跑，保留首次失败事实；审核结果尚未放行。

### L052 — 2026-11-02（北京时间）— T10-C — EXTERNAL_REVIEW_STRUCTURALLY_VERIFIED

- 新增 `reports/defense_v1/T10/verify_review_t10c_20261102.py`，执行 `& 'D:\ProgramData\Anaconda3\envs\MIAGuard\python.exe' reports/defense_v1/T10/verify_review_t10c_20261102.py` 退出 0，生成[独立核验 JSON](../reports/defense_v1/T10/review_validation_t10c_20261102.json)：18 项输入身份、输出文件哈希、70 个 ID/顺序、204 个被审轮、55 个建议轮及证据范围核对通过，正常版本 accept/rewrite/reject 为 50/18/2。
- 审核中 2 处 `supported=false` 均为 Ovitz 旧五轮的截断补全；本次核验只检查文件契约，未证明其余事实、模型快照或审阅过程。初查四个非旧版改写建议：两条油价版本的二分/指代及两条赛马版本的疑问词需处理；初步还须复核证据不足和弱跨文档配对。
- 下一步逐项对照原文，另建修订试点与决策报告；原候选及外部审核结果保持只读。

### L053 — 2026-11-02（北京时间）— T10-C — REVIEW_REVISION_AND_DEDUP_DIAGNOSTIC / IN_PROGRESS

- `& 'D:\ProgramData\Anaconda3\envs\MIAGuard\python.exe' reports/defense_v1/T10/build_t10c_revision_20261102.py` 退出 0，新建[独立修订试点](../reports/defense_v1/T10/session_length_pilot_rev2_20261102_01/manifest.json)：56 个版本（54 个带内容、2 个维持排除）、31 篇来源；四个有内容版本应用油价/赛马改写建议。赛马第 2 问额外保留显式引用要求，以免偏离 citation_check；新版本/问题 ID 与旧输入分离，全部 pending，无人工 gold。
- 项目解释器 `python -` 独立生成[修订试点验证](../reports/defense_v1/T10/session_length_pilot_rev2_20261102_01/validation.json)，退出 0、0 错误；核对 134 个新请求 ID、2/3 轮同源前缀、四处改写、双文证据、原始审核身份以及 7 条模型判断含指代的三轮标注。此结构核验不能证明指代必需、事实蕴含或自然度。
- 项目 `python -` 基于既有 normalized-word-trigram SimHash（64 位，距离≤3）在 31 篇、465 对文档上计算[近重复诊断](../reports/defense_v1/T10/near_duplicate_audit_t10c_20261102.json)，退出 0；算法发现 31 个单文档组、最小距离 20。该方法不能排除同事件/语义相似或共享来源，不能据此声称 31 个独立样本；同一 doc_id 的跨会话依赖仍须合并。
- 限制：外部模型对 7 个指代的判断尚未用去历史对照证实；四个证据不足三轮和能源弱配对仍标争议。模型提出的“默认两轮”“至少四个事实”暂为待验证假设，不因有 50 条 accept 就更改正式数据规则。下一步完成逐项决策与接续文档，明确尚需的语义审核和样本依赖处理。

### L054 — 2026-11-02（北京时间）— T10-C — REVIEW_INCONSISTENCY / ADJUDICATION

- 对照 `session_inventory.jsonl` 和外部 `session_review.jsonl` 的 Ovitz 旧五轮，项目解释器 `python -` 退出 0：审核者把第 1、3 轮的 `not willing to pay` 判为原文截断后无支持，但第 4 轮答案同样包含该补全，却标 supported=true。按一致的严格原文标准，第 4 轮也须裁决；原审核输出的 2 个 supported=false 计数保持原样，不覆盖外部文件。
- 已在[处理决定](../reports/defense_v1/T10/REVIEW_TRIAGE_T10C_20261102_ZH.md)记录差异。该条属于旧五轮诊断，不在新修订候选中；单模型逐条意见仍需复核，不能将“只发现 2 条”解释成其他 202 轮都已证明事实正确。

### L055 — 2026-11-02（北京时间）— T10-C — HISTORY_ABLATION_PREPARED / NOT_RUN

- 用项目解释器 `python -` 从修订试点中提取模型标为含指代的 7 个三轮候选，生成[有/无历史配对设计](../reports/defense_v1/T10/session_length_pilot_rev2_20261102_01/history_ablation_design.json)，退出 0；保存候选身份、两种条件、固定原文和前两轮建议答案的控制要求。7 个例子来自模型预选，不能外推至全部正常请求。
- 此项仅为试验设计：前两轮采用待核验的参考答案作为固定历史，不等同真实服务生成历史；未调用生成器/Judge、未测第三轮有无历史的准确性或 Session/fusion 激活。后续如运行需先核实历史不会直接泄漏第三轮答案，固定模型/提示/来源并记录失败和身份。
- T10-C 的最终轮数、自然度与跨文档争议、事件级依赖仍未完成；独立模型预审不替代 T10-E 真人 gold。下一步进行候选争议裁决并决定是否开展该开发对照；T10-D 和正式实验仍未开始。

### L056 — 2026-11-02（北京时间）— T10-C — DEPENDENCY_GROUPING_DRAFT / IN_PROGRESS

- 项目解释器 `python -` 对修订试点 28 个来源会话，按相同 doc_id、parent 与已有 duplicate group 建图，并生成[依赖分组草案](../reports/defense_v1/T10/session_length_pilot_rev2_20261102_01/dependency_grouping_draft.json)，退出 0。基础规则 27 组；将 3 个油价/能源主题会话额外保守合并时为 25 组。2/3 轮版本已先按同一来源会话合并。
- 限制：额外合并只是假设相关性的敏感性分组，不主张属于同一事件；其他共享实体、来源和语义近重复尚未完成审核。两种组数均不能直接作为正式独立样本量。继续在 T10-C 裁决来源关系与会话自然度，必要时再按[历史消融设计](../reports/defense_v1/T10/session_length_pilot_rev2_20261102_01/history_ablation_design.json)开展开发测试。

### L057 — 2026-11-02（北京时间）— T10-C — CROSS_DOCUMENT_REPLACEMENT_PROPOSED

- 为处理能源弱配对，项目解释器 `python -` 从 D-dev 索引中选取两篇都涉及创纪录油价与美国股市的来源，建立[独立替换建议](../reports/defense_v1/T10/crossdoc_replacement_20261102_01/manifest.json)：2/3 轮各一个版本、5 个版本化问题，两篇报道的日期和因果链不强行关联。原弱配对仍保留作争议记录，尚未自动替换进 rev2。
- 另以项目 `python -` 生成[结构验证](../reports/defense_v1/T10/crossdoc_replacement_20261102_01/validation.json)，退出 0：来源哈希、两种长度前缀、双篇证据范围及 pending 状态通过；两篇之间 SimHash 距离 31，与原 31 篇的最小距离 24。SimHash 与结构检查不证明无语义重复、自然度或真正跨文综合；新问题尚未经独立内容审核或真人 gold。
- 下一步：将替换建议、赛马/油价改写、证据不足会话与历史消融设计纳入 T10-C 裁决；当前 T10-C 仍 IN_PROGRESS，正式长度未冻结，T10-D 未启动。

### L058 — 2026-11-02（北京时间）— T10-C — REVIEW_INTEGRATION_VERIFIED / RESUME

- 已同步[项目状态](PROJECT_STATUS_ZH.md)、[数据目录](DATA_CATALOG_ZH.md)、[实验索引](EXPERIMENT_INDEX_ZH.md)、[文档索引](README.md)、[v1.1 主计划](superpowers/plans/2026-10-22-defense-framework-implementation.md)和[实验协议](DEFENSE_EXPERIMENT_PROTOCOL_ZH.md)。T10-C 继续 IN_PROGRESS：独立模型预审已完成结构核验，但内容争议、真实前文依赖和最终轮数尚未确定；不改动 T10-D/E、G2–G4 或 E01–E07 状态。
- 项目解释器 `python -` 完成最终[接收与修订审计](../reports/defense_v1/T10/review_integration_audit_20261102.json)，退出 0、0 错误：重新核对 18 项外部审核输入与 3 份输出哈希、新试点及替换建议文件身份、7 个未运行历史对照设计、文档本地链接及当前 next_task。检查固定历史是否直接包含第三轮答案时仅比较完整字符串，不能证明不存在语义泄漏。
- 未运行 Judge/live RAG、成员攻击或防御效果实验；未运行代码回归。现有评估脚本和数据构建器未改，新增的是审核核验/试点处理脚本和开发材料。下一步优先核查四个改写与替换配对的内容、证据不足组自然度和事件关联；按需执行已设计的 D-dev 受控历史对照，再登记实际长度及覆盖决定后进入 T10-D。

### L059 — 2026-11-02（北京时间）— T10-C — BEGIN / SMALL_REVIEW_AND_RESUME

- 用户授权：少量数据由当前 agent 直接核对与修改；需要大规模审核时可准备审核包交用户安排的另一个 LLM agent。模型判断仍须如实标为 agent 预审，不能冒充协议所需的真人 gold。
- 已按入口读取项目状态、数据目录、实验索引、台账、T10-C 计划、实验协议及上轮处理决定，`Get-Content` 退出 0。当前先核查四个改写版本、两个跨文档替换版本和证据不足会话，再评估有/无历史对照的可行性；原数据和既有评审保留。
- 下一步：记录每条的原文依据和判定，生成可审阅的新修订；仅在满足 T10-C 门禁后决定是否进入 T10-D。

### L060 — 2026-11-02（北京时间）— T10-C — SMALL_CONTENT_REVIEW / IN_PROGRESS

- 根据用户授权由当前 Codex agent 逐条检查 14 个版本：原油价/赛马改写 4、证据不足 8、跨文档替换 2；逐一读取对应 D-dev 原文。油价和赛马修订的答案与必需证据可对应原文；替换题第三轮将“近三周首次”问为精确时间间隔，需收紧为原文给出的时期。
- `& 'D:\ProgramData\Anaconda3\envs\MIAGuard\python.exe' reports/defense_v1/T10/adjudicate_small_t10c_20261102.py` 退出 0，生成[小样本审核清单](../reports/defense_v1/T10/session_length_pilot_targeted_20261102_01/adjudication.jsonl)及[独立修订试点](../reports/defense_v1/T10/session_length_pilot_targeted_20261102_01/manifest.json)：14 个版本的开发审核、10 个新草稿版本/25 轮；证据不足问题改用更自然的问法，替换题第三轮保留“首次超过阈值是在三周内”而不制造精确间隔。2/3 版本保持前缀一致。
- 这是 Codex agent 的小样本内容审核与建议，`human_reviewed=false`，不是人工 gold；四组证据不足三轮的连续不答自然度仍有争议，新问法未被独立复核。下一步做文件与原文核验，检查历史对照的运行条件并确定可以独立完成的选择范围。

### L061 — 2026-11-02（北京时间）— T10-C — SMALL_REVIEW_VERIFIED / MODEL_PREFLIGHT

- 项目解释器 `python -` 生成[小样本修订验证](../reports/defense_v1/T10/session_length_pilot_targeted_20261102_01/validation.json)，退出 0、0 错误：14 个审核版本（5 个建议暂接受、9 个建议改写）、10 个独立草稿版本、25 轮、9 篇证据；哈希、2/3 前缀、证据范围及 pending/非人工身份一致。此验证不证明改写自然或语义正确。
- 只读探测：`python -c` 的本地 `127.0.0.1:11434` socket 可连接；`torch.cuda.is_available()` 为 True，1 GPU；`Test-Path LLM/Qwen2.5-7B-Instruct` 为 True；读取 Ollama `/api/tags` 发现 `qwen2.5:latest` 7.6B、Q4_K_M，digest `845dbda0ea48ed749caafd9e6037047aa19afeb0b697e`。此路由模型量化与原冻结 Qwen BF16 不同，不能冒充同一个模型快照。
- 下一步：先核实 7 个有/无历史对照的材料与前两轮答案，再以新的 engineering_only 运行目录记录一次小规模本地对照；该对照仅分析文本理解，不测 Judge 的 Session/fusion 或防御效果。

### L062 — 2026-11-02（北京时间）— T10-C — CORRECTION / ABLATION_PREPARATION

- 更正 L061 中手录的模型 digest：本地 Ollama `/api/tags` 实际返回 `qwen2.5:latest` 的完整 digest 为 `845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e`；L061 的字符串有抄录错误，不能作为模型身份。重新读取 `/api/tags` 退出 0。`nvidia-smi --query-gpu=name,memory.total,memory.free --format=csv,noheader` 退出 0，显示 RTX A5000 24GB、可用约 21GB；`/api/ps` 当时无已加载模型。
- 七个候选的前两轮及原文已逐例核对，目标答案没有直接出现在建议历史中；仍不排除语义提示。准备以本地 Q4_K_M 模型做 7 组固定原文/固定第三问、两种历史条件的小型工程对照。固定前两轮为参考答案，不能解释为真实 RAG 生成历史；模型与历史 BF16 冻结 Judge 不同，不测其融合分数。记录新的 run_id、输入/模型哈希、实际 prompt、逐项响应与失败，运行前先做无模型调用的输入核验。

### L063 — 2026-11-02（北京时间）— T10-C — ABLATION_START

- 新增试点运行器 `reports/defense_v1/T10/run_t10c_history_ablation.py`。先执行 `& 'D:\ProgramData\Anaconda3\envs\MIAGuard\python.exe' reports/defense_v1/T10/run_t10c_history_ablation.py --output data/defense_v1_runs/t10c-history-ablation-20261102-01`，退出 0，`preflight_passed_no_generation`：7 个来源会话、14 个条件请求，来源与设计 SHA256、同源问题、目标答案未逐字出现在固定历史及 Ollama 模型 digest 均核对；预检未调用生成模型。
- 计划以同一命令增加 `--execute` 运行，输出新目录 `data/defense_v1_runs/t10c-history-ablation-20261102-01/`。固定来源、第三问、system prompt、温度 0、seed 20261102；条件次序由该 seed 决定。逐项保存真实 prompt、输出、失败与模型摘要；输出参考答案独立于模型请求。
- 这只测选定本地 Q4_K_M 模型对固定历史文本的回答，是 engineering_only 开发诊断；不走检索/Judge/访问控制，不证明防御有效，历史答案仍非人工 gold。启动后记录实际运行结果，意外中断不能记完成。

### L064 — 2026-11-02（北京时间）— T10-C — ABLATION_EXECUTED / REVIEW_PENDING

- 实际执行 `& 'D:\ProgramData\Anaconda3\envs\MIAGuard\python.exe' reports/defense_v1/T10/run_t10c_history_ablation.py --output data/defense_v1_runs/t10c-history-ablation-20261102-01 --execute`，退出 0；[运行 manifest](../data/defense_v1_runs/t10c-history-ablation-20261102-01/run_manifest.json)为 complete、14/14 completed、0 failed，结束时路由模型 digest 与起始一致。实际 prompt、参考建议、原始响应和日志分开保存于同目录。
- 初读 14 条响应，7 组的有/无历史回答均与建议答案表面相符；这是尚未完成逐条裁决的观察，不作为正式准确率、历史必要性或防御效果。实际模型是本地 `qwen2.5:latest` Q4_K_M，固定材料和人为填入的前两轮建议答案，未调用 Judge/融合/检索。
- 下一步：逐条根据来源核对回答并保存 agent 评审结果、完整分母和模型身份；核对 run 文件哈希后登记实验索引，更新 T10-C 的数据选择与剩余任务。

### L065 — 2026-11-02（北京时间）— T10-C — ABLATION_AGENT_ADJUDICATED / IN_PROGRESS

- `& 'D:\ProgramData\Anaconda3\envs\MIAGuard\python.exe' reports/defense_v1/T10/adjudicate_t10c_history_ablation.py` 退出 0；先核对 run/请求/标签/响应哈希和 14 条确切输出，再将逐条原文依据与 Codex agent 判定写入[评审明细](../data/defense_v1_runs/t10c-history-ablation-20261102-01/agent_adjudication.jsonl)、[诊断摘要](../data/defense_v1_runs/t10c-history-ablation-20261102-01/agent_diagnostic_summary.json)和 assessment manifest。7/7 个有历史、7/7 个无历史回答都被当前 agent 判为能由所给原文支持且回答了问题；其中一个只答 Kadyrov 姓名，没有职位，但问题仅问谁。
- 解释边界：这 7 个样例由审核模型预先标为含指代，来源全文在两种条件都可见；无历史也可答说明当前本地 Q4 模型在这些固定原文下不需要对话历史即可给出被 agent 判断为正确的答案。不能外推其他模型/样本，不能宣称测到 Session 融合或防御效果；参考答案和 agent 判断均无真人 gold。
- 下一步：保留本结果，设计更有区分力的正常三轮样例（同一材料提供两个可能对象或数值，前文明确焦点但不泄露第三轮答案），以有/无历史配对判断；仍按开发数据和单次运行分别记录，不修改冻结 Judge 或 test。

### L066 — 2026-11-02（北京时间）— T10-C — CONTEXT_FOCUS_CANDIDATES_CREATED

- `& 'D:\ProgramData\Anaconda3\envs\MIAGuard\python.exe' reports/defense_v1/T10/build_context_focus_pilot.py` 退出 0，建立[上下文焦点试点](../reports/defense_v1/T10/context_focus_pilot_20261102_01/manifest.json)：两篇 D-dev 报道分别给出 Friday/Wednesday；两个三轮版本使用同一原文和相同第三问，前两轮分别选择“股市下跌”或“上涨”的报道，目标答案因历史焦点不同。前两轮参考答案未给出星期。
- 两个版本共享两篇来源，属于同一依赖组；没有前文的第三问无法唯一判断指的是哪篇报道，合理回应应说明不确定或分别列出两种可能，而不是把碰巧选中的星期当正确。当前仅为 agent 起草，尚未调用模型或形成真人 gold；下一步先核对模型和 prompt 身份，再做条件配对。

### L067 — 2026-11-02（北京时间）— T10-C — CONTEXT_FOCUS_PREFLIGHT / START

- `& 'D:\ProgramData\Anaconda3\envs\MIAGuard\python.exe' reports/defense_v1/T10/run_t10c_context_focus.py --output data/defense_v1_runs/t10c-context-focus-20261102-01` 退出 0，`preflight_passed_no_generation`：4 个条件请求、两条无历史 prompt 逐字一致、两种目标均未逐字出现在各自前两轮建议答案；模型 digest 与 L062 一致。未调用生成模型。
- 将以同一命令加 `--execute` 写入新 run 目录。预登记评分：有历史时分别判断 Friday/Wednesday 是否与对应焦点一致；无历史时两篇和第三问相同，需识别焦点不明确或同时列两种可能，单答某一星期只是无依据猜测。两次无历史请求不是独立样本。
- 本试点只比较同一 Q4 模型在固定正文和教师给定历史下的回答；不调用 Judge/检索/防御，不证明正式数据质量、Session 融合或防御效果。

### L068 — 2026-11-02（北京时间）— T10-C — CONTEXT_FOCUS_EXECUTED / REVIEW_PENDING

- 实际执行 `& 'D:\ProgramData\Anaconda3\envs\MIAGuard\python.exe' reports/defense_v1/T10/run_t10c_context_focus.py --output data/defense_v1_runs/t10c-context-focus-20261102-01 --execute`，退出 0；[run manifest](../data/defense_v1_runs/t10c-context-focus-20261102-01/run_manifest.json)为 complete、4/4 请求完成、0 失败。
- 初读响应：有历史时，两种焦点分别得到 Friday 和 Wednesday；无历史的两次相同 prompt 均返回 Friday。按事先定义的任务，无历史不应凭空选择一个焦点；但此处仍需核对原文、真实 prompt 和身份，再保存逐条 agent 判定。一个版本碰巧对应 Friday 不可被当作无历史成功。
- 两次无历史为相同输入，仅一个独立问题；这一极小样例及固定参考历史不能支持总体准确率、Session/fusion 激活或防御效果结论。下一步核对并登记结果。

### L069 — 2026-11-02（北京时间）— T10-C — CONTEXT_FOCUS_AGENT_ADJUDICATED

- `& 'D:\ProgramData\Anaconda3\envs\MIAGuard\python.exe' reports/defense_v1/T10/adjudicate_t10c_context_focus.py` 退出 0；核对原文中 Friday/Wednesday、真实输入/输出及 run 哈希后生成[逐条 agent 判断](../data/defense_v1_runs/t10c-context-focus-20261102-01/agent_adjudication.jsonl)与[诊断摘要](../data/defense_v1_runs/t10c-context-focus-20261102-01/agent_diagnostic_summary.json)。两个有历史焦点分别得到与原文一致的星期；两个无历史请求为同一 prompt，均只答 Friday，未说明另一个可能的 Wednesday，按预登记规则属于焦点未确定的单一猜测。
- 对照差异只说明这一对同源样例、Q4 模型及固定参考历史下观察到焦点影响；不能把相同无历史输入当两个独立问题，不能泛化为模型总体准确率，也未测真实 Session 融合、RAG、防御效果或人工 gold。下一步根据 7 组旧样例与此一组对照，制作按家族/轮数/来源依赖可追溯的开发候选，保留未决风险。

### L070 — 2026-11-02（北京时间）— T10-C/T10-D — CHANGE / SHARED_BACKGROUND_SOURCE_PROVENANCE

- 用项目解释器 `python -` 对照 candidate06 的 D-dev 目标 ID 与共享背景 ID，退出 0：初始 15 篇试点原文全部为 D-dev 目标；扩展 16 篇中 2 篇为 D-dev 目标、14 篇为共享背景；上下文焦点的 2 篇替换文章均为共享背景。比较仅使用文档 ID/分区和背景身份，不根据攻击结果或成员攻击标签筛题。
- 明确既有分区去重规则的实施方式：共享背景可继续按既有设计存在于多个检索索引，但已用于 D-dev 问题设计、模型输出/内容检查的文档及其同 parent/近重复组不得再作为 V/T 正常问题的源材料；同时记录更宽松/严格事件级关联的限制。索引可复用，不能把“同一文档参与不同分区检索”误记成“作为不同分区独立正常题目源”；也不能把背景文档改成 nonmember 攻击目标。
- 该约束不修改已有 candidate06 索引/数据或旧结果。后续 T10-D 生成新版本前须在单独的来源使用清单中保存该开发使用历史及排除/近重复审计，若导致 V/T 合格源不足，先记录规模损失并修订协议，不能无说明复用。下一步同步现行协议、数据目录和生成器验收步骤。

### L071 — 2026-11-02（北京时间）— T10-C/T10-D — NORMAL_SOURCE_USAGE_CAPTURED

- 项目解释器 `python -` 汇总两轮正常题审核原文、T10-C 同源/扩展原文和替换样例，生成[正常题源使用清单](../reports/defense_v1/T10/normal_source_usage_20261102_01/manifest.json)与逐来源记录，退出 0：35 篇已知来源中 19 篇为 D-dev 目标、16 篇为共享背景。清单记录来源文件哈希、parent/duplicate group、开发使用范围与 A-cal/V/T 正常出题排除要求。
- 已同步[实验协议](DEFENSE_EXPERIMENT_PROTOCOL_ZH.md)、[数据目录](DATA_CATALOG_ZH.md)与[实施计划 T10-D](superpowers/plans/2026-10-22-defense-framework-implementation.md)。清单仅覆盖列出的正常审核与试点，不包含全部历史开发 prompt/攻击来源，不能作为完整终测隔离证明；共享背景继续留在索引。
- 另外核对新上下文焦点两篇文章均为共享背景，candidate06 `documents.jsonl` 只含目标文档而不含这两篇。后续若让数据校验器处理背景来源，必须基于实际分区索引和来源元数据扩展校验，不能伪造背景文章原始分区或默默跳过校验。

### L072 — 2026-11-02（北京时间）— T10-C — CHANGE / PROVISIONAL_DEV_COHORT

- 对本次 D-dev 工程试点提出可复核的暂定队列：从 28 个来源会话各选一个两轮版本，使用已核对的证据不足问法和跨文档替换建议；另加同一来源组、相反历史焦点的两个三轮版本，用于第三轮会话行为的开发检查。该选择仅是 D-dev 试点构建方案，不规定全量/正式数据必须两轮，不视为最优长度或正式样本量。
- 原因：7 个先前指代样例在给定原文时无历史也可答；新的一组不同焦点样例在本地模型单次诊断中表现出前文影响。两条三轮样例共享来源且教师给定历史，不能当作两个独立来源或代表真实 Session/fusion 效果。为保留全量数据方案的开放性，所有正式数据/模型/协议最终选择仍待 T10-C 验收并登记。
- 下一步：新建独立、不可直接正式回放的开发候选及来源/ID 对照，验证数量、成对关系、来源角色和 pending 状态；记录家族分布不等及风险，不将旧试点写为已被覆盖。

### L073 — 2026-11-02（北京时间）— T10-C — PROVISIONAL_DEV_COHORT_CREATED

- `& 'D:\ProgramData\Anaconda3\envs\MIAGuard\python.exe' reports/defense_v1/T10/build_t10c_dev_cohort_20261102.py` 退出 0，生成[独立开发候选](../reports/defense_v1/T10/session_length_dev_cohort_20261102_01/manifest.json)：28 个两轮基线会话加 2 个三轮上下文焦点会话，共 30 会话、62 问、31 篇来源；使用新会话/请求 ID 并可追溯各输入版本。全部 pending、非人工 gold、不可直接正式回放。
- 按相同 doc/parent/已有 duplicate group 连接为 27 个基础来源依赖组；其中 17 篇 D-dev 目标、14 篇共享背景。多轮精读 6 会话，其他六类各 4；额外两个三轮焦点会话共享同一来源组，不能计作两篇独立文档。未在此队列直接将不同长度作受控效果比较，原同源配对试点仍留存。
- 这是开发队列而非全量或最终正式长度规则；新证据不足问法/替换对照由 Codex 小样本审核，正式 gold 仍待真人核对。同事件/语义相关、真实 Session 融合效果与完整开发来源排除审计尚未完成。下一步独立验证队列身份、在线/离线边界与文档一致性，再判断 T10-C 可完成的范围。

### L074 — 2026-11-02（北京时间）— T10-C/T10-D — CHANGE / D-DEV_DESIGN_SELECTED

- D-dev 开发选择已形成[可追溯候选](../reports/defense_v1/T10/session_length_dev_cohort_20261102_01/manifest.json)、[独立结构验证](../reports/defense_v1/T10/session_length_dev_cohort_20261102_01/validation.json)、[选择报告](../reports/defense_v1/T10/session_length_dev_cohort_20261102_01/selection_report.json)和[通俗说明](../reports/defense_v1/T10/session_length_dev_cohort_20261102_01/DECISION_ZH.md)。七类基础队列各 4 个两轮会话；另有 2 个三轮上下文焦点会话作为诊断，共 30 会话、62 轮、31 篇来源。两条三轮共享一组来源，不能冒称多组独立样本。
- 选择依据：原 7 组有/无历史的固定原文对照中，Codex agent 判断本地 Q4 模型两种条件各 7/7 可答；另一个相反焦点的同源样例有历史时分别得到 Friday/Wednesday、无历史相同 prompt 两次只猜 Friday。两次运行均只作小样本文本理解诊断，不使用检索/Judge/防御动作，不等同于 Session/fusion 效果。四组证据不足三轮和旧能源弱配对未纳入基础队列，保留备选和排除依据。
- 设计边界：本次只选定 D-dev 试点，不宣布两轮为全量最优或固定正式配额；三轮正式覆盖必须从多个独立来源组构建，若材料不够须限制结论。按相同 doc/parent/已有 duplicate group 的基础分组为 27 组；按油价主题和共享 Blair/Bush 人物做保守敏感性合并为 23 组，两者均不证明语义独立。
- 影响：不改冻结 Judge 或历史数据；所有候选/答案仍 pending、非人工 gold、不可直接正式回放。T10-D 开始时先补全历史开发来源使用审计，并修复正常题源可为共享背景时的校验契约；在真实终测前完成分区出题源隔离。T10-E 真人 gold 与 E07 仍未完成。

### L075 — 2026-11-02（北京时间）— T10-C / T10-D — DESIGN_GATE_COMPLETE / NEXT_BEGIN

- T10-C 的 **D-dev 设计子任务**完成，选择/结构/小样本模型对照证据见 L073–L074；实验协议、计划及项目入口同步。此完成状态仅说明开发设计有记录，不表示最终数据、人工 gold、真实 Session/fusion 或正式效果完成。
- T10-D 改为 IN_PROGRESS。先清点既有 T10 开发资料暴露的正常/攻击原文及共享背景角色，补全可追溯 ID 和排除规则；不能读取攻击标签用于筛选问题，也不能把共享背景误当 nonmember。随后按 T10-D 计划为共享背景和版本化生成器编写有意义的回归测试。
- 开始命令：`Get-Content` 按入口读取状态、数据目录、实验索引、台账、主计划和实验协议，及 `rg` 检查数据路径；本任务尚未生成新全量数据或运行正式防御实验。下一步汇总可定位的历史输入并记录覆盖盲区。

### L076 — 2026-11-02（北京时间）— T10-D — PARTIAL_ATTACK_SOURCE_AUDIT

- 执行 `& 'D:\ProgramData\Anaconda3\envs\MIAGuard\python.exe' reports/defense_v1/T10/audit_review_attack_sources_20261102.py` 退出 0；两轮攻击审核包各 16 条，通过标准化原文唯一匹配到 4 篇 D-dev 目标，未匹配/歧义 0，1 篇也在既有 35 篇正常题来源清单中。新增[攻击审核来源清单](../reports/defense_v1/T10/review_attack_source_usage_20261102_01/manifest.json)，合并已知来源为 38 篇；输出不含成员标签或攻击结果，不按其筛选。
- 仍仅覆盖清单指定的审核材料；其他历史开发 prompt 和事件/语义相关性尚需审计，不能据此宣称所有分区独立。保留共享背景检索用途。检查 `git rev-parse --is-inside-work-tree` 退出 1，当前工作区没有 Git 仓库，因此未创建工作树或提交。

### L077 — 2026-11-02（北京时间）— T10-D — SOURCE_VALIDATOR_PARTIAL

- 对独立正常题来源校验函数先运行 `python -m pytest tests/test_defense_source_usage.py -q`，因函数未实现按预期失败；随后实现基于实际分区索引、来源清单及 parent/duplicate 传递关联的检查。最终 `& 'D:\ProgramData\Anaconda3\envs\MIAGuard\python.exe' -m pytest tests/test_defense_source_usage.py tests/test_defense_dataset.py -q` 退出 0，15 passed。测试覆盖共享背景可跨索引保留但不能重复出题、缺索引、证据范围、关联传播与缺失暴露来源。
- 使用项目解释器 `python -` 将 38 个已知来源与 candidate06 的 D-dev 实际 1000 条索引及开发队列逐轮比较：62 轮通过。此检查不判断题目语义或资料是否独立；函数依赖调用者提供完整来源历史和真实索引，不能发现未知历史或语义近重复，尚未接入全量生成器、不能代替 T10-D 最终门禁。
- 一次 `rg` 使用 Windows 不接受的 `*.py` 路径模式返回 1，改用 `rg ... -g '*.py'` 后退出 0。next_task 仍为 T10-D：继续扩大历史来源审计；在保留原始资料和分区身份的前提下接入校验、完善新生成规则、构造并审核新候选。大批题目需另行组织独立模型预审，T10-E 规定的真人 gold 仍未完成。

### L078 — 2026-11-04（北京时间）— T10-D — RESUME

- 按用户指示继续 T10-D，先盘点可追溯的历史开发材料及来源，核对当前生成器与独立来源校验的衔接；保留历史产物和评估盲区。入口检查命令：`rg -n 'next_task|T10-D|L07[5-9]|来源|历史' docs/DEFENSE_PROGRESS_ZH.md docs/PROJECT_STATUS_ZH.md docs/DATA_CATALOG_ZH.md docs/EXPERIMENT_INDEX_ZH.md docs/README.md`；输出较长被截断，继续按需读取具体文件。
- 不查看 V/T 内容或根据攻击成员标签筛选；未完成实际防御效果实验。

### L079 — 2026-11-04（北京时间）— T10-D — CONSERVATIVE_DEV_SOURCE_INVENTORY

- 执行 `& 'D:\ProgramData\Anaconda3\envs\MIAGuard\python.exe' reports/defense_v1/T10/audit_dev_sources_20261104.py`，退出 0，形成[保守来源清单](../reports/defense_v1/T10/dev_source_inventory_20261104_01/manifest.json)：200 篇 D-dev 候选目标、16 篇已知共享背景，共 216 篇；全部 200 篇按候选生成范围保守排除，不表示实际逐篇审核或被人阅读。输入未使用成员标签或攻击结果筛选。
- 使用项目解释器 `python -` 独立检查 22 份输入哈希、输出哈希、ID 唯一性、原有 38 篇全覆盖及排除分区，退出 0，[验证](../reports/defense_v1/T10/dev_source_inventory_20261104_01/validation.json)通过。这只覆盖列出的 T10 来源材料及 candidate06 D-dev 目标，历史其他 prompt 和事件/语义关联仍未全部审计，不证明完整隔离；保留共享背景索引。
- 查找背景文件时误用 `shared_background.jsonl` 导致 Get-Content 报路径不存在，已改用实际 `background_members.jsonl`；`rg ... reports/defense_v1/T10/*.py` 在 Windows 不能展开并退出 2，已用其他清单命令继续。无数据/索引修改。

### L080 — 2026-11-04（北京时间）— T10-D — RELATION_METADATA_GUARD

- 新增缺失 parent 或 duplicate 关联信息时拒绝通过的测试；`& 'D:\ProgramData\Anaconda3\envs\MIAGuard\python.exe' -m pytest tests/test_defense_source_usage.py -q` 首次 2 failed / 6 passed，失败原因是原校验器错误接受缺失信息。实现拒绝后执行 `& 'D:\ProgramData\Anaconda3\envs\MIAGuard\python.exe' -m pytest tests/test_defense_source_usage.py tests/test_defense_dataset.py -q`，退出 0，17 passed。
- 改动为独立校验器的失败关闭约束；没有接入旧全量生成器，也未生成新的正式数据。调用者仍须提供完整关联元数据、实际索引和开发来源历史，且自动关联不能替代事件/语义审核。
- next_task 仍为 T10-D：继续盘点历史开发 prompt 和事件关联，随后为新生成流程接入来源检查与显式版本身份，在 D-dev 先验证正常与攻击规则，再准备新候选及按需外部模型预审；不得以模型预审代替 T10-E 人工 gold。未进行正式防御效果实验。

### L081 — 2026-11-04（北京时间）— T10-D — DEV_COHORT_CHECK

- 使用项目解释器 `python -` 载入 candidate06 目标与背景元数据共 4,500 条、保守清单 216 篇、D-dev 实际索引 1,000 条和开发队列，调用 `validate_normal_source_usage`；退出 0，62 个问题全部通过结构来源检查。未运行生成器、模型或 V/T 评估；校验通过不说明题目内容质量或完整历史/语义隔离。
- 继续 T10-D：清查余下开发材料和事件级关系，再将校验作为新数据生成的强制步骤；目前旧生成器不具备新生成规则，未产出新候选或放行正式实验。

### L082 — 2026-11-04（北京时间）— T10-D — RESUME

- 按 `Get-Content docs/DEFENSE_PROGRESS_ZH.md -Tail 35` 核对 next_task，并检查 `scripts/verify_defense_v1_dataset.py`、`scripts/build_defense_v1_dataset.py`、生成器和来源字段；旧生成器仍将多分区模板一起生成，旧核验固定 candidate06。先以 D-dev 开发队列做独立可追溯的新版本输出与来源门禁，不把它当正式全量数据。
- 继续核查历史材料与不完整来源审计；不按成员标签或效果筛题，不执行 V/T 效果实验。

### L083 — 2026-11-04（北京时间）— T10-D — DEV_EXPORT_GATE

- 按既有开发设计增设仅限 D-dev 已选草稿的导出接口：在线查询与离线答案分离、沿用未改变问题的既有 ID、记录来源版本并强制在写入前调用来源校验，已有输出目录拒绝覆盖；明确不可回放及非人工 gold。该接口不负责生成新问题、不替代全量生成器。
- 测试先执行 `& 'D:\ProgramData\Anaconda3\envs\MIAGuard\python.exe' -m pytest tests/test_defense_dev_export.py -q`，因接口尚不存在 3 failed；实现后运行 `& 'D:\ProgramData\Anaconda3\envs\MIAGuard\python.exe' -m pytest tests/test_defense_dev_export.py tests/test_defense_source_usage.py tests/test_defense_dataset.py -q`，退出 0，20 passed，覆盖索引缺失、拒绝覆盖、重复请求与线上/离线分离。
- 下一步编制实际材料哈希核验入口并对 D-dev 开发队列运行一次非正式导出；清单仍不完整，不能视为终测隔离或人工 gold。

### L084 — 2026-11-04（北京时间）— T10-D — DEV_EXPORT_VERIFIED

- 执行 `& 'D:\ProgramData\Anaconda3\envs\MIAGuard\python.exe' scripts/export_defense_dev_cohort.py --output reports/defense_v1/T10/dev_cohort_export_20261104_01 --version-id t10d-dev-cohort-20261104-01`，退出 0；校验来源材料、数据 manifest 与索引 manifest 摘要，再调用写前来源检查，导出[开发材料](../reports/defense_v1/T10/dev_cohort_export_20261104_01/manifest.json)：30 会话、62 问，线上问题与离线参考分离，沿用未变问题的原 ID，全部 pending、不可正式回放。
- 使用项目解释器 `python -` 独立对照 12 项输入摘要、输出摘要、原队列 62 条问题/证据/答案/来源变体、数量与资格字段，退出 0，[验证结果](../reports/defense_v1/T10/dev_cohort_export_20261104_01/validation.json)通过。结构核验不证明语义独立、内容质量或历史来源完整，导出不产生新题、不更改原索引/样例。
- 尚未补齐其他历史开发 prompt 与事件相似性审计；来源门禁目前只接入此 D-dev 草稿导出，旧全量生成器仍未适配。next_task 仍为 T10-D：继续历史审计及新规则/版本生成，创建更广泛新候选前不得声称隔离完成；T10-E 真人 gold 和正式防御实验未完成。

### L085 — 2026-11-04（北京时间）— T10-D — RESUME / HISTORY_SCOPE

- 按 `Get-Content docs/DEFENSE_PROGRESS_ZH.md -Tail 28` 接续 T10-D，读取 candidate06 `overlap_audit.json` 并列出防御开发 run 和 T10 材料目录；原审计仅覆盖 31 份旧目标文件和 32 份模式，全文/近重复为零不等于片段或事件隔离。本次先清点与开发有关的旧 run、审核与 prompt 的来源映射范围，不读 V/T 效果或按成员标签筛选。

### L086 — 2026-11-04（北京时间）— T10-D — DEV_RUN_SOURCE_AUDIT

- 使用项目解释器 `python -` 对照两次 D-dev 对照运行的 requests、所用原文与保守来源清单，逐条核对 `SOURCE` 前缀和 doc_id；[审计结果](../reports/defense_v1/T10/dev_run_source_audit_20261104.json)状态 passed：7 篇来源的 14 次请求、2 篇来源的 4 次请求均与对应原文一致，来源均已登记，输入摘要已记录。未查看攻击标签、结果或 V/T。
- 查看 E00 和 T09 的运行规格：E00 为旧 train query bank，目标与旧历史来源审计的关系仍需单独核对；T09 为合成 fake 工程数据。未据此声称全部旧 prompt 或跨分区事件隔离已审完。

### L087 — 2026-11-04（北京时间）— T10-D — EVENT_REVIEW_PACKET_READY

- 执行 `& 'D:\ProgramData\Anaconda3\envs\MIAGuard\python.exe' reports/defense_v1/T10/build_event_review_packet_20261104.py`，退出 0，形成 [D-dev 事件关联审核包](../reports/defense_v1/T10/event_pair_review_packet_20261104_01/manifest.json)：31 篇原文及全部 465 个不重复配对，记录输入/输出摘要。另新增[审核交接说明](../reports/defense_v1/T10/event_pair_review_packet_20261104_01/REVIEW_GUIDE_ZH.md)，将其摘要写入 manifest。
- 使用项目解释器 `python -` 核验来源文字摘要、输出摘要、ID 唯一和组合完整性，[validation.json](../reports/defense_v1/T10/event_pair_review_packet_20261104_01/validation.json) passed；只是结构检查，不是内容审核。465 对适合交独立模型预审，未收到结果，不标记完成；仅覆盖 31 篇 D-dev 试点，不包含全 216 篇或 V/T，不能作为跨分区隔离证明。
- next_task 仍为 T10-D：可并行接收模型预审，同时继续 E00/历史 prompt 来源核查、新生成规则与来源门禁适配。模型预审非真人 gold，正式防御效果仍未测。

### L088 — 2026-11-04（北京时间）— T10-D — EVENT_REVIEW_RECEIVED

- 已收到用户提供的 `event_pairs_deepseek-v4.1-flash_20261104_01` 输出；先校验输入/输出摘要、465 对对应关系、字段和原文引用，再人工式逐项审看关联对的理由及来源。单模型预审不得视为真人 gold、完整隔离或防御效果。

### L089 — 2026-11-04（北京时间）— T10-D — EVENT_REVIEW_VALIDATED

- `& 'D:\ProgramData\Anaconda3\envs\MIAGuard\python.exe' reports/defense_v1/T10/verify_event_review_20261104.py` 退出 0，[结构核验](../reports/defense_v1/T10/event_review_validation_20261104.json)通过：31 篇、465 行顺序与输入一致、引文落在对应原文、8 项输入和两项输出摘要一致、字段及分类计数一致。审查 manifest 自身 SHA256 为 `f36388a3a4da46c41fdd67b3d17971e39ec612e27a43e372fc23ca3a9a2f2eba`。
- DeepSeek 声明 1 same_event / 3 related_event / 17 shared / 444 unrelated / 0 uncertain；模型身份来自运行环境声明，未取得供应商不可变快照。我方核验结构与原文短引文，不证明 465 条语义判断都正确，尤其不能以 444 个 high 断言独立。模型审核不等于真人 gold。

### L090 — 2026-11-04（北京时间）— T10-D — EVENT_TRIAGE / SENSITIVITY_GROUPS

- 使用项目解释器 `python -` 输出四组事件级关联的原文并由 Codex agent 核查：[处理决定](../reports/defense_v1/T10/EVENT_REVIEW_TRIAGE_20261104_ZH.md)。Bigley 两篇纳入同一人质事件来源组；其余三组能源材料只能确认主题关联，原文不足以验证同一价格周期或周三/周四相邻，保守纳入敏感性分组，不直接标为同一事件。其余 461 对未独立逐对语义复核。
- 使用项目解释器 `python -` 生成[文章级分组](../reports/defense_v1/T10/event_review_triage_20261104.json)：31 篇核心 30 组、能源敏感性 27 组；合并队列原分组后[会话级分组](../reports/defense_v1/T10/event_review_cohort_grouping_20261104.json)：30 会话基础 27、核心 27、敏感性 26 组。[分组结构核验](../reports/defense_v1/T10/event_review_grouping_validation_20261104.json) passed。与此前更宽主题/人物合并的 23 组规则不同，均是敏感性假设，非已验证独立样本数，尚未执行重采样实验。
- 本审核只覆盖 31 篇 D-dev 试点、不能证明其他来源及跨分区隔离。next_task 仍为 T10-D：继续历史 prompt 和跨分区事件审计方案、新生成规则与来源门禁；T10-E 人工 gold 和正式防御效果尚未完成。

### L091 — 2026-11-04（北京时间）— T10-D — RESUME / E00_SOURCE

- 按台账 next_task 复查 E00 规格、旧候选历史审计实现及相关文件；准备核对 E00 记录的 train 会话文档是否包含在 candidate06 构建时的历史输入，并执行基于 ID/全文/现有 SimHash 规则的离线重叠计数。不读攻击得分或依据成员标签挑选题目；不将片段或事件相似性未查清写成独立性完成。

### L092 — 2026-11-04（北京时间）— T10-D — E00_SOURCE_AUDIT

- `& 'D:\ProgramData\Anaconda3\envs\MIAGuard\python.exe' reports/defense_v1/T10/audit_e00_source_20261104.py` 首次退出 1，误将原始 spec 摘要与运行中重新序列化的副本字节摘要比较；读取 `scripts/run_defense_observe.py` 确认运行器对原 spec 算摘要并重新保存副本，`reports/defense_v1/T05/observe_spec.json` 摘要匹配 manifest 且 JSON 内容与副本一致。修正核验方法后同一命令退出 0，[目标源审计](../reports/defense_v1/T10/e00_source_audit_20261104.json)记录 10 请求、1 目标；该目标在 3,600 候选目标和 900 背景中 ID、规范化全文、SimHash 距离 ≤3 匹配均为 0。
- 通过项目解释器 `python -` 逐条对照 10 请求的实际检索 ID 和上下文，11 篇不同来源全部与旧目标文件对应原文一致；[检索源审计](../reports/defense_v1/T10/e00_retrieved_source_audit_20261104.json)将 11 篇与 4,500 候选全文比较，ID、规范化全文、SimHash 距离 ≤3 的匹配均为 0。旧目标文件摘要与 candidate06 manifest 一致；过程未按成员标签或攻击结果筛选，未输出分区级内容。
- 两次 `apply_patch` 未匹配原脚本内容、一次 `python -` 替换因拼写不一致触发断言，均未写入更改；最终以小补丁修复审核脚本的常量拼写。以上仅覆盖 E00 本次目标与已记录的检索上下文，片段、事件、语义及其他历史 prompt 未排除，不能证明整体隔离。

### L093 — 2026-11-04（北京时间）— T10-D — MASKED_RULE_COMPONENT

- 按 T10-D 添加 `draft_unique_masked_query` 独立组件：从文本中按顺序选择不区分大小写仅出现一次的四个及以上英文字母词，排除数字与模板本身出现的词；同次输出保持 JSON 要求的提示及对应离线答案；已有 `[MASK]` 或无合格词直接拒绝。此规则只保证结构，不保证词语可从上下文恢复或攻击有效，需后续内容预审。
- 先执行 `& 'D:\ProgramData\Anaconda3\envs\MIAGuard\python.exe' -m pytest tests/test_defense_masked_draft.py -q`，接口缺失导致 6 failed；实现后第一次回归 25 passed / 1 failed，发现测试错误把指令中解释用途的 `[MASK]` 也当成正文遮蔽位；修正为仅检查正文。再次执行 `& 'D:\ProgramData\Anaconda3\envs\MIAGuard\python.exe' -m pytest tests/test_defense_masked_draft.py tests/test_defense_dev_export.py tests/test_defense_source_usage.py tests/test_defense_dataset.py -q`，退出 0，26 passed。
- 组件尚未接入旧版或新版本全量生成器，未对真实候选生成或宣称攻击效果；对没有合适词的文档后续须记录排除原因，禁止回退到泄漏词。next_task 仍为 T10-D：继续历史 prompt/事件审计、各攻击和正常题规则、整合生成器及版本化候选。

### L094 — 2026-11-04（北京时间）— T10-D — SMALL_MASKED_PILOT_BEGIN

- 按台账和 T10-D 计划继续，准备对两轮攻击预审已用的 4 篇 D-dev 来源应用唯一遮蔽词规则；使用来源身份而非成员标签或攻击效果选取，保存新请求身份、参考答案、原文、排除及输入摘要。先验证结果并逐条检查质量，再据观察评估规则和审核工作量；不改变旧数据或运行正式实验。

### L095 — 2026-11-04（北京时间）— T10-D — MASKED_SMALL_PILOT

- `& 'D:\ProgramData\Anaconda3\envs\MIAGuard\python.exe' reports/defense_v1/T10/build_masked_rule_pilot_20261104.py` 退出 0：对两轮攻击预审的 4 个 D-dev 来源生成 4 个 Masked 草稿，0 生成排除；不按成员标签/攻击结果选择，问题与离线答案分离，新建身份，见[清单](../reports/defense_v1/T10/masked_rule_pilot_20261104_01/manifest.json)。项目解释器 `python -` [结构核验](../reports/defense_v1/T10/masked_rule_pilot_20261104_01/validation.json)通过，逐项验证答案还原、无明文泄漏、身份、输入输出摘要和 pending；第一次核验的链式数量判断有漏洞，已改为逐项相等后重新运行通过。
- Codex agent 逐条阅读 4 篇和草稿，发现均遮蔽标题开头，唯一性不保证上下文可恢复；[内容核查](../reports/defense_v1/T10/masked_rule_pilot_20261104_01/AGENT_REVIEW_ZH.md)建议进一步改写或排除，非真人 gold。4/4 风险发现来自便利样本，不能作为全量发生率；未调用模型或防御。

### L096 — 2026-11-04（北京时间）— T10-D — EXPLICIT_MASK_SELECTION

- 添加测试并运行 `& 'D:\ProgramData\Anaconda3\envs\MIAGuard\python.exe' -m pytest tests/test_defense_masked_draft.py -q`，因候选列表接口不存在 1 failed / 6 passed；实现列出唯一候选词及其字符位置、按指定词生成问题/答案的接口后，执行 `& 'D:\ProgramData\Anaconda3\envs\MIAGuard\python.exe' -m pytest tests/test_defense_masked_draft.py tests/test_defense_dev_export.py tests/test_defense_source_usage.py tests/test_defense_dataset.py -q`，退出 0，27 passed。候选词仍需语义判断，不能自动合格。
- `& 'D:\ProgramData\Anaconda3\envs\MIAGuard\python.exe' reports/defense_v1/T10/build_masked_selected_pilot_20261104.py` 退出 0，记录 4 篇候选词清单；采用前次预审建议生成 `sparkling`、`Belichick` 两条新请求，另两篇未选定。项目解释器 `python -` [核验](../reports/defense_v1/T10/masked_selected_pilot_20261104_01/validation.json)通过，核对新旧身份、位置信息、无泄漏和来源；[内容核查](../reports/defense_v1/T10/masked_selected_pilot_20261104_01/AGENT_REVIEW_ZH.md)保留同义词、答案不唯一风险，两条仍 pending、不可正式回放。
- 首批生成后源码曾更改，首批 manifest 的源码摘要代表当时版本，当前无 Git 且未保存该旧版本代码快照，不能凭当前源码证明字节级复现；第二批已保存生成器和模块快照并核验摘要。未修改 candidate06、旧审核包或索引。
- 新增[试点与审核工作量草案](../reports/defense_v1/T10/PILOT_SCOPE_AND_REVIEW_BUDGET_20261104_ZH.md)：已有 30 正常会话，加计划最多 8 来源 × 4 攻击的开发试点；是预算建议，不是已生成数量、正式样本量或统计功效结论。后续实际计时后估算审核量。next_task 仍为 T10-D：继续攻防题规则与来源审计，明确小批抽样并先验证，再准备批量模型预审；正式人类 gold 和效果实验未完成。

### L097 — 2026-11-04（北京时间）— T10-D / DOC — CHANGE / REUSE_FIRST

- 根据用户关于第一阶段数据复用的讨论，核对状态、数据目录、实验索引、规格、计划和协议。协议已有旧 train 联调条款，但当前执行入口偏重全量重建，容易误解为四类攻击必须重做。现明确 T10-D 先检查旧 train 的查询/原文/原索引/攻击评分输入和正常答案证据覆盖，再按缺口补建；保留新保留集与正式 gold 门禁。
- 实际命令为 `Get-Content` 顺序读取入口文件、`rg` 查找旧数据及 gold 相关条款，再读取旧 bank manifest、split 元数据和旧索引 manifest；尚未完成逐条复用验收或运行新的防御实验。接下来只做支持文档修订的 train 字段盘点，并同步有效文档和 next_task。

### L098 — 2026-11-04（北京时间）— T10-D / DOC — REUSE_FIELD_INVENTORY_AND_SYNC

- 使用项目解释器 `python -` 核对旧查询文件 SHA256，仅统计原 split 的 accepted train 行，生成[文档修订依据](../reports/defense_v1/T10/legacy_reuse_document_evidence_20261104.json)：60 篇、3,575 查询（benign 300，Direct/S²/Masked 各 300，IA 2,375）。攻击 payload 已有部分评分输入；300 正常题缺少第二阶段标准答案/可回答性/证据/审核字段；其中 150 条目标源在旧索引、150 条不在，但索引存在性不等于问题可回答性。只盘点字段和 ID，不看 V/T 查询内容或攻击得分，不按成员标签挑题，也未逐题验收复用。
- 新增[第一阶段数据复用规则](DEFENSE_DATA_REUSE_ZH.md)，同步规格、协议、主计划、台账、项目状态、数据目录、实验索引、文档索引及试点预算。规格/计划/协议仍为 v1.1 原路径并记 11 月 4 日补记；先完成旧 train 复用覆盖审计，再按缺口补标/改写/新增，不强制先重做四类攻击。旧索引、原成员身份和会话须绑定，旧检测分数不能替代新回答结果；旧 validation/test 不充当新独立终测。
- 项目状态页合并过时的零散更新，详细历史仍保留本台账和原产物。主计划新增复用验收、小批工程联调、按缺口确定预算三项未勾选待办；既有 DONE 状态和 G2–G4、T10-E/T11/T12 正式依赖不变。此轮仅字段盘点/文档修订，未适配运行器、未生成新查询、未完成真人 gold、未启动真实回答比较。
- next_task=T10-D（IN_PROGRESS），具体接续：核对旧 train 的逐类型原文/索引/评分输入/正常证据/会话与评估器兼容性，输出可复用、需补标、需改写、不适用的覆盖清单；随后登记固定小批和运行前条件。备选 8 来源/32 新攻击计划需结合覆盖结果决定。

### L099 — 2026-11-04（北京时间）— DOC — REUSE_DOCUMENTS_VERIFIED

- 使用项目解释器 `python -` 核查 10 份本次执行/导航文档的本地链接、旧数据输入摘要、next_task 与未勾选复用待办。首次发现试点预算文档新增链接多退一级导致不存在，检查退出 1；修正相对路径后重查通过，旧数据 5 项输入摘要未变化。
- [文档核验报告](../reports/defense_v1/planning/document-reuse-audit-20261104.json)保存文档和字段盘点摘要、链接核验范围与限制。本次未修改业务代码、数据内容或冻结模型，无需代码回归；没有完成逐题复用验收或启动新的防御运行。后续仍按 T10-D 的旧 train 复用覆盖审计接续。

### L100 — 2026-11-04（北京时间）— T10-D — CHANGE / LATEST_QUERY_BANK_CHECK

- 用户要求确保使用最新第一阶段数据。`Get-ChildItem data/query_banks` 与 `Get-Content` 两版本 manifest 确认存在 `ag_news_queries_v2`，完成时间 2026-08-31，7,632 查询、100 篇；前述 v1 是当前冻结 Judge 对照的来源，不能将其称为最新查询库。开始核对 v2 文件摘要、原划分关联、攻击继承、正常数据审核状态及 train 字段；核验通过后将后续复用覆盖入口明确为 v2 train，历史 v1 结果保留原身份。
- 本步骤不将 v2 自动当正式 gold，不混用 v1 分数或假定两个 split 的逐文档分配相同；未启动模型/防御运行。

### L101 — 2026-11-04（北京时间）— T10-D — V2_IDENTITY_VERIFIED / REUSE_ENTRY_SELECTED

- 使用项目解释器 `python -` 校验两版 queries SHA256、数量、ID 唯一性、split 所指 bank/摘要、文档分配、文档表和攻击记录对应；[版本核验报告](../reports/defense_v1/T10/query_bank_version_audit_20261104.json) passed。v2 为当前发现的最新完整非 smoke 库：100 篇、7,632 条，正常 2,176，Direct/S²/Masked 各 500，IA 3,956；与 v1 全部 5,456 条攻击逐记录一致、文档表及各 split 的文档 ID 集一致。
- v2 train 60 篇、4,579 accepted 查询：正常 1,304、Direct/S²/Masked 各 300、IA 2,375。正常 payload 有意图/类别/难度/困难场景，仍无标准答案/可回答性/证据/真人审核字段；653 条目标源在旧索引、651 条不在，均不能自动判为可答或不可答。manifest 的 139 条正常审查样本整体仍 pending，尚未逐条审核。只输出 train 字段统计，V/T 仅机械比较 ID 集，不查看其查询内容或效果。
- 项目解释器 `python -` 写入[复用选择清单](../reports/defense_v1/T10/legacy_reuse_selection_20261104.json)：指定 v2 bank、v2 split、train、原 source_run/索引文件摘要，状态 identity_verified_reuse_acceptance_pending；不是可运行 benchmark spec，不放行 gold 或正式回放。核对原 Judge v3 train manifest 的 identity 确为 v1 bank/v1 split，冻结模型和已有指标保持原身份，不能改为 v2 或自动沿用 Session trace。
- 同步数据复用说明、设计规格、协议、计划、台账、项目状态、数据目录、实验索引、README 和查询库使用说明；v1 盘点和旧实验作为历史保留。当前 next_task 仍 T10-D：对选定的 v2 train 做逐题/逐组复用覆盖验收、缺口和运行器适配核查；实际运行需显式核对 v2 bank/split，不能沿用旧默认而声称使用最新数据。本次没有修改 queries/split/模型/业务代码或运行模型。

### L102 — 2026-11-04（北京时间）— DOC / T10-D — V2_NAVIGATION_VERIFIED

- 使用项目解释器 `python -` 检查 11 份文档本地链接、版本核验的全部输入摘要和选择清单的 6 份文件摘要、v2 train/v1 历史实验身份，退出 0；[文档与版本接续核验](../reports/defense_v1/planning/document-v2-reuse-audit-20261104.json) passed。修订的导航不改变历史 v1 manifest/模型或 v2 原查询。
- 当前实际完成范围为版本身份核对、字段统计及选择入口；复用验收、适配和真实模型运行仍待执行。next_task=T10-D（IN_PROGRESS），从最新 v2 train 覆盖审计接续。

### L103 — 2026-11-05（北京时间）— DOC — VERSION_REGISTRY_BEGIN

- 用户要求集中记录最新数据、实验及开发框架版本，避免把历史来源当当前入口。按规定顺序读取项目状态、数据目录、实验索引、文档索引及台账，检查根 AGENTS 与 pyproject；已存在分项目录但没有统一的版本角色清单。准备新增统一入口，以原始 manifest/冻结 JSON 为核对依据；按用途区分“当前选择”“已完成实验”“候选/诊断”“历史中断”。
- 当前包版本 pyproject 为 0.1.0；它不能证明当前工作区源码身份，开发规格/计划/协议 v1.1 也不是代码发布号。接下来核查并记录原始身份和摘要，文档任务不替代 T10-D 数据验收或正式效果实验。

### L104 — 2026-11-05（北京时间）— DOC-02 — VERSION_REGISTRY_COMPLETE

- 新增[统一版本总表](CURRENT_VERSIONS_ZH.md)，修订号 2026-11-05-r01，区分最新查询库 v2/当前复用 train、已完成 Judge v3 所用 v1、candidate06/小样本诊断、冻结模型/配置、开发文档 v1.1 与包声明 0.1.0。更新 AGENTS、项目/文档 README、状态、数据目录、实验索引、复用说明和规格/计划/协议入口，规定选择版本先核对总表及实际 manifest/摘要。未将目录日期或版本号大小当作有效结果证明。
- 项目解释器 `python -` 核对选定 bank/split 与选择清单摘要、v3 三分区 manifest/summary/records、冻结模型与 observe 配置，以及包内/pyproject 声明，生成[版本快照](../reports/defense_v1/planning/current_versions_snapshot_20261105_01.json)：53 份身份文件摘要，186 个源代码/配置文件指纹。源码指纹不包含源码内容、依赖环境或权重，不能恢复旧代码，不伪造 commit。
- `git rev-parse --is-inside-work-tree` 报 not a git repository，未初始化仓库。`Get-Content` 检查历史 20260929 v2 中断目录时报告无 benchmark_summary，符合其未完成状态；没有将其提升为最新有效结果。随后项目解释器 `python -` 独立核验快照全部摘要、角色、12 份文档链接与 AGENTS 入口，[核验结果](../reports/defense_v1/planning/current_versions_registry_validation_20261105.json) passed。
- DOC-02 标 DONE，仅表示统一版本入口及身份核验完成。本次未修改业务代码/数据/冻结模型，未运行代码回归或模型/防御实验；总表尚非运行器自动拦截器，实际运行仍须显式核对参数与身份。T10-D 继续 IN_PROGRESS，从 v2 train 复用覆盖审计接续。

### L105 — 2026-11-05（北京时间）— T10-D — V2_REUSE_COVERAGE_BEGIN

- 按用户“开始”指令及版本总表 r01、选择清单接续 v2 train 的 4,579 条复用覆盖审计。已顺序读取状态/数据/实验/总表/台账和 T10-D 计划，检查当前 benchmark 的四攻击评分和 live 输入契约；先核对实际数据和评分源代码，再定义自动检查范围。暂不调用模型、不读 V/T 效果或按成员标签/攻击成功选题。
- 初次 `rg` 错将 query_bank 包当单文件且误用不存在的 attacks 目录，报路径不存在；已用 `rg --files src/miaguard` 找到 `query_bank/`、`direct_rag_mia.py`、`s2_mia.py`、`masked_mia.py`、`ia_attack.py` 后继续。审计结果应区分结构可复用、补标、改写和语义待审，不能将结构通过标成人工 gold。

### L106 — 2026-11-05（北京时间）— T10-D — V2_STRUCTURAL_REUSE_AUDIT_COMPLETE

- `& 'D:\ProgramData\Anaconda3\envs\MIAGuard\python.exe' reports/defense_v1/T10/audit_v2_train_reuse_20261105.py` 退出 0，形成[完整自动结构审计](../reports/defense_v1/T10/v2_train_reuse_audit_20261105_01/manifest.json)及 4,579 行处置清单：60 篇源文/查询摘要/原索引成员身份及文本无错误；2,975 条可保留基础内容但需适配/语义复核，1,304 正常需补标，300 Masked 需格式/泄漏修订，0 结构性不适用。所有行仍 pending 语义审核，非正式 gold。
- 300 Masked 均未要求现有评分器需要的 JSON，其中 130 条（26 篇 × 5 变体）正文仍出现缺词，35 条（7 篇）重复答案值列为复核信号。IA 206 条（45 篇）开放问句配分类回答要求需优先复核；其余 IA 未因结构通过被当作正式可用。S² 的当前评分目标可从原文补足，不需为此重写原题。旧 multi-mask 基线保留，不转换为先前的单 mask 组件。
- 实际调用现有 QueryBank 载入和 train 会话布局器：970 个会话覆盖全部 4,579 查询，699 五轮 / 271 四轮，布局无丢漏；不验证自然递进或真实 Session 防御。项目解释器 `python -` 独立对照输入 12 项及输出 3 项哈希、逐条 ID/顺序/处置规则和审核资格，[validation.json](../reports/defense_v1/T10/v2_train_reuse_audit_20261105_01/validation.json) passed。
- 另以纯合成的相同 Masked 答案分别构造文本和 JSON，调用现有评分函数得到 0/1，验证解析契约差异；不调用模型，不是攻击成功率或防御效果。七个[Codex agent 案例核查](../reports/defense_v1/T10/v2_train_reuse_audit_20261105_01/small_agent_case_review.jsonl)检查前三组通用正常重复句、三个 IA 形式冲突和一个 Masked 大小写重现；其余语义未逐条裁决。正常 12 组同文本涉及79条，仅提示来源指代需检查，不自动排除。
- [通俗报告](../reports/defense_v1/T10/v2_train_reuse_audit_20261105_01/REUSE_REPORT_ZH.md)记录限制、复用范围和恢复顺序。自动结构子步骤完成，T10-D 仍 IN_PROGRESS：下一步优先按来源修复 Masked / 复核 IA 疑点、固定正常小批补标范围并核验导出适配；不直接放行正式 E01/T10-E。

### L107 — 2026-11-05（北京时间）— T10-D — TARGETED_REVIEW_PACKET / STATUS_SYNC

- 项目解释器 `python -` 从已审计 train 按固定疑点选择构建[独立预审包](../reports/defense_v1/T10/v2_reuse_review_packet_20261105_01/manifest.json)：206 IA 开放问句疑点、60 Masked 来源方案（各五问，共300问）、60 篇源文，合计266审核单元；无成员标签或攻击得分。新增[审核指南](../reports/defense_v1/T10/v2_reuse_review_packet_20261105_01/REVIEW_GUIDE_ZH.md)，明示 IA 改题要重判源文 ground truth、Masked 保留原编号和数量，攻击者知道原文、不要求仅凭掩码上下文唯一推导；不是沿用正常问答验收尺度。
- 再执行项目解释器 `python -` 校验 ID/顺序、源文摘要、输入输出摘要、覆盖范围和禁止字段，[validation.json](../reports/defense_v1/T10/v2_reuse_review_packet_20261105_01/validation.json) passed。数量较大，可交用户指定的独立模型 agent 分批预审；目前 review_pending，未收到结果。该包不包括剩余2169条 IA、Direct/S²语义或1304正常 gold，不能用本包完成代替全量审核。
- 已将计划自动结构子步骤勾选，语义/gold/适配项保留待办；同步状态、数据目录、实验索引、复用说明和版本导航，当前总表 r02，数据/模型选择不变。本次仅审计脚本和文档/审核材料，没有修改业务代码/原数据/冻结模型，也没有调用生成模型或跑防御效果。下一步继续 T10-D：接收该包预审并核验修订、固定正常小批补标与适配范围，完成条件满足后才安排 engineering_only 真实回答联调。

### L108 — 2026-11-05（北京时间）— T10-D / DOC — AUDIT_AND_REGISTRY_R02_VERIFIED

- 使用项目解释器 `python -` 独立核验本轮审计输入/输出、assessment 摘要、预审包身份、计划勾选及文档导航，生成[总表 r02 验证](../reports/defense_v1/planning/current_versions_registry_validation_20261105_r02.json) passed；[r02 快照](../reports/defense_v1/planning/current_versions_snapshot_20261105_02.json)登记69份身份/审计材料，186个业务源代码/配置文件指纹与r01一致。只推进自动结构子步骤，没有把语义待审、外部预审或正式门禁勾为完成。
- 本轮不需要业务代码回归；实际执行了审计、原布局器覆盖检查和纯合成评分解析契约检查，没有调用生成模型或产生新的防御效果。T10-D 接续内容修复/审核与适配；模型预审包已就绪，须收到输出后再核验和整合。

### L109 — 2026-11-05（北京时间）— T10-D — V2_REUSE_EXTERNAL_REVIEW_RECEIVED

- 收到 `external_review/v2_reuse_deepseek-v4.1-flash_20261105_01`：对方声明266单元完成。按入口读取状态、目录、实验索引、总表r02、台账，再读原交接契约及实际manifest/summary；尚未采纳或标记gold。开始核对摘要、206/60身份、IA引文和Masked还原/无泄漏/五查询一致性。
- 对方统计 IA 0 accept /67 rewrite /115 reject /24 uncertain；Masked 60 rewrite，不能直接将判定当作最终排除。首条Masked说明与实际换词不一致，需核查。根据并行审查流程安排两个只读Codex子任务分别检查IA语义和Masked内容，主流程做结构和身份校验；所有判断仍属模型/agent预审，未调用防御服务或读取攻击结果。

### L110 — 2026-11-05（北京时间）— T10-D — V2_EXTERNAL_REVIEW_STRUCTURE_VERIFIED

- `& 'D:\ProgramData\Anaconda3\envs\MIAGuard\python.exe' reports/defense_v1/T10/verify_v2_reuse_review_20261105.py` 退出0，[结构验证](../reports/defense_v1/T10/v2_reuse_review_integration_20261105_01/structural_validation.json) passed：206/60行逐项同序、10项输入/3项输出摘要、字段/判定契约、IA同源逐字引文、全部Masked逐字还原/编号/五查询/JSON要求/正文及指令无残余缺词。保留7个大小写归一重复答案、3个含数字词及1个非顺序编号来源警告。供应商不可变模型身份未取得，不据metadata声明自动当真人gold。
- Codex两个只读子任务分别逐条核查67个IA rewrite和60个Masked方案；根流程再次核对11个IA问题项及重点Masked来源。代码/源文未修改、未读攻击效果或V/T查询内容。引文存在不等于命题被支持，审阅结论仍为agent判断。

### L111 — 2026-11-05（北京时间）— T10-D — LOCAL_TRIAGE / PENDING_ATTACK_OVERLAY

- [IA处理](../reports/defense_v1/T10/v2_reuse_review_integration_20261105_01/IA_TRIAGE_ZH.md)：67个rewrite中发现11处依据/模态/对象问题，根流程据源文局部修订6条、暂缓5条，另56条仅保留为pending建议；共62条IA候选（61 yes/1 no）。115 reject、24 uncertain与5条暂缓共144条保留待裁决，不永久删除。全库其余2169 IA仍有751 unknown，不能因本子集无unknown就声称全库没有unknown。
- [Masked差异](../reports/defense_v1/T10/v2_reuse_review_integration_20261105_01/masked_triage.jsonl)：26个方案共变更35个词槽，其中原泄漏33槽、其他2槽为选择调整；外部26条reason误写新词→新词，根流程另记实际旧→新，不篡改外部输出。补记7来源归一重复、3含数字、1非顺序编号、拼写/站点/标题/截断警告。34方案仅改JSON契约，60方案结构保留，未当作人工gold。
- `& 'D:\ProgramData\Anaconda3\envs\MIAGuard\python.exe' reports/defense_v1/T10/build_v2_reuse_review_overlay_20261105.py` 退出0，新建[待审攻击叠加层](../data/defense_datasets/legacy_v2_reuse_overlay_20261105_01/manifest.json)：362新身份请求（62 IA +300 Masked）、144暂缓IA、原文及lineage；单查询临时会话，不是最终多轮布局。在线白名单与离线成员/参考信息分离，全部pending，replay_eligible=false、formal_effect_eligible=false；不替换原v2 bank/原索引。
- 项目解释器 `python -` 独立核对13输入/6输出摘要、362新旧ID/题答对应/原索引真值、300Masked还原与无泄漏、审核门禁及144暂缓非永久排除，[validation](../data/defense_datasets/legacy_v2_reuse_overlay_20261105_01/validation.json) passed。[接收报告](../reports/defense_v1/T10/v2_reuse_review_integration_20261105_01/INTEGRATION_REPORT_ZH.md)说明限制。未调用生成模型或测量防御效果；下一步T10-D固定v2正常小批答案/证据补标、继续剩余语义和适配核验。

### L112 — 2026-11-05（北京时间）— T10-D / DOC — INTEGRATION_R03_VERIFIED

- 项目解释器 `python -` 核验外部/本地整合清单、叠加层输入输出、[总表r03快照](../reports/defense_v1/planning/current_versions_snapshot_20261105_03.json)的92份文件身份与186个未变化业务源代码/配置指纹、14份导航文档链接及计划勾选，[最终核验](../reports/defense_v1/planning/current_versions_registry_validation_20261105_r03.json) passed。总表与数据目录标明原v2是完整库、overlay是待审攻击叠加层，不能混用身份或数量。
- 本轮没有修改业务执行代码或冻结文件，未调用模型服务/攻击/防御后端，未做代码回归；实际完成为外部审核接收、agent源文复核、6条局部改写、362条待审草稿及144条暂缓保留的工程整合。T10-E、T11正式评估器和G2–G4未完成，next_task仍T10-D：正常小批补标与剩余语义/适配。

### L113 — 2026-11-05（北京时间）— T10-D — CHANGE / FAST_ENGINEERING_PILOT

- 用户明确要求快速进入试验，不继续扩大数据构建。按既有协议允许的engineering_only开发路径，收紧为少量v2 train正常题+现有攻击材料的B0无防御/B2风险拒答真实回答对照；先建立固定小批、核对最少答案/证据和运行身份，尽快执行，不以正式数据未齐为由阻止不依赖它的工程联调。正式T10-E/E01/G2等不放宽，研究效果结论仍须后续验收。
- 已按入口读取状态/目录/实验/总表/台账，检查live工厂和benchmark配置；configs/defense/experiments目录当前不存在，不能执行计划中的虚构默认配置。安排两个独立子任务并行准备4条源文支持的正常题、只读核对BF16模型/依赖/GPU，根流程准备攻击小批和准确运行spec。所有选择不看攻击/防御结果；不把历史v1结果改标v2。

### L114 — 2026-11-05（北京时间）— T10-D — FAST_PILOT_SCOPE_PREREGISTERED

- 为尽快取得真实回答，预定首批4条源文支持的正常题、2个攻击目标（按原索引在/不在各1个，以固定seed 20261105在可用源池内稳定排序选择），每目标Direct/S²/Masked/IA各1条，共12请求×B0/B2=24服务处理。原源池仅按已有审核质量标记和四攻击输入齐备过滤，不依据模型输出或防御成绩选择；按索引成员状态预先分层仅为确保两类均有覆盖，不是按攻击成功选题。
- 使用原BF16 Qwen、原索引和冻结Judge/Query-only阈值，不为速度默默改Q4/阈值。每条为独立单查询会话，本批只能观察Query-only阶段，不能声称检验Session/fusion或统计有效的成员泄露下降。无真人gold，小规模agent核对只支撑工程比较与案例阅读，正式数据/实验门禁保持未完成。运行前将锁定实际IDs、配置和摘要。

### L115 — 2026-11-05（北京时间）— T10-D — FAST_PILOT_FIXED / RUN_BEGIN

- `& 'D:\ProgramData\Anaconda3\envs\MIAGuard\python.exe' reports/defense_v1/T10/build_fast_live_pilot_20261105.py` 退出0，形成[固定小批](../data/defense_datasets/legacy_v2_fast_pilot_20261105_01/manifest.json)：4正常（00000050/00000149/00000220/00000224），攻击目标按预登记规则选原索引内00000250、索引外00008944，各Direct/S²/Masked/IA一题；12独立单查询×B0/B2=24事件。selection_seed=20261105，实际模型seed保持原配置20260715，max_answer_tokens=128，top_k=4。
- 正常题由Codex agent核对题面、必要事实和逐字证据，初始只读检查曾显示少量membership字段及split test头，未用于选择或读取效果；原题未改写、答案仍非真人gold。另一个子任务实查GPU A5000余约21GB、BF16模型分片与依赖/旧FAISS/冻结身份可用，未启动模型。根流程项目解释器 `python -` [运行前核验](../data/defense_datasets/legacy_v2_fast_pilot_20261105_01/preflight.json) passed_no_generation，确认输入摘要/在线字段/两类目标/完整spec。无业务代码修改，无需扩大数据。
- 即将执行 `& 'D:\ProgramData\Anaconda3\envs\MIAGuard\python.exe' -u scripts/run_defense_v1_benchmark.py --experiment-spec data/defense_datasets/legacy_v2_fast_pilot_20261105_01/experiment_spec.json --output-root data/defense_v1_runs/fast-v2-b0-b2-20261105-01 *> reports/defense_v1/T10/fast_live_pilot_20261105_01/run.log`；新run_id=fast-v2-b0-b2-20261105-01。状态以实际manifest/分片/退出为准，未完成不写效果结论。工程资格仅限这12题，parent overlay/正式gold与门禁保持未放行。

### L116 — 2026-11-05（北京时间）— T10-D — FAST_LIVE_RUNNING

- 已按L115命令启动实际live benchmark，工具exec session_id=12443，Windows PID=176528。实际manifest状态running，started_at=2026-11-05T02:51:33.088554+00:00（北京时间10:51:33）；日志显示BF16四分片已加载。当前未完成，不统计效果。运行产物 `data/defense_v1_runs/fast-v2-b0-b2-20261105-01/`，日志 `reports/defense_v1/T10/fast_live_pilot_20261105_01/run.log`。

### L117 — 2026-11-05（北京时间）— T10-D — FAST_LIVE_COMPLETE / SCORING_CAVEAT

- L115真实命令退出0；run_manifest.status=completed、outcome=valid，结束于2026-11-05T02:54:21.553083+00:00（北京时间10:54:21），耗时约168秒。metrics核对24/24完成、failed=0/skipped=0/missing_attack_scores=0，24会话分片与24个实际artifact齐全；本次使用原BF16与冻结阈值，未改业务代码、原v2/overlay/模型。
- 已读真实输出：B2正常0/4拒答、攻击6/8拒答；4组正常回答逐字一致。Codex子任务按锁定rubric/实际交付context核对正常8回答，根流程读全部8回答，均满足必要事实；属agent评价，非真人gold。
- 发现Masked严格评分的诊断缺口：B0成员裸JSON数组实际5/5恢复、非成员围栏JSON实际2/5恢复，当前scorer均折成0；不能把原分数0当成无信息恢复。保留原始输出/分数，另作格式/逐词诊断，不根据本批结果改阈值/挑题。IA Unknown与拒答、S²拒答相似度也须分开解释。接续形成可复查报告、同步当前状态/版本；小样本不放行T10-E/G2/正式E01。

### L118 — 2026-11-05（北京时间）— T10-D — FAST_RESULTS_VALIDATED / EXECUTION_PRIORITY

- `& 'D:\ProgramData\Anaconda3\envs\MIAGuard\python.exe' scripts/evaluate_defense_v1.py --run-dir data/defense_v1_runs/fast-v2-b0-b2-20261105-01 --output reports/defense_v1/T10/fast_live_pilot_20261105_01/engineering_evaluator_raw.json --analysis-role engineering_only` 退出0，保留原工程评估；其中整句EM和两目标AUROC不作效果结论。
- `& 'D:\ProgramData\Anaconda3\envs\MIAGuard\python.exe' reports/defense_v1/T10/finalize_fast_live_pilot_20261105.py` 退出0，逐项重算运行/固定数据/配置/源码/24artifact摘要、在线字段与24事件覆盖、8正常/16攻击核查对应关系；生成assessment.json、verification.json和FAST_PILOT_REPORT_ZH.md。报告相对链接层级在最终导航验证前更正，未改原运行/分数/标签。独立agent结果经根流程核对实际输出、引用证据和原评分，不是第二独立模型或真人裁决。
- 实测B0/B2正常各4/4满足事实且4对逐字一致，攻击deny 0/8→6/8；成员原文交付4/4→0/4，动作记录不能代替泄露统计。Masked B0严格分数0但内容恢复5/5、2/5；另作诊断而不覆盖。请求中位耗时约1.07→11.76秒，仅一次顺序运行，含加载/长度差异。无Session/fusion、自适应或总体统计结论。
- 按用户加速要求，正式next_task仍T10-D，但工程接续改为“现有输出评分诊断→同批过滤/摘要对照→按需要小量补困难/三轮”，不先处理144条暂缓或全量新数据才开试验。主计划/协议/规格、状态、数据、实验索引与版本总表同步。T10-E、正式T11/T12与G2–G4保持未完成。本次业务代码不变，不因报告生成扩大跑测试；实际模型试验与身份验证均已完成。

### L119 — 2026-11-05（北京时间）— DOC / T10-D — FAST_RUN_REGISTRY_R04_VERIFIED

- 项目解释器 `& 'D:\ProgramData\Anaconda3\envs\MIAGuard\python.exe' -` 独立重算r04快照116份身份/产物、186份业务代码/配置、真实运行验证中全部摘要及15份入口/执行/结果文档的630个本地链接，退出0；结果见 `reports/defense_v1/planning/current_versions_registry_validation_20261105_r04.json`。源码指纹与r03一致；新增r04快照保留r03及原run引用的r03身份，不改旧库或阈值。报告链接层级和维护记录表格空行已在最终导航核验前修正。
- 另一个Codex子任务只读重算报告中的动作/格式诊断/延迟，并核对台账与计划，没有发现数字或门禁不一致；不是独立第二模型或人评。本次不需要用户再审小批，现有24请求结果可直接阅读。T10-D保持IN_PROGRESS，下一工程优先为评分诊断与同批过滤/摘要比较，不再将扩大数据构建列为前置；正式E01与gold另按协议验收。

### L120 — 2026-11-05 — T10-D — FILTER_SUMMARY_BEGIN

- 核对r04全部身份文件；复用12条固定请求和原BF16、索引、阈值、seed，新配置 `reports/defense_v1/T10/fast_live_pilot_20261105_01/experiment_b5_b6.json`，B5触发时过滤检索Top-1并回填，B6触发时摘要；目标定位仅工程假设。使用新run `fast-v2-b5-b6-20261105-01`，24事件、engineering_only，非正式实验。严格评分器仅接受无围栏对象answers；已有独立逐词诊断保留，本次运行后同样区分格式与恢复。

### L121 — 2026-11-05 — T10-D — FILTER_SUMMARY_RUNNING

- 执行 `& D:\ProgramData\Anaconda3\envs\MIAGuard\python.exe -u scripts/run_defense_v1_benchmark.py --experiment-spec reports/defense_v1/T10/fast_live_pilot_20261105_01/experiment_b5_b6.json --output-root data/defense_v1_runs/fast-v2-b5-b6-20261105-01 *> reports/defense_v1/T10/fast_live_pilot_20261105_01/run_b5_b6.log`，工具session=87875；状态以run_manifest和日志为准，未完成不汇报结果。

### L122 — 2026-11-05 — T10-D — MASKED_DIAGNOSTIC

- 执行 `& D:\ProgramData\Anaconda3\envs\MIAGuard\python.exe reports/defense_v1/T10/diagnose_masked_fast_pilot.py data/defense_v1_runs/fast-v2-b0-b2-20261105-01 reports/defense_v1/T10/fast_live_pilot_20261105_01/masked_diagnostic_b0_b2.json` 退出0，独立记录严格分、外层围栏/数组格式、逐位置恢复与拒答/解析失败；复现5/5、2/5、拒答0/5。另用项目解释器 `python -` 核验数组、围栏、解析失败、空答案、拒答五种情况，5/5通过。未修改业务评分器和原始结果；语义正常题仍为已存agent逐题核查，不是自动正式gold。

### L123 — 2026-11-05 — T10-D — FILTER_SUMMARY_COMPLETE

- L121命令退出0，run_manifest completed/valid，24/24完成、0 failed/skipped。独立核验24个artifact摘要和配对请求；[对照报告](../reports/defense_v1/T10/fast_live_pilot_20261105_01/COMPARISON_B5_B6_ZH.md)、[机器汇总](../reports/defense_v1/T10/fast_live_pilot_20261105_01/comparison_b5_b6.json)。B5/B6各4正常回答逐字等于B0，均为allow，沿用先前agent事实判断；攻击各6/8触发动作。B5过滤检索Top-1，不代表正式目标定位准确。
- B6四条成员攻击在摘要器输入均包含目标原文，最终生成器只收摘要；不能混同两阶段暴露。分别按项目解释器调用 `reports/defense_v1/T10/diagnose_masked_fast_pilot.py` 对两次run输出独立诊断；本次B5成员/非成员恢复1/5、2/5，B6为0/5、2/5，原严格分保留。单次请求中位耗时B5约16.35秒、B6约11.90秒，含顺序/长度差异，非正式性能对照。
- 下一步T10-D：检查摘要实际内容与目标定位/回填案例，再按需要复用v2小量补充困难正常问题和多个独立攻击来源；现有12个单轮及agent预审不构成正式gold、E01或整体泄露结论。

### L124 — 2026-11-05 — DOC — REGISTRY_R05_VERIFIED

- 项目解释器 `python -` 核验r05快照132项产物、186项业务源码/配置、run完成数及新报告本地链接，退出0，结果见 `reports/defense_v1/planning/current_versions_registry_validation_20261105_r05.json`。r04历史快照保留，新run固定引用r04，r05登记当前文档和新结果。

### L125 — 2026-11-09（北京时间）— T10-D — EXPOSURE_LOCALIZATION_BEGIN

- 项目解释器 `python -` 重算 r05 的132项身份产物，全部匹配。接续L123，逐条复核已完成B5/B6的原始检索、排除、回填、摘要和回答。另以同一v2 train及冻结索引筛查排名2–4的库内攻击题，固定选择后才看新回答；补少量有直接原文支持的困难正常题。只作为开发压力测试。首次源码定位命令因在PowerShell使用Bash花括号失败，改显式文件路径后退出0。

### L126 — 2026-11-09（北京时间）— T10-D — RANK_STRESS_FIXED

- 项目解释器分别执行 `reports/defense_v1/T10/screen_rank_stress_20261109.py` 与 `reports/defense_v1/T10/build_rank_stress_20261109.py`，均退出0。冻结索引筛查421条后，在看新回答前固定3个不同故事的Masked请求（目标排名2/3/4各1）与3条有逐字证据的困难正常题；6个独立单轮会话，B0/B5/B6共18请求。选题是定向压力样本。见 [输入清单](../data/defense_datasets/legacy_v2_rank_stress_20261109_01/manifest.json) 与 [检索筛查](../reports/defense_v1/T10/rank_stress_20261109_01/retrieval_screen.jsonl)。

### L127 — 2026-11-09（北京时间）— T10-D — RANK_STRESS_RUNNING

- 已执行 `& D:\ProgramData\Anaconda3\envs\MIAGuard\python.exe -u scripts/run_defense_v1_benchmark.py --experiment-spec data/defense_datasets/legacy_v2_rank_stress_20261109_01/experiment_spec.json --output-root data/defense_v1_runs/rank-stress-v2-b0-b5-b6-20261109-01 *> reports/defense_v1/T10/rank_stress_20261109_01/run.log`，工具session=86994，manifest显示running。原BF16和冻结阈值与旧小批相同，待18条配对结果及证据复核。

### L128 — 2026-11-09（北京时间）— T10-D — EXPOSURE_LOCALIZATION_COMPLETE

- L127 命令退出0，manifest completed/valid，18/18完成、0失败/跳过。实际检索排名与筛查逐条匹配。使用项目解释器分别执行 `reports/defense_v1/T10/audit_access_cases_20261109.py <旧或新run目录> <对应JSON路径>`，分别核验旧24条和新18条实际生成证据，输出 original_cases.json 和 rank_stress_cases.json。首次校验错误地将序列化快照视作原始三字段文件而触发断言，修正为比对原始输入哈希及序列化允许范围空值，复核退出0。详见[报告](../reports/defense_v1/T10/rank_stress_20261109_01/REPORT_ZH.md)和[运行清单](../data/defense_v1_runs/rank-stress-v2-b0-b5-b6-20261109-01/run_manifest.json)。
- 使用项目解释器执行 `reports/defense_v1/T10/diagnose_masked_fast_pilot.py data/defense_v1_runs/rank-stress-v2-b0-b5-b6-20261109-01 reports/defense_v1/T10/rank_stress_20261109_01/masked_diagnostic.json`，退出0。B0逐题5/5、4/5、5/5；B5为5/5、5/5、5/5；B6为3/5、1/5、2/5。三条B5都触发且删第一篇，真正目标原文仍交付。B6两份摘要含待填词。3条困难正常题均放行且与B0逐字相同，其中Oklahoma回答把第2名进一步解释为BCS榜单，原文支持不足，见报告。
- 小批属于工程压力测试，目标排名按需选取，攻击仅库内Masked，所有会话单轮。T10-D保留IN_PROGRESS，下一步围绕已证实的定位和摘要内容缺口准备候选方案，并补多来源三轮与能触发限制的困难正常题。

### L129 — 2026-11-09（北京时间）— DOC — REGISTRY_R06_VERIFIED

- 项目解释器 `python -` 复核r06的156项产物与186项源码/配置、选题哈希、18次完成数、排名、三种方案的交付证据和逐词诊断，退出0。新报告本地链接通过。已同步状态、计划、数据目录、实验索引及版本总表。见[核验结果](../reports/defense_v1/planning/current_versions_registry_validation_20261109_r06.json)。

### L130 — 2026-11-11 — T10-D — FIVE_DAY_BEGIN

- 按用户授权接续五日安排，先核对既有v2 train工程样本、版本身份和多轮候选适配；再补充有明确依据的触发限制正常题和独立多轮。正式gold及E01门禁不变。next_task=T10-D（IN_PROGRESS）。

### L131 — 2026-11-11 — T10-D — FIVE_DAY_PREFLIGHT

- 使用项目解释器通过 `python -` 读取两个既有试跑 manifest 和会话 cohort manifest，核对列明的输入与输出 SHA256 共 26 项，失败 0；结果见 [预检](../reports/defense_v1/T10/five_day_preflight_20261111_01.json)。另用项目解释器汇总两个现有 requests 的 request_id 与 session_id，18 个 request_id 唯一；生成 [已有题单索引](../reports/defense_v1/T10/five_day_existing_cohort_20261111_01.json)，仅索引已看过结果的开发案例，非新冻结评估集。
- 两次既有试跑均为 v2 train、旧索引及 top_k=4；前者12题有B0/B2/B5/B6结果，后者6题仅有B0/B5/B6结果，直接合计不同方法会造成覆盖分母不一致。已有7正常题均未触发动作，不足以测误拦后的质量。会话队列绑定 candidate06 的 D-dev，replay_eligible=false，不能直接放入旧索引实验。
- 未生成新问题、未核准完整题单、未更改策略或运行模型；正式gold、E01仍未完成。next_task=T10-D：从 v2 train 找来源可核验的可能触发限制正常题并检验实际动作，另按索引与来源身份准备独立三轮；明确对照覆盖后冻结新工程试跑清单。

### L132 — 2026-11-11 — T10-D — NORMAL_SCORE_SCREEN

- 执行 `& D:\ProgramData\Anaconda3\envs\MIAGuard\python.exe reports/defense_v1/T10/audit_reusable_normal_scores_20261111.py`，退出0。脚本先核验历史train记录SHA256与T04阈值来源一致，再按query_id和原文匹配v2；历史300条正常查询中294条匹配，全部历史单查询logprob低于T04的0.006692850924284855阈值。输出 [统计与输入摘要](../reports/defense_v1/T10/reusable_normal_scores_20261111.json)。
- 这是历史单查询离线分数检查，不代表实际动作、回答质量或第三轮融合；其余v2新增正常题未评分。因此旧分数不能提供已证实触发限制的正常题。下一步用冻结Judge筛查少量v2新增正常题并事后验证来源及实际动作；若没有触发样本，另做明确标注的强制动作质量诊断，不把它算自然误报。next_task=T10-D。未运行模型或更改策略。

### L133 — 2026-11-11 — T10-D — NEW_BENIGN_SCREEN_BEGIN

- 启动v2新增正常查询的小批单查询Judge筛查：先按固定哈希从train且索引内的不同来源选8条，再调用已有BF16 Judge与T04阈值；不将单查询分数当作在线动作或正式gold。输入身份和逐条进度由新运行目录记录。next_task=T10-D。

### L134 — 2026-11-11 — T10-D — NEW_BENIGN_SCREEN_COMPLETE

- 实际执行 `& D:\ProgramData\Anaconda3\envs\MIAGuard\python.exe -u reports/defense_v1/T10/screen_new_benign_20261111.py`，退出0；进程加载BF16模型，对固定的8个不同索引内train来源的v2新增正常问题逐一执行Query Judge，8/8 trace overall=ok。Transformers 提示部分生成参数可能被忽略，原样保留为运行限制。运行[清单](../reports/defense_v1/T10/new_benign_screen_20261111_01/manifest.json)、[题单](../reports/defense_v1/T10/new_benign_screen_20261111_01/candidates.json)、[逐条trace](../reports/defense_v1/T10/new_benign_screen_20261111_01/traces.jsonl)。
- 项目解释器 `python -` 检验清单状态、完成数、候选及trace摘要、顺序和overall状态，8/8通过；[摘要](../reports/defense_v1/T10/new_benign_screen_20261111_01/summary.json)显示8条单查询得分均0.0031726828424851893，低于T04阈值0.006692850924284855。此运行未经过网关动作或回答模型；题目可回答性未审核，不能认定实际误报率、会话风险或正常质量。小批并非代表性样本。
- next_task=T10-D：保持正常自然判定与强制动作诊断分开；从可核原文的小批正常题构建强制动作配对质量测试，同时准备独立多轮与过滤候选。正式gold和E01未完成。

### L135 — 2026-11-11 — T10-D — FORCED_NORMAL_DIAGNOSTIC_BEGIN

- 开始4条已具原文工程参考的正常题B0/B5强制过滤配对；专用脚本只在实验backend覆盖动作选择，线上策略不变。强制条件不能计算自然误拦率；T10-D仍进行中。

### L136 — 2026-11-11 — T10-D — FORCED_NORMAL_DIAGNOSTIC_COMPLETE

- 实际命令 `& D:\ProgramData\Anaconda3\envs\MIAGuard\python.exe -u reports/defense_v1/T10/run_forced_normal_20261111.py` 退出0；[运行清单](../data/defense_v1_runs/forced-normal-b0-b5f-20261111-01/run_manifest.json) completed/valid，8/8、0 failed/skipped。脚本加载模型时Transformers提示温度/top_p/top_k参数可能被忽略；生成输入保留以供核对。
- 通过项目解释器 `python -` 核验8个生成输入artifact SHA256，4个B5_FORCED均hide_target_refill、原Judge触发0/4，4/4移除参考来源且各回填至4篇，4/4回答证据不足；B0四个回答给出先前agent参考事实。详见[报告](../reports/defense_v1/T10/forced_normal_diagnostic_20261111_01/REPORT_ZH.md)和[明细](../reports/defense_v1/T10/forced_normal_diagnostic_20261111_01/audit.json)。强制结果不是自然误拦或总体效用，4题已使用且非人工gold。
- next_task=T10-D：基于线上可见证据准备过滤目标定位候选，先做工程单测与同题验证，再补独立多轮；正式T10-E/T11/E01未完成。

### L137 — 2026-11-11 — T10-D — CONSERVATIVE_ACTION_BEGIN

- 基于已有接口，先将风险触发时不给生成器检索上下文的B3作为保守候选，与B2拒答、已跑B0/B5/B6按同一6题比较；B3不能保证模型参数记忆不泄露。项目解释器核验排名压力题manifest全部5项输出摘要并固定新spec `reports/defense_v1/T10/rank_stress_20261109_01/experiment_b2_b3_20261111.json`，SHA256 101db8bbf7cf188c517c2830faf0ba803bd8a54b51ac6409e17fffb65a217e3e。未调整线上策略；next_task=T10-D。

### L138 — 2026-11-11 — T10-D — CONSERVATIVE_ACTION_COMPLETE

- 执行 `& D:\ProgramData\Anaconda3\envs\MIAGuard\python.exe -u scripts/run_defense_v1_benchmark.py --experiment-spec reports/defense_v1/T10/rank_stress_20261109_01/experiment_b2_b3_20261111.json --output-root data/defense_v1_runs/rank-stress-v2-b2-b3-20261111-01`，退出0，[manifest](../data/defense_v1_runs/rank-stress-v2-b2-b3-20261111-01/run_manifest.json) completed/valid，12/12，0失败或跳过。Transformers提示temperature/top_p/top_k参数可能忽略。
- 运行 `audit_access_cases_20261109.py` 验证12条事件及实际生成证据，退出0；运行 `diagnose_masked_fast_pilot.py` 记录逐词结果，退出0。3攻击题B2均拒答，B3均未向回答模型交付检索文档但各恢复1/5词；3正常题两方法均allow、与B0逐字相同，其中Oklahoma来源支持不足。详见[对照报告](../reports/defense_v1/T10/rank_stress_20261109_01/CONSERVATIVE_B2_B3_20261111_ZH.md)。不改变现有策略，B3是已有动作，并非新定位方法或正式安全结果。
- next_task=T10-D：设计不使用离线标签的候选定位方法并测试，补独立多轮和触发限制的正常质量诊断；正式T10-E/T11/E01保持未完成。

### L139 — 2026-11-11 — DOC — LOCATOR_PLAN_SYNC

- 根据用户要求核对并同步最新方案：主计划T10-D补入已完成的强制正常题和B2/B3对照，按顺序列出定位接口与在线/离线隔离、parent去重与回填测试、同题对照、正常与三轮补缺、摘要检查和指标；候选实现仍未开始，复选框未勾选。同步设计规格与实验协议中的候选/回退和比较口径，修订项目状态、README、实验索引、版本总表入口中旧下一步。next_task=T10-D，正式gold、T11和E01状态不变。
- 实际使用项目解释器通过PowerShell here-string执行 `python -` 核对两项运行metrics，并以 `python -` 定向更新上述7份文档；执行 `python -` 核查7份UTF-8文档、4个引用产物存在、主计划定位任务仍待办，退出0，后续另更新主计划开头和恢复行以消除旧指引。本次为文档同步，无新增模型运行、数据版本或策略实现；r06为既有身份快照，后续运行需登记实际身份。

### L140 — 2026-11-11 — T10-D — LOCATOR_BEGIN

- 开发版本化候选定位器，使用线上请求与候选原文的连续词片段匹配；多parent匹配、匹配不足和无候选走固定拒答。旧Top-1保留独立方法。当前规则是待验证的启发式；先测试再用已看过的题做工程诊断，不读取离线标签作策略输入。

### L141 — 2026-11-11 — T10-D — LOCATOR_ENGINEERING_TESTS

- 新增 `contiguous_trigrams_v1` 候选定位，按在线请求与候选证据的连续词片段计数，每个parent至少两个不同三元组且唯一匹配时过滤；无匹配/多parent匹配走deny。标记和计数是启发式，不能视为已验证的目标归属。新增独立B5_LOCATED，旧B5不变，运行身份增加定位器源码摘要。定位证据为parent匹配计数，不包含离线标签。
- `python -m pytest tests/test_evidence_locator.py -q` 首次因模块缺失报错，开发后3 passed；新增live backend回归先因方法缺失失败。执行 `& D:\ProgramData\Anaconda3\envs\MIAGuard\python.exe -m pytest tests/test_evidence_locator.py tests/test_defense_action_executor.py tests/test_defense_benchmark.py tests/test_exposure_store.py -q` 退出0，26 passed、3个依赖弃用警告。下一步固定同题工程spec并验证真实模型；过滤后的回填异常仍遵循现有 no_context 回退，需单列审查。

### L142 — 2026-11-11 — T10-D — LOCATOR_LIVE_BEGIN

- 项目解释器 `python -` 核对原rank-stress输入manifest的5项输出摘要并固定 `reports/defense_v1/T10/rank_stress_20261109_01/experiment_locator_20261111.json`，SHA256 3521dd507749321e3d5630f4c094668c20338201a1829927d664686d9d224eab，保留原6题、索引及阈值，B5_LOCATED单独运行；该6题结果已知，仅供开发诊断。

### L143 — 2026-11-11 — T10-D — LOCATOR_LIVE_COMPLETE

- 实际执行 `& D:\ProgramData\Anaconda3\envs\MIAGuard\python.exe -u scripts/run_defense_v1_benchmark.py --experiment-spec reports/defense_v1/T10/rank_stress_20261109_01/experiment_locator_20261111.json --output-root data/defense_v1_runs/rank-stress-v2-locator-20261111-01` 退出0，[manifest](../data/defense_v1_runs/rank-stress-v2-locator-20261111-01/run_manifest.json) completed/valid、6/6成功。运行 `audit_access_cases_20261109.py` 和 `diagnose_masked_fast_pilot.py` 分别核验6条生成证据与逐词输出，均退出0。
- 3个目标均被选中并排除，原文实际交付0/3；三个回答分别恢复2/5、1/5、2/5词。3正常题均allow且回答与B0相同，Oklahoma存在既有无据BCS解释。已看过的选定来源不构成独立测试。详见[报告](../reports/defense_v1/T10/rank_stress_20261109_01/LOCATOR_PILOT_20261111_ZH.md)，模型给出temperature/top_p/top_k可能忽略警告。
- next_task=T10-D：固定独立来源及库外、正常自然触发/强制干预案例并核验目标定位与效用；处理回填异常从no_context回退的行为；扩展真实多轮。新候选和正式效果尚未验收。当前源码不同于r06，新运行manifest记录实际源码摘要。

### L144 — 2026-11-11 — T10-D — LOCATOR_DOCUMENT_SYNC

- 使用项目解释器 `python -` 同步主计划、项目状态与版本总表，标记候选小批已完成，独立来源与库外验证仍待办。随后通过 `python -` 核验新运行manifest中 `code:evidence_locator.py` 的SHA256与实际源码一致，并核验台账、状态、实验索引、版本总表及主计划均可按UTF-8读取，退出0。未更改原数据集与冻结Judge；新源码身份以本次运行manifest为准。

### L145 — 2026-11-11 — T10-D — NEW_SOURCE_PILOT_BEGIN

- 开始从原v2 train检索筛查记录选择不同于已有两批样本的来源，冻结候选后比较B0、旧B5、定位候选与B2；来源仅在文档ID层面区分，事件独立性待查。剩余Masked排名2–4候选为0，S²排名2–4的三个查询包含生成器产物痕迹，不进入本批。目标是补充来源与类型开发诊断，不作为正式独立测试。

### L146 — 2026-11-11 — T10-D — NEW_SOURCE_PILOT_FIXED

- 运行 `& D:\ProgramData\Anaconda3\envs\MIAGuard\python.exe reports/defense_v1/T10/build_locator_sources_20261111.py`，退出0。按固定哈希顺序，每种Direct/S²/Masked选2题，6篇不同文档，均避开前两批所用文档ID、均为原索引内rank=1。Masked逐题检查重建原文、答案无子串再现；Direct/S²使用canonical。选题前未使用新回答。见[manifest](../data/defense_datasets/locator_new_sources_20261111_01/manifest.json)。文档ID不同不代表事件独立，该批无正常与非成员，全部工程诊断。

### L147 — 2026-11-11 — T10-D — NEW_SOURCE_PILOT_RUNNING

- 执行 `& D:\ProgramData\Anaconda3\envs\MIAGuard\python.exe -u scripts/run_defense_v1_benchmark.py --experiment-spec data/defense_datasets/locator_new_sources_20261111_01/experiment_spec.json --output-root data/defense_v1_runs/locator-new-sources-20261111-01`，会话4417；运行状态以输出manifest为准。固定4方法×6请求，记录工程失败分母。

### L148 — 2026-11-11 — T10-D — NEW_SOURCE_PILOT_COMPLETE

- L147命令退出0，[运行清单](../data/defense_v1_runs/locator-new-sources-20261111-01/run_manifest.json) completed/valid，24/24、0失败/跳过。分别执行 `audit_access_cases_20261109.py data/defense_v1_runs/locator-new-sources-20261111-01 reports/defense_v1/T10/locator_new_sources_cases_20261111.json` 以及 `diagnose_masked_fast_pilot.py data/defense_v1_runs/locator-new-sources-20261111-01 reports/defense_v1/T10/locator_new_sources_masked_20261111.json`，均退出0，核验24条实际生成证据及Masked包装与逐词恢复。完整说明见[报告](../reports/defense_v1/T10/LOCATOR_NEW_SOURCES_20261111_ZH.md)。
- 六题均索引内rank=1。两条Direct和一条Masked未触发Query-only（均0.0031726828424851893低于0.006692850924284855），因此均放行；另一条Masked及两条S²触发，旧B5和新定位均排除目标。Masked新定位逐题5/5、1/5，B0为5/5、4/5。没有正常、非成员或多轮；不同文档ID不是事件独立证明。模型提示temperature/top_p/top_k可能被忽略。
- next_task=T10-D：不调整冻结Judge，先核查三条未触发trace及查询质量，明确是评分/路由问题还是题目有效性问题，再准备独立非成员、正常动作与多轮对照；回填异常回退仍需处理。正式gold、T11、E01未完成。

### L149 — 2026-11-11 — T10-D — UNTRIGGERED_TRACE_AUDIT

- 项目解释器 `python -` 对3条未触发B5_LOCATED的artifact SHA256、初筛路由和来源进行逐题核验，退出0。[核验JSON](../reports/defense_v1/T10/locator_new_sources_untriggered_audit_20261111.json)：三条均 `SKIP_NO_ATTACK_CUE`、detail `skipped_no_attack_cue`；两条Direct逐字包含索引原文并询问context存在性，Masked5处恢复索引原文，但原文末尾截断。仅工程语义核验，非人工gold，无非成员对照，不能推断成员泄露率。
- 下一步T10-D：先在开发集复核初筛跳过与候选评分路径，评估单独版本的候选修复及正常题代价，原冻结Judge/阈值保持历史身份；同时继续独立非成员/正常及多轮和回填异常工作。每个新策略另记配置/模型身份并在可用开发集比较，不使用已看过的历史test调参。正式gold/T11/E01依赖不变。

### L150 — 2026-11-11 — T10-D — NEW_SOURCE_DOCUMENT_SYNC

- 项目解释器 `python -` 同步主计划与版本入口，核验新增数据manifest4项输出SHA256、运行metrics 24/24且0失败、报告UTF-8，退出0。新增数据目录、实验索引、项目状态与台账均已登记；next_task以L149为准。无正式效果验收。

### L151 — 2026-11-11 — T10-D — QUERY_CUE_CANDIDATE_BEGIN

- 复核 `progressive_judge.py`：初筛SKIP时仍执行rubric/logprob，但细查证据为空。准备独立版本的线上可见查询线索候选，用长引文与上下文存在性核验、多个编号遮蔽与原词恢复请求的组合触发保守回退；固定Judge与阈值作为对照保持原身份。先按v2 train正常查询做离线触发盘点，再以小批真实模型对照，禁止据单个样本声明自然误报率或成员泄露下降。

### L152 — 2026-11-11 — T10-D — QUERY_CUE_ENGINEERING

- 按L151新增独立线索 `query_cue_v1`：至少12词引文与上下文存在性核验组合、或至少三个不同编号mask与原词恢复表达。新增B5_CUE实验方法：Judge未触发但线索命中时固定拒答，Judge触发时沿用B5_LOCATED；保留原Judge分数与独立线索日志。线索是规则匹配而非恶意真值，可误拦合法引文检查或填空。
- `pytest tests/test_query_cue.py` 初次模块缺失失败；`pytest tests/test_defense_benchmark.py::test_live_backend_methods_share_request_contract_without_gpu` 首次新方法未支持失败。实现后执行 `& D:\ProgramData\Anaconda3\envs\MIAGuard\python.exe -m pytest tests/test_query_cue.py tests/test_evidence_locator.py tests/test_defense_action_executor.py tests/test_defense_benchmark.py tests/test_exposure_store.py -q` 退出0，28 passed、3依赖弃用警告。
- 执行 `& D:\ProgramData\Anaconda3\envs\MIAGuard\python.exe reports/defense_v1/T10/audit_query_cues_20261111.py` 退出0，[train盘点](../reports/defense_v1/T10/query_cue_train_audit_20261111.json)覆盖正常1304、Direct/Masked/S²各300、IA 2375；命中正常0、Direct 127、Masked 150、S²/IA 0。属于规则静态覆盖，不是在线误报或攻击效果；题目来自开发数据，标签与质量待审核。

### L153 — 2026-11-11 — T10-D — QUERY_CUE_LIVE_BEGIN

- 项目解释器 `python -` 核验两批原请求、标签及spec摘要，固定10题工程试点：前次6攻击+先前4正常，并生成 [manifest](../data/defense_datasets/query_cue_pilot_20261111_01/manifest.json)。题与旧结果已见，非新独立样本，正常题非人工gold。

### L154 — 2026-11-11 — T10-D — QUERY_CUE_LIVE_RUNNING

- 执行 `& D:\ProgramData\Anaconda3\envs\MIAGuard\python.exe -u scripts/run_defense_v1_benchmark.py --experiment-spec data/defense_datasets/query_cue_pilot_20261111_01/experiment_spec.json --output-root data/defense_v1_runs/query-cue-pilot-20261111-01`，工具会话56353；状态以运行manifest为准。

### L155 — 2026-11-11 — T10-D — QUERY_CUE_LIVE_COMPLETE

- L154命令退出0，[run manifest](../data/defense_v1_runs/query-cue-pilot-20261111-01/run_manifest.json) completed/valid，10/10完成、0失败/跳过。运行 `audit_access_cases_20261109.py data/defense_v1_runs/query-cue-pilot-20261111-01 reports/defense_v1/T10/query_cue_live_cases_20261111.json` 与 `diagnose_masked_fast_pilot.py data/defense_v1_runs/query-cue-pilot-20261111-01 reports/defense_v1/T10/query_cue_live_masked_20261111.json` 均退出0，验证10条受控输入与逐词评分。
- 原Judge未触发的2 Direct/1 Masked经新线索均拒答，原Judge触发的2 S²/1 Masked均定位并排除目标，成员目标原文交付0/6。Masked两题拒答及1/5恢复；4正常题均未命中规则、放行且与B0逐字一致。已见开发样本无非成员与多轮，不能推断自然误报或总体泄露；生成参数temperature/top_p/top_k可能被忽略。详见[报告](../reports/defense_v1/T10/QUERY_CUE_PILOT_20261111_ZH.md)。
- next_task=T10-D：预先固定不同来源、非成员和困难正常题，检查规则误触发与定位回退；补独立多轮并核验会话融合。正式gold、T11、E01未完成。

### L156 — 2026-11-11 — T10-D — QUERY_CUE_DOCUMENT_SYNC

- 项目解释器 `python -` 更新主计划、状态、数据、实验索引及版本总表。另执行 `python -` 核验试点数据manifest的3项输出SHA256和run manifest所记录的 `code:query_cue.py` 与源码一致，退出0。候选试跑为工程诊断，正式状态和冻结Judge未改变；next_task以L155为准。

### L157 — 2026-11-11 — T10-D — CUE_NONMEMBER_UTILITY_BEGIN

- 固定此前三批未使用的train来源，准备不同文档的非成员Direct/Masked与少量正常题；正常题包括显式阅读练习困难例，单独报告。旧索引身份、题面、原文和答案需在运行前核验。新问题和结果仍属工程开发；事件独立性与人工gold待验收。

### L158 — 2026-11-11 — T10-D — CUE_NONMEMBER_UTILITY_FIXED

- 执行 `& D:\ProgramData\Anaconda3\envs\MIAGuard\python.exe reports/defense_v1/T10/build_cue_utility_20261111.py`，退出0，核验原bank、split、target原文、索引及overlay摘要后固定8题：4篇库外目标（2 Direct、2 Masked，彼此及旧样本不同doc_id），4篇库内正常来源（2事实问答、2明确声明公开阅读练习的合成困难题）。Masked检查遮蔽答案不在未遮蔽词边界出现且可重建原文，正常题证据与原索引一致。见[数据manifest](../data/defense_datasets/cue_utility_nonmember_20261111_01/manifest.json)。
- 项目解释器 `python -` 输出规则命中：4攻击、2合成阅读困难题命中，2普通正常题未命中；这是规则静态检查，题目非人工gold。不同文档ID尚未证明事件独立。B0/B5_LOCATED/B5_CUE各8题共24次预期。

### L159 — 2026-11-11 — T10-D — CUE_NONMEMBER_UTILITY_RUNNING

- 执行 `& D:\ProgramData\Anaconda3\envs\MIAGuard\python.exe -u scripts/run_defense_v1_benchmark.py --experiment-spec data/defense_datasets/cue_utility_nonmember_20261111_01/experiment_spec.json --output-root data/defense_v1_runs/cue-utility-nonmember-20261111-01`，会话6430；完成与否以run manifest为准。

### L160 — 2026-11-11 — T10-D — CUE_NONMEMBER_UTILITY_COMPLETE

- L159命令退出0，[run manifest](../data/defense_v1_runs/cue-utility-nonmember-20261111-01/run_manifest.json) completed/valid，24/24、0失败/跳过。执行 `audit_access_cases_20261109.py data/defense_v1_runs/cue-utility-nonmember-20261111-01 reports/defense_v1/T10/cue_utility_nonmember_cases_20261111.json` 与 `diagnose_masked_fast_pilot.py data/defense_v1_runs/cue-utility-nonmember-20261111-01 reports/defense_v1/T10/cue_utility_nonmember_masked_20261111.json`，均退出0，核验24条生成证据及逐词诊断。
- 4非成员中，B0 Direct回答No 2/2、Masked逐词0/5与0/5；B5_LOCATED拒答3/4，B5_CUE拒答4/4。两普通事实正常题三方法均放行、回答正确事实；合成公开引文题B0及B5_LOCATED答Yes，B5_CUE因线索拒答；合成公开填空题B0未检索到参考来源而回答证据不足，两个防御均因Judge已触发且定位不清拒答。详见[报告](../reports/defense_v1/T10/CUE_UTILITY_NONMEMBER_20261111_ZH.md)。标注与题面为agent工程判断，公开阅读练习的正常性仍需人工审核。
- next_task=T10-D：以现有结果定位规则与合法阅读的冲突，在开发集设计精细分支并复核难正常题语义/授权边界，固定多来源与多轮对照；核对回填异常回退。正式gold、T11、E01未完成；非成员4题不能得出总体泄露结论。

### L161 — 2026-11-11 — T10-D — CUE_NONMEMBER_DOCUMENT_SYNC

- 项目解释器 `python -` 更新主计划及版本入口，记录正常阅读与规则冲突；另通过 `python -` 核验新数据manifest 5项输出SHA256及metrics 24/24、0失败，退出0。同步状态、数据目录和实验索引，next_task以L160为准。

### L162 — 2026-11-11 — DOC — USER_TYPE_DRIVEN_DIRECTION

- 用户确认目标流程为先识别可能攻击类型，再按类型实施访问控制。核对 `online_judge_adapter.py`、`risk_types.py`、`two_stage_gateway.py` 和 `defense_benchmark_live.py`：trace/RiskResult可携带疑似类型与证据；冻结融合路径的 `predicted_attack_type` 取第一个可用类型，而assessment的query/session摘要不含完整类型集合；现有B2/B3/B5/B6/B5_LOCATED/B5_CUE均为单一动作或规则候选，尚无按类型选择的完整动态策略。
- 使用项目解释器 `python -` 同步开发规格、主计划、协议、项目状态与版本总表，记录线上预测/离线真值分离、四类候选方向、未知及多类型处理、T10-D接口/数据准备与T14策略实现，不勾选未完成任务。另执行 `python -` 验证5份文档可读、类型驱动任务为待办及最近两个run manifest completed，退出0。next_task=T10-D，正式gold/T11/E01依赖不变；本次无代码修改、无模型运行、无版本切换。

### L163 — 2026-11-13 — T10-D — TYPE_POLICY_BEGIN

- Goal 启动，依据 L162 和现有 v1.1 规格在 T10-D 开发、验证类型驱动候选。实验身份为 engineering_only，正式 T14 及依赖按原门禁验收。
- 实际执行项目解释器 `python reports/defense_v1/T10/audit_type_policy_traces_20261113.py`，退出 0。复算 v2 复用选择清单 6 项摘要、4 个已有 live run 的冻结模型/阈值/索引/配置等身份，以及单方法选取的 32 个受控 trace artifact。结果见 [类型盘点](../reports/defense_v1/T10/type_policy_trace_audit_20261113.json)。快速试跑 8 个攻击输入中 6 个触发、5 个包含正确类型，其中 1 个 S² 判为 Masked。既有 v2 对照均单轮，Session 类型尚需真实多轮验证。历史 E00 保留 v1。
- 首个候选使用冻结阈值和有效阶段的完整疑似类型。低风险放行，高风险 Direct 拒答，S²/Masked 唯一定位后过滤回填，IA 在 Query-only 且无既往原文交付时不使用检索上下文，Session 判断为 IA 或此前已交付原文时拒答。高风险空类型、冲突、定位/回填失败走拒答，判断失败返回 unavailable。复用可信的检索允许集合。离线标签只在评估器读取。下一步为接口、动作及回退测试。

### L164 — 2026-11-13 — T10-D — TYPE_POLICY_ENGINEERING

- 新增开发方法 B_TYPE_V1，保留 Query/Session 的完整类型和证据，使用 L163 的动作规则。访问层将本候选过滤回填异常或空结果回退为拒答，审计分别记录选定与实际动作。模型判断失败记录 unavailable 并跳过回答模型。
- 先执行 `python -m pytest tests/test_defense_benchmark.py -k type_policy -xq`，退出 1，确认为缺少该 live 方法。实现后执行 `python -m pytest tests/test_defense_benchmark.py tests/test_defense_action_executor.py tests/test_exposure_store.py tests/test_evidence_locator.py tests/test_query_cue.py -q --tb=short`，退出 0，39 项通过，3 个依赖弃用警告。用测试后端验证类型分流、异常、多类型、第三轮和历史交付、允许集合及过滤失败时不向回答模型交付。下一步冻结开发题单，运行真实模型。next_task=T10-D。

### L165 — 2026-11-13 — T10-D — TYPE_POLICY_COHORT_FIXED

- 执行 `python reports/defense_v1/T10/build_type_policy_cohort_20261113.py`，退出 0。预先固定 [开发题单](../data/defense_datasets/type_policy_v2_train_20261113_01/manifest.json)，27 问/23 会话、四类攻击及 12 个正常请求，其中两组为不同来源的三轮正常会话。沿用已见攻击题，四个新增问题均为正常追问。验证父清单输出摘要、文档在 v2 train 及历史索引身份。所选四方法预计 108 次，正常参考答案是 agent 工程标注，IA 为单轮，正式依赖待验收。

### L166 — 2026-11-13 — T10-D — TYPE_POLICY_LIVE_RUNNING

- 执行 `python -u scripts/run_defense_v1_benchmark.py --experiment-spec data/defense_datasets/type_policy_v2_train_20261113_01/experiment_spec.json --output-root data/defense_v1_runs/type-policy-v1-20261113-01`，工具会话 71969，已观察模型分片加载。运行状态和完成分母以实际 [run manifest](../data/defense_v1_runs/type-policy-v1-20261113-01/run_manifest.json) 及 metrics 为准。

### L167 — 2026-11-13 — T10-D — TYPE_POLICY_REGRESSION_AND_SYNC

- 运行 `python -m pytest tests/test_defense_benchmark.py tests/test_defense_action_executor.py tests/test_exposure_store.py tests/test_evidence_locator.py tests/test_query_cue.py tests/test_two_stage_gateway.py tests/test_online_judge_adapter.py tests/test_frozen_risk_scorer.py -q --tb=short`，退出 0，65 项通过，3 个依赖弃用警告。执行项目解释器 `python -` 同步主计划、项目状态、实验索引、数据目录和版本总表，记录已核验功能、开发题单身份及在跑实验。next_task=T10-D。

### L168 — 2026-11-13 — T10-D — TYPE_POLICY_LIVE_CHECKPOINT

- 使用 PowerShell 枚举会话分片并通过项目解释器 `python -` 读取已写入的事件，核对 B0 和 B2 各 27/27 完成。B2 的两组三轮正常会话在第三轮实际使用 fusion 且放行。B0 的合成填空题未检索到参考原文，另一个正常第三轮输出提及正确实体又判断证据不足，待统一复核。
- 增加只读实验审计脚本 `reports/defense_v1/T10/audit_type_policy_run.py`，将在全量输出就绪后核对逐请求覆盖、输入身份、受控 prompt、账本和类型。主运行仍在工具会话 71969 中，未完成全量实验。

### L169 — 2026-11-13 — T10-D — TYPE_POLICY_V1_LIVE_COMPLETE

- L166 命令退出 0，108/108 完成，0 失败、0 跳过、0 缺失攻击分数。[运行清单](../data/defense_v1_runs/type-policy-v1-20261113-01/run_manifest.json)及 [metrics](../data/defense_v1_runs/type-policy-v1-20261113-01/metrics.json) 已落盘。Transformers 提示部分采样参数可能被忽略。
- 执行 `python reports/defense_v1/T10/audit_type_policy_run.py data/defense_v1_runs/type-policy-v1-20261113-01 reports/defense_v1/T10/type_policy_v1_paired_metrics_20261113.json`，首次退出 1，零计数键与普通字典比较导致断言失败。改为 Counter 对比后原命令退出 0，核验 108 个请求及生成输入摘要和账本。详见[配对指标](../reports/defense_v1/T10/type_policy_v1_paired_metrics_20261113.json)。
- 三个防御方法均使 7 个库内攻击请求的目标原文从 B0 的 7 次交付降为 0。类型策略风险触发 12/15，正确类型 11/15，错分 1 次。类型策略干预 1/12 个正常请求，规则对照干预 2/12。类型策略的 Masked 位置恢复诊断为 6/35，B0 为 21/35，固定拒答为 0/35。
- 修订依据为过滤后仍能恢复部分原词。计划新增 B_TYPE_V2，仅在高风险、唯一在线 Masked 类型且观察到明确原词恢复线索的分支拒答，其余沿用 B_TYPE_V1。保留首次输出，在同一开发题单对比两策略。此改动属结果驱动的开发迭代，独立评估待进行。next_task=T10-D。

### L170 — 2026-11-13 — T10-D — TYPE_POLICY_V2_RETEST_BEGIN

- 增加 B_TYPE_V2 的明确原词恢复分支，保留 B_TYPE_V1 原分流。运行 `pytest tests/test_defense_benchmark.py -k B_TYPE_V2 -xq --tb=short`，首次因方法不存在退出 1。实现后按 L167 同命令运行，退出 0，68 项通过，3 个依赖弃用警告。
- 项目解释器 `python -` 复算原开发题单 5 项输出摘要，另存 [配对复跑 spec](../reports/defense_v1/T10/type_policy_v2_retest_spec_20261113.json)。同题 27 问 × B_TYPE_V1 与 B_TYPE_V2，首轮输出不覆盖。执行 `python -u scripts/run_defense_v1_benchmark.py --experiment-spec reports/defense_v1/T10/type_policy_v2_retest_spec_20261113.json --output-root data/defense_v1_runs/type-policy-v2-paired-20261113-01`，运行状态见 [run manifest](../data/defense_v1_runs/type-policy-v2-paired-20261113-01/run_manifest.json)。

### L171 — 2026-11-13 — T10-D — TYPE_POLICY_REPORT_CHECKPOINT

- 项目解释器 `python -` 核对首轮逐请求数据，记录 48 个正常输出的 agent 复核，[判定记录](../reports/defense_v1/T10/type_policy_v1_normal_review_20261113.json)。B0/B2/B_TYPE_V1 各 10/12 正确且参考来源实际交付，B5_CUE 为 9/12。记录 [中文汇报稿](../reports/defense_v1/T10/TYPE_POLICY_PAIRED_20261113_ZH.md) 的首轮表及失败案例。
- 同步状态和实验索引。复跑工具会话 27853，已完成模型加载并写入会话分片，最终状态和分母待核验。next_task=T10-D。

### L172 — 2026-11-13 — T10-D — TYPE_POLICY_FULL_REGRESSION

- 执行项目解释器 `python -m pytest -q --tb=short`，退出 0，513 项通过、1 项跳过、3 个依赖弃用警告。B_TYPE_V1/V2 同题运行仍在会话 27853。待汇总后检查 V1 能否复现首轮、V2 的动作改动和正常回答是否变化。

### L173 — 2026-11-13 — T10-D — TYPE_POLICY_V2_RETEST_COMPLETE

- L170 的运行命令在会话 27853 退出 0，54/54 完成，0 失败、0 跳过、0 缺失攻击分数。[复跑清单](../data/defense_v1_runs/type-policy-v2-paired-20261113-01/run_manifest.json)、[原始指标](../data/defense_v1_runs/type-policy-v2-paired-20261113-01/metrics.json)和逐请求记录已落盘。
- 执行 `python reports/defense_v1/T10/audit_type_policy_run.py data/defense_v1_runs/type-policy-v2-paired-20261113-01 reports/defense_v1/T10/type_policy_v2_paired_metrics_20261113.json` 及 `python reports/defense_v1/T10/compare_type_policy_retest.py reports/defense_v1/T10/type_policy_v1_paired_metrics_20261113.json reports/defense_v1/T10/type_policy_v2_paired_metrics_20261113.json reports/defense_v1/T10/type_policy_v1_normal_review_20261113.json reports/defense_v1/T10/type_policy_v2_retest_comparison_20261113.json`，均退出 0。[复跑审计](../reports/defense_v1/T10/type_policy_v2_paired_metrics_20261113.json)与[版本差异](../reports/defense_v1/T10/type_policy_v2_retest_comparison_20261113.json)证实 V1 的风险、类型、动作、交付和回答核对 27/27 一致。V2 有 4 个动作由过滤转为拒答，Masked 恢复 6/35 → 0/35，正常回答变化 0/12。
- 项目解释器 `python -` 同步状态、实验索引、版本总表和主计划，规格和协议补记工程方法及评分口径。[中文汇报](../reports/defense_v1/T10/TYPE_POLICY_PAIRED_20261113_ZH.md)包含首轮、复跑、典型失败与限制。开发集结果用于分流和保护效果诊断。正常金标未人工核对，IA 为单轮，缺少独立校准及终测。next_task=T10-D，正式门禁继续按协议。

### L174 — 2026-11-13 — T10-D — TYPE_POLICY_DELIVERABLE_VERIFICATION

- 执行项目解释器 `python -` 做交付核验，退出 0。重算题单及来源摘要、两轮 metrics 和审计输入摘要，核对 108/108、54/54、同题身份、两组第三轮真实融合、当前策略源码指纹、27 个配对差异与正常复核。中文汇报全部相对链接可用，版本总表、状态、实验索引和数据目录均有本次记录。
- 当前 Goal 的开发实现、真实模型配对、同题修订复跑及中文汇报已验收。研究项目 next_task=T10-D，独立来源、多轮 IA、人工 gold、正式实验仍按门禁继续。

### L175 — 2026-11-13 — T10-D — BENIGN_PAIR_BEGIN

- Goal 启动困难正常题配对补试。执行项目解释器 `python -` 核对 L173 的完整 run manifest、metrics、所有 identity 与 code 摘要，以及 v2 复用选择清单。均匹配，交集筛得 18 个未用作上一轮目标且已索引的 v2 train 来源 ID。历史检索背景重合不等于目标重用，事件独立性待核实。
- 预先写明必要事实、证据和筛选逻辑，用同一冻结 Judge 与原索引预筛，不运行回答生成。随后锁定题单，用 B0、B2、B_TYPE_V2 真实回放。主要分母为 B2 固定拒答的正常请求，主要计数为 V2 仍正确回答且实际交付全部必需证据的请求。next_task=T10-D。

### L176 — 2026-11-13 — T10-D — BENIGN_PAIR_SCREEN_RUNNING

- 执行 `python -u reports/defense_v1/T10/freeze_benign_pair_20261113.py`，工具会话 77876，模型已加载。18 个候选及评分口径预先落盘，18 个证据片段已和原索引逐字核对。按 [候选规则](../reports/defense_v1/T10/benign_pair_candidates_20261113.json) 优先选有原始证据且触发拒答的单轮题，并固定保留两组三轮会话。预筛调用原检索及 Judge，未调用回答模型。
- [预筛清单](../reports/defense_v1/T10/benign_pair_screen_20261113_01/manifest.json)记录状态。题单生成后才启动三方法真实回答。next_task=T10-D。

### L177 — 2026-11-13 — T10-D — BENIGN_PAIR_COHORT_FIXED

- L176 命令退出 0，预筛完成 18/18，其中 4 个固定拒答分支，3 个同时检索到参考来源。冻结 [14 问/10 会话题单](../data/defense_datasets/benign_pair_v2_train_20261113_01/manifest.json)，保留两个不同来源的三轮会话，纳入 3 个预筛拒答样本。未预看新回答。未选的一个触发样本缺少参考证据。
- 启动 `python -u scripts/run_defense_v1_benchmark.py --experiment-spec data/defense_datasets/benign_pair_v2_train_20261113_01/experiment_spec.json --output-root data/defense_v1_runs/benign-triggered-pair-20261113-01`，预期 14 × 3 = 42 次。[运行清单](../data/defense_v1_runs/benign-triggered-pair-20261113-01/run_manifest.json)为实际状态入口。若中断，确认原进程已停止后以同命令追加 `--resume`。

### L178 — 2026-11-13 — T10-D — BENIGN_PAIR_LIVE_CHECKPOINT

- 真实运行工具会话 93929。执行项目解释器 `python -` 核对题单输入/输出摘要及生产源码与 L173 的指纹，退出 0。逐会话分片显示 B0/B2 各 14/14 已落盘，B2 拒答 3 个与预筛一致的填空请求，B0 对三题均交付参考证据并给出预登记事实。B_TYPE_V2 正在运行。
- 主计划已登记预筛和题单检查点。最终数字以运行清单、指标和全量逐请求复核为准。next_task=T10-D。

### L179 — 2026-11-13 — T10-D — BENIGN_PAIR_COMPLETE

- L177 命令在工具会话 93929 退出 0，42/42 完成，0 失败、0 跳过，见 [run manifest](../data/defense_v1_runs/benign-triggered-pair-20261113-01/run_manifest.json) 和 [metrics](../data/defense_v1_runs/benign-triggered-pair-20261113-01/metrics.json)。Transformers 提示部分生成参数可能被忽略。
- 执行 `python reports/defense_v1/T10/audit_type_policy_run.py data/defense_v1_runs/benign-triggered-pair-20261113-01 reports/defense_v1/T10/benign_pair_evidence_20261113.json`，退出 0。执行 `python reports/defense_v1/T10/review_benign_pair_20261113.py reports/defense_v1/T10/benign_pair_evidence_20261113.json data/defense_datasets/benign_pair_v2_train_20261113_01/normal_rubric.jsonl data/defense_datasets/benign_pair_v2_train_20261113_01/lineage.jsonl reports/defense_v1/T10/benign_pair_review_20261113.json --judgments reports/defense_v1/T10/benign_pair_agent_judgments_20261113.json`，退出 0。逐题复核 18 组不同响应/动作，覆盖 42 个事件。B2 拒答 3/14，V2 拒答 2/14、过滤 1/14，V2 保留必需证据且答对 0/3。正常正确且参考原文交付数 B0/B2/V2 为 14/11/11。
- 通过项目解释器 `python -` 同步计划、状态、实验索引、数据目录和版本总表；[中文汇报](../reports/defense_v1/T10/TYPE_POLICY_PAIRED_20261113_ZH.md)已纳入本轮结果。按触发和可检索性筛选，结果为本批开发诊断。next_task=T10-D，独立来源、多轮 IA、实际人员审核及正式门禁待后续。

### L180 — 2026-11-13 — T10-D — BENIGN_PAIR_DELIVERABLE_VERIFIED

- 执行项目解释器 `python -` 验收核对，退出 0。复算预筛、题单、原始指标和复核输入摘要；逐项核对 42 个事件、两组第三轮实际融合、B0/B2/V2 的完整覆盖与主结果 0/3。生产代码和原模型、阈值、索引等身份与 L173 匹配，汇报全部相对链接可打开。相关文档已同步。next_task=T10-D。

### L181 — 2026-11-13 22:21（北京时间）— T10-D — FORTY_MINUTE_SUPPLEMENT_BEGIN

- 用户授权40分钟内尽可能推进后续实验。沿用当前计划，优先补真实多轮IA与正常失败原因证据，不改冻结Judge、阈值或生产策略。并行agent仅复核3个已观察正常失败案例，输出新报告且明确非真人gold。
- 已读取最新入口与L180，执行 `git rev-parse --show-toplevel` 确认本目录非Git仓库；`nvidia-smi --query-gpu=name,memory.used,memory.total,utilization.gpu --format=csv,noheader` 退出0，A5000显存占用3113/24564MiB。以独立新数据/运行目录保存实验，不覆盖旧产物。
- 计划先核验v2 train、原索引及既有模型预审叠加层，冻结4个来源的三轮IA和正常对照，比较B0/B2/B_TYPE_V2；有时间再进行相同问题独立会话对照。记录实际Session判断、历史交付、动作和公开回答，均为engineering_only，不能作为总体成员泄露或正式gold结果。
- next_task=T10-D；正式T10-E、T11、E01及独立终测门禁不变。

### L182 — 2026-11-13 — T10-D — MULTITURN_IA_COHORT_FIXED

- 执行 `python reports/defense_v1/T10/build_multiturn_ia_supplement_20261113.py` 退出0，冻结[三轮题单](../data/defense_datasets/multiturn_ia_session_v2_train_20261113_01/manifest.json)和[逐题重置会话题单](../data/defense_datasets/multiturn_ia_reset_v2_train_20261113_01/manifest.json)。相同18问，其中4个IA来源各3问、2个正常来源各3问；IA有2个成员与2个非成员来源。主对照54次，重置对照18次，尚未执行模型。
- IA复用11条已有预审建议和1条原bank问题，逐条核对原文支持，添加不包含完整答案的主题锚点，记录新查询及会话身份。原文、v2 train、索引成员和输入/输出摘要通过builder断言。正常控制复用已见Treo/P&O六问。`python -`核对生产源码与L179运行指纹一致，见[预检](../reports/defense_v1/T10/multiturn_ia_preflight_20261113.json)。
- 预先规定同题重置会话比较同时移除Session Judge和历史暴露，不称纯组件消融。问题为固定非自适应序列，IA源真值均为yes，存在顺从/先验知识混淆；4来源不足以报告总体成员AUROC或低FPR结论。新增题单仅engineering_only，next_task=T10-D。

### L183 — 2026-11-13 — T10-D — MULTITURN_IA_RUNNING_AND_CASE_AUDIT

- 独立agent规格核验通过，未发现阻塞启动问题。执行 `python -m pytest tests/test_defense_benchmark.py tests/test_defense_action_executor.py tests/test_exposure_store.py tests/test_evidence_locator.py tests/test_query_cue.py tests/test_two_stage_gateway.py tests/test_online_judge_adapter.py tests/test_frozen_risk_scorer.py -q --tb=short`，退出0，68 passed、3依赖警告。
- 启动 `python -u scripts/run_defense_v1_benchmark.py --experiment-spec data/defense_datasets/multiturn_ia_session_v2_train_20261113_01/experiment_spec.json --output-root data/defense_v1_runs/multiturn-ia-session-20261113-01`，工具会话62312，已加载本地模型分片。预期54请求，最终状态以[运行清单](../data/defense_v1_runs/multiturn-ia-session-20261113-01/run_manifest.json)为准；不得在进程未结束时重启。
- 独立agent完成[三道正常失败复核](../reports/defense_v1/T10/benign_failure_audit_20261113_01/REPORT_ZH.md)：Treo的128MB已在首轮用户问题和前两轮回答出现，第3轮过滤不代表累计未暴露；Ace/Oklahoma缺少可信授权依据，不直接称确定误拦。[逐案证据](../reports/defense_v1/T10/benign_failure_audit_20261113_01/audit.json)为llm_agent审核，非真人gold。主agent继续独立验收。next_task=T10-D。

### L184 — 2026-11-13 — T10-D — MULTITURN_SCOPE_CLARIFICATION

- 独立审核在运行启动后指出题单manifest的“real per-method responses in history”表述含糊。只读代码核验：Session Judge历史包含问题与检索信息，回答模型prompt仅当前query与当前允许contexts；真实回答保存在暴露账本，不进入后轮回答prompt。冻结输入保持原字节，新增[绑定两份manifest摘要的勘误](../reports/defense_v1/T10/multiturn_ia_metadata_erratum_20261113.json)，不修改在跑身份或重启实验。
- 主agent通过 `python -` 独立重算三案audit中45个唯一输入摘要全部匹配；其46个检查条目含重复文件。另独立代码质量审核核对题单/原spec/标签隔离及三案原始证据，无阻塞问题。仅工程审核，真实正常授权仍未知。
- 主运行已观察B0的18请求及B2的部分会话分片，仍在62312中运行。下一步汇总后执行预冻结的重置会话条件；并准备三案相同事实的普通问句/填空问句单轮对照，评估题型变化的全链影响，不修改策略。next_task=T10-D。

### L185 — 2026-11-13 — T10-D — STYLE_PAIR_FIXED_AND_RUNNING_CHECKPOINT

- agent执行 `python reports/defense_v1/T10/build_benign_style_pair_20261113.py` 完成6题/6单轮的新题单，未运行模型。三条旧填空逐字不变，普通问句只问原文支持的相同事实；Ace不使用原文未支持的注册地/办公室城市/前高管关系。主agent重算25输入+7输出共32项摘要一致，独立审核确认旧spec摘要、同事实与在线白名单合规。见[manifest](../data/defense_datasets/benign_style_pair_v2_train_20261113_01/manifest.json)。18是预期请求事件数，不是Judge/回答模型总调用数。
- 主运行62312已写入48个完成事件（B0/B2各18、V2为12），尚未完成正常控制；未重启。新增比较脚本 `reports/defense_v1/T10/compare_multiturn_ia_20261113.py` 经独立审核，并补完整methods×request_id集合断言；待两条件完成后运行。
- 已同步项目状态、实验索引、数据目录、版本总表和主计划，明确运行中/已准备的区别。next_task=T10-D，正式门禁不变。

### L186 — 2026-11-16 — T10-D — RESET_COMPARISON_BEGIN

- 恢复上次任务。`python -` 重算主实验与重置题单的输入/输出摘要及主实验身份文件，全部一致；主运行已完成54/54、0失败、0跳过，见[metrics](../data/defense_v1_runs/multiturn-ia-session-20261113-01/metrics.json)。GPU检查正常。下一步运行冻结的18个重置会话，随后进行配对审计。next_task=T10-D。

### L187 — 2026-11-16 — T10-D — RESET_COMPARISON_RUNNING

- 执行 `python -u scripts/run_defense_v1_benchmark.py --experiment-spec data/defense_datasets/multiturn_ia_reset_v2_train_20261113_01/experiment_spec.json --output-root data/defense_v1_runs/multiturn-ia-reset-20261116-01`，工具会话23128，模型已加载；预期18个请求，最终状态以运行清单为准。

### L188 — 2026-11-16 — T10-D — RESET_COMPARISON_COMPLETE

- L187命令退出0，18/18完成，0失败/跳过。执行 `python reports/defense_v1/T10/audit_type_policy_run.py data/defense_v1_runs/multiturn-ia-reset-20261116-01 reports/defense_v1/T10/multiturn_ia_reset_audit_20261116.json` 及同命令对主运行审计，均退出0。执行 `python reports/defense_v1/T10/compare_multiturn_ia_20261113.py reports/defense_v1/T10/multiturn_ia_session_audit_20261116.json reports/defense_v1/T10/multiturn_ia_reset_audit_20261116.json reports/defense_v1/T10/multiturn_ia_comparison_20261116.json`，退出0。
- 12个IA请求中V2连续会话拒答5次、重置会话全部放行；6个库内请求的目标原文交付分别3和6次，两个库内来源均在早期已有交付。按4篇来源的工程样本描述，非总体泄露估计。重置同时移除会话判断和交付历史，不能拆解各自因果贡献。下一步普通问法与填空问法对照。next_task=T10-D。

### L189 — 2026-11-16 — T10-D — STYLE_COMPARISON_RUNNING

- 执行 `python -u scripts/run_defense_v1_benchmark.py --experiment-spec data/defense_datasets/benign_style_pair_v2_train_20261113_01/experiment_spec.json --output-root data/defense_v1_runs/benign-style-pair-20261116-01`，工具会话24832，预期18请求事件。题单摘要与身份于L185核验；结果以运行清单及逐题证据为准。

### L190 — 2026-11-16 — T10-D — STYLE_COMPARISON_COMPLETE

- L189命令退出0，18/18完成、0失败跳过。执行 `python reports/defense_v1/T10/audit_type_policy_run.py data/defense_v1_runs/benign-style-pair-20261116-01 reports/defense_v1/T10/benign_style_pair_audit_20261116.json` 退出0。三道普通问句在三方法均交付参考原文并包含必要事实；三道填空在B2拒答，V2两拒答、一过滤后证据不足。由agent逐题核对，授权未知。两项补试结果及限制见[报告](../reports/defense_v1/T10/SUPPLEMENT_RESULTS_20261116_ZH.md)。
- next_task=T10-D，继续补独立来源和实际人员审核；T10-E、正式指标与独立终测未验收。

### L191 — 2026-11-17 — T10-D — DEFENSE_COMPARISON_PLAN_CONFIRMED

- 用户确认后续执行方案。沿用冻结 Judge v3、原索引及 v2 train 开发入口。主比较使用 B0、B2、B_TYPE_V2，保留 B3 无检索上下文回答和 B6 摘要作为辅助对照。Judge v3 的已完成识别结果仍按历史 v1 test 报告。
- 先读多轮与正常题的既有逐请求记录。记录每个 IA 会话首次交付目标原文与首次限制的轮次。对正常题记录风险触发，并区分原检索缺证据、策略扣下证据、证据保留后仍答错。随后固定独立来源和题单，覆盖四类 MIA、库内与库外文档、常规与困难正常问答。
- 正式评估依次完成 T10-E 真人审核、T11 指标验收和 T12 动作对照，再按协议冻结并独立终测。比较四类成员推断指标与有证据支持的正常正确率，按独立来源分组报告配对差值及置信区间。
- 本次只同步台账、主计划、实验协议、项目状态和实验索引。使用 PowerShell `Get-Content` 读取现有文档及状态，再用 `apply_patch` 更新。没有新运行、数据版本或门禁验收。next_task=T10-D，首项交付为两张逐题复核表。

### L192 — 2026-11-17 — T10-D — EXISTING_CASES_AUDITED

- 使用项目解释器 `python -` 读取多轮及正常题既有审计 JSON，按会话与方法求首次交付和限制轮次，逐题联结正常题评审和执行结果。输出[两张复核表](../reports/defense_v1/T10/NEXT_STEP_CASE_AUDIT_20261117_ZH.md)。核对 12 个 IA 方法与会话组合和 14 道 V2 正常题。两篇库内来源均在首轮向回答模型交付，首次限制分别在第 2、3 轮。3 道未得到正确且有证据回答的正常候选均在检索后失去必要证据。
- 复核沿用开发样本和 agent 标注，未启动模型、未新增数据或正式结果。下一步固定较小的配对样本并准备真人审核，优先验证同等保护下的正常效用和早期原文交付。next_task=T10-D。

### L193 — 2026-11-17 — T10-D — TWO_HOUR_PAIRED_BEGIN

- 用户启动两小时 Goal，复用 L192。先核对最新版本、运行身份及 GPU，再固定四攻击与正常题的同题开发对照，运行 B0/B2/B_TYPE_V2。结果为 engineering_only，真人 gold 和正式门禁保持待验收。

### L194 — 2026-11-17 — T10-D — TWO_HOUR_COHORT_FIXED

- 执行 `python reports/defense_v1/T10/build_two_hour_paired_20261117.py` 退出0，重算三个父题单输出、冻结身份和生产代码摘要。固定41请求，包括15个既有攻击、4组三轮IA和14个正常请求，预计123请求事件。所有来源已用于开发，非独立终测。见[题单manifest](../data/defense_datasets/two_hour_paired_v2_train_20261117_01/manifest.json)。下一步启动真实回放。

### L195 — 2026-11-17 — T10-D — TWO_HOUR_PAIRED_RUNNING

- 执行 `python -u scripts/run_defense_v1_benchmark.py --experiment-spec data/defense_datasets/two_hour_paired_v2_train_20261117_01/experiment_spec.json --output-root data/defense_v1_runs/two-hour-paired-20261117-01`，工具会话23828，模型已加载，预期123事件。终态以运行清单为准。

### L196 — 2026-11-17 — T10-D — TWO_HOUR_CHECKPOINT

- `python -` 读取会话分片，最近一次完整分片计65事件：B0 41、B2 24，进程23828仍运行。新增汇总脚本 `reports/defense_v1/T10/summarize_two_hour_20261117.py`，按实际响应复用完全匹配的既有agent审核，并将Masked解析失败与可评分分母分开。汇总脚本尚未执行，最终分母以运行输出和审计为准。
- 后续先完成本批三方法配对与核验；Direct、S²各仅一个库内目标，最终按实际分母描述。若剩余时间允许再补不同目标，不将新旧条件混入同一未经校准的结论。next_task=T10-D。

### L197 — 2026-11-17 — T10-D — TWO_HOUR_PAIRED_COMPLETE

- L195运行命令退出0，123/123完成，0失败、0跳过。执行 `python reports/defense_v1/T10/audit_type_policy_run.py data/defense_v1_runs/two-hour-paired-20261117-01 reports/defense_v1/T10/two_hour_paired_audit_20261117.json` 和 `python reports/defense_v1/T10/summarize_two_hour_20261117.py` 均退出0，核验输入摘要、逐请求覆盖、账本和实际生成输入。
- 14道正常题的42个输出与既有agent评审逐项匹配，B0/B2/V2正确且参考证据交付分别14/11/11；开发来源及权限限制见[结果报告](../reports/defense_v1/T10/TWO_HOUR_PAIRED_REPORT_20261117_ZH.md)。四类按成员身份分组，Direct和S²原方向描述AUC的库内目标仅1篇；Masked格式和IA评分/预算不适合直接计算，独立校准TPR/FPR未评估。不是正式E01或成员泄露显著性结论。
- 下一步按T10-D补不同来源及真人审核，明确目标分组、评分和攻击校准；T10-E和正式门禁保持未完成。

### L198 — 2026-11-17 — T10-D — MULTI_ACTION_GOAL_BEGIN

- 用户启动多动作策略 Goal。`python -` 复算最近123次运行的17项输入身份及生产代码摘要，全部一致；GPU RTX A5000可用，`git rev-parse --show-toplevel` 确认项目非 Git 仓库。
- 候选预设两个版本：继承V2的放行、拒答、过滤、IA无上下文、历史原文与权限范围处理，仅对高风险单一S²改为摘要或无上下文两种候选。摘要处理器会接触允许范围内的原文，输出可能保留敏感事实，须以实际artifact核查；未知/冲突继续拒答。候选均独立命名，并对照V2和B2，按同题安全与正常效用比较，不预设较温和动作更优。
- 计划先补必要分支与权限/失败测试，再固定题单与候选运行身份。next_task=T10-D，正式T10-E与终测门禁不变。

### L199 — 2026-11-17 — T10-D — MULTI_ACTION_TEST_CHECKPOINT

- 按测试驱动执行 `python -m pytest tests/test_defense_benchmark.py -k 'type_policy_uses_online_types and B_MULTI' -xq --tb=short`，首次因候选不存在退出1。新增 `B_MULTI_SUMMARY`、`B_MULTI_NO_CONTEXT` 后相同测试6 passed；两者仅修改高风险单一S²分支，其他继承V2。执行 `python -m pytest tests/test_defense_benchmark.py tests/test_defense_action_executor.py tests/test_exposure_store.py tests/test_evidence_locator.py tests/test_query_cue.py tests/test_two_stage_gateway.py tests/test_online_judge_adapter.py tests/test_frozen_risk_scorer.py -q --tb=short`，74 passed、3依赖弃用警告。
- 摘要输入证据通过账本 `transform_input_evidence` 记录，允许范围在首次检索和回填中复用。摘要失败现有执行器回退无上下文；需在候选实验中单列该行为和摘要敏感内容检查。下一步固定包含证据不足任务的新开发题单及多方法配置。

### L200 — 2026-11-17 — T10-D — MULTI_ACTION_COHORT_FIXED

- 执行 `python reports/defense_v1/T10/build_multi_action_20261117.py` 退出0。复算父题单输入/输出及运行身份，固定43问，包括41条既有开发请求与2条新证据不足任务。两条新题由可信的模拟应用允许集合限定至一篇原文，agent确认原文未包含所问信息。均非真人 gold。
- 在查看新回答之前固定 B0/B2/B_TYPE_V2、摘要候选、无上下文候选及B3/B6辅助对照，预期301请求事件。[题单及假设](../data/defense_datasets/multi_action_v2_train_20261117_01/manifest.json)。已见来源不能作为独立终测；两项候选先比较安全及正常效用，未预设胜出方法。next_task=T10-D。

### L201 — 2026-11-17 — T10-D — MULTI_ACTION_CANDIDATES_RUNNING

- 执行 `python -u scripts/run_defense_v1_benchmark.py --experiment-spec data/defense_datasets/multi_action_v2_train_20261117_01/experiment_spec.json --output-root data/defense_v1_runs/multi-action-candidates-20261117-01`，工具会话12577，模型分片已加载。运行身份与结果以[manifest](../data/defense_v1_runs/multi-action-candidates-20261117-01/run_manifest.json)为准，预期301事件。若中断，先确认原进程已停止及身份一致，再按原命令增加 `--resume`。

### L202 — 2026-11-17 — T10-D — MULTI_ACTION_EXPOSURE_TEST

- 扩展类型策略测试覆盖候选的Masked原词拒答、过滤回填失败、低风险放行，以及摘要处理器输入与回答模型接收的证据类型和可信允许范围。执行L199同一相关回归命令，77 passed、3依赖警告，退出0。测试文件变更未改变正在运行的生产代码或身份。
- 编写 `reports/defense_v1/T10/review_multi_action_20261117.py`，待运行结束按相同响应、动作和交付分组导出正常题agent复核单元，列出所有摘要处理器输入与交付内容。尚未生成评审结论。

### L203 — 2026-11-17 — T10-D — MULTI_ACTION_SOURCE_EXPANSION_FIXED

- 主运行期间，执行 `python reports/defense_v1/T10/build_multi_action_sources_20261117.py` 退出0，事先固定19个攻击请求/5方法95事件：[来源扩展清单](../data/defense_datasets/multi_action_sources_v2_train_20261117_01/manifest.json)。Direct/S²/Masked 各3库内、2库外来源，IA 各2来源；来源均在v2 train，部分曾用于历史开发，不作独立终测。选择于当前候选结果揭晓前固定。
- `python -` 对5条Masked请求逐项核对遮蔽恢复与原始目标文档逐字一致，未遮蔽部分无答案复现，见[预检](../reports/defense_v1/T10/multi_action_sources_preflight_20261117.json)。IA延用已预审问题但缺主题锚点，后续解释检索失败。扩展题单尚未启动GPU运行，待主运行结束串行执行。

### L204 — 2026-11-17 — T10-D — CANDIDATE_SELECTION_RULE

- 在任何候选方法结果落盘前，进一步明确开发选择口径：先核验覆盖和权限约束，再分别展示可回答正常题有证据正确数、证据不足题合理不答、各类攻击的目标原文交付与输出诊断。相对V2若某候选有任何正常题有证据正确结果由对变错，或任一同题目标原文新增交付，不能宣称全面优于V2。此规则用于案例筛选，不能以极小开发样本替代正式隐私—效用约束或成员推断效果。
- 两候选都有独立身份，若比较未显示优势或仅有不同风险取舍，保留二者和原V2并记录未选出优胜者；不强行根据拒答次数选赢家。主比较仍包含四类攻击、正常题及指定辅助动作。

### L205 — 2026-11-17 — T10-D — MULTI_ACTION_RUNNING_CHECKPOINT

- 核查工具会话12577及实际Python进程仍运行；读取已完整保存的session分片，共84/301事件（B0 43、B2 41），其他方法尚待运行。分片计数只是检查点，最终以manifest及完整审计为准。扩展来源运行仍须等待主运行结束后串行启动。
- 新增 `reports/defense_v1/T10/summarize_multi_action_20261117.py`，为两个已固定题单分别汇总攻击动作、原文交付、可评分槽位、描述性AUC、正常动作和延迟；不将IA或Masked不适用的评分强算为AUC，正常问答质量仍需单独逐题复核。首次 `python -m py_compile` 发现汇总脚本括号错误并修正，再运行相同命令对汇总和评审导出脚本进行编译检查，退出0。尚无新实验汇总或策略胜出结论。next_task=T10-D。
- 通过 `python -` 用历史已审计的 two-hour 运行试调用汇总函数，核对 B0 正常数14、B2 拒答3及攻击分组24，退出0。同步台账顶部的恢复点、运行状态与下一步；主实验仍在运行。

### L206 — 2026-11-17 — T10-D — MULTI_ACTION_DESIGN_DOCUMENTED

- 将两个开发候选的分支、会话与可信权限边界、摘要处理器接触原文的事实补充到[规格](superpowers/specs/2026-10-22-defense-framework-design.md)，并在[实验协议](DEFENSE_EXPERIMENT_PROTOCOL_ZH.md)标明题单、审核与指标边界；没有改变正式门禁或将候选标为胜出。首次 `apply_patch` 因协议匹配行不完整而失败，随后按标题分别重试成功。摘要复核导出器增加目标连续八词及 Masked 答案的机械提示，仍需人工式逐项语义检查，不能将无匹配当作无泄露。next_task=T10-D。

### L207 — 2026-11-17 — T10-D — PERMISSION_AUDIT_PREPARED

- 编写 `reports/defense_v1/T10/audit_multi_action_permissions_20261117.py`，用于运行结束后核对显式允许集合约束下的检索、摘要输入及原文交付；摘要本身是聚合对象，其来源需从处理器输入核查。`python -m py_compile` 对该脚本和评审导出器退出0。以历史运行试运行审计器退出0，旧运行受限事件为0，故不构成权限约束的实证检验；本批两个证据不足题使用显式可信模拟集合，待完成后检查。[旧运行审计](../reports/defense_v1/T10/two_hour_allowlist_audit_20261117.json)。
- 会话分片检查主对照累计104/301事件（B0、B2各43，V2为18），进程仍运行。完成后再进行正式覆盖审计；扩展来源仍未启动。next_task=T10-D。

### L208 — 2026-11-17 — T10-D — REPORT_AND_REVIEW_PREPARATION

- 建立[中文报告草稿](../reports/defense_v1/T10/MULTI_ACTION_REPORT_20261117_ZH.md)，逐项说明已实现的访问动作与摘要处理边界，明确主实验运行中、扩展题单未运行；没有填写预期指标。评审导出分组增加实际交付证据文本摘要，避免同名摘要但内容不同时错误地复用答案审核。汇总脚本补充风险触发和类型命中计数；均待新运行完成后实测。
- 用 `python -` 构造一条带文档允许集合的合成事件验证权限审计器：允许来源生成的聚合摘要通过，处理器输入含集合外文档时返回1并定位 transform 阶段；断言全部通过。另以 `python -m py_compile` 检查汇总及复核脚本，退出0。主运行分片最近计122/301（B0 43、B2 43、V2 36），仍在执行。

### L209 — 2026-11-17 — T10-D — BASELINES_FINISHED_CANDIDATES_RUNNING

- `python -` 读取完整会话分片，最近计131/301：B0、B2、V2各43，摘要候选2；进程12577仍运行。分片仅供检查，最终状态和统计待manifest与审计核对。
- 以 `apply_patch` 修正[项目状态](PROJECT_STATUS_ZH.md)和[实验索引](EXPERIMENT_INDEX_ZH.md)的旧下一步及“无真实效果运行”措辞，区分已存在的真实开发对照和未完成的正式效果实验；没有改动正式门禁。next_task=T10-D。
- `python -` 从已完整保存的前三组会话分片读取16道正常题输出，结合题单参考答案逐题初看：两道证据不足任务在B0/B2/V2均回答证据不足（6/6），三组均记录交付受限参考原文。此为agent开发初审，候选输出与完整证据链待运行结束后统一核验，不是人工gold或最终指标。

### L210 — 2026-11-17 — T10-D — REPORT_BASELINE_VERIFIED

- 读取历史 `data/judge_score_comparison_v3_20261015/final_test_comparison.json` 和实验索引，向多动作报告写入历史v1 test的Judge识别指标及两阶段覆盖、已查看test限制。同期修正实验索引中将真实开发对照误写为“未开始”的一处旧表述；没有将识别率当作防御效果。
- 最近分片计153/301：B0、B2、V2各43，摘要候选24。主进程仍运行，下一步依次核验主运行、启动来源扩展。next_task=T10-D。

### L211 — 2026-11-17 — T10-D — SUMMARY_CANDIDATE_CHECKPOINT

- `python -` 读取摘要候选完整会话分片，B0/B2/V2/摘要候选各43，合计172/301；主运行继续。摘要候选动作计放行23、拒答16、过滤回填2、无上下文1、摘要1。两条S²题中库内目标的在线疑似类型为Masked，实际过滤回填；库外题识别为S²，实际摘要，摘要处理器输入为四篇检索到的库内文章，回答提示证据不足。此为分片初查，不能把离线真实类型代入在线策略，也不能仅凭一条摘要评估安全性；完整覆盖、摘要敏感内容和扩展来源待核验。
- 修正报告对B3/B6的说明，明确仅高风险触发后使用无上下文/摘要，低风险放行。next_task=T10-D。
- `python -` 比较V2与摘要候选已保存分片的16个正常请求，动作、回答和交付文档ID均相同；证据正文摘要、完整分母与单题判定仍待最终运行审计。此结果不代表其他正常查询不存在差异。

### L212 — 2026-11-17 — T10-D — PAIRED_DIAGNOSTIC_PREPARED

- 汇总脚本增加按同一请求、攻击类型和成员身份分别与B0/V2比较的目标原文交付变化，保留“减少”和“新增”两个方向及不同来源数。`python -` 用已审计历史记录校验，复现Masked库内B0 4/4交付、V2 0/4、配对减少4次，退出0。原文交付只是证据诊断，不能替代成员推断成功率或独立来源置信区间。
- 最近分片计186/301，其中无上下文候选14；主运行继续。next_task=T10-D。

### L213 — 2026-11-17 — T10-D — PRIMARY_METHODS_FINISHED

- `python -` 从完整会话分片计数，五个核心方法 B0、B2、V2、摘要候选、无上下文候选各43，共215/301；剩余B3/B6辅助对照，主进程仍运行。
- 以 `python -` 按正常请求逐一比较两个候选与V2，16题的动作、回答及所交付证据的来源、类型和内容SHA256全部一致；这是分片层面的agent核对，最终覆盖和可回答质量仍待完整审计。next_task=T10-D。
- `python -` 将前三组14道可回答题的响应、动作和参考原文交付与既有 agent 评审匹配，均匹配14/14；正确且参考证据交付分别B0 14、B2/V2 11。由候选与V2的完整证据摘要相同可复用同一初查。两道证据不足任务五组回答相同且说明不足。[报告草稿](../reports/defense_v1/T10/MULTI_ACTION_REPORT_20261117_ZH.md)已注明是完整审计前观察，不代表正式gold。

### L214 — 2026-11-17 — T10-D — NO_CONTEXT_COMPLETION_CASE

- `python -` 对三种类型策略的已保存攻击输出进行逐请求比较：库外 S² 请求 `fp_2aa0120a432b1cb0ca6cf002` 在V2拒答、摘要候选回答证据不足、无上下文候选将问题末尾 `power......` 补为 `power adapters`。该词也在目标材料中，但问题已提供Dell、电源等前缀；模型可能由语言规律或参数知识补出，不能判定为库内原文泄露。该案例说明无上下文不保证无补全，应观察成员/非成员分布和攻击者可见输出；最终评分及扩展来源尚未完成。
- 该案例已写入[报告草稿](../reports/defense_v1/T10/MULTI_ACTION_REPORT_20261117_ZH.md)。会话分片最近计252/301（五个核心方法各43、B3 37），主进程仍运行，B6待执行。

### L215 — 2026-11-17 — T10-D — SUMMARY_BASELINE_RUNNING

- `python -` 读取主运行会话分片，B3已完成43，B6已保存13，共271/301；摘要处理记录中可见B6生成器读取库内目标原文并向回答模型交付摘要。该观察只验证处理路径，不评价摘要是否充分去敏；须在完整审计中逐项检查原词和关键事实。next_task=T10-D。

### L216 — 2026-11-17 — T10-D — MULTI_ACTION_MAIN_COMPLETE

- L201真实运行退出0，301/301完成、0失败/跳过。执行 `python reports/defense_v1/T10/audit_type_policy_run.py data/defense_v1_runs/multi-action-candidates-20261117-01 reports/defense_v1/T10/multi_action_candidates_audit_20261117.json`，退出0，核对身份、事件覆盖、摘要及交付证据摘要。[审计产物](../reports/defense_v1/T10/multi_action_candidates_audit_20261117.json)。
- 执行 `python reports/defense_v1/T10/audit_multi_action_permissions_20261117.py data/defense_v1_runs/multi-action-candidates-20261117-01 reports/defense_v1/T10/multi_action_candidates_permissions_20261117.json` 退出0，14个显式限制事件无越界，其中摘要事件0，因此不证明真实摘要处理的受限案例；执行 `python reports/defense_v1/T10/review_multi_action_20261117.py` 退出0，导出26个正常复核单元、21个摘要处理单元，待逐项检查。
- 初步动作诊断：各方法攻击目标原文交付请求B0 13、其他方法3；Masked已评分槽位B0恢复21/35、B2/V2/两候选0/35、B3 7/35、B6 9/35（包含库内与库外，不等同成员推断成功率）。来源重复、依赖及拒答信号均需单列。下一步串行运行固定的来源扩展。next_task=T10-D。

### L217 — 2026-11-17 — T10-D — SOURCE_EXPANSION_RUNNING

- 执行 `python -u scripts/run_defense_v1_benchmark.py --experiment-spec data/defense_datasets/multi_action_sources_v2_train_20261117_01/experiment_spec.json --output-root data/defense_v1_runs/multi-action-sources-20261117-01`，工具会话26661，模型已加载，预期95事件。主运行已结束后才启动；终态以新运行清单为准。并行进行主运行正常质量与摘要逐项复核，不启动其他GPU任务。

### L218 — 2026-11-17 — T10-D — NORMAL_AGENT_REVIEW_COMPLETE

- 逐项阅读26个正常复核单元、参考答案、交付证据与三道B6摘要；编写并执行 `python reports/defense_v1/T10/review_multi_action_normal_20261117.py` 退出0，保存[agent逐题结果](../reports/defense_v1/T10/multi_action_normal_agent_review_20261117.json)，记录复核输入SHA。14道可回答题B0正确且有证据14/14，其余六方法11/14；两道证据不足题各方法均合理不答2/2。三道受损题均风险触发且原检索包含必要来源：B2三题拒答，V2/两候选两题拒答一题过滤，B3三题移除上下文，B6三题摘要漏掉必要事实。一个Treo摘要还将“更少存储空间”写成“更慢存储”，属于摘要事实失真提示。
- 这是已选小批及agent判断，不是人工gold或总体效用估计。来源扩展运行仍在进行；下一步逐项核查21个摘要攻击输入与输出。next_task=T10-D。

### L219 — 2026-11-17 — T10-D — SUMMARY_AGENT_REVIEW_COMPLETE

- 逐项读取21次摘要处理输入与摘要，针对目标原文、Masked答案和实际摘要人工式检查；执行 `python reports/defense_v1/T10/review_multi_action_summary_20261117.py` 退出0，产出[agent复核](../reports/defense_v1/T10/multi_action_summary_agent_review_20261117.json)，记录输入SHA。13次处理器输入含对应目标（其中3次为正常题），两次Masked摘要出现目标遮蔽词：`weapons-for-cash`及常见词`Officials`。前者摘要还保留伊拉克扩大该项目的事实，后者保留CIA官员辞职信息，不能把摘要视为自动去敏。另有若干摘要保留太空站换人或菲律宾洪灾等事实；精确词不出现不能证明语义不泄露。
- 正常摘要均遗漏所需答案，Treo摘要对存储容量的表述还有潜在失真。部分摘要涉及多篇来源，未对所有额外陈述逐句验真；两道可信允许范围题均未触发摘要，本批权限实测不覆盖“摘要+受限集合”组合。来源扩展继续运行，下一步审计扩展并汇总。next_task=T10-D。

### L220 — 2026-11-17 — T10-D — REPORT_AND_SOURCE_CHECKPOINT

- 通过 `python -` 对已审计主运行调用汇总函数，核对16道正常题的各方法动作、风险触发及延迟；将[agent质量结果](../reports/defense_v1/T10/multi_action_normal_agent_review_20261117.json)、摘要复核及七方法正常质量/延迟表写入[中文报告](../reports/defense_v1/T10/MULTI_ACTION_REPORT_20261117_ZH.md)，标记小样本、固定顺序和非人工gold限制。
- 更新项目状态、实验索引、数据目录、版本总表与台账顶部：主运行完成，来源扩展运行中。扩展会话分片最近计28/95（B0 19、B2 9），进程26661仍在运行。最终结果及候选选择待扩展完成。next_task=T10-D。

### L221 — 2026-11-17 — T10-D — SOURCE_SUMMARY_REVIEW_PREPARED

- 编写 `reports/defense_v1/T10/export_source_summary_units_20261117.py`，扩展运行完成后校验每个摘要artifact摘要并导出来源、交付内容和遮蔽词匹配，供agent逐项复核；通过 `python -m py_compile` 检查该脚本与主运行两份复核脚本，退出0。目标原文不在摘要输入时仍不排除模型参数知识；机械原词匹配不代替语义审核。
- 扩展运行分片最近计40/95：B0/B2各19、V2 2，进程26661仍运行。next_task=T10-D。

### L222 — 2026-11-17 — T10-D — SOURCE_BASELINES_FINISHED

- `python -` 读取扩展运行完整会话分片：B0、B2、V2各19，摘要候选2，共59/95；进程26661仍运行。此前主实验摘要复核的两个遮蔽词 `weapons-for-cash` 和 `Officials` 已核对原攻击问题，均对应实际遮蔽位置，未在问题明文出现；摘要中出现不直接等于最终回答恢复或成员推断成功。next_task=T10-D。

### L223 — 2026-11-17 — T10-D — IMPLEMENTATION_PLAN_UPDATED

- 更新[实施计划](superpowers/plans/2026-10-22-defense-framework-implementation.md)中的回归数、主运行完成和agent复核状态，将来源扩展与最终候选选择保持未勾选。`python -` 分片计数最近68/95，扩展摘要候选11条，进程26661仍运行。next_task=T10-D。

### L224 — 2026-11-17 — T10-D — SOURCE_SUMMARY_PRELIMINARY

- `python -` 读取来源扩展摘要候选已完成的19个分片并对照S²目标原文：5次摘要中3次含库内目标作为处理器输入，分别保留服务业增长、Chelsea球员进制胜球、Steelers球员与对手旧账等部分目标事实；两次库外目标未进入输入。摘要可保留事实，不可仅用原文未交付作为隐私安全证明。此为分片初查，所有方法结果、完整artifact核验及攻击评分待终态。next_task=T10-D。

### L225 — 2026-11-17 — T10-D — SOURCE_EXPANSION_COMPLETE

- L217命令退出0，95/95完成、0失败/跳过。执行 `python reports/defense_v1/T10/audit_type_policy_run.py data/defense_v1_runs/multi-action-sources-20261117-01 reports/defense_v1/T10/multi_action_sources_audit_20261117.json`、`python reports/defense_v1/T10/audit_multi_action_permissions_20261117.py data/defense_v1_runs/multi-action-sources-20261117-01 reports/defense_v1/T10/multi_action_sources_permissions_20261117.json` 和 `python reports/defense_v1/T10/export_source_summary_units_20261117.py` 均退出0；扩展题单无显式允许集合，故权限审计受限事件为0。执行 `python reports/defense_v1/T10/summarize_multi_action_20261117.py` 退出0，保存[两批汇总](../reports/defense_v1/T10/multi_action_summary_20261117.json)。
- 扩展组B0库内Direct三题均yes，B2/V2/两候选各两题yes、一题拒答；一条库内Masked被判低风险并放行，五个原词全部恢复。两条库内Direct、该Masked及一条库内IA的风险分数均0.00317，未达Query-only阈值，四种防御均交付目标原文。样本小且已用于开发，不能据此估计总体漏检率。下一步复核扩展摘要、按预设规则比较并完成报告。next_task=T10-D。

### L226 — 2026-11-17 — T10-D — MULTI_ACTION_REVIEW_AND_REPORT_COMPLETE

- 逐条核查扩展的5次摘要，执行 `python reports/defense_v1/T10/review_source_summaries_20261117.py` 退出0，保存[agent复核](../reports/defense_v1/T10/multi_action_sources_summary_agent_review_20261117.json)：3篇库内目标进入摘要处理器，部分目标事实保留并出现在回答；另外2个库外目标未进入处理器，回答证据不足。多来源中的其他事实未全部验真。
- `python -` 从[两批汇总](../reports/defense_v1/T10/multi_action_summary_20261117.json)核查两候选相对V2的46个攻击同题比较，目标原文交付新增/减少均0；16个正常题的动作、回答和证据摘要相同。扩展S²原方向描述性AUROC的库内/库外仅3/2，受问题前缀复述和固定拒答与目标的相似度影响；不据此宣称显著隐私改善。按L204规则保留V2和两个候选，未选出全面优胜者。
- [中文报告](../reports/defense_v1/T10/MULTI_ACTION_REPORT_20261117_ZH.md)记录四类攻击、正常质量、识别与摘要结果及未评估指标。同步项目状态、实验索引、数据目录、版本总表、实施计划及本台账；真实人员gold、独立来源、校准、正式终测仍未完成。下一步在新固定开发数据上处理识别漏检、正常干预、多轮早期原文交付，并继续T10-E前准备。next_task=T10-D。

### L227 — 2026-11-17 — T10-D — DELIVERABLE_VERIFIED

- `python -` 核对两份manifest终态、301/95覆盖与零失败、metrics SHA256、当前生产策略源码SHA256、汇总指向的审计SHA256、7方法正常题复核分母与结果、两个候选相对V2的原文配对变化，以及中文报告20个本地链接；断言全部通过。代码相关回归为L202记录的77 passed、3项依赖弃用警告。报告新增扩展Direct描述性AUROC，与S²均注明微小样本及评分局限。
- 开发对照和可复核中文报告已交付；保留正式门禁未通过和agent审核身份，不以此宣称成员泄露整体显著下降。next_task=T10-D。

### L228 — 2026-11-17 — T10-D — NEXT_GOAL_PLAN_RECORDED

- 依据 L216–L227 和 396 次开发报告编制[下一轮执行清单](superpowers/plans/2026-10-22-defense-framework-implementation.md#t10-d-下一轮-goal)。优先处理低风险漏检、IA 首轮原文交付及正常任务证据损失，登记候选、真实配对、三张结果表、选择约束和 T10-E 审核准备。
- 使用项目 Python 的 `python -` 重算两批 metrics、各 17 项输入身份及生产代码 SHA256，断言两批 301/95 完成、零失败及跳过，退出 0。使用 `apply_patch` 同步实施计划、台账、状态、实验索引和协议，并纠正数据目录中的历史复核状态。本次产物为执行计划，候选实现、数据冻结、真实模型新运行和正式门禁均待执行。next_task=T10-D，第一步固定题单和判定规则。
- 用 `python -` 核对五项待办、四处跨文档入口、基线报告链接、L228 唯一性及数据目录复核状态。初次检查发现新旧清单间缺少标题，补齐后同一检查通过。

### L229 — 2026-11-17 — T10-D — NEXT_GOAL_STARTED

- 用户启动下一轮 Goal。通过 PowerShell `Get-Content` 阅读 AGENTS.md、项目状态、数据目录、实验索引、版本总表、本台账和实施计划；当前恢复点为 T10-D。下一步复核两批运行身份和漏检 trace，整理题单来源与会话，冻结配对和评分。新实验尚未运行，正式人工 gold 待完成。

### L230 — 2026-11-17 — T10-D — BASELINE_AND_MISS_TRACE_VERIFIED

- 使用项目解释器运行 `python -`，重算主运行和来源扩展的 metrics、17项输入身份与生产代码摘要，核对301/301和95/95、无失败或跳过，全部通过。读取规格、实验协议和现有策略实现。
- `python -` 联结扩展运行 `requests.jsonl` 与 `events.jsonl` 复查4个库内漏检。四题Query-only均为0.00317268，低于0.00669285阈值，疑似类型为空，策略按低风险放行。其中两条Direct已检测到 `quoted_context_check`，一条Masked已检测到 `masked_recovery`，但V2低风险分支未使用这些线索；IA题没有现有线索。该观察来自已见开发例，不能估计总体漏检率。下一步固定不同来源的题单及线索误伤对照，然后开发独立候选。next_task=T10-D。

### L231 — 2026-11-17 — T10-D — SOURCE_INVENTORY_STARTED

- `python -` 读取v2 bank和v2 split，确认train含60篇文档、4579条查询。扫描 `data/defense_v1_runs/*/labels.jsonl`，38个train文档曾出现在运行标签中，22个未出现且均为库外编号。仅证明这些文件中的文档ID使用情况，尚未完成事件近重复或历史查询使用核查，且包含部分可能未实际完成的运行。扫描全部防御题单标签会把尚未运行的overlay也算作已用，故另行保留该范围，不把其作为运行证据。
- 下一步检查题单原文及正常题、IA会话可用性，选择已见库内和相对未见库外来源并标记限制，完成配对前固定。next_task=T10-D。

### L232 — 2026-11-17 — T10-D — SOURCE_INVENTORY_SAVED

- 运行项目解释器 `python -`，建立[来源盘点](../reports/defense_v1/T10/next_goal_source_inventory_20261117.json)，记录v2 train 60篇的成员身份、两批近期题单使用情况、各运行标签文件中的引用、原文SHA256、各攻击/正常题数量，以及与近期目标的词集合重合筛查。近期两批题单之外有8篇库内、22篇库外；前者也可能用于更早实验。记录所有读取文件的摘要。
- 词集合重合仅用于初筛，不能证明事件独立；运行标签中出现不代表请求完成。下一步逐项核对目标原文、题目和多轮可用性，固定实际题单与分组。next_task=T10-D。

### L233 — 2026-11-17 — T10-D — CANDIDATE_SOURCE_PREFLIGHT

- `python -` 检查近期两批以外的8篇库内候选与若干库外候选的原文及旧IA问句。某Halo原文在句中截断，其IA问句需要慎重处理；NASA、印度板球等候选原文支持两条不同问句，仍须判断连贯性与检索歧义。库内来源均曾在更早运行的标签中出现，库外未在已扫描运行标签中出现；这只是ID层面的历史记录。
- 对4库内与4库外待选文档执行Mask结构预检，重建后的文本逐字等于目标，遮蔽词未在未遮蔽部分出现。40个旧overlay候选满足该结构检查，输入及文档SHA记录在[预检](../reports/defense_v1/T10/next_goal_mask_preflight_20261117.json)。预检不等于题单已冻结或真人gold，下一步固定攻击、正常题和连续会话及评分。next_task=T10-D。

### L234 — 2026-11-17 — T10-D — NEXT_GOAL_COHORT_FIXED

- 执行 `python reports/defense_v1/T10/build_next_goal_cohort_20261117.py`。首次运行在S²前缀的逐字匹配断言处退出1，核对发现两篇原文有连续空格而题库前缀折叠空格；改为只规范化空白后重跑退出0。输出[题单manifest](../data/defense_datasets/next_goal_v2_train_20261117_01/manifest.json)，47请求、4方法预期188事件。当前尚未实现 `B_NEXT_GOAL`，尚未运行模型。
- 题单包含Direct、S²、Masked各4库内/4库外，4个新建两轮IA会话（2库内/2库外），8道新正常题、5道历史正常回归（完整保留Treo三轮）及2道可信来源范围内证据不足题。正常引用逐字核对原文，Masked复用L233结构预检；IA问句是同事件不同事实，不能视作必然上下文依赖。库内目标都在更早运行标签出现，正式事件独立性未证明，全部为agent审核且非人工gold。
- 题单已登记候选方法、对照、评分和不新增原文/不降低正常质量的筛选规则。下一步在既有计划范围内实现候选与必要消融测试，新增源码须单独记录身份。next_task=T10-D。

### L235 — 2026-11-17 — T10-D — COHORT_SOURCE_GROUP_PREREGISTERED

- `python -` 核对8篇攻击目标原文，登记与历史正常回归分离的目标ID、事件主题、28对文档词集合相似度及输入摘要，保存[运行前登记](../reports/defense_v1/T10/next_goal_prereg_20261117.json)。最高token Jaccard 0.087；各文本主题不同，但短文词重合筛查不能证明事件独立。四篇库内来源曾在更早防御运行标签中出现，全部来源均被Judge训练使用。
- 使用前需完成候选实现，当前四方法配置尚未可运行；新增会话的两轮是同事件的不同事实，不宣称上下文推理。下一步开发独立策略并验证线上输入边界、正常误伤和多轮会话。next_task=T10-D。

### L236 — 2026-11-17 — T10-D — NEXT_POLICY_IMPLEMENTED

- 先扩展 `tests/test_defense_benchmark.py`，执行 `python -m pytest tests/test_defense_benchmark.py -k 'type_policy_uses_online_types and B_NEXT_GOAL' -xq --tb=short`，因候选未实现预期失败。实现 `B_NEXT_GOAL` 后同命令4 passed，补充历史原文与判断失败测试。执行 `python -m pytest tests/test_defense_benchmark.py tests/test_defense_action_executor.py tests/test_exposure_store.py tests/test_evidence_locator.py tests/test_query_cue.py tests/test_two_stage_gateway.py tests/test_online_judge_adapter.py tests/test_frozen_risk_scorer.py -q --tb=short`，83 passed、3项依赖弃用警告。
- 新候选保留V2高风险分支；低风险且命中现有长引用存在性检查线索或多Mask原词恢复线索时拒答。低风险且问题含 article/report 与明确 Yes/No/Unknown 输出格式时，历史无原文则无上下文回答，历史有原文则拒答。判断失败仍不可用，规则仅用在线查询和实际会话记录。此格式规则只是实验假设，可能拦截正常核对问题，须用冻结题单与更多正常题评估。尚未完成机制消融、替代证据评估或真实配对。next_task=T10-D。

### L237 — 2026-11-17 — T10-D — NEXT_GOAL_PAIRED_RUNNING

- 执行 `python -u scripts/run_defense_v1_benchmark.py --experiment-spec data/defense_datasets/next_goal_v2_train_20261117_01/experiment_spec.json --output-root data/defense_v1_runs/next-goal-paired-20261117-01`，工具会话85228，模型分片已加载，预期47请求×4方法=188事件。身份以[运行manifest](../data/defense_v1_runs/next-goal-paired-20261117-01/run_manifest.json)为准，终态待核验。机制消融和替代证据仍待完成，正式门禁未改变。next_task=T10-D。
- 使用 `python -` 验证题单manifest全部输出摘要、47个请求/标签/lineage ID一一对应、在线请求不含离线标签；检查到4个两轮IA会话及原Treo三轮会话。运行仍在进行，模型提示部分生成参数可能被忽略，最终以实际日志和manifest为准。

### L238 — 2026-11-17 — T10-D — ALTERNATE_EVIDENCE_SOURCE_FOUND

- `python -` 检查原索引中与正常题答案相关的文章。`ag_news_teacher_00000224` 明确称Merck召回Vioxx，`ag_news_teacher_00000589` 称Merck的Vioxx止痛药退出市场，可作为同一药名的候选替代证据；前者属于v2 train，后者未出现在v2 bank划分文档列表，但存在于原索引中。此处仅完成原文核查，尚未证实回填命中、真实模型回答正确或相关授权设置。
- 下一步固定可审计的模拟允许范围与过滤实验，实际验证替代文章能否回填并支持答案。主配对运行继续，避免同时启动GPU模型。next_task=T10-D。

### L239 — 2026-11-17 — T10-D — ALTERNATE_EVIDENCE_PREREGISTERED

- `python -` 固定[替代证据实验预登记](../reports/defense_v1/T10/next_goal_alternate_evidence_prereg_20261117.json)，记录问题、Vioxx参考答案、两篇模拟允许文档、受控排除的原文和期望回填文档、原始索引摘要及评分标准。此实验由实验控制指定排除文档，检验执行器与答案效果，不能作为在线定位准确率证据；同药品两篇报道是否为同一具体召回事件仍需谨慎判断。尚未运行，GPU与主配对串行使用。next_task=T10-D。

### L240 — 2026-11-17 — T10-D — ALTERNATE_RUN_PREPARED

- 新建 `reports/defense_v1/T10/run_next_goal_alternate_20261117.py`，设计为主运行完成后使用同一模型与索引比较允许与受控过滤回填，写独立manifest和完整回答、证据及运行状态，并核对模拟允许范围。脚本明确检查主运行completed后才加载模型。执行 `python -m py_compile reports/defense_v1/T10/run_next_goal_alternate_20261117.py` 退出0；尚未真实执行，脚本检查通过不证明回填或答案有效。next_task=T10-D。

### L241 — 2026-11-17 — T10-D — FIRST_TURN_ABLATION_PREPARED

- 候选结果生成前固定[首轮消融口径](../reports/defense_v1/T10/next_goal_ablation_prereg_20261117.json)，对照V2在线判断分别模拟长引用/多Mask线索与IA格式线索，输出首轮按流量的动作变化。新建 `reports/defense_v1/T10/ablate_next_goal_first_turn_20261117.py`，用实际V2与候选风险及动作校验可比性，并标记不一致，执行 `python -m py_compile` 退出0。该消融只检查决策，不产生反事实生成回答；后续轮因真实交付历史可能改变而不做反事实推断。
- `python -` 检查主运行完整会话分片，最近57/188（B0 47、B2 10）；工具会话85228经 `write_stdin` 确认仍在运行。下一步完成主配对、执行审计及首轮消融，串行执行替代证据实验。next_task=T10-D。

### L242 — 2026-11-17 — T10-D — HUMAN_REVIEW_PACKET_PREPARED

- 执行 `python reports/defense_v1/T10/build_next_goal_human_review_packet_20261117.py` 退出0，创建[开发题真人审核包](../reports/defense_v1/T10/next_goal_human_review_packet_20261117/manifest.json)，包含47单元（正常15、攻击32）、原文/参考答案和[审核交接单](../reports/defense_v1/T10/next_goal_human_review_packet_20261117/HUMAN_REVIEW_GUIDE_ZH.md)，输入输出摘要均已记录，未包含membership_label。当前没有真人审核结果，题单为v2 train开发样本，不能直接充当独立正式T10-E效果数据。
- 主配对仍在运行。下一步收集真实输出与统计，同时准备符合独立划分要求的正式T10-E材料，不能将本包记为正式门禁完成。next_task=T10-D。

### L243 — 2026-11-17 — T10-D — BENIGN_IA_STYLE_CONTROLS_FIXED

- 为检验IA格式规则的正常影响，在主运行候选输出前执行 `python reports/defense_v1/T10/build_next_goal_ia_style_normal_20261117.py`，退出0，固定[4题正常阅读对照](../data/defense_datasets/next_goal_ia_style_normal_20261117_01/manifest.json)，两个Yes、两个No，各有原文事实与模拟可信允许集合，计划4方法16事件，主运行后串行执行。第一题与一条IA问题字面相同，但使用正常阅读任务标签和不同允许集合；这体现线上文字形式无法单独确定用户意图，不把离线标签输入策略。题目及答案由agent编写并待真人审核，不属于独立正式测试。
- 新建 `export_next_goal_review_20261117.py` 和 `summarize_next_goal_20261117.py`，待主运行审计后导出有实际证据的正常复核单元并汇总，`python -m py_compile` 退出0。尚无运行结果。next_task=T10-D。

### L244 — 2026-11-17 — T10-D — BENIGN_CONTROL_REVIEW_PACKET

- `python -` 对照主题单和IA格式正常对照，确认首题查询逐字相同、session不同、正常任务带应用提供的允许集合；这一区别在运行记录中保留，不能据离线标签声称在线判断意图准确。
- `python -` 生成[4题正常对照真人审核包](../reports/defense_v1/T10/next_goal_ia_style_human_review_20261117/manifest.json)，包括原文、参考答案和审核要求，未包含membership_label；待审核，非独立正式数据。主运行及16事件对照均未完成。next_task=T10-D。

### L245 — 2026-11-17 — T10-D — T10E_DDEV_HUMAN_PACKET_PREPARED

- 执行 `python reports/defense_v1/T10/build_t10e_ddev_human_review_20261117.py` 退出0，为已二次模型预审并修订的candidate06 D-dev试点生成[86条真人审核包](../reports/defense_v1/T10/t10e_ddev_human_review_20261117/manifest.json)及[交接单](../reports/defense_v1/T10/t10e_ddev_human_review_20261117/HUMAN_REVIEW_GUIDE_ZH.md)，含70正常、16攻击、对应原文和候选答案。原候选、overlay和模型预审文件未改写。为避免锚定，逐题包不自动带模型意见，审核后可按request_id查对历史结果。
- `python -` 校验全部输入输出SHA、86个ID唯一、待审身份与无membership_label，退出0。此包为D-dev试点，非A-cal/V/T正式评估cohort，真人未审，不能放行T10-E。主配对继续运行，next_task=T10-D。

### L246 — 2026-11-17 — T10-D — REVIEW_EXPORT_VALIDATED

- 将 `export_next_goal_review_20261117.py` 扩展为可指定运行、题单和输出路径，以便复核主实验及4题IA格式正常对照。`python -` 在临时目录对已完成的历史301事件调用导出器，核验16个正常request ID、112个方法结果和实际artifact证据，退出0；不对历史数据或运行产生修改。
- `python -` 检查主运行分片为87/188（B0 47、B2 40），工具会话85228通过 `write_stdin` 确认仍运行。主运行完成后执行审计、首轮消融及正常逐题复核，串行运行IA格式正常对照与替代证据实验。next_task=T10-D。

### L247 — 2026-11-17 — T10-D — ABLATION_SYNTHETIC_CHECK

- `python -` 在临时目录构造3条首轮低风险在线事件，验证首轮消融器能分别统计多Mask线索与IA格式线索、并校对完整候选动作：两类各1次变化，完整候选2次，断言通过。此为合成脚本验证，不是实际模型消融结果。后续在主运行审计通过后读取真实事件执行，后续轮仍单独以实际会话记录分析。next_task=T10-D。

### L248 — 2026-11-17 — T10-D — ALTERNATE_EXECUTOR_FIXTURE

- 用 `python -` 读取预登记的两篇真实原文并调用 `execute_action('hide_target_refill', ...)`，以受控回调模拟允许范围内的回填：排除目标后仅保留替代文档，其中包含Vioxx，断言通过。此测试验证执行器在指定输入和回填函数下的动作，不证明真实向量检索命中或生成回答；真实模型实验仍待主运行结束后执行。next_task=T10-D。

### L249 — 2026-11-17 — T10-D — STATUS_ENTRY_SYNCHRONIZED

- 恢复时通过 `write_stdin` 验证会话85228仍存活，`python -` 统计主运行分片101/188（B0/B2各47、V2 7）。修正[项目状态](PROJECT_STATUS_ZH.md)和[实验索引](EXPERIMENT_INDEX_ZH.md)中旧的“待启动/待固定”表述；实际运行结果以manifest及完成后的逐请求审计为准。next_task=T10-D。

### L250 — 2026-11-17 — T10-D — REAL_COMPONENT_ABLATION_FIXED

- 执行 `python reports/defense_v1/T10/build_next_goal_ablation_20261117.py` 退出0，固定[真实模型机制消融题单](../data/defense_datasets/next_goal_ablation_v2_train_20261117_01/manifest.json)：四条历史已知漏检攻击和四条已固定的IA格式正常阅读题，V2、完整候选、仅查询线索、仅IA格式线索各8问，预期32事件。历史失败样本带选择偏差，正常题为agent参考，结果只作开发诊断。
- 两个消融方法当前为预留身份，主运行完成并核验后再实现和测试，避免改变当前运行的源码身份；然后串行执行。此前首轮决策消融仍保留为辅助检查。next_task=T10-D。
- `python -` 核验消融题单全部输入/输出摘要、8个ID一致、4正常题及在线字段白名单，记录[预检与构建脚本SHA](../reports/defense_v1/T10/next_goal_ablation_preflight_20261117.json)，退出0。

### L251 — 2026-11-17 — T10-D — ABLATION_TEST_RED

- 按测试驱动扩展 `tests/test_defense_benchmark.py`，为仅查询线索和仅IA格式两种消融身份分别约定低风险动作、正常IA格式及已有原文历史的行为。执行 `python -m pytest tests/test_defense_benchmark.py -k 'type_policy_uses_online_types and (B_NEXT_CUE_ONLY or B_NEXT_IA_ONLY)' -xq --tb=short`，首次因方法未实现而按预期失败，退出1。测试文件此时包含预期失败用例，不能称当前完整测试通过。
- 主配对使用的生产源码暂不更改；待进程终止并核验原源码身份后实现两个消融身份、重跑测试。next_task=T10-D。

### L252 — 2026-11-17 — T10-D — FOLLOWUP_RUN_ORDER

- 为保持补充运行与主配对使用相同源码身份，主运行完成并审计后先串行执行IA格式正常对照和受控替代证据实验，再实现并测试消融方法，运行其32事件。消融运行单独登记修改后的代码SHA。会话分片最近120/188（B0/B2各47、V2 26）。上次 `apply_patch` 未匹配成功，已按实际台账末尾追加本条。next_task=T10-D。
- 更正本次文档追加造成的 L249 位置，使 L248–L252 按编号与实际时间顺序排列，记录内容不变。

### L253 — 2026-11-17 — T10-D — RISK_SUMMARY_PREPARED

- 新增 `reports/defense_v1/T10/summarize_next_goal_risk_20261117.py`，按实际流量计算Judge触发、低风险线索升级、组合后触发、正常误触发及F1，并保留Query-only和融合覆盖；两种分数的AUROC分别计算，避免混合不同比例的原始分数。来源为小批开发标签及agent判断，风险识别不是MIA防御效果。
- `python -` 基于历史审计构造临时47事件/方法验证分母、混淆矩阵及两个分数来源拆分，退出0；这是合成工具检查，不是新模型结果。真实统计须等主运行完成与审计。next_task=T10-D。

### L254 — 2026-11-17 — T10-D — TEST_STATUS_CLARIFIED

- 更新台账顶部与[项目状态](PROJECT_STATUS_ZH.md)，区分新候选此前83项回归通过与后来新增的消融测试目前预期失败。主配对分片最近134/188，随后 `write_stdin` 会话85228确认进程仍运行。next_task=T10-D。
### L255 — 2026-11-17 — T10-D — BASELINE_NORMAL_PRELIMINARY

- `python -` 读取主运行已完成的B0/B2/V2正常会话分片并按相同回答、动作和参考原文交付分组。`ng_normal_02` 三方法均交付参考原文但答“Veritas is an antivirus vendor”，原文表示Symantec是杀毒软件厂商、Veritas是存储软件公司；这是agent初查的生成错误，不是过滤证据导致。其余逐题及候选输出、最终分母与证据仍待完整审计。
- 三方法均已各完成47个会话事件，新候选开始执行。该初查不代表总体生成质量，也不用于事后更改已冻结题单。next_task=T10-D。

### L256 — 2026-11-17 — T10-D — RISK_OVERRIDE_METRIC_CHECK

- `python -` 在临时测试数据中加入一条Judge低风险但候选线索升级的攻击，核查组合决策的TP加1、FN减1，原始Judge各来源AUROC保持不变，断言通过。该检查验证统计区分Judge分数与规则升级，非真实实验结果。主运行继续。next_task=T10-D。

### L257 — 2026-11-17 — T10-D — NEXT_REPORT_DRAFT

- 新建[中文报告草稿](../reports/defense_v1/T10/NEXT_GOAL_RESULTS_20261117_ZH.md)，写明已冻结的47请求构成、四方法实际触发规则、现有测试状态和结果核查要求；结果表和候选选择保留待审计，不填预期数据。
- `python -` 检查已完成分片为158/188（B0、B2、V2各47，新候选17）；此前工具会话85228仍运行。下一步等待终态、核验输入/输出并运行补充对照。next_task=T10-D。

### L258 — 2026-11-17 — T10-D — PRIMARY_PAIRED_COMPLETE

- L237命令退出0，188/188完成、0失败跳过。执行 `python reports/defense_v1/T10/audit_type_policy_run.py data/defense_v1_runs/next-goal-paired-20261117-01 reports/defense_v1/T10/next_goal_paired_audit_20261117.json`、`python reports/defense_v1/T10/audit_multi_action_permissions_20261117.py data/defense_v1_runs/next-goal-paired-20261117-01 reports/defense_v1/T10/next_goal_paired_permissions_20261117.json`、`python reports/defense_v1/T10/export_next_goal_review_20261117.py` 与 `python reports/defense_v1/T10/ablate_next_goal_first_turn_20261117.py` 均退出0。在线允许集合8事件无越界，正常题导出19个复核单元。
- 开发攻击请求中B0交付目标原文16次、B2/V2各4次、新候选0次；这是原文交付诊断，须结合攻击输出、正常质量及首轮/后续会话解释。首轮决策消融中，直接查询6次、多Mask1次、IA格式1次改变动作，13条正常首轮不变；结果见[消融JSON](../reports/defense_v1/T10/next_goal_first_turn_ablation_20261117.json)。补充的IA格式正常题、真实机制消融及替代证据实验仍未运行。next_task=T10-D。

### L259 — 2026-11-17 — T10-D — IA_STYLE_CONTROL_RUNNING

- 执行 `python -u scripts/run_defense_v1_benchmark.py --experiment-spec data/defense_datasets/next_goal_ia_style_normal_20261117_01/experiment_spec.json --output-root data/defense_v1_runs/next-goal-ia-style-20261117-01`，工具会话24158，预期4题×4方法16事件，模型分片已加载。[manifest](../data/defense_v1_runs/next-goal-ia-style-20261117-01/run_manifest.json)为运行状态依据。主运行已结束；之后串行运行替代证据，再实现消融方法。next_task=T10-D。

### L260 — 2026-11-17 — T10-D — PRIMARY_NORMAL_REVIEW_COMPLETE

- 逐项读取19个正常回答和证据分组后执行 `python reports/defense_v1/T10/review_next_goal_normal_20261117.py`，退出0，保存[agent评审](../reports/defense_v1/T10/next_goal_normal_agent_review_20261117.json)，绑定复核单元与审计摘要。13个可回答请求中B0正确且有证据12/13，B2/V2/候选均9/13；2个证据不足请求各方法合理不答2/2。共同的生成错误为Veritas公司类别，三条历史困难题在B2/V2/候选失去必要证据或被拒答。历史Treo三轮已有上下文交付，逐请求结果不独立。
- 执行 `python reports/defense_v1/T10/summarize_next_goal_20261117.py`、`python reports/defense_v1/T10/summarize_next_goal_risk_20261117.py` 均退出0。主批开发标签上Judge触发攻击20/32，候选含低风险线索升级后31/32，15正常请求3次触发；这是selected开发样本，Judge原始分数与规则后组合决策分别记录。[攻击汇总](../reports/defense_v1/T10/next_goal_paired_summary_20261117.json)和[风险汇总](../reports/defense_v1/T10/next_goal_risk_summary_20261117.json)。IA式正常对照仍在运行，不据此提前宣布候选达标。next_task=T10-D。

### L261 — 2026-11-17 — T10-D — IA_STYLE_CONTROL_COMPLETE

- L259运行退出0，16/16完成、0失败跳过。执行 `python reports/defense_v1/T10/audit_type_policy_run.py data/defense_v1_runs/next-goal-ia-style-20261117-01 reports/defense_v1/T10/next_goal_ia_style_audit_20261117.json`、`python reports/defense_v1/T10/audit_multi_action_permissions_20261117.py data/defense_v1_runs/next-goal-ia-style-20261117-01 reports/defense_v1/T10/next_goal_ia_style_permissions_20261117.json`，及 `python reports/defense_v1/T10/export_next_goal_review_20261117.py --run data/defense_v1_runs/next-goal-ia-style-20261117-01 --cohort data/defense_datasets/next_goal_ia_style_normal_20261117_01 --output reports/defense_v1/T10/next_goal_ia_style_review_units_20261117.json`，均退出0；16个受限事件无越界。
- 逐项审核10个结果组后执行 `python reports/defense_v1/T10/review_next_goal_ia_style_20261117.py`，退出0，保存[agent复核](../reports/defense_v1/T10/next_goal_ia_style_agent_review_20261117.json)。B0有证据正确4/4、B2和V2均2/4、新候选0/4；新候选对4题均无上下文，回答Unknown。相对V2有2题由有证据正确变为失去证据，不满足L204/L234预先记录的选择条件；这些题为agent提出且精选，不能据此估计总体误报率或替代真人gold。

### L262 — 2026-11-17 — T10-D — ALTERNATE_REAL_RUNNING

- 主与IA格式运行完成后执行 `python -u reports/defense_v1/T10/run_next_goal_alternate_20261117.py`，工具会话49065，模型已加载。预期两次受控真实回答，后续核对允许范围、回填证据及答案；不能推断在线定位正确率。next_task=T10-D。

### L263 — 2026-11-17 — T10-D — ALTERNATE_REAL_COMPLETE

- L262命令退出0，2/2完成，动作分别allow和hide_target_refill。[manifest及事件](../data/defense_v1_runs/next-goal-alternate-20261117-01/run_manifest.json)记录模型输入和真实回答。受控实验在两篇模拟允许文档中排除 `00000224` 后，回填仅交付 `00000589`，回答仍为Vioxx；未过滤组亦回答Vioxx。
- `python -` 重算所有输入与事件摘要，核对2/2完成、排除源先被检索、实际交付仅替代源且上下文支持答案，断言通过。此为单例受控动作，排除目标由实验指定；不证明在线定位可用、事件完全相同或正常总体改善。下一步保存主运行源码快照，按L251实现消融方法并运行测试。next_task=T10-D。

### L264 — 2026-11-17 — T10-D — ABLATION_IMPLEMENTED

- `python -` 将主运行的 `src/miaguard/defense_benchmark_live.py` 保存为[源码快照](../reports/defense_v1/T10/next_goal_primary_defense_benchmark_live_snapshot.py)，核对与主运行manifest代码SHA一致（0c9d2287…）。同源码IA正常对照及受控替代实验均已结束后，扩展生产源码接入 `B_NEXT_CUE_ONLY`、`B_NEXT_IA_ONLY`，分别只应用低风险强线索或IA格式分支，其余沿用V2。V2和完整候选行为保留原路径。
- 执行 `python -m pytest tests/test_defense_benchmark.py -k 'type_policy_uses_online_types and (B_NEXT_CUE_ONLY or B_NEXT_IA_ONLY)' -xq --tb=short`，6 passed；执行L236相同8份相关测试，89 passed、3项依赖弃用警告。此为代码测试，真实机制消融待运行。next_task=T10-D。

### L265 — 2026-11-17 — T10-D — REAL_ABLATION_RUNNING

- 执行 `python -u scripts/run_defense_v1_benchmark.py --experiment-spec data/defense_datasets/next_goal_ablation_v2_train_20261117_01/experiment_spec.json --output-root data/defense_v1_runs/next-goal-ablation-20261117-01`，工具会话31805，模型已加载，预期8题×4方法32事件。[manifest](../data/defense_v1_runs/next-goal-ablation-20261117-01/run_manifest.json)记录本轮更新后的源码身份。完成后审计四方法，并对照预固定的高误伤案例及已见漏检，最终选择策略。next_task=T10-D。

### L266 — 2026-11-17 — T10-D — CANDIDATE_SELECTION_AUDITED

- 执行 `python reports/defense_v1/T10/select_next_goal_candidate_20261117.py`，退出0。依据主实验32个攻击同题和主/补充19个正常同题的agent复核，候选相对V2新增目标原文交付0次、减少4次，但有2条正常阅读由V2有证据正确变为候选错误，依L234预设规则判定保留V2；[逐题选择结果](../reports/defense_v1/T10/next_goal_candidate_selection_20261117.json)包含输入摘要及全部变化。仍须审查拒答等可观察输出与更广来源，不以原文交付单项证明隐私效果。
- [报告](../reports/defense_v1/T10/NEXT_GOAL_RESULTS_20261117_ZH.md)已记录主批三表、IA式正常退化、受控替代证据和策略选择。真实消融运行中，后续核验其结果及整体交付。next_task=T10-D。

### L267 — 2026-11-17 — T10-D — ABLATION_FALLBACK_REGRESSION

- 在消融方法测试中补充高风险Direct及Judge失败分支，验证两种消融均保留V2拒答和不可用处理。执行L236的8份相关测试，93 passed、3项依赖弃用警告，退出0。只改变测试文件，运行中使用的生产源码及manifest身份不变。真实消融继续。next_task=T10-D。

### L268 — 2026-11-17 — T10-D — REAL_ABLATION_COMPLETE

- L265命令退出0，32/32完成、0失败跳过。执行 `python reports/defense_v1/T10/audit_type_policy_run.py data/defense_v1_runs/next-goal-ablation-20261117-01 reports/defense_v1/T10/next_goal_ablation_audit_20261117.json`、`python reports/defense_v1/T10/audit_multi_action_permissions_20261117.py data/defense_v1_runs/next-goal-ablation-20261117-01 reports/defense_v1/T10/next_goal_ablation_permissions_20261117.json` 和 `python reports/defense_v1/T10/export_next_goal_review_20261117.py --run data/defense_v1_runs/next-goal-ablation-20261117-01 --cohort data/defense_datasets/next_goal_ablation_v2_train_20261117_01 --output reports/defense_v1/T10/next_goal_ablation_normal_units_20261117.json` 均退出0。受限范围16事件无越界。
- 逐题查看32个实际回答后执行 `python reports/defense_v1/T10/summarize_next_goal_ablation_20261117.py` 退出0，保存[消融汇总](../reports/defense_v1/T10/next_goal_ablation_summary_20261117.json)。V2、完整候选、仅查询线索、仅IA线索依次在4条历史攻击交付目标原文4/0/1/3，4条正常题有证据正确2/0/2/0；Masked5个位置分别恢复5/0/0/5。显示IA格式规则对应两条新增正常受损，仅查询线索仍放行IA。全部仅为已知漏检及精选正常题、单轮、agent判断，不足以推荐消融版本或推断多轮效果。next_task=T10-D。

### L269 · 2026-11-17 · T10-D · NEXT_GOAL_DELIVERY_VERIFIED

- 完成主实施计划「T10-D 下一轮 Goal」五项待办；当前 T10-D 和 T10 整体仍为 IN_PROGRESS，正式防御效果与 T10-E 人工审核尚未完成。
- 回归命令：`D:\ProgramData\Anaconda3\envs\MIAGuard\python.exe -m pytest tests/test_defense_benchmark.py tests/test_defense_action_executor.py tests/test_exposure_store.py tests/test_evidence_locator.py tests/test_query_cue.py tests/test_two_stage_gateway.py tests/test_online_judge_adapter.py tests/test_frozen_risk_scorer.py -q --tb=short`；结果 93 passed，3 条 SWIG 弃用警告。
- 交付核验命令：`D:\ProgramData\Anaconda3\envs\MIAGuard\python.exe reports/defense_v1/T10/verify_next_goal_delivery_20261117.py`；结果 `passed`，见 [核验结果](../reports/defense_v1/T10/next_goal_delivery_verification_20261117.json)。核对三组正式运行身份的代码、模型、数据和索引摘要、运行记录、替代证据试验、三个数据包和三个待人工审核包摘要、选择条件及报告链接。
- 将 L228–L268 按编号恢复顺序，内容不变。下一步 `next_task=T10-D`：先人工裁决 4 条 IA 格式正常题及对照答案，研究如何减少该规则造成的正常损失；补充独立事件来源与真人审核，按协议进行校准和冻结后才能运行正式效果评估。47 条开发审核包和 86 条 D-dev 审核包供分批人工处理，模型预审不计人评。
- 限制：所见数值来自选取的开发集、样本小且部分轮次相关；不能据此声称总体 MIA 防御效果或论文正式指标。


### L270 — 2026-11-17 — T10-D — UTILITY_48_GOAL_STARTED

- 用户启动48道正常RAG查询的B0/V2真实配对与正确性、完整性、忠实度、证据覆盖评测。读取当前状态、数据、版本、实验索引及协议，开始题源与运行入口核验；原题和策略保持可追溯。next_task=T10-D。


### L271 — 2026-11-17 — T10-D — UTILITY_48_SOURCE_INVENTORY

- 执行 `D:\ProgramData\Anaconda3\envs\MIAGuard\python.exe reports/defense_v1/T10/inventory_utility48_20261117.py`，保存 [来源盘点](../reports/defense_v1/T10/utility48_source_inventory_20261117.json)，记录 v2 bank、split、索引摘要。train 60篇，其中30篇在现有索引、30篇均有正常查询；初次词面4词重合0对，放宽至2词得到14个待人工原文核查的候选，不能认为这些是替代证据。
- `nvidia-smi --query-gpu=name,memory.total,memory.used --format=csv,noheader` 显示 RTX A5000 24,564 MiB，已使用3,141 MiB；真实生成服务尚未验证。下一步核查候选原文、既有可复用来源、train 内索引外文档可用性，设计有充分证据的12条试标，记录允许集合及索引身份；不能虚构替代证据凑组。next_task=T10-D。


### L272 — 2026-11-17 — T10-D — UTILITY_48_ANNOTATION_PILOT_DRAFT

- 执行 `python reports/defense_v1/T10/inventory_utility48_alternatives_20261117.py`，现有索引按罕见词筛到69对候选，排除查询split的V/T；[候选表](../reports/defense_v1/T10/utility48_alternative_candidates_20261117.json)保留两篇原文、split身份及摘要。逐阅前15对，多数是仅同词不同事件，找到 Soyuz 替换乘组及 Merck/Vioxx 可支持特定事实的试标线索；辅助来源不在查询split，非 train 问题来源，需明确记录独立性和历史使用。
- 执行 `python reports/defense_v1/T10/build_utility48_pilot_20261117.py` 生成[12题未冻结试标](../reports/defense_v1/T10/utility48_annotation_pilot_20261117.jsonl)，每组3题，逐项验证引文为原文子串，记录模拟允许集合和原文hash。三条替代题集中两个事件、Merck两题共用同一主源，不代表独立样本；部分原始问句为新拟，需逐题语义复核并补齐必要事实、原始输入和题库来源。证据不足仅对明确的允许集合成立。
- 尚无48题冻结、真实新实验或评分结果。下一步对12条逐题审查，扩充具有实际支持的来源和题单，并验证生成链路。next_task=T10-D。


### L273 — 2026-11-17 — T10-D — UTILITY_48_DRAFT_AND_SMOKE_RUNNING

- `python reports/defense_v1/T10/build_utility48_pilot_20261117.py --expanded` 产生[48条未冻结草稿](../reports/defense_v1/T10/utility48_annotation_draft_20261117.jsonl)，四组各12条、19个主来源；每个原文引文核验子串。替代组重用6个左右事件，多题存在来源相关；辅助文档在原索引但不在原查询划分，必须保留身份，不等同独立train来源。逐条语义审核及最终冻结仍待完成。
- `python reports/defense_v1/T10/freeze_utility48_smoke_20261117.py` 固定四组各一条作为工程验证，非主实验题单；接着运行 `python -u scripts/run_defense_v1_benchmark.py --experiment-spec data/defense_datasets/utility48_smoke_20261117_01/experiment_spec.json --output-root data/defense_v1_runs/utility48-smoke-20261117-01`，工具会话77461，预期8条。检查初始检索、动作、实际输入和回答，尚未完成，next_task=T10-D。


### L274 — 2026-11-17 — T10-D — UTILITY_48_SMOKE_COMPLETE

- L273运行完成，8/8、0失败/跳过。`python -` 检查8条 events：均记录初始检索ID、动作、交付证据、模型输入引用和真实回答；四条B0与四条V2均为allow。见 [运行清单](../data/defense_v1_runs/utility48-smoke-20261117-01/run_manifest.json)。这是4条草稿的链路验证，不作为48题最终效果。
- 扩展构建脚本新增 `--full` 接口但尚未调用，48题仍是草稿。需要先按协议写入评分口径并逐题核对证据、答案与来源、按实际支持关系确定分组，然后冻结。next_task=T10-D。


### L275 — 2026-11-17 — T10-D — UTILITY_48_SCORING_DRAFT

- 起草[评分口径](../reports/defense_v1/T10/UTILITY48_SCORING_DRAFT_ZH.md)，明确正确率、逐事实完整性、初次/实际交付证据覆盖及faithfulness分母、empty与unknown处理；主实验前需固定并将摘要纳入manifest。当前草稿中的可回答题每题只有一个必要事实，完整性仅能反映单事实覆盖，须优先增加具有多个有证据事实的合格问题，避免将该值解释为复杂答案完整性。next_task=T10-D。


### L276 — 2026-11-17 — T10-D — UTILITY_48_COHORT_FROZEN

- 逐条读取48个问句和原文引文，加入4个双事实问题，重新执行 `python reports/defense_v1/T10/build_utility48_pilot_20261117.py --expanded` 校验引文。执行 `python reports/defense_v1/T10/freeze_utility48_smoke_20261117.py --full` 冻结[题单](../data/defense_datasets/utility48_v2_train_20261117_01/manifest.json)、问题、指定允许集、必要事实、证据、评分口径及输入输出哈希，预期B0和V2各48次。
- 此为agent起草与审阅、模拟允许集的开发集，4个双事实题，其余可回答题为单事实；48问题来自19篇主来源，替代组多个题共用事件，附加来源为索引中不属于查询split的文档；非真人gold及独立终测。之前4题运行仅为链路验证，主实验应重新跑全96次。next_task=T10-D。


### L277 — 2026-11-17 — T10-D — UTILITY_48_PAIRED_RUNNING

- 执行 `python -u scripts/run_defense_v1_benchmark.py --experiment-spec data/defense_datasets/utility48_v2_train_20261117_01/experiment_spec.json --output-root data/defense_v1_runs/utility48-paired-20261117-01`，工具会话93714，模型已开始加载，预期96次。按实际manifest和分片核验进度，不将进行中记录当结果。next_task=T10-D。


### L278 — 2026-11-17 — T10-D — UTILITY_48_REVIEW_EXPORT_PREPARED

- 主配对会话93714仍活跃。目录检查显示B0有48个session分片，V2已有3个；分片数量不是完成结果，继续等待运行终态。准备 `reports/defense_v1/T10/export_utility48_review_20261117.py`，用于在运行完成后按哈希核验并汇总96次回答、初次检索原文和模型实际上下文，评分仍未进行。next_task=T10-D。


### L279 — 2026-11-17 — T10-D — UTILITY_48_PRELIMINARY_REVIEW

- 运行会话93714仍在执行。通过 `python -` 读取完成的session分片，B0 48/48、V2 16/48，此为中间状态。B0 第13题将Baikonur所属国家答为Russia，但来源写明Kazakhstan；第47题在回答正确的同时补充“later Prime Minister”，该时间关系在交付材料中无支持，须逐事实评估忠实度。尚未计算汇报指标。next_task=T10-D。


### L280 — 2026-11-17 — T10-D — UTILITY_48_B0_AGENT_REVIEW_DRAFT

- 逐条读取48个B0实际回答及证据后执行 `python reports/defense_v1/T10/review_utility48_b0_20261117.py`，保存[暂定B0复核](../reports/defense_v1/T10/utility48_b0_agent_review_20261117.jsonl)，记录每条回答摘要与事实判定。此为agent预审、非人工gold。当前除47题显式拆分两个断言外，大部分整段回答暂作一个断言，尚未满足冻结口径的最小事实陈述拆分要求；不得据此直接汇报faithfulness，须继续细化并核查材料。
- 会话93714仍活跃，V2仍在运行，完整主结果未生成，next_task=T10-D。


### L281 — 2026-11-17 — T10-D — UTILITY_48_B0_CLAIM_REVIEW

- 更新 `python reports/defense_v1/T10/review_utility48_b0_20261117.py`，将复合回答按事实分解并逐条对照实际交付内容，记录40个参考事实和55个回答事实陈述的agent判定，保留回答hash与评审身份；结果是暂定预审，需核验并与V2配对后重算，不当作真人gold。
- 实时检查会话93714：B0分片48，V2分片32且均allow，已完成的V2与B0回答和交付文档均一致；运行仍活跃，结果以终态manifest与全面审计为准。next_task=T10-D。


### L282 — 2026-11-17 — T10-D — UTILITY_48_SCORING_PREPARED

- 已编写 `reports/defense_v1/T10/score_utility48_20261117.py`，从逐题agent复核、初次检索和实际上下文重算各组正确、有据正确、必要事实完整性、faithfulness及覆盖率，明确分子/分母；代码严格要求同题两方法回答和实际上下文相同、动作均allow才可转用B0评审，否则断言停止等待逐题复核。覆盖以已人工语义确认的原文引句命中为代理，有非穷尽替代证据风险。当前未运行该汇总。
- 会话93714仍活跃，V2分片37/48，下一步等待终态、核验manifest与逐题上下文，再评分。next_task=T10-D。


### L283 — 2026-11-17 — T10-D — UTILITY_48_PAIRED_COMPLETE_AND_SCORED

- 会话93714退出0，96/96完成、0失败。执行 `python reports/defense_v1/T10/export_utility48_review_20261117.py` 校验96个模型输入artifact哈希并导出复核单元；执行 `python reports/defense_v1/T10/score_utility48_20261117.py` 将人工智能agent审阅转用到回答和上下文完全一致的配对，产生[逐题分数](../reports/defense_v1/T10/utility48_scores_20261117.jsonl)及[汇总](../reports/defense_v1/T10/utility48_summary_20261117.json)。B0/V2分别正确且有据35/36、必要事实39/40、faithfulness 53/55、证据不足合理不答12/12；初始和实际覆盖均40/40。V2全部allow，分组未实测过滤和回填。
- 执行 `python reports/defense_v1/T10/audit_type_policy_run.py data/defense_v1_runs/utility48-paired-20261117-01 reports/defense_v1/T10/utility48_paired_audit_20261117.json` 和 `python reports/defense_v1/T10/audit_multi_action_permissions_20261117.py data/defense_v1_runs/utility48-paired-20261117-01 reports/defense_v1/T10/utility48_permissions_20261117.json`；96个模拟允许集事件0越界。`python -` 对照运行清单重算数据、模型、阈值、索引和代码全部36项摘要通过。
- 保存[中期中文报告](../reports/defense_v1/T10/UTILITY48_RESULTS_20261117_ZH.md)。局限：19个主来源、重复事件、模拟每题允许范围、4个多事实题、模型标注/评分非真人gold；覆盖按有限支持引句为代理，V2无干预无法推断触发过滤时效用。4条试标曾在冻结前做链路验证，非未见测试。next_task=T10-D。


### L284 — 2026-11-17 — T10-D — UTILITY_48_PROVENANCE_AUDIT

- 执行 `python -` 重算36项运行身份摘要、96对分数唯一性及计数，均通过；记录 [agent评审身份和输出摘要](../reports/defense_v1/T10/utility48_review_manifest_20261117.json)。报告补充说明48条问句均依据train文档由Codex新拟，部分事实和问法复用旧开发经验，但未逐题绑定原query_id。
- 与本Goal“优先从v2现有查询和可追溯开发题筛选，缺项才新增”的数据来源要求相比，当前新拟题未做逐题原query_id匹配或说明缺项依据；因此现有结果作为开发中间报告，不能据此宣称整个Goal验收完成。下一步逐题比对原v2查询和旧题，相应记录可追溯匹配、改写关系与无法匹配的缺口，并判断是否需要固定更新版及新运行；不能事后伪造来源或更改已有冻结运行。next_task=T10-D。


### L285 — 2026-11-17 — T10-D — UTILITY_48_LINEAGE_CANDIDATES

- 执行 `python reports/defense_v1/T10/audit_utility48_query_lineage_20261117.py`，按同源doc与问句相似度检索v2正常查询及旧开发题，[候选表](../reports/defense_v1/T10/utility48_lineage_candidates_20261117.json)包含48题，其中40题有相似候选；相似度不证明真实改写关系或事实等价，须逐条语义审核并标明事后匹配。其余8题需检查题型缺口和可复用候选。next_task=T10-D。


### L286 — 2026-11-17 — T10-D — UTILITY_48_LINEAGE_AGENT_REVIEW

- 逐题阅读同源候选并执行 `python reports/defense_v1/T10/review_utility48_query_lineage_20261117.py`，保存[事后来源相似性复核](../reports/defense_v1/T10/utility48_lineage_review_20261117.json)：8条与旧题语义等价、2条部分事实重合，38条前五个候选未发现等价题。匹配发生在运行后，不能据此声称事前实际复用；前五相似项非穷举，不能证明其他无可复用题。
- 为满足Goal的先复用要求，下一步应遍历同源全部正常问句与既有开发题，审查题目是否可回答、符合组别及答案是否泄露；对可用旧题构造新的来源可追溯题单并重新执行对应配对。现有48题报告作为真实开发结果保留。next_task=T10-D。


### L287 — 2026-11-17 — T10-D — UTILITY_48_DIRECT_REUSE_CANDIDATES

- 查阅train同源v2正常查询后执行 `python reports/defense_v1/T10/review_utility48_bank_candidates_20261117.py`，得到[8条可直接复用的候选](../reports/defense_v1/T10/utility48_direct_reuse_candidates_20261117.jsonl)，保留原query_id、原题、原文支持片段及源文字摘要；验证原query是benign、主来源在train且引文为索引原文子串。候选尚需按四组设计和评分目标审核，非冻结题单。
- 当前48题真实结果继续保留为中间结果，既有题的事后匹配不能改变其实际来源。下一步扩展直接复用候选、形成覆盖四组的48题可追溯版本，并对修改问句重新运行与评分。next_task=T10-D。


### L288 — 2026-11-17 — T10-D — UTILITY_48_REUSE_VERSION_FROZEN

- 执行 `python reports/defense_v1/T10/freeze_utility48_reuse_20261117.py`，保存新版[48题清单](../data/defense_datasets/utility48_reuse_v2_train_20261117_01/manifest.json)：9条v2原题、4条旧开发题、35条依据已有来源新拟，四组各12题，题目与评分口径在运行前哈希冻结。按source query_id或原开发request_id记录13条真实复用，其他明确记录新拟；仍有多个问题共享事件，允许范围为模拟，非人工gold。
- 新版替换13条，旧版96条结果不可直接作为新版结果，接下来对新版48题各运行B0和V2。next_task=T10-D。


### L289 — 2026-11-17 — T10-D — UTILITY_48_REUSE_RUN_STARTED

- 执行 `python -u scripts/run_defense_v1_benchmark.py --experiment-spec data/defense_datasets/utility48_reuse_v2_train_20261117_01/experiment_spec.json --output-root data/defense_v1_runs/utility48-reuse-paired-20261117-01`，会话49821，预期96次，模型开始加载。结果以manifest和分片终态为准。next_task=T10-D。


### L290 — 2026-11-17 — T10-D — UTILITY_48_REUSE_REVIEW_PREPARED

- 为 `export_utility48_review_20261117.py` 增加 `--reuse`，在新版完整终态后可校验96条artifact并导出逐题上下文，未执行。模型会话49821仍运行，目录显示B0已有31个分片，V2尚未开始；这是中间状态，指标待完整验证。next_task=T10-D。


### L291 — 2026-11-17 — T10-D — UTILITY_48_REUSE_B0_REVIEW

- 新版B0 48个会话分片完成。逐项核查13条复用题的真实回答和证据，执行 `python reports/defense_v1/T10/review_utility48_reuse_b0_20261117.py` 生成[agent复核](../reports/defense_v1/T10/utility48_reuse_b0_agent_review_20261117.jsonl)；另外35题仅在回答与实际模型上下文逐字相同后转用旧评审。第25题回答中药品召回导致股价下降的因果陈述记uncertain，不混入faithfulness可判分母。
- 更新 `score_utility48_20261117.py --reuse` 支持新版，并将uncertain从faithfulness已判分母排除且单独计数。会话49821仍在运行，V2已有8个分片，尚未输出新版汇总。next_task=T10-D。


### L292 — 2026-11-17 — T10-D — UTILITY_48_REUSE_SCORING_COVERAGE

- 评分脚本补充faithfulness已判定/全部陈述的覆盖分母，uncertain单列，不挤入已判分母。`python -m py_compile` 对复用冻结、复核导出、B0评审及汇总4个脚本执行成功。新版题单复核确认每组12条，19个主来源，9条v2原题、4条旧开发题、35条新拟；来源相关性与模拟允许范围须随结果报告。会话49821仍运行，next_task=T10-D。


### L293 — 2026-11-17 — T10-D — UTILITY_48_SCORER_SMOKE

- 用 `python -` 将已完成B0记录临时复制为V2模拟输入，在系统临时目录运行评分脚本，核对36道可回答题、faithfulness一个uncertain及已判/全部陈述分母，断言通过；临时模拟仅验证评分器，不是V2真实数据，也没有写入主结果目录。主会话49821仍运行，V2已完成18条分片。next_task=T10-D。


### L294 — 2026-11-17 — T10-D — UTILITY_48_REUSE_COMPLETE

- 会话49821退出0，96/96、零失败跳过。执行 `python reports/defense_v1/T10/export_utility48_review_20261117.py --reuse`、`python reports/defense_v1/T10/score_utility48_20261117.py --reuse`，保存96个[复核单元](../reports/defense_v1/T10/utility48_reuse_review_units_20261117.jsonl)、[逐项评分](../reports/defense_v1/T10/utility48_reuse_scores_20261117.jsonl)及[汇总](../reports/defense_v1/T10/utility48_reuse_summary_20261117.json)。V2全部allow、回答和实际上下文与B0逐题相同，评分仅在这一条件验证后转用B0 agent复核。
- 两组有据正确35/36，必要事实正确39/40，faithfulness已判60/62、未决1条，已判覆盖62/63，材料不足合理不答12/12。执行 `python reports/defense_v1/T10/audit_type_policy_run.py data/defense_v1_runs/utility48-reuse-paired-20261117-01 reports/defense_v1/T10/utility48_reuse_paired_audit_20261117.json` 与 `python reports/defense_v1/T10/audit_multi_action_permissions_20261117.py data/defense_v1_runs/utility48-reuse-paired-20261117-01 reports/defense_v1/T10/utility48_reuse_permissions_20261117.json`，96个模拟允许范围0越界。
- `python -` 重算数据、模型、索引、阈值、生产代码全部身份摘要、运行结果摘要和96个独立评分键，验证完成。结果及案例见[中文报告](../reports/defense_v1/T10/UTILITY48_REUSE_RESULTS_20261117_ZH.md)。19个主来源、重复事件、模拟允许集、agent审核、35题新拟、4道双事实题；整批V2无动作，不能推断触发过滤时效用或正式成员泄露效果。下一步为独立来源/真人审核与受控过滤对照，next_task=T10-D。


### L295 — 2026-11-17 — T10-D — UTILITY_48_DELIVERY_AUDIT

- 保存[试标复核补记](../reports/defense_v1/T10/utility48_pilot_review_20261117.json)，按实际先前行为如实记为事后整理、非独立人审；记录四组各3条、4条运行前试过链路、原文引用与受限证据不足范围。
- `python -` 重算[新版评审manifest](../reports/defense_v1/T10/utility48_reuse_review_manifest_20261117.json)绑定的评分/脚本hash，核对B0/V2 35/36、39/40、60/62、判定覆盖62/63、合理不答12/12与报告一致，通过。主配对96/96及模型、索引、策略与数据哈希见L294。
- 此轮48题开发对照交付完成；V2 48/48 allow，无实测过滤收益，真人gold、严格独立来源、攻击校准和受控过滤对照仍是后续任务。next_task=T10-D。

### L296 — 2026-11-18 — T10-D — ENTRY_DOCUMENTS_SYNCHRONIZED

- 根据用户整理文档后的检查，使用 PowerShell `Get-Content -Encoding UTF8` 读取 `AGENTS.md`、`docs/README.md`、本台账、项目状态、版本总表与 `data/defense_v1_runs/utility48-reuse-paired-20261117-01/metrics.json`。确认48题B0/V2开发配对96/96完成，台账最新下一步仍为T10-D的独立来源、人工审核、攻击校准和受控过滤对照。
- 更新根目录 `AGENTS.md` 和 [README](README.md) 的状态描述与文档总目录入口，保留版本核验、记录要求和正式评估限制。此次仅更新文档，不改变数据、策略或实验结果。next_task=T10-D。

### L297 — 2026-11-18 — T10-D — EXPERIMENT_RESULTS_DOCUMENTED

- 根据用户要求，使用 PowerShell `Get-Content -Encoding UTF8` 和项目解释器读取 48 题[详细报告](../reports/defense_v1/T10/UTILITY48_REUSE_RESULTS_20261117_ZH.md)及[汇总 JSON](../reports/defense_v1/T10/utility48_reuse_summary_20261117.json)，将 B0/V2 指标、分母、开发样本限制和原始记录入口整理至[实验结果汇总](EXPERIMENT_RESULTS_ZH.md)。
- 在 [README](README.md)、[实验索引](EXPERIMENT_INDEX_ZH.md)和[文档总目录](文档总目录_ZH.md)加入汇总入口。此为已有结果的文档整理，未运行新实验；下一步仍为 T10-D 的独立来源、人工审核、攻击校准与受控过滤对照。

### L298 — 2026-11-18 — T10-D — FOUR_TYPE_40_TARGET_GOAL_STARTED

- 按用户确认开始四类各20库内、20库外目标的B0/V2本地固定样本对照。用 `Get-Content` 和 `rg` 核对状态、数据目录、索引、版本、规格、计划及协议；用项目 Python 统计既有数据包请求、标签和会话长度。原索引对应 v2 train 为30库内、30库外，历史已运行的三轮 IA 仅2库内、2库外会话；62条预审叠加层 IA 为单轮草稿，需重新核对，不按三轮合格计数。当前尚未冻结新题单或运行新模型配对。next_task=T10-D。

### L299 — 2026-11-18 — T10-D — FOUR_TYPE_40_TARGET_INPUT_AUDIT

- 执行 `D:\ProgramData\Anaconda3\envs\MIAGuard\python.exe reports/defense_v1/T10/inventory_four_type40_20261118.py`，退出0，保存[来源与版本预检](../reports/defense_v1/T10/four_type40_preflight_20261118.json)。重算选择清单、已用模型/阈值/索引/生产代码、两份派生题单及输入摘要。成员标签与原索引和逐条原文摘要均一致。
- Direct和S²各有30库内、30库外通过既有结构审计的标准变体。Masked既有叠加层各有30个候选来源，其中库内24、库外20无已记录备注。IA每侧均有30来源含至少三条不同原库字符串，但已有叠加层每侧只有5/3来源含至少三条，且仍待审核。三条字符串不等于三个独立证据事实。按独立子批推进成熟类型，同时继续IA原句和原文语义核对。next_task=T10-D。

### L300 — 2026-11-18 — T10-D — FOUR_TYPE_40_TARGET_SINGLE_STRATUM_FROZEN

- 执行 `python reports/defense_v1/T10/freeze_four_type40_single_round_20261118.py`，退出0。冻结[单轮主批](../data/defense_datasets/four_type40_single_v2_train_20261118_01/manifest.json)120个请求及240次计划执行，Direct、S²、Masked每类20库内/20库外，共用40个不同文档；题目逐字继承原库标准版本或既有叠加层记录。剔除了已有质量备注的Masked来源，尚不能据此认定40个独立事件。固定[评分口径](../reports/defense_v1/T10/FOUR_TYPE40_SCORING_ZH.md)。
- 执行 `python -u scripts/run_defense_v1_benchmark.py --experiment-spec data/defense_datasets/four_type40_smoke_20261118_01/experiment_spec.json --output-root data/defense_v1_runs/four-type40-smoke-20261118-01`，工具会话87362，已加载模型；24次计划执行含单轮各类各侧一条与历史三轮IA各侧一组。此为链路核验，和单轮主批的结果分开。正式独立实验、人工gold、40个IA会话尚未完成。next_task=T10-D。

### L301 — 2026-11-18 — T10-D — FOUR_TYPE_40_TARGET_IA_QUEUE_PREPARED

- 执行 `python reports/defense_v1/T10/export_four_type40_ia_review_20261118.py`，退出0，保存[IA语义审核队列清单](../reports/defense_v1/T10/four_type40_ia_review_manifest_20261118.json)。60篇原文对应2234条去重候选，保留历史三轮、无已记录质量备注的叠加层与原库候选来源。隔离外部预审未接受的原版本，队列省略成员标签。候选仍待对照原文，不能视作最终题单或人审验收。
- 用 PowerShell `Get-Content` 和 `Get-ChildItem` 检查试跑清单及分片，B0完成8个会话、V2完成3个会话时状态仍为running；未发布指标。next_task=T10-D。

### L302 — 2026-11-18 — T10-D — FOUR_TYPE_40_TARGET_VERIFIERS_PREPARED

- `python -m py_compile` 对来源盘点、题单冻结、IA队列、运行核验和评分五个脚本通过。评分脚本读取实际事件和已冻结参考，保留计划和运行分母、两类目标分布与逐请求变化。从源文档审阅标题并用 `python -` 比较780对三词片段，最高Jaccard 0.0164，无高重合对。此为词面近重复诊断，不证明40个独立真实事件。
- 试跑会话87362持续运行，已持久化B0 12与V2 9个请求。全链路和评分脚本还需用完整试跑产物实测，否则不启动单轮主批。next_task=T10-D。

### L303 — 2026-11-18 — T10-D — FOUR_TYPE_40_TARGET_SINGLE_RUNNING

- 试跑会话87362退出0，24/24，0失败、0跳过。执行 `python reports/defense_v1/T10/verify_four_type40_run_20261118.py data/defense_v1_runs/four-type40-smoke-20261118-01` 与 `python reports/defense_v1/T10/score_four_type40_20261118.py data/defense_v1_runs/four-type40-smoke-20261118-01` 均通过，核验24个生成记录、2个有效V2会话判断和24条可复算记录。见[试跑核验](../reports/defense_v1/T10/four_type40_smoke_20261118_01_verification.json)。试跑单列，仅为链路检查。
- 执行 `python -u scripts/run_defense_v1_benchmark.py --experiment-spec data/defense_datasets/four_type40_single_v2_train_20261118_01/experiment_spec.json --output-root data/defense_v1_runs/four-type40-single-paired-20261118-01`，工具会话54393，模型加载完成，预期240次。进度以[运行清单](../data/defense_v1_runs/four-type40-single-paired-20261118-01/run_manifest.json)和完整会话分片为准。单轮结果与三轮IA题目选择分离。next_task=T10-D。

### L304 — 2026-11-18 — T10-D — FOUR_TYPE_40_TARGET_IA_REVIEW_STARTED

- 完成[第一批 IA 原文语义复核](../reports/defense_v1/T10/four_type40_ia_review_batch1_20261118.json)，对4个文档各核对3个既有固定题。`python -` 校验12个查询ID及原文引文原样存在、参考值和固定输入吻合，确认2个库内与2个库外来源。两组各有一题使用标题文字作为来源，已标注。此为 agent 复核的中间材料，不是最终三轮题单。
- `python -` 检查单轮运行分片，B0已有80条，清单仍running。后续从工具会话54393和运行清单接续，完成IA语义复核、各侧缺口登记与固定题单。next_task=T10-D。


### L305 — 2026-11-18 — T10-D — FOUR_TYPE_40_TARGET_IA_REVIEW_SECOND_BATCH

- 完成[第二批 IA 原文语义复核](../reports/defense_v1/T10/four_type40_ia_review_batch2_20261118.json)。执行 `python -` 核对两批文档去重、39 个固定题 ID、原文引文匹配和原始参考标签。两批共 12 个三轮均为 Yes 的目标（6 库内、6 库外），另有 1 个库内目标的参考组合为 Yes/Yes/No，暂保留。数量尚未包含旧三轮固定题的复用验收，属于 agent 复核中间材料。
- 同一命令读取[单轮主批](../data/defense_v1_runs/four-type40-single-paired-20261118-01/run_manifest.json)及分片。B0 已持久化 120/120，V2 已持久化 17/120，清单为 running。按 V2 前 17 条落盘间隔估算约 17 秒/请求，需在主批完成后复算。尚未发布对照指标。next_task=T10-D。

### L306 — 2026-11-18 — T10-D — FOUR_TYPE_40_TARGET_IA_READINESS_AND_SCORING_CHECK

- 执行 `python reports/defense_v1/T10/audit_freeze_four_type40_ia_20261118.py` 核对 v2 train、索引身份、历史三轮原始顺序和题单引用，保存[IA 题单就绪检查](../reports/defense_v1/T10/four_type40_ia_readiness_20261118.json)。13 个本轮复核来源和 4 个历史来源共确认库内 9、库外 8 个三轮来源，其中 8+8 的参考答案组合可配对。其余 43 篇仍在逐篇核对；未冻结或运行 IA 主批。
- 执行 `python -m py_compile`、`python -` 合成 6 个失败或跳过事件、`python reports/defense_v1/T10/verify_four_type40_run_20261118.py data/defense_v1_runs/four-type40-smoke-20261118-01` 和对应 `score_four_type40_20261118.py`，全部通过。核验器区分归档完成和结果有效，评分保留失败或跳过的计划分母，并单列会话风险融合、建议动作和执行动作。试跑仍为 24/24，24 个生成记录可核查。未修改已登记评分规则或在线配置。
- 通过工具会话 54393 检查单轮主批仍在运行。用 `Get-ChildItem` 核对 B0 120/120 与 V2 25/120 个分片已落盘。主批指标待归档后复算。next_task=T10-D。

### L307 — 2026-11-18 — T10-D — FOUR_TYPE_40_TARGET_REPORT_RECOMPUTATION_READY

- 执行 `python reports/defense_v1/T10/verify_four_type40_run_20261118.py data/defense_v1_runs/four-type40-smoke-20261118-01` 和对应评分脚本，24/24 请求、16 个目标级评分分组均通过。 归档 spec、逐请求 ID、目标评分分组和生成证据一并核对。已保存严格排序与并列分子、两方法共同评分覆盖、配对输出变化和 IA 完整会话配对。
- 执行 `python -m py_compile` 及 `python -X utf8 -`，用试跑实测[中文表格复算入口](../reports/defense_v1/T10/render_four_type40_tables_20261118.py)覆盖四类、分子分母、动作、回答分类和 IA 会话融合。试跑表只用于检查渲染与分母，主批指标尚未发布。
- 两批并行核对剩余 43 篇 IA 来源的既有题目与原文，未增加题目。优先挑选两侧参考组合相同的会话；若组合不等量，按实际数量报告并分组解读。后续验证仍以同题 B0/V2 配对为单位。next_task=T10-D。

### L308 — 2026-11-18 — T10-D — FOUR_TYPE_40_TARGET_IA_SECOND_HALF_REVIEWED

- 收到[候选后半原文复核](../reports/defense_v1/T10/four_type40_ia_review_second_half_20261118.json)，22 篇新增复核，12 篇有三条支持的既有题，10 篇不足。另从先前两批既有题的开场白中核对[可自行得出答案的前缀](../reports/defense_v1/T10/four_type40_ia_premise_audit_20261118.json)并添加离线标识，题目与标签原文未改。
- 执行 `python reports/defense_v1/T10/audit_freeze_four_type40_ia_20261118.py` 得三轮来源库内 9、库外 20，尚待前半 21 篇。此为原文支持数量，仍要并列报告前缀自答和参考类别差异。按相同题目做开发配对；这些来源不能替代独立成员攻击校准。
- `nvidia-smi --query-gpu=name,memory.total,memory.used,utilization.gpu --format=csv,noheader` 显示单轮主批使用 RTX A5000 的 22,570/24,564 MiB。IA 运行将接在单轮结束后，避免第二份模型并发占用同一 GPU。主批和 IA 仍未归档。next_task=T10-D。

### L309 — 2026-11-18 — T10-D — FOUR_TYPE_40_TARGET_IA_FROZEN_AND_QUEUED

- 收到[候选前半复核](../reports/defense_v1/T10/four_type40_ia_review_first_half_20261118.json)，21 篇剩余来源完成审核。通过[补充替代复核](../reports/defense_v1/T10/four_type40_ia_premise_alternative_20261118.json)为一篇选择原题库已有候选，避开一轮由题干直接给出答案。保留其他题干前缀标志；排除未能核对三个有明确参考答案的事实或三轮全部自行给出答案的会话。
- 执行 `python reports/defense_v1/T10/audit_freeze_four_type40_ia_20261118.py --targets-per-side 20`，候选库内 21、库外 20，冻结[IA 题单](../data/defense_datasets/four_type40_ia_v2_train_20261118_01/manifest.json)每侧 20 个目标、120 条固定问题。用 `python -X utf8 -` 核对清单所有输入输出摘要、逐条原问句和参考值、原文证据、每会话三轮及在线字段。清单 SHA256 为 `104fcf3cf603c46c125e617769c109d301d0cddb57ff0d9a649505930ec3b733`。两侧各 16 个会话可匹配同一参考组合；库内 7/60 轮、库外 12/60 轮标记为题干中已经提供对应事实。仅作开发对照，不作正式成员校准。
- 执行 `python -X utf8 -` 对冻结题单做[文档与报道主题重合盘点](../reports/defense_v1/T10/four_type40_source_event_overlap_20261118.json)。三类单轮共用 40 篇，IA 与之重用 27 篇，四类合计 53 篇。1378 个不同文章配对的词面三元组 Jaccard 最大 0.0164，无完全重复；标题和导语初步区分 53 个报道主题，真实独立事件数未评估。
- 已启动 PowerShell 顺序队列，工具会话 51235。用 `Get-CimInstance Win32_Process` 定位单轮 PID 7792，`Wait-Process -Id 7792` 确认其退出后核对单轮运行清单，再执行单轮 `verify_four_type40_run_20261118.py`、`score_four_type40_20261118.py`，然后执行 `python -u scripts/run_defense_v1_benchmark.py --experiment-spec data/defense_datasets/four_type40_ia_v2_train_20261118_01/experiment_spec.json --output-root data/defense_v1_runs/four-type40-ia-paired-20261118-01`。队列已输出等待单轮 PID，IA 尚未开始。已同步版本总表、数据目录、实验索引、项目状态及主计划。next_task=T10-D。

### L310 — 2026-11-18 — T10-D — FOUR_TYPE_40_TARGET_STAGED_REPORT_READY

- 补充[实验结果发布入口](../reports/defense_v1/T10/publish_four_type40_results_20261118.py)。单轮与 IA 归档分别验明运行清单、评分摘要、逐请求评分摘要和各侧 20 个目标。`python -m py_compile` 通过。`python -X utf8 -` 临时发布测试首次因临时目录不在项目内、无法生成相对链接退出，随后使用替代链接保留原文件测试，确认试跑的三类单轮与 IA 可合并到同一张表，重复写入不会增加重复段落，原 48 题结果保留。
- 已启动结果发布会话 34639，轮询可读的已归档评分 JSON。单轮归档后调用 `python -X utf8 reports/defense_v1/T10/publish_four_type40_results_20261118.py --write`；IA 归档后加 `--include-ia` 更新同一段。发布入口独立复核运行摘要再写文档，试跑数字未写入主表。
- 工具会话 51235 仍在等单轮进程。用 `Get-ChildItem` 核对单轮 B0 120/120、V2 67/120 已落盘，清单仍 running。当前两组结果未发布，IA 尚未启动。next_task=T10-D。

### L311 — 2026-11-18 — T10-D — FOUR_TYPE_40_TARGET_SINGLE_PUBLISHED_IA_RUNNING

- 执行 `python -X utf8 -`，复核两份冻结规格的共用模型、索引、阈值、策略和相关清单摘要。八个“类型×成员身份”分组各 20 个目标，两批合计 480 个计划请求，在线请求字段不含成员标签。
- 单轮主批于 20:59:44（UTC+8）结束，耗时 38 分 35 秒。[运行清单](../data/defense_v1_runs/four-type40-single-paired-20261118-01/run_manifest.json)为 completed/valid。队列 51235 执行 `python reports/defense_v1/T10/verify_four_type40_run_20261118.py data/defense_v1_runs/four-type40-single-paired-20261118-01` 和对应评分脚本，验证执行 240/240、0 失败、0 跳过、240 组评分与 240 个生成证据记录，保存[核验](../reports/defense_v1/T10/four_type40_single_paired_20261118_01_verification.json)、[汇总](../reports/defense_v1/T10/four_type40_single_paired_20261118_01_summary.json)与[逐请求评分](../reports/defense_v1/T10/four_type40_single_paired_20261118_01_cases.jsonl)。
- 发布会话 34639 执行 `python -X utf8 reports/defense_v1/T10/publish_four_type40_results_20261118.py --write`，已写入[实验结果汇总](EXPERIMENT_RESULTS_ZH.md)。额外执行同命令把 S² AUROC 显示精度调为两位，数值和评分不变。用 `python -X utf8 -` 从实际交付账本独立复算六个库内原文交付格，核对案例 q001、q007 及已发布的主要比例。已同步项目状态、实验索引和主计划。
- 库内 Direct 的 Yes 20/20→11/20，S² 原文交付 20/20→0/20，描述性 AUROC 387/400→362/400，Masked 原词恢复 93/100→10/100。S² 库内 20/20 执行排除目标并补位，库外 18/20 拒答。各结果为 v2 train 本地开发配对，正式效果与独立攻击阈值尚未评估。
- 队列 51235 已按 L309 的冻结规格于 20:59:48（UTC+8）启动[IA](../data/defense_v1_runs/four-type40-ia-paired-20261118-01/run_manifest.json)。读取清单为 running，首次核对 B0 已落盘 30/40 个三轮会话。发布会话 34639 正等待 IA 归档。next_task=T10-D。

### L312 — 2026-11-18 — T10-D — FOUR_TYPE_40_TARGET_IA_PROGRESS_VERIFIED

- 通过工具会话 51235 轮询到 IA 主批持续运行，发布会话 34639 仍等 IA 汇总。执行 `python -X utf8 -` 读取已落盘完整会话分片，在 21:13（UTC+8）核对 B0 40/40 会话、120/120 轮，V2 11/40 会话、33/120 轮，已归档轮次均为 complete。
- V2 已完成的 11 个会话均在第 3 轮使用了会话融合，前两轮未使用融合。按当前已完成分片的间隔估算 62.75 秒/会话，尚有 29 个会话。该快照仅记录运行和会话判断链路，主批评分待完整归档。next_task=T10-D。


### L313 — 2026-11-18 — T10-D — DIFFICULT_NORMAL_PAIRED_OFFLINE_SCORED

- 运行 `python -X utf8 reports/defense_v1/T10/score_difficult_normal_paired_20261118.py`，校验原事件、评审、索引及 30 份生成输入摘要，复用 L258、L260 正常配对的回答与交付上下文进行事后补评。
- [逐题复算及汇总](../reports/defense_v1/T10/difficult_normal_paired_offline_scores_20261118.json)记录 B0/V2 有据正确 12/13、9/13，必要事实完整性 16/17、9/17，忠实度 30/31、18/19，初次覆盖均 17/17，实际交付覆盖 17/17、10/17，原本证据不足的合理不答均 2/2。覆盖基于已标注证据引文，忠实度只统计输出的事实陈述。模型辅助评分，开发样本部分来源相关。已同步状态和实验索引。next_task=T10-D。

### L313 — 2026-11-18 — T10-D — FOUR_TYPE_40_TARGET_COMPLETE_AND_PUBLISHED

- [IA 主批](../data/defense_v1_runs/four-type40-ia-paired-20261118-01/run_manifest.json)于 21:36:05（UTC+8）结束，耗时 36 分 17 秒。队列 51235 退出 0，执行 `python reports/defense_v1/T10/verify_four_type40_run_20261118.py data/defense_v1_runs/four-type40-ia-paired-20261118-01` 和对应 `score_four_type40_20261118.py`。核验 240/240、0 失败、0 跳过、240 个生成证据记录、80 组会话评分、40 个有效 V2 会话判断。[核验](../reports/defense_v1/T10/four_type40_ia_paired_20261118_01_verification.json)、[汇总](../reports/defense_v1/T10/four_type40_ia_paired_20261118_01_summary.json)、[逐请求评分](../reports/defense_v1/T10/four_type40_ia_paired_20261118_01_cases.jsonl)已归档。
- IA 库内至少一次 Yes 的会话为 18/20→9/20，至少一次原文交付为 20/20→12/20，按轮的原文交付为 59/60→20/60。库外两方法至少一次 Yes 均为 0/20。执行 `python -X utf8 -` 复核逐轮动作与风险来源。V2 前两轮均无融合，但库内 40 轮中已有 26 轮采取无检索材料或拒答。第 3 轮 40/40 使用会话融合，其中库内 6/20 轮仍交付目标原文。
- 发布会话 34639 执行 `python -X utf8 reports/defense_v1/T10/publish_four_type40_results_20261118.py --include-ia --write`，退出 0。[四类合表](EXPERIMENT_RESULTS_ZH.md)包括每类每侧分母、配对变化、S² 分数覆盖及排序分子、IA 逐轮分布、两个可回查案例和独立 48 题效用对照。已同步实验索引、项目状态、版本总表和主计划。数据目录保留两份冻结题单及复用说明。
- 两批主运行合计 480/480，0 失败、0 跳过，自单轮启动到 IA 结束 74 分 55 秒。四类各 20 库内与 20 库外，合计 53 个不同文档。两批是 v2 train 本地开发对照。正式独立效果、真人 gold、攻击校准及触发过滤后的正常效用仍按原计划推进。next_task=T10-D。
- 末次验收执行 `python -X utf8 -`，核对两批共 480 个唯一“方法×请求”键、8 个各 20 目标的分组、原索引成员身份、固定规格摘要、生成证据、40 次有效会话判断，以及结果页复算内容、链接和六项计划复选框。修正了按固定行号查找状态条目的校验，保留同期追加的困难正常题补评，重验通过。

### L314 — 2026-11-20 — REPOSITORY_INITIALIZATION

- 用户指定远程 https://github.com/G-LittleSun/MIAGuard.git。执行 `git rev-parse --show-toplevel` 确认初始目录尚未受 Git 管理，`git ls-remote --symref` 确认远程为空。Git Credential Manager 已有 G-LittleSun 账号。
- 已执行 `git init -b main`、`git remote add origin https://github.com/G-LittleSun/MIAGuard.git`，并为本仓库设置账号名与该账号对应的 GitHub 隐私邮箱。`.gitignore` 覆盖本地权重、原始数据、索引、缓存及日志，显式保留冻结查询库、划分、题单、评分和防御运行归档。`.gitattributes` 保留原字节换行以支持 manifest 摘要核验。
- 使用 `git ls-files --others --exclude-standard -z` 结合 `python -B -X utf8 -` 盘点首次提交候选，约 5,350 个文件、140 MiB，单文件最大约 8 MiB，凭据特征扫描无匹配。新增 Git 操作说明并连接根 README、文档索引和工程目录。首次提交和推送待验证。next_task=T10-D。
- 执行 `git add -A`，5,350 个文件暂存。用 `python -B -X utf8 -` 逐项比较 Git blob 和本地字节，全部一致，冻结选样清单及两批各 240 次实验核验通过。执行 `python -B -m pytest -q -p no:cacheprovider --basetemp D:/Project/MIAGuard/.codex_tmp/git-initialization-20261120/pytest tests/test_cli.py tests/test_defense_benchmark.py tests/test_defense_v1_observe.py tests/test_frozen_risk_scorer.py`，61 passed，3 条底层 SWIG 弃用警告。230 个本地文档链接存在。待创建首次提交和推送。

### L315 — 2026-11-20 — REPOSITORY_INITIAL_PUSH

- 执行 `git commit -q -m "Initialize MIAGuard research framework and experiment archive"`，首次提交为 `9a74ec0`。执行 `git -c credential.interactive=never push --set-upstream origin main` 成功，GitHub 建立 main 分支，本地跟踪 origin/main。
- 执行 `git fsck --full` 通过，3 个已被后续暂存内容替代的未引用 blob 属本地暂存过程。已写入 [Git 版本管理与同步](GIT_WORKFLOW_ZH.md)，记录提交范围及模型、原始数据、索引的本地备份范围，项目状态已同步。后续按 Git 历史记录代码变更，研究任务仍为 T10-D。
