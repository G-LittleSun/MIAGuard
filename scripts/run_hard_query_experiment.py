from __future__ import annotations

import argparse
import json
from pathlib import Path

from miaguard.config import load_attack_config
from miaguard.defense import load_defense_config
from miaguard.hard_query_experiment import run_hard_query_experiment


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--defense-config", required=True)
    parser.add_argument("--source-run-id", required=True)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--output-run-id", required=True)
    parser.add_argument("--limit-per-class", type=int, default=10)
    parser.add_argument("--attack-offset-per-class", type=int, default=190)
    parser.add_argument("--benign-count", type=int, default=40)
    parser.add_argument("--benign-offset-per-class", type=int, default=190)
    parser.add_argument("--project-root", default=".")
    args = parser.parse_args()

    root = Path(args.project_root).resolve()
    result = run_hard_query_experiment(
        root,
        args.source_run_id,
        args.dataset,
        args.output_run_id,
        load_attack_config(args.config),
        load_defense_config(args.defense_config),
        limit_per_class=args.limit_per_class,
        attack_offset_per_class=args.attack_offset_per_class,
        benign_count=args.benign_count,
        benign_offset_per_class=args.benign_offset_per_class,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
