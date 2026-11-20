"""Check immutable candidate data and four partition-isolated index identities."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

import faiss

from miaguard.defense_dataset import PARTITIONS, SIZES, validate_dataset


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    data = root / "data/defense_datasets/defense_access_v1_candidate06"
    index_root = root / "data/vector_stores/defense_access_v1_candidate06"
    manifest = json.loads((data / "manifest.json").read_text(encoding="utf-8"))
    assert all(_sha(data / name) == expected for name, expected in manifest["artifact_sha256"].items())
    documents = _read(data / "documents.jsonl")
    normal_requests = _read(data / "normal_requests.jsonl")
    normal_tasks = _read(data / "normal_tasks.jsonl")
    attack_requests = _read(data / "attack_requests.jsonl")
    attack_labels = _read(data / "attack_labels.jsonl")
    validate_dataset(documents, normal_tasks)
    assert len(normal_requests) == len(normal_tasks) == 1750
    assert len(attack_requests) == len(attack_labels) == 14400
    assert {row["request_id"] for row in normal_requests} == {row["request_id"] for row in normal_tasks}
    assert {row["request_id"] for row in attack_requests} == {row["request_id"] for row in attack_labels}
    assert all(set(row) == {"request_id", "session_id", "query"} for row in normal_requests + attack_requests)
    assert all(row["review_status"] == "pending" and row["reviewed_by"] is None for row in normal_tasks + attack_labels)
    audit = json.loads((data / "overlap_audit.json").read_text(encoding="utf-8"))
    assert all(value == 0 for key, value in audit.items() if key.endswith("overlap"))
    target_by_partition = {partition: {row["doc_id"] for row in documents if row["partition"] == partition} for partition in PARTITIONS}
    background = _read(data / "background_members.jsonl")
    background_ids = {row["doc_id"] for row in background}
    all_target_ids = set().union(*target_by_partition.values())
    assert background_ids.isdisjoint(all_target_ids)
    split_counts = Counter((row["partition"], row["membership_label"]) for row in documents)
    indexes = {}
    for partition in PARTITIONS:
        folder = index_root / partition / "ag_news"
        meta = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
        rows = _read(folder / "documents.jsonl")
        ids = {row["doc_id"] for row in rows}
        own_member = {row["doc_id"] for row in documents if row["partition"] == partition and row["membership_label"] == 1}
        assert faiss.read_index(str(folder / "index.faiss")).ntotal == len(rows) == 1000
        assert ids & all_target_ids == own_member
        assert ids - own_member <= background_ids
        assert all(row["membership_label"] == 1 for row in rows)
        assert _sha(folder / "index.faiss") == meta["index_sha256"]
        assert _sha(folder / "documents.jsonl") == meta["documents_sha256"]
        assert _sha(data / "manifest.json") == meta["source_dataset_manifest_sha256"]
        indexes[partition] = {"target_member": len(own_member), "shared_background": len(ids - own_member),
                              "total": len(rows), "index_sha256": meta["index_sha256"]}
        assert split_counts[(partition, 0)] == split_counts[(partition, 1)] == SIZES[partition]
    result = {"dataset_id": manifest["dataset_id"], "candidate": data.name,
              "status": "engineering_valid_pending_human_review", "formal_effect_eligible": False,
              "target_document_count": len(documents), "normal_request_count": len(normal_requests),
              "attack_request_count": len(attack_requests), "normal_task_family_counts": dict(Counter(row["task_family"] for row in normal_tasks)),
              "attack_type_counts": dict(Counter(row["attack_type"] for row in attack_labels)),
              "historical_overlap": {key: value for key, value in audit.items() if key.endswith("overlap")},
              "indexes": indexes, "dataset_manifest_sha256": _sha(data / "manifest.json")}
    output = root / "reports/defense_v1/T10/validation.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
