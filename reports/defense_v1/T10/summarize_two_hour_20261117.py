"""Summarize completed paired replay using its audited events and prior agent judgments."""
from collections import Counter, defaultdict
from hashlib import sha256
import json
from pathlib import Path
from statistics import median
from sklearn.metrics import roc_auc_score

ROOT = Path.cwd()
REPORT = ROOT / 'reports/defense_v1/T10'
RUN = ROOT / 'data/defense_v1_runs/two-hour-paired-20261117-01'

def read(path):
    return json.loads(path.read_text(encoding='utf8'))

def rows(path):
    return [json.loads(line) for line in path.read_text(encoding='utf8').splitlines() if line.strip()]

def main():
    audit_path = REPORT / 'two_hour_paired_audit_20261117.json'
    audit = read(audit_path)
    prior = read(REPORT / 'benign_pair_review_20261113.json')
    judgments = {}
    for group in prior['review_groups']:
        for method in group['methods']:
            judgments[group['request_id'], method] = group
    cases = audit['cases']
    normal = [r for r in cases if r['traffic'] == 'benign']
    attacks = [r for r in cases if r['traffic'] != 'benign']
    summary = {}
    for method in ('B0', 'B2', 'B_TYPE_V2'):
        group = [r for r in normal if r['method'] == method]
        assessed = []
        for row in group:
            old = judgments[row['request_id'], method]
            same = (row['response'] == old['response'] and row['action'] == old['action'] and
                    row['reference_raw_delivered'] == old['reference_delivered'])
            assessed.append({'request_id': row['request_id'], 'matched_prior_review': same,
                             'correct_supported': old['correct_supported'] if same else None,
                             'response': row['response'], 'action': row['action'],
                             'reference_delivered': row['reference_raw_delivered']})
        times = [r['latency_ms'] for r in group]
        summary[method] = {'requests': len(group), 'review_matched': sum(x['matched_prior_review'] for x in assessed),
                           'correct_supported_known': sum(x['correct_supported'] is True for x in assessed),
                           'needs_agent_review': [x['request_id'] for x in assessed if not x['matched_prior_review']],
                           'interventions': sum(r['action'] not in ('allow', 'unavailable') for r in group),
                           'denials': sum(r['action'] == 'deny' for r in group),
                           'latency_p50_ms': median(times), 'cases': assessed}
    by_group = defaultdict(list)
    for row in attacks:
        by_group[row['method'], row['traffic'], row['member']].append(row)
    groups = []
    for (method, kind, member), group in sorted(by_group.items()):
        groups.append({'method': method, 'attack': kind, 'member': member,
                       'requests': len(group), 'distinct_documents': len({r['doc_id'] for r in group}),
                       'actions': dict(Counter(r['action'] for r in group)),
                       'responses': dict(Counter(r['yes_no_unknown'] or ('deny' if r['action'] == 'deny' else 'other') for r in group)),
                       'reference_raw_delivered': sum(r['reference_raw_delivered'] for r in group),
                       'masked_matched_slots': sum((r['masked'] or {}).get('matched') or 0 for r in group),
                       'masked_total_slots': sum((r['masked'] or {}).get('total') or 0 for r in group),
                       'masked_scored_slots': sum((r['masked'] or {}).get('total') or 0 for r in group if (r['masked'] or {}).get('matched') is not None),
                       'masked_status': dict(Counter((r['masked'] or {}).get('status') for r in group if r['masked'] is not None))})
    sessions = defaultdict(list)
    for row in attacks:
        if row['traffic'] == 'ia':
            sessions[row['method'], row['session_id']].append(row)
    histories = []
    for (method, sid), group in sessions.items():
        group.sort(key=lambda r: r['turn'])
        histories.append({'method': method, 'session_id': sid, 'doc_id': group[0]['doc_id'],
                          'member': group[0]['member'],
                          'first_raw_turn': min((r['turn'] for r in group if r['reference_raw_delivered']), default=None),
                          'first_limit_turn': min((r['turn'] for r in group if r['action'] not in ('allow', 'unavailable')), default=None)})
    scores = rows(RUN / 'attack_scores.jsonl')
    auc = {}
    for kind in ('direct_rag_mia', 's2_mia', 'masked_mia', 'ia'):
        per_method = {}
        for method in ('B0', 'B2', 'B_TYPE_V2'):
            selected = [r for r in scores if r['method'] == method and r['attack_type'] == kind]
            budgets = {r['budget'] for r in selected}
            values = [r for r in selected if r['score'] is not None]
            if kind == 'ia':
                reason = 'IA score uses offline reference answer; mixed one/three-query budgets.'
            elif kind == 'masked_mia':
                reason = 'Strict parser expects object format; compatible array answers are separately diagnosed.'
            elif len(budgets) != 1 or len(values) != len(selected) or {r['membership_label'] for r in values} != {0, 1}:
                reason = 'Missing scores, mixed budgets or single membership class.'
            else:
                reason = None
            per_method[method] = {'value': None if reason else float(roc_auc_score(
                [r['membership_label'] for r in values], [r['score'] for r in values])),
                'reason': reason, 'members': sum(r['membership_label'] == 1 for r in selected),
                'nonmembers': sum(r['membership_label'] == 0 for r in selected), 'budgets': sorted(budgets)}
        auc[kind] = per_method
    out = {'run_id': audit['run_id'], 'analysis_role': 'engineering_only', 'human_reviewed': False,
           'input_sha256': {str(path): sha256(path.read_bytes()).hexdigest() for path in [audit_path, REPORT / 'benign_pair_review_20261113.json']},
           'normal': summary, 'attacks': groups, 'ia_sessions': histories,
           'auc_descriptive_only': auc, 'auc_limit': 'Previously inspected development targets; Direct and S2 have one member target, intervals too wide for conclusions.',
           'fixed_threshold_tpr_fpr': None, 'threshold_reason': 'No independent attack calibration.'}
    path = REPORT / 'two_hour_paired_summary_20261117.json'
    with path.open('x', encoding='utf8') as handle:
        handle.write(json.dumps(out, ensure_ascii=False, indent=2) + '\n')
    print('Normal:', {k: {x:y for x,y in v.items() if x != 'cases'} for k,v in summary.items()})
    print('Attack groups:', len(groups), 'IA sessions:', len(histories))

if __name__ == '__main__':
    main()
