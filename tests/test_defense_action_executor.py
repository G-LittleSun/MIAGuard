from __future__ import annotations

import pytest

from miaguard.defense import DefenseDecision, GuardedRAG
from miaguard.defense_contracts import Evidence
from miaguard.defense_experiment import _text_response, summarize_for_defense_v1
from miaguard.evidence_access import execute_action


def evidence(doc: str, text: str, parent: str | None = None) -> Evidence:
    return Evidence(doc, parent or doc, text, .9)


def test_allow_and_hide_refill_deliver_only_allowed_evidence() -> None:
    candidates = (evidence("target", "secret"), evidence("b", "safe"))
    calls = []

    def retrieve(excluded):
        calls.append(excluded)
        return (evidence("b", "safe"), evidence("c", "replacement"))

    allow = execute_action("allow", candidates, frozenset(), retrieve, None)
    assert [item.doc_id for item in allow.evidence] == ["target", "b"]
    hidden = execute_action("hide_target_refill", candidates, frozenset({"target"}), retrieve, None)
    assert [item.doc_id for item in hidden.evidence] == ["b", "c"]
    assert calls == [frozenset({"target"})]
    assert hidden.applied_action == "hide_target_refill"


def test_no_context_and_deny_never_call_retrieval_or_summary() -> None:
    def forbidden(*args):
        raise AssertionError("must not be called")

    for action in ("no_context_answer", "deny"):
        result = execute_action(action, (evidence("a", "secret"),), frozenset(), forbidden, forbidden)
        assert result.evidence == ()
        assert result.applied_action == action


def test_summary_delivers_only_transformed_text_and_no_second_summary() -> None:
    summary_calls = []

    def summarize(items):
        summary_calls.append(items)
        return "General topic overview."

    execution = execute_action("summarize_context", (evidence("a", "raw sensitive excerpt"),), frozenset(), None, summarize)
    assert execution.recommended_action == "sanitized_context"
    assert execution.applied_action == "sanitized_context"
    assert [item.kind for item in execution.evidence] == ["summary"]
    assert [item.text for item in execution.evidence] == ["General topic overview."]
    assert len(summary_calls) == 1


def test_summary_failure_and_empty_candidates_fall_back_safely() -> None:
    def timeout(items):
        raise TimeoutError("slow")

    result = execute_action("sanitized_context", (evidence("a", "raw"),), frozenset(), None, timeout)
    assert (result.applied_action, result.status) == ("no_context_answer", "summary_failed")
    assert result.evidence == ()
    empty = execute_action("hide_target_refill", (), frozenset({"a"}), lambda _: (), None)
    assert empty.applied_action == "no_context_answer"
    with pytest.raises(ValueError, match="Unsupported"):
        execute_action("delete_index", (), frozenset(), None, None)


class Store:
    def search(self, query, top_k, *, allowed_doc_ids=None, excluded_parent_ids=frozenset()):
        docs = [{"doc_id": "target", "parent_doc_id": "target", "text": "raw sensitive excerpt"},
                {"doc_id": "safe", "parent_doc_id": "safe", "text": "safe context"}]
        return [{"document": d, "score": 1.0 - i / 10} for i, d in enumerate(docs)
                if d["parent_doc_id"] not in excluded_parent_ids][:top_k]


class Detector:
    def decide(self, *args):
        return DefenseDecision(.9, .0, .9, "high", (), "allow")


class Generator:
    def __init__(self):
        self.prompts = []

    def generate(self, model, prompt, **kwargs):
        self.prompts.append(prompt)
        return "response"


def test_guarded_rag_sends_summary_not_raw_excerpt_to_generator() -> None:
    selector = lambda decision, candidates: ("sanitized_context", frozenset())
    guard = GuardedRAG(Store(), Detector(), 2, action_selector=selector,
                       summarizer=lambda items: "General topic overview.")
    prepared = guard.prepare("What is this about?", "session")
    assert prepared.contexts == ["General topic overview."]
    assert prepared.action_execution.applied_action == "sanitized_context"
    assert prepared.decision.access_action == "sanitized_context"
    generator = Generator()
    attack_config = type("Config", (), {"generation_model": "fake"})()
    _text_response(prepared, generator, attack_config, "What is this about?", instruction="Answer", max_tokens=12)
    assert len(generator.prompts) == 1
    assert "raw sensitive excerpt" not in generator.prompts[0]
    assert "General topic overview." in generator.prompts[0]


def test_deny_skips_generation_and_no_context_keeps_question() -> None:
    generator = Generator()
    attack_config = type("Config", (), {"generation_model": "fake"})()
    deny = GuardedRAG(Store(), Detector(), 2,
                      action_selector=lambda decision, candidates: ("deny", frozenset())).prepare("private?", "s")
    response = _text_response(deny, generator, attack_config, "private?", instruction="Answer", max_tokens=12)
    assert response and generator.prompts == []
    no_context = GuardedRAG(Store(), Detector(), 2,
                            action_selector=lambda decision, candidates: ("no_context_answer", frozenset())).prepare("normal?", "s")
    _text_response(no_context, generator, attack_config, "normal?", instruction="Answer", max_tokens=12)
    assert "normal?" in generator.prompts[0]
    assert "raw sensitive excerpt" not in generator.prompts[0]


def test_allow_and_hide_change_the_actual_answer_prompt() -> None:
    generator = Generator()
    attack_config = type("Config", (), {"generation_model": "fake"})()
    allow = GuardedRAG(Store(), Detector(), 2,
                       action_selector=lambda decision, candidates: ("allow", frozenset())).prepare("question", "s")
    _text_response(allow, generator, attack_config, "question", instruction="Answer", max_tokens=12)
    assert "raw sensitive excerpt" in generator.prompts[-1]
    hidden = GuardedRAG(Store(), Detector(), 2,
                        action_selector=lambda decision, candidates: ("hide_target_refill", frozenset({"target"}))).prepare("question", "s")
    _text_response(hidden, generator, attack_config, "question", instruction="Answer", max_tokens=12)
    assert "raw sensitive excerpt" not in generator.prompts[-1]
    assert "safe context" in generator.prompts[-1]
    assert hidden.decision.two_stage_assessment["execution"]["candidate_doc_ids"] == ["target", "safe"]
    assert hidden.decision.two_stage_assessment["execution"]["delivered_doc_ids"] == ["safe"]


def test_summary_prompt_is_versioned_and_downstream_uses_only_summary() -> None:
    from miaguard.evidence_access import SUMMARY_TEMPLATE_VERSION

    generator = Generator()
    attack_config = type("Config", (), {"generation_model": "fake"})()
    text = summarize_for_defense_v1((evidence("a", "raw sensitive excerpt"),), generator, attack_config)
    assert text == "response"
    assert SUMMARY_TEMPLATE_VERSION in generator.prompts[0]
    assert generator.prompts[0].count("raw sensitive excerpt") == 1
