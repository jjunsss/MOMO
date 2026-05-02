"""Build an LLM provider from a models.yaml ``llm`` block."""

from __future__ import annotations

from typing import Any, Dict, Optional

from meeting_ai.providers.llm.base import LLMProvider
from meeting_ai.providers.llm.deterministic import DeterministicStubProvider
from meeting_ai.providers.llm.ollama import OllamaProvider
from meeting_ai.providers.llm.openai_compatible import OpenAICompatibleProvider


def build_llm_provider(llm_config: Optional[Dict[str, Any]]) -> LLMProvider:
    config = dict(llm_config or {})
    provider_name = str(config.get("provider") or "deterministic_mvp").lower().strip()
    if provider_name in {"deterministic_mvp", "deterministic", "none", ""}:
        return DeterministicStubProvider(config)
    if provider_name == "ollama":
        return OllamaProvider(config)
    if provider_name in {"openai", "openai_compatible", "openai-compatible"}:
        return OpenAICompatibleProvider(config)
    raise ValueError("unsupported llm provider: {0}".format(provider_name))
