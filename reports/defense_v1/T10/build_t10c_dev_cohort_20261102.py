"""Assemble a provisional, non-replayable D-dev cohort with explicit lineage."""
import collections
import hashlib
import json
from pathlib import Path

T10=Path(__file__).resolve().parent
REV=T10/"session_length_pilot_rev2_20261102_01"
TARGETED=T10/"session_length_pilot_targeted_20261102_01"
FOCUS=T10/"context_focus_pilot_20261102_01"
USAGE=T10/"normal_source_usage_20261102_01"
REPLACEMENT=T10/"crossdoc_replacement_20261102_01"
OUT=T10/"session_length_dev_cohort_20261102_01"

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding="utf-8"))
def rows(p):return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines()]
def dump(path,data):path.write_text("".join(json.dumps(x,ensure_ascii=False)+"\n" for x in data),encoding="utf-8")

def main():
    if OUT.exists():raise FileExistsError(OUT)
    for folder,field in ((REV,"file_sha256"),(TARGETED,"file_sha256"),(FOCUS,"files_sha256"),(REPLACEMENT,"file_sha256")):
        m=load(folder/"manifest.json")
        for name,digest in m[field].items():
            if sha(folder/name)!=digest:raise ValueError(f"Input changed: {folder/name}")
        if m["formal_effect_eligible"]:raise ValueError("Unexpected formal eligibility")
    usage_manifest=load(USAGE/"manifest.json")
    if sha(USAGE/"source_usage.jsonl")!=usage_manifest["source_usage_sha256"]:raise ValueError("Source usage changed")
    usage={x["doc_id"]:x for x in rows(USAGE/"source_usage.jsonl")}
    rev=rows(REV/"revised_variants.jsonl")
    targeted=rows(TARGETED/"targeted_variants.jsonl")
    focus=rows(FOCUS/"variants.jsonl")
    selected=[];excluded=[]
    for item in rev:
        sid=item["source_variant_id"]
        if item["target_turns"]!=2:
            excluded.append({"variant_id":item["variant_id"],"reason":"two_turn_development_baseline_or_previously_excluded"});continue
        if item["task_family"]=="evidence_insufficient":
            excluded.append({"variant_id":item["variant_id"],"reason":"replaced_by_targeted_wording"});continue
        if sid=="expanded_cross_document_synthesis_14_2":
            excluded.append({"variant_id":item["variant_id"],"reason":"weak_pair_replaced_for_provisional_cohort"});continue
        selected.append(("rev2",item))
    for item in targeted:
        if item["target_turns"]==2:selected.append(("targeted",item))
        else:excluded.append({"variant_id":item["variant_id"],"reason":"not_selected_for_two_turn_development_baseline"})
    selected.extend(("context_focus",x) for x in focus)
    if len(selected)!=30 or sum(len(x[1]["turns"]) for x in selected)!=62:raise ValueError("Unexpected cohort shape")
    if sum(x[0]=="rev2" for x in selected)!=23 or sum(x[0]=="targeted" for x in selected)!=5:raise ValueError("Unexpected provenance")
    source_map={}
    for folder in (REV,TARGETED,FOCUS):
        for item in rows(folder/"source_evidence.jsonl"):
            docid=item["doc_id"];text=item["text"]
            if docid in source_map and " ".join(source_map[docid].split())!=" ".join(text.split()):
                raise ValueError(f"Conflicting source: {docid}")
            source_map[docid]=text
    cohort=[];session_ids=set();request_ids=set()
    for origin,item in selected:
        variant=item["variant_id"]
        session_id="ds_"+hashlib.sha256(("t10c-dev-20261102:"+variant).encode()).hexdigest()[:24]
        if session_id in session_ids:raise ValueError("Duplicate session ID")
        session_ids.add(session_id);turns=[]
        for index,old in enumerate(item["turns"],1):
            turn=old.copy();prior=turn["request_id"]
            turn["request_id"]="dq_"+hashlib.sha256((session_id+":"+str(index)+":"+prior).encode()).hexdigest()[:24]
            if turn["request_id"] in request_ids:raise ValueError("Duplicate request")
            request_ids.add(turn["request_id"]);turn["source_request_id"]=prior;turns.append(turn)
            if turn["turn"]!=index or turn["source_scope_ids"]!=item["source_doc_ids"]:raise ValueError("Turn/source mismatch")
            if not set(turn["gold_evidence_ids"])<=set(item["source_doc_ids"]):raise ValueError("Evidence mismatch")
            if not turn["answerable"] and (turn["reference_answer_suggestion"] is not None or turn["gold_evidence_ids"]):raise ValueError("Unanswerable mismatch")
        docids=item["source_doc_ids"]
        if any(docid not in source_map or docid not in usage for docid in docids):raise ValueError("Missing source provenance")
        cohort.append({"session_id":session_id,"source_variant_id":variant,"source_artifact":origin,
                       "task_family":item.get("task_family",item.get("family")),"source_doc_ids":docids,
                       "source_roles":{docid:usage[docid]["source_role"] for docid in docids},"turns":turns,
                       "selection_reason":"three_turn_focus_diagnostic" if origin=="context_focus" else "two_turn_development_baseline",
                       "review_status":"pending","reviewed_by":None,"human_gold_eligible":False,"formal_effect_eligible":False})
    families=collections.Counter(x["task_family"] for x in cohort)
    if families.get("multi_turn_reading")!=6 or any(families.get(x)!=4 for x in ("citation_check","cross_document_synthesis","evidence_insufficient","exact_entity_number","single_fact","topic_summary")):
        raise ValueError("Unexpected family coverage")
    used=sorted({doc for item in cohort for doc in item["source_doc_ids"]})
    if len(used)!=31:raise ValueError("Unexpected unique source count")
    parent={x["session_id"]:x["session_id"] for x in cohort};seen={}
    def find(x):
        while parent[x]!=x:parent[x]=parent[parent[x]];x=parent[x]
        return x
    def union(a,b):
        a,b=find(a),find(b)
        if a!=b:parent[max(a,b)]=min(a,b)
    for item in cohort:
        for docid in item["source_doc_ids"]:
            for kind,value in (("doc",docid),("parent",usage[docid]["parent_doc_id"]),("duplicate",usage[docid]["duplicate_group_id"])):
                key=(kind,value)
                if key in seen:union(item["session_id"],seen[key])
                else:seen[key]=item["session_id"]
    groups=collections.defaultdict(list)
    for item in cohort:groups[find(item["session_id"])].append(item["session_id"])
    OUT.mkdir()
    dump(OUT/"cohort.jsonl",cohort)
    dump(OUT/"source_evidence.jsonl",[{"doc_id":docid,"text":source_map[docid],"source_role":usage[docid]["source_role"]} for docid in used])
    dump(OUT/"excluded_variants.jsonl",excluded)
    dependency={"base_group_count":len(groups),"groups":[sorted(x) for x in groups.values()],
                "rule":"connect source session on shared doc, parent or pre-existing duplicate group",
                "limitations":["Same event/semantic relations beyond existing groups remain unreviewed.","Two focus variants share one source group and do not supply independent documents."]}
    (OUT/"dependency_groups.json").write_text(json.dumps(dependency,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    names=("cohort.jsonl","source_evidence.jsonl","excluded_variants.jsonl","dependency_groups.json")
    result={"schema_version":1,"cohort_id":OUT.name,"status":"provisional_d_dev_content_review_pending_formal_gold",
            "partition":"D-dev","formal_effect_eligible":False,"human_gold_complete":False,"replay_eligible":False,
            "selection_policy":"28 two-turn development-baseline sessions plus 2 three-turn paired focus diagnostics; not a final dataset-wide length rule.",
            "sessions":len(cohort),"requests":len(request_ids),"unique_sources":len(used),"base_dependency_groups":len(groups),
            "session_family_counts":dict(families),"source_role_counts":dict(collections.Counter(usage[x]["source_role"] for x in used)),
            "input_manifest_sha256":{folder.name:sha(folder/"manifest.json") for folder in (REV,TARGETED,FOCUS,USAGE,REPLACEMENT)},
            "builder_sha256":sha(Path(__file__)),"files_sha256":{name:sha(OUT/name) for name in names},
            "limitations":["Candidate sessions remain pending and are not human gold.",
                           "Six multi-turn sessions vs four for other families; two extra three-turn sessions share one source group.",
                           "Two/three turns are not a controlled length comparison in this selected cohort; use original paired pilot for that question.",
                           "Exact/parent/duplicate groups do not prove semantic or event independence.",
                           "Shared-background articles cannot later be reused as A-cal/V/T normal question sources.",
                           "No full benchmark or actual Session/fusion policy effect is demonstrated."]}
    (OUT/"manifest.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({key:result[key] for key in ("status","sessions","requests","unique_sources","base_dependency_groups","session_family_counts","source_role_counts")},ensure_ascii=False))

if __name__=="__main__":main()
