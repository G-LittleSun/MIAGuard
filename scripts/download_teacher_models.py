from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from huggingface_hub import HfApi, snapshot_download


IGNORED_PATTERNS = [
    "*.bin",
    "*.gguf",
    "*.h5",
    "*.msgpack",
    "*.onnx",
    "*.tflite",
    "openvino/*",
    "onnx/*",
    "original/*",
]


def load_catalog(path: Path) -> dict[str, dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    models = raw.get("models") if isinstance(raw, dict) else None
    if not isinstance(models, dict):
        raise ValueError("Model catalog must contain a models mapping")
    return models


def inspect_model(api: HfApi, name: str, config: dict[str, Any]) -> dict[str, Any]:
    info = api.model_info(str(config["repo_id"]), files_metadata=True)
    total = sum((item.size or 0) for item in info.siblings)
    return {
        "name": name,
        "repo_id": config["repo_id"],
        "gated": bool(info.gated),
        "revision": info.sha,
        "repository_file_count": len(info.siblings),
        "repository_size_bytes": total,
    }


def downloaded_files(path: Path) -> tuple[int, int]:
    files = [
        item
        for item in path.rglob("*")
        if item.is_file() and ".cache" not in item.parts
    ]
    return len(files), sum(item.stat().st_size for item in files)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", default="configs/models/teacher_models.yaml")
    parser.add_argument("--model", action="append", dest="models")
    parser.add_argument("--inspect", action="store_true")
    parser.add_argument("--max-workers", type=int, default=4)
    parser.add_argument(
        "--manifest", default="models/teacher_model_download_manifest.json"
    )
    args = parser.parse_args()

    root = Path.cwd().resolve()
    catalog = load_catalog(root / args.catalog)
    selected = args.models or list(catalog)
    unknown = [name for name in selected if name not in catalog]
    if unknown:
        raise ValueError(f"Unknown model names: {unknown}")

    api = HfApi()
    if args.inspect:
        for name in selected:
            try:
                print(json.dumps(inspect_model(api, name, catalog[name]), ensure_ascii=False))
            except Exception as error:
                print(json.dumps({"name": name, "error": str(error)}, ensure_ascii=False))
        return 0

    manifest_path = root / args.manifest
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, Any] = {"models": {}}
    if manifest_path.exists():
        with manifest_path.open("r", encoding="utf-8") as handle:
            existing = json.load(handle)
        if isinstance(existing, dict):
            manifest = existing
            manifest.setdefault("models", {})

    failed = False
    for name in selected:
        config = catalog[name]
        destination = root / str(config["local_dir"])
        destination.mkdir(parents=True, exist_ok=True)
        try:
            info = inspect_model(api, name, config)
            snapshot_download(
                repo_id=str(config["repo_id"]),
                revision=info["revision"],
                local_dir=destination,
                ignore_patterns=IGNORED_PATTERNS,
                max_workers=args.max_workers,
            )
            file_count, size_bytes = downloaded_files(destination)
            manifest["models"][name] = {
                **info,
                "downloaded_at": datetime.now(timezone.utc).isoformat(),
                "local_dir": str(config["local_dir"]),
                "local_file_count": file_count,
                "local_size_bytes": size_bytes,
                "status": "downloaded",
            }
            print(json.dumps(manifest["models"][name], ensure_ascii=False))
        except Exception as error:
            failed = True
            manifest["models"][name] = {
                "repo_id": config["repo_id"],
                "local_dir": str(config["local_dir"]),
                "status": "blocked",
                "error": str(error),
            }
            print(json.dumps(manifest["models"][name], ensure_ascii=False))
        with manifest_path.open("w", encoding="utf-8", newline="\n") as handle:
            json.dump(manifest, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
