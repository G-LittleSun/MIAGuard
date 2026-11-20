from __future__ import annotations

import argparse
import gc
import json
from pathlib import Path
from typing import Any

import torch
import yaml
from sentence_transformers import SentenceTransformer
from transformers import AutoModelForCausalLM, AutoTokenizer


def load_catalog(path: Path) -> dict[str, dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    models = raw.get("models") if isinstance(raw, dict) else None
    if not isinstance(models, dict):
        raise ValueError("Model catalog must contain a models mapping")
    return models


def verify_embedding(path: Path) -> dict[str, Any]:
    model = SentenceTransformer(str(path), device="cuda")
    vector = model.encode(["MIAGuard embedding verification"], normalize_embeddings=True)
    result = {
        "device": str(model.device),
        "dimension": int(vector.shape[1]),
        "norm": float((vector[0] ** 2).sum() ** 0.5),
    }
    del model
    torch.cuda.empty_cache()
    return result


def input_device(model: torch.nn.Module) -> torch.device:
    device_map = getattr(model, "hf_device_map", None)
    if isinstance(device_map, dict):
        for value in device_map.values():
            if value not in ("cpu", "disk"):
                return torch.device(f"cuda:{value}" if isinstance(value, int) else value)
    return next(model.parameters()).device


def verify_gpt2_proxy(path: Path) -> dict[str, Any]:
    tokenizer = AutoTokenizer.from_pretrained(str(path), local_files_only=True)
    model = AutoModelForCausalLM.from_pretrained(
        str(path),
        dtype=torch.float32,
        local_files_only=True,
        low_cpu_mem_usage=True,
        device_map="auto",
        max_memory={0: "21GiB", "cpu": "42GiB"},
    )
    inputs = tokenizer("RAG membership inference", return_tensors="pt").to(
        input_device(model)
    )
    torch.cuda.reset_peak_memory_stats()
    with torch.inference_mode():
        outputs = model(**inputs)
    final_logits = outputs.logits[:, -1, :]
    top_token_id = int(final_logits.argmax(dim=-1).item())
    result = {
        "device_map": getattr(model, "hf_device_map", {"": str(model.device)}),
        "dtype": str(model.dtype),
        "logits_shape": list(final_logits.shape),
        "top_token_id": top_token_id,
        "top_token": tokenizer.decode([top_token_id]),
        "peak_cuda_gib": round(torch.cuda.max_memory_allocated() / 1024**3, 3),
    }
    del final_logits, outputs, inputs, model, tokenizer
    gc.collect()
    torch.cuda.empty_cache()
    return result


def verify_llm(path: Path, load_mode: str, offload_root: Path) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "dtype": torch.float32 if load_mode == "fp32_cuda" else torch.bfloat16,
        "local_files_only": True,
        "low_cpu_mem_usage": True,
    }
    if load_mode in {"fp32_cuda", "bf16_cuda", "bf16_cuda_short_context"}:
        kwargs["device_map"] = "auto"
        kwargs["max_memory"] = {0: "21GiB", "cpu": "42GiB"}
    else:
        offload_root.mkdir(parents=True, exist_ok=True)
        kwargs["device_map"] = "auto"
        kwargs["max_memory"] = {0: "19GiB", "cpu": "42GiB"}
        kwargs["offload_folder"] = str(offload_root)

    tokenizer = AutoTokenizer.from_pretrained(str(path), local_files_only=True)
    model = AutoModelForCausalLM.from_pretrained(str(path), **kwargs)
    messages = [{"role": "user", "content": "Reply with OK only."}]
    if getattr(tokenizer, "chat_template", None):
        prompt = tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
    else:
        prompt = messages[0]["content"]
    inputs = tokenizer(prompt, return_tensors="pt").to(input_device(model))
    torch.cuda.reset_peak_memory_stats()
    with torch.inference_mode():
        generated = model.generate(**inputs, max_new_tokens=8, do_sample=False)
    response = tokenizer.decode(
        generated[0, inputs["input_ids"].shape[1] :], skip_special_tokens=True
    ).strip()
    result = {
        "device_map": getattr(model, "hf_device_map", {"": str(model.device)}),
        "dtype": str(model.dtype),
        "generated": response,
        "peak_cuda_gib": round(torch.cuda.max_memory_allocated() / 1024**3, 3),
    }
    del generated, inputs, model, tokenizer
    gc.collect()
    torch.cuda.empty_cache()
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", default="configs/models/teacher_models.yaml")
    parser.add_argument("--model", required=True)
    args = parser.parse_args()
    root = Path.cwd().resolve()
    catalog = load_catalog(root / args.catalog)
    if args.model not in catalog:
        raise ValueError(f"Unknown model: {args.model}")
    config = catalog[args.model]
    path = root / str(config["local_dir"])
    if args.model == "embedding":
        details = verify_embedding(path)
    elif args.model == "gpt2_xl":
        details = verify_gpt2_proxy(path)
    else:
        details = verify_llm(
            path,
            str(config["load_mode"]),
            root / "models" / "offload" / args.model,
        )
    print(
        json.dumps(
            {
                "model": args.model,
                "path": str(path),
                "status": "verified",
                **details,
            },
            ensure_ascii=False,
            indent=2,
            default=str,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
