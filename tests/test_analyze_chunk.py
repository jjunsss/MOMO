import unittest

from meeting_ai.nodes.analyze_chunk import analyze_chunk


class AnalyzeChunkTest(unittest.TestCase):
    def test_uncertain_decision_is_not_final_decision(self):
        chunk = {
            "chunk_id": "c0001",
            "start": 0,
            "end": 10,
            "text": "이건 어떤 식으로 다듬을지 결정을 좀 내봐야 될 것 같습니다.",
            "segments": [
                {
                    "id": "t1",
                    "start": 0,
                    "end": 10,
                    "text": "이건 어떤 식으로 다듬을지 결정을 좀 내봐야 될 것 같습니다.",
                }
            ],
        }

        analysis = analyze_chunk(chunk, [])

        self.assertEqual(analysis["decisions"], [])
        self.assertEqual(len(analysis["open_questions"]), 1)

    def test_multiple_actions_in_one_chunk_are_kept(self):
        chunk = {
            "chunk_id": "c0002",
            "start": 0,
            "end": 30,
            "text": "다음 주까지 정리해 주세요. 결과는 보내주세요.",
            "segments": [
                {"id": "t1", "start": 0, "end": 10, "text": "다음 주까지 정리해 주세요."},
                {"id": "t2", "start": 12, "end": 20, "text": "결과는 보내주세요."},
            ],
        }

        analysis = analyze_chunk(chunk, [])

        tasks = sorted(item["task"] for item in analysis["action_items"])
        self.assertEqual(len(tasks), 2)
        self.assertTrue(any("정리해 주세요" in task for task in tasks))
        self.assertTrue(any("보내주세요" in task for task in tasks))

    def test_custom_keyword_override(self):
        chunk = {
            "chunk_id": "c0003",
            "start": 0,
            "end": 10,
            "text": "예산 승인 부탁드립니다.",
            "segments": [
                {"id": "t1", "start": 0, "end": 10, "text": "예산 승인 부탁드립니다."},
            ],
        }
        keywords = {"action": ["부탁드립니다"]}

        analysis = analyze_chunk(chunk, [], keywords=keywords)

        self.assertEqual(len(analysis["action_items"]), 1)
        self.assertIn("부탁드립니다", analysis["action_items"][0]["task"])


if __name__ == "__main__":
    unittest.main()

