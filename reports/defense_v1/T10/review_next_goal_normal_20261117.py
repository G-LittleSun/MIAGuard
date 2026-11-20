"""Persist agent review of the actual normal answer/evidence groups."""
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path

REPORT = Path('reports/defense_v1/T10')
SOURCE = REPORT / 'next_goal_normal_review_units_20261117.json'
AUDIT = REPORT / 'next_goal_paired_audit_20261117.json'
OUT = REPORT / 'next_goal_normal_agent_review_20261117.json'


def main():
    source = json.loads(SOURCE.read_text(encoding='utf8'))
    units = source['units']
    assert len(units) == 19 and not source['review_complete']
    cases = {(x['method'], x['request_id']): x for x in json.loads(AUDIT.read_text(encoding='utf8'))['cases']}
    reviewed = []
    for i, unit in enumerate(units):
        rid = unit['request_id']
        if rid == 'ng_normal_02':
            assert i == 1 and 'antivirus vendor' in unit['response']
            correct, insufficient = False, None
            reason = 'reference raw delivered; response confuses Symantec and Veritas'
        elif not unit['answerable']:
            assert i in (13, 14) and 'insufficient' in unit['response'].lower()
            assert all(doc in {x['parent_doc_id'] for x in unit['delivered_evidence']} for doc in unit['gold_evidence_ids'])
            correct, insufficient, reason = None, True, 'source lacks requested fact; response says evidence insufficient'
        elif i < 13:
            assert unit['action'] == 'allow'
            assert all(doc in {x['parent_doc_id'] for x in unit['delivered_evidence']} for doc in unit['gold_evidence_ids'])
            correct, insufficient, reason = True, None, 'required facts answered with source delivered'
        else:
            assert rid in ('bp_treo_3', 'bp_ace_1', 'bp_oklahoma_1')
            assert all(cases[m, rid]['reference_retrieved'] for m in unit['methods'])
            correct, insufficient = False, None
            reason = {'deny': 'retrieved source withheld by refusal',
                      'hide_target_refill': 'retrieved source removed by filtering'}[unit['action']]
        reviewed.append({'unit_index': i, 'request_id': rid, 'methods': unit['methods'],
                         'answerable': unit['answerable'], 'correct_supported': correct,
                         'reasonable_insufficient_answer': insufficient, 'reason': reason})
    summary = {}
    for method in ('B0', 'B2', 'B_TYPE_V2', 'B_NEXT_GOAL'):
        group = [x for x in reviewed if method in x['methods']]
        assert len(group) == 15
        summary[method] = {'answerable': sum(x['answerable'] for x in group),
                           'correct_supported': sum(x['correct_supported'] is True for x in group),
                           'insufficient': sum(not x['answerable'] for x in group),
                           'reasonable_insufficient': sum(x['reasonable_insufficient_answer'] is True for x in group),
                           'failures': dict(Counter(x['reason'] for x in group if x['correct_supported'] is False))}
    value = {'reviewer_kind': 'llm_agent', 'human_reviewed': False, 'formal_effect_eligible': False,
             'units_sha256': sha256(SOURCE.read_bytes()).hexdigest(), 'audit_sha256': sha256(AUDIT.read_bytes()).hexdigest(),
             'summary': summary, 'units': reviewed,
             'limitations': ['Agent judgments and selected development data; human gold pending.',
                             'Historical Treo session has prior exposure and is not independent of its earlier turns.']}
    with OUT.open('x', encoding='utf8') as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.write('\n')
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == '__main__':
    main()
