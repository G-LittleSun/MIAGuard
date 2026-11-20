# 老师实验模型的本地部署

模型清单以 `configs/models/teacher_models.yaml` 为唯一入口，下载目录均位于项目根目录，攻击实验通过目录读取，不依赖 Hugging Face 在线缓存。

| 用途 | 官方仓库 | 本地目录 | A5000 24GB 运行方式 |
| --- | --- | --- | --- |
| Embedding | `sentence-transformers/all-MiniLM-L6-v2` | `EmbeddingModel/sentence-transformers/all_minilm_l6_v2` | CUDA，384 维 |
| Masked MIA 代理模型 | `openai-community/gpt2-xl` | `LLM/gpt2-xl` | FP32 单卡，用于 token logits |
| Llama 3 | `meta-llama/Meta-Llama-3-8B-Instruct` | `LLM/meta-llama/meta-llama-3-8b-instruct` | BF16 单卡；官方仓库需授权 |
| Mistral | `mistralai/Mistral-7B-Instruct-v0.2` | `LLM/mistralai/mistral-7b-instruct-v0-2` | BF16 单卡 |
| GLM-4 | `zai-org/glm-4-9b-chat-hf` | `LLM/glm-4-9b-chat` | BF16 单卡，短上下文 |
| Phi-4 | `microsoft/phi-4` | `LLM/phi-4` | BF16，GPU + CPU 自动卸载 |
| Qwen2.5 14B 1M | `Qwen/Qwen2.5-14B-Instruct-1M` | `LLM/Qwen2.5-14B-Instruct-1M` | BF16，GPU + CPU 自动卸载，仅短上下文 |

`glm-4-9b-chat-hf` 是智谱官方提供的标准 Transformers 权重转换，模型对应老师配置中的 GLM-4-9B-Chat；本地目录名保持老师项目的命名习惯。

## 环境

Windows 上使用项目同名 Conda 环境：

```powershell
conda env create -f environment.yml
conda run -n MIAGuard python -c "import torch; print(torch.__version__, torch.cuda.is_available())"
```

预期为 `2.6.0+cu124 True`。RTX A5000 支持 BF16，但 14B 模型的 BF16 权重约 29GB，不能全部放入 24GB 显存，因此验证脚本会把一部分层卸载到 64GB 系统内存。一次只运行一个模型。

## 下载

公开模型可逐个下载，下载支持断点续传：

```powershell
conda run -n MIAGuard python scripts/download_hf_weights_chunked.py --model mistral_7b --workers 4
conda run -n MIAGuard python scripts/download_hf_weights_chunked.py --model gpt2_xl --workers 4
conda run -n MIAGuard python scripts/download_hf_weights_chunked.py --model glm4_9b --workers 4
conda run -n MIAGuard python scripts/download_hf_weights_chunked.py --model phi4_14b --workers 4
conda run -n MIAGuard python scripts/download_hf_weights_chunked.py --model qwen2_5_14b_1m --workers 4
```

Llama 3 需要先在官方模型页面接受许可证，并在本机登录；令牌不要写入项目配置或提交到版本库：

```powershell
conda run -n MIAGuard hf auth login
conda run -n MIAGuard python scripts/download_hf_weights_chunked.py --model llama3_8b --workers 4
```

## 最小验证

Embedding 和 LLM 分别执行一次真实 CUDA 编码或最小生成：

```powershell
conda run -n MIAGuard python scripts/verify_teacher_model.py --model embedding
conda run -n MIAGuard python scripts/verify_teacher_model.py --model gpt2_xl
conda run -n MIAGuard python scripts/verify_teacher_model.py --model mistral_7b
conda run -n MIAGuard python scripts/verify_teacher_model.py --model glm4_9b
conda run -n MIAGuard python scripts/verify_teacher_model.py --model phi4_14b
conda run -n MIAGuard python scripts/verify_teacher_model.py --model qwen2_5_14b_1m
```

Qwen 的“1M”表示模型结构支持超长上下文，不表示本机可以实际运行 100 万 token。当前硬件只用于 RAG 的短上下文实验，否则 KV cache 会远超显存和内存容量。

`gpt-4o-mini` 不在本地模型清单中。IA 的辅助生成继续使用项目现有的本地 Ollama 配置。
