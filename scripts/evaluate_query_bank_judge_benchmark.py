from __future__ import annotations

import argparse
import json
from pathlib import Path

from miaguard.judge_evaluation import evaluate_judge_records
from miaguard.query_bank.judge_benchmark import load_verified_judge_records
from rag_mia_data.io_utils import write_json_atomic


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Evaluate Progressive Judge rubric and logprob heads without selecting an access threshold"
    )
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--bootstrap-seed", type=int, default=20260823)
    parser.add_argument("--bootstrap-replicates", type=int, default=1000)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    output = Path(args.output).resolve()
    if output.exists():
        raise FileExistsError(f"Judge evaluation report already exists: {output}")
    records, source = load_verified_judge_records(Path(args.run_dir).resolve())
    report = evaluate_judge_records(
        records,
        bootstrap_seed=args.bootstrap_seed,
        bootstrap_replicates=args.bootstrap_replicates,
    )
    report["source"] = source
    write_json_atomic(output, report)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
