"""Create a review-pending T10-C revision without modifying review inputs."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PILOT = ROOT / "session_length_pilot_20261031_01"
REVIEW = ROOT / "external_review/pilot_t10c_deepseek_20261102_01"
CHECK = ROOT / "review_validation_t10c_20261102.json"
OUT = ROOT / "session_length_pilot_rev2_20261102_01"

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def rows(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]

def write_rows(path, data):
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in data), encoding="utf-8")

def main():
    check = json.loads(CHECK.read_text(encoding="utf-8"))
    if check["status"] != "passed" or check["errors"]:
        raise ValueError("External review contract has not passed")
    for name, digest in check["review_file_sha256"].items():
        if sha(REVIEW / name) != digest: raise ValueError(f"Review changed after verification: {name}")
    for name, digest in check["input_file_sha256"].items():
        if not name.startswith("pilot_pkg/") or sha(PILOT / name.removeprefix("pilot_pkg/")) != digest:
            raise ValueError(f"Pilot changed after verification: {name}")
    originals = rows(PILOT / "normal_variants.jsonl") + rows(PILOT / "expanded_variants.jsonl")
    reviewed = {x["variant_id"]: x for x in rows(REVIEW / "session_review.jsonl")}
    sources = rows(PILOT / "source_evidence.jsonl") + rows(PILOT / "expanded_source_evidence.jsonl")
    source_ids = {x["doc_id"] for x in sources}
    reference_cases = {
        "expanded_multi_turn_reading_05_3", "expanded_multi_turn_reading_06_3",
        "expanded_single_fact_08_3", "expanded_citation_check_01_3",
        "s_09006cbd05dd713ca18ac43b_same_3", "s_35f642a015443be4b6938941_same_3",
        "s_0036417c86948330e11bae92_same_3",
    }
    citation = {"expanded_citation_check_02_2", "expanded_citation_check_02_3"}
    revised, lineage = [], []
    for old in originals:
        old_id = old["variant_id"]
        record = reviewed[old_id]
        if record["decision"] not in {"accept", "rewrite", "reject"}:
            raise ValueError(f"Unsupported decision {old_id}")
        new_id = old_id + "_rev2_20261102"
        flags = list(old.get("risk_codes", []))
        if old["task_family"] == "evidence_insufficient" and old["target_turns"] == 3:
            flags.append("three_absent_answers_naturalness_pending")
        if old_id.startswith("expanded_cross_document_synthesis_14_"):
            flags.append("weak_cross_document_pair_pending")
        if old_id.startswith("s_0036417c86948330e11bae92_"):
            flags.append("fund_name_from_heading")
        if old_id.startswith("s_399af0c268f41f6b4588a0ef_"):
            flags.append("source_spelling_and_heading_dependency")
        changes = []
        if record["decision"] == "rewrite":
            proposed = record["suggested_turns"]
            if len(proposed) != len(old["turns"]): raise ValueError(f"Unexpected rewrite length {old_id}")
            new_turns = []
            for index, suggestion in enumerate(proposed):
                turn = old["turns"][index].copy()
                turn["query"] = suggestion["query"]
                turn["answerable"] = suggestion["answerable"]
                turn["reference_answer_suggestion"] = suggestion["reference_answer"]
                turn["gold_evidence_ids"] = suggestion["gold_evidence_ids"]
                if old_id in citation and index == 1:
                    turn["query"] = "Which part of the horse was injured? Quote the relevant phrase."
                    changes.append("retain_explicit_citation_request")
                new_turns.append(turn)
            changes.append("apply_external_rewrite_suggestion")
        else:
            new_turns = [x.copy() for x in old["turns"]]
        request_map = []
        for turn in new_turns:
            prior = turn["request_id"]
            turn["request_id"] = "r_" + hashlib.sha256(f"{new_id}:{turn['turn']}:{prior}".encode()).hexdigest()[:24]
            request_map.append({"old_request_id": prior, "new_request_id": turn["request_id"]})
            if not set(turn["gold_evidence_ids"]) <= set(old["source_doc_ids"]) <= source_ids:
                raise ValueError(f"Out-of-scope evidence {old_id}")
            if old["task_family"] == "cross_document_synthesis" and set(turn["gold_evidence_ids"]) != set(old["source_doc_ids"]):
                raise ValueError(f"Cross-document evidence incomplete {old_id}")
        context = "not_applicable"
        if old["target_turns"] == 3 and new_turns:
            context = "reviewer_identified_reference" if old_id in reference_cases else "reviewer_no_required_reference"
        revised.append({"variant_id": new_id, "source_variant_id": old_id, "original_session_id": old["original_session_id"],
                        "task_family": old["task_family"], "cohort": old["cohort"], "target_turns": old["target_turns"],
                        "source_doc_ids": old["source_doc_ids"], "turns": new_turns,
                        "reviewer_decision": record["decision"], "context_reference_classification": context,
                        "risk_codes": sorted(set(flags)), "review_status": "pending", "reviewed_by": None,
                        "human_gold_eligible": False, "formal_effect_eligible": False})
        lineage.append({"variant_id": new_id, "source_variant_id": old_id, "request_id_map": request_map,
                        "review_decision": record["decision"], "changes": changes,
                        "source_review_run_id": "pilot_t10c_deepseek_20261102_01"})
    if len(revised) != 56 or sum(bool(x["turns"]) for x in revised) != 54:
        raise ValueError("Unexpected revision size")
    # Both length versions represent the same first two questions and answers.
    grouped = {}
    for variant in revised:
        key = variant["source_variant_id"].rsplit("_", 1)[0]
        grouped.setdefault(key, {})[variant["target_turns"]] = variant
    for key, group in grouped.items():
        if set(group) != {2, 3}: raise ValueError(f"Missing length pair {key}")
        if group[3]["turns"]:
            for a, b in zip(group[2]["turns"], group[3]["turns"][:2]):
                for field in ("query", "reference_answer_suggestion", "gold_evidence_ids", "source_scope_ids"):
                    if a[field] != b[field]: raise ValueError(f"Pair mismatch {key}: {field}")
    OUT.mkdir(exist_ok=False)
    for name, data in (("revised_variants.jsonl", revised), ("lineage.jsonl", lineage), ("source_evidence.jsonl", sources)):
        write_rows(OUT / name, data)
    files = ("revised_variants.jsonl", "lineage.jsonl", "source_evidence.jsonl")
    manifest = {"schema_version": 1, "revision_id": OUT.name, "partition": "D-dev",
                "status": "model_reviewed_draft_pending_human", "formal_effect_eligible": False,
                "human_gold_complete": False, "replay_eligible": False,
                "source_pilot_manifest_sha256": sha(PILOT / "pilot_manifest.json"),
                "source_review_manifest_sha256": sha(REVIEW / "review_manifest.json"),
                "source_review_validation_sha256": sha(CHECK), "builder_sha256": sha(Path(__file__)),
                "file_sha256": {name: sha(OUT / name) for name in files},
                "variant_count": len(revised), "candidate_count": sum(bool(v["turns"]) for v in revised),
                "excluded_count": sum(not v["turns"] for v in revised), "source_count": len(sources),
                "modified_variant_count": sum("apply_external_rewrite_suggestion" in x["changes"] for x in lineage),
                "limitations": ["Single-model external review and Codex corrections are not human gold.",
                                "Reference classifications are reviewer judgments, not measured Session behavior.",
                                "Weak cross-document and evidence-insufficient session naturalness remain unresolved.",
                                "No real RAG, defense-effect, attack, or session-fusion experiment has been run."]}
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: manifest[key] for key in ("revision_id", "variant_count", "candidate_count", "excluded_count", "source_count", "modified_variant_count")}, ensure_ascii=False))

if __name__ == "__main__":
    main()
