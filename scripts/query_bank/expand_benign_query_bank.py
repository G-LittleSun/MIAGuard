from __future__ import annotations

import argparse
import json
from pathlib import Path

from miaguard.query_bank.benign_expansion import (
    expand_benign_query_bank,
    load_benign_expansion_config,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Create a frozen v2 Query Bank by replacing only v1 benign queries"
    )
    parser.add_argument("--config", required=True)
    parser.add_argument("--bank-id", required=True)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--split-id", required=True)
    parser.add_argument("--split-output", required=True)
    args = parser.parse_args(argv)

    root = Path(args.project_root).resolve()
    result = expand_benign_query_bank(
        project_root=root,
        bank_id=args.bank_id,
        dataset_id=args.dataset,
        config=load_benign_expansion_config(root / args.config),
        split_id=args.split_id,
        split_output=Path(args.split_output),
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
