from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from .config import load_config
from .dataset_catalog import load_catalog, resolve_dataset_ids
from .dataset_import import import_teacher_snapshots
from .dataset_normalize import normalize_dataset
from .dataset_validation import validate_and_record
from .experiment import load_experiment_config, prepare_run
from .inspect_data import inspect_dataset
from .preprocess import preprocess_dataset
from .split_membership import split_dataset
from .validate import validate_outputs


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="rag_mia_data")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("inspect", "preprocess", "split", "validate"):
        child = subparsers.add_parser(command)
        child.add_argument("--config", required=True)

    dataset_import = subparsers.add_parser("dataset-import")
    dataset_import.add_argument("--source-root", required=True)

    for command in ("dataset-normalize", "dataset-validate"):
        child = subparsers.add_parser(command)
        child.add_argument(
            "--mode", choices=("single", "selected", "all"), default="all"
        )
        child.add_argument("--include", action="append")

    prepare = subparsers.add_parser("prepare-run")
    prepare.add_argument("--config", required=True)
    prepare.add_argument("--run-id", required=True)
    prepare.add_argument("--mode", choices=("single", "selected", "all"))
    prepare.add_argument("--include", action="append")
    return parser


def _run(command: str, config_path: str) -> dict[str, Any]:
    config = load_config(config_path)
    if command == "inspect":
        return inspect_dataset(config)
    if command == "preprocess":
        return preprocess_dataset(config)
    if command == "split":
        return split_dataset(config)
    if command == "validate":
        return validate_outputs(config)
    raise ValueError(f"Unknown command: {command}")


def _run_dataset_command(args: argparse.Namespace, project_root: Path) -> dict[str, Any]:
    catalog = load_catalog(project_root)
    if args.command == "dataset-import":
        return import_teacher_snapshots(
            catalog,
            project_root,
            Path(args.source_root).resolve(),
            list(catalog),
        )
    if args.command in {"dataset-normalize", "dataset-validate"}:
        dataset_ids = resolve_dataset_ids(catalog, args.mode, args.include)
        operation = (
            normalize_dataset
            if args.command == "dataset-normalize"
            else validate_and_record
        )
        return {
            dataset_id: operation(catalog[dataset_id], project_root)
            for dataset_id in dataset_ids
        }
    if args.command == "prepare-run":
        config = load_experiment_config(
            project_root,
            args.config,
            mode_override=args.mode,
            include_override=args.include,
        )
        return prepare_run(project_root, catalog, config, args.run_id)
    raise ValueError(f"Unknown command: {args.command}")


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command in {"inspect", "preprocess", "split", "validate"}:
            result = _run(args.command, args.config)
        else:
            result = _run_dataset_command(args, Path.cwd().resolve())
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
