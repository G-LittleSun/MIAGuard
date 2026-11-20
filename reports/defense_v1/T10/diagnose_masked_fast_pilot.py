"""Produce separate, format-aware engineering diagnostics without changing scores."""
import argparse
import hashlib
import json
import re
from pathlib import Path

from miaguard.masked_mia import _normalize_answer


def diagnose(response, answers, action):
    if action == "deny":
        return {"status": "denied", "format": None, "matched": 0, "total": len(answers)}
    text = response.strip()
    fenced = re.fullmatch(r"```(?:json)?\s*\n(.*?)\n```", text, re.DOTALL | re.IGNORECASE)
    if fenced:
        text = fenced.group(1).strip()
    try:
        data = json.loads(text)
    except (ValueError, TypeError):
        return {"status": "parse_failed", "format": None, "matched": None, "total": len(answers)}
    if isinstance(data, list):
        recovered, fmt = data, "array"
    elif isinstance(data, dict) and isinstance(data.get("answers"), list):
        recovered, fmt = data["answers"], "object_answers"
    else:
        return {"status": "unsupported_structure", "format": None, "matched": None, "total": len(answers)}
    matches = sum(_normalize_answer(str(a)) == _normalize_answer(str(b))
                  for a, b in zip(answers, recovered))
    return {"status": "parsed", "format": ("fenced_" if fenced else "") + fmt,
            "matched": matches, "total": len(answers)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("run", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    read = lambda p: [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
    events = {(x["method"], x["request_id"]): x for x in read(args.run / "events.jsonl")}
    labels = {x["request_id"]: x for x in read(args.run / "labels.jsonl")}
    result = []
    for score in read(args.run / "attack_scores.jsonl"):
        if score["attack_type"] != "masked_mia":
            continue
        rid = score["request_ids"][0]
        event = events[score["method"], rid]
        result.append({"method": score["method"], "request_id": rid, "doc_id": score["doc_id"],
                       "action": event["action"], "strict_score": score["score"],
                       "diagnostic_only": True, "diagnostic": diagnose(event["response"] or "", labels[rid]["answers"], event["action"])})
    args.output.write_text(json.dumps({"run_id": args.run.name, "rows": result,
                                     "input_sha256": {name: hashlib.sha256((args.run / name).read_bytes()).hexdigest()
                                                      for name in ["events.jsonl", "labels.jsonl", "attack_scores.jsonl"]},
                                     "formal_effect_eligible": False}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
