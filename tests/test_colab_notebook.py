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
        self.assertIn("torch.cuda.is_available", source)
        self.assertIn("ollama\", \"pull", source)
        self.assertIn("meeting_ai.cli", source)
        self.assertIn("files.upload", source)


if __name__ == "__main__":
    unittest.main()
