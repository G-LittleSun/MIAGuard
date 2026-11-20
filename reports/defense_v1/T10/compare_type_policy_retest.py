"""Compare both strategy versions on the frozen local engineering cohort."""

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("first", type=Path)
    parser.add_argument("retest", type=Path)
    parser.add_argument("normal_review", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    first, retest, review = map(read, (args.first, args.retest, args.normal_review))
    assert first["cohort_manifest"] == retest["cohort_manifest"]
    old = {row["request_id"]: row for row in first["cases"] if row["method"] == "B_TYPE_V1"}
    by_method = {
        method: {row["request_id"]: row for row in retest["cases"] if row["method"] == method}
        for method in ("B_TYPE_V1", "B_TYPE_V2")
    }
    assert all(rows.keys() == old.keys() for rows in by_method.values())
    reviewed = {row["request_id"]: row for row in review["rows"] if row["method"] == "B_TYPE_V1"}
    checked_fields = (
        "status", "risk_source", "risk_status", "risk_score", "risk_triggered", "predicted_types",
        "action", "delivered_raw_parents", "response",
    )
    output = []
    for rid, earlier in old.items():
        before, after = (by_method[method][rid] for method in ("B_TYPE_V1", "B_TYPE_V2"))
        assert earlier["traffic"] == before["traffic"] == after["traffic"]
        differences = [key for key in checked_fields if before[key] != after[key]]
        reproduction = [key for key in checked_fields if earlier[key] != before[key]]
        grade = None
        if rid in reviewed:
            item = reviewed[rid]
            if after["response"] == item["response"] and after["reference_raw_delivered"] == item["reference_raw_delivered"]:
                grade = item["grade"]
            else:
                grade = "needs_review"
        output.append({
            "request_id": rid, "traffic": earlier["traffic"], "member": earlier["member"],
            "initial_to_retest_v1_differences": reproduction, "v1_to_v2_differences": differences,
            "v1_action": before["action"], "v2_action": after["action"],
            "v1_recovered_slots": before["masked"]["matched"] if before["masked"] else None,
            "v2_recovered_slots": after["masked"]["matched"] if after["masked"] else None,
            "v2_normal_grade": grade,
        })
    summary = {
        "same_cohort_requests": len(output),
        "v1_reproduced_on_checked_fields": sum(not row["initial_to_retest_v1_differences"] for row in output),
        "v2_action_changes": sum(row["v1_action"] != row["v2_action"] for row in output),
        "v2_normal_grades": Counter(row["v2_normal_grade"] for row in output if row["v2_normal_grade"] is not None),
        "v2_normal_outputs_changed": sum(
            "response" in row["v1_to_v2_differences"] for row in output if row["traffic"] == "benign"
        ),
    }
    with args.output.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps({
            "summary": summary,
            "formal_effect_eligible": False,
            "input_sha256": {path.name: sha256(path.read_bytes()).hexdigest()
                             for path in (args.first, args.retest, args.normal_review)},
            "rows": output,
        }, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
