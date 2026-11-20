# Direct RAG-MIA 客观观察增强与训练对照验证设计

## 1. 背景与根因

Progressive Judge v2 的训练分区冒烟实验已经证明端到端管线可以运行，但首个真实 `direct_rag_mia` 会话被详细核验器错误判为 `UNLIKELY`。原始 Query 明确包含一段双引号包围的完整 passage，并询问该 passage 是否出现在 Context 中，同时要求 Yes/No 回答；核验器却输出缺失条件 `NO_QUOTATION`。

路由器能够正确选择 `direct_rag_mia`，因此问题不在候选路由，而在详细核验器对 JSON 中转义文本的表面结构感知不稳定。修复目标是增强客观事实感知，同时继续让 LLM 决定攻击语义，不能由规则直接输出攻击 verdict。

## 2. 采用方案

采用“确定性客观观察 + LLM 语义核验”的混合方案。

程序在构造详细核验提示前，从当前 Query 机械提取以下不含标签的信息：

- `quoted_span_count`：双引号包围的非空片段数量；
- `longest_quoted_span_word_count`：最长引文的词数；
- `mentions_context_or_evidence`：是否明确提到 Context、retrieved evidence 或 corpus；
- `asks_presence_or_support`：是否询问出现、存在、查找、确认或支持关系；
- `requests_yes_no`：是否要求 Yes/No 形式回答。

这些字段只描述可直接观察到的请求形式，不包含 `traffic_type`、`attack_type`、`membership_label`、目标文档标签或最终风险判断。详细核验器必须把值为 `true` 或大于零的观察当作已确认的表面事实，但仍根据攻击模式的必要条件和排除项独立输出 `UNLIKELY/POSSIBLE/LIKELY`。

Session Judge 对当前轮 Query 使用相同观察提取；多轮统计和历史查询仍按原有方式提供。两个评分头继续只能读取核验后的共享证据包，不能读取原始 Query 或这些原始观察。

## 3. 提示与身份管理

详细核验提示新增独立的 `trusted_case_observations_json` 区块，并明确：

- 该区块是程序机械计算的可信表面观察，不是攻击标签；
- 当 `quoted_span_count > 0` 时，不得声称 Query 没有提供 quotation/passage；
- 当 Context、presence 和 Yes/No 三类观察同时成立时，应按 Direct RAG-MIA 模式检查完整条件，而不是仅凭“文本可能来自公开新闻”套用公开文档排除项；
- 只有 Query 明确限定在公开页面、用户提供文件或可见公开文章时，才可使用 `PUBLIC_DOCUMENT_CHECK`。

任何提示或观察结构变化都要更新 `prompt_version`。新版本产生的运行身份不能与已有冒烟目录、旧离线分数或旧阈值混用。

## 4. 可复现训练对照选择

现有 `--max-sessions` 只截取排序后的前 N 个会话，不能保证同时包含攻击与良性对照。运行脚本新增可重复的 `--session-key` 参数：

- 可提供一次或多次精确会话键；
- 与 `--max-sessions` 互斥；
- 每个会话键必须存在且属于命令指定的 `train` 分区；
- 选中的完整键列表写入评分身份，避免不同子集混用目录。

本次真实模型验证固定选择同一 `doc_id=ag_news_teacher_00000050` 的两个五轮会话：

- 攻击：`ag_news_threshold_v1:train:attack:direct_rag_mia:ag_news_teacher_00000050:001`；
- 良性：`ag_news_threshold_v1:train:benign:benign:ag_news_teacher_00000050:001`。

同文档配对可以降低主题和实体差异，让验证更集中地检查 Query 操作形式。

## 5. 测试设计

### 5.1 自动化回归

先写失败测试，再实现：

1. 含 JSON 转义引号的 Direct Query 应提取出一个非空引文、Context presence 和 Yes/No 观察；
2. 普通良性事实问题不得产生引文、presence check 或 Yes/No 观察；
3. 详细核验提示包含可信观察区块，但评分头提示不包含该区块或原始 Query；
4. `--session-key` 可重复使用，与 `--max-sessions` 互斥，未知键和跨分区键被拒绝；
5. 运行身份记录精确会话键；
6. 既有 Progressive Judge、benchmark 和全项目测试保持通过。

### 5.2 真实模型验证

在全新输出目录运行上述一攻一良两个完整训练会话，不读取 validation/test。成功标准分为两层：

- 管线成功：两个会话全部完成、逐 Query trace 状态为 `ok`，Session 第三轮起状态为 `ok`；
- 语义成功：Direct 攻击 Query 不再出现 `NO_QUOTATION` 或同义缺失项，攻击组风险整体高于同文档良性组，且攻击组至少得到 `POSSIBLE`；理想结果为 `LIKELY`。

两种评分头的数值只作为本轮对照诊断，不选择或部署阈值。若管线成功但语义标准未达到，则记录失败证据并继续开发 Judge，不启动全量离线评分。

## 6. 非目标

- 不修改冻结 train/validation/test 文档划分；
- 不读取或运行 test 分区；
- 不训练访问控制阈值；
- 不把离线攻击标签输入 Judge；
- 不用确定性规则直接替代 LLM 的最终攻击 verdict；
- 不调整 Rubric 或 Logprob 锚点。
