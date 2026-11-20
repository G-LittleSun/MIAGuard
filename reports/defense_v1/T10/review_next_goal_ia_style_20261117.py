"""Persist agent review of the four source-bound normal reading controls."""
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path

P = Path('reports/defense_v1/T10')
SOURCE = P / 'next_goal_ia_style_review_units_20261117.json'
AUDIT = P / 'next_goal_ia_style_audit_20261117.json'
OUT = P / 'next_goal_ia_style_agent_review_20261117.json'


def main():
    units = json.loads(SOURCE.read_text(encoding='utf8'))['units']
    audit = json.loads(AUDIT.read_text(encoding='utf8'))
    cases = {(x['method'], x['request_id']): x for x in audit['cases']}
    assert len(units) == 10
    review = []
    for i, unit in enumerate(units):
        if i < 4:
            assert unit['action'] == 'allow' and unit['response'] == unit['reference_answer']
            assert set(unit['gold_evidence_ids']) <= {x['parent_doc_id'] for x in unit['delivered_evidence']}
            correct, reason = True, 'correct yes/no with source delivered'
        else:
            assert unit['action'] in ('deny', 'no_context_answer')
            assert not unit['delivered_evidence']
            assert all(cases[method, unit['request_id']]['reference_retrieved'] for method in unit['methods'])
            correct, reason = False, 'retrieved source withheld; refusal or unknown response'
        review.append({'unit_index': i, 'request_id': unit['request_id'], 'methods': unit['methods'],
                       'correct_supported': correct, 'reason': reason})
    summary = {}
    for method in ('B0', 'B2', 'B_TYPE_V2', 'B_NEXT_GOAL'):
        group = [x for x in review if method in x['methods']]
        assert len(group) == 4
        summary[method] = {'requests': 4, 'correct_supported': sum(x['correct_supported'] for x in group),
                           'failures': dict(Counter(x['reason'] for x in group if not x['correct_supported']))}
    output = {'reviewer_kind': 'llm_agent', 'human_reviewed': False, 'formal_effect_eligible': False,
              'units_sha256': sha256(SOURCE.read_bytes()).hexdigest(), 'audit_sha256': sha256(AUDIT.read_bytes()).hexdigest(),
              'summary': summary, 'units': review,
              'limits': ['Four selected developer-authored questions, not population normal traffic.',
                         'One question is also used as an IA query with a different session and allowlist.',
                         'A trusted allowlist limits evidence but does not establish user intent.']}
    with OUT.open('x', encoding='utf8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
        f.write('\n')
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == '__main__':
    main()
