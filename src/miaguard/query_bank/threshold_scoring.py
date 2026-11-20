from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, is_dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from rag_mia_data.io_utils import (
    read_jsonl,
    sha256_file,
    write_json_atomic,
    write_jsonl_atomic,
)

from .sessions import PlannedSession


@dataclass(frozen=True)
class ThresholdScoringPaths:
    root: Path
    partition: str

    @property
    def partition_root(self) -> Path:
        return self.root / self.partition

    @property
    def work(self) -> Path:
        return self.partition_root / ".work"

    @property
    def risk_records(self) -> Path:
        return self.partition_root / "risk_records.jsonl"

    @property
    def run_manifest(self) -> Path:
        return self.partition_root / "run_manifest.json"

    @property
    def score_summary(self) -> Path:
        return self.partition_root / "score_summary.json"

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


def _canonical_sha256(value: Any) -> str:
    payload = json.dumps(
        _json_value(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def scoring_identity(
    bank: Any,
    split: Mapping[str, Any],
    partition: str,
    gateway_config: Any,
    scorer_config: Any,
    pattern_library_version: str,
    *,
    source_run_id: str,
    attack_config: Any,
    target_turns: int = 5,
    session_planner_version: str = "all_accepted_balanced_sessions_v1",
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "partition": partition,
        "query_bank": {
            "bank_id": str(bank.bank_id),
            "dataset_id": str(bank.dataset_id),
            "queries_sha256": str(bank.sha256),
        },
        "split_id": str(split["split_id"]),
        "split_manifest_sha256": _canonical_sha256(split),
        "split_query_bank": _json_value(split["query_bank"]),
        "gateway_config": _json_value(gateway_config),
        "scorer_config": _json_value(scorer_config),
        "pattern_library_version": str(pattern_library_version),
        "source_run_id": str(source_run_id),
        "attack_config": _json_value(attack_config),
        "session_planning": {
            "version": session_planner_version,
            "accepted_queries_only": True,
            "grouping_fields": [
                "partition",
                "doc_id",
                "traffic_type",
                "attack_type",
            ],
            "target_turns": target_turns,
            "minimum_turns": 3,
        },
    }


def _load_manifest(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("Scoring run manifest must be a mapping")
    return value


def _valid_shard(
    path: Path,
    session: PlannedSession,
    identity_sha256: str,
) -> bool:
    if not path.is_file():
        return False
    try:
        rows = list(read_jsonl(path))
        if len(rows) != len(session.queries):
            return False
        for turn_index, (row, query) in enumerate(
            zip(rows, session.queries), start=1
        ):
            if (
                str(row["session_key"]) != session.session_key
                or int(row["turn_index"]) != turn_index
                or str(row["query_id"]) != str(query["query_id"])
                or str(row["doc_id"]) != session.doc_id
                or str(row["attack_type"]) != session.attack_type
                or str(row["traffic_type"]) != session.traffic_type
                or str(row["scoring_identity_sha256"]) != identity_sha256
            ):
                return False
            score = float(row["total_risk_score"])
            if not 0.0 <= score <= 1.0:
                return False
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
        return False
    return True


def _risk_record(
    session: PlannedSession,
    query: Mapping[str, Any],
    turn_index: int,
    prepared: Any,
    identity_sha256: str,
) -> dict[str, Any]:
    decision = prepared.decision
    assessment = decision.two_stage_assessment
    if not isinstance(assessment, Mapping):
        raise ValueError("Observe scoring requires a two-stage assessment")
    query_detection = assessment["query_detection"]
    session_detection = assessment["session_detection"]
    aggregation = assessment["aggregation"]
    latency = assessment["latency_ms"]
    return {
        "query_id": str(query["query_id"]),
        "scoring_identity_sha256": identity_sha256,
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
        "query_text": str(query["query_text"]),
        "query_risk_score": float(query_detection["risk_score"]),
        "session_risk_score": float(session_detection["risk_score"]),
        "total_risk_score": float(aggregation["total_risk_score"]),
        "query_risk_class": str(query_detection["risk_class"]),
        "session_risk_class": str(session_detection["risk_class"]),
        "query_status": str(query_detection["status"]),
        "session_status": str(session_detection["status"]),
        "retrieved_doc_ids": list(prepared.retrieved_doc_ids),
        "retrieval_scores": [float(value) for value in prepared.retrieval_scores],
        "latency_ms": {
            "query_detector": float(latency["query_detector"]),
            "session_detector": float(latency["session_detector"]),
            "total_defense": float(latency["total_defense"]),
            "prepare": float(prepared.decision_latency_ms),
        },
    }


def score_planned_sessions(
    sessions: Sequence[PlannedSession],
    guard: Any,
    gateway: Any,
    paths: ThresholdScoringPaths,
    identity: Mapping[str, Any],
) -> dict[str, Any]:
    if gateway.config.mode != "observe":
        raise ValueError("Threshold scoring requires observe mode")
    normalized_identity = _json_value(identity)
    identity_sha256 = _canonical_sha256(normalized_identity)
    if normalized_identity.get("partition") != paths.partition:
        raise ValueError("Scoring identity partition does not match output paths")
    if any(session.partition != paths.partition for session in sessions):
        raise ValueError("Planned session partition does not match output paths")

    if paths.run_manifest.exists():
        existing = _load_manifest(paths.run_manifest)
        if (
            existing.get("identity") != normalized_identity
            or existing.get("identity_sha256") != identity_sha256
        ):
            raise ValueError("Existing scoring run identity does not match")
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
        try:
            for turn_index, query in enumerate(session.queries, start=1):
                prepared = guard.prepare(
                    str(query["query_text"]),
                    session.session_key,
                )
                rows.append(
                    _risk_record(
                        session,
                        query,
                        turn_index,
                        prepared,
                        identity_sha256,
                    )
                )
            write_jsonl_atomic(shard, rows)
            completed += 1
        finally:
            gateway.clear_session(session.session_key)

    compacted: list[dict[str, Any]] = []
    for session in sessions:
        shard = paths.shard(session.session_key)
        if not _valid_shard(shard, session, identity_sha256):
            raise ValueError(f"Incomplete scoring shard: {session.session_key}")
        compacted.extend(read_jsonl(shard))
    write_jsonl_atomic(paths.risk_records, compacted)
    summary = {
        "schema_version": 1,
        "partition": paths.partition,
        "session_count": len(sessions),
        "query_count": len(compacted),
        "completed_session_count": completed,
        "skipped_session_count": skipped,
        "invalid_shard_count": invalid,
        "risk_records_sha256": sha256_file(paths.risk_records),
        "scoring_identity_sha256": identity_sha256,
    }
    write_json_atomic(paths.score_summary, summary)
    return summary


__all__ = [
    "ThresholdScoringPaths",
    "score_planned_sessions",
    "scoring_identity",
]


def run_partition_threshold_scoring(
    project_root: Path,
    source_run_id: str,
    query_bank_id: str,
    dataset_id: str,
    split_path: Path,
    partition: str,
    output_root: Path,
    attack_config: Any,
    gateway_config: Any,
    scorer_config: Any,
) -> dict[str, Any]:
    """Load the production scoring stack and score one frozen partition."""
    from miaguard.attack_pattern_library import AttackPatternLibrary
    from miaguard.data import vector_store_path
    from miaguard.defense import GuardedRAG
    from miaguard.direct_scorer import (
        DirectQueryRiskDetector,
        DirectSessionRiskDetector,
    )
    from miaguard.model_client import create_model_client
    from miaguard.two_stage_gateway import TwoStageGateway
    from miaguard.vector_store import UnifiedVectorStore

    from .sessions import plan_partition_sessions
    from .storage import QueryBank, QueryBankPaths
    from .threshold_split import load_threshold_split

    if gateway_config.mode != "observe":
        raise ValueError("Threshold scoring requires observe mode")
    root = project_root.resolve()
    bank = QueryBank.load(QueryBankPaths(root, query_bank_id, dataset_id))
    split = load_threshold_split(split_path, bank)
    sessions = plan_partition_sessions(bank, split, partition, target_turns=5)

    client = create_model_client(attack_config, root)
    client.validate_models()
    store = UnifiedVectorStore.load(
        vector_store_path(root, source_run_id, dataset_id), client
    )
    library = AttackPatternLibrary.load(scorer_config.manifest_path)
    gateway = TwoStageGateway(
        gateway_config,
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
    identity = scoring_identity(
        bank,
        split,
        partition,
        gateway_config,
        scorer_config,
        library.version,
        source_run_id=source_run_id,
        attack_config=attack_config,
        target_turns=5,
    )
    return score_planned_sessions(
        sessions,
        guard,
        gateway,
        ThresholdScoringPaths(output_root.resolve(), partition),
        identity,
    )


__all__.append("run_partition_threshold_scoring")
