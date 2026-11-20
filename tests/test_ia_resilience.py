from miaguard.ia_attack import _generate_json_with_retry, _generate_questions


class _RetryClient:
    def __init__(self) -> None:
        self.calls = []

    def generate_json(self, model, prompt, **kwargs):
        self.calls.append((model, prompt, kwargs))
        if len(self.calls) == 1:
            raise RuntimeError("invalid JSON")
        return {"questions": ["valid"]}


def test_ia_json_retry_uses_compact_deterministic_prompt() -> None:
    client = _RetryClient()

    value = _generate_json_with_retry(
        client,  # type: ignore[arg-type]
        "model",
        "original prompt",
        128,
        0.2,
    )

    assert value == {"questions": ["valid"]}
    assert len(client.calls) == 2
    assert "compact, valid JSON" in client.calls[1][1]
    assert client.calls[1][2]["max_tokens"] == 256
    assert client.calls[1][2]["temperature"] == 0.0


class _CaptureClient:
    def __init__(self) -> None:
        self.prompt = ""

    def generate_json(self, model, prompt, **kwargs):
        self.prompt = prompt
        return {"summary": "topic", "questions": ["Is it present?"]}


def test_ia_question_prompt_replaces_corpus_double_quotes() -> None:
    client = _CaptureClient()

    summary, questions = _generate_questions(
        'The phrase "under God" appears.',
        1,
        client,  # type: ignore[arg-type]
        "model",
        128,
    )

    assert summary == "topic"
    assert questions == ["Is it present?"]
    assert 'The phrase \'under God\' appears.' in client.prompt
    assert "Generate one question with a definite yes or no answer." in client.prompt
    assert "Include both questions" not in client.prompt
