"""Sequential, idempotent accounting for retrieval, delivery and answer exposure."""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Any, Callable

from .defense_contracts import Evidence, OnlineRequest


def _input_sha256(request: OnlineRequest) -> str:
    payload = {
        "request_id": request.request_id,
        "session_id": request.session_id,
        "query": request.query,
        "allowed_doc_ids": None if request.allowed_doc_ids is None else sorted(request.allowed_doc_ids),
    }
    data = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ExposureEvent:
    request_id: str
    session_id: str
    input_sha256: str
    status: str
    retrieved_doc_ids: tuple[str, ...]
    delivered_evidence: tuple[Evidence, ...]
    response: str | None
    failure_reason: str | None
    referenced_parent_ids: tuple[str, ...]
    created_at: float
    finished_at: float | None
    delivery_attempted: bool
    transform_input_evidence: tuple[Evidence, ...]

    @property
    def delivered_doc_ids(self) -> tuple[str, ...]:
        return tuple(item.doc_id for item in self.delivered_evidence)

    @property
    def delivered_exposure(self) -> str:
        if any(item.kind == "raw" for item in self.delivered_evidence):
            return "raw"
        if any(item.kind == "summary" for item in self.delivered_evidence):
            return "transformed"
        return "none"

    @property
    def transform_input_doc_ids(self) -> tuple[str, ...]:
        return tuple(item.doc_id for item in self.transform_input_evidence)

    def to_dict(self) -> dict[str, Any]:
        def evidence_record(item: Evidence) -> dict[str, Any]:
            return {"doc_id": item.doc_id, "parent_doc_id": item.parent_doc_id,
                    "kind": item.kind, "score": item.score,
                    "text_sha256": hashlib.sha256(item.text.encode("utf-8")).hexdigest()}

        return {
            "request_id": self.request_id, "session_id": self.session_id,
            "input_sha256": self.input_sha256, "status": self.status,
            "retrieved_doc_ids": list(self.retrieved_doc_ids),
            "transform_input_evidence": [evidence_record(item) for item in self.transform_input_evidence],
            "delivered_evidence": [evidence_record(item) for item in self.delivered_evidence],
            "delivered_exposure": self.delivered_exposure,
            "delivery_attempted": self.delivery_attempted,
            "response": self.response, "failure_reason": self.failure_reason,
            "referenced_parent_ids": list(self.referenced_parent_ids),
            "created_at": self.created_at, "finished_at": self.finished_at,
        }


@dataclass(frozen=True)
class BeginResult:
    kind: str
    event: ExposureEvent


@dataclass(frozen=True)
class ServeResult:
    response: str | None
    status: str
    cached: bool
    event: ExposureEvent


@dataclass
class _Entry:
    request: OnlineRequest
    input_sha256: str
    created_at: float
    status: str = "pending"
    retrieved_doc_ids: tuple[str, ...] = ()
    retrieval_recorded: bool = False
    delivered_evidence: tuple[Evidence, ...] = ()
    attempted: bool = False
    transform_input_evidence: tuple[Evidence, ...] = ()
    transform_attempted: bool = False
    response: str | None = None
    failure_reason: str | None = None
    referenced_parent_ids: tuple[str, ...] = ()
    finished_at: float | None = None

    def snapshot(self) -> ExposureEvent:
        return ExposureEvent(
            self.request.request_id, self.request.session_id, self.input_sha256,
            self.status, self.retrieved_doc_ids, self.delivered_evidence,
            self.response, self.failure_reason, self.referenced_parent_ids,
            self.created_at, self.finished_at, self.attempted,
            self.transform_input_evidence,
        )


@dataclass
class _Session:
    entries: list[_Entry] = field(default_factory=list)
    pending_id: str | None = None
    last_activity: float = 0.0
    new_requests: int = 0
    retries: int = 0


class ExposureStore:
    def __init__(self, timeout_seconds: int = 1800) -> None:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self.timeout_seconds = timeout_seconds
        self._sessions: dict[str, _Session] = {}
        self._entries: dict[str, _Entry] = {}
        self.reset_events: list[dict[str, Any]] = []

    def _expire(self, session_id: str, now: float) -> None:
        session = self._sessions.get(session_id)
        if session is not None and now - session.last_activity >= self.timeout_seconds:
            for entry in session.entries:
                self._entries.pop(entry.request.request_id, None)
            self.reset_events.append({"session_id": session_id, "at": now, "prior_request_count": len(session.entries)})
            del self._sessions[session_id]

    def begin(self, request: OnlineRequest, *, now: float | None = None) -> BeginResult:
        current = time.time() if now is None else now
        self._expire(request.session_id, current)
        fingerprint = _input_sha256(request)
        existing = self._entries.get(request.request_id)
        if existing is not None:
            if existing.input_sha256 != fingerprint:
                raise ValueError("request_id was reused with different input")
            if existing.status == "pending":
                raise RuntimeError("This request is still pending")
            session = self._sessions[request.session_id]
            session.retries += 1
            session.last_activity = current
            return BeginResult("cached", existing.snapshot())
        session = self._sessions.setdefault(request.session_id, _Session(last_activity=current))
        if session.pending_id is not None:
            raise RuntimeError("A request is pending in this session")
        entry = _Entry(request, fingerprint, current)
        session.entries.append(entry)
        session.pending_id = request.request_id
        session.new_requests += 1
        session.last_activity = current
        self._entries[request.request_id] = entry
        return BeginResult("new", entry.snapshot())

    def _pending(self, request_id: str) -> _Entry:
        entry = self._entries[request_id]
        if entry.status != "pending":
            raise RuntimeError("Request is already terminal")
        return entry

    def record_retrieved(self, request_id: str, doc_ids: tuple[str, ...]) -> None:
        entry = self._pending(request_id)
        if entry.retrieval_recorded:
            raise RuntimeError("Retrieved evidence was already recorded")
        entry.retrieved_doc_ids = tuple(doc_ids)
        entry.retrieval_recorded = True

    def record_transform_attempt(self, request_id: str, evidence: tuple[Evidence, ...]) -> None:
        entry = self._pending(request_id)
        if entry.transform_attempted:
            raise RuntimeError("Transformation attempt was already recorded")
        entry.transform_input_evidence = tuple(evidence)
        entry.transform_attempted = True

    def record_attempt(self, request_id: str, evidence: tuple[Evidence, ...]) -> None:
        entry = self._pending(request_id)
        if entry.attempted:
            raise RuntimeError("Delivery attempt was already recorded")
        entry.delivered_evidence = tuple(evidence)
        entry.attempted = True

    def _finish(self, entry: _Entry, now: float) -> None:
        entry.finished_at = now
        session = self._sessions[entry.request.session_id]
        session.pending_id = None
        session.last_activity = now

    def complete(
        self, request_id: str, response: str, *,
        referenced_parent_ids: tuple[str, ...] = (), now: float | None = None,
    ) -> ExposureEvent:
        entry = self._pending(request_id)
        if not isinstance(response, str):
            raise ValueError("response must be a string")
        entry.response = response
        entry.referenced_parent_ids = tuple(referenced_parent_ids)
        entry.status = "complete"
        self._finish(entry, time.time() if now is None else now)
        return entry.snapshot()

    def fail(self, request_id: str, reason: str, *, now: float | None = None) -> ExposureEvent:
        entry = self._pending(request_id)
        if not reason.strip():
            raise ValueError("Failure reason must not be blank")
        entry.failure_reason = reason
        entry.status = "failed"
        self._finish(entry, time.time() if now is None else now)
        return entry.snapshot()

    def history(self, session_id: str, *, now: float | None = None) -> tuple[ExposureEvent, ...]:
        current = time.time() if now is None else now
        self._expire(session_id, current)
        session = self._sessions.get(session_id)
        return tuple(entry.snapshot() for entry in session.entries) if session is not None else ()

    def counters(self, session_id: str, *, now: float | None = None) -> dict[str, int]:
        current = time.time() if now is None else now
        self._expire(session_id, current)
        session = self._sessions.get(session_id)
        return {"new_requests": session.new_requests, "retries": session.retries} if session else {"new_requests": 0, "retries": 0}


def run_guarded_request(
    request: OnlineRequest,
    guard: Any,
    ledger: ExposureStore,
    answer: Callable[[Any], str],
) -> ServeResult:
    """Commit request state after an answer or explicit failure, never at lookup."""
    start = ledger.begin(request)
    if start.kind == "cached":
        return ServeResult(start.event.response, start.event.status, True, start.event)
    detector = guard.detector
    committed = False
    try:
        prepared = guard.prepare(request.query, request.session_id, allowed_doc_ids=request.allowed_doc_ids)
        ledger.record_retrieved(request.request_id, tuple(prepared.retrieved_doc_ids))
        if prepared.action_execution is None:
            raise RuntimeError("Guarded request requires the v1 action executor")
        if prepared.action_execution.transform_input_evidence:
            ledger.record_transform_attempt(request.request_id, prepared.action_execution.transform_input_evidence)
        if prepared.action_execution.applied_action not in {"deny", "unavailable"}:
            ledger.record_attempt(request.request_id, prepared.action_execution.evidence)
        response = answer(prepared)
        if hasattr(detector, "commit_session"):
            detector.commit_session(request.session_id)
            committed = True
        event = ledger.complete(request.request_id, response)
    except Exception as exc:
        ledger.fail(request.request_id, f"{type(exc).__name__}: {exc}")
        if not committed and hasattr(detector, "commit_session"):
            detector.commit_session(request.session_id)
        raise
    return ServeResult(response, "complete", False, event)


__all__ = ["BeginResult", "ExposureEvent", "ExposureStore", "ServeResult", "run_guarded_request"]
