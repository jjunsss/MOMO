"""LLM readiness checks for GUI-triggered runs."""

from __future__ import annotations

import json
from dataclasses import dataclass
from importlib import import_module
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


@dataclass(frozen=True)
class GPUStatus:
    """CUDA visibility state shown in the GUI before a run starts."""

    ok: bool
    code: str
    name: str = ""
    detail: str = ""
    device_count: int = 0


def check_gpu_status() -> GPUStatus:
    """Return whether PyTorch can see a CUDA GPU for ASR/LLM runs."""
    try:
        torch = import_module("torch")
    except ImportError as exc:
        return GPUStatus(
            ok=False,
            code="torch_missing",
            detail=str(exc) or "PyTorch is not installed",
        )

    cuda = getattr(torch, "cuda", None)
    if cuda is None:
        return GPUStatus(
            ok=False,
            code="cuda_module_missing",
            detail="torch.cuda is not available",
        )

    try:
        available = bool(cuda.is_available())
    except Exception as exc:  # pragma: no cover - defensive for broken torch installs
        return GPUStatus(
            ok=False,
            code="cuda_check_failed",
            detail=str(exc),
        )

    try:
        device_count = int(cuda.device_count())
    except Exception:  # pragma: no cover - device_count should be cheap and stable
        device_count = 0

    if not available:
        return GPUStatus(
            ok=False,
            code="cuda_unavailable",
            detail="torch.cuda.is_available() returned false",
            device_count=device_count,
        )

    try:
        name = str(cuda.get_device_name(0))
    except Exception:  # pragma: no cover - rare driver/runtime edge case
        name = "CUDA device"
    return GPUStatus(
        ok=True,
        code="cuda_available",
        name=name,
        device_count=max(device_count, 1),
    )


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
