from __future__ import annotations

import hashlib
from array import array
from collections import defaultdict
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from .config import PipelineConfig
from .io_utils import sha256_file, utc_now_iso, write_json_atomic
from .preprocess import normalize_text


_EXPECTED_FIELDS = {
    "collection.tsv": ["pid", "text"],
    "queries.train.tsv": ["qid", "text"],
    "queries.dev.tsv": ["qid", "text"],
    "queries.test.tsv": ["qid", "text"],
    "qrels.train.tsv": ["qid", "-", "pid", "rel"],
    "qrels.dev.tsv": ["qid", "-", "pid", "rel"],
    "qrels.retrieval.train.tsv": ["qid", "pid"],
    "qrels.retrieval.dev.tsv": ["qid", "pid"],
    "train.bm25.tsv": ["qid", "pid", "index"],
    "train.mined.tsv": ["qid", "pid", "index", "score"],
}


def _id_key(value: str) -> tuple[int, int | str]:
    stripped = value.strip()
    return (0, int(stripped)) if stripped.isdecimal() else (1, stripped)


def _value_type(value: str) -> int:
    if not value:
        return 0
    try:
        int(value)
        return 1
    except ValueError:
        try:
            float(value)
            return 2
        except ValueError:
            return 3


def _profile_tsv(
    path: Path,
    project_root: Path,
    callback: Callable[[dict[str, str]], None] | None = None,
) -> dict[str, Any]:
    digest = hashlib.sha256()
    samples: list[dict[str, str]] = []
    record_count = 0
    with path.open("rb") as handle:
        header_bytes = handle.readline()
        if not header_bytes:
            raise ValueError(f"Empty TSV file: {path}")
        digest.update(header_bytes)
        header_line = header_bytes.decode("utf-8").rstrip("\r\n")
        fields = header_line.split("\t")
        if any(not field for field in fields) or len(fields) != len(set(fields)):
            raise ValueError(f"Invalid TSV header: {path}")
        expected = _EXPECTED_FIELDS.get(path.name)
        if expected is not None and fields != expected:
            raise ValueError(f"Unexpected fields for {path.name}: {fields}; expected {expected}")
        type_ranks = {field: 0 for field in fields}

        for line_number, raw_line in enumerate(handle, start=2):
            digest.update(raw_line)
            line = raw_line.decode("utf-8").rstrip("\r\n")
            values = line.split("\t", len(fields) - 1)
            if len(values) != len(fields):
                raise ValueError(f"Wrong column count at {path}:{line_number}")
            row = dict(zip(fields, values))
            record_count += 1
            for field, value in row.items():
                type_ranks[field] = max(type_ranks[field], _value_type(value))
            if len(samples) < 5:
                samples.append({field: value[:200] for field, value in row.items()})
            if callback is not None:
                callback(row)

    type_names = {0: "unknown", 1: "integer", 2: "number", 3: "string"}
    stat = path.stat()
    return {
        "path": path.relative_to(project_root).as_posix(),
        "size_bytes": stat.st_size,
        "extension": path.suffix.lower(),
        "modified_at": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
        "sha256": digest.hexdigest(),
        "encoding": "utf-8",
        "delimiter": "tab",
        "compression": "none",
        "reading_method": "streaming binary lines with strict UTF-8 decoding",
        "fields": fields,
        "field_types": {field: type_names[type_ranks[field]] for field in fields},
        "record_count": record_count,
        "samples": samples,
    }


def _profile_text(path: Path, project_root: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    stat = path.stat()
    return {
        "path": path.relative_to(project_root).as_posix(),
        "size_bytes": stat.st_size,
        "extension": path.suffix.lower(),
        "modified_at": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
        "sha256": sha256_file(path),
        "encoding": "utf-8",
        "delimiter": None,
        "compression": "none",
        "reading_method": "UTF-8 text",
        "fields": [],
        "field_types": {},
        "record_count": len(text.splitlines()),
        "samples": [text[:500]],
    }


def _length_distribution(lengths: array) -> dict[str, float | int]:
    if not lengths:
        return {name: 0 for name in ("count", "min", "p25", "p50", "p75", "p95", "p99", "max", "mean")}
    values = np.frombuffer(lengths, dtype=np.uint32)
    percentiles = np.percentile(values, [25, 50, 75, 95, 99])
    return {
        "count": int(values.size),
        "min": int(values.min()),
        "p25": float(percentiles[0]),
        "p50": float(percentiles[1]),
        "p75": float(percentiles[2]),
        "p95": float(percentiles[3]),
        "p99": float(percentiles[4]),
        "max": int(values.max()),
        "mean": float(values.mean()),
    }


def _render_report(profile: dict[str, Any]) -> str:
    corpus = profile["corpus"]
    relations = profile["relations"]
    lines = [
        "# T2Ranking 本地源数据探查报告",
        "",
        f"- 探查时间：{profile['inspected_at']}",
        "- 数据集：T2Ranking",
        "- 本地路径：`DataSet/T2Ranking`",
        "- 来源：unknown（本地文件无法确认）",
        "- 许可：unknown（本地文件无法确认）",
        "- revision：unknown（本地文件无法确认）",
        f"- 原始数据被流水线修改：{'是' if profile['raw_data_modified'] else '否'}",
        "",
        "## 文件清单",
        "",
        "| 文件 | 字节数 | 记录数 | 字段 | SHA-256 |",
        "|---|---:|---:|---|---|",
    ]
    for item in profile["files"]:
        fields = ", ".join(item["fields"]) if item["fields"] else "-"
        lines.append(
            f"| `{item['path']}` | {item['size_bytes']} | {item['record_count']} | "
            f"{fields} | `{item['sha256']}` |"
        )
    lines.extend(
        [
            "",
            "## 语料质量",
            "",
            f"- 记录数：{corpus['record_count']}",
            f"- 空 ID：{corpus['empty_ids']}",
            f"- 重复 ID：{corpus['duplicate_ids']}",
            f"- 空正文：{corpus['empty_texts']}",
            f"- 规范化文本精确重复：{corpus['exact_duplicate_texts']}（比例 {corpus['exact_duplicate_ratio']:.6f}）",
            f"- 字符长度分布：`{corpus['char_length_distribution']}`",
            "",
            "## 查询与 qrels 关联",
            "",
            f"- 查询数：{relations['query_count']}",
            f"- qrels 记录数：{relations['qrels_record_count']}",
            f"- 未知 query ID 记录：{relations['qrels_unknown_query_ids']}",
            f"- 未知 document ID 记录：{relations['qrels_unknown_document_ids']}",
            f"- 没有相关标注的查询：{relations['queries_without_relevance']}",
            "",
            "## 安全样例",
            "",
        ]
    )
    for item in profile["files"]:
        if item["samples"]:
            lines.append(f"### {item['path']}")
            lines.append("")
            for sample in item["samples"][:3]:
                lines.append(f"- `{sample}`")
            lines.append("")
    lines.append("流水线仅以只读方式访问 `DataSet/T2Ranking`，未向该目录写入文件。")
    lines.append("")
    return "\n".join(lines)


def inspect_dataset(config: PipelineConfig) -> dict[str, Any]:
    if not config.dataset_path.is_dir():
        raise FileNotFoundError(f"Missing dataset directory: {config.dataset_path}")
    source_files = sorted(path for path in config.dataset_path.rglob("*") if path.is_file())
    if not source_files:
        raise ValueError(f"Dataset directory contains no files: {config.dataset_path}")
    before = {path: (path.stat().st_size, path.stat().st_mtime_ns) for path in source_files}

    document_ids: set[tuple[int, int | str]] = set()
    normalized_text_digests: set[bytes] = set()
    lengths = array("I")
    corpus_counts: defaultdict[str, int] = defaultdict(int)
    query_ids: set[tuple[int, int | str]] = set()
    related_query_ids: set[tuple[int, int | str]] = set()
    relation_counts: defaultdict[str, int] = defaultdict(int)
    profiles: dict[Path, dict[str, Any]] = {}

    def on_collection(row: dict[str, str]) -> None:
        pid = row["pid"].strip()
        text = row["text"]
        if not pid:
            corpus_counts["empty_ids"] += 1
        else:
            key = _id_key(pid)
            if key in document_ids:
                corpus_counts["duplicate_ids"] += 1
            document_ids.add(key)
        if not text.strip():
            corpus_counts["empty_texts"] += 1
        normalized = normalize_text(text)
        lengths.append(len(normalized))
        digest = hashlib.sha256(normalized.encode("utf-8")).digest()[:16]
        if digest in normalized_text_digests:
            corpus_counts["exact_duplicate_texts"] += 1
        normalized_text_digests.add(digest)

    collection_path = config.dataset_path / "collection.tsv"
    if not collection_path.is_file():
        raise FileNotFoundError(f"Missing corpus file: {collection_path}")
    profiles[collection_path] = _profile_tsv(collection_path, config.project_root, on_collection)

    query_paths = sorted(config.dataset_path.glob("queries.*.tsv"))
    for path in query_paths:
        def on_query(row: dict[str, str]) -> None:
            query_ids.add(_id_key(row["qid"]))
        profiles[path] = _profile_tsv(path, config.project_root, on_query)

    qrels_paths = sorted(config.dataset_path.glob("qrels*.tsv"))
    for path in qrels_paths:
        is_retrieval = ".retrieval." in path.name

        def on_qrel(row: dict[str, str], retrieval: bool = is_retrieval) -> None:
            relation_counts["qrels_record_count"] += 1
            qid = _id_key(row["qid"])
            pid = _id_key(row["pid"])
            if qid not in query_ids:
                relation_counts["qrels_unknown_query_ids"] += 1
            if pid not in document_ids:
                relation_counts["qrels_unknown_document_ids"] += 1
            relevant = retrieval or int(row.get("rel", "0") or 0) > 0
            if qid in query_ids and relevant:
                related_query_ids.add(qid)

        profiles[path] = _profile_tsv(path, config.project_root, on_qrel)

    for path in source_files:
        if path in profiles:
            continue
        profiles[path] = (
            _profile_tsv(path, config.project_root)
            if path.suffix.lower() == ".tsv"
            else _profile_text(path, config.project_root)
        )

    after = {path: (path.stat().st_size, path.stat().st_mtime_ns) for path in source_files}
    files = [profiles[path] for path in sorted(profiles)]
    record_count = profiles[collection_path]["record_count"]
    exact_duplicates = corpus_counts["exact_duplicate_texts"]
    profile = {
        "dataset_name": config.dataset_name,
        "dataset_path": config.dataset_path.relative_to(config.project_root).as_posix(),
        "source": "unknown",
        "license": "unknown",
        "revision": "unknown",
        "inspected_at": utc_now_iso(),
        "files": files,
        "components": {
            "corpus": collection_path.is_file(),
            "queries": bool(query_paths),
            "qrels_or_relevance": bool(qrels_paths),
        },
        "corpus": {
            "record_count": record_count,
            "empty_ids": corpus_counts["empty_ids"],
            "duplicate_ids": corpus_counts["duplicate_ids"],
            "empty_texts": corpus_counts["empty_texts"],
            "exact_duplicate_texts": exact_duplicates,
            "exact_duplicate_ratio": exact_duplicates / record_count if record_count else 0.0,
            "char_length_distribution": _length_distribution(lengths),
        },
        "relations": {
            "query_count": len(query_ids),
            "qrels_record_count": relation_counts["qrels_record_count"],
            "qrels_unknown_query_ids": relation_counts["qrels_unknown_query_ids"],
            "qrels_unknown_document_ids": relation_counts["qrels_unknown_document_ids"],
            "queries_without_relevance": len(query_ids - related_query_ids),
        },
        "raw_data_modified": before != after,
        "pipeline_statement": "The pipeline did not modify the raw dataset.",
    }
    if profile["raw_data_modified"]:
        raise RuntimeError("Raw dataset metadata changed during inspection")

    source_manifest = {
        key: profile[key]
        for key in (
            "dataset_name", "dataset_path", "source", "license", "revision",
            "inspected_at", "files", "raw_data_modified", "pipeline_statement"
        )
    }
    write_json_atomic(config.manifests_dir / "source_dataset_manifest.json", source_manifest)
    write_json_atomic(config.reports_dir / "data_profile.json", profile)
    report_path = config.reports_dir / "source_dataset_profile.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(_render_report(profile), encoding="utf-8", newline="\n")
    return profile
