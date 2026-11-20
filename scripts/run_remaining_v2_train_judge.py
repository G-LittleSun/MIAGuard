from __future__ import annotations

import argparse
import json
from pathlib import Path

from miaguard.config import load_attack_config
from miaguard.progressive_judge import load_progressive_judge_config
from miaguard.query_bank.incremental_benign_judge import select_unscored_sessions
from miaguard.query_bank.judge_benchmark import (
    load_verified_judge_records,
    run_partition_judge_benchmark,
)
from miaguard.query_bank.sessions import plan_partition_sessions
from miaguard.query_bank.storage import QueryBank, QueryBankPaths
from miaguard.query_bank.threshold_split import load_threshold_split


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Score all v2 train sessions absent from a verified partial Judge run"
    )
    parser.add_argument("--attack-config", required=True)
    parser.add_argument("--judge-config", required=True)
    parser.add_argument("--source-run-id", required=True)
    parser.add_argument("--query-bank-id", required=True)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--split", required=True)
    parser.add_argument("--partial-run-dir", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--project-root", default=".")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(args.project_root).resolve()
    partial_dir = Path(args.partial_run_dir).resolve()
    partial_records, _source = load_verified_judge_records(partial_dir)
    partial_manifest = json.loads(
        (partial_dir / "run_manifest.json").read_text(encoding="utf-8")
    )
    partial_identity = partial_manifest["identity"]
    expected_bank = {"bank_id": args.query_bank_id, "dataset_id": args.dataset}
    observed_bank = partial_identity.get("query_bank", {})
    if any(observed_bank.get(key) != value for key, value in expected_bank.items()):
        raise ValueError("Partial Judge run belongs to a different Query Bank")
    if partial_identity.get("partition") != "train":
        raise ValueError("Partial Judge run must belong to train")

    bank = QueryBank.load(QueryBankPaths(root, args.query_bank_id, args.dataset))
    split_path = Path(args.split).resolve()
    split = load_threshold_split(split_path, bank)
    sessions = plan_partition_sessions(bank, split, "train", target_turns=5)
    planned_keys = {session.session_key for session in sessions}
    completed_keys = {str(row["session_key"]) for row in partial_records}
    if not completed_keys.issubset(planned_keys):
        raise ValueError("Partial Judge run contains a session absent from the v2 plan")
    selected = select_unscored_sessions(
        sessions, completed_session_keys=completed_keys
    )
    if not selected:
        raise ValueError("Partial Judge run already covers every planned v2 train session")
    print(
        json.dumps(
            {
                "selection": "v2_train_sessions_absent_from_verified_partial_run",
                "completed_session_count": len(completed_keys),
                "remaining_session_count": len(selected),
                "remaining_query_count": sum(
                    len(session.queries) for session in selected
                ),
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
