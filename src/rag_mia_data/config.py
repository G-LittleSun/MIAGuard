from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class PipelineConfig:
    project_root: Path
    config_path: Path
    run_name: str
    dataset_name: str
    dataset_path: Path
    documents_dir: Path
    manifests_dir: Path
    reports_dir: Path
    schema_path: Path
    seed: int
    candidate_doc_count: int
    member_ratio: float
    target_doc_count: int
    target_split_ratio: tuple[float, float, float]
    min_doc_chars: int
    max_doc_chars: int
    minhash_ngram: int
    minhash_num_perm: int
    minhash_bands: int
    near_duplicate_threshold: float
    topic_clusters: int


def _read_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = yaml.safe_load(handle) or {}
    if not isinstance(value, dict):
        raise ValueError(f"Configuration must be a mapping: {path}")
    return value


def _resolve(root: Path, value: str) -> Path:
    path = Path(value)
    return (path if path.is_absolute() else root / path).resolve()


def load_config(path: Path | str) -> PipelineConfig:
    config_path = Path(path).resolve()
    raw = _read_yaml(config_path)
    parent_name = raw.pop("extends", None)
    if parent_name:
        parent = _read_yaml(config_path.parent / str(parent_name))
        parent.update(raw)
        raw = parent

    project_root = config_path.parent.parent.resolve()
    split = tuple(float(value) for value in raw["target_split_ratio"])
    if len(split) != 3 or abs(sum(split) - 1.0) > 1e-9:
        raise ValueError("target_split_ratio must contain three values summing to 1")

    candidate_count = int(raw["candidate_doc_count"])
    target_count = int(raw["target_doc_count"])
    member_ratio = float(raw["member_ratio"])
    num_perm = int(raw["minhash_num_perm"])
    bands = int(raw["minhash_bands"])
    if candidate_count <= 0 or candidate_count % 2:
        raise ValueError("candidate_doc_count must be a positive even integer")
    if target_count <= 0 or target_count % 2 or target_count > candidate_count:
        raise ValueError("target_doc_count must be positive, even, and no larger than candidates")
    if not 0.0 < member_ratio < 1.0:
        raise ValueError("member_ratio must be between 0 and 1")
    if num_perm <= 0 or bands <= 0 or num_perm % bands:
        raise ValueError("minhash_num_perm must be divisible by minhash_bands")

    return PipelineConfig(
        project_root=project_root,
        config_path=config_path,
        run_name=config_path.stem,
        dataset_name=str(raw["dataset_name"]),
        dataset_path=_resolve(project_root, str(raw["dataset_path"])),
        documents_dir=_resolve(project_root, str(raw["documents_dir"])),
        manifests_dir=_resolve(project_root, str(raw["manifests_dir"])),
        reports_dir=_resolve(project_root, str(raw["reports_dir"])),
        schema_path=_resolve(project_root, str(raw["schema_path"])),
        seed=int(raw["seed"]),
        candidate_doc_count=candidate_count,
        member_ratio=member_ratio,
        target_doc_count=target_count,
        target_split_ratio=split,
        min_doc_chars=int(raw["min_doc_chars"]),
        max_doc_chars=int(raw["max_doc_chars"]),
        minhash_ngram=int(raw["minhash_ngram"]),
        minhash_num_perm=num_perm,
        minhash_bands=bands,
        near_duplicate_threshold=float(raw["near_duplicate_threshold"]),
        topic_clusters=int(raw["topic_clusters"]),
    )
