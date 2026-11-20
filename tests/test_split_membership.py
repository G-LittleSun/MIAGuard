from rag_mia_data.split_membership import assign_membership, select_targets


def _doc(index, group):
    return {
        "doc_id": f"d{index:03d}",
        "text": f"主题{index % 4} 内容" * 20,
        "char_length": 120 + index,
        "duplicate_group_id": group,
        "membership_label": None,
        "target_split": None,
    }


def test_membership_is_exact_reproducible_and_group_safe():
    docs = [_doc(0, "g0"), _doc(1, "g0")] + [
        _doc(index, f"g{index}") for index in range(2, 20)
    ]

    one = assign_membership(docs, seed=13, member_ratio=0.5, topic_clusters=4)
    two = assign_membership(list(reversed(docs)), seed=13, member_ratio=0.5, topic_clusters=4)

    assert sum(doc["membership_label"] for doc in one) == 10
    assert {doc["doc_id"]: doc["membership_label"] for doc in one} == {
        doc["doc_id"]: doc["membership_label"] for doc in two
    }
    assert len(
        {
            doc["membership_label"]
            for doc in one
            if doc["duplicate_group_id"] == "g0"
        }
    ) == 1


def test_targets_are_balanced_and_split_60_20_20():
    docs = [
        _doc(index, f"g{index}") | {"membership_label": index % 2}
        for index in range(100)
    ]

    targets = select_targets(
        docs, target_count=20, seed=17, split_ratio=(0.6, 0.2, 0.2)
    )

    assert sum(doc["membership_label"] == 1 for doc in targets) == 10
    assert {
        name: sum(doc["target_split"] == name for doc in targets)
        for name in ("train", "validation", "test")
    } == {"train": 12, "validation": 4, "test": 4}
