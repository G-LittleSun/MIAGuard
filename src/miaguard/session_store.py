from __future__ import annotations

import time
from dataclasses import dataclass, replace

from .risk_types import SessionTurn


@dataclass
class _SessionState:
    turns: list[SessionTurn]
    last_activity: float
    total_turns: int


class SessionStore:
    def __init__(self, window_size: int, timeout_seconds: int) -> None:
        if window_size <= 0 or timeout_seconds <= 0:
            raise ValueError("Session window size and timeout must be positive")
        self.window_size = window_size
        self.timeout_seconds = timeout_seconds
        self._sessions: dict[str, _SessionState] = {}

    def _state(self, session_id: str, now: float) -> _SessionState | None:
        if not session_id.strip():
            raise ValueError("session_id must not be blank")
        state = self._sessions.get(session_id)
        if state is not None and now - state.last_activity >= self.timeout_seconds:
            del self._sessions[session_id]
            return None
        return state

    def window(
        self,
        session_id: str,
        *,
        now: float | None = None,
    ) -> tuple[SessionTurn, ...]:
        current = time.time() if now is None else now
        state = self._state(session_id, current)
        return tuple(state.turns) if state is not None else ()

    def append(
        self,
        session_id: str,
        turn: SessionTurn,
        *,
        now: float | None = None,
    ) -> SessionTurn:
        current = time.time() if now is None else now
        state = self._state(session_id, current)
        if state is None:
            state = _SessionState([], current, 0)
            self._sessions[session_id] = state
        stored = replace(turn, turn_id=state.total_turns + 1, timestamp=current)
        state.turns.append(stored)
        del state.turns[: -self.window_size]
        state.total_turns += 1
        state.last_activity = current
        return stored

    def turn_count(self, session_id: str, *, now: float | None = None) -> int:
        current = time.time() if now is None else now
        state = self._state(session_id, current)
        return state.total_turns if state is not None else 0

    def clear(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)


__all__ = ["SessionStore"]
