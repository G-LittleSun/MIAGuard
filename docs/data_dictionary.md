# MIAFence 统一查询数据字典

本数据字典对应任务书第 8 节。当前阶段只定义和校验格式，不生成查询 JSONL。

| 字段 | 类型 | 可空 | 含义 | 示例 |
|---|---|---:|---|---|
| `query_id` | string | 否 | 全局稳定查询 ID | `qry_direct_test_000001` |
| `session_id` | string | 否 | 会话 ID；单轮查询也必须提供 | `ses_direct_test_000001` |
| `turn_id` | integer | 否 | 会话内从 1 开始的轮次 | `1` |
| `split` | enum | 否 | `train`、`validation` 或 `test` | `test` |
| `attack_type` | enum | 否 | `benign`、`direct_ask`、`s2mia`、`mask_based` 或 `ia` | `direct_ask` |
| `attack_variant` | string | 否 | 同一查询类型内的构造变体 | `context_binary` |
| `template_id` | string | 否 | 生成模板的稳定 ID | `direct_test_03` |
| `target_doc_id` | string | 否 | 查询所针对的目标文档 ID | `t2rank_00001234` |
| `membership_label` | integer enum | 否 | 目标文档是否实际属于本地索引成员：0 或 1 | `1` |
| `query` | string | 否 | 将发送给本项目本地受控 RAG 的文本 | `该内容是否存在？` |
| `expected_answer` | string/null | 是 | 可自动评分时的标准答案 | `null` |
| `evidence_text` | string/null | 是 | 支持标准答案的目标文档片段 | `null` |
| `generation_method` | string | 否 | 查询的生成方式 | `template` |
| `generator_model` | string/null | 是 | 使用生成模型时记录模型名 | `null` |
| `seed` | integer | 否 | 生成记录使用的固定种子 | `20260713` |
| `metadata` | object | 否 | 攻击类型特有、但不替代公共字段的结构化信息 | `{}` |

## 标签区别

`attack_type` 描述查询行为类别，`membership_label` 描述目标文档是否真实存在于成员索引。针对非成员文档构造的攻击仍然具有攻击类型，例如 `attack_type=mask_based` 与 `membership_label=0` 可以同时成立。

内部 split 值统一使用 `validation`。后续第 9 节以后生成文件时，对应文件名使用任务书指定的 `val.jsonl`。

