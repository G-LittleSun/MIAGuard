"""Check the recorded E00 source against candidate06 historical inputs and corpus.

This checks identities and full-text signatures only; it does not establish event
or fragment independence. No attack scores or membership labels are selected.
"""
import hashlib
import json
from pathlib import Path

from miaguard.defense_dataset import _normalize, _simhash, DEDUP_MAX_HAMMING

ROOT = Path(__file__).resolve().parents[3]
T10 = ROOT / 'reports/defense_v1/T10'
RUN = ROOT / 'data/defense_v1_runs/e00-observe-20261022-01'
DATA = ROOT / 'data/defense_datasets/defense_access_v1_candidate06'
HISTORY = ROOT / 'data/runs/20260717-ag-news-four-medium/ag_news/target_docs.jsonl'
SPEC = ROOT / 'reports/defense_v1/T05/observe_spec.json'
OUT = T10 / 'e00_source_audit_20261104.json'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]


def main():
    spec = json.loads((RUN / 'experiment_spec.json').read_text(encoding='utf-8'))
    run = json.loads((RUN / 'run_manifest.json').read_text(encoding='utf-8'))
    data_manifest = json.loads((DATA / 'manifest.json').read_text(encoding='utf-8'))
    requests = rows(RUN / 'requests.jsonl')
    if (run['spec_sha256'] != sha(SPEC) or spec != json.loads(SPEC.read_text(encoding='utf-8'))
            or spec['session_keys'] != run['session_keys']):
        raise ValueError('E00 spec identity mismatch')
    if spec['partition'] != 'train' or len(spec['session_keys']) != 2:
        raise ValueError('Unexpected E00 scope')
    session_ids = set(spec['session_keys'])
    if {r['session_id'] for r in requests} != session_ids:
        raise ValueError('E00 request sessions mismatch')
    source_ids = {s.split(':')[-2] for s in session_ids}
    if len(source_ids) != 1:
        raise ValueError('Expected one E00 target document')
    source_id = next(iter(source_ids))
    matching = [r for r in rows(HISTORY) if r.get('doc_id') == source_id]
    if len(matching) != 1 or not matching[0].get('text'):
        raise ValueError('E00 source missing or ambiguous')
    historical_key = str(HISTORY.relative_to(ROOT))
    if data_manifest['source_files_sha256'].get(historical_key) != sha(HISTORY):
        raise ValueError('Historical target file missing or hash differs from frozen manifest')
    source_norm = _normalize(matching[0]['text'])
    source_signature = _simhash(matching[0]['text'])
    counts = {}
    paths = [SPEC, RUN / 'experiment_spec.json', RUN / 'run_manifest.json', RUN / 'requests.jsonl',
             HISTORY, DATA / 'manifest.json', DATA / 'documents.jsonl', DATA / 'background_members.jsonl']
    for name in ('documents.jsonl', 'background_members.jsonl'):
        path = DATA / name
        if data_manifest['artifact_sha256'][name] != sha(path):
            raise ValueError('Candidate corpus hash differs from frozen manifest')
        docs = rows(path)
        counts[name] = {'rows': len(docs),
                        'same_id': sum(r['doc_id'] == source_id for r in docs),
                        'same_normalized_full_text': sum(_normalize(r['text']) == source_norm for r in docs),
                        'simhash_hamming_le_3': sum((_simhash(r['text']) ^ source_signature).bit_count() <= DEDUP_MAX_HAMMING for r in docs)}
    result = {'status': 'complete', 'source_id': source_id, 'e00_requests': len(requests),
              'e00_sessions': len(session_ids), 'historical_target_file_in_candidate_manifest': True,
              'source_text_sha256': hashlib.sha256(matching[0]['text'].encode('utf-8')).hexdigest(),
              'comparison': counts, 'input_sha256': {str(p.relative_to(ROOT)).replace('\\', '/'): sha(p) for p in paths},
              'limitations': ['Only the source ID named by E00 session keys was checked; other development prompts may expose other sources.',
                              'Full-text SimHash and exact ID cannot prove absence of fragment or event/semantic overlap.',
                              'Candidate content was compared mechanically; no partition-level content, membership labels, attack outcomes, or effect data are reported.',
                              'E00 requests were not independently audited for indirect or undocumented sources.']}
    if OUT.exists():
        raise FileExistsError(OUT)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'source_id': source_id, 'requests': len(requests), 'comparison': counts}))


if __name__ == '__main__':
    main()
