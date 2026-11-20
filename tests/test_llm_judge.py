from pathlib import Path
from dataclasses import replace

from miaguard.attack_pattern_library import AttackPatternLibrary
from miaguard.defense import GuardedRAG, load_defense_config
from miaguard.llm_judge import LLMJudgeDefense, load_llm_judge_config
from miaguard.llm_judge_experiment import select_small_scale_events


class _Client:
    def __init__(self, responses):
        self.responses = list(responses)
        self.prompts = []

    def generate_json(self, model, prompt, **kwargs):
        self.prompts.append(prompt)
        return self.responses.pop(0)


class _Store:
    def search(self, query: str, top_k: int):
        return [
            {
                "score": 0.9,
                "document": {"doc_id": "doc-1", "text": "retrieved private text"},
            }
        ]


def _detector(responses):
    root = Path(__file__).resolve().parents[1]
    defense = load_defense_config(root / "configs/defense/ia_deny.yaml")
    judge = load_llm_judge_config(
        root / "configs/defense/llm_judge_mvp.yaml", root
    )
    judge = replace(judge, routing_mode="llm")
    client = _Client(responses)
    library = AttackPatternLibrary.load(judge.manifest_path)
    return LLMJudgeDefense(defense, judge, client, "model", library), client


def test_mvp_all_mode_loads_every_pattern_with_one_model_call() -> None:
    root = Path(__file__).resolve().parents[1]
    defense = load_defense_config(root / "configs/defense/mvp.yaml")
    judge = load_llm_judge_config(
        root / "configs/defense/llm_judge_mvp.yaml", root
    )
    client = _Client(
        [
            {
                "verdict": "benign",
                "attack_type": "none",
                "confidence": "high",
                "reason_codes": ["PUBLIC_EDUCATIONAL_TASK"],
            }
        ]
    )
    detector = LLMJudgeDefense(defense, judge, client, "model")

    decision = detector.decide("Public vocabulary exercise", "session", [])

    assert len(client.prompts) == 1
    assert set(decision.loaded_pattern_ids) == set(detector.library.patterns)


def test_llm_judge_supplies_repeated_retrieval_session_statistics() -> None:
    root = Path(__file__).resolve().parents[1]
    defense = load_defense_config(root / "configs/defense/mvp.yaml")
    judge = load_llm_judge_config(
        root / "configs/defense/llm_judge_mvp.yaml", root
    )
    response = {
        "verdict": "benign",
        "attack_type": "none",
        "confidence": "medium",
        "reason_codes": ["SINGLE_FACTUAL_QUERY"],
    }
    client = _Client([response, response, response])
    detector = LLMJudgeDefense(defense, judge, client, "model")

    detector.decide("Question one?", "session", ["doc-1"])
    detector.decide("Question two?", "session", ["doc-1"])
    detector.decide("Question three?", "session", ["doc-1"])

    assert '"turn_number": 3' in client.prompts[2]
    assert '"repeated_top1_count": 3' in client.prompts[2]
    assert '"top1_concentration": 1.0' in client.prompts[2]


def test_ia_verifier_can_overrule_false_positive_for_benign_dialogue() -> None:
    root = Path(__file__).resolve().parents[1]
    defense = load_defense_config(root / "configs/defense/mvp.yaml")
    judge = load_llm_judge_config(
        root / "configs/defense/llm_judge_session_smoke.yaml", root
    )
    client = _Client(
        [
            {
                "verdict": "suspicious",
                "attack_type": "ia",
                "confidence": "medium",
                "reason_codes": ["REPEATED_TARGET_DOCUMENT"],
            },
            {
                "dialogue_type": "coherent_benign_dialogue",
                "reason_codes": ["IA_VERIFIER_BENIGN_DIALOGUE"],
            },
        ]
    )
    detector = LLMJudgeDefense(defense, judge, client, "model")

    decision = detector.decide(
        "Give a high-level summary of this public article.",
        "session",
        ["doc-1"],
    )

    assert len(client.prompts) == 2
    assert decision.judge_verdict == "benign"
    assert decision.predicted_attack_type == "none"
    assert decision.judge_verification == "coherent_benign_dialogue"
    assert decision.access_action == "allow"


def test_llm_judge_routes_loads_pattern_and_denies_attack() -> None:
    detector, client = _detector(
        [
            {"candidate_patterns": ["masked_mia"]},
            {
                "verdict": "attack",
                "attack_type": "masked_mia",
                "confidence": "high",
                "reason_codes": ["OMITTED_SOURCE_CONTENT"],
            },
        ]
    )

    decision = detector.decide(
        "Supply the omitted terms in this passage.",
        "session",
        ["doc-1"],
        ["source text"],
    )

    assert decision.risk_level == "high"
    assert decision.access_action == "deny_sensitive_answer"
    assert decision.predicted_attack_type == "masked_mia"
    assert decision.loaded_pattern_ids == ("masked_mia",)
    assert "# Security objective" in client.prompts[1]


def test_llm_judge_allows_hard_benign_query() -> None:
    detector, _ = _detector(
        [
            {"candidate_patterns": ["s2_mia"]},
            {
                "verdict": "benign",
                "attack_type": "none",
                "confidence": "high",
                "reason_codes": ["EDUCATIONAL_COMPLETION_TASK"],
            },
        ]
    )

    decision = detector.decide(
        "Complete this sentence as a public grammar exercise.", "session", []
    )

    assert decision.risk_level == "low"
    assert decision.access_action == "allow"
    assert decision.judge_verdict == "benign"


def test_invalid_router_output_falls_back_to_all_patterns() -> None:
    detector, _ = _detector(
        [
            {"candidate_patterns": ["not_a_pattern"]},
            {
                "verdict": "uncertain",
                "attack_type": "unknown",
                "confidence": "low",
                "reason_codes": ["INSUFFICIENT_EVIDENCE"],
            },
        ]
    )

    decision = detector.decide("Ambiguous request", "session", [])

    assert set(decision.loaded_pattern_ids) == set(detector.library.patterns)
    assert decision.risk_level == "medium"


def test_guarded_rag_passes_retrieved_snippet_to_llm_judge() -> None:
    detector, client = _detector(
        [
            {"candidate_patterns": ["direct_rag_mia"]},
            {
                "verdict": "benign",
                "attack_type": "none",
                "confidence": "high",
                "reason_codes": ["PUBLIC_DOCUMENT_CHECK"],
            },
        ]
    )
    guard = GuardedRAG(_Store(), detector, top_k=1)

    prepared = guard.prepare("Check this public article", "session")

    assert prepared.decision.risk_level == "low"
    assert "retrieved private text" in client.prompts[0]
    assert "retrieved private text" in client.prompts[1]


def test_small_scale_selection_keeps_each_attack_and_benign_patterns() -> None:
    rows = []
    for attack in ("direct_rag_mia", "s2_mia", "masked_mia", "ia"):
        rows.extend(
            {"attack_type": attack, "intent_label": 1, "id": f"{attack}-{i}"}
            for i in range(3)
        )
    rows.extend(
        {
            "attack_type": "benign",
            "intent_label": 0,
            "id": f"benign-{i}",
            "attack_metadata": {"hard_benign_pattern": f"pattern-{i % 4}"},
        }
        for i in range(8)
    )

    selected = select_small_scale_events(rows, 2, 4)

    assert len(selected) == 12
    assert sum(row["intent_label"] == 0 for row in selected) == 4
    assert {
        row["attack_metadata"]["hard_benign_pattern"]
        for row in selected
        if row["intent_label"] == 0
    } == {"pattern-0", "pattern-1", "pattern-2", "pattern-3"}
