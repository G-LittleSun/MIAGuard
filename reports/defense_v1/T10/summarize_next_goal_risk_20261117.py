"""Report Judge decisions and candidate cue escalation separately."""
from collections import Counter, defaultdict
from hashlib import sha256
import json
from pathlib import Path

from sklearn.metrics import roc_auc_score

REPORT = Path('reports/defense_v1/T10')
AUDIT = REPORT / 'next_goal_paired_audit_20261117.json'
OUT = REPORT / 'next_goal_risk_summary_20261117.json'
METHODS = ('B2', 'B_TYPE_V2', 'B_NEXT_GOAL')
CUE_REASONS = {'cue_direct', 'cue_masked', 'cue_ia_first', 'cue_ia_prior_raw'}


def main():
    data = json.loads(AUDIT.read_text(encoding='utf8'))
    methods = {}
    for method in METHODS:
        cases = [x for x in data['cases'] if x['method'] == method]
        assert len(cases) == 47
        observed = [x for x in cases if x['status'] == 'complete' and x['risk_status'] == 'ok']
        detail = defaultdict(Counter)
        scored = defaultdict(list)
        tp = fp = tn = fn = 0
        for row in observed:
            truth = row['traffic'] != 'benign'
            cue = (row.get('policy') or {}).get('reason') in CUE_REASONS
            judge = row['risk_triggered'] is True
            effective = judge or cue
            group = detail[row['traffic']]
            group['observed'] += 1
            group['judge_triggered'] += judge
            group['cue_override'] += cue and not judge
            group['effective_triggered'] += effective
            group['type_matches_judge'] += row['traffic'] in row['predicted_types']
            group['query_only'] += row['risk_source'] == 'query_only'
            group['fusion'] += row['risk_source'] == 'fusion'
            tp += truth and effective
            fp += not truth and effective
            tn += not truth and not effective
            fn += truth and not effective
            if row['risk_score'] is not None:
                scored[row['risk_source']].append((int(truth), row['risk_score']))
        auc = {}
        for source in ('query_only', 'fusion'):
            pairs = scored[source]
            auc[source] = {'n': len(pairs), 'value': float(roc_auc_score([x[0] for x in pairs], [x[1] for x in pairs]))
                           if len({x[0] for x in pairs}) == 2 else None}
        methods[method] = {'expected': len(cases), 'observed': len(observed),
                           'unavailable_or_failed': len(cases) - len(observed),
                           'judge_score_auroc_by_source': auc,
                           'judge_score_auroc_scope': 'Raw judge risk separately by query-only or fusion; not cue-adjusted.',
                           'effective_confusion': {'tp': tp, 'fp': fp, 'tn': tn, 'fn': fn},
                           'effective_f1': 2 * tp / (2 * tp + fp + fn) if (2 * tp + fp + fn) else None,
                           'normal_trigger_fraction': fp / (fp + tn) if fp + tn else None,
                           'by_traffic': {k: dict(v) for k, v in grouped_sorted(detail)}}
    value = {'analysis_role': 'engineering_only', 'human_reviewed': False,
             'audit_sha256': sha256(AUDIT.read_bytes()).hexdigest(),
             'definitions': {'judge_triggered': 'Frozen score meets threshold.',
                             'cue_override': 'Candidate cue restricts a low-risk request.',
                             'effective_triggered': 'Judge trigger OR candidate cue override.',
                             'type_matches_judge': 'Offline traffic label appears in available judge predicted types; cues do not change judge output.'},
             'limits': ['Selected development requests and correlated turns; fractions are not general population estimates.',
                        'Effective F1 uses developer labels; benign intent is agent assessed, no human gold.',
                        'Query-only and fusion scores are reported separately; raw risk AUROC excludes cues and is not an MIA outcome.'], 'methods': methods}
    with OUT.open('x', encoding='utf8') as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.write('\n')
    print(json.dumps(methods, ensure_ascii=False))


def grouped_sorted(groups):
    return sorted(groups.items())


if __name__ == '__main__':
    main()
