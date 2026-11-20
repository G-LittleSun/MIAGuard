"""Export a D-dev-only pilot review packet without exposing membership labels."""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from pathlib import Path


def _rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _write(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    source = root / "data/defense_datasets/defense_access_v1_candidate06"
    output = root / "reports/defense_v1/T10"
    output.mkdir(parents=True, exist_ok=True)
    docs = {row["doc_id"]: row for row in _rows(source / "documents.jsonl")}
    requests = {row["request_id"]: row for row in _rows(source / "normal_requests.jsonl")}
    tasks = [row for row in _rows(source / "normal_tasks.jsonl") if row["partition"] == "D-dev"]
    by_family: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
    for row in tasks:
        by_family[row["task_family"]][requests[row["request_id"]]["session_id"]].append(row)
    normal_review = []
    for family, sessions in sorted(by_family.items()):
        for session_id in sorted(sessions)[:2]:
            for task in sessions[session_id]:
                request = requests[task["request_id"]]
                normal_review.append({"request_id": task["request_id"], "session_id": session_id,
                                      "task_family": family, "query": request["query"],
                                      "source_doc_id": task["doc_id"], "source_text": docs[task["doc_id"]]["text"],
                                      "draft_answerable": task["answerable"],
                                      "draft_reference_answer": task["reference_answer"],
                                      "draft_gold_evidence_ids": task["gold_evidence_ids"],
                                      "review_status": "pending", "reviewed_by": None,
                                      "decision": None, "corrected_reference_answer": None,
                                      "corrected_gold_evidence_ids": None, "notes": None})
    attack_requests = {row["request_id"]: row for row in _rows(source / "attack_requests.jsonl")}
    labels = [row for row in _rows(source / "attack_labels.jsonl") if row["partition"] == "D-dev"]
    by_attack: dict[str, list[dict]] = defaultdict(list)
    for row in labels:
        by_attack[row["attack_type"]].append(row)
    attack_review = []
    for attack, rows in sorted(by_attack.items()):
        # Two distinct targets from each underlying class, with the label hidden from reviewers.
        for label in (0, 1):
            chosen = sorted((row for row in rows if row["membership_label"] == label), key=lambda row: row["doc_id"])[:2]
            for row in chosen:
                request = attack_requests[row["request_id"]]
                attack_review.append({"request_id": row["request_id"], "attack_type": attack,
                                      "query": request["query"],
                                      "target_text": docs[row["doc_id"]]["text"],
                                      "review_status": "pending", "reviewed_by": None,
                                      "decision": None, "corrected_query": None, "notes": None})
    normal_path = output / "review_packet_d_dev_normal.jsonl"
    attack_path = output / "review_packet_d_dev_attack.jsonl"
    _write(normal_path, normal_review)
    _write(attack_path, attack_review)
    manifest = {"schema_version": 1, "source_dataset_manifest_sha256": _sha(source / "manifest.json"),
                "partition": "D-dev", "purpose": "pilot_query_and_gold_review_only",
                "sampling": "two lexicographically first opaque session IDs per normal family; two first target IDs per underlying class per attack, class hidden in packet",
                "normal_rows": len(normal_review), "attack_rows": len(attack_review),
                "review_status": "pending", "formal_effect_eligible": False,
                "files_sha256": {normal_path.name: _sha(normal_path), attack_path.name: _sha(attack_path)}}
    (output / "review_packet_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
