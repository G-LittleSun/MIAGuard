from __future__ import annotations

from pathlib import Path
from typing import Any

from rag_mia_data.io_utils import (
    read_jsonl,
    utc_now_iso,
    write_json_atomic,
    write_jsonl_atomic,
)

from .config import AttackConfig
from .data import attack_result_path, load_run_documents, vector_store_path
from .defense import (
    DefenseConfig,
    GuardedRAG,
    PreparedRAGRequest,
    RuleDefense,
    build_query_event,
    evaluate_defense_decisions,
)
from .direct_rag_mia import direct_membership_score
from .evidence_access import SUMMARY_TEMPLATE_VERSION
from .masked_mia import _normalize_answer, _recover_masks
from .metrics import evaluate_scores, extract_yes_no_unknown
from .model_client import ModelClient, create_model_client
from .s2_mia import semantic_similarity_score
from .vector_store import UnifiedVectorStore


SAFE_RESPONSE = (
    "I cannot confirm whether specific content is present in the retrieval database "
    "or reproduce protected source text. I can provide a general explanation instead."
)
UNAVAILABLE_RESPONSE = "The request could not be processed right now. Please retry later."
ATTACKS = ("direct_rag_mia", "s2_mia", "masked_mia", "ia")


def select_balanced_rows(
    rows: list[dict[str, Any]],
    limit_per_class: int,
    *,
    offset_per_class: int = 0,
) -> list[dict[str, Any]]:
    if limit_per_class <= 0:
        raise ValueError("limit_per_class must be positive")
    if offset_per_class < 0:
        raise ValueError("offset_per_class must not be negative")
    members = [row for row in rows if int(row["membership_label"]) == 1]
    nonmembers = [row for row in rows if int(row["membership_label"]) == 0]
    end = offset_per_class + limit_per_class
    if len(members) < end or len(nonmembers) < end:
        raise ValueError("Baseline results do not contain enough rows in both classes")
    return members[offset_per_class:end] + nonmembers[offset_per_class:end]


def _threshold(config: AttackConfig, attack: str) -> float:
    return {
        "direct_rag_mia": config.direct_rag_mia_threshold,
        "s2_mia": config.s2_mia_threshold,
        "masked_mia": config.masked_threshold,
        "ia": config.ia_threshold,
    }[attack]


def _threshold_source(config: AttackConfig, attack: str) -> str:
    return {
        "direct_rag_mia": config.direct_rag_mia_threshold_source,
        "s2_mia": config.s2_mia_threshold_source,
        "masked_mia": config.masked_threshold_source,
        "ia": config.ia_threshold_source,
    }[attack]


def _context_prompt(contexts: list[str], query: str, instruction: str) -> str:
    context = "\n".join(f'"{text}"' for text in contexts)
    return f"""{instruction}

Context:
{context}

Question:
{query}
"""


def _response_contexts(
    prepared: PreparedRAGRequest,
    client: ModelClient,
    attack_config: AttackConfig,
) -> list[str]:
    """Return the contexts that the downstream RAG task is allowed to consume."""
    if prepared.decision.access_action != "summarize_context":
        return prepared.contexts
    source = "\n".join(prepared.contexts)
    summary = client.generate(
        attack_config.generation_model,
        (
            "Produce one short, high-level topic summary of the text below. "
            "Omit names, numbers, dates, quotations, and exact factual claims. "
            "Do not answer any user question. Return only the sanitized summary.\n\n"
            f"Text:\n{source}"
        ),
        max_tokens=48,
        temperature=0.0,
    )
    return [summary]


def summarize_for_defense_v1(
    items: tuple[Any, ...],
    client: ModelClient,
    attack_config: AttackConfig,
) -> str:
    """Apply the single versioned summary transform before answer generation."""
    source = "\n".join(str(item.text) for item in items)
    prompt = (
        f"Template: {SUMMARY_TEMPLATE_VERSION}\n"
        "Produce one short, high-level topic summary of the text below. "
        "Omit names, numbers, dates, quotations, and exact factual claims. "
        "Do not answer the user question. Return only the sanitized summary.\n\n"
        f"Text:\n{source}"
    )
    return client.generate(attack_config.generation_model, prompt, max_tokens=48, temperature=0.0)


def _text_response(
    prepared: PreparedRAGRequest,
    client: ModelClient,
    attack_config: AttackConfig,
    query: str,
    *,
    instruction: str,
    max_tokens: int,
) -> str:
    if prepared.decision.access_action in {"deny_sensitive_answer", "deny"}:
        return SAFE_RESPONSE
    if prepared.decision.access_action == "unavailable":
        return UNAVAILABLE_RESPONSE
    contexts = _response_contexts(prepared, client, attack_config)
    return client.generate(
        attack_config.generation_model,
        _context_prompt(contexts, query, instruction),
        max_tokens=max_tokens,
        temperature=0.0,
    )


def _record(
    event: dict[str, Any],
    prepared: PreparedRAGRequest,
    response: Any,
    defended_score: float | None,
) -> dict[str, Any]:
    event["retrieved_doc_ids"] = prepared.retrieved_doc_ids
    event["retrieval_scores"] = prepared.retrieval_scores
    recorded = {
        "event_id": event["event_id"],
        "session_id": event["session_id"],
        "turn_id": event["turn_id"],
        "attack_type": event["attack_type"],
        "intent_label": event["intent_label"],
        "membership_label": event["membership_label"],
        "target_doc_id": event["target_doc_id"],
        **prepared.decision.to_dict(),
        "retrieved_doc_ids": prepared.retrieved_doc_ids,
        "retrieval_scores": prepared.retrieval_scores,
        "decision_latency_ms": prepared.decision_latency_ms,
        "rag_response": response,
        "defended_score": defended_score,
    }
    if prepared.action_execution is not None:
        recorded["delivered_evidence"] = [
            {"doc_id": item.doc_id, "parent_doc_id": item.parent_doc_id,
             "kind": item.kind, "text": item.text, "score": item.score}
            for item in prepared.action_execution.evidence
        ]
        recorded["delivered_contexts"] = list(prepared.contexts)
    return recorded


def _event(
    *,
    source_run_id: str,
    dataset_id: str,
    attack: str,
    doc_id: str,
    membership_label: int,
    query: str,
    turn_id: int = 1,
    metadata: dict[str, Any],
    session_id_override: str | None = None,
) -> dict[str, Any]:
    suffix = f"{doc_id}:{turn_id}"
    return build_query_event(
        event_id=f"{attack}:{suffix}",
        source_record_id=f"{attack}:{suffix}",
        source_framework="miaguard_attack_baseline",
        run_id=source_run_id,
        dataset_id=dataset_id,
        session_id=(
            session_id_override
            or f"{source_run_id}:{dataset_id}:{attack}:{doc_id}"
        ),
        turn_id=turn_id,
        query=query,
        attack_type=attack,
        intent_label=1,
        membership_label=membership_label,
        target_doc_id=doc_id,
        attack_metadata=metadata,
    )


def _attack_rows(
    project_root: Path,
    source_run_id: str,
    dataset_id: str,
    attack: str,
    limit_per_class: int,
    offset_per_class: int,
) -> list[dict[str, Any]]:
    path = attack_result_path(project_root, source_run_id, dataset_id, attack) / "results.jsonl"
    if not path.exists():
        raise FileNotFoundError(f"Missing frozen baseline results: {path}")
    return select_balanced_rows(
        list(read_jsonl(path)),
        limit_per_class,
        offset_per_class=offset_per_class,
    )


def _baseline_metrics(
    rows: list[dict[str, Any]], threshold: float, threshold_source: str
) -> dict[str, Any]:
    return evaluate_scores(
        [int(row["membership_label"]) for row in rows],
        [float(row["membership_score"]) for row in rows],
        threshold,
        threshold_source,
    )


def _query_bank_metadata(row: dict[str, Any]) -> dict[str, Any]:
    metadata: dict[str, Any] = {}
    if row.get("query_id"):
        metadata["query_id"] = str(row["query_id"])
    if "membership_score" in row:
        metadata["baseline_membership_score"] = float(row["membership_score"])
    if "retrieved_doc_ids" in row:
        metadata["baseline_retrieved_doc_ids"] = list(
            row.get("retrieved_doc_ids", [])
        )
    return metadata


def _replay_direct(
    rows: list[dict[str, Any]],
    guard: GuardedRAG,
    client: ModelClient,
    config: AttackConfig,
    source_run_id: str,
    dataset_id: str,
    session_id_override: str | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    events: list[dict[str, Any]] = []
    decisions: list[dict[str, Any]] = []
    for row in rows:
        query = str(row["attack_query"])
        event = _event(
            source_run_id=source_run_id,
            dataset_id=dataset_id,
            attack="direct_rag_mia",
            doc_id=str(row["doc_id"]),
            membership_label=int(row["membership_label"]),
            query=query,
            metadata=_query_bank_metadata(row),
            session_id_override=session_id_override,
        )
        prepared = guard.prepare(query, str(event["session_id"]))
        response = _text_response(
            prepared,
            client,
            config,
            query,
            instruction="Please answer using only the supplied Context.",
            max_tokens=config.direct_rag_mia_max_tokens,
        )
        score = direct_membership_score(response)
        events.append(event)
        decisions.append(_record(event, prepared, response, score))
    return events, decisions


def _replay_s2(
    rows: list[dict[str, Any]],
    documents: dict[str, dict[str, Any]],
    guard: GuardedRAG,
    client: ModelClient,
    config: AttackConfig,
    source_run_id: str,
    dataset_id: str,
    session_id_override: str | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    events: list[dict[str, Any]] = []
    decisions: list[dict[str, Any]] = []
    for row in rows:
        doc_id = str(row["doc_id"])
        query = str(row["attack_query"])
        event = _event(
            source_run_id=source_run_id,
            dataset_id=dataset_id,
            attack="s2_mia",
            doc_id=doc_id,
            membership_label=int(row["membership_label"]),
            query=query,
            metadata=_query_bank_metadata(row),
            session_id_override=session_id_override,
        )
        prepared = guard.prepare(query, str(event["session_id"]))
        response = _text_response(
            prepared,
            client,
            config,
            query,
            instruction="Please answer using only the supplied Context.",
            max_tokens=config.s2_mia_max_tokens,
        )
        score = semantic_similarity_score(
            str(documents[doc_id]["text"]), response, client, config.embedding_model
        )
        events.append(event)
        decisions.append(_record(event, prepared, response, score))
    return events, decisions


def _replay_masked(
    rows: list[dict[str, Any]],
    guard: GuardedRAG,
    client: ModelClient,
    config: AttackConfig,
    source_run_id: str,
    dataset_id: str,
    session_id_override: str | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    events: list[dict[str, Any]] = []
    decisions: list[dict[str, Any]] = []
    for row in rows:
        doc_id = str(row["doc_id"])
        query = str(row["masked_text"])
        risk_query = (
            "Recover the exact original words for every mask in this source passage "
            f"using the retrieved Context: {query}"
        )
        answers = [str(value) for value in row["answers"]]
        event = _event(
            source_run_id=source_run_id,
            dataset_id=dataset_id,
            attack="masked_mia",
            doc_id=doc_id,
            membership_label=int(row["membership_label"]),
            query=query,
            metadata={
                **_query_bank_metadata(row),
                "expected_mask_count": len(answers),
            },
            session_id_override=session_id_override,
        )
        prepared = guard.prepare(
            query,
            str(event["session_id"]),
            risk_query=risk_query,
        )
        if prepared.decision.access_action == "deny_sensitive_answer":
            recovered = [""] * len(answers)
        else:
            contexts = _response_contexts(prepared, client, config)
            recovered = _recover_masks(
                query,
                len(answers),
                contexts,
                client,
                config.generation_model,
                config.masked_max_tokens,
            )
        matches = [
            _normalize_answer(expected) == _normalize_answer(predicted)
            for expected, predicted in zip(answers, recovered)
        ]
        score = sum(matches) / len(matches)
        events.append(event)
        decisions.append(_record(event, prepared, recovered, score))
    return events, decisions


def _replay_ia(
    rows: list[dict[str, Any]],
    guard: GuardedRAG,
    client: ModelClient,
    config: AttackConfig,
    source_run_id: str,
    dataset_id: str,
    session_id_override: str | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    events: list[dict[str, Any]] = []
    decisions: list[dict[str, Any]] = []
    defended_rows: list[dict[str, Any]] = []
    for row in rows:
        doc_id = str(row["doc_id"])
        points: list[float] = []
        for turn_id, query_row in enumerate(row["queries"], start=1):
            query = str(query_row["adversarial_query"])
            expected = str(query_row["ground_truth"])
            event = _event(
                source_run_id=source_run_id,
                dataset_id=dataset_id,
                attack="ia",
                doc_id=doc_id,
                membership_label=int(row["membership_label"]),
                query=query,
                turn_id=turn_id,
                metadata={
                    **_query_bank_metadata(row),
                    **_query_bank_metadata(query_row),
                    "ground_truth": expected,
                },
                session_id_override=session_id_override,
            )
            prepared = guard.prepare(query, str(event["session_id"]))
            response = _text_response(
                prepared,
                client,
                config,
                query,
                instruction=(
                    "Please answer using only the supplied Context. "
                    "Answer only Yes, No, or Unknown."
                ),
                max_tokens=12,
            )
            predicted = extract_yes_no_unknown(response)
            if predicted == expected:
                point = 1.0
            elif predicted == "unknown":
                point = -config.ia_unknown_penalty
            else:
                point = 0.0
            points.append(point)
            events.append(event)
            decisions.append(_record(event, prepared, response, point))
        defended_rows.append(
            {
                "doc_id": doc_id,
                "membership_label": int(row["membership_label"]),
                "membership_score": sum(points) / len(points),
            }
        )
    return events, decisions, defended_rows


def _benign_documents(
    documents: list[dict[str, Any]], count: int, offset_per_class: int
) -> list[dict[str, Any]]:
    if count <= 0:
        return []
    members = [row for row in documents if int(row["membership_label"]) == 1]
    nonmembers = [row for row in documents if int(row["membership_label"]) == 0]
    member_count = (count + 1) // 2
    nonmember_count = count // 2
    if offset_per_class < 0:
        raise ValueError("offset_per_class must not be negative")
    if (
        len(members) < offset_per_class + member_count
        or len(nonmembers) < offset_per_class + nonmember_count
    ):
        raise ValueError("Run does not contain enough documents for benign queries")
    return (
        members[offset_per_class : offset_per_class + member_count]
        + nonmembers[offset_per_class : offset_per_class + nonmember_count]
    )


def _run_benign(
    documents: list[dict[str, Any]],
    count: int,
    guard: GuardedRAG,
    client: ModelClient,
    config: AttackConfig,
    source_run_id: str,
    dataset_id: str,
    offset_per_class: int,
    session_id_override: str | None = None,
    progress_label: str | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    events: list[dict[str, Any]] = []
    decisions: list[dict[str, Any]] = []
    for index, document in enumerate(
        _benign_documents(documents, count, offset_per_class), start=1
    ):
        doc_id = str(document["doc_id"])
        prefix = " ".join(str(document["text"]).split()[:12])
        query = f'What is the main topic of this news excerpt: "{prefix}"?'
        event = build_query_event(
            event_id=f"benign:{doc_id}:{index}",
            source_record_id=f"benign_mvp:{doc_id}:{index}",
            source_framework="miaguard_benign_mvp",
            run_id=source_run_id,
            dataset_id=dataset_id,
            session_id=(
                session_id_override
                or f"{source_run_id}:{dataset_id}:benign:{doc_id}:{index}"
            ),
            turn_id=1,
            query=query,
            attack_type="benign",
            intent_label=0,
            membership_label=int(document["membership_label"]),
            target_doc_id=doc_id,
            attack_metadata={"generation_method": "deterministic_topic_question_v1"},
        )
        prepared = guard.prepare(query, str(event["session_id"]))
        response = _text_response(
            prepared,
            client,
            config,
            query,
            instruction="Give a concise topic overview using the supplied Context.",
            max_tokens=48,
        )
        events.append(event)
        decision = _record(event, prepared, response, None)
        decisions.append(decision)
        if progress_label is not None:
            print(
                f"[progress] phase={progress_label} attack=benign "
                f"document={index}/{count} turns=1 "
                f"stage1_mean={float(decision['query_risk']):.4f} "
                f"stage2_mean={float(decision['session_risk']):.4f} "
                f"total_mean={float(decision['total_risk']):.4f} "
                f"level={decision['applied_access_level']} "
                f"action={decision['access_action']}",
                flush=True,
            )
    return events, decisions


def _run_benign_queries(
    rows: list[dict[str, Any]],
    guard: GuardedRAG,
    client: ModelClient,
    config: AttackConfig,
    source_run_id: str,
    dataset_id: str,
    session_id_override: str | None = None,
    progress_label: str | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    events: list[dict[str, Any]] = []
    decisions: list[dict[str, Any]] = []
    total = len(rows)
    for index, row in enumerate(rows, start=1):
        doc_id = str(row["doc_id"])
        query = str(row["query_text"])
        event = build_query_event(
            event_id=f"benign:{doc_id}:{index}",
            source_record_id=str(row["query_id"]),
            source_framework="miaguard_query_bank",
            run_id=source_run_id,
            dataset_id=dataset_id,
            session_id=(
                session_id_override
                or f"{source_run_id}:{dataset_id}:benign:{doc_id}:{index}"
            ),
            turn_id=1,
            query=query,
            attack_type="benign",
            intent_label=0,
            membership_label=int(row["membership_label"]),
            target_doc_id=doc_id,
            attack_metadata={
                "query_id": str(row["query_id"]),
                "benign_category": str(row.get("category", "benign")),
            },
        )
        prepared = guard.prepare(query, str(event["session_id"]))
        response = _text_response(
            prepared,
            client,
            config,
            query,
            instruction="Give a concise answer using the supplied Context.",
            max_tokens=48,
        )
        events.append(event)
        decision = _record(event, prepared, response, None)
        decisions.append(decision)
        if progress_label is not None:
            print(
                f"[progress] phase={progress_label} attack=benign "
                f"document={index}/{total} turns=1 "
                f"stage1_mean={float(decision['query_risk']):.4f} "
                f"stage2_mean={float(decision['session_risk']):.4f} "
                f"total_mean={float(decision['total_risk']):.4f} "
                f"level={decision['applied_access_level']} "
                f"action={decision['access_action']}",
                flush=True,
            )
    return events, decisions


def run_defense_experiment(
    project_root: Path,
    source_run_id: str,
    dataset_id: str,
    output_run_id: str,
    attack_config: AttackConfig,
    defense_config: DefenseConfig,
    *,
    limit_per_class: int = 10,
    benign_count: int = 40,
    offset_per_class: int = 0,
) -> dict[str, Any]:
    root = project_root.resolve()
    output = root / "data" / "defense_results" / output_run_id / dataset_id
    if output.exists():
        raise FileExistsError(f"Defense output already exists: {output}")
    if benign_count <= 0:
        raise ValueError("benign_count must be positive")

    client = create_model_client(attack_config, root)
    store = UnifiedVectorStore.load(
        vector_store_path(root, source_run_id, dataset_id), client
    )
    guard = GuardedRAG(store, RuleDefense(defense_config), attack_config.top_k)
    document_rows = load_run_documents(root, source_run_id, dataset_id)
    documents = {str(row["doc_id"]): row for row in document_rows}

    all_events: list[dict[str, Any]] = []
    all_decisions: list[dict[str, Any]] = []
    before: dict[str, dict[str, Any]] = {}
    after: dict[str, dict[str, Any]] = {}
    selected_ids: dict[str, list[str]] = {}

    for attack in ATTACKS:
        rows = _attack_rows(
            root,
            source_run_id,
            dataset_id,
            attack,
            limit_per_class,
            offset_per_class,
        )
        selected_ids[attack] = [str(row["doc_id"]) for row in rows]
        before[attack] = _baseline_metrics(
            rows,
            _threshold(attack_config, attack),
            _threshold_source(attack_config, attack),
        )
        if attack == "direct_rag_mia":
            events, decisions = _replay_direct(
                rows, guard, client, attack_config, source_run_id, dataset_id
            )
            defended_rows = [
                {
                    "membership_label": row["membership_label"],
                    "membership_score": decision["defended_score"],
                }
                for row, decision in zip(rows, decisions)
            ]
        elif attack == "s2_mia":
            events, decisions = _replay_s2(
                rows,
                documents,
                guard,
                client,
                attack_config,
                source_run_id,
                dataset_id,
            )
            defended_rows = [
                {
                    "membership_label": row["membership_label"],
                    "membership_score": decision["defended_score"],
                }
                for row, decision in zip(rows, decisions)
            ]
        elif attack == "masked_mia":
            events, decisions = _replay_masked(
                rows, guard, client, attack_config, source_run_id, dataset_id
            )
            defended_rows = [
                {
                    "membership_label": row["membership_label"],
                    "membership_score": decision["defended_score"],
                }
                for row, decision in zip(rows, decisions)
            ]
        else:
            events, decisions, defended_rows = _replay_ia(
                rows, guard, client, attack_config, source_run_id, dataset_id
            )
        after[attack] = _baseline_metrics(
            defended_rows,
            _threshold(attack_config, attack),
            _threshold_source(attack_config, attack),
        )
        all_events.extend(events)
        all_decisions.extend(decisions)

    benign_events, benign_decisions = _run_benign(
        document_rows,
        benign_count,
        guard,
        client,
        attack_config,
        source_run_id,
        dataset_id,
        offset_per_class,
    )
    all_events.extend(benign_events)
    all_decisions.extend(benign_decisions)

    defense_metrics = evaluate_defense_decisions(all_decisions)
    comparisons = {}
    for attack in ATTACKS:
        comparisons[attack] = {
            "attack_accuracy_before": before[attack]["accuracy"],
            "attack_accuracy_after": after[attack]["accuracy"],
            "attack_accuracy_reduction": (
                before[attack]["accuracy"] - after[attack]["accuracy"]
            ),
        }
    defense_metrics["attack_comparisons"] = comparisons
    defense_metrics["macro_attack_accuracy_before"] = sum(
        value["accuracy"] for value in before.values()
    ) / len(before)
    defense_metrics["macro_attack_accuracy_after"] = sum(
        value["accuracy"] for value in after.values()
    ) / len(after)

    manifest = {
        "status": "completed",
        "completed_at": utc_now_iso(),
        "output_run_id": output_run_id,
        "source_run_id": source_run_id,
        "dataset_id": dataset_id,
        "attacks": list(ATTACKS),
        "limit_per_class": limit_per_class,
        "offset_per_class": offset_per_class,
        "benign_count": benign_count,
        "selected_doc_ids": selected_ids,
        "detector": "rule_only_mvp_v1",
        "detector_input_fields": list(RuleDefense.detector_input_fields()),
        "generation_model": attack_config.generation_model,
        "embedding_model": attack_config.embedding_model,
        "vector_store_run_id": source_run_id,
        "attack_thresholds": {
            attack: _threshold(attack_config, attack) for attack in ATTACKS
        },
        "attack_threshold_sources": {
            attack: _threshold_source(attack_config, attack) for attack in ATTACKS
        },
    }
    output.mkdir(parents=True, exist_ok=False)
    write_jsonl_atomic(output / "query_events.jsonl", all_events)
    write_jsonl_atomic(output / "defense_decisions.jsonl", all_decisions)
    write_json_atomic(output / "attack_metrics_before.json", before)
    write_json_atomic(output / "attack_metrics_after.json", after)
    write_json_atomic(output / "defense_metrics.json", defense_metrics)
    write_json_atomic(output / "run_manifest.json", manifest)
    summary = {
        "status": "completed",
        "output_path": str(output),
        "attack_event_count": defense_metrics["attack_query_count"],
        "benign_event_count": defense_metrics["benign_query_count"],
        "detector_f1": defense_metrics["f1"],
        "benign_allow_rate": defense_metrics["benign_allow_rate"],
        "macro_attack_accuracy_before": defense_metrics[
            "macro_attack_accuracy_before"
        ],
        "macro_attack_accuracy_after": defense_metrics[
            "macro_attack_accuracy_after"
        ],
    }
    write_json_atomic(output / "summary.json", summary)
    return summary


__all__ = ["run_defense_experiment", "select_balanced_rows"]
