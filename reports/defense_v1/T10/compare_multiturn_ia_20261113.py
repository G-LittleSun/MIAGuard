"""Compare bounded real session and reset-history defense runs without MIA claims."""

import argparse
from collections import Counter, defaultdict
from hashlib import sha256
import json
from pathlib import Path


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def rows(path):
    return [json.loads(s) for s in path.read_text(encoding="utf-8").splitlines() if s.strip()]


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def public_category(case):
    if case["status"] != "complete":
        return case["status"]
    if case["action"] in {"deny", "unavailable"}:
        return case["action"]
    if case["traffic"] == "benign":
        return "answer_ungraded"
    return case["yes_no_unknown"] or "unparsed"


def summarize(group):
    return {
        "requests": len(group), "completed": sum(r["status"] == "complete" for r in group),
        "actions": dict(Counter(r["action"] for r in group)),
        "risk_sources": dict(Counter(r["risk_source"] or "disabled" for r in group)),
        "risk_triggered": sum(r["risk_triggered"] is True for r in group),
        "ia_in_predicted_types": sum("ia" in r["predicted_types"] for r in group),
        "reference_retrieved": sum(r["reference_retrieved"] for r in group),
        "reference_raw_delivered": sum(r["reference_raw_delivered"] for r in group),
        "public_response": dict(Counter(public_category(r) for r in group)),
        "policy_reasons": dict(Counter((r["policy"] or {}).get("reason", "not_type_policy") for r in group)),
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("session_audit", type=Path)
    p.add_argument("reset_audit", type=Path)
    p.add_argument("output", type=Path)
    args = p.parse_args()
    audits = [read(args.session_audit), read(args.reset_audit)]
    runs = [Path("data/defense_v1_runs") / a["run_id"] for a in audits]
    for audit, run in zip(audits, runs):
        for name, expected in audit["input_sha256"].items():
            assert digest(run / name) == expected, name
        assert audit["run_metrics"]["failed"] == audit["run_metrics"]["skipped"] == 0
    request_sets = [{r["request_id"]: r for r in rows(run / "requests.jsonl")} for run in runs]
    for audit, run, requests in zip(audits, runs, request_sets):
        manifest = read(run / "run_manifest.json")
        expected = {(method, rid) for method in manifest["methods"] for rid in requests}
        actual = [(c["method"], c["request_id"]) for c in audit["cases"]]
        assert len(actual) == len(set(actual)) == len(expected) == audit["run_metrics"]["expected"]
        assert set(actual) == expected
        assert all(c["status"] == "complete" for c in audit["cases"])
    assert request_sets[0].keys() == request_sets[1].keys()
    assert all(request_sets[0][rid]["query"] == request_sets[1][rid]["query"] for rid in request_sets[0])
    assert rows(runs[0] / "labels.jsonl") == rows(runs[1] / "labels.jsonl")
    main_cases = audits[0]["cases"]
    reset_cases = {c["request_id"]: c for c in audits[1]["cases"]}
    assert all(c["method"] == "B_TYPE_V2" and c["risk_source"] == "query_only" for c in reset_cases.values())
    by_session = defaultdict(list)
    for c in main_cases:
        by_session[c["method"], c["session_id"]].append(c)
    sessions = []
    for (method, sid), group in sorted(by_session.items()):
        group.sort(key=lambda c: c["turn"])
        assert [c["turn"] for c in group] == [1, 2, 3]
        prior_raw_requests = 0
        for c in group:
            if c["policy"]:
                assert c["policy"]["prior_raw_delivery_requests"] == prior_raw_requests
            prior_raw_requests += bool(c["delivered_raw_parents"])
        sessions.append({"method": method, "session_id": sid, "traffic": group[0]["traffic"],
                         "doc_id": group[0]["doc_id"], "member": group[0]["member"],
                         "ever_reference_delivered": any(c["reference_raw_delivered"] for c in group),
                         "reference_delivered_before_turn3": any(c["reference_raw_delivered"] for c in group[:2]),
                         "ever_deny": any(c["action"] == "deny" for c in group),
                         "actions": [c["action"] for c in group],
                         "public_responses": [public_category(c) for c in group],
                         "third_turn_session_status": group[2]["trace_statuses"].get("session"),
                         "third_turn_risk_source": group[2]["risk_source"]})
    pairs = []
    for c in main_cases:
        if c["method"] != "B_TYPE_V2":
            continue
        reset = reset_cases[c["request_id"]]
        pairs.append({"request_id": c["request_id"], "doc_id": c["doc_id"], "traffic": c["traffic"],
                      "original_turn": c["turn"], "member": c["member"],
                      "action_changed": c["action"] != reset["action"],
                      "response_changed": c["response"] != reset["response"],
                      "session": c, "reset": reset})
    stratified = {}
    for name, cases in [("session", main_cases), ("reset", list(reset_cases.values()))]:
        methods = sorted({c["method"] for c in cases})
        stratified[name] = {method: {label: summarize([c for c in cases if c["method"] == method and
                        (c["traffic"] == "benign" if member is None else c["traffic"] == "ia" and c["member"] == member)])
                        for label, member in [("ia_member", 1), ("ia_nonmember", 0), ("normal", None)]}
                        for method in methods}
    out = {"analysis_role": "engineering_only", "formal_effect_eligible": False, "human_reviewed": False,
           "run_ids": [a["run_id"] for a in audits], "input_sha256": {str(path): digest(path) for path in [args.session_audit, args.reset_audit]},
           "same_queries_and_labels_verified": True, "prior_raw_ledger_counts_verified": True,
           "membership_auroc": None, "membership_auroc_reason": "Two known development source IDs per class, no independent calibration or final cohort.",
           "stratified": stratified, "sessions": sessions, "pairs": pairs,
           "changed_actions": [p["request_id"] for p in pairs if p["action_changed"]],
           "limits": ["Fixed nonadaptive IA requests; all ground truths yes; no human gold.",
                      "Reset removes both Session judging and prior exposure state. It is not a pure component ablation.",
                      "Answer prompts have no earlier responses. Judge history contains queries/retrieval metadata; responses are in the exposure ledger.",
                      "Suppression on a later turn does not retract earlier source delivery or responses.",
                      "Public response categories are observations, not calibrated attack success rates."]}
    with args.output.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(out, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"stratified": stratified, "changed_actions": out["changed_actions"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
