"""OpenAI-compatible chat completions provider.

Works with any endpoint that speaks the OpenAI Chat Completions schema:
OpenAI itself, vLLM, llama.cpp's server, LocalAI, OpenRouter, and so on.
Supports JSON-schema response_format when the upstream advertises it.

API key resolution order: explicit ``api_key`` config -> ``api_key_env`` env
var -> ``OPENAI_API_KEY``. Endpoints that do not require auth (e.g. local
vLLM) work with the key omitted.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

from meeting_ai.providers.llm.base import LLMError, LLMResponse


class OpenAICompatibleProvider:
    name = "openai_compatible"

    def __init__(self, config: Dict[str, Any]) -> None:
        self._model = str(config.get("model") or "gpt-4o-mini")
        self._base_url = str(
            config.get("base_url") or "https://api.openai.com/v1"
        ).rstrip("/")
        self._temperature = float(config.get("temperature", 0.1))
        self._timeout = float(config.get("request_timeout_seconds", 600))
        env_var = config.get("api_key_env") or "OPENAI_API_KEY"
        self._api_key = config.get("api_key") or os.environ.get(env_var)

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
            raise LLMError("requests is required to call OpenAI-compatible APIs") from exc

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        payload: Dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "temperature": self._temperature,
        }
        if max_tokens:
            payload["max_tokens"] = int(max_tokens)
        if json_schema is not None:
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "structured_response",
                    "schema": json_schema,
                    "strict": True,
                },
            }
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = "Bearer {0}".format(self._api_key)

        url = "{0}/chat/completions".format(self._base_url)
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=self._timeout)
        except requests.RequestException as exc:
            raise LLMError("OpenAI-compatible request failed: {0}".format(exc)) from exc
        if response.status_code != 200:
            raise LLMError(
                "Upstream returned HTTP {0}: {1}".format(response.status_code, response.text[:500])
            )
        try:
            data = response.json()
        except json.JSONDecodeError as exc:
            raise LLMError("Upstream returned non-JSON body") from exc
        choices = data.get("choices") or []
        if not choices:
            raise LLMError("Upstream returned no choices")
        message = choices[0].get("message", {})
        content = message.get("content", "") if isinstance(message, dict) else ""
        return LLMResponse(text=str(content), raw=data)
