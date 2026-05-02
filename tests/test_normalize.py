import unittest

from meeting_ai.nodes.normalize import normalize_transcript


class NormalizeTranscriptTest(unittest.TestCase):
    def test_collapses_long_repeated_hallucination_runs(self):
        repeated_text = "그래서 지금 이 테스트를 통해서 질문하는 것에 대한 질문을 하고 있습니다."
        transcript = {
            "meeting_id": "m1",
            "duration_sec": 10,
            "segments": [
                {"id": "a", "start": 0, "end": 1, "text": "실제 발화입니다."},
                *[
                    {
                        "id": "r{0}".format(index),
                        "start": index,
                        "end": index + 1,
                        "text": repeated_text,
                    }
                    for index in range(1, 8)
                ],
            ],
        }

        normalized = normalize_transcript(transcript)

        self.assertEqual(
            [segment["text"] for segment in normalized["segments"]],
            ["실제 발화입니다.", repeated_text],
        )

    def test_keeps_short_backchannel_repetitions(self):
        transcript = {
            "meeting_id": "m1",
            "segments": [
                {"id": "n{0}".format(index), "start": index, "end": index + 1, "text": "네"}
                for index in range(5)
            ],
        }

        normalized = normalize_transcript(transcript)

        self.assertEqual(len(normalized["segments"]), 5)

    def test_drops_probable_silence_hallucination_from_asr_metrics(self):
        transcript = {
            "meeting_id": "m1",
            "segments": [
                {
                    "id": "bad",
                    "start": 0,
                    "end": 1,
                    "text": "무음 구간의 낮은 신뢰도 문장입니다.",
                    "no_speech_prob": 0.95,
                    "avg_logprob": -0.8,
                },
                {
                    "id": "good",
                    "start": 1,
                    "end": 2,
                    "text": "실제 발화입니다.",
                    "no_speech_prob": 0.1,
                    "avg_logprob": -0.1,
                },
            ],
        }

        normalized = normalize_transcript(transcript)

        self.assertEqual([segment["id"] for segment in normalized["segments"]], ["good"])


if __name__ == "__main__":
    unittest.main()
