"""Conservative D-dev source inventory; no membership labels or outcomes used."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
T10 = ROOT / 'reports/defense_v1/T10'
DATA = ROOT / 'data/defense_datasets/defense_access_v1_candidate06'
OUT = T10 / 'dev_source_inventory_20261104_01'


def rows(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8-sig').splitlines() if line.strip()]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    paths = [DATA / 'documents.jsonl', DATA / 'background_members.jsonl',
             T10 / 'normal_source_usage_20261102_01/source_usage.jsonl',
             T10 / 'review_attack_source_usage_20261102_01/source_usage.jsonl']
    targets = {r['doc_id']: r for r in rows(paths[0]) if r['partition'] == 'D-dev'}
    background = {r['doc_id']: r for r in rows(paths[1])}
    assert len(targets) == 200 and not set(targets) & set(background)
    all_docs = targets | background
    usage = {}
    def add(doc_id, reason):
        if doc_id not in all_docs:
            raise ValueError(f'unknown source {doc_id}')
        usage.setdefault(doc_id, set()).add(reason)
    for doc_id in targets:
        add(doc_id, 'conservative_all_d_dev_candidate_attack_targets')
    for path in paths[2:]:
        for r in rows(path):
            add(r['doc_id'], 'previous_partial_source_ledger')
    # Explicit source-bearing T10 development artifacts; do not scan V/T datasets.
    artifact_paths = sorted(p for p in T10.glob('**/*.jsonl')
        if 'external_review' not in p.parts
        and p.name in {'source_evidence.jsonl', 'expanded_source_evidence.jsonl',
                       'expanded_source_selection.jsonl', 'normal_variants.jsonl',
                       'expanded_variants.jsonl', 'revised_variants.jsonl',
                       'targeted_variants.jsonl', 'candidate_variants.jsonl',
                       'variants.jsonl', 'session_inventory.jsonl', 'cohort.jsonl',
                       'review_packet_d_dev_normal_evidence.jsonl'})
    for path in artifact_paths:
        for r in rows(path):
            ids = list(r.get('source_doc_ids', []))
            if 'doc_id' in r:
                ids.append(r['doc_id'])
            ids += [d['doc_id'] for d in r.get('supporting_documents', [])]
            for doc_id in ids:
                add(doc_id, 'explicit_t10_source_artifact')
    OUT.mkdir(exist_ok=False)
    records = []
    for doc_id, reasons in sorted(usage.items()):
        doc = all_docs[doc_id]
        records.append({'doc_id': doc_id, 'parent_doc_id': doc['parent_doc_id'],
                        'duplicate_group_id': doc['duplicate_group_id'],
                        'source_role': 'd_dev_target' if doc_id in targets else 'shared_background',
                        'inclusion_reasons': sorted(reasons),
                        'exclude_as_normal_question_source': ['A-cal', 'V', 'T']})
    output = OUT / 'source_usage.jsonl'
    output.write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in records), encoding='utf-8')
    manifest = {'status': 'partial_conservative_inventory', 'records': len(records),
        'd_dev_targets': sum(r['source_role'] == 'd_dev_target' for r in records),
        'shared_background': sum(r['source_role'] == 'shared_background' for r in records),
        'input_sha256': {str(p.relative_to(ROOT)).replace('\\', '/'): digest(p) for p in paths + artifact_paths},
        'output_sha256': digest(output), 'formal_effect_eligible': False,
        'limitations': ['Conservative candidate inclusion does not mean individual review or exposure to a person.',
          'Explicitly listed T10 source artifacts only; other historical prompts and semantic/event overlap remain unaudited.',
          'Same parent/duplicate group must also be excluded using complete source metadata.',
          'Shared background remains in existing retrieval indexes.']}
    (OUT / 'manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps({k: manifest[k] for k in ('records', 'd_dev_targets', 'shared_background')}))


if __name__ == '__main__':
    main()
