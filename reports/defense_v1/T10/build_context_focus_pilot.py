"""Draft a balanced, source-fixed context-disambiguation pilot for D-dev."""
import hashlib
import json
from pathlib import Path

T10 = Path(__file__).resolve().parent
SOURCE = T10 / "crossdoc_replacement_20261102_01"
OUT = T10 / "context_focus_pilot_20261102_01"

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    if OUT.exists(): raise FileExistsError(OUT)
    manifest = json.loads((SOURCE / "manifest.json").read_text(encoding="utf-8"))
    for name,digest in manifest["file_sha256"].items():
        if sha(SOURCE / name) != digest: raise ValueError(f"Source changed: {name}")
    source = [json.loads(x) for x in (SOURCE / "source_evidence.jsonl").read_text(encoding="utf-8").splitlines()]
    if [x["doc_id"] for x in source] != ["ag_news_teacher_00006603","ag_news_teacher_00007349"]:
        raise ValueError("Unexpected source identity")
    ids = [x["doc_id"] for x in source]
    q1 = "What contrasting U.S. stock movements do the two reports describe?"
    a1 = "One report says stocks fell; the other says they ended higher."
    q3 = "On which weekday did the stock movement in the report we just focused on occur?"
    specs = [
        ("falling", "Focusing on the report where stocks fell, what did the jobs report say?",
         "Employment growth unexpectedly slowed.", "Friday", ids[0]),
        ("rising", "Focusing on the report where stocks rose, what did investors shrug off?",
         "Record crude oil prices.", "Wednesday", ids[1]),
    ]
    output = []
    for focus,q2,a2,a3,target_doc in specs:
        variant_id = f"context_focus_oil_stocks_{focus}_20261102"
        values = [(q1,a1,ids,"contrast in reported stock movements"),
                  (q2,a2,[target_doc],"explicitly select a report and add a distinct detail"),
                  (q3,a3,[target_doc],"weekday of the previously selected report")]
        turns=[]
        for turn,(question,answer,gold,novelty) in enumerate(values,1):
            request_id="r_"+hashlib.sha256(f"{variant_id}:{turn}".encode()).hexdigest()[:24]
            turns.append({"turn":turn,"request_id":request_id,"query":question,"answerable":True,
                          "reference_answer_suggestion":answer,"gold_evidence_ids":gold,
                          "source_scope_ids":ids,"new_information":novelty})
        output.append({"variant_id":variant_id,"family":"multi_turn_reading","focus":focus,
                       "source_doc_ids":ids,"turns":turns,"review_status":"pending","reviewed_by":None,
                       "formal_effect_eligible":False,"human_gold_eligible":False,
                       "limitations":["Teacher-forced history is not a natural user transcript.",
                                      "Both variants share source documents and are a paired group, not independent documents.",
                                      "The source reports need not describe the same event; no causal/date ordering is asserted."]})
    if output[0]["turns"][2]["query"] != output[1]["turns"][2]["query"]:
        raise ValueError("Third-turn questions must match")
    if output[0]["turns"][2]["reference_answer_suggestion"] == output[1]["turns"][2]["reference_answer_suggestion"]:
        raise ValueError("The two focused targets must differ")
    OUT.mkdir()
    for name, data in (("variants.jsonl",output),("source_evidence.jsonl",source)):
        (OUT/name).write_text("".join(json.dumps(x,ensure_ascii=False)+"\n" for x in data),encoding="utf-8")
    result={"schema_version":1,"pilot_id":OUT.name,"status":"draft_agent_review_pending",
            "partition":"D-dev","formal_effect_eligible":False,"human_gold_complete":False,"replay_eligible":False,
            "purpose":"Compare two prior conversation foci under identical source and third question; no-history input is ambiguous.",
            "source_manifest_sha256":sha(SOURCE/"manifest.json"),"builder_sha256":sha(Path(__file__)),
            "variants":2,"turns":6,"unique_source_documents":2,"source_connected_groups":1,
            "without_history_expected":"The intended report is not identifiable: Friday and Wednesday are both plausible; a single weekday alone is an unsupported guess.",
            "files_sha256":{name:sha(OUT/name) for name in ("variants.jsonl","source_evidence.jsonl")}}
    (OUT/"manifest.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({key:result[key] for key in ("status","variants","turns","unique_source_documents","source_connected_groups")}))

if __name__ == "__main__":
    main()
