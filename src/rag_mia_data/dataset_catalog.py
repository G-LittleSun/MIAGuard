from __future__ import annotations

import json
from collections import OrderedDict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator


_CONFIG_KEYS = {
    "dataset_id",
    "adapter",
    "descriptor",
    "normalized_documents_dir",
    "source_files",
    "destination_files",
}
_ADAPTERS = {"teacher_json_array", "t2ranking_existing_jsonl"}


@dataclass(frozen=True)
class CatalogEntry:
    dataset_id: str
    descriptor_path: Path
    config_path: Path
    descriptor: dict[str, Any]
    config: dict[str, Any]


def _read_mapping(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        if path.suffix.lower() == ".json":
            value = json.load(handle)
        elif path.suffix.lower() in {".yaml", ".yml"}:
            value = yaml.safe_load(handle)
        else:
            raise ValueError(f"Unsupported mapping file type: {path}")
    if not isinstance(value, Mapping):
        raise ValueError(f"File must contain a mapping: {path}")
    return dict(value)


def _load_schema(path: Path) -> dict[str, Any]:
    schema = _read_mapping(path)
    Draft202012Validator.check_schema(schema)
    return schema


def _validate(value: Mapping[str, Any], schema: dict[str, Any], label: str) -> None:
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(value), key=lambda error: list(error.path))
    if not errors:
        return
    error = errors[0]
    location = ".".join(str(part) for part in error.path) or label
    raise ValueError(f"Invalid {label} field {location}: {error.message}")


def _resolve_inside(project_root: Path, value: Any, label: str) -> Path:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{label} must be a nonempty path string")
    path = Path(value)
    resolved = (path if path.is_absolute() else project_root / path).resolve()
    try:
        resolved.relative_to(project_root)
    except ValueError as error:
        raise ValueError(f"{label} must resolve inside the project root") from error
    return resolved


def _validate_config(
    config: dict[str, Any],
    dataset_id: str,
    descriptor_path: Path,
    project_root: Path,
) -> None:
    actual_keys = set(config)
    if actual_keys != _CONFIG_KEYS:
        missing = sorted(_CONFIG_KEYS - actual_keys)
        unexpected = sorted(str(key) for key in actual_keys - _CONFIG_KEYS)
        raise ValueError(
            f"Invalid config keys for {dataset_id}: "
            f"missing={missing}, unexpected={unexpected}"
        )
    if config["dataset_id"] != dataset_id:
        raise ValueError(
            f"config dataset_id {config['dataset_id']!r} does not match {dataset_id!r}"
        )
    adapter = config["adapter"]
    if not isinstance(adapter, str) or adapter not in _ADAPTERS:
        raise ValueError(f"unsupported adapter for {dataset_id}: {adapter!r}")

    configured_descriptor = _resolve_inside(
        project_root, config["descriptor"], f"config descriptor path for {dataset_id}"
    )
    if configured_descriptor != descriptor_path:
        raise ValueError(f"config descriptor path does not match registry for {dataset_id}")
    _resolve_inside(
        project_root,
        config["normalized_documents_dir"],
        f"normalized_documents_dir for {dataset_id}",
    )
    for field in ("source_files", "destination_files"):
        file_map = config[field]
        if not isinstance(file_map, Mapping):
            raise ValueError(f"{field} must be a mapping for {dataset_id}")
        for file_name, path in file_map.items():
            if not isinstance(file_name, str) or not file_name:
                raise ValueError(
                    f"{field} entry {file_name!r} for {dataset_id} "
                    "must have a nonempty string key"
                )
            if not isinstance(path, str) or not path:
                raise ValueError(
                    f"{field} entry {file_name!r} for {dataset_id} "
                    "must have a nonempty string value"
                )
            if field == "destination_files":
                _resolve_inside(
                    project_root,
                    path,
                    f"destination_files path {file_name} for {dataset_id}",
                )


def _validate_membership_labels(
    descriptor: dict[str, Any], dataset_id: str
) -> None:
    files = descriptor["files"]
    if files["target_member"].get("membership_label") != 1:
        raise ValueError(f"target_member membership_label must be 1 for {dataset_id}")
    if files["target_nonmember"].get("membership_label") != 0:
        raise ValueError(f"target_nonmember membership_label must be 0 for {dataset_id}")


def load_catalog(project_root: Path) -> OrderedDict[str, CatalogEntry]:
    root = Path(project_root).resolve()
    registry_schema = _load_schema(root / "schemas/registry.schema.json")
    dataset_schema = _load_schema(root / "schemas/dataset.schema.json")
    registry = _read_mapping(root / "DataSet/registry.json")
    _validate(registry, registry_schema, "registry")

    catalog: OrderedDict[str, CatalogEntry] = OrderedDict()
    for registry_entry in registry["datasets"]:
        dataset_id = registry_entry["dataset_id"]
        if dataset_id in catalog:
            raise ValueError(f"duplicate dataset_id in registry: {dataset_id}")

        descriptor_path = _resolve_inside(
            root, registry_entry["descriptor"], f"descriptor path for {dataset_id}"
        )
        config_path = _resolve_inside(
            root, registry_entry["config"], f"config path for {dataset_id}"
        )
        descriptor = _read_mapping(descriptor_path)
        _validate(descriptor, dataset_schema, f"descriptor {dataset_id}")
        if descriptor["dataset_id"] != dataset_id:
            raise ValueError(
                f"descriptor dataset_id {descriptor['dataset_id']!r} "
                f"does not match {dataset_id!r}"
            )
        for file_name, file_descriptor in descriptor["files"].items():
            _resolve_inside(
                root,
                file_descriptor["path"],
                f"descriptor file path {file_name} for {dataset_id}",
            )
        _validate_membership_labels(descriptor, dataset_id)

        config = _read_mapping(config_path)
        _validate_config(config, dataset_id, descriptor_path, root)
        catalog[dataset_id] = CatalogEntry(
            dataset_id=dataset_id,
            descriptor_path=descriptor_path,
            config_path=config_path,
            descriptor=descriptor,
            config=config,
        )
    return catalog


def resolve_dataset_ids(
    catalog: Mapping[str, CatalogEntry],
    mode: str,
    include: Sequence[str] | None,
) -> list[str]:
    requested = list(include or [])
    if mode == "all":
        resolved = [
            dataset_id
            for dataset_id, entry in catalog.items()
            if entry.descriptor["enabled"]
            and entry.descriptor["experiment_eligible"]
        ]
        if not resolved:
            raise ValueError("no enabled and experiment-eligible datasets are available")
        return resolved
    if mode == "single":
        if len(requested) != 1:
            raise ValueError("single mode requires exactly one included dataset")
    elif mode == "selected":
        if not requested:
            raise ValueError("selected mode requires at least one included dataset")
    else:
        raise ValueError(f"unsupported dataset selection mode: {mode!r}")

    if len(set(requested)) != len(requested):
        raise ValueError("duplicate dataset_id in explicit selection")
    for dataset_id in requested:
        if dataset_id not in catalog:
            raise ValueError(f"unknown dataset_id in explicit selection: {dataset_id}")
        descriptor = catalog[dataset_id].descriptor
        if not descriptor["enabled"] or not descriptor["experiment_eligible"]:
            raise ValueError(
                f"dataset {dataset_id} is disabled or experiment-ineligible"
            )
    return requested


__all__ = ["CatalogEntry", "load_catalog", "resolve_dataset_ids"]
