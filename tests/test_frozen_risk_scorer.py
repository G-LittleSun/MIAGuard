import hashlib
import json
from math import exp, nan
from pathlib import Path

import pandas as pd
import pytest

from miaguard.judge_score_frozen import evaluate_frozen_fusion


ROOT = Path(__file__).resolve().parents[1]
FROZEN = ROOT / "data/judge_score_frozen_v3_binary_logprob_20260920/logistic_l2.json"


def _write_artifact(tmp_path, change):
    value = json.loads(FROZEN.read_text(encoding="utf-8"))
    change(value)
    path = tmp_path / "model.json"
    path.write_text(json.dumps(value), encoding="utf-8")
    return path, hashlib.sha256(path.read_bytes()).hexdigest()


def test_real_frozen_model_matches_reference_grid_and_existing_evaluator():
    from miaguard.frozen_risk_scorer import FrozenRiskScorer

    expected_sha = hashlib.sha256(FROZEN.read_bytes()).hexdigest()
    scorer = FrozenRiskScorer.from_file(FROZEN, "logprob", expected_sha)
    frozen = json.loads(FROZEN.read_text(encoding="utf-8"))
    for x1 in (0.0, 0.5, 1.0):
        for x2 in (0.0, 0.5, 1.0):
            z = frozen["coefficient"][0] * x1 + frozen["coefficient"][1] * x2 + frozen["intercept"]
            assert abs(scorer.score(x1, x2) - 1 / (1 + exp(-z))) <= 1e-12

    rows = []
    for index, (x1, x2, label) in enumerate(((0.0, 0.0, 0), (0.5, 0.5, 0), (1.0, 1.0, 1), (1.0, 0.5, 1))):
        rows.append({"doc_id": f"d{index}", "partition": "validation", "head": "logprob", "session_score_available": True,
                     "x1": x1, "x2_observed": x2, "label": label, "attack_type": "benign" if label == 0 else "ia"})
    # Existing evaluator expects every attack category for its per-attack recall.
    for attack in ("direct_rag_mia", "s2_mia", "masked_mia"):
        rows.append({**rows[-1], "doc_id": attack, "attack_type": attack})
    table = pd.DataFrame(rows)
    existing = evaluate_frozen_fusion(table, frozen)
    from sklearn.metrics import brier_score_loss
    scores = [scorer.score(float(row["x1"]), float(row["x2_observed"])) for row in rows]
    assert abs(existing["probability_metrics"]["brier"] - brier_score_loss(table["label"], scores)) <= 1e-12


def test_rejects_wrong_file_hash_or_head(tmp_path):
    from miaguard.frozen_risk_scorer import FrozenRiskScorer

    path, digest = _write_artifact(tmp_path, lambda _: None)
    with pytest.raises(ValueError, match="SHA256"):
        FrozenRiskScorer.from_file(path, "logprob", "0" * 64)
    with pytest.raises(ValueError, match="head"):
        FrozenRiskScorer.from_file(path, "rubric", digest)


@pytest.mark.parametrize("change, message", [
    (lambda value: value.update(feature_order=["x2_observed", "x1"]), "feature_order"),
    (lambda value: value.update(coefficient=[nan, 0.1]), "coefficient"),
    (lambda value: value.update(thresholds={}), "thresholds"),
])
def test_rejects_invalid_artifact(tmp_path, change, message):
    from miaguard.frozen_risk_scorer import FrozenRiskScorer

    path, digest = _write_artifact(tmp_path, change)
    with pytest.raises(ValueError, match=message):
        FrozenRiskScorer.from_file(path, "logprob", digest)


def test_rejects_missing_or_invalid_features():
    from miaguard.frozen_risk_scorer import FrozenRiskScorer

    scorer = FrozenRiskScorer.from_file(FROZEN, "logprob", hashlib.sha256(FROZEN.read_bytes()).hexdigest())
    with pytest.raises(ValueError, match="x2"):
        scorer.score(0.5, None)
    with pytest.raises(ValueError, match="x1"):
        scorer.score(nan, 0.5)
    with pytest.raises(ValueError, match="x2"):
        scorer.score(0.5, 1.01)
