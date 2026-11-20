# Rubric 与二分类 Logprob 对等测试设计

## 目标

在不重新调用 Judge 模型的前提下，使用已有训练、验证和测试记录，为 `rubric`（LLM 直接评分）补齐与 `logprob`（二分类攻击概率）相同的冻结融合评估，并输出可并列的最终测试指标。

## 方案

冻结融合器显式接收评分头名称。它只从对应 `head` 的 x1/x2 可用记录拟合 L2 logistic 模型，并把该名称写入冻结产物。评估时从冻结产物读取评分头，只接受同一评分头的记录。默认评分头保持 `logprob`，因此既有调用和既有产物不变。

训练集上的既有阈值选择文件包含 `rubric` 和 `logprob` 两个头、同一个 `logistic_l2` 模型的阈值。本次为 `rubric` 生成独立冻结模型，随后在已保存的 validation/test Judge 记录上离线评估。不会搜索新阈值，也不会访问模型或修改 Judge 记录。

## 验收条件

- `freeze_logistic_l2(..., head="rubric")` 产物的 `head` 为 `rubric`，且行数来自 rubric 记录。
- rubric 冻结产物可在 validation 与 test 上评估。
- 评分头不匹配时，评估器明确拒绝。
- 既有未指定 `head` 的 logprob 测试继续通过。
- 最终对比表中两个方案均来自相同的 20 个 test 文档、可用 x1+x2 的记录、训练锁定的模型和阈值。
