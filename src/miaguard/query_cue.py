"""Experimental observable query cues for an additional defensive policy."""

import re


QUERY_CUE_VERSION = 'query_cue_v1'
_QUOTATION = re.compile(r'"([^"\n]+)"')
_WORDS = re.compile(r'[A-Za-z0-9]+')
_PRESENCE = re.compile(r'\b(?:appear|present|found|exists?|contain(?:s|ed)?)\b', re.I)
_CONTEXT = re.compile(r'\b(?:context|retrieval|database|corpus)\b', re.I)
_MASK = re.compile(r'\[mask[_\s-]*(\d+)\]', re.I)
_RECOVERY = re.compile(r'\b(?:recover|recovery|original)\b', re.I)


def query_cues(query: str) -> tuple[str, ...]:
    cues = []
    if (_PRESENCE.search(query) and _CONTEXT.search(query)
            and any(len(_WORDS.findall(match)) >= 12 for match in _QUOTATION.findall(query))):
        cues.append('quoted_context_check')
    if len(set(_MASK.findall(query))) >= 3 and _RECOVERY.search(query):
        cues.append('masked_recovery')
    return tuple(cues)
