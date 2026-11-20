import pytest

from miaguard.defense_metrics import (
    apply_frozen_attack_point,
    attack_auc,
    calibrate_attack_operating_points,
    evaluate_run,
    paired_cluster_bootstrap,
    score_normal_quality,
    score_retrieval_recall,
)


def test_auc_tie_reverse_and_missing_class():
    tied = attack_auc([{"doc_id": "a", "membership_label": 1, "score": .5},
                       {"doc_id": "b", "membership_label": 0, "score": .5}])
    assert tied["auc"] == .5 and tied["flipped_auc_diagnostic"] == .5
    reverse = attack_auc([{"doc_id": "a", "membership_label": 1, "score": 0},
                          {"doc_id": "b", "membership_label": 0, "score": 1}])
    assert reverse["auc"] == 0 and reverse["flipped_auc_diagnostic"] == 1
    missing = attack_auc([{"doc_id": "a", "membership_label": 1, "score": .5}])
    assert missing["auc"] is None and missing["reason"] == "single_class"
    with pytest.raises(ValueError, match="mixed budget"):
        attack_auc([{"doc_id": "a", "membership_label": 1, "score": .5, "budget": 1},
                    {"doc_id": "b", "membership_label": 0, "score": .5, "budget": 5}])


def test_normal_quality_keeps_denials_and_failures_in_denominator():
    rows = [
        {"request_id": "a", "answerable": True, "reference_answer": "Paris", "status": "complete", "response": "Paris", "action": "allow", "claims": ["Paris"], "supported_claims": ["Paris"]},
        {"request_id": "b", "answerable": True, "reference_answer": "Rome", "status": "complete", "response": "I cannot answer", "action": "deny", "claims": [], "supported_claims": []},
        {"request_id": "c", "answerable": True, "reference_answer": "London", "status": "failed", "response": None, "action": "unavailable", "claims": [], "supported_claims": []},
        {"request_id": "d", "answerable": False, "reference_answer": None, "status": "complete", "response": "Unknown", "action": "no_context_answer", "claims": [], "supported_claims": []},
    ]
    result = score_normal_quality(rows)
    assert result["answerable_correctness"] == {"numerator": 1, "denominator": 3, "rate": 1 / 3}
    assert result["unanswerable_appropriate_abstention"]["numerator"] == 1
    assert result["empty_answer_count"] == 3
    assert result["faithfulness"]["denominator"] == 1
    assert result["false_intervention"]["numerator"] == 2


def test_empty_fact_faithfulness_null_and_recall_requires_gold():
    result = score_normal_quality([{"request_id": "a", "answerable": True, "reference_answer": "X", "status": "complete",
                                    "response": "Unknown", "action": "allow", "claims": [], "supported_claims": []}])
    assert result["faithfulness"]["rate"] is None
    assert score_retrieval_recall(["x"], None)["reason"] == "gold_evidence_missing"
    assert score_retrieval_recall(["x"], ["x", "y"])["rate"] == .5


def test_paired_bootstrap_resamples_whole_document_clusters():
    rows = [{"doc_id": doc, "method": method, "turn": turn, "value": value}
            for doc, value in [("a", 0), ("b", 1), ("c", 0)]
            for method in ("B0", "B2") for turn in (1, 2)]
    draws = paired_cluster_bootstrap(rows, replicates=20, seed=17)
    assert len(draws) == 20
    for sample in draws:
        assert len(sample) == len(rows)
        by_method = {method: sorted((row["doc_id"], row["turn"]) for row in sample if row["method"] == method)
                     for method in ("B0", "B2")}
        assert by_method["B0"] == by_method["B2"]


def test_evaluate_fake_run_preserves_single_class_null_and_denominators():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    result = evaluate_run(root / "data/defense_v1_runs/t09-fake-20261022-05",
                          {"analysis_role": "engineering_only"})
    assert result["analysis_role"] == "engineering_only"
    assert result["methods"]["B0"]["normal_exact_match"]["denominator"] == 1
    assert result["methods"]["B0"]["attacks"]["direct_rag_mia"]["auc"] is None
    assert result["methods"]["B0"]["attacks"]["direct_rag_mia"]["reason"] == "single_class"
    assert result["methods"]["B2"]["cost"]["request_count"] == 5
    with pytest.raises(ValueError, match="Formal evaluation requires reviewed gold"):
        evaluate_run(root / "data/defense_v1_runs/t09-fake-20261022-05", {"analysis_role": "formal"})


def test_attack_threshold_direction_is_chosen_only_on_calibration():
    calibration = [{"doc_id": f"m{i}", "membership_label": 1, "score": score}
                   for i, score in enumerate((.9, .8))]
    calibration += [{"doc_id": f"n{i}", "membership_label": 0, "score": score}
                    for i, score in enumerate((.1, .2))]
    frozen = calibrate_attack_operating_points(calibration, fpr_caps=(0.0,))
    assert frozen["direction"] == 1
    assert frozen["points"]["0.0"]["threshold"] == .8
    test = [{"doc_id": "test-m", "membership_label": 1, "score": .5},
            {"doc_id": "test-n", "membership_label": 0, "score": .6}]
    actual = apply_frozen_attack_point(test, frozen["points"]["0.0"])
    assert actual["threshold"] == .8
    assert actual["tpr"] == 0 and actual["fpr"] == 0
    reverse = [{**row, "score": 1 - row["score"]} for row in calibration]
    reversed_frozen = calibrate_attack_operating_points(reverse, fpr_caps=(0.0,))
    assert reversed_frozen["direction"] == -1
