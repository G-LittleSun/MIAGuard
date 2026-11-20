from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import replace
from pathlib import Path
from typing import Any, Mapping, Sequence

from miaguard.attack_pattern_library import AttackPatternLibrary
from miaguard.config import AttackConfig
from miaguard.data import load_run_documents, vector_store_path
from miaguard.defense import GuardedRAG, evaluate_defense_decisions
from miaguard.defense_experiment import (
    _baseline_metrics,
    _event,
    _normalize_answer,
    _record,
    _recover_masks,
    _response_contexts,
    _run_benign_queries,
    _threshold,
    _threshold_source,
)
from miaguard.direct_scorer import (
    DirectQueryRiskDetector,
    DirectScorerConfig,
    DirectSessionRiskDetector,
)
from miaguard.model_client import create_model_client
from miaguard.query_bank.schema import document_sha256
from miaguard.two_stage_attack_comparison import _run_attack
from miaguard.two_stage_gateway import TwoStageConfig, TwoStageGateway
from miaguard.vector_store import UnifiedVectorStore
from miaguard.supervised_threshold import evaluate_locked_attack_threshold
from rag_mia_data.io_utils import write_json_atomic, write_jsonl_atomic

from .sessions import PlannedSession, plan_partition_sessions
from .storage import QueryBank, QueryBankPaths
from .threshold_scoring import scoring_identity
from .threshold_split import load_threshold_split


def adapt_planned_session(session: PlannedSession) -> list[dict[str, Any]]:
    common = {
        "doc_id": session.doc_id,
        "membership_label": session.membership_label,
        "planned_session_key": session.session_key,
    }
    if session.attack_type == "ia":
        queries = [
            {
                "query_id": str(query["query_id"]),
                "adversarial_query": str(query["query_text"]),
                "ground_truth": str(query["payload"]["ground_truth"]),
                "question": str(query["payload"].get("question", "")),
            }
            for query in session.queries
        ]
        return [
            {
                **common,
                "query_id": queries[0]["query_id"],
                "summary": str(session.queries[0]["payload"].get("summary", "")),
                "queries": queries,
            }
        ]

    rows: list[dict[str, Any]] = []
    for query in session.queries:
        payload = query.get("payload", {})
        row = {
            **common,
            "query_id": str(query["query_id"]),
        }
        if session.attack_type == "benign":
            row.update(
                query_text=str(query["query_text"]),
                category=str(payload.get("category", "benign")),
            )
        elif session.attack_type in {"direct_rag_mia", "s2_mia"}:
            row["attack_query"] = str(query["query_text"])
            if "prefix" in payload:
                row["prefix"] = str(payload["prefix"])
        elif session.attack_type == "masked_mia":
            row["attack_query"] = str(query["query_text"])
            row["masked_text"] = str(payload["masked_text"])
            row["answers"] = [str(value) for value in payload["answers"]]
        else:
            raise ValueError(f"Unsupported planned attack type: {session.attack_type}")
        rows.append(row)
    return rows


def build_condition_configs(
    base_config: TwoStageConfig,
    *,
    learned_threshold: float,
) -> dict[str, TwoStageConfig]:
    if not 0.0 <= learned_threshold <= 1.0:
        raise ValueError("learned_threshold must be in [0, 1]")
    return {
        "disabled": replace(
            base_config,
            mode="disabled",
            attack_detection_threshold=None,
        ),
        "fixed_0_10": replace(
            base_config,
            mode="enforce",
            attack_detection_threshold=0.10,
        ),
        "learned": replace(
            base_config,
            mode="enforce",
            attack_detection_threshold=learned_threshold,
        ),
    }


def _identity_core(value: Mapping[str, Any]) -> dict[str, Any]:
    return {str(key): item for key, item in value.items() if key != "partition"}


def _annotate(
    rows: list[dict[str, Any]],
    session: PlannedSession,
    condition: str,
) -> None:
    for turn_index, row in enumerate(rows, start=1):
        row["event_id"] = f"{condition}:{session.session_key}:{turn_index:03d}"
        row["session_id"] = session.session_key
        row["turn_id"] = turn_index
        row["planned_session_key"] = session.session_key
        row["condition"] = condition


def document_average_scores(
    rows: Sequence[dict[str, Any]],
) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["doc_id"])].append(row)
    result = []
    for doc_id, values in sorted(grouped.items()):
        labels = {int(value["membership_label"]) for value in values}
        if len(labels) != 1:
            raise ValueError(f"Membership label changed within document {doc_id}")
        total_weight = sum(int(value.get("query_count", 1)) for value in values)
        result.append(
            {
                "doc_id": doc_id,
                "membership_label": labels.pop(),
                "membership_score": sum(
                    float(value["membership_score"])
                    * int(value.get("query_count", 1))
                    for value in values
                )
                / total_weight,
            }
        )
    return result


def _replay_frozen_masked(
    rows: list[dict[str, Any]],
    guard: GuardedRAG,
    client: Any,
    config: AttackConfig,
    source_run_id: str,
    dataset_id: str,
    session_id: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    events: list[dict[str, Any]] = []
    decisions: list[dict[str, Any]] = []
    scores: list[dict[str, Any]] = []
    for row in rows:
        query = str(row["attack_query"])
        masked_text = str(row["masked_text"])
        answers = [str(value) for value in row["answers"]]
        event = _event(
            source_run_id=source_run_id,
            dataset_id=dataset_id,
            attack="masked_mia",
            doc_id=str(row["doc_id"]),
            membership_label=int(row["membership_label"]),
            query=query,
            metadata={
                "query_id": str(row["query_id"]),
                "expected_mask_count": len(answers),
            },
            session_id_override=session_id,
        )
        # Retrieval and both risk stages see the exact frozen query_text used
        # during train/validation/test observe scoring.
        prepared = guard.prepare(query, session_id)
        if prepared.decision.access_action == "deny_sensitive_answer":
            recovered = [""] * len(answers)
        else:
            contexts = _response_contexts(prepared, client, config)
            recovered = _recover_masks(
                masked_text,
                len(answers),
                contexts,
                client,
                config.generation_model,
                config.masked_max_tokens,
            )
        score = sum(
            _normalize_answer(expected) == _normalize_answer(predicted)
            for expected, predicted in zip(answers, recovered)
        ) / len(answers)
        events.append(event)
        decisions.append(_record(event, prepared, recovered, score))
        scores.append(
            {
                "doc_id": str(row["doc_id"]),
                "membership_label": int(row["membership_label"]),
                "membership_score": score,
            }
        )
    return events, decisions, scores


def _formal_detection_records(
    decisions: Sequence[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [
        {
            "query_id": str(row["event_id"]),
            "doc_id": str(row["target_doc_id"]),
            "traffic_type": "attack" if int(row["intent_label"]) == 1 else "benign",
            "attack_type": str(row["attack_type"]),
            "session_key": str(row["session_id"]),
            "turn_index": int(row["turn_id"]),
            "total_risk_score": float(row["total_risk"]),
        }
        for row in decisions
    ]


def run_formal_threshold_test_comparison(
    project_root: Path,
    source_run_id: str,
    query_bank_id: str,
    dataset_id: str,
    split_path: Path,
    validation_result_path: Path,
    output_run_id: str,
    attack_config: AttackConfig,
    base_gateway_config: TwoStageConfig,
    scorer_config: DirectScorerConfig,
    *,
    bootstrap_replicates: int = 2000,
) -> dict[str, Any]:
    if base_gateway_config.mode != "observe":
        raise ValueError("Formal comparison base gateway must be the observe config")
    validation = json.loads(validation_result_path.read_text(encoding="utf-8"))
    if not isinstance(validation, dict) or validation.get("status") != "passed":
        raise ValueError("Formal test comparison requires passed validation")
    learned_threshold = float(validation["threshold"])
    validation_identity = validation.get("source_identity")
    if not isinstance(validation_identity, Mapping):
        raise ValueError("Validation result has no scoring identity")

    root = project_root.resolve()
    output = (
        root
        / "data"
        / "two_stage_threshold_formal_results"
        / output_run_id
        / dataset_id
    )
    if output.exists():
        raise FileExistsError(f"Formal comparison output already exists: {output}")
    bank = QueryBank.load(QueryBankPaths(root, query_bank_id, dataset_id))
    split = load_threshold_split(split_path, bank)
    sessions = plan_partition_sessions(bank, split, "test", target_turns=5)

    document_rows = load_run_documents(root, source_run_id, dataset_id)
    documents = {str(row["doc_id"]): row for row in document_rows}
    for document in bank.documents:
        doc_id = str(document["doc_id"])
        if doc_id not in documents:
            raise ValueError(f"Query Bank document missing from source run: {doc_id}")
        if document_sha256(str(documents[doc_id]["text"])) != str(
            document["source_document_sha256"]
        ):
            raise ValueError(f"Source document hash changed: {doc_id}")

    client = create_model_client(attack_config, root)
    client.validate_models()
    store = UnifiedVectorStore.load(
        vector_store_path(root, source_run_id, dataset_id), client
    )
    library = AttackPatternLibrary.load(scorer_config.manifest_path)
    expected_identity = scoring_identity(
        bank,
        split,
        "validation",
        base_gateway_config,
        scorer_config,
        library.version,
        source_run_id=source_run_id,
        attack_config=attack_config,
        target_turns=5,
    )
    if _identity_core(validation_identity) != _identity_core(expected_identity):
        raise ValueError("Formal comparison inputs do not match validation identity")

    output.mkdir(parents=True, exist_ok=False)
    condition_summaries: dict[str, Any] = {}
    for condition, config in build_condition_configs(
        base_gateway_config,
        learned_threshold=learned_threshold,
    ).items():
        if condition == "disabled":
            gateway = TwoStageGateway(config)
        else:
            gateway = TwoStageGateway(
                config,
                query_detector=DirectQueryRiskDetector(
                    scorer_config,
                    client,
                    attack_config.generation_model,
                    library,
                ),
                session_detector=DirectSessionRiskDetector(
                    scorer_config,
                    client,
                    attack_config.generation_model,
                    library,
                ),
            )
        guard = GuardedRAG(store, gateway, attack_config.top_k)
        events: list[dict[str, Any]] = []
        decisions: list[dict[str, Any]] = []
        scores_by_attack: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for session in sessions:
            adapted = adapt_planned_session(session)
            try:
                if session.attack_type == "benign":
                    session_events, session_decisions = _run_benign_queries(
                        adapted,
                        guard,
                        client,
                        attack_config,
                        source_run_id,
                        dataset_id,
                        session.session_key,
                    )
                else:
                    if session.attack_type == "masked_mia":
                        session_events, session_decisions, session_scores = (
                            _replay_frozen_masked(
                                adapted,
                                guard,
                                client,
                                attack_config,
                                source_run_id,
                                dataset_id,
                                session.session_key,
                            )
                        )
                    else:
                        session_events, session_decisions, session_scores = _run_attack(
                            session.attack_type,
                            adapted,
                            documents,
                            guard,
                            client,
                            attack_config,
                            source_run_id,
                            dataset_id,
                            session.session_key,
                        )
                    if session.attack_type == "ia":
                        for value in session_scores:
                            value["query_count"] = len(session.queries)
                    scores_by_attack[session.attack_type].extend(session_scores)
                _annotate(session_events, session, condition)
                _annotate(session_decisions, session, condition)
                events.extend(session_events)
                decisions.extend(session_decisions)
            finally:
                gateway.clear_session(session.session_key)

        attack_metrics = {
            attack: _baseline_metrics(
                document_average_scores(scores_by_attack[attack]),
                _threshold(attack_config, attack),
                _threshold_source(attack_config, attack),
            )
            for attack in ("direct_rag_mia", "s2_mia", "masked_mia", "ia")
        }
        detector_metrics = evaluate_defense_decisions(decisions)
        detection_threshold = (
            1.0
            if condition == "disabled"
            else float(config.attack_detection_threshold)
        )
        formal_detection_metrics = evaluate_locked_attack_threshold(
            _formal_detection_records(decisions),
            detection_threshold,
            bootstrap_replicates=bootstrap_replicates,
        )
        condition_root = output / condition
        write_jsonl_atomic(condition_root / "events.jsonl", events)
        write_jsonl_atomic(condition_root / "decisions.jsonl", decisions)
        write_json_atomic(condition_root / "attack_metrics.json", attack_metrics)
        write_json_atomic(condition_root / "detector_metrics.json", detector_metrics)
        write_json_atomic(
            condition_root / "session_detection_metrics.json",
            formal_detection_metrics,
        )
        condition_summaries[condition] = {
            "mode": config.mode,
            "attack_detection_threshold": config.attack_detection_threshold,
            "event_count": len(events),
            "session_count": len(sessions),
            "macro_attack_accuracy": sum(
                value["accuracy"] for value in attack_metrics.values()
            )
            / len(attack_metrics),
            "benign_false_positive_rate": detector_metrics[
                "benign_false_positive_rate"
            ],
            "minimum_attack_document_balanced_query_recall": (
                formal_detection_metrics["minimum_attack_recall"]
            ),
            "attack_document_balanced_session_recall": (
                formal_detection_metrics[
                    "attack_document_balanced_session_recall"
                ]
            ),
        }

    summary = {
        "status": "completed",
        "output_run_id": output_run_id,
        "dataset_id": dataset_id,
        "split_id": split["split_id"],
        "partition": "test",
        "query_bank_sha256": bank.sha256,
        "query_count_per_condition": sum(len(session.queries) for session in sessions),
        "session_count_per_condition": len(sessions),
        "condition_order": ["disabled", "fixed_0_10", "learned"],
        "conditions": condition_summaries,
        "comparison_control": (
            "All conditions use the same frozen test sessions, order, source run, "
            "vector store, model client, scorer, and severity thresholds."
        ),
    }
    write_json_atomic(output / "summary.json", summary)
    return summary


__all__ = [
    "adapt_planned_session",
    "build_condition_configs",
    "document_average_scores",
    "run_formal_threshold_test_comparison",
]
