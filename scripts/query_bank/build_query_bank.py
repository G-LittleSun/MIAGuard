from __future__ import annotations

import argparse
import json
from pathlib import Path

from miaguard.query_bank.builder import build_query_bank
from miaguard.query_bank.schema import load_query_bank_config


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build or resume a versioned offline MIAGuard Query Bank"
    )
    parser.add_argument("--config", required=True)
    parser.add_argument("--bank-id", required=True)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--project-root", default=".")
    parser.add_argument(
        "--force-unlock",
        action="store_true",
        help="Remove a verified stale build lock before starting",
    )
    args = parser.parse_args()
    result = build_query_bank(
        Path(args.project_root),
        args.bank_id,
        args.dataset,
        load_query_bank_config(args.config),
        force_unlock=args.force_unlock,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
