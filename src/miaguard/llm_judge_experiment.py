from __future__ import annotations

import shutil
import time
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score

from rag_mia_data.io_utils import (
    read_jsonl,
    utc_now_iso,
    write_json_atomic,
    write_jsonl_atomic,
)

from .attack_pattern_library import AttackPatternLibrary
from .config import AttackConfig
from .data import vector_store_path
from .defense import DefenseConfig, evaluate_defense_decisions
from .defense_experiment import ATTACKS
from .llm_judge import LLMJudgeConfig, LLMJudgeDefense
from .model_client import create_model_client


def select_small_scale_events(
    rows: list[dict[str, Any]],
    limit_per_attack: int,
    benign_count: int,
) -> list[dict[str, Any]]:
    if limit_per_attack <= 0 or benign_count <= 0:
        raise ValueError("Small-scale sample sizes must be positive")
    selected: list[dict[str, Any]] = []
    for attack in ATTACKS:
        candidates = [row for row in rows if row.get("attack_type") == attack]
        if len(candidates) < limit_per_attack:
            raise ValueError(f"Not enough source events for {attack}")
        selected.extend(candidates[:limit_per_attack])

    benign = [row for row in rows if int(row.get("intent_label", -1)) == 0]
    if len(benign) < benign_count:
        raise ValueError("Not enough benign source events")
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in benign:
        metadata = row.get("attack_metadata", {})
        pattern = str(metadata.get("hard_benign_pattern", "benign"))
        groups.setdefault(pattern, []).append(row)
    selected_benign: list[dict[str, Any]] = []
    group_names = sorted(groups)
    while len(selected_benign) < benign_count:
        added = False
        for name in group_names:
            if groups[name] and len(selected_benign) < benign_count:
                selected_benign.append(groups[name].pop(0))
                added = True
        if not added:
            break
    selected.extend(selected_benign)
    return selected


def _document_texts(project_root: Path, event: dict[str, Any]) -> dict[str, str]:
    store_path = vector_store_path(
        project_root,
        str(event["run_id"]),
        str(event["dataset_id"]),
    )
    return {
        str(row["doc_id"]): str(row["text"])
        for row in read_jsonl(store_path / "documents.jsonl")
    }


def evaluate_judge_classification(rows: list[dict[str, Any]]) -> dict[str, Any]:
    labels = np.asarray([int(row["intent_label"]) for row in rows], dtype=int)
    predictions = np.asarray(
        [1 if row["judge_verdict"] in {"attack", "suspicious"} else 0 for row in rows],
        dtype=int,
    )
    benign = labels == 0
    attacks = labels == 1
    return {
        "accuracy": float(accuracy_score(labels, predictions)),
        "precision": float(precision_score(labels, predictions, zero_division=0)),
        "recall": float(recall_score(labels, predictions, zero_division=0)),
        "f1": float(f1_score(labels, predictions, zero_division=0)),
        "benign_false_positive_rate": float(np.mean(predictions[benign]))
        if np.any(benign)
        else 0.0,
        "attack_uncertain_rate": float(
            np.mean(
                [row["judge_verdict"] == "uncertain" for row in rows if row["intent_label"] == 1]
            )
        )
        if np.any(attacks)
        else 0.0,
        "benign_uncertain_rate": float(
            np.mean(
                [row["judge_verdict"] == "uncertain" for row in rows if row["intent_label"] == 0]
            )
        )
        if np.any(benign)
        else 0.0,
    }


def run_llm_judge_experiment(
    project_root: Path,
    source_events_path: Path,
    output_run_id: str,
    attack_config: AttackConfig,
    defense_config: DefenseConfig,
    judge_config: LLMJudgeConfig,
    *,
    limit_per_attack: int = 2,
    benign_count: int = 8,
) -> dict[str, Any]:
    root = project_root.resolve()
    rows = list(read_jsonl(source_events_path.resolve()))
    selected = select_small_scale_events(rows, limit_per_attack, benign_count)
    dataset_ids = {str(row["dataset_id"]) for row in selected}
    if len(dataset_ids) != 1:
        raise ValueError("Small-scale Judge experiment requires one dataset")
    dataset_id = next(iter(dataset_ids))
    output = root / "data" / "llm_judge_results" / output_run_id / dataset_id
    if output.exists():
        raise FileExistsError(f"LLM Judge output already exists: {output}")

    client = create_model_client(attack_config, root)
    client.validate_models()
    library = AttackPatternLibrary.load(judge_config.manifest_path)
    detector = LLMJudgeDefense(
        defense_config,
        judge_config,
        client,
        attack_config.generation_model,
        library,
    )
    documents = _document_texts(root, selected[0])
    decisions: list[dict[str, Any]] = []
    for event in selected:
        retrieved_ids = [str(value) for value in event.get("retrieved_doc_ids", [])]
        snippets = [documents[doc_id] for doc_id in retrieved_ids if doc_id in documents]
        started = time.perf_counter()
        decision = detector.decide(
            str(event["query"]),
            str(event["session_id"]),
            retrieved_ids,
            snippets,
        )
        latency_ms = (time.perf_counter() - started) * 1000
        decisions.append(
            {
                "event_id": str(event["event_id"]),
                "attack_type": str(event["attack_type"]),
                "intent_label": int(event["intent_label"]),
                "membership_label": event.get("membership_label"),
                **decision.to_dict(),
                "decision_latency_ms": latency_ms,
            }
        )

    policy_metrics = evaluate_defense_decisions(decisions)
    metrics = evaluate_judge_classification(decisions)
    metrics["sample_count"] = len(decisions)
    metrics["attack_query_count"] = sum(row["intent_label"] == 1 for row in decisions)
    metrics["benign_query_count"] = sum(row["intent_label"] == 0 for row in decisions)
    metrics["average_decision_latency_ms"] = policy_metrics[
        "average_decision_latency_ms"
    ]
    metrics["attack_detection_rate_by_type"] = {
        attack: sum(
            row["judge_verdict"] in {"attack", "suspicious"}
            for row in decisions
            if row["attack_type"] == attack
        )
        / limit_per_attack
        for attack in ATTACKS
    }
    metrics["predicted_attack_type_counts"] = dict(
        sorted(Counter(row["predicted_attack_type"] for row in decisions).items())
    )
    metrics["judge_verdict_counts"] = dict(
        sorted(Counter(row["judge_verdict"] for row in decisions).items())
    )
    metrics["scope"] = "llm_judge_detector_small_scale"
    metrics["policy_intervention"] = {
        "benign_intervention_rate": policy_metrics["benign_false_positive_rate"],
        "benign_allow_rate": policy_metrics["benign_allow_rate"],
        "action_counts": policy_metrics["action_counts"],
    }

    manifest = {
        "status": "completed",
        "completed_at": utc_now_iso(),
        "output_run_id": output_run_id,
        "dataset_id": dataset_id,
        "source_events_path": str(source_events_path.resolve()),
        "sample_size": len(selected),
        "limit_per_attack": limit_per_attack,
        "benign_count": benign_count,
        "detector": "llm_as_judge_mvp_v1",
        "routing_mode": judge_config.routing_mode,
        "detector_input_fields": list(detector.detector_input_fields()),
        "generation_model": attack_config.generation_model,
        "attack_pattern_library": {
            "name": library.name,
            "version": library.version,
            "patterns": {
                pattern.pattern_id: pattern.version
                for pattern in library.patterns.values()
            },
        },
    }
    output.mkdir(parents=True, exist_ok=False)
    write_jsonl_atomic(output / "query_events.jsonl", selected)
    write_jsonl_atomic(output / "judge_decisions.jsonl", decisions)
    write_json_atomic(output / "detector_metrics.json", metrics)
    write_json_atomic(output / "run_manifest.json", manifest)
    shutil.copytree(library.root, output / "attack_pattern_library_snapshot")
    summary = {
        "status": "completed",
        "output_path": str(output),
        "sample_count": len(selected),
        "detector_accuracy": metrics["accuracy"],
        "detector_f1": metrics["f1"],
        "attack_recall": metrics["recall"],
        "benign_false_positive_rate": metrics["benign_false_positive_rate"],
        "average_decision_latency_ms": metrics["average_decision_latency_ms"],
    }
    write_json_atomic(output / "summary.json", summary)
    return summary


__all__ = ["run_llm_judge_experiment", "select_small_scale_events"]
