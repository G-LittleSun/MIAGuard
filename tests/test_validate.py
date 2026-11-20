import pytest

from rag_mia_data.validate import validate_document_sets


def test_document_validation_rejects_membership_intersection():
    member = [{"doc_id": "d1", "duplicate_group_id": "g1", "membership_label": 1}]
    nonmember = [
        {"doc_id": "d1", "duplicate_group_id": "g2", "membership_label": 0}
    ]

    with pytest.raises(ValueError, match="intersection"):
        validate_document_sets(
            member, nonmember, [], expected_members=1, expected_targets=0
        )


def test_document_validation_accepts_balanced_disjoint_sets():
    member = [{"doc_id": "d1", "duplicate_group_id": "g1", "membership_label": 1}]
    nonmember = [
        {"doc_id": "d2", "duplicate_group_id": "g2", "membership_label": 0}
    ]

    result = validate_document_sets(
        member, nonmember, [], expected_members=1, expected_targets=0
    )

    assert result["member_count"] == 1
    assert result["nonmember_count"] == 1

