import unittest

from meeting_ai.renderers.evidence import (
    render_summary_evidence_markdown,
    strip_evidence_fields,
)
from meeting_ai.renderers.markdown import render_summary_markdown


class MarkdownRendererTest(unittest.TestCase):
    def test_final_markdown_hides_evidence_and_unknown_metadata(self) -> None:
        summary = {
            "title": "Test Meeting",
            "date": "unknown",
            "source_file": "video.mp4",
            "duration": "00:10:00",
            "tldr": "핵심 요약.",
            "executive_summary": "공유용 요약.",
            "key_topics": [
                {
                    "title": "토픽",
                    "summary": "요약",
                    "why_it_matters": "중요",
                    "evidence_timestamps": ["00:01:00"],
                }
            ],
            "decisions": [
                {
                    "decision": "결정",
                    "rationale": "맥락",
                    "support": "strong",
                    "evidence_timestamps": ["00:02:00"],
                }
            ],
            "action_items": [
                {
                    "task": "확인하기",
                    "owner": "unknown",
                    "deadline": "unknown",
                    "support": "strong",
                    "evidence_timestamps": ["00:03:00"],
                }
            ],
            "next_meeting": {
                "status": "found",
                "date": "2026-05-13",
                "time": "unknown",
                "agenda": ["데모"],
                "support": "strong",
                "evidence_timestamps": ["00:04:00"],
            },
            "worth_noting": [],
            "open_questions": [],
            "required_search_report": [
                {
                    "label": "다음 미팅",
                    "status": "found",
                    "summary": "다음 미팅 언급",
                    "evidence_timestamps": ["00:04:00"],
                    "evidence_snippets": [{"timestamp": "00:04:00", "text": "다음 미팅"}],
                }
            ],
            "metadata": {"pipeline_version": "test", "rendering": {}},
        }

        rendered = render_summary_markdown(summary)

        self.assertIn("확인하기", rendered)
        self.assertNotIn("owner: unknown", rendered)
        self.assertNotIn("deadline: unknown", rendered)
        self.assertNotIn("support:", rendered)
        self.assertNotIn("evidence:", rendered)
        self.assertNotIn("00:03:00", rendered)
        self.assertNotIn("근거 내용", rendered)

    def test_english_output_language_uses_english_markdown_chrome(self) -> None:
        summary = {
            "title": "Test Meeting",
            "date": "unknown",
            "source_file": "video.mp4",
            "duration": "00:10:00",
            "tldr": "A concise recap.",
            "executive_summary": "The meeting aligned on the next steps.",
            "key_topics": [],
            "decisions": [],
            "action_items": [],
            "next_meeting": {"status": "not_found"},
            "worth_noting": [],
            "open_questions": [],
            "required_search_report": [],
            "metadata": {
                "pipeline_version": "test",
                "rendering": {"output_language": "en"},
                "output_sections": [
                    {
                        "id": "executive_summary",
                        "title": "핵심 요약",
                        "enabled": True,
                    },
                    {"id": "key_topics", "title": "핵심 논의", "enabled": True},
                ],
            },
        }

        rendered = render_summary_markdown(summary)

        self.assertIn("## Executive Summary", rendered)
        self.assertIn("## Key Topics", rendered)
        self.assertIn("No clear key topics were detected.", rendered)
        self.assertNotIn("## 핵심 요약", rendered)
        self.assertNotIn("## 핵심 논의", rendered)
        self.assertNotIn("명확한 핵심 논의", rendered)

    def test_evidence_renderer_keeps_checkable_details(self) -> None:
        summary = {
            "title": "Test Meeting",
            "source_file": "video.mp4",
            "duration": "00:10:00",
            "key_topics": [],
            "decisions": [
                {
                    "decision": "결정",
                    "rationale": "맥락",
                    "support": "strong",
                    "evidence_timestamps": ["00:02:00"],
                }
            ],
            "action_items": [],
            "next_meeting": {},
            "worth_noting": [],
            "open_questions": [],
            "required_search_report": [],
            "metadata": {"pipeline_version": "test"},
        }
        transcript = {
            "segments": [
                {"start": 120, "text": "결정을 내렸습니다."},
            ]
        }

        rendered = render_summary_evidence_markdown(summary, transcript)

        self.assertIn("00:02:00", rendered)
        self.assertIn("strong", rendered)
        self.assertIn("결정을 내렸습니다.", rendered)

    def test_strip_evidence_fields_for_public_json(self) -> None:
        public = strip_evidence_fields(
            {
                "action_items": [
                    {
                        "task": "확인하기",
                        "support": "strong",
                        "evidence_timestamps": ["00:01:00"],
                    }
                ],
                "required_search_report": [
                    {
                        "status": "found",
                        "evidence_snippets": [{"text": "근거"}],
                    }
                ],
            }
        )

        self.assertNotIn("support", public["action_items"][0])
        self.assertNotIn("evidence_timestamps", public["action_items"][0])
        self.assertNotIn("evidence_snippets", public["required_search_report"][0])


if __name__ == "__main__":
    unittest.main()
