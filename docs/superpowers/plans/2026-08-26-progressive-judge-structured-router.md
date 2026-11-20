# Progressive Judge 结构化 Router 实施计划

1. 将 `lm-format-enforcer` 固定为项目模型依赖，并为 `ModelClient` 增加可选 JSON Schema 约束。
2. 将筛选阶段拆成 Gate 与 Candidate 两个提示、解析器和 schema；仅在 Gate 要求复核时调用 Candidate。
3. 补充 Router 的攻击必要条件与良性边界；更新提示版本和配置。
4. 先写覆盖结构 schema、两阶段调用和良性跳过路径的测试，再实现代码。
5. 运行相关测试、全量测试和此前 Windows 良性会话的本地 smoke；通过后再重启完整 5 文档开发集。
