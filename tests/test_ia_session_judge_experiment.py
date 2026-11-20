import pytest

from miaguard.ia_session_judge_experiment import (
    benign_session_queries,
    evaluate_session_detection,
)


def test_benign_session_queries_are_public_and_coherent() -> None:
    queries = benign_session_queries(
        "A company announced a product in a public news report.", 4
    )

    assert len(queries) == 4
    assert all("public" in query.casefold() or "reading" in query.casefold() for query in queries)
    assert len(set(queries)) == 4


@pytest.mark.parametrize("turn_count", [2, 6])
def test_benign_session_queries_reject_unsupported_turn_counts(turn_count: int) -> None:
    with pytest.raises(ValueError):
        benign_session_queries("document", turn_count)


def test_session_metrics_report_detection_turn_and_benign_false_positive() -> None:
    rows = []
    for turn, verdict in enumerate(("benign", "uncertain", "attack"), start=1):
        rows.append(
            {
                "session_id": "attack-1",
                "session_kind": "attack",
                "turn_id": turn,
                "judge_verdict": verdict,
                "risk_level": "high" if verdict == "attack" else "low",
            }
        )
    for turn in range(1, 4):
        rows.append(
            {
                "session_id": "benign-1",
                "session_kind": "benign",
                "turn_id": turn,
                "judge_verdict": "benign",
                "risk_level": "low",
            }
        )

    metrics = evaluate_session_detection(rows, 3)

    assert metrics["by_turn"]["1"]["attack_detection_rate"] == 0.0
    assert metrics["by_turn"]["3"]["attack_detection_rate"] == 1.0
    assert metrics["attack_session_detection_rate"] == 1.0
    assert metrics["benign_session_false_positive_rate"] == 0.0
    assert metrics["average_first_detection_turn"] == 3.0
