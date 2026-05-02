"""Two-pass synthesizer over per-slot extracts.

Pass 1: Korean prose with thinking enabled (Re-FRAME pattern).
Pass 2: Strict JSON conversion with thinking off (we want a literal mapping).

The synthesis input is now a list of per-slot extract bundles produced by
:func:`meeting_ai.nodes.llm_extract.extract_per_slot`, not chunk-level
extracts. This restores meeting-wide narrative coherence that the v1
chunk-by-chunk pipeline was losing.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from meeting_ai.prompts import render_named
from meeting_ai.providers.llm.base import LLMError, LLMProvider
from meeting_ai.utils.time import format_duration


def _slot_definition_block(profile: Dict[str, Any]) -> str:
    rows: List[str] = []
    for item in profile.get("required_search_items", []):
        rows.append(
            "- {0} ({1}): {2}".format(
                item.get("id", "?"),
                item.get("label", "?"),
                item.get("description", ""),
            )
        )
    return "\n".join(rows) if rows else "(없음)"


def _custom_topics_block(profile: Dict[str, Any]) -> str:
    rows: List[str] = []
    for topic in profile.get("custom_topics", []):
        rows.append(
            "- {0}: {1}".format(topic.get("label", "?"), topic.get("description", ""))
        )
    return "\n".join(rows) if rows else "(없음)"


def _verification_terms_block(profile: Dict[str, Any]) -> str:
    rows: List[str] = []
    for term in profile.get("verification_terms", []):
        rows.append(
            "- {0}: aliases={1}; check={2}".format(
                term.get("label", "?"),
                ", ".join(term.get("aliases") or []),
                term.get("description", ""),
            )
        )
    return "\n".join(rows) if rows else "(없음)"


def _slot_titles(profile: Dict[str, Any]) -> str:
    titles = [item.get("label", "?") for item in profile.get("required_search_items", [])]
    return ", ".join(titles) if titles else "(없음)"


def _slot_extracts_jsonl(slot_extracts: List[Dict[str, Any]]) -> str:
    return "\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in slot_extracts)


def _final_summary_schema() -> Dict[str, Any]:
    """Subset schema for the synthesizer JSON pass."""
    item_evidence = {"type": "array", "items": {"type": "string"}}
    return {
        "type": "object",
        "required": ["tldr", "executive_summary"],
        "properties": {
            "tldr": {"type": "string"},
            "executive_summary": {"type": "string"},
            "key_topics": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "topic_id": {"type": "string"},
                        "title": {"type": "string"},
                        "summary": {"type": "string"},
                        "why_it_matters": {"type": "string"},
                        "supporting_points": {"type": "array", "items": {"type": "string"}},
                        "evidence_timestamps": item_evidence,
                        "source_chunks": {"type": "array", "items": {"type": "string"}},
                    },
                },
            },
            "decisions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "decision": {"type": "string"},
                        "rationale": {"type": "string"},
                        "evidence_timestamps": item_evidence,
                        "support": {"type": "string"},
                    },
                },
            },
            "action_items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "task": {"type": "string"},
                        "owner": {"type": "string"},
                        "deadline": {"type": "string"},
                        "priority": {"type": "string"},
                        "evidence_timestamps": item_evidence,
                        "support": {"type": "string"},
                    },
                },
            },
            "next_meeting": {
                "type": "object",
                "properties": {
                    "status": {"type": "string"},
                    "date": {"type": "string"},
                    "time": {"type": "string"},
                    "agenda": {"type": "array", "items": {"type": "string"}},
                    "preparation": {"type": "array", "items": {"type": "string"}},
                    "evidence_timestamps": item_evidence,
                    "support": {"type": "string"},
                },
            },
            "worth_noting": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "note": {"type": "string"},
                        "why_it_matters": {"type": "string"},
                        "related_topic": {"type": "string"},
                        "importance": {"type": "string"},
                        "evidence_timestamps": item_evidence,
                        "support": {"type": "string"},
                    },
                },
            },
            "open_questions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "question": {"type": "string"},
                        "context": {"type": "string"},
                        "evidence_timestamps": item_evidence,
                        "support": {"type": "string"},
                    },
                },
            },
        },
    }


def _parse_json_response(raw_text: str) -> Optional[Dict[str, Any]]:
    text = (raw_text or "").strip()
    if not text:
        return None
    if text.startswith("```"):
        text = text.strip("`")
        if "\n" in text:
            head, body = text.split("\n", 1)
            text = body if head.lower().startswith("json") else text
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if 0 <= start < end:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                return None
    return None


def synthesize_with_llm(
    transcript: Dict[str, Any],
    chunks: List[Dict[str, Any]],
    slot_extracts: List[Dict[str, Any]],
    required_search_report: List[Dict[str, Any]],
    profile: Dict[str, Any],
    rendering: Dict[str, Any],
    llm: LLMProvider,
    run_id: str,
    source_file: str,
    extraction_meta: Optional[Dict[str, Any]] = None,
    model_info: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    title = (
        transcript.get("title")
        or profile.get("meeting_profile", {}).get("default_title", "Zoom Meeting Summary")
    )
    meeting_duration = format_duration(float(transcript.get("duration_sec", 0.0)))
    meeting_id = str(transcript.get("meeting_id", run_id))
    output_language = profile.get("meeting_profile", {}).get("output_language", "ko")
    slot_blob = _slot_extracts_jsonl(slot_extracts)

    prose_prompt = render_named(
        "synthesize_prose",
        {
            "meeting_id": meeting_id,
            "meeting_title": title,
            "meeting_duration": meeting_duration,
            "output_language": output_language,
            "slot_titles": _slot_titles(profile),
            "slot_definitions": _slot_definition_block(profile),
            "custom_topics": _custom_topics_block(profile),
            "verification_terms": _verification_terms_block(profile),
            "slot_extracts": slot_blob,
        },
    )

    try:
        # Prose synthesis is creative writing over already-extracted facts.
        # Thinking traces here only burn tokens without improving quality, so
        # we explicitly turn it off and give the writer a generous budget.
        prose_response = llm.call(prose_prompt, max_tokens=3072, think=False)
    except LLMError as exc:
        raise LLMError("prose synthesis failed: {0}".format(exc)) from exc
    prose_text = (prose_response.text or "").strip()
    if not prose_text:
        raise LLMError("prose synthesis returned empty text")

    json_prompt = render_named(
        "synthesize_json",
        {
            "meeting_id": meeting_id,
            "meeting_title": title,
            "meeting_duration": meeting_duration,
            "source_file": source_file,
            "prose_summary": prose_text,
            "slot_extracts": slot_blob,
            "verification_terms": _verification_terms_block(profile),
            "worth_noting_max": int(rendering.get("worth_noting_max", 8)),
            "key_topics_max": int(rendering.get("key_topics_max", 8)),
        },
    )

    try:
        json_response = llm.call(
            json_prompt,
            max_tokens=4096,
            think=False,
            json_schema=_final_summary_schema(),
        )
    except LLMError as exc:
        raise LLMError("JSON synthesis failed: {0}".format(exc)) from exc
    parsed = _parse_json_response(json_response.text)
    if parsed is None:
        raise LLMError("JSON synthesis returned unparsable text")

    kept = sum(1 for bundle in slot_extracts if bundle.get("items"))

    final = {
        "meeting_id": meeting_id,
        "title": title,
        "date": parsed.get("date", "unknown"),
        "source_file": source_file,
        "duration": meeting_duration,
        "tldr": parsed.get("tldr", ""),
        "executive_summary": parsed.get("executive_summary", ""),
        "key_topics": parsed.get("key_topics", []) or [],
        "decisions": parsed.get("decisions", []) or [],
        "action_items": parsed.get("action_items", []) or [],
        "next_meeting": parsed.get("next_meeting") or {
            "status": "not_found",
            "date": "unknown",
            "time": "unknown",
            "agenda": [],
            "preparation": [],
            "evidence_timestamps": [],
            "support": "none",
        },
        "worth_noting": parsed.get("worth_noting", []) or [],
        "open_questions": parsed.get("open_questions", []) or [],
        "required_search_report": required_search_report,
        "metadata": {
            "model_info": model_info or {"provider": llm.name},
            "pipeline_version": "0.3.0",
            "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "chunk_count": len(chunks),
            "kept_slot_count": kept,
            "output_sections": profile.get("output_sections", []),
            "rendering": rendering,
            "synthesis": {
                "prose_chars": len(prose_text),
                "two_pass": True,
            },
            "extraction": extraction_meta or {},
        },
    }
    return final
