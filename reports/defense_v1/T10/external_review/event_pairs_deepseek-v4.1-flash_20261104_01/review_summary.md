# D-dev 31 篇文章的成对事件关联：独立模型预审小结

运行目录：`reports/defense_v1/T10/external_review/event_pairs_deepseek-v4.1-flash_20261104_01/`
审核对象：`event_pair_review_packet_20261104_01`，31 篇 D-dev 试点原文的全部 465 对。
审核者：LLM agent，`model_id = deepseek-v4.1-flash`（来源：运行会话环境变量 `CODEBUDDY_CURRENT_MODEL_ID`；未取得供应商不可变快照号，未编造后缀）。
`reviewer_kind = llm_agent`，`human_reviewed = false`，`formal_effect_eligible = false`。**这是模型预审建议，不是人工 gold。**

## 1. 本轮能回答与不能回答

能回答：在这 31 篇随附文本范围内，每一对是否提供足以指向同一具体事件的证据、是否存在可文档化的事件链、还是只共享人物/机构/主题，或看不出关联。

不能回答：这些文章在更广语料中是否真的独立（本包只有 31 篇，未覆盖其原文出处、其他报道或跨分区材料）；也不能回答成员身份、攻击是否成功或防御是否有效。本轮未读成员标签、攻击结果、A-cal/V/T，未使用外部资料。

## 2. 输入核对与完成情况

`sources.jsonl` 摘要 `4485c940…`、`pairs.jsonl` 摘要 `80d9b2aa…`、`REVIEW_GUIDE_ZH.md` 摘要 `45f755fc…`，与 `manifest.json` 记录逐项一致；上游三份来源文件（`source_evidence.jsonl`、`expanded_source_evidence.jsonl`、`source_usage.jsonl`）摘要也一致。结构复核：31 篇、465 对、`pair_id` 465 个唯一、文档对 465 个唯一、无自配对。

465/465 完成，`status = complete`，未标 partial，未审 ID 为空。原始包与既有审核输出均未改动。

## 3. 判定计数

| relation | 数量 | high | medium | low |
|---|---:|---:|---:|---:|
| `same_event` | 1 | 1 | 0 | 0 |
| `related_event` | 3 | 0 | 2 | 1 |
| `shared_entity_or_topic` | 17 | 3 | 5 | 9 |
| `unrelated` | 444 | 444 | 0 | 0 |
| `uncertain` | 0 | 0 | 0 | 0 |
| **合计** | **465** | **448** | **7** | **10** |

465 对中只有 21 对存在可指认的关联，其余 444 对在给定文本内没有共同的具体事件、参与方、地点或实质主题。

## 4. `same_event`：1 对

| pair_id | 两篇 | 置信度 | 关键依据（分别来自两篇原文） |
|---|---|---|---|
| `pair_76e0bac073af4be7b8dc` | …5258 × …5627 | high | `The captive, Kenneth Bigley, appealed to British Prime Minister Tony Blair to intervene` / `Prime Minister Tony Blair condemned the killers of British hostage Kenneth Bigley as barbaric` |

Bigley 人质事件的两篇报道（`…5258` 为绑匪要求释放女囚、人质在录像中向 Blair 求救；`…5627` 为 Blair 谴责凶手、家属评价其处理方式）指向同一名被劫持者、同一批绑匪与同一条事件线，因此判 `same_event`。两者的差别是报道时点（求救阶段 / 遇害之后），不是两起事件。

## 5. `related_event`：3 对

| pair_id | 两篇 | 置信度 | 关键依据（分别来自两篇原文） |
|---|---|---|---|
| `pair_32e584653566e4b5456e` | …1079 × …7155 | medium | `because of higher fuel prices and colder weather` / `higher heating bills for American households` |
| `pair_35531810250b51dfc638` | …2987 × …3766 | medium | `an unexpectedly large rise in U.S. crude` / `as oil tumbled` |
| `pair_7d446ba6a0a5a62c5e54` | …2987 × …7155 | low | `an unexpectedly large rise in U.S. crude` / `higher heating bills for American households` |

- `pair_32e584653566e4b5456e`（取暖成本 × 油价 53 美元）：同一“今冬取暖成本上升”判断的两半——政府预测给出金额与归因，油价篇给出当日价位与传导。共享具体事实，但未共享消息来源或日期，故 `medium`。
- `pair_35531810250b51dfc638`（油价续跌 × 美股高开）：同一轮油价回落及其向股市的传导，交易日为相邻的周三/周四；报道对象不同（油市/股市），不是同一事件，故 `medium`。
- `pair_7d446ba6a0a5a62c5e54`（油价续跌 × 油价 53 美元）：两篇都描述“纪录高位后回落”，但一篇无日期、一篇只有“周四”，无法确认先后，故 `low`。这是本批最接近 `uncertain` 的一对。

## 6. `uncertain`：0 对，以及为什么

31 篇文本虽短（120–360 字符），但每篇的报道主体都能识别：既没有“两篇都可能指向同一事件、却缺少时间或参与方”的组合，也没有仅因截断而无法判断的对。4 篇存在截断（`…3040` 停在 "were not willing"、`…4036` 以省略号结尾、`…5258` 停在 "intervene"、`…7841` 停在 "servers that Lycos"），但它们与其余 30 篇的主体均无重合，截断不影响“无关联”的判断；因此没有把截断当作 `uncertain` 的理由。

需要说明的边界：`pair_7d446ba6a0a5a62c5e54` 若要求明确日期锚点，应降为 `shared_entity_or_topic`；Bigley 两篇若按“不同新闻事件”而非“同一事件的不同阶段”理解，应降为 `related_event`。这两处属判定尺度，不由模型预审单方面定死。

## 7. `shared_entity_or_topic`：17 对

- `pair_824d7fd350f313258ba8`：…1069 × …5258（high）
- `pair_375c9a3a1fa46c9c104c`：…1069 × …5627（high）
- `pair_50b7d93a25bf775d3ddd`：…1079 × …1135（low）
- `pair_b2d4b12c3b27b993d018`：…1079 × …2987（low）
- `pair_8ec127ad3a44450df057`：…1079 × …3766（low）
- `pair_03f46ba9d376d328d459`：…1079 × …7675（low）
- `pair_3a37d615dab43f1da7ec`：…1124 × …1214（high）
- `pair_f6b352550d2291755fc4`：…1135 × …2987（low）
- `pair_470ec8737ddba6621863`：…1135 × …3766（low）
- `pair_630a1c35d8af86cb80a3`：…1135 × …7155（low）
- `pair_0e27380acf681d83360d`：…1135 × …7675（low）
- `pair_16bcf60ca41247a72d24`：…1160 × …7841（medium）
- `pair_e85d03670705039cf8d0`：…1167 × …5971（low）
- `pair_5a0551e4a4c3938d659a`：…2987 × …7675（medium）
- `pair_d99f8162aef8a2b42cbf`：…3766 × …7155（medium）
- `pair_a67a19caf3eb29c8de56`：…3766 × …7675（medium）
- `pair_176db8fc4ee20b31892d`：…7155 × …7675（medium）

其中 3 对为 `high`（`…1069`×`…5258`、`…1069`×`…5627` 共享 Tony Blair；`…1124`×`…1214` 共享布什与同一“周一”），5 对 `medium`（油价与美股四对、垃圾邮件一对），9 对 `low`（沙特供应表态与各油价篇、取暖成本与各油价篇、加州金融语境）。`low` 的含义是：只能确认同属一个泛主题或地域行业语境，不能确认任何事件级联系。

## 8. 关联不具传递性

本轮结果不能自动合并成“事件簇”。典型反例：`…1079`（取暖成本）与 `…7155`（油价 53 美元）是 `related_event`，`…7155` 与 `…2987`（油价续跌）也是 `related_event`，但 `…1079` 与 `…2987` 只有 `shared_entity_or_topic`（`pair_b2d4b12c3b27b993d018`）。若按传递闭包合并，会把 6 篇油价/能源文章压成一个“事件”，其中多数对并没有共同的具体事实。

同理，`…1069` 因共享 Blair 而与 `…5258`、`…5627` 各自成 `shared_entity_or_topic`，但后两者才是 `same_event`；“共享同一人物”不能升级为“同一事件”。

## 9. 主要争议与需人工裁决

1. **Bigley 的阶段划分**：求救/谈判与遇害报道，算同一事件的不同阶段（本轮 `same_event`），还是相邻的两个事件（应改 `related_event`）？直接影响“同一事件”计数是 1 还是 0。
2. **油价六篇的边界**：`…1079`、`…1135`、`…2987`、`…3766`、`…7155`、`…7675` 都涉及原油/燃料价格，但只有 3 对被判为 `related_event`，其余 12 对为 `shared_entity_or_topic`。若项目按“同一价格周期”处理，应把它们并为一组做敏感性分析，而不是逐对判断独立性。
3. **`…7155`×`…2987` 的日期缺口**：`related_event`（low）与 `shared_entity_or_topic` 之间只差一个日期锚点，文本无法提供。
4. **体裁不算主题**：体育 15 对、科技/互联网 6 对、并购/公司新闻若干对均判 `unrelated`。若项目认为“同属体育/科技版块”也应计入弱关联，这些对需重新标注。
5. **`…1167`×`…5971` 的加州金融语境**（`low`）：是否值得保留为弱关联，取决于下游是把 `shared_entity_or_topic` 当作“需分层”还是“可忽略”。

## 10. 限制

- 仅 31 篇 D-dev 文本、465 对；未覆盖其余已知来源，也未跨分区核查，因此“unrelated”只表示**在给定文本内**未见关联，不证明语义独立。
- 全部判断基于随附片段，未查原文全文、发布时间或外部报道；`same_event`/`related_event` 的时点判断受片段长度限制。
- 单模型预审，无第二审核者、无人工裁定；`high` 也只是模型置信，不是人工确认。
- 未读成员标签、攻击结果、A-cal/V/T，未运行任何防御或攻击实验；本文件不能用于推断攻击成功率或防御效果。

## 11. 对下游使用的建议

- 把 `same_event`（1 对）与 `related_event`（3 对）作为**必须分层或合并**的最小集合：Bigley 两篇不应同时计入独立样本；取暖成本与油价、油价与美股三对在做独立性假设时应至少做一次剔除敏感性检验。
- 把 6 篇能源价格文章作为**一个主题簇**处理，而不是依赖逐对传递；`shared_entity_or_topic` 的 17 对可用于分层，不应用来合并样本。
- 其余 444 对可暂按独立处理，但这只是“未发现关联”，需要在更大语料上复核后才能作为独立性声明。
