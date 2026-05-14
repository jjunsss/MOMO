"""Runtime environment overrides shared by CLI, GUI, and containers."""

from __future__ import annotations

import os
from typing import Any, Dict


def apply_environment_overrides(
    profile: Dict[str, Any],
    pipeline_config: Dict[str, Any],
    models_config: Dict[str, Any],
) -> None:
    """Apply MOMO_* environment values after file/default config is loaded."""
    env_to_model = {
        "MOMO_ASR_MODEL": ("asr", "model"),
        "MOMO_ASR_LANGUAGE": ("asr", "language"),
        "MOMO_ASR_DEVICE": ("asr", "device"),
        "MOMO_LLM_PROVIDER": ("llm", "provider"),
        "MOMO_LLM_MODEL": ("llm", "model"),
        "MOMO_LLM_BASE_URL": ("llm", "base_url"),
        "MOMO_LLM_API_KEY_ENV": ("llm", "api_key_env"),
    }
    for env_key, (section, config_key) in env_to_model.items():
        value = os.environ.get(env_key)
        if value:
            models_config.setdefault(section, {})[config_key] = value

    for env_key, config_key in [
        ("MOMO_LLM_NUM_CTX", "num_ctx"),
        ("MOMO_LLM_REQUEST_TIMEOUT_SECONDS", "request_timeout_seconds"),
    ]:
        value = os.environ.get(env_key)
        if value:
            models_config.setdefault("llm", {})[config_key] = _env_int(env_key, value)

    summary_mode = os.environ.get("MOMO_LLM_SUMMARY_MODE")
    if summary_mode:
        pipeline_config.setdefault("rendering", {})["llm_summary_mode"] = summary_mode
    critique = os.environ.get("MOMO_ENABLE_CRITIQUE")
    if critique:
        pipeline_config.setdefault("rendering", {})["enable_critique"] = _env_bool(
            "MOMO_ENABLE_CRITIQUE",
            critique,
        )

    output_language = os.environ.get("MOMO_OUTPUT_LANGUAGE")
    if output_language:
        profile.setdefault("meeting_profile", {})["output_language"] = output_language
        pipeline_config.setdefault("rendering", {})["output_language"] = output_language


def _env_int(env_key: str, value: str) -> int:
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(
            "environment variable {0} must be an integer: {1}".format(
                env_key, value
            )
        ) from exc


def _env_bool(env_key: str, value: str) -> bool:
    lowered = value.strip().lower()
    if lowered in {"1", "true", "yes", "y", "on"}:
        return True
    if lowered in {"0", "false", "no", "n", "off"}:
        return False
    raise ValueError(
        "environment variable {0} must be a boolean: {1}".format(env_key, value)
    )
