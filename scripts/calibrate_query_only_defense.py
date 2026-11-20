"""Calibrate the startup Query-only defense on verified formal train scores."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from miaguard.judge_score_dataset import build_score_table
from miaguard.query_bank.judge_benchmark import load_verified_judge_records
from miaguard.query_only_calibration import calibrate_query_only


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train-run-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--bootstrap-replicates", type=int, default=1000)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f"Refusing to overwrite existing calibration: {args.output}")
    records, identity = load_verified_judge_records(args.train_run_dir)
    table, audit = build_score_table(records)
    if audit["partition"] != "train":
        raise ValueError("Only formal train data may calibrate Query-only thresholds")
    selected = table.loc[table["head"] == "logprob"].to_dict("records")
    result = calibrate_query_only(selected, bootstrap_replicates=args.bootstrap_replicates)
    result["source"] = {
        "run_dir": str(args.train_run_dir.resolve()),
        "scoring_identity_sha256": identity["scoring_identity_sha256"],
        "judge_records_sha256": identity["judge_records_sha256"],
        "score_table_audit": audit,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "working_points": result["working_points"], "sample_counts": result["sample_counts"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
