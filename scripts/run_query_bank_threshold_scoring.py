from __future__ import annotations

import argparse
import json
from pathlib import Path

from miaguard.config import load_attack_config
from miaguard.direct_scorer import load_direct_scorer_config
from miaguard.query_bank.threshold_scoring import run_partition_threshold_scoring
from miaguard.two_stage_gateway import load_two_stage_config


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Score one frozen Query Bank partition in observe mode"
    )
    parser.add_argument("--config", required=True)
    parser.add_argument("--gateway-config", required=True)
    parser.add_argument("--source-run-id", required=True)
    parser.add_argument("--query-bank-id", required=True)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--split", required=True)
    parser.add_argument("--partition", choices=("train", "validation", "test"), required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--project-root", default=".")
    args = parser.parse_args(argv)
    root = Path(args.project_root).resolve()
    result = run_partition_threshold_scoring(
        root,
        args.source_run_id,
        args.query_bank_id,
        args.dataset,
        Path(args.split).resolve(),
        args.partition,
        Path(args.output_root).resolve(),
        load_attack_config(args.config),
        load_two_stage_config(args.gateway_config),
        load_direct_scorer_config(args.gateway_config, root),
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
