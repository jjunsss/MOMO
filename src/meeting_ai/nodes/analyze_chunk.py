"""Rule-based chunk analysis for the MVP pipeline."""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Optional, Tuple

from meeting_ai.config.defaults import default_extraction_keywords
from meeting_ai.utils.time import format_seconds


_SENTENCE_SPLIT_RE = re.compile(r"(?<=[\.\?!。…])\s+|\n+")


def analyze_chunks(
    chunks: Iterable[Dict[str, Any]],
    required_items: List[Dict[str, Any]],
    keywords: Optional[Dict[str, List[str]]] = None,
) -> List[Dict[str, Any]]:
    resolved = _resolve_keywords(keywords)
    return [analyze_chunk(chunk, required_items, resolved) for chunk in chunks]


def analyze_chunk(
    chunk: Dict[str, Any],
    required_items: List[Dict[str, Any]],
    keywords: Optional[Dict[str, List[str]]] = None,
) -> Dict[str, Any]:
    kw = _resolve_keywords(keywords)
    text = chunk["text"]
    lowered = text.lower()
    start_label = format_seconds(float(chunk["start"]))
    end_label = format_seconds(float(chunk["end"]))
    segments = chunk.get("segments", [])

    key_points: List[Dict[str, Any]] = []
    decisions: List[Dict[str, Any]] = []
    actions: List[Dict[str, Any]] = []
    questions: List[Dict[str, Any]] = []
    next_meetings: List[Dict[str, Any]] = []
    worth_noting: List[Dict[str, Any]] = []

    for sentence_text, evidence in _all_segment_matches(segments, kw["decision"]):
        if _matches_any(sentence_text, kw["uncertain_decision"]):
            questions.append(
                {
                    "question": sentence_text,
                    "context": "decision still needs follow-up",
                    "evidence_timestamps": evidence,
                    "uncertainty": "medium",
                }
            )
            key_points.append(_key_point(sentence_text, "question", 4, evidence))
        else:
            decisions.append(
                {
                    "decision": sentence_text,
                    "evidence_timestamps": evidence,
                    "uncertainty": "medium",
                }
            )
            key_points.append(_key_point(sentence_text, "decision", 5, evidence))

    for sentence_text, evidence in _all_segment_matches(segments, kw["action"]):
        actions.append(
            {
                "task": sentence_text,
                "owner": "unknown",
                "deadline": "unknown",
                "priority": "medium",
                "evidence_timestamps": evidence,
                "uncertainty": "medium",
            }
        )
        key_points.append(_key_point(sentence_text, "action", 5, evidence))

    for sentence_text, evidence in _all_segment_matches(segments, kw["question"]):
        questions.append(
            {
                "question": sentence_text,
                "context": "chunk-level question",
                "evidence_timestamps": evidence,
                "uncertainty": "medium",
            }
        )
        key_points.append(_key_point(sentence_text, "question", 3, evidence))

    for sentence_text, evidence in _all_segment_matches(segments, kw["next_meeting"]):
        next_meetings.append(
            {
                "date": "unknown",
                "time": "unknown",
                "agenda": sentence_text,
                "preparation": "unknown",
                "evidence_timestamps": evidence,
                "uncertainty": "medium",
            }
        )
        key_points.append(_key_point(sentence_text, "next_meeting", 5, evidence))

    for sentence_text, evidence in _all_segment_matches(segments, kw["worth_noting"]):
        worth_noting.append(
            {
                "note": sentence_text,
                "why_it_matters": "회의 후속 판단에 영향을 줄 수 있는 맥락입니다.",
                "related_topic": "general",
                "importance": 4,
                "evidence_timestamps": evidence,
                "uncertainty": "medium",
            }
        )
        key_points.append(_key_point(sentence_text, "worth_noting", 4, evidence))

    required_hits = _required_hits(segments, lowered, required_items, [start_label])
    salience_score = min(5, len(key_points) + len(required_hits))
    classification = "kept" if salience_score > 0 else "skipped"
    skip_reason: Optional[str] = (
        None
        if classification == "kept"
        else "No decision, action, required item, or notable context detected."
    )

    return {
        "chunk_id": chunk["chunk_id"],
        "time_range": {"start": start_label, "end": end_label},
        "salience_score": salience_score,
        "classification": classification,
        "skip_reason": skip_reason,
        "topic": "general",
        "one_sentence_summary": _summary_sentence(key_points),
        "key_points": key_points,
        "decisions": decisions,
        "action_items": actions,
        "open_questions": questions,
        "next_meeting_mentions": next_meetings,
        "worth_noting_candidates": worth_noting,
        "required_search_hits": required_hits,
    }


def _resolve_keywords(overrides: Optional[Dict[str, List[str]]]) -> Dict[str, List[str]]:
    base = default_extraction_keywords()
    if not overrides:
        return base
    merged = dict(base)
    for key, value in overrides.items():
        if value:
            merged[key] = list(value)
    return merged


def _key_point(point: str, point_type: str, importance: int, evidence: List[str]) -> Dict[str, Any]:
    return {
        "point": point,
        "type": point_type,
        "importance": importance,
        "evidence_timestamps": evidence,
        "evidence_quote": point[:240],
        "uncertainty": "medium",
    }


def _all_segment_matches(
    segments: List[Dict[str, Any]], keywords: List[str]
) -> List[Tuple[str, List[str]]]:
    if not keywords:
        return []
    lowered_keywords = [kw.lower() for kw in keywords if kw]
    if not lowered_keywords:
        return []
    seen_sentences: set = set()
    results: List[Tuple[str, List[str]]] = []
    for segment in segments:
        text = str(segment.get("text", ""))
        if not text:
            continue
        evidence = [format_seconds(float(segment.get("start", 0.0)))]
        for sentence in _sentences(text):
            lowered = sentence.lower()
            if not any(kw in lowered for kw in lowered_keywords):
                continue
            normalized_key = " ".join(lowered.split())
            if normalized_key in seen_sentences:
                continue
            seen_sentences.add(normalized_key)
            results.append((sentence[:500].strip(), evidence))
    return results


def _matches_any(text: str, keywords: List[str]) -> bool:
    lowered = text.lower()
    return any(kw and kw.lower() in lowered for kw in keywords)


def _sentences(text: str) -> List[str]:
    parts = [part.strip() for part in _SENTENCE_SPLIT_RE.split(text) if part and part.strip()]
    return parts or [text.strip()]


def _required_hits(
    segments: List[Dict[str, Any]],
    lowered_text: str,
    required_items: List[Dict[str, Any]],
    fallback_evidence: List[str],
) -> List[Dict[str, Any]]:
    hits: List[Dict[str, Any]] = []
    for item in required_items:
        aliases = item.get("aliases", [])
        matched = [alias for alias in aliases if str(alias).lower() in lowered_text]
        if matched:
            evidence = _evidence_for_aliases(segments, matched) or fallback_evidence
            hits.append(
                {
                    "required_item_id": item.get("id", "unknown"),
                    "status": "found",
                    "value": {"matched_aliases": matched},
                    "evidence_timestamps": evidence,
                    "uncertainty": "medium",
                }
            )
    return hits


def _evidence_for_aliases(segments: List[Dict[str, Any]], aliases: List[str]) -> List[str]:
    evidence: List[str] = []
    lowered_aliases = [str(alias).lower() for alias in aliases]
    for segment in segments:
        text = str(segment.get("text", "")).lower()
        if any(alias in text for alias in lowered_aliases):
            evidence.append(format_seconds(float(segment.get("start", 0.0))))
    return sorted(set(evidence))


def _summary_sentence(key_points: List[Dict[str, Any]]) -> str:
    if not key_points:
        return "중요한 후속 처리 항목은 감지되지 않았습니다."
    return key_points[0]["point"]
