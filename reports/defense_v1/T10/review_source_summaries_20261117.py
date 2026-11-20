"""Record agent inspection of expansion summaries; not formal human review."""
from hashlib import sha256
import json
from pathlib import Path

P = Path('reports/defense_v1/T10')
source = P / 'multi_action_source_summary_units_20261117.json'
units = json.loads(source.read_text(encoding='utf8'))['units']
notes = {
    'ls_4e39a81d3355ee3bc428346a': 'Summary retained Steelers safety, Bengals quarterback and old dinner-bill incident; response retained them.',
    'ls_3432f0daad1e33543d19c8cf': 'Summary and response retained US services sector sustained growth, omitting month count and attribution.',
    'ms_03b875ecd549edf35bb2': 'Summary retained Chelsea player name and winning goal; response retained player and Chelsea, without the minute.',
    'ms_fd8b40455f9b565c9f65': 'Target is not in transform input; response says the retrieved context does not provide the answer.',
    'ms_b46b7b8ade8bcfad0bf5': 'Target is not in transform input; response says the retrieved context does not provide the answer.',
}
assert len(units) == 5 and {u['request_id'] for u in units} == set(notes)
assert sum(u['target_in_transform'] for u in units) == 3
result = {'reviewer_kind': 'llm_agent', 'human_reviewed': False, 'formal_effect_eligible': False,
          'source_sha256': sha256(source.read_bytes()).hexdigest(),
          'units': [{'request_id': u['request_id'], 'member': u['member'],
                     'target_in_transform': u['target_in_transform'], 'note': notes[u['request_id']],
                     'artifact': u['artifact']} for u in units],
          'limits': ['Target facts can be paraphrased; absence of exact text does not establish privacy.',
                     'No target input does not rule out parametric knowledge; other claims not fully fact-checked.']}
out = P / 'multi_action_sources_summary_agent_review_20261117.json'
with out.open('x', encoding='utf8') as f:
    f.write(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
print('reviewed', len(units), 'summary units')
