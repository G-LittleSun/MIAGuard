# Masked MIA 与 IA 的本地迁移说明

## 迁移方案

- 生成模型：smoke 使用 Ollama `qwen2.5:3b`，formal 使用 `qwen3:8b`。
- 嵌入模型：Ollama `nomic-embed-text:latest`。
- 向量数据库：FAISS `IndexFlatIP`；嵌入归一化后执行余弦相似度检索。
- Target 库内容：只写入 `membership_label=1` 的成员文档。
- Shadow：不构建、不读取。分类阈值由配置固定为 `0.5`，不会使用评测标签调参。
- 结果指标：Accuracy、Precision、Recall、F1、ROC-AUC、TPR@0.1%FPR、TPR@1%FPR、混淆矩阵和两类平均分。

## 老师文件与迁移文件对应关系

| 老师实现 | MIAGuard 迁移实现 | 作用 |
| --- | --- | --- |
| `MaskBasedMIA/MaskDocsWithProxyLLMv8.py` | `src/miaguard/masked_mia.py` | 分段选词、掩码、记录正确答案 |
| `MaskBasedMIA/QueryRAG_Target.py` | `src/miaguard/masked_mia.py` | Target RAG 检索与掩码恢复 |
| `MaskBasedMIA/Attack.py` | `src/miaguard/metrics.py` | 成员分数和分类指标 |
| `IAplusBigLLM/IA_QueryGeneration.py` | `src/miaguard/ia_attack.py` | yes/no 问题生成 |
| `IAplusBigLLM/IA_GroundTruthAnswerGen.py` | `src/miaguard/ia_attack.py` | 基于候选原文生成标准答案 |
| `IAplusBigLLM/IA_extract_summary.py` | `src/miaguard/ia_attack.py` | 生成主题摘要 |
| `IAplusBigLLM/IA_ConstructAdversarialQuery.py` | `src/miaguard/ia_attack.py` | 组装对抗查询 |
| `IAplusBigLLM/IA_QueryRAG.py` | `src/miaguard/ia_attack.py` | 查询 Target RAG |
| `IAplusBigLLM/IA_Attack.py` | `src/miaguard/ia_attack.py`、`src/miaguard/metrics.py` | IA 分数与最终指标 |
| `utils/vector_db_utils.py`、`model_target_create.py` | `src/miaguard/vector_store.py` | 统一向量库构建、持久化和加载 |

老师代码中的外部接口地址、明文 API 密钥、ShadowModel 脚本、训练型攻击器和历史结果没有迁移。

## 算法保持与必要改动

Masked MIA 仍然把文档分成 5 段、每段掩码一个难预测词，随后让 Target RAG 恢复掩码，并以精确恢复比例作为成员分数。老师的 GPT-2 代理模型依赖 token logits；Ollama 生成接口不返回等价 logits，因此迁移版让本地 Ollama 代理模型从每段复制一个难预测词。若输出不合法，只对该段使用确定性的最长内容词兜底，并在结果的 `selection_sources` 中记录。

IA 仍然执行“生成 yes/no 问题 → 用原文生成标准答案 → 添加主题摘要形成对抗问题 → 查询 Target RAG → 比较答案”的链路。评分保持老师定义：一致为 `1`，错误为 `0`，错误且 RAG 回答 unknown 时为 `-0.1`。

smoke 配置每篇文档生成 3 个 IA 问题以便快速验证；formal 配置保持老师的 30 个问题。两者都保持 Masked MIA 的 5 个 mask。

## 独立执行

```powershell
conda run -n MIAGuard python -m miaguard.cli doctor --config configs/attacks/ollama_smoke.yaml
conda run -n MIAGuard python scripts/build_vector_db.py --config configs/attacks/ollama_smoke.yaml --run-id 20260715-ag-news-smoke --dataset ag_news
conda run -n MIAGuard python scripts/run_masked_mia.py --config configs/attacks/ollama_smoke.yaml --run-id 20260715-ag-news-smoke --dataset ag_news --limit-per-class 1
conda run -n MIAGuard python scripts/run_ia.py --config configs/attacks/ollama_smoke.yaml --run-id 20260715-ag-news-smoke --dataset ag_news --limit-per-class 1
```

指标也可以从攻击结果独立重算：

```powershell
conda run -n MIAGuard python scripts/compute_attack_metrics.py --results data/attack_results/20260715-ag-news-smoke/ag_news/masked_mia/results.jsonl --output data/attack_results/20260715-ag-news-smoke/ag_news/masked_mia/metrics.recomputed.json --threshold 0.5
```

