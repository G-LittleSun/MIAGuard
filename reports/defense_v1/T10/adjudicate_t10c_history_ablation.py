"""Save explicit Codex judgments of the 14 observed D-dev ablation answers."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RUN = ROOT / "data/defense_v1_runs/t10c-history-ablation-20261102-01"
REV = ROOT / "reports/defense_v1/T10/session_length_pilot_rev2_20261102_01"

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def load(path):
    return json.loads(path.read_text(encoding="utf-8"))

def rows(path):
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines()]

# Each pair is the exact response observed in the run, with source-based reasoning.
# The assertions guard against silently applying these judgments to a different run.
JUDGMENTS = {
 "s_35f642a015443be4b6938941_same_3_rev2_20261102": {
  "with_history":"Both Mac and PC formats.",
  "without_history":'The "Make Love Not Spam" screensaver was available in both Mac and PC formats.',
  "rationale":"Source explicitly says the screensaver is available in both Mac and PC formats; both answers identify both platforms."},
 "expanded_single_fact_08_3_rev2_20261102": {
  "with_history":"California", "without_history":"California",
  "rationale":"Source identifies John Garamen as California's insurance commissioner; both answers identify the state."},
 "expanded_multi_turn_reading_06_3_rev2_20261102": {
  "with_history":"The article assesses Pete Carroll and Bill Belichick as arguably the most successful football coaches in America right now.",
  "without_history":"The article assesses Pete Carroll and Bill Belichick as arguably the most successful football coaches in America right now.",
  "rationale":"Source uses the same qualified assessment for both coaches; both answers retain 'arguably'."},
 "s_09006cbd05dd713ca18ac43b_same_3_rev2_20261102": {
  "with_history":"About two years before IBM's announcement, a Japanese supercomputer claimed the title.",
  "without_history":"About two years before IBM's announcement, a Japanese supercomputer claimed the title.",
  "rationale":"Source says the Japanese machine claimed the title some two years earlier; both answers preserve the approximate interval and referent."},
 "expanded_citation_check_01_3_rev2_20261102": {
  "with_history":"Monday.", "without_history":"Monday",
  "rationale":"Source says President Bush signed the legislation Monday; both answers give that weekday."},
 "s_0036417c86948330e11bae92_same_3_rev2_20261102": {
  "with_history":"The source text discusses pension funds, endowments, and other big activist investors in the context of corporate governance campaigns.",
  "without_history":"The source discusses the influence of pension funds, endowments, and other big activist investors in corporate governance campaigns.",
  "rationale":"Source explicitly describes their influence in corporate governance campaigns; both responses name the requested activity."},
 "expanded_multi_turn_reading_05_3_rev2_20261102": {
  "with_history":"Chechen deputy prime minister Ramzan Kadyrov made that statement, according to news reports.",
  "without_history":"Ramzan Kadyrov made that statement, according to news reports.",
  "rationale":"Source attributes the statement to Ramzan Kadyrov. The shorter answer still identifies the requested person."},
}

def main():
    manifest = load(RUN / "run_manifest.json")
    if manifest["status"] != "complete" or not manifest["model_identity_unchanged"]:
        raise ValueError("Run not complete or model identity changed")
    for name, field in (("experiment_spec.json","experiment_spec_sha256"),("requests.jsonl","requests_sha256"),
                        ("labels.jsonl","labels_sha256"),("events.jsonl","events_sha256")):
        if sha(RUN / name) != manifest[field]: raise ValueError(f"Run artifact hash mismatch: {name}")
    events, requests, labels = rows(RUN / "events.jsonl"), rows(RUN / "requests.jsonl"), rows(RUN / "labels.jsonl")
    by_request = {x["request_id"]:x for x in requests}
    by_label = {x["request_id"]:x for x in labels}
    if len(events)!=14 or set(by_request)!=set(by_label) or {x["request_id"] for x in events}!=set(by_request):
        raise ValueError("Incomplete run identity")
    if {x["variant_id"] for x in events} != set(JUDGMENTS): raise ValueError("Unexpected cases")
    grouped = {}
    graded = []
    for event in events:
        if event["status"] != "completed": raise ValueError("A request failed")
        case, condition = event["variant_id"], event["condition"]
        if event["response"] != JUDGMENTS[case][condition]: raise ValueError(f"Unexpected answer: {case} {condition}")
        request = by_request[event["request_id"]]
        label = by_label[event["request_id"]]
        if request["variant_id"] != case or request["condition"] != condition: raise ValueError("Request identity mismatch")
        grouped.setdefault(case,{})[condition] = event["response"]
        graded.append({"request_id":event["request_id"],"variant_id":case,"condition":condition,
                       "response":event["response"],"reference_answer_suggestion":label["reference_answer_suggestion"],
                       "source_doc_ids":request["source_doc_ids"],"agent_judgment":"supported_and_answers_question",
                       "rationale":JUDGMENTS[case]["rationale"],"reviewer_kind":"codex_agent","human_reviewed":False})
    for case, pair in grouped.items():
        if set(pair) != {"with_history","without_history"}: raise ValueError(f"Missing pair: {case}")
    graded_path = RUN / "agent_adjudication.jsonl"
    summary_path = RUN / "agent_diagnostic_summary.json"
    assessment_path = RUN / "assessment_manifest.json"
    if any(x.exists() for x in (graded_path,summary_path,assessment_path)): raise FileExistsError("Assessment outputs already exist")
    graded_path.write_text("".join(json.dumps(x,ensure_ascii=False)+"\n" for x in graded),encoding="utf-8")
    summary = {"schema_version":1,"run_id":manifest["run_id"],"analysis_role":"engineering_only",
               "model_name":"qwen2.5:latest","model_digest":"845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e",
               "cases":7,"completed_requests":14,"failed_requests":0,
               "agent_supported_by_condition":{"with_history":7,"without_history":7},
               "agent_pairs_supported_both":7,"human_reviewed":False,"formal_effect_eligible":False,
               "interpretation":"In these seven source-fixed cases this Q4 model produced source-supported answers with and without teacher-forced history; this observation does not establish general context independence.",
               "limitations":["Seven cases were selected for apparent references; they are not representative.",
                              "Same fixed source text in both conditions can itself resolve anaphora.",
                              "Teacher-forced prior answers are proposed answers, not real previous generated service responses.",
                              "Codex performed the answer assessment; it is not human gold or an independent human study.",
                              "No RAG retrieval, Judge Session/fusion, access policy, membership attack or defense effect was measured.",
                              "Qwen2.5 Q4_K_M Ollama model is not the original frozen BF16 Judge."]}
    summary_path.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    assessment={"schema_version":1,"reviewer_kind":"codex_agent","human_reviewed":False,
                "source_run_manifest_sha256":sha(RUN / "run_manifest.json"),"source_events_sha256":sha(RUN / "events.jsonl"),
                "reviewer_script_sha256":sha(Path(__file__)),"output_sha256":{graded_path.name:sha(graded_path),summary_path.name:sha(summary_path)}}
    assessment_path.write_text(json.dumps(assessment,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":"agent_adjudication_complete","cases":7,"requests":14,"supported_with":7,"supported_without":7,"human_reviewed":False},ensure_ascii=False))

if __name__ == "__main__":
    main()
