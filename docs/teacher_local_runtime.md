# 老师模型的本地直接调用

老师项目没有通过 Ollama 调用 Mistral、Llama、GLM 等本地权重，而是直接使用 Transformers：

- `AutoModelForCausalLM.from_pretrained(...)` 从本地 `LLM/` 目录加载模型；
- 使用 BF16，并把模型放到 CUDA；
- `AutoTokenizer.from_pretrained(...)` 加载对应 tokenizer；
- 自己封装 `invoke()`，调用 `model.generate()`。

Embedding 使用本地 `all-MiniLM-L6-v2`。老师通过 LangChain 的 `HuggingFaceBgeEmbeddings` 包装该模型，设置 CUDA 和 `normalize_embeddings=True`，再使用 LangChain FAISS。MIAGuard 保留自己的原生 FAISS 存储格式，但编码模型、384 维向量、归一化和余弦相似度行为与老师保持一致。

本地直接调用配置：

```text
configs/attacks/teacher_local_smoke.yaml
```

其中：

- generation backend：`transformers`
- generation model：`LLM/mistralai/mistral-7b-instruct-v0-2`
- embedding backend：`sentence_transformers`
- embedding model：`EmbeddingModel/sentence-transformers/all_minilm_l6_v2`
- FAISS：`IndexFlatIP`，归一化后等价于余弦相似度
- top-k：4

由于没有 `gpt-4o-mini` API，IA 的问题、标准答案和摘要也交给本地 Mistral。这里使用 Mistral-Instruct 自带的 chat template，仍然由本地 Transformers 直接执行；否则模型容易把 JSON 指令当成普通文本续写。

最小验证命令：

```powershell
conda run -n MIAGuard python -m miaguard.cli doctor --config configs/attacks/teacher_local_smoke.yaml
conda run -n MIAGuard python scripts/build_vector_db.py --config configs/attacks/teacher_local_smoke.yaml --run-id 20260716-ag-news-teacher-local-smoke --dataset ag_news
conda run -n MIAGuard python scripts/run_masked_mia.py --config configs/attacks/teacher_local_smoke.yaml --run-id 20260716-ag-news-teacher-local-smoke --dataset ag_news --limit-per-class 1
conda run -n MIAGuard python scripts/run_ia.py --config configs/attacks/teacher_local_smoke.yaml --run-id 20260716-ag-news-teacher-local-smoke --dataset ag_news --limit-per-class 1
```

该 smoke run 只有一个成员和一个非成员，指标只能用于验证链路，不能作为攻击效果结论。
