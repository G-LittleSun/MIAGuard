"""Decision-only ablation on first turns of the completed paired run."""
from collections import Counter, defaultdict
from hashlib import sha256
import json
from pathlib import Path
import re

from miaguard.query_cue import query_cues

RUN = Path('data/defense_v1_runs/next-goal-paired-20261117-01')
COHORT = Path('data/defense_datasets/next_goal_v2_train_20261117_01')
PREREG = Path('reports/defense_v1/T10/next_goal_ablation_prereg_20261117.json')
OUT = Path('reports/defense_v1/T10/next_goal_first_turn_ablation_20261117.json')


def rows(path):
    return [json.loads(x) for x in path.read_text(encoding='utf8').splitlines() if x.strip()]


def main():
    manifest = json.loads((RUN / 'run_manifest.json').read_text(encoding='utf8'))
    assert manifest['status'] == 'completed'
    prereg = json.loads(PREREG.read_text(encoding='utf8'))
    assert sha256((COHORT / 'manifest.json').read_bytes()).hexdigest() == prereg['dataset_manifest_sha256']
    requests = {x['request_id']: x for x in rows(RUN / 'requests.jsonl')}
    labels = {x['request_id']: x for x in rows(RUN / 'labels.jsonl')}
    lineage = {x['request_id']: x for x in rows(COHORT / 'lineage.jsonl')}
    events = {(x['method'], x['request_id']): x for x in rows(RUN / 'events.jsonl')}
    results = []
    for rid, request in requests.items():
        if lineage[rid]['turn'] != 1:
            continue
        base, candidate = events['B_TYPE_V2', rid], events['B_NEXT_GOAL', rid]
        if base['status'] != 'complete' or candidate['status'] != 'complete':
            results.append({'request_id': rid, 'status': 'failed', 'traffic': labels[rid]['attack_type']})
            continue
        base_risk = base['risk']['frozen_risk']
        candidate_risk = candidate['risk']['frozen_risk']
        comparable = all(base_risk.get(k) == candidate_risk.get(k) for k in ('status', 'risk_source', 'score', 'triggered'))
        query = request['query']
        cues = set(query_cues(query))
        presence = bool(re.search(r'\b(?:article|report)\b', query, re.I)
                        and re.search(r'\b(?:yes\s*,\s*no\s*,?\s*or\s*unknown)\b', query, re.I))
        base_action = base['action']
        cue_action = base_action
        ia_action = base_action
        if comparable and base_risk.get('status') == 'ok' and base_risk.get('triggered') is False:
            if cues & {'quoted_context_check', 'masked_recovery'}:
                cue_action = 'deny'
            if presence:
                ia_action = 'no_context_answer'
        expected_full = cue_action if cue_action != base_action else ia_action
        status = 'ok' if comparable and expected_full == candidate['action'] else 'incomparable'
        results.append({'request_id': rid, 'traffic': labels[rid]['attack_type'], 'status': status,
                        'risk_comparable': comparable, 'cue_signals': sorted(cues), 'ia_format': presence,
                        'v2_action': base_action, 'cue_only_action': cue_action, 'ia_only_action': ia_action,
                        'expected_full_action': expected_full, 'actual_full_action': candidate['action']})
    grouped = defaultdict(Counter)
    for row in results:
        grouped[row['traffic']]['total'] += 1
        grouped[row['traffic']][row['status']] += 1
        if row['status'] == 'ok':
            for name in ('cue_only_action', 'ia_only_action', 'actual_full_action'):
                grouped[row['traffic']][name + '_changed'] += row[name] != row['v2_action']
    output = {'analysis_role': 'engineering_only', 'prereg_sha256': sha256(PREREG.read_bytes()).hexdigest(),
              'events_sha256': sha256((RUN / 'events.jsonl').read_bytes()).hexdigest(),
              'scope': prereg['scope'], 'limitations': prereg['limits'],
              'by_traffic': dict(grouped), 'cases': results}
    with OUT.open('x', encoding='utf8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
        f.write('\n')
    print(json.dumps(output['by_traffic'], ensure_ascii=False))


if __name__ == '__main__':
    main()
