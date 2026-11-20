from __future__ import annotations

import math
from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np
import pandas as pd


SCORE_HEADS = ("rubric", "logprob")
ATTACK_TYPES = ("direct_rag_mia", "s2_mia", "masked_mia", "ia")


def _score(row: Mapping[str, Any], stage: str, head: str) -> float:
    try:
        value = float(row[f"{stage}_trace"][head]["score"])
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError(f"Invalid {stage}/{head} score") from error
    if not math.isfinite(value) or not 0.0 <= value <= 1.0:
        raise ValueError(f"Invalid {stage}/{head} score")
    return value


def _status(row: Mapping[str, Any], stage: str) -> str:
    try:
        value = str(row[f"{stage}_trace"]["statuses"]["overall"])
    except (KeyError, TypeError) as error:
        raise ValueError(f"Missing {stage} status") from error
    if not value:
        raise ValueError(f"Missing {stage} status")
    return value


def _validate_records(records: Sequence[Mapping[str, Any]]) -> None:
    if not records:
        raise ValueError("Judge score analysis requires records")
    required = {
        "query_id",
        "doc_id",
        "session_key",
        "turn_index",
        "session_length",
        "partition",
        "traffic_type",
        "attack_type",
        "membership_label",
        "scoring_identity_sha256",
        "query_trace",
        "session_trace",
    }
    keys: set[tuple[str, str, int]] = set()
    partitions: set[str] = set()
    identities: set[str] = set()
    sessions: dict[str, list[Mapping[str, Any]]] = {}
    for row in records:
        missing = required.difference(row)
        if missing:
            raise ValueError(f"Judge record is missing fields: {sorted(missing)}")
        key = (
            str(row["query_id"]),
            str(row["session_key"]),
            int(row["turn_index"]),
        )
        if key in keys:
            raise ValueError(f"Duplicate Judge score record: {key}")
        keys.add(key)
        partitions.add(str(row["partition"]))
        identities.add(str(row["scoring_identity_sha256"]))
        sessions.setdefault(str(row["session_key"]), []).append(row)
        traffic_type = str(row["traffic_type"])
        attack_type = str(row["attack_type"])
        if traffic_type not in {"benign", "attack"}:
            raise ValueError(f"Invalid traffic type: {traffic_type}")
        if (traffic_type == "benign") != (attack_type == "benign"):
            raise ValueError("Judge record traffic and attack labels disagree")
        if traffic_type == "attack" and attack_type not in ATTACK_TYPES:
            raise ValueError(f"Unsupported attack type: {attack_type}")
        for stage in ("query", "session"):
            _status(row, stage)
            for head in SCORE_HEADS:
                _score(row, stage, head)
    if len(partitions) != 1:
        raise ValueError("Judge records mix partitions")
    if len(identities) != 1:
        raise ValueError("Judge records mix scoring identity")
    for session_key, rows in sessions.items():
        if len({str(row["doc_id"]) for row in rows}) != 1:
            raise ValueError(f"Session mixes document IDs: {session_key}")
        if len({str(row["traffic_type"]) for row in rows}) != 1:
            raise ValueError(f"Session mixes traffic types: {session_key}")
        if len({str(row["attack_type"]) for row in rows}) != 1:
            raise ValueError(f"Session mixes attack types: {session_key}")
        turns = sorted(int(row["turn_index"]) for row in rows)
        if turns != list(range(1, len(rows) + 1)):
            raise ValueError(f"Session turns must be contiguous: {session_key}")
        lengths = {int(row["session_length"]) for row in rows}
        if lengths != {len(rows)}:
            raise ValueError(f"Session length disagrees with records: {session_key}")


def build_score_table(
    records: Sequence[Mapping[str, Any]],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    rows = list(records)
    _validate_records(rows)
    expanded: list[dict[str, Any]] = []
    excluded = 0
    unavailable_scores = {head: Counter() for head in SCORE_HEADS}
    for source in rows:
        session_status = _status(source, "session")
        available = session_status == "ok"
        for head in SCORE_HEADS:
            x1 = _score(source, "query", head)
            x2_raw = _score(source, "session", head)
            if not available:
                excluded += 1
                unavailable_scores[head][f"{x2_raw:.12g}"] += 1
            expanded.append(
                {
                    "query_id": str(source["query_id"]),
                    "doc_id": str(source["doc_id"]),
                    "session_key": str(source["session_key"]),
                    "turn_index": int(source["turn_index"]),
                    "session_length": int(source["session_length"]),
                    "partition": str(source["partition"]),
                    "traffic_type": str(source["traffic_type"]),
                    "attack_type": str(source["attack_type"]),
                    "label": int(str(source["traffic_type"]) == "attack"),
                    "membership_label": int(source["membership_label"]),
                    "head": head,
                    "x1": x1,
                    "x2_raw": x2_raw,
                    "x2_observed": x2_raw if available else np.nan,
                    "x2_filled": x2_raw if available else 0.0,
                    "session_score_available": available,
                    "query_status": _status(source, "query"),
                    "session_status": session_status,
                    "scoring_identity_sha256": str(
                        source["scoring_identity_sha256"]
                    ),
                }
            )
    table = pd.DataFrame.from_records(expanded)
    availability = (
        table.groupby("turn_index", sort=True)["session_score_available"]
        .mean()
        .to_dict()
    )
    audit = {
        "schema_version": 1,
        "partition": str(table["partition"].iloc[0]),
        "scoring_identity_sha256": str(
            table["scoring_identity_sha256"].iloc[0]
        ),
        "source_record_count": len(rows),
        "long_form_row_count": len(table),
        "unique_query_count": int(table["query_id"].nunique()),
        "unique_document_count": int(table["doc_id"].nunique()),
        "unique_session_count": int(table["session_key"].nunique()),
        "heads": list(SCORE_HEADS),
        "traffic_counts": {
            str(key): int(value)
            for key, value in Counter(
                str(row["traffic_type"]) for row in rows
            ).items()
        },
        "attack_counts": {
            str(key): int(value)
            for key, value in Counter(
                str(row["attack_type"]) for row in rows
            ).items()
        },
        "session_score_availability_by_turn": {
            str(int(key)): float(value) for key, value in availability.items()
        },
        "default_session_scores_excluded": excluded,
        "unavailable_raw_score_frequencies": {
            head: dict(counter) for head, counter in unavailable_scores.items()
        },
        "invalid_record_count": 0,
    }
    return table, audit


__all__ = ["ATTACK_TYPES", "SCORE_HEADS", "build_score_table"]
