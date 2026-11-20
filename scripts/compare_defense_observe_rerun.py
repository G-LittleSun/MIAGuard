"""Describe live Judge score drift against verified old train traces."""

from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter
from pathlib import Path

from miaguard.query_bank.judge_benchmark import load_verified_judge_records


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--old-train", type=Path, required=True)
    parser.add_argument("--observe-run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    manifest = json.loads((args.observe_run / "run_manifest.json").read_text(encoding="utf-8"))
    if manifest.get("status") != "complete" or manifest.get("partition") != "train":
        raise ValueError("A completed formal-train observe run is required")
    old, identity = load_verified_judge_records(args.old_train)
    by_id = {(row["query_id"], row["session_key"], row["turn_index"]): row for row in old}
    live = [json.loads(line) for line in (args.observe_run / "decisions.jsonl").read_text(encoding="utf-8").splitlines()]
    differences = {"query": [], "session": []}
    transitions = Counter()
    for row in live:
        source = by_id[(row["request_id"], row["session_id"], row["turn_index"])]
        risk = row["decision"]["two_stage_assessment"]["frozen_risk"]
        differences["query"].append(abs(risk["x1"] - source["query_trace"]["logprob"]["score"]))
        if risk["x2"] is not None:
            differences["session"].append(abs(risk["x2"] - source["session_trace"]["logprob"]["score"]))
        for stage in ("query", "session"):
            old_status = source[f"{stage}_trace"]["statuses"]["overall"]
            live_status = row["decision"]["two_stage_assessment"][f"{stage}_detection"]["status"]
            transitions[f"{stage}:{old_status}->{live_status}"] += 1
    output = {
        "schema_version": 1,
        "run_id": manifest["run_id"],
        "old_train_records_sha256": identity["judge_records_sha256"],
        "matched_request_count": len(live),
        "live_rerun_score_difference": {
            stage: {"count": len(values), "mean_absolute": statistics.mean(values) if values else None,
                    "max_absolute": max(values) if values else None}
            for stage, values in differences.items()
        },
        "status_transitions": dict(transitions),
        "interpretation": "The old and live Judge calls are separate stochastic executions; differences are descriptive and do not change the frozen threshold or determine G0 parity. Exact online/offline recomputation from the same saved trace is in comparison.json.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
