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
        self.assertIn("Visual guide / 화면 안내", source)
        self.assertIn("colab-01-runtime-menu.svg", source)
        self.assertIn("colab-04-run-cells-upload.svg", source)
        self.assertIn("10분 이상 걸려도 더 좋은 품질", source)
        self.assertIn("For higher quality, if a 10+ minute", source)
        self.assertIn("따옴표 안의 글자만 바꾸면 됩니다", source)
        self.assertIn("The most important field is `custom_instruction`", source)
        self.assertIn("torch.cuda.is_available", source)
        self.assertIn('ASR_MODEL = "medium"', source)
        self.assertIn('LLM_NUM_CTX = "8192"', source)
        self.assertIn('TORCH_INDEX_URL = "https://download.pytorch.org/whl/cu124"', source)
        self.assertIn('"torch", "torchaudio", "--index-url", TORCH_INDEX_URL', source)
        self.assertNotIn("https://ollama.com/install.sh | sh", source)
        self.assertIn("install_ollama_user_local", source)
        self.assertIn("ollama-linux-amd64.tar.zst", source)
        self.assertIn("zstandard", source)
        self.assertIn('SUMMARY_MODE = "fast"', source)
        self.assertIn('ENABLE_CRITIQUE = "false"', source)
        self.assertIn('ollama_cmd, "pull"', source)
        self.assertIn("meeting_ai.cli", source)
        self.assertIn("files.upload", source)

    def test_colab_docs_explain_meeting_focus_fields(self) -> None:
        guide = Path("docs/COLAB.md").read_text(encoding="utf-8")

        self.assertIn("## Meeting focus", guide)
        self.assertIn("custom_instruction", guide)
        self.assertIn("Most important", guide)
        self.assertIn("must_check", guide)
        self.assertIn("English technical names", guide)

    def test_colab_visual_guide_assets_are_documented(self) -> None:
        guide = Path("docs/COLAB.md").read_text(encoding="utf-8")
        for filename in [
            "colab-01-runtime-menu.svg",
            "colab-02-change-runtime-type.svg",
            "colab-03-select-gpu-save.svg",
            "colab-04-run-cells-upload.svg",
        ]:
            self.assertIn(filename, guide)
            path = Path("docs/screenshots") / filename
            self.assertTrue(path.exists())
            self.assertIn("<svg", path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
