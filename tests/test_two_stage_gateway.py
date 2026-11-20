from dataclasses import replace
import inspect
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from miaguard.defense import DefenseDecision, GuardedRAG
from miaguard.risk_types import RiskResult
from jsonschema import Draft202012Validator

from miaguard.two_stage_gateway import (
    TwoStageGateway,
    build_two_stage_risk_event,
    load_two_stage_config,
)


class _Store:
    def __init__(self) -> None:
        self.queries = []

    def search(self, query: str, top_k: int):
        self.queries.append(query)
        return [
            {"score": 0.9, "document": {"doc_id": "doc-1", "text": "primary"}},
            {"score": 0.8, "document": {"doc_id": "doc-2", "text": "secondary"}},
        ][:top_k]


class _LegacyAllowDetector:
    config = SimpleNamespace(restrict_context_chars=240)

    def decide(self, query, session_id, retrieved_doc_ids, retrieved_snippets):
        return DefenseDecision(0.0, 0.0, 0.0, "low", (), "allow")


class _FixedDetector:
    def __init__(self, result: RiskResult) -> None:
        self.result = result
        self.calls = []

    def evaluate(self, **kwargs):
        self.calls.append(kwargs)
        return self.result


def _config():
    root = Path(__file__).resolve().parents[1]
    return load_two_stage_config(root / "configs/defense/two_stage_disabled.yaml")


def test_disabled_gateway_matches_legacy_allow_path() -> None:
    legacy = GuardedRAG(_Store(), _LegacyAllowDetector(), top_k=2)
    gateway = TwoStageGateway(_config())
    staged = GuardedRAG(_Store(), gateway, top_k=2)

    before = legacy.prepare("normal query", "session")
    after = staged.prepare("normal query", "session")

    assert after.contexts == before.contexts
    assert after.retrieved_doc_ids == before.retrieved_doc_ids
    assert after.retrieval_scores == before.retrieval_scores
    assert after.decision.access_action == "allow"
    assert after.decision.access_level == "L0"
    assert after.decision.applied_access_level == "L0"
    assert gateway.session_store.window("session") == ()


def test_observe_records_high_risk_but_keeps_full_context() -> None:
    config = replace(_config(), mode="observe")
    query_detector = _FixedDetector(
        RiskResult("query", 0.95, "STRONG", "test", evidence_codes=("QUERY",))
    )
    session_detector = _FixedDetector(RiskResult("session", 0.1, "NONE", "test"))
    gateway = TwoStageGateway(
        config,
        query_detector=query_detector,
        session_detector=session_detector,
    )
    guard = GuardedRAG(_Store(), gateway, top_k=2)

    prepared = guard.prepare("probe", "session")

    assert prepared.decision.access_level == "L4"
    assert prepared.decision.applied_access_level == "L0"
    assert prepared.decision.access_action == "allow"
    assert prepared.contexts == ["primary", "secondary"]
    assert prepared.decision.query_risk_class == "STRONG"
    assert "membership_label" not in session_detector.calls[0]
    assert "intent_label" not in session_detector.calls[0]
    assert set(TwoStageGateway.detector_input_fields()).isdisjoint(
        {"membership_label", "intent_label", "attack_type", "target_doc_id"}
    )


def test_insufficient_session_history_does_not_dilute_query_risk() -> None:
    config = replace(_config(), mode="observe")
    gateway = TwoStageGateway(
        config,
        query_detector=_FixedDetector(
            RiskResult("query", 0.45, "WEAK", "test")
        ),
        session_detector=_FixedDetector(
            RiskResult(
                "session",
                0.0,
                "NONE",
                "test",
                status="insufficient_history",
            )
        ),
    )

    prepared = GuardedRAG(_Store(), gateway, top_k=1).prepare("probe", "session")

    assert prepared.decision.total_risk == 0.45
    assert prepared.decision.access_level == "L2"
    assert prepared.decision.window_size_actual == 1
    assert prepared.decision.window_coverage == 0.0


def test_enforce_applies_l4_and_removes_context() -> None:
    config = replace(_config(), mode="enforce")
    gateway = TwoStageGateway(
        config,
        query_detector=_FixedDetector(RiskResult("query", 0.95, "STRONG", "test")),
        session_detector=_FixedDetector(RiskResult("session", 0.0, "NONE", "test")),
    )
    guard = GuardedRAG(_Store(), gateway, top_k=2)

    prepared = guard.prepare("probe", "session")

    assert prepared.decision.applied_access_level == "L4"
    assert prepared.decision.access_action == "deny_sensitive_answer"
    assert prepared.contexts == []


def test_enforce_uses_attack_aware_l2_action() -> None:
    config = replace(
        _config(),
        mode="enforce",
        level_thresholds=(0.05, 0.1, 0.65, 0.85),
        l2_attack_actions={"s2_mia": "summarize_context"},
    )
    gateway = TwoStageGateway(
        config,
        query_detector=_FixedDetector(
            RiskResult(
                "query",
                0.5,
                "WEAK",
                "test",
                suspected_attack_types=("s2_mia",),
            )
        ),
        session_detector=_FixedDetector(
            RiskResult("session", 0.0, "NONE", "test")
        ),
    )

    prepared = GuardedRAG(_Store(), gateway, top_k=2).prepare("probe", "session")

    assert prepared.decision.applied_access_level == "L2"
    assert prepared.decision.access_action == "summarize_context"
    assert "ATTACK_AWARE_SUMMARIZE_CONTEXT" in prepared.decision.applied_policy_action_codes


def test_observe_mode_updates_isolated_session_windows() -> None:
    config = replace(_config(), mode="observe")
    gateway = TwoStageGateway(config)
    guard = GuardedRAG(_Store(), gateway, top_k=1)

    guard.prepare("a1", "session-a")
    guard.prepare("b1", "session-b")
    guard.prepare("a2", "session-a")

    assert [turn.query for turn in gateway.session_store.window("session-a")] == ["a1", "a2"]
    assert [turn.query for turn in gateway.session_store.window("session-b")] == ["b1"]


def test_online_event_builder_matches_schema_and_cannot_accept_truth_labels() -> None:
    root = Path(__file__).resolve().parents[1]
    gateway = TwoStageGateway(_config())
    prepared = GuardedRAG(_Store(), gateway, top_k=1).prepare("query", "session")

    event = build_two_stage_risk_event(
        event_id="event-1",
        session_id="session",
        turn_id=1,
        query_text="query",
        retrieved_doc_ids=prepared.retrieved_doc_ids,
        retrieval_scores=prepared.retrieval_scores,
        decision=prepared.decision,
    )
    schema = json.loads(
        (root / "schemas/two_stage_risk_event.schema.json").read_text(
            encoding="utf-8"
        )
    )

    Draft202012Validator(schema).validate(event)
    assert set(inspect.signature(build_two_stage_risk_event).parameters).isdisjoint(
        {"intent_label", "membership_label", "attack_type", "target_doc_id"}
    )


def test_config_loads_optional_attack_detection_threshold(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    raw = yaml.safe_load(
        (root / "configs/defense/two_stage_disabled.yaml").read_text(
            encoding="utf-8"
        )
    )
    raw["policy"]["attack_detection_threshold"] = 0.37
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(raw), encoding="utf-8")

    config = load_two_stage_config(path)

    assert config.attack_detection_threshold == 0.37


def test_config_rejects_invalid_attack_detection_threshold(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    raw = yaml.safe_load(
        (root / "configs/defense/two_stage_disabled.yaml").read_text(
            encoding="utf-8"
        )
    )
    raw["policy"]["attack_detection_threshold"] = 1.1
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(raw), encoding="utf-8")

    with pytest.raises(ValueError, match="attack detection threshold"):
        load_two_stage_config(path)


def test_gateway_clear_session_removes_window_and_cached_risk() -> None:
    config = replace(_config(), mode="observe")
    gateway = TwoStageGateway(
        config,
        session_detector=_FixedDetector(RiskResult("session", 0.4, "WEAK", "test")),
    )
    GuardedRAG(_Store(), gateway, top_k=1).prepare("probe", "session")
    assert gateway.session_store.window("session")
    assert "session" in gateway._session_risk_cache

    gateway.clear_session("session")

    assert gateway.session_store.window("session") == ()
    assert "session" not in gateway._session_risk_cache
