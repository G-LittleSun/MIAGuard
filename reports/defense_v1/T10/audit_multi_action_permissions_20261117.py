"""Verify explicit trusted allowlists across retrieval, transforms and raw delivery."""
import argparse
from hashlib import sha256
import json
from pathlib import Path


def rows(path):
    return [json.loads(x) for x in path.read_text(encoding='utf8').splitlines() if x.strip()]


def main():
    p = argparse.ArgumentParser()
    p.add_argument('run', type=Path)
    p.add_argument('output', type=Path)
    args = p.parse_args()
    requests = {r['request_id']: r for r in rows(args.run / 'requests.jsonl')}
    events = rows(args.run / 'events.jsonl')
    violations = []
    bounded = 0
    summary_count = 0
    for event in events:
        allowed = requests[event['request_id']]['allowed_doc_ids']
        if allowed is None:
            continue
        bounded += 1
        allowed = set(allowed)
        ledger = event.get('ledger_event') or {}
        raw = [item['parent_doc_id'] for item in ledger.get('delivered_evidence', []) if item['kind'] == 'raw']
        transform = [item['parent_doc_id'] for item in ledger.get('transform_input_evidence', [])]
        summary_count += any(item['kind'] == 'summary' for item in ledger.get('delivered_evidence', []))
        for stage, ids in [('retrieved', event.get('retrieved_doc_ids', [])), ('transform', transform), ('raw_delivered', raw)]:
            unexpected = sorted(set(ids) - allowed)
            if unexpected:
                violations.append({'method': event['method'], 'request_id': event['request_id'], 'stage': stage, 'unexpected': unexpected})
    result = {'bounded_events': bounded, 'bounded_summary_events': summary_count, 'violations': violations,
              'events_sha256': sha256((args.run / 'events.jsonl').read_bytes()).hexdigest(),
              'requests_sha256': sha256((args.run / 'requests.jsonl').read_bytes()).hexdigest(),
              'scope': 'Checks supplied allowlists, not real user identity or authentication.'}
    with args.output.open('x', encoding='utf8') as f:
        f.write(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result, ensure_ascii=False))
    if violations:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
