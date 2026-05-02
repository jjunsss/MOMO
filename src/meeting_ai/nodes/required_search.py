"""Required item search across transcript and chunk analyses."""

from __future__ import annotations

from typing import Any, Dict, List

from meeting_ai.utils.time import format_seconds


def build_required_search_report(
    required_items: List[Dict[str, Any]],
    transcript: Dict[str, Any],
    chunk_analyses: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    report: List[Dict[str, Any]] = []
    full_text = " ".join(segment["text"] for segment in transcript.get("segments", [])).lower()

    for item in required_items:
        item_id = item.get("id", "unknown")
        aliases = [str(alias) for alias in item.get("aliases", [])]
        matched_aliases = [alias for alias in aliases if alias.lower() in full_text]
        evidence = _evidence_for_aliases(transcript, matched_aliases)
        snippets = _snippets_for_aliases(transcript, matched_aliases)
        chunk_hits = [
            hit
            for analysis in chunk_analyses
            for hit in analysis.get("required_search_hits", [])
            if hit.get("required_item_id") == item_id
        ]
        for hit in chunk_hits:
            evidence.extend(hit.get("evidence_timestamps", []))
        evidence = sorted(set(evidence))

        if matched_aliases or chunk_hits:
            report.append(
                {
                    "required_item_id": item_id,
                    "label": item.get("label", item_id),
                    "status": "found",
                    "summary": "관련 표현 {0}건이 감지되었습니다: {1}".format(
                        len(evidence), ", ".join(sorted(set(matched_aliases))) or "chunk hit"
                    ),
                    "evidence_timestamps": evidence,
                    "evidence_snippets": snippets[:5],
                    "missing_reason": None,
                }
            )
        else:
            report.append(
                {
                    "required_item_id": item_id,
                    "label": item.get("label", item_id),
                    "status": "not_found",
                    "summary": "명시적으로 언급되지 않았습니다.",
                    "evidence_timestamps": [],
                    "evidence_snippets": [],
                    "missing_reason": "aliases and chunk-level hits did not produce a clear match.",
                }
            )
    return report


def _evidence_for_aliases(transcript: Dict[str, Any], aliases: List[str]) -> List[str]:
    evidence: List[str] = []
    lowered_aliases = [alias.lower() for alias in aliases]
    if not lowered_aliases:
        return evidence
    for segment in transcript.get("segments", []):
        text = segment["text"].lower()
        if any(alias in text for alias in lowered_aliases):
            evidence.append(format_seconds(float(segment["start"])))
    return evidence


def _snippets_for_aliases(transcript: Dict[str, Any], aliases: List[str]) -> List[Dict[str, str]]:
    snippets: List[Dict[str, str]] = []
    lowered_aliases = [alias.lower() for alias in aliases]
    if not lowered_aliases:
        return snippets
    for segment in transcript.get("segments", []):
        text = segment["text"]
        lowered = text.lower()
        if any(alias in lowered for alias in lowered_aliases):
            snippets.append(
                {
                    "timestamp": format_seconds(float(segment["start"])),
                    "text": text[:220],
                }
            )
    return snippets
