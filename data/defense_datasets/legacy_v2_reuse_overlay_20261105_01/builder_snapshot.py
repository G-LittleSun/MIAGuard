"""Export pending attack drafts; no formal gold or executable benchmark is released."""
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
T10 = ROOT / 'reports/defense_v1/T10'
INTEGRATION = T10 / 'v2_reuse_review_integration_20261105_01'
REVIEW = T10 / 'external_review/v2_reuse_deepseek-v4.1-flash_20261105_01'
PACKET = T10 / 'v2_reuse_review_packet_20261105_01'
OUT = ROOT / 'data/defense_datasets/legacy_v2_reuse_overlay_20261105_01'
VERSION = OUT.name


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return [json.loads(x) for x in path.read_text(encoding='utf-8').splitlines() if x.strip()]


def write(path, values):
    path.write_text(''.join(json.dumps(x, ensure_ascii=False) + '\n' for x in values), encoding='utf-8')


def main():
    if OUT.exists():
        raise FileExistsError(OUT)
    structural = json.loads((INTEGRATION / 'structural_validation.json').read_text(encoding='utf-8'))
    if structural['status'] != 'passed':
        raise ValueError('External review validation failed')
    review_manifest = json.loads((REVIEW / 'review_manifest.json').read_text(encoding='utf-8'))
    for name in ('ia_review.jsonl', 'masked_review.jsonl', 'review_summary.md'):
        if sha(REVIEW / name) != review_manifest['output_files'][name]['sha256']:
            raise ValueError('Review file changed')
    selection_path = T10 / 'legacy_reuse_selection_20261104.json'
    selection = json.loads(selection_path.read_text(encoding='utf-8'))
    if (selection['bank_id'], selection['split_id'], selection['partition']) != ('ag_news_queries_v2', 'ag_news_threshold_v2', 'train'):
        raise ValueError('Wrong parent data identity')
    for item in selection['input_files'].values():
        if sha(ROOT / item['path']) != item['sha256']:
            raise ValueError('Selected source input changed')
    split_path = ROOT / 'data/query_bank_splits/ag_news_threshold_v2.json'
    query_path = ROOT / 'data/query_banks/ag_news_queries_v2/ag_news/queries.jsonl'
    split = json.loads(split_path.read_text(encoding='utf-8'))
    train = set(split['partitions']['train']['doc_ids'])
    parents = {r['query_id']: r for r in read(query_path) if r['doc_id'] in train}
    index_path = ROOT / 'data/vector_stores/20260717-ag-news-four-medium/ag_news/documents.jsonl'
    index = {r['doc_id'] for r in read(index_path)}
    amend = {r['query_id']: r for r in read(INTEGRATION / 'ia_local_amendments.jsonl')}
    dispositions = {r['query_id']: r for r in read(INTEGRATION / 'ia_dispositions.jsonl')}
    mask_triage = {r['review_id']: r for r in read(INTEGRATION / 'masked_triage.jsonl')}
    requests, labels, lineage, holds = [], [], [], []

    def add(parent_id, query, score_payload, provenance, flags, notes):
        parent = parents[parent_id]
        if int(parent['membership_label']) != int(parent['doc_id'] in index):
            raise ValueError('Parent membership does not match original index')
        canonical = json.dumps({'version': VERSION, 'parent': parent_id, 'query': query,
                                'score_payload': score_payload}, sort_keys=True, separators=(',', ':'))
        ident = hashlib.sha256(canonical.encode('utf-8')).hexdigest()[:24]
        rid = 'vr_' + ident
        requests.append({'request_id': rid, 'session_id': 'vs_' + ident, 'query': query})
        labels.append({'request_id': rid, 'doc_id': parent['doc_id'], 'partition': 'train',
                       'traffic_type': 'attack', 'attack_type': parent['attack_type'],
                       'membership_label': parent['membership_label'], **score_payload,
                       'source_query_id': parent_id, 'source_document_sha256': parent['source_document_sha256'],
                       'review_status': 'pending', 'reviewed_by': None, 'human_reviewed': False,
                       'formal_effect_eligible': False, 'suggestion_origin': provenance,
                       'quality_flags': flags, 'integration_notes': notes})
        lineage.append({'request_id': rid, 'parent_query_id': parent_id,
                        'parent_query_sha256': hashlib.sha256(parent['query_text'].encode('utf-8')).hexdigest(),
                        'query_sha256': hashlib.sha256(query.encode('utf-8')).hexdigest(),
                        'source_document_sha256': parent['source_document_sha256'],
                        'query_changed': query != parent['query_text'], 'suggestion_origin': provenance,
                        'reuse_old_trace_allowed': False})

    for row in read(REVIEW / 'ia_review.jsonl'):
        rid = row['query_id']
        disposition = dispositions[rid]
        if not disposition['integration_disposition'].startswith('pending_engineering_draft'):
            holds.append({'source_query_id': rid, **disposition, 'reviewer_reason': row['reason'],
                          'reviewer_notes': row['notes'], 'permanently_excluded': False})
            continue
        chosen = amend.get(rid, row)
        add(rid, chosen['corrected_query'], {'ground_truth': chosen['corrected_ground_truth']},
            'Codex_local_amendment_after_DeepSeek' if rid in amend else 'DeepSeek_suggestion',
            disposition['quality_flags'], chosen.get('change_note', row['notes']))
    for row in read(REVIEW / 'masked_review.jsonl'):
        t = mask_triage[row['review_id']]
        for q in row['corrected_queries']:
            add(q['query_id'], q['query'], {'answers': row['corrected_answers']},
                'DeepSeek_suggestion_with_Codex_change_notes', t['quality_flags'], t['integration_change_note'])
    counts = dict(Counter(r['attack_type'] for r in labels))
    if counts != {'ia': 62, 'masked_mia': 300} or len(holds) != 144 or len({r['request_id'] for r in requests}) != 362:
        raise ValueError('Unexpected candidate/hold counts')
    OUT.mkdir(parents=True, exist_ok=False)
    outputs = {'requests.jsonl': requests, 'labels.jsonl': labels, 'lineage.jsonl': lineage,
               'held_ia.jsonl': holds, 'source_evidence.jsonl': read(PACKET / 'sources.jsonl')}
    for name, rows in outputs.items():
        write(OUT / name, rows)
    (OUT / 'builder_snapshot.py').write_bytes(Path(__file__).read_bytes())
    inputs = [selection_path, query_path, split_path, index_path, REVIEW / 'review_manifest.json',
              REVIEW / 'ia_review.jsonl', REVIEW / 'masked_review.jsonl', INTEGRATION / 'structural_validation.json',
              INTEGRATION / 'ia_local_amendments.jsonl', INTEGRATION / 'ia_dispositions.jsonl',
              INTEGRATION / 'masked_triage.jsonl', PACKET / 'sources.jsonl', Path(__file__).resolve()]
    manifest = {'version_id': VERSION, 'parent_bank_id': 'ag_news_queries_v2', 'parent_split_id': 'ag_news_threshold_v2',
                'source_run_id': '20260717-ag-news-four-medium', 'partition': 'train',
                'status': 'provisional_attack_drafts_pending_human_gold_and_adapter',
                'formal_effect_eligible': False, 'human_gold_complete': False, 'replay_eligible': False,
                'attack_query_counts': counts, 'requests': len(requests), 'source_documents': len({r['doc_id'] for r in labels}),
                'held_ia': len(holds), 'ia_ground_truth_counts': dict(Counter(r['ground_truth'] for r in labels if r['attack_type'] == 'ia')),
                'session_layout': 'one-query provisional sessions; not original multi-turn history or final replay allocation',
                'input_sha256': {p.relative_to(ROOT).as_posix(): sha(p) for p in inputs},
                'output_sha256': {name: sha(OUT / name) for name in [*outputs, 'builder_snapshot.py']},
                'limits': ['Targeted attack-only draft overlay; no normal gold, no acceptance of other 2169 IA or Direct/S2 semantics.',
                          '62 IA are suggestions after local triage, not accepted human gold; five original rewrites held, six locally amended.',
                          '115 model rejects and 24 uncertain items retained, not permanently deleted.',
                          'Three digit-containing, seven casefold-duplicate Masked schemes and other source warnings remain flagged.',
                          'New question/answer identities require fresh traces; source index and frozen Judge identity remain original.',
                          'No model calls, attack effectiveness or defense evaluation executed.']}
    (OUT / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'requests': len(requests), 'attack_counts': counts, 'held_ia': len(holds), 'status': manifest['status']}))


if __name__ == '__main__':
    main()
