"""Fast one-call LLM synthesizer over the full transcript."""

from __future__ import annotations

import json
import re
from datetime import date
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from meeting_ai.prompts import render_named
from meeting_ai.providers.llm.base import LLMError, LLMProvider
from meeting_ai.utils.time import format_duration, format_seconds


def _format_transcript(transcript: Dict[str, Any]) -> str:
    lines: List[str] = []
    for segment in transcript.get("segments", []):
        ts = format_seconds(float(segment.get("start", 0.0)))
        lines.append("[{0} | {1}] {2}".format(segment.get("id", "?"), ts, segment.get("text", "")))
    return "\n".join(lines)


def _required_items_block(profile: Dict[str, Any]) -> str:
    rows = []
    for item in profile.get("required_search_items", []):
        rows.append(
            "- {0} ({1}): aliases={2}; description={3}".format(
                item.get("id", "?"),
                item.get("label", "?"),
                ", ".join(item.get("aliases") or []),
                item.get("description", ""),
            )
        )
    return "\n".join(rows) if rows else "(없음)"


def _custom_topics_block(profile: Dict[str, Any]) -> str:
    rows = []
    for topic in profile.get("custom_topics", []):
        rows.append(
            "- {0} ({1}): aliases={2}; description={3}".format(
                topic.get("id", "?"),
                topic.get("label", "?"),
                ", ".join(topic.get("aliases") or []),
                topic.get("description", ""),
            )
        )
    return "\n".join(rows) if rows else "(없음)"


def _verification_terms_block(profile: Dict[str, Any]) -> str:
    rows = []
    for term in profile.get("verification_terms", []):
        rows.append(
            "- {0} ({1}): aliases={2}; check={3}".format(
                term.get("id", "?"),
                term.get("label", "?"),
                ", ".join(term.get("aliases") or []),
                term.get("description", ""),
            )
        )
    return "\n".join(rows) if rows else "(없음)"


def _required_report_json(required_search_report: List[Dict[str, Any]]) -> str:
    return json.dumps(required_search_report, ensure_ascii=False, sort_keys=True)


def _salience_map_jsonl(
    chunks: List[Dict[str, Any]], chunk_analyses: Optional[List[Dict[str, Any]]]
) -> str:
    if not chunk_analyses:
        return "(없음)"
    chunk_by_id = {chunk.get("chunk_id"): chunk for chunk in chunks}
    rows: List[str] = []
    for analysis in chunk_analyses:
        chunk_id = analysis.get("chunk_id", "?")
        chunk = chunk_by_id.get(chunk_id, {})
        row = {
            "chunk_id": chunk_id,
            "time_range": "{0}-{1}".format(
                format_seconds(float(chunk.get("start", 0.0))),
                format_seconds(float(chunk.get("end", 0.0))),
            ),
            "classification": analysis.get("classification", "unknown"),
            "salience_score": analysis.get("salience_score", 0),
            "skip_reason": analysis.get("skip_reason", ""),
            "key_points": _compact_items(analysis.get("key_points", []), "text", 4),
            "decisions": _compact_items(analysis.get("decisions", []), "decision", 3),
            "actions": _compact_items(analysis.get("action_items", []), "task", 3),
            "next_meeting": _compact_items(
                analysis.get("next_meeting_mentions", []), "summary", 3
            ),
            "worth_noting": _compact_items(
                analysis.get("worth_noting_candidates", []), "note", 3
            ),
            "required_hits": [
                {
                    "id": hit.get("required_item_id"),
                    "label": hit.get("label"),
                    "evidence": hit.get("evidence_timestamps", []),
                }
                for hit in (analysis.get("required_search_hits", []) or [])[:5]
            ],
        }
        rows.append(json.dumps(row, ensure_ascii=False, sort_keys=True))
    return "\n".join(rows)


def _compact_items(items: Any, text_key: str, limit: int) -> List[Dict[str, Any]]:
    compact: List[Dict[str, Any]] = []
    if not isinstance(items, list):
        return compact
    for item in items[:limit]:
        if not isinstance(item, dict):
            continue
        text = str(item.get(text_key) or item.get("summary") or item.get("text") or "").strip()
        if not text:
            continue
        compact.append(
            {
                "text": text[:240],
                "evidence": item.get("evidence_timestamps", []),
                "support": item.get("support") or item.get("uncertainty") or "",
            }
        )
    return compact


def _summary_schema() -> Dict[str, Any]:
    evidence = {"type": "array", "items": {"type": "string"}}
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
                        "evidence_timestamps": evidence,
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
                        "evidence_timestamps": evidence,
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
                        "evidence_timestamps": evidence,
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
                    "evidence_timestamps": evidence,
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
                        "evidence_timestamps": evidence,
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
                        "evidence_timestamps": evidence,
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


def _evidence_text(transcript: Dict[str, Any], timestamps: List[str], window: int = 8) -> str:
    targets = set()
    for timestamp in timestamps:
        try:
            h, m, s = (int(part) for part in str(timestamp).split(":"))
        except ValueError:
            continue
        targets.add(h * 3600 + m * 60 + s)
    if not targets:
        return ""
    lines: List[str] = []
    for segment in transcript.get("segments", []):
        start = float(segment.get("start", 0.0))
        if any(abs(start - target) <= window for target in targets):
            lines.append(str(segment.get("text", "")))
    return " ".join(lines)


def _repair_next_meeting_date(
    summary: Dict[str, Any], transcript: Dict[str, Any], source_file: str
) -> None:
    next_meeting = summary.get("next_meeting")
    if not isinstance(next_meeting, dict) or next_meeting.get("status") != "found":
        return
    date_value = str(next_meeting.get("date") or "unknown").strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", date_value):
        return
    evidence = _evidence_text(transcript, next_meeting.get("evidence_timestamps") or [], window=14)
    day_matches = [int(match) for match in re.findall(r"(\d{1,2})\s*일", evidence)]
    if not day_matches:
        return
    day = day_matches[-1]
    base_date = _source_date(source_file)
    month_matches = [int(match) for match in re.findall(r"(\d{1,2})\s*월", evidence)]
    if month_matches and base_date:
        month = month_matches[-1]
        year = base_date.year
        if month < base_date.month:
            year += 1
    elif base_date:
        year, month = _next_month_for_day(base_date, day)
    else:
        next_meeting["date"] = "{0}일".format(day)
        return
    try:
        repaired = date(year, month, day)
    except ValueError:
        return
    next_meeting["date"] = repaired.isoformat()


def _repair_next_meeting_time(summary: Dict[str, Any], transcript: Dict[str, Any]) -> None:
    next_meeting = summary.get("next_meeting")
    if not isinstance(next_meeting, dict) or next_meeting.get("status") != "found":
        return
    time_value = str(next_meeting.get("time") or "unknown").strip()
    if time_value in {"", "unknown"}:
        next_meeting["time"] = "unknown"
        return
    evidence = _evidence_text(transcript, next_meeting.get("evidence_timestamps") or [])
    has_explicit_time = bool(
        re.search(r"(\d{1,2}\s*시|\d{1,2}\s*:\s*\d{2}|오전|오후|한\s*시|두\s*시)", evidence)
    )
    has_date_day = bool(re.search(r"\d{1,2}\s*일", evidence))
    mentions_same_time = "똑같은 시간" in evidence or "같은 시간" in evidence
    if not has_explicit_time and (has_date_day or mentions_same_time):
        next_meeting["time"] = "unknown"


def _source_date(source_file: str) -> Optional[date]:
    match = re.search(r"(20\d{2})(\d{2})(\d{2})", source_file)
    if not match:
        return None
    try:
        return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
    except ValueError:
        return None


def _meeting_date(parsed: Dict[str, Any], source_file: str) -> str:
    value = str(parsed.get("date") or "").strip()
    if value and value.lower() not in {"unknown", "none", "null", "-"}:
        return value
    source_date = _source_date(source_file)
    return source_date.isoformat() if source_date else "unknown"


def _next_month_for_day(base_date: date, day: int) -> tuple[int, int]:
    year = base_date.year
    month = base_date.month
    try:
        candidate = date(year, month, day)
    except ValueError:
        candidate = base_date
    if candidate <= base_date:
        month += 1
        if month > 12:
            month = 1
            year += 1
    return year, month


def _dedupe_summary_items(summary: Dict[str, Any]) -> None:
    for field, key in [
        ("key_topics", "title"),
        ("decisions", "decision"),
        ("action_items", "task"),
        ("worth_noting", "note"),
        ("open_questions", "question"),
    ]:
        items = summary.get(field)
        if not isinstance(items, list):
            continue
        seen = set()
        deduped = []
        for item in items:
            if not isinstance(item, dict):
                continue
            identity = _normalize_identity(item.get(key, ""))
            if not identity or identity in seen:
                continue
            seen.add(identity)
            deduped.append(item)
        summary[field] = deduped


def _normalize_identity(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().lower())


def _chunk_counts(chunk_analyses: Optional[List[Dict[str, Any]]]) -> Dict[str, int]:
    if not chunk_analyses:
        return {"kept": 0, "skipped": 0}
    kept = sum(1 for item in chunk_analyses if item.get("classification") != "skipped")
    skipped = sum(1 for item in chunk_analyses if item.get("classification") == "skipped")
    return {"kept": kept, "skipped": skipped}


def synthesize_direct_with_llm(
    transcript: Dict[str, Any],
    chunks: List[Dict[str, Any]],
    required_search_report: List[Dict[str, Any]],
    profile: Dict[str, Any],
    rendering: Dict[str, Any],
    llm: LLMProvider,
    run_id: str,
    source_file: str,
    chunk_analyses: Optional[List[Dict[str, Any]]] = None,
    model_info: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    title = (
        transcript.get("title")
        or profile.get("meeting_profile", {}).get("default_title", "Zoom Meeting Summary")
    )
    meeting_duration = format_duration(float(transcript.get("duration_sec", 0.0)))
    meeting_id = str(transcript.get("meeting_id", run_id))
    prompt = render_named(
        "synthesize_direct_json",
        {
            "meeting_id": meeting_id,
            "meeting_title": title,
            "meeting_duration": meeting_duration,
            "source_file": source_file,
            "output_language": profile.get("meeting_profile", {}).get("output_language", "ko"),
            "required_items": _required_items_block(profile),
            "custom_topics": _custom_topics_block(profile),
            "verification_terms": _verification_terms_block(profile),
            "required_search_report": _required_report_json(required_search_report),
            "salience_map": _salience_map_jsonl(chunks, chunk_analyses),
            "worth_noting_max": int(rendering.get("worth_noting_max", 8)),
            "key_topics_max": int(rendering.get("key_topics_max", 8)),
            "transcript": _format_transcript(transcript),
        },
    )
    try:
        response = llm.call(
            prompt,
            max_tokens=int(rendering.get("direct_summary_max_tokens", 4096)),
            think=False,
            json_schema=_summary_schema(),
        )
    except LLMError as exc:
        raise LLMError("direct JSON synthesis failed: {0}".format(exc)) from exc
    parsed = _parse_json_response(response.text)
    if parsed is None:
        raise LLMError("direct JSON synthesis returned unparsable text")
    _dedupe_summary_items(parsed)
    _repair_next_meeting_date(parsed, transcript, source_file)
    _repair_next_meeting_time(parsed, transcript)
    chunk_counts = _chunk_counts(chunk_analyses)

    return {
        "meeting_id": meeting_id,
        "title": title,
        "date": _meeting_date(parsed, source_file),
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
            "kept_chunk_count": chunk_counts["kept"],
            "skipped_chunk_count": chunk_counts["skipped"],
            "output_sections": profile.get("output_sections", []),
            "rendering": rendering,
            "synthesis": {
                "mode": "fast_direct_json",
                "llm_calls": 1,
                "uses_salience_map": bool(chunk_analyses),
                "two_pass": False,
            },
            "extraction": {
                "strategy": "deterministic_salience_map",
                "analyzed_chunks": len(chunk_analyses or []),
            },
        },
    }
