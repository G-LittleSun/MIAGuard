"""Verify fixed benchmark input identities and inventory eligible source coverage."""

from collections import Counter, defaultdict
from hashlib import sha256
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[3]
REPORT = ROOT / 'reports/defense_v1/T10'
DATA = ROOT / 'data/defense_datasets'
SELECTION = REPORT / 'legacy_reuse_selection_20261104.json'
OVERLAY = DATA / 'legacy_v2_reuse_overlay_20261105_01'
THREE_ROUND = DATA / 'multiturn_ia_session_v2_train_20261113_01'
BASE_SPEC = DATA / 'next_goal_ablation_v2_train_20261117_01' / 'experiment_spec.json'
BASE_RUN = ROOT / 'data/defense_v1_runs/next-goal-ablation-20261117-01/run_manifest.json'
SOURCES = ROOT / 'data/runs/20260717-ag-news-four-medium/ag_news/target_docs.jsonl'
REUSE_AUDIT = REPORT / 'v2_train_reuse_audit_20261105_01/query_reuse_audit.jsonl'
OUTPUT = REPORT / 'four_type40_preflight_20261118.json'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def rows(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def verify():
    selection = read(SELECTION)
    assert (selection['bank_id'], selection['split_id'], selection['partition']) == (
        'ag_news_queries_v2', 'ag_news_threshold_v2', 'train')
    selected = {name: ROOT / item['path'] for name, item in selection['input_files'].items()}
    for name, path in selected.items():
        assert digest(path) == selection['input_files'][name]['sha256'], name
    for package in (OVERLAY, THREE_ROUND):
        for name, expected in read(package / 'manifest.json')['output_sha256'].items():
            assert digest(package / name) == expected, f'{package.name}/{name}'
    base = read(BASE_RUN)
    assert base['status'] == 'completed' and base['outcome'] == 'valid'
    spec = read(BASE_SPEC)
    assert digest(BASE_SPEC) == base['files_sha256']['spec']
    for name, file in spec['identity_files'].items():
        assert digest(Path(file)) == base['files_sha256']['identity:' + name], name
    for name, expected in base['files_sha256'].items():
        if name.startswith('code:'):
            filename = name.split(':', 1)[1]
            path = ROOT / ('scripts' if filename == 'run_defense_v1_benchmark.py' else 'src/miaguard') / filename
            assert digest(path) == expected, filename
    return selected, base


def main():
    selected, base = verify()
    split = read(selected['split'])
    assert split['query_bank']['queries_sha256'] == digest(selected['queries'])
    train = set(split['partitions']['train']['doc_ids'])
    index = {item.get('parent_doc_id') or item['doc_id'] for item in rows(selected['index_documents'])}
    sources = {item['doc_id']: item for item in rows(SOURCES) if item['doc_id'] in train}
    assert set(sources) == train and all(item['membership_label'] == int(doc in index) for doc, item in sources.items())
    by_doc = {doc: defaultdict(list) for doc in sorted(train)}
    for item in rows(selected['queries']):
        doc = item['doc_id']
        if doc in train and item['traffic_type'] == 'attack':
            assert item['membership_label'] == int(doc in index), item['query_id']
            assert sha256(sources[doc]['text'].encode('utf-8')).hexdigest() == item['source_document_sha256'], item['query_id']
            by_doc[doc][item['attack_type']].append(item)

    overlay_requests = {item['request_id']: item for item in rows(OVERLAY/'requests.jsonl')}
    overlay = defaultdict(lambda: defaultdict(list))
    for item in rows(OVERLAY/'labels.jsonl'):
        doc = item['doc_id']
        assert item['request_id'] in overlay_requests and doc in train and item['membership_label'] == int(doc in index)
        overlay[doc][item['attack_type']].append(item)

    sessions = defaultdict(list)
    prior_requests = {item['request_id']: item for item in rows(THREE_ROUND/'requests.jsonl')}
    for item in rows(THREE_ROUND/'labels.jsonl'):
        if item['attack_type'] == 'ia':
            sessions[prior_requests[item['request_id']]['session_id']].append(item)
    prior_ia_docs = set()
    for session in sessions.values():
        assert len(session) == 3 and len({item['doc_id'] for item in session}) == 1
        prior_ia_docs.add(session[0]['doc_id'])

    audit = {item['query_id']: item for item in rows(REUSE_AUDIT)}
    inventory = []
    for doc, records in by_doc.items():
        def structural_canonicals(attack):
            return [item['query_id'] for item in records[attack] if item['variant_type'] == 'canonical'
                    and audit[item['query_id']]['recommended_action'] == 'reuse_content_after_adapter'
                    and not audit[item['query_id']]['fatal_issues']]
        ia = records['ia']
        normalized = {re.sub(r'\W+', ' ', x['query_text'].casefold()).strip() for x in ia}
        inventory.append({
            'source_doc_id': doc, 'indexed': doc in index,
            'source_text_sha256': sha256(sources[doc]['text'].encode('utf-8')).hexdigest(),
            'direct_structural_canonical_ids': structural_canonicals('direct_rag_mia'),
            's2_structural_canonical_ids': structural_canonicals('s2_mia'),
            'masked_overlay_candidate_count': len(overlay[doc]['masked_mia']),
            'masked_overlay_without_documented_quality_flags': sum(not x['quality_flags'] for x in overlay[doc]['masked_mia']),
            'ia_distinct_original_query_count': len(normalized),
            'ia_original_reference_counts': dict(Counter(x['payload']['ground_truth'] for x in ia)),
            'ia_overlay_candidate_count': len(overlay[doc]['ia']),
            'ia_already_run_as_three_round_session': doc in prior_ia_docs,
        })
    counts = {}
    for member, label in ((True, 'indexed'), (False, 'not_indexed')):
        subset = [row for row in inventory if row['indexed'] == member]
        counts[label] = {
            'train_documents': len(subset),
            'direct_with_structural_canonical': sum(bool(row['direct_structural_canonical_ids']) for row in subset),
            's2_with_structural_canonical': sum(bool(row['s2_structural_canonical_ids']) for row in subset),
            'masked_with_overlay_candidate': sum(row['masked_overlay_candidate_count'] > 0 for row in subset),
            'masked_with_overlay_without_documented_flags': sum(row['masked_overlay_without_documented_quality_flags'] > 0 for row in subset),
            'ia_with_three_distinct_original_strings': sum(row['ia_distinct_original_query_count'] >= 3 for row in subset),
            'ia_with_three_overlay_records': sum(row['ia_overlay_candidate_count'] >= 3 for row in subset),
            'ia_with_previously_run_three_round_session': sum(row['ia_already_run_as_three_round_session'] for row in subset),
        }
    result = {
        'status': 'inventory_only', 'baseline_run_identity_sha256': base['identity_sha256'], 'counts': counts,
        'documents': inventory, 'formal_effect_eligible': False,
        'input_sha256': {str(path.relative_to(ROOT)): digest(path) for path in (
            SELECTION, *selected.values(), BASE_SPEC, BASE_RUN, SOURCES, REUSE_AUDIT,
            OVERLAY/'manifest.json', THREE_ROUND/'manifest.json', Path(__file__).resolve())},
        'limits': ['Candidate counts are not semantic approvals.',
                   'Three distinct query strings do not establish three distinct grounded facts or a valid session.',
                   'Overlay records are pending and the overlay manifest is not an approval for full replay.',
                   'No request text was generated or modified. No run was started by this inventory.'],
    }
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(counts, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
