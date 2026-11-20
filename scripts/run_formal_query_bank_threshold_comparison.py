from __future__ import annotations

import argparse
import json
from pathlib import Path

from miaguard.config import load_attack_config
from miaguard.direct_scorer import load_direct_scorer_config
from miaguard.query_bank.formal_threshold_comparison import (
    run_formal_threshold_test_comparison,
)
from miaguard.two_stage_gateway import load_two_stage_config


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run formal disabled/fixed/learned replay on frozen test sessions"
    )
    parser.add_argument("--config", required=True)
    parser.add_argument("--gateway-config", required=True)
    parser.add_argument("--source-run-id", required=True)
    parser.add_argument("--query-bank-id", required=True)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--split", required=True)
    parser.add_argument("--validation", required=True)
    parser.add_argument("--output-run-id", required=True)
    parser.add_argument("--project-root", default=".")
    args = parser.parse_args(argv)
    root = Path(args.project_root).resolve()
    result = run_formal_threshold_test_comparison(
        root,
        args.source_run_id,
        args.query_bank_id,
        args.dataset,
        Path(args.split).resolve(),
        Path(args.validation).resolve(),
        args.output_run_id,
        load_attack_config(args.config),
        load_two_stage_config(args.gateway_config),
        load_direct_scorer_config(args.gateway_config, root),
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
