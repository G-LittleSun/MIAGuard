import collections
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
bank = ROOT / 'data/query_banks/ag_news_queries_v2/ag_news/queries.jsonl'
records = ROOT / 'data/progressive_judge_v3_binary_logprob_train_qwen2_5_7b_bf16_20260916_retry1/train/judge_records.jsonl'
thresholds = ROOT / 'reports/defense_v1/T04/query_only_thresholds.json'
output = ROOT / 'reports/defense_v1/T10/reusable_normal_scores_20261111.json'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def rows(path):
    with path.open(encoding='utf-8') as stream:
        return [json.loads(line) for line in stream if line.strip()]

t = json.loads(thresholds.read_text(encoding='utf-8'))
assert sha(records) == t['source']['judge_records_sha256']
cutoff = t['working_points']['0.01']['threshold']
queries = {r['query_id']: r for r in rows(bank)}
old = [r for r in rows(records) if r['traffic_type'] == 'benign']
matched = [r for r in old if r['query_id'] in queries and r['query_text'] == queries[r['query_id']]['query_text']]
counts = collections.Counter((r['turn_index'], r['query_trace']['logprob']['score'] >= cutoff) for r in matched)
result = {
    'purpose': 'historical query-only score screen, not live action outcomes',
    'source_partition': 'train', 'old_benign_count': len(old),
    'v2_same_id_and_text_count': len(matched), 'threshold': cutoff,
    'at_or_above_threshold': sum(r['query_trace']['logprob']['score'] >= cutoff for r in matched),
    'turn_counts': [{'turn': k[0], 'at_or_above': k[1], 'count': v} for k, v in sorted(counts.items())],
    'input_sha256': {str(p.relative_to(ROOT)).replace('\\', '/'): sha(p) for p in (bank, records, thresholds)},
    'limitations': ['Historical v1 train scores are used only for exact-id/text matches in v2.', 'Scores do not establish live policy actions, answerability or quality.', 'Later-turn session/fusion behavior is not evaluated.', 'New v2 normal queries lack historical scores.'],
}
output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
print(json.dumps({'matched': len(matched), 'at_or_above': result['at_or_above_threshold'], 'output': str(output)}, ensure_ascii=False))
