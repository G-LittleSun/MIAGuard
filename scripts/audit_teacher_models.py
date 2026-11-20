from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from safetensors import safe_open


def load_catalog(path: Path) -> dict[str, dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    models = raw.get("models") if isinstance(raw, dict) else None
    if not isinstance(models, dict):
        raise ValueError("Model catalog must contain a models mapping")
    return models


def audit_embedding(path: Path) -> dict[str, Any]:
    required = ["config.json", "modules.json", "model.safetensors"]
    missing = [name for name in required if not (path / name).is_file()]
    return {
        "status": "complete" if not missing else "incomplete",
        "missing": missing,
        "size_bytes": sum(item.stat().st_size for item in path.rglob("*") if item.is_file()),
    }


def audit_llm(path: Path) -> dict[str, Any]:
    index_path = path / "model.safetensors.index.json"
    if not index_path.is_file():
        single_weight = path / "model.safetensors"
        if not single_weight.is_file():
            return {
                "status": "incomplete",
                "reason": "missing model.safetensors or model.safetensors.index.json",
            }
        try:
            with safe_open(str(single_weight), framework="pt", device="cpu") as handle:
                if not handle.keys():
                    raise ValueError("contains no tensors")
        except Exception as exc:
            return {"status": "incomplete", "invalid": str(exc)}
        return {
            "status": "complete",
            "shards": 1,
            "missing": [],
            "invalid": [],
            "size_bytes": single_weight.stat().st_size,
            "expected_size_bytes": single_weight.stat().st_size,
        }
    with index_path.open("r", encoding="utf-8") as handle:
        index = json.load(handle)
    shards = sorted(set(index.get("weight_map", {}).values()))
    missing = [name for name in shards if not (path / name).is_file()]
    invalid: list[dict[str, str]] = []
    if not missing:
        for name in shards:
            try:
                with safe_open(str(path / name), framework="pt", device="cpu") as handle:
                    if not handle.keys():
                        raise ValueError("contains no tensors")
            except Exception as exc:
                invalid.append({"file": name, "error": str(exc)})
    actual_size = sum((path / name).stat().st_size for name in shards if (path / name).is_file())
    expected_size = index.get("metadata", {}).get("total_size")
    # The index total_size counts tensor payload bytes, while file sizes also
    # include safetensors headers, so a complete shard set is slightly larger.
    complete = not missing and not invalid and (
        expected_size is None or actual_size >= int(expected_size)
    )
    return {
        "status": "complete" if complete else "incomplete",
        "shards": len(shards),
        "missing": missing,
        "invalid": invalid,
        "size_bytes": actual_size,
        "expected_size_bytes": expected_size,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", default="configs/models/teacher_models.yaml")
    parser.add_argument(
        "--model",
        action="append",
        dest="selected_models",
        help="Audit only this catalog key; repeat for multiple models",
    )
    parser.add_argument(
        "--output", default="reports/teacher_model_inventory.json"
    )
    args = parser.parse_args()
    root = Path.cwd().resolve()
    catalog = load_catalog(root / args.catalog)
    if args.selected_models:
        unknown = sorted(set(args.selected_models) - set(catalog))
        if unknown:
            raise ValueError(f"Unknown models: {', '.join(unknown)}")
        catalog = {
            name: config
            for name, config in catalog.items()
            if name in set(args.selected_models)
        }
    models: dict[str, Any] = {}
    for name, config in catalog.items():
        path = root / str(config["local_dir"])
        details = audit_embedding(path) if name == "embedding" else audit_llm(path)
        models[name] = {
            "repo_id": config["repo_id"],
            "local_dir": str(path),
            **details,
        }
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "models": models,
    }
    output = root / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if all(item["status"] == "complete" for item in models.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
