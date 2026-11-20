from __future__ import annotations

import argparse
import json
from pathlib import Path

from miaguard.config import load_attack_config
from miaguard.data import attack_result_path
from miaguard.defense_experiment import select_balanced_rows
from miaguard.threshold_calibration import calibrate_threshold
from rag_mia_data.io_utils import read_jsonl, utc_now_iso, write_json_atomic


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--source-run-id", required=True)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--calibration-per-class", type=int, default=100)
    parser.add_argument("--output", required=True)
    parser.add_argument("--project-root", default=".")
    args = parser.parse_args()

    root = Path(args.project_root).resolve()
    config = load_attack_config(args.config)
    configured_thresholds = {
        "s2_mia": config.s2_mia_threshold,
        "masked_mia": config.masked_threshold,
    }
    attacks = {}
    for attack, configured_threshold in configured_thresholds.items():
        results_path = (
            attack_result_path(root, args.source_run_id, args.dataset, attack)
            / "results.jsonl"
        )
        rows = select_balanced_rows(
            list(read_jsonl(results_path)),
            args.calibration_per_class,
        )
        calibrated = calibrate_threshold(
            [int(row["membership_label"]) for row in rows],
            [float(row["membership_score"]) for row in rows],
        )
        attacks[attack] = {
            "configured_threshold": configured_threshold,
            "calibrated_threshold": calibrated["threshold"],
            "selection_objective": calibrated["selection_objective"],
            "calibration_metrics": calibrated["metrics"],
            "calibration_member_doc_ids": [
                str(row["doc_id"])
                for row in rows
                if int(row["membership_label"]) == 1
            ],
            "calibration_nonmember_doc_ids": [
                str(row["doc_id"])
                for row in rows
                if int(row["membership_label"]) == 0
            ],
            "source_results": str(results_path.relative_to(root)).replace("\\", "/"),
        }
    report = {
        "created_at": utc_now_iso(),
        "source_run_id": args.source_run_id,
        "dataset_id": args.dataset,
        "calibration_per_class": args.calibration_per_class,
        "calibration_offset_per_class": 0,
        "evaluation_offset_per_class": args.calibration_per_class,
        "attacks": attacks,
    }
    output = Path(args.output)
    if not output.is_absolute():
        output = root / output
    write_json_atomic(output, report)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
