"""Summarize evidence and agent judgments for the paired benign utility experiment."""

import argparse
from collections import Counter, defaultdict
from pathlib import Path

from freeze_benign_pair_20261113 import digest, read, rows, write


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("audit", type=Path)
    parser.add_argument("rubric", type=Path)
    parser.add_argument("lineage", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--judgments", type=Path)
    args = parser.parse_args()
    audit = read(args.audit)
    rubric = {row["request_id"]: row for row in rows(args.rubric)}
    lineage = {row["request_id"]: row for row in rows(args.lineage)}
    cases = defaultdict(dict)
    for row in audit["cases"]:
        assert row["traffic"] == "benign"
        cases[row["request_id"]][row["method"]] = row
    assert cases.keys() == rubric.keys() == lineage.keys()
    assert all(set(group) == {"B0", "B2", "B_TYPE_V2"} for group in cases.values())

    reviews = []
    for rid, group in cases.items():
        equivalent = defaultdict(list)
        for method, row in group.items():
            key = (row["status"], row["action"], row["reference_raw_delivered"], row["response"])
            equivalent[key].append(method)
        for n, ((status, action, evidence, response), methods) in enumerate(equivalent.items(), start=1):
            review = {
                "review_id": f"{rid}_{n}", "request_id": rid, "methods": methods, "status": status,
                "action": action, "reference_delivered": evidence, "response": response,
                "reference_answer": rubric[rid]["reference_answer"], "evidence_quote": rubric[rid]["evidence_quote"],
            }
            reviews.append(review)

    if args.output.exists():
        raise FileExistsError(args.output)
    if args.judgments is None:
        write(args.output, reviews)
        print("Review groups:", len(reviews))
        return

    judgments = read(args.judgments)
    needs_review = {
        row["review_id"] for row in reviews
        if row["status"] == "complete" and row["action"] not in {"deny", "unavailable"}
    }
    assert judgments.keys() == needs_review
    evidence_and_grade = {}
    for review in reviews:
        key = review["review_id"]
        judgment = judgments.get(key)
        if judgment:
            assert isinstance(judgment["facts_correct"], bool) and judgment["reason"].strip()
        review["agent_judgment"] = judgment
        review["correct_supported"] = bool(judgment and judgment["facts_correct"] and review["reference_delivered"])
        for method in review["methods"]:
            evidence_and_grade[method, review["request_id"]] = review["correct_supported"]

    summaries = {}
    for method in ("B0", "B2", "B_TYPE_V2"):
        group = [methods[method] for methods in cases.values()]
        supported = [row for row in group if evidence_and_grade[method, row["request_id"]]]
        complete = [row for row in group if row["status"] == "complete"]
        summaries[method] = {
            "expected": len(group), "completed": len(complete),
            "failed": sum(row["status"] == "failed" for row in group),
            "skipped": sum(row["status"] == "skipped" for row in group),
            "correct_supported": len(supported),
            "normal_intervention": sum(row["action"] not in {"allow", "unavailable"} for row in complete),
            "unavailable": sum(row["action"] == "unavailable" for row in complete),
            "reference_delivered": sum(row["reference_raw_delivered"] for row in complete),
            "actions": dict(Counter(row["action"] for row in complete)),
            "fusion": sum(row["risk_source"] == "fusion" and row["trace_statuses"].get("session") == "ok" for row in group),
            "latency_ms_p50": audit["methods"][method]["latency_ms_p50"],
            "latency_ms_p95_nearest_rank": audit["methods"][method]["latency_ms_p95_nearest_rank"],
        }

    paired = []
    for rid, group in cases.items():
        baseline, b2, v2 = (group[method] for method in ("B0", "B2", "B_TYPE_V2"))
        assert all(row["turn"] == lineage[rid]["turn"] for row in group.values())
        correct = evidence_and_grade["B_TYPE_V2", rid]
        if v2["status"] != "complete" or v2["action"] == "unavailable":
            cause = "execution_failure"
        elif correct:
            cause = "correct_supported"
        elif not baseline["reference_retrieved"]:
            cause = "baseline_missing_reference"
        elif not v2["reference_raw_delivered"]:
            cause = "reference_withheld_by_policy"
        else:
            cause = "answer_incorrect_despite_reference"
        paired.append({
            "request_id": rid, "doc_id": baseline["doc_id"], "turn": baseline["turn"],
            "screen_triggered": lineage[rid]["selected_with_screen_trigger"],
            "b0_reference_retrieved": baseline["reference_retrieved"],
            "b0_correct_supported": evidence_and_grade["B0", rid],
            "b2_action": b2["action"], "v2_action": v2["action"],
            "v2_reference_delivered": v2["reference_raw_delivered"],
            "v2_correct_supported": correct,
            "v2_outcome_category": cause, "v2_excluded_parents": v2["excluded_parents"],
            "v2_policy": v2["policy"],
        })
    denied = [row for row in paired if row["b2_action"] == "deny"]
    result = {
        "run_id": audit["run_id"], "analysis_role": "engineering_only",
        "reviewer_kind": "llm_agent", "human_reviewed": False, "formal_effect_eligible": False,
        "b2_denied": len(denied),
        "v2_correct_supported_among_b2_denied": sum(row["v2_correct_supported"] for row in denied),
        "b2_denied_with_b0_reference_retrieved": sum(row["b0_reference_retrieved"] for row in denied),
        "v2_outcome_among_b2_denied": dict(Counter(row["v2_outcome_category"] for row in denied)),
        "methods": summaries, "pairs": paired, "review_groups": reviews,
        "input_sha256": {path.name: digest(path) for path in (
            args.audit, args.rubric, args.lineage, args.judgments,
        )},
    }
    write(args.output, result)
    print({key: result[key] for key in ("b2_denied", "v2_correct_supported_among_b2_denied", "methods")})


if __name__ == "__main__":
    main()
