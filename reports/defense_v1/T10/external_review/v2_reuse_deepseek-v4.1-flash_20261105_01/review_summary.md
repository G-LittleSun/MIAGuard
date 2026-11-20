# v2 train 复用缺口：独立模型预审小结

运行目录：`reports/defense_v1/T10/external_review/v2_reuse_deepseek-v4.1-flash_20261105_01/`
审核对象：`v2_reuse_review_packet_20261105_01`，206 条 IA 疑点 + 60 个来源级 Masked 方案（300 条提问）。
审核者：LLM agent，`model_id = deepseek-v4.1-flash`（来源：运行会话环境变量 `CODEBUDDY_CURRENT_MODEL_ID`；未取得供应商不可变快照号，未编造后缀）。
`reviewer_kind = llm_agent`，`human_reviewed = false`，`formal_effect_eligible = false`。**这是单模型预审建议，不是人工审核或人工 gold。**

## 1. 本轮能回答与不能回答

能回答：这 206 条 IA 问句能否在随附原文上形成可判定的 Yes/No/Unknown 核对，以及 60 个 Masked 方案能否逐字还原、无缺词泄漏、五条提问格式合规。

不能回答：v2 全库其余 2,169 条 IA、Direct/S² 的语义质量、1,304 条正常题的答案证据，以及任何防御效果。未读成员标签、其他分区、攻击结果或 A-cal/V/T，未使用外部资料。

## 2. 输入核对与完成情况

`sources.jsonl`（`ba8c63a8…`）、`ia_items.jsonl`（`5f3624be…`）、`masked_items.jsonl`（`b17f2ac2…`）、`REVIEW_GUIDE_ZH.md`（`809901ed…`）均与 `manifest.json` 的 `files_sha256` 一致；上游 5 个文件（queries.jsonl、split json、target_docs.jsonl、审计 manifest 与 query_reuse_audit.jsonl）也逐一核对一致。结构：60 篇、206 条 IA、60 个遮蔽方案、每个方案 5 条提问，ID 唯一、无自配对。

完成 266/266 单元，`status = complete`，`partial = false`，未审 ID 为空。输入文件未改动。

## 3. IA：206 条

| 判定 | 数量 |
|---|---:|
| accept | 0 |
| rewrite | 67 |
| reject | 115 |
| uncertain | 24 |

原库 206 条**全部**存在同一结构缺陷：查询把含答案的 summary 原样放在开头（206/206），紧接着却用 What/Which/How 问句并要求 “Yes, No, or Unknown”（206/206），既泄漏答案又不构成二分类核对。因此没有一条可以原样接受。

- **rewrite 67 条**：改为单一 Yes/No/Unknown 陈述核对，答案均能在原文逐字定位。ground truth 分布为 yes 66 / no 1 / unknown 0。代表：`ag_news:ag_news_teacher_00000050:ia:generated:0001`（金额核对）、`ag_news:ag_news_teacher_00000220:ia:generated:0016`（唯一 no 项：原文明确写 Siberian tiger，故“未说明品种”为假）。
- **reject 115 条**：原文根本没有所问事实（约 82 条），或与同文另一条重复/同一缺口（约 15 条），或问题预设、同义反复不成立（3 条），其余 15 条为同一缺口的换述或指代/数字关系不成立。代表：`ag_news:ag_news_teacher_00000050:ia:generated:0010`（原文只有一句收购报道，无“收购后角色”）、`ag_news:ag_news_teacher_00008636:ia:generated:0005`（一句 Vaughan 报道，未列任何纪录）。
- **uncertain 24 条**：原文在目标处截断（21 条）或指代/归属不明（3 条），无法判断事实是否存在。代表：`ag_news:ag_news_teacher_00000176:ia:generated:0002`（截断于 thorny issues 之后）。

需要强调：**改写后没有 unknown 类探针**。119 条原建议为 unknown 的条目，绝大多数问的是原文完全没有的细节；要构成“具体但原文未述”的探针必须补写候选值，本轮不做这种补造，故归入 reject/uncertain。这意味着修正集是 66 yes + 1 no，无法用于检验“模型是否会对未述细节说 Unknown”；这批分支需要生成器带真实候选值重造。

## 4. Masked：60 个来源方案

| 判定 | 数量 |
|---|---:|
| accept | 0 |
| rewrite | 60 |
| reject / uncertain | 0 |

60 个方案的遮蔽文本都能用 `answers_suggestion` 逐字还原原文，编号 1–5 完整，这一点全部通过。但 **60/60 的五条提问都没有要求 JSON 输出**（也没有 `answers` 数组与编号顺序要求），所以全部至少需要重写提问；遮蔽文本与答案不变的 34 个方案只改提问。

**26 个方案存在缺词残留泄漏**，已按“保持 5 个编号遮蔽、移位换词”修复，修复后剩余正文不再出现任一缺词（逐条用词边界、不区分大小写复核）。改动较多的：

- `masked_source_ag_news_teacher_00000224`：`Merck` 在标题与正文各出现一次、`FullQuote` 只存在于 URL 锚文本；把 3 个遮蔽位移到正文 `Down` / `recalled` / `widely`，同时去掉了两个 HTML 标记型遮蔽。
- `masked_source_ag_news_teacher_00008622`：`Macromedia`、`Captivate`、`simulations` 均在标题与正文重复，改为遮蔽 `readies` / `Monday` / `announcing`。
- `masked_source_ag_news_teacher_00000102`：`Longhorn` 出现三次，改为遮蔽 `march`。
- `masked_source_ag_news_teacher_00000997`：`Losses` 在标题与正文重复，改用 `largest`；该处移位后 `[Mask_1]` 在正文中位于 `[Mask_2]` 之后，编号与答案仍一一对应。

其他需注意：5 个方案答案值重复（doc 尾号 0149 的 intelligence、0910 的 cybersecurity、8559 的 Australian、8603 的 Conservationists、8927 的 progress），评分时同词多位相关，不宜当独立题；3 个方案仍含数量型缺词（`8001` 12-seater、`8319` 40-Year、`8361` 20-year-old），优先度低于非数字词；所有移位都改变了难度，与原方案不完全可比。

## 5. 主要争议与需人工裁决

1. **reject 尺度**：我把“原文没有该事实”判 reject，而不是勉强改写成同文另一条（会造成重复探针）。若项目希望保留条目、允许换核对目标，这 115 条里有一部分可转为 rewrite，但题面会与已有条目高度重叠。
2. **unknown 类缺失**：修正集 0 条 unknown。是接受“这批 unknown 建议不可修”，还是由生成器补候选值后重造，需要项目定。
3. **Masked 移位幅度**：26 个方案换了遮蔽词，难度与原方案不可直接比较；若实验要求前后可比，应把修复版当作新方案重新编号，而不是当作同一方案的勘误。
4. **数字型缺词**：3 个方案保留数量词遮蔽；指南只要求“优先”非数字词，未强制，故未再改动。
5. **HTML 噪声**：`0224` 原方案把 URL 片段当缺词，说明生成器未过滤标记文本；其余方案是否也有类似问题，需要在生成侧统一清洗。

## 6. 限制

- 只覆盖被标记的 206 条 IA 与全部 60 个 train Masked 方案，不代表整个 v2 复用验收。
- 二分类改写与 ground truth 均为单模型判断，未与人工标注或第二模型交叉验证；`yes/no` 只针对随附片段，不代表全文。
- 未读成员标签、攻击结果、A-cal/V/T，未运行任何攻击或防御实验；不能据此推断攻击成功率、防御有效性或误伤率。
- 改写问句保留原文措辞，可能与真实用户提问分布有差异；自然度未量化。
