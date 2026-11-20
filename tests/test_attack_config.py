from pathlib import Path

from miaguard.config import load_attack_config


def test_existing_ollama_attack_config_remains_supported():
    config = load_attack_config(Path("configs/attacks/ollama_smoke.yaml"))

    assert config.generation_backend == "ollama"
    assert config.embedding_backend == "ollama"
    assert config.generation_model == "qwen2.5:3b"


def test_teacher_local_config_uses_downloaded_models():
    config = load_attack_config(Path("configs/attacks/teacher_local_smoke.yaml"))

    assert config.generation_backend == "transformers"
    assert config.generation_model == "LLM/mistralai/mistral-7b-instruct-v0-2"
    assert config.embedding_backend == "sentence_transformers"
    assert config.embedding_model.endswith("all_minilm_l6_v2")
    assert config.direct_rag_mia_threshold == 0.5
    assert config.direct_rag_mia_max_tokens == 12
    assert config.s2_mia_threshold == 0.7
    assert config.s2_mia_prefix_words == 10


def test_ag_news_calibrated_config_uses_independent_threshold_report():
    config = load_attack_config(Path("configs/attacks/ag_news_calibrated.yaml"))

    assert config.masked_threshold == 0.2
    assert config.masked_threshold_source == "ag_news_calibration_100_per_class"
    assert config.s2_mia_threshold == 0.915322333574295
    assert config.s2_mia_threshold_source == "ag_news_calibration_100_per_class"
    assert config.generation_model == "LLM/mistralai/mistral-7b-instruct-v0-2"
    assert config.generation_load_mode == "bf16"


def test_ag_news_int8_config_selects_bitsandbytes_loading():
    config = load_attack_config(Path("configs/attacks/ag_news_calibrated_int8.yaml"))

    assert config.generation_backend == "transformers"
    assert config.generation_load_mode == "int8"
    assert config.generation_model == "LLM/mistralai/mistral-7b-instruct-v0-2"


def test_progressive_judge_qwen_config_uses_local_bf16_model():
    config = load_attack_config(
        Path("configs/attacks/ag_news_progressive_judge_qwen2_5_7b_bf16.yaml")
    )

    assert config.generation_backend == "transformers"
    assert config.generation_load_mode == "bf16"
    assert config.generation_model == "LLM/Qwen2.5-7B-Instruct"
    assert config.embedding_model.endswith("all_minilm_l6_v2")
