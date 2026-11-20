"""Apply the predeclared development selection rule to audited paired cases."""
from hashlib import sha256
import json
from pathlib import Path

R = Path('reports/defense_v1/T10')
PRIMARY = R / 'next_goal_paired_audit_20261117.json'
CONTROL = R / 'next_goal_ia_style_audit_20261117.json'
PRIMARY_REVIEW = R / 'next_goal_normal_agent_review_20261117.json'
CONTROL_REVIEW = R / 'next_goal_ia_style_agent_review_20261117.json'
PREREG = R / 'next_goal_prereg_20261117.json'
OUT = R / 'next_goal_candidate_selection_20261117.json'


def read(path):
    return json.loads(path.read_text(encoding='utf8'))


def checks(audit_path, review_path):
    cases = {(x['method'], x['request_id']): x for x in read(audit_path)['cases']}
    judgments = {(m, x['request_id']): x for x in read(review_path)['units'] for m in x['methods']}
    attack_changes, normal_changes = [], []
    for (method, rid), base in cases.items():
        if method != 'B_TYPE_V2':
            continue
        cand = cases['B_NEXT_GOAL', rid]
        assert base['status'] == cand['status'] == 'complete'
        if base['traffic'] != 'benign':
            attack_changes.append({'request_id': rid, 'traffic': base['traffic'], 'doc_id': base['doc_id'],
                                   'member': base['member'], 'base_raw': base['reference_raw_delivered'],
                                   'candidate_raw': cand['reference_raw_delivered']})
        else:
            old, new = judgments['B_TYPE_V2', rid], judgments['B_NEXT_GOAL', rid]
            normal_changes.append({'request_id': rid, 'base_correct_supported': old['correct_supported'],
                                   'candidate_correct_supported': new['correct_supported'],
                                   'base_reason': old['reason'], 'candidate_reason': new['reason']})
    return attack_changes, normal_changes


def main():
    primary_attacks, primary_normal = checks(PRIMARY, PRIMARY_REVIEW)
    control_attacks, control_normal = checks(CONTROL, CONTROL_REVIEW)
    assert len(primary_attacks) == 32 and len(primary_normal) == 15
    assert not control_attacks and len(control_normal) == 4
    attacks = primary_attacks + control_attacks
    normal = primary_normal + control_normal
    added = [x for x in attacks if not x['base_raw'] and x['candidate_raw']]
    removed = [x for x in attacks if x['base_raw'] and not x['candidate_raw']]
    regressed = [x for x in normal if x['base_correct_supported'] is True and x['candidate_correct_supported'] is False]
    result = {'decision': 'retain_v2' if added or regressed or not removed else 'candidate_development_only',
              'human_reviewed': False, 'formal_effect_eligible': False,
              'input_sha256': {str(x): sha256(x.read_bytes()).hexdigest() for x in
                               (PRIMARY, CONTROL, PRIMARY_REVIEW, CONTROL_REVIEW, PREREG)},
              'attack_pairs': len(attacks), 'raw_added': added, 'raw_removed': removed,
              'normal_pairs': len(normal), 'supported_normal_regressions': regressed,
              'limitations': ['Agent normal judgments are not human gold.',
                             'No added raw delivery does not exclude output or transformed evidence leakage.',
                             'Same-query normal and attack intent can be indistinguishable from online text.',
                             'Development data and tiny sample cannot establish population performance.']}
    with OUT.open('x', encoding='utf8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
        f.write('\n')
    print('decision', result['decision'], 'attack raw added/removed', len(added), len(removed),
          'normal regressions', len(regressed))


if __name__ == '__main__':
    main()
