import json
from collections import OrderedDict
from pathlib import Path

import pytest

from rag_mia_data.dataset_catalog import CatalogEntry
from rag_mia_data.experiment import (
    AttackCount,
    ExperimentConfig,
    load_experiment_config,
    prepare_run,
)
from rag_mia_data.io_utils import read_jsonl, write_jsonl_atomic


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def _catalog_with_rows(root: Path, count: int) -> OrderedDict[str, CatalogEntry]:
    dataset_id = "fixture"
    source_dir = Path("DataSet/Fixture/teacher_snapshot")
    corpus_path = source_dir / "corpus.json"
    member_path = source_dir / "members.json"
    nonmember_path = source_dir / "nonmembers.json"
    members = [f"member {index}" for index in range(count)]
    nonmembers = [f"nonmember {index}" for index in range(count)]
    _write_json(root / corpus_path, members + nonmembers)
    _write_json(root / member_path, members)
    _write_json(root / nonmember_path, nonmembers)

    descriptor = {
        "dataset_id": dataset_id,
        "enabled": True,
        "experiment_eligible": True,
        "language": ["en"],
        "supported_attacks": ["masked_mia", "ia"],
        "files": {
            "processed_corpus": {
                "path": corpus_path.as_posix(),
                "record_count": count * 2,
            },
            "target_member": {
                "path": member_path.as_posix(),
                "record_count": count,
                "membership_label": 1,
            },
            "target_nonmember": {
                "path": nonmember_path.as_posix(),
                "record_count": count,
                "membership_label": 0,
            },
        },
    }
    normalized_dir = Path("data/processed/fixture/documents")
    config = {
        "adapter": "teacher_json_array",
        "normalized_documents_dir": normalized_dir.as_posix(),
    }
    entry = CatalogEntry(
        dataset_id=dataset_id,
        descriptor_path=root / "DataSet/Fixture/dataset.json",
        config_path=root / "configs/datasets/fixture.yaml",
        descriptor=descriptor,
        config=config,
    )
    member_rows = [
        {
            "doc_id": f"member-{index:04d}",
            "dataset_id": dataset_id,
            "text": text,
            "language": "en",
            "membership_label": 1,
            "source_partition": "target_member",
            "source_index": index,
            "metadata": {},
        }
        for index, text in reversed(list(enumerate(members)))
    ]
    nonmember_rows = [
        {
            "doc_id": f"nonmember-{index:04d}",
            "dataset_id": dataset_id,
            "text": text,
            "language": "en",
            "membership_label": 0,
            "source_partition": "target_nonmember",
            "source_index": count + index,
            "metadata": {},
        }
        for index, text in reversed(list(enumerate(nonmembers)))
    ]
    write_jsonl_atomic(root / normalized_dir / "member_docs.jsonl", member_rows)
    write_jsonl_atomic(root / normalized_dir / "nonmember_docs.jsonl", nonmember_rows)
    return OrderedDict([(dataset_id, entry)])


def _config(root: Path, profile: str, counts: dict[str, AttackCount]) -> ExperimentConfig:
    return ExperimentConfig(
        profile=profile,
        mode="single",
        include=("fixture",),
        attacks=tuple(counts),
        target_counts=counts,
        runs_dir=(root / "data/runs").resolve(),
    )


def test_experiment_profiles_have_exact_counts_and_default_selection():
    expected = {
        "smoke": {"masked_mia": (10, 10), "ia": (10, 10)},
        "pilot": {"masked_mia": (100, 100), "ia": (100, 100)},
        "formal": {"masked_mia": (1000, 1000), "ia": (200, 200)},
    }

    for profile, counts in expected.items():
        config = load_experiment_config(
            PROJECT_ROOT, PROJECT_ROOT / f"configs/experiments/{profile}.yaml"
        )
        assert config.profile == profile
        assert config.mode == "single"
        assert config.include == ("t2ranking",)
        assert config.attacks == ("masked_mia", "ia")
        assert {
            attack: (count.members, count.nonmembers)
            for attack, count in config.target_counts.items()
        } == counts
        assert config.runs_dir == (PROJECT_ROOT / "data/runs").resolve()


def test_prepare_single_smoke_selects_sorted_ten_plus_ten(tmp_path: Path):
    catalog = _catalog_with_rows(tmp_path, 12)
    counts = {
        "masked_mia": AttackCount(10, 10),
        "ia": AttackCount(10, 10),
    }

    manifest = prepare_run(tmp_path, catalog, _config(tmp_path, "smoke", counts), "smoke-1")

    rows = list(read_jsonl(tmp_path / "data/runs/smoke-1/fixture/target_docs.jsonl"))
    assert [row["doc_id"] for row in rows[:10]] == [
        f"member-{index:04d}" for index in range(10)
    ]
    assert [row["doc_id"] for row in rows[10:]] == [
        f"nonmember-{index:04d}" for index in range(10)
    ]
    assert manifest["status"] == "prepared"
    assert manifest["datasets"] == ["fixture"]
    assert not (tmp_path / "data/runs/smoke-1/summary.json").exists()
    assert not (tmp_path / "data/runs/smoke-1/fixture/masked_mia").exists()


def test_formal_ia_ids_are_prefixes_of_masked_ids(tmp_path: Path):
    catalog = _catalog_with_rows(tmp_path, 1000)
    config = _config(
        tmp_path,
        "formal",
        {
            "masked_mia": AttackCount(1000, 1000),
            "ia": AttackCount(200, 200),
        },
    )

    manifest = prepare_run(tmp_path, catalog, config, "formal-1")

    attacks = manifest["dataset_runs"]["fixture"]["attacks"]
    assert attacks["ia"]["member_ids"] == attacks["masked_mia"]["member_ids"][:200]
    assert attacks["ia"]["nonmember_ids"] == attacks["masked_mia"]["nonmember_ids"][:200]


def test_prepare_rejects_invalid_and_existing_run_ids(tmp_path: Path):
    catalog = _catalog_with_rows(tmp_path, 10)
    config = _config(tmp_path, "smoke", {"masked_mia": AttackCount(10, 10)})

    with pytest.raises(ValueError, match="run_id"):
        prepare_run(tmp_path, catalog, config, "../escape")
    assert not (tmp_path / "data/runs").exists()

    prepare_run(tmp_path, catalog, config, "same-run")
    before = (tmp_path / "data/runs/same-run/run_manifest.json").read_bytes()
    with pytest.raises(FileExistsError, match="same-run"):
        prepare_run(tmp_path, catalog, config, "same-run")
    assert (tmp_path / "data/runs/same-run/run_manifest.json").read_bytes() == before


def test_load_config_rejects_duplicate_attacks(tmp_path: Path, catalog_project: Path):
    config_path = catalog_project / "duplicate.yaml"
    config_path.write_text(
        """profile: smoke
dataset_selection:
  mode: single
  include: [t2ranking]
attacks: [masked_mia, masked_mia]
target_counts:
  masked_mia: {members: 10, nonmembers: 10}
runs_dir: data/runs
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="duplicate"):
        load_experiment_config(catalog_project, config_path)
