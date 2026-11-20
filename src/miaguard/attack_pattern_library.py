from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class AttackPattern:
    pattern_id: str
    name: str
    version: str
    summary: str
    entrypoint: Path
    required_context: tuple[str, ...]
    optional_context: tuple[str, ...]


class AttackPatternLibrary:
    def __init__(
        self,
        *,
        root: Path,
        name: str,
        version: str,
        protocol_path: Path,
        patterns: dict[str, AttackPattern],
        manifest: dict[str, Any],
    ) -> None:
        self.root = root
        self.name = name
        self.version = version
        self.protocol_path = protocol_path
        self.patterns = patterns
        self.manifest = manifest

    @classmethod
    def load(cls, manifest_path: str | Path) -> "AttackPatternLibrary":
        path = Path(manifest_path).resolve()
        with path.open("r", encoding="utf-8") as handle:
            raw = yaml.safe_load(handle)
        if not isinstance(raw, dict):
            raise ValueError("Attack pattern manifest must be a YAML mapping")
        pack = raw.get("library")
        entries = raw.get("patterns")
        if not isinstance(pack, dict) or not isinstance(entries, list):
            raise ValueError("Manifest requires library and patterns sections")

        root = path.parent
        protocol_path = cls._safe_file(root, str(pack.get("judge_protocol", "")))
        patterns: dict[str, AttackPattern] = {}
        for entry in entries:
            if not isinstance(entry, dict):
                raise ValueError("Each attack pattern entry must be a mapping")
            if not bool(entry.get("enabled", True)):
                continue
            pattern_id = str(entry.get("id", ""))
            if not re.fullmatch(r"[a-z0-9_]+", pattern_id):
                raise ValueError(f"Invalid attack pattern id: {pattern_id!r}")
            if pattern_id in patterns:
                raise ValueError(f"Duplicate attack pattern id: {pattern_id}")
            entrypoint = cls._safe_file(root, str(entry.get("entrypoint", "")))
            summary = str(entry.get("summary", "")).strip()
            if not summary:
                raise ValueError(f"Attack pattern summary is blank: {pattern_id}")
            patterns[pattern_id] = AttackPattern(
                pattern_id=pattern_id,
                name=str(entry.get("name", pattern_id)).strip(),
                version=str(entry.get("version", "")).strip(),
                summary=summary,
                entrypoint=entrypoint,
                required_context=tuple(str(value) for value in entry.get("required_context", [])),
                optional_context=tuple(str(value) for value in entry.get("optional_context", [])),
            )
        if not patterns:
            raise ValueError("Attack pattern library has no enabled patterns")
        return cls(
            root=root,
            name=str(pack.get("name", "")).strip(),
            version=str(pack.get("version", "")).strip(),
            protocol_path=protocol_path,
            patterns=patterns,
            manifest=raw,
        )

    @staticmethod
    def _safe_file(root: Path, relative_path: str) -> Path:
        if not relative_path.strip():
            raise ValueError("Attack pattern file path must not be blank")
        path = (root / relative_path).resolve()
        if not path.is_relative_to(root):
            raise ValueError(f"Attack pattern file escapes library root: {relative_path}")
        if not path.is_file():
            raise FileNotFoundError(f"Attack pattern file does not exist: {path}")
        return path

    def index(self) -> list[dict[str, Any]]:
        return [
            {
                "id": pattern.pattern_id,
                "name": pattern.name,
                "version": pattern.version,
                "summary": pattern.summary,
                "required_context": list(pattern.required_context),
                "optional_context": list(pattern.optional_context),
            }
            for pattern in self.patterns.values()
        ]

    def protocol(self) -> str:
        return self.protocol_path.read_text(encoding="utf-8").strip()

    def read_patterns(self, pattern_ids: list[str]) -> dict[str, str]:
        unknown = [pattern_id for pattern_id in pattern_ids if pattern_id not in self.patterns]
        if unknown:
            raise KeyError(f"Unknown attack pattern ids: {unknown}")
        return {
            pattern_id: self.patterns[pattern_id].entrypoint.read_text(
                encoding="utf-8"
            ).strip()
            for pattern_id in pattern_ids
        }


__all__ = ["AttackPattern", "AttackPatternLibrary"]
