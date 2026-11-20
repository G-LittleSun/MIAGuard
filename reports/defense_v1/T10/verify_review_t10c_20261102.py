"""Independently verify the T10-C external review file contract."""
import collections
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PILOT = ROOT / "session_length_pilot_20261031_01"
REVIEW = ROOT / "external_review/pilot_t10c_deepseek_20261102_01"
OUT = ROOT / "review_validation_t10c_20261102.json"

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def load(path):
    return json.loads(path.read_text(encoding="utf-8"))

def rows(path):
    content = path.read_bytes()
    if content.startswith(b"\xef\xbb\xbf"):
        raise ValueError(f"UTF-8 BOM: {path}")
    return [json.loads(line) for line in content.decode("utf-8").splitlines()]

def main():
    m, pm = load(REVIEW / "review_manifest.json"), load(PILOT / "pilot_manifest.json")
    errors = []
    for name, digest in pm["files_sha256"].items():
        if sha(PILOT / name) != digest: errors.append(f"pilot hash {name}")
    for name, digest in m["input_file_sha256"].items():
        if not name.startswith("pilot_pkg/") or sha(PILOT / name.removeprefix("pilot_pkg/")) != digest:
            errors.append(f"review input hash {name}")
    if sha(REVIEW / "session_review.jsonl") != m["output_files"]["session_review.jsonl"]["sha256"]:
        errors.append("review output hash")
    same, expanded = rows(PILOT / "normal_variants.jsonl"), rows(PILOT / "expanded_variants.jsonl")
    base = rows(PILOT / "baseline_review.jsonl")
    inventory = {x["session_id"]: x for x in rows(PILOT / "session_inventory.jsonl")}
    originals = {x["variant_id"]: x for x in same + expanded}
    basemap = {x["variant_id"]: x for x in base}
    expected = [x["variant_id"] for x in same + expanded + base]
    reviewed = rows(REVIEW / "session_review.jsonl")
    ids = [x["variant_id"] for x in reviewed]
    if ids != expected or len(ids) != len(set(ids)): errors.append("ID/order mismatch")
    docs = {x["doc_id"] for x in rows(PILOT / "source_evidence.jsonl") + rows(PILOT / "expanded_source_evidence.jsonl")}
    decisions, cohorts = collections.Counter(), collections.defaultdict(collections.Counter)
    unsupported, suggestions, turns = [], 0, 0
    for row in reviewed:
        rid = row["variant_id"]
        if rid in originals:
            old = originals[rid]
            scope, expected_turns = old["source_doc_ids"], len(old["turns"])
            cohort = old["cohort"] + "_" + str(old["target_turns"])
        elif rid in basemap:
            old = basemap[rid]
            scope, expected_turns = old["source_refs"], len(inventory[old["session_id"]]["turns"])
            cohort = "baseline_5"
        else:
            errors.append(f"unknown {rid}")
            continue
        decision = row.get("decision")
        decisions[decision] += 1
        cohorts[cohort][decision] += 1
        if decision not in ("accept", "rewrite", "reject", "uncertain"): errors.append(f"decision {rid}")
        if set(row.get("source_refs", [])) != set(scope) or not set(scope) <= docs: errors.append(f"source scope {rid}")
        tr = row.get("turn_reviews", [])
        if len(tr) != expected_turns or [x.get("turn") for x in tr] != list(range(1, expected_turns + 1)):
            errors.append(f"turn reviews {rid}")
        turns += len(tr)
        for item in tr:
            if type(item.get("supported")) is not bool: errors.append(f"support field {rid}")
            if not set(item.get("evidence_ids", [])) <= set(scope): errors.append(f"turn evidence {rid}")
            if item.get("supported") is False: unsupported.append({"variant_id": rid, "turn": item["turn"]})
        for item in row.get("suggested_turns", []):
            suggestions += 1
            gold = item.get("gold_evidence_ids")
            if not isinstance(gold, list) or not set(gold) <= set(scope):
                errors.append(f"suggestion evidence {rid}")
                continue
            if item.get("answerable") is True and (not gold or not item.get("reference_answer")):
                errors.append(f"suggestion answer {rid}")
            if item.get("answerable") is False and (gold or item.get("reference_answer") is not None):
                errors.append(f"suggestion unanswerable {rid}")
            if not item.get("query"): errors.append(f"suggestion query {rid}")
        if not row.get("notes") or not isinstance(row.get("reason_codes"), list): errors.append(f"notes {rid}")
    if dict(decisions) != m["decision_counts"]["overall"]: errors.append("decision counts")
    for name, counts in m["decision_counts"]["by_cohort"].items():
        if dict(cohorts[name]) != counts: errors.append(f"cohort counts {name}")
    if turns != m["scope"]["turn_reviews_total"] or len(reviewed) != 70: errors.append("counts")
    result = {"schema_version": 1, "review_run_id": m["run_id"], "status": "passed" if not errors else "failed",
              "errors": errors, "scope": "Input/output identity, UTF-8, IDs/order, per-turn coverage, scoped evidence and proposed-answer contract; not proof of factual correctness, review independence, or provider snapshot.",
              "model_id_claim": m["model_id"], "model_id_source": m["model_id_source"], "reviewer_kind": m["reviewer_kind"],
              "input_file_count": len(m["input_file_sha256"]), "rows": len(reviewed), "turn_reviews": turns,
              "suggested_turns": suggestions, "decisions": dict(decisions),
              "cohort_decisions": {key: dict(value) for key, value in cohorts.items()}, "unsupported_turns": unsupported,
              "input_file_sha256": m["input_file_sha256"],
              "review_file_sha256": {name: sha(REVIEW / name) for name in ("review_manifest.json", "session_review.jsonl", "review_summary.md")},
              "limitations": ["Runtime model ID is not an immutable provider snapshot.", "Reviewer findings and self-declared process are not independently attested.", "Evidence ID scope does not prove entailment."]}
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: result[key] for key in ("status", "errors", "rows", "turn_reviews", "suggested_turns", "decisions", "unsupported_turns")}, ensure_ascii=False))
    if errors: raise SystemExit(1)

if __name__ == "__main__":
    main()
