from __future__ import annotations

import argparse
import json
from pathlib import Path

from miaguard.query_bank.threshold_workflow import (
    export_enforce_config,
    validate_locked_threshold,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate a locked train threshold")
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--selection", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--max-benign-fpr", type=float, default=0.10)
    parser.add_argument("--base-config")
    parser.add_argument("--export-config")
    args = parser.parse_args(argv)
    if bool(args.base_config) != bool(args.export_config):
        parser.error("--base-config and --export-config must be supplied together")
    run_dir = Path(args.run_dir)
    output = Path(args.output)
    result = validate_locked_threshold(
        run_dir / "risk_records.jsonl",
        run_dir / "run_manifest.json",
        Path(args.selection),
        output,
        max_validation_benign_fpr=args.max_benign_fpr,
    )
    if args.base_config:
        export_enforce_config(Path(args.base_config), output, Path(args.export_config))
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
