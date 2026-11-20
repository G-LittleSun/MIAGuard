# v2 复用预审接收与修订结果

日期：2026-11-05。外部[审核清单](../external_review/v2_reuse_deepseek-v4.1-flash_20261105_01/review_manifest.json)声明 DeepSeek V4.1 Flash，模型标识来源为其运行会话环境变量，未取得供应商不可变快照。实际运行模型身份无法由我方独立证明；未编造后缀。外部文件保留原样。

## 1. 接收和结构核验

[结构验证](structural_validation.json)通过：206 IA、60 Masked 来源方案与输入逐条、同序对应，10 项输入和3项输出摘要一致；IA 引文都在对应原文内，Masked 全部可逐字还原、编号和五查询对应、剩余正文及指令无缺词重现。外部输出 manifest 的完整 SHA256 已记入上述验证 JSON，避免用缩写作为身份判断。

外部判定：IA 0 accept /67 rewrite /115 reject /24 uncertain；Masked 60 rewrite。上述判定不是人工 gold，不直接转换为最终使用/删除决定。

## 2. IA：采用有依据的局部修订，保留争议

Codex 子任务逐条比对67个 rewrite 与原文，主流程再次检查11个问题项，详见[IA 处理记录](IA_TRIAGE_ZH.md)及[本地改写](ia_local_amendments.jsonl)：

- 6 条原改写被主流程局部修订，恢复原文中的 may/planning、相对时间、人物归属、时序和主持条件。
- 5 条因肝损伤诊断无依据、核对对象漂移或需同源去重而暂缓。
- 56 条保留原模型建议，仍标 pending；其中的目标范围、引文片段、标题/截断和同源事实重复等质量风险继续记录。
- 115 reject 和24 uncertain 保留为待裁决队列，加上上述5条共144条暂不导出。原库不删除；有些 reject 可修复或仅应去重，不能一概认为材料不支持。

形成 **62 条 pending IA 草稿**（61 yes /1 no）。这不是全 train 的 IA 分布，也不代表62条已正式合格：本包之外的2,169条仍有751个 unknown 参考值，尚未语义验收。模型把缺失事实全排除的尺度不直接成为项目规则；不为凑类别生成无依据候选值。

## 3. Masked：数据结构修复可保留，理由重新记录

两个 Codex 检查路径核对全部60方案。26个换词方案共改35个答案槽；原文可见的旧答案泄漏是33槽，另两个变更涉及非数字/正文词优先性。外部26条说明均把新词误写成“原词”并表述为新词→新词；新材料使用[实际差异记录](masked_triage.jsonl)，同时保留外部原理由。

例如00000050实际是 `may → vendor`，原 `may` 与标题 `May` 重现；不是外部理由所称 `vendor → vendor`。00000220的 `350-pound → Siberian` 和00000224的 `quickinfo → widely` 不能解释成原词残余泄漏。

**300 条 Masked 提问进入 pending 草稿**。34个方案只补JSON输出要求，26个改变遮蔽方案；每方案保留五种提问和五个编号，新的题/答案身份不得复用旧trace或声称同难度。继续标记：

- 7个来源存在大小写归一后的重复答案值；它们的多个位置不是独立样本。
- 3个来源答案含字面数字；“优先非数字”不是本交接中的硬排除规则，仍待优化。数量语义词不限于这3项。
- 1个方案正文编号顺序为2、1、3、4、5；数字到答案的映射合法，不因出现顺序自动排除。
- 原拼写 `Repects`、站点词 `newratings`、标题词和3篇截断来源已补记，不能通过清洗原文默默改变身份。

## 4. 新候选与使用边界

新建[候选叠加层](../../../../data/defense_datasets/legacy_v2_reuse_overlay_20261105_01/manifest.json)，只包含本次修改的攻击草稿：**362 查询 = 62 IA +300 Masked**；[独立验证](../../../../data/defense_datasets/legacy_v2_reuse_overlay_20261105_01/validation.json)通过。在线请求只有 `request_id/session_id/query`；原索引成员真值、评分参考、原文身份、质量警告与新旧映射都在离线文件。

每条内容/答案修改均建立新身份，不复用旧 Session trace。当前每条使用一个临时单查询会话，**不是最终多轮布局**，不得用于声称 Session 覆盖或策略效果。所有条目 `review_status=pending`，全局 `human_gold_complete=false`、`formal_effect_eligible=false`、`replay_eligible=false`。

该层不是新完整 QueryBank，不替换最新 v2 原库，也不包含1,304正常题、Direct/S²或其余2,169 IA 的完整验收。旧v1识别结果、v2原查询和原索引均未改动。本轮没有调用生成模型或运行防御实验。

## 5. 接下来

先确定并补齐一小批 v2 正常题的答案、证据和来源范围；继续裁决被暂缓 IA、补充其余攻击语义核对及上述 Masked 警告，再做成对方法输入与实际会话的最小适配。条件满足后安排 engineering_only 真实回答联调。正式 T10-E 人工 gold、T11/G2 和新终测门禁保持未完成。
