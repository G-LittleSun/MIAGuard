"""Verify external v2 review contract and identities without accepting semantics."""
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
T10 = ROOT / 'reports/defense_v1/T10'
PACKET = T10 / 'v2_reuse_review_packet_20261105_01'
REVIEW = T10 / 'external_review/v2_reuse_deepseek-v4.1-flash_20261105_01'
OUT = T10 / 'v2_reuse_review_integration_20261105_01'


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def read(p):
    raw = p.read_bytes()
    if raw.startswith(b'\xef\xbb\xbf'):
        raise ValueError('BOM: ' + str(p))
    return [json.loads(x) for x in raw.decode('utf-8').splitlines() if x.strip()]


def main():
    OUT.mkdir(exist_ok=True)
    output = OUT / 'structural_validation.json'
    if output.exists():
        raise FileExistsError(output)
    m = json.loads((REVIEW / 'review_manifest.json').read_text(encoding='utf-8'))
    p = json.loads((PACKET / 'manifest.json').read_text(encoding='utf-8'))
    sources = {r['doc_id']: r['text'] for r in read(PACKET / 'sources.jsonl')}
    originals_ia, originals_mask = read(PACKET / 'ia_items.jsonl'), read(PACKET / 'masked_items.jsonl')
    ia, masked = read(REVIEW / 'ia_review.jsonl'), read(REVIEW / 'masked_review.jsonl')
    errors, warnings, mask_checks = [], [], []
    paths = {'packet/' + name: PACKET / name for name in
             ['manifest.json', 'sources.jsonl', 'ia_items.jsonl', 'masked_items.jsonl', 'REVIEW_GUIDE_ZH.md']}
    paths.update({'upstream/queries.jsonl': ROOT / 'data/query_banks/ag_news_queries_v2/ag_news/queries.jsonl',
                  'upstream/ag_news_threshold_v2.json': ROOT / 'data/query_bank_splits/ag_news_threshold_v2.json',
                  'upstream/target_docs.jsonl': ROOT / 'data/runs/20260717-ag-news-four-medium/ag_news/target_docs.jsonl',
                  'upstream/reuse_audit_manifest.json': T10 / 'v2_train_reuse_audit_20261105_01/manifest.json',
                  'upstream/query_reuse_audit.jsonl': T10 / 'v2_train_reuse_audit_20261105_01/query_reuse_audit.jsonl'})
    if set(paths) != set(m['input_sha256']):
        errors.append('review input identity keys')
    for name, path in paths.items():
        if m['input_sha256'].get(name) != sha(path):
            errors.append('review input hash: ' + name)
    for name in ['ia_review.jsonl', 'masked_review.jsonl', 'review_summary.md']:
        if sha(REVIEW / name) != m['output_files'][name]['sha256']:
            errors.append('review output hash: ' + name)
    for name, digest in p['files_sha256'].items():
        if sha(PACKET / name) != digest:
            errors.append('packet file hash: ' + name)
    for name, digest in p['input_sha256'].items():
        if sha(ROOT / name) != digest:
            errors.append('packet upstream hash: ' + name)
    if len(ia) != len(originals_ia) or len(ia) != 206 or len(masked) != len(originals_mask) or len(masked) != 60:
        errors.append('row counts')
    decisions = {'accept', 'rewrite', 'reject', 'uncertain'}
    required_ia = {'query_id', 'doc_id', 'decision', 'reason', 'evidence_quotes', 'corrected_query',
                   'corrected_question', 'corrected_ground_truth', 'notes'}
    required_mask = {'review_id', 'doc_id', 'decision', 'reason', 'corrected_masked_text',
                     'corrected_answers', 'corrected_queries', 'notes'}
    if len({r['query_id'] for r in ia}) != len(ia) or len({r['review_id'] for r in masked}) != len(masked):
        errors.append('duplicate review IDs')
    for old, row in zip(originals_ia, ia):
        rid = row.get('query_id', '?')
        if set(row) != required_ia or row.get('query_id') != old['query_id'] or row.get('doc_id') != old['doc_id']:
            errors.append('IA identity/fields: ' + rid)
        if row.get('decision') not in decisions or not str(row.get('reason', '')).strip():
            errors.append('IA decision/reason: ' + rid)
        quotes = row.get('evidence_quotes')
        if not isinstance(quotes, list) or any(not isinstance(q, str) or not q or q not in sources[old['doc_id']] for q in quotes):
            errors.append('IA evidence: ' + rid)
        fields = ['corrected_query', 'corrected_question', 'corrected_ground_truth']
        if row['decision'] in {'reject', 'uncertain'}:
            if any(row[k] is not None for k in fields):
                errors.append('IA null contract: ' + rid)
        else:
            if not all(isinstance(row[k], str) and row[k].strip() for k in fields) or row['corrected_ground_truth'] not in {'yes', 'no', 'unknown'}:
                errors.append('IA corrected fields: ' + rid)
            if row['decision'] == 'accept' and [row[k] for k in fields] != [old['query'], old['question'], old['ground_truth_suggestion']]:
                errors.append('IA accept equality: ' + rid)
            if row['corrected_question'] not in row['corrected_query']:
                warnings.append({'kind': 'ia_question_not_literal_substring', 'id': rid})
    for old, row in zip(originals_mask, masked):
        rid = row.get('review_id', '?')
        if set(row) != required_mask or row.get('review_id') != old['review_id'] or row.get('doc_id') != old['doc_id']:
            errors.append('Masked identity/fields: ' + rid)
        if row.get('decision') not in decisions or not str(row.get('reason', '')).strip():
            errors.append('Masked decision/reason: ' + rid)
        if row['decision'] in {'reject', 'uncertain'}:
            if any(row[k] is not None for k in ['corrected_masked_text', 'corrected_answers', 'corrected_queries']):
                errors.append('Masked null contract: ' + rid)
            continue
        text, answers, queries = row['corrected_masked_text'], row['corrected_answers'], row['corrected_queries']
        if not isinstance(text, str) or not isinstance(answers, list) or not all(isinstance(x, str) and x for x in answers):
            errors.append('Masked corrected fields: ' + rid)
            continue
        indices = [int(n) for n in re.findall(r'\[Mask_(\d+)\]', text, re.I)]
        n = len(old['answers_suggestion'])
        if sorted(indices) != list(range(1, n + 1)) or len(answers) != n:
            errors.append('Masked numbering/count: ' + rid)
            continue
        restored = re.sub(r'\[Mask_(\d+)\]', lambda mat: answers[int(mat.group(1)) - 1], text, flags=re.I)
        if restored != sources[row['doc_id']]:
            errors.append('Masked exact reconstruction: ' + rid)
        remaining = re.sub(r'\[Mask_\d+\]', '', text, flags=re.I)
        leaked = [i + 1 for i, answer in enumerate(answers) if re.search(r'(?<!\w)' + re.escape(answer) + r'(?!\w)', remaining, re.I)]
        if leaked:
            errors.append('Masked passage leakage: ' + rid)
        if len(queries) != 5 or [x.get('query_id') for x in queries] != [x['query_id'] for x in old['queries']]:
            errors.append('Masked five-query identities: ' + rid)
        instruction_leaks = []
        for q in queries:
            value = q.get('query', '')
            if set(q) != {'query_id', 'query'} or value.count(text) != 1 or 'json' not in value.casefold() or 'answers' not in value:
                errors.append('Masked query passage/format: ' + q.get('query_id', rid))
            instruction = value.replace(text, '', 1)
            found = [a for a in answers if re.search(r'(?<!\w)' + re.escape(a) + r'(?!\w)', instruction, re.I)]
            if found:
                instruction_leaks.append({'query_id': q['query_id'], 'words': found})
        if instruction_leaks:
            warnings.append({'kind': 'masked_answer_in_instruction', 'id': rid, 'queries': instruction_leaks})
        if indices != sorted(indices):
            warnings.append({'kind': 'masked_nonascending_number_order', 'id': rid})
        if any(re.search(r'\d', a) for a in answers):
            warnings.append({'kind': 'masked_answer_contains_digits', 'id': rid})
        if len({a.casefold() for a in answers}) != n:
            warnings.append({'kind': 'masked_repeated_answer_value', 'id': rid})
        if row['decision'] == 'accept' and [text, answers, queries] != [old['masked_text'], old['answers_suggestion'], old['queries']]:
            errors.append('Masked accept equality: ' + rid)
        mask_checks.append({'review_id': rid, 'payload_changed': text != old['masked_text'] or answers != old['answers_suggestion'],
                            'instruction_leaks': instruction_leaks, 'mask_number_order': indices})
    counts = {'ia': dict(Counter(r['decision'] for r in ia)), 'masked': dict(Counter(r['decision'] for r in masked))}
    for kind in counts:
        actual = {d: counts[kind].get(d, 0) for d in decisions}
        if actual != m['decision_counts'][kind]:
            errors.append('decision counts: ' + kind)
    if m['status'] != 'complete' or m['partial'] or m['scope']['unreviewed_ids'] or m['human_reviewed'] or m['formal_effect_eligible']:
        errors.append('review completion/eligibility')
    result = {'status': 'passed' if not errors else 'failed', 'errors': errors, 'decision_counts': counts,
              'review_manifest_sha256': sha(REVIEW / 'review_manifest.json'), 'input_hashes_checked': len(paths),
              'output_hashes_checked': 3, 'warnings': warnings,
              'warning_counts': dict(Counter(r['kind'] for r in warnings)), 'masked_checks': mask_checks,
              'ia_ground_truth_counts': dict(Counter(r['corrected_ground_truth'] for r in ia if r['decision'] in {'accept', 'rewrite'})),
              'limits': ['Structural contract/quoted evidence only; not semantic gold or attack effectiveness.',
                        'Instruction word overlap is a flagged concern; common instruction words need manual handling.',
                        'Actual provider runtime model identity cannot be independently established from submitted metadata.']}
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    (OUT / 'verifier_snapshot.py').write_bytes(Path(__file__).read_bytes())
    print(json.dumps({k: result[k] for k in ['status', 'errors', 'decision_counts', 'warning_counts', 'ia_ground_truth_counts']}, ensure_ascii=False))
    if errors:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
