"""Fix a small real-model ablation cohort before candidate results are observed."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path

ROOT = Path.cwd()
PRIMARY = ROOT / 'data/defense_datasets/next_goal_v2_train_20261117_01'
NORMAL = ROOT / 'data/defense_datasets/next_goal_ia_style_normal_20261117_01'
ATTACK = ROOT / 'data/defense_datasets/multi_action_sources_v2_train_20261117_01'
OUT = ROOT / 'data/defense_datasets/next_goal_ablation_v2_train_20261117_01'
ATTACK_IDS = ['ls_ed05edb2468d8b76077b713b', 'ls_7320d138516429cbb045a291',
              'ls_7e5e4e48bf338d0fd381ad84', 'vr_787d24f61245772af483db82']


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def rows(path):
    return [json.loads(x) for x in path.read_text(encoding='utf8').splitlines() if x.strip()]


def main():
    for parent in (PRIMARY, NORMAL, ATTACK):
        manifest = json.loads((parent / 'manifest.json').read_text(encoding='utf8'))
        for name, expected in manifest['output_sha256'].items():
            assert digest(parent / name) == expected, (parent, name)
    output = {name: [] for name in ('requests', 'labels', 'lineage', 'normal_rubric')}
    for parent, wanted in ((ATTACK, set(ATTACK_IDS)), (NORMAL, None)):
        labels = {x['request_id']: x for x in rows(parent / 'labels.jsonl')}
        requests = rows(parent / 'requests.jsonl')
        selected = [x for x in requests if wanted is None or x['request_id'] in wanted]
        for request in selected:
            rid = request['request_id']
            output['requests'].append(request)
            output['labels'].append(labels[rid])
            output['lineage'].append({'request_id': rid, 'source_doc_id': labels[rid]['doc_id'],
                                      'turn': 1, 'source_cohort': parent.name})
        if parent == NORMAL:
            output['normal_rubric'].extend(rows(parent / 'normal_rubric.jsonl'))
    assert len(output['requests']) == 8 and len(output['normal_rubric']) == 4
    OUT.mkdir(exist_ok=False)
    for name, values in output.items():
        with (OUT / (name + '.jsonl')).open('x', encoding='utf8') as f:
            for value in values:
                f.write(json.dumps(value, ensure_ascii=False) + '\n')
    spec = deepcopy(json.loads((PRIMARY / 'experiment_spec.json').read_text(encoding='utf8')))
    spec.update(experiment_id='T10D-next-goal-component-ablation',
                methods=['B_TYPE_V2', 'B_NEXT_GOAL', 'B_NEXT_CUE_ONLY', 'B_NEXT_IA_ONLY'],
                requests_path=str(OUT / 'requests.jsonl'), labels_path=str(OUT / 'labels.jsonl'))
    for name in ('normal_rubric', 'lineage'):
        spec['identity_files'][name] = str(OUT / (name + '.jsonl'))
    spec['identity_files']['cohort_manifest'] = str(OUT / 'manifest.json')
    (OUT / 'experiment_spec.json').write_text(json.dumps(spec, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    manifest = {'version_id': OUT.name, 'bank_id': 'ag_news_queries_v2', 'split_id': 'ag_news_threshold_v2',
                'partition': 'train', 'analysis_role': 'engineering_only', 'human_gold_complete': False,
                'formal_effect_eligible': False, 'request_count': 8, 'expected_events': 32,
                'methods': spec['methods'],
                'input_sha256': {str(p / 'manifest.json'): digest(p / 'manifest.json') for p in (PRIMARY, NORMAL, ATTACK)},
                'output_sha256': {x.name: digest(x) for x in sorted(OUT.iterdir())},
                'selection': 'Four already observed missed attacks and four preselected ordinary yes/no reading controls; fixed before full-candidate outputs.',
                'limits': ['Prior attack cases deliberately selected from known failures; not an unbiased test.',
                           'Normal intent and references are agent assessments and require human review.',
                           'One-turn ablation isolates rule components but not multi-turn history effects.']}
    (OUT / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    print('Frozen 8 requests, 4 methods, 32 events:', OUT)


if __name__ == '__main__':
    main()
