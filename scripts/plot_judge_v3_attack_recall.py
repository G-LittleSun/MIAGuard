"""Plot per-attack recall at the published, train-frozen operating point."""

from __future__ import annotations

import json
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

from miaguard.judge_score_dataset import build_score_table
from miaguard.judge_score_frozen import evaluate_frozen_fusion
from miaguard.query_bank.judge_benchmark import load_verified_judge_records


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
TEST_RUN = DATA / "progressive_judge_v3_binary_logprob_test_qwen2_5_7b_bf16_20260920" / "test"
COMPARISON = DATA / "judge_score_comparison_v3_20261015" / "final_test_comparison.json"
TARGET = ROOT / "docs" / "assets" / "miaguard-judge-v3-attack-recall"
ATTACKS = (
    ("direct_rag_mia", "Direct RAG-MIA"),
    ("s2_mia", "S²-MIA"),
    ("masked_mia", "Masked MIA"),
    ("ia", "IA"),
)
METHODS = (
    ("rubric", "LLM 直接评分", "judge_score_frozen_v3_rubric_20261015", "#2865A8", -0.19),
    ("binary_logprob", "基于 Logprob 的风险评分",
     "judge_score_frozen_v3_binary_logprob_20260920", "#D55E00", 0.19),
)


def main() -> None:
    records, _ = load_verified_judge_records(TEST_RUN)
    table, _ = build_score_table(records)
    comparison = json.loads(COMPARISON.read_text(encoding="utf-8"))
    cohort = comparison["cohort"]

    font_manager.fontManager.addfont("C:/Windows/Fonts/msyh.ttc")
    plt.rcParams.update({
        "font.family": "Microsoft YaHei",
        "font.size": 10,
        "pdf.fonttype": 42,
        "text.color": "#172831",
        "axes.labelcolor": "#172831",
        "xtick.color": "#435359",
        "ytick.color": "#172831",
    })
    fig, ax = plt.subplots(figsize=(8, 4.5), facecolor="white")
    fig.subplots_adjust(left=0.115, right=0.97, top=0.79, bottom=0.13)
    positions = list(range(len(ATTACKS)))

    for scheme, label, model_dir, color, offset in METHODS:
        frozen = json.loads((DATA / model_dir / "logistic_l2.json").read_text(encoding="utf-8"))
        evaluated = evaluate_frozen_fusion(table, frozen, partition="test")
        published = comparison["schemes"][scheme]["operating_points"]["0.01"]
        if (evaluated["rows"] != cohort["rows"] or evaluated["documents"] != cohort["documents"]
                or any(not math.isclose(evaluated["operating_points"]["0.01"][key], published[key])
                       for key in ("threshold", "benign_fpr"))):
            raise ValueError(f"{scheme}: test cohort or frozen operating point does not match")
        method_rows = table.loc[(table["head"] == frozen["head"]) & table["session_score_available"]]
        counts = method_rows["attack_type"].value_counts()
        verified = evaluated["operating_points"]["0.01"]["attack_recalls"]
        plotted = []
        bar_labels = []
        normal_count = int((method_rows["label"] == 0).sum())
        print(f"{scheme}: false positives {round(published['benign_fpr'] * normal_count)}/{normal_count}")
        for attack, _ in ATTACKS:
            recall = verified[attack]
            if not math.isclose(recall, published["attack_recalls"][attack]):
                raise ValueError(f"{scheme}: {attack} recall does not match the published result")
            total = int(counts[attack])
            detected = round(recall * total)
            if not math.isclose(detected / total, recall):
                raise ValueError(f"{scheme}: {attack} recall is not consistent with the count")
            percent = 100.0 * recall
            plotted.append(percent)
            number = f"{percent:.0f}" if percent.is_integer() else f"{percent:.2f}"
            bar_labels.append(f"{number}%")
            print(f"  {attack}: {detected}/{total} ({number}%)")
        bars = ax.bar([pos + offset for pos in positions], plotted, width=0.32,
                      color=color, label=label, zorder=3)
        ax.bar_label(bars, labels=bar_labels, padding=4,
                     bbox={"facecolor": "white", "edgecolor": "none", "pad": 1})

    ax.set_xlim(-0.55, len(ATTACKS) - 0.45)
    ax.set_ylim(0, 112)
    ax.set_xticks(positions, [label for _, label in ATTACKS])
    ax.set_yticks([0, 25, 50, 75, 100])
    ax.set_ylabel("攻击检出率（%）", labelpad=6)
    ax.tick_params(axis="x", length=0, pad=8)
    ax.tick_params(axis="y", length=3)
    ax.grid(axis="y", color="#DCE4E8", linewidth=0.65, zorder=0)
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color("#819098")
    ax.spines[["left", "bottom"]].set_linewidth(0.6)

    fig.text(0.5, 0.965, "四类攻击的检出率", ha="center", va="top",
             fontsize=17, fontweight="bold")
    handles, labels = ax.get_legend_handles_labels()
    fig.legend(handles, labels, ncol=2, frameon=False, loc="upper center",
               bbox_to_anchor=(0.5, 0.89), handlelength=1.9, columnspacing=2.4)
    fig.savefig(TARGET.with_suffix(".png"), dpi=300, facecolor="white")
    fig.savefig(TARGET.with_suffix(".pdf"), facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    main()
