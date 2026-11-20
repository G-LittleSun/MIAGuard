"""Freeze a small source-distinct train diagnostic before generating answers."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCREEN = ROOT / 'reports/defense_v1/T10/rank_stress_20261109_01/retrieval_screen.jsonl'
INDEX = ROOT / 'data/vector_stores/20260717-ag-news-four-medium/ag_news/documents.jsonl'
OLD = [ROOT / 'data/defense_datasets/legacy_v2_fast_pilot_20261105_01',
       ROOT / 'data/defense_datasets/legacy_v2_rank_stress_20261109_01']
OUT = ROOT / 'data/defense_datasets/locator_new_sources_20261111_01'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]


def main():
    prior_manifest = json.loads((OLD[1] / 'manifest.json').read_text(encoding='utf-8'))
    assert sha(SCREEN) == prior_manifest['input_sha256']['reports\\defense_v1\\T10\\rank_stress_20261109_01\\retrieval_screen.jsonl']
    assert sha(INDEX) == prior_manifest['input_sha256']['data\\vector_stores\\20260717-ag-news-four-medium\\ag_news\\documents.jsonl']
    for directory in OLD:
        manifest = json.loads((directory / 'manifest.json').read_text(encoding='utf-8'))
        assert sha(directory / 'labels.jsonl') == manifest['output_sha256']['labels.jsonl']
    excluded = {row['doc_id'] for directory in OLD for row in rows(directory / 'labels.jsonl')}
    texts = {r['doc_id']: r['text'] for r in rows(INDEX)}
    candidates = rows(SCREEN)
    selected = []
    for kind in ('direct_rag_mia', 's2_mia', 'masked_mia'):
        pool = [r for r in candidates if r['attack_type'] == kind and r['doc_id'] not in excluded
                and r['target_rank'] == 1 and (kind == 'masked_mia' or ':canonical:' in r['source_id'])]
        pool.sort(key=lambda r: hashlib.sha256(('locator-sources-v1:' + r['source_id']).encode()).hexdigest())
        count = 0
        for row in pool:
            if row['doc_id'] in excluded:
                continue
            if kind == 'masked_mia':
                answers = row['payload']['answers']
                if 'Passage:' not in row['query'] or len(answers) != 5:
                    continue
                restored = row['query'].split('Passage:', 1)[1].strip()
                for i, answer in enumerate(answers, 1):
                    token = f'[Mask_{i}]'
                    if restored.count(token) != 1:
                        break
                    restored = restored.replace(token, answer)
                if restored != texts[row['doc_id']].strip():
                    continue
            selected.append(row)
            excluded.add(row['doc_id'])
            count += 1
            if count == 2:
                break
        if count != 2:
            raise ValueError(f'Insufficient eligible sources for {kind}')
    if OUT.exists():
        raise FileExistsError(OUT)
    OUT.mkdir()
    requests, labels, lineage = [], [], []
    for row in selected:
        ident = hashlib.sha256((OUT.name + ':' + row['source_id']).encode()).hexdigest()[:24]
        request_id = 'ls_' + ident
        requests.append({'request_id': request_id, 'session_id': 'lss_' + ident, 'query': row['query']})
        label = {'request_id': request_id, 'doc_id': row['doc_id'], 'traffic_type': 'attack',
                 'attack_type': row['attack_type'], 'membership_label': 1,
                 'human_reviewed': False, 'formal_effect_eligible': False}
        if row['attack_type'] == 's2_mia':
            label['target_text'] = texts[row['doc_id']]
        if row['attack_type'] == 'masked_mia':
            label['answers'] = row['payload']['answers']
        labels.append(label)
        lineage.append({'request_id': request_id, 'source_id': row['source_id'],
                        'target_rank_screen': row['target_rank'], 'retrieved_doc_ids_screen': row['retrieved_doc_ids']})
    for name, data in [('requests', requests), ('labels', labels), ('lineage', lineage)]:
        (OUT / f'{name}.jsonl').write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in data), encoding='utf-8')
    spec = json.loads((OLD[1] / 'experiment_spec.json').read_text(encoding='utf-8'))
    spec.update(experiment_id='T10D-locator-source-diagnostic', methods=['B0', 'B2', 'B5', 'B5_LOCATED'],
                requests_path=str(OUT / 'requests.jsonl'), labels_path=str(OUT / 'labels.jsonl'))
    spec['identity_files']['lineage'] = str(OUT / 'lineage.jsonl')
    spec['identity_files']['selection_builder'] = str(Path(__file__))
    (OUT / 'experiment_spec.json').write_text(json.dumps(spec, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    manifest = {'version_id': OUT.name, 'analysis_role': 'engineering_only', 'formal_effect_eligible': False,
                'human_gold_complete': False, 'selection': 'Two rank-one member examples per type on distinct source document IDs, deterministic hash order; excluded both previous pilot source sets; no generation outcomes consulted.',
                'limitations': ['Distinct document IDs do not establish event independence.', 'All target documents rank first; not a rank stress test.', 'No normal or nonmember samples in this batch.', 'Pending model review and human gold.'],
                'input_sha256': {str(p.relative_to(ROOT)).replace('\\', '/'): sha(p) for p in (SCREEN, INDEX, OLD[0] / 'manifest.json', OLD[1] / 'manifest.json', Path(__file__))},
                'output_sha256': {p.name: sha(p) for p in OUT.iterdir() if p.is_file()}}
    (OUT / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('Fixed', len(requests), 'requests on', len({r['doc_id'] for r in labels}), 'source IDs')


if __name__ == '__main__':
    main()
