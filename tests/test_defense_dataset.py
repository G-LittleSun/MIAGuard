import pytest

from miaguard.defense_dataset import duplicate_groups, draft_queries, validate_dataset


def _doc(doc_id, partition, label, group=None):
    return {"doc_id": doc_id, "parent_doc_id": doc_id, "partition": partition,
            "membership_label": label, "duplicate_group_id": group or doc_id}


def _task(doc_id="a", answerable=True, answer="A", evidence=None):
    return {"request_id": "q1", "doc_id": doc_id, "task_family": "single_fact",
            "answerable": answerable, "reference_answer": answer,
            "gold_evidence_ids": [doc_id] if evidence is None else evidence,
            "review_status": "pending", "reviewed_by": None}


def test_rejects_group_cross_partition():
    with pytest.raises(ValueError, match="duplicate group"):
        validate_dataset([_doc("a", "D-dev", 1, "g"), _doc("b", "T", 0, "g")], [])


def test_rejects_parent_cross_partition():
    rows = [_doc("a", "D-dev", 1), _doc("b", "V", 0)]
    rows[1]["parent_doc_id"] = "a"
    with pytest.raises(ValueError, match="parent"):
        validate_dataset(rows, [])


def test_rejects_blank_answer_missing_evidence_and_unanswerable_conflict():
    docs = [_doc("a", "D-dev", 1)]
    for task, match in [(_task(answer=" "), "reference_answer"),
                        (_task(evidence=[]), "gold_evidence"),
                        (_task(answerable=False, answer="A", evidence=[]), "unanswerable")]:
        with pytest.raises(ValueError, match=match):
            validate_dataset(docs, [task])


def test_rejects_label_confusion_and_false_review():
    docs = [_doc("a", "D-dev", 1), _doc("b", "D-dev", 0)]
    docs[1]["duplicate_group_id"] = "a"
    with pytest.raises(ValueError, match="mixed membership"):
        validate_dataset(docs, [])
    task = _task()
    task["review_status"] = "reviewed"
    with pytest.raises(ValueError, match="reviewed_by"):
        validate_dataset([docs[0]], [task])


def test_rejects_gold_evidence_from_another_partition():
    with pytest.raises(ValueError, match="gold_evidence_ids crosses"):
        validate_dataset([_doc("a", "D-dev", 1), _doc("b", "T", 1)], [_task(evidence=["b"])])


def test_near_duplicate_group_is_stable_and_links_rephrased_text():
    rows = [{"doc_id": "x", "text": "The prime minister said the election would take place next Sunday."},
            {"doc_id": "y", "text": "The prime minister said the election would take place next Sunday!"},
            {"doc_id": "z", "text": "A spacecraft landed safely on Mars after a long flight."}]
    groups = duplicate_groups(rows)
    assert groups["x"] == groups["y"]
    assert groups["z"] != groups["x"]


def test_valid_unanswerable_has_explicit_reason_and_no_gold():
    task = _task(answerable=False, answer=None, evidence=[])
    task["unanswerable_reason"] = "Not stated in the allowed source."
    validate_dataset([_doc("a", "D-dev", 1)], [task])


def test_draft_queries_separate_online_requests_from_gold_and_use_opaque_ids():
    sizes = {"D-dev": 100, "A-cal": 500, "V": 200, "T": 1000}
    docs = []
    for partition, count in sizes.items():
        for label in (0, 1):
            for index in range(count):
                doc_id = f"{partition}_{label}_{index}"
                docs.append({**_doc(doc_id, partition, label),
                             "text": f"Report {doc_id} says the event took place in London. More details follow."})
    normal, normal_gold, attacks, attack_gold = draft_queries(docs)
    assert len(normal) == len(normal_gold) == 1750
    assert len(attacks) == len(attack_gold) == 14400
    assert all("membership_label" not in row and "doc_id" not in row for row in normal + attacks)
    assert all(row["review_status"] == "pending" and row["reviewed_by"] is None for row in normal_gold + attack_gold)
    assert all(label["doc_id"] not in request["request_id"] and label["doc_id"] not in request["session_id"]
               for request, label in zip(attacks, attack_gold, strict=True))
    first_session = normal[0]["session_id"]
    assert len({row["query"] for row in normal if row["session_id"] == first_session}) == 5


def test_draft_query_strips_encoded_html_from_online_prompt():
    sizes = {"D-dev": 100, "A-cal": 500, "V": 200, "T": 1000}
    docs = [{**_doc(f"{partition}_{label}_{i}", partition, label),
             "text": "News &lt;p&gt;Police reported an event in the city.&lt;/p&gt;"}
            for partition, count in sizes.items() for label in (0, 1) for i in range(count)]
    normal, _, attacks, _ = draft_queries(docs)
    assert "&lt;" not in normal[0]["query"] and "<p>" not in normal[0]["query"]
    assert "&lt;" not in attacks[0]["query"] and "<p>" not in attacks[0]["query"]
