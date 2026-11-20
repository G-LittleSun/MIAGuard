from __future__ import annotations

import hashlib
from collections import defaultdict
from itertools import combinations
from typing import Any

from datasketch import MinHash


def char_ngrams(text: str, ngram: int) -> set[str]:
    if ngram <= 0:
        raise ValueError("ngram must be positive")
    if not text:
        return set()
    if len(text) <= ngram:
        return {text}
    return {text[index : index + ngram] for index in range(len(text) - ngram + 1)}


def _jaccard(left: set[str], right: set[str]) -> float:
    union = left | right
    return len(left & right) / len(union) if union else 1.0


class _UnionFind:
    def __init__(self, size: int) -> None:
        self.parent = list(range(size))

    def find(self, value: int) -> int:
        while self.parent[value] != value:
            self.parent[value] = self.parent[self.parent[value]]
            value = self.parent[value]
        return value

    def union(self, left: int, right: int) -> None:
        left_root = self.find(left)
        right_root = self.find(right)
        if left_root == right_root:
            return
        if left_root < right_root:
            self.parent[right_root] = left_root
        else:
            self.parent[left_root] = right_root


def assign_duplicate_groups(
    docs: list[dict[str, Any]],
    ngram: int,
    num_perm: int,
    bands: int,
    threshold: float,
    seed: int,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    if num_perm <= 0 or bands <= 0 or num_perm % bands:
        raise ValueError("num_perm must be positive and divisible by bands")
    if not 0.0 <= threshold <= 1.0:
        raise ValueError("threshold must be between 0 and 1")

    ordered = sorted((dict(doc) for doc in docs), key=lambda doc: doc["doc_id"])
    shingle_sets: list[set[str]] = []
    signatures = []
    for doc in ordered:
        shingles = char_ngrams(str(doc["text"]), ngram)
        shingle_sets.append(shingles)
        minhash = MinHash(num_perm=num_perm, seed=seed)
        if shingles:
            minhash.update_batch(item.encode("utf-8") for item in sorted(shingles))
        signatures.append(minhash.hashvalues)

    rows_per_band = num_perm // bands
    buckets: dict[tuple[int, bytes], list[int]] = defaultdict(list)
    for index, signature in enumerate(signatures):
        for band in range(bands):
            start = band * rows_per_band
            key = (band, signature[start : start + rows_per_band].tobytes())
            buckets[key].append(index)

    candidate_pairs: set[tuple[int, int]] = set()
    for indexes in buckets.values():
        if len(indexes) > 1:
            candidate_pairs.update(combinations(indexes, 2))

    union_find = _UnionFind(len(ordered))
    verified_pairs = 0
    for left, right in sorted(candidate_pairs):
        if _jaccard(shingle_sets[left], shingle_sets[right]) >= threshold:
            union_find.union(left, right)
            verified_pairs += 1

    components: dict[int, list[int]] = defaultdict(list)
    for index in range(len(ordered)):
        components[union_find.find(index)].append(index)

    for indexes in components.values():
        doc_ids = sorted(str(ordered[index]["doc_id"]) for index in indexes)
        digest = hashlib.sha256("\n".join(doc_ids).encode("utf-8")).hexdigest()[:12]
        group_id = f"dup_{digest}"
        for index in indexes:
            ordered[index]["duplicate_group_id"] = group_id

    group_sizes = [len(indexes) for indexes in components.values()]
    stats = {
        "candidate_pairs": len(candidate_pairs),
        "near_duplicate_pairs": verified_pairs,
        "duplicate_groups": len(group_sizes),
        "multi_document_groups": sum(size > 1 for size in group_sizes),
        "largest_group": max(group_sizes, default=0),
    }
    return ordered, stats
