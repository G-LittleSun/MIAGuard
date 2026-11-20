from __future__ import annotations

import argparse
import json
from pathlib import Path

from miaguard.two_stage_splits import freeze_split


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--project-root", default=".")
    args = parser.parse_args()

    manifest = freeze_split(
        Path(args.project_root).resolve(),
        Path(args.spec).resolve(),
        Path(args.output).resolve(),
    )
    summary = {
        "status": "frozen",
        "split_id": manifest["split_id"],
        "output": str(Path(args.output).resolve()),
        "counts": {
            name: {
                "members": value["member_count"],
                "nonmembers": value["nonmember_count"],
            }
            for name, value in manifest["partitions"].items()
        },
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
