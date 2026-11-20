"""Summarize the audited next-goal run using the established diagnostic format."""
from hashlib import sha256
import importlib.util
import json
from pathlib import Path

REPORT = Path('reports/defense_v1/T10')
RUN = Path('data/defense_v1_runs/next-goal-paired-20261117-01')
AUDIT = REPORT / 'next_goal_paired_audit_20261117.json'
OUT = REPORT / 'next_goal_paired_summary_20261117.json'

spec = importlib.util.spec_from_file_location('prior_summary', REPORT / 'summarize_multi_action_20261117.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.METHODS = ('B0', 'B2', 'B_TYPE_V2', 'B_NEXT_GOAL')
summary = module.summarize(RUN, AUDIT)
value = {'analysis_role': 'engineering_only', 'human_reviewed': False, 'formal_effect_eligible': False,
         'audit_sha256': sha256(AUDIT.read_bytes()).hexdigest(), 'run': summary,
         'fixed_threshold_tpr_fpr': None, 'reason': 'Independent attack calibration not completed.',
         'limits': ['Prior references are agent-only; selected topics are not independent final evaluation.',
                    'Masked parser mismatch and IA label-dependent score make those AUCs inapplicable.',
                    'S2 semantic scores can reflect repeated query text and fixed denial.']}
with OUT.open('x', encoding='utf8') as f:
    json.dump(value, f, ensure_ascii=False, indent=2)
    f.write('\n')
print('Wrote', OUT)
