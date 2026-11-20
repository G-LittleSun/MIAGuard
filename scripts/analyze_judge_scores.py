from __future__ import annotations

import argparse
import json
from pathlib import Path

from miaguard.query_bank.judge_score_workflow import run_train_score_analysis


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Analyze rubric/logprob query and session score distributions on a "
            "verified Progressive Judge train run"
        )
    )
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--bootstrap-seed", type=int, default=20260829)
    parser.add_argument("--bootstrap-replicates", type=int, default=1000)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = run_train_score_analysis(
        Path(args.run_dir),
        Path(args.output_dir),
        bootstrap_seed=args.bootstrap_seed,
        bootstrap_replicates=args.bootstrap_replicates,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
