"""Construct an evidence-anchored, unfrozen 12-item utility annotation pilot."""
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path.cwd()
DOCS = ROOT / 'data/vector_stores/20260717-ag-news-four-medium/ag_news/documents.jsonl'
OUT = ROOT / 'reports/defense_v1/T10/utility48_annotation_pilot_20261117.jsonl'

# Facts and quotations are manually checked against the indexed source text.
ITEMS = [
 ('standard', '00000149', 'What capability is NASA planning to add to planetary rovers?', 'artificial intelligence', [('00000149','artificial intelligence (AI)')]),
 ('standard', '00000220', 'How old was the boy attacked at the Florida fair?', '14 years old', [('00000220','A 14-year old boy')]),
 ('standard', '00000532', 'How many executives did Ace dismiss?', 'two', [('00000532','dismissed two executives')]),
 ('alternative', '00000363', 'Which type of spacecraft is associated with the space station replacement crew?', 'Soyuz', [('00000363','Soyuz spacecraft'),('00000794','Soyuz spacecraft')]),
 ('alternative', '00000224', 'Which drug was involved in the Merck recall?', 'Vioxx', [('00000224','Vioxx painkiller'),('00000909','Vioxx recall')]),
 ('alternative', '00000224', 'Which company was associated with Vioxx withdrawal?', 'Merck', [('00000224','Merck'),('00000589','withdrawal of its Vioxx pain reliever')]),
 ('dependent', '00000367', 'What size expansion card did PalmOne plan to offer Treo 650 owners?', '128MB', [('00000367','128MB expansion card')]),
 ('dependent', '00000843', 'How many yards did Adrian Peterson run against Baylor?', '240 yards', [('00000843','ran for 240 yards')]),
 ('dependent', '00000997', 'How many jobs did P&O plan to cut at its ferry unit?', '1,200', [('00000997','cut 1,200 jobs')]),
 ('insufficient', '00000149', 'Which planet will NASA send these AI-equipped rovers to?', None, []),
 ('insufficient', '00000532', 'What are the names of the two dismissed Ace executives?', None, []),
 ('insufficient', '00000988', 'At what exact time did the PayPal outages end?', None, []),
]

# Additional candidates are maintained separately from the pilot until semantic review.
MORE = [
 ('standard','00000363','From which country is the Baikonur cosmodrome?', 'Kazakhstan',[('00000363','Baikonur cosmodrome in Kazakhstan')]),
 ('standard','00000388','Which intelligence agency had two officials resign?', 'CIA',[('00000388',"C.I.A.'s clandestine service")]),
 ('standard','00000479','How many people were killed in the fresh Philippine flooding, at minimum?', '26',[('00000479','killed at least 26 people')]),
 ('standard','00000544','How many advertiser accounts did Google expect to add by 2008?', '372,050',[('00000544','372,050\\advertiser accounts by 2008')]),
 ('standard','00000639','Which airline was blamed by the French Concorde inquiry?', 'Continental Airlines',[('00000639','Continental Airlines')]),
 ('standard','00000843','Which team did Oklahoma defeat 35-0?', 'Baylor',[('00000843','beating Baylor 35-0')]),
 ('standard','00000979','Which sector witnessed an upturn in the report?', 'US services sector',[('00000979','US services sector witnessed a continued upturn')]),
 ('standard','00000988','Which payment service had outages?', 'PayPal',[('00000988','payment service PayPal')]),
 ('standard','00000997','How many jobs did the ferry unit plan to cut?', '1,200',[('00000997','cut 1,200 jobs')]),
 ('dependent','00000050','What price might Symantec pay for Veritas?', '$13 billion',[('00000050','may pay \\$13 billion')]),
 ('dependent','00000149','What can the planned AI let the rovers do during a mission?', 'make basic decisions',[('00000149','making basic decisions during a mission')]),
 ('dependent','00000220','How old was the injured boy, and how heavy was the tiger at the Florida fair?', '14 years old and 350 pounds',[('00000220','A 14-year old boy'),('00000220','350-pound Siberian tiger')]),
 ('dependent','00000224','How much did Merck stock fall after the recall?', '27 percent',[('00000224','stock sunk 27  percent')]),
 ('dependent','00000363','Who were the two space station crew members named in the report?', 'Gennady Padalka and Michael Fincke',[('00000363','Gennady Padalka and NASA astronaut Michael Fincke')]),
 ('dependent','00000433','How many Japanese yen was the Australian dollar worth?', '81.29 yen',[('00000433','81.29 Japanese yen')]),
 ('dependent','00000544','How many advertiser accounts did Google expect to add, and by what year?', '372,050 by 2008',[('00000544','372,050\\advertiser accounts by 2008')]),
 ('dependent','00000979','For how many consecutive months had the US services sector grown?', '19 months',[('00000979','nineteenth consecutive month')]),
 ('dependent','00000988','Which service had outages and for how many consecutive days?', 'PayPal, five days',[('00000988','payment service PayPal'),('00000988','fifth consecutive day')]),
 ('insufficient','00000050','On what date would the Symantec-Veritas acquisition be finalized?',None,[]),
 ('insufficient','00000220','What was the name of the injured tiger handler?',None,[]),
 ('insufficient','00000224','What was the exact closing price of Merck stock after the recall?',None,[]),
 ('insufficient','00000363','What is the name of the replacement crew commander?',None,[]),
 ('insufficient','00000367','On what date will PalmOne mail the expansion cards?',None,[]),
 ('insufficient','00000479','Which specific village had the most flooding deaths?',None,[]),
 ('insufficient','00000544','How much revenue did Google earn from the new advertisers?',None,[]),
 ('insufficient','00000639','What was the amount of damages awarded by the French court?',None,[]),
 ('insufficient','00000843','What was the attendance at the Oklahoma-Baylor game?',None,[]),
 ('alternative','00000313','Which football club is Mateja Kezman associated with?', 'Chelsea',[('00000313','Kezman believes he can go on a goalscoring spree after finally opening his account for Chelsea'),('00000820','Mateja Kezman today hailed Chelsea')]),
 ('alternative','00000992','What is the name of the Iraqi prime minister in the reports?', 'Ayad Allawi',[('00000992','Prime Minister Ayad Allawi'),('00000422','Prime Minister Ayad Allawi')]),
 ('alternative','00000665','Which US president is mentioned in accounts of the Pacific Rim summit protests?', 'Bush',[('00000665','President Bush'),('00000801','President Bush')]),
 ('alternative','00000665','Who clashed with protesters around the Pacific Rim summit?', 'police',[('00000665','Riot police'),('00000801','police battled')]),
 ('alternative','00000363','What destination was mentioned for the Soyuz replacement crew?', 'space station',[('00000363','Space Station'),('00000794','space station')]),
 ('alternative','00000224','Which drug is mentioned with Merck in the reports?', 'Vioxx',[('00000224','Vioxx painkiller'),('00000589','Vioxx pain reliever')]),
 ('alternative','00000313','What is the first name of Chelsea player Kezman?', 'Mateja',[('00000313','Mateja Kezman'),('00000820','Mateja Kezman')]),
 ('alternative','00000992','What position did Ayad Allawi hold in Iraq?', 'prime minister',[('00000992','Prime Minister Ayad Allawi'),('00000422','Prime Minister Ayad Allawi')]),
 ('alternative','00000665','What regional group was holding the summit where protests occurred?', 'Pacific Rim',[('00000665','Pacific Rim leaders'),('00000801','Pacific Rim nations')]),
]

MULTI_FACTS = {
    'How old was the injured boy, and how heavy was the tiger at the Florida fair?': [
        ('14 years old', [('00000220','A 14-year old boy')]),
        ('350 pounds', [('00000220','350-pound Siberian tiger')])],
    'How many advertiser accounts did Google expect to add, and by what year?': [
        ('372,050 advertiser accounts', [('00000544','372,050\\advertiser accounts by 2008')]),
        ('2008', [('00000544','advertiser accounts by 2008')])],
    'Which service had outages and for how many consecutive days?': [
        ('PayPal', [('00000988','payment service PayPal')]),
        ('five days', [('00000988','fifth consecutive day')])],
    'Who were the two space station crew members named in the report?': [
        ('Gennady Padalka', [('00000363','Gennady Padalka')]),
        ('Michael Fincke', [('00000363','Michael Fincke')])],
}

def main():
    docs = {row['doc_id']: row['text'] for line in DOCS.read_text(encoding='utf-8').splitlines()
            if (row := json.loads(line))}
    rows = []
    expanded = '--expanded' in sys.argv
    output = OUT.with_name('utility48_annotation_draft_20261117.jsonl') if expanded else OUT
    items = ITEMS + MORE if expanded else ITEMS
    for number, (group, target, query, answer, evidence) in enumerate(items, 1):
        target_id = 'ag_news_teacher_' + target
        sources = []
        for doc, quote in evidence:
            doc_id = 'ag_news_teacher_' + doc
            assert quote in docs[doc_id], (doc_id, quote)
            sources.append({'doc_id': doc_id, 'quote': quote})
        # The finite allowed scope makes absence checks for insufficient items meaningful.
        allowed = sorted({target_id} | {item['doc_id'] for item in sources})
        fact_items = MULTI_FACTS.get(query, [(answer, evidence)]) if answer is not None else []
        facts = []
        for fact, fact_evidence in fact_items:
            supporting = []
            for doc, quote in fact_evidence:
                doc_id = 'ag_news_teacher_' + doc
                assert quote in docs[doc_id], (doc_id, quote)
                supporting.append({'doc_id':doc_id, 'quote':quote})
            facts.append({'fact':fact, 'supporting_quotes':supporting})
        rows.append({'request_id': f'utility48_pilot_{number:02d}', 'group': group, 'query': query,
                     'target_doc_id': target_id, 'allowed_doc_ids': allowed,
                     'answerable': answer is not None, 'reference_answer':answer, 'required_facts': facts,
                     'missing_information': query if answer is None else None,
                     'source_text_sha256': {doc: sha256(docs[doc].encode('utf-8')).hexdigest() for doc in allowed},
                     'reviewer_kind': 'llm_agent', 'human_reviewed': False, 'status': 'draft_not_frozen',
                     'source_note': 'New question drafted from indexed source; supplementary sources may be outside query split.'})
    assert len(rows) == (48 if expanded else 12) and len({x['query'] for x in rows}) == len(rows)
    output.write_text(''.join(json.dumps(x, ensure_ascii=False) + '\n' for x in rows), encoding='utf-8')
    print('draft rows:', len(rows), 'sha256:', sha256(output.read_bytes()).hexdigest())

if __name__ == '__main__':
    main()
