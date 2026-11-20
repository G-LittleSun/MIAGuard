from rag_mia_data.deduplicate import assign_duplicate_groups, char_ngrams


def test_char_ngrams_handles_short_text():
    assert char_ngrams("中文", 5) == {"中文"}


def test_near_duplicates_share_group_but_unrelated_text_does_not():
    docs = [
        {"doc_id": "a", "text": "机器学习模型用于中文检索和排序，并支持稳定的检索结果。"},
        {"doc_id": "b", "text": "机器学习模型用于中文检索与排序，并支持稳定的检索结果。"},
        {"doc_id": "c", "text": "产后恢复需要合理饮食与运动。"},
    ]

    grouped, stats = assign_duplicate_groups(
        docs, ngram=3, num_perm=64, bands=16, threshold=0.70, seed=9
    )

    groups = {doc["doc_id"]: doc["duplicate_group_id"] for doc in grouped}
    assert groups["a"] == groups["b"]
    assert groups["a"] != groups["c"]
    assert stats["near_duplicate_pairs"] == 1
