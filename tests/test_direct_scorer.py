import inspect
from pathlib import Path

import pytest

from miaguard.attack_pattern_library import AttackPatternLibrary
from miaguard.direct_scorer import (
    DirectQueryRiskDetector,
    DirectSessionRiskDetector,
    load_direct_scorer_config,
)
from miaguard.risk_types import SessionTurn


class _Client:
    def __init__(self, responses):
        self.responses = list(responses)
        self.prompts = []

    def generate_json(self, model, prompt, **kwargs):
        self.prompts.append(prompt)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def _config():
    root = Path(__file__).resolve().parents[1]
    return load_direct_scorer_config(
        root / "configs/defense/two_stage_direct_observe.yaml",
        root,
    )


def _turn(turn_id: int, query: str, doc_id: str = "doc-1") -> SessionTurn:
    return SessionTurn(
        turn_id=turn_id,
        timestamp=float(turn_id),
        query=query,
        query_risk_score=0.2,
        query_risk_class="NONE",
        retrieved_doc_ids=(doc_id,),
        retrieval_scores=(0.9,),
        recommended_level="L1",
        applied_level="L0",
    )


def test_query_direct_scorer_uses_patterns_and_parses_score() -> None:
    config = _config()
    client = _Client(
        [
            {
                "risk_score": 0.91,
                "suspected_attack_types": ["masked_mia"],
                "evidence_codes": ["omitted_source_content"],
            }
        ]
    )
    detector = DirectQueryRiskDetector(config, client, "model")

    result = detector.evaluate(query="Recover <omitted-1>", session_id="s1")

    assert result.score == 0.91
    assert result.risk_class == "STRONG"
    assert result.suspected_attack_types == ("masked_mia",)
    assert result.evidence_codes == ("OMITTED_SOURCE_CONTENT",)
    assert "# Security objective" in client.prompts[0]
    assert "Recover <omitted-1>" in client.prompts[0]
    assert "0.80-0.95" in client.prompts[0]
    assert 'Complete this sentence "<source prefix>......"' in client.prompts[0]


def test_query_direct_scorer_retries_invalid_output() -> None:
    config = _config()
    client = _Client(
        [
            {"risk_score": 82, "suspected_attack_types": [], "evidence_codes": []},
            {"risk_score": 0.2, "suspected_attack_types": [], "evidence_codes": []},
        ]
    )
    detector = DirectQueryRiskDetector(config, client, "model")

    result = detector.evaluate(query="ordinary question", session_id="s1")

    assert result.score == 0.2
    assert result.risk_class == "NONE"
    assert len(client.prompts) == 2
    assert "FORMAT REPAIR" not in client.prompts[0]
    assert "FORMAT REPAIR" in client.prompts[1]


def test_query_direct_scorer_records_explicit_fallback() -> None:
    config = _config()
    client = _Client([RuntimeError("bad"), {"not_a_score": 1}])
    detector = DirectQueryRiskDetector(config, client, "model")

    result = detector.evaluate(query="ambiguous", session_id="s1")

    assert result.score == 0.5
    assert result.risk_class == "WEAK"
    assert result.status == "fallback_invalid_output"
    assert result.evidence_codes == ("DIRECT_SCORER_INVALID_OUTPUT",)


def test_session_scorer_waits_for_minimum_history_without_model_call() -> None:
    config = _config()
    client = _Client([])
    detector = DirectSessionRiskDetector(config, client, "model")

    result = detector.evaluate(
        query="second query",
        session_id="s1",
        recent_turns=(_turn(1, "first query"),),
        retrieved_doc_ids=("doc-1",),
        retrieval_scores=(0.9,),
        min_session_queries=3,
    )

    assert result.score == 0.0
    assert result.status == "insufficient_history"
    assert client.prompts == []


def test_session_scorer_supplies_only_online_window_and_retrieval_statistics() -> None:
    config = _config()
    client = _Client(
        [
            {
                "risk_score": 0.88,
                "suspected_attack_types": ["ia"],
                "evidence_codes": ["REPEATED_FACT_PROBES"],
            }
        ]
    )
    detector = DirectSessionRiskDetector(config, client, "model")

    result = detector.evaluate(
        query="third narrow question",
        session_id="s1",
        recent_turns=(
            _turn(1, "first narrow question"),
            _turn(2, "second narrow question"),
        ),
        retrieved_doc_ids=("doc-1",),
        retrieval_scores=(0.9,),
        min_session_queries=3,
    )

    assert result.score == 0.88
    assert result.suspected_attack_types == ("ia",)
    assert '"repeated_top1_count": 3' in client.prompts[0]
    assert '"top1_concentration": 1.0' in client.prompts[0]
    assert "systematic probes plus repeated or concentrated target retrieval" in client.prompts[0]
    assert "membership_label" not in client.prompts[0]
    assert "intent_label" not in client.prompts[0]
    assert "attack_type\"" not in client.prompts[0]


def test_direct_detector_signatures_do_not_accept_offline_truth() -> None:
    forbidden = {"membership_label", "intent_label", "attack_type", "target_doc_id"}
    assert set(inspect.signature(DirectQueryRiskDetector.evaluate).parameters).isdisjoint(
        forbidden
    )
    assert set(inspect.signature(DirectSessionRiskDetector.evaluate).parameters).isdisjoint(
        forbidden
    )


def test_direct_config_rejects_unknown_pattern_at_detector_construction() -> None:
    config = _config()
    root = Path(__file__).resolve().parents[1]
    library = AttackPatternLibrary.load(config.manifest_path)
    invalid = config.__class__(
        **{**config.__dict__, "query_pattern_ids": ("missing_pattern",)}
    )

    with pytest.raises(ValueError, match="Unknown"):
        DirectQueryRiskDetector(invalid, _Client([]), "model", library)
