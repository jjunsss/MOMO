import unittest
from pathlib import Path
from unittest.mock import patch

from meeting_ai.cli import _load_yaml_runtime


class CLIRuntimeTest(unittest.TestCase):
    def test_yaml_runtime_applies_environment_overrides(self) -> None:
        with patch.dict(
            "os.environ",
            {
                "MOMO_LLM_BASE_URL": "http://remote-ollama:11434",
                "MOMO_LLM_MODEL": "qwen3.5:9b",
                "MOMO_ASR_DEVICE": "cuda",
                "MOMO_OUTPUT_LANGUAGE": "en",
            },
        ):
            loaded = _load_yaml_runtime(
                Path("config/user_profile.example.yaml"),
                Path("config/pipeline.yaml"),
                Path("config/models.yaml"),
            )

        self.assertEqual(
            loaded["models_config"]["llm"]["base_url"],
            "http://remote-ollama:11434",
        )
        self.assertEqual(loaded["models_config"]["llm"]["model"], "qwen3.5:9b")
        self.assertEqual(loaded["models_config"]["asr"]["device"], "cuda")
        self.assertEqual(
            loaded["profile"]["meeting_profile"]["output_language"],
            "en",
        )
        self.assertEqual(
            loaded["pipeline_config"]["rendering"]["output_language"],
            "en",
        )


if __name__ == "__main__":
    unittest.main()
