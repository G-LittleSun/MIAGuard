"""Build a D-dev engineering overlay from the second T10 model pre-review.

The source candidate and external review stay immutable. This overlay is not
human gold and is not eligible for formal defense-effect experiments.
"""

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

from miaguard.defense_dataset import validate_dataset


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(root: Path, output: Path) -> dict:
    candidate = root / "data/defense_datasets/defense_access_v1_candidate06"
    pilot = root / "reports/defense_v1/T10/pilot_revision_20261030_01"
    review = root / "reports/defense_v1/T10/external_review/pilot_deepseek_rev2_20261030_01"
    check = json.loads((root / "reports/defense_v1/T10/review_validation_rev2_20261030.json").read_text(encoding="utf-8"))
    if check["status"] != "contract_passed_with_semantic_blockers" or check["errors"]:
        raise ValueError("Second review has not passed its file contract check")
    source_manifest = json.loads((candidate / "manifest.json").read_text(encoding="utf-8"))
    review_manifest = json.loads((review / "review_manifest.json").read_text(encoding="utf-8"))
    if review_manifest["run_id"] != check["review_run_id"] or sha(review / "review_manifest.json") != check["review_file_sha256"]["review_manifest.json"]:
        raise ValueError("Review identity changed after validation")
    source_files = ("normal_requests.jsonl", "normal_tasks.jsonl", "attack_requests.jsonl", "attack_labels.jsonl", "documents.jsonl")
    if any(sha(candidate / name) != source_manifest["artifact_sha256"][name] for name in source_files):
        raise ValueError("Source candidate artifacts changed")
    if any(sha(review / name) != check["review_file_sha256"][name] for name in ("normal_review.jsonl", "attack_review.jsonl")):
        raise ValueError("Review rows changed after validation")
    data = {name: read_jsonl(candidate / name) for name in source_files}
    request_maps = {name: {row["request_id"]: row for row in data[name]} for name in source_files[:4]}
    evidence = {row["request_id"]: [doc["doc_id"] for doc in row["supporting_documents"]]
                for row in read_jsonl(pilot / "review_packet_d_dev_normal_evidence.jsonl")}
    normal_review = read_jsonl(review / "normal_review.jsonl")
    attack_review = read_jsonl(review / "attack_review.jsonl")
    if len(normal_review) != 70 or len(attack_review) != 16:
        raise ValueError("Unexpected review size")

    normal_requests, normal_tasks, attack_requests, attack_labels = [], [], [], []
    evidence_repairs = []
    for row in normal_review:
        rid = row["request_id"]
        if row["decision"] not in ("accept", "rewrite"):
            raise ValueError(f"Unusable normal review decision: {rid}")
        request = request_maps["normal_requests.jsonl"][rid].copy()
        task = request_maps["normal_tasks.jsonl"][rid].copy()
        if task["partition"] != "D-dev" or task["task_family"] != row["task_family"]:
            raise ValueError(f"Normal identity mismatch: {rid}")
        gold = row["final_gold_evidence_ids"].copy()
        if task["task_family"] == "cross_document_synthesis":
            required = evidence[rid]
            if len(required) != 2 or not set(gold) <= set(required):
                raise ValueError(f"Invalid cross-document evidence: {rid}")
            if set(gold) != set(required):
                evidence_repairs.append(rid)
                gold = required.copy()
        elif not set(gold) <= set(evidence[rid]):
            raise ValueError(f"Evidence outside supplied text: {rid}")
        request["query"] = row["final_query"]
        task.update(doc_id=evidence[rid][0], answerable=row["final_answerable"],
                    reference_answer=row["final_reference_answer"], gold_evidence_ids=gold,
                    unanswerable_reason=("The supplied article does not state the requested fact."
                                         if not row["final_answerable"] else None),
                    review_status="pending", reviewed_by=None,
                    draft_method="second_llm_review_suggestion_not_human_gold")
        normal_requests.append(request)
        normal_tasks.append(task)

    mask_answers = {
        "r_1f9d323024df6bef5ff05a7e": "sparkling",
        "r_641a74d1367a3cbfb1a8833d": "eclipse",
        "r_48c152e05236bb36c74a3d6c": "Aims",
        "r_ff5aedec7730877adfdc9ebb": "Belichick",
    }
    for row in attack_review:
        rid = row["request_id"]
        if row["decision"] not in ("accept", "rewrite"):
            raise ValueError(f"Unusable attack review decision: {rid}")
        request = request_maps["attack_requests.jsonl"][rid].copy()
        label = request_maps["attack_labels.jsonl"][rid].copy()
        if label["partition"] != "D-dev" or label["attack_type"] != row["attack_type"]:
            raise ValueError(f"Attack identity mismatch: {rid}")
        request["query"] = row["final_query"]
        label.update(review_status="pending", reviewed_by=None)
        if label["attack_type"] == "masked_mia":
            answer = mask_answers[rid]
            passage = request["query"].partition('}: ')[2]
            if not passage or passage.count("[MASK]") != 1 or re.search(r"\b" + re.escape(answer) + r"\b", passage, re.IGNORECASE):
                raise ValueError(f"Masked word leaked or mask absent: {rid}")
            label["answers"] = [answer]
        attack_requests.append(request)
        attack_labels.append(label)

    validate_dataset(data["documents.jsonl"], normal_tasks)
    if len(evidence_repairs) != 3 or len({r["request_id"] for r in normal_requests + attack_requests}) != 86:
        raise ValueError("Unexpected evidence repair or duplicate request")
    output.mkdir(parents=True, exist_ok=False)
    result_rows = {"normal_requests.jsonl": normal_requests, "normal_tasks.jsonl": normal_tasks,
                   "attack_requests.jsonl": attack_requests, "attack_labels.jsonl": attack_labels}
    for name, rows in result_rows.items():
        write_jsonl(output / name, rows)
    manifest = {
        "schema_version": 1, "version": output.name, "partition": "D-dev",
        "purpose": "engineering_pilot_overlay_only", "formal_effect_eligible": False,
        "human_gold_complete": False, "review_status": "pending",
        "source_candidate_manifest_sha256": sha(candidate / "manifest.json"),
        "source_candidate_dir": str(candidate.relative_to(root)),
        "source_candidate_id": source_manifest.get("dataset_id", candidate.name),
        "source_review_manifest_sha256": sha(review / "review_manifest.json"),
        "source_review_run_id": review_manifest["run_id"],
        "source_review_validation_sha256": sha(root / "reports/defense_v1/T10/review_validation_rev2_20261030.json"),
        "source_files_sha256": {name: sha(candidate / name) for name in source_files},
        "pilot_evidence_sha256": sha(pilot / "review_packet_d_dev_normal_evidence.jsonl"),
        "review_files_sha256": {name: sha(review / name) for name in ("normal_review.jsonl", "attack_review.jsonl")},
        "output_files_sha256": {name: sha(output / name) for name in result_rows},
        "counts": {name: len(rows) for name, rows in result_rows.items()},
        "normal_family_counts": dict(Counter(row["task_family"] for row in normal_tasks)),
        "attack_type_counts": dict(Counter(row["attack_type"] for row in attack_labels)),
        "cross_document_evidence_repairs": evidence_repairs,
        "masked_answer_changes_from_candidate06": [rid for rid in mask_answers if request_maps["attack_labels.jsonl"][rid]["answers"] != [mask_answers[rid]]],
        "limitations": ["Model pre-review is not human gold.",
                        "Several accepted five-turn sessions remain semantically repetitive.",
                        "All source articles are short snippets; content quality needs further revision.",
                        "IA yes/no prompts require nonmember false-positive calibration.",
                        "This overlay does not replace the full candidate06 dataset or its frozen indexes."],
    }
    (output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.root.resolve(), args.output.resolve()), ensure_ascii=False, indent=2))
