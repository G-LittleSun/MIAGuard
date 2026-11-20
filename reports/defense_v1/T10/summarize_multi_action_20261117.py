"""Describe audited development runs; this does not create human gold."""
from collections import Counter, defaultdict
from hashlib import sha256
import json
from pathlib import Path
from statistics import median

from sklearn.metrics import roc_auc_score

ROOT = Path.cwd()
REPORT = ROOT / 'reports/defense_v1/T10'
METHODS = ('B0', 'B2', 'B_TYPE_V2', 'B_MULTI_SUMMARY', 'B_MULTI_NO_CONTEXT', 'B3', 'B6')


def read(path):
    return json.loads(path.read_text(encoding='utf8'))


def rows(path):
    return [json.loads(line) for line in path.read_text(encoding='utf8').splitlines() if line.strip()]


def summarize(run, audit_path):
    audit = read(audit_path)
    cases = audit['cases']
    scores = rows(run / 'attack_scores.jsonl')
    groups = defaultdict(list)
    for row in cases:
        groups[row['method'], row['traffic'], row['member']].append(row)
    attack_groups = []
    for (method, kind, member), group in sorted(groups.items()):
        if kind == 'benign':
            continue
        attack_groups.append({
            'method': method, 'attack': kind, 'member': member, 'requests': len(group),
            'distinct_documents': len({r['doc_id'] for r in group}),
            'actions': dict(Counter(r['action'] for r in group)),
            'risk_triggered': sum(r['risk_triggered'] is True for r in group),
            'risk_observed': sum(r['risk_triggered'] is not None for r in group),
            'suspected_type_matches': sum(r['traffic'] in r['predicted_types'] for r in group),
            'outputs': dict(Counter(r['yes_no_unknown'] or ('deny' if r['action'] == 'deny' else 'other') for r in group)),
            'target_raw_delivered': sum(r['reference_raw_delivered'] for r in group),
            'masked_matched_slots': sum((r['masked'] or {}).get('matched') or 0 for r in group),
            'masked_total_slots': sum((r['masked'] or {}).get('total') or 0 for r in group),
            'masked_scored_slots': sum((r['masked'] or {}).get('total') or 0 for r in group if (r['masked'] or {}).get('matched') is not None),
            'masked_status': dict(Counter((r['masked'] or {}).get('status') for r in group if r['masked'] is not None)),
        })
    auc = []
    for method in METHODS:
        for kind in ('direct_rag_mia', 's2_mia', 'masked_mia', 'ia'):
            selected = [r for r in scores if r['method'] == method and r['attack_type'] == kind]
            if not selected:
                continue
            values = [r for r in selected if r['score'] is not None]
            budgets = {r['budget'] for r in selected}
            reason = None
            if kind == 'ia':
                reason = 'IA score uses offline reference; budgets or statements may be incomparable.'
            elif kind == 'masked_mia':
                reason = 'Strict parser and compatible array answers differ; report slots and failures.'
            elif len(budgets) != 1 or len(values) != len(selected) or {r['membership_label'] for r in values} != {0, 1}:
                reason = 'Missing scores, mixed budgets, or only one membership class.'
            auc.append({'method': method, 'attack': kind, 'n': len(selected), 'budgets': sorted(budgets),
                        'value': None if reason else float(roc_auc_score([r['membership_label'] for r in values], [r['score'] for r in values])),
                        'reason': reason})
    normal = {}
    for method in METHODS:
        selected = [r for r in cases if r['method'] == method and r['traffic'] == 'benign']
        if not selected:
            continue
        times = sorted(r['latency_ms'] for r in selected if r['latency_ms'] is not None)
        normal[method] = {'requests': len(selected), 'actions': dict(Counter(r['action'] for r in selected)),
                          'risk_triggered': sum(r['risk_triggered'] is True for r in selected),
                          'risk_observed': sum(r['risk_triggered'] is not None for r in selected),
                          'latency_p50_ms': median(times) if times else None,
                          'latency_p95_ms': times[max(0, __import__('math').ceil(.95 * len(times)) - 1)] if times else None}
    histories = defaultdict(list)
    for r in cases:
        if r['traffic'] == 'ia':
            histories[r['method'], r['session_id']].append(r)
    sessions = []
    for (method, sid), group in sorted(histories.items()):
        sessions.append({'method': method, 'session_id': sid, 'member': group[0]['member'], 'doc_id': group[0]['doc_id'],
                         'turns': len(group),
                         'first_raw_turn': min((r['turn'] for r in group if r['reference_raw_delivered']), default=None),
                         'first_limit_turn': min((r['turn'] for r in group if r['action'] not in ('allow', 'unavailable')), default=None)})
    by_request = {(r['method'], r['request_id']): r for r in cases}
    pairs = []
    for comparator in ('B0', 'B_TYPE_V2'):
        for method in METHODS:
            if method == comparator:
                continue
            paired = defaultdict(list)
            for (m, rid), candidate in by_request.items():
                if m != method or candidate['traffic'] == 'benign' or (comparator, rid) not in by_request:
                    continue
                paired[candidate['traffic'], candidate['member']].append((by_request[comparator, rid], candidate))
            for (kind, member), group in sorted(paired.items()):
                pairs.append({'reference_method': comparator, 'method': method, 'attack': kind, 'member': member,
                              'requests': len(group), 'distinct_documents': len({a['doc_id'] for a, _ in group}),
                              'raw_reference': sum(a['reference_raw_delivered'] for a, _ in group),
                              'raw_candidate': sum(b['reference_raw_delivered'] for _, b in group),
                              'raw_removed': sum(a['reference_raw_delivered'] and not b['reference_raw_delivered'] for a, b in group),
                              'raw_added': sum(not a['reference_raw_delivered'] and b['reference_raw_delivered'] for a, b in group)})
    return {'run_id': audit['run_id'], 'audit_sha256': sha256(audit_path.read_bytes()).hexdigest(),
            'normal_execution': normal, 'attacks': attack_groups, 'auc_descriptive_only': auc,
            'paired_target_raw': pairs, 'ia_sessions': sessions}


def main():
    items = [
        ('multi-action-candidates-20261117-01', 'multi_action_candidates_audit_20261117.json'),
        ('multi-action-sources-20261117-01', 'multi_action_sources_audit_20261117.json'),
    ]
    output = {'analysis_role': 'engineering_only', 'human_reviewed': False, 'formal_effect_eligible': False,
              'fixed_threshold_tpr_fpr': None, 'reason': 'No independent attack calibration.',
              'runs': [summarize(ROOT / 'data/defense_v1_runs' / run, REPORT / audit) for run, audit in items]}
    path = REPORT / 'multi_action_summary_20261117.json'
    with path.open('x', encoding='utf8') as f:
        f.write(json.dumps(output, ensure_ascii=False, indent=2) + '\n')
    print('Wrote', path)


if __name__ == '__main__':
    main()
