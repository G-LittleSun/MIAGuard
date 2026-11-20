from pathlib import Path

from rag_mia_data.dataset_catalog import CatalogEntry
from rag_mia_data.dataset_normalize import normalize_dataset
from rag_mia_data.io_utils import read_jsonl, write_json_atomic, write_jsonl_atomic


NORMALIZED_KEYS = {
    "doc_id",
    "dataset_id",
    "text",
    "language",
    "membership_label",
    "source_partition",
    "source_index",
    "metadata",
}


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
    suffix = ".json" if adapter == "teacher_json_array" else ".jsonl"
    files = {
        "processed_corpus": {
            "path": (source_dir / "corpus.json").as_posix(),
            "record_count": corpus_count,
        },
        "target_member": {
            "path": (source_dir / f"member{suffix}").as_posix(),
            "record_count": member_count,
            "membership_label": 1,
        },
        "target_nonmember": {
            "path": (source_dir / f"nonmember{suffix}").as_posix(),
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


def test_teacher_normalize_preserves_order_and_nonmember_corpus_offset(
    tmp_path: Path,
) -> None:
    entry = _entry(
        tmp_path,
        dataset_id="ag_news",
        adapter="teacher_json_array",
        corpus_count=3,
        member_count=2,
        nonmember_count=1,
    )
    files = entry.descriptor["files"]
    write_json_atomic(
        tmp_path / files["processed_corpus"]["path"],
        ["member zero", "member one", "nonmember two"],
    )
    write_json_atomic(
        tmp_path / files["target_member"]["path"], ["member zero", "member one"]
    )
    write_json_atomic(
        tmp_path / files["target_nonmember"]["path"], ["nonmember two"]
    )

    assert normalize_dataset(entry, tmp_path) == {
        "member_count": 2,
        "nonmember_count": 1,
    }

    output_dir = tmp_path / entry.config["normalized_documents_dir"]
    members = list(read_jsonl(output_dir / "member_docs.jsonl"))
    nonmembers = list(read_jsonl(output_dir / "nonmember_docs.jsonl"))
    assert members[0] == {
        "doc_id": "ag_news_teacher_00000000",
        "dataset_id": "ag_news",
        "text": "member zero",
        "language": "en",
        "membership_label": 1,
        "source_partition": "target_member",
        "source_index": 0,
        "metadata": {},
    }
    assert nonmembers[0]["doc_id"] == "ag_news_teacher_00000002"
    assert nonmembers[0]["source_index"] == 2
    assert set(nonmembers[0]) == NORMALIZED_KEYS
    assert not any("sha" in key for row in members + nonmembers for key in row)


def test_t2_normalize_projects_exact_fields_and_is_stably_sorted(tmp_path: Path) -> None:
    entry = _entry(
        tmp_path,
        dataset_id="t2ranking",
        adapter="t2ranking_existing_jsonl",
        corpus_count=99,
        member_count=2,
        nonmember_count=1,
    )
    member_path = tmp_path / entry.config["source_files"]["target_member"]
    nonmember_path = tmp_path / entry.config["source_files"]["target_nonmember"]
    write_jsonl_atomic(
        member_path,
        [
            {
                "doc_id": "t2rank_00000020",
                "source_doc_id": "20",
                "text": "twenty",
                "duplicate_group_id": "dup-20",
                "membership_label": 1,
                "raw_text_sha256": "remove-me",
                "normalized_text_sha256": "remove-me-too",
            },
            {
                "doc_id": "t2rank_00000003",
                "source_doc_id": "3",
                "text": "three",
                "duplicate_group_id": "dup-3",
                "membership_label": 1,
                "raw_text_sha256": "remove-me",
            },
        ],
    )
    write_jsonl_atomic(
        nonmember_path,
        [
            {
                "doc_id": "t2rank_00000011",
                "source_doc_id": "11",
                "text": "eleven",
                "duplicate_group_id": "dup-11",
                "membership_label": 0,
                "raw_text_sha256": "remove-me",
            }
        ],
    )

    assert normalize_dataset(entry, tmp_path) == {
        "member_count": 2,
        "nonmember_count": 1,
    }
    output_dir = tmp_path / entry.config["normalized_documents_dir"]
    member_output = output_dir / "member_docs.jsonl"
    first_bytes = member_output.read_bytes()
    members = list(read_jsonl(member_output))
    nonmembers = list(read_jsonl(output_dir / "nonmember_docs.jsonl"))

    assert [row["doc_id"] for row in members] == [
        "t2rank_00000003",
        "t2rank_00000020",
    ]
    assert members[0] == {
        "doc_id": "t2rank_00000003",
        "dataset_id": "t2ranking",
        "text": "three",
        "language": "zh",
        "membership_label": 1,
        "source_partition": "target_member",
        "source_index": 3,
        "metadata": {
            "source_doc_id": "3",
            "duplicate_group_id": "dup-3",
        },
    }
    assert set(nonmembers[0]) == NORMALIZED_KEYS
    assert normalize_dataset(entry, tmp_path) == {
        "member_count": 2,
        "nonmember_count": 1,
    }
    assert member_output.read_bytes() == first_bytes
