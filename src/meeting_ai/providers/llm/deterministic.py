"""Stub provider returning empty responses.

Used as the offline fallback when no LLM is configured. The synthesis nodes
treat an empty response as 'no LLM available, defer to deterministic path'.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from meeting_ai.providers.llm.base import LLMResponse


class DeterministicStubProvider:
    name = "deterministic_mvp"

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        self._config = config or {}

    def call(
        self,
        prompt: str,
        *,
        json_schema: Optional[Dict[str, Any]] = None,
        max_tokens: Optional[int] = None,
        think: Optional[bool] = None,
        system: Optional[str] = None,
    ) -> LLMResponse:
        return LLMResponse(text="", raw={"provider": self.name, "stub": True})
