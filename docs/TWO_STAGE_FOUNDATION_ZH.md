# MIAGuard 两阶段风险框架：基础阶段说明

## 1. 当前结论

本阶段已经完成两阶段风险框架的“可运行骨架”，包括固定实验划分、统一风险对象、会话窗口、风险融合、L0–L4 访问策略，以及 `disabled / observe / enforce` 三种运行模式。

当前检测器仍是 `NoOpRiskDetector`，始终输出零风险。因此本阶段只证明架构接入正确、实验数据不泄漏、关闭防御时不改变原 RAG 行为；不能据此宣称已经获得有效的攻击检测率或防御效果。

## 2. 在线处理流程

```text
用户查询
  -> 查询级检测器（检索前）
  -> FAISS 检索
  -> 会话级检测器（只读取在线可见信息）
  -> 查询风险与会话风险融合
  -> L0-L4 策略映射
  -> RAG 上下文与回答
```

查询检测先于向量检索执行。会话检测可读取当前查询、同一会话最近若干轮查询、检索文档 ID 和相似度分数，但不会读取成员/非成员真值、攻击标签或测试集答案。真值只能在离线评测阶段与日志预测结果对齐。

## 3. 三种运行模式

| 模式 | 是否计算风险 | 是否保存会话窗口 | 是否真正执行限制 |
|---|---:|---:|---:|
| `disabled` | 否 | 否 | 否，固定 L0 |
| `observe` | 是 | 是 | 否；记录推荐等级，但实际固定 L0 |
| `enforce` | 是 | 是 | 是；执行推荐的 L0–L4 策略 |

开发新检测方法时先使用 `observe`。只有在验证集上完成阈值选择、误报检查和消融实验后，才应进入 `enforce`。目前仓库只提供 `disabled` 和 `observe` 配置，避免尚未验证的策略被误开启。

## 4. 风险与访问等级

查询级和会话级检测器统一返回 `RiskResult`：风险分数、风险类别（`NONE / WEAK / STRONG`）、方法名、攻击类型、证据、状态和延迟。融合器输出总风险分数及融合依据。

默认融合使用动态窗口覆盖率：会话历史尚短时降低会话风险权重；窗口逐渐填满后再恢复配置权重。若查询风险或会话风险超过各自的关键阈值，则保留该高风险信号，避免加权平均把它稀释掉。

| 等级 | 默认风险区间 | 推荐动作 |
|---|---|---|
| L0 | `< 0.20` | 完整访问，正常回答 |
| L1 | `0.20–0.39` | 仅审计记录 |
| L2 | `0.40–0.64` | 减少 Top-K，限制上下文细节 |
| L3 | `0.65–0.84` | 清洗/摘要上下文，启用限速 |
| L4 | `>= 0.85` | 拒绝敏感请求，完整审计 |

上述阈值目前只是策略初值，后续必须只在验证集上校准；测试集不得参与选阈值。

## 5. 固定实验划分

划分单位是目标文档，同一文档不会跨 development、validation、test 出现。当前固定文件为：

- 规格：`configs/data_splits/ag_news_two_stage_v1.yaml`
- 固定 ID 清单：`data/two_stage_splits/ag_news_two_stage_v1.json`
- JSON Schema：`schemas/two_stage_split.schema.json`

| 分区 | member | nonmember | 用途 |
|---|---:|---:|---|
| development | 300 | 300 | 编码、提示词迭代、调试 |
| validation | 100 | 100 | 阈值选择、策略选择、模型选择 |
| test | 100 | 100 | 最终一次性报告，不参与开发决策 |

已有实验使用过每类至少前 218 条数据，因此保守地将每类前 300 条全部划入 development。不要重新生成或编辑固定 ID 清单；需要新版本时应创建新的 `split_id` 和输出文件。

如确实需要从规格重新生成，可执行：

```powershell
conda activate MIAGuard
python scripts/freeze_two_stage_split.py `
  --spec configs/data_splits/ag_news_two_stage_v1.yaml `
  --output data/two_stage_splits/ag_news_two_stage_v1.json `
  --project-root .
```

## 6. 主要代码与配置

| 文件 | 作用 |
|---|---|
| `src/miaguard/risk_types.py` | 风险结果、融合结果、策略结果、会话轮次类型 |
| `src/miaguard/session_store.py` | 按 `session_id` 隔离的内存滑动窗口和超时清理 |
| `src/miaguard/risk_aggregator.py` | 查询/会话风险融合与关键风险保护 |
| `src/miaguard/access_policy.py` | 总风险到 L0–L4 的映射 |
| `src/miaguard/two_stage_gateway.py` | 两阶段编排、三种模式和结构化事件构造 |
| `src/miaguard/defense.py` | 将查询级检测接到检索前、会话级检测接到检索后 |
| `configs/defense/two_stage_disabled.yaml` | 完全关闭、防御零影响配置 |
| `configs/defense/two_stage_observe.yaml` | 只记录推荐决策、不影响回答配置 |
| `schemas/two_stage_risk_event.schema.json` | 两阶段在线日志事件契约 |

结构化在线事件包含查询风险、会话风险、融合风险、推荐策略和实际策略。事件构造接口不接受 `membership_label`、`attack_label`、`intent_label` 或目标真值，从接口层降低在线标签泄漏风险。

## 7. 验收与复现

### 7.1 关闭模式等价性

下面的命令使用真实 AG News FAISS 向量库，对比原始检索和两阶段网关关闭后的结果：

```powershell
conda activate MIAGuard
python scripts/verify_two_stage_disabled.py `
  --config configs/attacks/ag_news_calibrated.yaml `
  --gateway-config configs/defense/two_stage_disabled.yaml `
  --source-run-id 20260717-ag-news-four-medium `
  --dataset ag_news `
  --output reports/two_stage_disabled_verification.json `
  --project-root .
```

验收条件：文档 ID、检索分数、上下文完全一致；实际动作是 `allow`；等级是 L0；不会留下会话状态。已生成的验证报告位于 `reports/two_stage_disabled_verification.json`，当前状态为 `passed`。

### 7.2 自动化测试

```powershell
conda activate MIAGuard
python -m pytest -p no:cacheprovider tests/test_session_store.py tests/test_risk_aggregator.py tests/test_access_policy.py tests/test_two_stage_gateway.py tests/test_two_stage_splits.py tests/test_defense.py -q
python -m pytest -p no:cacheprovider -q
python -m pip check
```

测试覆盖会话顺序、窗口上限、会话隔离、超时清理、融合边界、关键风险不被稀释、L0–L4 映射、三种模式、固定划分互斥、Schema 校验和在线事件不接收真值标签。

## 8. 下一阶段

查询级与会话级 LLM Direct Scoring 已经在 `observe` 模式完成最小验证，详见 `docs/TWO_STAGE_DIRECT_SCORING_ZH.md`。后续应按以下顺序继续：

1. 为批量评测增加增量落盘、运行进度和断点续跑。
2. 继续仅使用 development 扩大 Direct Scoring 样本。
3. 方法冻结后使用 validation 校准阈值。
4. 同时报告攻击检出率、良性误报率、风险分数分布、平均/P95 延迟和 L0–L4 推荐分布。
5. 保持实际访问等级为 L0，确认检测质量后再讨论 `enforce`。

随后再逐步加入第二阶段候选召回、LLM-as-Judge 和攻击模式库，而不是一次性把复杂模型接入控制链路。
