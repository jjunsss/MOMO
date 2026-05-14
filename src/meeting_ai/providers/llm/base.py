"""LLM provider contract."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Protocol


class LLMError(RuntimeError):
    """Raised when an LLM provider cannot return a usable response."""


@dataclass(frozen=True)
class LLMResponse:
    text: str
    raw: Dict[str, Any] = field(default_factory=dict)


class LLMProvider(Protocol):
    """Minimal LLM contract used by synthesis nodes.

    Implementations must be deterministic given the same input + config so
    pipeline reruns are reproducible. ``call`` should raise :class:`LLMError`
    on transport failures so the pipeline can fail loudly instead of silently
    replacing the LLM with rule-based output.
    """

    name: str

    def call(
        self,
        prompt: str,
        *,
        json_schema: Optional[Dict[str, Any]] = None,
        max_tokens: Optional[int] = None,
        think: Optional[bool] = None,
        system: Optional[str] = None,
    ) -> LLMResponse:  # pragma: no cover - protocol
        ...
