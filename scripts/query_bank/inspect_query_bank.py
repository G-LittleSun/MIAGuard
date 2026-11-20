from __future__ import annotations

import argparse
import json
from pathlib import Path

from miaguard.query_bank.validator import inspect_query_bank


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inspect statistics for a complete MIAGuard Query Bank"
    )
    parser.add_argument("--bank-id", required=True)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--project-root", default=".")
    args = parser.parse_args()
    result = inspect_query_bank(
        Path(args.project_root), args.bank_id, args.dataset
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
