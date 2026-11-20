from __future__ import annotations

import argparse
import json
from pathlib import Path

from miaguard.config import load_attack_config
from miaguard.defense import load_defense_config
from miaguard.llm_judge import load_llm_judge_config
from miaguard.llm_judge_experiment import run_llm_judge_experiment


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--defense-config", required=True)
    parser.add_argument("--judge-config", required=True)
    parser.add_argument("--source-events", required=True)
    parser.add_argument("--output-run-id", required=True)
    parser.add_argument("--limit-per-attack", type=int, default=2)
    parser.add_argument("--benign-count", type=int, default=8)
    parser.add_argument("--project-root", default=".")
    args = parser.parse_args()

    root = Path(args.project_root).resolve()
    result = run_llm_judge_experiment(
        root,
        Path(args.source_events),
        args.output_run_id,
        load_attack_config(args.config),
        load_defense_config(args.defense_config),
        load_llm_judge_config(args.judge_config, root),
        limit_per_attack=args.limit_per_attack,
        benign_count=args.benign_count,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
