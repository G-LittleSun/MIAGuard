# MIAGuard 攻击识别阶段交接文档

记录日期：2026-10-15（北京时间）；rubric 独立评估状态同日补正  
项目根目录：`D:\Project\MIAGuard`  
性质：攻击识别阶段的完成快照与访问控制阶段的开发入口。本文依据现存代码、运行清单及实验结果核对，不代表下一阶段已经完成。

## 0. 新会话先读这里

当前已实现面向 RAG 成员推断攻击的证据化识别框架：Query/Session 两阶段检测、四类攻击模式库、候选路由、逐候选证据核验、共享证据上的两种评分头，以及按文档分组训练的风险融合。

本轮要比较的两种方案是：**LLM 按量表直接评分（rubric）**与**二分类归一化 logprob（logprob）**。两者共享前面的证据化 Judge。旧三分类锚点评分不属于当前比较目标，不再续跑其对比实验。

两种评分头都已完成训练集分布分析、分组交叉验证、阈值选择，以及各自冻结模型的 validation/test 评估。rubric 的独立评估使用已保存的 Judge 记录离线完成，没有重新调用 LLM；最终同口径测试对比见[实验索引](EXPERIMENT_INDEX_ZH.md)。

下一阶段目标是把新版识别器和冻结融合模型接入 RAG 访问控制，验证防御是否减少成员信息泄露，以及对正常使用和延迟的影响。现有网关和访问策略可复用，但**新版冻结融合模型尚未接入在线网关，当前识别指标不能直接称为完整防御效果**。

新会话先读[项目状态](PROJECT_STATUS_ZH.md)、[数据目录](DATA_CATALOG_ZH.md)和[实验索引](EXPERIMENT_INDEX_ZH.md)，再按任务阅读本文第 5 节的冻结模型、第 8 节的产物位置和第 10 节的接入说明。后续访问控制开发另建文档，引用本快照；若发现本快照事实有误，应在文末追加更正记录。

## 1. 阶段目标、范围和当前状态

本阶段判断请求是否表现为攻击行为；监督标签是 `traffic_type=attack/benign`，不是目标文档是否属于私有语料库。`membership_label` 记录成员身份，供数据审计和攻击效果评估使用，不作为当前攻击识别的训练目标，也不应传入 Judge 提示词。

| 工作项 | 当前状态 |
|---|---|
| 四类攻击模式库、Query/Session 证据化 Judge | 已实现 |
| rubric 与二分类 logprob 两种评分头 | 已实现，并在同一批记录中保存 |
| 训练集分布分析与人工确认后再训练 | 已完成；融合清单中 `stage_a_reviewed=true` |
| x1-only、x2-only、融合模型的文档分组 OOF 比较 | 已完成，两种评分头均有结果 |
| 1% / 5% 正常 FPR 约束的阈值选择 | 已完成；本次两种约束选到相同工作点 |
| logprob + L2 Logistic 的独立冻结评估 | validation / test 均已完成 |
| rubric + L2 Logistic 的独立冻结评估 | validation / test 均已完成；离线复用已保存的 Judge 记录 |
| 新版 Judge → 冻结融合模型 → 在线访问控制 | 尚未完成接入 |
| 基于新版检测的攻击泄露、正常效用和时延评估 | 下一阶段任务 |

注意：Stage A 的原始清单仍写有 `awaiting_human_review` / `classifier_training_authorized=false`，它是生成分析时的快照。后续 Stage B 清单的 `stage_a_reviewed=true` 记录了训练前的确认，不要据 Stage A 字段误判为从未进行融合训练。

## 2. 已实现的攻击识别架构

```text
当前 Query + 会话历史 + 检索文档 ID/分数
  ├─ Query Judge：分析当前查询
  └─ Session Judge：从第三轮开始分析多轮行为
       每个 Judge 内部均执行：
       机制筛查 → 候选攻击路由（最多两类）→ 逐候选核验 → 结构化证据包
                                                        ├─ rubric 评分
                                                        └─ 二分类 logprob 评分

每种评分头分别得到 x1（Query）和 x2（Session）
  → 在训练集按 doc_id 分组交叉验证，训练融合分类器
  → 从 OOF 预测选择阈值
  → 全训练集拟合并冻结模型 → validation 确认 → test 评估
```

两种评分头读取同一份路由结果及核验后的结构化证据，不在最后评分时重新读取原始 Query/Session。它们是两个对照方案，不是把 rubric 和 logprob 再合成一个分数。

### 2.1 四类攻击模式与证据核验

模式库版本 `1.7.0`，入口为 [manifest.yaml](../attack_pattern_library/manifest.yaml)。各模式包含必要条件、良性排除条件及允许的证据码。

| 模式 ID | 版本 | 识别关注点 |
|---|---|---|
| `direct_rag_mia` | 1.3.0 | 给出具体文本，探测私有检索上下文是否包含或支持该文本 |
| `s2_mia` | 1.3.0 | 给出来源式前缀，要求依靠上下文恢复原文后续内容 |
| `masked_mia` | 1.3.0 | 对来源文本挖空，要求依靠上下文恢复准确原文 |
| `ia` | 1.6.0 | 围绕同一目标进行多轮受约束事实探测；普通阅读、同一事实改写、重复检索本身不足以成立 |

路由可进入 `REVIEW`，也可因明确良性或缺少攻击线索跳过详细核验；跳过详细核验仍继续执行评分头。核验为每个候选输出 `UNLIKELY/POSSIBLE/LIKELY`、必要条件是否满足、是否命中排除项、缺失条件、支持和反证码。程序校验结构和一致性，配置允许一次修复重试。结构化证据是模型产生并经程序校验的判断，不等同于人工逐条确认的事实真值。

### 2.2 Query 与 Session 的输入边界

- Query 接口为 `ProgressiveJudge.evaluate_query(query=..., session_id=...)`，判断单条查询。
- Session 接口为 `evaluate_session(...)`，接收有序历史、当前查询、检索文档 ID/分数和最小轮数；使用重复 Top-1、检索集中度及查询形式等会话统计。
- 当前离线 benchmark 按每会话 4～5 轮规划，从第 3 轮产生可用 Session 分数；会话之间不共享历史。
- 前两轮状态为 `insufficient_history`。trace 中可能有占位数值，但分析表的 `x2_observed` 为缺失值，主融合评估排除这些行。`x2_filled` 虽存在于表中，也不是当前主模型使用的特征。
- 当前结果是满足 Session 历史条件的逐轮判断结果，不是覆盖全部轮次的线上端到端检出率，也不是“任意一轮检出即会话检出”的会话级指标。

### 2.3 两种评分头的精确定义

**rubric：**LLM 按提示中的语义量表输出 `risk_score`（0～100 整数），程序除以 100。量表区间为 0～19、20～39、40～59、60～79、80～100，分别对应低风险、弱可疑、模糊、高风险和强直接证据。分数由模型选择，程序还校验疑似类型与核验证据是否一致；它不是按证据码计数的确定性公式。

**logprob：**提示固定 `A=BENIGN`、`B=ATTACK`。只有已核验的证据使攻击解释比良性解释更合理、必要条件满足且无良性排除时，才支持 ATTACK；仅有模糊怀疑不充分。候选使用 A/B 是为保证最终提示上下文中各对应一个 Qwen token，直接使用 BENIGN/ATTACK 曾因多 token 失败。

```text
x = P(B) / [P(A) + P(B)]
```

`ModelClient.candidate_label_probabilities` 读取最终输出位置 A、B 的 logits，在这两个候选间归一化，不要求模型生成一个数。该值表示受限标签间的相对倾向，不天然等于真实攻击发生概率；本文 Brier 等指标衡量的是后续融合输出，不能直接用来证明原始 token 概率已校准。

两种方案中 `x1` 均指当前 Query 风险，`x2_observed` 均指当前可用的 Session 风险。相同特征名必须与评分头身份一同解释，不能混用 rubric 的 x1 和 logprob 的 x2。

## 3. 数据、模型与实验身份

| 项目 | 本阶段使用的身份 |
|---|---|
| 数据集 / 查询库 | `ag_news` / `ag_news_queries_v1` |
| 来源运行 | `20260717-ag-news-four-medium` |
| 文档冻结划分 | `ag_news_threshold_v1`，train/validation/test = 60/20/20 文档 |
| 划分文件 | `data/query_bank_splits/ag_news_threshold_v1.json` |
| Judge 模型 | `LLM/Qwen2.5-7B-Instruct`，Transformers，BF16 |
| 检索 | FAISS，`all_minilm_l6_v2` embedding，top-k=4 |
| Judge 配置 | `configs/defense/progressive_judge_v3_binary_logprob_qwen2_5_7b.yaml` |
| 对应模型配置 | `configs/attacks/ag_news_progressive_judge_qwen2_5_7b_bf16.yaml` |
| Prompt 身份 | `progressive_v3_binary_logprob_strict_validated_attack_evidence` |
| Session 协议 | `all_accepted_balanced_sessions_v1`，目标 5 轮，最小可用历史 3 轮 |

以各运行的 `run_manifest.json` 为实际身份依据。不要从带 `int8` 字样的其他配置名推断本实验模型；当前 `ag_news_calibrated_int8.yaml` 配置为 Mistral INT8，与这三份已完成的 Qwen BF16 记录不一致。

| 分区 | 文档数 | 全部查询数 | 会话数 | 每个评分头可用 x1+x2 行数 | 其中正常行数 |
|---|---:|---:|---:|---:|---:|
| train | 60 | 3,575 | 734 | 2,107 | 180 |
| validation | 20 | 1,194 | 248 | 698 | 60 |
| test | 20 | 1,187 | 244 | 699 | 60 |

全部查询合计 5,956 条，审计无缺失、重复或越界。训练分析长表 7,150 行，是 3,575 条原始记录按两个评分头展开，不是新增样本。训练融合 cohort 的其余组成是 Direct/S²/Masked 各 180 条、IA 1,387 条；test 对应各 60 条、IA 459 条，类别比例明显不均衡。

## 4. 训练、模型比较和阈值选择规则

1. 只对 train 做分布分析并确认，再进入融合训练。已导出边际分布、二维密度、分类型富集和分数随轮次可用性图；以图目录及 figure manifest 为准，不把尚未核对的图形类型写成已交付。
2. 使用 `StratifiedGroupKFold`，5 折、seed=`20260918`、分组单位 `doc_id`。同一文档不会同时进入一折的训练和评估。
3. 比较 `x1_only`、`x2_only`、固定 `0.4x1+0.6x2`、`logistic_l2`、带交互项 Logistic、MLP（2→8→1）；两个评分头均执行。
4. 拟合权重在每折训练数据内计算：正常流量占总权重 0.5，四类攻击各占 0.125；各类别内按文档均分，文档内部再按记录均分。权重总和为 1。
5. 每条记录获得未参与该折模型拟合的 OOF 预测。基于整份 OOF 选择阈值，因此阈值处的 OOF 指标含选择用途，不能替代独立测试。
6. 阈值扫描在正常 FPR ≤1% / ≤5% 的候选中，依次最大化四类攻击宏平均 Recall、最弱攻击 Recall，再偏好更低 FPR 和更低阈值。以 `select_threshold_at_fpr` 的实现为准。
7. Stage B 使用 `doc_id` 为单位做 1,000 次 bootstrap，seed=`20260918`，区间存于模型比较文件。冻结 validation/test JSON 当前未给出相应区间。

继续采用 logprob + L2 Logistic 作为已冻结主方案，理由是模型简单、便于部署和解释，且完成了后续锁定评估；不要描述为所有候选指标上最优。例如固定加权的 OOF 宏平均召回略高、部分 MLP 的 Brier 更低。不能根据已经看到的 test 结果重新挑选模型。

## 5. 可供下一阶段接入的冻结产物

主方案冻结文件：[logprob logistic_l2.json](../data/judge_score_frozen_v3_binary_logprob_20260920/logistic_l2.json)。对照方案冻结文件：[rubric logistic_l2.json](../data/judge_score_frozen_v3_rubric_20261015/logistic_l2.json)。两者使用相同特征名，但系数与阈值不同，不可互换。

```text
评分头：logprob
特征顺序：[x1, x2_observed]
z = -0.10300497867119779
    + 0.12467715894312009 * x1
    + 0.1792509147102471  * x2_observed
融合分数 = 1 / (1 + exp(-z))

严格工作点（正常 FPR 上限 1%）：threshold = 0.4798231627374044
平衡工作点（正常 FPR 上限 5%）：threshold = 0.4798231627374044
判断规则：融合分数 >= threshold 时识别为攻击
```

模型在全部 60 个训练文档、2,107 条可用记录上拟合，阈值来自 OOF。其分数尺度与原始 x1/x2 不相同，不能把原始分数、旧网关总分和冻结融合分数的阈值互换。当前权重归一化与 L2 正则的组合也是模型定义的一部分，后续不要无记录地改变权重尺度或 C 值再沿用旧阈值。

冻结器使用 `LogisticRegression(penalty='l2', C=1.0, solver='lbfgs', max_iter=1000, random_state=20260918)`。`judge_score_frozen.py` 现可按冻结产物中的 `head` 选择 rubric 或 logprob 记录；现有 `scripts/validate_judge_score_fusion.py` 命令仍默认固定为 logprob。rubric 冻结与 validation 产物通过冻结评估 API 离线生成，test 产物使用相同冻结身份评估。rubric 的 1%/5% 工作点都使用阈值 `0.4993095180045256`。

1% / 5% 两种约束选到同一个阈值是本次训练数据的结果；它们是两个命名工作点，尚未形成两种不同的实际控制强度。冻结 JSON 本身不包含完整输入哈希，追溯时还须保留第 8、9 节的上游记录。

## 6. 已完成实验结果

### 6.1 两种评分头的训练集分组 OOF 对照

以下均为各自评分头的 `logistic_l2`，每头 2,107 行。1% 与 5% 工作点的结果相同。

| 指标 | LLM 直接评分（rubric） | 二分类 logprob |
|---|---:|---:|
| AUROC | 0.888843 | 0.879652 |
| AUPRC（average precision） | 0.987928 | 0.987320 |
| Brier（越低越好） | 0.241493 | 0.239332 |
| 正常 FPR | 0% | 0% |
| Accuracy | 81.49% | 81.49% |
| Precision | 100% | 100% |
| 整体攻击 Recall | 79.76% | 79.76% |
| F1 | 88.74% | 88.74% |
| 四类攻击宏平均 Recall | 92.25% | 92.25% |
| Direct / IA / Masked / S² Recall | 96.67% / 72.31% / 100% / 100% | 96.67% / 72.31% / 100% / 100% |
| 阈值 | 0.4993095180045256 | 0.4798231627374044 |

来源：Stage B 的 `model_comparison.json` 与 `threshold_selection.json`。其中 Accuracy/Precision/整体 Recall/F1 在本次文档核对时，从既有 `oof_predictions.parquet` 和既有阈值只读计算，未重训练或重选阈值。

### 6.2 x1 / x2 的互补性：logprob 训练 OOF

| 模型 | AUROC | 正常 FPR | 四类攻击宏平均 Recall | IA Recall |
|---|---:|---:|---:|---:|
| x1-only | 0.658681 | 0% | 71.32% | 20.84% |
| x2-only | 0.874053 | 0% | 90.43% | 69.50% |
| x1+x2 L2 Logistic | 0.879652 | 0% | 92.25% | 72.31% |

这是相同“Session 分数可用”cohort 上的比较。结果支持多轮信息对本数据中的 IA 识别有帮助，融合较单分数有补充作用；没有覆盖前两轮线上行为。分布的直观观察和该表互相补充，不能用肉眼分离替代独立评估。

### 6.3 已冻结 logprob + L2 Logistic 的 validation / test

| 指标 | validation | test |
|---|---:|---:|
| 文档 / 可用记录 | 20 / 698 | 20 / 699 |
| AUROC | 0.870690 | 0.861502 |
| AUPRC（average precision） | 0.979734 | 0.978831 |
| Brier | 0.240470 | 0.241058 |
| Accuracy | 78.51% | 77.97% |
| Precision | 100% | 100% |
| 整体攻击 Recall | 76.49% | 75.90% |
| F1 | 86.68% | 86.30% |
| 正常 FPR | 0% | 0% |
| 四类攻击宏平均 Recall | 90.73% | 90.53% |
| 最弱攻击 IA Recall | 67.90% | 67.10% |
| Direct Recall | 95% | 95% |
| Masked / S² Recall | 100% / 100% | 100% / 100% |

两个 FPR 约束使用第 5 节同一冻结阈值，两列结果均未从各自评估分区重选阈值。整体 Recall 按攻击记录计算；宏平均 Recall 对四种攻击等权。IA 记录较多，因而整体 Recall 明显低于宏平均 Recall。

### 6.4 rubric 的独立评估与最终对照

rubric 使用 train 上的 60 个文档、2,107 条可用记录拟合独立的 L2 Logistic，阈值来自 rubric 自己的训练 OOF。validation 为 20 文档、698 条可用记录：AUROC `0.882445`、F1 `0.866785`、良性 FPR `0`。test 为相同的 20 文档、699 条可用记录：AUROC `0.879499`、F1 `0.859946`、良性 FPR `0`、IA Recall `0.664488`。logprob 在同一 test cohort 上的对应值是 AUROC `0.861502`、F1 `0.862989`、良性 FPR `0`、IA Recall `0.671024`。完整指标、两个 FPR 工作点及产物链接以[实验索引](EXPERIMENT_INDEX_ZH.md)和[最终对比 JSON](../data/judge_score_comparison_v3_20261015/final_test_comparison.json)为准。

## 7. 可支持的结论与尚不能支持的结论

可以支持：当前证据化 Judge 流程可在这批冻结数据上运行；两种评分头均有独立 validation/test 检测结果，整体效果接近；IA 是当前较弱的攻击类型，多轮分数比仅使用单查询分数更有效。

尚不能支持：一种评分头在统计意义上总体优于另一种；直接评分本质上不可靠；证据化设计是性能的主要因果来源；token 概率或融合分数已良好校准；实际线上 FPR 一定 ≤1%；新版框架已有效降低成员推断攻击成功率。这些分别需要不确定性/稳定性检验、消融、校准评估或访问控制后的防御实验。

特别注意以下实验边界：

- test 的可用正常记录仅 60 条、来自 20 个文档，且同会话记录相关；本次 0% 误报不能当作部署保证。AUPRC 很高也受攻击占比较高影响，应连同类别比例、AUROC、Brier 和分类型召回报告。
- 对比表衡量的是“评分头 + 后续融合”组合，不能仅凭该表断言原始 rubric 和原始 logprob 完全等价。小幅 Brier 差异也不等同于充分的校准优势证明。
- rubric 独立评估是在 logprob test 已被查看后补充的固定基线分析，不能宣称整套新对比从未接触过 test。模型/提示或策略变更应使用开发数据，最终确认考虑新的保留数据。
- 早期 [v2 实验说明](PROGRESSIVE_JUDGE_V2_EXPERIMENT_ZH.md) 写明 validation 曾用于 Prompt 开发；现阶段不宜无审计地宣称该 validation 在整个项目历史中完全未用于开发。若需要严格独立性结论，应核对实际使用文档和版本历史，必要时建立新保留集。

## 8. 核心实现与实验产物索引

下表路径均相对于项目根目录。新会话应读实际文件确认字段，不只依赖历史对话。

| 路径 | 用途 |
|---|---|
| `src/miaguard/progressive_judge.py` | Judge 配置、Query/Session 接口、路由、核验、评分提示及 trace |
| `src/miaguard/attack_pattern_library.py` | 加载攻击模式库 |
| `attack_pattern_library/manifest.yaml`、`JUDGE_PROTOCOL.md`、`patterns/` | 模式版本、协议和模式正文 |
| `src/miaguard/model_client.py` | 本地模型调用、候选单 token 校验与受限概率 |
| `src/miaguard/query_bank/sessions.py`、`threshold_split.py` | 会话规划和冻结划分 |
| `src/miaguard/query_bank/judge_benchmark.py` | 逐会话评分、分片续跑、运行身份及文件校验 |
| `src/miaguard/judge_score_dataset.py` | 双头长表、标签、状态与 x2 可用性处理 |
| `src/miaguard/judge_score_analysis.py` | 分布统计和图形 |
| `src/miaguard/judge_score_fusion.py` | 分组 OOF、训练权重、模型比较、阈值和曲线 |
| `src/miaguard/query_bank/judge_score_workflow.py` | train-only 分析/训练工作流与人工确认入口 |
| `src/miaguard/judge_score_frozen.py` | 按评分头冻结 L2 Logistic 并做独立评估 |
| `tests/test_progressive_judge.py`、`tests/test_query_bank_judge_benchmark.py` | Judge/评分运行相关回归测试 |
| `tests/test_judge_score_dataset.py`、`test_judge_score_analysis.py`、`test_judge_score_fusion.py`、`test_judge_score_workflow.py`、`test_judge_score_frozen.py` | 分析、融合和冻结流程相关测试；后四项同属 `tests/` |

### 8.1 已完成评分与分析目录

| 产物 | 路径 |
|---|---|
| 会话审计 | `reports/ag_news_threshold_session_plan_audit.json` |
| 正式 train 评分 | `data/progressive_judge_v3_binary_logprob_train_qwen2_5_7b_bf16_20260916_retry1/train/` |
| 正式 validation 评分 | `data/progressive_judge_v3_binary_logprob_validation_qwen2_5_7b_bf16_20260918/validation/` |
| 正式 test 评分 | `data/progressive_judge_v3_binary_logprob_test_qwen2_5_7b_bf16_20260920/test/` |
| Stage A 分布分析 | `data/judge_score_analysis_v3_binary_logprob_20260918/train/` |
| Stage B 分组融合 | `data/judge_score_fusion_v3_binary_logprob_20260918/train/` |
| 冻结模型 | `data/judge_score_frozen_v3_binary_logprob_20260920/logistic_l2.json` |
| validation 结果 | `data/judge_score_validation_v3_binary_logprob_20260920/validation.json` |
| test 结果 | `data/judge_score_test_v3_binary_logprob_20260920/test.json` |
| rubric 冻结模型 | `data/judge_score_frozen_v3_rubric_20261015/logistic_l2.json` |
| rubric validation / test | `data/judge_score_validation_v3_rubric_20261015/validation.json`；`data/judge_score_test_v3_rubric_20261015/test.json` |
| 双方案最终 test 对比 | `data/judge_score_comparison_v3_20261015/final_test_comparison.json` |

每个正式评分目录包含 `run_manifest.json`、`judge_records.jsonl`、`benchmark_summary.json` 和 `.work/` 分片。三份汇总均为完整运行，无损坏分片重算或已完成会话跳过计数。Stage A 包含 `separability_dataset.parquet`、`score_audit.json`、`separability_report.json`、`figure_manifest.json`、`figures/`；Stage B 包含 `oof_predictions.parquet`、`model_comparison.json`、`threshold_selection.json`、运行与图形清单及 ROC/PR/Calibration/低 FPR 图。

不要把最初失败的 `...train_qwen2_5_7b_bf16_20260916/` 当作正式 train；有效版本是上表带 `_retry1` 的目录。旧说明文档中的示例日期和输出名不一定对应正式产物。

### 8.2 历史中断任务（排除出本轮结果）

`data/progressive_judge_v2_three_class_logprob_train_qwen2_5_7b_bf16_20260929/train/` 是误扩展到旧三分类比较后启动的运行。其已有 26 个会话分片，无最终汇总；日志 `data/logs/progressive_judge_v2_three_class_train_20260929.stderr.log` 记录 `suspected_attack_types must be a list of strings`，一次修复后仍失败导致程序退出。

用户已明确取消该比较方向，无需为当前阶段补跑。此故障也说明 benchmark 尚无逐条失败后自动继续的完整容错，在线接入时需明确失败策略。不得把失败样本静默记成正常，或删除后不报告覆盖率。本快照建立过程未修复或重启该历史任务。

## 9. 溯源与只读复核

查询库 SHA256：`93b0baf6d1e660cae31dc57cd7cd33c797f2f71b0f0f14f0b59a1d9db3f040e1`。划分文件 SHA256：`c7f42950276f787bbc38862fad219b7c2436c8e562a9447c52388b0b809d8a93`。

| 文件 | SHA256 |
|---|---|
| 正式 train 的 `judge_records.jsonl` | `afb19dfce92bc584db11842bd9716fbae341f0b1d0e2287b21b9d344c55ba378` |
| 正式 validation 的 `judge_records.jsonl` | `81dc7406a643a04311489ac1fb4efd60c6dcb0ce4ceaec51a2c4e23bd44f1241` |
| 正式 test 的 `judge_records.jsonl` | `d920fea4fbd0aa8dc484c7303fbbabf9ed04b78d1c2f18aa5adf169884d34c20` |
| 冻结 `logistic_l2.json` | `b24b81b88a4ce9579e81eb51cb4e0cc940972dc22499fce77ef80c60f587d188` |

运行身份哈希：train=`56f9e13083dcdab067e204a4517a3a32d2420b77dbad3a241e810198b7744d4d`；validation=`4e671f2ab430a0411bfb6b4007a41a4e8003473e6d60f30984e539fb2b0ce00f`；test=`ccdeecc688a4090c4b3519ba85e46f93f8f342487c3d35a686cf93af3880accf`。身份含分区，三者哈希不同是正常现象，应比较公共模型/Prompt/模式库/数据身份而非要求整个哈希相同。

本次建档已用 `load_verified_judge_records` 通过三份评分文件的身份和内容校验，再从记录构建长表确认 cohort 数量；没有重新执行 GPU 评分或修改阈值。

## 10. 下一阶段：访问控制接入说明

### 10.1 可以复用的代码及边界

| 组件 | 已有职责 | 接入新版时须注意 |
|---|---|---|
| `src/miaguard/defense.py` 的 `GuardedRAG.prepare` | Query 检测、检索、调用网关 finalize、按动作准备上下文 | 该顺序中 Session 检测发生在取得检索元数据后、回答生成前 |
| `src/miaguard/two_stage_gateway.py` 的 `TwoStageGateway` | 会话状态、检测器调用、聚合、策略、审计 | 接受的是输出 `RiskResult` 的 detector，现有 `ProgressiveJudgeTrace` 不能直接等同替换 |
| `src/miaguard/risk_types.py` | `RiskResult`、`SessionTurn`、策略和聚合结果结构 | 新适配器需保留分数、状态、证据、延迟和版本身份 |
| `src/miaguard/session_store.py` | 会话窗口、超时与清理 | 必须明确新在线窗口与当前 4～5 轮离线协议的关系 |
| `src/miaguard/risk_aggregator.py` | 旧固定/窗口覆盖加权及 Query/极高风险保护 | 它不是本阶段训练的 Logistic，不可把旧聚合结果套用新阈值 |
| `src/miaguard/access_policy.py` | L0～L4、observe/enforce、可选攻击阈值 | 攻击阈值与四个严重度阈值含义不同 |
| `src/miaguard/defense_experiment.py` | 生成回答、部分动作的下游执行与攻击回放辅助 | 摘要及拒答不是只靠网关动作字符串就全部完成 |

现有 L0/L1 允许正常访问或审计；L2/L3/L4 对应限制上下文、摘要、拒绝敏感回答等策略。实际 `GuardedRAG` 中 `restrict_context` 只保留首个命中并截断；`summarize_context` 本身只保留首个命中全文，摘要生成在 `defense_experiment._response_contexts`。拒答在 `_text_response` 等下游响应路径实现。新服务需核对自己确实走到了相应处理。`ENABLE_RATE_LIMIT` 当前是策略动作码，不能仅凭它认定有真实限流器。

### 10.2 建议接入顺序与待确定设计

1. 为 Progressive Judge 建立 detector 适配，明确如何从共享证据得到主方案分数、疑似类型和证据码。当前 `_evaluate` 同时调用两个评分头；上线只用 logprob 时是否保留 rubric 调用，需要独立决策并记录性能/行为差异。
2. 新增能读取冻结 JSON 的在线融合入口，严格校验 `head`、特征顺序、模型和阈值身份；不要把 Logistic 接入变成无记录地重新训练或改权重。
3. 明确前两轮策略。可评估 Query-only 作为启动期策略，但现有主融合性能没有证明此策略的完整效果；不能简单用 0 替代缺失 x2 后声称沿用原评估。
4. 明确检测失败/超时处理、跨会话隔离、窗口大小和执行时延。异常不应被误认作正常分数，策略选择应形成可测试的配置。
5. 先以 observe 模式核对在线与离线特征、分数和决策一致性，再在 enforce 中实现选定的访问动作。当前冻结分数较集中，不能不经分析就复用旧的 L0～L4 数字边界。
6. 在开发数据上确定访问策略，记录无防御与防御条件的真实 RAG 回答和攻击结果；联合报告攻击成功/泄露、正常任务效用、误拒绝、动作分布、延迟及首次检出轮次。访问控制可能改变后续检索/回答和行为，不能仅重用静态风险表代替防御回放。
7. 当前 test 的检测结果已被查看。访问策略调试应使用开发数据；最终防御报告须明确测试复用情况，并在需要严格最终确认时采用新保留集。

以上为下一阶段开发建议，不是已完成清单；不要从本文推断在线接入或防御有效性已经验证。

## 11. 必要运行入口与复现方式

以下命令在项目根目录的 PowerShell 中执行。既有结果无需重跑；需要新实验时使用新的输出路径，并记录变更，避免覆盖阶段快照。

```powershell
$python = 'D:\ProgramData\Anaconda3\envs\MIAGuard\python.exe'
```

| 工作 | 脚本 | 关键参数 |
|---|---|---|
| train/validation Judge 评分 | `scripts/run_query_bank_judge_benchmark.py` | `--attack-config`、`--judge-config`、`--source-run-id`、`--query-bank-id`、`--dataset`、`--split`、`--partition`、`--output-root` |
| 训练分布分析 | `scripts/analyze_judge_scores.py` | `--run-dir`、`--output-dir`、`--bootstrap-seed 20260918` |
| 文档分组融合 | `scripts/train_judge_score_fusion.py` | `--analysis-dir`、`--output-dir`、`--stage-a-reviewed`、`--cv-splits 5 --cv-seed 20260918 --bootstrap-seed 20260918` |
| 冻结并验证 logprob | `scripts/validate_judge_score_fusion.py` | `--train-analysis-dir`、`--fusion-dir`、`--validation-run-dir`、`--frozen-output`、`--output`；当前脚本固定 logprob |
| 冻结身份下的最终 test 评分 | `scripts/run_frozen_test_judge_benchmark.py` | `--frozen-artifact` 及模型、Judge、查询库、划分和输出参数；只用于已锁定实验 |
| 从现存 test 记录评估 | `scripts/evaluate_frozen_test_judge_fusion.py` | `--frozen-artifact`、`--test-run-dir`、`--output`；按冻结产物中的评分头取分 |

不调用 GPU、只用现存记录复核 logprob 测试结果的示例；输出使用新名字，若已存在则停止：

```powershell
$taskOutput = 'data/judge_score_test_v3_binary_logprob_20260920/test_recheck_20261015.json'
if (Test-Path -LiteralPath $taskOutput) { throw '复核文件已存在，请选择新文件名' }
& $python scripts/evaluate_frozen_test_judge_fusion.py `
  --frozen-artifact data/judge_score_frozen_v3_binary_logprob_20260920/logistic_l2.json `
  --test-run-dir data/progressive_judge_v3_binary_logprob_test_qwen2_5_7b_bf16_20260920/test `
  --output $taskOutput
```

这是对既有冻结结果的复核，不是重新选模型或查看新 test。rubric 已用独立冻结模型和原 train OOF 的 rubric 阈值完成补评估；不要用 logprob 冻结 JSON 解释 rubric 分数。

## 12. 维护与核查记录

- 2026-10-15：创建阶段快照；读取当前实现、配置、Stage A/B 清单和结果；校验三分区原始评分，核对 cohort；从既有 OOF 补算表中四项分类指标；确认冻结模型和关键文件哈希。本次仅新增交接文档，未修改代码、评分、模型、阈值或历史实验产物。
- 本文不把历史对话中的测试通过次数当作当前代码测试证明。下一阶段有代码修改时，应运行相应 Judge/融合/网关/访问控制测试；纯文档交接的核查重点是路径、数值和状态是否与现存产物一致。
- 配套旧文档可查 [v3 实验说明](PROGRESSIVE_JUDGE_V3_BINARY_LOGPROB_EXPERIMENT_ZH.md)、[v3 设计](superpowers/specs/2026-09-16-progressive-judge-v3-binary-logprob-design.md)、[冻结评估设计](superpowers/specs/2026-09-20-frozen-fusion-validation-design.md)。历史设计中的语义标签或示例路径应按本快照与实际运行清单核对，不要直接覆盖已完成产物。
- 2026-10-15 补正：rubric 的独立冻结、validation/test 评估和同口径最终对比已完成；修订第 0、1、5～8、11 节的过期状态。阶段后续开发以[项目状态](PROJECT_STATUS_ZH.md)、[数据目录](DATA_CATALOG_ZH.md)和[实验索引](EXPERIMENT_INDEX_ZH.md)为入口。
