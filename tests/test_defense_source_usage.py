import pytest

from miaguard import defense_dataset


def validate_normal_source_usage(*args):
    return defense_dataset.validate_normal_source_usage(*args)


def document(doc_id, parent=None, group=None):
    return {"doc_id": doc_id, "parent_doc_id": parent or doc_id,
            "duplicate_group_id": group or doc_id}


def task(partition, sources, evidence=None):
    return {"partition": partition, "source_doc_ids": sources,
            "gold_evidence_ids": sources if evidence is None else evidence}


def test_shared_background_can_be_indexed_in_both_partitions_but_used_only_in_dev():
    docs = [document("shared"), document("fresh")]
    indexes = {"D-dev": {"shared"}, "V": {"shared", "fresh"}}
    validate_normal_source_usage(docs, [task("D-dev", ["shared"]), task("V", ["fresh"])], indexes, {"shared"})
    with pytest.raises(ValueError, match="development exposure"):
        validate_normal_source_usage(docs, [task("V", ["shared"])], indexes, {"shared"})


@pytest.mark.parametrize("relation", ["parent", "group"])
def test_excludes_related_parent_or_duplicate_group(relation):
    docs = [document("dev", parent="p", group="g"),
            document("other", parent="p" if relation == "parent" else "other",
                     group="g" if relation == "group" else "other")]
    with pytest.raises(ValueError, match="development exposure"):
        validate_normal_source_usage(docs, [task("T", ["other"])], {"T": {"other"}}, {"dev"})


def test_excludes_transitively_linked_source():
    docs = [document("dev", parent="p"), document("bridge", parent="p", group="g"),
            document("other", group="g")]
    with pytest.raises(ValueError, match="development exposure"):
        validate_normal_source_usage(docs, [task("A-cal", ["other"])], {"A-cal": {"other"}}, {"dev"})


def test_requires_each_source_in_actual_partition_index():
    with pytest.raises(ValueError, match="partition index"):
        validate_normal_source_usage([document("shared")], [task("V", ["shared"])], {"V": set()}, set())


def test_evidence_must_be_declared_and_missing_exposure_fails_closed():
    docs = [document("a"), document("b")]
    with pytest.raises(ValueError, match="declared source"):
        validate_normal_source_usage(docs, [task("V", ["a"], ["b"])], {"V": {"a", "b"}}, set())
    with pytest.raises(ValueError, match="exposure.*missing"):
        validate_normal_source_usage(docs, [], {}, {"unknown"})


@pytest.mark.parametrize("field", ["parent_doc_id", "duplicate_group_id"])
def test_rejects_missing_source_relation_metadata(field):
    docs = [document("dev"), document("other")]
    docs[1][field] = None
    with pytest.raises(ValueError, match="source relation metadata"):
        validate_normal_source_usage(docs, [task("V", ["other"])], {"V": {"other"}}, {"dev"})
