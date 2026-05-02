"""Default configuration values used by the MVP pipeline."""

from __future__ import annotations

from typing import Any, Dict, List


ASR_PRESETS: Dict[str, str] = {
    "fast": "small",
    "balanced": "medium",
    "best": "large-v3",
}


def default_extraction_keywords() -> Dict[str, List[str]]:
    return {
        "decision": [
            "결정", "하기로", "가기로", "확정", "채택", "decided", "decision",
        ],
        "uncertain_decision": [
            "결정해야", "결정을 좀 내봐야", "결정해야 될", "정해야",
            "확인 필요", "논의 필요",
        ],
        "action": [
            "해야 할 일", "액션 아이템", "해주세요", "해 주세요",
            "확인해 주세요", "정리해 주세요", "준비해 주세요",
            "공유해 주세요", "작성해 주세요", "보내주세요",
            "todo", "action item", "next step",
        ],
        "next_meeting": [
            "다음 미팅", "다음 회의", "다음 주", "follow-up", "next meeting",
        ],
        "worth_noting": [
            "중요", "참고", "리스크", "우려", "기억", "주의", "worth noting",
        ],
        "question": [
            "?", "질문", "확인 필요", "논의 필요", "open question",
        ],
    }


def default_required_search_items() -> List[Dict[str, Any]]:
    return [
        {
            "id": "next_meeting",
            "label": "다음 미팅",
            "required": True,
            "priority": "high",
            "aliases": ["다음 미팅", "다음 회의", "다음 주", "next meeting", "follow-up meeting"],
        },
        {
            "id": "action_items",
            "label": "해야 할 일",
            "required": True,
            "priority": "high",
            "aliases": [
                "해야 할 일",
                "액션 아이템",
                "todo",
                "action item",
                "next step",
                "확인해 주세요",
                "정리해 주세요",
                "준비해 주세요",
            ],
        },
        {
            "id": "worth_noting",
            "label": "Worth Noting",
            "required": True,
            "priority": "medium",
            "aliases": ["중요", "참고", "리스크", "우려", "기억", "worth noting"],
        },
    ]


def default_user_profile() -> Dict[str, Any]:
    return {
        "meeting_profile": {
            "default_title": "Zoom Meeting Summary",
            "output_language": "ko",
            "tone": "professional_research_notes",
        },
        "required_search_items": default_required_search_items(),
        "verification_terms": [],
        "output_sections": [],
    }


def default_pipeline_config() -> Dict[str, Any]:
    return {
        "chunking": {
            "target_minutes": 6,
            "max_minutes": 10,
            "overlap_seconds": 30,
        },
        "extraction": {
            "keywords": default_extraction_keywords(),
        },
        "verification": {
            "enabled": True,
            "evidence_window_seconds": 90,
        },
        "rendering": {
            "output_language": "ko",
            "include_timestamps": True,
            "include_evidence_snippets": True,
            "include_skipped_chunk_stats": True,
            "write_evidence_report": True,
            "write_transcript_markdown": True,
            "write_chunk_analysis_jsonl": True,
            "worth_noting_max": 8,
            "key_topics_max": 8,
            "max_per_slot_per_chunk": 3,
            "max_items_per_slot": 8,
            "single_pass_token_limit": 60_000,
            "direct_summary_max_tokens": 8192,
            "llm_summary_mode": "fast",
            "enable_critique": False,
        },
    }


def default_models_config() -> Dict[str, Any]:
    return {
        "asr": {
            "provider": "openai_whisper",
            "model": "large-v3",
            "language": "auto",
            "device": "auto",
            "fp16": True,
            "temperature": 0.0,
            "condition_on_previous_text": False,
            "no_speech_threshold": 0.6,
            "logprob_threshold": -1.0,
            "compression_ratio_threshold": 2.4,
            "diarization": False,
        },
        "llm": {
            "provider": "deterministic_mvp",
            "model": "rule_based",
            "temperature": 0.0,
            "structured_outputs": True,
        },
        "embedding": {"provider": "none", "model": "none"},
        "fallbacks": {"allow_cloud_llm": False, "allow_cloud_asr": False},
    }
