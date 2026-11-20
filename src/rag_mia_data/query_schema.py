from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from .io_utils import read_jsonl


def default_schema_path() -> Path:
    return Path(__file__).resolve().parents[2] / "schemas/query.schema.json"


def load_query_schema(path: Path | None = None) -> dict[str, Any]:
    schema_path = path or default_schema_path()
    with schema_path.open("r", encoding="utf-8") as handle:
        schema = json.load(handle)
    Draft202012Validator.check_schema(schema)
    return schema


def validate_query_record(
    record: dict[str, Any], schema_path: Path | None = None
) -> None:
    validator = Draft202012Validator(load_query_schema(schema_path))
    errors = sorted(validator.iter_errors(record), key=lambda error: list(error.path))
    if errors:
        error = errors[0]
        location = ".".join(str(part) for part in error.path) or "record"
        raise ValueError(f"Invalid query field {location}: {error.message}")


def validate_query_jsonl(path: Path, schema_path: Path | None = None) -> int:
    count = 0
    for count, record in enumerate(read_jsonl(path), start=1):
        try:
            validate_query_record(record, schema_path)
        except ValueError as error:
            raise ValueError(f"{path}:{count}: {error}") from error
    return count

