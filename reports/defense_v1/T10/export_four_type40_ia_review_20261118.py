"""Export already recorded IA items for source-grounding review without member labels."""

from collections import Counter, defaultdict
from hashlib import sha256
import json
import re

from inventory_four_type40_20261118 import (
    OUTPUT, OVERLAY, REPORT, ROOT, SOURCES, THREE_ROUND, digest, read, rows, verify,
)

EXTERNAL = REPORT / 'external_review/v2_reuse_deepseek-v4.1-flash_20261105_01/ia_review.jsonl'
PACKET = REPORT / 'four_type40_ia_review_packet_20261118.jsonl'
MANIFEST = REPORT / 'four_type40_ia_review_manifest_20261118.json'


def main():
    selected, _ = verify()
    docs = {q['source_doc_id']: q for q in read(OUTPUT)['documents']}
    source_text = {q['doc_id']: q['text'] for q in rows(SOURCES) if q['doc_id'] in docs}
    external = {q['query_id']: q for q in rows(EXTERNAL)}
    assert digest(EXTERNAL) == read(OVERLAY / 'manifest.json')['input_sha256'][EXTERNAL.relative_to(ROOT).as_posix()]
    prior = defaultdict(list)
    prior_requests = {q['request_id']: q for q in rows(THREE_ROUND / 'requests.jsonl')}
    for a in rows(THREE_ROUND / 'labels.jsonl'):
        if a['attack_type'] == 'ia':
            q = prior_requests[a['request_id']]
            prior[a['doc_id']].append({'id': q['request_id'], 'query': q['query'], 'reference': a['ground_truth']})
    overlay = defaultdict(list)
    overlay_requests = {q['request_id']: q for q in rows(OVERLAY / 'requests.jsonl')}
    for a in rows(OVERLAY / 'labels.jsonl'):
        if a['attack_type'] == 'ia' and not a['quality_flags']:
            q = overlay_requests[a['request_id']]
            overlay[a['doc_id']].append({'id': q['request_id'], 'query': q['query'], 'reference': a['ground_truth'],
                                         'parent_query_id': a['source_query_id']})
    originals = defaultdict(list)
    withheld = Counter()
    for item in rows(selected['queries']):
        doc, qid = item['doc_id'], item['query_id']
        if doc not in docs or item['attack_type'] != 'ia':
            continue
        if qid in external and external[qid]['decision'] != 'accept':
            withheld[external[qid]['decision']] += 1
            continue
        if item['validation']['status'] != 'accepted':
            continue
        p = item['payload']
        originals[doc].append({'id': qid, 'query': item['query_text'], 'reference': p['ground_truth'],
                               'question': p['question']})
    result = []
    for doc in sorted(docs):
        assert sha256(source_text[doc].encode('utf-8')).hexdigest() == docs[doc]['source_text_sha256']
        seen = set()
        candidates = []
        for origin, values in (('existing_three_round', prior[doc]), ('pending_overlay', overlay[doc]),
                               ('original_bank_not_externally_rejected', originals[doc])):
            for q in values:
                normalized = re.sub(r'\W+', ' ', q['query'].casefold()).strip()
                if normalized not in seen:
                    seen.add(normalized)
                    candidates.append(dict(q, origin=origin))
        result.append({'doc_id': doc, 'source_text': source_text[doc], 'candidates': candidates})
    PACKET.write_text(''.join(json.dumps(row, ensure_ascii=False) + '\n' for row in result), encoding='utf-8')
    manifest = {
        'status': 'pending_semantic_review', 'documents': len(result),
        'distinct_query_candidates': sum(len(row['candidates']) for row in result),
        'withheld_original_external_decisions': dict(withheld),
        'prior_exact_three_round_document_count': sum(len(v) == 3 for v in prior.values()),
        'review_requirements': [
            'Only fixed existing items can be selected, and the reference must agree with the full source.',
            'Read the actual wording and verify three distinct checkable propositions with supporting spans.',
            'Do not count the same proposition under different wording. Record unresolved items and per-document gaps.',
        ],
        'input_sha256': {str(p.relative_to(ROOT)): digest(p) for p in (
            OUTPUT, SOURCES, EXTERNAL, selected['queries'], OVERLAY/'manifest.json', THREE_ROUND/'manifest.json')},
        'output_sha256': {PACKET.name: digest(PACKET)}, 'human_reviewed': False, 'formal_effect_eligible': False,
    }
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f"{manifest['documents']} source documents; {manifest['distinct_query_candidates']} distinct candidate records; pending semantic review")


if __name__ == '__main__':
    main()
