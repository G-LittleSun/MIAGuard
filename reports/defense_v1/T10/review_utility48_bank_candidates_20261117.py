"""Record a small evidence-checked pool of directly reusable v2 queries."""
from hashlib import sha256
import json
from pathlib import Path

ROOT=Path.cwd()
BANK=ROOT/'data/query_banks/ag_news_queries_v2/ag_news/queries.jsonl'
DOCS=ROOT/'data/vector_stores/20260717-ag-news-four-medium/ag_news/documents.jsonl'
SPLIT=ROOT/'data/query_bank_splits/ag_news_threshold_v2.json'
OUT=ROOT/'reports/defense_v1/T10/utility48_direct_reuse_candidates_20261117.jsonl'

# Each item selects an existing verbatim question and cites a contiguous source span.
SELECTION=[
 ('00000220','0013','A tiger attacked a 14-year-old boy and a handler at a Florida county fair.','A 14-year old boy and a tiger handler are recovering after being attacked'),
 ('00000224','0017','Merck recalled Vioxx.','recalled its widely sold Vioxx painkiller'),
 ('00000367','0005','The new file system reduced available memory.','a new file system used for the handheld actually offers less memory'),
 ('00000388','0013','The officials clashed with advisers to Porter J. Goss.','after clashes with advisers to Porter J. Goss'),
 ('00000639','0017','The inquiry blamed Continental Airlines.','placed much of the blame on the American carrier, Continental Airlines'),
 ('00000843','0012','Oklahoma defeated Baylor 35-0.','beating Baylor 35-0'),
 ('00000988','0013','PayPal continued experiencing intermittent service outages.','intermittent service outages at the online payment service PayPal continued'),
 ('00000992','0017','The weapons-for-cash program would be expanded nationwide.','weapons-for-cash program in Baghdad would be expanded nationwide'),
]

def main():
    train=set(json.loads(SPLIT.read_text(encoding='utf8'))['partitions']['train']['doc_ids'])
    bank={x['query_id']:x for x in (json.loads(s) for s in BANK.read_text(encoding='utf8').splitlines())}
    docs={x['doc_id']:x for x in (json.loads(s) for s in DOCS.read_text(encoding='utf8').splitlines())}
    out=[]
    for tail,n,answer,quote in SELECTION:
        doc='ag_news_teacher_'+tail
        qid=f'ag_news:{doc}:benign:generated:{n}'
        item=bank[qid]
        assert doc in train and item['traffic_type']=='benign' and quote in docs[doc]['text']
        out.append({'source_query_id':qid,'query':item['query_text'],'doc_id':doc,
                    'candidate_reference_answer':answer,'evidence_quote':quote,
                    'source_text_sha256':sha256(docs[doc]['text'].encode('utf8')).hexdigest(),
                    'reviewer_kind':'llm_agent','human_reviewed':False,'status':'candidate_not_frozen',
                    'caveat':'Source-bound answer; review wording and scoring against full context before selection.'})
    OUT.write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in out),encoding='utf8')
    print('Evidence anchored reusable v2 candidates:',len(out),'output sha256:',sha256(OUT.read_bytes()).hexdigest())

if __name__=='__main__':main()
