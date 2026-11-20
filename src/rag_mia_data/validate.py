from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np

from .config import PipelineConfig
from .io_utils import read_jsonl, utc_now_iso, write_json_atomic
from .query_schema import load_query_schema


_DOCUMENT_FIELDS = {
    "doc_id", "source_doc_id", "source_dataset", "title", "text",
    "raw_text_sha256", "normalized_text_sha256", "char_length", "language",
    "duplicate_group_id", "membership_label", "target_split",
}


def _require_unique_ids(records: list[dict[str, Any]], name: str) -> set[str]:
    ids = [str(record.get("doc_id", "")) for record in records]
    if any(not value for value in ids):
        raise ValueError(f"{name} contains an empty document ID")
    if len(ids) != len(set(ids)):
        raise ValueError(f"{name} contains duplicate document IDs")
    return set(ids)


def validate_document_sets(
    members: list[dict[str, Any]],
    nonmembers: list[dict[str, Any]],
    targets: list[dict[str, Any]],
    expected_members: int,
    expected_targets: int,
    split_ratio: tuple[float, float, float] = (0.6, 0.2, 0.2),
) -> dict[str, Any]:
    member_ids = _require_unique_ids(members, "member set")
    nonmember_ids = _require_unique_ids(nonmembers, "nonmember set")
    intersection = member_ids & nonmember_ids
    if intersection:
        raise ValueError(f"Member/nonmember ID intersection is non-empty: {len(intersection)}")
    if len(members) != expected_members or len(nonmembers) != expected_members:
        raise ValueError(
            f"Expected {expected_members} documents per membership set, found "
            f"{len(members)} and {len(nonmembers)}"
        )
    if any(record.get("membership_label") != 1 for record in members):
        raise ValueError("Member set contains an incorrect membership_label")
    if any(record.get("membership_label") != 0 for record in nonmembers):
        raise ValueError("Nonmember set contains an incorrect membership_label")

    group_labels: defaultdict[str, set[int]] = defaultdict(set)
    for record in members + nonmembers:
        group_labels[str(record["duplicate_group_id"])].add(int(record["membership_label"]))
    leaking_groups = [group for group, labels in group_labels.items() if len(labels) > 1]
    if leaking_groups:
        raise ValueError(f"Duplicate groups cross membership: {len(leaking_groups)}")

    target_ids = _require_unique_ids(targets, "target set")
    if len(targets) != expected_targets:
        raise ValueError(f"Expected {expected_targets} targets, found {len(targets)}")
    all_ids = member_ids | nonmember_ids
    unresolved = target_ids - all_ids
    if unresolved:
        raise ValueError(f"Targets contain unresolved document IDs: {len(unresolved)}")

    source_labels = {
        str(record["doc_id"]): int(record["membership_label"])
        for record in members + nonmembers
    }
    for target in targets:
        if int(target["membership_label"]) != source_labels[str(target["doc_id"])]:
            raise ValueError("Target membership_label differs from its source document")

    split_by_group: defaultdict[str, set[str]] = defaultdict(set)
    for target in targets:
        split = target.get("target_split")
        if split not in {"train", "validation", "test"}:
            raise ValueError(f"Invalid target split: {split}")
        split_by_group[str(target["duplicate_group_id"])].add(str(split))
    if any(len(splits) > 1 for splits in split_by_group.values()):
        raise ValueError("A duplicate group crosses target splits")

    split_counts = Counter(str(target["target_split"]) for target in targets)
    if expected_targets:
        expected_split_counts = {
            "train": int(round(expected_targets * split_ratio[0])),
            "validation": int(round(expected_targets * split_ratio[1])),
        }
        expected_split_counts["test"] = expected_targets - sum(expected_split_counts.values())
        if dict(split_counts) != expected_split_counts:
            raise ValueError(
                f"Target split counts differ: {dict(split_counts)} vs {expected_split_counts}"
            )
        membership_counts = Counter(int(target["membership_label"]) for target in targets)
        if membership_counts[0] != membership_counts[1]:
            raise ValueError("Target membership labels are not balanced")
        for split in ("train", "validation", "test"):
            labels = Counter(
                int(target["membership_label"])
                for target in targets
                if target["target_split"] == split
            )
            if labels[0] != labels[1]:
                raise ValueError(f"Target labels are not balanced in split {split}")

    return {
        "member_count": len(members),
        "nonmember_count": len(nonmembers),
        "target_count": len(targets),
        "intersection_count": 0,
        "leaking_duplicate_groups": 0,
        "split_counts": dict(split_counts),
    }


def _validate_document_fields(records: list[dict[str, Any]]) -> None:
    for index, record in enumerate(records, start=1):
        missing = _DOCUMENT_FIELDS - record.keys()
        if missing:
            raise ValueError(f"Document record {index} is missing fields: {sorted(missing)}")
        if not str(record["text"]).strip():
            raise ValueError(f"Document record {index} has empty text")
        if int(record["char_length"]) != len(str(record["text"])):
            raise ValueError(f"Document record {index} has an incorrect char_length")


def _length_summary(records: list[dict[str, Any]]) -> dict[str, float | int]:
    if not records:
        return {"count": 0}
    values = np.asarray([int(record["char_length"]) for record in records])
    return {
        "count": len(records),
        "min": int(values.min()),
        "p50": float(np.percentile(values, 50)),
        "p95": float(np.percentile(values, 95)),
        "max": int(values.max()),
        "mean": float(values.mean()),
    }


def _render_quality_report(
    summary: dict[str, Any], member_lengths: dict[str, Any], nonmember_lengths: dict[str, Any]
) -> str:
    return "\n".join(
        [
            "# MIAFence 数据质量报告（任务书第 1～8 节）",
            "",
            f"- 生成时间：{summary['validated_at']}",
            f"- 候选文档：{summary['candidate_count']}",
            f"- 成员文档：{summary['member_count']}",
            f"- 非成员文档：{summary['nonmember_count']}",
            f"- 目标文档：{summary['target_count']}",
            f"- 目标 split：{summary['split_counts']}",
            f"- 文档 ID 交集：{summary['intersection_count']}",
            f"- 跨 membership 的重复组：{summary['leaking_duplicate_groups']}",
            f"- 成员长度分布：{member_lengths}",
            f"- 非成员长度分布：{nonmember_lengths}",
            "- benign 查询：0（第 9 节以后，按范围未执行）",
            "- Direct Ask 查询：0（第 9 节以后，按范围未执行）",
            "- S²MIA 查询：0（第 9 节以后，按范围未执行）",
            "- Mask-based 查询：0（第 9 节以后，按范围未执行）",
            "- IA 查询：0（第 9 节以后，按范围未执行）",
            "",
            "当前阶段仅完成统一查询 Schema，没有生成查询 JSONL。",
            "",
        ]
    )


def validate_outputs(config: PipelineConfig) -> dict[str, Any]:
    paths = {
        "candidates": config.documents_dir / "candidate_docs.jsonl",
        "members": config.documents_dir / "member_docs.jsonl",
        "nonmembers": config.documents_dir / "nonmember_docs.jsonl",
        "targets": config.documents_dir / "target_docs.jsonl",
    }
    for name, path in paths.items():
        if not path.is_file():
            raise FileNotFoundError(f"Missing {name} output: {path}")
    candidates = list(read_jsonl(paths["candidates"]))
    members = list(read_jsonl(paths["members"]))
    nonmembers = list(read_jsonl(paths["nonmembers"]))
    targets = list(read_jsonl(paths["targets"]))
    if len(candidates) != config.candidate_doc_count:
        raise ValueError(
            f"Expected {config.candidate_doc_count} candidates, found {len(candidates)}"
        )
    _validate_document_fields(candidates)
    expected_members = int(round(config.candidate_doc_count * config.member_ratio))
    summary = validate_document_sets(
        members,
        nonmembers,
        targets,
        expected_members=expected_members,
        expected_targets=config.target_doc_count,
        split_ratio=config.target_split_ratio,
    )
    summary["candidate_count"] = len(candidates)
    summary["validated_at"] = utc_now_iso()

    load_query_schema(config.schema_path)
    query_roots = [config.project_root / "data/processed/benign"] + [
        config.project_root / "data/processed/attacks" / attack
        for attack in ("direct_ask", "s2mia", "mask_based", "ia")
    ]
    for root in query_roots:
        root.mkdir(parents=True, exist_ok=True)
    query_files = [path for root in query_roots for path in root.rglob("*.jsonl")]
    if query_files:
        raise ValueError(f"Query JSONL files exist beyond the approved stop boundary: {query_files}")
    summary["query_jsonl_count"] = 0

    write_json_atomic(config.manifests_dir / "validation_manifest.json", summary)
    config.reports_dir.mkdir(parents=True, exist_ok=True)
    (config.reports_dir / "data_quality_report.md").write_text(
        _render_quality_report(summary, _length_summary(members), _length_summary(nonmembers)),
        encoding="utf-8",
        newline="\n",
    )
    return summary

