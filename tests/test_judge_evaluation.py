import pytest

from miaguard.judge_evaluation import (
    compare_judge_heads,
    evaluate_judge_records,
    fixed_fpr_operating_point,
)


def _trace(stage: str, rubric: float, logprob: float, attack_type: str):
    if attack_type == "benign":
        screening = {
            "routing_decision": "SKIP_EXPLICIT_BENIGN",
            "candidate_attack_types": [],
            "observed_feature_codes": [
                "EXPLICIT_BENIGN_PURPOSE",
                "NO_CONTRADICTORY_SUSPICIOUS_MECHANISM",
            ],
            "candidate_ambiguity": False,
        }
    else:
        candidates = (
            ["direct_rag_mia", attack_type]
            if attack_type == "masked_mia"
            else [attack_type]
        )
        screening = {
            "routing_decision": "REVIEW",
            "candidate_attack_types": candidates,
            "observed_feature_codes": ["SOURCE_LIKE_PREFIX"],
            "candidate_ambiguity": len(candidates) == 2,
        }
    return {
        "stage": stage,
        "screening": screening,
        "rubric": {"score": rubric},
        "logprob": {"score": logprob, "probabilities": {"A": 0.2, "B": 0.3, "C": 0.5}},
        "statuses": {"overall": "ok"},
        "latencies_ms": {"total": 2.0},
    }


def _records():
    rows = []
    scores = {
        "benign": (0.05, 0.10),
        "direct_rag_mia": (0.90, 0.85),
        "masked_mia": (0.80, 0.75),
        "s2_mia": (0.70, 0.65),
        "ia": (0.45, 0.80),
    }
    for attack_type, pair in scores.items():
        for index in range(2):
            query_score = pair[0] - index * 0.01
            session_score = pair[1] - index * 0.01
            rows.append(
                {
                    "query_id": f"{attack_type}-{index}",
                    "doc_id": f"doc-{attack_type}-{index}",
                    "session_key": f"session-{attack_type}-{index}",
                    "turn_index": 3,
                    "session_length": 3,
                    "traffic_type": "benign" if attack_type == "benign" else "attack",
                    "attack_type": attack_type,
                    "query_trace": _trace(
                        "query", query_score, query_score, attack_type
                    ),
                    "session_trace": _trace(
                        "session", session_score, session_score, attack_type
                    ),
                }
            )
    return rows


def test_evaluation_treats_ia_query_metrics_as_diagnostic() -> None:
    report = evaluate_judge_records(_records(), bootstrap_replicates=0)

    assert report["metric_roles"]["ia_query"] == "diagnostic"
    assert report["metric_roles"]["ia_session"] == "primary"


def test_fixed_fpr_operating_point_maximizes_recall_under_cap() -> None:
    labels = [0, 0, 0, 1, 1, 1]
    scores = [0.05, 0.10, 0.20, 0.21, 0.70, 0.90]

    point = fixed_fpr_operating_point(labels, scores, max_fpr=0.05)

    assert point["fpr"] <= 0.05
    assert point["recall"] == pytest.approx(1.0)
    assert point["threshold_kind"] == "diagnostic_only"
    assert point["deployable"] is False


def test_fixed_fpr_point_uses_null_when_only_reject_all_is_feasible() -> None:
    point = fixed_fpr_operating_point(
        [0, 0, 1], [0.9, 0.8, 0.1], max_fpr=0.0
    )

    assert point["threshold"] is None
    assert point["recall"] == 0.0


def test_both_heads_are_evaluated_on_identical_rows() -> None:
    report = evaluate_judge_records(_records(), bootstrap_replicates=0)

    assert set(report["heads"]) == {"rubric", "logprob"}
    assert report["heads"]["rubric"]["query_count"] == report["heads"]["logprob"]["query_count"]


def test_selection_uses_predeclared_lexicographic_objective() -> None:
    report = evaluate_judge_records(_records(), bootstrap_replicates=0)

    selection = compare_judge_heads(report)

    assert selection["selection_objective"][0] == "maximize_minimum_primary_recall_at_5pct_fpr"
    assert selection["recommended_head"] in {"rubric", "logprob"}
    assert selection["does_not_select_access_threshold"] is True


def test_evaluation_reports_router_candidate_coverage_and_skip_errors() -> None:
    report = evaluate_judge_records(_records(), bootstrap_replicates=0)

    query = report["routing"]["query"]
    session = report["routing"]["session"]
    assert query["per_attack"]["s2_mia"]["top2_candidate_coverage"] == 1.0
    assert query["per_attack"]["masked_mia"]["top1_candidate_accuracy"] == 0.0
    assert query["per_attack"]["masked_mia"]["top2_candidate_coverage"] == 1.0
    assert query["attack_erroneous_skip_rate"] == 0.0
    assert query["benign_review_rate"] == 0.0
    assert session["per_attack"]["ia"]["top2_candidate_coverage"] == 1.0
