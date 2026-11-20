from __future__ import annotations

import re
import shutil
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .dataset_catalog import CatalogEntry, load_catalog, resolve_dataset_ids
from .dataset_validation import validate_and_record
from .io_utils import (
    read_jsonl,
    utc_now_iso,
    write_json_atomic,
    write_jsonl_atomic,
    write_yaml_atomic,
)


_PROFILES = {"smoke", "pilot", "formal"}
_ATTACKS = {"masked_mia", "ia", "direct_rag_mia", "s2_mia"}
_CONFIG_KEYS = {
    "profile",
    "dataset_selection",
    "attacks",
    "target_counts",
    "runs_dir",
}
_SELECTION_KEYS = {"mode", "include"}
_COUNT_KEYS = {"members", "nonmembers"}
_RUN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")


@dataclass(frozen=True)
class AttackCount:
    members: int
    nonmembers: int


@dataclass(frozen=True)
class ExperimentConfig:
    profile: str
    mode: str
    include: tuple[str, ...]
    attacks: tuple[str, ...]
    target_counts: Mapping[str, AttackCount]
    runs_dir: Path


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be a mapping")
    return dict(value)


def _exact_keys(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    actual = set(value)
    if actual != expected:
        missing = sorted(expected - actual)
        unexpected = sorted(str(key) for key in actual - expected)
        raise ValueError(
            f"Invalid {label} keys: missing={missing}, unexpected={unexpected}"
        )


def _inside(project_root: Path, value: str | Path, label: str) -> Path:
    root = Path(project_root).resolve()
    if not isinstance(value, (str, Path)) or not str(value):
        raise ValueError(f"{label} must be a nonempty path")
    path = Path(value)
    resolved = (path if path.is_absolute() else root / path).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as error:
        raise ValueError(f"{label} must resolve inside the project root") from error
    return resolved


def _validate_counts(attacks: Sequence[str], counts: Mapping[str, AttackCount]) -> None:
    if set(counts) != set(attacks):
        raise ValueError("target_counts keys must exactly match attacks")
    for attack in attacks:
        count = counts[attack]
        if (
            type(count.members) is not int
            or type(count.nonmembers) is not int
            or count.members <= 0
            or count.nonmembers <= 0
        ):
            raise ValueError(f"target counts for {attack} must be positive integers")
        if count.members != count.nonmembers:
            raise ValueError(f"target counts for {attack} must be balanced")


def _validate_config(config: ExperimentConfig) -> None:
    if config.profile not in _PROFILES:
        raise ValueError(f"unsupported experiment profile: {config.profile!r}")
    if not config.attacks:
        raise ValueError("attacks must not be empty")
    if len(set(config.attacks)) != len(config.attacks):
        raise ValueError("duplicate attacks are not allowed")
    invalid = [attack for attack in config.attacks if attack not in _ATTACKS]
    if invalid:
        raise ValueError(f"unsupported attacks: {invalid}")
    _validate_counts(config.attacks, config.target_counts)


def load_experiment_config(
    project_root: Path,
    path: str | Path,
    mode_override: str | None = None,
    include_override: Sequence[str] | None = None,
) -> ExperimentConfig:
    root = Path(project_root).resolve()
    config_path = _inside(root, path, "experiment config path")
    with config_path.open("r", encoding="utf-8") as handle:
        raw = _mapping(yaml.safe_load(handle), "experiment config")
    _exact_keys(raw, _CONFIG_KEYS, "experiment config")

    selection = _mapping(raw["dataset_selection"], "dataset_selection")
    _exact_keys(selection, _SELECTION_KEYS, "dataset_selection")
    configured_include = selection["include"]
    if not isinstance(configured_include, list) or any(
        not isinstance(dataset_id, str) or not dataset_id
        for dataset_id in configured_include
    ):
        raise ValueError("dataset_selection.include must be a list of dataset IDs")
    mode = mode_override if mode_override is not None else selection["mode"]
    include = list(include_override) if include_override is not None else configured_include
    if not isinstance(mode, str):
        raise ValueError("dataset_selection.mode must be a string")

    raw_attacks = raw["attacks"]
    if not isinstance(raw_attacks, list) or any(
        not isinstance(attack, str) or not attack for attack in raw_attacks
    ):
        raise ValueError("attacks must be a list of attack names")
    if len(set(raw_attacks)) != len(raw_attacks):
        raise ValueError("duplicate attacks are not allowed")

    raw_counts = _mapping(raw["target_counts"], "target_counts")
    counts: dict[str, AttackCount] = {}
    for attack, value in raw_counts.items():
        count = _mapping(value, f"target_counts.{attack}")
        _exact_keys(count, _COUNT_KEYS, f"target_counts.{attack}")
        counts[str(attack)] = AttackCount(count["members"], count["nonmembers"])

    catalog = load_catalog(root)
    resolved_include = tuple(resolve_dataset_ids(catalog, mode, include))
    config = ExperimentConfig(
        profile=raw["profile"],
        mode=mode,
        include=resolved_include,
        attacks=tuple(raw_attacks),
        target_counts=counts,
        runs_dir=_inside(root, raw["runs_dir"], "runs_dir"),
    )
    _validate_config(config)
    for dataset_id in resolved_include:
        supported = set(catalog[dataset_id].descriptor["supported_attacks"])
        unsupported = [attack for attack in config.attacks if attack not in supported]
        if unsupported:
            raise ValueError(
                f"dataset {dataset_id} does not support attacks: {unsupported}"
            )
    return config


def _load_pools(
    project_root: Path, entry: CatalogEntry
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    output_dir = _inside(
        project_root,
        entry.config["normalized_documents_dir"],
        f"{entry.dataset_id} normalized_documents_dir",
    )
    member_path = _inside(
        project_root,
        output_dir / "member_docs.jsonl",
        f"{entry.dataset_id} member pool",
    )
    nonmember_path = _inside(
        project_root,
        output_dir / "nonmember_docs.jsonl",
        f"{entry.dataset_id} nonmember pool",
    )
    key = lambda row: (row["source_index"], row["doc_id"])
    return sorted(read_jsonl(member_path), key=key), sorted(
        read_jsonl(nonmember_path), key=key
    )


def _relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _resolved_config(config: ExperimentConfig, project_root: Path) -> dict[str, Any]:
    return {
        "profile": config.profile,
        "dataset_selection": {
            "mode": config.mode,
            "include": list(config.include),
        },
        "attacks": list(config.attacks),
        "target_counts": {
            attack: {
                "members": config.target_counts[attack].members,
                "nonmembers": config.target_counts[attack].nonmembers,
            }
            for attack in config.attacks
        },
        "runs_dir": _relative(config.runs_dir, project_root),
    }


def prepare_run(
    project_root: Path,
    catalog: Mapping[str, CatalogEntry],
    config: ExperimentConfig,
    run_id: str,
) -> dict[str, Any]:
    root = Path(project_root).resolve()
    if not isinstance(run_id, str) or _RUN_ID.fullmatch(run_id) is None:
        raise ValueError(
            "run_id must match ^[A-Za-z0-9][A-Za-z0-9_-]*$"
        )
    _validate_config(config)
    runs_dir = _inside(root, config.runs_dir, "runs_dir")
    selected = resolve_dataset_ids(catalog, config.mode, config.include)
    final_dir = runs_dir / run_id
    if final_dir.exists():
        raise FileExistsError(f"run_id already exists: {run_id}")

    for dataset_id in selected:
        entry = catalog[dataset_id]
        unsupported = [
            attack
            for attack in config.attacks
            if attack not in entry.descriptor["supported_attacks"]
        ]
        if unsupported:
            raise ValueError(
                f"dataset {dataset_id} does not support attacks: {unsupported}"
            )
        validate_and_record(entry, root)

    maximum_members = max(
        config.target_counts[attack].members for attack in config.attacks
    )
    maximum_nonmembers = max(
        config.target_counts[attack].nonmembers for attack in config.attacks
    )
    pools: dict[str, tuple[list[dict[str, Any]], list[dict[str, Any]]]] = {}
    for dataset_id in selected:
        members, nonmembers = _load_pools(root, catalog[dataset_id])
        if len(members) < maximum_members:
            raise ValueError(
                f"dataset {dataset_id} member capacity {len(members)} is below "
                f"required count {maximum_members}"
            )
        if len(nonmembers) < maximum_nonmembers:
            raise ValueError(
                f"dataset {dataset_id} nonmember capacity {len(nonmembers)} is below "
                f"required count {maximum_nonmembers}"
            )
        pools[dataset_id] = (members, nonmembers)

    created_at = utc_now_iso()
    validation_manifests = {
        dataset_id: f"data/manifests/datasets/{dataset_id}.validation.json"
        for dataset_id in selected
    }
    manifest: dict[str, Any] = {
        "run_id": run_id,
        "status": "prepared",
        "profile": config.profile,
        "datasets": list(selected),
        "attacks": list(config.attacks),
        "target_counts": {
            attack: {
                "members": config.target_counts[attack].members,
                "nonmembers": config.target_counts[attack].nonmembers,
            }
            for attack in config.attacks
        },
        "validation_manifests": validation_manifests,
        "dataset_runs": {},
        "created_at": created_at,
    }
    for dataset_id in selected:
        members, nonmembers = pools[dataset_id]
        dataset_attacks = {}
        for attack in config.attacks:
            count = config.target_counts[attack]
            dataset_attacks[attack] = {
                "member_ids": [row["doc_id"] for row in members[: count.members]],
                "nonmember_ids": [
                    row["doc_id"] for row in nonmembers[: count.nonmembers]
                ],
            }
        manifest["dataset_runs"][dataset_id] = {
            "target_docs_path": f"{dataset_id}/target_docs.jsonl",
            "validation_manifest_path": validation_manifests[dataset_id],
            "attacks": dataset_attacks,
        }

    runs_dir.mkdir(parents=True, exist_ok=True)
    temporary_dir = Path(tempfile.mkdtemp(prefix=f".{run_id}.", dir=runs_dir))
    try:
        for dataset_id in selected:
            members, nonmembers = pools[dataset_id]
            write_jsonl_atomic(
                temporary_dir / dataset_id / "target_docs.jsonl",
                members[:maximum_members] + nonmembers[:maximum_nonmembers],
            )
        write_yaml_atomic(
            temporary_dir / "resolved_config.yaml",
            _resolved_config(config, root),
        )
        write_json_atomic(temporary_dir / "run_manifest.json", manifest)
        if final_dir.exists():
            raise FileExistsError(f"run_id already exists: {run_id}")
        temporary_dir.replace(final_dir)
    finally:
        if temporary_dir.exists():
            shutil.rmtree(temporary_dir)
    return manifest


__all__ = [
    "AttackCount",
    "ExperimentConfig",
    "load_experiment_config",
    "prepare_run",
]
