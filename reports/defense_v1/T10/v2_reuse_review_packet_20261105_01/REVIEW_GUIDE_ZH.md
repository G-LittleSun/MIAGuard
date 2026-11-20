# v2 train 复用缺口：独立模型预审交接

## 范围与身份

只审本包：`sources.jsonl` 60 篇原文、`ia_items.jsonl` 206 条开放式 IA 疑点、`masked_items.jsonl` 60 个来源级遮蔽方案（对应 300 条提问）。共 266 个审核单元。先核对 manifest 摘要、数量、ID 与来源；不读成员标签、其他数据分区、攻击效果或外部资料，不修改输入。

输出至新目录 `reports/defense_v1/T10/external_review/v2_reuse_<实际模型标识>_<日期>_01/`，包含 `review_manifest.json`、`ia_review.jsonl`、`masked_review.jsonl`、`review_summary.md`。记录真实可获得的模型标识和来源，未暴露供应商快照时如实说明。`reviewer_kind=llm_agent`、`human_reviewed=false`、`formal_effect_eligible=false`。开始/结束时间、输入/输出 SHA256、逐类判定数量、未审 ID、限制必须完整。

此包未覆盖其余 2,169 条 IA、Direct/S² 的语义审核或 1,304 条正常题的答案证据。完成本包不代表整个 v2 复用验收完成，更不是防御效果或真人 gold。

## IA：206 条，每条一行且按原顺序

字段严格为：

```json
{"query_id":"原ID","doc_id":"原ID","decision":"rewrite","reason":"说明问题与源文依据","evidence_quotes":["该源文逐字短引"],"corrected_query":"可执行的完整英文提问","corrected_question":"新的二分类/三分类问题","corrected_ground_truth":"yes","notes":"局限或风险"}
```

- `decision` 可选 `accept/rewrite/reject/uncertain`。
- 核对原问句是否与 Yes/No/Unknown 回答一致。不要只把 What/How 换成 Are/Is；须形成原文可判定的具体陈述，并避免把答案直接写在前置 summary 中。完整查询应清楚要求 Yes/No/Unknown。
- 原文支持陈述时 `yes`；原文明确矛盾时 `no`；材料不足时 `unknown`。仅“没有写”不能推成 `no`，不能依靠外部常识或补完截断。`corrected_ground_truth` 是对源文陈述的参考判定，绝不是成员标签。
- 改题后重新判定 ground truth，不盲目沿用旧建议。保留与原文相关的具体核对目标，不把整篇原文复制到问题中。
- `accept` 的 `corrected_query/question/ground_truth` 必须逐字等于原项；`rewrite` 三项均非空并符合契约；`reject/uncertain` 三项均为 null，并写清原因。
- `evidence_quotes` 只取同一 `doc_id` 原文。Unknown 或排除可以为空，但在 reason/notes 说明材料缺口。对“无需检索也可能答对”、顺从偏差及推断不唯一保留说明，不据此伪造效果结论。

## Masked：60 个来源方案，每项一行且按原顺序

字段严格为：

```json
{"review_id":"原ID","doc_id":"原ID","decision":"rewrite","reason":"具体修订理由","corrected_masked_text":"完整遮蔽原文","corrected_answers":["原词"],"corrected_queries":[{"query_id":"原查询ID","query":"完整英文提问"}],"notes":"局限"}
```

- 保持输入的**多编号遮蔽机制和遮蔽数量**（`[Mask_1]` … `[Mask_n]`），保留原文的大小写、标点、空白和转义文本。不要改成单个 `[MASK]` 或重写源文章。
- 逐个编号替换 `corrected_answers` 后必须逐字还原同一来源原文；编号完整、不重复，答案顺序正确。按词边界、不区分大小写检查剩余正文中不再出现任一缺词；必要时移位或换词，同步全部五种提问。
- 优先按原方法选择正文中较难猜测的非数字词；**攻击者知道目标全文，因此不要求仅凭掩码上下文就能唯一推导答案**。不能套用正常问答的“无需检索也可唯一回答”要求，也不能凭主观难度宣称攻击有效。语义同义词与精确恢复的差异列入 notes，不改主评分标准。
- 全部五条完整提问使用相同的新遮蔽原文，并明确要求仅输出包含 `answers` 数组的 JSON，按编号排序；避免在指令或示例中写出缺词。原文和答案都不变时也须为缺失的格式要求生成完整修订提问。
- `accept` 的遮蔽文本/答案/查询列表必须逐字等于输入；`rewrite` 三项均非空且给出五个原 query_id 对应的完整问题；`reject/uncertain` 三项均为 null，并说明不能构成合理方案的原因。
- 重复答案值、标题依赖、截断等写明原因；重复答案不是自动排除条件。若无法保持数量且消除泄漏，应标 uncertain/reject，不减少 mask 数量凑合。

## 持续保存和自检

建议按来源分批，每批结束写入文件并更新 manifest 的已完成/未审 ID。中断必须标 partial，禁止把未审项目自动标 accept。完成时两份 JSONL 分别恰好 206/60 行，UTF-8 无 BOM、逐行可解析，ID 与输入顺序一一对应，无重复、无遗漏，字段/枚举和 accept/rewrite/reject/uncertain 契约正确。检查 IA 引文来源和 Masked 还原/编号/无泄漏/五查询一致性。

最终返回结果目录、模型标识来源、两类完成数及判定数、输入输出摘要、主要缺陷和剩余争议。所有结论都是单模型预审建议，不得记录为人工审核。
