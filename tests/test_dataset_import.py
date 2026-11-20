from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest

from rag_mia_data.dataset_catalog import CatalogEntry
from rag_mia_data.dataset_import import _copy_exact, import_teacher_snapshots


SNAPSHOT_KEYS = ("processed_corpus", "target_member", "target_nonmember")


def _entry(
    dataset_id: str = "teacher",
    *,
    adapter: str = "teacher_json_array",
    source_files: dict[str, str] | None = None,
    destination_files: dict[str, str] | None = None,
) -> CatalogEntry:
    sources = source_files or {
        "processed_corpus": f"sources/{dataset_id}/processed.json",
        "target_member": f"sources/{dataset_id}/member.json",
        "target_nonmember": f"sources/{dataset_id}/nonmember.json",
    }
    destinations = destination_files or {
        "processed_corpus": f"snapshots/{dataset_id}/processed.json",
        "target_member": f"snapshots/{dataset_id}/member.json",
        "target_nonmember": f"snapshots/{dataset_id}/nonmember.json",
    }
    return CatalogEntry(
        dataset_id=dataset_id,
        descriptor_path=Path(f"descriptors/{dataset_id}.json"),
        config_path=Path(f"configs/{dataset_id}.yaml"),
        descriptor={},
        config={
            "dataset_id": dataset_id,
            "adapter": adapter,
            "source_files": sources,
            "destination_files": destinations,
        },
    )


def _write_sources(source_root: Path, entry: CatalogEntry) -> dict[str, bytes]:
    contents = {
        "processed_corpus": b'[..., "processed"]\x00\xff',
        "target_member": b'["member"]\r\n',
        "target_nonmember": b'["nonmember"]\n',
    }
    for key, content in contents.items():
        path = source_root / entry.config["source_files"][key]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    return contents


def _destination(project_root: Path, entry: CatalogEntry, key: str) -> Path:
    return project_root / entry.config["destination_files"][key]


def test_import_copies_exact_configured_snapshot_bytes(tmp_path: Path):
    source_root = tmp_path / "external"
    project_root = tmp_path / "project"
    entry = _entry()
    source_contents = _write_sources(source_root, entry)

    result = import_teacher_snapshots(
        {entry.dataset_id: entry}, project_root, source_root, [entry.dataset_id]
    )

    assert result == {"teacher": {"copied": 3, "unchanged": 0}}
    for key, expected in source_contents.items():
        assert _destination(project_root, entry, key).read_bytes() == expected


def test_import_rerun_reports_all_three_files_unchanged(tmp_path: Path):
    source_root = tmp_path / "external"
    project_root = tmp_path / "project"
    entry = _entry()
    _write_sources(source_root, entry)
    catalog = {entry.dataset_id: entry}

    import_teacher_snapshots(catalog, project_root, source_root, [entry.dataset_id])
    result = import_teacher_snapshots(
        catalog, project_root, source_root, [entry.dataset_id]
    )

    assert result == {"teacher": {"copied": 0, "unchanged": 3}}


def test_import_refuses_to_overwrite_different_destination(tmp_path: Path):
    source_root = tmp_path / "external"
    project_root = tmp_path / "project"
    entry = _entry()
    _write_sources(source_root, entry)
    destination = _destination(project_root, entry, "processed_corpus")
    destination.parent.mkdir(parents=True)
    destination.write_bytes(b"keep this existing snapshot")

    with pytest.raises(FileExistsError, match="teacher.*processed_corpus"):
        import_teacher_snapshots(
            {entry.dataset_id: entry},
            project_root,
            source_root,
            [entry.dataset_id],
        )

    assert destination.read_bytes() == b"keep this existing snapshot"
    assert not list(destination.parent.glob("*.tmp"))


def test_missing_source_preflight_leaves_all_requested_destinations_absent(
    tmp_path: Path,
):
    source_root = tmp_path / "external"
    project_root = tmp_path / "project"
    first = _entry("first")
    second = _entry("second")
    _write_sources(source_root, first)
    _write_sources(source_root, second)
    (source_root / second.config["source_files"]["target_nonmember"]).unlink()

    with pytest.raises(FileNotFoundError, match="second.*target_nonmember"):
        import_teacher_snapshots(
            {"first": first, "second": second},
            project_root,
            source_root,
            ["first", "second"],
        )

    for entry in (first, second):
        for key in SNAPSHOT_KEYS:
            assert not _destination(project_root, entry, key).exists()


def test_import_rejects_source_parent_escape(tmp_path: Path):
    source_root = tmp_path / "external"
    project_root = tmp_path / "project"
    outside = tmp_path / "outside.json"
    outside.write_bytes(b"outside")
    entry = _entry(
        source_files={
            "processed_corpus": "../outside.json",
            "target_member": "sources/member.json",
            "target_nonmember": "sources/nonmember.json",
        }
    )

    with pytest.raises(ValueError, match="teacher.*processed_corpus.*source root"):
        import_teacher_snapshots(
            {entry.dataset_id: entry},
            project_root,
            source_root,
            [entry.dataset_id],
        )


def test_import_rejects_source_symlink_escape(tmp_path: Path):
    source_root = tmp_path / "external"
    project_root = tmp_path / "project"
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "processed.json").write_bytes(b"outside")
    source_root.mkdir()
    link = source_root / "linked"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError as error:
        pytest.skip(f"directory symlinks unavailable: {error}")
    entry = _entry(
        source_files={
            "processed_corpus": "linked/processed.json",
            "target_member": "sources/member.json",
            "target_nonmember": "sources/nonmember.json",
        }
    )

    with pytest.raises(ValueError, match="teacher.*processed_corpus.*source root"):
        import_teacher_snapshots(
            {entry.dataset_id: entry},
            project_root,
            source_root,
            [entry.dataset_id],
        )


def test_import_rejects_destination_escape_from_direct_catalog_entry(
    tmp_path: Path,
):
    source_root = tmp_path / "external"
    project_root = tmp_path / "project"
    entry = _entry(
        destination_files={
            "processed_corpus": "../escaped.json",
            "target_member": "snapshots/member.json",
            "target_nonmember": "snapshots/nonmember.json",
        }
    )
    _write_sources(source_root, entry)

    with pytest.raises(ValueError, match="teacher.*processed_corpus.*project root"):
        import_teacher_snapshots(
            {entry.dataset_id: entry},
            project_root,
            source_root,
            [entry.dataset_id],
        )

    assert not (tmp_path / "escaped.json").exists()


@pytest.mark.parametrize("failure_stage", ["copy", "compare"])
def test_copy_or_compare_failure_cleans_final_and_temporary_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure_stage: str
):
    source = tmp_path / "source" / "snapshot.json"
    destination = tmp_path / "destination" / "snapshot.json"
    source.parent.mkdir()
    source.write_bytes(b"source remains immutable")
    original = source.read_bytes()

    if failure_stage == "copy":
        def fail_copy(_source: Path, temporary: Path) -> None:
            Path(temporary).write_bytes(b"partial")
            raise OSError("injected copy failure")

        monkeypatch.setattr(shutil, "copyfile", fail_copy)
    else:
        def fail_compare(_source: Path, _temporary: Path) -> bool:
            raise OSError("injected compare failure")

        monkeypatch.setattr("rag_mia_data.dataset_import._files_equal", fail_compare)

    with pytest.raises(OSError, match="injected"):
        _copy_exact(source, destination)

    assert source.read_bytes() == original
    assert not destination.exists()
    assert not list(destination.parent.glob("*.tmp"))


def test_copy_uses_unique_temporary_and_preserves_preexisting_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    source = tmp_path / "source.json"
    destination = tmp_path / "snapshots" / "snapshot.json"
    source.write_bytes(b"source")
    destination.parent.mkdir()
    preexisting = destination.with_name(f"{destination.name}.tmp")
    preexisting.write_bytes(b"preexisting")
    copied_to: list[Path] = []
    original_copyfile = shutil.copyfile

    def record_copy(copy_source: Path, copy_destination: Path) -> str:
        copied_to.append(Path(copy_destination))
        return original_copyfile(copy_source, copy_destination)

    monkeypatch.setattr(shutil, "copyfile", record_copy)

    assert _copy_exact(source, destination) == "copied"
    assert preexisting.read_bytes() == b"preexisting"
    assert len(copied_to) == 1
    assert copied_to[0] != preexisting
    assert copied_to[0].parent == destination.parent


def test_publish_race_does_not_overwrite_competing_destination(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    source = tmp_path / "source.json"
    destination = tmp_path / "snapshots" / "snapshot.json"
    source.write_bytes(b"source")
    original_link = os.link

    def publish_after_competitor(temporary: Path, final: Path) -> None:
        Path(final).write_bytes(b"competitor")
        original_link(temporary, final)

    monkeypatch.setattr(os, "link", publish_after_competitor)

    with pytest.raises(FileExistsError):
        _copy_exact(source, destination)

    assert destination.read_bytes() == b"competitor"


def test_same_size_changed_destination_with_restored_mtime_is_not_unchanged(
    tmp_path: Path,
):
    source = tmp_path / "source.json"
    destination = tmp_path / "snapshot.json"
    source.write_bytes(b"AAAA")
    destination.write_bytes(b"AAAA")
    original_stat = destination.stat()
    assert _copy_exact(source, destination) == "unchanged"

    destination.write_bytes(b"BBBB")
    os.utime(
        destination,
        ns=(original_stat.st_atime_ns, original_stat.st_mtime_ns),
    )
    assert destination.stat().st_mtime == original_stat.st_mtime

    with pytest.raises(FileExistsError):
        _copy_exact(source, destination)

    assert destination.read_bytes() == b"BBBB"


def test_non_teacher_entry_is_skipped(tmp_path: Path):
    source_root = tmp_path / "external"
    project_root = tmp_path / "project"
    entry = _entry("t2ranking", adapter="t2ranking_existing_jsonl")

    result = import_teacher_snapshots(
        {entry.dataset_id: entry}, project_root, source_root, [entry.dataset_id]
    )

    assert result == {}
    assert not project_root.exists()


def test_import_copies_only_three_configured_files(tmp_path: Path):
    source_root = tmp_path / "external"
    project_root = tmp_path / "project"
    entry = _entry()
    _write_sources(source_root, entry)
    excluded = {
        "Shadow/shadow.json": b"shadow",
        "indexes/corpus.faiss": b"faiss",
        "models/embedding.pkl": b"pickle",
        "attack_results/result.json": b"attack",
        "Datasets/ms_qa/auxiliary.json": b"auxiliary",
    }
    for relative, content in excluded.items():
        path = source_root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)

    import_teacher_snapshots(
        {entry.dataset_id: entry}, project_root, source_root, [entry.dataset_id]
    )

    files = {path.relative_to(project_root).as_posix() for path in project_root.rglob("*") if path.is_file()}
    assert files == {
        "snapshots/teacher/processed.json",
        "snapshots/teacher/member.json",
        "snapshots/teacher/nonmember.json",
    }
