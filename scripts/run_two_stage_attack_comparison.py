from __future__ import annotations

import argparse
import json
from pathlib import Path

from miaguard.config import load_attack_config
from miaguard.direct_scorer import load_direct_scorer_config
from miaguard.two_stage_attack_comparison import run_two_stage_attack_comparison
from miaguard.two_stage_gateway import load_two_stage_config


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare all RAG-MIA attacks with and without two-stage defense"
    )
    parser.add_argument("--config", required=True)
    parser.add_argument("--gateway-config", required=True)
    parser.add_argument("--source-run-id", required=True)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--output-run-id", required=True)
    parser.add_argument("--limit-per-class", type=int, default=1)
    parser.add_argument("--benign-count", type=int, default=4)
    parser.add_argument("--offset-per-class", type=int, default=0)
    parser.add_argument("--continuous-attack-sessions", action="store_true")
    parser.add_argument("--ia-turn-count", type=int, default=1)
    parser.add_argument(
        "--query-bank-id",
        help=(
            "Use a complete offline Query Bank. When set, the experiment never "
            "generates attack or benign queries online."
        ),
    )
    parser.add_argument("--query-seed", type=int, default=20260725)
    parser.add_argument(
        "--variant-mode",
        choices=("canonical", "paraphrase", "mixed"),
        default="canonical",
    )
    parser.add_argument("--project-root", default=".")
    args = parser.parse_args()

    root = Path(args.project_root).resolve()
    result = run_two_stage_attack_comparison(
        root,
        args.source_run_id,
        args.dataset,
        args.output_run_id,
        load_attack_config(args.config),
        load_two_stage_config(args.gateway_config),
        load_direct_scorer_config(args.gateway_config, root),
        limit_per_class=args.limit_per_class,
        benign_count=args.benign_count,
        offset_per_class=args.offset_per_class,
        continuous_attack_sessions=args.continuous_attack_sessions,
        ia_turn_count=args.ia_turn_count,
        query_bank_id=args.query_bank_id,
        query_seed=args.query_seed,
        variant_mode=args.variant_mode,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
