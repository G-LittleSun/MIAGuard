from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from .config import load_attack_config
from .defense import load_defense_config
from .defense_experiment import run_defense_experiment
from .direct_rag_mia import run_direct_rag_mia
from .ia_attack import run_ia
from .masked_mia import run_masked_mia
from .metrics import compute_metrics_file
from .model_client import create_model_client
from .s2_mia import run_s2_mia
from .vector_store import build_vector_store


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="miaguard")
    subparsers = parser.add_subparsers(dest="command", required=True)

    doctor = subparsers.add_parser("doctor")
    doctor.add_argument("--config", required=True)

    for command in ("build-index", "masked-mia", "ia", "direct-rag-mia", "s2-mia"):
        child = subparsers.add_parser(command)
        child.add_argument("--config", required=True)
        child.add_argument("--run-id", required=True)
        child.add_argument("--dataset", required=True)
        child.add_argument("--project-root", default=".")
        if command != "build-index":
            child.add_argument("--limit-per-class", type=int)

    metrics = subparsers.add_parser("metrics")
    metrics.add_argument("--results", required=True)
    metrics.add_argument("--output", required=True)
    metrics.add_argument("--threshold", type=float, default=0.5)

    defense = subparsers.add_parser("defense-mvp")
    defense.add_argument("--config", required=True)
    defense.add_argument("--defense-config", required=True)
    defense.add_argument("--source-run-id", required=True)
    defense.add_argument("--dataset", required=True)
    defense.add_argument("--output-run-id", required=True)
    defense.add_argument("--project-root", default=".")
    defense.add_argument("--limit-per-class", type=int, default=10)
    defense.add_argument("--benign-count", type=int, default=40)
    defense.add_argument("--offset-per-class", type=int, default=0)
    return parser


def doctor(config_path: str | Path) -> dict[str, Any]:
    config = load_attack_config(config_path)
    client = create_model_client(config, Path.cwd())
    client.validate_models()
    embedding = client.embed(config.embedding_model, ["MIAGuard vector check"])[0]
    generation = client.generate(
        config.generation_model,
        "Reply with OK only.",
        max_tokens=8,
        temperature=0.0,
    )
    result = {
        "generation_backend": config.generation_backend,
        "embedding_dimension": len(embedding),
        "embedding_model": config.embedding_model,
        "embedding_backend": config.embedding_backend,
        "generation_model": config.generation_model,
        "generation_response": generation,
        "status": "ok",
    }
    if "ollama" in {config.generation_backend, config.embedding_backend}:
        result["base_url"] = config.base_url
    return result


def _run(args: argparse.Namespace) -> dict[str, Any]:
    if args.command == "doctor":
        return doctor(args.config)
    if args.command == "metrics":
        return compute_metrics_file(
            Path(args.results).resolve(),
            Path(args.output).resolve(),
            args.threshold,
        )

    config = load_attack_config(args.config)
    root = Path(args.project_root).resolve()
    if args.command == "defense-mvp":
        return run_defense_experiment(
            root,
            args.source_run_id,
            args.dataset,
            args.output_run_id,
            config,
            load_defense_config(args.defense_config),
            limit_per_class=args.limit_per_class,
            benign_count=args.benign_count,
            offset_per_class=args.offset_per_class,
        )
    if args.command == "build-index":
        return build_vector_store(root, args.run_id, args.dataset, config)
    if args.command == "masked-mia":
        return run_masked_mia(
            root, args.run_id, args.dataset, config, args.limit_per_class
        )
    if args.command == "ia":
        return run_ia(root, args.run_id, args.dataset, config, args.limit_per_class)
    if args.command == "direct-rag-mia":
        return run_direct_rag_mia(
            root, args.run_id, args.dataset, config, args.limit_per_class
        )
    if args.command == "s2-mia":
        return run_s2_mia(
            root, args.run_id, args.dataset, config, args.limit_per_class
        )
    raise ValueError(f"Unknown command: {args.command}")


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = _run(args)
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
