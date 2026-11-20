from __future__ import annotations

import argparse
import json
from pathlib import Path

from miaguard.query_bank.sessions import audit_full_session_plan
from miaguard.query_bank.storage import QueryBank, QueryBankPaths
from miaguard.query_bank.threshold_split import load_threshold_split
from rag_mia_data.io_utils import write_json_atomic


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Audit all frozen Query Bank threshold sessions without loading models"
    )
    parser.add_argument("--query-bank-id", required=True)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--split", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--project-root", default=".")
    args = parser.parse_args(argv)
    root = Path(args.project_root).resolve()
    bank = QueryBank.load(QueryBankPaths(root, args.query_bank_id, args.dataset))
    split = load_threshold_split(Path(args.split), bank)
    report = audit_full_session_plan(bank, split)
    output = Path(args.output)
    if not output.is_absolute():
        output = root / output
    write_json_atomic(output, report)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
