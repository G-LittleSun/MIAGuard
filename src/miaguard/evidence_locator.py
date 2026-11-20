"""Conservative source localization from a request and retrieved evidence."""

from collections import defaultdict
from dataclasses import dataclass
import re

from .defense_contracts import Evidence


LOCATOR_VERSION = 'contiguous_trigrams_v1'
_MASK = re.compile(r'\[mask[_\s-]*\d+\]', re.IGNORECASE)
_TOKEN = re.compile(r"[a-z0-9]+")


@dataclass(frozen=True)
class Localization:
    status: str
    parent_ids: frozenset[str]
    matching_trigrams: dict[str, int]


def _trigrams(text: str) -> set[tuple[str, str, str]]:
    parts = _MASK.split(text.lower())
    result = set()
    for part in parts:
        tokens = _TOKEN.findall(part)
        result.update(zip(tokens, tokens[1:], tokens[2:]))
    return result


def locate_evidence(query: str, candidates: tuple[Evidence, ...]) -> Localization:
    query_grams = _trigrams(query)
    matches: dict[str, set[tuple[str, str, str]]] = defaultdict(set)
    for item in candidates:
        matches[item.parent_doc_id].update(query_grams & _trigrams(item.text))
    counts = {parent: len(grams) for parent, grams in matches.items()}
    possible = frozenset(parent for parent, count in counts.items() if count >= 2)
    if len(possible) == 1:
        return Localization('located', possible, counts)
    return Localization('ambiguous' if possible else 'unresolved', frozenset(), counts)
