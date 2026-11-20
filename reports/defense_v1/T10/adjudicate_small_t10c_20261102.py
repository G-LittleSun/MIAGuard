"""Record a small Codex content review and versioned draft corrections."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REV = ROOT / "session_length_pilot_rev2_20261102_01"
REPLACEMENT = ROOT / "crossdoc_replacement_20261102_01"
OUT = ROOT / "session_length_pilot_targeted_20261102_01"

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def load(path):
    return json.loads(path.read_text(encoding="utf-8"))

def rows(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]

def write_rows(path, values):
    path.write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in values), encoding="utf-8")

def main():
    if OUT.exists(): raise FileExistsError(OUT)
    for folder in (REV, REPLACEMENT):
        m = load(folder / "manifest.json")
        if m["formal_effect_eligible"] or m["replay_eligible"]: raise ValueError("Unexpected eligibility")
        for name, digest in m["file_sha256"].items():
            if sha(folder / name) != digest: raise ValueError(f"Source hash mismatch: {folder / name}")
        if load(folder / "validation.json")["status"] != "passed": raise ValueError("Source validation failed")
    variants = rows(REV / "revised_variants.jsonl")
    selected = [x for x in variants if x["task_family"] == "evidence_insufficient" or x["source_variant_id"].startswith(("s_3e92f4335d69f54d3c656df2_same_", "expanded_citation_check_02_"))]
    replacements = rows(REPLACEMENT / "candidate_variants.jsonl")
    all_docs = {x["doc_id"]: x["text"] for x in rows(REV / "source_evidence.jsonl") + rows(REPLACEMENT / "source_evidence.jsonl")}
    if len(selected) != 12 or len(replacements) != 2: raise ValueError("Unexpected review scope")
    ei_questions = {
        "s_08e8938c350e35aa9a8fa6fb_same": ["When was Kenneth Bigley killed, according to the report?", "Does it name the group responsible for his killing?", "Does it say where his body was found?"],
        "s_1709052c2c393baf1346bd1f_same": ["What qualifying lap time does the report give for Kurt Busch?", "How many points ahead was he?", "Which team did he drive for?"],
        "expanded_evidence_insufficient_09": ["What calendar date is given for the Cabinet meeting?", "Which minister left during that reshuffle?", "Why did the reshuffle take place?"],
        "expanded_evidence_insufficient_10": ["What percentage of spam was domestic according to the study?", "Which organization conducted the study?", "How was the study's sample selected?"],
    }
    evidence_notes = {
        "ag_news_teacher_00005627": "Excerpt names Bigley, Iraq, Blair and victims' relatives, but not a date, responsible group or body location.",
        "ag_news_teacher_00003981": "Excerpt states Busch's pole on Friday and points-leader status, but no lap time, lead margin or team.",
        "ag_news_teacher_00001069": "Excerpt states Thursday and Milburn's return, but no calendar date, departing minister or reason for reshuffle.",
        "ag_news_teacher_00001160": "Headline says most spam is domestic; excerpt does not provide an exact percentage, organization or sampling method.",
    }
    reviews, proposals = [], []
    for item in selected + replacements:
        source_id = item.get("source_variant_id", item["variant_id"])
        docs = item["source_doc_ids"]
        if not set(docs) <= set(all_docs): raise ValueError(f"Missing source {source_id}")
        family = item["task_family"]
        new_queries = None
        if family == "evidence_insufficient":
            key = source_id.rsplit("_", 1)[0]
            new_queries = ei_questions[key][:item["target_turns"]]
            decision = "rewrite"
            note = evidence_notes[docs[0]] + (" Three consecutive unanswered questions remain a naturalness concern." if item["target_turns"] == 3 else " Weekday/qualitative details remain available where present, even without the exact requested fact.")
        elif source_id.startswith("expanded_crossdoc_replacement_oilstocks_3_"):
            new_queries = [t["query"] for t in item["turns"]]
            new_queries[2] = "In the jobs-report account, how many straight days had oil prices reached records, and what period does the other report give for the Dow's return above 10,000?"
            decision = "rewrite"
            note = "The source says the first close above 10,000 in three weeks; avoid presenting that as an exact elapsed interval."
        elif source_id.startswith("expanded_crossdoc_replacement_oilstocks_2_"):
            decision = "provisional_accept"
            note = "Jobs-report source states U.S. stocks fell; the other says stocks ended higher while investors shrugged off record crude. No event/date equivalence is asserted."
        elif source_id.startswith("s_3e92f4335d69f54d3c656df2_same_"):
            decision = "provisional_accept"
            note = "One source supplies $53 and household heating/gasoline, the other shares and market concerns/indexes; both IDs are needed."
        else:
            decision = "provisional_accept"
            note = "The source names Peace Rules, the colt's left front leg, and Belmont Park; the rewritten second turn requests a quote."
        reviews.append({"source_variant_id":source_id,"input_variant_id":item["variant_id"],"task_family":family,
                        "decision":decision,"source_refs":docs,"notes":note,"reviewer_kind":"codex_agent",
                        "reviewer_model_id":"Codex; immutable provider snapshot unavailable","human_reviewed":False,
                        "limitation":"Small development content review; not independent human gold or a service test."})
        if family == "evidence_insufficient" or source_id.startswith("expanded_crossdoc_replacement_oilstocks_"):
            new_id = source_id + "_targeted_20261102"
            turns = []
            for index, source_turn in enumerate(item["turns"]):
                turn = source_turn.copy()
                turn["request_id"] = "r_" + hashlib.sha256(f"{new_id}:{index + 1}:{turn['request_id']}".encode()).hexdigest()[:24]
                if new_queries is not None: turn["query"] = new_queries[index]
                if source_id.startswith("expanded_crossdoc_replacement_oilstocks_3_") and index == 2:
                    turn["reference_answer_suggestion"] = "Four straight days; the first close above 10,000 in three weeks."
                turns.append(turn)
            risks = list(item.get("risk_codes", []))
            if family == "evidence_insufficient" and item["target_turns"] == 3:
                risks.append("three_absent_answers_naturalness_pending")
            if source_id.startswith("expanded_crossdoc_replacement_oilstocks_"):
                risks.append("same_event_and_semantic_dependency_not_established")
            proposals.append({"variant_id":new_id,"source_variant_id":source_id,"input_variant_id":item["variant_id"],
                              "task_family":family,"target_turns":item["target_turns"],"source_doc_ids":docs,"turns":turns,
                              "risk_codes":sorted(set(risks)),"review_status":"pending","reviewed_by":None,
                              "formal_effect_eligible":False,"human_gold_eligible":False})
    if len(reviews) != 14 or len(proposals) != 10 or sum(len(x["turns"]) for x in proposals) != 25:
        raise ValueError("Unexpected output count")
    for item in proposals:
        for t in item["turns"]:
            if not set(t["gold_evidence_ids"]) <= set(item["source_doc_ids"]): raise ValueError("Evidence outside scope")
            if item["task_family"] == "cross_document_synthesis" and set(t["gold_evidence_ids"]) != set(item["source_doc_ids"]): raise ValueError("Cross-document gold incomplete")
    groups = {}
    for item in proposals:
        groups.setdefault(item["source_variant_id"].rsplit("_", 1)[0] if item["task_family"] == "evidence_insufficient" else "replacement", {})[item["target_turns"]] = item
    for key, group in groups.items():
        if set(group) != {2,3}: raise ValueError(f"Missing paired length: {key}")
        for a,b in zip(group[2]["turns"], group[3]["turns"][:2]):
            for field in ("query","reference_answer_suggestion","gold_evidence_ids"):
                if a[field] != b[field]: raise ValueError(f"Paired prefix mismatch: {key} {field}")
    OUT.mkdir()
    write_rows(OUT / "adjudication.jsonl", reviews)
    write_rows(OUT / "targeted_variants.jsonl", proposals)
    source_ids = sorted({doc for item in selected + replacements for doc in item["source_doc_ids"]})
    write_rows(OUT / "source_evidence.jsonl", [{"doc_id":doc,"text":all_docs[doc]} for doc in source_ids])
    files = ("adjudication.jsonl","targeted_variants.jsonl","source_evidence.jsonl")
    m = {"schema_version":1,"review_id":OUT.name,"status":"agent_reviewed_development_drafts_pending_human",
         "partition":"D-dev","reviewer_kind":"codex_agent","human_reviewed":False,"formal_effect_eligible":False,
         "source_rev2_manifest_sha256":sha(REV / "manifest.json"),"source_replacement_manifest_sha256":sha(REPLACEMENT / "manifest.json"),
         "builder_sha256":sha(Path(__file__)),"file_sha256":{name:sha(OUT / name) for name in files},
         "reviewed_versions":len(reviews),"new_draft_versions":len(proposals),"new_draft_turns":sum(len(x["turns"]) for x in proposals),
         "limitations":["Codex agent review is not human gold and does not independently validate its own proposed corrections.",
                        "Three consecutive absent answers remain a naturalness concern.",
                        "The replacement pairing's common factor does not establish shared event or independent sources.",
                        "No RAG, Judge or defense experiment was run."]}
    (OUT / "manifest.json").write_text(json.dumps(m, ensure_ascii=False, indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:m[k] for k in ("status","reviewed_versions","new_draft_versions","new_draft_turns")},ensure_ascii=False))

if __name__ == "__main__":
    main()
