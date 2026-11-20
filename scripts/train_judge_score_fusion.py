from __future__ import annotations

import argparse
import json
from pathlib import Path

from miaguard.query_bank.judge_score_workflow import run_train_score_fusion


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Train document-grouped OOF Judge-score fusion models from a reviewed "
            "train-only Stage A artifact directory"
        )
    )
    parser.add_argument("--analysis-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument(
        "--stage-a-reviewed",
        action="store_true",
        help="Required acknowledgement that the Stage A score-distribution review is complete",
    )
    parser.add_argument("--cv-splits", type=int, default=5)
    parser.add_argument("--cv-seed", type=int, default=20260903)
    parser.add_argument("--bootstrap-replicates", type=int, default=1000)
    parser.add_argument("--bootstrap-seed", type=int, default=20260903)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = run_train_score_fusion(
        Path(args.analysis_dir),
        Path(args.output_dir),
        stage_a_reviewed=args.stage_a_reviewed,
        cv_splits=args.cv_splits,
        cv_seed=args.cv_seed,
        bootstrap_replicates=args.bootstrap_replicates,
        bootstrap_seed=args.bootstrap_seed,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
