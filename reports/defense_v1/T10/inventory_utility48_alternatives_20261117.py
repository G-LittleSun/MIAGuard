"""Rank possible supplementary sources for train targets by rare shared terms."""
from collections import Counter
from hashlib import sha256
import json
import math
from pathlib import Path
import re

ROOT = Path.cwd()
DOCS = ROOT / 'data/vector_stores/20260717-ag-news-four-medium/ag_news/documents.jsonl'
SPLIT = ROOT / 'data/query_bank_splits/ag_news_threshold_v2.json'
OUT = ROOT / 'reports/defense_v1/T10/utility48_alternative_candidates_20261117.json'

def words(text):
    text = re.sub(r'&lt;.*?&gt;', ' ', text, flags=re.I)
    return set(re.findall(r'[a-z]{4,}', text.lower()))

def main():
    documents = [json.loads(line) for line in DOCS.read_text(encoding='utf-8').splitlines() if line.strip()]
    partitions = json.loads(SPLIT.read_text(encoding='utf-8'))['partitions']
    membership = {doc_id: part for part, data in partitions.items() for doc_id in data['doc_ids']}
    token_sets = {d['doc_id']: words(d['text']) for d in documents}
    frequencies = Counter(word for terms in token_sets.values() for word in terms)
    candidates = []
    for target in documents:
        target_id = target['doc_id']
        if membership.get(target_id) != 'train':
            continue
        for other in documents:
            other_id = other['doc_id']
            if other_id == target_id or membership.get(other_id) in ('test', 'validation'):
                continue
            shared = sorted(w for w in token_sets[target_id] & token_sets[other_id] if frequencies[w] <= 10)
            if len(shared) < 2:
                continue
            score = sum(math.log(len(documents) / frequencies[w]) for w in shared)
            candidates.append({'target_id': target_id, 'other_id': other_id,
                               'other_partition': membership.get(other_id, 'not_in_query_split'),
                               'shared_rare_terms': shared, 'rank_score': score,
                               'target_text': target['text'], 'other_text': other['text']})
    candidates.sort(key=lambda x: (-x['rank_score'], x['target_id'], x['other_id']))
    result = {'status': 'candidates_only', 'count': len(candidates), 'candidates': candidates,
              'input_sha256': {str(path): sha256(path.read_bytes()).hexdigest() for path in (DOCS, SPLIT)},
              'limits': ['Shared terms do not prove that documents support the same fact.',
                         'Supplementary documents outside query split require separate provenance disclosure.']}
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('candidate pairs:', len(candidates))
    for item in candidates[:15]:
        print(item['target_id'], item['other_id'], item['shared_rare_terms'])

if __name__ == '__main__':
    main()
