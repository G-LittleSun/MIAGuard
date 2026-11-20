"""Export source-expansion summary contexts for agent inspection."""
from hashlib import sha256
import json
from pathlib import Path
import re

run = Path('data/defense_v1_runs/multi-action-sources-20261117-01')
report = Path('reports/defense_v1/T10/multi_action_source_summary_units_20261117.json')
def rows(path):
    return [json.loads(x) for x in path.read_text(encoding='utf8').splitlines() if x.strip()]
labels = {x['request_id']: x for x in rows(run / 'labels.jsonl')}
units = []
for e in rows(run / 'events.jsonl'):
    ledger = e.get('ledger_event') or {}
    transformed = ledger.get('transform_input_evidence', [])
    if not transformed:
        continue
    artifact = (run / e['generation_input_ref']).resolve()
    assert artifact.is_relative_to(run.resolve())
    assert sha256(artifact.read_bytes()).hexdigest() == e['artifact_sha256']
    context = json.loads(artifact.read_text(encoding='utf8'))['generation_input']['contexts']
    label = labels[e['request_id']]
    normalized = ' '.join(context).casefold()
    present = [w for w in label.get('answers', []) if re.search(r'(?<!\w)' + re.escape(w.casefold()) + r'(?!\w)', normalized)]
    units.append({'request_id': e['request_id'], 'method': e['method'], 'type': label['attack_type'],
                  'member': label['membership_label'], 'target_doc_id': label['doc_id'],
                  'target_in_transform': label['doc_id'] in [x['parent_doc_id'] for x in transformed],
                  'transform_input': transformed, 'contexts': context, 'masked_answers_present': present,
                  'response': e.get('response'), 'artifact': e['generation_input_ref']})
output = {'reviewer_kind': 'llm_agent', 'human_reviewed': False,
          'input_sha256': {p.name: sha256(p.read_bytes()).hexdigest() for p in [run / 'events.jsonl', run / 'labels.jsonl']},
          'units': units, 'status': 'requires_agent_review'}
with report.open('x', encoding='utf8') as f:
    f.write(json.dumps(output, ensure_ascii=False, indent=2) + '\n')
print('summary units', len(units))
