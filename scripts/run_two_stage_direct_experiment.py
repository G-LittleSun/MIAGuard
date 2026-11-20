from __future__ import annotations

import argparse
import json
from pathlib import Path

from miaguard.config import load_attack_config
from miaguard.direct_scorer import load_direct_scorer_config
from miaguard.two_stage_direct_experiment import run_two_stage_direct_experiment
from miaguard.two_stage_gateway import load_two_stage_config


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--gateway-config", required=True)
    parser.add_argument("--split", required=True)
    parser.add_argument("--partition", default="development")
    parser.add_argument("--source-run-id", required=True)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--output-run-id", required=True)
    parser.add_argument("--samples-per-type", type=int, default=1)
    parser.add_argument("--ia-turn-count", type=int, default=3)
    parser.add_argument("--project-root", default=".")
    args = parser.parse_args()

    root = Path(args.project_root).resolve()
    result = run_two_stage_direct_experiment(
        root,
        args.source_run_id,
        args.dataset,
        args.output_run_id,
        load_attack_config(args.config),
        load_two_stage_config(args.gateway_config),
        load_direct_scorer_config(args.gateway_config, root),
        split_path=Path(args.split),
        partition=args.partition,
        samples_per_type=args.samples_per_type,
        ia_turn_count=args.ia_turn_count,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
