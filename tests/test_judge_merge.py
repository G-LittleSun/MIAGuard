from miaguard.query_bank.judge_merge import merge_partition_records, scoring_identity_core
from miaguard.query_bank.sessions import PlannedSession


def _session(key: str, query_ids: tuple[str, ...]) -> PlannedSession:
    return PlannedSession(
        session_key=key,
        partition="train",
        doc_id="doc-1",
        membership_label=1,
        traffic_type="benign",
        attack_type="benign",
        session_index=1,
        queries=tuple({"query_id": query_id} for query_id in query_ids),
    )


def _record(session: PlannedSession, turn: int) -> dict[str, object]:
    return {
        "session_key": session.session_key,
        "query_id": session.queries[turn - 1]["query_id"],
        "doc_id": session.doc_id,
        "partition": session.partition,
        "turn_index": turn,
        "session_length": len(session.queries),
    }


def test_merge_partition_records_requires_complete_disjoint_session_coverage() -> None:
    first = _session("first", ("q-1", "q-2", "q-3"))
    second = _session("second", ("q-4", "q-5", "q-6"))

    merged = merge_partition_records(
        (first, second),
        (
            [_record(second, 1), _record(second, 2), _record(second, 3)],
            [_record(first, 1), _record(first, 2), _record(first, 3)],
        ),
    )

    assert [row["query_id"] for row in merged] == [
        "q-1", "q-2", "q-3", "q-4", "q-5", "q-6"
    ]


def test_scoring_identity_core_ignores_only_session_selection_metadata() -> None:
    identity = {
        "query_bank": {"bank_id": "v2"},
        "session_planning": {
            "version": "all_accepted_balanced_sessions_v1",
            "selection_mode": "explicit_keys",
            "selected_session_keys": ["first"],
        },
    }

    assert scoring_identity_core(identity) == {"query_bank": {"bank_id": "v2"}}
