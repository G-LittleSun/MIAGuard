from __future__ import annotations

import argparse
import json
import sys
import time
import traceback
from pathlib import Path

from miaguard.query_bank.repair import repair_ia_query_bank


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Append verified IA queries until every document has 10 yes and 10 no labels"
    )
    parser.add_argument("--bank-id", required=True)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--attack-config", required=True)
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--seed", type=int, default=20260813)
    parser.add_argument(
        "--retry-on-failure",
        action="store_true",
        help="retry indefinitely from the saved checkpoint after a failure",
    )
    parser.add_argument("--retry-delay-seconds", type=float, default=30.0)
    args = parser.parse_args(argv)
    if args.retry_delay_seconds < 0:
        parser.error("--retry-delay-seconds must be non-negative")
    attempt = 0
    while True:
        attempt += 1
        try:
            result = repair_ia_query_bank(
                Path(args.project_root),
                args.bank_id,
                args.dataset,
                Path(args.attack_config),
                seed=args.seed,
            )
            break
        except Exception as error:
            if not args.retry_on_failure:
                raise
            traceback.print_exc()
            print(
                "[query-bank][repair] "
                f"attempt={attempt} failed={type(error).__name__}: {error}; "
                f"retrying_in={args.retry_delay_seconds:g}s",
                file=sys.stderr,
                flush=True,
            )
            time.sleep(args.retry_delay_seconds)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
