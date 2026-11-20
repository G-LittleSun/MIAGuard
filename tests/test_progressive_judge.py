import inspect
import re
from pathlib import Path

import pytest
from jsonschema import ValidationError, validate

import miaguard.progressive_judge as progressive_judge_module
from miaguard.attack_pattern_library import AttackPatternLibrary
from miaguard.progressive_judge import (
    AttackAssessment,
    EvidencePacket,
    ProgressiveJudge,
    ProgressiveJudgeConfig,
    ScreeningResult,
    _case_observations,
    _session_query_statistics,
    build_detail_prompt,
    build_screening_candidate_prompt,
    build_screening_gate_prompt,
    load_progressive_judge_config,
    parse_evidence,
    parse_rubric,
    parse_screening,
    screening_candidate_json_schema,
    screening_gate_json_schema,
)
from miaguard.risk_types import SessionTurn


ROOT = Path(__file__).resolve().parents[1]


def test_session_query_statistics_distinguish_constrained_probes_from_open_questions() -> None:
    constrained = _session_query_statistics(
        (
            "Did the event happen? Please answer Yes, No, or Unknown.",
            "Was the company involved? Reply with Yes, No, or Unknown.",
            "Is the stated price correct? Answer Yes, No, or Unknown.",
        )
    )
    open_ended = _session_query_statistics(
        (
            "What was the proposed acquisition price?",
            "How much could the company pay?",
            "Why was the acquisition considered?",
        )
    )

    assert constrained == {
        "constrained_yes_no_unknown_count": 3,
        "open_ended_query_count": 0,
    }
    assert open_ended == {
        "constrained_yes_no_unknown_count": 0,
        "open_ended_query_count": 3,
    }


def test_direct_query_observations_preserve_json_escaped_quotation() -> None:
    query = (
        'Does this: "Report: Symantec May Buy Veritas Antivirus vendor may pay \\$13 '
        'billion for the storage software company." appear in the context? '
        'Answer with Yes or No.'
    )

    observations = _case_observations("query", {"query": query})

    assert observations == {
        "quoted_span_count": 1,
        "longest_quoted_span_word_count": 16,
        "mentions_context_or_evidence": True,
        "asks_presence_or_support": True,
        "requests_yes_no": True,
    }


def test_benign_fact_query_has_no_direct_membership_surface_mechanism() -> None:
    observations = _case_observations(
        "query",
        {"query": "What is the potential cost of Symantec's acquisition of Veritas?"},
    )

    assert observations["quoted_span_count"] == 0
    assert observations["longest_quoted_span_word_count"] == 0
    assert observations["mentions_context_or_evidence"] is False
    assert observations["asks_presence_or_support"] is False
    assert observations["requests_yes_no"] is False


def test_progressive_config_loads_versioned_scoring_contract() -> None:
    config = load_progressive_judge_config(
        ROOT / "configs/defense/progressive_judge_v2.yaml", ROOT
    )

    assert config.prompt_version == (
        "progressive_v2_direct_private_context_validated_codes_targeted_repair_"
        "possible_uncertainty_minimal_rubric_no_attack_cue_trusted_surface_empty_"
        "skip_ia_constrained_session_rubric_consistency_combined_repair"
        "_exclusion_sufficient_evidence_code_targeted_repair"
        "_structured_router_gate_constrained_json"
        "_single_candidate_verifier_closed_missing_codes"
        "_string_state_schema"
        "_complete_array_branches"
        )
    assert config.max_candidate_patterns == 2
    assert config.logprob_labels == ("A", "B", "C")
    assert config.logprob_anchors == (0.1, 0.5, 0.9)


def test_binary_logprob_v3_config_has_two_semantic_labels() -> None:
    v2 = load_progressive_judge_config(
        ROOT / "configs/defense/progressive_judge_v2.yaml", ROOT
    )
    v3 = load_progressive_judge_config(
        ROOT / "configs/defense/progressive_judge_v3_binary_logprob.yaml", ROOT
    )

    assert v2.logprob_labels == ("A", "B", "C")
    assert v2.logprob_anchors == (0.1, 0.5, 0.9)
    assert v3.logprob_labels == ("A", "B")
    assert v3.logprob_anchors == ()


def test_qwen_progressive_config_allows_two_complete_detail_assessments() -> None:
    baseline = load_progressive_judge_config(
        ROOT / "configs/defense/progressive_judge_v2.yaml", ROOT
    )
    qwen = load_progressive_judge_config(
        ROOT / "configs/defense/progressive_judge_v2_qwen2_5_7b.yaml", ROOT
    )

    assert qwen.detail_max_tokens == 256
    assert qwen.prompt_version == baseline.prompt_version
    assert qwen.screening_max_tokens == baseline.screening_max_tokens
    assert qwen.rubric_max_tokens == baseline.rubric_max_tokens
    assert qwen.logprob_labels == baseline.logprob_labels
    assert qwen.logprob_anchors == baseline.logprob_anchors


def test_router_gate_discloses_mechanism_boundaries_without_attack_selection() -> None:
    config = load_progressive_judge_config(
        ROOT / "configs/defense/progressive_judge_v2.yaml", ROOT
    )
    library = AttackPatternLibrary.load(config.manifest_path)

    prompt = build_screening_gate_prompt(
        stage="query",
        case={"query": "Does this passage appear?"},
        config=config,
        library=library,
    )

    assert "membership_label" not in prompt
    assert "first stage of a security Router" in prompt
    assert "Do not select an attack type" in prompt
    assert "private-corpus fact" in prompt
    assert "creative" in prompt.lower()
    assert "invented ending" in prompt
    assert "ordinary reading discussion" in prompt.lower()
    assert "SKIP_NO_ATTACK_CUE" in prompt
    assert "suspicious, conflicting, or uncertain" in prompt
    assert "<trusted_case_observations_json>" in prompt
    assert '"quoted_span_count": 0' in prompt
    assert "merely refers to a report or article" in prompt
    assert "candidate_attack_types" not in prompt


def test_session_router_gate_requires_constrained_diverse_ia_probes() -> None:
    config = load_progressive_judge_config(
        ROOT / "configs/defense/progressive_judge_v2.yaml", ROOT
    )
    library = AttackPatternLibrary.load(config.manifest_path)
    case = {
        "recent_turns": [
            {"turn_id": 1, "query": "Answer Yes, No, or Unknown.", "retrieved_doc_ids": ["d1"]},
            {"turn_id": 2, "query": "Reply Yes, No, or Unknown.", "retrieved_doc_ids": ["d1"]},
        ],
        "current_turn": {
            "turn_id": 3,
            "query": "Respond Yes, No, or Unknown.",
            "retrieved_doc_ids": ["d1"],
        },
        "session_statistics": {
            "turn_number": 3,
            "repeated_top1_count": 3,
            "top1_concentration": 1.0,
            "constrained_yes_no_unknown_count": 3,
            "open_ended_query_count": 0,
        },
    }

    prompt = build_screening_gate_prompt(
        stage="session", case=case, config=config, library=library
    )

    assert '"constrained_yes_no_unknown_count": 3' in prompt
    assert "same-fact paraphrases" in prompt
    assert "Ordinary reading discussion" in prompt
    assert "repeated retrieval alone" in prompt


def test_router_candidate_discloses_summaries_but_not_full_patterns() -> None:
    config = load_progressive_judge_config(
        ROOT / "configs/defense/progressive_judge_v2.yaml", ROOT
    )
    library = AttackPatternLibrary.load(config.manifest_path)

    prompt = build_screening_candidate_prompt(
        stage="query",
        case={"query": "Does this passage appear?"},
        config=config,
        library=library,
    )

    assert library.patterns["direct_rag_mia"].summary in prompt
    assert "# Strong indicators" not in prompt
    assert "second stage of a security Router" in prompt
    assert "one or two distinct values" in prompt
    assert "direct_rag_mia" in prompt
    assert "candidate_attack_types" in prompt


def test_detail_discloses_only_selected_patterns() -> None:
    config = load_progressive_judge_config(
        ROOT / "configs/defense/progressive_judge_v2.yaml", ROOT
    )
    library = AttackPatternLibrary.load(config.manifest_path)
    screening = ScreeningResult(
        "REVIEW",
        ("ia",),
        ("MULTI_TURN_FACT_PROBES", "REPEATED_TOP1_DOCUMENT"),
        False,
    )

    prompt = build_detail_prompt(
        stage="session",
        case={
            "recent_turns": [],
            "current_turn": {"query": "What happened in the report?"},
        },
        screening=screening,
        config=config,
        library=library,
    )

    assert "# Security objective" in prompt
    assert "SYSTEMATIC_ENTITY_PROBING" in prompt
    assert "REQUESTS_EXACT_CONTINUATION" not in prompt
    assert "screening result is only a routing proposal" in prompt
    assert "LIKELY requires all required conditions" in prompt
    assert "POSSIBLE allows required conditions to be met or missing" in prompt
    assert "POSSIBLE always requires supporting evidence and no benign exclusion" in prompt
    assert "UNLIKELY requires a benign exclusion" in prompt
    assert "exclusion_applies" in prompt
    assert "missing_condition_codes" in prompt
    assert 'Top-level JSON must be {"assessments": [...]}' in prompt
    assert "required_conditions_met=false and exclusion_applies=false" in prompt
    assert "exclusion_applies=true requires one or more counter_evidence_codes" in prompt
    assert "Do not copy screening observed_feature_codes" in prompt
    assert '"INSUFFICIENT_EVIDENCE"' in prompt
    assert "missing_condition_codes may use concise descriptive" in prompt
    assert "<trusted_case_observations_json>" in prompt
    assert '"quoted_span_count": 0' in prompt
    assert "not an attack label" in prompt


def test_direct_detail_prompt_treats_supplied_quotation_as_observed_fact() -> None:
    config = load_progressive_judge_config(
        ROOT / "configs/defense/progressive_judge_v2.yaml", ROOT
    )
    library = AttackPatternLibrary.load(config.manifest_path)
    screening = ScreeningResult(
        "REVIEW",
        ("direct_rag_mia",),
        ("EXACT_PASSAGE_INPUT", "CORPUS_PRESENCE_CHECK", "CONSTRAINED_YES_NO"),
        False,
    )

    prompt = build_detail_prompt(
        stage="query",
        case={
            "query": (
                'Does this: "Report: Symantec May Buy Veritas." appear in the '
                "context? Answer with Yes or No."
            )
        },
        screening=screening,
        config=config,
        library=library,
    )

    assert '"quoted_span_count": 1' in prompt
    assert '"mentions_context_or_evidence": true' in prompt
    assert '"asks_presence_or_support": true' in prompt
    assert '"requests_yes_no": true' in prompt
    assert "do not claim that no quotation or passage was supplied" in prompt
    assert "denotes the private RAG context" in prompt


@pytest.mark.parametrize("partition", ["test", "TEST"])
def test_progressive_config_never_enables_test(partition: str) -> None:
    config = ProgressiveJudgeConfig.for_test(ROOT)

    with pytest.raises(ValueError, match="test partition"):
        config.validate_partition(partition)


def test_router_gate_and_candidate_schemas_enforce_the_two_stage_contract() -> None:
    config = ProgressiveJudgeConfig.for_test(ROOT)
    validate(
        {"mechanism_decision": "REVIEW_REQUIRED"}, screening_gate_json_schema()
    )
    with pytest.raises(ValidationError):
        validate(
            {"mechanism_decision": "REVIEW"}, screening_gate_json_schema()
        )

    candidate_schema = screening_candidate_json_schema(
        allowed_pattern_ids=config.query_pattern_ids,
        max_candidate_patterns=config.max_candidate_patterns,
    )
    validate(
        {
            "candidate_attack_types": ["s2_mia"],
            "observed_feature_codes": ["SOURCE_LIKE_PREFIX"],
        },
        candidate_schema,
    )
    with pytest.raises(ValidationError):
        validate(
            {
                "candidate_attack_types": [],
                "observed_feature_codes": ["SOURCE_LIKE_PREFIX"],
            },
            candidate_schema,
        )


class _ProgressiveClient:
    def __init__(self, json_responses, label_probabilities):
        self.json_responses = list(json_responses)
        self.label_probabilities = label_probabilities
        self.json_prompts = []
        self.gate_prompts = []
        self.json_schemas = []
        self.logprob_prompts = []

    def generate_json(self, model, prompt, **kwargs):
        if "Router Gate task" in prompt:
            self.gate_prompts.append(prompt)
            if self.json_responses and isinstance(self.json_responses[0], dict):
                legacy_decision = self.json_responses[0].get("routing_decision")
                if legacy_decision in {
                    "SKIP_NO_ATTACK_CUE",
                    "SKIP_EXPLICIT_BENIGN",
                } and not self.json_responses[0].get("candidate_attack_types"):
                    self.json_responses.pop(0)
                    return {"mechanism_decision": legacy_decision}
            return {"mechanism_decision": "REVIEW_REQUIRED"}
        self.json_prompts.append(prompt)
        self.json_schemas.append(kwargs.get("json_schema"))
        if (
            "Verifier candidate task" in prompt
            and self.json_responses
            and isinstance(self.json_responses[0], dict)
            and isinstance(self.json_responses[0].get("assessments"), list)
        ):
            match = re.search(r'<attack_pattern id="([a-z0-9_]+)">', prompt)
            assert match is not None
            requested = match.group(1)
            assessments = self.json_responses[0]["assessments"]
            for index, assessment in enumerate(assessments):
                if assessment.get("attack_type") == requested:
                    response = assessments.pop(index)
                    if not assessments:
                        self.json_responses.pop(0)
                    return response
        response = self.json_responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response

    def candidate_label_probabilities(self, model, prompt, **kwargs):
        self.logprob_prompts.append(prompt)
        return dict(self.label_probabilities)


def _judge(client) -> ProgressiveJudge:
    config = ProgressiveJudgeConfig.for_test(ROOT)
    return ProgressiveJudge(config, client, "judge-model")


def _binary_judge(client) -> ProgressiveJudge:
    config = load_progressive_judge_config(
        ROOT / "configs/defense/progressive_judge_v3_binary_logprob.yaml", ROOT
    )
    return ProgressiveJudge(config, client, "judge-model")


def _turn(turn_id: int, query: str, doc_id: str = "doc-1") -> SessionTurn:
    return SessionTurn(
        turn_id=turn_id,
        timestamp=float(turn_id),
        query=query,
        query_risk_score=0.99,
        query_risk_class="STRONG",
        retrieved_doc_ids=(doc_id,),
        retrieval_scores=(0.9,),
        recommended_level="L3",
        applied_level="L3",
    )


def _attack_responses(attack_type: str = "s2_mia"):
    evidence_code = (
        "REPEATED_FACT_PROBES" if attack_type == "ia" else "SOURCE_PREFIX_PROVIDED"
    )
    return [
        {
            "routing_decision": "REVIEW",
            "candidate_attack_types": [attack_type],
            "observed_feature_codes": [
                "MULTI_TURN_FACT_PROBES"
                if attack_type == "ia"
                else "SOURCE_LIKE_PREFIX"
            ],
            "candidate_ambiguity": False,
        },
        {
            "assessments": [
                {
                    "attack_type": attack_type,
                    "verdict": "LIKELY",
                    "required_conditions_met": True,
                    "exclusion_applies": False,
                    "missing_condition_codes": [],
                    "supporting_evidence_codes": [evidence_code],
                    "counter_evidence_codes": [],
                }
            ]
        },
        {
            "risk_score": 72,
            "risk_band": "HIGH",
            "judge_confidence": 0.81,
            "suspected_attack_types": [attack_type],
            "evidence_codes": [evidence_code],
        },
    ]


def test_query_trace_reuses_one_evidence_packet_for_both_heads() -> None:
    client = _ProgressiveClient(
        _attack_responses(),
        {"A": 0.05, "B": 0.25, "C": 0.70},
    )

    trace = _judge(client).evaluate_query(
        query="Complete this source prefix", session_id="s1"
    )

    assert trace.rubric.score == pytest.approx(0.72)
    assert trace.logprob.score == pytest.approx(0.76)
    assert trace.evidence.assessments[0].attack_type == "s2_mia"
    assert len(client.json_prompts) == 3
    assert len(client.logprob_prompts) == 1
    assert "risk_score" not in client.logprob_prompts[0]
    assert "Complete this source prefix" not in client.json_prompts[-1]
    assert "Complete this source prefix" not in client.logprob_prompts[0]
    assert "<untrusted_case_json>" not in client.json_prompts[-1]
    assert "<untrusted_case_json>" not in client.logprob_prompts[0]
    assert "<shared_evidence_json>" in client.json_prompts[-1]
    assert "<shared_evidence_json>" in client.logprob_prompts[0]
    assert "<trusted_case_observations_json>" not in client.json_prompts[-1]
    assert "<trusted_case_observations_json>" not in client.logprob_prompts[0]


def test_binary_logprob_score_is_normalized_attack_probability() -> None:
    client = _ProgressiveClient(
        _attack_responses(),
        {"A": 0.2, "B": 0.8},
    )

    trace = _binary_judge(client).evaluate_query(
        query="Complete this source prefix", session_id="s1"
    )

    assert trace.logprob.score == pytest.approx(0.8)
    assert trace.logprob.probabilities == {"A": 0.2, "B": 0.8}
    assert trace.logprob.anchors == ()
    assert "A=BENIGN" in client.logprob_prompts[0]
    assert "B=ATTACK" in client.logprob_prompts[0]
    assert "validated evidence" in client.logprob_prompts[0]


def test_low_screening_skips_detail_but_scores_both_heads() -> None:
    client = _ProgressiveClient(
        [
            {
                "routing_decision": "SKIP_EXPLICIT_BENIGN",
                "candidate_attack_types": [],
                "observed_feature_codes": [
                    "EXPLICIT_BENIGN_PURPOSE",
                    "NO_CONTRADICTORY_SUSPICIOUS_MECHANISM",
                ],
                "candidate_ambiguity": False,
            },
            {
                "risk_score": 8,
                "risk_band": "LOW",
                "judge_confidence": 0.9,
                "suspected_attack_types": [],
                "evidence_codes": [],
            },
        ],
        {"A": 0.9, "B": 0.08, "C": 0.02},
    )

    trace = _judge(client).evaluate_query(query="What is the headline?", session_id="s1")

    assert trace.evidence.assessments == ()
    assert trace.statuses["detail"] == "skipped_explicit_benign"
    assert len(client.json_prompts) == 1
    assert len(client.gate_prompts) == 1
    assert len(client.logprob_prompts) == 1


def test_no_attack_cue_skips_detail_but_scores_both_heads() -> None:
    client = _ProgressiveClient(
        [
            {
                "routing_decision": "SKIP_NO_ATTACK_CUE",
                "candidate_attack_types": [],
                "observed_feature_codes": [],
            },
            {"risk_score": 5, "suspected_attack_types": []},
        ],
        {"A": 0.95, "B": 0.04, "C": 0.01},
    )

    trace = _judge(client).evaluate_query(
        query="What is the potential cost of the acquisition?", session_id="s1"
    )

    assert trace.evidence.assessments == ()
    assert trace.statuses["detail"] == "skipped_no_attack_cue"
    assert trace.rubric.score == pytest.approx(0.05)
    assert trace.logprob.score == pytest.approx(0.124)
    assert len(client.json_prompts) == 1
    assert len(client.gate_prompts) == 1
    assert len(client.logprob_prompts) == 1


def test_router_requires_review_for_ambiguous_or_non_explicitly_benign_input() -> None:
    client = _ProgressiveClient(
        [
            {
                "routing_decision": "SKIP_EXPLICIT_BENIGN",
                "candidate_attack_types": ["s2_mia"],
                "observed_feature_codes": ["SOURCE_LIKE_PREFIX"],
                "candidate_ambiguity": False,
            },
            {
                "routing_decision": "REVIEW",
                "candidate_attack_types": ["s2_mia", "direct_rag_mia"],
                "observed_feature_codes": ["SOURCE_LIKE_PREFIX"],
                "candidate_ambiguity": True,
            },
            {
                "assessments": [
                    {
                        "attack_type": "s2_mia",
                        "verdict": "UNLIKELY",
                        "required_conditions_met": False,
                        "exclusion_applies": True,
                            "missing_condition_codes": [],
                        "supporting_evidence_codes": [],
                        "counter_evidence_codes": ["CREATIVE_WRITING_REQUEST"],
                    },
                    {
                        "attack_type": "direct_rag_mia",
                        "verdict": "UNLIKELY",
                        "required_conditions_met": False,
                        "exclusion_applies": True,
                            "missing_condition_codes": [],
                        "supporting_evidence_codes": [],
                        "counter_evidence_codes": ["PUBLIC_DOCUMENT_CHECK"],
                    },
                ]
            },
            {
                "risk_score": 12,
                "risk_band": "LOW",
                "judge_confidence": 0.8,
                "suspected_attack_types": [],
                "evidence_codes": [],
            },
        ],
        {"A": 0.9, "B": 0.08, "C": 0.02},
    )

    trace = _judge(client).evaluate_query(query="Continue this passage", session_id="s1")

    assert trace.screening.routing_decision == "REVIEW"
    assert trace.screening.candidate_ambiguity is True
    assert "FORMAT REPAIR" in client.json_prompts[1]


def test_router_derives_candidate_ambiguity_from_candidate_count() -> None:
    config = ProgressiveJudgeConfig.for_test(ROOT)

    single = parse_screening(
        {
            "routing_decision": "REVIEW",
            "candidate_attack_types": ["s2_mia"],
            "observed_feature_codes": ["SOURCE_LIKE_PREFIX"],
            "candidate_ambiguity": True,
        },
        allowed_pattern_ids=config.query_pattern_ids,
        max_candidate_patterns=config.max_candidate_patterns,
    )
    double = parse_screening(
        {
            "routing_decision": "REVIEW",
            "candidate_attack_types": ["s2_mia", "direct_rag_mia"],
            "observed_feature_codes": ["SOURCE_LIKE_PREFIX"],
        },
        allowed_pattern_ids=config.query_pattern_ids,
        max_candidate_patterns=config.max_candidate_patterns,
    )

    assert single.candidate_ambiguity is False
    assert double.candidate_ambiguity is True


def test_router_accepts_no_attack_cue_for_ordinary_fact_query() -> None:
    config = ProgressiveJudgeConfig.for_test(ROOT)

    result = parse_screening(
        {
            "routing_decision": "SKIP_NO_ATTACK_CUE",
            "candidate_attack_types": [],
            "observed_feature_codes": [],
        },
        allowed_pattern_ids=config.query_pattern_ids,
        max_candidate_patterns=config.max_candidate_patterns,
    )

    assert result.routing_decision == "SKIP_NO_ATTACK_CUE"
    assert result.candidate_attack_types == ()
    assert result.observed_feature_codes == ()
    assert result.candidate_ambiguity is False


@pytest.mark.parametrize(
    ("candidate_attack_types", "observed_feature_codes", "error"),
    [
        (
            ["ia"],
            [],
            "SKIP_NO_ATTACK_CUE cannot contain candidates",
        ),
        (
            [],
            ["CONTEXT_GROUNDED_CONTINUATION"],
            "SKIP_NO_ATTACK_CUE requires empty observed_feature_codes",
        ),
    ],
)
def test_router_rejects_inconsistent_no_attack_cue(
    candidate_attack_types, observed_feature_codes, error
) -> None:
    config = ProgressiveJudgeConfig.for_test(ROOT)

    with pytest.raises(ValueError, match=error):
        parse_screening(
            {
                "routing_decision": "SKIP_NO_ATTACK_CUE",
                "candidate_attack_types": candidate_attack_types,
                "observed_feature_codes": observed_feature_codes,
            },
            allowed_pattern_ids=config.query_pattern_ids,
            max_candidate_patterns=config.max_candidate_patterns,
        )


def test_inconsistent_likely_evidence_triggers_format_repair_retry() -> None:
    valid = _attack_responses()
    invalid_evidence = {
        "assessments": [
            {
                "attack_type": "s2_mia",
                "verdict": "LIKELY",
                "required_conditions_met": False,
                "exclusion_applies": True,
                "missing_condition_codes": [],
                "supporting_evidence_codes": ["SOURCE_PREFIX_PROVIDED"],
                "counter_evidence_codes": ["CREATIVE_WRITING_REQUEST"],
            }
        ]
    }
    client = _ProgressiveClient(
        [valid[0], invalid_evidence, valid[1], valid[2]],
        {"A": 0.05, "B": 0.25, "C": 0.70},
    )

    trace = _judge(client).evaluate_query(
        query="Complete this source prefix", session_id="s1"
    )

    assert trace.evidence.assessments[0].verdict == "LIKELY"
    assert "FORMAT REPAIR" in client.json_prompts[2]
    assert "Assessment s2_mia" in client.json_prompts[2]
    assert "LIKELY requires all conditions and no exclusion" in client.json_prompts[2]
    assert "<invalid_previous_json>" in client.json_prompts[2]
    assert '"exclusion_applies": true' in client.json_prompts[2]
    assert "Keep every already-valid assessment unchanged" in client.json_prompts[2]


def test_unknown_masked_evidence_code_triggers_scoped_repair_retry() -> None:
    invalid_evidence = {
        "assessments": [
            {
                "attack_type": "masked_mia",
                "verdict": "POSSIBLE",
                "required_conditions_met": False,
                "exclusion_applies": False,
                "missing_condition_codes": ["EXACT_RECOVERY_REQUEST_MISSING"],
                "supporting_evidence_codes": ["MENTIONS_CONTEXT_OR_EVIDENCE"],
                "counter_evidence_codes": [],
            }
        ]
    }
    valid_evidence = {
        "assessments": [
            {
                "attack_type": "masked_mia",
                "verdict": "LIKELY",
                "required_conditions_met": True,
                "exclusion_applies": False,
                "missing_condition_codes": [],
                "supporting_evidence_codes": [
                    "OMITTED_SOURCE_CONTENT",
                    "REQUESTS_EXACT_RECOVERY",
                ],
                "counter_evidence_codes": [],
            }
        ]
    }
    client = _ProgressiveClient(
        [
            {
                "routing_decision": "REVIEW",
                "candidate_attack_types": ["masked_mia"],
                "observed_feature_codes": ["MASKED_OR_OMITTED_SPANS"],
                "candidate_ambiguity": False,
            },
            invalid_evidence,
            valid_evidence,
            {"risk_score": 83, "suspected_attack_types": ["masked_mia"]},
        ],
        {"A": 0.02, "B": 0.08, "C": 0.90},
    )

    trace = _judge(client).evaluate_query(
        query="Recover every [Mask_n] from this source passage.", session_id="s1"
    )

    assert trace.evidence.assessments[0].supporting_evidence_codes == (
        "OMITTED_SOURCE_CONTENT",
        "REQUESTS_EXACT_RECOVERY",
    )
    repair_prompt = client.json_prompts[2]
    assert "UNKNOWN EVIDENCE CODE REPAIR" in repair_prompt
    assert "allowed_evidence_codes_json" in repair_prompt
    assert "Do not invent evidence codes" in repair_prompt
    assert repair_prompt.index("UNKNOWN EVIDENCE CODE REPAIR") > repair_prompt.index(
        "</invalid_previous_json>"
    )


def test_router_candidate_schema_is_used_for_review_selection() -> None:
    client = _ProgressiveClient(
        [
            {
                "candidate_attack_types": ["s2_mia"],
                "observed_feature_codes": ["SOURCE_LIKE_PREFIX"],
            },
            {
                "assessments": [
                    {
                        "attack_type": "s2_mia",
                        "verdict": "UNLIKELY",
                        "required_conditions_met": False,
                        "exclusion_applies": True,
                        "missing_condition_codes": [],
                        "supporting_evidence_codes": [],
                        "counter_evidence_codes": ["CREATIVE_WRITING_REQUEST"],
                    }
                ]
            },
            {"risk_score": 0, "suspected_attack_types": []},
        ],
        {"A": 0.99, "B": 0.009, "C": 0.001},
    )

    trace = _judge(client).evaluate_query(
        query="Continue this source-like prefix from Context.", session_id="s1"
    )

    assert trace.screening.routing_decision == "REVIEW"
    assert client.json_schemas[0]["properties"]["candidate_attack_types"]["minItems"] == 1
    assert len(client.gate_prompts) == 1


def test_missing_condition_codes_are_closed_per_candidate() -> None:
    config = ProgressiveJudgeConfig.for_test(ROOT)
    library = AttackPatternLibrary.load(config.manifest_path)

    packet = parse_evidence(
        {
            "assessments": [
                {
                    "attack_type": "direct_rag_mia",
                    "verdict": "POSSIBLE",
                    "required_conditions_met": False,
                    "exclusion_applies": False,
                    "missing_condition_codes": ["PRIVATE_CONTEXT_CHECK_MISSING"],
                    "supporting_evidence_codes": ["EXACT_PASSAGE_VERIFICATION"],
                    "counter_evidence_codes": [],
                }
            ]
        },
        candidate_attack_types=("direct_rag_mia",),
        library=library,
    )

    assert packet.assessments[0].missing_condition_codes == (
        "PRIVATE_CONTEXT_CHECK_MISSING",
    )


def test_single_candidate_verifier_schema_rejects_unmet_s2_without_missing_code() -> None:
    schema_factory = getattr(
        progressive_judge_module, "evidence_assessment_json_schema", None
    )
    assert callable(schema_factory)
    schema = schema_factory(
        candidate_attack_type="s2_mia",
        library=AttackPatternLibrary.load(
            ProgressiveJudgeConfig.for_test(ROOT).manifest_path
        ),
    )
    invalid = {
        "attack_type": "s2_mia",
        "verdict": "POSSIBLE",
        "required_conditions_met": False,
        "exclusion_applies": False,
        "missing_condition_codes": [],
        "supporting_evidence_codes": ["SOURCE_PREFIX_PROVIDED"],
        "counter_evidence_codes": [],
    }

    with pytest.raises(ValidationError):
        validate(invalid, schema)


def test_single_candidate_verifier_schema_uses_string_state_for_lmfe_compatibility() -> None:
    library = AttackPatternLibrary.load(ProgressiveJudgeConfig.for_test(ROOT).manifest_path)
    schema = progressive_judge_module.evidence_assessment_json_schema(
        candidate_attack_type="s2_mia", library=library
    )

    assert "assessment_state" in schema["properties"]
    assert schema["properties"]["assessment_state"]["type"] == "string"


def test_single_candidate_verifier_schema_keeps_array_types_inside_each_branch() -> None:
    library = AttackPatternLibrary.load(ProgressiveJudgeConfig.for_test(ROOT).manifest_path)
    schema = progressive_judge_module.evidence_assessment_json_schema(
        candidate_attack_type="s2_mia", library=library
    )

    for branch in schema["oneOf"]:
        for field in (
            "missing_condition_codes",
            "supporting_evidence_codes",
            "counter_evidence_codes",
        ):
            if field in branch["properties"]:
                assert branch["properties"][field]["type"] == "array"


def test_parse_evidence_rejects_missing_code_outside_candidate_vocabulary() -> None:
    library = AttackPatternLibrary.load(ProgressiveJudgeConfig.for_test(ROOT).manifest_path)
    invalid = {
        "assessments": [
            {
                "attack_type": "s2_mia",
                "verdict": "POSSIBLE",
                "required_conditions_met": False,
                "exclusion_applies": False,
                "missing_condition_codes": ["INVENTED_MISSING_CONDITION"],
                "supporting_evidence_codes": ["SOURCE_PREFIX_PROVIDED"],
                "counter_evidence_codes": [],
            }
        ]
    }

    with pytest.raises(ValueError, match="unknown missing condition code"):
        parse_evidence(
            invalid, candidate_attack_types=("s2_mia",), library=library
        )


def test_single_candidate_verifier_prompt_and_parser_are_available() -> None:
    builder = getattr(progressive_judge_module, "build_candidate_detail_prompt", None)
    parser = getattr(progressive_judge_module, "parse_evidence_assessment", None)

    assert callable(builder)
    assert callable(parser)


def test_two_router_candidates_use_two_independent_verifier_calls() -> None:
    client = _ProgressiveClient(
        [
            {
                "routing_decision": "REVIEW",
                "candidate_attack_types": ["direct_rag_mia", "s2_mia"],
                "observed_feature_codes": ["SOURCE_LIKE_PREFIX"],
            },
            {
                "attack_type": "direct_rag_mia",
                "verdict": "LIKELY",
                "required_conditions_met": True,
                "exclusion_applies": False,
                "missing_condition_codes": [],
                "supporting_evidence_codes": ["EXACT_PASSAGE_VERIFICATION"],
                "counter_evidence_codes": [],
            },
            {
                "attack_type": "s2_mia",
                "verdict": "LIKELY",
                "required_conditions_met": True,
                "exclusion_applies": False,
                "missing_condition_codes": [],
                "supporting_evidence_codes": ["SOURCE_PREFIX_PROVIDED"],
                "counter_evidence_codes": [],
            },
            {"risk_score": 70, "suspected_attack_types": ["direct_rag_mia", "s2_mia"]},
        ],
        {"A": 0.05, "B": 0.25, "C": 0.70},
    )

    trace = _judge(client).evaluate_query(
        query="Does this source passage appear in Context?", session_id="s1"
    )

    verifier_prompts = [
        prompt for prompt in client.json_prompts if "Verifier candidate task" in prompt
    ]
    assert [item.attack_type for item in trace.evidence.assessments] == [
        "direct_rag_mia",
        "s2_mia",
    ]
    assert len(verifier_prompts) == 2
    assert 'id="direct_rag_mia"' in verifier_prompts[0]
    assert 'id="s2_mia"' in verifier_prompts[1]


def test_unmet_verifier_conditions_trigger_missing_code_targeted_repair() -> None:
    client = _ProgressiveClient(
        [
            {
                "routing_decision": "REVIEW",
                "candidate_attack_types": ["s2_mia"],
                "observed_feature_codes": ["SOURCE_LIKE_PREFIX"],
            },
            {
                "attack_type": "s2_mia",
                "verdict": "POSSIBLE",
                "required_conditions_met": False,
                "exclusion_applies": False,
                "missing_condition_codes": [],
                "supporting_evidence_codes": ["SOURCE_PREFIX_PROVIDED"],
                "counter_evidence_codes": [],
            },
            {
                "attack_type": "s2_mia",
                "verdict": "POSSIBLE",
                "required_conditions_met": False,
                "exclusion_applies": False,
                "missing_condition_codes": ["CONTEXT_GROUNDED_RECOVERY_MISSING"],
                "supporting_evidence_codes": ["SOURCE_PREFIX_PROVIDED"],
                "counter_evidence_codes": [],
            },
            {"risk_score": 45, "suspected_attack_types": ["s2_mia"]},
        ],
        {"A": 0.1, "B": 0.8, "C": 0.1},
    )

    _judge(client).evaluate_query(query="Continue this prefix from Context.", session_id="s1")

    repair_prompt = client.json_prompts[2]
    assert "MISSING CONDITION CODE REPAIR" in repair_prompt
    assert "allowed_missing_condition_codes_json" in repair_prompt
    assert "do not change assessment_state" in repair_prompt


def test_unlikely_exclusion_can_omit_redundant_missing_conditions() -> None:
    config = ProgressiveJudgeConfig.for_test(ROOT)
    library = AttackPatternLibrary.load(config.manifest_path)

    packet = parse_evidence(
        {
            "assessments": [
                {
                    "attack_type": "ia",
                    "verdict": "UNLIKELY",
                    "required_conditions_met": False,
                    "exclusion_applies": True,
                    "missing_condition_codes": [],
                    "supporting_evidence_codes": [],
                    "counter_evidence_codes": ["NORMAL_FOLLOW_UP_CONVERSATION"],
                }
            ]
        },
        candidate_attack_types=("ia",),
        library=library,
    )

    assert packet.assessments[0].verdict == "UNLIKELY"
    assert packet.assessments[0].missing_condition_codes == ()
    assert packet.assessments[0].counter_evidence_codes == (
        "NORMAL_FOLLOW_UP_CONVERSATION",
    )


def test_possible_accepts_met_conditions_when_support_is_not_conclusive() -> None:
    config = ProgressiveJudgeConfig.for_test(ROOT)
    library = AttackPatternLibrary.load(config.manifest_path)

    packet = parse_evidence(
        {
            "assessments": [
                {
                    "attack_type": "ia",
                    "verdict": "POSSIBLE",
                    "required_conditions_met": True,
                    "exclusion_applies": False,
                    "missing_condition_codes": [],
                    "supporting_evidence_codes": ["REPEATED_FACT_PROBES"],
                    "counter_evidence_codes": [],
                }
            ]
        },
        candidate_attack_types=("ia",),
        library=library,
    )

    assessment = packet.assessments[0]
    assert assessment.verdict == "POSSIBLE"
    assert assessment.required_conditions_met is True
    assert assessment.missing_condition_codes == ()


def test_rubric_codes_are_derived_from_validated_evidence_packet() -> None:
    missing_code = "PRIVATE_CONTEXT_CHECK_MISSING"
    client = _ProgressiveClient(
        [
            {
                "routing_decision": "REVIEW",
                "candidate_attack_types": ["direct_rag_mia"],
                "observed_feature_codes": ["EXACT_PASSAGE_INPUT"],
            },
            {
                "assessments": [
                    {
                        "attack_type": "direct_rag_mia",
                        "verdict": "POSSIBLE",
                        "required_conditions_met": False,
                        "exclusion_applies": False,
                        "missing_condition_codes": [missing_code],
                        "supporting_evidence_codes": ["EXACT_PASSAGE_VERIFICATION"],
                        "counter_evidence_codes": [],
                    }
                ]
            },
            {
                "risk_score": 50,
                "risk_band": "AMBIGUOUS",
                "judge_confidence": 0.7,
                "suspected_attack_types": ["direct_rag_mia"],
                "evidence_codes": ["CORPUS_PRESENCE_CHECK"],
            },
            {
                "risk_score": 50,
                "risk_band": "AMBIGUOUS",
                "judge_confidence": 0.7,
                "suspected_attack_types": ["direct_rag_mia"],
                "evidence_codes": ["CORPUS_PRESENCE_CHECK"],
            },
        ],
        {"A": 0.1, "B": 0.8, "C": 0.1},
    )

    trace = _judge(client).evaluate_query(
        query='Does this: "quoted passage" appear in the context? Yes or No.',
        session_id="s1",
    )

    assert trace.rubric.evidence_codes == (
        "EXACT_PASSAGE_VERIFICATION",
        missing_code,
    )
    assert "FORMAT REPAIR" not in client.json_prompts[-1]


def test_scoring_prompts_define_semantic_risk_criteria() -> None:
    client = _ProgressiveClient(
        _attack_responses(),
        {"A": 0.05, "B": 0.25, "C": 0.70},
    )

    _judge(client).evaluate_query(query="Complete this source prefix", session_id="s1")

    rubric_prompt = client.json_prompts[-1]
    logprob_prompt = client.logprob_prompts[-1]
    assert "benign explanation is more plausible" in rubric_prompt
    assert "major required conditions" in rubric_prompt
    assert "all assessments are UNLIKELY" in rubric_prompt
    assert 'Return JSON exactly as {"risk_score": <integer 0-100>' in rubric_prompt
    assert "matching risk_band" not in rubric_prompt
    assert "judge_confidence" not in rubric_prompt
    assert "A=LOW" in logprob_prompt
    assert "explicit benign purpose" in logprob_prompt
    assert "required attack conditions" in logprob_prompt


def test_invalid_rubric_score_triggers_format_repair_retry() -> None:
    responses = _attack_responses()
    responses[-1] = {**responses[-1], "risk_score": "HIGH"}
    responses.append({**_attack_responses()[-1], "risk_score": 85, "risk_band": "CRITICAL"})
    client = _ProgressiveClient(responses, {"A": 0.1, "B": 0.2, "C": 0.7})

    trace = _judge(client).evaluate_query(query="Complete this source", session_id="s1")

    assert trace.rubric.score == pytest.approx(0.85)
    assert "FORMAT REPAIR" in client.json_prompts[-1]


def test_rubric_derives_band_from_minimal_model_output() -> None:
    evidence = EvidencePacket(
        (
            AttackAssessment(
                "direct_rag_mia",
                "LIKELY",
                True,
                False,
                (),
                ("EXACT_PASSAGE_VERIFICATION",),
                (),
            ),
        )
    )
    result = parse_rubric(
        {
            "risk_score": 75,
            "suspected_attack_types": ["direct_rag_mia"],
        },
        allowed_pattern_ids=("direct_rag_mia",),
        allowed_evidence_codes={"EXACT_PASSAGE_VERIFICATION"},
        validated_evidence_codes=("EXACT_PASSAGE_VERIFICATION",),
        evidence=evidence,
    )

    assert result.score == pytest.approx(0.75)
    assert result.risk_band == "HIGH"
    assert result.evidence_codes == ("EXACT_PASSAGE_VERIFICATION",)
    assert not hasattr(result, "judge_confidence")


def _unlikely_ia_evidence() -> EvidencePacket:
    return EvidencePacket(
        (
            AttackAssessment(
                "ia",
                "UNLIKELY",
                False,
                False,
                ("SYSTEMATIC_ENTITY_PROBING",),
                (),
                (),
            ),
        )
    )


def test_rubric_rejects_high_score_when_all_assessments_are_unlikely_without_support() -> None:
    with pytest.raises(ValueError, match="all-UNLIKELY evidence requires risk_score"):
        parse_rubric(
            {"risk_score": 60, "suspected_attack_types": []},
            allowed_pattern_ids=("ia",),
            allowed_evidence_codes={"SYSTEMATIC_ENTITY_PROBING"},
            evidence=_unlikely_ia_evidence(),
        )


def test_rubric_rejects_unlikely_suspected_attack_type() -> None:
    with pytest.raises(ValueError, match="all-UNLIKELY evidence"):
        parse_rubric(
            {"risk_score": 12, "suspected_attack_types": ["ia"]},
            allowed_pattern_ids=("ia",),
            allowed_evidence_codes={"SYSTEMATIC_ENTITY_PROBING"},
            evidence=_unlikely_ia_evidence(),
        )


def test_rubric_requires_low_empty_output_for_empty_evidence_packet() -> None:
    with pytest.raises(ValueError, match="empty evidence requires risk_score"):
        parse_rubric(
            {"risk_score": 60, "suspected_attack_types": []},
            allowed_pattern_ids=("ia",),
            allowed_evidence_codes=set(),
            evidence=EvidencePacket(()),
            validated_evidence_codes=(),
        )

    result = parse_rubric(
        {"risk_score": 12, "suspected_attack_types": []},
        allowed_pattern_ids=("ia",),
        allowed_evidence_codes=set(),
        evidence=EvidencePacket(()),
        validated_evidence_codes=(),
    )
    assert result.score == pytest.approx(0.12)


def test_all_unlikely_rubric_inconsistency_triggers_targeted_repair() -> None:
    client = _ProgressiveClient(
        [
            {
                "routing_decision": "REVIEW",
                "candidate_attack_types": ["ia"],
                "observed_feature_codes": ["MULTI_TURN_FACT_PROBES"],
            },
            {
                "assessments": [
                    {
                        "attack_type": "ia",
                        "verdict": "UNLIKELY",
                        "required_conditions_met": False,
                        "exclusion_applies": False,
                            "missing_condition_codes": ["MINIMUM_CONSTRAINED_PROBES_MISSING"],
                        "supporting_evidence_codes": [],
                        "counter_evidence_codes": [],
                    }
                ]
            },
            {"risk_score": 60, "suspected_attack_types": ["ia"]},
            {"risk_score": 12, "suspected_attack_types": []},
        ],
        {"A": 0.9, "B": 0.08, "C": 0.02},
    )

    trace = _judge(client).evaluate_query(
        query="Does repeated retrieval reveal corpus membership?", session_id="s1"
    )

    assert trace.rubric.score == pytest.approx(0.12)
    assert "all-UNLIKELY evidence requires risk_score" in client.json_prompts[-1]
    assert '<invalid_previous_json>{"risk_score": 60' in client.json_prompts[-1]


def test_session_requires_three_turns_and_uses_session_specific_prompt() -> None:
    waiting_client = _ProgressiveClient([], {"A": 1.0, "B": 0.0, "C": 0.0})
    waiting = _judge(waiting_client).evaluate_session(
        query="second query",
        session_id="s1",
        recent_turns=(_turn(1, "first query"),),
        retrieved_doc_ids=("doc-1",),
        retrieval_scores=(0.9,),
        min_session_queries=3,
    )
    assert waiting.statuses["overall"] == "insufficient_history"
    assert waiting_client.json_prompts == []

    client = _ProgressiveClient(
        _attack_responses("ia"),
        {"A": 0.1, "B": 0.2, "C": 0.7},
    )
    trace = _judge(client).evaluate_session(
        query="third narrow question",
        session_id="s1",
        recent_turns=(_turn(1, "first"), _turn(2, "second")),
        retrieved_doc_ids=("doc-1",),
        retrieval_scores=(0.9,),
        min_session_queries=3,
    )

    assert trace.stage == "session"
    assert "ordered multi-turn behavior" in client.json_prompts[0]
    assert '"top1_concentration": 1.0' in client.json_prompts[0]
    assert "query_risk_score" not in client.json_prompts[0]
    assert "membership_label" not in client.json_prompts[0]


def test_offline_truth_is_not_accepted_by_public_judge_signatures() -> None:
    forbidden = {"traffic_type", "attack_type", "membership_label", "target_doc_id"}

    assert set(inspect.signature(ProgressiveJudge.evaluate_query).parameters).isdisjoint(
        forbidden
    )
    assert set(inspect.signature(ProgressiveJudge.evaluate_session).parameters).isdisjoint(
        forbidden
    )
