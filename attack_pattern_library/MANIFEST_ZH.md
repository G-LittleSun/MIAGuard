# 攻击模式库清单（`manifest.yaml` 中文译本）

> 本文件是 [`manifest.yaml`](manifest.yaml) 的中文说明译本，仅供阅读和汇报使用；运行时仍读取英文原始清单。

## 顶层字段

| 字段 | 当前值 | 中文含义 |
|---|---|---|
| `schema_version` | `1` | 清单数据结构版本。 |
| `library.name` | `MIAGuard Attack Pattern Library` | 攻击模式库名称。 |
| `library.version` | `1.5.0` | 当前模式库整体版本。 |
| `library.judge_protocol` | `JUDGE_PROTOCOL.md` | 所有判定器共同遵循的安全协议文件。 |

## 已登记模式

| ID | 名称 | 版本 | 是否启用 | 必需上下文 | 可选上下文 | 中文概述 |
|---|---|---:|---|---|---|---|
| `direct_rag_mia` | Direct RAG-MIA | `1.1.0` | 是 | `current_query` | `retrieved_snippets`、`retrieval_history` | 识别试图判断某个特定片段是否存在于、被索引于或被私有 RAG 语料支持的请求。 |
| `s2_mia` | S²-MIA | `1.1.0` | 是 | `current_query` | `retrieved_snippets` | 识别要求恢复已有来源文本后续内容的请求，而不是正常的创意续写。 |
| `masked_mia` | Masked MIA | `1.1.0` | 是 | `current_query` | `retrieved_snippets` | 识别要求从已有来源文本中恢复被遮盖的准确词语的请求，而不是普通填空题。 |
| `ia` | Information Association Attack | `1.3.0` | 是 | `current_query`、`recent_turns`、`retrieval_history`、`session_statistics` | `retrieved_snippets` | 识别为推断目标文档是否被索引而进行的连续事实探测；单次普通事实问题不是充分证据。 |

## 字段解释

- `id`：供程序和配置引用的稳定标识，不随中文翻译变化。
- `version`：该攻击模式自身的版本号。更新其判断标准或示例后应递增。
- `entrypoint`：该模式的详细说明文档，例如 `patterns/direct_rag_mia/PATTERN.md`。
- `required_context`：判定该攻击最少需要的输入信息。
- `optional_context`：可用于增强判断、但不是每次都必须存在的信息。
- `enabled`：是否在当前模式库版本中启用该攻击定义。

## 对应关系

```text
manifest.yaml
  ├─ JUDGE_PROTOCOL.md：所有模式共用的判定边界
  └─ patterns/
       ├─ direct_rag_mia/PATTERN.md
       ├─ s2_mia/PATTERN.md
       ├─ masked_mia/PATTERN.md
       └─ ia/PATTERN.md
```
