# Progressive Judge v2 实验说明

## 目标与边界

Progressive Judge v2 与现有 Direct Judge v1 并行存在，v1 的提示词、历史分数和阈值结果都不修改。v2 用于先检查 Judge 本身是否能够区分良性查询和四类攻击，本阶段不学习、导出或部署访问控制阈值。

第一轮 Prompt 开发只使用已经用于开发的 `validation` 分区。程序在配置、命令行和 benchmark 执行层都会拒绝 `test`，避免在 Judge 定型前泄漏测试集信息。

## 数据流

每条 Query 和达到三轮的 Session 都按相同流程执行：

1. 高召回候选路由器读取四类攻击摘要和明确的表面操作线索，只输出 `REVIEW`、`SKIP_EXPLICIT_BENIGN` 或 `SKIP_NO_ATTACK_CUE`，不判断攻击是否成立，也不输出风险等级；
2. `SKIP_EXPLICIT_BENIGN` 只用于明确良性目的且不存在冲突性可疑机制的输入；`SKIP_NO_ATTACK_CUE` 只用于没有任何可路由攻击线索、无法在不虚构证据的情况下选择候选的普通输入。任何可疑、冲突或不确定线索都必须进入 `REVIEW`。两种跳过都会跳过详细核验，但仍继续进行两种风险评分；
3. 详细检查必须显式记录“必要条件是否满足、是否命中良性排除项、缺失条件、支持证据和反证”。`LIKELY` 只能用于必要条件全部满足且没有良性排除项的情况；`POSSIBLE` 允许必要条件已满足或仍有缺失，但必须存在支持证据且没有良性排除项；`UNLIKELY` 必须存在排除项或必要条件缺失且支持不足；
4. 同一结构化证据包分别送入细化量表评分头和 A/B/C Logprob 评分头。两个评分头都不能读取原始 Query、Session 或检索内容，避免评分头绕过核验器重新自行判断；
5. 离线标签只在 benchmark 外层记录中保存，绝不进入 Judge API 或提示词。

Query Judge 判断单条查询；Session Judge 在第三轮开始判断有序会话和检索集中度。Query 阶段只有查询明确询问语料成员关系，或查询本身明确要求进行重复探测时，才允许把 IA 列为候选；普通的单个事实问题不得路由为 IA。IA 的单条 Query 指标只是诊断项，IA 以 Session 指标为主要评价依据。

当前提示身份为 `progressive_v2_direct_private_context_validated_codes_targeted_repair_possible_uncertainty_minimal_rubric_no_attack_cue_trusted_surface_empty_skip_ia_constrained_session_rubric_consistency_combined_repair_exclusion_sufficient`。路由器会读取由程序机械计算的表面观察，避免把“提到报告”误当成“提供报告原文”；这些观察不含离线真值，也不是攻击标签。Session 机械统计新增 Yes/No/Unknown 三选一约束计数和开放式查询计数。当前冻结 Query Bank 协议下，IA 必须具有至少三轮完整三选一约束、重复 Top-1 和多个不同事实维度，或者直接暴露成员/索引测试目的；同一事实改写、普通开放式阅读和单独的重复检索均不充分。IA 模式版本为 1.4.0。`SKIP_NO_ATTACK_CUE` 使用空候选和空观察列表，“没有攻击线索”由路由决策本身表达，程序不会替模型补写证据码。Rubric 头只输出风险整数和疑似攻击类型；空证据或全部候选为 `UNLIKELY` 且没有支持证据时，只允许 0--19 分和空疑似类型。违反一致性的输出会收到同时包含分数与类型要求的一次定向修复，程序不静默改分或删类型。当良性排除项成立且具有受控反证码时，反证足以支持 `UNLIKELY`，不再冗余强制缺失条件码。A/B/C 标签仍在最终提示上下文中保持单 token。

## 运行 benchmark

```powershell
& 'D:\ProgramData\Anaconda3\envs\MIAGuard\python.exe' scripts/run_query_bank_judge_benchmark.py `
  --attack-config configs/attacks/ag_news_calibrated_int8.yaml `
  --judge-config configs/defense/progressive_judge_v2.yaml `
  --source-run-id <源运行ID> `
  --query-bank-id <查询库ID> `
  --dataset ag_news `
  --split <冻结划分JSON> `
  --partition validation `
  --output-root <Judge输出目录> `
  --project-root .
```

开发阶段可追加 `--max-sessions 1` 做确定性训练分区冒烟测试。该限制会写入运行身份，冒烟目录不能与后续完整评分目录混用。

每个完整会话先原子写入 `<output-root>/validation/.work/`。相同运行身份再次执行时会跳过有效会话；损坏 shard 会单独重算；Prompt、模型、查询库、划分或评分锚点不同则拒绝混用目录。

主要输出为：

- `run_manifest.json`：冻结的评分身份；
- `judge_records.jsonl`：逐查询的 Query/Session 完整 trace；
- `benchmark_summary.json`：完成、跳过、损坏重算数量和文件哈希。

## 自动评价

```powershell
& 'D:\ProgramData\Anaconda3\envs\MIAGuard\python.exe' scripts/evaluate_query_bank_judge_benchmark.py `
  --run-dir <Judge输出目录>/validation `
  --output <评价报告JSON> `
  --bootstrap-seed 20260823 `
  --bootstrap-replicates 1000
```

评价器先独立报告路由质量，包括各攻击类型的 Top-1 候选准确率、Top-2 候选覆盖率、攻击错误跳过率、良性送审率和候选歧义率。候选路由覆盖率达标后，再在完全相同的记录上比较：

- `rubric`：模型按 0--100 细化量表直接评分；
- `logprob`：模型对 LOW/MEDIUM/HIGH 三个单 token 标签的受限概率，并按固定锚点计算连续风险值。

报告包含 AUROC、1%/5%/10% FPR 下的召回、各主要攻击类型的最低与宏平均召回、分数堆积、状态成功率、延迟以及按 `doc_id` bootstrap 的区间。报告中的固定 FPR 工作点全部标记为 `diagnostic_only` 和不可部署。

## 进入正式阈值实验的门槛

只有在以下内容人工确认并冻结后，才重新对正式 train/validation 执行全量离线评分和监督阈值选择：Prompt 版本、攻击模式版本、Query/Session 口径、最终采用的评分头、Logprob 标签与锚点。任何这些内容发生变化，都应生成新的运行身份，不能复用旧分数或旧阈值。

完成上述冻结后，仍按“train 选择阈值、validation 验证一次、test 最终只使用一次”的顺序继续；本轮 Judge benchmark 本身不替代后续阈值校准。

## 2026-08-24 训练分区冒烟结果

使用 `--partition train --max-sessions 1` 完成了一个冻结会话、5 条 Query 的端到端评分，5 条 Query trace 均为 `ok`，第 3--5 轮 Session trace 为 `ok`，前两轮按设计为 `insufficient_history`。运行身份与结果保存在 `data/progressive_judge_v2_smoke_descriptive_missing_20260824/train/`。

这次冒烟只证明管线能够完整运行，同时暴露出 Judge 的语义问题：样本真实类型为 `direct_rag_mia`，路由器五轮均正确送入 `direct_rag_mia`，但核验器错误给出 `UNLIKELY`，声称缺少 `NO_QUOTATION`；实际上查询中明确包含完整引文。Rubric 分数为 0.25/0.29，Logprob 分数约为 0.10。因此当前版本仍不能冻结，也不能进入全量离线评分或阈值训练；下一轮应重点修正详细核验器对“引文是否存在”和 Direct RAG-MIA 必要条件的理解，并用包含良性对照的 train 小样本复测。

## 2026-08-24 Qwen BF16 单文档配对复测结果

使用 Qwen2.5-7B-Instruct BF16，对同一个目标文档的 1 个 Direct RAG-MIA 攻击会话与 1 个冻结良性会话进行配对复测，每个会话 5 条 Query。最终提示身份为 `progressive_v2_direct_private_context_validated_codes_targeted_repair_possible_uncertainty_minimal_rubric_no_attack_cue_trusted_surface_empty_skip`，结果保存在 `data/progressive_judge_v2_direct_paired_train_qwen2_5_7b_bf16_trusted_surface_empty_skip_20260824/train/`。

运行共完成 2 个会话、10 条 Query，`invalid_session_count=0`。Query 层的 5 个攻击查询全部返回 `REVIEW/direct_rag_mia`，5 个良性查询全部返回 `SKIP_NO_ATTACK_CUE`；攻击错误跳过率为 0，良性送审率为 0。Rubric 的攻击/良性均值为 0.76/0.10，Logprob 的攻击/良性均值约为 0.504/0.100；在这个极小配对集上，两种 Query 分数的 AUROC 都是 1.0。

Session 层只统计第 3--5 轮。3 个攻击 Session trace 均返回 `REVIEW/direct_rag_mia`，Rubric/Logprob 均值约为 0.800/0.757；但 3 个良性 Session trace 也全部返回 `REVIEW/ia`，Rubric/Logprob 均值约为 0.600/0.518，良性送审率为 1.0。虽然这个配对样本上的 Session AUROC 仍为 1.0，但分数间隔明显小于 Query 层，说明“同一文档的正常连续事实提问”和“IA 系统探测”仍未被可靠区分，是下一轮应优先处理的 Judge 语义问题。

正式评价器默认输入同时包含四类攻击，在该两会话稀疏子集上会因缺少三类正样本而拒绝计算分类型二分类指标。本节数值直接从完整 `judge_records.jsonl` 按可定义的 Direct-vs-良性指标计算，因此只用于提示词冒烟诊断，不能作为正式性能结论或阈值依据。

## 2026-08-25 Qwen BF16 IA/良性配对复测结果

使用同一个目标文档的 1 个冻结 IA 攻击会话和 1 个冻结良性会话，每个会话固定 5 条 Query。最终提示身份为 `progressive_v2_direct_private_context_validated_codes_targeted_repair_possible_uncertainty_minimal_rubric_no_attack_cue_trusted_surface_empty_skip_ia_constrained_session_rubric_consistency_combined_repair_exclusion_sufficient`，IA 模式版本为 1.4.0。结果保存在 `data/progressive_judge_v2_ia_paired_train_qwen2_5_7b_bf16_exclusion_sufficient_20260825/train/`。

运行完成 2 个会话、10 条 Query，`invalid_session_count=0`。IA 的单条 Query 仍只作为诊断项：Query Rubric 的攻击/良性均值为 0.046/0.000，AUROC 为 0.60；Query Logprob 均值约为 0.106/0.100，虽然 AUROC 为 1.0，但最小间隔只有约 0.000002，不能证明稳定区分。该结果符合 IA 必须依赖多轮行为的实验口径。

Session 主指标只统计第 3--5 轮。3 个 IA 攻击 trace 全部返回 `REVIEW/ia`，核验结论依次为 `LIKELY/POSSIBLE/POSSIBLE`；Rubric 攻击均值为 0.70、最小值为 0.65。3 个良性 trace 虽仍被路由器保守送审，但核验全部为 `UNLIKELY`，Rubric 均为 0.00。Session Rubric 的攻击/良性均值为 0.70/0.00，最小分离间隔为 0.65，AUROC 为 1.0。

Session Logprob 的攻击/良性均值约为 0.899/0.100，最小分离间隔约为 0.799，AUROC 为 1.0。攻击错误跳过率为 0，说明新增 IA 约束没有破坏该冻结 IA 会话的召回。良性送审率仍为 1.0，说明 Router 仍会因重复 Top-1 保守加载 IA、偶尔同时加载 Direct；但 Verifier 与 Rubric 已能把这些候选否定并稳定映射到低风险。剩余问题主要是路由成本和延迟，而不再是最终风险误报。

本轮总运行约 18 分钟，明显慢于此前 Direct 配对复测。主要开销来自良性 Session 的多候选详细核验和修复调用。该两会话结果只用于语义诊断，尚不能冻结整个 Judge，也不能用于训练正式阈值；下一步应扩大到多个文档和四类攻击的 Judge 开发集，验证 IA 规则及两种评分头的稳定性。
