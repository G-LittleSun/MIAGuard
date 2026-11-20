from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml

from rag_mia_data.dataset_catalog import load_catalog, resolve_dataset_ids


DATASET_IDS = ["t2ranking", "ag_news", "healthcare_magic", "ms_marco", "nq"]
DATASET_DIRECTORIES = {
    "t2ranking": "T2Ranking",
    "ag_news": "AgNews",
    "healthcare_magic": "HealthCareMagic",
    "ms_marco": "MsMarco",
    "nq": "NQ",
}

PROJECT_ROOT = Path(__file__).resolve().parents[1]


REAL_CATALOG_EXPECTED = {
    "t2ranking": {
        "descriptor": {
            "schema_version": 1,
            "dataset_id": "t2ranking",
            "display_name": "T2Ranking",
            "enabled": True,
            "experiment_eligible": True,
            "language": ["zh"],
            "domain": "retrieval",
            "document_unit": "passage",
            "snapshot_provenance": {
                "kind": "local_public_dataset",
                "source_project": "unknown",
            },
            "files": {
                "processed_corpus": {
                    "path": "DataSet/T2Ranking/collection.tsv",
                    "format": "tsv",
                    "encoding": "utf-8",
                    "top_level": "rows",
                    "record_type": "object",
                    "record_count": 2_303_643,
                },
                "target_member": {
                    "path": "data/processed/documents/member_docs.jsonl",
                    "format": "jsonl",
                    "encoding": "utf-8",
                    "top_level": "jsonl",
                    "record_type": "object",
                    "record_count": 5_000,
                    "membership_label": 1,
                },
                "target_nonmember": {
                    "path": "data/processed/documents/nonmember_docs.jsonl",
                    "format": "jsonl",
                    "encoding": "utf-8",
                    "top_level": "jsonl",
                    "record_type": "object",
                    "record_count": 5_000,
                    "membership_label": 0,
                },
            },
            "supported_attacks": [
                "masked_mia",
                "ia",
                "direct_rag_mia",
                "s2_mia",
            ],
        },
        "config": {
            "dataset_id": "t2ranking",
            "adapter": "t2ranking_existing_jsonl",
            "descriptor": "DataSet/T2Ranking/dataset.json",
            "normalized_documents_dir": "data/processed/t2ranking/documents",
            "source_files": {
                "target_member": "data/processed/documents/member_docs.jsonl",
                "target_nonmember": "data/processed/documents/nonmember_docs.jsonl",
            },
            "destination_files": {},
        },
    },
    "ag_news": {
        "descriptor": {
            "schema_version": 1,
            "dataset_id": "ag_news",
            "display_name": "AG News",
            "enabled": True,
            "experiment_eligible": True,
            "language": ["en"],
            "domain": "news",
            "document_unit": "news article text",
            "snapshot_provenance": {
                "kind": "teacher_processed_snapshot",
                "source_project": "D:/Project/MIA-lihao/IAplusBigLLM",
            },
            "files": {
                "processed_corpus": {
                    "path": (
                        "DataSet/AgNews/teacher_snapshot/processed/"
                        "ag_news_processed.json"
                    ),
                    "format": "json",
                    "encoding": "utf-8",
                    "top_level": "array",
                    "record_type": "string",
                    "record_count": 120_000,
                },
                "target_member": {
                    "path": (
                        "DataSet/AgNews/teacher_snapshot/splits/target_member.json"
                    ),
                    "format": "json",
                    "encoding": "utf-8",
                    "top_level": "array",
                    "record_type": "string",
                    "record_count": 8_000,
                    "membership_label": 1,
                },
                "target_nonmember": {
                    "path": (
                        "DataSet/AgNews/teacher_snapshot/splits/"
                        "target_nonmember.json"
                    ),
                    "format": "json",
                    "encoding": "utf-8",
                    "top_level": "array",
                    "record_type": "string",
                    "record_count": 1_000,
                    "membership_label": 0,
                },
            },
            "supported_attacks": [
                "masked_mia",
                "ia",
                "direct_rag_mia",
                "s2_mia",
            ],
        },
        "config": {
            "dataset_id": "ag_news",
            "adapter": "teacher_json_array",
            "descriptor": "DataSet/AgNews/dataset.json",
            "normalized_documents_dir": "data/processed/ag_news/documents",
            "source_files": {
                "processed_corpus": "Datasets/AgNews/ag_news_processed.json",
                "target_member": (
                    "SamplesDatabase/AgNews/TargetModel/samples_member.json"
                ),
                "target_nonmember": (
                    "SamplesDatabase/AgNews/TargetModel/samples_nonmember.json"
                ),
            },
            "destination_files": {
                "processed_corpus": (
                    "DataSet/AgNews/teacher_snapshot/processed/"
                    "ag_news_processed.json"
                ),
                "target_member": (
                    "DataSet/AgNews/teacher_snapshot/splits/target_member.json"
                ),
                "target_nonmember": (
                    "DataSet/AgNews/teacher_snapshot/splits/target_nonmember.json"
                ),
            },
        },
    },
    "healthcare_magic": {
        "descriptor": {
            "schema_version": 1,
            "dataset_id": "healthcare_magic",
            "display_name": "HealthCareMagic",
            "enabled": True,
            "experiment_eligible": True,
            "language": ["en"],
            "domain": "medical QA",
            "document_unit": "patient text and doctor answer",
            "snapshot_provenance": {
                "kind": "teacher_processed_snapshot",
                "source_project": "D:/Project/MIA-lihao/IAplusBigLLM",
            },
            "files": {
                "processed_corpus": {
                    "path": (
                        "DataSet/HealthCareMagic/teacher_snapshot/processed/"
                        "HealthCareMagic-100k-en-processed.json"
                    ),
                    "format": "json",
                    "encoding": "utf-8",
                    "top_level": "array",
                    "record_type": "string",
                    "record_count": 112_165,
                },
                "target_member": {
                    "path": (
                        "DataSet/HealthCareMagic/teacher_snapshot/splits/"
                        "target_member.json"
                    ),
                    "format": "json",
                    "encoding": "utf-8",
                    "top_level": "array",
                    "record_type": "string",
                    "record_count": 8_000,
                    "membership_label": 1,
                },
                "target_nonmember": {
                    "path": (
                        "DataSet/HealthCareMagic/teacher_snapshot/splits/"
                        "target_nonmember.json"
                    ),
                    "format": "json",
                    "encoding": "utf-8",
                    "top_level": "array",
                    "record_type": "string",
                    "record_count": 1_000,
                    "membership_label": 0,
                },
            },
            "supported_attacks": [
                "masked_mia",
                "ia",
                "direct_rag_mia",
                "s2_mia",
            ],
        },
        "config": {
            "dataset_id": "healthcare_magic",
            "adapter": "teacher_json_array",
            "descriptor": "DataSet/HealthCareMagic/dataset.json",
            "normalized_documents_dir": (
                "data/processed/healthcare_magic/documents"
            ),
            "source_files": {
                "processed_corpus": (
                    "Datasets/HealthCareMagic/"
                    "HealthCareMagic-100k-en-processed.json"
                ),
                "target_member": (
                    "SamplesDatabase/HealthCareMagic/TargetModel/"
                    "samples_member.json"
                ),
                "target_nonmember": (
                    "SamplesDatabase/HealthCareMagic/TargetModel/"
                    "samples_nonmember.json"
                ),
            },
            "destination_files": {
                "processed_corpus": (
                    "DataSet/HealthCareMagic/teacher_snapshot/processed/"
                    "HealthCareMagic-100k-en-processed.json"
                ),
                "target_member": (
                    "DataSet/HealthCareMagic/teacher_snapshot/splits/"
                    "target_member.json"
                ),
                "target_nonmember": (
                    "DataSet/HealthCareMagic/teacher_snapshot/splits/"
                    "target_nonmember.json"
                ),
            },
        },
    },
    "ms_marco": {
        "descriptor": {
            "schema_version": 1,
            "dataset_id": "ms_marco",
            "display_name": "MS MARCO",
            "enabled": True,
            "experiment_eligible": True,
            "language": ["en"],
            "domain": "web QA",
            "document_unit": "question and answer",
            "snapshot_provenance": {
                "kind": "teacher_processed_snapshot",
                "source_project": "D:/Project/MIA-lihao/IAplusBigLLM",
            },
            "files": {
                "processed_corpus": {
                    "path": (
                        "DataSet/MsMarco/teacher_snapshot/processed/"
                        "ms_processed.json"
                    ),
                    "format": "json",
                    "encoding": "utf-8",
                    "top_level": "array",
                    "record_type": "string",
                    "record_count": 23_177,
                },
                "target_member": {
                    "path": (
                        "DataSet/MsMarco/teacher_snapshot/splits/"
                        "target_member.json"
                    ),
                    "format": "json",
                    "encoding": "utf-8",
                    "top_level": "array",
                    "record_type": "string",
                    "record_count": 8_000,
                    "membership_label": 1,
                },
                "target_nonmember": {
                    "path": (
                        "DataSet/MsMarco/teacher_snapshot/splits/"
                        "target_nonmember.json"
                    ),
                    "format": "json",
                    "encoding": "utf-8",
                    "top_level": "array",
                    "record_type": "string",
                    "record_count": 1_000,
                    "membership_label": 0,
                },
            },
            "supported_attacks": [
                "masked_mia",
                "ia",
                "direct_rag_mia",
                "s2_mia",
            ],
        },
        "config": {
            "dataset_id": "ms_marco",
            "adapter": "teacher_json_array",
            "descriptor": "DataSet/MsMarco/dataset.json",
            "normalized_documents_dir": "data/processed/ms_marco/documents",
            "source_files": {
                "processed_corpus": "Datasets/MsMarco/ms_processed.json",
                "target_member": (
                    "SamplesDatabase/MsMarco/TargetModel/samples_member.json"
                ),
                "target_nonmember": (
                    "SamplesDatabase/MsMarco/TargetModel/samples_nonmember.json"
                ),
            },
            "destination_files": {
                "processed_corpus": (
                    "DataSet/MsMarco/teacher_snapshot/processed/ms_processed.json"
                ),
                "target_member": (
                    "DataSet/MsMarco/teacher_snapshot/splits/target_member.json"
                ),
                "target_nonmember": (
                    "DataSet/MsMarco/teacher_snapshot/splits/target_nonmember.json"
                ),
            },
        },
    },
    "nq": {
        "descriptor": {
            "schema_version": 1,
            "dataset_id": "nq",
            "display_name": "Natural Questions",
            "enabled": True,
            "experiment_eligible": True,
            "language": ["en"],
            "domain": "open-domain QA",
            "document_unit": "question and answer or context",
            "snapshot_provenance": {
                "kind": "teacher_processed_snapshot",
                "source_project": "D:/Project/MIA-lihao/IAplusBigLLM",
            },
            "files": {
                "processed_corpus": {
                    "path": (
                        "DataSet/NQ/teacher_snapshot/processed/nq_processed.json"
                    ),
                    "format": "json",
                    "encoding": "utf-8",
                    "top_level": "array",
                    "record_type": "string",
                    "record_count": 42_023,
                },
                "target_member": {
                    "path": (
                        "DataSet/NQ/teacher_snapshot/splits/target_member.json"
                    ),
                    "format": "json",
                    "encoding": "utf-8",
                    "top_level": "array",
                    "record_type": "string",
                    "record_count": 8_000,
                    "membership_label": 1,
                },
                "target_nonmember": {
                    "path": (
                        "DataSet/NQ/teacher_snapshot/splits/target_nonmember.json"
                    ),
                    "format": "json",
                    "encoding": "utf-8",
                    "top_level": "array",
                    "record_type": "string",
                    "record_count": 1_000,
                    "membership_label": 0,
                },
            },
            "supported_attacks": [
                "masked_mia",
                "ia",
                "direct_rag_mia",
                "s2_mia",
            ],
        },
        "config": {
            "dataset_id": "nq",
            "adapter": "teacher_json_array",
            "descriptor": "DataSet/NQ/dataset.json",
            "normalized_documents_dir": "data/processed/nq/documents",
            "source_files": {
                "processed_corpus": "Datasets/NQ/nq_processed.json",
                "target_member": (
                    "SamplesDatabase/NQ/TargetModel/samples_member.json"
                ),
                "target_nonmember": (
                    "SamplesDatabase/NQ/TargetModel/samples_nonmember.json"
                ),
            },
            "destination_files": {
                "processed_corpus": (
                    "DataSet/NQ/teacher_snapshot/processed/nq_processed.json"
                ),
                "target_member": (
                    "DataSet/NQ/teacher_snapshot/splits/target_member.json"
                ),
                "target_nonmember": (
                    "DataSet/NQ/teacher_snapshot/splits/target_nonmember.json"
                ),
            },
        },
    },
}


def test_real_catalog_preserves_expected_registry_order():
    catalog = load_catalog(PROJECT_ROOT)

    assert list(catalog) == DATASET_IDS


@pytest.mark.parametrize("dataset_id", DATASET_IDS)
def test_real_catalog_declares_exact_dataset_contract(dataset_id: str):
    catalog = load_catalog(PROJECT_ROOT)
    expected = REAL_CATALOG_EXPECTED[dataset_id]

    assert catalog[dataset_id].descriptor == expected["descriptor"]
    assert catalog[dataset_id].config == expected["config"]


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2), encoding="utf-8")


def _read_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _write_yaml(path: Path, value: dict[str, Any]) -> None:
    path.write_text(yaml.safe_dump(value, sort_keys=False), encoding="utf-8")


def _descriptor_path(project_root: Path, dataset_id: str) -> Path:
    return project_root / "DataSet" / DATASET_DIRECTORIES[dataset_id] / "dataset.json"


def test_load_catalog_preserves_registry_order_and_resolves_paths(
    catalog_project: Path,
):
    catalog = load_catalog(catalog_project)

    assert list(catalog) == DATASET_IDS
    assert catalog["ag_news"].descriptor_path == (
        catalog_project / "DataSet/AgNews/dataset.json"
    ).resolve()
    assert catalog["ag_news"].config_path == (
        catalog_project / "configs/datasets/ag_news.yaml"
    ).resolve()
    assert catalog["ag_news"].descriptor["dataset_id"] == "ag_news"
    assert catalog["ag_news"].config["adapter"] == "teacher_json_array"


def test_load_catalog_accepts_external_teacher_sources_and_empty_t2_destination(
    catalog_project: Path,
):
    catalog = load_catalog(catalog_project)

    assert catalog["ag_news"].config["source_files"]["processed_corpus"].startswith(
        "Datasets/AgNews/"
    )
    assert catalog["t2ranking"].config["adapter"] == "t2ranking_existing_jsonl"
    assert catalog["t2ranking"].config["destination_files"] == {}


def test_resolve_dataset_ids_supports_single_selected_and_all(catalog_project: Path):
    catalog = load_catalog(catalog_project)

    assert resolve_dataset_ids(catalog, "single", ["ms_marco"]) == ["ms_marco"]
    assert resolve_dataset_ids(catalog, "selected", ["nq", "ag_news"]) == [
        "nq",
        "ag_news",
    ]
    assert resolve_dataset_ids(catalog, "all", []) == DATASET_IDS


@pytest.mark.parametrize("include", [[], ["ag_news", "nq"]])
def test_resolve_single_requires_exactly_one_dataset(
    catalog_project: Path, include: list[str]
):
    catalog = load_catalog(catalog_project)

    with pytest.raises(ValueError, match="exactly one"):
        resolve_dataset_ids(catalog, "single", include)


def test_load_catalog_rejects_descriptor_id_mismatch(catalog_project: Path):
    descriptor_path = _descriptor_path(catalog_project, "ag_news")
    descriptor = _read_json(descriptor_path)
    descriptor["dataset_id"] = "wrong_dataset"
    _write_json(descriptor_path, descriptor)

    with pytest.raises(ValueError, match="descriptor dataset_id"):
        load_catalog(catalog_project)


def test_all_skips_disabled_dataset_but_explicit_selection_rejects_it(
    catalog_project: Path,
):
    descriptor_path = _descriptor_path(catalog_project, "nq")
    descriptor = _read_json(descriptor_path)
    descriptor["enabled"] = False
    _write_json(descriptor_path, descriptor)
    catalog = load_catalog(catalog_project)

    assert resolve_dataset_ids(catalog, "all", []) == DATASET_IDS[:-1]
    with pytest.raises(ValueError, match="disabled or experiment-ineligible"):
        resolve_dataset_ids(catalog, "single", ["nq"])


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("dataset_id", "wrong_dataset", "config dataset_id"),
        ("adapter", "unknown_adapter", "unsupported adapter"),
        ("adapter", [], "unsupported adapter"),
        ("descriptor", "DataSet/NQ/dataset.json", "descriptor path"),
        ("normalized_documents_dir", "../outside", "project root"),
        ("source_files", [], "source_files must be a mapping"),
        ("destination_files", [], "destination_files must be a mapping"),
    ],
)
def test_load_catalog_rejects_invalid_config_contract(
    catalog_project: Path, field: str, value: object, message: str
):
    config_path = catalog_project / "configs/datasets/ag_news.yaml"
    config = _read_yaml(config_path)
    config[field] = value
    _write_yaml(config_path, config)

    with pytest.raises(ValueError, match=message):
        load_catalog(catalog_project)


def test_load_catalog_rejects_unexpected_config_key(catalog_project: Path):
    config_path = catalog_project / "configs/datasets/ag_news.yaml"
    config = _read_yaml(config_path)
    config["sha256"] = "not-allowed"
    _write_yaml(config_path, config)

    with pytest.raises(ValueError, match="config keys"):
        load_catalog(catalog_project)


def test_load_catalog_rejects_descriptor_file_path_outside_project_root(
    catalog_project: Path,
):
    descriptor_path = _descriptor_path(catalog_project, "ag_news")
    descriptor = _read_json(descriptor_path)
    descriptor["files"]["processed_corpus"]["path"] = "../outside/processed.json"
    _write_json(descriptor_path, descriptor)

    with pytest.raises(ValueError, match="project root"):
        load_catalog(catalog_project)


def test_load_catalog_rejects_destination_file_path_outside_project_root(
    catalog_project: Path,
):
    config_path = catalog_project / "configs/datasets/ag_news.yaml"
    config = _read_yaml(config_path)
    config["destination_files"]["processed_corpus"] = "../outside/corpus.jsonl"
    _write_yaml(config_path, config)

    with pytest.raises(ValueError, match="project root"):
        load_catalog(catalog_project)


@pytest.mark.parametrize(
    ("field", "key", "value"),
    [
        ("source_files", "", "Datasets/AgNews/processed.json"),
        ("source_files", 1, "Datasets/AgNews/processed.json"),
        ("source_files", "processed_corpus", ""),
        ("source_files", "processed_corpus", 1),
        ("destination_files", "", "data/processed/ag_news/corpus.jsonl"),
        ("destination_files", 1, "data/processed/ag_news/corpus.jsonl"),
        ("destination_files", "processed_corpus", ""),
        ("destination_files", "processed_corpus", 1),
    ],
)
def test_load_catalog_rejects_invalid_file_map_entries_with_context(
    catalog_project: Path, field: str, key: object, value: object
):
    config_path = catalog_project / "configs/datasets/ag_news.yaml"
    config = _read_yaml(config_path)
    config[field] = {key: value}
    _write_yaml(config_path, config)

    with pytest.raises(ValueError) as error_info:
        load_catalog(catalog_project)
    message = str(error_info.value)
    assert field in message
    assert "ag_news" in message
    assert repr(key) in message


@pytest.mark.parametrize(
    ("case", "value"),
    [
        ("additional", "not-allowed"),
        ("missing", None),
        ("wrong_type", "yes"),
    ],
)
def test_load_catalog_rejects_strict_descriptor_schema_violations(
    catalog_project: Path, case: str, value: object
):
    descriptor_path = _descriptor_path(catalog_project, "ag_news")
    descriptor = _read_json(descriptor_path)
    if case == "additional":
        descriptor["sha256"] = value
    elif case == "missing":
        descriptor.pop("display_name")
    else:
        descriptor["enabled"] = value
    _write_json(descriptor_path, descriptor)

    with pytest.raises(ValueError, match="Invalid descriptor ag_news"):
        load_catalog(catalog_project)


@pytest.mark.parametrize("case", ["additional", "missing", "wrong_type"])
def test_load_catalog_rejects_strict_registry_schema_violations(
    catalog_project: Path, case: str
):
    registry_path = catalog_project / "DataSet/registry.json"
    registry = _read_json(registry_path)
    if case == "additional":
        registry["sha256"] = "not-allowed"
    elif case == "missing":
        registry.pop("schema_version")
    else:
        registry["datasets"] = {}
    _write_json(registry_path, registry)

    with pytest.raises(ValueError, match="Invalid registry"):
        load_catalog(catalog_project)


@pytest.mark.parametrize(
    ("file_name", "label", "message"),
    [
        ("target_member", 0, "target_member membership_label must be 1"),
        ("target_nonmember", 1, "target_nonmember membership_label must be 0"),
    ],
)
def test_load_catalog_rejects_wrong_target_membership_label(
    catalog_project: Path, file_name: str, label: int, message: str
):
    descriptor_path = _descriptor_path(catalog_project, "ag_news")
    descriptor = _read_json(descriptor_path)
    descriptor["files"][file_name]["membership_label"] = label
    _write_json(descriptor_path, descriptor)

    with pytest.raises(ValueError, match=message):
        load_catalog(catalog_project)


def test_load_catalog_rejects_duplicate_registry_ids(catalog_project: Path):
    registry_path = catalog_project / "DataSet/registry.json"
    registry = _read_json(registry_path)
    registry["datasets"][1]["dataset_id"] = "t2ranking"
    _write_json(registry_path, registry)

    with pytest.raises(ValueError, match="duplicate dataset_id"):
        load_catalog(catalog_project)


def test_explicit_selection_rejects_unknown_duplicate_and_ineligible_ids(
    catalog_project: Path,
):
    descriptor_path = _descriptor_path(catalog_project, "ms_marco")
    descriptor = _read_json(descriptor_path)
    descriptor["experiment_eligible"] = False
    _write_json(descriptor_path, descriptor)
    catalog = load_catalog(catalog_project)

    with pytest.raises(ValueError, match="unknown dataset_id"):
        resolve_dataset_ids(catalog, "selected", ["missing"])
    with pytest.raises(ValueError, match="duplicate dataset_id"):
        resolve_dataset_ids(catalog, "selected", ["ag_news", "ag_news"])
    with pytest.raises(ValueError, match="disabled or experiment-ineligible"):
        resolve_dataset_ids(catalog, "selected", ["ms_marco"])


def test_all_errors_when_no_dataset_is_enabled_and_eligible(catalog_project: Path):
    for dataset_id in DATASET_IDS:
        descriptor_path = _descriptor_path(catalog_project, dataset_id)
        descriptor = _read_json(descriptor_path)
        descriptor["enabled"] = False
        _write_json(descriptor_path, descriptor)
    catalog = load_catalog(catalog_project)

    with pytest.raises(ValueError, match="no enabled and experiment-eligible"):
        resolve_dataset_ids(catalog, "all", [])
