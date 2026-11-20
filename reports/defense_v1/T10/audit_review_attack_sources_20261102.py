"""Identify previously reviewed attack texts without exporting membership labels."""
import hashlib
import json
from collections import defaultdict
from pathlib import Path

from miaguard.defense_dataset import _normalize

ROOT = Path(__file__).resolve().parents[3]
T10 = ROOT / "reports/defense_v1/T10"
PACKETS = [T10 / "review_packet_d_dev_attack.jsonl",
           T10 / "pilot_revision_20261030_01/review_packet_d_dev_attack.jsonl"]
DOCS = ROOT / "data/defense_datasets/defense_access_v1_candidate06/documents.jsonl"
NORMAL = T10 / "normal_source_usage_20261102_01/source_usage.jsonl"
OUT = T10 / "review_attack_source_usage_20261102_01"


def read(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    lookup = defaultdict(list)
    for row in read(DOCS):
        if row["partition"] == "D-dev":
            lookup[_normalize(row["text"])].append({key: row[key] for key in
                ("doc_id", "parent_doc_id", "duplicate_group_id")})
    known_normal = {r["doc_id"] for r in read(NORMAL)}
    found, unmatched = {}, []
    for packet in PACKETS:
        for row in read(packet):
            matches = lookup.get(_normalize(row["target_text"]), [])
            if len(matches) != 1:
                unmatched.append({"packet": str(packet.relative_to(ROOT)),
                                  "request_id": row["request_id"], "match_count": len(matches)})
                continue
            doc = matches[0]
            entry = found.setdefault(doc["doc_id"], {**doc, "packet_requests": {},
                "also_in_normal_source_ledger": doc["doc_id"] in known_normal,
                "exclude_as_normal_question_source": ["A-cal", "V", "T"]})
            entry["packet_requests"].setdefault(str(packet.relative_to(ROOT)), []).append(row["request_id"])
    OUT.mkdir(exist_ok=False)
    output = OUT / "source_usage.jsonl"
    output.write_text("".join(json.dumps(found[k], ensure_ascii=False) + "\n" for k in sorted(found)), encoding="utf-8")
    manifest = {"status": "partial_history_audit", "unique_sources": len(found),
                "packet_rows": {str(p.relative_to(ROOT)): len(read(p)) for p in PACKETS},
                "unmatched_or_ambiguous": unmatched, "normal_ledger_overlap": sum(
                    r["also_in_normal_source_ledger"] for r in found.values()),
                "input_sha256": {str(p.relative_to(ROOT)): sha(p) for p in [*PACKETS, DOCS, NORMAL]},
                "output_sha256": sha(output), "matching": "exact normalized text against D-dev candidate06 documents",
                "limitations": ["Only the two named packets and existing partial normal ledger were examined.",
                    "Other historical prompts and semantic/event similarity require separate audit.",
                    "Membership labels and attack outcomes were not used for matching or exported."],
                "formal_effect_eligible": False}
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"unique_sources": len(found), "unmatched": len(unmatched),
                      "normal_overlap": manifest["normal_ledger_overlap"]}))


if __name__ == "__main__":
    main()
