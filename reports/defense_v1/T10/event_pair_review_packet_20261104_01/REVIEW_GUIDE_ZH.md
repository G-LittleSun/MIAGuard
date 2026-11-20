# D-dev 试点文章事件关联：独立模型预审交接

## 目标和边界

判断这 31 篇 D-dev 试点材料中，哪些文章可能描述同一事件或存在影响统计独立性的关联。清单列出全部 465 对，而非仅审查相似度高的组合。只阅读本包，不读取成员标签、攻击结果、A-cal/V/T 或外部资料；依据不足应选 `uncertain`。审核属于模型预审，不是真人审核、人工 gold 或防御实验。

## 输入与输出

- 输入：同目录 `manifest.json`、`sources.jsonl`、`pairs.jsonl`。先重算输入文件摘要，确认与 manifest 一致，确保 31 篇、465 对及编号唯一。
- 输出到新目录 `reports/defense_v1/T10/external_review/event_pairs_<模型标识>_<日期>_01/`；不得覆盖本包、原材料或其他审核结果。
- 输出 `review_manifest.json`、`pair_reviews.jsonl`、`review_summary.md`。记录实际可获得的模型标识及来源，不编造不可变快照。记录输入和输出 SHA256、开始结束时间、状态、每类计数、未审核 ID、限制；标记 `reviewer_kind=llm_agent`、`human_reviewed=false`、`formal_effect_eligible=false`。

## 逐对判断

每个 `pair_id` 恰好一行，按 `pairs.jsonl` 顺序输出以下字段：

```json
{"pair_id":"pair_...","left_doc_id":"...","right_doc_id":"...","relation":"same_event","reason":"以两个来源中的具体事实说明","left_evidence":"原文短片段","right_evidence":"原文短片段","confidence":"high"}
```

`relation` 仅可选：

- `same_event`：两篇都提供足以把报道指向同一具体事件的证据，例如同一行为、参与方与特定时间线；仅共享人物或关键词不足。
- `related_event`：不同事件但有明确的事件链、直接后续、同一明确争议或紧密相连的具体事实；写出依据和可能的统计依赖。
- `shared_entity_or_topic`：只有共同人物、机构、地点或一般主题，无法确认同一事件或直接事件链；列明不能确认的原因。
- `unrelated`：两篇可识别内容之间未见具体事件、实体或主题关联；这只是基于提供的文本，不证明语义独立。
- `uncertain`：片段过短、截断、时间或事件边界不明，无法有依据地判断；说明缺什么。

`confidence` 为 `high`、`medium` 或 `low`。每项理由应指向双方文本，`left_evidence` / `right_evidence` 应从各自原文逐字摘取简短片段，不补写截断内容；不能从标题推测正文没有的先后或因果。若正文无法提供证据，可用空字符串并在理由注明。不得将共同主题自动等同同一事件，也不得用外部常识填充。

## 完成及自检

可以分批处理并持续保存；若中断，manifest 标 `partial` 并列出全部未审核 ID，不能谎称完成。结束时核对 465 对一一对应、顺序一致、不重复、JSONL 每行可解析、左右 ID 与输入一致、枚举合法、证据属于对应来源，统计与文件一致并计算摘要。摘要中列出 `same_event`、`related_event` 和 `uncertain` 的所有编号、最关键证据及需要真人裁决的歧义；说明关联不具传递性，不能自动将所有共享实体的文章合成同一事件。

最终请返回输出目录、真实模型标识来源、已审数量与各类计数、输入输出摘要、主要争议和限制。不要修改输入或标记 `human_reviewed`。
