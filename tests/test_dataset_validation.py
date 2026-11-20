import json
from pathlib import Path

import pytest

from rag_mia_data.dataset_catalog import CatalogEntry
from rag_mia_data.dataset_validation import (
    validate_and_record,
    validate_normalized_dataset,
    validate_raw_dataset,
)
from rag_mia_data.io_utils import write_jsonl_atomic


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


def _entry(
    root: Path,
    *,
    dataset_id: str,
    adapter: str,
    corpus_count: int,
    member_count: int,
    nonmember_count: int,
) -> CatalogEntry:
    source_dir = Path("DataSet") / dataset_id / "source"
    source_suffix = ".json" if adapter == "teacher_json_array" else ".jsonl"
    files = {
        "processed_corpus": {
            "path": (source_dir / "corpus.json").as_posix(),
            "record_count": corpus_count,
        },
        "target_member": {
            "path": (source_dir / f"member{source_suffix}").as_posix(),
            "record_count": member_count,
            "membership_label": 1,
        },
        "target_nonmember": {
            "path": (source_dir / f"nonmember{source_suffix}").as_posix(),
            "record_count": nonmember_count,
            "membership_label": 0,
        },
    }
    descriptor = {
        "dataset_id": dataset_id,
        "language": ["zh" if dataset_id == "t2ranking" else "en"],
        "files": files,
    }
    config = {
        "adapter": adapter,
        "normalized_documents_dir": f"data/processed/{dataset_id}/documents",
        "source_files": {
            "processed_corpus": files["processed_corpus"]["path"],
            "target_member": files["target_member"]["path"],
            "target_nonmember": files["target_nonmember"]["path"],
        },
    }
    return CatalogEntry(
        dataset_id=dataset_id,
        descriptor_path=root / "unused-dataset.json",
        config_path=root / "unused-config.yaml",
        descriptor=descriptor,
        config=config,
    )


def _legacy_row(doc_id: str, source_doc_id: str, label: int) -> dict[str, object]:
    return {
        "doc_id": doc_id,
        "source_doc_id": source_doc_id,
        "text": f"text {source_doc_id}",
        "duplicate_group_id": f"group-{source_doc_id}",
        "membership_label": label,
    }


def _normalized_row(
    dataset_id: str,
    doc_id: str,
    label: int,
    partition: str,
    source_index: int,
) -> dict[str, object]:
    return {
        "doc_id": doc_id,
        "dataset_id": dataset_id,
        "text": f"text {doc_id}",
        "language": "zh" if dataset_id == "t2ranking" else "en",
        "membership_label": label,
        "source_partition": partition,
        "source_index": source_index,
        "metadata": {},
    }


def test_teacher_raw_validation_accepts_exact_slices_and_rejects_wrong_slice(
    tmp_path: Path,
) -> None:
    entry = _entry(
        tmp_path,
        dataset_id="teacher_fixture",
        adapter="teacher_json_array",
        corpus_count=4,
        member_count=2,
        nonmember_count=2,
    )
    paths = entry.descriptor["files"]
    _write_json(tmp_path / paths["processed_corpus"]["path"], ["m0", "m1", "n0", "n1"])
    _write_json(tmp_path / paths["target_member"]["path"], ["m0", "m1"])
    nonmember_path = tmp_path / paths["target_nonmember"]["path"]
    _write_json(nonmember_path, ["n0", "n1"])

    assert validate_raw_dataset(entry, tmp_path) == {
        "dataset_id": "teacher_fixture",
        "status": "valid",
        "corpus_count": 4,
        "member_count": 2,
        "nonmember_count": 2,
    }

    _write_json(nonmember_path, ["n1", "n0"])
    with pytest.raises(ValueError, match="immediately following"):
        validate_raw_dataset(entry, tmp_path)


def test_t2_raw_validation_uses_descriptor_count_and_checks_labels_and_ids(
    tmp_path: Path,
) -> None:
    entry = _entry(
        tmp_path,
        dataset_id="t2ranking",
        adapter="t2ranking_existing_jsonl",
        corpus_count=2_303_643,
        member_count=2,
        nonmember_count=2,
    )
    member_path = tmp_path / entry.config["source_files"]["target_member"]
    nonmember_path = tmp_path / entry.config["source_files"]["target_nonmember"]
    member_rows = [_legacy_row("d2", "2", 1), _legacy_row("d1", "1", 1)]
    nonmember_rows = [_legacy_row("d4", "4", 0), _legacy_row("d3", "3", 0)]
    write_jsonl_atomic(member_path, member_rows)
    write_jsonl_atomic(nonmember_path, nonmember_rows)

    assert validate_raw_dataset(entry, tmp_path)["corpus_count"] == 2_303_643

    member_rows[0]["membership_label"] = 1.0
    write_jsonl_atomic(member_path, member_rows)
    with pytest.raises(ValueError, match="membership_label"):
        validate_raw_dataset(entry, tmp_path)

    member_rows[0]["membership_label"] = 1
    member_path.write_text(
        json.dumps(member_rows[0]) + "\n[]\n", encoding="utf-8"
    )
    with pytest.raises(ValueError, match="object"):
        validate_raw_dataset(entry, tmp_path)

    nonmember_rows[0]["doc_id"] = "d2"
    write_jsonl_atomic(member_path, member_rows)
    write_jsonl_atomic(nonmember_path, nonmember_rows)
    with pytest.raises(ValueError, match="disjoint"):
        validate_raw_dataset(entry, tmp_path)


@pytest.mark.parametrize("invalid_case", ["wrong_label", "overlap"])
def test_normalized_validation_rejects_wrong_label_or_overlap(
    tmp_path: Path, invalid_case: str
) -> None:
    entry = _entry(
        tmp_path,
        dataset_id="teacher_fixture",
        adapter="teacher_json_array",
        corpus_count=2,
        member_count=1,
        nonmember_count=1,
    )
    output_dir = tmp_path / entry.config["normalized_documents_dir"]
    member = _normalized_row("teacher_fixture", "member-1", 1, "target_member", 0)
    nonmember = _normalized_row(
        "teacher_fixture", "nonmember-1", 0, "target_nonmember", 1
    )
    if invalid_case == "wrong_label":
        member["membership_label"] = 1.0
    else:
        nonmember["doc_id"] = member["doc_id"]
    write_jsonl_atomic(output_dir / "member_docs.jsonl", [member])
    write_jsonl_atomic(output_dir / "nonmember_docs.jsonl", [nonmember])

    with pytest.raises(ValueError, match="membership_label|disjoint"):
        validate_normalized_dataset(entry, tmp_path)


def test_validate_and_record_writes_only_status_and_counts(tmp_path: Path) -> None:
    entry = _entry(
        tmp_path,
        dataset_id="teacher_fixture",
        adapter="teacher_json_array",
        corpus_count=2,
        member_count=1,
        nonmember_count=1,
    )
    files = entry.descriptor["files"]
    _write_json(tmp_path / files["processed_corpus"]["path"], ["m", "n"])
    _write_json(tmp_path / files["target_member"]["path"], ["m"])
    _write_json(tmp_path / files["target_nonmember"]["path"], ["n"])
    output_dir = tmp_path / entry.config["normalized_documents_dir"]
    write_jsonl_atomic(
        output_dir / "member_docs.jsonl",
        [_normalized_row("teacher_fixture", "member-1", 1, "target_member", 0)],
    )
    write_jsonl_atomic(
        output_dir / "nonmember_docs.jsonl",
        [_normalized_row("teacher_fixture", "nonmember-1", 0, "target_nonmember", 1)],
    )

    summary = validate_and_record(entry, tmp_path)

    assert summary == {
        "dataset_id": "teacher_fixture",
        "status": "valid",
        "corpus_count": 2,
        "member_count": 1,
        "nonmember_count": 1,
    }
    manifest_path = (
        tmp_path / "data/manifests/datasets/teacher_fixture.validation.json"
    )
    assert json.loads(manifest_path.read_text(encoding="utf-8")) == summary


def test_normalized_validation_rejects_file_symlink_outside_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project_root = tmp_path / "project"
    entry = _entry(
        project_root,
        dataset_id="teacher_fixture",
        adapter="teacher_json_array",
        corpus_count=2,
        member_count=1,
        nonmember_count=1,
    )
    output_dir = project_root / entry.config["normalized_documents_dir"]
    outside_member = tmp_path / "outside-member.jsonl"
    write_jsonl_atomic(
        outside_member,
        [_normalized_row("teacher_fixture", "member-1", 1, "target_member", 0)],
    )
    write_jsonl_atomic(
        output_dir / "nonmember_docs.jsonl",
        [_normalized_row("teacher_fixture", "nonmember-1", 0, "target_nonmember", 1)],
    )
    try:
        (output_dir / "member_docs.jsonl").symlink_to(outside_member)
    except OSError:
        original_is_symlink = Path.is_symlink
        monkeypatch.setattr(
            Path,
            "is_symlink",
            lambda path: path.name == "member_docs.jsonl"
            or original_is_symlink(path),
        )

    with pytest.raises(ValueError, match="symlink|project root"):
        validate_normalized_dataset(entry, project_root)
