from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from miaguard.defense_experiment import _query_bank_metadata
from miaguard.query_bank.schema import document_sha256
from miaguard.two_stage_attack_comparison import prepare_frozen_query_selection


def test_two_stage_script_exposes_frozen_query_options() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_two_stage_attack_comparison.py",
            "--help",
        ],
        cwd=Path.cwd(),
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "--query-bank-id" in result.stdout
    assert "--query-seed" in result.stdout
    assert "--variant-mode" in result.stdout


def test_query_bank_metadata_does_not_require_baseline_score() -> None:
    assert _query_bank_metadata({"query_id": "query-1"}) == {
        "query_id": "query-1"
    }
    assert _query_bank_metadata(
        {
            "query_id": "query-1",
            "membership_score": 0.8,
            "retrieved_doc_ids": ["doc-2"],
        }
    ) == {
        "query_id": "query-1",
        "baseline_membership_score": 0.8,
        "baseline_retrieved_doc_ids": ["doc-2"],
    }


def test_prepare_frozen_selection_rejects_changed_source_document() -> None:
    bank = SimpleNamespace(
        documents=(
            {
                "doc_id": "doc-1",
                "membership_label": 1,
                "source_document_sha256": document_sha256("original"),
            },
        )
    )

    with pytest.raises(ValueError, match="hash changed"):
        prepare_frozen_query_selection(
            bank,
            [{"doc_id": "doc-1", "membership_label": 1, "text": "changed"}],
            limit_per_class=1,
            benign_count=1,
            ia_turn_count=3,
            seed=17,
            variant_mode="canonical",
        )
