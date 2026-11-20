from pathlib import Path

import pandas as pd
import pytest

from miaguard.judge_score_analysis import (
    joint_density_maps,
    render_score_figures,
    summarize_score_table,
)


def _table() -> pd.DataFrame:
    rows = []
    groups = (
        ("benign-1", "benign", 0),
        ("benign-2", "benign", 0),
        ("ia-1", "ia", 1),
        ("ia-2", "ia", 1),
    )
    for head in ("rubric", "logprob"):
        for doc_index, (doc_id, attack_type, label) in enumerate(groups):
            for turn in range(1, 6):
                available = turn >= 3
                value = (doc_index * 5 + turn) / 25
                rows.append(
                    {
                        "query_id": f"{doc_id}-q{turn}",
                        "doc_id": doc_id,
                        "session_key": f"session-{doc_id}",
                        "turn_index": turn,
                        "traffic_type": "attack" if label else "benign",
                        "attack_type": attack_type,
                        "label": label,
                        "head": head,
                        "x1": value,
                        "x2_observed": value if available else float("nan"),
                        "session_score_available": available,
                    }
                )
    return pd.DataFrame(rows)


def test_summary_reports_empirical_statistics_and_availability() -> None:
    report = summarize_score_table(
        _table(), bootstrap_seed=17, bootstrap_replicates=20
    )

    assert set(report["heads"]) == {"rubric", "logprob"}
    logprob = report["heads"]["logprob"]
    assert logprob["availability"]["turn_1"] == 0.0
    assert logprob["availability"]["turn_3"] == 1.0
    assert logprob["correlation"]["all"]["spearman"] == pytest.approx(1.0)
    benign_x1 = logprob["groups"]["benign"]["x1"]
    assert set(benign_x1) == {
        "count",
        "mean",
        "std",
        "median",
        "iqr",
        "p05",
        "p25",
        "p75",
        "p95",
    }
    assert logprob["groups"]["benign"]["x2_missing_rate"] == pytest.approx(
        0.4
    )
    assert report["bootstrap"]["unit"] == "doc_id"
    assert report["bootstrap"]["replicates"] == 20


def test_summary_uses_none_for_constant_correlation() -> None:
    table = _table()
    table.loc[table["head"] == "rubric", "x1"] = 0.5

    report = summarize_score_table(table, bootstrap_replicates=0)

    correlation = report["heads"]["rubric"]["correlation"]["all"]
    assert correlation["spearman"] is None
    assert correlation["reason"] == "constant_input"


def test_render_score_figures_writes_publication_formats(tmp_path: Path) -> None:
    manifest = render_score_figures(_table(), tmp_path / "figures")

    expected = {
        "rubric_joint_density_triptych",
        "rubric_attack_enrichment_small_multiples",
        "rubric_marginal_frequency_map",
        "rubric_temporal_availability",
        "logprob_joint_density_triptych",
        "logprob_attack_enrichment_small_multiples",
        "logprob_marginal_frequency_map",
        "logprob_temporal_availability",
    }
    assert set(manifest) == expected
    for item in manifest.values():
        png = Path(item["png"])
        pdf = Path(item["pdf"])
        assert png.is_file() and png.stat().st_size > 1_000
        assert pdf.is_file() and pdf.stat().st_size > 1_000
        assert item["style"] == "publication_v2"
        assert item["label_source"] == "frozen_ground_truth"


def test_joint_density_maps_macro_balance_attack_types_and_exclude_missing() -> None:
    rows = []
    for attack_type, count, x1, x2 in (
        ("direct_rag_mia", 1, 0.9, 0.9),
        ("s2_mia", 1, 0.7, 0.7),
        ("masked_mia", 1, 0.5, 0.5),
        ("ia", 100, 0.1, 0.1),
    ):
        for _ in range(count):
            rows.append(
                {
                    "doc_id": f"{attack_type}-doc",
                    "attack_type": attack_type,
                    "label": 1,
                    "x1": x1,
                    "x2_observed": x2,
                    "session_score_available": True,
                }
            )
    rows.extend(
        {
            "doc_id": "benign-doc",
            "attack_type": "benign",
            "label": 0,
            "x1": 0.1,
            "x2_observed": 0.1,
            "session_score_available": True,
        }
        for _ in range(4)
    )
    rows.append(
        {
            "doc_id": "ia-doc",
            "attack_type": "ia",
            "label": 1,
            "x1": 0.9,
            "x2_observed": float("nan"),
            "session_score_available": False,
        }
    )

    maps = joint_density_maps(pd.DataFrame(rows), bin_edges=[0.0, 0.25, 0.5, 0.75, 1.0])

    assert maps["benign_density"].sum() == pytest.approx(1.0)
    assert maps["attack_macro_density"].sum() == pytest.approx(1.0)
    assert maps["attack_macro_density"][0, 0] == pytest.approx(0.25)
    assert maps["attack_macro_density"][3, 3] == pytest.approx(0.25)
    assert maps["combined_counts"].sum() == 107
    assert maps["sparse_threshold"] == 5
    assert maps["sparse_note"] == "Hatched cells: fewer than 5 raw samples"
