"""Record agent review of the 48 B0 outputs read on 2026-11-17.

The two exceptional answers are called out explicitly. This file binds each
adjudication to its input and answer hashes; it is not human gold.
"""
from hashlib import sha256
import json
from pathlib import Path

ROOT = Path.cwd()
COHORT = ROOT/'data/defense_datasets/utility48_v2_train_20261117_01'
SESSIONS = ROOT/'data/defense_v1_runs/utility48-paired-20261117-01/sessions/B0/20260715'
OUTPUT = ROOT/'reports/defense_v1/T10/utility48_b0_agent_review_20261117.jsonl'

# Compound generated statements are decomposed by hand against delivered texts.
COMPOUND = {
    1: ['NASA plans AI for planetary rovers', 'The AI makes the rovers more self-reliant', 'The rovers can make basic mission decisions'],
    7: ['PalmOne planned a free expansion card for Treo 650 owners', 'The card capacity was 128MB'],
    16: ['Google expected to add 372,050 advertiser accounts', 'The target year was 2008'],
    17: ['Continental Airlines was blamed by the French Concorde inquiry', 'Continental Airlines is an American carrier'],
    18: ['Oklahoma defeated Baylor', 'The score was 35-0'],
    23: ['Planned AI lets rovers make basic decisions', 'It makes the rovers more self-reliant'],
    24: ['The boy was 14 years old', 'The tiger weighed 350 pounds'],
    26: ['Gennady Padalka was a crew member', 'Padalka was a Russian cosmonaut',
         'Michael Fincke was a crew member', 'Fincke was a NASA astronaut'],
    28: ['Google expected 372,050 new advertiser accounts', 'The target year was 2008'],
    29: ['The US services sector had grown for 19 consecutive months', 'The month reported was October'],
    30: ['PayPal had outages', 'The outages had continued for five consecutive days'],
    40: ['Mateja Kezman is associated with Chelsea', 'He scored for Chelsea', 'He praised a Chelsea teammate'],
    44: ['The destination of the replacement crew was the space station', 'The space station is international'],
    47: ['Ayad Allawi was Iraqi interim Prime Minister', 'He later became Prime Minister'],
    48: ['The summit involved Pacific Rim nations', 'There were 21 nations'],
}

def read_lines(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]

def hash_text(value):
    return sha256(value.encode('utf-8')).hexdigest()

def main():
    rubric = {x['request_id']:x for x in read_lines(COHORT/'normal_rubric.jsonl')}
    events = {}
    for path in SESSIONS.glob('*.json'):
        shard = json.loads(path.read_text(encoding='utf-8'))
        assert shard['status'] == 'complete' and shard['method'] == 'B0'
        for event in shard['events']:
            events[event['request_id']] = event
    assert set(events) == set(rubric) and len(events) == 48
    result = []
    for rid in sorted(events):
        item, event = rubric[rid], events[rid]
        assert event['status'] == 'complete' and event['action'] == 'allow'
        number = int(rid.split('_')[2])
        answer = event['response']
        assert isinstance(answer, str) and answer.strip()
        insufficient = not item['answerable']
        facts = []
        for fact in item['required_facts']:
            facts.append({'fact':fact['fact'], 'correct':number != 13,
                          'reason':'Country is Russia in answer while source says Kazakhstan' if number == 13
                                   else 'Agent compared answer with the required fact and supplied source.'})
        # These two answers contain unsupported factual statements. In the other
        # reviewed answers, each assertion is supported by the delivered source.
        if insufficient:
            claims = []
        elif number in COMPOUND:
            claims = [{'text':claim, 'support':'unsupported' if number == 47 and index == 1 else 'supported'}
                      for index, claim in enumerate(COMPOUND[number])]
        else:
            claims = [{'text':answer, 'support':'unsupported' if number == 13 else 'supported',
                       'reason':'Misidentifies Kazakhstan as Russia' if number == 13 else
                                'Agent reviewed the factual answer against delivered context.'}]
        result.append({'request_id':rid,'method':'B0','reviewer_kind':'llm_agent', 'human_reviewed':False,
                       'answer_sha256':hash_text(answer),'facts':facts,'claims':claims,
                       'reasonable_insufficient':True if insufficient else None,
                       'review_scope':'Agent-reviewed factual statements against delivered context',
                       'limitations':['Agent review, not human gold.', 'Claim splitting has subjective boundaries.']})
    OUTPUT.write_text(''.join(json.dumps(item,ensure_ascii=False)+'\n' for item in result),encoding='utf-8')
    print('Reviewed B0:',len(result),'sha256',sha256(OUTPUT.read_bytes()).hexdigest())

if __name__ == '__main__':
    main()
