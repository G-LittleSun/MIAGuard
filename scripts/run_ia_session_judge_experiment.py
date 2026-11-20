from __future__ import annotations

import argparse
import json
from pathlib import Path

from miaguard.config import load_attack_config
from miaguard.defense import load_defense_config
from miaguard.ia_session_judge_experiment import run_ia_session_judge_experiment
from miaguard.llm_judge import load_llm_judge_config


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--defense-config", required=True)
    parser.add_argument("--judge-config", required=True)
    parser.add_argument("--source-run-id", required=True)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--output-run-id", required=True)
    parser.add_argument("--sessions-per-class", type=int, default=2)
    parser.add_argument("--turn-count", type=int, default=4)
    parser.add_argument("--document-offset", type=int, default=210)
    parser.add_argument("--project-root", default=".")
    args = parser.parse_args()

    root = Path(args.project_root).resolve()
    result = run_ia_session_judge_experiment(
        root,
        args.source_run_id,
        args.dataset,
        args.output_run_id,
        load_attack_config(args.config),
        load_defense_config(args.defense_config),
        load_llm_judge_config(args.judge_config, root),
        sessions_per_class=args.sessions_per_class,
        turn_count=args.turn_count,
        document_offset=args.document_offset,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
