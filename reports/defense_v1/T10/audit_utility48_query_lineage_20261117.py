"""Find same-source v2 and prior-development query candidates, without asserting lineage."""
from collections import defaultdict
from difflib import SequenceMatcher
from hashlib import sha256
import json
from pathlib import Path
import re

ROOT=Path.cwd()
BANK=ROOT/'data/query_banks/ag_news_queries_v2/ag_news/queries.jsonl'
COHORT=ROOT/'data/defense_datasets/utility48_v2_train_20261117_01/normal_rubric.jsonl'
PRIOR=ROOT/'data/defense_datasets/next_goal_v2_train_20261117_01'
OUT=ROOT/'reports/defense_v1/T10/utility48_lineage_candidates_20261117.json'

def rows(path):
    return [json.loads(s) for s in path.read_text(encoding='utf8').splitlines() if s.strip()]

def normalize(s):
    return ' '.join(re.findall(r'[a-z0-9]+',s.lower()))

def main():
    by_doc=defaultdict(list)
    for q in rows(BANK):
        if q.get('traffic_type')=='benign':
            by_doc[q['doc_id']].append({'source':'v2_bank','id':q['query_id'],'query':q['query_text']})
    old_requests={q['request_id']:q for q in rows(PRIOR/'requests.jsonl')}
    for label in rows(PRIOR/'labels.jsonl'):
        if label.get('traffic_type')=='benign' and label['request_id'] in old_requests:
            q=old_requests[label['request_id']]
            by_doc[label['doc_id']].append({'source':'prior_development','id':q['request_id'],'query':q['query']})
    result=[]
    for item in rows(COHORT):
        candidates=[]
        for old in by_doc[item['target_doc_id']]:
            ratio=SequenceMatcher(None,normalize(item['query']),normalize(old['query'])).ratio()
            if ratio>=0.48:
                candidates.append(dict(old,similarity=round(ratio,4)))
        candidates.sort(key=lambda x:(-x['similarity'],x['id']))
        result.append({'request_id':item['request_id'],'source_doc_id':item['target_doc_id'],
                       'query':item['query'],'candidates':candidates[:5]})
    output={'status':'candidates_only','semantic_review_required':True,'cases':result,
            'input_sha256':{str(p):sha256(p.read_bytes()).hexdigest() for p in
                            [BANK,COHORT,PRIOR/'requests.jsonl',PRIOR/'labels.jsonl']}}
    OUT.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print('Cases:',len(result),'with same-document candidates:',sum(bool(x['candidates']) for x in result))

if __name__=='__main__':main()
