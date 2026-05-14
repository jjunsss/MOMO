import json
import unittest
from pathlib import Path


class ColabNotebookTest(unittest.TestCase):
    def test_notebook_is_valid_and_contains_trial_flow(self) -> None:
        notebook_path = Path("notebooks/MOMO_Colab.ipynb")
        notebook = json.loads(notebook_path.read_text(encoding="utf-8"))

        self.assertEqual(notebook["nbformat"], 4)
        source = "\n".join(
            line
            for cell in notebook["cells"]
            for line in cell.get("source", [])
        )

        self.assertIn("MOMO Colab Quick Trial", source)
        self.assertIn("초보자 / Beginner", source)
        self.assertIn("셀을 위에서 아래로 하나씩 실행하세요", source)
        self.assertIn("Run each cell one by one from top to bottom", source)
        self.assertIn("GPU 확인", source)
        self.assertIn("GPU check", source)
        self.assertIn("torch.cuda.is_available", source)
        self.assertIn('ASR_MODEL = "medium"', source)
        self.assertIn('LLM_NUM_CTX = "8192"', source)
        self.assertIn('TORCH_INDEX_URL = "https://download.pytorch.org/whl/cu124"', source)
        self.assertIn('"torch", "torchaudio", "--index-url", TORCH_INDEX_URL', source)
        self.assertIn('SUMMARY_MODE = "fast"', source)
        self.assertIn('ENABLE_CRITIQUE = "false"', source)
        self.assertIn("ollama\", \"pull", source)
        self.assertIn("meeting_ai.cli", source)
        self.assertIn("files.upload", source)


if __name__ == "__main__":
    unittest.main()
