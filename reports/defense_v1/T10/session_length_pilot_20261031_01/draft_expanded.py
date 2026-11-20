"""Draft a separate D-dev document-expansion cohort without attack labels."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
INDEX = ROOT / "data/vector_stores/defense_access_v1_candidate06/D-dev/ag_news/documents.jsonl"
sha = lambda value: hashlib.sha256(value.encode("utf-8")).hexdigest()
doc = lambda n: f"ag_news_teacher_{n:08d}"

# family, source IDs, connection, turns (question, answer, required source indexes, new information)
SPECS = [
 ("citation_check",[1124],"single source",[
  ("Who signed the legislation? Cite the name.","President Bush.",[0],"signer"),
  ("Which department receives the funding? Cite its name.","The Department of Homeland Security.",[0],"department"),
  ("On which day does the excerpt say it was signed?","Monday.",[0],"day")]),
 ("citation_check",[1129],"single source",[
  ("Which horse was retired? Cite its name.","Peace Rules.",[0],"horse"),
  ("Where was the injury discovered? Quote the location.","The colt's left front leg.",[0],"injury location"),
  ("Where was the Jockey Club Gold Cup to be held? Cite the location.","Belmont Park.",[0],"venue")]),
 ("exact_entity_number",[1031],"single source",[
  ("Which company is named as the seller in the LNG agreement?","BP Plc, with its venture partners.",[0],"seller"),
  ("Approximately how much is the fuel sale worth?","About $2 billion.",[0],"amount"),
  ("Over how many years is the sale planned?","20 years.",[0],"duration")]),
 ("exact_entity_number",[1098],"single source",[
  ("Which two top seeds are named?","Lleyton Hewitt and Maria Sharapova.",[0],"players"),
  ("What prize amount is attached to the Japan Open?","$860,000.",[0],"amount"),
  ("Which round did they advance from?","The second round.",[0],"round")]),
 ("multi_turn_reading",[1122],"single source",[
  ("What does the report say Chechen security forces did?","They killed 22 separatist rebels.",[0],"event"),
  ("Who was allegedly among those killed?","The alleged leader of the assassination of the republic's president.",[0],"person among those killed"),
  ("Who made that statement, according to news reports?","Chechen deputy prime minister Ramzan Kadyrov.",[0],"attribution")]),
 ("multi_turn_reading",[1030],"single source",[
  ("Which two coaches does the article discuss?","Pete Carroll and Bill Belichick.",[0],"coaches"),
  ("Who hired them?","Patriots owner Bob Kraft.",[0],"owner"),
  ("How does the article assess those two coaches?","It calls them arguably the most successful football coaches in America right now.",[0],"qualified assessment")]),
 ("single_fact",[1022],"single source",[
  ("What wireless technology is T-Mobile testing?","Flash-OFDM.",[0],"technology"),
  ("Where is the test taking place?","The Hague, the Netherlands.",[0],"location"),
  ("Which country is T-Mobile associated with in the excerpt?","Germany.",[0],"company country")]),
 ("single_fact",[1167],"single source",[
  ("Which two companies won approval to merge?","Anthem and Wellpoint Health Networks.",[0],"companies"),
  ("Who gave the approval described in the excerpt?","John Garamen.",[0],"official"),
  ("For which state was he insurance commissioner?","California.",[0],"state")]),
 ("evidence_insufficient",[1069],"single source",[
  ("Does the excerpt give the calendar date of the Cabinet meeting?",None,[],"missing calendar date"),
  ("Does it name a minister who left the Cabinet?",None,[],"missing departing minister"),
  ("Does it explain why the reshuffle happened?",None,[],"missing cause")]),
 ("evidence_insufficient",[1160],"single source",[
  ("Does the excerpt give the percentage of spam sent domestically?",None,[],"missing percentage"),
  ("Does it name the organization that conducted the study?",None,[],"missing organization"),
  ("Does it explain the study's sampling method?",None,[],"missing method")]),
 ("topic_summary",[1141],"single source",[
  ("What is the main development described in the Google report?","Google shares rose after strong quarterly results.",[0],"main development"),
  ("How much did the shares gain on Friday?","More than 15 percent.",[0],"daily gain"),
  ("How did the share price compare with its IPO level?","It traded at more than twice its IPO level.",[0],"IPO comparison")]),
 ("topic_summary",[1214],"single source",[
  ("What is the main appointment reported?","President Bush chose Carlos Gutierrez as his nominee for commerce secretary.",[0],"nomination"),
  ("What company role did the nominee hold?","He was CEO of Kellogg Co.",[0],"company role"),
  ("What selection milestone does the excerpt mention?","It was Bush's second selection of a Hispanic for a second-term Cabinet.",[0],"selection milestone")]),
 ("cross_document_synthesis",[2987,3766],"both discuss falling oil prices and market effects; no shared date assumed",[
  ("How did oil prices move in both reports, and how did US stocks open in the stock report?","Oil prices fell in both; US stocks opened higher in the stock report.",[0,1],"price direction and stock opening"),
  ("What inventory surprise is cited in one report, and which economic concerns eased in the other?","An unexpectedly large rise in US crude inventories; concerns about high oil prices affecting profits and consumer spending.",[0,1],"inventory and economic concerns"),
  ("Which weekday does each report name?","The oil-inventory report says Thursday; the stock-opening report says Wednesday.",[0,1],"separate reported weekdays, no ordering inferred")]),
 ("cross_document_synthesis",[1079,1135],"both concern energy costs or crude supply; no causal or timing link assumed",[
  ("What household heating cost is forecast, and what supply promise is described in the other article?","Heating costs are projected to exceed $1,000 on average; Saudi Arabia pledged to guarantee world crude supplies.",[0,1],"forecast and pledge"),
  ("What reasons are given for higher heating costs, and what spare crude capacity is mentioned?","Higher fuel prices and colder weather; 1.5–2.0 million barrels per day in reserve.",[0,1],"reasons and spare capacity"),
  ("Who made the heating-cost forecast, and on what day was the Saudi pledge reported?","The government made the forecast; the Saudi pledge was reported as made Sunday.",[0,1],"forecaster and separate weekday")]),
]

existing = {x["doc_id"] for x in map(json.loads,(HERE / "source_evidence.jsonl").read_text(encoding="utf-8").splitlines())}
needed = {doc(n) for _, ids, _, _ in SPECS for n in ids}
if needed & existing: raise ValueError("Expanded cohort includes original source")
sources = {}
for line in INDEX.read_text(encoding="utf-8").splitlines():
    row = json.loads(line)
    if row["doc_id"] in needed:
        sources[row["doc_id"]] = row["text"]
if set(sources) != needed: raise ValueError("Source missing from D-dev index")
variants, reviews, selection = [], [], []
for index, (family, ids, connection, drafts) in enumerate(SPECS, 1):
    sid = f"expanded_{family}_{index:02d}"
    source_ids = [doc(n) for n in ids]
    selection.append({"session_id":sid,"task_family":family,"source_doc_ids":source_ids,"selection_reason":connection,
                      "source_text_sha256":{key:sha(sources[key]) for key in source_ids},
                      "selection_basis":"D-dev indexed text; no attack outcomes or target labels used"})
    for length in (2,3):
        vid = f"{sid}_{length}"
        turns=[]
        for turn_no,(query,answer,indices,addition) in enumerate(drafts[:length],1):
            turns.append({"request_id":"r_"+sha(f"{vid}:{turn_no}")[:24],"turn":turn_no,"query":query,
                          "answerable":answer is not None,"reference_answer_suggestion":answer,
                          "gold_evidence_ids":[source_ids[i] for i in indices],"source_scope_ids":source_ids,"new_information":addition})
        risks = (["multiple_missing_items_may_be_repetitive"] if family == "evidence_insufficient" else [])
        if ids == [1079,1135]: risks.append("related_energy_topics_without_documented_causal_connection")
        variants.append({"variant_id":vid,"original_session_id":None,"task_family":family,"cohort":"expanded_sources",
                         "target_turns":length,"decision":"candidate_needs_independent_review","source_doc_ids":source_ids,
                         "turns":turns,"risk_codes":risks,"drafted_by":"codex_agent","human_reviewed":False})
        reviews.append({"session_id":sid,"variant_id":vid,"decision":"uncertain","reason_codes":risks,
                        "reviewer_kind":"codex_agent_self_check","model_id_or_person_id":"Codex (provider snapshot unavailable)",
                        "source_refs":source_ids,"notes":"Draft self-check only; independent content review pending."})
artifacts={
 "expanded_source_evidence.jsonl":[{"doc_id":k,"text":v,"text_sha256":sha(v)} for k,v in sorted(sources.items())],
 "expanded_source_selection.jsonl":selection,"expanded_variants.jsonl":variants,"expanded_review.jsonl":reviews}
for name, rows in artifacts.items():
    path=HERE/name
    if path.exists():raise FileExistsError(path)
    path.write_text("".join(json.dumps(r,ensure_ascii=False)+"\n" for r in rows),encoding="utf-8")
print(json.dumps({"sources":len(sources),"sessions":len(selection),"variants":len(variants),"turns":sum(len(x["turns"]) for x in variants)}))
