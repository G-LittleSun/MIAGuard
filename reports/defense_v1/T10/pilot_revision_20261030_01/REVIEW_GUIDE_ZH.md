# T10 D-dev 修订试点：第二轮独立审核

本目录是依据 [DeepSeek 首轮模型预审](../external_review/pilot_deepseek_20261029_01/review_manifest.json)建立的**新试点草稿**，不是正式 gold，也不是 `candidate06` 的全量替代。正常 70 条中，60 条采用首轮 agent 的改写建议，10 条跨文档题由 Codex 重新配对并起草；攻击 16 条中，10 条保留、5 条采用首轮改写、1 条 Masked 因首轮建议遮蔽数字而由 Codex 再改。所有行仍为 `review_status=pending`，`formal_effect_eligible=false`。原包和首轮输出保留不动。**暂不可用于回放评分**：跨文档题的旧离线证据、两条 Masked 的旧离线答案尚未同步，且所有参考答案仍待复核。

## 输入与检查

1. 先读 [修订清单](revision_manifest.json)，逐个重算其中三个 JSONL 的 SHA256；不一致则停止并说明。
2. 读 [70 条正常题](review_packet_d_dev_normal.jsonl)和[逐题原文](review_packet_d_dev_normal_evidence.jsonl)，按 `request_id` 对齐、按 `session_id` 连续审五轮。`draft_*` 是**答案建议**，必须重新核对，不能直接接受。
3. 读 [16 条攻击题](review_packet_d_dev_attack.jsonl)。不读取 `candidate06` 的 `documents.jsonl`、`labels.jsonl`、`attack_labels.jsonl` 或 V/T 结果；攻击题的成员标签仍然隐藏。
4. 判定规则与输出字段沿用[首轮交接单](../AGENT_REVIEW_HANDOFF_ZH.md)第 2–5 节，逐条给 `accept/rewrite/reject/uncertain`；不要因为它是“修订版”就降低标准。

建议在新会话中审核，先不要阅读首轮逐条结论和小结，以减少既有判定对第二轮的影响；需要追溯来源时再看修订清单。

## 本轮重点

- **跨文档两组各五轮：**Kenneth Bigley 的求救报道与遇害后报道、油价影响家庭取暖成本与股票市场的两篇报道。每道题及答案都须真正需要**两篇**；发现只靠一篇就能回答、两篇时间关系被臆测、五轮又重复，应 `rewrite/reject`。证据仍只来自当前随附原文。
- **其余正常题：**核查首轮改写是否仍存在标题词硬拼、同义重复、会话历史无作用、答案超出截断片段。特别检查 Ovitz 的“被拒绝”表述是否比原文更强、Gaza/Lycos 的句尾截断、Mars 的实体是否仅来自标题。
- **攻击题：**复查两条 Masked 的新遮蔽词在正文中是否只出现一次且 JSON 契约未破坏；其中 Clement 条首轮建议改遮数字“64”，与现有 Masked 选词规则冲突，本包改为遮“sparkling”，也须重新判断是否合适。四条 IA 是否真正可检索验证、是否无需文档也能猜出 “Yes”；Direct/S² 仍逐项检查机制。不要推断攻击成功率。

## 输出

新建 `reports/defense_v1/T10/external_review/<新run_id>/`，保存 `review_manifest.json`、`normal_review.jsonl`、`attack_review.jsonl`、`review_summary.md`；不要覆盖首轮目录。manifest 应记录本修订清单和三个 JSONL 的 SHA256、实际模型标识、审核者类型、完成/未完成 ID 与限制。两份 JSONL 分别恰好 70/16 行，ID 与本目录原包一一对应。摘要须单列两组跨文档题、Mask 与 IA 的结论及剩余缺陷。

即使第二轮模型全部接受，也只得到更可靠的**模型预审建议**。正式论文中的人工 gold 和 E07 人评仍按[实验协议](../../../../docs/DEFENSE_EXPERIMENT_PROTOCOL_ZH.md)的真实人员要求处理。更新独立的离线答案/证据并通过核验后，才能将本修订包用于开发阶段的工程联调。
