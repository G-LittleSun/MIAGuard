from rag_mia_data.preprocess import make_doc_id, normalize_text, select_candidates


def test_normalize_text_keeps_facts_and_removes_markup():
    raw = "ＡＩ<br><b>模型</b>\x00  在  2026 年发布。"

    assert normalize_text(raw) == "AI 模型 在 2026 年发布。"


def test_make_doc_id_is_stable_for_numeric_and_text_ids():
    assert make_doc_id("12") == "t2rank_00000012"
    assert make_doc_id("abc") == make_doc_id("abc")
    assert make_doc_id("abc").startswith("t2rank_h")


def test_select_candidates_is_order_independent_for_unique_text():
    rows = [
        {"pid": "2", "text": "甲" * 20},
        {"pid": "1", "text": "乙" * 20},
        {"pid": "3", "text": "甲" * 20},
    ]

    first = select_candidates(rows, count=2, seed=7, min_chars=1, max_chars=100)
    second = select_candidates(reversed(rows), count=2, seed=7, min_chars=1, max_chars=100)

    assert [row["normalized_text_sha256"] for row in first] == [
        row["normalized_text_sha256"] for row in second
    ]
    assert len(first) == 2
    assert all(row["membership_label"] is None for row in first)
