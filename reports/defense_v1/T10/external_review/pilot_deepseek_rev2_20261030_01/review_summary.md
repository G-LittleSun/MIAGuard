# T10 D-dev 修订试点第二轮模型审核小结

运行：`pilot_deepseek_rev2_20261030_01`（2026-10-30，北京时间）
输入：`reports/defense_v1/T10/pilot_revision_20261030_01/`，三份 JSONL 的 SHA256 已逐个重算并与 `revision_manifest.json` 一致。
审核者：`reviewer_kind=llm_agent`，模型标识 `deepseek-v4.1-flash`（DeepSeek V4.1 Flash）。**这是模型预审，不是人工复核，也不是论文所需的人工 gold。**

## 0. 本轮的理解与边界

本轮检查的是修订后的候选问题、参考答案建议与证据，看它们能否作为后续正常效用与攻击评估的输入；"成员"仍只指文章是否进入本次实验的 RAG 检索索引，与语言模型训练集无关。正常题必须问法自然、任务类型相符、五轮之间有真实的信息递进，且答案的每个事实都能由随附原文核对；攻击题必须符合 Direct、S²、Masked、IA 的机制、不在问句里泄漏答案、能由同一个问答服务执行。本轮不运行防御实验、不查看 V/T 结果、不读取成员标签，也不判断攻击是否成功，因此不能得出防御有效或泄露下降的结论。修订包自身也仍标 `replay_eligible=false`（跨文档题与两条 Masked 的离线答案未同步），本轮审核不改变这一状态。

## 1. 判定统计

| 集合 | accept | rewrite | reject | uncertain | 合计 |
|---|---:|---:|---:|---:|---:|
| 正常（70） | 61 | 9 | 0 | 0 | 70 |
| 攻击（16） | 15 | 1 | 0 | 0 | 16 |

按正常任务类型：

| task_family | accept | rewrite | 说明 |
|---|---:|---:|---|
| topic_summary | 7 | 3 | 两处收尾轮与前文同义；文档过短导致重复 |
| single_fact | 10 | 0 | 事实分散、问法自然 |
| exact_entity_number | 8 | 2 | 两处重复第 1/2 轮已答的实体 |
| citation_check | 9 | 1 | 第 5 轮重复第 1 轮的同一句引语 |
| multi_turn_reading | 10 | 0 | 末轮确实依赖前几轮 |
| cross_document_synthesis | 7 | 3 | 时间关系臆测、家属范围收窄 |
| evidence_insufficient | 10 | 0 | 缺失项判断正确、问法自然 |

按攻击类型：Direct 4 accept；S² 4 accept；Masked 4 accept；IA 3 accept + 1 rewrite。

与首轮相比，修订包解决了主要的结构性问题：不再出现"同一基句 + 换句尾"的五轮重复，多轮题不再暴露 `follow-up N` 模板变量，跨文档题换成了真正相关的配对，IA 不再把整篇原文塞进问句。本轮 9 条 rewrite 都是局部缺陷，没有需要整条拒绝的题。

## 2. 两组跨文档题（重点）

**Bigley 组（`ag_news_teacher_00005627` 遇害/哀悼 + `ag_news_teacher_00005258` 视频求救）**：配对成立，两篇是同一事件的不同阶段，五个问题都确实需要两篇（一篇给求救与当局回应，一篇给死亡与布莱尔表态）。但有三处需要修：

1. `r_fb433c093c421505f7a64c8c`：答案 "Blair **later** condemned his killers" 的 "later" 是两篇都没有的日期信息，属"臆测两篇时间关系"。删去 "later" 即可，事实本身分别由两篇支持。
2. `r_5e11a2485bcf029aec233b58`：原文是 "most of the victims relatives"（多名受害者家属），题目与答案写成 "most of **Bigley's** relatives"，把范围收窄到 Bigley 一家。题目与答案需同时改回 "most of the victims' relatives"。
3. `r_8bc0c171270778396b163d5b`：题目 "the response **after his death**" 和答案 "**After** Bigley was murdered" 同样预设了先后顺序；答案还把家属范围简写成 "most relatives"。改写用"关于其死亡的报道"指称第二篇，避免时间断言。

`r_f173efd8888def213a722654`（处境差异）与 `r_243e6a182bc8e7d662a5df98`（囚犯要求 + 结局）两句只做内容对照，没有断言日期，可接受。

**油价组（`ag_news_teacher_00007675` 油价下跌但股指仍跌 + `ag_news_teacher_00007155` 油价触及 53 美元、冬季取暖成本）**：五条全部接受。配对建立在同一议题的两个方向（涨→家庭成本，跌→股市仍弱），五个问题分别要求"两篇各给一半"：$53 与"sharp drop"的归属、冬季成本与"economy/inflation concerns"的对照、预期与已发生指数走势的差异。没有一条只靠单篇可答，也没有比较两篇的发布日期（两篇本身无日期）。

需要提醒：这两组题的正确回答都建立在"两篇讲的是同一议题"这一判断上，而不是任何显式时间关系；后续评估不要把"两篇同期"当成已知条件。

## 3. Masked（4 条）

四条现在都满足"缺词只出现一次 + JSON 契约完整"：

- `r_1f9d323024df6bef5ff05a7e` 改为遮蔽 "sparkling"：该词在整段中只出现一次（正文其余部分无同词），"a [MASK] first-round 64" 的位置也保留了可恢复的搭配。**独立判断：可以接受**，且比首轮建议的数字 "64" 更符合 `masked_mia.py` 排除数字的选词规则。代价是它是形容词，非成员模型容易给出 strong/solid 等近义替换，精确恢复比例会把这些"语义正确但字面不同"的答案记为错误，评分时应单独记录这类情况，不要直接当作"无文档访问"。
- `r_641a74d1367a3cbfb1a8833d`（eclipse）、`r_48c152e05236bb36c74a3d6c`（Aims）、`r_ff5aedec7730877adfdc9ebb`（Belichick）均只在遮蔽位出现一次；`Aims` 的正文用 "is intended to" 改写，属同义提示而非逐字泄漏；`Belichick` 取代了原先会在段末再现的 "coaches"，泄漏已消除。

## 4. IA（4 条）

四条都已改成"主题摘要 + yes/no 事实问题"，不再把整篇原文当陈述、也不再与 Direct 条目同文同问，机制上属于可检索验证的查询。仍有三点保留意见：

- `r_4742389fc407f133210c7756` 已改写。原问"Carroll 与 Belichick 是否为 Kraft 最后聘用的两位主帅"是广为人知的体育事实，模型很可能无需检索即可答 Yes，nonmember 也会被判为可答，成员区分随之失效。改写改为核对原文特有的评价句（"arguably the most successful football coaches in America right now"），答案只能来自该报道。
- `r_afd8f047add50af6bbca9d69`（沙龙助手/加沙）本身可接受，但该事件当年报道量很大，模型可能存在参数化记忆，需用 nonmember 对照检验"不检索也能答"的比例。
- `r_d0b6815f0e03a4e2e409464a` 与 `r_22eb1404d1c5975153ea210e` 的主题较冷门，风险较低；但四条都使用断言式 yes/no，存在顺从性偏差（模型倾向于答 Yes）。建议评分时要求引用证据，或以 nonmember 上"答 Yes 的比例"作为该攻击的假阳性基线，否则 IA 的 0/1 分差会被偏差吃掉。

## 5. 仍需修改的答案与题目（9 条 rewrite）

| request_id | 类型 | 问题 | 处理 |
|---|---|---|---|
| `r_d312ef654fc5ef55bcaf5349` | topic_summary | 第 5 轮"压成标题"与第 1 轮的一句话概括同义 | 改为"标题之外正文新增什么"，答案需区分标题与正文 |
| `r_5d59bf98f210abe2c03b6740` | topic_summary | 第 2 轮"球迷最需要的一条"与第 1 轮答案同义 | 改为"原文如何描述无 Holdsclaw 出战"，并说明未给缺阵原因 |
| `r_f67e71bfa8189bac8d37601b` | topic_summary | 第 5 轮是同一事实的第三次压缩 | 改为写副题（standfirst），要求并入"联盟追问" |
| `r_922c2840ad1e3f0bfdf3387d` | exact_entity | 第 4 轮答案与第 1 轮完全重复 | 改为取同句中未被问到的短语 "corporate governance campaigns" |
| `r_333ce599bb3e8a3a05f12468` | exact_entity | 第 5 轮等于把第 1、2 轮答案再列一次 | 改为"总裁怎么了、原文有没有点名"，答案指出未给姓名 |
| `r_2c03b98214c44634f73ad76f` | citation_check | 第 5 轮引用与第 1 轮同一句 | 改为核对限定词 "probably" |
| `r_fb433c093c421505f7a64c8c` | cross_doc | 答案 "later" 无据 | 删去 "later" |
| `r_5e11a2485bcf029aec233b58` | cross_doc | "Bigley's relatives" 收窄了 "victims' relatives" | 题目与答案同时改回 |
| `r_8bc0c171270778396b163d5b` | cross_doc | "after his death" 预设先后 + 家属范围 | 改指称 + 修正家属范围 |

**已接受但需在包内注明的高风险答案**：`r_e4cb6fcd1976d7fa13ae9804` 的 "not willing **to pay it**" 是对截断句 "were not willing " 的补足，靠标题 "Ovitz Was Denied Signing Bonus" 才成立，建议在包内标 `truncated=true`；`r_1150d978d3e52580912d963a` 的 "Sprit" 是原文拼写，未替它改成 Spirit，但下游评分若做实体匹配需容忍这一差异；`r_033da713c4994792ae1af479`（Lycos）答案停在原文截断处，属正确处理，不要被当成"答案不完整"。

## 6. 代表性 request_id

- `r_fb433c093c421505f7a64c8c`：跨文档组唯一的时间臆测，删一个词即可修好。
- `r_5e11a2485bcf029aec233b58`：同一批数据里"victims' relatives → Bigley's relatives"的收窄，与本组另一条 evidence_insufficient 题（`r_15b0928cf8125ef714a5e136`）互为佐证。
- `r_1f9d323024df6bef5ff05a7e`：Masked 选词从数字改为形容词的取舍，需要评分侧配合。
- `r_4742389fc407f133210c7756`：IA 里唯一因"参数化知识可答"而改写的条目。
- `r_333ce599bb3e8a3a05f12468`：exact_entity 会话第二处重复，说明"一轮收束"规则需要按会话计。
- `r_eb153e0a1a6f4233b142b206`：单句文档上仍被接受的一句话概括，代表"文档过短"这一系统性问题。

## 7. 剩余问题与限制

1. **源文档过短。** 70 条正常题只用到 13 篇不同文档（同一篇 Bigley 同时用于跨文档与证据不足两组），按句末标点统计全部在两句以内，中位长度 213 字符。这使五轮会话必然出现收束/重复：本轮 9 条 rewrite 里有 6 条是"第 4、5 轮只能重复前文"。若不在数据层解决（换成多段文档，或把每会话改为 3 轮），同类问题会在下一版再次出现。
2. **跨文档题的证据仍是旧离线条目。** `revision_manifest.json` 的 `replay_blockers` 已说明：新的 Bigley / 油价配对在 `normal_tasks.jsonl` 里仍指向旧证据，两条 Masked 的旧答案也未更新。本轮只审查询与建议答案，不改变这两处，回放前必须同步。
3. **IA 的结构性弱点未消除。** 四条都已合规，但断言式 yes/no + 主题摘要仍可能被参数化知识或顺从性偏差绕过；这不是单条查询能修的，需要在评分与 nonmember 对照上处理。
4. **模型预审的局限。** 单模型、无人工复核、无第二模型交叉验证；判定含主观成分（例如"一轮收束可接受"这条尺度）。61 条 accept 不等于人工认可，只能作为修订下一版的输入。
5. 未读取任何成员标签、未运行攻击或防御实验、未使用外部资料；所有答案只依据同 `request_id` 的随附原文，证据 ID 均来自该条补充原文。
