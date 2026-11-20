"""Verify a local defense run and produce paired development diagnostics."""

import argparse
from collections import Counter, defaultdict
from hashlib import sha256
import json
import math
from pathlib import Path
from statistics import median

from diagnose_masked_fast_pilot import diagnose
from miaguard.metrics import extract_yes_no_unknown


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def rows(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def summarize(cases):
    completed = [row for row in cases if row["status"] == "complete"]
    observed = [row for row in completed if row["risk_source"]]
    attack = [row for row in completed if row["traffic"] != "benign"]
    normal = [row for row in completed if row["traffic"] == "benign"]
    latency = sorted(row["latency_ms"] for row in completed)
    masked = [row["masked"] for row in attack if row["masked"] is not None]
    return {
        "expected": len(cases), "completed": len(completed),
        "failed": sum(row["status"] == "failed" for row in cases),
        "skipped": sum(row["status"] == "skipped" for row in cases),
        "actions": Counter(row["action"] for row in completed),
        "risk_sources": Counter(row["risk_source"] for row in observed),
        "risk_triggers": sum(row["risk_triggered"] is True for row in observed),
        "observed_with_type": sum(bool(row["predicted_types"]) for row in observed),
        "attack_risk_triggers": sum(row["risk_triggered"] is True for row in attack),
        "attack_correct_type": sum(row["traffic"] in row["predicted_types"] for row in attack),
        "attack_typed_but_wrong": sum(bool(row["predicted_types"]) and row["traffic"] not in row["predicted_types"]
                                      for row in attack),
        "attack_target_raw_delivered": sum(row["reference_raw_delivered"] for row in attack),
        "attack_member_requests": sum(row["member"] == 1 for row in attack),
        "attack_yes_no": Counter(row["yes_no_unknown"] for row in attack if row["yes_no_unknown"] is not None),
        "normal_intervention": sum(row["action"] not in {"allow", "unavailable"} for row in normal),
        "normal_unavailable": sum(row["action"] == "unavailable" for row in normal),
        "normal_reference_raw_delivered": sum(row["reference_raw_delivered"] for row in normal),
        "masked_diagnostic_status": Counter(row["status"] for row in masked),
        "masked_known_matching_slots": sum(row["matched"] or 0 for row in masked),
        "masked_known_slots": sum(row["total"] for row in masked if row["matched"] is not None),
        "masked_all_slots": sum(row["total"] for row in masked),
        "latency_ms_p50": round(median(latency), 1) if latency else None,
        "latency_ms_p95_nearest_rank": round(latency[math.ceil(len(latency) * .95) - 1], 1) if latency else None,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("run", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    run = args.run
    manifest, metrics, spec = (read(run / name) for name in ("run_manifest.json", "metrics.json", "experiment_spec.json"))
    assert manifest["status"] == "completed" and metrics["analysis_role"] == "engineering_only"
    assert digest(run / "metrics.json") == manifest["metrics_sha256"]
    for name, path in spec["identity_files"].items():
        assert digest(Path(path)) == manifest["files_sha256"]["identity:" + name], name
    for name in ("requests", "labels"):
        assert digest(Path(spec[name + "_path"])) == manifest["files_sha256"][name], name
    labels = {row["request_id"]: row for row in rows(run / "labels.jsonl")}
    requests = {row["request_id"]: row for row in rows(run / "requests.jsonl")}
    assert labels.keys() == requests.keys()
    assert all(set(row) == {"request_id", "session_id", "query", "allowed_doc_ids"} for row in requests.values())
    lineage = {row["request_id"]: row for row in rows(Path(spec["identity_files"]["lineage"]))}
    entries = rows(run / "events.jsonl")
    assert Counter(row["status"] for row in entries) == Counter({
        "complete": metrics["completed"], "failed": metrics["failed"], "skipped": metrics["skipped"],
    })
    attack_scores = {
        (row["method"], rid): row["score"]
        for row in rows(run / "attack_scores.jsonl") for rid in row["request_ids"]
    }
    expected = {(method, rid) for method in manifest["methods"] for rid in requests}
    assert len(entries) == len(expected) == metrics["expected"]
    assert {(row["method"], row["request_id"]) for row in entries} == expected
    cases = []
    groups = defaultdict(list)
    for event in entries:
        rid = event["request_id"]
        label = labels[rid]
        risk = event.get("risk") or {}
        frozen = risk.get("frozen_risk", {})
        query = risk.get("query_detection", {})
        session = risk.get("session_detection", {})
        query_types = query.get("suspected_attack_types", [])
        session_types = session.get("suspected_attack_types", [])
        valid_types = (query_types if query.get("status") == "ok" else []) + (
            session_types if session.get("status") == "ok" else []
        )
        traces = {}
        ledger = event.get("ledger_event") or {}
        delivered = ledger.get("delivered_evidence", [])
        reference = event.get("generation_input_ref")
        if reference:
            path = (run / reference).resolve()
            assert path.is_relative_to(run.resolve())
            assert digest(path) == event["artifact_sha256"]
            artifact = read(path)
            generation = artifact["generation_input"]
            assert generation["query"] == requests[rid]["query"]
            assert len(generation["contexts"]) == len(delivered)
            assert [row["doc_id"] for row in delivered] == event["delivered_doc_ids"]
            for item, context in zip(delivered, generation["contexts"]):
                assert sha256(context.encode()).hexdigest() == item["text_sha256"]
            if event["action"] in {"deny", "unavailable"}:
                assert generation["prompt"] is None and not ledger["delivery_attempted"] and not delivered
            for entry in artifact["judge_traces"]:
                stage = entry["risk"]["stage"]
                traces[stage] = entry["risk"]["status"]
                expected_types = query_types if stage == "query" else session_types
                assert entry["risk"]["suspected_attack_types"] == expected_types
        if event["status"] == "complete":
            assert reference and ledger.get("response") == event["response"]
        excluded = risk.get("execution", {}).get("excluded_parent_ids", [])
        assert not set(excluded) & {item["parent_doc_id"] for item in delivered}
        raw_parents = {item["parent_doc_id"] for item in delivered if item["kind"] == "raw"}
        is_masked = label["attack_type"] == "masked_mia"
        response = event.get("response") or ""
        action = event.get("action")
        masked = None
        if is_masked and event["status"] == "complete":
            masked = diagnose(response, label["answers"], action) if action != "unavailable" else {
                "status": "unavailable", "matched": None, "total": len(label["answers"]),
            }
        expected_evidence = label.get("gold_evidence_ids") or [label["doc_id"]]
        row = {
            "request_id": rid, "session_id": event["session_id"], "turn": lineage[rid]["turn"],
            "method": event["method"], "traffic": label["attack_type"], "member": label.get("membership_label"),
            "doc_id": label["doc_id"], "status": event["status"], "reason": event.get("reason"),
            "risk_source": frozen.get("risk_source"), "risk_status": frozen.get("status"),
            "risk_score": frozen.get("score"), "risk_triggered": frozen.get("triggered"),
            "query_types": query_types, "session_types": session_types,
            "predicted_types": sorted(set(valid_types)), "trace_statuses": traces,
            "action": action, "policy": risk.get("type_policy"), "excluded_parents": excluded,
            "reference_raw_delivered": set(expected_evidence) <= raw_parents,
            "reference_retrieved": label["doc_id"] in event.get("retrieved_doc_ids", []),
            "delivered_raw_parents": sorted(raw_parents), "latency_ms": event.get("latency_ms"),
            "response": response, "reference_answer": label.get("reference_answer"),
            "yes_no_unknown": extract_yes_no_unknown(response) if label["attack_type"] in {"ia", "direct_rag_mia"}
            and action not in {"deny", "unavailable"} else None,
            "offline_attack_score": attack_scores.get((event["method"], rid)),
            "masked": masked, "generation_input_ref": reference,
        }
        cases.append(row)
        groups[row["method"]].append(row)
    out = {
        "run_id": manifest["run_id"], "analysis_role": metrics["analysis_role"],
        "cohort_manifest": spec["identity_files"]["cohort_manifest"],
        "formal_effect_eligible": False, "membership_inference_metrics": None,
        "membership_inference_metrics_reason": "Convenience development cohort; no independent calibration or valid formal cohort.",
        "run_metrics": metrics,
        "input_sha256": {name: digest(run / name) for name in (
            "run_manifest.json", "metrics.json", "events.jsonl", "attack_scores.jsonl",
        )},
        "methods": {method: summarize(group) for method, group in groups.items()},
        "by_traffic": {
            method: {traffic: summarize([row for row in group if row["traffic"] == traffic])
                     for traffic in sorted({row["traffic"] for row in group})}
            for method, group in groups.items()
        },
        "cases": cases,
    }
    with args.output.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(out["methods"], ensure_ascii=False))


if __name__ == "__main__":
    main()
