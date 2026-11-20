"""Freeze a new version using evidence-reviewed original questions where possible."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path

ROOT=Path.cwd()
BASE=ROOT/'data/defense_datasets/utility48_v2_train_20261117_01'
PRIOR=ROOT/'data/defense_datasets/next_goal_v2_train_20261117_01'
CANDIDATES=ROOT/'reports/defense_v1/T10/utility48_direct_reuse_candidates_20261117.jsonl'
OUT=ROOT/'data/defense_datasets/utility48_reuse_v2_train_20261117_01'

def read(path):
    return [json.loads(line) for line in path.read_text(encoding='utf8').splitlines() if line.strip()]

def digest(path):
    return sha256(path.read_bytes()).hexdigest()

def main():
    meta=json.loads((BASE/'manifest.json').read_text(encoding='utf8'))
    for name,expected in meta['output_sha256'].items(): assert digest(BASE/name)==expected
    old_requests={x['request_id']:x for x in read(PRIOR/'requests.jsonl')}
    candidates={x['doc_id'][-8:]:x for x in read(CANDIDATES)}
    rubric=read(BASE/'normal_rubric.jsonl')
    bank_map={2:'00000220',25:'00000224',7:'00000367',14:'00000388',17:'00000639',
              18:'00000843',20:'00000988',9:'00000992'}
    prior_map={1:'ng_normal_03',5:'ng_normal_07',22:'ng_normal_01',23:'ng_normal_04'}
    bank_path=ROOT/'data/query_banks/ag_news_queries_v2/ag_news/queries.jsonl'
    bank={x['query_id']:x for x in read(bank_path)}
    bank_11='ag_news:ag_news_teacher_00000532:benign:generated:0005'
    assert bank[bank_11]['traffic_type']=='benign'
    requests=[]; labels=[]; lineage=[]; updated=[]
    for case in rubric:
        item=deepcopy(case)
        number=int(item['request_id'].split('_')[2])
        rid=f'utility48_reuse_{number:02d}'
        source={'kind':'new_agent_authored','source_doc_id':item['target_doc_id']}
        if number in bank_map:
            c=candidates[bank_map[number]]
            item.update(query=c['query'],target_doc_id=c['doc_id'],allowed_doc_ids=[c['doc_id']],
                        reference_answer=c['candidate_reference_answer'],answerable=True,
                        required_facts=[{'fact':c['candidate_reference_answer'],
                                         'supporting_quotes':[{'doc_id':c['doc_id'],'quote':c['evidence_quote']}]}],
                        source_text_sha256={c['doc_id']:c['source_text_sha256']})
            source={'kind':'verbatim_v2_train','source_query_id':c['source_query_id'],'source_doc_id':c['doc_id']}
        elif number in prior_map:
            old=old_requests[prior_map[number]]
            item['query']=old['query']
            source={'kind':'verbatim_previous_development','source_request_id':prior_map[number],
                    'source_doc_id':item['target_doc_id']}
        elif number == 11:
            item['query']=bank[bank_11]['query_text']
            source={'kind':'verbatim_v2_train','source_query_id':bank_11,'source_doc_id':item['target_doc_id']}
        item.update(request_id=rid,status='frozen_agent_reviewed',lineage=source)
        requests.append({'request_id':rid,'session_id':rid,'query':item['query'],
                         'allowed_doc_ids':item['allowed_doc_ids']})
        labels.append({'request_id':rid,'doc_id':item['target_doc_id'],'attack_type':'benign','traffic_type':'benign',
                       'answerable':item['answerable'],'reference_answer':item.get('reference_answer'),
                       'gold_evidence_ids':[item['target_doc_id']] if item['answerable'] else [],
                       'human_reviewed':False,'formal_effect_eligible':False})
        lineage.append(dict(source,request_id=rid,turn=1))
        updated.append(item)
    assert len(requests)==48 and len({x['query'] for x in requests})==48
    from collections import Counter
    assert Counter(x['group'] for x in updated)=={'standard':12,'alternative':12,'dependent':12,'insufficient':12}
    OUT.mkdir(exist_ok=False)
    for name,rows in [('requests',requests),('labels',labels),('lineage',lineage),('normal_rubric',updated)]:
        (OUT/(name+'.jsonl')).write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in rows),encoding='utf8')
    (OUT/'scoring_protocol_zh.md').write_bytes((BASE/'scoring_protocol_zh.md').read_bytes())
    config=deepcopy(json.loads((BASE/'experiment_spec.json').read_text(encoding='utf8')))
    config.update(experiment_id='T10D-utility48-reuse',requests_path=str(OUT/'requests.jsonl'),labels_path=str(OUT/'labels.jsonl'))
    for name in ('lineage','normal_rubric'):config['identity_files'][name]=str(OUT/(name+'.jsonl'))
    config['identity_files']['cohort_manifest']=str(OUT/'manifest.json')
    (OUT/'experiment_spec.json').write_text(json.dumps(config,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    manifest={'version_id':OUT.name,'partition':'train','analysis_role':'engineering_only',
              'request_count':48,'expected_events':96,'methods':config['methods'],'human_gold_complete':False,
              'formal_effect_eligible':False,'lineage_counts':dict(Counter(x['kind'] for x in lineage)),
              'input_sha256':{str(p):digest(p) for p in (BASE/'manifest.json',CANDIDATES,bank_path,
                                                         PRIOR/'requests.jsonl',Path(__file__).resolve())},
              'output_sha256':{p.name:digest(p) for p in OUT.iterdir()},
              'limits':['Agent annotations, simulated per-question allowlists, repeated event sources.',
                        'Supplementary index sources for alternative cases outside query split.',
                        'New agent-authored questions retained where candidate coverage remains incomplete.']}
    (OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print('Frozen',len(requests),'questions, lineage',manifest['lineage_counts'])

if __name__=='__main__':main()
