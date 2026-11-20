# T10-C 试点独立内容审核交接

## 目的与身份

审核 D-dev 正常问题的自然度、事实支撑和会话信息递进，为选择会话轮数提供依据。这里的模型预审是开发阶段意见，**不是人工 gold，也不是防御效果评估**。如为模型 agent，记录实际可获得的模型标识及来源；无法取得供应商完整快照时如实说明，不编造。不要读取攻击成员标签、A-cal/V/T 效果，不运行防御实验。

先读 [阶段记录](DECISION_ZH.md)、[pilot_manifest.json](pilot_manifest.json) 和 [validation.json](validation.json)，重新计算清单中各输入的 SHA256；不一致时停止并说明。只使用以下材料中的同一来源原文核对事实：

- 原会话与旧五轮：[session_inventory.jsonl](session_inventory.jsonl)、[source_evidence.jsonl](source_evidence.jsonl)、[baseline_review.jsonl](baseline_review.jsonl)。
- 同源两轮/三轮草稿：[normal_variants.jsonl](normal_variants.jsonl)、[session_review.jsonl](session_review.jsonl)。
- 扩展组：[expanded_source_selection.jsonl](expanded_source_selection.jsonl)、[expanded_source_evidence.jsonl](expanded_source_evidence.jsonl)、[expanded_variants.jsonl](expanded_variants.jsonl)、[expanded_review.jsonl](expanded_review.jsonl)。

问题、答案和证据 ID 放在同一个审核文件中，仅供审核；不能把整个 JSON 直接当在线请求发送给实验服务。

## 审核对象与规则

1. **54 个有内容的版本**：原文组 14 个两轮、12 个三轮；扩展组 14 个两轮、14 个三轮。将同来源的 2/3 轮按配对关系比较，逐轮指出带来了什么新信息、是否能从当前问句及历史理解，以及答案每项事实是否有原文支持。
2. **2 个排除的三轮版本**：判断原文是否真的不足以形成不重复的第三问；如能提出自然且有依据的新问，提供完整问题、答案与证据，不要为了补齐数量勉强设计。
3. **14 个原五轮参考会话**：对照原文和整段会话，独立判断本次自检提出的重复、截断和双篇证据问题。不要默认 Codex 的草稿或自检意见正确。
4. 同源两轮是三轮的前缀；独立判断两个版本是否适合各自长度。三轮多轮精读的第三问必须使用前文语境，不能仅仅是第三个独立事实问句。扩展组改了来源，不能用其接受率和原文组直接估计“长度效果”。
5. 跨文档题中，两篇应分别提供回答必需的事实。不得凭主题相近补造因果或时间关系；重点检查家庭取暖/沙特原油配对。证据不足题须确认所问事实确实不在给定材料内，并评价连续不答是否自然。
6. 对截断正文、标题与正文边界、源文拼写和引用文字逐条标注；不能用外部常识补足。需改写时，标明是哪一轮、建议的完整问题/答案及支持该答案的原文 ID；不可回答的建议答案为 null、gold evidence 为空，材料范围另列。

## 输出契约

新建目录 `reports/defense_v1/T10/external_review/<本次独立run_id>/`，保存以下三个文件，不覆盖任何输入：

- `review_manifest.json`：运行 ID、审核者类型、实际模型/人员标识、开始结束时间、输入文件哈希、预期/完成数量、未审 ID、中断和限制；若没完成全部对象则明确 `partial`。
- `session_review.jsonl`：**恰好 70 行**，其中 56 个 `variant_id` 来自两份草稿文件（含 2 个排除项），14 个旧五轮 ID 来自 `baseline_review.jsonl`。每个 ID 一行，不重复。字段包括 `variant_id`、`decision`（accept/rewrite/reject/uncertain）、`reason_codes`（数组）、`turn_reviews`（逐轮的 `turn`、`new_information`、`supported`、`evidence_ids`、`issue`）、`suggested_turns`（不需改写时为空数组）、`source_refs`、`notes`。对无草稿的排除项可留空 `turn_reviews`，但须写明是否维持排除及原因。
- `review_summary.md`：分别统计同源两轮、同源三轮、扩展两轮、扩展三轮及旧五轮的判定、被排除项、多轮精读可用性、证据不足和跨文档争议；给出至少 5 个可定位的代表性 ID。单列仍未解决的问题和判断的主观性。

结构校验只能证明 ID、数量及引用范围一致；每个 accept 的所有轮次仍须人工或模型按原文内容判断。原始试点文件、现有 candidate06 和历史审核输出保持只读。

## 可复制给审核 agent 的任务

> 请独立审核 MIAGuard 的 T10-C 正常会话试点。先阅读 `reports/defense_v1/T10/session_length_pilot_20261031_01/REVIEW_GUIDE_ZH.md`，核对输入哈希，然后按指南逐一审查 54 个候选、2 个已排除版本和 14 个旧五轮会话。请重点核实每轮信息递进、答案事实与原文证据、双文是否都必要、截断边界，以及三轮多轮精读是否真正依赖前文。按规定写入一个新的 `external_review/<run_id>/`，保存 manifest、70 行 JSONL 和摘要；记录实际模型身份及限制。不要读取成员标签或 V/T 效果，不要修改输入，也不要把模型判断写成人工审核。
