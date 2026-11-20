from collections import Counter, defaultdict
from hashlib import sha256
from pathlib import Path
import json

def read(path):
    return json.loads(path.read_text(encoding="utf-8"))

def rows(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]

def check(path, expected):
    assert sha256(path.read_bytes()).hexdigest() == expected, path

selection = Path("reports/defense_v1/T10/legacy_reuse_selection_20261104.json")
for item in read(selection)["input_files"].values():
    check(Path(item["path"]), item["sha256"])

runs = {
    "fast-v2-b0-b2-20261105-01": "B2",
    "rank-stress-v2-locator-20261111-01": "B5_LOCATED",
    "locator-new-sources-20261111-01": "B5_LOCATED",
    "cue-utility-nonmember-20261111-01": "B5_CUE",
    "e00-observe-20261022-01": None,
}
summary = {}
for name, method in runs.items():
    root = Path("data/defense_v1_runs") / name
    manifest = read(root / "run_manifest.json")
    if method is None:
        summary[name] = {"status": manifest["status"], "note": "Historical v1 E00, separate from v2 replay"}
        continue
    check(root / "metrics.json", manifest["metrics_sha256"])
    check(root / "labels.jsonl", manifest["files_sha256"]["labels"])
    spec = read(root / "experiment_spec.json")
    for key in ("frozen_model", "query_only_threshold", "vector_index", "source_train_manifest", "gateway_config", "judge_config"):
        check(Path(spec["identity_files"][key]), manifest["files_sha256"]["identity:" + key])
    labels = {row["request_id"]: row.get("attack_type") or "normal" for row in rows(root / "labels.jsonl")}
    by_truth = defaultdict(Counter)
    for event in rows(root / "events.jsonl"):
        if event["method"] != method:
            continue
        path = root / event["generation_input_ref"]
        check(path, event["artifact_sha256"])
        traces = read(path)["judge_traces"]
        trigger = event["risk"]["frozen_risk"]["triggered"]
        true_type = labels[event["request_id"]]
        counts = by_truth[true_type]
        counts["requests"] += 1
        counts["triggered"] += bool(trigger)
        for trace in traces:
            risk = trace["risk"]
            stage = risk["stage"]
            counts[stage + "_trace"] += 1
            counts[stage + "_ok"] += risk["status"] == "ok"
            predicted = risk["suspected_attack_types"]
            counts[stage + "_typed"] += bool(predicted)
            counts[stage + "_correct_type"] += true_type in predicted
            counts[stage + "_evidence"] += bool(risk["evidence_codes"])
            counts[stage + "_multi_type"] += len(predicted) > 1
            if predicted:
                counts[stage + "_pred:" + ",".join(sorted(predicted))] += 1
    summary[name] = {"status": manifest["status"], "method": method, "by_truth": by_truth}

output = Path("reports/defense_v1/T10/type_policy_trace_audit_20261113.json")
output.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
print(json.dumps(summary))
