"""Per-slot extraction over (potentially) the full transcript.

Strategy
--------
Adaptive hierarchical:
- Estimate transcript token count.
- If it fits in ``single_pass_token_limit`` (default 60K), make ONE LLM call
  per slot over the entire transcript. This avoids the chunk-extract
  information-loss cascade we saw in v1.
- Otherwise fall back to a chunk pyramid: per-chunk extract -> per-slot merge.

Each slot prompt includes:
- The slot definition (id, label, description, aliases) drawn from
  ``meeting_profile.md``.
- A few-shot block (date vs. time discrimination, owner-attribution refusal).
- The transcript with stable timestamps so the LLM can cite evidence directly.

Returns a uniform structure regardless of strategy::

    [
      {"slot_id": "next_meeting", "items": [...], "method": "single_pass"|"hierarchical"},
      ...
    ]

so the synthesis node does not care how the items were collected.
"""

from __future__ import annotations

import json
from typing import Any, Dict, Iterable, List, Optional, Tuple

from meeting_ai.prompts import render_named
from meeting_ai.providers.llm.base import LLMError, LLMProvider
from meeting_ai.utils.time import format_seconds


def _slot_definitions(
    required_items: List[Dict[str, Any]], custom_topics: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    slots: List[Dict[str, Any]] = []
    for item in required_items:
        slots.append(
            {
                "id": str(item.get("id") or "unknown"),
                "label": str(item.get("label") or item.get("id") or "unknown"),
                "kind": "required",
                "description": str(item.get("description") or ""),
                "aliases": list(item.get("aliases") or []),
            }
        )
    for topic in custom_topics:
        slots.append(
            {
                "id": "topic_{0}".format(topic.get("id") or "unknown"),
                "label": str(topic.get("label") or topic.get("id") or "unknown"),
                "kind": "custom_topic",
                "description": str(topic.get("description") or ""),
                "aliases": list(topic.get("aliases") or []),
            }
        )
    return slots


def _format_transcript(transcript: Dict[str, Any]) -> str:
    lines: List[str] = []
    for segment in transcript.get("segments", []):
        ts = format_seconds(float(segment.get("start", 0.0)))
        lines.append("[{0} | {1}] {2}".format(segment.get("id", "?"), ts, segment.get("text", "")))
    return "\n".join(lines)


def _format_chunk(chunk: Dict[str, Any]) -> str:
    lines: List[str] = []
    for segment in chunk.get("segments", []):
        ts = format_seconds(float(segment.get("start", 0.0)))
        lines.append("[{0} | {1}] {2}".format(segment.get("id", "?"), ts, segment.get("text", "")))
    return "\n".join(lines) if lines else str(chunk.get("text", ""))


def _estimate_tokens(text: str) -> int:
    # Korean text averages ~1.3 chars per token for Qwen tokenizers; using 1.0
    # is a safe upper-bound estimate (we want to *underuse* the context budget).
    return max(1, len(text))


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


def _normalize_items(raw_items: Any, slot_id: str, max_items: int) -> List[Dict[str, Any]]:
    if not isinstance(raw_items, list):
        return []
    normalized: List[Dict[str, Any]] = []
    for entry in raw_items:
        if not isinstance(entry, dict):
            continue
        summary = str(entry.get("summary") or entry.get("note") or "").strip()
        if not summary:
            continue
        evidence = entry.get("evidence_timestamps") or []
        if not isinstance(evidence, list):
            evidence = [evidence]
        evidence = [str(e).strip() for e in evidence if str(e).strip()]
        normalized.append(
            {
                "slot_id": slot_id,
                "summary": summary[:500],
                "importance": _safe_int(entry.get("importance"), 3, lo=1, hi=5),
                "owner": str(entry.get("owner") or "unknown")[:80],
                "deadline": str(entry.get("deadline") or "unknown")[:80],
                "date": str(entry.get("date") or "unknown")[:80],
                "time": str(entry.get("time") or "unknown")[:80],
                "evidence_timestamps": evidence[:8],
                "evidence_quote": str(entry.get("evidence_quote") or "")[:300],
            }
        )
    normalized.sort(key=lambda item: -int(item.get("importance", 0)))
    return normalized[:max_items]


def _safe_int(value: Any, default: int, lo: Optional[int] = None, hi: Optional[int] = None) -> int:
    try:
        result = int(value)
    except (TypeError, ValueError):
        result = default
    if lo is not None:
        result = max(lo, result)
    if hi is not None:
        result = min(hi, result)
    return result


def _slot_extract_schema() -> Dict[str, Any]:
    """JSON schema enforced at decoding time by Ollama (model-side grammar)."""
    return {
        "type": "object",
        "required": ["items"],
        "properties": {
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["summary", "importance", "evidence_timestamps"],
                    "properties": {
                        "summary": {"type": "string"},
                        "importance": {"type": "integer", "minimum": 1, "maximum": 5},
                        "owner": {"type": "string"},
                        "deadline": {"type": "string"},
                        "date": {"type": "string"},
                        "time": {"type": "string"},
                        "evidence_timestamps": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "evidence_quote": {"type": "string"},
                    },
                },
            }
        },
    }


def extract_per_slot(
    transcript: Dict[str, Any],
    chunks: List[Dict[str, Any]],
    profile: Dict[str, Any],
    llm: LLMProvider,
    *,
    single_pass_token_limit: int = 60_000,
    max_items_per_slot: int = 8,
    meeting_id: str = "unknown",
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Run per-slot extraction.

    Returns ``(slot_extracts, meta)`` where ``meta`` records which strategy
    was used per slot and what the transcript-token estimate was.
    """

    slots = _slot_definitions(
        profile.get("required_search_items", []),
        profile.get("custom_topics", []),
    )
    transcript_text = _format_transcript(transcript)
    estimated_tokens = _estimate_tokens(transcript_text)
    fits_single_pass = estimated_tokens <= single_pass_token_limit
    meta: Dict[str, Any] = {
        "strategy": "single_pass" if fits_single_pass else "hierarchical",
        "estimated_chars": estimated_tokens,
        "single_pass_token_limit": single_pass_token_limit,
        "slots": [],
    }

    slot_extracts: List[Dict[str, Any]] = []
    for slot in slots:
        if fits_single_pass:
            items = _extract_single_pass(slot, transcript_text, llm, meeting_id, max_items_per_slot)
            method = "single_pass"
        else:
            items = _extract_hierarchical(slot, chunks, llm, meeting_id, max_items_per_slot)
            method = "hierarchical"
        slot_extracts.append(
            {
                "slot_id": slot["id"],
                "label": slot["label"],
                "kind": slot["kind"],
                "method": method,
                "items": items,
            }
        )
        meta["slots"].append({"slot_id": slot["id"], "method": method, "items": len(items)})
    return slot_extracts, meta


def _extract_single_pass(
    slot: Dict[str, Any],
    transcript_text: str,
    llm: LLMProvider,
    meeting_id: str,
    max_items: int,
) -> List[Dict[str, Any]]:
    prompt = render_named(
        "slot_extractor_single_pass",
        {
            "meeting_id": meeting_id,
            "slot_id": slot["id"],
            "slot_label": slot["label"],
            "slot_kind": slot["kind"],
            "slot_description": slot["description"] or "(설명 없음)",
            "slot_aliases": ", ".join(slot["aliases"]) or "(없음)",
            "max_items": max_items,
            "transcript": transcript_text,
        },
    )
    try:
        # think=True helps the model locate evidence in long transcripts;
        # json_schema enforces the {"items":[...]} contract at decode time so
        # the model cannot drift to ad-hoc shapes like {"next_meeting":"..."}.
        response = llm.call(
            prompt,
            think=True,
            max_tokens=4096,
            json_schema=_slot_extract_schema(),
        )
    except LLMError:
        return []
    parsed = _parse_json_response(response.text)
    if not parsed:
        return []
    return _normalize_items(parsed.get("items"), slot["id"], max_items)


def _extract_hierarchical(
    slot: Dict[str, Any],
    chunks: Iterable[Dict[str, Any]],
    llm: LLMProvider,
    meeting_id: str,
    max_items: int,
) -> List[Dict[str, Any]]:
    chunk_results: List[Dict[str, Any]] = []
    for chunk in chunks:
        prompt = render_named(
            "slot_extractor_chunk",
            {
                "meeting_id": meeting_id,
                "chunk_id": chunk.get("chunk_id", "?"),
                "chunk_time_range": "{0} - {1}".format(
                    format_seconds(float(chunk.get("start", 0.0))),
                    format_seconds(float(chunk.get("end", 0.0))),
                ),
                "slot_id": slot["id"],
                "slot_label": slot["label"],
                "slot_kind": slot["kind"],
                "slot_description": slot["description"] or "(설명 없음)",
                "slot_aliases": ", ".join(slot["aliases"]) or "(없음)",
                "max_items": max_items,
                "chunk_text": _format_chunk(chunk),
            },
        )
        try:
            response = llm.call(
                prompt,
                think=True,
                max_tokens=2048,
                json_schema=_slot_extract_schema(),
            )
        except LLMError:
            continue
        parsed = _parse_json_response(response.text)
        if not parsed:
            continue
        chunk_results.extend(_normalize_items(parsed.get("items"), slot["id"], max_items))

    if not chunk_results:
        return []

    # Reduce: ask the LLM to merge across chunks.
    merge_prompt = render_named(
        "slot_merger",
        {
            "meeting_id": meeting_id,
            "slot_id": slot["id"],
            "slot_label": slot["label"],
            "slot_description": slot["description"] or "(설명 없음)",
            "max_items": max_items,
            "chunk_items_jsonl": "\n".join(
                json.dumps(item, ensure_ascii=False, sort_keys=True) for item in chunk_results
            ),
        },
    )
    try:
        merged = llm.call(
            merge_prompt,
            think=True,
            max_tokens=3072,
            json_schema=_slot_extract_schema(),
        )
    except LLMError:
        return chunk_results[:max_items]
    parsed_merge = _parse_json_response(merged.text)
    if not parsed_merge:
        return chunk_results[:max_items]
    return _normalize_items(parsed_merge.get("items"), slot["id"], max_items)
