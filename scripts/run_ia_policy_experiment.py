from __future__ import annotations

import argparse
import json
from pathlib import Path

from miaguard.config import load_attack_config
from miaguard.defense import load_defense_config
from miaguard.ia_policy_experiment import run_ia_policy_experiment


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--source-run-id", required=True)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--output-run-id", required=True)
    parser.add_argument("--limit-per-class", type=int, default=20)
    parser.add_argument("--offset-per-class", type=int, default=110)
    parser.add_argument("--project-root", default=".")
    args = parser.parse_args()

    root = Path(args.project_root).resolve()
    policy_paths = {
        "restrict_context": root / "configs/defense/mvp.yaml",
        "summarize_context": root / "configs/defense/ia_summary.yaml",
        "no_context_answer": root / "configs/defense/ia_no_context.yaml",
        "deny_sensitive_answer": root / "configs/defense/ia_deny.yaml",
    }
    result = run_ia_policy_experiment(
        root,
        args.source_run_id,
        args.dataset,
        args.output_run_id,
        load_attack_config(args.config),
        {name: load_defense_config(path) for name, path in policy_paths.items()},
        limit_per_class=args.limit_per_class,
        offset_per_class=args.offset_per_class,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
