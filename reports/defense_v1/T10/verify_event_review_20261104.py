"""Validate external model review identities and verbatim evidence, not semantics."""
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
T10 = ROOT / 'reports/defense_v1/T10'
PACKET = T10 / 'event_pair_review_packet_20261104_01'
REVIEW = T10 / 'external_review/event_pairs_deepseek-v4.1-flash_20261104_01'
OUT = T10 / 'event_review_validation_20261104.json'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows(path):
    raw = path.read_bytes()
    if raw.startswith(b'\xef\xbb\xbf'):
        raise ValueError(f'Unexpected BOM: {path}')
    return [json.loads(x) for x in raw.decode('utf-8').splitlines() if x.strip()]


def main():
    m = json.loads((REVIEW / 'review_manifest.json').read_text(encoding='utf-8'))
    packet_m = json.loads((PACKET / 'manifest.json').read_text(encoding='utf-8'))
    expected_inputs = {f'packet/{name}': PACKET / name for name in
                       ('manifest.json', 'sources.jsonl', 'pairs.jsonl', 'REVIEW_GUIDE_ZH.md', 'validation.json')}
    expected_inputs.update({f'upstream/{name}': T10 / name for name in (
        'session_length_pilot_20261031_01/source_evidence.jsonl',
        'session_length_pilot_20261031_01/expanded_source_evidence.jsonl',
        'dev_source_inventory_20261104_01/source_usage.jsonl')})
    errors = []
    if set(m['input_sha256']) != set(expected_inputs):
        errors.append('input identity inventory mismatch')
    for name, path in expected_inputs.items():
        if m['input_sha256'].get(name) != sha(path):
            errors.append('input hash: ' + name)
    for name in ('pair_reviews.jsonl', 'review_summary.md'):
        if m['output_files'][name]['sha256'] != sha(REVIEW / name):
            errors.append('output hash: ' + name)
    for name, digest in packet_m['output_sha256'].items():
        if sha(PACKET / name) != digest:
            errors.append('packet hash: ' + name)
    if packet_m['guide_sha256'] != sha(PACKET / 'REVIEW_GUIDE_ZH.md'):
        errors.append('guide hash')
    sources = {r['doc_id']: r['text'] for r in rows(PACKET / 'sources.jsonl')}
    pairs, reviews = rows(PACKET / 'pairs.jsonl'), rows(REVIEW / 'pair_reviews.jsonl')
    required = {'pair_id', 'left_doc_id', 'right_doc_id', 'relation', 'reason',
                'left_evidence', 'right_evidence', 'confidence'}
    if len(pairs) != 465 or len(reviews) != 465 or len(sources) != 31:
        errors.append('counts')
    if len({r['pair_id'] for r in reviews}) != len(reviews):
        errors.append('duplicate pair ID')
    for p, r in zip(pairs, reviews):
        if set(r) != required:
            errors.append('field set: ' + str(r.get('pair_id')))
        if any(r.get(k) != p[k] for k in ('pair_id', 'left_doc_id', 'right_doc_id')):
            errors.append('identity/order: ' + str(r.get('pair_id')))
        if r.get('relation') not in {'same_event', 'related_event', 'shared_entity_or_topic', 'unrelated', 'uncertain'}:
            errors.append('relation: ' + str(r.get('pair_id')))
        if r.get('confidence') not in {'high', 'medium', 'low'} or not isinstance(r.get('reason'), str) or not r['reason'].strip():
            errors.append('confidence/reason: ' + str(r.get('pair_id')))
        for side in ('left', 'right'):
            evidence = r.get(side + '_evidence')
            if not isinstance(evidence, str) or evidence not in sources.get(p[side + '_doc_id'], ''):
                errors.append('evidence: ' + str(r.get('pair_id')) + ':' + side)
    counts = dict(Counter(r['relation'] for r in reviews))
    counts_full = {x: counts.get(x, 0) for x in ('same_event', 'related_event', 'shared_entity_or_topic', 'unrelated', 'uncertain')}
    if counts_full != m['decision_counts']:
        errors.append('decision counts')
    if m['status'] != 'complete' or m['partial'] or m['human_reviewed'] or m['formal_effect_eligible']:
        errors.append('status or eligibility')
    result = {'status': 'passed' if not errors else 'failed', 'errors': errors,
              'sources': len(sources), 'pairs': len(pairs), 'reviews': len(reviews),
              'decision_counts': counts_full, 'review_manifest_sha256': sha(REVIEW / 'review_manifest.json'),
              'review_sha256': sha(REVIEW / 'pair_reviews.jsonl'),
              'limits': ['Structural verification and verbatim evidence only; not semantic validation.',
                         'Actual runtime model identity is not independently verifiable from these artifacts.']}
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False))
    if errors:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
