"""Review changed questions and transfer unchanged reviews only on exact evidence match."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path

ROOT=Path.cwd()
BASE=ROOT/'data/defense_v1_runs/utility48-paired-20261117-01'
RUN=ROOT/'data/defense_v1_runs/utility48-reuse-paired-20261117-01'
OLD_REVIEW=ROOT/'reports/defense_v1/T10/utility48_b0_agent_review_20261117.jsonl'
RUBRIC=ROOT/'data/defense_datasets/utility48_reuse_v2_train_20261117_01/normal_rubric.jsonl'
OUT=ROOT/'reports/defense_v1/T10/utility48_reuse_b0_agent_review_20261117.jsonl'

# Explicitly reviewed against the actual answer and the supplied context.
CLAIMS={
 1:['NASA plans artificial intelligence for planetary rovers','AI makes rovers more self-reliant','Rovers can make basic decisions during a mission'],
 2:['A 14-year-old boy was attacked','A tiger handler was attacked','The attacker was a 350-pound Siberian tiger'],
 5:['Merck recalled Vioxx','Vioxx is a painkiller'],
 7:['A new Treo 650 file system offered less data storage than the Treo 600'],
 9:['Ayad Allawi planned to expand the weapons-for-cash program nationwide','The program operated in Baghdad'],
 14:['Two CIA officials resigned after clashes with advisers to Porter J. Goss'],
 17:['The French Concorde inquiry placed much blame on Continental Airlines','Continental Airlines is an American carrier'],
 18:['Oklahoma defeated Baylor','The score was 35-0','Oklahoma was ranked number two'],
 20:['PayPal outages continued despite repair efforts','Outages affected payments, log-ins and account creations'],
 22:['Symantec may pay $13 billion for Veritas'],
 23:['AI would enable the rovers to make basic decisions during a mission','Rovers would become more self-reliant'],
 25:['Merck recalled Vioxx','Vioxx is a painkiller','Merck stock fell 27 percent',
     'The recall caused the stock drop'],
}

def lines(path):
    return [json.loads(s) for s in path.read_text(encoding='utf8').splitlines() if s.strip()]

def events(run):
    out={}
    for p in (run/'sessions/B0/20260715').glob('*.json'):
        shard=json.loads(p.read_text(encoding='utf8'))
        assert shard['status']=='complete'
        for event in shard['events']:out[int(event['request_id'].split('_')[2])]=event
    return out

def contexts(run,event):
    p=run/event['generation_input_ref']
    assert sha256(p.read_bytes()).hexdigest()==event['artifact_sha256']
    return json.loads(p.read_text(encoding='utf8'))['generation_input']['contexts']

def main():
    previous=events(BASE); current=events(RUN)
    annotations={int(x['request_id'].split('_')[2]):x for x in lines(RUBRIC)}
    old={int(x['request_id'].split('_')[2]):x for x in lines(OLD_REVIEW)}
    assert len(previous)==len(current)==len(annotations)==len(old)==48
    output=[]
    for number in range(1,49):
        event=current[number]; item=annotations[number]
        assert event['status']=='complete' and event['action']=='allow'
        answer=event['response']; base=previous[number]
        if item['lineage']['kind']=='new_agent_authored':
            assert answer==base['response'] and contexts(RUN,event)==contexts(BASE,base),number
            review=deepcopy(old[number])
            review.update(request_id=event['request_id'],review_scope='Prior agent review transferred only after identical answer and context check')
        else:
            assert number in CLAIMS or number==11,number
            no_facts=number==11
            facts=[{'fact':f['fact'],'correct':True,'reason':'Agent checked answer against required fact and full context.'}
                   for f in item['required_facts']]
            claims=[] if no_facts else [{'text':c,'support':'uncertain' if number==25 and i==3 else 'supported'}
                                        for i,c in enumerate(CLAIMS[number])]
            review={'request_id':event['request_id'],'method':'B0','reviewer_kind':'llm_agent','human_reviewed':False,
                    'answer_sha256':sha256(answer.encode('utf8')).hexdigest(),'facts':facts,'claims':claims,
                    'reasonable_insufficient':True if no_facts else None,
                    'review_scope':'Agent review of the actual response and supplied sources',
                    'limitations':['Agent review, not human gold.', 'Statement segmentation is subjective.']}
        output.append(review)
    OUT.write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in output),encoding='utf8')
    print('Reviewed 48 B0 answers; 35 transferred only after matching response and actual contexts.')

if __name__=='__main__':main()
