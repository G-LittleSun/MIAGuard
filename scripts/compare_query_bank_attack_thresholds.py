from __future__ import annotations

import argparse
import json
from pathlib import Path

from miaguard.query_bank.threshold_comparison import compare_test_conditions
from miaguard.two_stage_gateway import load_two_stage_config


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Compare disabled, fixed 0.10, and learned policies on test scores"
    )
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--validation", required=True)
    parser.add_argument("--gateway-config", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    run_dir = Path(args.run_dir)
    config = load_two_stage_config(args.gateway_config)
    result = compare_test_conditions(
        run_dir / "risk_records.jsonl",
        run_dir / "run_manifest.json",
        Path(args.validation),
        Path(args.output),
        level_thresholds=config.level_thresholds,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
