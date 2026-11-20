"""Screen the fixed v2 train bank without invoking a model or reading test."""
import collections
import hashlib
import json
from pathlib import Path

from miaguard.query_cue import QUERY_CUE_VERSION, query_cues

ROOT = Path(__file__).resolve().parents[3]
BANK = ROOT / 'data/query_banks/ag_news_queries_v2/ag_news/queries.jsonl'
SPLIT = ROOT / 'data/query_bank_splits/ag_news_threshold_v2.json'
OUT = ROOT / 'reports/defense_v1/T10/query_cue_train_audit_20261111.json'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    assert digest(BANK) == '7d44945635a768ec9e107b516040364b934a6c11e33525654727012f71134972'
    assert digest(SPLIT) == '96977e550be6c0e42ab0b7609f2c73af261a99474b459778ae46fd123c7b80ef'
    train = set(json.loads(SPLIT.read_text(encoding='utf-8'))['partitions']['train']['doc_ids'])
    counts = collections.Counter()
    triggered = collections.Counter()
    benign_ids = []
    for line in BANK.read_text(encoding='utf-8').splitlines():
        row = json.loads(line)
        if row['doc_id'] not in train or row['validation']['status'] != 'accepted':
            continue
        kind = row['attack_type']
        counts[kind] += 1
        cues = query_cues(row['query_text'])
        if cues:
            triggered[kind] += 1
            if kind == 'benign':
                benign_ids.append(row['query_id'])
    result = {'version': QUERY_CUE_VERSION, 'partition': 'train', 'counts': dict(counts),
              'cues_by_attack_type': dict(triggered), 'benign_flagged_query_ids': benign_ids,
              'limitations': ['Offline query cue matches, not online actions or measured false-positive rates.',
                              'Train data labels and benign semantics require review.',
                              'Candidate was motivated by already-observed development examples.'],
              'input_sha256': {str(p.relative_to(ROOT)).replace('\\', '/'): digest(p) for p in
                               (BANK, SPLIT, ROOT / 'src/miaguard/query_cue.py', Path(__file__))}}
    if OUT.exists():
        raise FileExistsError(OUT)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'counts': counts, 'cues': triggered}, ensure_ascii=False))


if __name__ == '__main__':
    main()
