"""Record post-hoc agent assessment of candidate query similarity.

This never asserts the historic origin of a newly authored query.
"""
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path

ROOT=Path.cwd()
INPUT=ROOT/'reports/defense_v1/T10/utility48_lineage_candidates_20261117.json'
OUTPUT=ROOT/'reports/defense_v1/T10/utility48_lineage_review_20261117.json'

# IDs below point to the already available queries, matched after the run.
EQUIVALENT={
    1:'ng_normal_03',2:'ng_normal_05',5:'ng_normal_07',
    11:'ag_news:ag_news_teacher_00000532:benign:generated:0005',
    22:'ng_normal_01',23:'ng_normal_04',25:'ng_normal_08',45:'ng_normal_07',
}
PARTIAL={24:'ng_normal_05',7:'bp_treo_3'}

def main():
    data=json.loads(INPUT.read_text(encoding='utf8'))
    result=[]
    for case in data['cases']:
        number=int(case['request_id'].split('_')[2])
        chosen=EQUIVALENT.get(number) or PARTIAL.get(number)
        matched=next((x for x in case['candidates'] if x['id']==chosen), None) if chosen else None
        assert not chosen or matched is not None, (number,chosen)
        relation='posthoc_semantic_equivalent' if number in EQUIVALENT else ('partial_fact_overlap' if number in PARTIAL else 'no_equivalent_found_in_top_candidates')
        result.append({'request_id':case['request_id'],'relationship':relation,
                       'matched_query':matched,
                       'limitation':'Post-hoc similarity; not proof of actual reuse or of exhaustive search.'})
    output={'reviewer_kind':'llm_agent','reviewer_model':'gpt-6.1-terra','human_reviewed':False,
            'scope':'Manual semantic review of up to five similarity-ranked queries per target document.',
            'counts':dict(Counter(x['relationship'] for x in result)), 'cases':result,
            'input_sha256':sha256(INPUT.read_bytes()).hexdigest(),
            'limits':['Matching performed after experiment, not evidence of selection before experiment.',
                      'Top-five similarity search is not exhaustive; no equivalent found is not proof of absence.']}
    OUTPUT.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps(output['counts'],ensure_ascii=False))

if __name__=='__main__':main()
