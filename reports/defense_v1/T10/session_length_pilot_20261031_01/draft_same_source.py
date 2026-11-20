"""Draft D-dev same-source session variants; source data remain read-only."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
inventory = [json.loads(line) for line in (HERE / "session_inventory.jsonl").read_text(encoding="utf-8").splitlines()]

# Each tuple is (question, suggested answer, source indexes, new information).
# Negative answers keep empty gold evidence and preserve the material scope separately.
DRAFTS = {
"s_173b030fcf5fd3dcd095227b": [
 ("Which company is named as the buyer? Quote the buyer phrase.", "An affiliate of Colony Capital.", [0], "buyer"),
 ("How many properties does that affiliate plan to buy? Quote the number phrase.", "Four properties.", [0], "number"),
 ("Which companies are identified as the sellers? Cite their names.", "Caesars Entertainment Inc. and Harrah's Entertainment Inc.", [0], "sellers")],
"s_437a104284d832b1cd5f0849": [
 ("Who is quoted in the report? Cite the name.", "Jean Todt.", [0], "speaker"),
 ("How does he describe the circuit? Quote the qualifier as well.", 'He says it is "probably the most interesting on the current Formula 1 calendar."', [0], "qualified opinion"),
 ("Which Grand Prix and circuit are named in the heading?", "The Belgian Grand Prix and Spa-Francorchamps.", [0], "heading names")],
"s_04986002cdaa941b4e001f09": [
 ("Across the two reports about Kenneth Bigley, how does his situation differ?", "One account describes Bigley pleading for help; the other reports his murder.", [0,1], "situation in each report"),
 ("What did he ask Blair to do, and how did Blair describe his killers?", "Bigley appealed to Blair to intervene; Blair called his killers barbaric.", [0,1], "appeal and condemnation"),
 ("What was the response to the prisoner demand, and how did most victims' relatives assess Blair's handling?", "Authorities would not free the female Iraqi prisoners; most victims' relatives praised Blair's handling.", [0,1], "prisoner demand and relatives")],
"s_3e92f4335d69f54d3c656df2": [
 ("Which report mentions crude touching $53, and which reports an oil-price drop?", "The household-cost report mentions $53; the stock-market report describes a sharp drop.", [0,1], "price in each report"),
 ("What winter cost does the first report anticipate, and what concerns outweighed cheaper oil in the other?", "Higher household heating bills; concerns about the economy and potential inflation.", [0,1], "household cost and market concerns"),
 ("What summer cost does the household report mention, and what happened to the major indexes over the week in the other?", "Gasoline costs rose for US drivers; all three major indexes were lower for the week.", [0,1], "summer gasoline and weekly indexes")],
"s_08e8938c350e35aa9a8fa6fb": [
 ("Does the excerpt give the date Kenneth Bigley was killed?", None, [], "missing date"),
 ("Does it identify the group responsible for his murder?", None, [], "missing group"),
 ("Does it say where in Iraq his body was found?", None, [], "missing location")],
"s_1709052c2c393baf1346bd1f": [
 ("Does the excerpt give Kurt Busch's qualifying lap time?", None, [], "missing lap time"),
 ("Does it specify how many points he leads the championship by?", None, [], "missing points margin"),
 ("Does it identify the team he drives for?", None, [], "missing team")],
"s_0036417c86948330e11bae92": [
 ("Which pension fund is named, and which state is it associated with?", "Calpers, California's public pension fund.", [0], "fund and state"),
 ("What other kinds of investor does the excerpt list alongside pension funds?", "Endowments and other big activist investors.", [0], "investor types"),
 ("In what exact campaigns does it discuss those investors' influence?", "Corporate governance campaigns.", [0], "campaign phrase")],
"s_399af0c268f41f6b4588a0ef": [
 ("What rover names appear in the source?", "Opportunity and Sprit, as spelled in the source.", [0], "names"),
 ("In what month was their mission originally expected to end?", "April.", [0], "month"),
 ("Which planet is identified in the heading for these rovers?", "Mars.", [0], "planet in heading")],
"s_09006cbd05dd713ca18ac43b": [
 ("What did IBM announce about a computer it developed?", "It said it had developed the world's fastest computer.", [0], "IBM announcement"),
 ("Whose machine had previously claimed that title?", "A Japanese supercomputer.", [0], "earlier holder"),
 ("Roughly how long before IBM's announcement did it claim the title?", "About two years earlier.", [0], "time interval referring to previous holder")],
"s_35f642a015443be4b6938941": [
 ("What did Lycos Europe release?", 'A free screensaver called "Make Love Not Spam".', [0], "product"),
 ("What was the screensaver intended to do to spam servers?", "Deliberately clog them.", [0], "purpose"),
 ("Which computer platforms was it available for?", "Mac and PC.", [0], "platforms referring to screensaver")],
"s_018315d1c2b3844d065f3271": [
 ("What kind of measure gives rhino populations a chance to recover?", "Anti-poaching measures.", [0], "measure"),
 ("Which country's rhino populations does the excerpt discuss?", "Tanzania's.", [0], "country"),
 ("Who is credited with the report?", "Tira Shubart.", [0], "reporter credit")],
"s_1719eb75e00dd29b35bc741b": [
 ("What did Turkey's prime minister back down over?", "A row with the EU over attempts to ban adultery in Turkey.", [0], "dispute"),
 ("Which leader is named as having backed down?", "Prime Minister Tayyip Erdogan.", [0], "leader"),
 ("On what day was Turkey's EU bid described as back on course?", "Thursday.", [0], "day")],
"s_153a5ba7fed9ffda622c892d": [
 ("What does the headline say happened to Ovitz's signing bonus?", "It says he was denied a signing bonus.", [0], "headline outcome"),
 ("What amount did he seek, and for which role?", "$50 million to become president of the Walt Disney Co.", [0], "amount and role")],
"s_1d0d4cac7b5f8389d38dd6cc": [
 ("What did the Washington Mystics achieve?", "They made the playoffs.", [0], "playoff outcome"),
 ("Whose absence made that run the subject of the league's question?", "Chamique Holdsclaw's.", [0], "absent player")],
}

assert set(DRAFTS) == {x["session_id"] for x in inventory}
outputs = []
reviews = []
for session in inventory:
    sid = session["session_id"]
    drafts = DRAFTS[sid]
    for length in (2, 3):
        variant = f"{sid}_same_{length}"
        possible = len(drafts) >= length
        turns = []
        if possible:
            for turn_no, (query, answer, indexes, addition) in enumerate(drafts[:length], 1):
                scope = session["source_doc_ids"]
                gold = [scope[i] for i in indexes]
                if answer is not None and not gold:
                    raise ValueError(variant)
                if answer is None and gold:
                    raise ValueError(variant)
                request_id = "r_" + hashlib.sha256(f"{variant}:{turn_no}".encode()).hexdigest()[:24]
                turns.append({"request_id":request_id,"turn":turn_no,"query":query,"answerable":answer is not None,
                              "reference_answer_suggestion":answer,"gold_evidence_ids":gold,
                              "source_scope_ids":scope,"new_information":addition})
        risk = []
        if sid in {"s_08e8938c350e35aa9a8fa6fb", "s_1709052c2c393baf1346bd1f"}:
            risk.append("multiple_missing_items_may_be_repetitive")
        if sid == "s_153a5ba7fed9ffda622c892d":
            risk.append("headline_body_boundary_and_truncated_sentence")
        if sid == "s_399af0c268f41f6b4588a0ef":
            risk.append("source_spelling_and_heading_dependency")
        if sid == "s_35f642a015443be4b6938941":
            risk.append("source_truncated_after_platform_information")
        decision = "candidate_needs_independent_review" if possible else "excluded_insufficient_distinct_facts"
        outputs.append({"variant_id":variant,"original_session_id":sid,"task_family":session["task_family"],
                        "cohort":"same_source","target_turns":length,"decision":decision,
                        "source_doc_ids":session["source_doc_ids"],"turns":turns,"risk_codes":risk,
                        "drafted_by":"codex_agent","human_reviewed":False})
        reviews.append({"session_id":sid,"variant_id":variant,"decision":"uncertain" if possible else "reject",
                        "reason_codes":risk if possible else ["insufficient_distinct_facts"],
                        "reviewer_kind":"codex_agent_self_check","model_id_or_person_id":"Codex (provider snapshot unavailable)",
                        "source_refs":session["source_doc_ids"],
                        "notes":"Draft self-check only; independent content review and session quality judgment pending." if possible
                        else "A third distinct turn could not be grounded without repeating the source's central facts."})
for name, rows in (("normal_variants.jsonl", outputs), ("session_review.jsonl", reviews)):
    path = HERE / name
    if path.exists(): raise FileExistsError(path)
    path.write_text("".join(json.dumps(row,ensure_ascii=False)+"\n" for row in rows),encoding="utf-8")
print(json.dumps({"variants":len(outputs),"two_turn_candidates":sum(x["target_turns"]==2 and x["turns"]!=[] for x in outputs),
                  "three_turn_candidates":sum(x["target_turns"]==3 and x["turns"]!=[] for x in outputs),
                  "excluded":sum(x["turns"]==[] for x in outputs)}))
