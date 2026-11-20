"""Export the selected D-dev cohort after checking frozen input identities."""
import argparse
import hashlib
import json
from pathlib import Path

from miaguard.defense_dataset import export_dev_cohort


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--version-id', required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    data = root / 'data/defense_datasets/defense_access_v1_candidate06'
    cohort = root / 'reports/defense_v1/T10/session_length_dev_cohort_20261102_01'
    usage = root / 'reports/defense_v1/T10/dev_source_inventory_20261104_01'
    index = root / 'data/vector_stores/defense_access_v1_candidate06/D-dev/ag_news'
    paths = [data / 'manifest.json', data / 'documents.jsonl', data / 'background_members.jsonl',
             cohort / 'manifest.json', cohort / 'cohort.jsonl', usage / 'manifest.json',
             usage / 'source_usage.jsonl', index / 'manifest.json', index / 'documents.jsonl',
             index / 'index.faiss', Path(__file__).resolve(), root / 'src/miaguard/defense_dataset.py']
    data_manifest = json.loads(paths[0].read_text(encoding='utf-8'))
    cohort_manifest = json.loads(paths[3].read_text(encoding='utf-8'))
    usage_manifest = json.loads(paths[5].read_text(encoding='utf-8'))
    index_manifest = json.loads(paths[7].read_text(encoding='utf-8'))
    expected = {paths[1]: data_manifest['artifact_sha256']['documents.jsonl'],
                paths[2]: data_manifest['artifact_sha256']['background_members.jsonl'],
                paths[4]: cohort_manifest['files_sha256']['cohort.jsonl'],
                paths[6]: usage_manifest['output_sha256'],
                paths[8]: index_manifest['documents_sha256'],
                paths[9]: index_manifest['index_sha256'],
                paths[0]: index_manifest['source_dataset_manifest_sha256']}
    for path, digest in expected.items():
        if sha(path) != digest:
            raise ValueError(f'Input hash mismatch: {path}')
    identity = {str(p.relative_to(root)).replace('\\', '/'): sha(p) for p in paths}
    result = export_dev_cohort(args.output, args.version_id, read(paths[4]),
        read(paths[1]) + read(paths[2]), {r['doc_id'] for r in read(paths[8])},
        {r['doc_id'] for r in read(paths[6])}, identity)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
