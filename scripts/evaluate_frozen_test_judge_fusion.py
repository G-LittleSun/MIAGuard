from __future__ import annotations

import argparse
import json
from pathlib import Path

from miaguard.judge_score_dataset import build_score_table
from miaguard.judge_score_frozen import evaluate_frozen_fusion
from miaguard.query_bank.judge_benchmark import load_verified_judge_records
from rag_mia_data.io_utils import write_json_atomic


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate test scores with a locked fusion artifact")
    parser.add_argument("--frozen-artifact", required=True)
    parser.add_argument("--test-run-dir", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    frozen = json.loads(Path(args.frozen_artifact).read_text(encoding="utf-8"))
    records, _ = load_verified_judge_records(Path(args.test_run_dir))
    table, _ = build_score_table(records)
    result = evaluate_frozen_fusion(table, frozen, partition="test")
    write_json_atomic(Path(args.output), result)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
