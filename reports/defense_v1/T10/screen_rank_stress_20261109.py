"""Select engineering candidates by retrieval only, before any new answer generation."""
import json
from collections import Counter
from pathlib import Path

import faiss
import numpy as np

from miaguard.config import load_attack_config
from miaguard.model_client import create_model_client
from miaguard.vector_store import UnifiedVectorStore


ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).with_name('rank_stress_20261109_01')


def rows(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]


def main():
    output = OUT / 'retrieval_screen.jsonl'
    if output.exists():
        raise FileExistsError(output)
    split = json.loads((ROOT / 'data/query_bank_splits/ag_news_threshold_v2.json').read_text(encoding='utf-8'))
    train = set(split['partitions']['train']['doc_ids'])
    old_labels = rows(ROOT / 'data/defense_datasets/legacy_v2_fast_pilot_20261105_01/labels.jsonl')
    excluded = {label['doc_id'] for label in old_labels}
    config = load_attack_config(ROOT / 'configs/attacks/ag_news_progressive_judge_qwen2_5_7b_bf16.yaml')
    client = create_model_client(config, ROOT)
    store = UnifiedVectorStore.load(ROOT / 'data/vector_stores/20260717-ag-news-four-medium/ag_news', client)
    index_docs = {doc['doc_id'] for doc in store.documents}
    candidates = []
    for row in rows(ROOT / 'data/query_banks/ag_news_queries_v2/ag_news/queries.jsonl'):
        if row['doc_id'] not in (train & index_docs) - excluded or row['validation']['status'] != 'accepted':
            continue
        kind = row['attack_type']
        if kind in {'direct_rag_mia', 's2_mia'} or (kind == 'benign' and row['payload'].get('difficulty') == 'hard'):
            candidates.append({'source_id': row['query_id'], 'doc_id': row['doc_id'], 'attack_type': kind,
                               'query': row['query_text'], 'payload': row['payload']})
    overlay = ROOT / 'data/defense_datasets/legacy_v2_reuse_overlay_20261105_01'
    queries = {row['request_id']: row['query'] for row in rows(overlay / 'requests.jsonl')}
    for row in rows(overlay / 'labels.jsonl'):
        if row['doc_id'] in (train & index_docs) - excluded and not row['quality_flags']:
            kind = row['attack_type']
            field = {'ia': 'ground_truth', 'masked_mia': 'answers'}[kind]
            candidates.append({'source_id': row['request_id'], 'doc_id': row['doc_id'], 'attack_type': kind,
                               'query': queries[row['request_id']], 'payload': {field: row[field]}})
    candidates.sort(key=lambda row: row['source_id'])
    for start in range(0, len(candidates), 64):
        batch = candidates[start:start + 64]
        vectors = np.asarray(client.embed(store.embedding_model, [row['query'] for row in batch]), dtype='float32')
        faiss.normalize_L2(vectors)
        _, positions = store.index.search(vectors, 4)
        for row, hits in zip(batch, positions):
            retrieved = [store.documents[i]['doc_id'] for i in hits if i >= 0]
            row['retrieved_doc_ids'] = retrieved
            row['target_rank'] = retrieved.index(row['doc_id']) + 1 if row['doc_id'] in retrieved else None
    OUT.mkdir(exist_ok=True)
    output.write_text(''.join(json.dumps(row, ensure_ascii=False) + '\n' for row in candidates), encoding='utf-8')
    print(Counter((row['attack_type'], row['target_rank']) for row in candidates))


if __name__ == '__main__':
    main()
