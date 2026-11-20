"""Export paired normal answers with actual evidence for agent review."""
from collections import defaultdict
from hashlib import sha256
import argparse
import json
from pathlib import Path

RUN = Path('data/defense_v1_runs/next-goal-paired-20261117-01')
COHORT = Path('data/defense_datasets/next_goal_v2_train_20261117_01')
OUT = Path('reports/defense_v1/T10/next_goal_normal_review_units_20261117.json')


def rows(path):
    return [json.loads(x) for x in path.read_text(encoding='utf8').splitlines() if x.strip()]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', type=Path, default=RUN)
    parser.add_argument('--cohort', type=Path, default=COHORT)
    parser.add_argument('--output', type=Path, default=OUT)
    args = parser.parse_args()
    run, cohort, output_path = args.run, args.cohort, args.output
    manifest = json.loads((run / 'run_manifest.json').read_text(encoding='utf8'))
    assert manifest['status'] == 'completed'
    labels = {x['request_id']: x for x in rows(run / 'labels.jsonl')}
    rubrics = {x['request_id']: x for x in rows(cohort / 'normal_rubric.jsonl')}
    groups = defaultdict(list)
    for event in rows(run / 'events.jsonl'):
        rid = event['request_id']
        if labels[rid]['attack_type'] != 'benign':
            continue
        evidence = (event.get('ledger_event') or {}).get('delivered_evidence', [])
        hashes = tuple(x['text_sha256'] for x in evidence)
        key = (rid, event['status'], event['action'], event.get('response'), hashes)
        groups[key].append(event)
    result = []
    for (rid, status, action, response, hashes), events in groups.items():
        e = events[0]
        artifact = (run / e['generation_input_ref']).resolve()
        assert artifact.is_relative_to(run.resolve()) and sha256(artifact.read_bytes()).hexdigest() == e['artifact_sha256']
        actual = json.loads(artifact.read_text(encoding='utf8'))['generation_input']
        result.append({'request_id': rid, 'methods': [x['method'] for x in events],
                       'status': status, 'action': action, 'response': response,
                       'answerable': labels[rid]['answerable'], 'reference_answer': labels[rid]['reference_answer'],
                       'gold_evidence_ids': labels[rid]['gold_evidence_ids'], 'rubric': rubrics[rid],
                       'contexts': actual['contexts'], 'delivered_evidence': e['ledger_event']['delivered_evidence'],
                       'delivered_sha256': list(hashes), 'artifact': e['generation_input_ref']})
    output = {'reviewer_kind': 'llm_agent', 'human_reviewed': False, 'review_complete': False,
              'events_sha256': sha256((run / 'events.jsonl').read_bytes()).hexdigest(),
              'rubric_sha256': sha256((cohort / 'normal_rubric.jsonl').read_bytes()).hexdigest(), 'units': result}
    with output_path.open('x', encoding='utf8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
        f.write('\n')
    print('normal review groups', len(result))


if __name__ == '__main__':
    main()
