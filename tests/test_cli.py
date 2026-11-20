import json
from collections import OrderedDict
from types import SimpleNamespace

import rag_mia_data.cli as cli
from rag_mia_data.cli import main


def test_cli_returns_nonzero_and_clear_error_for_missing_config(tmp_path, capsys):
    exit_code = main(["inspect", "--config", str(tmp_path / "missing.yaml")])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "ERROR:" in captured.err


def test_cli_dataset_normalize_dispatches_selected_datasets(
    tmp_path, monkeypatch, capsys
):
    entries = OrderedDict(
        [
            ("first", SimpleNamespace(dataset_id="first")),
            ("second", SimpleNamespace(dataset_id="second")),
        ]
    )
    calls = []
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli, "load_catalog", lambda root: entries, raising=False)
    monkeypatch.setattr(
        cli,
        "resolve_dataset_ids",
        lambda catalog, mode, include: ["first", "second"],
        raising=False,
    )
    monkeypatch.setattr(
        cli,
        "normalize_dataset",
        lambda entry, root: calls.append((entry.dataset_id, root)) or {"member_count": 1},
        raising=False,
    )

    exit_code = main(["dataset-normalize", "--mode", "selected", "--include", "first"])

    assert exit_code == 0
    assert calls == [("first", tmp_path.resolve()), ("second", tmp_path.resolve())]
    assert json.loads(capsys.readouterr().out) == {
        "first": {"member_count": 1},
        "second": {"member_count": 1},
    }
