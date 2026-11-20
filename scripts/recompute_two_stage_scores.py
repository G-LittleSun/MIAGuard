from __future__ import annotations

import argparse
import json
from pathlib import Path

from rag_mia_data.io_utils import read_jsonl, write_json_atomic

from miaguard.two_stage_attack_comparison import _stage_scores


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--threshold", required=True, type=float)
    args = parser.parse_args()

    output = Path(args.output).resolve()
    attack = list(read_jsonl(output / "with_defense_decisions.jsonl"))
    benign = list(read_jsonl(output / "benign_decisions.jsonl"))
    stages = _stage_scores(attack, benign, args.threshold)
    write_json_atomic(output / "stage_scores.json", stages)

    summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
    summary["query_stage_f1"] = stages["query_stage"][
        "overall_detection_metrics"
    ]["f1"]
    summary["session_stage_f1"] = stages["session_stage"][
        "overall_detection_metrics"
    ]["f1"]
    write_json_atomic(output / "summary.json", summary)
    manifest_path = output / "run_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("continuous_attack_sessions"):
        manifest["limitations"] = [
            "Smoke-scale results are functional evidence, not paper-level statistics.",
            "Attack rows are grouped into one continuous session per attack type; "
            "the session detector activates on turn three and its latest assessment "
            "is cached according to the gateway evaluation interval.",
        ]
        write_json_atomic(manifest_path, manifest)
    print(json.dumps(stages, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
