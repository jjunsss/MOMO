"""Tests for GUI LLM readiness checks."""

from __future__ import annotations

import json
import unittest
from io import BytesIO
from unittest.mock import patch

from meeting_ai.app.quality import check_gpu_status, check_llm_ready


class _FakeResponse:
    status = 200

    def __init__(self, payload: dict) -> None:
        self._body = json.dumps(payload).encode("utf-8")

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return BytesIO(self._body).read()


class _FakeCuda:
    def __init__(self, available: bool, name: str = "RTX Test") -> None:
        self._available = available
        self._name = name

    def is_available(self) -> bool:
        return self._available

    def device_count(self) -> int:
        return 1 if self._available else 0

    def get_device_name(self, index: int) -> str:
        return self._name


class _FakeTorch:
    def __init__(self, cuda: _FakeCuda) -> None:
        self.cuda = cuda


class AppQualityTest(unittest.TestCase):
    def test_gpu_status_reports_on_when_cuda_visible(self) -> None:
        with patch(
            "meeting_ai.app.quality.import_module",
            return_value=_FakeTorch(_FakeCuda(True, "NVIDIA Test GPU")),
        ):
            status = check_gpu_status()

        self.assertTrue(status.ok)
        self.assertEqual(status.code, "cuda_available")
        self.assertEqual(status.name, "NVIDIA Test GPU")

    def test_gpu_status_reports_off_when_cuda_missing(self) -> None:
        with patch(
            "meeting_ai.app.quality.import_module",
            return_value=_FakeTorch(_FakeCuda(False)),
        ):
            status = check_gpu_status()

        self.assertFalse(status.ok)
        self.assertEqual(status.code, "cuda_unavailable")

    def test_gpu_status_reports_off_when_torch_missing(self) -> None:
        with patch(
            "meeting_ai.app.quality.import_module",
            side_effect=ImportError("no torch"),
        ):
            status = check_gpu_status()

        self.assertFalse(status.ok)
        self.assertEqual(status.code, "torch_missing")

    def test_missing_provider_is_reported(self) -> None:
        issue = check_llm_ready({"llm": {"model": "qwen3.5:9b"}})

        self.assertIsNotNone(issue)
        self.assertEqual(issue.code, "missing_provider")

    def test_stub_provider_is_blocked_when_llm_required(self) -> None:
        issue = check_llm_ready(
            {"llm": {"provider": "deterministic_mvp", "model": "rule_based"}},
        )

        self.assertIsNotNone(issue)
        self.assertEqual(issue.code, "disabled_stub_provider")

    def test_ollama_model_missing_is_reported(self) -> None:
        with patch(
            "meeting_ai.app.quality.urlopen",
            return_value=_FakeResponse({"models": [{"name": "other-model"}]}),
        ):
            issue = check_llm_ready(
                {
                    "llm": {
                        "provider": "ollama",
                        "model": "qwen3.5:9b",
                        "base_url": "http://localhost:11434",
                    }
                },
            )

        self.assertIsNotNone(issue)
        self.assertEqual(issue.code, "ollama_model_missing")

    def test_ollama_empty_model_list_is_reported(self) -> None:
        with patch(
            "meeting_ai.app.quality.urlopen",
            return_value=_FakeResponse({"models": []}),
        ):
            issue = check_llm_ready(
                {
                    "llm": {
                        "provider": "ollama",
                        "model": "qwen3.5:9b",
                        "base_url": "http://localhost:11434",
                    }
                },
            )

        self.assertIsNotNone(issue)
        self.assertEqual(issue.code, "ollama_model_missing")

    def test_unknown_provider_is_reported(self) -> None:
        issue = check_llm_ready(
            {"llm": {"provider": "made_up_provider", "model": "some-model"}},
        )

        self.assertIsNotNone(issue)
        self.assertEqual(issue.code, "unsupported_provider")

    def test_openai_compatible_requires_model_name(self) -> None:
        issue = check_llm_ready({"llm": {"provider": "openai_compatible"}})

        self.assertIsNotNone(issue)
        self.assertEqual(issue.code, "missing_model")


if __name__ == "__main__":
    unittest.main()
