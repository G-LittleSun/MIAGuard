from pathlib import Path

import pytest

from miaguard.direct_rag_mia import (
    direct_attack_query,
    direct_membership_score,
)
from miaguard.s2_mia import semantic_similarity_score, s2_query_prefix
from rag_mia_data.experiment import load_experiment_config


class _EmbeddingClient:
    def __init__(self, vectors: list[list[float]]) -> None:
        self.vectors = vectors

    def embed(self, model: str, texts: list[str]) -> list[list[float]]:
        return self.vectors


def test_direct_rag_mia_uses_paper_yes_no_prompt_and_score():
    query = direct_attack_query("target passage")

    assert query == (
        'Does this: "target passage" appear in the context? '
        "Answer with Yes or No."
    )
    assert direct_membership_score("Yes") == 1.0
    assert direct_membership_score("No") == 0.0
    assert direct_membership_score("Unknown") == 0.0


def test_s2_prefix_matches_teacher_ag_news_and_qa_rules():
    assert s2_query_prefix("one two three four", 3) == "one two three"
    assert s2_query_prefix("question text\tanswer text", 3) == "question text"


def test_s2_similarity_uses_teacher_normalized_cosine_score():
    identical = semantic_similarity_score(
        "original",
        "generated",
        _EmbeddingClient([[1.0, 0.0], [1.0, 0.0]]),  # type: ignore[arg-type]
        "embedding",
    )
    orthogonal = semantic_similarity_score(
        "original",
        "generated",
        _EmbeddingClient([[1.0, 0.0], [0.0, 1.0]]),  # type: ignore[arg-type]
        "embedding",
    )

    assert identical == pytest.approx(1.0)
    assert orthogonal == pytest.approx(0.5)


def test_baseline_smoke_config_selects_both_new_attacks():
    root = Path(__file__).resolve().parents[1]
    config = load_experiment_config(
        root, root / "configs/experiments/baseline_smoke.yaml"
    )

    assert config.include == ("ag_news",)
    assert config.attacks == ("direct_rag_mia", "s2_mia")
    assert config.target_counts["direct_rag_mia"].members == 10
    assert config.target_counts["s2_mia"].nonmembers == 10
