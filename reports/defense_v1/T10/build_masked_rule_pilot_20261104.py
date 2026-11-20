"""Generate an unreviewed D-dev Masked rule pilot from previously reviewed sources."""
import hashlib
import json
from pathlib import Path

from miaguard.defense_dataset import _clean_article, draft_unique_masked_query

ROOT = Path(__file__).resolve().parents[3]
T10 = ROOT / 'reports/defense_v1/T10'
DATA = ROOT / 'data/defense_datasets/defense_access_v1_candidate06'
OUT = T10 / 'masked_rule_pilot_20261104_01'
VERSION = 't10d-masked-rule-pilot-20261104-01'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]


def write(path, rows):
    path.write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in rows), encoding='utf-8')


def main():
    source_ledger = T10 / 'review_attack_source_usage_20261102_01/source_usage.jsonl'
    source_manifest = T10 / 'review_attack_source_usage_20261102_01/manifest.json'
    dataset_manifest = DATA / 'manifest.json'
    dataset_docs = DATA / 'documents.jsonl'
    ledger = json.loads(source_manifest.read_text(encoding='utf-8'))
    manifest = json.loads(dataset_manifest.read_text(encoding='utf-8'))
    if ledger['output_sha256'] != sha(source_ledger) or manifest['artifact_sha256']['documents.jsonl'] != sha(dataset_docs):
        raise ValueError('Input hash mismatch')
    source_ids = sorted(r['doc_id'] for r in read(source_ledger))
    if len(source_ids) != 4 or len(set(source_ids)) != 4:
        raise ValueError('Unexpected review source IDs')
    docs = {r['doc_id']: r for r in read(dataset_docs) if r['doc_id'] in source_ids}
    if len(docs) != 4 or any(r['partition'] != 'D-dev' for r in docs.values()):
        raise ValueError('Missing source or wrong partition')
    requests, labels, sources, excluded = [], [], [], []
    for doc_id in source_ids:
        source = _clean_article(docs[doc_id]['text'])
        sources.append({'doc_id': doc_id, 'text': source, 'text_sha256': hashlib.sha256(source.encode('utf-8')).hexdigest()})
        try:
            query, answers = draft_unique_masked_query(source)
        except ValueError as exc:
            excluded.append({'doc_id': doc_id, 'reason': str(exc)})
            continue
        identity = hashlib.sha256((VERSION + ':' + doc_id).encode('utf-8')).hexdigest()[:24]
        request_id = 'mr_' + identity
        requests.append({'request_id': request_id, 'session_id': 'ms_' + identity, 'query': query})
        labels.append({'request_id': request_id, 'doc_id': doc_id, 'attack_type': 'masked_mia',
                       'answers': answers, 'review_status': 'pending', 'reviewed_by': None})
    OUT.mkdir(exist_ok=False)
    outputs = {'requests.jsonl': requests, 'labels.jsonl': labels, 'sources.jsonl': sources, 'excluded.jsonl': excluded}
    for name, values in outputs.items():
        write(OUT / name, values)
    paths = [source_manifest, source_ledger, dataset_manifest, dataset_docs,
             ROOT / 'src/miaguard/defense_dataset.py', Path(__file__).resolve()]
    result = {'version_id': VERSION, 'partition': 'D-dev', 'status': 'pending_agent_review',
              'formal_effect_eligible': False, 'human_gold_complete': False, 'replay_eligible': False,
              'source_count': len(source_ids), 'requests': len(requests), 'excluded': len(excluded),
              'selection': 'Four D-dev sources of previous attack review; no membership labels or outcomes used.',
              'input_sha256': {str(p.relative_to(ROOT)).replace('\\', '/'): sha(p) for p in paths},
              'output_sha256': {name: sha(OUT / name) for name in outputs},
              'limitations': ['Small nonrepresentative development pilot; not an attack effectiveness experiment.',
                              'Unique word is not necessarily recoverable or informative.',
                              'Does not establish historical or cross-partition independence.']}
    (OUT / 'manifest.json').write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps({'sources': len(source_ids), 'requests': len(requests), 'excluded': len(excluded)}))


if __name__ == '__main__':
    main()
