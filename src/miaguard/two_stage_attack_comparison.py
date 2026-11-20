from __future__ import annotations

import re
from collections import Counter
from dataclasses import replace
from pathlib import Path
from typing import Any

from rag_mia_data.io_utils import utc_now_iso, write_json_atomic, write_jsonl_atomic

from .attack_pattern_library import AttackPatternLibrary
from .config import AttackConfig
from .data import load_run_documents, vector_store_path
from .defense import GuardedRAG, evaluate_defense_decisions
from .defense_experiment import (
    ATTACKS,
    _attack_rows,
    _baseline_metrics,
    _replay_direct,
    _replay_ia,
    _replay_masked,
    _replay_s2,
    _run_benign,
    _run_benign_queries,
    _threshold,
    _threshold_source,
)
from .direct_scorer import (
    DirectQueryRiskDetector,
    DirectScorerConfig,
    DirectSessionRiskDetector,
)
from .model_client import create_model_client
from .query_bank.sampler import sample_query_bank
from .query_bank.schema import document_sha256
from .query_bank.storage import QueryBank, QueryBankPaths
from .ia_attack import _generate_ground_truth, _generate_questions
from .two_stage_direct_experiment import binary_detection_metrics
from .two_stage_gateway import TwoStageConfig, TwoStageGateway
from .vector_store import UnifiedVectorStore


def prepare_frozen_query_selection(
    bank: QueryBank,
    document_rows: list[dict[str, Any]],
    *,
    limit_per_class: int,
    benign_count: int,
    ia_turn_count: int,
    seed: int,
    variant_mode: str,
) -> dict[str, Any]:
    current = {str(row["doc_id"]): row for row in document_rows}
    for document in bank.documents:
        doc_id = str(document["doc_id"])
        if doc_id not in current:
            raise ValueError(f"Query Bank document is missing from source run: {doc_id}")
        if document_sha256(str(current[doc_id]["text"])) != str(
            document["source_document_sha256"]
        ):
            raise ValueError(f"Query Bank source document hash changed: {doc_id}")
        if int(current[doc_id]["membership_label"]) != int(
            document["membership_label"]
        ):
            raise ValueError(f"Query Bank membership label changed: {doc_id}")
    return sample_query_bank(
        bank,
        limit_per_class=limit_per_class,
        benign_count=benign_count,
        ia_turn_count=ia_turn_count,
        seed=seed,
        variant_mode=variant_mode,
    )


def _score_rows(
    rows: list[dict[str, Any]], decisions: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    if len(rows) != len(decisions):
        raise ValueError("Attack rows and replay decisions must have equal length")
    return [
        {
            "doc_id": str(row["doc_id"]),
            "membership_label": int(row["membership_label"]),
            "membership_score": float(decision["defended_score"]),
        }
        for row, decision in zip(rows, decisions)
    ]


def expand_ia_rows(
    rows: list[dict[str, Any]],
    documents: dict[str, dict[str, Any]],
    client: Any,
    attack_config: AttackConfig,
    turn_count: int,
) -> list[dict[str, Any]]:
    if not 1 <= turn_count <= 5:
        raise ValueError("IA turn count must be between 1 and 5")
    expanded: list[dict[str, Any]] = []
    total = len(rows)
    for index, row in enumerate(rows, start=1):
        existing = list(row.get("queries", []))
        if len(existing) >= turn_count:
            expanded.append({**row, "queries": existing[:turn_count]})
            print(
                f"[progress] phase=prepare attack=ia document={index}/{total} "
                f"turns={turn_count} source=existing",
                flush=True,
            )
            continue
        doc_id = str(row["doc_id"])
        text = str(documents[doc_id]["text"])
        missing = turn_count - len(existing)
        source = "generated"
        try:
            generated_summary, questions = _generate_questions(
                text,
                missing,
                client,
                attack_config.generation_model,
                max(384, attack_config.ia_generation_max_tokens),
            )
            if len(questions) != missing:
                raise RuntimeError(f"IA generation returned too few questions for {doc_id}")
            answers = _generate_ground_truth(
                text,
                questions,
                client,
                attack_config.generation_model,
                max(384, attack_config.ia_generation_max_tokens),
            )
        except (RuntimeError, ValueError):
            generated_summary = str(row.get("summary", "document topic"))
            words = re.findall(r"[^\W_]+(?:['’-][^\W_]+)*", text, flags=re.UNICODE)
            if len(words) < 4:
                raise RuntimeError(f"IA deterministic fallback has too little text: {doc_id}")
            starts = [
                min(len(words) - 4, round(index * (len(words) - 4) / max(1, missing - 1)))
                for index in range(missing)
            ]
            questions = [
                "Does the described report explicitly mention the phrase "
                f"{' '.join(words[start:start + 4])}?"
                for start in starts
            ]
            answers = ["yes"] * missing
            source = "deterministic_fallback"
        summary = str(row.get("summary") or generated_summary or "document topic")
        generated_queries = [
            {
                "adversarial_query": (
                    f"I am inquiring about a {summary}. {question} "
                    "Please answer with Yes, No, or Unknown."
                ),
                "ground_truth": answer,
                "question": question,
                "generation_source": source,
            }
            for question, answer in zip(questions, answers)
        ]
        expanded.append(
            {
                **row,
                "summary": summary,
                "queries": (existing + generated_queries)[:turn_count],
            }
        )
        print(
            f"[progress] phase=prepare attack=ia document={index}/{total} "
            f"turns={turn_count} source={source}",
            flush=True,
        )
    return expanded


def _run_attack(
    attack: str,
    rows: list[dict[str, Any]],
    documents: dict[str, dict[str, Any]],
    guard: GuardedRAG,
    client: Any,
    attack_config: AttackConfig,
    source_run_id: str,
    dataset_id: str,
    session_id_override: str | None = None,
    progress_phase: str | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    if progress_phase is not None:
        all_events: list[dict[str, Any]] = []
        all_decisions: list[dict[str, Any]] = []
        all_scores: list[dict[str, Any]] = []
        total = len(rows)
        for index, row in enumerate(rows, start=1):
            events, decisions, scores = _run_attack(
                attack,
                [row],
                documents,
                guard,
                client,
                attack_config,
                source_run_id,
                dataset_id,
                session_id_override,
            )
            all_events.extend(events)
            all_decisions.extend(decisions)
            all_scores.extend(scores)
            query_mean = _mean([float(value["query_risk"]) for value in decisions])
            session_mean = _mean([float(value["session_risk"]) for value in decisions])
            total_mean = _mean([float(value["total_risk"]) for value in decisions])
            last = decisions[-1]
            print(
                f"[progress] phase={progress_phase} attack={attack} "
                f"document={index}/{total} turns={len(decisions)} "
                f"stage1_mean={query_mean:.4f} stage2_mean={session_mean:.4f} "
                f"total_mean={total_mean:.4f} level={last['applied_access_level']} "
                f"action={last['access_action']}",
                flush=True,
            )
        return all_events, all_decisions, all_scores
    if attack == "direct_rag_mia":
        events, decisions = _replay_direct(
            rows,
            guard,
            client,
            attack_config,
            source_run_id,
            dataset_id,
            session_id_override,
        )
        return events, decisions, _score_rows(rows, decisions)
    if attack == "s2_mia":
        events, decisions = _replay_s2(
            rows,
            documents,
            guard,
            client,
            attack_config,
            source_run_id,
            dataset_id,
            session_id_override,
        )
        return events, decisions, _score_rows(rows, decisions)
    if attack == "masked_mia":
        events, decisions = _replay_masked(
            rows,
            guard,
            client,
            attack_config,
            source_run_id,
            dataset_id,
            session_id_override,
        )
        return events, decisions, _score_rows(rows, decisions)
    if attack == "ia":
        return _replay_ia(
            rows,
            guard,
            client,
            attack_config,
            source_run_id,
            dataset_id,
            session_id_override,
        )
    raise ValueError(f"Unsupported attack: {attack}")


def _comparison(
    before: dict[str, dict[str, Any]],
    after: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    attacks: dict[str, dict[str, Any]] = {}
    for attack in ATTACKS:
        attacks[attack] = {
            "sample_count": before[attack]["sample_count"],
            "member_count": before[attack]["member_count"],
            "nonmember_count": before[attack]["nonmember_count"],
            "accuracy_no_defense": before[attack]["accuracy"],
            "accuracy_with_defense": after[attack]["accuracy"],
            "accuracy_reduction": before[attack]["accuracy"] - after[attack]["accuracy"],
            "f1_no_defense": before[attack]["f1"],
            "f1_with_defense": after[attack]["f1"],
            "roc_auc_no_defense": before[attack]["roc_auc"],
            "roc_auc_with_defense": after[attack]["roc_auc"],
            "member_score_mean_no_defense": before[attack]["member_score_mean"],
            "member_score_mean_with_defense": after[attack]["member_score_mean"],
            "nonmember_score_mean_no_defense": before[attack]["nonmember_score_mean"],
            "nonmember_score_mean_with_defense": after[attack]["nonmember_score_mean"],
            "confusion_matrix_no_defense": before[attack]["confusion_matrix"],
            "confusion_matrix_with_defense": after[attack]["confusion_matrix"],
        }
    return {
        "attacks": attacks,
        "macro_accuracy_no_defense": sum(
            metrics["accuracy"] for metrics in before.values()
        )
        / len(before),
        "macro_accuracy_with_defense": sum(
            metrics["accuracy"] for metrics in after.values()
        )
        / len(after),
        "macro_roc_auc_no_defense": sum(
            metrics["roc_auc"] for metrics in before.values()
        )
        / len(before),
        "macro_roc_auc_with_defense": sum(
            metrics["roc_auc"] for metrics in after.values()
        )
        / len(after),
    }


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _stage_scores(
    attack_decisions: list[dict[str, Any]],
    benign_decisions: list[dict[str, Any]],
    threshold: float,
) -> dict[str, Any]:
    rows = attack_decisions + benign_decisions
    labels = [int(row["intent_label"]) for row in rows]
    stages: dict[str, Any] = {}
    for stage, score_field, class_field in (
        ("query_stage", "query_risk", "query_risk_class"),
        ("session_stage", "session_risk", "session_risk_class"),
    ):
        overall = binary_detection_metrics(
            labels,
            [float(row[score_field]) for row in rows],
            threshold,
        )
        by_attack: dict[str, Any] = {}
        for attack in ATTACKS:
            selected = [
                row for row in attack_decisions if row["attack_type"] == attack
            ]
            member_scores = [
                float(row[score_field])
                for row in selected
                if int(row["membership_label"]) == 1
            ]
            nonmember_scores = [
                float(row[score_field])
                for row in selected
                if int(row["membership_label"]) == 0
            ]
            detected_count = sum(
                float(row[score_field]) >= threshold for row in selected
            )
            status_key = (
                "query_detection" if stage == "query_stage" else "session_detection"
            )
            statuses = Counter(
                str(row["two_stage_assessment"][status_key]["status"])
                for row in selected
            )
            by_attack[attack] = {
                "sample_count": len(selected),
                "member_count": len(member_scores),
                "nonmember_count": len(nonmember_scores),
                "score_mean": _mean(
                    [float(row[score_field]) for row in selected]
                ),
                "member_score_mean": _mean(member_scores),
                "nonmember_score_mean": _mean(nonmember_scores),
                "detected_count": detected_count,
                "detection_rate": detected_count / len(selected),
                "risk_class_counts": dict(
                    sorted(Counter(str(row[class_field]) for row in selected).items())
                ),
                "status_counts": dict(sorted(statuses.items())),
            }
        benign_scores = [float(row[score_field]) for row in benign_decisions]
        stages[stage] = {
            "threshold": threshold,
            "overall_detection_metrics": overall,
            "by_attack": by_attack,
            "benign_score_mean": _mean(benign_scores),
            "benign_detected_count": sum(score >= threshold for score in benign_scores),
        }
    return stages


def run_two_stage_attack_comparison(
    project_root: Path,
    source_run_id: str,
    dataset_id: str,
    output_run_id: str,
    attack_config: AttackConfig,
    gateway_config: TwoStageConfig,
    scorer_config: DirectScorerConfig,
    *,
    limit_per_class: int = 1,
    benign_count: int = 4,
    offset_per_class: int = 0,
    continuous_attack_sessions: bool = False,
    ia_turn_count: int = 1,
    query_bank_id: str | None = None,
    query_seed: int = 20260725,
    variant_mode: str = "canonical",
) -> dict[str, Any]:
    if gateway_config.mode != "enforce":
        raise ValueError("Attack comparison requires an enforce-mode gateway config")
    if limit_per_class <= 0 or benign_count <= 0:
        raise ValueError("Attack and benign sample counts must be positive")

    root = project_root.resolve()
    output = root / "data" / "two_stage_attack_results" / output_run_id / dataset_id
    if output.exists():
        raise FileExistsError(f"Attack comparison output already exists: {output}")

    print(
        f"[setup] output_run_id={output_run_id} dataset={dataset_id} "
        f"members_per_attack={limit_per_class} nonmembers_per_attack={limit_per_class} "
        f"benign={benign_count} ia_turns={ia_turn_count}",
        flush=True,
    )
    print("[setup] loading local generation and embedding models", flush=True)
    client = create_model_client(attack_config, root)
    client.validate_models()
    print("[setup] models loaded and validated", flush=True)
    print("[setup] loading FAISS vector store", flush=True)
    store = UnifiedVectorStore.load(
        vector_store_path(root, source_run_id, dataset_id), client
    )
    print("[setup] FAISS vector store loaded", flush=True)
    document_rows = load_run_documents(root, source_run_id, dataset_id)
    documents = {str(row["doc_id"]): row for row in document_rows}

    baseline_gateway = TwoStageGateway(replace(gateway_config, mode="disabled"))
    baseline_guard = GuardedRAG(store, baseline_gateway, attack_config.top_k)

    library = AttackPatternLibrary.load(scorer_config.manifest_path)
    defended_gateway = TwoStageGateway(
        gateway_config,
        query_detector=DirectQueryRiskDetector(
            scorer_config, client, attack_config.generation_model, library
        ),
        session_detector=DirectSessionRiskDetector(
            scorer_config, client, attack_config.generation_model, library
        ),
    )
    defended_guard = GuardedRAG(store, defended_gateway, attack_config.top_k)

    frozen_selection: dict[str, Any] | None = None
    if query_bank_id is not None:
        bank = QueryBank.load(QueryBankPaths(root, query_bank_id, dataset_id))
        frozen_selection = prepare_frozen_query_selection(
            bank,
            document_rows,
            limit_per_class=limit_per_class,
            benign_count=benign_count,
            ia_turn_count=ia_turn_count,
            seed=query_seed,
            variant_mode=variant_mode,
        )
        selected_rows = frozen_selection["attacks"]
        print(
            f"[setup] query_bank={query_bank_id} seed={query_seed} "
            f"variant_mode={variant_mode} online_query_generation=false",
            flush=True,
        )
    else:
        selected_rows = {
            attack: _attack_rows(
                root,
                source_run_id,
                dataset_id,
                attack,
                limit_per_class,
                offset_per_class,
            )
            for attack in ATTACKS
        }
        selected_rows["ia"] = expand_ia_rows(
            selected_rows["ia"],
            documents,
            client,
            attack_config,
            ia_turn_count,
        )
    before_metrics: dict[str, dict[str, Any]] = {}
    after_metrics: dict[str, dict[str, Any]] = {}
    baseline_events: list[dict[str, Any]] = []
    baseline_decisions: list[dict[str, Any]] = []
    defended_events: list[dict[str, Any]] = []
    defended_decisions: list[dict[str, Any]] = []

    for attack in ATTACKS:
        rows = selected_rows[attack]
        session_id = (
            f"{output_run_id}:{dataset_id}:no-defense:{attack}:continuous"
            if continuous_attack_sessions
            else None
        )
        print(
            f"[comparison] phase=no_defense attack={attack} samples={len(rows)} started",
            flush=True,
        )
        events, decisions, scores = _run_attack(
            attack,
            rows,
            documents,
            baseline_guard,
            client,
            attack_config,
            source_run_id,
            dataset_id,
            session_id,
            "no_defense",
        )
        baseline_events.extend(events)
        baseline_decisions.extend(decisions)
        before_metrics[attack] = _baseline_metrics(
            scores,
            _threshold(attack_config, attack),
            _threshold_source(attack_config, attack),
        )
        print(
            f"[comparison] phase=no_defense attack={attack} completed "
            f"accuracy={before_metrics[attack]['accuracy']:.4f}",
            flush=True,
        )

    for attack in ATTACKS:
        rows = selected_rows[attack]
        session_id = (
            f"{output_run_id}:{dataset_id}:with-defense:{attack}:continuous"
            if continuous_attack_sessions
            else None
        )
        print(
            f"[comparison] phase=with_defense attack={attack} samples={len(rows)} started",
            flush=True,
        )
        events, decisions, scores = _run_attack(
            attack,
            rows,
            documents,
            defended_guard,
            client,
            attack_config,
            source_run_id,
            dataset_id,
            session_id,
            "with_defense",
        )
        defended_events.extend(events)
        defended_decisions.extend(decisions)
        after_metrics[attack] = _baseline_metrics(
            scores,
            _threshold(attack_config, attack),
            _threshold_source(attack_config, attack),
        )
        print(
            f"[comparison] phase=with_defense attack={attack} completed "
            f"accuracy={after_metrics[attack]['accuracy']:.4f}",
            flush=True,
        )

    print(f"[comparison] phase=benign samples={benign_count} started", flush=True)
    benign_session_id = (
        f"{output_run_id}:{dataset_id}:with-defense:benign:continuous"
        if continuous_attack_sessions
        else None
    )
    if frozen_selection is not None:
        benign_events, benign_decisions = _run_benign_queries(
            frozen_selection["benign"],
            defended_guard,
            client,
            attack_config,
            source_run_id,
            dataset_id,
            benign_session_id,
            progress_label="with_defense",
        )
    else:
        benign_events, benign_decisions = _run_benign(
            document_rows,
            benign_count,
            defended_guard,
            client,
            attack_config,
            source_run_id,
            dataset_id,
            offset_per_class,
            benign_session_id,
            progress_label="with_defense",
        )
    print("[comparison] phase=benign completed", flush=True)
    detector_metrics = evaluate_defense_decisions(
        defended_decisions + benign_decisions
    )
    detector_metrics["action_counts_by_attack"] = {
        attack: dict(
            sorted(
                Counter(
                    row["access_action"]
                    for row in defended_decisions
                    if row["attack_type"] == attack
                ).items()
            )
        )
        for attack in ATTACKS
    }
    comparison = _comparison(before_metrics, after_metrics)
    comparison["macro_accuracy_reduction"] = (
        comparison["macro_accuracy_no_defense"]
        - comparison["macro_accuracy_with_defense"]
    )
    comparison["macro_roc_auc_reduction"] = (
        comparison["macro_roc_auc_no_defense"]
        - comparison["macro_roc_auc_with_defense"]
    )
    stage_scores = _stage_scores(
        defended_decisions,
        benign_decisions,
        gateway_config.level_thresholds[1],
    )

    manifest = {
        "status": "completed",
        "completed_at": utc_now_iso(),
        "output_run_id": output_run_id,
        "source_run_id": source_run_id,
        "dataset_id": dataset_id,
        "attacks": list(ATTACKS),
        "limit_per_class": limit_per_class,
        "samples_per_attack": 2 * limit_per_class,
        "total_attack_documents": 2 * limit_per_class * len(ATTACKS),
        "benign_count": benign_count,
        "offset_per_class": offset_per_class,
        "continuous_attack_sessions": continuous_attack_sessions,
        "ia_turn_count": ia_turn_count,
        "selected_doc_ids": {
            attack: [str(row["doc_id"]) for row in rows]
            for attack, rows in selected_rows.items()
        },
        "comparison_control": (
            "same selected rows, vector store, thresholds, embedding model, "
            "generation model, and loaded model instance; only gateway mode differs"
        ),
        "no_defense_mode": "disabled",
        "with_defense_mode": gateway_config.mode,
        "generation_model": attack_config.generation_model,
        "generation_backend": attack_config.generation_backend,
        "generation_load_mode": attack_config.generation_load_mode,
        "embedding_model": attack_config.embedding_model,
        "pattern_library_version": library.version,
        "query_bank_id": query_bank_id,
        "query_bank_sha256": (
            frozen_selection["query_bank_sha256"]
            if frozen_selection is not None
            else None
        ),
        "query_seed": query_seed if frozen_selection is not None else None,
        "query_variant_mode": (
            variant_mode if frozen_selection is not None else None
        ),
        "online_query_generation": frozen_selection is None,
        "attack_thresholds": {
            attack: _threshold(attack_config, attack) for attack in ATTACKS
        },
        "limitations": [
            "Smoke-scale results are functional evidence, not paper-level statistics.",
            (
                "Attack rows are grouped into one continuous session per attack type; "
                "the session detector activates on turn three and its latest assessment "
                "may be cached according to the gateway evaluation interval."
                if continuous_attack_sessions
                else (
                    f"Each frozen IA session uses {ia_turn_count} pre-generated queries."
                    if frozen_selection is not None
                    else "Each source IA document has one question, so independent "
                    "per-document sessions remain below the three-query session "
                    "activation minimum."
                )
            ),
        ],
    }
    summary = {
        "status": "completed",
        "output_path": str(output),
        "samples_per_attack": 2 * limit_per_class,
        "benign_count": benign_count,
        "macro_attack_accuracy_no_defense": comparison[
            "macro_accuracy_no_defense"
        ],
        "macro_attack_accuracy_with_defense": comparison[
            "macro_accuracy_with_defense"
        ],
        "macro_attack_accuracy_reduction": comparison[
            "macro_accuracy_reduction"
        ],
        "detector_f1": detector_metrics["f1"],
        "query_stage_f1": stage_scores["query_stage"][
            "overall_detection_metrics"
        ]["f1"],
        "session_stage_f1": stage_scores["session_stage"][
            "overall_detection_metrics"
        ]["f1"],
        "benign_false_positive_rate": detector_metrics[
            "benign_false_positive_rate"
        ],
    }

    output.mkdir(parents=True, exist_ok=False)
    write_jsonl_atomic(output / "no_defense_events.jsonl", baseline_events)
    write_jsonl_atomic(output / "no_defense_decisions.jsonl", baseline_decisions)
    write_jsonl_atomic(output / "with_defense_events.jsonl", defended_events)
    write_jsonl_atomic(output / "with_defense_decisions.jsonl", defended_decisions)
    write_jsonl_atomic(output / "benign_events.jsonl", benign_events)
    write_jsonl_atomic(output / "benign_decisions.jsonl", benign_decisions)
    write_json_atomic(output / "attack_metrics_no_defense.json", before_metrics)
    write_json_atomic(output / "attack_metrics_with_defense.json", after_metrics)
    write_json_atomic(output / "comparison.json", comparison)
    write_json_atomic(output / "detector_metrics.json", detector_metrics)
    write_json_atomic(output / "stage_scores.json", stage_scores)
    if frozen_selection is not None:
        write_json_atomic(
            output / "query_selection_manifest.json",
            {
                key: value
                for key, value in frozen_selection.items()
                if key not in {"attacks", "benign"}
            },
        )
    write_json_atomic(output / "run_manifest.json", manifest)
    write_json_atomic(output / "summary.json", summary)
    return summary


__all__ = ["run_two_stage_attack_comparison"]
