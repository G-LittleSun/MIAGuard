from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from miaguard.defense import DefenseDecision, PreparedRAGRequest
from miaguard.query_bank.sessions import PlannedSession
from miaguard.query_bank.threshold_scoring import (
    ThresholdScoringPaths,
    score_planned_sessions,
)
from rag_mia_data.io_utils import read_jsonl
from rag_mia_data.io_utils import write_jsonl_atomic


class _Gateway:
    def __init__(self, mode: str = "observe") -> None:
        self.config = SimpleNamespace(mode=mode)
        self.cleared: list[str] = []

    def clear_session(self, session_id: str) -> None:
        self.cleared.append(session_id)


class _Guard:
    def __init__(self, gateway: _Gateway) -> None:
        self.detector = gateway
        self.calls: list[tuple[str, str]] = []

    def prepare(self, query: str, session_id: str) -> PreparedRAGRequest:
        self.calls.append((query, session_id))
        turn = len([call for call in self.calls if call[1] == session_id])
        query_score = turn / 10
        session_score = 0.0 if turn < 3 else 0.6
        total_score = max(query_score, session_score)
        assessment = {
            "query_detection": {
                "risk_score": query_score,
                "risk_class": "WEAK",
                "status": "ok",
            },
            "session_detection": {
                "risk_score": session_score,
                "risk_class": "WEAK" if session_score else "NONE",
                "status": "ok" if turn >= 3 else "insufficient_history",
            },
            "aggregation": {"total_risk_score": total_score},
            "latency_ms": {
                "query_detector": 1.0,
                "session_detector": 2.0,
                "total_defense": 3.0,
            },
        }
        decision = DefenseDecision(
            query_risk=query_score,
            session_risk=session_score,
            total_risk=total_score,
            risk_level="low",
            reason_codes=(),
            access_action="allow",
            query_risk_class="WEAK",
            session_risk_class="WEAK" if session_score else "NONE",
            two_stage_assessment=assessment,
        )
        return PreparedRAGRequest(
            contexts=["context"],
            retrieved_doc_ids=["retrieved-1"],
            retrieval_scores=[0.9],
            decision=decision,
            decision_latency_ms=4.0,
        )


def _session(name: str, query_count: int = 3) -> PlannedSession:
    return PlannedSession(
        session_key=name,
        partition="train",
        doc_id="doc-1",
        membership_label=1,
        traffic_type="attack",
        attack_type="ia",
        session_index=1,
        queries=tuple(
            {
                "query_id": f"{name}-q{index}",
                "query_text": f"query {index}",
            }
            for index in range(1, query_count + 1)
        ),
    )


def test_scoring_writes_complete_shards_and_resumes(tmp_path: Path) -> None:
    paths = ThresholdScoringPaths(tmp_path, "train")
    gateway = _Gateway()
    guard = _Guard(gateway)
    sessions = (_session("session-a"), _session("session-b"))
    identity = {"partition": "train", "query_bank_sha256": "a" * 64}

    first = score_planned_sessions(sessions, guard, gateway, paths, identity)
    second = score_planned_sessions(sessions, guard, gateway, paths, identity)

    assert first["completed_session_count"] == 2
    assert first["skipped_session_count"] == 0
    assert second["completed_session_count"] == 0
    assert second["skipped_session_count"] == 2
    assert len(guard.calls) == 6
    assert gateway.cleared == ["session-a", "session-b"]
    rows = list(read_jsonl(paths.risk_records))
    assert [row["turn_index"] for row in rows] == [1, 2, 3, 1, 2, 3]
    assert rows[2]["total_risk_score"] == 0.6
    assert rows[0]["variant_type"] == "generated"
    assert rows[0]["session_length"] == 3


def test_invalid_existing_shard_is_rerun(tmp_path: Path) -> None:
    paths = ThresholdScoringPaths(tmp_path, "train")
    gateway = _Gateway()
    guard = _Guard(gateway)
    session = _session("session-a")
    identity = {"partition": "train", "query_bank_sha256": "a" * 64}
    score_planned_sessions((session,), guard, gateway, paths, identity)
    shard = paths.shard("session-a")
    shard.write_text('{"broken": true}\n', encoding="utf-8")

    result = score_planned_sessions((session,), guard, gateway, paths, identity)

    assert result["completed_session_count"] == 1
    assert result["invalid_shard_count"] == 1
    assert len(guard.calls) == 6


def test_shard_from_a_different_scoring_identity_is_rerun(tmp_path: Path) -> None:
    paths = ThresholdScoringPaths(tmp_path, "train")
    gateway = _Gateway()
    guard = _Guard(gateway)
    session = _session("session-a")
    identity = {"partition": "train", "query_bank_sha256": "a" * 64}
    score_planned_sessions((session,), guard, gateway, paths, identity)
    shard = paths.shard("session-a")
    rows = list(read_jsonl(shard))
    rows[0]["scoring_identity_sha256"] = "0" * 64
    write_jsonl_atomic(shard, rows)

    result = score_planned_sessions((session,), guard, gateway, paths, identity)

    assert result["invalid_shard_count"] == 1
    assert result["completed_session_count"] == 1
    assert len(guard.calls) == 6


def test_identity_mismatch_and_non_observe_mode_are_rejected(tmp_path: Path) -> None:
    paths = ThresholdScoringPaths(tmp_path, "train")
    gateway = _Gateway()
    guard = _Guard(gateway)
    session = _session("session-a")
    score_planned_sessions(
        (session,), guard, gateway, paths, {"partition": "train", "version": 1}
    )

    with pytest.raises(ValueError, match="identity"):
        score_planned_sessions(
            (session,), guard, gateway, paths, {"partition": "train", "version": 2}
        )
    with pytest.raises(ValueError, match="observe"):
        score_planned_sessions(
            (session,),
            _Guard(_Gateway("enforce")),
            _Gateway("enforce"),
            ThresholdScoringPaths(tmp_path / "other", "train"),
            {"partition": "train"},
        )
