import json
from pathlib import Path

import pytest

from miaguard.progressive_judge import (
    AttackAssessment,
    EvidencePacket,
    LogprobScore,
    ProgressiveJudgeTrace,
    RubricScore,
    ScreeningResult,
)
from miaguard.query_bank.judge_benchmark import (
    JudgeBenchmarkPaths,
    _select_sessions,
    load_verified_judge_records,
    run_judge_benchmark,
)
from miaguard.query_bank.sessions import PlannedSession
from rag_mia_data.io_utils import (
    read_jsonl,
    sha256_file,
    write_json_atomic,
    write_jsonl_atomic,
)


def _trace(stage: str, status: str = "ok") -> ProgressiveJudgeTrace:
    screening = (
        ScreeningResult(
            "DEFER_INSUFFICIENT_HISTORY", (), ("INSUFFICIENT_HISTORY",), False
        )
        if status == "insufficient_history"
        else ScreeningResult(
            "SKIP_EXPLICIT_BENIGN",
            (),
            (
                "EXPLICIT_BENIGN_PURPOSE",
                "NO_CONTRADICTORY_SUSPICIOUS_MECHANISM",
            ),
            False,
        )
    )
    return ProgressiveJudgeTrace(
        stage=stage,
        screening=screening,
        evidence=EvidencePacket(()),
        rubric=RubricScore(0.1, 10, "LOW", (), ()),
        logprob=LogprobScore(
            0.18,
            {"A": 0.8, "B": 0.15, "C": 0.05},
            (0.1, 0.5, 0.9),
        ),
        statuses={"overall": status},
        latencies_ms={"total": 1.0},
    )


def _attack_trace(stage: str) -> ProgressiveJudgeTrace:
    return ProgressiveJudgeTrace(
        stage=stage,
        screening=ScreeningResult(
            "REVIEW", ("ia",), ("MULTI_TURN_FACT_PROBES",), False
        ),
        evidence=EvidencePacket(
            (
                AttackAssessment(
                    "ia",
                    "LIKELY",
                    True,
                    False,
                    (),
                    ("REPEATED_FACT_PROBES",),
                    (),
                ),
            )
        ),
        rubric=RubricScore(0.8, 80, "CRITICAL", ("ia",), ("REPEATED_FACT_PROBES",)),
        logprob=LogprobScore(0.82, {"A": 0.05, "B": 0.15, "C": 0.8}, (0.1, 0.5, 0.9)),
        statuses={"overall": "ok"},
        latencies_ms={"total": 1.0},
    )


def _no_attack_cue_trace(stage: str) -> ProgressiveJudgeTrace:
    return ProgressiveJudgeTrace(
        stage=stage,
        screening=ScreeningResult(
            "SKIP_NO_ATTACK_CUE", (), (), False
        ),
        evidence=EvidencePacket(()),
        rubric=RubricScore(0.05, 5, "LOW", (), ()),
        logprob=LogprobScore(
            0.124,
            {"A": 0.95, "B": 0.04, "C": 0.01},
            (0.1, 0.5, 0.9),
        ),
        statuses={"overall": "ok", "detail": "skipped_no_attack_cue"},
        latencies_ms={"total": 1.0},
    )


class _Judge:
    def __init__(self) -> None:
        self.calls = []

    def evaluate_query(self, **kwargs):
        self.calls.append(("query", kwargs))
        return _trace("query")

    def evaluate_session(self, **kwargs):
        self.calls.append(("session", kwargs))
        status = "insufficient_history" if len(kwargs["recent_turns"]) < 2 else "ok"
        return _trace("session", status)


class _Store:
    def __init__(self) -> None:
        self.calls = []

    def search(self, query: str, top_k: int):
        self.calls.append((query, top_k))
        return [
            {
                "score": 0.9,
                "document": {"doc_id": "retrieved-1", "text": "private text"},
            }
        ]


def _session(name: str, doc_id: str) -> PlannedSession:
    return PlannedSession(
        session_key=name,
        partition="validation",
        doc_id=doc_id,
        membership_label=1,
        traffic_type="attack",
        attack_type="ia",
        session_index=1,
        queries=tuple(
            {"query_id": f"{name}-q{index}", "query_text": f"query {index}"}
            for index in range(1, 4)
        ),
    )


def test_select_sessions_uses_explicit_keys_in_requested_order() -> None:
    sessions = (_session("session-a", "doc-a"), _session("session-b", "doc-b"))

    selected = _select_sessions(
        sessions,
        max_sessions=None,
        session_keys=("session-b", "session-a"),
    )

    assert [session.session_key for session in selected] == ["session-b", "session-a"]


@pytest.mark.parametrize("keys", [("missing",), ("session-a", "session-a")])
def test_select_sessions_rejects_unknown_or_duplicate_keys(keys) -> None:
    with pytest.raises(ValueError):
        _select_sessions(
            (_session("session-a", "doc-a"),),
            max_sessions=None,
            session_keys=keys,
        )


def test_select_sessions_rejects_limit_with_explicit_keys() -> None:
    with pytest.raises(ValueError, match="mutually exclusive"):
        _select_sessions(
            (_session("session-a", "doc-a"),),
            max_sessions=1,
            session_keys=("session-a",),
        )


def _kwargs(tmp_path: Path, judge: _Judge):
    return {
        "sessions": (_session("session-a", "doc-a"), _session("session-b", "doc-b")),
        "judge": judge,
        "store": _Store(),
        "top_k": 4,
        "paths": JudgeBenchmarkPaths(tmp_path / "runs", "validation"),
        "identity": {"partition": "validation", "prompt_version": "v2"},
        "allowed_partitions": ("train", "validation"),
    }


def _keys(value):
    if isinstance(value, dict):
        return set(value).union(*(_keys(item) for item in value.values()), set())
    if isinstance(value, list):
        return set().union(*(_keys(item) for item in value), set())
    return set()


def test_benchmark_rejects_test_before_any_model_call(tmp_path: Path) -> None:
    judge = _Judge()

    with pytest.raises(ValueError, match="forbids test"):
        run_judge_benchmark(
            sessions=(),
            judge=judge,
            store=_Store(),
            top_k=4,
            paths=JudgeBenchmarkPaths(tmp_path / "runs", "test"),
            identity={"partition": "test", "prompt_version": "v2"},
            allowed_partitions=("train", "validation"),
        )

    assert judge.calls == []


def test_benchmark_resumes_complete_session_shards(tmp_path: Path) -> None:
    judge = _Judge()
    kwargs = _kwargs(tmp_path, judge)

    first = run_judge_benchmark(**kwargs)
    second = run_judge_benchmark(**kwargs)

    assert first["completed_session_count"] == 2
    assert second["skipped_session_count"] == 2
    assert len(judge.calls) == 12
    rows = list(read_jsonl(kwargs["paths"].judge_records))
    assert [row["query_id"] for row in rows] == [
        "session-a-q1",
        "session-a-q2",
        "session-a-q3",
        "session-b-q1",
        "session-b-q2",
        "session-b-q3",
    ]
    assert rows[0]["attack_type"] == "ia"
    assert "attack_type" not in _keys(rows[0]["query_trace"])


def test_benchmark_recomputes_invalid_shard(tmp_path: Path) -> None:
    judge = _Judge()
    kwargs = _kwargs(tmp_path, judge)
    run_judge_benchmark(**kwargs)
    kwargs["paths"].shard("session-a").write_text('{"broken":true}\n', encoding="utf-8")

    result = run_judge_benchmark(**kwargs)

    assert result["invalid_session_count"] == 1
    assert result["completed_session_count"] == 1
    assert len(judge.calls) == 18


def test_benchmark_refuses_identity_mismatch(tmp_path: Path) -> None:
    judge = _Judge()
    kwargs = _kwargs(tmp_path, judge)
    run_judge_benchmark(**kwargs)

    with pytest.raises(ValueError, match="identity"):
        run_judge_benchmark(
            **{**kwargs, "identity": {"partition": "validation", "prompt_version": "v3"}}
        )


def test_benchmark_accepts_predicted_attack_type_inside_evidence_trace(tmp_path: Path) -> None:
    class _AttackJudge(_Judge):
        def evaluate_query(self, **kwargs):
            self.calls.append(("query", kwargs))
            return _attack_trace("query")

        def evaluate_session(self, **kwargs):
            self.calls.append(("session", kwargs))
            return _attack_trace("session")

    judge = _AttackJudge()
    kwargs = _kwargs(tmp_path, judge)

    result = run_judge_benchmark(**kwargs)

    assert result["completed_session_count"] == 2


def test_benchmark_resumes_no_attack_cue_trace(tmp_path: Path) -> None:
    class _NoAttackCueJudge(_Judge):
        def evaluate_query(self, **kwargs):
            self.calls.append(("query", kwargs))
            return _no_attack_cue_trace("query")

        def evaluate_session(self, **kwargs):
            self.calls.append(("session", kwargs))
            return _no_attack_cue_trace("session")

    judge = _NoAttackCueJudge()
    kwargs = _kwargs(tmp_path, judge)

    first = run_judge_benchmark(**kwargs)
    second = run_judge_benchmark(**kwargs)

    assert first["completed_session_count"] == 2
    assert second["skipped_session_count"] == 2
    assert second["invalid_session_count"] == 0


def test_benchmark_recomputes_shard_with_invalid_router_schema(tmp_path: Path) -> None:
    judge = _Judge()
    kwargs = _kwargs(tmp_path, judge)
    run_judge_benchmark(**kwargs)
    shard = kwargs["paths"].shard("session-a")
    rows = list(read_jsonl(shard))
    rows[0]["query_trace"]["screening"]["routing_decision"] = "LOW"
    write_jsonl_atomic(shard, rows)

    result = run_judge_benchmark(**kwargs)

    assert result["invalid_session_count"] == 1
    assert result["completed_session_count"] == 1


def test_verified_loader_returns_hash_checked_records(tmp_path: Path) -> None:
    kwargs = _kwargs(tmp_path, _Judge())
    run_judge_benchmark(**kwargs)

    records, source = load_verified_judge_records(kwargs["paths"].partition_root)

    assert records[0]["query_id"] == "session-a-q1"
    assert source["judge_records_sha256"] == sha256_file(
        kwargs["paths"].judge_records
    )
    assert source["scoring_identity_sha256"] == records[0][
        "scoring_identity_sha256"
    ]


def test_verified_loader_rejects_tampered_records(tmp_path: Path) -> None:
    kwargs = _kwargs(tmp_path, _Judge())
    run_judge_benchmark(**kwargs)
    with kwargs["paths"].judge_records.open("a", encoding="utf-8") as handle:
        handle.write("\n")

    with pytest.raises(ValueError, match="record hash"):
        load_verified_judge_records(kwargs["paths"].partition_root)


def test_verified_loader_rejects_mixed_identity(tmp_path: Path) -> None:
    kwargs = _kwargs(tmp_path, _Judge())
    run_judge_benchmark(**kwargs)
    rows = list(read_jsonl(kwargs["paths"].judge_records))
    rows[0]["scoring_identity_sha256"] = "different"
    write_jsonl_atomic(kwargs["paths"].judge_records, rows)
    summary = json.loads(
        kwargs["paths"].benchmark_summary.read_text(encoding="utf-8")
    )
    summary["judge_records_sha256"] = sha256_file(kwargs["paths"].judge_records)
    write_json_atomic(kwargs["paths"].benchmark_summary, summary)

    with pytest.raises(ValueError, match="mixed scoring identity"):
        load_verified_judge_records(kwargs["paths"].partition_root)
