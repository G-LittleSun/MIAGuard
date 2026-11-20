"""Save source-grounded agent judgments for the focus-disambiguation run."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
RUN=ROOT/"data/defense_v1_runs/t10c-context-focus-20261102-01"
PILOT=ROOT/"reports/defense_v1/T10/context_focus_pilot_20261102_01"

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def load(path):return json.loads(path.read_text(encoding="utf-8"))
def rows(path):return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines()]

def main():
    manifest=load(RUN/"run_manifest.json")
    if manifest["status"]!="complete" or not manifest["model_identity_unchanged"]:raise ValueError("Run incomplete")
    for name,key in (("experiment_spec.json","experiment_spec_sha256"),("requests.jsonl","requests_sha256"),
                     ("labels.jsonl","labels_sha256"),("events.jsonl","events_sha256")):
        if sha(RUN/name)!=manifest[key]:raise ValueError(f"Run file changed: {name}")
    source={x["doc_id"]:x["text"] for x in rows(PILOT/"source_evidence.jsonl")}
    if "stocks fell on Friday" not in source["ag_news_teacher_00006603"]:
        raise ValueError("Falling weekday not supported by source")
    if "stocks ended higher on Wednesday" not in source["ag_news_teacher_00007349"]:
        raise ValueError("Rising weekday not supported by source")
    req={x["request_id"]:x for x in rows(RUN/"requests.jsonl")}
    label={x["request_id"]:x for x in rows(RUN/"labels.jsonl")}
    events=rows(RUN/"events.jsonl")
    if len(events)!=4 or set(req)!=set(label) or {e["request_id"] for e in events}!=set(req):raise ValueError("Request mismatch")
    without=[x["prompt"] for x in req.values() if x["condition"]=="without_history"]
    if len(without)!=2 or without[0]!=without[1]:raise ValueError("Without-history prompts differ")
    expected={
      ("rising","with_history"):"The stock movement in the report we just focused on occurred on Wednesday.",
      ("falling","with_history"):"The stock movement in the report we just focused on occurred on Friday.",
      ("rising","without_history"):"Friday",("falling","without_history"):"Friday"}
    graded=[]
    for event in events:
        rid=event["request_id"];condition=event["condition"];focus=label[rid]["focus"]
        if event["status"]!="completed" or event["response"]!=expected[(focus,condition)]:raise ValueError("Unexpected result")
        if condition=="with_history":
            judgment="supported_focus_consistent"
            rationale="The fixed history selected this report, whose source gives the returned weekday."
        else:
            judgment="unresolved_focus_single_weekday_guess"
            rationale="The same no-history prompt contains Friday and Wednesday in different reports and does not identify a selected report; a lone Friday cannot resolve the referent, regardless of accidental agreement with either label."
        graded.append({"request_id":rid,"variant_id":event["variant_id"],"condition":condition,"focus":focus,
                       "response":event["response"],"agent_judgment":judgment,"rationale":rationale,
                       "reviewer_kind":"codex_agent","human_reviewed":False})
    paths=[RUN/"agent_adjudication.jsonl",RUN/"agent_diagnostic_summary.json",RUN/"assessment_manifest.json"]
    if any(p.exists() for p in paths):raise FileExistsError("Assessment outputs exist")
    paths[0].write_text("".join(json.dumps(x,ensure_ascii=False)+"\n" for x in graded),encoding="utf-8")
    summary={"schema_version":1,"run_id":manifest["run_id"],"analysis_role":"engineering_only","formal_effect_eligible":False,
             "source_connected_groups":1,"focused_history_conditions":2,"requests_with_history":2,
             "agent_with_history_focus_consistent":2,"requests_without_history":2,"unique_without_history_prompts":1,
             "agent_without_history_responses_acknowledging_ambiguity":0,
             "observed_without_history_response":"Friday in both repeated requests",
             "interpretation":"For this one paired example and this local model, teacher-forced history selected the correct weekday under both focuses; the identical no-history prompt received an unsupported single-focus guess twice.",
             "limitations":["One source-connected example, not a population estimate.","The two no-history requests are identical and correlated, not two independent samples.",
                            "Source order, prompt wording, model and teacher-forced history can affect the response.",
                            "No human gold, real dialog history, RAG retrieval, Judge Session/fusion, attack or defense effect was measured.",
                            "Local Q4 model differs from the frozen BF16 Judge."]}
    paths[1].write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    assessment={"reviewer_kind":"codex_agent","human_reviewed":False,"source_run_manifest_sha256":sha(RUN/"run_manifest.json"),
                "source_events_sha256":sha(RUN/"events.jsonl"),"reviewer_script_sha256":sha(Path(__file__)),
                "output_sha256":{p.name:sha(p) for p in paths[:2]}}
    paths[2].write_text(json.dumps(assessment,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":"agent_adjudication_complete","with_history_focus_consistent":2,"without_history_unique_prompts":1,"without_history_ambiguity_acknowledged":False,"human_reviewed":False}))

if __name__=="__main__":main()
