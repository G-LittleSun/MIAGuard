"""Freeze extra development sources, preserving original documents and online requests."""
from collections import Counter
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path

ROOT = Path.cwd()
OUT = ROOT / 'data/defense_datasets/multi_action_sources_v2_train_20261117_01'

def digest(path):
    return sha256(path.read_bytes()).hexdigest()

def read(path):
    return json.loads(path.read_text(encoding='utf8'))

def rows(path):
    return [json.loads(line) for line in path.read_text(encoding='utf8').splitlines() if line.strip()]

def write(path, obj):
    with path.open('x', encoding='utf8') as f:
        f.write(json.dumps(obj, ensure_ascii=False, indent=2) + '\n')

def main():
    base = ROOT / 'data/defense_datasets/multi_action_v2_train_20261117_01'
    locator = ROOT / 'data/defense_datasets/locator_new_sources_20261111_01'
    overlay = ROOT / 'data/defense_datasets/legacy_v2_reuse_overlay_20261105_01'
    for parent in (base, locator, overlay):
        for name, expected in read(parent / 'manifest.json')['output_sha256'].items():
            assert digest(parent / name) == expected, (parent, name)
    spec = read(base / 'experiment_spec.json')
    source = {r['doc_id']: r for r in rows(ROOT / 'data/runs/20260717-ag-news-four-medium/ag_news/target_docs.jsonl')}
    bank = rows(Path(spec['identity_files']['query_bank_queries']))
    train_ids = set(read(Path(spec['identity_files']['split']))['partitions']['train']['doc_ids'])
    indexed = {r.get('parent_doc_id') or r['doc_id'] for r in rows(Path(spec['identity_files']['index_documents']))}
    prior_targets = {r['doc_id'] for r in rows(base / 'labels.jsonl')}
    locator_labels = {r['request_id']: r for r in rows(locator / 'labels.jsonl')}
    overlay_labels = {r['request_id']: r for r in rows(overlay / 'labels.jsonl')}
    overlay_requests = {r['request_id']: r for r in rows(overlay / 'requests.jsonl')}
    requests, labels, lineage = [], [], []
    for r in rows(locator / 'requests.jsonl'):
        label = locator_labels[r['request_id']]
        assert label['doc_id'] not in prior_targets
        requests.append(r); labels.append(label)
        lineage.append({'request_id': r['request_id'], 'source_doc_id': label['doc_id'], 'turn': 1,
                        'source_cohort': locator.name, 'reviewer_kind': 'llm_agent'})
    for doc in ('ag_news_teacher_00000313', 'ag_news_teacher_00008001', 'ag_news_teacher_00008290'):
        assert doc not in prior_targets and doc in train_ids and doc in source
        member = int(doc in indexed)
        assert member == source[doc]['membership_label']
        for kind in ('direct_rag_mia', 's2_mia'):
            matches = [r for r in bank if r['doc_id'] == doc and r['attack_type'] == kind and r['variant_type'] == 'canonical']
            assert len(matches) == 1
            entry = matches[0]
            assert sha256(source[doc]['text'].encode()).hexdigest() == entry['source_document_sha256']
            rid = 'ms_' + sha256(entry['query_id'].encode()).hexdigest()[:20]
            requests.append({'request_id': rid, 'session_id': rid, 'query': entry['query_text']})
            label = {'request_id': rid, 'doc_id': doc, 'traffic_type': 'attack', 'attack_type': kind,
                     'membership_label': member, 'human_reviewed': False, 'formal_effect_eligible': False}
            if kind == 's2_mia':
                label['target_text'] = source[doc]['text']
                assert entry['payload']['prefix'] in source[doc]['text']
            labels.append(label)
            lineage.append({'request_id': rid, 'source_doc_id': doc, 'source_query_id': entry['query_id'], 'turn': 1})
        masked = sorted((r for r in overlay_labels.values() if r['doc_id'] == doc and r['attack_type'] == 'masked_mia'), key=lambda x: x['request_id'])
        assert masked
        label = masked[0]; request = overlay_requests[label['request_id']]
        assert label['membership_label'] == member and label['answers']
        requests.append(request); labels.append(label)
        lineage.append({'request_id': request['request_id'], 'source_doc_id': doc, 'turn': 1,
                        'source_cohort': overlay.name, 'reviewer_kind': 'llm_agent'})
    ia = ('vr_787d24f61245772af483db82', 'vr_ba19bccf08d9e67cdadc02f6',
          'vr_9a5bac42391b7969968ed388', 'vr_6fb2eac53477b9bfe9167516')
    for rid in ia:
        label = overlay_labels[rid]; doc = label['doc_id']
        assert doc not in prior_targets and doc in train_ids and label['membership_label'] == int(doc in indexed)
        requests.append(overlay_requests[rid]); labels.append(label)
        lineage.append({'request_id': rid, 'source_doc_id': doc, 'turn': 1,
                        'source_cohort': overlay.name, 'reviewer_kind': 'llm_agent'})
    assert len(requests) == 19 and len({r['request_id'] for r in requests}) == len(requests)
    assert all(set(r) == {'request_id', 'session_id', 'query'} for r in requests)
    OUT.mkdir(exist_ok=False)
    for name, values in [('requests', requests), ('labels', labels), ('lineage', lineage), ('normal_rubric', [])]:
        with (OUT / (name + '.jsonl')).open('x', encoding='utf8') as f:
            for value in values:
                f.write(json.dumps(value, ensure_ascii=False) + '\n')
    spec = deepcopy(spec)
    spec.update(experiment_id='T10D-multi-action-source-expansion',
                methods=['B0', 'B2', 'B_TYPE_V2', 'B_MULTI_SUMMARY', 'B_MULTI_NO_CONTEXT'],
                requests_path=str(OUT / 'requests.jsonl'), labels_path=str(OUT / 'labels.jsonl'))
    for key in ('normal_rubric', 'lineage'):
        spec['identity_files'][key] = str(OUT / (key + '.jsonl'))
    spec['identity_files']['cohort_manifest'] = str(OUT / 'manifest.json')
    write(OUT / 'experiment_spec.json', spec)
    inputs = {str(parent / 'manifest.json'): digest(parent / 'manifest.json') for parent in (base, locator, overlay)}
    inputs[str(Path(__file__).resolve())] = digest(Path(__file__))
    counts = Counter((r['attack_type'], r['membership_label']) for r in labels)
    write(OUT / 'manifest.json', {'version_id': OUT.name, 'bank_id': 'ag_news_queries_v2',
          'split_id': 'ag_news_threshold_v2', 'partition': 'train', 'analysis_role': 'engineering_only',
          'formal_effect_eligible': False, 'human_gold_complete': False, 'request_count': len(requests),
          'expected_events': len(requests)*len(spec['methods']), 'methods': spec['methods'],
          'counts': {str(k): v for k,v in counts.items()}, 'input_sha256': inputs,
          'output_sha256': {p.name: digest(p) for p in sorted(OUT.iterdir())},
          'selection': 'Six previous locator member examples; three sources outside current parent target IDs with canonical Direct/S2 and first overlay Masked; four pre-reviewed overlay IA queries on four sources outside current parent. Fixed before current candidate outcomes.',
          'limitations': ['All sources are v2 train known to the frozen Judge; six member examples previously used in defense development.',
                          'Distinct IDs are not independent events; do not claim fresh test or statistical significance.',
                          'Overlay pending review; IA questions lack a topic anchor and may not retrieve the intended article.',
                          'Attack-only supplement; normal quality and budget comparisons use the main cohort.']})
    print(OUT, 'counts', counts, 'expected', len(requests)*len(spec['methods']))

if __name__ == '__main__':
    main()
