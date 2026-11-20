import json
import pytest

from miaguard import defense_dataset


def export_dev_cohort(*args):
    return defense_dataset.export_dev_cohort(*args)


def fixture_data():
    docs = [{'doc_id': 'd', 'parent_doc_id': 'd', 'duplicate_group_id': 'd'}]
    sessions = [{'session_id': 's', 'source_variant_id': 'v', 'task_family': 'single_fact',
                 'source_doc_ids': ['d'], 'review_status': 'pending', 'turns': [
                     {'request_id': 'r', 'turn': 1, 'query': 'What happened?',
                      'answerable': True, 'reference_answer_suggestion': 'It happened.',
                      'gold_evidence_ids': ['d']}]}]
    return docs, sessions


def test_exports_separate_online_offline_with_lineage(tmp_path):
    docs, sessions = fixture_data()
    out = tmp_path / 'version'
    export_dev_cohort(out, 'dev-v1', sessions, docs, {'d'}, {'d'}, {'cohort': 'abc'})
    online = json.loads((out / 'normal_requests.jsonl').read_text().strip())
    offline = json.loads((out / 'normal_tasks.jsonl').read_text().strip())
    manifest = json.loads((out / 'manifest.json').read_text())
    assert online == {'request_id': 'r', 'session_id': 's', 'query': 'What happened?'}
    assert offline['source_variant_id'] == 'v' and offline['gold_evidence_ids'] == ['d']
    assert manifest['formal_effect_eligible'] is False and manifest['replay_eligible'] is False


def test_refuses_missing_index_or_existing_destination(tmp_path):
    docs, sessions = fixture_data()
    out = tmp_path / 'version'
    with pytest.raises(ValueError, match='partition index'):
        export_dev_cohort(out, 'dev-v1', sessions, docs, set(), {'d'}, {'cohort': 'abc'})
    assert not out.exists()
    out.mkdir()
    with pytest.raises(FileExistsError):
        export_dev_cohort(out, 'dev-v1', sessions, docs, {'d'}, {'d'}, {'cohort': 'abc'})


def test_refuses_duplicate_request_identity(tmp_path):
    docs, sessions = fixture_data()
    sessions[0]['turns'].append(dict(sessions[0]['turns'][0], turn=2))
    with pytest.raises(ValueError, match='Duplicate request'):
        export_dev_cohort(tmp_path / 'version', 'dev-v1', sessions, docs, {'d'}, {'d'}, {'cohort': 'abc'})
