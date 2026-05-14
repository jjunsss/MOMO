"""Tests for the LLM synthesis path using a canned LLM provider."""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from typing import Any, Dict, Optional

from meeting_ai.config.markdown_profile import load_markdown_profile
from meeting_ai.config.topic_details import apply_topic_details
from meeting_ai.nodes.analyze_chunk import analyze_chunks
from meeting_ai.nodes.chunk import build_chunks
from meeting_ai.nodes.llm_direct_synthesize import synthesize_direct_with_llm
from meeting_ai.nodes.llm_extract import extract_per_slot
from meeting_ai.nodes.llm_synthesize import synthesize_with_llm
from meeting_ai.nodes.normalize import normalize_transcript
from meeting_ai.nodes.required_search import build_required_search_report
from meeting_ai.nodes.verify import verify_summary
from meeting_ai.providers.llm.base import LLMResponse
from meeting_ai.providers.llm.factory import build_llm_provider
from meeting_ai.schemas.summary import validate_final_summary
from meeting_ai.utils.io import read_json


class StubLLMProvider:
    """Returns canned JSON for slot extraction and synthesis prompts."""

    name = "stub_test"

    def __init__(self) -> None:
        self.calls = []

    def call(
        self,
        prompt: str,
        *,
        json_schema: Optional[Dict[str, Any]] = None,
        max_tokens: Optional[int] = None,
        think: Optional[bool] = None,
        system: Optional[str] = None,
    ) -> LLMResponse:
        self.calls.append(prompt[:80])

        # Per-slot single-pass extraction prompt
        if "단 하나의 슬롯에 해당하는 사실만" in prompt:
            payload = {
                "items": [
                    {
                        "summary": "샘플 슬롯 추출 결과",
                        "importance": 4,
                        "owner": "unknown",
                        "deadline": "unknown",
                        "date": "unknown",
                        "time": "unknown",
                        "evidence_timestamps": ["00:02:00"],
                        "evidence_quote": "stub evidence",
                    }
                ]
            }
            return LLMResponse(text=json.dumps(payload, ensure_ascii=False), raw={"stub": True})

        # Prose synthesis prompt
        if "다음 6개 H2 섹션" in prompt:
            return LLMResponse(text="## TL;DR\n샘플 회의 요약입니다.", raw={"stub": True})

        # JSON synthesis prompt
        if "strict JSON으로 변환" in prompt or "one-pass fast mode" in prompt:
            payload = {
                "tldr": "샘플 회의에서 파이프라인 범위와 후속 작업이 정리되었습니다.",
                "executive_summary": "transcript JSON -> chunk analysis -> final summary -> Markdown 흐름을 확정했고, 16GB GPU 제약을 인지했습니다.",
                "key_topics": [
                    {
                        "topic_id": "t01",
                        "title": "파이프라인 범위 확정",
                        "summary": "transcript JSON 단계부터 Markdown 렌더까지의 단계가 합의됨.",
                        "why_it_matters": "산출물 계약 기준이 됨.",
                        "supporting_points": ["chunk analysis JSONL 도입"],
                        "evidence_timestamps": ["00:01:30"],
                        "source_chunks": ["c0001"],
                    }
                ],
                "decisions": [
                    {
                        "decision": "transcript JSON에서 chunk analysis JSONL을 만든 뒤 final summary JSON을 거쳐 Markdown을 렌더링",
                        "rationale": "재현성과 단계별 검증",
                        "evidence_timestamps": ["00:01:30"],
                        "support": "strong",
                    }
                ],
                "action_items": [
                    {
                        "task": "config 모델 설정 분리 + required search report 보존",
                        "owner": "unknown",
                        "deadline": "unknown",
                        "priority": "high",
                        "evidence_timestamps": ["00:02:00"],
                        "support": "strong",
                    }
                ],
                "next_meeting": {
                    "status": "found",
                    "date": "unknown",
                    "time": "unknown",
                    "agenda": ["실제 Zoom 파일 처리", "ASR provider 결합"],
                    "preparation": [],
                    "evidence_timestamps": ["00:05:00"],
                    "support": "strong",
                },
                "worth_noting": [
                    {
                        "note": "16GB GPU에서 ASR + LLM 동시 로딩은 메모리 리스크",
                        "why_it_matters": "OOM 또는 처리 지연을 유발할 수 있음",
                        "related_topic": "리소스",
                        "importance": "high",
                        "evidence_timestamps": ["00:03:30"],
                        "support": "strong",
                    }
                ],
                "open_questions": [],
            }
            return LLMResponse(text=json.dumps(payload, ensure_ascii=False), raw={"stub": True})

        return LLMResponse(text="", raw={"stub": True})


class LLMSynthesisTest(unittest.TestCase):
    def setUp(self) -> None:
        loaded = apply_topic_details(
            load_markdown_profile(Path("meeting_profile.md")),
            Path("topic_details.json"),
        )
        self.profile = loaded["profile"]
        self.pipeline_config = loaded["pipeline_config"]
        self.transcript = normalize_transcript(read_json(Path("tests/fixtures/sample_transcript.json")))
        self.chunks = build_chunks(self.transcript, self.pipeline_config["chunking"])
        self.analyses = analyze_chunks(
            self.chunks,
            self.profile["required_search_items"],
            keywords=self.pipeline_config["extraction"]["keywords"],
        )
        self.required_report = build_required_search_report(
            required_items=self.profile["required_search_items"],
            transcript=self.transcript,
            chunk_analyses=self.analyses,
        )

    def test_factory_rejects_disabled_stub_provider(self) -> None:
        with self.assertRaisesRegex(ValueError, "rule-based LLM fallback is disabled"):
            build_llm_provider({"provider": "deterministic_mvp"})

    def test_factory_rejects_unknown_provider(self) -> None:
        with self.assertRaises(ValueError):
            build_llm_provider({"provider": "made_up_provider"})

    def test_extract_per_slot_calls_llm_once_per_slot(self) -> None:
        stub = StubLLMProvider()
        slot_extracts, meta = extract_per_slot(
            transcript=self.transcript,
            chunks=self.chunks,
            profile=self.profile,
            llm=stub,
            meeting_id=self.transcript["meeting_id"],
        )
        self.assertEqual(meta["strategy"], "single_pass")
        # one call per slot defined in the profile (required + custom topics)
        expected_slot_count = len(self.profile["required_search_items"]) + len(
            self.profile.get("custom_topics", [])
        )
        self.assertEqual(len(slot_extracts), expected_slot_count)
        for bundle in slot_extracts:
            self.assertEqual(bundle["method"], "single_pass")
            self.assertTrue(bundle["items"])  # stub always returns one
        self.assertGreaterEqual(len(stub.calls), expected_slot_count)

    def test_two_pass_synthesis_produces_validated_summary(self) -> None:
        stub = StubLLMProvider()
        slot_extracts, meta = extract_per_slot(
            transcript=self.transcript,
            chunks=self.chunks,
            profile=self.profile,
            llm=stub,
            meeting_id=self.transcript["meeting_id"],
        )
        draft = synthesize_with_llm(
            transcript=self.transcript,
            chunks=self.chunks,
            slot_extracts=slot_extracts,
            required_search_report=self.required_report,
            profile=self.profile,
            rendering=self.pipeline_config["rendering"],
            llm=stub,
            run_id="stub_run",
            source_file="sample_zoom.mp4",
            extraction_meta=meta,
        )
        _, final = verify_summary(draft)
        validate_final_summary(final)
        self.assertEqual(final["next_meeting"]["status"], "found")
        self.assertEqual(final["metadata"]["synthesis"]["two_pass"], True)
        self.assertEqual(final["metadata"]["extraction"]["strategy"], "single_pass")
        self.assertGreaterEqual(len(final["action_items"]), 1)
        self.assertLessEqual(
            len(final["worth_noting"]),
            self.pipeline_config["rendering"]["worth_noting_max"],
        )

    def test_direct_synthesis_uses_one_llm_call(self) -> None:
        stub = StubLLMProvider()

        draft = synthesize_direct_with_llm(
            transcript=self.transcript,
            chunks=self.chunks,
            required_search_report=self.required_report,
            profile=self.profile,
            rendering=self.pipeline_config["rendering"],
            llm=stub,
            run_id="stub_run",
            source_file="sample_zoom.mp4",
            chunk_analyses=self.analyses,
        )
        _, final = verify_summary(draft)
        validate_final_summary(final)

        self.assertEqual(len(stub.calls), 1)
        self.assertEqual(final["metadata"]["synthesis"]["mode"], "fast_direct_json")
        self.assertTrue(final["metadata"]["synthesis"]["uses_salience_map"])
        self.assertEqual(
            final["metadata"]["extraction"]["strategy"],
            "deterministic_salience_map",
        )
        self.assertFalse(final["metadata"]["synthesis"]["two_pass"])

    def test_direct_synthesis_repairs_day_as_time_confusion(self) -> None:
        class DayAsTimeStub(StubLLMProvider):
            def call(self, *args: Any, **kwargs: Any) -> LLMResponse:
                response = super().call(*args, **kwargs)
                payload = json.loads(response.text)
                payload["next_meeting"] = {
                    "status": "found",
                    "date": "13일",
                    "time": "13:00",
                    "agenda": [],
                    "preparation": [],
                    "evidence_timestamps": ["00:57:49"],
                    "support": "strong",
                }
                return LLMResponse(text=json.dumps(payload, ensure_ascii=False), raw={"stub": True})

        transcript = {
            **self.transcript,
            "segments": [
                *self.transcript["segments"],
                {
                    "id": "t999999",
                    "start": 3469,
                    "end": 3472,
                    "text": "13일은 똑같은 시간이 될 것 같습니다.",
                },
            ],
        }
        stub = DayAsTimeStub()

        draft = synthesize_direct_with_llm(
            transcript=transcript,
            chunks=self.chunks,
            required_search_report=self.required_report,
            profile=self.profile,
            rendering=self.pipeline_config["rendering"],
            llm=stub,
            run_id="stub_run",
            source_file="Screen_Recording_20260429_172841_Zoom.mp4",
            chunk_analyses=self.analyses,
        )

        self.assertEqual(draft["next_meeting"]["date"], "2026-05-13")
        self.assertEqual(draft["next_meeting"]["time"], "unknown")


if __name__ == "__main__":
    unittest.main()
