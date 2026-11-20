import json
from pathlib import Path
import shutil

import pytest
import yaml

from rag_mia_data.config import PipelineConfig


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def catalog_project(tmp_path: Path) -> Path:
    schemas_dir = tmp_path / "schemas"
    schemas_dir.mkdir()
    for name in ("dataset.schema.json", "registry.schema.json"):
        shutil.copy2(PROJECT_ROOT / "schemas" / name, schemas_dir / name)

    dataset_directories = {
        "t2ranking": "T2Ranking",
        "ag_news": "AgNews",
        "healthcare_magic": "HealthCareMagic",
        "ms_marco": "MsMarco",
        "nq": "NQ",
    }
    registry_entries = []
    for dataset_id, dataset_directory in dataset_directories.items():
        descriptor_relative = Path("DataSet") / dataset_directory / "dataset.json"
        config_relative = Path("configs") / "datasets" / f"{dataset_id}.yaml"
        registry_entries.append(
            {
                "dataset_id": dataset_id,
                "descriptor": descriptor_relative.as_posix(),
                "config": config_relative.as_posix(),
            }
        )

        if dataset_id == "t2ranking":
            descriptor_files = {
                "processed_corpus": "data/processed/documents/candidate_docs.jsonl",
                "target_member": "data/processed/documents/member_docs.jsonl",
                "target_nonmember": "data/processed/documents/nonmember_docs.jsonl",
            }
            source_files = dict(descriptor_files)
        else:
            snapshot_dir = Path("DataSet") / dataset_directory / "teacher_snapshot"
            descriptor_files = {
                "processed_corpus": (snapshot_dir / "processed.json").as_posix(),
                "target_member": (snapshot_dir / "member.json").as_posix(),
                "target_nonmember": (snapshot_dir / "nonmember.json").as_posix(),
            }
            external_dir = Path("Datasets") / dataset_directory
            source_files = {
                "processed_corpus": (external_dir / "processed.json").as_posix(),
                "target_member": (external_dir / "member.json").as_posix(),
                "target_nonmember": (external_dir / "nonmember.json").as_posix(),
            }

        file_format = "jsonl" if dataset_id == "t2ranking" else "json"
        top_level = "jsonl" if dataset_id == "t2ranking" else "array"
        descriptor = {
            "schema_version": 1,
            "dataset_id": dataset_id,
            "display_name": dataset_id.replace("_", " ").title(),
            "enabled": True,
            "experiment_eligible": True,
            "language": ["en"],
            "domain": "fixture",
            "document_unit": "document",
            "snapshot_provenance": {
                "kind": (
                    "local_public_dataset"
                    if dataset_id == "t2ranking"
                    else "teacher_processed_snapshot"
                ),
                "source_project": "fixture-project",
            },
            "files": {
                "processed_corpus": {
                    "path": descriptor_files["processed_corpus"],
                    "format": file_format,
                    "encoding": "utf-8",
                    "top_level": top_level,
                    "record_type": (
                        "object" if dataset_id == "t2ranking" else "string"
                    ),
                    "record_count": 10,
                },
                "target_member": {
                    "path": descriptor_files["target_member"],
                    "format": file_format,
                    "encoding": "utf-8",
                    "top_level": top_level,
                    "record_type": "object",
                    "record_count": 5,
                    "membership_label": 1,
                },
                "target_nonmember": {
                    "path": descriptor_files["target_nonmember"],
                    "format": file_format,
                    "encoding": "utf-8",
                    "top_level": top_level,
                    "record_type": "object",
                    "record_count": 5,
                    "membership_label": 0,
                },
            },
            "supported_attacks": ["masked_mia", "ia"],
        }
        descriptor_path = tmp_path / descriptor_relative
        descriptor_path.parent.mkdir(parents=True, exist_ok=True)
        descriptor_path.write_text(
            json.dumps(descriptor, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        config = {
            "dataset_id": dataset_id,
            "adapter": (
                "t2ranking_existing_jsonl"
                if dataset_id == "t2ranking"
                else "teacher_json_array"
            ),
            "descriptor": descriptor_relative.as_posix(),
            "normalized_documents_dir": f"data/processed/{dataset_id}/documents",
            "source_files": source_files,
            "destination_files": (
                {}
                if dataset_id == "t2ranking"
                else {
                    "processed_corpus": (
                        f"data/processed/{dataset_id}/documents/corpus.jsonl"
                    ),
                    "target_member": (
                        f"data/processed/{dataset_id}/documents/member.jsonl"
                    ),
                    "target_nonmember": (
                        f"data/processed/{dataset_id}/documents/nonmember.jsonl"
                    ),
                }
            ),
        }
        config_path = tmp_path / config_relative
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(
            yaml.safe_dump(config, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )

    registry_path = tmp_path / "DataSet" / "registry.json"
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(
        json.dumps(
            {"schema_version": 1, "datasets": registry_entries},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return tmp_path


@pytest.fixture
def tiny_config(tmp_path: Path) -> PipelineConfig:
    root = tmp_path
    dataset = root / "DataSet/T2Ranking"
    dataset.mkdir(parents=True)
    files = {
        "collection.tsv": "pid\ttext\n1\t第一篇中文文档内容\n2\t第二篇中文文档内容\n3\t第三篇中文文档内容\n",
        "queries.train.tsv": "qid\ttext\nq1\t训练查询\n",
        "queries.dev.tsv": "qid\ttext\nq2\t开发查询\n",
        "queries.test.tsv": "qid\ttext\nq3\t测试查询\n",
        "qrels.train.tsv": "qid\t-\tpid\trel\nq1\t0\t1\t1\nqx\t0\t9\t1\n",
        "qrels.dev.tsv": "qid\t-\tpid\trel\nq2\t0\t2\t1\n",
        "qrels.retrieval.train.tsv": "qid\tpid\nq1\t1\n",
        "qrels.retrieval.dev.tsv": "qid\tpid\nq2\t2\n",
        "train.bm25.tsv": "qid\tpid\tindex\nq1\t1\t1\n",
        "train.mined.tsv": "qid\tpid\tindex\tscore\nq1\t1\t1\t9.5\n",
        "info.md": "local fixture\n",
    }
    for name, content in files.items():
        (dataset / name).write_text(content, encoding="utf-8")

    return PipelineConfig(
        project_root=root,
        config_path=root / "configs/smoke.yaml",
        run_name="smoke",
        dataset_name="T2Ranking",
        dataset_path=dataset,
        documents_dir=root / "data/processed/documents",
        manifests_dir=root / "data/manifests",
        reports_dir=root / "reports",
        schema_path=root / "schemas/query.schema.json",
        seed=20260713,
        candidate_doc_count=2,
        member_ratio=0.5,
        target_doc_count=2,
        target_split_ratio=(0.6, 0.2, 0.2),
        min_doc_chars=1,
        max_doc_chars=100,
        minhash_ngram=3,
        minhash_num_perm=64,
        minhash_bands=16,
        near_duplicate_threshold=0.8,
        topic_clusters=2,
    )
