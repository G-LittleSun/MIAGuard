import pytest

from rag_mia_data.query_schema import validate_query_record


VALID_QUERY = {
    "query_id": "qry_direct_test_000001",
    "session_id": "ses_direct_test_000001",
    "turn_id": 1,
    "split": "test",
    "attack_type": "direct_ask",
    "attack_variant": "context_binary",
    "template_id": "direct_test_03",
    "target_doc_id": "t2rank_00000001",
    "membership_label": 1,
    "query": "该内容是否在本地知识库中？",
    "expected_answer": None,
    "evidence_text": None,
    "generation_method": "template",
    "generator_model": None,
    "seed": 20260713,
    "metadata": {},
}


def test_query_schema_accepts_common_record_and_separates_labels():
    validate_query_record(VALID_QUERY)
    validate_query_record(
        VALID_QUERY | {"attack_type": "mask_based", "membership_label": 0}
    )


@pytest.mark.parametrize(
    "change",
    [
        {"query": ""},
        {"split": "val"},
        {"membership_label": 2},
        {"attack_type": "unknown"},
    ],
)
def test_query_schema_rejects_invalid_common_fields(change):
    with pytest.raises(ValueError):
        validate_query_record(VALID_QUERY | change)


def test_query_schema_rejects_missing_required_field():
    record = dict(VALID_QUERY)
    record.pop("template_id")

    with pytest.raises(ValueError, match="template_id"):
        validate_query_record(record)

