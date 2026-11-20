"""Small deterministic v2 train query-only screen; not an effect experiment."""
import hashlib
import json
from dataclasses import asdict
from pathlib import Path

from miaguard.attack_pattern_library import AttackPatternLibrary
from miaguard.config import load_attack_config
from miaguard.model_client import create_model_client
from miaguard.progressive_judge import ProgressiveJudge, load_progressive_judge_config

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'reports/defense_v1/T10/new_benign_screen_20261111_01'
BANK = ROOT / 'data/query_banks/ag_news_queries_v2/ag_news/queries.jsonl'
PRIOR = ROOT / 'data/query_banks/ag_news_queries_v1/ag_news/queries.jsonl'
SPLIT = ROOT / 'data/query_bank_splits/ag_news_threshold_v2.json'
INDEX = ROOT / 'data/vector_stores/20260717-ag-news-four-medium/ag_news/documents.jsonl'
THRESHOLD = ROOT / 'reports/defense_v1/T04/query_only_thresholds.json'
ATTACK = ROOT / 'configs/attacks/ag_news_progressive_judge_qwen2_5_7b_bf16.yaml'
JUDGE = ROOT / 'configs/defense/progressive_judge_v3_binary_logprob_qwen2_5_7b.yaml'

def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def rows(p):
    with p.open(encoding='utf-8') as f:
        return [json.loads(line) for line in f if line.strip()]

def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

def main():
    assert digest(BANK) == '7d44945635a768ec9e107b516040364b934a6c11e33525654727012f71134972'
    assert digest(SPLIT) == '96977e550be6c0e42ab0b7609f2c73af261a99474b459778ae46fd123c7b80ef'
    assert digest(THRESHOLD) == 'a2b482352326a4e9154abeb1126169694df5c7c9ff70a87d9bc5a3ca07aa0759'
    train = set(json.loads(SPLIT.read_text(encoding='utf-8'))['partitions']['train']['doc_ids'])
    previous = {r['query_id'] for r in rows(PRIOR)}
    index = {r['doc_id'] for r in rows(INDEX)}
    candidates = [r for r in rows(BANK) if r['traffic_type'] == 'benign' and r['doc_id'] in train and r['doc_id'] in index and r['query_id'] not in previous and r['validation']['status'] == 'accepted' and r['query_text'].endswith('?')]
    candidates.sort(key=lambda r: hashlib.sha256(('normal-screen-20261111:' + r['query_id']).encode()).hexdigest())
    selected, seen = [], set()
    for row in candidates:
        if row['doc_id'] not in seen:
            selected.append({'query_id': row['query_id'], 'doc_id': row['doc_id'], 'query': row['query_text']})
            seen.add(row['doc_id'])
        if len(selected) == 8:
            break
    assert len(selected) == 8
    OUT.mkdir(exist_ok=False)
    write(OUT / 'candidates.json', selected)
    manifest = {'status': 'running', 'scope': 'engineering query-only screening; no gold or live policy', 'selection': '8 distinct indexed train documents by deterministic SHA256 rank of v2-only benign question IDs; no result-based selection', 'threshold': json.loads(THRESHOLD.read_text(encoding='utf-8'))['working_points']['0.01']['threshold'], 'input_sha256': {str(p.relative_to(ROOT)).replace('\\', '/'): digest(p) for p in (BANK, PRIOR, SPLIT, INDEX, THRESHOLD, ATTACK, JUDGE, Path(__file__))}, 'candidate_sha256': digest(OUT / 'candidates.json'), 'completed': 0}
    write(OUT / 'manifest.json', manifest)
    try:
        config = load_attack_config(ATTACK)
        judge_config = load_progressive_judge_config(JUDGE, ROOT)
        client = create_model_client(config, ROOT)
        client.validate_models()
        judge = ProgressiveJudge(judge_config, client, config.generation_model, AttackPatternLibrary.load(judge_config.manifest_path))
        with (OUT / 'traces.jsonl').open('w', encoding='utf-8') as output:
            for row in selected:
                trace = judge.evaluate_query(query=row['query'], session_id=row['query_id'])
                output.write(json.dumps({'query_id': row['query_id'], 'trace': asdict(trace)}, ensure_ascii=False) + '\n')
                output.flush()
                manifest['completed'] += 1
                write(OUT / 'manifest.json', manifest)
                print('completed', manifest['completed'], '/ 8', flush=True)
        manifest['status'] = 'completed'
        manifest['traces_sha256'] = digest(OUT / 'traces.jsonl')
    except BaseException as exc:
        manifest['status'] = 'interrupted' if isinstance(exc, KeyboardInterrupt) else 'failed'
        manifest['error'] = repr(exc)
        raise
    finally:
        write(OUT / 'manifest.json', manifest)

if __name__ == '__main__':
    main()
