from __future__ import annotations

import json
import re
from collections import Counter
from types import SimpleNamespace

import pytest
import miaguard.query_bank.builder as query_bank_builder

from miaguard.query_bank.builder import (
    _benign_queries,
    _ia_candidates,
    _paraphrases,
    _parse_query_list,
    _verify_ia_answers,
    build_document_records,
    validate_manifest_identity,
)
from miaguard.query_bank.schema import QueryBankBuildConfig


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ("Did Newman dominate Dover?", True),
        ("Was Gordon the points leader?", True),
        ("Who took the points lead?", False),
        ("What happened at Dover?", False),
    ],
)
def test_safe_yes_anchor_detection(question: str, expected: bool) -> None:
    assert hasattr(query_bank_builder, "_is_safe_yes_anchor")
    assert query_bank_builder._is_safe_yes_anchor(question) is expected


def test_polarity_flip_inserts_and_removes_not_after_auxiliary() -> None:
    assert hasattr(query_bank_builder, "_flip_question_polarity")
    assert query_bank_builder._flip_question_polarity(
        "Did Newman dominate Dover?"
    ) == "Did Newman not dominate Dover?"
    assert query_bank_builder._flip_question_polarity(
        "Did Newman not dominate Dover?"
    ) == "Did Newman dominate Dover?"


def test_yes_anchor_generation_accepts_only_safe_verified_yes_questions() -> None:
    assert hasattr(query_bank_builder, "_ia_yes_anchor_candidates")
    build_config = QueryBankBuildConfig(
        source_run_id="run-1",
        attack_config_path=SimpleNamespace(),
        seed=17,
        member_count=1,
        nonmember_count=1,
        paraphrases_per_attack=4,
        ia_questions_per_document=30,
        ia_batch_size=6,
        ia_max_attempts=3,
        benign_categories=("topic", "entity", "event", "summary", "follow_up"),
    )
    attack_config = SimpleNamespace(
        generation_model="local-model",
        embedding_model="embedding-model",
        ia_generation_max_tokens=128,
    )

    _summary, anchors = query_bank_builder._ia_yes_anchor_candidates(
        "Alpha Corp acquired Beta Labs.",
        build_config,
        attack_config,
        _FakeClient(),
        target_count=2,
    )

    assert len(anchors) == 2
    assert {item["ground_truth"] for item in anchors} == {"yes"}
    assert all(
        query_bank_builder._is_safe_yes_anchor(item["question"])
        for item in anchors
    )


def test_yes_anchor_generation_uses_explicit_fact_strategies_only() -> None:
    build_config = QueryBankBuildConfig(
        source_run_id="run-1",
        attack_config_path=SimpleNamespace(),
        seed=17,
        member_count=1,
        nonmember_count=1,
        paraphrases_per_attack=4,
        ia_questions_per_document=30,
        ia_batch_size=6,
        ia_max_attempts=3,
        benign_categories=("topic", "entity", "event", "summary", "follow_up"),
    )
    attack_config = SimpleNamespace(
        generation_model="local-model",
        embedding_model="embedding-model",
        ia_generation_max_tokens=128,
    )
    client = _FakeClient()

    query_bank_builder._ia_yes_anchor_candidates(
        "Alpha Corp acquired Beta Labs.",
        build_config,
        attack_config,
        client,
        target_count=1,
    )

    prompt = next(
        item for item in client.prompts if "[IA_CANDIDATES]" in item
    )
    assert "answer must be yes for every question" in prompt
    assert "use negated factual questions" not in prompt
    assert "details not explicitly established" not in prompt


def test_yes_fact_templates_produce_safe_independently_verified_anchors() -> None:
    assert hasattr(query_bank_builder, "_ia_yes_candidates_from_facts")

    class _FactClient(_FakeClient):
        def generate_json(self, model, prompt, **kwargs):
            if "[IA_NO_FACTS]" in prompt:
                return {
                    "facts": [
                        {
                            "subject": "Troy Polamalu",
                            "attribute": "team role",
                            "value": "Steelers safety",
                            "statement": "Troy Polamalu was a Steelers safety",
                        }
                    ]
                }
            if "[IA_VERIFY]" in prompt:
                questions = re.findall(r"^\d+\. (.+)$", prompt, flags=re.MULTILINE)
                return {"answers": ["yes"] * len(questions)}
            return super().generate_json(model, prompt, **kwargs)

    _summary, anchors = query_bank_builder._ia_yes_candidates_from_facts(
        "Troy Polamalu was a Steelers safety.",
        SimpleNamespace(
            generation_model="local-model",
            ia_generation_max_tokens=128,
        ),
        _FactClient(),
        target_count=5,
        existing_questions=(),
    )

    assert len(anchors) == 5
    assert {item["ground_truth"] for item in anchors} == {"yes"}
    assert all(
        query_bank_builder._is_safe_yes_anchor(item["question"])
        for item in anchors
    )


def test_yes_fact_templates_fall_back_to_cleaned_source_claim() -> None:
    class _SourceClaimClient(_FakeClient):
        def generate_json(self, model, prompt, **kwargs):
            if "[IA_NO_FACTS]" in prompt:
                return {"facts": []}
            if "[IA_VERIFY]" in prompt:
                questions = re.findall(r"^\d+\. (.+)$", prompt, flags=re.MULTILINE)
                return {"answers": ["yes"] * len(questions)}
            return super().generate_json(model, prompt, **kwargs)

    _summary, anchors = query_bank_builder._ia_yes_candidates_from_facts(
        "Headline (AP) AP - Troy Polamalu was a Steelers safety.",
        SimpleNamespace(
            generation_model="local-model",
            ia_generation_max_tokens=128,
        ),
        _SourceClaimClient(),
        target_count=4,
        existing_questions=(),
    )

    assert len(anchors) == 4
    assert all(
        "Troy Polamalu was a Steelers safety" in item["question"]
        for item in anchors
    )
    assert all("Headline" not in item["question"] for item in anchors)


def test_no_fact_templates_fall_back_to_cleaned_source_claim() -> None:
    class _SourceClaimClient(_FakeClient):
        def generate_json(self, model, prompt, **kwargs):
            if "[IA_NO_FACTS]" in prompt:
                return {"facts": []}
            if "[IA_VERIFY]" in prompt:
                questions = re.findall(r"^\d+\. (.+)$", prompt, flags=re.MULTILINE)
                return {"answers": ["no"] * len(questions)}
            return super().generate_json(model, prompt, **kwargs)

    _summary, candidates = query_bank_builder._ia_no_candidates_from_facts(
        "Headline (AP) AP - Troy Polamalu was a Steelers safety.",
        QueryBankBuildConfig(
            source_run_id="run-1",
            attack_config_path=SimpleNamespace(),
            seed=17,
            member_count=1,
            nonmember_count=1,
            paraphrases_per_attack=4,
            ia_questions_per_document=30,
            ia_batch_size=6,
            ia_max_attempts=3,
            benign_categories=("topic", "entity", "event", "summary", "follow_up"),
        ),
        SimpleNamespace(
            generation_model="local-model",
            ia_generation_max_tokens=128,
        ),
        _SourceClaimClient(),
        target_count=4,
        existing_questions=(),
    )

    assert len(candidates) == 4
    assert all(
        "Troy Polamalu was a Steelers safety" in item["question"]
        for item in candidates
    )
    assert {item["ground_truth"] for item in candidates} == {"no"}


def test_counterfactual_no_uses_each_anchor_once() -> None:
    assert hasattr(query_bank_builder, "_ia_no_candidates_from_anchors")

    class _CounterfactualClient(_FakeClient):
        def generate_json(self, model, prompt, **kwargs):
            if "[IA_ANCHOR_COUNTERFACTUAL]" in prompt:
                self.prompts.append(prompt)
                if "Verified true anchor:\nDid Ryan Newman" in prompt:
                    return {"questions": ["Did Ryan Newman dominate Charlotte?"]}
                return {"questions": ["Did Jeff Gordon lose the standings lead?"]}
            if "IA_VERIFY" in prompt:
                self.prompts.append(prompt)
                questions = re.findall(r"^\d+\. (.+)$", prompt, flags=re.MULTILINE)
                return {"answers": ["no"] * len(questions)}
            return super().generate_json(model, prompt, **kwargs)

    rows = query_bank_builder._ia_no_candidates_from_anchors(
        text="Ryan Newman dominated Dover while Jeff Gordon led the standings.",
        anchors=(
            "Did Ryan Newman dominate Dover?",
            "Did Jeff Gordon lead the standings?",
        ),
        target_count=2,
        existing_questions=(),
        attack_config=SimpleNamespace(
            generation_model="local-model",
            ia_generation_max_tokens=128,
        ),
        client=_CounterfactualClient(),
    )

    assert len(rows) == 2
    assert len({row["anchor_question"] for row in rows}) == 2
    assert {row["ground_truth"] for row in rows} == {"no"}
    assert {row["construction"] for row in rows} == {"counterfactual"}


def test_polarity_fallback_runs_after_counterfactual_rejection() -> None:
    assert hasattr(query_bank_builder, "_ia_no_candidates_from_anchors")

    class _FallbackClient(_FakeClient):
        def generate_json(self, model, prompt, **kwargs):
            if "[IA_ANCHOR_COUNTERFACTUAL]" in prompt:
                self.prompts.append(prompt)
                return {"questions": ["Did Ryan Newman dominate Dover?"]}
            if "IA_VERIFY" in prompt:
                self.prompts.append(prompt)
                questions = re.findall(r"^\d+\. (.+)$", prompt, flags=re.MULTILINE)
                return {
                    "answers": [
                        "no" if " not " in question.casefold() else "yes"
                        for question in questions
                    ]
                }
            return super().generate_json(model, prompt, **kwargs)

    rows = query_bank_builder._ia_no_candidates_from_anchors(
        text="Ryan Newman dominated Dover.",
        anchors=("Did Ryan Newman dominate Dover?",),
        target_count=1,
        existing_questions=(),
        attack_config=SimpleNamespace(
            generation_model="local-model",
            ia_generation_max_tokens=128,
        ),
        client=_FallbackClient(),
    )

    assert rows == [
        {
            "question": "Did Ryan Newman not dominate Dover?",
            "ground_truth": "no",
            "anchor_question": "Did Ryan Newman dominate Dover?",
            "construction": "polarity_flip",
        }
    ]


class _FakeClient:
    def __init__(self) -> None:
        self.prompts: list[str] = []
        self.config = SimpleNamespace(generation_backend="transformers")
        self.ia_question_index = 0

    def generate_json(self, model, prompt, **kwargs):
        self.prompts.append(prompt)
        if "IA_NO_FACTS" in prompt:
            return {
                "facts": [
                    {
                        "subject": "Alpha Corp",
                        "attribute": "acquisition target",
                        "value": "Beta Labs",
                    }
                ]
            }
        if "IA_NO_CONTRADICTIONS" in prompt:
            prompt = prompt.replace("[IA_NO_CONTRADICTIONS]", "[IA_CANDIDATES]")
        if "Select exactly one contextually difficult-to-predict word" in prompt:
            return {"words": ["acquired"]}
        if "DIRECT_PARAPHRASE" in prompt:
            return {
                "queries": [
                    f"Direct equivalent query {index}" for index in range(1, 5)
                ]
            }
        if "S2_PARAPHRASE" in prompt:
            return {
                "queries": [
                    f"Continue the protected opening variant {index}"
                    for index in range(1, 5)
                ]
            }
        if "MASKED_PARAPHRASE" in prompt:
            return {
                "queries": [
                    f"Recover every omitted value variant {index}: [Mask_1]"
                    for index in range(1, 5)
                ]
            }
        if "IA_CANDIDATES" in prompt:
            match = re.search(
                r"generate exactly (\d+) new",
                prompt,
                flags=re.IGNORECASE,
            )
            if match is None:
                raise AssertionError(f"Missing IA requested count: {prompt[:120]}")
            count = int(match.group(1))
            questions = []
            for _ in range(count):
                self.ia_question_index += 1
                questions.append(
                    f"Did documented fact {self.ia_question_index} happen?"
                )
            return {
                "summary": "Alpha acquisition",
                "questions": questions,
            }
        if "IA_VERIFY" in prompt:
            questions = re.findall(r"^\d+\. (.+)$", prompt, flags=re.MULTILINE)
            if any(
                question.startswith(
                    (
                        "Is it false that",
                        "Is it untrue that",
                        "Does the claim that",
                        "Is the claim that",
                        "Can it be said that",
                        "Is it wrong to say that",
                        "Is the statement",
                        "Is '",
                    )
                )
                for question in questions
            ):
                return {"answers": ["no"] * len(questions)}
            answers = ("yes", "no", "unknown")
            return {
                "answers": [
                    answers[(index - 1) % len(answers)]
                    for index, _question in enumerate(questions, start=1)
                ]
            }
        if "BENIGN_QUERIES" in prompt:
            return {
                "topic": "What broad topic does this report cover?",
                "entity": "Which organization is central to the report?",
                "event": "What main event is described?",
                "summary": "Give a short high-level summary.",
                "follow_up": "What related topic could a reader research?",
            }
        raise AssertionError(f"Unexpected prompt: {prompt[:80]}")

    def generate(self, model, prompt, **kwargs):
        self.prompts.append(prompt)
        if "IA_VERIFY_PLAIN" in prompt:
            questions = re.findall(r"^\d+\. (.+)$", prompt, flags=re.MULTILINE)
            return "\n".join(
                ("yes", "no", "unknown")[(index - 1) % 3]
                for index, _question in enumerate(questions, start=1)
            )
        marker = next(
            value
            for value in (
                "DIRECT_PARAPHRASE",
                "S2_PARAPHRASE",
                "MASKED_PARAPHRASE",
            )
            if value in prompt
        )
        return json.dumps(
            {
                "queries": [
                    f"{marker} equivalent query {index}"
                    for index in range(1, 5)
                ]
            }
        )

    def embed(self, model, texts):
        raise AssertionError("IA generation must not use semantic embeddings")


class _RetryingIaClient(_FakeClient):
    def __init__(self) -> None:
        super().__init__()
        self.failed_once = False

    def generate_json(self, model, prompt, **kwargs):
        if "IA_CANDIDATES" in prompt and not self.failed_once:
            self.failed_once = True
            raise RuntimeError("Model did not return JSON")
        return super().generate_json(model, prompt, **kwargs)


class _DuplicateIaClient(_FakeClient):
    def __init__(self) -> None:
        super().__init__()
        self.ia_candidate_calls = 0

    def generate_json(self, model, prompt, **kwargs):
        if "IA_CANDIDATES" not in prompt:
            return super().generate_json(model, prompt, **kwargs)
        self.prompts.append(prompt)
        match = re.search(
            r"generate exactly (\d+) new",
            prompt,
            flags=re.IGNORECASE,
        )
        if match is None:
            raise AssertionError(f"Missing IA requested count: {prompt[:120]}")
        count = int(match.group(1))
        self.ia_candidate_calls += 1
        questions = []
        if self.ia_candidate_calls == 2:
            questions.append("Did documented fact 1 happen?")
        while len(questions) < count:
            self.ia_question_index += 1
            questions.append(
                f"Did documented fact {self.ia_question_index} happen?"
            )
        return {"summary": "Alpha acquisition", "questions": questions}


class _NonMappingBenignClient(_FakeClient):
    def __init__(self) -> None:
        super().__init__()
        self.benign_calls = 0

    def generate_json(self, model, prompt, **kwargs):
        if "BENIGN_QUERIES" in prompt:
            self.benign_calls += 1
            if self.benign_calls == 1:
                self.prompts.append(prompt)
                return ["not", "an", "object"]
        return super().generate_json(model, prompt, **kwargs)


class _FailingVerificationIaClient(_FakeClient):
    def __init__(self) -> None:
        super().__init__()
        self.verification_failures_remaining = 2

    def generate_json(self, model, prompt, **kwargs):
        if (
            "IA_VERIFY" in prompt
            and self.verification_failures_remaining > 0
        ):
            self.prompts.append(prompt)
            self.verification_failures_remaining -= 1
            raise RuntimeError("Model returned incomplete JSON")
        return super().generate_json(model, prompt, **kwargs)


class _OverproducingIaClient(_FakeClient):
    def __init__(self) -> None:
        super().__init__()
        self.requested_counts: list[int] = []

    def generate_json(self, model, prompt, **kwargs):
        if "IA_CANDIDATES" not in prompt:
            return super().generate_json(model, prompt, **kwargs)
        self.prompts.append(prompt)
        match = re.search(
            r"generate exactly (-?\d+) new",
            prompt,
            flags=re.IGNORECASE,
        )
        if match is None:
            raise AssertionError(f"Missing IA requested count: {prompt[:120]}")
        requested = int(match.group(1))
        self.requested_counts.append(requested)
        questions = []
        for _ in range(40):
            self.ia_question_index += 1
            questions.append(
                f"Did overproduced documented fact {self.ia_question_index} happen?"
            )
        return {"summary": "Alpha acquisition", "questions": questions}


class _PlainTextVerificationFallbackClient(_FakeClient):
    def __init__(self) -> None:
        super().__init__()
        self.ia_candidate_calls = 0

    def generate_json(self, model, prompt, **kwargs):
        if "IA_CANDIDATES" in prompt:
            self.ia_candidate_calls += 1
        if "IA_VERIFY" in prompt:
            self.prompts.append(prompt)
            raise RuntimeError("Model returned incomplete JSON")
        return super().generate_json(model, prompt, **kwargs)

    def generate(self, model, prompt, **kwargs):
        if "IA_VERIFY_PLAIN" in prompt:
            self.prompts.append(prompt)
            questions = re.findall(r"^\d+\. (.+)$", prompt, flags=re.MULTILINE)
            return "\n".join(
                f"{index}. {('yes', 'no', 'unknown')[(index - 1) % 3]}"
                for index, _question in enumerate(questions, start=1)
            )
        return super().generate(model, prompt, **kwargs)


class _IncompleteBenignClient(_FakeClient):
    def __init__(self) -> None:
        super().__init__()
        self.repaired_categories: list[str] = []

    def generate_json(self, model, prompt, **kwargs):
        if "BENIGN_QUERIES" in prompt:
            self.prompts.append(prompt)
            raise RuntimeError("Model returned incomplete JSON")
        return super().generate_json(model, prompt, **kwargs)

    def generate(self, model, prompt, **kwargs):
        if "BENIGN_FIELD:" in prompt:
            self.prompts.append(prompt)
            match = re.search(r"\[BENIGN_FIELD:([a-z_]+)]", prompt)
            if match is None:
                raise AssertionError(f"Missing benign category: {prompt[:120]}")
            category = match.group(1)
            self.repaired_categories.append(category)
            return f"What legitimate {category} question applies here?"
        return super().generate(model, prompt, **kwargs)


class _SingletonListBenignClient(_FakeClient):
    def __init__(self) -> None:
        super().__init__()
        self.benign_calls = 0

    def generate_json(self, model, prompt, **kwargs):
        if "BENIGN_QUERIES" in prompt:
            self.prompts.append(prompt)
            self.benign_calls += 1
            return [
                {
                    "topic": "What broad topic does this report cover?",
                    "entity": "Which organization is central to the report?",
                    "event": "What main event is described?",
                    "summary": "Give a short high-level summary.",
                    "follow_up": "What related topic could a reader research?",
                }
            ]
        return super().generate_json(model, prompt, **kwargs)


class _RetryingParaphraseClient(_FakeClient):
    def __init__(self) -> None:
        super().__init__()
        self.paraphrase_calls = 0

    def generate(self, model, prompt, **kwargs):
        if "DIRECT_PARAPHRASE" in prompt:
            self.prompts.append(prompt)
            self.paraphrase_calls += 1
            if self.paraphrase_calls == 1:
                return json.dumps(
                    {
                        "queries": [
                            "First equivalent instruction",
                            1,
                            "Second equivalent instruction",
                            2,
                            "Third equivalent instruction",
                        ]
                    }
                )
            return json.dumps(
                {
                    "queries": [
                        f"Recovered equivalent instruction {index}"
                        for index in range(1, 5)
                    ]
                }
            )
        return super().generate(model, prompt, **kwargs)


class _PlainCandidateFallbackClient(_FakeClient):
    def __init__(self) -> None:
        super().__init__()
        self.plain_candidate_calls = 0

    def generate_json(self, model, prompt, **kwargs):
        if "IA_CANDIDATES" in prompt:
            self.prompts.append(prompt)
            raise RuntimeError("Model returned incomplete JSON")
        return super().generate_json(model, prompt, **kwargs)

    def generate(self, model, prompt, **kwargs):
        if "IA_CANDIDATES_PLAIN" in prompt:
            self.prompts.append(prompt)
            self.plain_candidate_calls += 1
            match = re.search(
                r"generate up to (\d+) new",
                prompt,
                flags=re.IGNORECASE,
            )
            if match is None:
                raise AssertionError(
                    f"Missing IA fallback requested count: {prompt[:120]}"
                )
            count = int(match.group(1))
            questions = []
            for _ in range(count):
                self.ia_question_index += 1
                questions.append(
                    f"Q{len(questions) + 1}: "
                    f"Did fallback fact {self.ia_question_index} happen?"
                )
            return "\n".join(["SUMMARY: Alpha acquisition", *questions])
        return super().generate(model, prompt, **kwargs)


class _PartialIndexedVerificationClient(_FakeClient):
    def __init__(self) -> None:
        super().__init__()
        self.indexed_prompts: list[str] = []
        self.single_indexes: list[int] = []

    def generate_json(self, model, prompt, **kwargs):
        if "IA_VERIFY" in prompt:
            self.prompts.append(prompt)
            return {"answers": ["yes", "invalid", "unknown"]}
        return super().generate_json(model, prompt, **kwargs)

    def generate(self, model, prompt, **kwargs):
        if "IA_VERIFY_INDEXED" in prompt:
            self.prompts.append(prompt)
            self.indexed_prompts.append(prompt)
            return "2=no\n4=yes"
        match = re.search(r"\[IA_VERIFY_SINGLE:(\d+)]", prompt)
        if match is not None:
            self.prompts.append(prompt)
            index = int(match.group(1))
            self.single_indexes.append(index)
            return "unknown" if index == 5 else "no"
        return super().generate(model, prompt, **kwargs)


class _TailOversamplingIaClient(_FakeClient):
    def __init__(self) -> None:
        super().__init__()
        self.candidate_calls = 0
        self.requested_counts: list[int] = []

    def generate_json(self, model, prompt, **kwargs):
        if "IA_CANDIDATES" not in prompt:
            return super().generate_json(model, prompt, **kwargs)
        self.prompts.append(prompt)
        match = re.search(
            r"generate exactly (\d+) new",
            prompt,
            flags=re.IGNORECASE,
        )
        if match is None:
            raise AssertionError(f"Missing IA requested count: {prompt[:120]}")
        requested = int(match.group(1))
        self.requested_counts.append(requested)
        self.candidate_calls += 1
        if self.candidate_calls <= 4:
            start = (self.candidate_calls - 1) * 6 + 1
            questions = [
                f"Did tail fact {index} happen?"
                for index in range(start, start + 6)
            ]
        elif self.candidate_calls == 5:
            questions = [
                *(f"Did tail fact {index} happen?" for index in range(25, 30)),
                "Did tail fact 1 happen?",
            ]
        elif requested == 6:
            questions = [
                *(f"Did tail fact {index} happen?" for index in range(1, 6)),
                "Did tail fact 30 happen?",
            ]
        else:
            questions = ["Did tail fact 1 happen?"] * requested
        return {"summary": "Tail acquisition", "questions": questions}


class _NoveltyRepairIaClient(_FakeClient):
    def __init__(self) -> None:
        super().__init__()
        self.primary_calls = 0
        self.repair_calls = 0
        self.repair_question_index = 6

    def generate_json(self, model, prompt, **kwargs):
        if "IA_CANDIDATES" not in prompt:
            return super().generate_json(model, prompt, **kwargs)
        self.prompts.append(prompt)
        self.primary_calls += 1
        if self.primary_calls == 1:
            questions = [
                f"Did primary fact {index} happen?"
                for index in range(1, 7)
            ]
        else:
            questions = [
                f"Did primary fact {index} happen?"
                for index in range(1, 7)
            ]
        return {"summary": "Alpha acquisition", "questions": questions}

    def generate(self, model, prompt, **kwargs):
        if "IA_CANDIDATES_NOVELTY_REPAIR" in prompt:
            self.prompts.append(prompt)
            self.repair_calls += 1
            questions = []
            for index in range(1, 7):
                self.repair_question_index += 1
                questions.append(
                    f"Q{index}: Did repaired fact "
                    f"{self.repair_question_index} happen?"
                )
            return "\n".join(["SUMMARY: Alpha acquisition", *questions])
        return super().generate(model, prompt, **kwargs)


def test_build_document_records_creates_complete_teacher_aligned_pool() -> None:
    build_config = QueryBankBuildConfig(
        source_run_id="run-1",
        attack_config_path=SimpleNamespace(),
        seed=17,
        member_count=1,
        nonmember_count=1,
        paraphrases_per_attack=4,
        ia_questions_per_document=30,
        ia_batch_size=30,
        ia_max_attempts=2,
        benign_categories=("topic", "entity", "event", "summary", "follow_up"),
    )
    attack_config = SimpleNamespace(
        generation_backend="transformers",
        generation_model="local-model",
        embedding_model="embedding-model",
        s2_mia_prefix_words=5,
        mask_count=1,
        masked_max_tokens=64,
        ia_generation_max_tokens=512,
    )
    client = _FakeClient()

    records = build_document_records(
        dataset_id="ag_news",
        document={
            "doc_id": "doc-1",
            "membership_label": 1,
            "text": "Alpha Corp acquired Beta Labs in Paris on Monday.",
        },
        build_config=build_config,
        attack_config=attack_config,
        client=client,
    )

    assert len(records) == 50
    assert Counter(row["attack_type"] for row in records) == {
        "direct_rag_mia": 5,
        "s2_mia": 5,
        "masked_mia": 5,
        "ia": 30,
        "benign": 5,
    }
    assert Counter(
        row["payload"]["ground_truth"]
        for row in records
        if row["attack_type"] == "ia"
    ) == {"yes": 15, "no": 15}
    ia_prompts = [
        prompt
        for prompt in client.prompts
        if "[IA_CANDIDATES]" in prompt
    ]
    assert any(
        "correct source-grounded answer must be yes" in prompt
        for prompt in ia_prompts
    )
    assert any("[IA_NO_FACTS]" in prompt for prompt in client.prompts)
    assert not any("[IA_NO_CONTRADICTIONS]" in prompt for prompt in client.prompts)
    assert all("membership_label" not in prompt for prompt in client.prompts)
    paraphrase_prompts = [
        prompt for prompt in client.prompts if "PARAPHRASE" in prompt
    ]
    assert all(
        "Alpha Corp acquired Beta Labs" not in prompt
        for prompt in paraphrase_prompts
    )
    direct_paraphrases = [
        row
        for row in records
        if row["attack_type"] == "direct_rag_mia"
        and row["variant_type"] == "paraphrase"
    ]
    assert all(
        "Alpha Corp acquired Beta Labs in Paris on Monday."
        in row["query_text"]
        for row in direct_paraphrases
    )
    masked = [row for row in records if row["attack_type"] == "masked_mia"]
    assert len({row["payload"]["masked_text"] for row in masked}) == 1
    assert len(
        {
            tuple(row["payload"]["answers"])
            for row in masked
        }
    ) == 1


def test_manifest_identity_rejects_reusing_bank_id_with_new_config() -> None:
    manifest = {
        "source_run_id": "run-1",
        "seed": 17,
        "generation_model": "local-model",
        "embedding_model": "embedding-model",
    }

    validate_manifest_identity(
        manifest,
        source_run_id="run-1",
        seed=17,
        generation_model="local-model",
        embedding_model="embedding-model",
    )

    with pytest.raises(ValueError, match="new bank_id"):
        validate_manifest_identity(
            manifest,
            source_run_id="run-1",
            seed=18,
            generation_model="local-model",
            embedding_model="embedding-model",
        )


def test_parse_query_list_accepts_mistral_numbered_output() -> None:
    text = """1. Query 1: Does the first claim appear? Answer Yes or No.
2. Query 2: Can the evidence confirm the second claim? Answer Yes or No.
3. Query 3: Is the quoted statement present? Answer Yes or No.
4. Query 4: Does the context substantiate the quotation? Answer Yes or No."""

    assert _parse_query_list(text, 4) == [
        "Does the first claim appear? Answer Yes or No.",
        "Can the evidence confirm the second claim? Answer Yes or No.",
        "Is the quoted statement present? Answer Yes or No.",
        "Does the context substantiate the quotation? Answer Yes or No.",
    ]


def test_parse_query_list_ignores_numeric_array_markers() -> None:
    text = json.dumps(
        {
            "queries": [
                "First equivalent instruction",
                1,
                "Second equivalent instruction",
                2,
                "Third equivalent instruction",
                3,
                "Fourth equivalent instruction",
                4,
            ]
        }
    )

    assert _parse_query_list(text, 4) == [
        "First equivalent instruction",
        "Second equivalent instruction",
        "Third equivalent instruction",
        "Fourth equivalent instruction",
    ]


def test_paraphrase_generation_retries_after_wrong_query_count() -> None:
    client = _RetryingParaphraseClient()

    queries = _paraphrases(
        client,
        "local-model",
        "DIRECT_PARAPHRASE",
        "Determine whether the Context contains the target text.",
        4,
        128,
    )

    assert queries == [
        "Recovered equivalent instruction 1",
        "Recovered equivalent instruction 2",
        "Recovered equivalent instruction 3",
        "Recovered equivalent instruction 4",
    ]
    assert client.paraphrase_calls == 2


def test_ia_generation_retries_one_invalid_json_response() -> None:
    build_config = QueryBankBuildConfig(
        source_run_id="run-1",
        attack_config_path=SimpleNamespace(),
        seed=17,
        member_count=1,
        nonmember_count=1,
        paraphrases_per_attack=4,
        ia_questions_per_document=30,
        ia_batch_size=6,
        ia_max_attempts=6,
        benign_categories=("topic", "entity", "event", "summary", "follow_up"),
    )
    attack_config = SimpleNamespace(
        generation_model="local-model",
        embedding_model="embedding-model",
        ia_generation_max_tokens=512,
    )

    summary, candidates = _ia_candidates(
        "Alpha Corp acquired Beta Labs.",
        build_config,
        attack_config,
        _RetryingIaClient(),
    )

    assert summary == "Alpha acquisition"
    assert len(candidates) == 30


def test_ia_no_candidates_are_programmatically_negated_facts() -> None:
    class _NoFactClient(_FakeClient):
        def generate_json(self, model, prompt, **kwargs):
            if "[IA_NO_FACTS]" in prompt:
                self.prompts.append(prompt)
                return {
                    "facts": [
                        {
                            "subject": "Alpha Corp",
                            "attribute": "acquisition target",
                            "value": "Beta Labs",
                            "statement": "Alpha Corp acquired Beta Labs",
                        }
                    ]
                }
            if "IA_VERIFY" in prompt:
                self.prompts.append(prompt)
                questions = re.findall(r"^\d+\. (.+)$", prompt, flags=re.MULTILINE)
                return {"answers": ["no"] * len(questions)}
            if "[IA_NO_CONTRADICTIONS]" in prompt:
                self.prompts.append(prompt)
                return super().generate_json(
                    model,
                    prompt.replace("[IA_NO_CONTRADICTIONS]", "[IA_CANDIDATES]"),
                    **kwargs,
                )
            return super().generate_json(model, prompt, **kwargs)

    build_config = QueryBankBuildConfig(
        source_run_id="run-1",
        attack_config_path=SimpleNamespace(),
        seed=17,
        member_count=1,
        nonmember_count=1,
        paraphrases_per_attack=4,
        ia_questions_per_document=30,
        ia_batch_size=6,
        ia_max_attempts=3,
        benign_categories=("topic", "entity", "event", "summary", "follow_up"),
    )
    attack_config = SimpleNamespace(
        generation_model="local-model",
        embedding_model="embedding-model",
        ia_generation_max_tokens=128,
    )
    client = _NoFactClient()

    _summary, candidates = _ia_candidates(
        "Alpha Corp acquired Beta Labs.",
        build_config,
        attack_config,
        client,
        target_count=4,
        required_answer="no",
    )

    assert len(candidates) == 4
    assert {item["ground_truth"] for item in candidates} == {"no"}
    assert all(
        item["question"].startswith(
            ("Is it false that", "Is it untrue that", "Does the claim that", "Is the claim that")
        )
        for item in candidates
    )
    verification_prompt = next(
        prompt for prompt in client.prompts if "[IA_VERIFY]" in prompt
    )
    assert len(re.findall(r"^\d+\. (.+)$", verification_prompt, flags=re.MULTILINE)) == 8
    assert any("[IA_NO_FACTS]" in prompt for prompt in client.prompts)
    assert not any("[IA_NO_CONTRADICTIONS]" in prompt for prompt in client.prompts)


def test_ia_generation_skips_exact_duplicates_and_shows_prior_questions() -> None:
    build_config = QueryBankBuildConfig(
        source_run_id="run-1",
        attack_config_path=SimpleNamespace(),
        seed=17,
        member_count=1,
        nonmember_count=1,
        paraphrases_per_attack=4,
        ia_questions_per_document=30,
        ia_batch_size=6,
        ia_max_attempts=6,
        benign_categories=("topic", "entity", "event", "summary", "follow_up"),
    )
    attack_config = SimpleNamespace(
        generation_model="local-model",
        embedding_model="embedding-model",
        ia_generation_max_tokens=512,
    )
    client = _DuplicateIaClient()

    summary, candidates = _ia_candidates(
        "Alpha Corp acquired Beta Labs.",
        build_config,
        attack_config,
        client,
    )

    assert summary == "Alpha acquisition"
    assert len(candidates) == 30
    assert len(
        {
            re.sub(r"[^\w\s]", " ", item["question"].casefold()).strip()
            for item in candidates
        }
    ) == 30
    assert any(
        "Previously accepted questions:" in prompt
        for prompt in client.prompts
        if "IA_CANDIDATES" in prompt
    )


def test_benign_generation_retries_valid_json_with_wrong_shape() -> None:
    attack_config = SimpleNamespace(
        generation_model="local-model",
        ia_generation_max_tokens=128,
    )
    client = _NonMappingBenignClient()

    result = _benign_queries(
        "Alpha Corp acquired Beta Labs.",
        attack_config,
        client,
    )

    assert set(result) == {
        "topic",
        "entity",
        "event",
        "summary",
        "follow_up",
    }
    assert client.benign_calls == 2


def test_ia_generation_continues_after_one_failed_verification_batch() -> None:
    build_config = QueryBankBuildConfig(
        source_run_id="run-1",
        attack_config_path=SimpleNamespace(),
        seed=17,
        member_count=1,
        nonmember_count=1,
        paraphrases_per_attack=4,
        ia_questions_per_document=30,
        ia_batch_size=6,
        ia_max_attempts=6,
        benign_categories=("topic", "entity", "event", "summary", "follow_up"),
    )
    attack_config = SimpleNamespace(
        generation_model="local-model",
        embedding_model="embedding-model",
        ia_generation_max_tokens=128,
    )

    summary, candidates = _ia_candidates(
        "Alpha Corp acquired Beta Labs.",
        build_config,
        attack_config,
        _FailingVerificationIaClient(),
    )

    assert summary == "Alpha acquisition"
    assert len(candidates) == 30


def test_ia_generation_caps_model_overproduction_at_target_count() -> None:
    build_config = QueryBankBuildConfig(
        source_run_id="run-1",
        attack_config_path=SimpleNamespace(),
        seed=17,
        member_count=1,
        nonmember_count=1,
        paraphrases_per_attack=4,
        ia_questions_per_document=30,
        ia_batch_size=6,
        ia_max_attempts=6,
        benign_categories=("topic", "entity", "event", "summary", "follow_up"),
    )
    attack_config = SimpleNamespace(
        generation_model="local-model",
        embedding_model="embedding-model",
        ia_generation_max_tokens=128,
    )
    client = _OverproducingIaClient()

    _summary, candidates = _ia_candidates(
        "Alpha Corp acquired Beta Labs.",
        build_config,
        attack_config,
        client,
    )

    assert len(candidates) == 30
    assert client.requested_counts == [6, 6, 6, 6, 6]
    assert all(count > 0 for count in client.requested_counts)


def test_ia_verification_falls_back_to_plain_labels_without_regenerating() -> None:
    build_config = QueryBankBuildConfig(
        source_run_id="run-1",
        attack_config_path=SimpleNamespace(),
        seed=17,
        member_count=1,
        nonmember_count=1,
        paraphrases_per_attack=4,
        ia_questions_per_document=30,
        ia_batch_size=6,
        ia_max_attempts=5,
        benign_categories=("topic", "entity", "event", "summary", "follow_up"),
    )
    attack_config = SimpleNamespace(
        generation_model="local-model",
        embedding_model="embedding-model",
        ia_generation_max_tokens=128,
    )
    client = _PlainTextVerificationFallbackClient()

    _summary, candidates = _ia_candidates(
        "Alpha Corp acquired Beta Labs.",
        build_config,
        attack_config,
        client,
    )

    assert len(candidates) == 30
    assert client.ia_candidate_calls == 5
    assert any("IA_VERIFY_PLAIN" in prompt for prompt in client.prompts)


def test_benign_generation_repairs_each_field_after_incomplete_json() -> None:
    attack_config = SimpleNamespace(
        generation_model="local-model",
        ia_generation_max_tokens=128,
    )
    client = _IncompleteBenignClient()

    result = _benign_queries(
        "Alpha Corp acquired Beta Labs.",
        attack_config,
        client,
    )

    assert set(result) == {
        "topic",
        "entity",
        "event",
        "summary",
        "follow_up",
    }
    assert client.repaired_categories == [
        "topic",
        "entity",
        "event",
        "summary",
        "follow_up",
    ]


def test_benign_generation_unwraps_single_object_array() -> None:
    attack_config = SimpleNamespace(
        generation_model="local-model",
        ia_generation_max_tokens=128,
    )
    client = _SingletonListBenignClient()

    result = _benign_queries(
        "Alpha Corp acquired Beta Labs.",
        attack_config,
        client,
    )

    assert set(result) == {
        "topic",
        "entity",
        "event",
        "summary",
        "follow_up",
    }
    assert client.benign_calls == 1


def test_ia_generation_uses_plain_fallback_after_candidate_json_failure(
    capsys,
) -> None:
    build_config = QueryBankBuildConfig(
        source_run_id="run-1",
        attack_config_path=SimpleNamespace(),
        seed=17,
        member_count=1,
        nonmember_count=1,
        paraphrases_per_attack=4,
        ia_questions_per_document=30,
        ia_batch_size=6,
        ia_max_attempts=5,
        benign_categories=("topic", "entity", "event", "summary", "follow_up"),
    )
    attack_config = SimpleNamespace(
        generation_model="local-model",
        embedding_model="embedding-model",
        ia_generation_max_tokens=128,
    )
    client = _PlainCandidateFallbackClient()

    summary, candidates = _ia_candidates(
        "Alpha Corp acquired Beta Labs.",
        build_config,
        attack_config,
        client,
    )

    assert summary == "Alpha acquisition"
    assert len(candidates) == 30
    assert client.plain_candidate_calls == 5
    output = capsys.readouterr().out
    assert "generation_fallback=plain" in output
    assert "generation_error=RuntimeError" in output


def test_ia_verification_retries_only_missing_indexes() -> None:
    attack_config = SimpleNamespace(
        generation_model="local-model",
        ia_generation_max_tokens=128,
    )
    client = _PartialIndexedVerificationClient()
    questions = [
        f"Did documented fact {index} happen?"
        for index in range(1, 7)
    ]

    labels = _verify_ia_answers(
        text="Alpha Corp acquired Beta Labs.",
        questions=questions,
        attack_config=attack_config,
        client=client,
    )

    assert labels == ["yes", "no", "unknown", "yes", "unknown", "no"]
    assert len(client.indexed_prompts) == 1
    assert "1. Did documented fact 1 happen?" not in client.indexed_prompts[0]
    assert "2. Did documented fact 2 happen?" in client.indexed_prompts[0]
    assert "3. Did documented fact 3 happen?" not in client.indexed_prompts[0]
    assert client.single_indexes == [5, 6]


def test_ia_tail_always_requests_full_batch_and_caps_at_target() -> None:
    build_config = QueryBankBuildConfig(
        source_run_id="run-1",
        attack_config_path=SimpleNamespace(),
        seed=17,
        member_count=1,
        nonmember_count=1,
        paraphrases_per_attack=4,
        ia_questions_per_document=30,
        ia_batch_size=6,
        ia_max_attempts=6,
        benign_categories=("topic", "entity", "event", "summary", "follow_up"),
    )
    attack_config = SimpleNamespace(
        generation_model="local-model",
        embedding_model="embedding-model",
        ia_generation_max_tokens=128,
    )
    client = _TailOversamplingIaClient()

    _summary, candidates = _ia_candidates(
        "Alpha Corp acquired Beta Labs.",
        build_config,
        attack_config,
        client,
    )

    assert len(candidates) == 30
    assert client.requested_counts == [6, 6, 6, 6, 6, 6]


def test_ia_duplicate_only_batch_triggers_novelty_repair() -> None:
    build_config = QueryBankBuildConfig(
        source_run_id="run-1",
        attack_config_path=SimpleNamespace(),
        seed=17,
        member_count=1,
        nonmember_count=1,
        paraphrases_per_attack=4,
        ia_questions_per_document=30,
        ia_batch_size=6,
        ia_max_attempts=5,
        benign_categories=("topic", "entity", "event", "summary", "follow_up"),
    )
    attack_config = SimpleNamespace(
        generation_model="local-model",
        embedding_model="embedding-model",
        ia_generation_max_tokens=128,
    )
    client = _NoveltyRepairIaClient()

    _summary, candidates = _ia_candidates(
        "Alpha Corp acquired Beta Labs.",
        build_config,
        attack_config,
        client,
    )

    assert len(candidates) == 30
    assert client.repair_calls == 4
    candidate_prompts = [
        prompt for prompt in client.prompts if "[IA_CANDIDATES]" in prompt
    ]
    assert len(
        {
            re.search(r"Novelty strategy: (.+)", prompt).group(1)
            for prompt in candidate_prompts
        }
    ) > 1
