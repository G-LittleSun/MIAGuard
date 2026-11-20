from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import matplotlib
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from .judge_score_dataset import ATTACK_TYPES, SCORE_HEADS

matplotlib.use("Agg", force=True)
from matplotlib import pyplot as plt  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap, Normalize  # noqa: E402


_COLORS = {
    "benign": "#0072B2",
    "attack": "#D55E00",
    "neutral": "#6B7280",
    "accent": "#009E73",
}
_STYLE = {
    "font.family": "sans-serif",
    "font.sans-serif": ["DejaVu Sans", "Arial", "Liberation Sans"],
    "font.size": 8.0,
    "axes.labelsize": 8.0,
    "axes.titlesize": 8.5,
    "axes.linewidth": 0.7,
    "xtick.labelsize": 7.0,
    "ytick.labelsize": 7.0,
    "legend.fontsize": 7.0,
    "legend.frameon": False,
    "lines.linewidth": 1.4,
    "savefig.dpi": 300,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
}
_PUBLICATION_STYLE_V2 = {
    **_STYLE,
    "font.size": 7.5,
    "axes.labelsize": 7.5,
    "axes.titlesize": 7.5,
    "legend.fontsize": 6.8,
}
_DIVERGING_CMAP = LinearSegmentedColormap.from_list(
    "attack_enrichment", ["#2166AC", "#F7F7F7", "#B2182B"]
)


def _number(value: float) -> float | None:
    return float(value) if math.isfinite(float(value)) else None


def _describe(values: pd.Series) -> dict[str, Any]:
    clean = values.dropna().astype(float)
    if clean.empty:
        return {
            "count": 0,
            "mean": None,
            "std": None,
            "median": None,
            "iqr": None,
            "p05": None,
            "p25": None,
            "p75": None,
            "p95": None,
        }
    quantiles = clean.quantile([0.05, 0.25, 0.5, 0.75, 0.95])
    return {
        "count": int(len(clean)),
        "mean": _number(clean.mean()),
        "std": _number(clean.std(ddof=1)) if len(clean) > 1 else 0.0,
        "median": _number(quantiles.loc[0.5]),
        "iqr": _number(quantiles.loc[0.75] - quantiles.loc[0.25]),
        "p05": _number(quantiles.loc[0.05]),
        "p25": _number(quantiles.loc[0.25]),
        "p75": _number(quantiles.loc[0.75]),
        "p95": _number(quantiles.loc[0.95]),
    }


def _correlation(rows: pd.DataFrame) -> dict[str, Any]:
    available = rows.loc[
        rows["session_score_available"].astype(bool), ["x1", "x2_observed"]
    ].dropna()
    if len(available) < 2:
        return {
            "count": int(len(available)),
            "spearman": None,
            "reason": "insufficient_observations",
        }
    if (
        available["x1"].nunique() < 2
        or available["x2_observed"].nunique() < 2
    ):
        return {
            "count": int(len(available)),
            "spearman": None,
            "reason": "constant_input",
        }
    result = spearmanr(available["x1"], available["x2_observed"])
    return {
        "count": int(len(available)),
        "spearman": float(result.statistic),
        "reason": None,
    }


def _group_summary(rows: pd.DataFrame) -> dict[str, Any]:
    return {
        "row_count": int(len(rows)),
        "x2_missing_rate": (
            float(1.0 - rows["session_score_available"].astype(bool).mean())
            if len(rows)
            else None
        ),
        "x1": _describe(rows["x1"]),
        "x2_observed": _describe(rows["x2_observed"]),
    }


def _category_rows(rows: pd.DataFrame) -> dict[str, pd.DataFrame]:
    return {
        "benign": rows[rows["label"] == 0],
        "all_attack": rows[rows["label"] == 1],
        **{
            attack: rows[rows["attack_type"] == attack]
            for attack in ATTACK_TYPES
        },
    }


def _correlation_rows(rows: pd.DataFrame) -> dict[str, pd.DataFrame]:
    return {
        "all": rows,
        "benign": rows[rows["label"] == 0],
        "attack": rows[rows["label"] == 1],
    }


def _bootstrap_correlations(
    table: pd.DataFrame,
    *,
    seed: int,
    replicates: int,
) -> dict[str, Any]:
    if replicates <= 0:
        return {}
    doc_ids = sorted(str(value) for value in table["doc_id"].unique())
    by_doc = {doc_id: table[table["doc_id"] == doc_id] for doc_id in doc_ids}
    rng = np.random.default_rng(seed)
    samples: dict[str, dict[str, list[float]]] = {
        head: {category: [] for category in ("all", "benign", "attack")}
        for head in SCORE_HEADS
    }
    for _ in range(replicates):
        sampled = pd.concat(
            [by_doc[str(doc_id)] for doc_id in rng.choice(doc_ids, len(doc_ids))],
            ignore_index=True,
        )
        for head in SCORE_HEADS:
            head_rows = sampled[sampled["head"] == head]
            for category, rows in _correlation_rows(head_rows).items():
                value = _correlation(rows)["spearman"]
                if value is not None:
                    samples[head][category].append(float(value))
    return {
        head: {
            category: {
                "low_95": float(np.quantile(values, 0.025)),
                "high_95": float(np.quantile(values, 0.975)),
                "valid_replicates": len(values),
            }
            for category, values in categories.items()
            if values
        }
        for head, categories in samples.items()
    }


def summarize_score_table(
    table: pd.DataFrame,
    *,
    bootstrap_seed: int = 20260829,
    bootstrap_replicates: int = 1000,
) -> dict[str, Any]:
    if bootstrap_replicates < 0:
        raise ValueError("bootstrap_replicates must be non-negative")
    required = {
        "doc_id",
        "turn_index",
        "label",
        "attack_type",
        "head",
        "x1",
        "x2_observed",
        "session_score_available",
    }
    missing = required.difference(table.columns)
    if missing:
        raise ValueError(f"Score table is missing columns: {sorted(missing)}")
    if set(table["head"].unique()) != set(SCORE_HEADS):
        raise ValueError("Score table must contain rubric and logprob heads")
    heads: dict[str, Any] = {}
    for head in SCORE_HEADS:
        rows = table[table["head"] == head]
        availability = (
            rows.groupby("turn_index", sort=True)["session_score_available"]
            .mean()
            .to_dict()
        )
        heads[head] = {
            "row_count": int(len(rows)),
            "availability": {
                f"turn_{int(turn)}": float(value)
                for turn, value in availability.items()
            },
            "groups": {
                name: _group_summary(group_rows)
                for name, group_rows in _category_rows(rows).items()
            },
            "correlation": {
                name: _correlation(group_rows)
                for name, group_rows in _correlation_rows(rows).items()
            },
        }
    return {
        "schema_version": 1,
        "heads": heads,
        "bootstrap": {
            "unit": "doc_id",
            "seed": bootstrap_seed,
            "replicates": bootstrap_replicates,
            "confidence_level": 0.95,
            "correlation_intervals": _bootstrap_correlations(
                table,
                seed=bootstrap_seed,
                replicates=bootstrap_replicates,
            ),
        },
        "distribution_assumption": "empirical_nonparametric",
        "gaussian_fit_used": False,
    }


def _finish_axes(ax: Any, *, equal: bool = False) -> None:
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(direction="out", length=3, width=0.7)
    ax.grid(axis="y", color="#D1D5DB", linewidth=0.45, alpha=0.55)
    if equal:
        ax.set_xlim(0.0, 1.0)
        ax.set_ylim(0.0, 1.0)
        ax.set_aspect("equal", adjustable="box")


def _document_balanced_weights(rows: pd.DataFrame) -> np.ndarray:
    groups = rows.groupby("doc_id", sort=True).groups
    weights = pd.Series(0.0, index=rows.index, dtype=float)
    for _, indices in groups.items():
        weights.loc[indices] = 1.0 / (len(groups) * len(indices))
    return weights.to_numpy()


def _density(
    rows: pd.DataFrame,
    x_edges: np.ndarray,
    y_edges: np.ndarray,
) -> np.ndarray:
    if rows.empty:
        return np.zeros((len(x_edges) - 1, len(y_edges) - 1), dtype=float)
    weights = _document_balanced_weights(rows)
    density, _, _ = np.histogram2d(
        rows["x1"], rows["x2_observed"], bins=(x_edges, y_edges), weights=weights
    )
    total = density.sum()
    return density / total if total else density


def joint_density_maps(
    rows: pd.DataFrame,
    *,
    bin_edges: list[float] | np.ndarray,
    epsilon: float = 1e-4,
) -> dict[str, np.ndarray]:
    """Return document-balanced benign and attack-macro joint distributions."""
    sparse_threshold = 5
    edges = np.asarray(bin_edges, dtype=float)
    if len(edges) < 2 or not np.all(np.diff(edges) > 0):
        raise ValueError("bin_edges must be strictly increasing")
    available = rows.loc[
        rows["session_score_available"].astype(bool)
    ].dropna(subset=["x1", "x2_observed"])
    benign = available[available["label"] == 0]
    attack = available[available["label"] == 1]
    benign_density = _density(benign, edges, edges)
    attack_densities = {
        attack_type: _density(
            attack[attack["attack_type"] == attack_type], edges, edges
        )
        for attack_type in ATTACK_TYPES
        if not attack[attack["attack_type"] == attack_type].empty
    }
    if attack_densities:
        attack_macro_density = sum(attack_densities.values()) / len(attack_densities)
    else:
        attack_macro_density = np.zeros_like(benign_density)
    counts, _, _ = np.histogram2d(
        available["x1"], available["x2_observed"], bins=(edges, edges)
    )
    enrichment = np.log2(
        (attack_macro_density + epsilon) / (benign_density + epsilon)
    )
    return {
        "bin_edges": edges,
        "benign_density": benign_density,
        "attack_macro_density": attack_macro_density,
        "attack_type_densities": attack_densities,
        "combined_counts": counts,
        "log2_enrichment": enrichment,
        "sparse_mask": counts < sparse_threshold,
        "sparse_threshold": sparse_threshold,
        "sparse_note": f"Hatched cells: fewer than {sparse_threshold} raw samples",
    }


def _add_sparse_hatching(ax: Any, maps: dict[str, np.ndarray]) -> None:
    edges = maps["bin_edges"]
    mask = maps["sparse_mask"]
    for x_index in range(mask.shape[0]):
        for y_index in range(mask.shape[1]):
            if mask[x_index, y_index] and maps["combined_counts"][x_index, y_index] > 0:
                ax.add_patch(
                    plt.Rectangle(
                        (edges[x_index], edges[y_index]),
                        edges[x_index + 1] - edges[x_index],
                        edges[y_index + 1] - edges[y_index],
                        fill=False,
                        hatch="////",
                        edgecolor="#9CA3AF",
                        linewidth=0.25,
                    )
                )


def _draw_density_grid(
    ax: Any,
    values: np.ndarray,
    edges: np.ndarray,
    *,
    cmap: Any,
    norm: Normalize,
) -> Any:
    image = ax.pcolormesh(
        edges,
        edges,
        values.T,
        cmap=cmap,
        norm=norm,
        shading="flat",
        rasterized=True,
    )
    _finish_axes(ax, equal=True)
    ax.grid(False)
    return image


def _plot_joint_density_triptych(rows: pd.DataFrame, title: str) -> Any:
    maps = joint_density_maps(rows, bin_edges=np.linspace(0.0, 1.0, 11))
    maximum = max(
        float(maps["benign_density"].max()),
        float(maps["attack_macro_density"].max()),
        1e-6,
    )
    figure, axes = plt.subplots(
        1, 3, figsize=(7.16, 2.45), sharex=True, sharey=True, constrained_layout=True
    )
    panels = (
        ("(a) Benign density", maps["benign_density"], "Blues", Normalize(0, maximum)),
        (
            "(b) Attack density (macro-balanced)",
            maps["attack_macro_density"],
            "Oranges",
            Normalize(0, maximum),
        ),
        (
            "(c) Attack enrichment, log₂ ratio",
            np.clip(maps["log2_enrichment"], -3, 3),
            _DIVERGING_CMAP,
            Normalize(-3, 3),
        ),
    )
    for axis, (panel_title, values, cmap, norm) in zip(axes, panels):
        image = _draw_density_grid(
            axis, values, maps["bin_edges"], cmap=cmap, norm=norm
        )
        if axis is axes[2]:
            _add_sparse_hatching(axis, maps)
        axis.set_title(panel_title, loc="left", fontweight="semibold")
        axis.set_xlabel("Query risk, x1")
        if axis is axes[0]:
            axis.set_ylabel("Session risk, x2")
        colorbar = figure.colorbar(image, ax=axis, fraction=0.045, pad=0.025)
        colorbar.ax.tick_params(labelsize=5.8, length=2)
    axes[2].text(
        0.98,
        0.03,
        maps["sparse_note"],
        transform=axes[2].transAxes,
        ha="right",
        va="bottom",
        fontsize=5.3,
        color="#4B5563",
        bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.82, "pad": 1.2},
    )
    figure.suptitle(title, x=0.01, ha="left", fontsize=8.2, fontweight="semibold")
    return figure


def _plot_attack_enrichment_small_multiples(rows: pd.DataFrame, title: str) -> Any:
    maps = joint_density_maps(rows, bin_edges=np.linspace(0.0, 1.0, 9))
    figure, axes = plt.subplots(
        2, 2, figsize=(7.16, 5.0), sharex=True, sharey=True, constrained_layout=True
    )
    names = {
        "direct_rag_mia": "Direct RAG-MIA",
        "s2_mia": "S²-MIA",
        "masked_mia": "Masked MIA",
        "ia": "IA",
    }
    for axis, attack_type in zip(axes.flat, ATTACK_TYPES):
        density = maps["attack_type_densities"].get(attack_type)
        if density is None:
            values = np.zeros_like(maps["benign_density"])
        else:
            values = np.clip(
                np.log2((density + 1e-4) / (maps["benign_density"] + 1e-4)),
                -3,
                3,
            )
        image = _draw_density_grid(
            axis,
            values,
            maps["bin_edges"],
            cmap=_DIVERGING_CMAP,
            norm=Normalize(-3, 3),
        )
        _add_sparse_hatching(axis, maps)
        axis.set_title(f"{names[attack_type]} vs benign", loc="left", fontweight="semibold")
    axes[1, 0].set_xlabel("Query risk, x1")
    axes[1, 1].set_xlabel("Query risk, x1")
    axes[0, 0].set_ylabel("Session risk, x2")
    axes[1, 0].set_ylabel("Session risk, x2")
    colorbar = figure.colorbar(image, ax=axes.ravel().tolist(), fraction=0.025, pad=0.02)
    colorbar.set_label("log₂ density ratio", fontsize=6.5)
    colorbar.ax.tick_params(labelsize=5.8, length=2)
    axes[1, 1].text(
        0.98,
        0.03,
        maps["sparse_note"],
        transform=axes[1, 1].transAxes,
        ha="right",
        va="bottom",
        fontsize=5.3,
        color="#4B5563",
        bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.82, "pad": 1.2},
    )
    figure.suptitle(title, x=0.01, ha="left", fontsize=8.2, fontweight="semibold")
    return figure


def _weighted_histogram(rows: pd.DataFrame, column: str, edges: np.ndarray) -> np.ndarray:
    if rows.empty:
        return np.zeros(len(edges) - 1, dtype=float)
    values = rows[column].dropna()
    if values.empty:
        return np.zeros(len(edges) - 1, dtype=float)
    selected = rows.loc[values.index]
    weights = _document_balanced_weights(selected)
    histogram, _ = np.histogram(values, bins=edges, weights=weights)
    return histogram / histogram.sum() if histogram.sum() else histogram


def _plot_marginal_frequency_map(rows: pd.DataFrame, title: str) -> Any:
    edges = np.linspace(0.0, 1.0, 11)
    categories = ("benign", *ATTACK_TYPES)
    labels = ("Benign", "Direct", "S²", "Masked", "IA")
    figure, axes = plt.subplots(1, 2, figsize=(7.16, 2.8), constrained_layout=True)
    for axis, column, panel in (
        (axes[0], "x1", "(a) Query-risk mass"),
        (axes[1], "x2_observed", "(b) Available session-risk mass"),
    ):
        source = rows if column == "x1" else rows[rows["session_score_available"].astype(bool)]
        matrix = np.vstack(
            [
                _weighted_histogram(source[source["attack_type"] == category], column, edges)
                for category in categories
            ]
        )
        image = axis.imshow(
            matrix,
            cmap="YlGnBu",
            norm=Normalize(0, max(float(matrix.max()), 1e-6)),
            aspect="auto",
            interpolation="nearest",
            extent=(0, 1, len(categories) - 0.5, -0.5),
            rasterized=True,
        )
        axis.set(title=panel, xlabel="Risk score", yticks=range(len(categories)), yticklabels=labels)
        _finish_axes(axis)
        axis.grid(False)
        colorbar = figure.colorbar(image, ax=axis, fraction=0.045, pad=0.03)
        colorbar.set_label("Within-group probability mass", fontsize=6.2)
        colorbar.ax.tick_params(labelsize=5.8, length=2)
    figure.suptitle(title, x=0.01, ha="left", fontsize=8.2, fontweight="semibold")
    return figure


def _save_figure(
    figure: Any,
    output_dir: Path,
    key: str,
    *,
    style: str,
) -> dict[str, Any]:
    png = (output_dir / f"{key}.png").resolve()
    pdf = (output_dir / f"{key}.pdf").resolve()
    metadata = {"Creator": "MIAGuard", "Subject": "Judge score analysis"}
    figure.savefig(png, bbox_inches="tight", facecolor="white")
    figure.savefig(pdf, bbox_inches="tight", facecolor="white", metadata=metadata)
    plt.close(figure)
    return {
        "png": str(png),
        "pdf": str(pdf),
        "style": style,
        "label_source": "frozen_ground_truth",
        "dpi": 300,
    }


def _plot_ecdf(rows: pd.DataFrame, column: str, title: str) -> Any:
    figure, ax = plt.subplots(figsize=(3.35, 2.45), constrained_layout=True)
    for label, name, color in (
        (0, "Benign", _COLORS["benign"]),
        (1, "Attack", _COLORS["attack"]),
    ):
        values = np.sort(
            rows.loc[rows["label"] == label, column].dropna().to_numpy(float)
        )
        if len(values):
            y = np.arange(1, len(values) + 1) / len(values)
            ax.step(
                values,
                y,
                where="post",
                color=color,
                label=f"{name} (n={len(values):,})",
            )
    ax.set(xlim=(0, 1), ylim=(0, 1), xlabel="Risk score", ylabel="Empirical CDF")
    ax.set_title(title, loc="left", fontweight="semibold")
    ax.legend(loc="lower right")
    _finish_axes(ax)
    return figure


def _plot_binary_plane(rows: pd.DataFrame, title: str) -> Any:
    available = rows[rows["session_score_available"].astype(bool)]
    figure, ax = plt.subplots(figsize=(3.35, 3.0), constrained_layout=True)
    if len(available):
        ax.hexbin(
            available["x1"],
            available["x2_observed"],
            gridsize=25,
            extent=(0, 1, 0, 1),
            mincnt=1,
            cmap="Greys",
            alpha=0.28,
            linewidths=0,
            rasterized=True,
        )
        for label, name, color, marker in (
            (0, "Benign", _COLORS["benign"], "o"),
            (1, "Attack", _COLORS["attack"], "^"),
        ):
            group = available[available["label"] == label]
            ax.scatter(
                group["x1"],
                group["x2_observed"],
                s=10,
                marker=marker,
                facecolors="none",
                edgecolors=color,
                linewidths=0.55,
                alpha=0.5,
                label=f"{name} (n={len(group):,})",
                rasterized=True,
            )
    ax.set(xlabel="Query risk, x1", ylabel="Session risk, x2")
    ax.set_title(title, loc="left", fontweight="semibold")
    ax.legend(loc="lower right")
    _finish_axes(ax, equal=True)
    return figure


def _plot_attack_panels(rows: pd.DataFrame, title: str) -> Any:
    available = rows[rows["session_score_available"].astype(bool)]
    benign = available[available["label"] == 0]
    figure, axes = plt.subplots(
        2,
        2,
        figsize=(7.0, 5.8),
        sharex=True,
        sharey=True,
        constrained_layout=True,
    )
    names = {
        "direct_rag_mia": "Direct RAG-MIA",
        "s2_mia": "S²-MIA",
        "masked_mia": "Masked MIA",
        "ia": "IA",
    }
    for panel, attack_type in zip(axes.flat, ATTACK_TYPES):
        attack = available[available["attack_type"] == attack_type]
        panel.scatter(
            benign["x1"],
            benign["x2_observed"],
            s=9,
            facecolors="none",
            edgecolors=_COLORS["benign"],
            linewidths=0.5,
            alpha=0.38,
            label=f"Benign (n={len(benign):,})",
            rasterized=True,
        )
        panel.scatter(
            attack["x1"],
            attack["x2_observed"],
            s=10,
            marker="^",
            facecolors="none",
            edgecolors=_COLORS["attack"],
            linewidths=0.55,
            alpha=0.55,
            label=f"Attack (n={len(attack):,})",
            rasterized=True,
        )
        panel.set_title(names[attack_type], loc="left", fontweight="semibold")
        _finish_axes(panel, equal=True)
    axes[1, 0].set_xlabel("Query risk, x1")
    axes[1, 1].set_xlabel("Query risk, x1")
    axes[0, 0].set_ylabel("Session risk, x2")
    axes[1, 0].set_ylabel("Session risk, x2")
    axes[0, 0].legend(loc="lower right")
    figure.suptitle(title, x=0.01, ha="left", fontweight="semibold")
    return figure


def _plot_binned_attack_rate(rows: pd.DataFrame, title: str) -> Any:
    available = rows[rows["session_score_available"].astype(bool)]
    bins = np.linspace(0.0, 1.0, 11)
    total, _, _ = np.histogram2d(
        available["x1"], available["x2_observed"], bins=(bins, bins)
    )
    attack, _, _ = np.histogram2d(
        available.loc[available["label"] == 1, "x1"],
        available.loc[available["label"] == 1, "x2_observed"],
        bins=(bins, bins),
    )
    rate = np.divide(attack, total, out=np.zeros_like(attack), where=total > 0)
    cmap = LinearSegmentedColormap.from_list(
        "benign_attack", ["#E6F2F8", "#F7F7F7", "#F4D9CC"]
    )
    figure, ax = plt.subplots(figsize=(3.7, 3.15), constrained_layout=True)
    image = ax.imshow(
        rate.T,
        origin="lower",
        extent=(0, 1, 0, 1),
        vmin=0,
        vmax=1,
        cmap=cmap,
        interpolation="nearest",
        aspect="equal",
    )
    for x in range(10):
        for y in range(10):
            count = int(total[x, y])
            if count:
                text = f"{rate[x, y]:.2f}\nn={count}" if count >= 5 else f"n={count}"
                ax.text(
                    (x + 0.5) / 10,
                    (y + 0.5) / 10,
                    text,
                    ha="center",
                    va="center",
                    fontsize=4.6,
                    color="#111827",
                )
                if count < 5:
                    ax.add_patch(
                        plt.Rectangle(
                            (x / 10, y / 10),
                            0.1,
                            0.1,
                            fill=False,
                            hatch="////",
                            edgecolor="#9CA3AF",
                            linewidth=0.25,
                        )
                    )
    colorbar = figure.colorbar(image, ax=ax, fraction=0.046, pad=0.04)
    colorbar.set_label("Attack fraction")
    ax.set(xlabel="Query risk, x1", ylabel="Session risk, x2")
    ax.set_title(title, loc="left", fontweight="semibold")
    _finish_axes(ax, equal=True)
    return figure


def _plot_by_turn(rows: pd.DataFrame, title: str) -> Any:
    turns = sorted(int(value) for value in rows["turn_index"].unique())
    figure, axes = plt.subplots(
        1, 3, figsize=(7.0, 2.35), constrained_layout=True
    )
    for ax, column, label in (
        (axes[0], "x1", "Query risk, x1"),
        (axes[1], "x2_observed", "Session risk, x2"),
    ):
        for target, name, color in (
            (0, "Benign", _COLORS["benign"]),
            (1, "Attack", _COLORS["attack"]),
        ):
            group = rows[rows["label"] == target]
            grouped = group.groupby("turn_index")[column]
            median = grouped.median().reindex(turns)
            lower = grouped.quantile(0.25).reindex(turns)
            upper = grouped.quantile(0.75).reindex(turns)
            ax.plot(turns, median, marker="o", markersize=3, color=color, label=name)
            ax.fill_between(turns, lower, upper, color=color, alpha=0.12, linewidth=0)
        ax.set(xlabel="Turn", ylabel=label, ylim=(0, 1), xticks=turns)
        _finish_axes(ax)
    for target, name, color, offset in (
        (0, "Benign", _COLORS["benign"], -0.14),
        (1, "Attack", _COLORS["attack"], 0.14),
    ):
        rates = (
            rows[rows["label"] == target]
            .groupby("turn_index")["session_score_available"]
            .mean()
            .reindex(turns)
        )
        axes[2].bar(
            np.asarray(turns) + offset,
            rates,
            width=0.28,
            color=color,
            alpha=0.8,
            label=name,
        )
    axes[2].set(
        xlabel="Turn",
        ylabel="x2 availability",
        ylim=(0, 1),
        xticks=turns,
    )
    _finish_axes(axes[2])
    axes[0].legend(loc="best")
    figure.suptitle(title, x=0.01, ha="left", fontweight="semibold")
    return figure


def render_score_figures(
    table: pd.DataFrame,
    output_dir: Path,
) -> dict[str, dict[str, Any]]:
    output_dir.mkdir(parents=True, exist_ok=False)
    manifest: dict[str, dict[str, Any]] = {}
    with plt.rc_context(_PUBLICATION_STYLE_V2):
        for head in SCORE_HEADS:
            rows = table[table["head"] == head]
            display = "Rubric" if head == "rubric" else "Log-probability"
            figures = {
                f"{head}_joint_density_triptych": _plot_joint_density_triptych(
                    rows, f"{display} score geometry"
                ),
                f"{head}_attack_enrichment_small_multiples": (
                    _plot_attack_enrichment_small_multiples(
                        rows, f"{display} attack-specific enrichment"
                    )
                ),
                f"{head}_marginal_frequency_map": _plot_marginal_frequency_map(
                    rows, f"{display} marginal score distributions"
                ),
                f"{head}_temporal_availability": _plot_by_turn(
                    rows, f"{display} temporal scoring semantics"
                ),
            }
            for key, figure in figures.items():
                manifest[key] = _save_figure(
                    figure, output_dir, key, style="publication_v2"
                )
    return manifest


__all__ = [
    "joint_density_maps",
    "render_score_figures",
    "summarize_score_table",
]
