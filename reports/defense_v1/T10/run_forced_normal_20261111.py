"""Paired, forced-action normal utility diagnostic, not a natural-risk evaluation."""
import hashlib
import json
from pathlib import Path

from miaguard.defense_benchmark import run_benchmark
from miaguard.defense_benchmark_live import make_live_backend_factory

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / 'data/defense_datasets/legacy_v2_fast_pilot_20261105_01'
DATA = ROOT / 'data/defense_datasets/forced_normal_diagnostic_20261111_01'
RUN = ROOT / 'data/defense_v1_runs/forced-normal-b0-b5f-20261111-01'

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def read(p):
    return [json.loads(line) for line in p.read_text(encoding='utf-8').splitlines() if line.strip()]

def main():
    parent = json.loads((SOURCE / 'manifest.json').read_text(encoding='utf-8'))
    for name, expected in parent['output_sha256'].items():
        if sha(SOURCE / name) != expected:
            raise ValueError('Input identity mismatch: ' + name)
    reqs = read(SOURCE / 'requests.jsonl')
    labels = [r for r in read(SOURCE / 'labels.jsonl') if r['traffic_type'] == 'benign']
    ids = {r['request_id'] for r in labels}
    reqs = [r for r in reqs if r['request_id'] in ids]
    assert len(reqs) == len(labels) == 4 and len(ids) == 4
    spec = json.loads((SOURCE / 'experiment_spec.json').read_text(encoding='utf-8'))
    spec.update(experiment_id='T10D-forced-normal-diagnostic', methods=['B0', 'B5_FORCED'],
                requests_path=str(DATA / 'requests.jsonl'), labels_path=str(DATA / 'labels.jsonl'))
    spec['identity_files']['forced_runner'] = str(Path(__file__).resolve())
    spec['identity_files']['source_manifest'] = str(SOURCE / 'manifest.json')
    spec['identity_files']['registry_snapshot'] = str(ROOT / 'reports/defense_v1/planning/current_versions_snapshot_20261109_06.json')
    if DATA.exists() or RUN.exists():
        raise FileExistsError('Diagnostic output already exists')
    DATA.mkdir()
    for name, records in [('requests.jsonl', reqs), ('labels.jsonl', labels)]:
        (DATA / name).write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in records), encoding='utf-8')
    (DATA / 'experiment_spec.json').write_text(json.dumps(spec, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (DATA / 'manifest.json').write_text(json.dumps({'analysis_role':'engineering_only', 'forced_action':True, 'human_gold_complete':False, 'formal_effect_eligible':False, 'requests':4, 'input_manifest_sha256':sha(SOURCE / 'manifest.json'), 'runner_sha256':sha(Path(__file__))}, indent=2) + '\n', encoding='utf-8')
    original_factory, client = make_live_backend_factory(spec)

    def factory(method, seed, session_id):
        backend = original_factory('B5' if method == 'B5_FORCED' else method, seed, session_id)
        if method == 'B5_FORCED':
            backend.guard.action_selector = lambda decision, candidates: (
                ('hide_target_refill', frozenset({candidates[0].parent_doc_id})) if candidates
                else ('no_context_answer', frozenset()))
        return backend

    result = run_benchmark(DATA / 'experiment_spec.json', RUN, backend_factory=factory, score_client=client)
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)

if __name__ == '__main__':
    main()
