from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from miaguard.judge_score_fusion import (
    FPR_CAPS,
    MODEL_NAMES,
    build_grouped_folds,
    compute_training_weights,
    render_fusion_figures,
    run_head_grouped_oof,
    select_threshold_at_fpr,
    summarize_oof_predictions,
)


def _available_table(*, include_unavailable: bool = False) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for doc_number in range(10):
        for category, label, x1, x2 in (
            ("benign", 0, 0.08, 0.10),
            ("direct_rag_mia", 1, 0.86, 0.88),
            ("s2_mia", 1, 0.46, 0.62),
            ("masked_mia", 1, 0.76, 0.76),
            ("ia", 1, 0.12, 0.56),
        ):
            rows.append(
                {
                    "query_id": f"q-{doc_number}-{category}",
                    "doc_id": f"doc-{doc_number}",
                    "session_key": f"session-{doc_number}-{category}",
                    "turn_index": 3,
                    "attack_type": category,
                    "label": label,
                    "head": "logprob",
                    "x1": x1 + doc_number * 0.001,
                    "x2_observed": x2 + doc_number * 0.001,
                    "session_score_available": True,
                }
            )
            if include_unavailable:
                rows.append(
                    {
                        **rows[-1],
                        "query_id": f"early-{doc_number}-{category}",
                        "turn_index": 1,
                        "x2_observed": np.nan,
                        "session_score_available": False,
                    }
                )
    return pd.DataFrame(rows)


def test_grouped_folds_never_split_a_document() -> None:
    table = _available_table()

    folds = build_grouped_folds(table, n_splits=5, seed=19)

    assert len(folds) == 5
    for train_index, test_index in folds:
        train_docs = set(table.iloc[train_index]["doc_id"])
        test_docs = set(table.iloc[test_index]["doc_id"])
        assert train_docs.isdisjoint(test_docs)


def test_training_weights_balance_benign_and_attack_types() -> None:
    table = _available_table()

    weights = compute_training_weights(table)
    weighted_mass = table.assign(weight=weights).groupby("attack_type")["weight"].sum()

    assert weighted_mass["benign"] == pytest.approx(0.5)
    for attack_type in ("direct_rag_mia", "s2_mia", "masked_mia", "ia"):
        assert weighted_mass[attack_type] == pytest.approx(0.125)


def test_threshold_selection_enforces_benign_fpr_cap() -> None:
    rows = pd.DataFrame(
        {
            "label": [0, 0, 0, 0, 1, 1, 1, 1],
            "attack_type": ["benign"] * 4
            + ["direct_rag_mia", "s2_mia", "masked_mia", "ia"],
            "score": [0.01, 0.05, 0.10, 0.20, 0.20, 0.80, 0.90, 0.95],
        }
    )

    result = select_threshold_at_fpr(rows, fpr_cap=0.0)

    assert result["benign_fpr"] == pytest.approx(0.0)
    assert result["attack_macro_recall"] == pytest.approx(0.75)
    assert result["threshold"] == pytest.approx(0.80)


def test_grouped_oof_emits_all_models_for_available_session_rows() -> None:
    table = _available_table(include_unavailable=True)

    predictions, metadata = run_head_grouped_oof(
        table, head="logprob", n_splits=5, seed=23
    )

    assert set(predictions["model"]) == set(MODEL_NAMES)
    assert set(predictions["query_id"]) == {
        query_id for query_id in table.loc[table["session_score_available"], "query_id"]
    }
    assert predictions.groupby(["model", "query_id"]).size().eq(1).all()
    assert len(metadata["folds"]) == 5
    assert metadata["cohort"] == "session_score_available"
    assert set(FPR_CAPS) == {0.01, 0.05}


def test_oof_summary_and_figures_cover_all_threshold_constraints(tmp_path: Path) -> None:
    predictions, _ = run_head_grouped_oof(
        _available_table(), head="logprob", n_splits=5, seed=29
    )

    summary = summarize_oof_predictions(
        predictions, bootstrap_replicates=5, bootstrap_seed=31
    )
    model = summary["heads"]["logprob"]["models"]["logistic_l2"]
    assert 0.0 <= model["metrics"]["auroc"] <= 1.0
    assert set(model["thresholds"]) == {"0.01", "0.05"}
    for operating_point in model["thresholds"].values():
        assert "attack_macro_recall" in operating_point
        assert "weakest_attack_recall" in operating_point
    assert model["bootstrap"]["unit"] == "doc_id"

    manifest = render_fusion_figures(predictions, summary, tmp_path / "figures")

    assert set(manifest) == {
        "roc_curves",
        "precision_recall_curves",
        "low_fpr_recall_frontier",
        "calibration_curves",
    }
    for item in manifest.values():
        assert Path(item["png"]).is_file()
        assert Path(item["pdf"]).is_file()
