"""Freeze a traceable engineering cohort from existing reviewed development fixtures."""
from collections import Counter
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path

ROOT = Path.cwd()
OUT = ROOT / 'data/defense_datasets/two_hour_paired_v2_train_20261117_01'

def digest(path):
    return sha256(path.read_bytes()).hexdigest()

def read(path):
    return json.loads(path.read_text(encoding='utf8'))

def rows(path):
    return [json.loads(line) for line in path.read_text(encoding='utf8').splitlines() if line.strip()]

def write(path, value):
    with path.open('x', encoding='utf8') as handle:
        handle.write(json.dumps(value, ensure_ascii=False, indent=2) + '\n')

def main():
    parents = [ROOT / 'data/defense_datasets' / n for n in (
        'type_policy_v2_train_20261113_01', 'multiturn_ia_session_v2_train_20261113_01',
        'benign_pair_v2_train_20261113_01')]
    inputs = {}
    for parent in parents:
        manifest = read(parent / 'manifest.json')
        inputs[str(parent / 'manifest.json')] = digest(parent / 'manifest.json')
        for name, expected in manifest['output_sha256'].items():
            path = parent / name
            assert digest(path) == expected, path
            inputs[str(path)] = expected
    baseline = ROOT / 'data/defense_v1_runs/type-policy-v2-paired-20261113-01'
    manifest = read(baseline / 'run_manifest.json')
    spec = read(baseline / 'experiment_spec.json')
    for key, path in spec['identity_files'].items():
        assert digest(Path(path)) == manifest['files_sha256']['identity:' + key], key
    for key, expected in manifest['files_sha256'].items():
        if key.startswith('code:'):
            name = key.split(':', 1)[1]
            path = ROOT / ('scripts' if name == 'run_defense_v1_benchmark.py' else 'src/miaguard') / name
            assert digest(path) == expected, path
    requests, labels, lineage, rubric = [], [], [], []
    for i, parent in enumerate(parents):
        by_label = {r['request_id']: r for r in rows(parent / 'labels.jsonl')}
        by_lineage = {r['request_id']: r for r in rows(parent / 'lineage.jsonl')}
        by_rubric = {r['request_id']: r for r in rows(parent / 'normal_rubric.jsonl')}
        for request in rows(parent / 'requests.jsonl'):
            rid = request['request_id']
            label = by_label[rid]
            if i == 0 and label['attack_type'] == 'benign':
                continue
            if i == 1 and label['attack_type'] != 'ia':
                continue
            requests.append(request); labels.append(label); lineage.append(by_lineage[rid])
            if label['attack_type'] == 'benign':
                rubric.append(by_rubric[rid])
    assert len(requests) == 41 and len({r['request_id'] for r in requests}) == 41
    assert all(set(r) == {'request_id', 'session_id', 'query'} for r in requests)
    counts = Counter((r['attack_type'], r.get('membership_label')) for r in labels)
    for kind in ('direct_rag_mia', 's2_mia', 'masked_mia', 'ia'):
        assert counts[kind, 0] and counts[kind, 1], kind
    OUT.mkdir(exist_ok=False)
    for name, values in [('requests', requests), ('labels', labels), ('lineage', lineage), ('normal_rubric', rubric)]:
        with (OUT / (name + '.jsonl')).open('x', encoding='utf8') as handle:
            for value in values:
                handle.write(json.dumps(value, ensure_ascii=False) + '\n')
    spec = deepcopy(spec)
    spec.update(experiment_id='T10D-two-hour-paired', methods=['B0', 'B2', 'B_TYPE_V2'],
                requests_path=str(OUT / 'requests.jsonl'), labels_path=str(OUT / 'labels.jsonl'))
    for key in ('normal_rubric', 'lineage'):
        spec['identity_files'][key] = str(OUT / (key + '.jsonl'))
    spec['identity_files']['cohort_manifest'] = str(OUT / 'manifest.json')
    write(OUT / 'experiment_spec.json', spec)
    inputs[str(Path(__file__).resolve())] = digest(Path(__file__))
    inputs[str(baseline / 'run_manifest.json')] = digest(baseline / 'run_manifest.json')
    write(OUT / 'manifest.json', {'version_id': OUT.name, 'partition': 'train',
        'bank_id': 'ag_news_queries_v2', 'split_id': 'ag_news_threshold_v2',
        'analysis_role': 'engineering_only', 'human_gold_complete': False, 'formal_effect_eligible': False,
        'selection': 'All 15 attacks from frozen type-policy cohort, all 12 IA requests from four frozen three-turn sessions, and all 14 normal questions from frozen benign cohort. Selection precedes this run. Previously inspected development cases; source dependence remains.',
        'counts': {str(k): v for k, v in counts.items()}, 'expected_requests': len(requests),
        'expected_events': len(requests)*3, 'input_sha256': inputs,
        'output_sha256': {p.name: digest(p) for p in sorted(OUT.iterdir())},
        'limitations': ['Prior outputs and sources inspected; non-independent engineering cohort.',
                        'IA mixes single and three-turn budgets; report separately.',
                        'Normal correctness uses provisional agent review and authorization is unknown.']})
    print('Frozen', OUT, 'counts', counts, 'events', len(requests)*3)

if __name__ == '__main__':
    main()
