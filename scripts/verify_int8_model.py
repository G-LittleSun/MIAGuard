from __future__ import annotations

import argparse
import json
from pathlib import Path

import torch

from miaguard.config import load_attack_config
from miaguard.model_client import create_model_client


def memory_snapshot() -> dict[str, float]:
    torch.cuda.synchronize()
    free, total = torch.cuda.mem_get_info()
    return {
        "allocated_mib": round(torch.cuda.memory_allocated() / 1024**2, 1),
        "reserved_mib": round(torch.cuda.memory_reserved() / 1024**2, 1),
        "peak_allocated_mib": round(torch.cuda.max_memory_allocated() / 1024**2, 1),
        "global_used_mib": round((total - free) / 1024**2, 1),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--project-root", default=".")
    args = parser.parse_args()

    root = Path(args.project_root).resolve()
    config = load_attack_config(args.config)
    if config.generation_backend != "transformers":
        raise ValueError("INT8 verification requires the Transformers backend")
    if config.generation_load_mode != "int8":
        raise ValueError("INT8 verification requires generation.load_mode: int8")
    client = create_model_client(config, root)
    client.validate_models()
    torch.cuda.reset_peak_memory_stats()
    before = memory_snapshot()
    model, _ = client._load_generation(config.generation_model)
    after_load = memory_snapshot()

    import bitsandbytes as bnb

    int8_layers = sum(
        isinstance(module, bnb.nn.Linear8bitLt) for module in model.modules()
    )
    response = client.generate(
        config.generation_model,
        "Reply with exactly: INT8_OK",
        max_tokens=8,
        temperature=0.0,
    )
    after_generate = memory_snapshot()
    report = {
        "status": "passed" if int8_layers > 0 and bool(response.strip()) else "failed",
        "model": config.generation_model,
        "load_mode": config.generation_load_mode,
        "bitsandbytes_version": bnb.__version__,
        "int8_linear_layer_count": int8_layers,
        "model_memory_footprint_mib": round(model.get_memory_footprint() / 1024**2, 1),
        "response": response,
        "memory": {
            "before": before,
            "after_load": after_load,
            "after_generate": after_generate,
        },
    }
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
