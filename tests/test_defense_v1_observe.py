from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from miaguard.defense import GuardedRAG
from miaguard.frozen_risk_scorer import FrozenRiskScorer
from miaguard.progressive_judge import EvidencePacket, LogprobScore, ProgressiveJudgeTrace, RubricScore, ScreeningResult
from miaguard.two_stage_gateway import TwoStageGateway, load_defense_v1_observe_config, load_two_stage_config


class Store:
    def search(self, query: str, top_k: int):
        return [{"score": .9, "document": {"doc_id": "d1", "text": "full primary"}},
                {"score": .8, "document": {"doc_id": "d2", "text": "full secondary"}}][:top_k]


def trace(stage: str, score: float, status: str = "ok") -> ProgressiveJudgeTrace:
    return ProgressiveJudgeTrace(stage, ScreeningResult("NO_ATTACK", (), (), False), EvidencePacket(()),
                                 RubricScore(score, 80, "HIGH", (), ()),
                                 LogprobScore(score, {"A": 1-score, "B": score}, (.1, .5, .9)),
                                 {"overall": status}, {"total": 3.0})


class Judge:
    def __init__(self, query_status: str = "ok", session_status: str = "ok") -> None:
        self.query_status = query_status
        self.session_status = session_status
        self.query_calls = 0
        self.session_calls = 0

    def evaluate_query(self, **kwargs):
        self.query_calls += 1
        return trace("query", .8, self.query_status)

    def evaluate_session(self, **kwargs):
        self.session_calls += 1
        return trace("session", .9, self.session_status)


def gateway(mode: str, judge: Judge) -> TwoStageGateway:
    base = load_two_stage_config(Path(__file__).resolve().parents[1] / "configs/defense/two_stage_disabled.yaml")
    config = replace(base, mode=mode, window_size=5, min_session_queries=3, session_evaluation_interval=1)
    scorer = FrozenRiskScorer("logprob", "test-hash", (2., 2.), -1., {"0.01": .8, "0.05": .8})
    return TwoStageGateway(config, query_detector=judge, session_detector=judge,
                           frozen_scorer=scorer, query_only_threshold=.75, fused_threshold=.8)


def test_disabled_does_not_call_judge() -> None:
    judge = Judge()
    prepared = GuardedRAG(Store(), gateway("disabled", judge), 2).prepare("normal", "s")
    assert (judge.query_calls, judge.session_calls) == (0, 0)
    assert prepared.contexts == ["full primary", "full secondary"]


def test_observe_query_only_then_fusion_preserves_context() -> None:
    judge = Judge()
    guard = GuardedRAG(Store(), gateway("observe", judge), 2)
    prepared = [guard.prepare(f"probe {i}", "s") for i in range(3)]
    assert (judge.query_calls, judge.session_calls) == (3, 1)
    assert [item.decision.two_stage_assessment["frozen_risk"]["risk_source"] for item in prepared] == ["query_only", "query_only", "fusion"]
    assert all(item.contexts == ["full primary", "full secondary"] for item in prepared)
    assert all(item.decision.access_action == "allow" for item in prepared)
    assert all(item.decision.access_level == "L4" for item in prepared)
    assert prepared[2].decision.two_stage_assessment["frozen_risk"]["score"] == gateway("observe", Judge()).frozen_scorer.score(.8, .9)
    assert prepared[2].decision.two_stage_assessment["frozen_risk"]["query_trace_ref"].startswith("sha256:")


def test_session_error_falls_back_and_query_error_does_not_become_low_risk() -> None:
    judge = Judge(session_status="error")
    guard = GuardedRAG(Store(), gateway("observe", judge), 2)
    result = [guard.prepare(f"q{i}", "s") for i in range(3)][-1]
    assert result.decision.two_stage_assessment["frozen_risk"]["status"] == "session_error"
    assert result.decision.two_stage_assessment["frozen_risk"]["risk_source"] == "query_only"
    assert result.contexts == ["full primary", "full secondary"]
    bad = GuardedRAG(Store(), gateway("observe", Judge(query_status="error")), 2).prepare("q", "s")
    assert bad.decision.two_stage_assessment["frozen_risk"]["risk_source"] == "error"
    assert bad.decision.two_stage_assessment["frozen_risk"]["score"] is None
    assert bad.decision.access_action == "allow"


def test_saved_traces_recompute_exact_fusion_score() -> None:
    saved = []
    judge = Judge()
    active = gateway("observe", judge)
    active.trace_sink = saved.append
    guard = GuardedRAG(Store(), active, 2)
    for index in range(3):
        final = guard.prepare(f"q{index}", "s")
    assert len(saved) == 4
    query = saved[-2].risk.score
    session = saved[-1].risk.score
    assert final.decision.two_stage_assessment["frozen_risk"]["score"] == active.frozen_scorer.score(query, session)
    assert final.decision.two_stage_assessment["frozen_risk"]["query_trace_ref"] == saved[-2].trace_ref


def test_observe_config_binds_frozen_artifacts() -> None:
    root = Path(__file__).resolve().parents[1]
    bound = load_defense_v1_observe_config(root / "configs/defense/defense_v1_observe.yaml", root)
    assert bound.gateway.mode == "observe"
    assert (bound.gateway.window_size, bound.gateway.min_session_queries, bound.gateway.session_evaluation_interval) == (5, 3, 1)
    assert bound.scorer.head == "logprob"
    assert bound.query_only_threshold > 0
    assert bound.fused_threshold == bound.scorer.thresholds["0.01"]
