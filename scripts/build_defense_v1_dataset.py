"""Build the review-pending defense_access_v1 document split."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from miaguard.defense_dataset import build_defense_dataset


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, default=Path("data/defense_datasets/defense_access_v1"))
    args = parser.parse_args()
    root = args.project_root.resolve()
    output = args.output if args.output.is_absolute() else root / args.output
    print(json.dumps(build_defense_dataset(root, output), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
