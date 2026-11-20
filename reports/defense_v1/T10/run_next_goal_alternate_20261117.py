"""Run a controlled real-model refill probe after the primary run finishes."""
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path

from miaguard.defense_benchmark_live import make_live_backend_factory
from miaguard.defense_contracts import OnlineRequest

ROOT = Path.cwd()
SPEC = ROOT / 'data/defense_datasets/next_goal_v2_train_20261117_01/experiment_spec.json'
PREREG = ROOT / 'reports/defense_v1/T10/next_goal_alternate_evidence_prereg_20261117.json'
PARENT = ROOT / 'data/defense_v1_runs/next-goal-paired-20261117-01/run_manifest.json'
OUTPUT = ROOT / 'data/defense_v1_runs/next-goal-alternate-20261117-01'


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf8')


def main():
    config = json.loads(SPEC.read_text(encoding='utf8'))
    control = json.loads(PREREG.read_text(encoding='utf8'))
    parent = json.loads(PARENT.read_text(encoding='utf8'))
    assert parent['status'] == 'completed', 'Primary run must finish before loading another model.'
    index_docs = Path(config['identity_files']['index_documents'])
    assert digest(index_docs) == control['source_sha256']
    assert digest(ROOT / 'src/miaguard/defense_benchmark_live.py') == parent['files_sha256']['code:defense_benchmark_live.py']
    for name, path in config['identity_files'].items():
        assert digest(Path(path)) == parent['files_sha256']['identity:' + name], name
    OUTPUT.mkdir(exist_ok=False)
    manifest = {'schema_version': 1, 'status': 'running', 'analysis_role': 'engineering_only',
                'human_reviewed': False, 'formal_effect_eligible': False,
                'started_at': datetime.now(timezone.utc).isoformat(),
                'input_sha256': {str(p): digest(p) for p in [SPEC, PREREG, PARENT, Path(__file__).resolve()]},
                'parent_identity_sha256': parent['identity_sha256'], 'expected': 2,
                'scope': 'Forced action experiment with simulated allowlist; not an online locator evaluation.'}
    write(OUTPUT / 'run_manifest.json', manifest)
    try:
        factory, _client = make_live_backend_factory(config)
        allowed = frozenset(control['controlled_allowed_doc_ids'])
        excluded = frozenset(control['controlled_excluded_parent_ids'])
        events = []
        for method in ('allow', 'forced_hide_target_refill'):
            sid = 'alternate_' + method
            backend = factory('B0', config['seed'], sid)
            if method == 'forced_hide_target_refill':
                backend.guard.action_selector = lambda decision, candidates: ('hide_target_refill', excluded)
            event = backend.run(OnlineRequest(sid, sid, control['question'], allowed))
            event['control_method'] = method
            events.append(event)
        with (OUTPUT / 'events.jsonl').open('x', encoding='utf8') as f:
            for event in events:
                f.write(json.dumps(event, ensure_ascii=False) + '\n')
        for event in events:
            assert event['status'] == 'complete', event.get('reason')
            assert set(event['retrieved_doc_ids']) <= allowed
            delivered = event['ledger_event']['delivered_evidence']
            assert all(x['parent_doc_id'] in allowed for x in delivered)
            if event['control_method'] == 'forced_hide_target_refill':
                assert not excluded & {x['parent_doc_id'] for x in delivered}
        manifest.update(status='completed', completed=len(events), failed=0,
                        events_sha256=digest(OUTPUT / 'events.jsonl'), finished_at=datetime.now(timezone.utc).isoformat())
        write(OUTPUT / 'run_manifest.json', manifest)
        print(json.dumps({'status': manifest['status'], 'completed': len(events),
                          'actions': [x['action'] for x in events]}, ensure_ascii=False))
    except Exception as exc:
        manifest.update(status='failed', error=f'{type(exc).__name__}: {exc}',
                        finished_at=datetime.now(timezone.utc).isoformat())
        write(OUTPUT / 'run_manifest.json', manifest)
        raise


if __name__ == '__main__':
    main()
