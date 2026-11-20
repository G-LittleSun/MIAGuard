# MIAGuard 代码文件索引

2026-11-20。按当前文件、实际导入、顶层类与函数建立逐文件导航。当前版本和实验身份从版本总表及原始 manifest 核对。[工程目录](PROJECT_STRUCTURE_ZH.md) · [版本总表](CURRENT_VERSIONS_ZH.md)

本次覆盖 84 个源码文件、61 个 Python 命令脚本、4 个 PowerShell 脚本、43 个配置、8 个 Schema、76 个测试文件和 96 个实验专用 Python 脚本。另列根目录文件及查询库说明入口。新文件加入后同步更新本索引。

## 根目录入口

| 文件 | 用途 |
|---|---|
| [README.md](../README.md) | 新成员的项目与文档总入口 |
| [AGENTS.md](../AGENTS.md) | 新会话阅读顺序、版本核对和持续记录要求 |
| [pyproject.toml](../pyproject.toml) | 包版本、依赖、命令注册与测试配置 |
| [environment.yml](../environment.yml) | Conda 环境定义 |
| [requirements.txt](../requirements.txt) | Python 依赖安装入口 |
| [.gitignore](../.gitignore) | Git 跟踪和本地文件的范围 |
| [.gitattributes](../.gitattributes) | 保留原文件换行字节以支持摘要复核 |

## 源码模块

| 文件 | 用途 | 顶层类或函数示例 |
|---|---|---|
| [src/miaguard/__init__.py](../src/miaguard/__init__.py) | miaguard 包入口 |  |
| [src/miaguard/access_policy.py](../src/miaguard/access_policy.py) | 将风险结果映射为访问等级和策略 | LevelMapper |
| [src/miaguard/attack_pattern_library.py](../src/miaguard/attack_pattern_library.py) | 加载和管理带版本的攻击模式库 | AttackPattern, AttackPatternLibrary |
| [src/miaguard/cli.py](../src/miaguard/cli.py) | 主命令行参数、模型检查和实验分派 | _parser, doctor, _run |
| [src/miaguard/config.py](../src/miaguard/config.py) | 攻击运行配置、输入和输出路径 | AttackConfig, _section, load_attack_config |
| [src/miaguard/data.py](../src/miaguard/data.py) | 加载目标样本与历史攻击结果，支持续跑 | load_run_manifest, load_run_documents, load_attack_documents |
| [src/miaguard/defense.py](../src/miaguard/defense.py) | 规则防御与 GuardedRAG 的检索、决策和材料准备 | DefenseConfig, DefenseDecision, PreparedRAGRequest |
| [src/miaguard/defense_benchmark.py](../src/miaguard/defense_benchmark.py) | 绑定身份的会话分片回放、续跑与离线评分 | _sha, _write_json, _write_jsonl |
| [src/miaguard/defense_benchmark_fake.py](../src/miaguard/defense_benchmark_fake.py) | 使用确定性模拟后端验证回放契约 | _Store, _Detector, _Client |
| [src/miaguard/defense_benchmark_live.py](../src/miaguard/defense_benchmark_live.py) | 真实 Judge/RAG 后端、类型动作选择和生成记录 | LiveBackend, make_live_backend_factory |
| [src/miaguard/defense_contracts.py](../src/miaguard/defense_contracts.py) | 在线请求、证据、风险等跨组件契约 | OnlineRequest, RiskEstimate, Evidence |
| [src/miaguard/defense_dataset.py](../src/miaguard/defense_dataset.py) | 防御候选数据构造、划分和校验 | _sha, _normalize, _clean_article |
| [src/miaguard/defense_experiment.py](../src/miaguard/defense_experiment.py) | 早期规则防御对照运行与结果输出 | select_balanced_rows, _threshold, _threshold_source |
| [src/miaguard/defense_metrics.py](../src/miaguard/defense_metrics.py) | 按目标、任务和覆盖率计算防御指标 | _rate, _validate_attack_cohort, attack_auc |
| [src/miaguard/direct_rag_mia.py](../src/miaguard/direct_rag_mia.py) | Direct RAG-MIA 基线回放与回答打分 | direct_attack_query, direct_membership_score, run_direct_rag_mia |
| [src/miaguard/direct_scorer.py](../src/miaguard/direct_scorer.py) | 按可见查询线索与模式计算风险证据 | DirectScorerConfig, load_direct_scorer_config, _BaseDirectDetector |
| [src/miaguard/evidence_access.py](../src/miaguard/evidence_access.py) | 执行拒答、过滤补位、无上下文或材料处理等访问动作 | ActionExecution, parent_doc_id, evidence_from_hit |
| [src/miaguard/evidence_locator.py](../src/miaguard/evidence_locator.py) | 从查询与检索结果定位目标来源 | Localization, _trigrams, locate_evidence |
| [src/miaguard/exposure_store.py](../src/miaguard/exposure_store.py) | 请求、检索、实际交付与回答的暴露账本 | _input_sha256, ExposureEvent, BeginResult |
| [src/miaguard/frozen_risk_scorer.py](../src/miaguard/frozen_risk_scorer.py) | 校验并应用冻结的 v3 逻辑回归融合评分 | FrozenRiskScorer, classify_source, error_action |
| [src/miaguard/hard_query_experiment.py](../src/miaguard/hard_query_experiment.py) | 困难查询的规则防御对照实验 | paraphrase_attack_query, hard_benign_query, _decision_row |
| [src/miaguard/ia_attack.py](../src/miaguard/ia_attack.py) | IA 基线请求、回答解析、评分与续跑 | _string_list, _generate_json_with_retry, _generate_questions |
| [src/miaguard/ia_policy_experiment.py](../src/miaguard/ia_policy_experiment.py) | IA 不同访问动作的早期对照实验 | select_ia_policy, run_ia_policy_experiment |
| [src/miaguard/ia_session_judge_experiment.py](../src/miaguard/ia_session_judge_experiment.py) | 会话 Judge 的 IA 对照实验 | benign_session_queries, evaluate_session_detection, _session_statistics |
| [src/miaguard/judge_evaluation.py](../src/miaguard/judge_evaluation.py) | Judge 记录的识别指标和分组评估 | _binary_values, fixed_fpr_operating_point, _pair_metrics |
| [src/miaguard/judge_score_analysis.py](../src/miaguard/judge_score_analysis.py) | 风险分数统计、相关性和绘图 | _number, _describe, _correlation |
| [src/miaguard/judge_score_dataset.py](../src/miaguard/judge_score_dataset.py) | 从核验记录建立评分分析表 | _score, _status, _validate_records |
| [src/miaguard/judge_score_frozen.py](../src/miaguard/judge_score_frozen.py) | 冻结融合模型、工作点和独立评估 | _rows, freeze_logistic_l2, evaluate_frozen_fusion |
| [src/miaguard/judge_score_fusion.py](../src/miaguard/judge_score_fusion.py) | 评分头逻辑回归融合、OOF 评估与绘图 | _session_available_rows, build_grouped_folds, compute_training_weights |
| [src/miaguard/llm_judge.py](../src/miaguard/llm_judge.py) | 早期 LLM Judge 检测器及配置 | LLMJudgeConfig, load_llm_judge_config, LLMJudgeDefense |
| [src/miaguard/llm_judge_experiment.py](../src/miaguard/llm_judge_experiment.py) | 早期 LLM Judge 运行与分类指标 | select_small_scale_events, _document_texts, evaluate_judge_classification |
| [src/miaguard/masked_mia.py](../src/miaguard/masked_mia.py) | Masked 基线请求、恢复词解析和评分 | _groups, _strings, _fallback_word |
| [src/miaguard/metrics.py](../src/miaguard/metrics.py) | 通用攻击评分、混淆矩阵及文件指标复算 | extract_yes_no_unknown, evaluate_scores, compute_metrics_file |
| [src/miaguard/model_client.py](../src/miaguard/model_client.py) | 生成、向量计算与结构化或 logprob 输出 | _candidate_token_ids, _flat_input_ids, _contextual_candidate_token_ids |
| [src/miaguard/ollama_client.py](../src/miaguard/ollama_client.py) | Ollama 服务调用适配 | OllamaClient |
| [src/miaguard/online_judge_adapter.py](../src/miaguard/online_judge_adapter.py) | 把 Judge trace 转换为保留身份的在线风险 | AdaptedTrace, trace_to_risk, adapt_trace |
| [src/miaguard/progressive_judge.py](../src/miaguard/progressive_judge.py) | 递进 Judge 的提示、执行、解析和 trace | ProgressiveJudgeConfig, ScreeningResult, RouterGateResult |
| [src/miaguard/query_bank/__init__.py](../src/miaguard/query_bank/__init__.py) | 查询库工具的包级导出 |  |
| [src/miaguard/query_bank/benign_expansion.py](../src/miaguard/query_bank/benign_expansion.py) | 扩充正常查询候选 | BenignExpansionConfig, BenignSlot, load_benign_expansion_config |
| [src/miaguard/query_bank/builder.py](../src/miaguard/query_bank/builder.py) | 离线查询库构建和检查点 | _is_safe_yes_anchor, _flip_question_polarity, _ia_answer_counts |
| [src/miaguard/query_bank/formal_threshold_comparison.py](../src/miaguard/query_bank/formal_threshold_comparison.py) | 既有正式划分下的阈值条件对照 | adapt_planned_session, build_condition_configs, _identity_core |
| [src/miaguard/query_bank/incremental_benign_judge.py](../src/miaguard/query_bank/incremental_benign_judge.py) | 选择新增正常会话供增量 Judge 评分 | select_incremental_benign_sessions, select_unscored_sessions |
| [src/miaguard/query_bank/judge_benchmark.py](../src/miaguard/query_bank/judge_benchmark.py) | 按固定会话运行 Judge 并验证记录身份 | JudgeBenchmarkPaths, _json_value, canonical_identity_sha256 |
| [src/miaguard/query_bank/judge_merge.py](../src/miaguard/query_bank/judge_merge.py) | 合并兼容的分区评分记录 | scoring_identity_core, merge_partition_records |
| [src/miaguard/query_bank/judge_score_workflow.py](../src/miaguard/query_bank/judge_score_workflow.py) | 评分表、分析、融合和绘图工作流 | _load_mapping, _portable_figure_manifest, run_train_score_analysis |
| [src/miaguard/query_bank/repair.py](../src/miaguard/query_bank/repair.py) | 补齐 IA 候选类别和断点修复 | _ia_answer_counts, _counts_by_attack, _build_config |
| [src/miaguard/query_bank/sampler.py](../src/miaguard/query_bank/sampler.py) | 按类型和文档条件抽取查询 | _seed, _has_balanced_ia_capacity, _single_attack_row |
| [src/miaguard/query_bank/schema.py](../src/miaguard/query_bank/schema.py) | 查询记录与构建配置的字段契约和身份 | QueryBankBuildConfig, document_sha256, make_query_id |
| [src/miaguard/query_bank/sessions.py](../src/miaguard/query_bank/sessions.py) | 按冻结划分规划 Judge 会话和轮次 | PlannedSession, balanced_session_sizes, _variant_sort_key |
| [src/miaguard/query_bank/storage.py](../src/miaguard/query_bank/storage.py) | 查询库文件读写、路径、摘要和紧凑存储 | QueryBankPaths, QueryBankLock, write_document_shard |
| [src/miaguard/query_bank/threshold_comparison.py](../src/miaguard/query_bank/threshold_comparison.py) | 冻结阈值的条件指标比较 | _mapping, _identity_core, _disabled_metrics |
| [src/miaguard/query_bank/threshold_scoring.py](../src/miaguard/query_bank/threshold_scoring.py) | 按分区运行双阶段风险评分并校验身份 | ThresholdScoringPaths, _json_value, _canonical_sha256 |
| [src/miaguard/query_bank/threshold_split.py](../src/miaguard/query_bank/threshold_split.py) | 构造并冻结查询库文档级划分 | _ordered_doc_ids, _document_labels, build_threshold_split |
| [src/miaguard/query_bank/threshold_workflow.py](../src/miaguard/query_bank/threshold_workflow.py) | 阈值选择、验证和配置导出 | _load_mapping, _canonical_sha256, load_verified_scoring_records |
| [src/miaguard/query_bank/validator.py](../src/miaguard/query_bank/validator.py) | 查询内容、文档来源、数量和摘要校验 | normalize_query, validate_document_records, _validated_ia_answer_counts |
| [src/miaguard/query_cue.py](../src/miaguard/query_cue.py) | 识别可观察的查询线索 | query_cues |
| [src/miaguard/query_only_calibration.py](../src/miaguard/query_only_calibration.py) | train 文档均衡的 Query-only 阈值标定 | _mean, _quantile, _wilson_upper |
| [src/miaguard/risk_aggregator.py](../src/miaguard/risk_aggregator.py) | 聚合查询和会话风险结果 | RiskAggregator |
| [src/miaguard/risk_types.py](../src/miaguard/risk_types.py) | 风险、会话轮次和聚合结果的数据结构 | RiskResult, AggregatedRisk, PolicyDecision |
| [src/miaguard/s2_mia.py](../src/miaguard/s2_mia.py) | S² 续写基线与语义相似度评分 | s2_query_prefix, semantic_similarity_score, run_s2_mia |
| [src/miaguard/session_store.py](../src/miaguard/session_store.py) | 会话轮次保存、读取和更新 | _SessionState, SessionStore |
| [src/miaguard/supervised_threshold.py](../src/miaguard/supervised_threshold.py) | 受监督攻击识别阈值和分组评估 | _validated_records, _safe_ratio, _document_balanced_query_recalls |
| [src/miaguard/threshold_calibration.py](../src/miaguard/threshold_calibration.py) | 基础攻击工作点选择和指标计算 | calibrate_threshold |
| [src/miaguard/two_stage_attack_comparison.py](../src/miaguard/two_stage_attack_comparison.py) | 两阶段网关下的攻击对照 | prepare_frozen_query_selection, _score_rows, expand_ia_rows |
| [src/miaguard/two_stage_direct_experiment.py](../src/miaguard/two_stage_direct_experiment.py) | Direct 两阶段风险识别对照 | binary_detection_metrics, _load_split, _attack_row |
| [src/miaguard/two_stage_gateway.py](../src/miaguard/two_stage_gateway.py) | 查询、会话 Judge、冻结评分和阈值的在线网关 | TwoStageConfig, FrozenObserveConfig, load_defense_v1_observe_config |
| [src/miaguard/two_stage_splits.py](../src/miaguard/two_stage_splits.py) | 冻结两阶段实验的来源划分 | load_split_spec, build_split_manifest, freeze_split |
| [src/miaguard/two_stage_threshold_calibration.py](../src/miaguard/two_stage_threshold_calibration.py) | 两阶段风险分数的阈值标定 | interleave_balanced_rows, select_balanced_detection_threshold, _queries |
| [src/miaguard/vector_store.py](../src/miaguard/vector_store.py) | FAISS 索引、受限检索、来源排除和补位审计 | UnifiedVectorStore, build_vector_store |
| [src/rag_mia_data/__init__.py](../src/rag_mia_data/__init__.py) | 数据基础包入口 |  |
| [src/rag_mia_data/cli.py](../src/rag_mia_data/cli.py) | 数据导入、标准化、校验和运行准备命令 | _parser, _run, _run_dataset_command |
| [src/rag_mia_data/config.py](../src/rag_mia_data/config.py) | 预处理和划分配置 | PipelineConfig, _read_yaml, _resolve |
| [src/rag_mia_data/dataset_catalog.py](../src/rag_mia_data/dataset_catalog.py) | 加载和校验数据集注册表 | CatalogEntry, _read_mapping, _load_schema |
| [src/rag_mia_data/dataset_import.py](../src/rag_mia_data/dataset_import.py) | 从外部来源导入原始数据快照 | _resolve_inside, _files_equal, _copy_exact |
| [src/rag_mia_data/dataset_normalize.py](../src/rag_mia_data/dataset_normalize.py) | 统一不同来源的数据格式和字段 | _teacher_row, _normalize_teacher, _project_t2_row |
| [src/rag_mia_data/dataset_validation.py](../src/rag_mia_data/dataset_validation.py) | 原始和统一格式数据的质量校验 | _resolve_project_path, _resolve_normalized_file, load_string_array |
| [src/rag_mia_data/deduplicate.py](../src/rag_mia_data/deduplicate.py) | MinHash 近重复识别和重复组 | char_ngrams, _jaccard, _UnionFind |
| [src/rag_mia_data/experiment.py](../src/rag_mia_data/experiment.py) | 选择数据集并冻结实验目标样本 | AttackCount, ExperimentConfig, _mapping |
| [src/rag_mia_data/inspect_data.py](../src/rag_mia_data/inspect_data.py) | 数据分布、规模和来源盘点 | _id_key, _value_type, _profile_tsv |
| [src/rag_mia_data/io_utils.py](../src/rag_mia_data/io_utils.py) | 读写、原子写入、时间和摘要工具 | iter_tsv, read_jsonl, _atomic_path |
| [src/rag_mia_data/preprocess.py](../src/rag_mia_data/preprocess.py) | 原始文本预处理和候选池输出 | normalize_text, make_doc_id, _source_sort_key |
| [src/rag_mia_data/query_schema.py](../src/rag_mia_data/query_schema.py) | 加载和校验查询 JSON Schema | default_schema_path, load_query_schema, validate_query_record |
| [src/rag_mia_data/split_membership.py](../src/rag_mia_data/split_membership.py) | 成员分配、主题和重复组约束 | _stable_value, _document_strata, assign_membership |
| [src/rag_mia_data/validate.py](../src/rag_mia_data/validate.py) | 划分结果、来源和完整性检查 | _require_unique_ids, validate_document_sets, _validate_document_fields |

## 命令脚本

名称中的 test、formal、v1 和 v2 保留所属实验的含义。运行前核对目标分区、输入、配置和输出目录。

| 文件 | 用途 |
|---|---|
| [scripts/analyze_judge_scores.py](../scripts/analyze_judge_scores.py) | 生成已有 Judge 分数的分析结果 |
| [scripts/audit_query_bank_threshold_sessions.py](../scripts/audit_query_bank_threshold_sessions.py) | 核对阈值实验会话规划 |
| [scripts/audit_teacher_models.py](../scripts/audit_teacher_models.py) | 盘点教师模型文件与下载完整性 |
| [scripts/build_defense_v1_dataset.py](../scripts/build_defense_v1_dataset.py) | 构造待审防御候选和隔离划分 |
| [scripts/build_defense_v1_index.py](../scripts/build_defense_v1_index.py) | 构建防御候选的独立 FAISS 索引 |
| [scripts/build_t10_review_overlay.py](../scripts/build_t10_review_overlay.py) | 将模型审核转为开发叠加层 |
| [scripts/build_vector_db.py](../scripts/build_vector_db.py) | 调用主命令行构建向量索引 |
| [scripts/calibrate_attack_thresholds.py](../scripts/calibrate_attack_thresholds.py) | 标定基础攻击评分阈值 |
| [scripts/calibrate_query_bank_attack_threshold.py](../scripts/calibrate_query_bank_attack_threshold.py) | 在 train 查询库记录上选择攻击阈值 |
| [scripts/calibrate_query_only_defense.py](../scripts/calibrate_query_only_defense.py) | 在核验 train 分数上标定启动阈值 |
| [scripts/check_defense_g1.py](../scripts/check_defense_g1.py) | 用模拟请求核对 G1 证据链 |
| [scripts/check_evidence_backfill.py](../scripts/check_evidence_backfill.py) | 只读检查冻结索引的补位检索 |
| [scripts/compare_defense_observe_rerun.py](../scripts/compare_defense_observe_rerun.py) | 比较在线 observe 与历史 trace 漂移 |
| [scripts/compare_query_bank_attack_thresholds.py](../scripts/compare_query_bank_attack_thresholds.py) | 对照冻结阈值的测试条件 |
| [scripts/compute_attack_metrics.py](../scripts/compute_attack_metrics.py) | 调用主命令行复算攻击评分文件 |
| [scripts/download_hf_weights_chunked.py](../scripts/download_hf_weights_chunked.py) | 分块下载 Hugging Face 模型文件 |
| [scripts/download_teacher_models.py](../scripts/download_teacher_models.py) | 下载教师模型并记录来源 |
| [scripts/evaluate_defense_v1.py](../scripts/evaluate_defense_v1.py) | 对防御回放输出开发指标 |
| [scripts/evaluate_frozen_test_judge_fusion.py](../scripts/evaluate_frozen_test_judge_fusion.py) | 复算既有 test 的冻结融合识别指标 |
| [scripts/evaluate_query_bank_judge_benchmark.py](../scripts/evaluate_query_bank_judge_benchmark.py) | 核验和评估 Judge 记录 |
| [scripts/export_defense_dev_cohort.py](../scripts/export_defense_dev_cohort.py) | 核对冻结身份并导出开发队列 |
| [scripts/export_defense_v1_review_packet.py](../scripts/export_defense_v1_review_packet.py) | 导出隔离成员标签的 D-dev 审核包 |
| [scripts/freeze_two_stage_split.py](../scripts/freeze_two_stage_split.py) | 固定两阶段来源划分 |
| [scripts/manage_attack_patterns.py](../scripts/manage_attack_patterns.py) | 管理攻击模式库条目和版本 |
| [scripts/merge_v2_train_judge_runs.py](../scripts/merge_v2_train_judge_runs.py) | 合并兼容的 v2 train 增量评分 |
| [scripts/plot_judge_v3_attack_recall.py](../scripts/plot_judge_v3_attack_recall.py) | 绘制发布工作点的各类召回 |
| [scripts/query_bank/build_query_bank.py](../scripts/query_bank/build_query_bank.py) | 构建、恢复或复用查询库 |
| [scripts/query_bank/build_threshold_split.py](../scripts/query_bank/build_threshold_split.py) | 构建和冻结文档级阈值划分 |
| [scripts/query_bank/expand_benign_query_bank.py](../scripts/query_bank/expand_benign_query_bank.py) | 扩充正常查询数据 |
| [scripts/query_bank/inspect_query_bank.py](../scripts/query_bank/inspect_query_bank.py) | 查看查询库统计 |
| [scripts/query_bank/repair_ia_query_bank.py](../scripts/query_bank/repair_ia_query_bank.py) | 补齐 IA 类别与修复检查点 |
| [scripts/query_bank/validate_query_bank.py](../scripts/query_bank/validate_query_bank.py) | 校验查询库内容和摘要 |
| [scripts/recompute_two_stage_scores.py](../scripts/recompute_two_stage_scores.py) | 从原风险记录复算两阶段得分 |
| [scripts/run_defense_experiment.py](../scripts/run_defense_experiment.py) | 调用早期规则防御实验 |
| [scripts/run_defense_observe.py](../scripts/run_defense_observe.py) | 在选定 train 会话上回放 observe |
| [scripts/run_defense_v1_benchmark.py](../scripts/run_defense_v1_benchmark.py) | 当前防御开发回放和续跑入口 |
| [scripts/run_direct_rag_mia.py](../scripts/run_direct_rag_mia.py) | 调用 Direct 基线 |
| [scripts/run_formal_query_bank_threshold_comparison.py](../scripts/run_formal_query_bank_threshold_comparison.py) | 运行既有正式划分的冻结阈值对照 |
| [scripts/run_frozen_test_judge_benchmark.py](../scripts/run_frozen_test_judge_benchmark.py) | 使用冻结配置运行既有 test Judge |
| [scripts/run_hard_query_experiment.py](../scripts/run_hard_query_experiment.py) | 运行困难查询对照 |
| [scripts/run_ia.py](../scripts/run_ia.py) | 调用 IA 基线 |
| [scripts/run_ia_policy_experiment.py](../scripts/run_ia_policy_experiment.py) | 运行 IA 访问动作对照 |
| [scripts/run_ia_session_judge_experiment.py](../scripts/run_ia_session_judge_experiment.py) | 运行 IA 会话 Judge 对照 |
| [scripts/run_incremental_v2_benign_judge.py](../scripts/run_incremental_v2_benign_judge.py) | 运行新增正常会话的增量评分 |
| [scripts/run_llm_judge_experiment.py](../scripts/run_llm_judge_experiment.py) | 运行早期 LLM Judge 对照 |
| [scripts/run_masked_mia.py](../scripts/run_masked_mia.py) | 调用 Masked 基线 |
| [scripts/run_query_bank_judge_benchmark.py](../scripts/run_query_bank_judge_benchmark.py) | 对固定查询会话运行递进 Judge |
| [scripts/run_query_bank_threshold_scoring.py](../scripts/run_query_bank_threshold_scoring.py) | 对固定查询会话计算双阶段风险 |
| [scripts/run_remaining_v2_train_judge.py](../scripts/run_remaining_v2_train_judge.py) | 补跑 train 未完成的 Judge 会话 |
| [scripts/run_s2_mia.py](../scripts/run_s2_mia.py) | 调用 S² 基线 |
| [scripts/run_two_stage_attack_comparison.py](../scripts/run_two_stage_attack_comparison.py) | 运行两阶段攻击对照 |
| [scripts/run_two_stage_direct_experiment.py](../scripts/run_two_stage_direct_experiment.py) | 运行 Direct 两阶段识别对照 |
| [scripts/run_two_stage_threshold_calibration.py](../scripts/run_two_stage_threshold_calibration.py) | 运行两阶段阈值标定 |
| [scripts/train_judge_score_fusion.py](../scripts/train_judge_score_fusion.py) | 在 train 拟合风险融合模型 |
| [scripts/validate_judge_score_fusion.py](../scripts/validate_judge_score_fusion.py) | 验证工作点并冻结融合模型 |
| [scripts/validate_query_bank_attack_threshold.py](../scripts/validate_query_bank_attack_threshold.py) | 核验冻结阈值和导出执行配置 |
| [scripts/verify_defense_v1_dataset.py](../scripts/verify_defense_v1_dataset.py) | 核验候选数据与分区隔离索引 |
| [scripts/verify_int8_model.py](../scripts/verify_int8_model.py) | 检查 INT8 模型配置 |
| [scripts/verify_migration.py](../scripts/verify_migration.py) | 核验迁移后的本地攻击运行链路 |
| [scripts/verify_teacher_model.py](../scripts/verify_teacher_model.py) | 检查教师生成模型和向量模型 |
| [scripts/verify_two_stage_disabled.py](../scripts/verify_two_stage_disabled.py) | 核验关闭网关时的链路一致性 |

### PowerShell 与说明入口

| 文件 | 用途 |
|---|---|
| [scripts/run_pipeline.ps1](../scripts/run_pipeline.ps1) | 串联数据盘点、预处理、划分和校验，脚本使用历史 rag_env 环境 |
| [scripts/run_full_10x10.ps1](../scripts/run_full_10x10.ps1) | 历史 10×10 查询库运行，默认查询库为 v1，使用时核对实验身份 |
| [scripts/prepare_datasets.ps1](../scripts/prepare_datasets.ps1) | 从外部教师项目准备数据，依赖外部来源及历史 rag_env 环境 |
| [scripts/download_and_verify_public_teacher_models.ps1](../scripts/download_and_verify_public_teacher_models.ps1) | 使用 MIAGuard 环境批量下载与核验教师模型 |
| [scripts/query_bank/README.md](../scripts/query_bank/README.md) | 查询库工具的参数与使用方式 |

## 配置与数据契约

| 文件 | 用途 |
|---|---|
| [configs/attacks/ag_news_calibrated.yaml](../configs/attacks/ag_news_calibrated.yaml) | AG News 历史 Mistral 攻击工作点 |
| [configs/attacks/ag_news_calibrated_int8.yaml](../configs/attacks/ag_news_calibrated_int8.yaml) | AG News 历史 INT8 模型变体 |
| [configs/attacks/ag_news_progressive_judge_qwen2_5_7b_bf16.yaml](../configs/attacks/ag_news_progressive_judge_qwen2_5_7b_bf16.yaml) | 当前开发配对绑定的 Qwen BF16 与检索参数 |
| [configs/attacks/ollama_formal.yaml](../configs/attacks/ollama_formal.yaml) | 早期 Ollama 较大规模攻击 |
| [configs/attacks/ollama_smoke.yaml](../configs/attacks/ollama_smoke.yaml) | 早期 Ollama 小规模模型 |
| [configs/attacks/teacher_local_smoke.yaml](../configs/attacks/teacher_local_smoke.yaml) | 本地 Mistral 和向量模型检查示例 |
| [configs/base.yaml](../configs/base.yaml) | 原始 T2Ranking 数据流水线基础参数 |
| [configs/data_splits/ag_news_two_stage_v1.yaml](../configs/data_splits/ag_news_two_stage_v1.yaml) | AG News 历史两阶段划分 |
| [configs/datasets/ag_news.yaml](../configs/datasets/ag_news.yaml) | ag_news 数据集注册、原始来源和标准化路径 |
| [configs/datasets/healthcare_magic.yaml](../configs/datasets/healthcare_magic.yaml) | healthcare_magic 数据集注册、原始来源和标准化路径 |
| [configs/datasets/ms_marco.yaml](../configs/datasets/ms_marco.yaml) | ms_marco 数据集注册、原始来源和标准化路径 |
| [configs/datasets/nq.yaml](../configs/datasets/nq.yaml) | nq 数据集注册、原始来源和标准化路径 |
| [configs/datasets/t2ranking.yaml](../configs/datasets/t2ranking.yaml) | t2ranking 数据集注册、原始来源和标准化路径 |
| [configs/defense/defense_v1_observe.yaml](../configs/defense/defense_v1_observe.yaml) | 当前开发配对绑定的冻结评分与网关 observe |
| [configs/defense/ia_deny.yaml](../configs/defense/ia_deny.yaml) | IA 高风险拒答对照 |
| [configs/defense/ia_no_context.yaml](../configs/defense/ia_no_context.yaml) | IA 无检索上下文对照 |
| [configs/defense/ia_summary.yaml](../configs/defense/ia_summary.yaml) | IA 摘要上下文对照 |
| [configs/defense/llm_judge_mvp.yaml](../configs/defense/llm_judge_mvp.yaml) | 早期单查询 LLM Judge |
| [configs/defense/llm_judge_session_smoke.yaml](../configs/defense/llm_judge_session_smoke.yaml) | 早期会话 Judge 小规模对照 |
| [configs/defense/mvp.yaml](../configs/defense/mvp.yaml) | 早期规则防御参数 |
| [configs/defense/progressive_judge_v2.yaml](../configs/defense/progressive_judge_v2.yaml) | 递进 Judge v2 参数 |
| [configs/defense/progressive_judge_v2_qwen2_5_7b.yaml](../configs/defense/progressive_judge_v2_qwen2_5_7b.yaml) | Qwen 适配的 Judge v2 参数 |
| [configs/defense/progressive_judge_v3_binary_logprob.yaml](../configs/defense/progressive_judge_v3_binary_logprob.yaml) | Judge v3 二分类 logprob 参数 |
| [configs/defense/progressive_judge_v3_binary_logprob_qwen2_5_7b.yaml](../configs/defense/progressive_judge_v3_binary_logprob_qwen2_5_7b.yaml) | 当前开发配对绑定的 Qwen Judge v3 参数 |
| [configs/defense/two_stage_direct_enforce.yaml](../configs/defense/two_stage_direct_enforce.yaml) | 历史 Direct 两阶段执行 |
| [configs/defense/two_stage_direct_enforce_calibrated_010.yaml](../configs/defense/two_stage_direct_enforce_calibrated_010.yaml) | 历史 Direct 标定工作点执行 |
| [configs/defense/two_stage_direct_observe.yaml](../configs/defense/two_stage_direct_observe.yaml) | 历史 Direct 两阶段 observe |
| [configs/defense/two_stage_direct_observe_calibration.yaml](../configs/defense/two_stage_direct_observe_calibration.yaml) | 历史 Direct observe 标定参数 |
| [configs/defense/two_stage_direct_observe_threshold.yaml](../configs/defense/two_stage_direct_observe_threshold.yaml) | 历史 Direct observe 阈值 |
| [configs/defense/two_stage_disabled.yaml](../configs/defense/two_stage_disabled.yaml) | 关闭两阶段网关的对照 |
| [configs/defense/two_stage_observe.yaml](../configs/defense/two_stage_observe.yaml) | 早期两阶段 observe |
| [configs/experiments/baseline_smoke.yaml](../configs/experiments/baseline_smoke.yaml) | baseline_smoke 实验目标数、数据集和划分选择 |
| [configs/experiments/formal.yaml](../configs/experiments/formal.yaml) | formal 实验目标数、数据集和划分选择 |
| [configs/experiments/four_attacks_medium.yaml](../configs/experiments/four_attacks_medium.yaml) | four_attacks_medium 实验目标数、数据集和划分选择 |
| [configs/experiments/pilot.yaml](../configs/experiments/pilot.yaml) | pilot 实验目标数、数据集和划分选择 |
| [configs/experiments/smoke.yaml](../configs/experiments/smoke.yaml) | smoke 实验目标数、数据集和划分选择 |
| [configs/formal.yaml](../configs/formal.yaml) | 原始数据流水线扩展规模 |
| [configs/models/teacher_models.yaml](../configs/models/teacher_models.yaml) | 教师模型来源和本地路径 |
| [configs/pilot.yaml](../configs/pilot.yaml) | 原始数据流水线试点规模 |
| [configs/query_banks/ag_news_smoke.yaml](../configs/query_banks/ag_news_smoke.yaml) | AG News 查询库小规模构建 |
| [configs/query_banks/ag_news_v1.yaml](../configs/query_banks/ag_news_v1.yaml) | AG News v1 查询库构建 |
| [configs/query_banks/ag_news_v2_benign_expansion.yaml](../configs/query_banks/ag_news_v2_benign_expansion.yaml) | AG News v2 正常题扩充 |
| [configs/smoke.yaml](../configs/smoke.yaml) | 原始数据流水线小规模 |
| [schemas/attack_pattern_manifest.schema.json](../schemas/attack_pattern_manifest.schema.json) | 攻击模式库 manifest 字段契约 |
| [schemas/dataset.schema.json](../schemas/dataset.schema.json) | 数据集描述字段契约 |
| [schemas/defense_event.schema.json](../schemas/defense_event.schema.json) | 防御事件字段契约 |
| [schemas/query.schema.json](../schemas/query.schema.json) | 查询记录契约 |
| [schemas/query_bank_threshold_split.schema.json](../schemas/query_bank_threshold_split.schema.json) | 查询库阈值划分契约 |
| [schemas/registry.schema.json](../schemas/registry.schema.json) | 数据集注册表契约 |
| [schemas/two_stage_risk_event.schema.json](../schemas/two_stage_risk_event.schema.json) | 两阶段风险事件契约 |
| [schemas/two_stage_split.schema.json](../schemas/two_stage_split.schema.json) | 两阶段来源划分契约 |

## 自动测试

覆盖模块从实际导入提取。测试项按函数定义计数，实际收集数量可能因参数化增加。

| 文件 | 覆盖的项目模块 | 测试函数数 |
|---|---|---:|
| [tests/conftest.py](../tests/conftest.py) | 共享 pytest fixture，构造隔离的数据、配置和样例 | 0 |
| [tests/test_access_policy.py](../tests/test_access_policy.py) | miaguard.access_policy | 5 |
| [tests/test_analysis_dependencies.py](../tests/test_analysis_dependencies.py) | 通过命令入口或文件契约进行集成验证 | 1 |
| [tests/test_attack_config.py](../tests/test_attack_config.py) | miaguard.config | 5 |
| [tests/test_attack_pattern_library.py](../tests/test_attack_pattern_library.py) | miaguard.attack_pattern_library | 2 |
| [tests/test_attack_resume.py](../tests/test_attack_resume.py) | miaguard.data, rag_mia_data.io_utils | 2 |
| [tests/test_baseline_attacks.py](../tests/test_baseline_attacks.py) | miaguard.direct_rag_mia, miaguard.s2_mia, rag_mia_data.experiment | 4 |
| [tests/test_benign_query_bank_expansion.py](../tests/test_benign_query_bank_expansion.py) | miaguard.query_bank.benign_expansion, miaguard.query_bank.schema, miaguard.query_bank.storage, miaguard.query_bank.threshold_split, miaguard.query_bank.validator, rag_mia_data.io_utils | 6 |
| [tests/test_cli.py](../tests/test_cli.py) | rag_mia_data.cli | 2 |
| [tests/test_config.py](../tests/test_config.py) | rag_mia_data.config | 2 |
| [tests/test_dataset_catalog.py](../tests/test_dataset_catalog.py) | rag_mia_data.dataset_catalog | 19 |
| [tests/test_dataset_import.py](../tests/test_dataset_import.py) | rag_mia_data.dataset_catalog, rag_mia_data.dataset_import | 13 |
| [tests/test_dataset_normalize.py](../tests/test_dataset_normalize.py) | rag_mia_data.dataset_catalog, rag_mia_data.dataset_normalize, rag_mia_data.io_utils | 2 |
| [tests/test_dataset_validation.py](../tests/test_dataset_validation.py) | rag_mia_data.dataset_catalog, rag_mia_data.dataset_validation, rag_mia_data.io_utils | 5 |
| [tests/test_deduplicate.py](../tests/test_deduplicate.py) | rag_mia_data.deduplicate | 2 |
| [tests/test_defense.py](../tests/test_defense.py) | miaguard.defense, miaguard.defense_experiment | 11 |
| [tests/test_defense_action_executor.py](../tests/test_defense_action_executor.py) | miaguard.defense, miaguard.defense_contracts, miaguard.defense_experiment, miaguard.evidence_access | 8 |
| [tests/test_defense_benchmark.py](../tests/test_defense_benchmark.py) | miaguard.defense_benchmark, miaguard.defense_benchmark_live, miaguard.defense_contracts, miaguard.frozen_risk_scorer, miaguard.risk_types, miaguard.two_stage_gateway | 10 |
| [tests/test_defense_dataset.py](../tests/test_defense_dataset.py) | miaguard.defense_dataset | 9 |
| [tests/test_defense_dev_export.py](../tests/test_defense_dev_export.py) | miaguard | 3 |
| [tests/test_defense_masked_draft.py](../tests/test_defense_masked_draft.py) | miaguard | 4 |
| [tests/test_defense_metrics.py](../tests/test_defense_metrics.py) | miaguard.defense_metrics | 6 |
| [tests/test_defense_source_usage.py](../tests/test_defense_source_usage.py) | miaguard | 6 |
| [tests/test_defense_v1_observe.py](../tests/test_defense_v1_observe.py) | miaguard.defense, miaguard.frozen_risk_scorer, miaguard.progressive_judge, miaguard.two_stage_gateway | 5 |
| [tests/test_direct_scorer.py](../tests/test_direct_scorer.py) | miaguard.attack_pattern_library, miaguard.direct_scorer, miaguard.risk_types | 7 |
| [tests/test_evidence_access.py](../tests/test_evidence_access.py) | miaguard.evidence_access, miaguard.vector_store | 5 |
| [tests/test_evidence_locator.py](../tests/test_evidence_locator.py) | miaguard.defense_contracts, miaguard.evidence_locator | 3 |
| [tests/test_experiment.py](../tests/test_experiment.py) | rag_mia_data.dataset_catalog, rag_mia_data.experiment, rag_mia_data.io_utils | 5 |
| [tests/test_exposure_store.py](../tests/test_exposure_store.py) | miaguard.defense, miaguard.defense_contracts, miaguard.exposure_store, miaguard.risk_types, miaguard.two_stage_gateway | 6 |
| [tests/test_frozen_risk_scorer.py](../tests/test_frozen_risk_scorer.py) | miaguard.frozen_risk_scorer, miaguard.judge_score_frozen | 4 |
| [tests/test_hard_query_experiment.py](../tests/test_hard_query_experiment.py) | miaguard.defense, miaguard.hard_query_experiment | 2 |
| [tests/test_ia_policy_experiment.py](../tests/test_ia_policy_experiment.py) | miaguard.ia_policy_experiment | 2 |
| [tests/test_ia_resilience.py](../tests/test_ia_resilience.py) | miaguard.ia_attack | 2 |
| [tests/test_ia_session_judge_experiment.py](../tests/test_ia_session_judge_experiment.py) | miaguard.ia_session_judge_experiment | 3 |
| [tests/test_incremental_benign_judge.py](../tests/test_incremental_benign_judge.py) | miaguard.query_bank.incremental_benign_judge, miaguard.query_bank.sessions | 2 |
| [tests/test_inspect_data.py](../tests/test_inspect_data.py) | rag_mia_data.inspect_data | 1 |
| [tests/test_io_utils.py](../tests/test_io_utils.py) | rag_mia_data.io_utils | 4 |
| [tests/test_judge_evaluation.py](../tests/test_judge_evaluation.py) | miaguard.judge_evaluation | 6 |
| [tests/test_judge_merge.py](../tests/test_judge_merge.py) | miaguard.query_bank.judge_merge, miaguard.query_bank.sessions | 2 |
| [tests/test_judge_score_analysis.py](../tests/test_judge_score_analysis.py) | miaguard.judge_score_analysis | 4 |
| [tests/test_judge_score_dataset.py](../tests/test_judge_score_dataset.py) | miaguard.judge_score_dataset | 5 |
| [tests/test_judge_score_frozen.py](../tests/test_judge_score_frozen.py) | miaguard.judge_score_frozen | 3 |
| [tests/test_judge_score_fusion.py](../tests/test_judge_score_fusion.py) | miaguard.judge_score_fusion | 5 |
| [tests/test_judge_score_workflow.py](../tests/test_judge_score_workflow.py) | miaguard.query_bank.judge_benchmark, miaguard.query_bank.judge_score_workflow, rag_mia_data.io_utils | 4 |
| [tests/test_llm_judge.py](../tests/test_llm_judge.py) | miaguard.attack_pattern_library, miaguard.defense, miaguard.llm_judge, miaguard.llm_judge_experiment | 8 |
| [tests/test_masked_mia_resilience.py](../tests/test_masked_mia_resilience.py) | miaguard.masked_mia | 1 |
| [tests/test_model_client.py](../tests/test_model_client.py) | miaguard.model_client | 10 |
| [tests/test_online_judge_adapter.py](../tests/test_online_judge_adapter.py) | miaguard.defense_contracts, miaguard.online_judge_adapter, miaguard.progressive_judge | 6 |
| [tests/test_preprocess.py](../tests/test_preprocess.py) | rag_mia_data.preprocess | 3 |
| [tests/test_progressive_judge.py](../tests/test_progressive_judge.py) | miaguard.attack_pattern_library, miaguard.progressive_judge, miaguard.risk_types | 44 |
| [tests/test_query_bank.py](../tests/test_query_bank.py) | miaguard.query_bank.sampler, miaguard.query_bank.schema, miaguard.query_bank.storage, miaguard.query_bank.validator, rag_mia_data.io_utils | 13 |
| [tests/test_query_bank_builder.py](../tests/test_query_bank_builder.py) | miaguard.query_bank.builder, miaguard.query_bank.schema | 27 |
| [tests/test_query_bank_formal_threshold_comparison.py](../tests/test_query_bank_formal_threshold_comparison.py) | miaguard.query_bank.formal_threshold_comparison, miaguard.query_bank.sessions, miaguard.two_stage_gateway | 4 |
| [tests/test_query_bank_judge_benchmark.py](../tests/test_query_bank_judge_benchmark.py) | miaguard.progressive_judge, miaguard.query_bank.judge_benchmark, miaguard.query_bank.sessions, rag_mia_data.io_utils | 13 |
| [tests/test_query_bank_repair.py](../tests/test_query_bank_repair.py) | miaguard.query_bank.builder, miaguard.query_bank.repair, miaguard.query_bank.schema, miaguard.query_bank.storage, rag_mia_data.io_utils | 6 |
| [tests/test_query_bank_scripts.py](../tests/test_query_bank_scripts.py) | 通过命令入口或文件契约进行集成验证 | 7 |
| [tests/test_query_bank_sessions.py](../tests/test_query_bank_sessions.py) | miaguard.query_bank.sessions, miaguard.query_bank.storage | 4 |
| [tests/test_query_bank_threshold_comparison.py](../tests/test_query_bank_threshold_comparison.py) | miaguard.query_bank.threshold_comparison, miaguard.supervised_threshold, rag_mia_data.io_utils | 2 |
| [tests/test_query_bank_threshold_scoring.py](../tests/test_query_bank_threshold_scoring.py) | miaguard.defense, miaguard.query_bank.sessions, miaguard.query_bank.threshold_scoring, rag_mia_data.io_utils | 4 |
| [tests/test_query_bank_threshold_split.py](../tests/test_query_bank_threshold_split.py) | miaguard.query_bank.storage, miaguard.query_bank.threshold_split | 5 |
| [tests/test_query_bank_threshold_workflow.py](../tests/test_query_bank_threshold_workflow.py) | miaguard.query_bank.threshold_workflow, miaguard.supervised_threshold, rag_mia_data.io_utils | 5 |
| [tests/test_query_bank_two_stage_integration.py](../tests/test_query_bank_two_stage_integration.py) | miaguard.defense_experiment, miaguard.query_bank.schema, miaguard.two_stage_attack_comparison | 3 |
| [tests/test_query_cue.py](../tests/test_query_cue.py) | miaguard.query_cue | 2 |
| [tests/test_query_only_calibration.py](../tests/test_query_only_calibration.py) | miaguard.frozen_risk_scorer, miaguard.query_only_calibration | 5 |
| [tests/test_query_schema.py](../tests/test_query_schema.py) | rag_mia_data.query_schema | 3 |
| [tests/test_risk_aggregator.py](../tests/test_risk_aggregator.py) | miaguard.risk_aggregator, miaguard.risk_types | 4 |
| [tests/test_session_store.py](../tests/test_session_store.py) | miaguard.risk_types, miaguard.session_store | 2 |
| [tests/test_split_membership.py](../tests/test_split_membership.py) | rag_mia_data.split_membership | 2 |
| [tests/test_supervised_threshold.py](../tests/test_supervised_threshold.py) | miaguard.supervised_threshold | 5 |
| [tests/test_threshold_calibration.py](../tests/test_threshold_calibration.py) | miaguard.threshold_calibration | 2 |
| [tests/test_two_stage_attack_comparison.py](../tests/test_two_stage_attack_comparison.py) | miaguard.two_stage_attack_comparison | 2 |
| [tests/test_two_stage_direct_experiment.py](../tests/test_two_stage_direct_experiment.py) | miaguard.two_stage_direct_experiment | 3 |
| [tests/test_two_stage_gateway.py](../tests/test_two_stage_gateway.py) | miaguard.defense, miaguard.risk_types, miaguard.two_stage_gateway | 10 |
| [tests/test_two_stage_splits.py](../tests/test_two_stage_splits.py) | miaguard.two_stage_splits | 3 |
| [tests/test_two_stage_threshold_calibration.py](../tests/test_two_stage_threshold_calibration.py) | miaguard.two_stage_threshold_calibration | 2 |
| [tests/test_validate.py](../tests/test_validate.py) | rag_mia_data.validate | 2 |

## 实验专用脚本

这些脚本随历史实验保存在 reports 下。自述列取自源码 docstring，缺少自述时列出入口符号。当前四类对照复算使用 verify_four_type40_run_20261118.py、score_four_type40_20261118.py 和 publish_four_type40_results_20261118.py。

| 文件 | 源码自述或入口符号 |
|---|---|
| [reports/defense_v1/T10/ablate_next_goal_first_turn_20261117.py](../reports/defense_v1/T10/ablate_next_goal_first_turn_20261117.py) | Decision-only ablation on first turns of the completed paired run. |
| [reports/defense_v1/T10/adjudicate_small_t10c_20261102.py](../reports/defense_v1/T10/adjudicate_small_t10c_20261102.py) | Record a small Codex content review and versioned draft corrections. |
| [reports/defense_v1/T10/adjudicate_t10c_context_focus.py](../reports/defense_v1/T10/adjudicate_t10c_context_focus.py) | Save source-grounded agent judgments for the focus-disambiguation run. |
| [reports/defense_v1/T10/adjudicate_t10c_history_ablation.py](../reports/defense_v1/T10/adjudicate_t10c_history_ablation.py) | Save explicit Codex judgments of the 14 observed D-dev ablation answers. |
| [reports/defense_v1/T10/audit_access_cases_20261109.py](../reports/defense_v1/T10/audit_access_cases_20261109.py) | Audit what the completed live runs actually retrieved, transformed and delivered. |
| [reports/defense_v1/T10/audit_dev_sources_20261104.py](../reports/defense_v1/T10/audit_dev_sources_20261104.py) | Conservative D-dev source inventory; no membership labels or outcomes used. |
| [reports/defense_v1/T10/audit_e00_source_20261104.py](../reports/defense_v1/T10/audit_e00_source_20261104.py) | Check the recorded E00 source against candidate06 historical inputs and corpus. |
| [reports/defense_v1/T10/audit_freeze_four_type40_ia_20261118.py](../reports/defense_v1/T10/audit_freeze_four_type40_ia_20261118.py) | Check reviewed fixed IA fixtures and optionally freeze a balanced cohort. |
| [reports/defense_v1/T10/audit_multi_action_permissions_20261117.py](../reports/defense_v1/T10/audit_multi_action_permissions_20261117.py) | Verify explicit trusted allowlists across retrieval, transforms and raw delivery. |
| [reports/defense_v1/T10/audit_query_cues_20261111.py](../reports/defense_v1/T10/audit_query_cues_20261111.py) | Screen the fixed v2 train bank without invoking a model or reading test. |
| [reports/defense_v1/T10/audit_reusable_normal_scores_20261111.py](../reports/defense_v1/T10/audit_reusable_normal_scores_20261111.py) | 入口符号 sha, rows |
| [reports/defense_v1/T10/audit_review_attack_sources_20261102.py](../reports/defense_v1/T10/audit_review_attack_sources_20261102.py) | Identify previously reviewed attack texts without exporting membership labels. |
| [reports/defense_v1/T10/audit_type_policy_run.py](../reports/defense_v1/T10/audit_type_policy_run.py) | Verify a local defense run and produce paired development diagnostics. |
| [reports/defense_v1/T10/audit_type_policy_traces_20261113.py](../reports/defense_v1/T10/audit_type_policy_traces_20261113.py) | 入口符号 read, rows, check |
| [reports/defense_v1/T10/audit_utility48_query_lineage_20261117.py](../reports/defense_v1/T10/audit_utility48_query_lineage_20261117.py) | Find same-source v2 and prior-development query candidates, without asserting lineage. |
| [reports/defense_v1/T10/audit_v2_train_reuse_20261105.py](../reports/defense_v1/T10/audit_v2_train_reuse_20261105.py) | Offline coverage audit of the selected v2 train, without model/effect calls. |
| [reports/defense_v1/T10/build_benign_style_pair_20261113.py](../reports/defense_v1/T10/build_benign_style_pair_20261113.py) | Freeze six single-turn style pairs from three audited v2 train sources. |
| [reports/defense_v1/T10/build_context_focus_pilot.py](../reports/defense_v1/T10/build_context_focus_pilot.py) | Draft a balanced, source-fixed context-disambiguation pilot for D-dev. |
| [reports/defense_v1/T10/build_cue_utility_20261111.py](../reports/defense_v1/T10/build_cue_utility_20261111.py) | Freeze a small nonmember and normal-query engineering diagnostic. |
| [reports/defense_v1/T10/build_event_review_packet_20261104.py](../reports/defense_v1/T10/build_event_review_packet_20261104.py) | Prepare D-dev-only source-pair review material; no V/T or attack outcomes. |
| [reports/defense_v1/T10/build_fast_live_pilot_20261105.py](../reports/defense_v1/T10/build_fast_live_pilot_20261105.py) | Lock a minimal engineering-only v2 real-answer B0/B2 pilot. |
| [reports/defense_v1/T10/build_locator_sources_20261111.py](../reports/defense_v1/T10/build_locator_sources_20261111.py) | Freeze a small source-distinct train diagnostic before generating answers. |
| [reports/defense_v1/T10/build_masked_rule_pilot_20261104.py](../reports/defense_v1/T10/build_masked_rule_pilot_20261104.py) | Generate an unreviewed D-dev Masked rule pilot from previously reviewed sources. |
| [reports/defense_v1/T10/build_masked_selected_pilot_20261104.py](../reports/defense_v1/T10/build_masked_selected_pilot_20261104.py) | Try two previously suggested words, without claiming semantic validity. |
| [reports/defense_v1/T10/build_multi_action_20261117.py](../reports/defense_v1/T10/build_multi_action_20261117.py) | Freeze the multi-action development cohort and candidate configuration. |
| [reports/defense_v1/T10/build_multi_action_sources_20261117.py](../reports/defense_v1/T10/build_multi_action_sources_20261117.py) | Freeze extra development sources, preserving original documents and online requests. |
| [reports/defense_v1/T10/build_multiturn_ia_supplement_20261113.py](../reports/defense_v1/T10/build_multiturn_ia_supplement_20261113.py) | Freeze a bounded development-only multi-turn IA and reset-history comparison. |
| [reports/defense_v1/T10/build_next_goal_ablation_20261117.py](../reports/defense_v1/T10/build_next_goal_ablation_20261117.py) | Fix a small real-model ablation cohort before candidate results are observed. |
| [reports/defense_v1/T10/build_next_goal_cohort_20261117.py](../reports/defense_v1/T10/build_next_goal_cohort_20261117.py) | Freeze the next development cohort before candidate implementation or outputs. |
| [reports/defense_v1/T10/build_next_goal_human_review_packet_20261117.py](../reports/defense_v1/T10/build_next_goal_human_review_packet_20261117.py) | Prepare a blinded human review packet for this development cohort. |
| [reports/defense_v1/T10/build_next_goal_ia_style_normal_20261117.py](../reports/defense_v1/T10/build_next_goal_ia_style_normal_20261117.py) | Freeze benign yes/no reading controls before candidate answers are observed. |
| [reports/defense_v1/T10/build_rank_stress_20261109.py](../reports/defense_v1/T10/build_rank_stress_20261109.py) | Lock six previously screened v2 train questions for a small live check. |
| [reports/defense_v1/T10/build_t10c_dev_cohort_20261102.py](../reports/defense_v1/T10/build_t10c_dev_cohort_20261102.py) | Assemble a provisional, non-replayable D-dev cohort with explicit lineage. |
| [reports/defense_v1/T10/build_t10c_revision_20261102.py](../reports/defense_v1/T10/build_t10c_revision_20261102.py) | Create a review-pending T10-C revision without modifying review inputs. |
| [reports/defense_v1/T10/build_t10e_ddev_human_review_20261117.py](../reports/defense_v1/T10/build_t10e_ddev_human_review_20261117.py) | Prepare the previously model-reviewed D-dev pilot for human adjudication. |
| [reports/defense_v1/T10/build_two_hour_paired_20261117.py](../reports/defense_v1/T10/build_two_hour_paired_20261117.py) | Freeze a traceable engineering cohort from existing reviewed development fixtures. |
| [reports/defense_v1/T10/build_type_policy_cohort_20261113.py](../reports/defense_v1/T10/build_type_policy_cohort_20261113.py) | Freeze a local, defense-only regression cohort from verified v2 train inputs. |
| [reports/defense_v1/T10/build_utility48_pilot_20261117.py](../reports/defense_v1/T10/build_utility48_pilot_20261117.py) | Construct an evidence-anchored, unfrozen 12-item utility annotation pilot. |
| [reports/defense_v1/T10/build_v2_reuse_review_overlay_20261105.py](../reports/defense_v1/T10/build_v2_reuse_review_overlay_20261105.py) | Export pending attack drafts; no formal gold or executable benchmark is released. |
| [reports/defense_v1/T10/compare_multiturn_ia_20261113.py](../reports/defense_v1/T10/compare_multiturn_ia_20261113.py) | Compare bounded real session and reset-history defense runs without MIA claims. |
| [reports/defense_v1/T10/compare_type_policy_retest.py](../reports/defense_v1/T10/compare_type_policy_retest.py) | Compare both strategy versions on the frozen local engineering cohort. |
| [reports/defense_v1/T10/diagnose_masked_fast_pilot.py](../reports/defense_v1/T10/diagnose_masked_fast_pilot.py) | Produce separate, format-aware engineering diagnostics without changing scores. |
| [reports/defense_v1/T10/export_four_type40_ia_review_20261118.py](../reports/defense_v1/T10/export_four_type40_ia_review_20261118.py) | Export already recorded IA items for source-grounding review without member labels. |
| [reports/defense_v1/T10/export_next_goal_review_20261117.py](../reports/defense_v1/T10/export_next_goal_review_20261117.py) | Export paired normal answers with actual evidence for agent review. |
| [reports/defense_v1/T10/export_source_summary_units_20261117.py](../reports/defense_v1/T10/export_source_summary_units_20261117.py) | Export source-expansion summary contexts for agent inspection. |
| [reports/defense_v1/T10/export_utility48_review_20261117.py](../reports/defense_v1/T10/export_utility48_review_20261117.py) | Export completed benchmark events with source text for evidence-based scoring. |
| [reports/defense_v1/T10/finalize_fast_live_pilot_20261105.py](../reports/defense_v1/T10/finalize_fast_live_pilot_20261105.py) | Validate and describe the fixed tiny live run; never overwrite raw scores. |
| [reports/defense_v1/T10/freeze_benign_pair_20261113.py](../reports/defense_v1/T10/freeze_benign_pair_20261113.py) | Screen benign utility cases and freeze a local paired experiment before answering. |
| [reports/defense_v1/T10/freeze_four_type40_single_round_20261118.py](../reports/defense_v1/T10/freeze_four_type40_single_round_20261118.py) | Freeze the single-turn stratum and a small harness check using existing fixtures. |
| [reports/defense_v1/T10/freeze_utility48_reuse_20261117.py](../reports/defense_v1/T10/freeze_utility48_reuse_20261117.py) | Freeze a new version using evidence-reviewed original questions where possible. |
| [reports/defense_v1/T10/freeze_utility48_smoke_20261117.py](../reports/defense_v1/T10/freeze_utility48_smoke_20261117.py) | Freeze a small engineering smoke test of the utility evidence pipeline. |
| [reports/defense_v1/T10/inventory_four_type40_20261118.py](../reports/defense_v1/T10/inventory_four_type40_20261118.py) | Verify fixed benchmark input identities and inventory eligible source coverage. |
| [reports/defense_v1/T10/inventory_utility48_20261117.py](../reports/defense_v1/T10/inventory_utility48_20261117.py) | Inventory available train sources before selecting utility evaluation items. |
| [reports/defense_v1/T10/inventory_utility48_alternatives_20261117.py](../reports/defense_v1/T10/inventory_utility48_alternatives_20261117.py) | Rank possible supplementary sources for train targets by rare shared terms. |
| [reports/defense_v1/T10/masked_selected_pilot_20261104_01/builder_snapshot.py](../reports/defense_v1/T10/masked_selected_pilot_20261104_01/builder_snapshot.py) | Try two previously suggested words, without claiming semantic validity. |
| [reports/defense_v1/T10/masked_selected_pilot_20261104_01/defense_dataset_snapshot.py](../reports/defense_v1/T10/masked_selected_pilot_20261104_01/defense_dataset_snapshot.py) | Build and validate an isolated candidate corpus for defense experiments. |
| [reports/defense_v1/T10/next_goal_primary_defense_benchmark_live_snapshot.py](../reports/defense_v1/T10/next_goal_primary_defense_benchmark_live_snapshot.py) | Real Judge/RAG backend for the shared defense benchmark service. |
| [reports/defense_v1/T10/publish_four_type40_results_20261118.py](../reports/defense_v1/T10/publish_four_type40_results_20261118.py) | Publish verified single-round results, then extend the same section with IA. |
| [reports/defense_v1/T10/render_four_type40_tables_20261118.py](../reports/defense_v1/T10/render_four_type40_tables_20261118.py) | Render Chinese comparison tables from verified scores, without changing the results. |
| [reports/defense_v1/T10/review_benign_pair_20261113.py](../reports/defense_v1/T10/review_benign_pair_20261113.py) | Summarize evidence and agent judgments for the paired benign utility experiment. |
| [reports/defense_v1/T10/review_multi_action_20261117.py](../reports/defense_v1/T10/review_multi_action_20261117.py) | Export agent review units for normal outputs and summary evidence exposure. |
| [reports/defense_v1/T10/review_multi_action_normal_20261117.py](../reports/defense_v1/T10/review_multi_action_normal_20261117.py) | Persist agent's case-by-case judgments; not human gold. |
| [reports/defense_v1/T10/review_multi_action_summary_20261117.py](../reports/defense_v1/T10/review_multi_action_summary_20261117.py) | Persist manual agent inspection of 21 main-run summary inputs/outputs. |
| [reports/defense_v1/T10/review_next_goal_ia_style_20261117.py](../reports/defense_v1/T10/review_next_goal_ia_style_20261117.py) | Persist agent review of the four source-bound normal reading controls. |
| [reports/defense_v1/T10/review_next_goal_normal_20261117.py](../reports/defense_v1/T10/review_next_goal_normal_20261117.py) | Persist agent review of the actual normal answer/evidence groups. |
| [reports/defense_v1/T10/review_source_summaries_20261117.py](../reports/defense_v1/T10/review_source_summaries_20261117.py) | Record agent inspection of expansion summaries; not formal human review. |
| [reports/defense_v1/T10/review_utility48_b0_20261117.py](../reports/defense_v1/T10/review_utility48_b0_20261117.py) | Record agent review of the 48 B0 outputs read on 2026-11-17. |
| [reports/defense_v1/T10/review_utility48_bank_candidates_20261117.py](../reports/defense_v1/T10/review_utility48_bank_candidates_20261117.py) | Record a small evidence-checked pool of directly reusable v2 queries. |
| [reports/defense_v1/T10/review_utility48_query_lineage_20261117.py](../reports/defense_v1/T10/review_utility48_query_lineage_20261117.py) | Record post-hoc agent assessment of candidate query similarity. |
| [reports/defense_v1/T10/review_utility48_reuse_b0_20261117.py](../reports/defense_v1/T10/review_utility48_reuse_b0_20261117.py) | Review changed questions and transfer unchanged reviews only on exact evidence match. |
| [reports/defense_v1/T10/run_forced_normal_20261111.py](../reports/defense_v1/T10/run_forced_normal_20261111.py) | Paired, forced-action normal utility diagnostic, not a natural-risk evaluation. |
| [reports/defense_v1/T10/run_next_goal_alternate_20261117.py](../reports/defense_v1/T10/run_next_goal_alternate_20261117.py) | Run a controlled real-model refill probe after the primary run finishes. |
| [reports/defense_v1/T10/run_t10c_context_focus.py](../reports/defense_v1/T10/run_t10c_context_focus.py) | Run a controlled focus-disambiguation check; not a defense benchmark. |
| [reports/defense_v1/T10/run_t10c_history_ablation.py](../reports/defense_v1/T10/run_t10c_history_ablation.py) | Run a seven-case, source-fixed D-dev history ablation on a local Ollama model. |
| [reports/defense_v1/T10/score_difficult_normal_paired_20261118.py](../reports/defense_v1/T10/score_difficult_normal_paired_20261118.py) | Retrospective agent scoring of the existing 2026-11-17 normal pairs. |
| [reports/defense_v1/T10/score_four_type40_20261118.py](../reports/defense_v1/T10/score_four_type40_20261118.py) | Recompute descriptive privacy diagnostics from the completed local defense run. |
| [reports/defense_v1/T10/score_utility48_20261117.py](../reports/defense_v1/T10/score_utility48_20261117.py) | Recompute utility metrics from agent-reviewed facts and actual run evidence. |
| [reports/defense_v1/T10/screen_new_benign_20261111.py](../reports/defense_v1/T10/screen_new_benign_20261111.py) | Small deterministic v2 train query-only screen; not an effect experiment. |
| [reports/defense_v1/T10/screen_rank_stress_20261109.py](../reports/defense_v1/T10/screen_rank_stress_20261109.py) | Select engineering candidates by retrieval only, before any new answer generation. |
| [reports/defense_v1/T10/select_next_goal_candidate_20261117.py](../reports/defense_v1/T10/select_next_goal_candidate_20261117.py) | Apply the predeclared development selection rule to audited paired cases. |
| [reports/defense_v1/T10/session_length_pilot_20261031_01/draft_expanded.py](../reports/defense_v1/T10/session_length_pilot_20261031_01/draft_expanded.py) | Draft a separate D-dev document-expansion cohort without attack labels. |
| [reports/defense_v1/T10/session_length_pilot_20261031_01/draft_same_source.py](../reports/defense_v1/T10/session_length_pilot_20261031_01/draft_same_source.py) | Draft D-dev same-source session variants; source data remain read-only. |
| [reports/defense_v1/T10/session_length_pilot_20261031_01/review_baseline.py](../reports/defense_v1/T10/session_length_pilot_20261031_01/review_baseline.py) | Record a development-only recheck of the original five-turn sessions. |
| [reports/defense_v1/T10/session_length_pilot_20261031_01/verify_and_summarize.py](../reports/defense_v1/T10/session_length_pilot_20261031_01/verify_and_summarize.py) | Verify D-dev session draft structure and write an interim selection report. |
| [reports/defense_v1/T10/summarize_multi_action_20261117.py](../reports/defense_v1/T10/summarize_multi_action_20261117.py) | Describe audited development runs; this does not create human gold. |
| [reports/defense_v1/T10/summarize_next_goal_20261117.py](../reports/defense_v1/T10/summarize_next_goal_20261117.py) | Summarize the audited next-goal run using the established diagnostic format. |
| [reports/defense_v1/T10/summarize_next_goal_ablation_20261117.py](../reports/defense_v1/T10/summarize_next_goal_ablation_20261117.py) | Summarize actual single-turn ablation results with paired denominators. |
| [reports/defense_v1/T10/summarize_next_goal_risk_20261117.py](../reports/defense_v1/T10/summarize_next_goal_risk_20261117.py) | Report Judge decisions and candidate cue escalation separately. |
| [reports/defense_v1/T10/summarize_two_hour_20261117.py](../reports/defense_v1/T10/summarize_two_hour_20261117.py) | Summarize completed paired replay using its audited events and prior agent judgments. |
| [reports/defense_v1/T10/v2_reuse_review_integration_20261105_01/verifier_snapshot.py](../reports/defense_v1/T10/v2_reuse_review_integration_20261105_01/verifier_snapshot.py) | Verify external v2 review contract and identities without accepting semantics. |
| [reports/defense_v1/T10/v2_train_reuse_audit_20261105_01/audit_script_snapshot.py](../reports/defense_v1/T10/v2_train_reuse_audit_20261105_01/audit_script_snapshot.py) | Offline coverage audit of the selected v2 train, without model/effect calls. |
| [reports/defense_v1/T10/verify_event_review_20261104.py](../reports/defense_v1/T10/verify_event_review_20261104.py) | Validate external model review identities and verbatim evidence, not semantics. |
| [reports/defense_v1/T10/verify_four_type40_run_20261118.py](../reports/defense_v1/T10/verify_four_type40_run_20261118.py) | Audit fixed pairings, run identity, and attached generation evidence. |
| [reports/defense_v1/T10/verify_next_goal_delivery_20261117.py](../reports/defense_v1/T10/verify_next_goal_delivery_20261117.py) | 入口符号 read, digest, check_map |
| [reports/defense_v1/T10/verify_review_t10c_20261102.py](../reports/defense_v1/T10/verify_review_t10c_20261102.py) | Independently verify the T10-C external review file contract. |
| [reports/defense_v1/T10/verify_v2_reuse_review_20261105.py](../reports/defense_v1/T10/verify_v2_reuse_review_20261105.py) | Verify external v2 review contract and identities without accepting semantics. |

## 数据与结果文件的阅读顺序

数据、结果、审核 JSON 和图表从[数据目录](DATA_CATALOG_ZH.md)、[实验索引](EXPERIMENT_INDEX_ZH.md)及[实验结果汇总](EXPERIMENT_RESULTS_ZH.md)进入，按每次实验的 manifest 关联同批产物。冻结题单中的 requests、labels、lineage 分别记录请求、离线参考和来源，运行目录中的 events、artifacts、metrics 分别记录执行、生成材料和汇总。具体字段以相应代码和实验归档为准。

Git 跟踪和本地备份的范围见[Git 版本管理与同步](GIT_WORKFLOW_ZH.md)。
