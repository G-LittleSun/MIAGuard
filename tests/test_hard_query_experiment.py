import pytest

from miaguard.defense import RuleDefense
from miaguard.hard_query_experiment import (
    hard_benign_query,
    paraphrase_attack_query,
)


@pytest.mark.parametrize(
    ("attack", "row", "text"),
    [
        (
            "direct_rag_mia",
            {"attack_query": "unused"},
            "A company announced a product.",
        ),
        (
            "s2_mia",
            {"prefix": "A company announced"},
            "A company announced a product.",
        ),
        (
            "masked_mia",
            {"masked_text": "A [Mask_1] announced [Mask_2]."},
            "A company announced a product.",
        ),
        (
            "ia",
            {"queries": [{"question": "Did the company announce a product?"}]},
            "A company announced a product.",
        ),
    ],
)
def test_attack_paraphrases_avoid_current_rule_keywords(attack, row, text) -> None:
    query = paraphrase_attack_query(attack, row, text)

    risk, reasons = RuleDefense._query_signals(query)

    assert risk == 0.0
    assert reasons == []


@pytest.mark.parametrize("pattern_index", [0, 1, 2, 3])
def test_hard_benign_queries_trigger_current_rules(pattern_index: int) -> None:
    query, pattern = hard_benign_query(
        "A company announced a product in a public news article.", pattern_index
    )

    risk, reasons = RuleDefense._query_signals(query)

    assert pattern
    assert risk >= 0.5
    assert reasons
