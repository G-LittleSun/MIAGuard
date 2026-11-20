from __future__ import annotations

import hashlib
from collections import Counter, defaultdict
from typing import Any

import numpy as np
from sklearn.cluster import MiniBatchKMeans
from sklearn.feature_extraction.text import TfidfVectorizer

from .config import PipelineConfig
from .deduplicate import assign_duplicate_groups
from .io_utils import read_jsonl, utc_now_iso, write_json_atomic, write_jsonl_atomic


def _stable_value(seed: int, namespace: str, value: str) -> int:
    digest = hashlib.sha256(f"{seed}:{namespace}:{value}".encode("utf-8")).digest()
    return int.from_bytes(digest, "big")


def _document_strata(
    docs: list[dict[str, Any]], seed: int, topic_clusters: int
) -> list[tuple[int, int]]:
    texts = [str(doc["text"]) for doc in docs]
    cluster_count = min(max(1, topic_clusters), len(texts))
    if cluster_count == 1:
        topics = np.zeros(len(texts), dtype=int)
    else:
        matrix = TfidfVectorizer(
            analyzer="char", ngram_range=(2, 3), max_features=4096, min_df=1
        ).fit_transform(texts)
        topics = MiniBatchKMeans(
            n_clusters=cluster_count,
            random_state=seed,
            n_init=3,
            batch_size=min(1024, len(texts)),
        ).fit_predict(matrix)

    lengths = np.asarray([int(doc["char_length"]) for doc in docs], dtype=float)
    boundaries = np.unique(np.quantile(lengths, [0.25, 0.5, 0.75]))
    length_bins = np.digitize(lengths, boundaries, right=True)
    return [(int(topic), int(length_bin)) for topic, length_bin in zip(topics, length_bins)]


def assign_membership(
    docs: list[dict[str, Any]],
    seed: int,
    member_ratio: float,
    topic_clusters: int,
) -> list[dict[str, Any]]:
    if not docs:
        raise ValueError("Cannot assign membership to an empty document list")
    ordered = sorted((dict(doc) for doc in docs), key=lambda doc: doc["doc_id"])
    if len({doc["doc_id"] for doc in ordered}) != len(ordered):
        raise ValueError("Document IDs must be unique")

    member_target = int(round(len(ordered) * member_ratio))
    capacities = {0: len(ordered) - member_target, 1: member_target}
    if min(capacities.values()) <= 0:
        raise ValueError("member_ratio leaves an empty membership set")

    strata = _document_strata(ordered, seed, topic_clusters)
    grouped: dict[str, list[int]] = defaultdict(list)
    for index, doc in enumerate(ordered):
        grouped[str(doc["duplicate_group_id"])].append(index)

    group_rows: list[tuple[str, list[int], tuple[int, int]]] = []
    for group_id, indexes in grouped.items():
        stratum_counts = Counter(strata[index] for index in indexes)
        group_stratum = min(
            stratum_counts,
            key=lambda item: (-stratum_counts[item], item),
        )
        group_rows.append((group_id, indexes, group_stratum))

    multi = [row for row in group_rows if len(row[1]) > 1]
    singles = [row for row in group_rows if len(row[1]) == 1]
    multi.sort(
        key=lambda row: (
            -len(row[1]),
            _stable_value(seed, "membership-group", row[0]),
        )
    )
    singles.sort(key=lambda row: _stable_value(seed, "membership-group", row[0]))

    counts = {0: 0, 1: 0}
    stratum_counts: dict[int, Counter[tuple[int, int]]] = {
        0: Counter(),
        1: Counter(),
    }
    assignments: dict[str, int] = {}

    def allocate(row: tuple[str, list[int], tuple[int, int]]) -> None:
        group_id, indexes, stratum = row
        size = len(indexes)
        allowed = [label for label in (0, 1) if counts[label] + size <= capacities[label]]
        if not allowed:
            raise ValueError(f"Duplicate group {group_id} cannot fit without crossing membership")
        preferred = _stable_value(seed, "membership-side", group_id) % 2
        label = min(
            allowed,
            key=lambda item: (
                stratum_counts[item][stratum],
                counts[item] / capacities[item],
                item != preferred,
            ),
        )
        assignments[group_id] = label
        counts[label] += size
        stratum_counts[label][stratum] += size

    for row in multi:
        allocate(row)
    for row in singles:
        allocate(row)

    if counts != capacities:
        raise ValueError(f"Could not reach exact membership counts: {counts} vs {capacities}")
    for doc in ordered:
        doc["membership_label"] = assignments[str(doc["duplicate_group_id"])]
    return ordered


def select_targets(
    docs: list[dict[str, Any]],
    target_count: int,
    seed: int,
    split_ratio: tuple[float, float, float],
) -> list[dict[str, Any]]:
    if target_count <= 0 or target_count % 2:
        raise ValueError("target_count must be a positive even integer")
    per_label = target_count // 2
    selected: list[dict[str, Any]] = []

    for label in (0, 1):
        groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for doc in docs:
            if doc.get("membership_label") == label:
                groups[str(doc["duplicate_group_id"])].append(doc)
        representatives = []
        for group_id, group_docs in groups.items():
            representative = min(
                group_docs,
                key=lambda doc: _stable_value(seed, "target-doc", str(doc["doc_id"])),
            )
            representatives.append((group_id, representative))
        representatives.sort(
            key=lambda item: _stable_value(seed, "target-group", item[0])
        )
        if len(representatives) < per_label:
            raise ValueError(
                f"Membership label {label} has {len(representatives)} groups; {per_label} required"
            )

        chosen = [dict(item[1]) for item in representatives[:per_label]]
        train_count = int(round(per_label * split_ratio[0]))
        validation_count = int(round(per_label * split_ratio[1]))
        test_count = per_label - train_count - validation_count
        if min(train_count, validation_count, test_count) < 0:
            raise ValueError("Invalid target split ratio")
        boundaries = (
            ("train", train_count),
            ("validation", validation_count),
            ("test", test_count),
        )
        offset = 0
        for split_name, split_count in boundaries:
            for doc in chosen[offset : offset + split_count]:
                doc["target_split"] = split_name
            offset += split_count
        selected.extend(chosen)

    return sorted(selected, key=lambda doc: doc["doc_id"])


def split_dataset(config: PipelineConfig) -> dict[str, Any]:
    candidate_path = config.documents_dir / "candidate_docs.jsonl"
    docs = list(read_jsonl(candidate_path))
    if len(docs) != config.candidate_doc_count:
        raise ValueError(
            f"Expected {config.candidate_doc_count} candidates, found {len(docs)}"
        )

    grouped, duplicate_stats = assign_duplicate_groups(
        docs,
        ngram=config.minhash_ngram,
        num_perm=config.minhash_num_perm,
        bands=config.minhash_bands,
        threshold=config.near_duplicate_threshold,
        seed=config.seed,
    )
    annotated = assign_membership(
        grouped,
        seed=config.seed,
        member_ratio=config.member_ratio,
        topic_clusters=config.topic_clusters,
    )
    targets = select_targets(
        annotated,
        target_count=config.target_doc_count,
        seed=config.seed,
        split_ratio=config.target_split_ratio,
    )
    target_splits = {doc["doc_id"]: doc["target_split"] for doc in targets}
    for doc in annotated:
        doc["target_split"] = target_splits.get(doc["doc_id"])
    targets = [dict(doc) for doc in annotated if doc["doc_id"] in target_splits]
    members = [dict(doc) for doc in annotated if doc["membership_label"] == 1]
    nonmembers = [dict(doc) for doc in annotated if doc["membership_label"] == 0]

    write_jsonl_atomic(candidate_path, annotated)
    write_jsonl_atomic(config.documents_dir / "member_docs.jsonl", members)
    write_jsonl_atomic(config.documents_dir / "nonmember_docs.jsonl", nonmembers)
    write_jsonl_atomic(config.documents_dir / "target_docs.jsonl", targets)

    membership_manifest = {
        "dataset": config.dataset_name,
        "config": config.config_path.relative_to(config.project_root).as_posix(),
        "seed": config.seed,
        "candidate_count": len(annotated),
        "member_count": len(members),
        "nonmember_count": len(nonmembers),
        "member_doc_ids": [doc["doc_id"] for doc in members],
        "nonmember_doc_ids": [doc["doc_id"] for doc in nonmembers],
        "duplicate_statistics": duplicate_stats,
        "created_at": utc_now_iso(),
    }
    split_manifest = {
        "seed": config.seed,
        "target_count": len(targets),
        "split_counts": dict(Counter(doc["target_split"] for doc in targets)),
        "membership_counts": dict(Counter(str(doc["membership_label"]) for doc in targets)),
        "target_doc_ids": {
            name: [doc["doc_id"] for doc in targets if doc["target_split"] == name]
            for name in ("train", "validation", "test")
        },
        "created_at": utc_now_iso(),
    }
    write_json_atomic(config.manifests_dir / "membership_manifest.json", membership_manifest)
    write_json_atomic(config.manifests_dir / "split_manifest.json", split_manifest)
    return {"membership": membership_manifest, "split": split_manifest}
