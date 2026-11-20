import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
REPORTS = ROOT / 'reports/defense_v1/T10'

def read(p):
    return json.loads(p.read_text(encoding='utf-8'))

def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def check_map(values, base):
    for name, expected in values.items():
        p = Path(name)
        if not p.is_absolute():
            p = base / p
        assert p.is_file(), str(p)
        assert digest(p) == expected, str(p)

checks = []
for run, count, audit_name in [
    ('next-goal-paired-20261117-01', 188, 'next_goal_paired_audit_20261117.json'),
    ('next-goal-ia-style-20261117-01', 16, 'next_goal_ia_style_audit_20261117.json'),
    ('next-goal-ablation-20261117-01', 32, 'next_goal_ablation_audit_20261117.json'),
]:
    d = ROOT / 'data/defense_v1_runs' / run
    manifest, metrics, audit = read(d/'run_manifest.json'), read(d/'metrics.json'), read(REPORTS/audit_name)
    assert manifest['status'] == 'completed' and manifest['outcome'] == 'valid'
    assert metrics['expected'] == metrics['completed'] == count and metrics['failed'] == metrics['skipped'] == 0
    assert digest(d/'metrics.json') == manifest['metrics_sha256']
    check_map(audit['input_sha256'], d)
    spec_path = {'next-goal-paired-20261117-01':'next_goal_v2_train_20261117_01', 'next-goal-ia-style-20261117-01':'next_goal_ia_style_normal_20261117_01', 'next-goal-ablation-20261117-01':'next_goal_ablation_v2_train_20261117_01'}[run]
    spec_file = ROOT/'data/defense_datasets'/spec_path/'experiment_spec.json'
    spec = read(spec_file)
    assert digest(spec_file) == manifest['files_sha256']['spec']
    for field in ('requests', 'labels'):
        assert digest(Path(spec[field+'_path'])) == manifest['files_sha256'][field]
    for key, path in spec['identity_files'].items():
        assert digest(Path(path)) == manifest['files_sha256']['identity:'+key], key
    for key, expected in manifest['files_sha256'].items():
        if not key.startswith('code:'):
            continue
        name = key.removeprefix('code:')
        if name == 'defense_benchmark_live.py' and run != 'next-goal-ablation-20261117-01':
            path = REPORTS/'next_goal_primary_defense_benchmark_live_snapshot.py'
        elif name == 'run_defense_v1_benchmark.py':
            path = ROOT/'scripts'/name
        else:
            path = ROOT/'src/miaguard'/name
        assert digest(path) == expected, str(path)
    assert sum(1 for line in (d/'events.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()) == count
    checks.append({'run':run,'completed':count,'audit_sha256':digest(REPORTS/audit_name)})

d = ROOT/'data/defense_v1_runs/next-goal-alternate-20261117-01'
m = read(d/'run_manifest.json')
assert m['status'] == 'completed' and m['expected'] == m['completed'] == 2 and m['failed'] == 0
check_map(m['input_sha256'], ROOT)
assert digest(d/'events.jsonl') == m['events_sha256']
checks.append({'run':'next-goal-alternate-20261117-01','completed':2})

for name in ['next_goal_v2_train_20261117_01','next_goal_ia_style_normal_20261117_01','next_goal_ablation_v2_train_20261117_01']:
    d = ROOT/'data/defense_datasets'/name
    m = read(d/'manifest.json')
    check_map(m['input_sha256'], ROOT)
    check_map(m['output_sha256'], d)
    checks.append({'dataset':name,'manifest_sha256':digest(d/'manifest.json')})

for name, count in [('next_goal_human_review_packet_20261117',47),('next_goal_ia_style_human_review_20261117',4),('t10e_ddev_human_review_20261117',86)]:
    d = REPORTS/name
    m = read(d/'manifest.json')
    assert m['status'] == 'pending_human_review' and not m['human_reviewed'] and not m['formal_effect_eligible']
    check_map(m['inputs_sha256'], ROOT)
    check_map(m['outputs_sha256'], d)
    lines = [json.loads(x) for x in (d/'review_packet.jsonl').read_text(encoding='utf-8').splitlines() if x.strip()]
    assert len(lines) == count and 'membership_label' not in json.dumps(lines)
    checks.append({'human_review_packet':name,'count':count})

sel = read(REPORTS/'next_goal_candidate_selection_20261117.json')
check_map(sel['input_sha256'], ROOT)
assert sel['decision'] == 'retain_v2' and len(sel['raw_added']) == 0 and len(sel['raw_removed']) == 4
assert len(sel['supported_normal_regressions']) == 2
risk = read(REPORTS/'next_goal_risk_summary_20261117.json')
assert risk['methods']['B_TYPE_V2']['effective_confusion']['tp'] == 20
assert risk['methods']['B_NEXT_GOAL']['effective_confusion']['tp'] == 31
abl = read(REPORTS/'next_goal_ablation_summary_20261117.json')['summary']
assert [abl[n]['attack_target_raw_delivered'] for n in ['B_TYPE_V2','B_NEXT_GOAL','B_NEXT_CUE_ONLY','B_NEXT_IA_ONLY']] == [4,0,1,3]
assert [abl[n]['normal_correct_supported'] for n in ['B_TYPE_V2','B_NEXT_GOAL','B_NEXT_CUE_ONLY','B_NEXT_IA_ONLY']] == [2,0,2,0]

report = REPORTS/'NEXT_GOAL_RESULTS_20261117_ZH.md'
for target in re.findall(r'\]\(([^)]+)\)', report.read_text(encoding='utf-8')):
    if target.startswith(('http:', 'https:', '#')):
        continue
    p = Path(target.split('#')[0])
    if not p.is_absolute():
        p = report.parent/p
    assert p.exists(), str(p)
checks.append({'selection':'retain_v2','raw_removed':4,'normal_regressions':2,'report_links':'valid'})

output = {'verified_at':datetime.now(timezone.utc).isoformat(),'status':'passed','formal_effect_eligible':False,'checks':checks}
(REPORTS/'next_goal_delivery_verification_20261117.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(output,ensure_ascii=False,indent=2))
