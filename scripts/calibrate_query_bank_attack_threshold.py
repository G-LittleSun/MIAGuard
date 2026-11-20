from __future__ import annotations

import argparse
import json
from pathlib import Path

from miaguard.query_bank.threshold_workflow import calibrate_train_partition


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Select one attack threshold on train scores")
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--max-benign-fpr", type=float, default=0.05)
    args = parser.parse_args(argv)
    run_dir = Path(args.run_dir)
    result = calibrate_train_partition(
        run_dir / "risk_records.jsonl",
        run_dir / "run_manifest.json",
        Path(args.output),
        max_benign_fpr=args.max_benign_fpr,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
