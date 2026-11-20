# T10 D-dev 人工复核试点说明

来源：[候选 v06 manifest](../../../data/defense_datasets/defense_access_v1_candidate06/manifest.json)；[试点包 manifest](review_packet_manifest.json)。本包只含 D-dev 的 70 条正常问题（七类各 2 个五轮会话）与 16 条攻击问题（四类各 4 条）。攻击包不提供成员标签。当前全部 `review_status=pending`，本文件不表示任何人已经复核。

若由用户安排的模型 agent 先审，使用[专门交接单](AGENT_REVIEW_HANDOFF_ZH.md)及[补充原文](review_packet_d_dev_normal_evidence.jsonl)，输出放在[独立目录](external_review/README.md)。该输出是模型预审，不适用下文真实人员 `reviewed_by` 的填写方式。

## 复核动作

1. 正常问题逐条判断是否自然、是否真的要求该任务类型、是否仅凭所给原文可回答。五轮应有真实信息递进；仅改句尾措辞的重复提问标为 `rewrite`。`evidence_insufficient` 要特别检查原文是否真的缺少所问信息。
2. 对可回答项给出精确且简短的参考答案，并核实每个 `gold_evidence_id`；对不可回答项保留空证据并写明理由。原文中的 HTML 痕迹不应直接复制进答案。跨文档题需两篇来源都相关且必须都用到，若随意拼接两篇则标 `reject`。
3. 攻击问题核对 Direct、S²、Masked、IA 的查询语义与既有攻击实现是否一致。Masked 确认被遮蔽词没有在问题其他位置直接出现，JSON 输出契约明确；IA 核对问句真假与“从检索结果判断”的可执行性。发现只靠问题本身就能回答、无需 RAG 检索的样例，标 `reject`。
4. 在 JSONL 副本中填写 `decision`（`accept`/`rewrite`/`reject`）、必要的 `corrected_*`、`notes`、真实 `reviewed_by` 和 `review_status=reviewed`。不要覆盖原试点包；新复核文件另建版本并记录复核者、时间和原包 SHA256。缺失或未核对的字段保持 pending，不推断已完成。

## 放行条件

- D-dev 试点先统计七类任务与四攻击的接受率、主要拒绝原因，并据此修订自动候选；不因 V/T 表现调模板。
- 正式正常效用 gold 需要独立复核后的答案/可回答性/证据。T 的复核者不看开发策略效果和成员标签；复核过程记录版本与人员身份。
- 本试点包及当前候选数据 `formal_effect_eligible=false`。通过工程校验、模型能生成回答或测试全通过，都不能代替上述人工判断。
