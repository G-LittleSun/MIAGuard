"""Freeze a small engineering smoke test of the utility evidence pipeline."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path.cwd()
PARENT = ROOT / 'data/defense_datasets/next_goal_v2_train_20261117_01'
PILOT = ROOT / 'reports/defense_v1/T10/utility48_annotation_pilot_20261117.jsonl'
OUT = ROOT / 'data/defense_datasets/utility48_smoke_20261117_01'

def digest(path):
    return sha256(path.read_bytes()).hexdigest()

def main():
    base_manifest = json.loads((PARENT/'manifest.json').read_text(encoding='utf-8'))
    for name, expected in base_manifest['output_sha256'].items():
        assert digest(PARENT/name) == expected
    full = '--full' in sys.argv
    pilot = PILOT.with_name('utility48_annotation_draft_20261117.jsonl') if full else PILOT
    out = ROOT / 'data/defense_datasets/utility48_v2_train_20261117_01' if full else OUT
    cases = [json.loads(line) for line in pilot.read_text(encoding='utf-8').splitlines()]
    # One case from each category verifies the interface, not the final 48-item scoring.
    if not full:
        cases = [cases[i] for i in (0, 3, 6, 9)]
    out.mkdir(exist_ok=False)
    requests, labels, lineage, rubrics = [], [], [], []
    for case in cases:
        rid = case['request_id'] + ('_main' if full else '_smoke')
        requests.append({'request_id':rid, 'session_id':rid, 'query':case['query'], 'allowed_doc_ids':case['allowed_doc_ids']})
        facts = case['required_facts']
        labels.append({'request_id':rid, 'doc_id':case['target_doc_id'], 'attack_type':'benign',
                       'traffic_type':'benign', 'answerable':case['answerable'],
                       'reference_answer':case.get('reference_answer', facts[0]['fact'] if facts else None),
                       'gold_evidence_ids':[case['target_doc_id']] if facts else [],
                       'human_reviewed':False, 'formal_effect_eligible':False})
        lineage.append({'request_id':rid, 'source_doc_id':case['target_doc_id'], 'source_kind':'pilot_draft', 'turn':1})
        rubrics.append(dict(case, request_id=rid))
    for name, data in [('requests',requests),('labels',labels),('lineage',lineage),('normal_rubric',rubrics)]:
        (out/(name+'.jsonl')).write_text(''.join(json.dumps(x, ensure_ascii=False)+'\n' for x in data),encoding='utf-8')
    config = deepcopy(json.loads((PARENT/'experiment_spec.json').read_text(encoding='utf-8')))
    config.update(experiment_id='T10D-utility48-main' if full else 'T10D-utility48-smoke', methods=['B0','B_TYPE_V2'],
                  requests_path=str(out/'requests.jsonl'), labels_path=str(out/'labels.jsonl'))
    for name in ('lineage','normal_rubric'):
        config['identity_files'][name] = str(out/(name+'.jsonl'))
    config['identity_files']['cohort_manifest'] = str(out/'manifest.json')
    scoring = ROOT/'reports/defense_v1/T10/UTILITY48_SCORING_DRAFT_ZH.md'
    if full:
        (out/'scoring_protocol_zh.md').write_bytes(scoring.read_bytes())
    (out/'experiment_spec.json').write_text(json.dumps(config,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    manifest = {'version_id':out.name,'partition':'train','analysis_role':'engineering_only' if full else 'engineering_smoke',
                'human_gold_complete':False,'formal_effect_eligible':False,'request_count':len(cases),
                'methods':config['methods'],'expected_events':len(cases)*2,
                'input_sha256':{str(p):digest(p) for p in [pilot,PARENT/'manifest.json',Path(__file__).resolve(),scoring]},
                'output_sha256':{p.name:digest(p) for p in out.iterdir()},
                'limitations':(['Agent-authored questions and references, not human gold.',
                                'Repeated event sources; 48 queries are not independent events.',
                                'Simulated per-query allowlists; supplementary indexed documents outside query split.']
                               if full else ['Four draft questions; no final annotations or effect evaluation.',
                                             'Simulated per-query allowlists, supplementary indexed document outside query split.'])}
    (out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Frozen questions:', len(cases), 'expected events:', len(cases)*2, 'at', out)

if __name__ == '__main__':
    main()
