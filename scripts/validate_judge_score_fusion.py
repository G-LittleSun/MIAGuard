from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from miaguard.judge_score_frozen import evaluate_frozen_fusion, freeze_logistic_l2
from miaguard.judge_score_dataset import build_score_table
from miaguard.query_bank.judge_benchmark import load_verified_judge_records
from rag_mia_data.io_utils import write_json_atomic


def main() -> int:
    parser = argparse.ArgumentParser(description="Freeze train logistic fusion and evaluate it on validation")
    parser.add_argument("--train-analysis-dir", required=True)
    parser.add_argument("--fusion-dir", required=True)
    parser.add_argument("--validation-run-dir", required=True)
    parser.add_argument("--frozen-output", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    train = pd.read_parquet(Path(args.train_analysis_dir) / "separability_dataset.parquet")
    selections = json.loads((Path(args.fusion_dir) / "threshold_selection.json").read_text(encoding="utf-8"))
    frozen = freeze_logistic_l2(train, selections["logprob"]["logistic_l2"], Path(args.frozen_output))
    records, _ = load_verified_judge_records(Path(args.validation_run_dir))
    validation, _ = build_score_table(records)
    result = {"frozen_model": frozen, "validation": evaluate_frozen_fusion(validation, frozen)}
    write_json_atomic(Path(args.output), result)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
