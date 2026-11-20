# Progressive Judge 闭集证据码定向修复设计

## 1. 背景与问题

在五文档开发级验证中，Qwen2.5-7B-Instruct 在 Masked MIA 的详细核验阶段输出了
`MENTIONS_CONTEXT_OR_EVIDENCE`。该字符串不属于 Masked MIA 模式的闭集证据码，解析器
正确拒绝；现有的一次通用格式重试仍输出非法码，导致整批评分在第 24 个会话停止。

这不是 CUDA、模型加载或查询库问题。闭集证据码仍是可解释性和可审计性的必要约束，不能
通过允许任意大写代码绕过。

## 2. 目标与非目标

目标：当详细核验输出含有未知 `supporting_evidence_codes` 或
`counter_evidence_codes` 时，给模型一次面向该字段的定向修复机会，使其仅使用已加载模式
中列出的证据码，或移除不合法的码并同步修正 verdict。

非目标：

- 不向 Masked MIA 模式增加 `MENTIONS_CONTEXT_OR_EVIDENCE`；
- 不放宽解析器的闭集验证；
- 不修改冻结 Query Bank、会话规划或数据划分；
- 不把旧提示版本的 23 个已完成会话与新结果混用。

## 3. 方案

保留 `_code_tuple` 对支持证据和反证据的严格闭集校验。在 `_json_stage` 生成重试提示时，
新增一段字段级修复协议：

1. 如果前一次错误指出未知 evidence code，只能在原始详细提示的
   `allowed_reason_codes_json` 中选择替代码，或删除该码；
2. 禁止把 Router 的观察码或新造的描述码写入 supporting/counter evidence 字段；
3. 若删除支持码导致 `POSSIBLE` 不再满足条件，必须将 verdict 与证据同步调整；
4. 保持其它已通过校验的 assessment 不变。

该协议只影响重试提示，原始详细提示已经包含每个候选攻击的合法码清单。为保证运行身份
隔离，配置中的 `prompt_version` 增加 `evidence_code_targeted_repair` 后缀。

## 4. 测试与运行

- 单元测试：模拟第一次详细核验返回未知证据码、第二次返回合法修正 JSON；断言第二次提示
  明确禁止新造 evidence code，并保留闭集解析。
- 回归测试：现有 Progressive Judge 测试文件必须全部通过。
- 模型冒烟：只运行此前失败的 Masked MIA 会话，确认会生成有效 shard。
- 完整开发验证：以新输出目录重新运行同样 5 个文档、65 个会话、318 条查询；旧目录仅保留
  为中止版本的诊断记录。

## 5. 成功标准

1. 未知证据码仍被解析器拒绝，不能静默进入结果；
2. 定向修复提示具有明确、可测试的闭集约束；
3. 失败的 Masked MIA 会话可在新版本下完成；
4. 完整运行有独立日志、可断点续跑，且最终记录只包含同一新评分身份。
