from __future__ import annotations

import argparse
import json
from pathlib import Path

from miaguard.config import load_attack_config
from miaguard.progressive_judge import load_progressive_judge_config
from miaguard.query_bank.incremental_benign_judge import (
    select_incremental_benign_sessions,
)
from miaguard.query_bank.judge_benchmark import run_partition_judge_benchmark
from miaguard.query_bank.sessions import plan_partition_sessions
from miaguard.query_bank.storage import QueryBank, QueryBankPaths
from miaguard.query_bank.threshold_split import load_threshold_split


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Score only v2 benign sessions that contain queries absent from v1"
    )
    parser.add_argument("--attack-config", required=True)
    parser.add_argument("--judge-config", required=True)
    parser.add_argument("--source-run-id", required=True)
    parser.add_argument("--prior-query-bank-id", required=True)
    parser.add_argument("--query-bank-id", required=True)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--split", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--project-root", default=".")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(args.project_root).resolve()
    bank = QueryBank.load(QueryBankPaths(root, args.query_bank_id, args.dataset))
    split_path = Path(args.split).resolve()
    split = load_threshold_split(split_path, bank)
    prior_bank = QueryBank.load(
        QueryBankPaths(root, args.prior_query_bank_id, args.dataset)
    )
    prior_query_ids = {str(row["query_id"]) for row in prior_bank.records}
    sessions = plan_partition_sessions(bank, split, "train", target_turns=5)
    selected = select_incremental_benign_sessions(
        sessions, prior_query_ids=prior_query_ids
    )
    selected_query_count = sum(len(session.queries) for session in selected)
    new_query_count = sum(
        str(query["query_id"]) not in prior_query_ids
        for session in selected
        for query in session.queries
    )
    print(
        json.dumps(
            {
                "selection": "v2_train_benign_sessions_containing_new_query",
                "session_count": len(selected),
                "scored_query_count": selected_query_count,
                "new_query_count": new_query_count,
                "context_required_retained_query_count": selected_query_count
                - new_query_count,
                "session_keys": [session.session_key for session in selected],
            },
            ensure_ascii=False,
            sort_keys=True,
        ),
        flush=True,
    )
    judge_config = load_progressive_judge_config(args.judge_config, root)
    result = run_partition_judge_benchmark(
        project_root=root,
        source_run_id=args.source_run_id,
        query_bank_id=args.query_bank_id,
        dataset_id=args.dataset,
        split_path=split_path,
        partition="train",
        output_root=Path(args.output_root).resolve(),
        attack_config=load_attack_config(args.attack_config),
        judge_config=judge_config,
        session_keys=tuple(session.session_key for session in selected),
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
