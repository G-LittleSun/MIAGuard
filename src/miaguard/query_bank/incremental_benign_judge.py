from __future__ import annotations

from typing import Iterable

from .sessions import PlannedSession


def select_incremental_benign_sessions(
    sessions: Iterable[PlannedSession],
    *,
    prior_query_ids: set[str],
) -> tuple[PlannedSession, ...]:
    """Select benign sessions containing at least one query absent from a prior bank."""
    return tuple(
        session
        for session in sessions
        if session.traffic_type == "benign"
        and any(str(query["query_id"]) not in prior_query_ids for query in session.queries)
    )


def select_unscored_sessions(
    sessions: Iterable[PlannedSession],
    *,
    completed_session_keys: set[str],
) -> tuple[PlannedSession, ...]:
    """Return planned sessions absent from a verified completed-session set."""
    return tuple(
        session
        for session in sessions
        if session.session_key not in completed_session_keys
    )


__all__ = ["select_incremental_benign_sessions", "select_unscored_sessions"]
