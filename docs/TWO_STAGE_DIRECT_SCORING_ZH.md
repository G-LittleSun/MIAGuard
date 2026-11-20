# MIAGuard 两阶段 LLM Direct Scoring 使用与实验说明

## 1. 本阶段实现内容

当前已经按照两阶段方案实现“本地大模型直接风险评分”基线：

- 查询级 Direct Scorer：检索前读取当前查询，输出 0–1 查询风险。
- 会话级 Direct Scorer：从第 3 轮开始读取同一会话的滑动窗口、查询风险和检索轨迹，输出 0–1 会话风险。
- 两个 Scorer 均读取攻击模式库 1.4.0，而不是把全部攻击定义硬编码进系统提示词。
- 使用 Mistral-7B-Instruct-v0.2 的本地 Transformers/CUDA 推理，温度为 0。
- 当前只运行 `observe`：记录推荐 L0–L4，但实际始终采用 L0，不改变 RAG 检索上下文。

这里的 Direct Scoring 是“LLM 直接输出风险分数”的含义，不等同于四种攻击中的 Direct RAG-MIA。

## 2. 代码与配置

| 文件 | 作用 |
|---|---|
| `src/miaguard/direct_scorer.py` | 查询级、会话级 LLM Direct Scorer 和配置解析 |
| `src/miaguard/two_stage_direct_experiment.py` | 固定数据划分上的攻击/良性会话构造与指标计算 |
| `scripts/run_two_stage_direct_experiment.py` | 命令行入口 |
| `configs/defense/two_stage_direct_observe.yaml` | Direct Scorer、会话窗口、融合和 L0–L4 配置 |
| `attack_pattern_library/manifest.yaml` | 攻击模式库入口，当前版本 1.4.0 |

模型输出必须包含：

- `risk_score`：0–1 JSON 数字；
- `suspected_attack_types`：可能的攻击模式 ID；
- `evidence_codes`：攻击模式库定义的证据码。

风险类别由代码根据分数确定：小于 0.4 为 `NONE`，0.4–0.69 为 `WEAK`，0.7 及以上为 `STRONG`。模型输出异常时最多重试一次；仍然失败会记录 `fallback_invalid_output` 和 `DIRECT_SCORER_INVALID_OUTPUT`，不会伪装成有效预测。

## 3. 在线可见信息边界

查询检测器只接收 `query` 和 `session_id`。

会话检测器只接收：

- 当前查询；
- 同一 `session_id` 的最近轮次；
- 当前及历史检索文档 ID、相似度；
- 第一阶段历史风险；
- 最小会话轮数配置。

成员/非成员标签、攻击标签、目标文档真值和测试答案不会传入检测器。输出目录进一步将信息分开：

- `risk_events.jsonl`：模拟在线日志，没有 ground truth；
- `evaluation_records.jsonl`：离线评测对齐文件，单独保存 ground truth；
- `detector_metrics.json`：聚合指标；
- `run_manifest.json`：模型、划分、样本 ID 和输入字段；
- `summary.json`：简要结果。

## 4. 运行命令

```powershell
conda activate MIAGuard
python scripts/run_two_stage_direct_experiment.py `
  --config configs/attacks/ag_news_calibrated.yaml `
  --gateway-config configs/defense/two_stage_direct_observe.yaml `
  --split data/two_stage_splits/ag_news_two_stage_v1.json `
  --partition development `
  --source-run-id 20260717-ag-news-four-medium `
  --dataset ag_news `
  --output-run-id 自定义且不重复的运行ID `
  --samples-per-type 1 `
  --ia-turn-count 3 `
  --project-root .
```

`samples-per-type=1` 会构造：

- Direct RAG-MIA、S²-MIA、Masked MIA 各 1 条攻击查询；
- 与上述三种攻击分别对应的困难良性查询各 1 条；
- IA 攻击会话和良性会话各 1 个，每个 3 轮；
- 共 12 个在线事件。

当前阶段只能使用 `development`。不要在完善提示词、模式库和格式解析期间运行 test。validation 应在方法固定后用于阈值校准，test 只用于最终报告。

## 5. 已完成的真实 Smoke

正式验收结果位于：

`data/two_stage_results/20260721-ag-news-two-stage-direct-smoke-v4/ag_news`

环境与输入：

- 数据集：AG News；
- 划分：`ag_news_two_stage_v1 / development`；
- 样本：12 个事件；
- LLM：本地 Mistral-7B-Instruct-v0.2；
- Embedding：all-MiniLM-L6-v2；
- FAISS：`20260717-ag-news-four-medium` 已构建向量库；
- 模式：observe。

| 指标 | v4 结果 |
|---|---:|
| Direct/S²/Masked 查询级 F1 | 1.000 |
| Direct/S²/Masked 查询级良性误报率 | 0.000 |
| IA 第 3 轮会话检出率 | 1.000（1/1） |
| IA 第 3 轮良性误报率 | 0.000（0/1） |
| 全事件融合 F1 | 0.909 |
| 全事件融合 AUROC | 0.889 |
| 全事件融合 AUPRC | 0.917 |
| 结构化输出失败 | 0/12 |
| observe 实际 L0 比例 | 1.000 |
| 查询检测平均延迟 | 4.55 秒 |
| 活跃会话检测平均延迟 | 5.10 秒 |
| 总防御 P95 延迟 | 9.37 秒 |

四种攻击在本次样本中的查询检测率分别为 Direct 1.0、S² 1.0、Masked 1.0、IA 0.667。IA 的单轮指标只用于观察，因为 IA 的正式判断应以完整会话最终轮为准。

## 6. 结果应如何解释

v4 证明以下事项已经成立：

- 本地模型能够在 GPU 上完成查询级和会话级直接评分；
- 攻击模式库可以被两级检测器共同读取；
- JSON 输出、风险融合、L0–L4 推荐和分离日志能够端到端运行；
- 最小样本上能够区分四类攻击与相应困难良性行为；
- observe 模式没有改变实际 RAG 访问行为。

但不能据此声称达到论文水平。Direct/S²/Masked 只有 3 个攻击和 3 个良性样本，IA 最终轮只有 1 个攻击会话和 1 个良性会话；AUROC、F1 等数值方差很大。

## 7. 调试运行与已知问题

- v1：模型经常输出解释文本而不是 JSON，8/12 回退；该结果无效。
- v2：格式已合法，但输出模板中的固定 `0.0` 造成数值锚定，全部低风险；该结果无效。
- v3：移除数值锚定后检测恢复，但历史不足的零会话风险会稀释单轮查询风险。
- v4：会话检测未启用时只使用查询风险，作为本阶段正式 Smoke。

尝试把 `samples-per-type` 增加到 2 时，批量任务长期占满约 24 GiB 显存，且当前运行器只在全部结束后落盘。该 Pilot 被主动终止，没有生成结果目录。扩大样本前应先实现逐事件落盘、运行进度、超时记录和断点续跑；这属于工程可靠性问题，不应通过无限等待掩盖。

## 8. 下一阶段建议

1. 为 Direct Scoring 评测增加逐事件原子落盘、进度输出和断点续跑。
2. 在 development 上扩大到每类 5 个样本，先检查无效输出率和延迟。
3. 冻结提示词和攻击模式库版本后，在 validation 上校准 0.4/0.7 分类阈值及 L0–L4 阈值。
4. 报告至少三次重复运行的均值、标准差和分数一致率。
5. Direct 路线稳定后，再验证本地推理后端是否能提供真实 token log probability，进入 Log Probability Scoring 阶段。

## 9. Mistral 8-bit 加载实验

项目新增了独立 INT8 配置：

`configs/attacks/ag_news_calibrated_int8.yaml`

原来的 `ag_news_calibrated.yaml` 继续保持 BF16 默认行为，历史实验配置没有被覆盖。INT8 使用 `bitsandbytes==0.49.2`、`BitsAndBytesConfig(load_in_8bit=True)` 和 FP16 辅助计算；查询检测、会话检测和 IA 生成共享同一个量化模型实例。

验证量化模型是否正确加载：

```powershell
conda activate MIAGuard
python scripts/verify_int8_model.py `
  --config configs/attacks/ag_news_calibrated_int8.yaml `
  --project-root .
```

已验证 Mistral 中有 224 个 `Linear8bitLt` 层，模型内存 footprint 约 7156.5 MiB。单次短生成时，模型加载后的 GPU 全局占用约 8.8–9.4 GiB。

完整 INT8 Smoke 命令与普通命令相同，只需替换攻击配置：

```powershell
python scripts/run_two_stage_direct_experiment.py `
  --config configs/attacks/ag_news_calibrated_int8.yaml `
  --gateway-config configs/defense/two_stage_direct_observe.yaml `
  --split data/two_stage_splits/ag_news_two_stage_v1.json `
  --partition development `
  --source-run-id 20260717-ag-news-four-medium `
  --dataset ag_news `
  --output-run-id 自定义且不重复的运行ID `
  --samples-per-type 1 `
  --ia-turn-count 3 `
  --project-root .
```

正式 INT8 验证结果位于：

`data/two_stage_results/20260721-ag-news-two-stage-direct-int8-smoke-v2/ag_news`

| 指标 | BF16 v4 | INT8 v2 |
|---|---:|---:|
| 结构化输出失败 | 0/12 | 0/12 |
| 查询级显式攻击 F1 | 1.000 | 1.000 |
| IA 最终轮会话检出率 | 1.000 | 1.000 |
| 融合 F1 | 0.909 | 1.000 |
| 查询检测平均延迟 | 4.55 秒 | 9.38 秒 |
| 会话检测平均延迟 | 5.10 秒 | 9.84 秒 |
| 总防御 P95 延迟 | 9.37 秒 | 19.14 秒 |
| 运行中观测最高显存 | 约 20–24 GiB | 约 16.1 GiB |

检测指标只有每类 1 个样本，不能据此判断 INT8 比 BF16 更准确；量化会造成风险分数变化，需要扩大样本后单独校准。当前可以确认的是：INT8 显著降低显存，但在这台 Windows + RTX A5000 上推理约慢一倍。
