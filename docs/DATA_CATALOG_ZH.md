# MIAGuard 数据与正式产物目录

2026-11-18：[四类对照的单轮题单](../data/defense_datasets/four_type40_single_v2_train_20261118_01/manifest.json)已冻结。Direct、S²、Masked 各 20 库内和 20 库外，三类共享 40 个文档，使用 v2 train 及已有叠加层。[IA 题单](../data/defense_datasets/four_type40_ia_v2_train_20261118_01/manifest.json)已冻结，20 库内及 20 库外，每篇固定三轮，与单轮共享 27 个文档，四类合计 53 个不同文档。IA 保留原题及既有参考答案，离线记录题干前缀、原文证据和参考组合差异，未做人类审核。

2026-11-17：[48题复用新版](../data/defense_datasets/utility48_reuse_v2_train_20261117_01/manifest.json)真实B0/V2配对96/96完成，题单非真人gold；结果见[报告](../reports/defense_v1/T10/UTILITY48_REUSE_RESULTS_20261117_ZH.md)。

2026-11-17：[utility48_reuse_v2_train_20261117_01](../data/defense_datasets/utility48_reuse_v2_train_20261117_01/manifest.json)为48题新版，9条v2原题、4条旧开发原题、35条新拟，模型预审与模拟允许集，主配对运行中。

2026-11-17：[utility48_v2_train_20261117_01](../data/defense_datasets/utility48_v2_train_20261117_01/manifest.json)冻结48题及评分口径，19个主来源、4道双事实题；模拟允许集、agent标注，辅助证据部分来自查询split外的索引文档，非人工gold。

2026-11-17：[真实机制消融题单](../data/defense_datasets/next_goal_ablation_v2_train_20261117_01/manifest.json)固定8题、四方法[32/32完成](../data/defense_v1_runs/next-goal-ablation-20261117-01/run_manifest.json)。四条为历史漏检攻击，四条为agent正常阅读对照，仅开发用途。

2026-11-17：[IA格式正常阅读对照](../data/defense_datasets/next_goal_ia_style_normal_20261117_01/manifest.json)固定4题、两Yes两No，模拟可信允许集合，[四方法16/16完成](../data/defense_v1_runs/next-goal-ia-style-20261117-01/run_manifest.json)。agent参考答案，非正式gold。

2026-11-17：[下一轮开发题单](../data/defense_datasets/next_goal_v2_train_20261117_01/manifest.json)固定47问，[四方法188/188完成](../data/defense_v1_runs/next-goal-paired-20261117-01/run_manifest.json)。v2 train，部分历史来源和正常回归，agent参考标注，正式gold待审核。

2026-11-17：固定[多动作来源扩展](../data/defense_datasets/multi_action_sources_v2_train_20261117_01/manifest.json)，19个攻击请求，四类均含库内/库外，5条Masked遮蔽结构与原文核验通过。[五方法运行95/95完成](../data/defense_v1_runs/multi-action-sources-20261117-01/run_manifest.json)。v2 train，部分历史开发来源，非正式gold及独立终测。

2026-11-17：新增[multi_action_v2_train_20261117_01](../data/defense_datasets/multi_action_v2_train_20261117_01/manifest.json)，复用41条开发请求并新增2条来源范围受限的证据不足任务，43问。engineering_only，[7方法301/301完成](../data/defense_v1_runs/multi-action-candidates-20261117-01/run_manifest.json)，正常题与摘要的[agent复核结果](../reports/defense_v1/T10/MULTI_ACTION_REPORT_20261117_ZH.md)已登记。

2026-11-17：新增 [two_hour_paired_v2_train_20261117_01](../data/defense_datasets/two_hour_paired_v2_train_20261117_01/manifest.json)，绑定v2 train及原索引，复用已见四类攻击、四组三轮IA和14道正常候选，41请求。agent 标注，engineering_only，运行状态见台账 L195。

2026-11-13 40分钟补充题单已冻结：[多轮IA](../data/defense_datasets/multiturn_ia_session_v2_train_20261113_01/manifest.json)18问/6会话（12 IA、6正常）；[同题逐次重置](../data/defense_datasets/multiturn_ia_reset_v2_train_20261113_01/manifest.json)18问/18会话；[三组问法对照](../data/defense_datasets/benign_style_pair_v2_train_20261113_01/manifest.json)6问/6会话。均为v2 train、agent参考标注、engineering_only，正式资格为false。三项运行已于2026-11-16核验完成，详见运行台账；多轮输入的历史含义见[追加勘误](../reports/defense_v1/T10/multiturn_ia_metadata_erratum_20261113.json)，冻结字节未修改。

2026-11-13：新增 [benign_pair_v2_train_20261113_01](../data/defense_datasets/benign_pair_v2_train_20261113_01/manifest.json)，固定 v2 train 困难正常 14 问、10 个目标文档和 10 个会话，含两个不同文档的三轮会话。3 问为预筛拒答且参考来源可检索，agent 参考标注仅供开发诊断。

2026-11-13：新增开发题单 [type_policy_v2_train_20261113_01](../data/defense_datasets/type_policy_v2_train_20261113_01/manifest.json)，绑定原 v2 train 与同一旧索引。复用已有工程试题并补四个正常追问，27 问 / 23 会话，含两组不同来源的三轮正常会话。均为开发题单，正常参考答案为 agent 工程标注。

核对日期：2026-11-09（北京时间）。本页列 Judge v3 正式对照数据及防御阶段候选；实验数值以各自原始结果为准。路径相对项目根目录。T10-C 已选定开发队列，尚未形成新的正式全量数据；原有数据 manifest 未修改。

数据、实验、模型和开发框架的版本角色统一从[当前版本总表](CURRENT_VERSIONS_ZH.md)选择；本页负责具体数据清单，不把最新 v2 复用入口与历史 v1 结果混为同一身份。

当前 T10-D 优先核对最新 `ag_news_queries_v2` / `ag_news_threshold_v2` 的 train 可复用范围，再按缺口补充，详见[数据复用规则](DEFENSE_DATA_REUSE_ZH.md)和[选择清单](../reports/defense_v1/T10/legacy_reuse_selection_20261104.json)。v2 绑定旧索引用于开发联调；candidate06 是补缺及新保留数据的父候选，二者成员标签不能跨索引混用。旧 validation/test 已使用，v2 又继承同样的文档分配和攻击记录，不作为新独立终测。现有[保守来源清单](../reports/defense_v1/T10/dev_source_inventory_20261104_01/manifest.json)共 216 篇，仍非完整历史/语义隔离证明。

### 第一阶段数据对防御阶段的复用状态

2026-11-05：[逐条自动结构审计](../reports/defense_v1/T10/v2_train_reuse_audit_20261105_01/REUSE_REPORT_ZH.md)覆盖 v2 train 4,579 条，形成处置清单但未生成新查询版本；2,975 条基础内容可保留待适配/语义复核、1,304 正常需补标、300 Masked 需格式/泄漏修订，全部非正式 gold。

[最新版本核验](../reports/defense_v1/T10/query_bank_version_audit_20261104.json)确认 v2 train：60 篇文档、4,579 条 accepted 查询（正常 1,304、Direct/S²/Masked 各 300、IA 2,375）。正常题 payload 有意图/难度信息，但无第二阶段标准答案/证据；目标源 653 条在旧索引、651 条不在，不能直接当可答/不可答标签。v2 manifest 的正常审核仍 pending。此前 [v1 盘点](../reports/defense_v1/T10/legacy_reuse_document_evidence_20261104.json)的 3,575 条保留为历史记录，不是最新版本数量。原v2库未改变；本轮修订请求另存待审叠加层，仍无正式gold；另有固定12题真实工程试跑。

2026-11-05 新增[固定快速试跑材料](../data/defense_datasets/legacy_v2_fast_pilot_20261105_01/manifest.json)：4正常+8攻击、12独立单查询，父库为v2 train；仅这批engineering_replay_eligible=true，原362条overlay仍pending不可正式回放。已完成[24请求B0/B2真实试跑](../reports/defense_v1/T10/fast_live_pilot_20261105_01/FAST_PILOT_REPORT_ZH.md)；agent参考事实不是人工gold，未产生完整新查询库或正式数据版本。

2026-11-09 新增[排名压力测试小批](../data/defense_datasets/legacy_v2_rank_stress_20261109_01/manifest.json)，来源为 v2 train 及其待审 Masked 叠加层。三条库内填空攻击各用一篇不同故事，实际检索排名2/3/4各1。另有三条困难正常题，均有逐字原文依据。六条均为单轮，参考答案为 agent 工程标注。实际结果见[试验报告](../reports/defense_v1/T10/rank_stress_20261109_01/REPORT_ZH.md)。

## 最新查询库与当前复用入口

| 层级 | 身份与位置 | 已核对规模/状态 |
|---|---|---|
| 最新完整非 smoke 查询库 | [v2 manifest](../data/query_banks/ag_news_queries_v2/ag_news/manifest.json)、[queries.jsonl](../data/query_banks/ag_news_queries_v2/ag_news/queries.jsonl)；`bank_id=ag_news_queries_v2`；SHA256=`7d44945635a768ec9e107b516040364b934a6c11e33525654727012f71134972` | 2026-08-31 完成，100 篇、7,632 查询：正常 2,176，Direct/S²/Masked 各 500，IA 3,956。正常审核 pending，不是正式 gold。 |
| 配套划分 | [ag_news_threshold_v2.json](../data/query_bank_splits/ag_news_threshold_v2.json)；`split_id=ag_news_threshold_v2` | 与 v1 的 train/validation/test 文档分配一致，60/20/20；后续复用只取 train。 |
| 与 v1 的关系 | [版本核验报告](../reports/defense_v1/T10/query_bank_version_audit_20261104.json) | v2 全部 5,456 条攻击记录和文档表与 v1 完全一致，主要扩充正常查询；不构成新独立保留集。 |

## 已完成 Judge v3 对照所用的上游数据与冻结划分（v1）

| 层级 | 正式位置与身份 | 规模 |
|---|---|---|
| 来源攻击运行 | `data/attack_results/20260717-ag-news-four-medium/ag_news/`；`source_run_id=20260717-ag-news-four-medium` | 四类攻击的上游运行 |
| 离线查询库 | `data/query_banks/ag_news_queries_v1/ag_news/`；`bank_id=ag_news_queries_v1`；查询文件 SHA256=`93b0baf6d1e660cae31dc57cd7cd33c797f2f71b0f0f14f0b59a1d9db3f040e1` | 100 文档、5,956 条 accepted 查询：正常 500，Direct/S²/Masked 各 500，IA 3,956 |
| 冻结划分 | `data/query_bank_splits/ag_news_threshold_v1.json`；`split_id=ag_news_threshold_v1`；文件 SHA256=`c7f42950276f787bbc38862fad219b7c2436c8e562a9447c52388b0b809d8a93` | 按 `doc_id` 分组，train/validation/test 为 60/20/20 文档；各分区成员/非成员文档数量相等 |

查询库的生成模型和 Judge 的评分模型不是同一身份：前者的 manifest 记录 Mistral 生成查询，后者的正式评分清单记录 Qwen2.5-7B-Instruct BF16。不能只凭某个配置文件名推断正式运行模型；以运行目录中的 `run_manifest.json` 为准。

## Judge v3 正式评分记录

| 分区 | Judge 运行目录 | 查询 / 会话 | 每个评分头可用 x1+x2 行数 | `judge_records.jsonl` SHA256 |
|---|---|---:|---:|---|
| train | `data/progressive_judge_v3_binary_logprob_train_qwen2_5_7b_bf16_20260916_retry1/train/` | 3,575 / 734 | 2,107 | `afb19dfce92bc584db11842bd9716fbae341f0b1d0e2287b21b9d344c55ba378` |
| validation | `data/progressive_judge_v3_binary_logprob_validation_qwen2_5_7b_bf16_20260918/validation/` | 1,194 / 248 | 698 | `81dc7406a643a04311489ac1fb4efd60c6dcb0ce4ceaec51a2c4e23bd44f1241` |
| test | `data/progressive_judge_v3_binary_logprob_test_qwen2_5_7b_bf16_20260920/test/` | 1,187 / 244 | 699 | `d920fea4fbd0aa8dc484c7303fbbabf9ed04b78d1c2f18aa5adf169884d34c20` |

一条 Judge 记录同时保存 rubric 和 logprob 的 Query/Session 分数。`x1` 是当前 Query 风险，`x2_observed` 是可用 Session 风险；前两轮因历史不足没有可用 x2，双分数融合不包含它们。训练分析表按两个评分头展开，因此长表 7,150 行并不代表 7,150 条独立查询。详见[数据字段字典](data_dictionary.md)和[v3 实验报告](PROGRESSIVE_JUDGE_V3_BINARY_LOGPROB_EXPERIMENT_ZH.md)。

## 派生数据与冻结结果

| 产物 | 正式位置 |
|---|---|
| train 分布分析与分数表 | `data/judge_score_analysis_v3_binary_logprob_20260918/train/` |
| train 按文档分组 OOF、模型比较和阈值选择 | `data/judge_score_fusion_v3_binary_logprob_20260918/train/` |
| 二分类 logprob 冻结融合模型 | `data/judge_score_frozen_v3_binary_logprob_20260920/logistic_l2.json` |
| rubric 冻结融合模型 | `data/judge_score_frozen_v3_rubric_20261015/logistic_l2.json` |
| 两种方案的 validation/test 指标和最终对比 | 见[实验索引](EXPERIMENT_INDEX_ZH.md) |

## 不能混用的历史目录

- `data/progressive_judge_v3_binary_logprob_train_qwen2_5_7b_bf16_20260916/` 是首次失败运行；正式 train 是带 `_retry1` 的目录。
- `data/progressive_judge_v2_three_class_logprob_train_qwen2_5_7b_bf16_20260929/` 只有部分会话分片，无最终汇总，不属于当前 rubric/logprob 对照。
- `ag_news_queries_v2` 是最新查询库和当前防御数据复用入口；既有 Judge v3 对照和 E00 的 v1 分数/运行仍按 v1 身份解释，不与 v2 混合或自动改名。

新增数据版本时，新建输出目录，记录查询库 ID、划分 ID、模型/Prompt 身份、运行清单和摘要哈希；在本页标明是否为正式产物。不要覆盖已有冻结文件。

## 防御候选数据（2026-10-22；尚非正式效果数据）

`defense_access_v1_candidate06` 位于 [候选目录](../data/defense_datasets/defense_access_v1_candidate06/manifest.json)，状态 `candidate_pending_human_review`、`formal_effect_eligible=false`。原 2,000 篇攻击目标均有历史运行结果，故本候选从同一冻结 AG News 120,000 篇 processed corpus 的未用区域构建；原 `target_member` 中旧索引外的文章作为**新 RAG 索引成员目标**，`source_index>=9000` 的未指定区域作为新非成员目标。这里的成员标签只表示是否纳入**新索引**，不是 teacher 模型训练成员标签。

按 [split.json](../data/defense_datasets/defense_access_v1_candidate06/split.json)，D-dev/A-cal/V/T 各有 `100/500/200/1000` 篇 member 与同数 nonmember，总计 3,600 篇目标；另有 900 篇共享背景成员文章，不作为被攻击目标。四个[分区索引](../data/vector_stores/defense_access_v1_candidate06/D-dev/ag_news/manifest.json)各为 1,000 篇，分别包含本分区的 member 目标和所需共享背景，不包含其他分区目标；A-cal/V/T 各自 manifest 位于对应分区的 `ag_news/`。索引 embedding 为本地 all-MiniLM-L6-v2，384 维 FAISS 内积；来源、构建器和索引哈希见 manifest 与[核验 JSON](../reports/defense_v1/T10/validation.json)。

工程候选还包含 1,750 条七类正常请求（每类 250）和 14,400 条四攻击请求（每类 3,600）；在线 `normal_requests.jsonl` / `attack_requests.jsonl` 与离线 `normal_tasks.jsonl` / `attack_labels.jsonl` 分离。全部查询/答案为自动模板草稿，`review_status=pending`；v06 清除了查询中的编码 HTML，五轮提问也不再完全相同，但仍有相似提问、提取式答案和攻击语义待校验，不能当作正式 gold 或论文效果数据。[重叠审计](../data/defense_datasets/defense_access_v1_candidate06/overlap_audit.json)读取 31 份旧目标文件和 32 份模式文件，候选与历史 ID、规范化全文 SimHash 近重复及整篇 Prompt 包含关系计数为零；片段级/语义级重叠与人工质量仍未证明。`candidate01`（目录名 `defense_access_v1`）及 `candidate02`–`candidate05` 是迭代工程草稿，已由 `candidate06` 取代，不合并分析。

### 2026-10-30 D-dev 修订材料与工程 overlay

[pilot_revision_20261030_01 清单](../reports/defense_v1/T10/pilot_revision_20261030_01/revision_manifest.json)记录原 candidate06 manifest、首轮模型审核 manifest、两组新跨文档起草依据以及 3 份修订 JSONL 的 SHA256。范围仍只是 D-dev 的 70 条正常和 16 条攻击；无新划分、索引或正式实验运行。正常 60 条取首轮模型改写，10 条跨文档重配对；攻击 10 条保留、5 条取首轮改写、1 条 Masked 由 Codex 修正数字缺词。全部 `review_status=pending`、`formal_effect_eligible=false`、`replay_eligible=false`。旧离线证据与两条 Masked 答案尚不匹配，新参考答案仅为模型建议。第二轮审核见[指南](../reports/defense_v1/T10/pilot_revision_20261030_01/REVIEW_GUIDE_ZH.md)；首轮原始输出见[模型审核清单](../reports/defense_v1/T10/external_review/pilot_deepseek_20261029_01/review_manifest.json)。不得与 candidate06 的在线请求/离线 gold 混用。

第二轮模型预审见[审核清单](../reports/defense_v1/T10/external_review/pilot_deepseek_rev2_20261030_01/review_manifest.json)与[我方核验](../reports/defense_v1/T10/review_validation_rev2_20261030.json)：70 正常为 61 accept/9 rewrite，16 攻击为 15 accept/1 rewrite；三条跨文档改写漏列第二篇证据。新建的[D-dev 开发试点 overlay](../data/defense_datasets/defense_access_v1_pilot_overlay_rev2_20261030/manifest.json)只含 70 正常/16 攻击的在线请求及对齐离线答案/标签，补齐三条双篇证据和两条 Masked 缺词；[独立工程核验](../data/defense_datasets/defense_access_v1_pilot_overlay_rev2_20261030/validation.json)通过。它引用 candidate06 的原文与索引，不替代 1,750/14,400 条全量候选，全部 `pending`、`formal_effect_eligible=false`；模型建议不是人工 gold。原 `pilot_revision_20261030_01` 的 `replay_eligible=false` 历史状态保持不变，不应将它和 overlay 文件交叉混用。

### 开发产物使用范围与下一版本规则（含 2026-11-04 补记）

| 产物 | 允许用途 | 不足 |
|---|---|---|
| candidate06 全量及四索引 | 数据身份、隔离基础、候选原文；作为新查询版本的父数据 | 模板问题与参考答案未正式审核 |
| pilot_revision_20261030_01 | 保留第二轮审核输入，追溯当时问题/证据 | 离线答案未在该目录同步，原 replay_eligible=false |
| 两轮 external_review 输出 | 模型预审原始证据 | 不能当真人 gold；第二轮三条证据遗漏须结合修订记录阅读 |
| pilot_overlay_rev2_20261030 | 已同步 70/16 在线请求与离线标签的开发联调输入 | 仍 pending，五轮会话重复未解决；结构通过不保证真实后端/正式评估器已就绪 |
| T10-C 轮数试点 | [D-dev 试点清单](../reports/defense_v1/T10/session_length_pilot_20261031_01/pilot_manifest.json)及[结构核验](../reports/defense_v1/T10/session_length_pilot_20261031_01/validation.json)：同源和扩展来源的开发草稿 | 54 个有内容版本、2 个排除版本已于 11 月 2 日收到独立模型预审；部分争议待裁决，没有最终轮数或人工 gold |
| T10-C 审核后修订试点 | [rev2 清单](../reports/defense_v1/T10/session_length_pilot_rev2_20261102_01/manifest.json)、[验证](../reports/defense_v1/T10/session_length_pilot_rev2_20261102_01/validation.json)、[中间选择报告](../reports/defense_v1/T10/session_length_pilot_rev2_20261102_01/selection_report.json)；引用原 31 篇 D-dev 原文，修订 4 个候选版本并另建请求身份 | 54 个带内容、2 个排除、134 个请求；单模型预审和 Codex 修订，全部 pending，replay_eligible=false、formal_effect_eligible=false；自然度/跨文档/来源依赖尚待裁决。 |
| T10-C 跨文档替换建议 | [独立清单](../reports/defense_v1/T10/crossdoc_replacement_20261102_01/manifest.json)、[结构验证](../reports/defense_v1/T10/crossdoc_replacement_20261102_01/validation.json)；另取两篇 D-dev 索引原文，起草两个候选版本 | 5 个问题仅为开发建议，未加入 rev2 的 54 个候选，尚未独立内容审核或人工 gold，不得回放作正式效果。 |
| T10-C D-dev 选定开发队列 | [清单](../reports/defense_v1/T10/session_length_dev_cohort_20261102_01/manifest.json)、[选择报告](../reports/defense_v1/T10/session_length_dev_cohort_20261102_01/selection_report.json)、[验证](../reports/defense_v1/T10/session_length_dev_cohort_20261102_01/validation.json)：28 个两轮基础会话和 2 个三轮焦点诊断 | 30 会话、62 问、31 篇来源；17 个 D-dev 目标与 14 篇共享背景；全部 pending，无真人 gold。三轮诊断共享一组来源，不能泛化或当两个独立来源。 |
| 新全量候选、正式 gold | 后续计划产物，尚未生成/验收 | 不能将计划中的轮数或数量写入已完成统计 |

下一版本按[主计划 T10-D–E](superpowers/plans/2026-10-22-defense-framework-implementation.md)推进：先核查第一阶段旧 train 的复用覆盖，再结合 D-dev 已选队列补足答案/证据、历史来源审计与共享背景校验，仅对需改写/新增部分生成新查询/会话版本，并关联原文、划分、索引、答案和审核身份。查询变化不自动触发索引重建，但必须记录索引复用的哈希依据。现有 1,750/14,400 只属于 candidate06，不是新版本的合格数量承诺。

T10-C 试点的 D-dev 扩展来源中有共享背景文档；[已知正常题源使用清单](../reports/defense_v1/T10/normal_source_usage_20261102_01/manifest.json)覆盖所列正常题预审/试点的 35 篇（19 篇 D-dev 目标、16 篇共享背景）。共享背景保留在原有多分区检索索引中；已用于 D-dev 出题或审核的文档及同 parent/近重复组不得再作为 A-cal/V/T 正常题源。该清单尚不包含所有历史开发 prompt/攻击来源，T10-D 前必须补齐，不能单凭它宣布终测隔离已完成。

2026-11-04 T10-D 新增[保守开发来源清单](../reports/defense_v1/T10/dev_source_inventory_20261104_01/manifest.json)及[结构核验](../reports/defense_v1/T10/dev_source_inventory_20261104_01/validation.json)：216 篇（200 D-dev 候选目标、16 共享背景），包含先前 38 篇。所有 D-dev 目标因已生成候选而保守列入，不能解释为已逐篇审核；未覆盖全部历史 prompt 或事件语义近重复，不代表数据版本更新或终测隔离完成。共享背景仍可用于原检索索引。

2026-11-04 新增 [D-dev 队列导出](../reports/defense_v1/T10/dev_cohort_export_20261104_01/manifest.json)及[结构核验](../reports/defense_v1/T10/dev_cohort_export_20261104_01/validation.json)，按来源门禁整理原 30 会话 / 62 问，分离在线问题和离线参考并保留身份；非新查询，全部 pending，`replay_eligible=false`，不作为正式数据版本或 human gold。

2026-11-04 [事件关联预审包](../reports/defense_v1/T10/event_pair_review_packet_20261104_01/manifest.json)列出 31 篇 D-dev 试点来源的 465 对完整组合，[审核指南](../reports/defense_v1/T10/event_pair_review_packet_20261104_01/REVIEW_GUIDE_ZH.md)与结构验证当时已备，后续预审结果见下一条；仍不覆盖全历史或 V/T。两次开发对照的[来源核验](../reports/defense_v1/T10/dev_run_source_audit_20261104.json)只验证记录和原文的一致性。

2026-11-04 事件预审已收到：[结构核验](../reports/defense_v1/T10/event_review_validation_20261104.json)、[复核处理](../reports/defense_v1/T10/EVENT_REVIEW_TRIAGE_20261104_ZH.md)和[会话分组诊断](../reports/defense_v1/T10/event_review_cohort_grouping_20261104.json)。仅复核模型标出的四个事件级关联，其余语义未独立复核；31 篇 D-dev 不证明全量或跨分区独立。

2026-11-04 [E00 目标源](../reports/defense_v1/T10/e00_source_audit_20261104.json)及[11 篇实际检索源](../reports/defense_v1/T10/e00_retrieved_source_audit_20261104.json)与 4,500 篇候选全文的 ID、规范化全文和 SimHash ≤3 比较无匹配；只检查此 E00 运行，不证明片段、事件或完整历史独立，没有建立新数据版本。

2026-11-04 [Masked 初始试点](../reports/defense_v1/T10/masked_rule_pilot_20261104_01/manifest.json)4 来源/4 草稿，[显式选择试点](../reports/defense_v1/T10/masked_selected_pilot_20261104_01/manifest.json)4 来源候选词清单/2 条新草稿；均 pending、无真人 gold、不可正式回放。首批旧代码未保存快照，第二批已保存并核验快照。均为小样本工程产物，不替代正式候选。

2026-11-05 [v2 复用针对性预审包](../reports/defense_v1/T10/v2_reuse_review_packet_20261105_01/manifest.json)含206 IA 与60 Masked来源方案（300问），共266审核单元及60原文；无成员标签/效果，创建时待审；现已收到预审，见后续接收条目，仍非正式数据版本。

2026-11-05 [针对性预审接收](../reports/defense_v1/T10/v2_reuse_review_integration_20261105_01/integration_manifest.json)已核验；新增[legacy_v2_reuse_overlay_20261105_01](../data/defense_datasets/legacy_v2_reuse_overlay_20261105_01/manifest.json)和[独立核验](../data/defense_datasets/legacy_v2_reuse_overlay_20261105_01/validation.json)：362新请求、62 IA/300 Masked、144暂缓IA。绑定v2 train及旧原索引，在线/离线信息分开；仍pending、无真人gold、replay_eligible=false，非完整新QueryBank。外部原review与父数据不修改。

2026-11-11：新增工程诊断材料 [forced_normal_diagnostic_20261111_01](../data/defense_datasets/forced_normal_diagnostic_20261111_01/manifest.json)，复用已登记v2 train试跑中的4条正常题、原索引及agent参考；未人工gold、不可正式效果评价。相关[真实模型对照](../reports/defense_v1/T10/forced_normal_diagnostic_20261111_01/REPORT_ZH.md)为强制过滤，不是自然误报。

2026-11-11：新增工程候选 [locator_new_sources_20261111_01](../data/defense_datasets/locator_new_sources_20261111_01/manifest.json)，v2 train、旧索引6篇不同文档、6条单轮攻击，全部rank=1、成员，human_gold_complete=false；事件独立性未证，未纳入正常或非成员。

2026-11-11：[query_cue_pilot_20261111_01](../data/defense_datasets/query_cue_pilot_20261111_01/manifest.json)复用此前6攻击及4正常；所有题的旧结果已见，工程诊断，human_gold_complete=false。

2026-11-11：[cue_utility_nonmember_20261111_01](../data/defense_datasets/cue_utility_nonmember_20261111_01/manifest.json)为4条v2 train库外攻击和4条自行构造的库内正常阅读题，其中2条是定向困难练习；agent证据、非人工gold，文档ID不同不证明事件独立。
