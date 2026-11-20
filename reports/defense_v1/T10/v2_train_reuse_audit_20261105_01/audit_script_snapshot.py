"""Offline coverage audit of the selected v2 train, without model/effect calls.

Proposed actions are structural engineering triage, not semantic/human approval.
No target is selected or excluded based on membership or attack outcomes.
"""
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from miaguard.query_bank.schema import document_sha256, validate_query_record
from miaguard.query_bank.storage import QueryBank, QueryBankPaths
from miaguard.query_bank.sessions import plan_partition_sessions

ROOT = Path(__file__).resolve().parents[3]
T10 = ROOT / 'reports/defense_v1/T10'
OUT = T10 / 'v2_train_reuse_audit_20261105_01'


def read(path):
    return [json.loads(x) for x in path.read_text(encoding='utf-8').splitlines() if x.strip()]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ws(text):
    return ' '.join(str(text).split())


def phrase_in(phrase, text):
    return bool(re.search(r'(?<!\w)' + re.escape(phrase) + r'(?!\w)', text, re.I))


def inspect_mask(payload, text, query):
    reasons, flags, details = [], [], {}
    passage, answers = payload.get('masked_text'), payload.get('answers')
    if not isinstance(passage, str) or not isinstance(answers, list) or not answers or any(not isinstance(a, str) or not a.strip() for a in answers):
        return ['masked_missing_inputs'], flags, details
    indices = [int(n) for n in re.findall(r'\[Mask_(\d+)\]', passage, re.I)]
    details['mask_count'] = len(indices)
    if sorted(indices) != list(range(1, len(answers) + 1)):
        reasons.append('masked_placeholder_answer_mismatch')
    else:
        restored = re.sub(r'\[Mask_(\d+)\]', lambda m: answers[int(m.group(1)) - 1], passage, flags=re.I)
        if restored != text:
            reasons.append('masked_source_reconstruction_mismatch')
    if ws(passage) not in ws(query):
        reasons.append('masked_passage_not_in_query')
    remaining = re.sub(r'\[Mask_\d+\]', '', passage, flags=re.I)
    leaked = [i + 1 for i, answer in enumerate(answers) if phrase_in(answer, remaining)]
    details['leaked_answer_positions'] = leaked
    if leaked:
        reasons.append('masked_answer_visible_in_remaining_passage')
    if len({a.casefold() for a in answers}) != len(answers):
        flags.append('masked_duplicate_answer_values')
    if any(re.fullmatch(r'[\d.,]+', a) for a in answers):
        flags.append('masked_numeric_selection_review')
    if 'json' not in query.casefold():
        reasons.append('masked_json_output_instruction_missing')
    return reasons, flags, details


def main():
    selection_path = T10 / 'legacy_reuse_selection_20261104.json'
    selection = json.loads(selection_path.read_text(encoding='utf-8'))
    if (selection['bank_id'], selection['split_id'], selection['partition']) != ('ag_news_queries_v2', 'ag_news_threshold_v2', 'train'):
        raise ValueError('Wrong selected bank/split/partition')
    for item in selection['input_files'].values():
        if sha(ROOT / item['path']) != item['sha256']:
            raise ValueError('Selected input changed: ' + item['path'])
    bank_path = ROOT / 'data/query_banks/ag_news_queries_v2/ag_news'
    split_path = ROOT / 'data/query_bank_splits/ag_news_threshold_v2.json'
    source_path = ROOT / 'data/runs/20260717-ag-news-four-medium/ag_news/target_docs.jsonl'
    index_path = ROOT / 'data/vector_stores/20260717-ag-news-four-medium/ag_news/documents.jsonl'
    split = json.loads(split_path.read_text(encoding='utf-8'))
    if split['query_bank']['bank_id'] != selection['bank_id'] or split['query_bank']['queries_sha256'] != sha(bank_path / 'queries.jsonl'):
        raise ValueError('Split/bank identity mismatch')
    ids = set(split['partitions']['train']['doc_ids'])
    source_rows = read(source_path)
    sources = {r['doc_id']: r for r in source_rows if r['doc_id'] in ids}
    bank_docs = {r['doc_id']: r for r in read(bank_path / 'documents.jsonl') if r['doc_id'] in ids}
    index_rows = read(index_path)
    index = {r['doc_id']: r for r in index_rows}
    queries = [r for r in read(bank_path / 'queries.jsonl') if r['doc_id'] in ids and r.get('validation', {}).get('status') == 'accepted']
    if len(ids) != 60 or len(sources) != 60 or len(bank_docs) != 60 or len(index) != len(index_rows) or len(queries) != 4579:
        raise ValueError('Unexpected input count or duplicate source/index IDs')
    if len({r['query_id'] for r in queries}) != len(queries):
        raise ValueError('Duplicate query ID')
    doc_checks = {}
    for did in sorted(ids):
        source, meta = sources[did], bank_docs[did]
        issues = []
        if document_sha256(source['text']) != meta['source_document_sha256']:
            issues.append('bank_doc_source_hash_mismatch')
        if source['membership_label'] != meta['membership_label'] or int(meta['membership_label']) != int(did in index):
            issues.append('membership_does_not_match_original_index')
        if did in index and source['text'] != index[did]['text']:
            issues.append('indexed_text_differs_from_source')
        doc_checks[did] = issues
    # Existing planner is exercised without invoking any model. Its grouping is
    # an engineering layout; this audit does not judge semantic progression.
    planner = {}
    try:
        bank = QueryBank.load(QueryBankPaths(ROOT, selection['bank_id'], 'ag_news'))
        sessions = plan_partition_sessions(bank, split, 'train', target_turns=5)
        session_ids = [r['query_id'] for s in sessions for r in s.queries]
        planner = {'status': 'passed' if Counter(session_ids) == Counter(r['query_id'] for r in queries) else 'coverage_mismatch',
                   'sessions': len(sessions), 'turn_count_distribution': dict(Counter(len(s.queries) for s in sessions)),
                   'session_attack_counts': dict(Counter(s.attack_type for s in sessions)),
                   'semantic_progression_verified': False}
    except Exception as exc:
        planner = {'status': 'failed', 'reason': f'{type(exc).__name__}: {exc}', 'semantic_progression_verified': False}
    records = []
    for r in queries:
        did, attack, payload, query = r['doc_id'], r['attack_type'], r['payload'], r['query_text']
        source, meta = sources[did], bank_docs[did]
        fatal, rewrite, supplement, flags, details = list(doc_checks[did]), [], [], [], {}
        try:
            validate_query_record(r)
        except (ValueError, KeyError, TypeError) as exc:
            fatal.append('legacy_schema_error:' + str(exc))
        if r['source_document_sha256'] != meta['source_document_sha256'] or r['membership_label'] != meta['membership_label']:
            fatal.append('query_source_identity_mismatch')
        if attack == 'benign':
            supplement.append('normal_answerability_answer_evidence_and_review_missing')
            details['category'] = payload.get('category')
            details['difficulty'] = payload.get('difficulty')
        elif attack == 'direct_rag_mia':
            target = payload.get('target_text')
            if not isinstance(target, str) or target != source['text']:
                fatal.append('direct_target_source_mismatch')
            elif ws(target) not in ws(query):
                rewrite.append('direct_target_not_visible_in_query')
        elif attack == 's2_mia':
            prefix = payload.get('prefix')
            if not isinstance(prefix, str) or not prefix.strip() or not ws(source['text']).startswith(ws(prefix)):
                fatal.append('s2_prefix_source_mismatch')
            if not isinstance(prefix, str) or ws(prefix) not in ws(query):
                rewrite.append('s2_prefix_not_visible_in_query')
            details['benchmark_target_text_derivable_from_source'] = True
            flags.append('s2_adapter_must_supply_original_target_text_and_embedding_identity')
        elif attack == 'masked_mia':
            a, b, c = inspect_mask(payload, source['text'], query)
            rewrite.extend(a); flags.extend(b); details.update(c)
        elif attack == 'ia':
            question = payload.get('question', '')
            if ws(question) not in ws(query):
                rewrite.append('ia_question_not_visible_in_query')
            if payload.get('ground_truth') not in {'yes', 'no', 'unknown'}:
                fatal.append('ia_ground_truth_invalid')
            if re.match(r'^\s*(?:what|who|whom|whose|when|where|why|how|which)\b', question, re.I):
                flags.append('ia_open_question_with_categorical_answer_review')
            flags.append('ia_source_ground_truth_and_probe_semantics_pending_review')
        else:
            fatal.append('unsupported_attack_type')
        action = 'not_applicable' if fatal else 'needs_rewrite' if rewrite else 'needs_annotation' if supplement else 'reuse_content_after_adapter'
        records.append({'query_id': r['query_id'], 'doc_id': did, 'attack_type': attack,
                        'recommended_action': action, 'fatal_issues': fatal, 'rewrite_reasons': rewrite,
                        'annotation_gaps': supplement, 'review_flags': flags, 'checks': details,
                        'semantic_review_status': 'pending', 'human_reviewed': False, 'formal_effect_eligible': False})
    OUT.mkdir(exist_ok=False)
    output = OUT / 'query_reuse_audit.jsonl'
    output.write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in records), encoding='utf-8')
    actions = Counter(r['recommended_action'] for r in records)
    by_type = {kind: dict(Counter(r['recommended_action'] for r in records if r['attack_type'] == kind)) for kind in sorted({r['attack_type'] for r in records})}
    issues = Counter(code for r in records for field in ('fatal_issues', 'rewrite_reasons', 'annotation_gaps', 'review_flags') for code in r[field])
    summary = {'status': 'complete_structural_audit_semantic_review_pending', 'bank_id': selection['bank_id'],
               'split_id': selection['split_id'], 'partition': 'train', 'documents': len(ids), 'queries': len(records),
               'action_counts': dict(actions), 'by_attack_type': by_type, 'issue_counts': dict(issues),
               'document_identity_issue_count': sum(bool(v) for v in doc_checks.values()), 'session_planner': planner,
               'semantic_review_complete': False, 'human_gold_complete': False, 'formal_effect_eligible': False,
               'classification_scope': 'Engineering content-reuse triage only; no row is accepted as formal gold or ready for current benchmark without an adapter.',
               'limits': ['All proposed actions are based on explicit structural tests; mechanisms, normal evidence and semantic quality require further review.',
                         'Membership labels are compared only to validate original-index identity; not used to choose queries or estimate effectiveness.',
                         'IA open-question flags are review candidates, not automatic correctness or attack-success judgments.',
                         'Session grouping tests layout/coverage only, not natural conversation or historical trace compatibility.',
                         'Masked baseline uses multiple numbered masks; this audit does not silently convert it to new single-mask templates.']}
    (OUT / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    files = [selection_path, bank_path / 'manifest.json', bank_path / 'queries.jsonl', bank_path / 'documents.jsonl', split_path, source_path, index_path,
             ROOT / 'src/miaguard/query_bank/schema.py', ROOT / 'src/miaguard/query_bank/sessions.py',
             ROOT / 'src/miaguard/defense_benchmark.py', ROOT / 'src/miaguard/defense_benchmark_live.py', Path(__file__).resolve()]
    (OUT / 'audit_script_snapshot.py').write_bytes(Path(__file__).read_bytes())
    manifest = {'status': 'complete', 'analysis_role': 'offline_structural_audit', 'registry_revision': '2026-11-05-r01',
                'formal_effect_eligible': False, 'input_sha256': {p.relative_to(ROOT).as_posix(): sha(p) for p in files},
                'output_sha256': {name: sha(OUT / name) for name in ('query_reuse_audit.jsonl', 'summary.json', 'audit_script_snapshot.py')}}
    (OUT / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'queries': len(records), 'by_type': by_type, 'issues': dict(issues), 'session_planner': planner}, ensure_ascii=False))


if __name__ == '__main__':
    main()
