"""Try two previously suggested words, without claiming semantic validity."""
import hashlib
import json
from pathlib import Path

from miaguard.defense_dataset import draft_masked_query_for_word, masked_word_candidates

ROOT = Path(__file__).resolve().parents[3]
T10 = ROOT / 'reports/defense_v1/T10'
PREV = T10 / 'masked_rule_pilot_20261104_01'
OUT = T10 / 'masked_selected_pilot_20261104_01'
VERSION = 't10d-masked-selected-20261104-01'
CHOICES = {'ag_news_defense_00009018': 'sparkling', 'ag_news_teacher_00001030': 'Belichick'}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return [json.loads(x) for x in path.read_text(encoding='utf-8').splitlines() if x.strip()]


def main():
    prior_manifest = json.loads((PREV / 'manifest.json').read_text(encoding='utf-8'))
    for name, expected in prior_manifest['output_sha256'].items():
        if sha(PREV / name) != expected:
            raise ValueError('Prior output hash mismatch')
    sources = {r['doc_id']: r for r in read(PREV / 'sources.jsonl')}
    prior = {r['doc_id']: r['request_id'] for r in read(PREV / 'labels.jsonl')}
    if len(sources) != 4 or not set(CHOICES) <= sources.keys():
        raise ValueError('Unexpected sources')
    requests, offline, options = [], [], []
    for doc_id, source in sorted(sources.items()):
        text = source['text']
        options.append({'doc_id': doc_id, 'source_text_sha256': source['text_sha256'],
                        'candidates': masked_word_candidates(text),
                        'selected_word': CHOICES.get(doc_id)})
        if doc_id not in CHOICES:
            continue
        query, answer = draft_masked_query_for_word(text, CHOICES[doc_id])
        ident = hashlib.sha256((VERSION + ':' + doc_id).encode()).hexdigest()[:24]
        rid = 'mr_' + ident
        requests.append({'request_id': rid, 'session_id': 'ms_' + ident, 'query': query})
        offline.append({'request_id': rid, 'doc_id': doc_id, 'attack_type': 'masked_mia',
                        'answers': answer, 'source_request_id': prior[doc_id],
                        'review_status': 'pending', 'reviewed_by': None})
    OUT.mkdir(exist_ok=False)
    outputs = {'requests.jsonl': requests, 'labels.jsonl': offline, 'candidate_words.jsonl': options}
    for name, values in outputs.items():
        (OUT / name).write_text(''.join(json.dumps(x, ensure_ascii=False) + '\n' for x in values), encoding='utf-8')
    inputs = [PREV / 'manifest.json', PREV / 'sources.jsonl', PREV / 'labels.jsonl',
              T10 / 'REVIEW_TRIAGE_REV2_20261030_ZH.md', ROOT / 'src/miaguard/defense_dataset.py', Path(__file__).resolve()]
    result = {'version_id': VERSION, 'partition': 'D-dev', 'status': 'pending_content_review',
              'formal_effect_eligible': False, 'human_gold_complete': False, 'replay_eligible': False,
              'source_count': 4, 'drafts': 2, 'unselected_sources': 2,
              'input_sha256': {str(p.relative_to(ROOT)).replace('\\', '/'): sha(p) for p in inputs},
              'output_sha256': {name: sha(OUT / name) for name in outputs},
              'selection_basis': 'Previously suggested review words, selected only to test explicit selection; semantic validity not established.',
              'limitations': ['Two sources have no selected word; not all sources can necessarily yield valid cloze questions.',
                              'Adjective synonyms and multiple plausible names may prevent unique recovery.',
                              'Pending agent review, not human gold or formal replay.']}
    (OUT / 'manifest.json').write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps({'sources': 4, 'drafts': len(requests), 'unselected': 2}))


if __name__ == '__main__':
    main()
