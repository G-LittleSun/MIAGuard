from types import SimpleNamespace

import pytest
import torch

from miaguard.model_client import (
    ModelClient,
    _candidate_token_ids,
    _contextual_candidate_token_ids,
    _has_complete_json_value,
    _restricted_probabilities,
)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ('{"risk_score":0.7}', True),
        ('```json\n{"evidence":["a}","b"]}\n```', True),
        ('{"risk_score":0.7', False),
        ('plain text', False),
        ('{"value":[1,2}', False),
    ],
)
def test_complete_json_detection(text: str, expected: bool) -> None:
    assert _has_complete_json_value(text) is expected


def test_generate_json_accepts_trailing_model_commentary():
    client = object.__new__(ModelClient)
    client.generate = lambda *args, **kwargs: (  # type: ignore[method-assign]
        '{"answers":["yes"]}\nThe answer follows from the corpus.'
    )

    assert client.generate_json("model", "prompt") == {"answers": ["yes"]}


def test_generate_json_repairs_latex_dollar_escape():
    client = object.__new__(ModelClient)
    client.generate = lambda *args, **kwargs: (  # type: ignore[method-assign]
        '{"summary":"A \\$225 million complex"}'
    )

    assert client.generate_json("model", "prompt") == {
        "summary": "A $225 million complex"
    }


def test_generate_json_repairs_markdown_escaped_field_names():
    client = object.__new__(ModelClient)
    client.generate = lambda *args, **kwargs: (  # type: ignore[method-assign]
        '{"risk\\_score":0.8,"evidence\\_codes":[]}'
    )

    assert client.generate_json("model", "prompt") == {
        "risk_score": 0.8,
        "evidence_codes": [],
    }


class _CandidateTokenizer:
    def __call__(self, text, **kwargs):
        assert kwargs["add_special_tokens"] is False
        mapping = {"A": [11], "B": [12], "C": [13], "BAD": [14, 15]}
        return {"input_ids": mapping[text]}


def test_candidate_labels_must_each_be_one_token() -> None:
    assert _candidate_token_ids(_CandidateTokenizer(), ("A", "B", "C")) == {
        "A": 11,
        "B": 12,
        "C": 13,
    }
    with pytest.raises(ValueError, match="single token"):
        _candidate_token_ids(_CandidateTokenizer(), ("A", "BAD", "C"))


class _ContextTokenizer:
    def __call__(self, text, **kwargs):
        assert kwargs["add_special_tokens"] is False
        mapping = {
            "prompt": [7, 8],
            "promptA": [7, 8, 11],
            "promptB": [7, 8, 12],
            "promptC": [7, 8, 13],
        }
        return {"input_ids": mapping[text]}


def test_candidate_labels_are_validated_in_final_prompt_context() -> None:
    assert _contextual_candidate_token_ids(
        _ContextTokenizer(), "prompt", ("A", "B", "C"), add_special_tokens=False
    ) == {"A": 11, "B": 12, "C": 13}


class _BoundaryChangingTokenizer:
    def __call__(self, text, **kwargs):
        mapping = {"prompt": [7, 8], "promptA": [7, 9]}
        return {"input_ids": mapping[text]}


def test_contextual_candidate_rejects_boundary_retokenization() -> None:
    with pytest.raises(ValueError, match="final prompt context"):
        _contextual_candidate_token_ids(
            _BoundaryChangingTokenizer(),
            "prompt",
            ("A", "B"),
            add_special_tokens=False,
        )


def test_restricted_probabilities_normalize_only_candidates() -> None:
    result = _restricted_probabilities({"A": 0.0, "B": 1.0, "C": 2.0})

    assert set(result) == {"A", "B", "C"}
    assert sum(result.values()) == pytest.approx(1.0)
    assert result["C"] > result["B"] > result["A"]


class _Batch(dict):
    def to(self, device: str):
        assert device == "cuda"
        return self


class _ProbabilityTokenizer:
    chat_template = "template"

    def __init__(self) -> None:
        self.rendered_messages = None
        self.prompt = None

    def apply_chat_template(self, messages, **kwargs):
        self.rendered_messages = messages
        assert kwargs == {"tokenize": False, "add_generation_prompt": True}
        return "rendered prompt"

    def __call__(self, text, **kwargs):
        contextual_ids = {
            "rendered promptA": [7, 8, 1],
            "rendered promptB": [7, 8, 2],
            "rendered promptC": [7, 8, 3],
        }
        if text in contextual_ids:
            return {"input_ids": contextual_ids[text]}
        self.prompt = text
        return _Batch(
            input_ids=torch.tensor([[7, 8]]),
            attention_mask=torch.tensor([[1, 1]]),
        )


class _ProbabilityModel:
    def __init__(self) -> None:
        self.calls = 0

    def __call__(self, **inputs):
        self.calls += 1
        assert set(inputs) == {"input_ids", "attention_mask"}
        logits = torch.zeros((1, 2, 8), dtype=torch.float32)
        logits[0, -1, 1:4] = torch.tensor([0.0, 1.0, 2.0])
        return SimpleNamespace(logits=logits)


def test_candidate_label_probabilities_uses_one_forward_pass() -> None:
    tokenizer = _ProbabilityTokenizer()
    model = _ProbabilityModel()
    client = object.__new__(ModelClient)
    client.config = SimpleNamespace(generation_backend="transformers")
    client._load_generation = lambda model_name: (model, tokenizer)  # type: ignore[method-assign]

    result = client.candidate_label_probabilities(
        "judge-model",
        "choose one label",
        labels=("A", "B", "C"),
        system="security system",
    )

    assert list(result) == ["A", "B", "C"]
    assert sum(result.values()) == pytest.approx(1.0)
    assert result["C"] > result["B"] > result["A"]
    assert tokenizer.rendered_messages == [
        {"role": "user", "content": "security system\n\nchoose one label"}
    ]
    assert tokenizer.prompt == "rendered prompt"
    assert model.calls == 1


def test_candidate_label_probabilities_rejects_ollama() -> None:
    client = object.__new__(ModelClient)
    client.config = SimpleNamespace(generation_backend="ollama")

    with pytest.raises(RuntimeError, match="require transformers backend"):
        client.candidate_label_probabilities("model", "prompt", labels=("A", "B"))
