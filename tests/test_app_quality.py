"""Tests for GUI LLM readiness checks."""

from __future__ import annotations

import json
import unittest
from io import BytesIO
from unittest.mock import patch

from meeting_ai.app.quality import check_llm_ready


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


class AppQualityTest(unittest.TestCase):
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
