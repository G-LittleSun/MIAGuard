"""Inventory available train sources before selecting utility evaluation items."""
from collections import Counter
from hashlib import sha256
import itertools
import json
from pathlib import Path
import re

ROOT = Path.cwd()
BANK = ROOT / 'data/query_banks/ag_news_queries_v2/ag_news/queries.jsonl'
SPLIT = ROOT / 'data/query_bank_splits/ag_news_threshold_v2.json'
DOCS = ROOT / 'data/vector_stores/20260717-ag-news-four-medium/ag_news/documents.jsonl'
OUT = ROOT / 'reports/defense_v1/T10/utility48_source_inventory_20261117.json'


def rows(path):
    with path.open(encoding='utf-8') as handle:
        return [json.loads(line) for line in handle if line.strip()]


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    train = set(json.loads(SPLIT.read_text(encoding='utf-8'))['partitions']['train']['doc_ids'])
    docs = {d['doc_id']: d['text'] for d in rows(DOCS) if d['doc_id'] in train}
    counts = Counter()
    queries = Counter()
    for row in rows(BANK):
        if row['doc_id'] in train and row['traffic_type'] == 'benign':
            counts[row['payload'].get('category', 'unknown')] += 1
            if row['doc_id'] in docs:
                queries[row['doc_id']] += 1
    stop = set('the and for with that this from said have has was were would after over their about into than year more will had says its but are not new his her who first'.split())
    def tokens(text):
        return {x for x in re.findall(r'[a-z]{4,}', text.lower()) if x not in stop}
    words = {doc_id: tokens(text) for doc_id, text in docs.items()}
    pairs = []
    for (a, aw), (b, bw) in itertools.combinations(words.items(), 2):
        shared = sorted(aw & bw)
        if len(shared) >= 2:
            pairs.append({'doc_ids': [a, b], 'shared_words': shared, 'score': len(shared) / len(aw | bw)})
    pairs.sort(key=lambda item: (-item['score'], item['doc_ids']))
    result = {'analysis_role': 'source_inventory_not_annotation', 'train_doc_ids': len(train),
              'indexed_train_docs': len(docs), 'indexed_train_docs_with_benign_queries': len(queries),
              'benign_categories': dict(counts), 'candidate_pairs': pairs,
              'input_sha256': {str(p): digest(p) for p in (BANK, SPLIT, DOCS)},
              'limits': ['Lexical overlap does not establish shared event or alternative factual support.',
                         'Dataset partition is train; source text and question evidence require review.']}
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f"train={len(train)}, indexed_train={len(docs)}, queried_indexed={len(queries)}, candidate_pairs={len(pairs)}")


if __name__ == '__main__':
    main()
