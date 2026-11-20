"""Run or resume a session-sharded defense v1 benchmark."""

from __future__ import annotations

import argparse
import json

from miaguard.defense_benchmark import run_benchmark


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment-spec", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    print(json.dumps(run_benchmark(args.experiment_spec, args.output_root, resume=args.resume), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
