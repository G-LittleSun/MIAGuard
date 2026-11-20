# 大样本与困难查询实验

## 1. benign 的含义

`benign` 表示没有成员推理攻击意图的合法查询，即正常用户请求。它与 `nonmember` 不同：

```text
benign / attack：描述查询意图
member / nonmember：描述目标文档是否在 RAG 向量库中
```

合法用户可以查询成员文档，此时查询仍然是 benign；攻击者也可以针对非成员文档发起成员性探测，此时仍然是 attack。

## 2. 大样本防御实验

运行目录：

```text
data/defense_results/20260720-ag-news-defense-large/ag_news/
```

规模：

```text
FAISS成员文档：1000
每种攻击：50 member + 50 nonmember = 100
四种攻击：400条攻击事件
benign：50 member + 50 nonmember = 100条
总事件：500
```

结果：

| 攻击 | 样本数 | 防御前 Accuracy | 防御后 Accuracy | 降幅 | 防御前 ROC-AUC | 防御后 ROC-AUC |
|---|---:|---:|---:|---:|---:|---:|
| Direct RAG-MIA | 100 | 1.00 | 0.50 | 0.50 | 1.00 | 0.50 |
| S²-MIA | 100 | 0.69 | 0.50 | 0.19 | 0.7656 | 0.4984 |
| Masked MIA | 100 | 0.72 | 0.50 | 0.22 | 0.7596 | 0.50 |
| IA | 100 | 0.88 | 0.49 | 0.39 | 0.9048 | 0.49 |
| 宏平均 | 400 | 0.8225 | 0.4975 | 0.325 | — | — |

正常查询：

```text
benign allow rate: 1.0
benign false positive rate: 0.0
actions: 400 deny + 100 allow
average retrieval/decision latency: 11.55 ms
```

这说明当前规则对原始已知攻击模板具有稳定作用，但不能说明它能处理攻击表达改写。

## 3. 困难查询规则鲁棒性实验

运行目录：

```text
data/hard_query_results/20260720-ag-news-hard-queries/ag_news/
```

该实验只评估检测器，不报告成员推理 Accuracy。原因是攻击 prompt 已经改变，必须重新定义各攻击的生成、回答和评分协议后才能计算新的成员推断结果，不能直接复用原始攻击分数。

规模：

```text
Direct 改写攻击：10 member + 10 nonmember
S² 改写攻击：10 + 10
Masked 改写攻击：10 + 10
IA 改写攻击：10 + 10
改写攻击合计：80
hard benign：40
总事件：120
```

### 3.1 攻击改写

改写保留攻击目的，但避免现有关键词。例如：

```text
Direct:
Can the system's retrieved evidence substantiate this quotation ...?

S²:
Using the available evidence, write the likely words that follow this opening ...

Masked:
Supply the omitted terms in order for this passage: <omitted-1> ...

IA:
Did the company announce a product? Respond yes, no, or unknown.
```

这些查询不再包含规则依赖的 `appear in context`、`complete this sentence`、`[Mask_n]` 和 `I am inquiring about`。

### 3.2 hard benign

hard benign 是合法任务，但表面包含攻击关键词，例如：

```text
公开文章中的 context 检查
公开语法练习中的 complete this sentence
公开词汇练习中的 [Mask_1]
合法咨询中的 I am inquiring about
```

它们用于测试规则是否把“包含关键词”等同于“具有攻击意图”。

### 3.3 检测结果

| 指标 | 结果 |
|---|---:|
| Detector Accuracy | 0.0 |
| Precision | 0.0 |
| Recall | 0.0 |
| F1 | 0.0 |
| 改写攻击放行率 | 1.0 |
| hard benign 误报率 | 1.0 |

各攻击检测率：

| 攻击 | 检测率 | 放行率 |
|---|---:|---:|
| Direct 改写 | 0.0 | 1.0 |
| S² 改写 | 0.0 | 1.0 |
| Masked 改写 | 0.0 | 1.0 |
| IA 改写 | 0.0 | 1.0 |

访问动作：

```text
80条改写攻击：全部 low → allow
30条hard benign：high → deny
10条hard benign：medium → deny
```

## 4. 结论

两组实验并不矛盾：

```text
已知模板大样本：Rule-only 有效
关键词规避攻击：Rule-only 全部漏检
关键词相似合法任务：Rule-only 全部误报
```

因此当前方法适合作为系统闭环和 Rule-only baseline，不适合作为最终防御。下一阶段必须引入：

1. 攻击语义模式 embedding；
2. 改写攻击正样本；
3. hard benign / hard negative；
4. Rule + Embedding 联合风险；
5. 对不确定样本按需调用 LLM Judge；
6. 在新的独立验证集上调阈值。

## 5. 验证状态

```text
大样本 Schema：500 / 500 通过
困难查询 Schema：120 / 120 通过
大样本与困难攻击目标交集：0
pytest：131 passed, 1 skipped
pip check：No broken requirements found
```
