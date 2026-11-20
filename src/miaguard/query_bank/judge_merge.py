from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from typing import Any, Mapping, Sequence

from .sessions import PlannedSession


def scoring_identity_core(identity: Mapping[str, Any]) -> dict[str, Any]:
    """Return the score-producing identity, excluding session-selection metadata."""
    core = deepcopy(dict(identity))
    core.pop("session_planning", None)
    return core


def merge_partition_records(
    sessions: Sequence[PlannedSession],
    record_sources: Sequence[Sequence[Mapping[str, Any]]],
) -> list[dict[str, Any]]:
    """Validate disjoint full-session coverage and order rows by the frozen plan."""
    planned = {session.session_key: session for session in sessions}
    if len(planned) != len(sessions):
        raise ValueError("Planned session keys are not unique")
    source_by_session: dict[str, int] = {}
    rows_by_session: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for source_index, source in enumerate(record_sources):
        for row in source:
            session_key = str(row["session_key"])
            if session_key not in planned:
                raise ValueError(f"Record belongs to an unplanned session: {session_key}")
            prior_source = source_by_session.setdefault(session_key, source_index)
            if prior_source != source_index:
                raise ValueError(f"Session appears in multiple sources: {session_key}")
            rows_by_session[session_key].append(row)
    missing = [key for key in planned if key not in rows_by_session]
    if missing:
        raise ValueError(f"Merged records are missing planned sessions: {missing[:3]}")

    merged: list[dict[str, Any]] = []
    for session in sessions:
        rows = rows_by_session[session.session_key]
        if len(rows) != len(session.queries):
            raise ValueError(f"Session length mismatch: {session.session_key}")
        ordered = sorted(rows, key=lambda row: int(row["turn_index"]))
        for turn_index, (row, query) in enumerate(
            zip(ordered, session.queries, strict=True), start=1
        ):
            if (
                str(row["query_id"]) != str(query["query_id"])
                or str(row["doc_id"]) != session.doc_id
                or str(row["partition"]) != session.partition
                or int(row["turn_index"]) != turn_index
                or int(row["session_length"]) != len(session.queries)
            ):
                raise ValueError(f"Record disagrees with planned session: {session.session_key}")
            merged.append(dict(row))
    return merged


__all__ = ["merge_partition_records", "scoring_identity_core"]
