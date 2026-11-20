"""Replay selected formal-train sessions through the v1 observe gateway."""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import time
from collections import Counter
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from miaguard.attack_pattern_library import AttackPatternLibrary
from miaguard.config import load_attack_config
from miaguard.data import vector_store_path
from miaguard.defense import GuardedRAG
from miaguard.model_client import create_model_client
from miaguard.progressive_judge import ProgressiveJudge, load_progressive_judge_config
from miaguard.query_bank.sessions import plan_partition_sessions
from miaguard.query_bank.storage import QueryBank, QueryBankPaths
from miaguard.query_bank.threshold_split import load_threshold_split
from miaguard.two_stage_gateway import TwoStageGateway, load_defense_v1_observe_config
from miaguard.vector_store import UnifiedVectorStore


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    low = int(position)
    high = min(low + 1, len(ordered) - 1)
    return ordered[low] * (high - position) + ordered[high] * (position - low)


def execute(spec_path: Path, output_root: Path) -> dict[str, Any]:
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    if spec.get("partition") != "train" or spec.get("head") != "logprob":
        raise ValueError("Observe smoke accepts formal train and logprob only")
    session_keys = spec.get("session_keys")
    if not isinstance(session_keys, list) or not session_keys or len(session_keys) != len(set(session_keys)):
        raise ValueError("Specify distinct formal-train session_keys")
    project_root = Path(__file__).resolve().parents[1]
    paths = {key: project_root / str(spec[key]) for key in ("split", "attack_config", "judge_config", "gateway_config")}
    bound = load_defense_v1_observe_config(paths["gateway_config"], project_root)
    judge_config = load_progressive_judge_config(paths["judge_config"], project_root)
    judge_config.validate_partition("train")
    if judge_config.prompt_version != spec["prompt_version"]:
        raise ValueError("Judge prompt_version differs from spec")
    bank = QueryBank.load(QueryBankPaths(project_root, spec["query_bank_id"], spec["dataset_id"]))
    split = load_threshold_split(paths["split"], bank)
    all_sessions = plan_partition_sessions(bank, split, "train", target_turns=5)
    indexed = {session.session_key: session for session in all_sessions}
    if any(key not in indexed for key in session_keys):
        raise ValueError("A selected session is not in the frozen train partition")
    sessions = [indexed[key] for key in session_keys]
    if any(len(session.queries) < 3 for session in sessions):
        raise ValueError("Observe smoke requires sessions of at least 3 turns")
    if output_root.exists():
        raise FileExistsError(f"Run directory already exists: {output_root}")
    output_root.mkdir(parents=True)
    write_json(output_root / "experiment_spec.json", spec)
    started = datetime.now(timezone.utc).isoformat()
    manifest = {
        "schema_version": 1, "experiment_id": "E00-observe", "run_id": output_root.name,
        "status": "running", "started_at": started, "partition": "train",
        "query_bank_id": bank.bank_id, "query_bank_sha256": bank.sha256,
        "split_id": split["split_id"], "session_keys": session_keys,
        "frozen_model_sha256": bound.scorer.sha256, "query_only_sha256": bound.query_only_sha256,
        "fpr_cap": bound.fpr_cap, "head": bound.scorer.head,
        "prompt_version": judge_config.prompt_version,
        "input_sha256": {key: digest(path) for key, path in paths.items()},
        "spec_sha256": digest(spec_path),
    }
    write_json(output_root / "run_manifest.json", manifest)
    try:
        attack_config = load_attack_config(paths["attack_config"])
        client = create_model_client(attack_config, project_root)
        client.validate_models()
        store = UnifiedVectorStore.load(vector_store_path(project_root, spec["source_run_id"], spec["dataset_id"]), client)
        library = AttackPatternLibrary.load(judge_config.manifest_path)
        judge = ProgressiveJudge(judge_config, client, attack_config.generation_model, library)
        trace_rows = []

        def save_trace(adapted):
            trace_rows.append({"trace_ref": adapted.trace_ref, "risk": adapted.risk.to_dict(), "trace": asdict(adapted.trace)})

        gateway = TwoStageGateway(bound.gateway, query_detector=judge, session_detector=judge,
                                  frozen_scorer=bound.scorer,
                                  query_only_threshold=bound.query_only_threshold,
                                  fused_threshold=bound.fused_threshold,
                                  trace_sink=save_trace)
        rag = GuardedRAG(store, gateway, top_k=int(spec["top_k"]))
        request_rows = []
        decision_rows = []
        timings = []
        for session in sessions:
            for turn, query in enumerate(session.queries, 1):
                text = str(query["query_text"])
                request = {"request_id": str(query["query_id"]), "session_id": session.session_key, "query": text}
                request_rows.append(request)
                before = time.perf_counter()
                prepared = rag.prepare(text, session.session_key)
                timings.append((time.perf_counter() - before) * 1000)
                decision_rows.append({"request_id": request["request_id"], "session_id": session.session_key,
                                      "turn_index": turn, "retrieved_doc_ids": prepared.retrieved_doc_ids,
                                      "retrieval_scores": prepared.retrieval_scores, "contexts": prepared.contexts,
                                      "decision": prepared.decision.to_dict(), "decision_latency_ms": prepared.decision_latency_ms})
        for name, rows in (("requests.jsonl", request_rows), ("decisions.jsonl", decision_rows), ("judge_traces.jsonl", trace_rows)):
            (output_root / name).write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
        trace_by_ref = {row["trace_ref"]: row for row in trace_rows}
        max_difference = 0.0
        for row in decision_rows:
            risk = row["decision"]["two_stage_assessment"]["frozen_risk"]
            if risk["score"] is None:
                continue
            source_score = trace_by_ref[risk["query_trace_ref"]]["trace"]["logprob"]["score"]
            if risk["risk_source"] == "fusion":
                session_score = trace_by_ref[risk["session_trace_ref"]]["trace"]["logprob"]["score"]
                offline = bound.scorer.score(source_score, session_score)
            else:
                offline = source_score
            max_difference = max(max_difference, abs(offline - risk["score"]))
        summary = {
            "schema_version": 1, "experiment_id": "E00-observe", "partition": "train",
            "session_count": len(sessions), "request_count": len(request_rows),
            "query_judge_calls": sum(row["risk"]["stage"] == "query" for row in trace_rows),
            "session_judge_calls": sum(row["risk"]["stage"] == "session" for row in trace_rows),
            "risk_source_counts": dict(Counter(row["decision"]["two_stage_assessment"]["frozen_risk"]["risk_source"] for row in decision_rows)),
            "status_counts": dict(Counter(row["decision"]["two_stage_assessment"]["frozen_risk"]["status"] for row in decision_rows)),
            "actions": dict(Counter(row["decision"]["access_action"] for row in decision_rows)),
            "full_context_count": sum(len(row["contexts"]) == len(row["retrieved_doc_ids"]) for row in decision_rows),
            "latency_ms": {"p50": statistics.median(timings), "p95": percentile(timings, .95), "max": max(timings)},
            "max_online_offline_score_difference": max_difference,
            "saved_trace_count": len(trace_rows),
            "limitations": "Development smoke on old formal train sessions; no defense leakage or answer-quality result.",
        }
        write_json(output_root / "comparison.json", summary)
        manifest.update(status="complete", finished_at=datetime.now(timezone.utc).isoformat(), result_sha256=digest(output_root / "comparison.json"))
        write_json(output_root / "run_manifest.json", manifest)
        return summary
    except BaseException as exc:
        manifest.update(status="interrupted", finished_at=datetime.now(timezone.utc).isoformat(), error=repr(exc))
        write_json(output_root / "run_manifest.json", manifest)
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment-spec", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(execute(args.experiment_spec, args.output_root), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
