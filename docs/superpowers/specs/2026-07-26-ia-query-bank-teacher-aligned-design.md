# IA Query Bank 教师流程对齐设计

## 1. 背景

当前 Query Bank 要求每个目标文档生成并接受 15 条 `yes` 和 15 条 `no`
IA 问题，同时使用 embedding 相似度阈值 `0.92` 删除语义近似问题。
AG News 文档通常只有两三句话，本地 Mistral 在重复生成时会围绕少量事实产生相似
问题。经过答案复核、文本去重和语义去重后，每个文档通常只能保留约 5 至 9 条问题，
导致构建器在 20 轮后失败。

老师项目的正式流程要求每个文档生成 30 个 IA 问题，但不要求固定的
`15 yes + 15 no` 分布，也没有语义 embedding 去重约束。Query Bank 应恢复这一核心
语义，同时继续提供离线冻结、验证和断点续建能力。

## 2. 目标

- 每个目标文档保存恰好 30 条 IA 查询。
- IA 标准答案允许 `yes`、`no` 和 `unknown`。
- 标准答案由独立的第二次模型调用根据源文档判定，而不是由问题生成调用自报。
- 只拒绝空问题、模糊指代问题和规范化文本完全重复的问题。
- 不使用 embedding 语义相似度作为 IA 候选的硬淘汰条件。
- 保持每文档总查询数为 50：
  `Direct 5 + S² 5 + Masked 5 + IA 30 + benign 5`。
- 保持现有 IA 最终查询格式和老师迁移版评分逻辑不变。
- 在生成日志和 Query Bank 统计中公开实际的 `yes/no/unknown` 分布。

## 3. 非目标

- 不修改 Direct RAG-MIA、S²-MIA 或 Masked MIA 的攻击算法。
- 不要求 30 条问题对应 30 个完全不同的事实。
- 不修改 Target RAG 的检索、回答或 IA 得分计算方式。
- 本次不引入文档内部的阶段级缓存；仍以一个文档的 50 条记录为原子分片。

## 4. 配置与数据契约

Query Bank 配置的 IA 字段调整为：

```yaml
queries:
  paraphrases_per_attack: 4
  ia_questions_per_document: 30
  ia_batch_size: 6
  ia_max_attempts: 20
```

删除以下构建字段：

```yaml
ia_yes
ia_no
semantic_duplicate_threshold
```

`QueryBankBuildConfig` 使用 `ia_questions_per_document` 表示目标总数。
该值当前必须为 30。记录中的
`payload.ground_truth` 允许 `yes`、`no`、`unknown`。

Query Bank manifest 的构建期字段由固定的 `ia_balance` 改为：

```json
{
  "ia_questions_per_document": 30
}
```

构建完成后增加整个 Bank 的实际答案计数：

```json
{
  "ia_answer_counts": {
    "yes": 1234,
    "no": 987,
    "unknown": 779
  }
}
```

计数中可以缺少数量为零的类别。Query Bank schema version 升级为 `1.1.0`。

## 5. IA 离线生成流程

每个文档维护：

- 一个文档级 `summary`；
- 按接受顺序保存的问题列表；
- 规范化问题文本集合，用于精确去重。

每轮流程如下：

1. 计算距离 30 条还缺少的问题数，并按 `ia_batch_size` 决定本轮请求数量。
2. 提示本地模型根据源文档生成指定数量的问题，只返回 `summary` 和问题字符串。
3. 提示中附带已经接受的问题，要求不要重复。
4. 删除空问题、包含“本文/这段文字”等模糊指代的问题，以及规范化文本完全重复的
   问题。
5. 对剩余候选进行独立答案判定，只允许 `yes`、`no`、`unknown`。
6. 将问题、独立标准答案和文档 summary 加入接受集合，直到达到 30 条。

问题生成调用不再提供或声明 ground truth，因此生成模型不能通过自报标签绕过独立
复核。答案判定返回无效值或数量不足时，只接受具有合法对应答案的前缀候选，其余问题
在后续轮次补齐。

每轮输出一条紧凑诊断日志，包括：

```text
[query-bank][ia] attempt=3 requested=6 generated=6 invalid=0
duplicate=2 unverified=0 accepted=4 total=16/30
answers=yes:10,no:4,unknown:2
```

达到 `ia_max_attempts` 后仍不足 30 条时，错误中报告最终接受数量和答案分布。

## 6. 校验与检查

单记录校验：

- `payload.question` 和 `payload.summary` 非空；
- `payload.ground_truth` 属于 `yes/no/unknown`。

单文档校验：

- IA 记录恰好 30 条；
- 规范化问题文本没有完全重复；
- 不要求固定答案比例，也不要求三个答案类别都出现。

Bank 检查输出：

- 全局 IA `yes/no/unknown` 数量；
- 每个文档仍由内部校验保证 30 条；
- manifest 中的 `ia_answer_counts` 必须与冻结记录统计一致。

## 7. 错误处理与恢复

- JSON 解析继续使用现有限次重试。
- 单轮输出数量不足不会立即使文档失败，后续轮次继续补齐。
- 单个文档只有在 30 条 IA 记录及其他 20 条记录全部通过校验后才写入 `.work`
  分片。
- 已成功写入且文档哈希匹配的分片在重新执行时继续复用。
- 当前 smoke 构建留下的失效锁需在第一次重跑时通过 `--force-unlock` 清理。

## 8. 测试与验收

自动化测试至少覆盖：

1. 配置接受 `ia_questions_per_document: 30`，拒绝非 30 的值。
2. 配置不再要求 `ia_yes`、`ia_no` 和 `semantic_duplicate_threshold`。
3. IA ground truth 接受 `yes/no/unknown`，拒绝其他值。
4. 生成器接受任意实际答案分布，只要总数为 30。
5. 规范化文本完全重复的问题仍被拒绝或跳过。
6. 后续生成提示词包含已接受问题。
7. IA 生成流程不调用 embedding。
8. validator 不再检查 15/15，仍严格检查 30 条和文本唯一性。
9. manifest 和 inspect 输出实际答案计数。
10. 现有 Query Bank、攻击和两阶段实验测试无回归。

运行顺序：

1. 执行 Query Bank 定向测试；
2. 执行完整测试套件；
3. 使用 `ag_news_smoke.yaml` 和 `--force-unlock` 构建两个文档；
4. 运行 validate 和 inspect；
5. 仅在 smoke 完整通过后启动 `ag_news_v1.yaml` 正式构建。

## 9. 成功标准

- smoke Bank 状态为 `complete`。
- smoke 中两个文档各有 30 条 IA、总计各 50 条查询。
- `yes/no/unknown` 的实际分布可检查但不触发失败。
- validate 返回 `status=valid`。
- 完整测试套件通过。
- 正式构建能够按文档写入分片并在中断后复用已完成分片。
