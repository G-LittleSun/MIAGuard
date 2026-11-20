from __future__ import annotations

import time
from collections import Counter
from pathlib import Path
from typing import Any

from rag_mia_data.io_utils import utc_now_iso, write_json_atomic, write_jsonl_atomic

from .config import AttackConfig
from .data import vector_store_path
from .defense import DefenseConfig, GuardedRAG, RuleDefense
from .defense_experiment import (
    _attack_rows,
    _baseline_metrics,
    _replay_ia,
    _threshold,
    _threshold_source,
)
from .model_client import create_model_client
from .vector_store import UnifiedVectorStore


_POLICY_SEVERITY = {
    "restrict_context": 0,
    "summarize_context": 1,
    "no_context_answer": 2,
    "deny_sensitive_answer": 3,
}


def select_ia_policy(policy_metrics: dict[str, dict[str, Any]]) -> str:
    if set(policy_metrics) != set(_POLICY_SEVERITY):
        raise ValueError("IA policy comparison requires all four MVP policies")
    return min(
        policy_metrics,
        key=lambda name: (
            float(policy_metrics[name]["attack_accuracy_after"]),
            _POLICY_SEVERITY[name],
        ),
    )


def run_ia_policy_experiment(
    project_root: Path,
    source_run_id: str,
    dataset_id: str,
    output_run_id: str,
    attack_config: AttackConfig,
    policies: dict[str, DefenseConfig],
    *,
    limit_per_class: int,
    offset_per_class: int,
) -> dict[str, Any]:
    if set(policies) != set(_POLICY_SEVERITY):
        raise ValueError("IA policy experiment requires all four policies")
    for name, config in policies.items():
        if config.medium_action != name:
            raise ValueError(f"Policy name and medium_action differ: {name}")

    root = project_root.resolve()
    output = root / "data" / "defense_policy_results" / output_run_id / dataset_id
    if output.exists():
        raise FileExistsError(f"IA policy output already exists: {output}")

    rows = _attack_rows(
        root,
        source_run_id,
        dataset_id,
        "ia",
        limit_per_class,
        offset_per_class,
    )
    threshold = _threshold(attack_config, "ia")
    threshold_source = _threshold_source(attack_config, "ia")
    baseline = _baseline_metrics(rows, threshold, threshold_source)
    client = create_model_client(attack_config, root)
    store = UnifiedVectorStore.load(
        vector_store_path(root, source_run_id, dataset_id), client
    )

    policy_metrics: dict[str, dict[str, Any]] = {}
    all_decisions: list[dict[str, Any]] = []
    query_events: list[dict[str, Any]] = []
    for policy_name, defense_config in policies.items():
        guard = GuardedRAG(store, RuleDefense(defense_config), attack_config.top_k)
        started = time.perf_counter()
        events, decisions, defended_rows = _replay_ia(
            rows,
            guard,
            client,
            attack_config,
            source_run_id,
            dataset_id,
        )
        elapsed_ms = (time.perf_counter() - started) * 1000
        after = _baseline_metrics(defended_rows, threshold, threshold_source)
        policy_metrics[policy_name] = {
            "access_action": policy_name,
            "attack_accuracy_before": baseline["accuracy"],
            "attack_accuracy_after": after["accuracy"],
            "attack_accuracy_reduction": baseline["accuracy"] - after["accuracy"],
            "attack_metrics_after": after,
            "action_counts": dict(
                sorted(Counter(row["access_action"] for row in decisions).items())
            ),
            "total_elapsed_ms": elapsed_ms,
            "average_end_to_end_ms": elapsed_ms / len(decisions),
        }
        for decision in decisions:
            decision["policy"] = policy_name
        all_decisions.extend(decisions)
        if not query_events:
            query_events = events

    selected = select_ia_policy(policy_metrics)
    selection = {
        "selected_policy": selected,
        "selection_objective": (
            "lowest_validation_attack_accuracy_then_least_severe_action"
        ),
        "validation_attack_accuracy": policy_metrics[selected][
            "attack_accuracy_after"
        ],
        "baseline_attack_accuracy": baseline["accuracy"],
        "requires_independent_holdout": True,
    }
    manifest = {
        "status": "completed",
        "completed_at": utc_now_iso(),
        "output_run_id": output_run_id,
        "source_run_id": source_run_id,
        "dataset_id": dataset_id,
        "attack": "ia",
        "limit_per_class": limit_per_class,
        "offset_per_class": offset_per_class,
        "selected_doc_ids": [str(row["doc_id"]) for row in rows],
        "policies": list(policies),
        "generation_model": attack_config.generation_model,
        "embedding_model": attack_config.embedding_model,
    }
    output.mkdir(parents=True, exist_ok=False)
    write_json_atomic(output / "run_manifest.json", manifest)
    write_json_atomic(output / "baseline_metrics.json", baseline)
    write_json_atomic(output / "policy_metrics.json", policy_metrics)
    write_json_atomic(output / "selected_policy.json", selection)
    write_jsonl_atomic(output / "query_events.jsonl", query_events)
    write_jsonl_atomic(output / "policy_decisions.jsonl", all_decisions)
    return {**selection, "output_path": str(output), "status": "completed"}


__all__ = ["run_ia_policy_experiment", "select_ia_policy"]
