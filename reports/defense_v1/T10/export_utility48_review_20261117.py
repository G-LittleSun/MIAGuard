"""Export completed benchmark events with source text for evidence-based scoring."""
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path.cwd()
COHORT = ROOT/'data/defense_datasets/utility48_v2_train_20261117_01'
RUN = ROOT/'data/defense_v1_runs/utility48-paired-20261117-01'
OUTPUT = ROOT/'reports/defense_v1/T10/utility48_review_units_20261117.jsonl'
REPORTS_OUTPUT_REUSE = ROOT/'reports/defense_v1/T10/utility48_reuse_review_units_20261117.jsonl'

def rows(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]

def digest(path):
    return sha256(path.read_bytes()).hexdigest()

def main():
    reuse = '--reuse' in sys.argv
    cohort = ROOT/'data/defense_datasets/utility48_reuse_v2_train_20261117_01' if reuse else COHORT
    run = ROOT/'data/defense_v1_runs/utility48-reuse-paired-20261117-01' if reuse else RUN
    output = REPORTS_OUTPUT_REUSE if reuse else OUTPUT
    manifest = json.loads((run/'run_manifest.json').read_text(encoding='utf-8'))
    assert manifest['status'] == 'completed' and manifest['outcome'] == 'valid'
    cohort_manifest = json.loads((cohort/'manifest.json').read_text(encoding='utf-8'))
    for name, expected in cohort_manifest['output_sha256'].items():
        assert digest(cohort/name) == expected, name
    annotations = {x['request_id']:x for x in rows(cohort/'normal_rubric.jsonl')}
    documents = {x['doc_id']:x['text'] for x in rows(ROOT/'data/vector_stores/20260717-ag-news-four-medium/ag_news/documents.jsonl')}
    units = []
    events = rows(run/'events.jsonl')
    assert len(events) == 96 and len({(x['request_id'],x['method']) for x in events}) == 96
    for event in events:
        artifact = run/event['generation_input_ref']
        assert digest(artifact) == event['artifact_sha256'], str(artifact)
        captured = json.loads(artifact.read_text(encoding='utf-8'))['generation_input']
        retrieved = [{'doc_id':doc, 'text':documents[doc]} for doc in event['retrieved_doc_ids']]
        units.append({'request_id':event['request_id'],'method':event['method'],'status':event['status'],
                      'action':event['action'],'response':event['response'],'annotation':annotations[event['request_id']],
                      'retrieved':retrieved,'delivered_contexts':captured['contexts'],
                      'artifact_sha256':event['artifact_sha256']})
    output.write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in units),encoding='utf-8')
    print('Exported',len(units),'review units, sha256',digest(output))

if __name__ == '__main__':
    main()
