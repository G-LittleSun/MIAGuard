from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Mapping

from .config import AttackConfig
from .ollama_client import OllamaClient


def _candidate_token_ids(tokenizer: Any, labels: tuple[str, ...]) -> dict[str, int]:
    if len(labels) < 2 or len(set(labels)) != len(labels):
        raise ValueError("Candidate labels must contain at least two unique values")
    token_ids: dict[str, int] = {}
    for label in labels:
        if not isinstance(label, str) or not label:
            raise ValueError("Candidate labels must be non-blank strings")
        encoded = tokenizer(label, add_special_tokens=False)
        ids = encoded["input_ids"]
        if hasattr(ids, "tolist"):
            ids = ids.tolist()
        if ids and isinstance(ids[0], list):
            ids = ids[0]
        if len(ids) != 1:
            raise ValueError(f"Candidate label must encode as a single token: {label!r}")
        token_ids[label] = int(ids[0])
    if len(set(token_ids.values())) != len(token_ids):
        raise ValueError("Candidate labels must map to distinct token ids")
    return token_ids


def _flat_input_ids(encoded: Any) -> list[int]:
    ids = encoded["input_ids"]
    if hasattr(ids, "tolist"):
        ids = ids.tolist()
    if ids and isinstance(ids[0], list):
        ids = ids[0]
    return [int(token_id) for token_id in ids]


def _contextual_candidate_token_ids(
    tokenizer: Any,
    rendered_prompt: str,
    labels: tuple[str, ...],
    *,
    add_special_tokens: bool,
) -> dict[str, int]:
    if len(labels) < 2 or len(set(labels)) != len(labels):
        raise ValueError("Candidate labels must contain at least two unique values")
    prompt_ids = _flat_input_ids(
        tokenizer(rendered_prompt, add_special_tokens=add_special_tokens)
    )
    token_ids: dict[str, int] = {}
    for label in labels:
        if not isinstance(label, str) or not label:
            raise ValueError("Candidate labels must be non-blank strings")
        combined_ids = _flat_input_ids(
            tokenizer(rendered_prompt + label, add_special_tokens=add_special_tokens)
        )
        if combined_ids[: len(prompt_ids)] != prompt_ids or len(combined_ids) != len(prompt_ids) + 1:
            raise ValueError(
                f"Candidate label must append exactly one token in final prompt context: {label!r}"
            )
        token_ids[label] = combined_ids[-1]
    if len(set(token_ids.values())) != len(token_ids):
        raise ValueError("Candidate labels must map to distinct token ids in final prompt context")
    return token_ids


def _restricted_probabilities(logits: dict[str, float]) -> dict[str, float]:
    if len(logits) < 2 or len(set(logits)) != len(logits):
        raise ValueError("Candidate logits must contain at least two unique labels")
    values: list[float] = []
    for label, value in logits.items():
        if not isinstance(label, str) or not label:
            raise ValueError("Candidate logit labels must be non-blank strings")
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"Candidate logit must be numeric: {label}")
        number = float(value)
        if not math.isfinite(number):
            raise ValueError(f"Candidate logit must be finite: {label}")
        values.append(number)
    maximum = max(values)
    weights = [math.exp(value - maximum) for value in values]
    total = sum(weights)
    return {
        label: weight / total
        for label, weight in zip(logits, weights, strict=True)
    }


def _has_complete_json_value(text: str) -> bool:
    starts = [position for position in (text.find("{"), text.find("[")) if position >= 0]
    if not starts:
        return False
    stack: list[str] = []
    in_string = False
    escaped = False
    pairs = {"}": "{", "]": "["}
    for character in text[min(starts) :]:
        if in_string:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                in_string = False
            continue
        if character == '"':
            in_string = True
        elif character in "{[":
            stack.append(character)
        elif character in "}]":
            if not stack or stack[-1] != pairs[character]:
                return False
            stack.pop()
            if not stack:
                return True
    return False


class ModelClient:
    def __init__(self, config: AttackConfig, project_root: Path) -> None:
        self.config = config
        self.project_root = project_root.resolve()
        self.ollama = (
            OllamaClient(
                config.base_url,
                config.timeout_seconds,
                config.keep_alive,
                config.seed,
            )
            if "ollama" in {config.generation_backend, config.embedding_backend}
            else None
        )
        self._generation_model: Any = None
        self._generation_tokenizer: Any = None
        self._embedding_model: Any = None

    def _model_path(self, value: str) -> Path:
        path = Path(value)
        if not path.is_absolute():
            path = self.project_root / path
        return path.resolve()

    def validate_models(self) -> None:
        local_models: list[tuple[str, str]] = []
        if self.config.generation_backend == "transformers":
            local_models.append(("generation", self.config.generation_model))
        if self.config.embedding_backend == "sentence_transformers":
            local_models.append(("embedding", self.config.embedding_model))
        missing_paths = [
            f"{kind}: {self._model_path(model)}"
            for kind, model in local_models
            if not self._model_path(model).is_dir()
        ]
        if missing_paths:
            raise RuntimeError(f"Local model directories do not exist: {missing_paths}")
        if self.ollama is not None:
            installed = self.ollama.list_models()
            required = []
            if self.config.generation_backend == "ollama":
                required.append(self.config.generation_model)
            if self.config.embedding_backend == "ollama":
                required.append(self.config.embedding_model)
            missing = [model for model in required if model not in installed]
            if missing:
                raise RuntimeError(f"Required Ollama models are not installed: {missing}")

    def _load_generation(self, model_name: str) -> tuple[Any, Any]:
        if self._generation_model is not None:
            return self._generation_model, self._generation_tokenizer
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        if not torch.cuda.is_available():
            raise RuntimeError("The Transformers generation backend requires CUDA")
        path = self._model_path(model_name)
        load_dtype = (
            torch.float16
            if self.config.generation_load_mode == "int8"
            else torch.bfloat16
        )
        load_kwargs: dict[str, Any] = {
            "dtype": load_dtype,
            "local_files_only": True,
            "low_cpu_mem_usage": True,
        }
        if self.config.generation_load_mode == "int8":
            from transformers import BitsAndBytesConfig

            load_kwargs.update(
                quantization_config=BitsAndBytesConfig(load_in_8bit=True),
                device_map="auto",
            )
        model = AutoModelForCausalLM.from_pretrained(str(path), **load_kwargs)
        if self.config.generation_load_mode == "bf16":
            model = model.to("cuda")
        tokenizer = AutoTokenizer.from_pretrained(str(path), local_files_only=True)
        if tokenizer.pad_token_id is None:
            tokenizer.add_special_tokens({"pad_token": "[PAD]"})
            model.resize_token_embeddings(len(tokenizer), mean_resizing=False)
        model.eval()
        torch.manual_seed(self.config.seed)
        torch.cuda.manual_seed_all(self.config.seed)
        self._generation_model = model
        self._generation_tokenizer = tokenizer
        return model, tokenizer

    def generate(
        self,
        model: str,
        prompt: str,
        *,
        system: str = "",
        max_tokens: int = 128,
        temperature: float = 0.0,
        json_output: bool = False,
        json_schema: Mapping[str, Any] | None = None,
    ) -> str:
        if self.config.generation_backend == "ollama":
            if json_schema is not None:
                raise RuntimeError(
                    "JSON Schema constrained decoding requires the transformers backend"
                )
            if self.ollama is None:
                raise RuntimeError("Ollama client is not configured")
            return self.ollama.generate(
                model,
                prompt,
                system=system,
                max_tokens=max_tokens,
                temperature=temperature,
                json_output=json_output,
            )

        import torch

        local_model, tokenizer = self._load_generation(model)
        if system:
            prompt = f"{system}\n\n{prompt}"
        add_special_tokens = True
        if tokenizer.chat_template:
            prompt = tokenizer.apply_chat_template(
                [{"role": "user", "content": prompt}],
                tokenize=False,
                add_generation_prompt=True,
            )
            add_special_tokens = False
        inputs = tokenizer(
            prompt,
            return_tensors="pt",
            padding=True,
            return_attention_mask=True,
            add_special_tokens=add_special_tokens,
        ).to("cuda")
        generate_kwargs: dict[str, Any] = {
            **inputs,
            "max_new_tokens": max_tokens,
            "eos_token_id": local_model.config.eos_token_id,
            "pad_token_id": tokenizer.pad_token_id,
            "do_sample": temperature > 0,
        }
        if temperature > 0:
            generate_kwargs["temperature"] = temperature
        if json_output:
            from transformers import StoppingCriteria, StoppingCriteriaList

            prompt_length = inputs["input_ids"].shape[1]

            class _CompleteJsonStoppingCriteria(StoppingCriteria):
                def __call__(self, input_ids, scores, **kwargs):  # type: ignore[no-untyped-def]
                    del scores, kwargs
                    generated_text = tokenizer.decode(
                        input_ids[0, prompt_length:],
                        skip_special_tokens=True,
                    )
                    return _has_complete_json_value(generated_text)

            generate_kwargs["stopping_criteria"] = StoppingCriteriaList(
                [_CompleteJsonStoppingCriteria()]
            )
        if json_schema is not None:
            try:
                from lmformatenforcer import JsonSchemaParser
                from lmformatenforcer.integrations.transformers import (
                    build_transformers_prefix_allowed_tokens_fn,
                )
            except ImportError as error:
                raise RuntimeError(
                    "JSON Schema constrained decoding requires lm-format-enforcer. "
                    "Install the project model dependencies first."
                ) from error
            parser = JsonSchemaParser(json_schema)
            generate_kwargs["prefix_allowed_tokens_fn"] = (
                build_transformers_prefix_allowed_tokens_fn(tokenizer, parser)
            )
        with torch.inference_mode():
            output = local_model.generate(**generate_kwargs)
        generated = output[:, inputs["input_ids"].shape[1] :]
        return tokenizer.decode(generated[0], skip_special_tokens=True).strip()

    def generate_json(self, model: str, prompt: str, **kwargs: Any) -> Any:
        text = self.generate(model, prompt, json_output=True, **kwargs)
        cleaned = text.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.replace("\\$", "$").replace("\\_", "_")
        try:
            return json.loads(cleaned.strip())
        except json.JSONDecodeError:
            starts = [
                position
                for position in (cleaned.find("{"), cleaned.find("["))
                if position >= 0
            ]
            if not starts:
                raise RuntimeError(f"Model did not return JSON: {text[:200]}")
            start = min(starts)
            try:
                value, _ = json.JSONDecoder().raw_decode(cleaned[start:])
                return value
            except json.JSONDecodeError as error:
                raise RuntimeError(
                    f"Model returned incomplete JSON: {text[:200]}"
                ) from error

    def candidate_label_probabilities(
        self,
        model: str,
        prompt: str,
        *,
        labels: tuple[str, ...],
        system: str = "",
    ) -> dict[str, float]:
        if self.config.generation_backend != "transformers":
            raise RuntimeError("Candidate label probabilities require transformers backend")

        import torch

        local_model, tokenizer = self._load_generation(model)
        if system:
            prompt = f"{system}\n\n{prompt}"
        add_special_tokens = True
        if tokenizer.chat_template:
            prompt = tokenizer.apply_chat_template(
                [{"role": "user", "content": prompt}],
                tokenize=False,
                add_generation_prompt=True,
            )
            add_special_tokens = False
        token_ids = _contextual_candidate_token_ids(
            tokenizer,
            prompt,
            labels,
            add_special_tokens=add_special_tokens,
        )
        inputs = tokenizer(
            prompt,
            return_tensors="pt",
            padding=True,
            return_attention_mask=True,
            add_special_tokens=add_special_tokens,
        ).to("cuda")
        with torch.inference_mode():
            outputs = local_model(**inputs)
        candidate_logits = {
            label: float(outputs.logits[0, -1, token_id].item())
            for label, token_id in token_ids.items()
        }
        return _restricted_probabilities(candidate_logits)

    def embed(self, model: str, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if self.config.embedding_backend == "ollama":
            if self.ollama is None:
                raise RuntimeError("Ollama client is not configured")
            return self.ollama.embed(model, texts)
        if self._embedding_model is None:
            from sentence_transformers import SentenceTransformer

            self._embedding_model = SentenceTransformer(
                str(self._model_path(model)), device="cuda"
            )
        vectors = self._embedding_model.encode(
            texts,
            normalize_embeddings=True,
            convert_to_numpy=True,
        )
        return vectors.tolist()


def create_model_client(config: AttackConfig, project_root: Path) -> ModelClient:
    return ModelClient(config, project_root)


__all__ = [
    "ModelClient",
    "_candidate_token_ids",
    "_contextual_candidate_token_ids",
    "_restricted_probabilities",
    "create_model_client",
]
