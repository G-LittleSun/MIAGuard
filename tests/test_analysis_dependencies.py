from pathlib import Path


def test_analysis_extra_declares_reproducible_stack() -> None:
    root = Path(__file__).resolve().parents[1]
    text = (root / "pyproject.toml").read_text(encoding="utf-8")

    assert "analysis = [" in text
    assert '"pandas>=2.3,<3"' in text
    assert '"scipy>=1.15,<2"' in text
    assert '"matplotlib>=3.10,<4"' in text
    assert '"pyarrow>=20,<22"' in text
