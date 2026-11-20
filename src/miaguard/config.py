from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class AttackConfig:
    base_url: str
    generation_backend: str
    generation_model: str
    generation_load_mode: str
    embedding_backend: str
    embedding_model: str
    timeout_seconds: int
    keep_alive: str
    seed: int
    embedding_batch_size: int
    top_k: int
    mask_count: int
    masked_threshold: float
    masked_threshold_source: str
    masked_max_tokens: int
    questions_per_document: int
    ia_threshold: float
    ia_threshold_source: str
    ia_unknown_penalty: float
    ia_generation_max_tokens: int
    direct_rag_mia_threshold: float
    direct_rag_mia_threshold_source: str
    direct_rag_mia_max_tokens: int
    s2_mia_threshold: float
    s2_mia_threshold_source: str
    s2_mia_max_tokens: int
    s2_mia_prefix_words: int


def _section(raw: dict[str, Any], name: str) -> dict[str, Any]:
    value = raw.get(name)
    if not isinstance(value, dict):
        raise ValueError(f"Missing or invalid configuration section: {name}")
    return value


def load_attack_config(path: str | Path) -> AttackConfig:
    config_path = Path(path)
    with config_path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    if not isinstance(raw, dict):
        raise ValueError("Attack configuration must be a YAML mapping")

    ollama = raw.get("ollama", {})
    if not isinstance(ollama, dict):
        raise ValueError("Invalid configuration section: ollama")
    models = raw.get("models")
    if models is None:
        generation_backend = "ollama"
        generation_model = str(ollama["generation_model"])
        generation_load_mode = "native"
        embedding_backend = "ollama"
        embedding_model = str(ollama["embedding_model"])
    else:
        if not isinstance(models, dict):
            raise ValueError("Invalid configuration section: models")
        generation = _section(models, "generation")
        embedding = _section(models, "embedding")
        generation_backend = str(generation["backend"])
        generation_model = str(generation["model"])
        generation_load_mode = str(generation.get("load_mode", "bf16"))
        embedding_backend = str(embedding["backend"])
        embedding_model = str(embedding["model"])
    vector_store = _section(raw, "vector_store")
    masked = _section(raw, "masked_mia")
    ia = _section(raw, "ia")
    direct = raw.get("direct_rag_mia", {})
    s2 = raw.get("s2_mia", {})
    if not isinstance(direct, dict):
        raise ValueError("Invalid configuration section: direct_rag_mia")
    if not isinstance(s2, dict):
        raise ValueError("Invalid configuration section: s2_mia")
    config = AttackConfig(
        base_url=str(ollama.get("base_url", "http://127.0.0.1:11434")).rstrip("/"),
        generation_backend=generation_backend,
        generation_model=generation_model,
        generation_load_mode=generation_load_mode,
        embedding_backend=embedding_backend,
        embedding_model=embedding_model,
        timeout_seconds=int(ollama.get("timeout_seconds", 300)),
        keep_alive=str(ollama.get("keep_alive", "10m")),
        seed=int(raw.get("seed", 20260715)),
        embedding_batch_size=int(vector_store.get("embedding_batch_size", 16)),
        top_k=int(vector_store.get("top_k", 4)),
        mask_count=int(masked.get("mask_count", 5)),
        masked_threshold=float(masked.get("threshold", 0.5)),
        masked_threshold_source=str(
            masked.get("threshold_source", "fixed_config_no_shadow")
        ),
        masked_max_tokens=int(masked.get("max_tokens", 128)),
        questions_per_document=int(ia.get("questions_per_document", 30)),
        ia_threshold=float(ia.get("threshold", 0.5)),
        ia_threshold_source=str(
            ia.get("threshold_source", "fixed_config_no_shadow")
        ),
        ia_unknown_penalty=float(ia.get("unknown_penalty", 0.1)),
        ia_generation_max_tokens=int(ia.get("generation_max_tokens", 512)),
        direct_rag_mia_threshold=float(direct.get("threshold", 0.5)),
        direct_rag_mia_threshold_source=str(
            direct.get("threshold_source", "fixed_config_no_shadow")
        ),
        direct_rag_mia_max_tokens=int(direct.get("max_tokens", 12)),
        s2_mia_threshold=float(s2.get("threshold", 0.7)),
        s2_mia_threshold_source=str(
            s2.get("threshold_source", "fixed_config_no_shadow")
        ),
        s2_mia_max_tokens=int(s2.get("max_tokens", 128)),
        s2_mia_prefix_words=int(s2.get("prefix_words", 10)),
    )
    if config.embedding_batch_size <= 0 or config.top_k <= 0:
        raise ValueError("Vector-store sizes must be positive")
    if config.mask_count <= 0 or config.questions_per_document <= 0:
        raise ValueError("Attack query counts must be positive")
    thresholds = (
        config.masked_threshold,
        config.ia_threshold,
        config.direct_rag_mia_threshold,
        config.s2_mia_threshold,
    )
    if any(not 0 <= threshold <= 1 for threshold in thresholds):
        raise ValueError("Attack thresholds must be between 0 and 1")
    if config.ia_unknown_penalty < 0:
        raise ValueError("IA unknown penalty must be non-negative")
    if (
        config.direct_rag_mia_max_tokens <= 0
        or config.s2_mia_max_tokens <= 0
        or config.s2_mia_prefix_words <= 0
    ):
        raise ValueError("Direct RAG-MIA and S2-MIA sizes must be positive")
    if config.generation_backend not in {"ollama", "transformers"}:
        raise ValueError(f"Unsupported generation backend: {config.generation_backend}")
    if config.generation_backend == "transformers" and config.generation_load_mode not in {
        "bf16",
        "int8",
    }:
        raise ValueError(
            f"Unsupported Transformers generation load mode: {config.generation_load_mode}"
        )
    if config.generation_backend == "ollama" and config.generation_load_mode != "native":
        raise ValueError("Ollama generation load mode must be native")
    if config.embedding_backend not in {"ollama", "sentence_transformers"}:
        raise ValueError(f"Unsupported embedding backend: {config.embedding_backend}")
    return config


__all__ = ["AttackConfig", "load_attack_config"]
