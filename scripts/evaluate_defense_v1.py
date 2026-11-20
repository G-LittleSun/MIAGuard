"""Evaluate a defense replay; current implementation is engineering-only."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from miaguard.defense_metrics import evaluate_run


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--analysis-role", choices=("engineering_only",), default="engineering_only")
    args = parser.parse_args()
    result = evaluate_run(args.run_dir, {"analysis_role": args.analysis_role})
    if args.output.exists():
        raise FileExistsError(args.output)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "run_id": result["run_id"],
                      "analysis_role": result["analysis_role"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
