import unittest

from meeting_ai.config.defaults import default_required_search_items
from meeting_ai.nodes.analyze_chunk import analyze_chunks
from meeting_ai.nodes.chunk import build_chunks
from meeting_ai.nodes.normalize import normalize_transcript
from meeting_ai.nodes.required_search import build_required_search_report


class RequiredSearchTest(unittest.TestCase):
    def test_required_search_reports_found_and_not_found(self):
        transcript = normalize_transcript(
            {
                "meeting_id": "test",
                "duration_sec": 20,
                "segments": [
                    {"id": "t1", "start": 0, "end": 10, "text": "다음 미팅에서 다시 확인해 주세요."}
                ],
            }
        )
        required_items = default_required_search_items() + [
            {"id": "budget", "label": "Budget", "aliases": ["budget"], "required": True}
        ]
        chunks = build_chunks(transcript, {"target_minutes": 6, "max_minutes": 10, "overlap_seconds": 30})
        analyses = analyze_chunks(chunks, required_items)
        report = build_required_search_report(required_items, transcript, analyses)

        statuses = {item["required_item_id"]: item["status"] for item in report}
        self.assertEqual(statuses["next_meeting"], "found")
        self.assertEqual(statuses["action_items"], "found")
        self.assertEqual(statuses["budget"], "not_found")


if __name__ == "__main__":
    unittest.main()
