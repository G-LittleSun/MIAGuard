"""Audit what the completed live runs actually retrieved, transformed and delivered."""
import argparse
import hashlib
import json
import re
from pathlib import Path

from screen_rank_stress_20261109 import ROOT, rows


def sha(data):
    return hashlib.sha256(data).hexdigest()


def term_hits(terms, text):
    return [term for term in terms if re.search(r'(?<!\w)' + re.escape(term) + r'(?!\w)', text, re.IGNORECASE)]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('run', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    run = args.run
    manifest = json.loads((run / 'run_manifest.json').read_text(encoding='utf-8'))
    metrics = json.loads((run / 'metrics.json').read_text(encoding='utf-8'))
    assert manifest['status'] == 'completed' and metrics['outcome'] == 'valid'
    assert metrics['analysis_role'] == 'engineering_only'
    assert manifest['metrics_sha256'] == sha((run / 'metrics.json').read_bytes())
    labels = {x['request_id']: x for x in rows(run / 'labels.jsonl')}
    requests = {x['request_id']: x for x in rows(run / 'requests.jsonl')}
    assert all(set(x) == {'request_id', 'session_id', 'query', 'allowed_doc_ids'}
               and x['allowed_doc_ids'] is None for x in requests.values())
    assert set(requests) == set(labels)
    spec = json.loads((run / 'experiment_spec.json').read_text(encoding='utf-8'))
    for name, stored in [('requests', requests), ('labels', labels)]:
        path = Path(spec[f'{name}_path'])
        assert manifest['files_sha256'][name] == sha(path.read_bytes())
        for row in rows(path):
            copied = stored[row['request_id']]
            assert (row | {'allowed_doc_ids': None} if name == 'requests' else row) == copied
    docs_path = ROOT / 'data/vector_stores/20260717-ag-news-four-medium/ag_news/documents.jsonl'
    assert manifest['files_sha256']['identity:index_documents'] == sha(docs_path.read_bytes())
    docs = {x['doc_id']: x for x in rows(docs_path)}
    events = rows(run / 'events.jsonl')
    assert len(events) == metrics['expected'] == metrics['completed']
    assert len(events) == len({(e['method'], e['request_id']) for e in events}) == len(requests) * len(manifest['methods'])
    result = []
    for event in events:
        rid = event['request_id']
        label = labels[rid]
        target = label['doc_id']
        raw_artifact = (run / event['generation_input_ref']).read_bytes()
        assert event['status'] == 'complete' and sha(raw_artifact) == event['artifact_sha256']
        artifact = json.loads(raw_artifact)['generation_input']
        assert artifact['query'] == requests[rid]['query']
        exposure = event['ledger_event']
        retrieved = event['retrieved_doc_ids']
        transforms = exposure['transform_input_evidence']
        delivered = exposure['delivered_evidence']
        assert [x['doc_id'] for x in delivered] == event['delivered_doc_ids']
        assert len(artifact['contexts']) == len(delivered)
        for item, context in zip(delivered, artifact['contexts']):
            assert sha(context.encode()) == item['text_sha256'], (rid, item['doc_id'])
        for item in transforms:
            assert item['kind'] == 'raw' and sha(docs[item['doc_id']]['text'].encode()) == item['text_sha256']
        execution = (event['risk'] or {}).get('execution', {})
        excluded = execution.get('excluded_parent_ids', [])
        assert not set(excluded) & {x['parent_doc_id'] for x in delivered}
        summary = [c for item, c in zip(delivered, artifact['contexts']) if item['kind'] == 'summary']
        row = {'request_id': rid, 'method': event['method'], 'attack_type': label['attack_type'],
               'target_doc_id': target, 'target_in_index': target in docs, 'action': event['action'],
               'target_rank': retrieved.index(target) + 1 if target in retrieved else None,
               'retrieved_doc_ids': retrieved, 'excluded_parent_ids': excluded,
               'added_doc_ids': [x['doc_id'] for x in delivered if x['kind'] == 'raw' and x['doc_id'] not in retrieved],
               'target_in_summary_input': any(x['parent_doc_id'] == target for x in transforms),
               'target_raw_in_answer_input': any(x['parent_doc_id'] == target and x['kind'] == 'raw' for x in delivered),
               'delivered_summary': summary, 'response': event['response'], 'artifact_ref': event['generation_input_ref']}
        if label['attack_type'] == 'masked_mia':
            terms = label['answers']
            row['masked_terms_in_query'] = term_hits(terms, artifact['query'])
            row['masked_terms_in_delivered_summary'] = term_hits(terms, '\n'.join(summary))
        result.append(row)
    args.output.write_text(json.dumps({'run_id': manifest['run_id'], 'verified_events': len(events),
                                      'formal_effect_eligible': False, 'cases': result},
                                     ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'Verified {len(events)} events and generation evidence in {run.name}')


if __name__ == '__main__':
    main()
