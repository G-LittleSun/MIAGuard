"""Record a development-only recheck of the original five-turn sessions."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
issues = {
 "s_173b030fcf5fd3dcd095227b":("rewrite",["repetitive_turn"],"Turns 1 and 3 ask for the same buyer, while turn 5 repeats buyer and number."),
 "s_437a104284d832b1cd5f0849":("rewrite",["repetitive_turn","wrong_family"],"Turn 5 revisits the qualifier already quoted in turn 1; turn 4 asks about missing results rather than citation."),
 "s_04986002cdaa941b4e001f09":("rewrite",["repetitive_turn","wrong_evidence"],"Turn 5 recombines details already asked; review output for turns 2, 3 and 5 omits one required document ID."),
 "s_3e92f4335d69f54d3c656df2":("rewrite",["repetitive_turn"],"Turns 1, 3 and 5 repeat the heating-cost and market-concerns contrast."),
 "s_08e8938c350e35aa9a8fa6fb":("uncertain",["repeated_absence_pattern"],"The missing facts differ, but five consecutive absent-answer questions need a session-level naturalness review."),
 "s_1709052c2c393baf1346bd1f":("uncertain",["repeated_absence_pattern"],"The missing facts differ, but five consecutive absent-answer questions need a session-level naturalness review."),
 "s_0036417c86948330e11bae92":("rewrite",["repetitive_turn"],"Turns 3 and 4 both recover corporate governance campaigns."),
 "s_399af0c268f41f6b4588a0ef":("rewrite",["repetitive_turn","source_spelling"],"Turn 5 combines names and month already asked; source spells the second rover Sprit."),
 "s_09006cbd05dd713ca18ac43b":("rewrite",["repetitive_turn","source_interpretation"],"Turn 4 repeats IBM from turn 1; turn 5 requires care about the earlier title change."),
 "s_35f642a015443be4b6938941":("rewrite",["repetitive_turn","source_truncated"],"The final summary repeats prior points and the source cuts off in the server description."),
 "s_018315d1c2b3844d065f3271":("rewrite",["repetitive_turn"],"Turn 4 repeats the measure from turn 1 and turn 5 combines earlier answers."),
 "s_1719eb75e00dd29b35bc741b":("rewrite",["repetitive_turn"],"Turn 5 repeats the dispute and leader covered in turns 1 and 4."),
 "s_153a5ba7fed9ffda622c892d":("rewrite",["repetitive_turn","source_truncated","headline_dependency"],"Several turns repeat the bonus decision; the body cuts off after 'were not willing'."),
 "s_1d0d4cac7b5f8389d38dd6cc":("rewrite",["repetitive_turn"],"Five questions revisit the playoff run without Holdsclaw; the excerpt has few independent facts."),
}
sessions=[json.loads(x) for x in (HERE/"session_inventory.jsonl").read_text(encoding="utf-8").splitlines()]
assert {x["session_id"] for x in sessions} == set(issues)
rows=[]
for item in sessions:
    decision,codes,notes=issues[item["session_id"]]
    rows.append({"session_id":item["session_id"],"variant_id":item["session_id"]+"_baseline_5",
                 "decision":decision,"reason_codes":codes,"notes":notes,
                 "reviewer_kind":"codex_agent_self_check","model_id_or_person_id":"Codex (provider snapshot unavailable)",
                 "source_refs":item["source_doc_ids"],"original_request_ids":[x["request_id"] for x in item["turns"]],
                 "purpose":"same-source five-turn diagnostic; not independently reviewed"})
out=HERE/"baseline_review.jsonl"
if out.exists():raise FileExistsError(out)
out.write_text("".join(json.dumps(x,ensure_ascii=False)+"\n" for x in rows),encoding="utf-8")
print(json.dumps({"sessions":len(rows),"decisions":{k:sum(x["decision"]==k for x in rows) for k in ("rewrite","uncertain")}}))
