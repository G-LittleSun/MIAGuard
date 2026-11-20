# T10 第二轮模型预审接收与开发决策

日期：2026-10-30。范围：D-dev 70 条正常问题、16 条攻击问题。输入为 [`pilot_revision_20261030_01`](pilot_revision_20261030_01/revision_manifest.json)，外部输出为 [`pilot_deepseek_rev2_20261030_01`](external_review/pilot_deepseek_rev2_20261030_01/review_manifest.json)。这是模型预审，不能记为人工 gold。

## 独立核验

[`review_validation_rev2_20261030.json`](review_validation_rev2_20261030.json)重算了四份输入哈希、引导文件哈希、两份输出的行数/顺序/ID/字段和对应证据范围。文件契约无错误：正常 61 accept、9 rewrite；攻击 15 accept、1 rewrite。实际模型 ID 只由运行环境自报为 `deepseek-v4.1-flash`，没有供应商快照证明。

**发现审核自查漏掉的证据错误：**Bigley 组 3 条被标为 rewrite 的题目与答案都需两篇原文，但 `final_gold_evidence_ids` 只写了 `ag_news_teacher_00005627`，漏掉 `ag_news_teacher_00005258`：`r_fb433c093c421505f7a64c8c`、`r_5e11a2485bcf029aec233b58`、`r_8bc0c171270778396b163d5b`。本地核对两篇原文后，在**独立开发试点**补齐，外部原始审核文件不改。

## 已落地的局部修订

[`defense_access_v1_pilot_overlay_rev2_20261030`](../../../data/defense_datasets/defense_access_v1_pilot_overlay_rev2_20261030/manifest.json)只取 D-dev 的 86 条，把模型最终查询/答案建议写入新的在线请求与离线任务文件；修复上面 3 条跨文档证据；同步两条 Masked 的离线缺词 `Clement→sparkling`、`coaches→Belichick`。[`validation.json`](../../../data/defense_datasets/defense_access_v1_pilot_overlay_rev2_20261030/validation.json)确认 70/70/16/16 行、ID 对齐、在线请求无成员标签、跨文档均有双证据、Masked 缺词不在问题正文中泄漏、正常任务满足数据契约。原 `candidate06`、两轮审核输出和冻结索引未改。

该 overlay 用于**开发阶段联调**，不是完整候选数据集，也没有人工复核；全部任务仍 `review_status=pending`、`reviewed_by=null`、`formal_effect_eligible=false`。不运行 E01–E07 正式效果实验。

## 仍然阻塞全量生成的内容质量问题

1. **五轮会话在短新闻片段上仍重复。**例如 Mystics 的同一会话中，第 1、2、3、4、5 轮都围绕“无 Holdsclaw 却进季后赛”；Calpers 会话第 3、4 轮都答 `corporate governance campaigns`。61 条 accept 只能表示该审核模型的判定，不能证明会话多样性。当前候选 D-dev 100 篇成员文档的长度中位数为 234 字符，句末标点中位数为 1；V/T 也分别约 228/229 字符。下一版不得继续把每篇短片段机械扩展为五轮。先在 D-dev 对**短片段每会话至多 2–3 轮、增加独立文档覆盖**做小样本试验；真正 `multi_turn_reading` 应选择有足够独立事实的长文，做不到则减少该家族规模并在协议中记录。不能只靠换句式来提高“多样性”。
2. **部分答案依赖标题或截断边界。**Ovitz `r_e4cb6fcd1976d7fa13ae9804` 等题的“董事不愿支付”依赖标题与截断正文合看；标题/正文边界应在数据中显式表示，人工审核时标出截断。现有 overlay 保留了模型建议，但这些题不得直接升级为正式 gold。
3. **IA 的 yes/no 基线未测。**`r_4742389fc407f133210c7756` 已改问原文特有评价，但四条 IA 均可能被顺从性偏差或模型记忆影响。正式攻击评分须在相同提示、预算和索引条件下报告 nonmember 的 Yes 率/假阳性率及成员-非成员差异；仅有 member Yes 率不能证明成员泄露。是否要求引用证据要在开发集比较后统一冻结，不能只对 IA 单独放宽服务行为。
4. **Masked 的精确恢复与语义合理不同。**`sparkling` 满足唯一遮蔽和选词约束；近义词仍应按预先定义的精确恢复主指标判错。可另列同义回答诊断及 JSON 解析失败率，但不事后修改主指标。
5. **模型审核不等于人评。**这 86 条只用于发现生成缺陷。T10 全量候选仍未正式复核；E07 双人评定和正式 gold 要按实验协议执行。

## 后续实施顺序

1. 在 D-dev 建短片段会话长度/文档选择试验，逐会话审核重复、事实支撑、家族符合度；明确采用的轮数和样本量损失，先登记台账 CHANGE 并更新协议，再生成全量新候选。不要将本 overlay 的 86 条直接外推到 A-cal/V/T。
2. 重写生成器：不再固定五轮追加句尾；跨文档按共享实体/事件选择且双证据；Masked 选唯一非数字词并同步答案；IA 避免整段原文和常识性事实；答案和证据在同一生成步骤绑定。新版本独立目录，保留旧 `candidate06`。
3. 新候选先做结构验证和 D-dev 模型预审，再由真人对正式 gold 做抽查/复核；冻结后才可做真实 RAG 工程回放、A-cal 阈值和正式 E01–E07。预审或工程回放结果不能写成防御有效性结论。
