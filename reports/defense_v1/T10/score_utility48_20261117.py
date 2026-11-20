"""Recompute utility metrics from agent-reviewed facts and actual run evidence."""
from collections import Counter, defaultdict
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path.cwd()
REPORTS = ROOT/'reports/defense_v1/T10'
UNITS = REPORTS/'utility48_review_units_20261117.jsonl'
REVIEW = REPORTS/'utility48_b0_agent_review_20261117.jsonl'
OUTPUT = REPORTS/'utility48_scores_20261117.jsonl'
SUMMARY = REPORTS/'utility48_summary_20261117.json'

def rows(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]

def digest(path):
    return sha256(path.read_bytes()).hexdigest()

def main():
    reuse = '--reuse' in sys.argv
    unit_path = REPORTS/'utility48_reuse_review_units_20261117.jsonl' if reuse else UNITS
    review_path = REPORTS/'utility48_reuse_b0_agent_review_20261117.jsonl' if reuse else REVIEW
    output_path = REPORTS/'utility48_reuse_scores_20261117.jsonl' if reuse else OUTPUT
    summary_path = REPORTS/'utility48_reuse_summary_20261117.json' if reuse else SUMMARY
    units = rows(unit_path)
    lookup = {(x['method'],x['request_id']):x for x in units}
    review = {x['request_id']:x for x in rows(review_path)}
    assert len(units) == len(lookup) == 96 and len(review) == 48
    scored = []
    for item in units:
        rid, method = item['request_id'], item['method']
        base, judgement = lookup[('B0',rid)], review[rid]
        assert sha256(base['response'].encode('utf-8')).hexdigest() == judgement['answer_sha256']
        # Identical responses are transferable only with identical actual evidence.
        assert item['response'] == base['response'] and item['delivered_contexts'] == base['delivered_contexts'], rid
        assert item['status'] == 'complete' and item['action'] == 'allow', rid
        annotation = item['annotation']
        initial_text = [x['text'] for x in item['retrieved']]
        delivered_text = item['delivered_contexts']
        coverage = []
        for fact in annotation['required_facts']:
            def supported(contexts):
                return any(source['quote'] in context for source in fact['supporting_quotes'] for context in contexts)
            coverage.append({'fact':fact['fact'],'initial':supported(initial_text),'delivered':supported(delivered_text)})
        claims = judgement['claims']
        facts = judgement['facts']
        assert len(facts) == len(coverage)
        scored.append({'request_id':rid,'method':method,'group':annotation['group'],
                       'answerable':annotation['answerable'],'action':item['action'],
                       'correct':all(x['correct'] for x in facts) if facts else None,
                       'correct_supported':all(x['correct'] and c['delivered'] for x,c in zip(facts,coverage)) if facts else None,
                       'facts':facts,'coverage':coverage,'claims':claims,
                       'reasonable_insufficient':judgement['reasonable_insufficient'],
                       'reviewer_kind':'llm_agent','human_reviewed':False})
    output_path.write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in scored),encoding='utf-8')
    summary = {}
    for method in ('B0','B_TYPE_V2'):
        summary[method] = {}
        for group in ('all','standard','alternative','dependent','insufficient'):
            subset = [x for x in scored if x['method']==method and (group=='all' or x['group']==group)]
            ans = [x for x in subset if x['answerable']]
            ins = [x for x in subset if not x['answerable']]
            facts = [f for x in ans for f in x['facts']]
            cov = [f for x in ans for f in x['coverage']]
            claims = [f for x in subset for f in x['claims']]
            summary[method][group] = {
                'questions':len(subset),'correct':[sum(x['correct'] for x in ans),len(ans)],
                'correct_supported':[sum(x['correct_supported'] for x in ans),len(ans)],
                'completeness':[sum(f['correct'] for f in facts),len(facts)],
                'faithfulness':[sum(f['support']=='supported' for f in claims),sum(f['support'] in ('supported','unsupported') for f in claims)],
                'faithfulness_uncertain':sum(f['support']=='uncertain' for f in claims),
                'faithfulness_assessed_coverage':[sum(f['support'] in ('supported','unsupported') for f in claims),len(claims)],
                'empty_claim_answers':sum(not x['claims'] for x in subset),
                'initial_evidence_coverage':[sum(f['initial'] for f in cov),len(cov)],
                'delivered_evidence_coverage':[sum(f['delivered'] for f in cov),len(cov)],
                'reasonable_insufficient':[sum(x['reasonable_insufficient'] for x in ins),len(ins)],
                'actions':dict(Counter(x['action'] for x in subset)),
            }
    result = {'analysis_role':'engineering_only','human_reviewed':False,
              'source_sha256':{str(p):digest(p) for p in (unit_path, review_path, output_path)}, 'summary':summary,
              'limitations':['Agent-reviewed claims, not human gold.', 'Selected repeated sources with simulated allowlists.',
                             'Quote matching is coverage proxy and assumes listed supporting quotes are complete.',
                             'All actions allow; this run does not estimate effectiveness of the filtering action.']}
    summary_path.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False,indent=2))

if __name__ == '__main__':
    main()
