from __future__ import annotations

import os
import shutil
import tempfile
from collections.abc import Mapping
from pathlib import Path

from .dataset_catalog import CatalogEntry


_SNAPSHOT_KEYS = ("processed_corpus", "target_member", "target_nonmember")
_TEACHER_ADAPTER = "teacher_json_array"
_COMPARE_CHUNK_SIZE = 1024 * 1024


def _resolve_inside(
    root: Path,
    configured_path: str,
    *,
    dataset_id: str,
    key: str,
    root_label: str,
) -> Path:
    resolved_root = Path(root).resolve()
    resolved_path = (resolved_root / configured_path).resolve()
    try:
        resolved_path.relative_to(resolved_root)
    except ValueError as error:
        raise ValueError(
            f"{dataset_id} {key} path {configured_path!r} resolves outside "
            f"the {root_label}: {resolved_path}"
        ) from error
    return resolved_path


def _files_equal(left: Path, right: Path) -> bool:
    with left.open("rb") as left_handle, right.open("rb") as right_handle:
        while True:
            left_chunk = left_handle.read(_COMPARE_CHUNK_SIZE)
            right_chunk = right_handle.read(_COMPARE_CHUNK_SIZE)
            if left_chunk != right_chunk:
                return False
            if not left_chunk:
                return True


def _copy_exact(source: Path, destination: Path) -> str:
    if destination.exists():
        if _files_equal(source, destination):
            return "unchanged"
        raise FileExistsError(
            f"destination exists with different bytes: {destination}"
        )

    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=destination.parent,
        prefix=f"{destination.name}.",
        suffix=".tmp",
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        shutil.copyfile(source, temporary)
        if not _files_equal(source, temporary):
            raise OSError(
                f"copied bytes differ from source {source}: {temporary}"
            )
        try:
            os.link(temporary, destination)
        except FileExistsError as error:
            try:
                unchanged = _files_equal(source, destination)
            except OSError:
                unchanged = False
            if unchanged:
                return "unchanged"
            raise FileExistsError(
                f"destination exists with different bytes: {destination}"
            ) from error
    finally:
        if temporary.exists():
            temporary.unlink()
    return "copied"


def import_teacher_snapshots(
    catalog: Mapping[str, CatalogEntry],
    project_root: Path,
    source_root: Path,
    dataset_ids: list[str],
) -> dict[str, dict[str, int]]:
    manifest: list[tuple[str, str, Path, Path]] = []
    teacher_ids: list[str] = []

    for dataset_id in dataset_ids:
        entry = catalog[dataset_id]
        if entry.config["adapter"] != _TEACHER_ADAPTER:
            continue
        teacher_ids.append(dataset_id)
        for key in _SNAPSHOT_KEYS:
            source = _resolve_inside(
                source_root,
                entry.config["source_files"][key],
                dataset_id=dataset_id,
                key=key,
                root_label="source root",
            )
            destination = _resolve_inside(
                project_root,
                entry.config["destination_files"][key],
                dataset_id=dataset_id,
                key=key,
                root_label="project root",
            )
            if not source.is_file():
                raise FileNotFoundError(
                    f"{dataset_id} {key} source file is missing: {source}"
                )
            manifest.append((dataset_id, key, source, destination))

    results = {
        dataset_id: {"copied": 0, "unchanged": 0}
        for dataset_id in teacher_ids
    }
    for dataset_id, key, source, destination in manifest:
        try:
            outcome = _copy_exact(source, destination)
        except FileExistsError as error:
            raise FileExistsError(
                f"{dataset_id} {key} destination differs: {destination}"
            ) from error
        results[dataset_id][outcome] += 1
    return results


__all__ = ["import_teacher_snapshots"]
