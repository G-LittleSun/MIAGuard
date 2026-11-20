"""Verify D-dev session draft structure and write an interim selection report."""
import collections
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
def rows(name):
    raw = (HERE / name).read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        raise ValueError(f"unexpected BOM: {name}")
    return [json.loads(x) for x in raw.decode("utf-8").splitlines()]

inventory = rows("session_inventory.jsonl")
original_sources = rows("source_evidence.jsonl")
expanded_sources = rows("expanded_source_evidence.jsonl")
selection = rows("expanded_source_selection.jsonl")
same = rows("normal_variants.jsonl")
expanded = rows("expanded_variants.jsonl")
reviews = rows("session_review.jsonl") + rows("expanded_review.jsonl")
baseline = rows("baseline_review.jsonl")
errors = []
sources = {x["doc_id"]:x for x in original_sources + expanded_sources}
if len(sources) != len(original_sources) + len(expanded_sources): errors.append("source IDs overlap")
for s in sources.values():
    if hashlib.sha256(s["text"].encode("utf-8")).hexdigest() != s["text_sha256"]:
        errors.append(f"source text hash {s['doc_id']}")
index = ROOT / "data/vector_stores/defense_access_v1_candidate06/D-dev/ag_news/documents.jsonl"
index_manifest = json.loads((index.parent / "manifest.json").read_text(encoding="utf-8"))
if sha(index) != index_manifest["documents_sha256"]: errors.append("D-dev index document hash")
indexed = {}
for row in map(json.loads,index.read_text(encoding="utf-8").splitlines()):
    if row["doc_id"] in sources: indexed[row["doc_id"]] = row["text"]
# The original review evidence can contain whitespace normalization; compare normalized text only there.
normalize = lambda value: " ".join(value.split())
for doc_id, obj in sources.items():
    if doc_id not in indexed or normalize(indexed[doc_id]) != normalize(obj["text"]):
        errors.append(f"source not consistent with index {doc_id}")
if len(inventory)!=14 or len(original_sources)!=15 or len(selection)!=14 or len(expanded_sources)!=16:
    errors.append("unexpected source/session counts")
original_ids = {x["session_id"] for x in inventory}
expanded_ids = {x["session_id"] for x in selection}
if len(original_ids)!=14 or len(expanded_ids)!=14: errors.append("duplicate session IDs")
groups = collections.defaultdict(list)
all_variants = same + expanded
request_ids = set()
for v in all_variants:
    group = v["original_session_id"] if v["cohort"] == "same_source" else v["variant_id"].rsplit("_",1)[0]
    groups[(v["cohort"],group)].append(v)
    doc_ids = v["source_doc_ids"]
    if not set(doc_ids).issubset(sources): errors.append(f"missing source {v['variant_id']}")
    if v["human_reviewed"] or v["drafted_by"] != "codex_agent": errors.append(f"review identity {v['variant_id']}")
    if v["decision"] == "excluded_insufficient_distinct_facts":
        if v["turns"]: errors.append(f"excluded has turns {v['variant_id']}")
        continue
    if len(v["turns"]) != v["target_turns"]: errors.append(f"turn count {v['variant_id']}")
    for pos,t in enumerate(v["turns"],1):
        if t["turn"] != pos or t["request_id"] in request_ids: errors.append(f"turn identity {v['variant_id']}")
        request_ids.add(t["request_id"])
        if t["source_scope_ids"] != doc_ids or not set(t["gold_evidence_ids"]).issubset(doc_ids):
            errors.append(f"scope {v['variant_id']}")
        if t["answerable"] != (t["reference_answer_suggestion"] is not None): errors.append(f"answerability {v['variant_id']}")
        if t["answerable"] and not t["gold_evidence_ids"]: errors.append(f"empty gold {v['variant_id']}")
        if not t["answerable"] and t["gold_evidence_ids"]: errors.append(f"unanswerable gold {v['variant_id']}")
        if v["task_family"] == "cross_document_synthesis" and set(t["gold_evidence_ids"]) != set(doc_ids):
            errors.append(f"cross-document gold {v['variant_id']}")
        if any(k in t for k in ("membership_label","attack_type","target_doc_id")): errors.append(f"label leak {v['variant_id']}")
for key,vs in groups.items():
    if sorted(x["target_turns"] for x in vs) != [2,3]: errors.append(f"missing pair {key}")
    if len(vs) == 2 and all(v["turns"] for v in vs):
        two,three = sorted(vs,key=lambda x:x["target_turns"])
        for left,right in zip(two["turns"],three["turns"][:2]):
            if any(left[k] != right[k] for k in ("query","reference_answer_suggestion","gold_evidence_ids","source_scope_ids")):
                errors.append(f"unequal same-source prefix {key}")
variant_ids = [x["variant_id"] for x in all_variants]
if len(set(variant_ids)) != len(variant_ids) or set(variant_ids)!={x["variant_id"] for x in reviews}:
    errors.append("review/variant identity")
if {x["session_id"] for x in baseline} != original_ids: errors.append("baseline identity")
if len(request_ids)!=sum(len(x["turns"]) for x in all_variants): errors.append("request duplication")

# Count independent source-connected session groups; overlapping source means paired resampling.
parents={key:key for key in groups}
def find(x):
    while parents[x]!=x:
        parents[x]=parents[parents[x]];x=parents[x]
    return x
seen={}
for key, vs in groups.items():
    for source in vs[0]["source_doc_ids"]:
        if source in seen: parents[find(key)]=find(seen[source])
        else: seen[source]=key
components=len({find(x) for x in groups})
counts={}
for label,vs in (("same_source",same),("expanded_sources",expanded)):
    counts[label]={"session_groups":len({v["original_session_id"] if label=="same_source" else v["variant_id"].rsplit("_",1)[0] for v in vs}),
                   "two_turn_candidates":sum(v["target_turns"]==2 and bool(v["turns"]) for v in vs),
                   "three_turn_candidates":sum(v["target_turns"]==3 and bool(v["turns"]) for v in vs),
                   "excluded_three_turn":sum(v["target_turns"]==3 and not v["turns"] for v in vs),
                   "turns":sum(len(v["turns"]) for v in vs)}
if errors:
    print(json.dumps({"status":"failed","errors":errors},ensure_ascii=False,indent=2))
    raise SystemExit(1)
report={"schema_version":1,"status":"interim_pending_independent_content_review","final_length_selected":False,
 "cohort_counts":counts,"baseline_five_turn_sessions":len(baseline),"unique_source_documents":len(sources),
 "source_connected_session_groups":components,"unique_drafted_request_ids":len(request_ids),
 "review_counts":dict(collections.Counter(x["decision"] for x in reviews)),
 "five_turn_self_review_counts":dict(collections.Counter(x["decision"] for x in baseline)),
 "candidate_only_observation":"Two of 14 original-source sessions did not yield a three-turn draft without repeating facts; draft availability is not a measured acceptance rate.",
 "three_turn_session_judge":"Three-turn drafts exist, including four multi-turn-reading groups; actual Session/fusion scoring and quality remain untested.",
 "risks":["All new variants are self-drafted and require independent session-level review.",
          "The 27 source-connected groups only merge shared doc IDs; near-duplicate relationships have not been audited for this pilot.",
          "Repeated evidence-insufficient questions may lack conversational progression.",
          "One expanded cross-document pair shares an energy topic without a documented causal relationship.",
          "Source truncation, inferred title boundaries and typo-sensitive answers need review.",
          "Expanded source pairs differ from the same-source cohort and cannot estimate a length effect.",
          "New problem/answer variants are review-only artifacts, not online request files or formal gold."],
 "next":"Obtain independent review of the complete paired sessions and adjudicate issues; only then record a length/coverage decision and update the protocol before T10-D."}
report_path=HERE/"selection_report.json"
report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
input_files=["session_inventory.jsonl","source_evidence.jsonl","normal_variants.jsonl","session_review.jsonl",
             "expanded_source_evidence.jsonl","expanded_source_selection.jsonl","expanded_variants.jsonl","expanded_review.jsonl",
             "baseline_review.jsonl","draft_same_source.py","draft_expanded.py","review_baseline.py","verify_and_summarize.py","selection_report.json",
             "DECISION_ZH.md","REVIEW_GUIDE_ZH.md"]
validation={"schema_version":1,"status":"passed","errors":[],"scope":"identity, hashes, line counts, variant pairing, source scope and structural evidence; not factual entailment or human review",
            "files_sha256":{name:sha(HERE/name) for name in input_files},"d_dev_index_documents_sha256":sha(index),
            "candidate_request_count":len(request_ids),"limitations":report["risks"]}
vp=HERE/"validation.json"
vp.write_text(json.dumps(validation,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
mp=HERE/"pilot_manifest.json"
manifest=json.loads(mp.read_text(encoding="utf-8"))
manifest.update(status="in_progress_pending_independent_review",d_dev_index_documents_sha256=sha(index),
                files_sha256={**validation["files_sha256"],"validation.json":sha(vp)},
                expanded_sessions=len(selection),expanded_unique_source_documents=len(expanded_sources),
                candidate_session_variants=sum(bool(x["turns"]) for x in all_variants),
                excluded_session_variants=sum(not x["turns"] for x in all_variants),
                draft_request_count=len(request_ids),source_connected_session_groups=components)
mp.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"status":validation["status"],"same_source":counts["same_source"],"expanded":counts["expanded_sources"],
                  "source_documents":len(sources),"source_connected_groups":components,"requests":len(request_ids)},ensure_ascii=False))
