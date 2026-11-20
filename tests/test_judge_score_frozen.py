from pathlib import Path

import pandas as pd

from miaguard.judge_score_frozen import evaluate_frozen_fusion, freeze_logistic_l2


def _table(partition: str, *, head: str = "logprob") -> pd.DataFrame:
    rows = []
    for doc in range(4):
        for attack_type, label, x1, x2 in (
            ("benign", 0, 0.05, 0.05),
            ("direct_rag_mia", 1, 0.9, 0.9),
            ("s2_mia", 1, 0.8, 0.8),
            ("masked_mia", 1, 0.7, 0.8),
            ("ia", 1, 0.1, 0.8),
        ):
            rows.append({"query_id": f"{doc}-{attack_type}", "doc_id": f"d{doc}", "attack_type": attack_type, "label": label, "head": head, "x1": x1, "x2_observed": x2, "session_score_available": True, "partition": partition})
    return pd.DataFrame(rows)


def test_frozen_logistic_validation_uses_saved_thresholds(tmp_path: Path) -> None:
    frozen = freeze_logistic_l2(_table("train"), {"0.01": {"threshold": 0.5}, "0.05": {"threshold": 0.4}}, tmp_path / "frozen.json")
    result = evaluate_frozen_fusion(_table("validation"), frozen)

    assert frozen["model"] == "logistic_l2"
    assert set(result["operating_points"]) == {"0.01", "0.05"}
    assert result["operating_points"]["0.01"]["threshold"] == 0.5
    assert result["operating_points"]["0.01"]["benign_fpr"] == 0.0


def test_frozen_evaluation_can_only_switch_partition_explicitly(tmp_path: Path) -> None:
    frozen = freeze_logistic_l2(_table("train"), {"0.01": {"threshold": 0.5}, "0.05": {"threshold": 0.4}}, tmp_path / "frozen.json")

    result = evaluate_frozen_fusion(_table("test"), frozen, partition="test")

    assert result["partition"] == "test"


def test_frozen_rubric_evaluation_uses_rubric_rows(tmp_path: Path) -> None:
    frozen = freeze_logistic_l2(
        _table("train", head="rubric"),
        {"0.01": {"threshold": 0.5}, "0.05": {"threshold": 0.4}},
        tmp_path / "rubric.json",
        head="rubric",
    )

    result = evaluate_frozen_fusion(_table("validation", head="rubric"), frozen)

    assert frozen["head"] == "rubric"
    assert result["partition"] == "validation"
