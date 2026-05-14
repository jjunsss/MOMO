"""LLM readiness checks for GUI-triggered runs."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DISALLOWED_LOCAL_STUB_PROVIDERS = {"none", "deterministic", "deterministic_mvp"}
OPENAI_COMPATIBLE_PROVIDERS = {"openai", "openai_compatible", "openai-compatible"}
SUPPORTED_PROVIDERS = {"ollama", *OPENAI_COMPATIBLE_PROVIDERS}


@dataclass(frozen=True)
class LLMQualityIssue:
    """A user-facing reason the GUI should not start a quality-protected run."""

    code: str
    provider: str
    model: str
    detail: str = ""


def check_llm_ready(
    models_config: Dict[str, Any],
    *,
    timeout_seconds: float = 2.0,
) -> Optional[LLMQualityIssue]:
    """Return an issue when a GUI run cannot reach its required LLM."""
    llm_config = _object(models_config.get("llm"))
    provider = str(llm_config.get("provider") or "").lower().strip()
    model = str(llm_config.get("model") or "").strip()
    if not provider:
        return LLMQualityIssue(
            code="missing_provider",
            provider="",
            model=model,
        )
    if provider in DISALLOWED_LOCAL_STUB_PROVIDERS:
        return LLMQualityIssue(
            code="disabled_stub_provider",
            provider=provider,
            model=model,
        )
    if provider == "ollama":
        return _check_ollama(llm_config, provider=provider, model=model, timeout_seconds=timeout_seconds)
    if provider not in SUPPORTED_PROVIDERS:
        return LLMQualityIssue(
            code="unsupported_provider",
            provider=provider,
            model=model,
        )
    if provider in OPENAI_COMPATIBLE_PROVIDERS and not model:
        return LLMQualityIssue(
            code="missing_model",
            provider=provider,
            model=model,
        )
    return None


def _check_ollama(
    llm_config: Dict[str, Any],
    *,
    provider: str,
    model: str,
    timeout_seconds: float,
) -> Optional[LLMQualityIssue]:
    base_url = str(llm_config.get("base_url") or "http://localhost:11434").rstrip("/")
    url = "{0}/api/tags".format(base_url)
    request = Request(url, method="GET")
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            status = getattr(response, "status", 200)
            body = response.read().decode("utf-8")
    except HTTPError as exc:
        return LLMQualityIssue(
            code="ollama_http_error",
            provider=provider,
            model=model,
            detail="HTTP {0}: {1}".format(exc.code, str(exc.reason)),
        )
    except (OSError, TimeoutError, URLError) as exc:
        return LLMQualityIssue(
            code="ollama_unreachable",
            provider=provider,
            model=model,
            detail=str(exc),
        )

    if status < 200 or status >= 300:
        return LLMQualityIssue(
            code="ollama_http_error",
            provider=provider,
            model=model,
            detail="HTTP {0}".format(status),
        )
    if not model:
        return None

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return LLMQualityIssue(
            code="ollama_bad_response",
            provider=provider,
            model=model,
            detail="non-JSON /api/tags response",
        )
    available = {
        str(item.get("name") or item.get("model") or "").strip()
        for item in payload.get("models", [])
        if isinstance(item, dict)
    }
    if model and model not in available:
        sample = ", ".join(sorted(available)[:5])
        return LLMQualityIssue(
            code="ollama_model_missing",
            provider=provider,
            model=model,
            detail=sample,
        )
    return None


def _object(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}
