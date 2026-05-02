import unittest
from pathlib import Path

from meeting_ai.config.markdown_profile import load_markdown_profile
from meeting_ai.config.topic_details import apply_topic_details


class MarkdownProfileTest(unittest.TestCase):
    def test_loads_profile_sections(self):
        loaded = load_markdown_profile(Path("meeting_profile.md"))

        self.assertEqual(loaded["automation"]["videos_dir"], "videos")
        self.assertEqual(loaded["models_config"]["asr"]["model"], "large-v3")
        self.assertFalse(loaded["models_config"]["asr"]["condition_on_previous_text"])
        self.assertEqual(loaded["models_config"]["asr"]["no_speech_threshold"], 0.6)
        self.assertTrue(loaded["profile"]["required_search_items"])
        self.assertFalse(loaded["profile"]["custom_topics"])
        self.assertTrue(loaded["profile"]["verification_terms"])

        sections = {
            section["id"]: section["enabled"]
            for section in loaded["profile"]["output_sections"]
        }
        self.assertTrue(sections["key_topics"])
        self.assertFalse(sections["required_search_report"])
        self.assertFalse(sections["appendix"])

        rendering = loaded["pipeline_config"]["rendering"]
        self.assertTrue(rendering["include_timestamps"])
        self.assertTrue(rendering["include_evidence_snippets"])
        self.assertTrue(rendering["write_transcript_markdown"])
        self.assertTrue(rendering["write_evidence_report"])
        self.assertEqual(rendering["llm_summary_mode"], "fast")
        self.assertFalse(rendering["enable_critique"])

        keywords = loaded["pipeline_config"]["extraction"]["keywords"]
        self.assertIn("결정", keywords["decision"])
        self.assertIn("정리해 주세요", keywords["action"])
        self.assertIn("worth noting", [kw.lower() for kw in keywords["worth_noting"]])
        self.assertIn("?", keywords["question"])

    def test_topic_details_overlays_user_facing_topics(self):
        loaded = apply_topic_details(
            load_markdown_profile(Path("meeting_profile.md")),
            Path("topic_details.json"),
        )

        self.assertTrue(loaded["profile"]["custom_topics"])
        self.assertTrue(loaded["profile"]["topic_details"]["loaded"])
        self.assertIn(
            "date_time",
            {term["id"] for term in loaded["profile"]["verification_terms"]},
        )
        self.assertIn(
            "비주얼 피처와 텍스트 임베딩의 역할과 결론을 구분한다",
            {term["label"] for term in loaded["profile"]["verification_terms"]},
        )


if __name__ == "__main__":
    unittest.main()
