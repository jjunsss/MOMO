"""Tests for mandatory LLM behavior in the pipeline."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, Optional
from unittest.mock import patch

from meeting_ai.config.defaults import default_pipeline_config, default_user_profile
from meeting_ai.pipeline import process_transcript_source
from meeting_ai.providers.llm.base import LLMError, LLMResponse


class FailingLLMProvider:
    name = "failing_test_provider"

    def call(
        self,
        prompt: str,
        *,
        json_schema: Optional[Dict[str, Any]] = None,
        max_tokens: Optional[int] = None,
        think: Optional[bool] = None,
        system: Optional[str] = None,
    ) -> LLMResponse:
        raise LLMError("synthetic LLM failure")


class PipelineLLMRequiredTest(unittest.TestCase):
    def test_stub_provider_is_rejected_by_pipeline(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(LLMError, "rule-based LLM fallback is disabled"):
                process_transcript_source(
                    source_path=Path("tests/fixtures/sample_transcript.json"),
                    runs_dir=Path(tmp),
                    run_id="deterministic_rejected",
                    profile=default_user_profile(),
                    pipeline_config=default_pipeline_config(),
                    models_config={"llm": {"provider": "deterministic_mvp"}},
                )

    def test_llm_failure_raises_instead_of_falling_back(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with patch(
                "meeting_ai.pipeline.build_llm_provider",
                return_value=FailingLLMProvider(),
            ):
                with self.assertRaisesRegex(LLMError, "LLM synthesis failed"):
                    process_transcript_source(
                        source_path=Path("tests/fixtures/sample_transcript.json"),
                        runs_dir=Path(tmp),
                        run_id="llm_failure",
                        profile=default_user_profile(),
                        pipeline_config=default_pipeline_config(),
                        models_config={"llm": {"provider": "failing_test_provider"}},
                    )


if __name__ == "__main__":
    unittest.main()
