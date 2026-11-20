from __future__ import annotations

import argparse
import json
from pathlib import Path

from miaguard.config import load_attack_config
from miaguard.direct_scorer import load_direct_scorer_config
from miaguard.two_stage_gateway import load_two_stage_config
from miaguard.two_stage_threshold_calibration import (
    run_two_stage_threshold_calibration,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Calibrate a balanced two-stage detection threshold"
    )
    parser.add_argument("--config", required=True)
    parser.add_argument("--gateway-config", required=True)
    parser.add_argument("--source-run-id", required=True)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--output-run-id", required=True)
    parser.add_argument("--limit-per-class", type=int, default=10)
    parser.add_argument("--benign-count", type=int, default=20)
    parser.add_argument("--offset-per-class", type=int, default=0)
    parser.add_argument("--max-benign-fpr", type=float, default=0.05)
    parser.add_argument("--project-root", default=".")
    args = parser.parse_args()

    root = Path(args.project_root).resolve()
    result = run_two_stage_threshold_calibration(
        root,
        args.source_run_id,
        args.dataset,
        args.output_run_id,
        load_attack_config(args.config),
        load_two_stage_config(args.gateway_config),
        load_direct_scorer_config(args.gateway_config, root),
        limit_per_class=args.limit_per_class,
        benign_count=args.benign_count,
        offset_per_class=args.offset_per_class,
        max_benign_fpr=args.max_benign_fpr,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
