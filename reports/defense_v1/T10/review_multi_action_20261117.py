"""Export agent review units for normal outputs and summary evidence exposure."""
from collections import defaultdict
from hashlib import sha256
import json
from pathlib import Path
import re

ROOT = Path.cwd()
RUN = ROOT / 'data/defense_v1_runs/multi-action-candidates-20261117-01'
COHORT = ROOT / 'data/defense_datasets/multi_action_v2_train_20261117_01'
OUT = ROOT / 'reports/defense_v1/T10/multi_action_review_units_20261117.json'

def rows(path):
    return [json.loads(line) for line in path.read_text(encoding='utf8').splitlines() if line.strip()]

def main():
    labels = {r['request_id']: r for r in rows(RUN / 'labels.jsonl')}
    rubrics = {r['request_id']: r for r in rows(COHORT / 'normal_rubric.jsonl')}
    groups = defaultdict(list)
    summaries = []
    for event in rows(RUN / 'events.jsonl'):
        rid = event['request_id']
        label = labels[rid]
        if label['attack_type'] == 'benign':
            delivered = (event.get('ledger_event') or {}).get('delivered_evidence', [])
            evidence_hashes = tuple(item['text_sha256'] for item in delivered)
            record = {'method': event['method'], 'request_id': rid, 'action': event['action'],
                      'status': event['status'], 'response': event.get('response'),
                      'delivered_doc_ids': event.get('delivered_doc_ids', []),
                      'delivered_evidence_sha256': evidence_hashes,
                      'artifact': event.get('generation_input_ref')}
            key = (rid, event['status'], event['action'], event.get('response'), tuple(event.get('delivered_doc_ids', [])), evidence_hashes)
            groups[key].append(record)
        ledger = event.get('ledger_event') or {}
        transformed = ledger.get('transform_input_evidence', [])
        if transformed:
            artifact_path = (RUN / event['generation_input_ref']).resolve()
            assert artifact_path.is_relative_to(RUN.resolve())
            assert sha256(artifact_path.read_bytes()).hexdigest() == event['artifact_sha256']
            artifact = json.loads(artifact_path.read_text(encoding='utf8'))
            summary_text = ' '.join(artifact['generation_input']['contexts']).casefold()
            target_tokens = re.findall(r"[\w]+", label.get('target_text', '').casefold())
            summary_tokens = re.findall(r"[\w]+", summary_text)
            summary_ngrams = {tuple(summary_tokens[i:i + 8]) for i in range(max(0, len(summary_tokens) - 7))}
            overlaps = sorted({' '.join(target_tokens[i:i + 8]) for i in range(max(0, len(target_tokens) - 7))
                               if tuple(target_tokens[i:i + 8]) in summary_ngrams})
            retained_answers = [answer for answer in label.get('answers', [])
                                if re.search(r'(?<!\w)' + re.escape(answer.casefold()) + r'(?!\w)', summary_text)]
            summaries.append({'method': event['method'], 'request_id': rid, 'attack_type': label['attack_type'],
                              'doc_id': label['doc_id'], 'action': event['action'],
                              'transform_input': transformed,
                              'contexts': artifact['generation_input']['contexts'],
                              'exact_eight_token_target_overlaps': overlaps,
                              'masked_answers_present': retained_answers,
                              'response': event.get('response'), 'artifact': event['generation_input_ref']})
    review = []
    for key, records in groups.items():
        rid = key[0]
        review.append({'request_id': rid, 'methods': [r['method'] for r in records],
                       'answerable': labels[rid]['answerable'], 'reference_answer': labels[rid]['reference_answer'],
                       'reference_doc_id': labels[rid]['doc_id'], 'rubric': rubrics[rid],
                       'action': key[2], 'response': key[3], 'delivered_doc_ids': list(key[4]),
                       'delivered_evidence_sha256': list(key[5]),
                       'records': records})
    value = {'analysis_role': 'engineering_only', 'human_reviewed': False,
             'input_sha256': {str(path): sha256(path.read_bytes()).hexdigest() for path in
                              (RUN / 'events.jsonl', RUN / 'labels.jsonl', COHORT / 'normal_rubric.jsonl')},
             'normal_review_units': review, 'summary_exposure_units': summaries}
    with OUT.open('x', encoding='utf8') as f:
        f.write(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    print('normal review units', len(review), 'summary units', len(summaries))

if __name__ == '__main__':
    main()
