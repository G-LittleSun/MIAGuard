from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

from rag_mia_data.io_utils import read_jsonl, utc_now_iso, write_json_atomic, write_jsonl_atomic

from .attack_pattern_library import AttackPatternLibrary
from .config import AttackConfig
from .data import attack_result_path, load_run_documents, vector_store_path
from .defense import GuardedRAG
from .direct_scorer import (
    DirectQueryRiskDetector,
    DirectScorerConfig,
    DirectSessionRiskDetector,
)
from .hard_query_experiment import hard_benign_query, paraphrase_attack_query
from .ia_attack import _generate_questions
from .ia_session_judge_experiment import benign_session_queries
from .model_client import create_model_client
from .two_stage_gateway import (
    TwoStageConfig,
    TwoStageGateway,
    build_two_stage_risk_event,
)
from .vector_store import UnifiedVectorStore


QUERY_ATTACKS = ("direct_rag_mia", "s2_mia", "masked_mia")


def binary_detection_metrics(
    labels: list[int],
    scores: list[float],
    threshold: float,
) -> dict[str, Any]:
    if len(labels) != len(scores) or not labels or set(labels) != {0, 1}:
        raise ValueError("Detection metrics require equally sized attack and benign labels")
    y_true = np.asarray(labels, dtype=int)
    y_score = np.asarray(scores, dtype=float)
    y_pred = (y_score >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    attack_scores = y_score[y_true == 1]
    benign_scores = y_score[y_true == 0]
    return {
        "sample_count": len(labels),
        "attack_count": int(np.sum(y_true == 1)),
        "benign_count": int(np.sum(y_true == 0)),
        "threshold": float(threshold),
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "auroc": float(roc_auc_score(y_true, y_score)),
        "auprc": float(average_precision_score(y_true, y_score)),
        "false_positive_rate": float(fp / (fp + tn)) if fp + tn else 0.0,
        "false_negative_rate": float(fn / (fn + tp)) if fn + tp else 0.0,
        "attack_score_mean": float(np.mean(attack_scores)),
        "benign_score_mean": float(np.mean(benign_scores)),
        "confusion_matrix": {
            "tn": int(tn),
            "fp": int(fp),
            "fn": int(fn),
            "tp": int(tp),
        },
    }


def _load_split(path: Path, partition: str) -> tuple[dict[str, Any], list[str]]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    partitions = manifest.get("partitions", {})
    if partition not in partitions:
        raise ValueError(f"Unknown frozen split partition: {partition}")
    doc_ids = [str(value) for value in partitions[partition]["member_doc_ids"]]
    return manifest, doc_ids


def _attack_row(project_root: Path, run_id: str, dataset_id: str, attack: str, doc_id: str) -> dict[str, Any]:
    path = attack_result_path(project_root, run_id, dataset_id, attack) / "results.jsonl"
    for row in read_jsonl(path):
        if str(row["doc_id"]) == doc_id:
            return row
    raise ValueError(f"Frozen {attack} result does not contain development doc {doc_id}")


def _latency_summary(values: list[float]) -> dict[str, float]:
    return {
        "mean_ms": float(np.mean(values)) if values else 0.0,
        "median_ms": float(np.median(values)) if values else 0.0,
        "p95_ms": float(np.percentile(values, 95)) if values else 0.0,
    }


def _scenario(
    *,
    session_id: str,
    traffic_type: str,
    attack_type: str,
    comparison_type: str,
    target_doc_id: str,
    queries: list[str],
) -> dict[str, Any]:
    return {
        "session_id": session_id,
        "traffic_type": traffic_type,
        "attack_type": attack_type,
        "comparison_type": comparison_type,
        "target_doc_id": target_doc_id,
        "queries": queries,
    }


def run_two_stage_direct_experiment(
    project_root: Path,
    source_run_id: str,
    dataset_id: str,
    output_run_id: str,
    attack_config: AttackConfig,
    gateway_config: TwoStageConfig,
    scorer_config: DirectScorerConfig,
    *,
    split_path: Path,
    partition: str = "development",
    samples_per_type: int = 1,
    ia_turn_count: int = 3,
) -> dict[str, Any]:
    if gateway_config.mode != "observe":
        raise ValueError("Direct scorer development experiments require observe mode")
    if not 1 <= samples_per_type <= 25:
        raise ValueError("samples_per_type must be between 1 and 25")
    if not 3 <= ia_turn_count <= 5:
        raise ValueError("ia_turn_count must be between 3 and 5")

    root = project_root.resolve()
    output = root / "data" / "two_stage_results" / output_run_id / dataset_id
    if output.exists():
        raise FileExistsError(f"Two-stage experiment output already exists: {output}")
    split_manifest, member_doc_ids = _load_split(split_path.resolve(), partition)
    required = 8 * samples_per_type
    if len(member_doc_ids) < required:
        raise ValueError("Frozen partition does not contain enough member documents")

    documents = {
        str(row["doc_id"]): row
        for row in load_run_documents(root, source_run_id, dataset_id)
    }
    client = create_model_client(attack_config, root)
    client.validate_models()
    store = UnifiedVectorStore.load(
        vector_store_path(root, source_run_id, dataset_id), client
    )
    library = AttackPatternLibrary.load(scorer_config.manifest_path)
    query_detector = DirectQueryRiskDetector(
        scorer_config,
        client,
        attack_config.generation_model,
        library,
    )
    session_detector = DirectSessionRiskDetector(
        scorer_config,
        client,
        attack_config.generation_model,
        library,
    )
    gateway = TwoStageGateway(
        gateway_config,
        query_detector=query_detector,
        session_detector=session_detector,
    )
    guard = GuardedRAG(store, gateway, attack_config.top_k)

    scenarios: list[dict[str, Any]] = []
    selected_doc_ids: dict[str, list[str]] = {}
    for attack_index, attack in enumerate(QUERY_ATTACKS):
        start = attack_index * samples_per_type
        attack_ids = member_doc_ids[start : start + samples_per_type]
        selected_doc_ids[attack] = attack_ids
        for doc_id in attack_ids:
            row = _attack_row(root, source_run_id, dataset_id, attack, doc_id)
            query = paraphrase_attack_query(
                attack,
                row,
                str(documents[doc_id]["text"]),
            )
            scenarios.append(
                _scenario(
                    session_id=f"direct-observe:attack:{attack}:{doc_id}",
                    traffic_type="attack",
                    attack_type=attack,
                    comparison_type=attack,
                    target_doc_id=doc_id,
                    queries=[query],
                )
            )

    ia_start = 3 * samples_per_type
    ia_attack_ids = member_doc_ids[ia_start : ia_start + samples_per_type]
    selected_doc_ids["ia"] = ia_attack_ids
    for doc_id in ia_attack_ids:
        summary, questions = _generate_questions(
            str(documents[doc_id]["text"]),
            ia_turn_count,
            client,
            attack_config.generation_model,
            max(256, attack_config.ia_generation_max_tokens),
        )
        if len(questions) != ia_turn_count:
            raise RuntimeError("IA generation returned too few questions")
        scenarios.append(
            _scenario(
                session_id=f"direct-observe:attack:ia:{doc_id}",
                traffic_type="attack",
                attack_type="ia",
                comparison_type="ia",
                target_doc_id=doc_id,
                queries=[
                    f"Regarding {summary}, {question} Respond yes, no, or unknown."
                    for question in questions
                ],
            )
        )

    benign_start = 4 * samples_per_type
    for comparison_index, comparison_type in enumerate(QUERY_ATTACKS):
        start = benign_start + comparison_index * samples_per_type
        benign_ids = member_doc_ids[start : start + samples_per_type]
        selected_doc_ids[f"benign_{comparison_type}"] = benign_ids
        benign_pattern_index = comparison_index
        for doc_id in benign_ids:
            query, _ = hard_benign_query(
                str(documents[doc_id]["text"]), benign_pattern_index
            )
            scenarios.append(
                _scenario(
                    session_id=f"direct-observe:benign:{comparison_type}:{doc_id}",
                    traffic_type="benign",
                    attack_type="benign",
                    comparison_type=comparison_type,
                    target_doc_id=doc_id,
                    queries=[query],
                )
            )

    ia_benign_start = 7 * samples_per_type
    ia_benign_ids = member_doc_ids[ia_benign_start : ia_benign_start + samples_per_type]
    selected_doc_ids["benign_ia"] = ia_benign_ids
    for doc_id in ia_benign_ids:
        scenarios.append(
            _scenario(
                session_id=f"direct-observe:benign:ia:{doc_id}",
                traffic_type="benign",
                attack_type="benign",
                comparison_type="ia",
                target_doc_id=doc_id,
                queries=benign_session_queries(
                    str(documents[doc_id]["text"]), ia_turn_count
                ),
            )
        )

    online_events: list[dict[str, Any]] = []
    evaluation_records: list[dict[str, Any]] = []
    for scenario in scenarios:
        for turn_id, query in enumerate(scenario["queries"], start=1):
            prepared = guard.prepare(str(query), str(scenario["session_id"]))
            event_id = f"{scenario['session_id']}:{turn_id}"
            online_events.append(
                build_two_stage_risk_event(
                    event_id=event_id,
                    session_id=str(scenario["session_id"]),
                    turn_id=turn_id,
                    query_text=str(query),
                    retrieved_doc_ids=prepared.retrieved_doc_ids,
                    retrieval_scores=prepared.retrieval_scores,
                    decision=prepared.decision,
                )
            )
            assessment = prepared.decision.two_stage_assessment
            if assessment is None:
                raise RuntimeError("Two-stage decision has no structured assessment")
            evaluation_records.append(
                {
                    "event_id": event_id,
                    "session_id": scenario["session_id"],
                    "turn_id": turn_id,
                    "ground_truth": {
                        "traffic_type": scenario["traffic_type"],
                        "attack_type": scenario["attack_type"],
                        "comparison_type": scenario["comparison_type"],
                        "target_doc_id": scenario["target_doc_id"],
                    },
                    "query_risk_score": assessment["query_detection"]["risk_score"],
                    "query_risk_class": assessment["query_detection"]["risk_class"],
                    "query_status": assessment["query_detection"]["status"],
                    "session_risk_score": assessment["session_detection"]["risk_score"],
                    "session_risk_class": assessment["session_detection"]["risk_class"],
                    "session_status": assessment["session_detection"]["status"],
                    "total_risk_score": assessment["aggregation"]["total_risk_score"],
                    "recommended_level": assessment["access_control"]["recommended_level"],
                    "applied_level": assessment["access_control"]["applied_level"],
                    "query_latency_ms": assessment["latency_ms"]["query_detector"],
                    "session_latency_ms": assessment["latency_ms"]["session_detector"],
                    "total_defense_latency_ms": prepared.decision_latency_ms,
                    "predicted_attack_type": prepared.decision.predicted_attack_type,
                }
            )

    labels = [
        1 if row["ground_truth"]["traffic_type"] == "attack" else 0
        for row in evaluation_records
    ]
    weak_threshold = scorer_config.weak_threshold
    query_all_turns_metrics = binary_detection_metrics(
        labels,
        [float(row["query_risk_score"]) for row in evaluation_records],
        weak_threshold,
    )
    explicit_query_rows = [
        row
        for row in evaluation_records
        if row["ground_truth"]["comparison_type"] in QUERY_ATTACKS
    ]
    query_metrics = binary_detection_metrics(
        [
            1 if row["ground_truth"]["traffic_type"] == "attack" else 0
            for row in explicit_query_rows
        ],
        [float(row["query_risk_score"]) for row in explicit_query_rows],
        weak_threshold,
    )
    combined_metrics = binary_detection_metrics(
        labels,
        [float(row["total_risk_score"]) for row in evaluation_records],
        gateway_config.level_thresholds[1],
    )
    ia_final_rows = [
        row
        for row in evaluation_records
        if row["ground_truth"]["comparison_type"] == "ia"
        and int(row["turn_id"]) == ia_turn_count
    ]
    session_metrics = binary_detection_metrics(
        [
            1 if row["ground_truth"]["traffic_type"] == "attack" else 0
            for row in ia_final_rows
        ],
        [float(row["session_risk_score"]) for row in ia_final_rows],
        weak_threshold,
    )
    detection_by_type: dict[str, dict[str, float]] = {}
    for attack in (*QUERY_ATTACKS, "ia"):
        attack_rows = [
            row
            for row in evaluation_records
            if row["ground_truth"]["attack_type"] == attack
        ]
        detection_by_type[attack] = {
            "query_detection_rate": float(
                np.mean(
                    [float(row["query_risk_score"]) >= weak_threshold for row in attack_rows]
                )
            ),
            "combined_detection_rate": float(
                np.mean(
                    [
                        float(row["total_risk_score"])
                        >= gateway_config.level_thresholds[1]
                        for row in attack_rows
                    ]
                )
            ),
        }

    ia_attack_rows = [
        row
        for row in evaluation_records
        if row["ground_truth"]["attack_type"] == "ia"
    ]
    first_detection_turns = [
        int(row["turn_id"])
        for row in ia_attack_rows
        if float(row["session_risk_score"]) >= weak_threshold
    ]
    session_latencies = [
        float(row["session_latency_ms"])
        for row in evaluation_records
        if row["session_status"] != "insufficient_history"
    ]
    metrics = {
        "scope": f"two_stage_llm_direct_{partition}_smoke",
        "query_detection_explicit_attacks": query_metrics,
        "query_detection_all_attack_generated_turns": query_all_turns_metrics,
        "session_detection_ia_final_turn": session_metrics,
        "combined_detection": combined_metrics,
        "attack_detection_rate_by_type": detection_by_type,
        "ia_average_first_session_detection_turn": (
            float(np.mean(first_detection_turns)) if first_detection_turns else None
        ),
        "latency": {
            "query_detector": _latency_summary(
                [float(row["query_latency_ms"]) for row in evaluation_records]
            ),
            "active_session_detector": _latency_summary(session_latencies),
            "total_defense": _latency_summary(
                [float(row["total_defense_latency_ms"]) for row in evaluation_records]
            ),
        },
        "recommended_level_counts": dict(
            sorted(Counter(str(row["recommended_level"]) for row in evaluation_records).items())
        ),
        "applied_level_counts": dict(
            sorted(Counter(str(row["applied_level"]) for row in evaluation_records).items())
        ),
        "observe_applied_l0_rate": float(
            np.mean([row["applied_level"] == "L0" for row in evaluation_records])
        ),
        "invalid_output_count": sum(
            row["query_status"] == "fallback_invalid_output"
            or row["session_status"] == "fallback_invalid_output"
            for row in evaluation_records
        ),
    }
    manifest = {
        "status": "completed",
        "completed_at": utc_now_iso(),
        "output_run_id": output_run_id,
        "source_run_id": source_run_id,
        "dataset_id": dataset_id,
        "split_id": split_manifest["split_id"],
        "partition": partition,
        "samples_per_type": samples_per_type,
        "ia_turn_count": ia_turn_count,
        "selected_doc_ids": selected_doc_ids,
        "mode": gateway_config.mode,
        "generation_model": attack_config.generation_model,
        "generation_backend": attack_config.generation_backend,
        "generation_load_mode": attack_config.generation_load_mode,
        "embedding_model": attack_config.embedding_model,
        "pattern_library_version": library.version,
        "query_detector_input_fields": list(query_detector.detector_input_fields()),
        "session_detector_input_fields": list(session_detector.detector_input_fields()),
        "ground_truth_storage": "evaluation_records.jsonl only; never passed to detectors",
    }
    summary = {
        "status": "completed",
        "output_path": str(output),
        "event_count": len(evaluation_records),
        "query_f1": query_metrics["f1"],
        "query_benign_false_positive_rate": query_metrics["false_positive_rate"],
        "ia_final_session_detection_rate": session_metrics["recall"],
        "ia_final_benign_false_positive_rate": session_metrics["false_positive_rate"],
        "combined_f1": combined_metrics["f1"],
        "observe_applied_l0_rate": metrics["observe_applied_l0_rate"],
        "invalid_output_count": metrics["invalid_output_count"],
    }
    output.mkdir(parents=True, exist_ok=False)
    write_jsonl_atomic(output / "risk_events.jsonl", online_events)
    write_jsonl_atomic(output / "evaluation_records.jsonl", evaluation_records)
    write_json_atomic(output / "detector_metrics.json", metrics)
    write_json_atomic(output / "run_manifest.json", manifest)
    write_json_atomic(output / "summary.json", summary)
    return summary


__all__ = ["binary_detection_metrics", "run_two_stage_direct_experiment"]
