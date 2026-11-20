"""Audit fixed pairings, run identity, and attached generation evidence."""

from collections import Counter, defaultdict
from hashlib import sha256
import json
from pathlib import Path
import sys

from inventory_four_type40_20261118 import REPORT, digest, read, rows


def verify_run(run):
    manifest = read(run / 'run_manifest.json')
    spec_path = run / 'experiment_spec.json'
    spec = read(spec_path)
    metrics = read(run / 'metrics.json')
    hashes = manifest['files_sha256']
    assert manifest['status'] == 'completed' and metrics['status'] in {'completed', 'invalid'}
    assert manifest['outcome'] == metrics['outcome']
    assert manifest['backend'] == 'live' and manifest['methods'] == ['B0', 'B_TYPE_V2']
    assert digest(run / 'metrics.json') == manifest['metrics_sha256']
    assert digest(spec_path) == hashes['spec']
    for name, path in spec['identity_files'].items():
        assert digest(Path(path)) == hashes['identity:' + name], name
    cohort_path = Path(spec['identity_files']['cohort_manifest'])
    cohort = read(cohort_path)
    for name, expected in cohort['output_sha256'].items():
        assert digest(cohort_path.parent / name) == expected, name
    assert hashes['spec'] == digest(cohort_path.parent / 'experiment_spec.json')
    request_rows = rows(run / 'requests.jsonl')
    input_requests = rows(Path(spec['requests_path']))
    assert len(request_rows) == len(input_requests)
    for original, archived in zip(input_requests, request_rows, strict=True):
        assert set(archived) <= {'request_id', 'session_id', 'query', 'allowed_doc_ids'}
        assert all(archived[k] == v for k, v in original.items())
    assert digest(Path(spec['requests_path'])) == hashes['requests']
    assert digest(Path(spec['labels_path'])) == hashes['labels']
    assert rows(run / 'labels.jsonl') == rows(Path(spec['labels_path']))
    requests = {q['request_id']: q for q in request_rows}
    labels = {q['request_id']: q for q in rows(run / 'labels.jsonl')}
    assert len(request_rows) == len(requests) == len(labels) and requests.keys() == labels.keys()
    source_ids = {q.get('parent_doc_id') or q['doc_id'] for q in rows(Path(spec['identity_files']['index_documents']))}
    for label in labels.values():
        assert label['membership_label'] == int(label['doc_id'] in source_ids)
    events = rows(run / 'events.jsonl')
    expected_pairs = {(method, rid) for method in manifest['methods'] for rid in requests}
    assert len(events) == len(expected_pairs) == cohort['expected_events'] == metrics['expected']
    assert {(e['method'], e['request_id']) for e in events} == expected_pairs
    states = Counter(e['status'] for e in events)
    assert (states['complete'], states['failed'], states['skipped']) == (metrics['completed'], metrics['failed'], metrics['skipped'])
    assert metrics['status'] == ('invalid' if states['skipped'] else 'completed')
    expected_score_groups = defaultdict(list)
    for event in events:
        label = labels[event['request_id']]
        if label['attack_type'] != 'benign':
            key = (event['method'], event['seed'], label['doc_id'], label['attack_type'], label['membership_label'])
            expected_score_groups[key].append(event['request_id'])
    scores = rows(run / 'attack_scores.jsonl')
    archived_score_groups = {
        (score['method'], score['seed'], score['doc_id'], score['attack_type'], score['membership_label']): score['request_ids']
        for score in scores if len(score['request_ids']) == score['budget']}
    assert len(scores) == len(archived_score_groups) and archived_score_groups == expected_score_groups
    checked_artifacts = 0
    session_traces = Counter()
    for event in events:
        rid = event['request_id']
        assert event['session_id'] == requests[rid]['session_id']
        if event['status'] != 'complete':
            continue
        assert isinstance(event['retrieved_doc_ids'], list) and isinstance(event['latency_ms'], (int, float))
        path = (run / event['generation_input_ref']).resolve()
        assert path.is_relative_to(run.resolve()) and digest(path) == event['artifact_sha256']
        artifact = read(path)
        ledger = event['ledger_event']
        assert ledger['response'] == event['response'] and ledger['retrieved_doc_ids'] == event['retrieved_doc_ids']
        captured = artifact['generation_input']
        assert captured['query'] == requests[rid]['query']
        delivered = ledger['delivered_evidence']
        assert [x['doc_id'] for x in delivered] == event['delivered_doc_ids']
        assert len(delivered) == len(captured['contexts'])
        for text, record in zip(captured['contexts'], delivered, strict=True):
            assert sha256(text.encode('utf-8')).hexdigest() == record['text_sha256']
        for trace in artifact['judge_traces']:
            risk = trace['risk']
            if risk['stage'] == 'session':
                session_traces[event['method'], risk['status']] += 1
        checked_artifacts += 1
    return {
        'run_id': manifest['run_id'], 'verified_method_request_pairs': len(events),
        'event_status': states, 'outcome': manifest['outcome'], 'generation_artifacts_verified': checked_artifacts,
        'verified_attack_score_groups': len(scores),
        'session_judge_trace_counts': {str(k): v for k, v in session_traces.items()},
        'verifier_sha256': digest(Path(__file__)),
        'input_sha256': {name: digest(run / name) for name in (
            'run_manifest.json', 'metrics.json', 'events.jsonl', 'attack_scores.jsonl')},
        'formal_effect_eligible': False,
    }


if __name__ == '__main__':
    result = verify_run(Path(sys.argv[1]).resolve())
    path = REPORT / (result['run_id'].replace('-', '_') + '_verification.json')
    payload = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
    path.write_text(payload, encoding='utf-8')
    print(payload)
