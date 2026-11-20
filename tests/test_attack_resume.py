from pathlib import Path

import pytest

from miaguard.data import resume_attack_results
from rag_mia_data.io_utils import write_jsonl_atomic


def test_resume_attack_results_skips_completed_prefix(tmp_path: Path) -> None:
    output = tmp_path / "attack"
    write_jsonl_atomic(output / "results.jsonl", [{"doc_id": "member-1"}])
    documents = [{"doc_id": "member-1"}, {"doc_id": "nonmember-1"}]

    rows, pending = resume_attack_results(output, documents)

    assert rows == [{"doc_id": "member-1"}]
    assert pending == [{"doc_id": "nonmember-1"}]


def test_resume_attack_results_rejects_mismatched_results(tmp_path: Path) -> None:
    output = tmp_path / "attack"
    write_jsonl_atomic(output / "results.jsonl", [{"doc_id": "unexpected"}])

    with pytest.raises(ValueError, match="not a prefix"):
        resume_attack_results(output, [{"doc_id": "member-1"}])
