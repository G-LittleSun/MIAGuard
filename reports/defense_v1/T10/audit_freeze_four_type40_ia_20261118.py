"""Check reviewed fixed IA fixtures and optionally freeze a balanced cohort."""

import argparse
from collections import Counter, defaultdict
from hashlib import sha256
import json
from pathlib import Path
import re

from export_four_type40_ia_review_20261118 import MANIFEST as PACKET_MANIFEST, PACKET
from freeze_four_type40_single_round_20261118 import RULES, export
from inventory_four_type40_20261118 import DATA, OUTPUT, REPORT, ROOT, THREE_ROUND, digest, read, rows, verify

AUDIT = REPORT / 'four_type40_ia_readiness_20261118.json'
SINGLE = DATA / 'four_type40_single_v2_train_20261118_01'
REVIEWS = [REPORT / f'four_type40_ia_review_{part}_20261118.json'
           for part in ('batch1', 'batch2', 'first_half', 'second_half')]
PREMISES = REPORT / 'four_type40_ia_premise_audit_20261118.json'
PREMISE_ALTERNATIVE = REPORT / 'four_type40_ia_premise_alternative_20261118.json'
ALL_YES = ('yes', 'yes', 'yes')


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def collect():
    selected, _ = verify()
    packet_manifest = read(PACKET_MANIFEST)
    assert digest(PACKET) == packet_manifest['output_sha256'][PACKET.name]
    for file, expected in packet_manifest['input_sha256'].items():
        assert digest(ROOT / file) == expected, file
    packet = {row['doc_id']: row for row in rows(PACKET)}
    assert len(packet) == packet_manifest['documents']
    inventory = {row['source_doc_id']: row for row in read(OUTPUT)['documents']}
    split = read(selected['split'])
    train = set(split['partitions']['train']['doc_ids'])
    index = {row.get('parent_doc_id') or row['doc_id'] for row in rows(selected['index_documents'])}
    assert set(packet) == set(inventory) == train
    for doc, row in packet.items():
        assert inventory[doc]['indexed'] == (doc in index)
        assert inventory[doc]['source_text_sha256'] == sha256(row['source_text'].encode()).hexdigest()

    history = {row['request_id']: row for row in rows(THREE_ROUND / 'lineage.jsonl')
               if 'evidence_quote' in row}
    reviews = {}
    rejected = {}
    premise_audit = read(PREMISES)
    for file, expected in premise_audit['input_sha256'].items():
        assert digest(REPORT / file) == expected, file
    premise_ids = set(premise_audit['answer_in_query_ids'])
    supplement = read(PREMISE_ALTERNATIVE)
    assert digest(REVIEWS[-1]) == supplement['source_review_sha256']
    supplied = [path for path in REVIEWS if path.is_file()]
    for path in supplied:
        batch = read(path)
        assert batch['human_reviewed'] is False
        for row in batch['document_reviews']:
            doc = row['doc_id']
            assert doc in packet and doc not in reviews
            flagged = set(row.get('answer_in_query_ids', []))
            decisions = row['decisions']
            assert flagged <= {decision[0] for decision in decisions}, doc
            candidates = {q['id']: q for q in packet[doc]['candidates']}
            alternatives = {a['replaces_candidate_id']: a for a in row.get('alternate_valid_candidates', [])
                            if a['replaces_candidate_id'] in flagged and not a['answer_in_query']}
            replaced = []
            for qid, proposition, quote in decisions:
                alternate = alternatives.get(qid)
                if alternate:
                    q = candidates[alternate['candidate_id']]
                    assert (q['query'], q['reference']) == (alternate['query'], alternate['reference']), doc
                    replaced.append((q['id'], alternate['proposition'], alternate['evidence_quote']))
                    flagged.remove(qid)
                else:
                    replaced.append((qid, proposition, quote))
            if doc == supplement['doc_id']:
                old = supplement['replace_id']
                q = candidates[supplement['replacement_id']]
                assert old in flagged and q['reference'] == supplement['reference'] and supplement['place_first']
                replaced = [(q['id'], supplement['proposition'], supplement['evidence_quote'])] + [
                    decision for decision in replaced if decision[0] != old]
                flagged.remove(old)
            reviews[doc] = (replaced, path.name)
            premise_ids.update(flagged)
        for row in batch.get('rejected_documents', []):
            doc = row['doc_id']
            assert doc in packet and doc not in rejected
            rejected[doc] = row

    assert not set(rejected) & set(reviews)
    eligible = defaultdict(list)
    validated = {}
    reviewed_ids = set()
    for doc, row in packet.items():
        candidates = {candidate['id']: candidate for candidate in row['candidates']}
        prior = [q for q in candidates.values() if q['origin'] == 'existing_three_round']
        if prior:
            assert len(prior) == 3 and doc not in reviews and doc not in rejected
            prior.sort(key=lambda q: history[q['id']]['turn'])
            decisions = [(q['id'], '', history[q['id']]['evidence_quote']) for q in prior]
            origin = THREE_ROUND.name
        elif doc in reviews:
            decisions, origin = reviews[doc]
        else:
            continue
        assert len(decisions) == len({decision[0] for decision in decisions}) == 3, doc
        evidence = []
        for qid, proposition, quote in decisions:
            candidate = candidates[qid]
            assert quote and quote in row['source_text'], (doc, qid)
            reference = candidate['reference'].lower()
            assert reference in ('yes', 'no', 'unknown')
            reviewed_ids.add(qid)
            evidence.append({'original_id': qid, 'reference': reference, 'proposition': proposition,
                             'premise_supplies_reference': qid in premise_ids,
                             'source_quote': quote, 'source_review': origin})
        if not prior:
            assert len({item['proposition'] for item in evidence if item['proposition']}) == 3, doc
        pattern = tuple(item['reference'] for item in evidence)
        if 'unknown' in pattern:
            rejected[doc] = {'doc_id': doc, 'reason': 'Fewer than three definitive source facts in reviewed fixtures.',
                             'reviewed_reference_pattern': list(pattern), 'review_file': origin}
            continue
        if all(item['premise_supplies_reference'] for item in evidence):
            rejected[doc] = {'doc_id': doc, 'reason': 'All three reviewed questions have answer-bearing premises.',
                             'reviewed_reference_pattern': list(pattern), 'review_file': origin}
            continue
        eligible[pattern, int(doc in index)].append(doc)
        validated[doc] = [(candidates[item['original_id']], item) for item in evidence]
    assert premise_ids <= reviewed_ids
    for docs in eligible.values():
        docs.sort(key=lambda doc: sum(proof['premise_supplies_reference'] for _, proof in validated[doc]))
    return packet, validated, eligible, rejected, supplied, index


def choose(eligible, packet, limit):
    patterns = sorted({pattern for pattern, _ in eligible}, key=lambda p: (p != ALL_YES, p))
    chosen = {0: [], 1: []}
    seen = set()
    for pattern in patterns:
        possible = {0: [], 1: []}
        pattern_keys = set()
        for side in (0, 1):
            for doc in eligible[pattern, side]:
                key = ' '.join(re.findall(r'\w+', packet[doc]['source_text'].casefold()))
                if key not in seen and key not in pattern_keys:
                    possible[side].append((doc, key))
                    pattern_keys.add(key)
        count = min(limit - len(chosen[0]), len(possible[0]), len(possible[1]))
        for side, items in possible.items():
            for doc, key in items[:count]:
                chosen[side].append(doc)
                seen.add(key)
    matched = len(chosen[0])
    for side in (0, 1):
        for pattern in patterns:
            for doc in eligible[pattern, side]:
                key = ' '.join(re.findall(r'\w+', packet[doc]['source_text'].casefold()))
                if len(chosen[side]) < limit and key not in seen:
                    chosen[side].append(doc)
                    seen.add(key)
    return chosen, matched


def main(targets):
    packet, validated, eligible, rejected, supplied, index = collect()
    chosen, matched = choose(eligible, packet, targets or 20)
    patterns = [{'reference_pattern': list(pattern), 'indexed': len(eligible[pattern, 1]),
                 'not_indexed': len(eligible[pattern, 0])} for pattern in sorted({p for p, _ in eligible})]
    pending = sorted(set(packet) - set(validated) - set(rejected))
    single_docs = {row['doc_id'] for row in rows(SINGLE / 'labels.jsonl')}
    result = {
        'planned_per_membership_side': 20,
        'validated_source_counts': {'indexed': sum(doc in index for doc in validated),
                                    'not_indexed': sum(doc not in index for doc in validated)},
        'matched_per_membership_side': matched, 'reference_pattern_counts': patterns,
        'selected_premise_supplied_rounds': {str(side): sum(proof['premise_supplies_reference']
                                            for doc in docs for _, proof in validated[doc]) for side, docs in chosen.items()},
        'selected_doc_ids': {'indexed': chosen[1], 'not_indexed': chosen[0]}, 'pending_doc_ids': pending,
        'rejected_documents': list(rejected.values()), 'human_reviewed': False,
        'source_event_independence_proven': False, 'formal_effect_eligible': False,
        'input_sha256': {str(path.relative_to(ROOT)): digest(path)
                         for path in (PACKET, PACKET_MANIFEST, PREMISES, PREMISE_ALTERNATIVE, *supplied, THREE_ROUND / 'manifest.json',
                                      SINGLE / 'manifest.json', SINGLE / 'labels.jsonl', RULES, Path(__file__))},
    }
    write_json(AUDIT, result)
    print(f"Three supported rounds: {result['validated_source_counts']}; "
          f"matched reference patterns per side: {matched}; pending: {len(pending)}; insufficient: {len(rejected)}")
    if targets is None:
        return
    assert len(chosen[0]) == len(chosen[1]) == targets, 'Insufficient balanced source coverage.'

    records = []
    evidence_rows = []
    for side in (1, 0):
        for doc in chosen[side]:
            for turn, (candidate, proof) in enumerate(validated[doc], 1):
                original = candidate['id']
                ref = proof['reference']
                extra = {'ground_truth': ref, 'premise_supplies_reference': proof['premise_supplies_reference']}
                records.append((candidate['query'], 'ia', doc, side, extra, original,
                                candidate['origin'], candidate.get('parent_query_id') or original))
                evidence_rows.append({'request_id': f'q{len(records):03d}', 'source_doc_id': doc,
                                      'turn': turn, **proof})
    suffix = '' if targets == 20 else f'_partial_{targets}x2'
    folder = DATA / f'four_type40_ia{suffix}_v2_train_20261118_01'
    export(folder, records, 'Fixed three-round IA stratum. Development evaluation only.')
    snapshot = folder / 'selection_audit.json'
    write_json(snapshot, result)
    evidence_path = folder / 'review_evidence.jsonl'
    evidence_path.write_text(''.join(json.dumps(row, ensure_ascii=False) + '\n' for row in evidence_rows),
                             encoding='utf-8')
    manifest_path = folder / 'manifest.json'
    frozen = read(manifest_path)
    frozen.update(selection='Source-reviewed fixed records; prefer matching reference patterns, starting with three Yes; '
                           'within each pattern prefer fewer answer-bearing premises, then stable document order. '
                           'Exact duplicates excluded. '
                           'Any unbalanced reference patterns are reported. Both methods use the same fixed sessions.',
                  full_target_coverage=targets == 20, distinct_sessions=2 * targets, rounds_per_session=3,
                  reference_pattern_counts_by_membership=dict(Counter(
                      str((side, tuple(item['reference'] for _, item in validated[doc])))
                      for side, docs in chosen.items() for doc in docs)),
                  shared_with_single_turn_documents=len(single_docs & set(chosen[0] + chosen[1])))
    frozen['input_sha256'].update(result['input_sha256'])
    for path in (evidence_path, snapshot):
        frozen['output_sha256'][path.name] = digest(path)
    write_json(manifest_path, frozen)
    for name, expected in frozen['output_sha256'].items():
        assert digest(folder / name) == expected
    assert len(records) == targets * 6 and len(evidence_rows) == len(records)
    assert Counter(row['session_id'] for row in rows(folder / 'requests.jsonl')) == {
        f'ia_{doc}': 3 for doc in chosen[0] + chosen[1]}
    print(f'{folder.name}: {2 * targets} sources, {len(records) * 2} paired requests')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--targets-per-side', type=int, choices=range(1, 21))
    main(parser.parse_args().targets_per_side)
