from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from rag_mia_data.io_utils import read_jsonl, utc_now_iso, write_json_atomic, write_jsonl_atomic

from miaguard.config import load_attack_config
from miaguard.data import load_run_documents
from miaguard.model_client import ModelClient, create_model_client

from .builder import (
    _ia_no_candidates_from_anchors,
    _ia_no_candidates_from_facts,
    _ia_yes_anchor_candidates,
    _ia_yes_candidates_from_facts,
    _is_safe_yes_anchor,
    _record,
)
from .schema import QueryBankBuildConfig
from .storage import QueryBank, QueryBankLock, QueryBankPaths, compact_query_bank, write_document_shard
from .validator import IA_MIN_ANSWER_COUNTS, normalize_query, validate_document_records


REPAIR_SCHEME_VERSION = "anchor-pair-10x10-v1"


def _ia_answer_counts(records: list[dict[str, Any]]) -> dict[str, int]:
    counts = Counter(
        str(row["payload"]["ground_truth"])
        for row in records
        if row["attack_type"] == "ia"
    )
    return dict(sorted(counts.items()))


def _counts_by_attack(records: list[dict[str, Any]]) -> dict[str, int]:
    return dict(sorted(Counter(str(row["attack_type"]) for row in records).items()))


def _build_config(
    bank: QueryBank,
    attack_config_path: Path,
    seed: int,
) -> QueryBankBuildConfig:
    return QueryBankBuildConfig(
        source_run_id=str(bank.manifest["source_run_id"]),
        attack_config_path=attack_config_path,
        seed=seed,
        member_count=sum(
            int(row["membership_label"]) == 1 for row in bank.documents
        ),
        nonmember_count=sum(
            int(row["membership_label"]) == 0 for row in bank.documents
        ),
        paraphrases_per_attack=4,
        ia_questions_per_document=30,
        ia_batch_size=6,
        ia_max_attempts=20,
        benign_categories=("topic", "entity", "event", "summary", "follow_up"),
    )


def repair_ia_query_bank(
    project_root: Path,
    bank_id: str,
    dataset_id: str,
    attack_config_path: Path,
    *,
    seed: int,
    client: ModelClient | None = None,
) -> dict[str, Any]:
    """Append verified IA rows until every document has 10 yes and 10 no rows."""
    root = project_root.resolve()
    paths = QueryBankPaths(root, bank_id, dataset_id)
    bank = QueryBank.load(paths)
    if bank.dataset_id != dataset_id:
        raise ValueError("Query Bank dataset does not match requested dataset")
    resolved_attack_config_path = attack_config_path
    if not resolved_attack_config_path.is_absolute():
        resolved_attack_config_path = root / resolved_attack_config_path
    attack_config = load_attack_config(resolved_attack_config_path)
    client = client or create_model_client(attack_config, root)
    build_config = _build_config(bank, resolved_attack_config_path, seed)
    source_rows = load_run_documents(
        root, str(bank.manifest["source_run_id"]), dataset_id
    )
    source_text = {str(row["doc_id"]): str(row["text"]) for row in source_rows}
    records_by_doc: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in bank.records:
        records_by_doc[str(record["doc_id"])].append(record)

    proposed_by_doc = {
        doc_id: list(records)
        for doc_id, records in records_by_doc.items()
    }
    audit_rows: list[dict[str, Any]] = []
    added_query_count = 0
    progress_rows = (
        list(read_jsonl(paths.repair_progress))
        if paths.repair_progress.exists()
        else []
    )
    if progress_rows and progress_rows[-1].get("scheme_version") != REPAIR_SCHEME_VERSION:
        paths.repair_progress_archive.mkdir(parents=True, exist_ok=True)
        timestamp = utc_now_iso().replace(":", "-")
        archive_path = paths.repair_progress_archive / f"ia_repair_progress.{timestamp}.jsonl"
        paths.repair_progress.replace(archive_path)
        progress_rows = []
    progress: dict[str, Any] = dict(progress_rows[-1]) if progress_rows else {}
    completed_documents: dict[str, dict[str, Any]] = dict(
        progress.get("completed_documents", {})
    )
    pending_document = progress.get("pending_document")

    def save_progress(
        *,
        pending: dict[str, Any] | None,
        last_failure: dict[str, Any] | None = None,
    ) -> None:
        state: dict[str, Any] = {
            "scheme_version": REPAIR_SCHEME_VERSION,
            "ia_min_answer_counts": dict(IA_MIN_ANSWER_COUNTS),
            "bank_id": bank_id,
            "dataset_id": dataset_id,
            "seed": seed,
            "updated_at": utc_now_iso(),
            "completed_documents": completed_documents,
            "pending_document": pending,
        }
        if last_failure is not None:
            state["last_failure"] = last_failure
        write_jsonl_atomic(paths.repair_progress, [state])

    for document in bank.documents:
        doc_id = str(document["doc_id"])
        if doc_id not in source_text:
            raise ValueError(f"Query Bank document is missing from source run: {doc_id}")
        existing = proposed_by_doc.get(doc_id, [])
        old_counts = _ia_answer_counts(existing)
        required_answers = {
            answer: max(0, minimum - old_counts.get(answer, 0))
            for answer, minimum in IA_MIN_ANSWER_COUNTS.items()
        }
        if not any(required_answers.values()):
            continue
        saved_document = completed_documents.get(doc_id)
        if saved_document is not None:
            added_rows = list(saved_document["added_rows"])
            proposed_by_doc[doc_id] = [*existing, *added_rows]
            audit_rows.append(dict(saved_document["audit"]))
            added_query_count += len(added_rows)
            continue
        saved_pending = (
            pending_document
            if isinstance(pending_document, dict)
            and pending_document.get("doc_id") == doc_id
            else None
        )
        added_rows: list[dict[str, Any]] = (
            list(saved_pending.get("added_rows", [])) if saved_pending else []
        )
        attempted_anchors = set(
            saved_pending.get("attempted_anchors", []) if saved_pending else []
        )
        existing_questions = tuple(
            str(row["payload"]["question"])
            for row in existing
            if row["attack_type"] == "ia"
        )
        existing_questions = (
            *existing_questions,
            *(
                str(row["payload"]["question"])
                for row in added_rows
                if row["attack_type"] == "ia"
            ),
        )
        next_index = max(
            (
                int(row["query_index"])
                for row in [*existing, *added_rows]
                if row["attack_type"] == "ia"
            ),
            default=0,
        ) + 1
        summary = (
            str(added_rows[0]["payload"].get("summary", ""))
            if added_rows
            else ""
        )

        def pending_state() -> dict[str, Any]:
            working_counts = _ia_answer_counts([*existing, *added_rows])
            completed_answers = sorted(
                answer
                for answer, minimum in IA_MIN_ANSWER_COUNTS.items()
                if working_counts.get(answer, 0) >= minimum
            )
            return {
                "doc_id": doc_id,
                "old_ia_answer_counts": old_counts,
                "required_answers": required_answers,
                "completed_answers": completed_answers,
                "added_rows": added_rows,
                "attempted_anchors": sorted(attempted_anchors),
                "summary": summary,
            }

        def append_yes_anchors(target_count: int) -> list[str]:
            nonlocal existing_questions, next_index, summary
            if target_count <= 0:
                return []
            anchors: list[str] = []

            def checkpoint_anchor(
                candidate_summary: str,
                candidate: dict[str, str],
            ) -> None:
                nonlocal existing_questions, next_index, summary
                question = candidate["question"]
                summary = summary or candidate_summary or "reported fact"
                row = _record(
                    dataset_id=dataset_id,
                    document={
                        "doc_id": doc_id,
                        "membership_label": int(document["membership_label"]),
                        "text": source_text[doc_id],
                    },
                    attack_type="ia",
                    variant_type="generated",
                    query_index=next_index,
                    query_text=(
                        f"I am inquiring about a {summary}. {question} "
                        "Please answer with Yes, No, or Unknown."
                    ),
                    payload={
                        "summary": summary,
                        "question": question,
                        "ground_truth": "yes",
                    },
                    attack_config=attack_config,
                    prompt_version=REPAIR_SCHEME_VERSION,
                    temperature=0.2,
                    seed=seed,
                )
                added_rows.append(row)
                anchors.append(question)
                next_index += 1
                existing_questions = (*existing_questions, question)
                save_progress(pending=pending_state())

            candidate_summary, candidates = _ia_yes_candidates_from_facts(
                source_text[doc_id],
                attack_config,
                client,
                target_count=target_count,
                existing_questions=existing_questions,
            )
            for candidate in candidates:
                checkpoint_anchor(candidate_summary, candidate)

            stalled_rounds = 0
            while len(anchors) < target_count:
                remaining = target_count - len(anchors)
                before_count = len(anchors)
                try:
                    _ia_yes_anchor_candidates(
                        source_text[doc_id],
                        build_config,
                        attack_config,
                        client,
                        target_count=remaining,
                        existing_questions=existing_questions,
                        on_accept=checkpoint_anchor,
                    )
                except Exception as error:
                    if len(anchors) > before_count:
                        stalled_rounds = 0
                        continue
                    stalled_rounds += 1
                    if stalled_rounds < 3:
                        continue
                    save_progress(
                        pending=pending_state(),
                        last_failure={
                            "doc_id": doc_id,
                            "answer": "yes",
                            "error": str(error),
                            "failed_at": utc_now_iso(),
                        },
                    )
                    raise
            return anchors

        working_rows = [*existing, *added_rows]
        working_counts = _ia_answer_counts(working_rows)
        safe_anchors = [
            str(row["payload"]["question"])
            for row in working_rows
            if row["attack_type"] == "ia"
            and row["payload"]["ground_truth"] == "yes"
            and _is_safe_yes_anchor(str(row["payload"]["question"]))
        ]
        yes_needed = max(
            0,
            IA_MIN_ANSWER_COUNTS["yes"] - working_counts.get("yes", 0),
        )
        no_needed = max(
            0,
            IA_MIN_ANSWER_COUNTS["no"] - working_counts.get("no", 0),
        )
        yes_to_generate = max(yes_needed, no_needed - len(safe_anchors))
        append_yes_anchors(yes_to_generate)

        working_rows = [*existing, *added_rows]
        working_counts = _ia_answer_counts(working_rows)
        no_needed = max(
            0,
            IA_MIN_ANSWER_COUNTS["no"] - working_counts.get("no", 0),
        )
        used_anchors = {
            str(row["payload"].get("anchor_question", ""))
            for row in added_rows
            if row["attack_type"] == "ia"
            and row["payload"].get("construction")
        }
        safe_anchors = [
            str(row["payload"]["question"])
            for row in working_rows
            if row["attack_type"] == "ia"
            and row["payload"]["ground_truth"] == "yes"
            and _is_safe_yes_anchor(str(row["payload"]["question"]))
            and str(row["payload"]["question"]) not in used_anchors
            and str(row["payload"]["question"]) not in attempted_anchors
        ]
        replenishment_rounds = 0
        fact_no_attempted = False
        while no_needed > 0:
            if not safe_anchors:
                if not fact_no_attempted:
                    fact_no_attempted = True
                    fact_summary, fact_candidates = _ia_no_candidates_from_facts(
                        source_text[doc_id],
                        build_config,
                        attack_config,
                        client,
                        target_count=no_needed,
                        existing_questions=existing_questions,
                        allow_partial=True,
                    )
                    for candidate in fact_candidates:
                        question = candidate["question"]
                        row = _record(
                            dataset_id=dataset_id,
                            document={
                                "doc_id": doc_id,
                                "membership_label": int(document["membership_label"]),
                                "text": source_text[doc_id],
                            },
                            attack_type="ia",
                            variant_type="generated",
                            query_index=next_index,
                            query_text=(
                                f"I am inquiring about a {fact_summary}. "
                                f"{question} Please answer with Yes, No, or Unknown."
                            ),
                            payload={
                                "summary": fact_summary,
                                "question": question,
                                "ground_truth": "no",
                                "construction": "verified_fact_negation",
                            },
                            attack_config=attack_config,
                            prompt_version=REPAIR_SCHEME_VERSION,
                            temperature=0.0,
                            seed=seed,
                        )
                        added_rows.append(row)
                        existing_questions = (*existing_questions, question)
                        next_index += 1
                        no_needed -= 1
                        save_progress(pending=pending_state())
                    if no_needed <= 0:
                        break
                if replenishment_rounds >= build_config.ia_max_attempts:
                    break
                safe_anchors.extend(append_yes_anchors(no_needed))
                replenishment_rounds += 1
                if not safe_anchors:
                    break
            anchor = safe_anchors.pop(0)
            try:
                candidate = _ia_no_candidates_from_anchors(
                    source_text[doc_id],
                    (anchor,),
                    attack_config,
                    client,
                    target_count=1,
                    existing_questions=existing_questions,
                )[0]
            except RuntimeError:
                attempted_anchors.add(anchor)
                save_progress(pending=pending_state())
                continue
            question = candidate["question"]
            row = _record(
                dataset_id=dataset_id,
                document={
                    "doc_id": doc_id,
                    "membership_label": int(document["membership_label"]),
                    "text": source_text[doc_id],
                },
                attack_type="ia",
                variant_type="generated",
                query_index=next_index,
                query_text=(
                    f"I am inquiring about a {summary or 'reported fact'}. "
                    f"{question} Please answer with Yes, No, or Unknown."
                ),
                payload={
                    "summary": summary or "reported fact",
                    "question": question,
                    "ground_truth": "no",
                    "anchor_question": candidate["anchor_question"],
                    "construction": candidate["construction"],
                },
                attack_config=attack_config,
                prompt_version=REPAIR_SCHEME_VERSION,
                temperature=0.2,
                seed=seed,
            )
            added_rows.append(row)
            existing_questions = (*existing_questions, question)
            attempted_anchors.add(anchor)
            next_index += 1
            no_needed -= 1
            save_progress(pending=pending_state())
        if no_needed:
            error = RuntimeError(
                f"IA anchor-pair repair still needs {no_needed} no questions "
                f"for {doc_id}; safe anchors exhausted after "
                f"{replenishment_rounds} replenishment rounds"
            )
            save_progress(
                pending=pending_state(),
                last_failure={
                    "doc_id": doc_id,
                    "answer": "no",
                    "error": str(error),
                    "failed_at": utc_now_iso(),
                },
            )
            raise error
        proposed_by_doc[doc_id] = [*existing, *added_rows]
        new_counts = _ia_answer_counts(proposed_by_doc[doc_id])
        audit = {
            "doc_id": doc_id,
            "old_ia_answer_counts": old_counts,
            "new_ia_answer_counts": new_counts,
            "added_query_ids": [str(row["query_id"]) for row in added_rows],
            "requested_answers": required_answers,
            "seed": seed,
            "repaired_at": utc_now_iso(),
            "generation_model": attack_config.generation_model,
        }
        audit_rows.append(audit)
        completed_documents[doc_id] = {"added_rows": added_rows, "audit": audit}
        pending_document = None
        save_progress(pending=None)
        added_query_count += len(added_rows)

    all_records = [
        record
        for document in bank.documents
        for record in proposed_by_doc.get(str(document["doc_id"]), [])
    ]
    query_ids = [str(row["query_id"]) for row in all_records]
    if len(query_ids) != len(set(query_ids)):
        raise ValueError("IA repair would create duplicate query_id values")
    for document in bank.documents:
        doc_id = str(document["doc_id"])
        records = proposed_by_doc.get(doc_id, [])
        validate_document_records(records, document)
        questions = [
            normalize_query(str(row["payload"]["question"]))
            for row in records
            if row["attack_type"] == "ia"
        ]
        if len(questions) != len(set(questions)):
            raise ValueError(f"Document contains a duplicate IA question: {doc_id}")

    if not audit_rows:
        if paths.repair_progress.exists():
            paths.repair_progress.unlink()
        return {
            "status": "complete",
            "bank_id": bank_id,
            "dataset_id": dataset_id,
            "repaired_document_count": 0,
            "added_query_count": 0,
            "queries_sha256": bank.sha256,
            "repair_log": str(paths.repair_log),
        }

    with QueryBankLock(paths):
        for document in bank.documents:
            doc_id = str(document["doc_id"])
            write_document_shard(paths, doc_id, proposed_by_doc[doc_id])
        digest = compact_query_bank(paths, list(bank.documents))
        manifest = dict(bank.manifest)
        manifest.update(
            {
                "query_count": len(all_records),
                "queries_sha256": digest,
                "counts_by_attack": _counts_by_attack(all_records),
                "ia_answer_counts": _ia_answer_counts(all_records),
                "ia_min_answer_counts": dict(IA_MIN_ANSWER_COUNTS),
                "ia_repair_version": "v1",
                "updated_at": utc_now_iso(),
            }
        )
        write_json_atomic(paths.manifest, manifest)

    prior_audit = list(read_jsonl(paths.repair_log)) if paths.repair_log.exists() else []
    write_jsonl_atomic(paths.repair_log, [*prior_audit, *audit_rows])
    if paths.repair_progress.exists():
        paths.repair_progress.unlink()
    return {
        "status": "complete",
        "bank_id": bank_id,
        "dataset_id": dataset_id,
        "repaired_document_count": len(audit_rows),
        "added_query_count": added_query_count,
        "queries_sha256": digest,
        "repair_log": str(paths.repair_log),
    }


__all__ = ["repair_ia_query_bank"]
