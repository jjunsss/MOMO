"""Tests for GUI copy that materially affects user inputs."""

from __future__ import annotations

import unittest

from meeting_ai.app.i18n import LANG_EN, LANG_KO, t
from meeting_ai.app.templates import by_key


class AppI18nTest(unittest.TestCase):
    def test_korean_must_check_guides_english_term_spelling(self) -> None:
        help_text = t("guide.must_check_help", LANG_KO)
        placeholder = t("guide.must_check_placeholder", LANG_KO)
        research_template = by_key("research").localized_must_check(LANG_KO)

        self.assertIn("기술명·논문명", help_text)
        self.assertIn("영어 원문 표기", placeholder)
        self.assertIn("Chain-of-Thought", placeholder)
        self.assertIn("기술명·논문명은 영어 원문 표기를 우선한다", research_template)

    def test_english_must_check_copy_stays_minimal(self) -> None:
        help_text = t("guide.must_check_help", LANG_EN)

        self.assertEqual(
            help_text,
            "One per line. Telling the AI in advance prevents common confusions.",
        )


if __name__ == "__main__":
    unittest.main()
