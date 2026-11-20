"""Freeze the single-turn stratum and a small harness check using existing fixtures."""

from collections import Counter, defaultdict
import json
from pathlib import Path
import re

from inventory_four_type40_20261118 import (
    BASE_RUN, BASE_SPEC, DATA, OVERLAY, OUTPUT, REPORT, ROOT, SOURCES, THREE_ROUND,
    digest, read, rows, verify,
)

KINDS = ('direct_rag_mia', 's2_mia', 'masked_mia')
RULES = REPORT / 'FOUR_TYPE40_SCORING_ZH.md'


def existing_records():
    selected, _ = verify()
    inventory = read(OUTPUT)
    for name, expected in inventory['input_sha256'].items():
        assert digest(ROOT / name) == expected, name
    bank = {q['query_id']: q for q in rows(selected['queries'])}
    sources = {row['doc_id']: row['text'] for row in rows(SOURCES)}
    assert read(OVERLAY / 'validation.json')['errors'] == []
    requests = {q['request_id']: q for q in rows(OVERLAY / 'requests.jsonl')}
    lineage = {q['request_id']: q for q in rows(OVERLAY / 'lineage.jsonl')}
    by_mask_doc = defaultdict(list)
    for row in rows(OVERLAY / 'labels.jsonl'):
        if row['attack_type'] == 'masked_mia' and not row['quality_flags']:
            by_mask_doc[row['doc_id']].append(row)

    chosen = []
    norm_seen = set()
    for member in (True, False):
        # A shared document set makes cross-type coverage explicit. Selection uses
        # existing quality records, never the outcomes of the methods being compared.
        for item in inventory['documents']:
            doc = item['source_doc_id']
            if item['indexed'] != member or not by_mask_doc[doc]:
                continue
            key = ' '.join(re.findall(r'\w+', sources[doc].casefold()))
            if key in norm_seen or not item['direct_structural_canonical_ids'] or not item['s2_structural_canonical_ids']:
                continue
            norm_seen.add(key)
            chosen.append(item)
            if sum(x['indexed'] == member for x in chosen) == 20:
                break
    assert Counter(x['indexed'] for x in chosen) == {True: 20, False: 20}
    records = []
    for item in chosen:
        doc = item['source_doc_id']
        member = int(item['indexed'])
        for kind, field in (('direct_rag_mia', 'direct_structural_canonical_ids'),
                            ('s2_mia', 's2_structural_canonical_ids')):
            qid, = item[field]
            q = bank[qid]
            extras = {'target_text': sources[doc]} if kind == 's2_mia' else {}
            if kind == 's2_mia':
                assert ' '.join(q['payload']['prefix'].split()) in ' '.join(sources[doc].split())
            else:
                assert ' '.join(q['payload']['target_text'].split()) == ' '.join(sources[doc].split())
            records.append((q['query_text'], kind, doc, member, extras, qid, 'v2_bank_canonical', qid))
        mask = min(by_mask_doc[doc], key=lambda q: q['source_query_id'])
        q = requests[mask['request_id']]
        assert len(mask['answers']) == 5 and len({a.casefold() for a in mask['answers']}) == 5
        assert lineage[q['request_id']]['parent_query_id'] == mask['source_query_id']
        records.append((q['query'], 'masked_mia', doc, member, {'answers': mask['answers']},
                        q['request_id'], 'existing_overlay_reviewed_fixture', mask['source_query_id']))
    return records


def export(folder, records, scope):
    folder.mkdir(exist_ok=False)
    requests, labels, provenance = [], [], []
    for index, (query, kind, doc, member, extra, origin, source, parent) in enumerate(records, 1):
        rid = f'q{index:03d}'
        session = f'ia_{doc}' if kind == 'ia' else rid
        requests.append({'request_id': rid, 'session_id': session, 'query': query})
        labels.append({'request_id': rid, 'doc_id': doc, 'attack_type': kind, 'membership_label': member,
                       'traffic_type': 'attack', 'human_reviewed': False, 'formal_effect_eligible': False, **extra})
        provenance.append({'request_id': rid, 'source_kind': source, 'original_id': origin,
                           'source_query_id': parent, 'source_doc_id': doc})
    for name, data in [('requests', requests), ('labels', labels), ('lineage', provenance)]:
        (folder / (name + '.jsonl')).write_text(''.join(json.dumps(row, ensure_ascii=False) + '\n' for row in data), encoding='utf-8')
    config = read(BASE_SPEC)
    config.update(experiment_id=folder.name, methods=['B0', 'B_TYPE_V2'],
                  requests_path=str(folder / 'requests.jsonl'), labels_path=str(folder / 'labels.jsonl'))
    config['identity_files'].pop('normal_rubric', None)
    config['identity_files'].update(lineage=str(folder / 'lineage.jsonl'),
                                    cohort_manifest=str(folder / 'manifest.json'), scoring_rules=str(RULES))
    (folder / 'experiment_spec.json').write_text(json.dumps(config, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    manifest = {
        'version_id': folder.name, 'bank_id': 'ag_news_queries_v2', 'split_id': 'ag_news_threshold_v2',
        'partition': 'train', 'scope': scope, 'analysis_role': 'engineering_only', 'human_reviewed': False,
        'formal_effect_eligible': False, 'expected_events': len(requests) * 2,
        'target_counts': {str(key): len({x['doc_id'] for x in labels if (x['attack_type'], x['membership_label']) == key})
                          for key in sorted({(x['attack_type'], x['membership_label']) for x in labels})},
        'unique_documents': len({x['doc_id'] for x in labels}),
        'source_event_independence_proven': False,
        'selection': 'Existing frozen fixtures, shared selected docs for single-turn types, no exact normalized source duplicates.',
        'input_sha256': {str(path): digest(path) for path in (OUTPUT, BASE_SPEC, BASE_RUN, RULES, Path(__file__))},
        'output_sha256': {file.name: digest(file) for file in folder.iterdir()},
    }
    (folder / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(folder.name, manifest['target_counts'], 'events', manifest['expected_events'])


def main():
    records = existing_records()
    assert len(records) == 120 and Counter((r[1], r[3]) for r in records) == {
        (kind, member): 20 for kind in KINDS for member in (0, 1)}
    smoke = [next(r for r in records if r[1] == kind and r[3] == member)
             for kind in KINDS for member in (0, 1)]
    prior = {q['request_id']: q for q in rows(THREE_ROUND / 'labels.jsonl') if q['attack_type'] == 'ia'}
    picked = {member: next(q['doc_id'] for q in prior.values() if q['membership_label'] == member) for member in (0, 1)}
    for q in rows(THREE_ROUND / 'requests.jsonl'):
        lid = q['request_id']
        if lid in prior and prior[lid]['doc_id'] in picked.values():
            a = prior[lid]
            smoke.append((q['query'], 'ia', a['doc_id'], a['membership_label'], {'ground_truth': a['ground_truth']},
                          lid, 'historical_three_round_validation', a.get('source_query_id')))
    assert len(smoke) == 12
    export(DATA / 'four_type40_smoke_20261118_01', smoke, 'Harness validation only; prior three-round IA fixtures.')
    export(DATA / 'four_type40_single_v2_train_20261118_01', records, 'Main single-turn stratum; IA is a separate stratum.')


if __name__ == '__main__':
    main()
