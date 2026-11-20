from __future__ import annotations

import argparse
import json
from pathlib import Path

from miaguard.attack_pattern_library import AttackPatternLibrary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("list", "show", "validate"))
    parser.add_argument("pattern_id", nargs="?")
    parser.add_argument(
        "--manifest",
        default="attack_pattern_library/manifest.yaml",
    )
    args = parser.parse_args()

    library = AttackPatternLibrary.load(Path(args.manifest))
    if args.command == "list":
        print(json.dumps(library.index(), ensure_ascii=False, indent=2))
    elif args.command == "show":
        if not args.pattern_id:
            parser.error("show requires pattern_id")
        print(library.read_patterns([args.pattern_id])[args.pattern_id])
    else:
        print(
            json.dumps(
                {
                    "status": "valid",
                    "library": library.name,
                    "version": library.version,
                    "enabled_patterns": list(library.patterns),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
