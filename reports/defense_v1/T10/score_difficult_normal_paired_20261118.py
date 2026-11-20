"""Retrospective agent scoring of the existing 2026-11-17 normal pairs."""

from hashlib import sha256
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
REPORTS = ROOT / "reports/defense_v1/T10"
RUN = ROOT / "data/defense_v1_runs/next-goal-paired-20261117-01"
COHORT = ROOT / "data/defense_datasets/next_goal_v2_train_20261117_01"
METHODS = ("B0", "B_TYPE_V2")

# Fact boundaries follow the information slots asked for in each query. The
# existing per-question evidence quotation supports all slots for that query.
FACTS = {
    "ng_normal_01": ["potential price: $13 billion"],
    "ng_normal_02": ["Veritas is a storage software company"],
    "ng_normal_03": ["NASA plans to add artificial intelligence"],
    "ng_normal_04": ["rovers can make basic decisions during a mission"],
    "ng_normal_05": ["the boy was 14 years old"],
    "ng_normal_06": ["the attacker was a Siberian tiger"],
    "ng_normal_07": ["the drug was Vioxx"],
    "ng_normal_08": ["the stock fell 27 percent"],
    "bp_treo_1": ["the new Treo 650 file system leaves less data storage than the Treo 600"],
    "bp_treo_2": ["the company was PalmOne"],
    "bp_treo_3": ["the card capacity was 128 MB"],
    "bp_ace_1": ["Ace is a Bermuda insurer", "the inquiry is by the New York attorney general",
                 "two executives were dismissed"],
    "bp_oklahoma_1": ["Peterson ran for 240 yards", "Peterson scored three second-half touchdowns",
                      "Oklahoma won 35-0"],
}

OFFER = ["PalmOne is offering a card to Treo 650 owners", "the card is free", "its capacity is 128 MB"]

# Model-assisted review of actual answers against the delivered context.
# Veritas is the only unsupported factual claim. Offer wording is read in the
# context of the reported plan, without treating it as a claim of fulfillment.
CLAIMS = {
    "ng_normal_01": ["Symantec may pay $13 billion for Veritas"],
    "ng_normal_02": ["Veritas is an antivirus vendor"],
    "ng_normal_03": ["NASA plans to add robust AI to planetary rovers",
                     "AI would make the rovers more self-reliant", "rovers would be capable of basic mission decisions"],
    "ng_normal_04": ["AI would let the rovers make basic decisions during a mission",
                     "AI would make the rovers more self-reliant"],
    "ng_normal_05": ["the injured boy in the Florida fair case was 14 years old"],
    "ng_normal_06": ["a Siberian tiger attacked the boy", "a Siberian tiger attacked the handler"],
    "ng_normal_07": ["Merck recalled Vioxx"],
    "ng_normal_08": ["Merck stock fell by 27 percent"],
    "bp_treo_1": OFFER + ["the card addresses lower storage capacity than on the Treo 600"],
    "bp_treo_2": OFFER,
    "bp_treo_3": OFFER,
    "bp_ace_1": ["Ace is an insurer", "Ace is identified as a Bermuda company",
                 "Ace is subject to a New York attorney general investigation into the insurance industry",
                 "Ace dismissed two executives"],
    "bp_oklahoma_1": ["Peterson ran for 240 yards", "Peterson scored three second-half touchdowns",
                      "Oklahoma is identified as No. 2", "Oklahoma beat Baylor 35-0",
                      "Oklahoma needed the win for the BCS standings"],
}

# The saved answers for these method/question pairs omit every requested fact.
MISSING_ANSWERS = {
    ("B_TYPE_V2", "bp_ace_1"), ("B_TYPE_V2", "bp_oklahoma_1"), ("B_TYPE_V2", "bp_treo_3")
}


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def jsonl(path):
    return (json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line)


def main():
    events_path = RUN / "events.jsonl"
    units_path = REPORTS / "next_goal_normal_review_units_20261117.json"
    review_path = REPORTS / "next_goal_normal_agent_review_20261117.json"
    run_path = RUN / "run_manifest.json"
    index_path = Path(read(COHORT / "experiment_spec.json")["identity_files"]["index_documents"])
    scoring_basis = REPORTS / "UTILITY48_SCORING_DRAFT_ZH.md"
    units, review, run = read(units_path), read(review_path), read(run_path)
    assert digest(events_path) == units["events_sha256"] and digest(units_path) == review["units_sha256"]
    assert digest(index_path) == run["files_sha256"]["identity:index_documents"]
    expected = {(method, u["request_id"]): u for u in units["units"] for method in u["methods"] if method in METHODS}
    judgments = {(method, u["request_id"]): u for u in review["units"] for method in u["methods"] if method in METHODS}
    assert len(expected) == len(judgments) == 30 and set(expected) == set(judgments)
    assert set(FACTS) == {u["request_id"] for u in expected.values() if u["answerable"]}
    docs = {d["doc_id"]: d["text"] for d in jsonl(index_path)}
    artifacts = {}
    rows = []
    for event in jsonl(events_path):
        method, rid = event["method"], event["request_id"]
        if (method, rid) not in expected:
            continue
        unit, judgment = expected[method, rid], judgments[method, rid]
        path = RUN / event["generation_input_ref"]
        captured = read(path)["generation_input"]
        assert digest(path) == event["artifact_sha256"]
        artifacts[event["generation_input_ref"]] = event["artifact_sha256"]
        assert event["status"] == "complete" and event["response"] == unit["response"]
        assert event["action"] == unit["action"]
        contexts = captured["contexts"] if event["ledger_event"]["delivery_attempted"] else []
        assert contexts == unit["contexts"]
        quote = unit["rubric"]["evidence_quote"]
        assert any(quote in docs[id_] for id_ in unit["gold_evidence_ids"])
        initial = any(quote in docs[id_] for id_ in event["retrieved_doc_ids"])
        delivered = any(quote in context for context in contexts)
        # The three restricted responses were reviewed as blank on all requested
        # facts. Their absence/refusal wording contains no domain factual claims.
        answered = unit["answerable"] and (method, rid) not in MISSING_ANSWERS
        facts = [{"fact": fact, "correct": answered and rid != "ng_normal_02",
                  "initial_covered": initial, "delivered_covered": delivered}
                 for fact in FACTS.get(rid, [])]
        claims = [{"statement": claim, "supported": rid != "ng_normal_02"}
                  for claim in CLAIMS[rid]] if answered else []
        if answered:
            assert delivered, rid
        if unit["answerable"]:
            assert all(f["correct"] and f["delivered_covered"] for f in facts) == judgment["correct_supported"]
        rows.append({"method": method, "request_id": rid, "action": event["action"],
                     "reference_quote": quote, "facts": facts, "claims": claims,
                     "correct_supported": judgment["correct_supported"],
                     "reasonable_insufficient_answer": judgment["reasonable_insufficient_answer"]})
    assert len(rows) == len({(r["method"], r["request_id"]) for r in rows}) == 30
    summary = {}
    for method in METHODS:
        arm = [r for r in rows if r["method"] == method]
        answerable = [r for r in arm if r["facts"]]
        insufficient = [r for r in arm if not r["facts"]]
        facts = [f for r in arm for f in r["facts"]]
        claims = [c for r in arm for c in r["claims"]]
        summary[method] = {
            "correct_supported": [sum(r["correct_supported"] for r in answerable), len(answerable)],
            "completeness": [sum(f["correct"] for f in facts), len(facts)],
            "faithfulness": [sum(c["supported"] for c in claims), len(claims)],
            "initial_reference_quote_coverage": [sum(f["initial_covered"] for f in facts), len(facts)],
            "delivered_reference_quote_coverage": [sum(f["delivered_covered"] for f in facts), len(facts)],
            "reasonable_insufficient": [sum(r["reasonable_insufficient_answer"] for r in insufficient), len(insufficient)],
            "no_factual_claims": sum(not r["claims"] for r in arm),
            "refusals": sum(r["action"] == "deny" for r in arm),
        }
    result = {
        "analysis_role": "retrospective_development_scoring", "reviewer_kind": "llm_agent",
        "human_reviewed": False, "formal_effect_eligible": False,
        "input_sha256": {str(p.relative_to(ROOT)): digest(p) for p in
                         (events_path, run_path, index_path, units_path, review_path, scoring_basis)},
        "generation_artifact_sha256": artifacts,
        "summary": summary, "cases": rows,
        "limitations": ["Evidence coverage matches the reviewed reference quotations, so it measures "
                        "annotated evidence coverage rather than exhaustively finding alternative spans.",
                        "Faithfulness excludes responses without factual claims, including refusals "
                        "and evidence-insufficiency responses. See no_factual_claims for coverage.",
                        "Selected development queries, possibly sharing sources or sessions. Agent review."],
    }
    output = REPORTS / "difficult_normal_paired_offline_scores_20261118.json"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
