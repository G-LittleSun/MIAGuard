from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass, is_dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from rag_mia_data.io_utils import (
    read_jsonl,
    sha256_file,
    write_json_atomic,
    write_jsonl_atomic,
)

from miaguard.risk_types import SessionTurn

from .sessions import PlannedSession


# ``attack_type`` is valid inside a Judge assessment because it is a prediction.
# The remaining fields have no role in a trace and would reveal offline truth.
_TRUTH_FIELDS = {"traffic_type", "membership_label", "target_doc_id"}


@dataclass(frozen=True)
class JudgeBenchmarkPaths:
    root: Path
    partition: str

    @property
    def partition_root(self) -> Path:
        return self.root / self.partition

    @property
    def work(self) -> Path:
        return self.partition_root / ".work"

    @property
    def run_manifest(self) -> Path:
        return self.partition_root / "run_manifest.json"

    @property
    def judge_records(self) -> Path:
        return self.partition_root / "judge_records.jsonl"

    @property
    def benchmark_summary(self) -> Path:
        return self.partition_root / "benchmark_summary.json"

    def shard(self, session_key: str) -> Path:
        digest = hashlib.sha256(session_key.encode("utf-8")).hexdigest()
        return self.work / f"{digest}.jsonl"


def _json_value(value: Any) -> Any:
    if is_dataclass(value):
        return _json_value(asdict(value))
    if isinstance(value, Path):
        return str(value.resolve())
    if isinstance(value, Mapping):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json_value(item) for item in value]
    return value


def canonical_identity_sha256(identity: Mapping[str, Any]) -> str:
    payload = json.dumps(
        _json_value(identity),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _load_manifest(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("Judge benchmark manifest must be a mapping")
    return value


def load_verified_judge_records(
    run_dir: Path,
) -> tuple[list[dict[str, Any]], dict[str, str]]:
    manifest = _load_manifest(run_dir / "run_manifest.json")
    summary = _load_manifest(run_dir / "benchmark_summary.json")
    records_path = run_dir / "judge_records.jsonl"
    identity_sha256 = canonical_identity_sha256(manifest["identity"])
    if manifest.get("identity_sha256") != identity_sha256:
        raise ValueError("Judge benchmark manifest identity hash does not match")
    if summary.get("scoring_identity_sha256") != identity_sha256:
        raise ValueError("Judge benchmark summary identity hash does not match")
    records_sha256 = sha256_file(records_path)
    if summary.get("judge_records_sha256") != records_sha256:
        raise ValueError("Judge benchmark record hash does not match")
    records = list(read_jsonl(records_path))
    if any(
        row.get("scoring_identity_sha256") != identity_sha256
        for row in records
    ):
        raise ValueError("Judge benchmark contains a mixed scoring identity")
    return records, {
        "scoring_identity_sha256": identity_sha256,
        "judge_records_sha256": records_sha256,
    }


def _contains_truth_field(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(
            str(key) in _TRUTH_FIELDS or _contains_truth_field(item)
            for key, item in value.items()
        )
    if isinstance(value, list):
        return any(_contains_truth_field(item) for item in value)
    return False


def _valid_trace(value: Any, stage: str) -> bool:
    if not isinstance(value, Mapping) or value.get("stage") != stage:
        return False
    if _contains_truth_field(value):
        return False
    try:
        screening = value["screening"]
        rubric = value["rubric"]
        logprob = value["logprob"]
        statuses = value["statuses"]
        if not all(key in value for key in ("evidence", "latencies_ms")):
            return False
        if (
            not isinstance(screening, Mapping)
            or not isinstance(rubric, Mapping)
            or not isinstance(logprob, Mapping)
        ):
            return False
        if not isinstance(statuses, Mapping) or not str(statuses["overall"]):
            return False
        decision = screening.get("routing_decision")
        allowed_decisions = {
            "REVIEW",
            "SKIP_EXPLICIT_BENIGN",
            "SKIP_NO_ATTACK_CUE",
        }
        if stage == "session":
            allowed_decisions.add("DEFER_INSUFFICIENT_HISTORY")
        if decision not in allowed_decisions:
            return False
        candidates = screening.get("candidate_attack_types")
        features = screening.get("observed_feature_codes")
        ambiguity = screening.get("candidate_ambiguity")
        if (
            not isinstance(candidates, list)
            or any(not isinstance(item, str) for item in candidates)
            or len(candidates) > 2
            or len(candidates) != len(set(candidates))
            or not isinstance(features, list)
            or any(not isinstance(item, str) for item in features)
            or not isinstance(ambiguity, bool)
        ):
            return False
        if decision == "REVIEW" and not candidates:
            return False
        if decision == "SKIP_EXPLICIT_BENIGN" and (
            candidates
            or ambiguity
            or not {
                "EXPLICIT_BENIGN_PURPOSE",
                "NO_CONTRADICTORY_SUSPICIOUS_MECHANISM",
            }.issubset(features)
        ):
            return False
        if decision == "SKIP_NO_ATTACK_CUE" and (
            candidates
            or ambiguity
            or features
        ):
            return False
        if decision == "DEFER_INSUFFICIENT_HISTORY" and (candidates or ambiguity):
            return False
        if (statuses["overall"] == "insufficient_history") != (
            decision == "DEFER_INSUFFICIENT_HISTORY"
        ):
            return False
        if ambiguity and len(candidates) != 2:
            return False
        for score in (rubric["score"], logprob["score"]):
            number = float(score)
            if not math.isfinite(number) or not 0 <= number <= 1:
                return False
        probabilities = logprob["probabilities"]
        if not isinstance(probabilities, Mapping) or len(probabilities) < 2:
            return False
        probability_values = [float(item) for item in probabilities.values()]
        if any(not math.isfinite(item) or item < 0 for item in probability_values):
            return False
        if not math.isclose(sum(probability_values), 1.0, abs_tol=1e-6):
            return False
    except (KeyError, TypeError, ValueError):
        return False
    return True


def _valid_shard(
    path: Path, session: PlannedSession, identity_sha256: str
) -> bool:
    if not path.is_file():
        return False
    try:
        rows = list(read_jsonl(path))
        if len(rows) != len(session.queries):
            return False
        for turn_index, (row, query) in enumerate(zip(rows, session.queries), start=1):
            if (
                str(row["session_key"]) != session.session_key
                or int(row["turn_index"]) != turn_index
                or str(row["query_id"]) != str(query["query_id"])
                or str(row["doc_id"]) != session.doc_id
                or str(row["scoring_identity_sha256"]) != identity_sha256
                or not _valid_trace(row["query_trace"], "query")
                or not _valid_trace(row["session_trace"], "session")
            ):
                return False
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
        return False
    return True


def _retrieval_values(hits: Sequence[Mapping[str, Any]]) -> tuple[tuple[str, ...], tuple[float, ...]]:
    doc_ids: list[str] = []
    scores: list[float] = []
    for hit in hits:
        document = hit.get("document")
        if not isinstance(document, Mapping) or not str(document.get("doc_id", "")).strip():
            raise ValueError("Vector-store hit is missing document.doc_id")
        score = float(hit["score"])
        if not math.isfinite(score):
            raise ValueError("Vector-store hit score must be finite")
        doc_ids.append(str(document["doc_id"]))
        scores.append(score)
    return tuple(doc_ids), tuple(scores)


def _record(
    *,
    session: PlannedSession,
    query: Mapping[str, Any],
    turn_index: int,
    query_trace: Any,
    session_trace: Any,
    retrieved_doc_ids: tuple[str, ...],
    retrieval_scores: tuple[float, ...],
    identity_sha256: str,
) -> dict[str, Any]:
    query_value = _json_value(query_trace)
    session_value = _json_value(session_trace)
    if _contains_truth_field(query_value) or _contains_truth_field(session_value):
        raise ValueError("Offline truth must not appear inside Judge traces")
    return {
        "query_id": str(query["query_id"]),
        "query_text": str(query["query_text"]),
        "doc_id": session.doc_id,
        "membership_label": session.membership_label,
        "partition": session.partition,
        "traffic_type": session.traffic_type,
        "attack_type": session.attack_type,
        "session_key": session.session_key,
        "session_index": session.session_index,
        "turn_index": turn_index,
        "session_length": len(session.queries),
        "variant_type": str(query.get("variant_type", "generated")),
        "query_index": int(query.get("query_index", turn_index)),
        "retrieved_doc_ids": list(retrieved_doc_ids),
        "retrieval_scores": list(retrieval_scores),
        "query_trace": query_value,
        "session_trace": session_value,
        "scoring_identity_sha256": identity_sha256,
    }


def run_judge_benchmark(
    *,
    sessions: Sequence[PlannedSession],
    judge: Any,
    store: Any,
    top_k: int,
    paths: JudgeBenchmarkPaths,
    identity: Mapping[str, Any],
    allowed_partitions: tuple[str, ...],
    allow_frozen_test: bool = False,
) -> dict[str, Any]:
    partition = paths.partition.strip().lower()
    normalized_allowed = tuple(value.strip().lower() for value in allowed_partitions)
    if partition == "test" and not allow_frozen_test:
        raise ValueError(f"Progressive Judge benchmark forbids test partition: {paths.partition}")
    if partition != "test" and partition not in normalized_allowed:
        raise ValueError(f"Progressive Judge benchmark forbids test partition: {paths.partition}")
    if "test" in normalized_allowed:
        raise ValueError("Progressive Judge allowed partitions must exclude test")
    if isinstance(top_k, bool) or not isinstance(top_k, int) or top_k <= 0:
        raise ValueError("top_k must be a positive integer")

    normalized_identity = _json_value(identity)
    if normalized_identity.get("partition") != partition:
        raise ValueError("Judge benchmark identity partition does not match output paths")
    if any(session.partition != partition for session in sessions):
        raise ValueError("Planned session partition does not match output paths")
    identity_sha256 = canonical_identity_sha256(normalized_identity)

    if paths.run_manifest.exists():
        manifest = _load_manifest(paths.run_manifest)
        if (
            manifest.get("identity") != normalized_identity
            or manifest.get("identity_sha256") != identity_sha256
        ):
            raise ValueError("Existing Judge benchmark identity does not match")
    else:
        write_json_atomic(
            paths.run_manifest,
            {
                "schema_version": 1,
                "identity": normalized_identity,
                "identity_sha256": identity_sha256,
            },
        )

    completed = 0
    skipped = 0
    invalid = 0
    for session in sessions:
        shard = paths.shard(session.session_key)
        if _valid_shard(shard, session, identity_sha256):
            skipped += 1
            continue
        if shard.exists():
            invalid += 1
        rows: list[dict[str, Any]] = []
        recent_turns: list[SessionTurn] = []
        for turn_index, query in enumerate(session.queries, start=1):
            query_text = str(query["query_text"])
            hits = store.search(query_text, top_k)
            retrieved_doc_ids, retrieval_scores = _retrieval_values(hits)
            query_trace = judge.evaluate_query(
                query=query_text, session_id=session.session_key
            )
            session_trace = judge.evaluate_session(
                query=query_text,
                session_id=session.session_key,
                recent_turns=tuple(recent_turns),
                retrieved_doc_ids=retrieved_doc_ids,
                retrieval_scores=retrieval_scores,
                min_session_queries=3,
            )
            rows.append(
                _record(
                    session=session,
                    query=query,
                    turn_index=turn_index,
                    query_trace=query_trace,
                    session_trace=session_trace,
                    retrieved_doc_ids=retrieved_doc_ids,
                    retrieval_scores=retrieval_scores,
                    identity_sha256=identity_sha256,
                )
            )
            recent_turns.append(
                SessionTurn(
                    turn_id=turn_index,
                    timestamp=float(turn_index),
                    query=query_text,
                    query_risk_score=0.0,
                    query_risk_class="NONE",
                    retrieved_doc_ids=retrieved_doc_ids,
                    retrieval_scores=retrieval_scores,
                    recommended_level="UNUSED",
                    applied_level="UNUSED",
                )
            )
        write_jsonl_atomic(shard, rows)
        completed += 1

    compacted: list[dict[str, Any]] = []
    for session in sessions:
        shard = paths.shard(session.session_key)
        if not _valid_shard(shard, session, identity_sha256):
            raise ValueError(f"Incomplete Judge benchmark shard: {session.session_key}")
        compacted.extend(read_jsonl(shard))
    write_jsonl_atomic(paths.judge_records, compacted)
    summary = {
        "schema_version": 1,
        "partition": partition,
        "session_count": len(sessions),
        "query_count": len(compacted),
        "completed_session_count": completed,
        "skipped_session_count": skipped,
        "invalid_session_count": invalid,
        "judge_records_sha256": sha256_file(paths.judge_records),
        "scoring_identity_sha256": identity_sha256,
    }
    write_json_atomic(paths.benchmark_summary, summary)
    return summary


__all__ = [
    "JudgeBenchmarkPaths",
    "canonical_identity_sha256",
    "load_verified_judge_records",
    "run_judge_benchmark",
]


def _select_sessions(
    sessions: Sequence[PlannedSession],
    *,
    max_sessions: int | None,
    session_keys: tuple[str, ...],
) -> tuple[PlannedSession, ...]:
    if max_sessions is not None and session_keys:
        raise ValueError("max_sessions and session_keys are mutually exclusive")
    if len(session_keys) != len(set(session_keys)):
        raise ValueError("session_keys contains duplicates")
    if session_keys:
        by_key = {session.session_key: session for session in sessions}
        unknown = [key for key in session_keys if key not in by_key]
        if unknown:
            raise ValueError(f"Unknown session keys for selected partition: {unknown}")
        return tuple(by_key[key] for key in session_keys)
    if max_sessions is not None:
        if isinstance(max_sessions, bool) or max_sessions <= 0:
            raise ValueError("max_sessions must be a positive integer")
        return tuple(sessions[:max_sessions])
    return tuple(sessions)


def run_partition_judge_benchmark(
    *,
    project_root: Path,
    source_run_id: str,
    query_bank_id: str,
    dataset_id: str,
    split_path: Path,
    partition: str,
    output_root: Path,
    attack_config: Any,
    judge_config: Any,
    max_sessions: int | None = None,
    session_keys: tuple[str, ...] = (),
    allow_frozen_test: bool = False,
) -> dict[str, Any]:
    """Load the frozen Query Bank stack and run one non-test Judge benchmark."""
    from miaguard.attack_pattern_library import AttackPatternLibrary
    from miaguard.data import vector_store_path
    from miaguard.model_client import create_model_client
    from miaguard.progressive_judge import ProgressiveJudge
    from miaguard.vector_store import UnifiedVectorStore

    from .sessions import plan_partition_sessions
    from .storage import QueryBank, QueryBankPaths
    from .threshold_split import load_threshold_split

    if allow_frozen_test:
        if partition != "test" or "test" in judge_config.allowed_partitions:
            raise ValueError("Frozen test scoring requires test only and a train/validation Judge config")
    else:
        judge_config.validate_partition(partition)
    root = project_root.resolve()
    bank = QueryBank.load(QueryBankPaths(root, query_bank_id, dataset_id))
    split = load_threshold_split(split_path, bank)
    sessions = plan_partition_sessions(bank, split, partition, target_turns=5)
    sessions = _select_sessions(
        sessions,
        max_sessions=max_sessions,
        session_keys=session_keys,
    )

    client = create_model_client(attack_config, root)
    client.validate_models()
    store = UnifiedVectorStore.load(
        vector_store_path(root, source_run_id, dataset_id), client
    )
    library = AttackPatternLibrary.load(judge_config.manifest_path)
    judge = ProgressiveJudge(
        judge_config,
        client,
        attack_config.generation_model,
        library,
    )
    identity = {
        "schema_version": 1,
        "partition": partition,
        "query_bank": {
            "bank_id": bank.bank_id,
            "dataset_id": bank.dataset_id,
            "queries_sha256": bank.sha256,
        },
        "split_id": str(split["split_id"]),
        "split_file_sha256": sha256_file(split_path),
        "source_run_id": source_run_id,
        "model_configuration": _json_value(attack_config),
        "progressive_judge_configuration": _json_value(judge_config),
        "pattern_library": {
            "version": library.version,
            "patterns": {
                pattern_id: pattern.version
                for pattern_id, pattern in library.patterns.items()
            },
        },
        "logprob_labels": list(judge_config.logprob_labels),
        "logprob_anchors": list(judge_config.logprob_anchors),
        "logprob_scoring": judge_config.logprob_scoring,
        "session_planning": {
            "version": "all_accepted_balanced_sessions_v1",
            "target_turns": 5,
            "minimum_turns": 3,
            "max_sessions": max_sessions,
            "selection_mode": "explicit_keys" if session_keys else (
                "prefix_limit" if max_sessions is not None else "all"
            ),
            "selected_session_keys": list(session_keys),
        },
    }
    return run_judge_benchmark(
        sessions=sessions,
        judge=judge,
        store=store,
        top_k=attack_config.top_k,
        paths=JudgeBenchmarkPaths(output_root.resolve(), partition),
        identity=identity,
        allowed_partitions=judge_config.allowed_partitions,
        allow_frozen_test=allow_frozen_test,
    )


__all__.extend(("_select_sessions", "run_partition_judge_benchmark"))
