"""Prepare D-dev-only source-pair review material; no V/T or attack outcomes."""
import hashlib
import itertools
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
T10 = ROOT / 'reports/defense_v1/T10'
PILOT = T10 / 'session_length_pilot_20261031_01'
OUT = T10 / 'event_pair_review_packet_20261104_01'


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def read(p):
    return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]


def write(p, data):
    p.write_text(''.join(json.dumps(x, ensure_ascii=False) + '\n' for x in data), encoding='utf-8')


def main():
    inputs = [PILOT / 'source_evidence.jsonl', PILOT / 'expanded_source_evidence.jsonl',
              T10 / 'dev_source_inventory_20261104_01/source_usage.jsonl']
    docs = {}
    for path in inputs[:2]:
        for r in read(path):
            if r['doc_id'] in docs and docs[r['doc_id']] != r['text']:
                raise ValueError('Conflicting source text')
            docs[r['doc_id']] = r['text']
    known = {r['doc_id'] for r in read(inputs[2])}
    if len(docs) != 31 or not set(docs) <= known:
        raise ValueError('Unexpected sources or missing development inventory')
    sources = [{'doc_id': k, 'text': docs[k], 'text_sha256': hashlib.sha256(docs[k].encode('utf-8')).hexdigest()}
               for k in sorted(docs)]
    pairs = [{'pair_id': 'pair_' + hashlib.sha256((a+'\n'+b).encode()).hexdigest()[:20],
              'left_doc_id': a, 'right_doc_id': b}
             for a, b in itertools.combinations(sorted(docs), 2)]
    if len(pairs) != 465 or len({p['pair_id'] for p in pairs}) != 465:
        raise ValueError('Unexpected pair count or collision')
    OUT.mkdir(exist_ok=False)
    write(OUT / 'sources.jsonl', sources)
    write(OUT / 'pairs.jsonl', pairs)
    manifest = {'status': 'review_pending', 'scope': '31 D-dev pilot sources only',
                'source_count': len(sources), 'pair_count': len(pairs),
                'input_sha256': {str(p.relative_to(ROOT)).replace('\\', '/'): sha(p) for p in inputs},
                'output_sha256': {p: sha(OUT / p) for p in ('sources.jsonl', 'pairs.jsonl')},
                'review_kind': 'llm_pre_review_requested', 'human_reviewed': False,
                'formal_effect_eligible': False,
                'limitations': ['Only these 31 D-dev sources; not all 216 known sources or other historical prompts.',
                                'No cross-partition or V/T source review; event association is not proven absent.',
                                'Model review will be advisory and does not establish human gold.']}
    (OUT / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'sources': len(sources), 'pairs': len(pairs), 'status': 'review_pending'}))


if __name__ == '__main__':
    main()
