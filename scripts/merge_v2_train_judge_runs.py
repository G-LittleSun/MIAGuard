from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path

from miaguard.query_bank.judge_benchmark import (
    canonical_identity_sha256,
    load_verified_judge_records,
)
from miaguard.query_bank.judge_merge import (
    merge_partition_records,
    scoring_identity_core,
)
from miaguard.query_bank.sessions import plan_partition_sessions
from miaguard.query_bank.storage import QueryBank, QueryBankPaths
from miaguard.query_bank.threshold_split import load_threshold_split
from rag_mia_data.io_utils import sha256_file, write_json_atomic, write_jsonl_atomic


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Merge disjoint verified v2 train Judge runs into one full frozen partition"
    )
    parser.add_argument("--query-bank-id", required=True)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--split", required=True)
    parser.add_argument("--run-dir", action="append", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--project-root", default=".")
    return parser


def _load_manifest(run_dir: Path) -> dict[str, object]:
    value = json.loads((run_dir / "run_manifest.json").read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("Judge run manifest must be a mapping")
    return value


def _full_identity(identity: dict[str, object]) -> dict[str, object]:
    full = deepcopy(identity)
    full["session_planning"] = {
        "version": "all_accepted_balanced_sessions_v1",
        "target_turns": 5,
        "minimum_turns": 3,
        "max_sessions": None,
        "selection_mode": "all",
        "selected_session_keys": [],
    }
    return full


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(args.project_root).resolve()
    output_root = Path(args.output_root).resolve()
    output_dir = output_root / "train"
    if output_root.exists():
        raise FileExistsError(f"Merged output root already exists: {output_root}")

    run_dirs = [Path(value).resolve() for value in args.run_dir]
    verified = [load_verified_judge_records(run_dir) for run_dir in run_dirs]
    manifests = [_load_manifest(run_dir) for run_dir in run_dirs]
    identities = [manifest["identity"] for manifest in manifests]
    if any(not isinstance(identity, dict) for identity in identities):
        raise ValueError("Judge run manifest has an invalid identity")
    identities = [dict(identity) for identity in identities]
    expected_bank = {"bank_id": args.query_bank_id, "dataset_id": args.dataset}
    for identity in identities:
        if identity.get("partition") != "train":
            raise ValueError("Only train Judge runs can be merged")
        bank_identity = identity.get("query_bank")
        if not isinstance(bank_identity, dict) or any(
            bank_identity.get(key) != value for key, value in expected_bank.items()
        ):
            raise ValueError("Judge run belongs to a different Query Bank")
    first_core = scoring_identity_core(identities[0])
    if any(scoring_identity_core(identity) != first_core for identity in identities[1:]):
        raise ValueError("Judge runs differ outside session-selection metadata")

    bank = QueryBank.load(QueryBankPaths(root, args.query_bank_id, args.dataset))
    split_path = Path(args.split).resolve()
    split = load_threshold_split(split_path, bank)
    sessions = plan_partition_sessions(bank, split, "train", target_turns=5)
    records = merge_partition_records(sessions, tuple(rows for rows, _source in verified))
    identity = _full_identity(identities[0])
    identity_sha256 = canonical_identity_sha256(identity)
    for row in records:
        row["scoring_identity_sha256"] = identity_sha256

    records_path = output_dir / "judge_records.jsonl"
    write_jsonl_atomic(records_path, records)
    source_runs = [
        {
            "run_dir": str(run_dir),
            "scoring_identity_sha256": source["scoring_identity_sha256"],
            "judge_records_sha256": source["judge_records_sha256"],
        }
        for run_dir, (_rows, source) in zip(run_dirs, verified, strict=True)
    ]
    write_json_atomic(
        output_dir / "benchmark_summary.json",
        {
            "schema_version": 1,
            "partition": "train",
            "session_count": len(sessions),
            "query_count": len(records),
            "completed_session_count": len(sessions),
            "skipped_session_count": 0,
            "invalid_session_count": 0,
            "judge_records_sha256": sha256_file(records_path),
            "scoring_identity_sha256": identity_sha256,
            "merge_sources": source_runs,
        },
    )
    write_json_atomic(
        output_dir / "run_manifest.json",
        {
            "schema_version": 1,
            "identity": identity,
            "identity_sha256": identity_sha256,
            "merge_sources": source_runs,
        },
    )
    print(
        json.dumps(
            {
                "partition": "train",
                "session_count": len(sessions),
                "query_count": len(records),
                "output_dir": str(output_dir),
                "scoring_identity_sha256": identity_sha256,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
