from __future__ import annotations

import argparse
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import requests
import yaml
from huggingface_hub import HfApi, get_token, hf_hub_url, snapshot_download


SMALL_FILE_IGNORE = [
    "*.bin",
    "*.gguf",
    "*.h5",
    "*.msgpack",
    "*.onnx",
    "*.safetensors",
    "*.tflite",
    "onnx/*",
    "openvino/*",
    "original/*",
]


def load_catalog(path: Path) -> dict[str, dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    models = raw.get("models") if isinstance(raw, dict) else None
    if not isinstance(models, dict):
        raise ValueError("Model catalog must contain a models mapping")
    return models


def save_state(path: Path, completed: set[int], size: int, chunk_size: int) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(
            {
                "chunk_size": chunk_size,
                "completed": sorted(completed),
                "size": size,
            },
            handle,
            indent=2,
        )
        handle.write("\n")
    temporary.replace(path)


def load_state(path: Path, size: int, chunk_size: int) -> set[int]:
    if not path.exists():
        return set()
    with path.open("r", encoding="utf-8") as handle:
        raw = json.load(handle)
    if raw.get("size") != size or raw.get("chunk_size") != chunk_size:
        raise ValueError(f"Chunk state does not match current download: {path}")
    return {int(value) for value in raw.get("completed", [])}


def fetch_chunk(
    url: str,
    part_path: Path,
    start: int,
    end: int,
    retries: int,
    token: str | None,
) -> int:
    expected = end - start + 1
    for attempt in range(retries):
        try:
            headers = {"Range": f"bytes={start}-{end}"}
            if token:
                headers["Authorization"] = f"Bearer {token}"
            with requests.get(
                url,
                headers=headers,
                stream=True,
                timeout=(30, 180),
            ) as response:
                if response.status_code != 206:
                    raise RuntimeError(
                        f"Expected HTTP 206 for range {start}-{end}, got {response.status_code}"
                    )
                written = 0
                with part_path.open("r+b", buffering=0) as handle:
                    handle.seek(start)
                    for block in response.iter_content(chunk_size=4 * 1024 * 1024):
                        if block:
                            handle.write(block)
                            written += len(block)
                if written != expected:
                    raise RuntimeError(
                        f"Range {start}-{end} wrote {written} bytes, expected {expected}"
                    )
                return written
        except Exception:
            if attempt + 1 == retries:
                raise
            time.sleep(min(2 ** attempt, 20))
    raise AssertionError("unreachable")


def download_file(
    repo_id: str,
    revision: str,
    filename: str,
    size: int,
    destination: Path,
    chunk_size: int,
    workers: int,
    token: str | None,
) -> None:
    if destination.exists() and destination.stat().st_size == size:
        print(f"SKIP {filename} {size}", flush=True)
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    part_path = destination.with_suffix(destination.suffix + ".chunked")
    state_path = destination.with_suffix(destination.suffix + ".chunks.json")
    if not part_path.exists():
        with part_path.open("wb") as handle:
            handle.truncate(size)
    elif part_path.stat().st_size != size:
        raise ValueError(f"Partial file size mismatch: {part_path}")
    completed = load_state(state_path, size, chunk_size)
    total_chunks = (size + chunk_size - 1) // chunk_size
    pending = [index for index in range(total_chunks) if index not in completed]
    url = hf_hub_url(repo_id, filename, revision=revision)
    print(
        f"START {repo_id}/{filename} size={size} chunks={total_chunks} remaining={len(pending)}",
        flush=True,
    )
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {}
        for index in pending:
            start = index * chunk_size
            end = min(size - 1, start + chunk_size - 1)
            future = executor.submit(
                fetch_chunk, url, part_path, start, end, 5, token
            )
            futures[future] = index
        for future in as_completed(futures):
            index = futures[future]
            future.result()
            completed.add(index)
            save_state(state_path, completed, size, chunk_size)
            print(
                f"PROGRESS {filename} {len(completed)}/{total_chunks}",
                flush=True,
            )
    if len(completed) != total_chunks:
        raise RuntimeError(f"Download did not complete: {filename}")
    part_path.replace(destination)
    state_path.unlink(missing_ok=True)
    print(f"DONE {filename} {size}", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", default="configs/models/teacher_models.yaml")
    parser.add_argument("--model", required=True)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--chunk-mb", type=int, default=128)
    args = parser.parse_args()

    root = Path.cwd().resolve()
    catalog = load_catalog(root / args.catalog)
    if args.model not in catalog:
        raise ValueError(f"Unknown model: {args.model}")
    config = catalog[args.model]
    repo_id = str(config["repo_id"])
    destination = root / str(config["local_dir"])
    api = HfApi()
    info = api.model_info(repo_id, files_metadata=True)
    revision = str(info.sha)
    token = get_token()

    os.environ["HF_HUB_DISABLE_XET"] = "1"
    snapshot_download(
        repo_id=repo_id,
        revision=revision,
        local_dir=destination,
        ignore_patterns=SMALL_FILE_IGNORE,
        max_workers=4,
    )
    weights = [
        item
        for item in info.siblings
        if item.rfilename.endswith(".safetensors")
        and item.size
        and not item.rfilename.startswith(("onnx/", "openvino/", "original/"))
    ]
    if not weights:
        raise RuntimeError(f"No safetensors weights found for {repo_id}")
    for item in weights:
        download_file(
            repo_id,
            revision,
            item.rfilename,
            int(item.size),
            destination / item.rfilename,
            args.chunk_mb * 1024 * 1024,
            args.workers,
            token,
        )
    print(
        json.dumps(
            {
                "model": args.model,
                "repo_id": repo_id,
                "revision": revision,
                "status": "downloaded",
                "weight_files": len(weights),
                "weight_size_bytes": sum(int(item.size) for item in weights),
            },
            ensure_ascii=False,
        ),
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
