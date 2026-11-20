# Progressive Judge Verifier Contract 修复设计

## 问题

完整开发集在 S2-MIA 的 Verifier 阶段停止。模型输出了“必要条件未满足、没有良性排除、缺失条件列表为空”的组合；该组合语义自相矛盾，解析器正确拒绝了它。现有自由 JSON 输出和一次性多候选核验没有在生成时阻止这一组合。

## 已确认的方案

1. 每个 Router 候选攻击类型单独调用一次 Verifier；最多两个候选，因此最多增加一次 Verifier 调用。
2. 每个攻击类型在攻击卡中声明固定的 `missing_condition_codes` 词典。模型只能从当前攻击类型的词典中选择缺失条件代码，不能临时发明代码。
3. 每次单候选 Verifier 使用 JSON Schema 受约束生成。模型以字符串 `assessment_state` 表达 verdict、必要条件状态和良性排除状态，Schema 再以互斥分支编码既有协议：
   - 必要条件满足时，缺失条件数组必须为空；
   - 必要条件不满足且没有良性排除时，缺失条件数组至少一个；
   - 有良性排除时，反证据数组至少一个；
   - `LIKELY` 只能处于“必要条件满足且无排除”分支；
   - `POSSIBLE` 必须有支持证据且无排除；
   - `UNLIKELY` 必须有良性排除或缺失条件。
4. 程序继续只校验模型选择的字段，不自动替模型补缺失代码或改变 verdict。

## 数据流

```
Router Candidate [A, B]
       |
       +--> Verifier(A, A 的攻击卡、A 的证据与缺失代码词典) --+
       |                                                       |
       +--> Verifier(B, B 的攻击卡、B 的证据与缺失代码词典) --+--> EvidencePacket
                                                                    |
                                                                    v
                                                             Rubric / Logprob
```

单候选 Verifier 的返回对象不再需要顶层 `assessments` 数组，也不直接输出布尔字段；程序只将模型明确选择的字符串状态还原为原有 verdict/布尔字段。内部转换后仍合成为原有 `EvidencePacket`，所以 Rubric、Logprob 和基准输出格式无需改变。

## 攻击卡字段

每张攻击卡新增 `# Missing condition codes`，每条代码对应一个确定的未满足必要条件。四类分别覆盖：

- Direct RAG-MIA：具体文本、私有 Context/检索存在性检查、会泄露存在性的回答请求；
- S2-MIA：源文本式前缀、基于 Context/证据恢复已有内容、精确或源忠实的续写请求；
- Masked MIA：掩码源文本、精确恢复请求、私有 Context/证据基础；
- IA：足够轮数的受约束探测、重复 Top-1、多个事实维度，或显式索引/成员测试目标。

这些代码是 verifier 专用的缺失条件代码，和支持/反证据 reason code 分离。

## 本地约束库兼容性

当前 `lm-format-enforcer` 不支持布尔 `const`，且其 `oneOf` 分支不会递归合并数组属性。因此 Verifier schema 使用字符串状态而非布尔常量，并在每个数组约束分支中重复完整的 `type`、`items` 和 `uniqueItems` 定义。这个写法保持同一语义约束，同时能在本地 Transformers 后端稳定执行。

## 错误处理与可观测性

仍保留一次格式修复重试。若约束生成或解析仍失败，异常信息必须包含当前候选攻击类型；基准脚本应在运行日志中写入该会话键和查询 ID，便于定位，不写入离线真值以外的 Judge 输入。

## 验收标准

- schema 拒绝本次失败的 `required_conditions_met=false`、`exclusion_applies=false`、空缺失条件数组。
- schema 接受合法 S2-MIA 的 `POSSIBLE` 与 `UNLIKELY` 分支。
- 单候选调用能合成多个候选的 `EvidencePacket`，并保持候选顺序。
- 使用实际失败的 S2 会话 smoke 不再停止。
- 全量测试通过；新评分版本在独立输出目录完整重跑，不与 519 个旧版部分结果混合。
