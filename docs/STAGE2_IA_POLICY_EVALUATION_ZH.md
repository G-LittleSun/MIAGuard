# 阶段二：IA 访问动作安全校正评测

## 1. 目标

阶段一使用 `restrict_context` 处理中风险 IA 查询，曾出现防御后 IA Accuracy 高于防御前的情况。阶段二固定 Rule-only 检测器和攻击实现，只改变中风险访问动作，目标是消除这种反向增强。

## 2. 样本隔离

AG News 样本按每个 membership 类别分别切分：

| 用途 | 类内位置 | 数量 |
|---|---|---:|
| S²/Masked 阈值校准 | 1～100 | 100 member + 100 nonmember |
| 校准版阶段一 MVP | 101～110 | 10 + 10 |
| 阶段二 IA 策略验证 | 111～130 | 20 + 20 |
| 阶段二最终留出评测 | 131～140 | 10 + 10 |

程序已经验证阈值校准集、策略验证集和最终留出集交集均为0。

## 3. IA 策略验证

验证运行：

```text
data/defense_policy_results/20260720-ag-news-ia-policy-validation/ag_news/
```

无防御 IA Accuracy 为0.725。四种动作结果：

| 中风险动作 | 防御后 Accuracy | 降幅 | 平均端到端延迟 |
|---|---:|---:|---:|
| `restrict_context` | 0.725 | 0 | 562.5 ms |
| `summarize_context` | 0.650 | 0.075 | 1508.9 ms |
| `no_context_answer` | 0.600 | 0.125 | 423.5 ms |
| `deny_sensitive_answer` | 0.500 | 0.225 | 3.4 ms |

策略选择规则在运行前固定为：

```text
先选择验证集攻击 Accuracy 最低的动作；
若 Accuracy 相同，再选择限制程度较低的动作。
```

因此当前 MVP 选择：

```text
medium → deny_sensitive_answer
high   → deny_sensitive_answer
low    → allow
```

对应配置为 `configs/defense/ia_deny.yaml`。

## 4. 独立留出评测

最终运行：

```text
data/defense_results/20260720-ag-news-defense-stage2-holdout/ag_news/
```

每种攻击使用10个成员和10个非成员，另有40条 benign 查询。

| 攻击 | 防御前 Accuracy | 防御后 Accuracy | 降幅 | 防御前 ROC-AUC | 防御后 ROC-AUC |
|---|---:|---:|---:|---:|---:|
| Direct RAG-MIA | 1.00 | 0.50 | 0.50 | 1.00 | 0.50 |
| S²-MIA | 0.65 | 0.50 | 0.15 | 0.73 | 0.44 |
| Masked MIA | 0.80 | 0.50 | 0.30 | 0.89 | 0.50 |
| IA | 0.80 | 0.40 | 0.40 | 0.80 | 0.40 |
| 宏平均 | 0.8125 | 0.475 | 0.3375 | — | — |

防御检测与正常查询：

```text
attack events: 80
benign events: 40
benign allow rate: 1.0
benign false positive rate: 0.0
actions: 80 deny + 40 allow
schema-valid events: 120 / 120
```

## 5. 阶段二验收

| 验收项 | 结果 |
|---|---|
| IA 防御后 Accuracy 不高于无防御 | 0.40 < 0.80，通过 |
| 正常查询放行率不低于0.95 | 1.0，通过 |
| 策略验证集与最终留出集不重叠 | 交集0，通过 |
| 阈值校准集与最终留出集不重叠 | 交集0，通过 |
| 四攻击和 benign 共用统一入口 | 通过 |
| 完整测试与依赖检查 | 123 passed、1 skipped；pip check通过 |

阶段二的 MVP 目标已经完成：当前固定 IA 攻击不再因 top-1 截短而增强。

## 6. 不能过度解读的部分

1. IA 防御后 ROC-AUC 为0.40，自适应攻击者如果知道防御规则并反转分数，仍可能获得0.60的区分度；
2. 当前 benign 查询比较简单，没有覆盖与 IA 表面相似的合法细粒度问题；
3. `deny_sensitive_answer` 的安全性最好，但对被误判的合法查询效用损失最大；
4. 当前 detector F1 为1.0主要因为规则直接匹配已知攻击模板，不代表能够识别改写攻击；
5. 10+10攻击样本适合MVP验证，不足以支撑论文最终统计结论。

因此，阶段三必须首先增加 IA-like hard negative 和攻击改写，再决定固定拒绝是否仍是最佳中风险动作。`no_context_answer` 是当前更温和的候选策略，后续应在安全性—可用性联合指标下重新比较。
