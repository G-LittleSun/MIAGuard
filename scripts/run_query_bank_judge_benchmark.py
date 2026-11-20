from __future__ import annotations

import argparse
import json
from pathlib import Path

from miaguard.config import load_attack_config
from miaguard.progressive_judge import load_progressive_judge_config
from miaguard.query_bank.judge_benchmark import run_partition_judge_benchmark


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run Progressive Judge v2 on one frozen non-test Query Bank partition"
    )
    parser.add_argument("--attack-config", required=True)
    parser.add_argument("--judge-config", required=True)
    parser.add_argument("--source-run-id", required=True)
    parser.add_argument("--query-bank-id", required=True)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--split", required=True)
    parser.add_argument("--partition", choices=("train", "validation"), required=True)
    parser.add_argument("--output-root", required=True)
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument(
        "--max-sessions",
        type=_positive_int,
        help="Deterministically run only the first N planned sessions for a smoke test",
    )
    selection.add_argument(
        "--session-key",
        dest="session_keys",
        action="append",
        default=[],
        help="Run one exact planned session; repeat to select multiple sessions",
    )
    parser.add_argument("--project-root", default=".")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(args.project_root).resolve()
    judge_config = load_progressive_judge_config(args.judge_config, root)
    judge_config.validate_partition(args.partition)
    result = run_partition_judge_benchmark(
        project_root=root,
        source_run_id=args.source_run_id,
        query_bank_id=args.query_bank_id,
        dataset_id=args.dataset,
        split_path=Path(args.split).resolve(),
        partition=args.partition,
        output_root=Path(args.output_root).resolve(),
        attack_config=load_attack_config(args.attack_config),
        judge_config=judge_config,
        max_sessions=args.max_sessions,
        session_keys=tuple(args.session_keys),
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
