from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from miaguard.query_bank.formal_threshold_comparison import (
    adapt_planned_session,
    build_condition_configs,
    document_average_scores,
)
from miaguard.query_bank.sessions import PlannedSession
from miaguard.two_stage_gateway import load_two_stage_config


def _session(attack_type: str, queries: tuple[dict, ...]) -> PlannedSession:
    return PlannedSession(
        session_key=f"split:test:attack:{attack_type}:doc-1:001",
        partition="test",
        doc_id="doc-1",
        membership_label=1,
        traffic_type="benign" if attack_type == "benign" else "attack",
        attack_type=attack_type,
        session_index=1,
        queries=queries,
    )


def test_adapter_preserves_full_non_ia_and_ia_session_order() -> None:
    direct = _session(
        "direct_rag_mia",
        tuple(
            {"query_id": f"d-{index}", "query_text": f"direct {index}", "payload": {}}
            for index in range(5)
        ),
    )
    ia = _session(
        "ia",
        tuple(
            {
                "query_id": f"ia-{index}",
                "query_text": f"ia {index}",
                "payload": {"ground_truth": "yes", "question": f"q {index}"},
            }
            for index in range(4)
        ),
    )

    direct_rows = adapt_planned_session(direct)
    ia_rows = adapt_planned_session(ia)

    assert [row["query_id"] for row in direct_rows] == [f"d-{index}" for index in range(5)]
    assert [row["attack_query"] for row in direct_rows] == [
        f"direct {index}" for index in range(5)
    ]
    assert len(ia_rows) == 1
    assert [row["query_id"] for row in ia_rows[0]["queries"]] == [
        f"ia-{index}" for index in range(4)
    ]


def test_condition_configs_are_disabled_fixed_and_learned() -> None:
    root = Path(__file__).resolve().parents[1]
    base = load_two_stage_config(
        root / "configs/defense/two_stage_direct_observe_threshold.yaml"
    )

    configs = build_condition_configs(base, learned_threshold=0.73)

    assert list(configs) == ["disabled", "fixed_0_10", "learned"]
    assert configs["disabled"].mode == "disabled"
    assert configs["fixed_0_10"].attack_detection_threshold == 0.10
    assert configs["learned"].attack_detection_threshold == 0.73
    assert configs["learned"].level_thresholds == base.level_thresholds


def test_masked_adapter_preserves_scoring_query_and_recovery_payload() -> None:
    session = _session(
        "masked_mia",
        (
            {
                "query_id": "masked-1",
                "query_text": "Recover every mask: source [Mask_1]",
                "payload": {
                    "masked_text": "source [Mask_1]",
                    "answers": ["word"],
                },
            },
        ) * 4,
    )

    row = adapt_planned_session(session)[0]

    assert row["attack_query"] == "Recover every mask: source [Mask_1]"
    assert row["masked_text"] == "source [Mask_1]"


def test_ia_document_average_weights_sessions_by_query_count() -> None:
    averaged = document_average_scores(
        [
            {
                "doc_id": "doc-1",
                "membership_label": 1,
                "membership_score": 0.5,
                "query_count": 4,
            },
            {
                "doc_id": "doc-1",
                "membership_label": 1,
                "membership_score": 1.0,
                "query_count": 5,
            },
        ]
    )

    assert averaged[0]["membership_score"] == (0.5 * 4 + 1.0 * 5) / 9
