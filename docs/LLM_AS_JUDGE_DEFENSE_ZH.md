# LLM-as-Judge 防御与攻击模式库

## 当前 MVP

当前实现使用项目内部“攻击模式库”管理四种攻击定义。它不依赖 Codex Skill，
而是由 MIAGuard 读取注册表和模式文件，再按需提供给本地 Mistral Judge。

MVP 每次判断会从注册表查询当前启用的模式，并加载四个小型 `PATTERN.md`，结合
查询、检索片段和当前会话输出 JSON。模式定义来自独立文件，不写死在系统提示词中。
早期测试发现 7B 模型的独立路由会漏选 S²/Masked，因此当前使用一次性全量加载：
它更可靠，并且只需要一次模型生成。配置仍保留 `routing_mode: llm`，供后续模型能力
足够时重新评估。Judge 输出无效时按 `uncertain` 处理，不会默认放行。

## 小规模检测实验

激活环境：

```powershell
conda activate MIAGuard
```

运行四种攻击各 2 条、困难 benign 8 条，共 16 条：

```powershell
python scripts/run_llm_judge_experiment.py `
  --config configs/attacks/ag_news_calibrated.yaml `
  --defense-config configs/defense/mvp.yaml `
  --judge-config configs/defense/llm_judge_mvp.yaml `
  --source-events data/hard_query_results/20260720-ag-news-hard-queries/ag_news/query_events.jsonl `
  --output-run-id 20260720-ag-news-llm-judge-smoke `
  --limit-per-attack 2 `
  --benign-count 8
```

结果位于：

```text
data/llm_judge_results/<run-id>/ag_news/
├── summary.json
├── detector_metrics.json
├── judge_decisions.jsonl
├── query_events.jsonl
├── run_manifest.json
└── attack_pattern_library_snapshot/
```

本轮只评估 Judge 是否识别攻击意图，不重新生成四种攻击的防御后回答，因此不输出
成员推理攻击 Accuracy。Judge 检测确认可用后，再接入完整 RAG 攻击链路评估防御前后
Accuracy、AUROC 和 Privacy Advantage。

## 已验证的小规模结果

验证运行：`20260720-ag-news-llm-judge-smoke-v3`，使用攻击模式库 1.1.0 和本地
`Mistral-7B-Instruct-v0.2`。数据为四种困难攻击各 2 条、四类困难 benign 各 2 条，
总计 16 条。

| 类型 | 检出/总数 | 检出率 |
|---|---:|---:|
| Direct RAG-MIA | 2/2 | 100% |
| S²-MIA | 2/2 | 100% |
| Masked MIA | 2/2 | 100% |
| IA（单条事实查询） | 0/2 | 0% |

总体分类 Accuracy 为 87.5%，Precision 为 100%，Recall 为 75%，F1 为 85.71%。
8 条困难 benign 没有被明确判成攻击；其中 6 条允许，2 条因 `uncertain` 被限制上下文，
所以明确攻击误报率为 0%，策略干预率为 25%。平均单条 Judge 延迟约 5.28 秒。

IA 结果符合当前模式定义：单条普通事实问题缺少足够证据，下一阶段需要构造连续 3～5
轮、重复命中同一文档的会话再评测。当前结果是检测器 MVP，不代表端到端防御已经使成员
推理攻击 Accuracy 降至随机水平。

## 更新攻击模式

查询和校验模式库：

```powershell
python scripts/manage_attack_patterns.py list
python scripts/manage_attack_patterns.py show masked_mia
python scripts/manage_attack_patterns.py validate
```

1. 修改 `attack_pattern_library/patterns/<id>/PATTERN.md`。
2. 递增该模式在 `manifest.yaml` 中的版本。
3. 递增模式库版本。
4. 运行 `pytest tests/test_attack_pattern_library.py tests/test_llm_judge.py`。
5. 使用新的输出运行 ID 执行检测实验。

每个实验目录保存模式库快照，因此后续更新不会改变已经完成实验的判定依据。

## 第二阶段：会话级 IA Judge

会话实验使用老师 IA 实现同类的本地 LLM 问题生成方法，对同一个成员文档生成多个
不同的 yes/no/unknown 事实探测问题。对照组是围绕另一篇公共新闻依次询问主题、核心
人物或机构、主要事件和高层摘要的正常阅读会话。两类会话都真实经过 FAISS 检索。

Judge 输入增加：

- 最近查询和每轮 Top-k 文档 ID；
- 当前轮次；
- 同一 Top-1 文档重复次数；
- Top-1 文档集中度。

当通用 Judge 判为 IA suspicious/attack 时，再调用只读取 IA 模式的复核 Judge，区分
`systematic_fact_probes` 和 `coherent_benign_dialogue`。重复检索本身不能确认攻击。

已成功运行：`20260720-ag-news-llm-judge-ia-session-smoke-v5`。使用攻击模式库 1.4.0，
包含 1 个四轮攻击会话和 1 个四轮 benign 会话，共 8 次基础判断。

| 轮次 | IA 攻击检出率 | benign 明确误报率 | benign 干预率 |
|---:|---:|---:|---:|
| 1 | 0% | 0% | 0% |
| 2 | 0% | 0% | 0% |
| 3 | 100% | 0% | 100% |
| 4 | 100% | 0% | 0% |

攻击会话在第 3 轮首次检出；benign 会话没有被明确判成攻击，但第 3 轮复核返回
`uncertain`，因此被限制上下文一次。会话级明确攻击误报率为 0%，benign 放行率为
75%。全部轮次 Precision 为 100%，Recall 为 50%；该 Recall 把证据不足的前两轮也
计入攻击分母，因此不能代替“会话最终检出率 100%”。

性能方面，FAISS 平均检索约 111 毫秒，Judge 中位延迟约 5.79 秒，P95 约 26.64 秒，
平均约 10.59 秒。扩展到 2+2 个会话时曾触及 10 分钟上限且没有完成，因此当前结果只
能证明最小会话链路可行，不能证明大样本稳定性。进入端到端攻击评测前，应先压缩提示、
限制生成长度并实现逐会话检查点。

运行最小会话实验：

```powershell
python scripts/run_ia_session_judge_experiment.py `
  --config configs/attacks/ag_news_calibrated.yaml `
  --defense-config configs/defense/mvp.yaml `
  --judge-config configs/defense/llm_judge_session_smoke.yaml `
  --source-run-id 20260717-ag-news-four-medium `
  --dataset ag_news `
  --output-run-id <new-run-id> `
  --sessions-per-class 1 `
  --turn-count 4 `
  --document-offset 216
```
