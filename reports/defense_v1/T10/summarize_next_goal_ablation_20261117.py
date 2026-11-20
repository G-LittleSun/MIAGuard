"""Summarize actual single-turn ablation results with paired denominators."""
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path

REPORT = Path('reports/defense_v1/T10')
AUDIT = REPORT / 'next_goal_ablation_audit_20261117.json'
OUT = REPORT / 'next_goal_ablation_summary_20261117.json'
METHODS = ('B_TYPE_V2', 'B_NEXT_GOAL', 'B_NEXT_CUE_ONLY', 'B_NEXT_IA_ONLY')


def main():
    audit = json.loads(AUDIT.read_text(encoding='utf8'))
    summary = {}
    for method in METHODS:
        cases = [x for x in audit['cases'] if x['method'] == method]
        attack = [x for x in cases if x['traffic'] != 'benign']
        normal = [x for x in cases if x['traffic'] == 'benign']
        assert len(attack) == len(normal) == 4 and all(x['status'] == 'complete' for x in cases)
        answers = [{'request_id': x['request_id'],
                    'correct_supported': x['response'].strip().casefold() == x['reference_answer'].strip().casefold()
                    and x['reference_raw_delivered'],
                    'response': x['response'], 'reference_answer': x['reference_answer'],
                    'reference_raw_delivered': x['reference_raw_delivered']} for x in normal]
        summary[method] = {'attack_count': 4, 'attack_target_raw_delivered': sum(x['reference_raw_delivered'] for x in attack),
                           'attack_actions': dict(Counter(x['action'] for x in attack)),
                           'attack_outputs': dict(Counter(x['yes_no_unknown'] or ('deny' if x['action'] == 'deny' else 'other') for x in attack)),
                           'masked_matched': sum((x['masked'] or {}).get('matched') or 0 for x in attack),
                           'masked_slots': sum((x['masked'] or {}).get('total') or 0 for x in attack),
                           'normal_count': len(normal), 'normal_correct_supported': sum(x['correct_supported'] for x in answers),
                           'normal_interventions': sum(x['action'] not in ('allow', 'unavailable') for x in normal),
                           'normal_cases': answers}
    value = {'analysis_role': 'engineering_only', 'human_reviewed': False, 'formal_effect_eligible': False,
             'audit_sha256': sha256(AUDIT.read_bytes()).hexdigest(), 'summary': summary,
             'limitations': ['Four known-failure attacks and four agent-authored normal controls; intentionally selected.',
                             'Only single turns; no causal measurement of multi-turn escalation.',
                             'Four yes/no normal responses assessed against raw source; human review remains pending.']}
    with OUT.open('x', encoding='utf8') as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.write('\n')
    print(json.dumps({k: {a: b for a, b in v.items() if a != 'normal_cases'} for k, v in summary.items()}, ensure_ascii=False))


if __name__ == '__main__':
    main()
