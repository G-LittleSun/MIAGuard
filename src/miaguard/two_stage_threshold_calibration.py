from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
from rag_mia_data.io_utils import utc_now_iso, write_json_atomic, write_jsonl_atomic

from .attack_pattern_library import AttackPatternLibrary
from .config import AttackConfig
from .data import load_run_documents, vector_store_path
from .defense import GuardedRAG
from .defense_experiment import ATTACKS, _attack_rows, _benign_documents
from .direct_scorer import (
    DirectQueryRiskDetector,
    DirectScorerConfig,
    DirectSessionRiskDetector,
)
from .model_client import create_model_client
from .two_stage_gateway import TwoStageConfig, TwoStageGateway
from .vector_store import UnifiedVectorStore


def interleave_balanced_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    members = [row for row in rows if int(row["membership_label"]) == 1]
    nonmembers = [row for row in rows if int(row["membership_label"]) == 0]
    if len(members) != len(nonmembers) or not members:
        raise ValueError("Continuous-session rows must be balanced and non-empty")
    return [row for pair in zip(members, nonmembers) for row in pair]


def select_balanced_detection_threshold(
    records: list[dict[str, Any]],
    *,
    max_benign_fpr: float = 0.05,
) -> dict[str, Any]:
    if not 0 <= max_benign_fpr < 1:
        raise ValueError("max_benign_fpr must be in [0, 1)")
    attacks = [row for row in records if row["traffic_type"] == "attack"]
    benign = [row for row in records if row["traffic_type"] == "benign"]
    if not attacks or not benign:
        raise ValueError("Threshold calibration requires attack and benign records")
    present = {str(row["attack_type"]) for row in attacks}
    if present != set(ATTACKS):
        raise ValueError("Threshold calibration requires all four attack types")

    scores = np.asarray([float(row["total_risk_score"]) for row in records])
    positive = sorted({float(value) for value in scores if float(value) > 0.0})
    candidates = positive + [float(np.nextafter(np.max(scores), np.inf))]
    if not candidates:
        candidates = [float(np.nextafter(0.0, 1.0))]

    results: list[dict[str, Any]] = []
    for threshold in candidates:
        rates: dict[str, float] = {}
        counts: dict[str, int] = {}
        for attack in ATTACKS:
            selected = [row for row in attacks if row["attack_type"] == attack]
            detected = sum(
                float(row["total_risk_score"]) >= threshold for row in selected
            )
            counts[attack] = detected
            rates[attack] = detected / len(selected)
        benign_detected = sum(
            float(row["total_risk_score"]) >= threshold for row in benign
        )
        benign_fpr = benign_detected / len(benign)
        results.append(
            {
                "threshold": threshold,
                "min_attack_detection_rate": min(rates.values()),
                "macro_attack_detection_rate": sum(rates.values()) / len(rates),
                "attack_detection_rates": rates,
                "attack_detected_counts": counts,
                "benign_false_positive_rate": benign_fpr,
                "benign_detected_count": benign_detected,
                "feasible": benign_fpr <= max_benign_fpr,
            }
        )
    feasible = [row for row in results if row["feasible"]]
    if not feasible:
        raise RuntimeError("No candidate threshold satisfies the benign FPR constraint")
    selected = max(
        feasible,
        key=lambda row: (
            row["min_attack_detection_rate"],
            row["macro_attack_detection_rate"],
            -row["benign_false_positive_rate"],
            row["threshold"],
        ),
    )
    ranked = sorted(
        results,
        key=lambda row: (
            row["feasible"],
            row["min_attack_detection_rate"],
            row["macro_attack_detection_rate"],
            -row["benign_false_positive_rate"],
            row["threshold"],
        ),
        reverse=True,
    )
    return {
        "selected_threshold": selected["threshold"],
        "selection_objective": (
            "maximize minimum per-attack detection rate, then macro detection rate, "
            "subject to benign false-positive-rate constraint"
        ),
        "max_benign_false_positive_rate": max_benign_fpr,
        "selected_metrics": selected,
        "candidate_count": len(results),
        "top_candidates": ranked[:20],
    }


def _queries(attack: str, row: dict[str, Any]) -> list[str]:
    if attack in {"direct_rag_mia", "s2_mia"}:
        return [str(row["attack_query"])]
    if attack == "masked_mia":
        return [str(row["masked_text"])]
    if attack == "ia":
        return [str(value["adversarial_query"]) for value in row["queries"]]
    raise ValueError(f"Unsupported attack: {attack}")


def _record(
    *,
    traffic_type: str,
    attack_type: str,
    membership_label: int | None,
    doc_id: str,
    session_id: str,
    session_turn: int,
    query: str,
    prepared: Any,
) -> dict[str, Any]:
    assessment = prepared.decision.two_stage_assessment
    if assessment is None:
        raise RuntimeError("Two-stage decision has no structured assessment")
    return {
        "traffic_type": traffic_type,
        "attack_type": attack_type,
        "membership_label": membership_label,
        "doc_id": doc_id,
        "session_id": session_id,
        "session_turn": session_turn,
        "query": query,
        "query_risk_score": float(assessment["query_detection"]["risk_score"]),
        "query_risk_class": assessment["query_detection"]["risk_class"],
        "query_status": assessment["query_detection"]["status"],
        "session_risk_score": float(assessment["session_detection"]["risk_score"]),
        "session_risk_class": assessment["session_detection"]["risk_class"],
        "session_status": assessment["session_detection"]["status"],
        "window_coverage": float(assessment["aggregation"]["window_coverage"]),
        "total_risk_score": float(assessment["aggregation"]["total_risk_score"]),
        "recommended_level": assessment["access_control"]["recommended_level"],
        "retrieved_doc_ids": prepared.retrieved_doc_ids,
        "retrieval_scores": prepared.retrieval_scores,
        "query_latency_ms": float(assessment["latency_ms"]["query_detector"]),
        "session_latency_ms": float(assessment["latency_ms"]["session_detector"]),
    }


def _score_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for traffic_type in (*ATTACKS, "benign"):
        selected = [
            row
            for row in records
            if (
                row["attack_type"] == traffic_type
                if traffic_type != "benign"
                else row["traffic_type"] == "benign"
            )
        ]
        result[traffic_type] = {
            "sample_count": len(selected),
            "query_score_mean": float(
                np.mean([row["query_risk_score"] for row in selected])
            ),
            "session_score_mean": float(
                np.mean([row["session_risk_score"] for row in selected])
            ),
            "total_score_mean": float(
                np.mean([row["total_risk_score"] for row in selected])
            ),
            "active_session_count": sum(
                row["session_status"] != "insufficient_history" for row in selected
            ),
            "session_status_counts": dict(
                sorted(Counter(row["session_status"] for row in selected).items())
            ),
        }
    return result


def run_two_stage_threshold_calibration(
    project_root: Path,
    source_run_id: str,
    dataset_id: str,
    output_run_id: str,
    attack_config: AttackConfig,
    gateway_config: TwoStageConfig,
    scorer_config: DirectScorerConfig,
    *,
    limit_per_class: int = 10,
    benign_count: int = 20,
    offset_per_class: int = 0,
    max_benign_fpr: float = 0.05,
) -> dict[str, Any]:
    if gateway_config.mode != "observe":
        raise ValueError("Threshold calibration requires observe mode")
    root = project_root.resolve()
    output = root / "data" / "two_stage_calibration" / output_run_id / dataset_id
    if output.exists():
        raise FileExistsError(f"Calibration output already exists: {output}")

    client = create_model_client(attack_config, root)
    client.validate_models()
    store = UnifiedVectorStore.load(
        vector_store_path(root, source_run_id, dataset_id), client
    )
    library = AttackPatternLibrary.load(scorer_config.manifest_path)
    gateway = TwoStageGateway(
        gateway_config,
        query_detector=DirectQueryRiskDetector(
            scorer_config, client, attack_config.generation_model, library
        ),
        session_detector=DirectSessionRiskDetector(
            scorer_config, client, attack_config.generation_model, library
        ),
    )
    guard = GuardedRAG(store, gateway, attack_config.top_k)
    records: list[dict[str, Any]] = []

    for attack in ATTACKS:
        rows = interleave_balanced_rows(
            _attack_rows(
                root,
                source_run_id,
                dataset_id,
                attack,
                limit_per_class,
                offset_per_class,
            )
        )
        session_id = f"{output_run_id}:{dataset_id}:train:{attack}:continuous"
        turn = 0
        print(
            f"[calibration] attack={attack} documents={len(rows)} started",
            flush=True,
        )
        for row in rows:
            for query in _queries(attack, row):
                turn += 1
                prepared = guard.prepare(query, session_id)
                records.append(
                    _record(
                        traffic_type="attack",
                        attack_type=attack,
                        membership_label=int(row["membership_label"]),
                        doc_id=str(row["doc_id"]),
                        session_id=session_id,
                        session_turn=turn,
                        query=query,
                        prepared=prepared,
                    )
                )
        print(f"[calibration] attack={attack} completed", flush=True)

    documents = interleave_balanced_rows(
        _benign_documents(
            load_run_documents(root, source_run_id, dataset_id),
            benign_count,
            offset_per_class,
        )
    )
    benign_session_id = f"{output_run_id}:{dataset_id}:train:benign:continuous"
    print(f"[calibration] benign documents={len(documents)} started", flush=True)
    for turn, document in enumerate(documents, start=1):
        prefix = " ".join(str(document["text"]).split()[:12])
        query = f'What is the main topic of this news excerpt: "{prefix}"?'
        prepared = guard.prepare(query, benign_session_id)
        records.append(
            _record(
                traffic_type="benign",
                attack_type="benign",
                membership_label=int(document["membership_label"]),
                doc_id=str(document["doc_id"]),
                session_id=benign_session_id,
                session_turn=turn,
                query=query,
                prepared=prepared,
            )
        )
    print("[calibration] benign completed", flush=True)

    calibration = select_balanced_detection_threshold(
        records,
        max_benign_fpr=max_benign_fpr,
    )
    score_summary = _score_summary(records)
    manifest = {
        "status": "completed",
        "completed_at": utc_now_iso(),
        "output_run_id": output_run_id,
        "source_run_id": source_run_id,
        "dataset_id": dataset_id,
        "data_scope": "development_internal_training",
        "limit_per_class": limit_per_class,
        "benign_count": benign_count,
        "offset_per_class": offset_per_class,
        "continuous_session_unit": "one session per attack type; member and nonmember rows deterministically interleaved",
        "generation_model": attack_config.generation_model,
        "generation_load_mode": attack_config.generation_load_mode,
        "pattern_library_version": library.version,
        "llm_scores_modified": False,
        "ground_truth_passed_to_detectors": False,
    }
    summary = {
        "status": "completed",
        "output_path": str(output),
        "selected_threshold": calibration["selected_threshold"],
        "selected_metrics": calibration["selected_metrics"],
    }
    output.mkdir(parents=True, exist_ok=False)
    write_jsonl_atomic(output / "risk_records.jsonl", records)
    write_json_atomic(output / "threshold_calibration.json", calibration)
    write_json_atomic(output / "score_summary.json", score_summary)
    write_json_atomic(output / "run_manifest.json", manifest)
    write_json_atomic(output / "summary.json", summary)
    return summary


__all__ = [
    "interleave_balanced_rows",
    "run_two_stage_threshold_calibration",
    "select_balanced_detection_threshold",
]
