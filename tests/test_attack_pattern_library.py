from pathlib import Path

import json
import yaml
from jsonschema import Draft202012Validator

from miaguard.attack_pattern_library import AttackPatternLibrary


def test_attack_pattern_library_loads_four_enabled_patterns() -> None:
    root = Path(__file__).resolve().parents[1]

    library = AttackPatternLibrary.load(root / "attack_pattern_library/manifest.yaml")

    assert library.name == "MIAGuard Attack Pattern Library"
    assert library.version == "1.7.0"
    assert set(library.patterns) == {
        "direct_rag_mia",
        "s2_mia",
        "masked_mia",
        "ia",
    }
    assert "untrusted" in library.protocol().casefold()
    ia = library.read_patterns(["ia"])["ia"]
    assert library.patterns["ia"].version == "1.6.0"
    assert "single ordinary factual question" in ia
    assert "Yes/No/Unknown" in ia
    assert "at least three" in ia
    assert "NORMAL_FOLLOW_UP_CONVERSATION" in ia


def test_attack_pattern_manifest_matches_schema() -> None:
    root = Path(__file__).resolve().parents[1]
    manifest = yaml.safe_load(
        (root / "attack_pattern_library/manifest.yaml").read_text(encoding="utf-8")
    )
    schema = json.loads(
        (root / "schemas/attack_pattern_manifest.schema.json").read_text(
            encoding="utf-8"
        )
    )

    Draft202012Validator(schema).validate(manifest)
