"""Run a controlled focus-disambiguation check; not a defense benchmark."""
import argparse
import hashlib
import json
import random
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from run_t10c_history_ablation import ENDPOINT, MODEL, MODEL_DIGEST, SEED, SYSTEM, read_api, sha

T10 = Path(__file__).resolve().parent
PILOT = T10 / "context_focus_pilot_20261102_01"

def load(path):
    return json.loads(path.read_text(encoding="utf-8"))

def rows(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]

def write_json(path,value):
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

def prepare():
    manifest = load(PILOT/"manifest.json")
    for name,digest in manifest["files_sha256"].items():
        if sha(PILOT/name)!=digest:raise ValueError(f"Pilot input changed: {name}")
    variants = rows(PILOT/"variants.jsonl")
    sources = {x["doc_id"]:x["text"] for x in rows(PILOT/"source_evidence.jsonl")}
    if len(variants)!=2 or {x["focus"] for x in variants}!={"falling","rising"}:
        raise ValueError("Unexpected focus cases")
    if variants[0]["source_doc_ids"]!=variants[1]["source_doc_ids"] or variants[0]["turns"][2]["query"]!=variants[1]["turns"][2]["query"]:
        raise ValueError("Source or target not paired")
    requests=[]; labels=[]
    for variant in variants:
        source="\n\n".join(sources[x] for x in variant["source_doc_ids"])
        first,second,target=variant["turns"]
        expected=target["reference_answer_suggestion"]
        history=[{"query":x["query"],"answer":x["reference_answer_suggestion"]} for x in (first,second)]
        if expected.casefold() in " ".join(str(x) for x in history).casefold():raise ValueError("Target leaked into history")
        for condition in ("with_history","without_history"):
            hist="\n".join(f"User: {x['query']}\nAssistant: {x['answer']}" for x in history) if condition=="with_history" else "(none)"
            prompt=f"SOURCE:\n{source}\n\nPRIOR CONVERSATION:\n{hist}\n\nCURRENT QUESTION:\n{target['query']}\n\nAnswer:"
            identity=variant["variant_id"]+":"+condition
            rid="af_"+hashlib.sha256(identity.encode()).hexdigest()[:24]
            requests.append({"request_id":rid,"variant_id":variant["variant_id"],"condition":condition,"prompt":prompt,
                             "source_doc_ids":variant["source_doc_ids"]})
            labels.append({"request_id":rid,"focus":variant["focus"],
                           "expected_with_history":expected,
                           "expected_without_history":"Both weekdays are possible; report the missing focus rather than assert one weekday.",
                           "human_reviewed":False})
    without=[x["prompt"] for x in requests if x["condition"]=="without_history"]
    if len(without)!=2 or without[0]!=without[1]:raise ValueError("No-history prompts must be identical")
    models=read_api("/api/tags").get("models",[])
    model=next((x for x in models if x.get("name")==MODEL),None)
    if not model or model.get("digest")!=MODEL_DIGEST:raise ValueError("Local model identity changed")
    random.Random(SEED).shuffle(requests)
    return requests,labels,model

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--execute",action="store_true");ap.add_argument("--output",required=True,type=Path)
    args=ap.parse_args();requests,labels,model=prepare()
    if not args.execute:
        print(json.dumps({"status":"preflight_passed_no_generation","requests":4,"identical_no_history_prompts":True}));return
    out=args.output.resolve()
    if out.exists():raise FileExistsError(out)
    out.mkdir(parents=True);(out/"logs").mkdir()
    spec={"schema_version":1,"run_id":out.name,"purpose":"Source-fixed paired focus disambiguation",
          "partition":"D-dev","analysis_role":"engineering_only","formal_effect_eligible":False,
          "model_name":MODEL,"model_digest":MODEL_DIGEST,"model_details":model.get("details"),"system_prompt":SYSTEM,
          "temperature":0,"seed":SEED,"num_predict":96,"source_pilot_sha256":sha(PILOT/"manifest.json"),
          "runner_sha256":sha(Path(__file__)),"dependency_runner_sha256":sha(T10/"run_t10c_history_ablation.py"),
          "expected_requests":4,"independent_source_groups":1,"no_history_prompts_identical":True,
          "predeclared_rubric":"With history: the correct focused weekday is Friday for falling, Wednesday for rising. Without history: either an explicit ambiguity or both possibilities is acceptable; a lone weekday is an unsupported guess, even if it matches one variant's target.",
          "limitations":["One paired example, two related documents; not a representative dataset.","No-history prompts are duplicates and must not be counted as independent samples.","Teacher-forced history, not generated dialog; agent review, not human gold.","Local Q4 model is not frozen BF16 Judge; no Session/fusion, retrieval, attack or defense effect is measured."]}
    write_json(out/"experiment_spec.json",spec)
    for name,data in (("requests.jsonl",requests),("labels.jsonl",labels)):
        (out/name).write_text("".join(json.dumps(x,ensure_ascii=False)+"\n" for x in data),encoding="utf-8")
    manifest={"run_id":out.name,"status":"running","started_at_utc":datetime.now(timezone.utc).isoformat(),
              "expected_requests":4,"formal_effect_eligible":False,"experiment_spec_sha256":sha(out/"experiment_spec.json"),
              "requests_sha256":sha(out/"requests.jsonl"),"labels_sha256":sha(out/"labels.jsonl")}
    write_json(out/"run_manifest.json",manifest);completed=failed=0
    with (out/"events.jsonl").open("w",encoding="utf-8") as events,(out/"logs/run.log").open("w",encoding="utf-8") as log:
        for i,request in enumerate(requests,1):
            payload={"model":MODEL,"system":SYSTEM,"prompt":request["prompt"],"stream":False,"keep_alive":"5m",
                     "options":{"temperature":0,"seed":SEED,"num_predict":96}}
            start=time.perf_counter()
            try:
                req=urllib.request.Request(ENDPOINT+"/api/generate",data=json.dumps(payload).encode("utf-8"),headers={"Content-Type":"application/json"})
                with urllib.request.urlopen(req,timeout=150) as response:raw=json.load(response)
                answer=raw.get("response")
                if not isinstance(answer,str) or not answer.strip():raise ValueError("Empty response")
                event={"request_id":request["request_id"],"variant_id":request["variant_id"],"condition":request["condition"],"status":"completed","response":answer,"api_response":raw,"elapsed_seconds":round(time.perf_counter()-start,3)};completed+=1
            except Exception as exc:
                event={"request_id":request["request_id"],"variant_id":request["variant_id"],"condition":request["condition"],"status":"failed","error_type":type(exc).__name__,"error":str(exc),"elapsed_seconds":round(time.perf_counter()-start,3)};failed+=1
            events.write(json.dumps(event,ensure_ascii=False)+"\n");events.flush()
            line=f"{i}/4 {request['condition']} {event['status']} {event['elapsed_seconds']}s"
            print(line,flush=True);log.write(line+"\n");log.flush()
    latest=next((x for x in read_api("/api/tags").get("models",[]) if x.get("name")==MODEL),None)
    unchanged=bool(latest and latest.get("digest")==MODEL_DIGEST)
    manifest.update(status="complete" if failed==0 and unchanged else "complete_with_failures_or_identity_mismatch",
                    finished_at_utc=datetime.now(timezone.utc).isoformat(),completed_requests=completed,failed_requests=failed,
                    model_identity_unchanged=unchanged,events_sha256=sha(out/"events.jsonl"),log_sha256=sha(out/"logs/run.log"))
    write_json(out/"run_manifest.json",manifest)
    print(json.dumps({"run_id":out.name,"status":manifest["status"],"completed":completed,"failed":failed}),flush=True)

if __name__=="__main__":main()
