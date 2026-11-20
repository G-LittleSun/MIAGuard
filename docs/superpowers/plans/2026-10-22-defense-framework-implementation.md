# MIAGuard Defense Framework Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task in the current session. Steps use checkbox syntax for tracking. 不自动启动子代理；按用户授权的范围执行。

**Goal:** 建立可审计、可复现的在线证据访问控制与防御评测闭环。

**Architecture:** 在现有 Judge、网关、检索和攻击回放上增量接入。评分、策略、证据执行和评估各自独立，原冻结产物只读。当前状态以[进度台账](../../DEFENSE_PROGRESS_ZH.md)为准。

**Tech Stack:** Python 3.10/3.11、pytest、NumPy、scikit-learn、FAISS、现有模型客户端、JSON/JSONL/YAML。

---

执行基线：**v1.1 / 2026-10-31，D-dev 选择补记 2026-11-02，数据复用澄清 2026-11-04**。依据：[规格 v1.1](../specs/2026-10-22-defense-framework-design.md)、[实验协议 v1.1](../../DEFENSE_EXPERIMENT_PROTOCOL_ZH.md)。T01–T09 已完成；T10-C 的 D-dev 开发选择已完成，T10-D/T10-E 和 T11 正式指标未完成；T12–T18 未开始。当前恢复点为 [T10-D 下一轮 Goal](#t10-d-下一轮-goal)。各节“新增”描述任务的原交付范围，是否已经存在须结合[台账](../../DEFENSE_PROGRESS_ZH.md)及源码确认。

本文件是当前唯一有效的 T01–T18 主实施计划，后续直接在本文件更新步骤与复选框。两轮审核与开发 overlay 的证据见[第二轮处理决定](../../../reports/defense_v1/T10/REVIEW_TRIAGE_REV2_20261030_ZH.md)；该报告保存当时的判断，当前执行约束以本计划和协议为准。

2026-11-05 新增[统一版本总表](../../CURRENT_VERSIONS_ZH.md)：每次选择输入前核对用途、bank/split/index/model 和原 manifest；版本切换同步总表、选择清单及台账，不从旧默认配置或目录日期猜“最新”。文档修订/源码指纹不代表数据或实验验收。

## 执行约定

每次从台账的 next_task 接续。开始任务时写 IN_PROGRESS；每完成一个可验证步骤即勾选本计划并在台账追加事件。结束、失败或中断时更新下一步、命令、退出状态和产物。任务 DONE 要有验收证据；只写代码但未验证为 IN_PROGRESS。每项完成后同步项目状态/实验索引，涉及数据时同步数据目录。

当前工作目录无 Git 仓库（2026-10-22 `git rev-parse --show-toplevel` 返回失败）。不自动初始化，不伪造提交；使用任务文件清单与 SHA256 记录。未来已有 Git 时记录实际 commit，不能提交历史运行数据或无关文件。

实施前确认解释器。本次已确认以下文件存在，未据此声称依赖或测试通过：

```powershell
$taskPython = 'D:\ProgramData\Anaconda3\envs\MIAGuard\python.exe'
& $taskPython --version
& $taskPython -m pip check
```

各代码任务先添加下文指定的失败用例，运行该任务测试确认失败原因是缺失能力，再实现、重跑并检查相关回归。测试使用 fake 模型/小内存索引，live 模型调用仅在显式实验任务发生。不得以断言实现细节替代真实行为检查。

## 文件和接口约定

完整文件职责见规格第 3 节。新增测试文件逐任务列出。所有数据类放 `defense_contracts.py`，其他模块不得自建同名不兼容字段。线上 DTO 不含标签；离线 `labels.jsonl` 与请求分离。

核心契约示例（T02 实现；省略的日志字段依规格补齐，不改变这些字段语义）：

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class OnlineRequest:
    request_id: str
    session_id: str
    query: str
    allowed_doc_ids: frozenset[str] | None = None

@dataclass(frozen=True)
class RiskEstimate:
    x1: float | None
    x2: float | None
    fused_score: float | None
    risk_source: str
    status: str

@dataclass(frozen=True)
class Evidence:
    doc_id: str
    parent_doc_id: str
    text: str
    score: float
    kind: str = 'raw'
```

benchmark CLI 已支持 `--experiment-spec`、`--output-root`、`--resume`；同身份恢复和禁止覆盖规则按实现检查。`--validate-only`、`--freeze-manifest` 是 T16 待交付接口，当前不可执行。评估 CLI 当前必须给 `--run-dir`、`--output`，仅支持 `--analysis-role engineering_only`。所有脚本先 `--help` 检查参数；当前可用命令与未来接口分列于文末。

## P0：冻结 Judge 在线 observe

### T01 环境、身份与基线快照

依赖：无。修改文件：无业务代码。产物：`reports/defense_v1/T01/environment.json`、`baseline-tests.txt`、`input_hashes.json`。记录 Python、依赖、正式 train manifest/冻结模型/相关源代码 SHA256，保持原数据只读。

- [x] 执行解释器与依赖检查，记录现有失败，不能无关升级依赖。
- [x] 运行以下已有回归并保存完整输出及 `$LASTEXITCODE`；预期无新增失败，不预填通过数。

```powershell
& $taskPython -m pytest tests/test_progressive_judge.py tests/test_judge_score_frozen.py tests/test_two_stage_gateway.py tests/test_defense.py tests/test_session_store.py -q
```

- [x] 用 Python hashlib 记录冻结模型、train manifest、划分文件与本次涉及源代码的 SHA256；确认新输出目录不覆盖已有运行。
- [x] 写入台账 T01 结果及基线失败的归属；非本任务导致的失败也保留，影响门禁的先解决。

验收：环境与基线证据可读，原冻结文件哈希未变。下一任务 T02。

### T02 输入契约与 Judge trace 适配

依赖：T01。新增 `src/miaguard/defense_contracts.py`、`online_judge_adapter.py`；新增 `tests/test_online_judge_adapter.py`。定义 `trace_to_risk(trace, head)`，返回兼容 `RiskResult` 与 trace 引用；`head` 仅 logprob/rubric，score 分别取 `trace.logprob.score/trace.rubric.score`。

- [x] 编写 fake trace 测试，rubric=0.8、logprob=0.2，断言两头不混用；未知 head、NaN、越界分数必须报错。
- [x] 添加 `insufficient_history` 和异常 trace 用例，状态保留，不能被当作有效零风险；检查 OnlineRequest 不含四个真值字段。

```python
from dataclasses import fields
assert {f.name for f in fields(OnlineRequest)}.isdisjoint(
    {'intent_label', 'membership_label', 'attack_type', 'target_doc_id'}
)
assert trace_to_risk(trace, 'logprob').score == 0.2
assert trace_to_risk(trace, 'rubric').score == 0.8
```

- [x] 运行 `& $taskPython -m pytest tests/test_online_judge_adapter.py -q` 确认缺失行为，然后实现选头、状态和 trace 留存；疑似机制从现有 trace 证据读取，不能读真值。
- [x] 同命令通过后连跑 `tests/test_progressive_judge.py`，记录结果与变更哈希。

验收：分数、证据、时延、状态均可溯源，无标签注入路径。

### T03 冻结融合与身份校验

依赖：T02。新增 `src/miaguard/frozen_risk_scorer.py`、`tests/test_frozen_risk_scorer.py`。定义 `FrozenRiskScorer.from_file(path, expected_head, expected_sha256)` 和 `score(x1, x2)`。

- [x] 测试错误 head、错误特征顺序、错误 SHA、非有限系数、缺阈值、x2=None 均不进入双分数计算。
- [x] 用以下独立数值参照写断言，对网格 0/0.5/1 组合与已有评估函数比较，绝对误差 ≤1e-12。

```python
from math import exp
z = coefficient[0] * x1 + coefficient[1] * x2 + intercept
expected = 1 / (1 + exp(-z))
assert abs(scorer.score(x1, x2) - expected) <= 1e-12
```

- [x] 运行 `& $taskPython -m pytest tests/test_frozen_risk_scorer.py -q` 确认失败，然后实现稳定 sigmoid 和启动身份验证，禁止 fit。
- [x] 同命令及 `tests/test_judge_score_frozen.py` 通过后记录模型哈希与结果。

验收：仅加载旧模型，无新训练或阈值变化。

### T04 Query-only 工作点与失败分支

依赖：T03。新增 `src/miaguard/query_only_calibration.py`、`scripts/calibrate_query_only_defense.py`、`tests/test_query_only_calibration.py`。读取已校验的正式 train 评分，按文档平衡汇总候选阈值；默认检测良性 FPR 上限候选为 1%/5%，这是开发工作点，不是部署保证。

  - [x] 写测试：拒绝 validation/test 输入；所有候选含“不触发”阈值；同分数 tie 使用 `score >= threshold` 统一处理；无正常样本时不输出阈值。
  - [x] 实现候选选择：在满足训练良性 FPR 上限的阈值中，最大化四攻击宏召回；并列取较高阈值。保存样本数、分文档区间与选择规则；低样本区间不满足上限时显式标 empirical_only。
  - [x] 为运行分支增加测试：x1 有效+x2 缺失→query_only；x1 有效+x2 错误→query_only/session_error；x1 错误→error；enforce 的 error→unavailable，observe 的 error→allow。

```python
assert classify_source(x1_ok=True, x2_ok=False) == 'query_only'
assert classify_source(x1_ok=False, x2_ok=True) == 'error'
```

`classify_source(*, x1_ok, x2_ok)` 是本任务在 `frozen_risk_scorer.py` 新增的纯函数。

  - [x] 运行 `& $taskPython -m pytest tests/test_query_only_calibration.py tests/test_frozen_risk_scorer.py -q`，然后仅在 train 产生 `reports/defense_v1/T04/query_only_thresholds.json`。
  - [x] 登记分数分布、阈值和限制；原融合 JSON 哈希必须不变。

验收：缺 x2 不伪造 0，错误与正常低分分离。

### T05 网关 observe 接入与小样本在线核对

依赖：T04。修改 `two_stage_gateway.py`、`defense.py`；新增 `configs/defense/defense_v1_observe.yaml`、`scripts/run_defense_observe.py`、`tests/test_defense_v1_observe.py`。通过可选注入新 scorer/策略，旧构造默认行为保持原样。

  - [x] 添加 disabled 不调用 Judge、observe 高风险仍使用完整原上下文、前两轮 Query-only、第三轮融合、未知状态回退的集成测试。
  - [x] 添加同一保存 trace 在线/离线数值一致测试；live Judge 重跑差异写专门字段，不以精确复现强制通过。
  - [x] 实现配置绑定 frozen 路径/哈希、head、window=5、min_session_queries=3、每轮评估；建独立运行 manifest，不覆盖旧 YAML。
  - [x] 运行 `& $taskPython -m pytest tests/test_defense_v1_observe.py tests/test_two_stage_gateway.py tests/test_defense.py -q`。
  - [x] 创建仅含旧 train 代表性会话的 `reports/defense_v1/T05/observe_spec.json`，运行新 observe CLI；记录全部状态、调用次数和 p50/p95。该文件绑定模型、Prompt、请求路径、head、冻结产物、阈值路径、partition=train。

```powershell
& $taskPython scripts/run_defense_observe.py --experiment-spec reports/defense_v1/T05/observe_spec.json --output-root data/defense_v1_runs/p0-observe-20261022-01
```

日期为命名示例，执行时用当日及递增序号；重名不得覆盖。验收 G0：离线计算一致、observe 不改生成输入、live 成本已测。

## P1：证据访问动作闭环

### T06 允许范围、目标过滤与回填

依赖：T05。修改 `vector_store.py`；新增 `evidence_access.py`、`tests/test_evidence_access.py`。扩展 `search(query, top_k, *, allowed_doc_ids=None, excluded_parent_ids=frozenset())`，保留旧二参数调用；先允许后排除，按原分数排序返回。

  - [x] 用 fake embedding/小内存索引写用例：最高目标被过滤后低排名补足；空允许集合返回空；None 全允许；同 parent 的所有片段排除；无足够候选返回短缺。

```python
hits = store.search('q', 2, allowed_doc_ids={'a', 'b', 'c'},
                    excluded_parent_ids=frozenset({'a'}))
assert [h['document']['doc_id'] for h in hits] == ['b', 'c']
assert store.search('q', 2, allowed_doc_ids=set()) == []
```

  - [x] 先运行失败测试，再实现倍增候选扩展直到足够或允许库耗尽，去重并保持排名；相似度特征只能来自允许范围。
  - [x] 运行 `& $taskPython -m pytest tests/test_evidence_access.py tests/test_defense.py -q`；验证索引内容及哈希未修改。
  - [x] 记录检索前后 ID、回填次数、短缺原因的示例产物。

验收：无禁止文档回填、无永久索引变更。

### T07 单一动作执行器

依赖：T06。修改 `evidence_access.py`、`defense.py`、`defense_experiment.py`；新增 `tests/test_defense_action_executor.py`。定义 `execute_action(action, candidates, target_parent_ids, retrieve, summarize)`；返回实际 Evidence、applied_action、status、原因。

  - [x] fake 生成器捕获完整 prompt，验证 allow/full、hide/refill、no_context/empty、deny/不调用生成器、summary/只送实际摘要；禁止下游二次摘要。
  - [x] 添加 summary 超时→no_context、空候选、不支持动作直接错误用例。旧 `summarize_context` 映射 sanitized_context，仅新路径使用新契约。

```python
assert execution.applied_action == 'sanitized_context'
assert [item.kind for item in execution.evidence] == ['summary']
assert generator_prompt.count('原始敏感片段') == 0
```

  - [x] 先跑失败用例，再实现五动作及统一异常回退，模板版本写 manifest。
  - [x] 运行 `& $taskPython -m pytest tests/test_defense_action_executor.py tests/test_defense.py tests/test_ia_policy_experiment.py -q`。

验收：已建议/已执行动作分开，实际上下文可复核。

### T08 暴露账本与会话提交

依赖：T07。新增 `exposure_store.py`、`tests/test_exposure_store.py`；局部修改 gateway/runner 的提交点。定义 `begin(request)`、`record_attempt(request_id, evidence)`、`complete(request_id, response)`、`fail(request_id, reason)`、`history(session_id)`。

  - [x] 测试同 ID 同输入重试不增预算；同 ID 不同输入报错；不同 session 隔离；过期重置记录；生成失败保留已交付证据尝试。
  - [x] 测试隐藏目标不计原文交付，摘要记 transformed；现有 Judge 继续读取控制前检索轨迹。

```python
assert len(store.history('session-a')) == 1
assert store.history('session-b') == ()
assert event['retrieved_doc_ids'] != event['delivered_doc_ids']
```

  - [x] 实现单 session 顺序执行；commit 在回答或明确失败后发生。新请求数与重试次数分列，不因重试重复改变策略。
  - [x] 运行 `& $taskPython -m pytest tests/test_exposure_store.py tests/test_session_store.py tests/test_two_stage_gateway.py -q`。
  - [x] 运行 fake 完整请求检查 G1：标签隔离、动作执行、状态隔离、回退和证据链全部通过。

## P2：数据、指标与固定策略筛选

### T09 统一回放、分片和身份校验

依赖：T08。新增 `defense_benchmark.py`、`scripts/run_defense_v1_benchmark.py`、`tests/test_defense_benchmark.py`。定义 `run_benchmark(spec_path, output_root, resume=False)`；用现有四攻击评分逻辑，所有问题经过同一服务接口。

  - [x] 测试分片中断续跑、已完成不重复、身份改变拒绝 resume、failed/skipped 计数、攻击标签只在离线评分连接、不同方法状态隔离。
  - [x] 实现 manifest 原子写与会话分片；完成摘要包含 expected/completed/failed/skipped/coverage，保留 raw answer 和实际输入引用。

```python
assert summary['expected'] == (summary['completed'] +
                               summary['failed'] + summary['skipped'])
assert summary['status'] != 'completed' or summary['skipped'] == 0
```

completed 允许有已报告失败请求，另设 outcome=valid/invalid；不能把“运行结束”当“有效防御”。

  - [x] 运行 `& $taskPython -m pytest tests/test_defense_benchmark.py tests/test_query_bank_two_stage_integration.py -q`。
  - [x] 以 fake 模型完成 B0/B2/B3/B5 的小型链路；产物接口按实验协议 §2。

### T10 新数据契约、划分和困难正常集

依赖：T09。现有实现为 `src/miaguard/defense_dataset.py`、`scripts/build_defense_v1_dataset.py`、`scripts/export_defense_v1_review_packet.py`、`scripts/verify_defense_v1_dataset.py`、`tests/test_defense_dataset.py`；开发 overlay 构建脚本为 `scripts/build_t10_review_overlay.py`。新数据另建目录，不能重命名旧 test。以下 A–E 是 T10 的子步骤，不增加 T01–T18 的任务总数。

- [x] 测试同 parent/近重复组不得跨 D-dev/A-cal/V/T，空白答案、缺证据、不可回答标注矛盾、member/nonmember 混淆被拒绝。证据见 T10 单测与 `validation.json`。
- [x] 实现请求、标签、答案/证据、group ID 分离；新数据与历史目标/Prompt 模式文件做重叠审计。重复组算法版本与阈值写候选 manifest。Prompt 审计目前只覆盖整篇规范化包含关系，片段级人工复核尚需完成。
- [ ] 按实验协议准备七类正常任务和四攻击；优先核对旧 train 可复用范围，再补充缺失任务、标注或新保留数据。自动候选仍 `review_status=pending`。D-dev 两轮 86 条模型预审及独立核验完成，详见[第二轮接收与开发决策](../../../reports/defense_v1/T10/REVIEW_TRIAGE_REV2_20261030_ZH.md)；T10-C 开发轮数设计已选，正式 gold 和真人复核尚未完成。无需为开发联调先把四类攻击全量重生成，正式质量/攻击结论仍须按门禁验收。

```python
for left, right in [('D-dev', 'A-cal'), ('D-dev', 'T'), ('V', 'T')]:
    assert groups[left].isdisjoint(groups[right])
```

实现应校验所有两两分区，不限示例三组。

- [x] 运行 `& $taskPython -m pytest tests/test_defense_dataset.py -q`，生成新 manifest/overlap_audit/split；原目标池规模不足，改用冻结 120,000 篇 processed corpus 建新索引；候选和人工待复核项已登记数据目录。T10 整体仍 IN_PROGRESS。

#### T10-A 数据与索引基础（DONE）

- [x] 记录 candidate06 的 3,600 个目标、900 个共享背景及四个隔离索引，依据为[候选验证](../../../reports/defense_v1/T10/validation.json)。1,750/14,400 条是已生成草稿数量，不是下一版必须凑齐的合格题数。

#### T10-B 两轮模型预审与答案同步（DONE，仅工程子步骤）

- [x] 保存两轮原始审核，第二轮 70 正常/16 攻击的文件契约已独立核验；三条跨文档双篇证据与两条 Masked 缺词已在[独立开发 overlay](../../../data/defense_datasets/defense_access_v1_pilot_overlay_rev2_20261030/manifest.json)同步，[工程验证](../../../data/defense_datasets/defense_access_v1_pilot_overlay_rev2_20261030/validation.json)通过。仍全部 pending，无人工 gold，不代表剩余题或整个会话质量通过。

#### T10-C D-dev 会话轮数与文档选择（DONE：仅 D-dev 设计验收）

输入：candidate06 的 D-dev 原文、第二轮审核和独立 overlay；只按 D-dev 结果选择规则。读原文以核对事实，不使用 V/T 回答效果或攻击标签筛选问题。

原始试点：[session_length_pilot_20261031_01](../../../reports/defense_v1/T10/session_length_pilot_20261031_01/pilot_manifest.json)。2026-11-02 已接收独立模型预审并建立[修订试点 rev2](../../../reports/defense_v1/T10/session_length_pilot_rev2_20261102_01/manifest.json)；[处理决定](../../../reports/defense_v1/T10/REVIEW_TRIAGE_T10C_20261102_ZH.md)记录四处局部修订。后续已选定 D-dev 开发队列，见台账 L074；正式数据轮数与内容仍未定稿。

- [x] 清点原 14 个正常会话与其证据，逐篇记录来源、原文哈希、截断/标题边界、候选事实和跨文档配对关系；见[会话清点](../../../reports/defense_v1/T10/session_length_pilot_20261031_01/session_inventory.jsonl)。候选事实由 Codex 开发审阅，不是人工 gold；字数不能自动证明事实数量。
- [x] 对原 14 个会话分别尝试 2/3 轮：14 个两轮草稿、12 个三轮草稿，另有 2 个三轮因缺少可区分事实而排除；旧 5 轮已记录诊断意见。每轮标注候选新信息；草稿质量与排除是否合理仍须独立复核，不能将这些数量当作合格数。
- [x] 分别保留同源轮数比较和扩展文档 cohort；选定[开发基础队列](../../../reports/defense_v1/T10/session_length_dev_cohort_20261102_01/manifest.json)七类各 4 个两轮会话，扩展组每类覆盖至少 2 个不同来源会话。候选来自模型/agent 预审，不是已验证的人类 gold；正式来源分布与排除比例在 T10-D/E 继续核查。
- [x] 建立两个相反焦点的三轮正常会话作为开发诊断；它们只代表同一个来源依赖组。本地模型[固定来源对照](../../../data/defense_v1_runs/t10c-context-focus-20261102-01/agent_diagnostic_summary.json)中有历史时两个焦点各答对，无历史时对相同问题两次均猜 Friday。仅满足小样本工程诊断，不证明实际 Session/fusion；T10-D 必须尝试多个独立来源组或缩减结论。
- [x] 独立模型预审的 70 条意见已[核验](../../../reports/defense_v1/T10/review_validation_t10c_20261102.json)，针对四处改写、8 个证据不足版本及两个替换版本由 Codex agent 做[14 条小样本审核](../../../reports/defense_v1/T10/session_length_pilot_targeted_20261102_01/adjudication.jsonl)。连续三轮不答与原弱配对未纳入基础队列；保留原因与改写记录。不是人工 gold，正式数据逐条审核留给 T10-E。
- [x] 形成[D-dev 选择报告](../../../reports/defense_v1/T10/session_length_dev_cohort_20261102_01/selection_report.json)：基础 28 会话/56 问，附加 2 个三轮会话/6 问；来源 31 篇，基础依赖 27 组、保守敏感性 23 组，均非已证明独立样本数。[七组历史对照](../../../data/defense_v1_runs/t10c-history-ablation-20261102-01/agent_diagnostic_summary.json)和[焦点对照](../../../data/defense_v1_runs/t10c-context-focus-20261102-01/agent_diagnostic_summary.json)均为本地 Q4 工程诊断；未测 Judge `risk_source`。台账 L070/L072/L074 和协议已记录开发选择、共享背景限制与正式结论边界。

验收结论：D-dev 开发设计与来源/ID 结构已验收，保留真人 gold、事件级依赖及多来源三轮覆盖作为 T10-D/E 未完成工作；不将模型 accept 或本地诊断写成正式质量/防御效果。T10 整体仍 IN_PROGRESS。

#### T10-D 数据复用、缺口补齐与新候选（IN_PROGRESS；当前 next_task，依赖 T10-C）

**当前先做：定位候选和已见6题试跑完成；固定独立来源与库外、正常题样本验证定位、回退和效用，再补摘要检查及多来源三轮。具体顺序和验收见下方 2026-11-11 执行清单。** [选择清单](../../../reports/defense_v1/T10/legacy_reuse_selection_20261104.json)固定 `ag_news_queries_v2` / `ag_news_threshold_v2`，共 4,579 条 train 查询；[版本与字段核验](../../../reports/defense_v1/T10/query_bank_version_audit_20261104.json)通过但[自动结构审计](../../../reports/defense_v1/T10/v2_train_reuse_audit_20261105_01/summary.json)已完成，语义/gold/适配未验收。此前 v1 的 3,575 条盘点仅保留历史依据，Judge/E00 原 v1 结果不得改名。详细角色见[数据复用规则](../../DEFENSE_DATA_REUSE_ZH.md)。

- [x] 自动逐条核查 v2 train 问题与旧原文/索引/成员身份、四攻击结构评分输入及会话布局，输出工程处置和原因。[审计报告](../../../reports/defense_v1/T10/v2_train_reuse_audit_20261105_01/REUSE_REPORT_ZH.md)、[独立验证](../../../reports/defense_v1/T10/v2_train_reuse_audit_20261105_01/validation.json)覆盖全部 4,579 条；仅结构子步骤完成，不是逐条语义或 gold 验收。
- [x] 接收并核验266单元预审；[接收报告](../../../reports/defense_v1/T10/v2_reuse_review_integration_20261105_01/INTEGRATION_REPORT_ZH.md)记录IA6条本地改写/5条暂缓、Masked60方案结构修复及说明补正，形成[362条待审攻击层](../../../data/defense_datasets/legacy_v2_reuse_overlay_20261105_01/manifest.json)。仅工程接收/暂存完成，非语义或gold放行。
- [x] 固定4条v2正常题的agent必要事实/证据及8攻击输入，锁定12题独立小批和运行身份，完成24/24真实B0/B2工程试跑；见[试跑报告](../../../reports/defense_v1/T10/fast_live_pilot_20261105_01/FAST_PILOT_REPORT_ZH.md)。仅覆盖这批，未放行全量gold。
- [x] Masked严格分与格式/恢复数量独立记录，同批B5/B6已完成。追加[排名压力测试](../../../reports/defense_v1/T10/rank_stress_20261109_01/REPORT_ZH.md)，核查旧24条与新18条生成证据，定位了Top-1误删和摘要保留待填词实例。
- [x] 完成4正常题强制过滤配对与排名压力题B2/B3同题对照，分别8/8与12/12；[强制过滤报告](../../../reports/defense_v1/T10/forced_normal_diagnostic_20261111_01/REPORT_ZH.md)、[B2/B3报告](../../../reports/defense_v1/T10/rank_stress_20261109_01/CONSERVATIVE_B2_B3_20261111_ZH.md)。

**2026-11-11 执行清单，T10-D 当前优先级**

**用户确认的类型驱动策略方向，当前先验证接口和数据，T14实现完整动态策略**

2026-11-13 开发候选检查点（T10-D）

- [x] 核验旧 live 记录及输入摘要，盘点四类攻击的类型输出、风险触发与错分。[审计 JSON](../../../reports/defense_v1/T10/type_policy_trace_audit_20261113.json)
- [x] 将完整在线类型和证据接入 B_TYPE_V1，测试低风险、空类型、多类型、查询/会话失败、第三轮、允许范围及定位回填失败。实测 65 项相关测试通过，见台账 L164、L167。
- [x] 冻结 27 问 / 23 会话的工程题单，包含两组实际三轮会话。[题单清单](../../../data/defense_datasets/type_policy_v2_train_20261113_01/manifest.json)
- [x] 四方法真实配对 108/108 完成，审计动作、交付、正常质量和运行开销。按首轮 Masked 残留恢复问题建立 B_TYPE_V2，同题复跑 54/54 完成。[中文汇报](../../../reports/defense_v1/T10/TYPE_POLICY_PAIRED_20261113_ZH.md)
- [ ] T10-D 后续补独立来源的多轮 IA 和困难正常题，并准备 T10-E 实际人员审核。
- [x] 以冻结 Judge 和原索引完成 18 个困难正常候选预筛，在回答生成前固定 14 问、两组三轮及必要证据。[题单](../../../data/defense_datasets/benign_pair_v2_train_20261113_01/manifest.json)
- [x] B0、B2、B_TYPE_V2 真实配对 42/42。B2 拒答子组 V2 保留证据且答对 0/3，定位到两次固定拒答和一次移除必要来源。[汇报及原始证据](../../../reports/defense_v1/T10/TYPE_POLICY_PAIRED_20261113_ZH.md)

2026-11-13 40分钟补充任务（T10-D，工程诊断）

- [x] 固定4个IA来源的三轮序列和两组正常控制，共18问；另固定相同问题的逐题新会话条件。核对v2 train、原索引和生产源码身份。[三轮清单](../../../data/defense_datasets/multiturn_ia_session_v2_train_20261113_01/manifest.json)、[重置清单](../../../data/defense_datasets/multiturn_ia_reset_v2_train_20261113_01/manifest.json)
- [x] 主对照B0/B2/B_TYPE_V2完成54次真实请求，V2逐题重置18次，已核查实际Session/fusion、历史交付和动作差异。[结果](../../../reports/defense_v1/T10/SUPPLEMENT_RESULTS_20261116_ZH.md)。重置同时去除两种状态，不作为纯Session组件消融。
- [x] 对Treo/Ace/Oklahoma三个已见正常失败做独立agent证据核查，记录授权未知与此前答案暴露，仍非真人gold。
- [x] 冻结三案原填空与相同事实普通问句的6个独立会话，原文支持和摘要已核验。[题单](../../../data/defense_datasets/benign_style_pair_v2_train_20261113_01/manifest.json)
- [x] B0/B2/V2共18个请求事件问法对照完成，记录检索、动作与agent事实核对。[结果](../../../reports/defense_v1/T10/SUPPLEMENT_RESULTS_20261116_ZH.md)。
- [x] 汇总逐请求配对结果、限制与下一步，并同步状态/数据/实验/版本入口；正式门禁不变。

##### 2026-11-17 已确认的接续顺序

当前执行顺序见本节下方 [T10-D 下一轮 Goal](#t10-d-下一轮-goal)。以下复选框同时保留已交付的历史记录。

- [x] 测试并接入两个多动作开发候选，保留V2：高风险单一S²分别摘要与无上下文，77项相关测试通过。摘要处理器接触允许范围的原文，须核验输出内容。
- [x] 冻结43问/7方法开发题单，新增两道受限来源的证据不足问题；[manifest](../../../data/defense_datasets/multi_action_v2_train_20261117_01/manifest.json)。
- [x] 301事件主对照与工程审计完成，正常题及摘要内容由agent复核；[报告](../../../reports/defense_v1/T10/MULTI_ACTION_REPORT_20261117_ZH.md)。不是人工gold。
- [x] 联合补充来源，完成四类攻击统计及候选比较：没有证据选出全面优胜候选；正式门禁保持待验收。[报告](../../../reports/defense_v1/T10/MULTI_ACTION_REPORT_20261117_ZH.md)
- [x] 在候选结果可见前固定19问扩展攻击题单，四类均有库内及库外来源。[清单](../../../data/defense_datasets/multi_action_sources_v2_train_20261117_01/manifest.json)
- [x] 主运行结束后串行执行95次扩展对照（95/95，0失败），保留历史开发来源标记，比较各候选安全/效用；未宣称候选全面优胜。

- [x] 两小时开发对照已冻结41请求，包含四类攻击及14正常候选，来源和局限见[manifest](../../../data/defense_datasets/two_hour_paired_v2_train_20261117_01/manifest.json)。
- [x] 完成 B0/B2/B_TYPE_V2 真实配对123事件，输出四类开发诊断及正常质量表。[报告](../../../reports/defense_v1/T10/TWO_HOUR_PAIRED_REPORT_20261117_ZH.md)。不足条件的指标未评估，正式门禁继续待办。

- [x] **T10-D 复核已有日志。** 已交付[两张逐题复核表](../../../reports/defense_v1/T10/NEXT_STEP_CASE_AUDIT_20261117_ZH.md)。下一批优先验证两项：限制前的目标原文交付是否能减少，以及高风险正常题是否能保留必要证据并答对。风险误报需结合题目与权限审核。
- [ ] **T10-D 再固定独立来源及题单。** 开发诊断使用冻结 Judge v3、v2 train 和原索引。复用适用数据，按缺口补题；在看新回答前固定独立来源组，覆盖 Direct、S²、Masked、IA 的库内与库外目标、真实多轮 IA、常规与困难正常题。核对已用于开发的文档或事件重叠、索引和成员身份，保留可回答性和必要证据。新保留集按实验协议验收。
- [ ] **随后完成 T10-E、T11 和 T12，按协议推进独立终测。** 主配对使用 B0 无防御、B2 高风险统一拒答、B_TYPE_V2 类型策略，控制题目、索引、生成模型、检索设置和请求预算，B2/V2 共用同一冻结 Judge 和阈值。B3 和 B6 可用作辅助动作对照。以分类型成员推断指标和正常题正确且有必要证据的比例为主，另记证据交付、限制、合理不答和延迟。报告按来源分组的配对差值及置信区间。

##### T10-D 下一轮 Goal

目标：在真实模型配对实验中验证一版新的访问控制候选，优先解决低风险漏检、IA 首轮原文交付和正常问答失去必要证据。以 [396 次开发对照报告](../../../reports/defense_v1/T10/MULTI_ACTION_REPORT_20261117_ZH.md)及两份运行清单为起点。上一轮两个候选缺少全面优于 V2 的证据。

- [x] **固定数据和判定规则。** 47问及四方法清单、审计和限制见 [manifest](../../../data/defense_datasets/next_goal_v2_train_20261117_01/manifest.json) 及 [运行前登记](../../../reports/defense_v1/T10/next_goal_prereg_20261117.json)。历史失败案例用于调试，历史正常题回归与新攻击目标分组；不等同独立终测。
- [x] **开发最小候选与消融。** 从 `src/miaguard/defense_benchmark_live.py`、`query_cue.py`、`two_stage_gateway.py`、`exposure_store.py` 和 `evidence_access.py` 核对现有执行路径。先用历史日志判断四个漏检来自哪段。候选的前置判断只使用在线信号和可信权限，先验证强线索及正常填空的边界，避免整体下调阈值或见到填空就拒答。为首轮无历史与后续多轮分别定义规则：首轮依据当前证据和风险限制，后续可基于风险和实际交付记录升级。对被误干预的正常题，检验能否使用允许范围内的替代证据回答。保持 V2 版本可复现，为新策略单独登记配置和版本。机制较多时用小批消融区分前置风险规则与会话规则的贡献。摘要降精度继续作为历史对照，并在启用时审计处理器输入和敏感事实。离线目标、成员标签和参考答案只供评分。针对失败分支、会话隔离、权限及正常查询回归编写必要测试并运行。
- [x] **完成真实配对与质量复核。** 同题比较 B0 无防御、B2 风险触发后统一拒答、B_TYPE_V2 与新候选。保留所选与实际动作、风险来源和类型、过滤/回填状态、处理器输入、实际交付、回答及延迟。运行时使用新目录和完整 manifest。中断时核对身份与已完成会话后恢复。按证据核对正常回答和必要事实，对证据不足题单记合理不答。若已有足量可复用题，则直接开展开发比较，真人审核可独立准备。
- [x] **汇总三张表并作选择。** 风险表记录覆盖分母、四类触发与类型命中、正常触发和 Query-only/融合；样本、评分适用时附 AUROC/F1。防御表按类型、成员身份、预算和来源记录目标原文/事实保留、Masked 恢复、拒答/未知/解析失败及 IA 首次交付和限制轮次。现有固定评分适用时给描述性 AUROC；独立校准后才给固定阈值 TPR/FPR。正常表记录有证据的正确率、证据不足时合理不答、正常干预和延迟 p50/p95，按常规与困难题拆分并逐题定位损失。对照 V2 写同题新增/减少和来源级配对差值，样本允许时给区间。开发筛选至少要求针对已记录短板出现改善、无新增目标原文交付，且无原本有依据的正常正确答案退化。任何达不到约束或出现输出信号恶化的情况均须报告；无可行候选时保留 V2，并交付可复核的失败分析。
- [x] **交付报告与审核包。** 提交运行命令、代码/数据/模型身份、可复核结果、三张表及成功和失败案例。同步台账、主计划、项目状态和实验索引。新增数据或版本时同步数据目录和总表。在准备正式 T10-E 时交付带原文、参考事实、判定表和待审数量的真人审核包，按实验协议保持正式校准及终测为待验收。下一轮 Goal 的完成条件为候选实现、测试、真实开发对照、报告和文档记录均已核验，候选是否达标由数据决定。


##### 类型策略历史清单

- [ ] 盘点现有Query/Session trace中的疑似类型、证据、状态及首轮/多轮可用性；建立在线白名单和日志契约，禁止离线 `attack_type`、目标真值、成员标签进入选择器。区分模型预测与真实标签，类型分数无校准依据时不称为类型概率。
- [ ] 对Direct、S²、Masked、IA分别列出候选动作、适用前提和验证指标；统一处理正常/低风险、高风险未知、多类型及判断失败。可信权限约束优先；用户自述的公开/学习用途不是权限证明。先复用现有数据及动作，保留B0/B2/B3/B5/B6/B5_LOCATED/B5_CUE为对照，未完成新策略前不声称类型驱动效果。
- [ ] 用已有小批离线核查类型预测是否可进入决策且不使用真值，再补不同来源、正常困难题及三轮会话；评估分类型检测、动作、定位、正常正确性、证据暴露和成本，记录空类型和类型错误。不得根据历史test调策略。
- [ ] T14实现并验证按在线类型/风险/定位/暴露选择动作的独立版本；增加多候选、未知、类型冲突、缺失和错误回退测试，记录选择理由和实际交付。正式实验继续满足T10-E/T11及协议门禁。


- [x] 完成4非成员与4正常阅读题的24次工程对照，发现1个新增线索拒答而原策略可答的公开阅读练习；[报告](../../../reports/defense_v1/T10/CUE_UTILITY_NONMEMBER_20261111_ZH.md)。正常性与授权边界待人工确认。
- [ ] 优先设计更细的线索分支，在预先固定的可回答正常题和成员/非成员上共同验证，比较准确性、拒答和泄露表现；现有版本保留对照，不将公开练习案例直接外推。

- [x] 查询线索候选 `query_cue_v1` 与 B5_CUE 已完成train静态盘点、28项相关工程测试和10题真实试跑，详见[结果](../../../reports/defense_v1/T10/QUERY_CUE_PILOT_20261111_ZH.md)；独立来源与困难正常题验证仍未完成。

- [x] 不同于前两批的6个文档ID完成四方法24/24工程对照；3条未触发均在初筛跳过细查，[结果与限制](../../../reports/defense_v1/T10/LOCATOR_NEW_SOURCES_20261111_ZH.md)。
- [ ] 优先复核这三条的初筛与评分路径，在开发集准备版本化候选修复并比较困难正常题代价；原冻结Judge和阈值保留历史身份，不使用历史test调参。

- [x] 连续三词定位候选和已有6题真实工程试跑已完成，26项相关测试通过；[报告](../../../reports/defense_v1/T10/rank_stress_20261109_01/LOCATOR_PILOT_20261111_ZH.md)。独立来源、库外和触发正常题仍需验证，下方相关任务保持未完成。

- [ ] 设计版本化定位候选，输入仅限在线请求、检索候选及可用授权信息；输出候选 parent、证据及定位不确定状态。离线来源或成员标签只用于评估。保留原B5 Top-1独立基线；不确定时测试固定拒答等回退，不把回填后的位置当成定位真值。
- [ ] 按项目测试流程先验证正确定位、排名非第一、无候选、多候选、parent去重及回填，检查补入材料不会重引入被排除parent。记录测试命令和结果。
- [ ] 固定同一开发题单后比较B0、旧B5、新定位候选和B2；逐题记录风险、定位、排除与交付、生成内容、完成数和延迟；风险触发、成员标签与证据验证相互独立。已看过的案例用于开发诊断，另外预先固定独立来源案例评估泛化。
- [ ] 补充正常题可回答性、必要事实和证据，分别报告自然触发与强制动作；补独立来源的三轮会话并核验实际使用Session/fusion的记录。不得将人工强制过滤计入自然误拦率。
- [ ] 完成定位对照后，试验摘要输出中具体事实和原文片段的检查以及失败回退；分别记录摘要器输入、最终生成器输入和回答。检查结果、策略和规则须版本化，按实验结果决定后续采用。
- [ ] 工程比较报告分别给出目标原文交付、逐词恢复、格式/拒答/解析失败、正常事实正确性与证据、定位错误、延迟及失败分母。小样本只报告实际计数和明确范围；正式gold、T11和E01门禁不变。

- [ ] 扩充正常语义和IA未知/拒答等正式评估依据。准备定位与摘要候选对照，增加不同来源的三轮会话及触发限制的困难正常题。
- [ ] 根据实际缺口再处理144暂缓IA及其余语义/Masked警告、会话自然度和接口；正式gold与来源审计保持待办，不阻止满足条件的小批工程试验。不能将accepted或agent建议当人工gold。
- [x] 固定小批已显式绑定v2 bank/split、原索引、原BF16与冻结阈值，完成运行前/后摘要核验及真实联调；正式E01/门禁依赖保持不变。
- [ ] 基于已核实的复用范围确定新增查询和人工审核预算；优先补充七类正常任务、多来源三轮和不足的攻击评分依据。candidate06 与现有 D-dev 产物继续保留，新保留集另行验收；旧 validation/test 不转换成新终测。先前 8 来源/32 攻击预算是备选开发方案，非必须先完成的重建配额。

下列生成规则仅针对覆盖审计发现需改写/新增的部分及新保留数据。主要修改 `src/miaguard/defense_dataset.py`、`scripts/build_defense_v1_dataset.py`、`scripts/export_defense_v1_review_packet.py`、`scripts/verify_defense_v1_dataset.py`、`tests/test_defense_dataset.py`。当前旧构建器会重新选数据且默认旧目录，旧核验脚本固定 candidate06/1,750/14,400；适配显式输入和 manifest 数量后才用于新版本，不能直接执行旧默认命令冒称已应用新规则。

- [ ] 保留或显式关联已冻结原文/划分/索引身份；增加查询版本、会话版本和旧新 ID 对照。改变查询、答案或轮次历史后不复用旧 trace/Session 缓存；新候选输出目录存在即拒绝覆盖。
- [ ] 将选定的轮数/文档选择规则写入生成配置。正常题与答案/证据一起生成，保留逐事实依据；跨文档须两篇各有必要事实；证据不足只说明给定材料缺失的事实，不能把常识未知和原文未给混为一谈。
- [ ] Masked 选择正文唯一、符合既有非数字选词契约的词，按词边界检查剩余正文无泄漏，保持 JSON 输出要求并同步离线答案；IA 避免整段复制和纯常识题，保留 nonmember 假阳性诊断。Direct/S² 按原机制检查目标文本/前缀对应关系。
- [ ] 增加针对三条跨文档漏证据、模板重复、遮蔽词重复出现、问句变化但离线答案未变、不同会话历史误复用的回归用例；结构测试不冒充语义质量测试。先观察缺失行为导致的失败，再实现并运行 `& $taskPython -m pytest tests/test_defense_dataset.py -q`，涉及回放缓存时再运行 `tests/test_defense_benchmark.py`。
- [ ] D-dev 语义规则稳定后按同一版本生成其他分区；保留数据内容审核与开发策略调参的角色分离，不向开发选择环节输出 V/T 的成员标签或效果。按协议及[部分正常题源使用清单](../../../reports/defense_v1/T10/normal_source_usage_20261102_01/manifest.json)扩充全部历史开发来源/事件清单：已用于 D-dev 的文档及同 parent/近重复组不得作为 A-cal/V/T 正常题源；共享背景可仍在各索引中，不能误删或作为 nonmember 目标。保存 manifest、来源哈希、全部分区隔离/重叠报告、清洗与生成身份、请求和离线答案的对应验证；索引未变时引用既有索引身份，不把查询版本变化当成新索引。

进展（2026-11-04）：[保守来源清单](../../../reports/defense_v1/T10/dev_source_inventory_20261104_01/manifest.json)覆盖 200 D-dev 目标及 16 已知共享背景；关联字段缺失拒绝校验已测试。历史 prompt/事件关联未完整，生成器尚未接入，以上复选框保持未完成。

补充进展（2026-11-04）：[D-dev 既有队列导出](../../../reports/defense_v1/T10/dev_cohort_export_20261104_01/manifest.json)在写入前检查实际索引与来源；30 会话、62 问，原 ID 不变，非正式回放。仅为开发导出，并未接入全量生成器或实现新查询生成，以上复选框仍未完成。

补充进展（2026-11-04）：[事件关联预审包](../../../reports/defense_v1/T10/event_pair_review_packet_20261104_01/manifest.json)已覆盖 31 篇 D-dev 试点的 465 对，已收到独立模型预审并完成[结构核验与四组关联处理](../../../reports/defense_v1/T10/EVENT_REVIEW_TRIAGE_20261104_ZH.md)；其余语义未逐对独立复核，且不覆盖全部历史或跨分区，不能勾选来源审计完成。

补充进展（2026-11-04）：[E00 检索来源](../../../reports/defense_v1/T10/e00_retrieved_source_audit_20261104.json)已做全文/近重复机械审计；Masked 唯一非数字词及同步答案已有独立组件和测试，尚未接入新版生成器、处理语义质量或审核，因此相关步骤仍未完成。

补充进展（2026-11-04）：[4 篇 Masked 小批检查](../../../reports/defense_v1/T10/masked_rule_pilot_20261104_01/AGENT_REVIEW_ZH.md)发现标题选词问题；已实现候选位置及显式选择并生成[两条待审试点](../../../reports/defense_v1/T10/masked_selected_pilot_20261104_01/AGENT_REVIEW_ZH.md)，尚未证明可恢复或接入完整生成流程。[试点预算草案](../../../reports/defense_v1/T10/PILOT_SCOPE_AND_REVIEW_BUDGET_20261104_ZH.md)不冻结正式规模。

验收：新候选独立目录，结构与隔离通过，所有新增/修改题仍 pending 直到完成对应复核；更新数据目录、状态页、实验索引和台账。仅生成候选不放行 T12。

#### T10-E 正式 gold 审核与数据验收（NOT_STARTED；依赖 T10-D）

- [ ] 导出新候选审核包和原文证据；模型预审只作建议，记录真实模型 ID/提示哈希/完成范围。逐条参考答案与证据须有可追溯的真实人员核对或裁决，跨文档、截断、证据不足和全部改写重点核查；未核对项保留 pending，并从正式 cohort 排除，不能因抽查通过将全量自动标 reviewed。
- [ ] 汇总 `reviewed_by`、审核范围、修订、排除和最终文档/会话/请求数，写数据验收报告。若没有真人复核资源，正式数据放行维持未满足，可继续独立工程工作；改变审核标准必须另记 CHANGE 并修订协议与论文口径。
- [ ] 形成供 T11/T12 使用的数据身份及 gold 清单，完成全部配对/离线标签验证。该次数据验收不是 T16 的最终实验冻结，也不是 T18/E07 对生成回答的人评。

T10 完成条件：A–E 均有实际证据、正式 cohort 中无未解决审核项、数据身份和文档入口一致。未完成部分保留未勾选，不因开发 overlay 可读或模型接受率提高而放行。

### T11 指标与配对统计

正式验收依赖 T10-E；无需正式 gold 的合成测试与指标实现可在 T10 进行时继续。现有 `src/miaguard/defense_metrics.py`、`scripts/evaluate_defense_v1.py`、`tests/test_defense_metrics.py` 已有工程版本，`evaluate_run(run_dir, evaluator_spec)` 当前仅允许 engineering_only。

- [x] 用手算 fixture 测 AUC=0.5、反向 AUC=0、翻转诊断=1；缺单一类别则指标 null+reason，不能写零。工程单测已完成。
- [x] 测拒答在可回答问题上 correctness=0、不可回答问题合理拒答可成功；空事实 faithfulness=null；无 gold relevance 的 Recall@k 不计算。工程单测已完成，正式评分器仍待 gold。
- [ ] 测 bootstrap 以 doc/group 同时重采样各方法与所有轮次，避免按独立 query 抽样；失败样本保留在正常效用分母，安全样本缺响应另列覆盖和敏感性分析。成对整组重采样与失败效用分母已有单测；安全缺响应敏感性分析尚未实现。

```python
assert metrics['answerable_correctness']['denominator'] == expected_answerable
assert metrics['empty_answer_count'] == expected_empty
assert metrics['membership']['target_count'] == expected_targets
```

- [ ] 实现 A-cal 固定攻击阈值与 test ROC 描述曲线分开，重复种子不算额外独立目标。合成 fixture 已验证 A-cal 方向/固定阈值与多 seed 目标聚合；真实 A-cal 校准和 test 描述 ROC 尚未实现。
- [x] 已运行指标单测及 fake 全链核对，证据见[T11 fake 评估 v3](../../../reports/defense_v1/T11/fake_evaluation_v3.json)；这只完成工程子步骤，不满足正式 G2。
- [ ] 按协议 v1.1 补充变长正常会话的分层/会话平均/家族宏平均、依赖组配对区间、Query-only/Session 有效覆盖、IA member/nonmember Yes 率及失败分母、Masked 精确恢复与解析失败诊断；同一比较使用相同 cohort 和预算。
- [ ] T10-E 验收后绑定真实 gold、正确性/完整性/faithfulness/citation 评分器及其版本，完成成本拆分、缺失响应敏感性分析和置信区间；新增正式评估模式时明确拒绝 pending 数据，不能只改 `analysis_role` 字符串绕过检查。
- [ ] 与 T12 的实际比较配合核对分母、逐行分数和汇总，才可确认 G2。T15 实际 A-cal 校准尚未运行时只报告开发描述指标，不声称已得到正式固定阈值工作点。

### T12 开发集统一动作比较

依赖：T11。新增 `configs/defense/experiments/v1_action_screening.json`；输出新的 `data/defense_v1_runs/` 子目录。代码只做必要修复，不借结果改 test。

2026-10-31 源码核对：`src/miaguard/defense_benchmark_live.py` 当前只接受 B0/B2/B3/B5/B6，B1 尚未接入；其 B5 直接选择第一个检索候选的 parent，属于 Top-1 工程定位规则，不能写成已可靠识别攻击目标。T09 的 fake 证据只证明传入排除集合会执行，不证明 live 定位正确。

- [ ] 先补齐 B1 在统一 live 服务的适配并验证与旧规则对同输入的一致性；在 `defense_benchmark_live.py` 和 `tests/test_defense_benchmark.py` 核验方法列表、在线标签隔离及错误回退。所有正式方法先完成小规模工程 smoke，并将其身份和结果作为正式运行前置证据。
- [ ] 明确 B5 定位算法和版本：实现并核验基于可观测信息的候选定位，或把现有实现明确命名为 Top-1 启发式独立基线，更新协议方法表后再比较；不能把 Top-1 当成真实目标命中。记录误定位、无定位和回填不足案例，目标真值仅由离线评估器使用。

- [ ] 填入 D-dev 数据、模型/索引/Prompt 哈希，运行 B0/B1/B2/B3/B5/B6，顺序和种子固定；B6 失败回退也计成本。
- [ ] 按实际实现的 CLI 参数登记运行/评估命令，检查所有方法目标集合一致，未完成方法不加入同口径总表；文末帮助命令只能确认接口，不能代替正式配置和 live 验收。
- [ ] 逐类阅读误伤/漏防/动作增强攻击的案例，至少覆盖 IA 与单文档事实正常问答。
- [ ] 输出 `action_comparison.json`、`failure_cases.jsonl`、`quality_cost.csv`（仅评估导出，不手改），更新实验索引；达到 G2 后才进入策略学习。

## P3：外部基线、策略与攻击适应

### T13 Mirabel 忠实基线

依赖：T12。新增 `mirabel.py`、`tests/test_mirabel.py`，实验配置追加 B4。复核原论文算法及实现版本，在允许集合上计算全量相似度；去掉最大值后估计背景均值/std，按论文极值阈值定位，显著性候选固定为 0.001/0.01/0.05，在 D-dev 选。

- [ ] 保存原论文/代码引用和公式版本；tiny corpus、零方差、相似度相同与多个峰值的处理明确记录。无法适用时 abstain，不强行宣称统计有效。
- [ ] 测合成离群点定位与全体相等时不任意删文档；对照手算阈值。

```python
assert detect([0.1, 0.1, 0.1, 0.1], alpha=0.01).target_index is None
```

`detect(scores, alpha)` 返回 target_index/threshold/status；行为与论文的必要数值保护差异须记录。

- [ ] 运行 `& $taskPython -m pytest tests/test_mirabel.py tests/test_evidence_access.py -q`，再在同一 D-dev 运行 B4。
- [ ] 报告复现差异、额外相似度成本和质量，Top-1/Top-2 近似只可独立命名为消融。

### T14 动态策略与暴露候选

依赖：T13。新增 `defense_policy_v1.py`、`tests/test_defense_policy_v1.py`，配置 `configs/defense/experiments/v1_policy_search.json`。

- [ ] 固定有限搜索空间：触发阈值为 D-dev 正常风险 95/99 分位及旧冻结阈值（数值分别绑定分支）；动作族 hide/no_context/summary；会话同目标原文交付次数门槛 2/3/5。这些是候选，不是最终参数。
- [ ] 定义 `choose_action(risk, localization, exposure, config)`；低于触发阈值 allow；触发且可靠定位 hide；无定位使用配置中的 no_context/summary；开启会话预算且达到门槛时升级到 no_context/deny 候选。疑似机制只作为已版本化分支条件，未知类型走统一策略。
- [ ] 写阈值边界、未知类型、无目标、单一会话重复合法阅读、预算不跨 session 的测试；Oracle 输入只能出现在独立诊断配置。

```python
assert choose_action(low_risk, location, exposure, config).action == 'allow'
assert choose_action(high_risk, no_location, exposure, config).action in {
    'no_context_answer', 'sanitized_context', 'deny'}
```

- [ ] 运行 `& $taskPython -m pytest tests/test_defense_policy_v1.py tests/test_exposure_store.py -q`，再在 D-dev 搜索，按实验协议约束筛选；记录全部候选，包括无可行解。
- [ ] 保留最多 3 个候选进入 V，避免在 V 继续反复搜索；消融固定其他组件。

### T15 自适应攻击与侧信道

依赖：T14。新增 `adaptive_defense_attack.py`、`tests/test_adaptive_defense_attack.py`、`configs/defense/experiments/v1_adaptive.json`。

- [ ] 定义攻击只调用 `ask(query, session_id)` 获取公开 answer/citations/elapsed/status；不能获取内部动作、风险或目标真值。
- [ ] 实现 A-cal 上分数方向/阈值校准，公开响应特征 Logistic 侧信道基线，及基于上一轮回答选择下一问的固定版本攻击程序。
- [ ] 测拒答/超时均耗一次外部查询、总预算不可超限、不同防御独立会话、不能访问内部日志。

```python
assert attack_result['query_count'] <= configured_budget
assert set(public_response).isdisjoint({'risk_score', 'applied_action', 'membership_label'})
```

- [ ] 运行 `& $taskPython -m pytest tests/test_adaptive_defense_attack.py -q`；在 A-cal 校准，V 上比较 1/3/5/10/30 次预算及会话重置/混合提问。
- [ ] 保存攻击模型/阈值/Prompt 和成本，若简单侧信道仍强于语义攻击，作为主要失败分析，不丢弃。

## P4：冻结与独立终测

### T16 冻结包与自动门禁

依赖：T15。新增 `scripts/freeze_defense_v1_experiment.py`、`tests/test_defense_experiment_freeze.py`，校验逻辑放 `defense_benchmark.py`，不新增重复 schema。

- [ ] 验证 G0–G2 证据、V 选择报告、A-cal 攻击产物、T 隔离审计与数据/模型/策略/评估器哈希。
- [ ] 写测试：缺阈值、哈希不匹配、T 标签被开发使用、缺 baseline、未知版本或旧输出覆盖均拒绝；新终测脚本无有效冻结包不得读 T。
- [ ] 冻结 `experiment_spec.json` 和 `freeze_manifest.json`，记录候选选择规则、样本规模、失败分母与 live 延迟设置。
- [ ] 运行 `& $taskPython -m pytest tests/test_defense_experiment_freeze.py tests/test_defense_benchmark.py -q`，G3 全部满足后登记可执行终测；无需额外的逐项人工许可。

### T17 新保留集完整运行

依赖：T16。使用已存在且验证通过的 CLI，产物独立目录；参数读取冻结包。

- [ ] 先执行 `--validate-only` 检查身份与预计调用量，不输出 T 效果；随后完整运行，记录启动时间/进程/日志。
- [ ] 中断时记 INTERRUPTED、分片数和恢复命令；同身份用 --resume，身份改变必须新 run_id，不能拼接旧分片。
- [ ] 固定评估器汇总主比较、低 FPR、正常分组、配对区间、成本；样本不足的工作点写限制，不补调阈值。
- [ ] 达到 G4 后更新项目状态/实验索引，结论不满足目标也如实记录。修改方法则开启后续版本，不污染本次终测。

### T18 泛化、人评与论文材料

依赖：T17。使用协议规定的扩展实验登记，不自动扩大全部配置组合。输出 `reports/defense_v1/paper/`。

- [ ] 最终方法与最强基线增加一个独立数据域和一个生成模型；使用各自冻结清单，报告是否重新校准。
- [ ] 完成分层盲评样本和真实评审记录，未得到人工评审时明确标记该证据缺失，不由模型代签。
- [ ] 导出主表、困难正常表、消融表、Pareto/预算/动作分布图及失败案例，所有单元格可回溯结果 JSON。
- [ ] 记录计算成本、测试复用、无法满足的约束和结论边界；完成文档间交叉核查后关闭任务。

## CLI 当前可用范围与待交付契约

2026-10-31 源码核对：benchmark 支持运行/恢复；评估器仅支持工程口径；T12 正式配置尚未生成；T16 的预检查/冻结参数尚未实现。以下帮助命令可直接核对当前接口，不启动模型调用：

```powershell
& $taskPython scripts/run_defense_v1_benchmark.py --help
& $taskPython scripts/evaluate_defense_v1.py --help
& $taskPython scripts/build_defense_v1_dataset.py --help
```

现有工程评估示例（输出文件必须不存在；仅重评既有 fake 结果，不运行新防御实验）：

```powershell
& $taskPython scripts/evaluate_defense_v1.py --run-dir data/defense_v1_runs/t09-fake-20261022-05 --output reports/defense_v1/T11/fake_evaluation_manual_check.json --analysis-role engineering_only
```

T16 待交付要求：`--validate-only` 不写已完成标识、不调用生成模型、不查看 T 效果；同路径随后允许 validated → running。终测增加 `--freeze-manifest`，其哈希与 spec 一致。正式数据/配置/评估器验收前不提供一条看似可直接执行的正式实验命令；任务执行时根据已实现 CLI 和实际新 run_id 在台账保存准确命令。

## 完成检查

- [ ] T01–T18 的状态与计划复选框一致，跳过任务有原因与结论影响。
- [ ] G0–G4 全有可定位证据，未完成门禁没有被记成通过。
- [ ] 项目状态/实验索引/数据目录和进度台账一致；原冻结产物哈希保持不变。
- [ ] 所有声称的实验结果均有完整原始记录、身份和失败分母。

当前恢复任务：**T10-D**，按本计划2026-11-11执行清单先实现并验证可观测证据定位与回退；补齐正常题证据、独立三轮和来源审计。旧 train 可在条件满足后用于 engineering_only 真实回答联调；正式 E01、gold 和新保留终测的门禁不变。T01–T09 与 T10-C D-dev 设计子步骤已完成，T10 整体仍在进行；执行期间不以示例命令或预期结果充当实际证据。

版本记录：v1 / 2026-10-22 首次建立；v1.1 / 2026-10-31 对齐 T01–T09 工程证据、T10 两轮预审及 overlay，细化 T10-A–E、T11 正式验收和 CLI 可用边界。

2026-11-04 v1.1 补记：T10-D 执行优先级调整为复用覆盖审计、必要适配和按缺口补建，详见台账 L097；不重开 T10-A–C，不把待办勾为完成，不改变正式实验依赖。

2026-11-04 版本补记：后续复用指定 v2 bank 与 v2 split，v1 已完成 Judge/observe 保留原身份。版本核验不等于 gold 或适配完成，详见台账 L100–L101。

2026-11-05 工程补充：[B5/B6同批真实对照](../../../reports/defense_v1/T10/fast_live_pilot_20261105_01/COMPARISON_B5_B6_ZH.md)已完成24/24；Masked格式与逐词恢复独立诊断已产出，正式评估器及人工gold仍待完成。下一步检查摘要暴露、Top-1定位和回填案例，按需要小量补困难题/独立来源。


## T10-D 正常效用48题开发对照（2026-11-17）

- [x] 固定48条v2 train来源开发题及模拟允许集，记录事实、引文和评分口径。
- [x] 真实B0/V2配对96/96并保存检索、动作、上下文及回答。
- [x] agent逐事实评分并输出[中文报告](../../../reports/defense_v1/T10/UTILITY48_RESULTS_20261117_ZH.md)与可复算JSON。
- [ ] 独立来源和真人gold审核；V2触发限制场景的正常质量另行扩展。此批V2全部allow。


## T10-D 48题复用版效用对照（2026-11-17）

- [x] 固定13条直接复用及35条新拟问题、评分和来源摘要。
- [x] 完成B0/V2 96次真实配对、证据核验、逐题agent评分和[中文报告](../../../reports/defense_v1/T10/UTILITY48_REUSE_RESULTS_20261117_ZH.md)。
- [ ] 扩展触发控制的困难正常题、独立来源与真人gold，继续正式防御评估。

## T10-D 四类各 40 目标的开发对照（2026-11-18）

- [x] 核对 v2 train、原索引成员标签、冻结模型与策略。固定 Direct、S²、Masked 各 20 库内与 20 库外目标及[评分口径](../../../reports/defense_v1/T10/FOUR_TYPE40_SCORING_ZH.md)。
- [x] 完成[小批链路核验](../../../reports/defense_v1/T10/four_type40_smoke_20261118_01_verification.json)及评分复算验证，24/24 次请求。
- [x] 运行并复算[三类单轮 B0/V2 配对](../../../reports/defense_v1/T10/four_type40_single_paired_20261118_01_summary.json)，240/240 个请求，0 失败、0 跳过。
- [x] 从已有问句核验并冻结 [40 个三轮 IA 会话](../../../data/defense_datasets/four_type40_ia_v2_train_20261118_01/manifest.json)，每侧 20 个。
- [x] 完成 [IA 的 B0/V2 配对及复算](../../../reports/defense_v1/T10/four_type40_ia_paired_20261118_01_summary.json)，240/240 个请求，0 失败、0 跳过。
- [x] 交付[四类对照表及案例](../../EXPERIMENT_RESULTS_ZH.md)，同步实验索引、项目状态、进度台账、数据目录和版本总表。记录跨类重用、实际覆盖及开发限制。T10-D 的独立来源、真人 gold、校准及正式效果工作仍按主计划推进。
