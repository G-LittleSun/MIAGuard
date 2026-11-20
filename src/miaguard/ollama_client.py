from __future__ import annotations

import json
from typing import Any

import requests


class OllamaClient:
    def __init__(
        self,
        base_url: str = "http://127.0.0.1:11434",
        timeout_seconds: int = 300,
        keep_alive: str = "10m",
        seed: int = 20260715,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.keep_alive = keep_alive
        self.seed = seed
        self.session = requests.Session()

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        response = self.session.post(
            f"{self.base_url}{path}", json=payload, timeout=self.timeout_seconds
        )
        response.raise_for_status()
        value = response.json()
        if not isinstance(value, dict):
            raise RuntimeError(f"Unexpected Ollama response from {path}")
        return value

    def list_models(self) -> list[str]:
        response = self.session.get(
            f"{self.base_url}/api/tags", timeout=self.timeout_seconds
        )
        response.raise_for_status()
        return [str(model["name"]) for model in response.json().get("models", [])]

    def generate(
        self,
        model: str,
        prompt: str,
        *,
        system: str = "",
        max_tokens: int = 128,
        temperature: float = 0.0,
        json_output: bool = False,
    ) -> str:
        payload: dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "keep_alive": self.keep_alive,
            "options": {
                "num_predict": max_tokens,
                "temperature": temperature,
                "seed": self.seed,
            },
        }
        if system:
            payload["system"] = system
        if json_output:
            payload["format"] = "json"
        result = self._post("/api/generate", payload).get("response")
        if not isinstance(result, str):
            raise RuntimeError("Ollama generation response has no text")
        return result.strip()

    def generate_json(self, model: str, prompt: str, **kwargs: Any) -> Any:
        text = self.generate(model, prompt, json_output=True, **kwargs)
        cleaned = text.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        try:
            return json.loads(cleaned.strip())
        except json.JSONDecodeError:
            starts = [position for position in (cleaned.find("{"), cleaned.find("[")) if position >= 0]
            if not starts:
                raise RuntimeError(f"Ollama did not return JSON: {text[:200]}")
            start = min(starts)
            end = max(cleaned.rfind("}"), cleaned.rfind("]"))
            if end < start:
                raise RuntimeError(f"Ollama returned incomplete JSON: {text[:200]}")
            return json.loads(cleaned[start : end + 1])

    def embed(self, model: str, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        payload = {"model": model, "input": texts, "keep_alive": self.keep_alive}
        response = self._post("/api/embed", payload)
        embeddings = response.get("embeddings")
        if not isinstance(embeddings, list) or len(embeddings) != len(texts):
            raise RuntimeError("Ollama embedding count does not match input count")
        return embeddings


__all__ = ["OllamaClient"]

