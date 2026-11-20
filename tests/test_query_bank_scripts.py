from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from scripts.query_bank import repair_ia_query_bank as repair_script
from scripts import evaluate_query_bank_judge_benchmark as evaluate_judge_script
from scripts import run_query_bank_judge_benchmark as run_judge_script


@pytest.mark.parametrize(
    "script",
    (
        "scripts/query_bank/build_query_bank.py",
        "scripts/query_bank/expand_benign_query_bank.py",
        "scripts/query_bank/repair_ia_query_bank.py",
        "scripts/query_bank/validate_query_bank.py",
        "scripts/query_bank/inspect_query_bank.py",
        "scripts/query_bank/build_threshold_split.py",
        "scripts/audit_query_bank_threshold_sessions.py",
        "scripts/run_query_bank_threshold_scoring.py",
        "scripts/calibrate_query_bank_attack_threshold.py",
        "scripts/validate_query_bank_attack_threshold.py",
        "scripts/compare_query_bank_attack_thresholds.py",
        "scripts/run_formal_query_bank_threshold_comparison.py",
        "scripts/run_query_bank_judge_benchmark.py",
        "scripts/run_remaining_v2_train_judge.py",
        "scripts/merge_v2_train_judge_runs.py",
        "scripts/evaluate_query_bank_judge_benchmark.py",
    ),
)
def test_query_bank_script_help(script: str) -> None:
    result = subprocess.run(
        [sys.executable, script, "--help"],
        cwd=Path.cwd(),
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "usage:" in result.stdout.casefold()


def test_repair_script_retries_from_checkpoint_until_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    attempts = 0
    delays: list[float] = []

    def fake_repair(*args, **kwargs):
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise RuntimeError(f"transient failure {attempts}")
        return {"status": "complete"}

    monkeypatch.setattr(repair_script, "repair_ia_query_bank", fake_repair)
    monkeypatch.setattr(repair_script.time, "sleep", delays.append)

    result = repair_script.main(
        [
            "--bank-id", "bank-1",
            "--dataset", "ag_news",
            "--attack-config", "attack.yaml",
            "--retry-on-failure",
            "--retry-delay-seconds", "2",
        ]
    )

    assert result == 0
    assert attempts == 3
    assert delays == [2.0, 2.0]


def test_progressive_judge_run_parser_excludes_test_partition() -> None:
    parser = run_judge_script.build_parser()
    partition_action = next(
        action for action in parser._actions if action.dest == "partition"
    )

    assert partition_action.choices == ("train", "validation")


def test_progressive_judge_run_parser_accepts_positive_smoke_limit() -> None:
    parser = run_judge_script.build_parser()

    args = parser.parse_args(
        [
            "--attack-config", "attack.yaml",
            "--judge-config", "judge.yaml",
            "--source-run-id", "run-1",
            "--query-bank-id", "bank-1",
            "--dataset", "ag_news",
            "--split", "split.json",
            "--partition", "train",
            "--output-root", "output",
            "--max-sessions", "1",
        ]
    )

    assert args.max_sessions == 1
    with pytest.raises(SystemExit):
        parser.parse_args(
            [
                "--attack-config", "attack.yaml",
                "--judge-config", "judge.yaml",
                "--source-run-id", "run-1",
                "--query-bank-id", "bank-1",
                "--dataset", "ag_news",
                "--split", "split.json",
                "--partition", "train",
                "--output-root", "output",
                "--max-sessions", "0",
            ]
        )


def _judge_run_base_args() -> list[str]:
    return [
        "--attack-config", "attack.yaml",
        "--judge-config", "judge.yaml",
        "--source-run-id", "run-1",
        "--query-bank-id", "bank-1",
        "--dataset", "ag_news",
        "--split", "split.json",
        "--partition", "train",
        "--output-root", "output",
    ]


def test_progressive_judge_run_parser_accepts_repeated_session_keys() -> None:
    parser = run_judge_script.build_parser()

    args = parser.parse_args(
        _judge_run_base_args()
        + ["--session-key", "session-a", "--session-key", "session-b"]
    )

    assert args.session_keys == ["session-a", "session-b"]


def test_progressive_judge_run_parser_rejects_limit_with_session_keys() -> None:
    parser = run_judge_script.build_parser()

    with pytest.raises(SystemExit):
        parser.parse_args(
            _judge_run_base_args()
            + ["--max-sessions", "1", "--session-key", "session-a"]
        )


def test_judge_evaluation_refuses_to_overwrite_existing_report(tmp_path: Path) -> None:
    output = tmp_path / "report.json"
    output.write_text("{}\n", encoding="utf-8")

    with pytest.raises(FileExistsError, match="already exists"):
        evaluate_judge_script.main(
            ["--run-dir", str(tmp_path / "run"), "--output", str(output)]
        )
