from miaguard.query_bank.incremental_benign_judge import (
    select_incremental_benign_sessions,
    select_unscored_sessions,
)
from miaguard.query_bank.sessions import PlannedSession


def _session(
    key: str,
    traffic_type: str,
    query_ids: tuple[str, ...],
) -> PlannedSession:
    return PlannedSession(
        session_key=key,
        partition="train",
        doc_id="doc-1",
        membership_label=1,
        traffic_type=traffic_type,
        attack_type="benign" if traffic_type == "benign" else "ia",
        session_index=1,
        queries=tuple({"query_id": query_id} for query_id in query_ids),
    )


def test_select_incremental_benign_sessions_keeps_new_and_context_sessions() -> None:
    sessions = (
        _session("retained", "benign", ("old-1", "old-2", "old-3")),
        _session("new", "benign", ("new-1", "new-2", "new-3")),
        _session("mixed", "benign", ("old-4", "old-5", "new-4")),
        _session("attack", "attack", ("new-5", "new-6", "new-7")),
    )

    selected = select_incremental_benign_sessions(
        sessions, prior_query_ids={"old-1", "old-2", "old-3", "old-4", "old-5"}
    )

    assert [session.session_key for session in selected] == ["new", "mixed"]
    assert sum(len(session.queries) for session in selected) == 6


def test_select_unscored_sessions_excludes_exact_completed_session_keys() -> None:
    sessions = (
        _session("retained", "benign", ("old-1", "old-2", "old-3")),
        _session("new", "benign", ("new-1", "new-2", "new-3")),
        _session("attack", "attack", ("attack-1", "attack-2", "attack-3")),
    )

    selected = select_unscored_sessions(sessions, completed_session_keys={"new"})

    assert [session.session_key for session in selected] == ["retained", "attack"]
