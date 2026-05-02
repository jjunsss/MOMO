"""Ollama HTTP provider.

Uses /api/chat with optional structured output (``format`` = JSON schema) and
Ollama's ``think`` parameter for reasoning-trace models (Qwen3, Qwen3.5,
DeepSeek-R1, etc.). Requires an Ollama server reachable at ``base_url`` and
the named model already pulled. Uses ``requests`` (already in the venv) so
no new dependency.
"""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

from meeting_ai.providers.llm.base import LLMError, LLMResponse


class OllamaProvider:
    name = "ollama"

    def __init__(self, config: Dict[str, Any]) -> None:
        self._model = str(config.get("model") or "qwen3.5:9b")
        self._base_url = str(config.get("base_url") or "http://localhost:11434").rstrip("/")
        self._temperature = float(config.get("temperature", 0.1))
        self._timeout = float(config.get("request_timeout_seconds", 1800))
        self._num_ctx = int(config.get("num_ctx", 32768))
        # default thinking on; the synthesis nodes can override per call.
        self._think_default = _truthy(config.get("think", True))
        self._top_p = config.get("top_p")
        self._repeat_penalty = config.get("repeat_penalty")

    def call(
        self,
        prompt: str,
        *,
        json_schema: Optional[Dict[str, Any]] = None,
        max_tokens: Optional[int] = None,
        think: Optional[bool] = None,
        system: Optional[str] = None,
    ) -> LLMResponse:
        try:
            import requests
        except ImportError as exc:  # pragma: no cover - venv ships requests
            raise LLMError("requests is required to call Ollama") from exc

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        options: Dict[str, Any] = {
            "temperature": self._temperature,
            "num_ctx": self._num_ctx,
        }
        # Thinking models (Qwen3, Qwen3.5, DeepSeek-R1) emit a reasoning trace
        # that consumes ``num_predict`` tokens before the answer is generated.
        # Without an explicit thinking budget the answer is silently empty,
        # which is exactly the failure we hit on Qwen3.5:9b. We pad the user's
        # ``max_tokens`` with a thinking allowance so the answer has room.
        thinking_on = bool(self._think_default if think is None else think)
        if max_tokens:
            base = int(max_tokens)
            options["num_predict"] = base + (4096 if thinking_on else 0)
        elif thinking_on:
            options["num_predict"] = 8192
        if self._top_p is not None:
            options["top_p"] = float(self._top_p)
        if self._repeat_penalty is not None:
            options["repeat_penalty"] = float(self._repeat_penalty)

        payload: Dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "stream": False,
            "options": options,
            # Ollama returns reasoning in a separate `thinking` field when
            # `think: true`. Newer Qwen3/Qwen3.5 small models default to off.
            "think": thinking_on,
        }
        if json_schema is not None:
            payload["format"] = json_schema

        url = "{0}/api/chat".format(self._base_url)
        try:
            response = requests.post(url, json=payload, timeout=self._timeout)
        except requests.RequestException as exc:
            raise LLMError("Ollama request failed: {0}".format(exc)) from exc
        if response.status_code != 200:
            raise LLMError(
                "Ollama returned HTTP {0}: {1}".format(response.status_code, response.text[:500])
            )
        try:
            data = response.json()
        except json.JSONDecodeError as exc:
            raise LLMError("Ollama returned non-JSON body") from exc
        message = data.get("message", {}) if isinstance(data.get("message"), dict) else {}
        content = str(message.get("content", ""))
        thinking = str(message.get("thinking", "") or "")
        # Make the thinking trace observable to callers via ``raw``; the user-
        # visible output is still ``text``.
        return LLMResponse(text=content, raw={**data, "_thinking": thinking})


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)
