from __future__ import annotations

import argparse
import json
from pathlib import Path

from miaguard.query_bank.storage import QueryBank, QueryBankPaths
from miaguard.query_bank.threshold_split import (
    build_threshold_split,
    freeze_threshold_split,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Freeze a document-level split for supervised threshold experiments"
    )
    parser.add_argument("--bank-id", required=True)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--split-id", required=True)
    parser.add_argument("--seed", required=True, type=int)
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)

    project_root = Path(args.project_root).resolve()
    bank = QueryBank.load(QueryBankPaths(project_root, args.bank_id, args.dataset))
    split = build_threshold_split(
        bank,
        split_id=args.split_id,
        seed=args.seed,
    )
    output = Path(args.output)
    if not output.is_absolute():
        output = project_root / output
    freeze_threshold_split(split, output)
    print(json.dumps(split, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
