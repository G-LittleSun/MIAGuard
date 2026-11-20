from pathlib import Path

from rag_mia_data.config import load_config


def test_smoke_config_resolves_paths_from_project_root():
    cfg = load_config(Path("configs/smoke.yaml"))

    assert cfg.project_root == Path.cwd().resolve()
    assert cfg.dataset_path == (Path.cwd() / "DataSet/T2Ranking").resolve()
    assert cfg.candidate_doc_count == 200
    assert cfg.target_doc_count == 20
    assert cfg.seed == 20260713


def test_formal_config_has_exact_required_scale():
    cfg = load_config(Path("configs/formal.yaml"))

    assert (cfg.candidate_doc_count, cfg.target_doc_count) == (10_000, 1_000)
    assert cfg.member_ratio == 0.5
    assert cfg.target_split_ratio == (0.6, 0.2, 0.2)
