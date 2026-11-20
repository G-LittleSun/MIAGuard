from __future__ import annotations

import csv
import hashlib
import json
from collections.abc import Iterable, Iterator
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


def iter_tsv(path: Path) -> Iterator[dict[str, str]]:
    csv.field_size_limit(2**31 - 1)
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        fields = reader.fieldnames
        if not fields or any(not field for field in fields):
            raise ValueError(f"TSV has a missing header: {path}")
        if len(fields) != len(set(fields)):
            raise ValueError(f"TSV has duplicate headers: {path}")
        for row in reader:
            if None in row:
                raise ValueError(f"TSV row has too many columns: {path}")
            yield {field: row[field] for field in fields}


def read_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                raise ValueError(f"Blank JSONL line at {path}:{line_number}")
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"JSONL value must be an object at {path}:{line_number}")
            yield value


def _atomic_path(path: Path) -> Path:
    return path.with_suffix(path.suffix + ".tmp")


def write_jsonl_atomic(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = _atomic_path(path)
    try:
        with temporary.open("w", encoding="utf-8", newline="\n") as handle:
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True))
                handle.write("\n")
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()


def write_json_atomic(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = _atomic_path(path)
    try:
        with temporary.open("w", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()


def write_yaml_atomic(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = _atomic_path(path)
    try:
        with temporary.open("w", encoding="utf-8", newline="\n") as handle:
            yaml.safe_dump(
                value,
                handle,
                allow_unicode=True,
                sort_keys=False,
            )
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()


def sha256_file(path: Path, chunk_size: int = 8 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def file_manifest_entry(path: Path, root: Path) -> dict[str, Any]:
    stat = path.stat()
    return {
        "path": path.relative_to(root).as_posix(),
        "size_bytes": stat.st_size,
        "modified_at": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
        "sha256": sha256_file(path),
    }
