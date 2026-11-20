# IA Query Bank 平衡容量增量修复设计

## 目标

在不删除或修改 `ag_news_queries_v1` 已有查询记录的前提下，为 IA 查询标签不足的文档追加离线生成记录，使每个文档最终至少具有 15 条 `yes` 和 15 条 `no` IA 查询。

## 范围

- 保留现有的 Direct RAG-MIA、S²-MIA、Masked MIA 和 benign 查询，不重建这些攻击类型。
- 保留已有 IA 查询，包括 `ground_truth=unknown` 的记录。
- 仅为 IA 标签计数未达到 15 的一侧生成追加查询。
- 新增的记录写入现有 Query Bank，并记录单独的修复审计日志。

## 数据契约

对每个文档，令现有 IA 标签数为 `yes_count`、`no_count` 和 `unknown_count`。修复数量为：

```text
required_yes = max(0, 15 - yes_count)
required_no  = max(0, 15 - no_count)
```

修复完成后，文档必须满足：

```text
yes_count >= 15
no_count  >= 15
ia_count  >= 30
```

`unknown` 可保留在 Query Bank 中，但不会被 IA 攻击抽样器选取。它不计入 15+15 容量。

## 修复流程

1. 审计 `queries.jsonl`，逐文档计算 IA 的 `yes/no/unknown` 分布。
2. 对每个不满足 15+15 的文档，仅请求缺失标签方向的候选问题。
3. 每条候选经过现有格式、文档绑定性、规范化去重和独立标签验证。
4. 只接受标签恰为该文档缺失方向的记录；`unknown` 和另一方向标签不写入修复结果。
5. 为每篇已修复文档追加唯一 `query_id` 的 IA 记录，并写入 `repair_log.jsonl`。
6. 原子性重写 `queries.jsonl` 和更新 manifest 哈希、总查询数、IA 标签统计与修复元数据。
7. 运行完整 Query Bank 校验及抽样审计。

## 抽样规则

- IA 池资格：文档必须有至少 15 条 `yes` 和 15 条 `no`。
- `ia-turn-count=30`：以固定种子从该文档选择 15 条 `yes` 与 15 条 `no`。
- 小于 30 的轮数：仅从 `yes/no` 池中按固定种子均衡选择；奇数轮随机但可复现地多选一条标签。
- `unknown` 不进入 `selected_query_ids["ia"]`。

## 校验与错误处理

- 构建器新建文档仍生成原有的 30 条 IA 查询；仅修复后 Bank 允许单文档 IA 数量超过 30。
- 验证器保留其他攻击类型固定数量要求，将 IA 校验从“恰好 30”改为“至少 30，且 yes/no 各至少 15”。
- 若候选生成在最大尝试次数内无法补足某一标签，修复过程失败并保留原 Bank，不写入部分结果。
- 修复日志至少记录：文档 ID、原始与最终标签计数、新增 query ID、目标标签、种子、时间和生成配置摘要。

## 成功标准

- 100 个 AG News 文档都满足 IA `yes >= 15` 且 `no >= 15`。
- Query Bank 完整性校验通过，且查询总数、SHA256 和 IA 标签统计与 manifest 一致。
- 50+50 的候选文档能够在 `ia-turn-count=30` 下完成离线、平衡抽样。
- 已有 10+10 和 32+32 实验目录不修改；其已有选择 manifest 继续指向修复前的查询哈希。
- 完整测试套件通过。
