from __future__ import annotations

import argparse
import json
from pathlib import Path

from miaguard.config import load_attack_config
from miaguard.progressive_judge import load_progressive_judge_config
from miaguard.query_bank.judge_benchmark import run_partition_judge_benchmark


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a frozen-model test Judge benchmark")
    parser.add_argument("--frozen-artifact", required=True)
    parser.add_argument("--attack-config", required=True)
    parser.add_argument("--judge-config", required=True)
    parser.add_argument("--source-run-id", required=True)
    parser.add_argument("--query-bank-id", required=True)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--split", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--project-root", default=".")
    args = parser.parse_args()
    frozen = json.loads(Path(args.frozen_artifact).read_text(encoding="utf-8"))
    if frozen.get("model") != "logistic_l2" or set(frozen.get("thresholds", {})) != {"0.01", "0.05"}:
        raise ValueError("Frozen test benchmark requires the locked logistic_l2 artifact")
    root = Path(args.project_root).resolve()
    result = run_partition_judge_benchmark(
        project_root=root, source_run_id=args.source_run_id, query_bank_id=args.query_bank_id,
        dataset_id=args.dataset, split_path=Path(args.split).resolve(), partition="test",
        output_root=Path(args.output_root).resolve(), attack_config=load_attack_config(args.attack_config),
        judge_config=load_progressive_judge_config(args.judge_config, root), allow_frozen_test=True,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
