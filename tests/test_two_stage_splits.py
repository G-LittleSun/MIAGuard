import json
from pathlib import Path

from jsonschema import Draft202012Validator

from miaguard.two_stage_splits import build_split_manifest, load_split_spec


def test_frozen_split_is_grouped_disjoint_and_matches_schema() -> None:
    root = Path(__file__).resolve().parents[1]
    manifest = build_split_manifest(
        root,
        load_split_spec(root / "configs/data_splits/ag_news_two_stage_v1.yaml"),
    )
    schema = json.loads(
        (root / "schemas/two_stage_split.schema.json").read_text(encoding="utf-8")
    )

    Draft202012Validator(schema).validate(manifest)
    partitions = manifest["partitions"]
    assert partitions["development"]["member_count"] == 300
    assert partitions["validation"]["member_count"] == 100
    assert partitions["test"]["member_count"] == 100
    id_sets = [
        set(value["member_doc_ids"] + value["nonmember_doc_ids"])
        for value in partitions.values()
    ]
    assert id_sets[0].isdisjoint(id_sets[1])
    assert id_sets[0].isdisjoint(id_sets[2])
    assert id_sets[1].isdisjoint(id_sets[2])


def test_online_risk_schema_does_not_accept_ground_truth() -> None:
    root = Path(__file__).resolve().parents[1]
    schema = json.loads(
        (root / "schemas/two_stage_risk_event.schema.json").read_text(
            encoding="utf-8"
        )
    )
    validator = Draft202012Validator(schema)
    event = {
        "event_id": "event-1",
        "session_id": "session-1",
        "turn_id": 1,
        "timestamp": "2026-07-21T00:00:00+08:00",
        "query_text": "query",
        "retrieved_doc_ids": ["doc-1"],
        "retrieval_scores": [0.9],
        "query_detection": {
            "stage": "query",
            "risk_score": 0.0,
            "risk_class": "NONE",
            "scoring_method": "noop",
            "suspected_attack_types": [],
            "evidence_codes": [],
            "status": "ok",
        },
        "session_detection": {
            "stage": "session",
            "risk_score": 0.0,
            "risk_class": "NONE",
            "scoring_method": "noop",
            "suspected_attack_types": [],
            "evidence_codes": [],
            "status": "ok",
        },
        "aggregation": {
            "method": "dynamic_window_coverage",
            "query_weight": 0.4,
            "session_weight": 0.6,
            "window_coverage": 0.0,
            "total_risk_score": 0.0,
        },
        "access_control": {
            "mode": "disabled",
            "recommended_level": "L0",
            "applied_level": "L0",
            "recommended_actions": ["FULL_ACCESS"],
            "applied_actions": ["FULL_ACCESS"],
            "access_action": "allow",
        },
        "latency_ms": {
            "query_detector": 0.0,
            "session_detector": 0.0,
            "total_defense": 0.0,
        },
        "versions": {"policy": "two_stage_policy_v1"},
    }

    validator.validate(event)
    event["ground_truth"] = {"traffic_type": "attack"}
    assert list(validator.iter_errors(event))


def test_checked_in_frozen_split_matches_schema() -> None:
    root = Path(__file__).resolve().parents[1]
    frozen = json.loads(
        (root / "data/two_stage_splits/ag_news_two_stage_v1.json").read_text(
            encoding="utf-8"
        )
    )
    schema = json.loads(
        (root / "schemas/two_stage_split.schema.json").read_text(encoding="utf-8")
    )

    Draft202012Validator(schema).validate(frozen)
    assert frozen["partitions"]["validation"]["member_doc_ids"][0] == (
        "ag_news_teacher_00000300"
    )
    assert frozen["partitions"]["test"]["nonmember_doc_ids"][0] == (
        "ag_news_teacher_00008400"
    )
