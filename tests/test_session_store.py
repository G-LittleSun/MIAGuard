from miaguard.risk_types import SessionTurn
from miaguard.session_store import SessionStore


def _turn(query: str) -> SessionTurn:
    return SessionTurn(
        turn_id=0,
        timestamp=0.0,
        query=query,
        query_risk_score=0.0,
        query_risk_class="NONE",
        retrieved_doc_ids=("doc-1",),
        retrieval_scores=(0.9,),
        recommended_level="L0",
        applied_level="L0",
    )


def test_session_store_preserves_order_and_window_size() -> None:
    store = SessionStore(window_size=2, timeout_seconds=60)

    first = store.append("session", _turn("q1"), now=1.0)
    second = store.append("session", _turn("q2"), now=2.0)
    third = store.append("session", _turn("q3"), now=3.0)

    assert (first.turn_id, second.turn_id, third.turn_id) == (1, 2, 3)
    assert [turn.query for turn in store.window("session", now=3.0)] == ["q2", "q3"]


def test_session_store_isolates_sessions_and_resets_after_timeout() -> None:
    store = SessionStore(window_size=3, timeout_seconds=10)
    store.append("session-a", _turn("a1"), now=1.0)
    store.append("session-b", _turn("b1"), now=2.0)

    assert [turn.query for turn in store.window("session-a", now=5.0)] == ["a1"]
    assert [turn.query for turn in store.window("session-b", now=5.0)] == ["b1"]
    assert store.window("session-a", now=11.0) == ()

    restarted = store.append("session-a", _turn("a2"), now=12.0)
    assert restarted.turn_id == 1
