from types import SimpleNamespace

from miaguard.two_stage_attack_comparison import expand_ia_rows


class _Client:
    def generate_json(self, model, prompt, **kwargs):
        if "generate exactly" in prompt:
            return {
                "summary": "target event",
                "questions": ["Did A happen?", "Did B happen?", "Did C happen?"],
            }
        return {"answers": ["yes", "no", "yes"]}


class _BrokenClient:
    def generate_json(self, model, prompt, **kwargs):
        raise RuntimeError("incomplete JSON")


def test_expand_ia_rows_builds_one_three_turn_session_per_document() -> None:
    rows = [{"doc_id": "doc-1", "membership_label": 1, "queries": []}]
    documents = {"doc-1": {"doc_id": "doc-1", "text": "A happened; B did not; C happened."}}
    config = SimpleNamespace(
        generation_model="model",
        ia_generation_max_tokens=128,
    )

    expanded = expand_ia_rows(rows, documents, _Client(), config, 3)

    assert len(expanded) == 1
    assert len(expanded[0]["queries"]) == 3
    assert [row["ground_truth"] for row in expanded[0]["queries"]] == [
        "yes",
        "no",
        "yes",
    ]


def test_expand_ia_rows_preserves_existing_query_and_falls_back_deterministically() -> None:
    existing = {
        "adversarial_query": "Did the event happen?",
        "ground_truth": "yes",
        "question": "Did the event happen?",
    }
    rows = [
        {
            "doc_id": "doc-1",
            "membership_label": 1,
            "summary": "target event",
            "queries": [existing],
        }
    ]
    documents = {
        "doc-1": {
            "doc_id": "doc-1",
            "text": "Alpha company announced a technology partnership in London on Monday.",
        }
    }
    config = SimpleNamespace(
        generation_model="model",
        ia_generation_max_tokens=128,
    )

    expanded = expand_ia_rows(rows, documents, _BrokenClient(), config, 3)

    assert expanded[0]["queries"][0] == existing
    assert len(expanded[0]["queries"]) == 3
    assert all(
        row["generation_source"] == "deterministic_fallback"
        for row in expanded[0]["queries"][1:]
    )
    assert all(row["ground_truth"] == "yes" for row in expanded[0]["queries"][1:])
