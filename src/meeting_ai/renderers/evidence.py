"""Evidence/audit rendering separate from user-facing summaries."""

from __future__ import annotations

import re
from copy import deepcopy
from typing import Any, Dict, Iterable, List

from meeting_ai.utils.time import format_seconds


EVIDENCE_KEYS = {
    "evidence_timestamps",
    "evidence_snippets",
    "evidence_quote",
    "source_chunks",
    "support",
    "include_evidence_snippets",
    "include_timestamps",
}


def strip_evidence_fields(value: Any) -> Any:
    """Return a copy with evidence/support fields removed for public artifacts."""
    return _strip(deepcopy(value))


def render_summary_evidence_markdown(
    summary: Dict[str, Any], transcript: Dict[str, Any]
) -> str:
    lines: List[str] = []
    metadata = summary.get("metadata", {})
    lines.append("# Summary Evidence")
    lines.append("")
    lines.append("- **Title**: {0}".format(summary.get("title", "Meeting Summary")))
    lines.append("- **Source**: {0}".format(summary.get("source_file", "unknown")))
    lines.append("- **Duration**: {0}".format(summary.get("duration", "unknown")))
    lines.append("- **Pipeline**: {0}".format(metadata.get("pipeline_version", "unknown")))
    lines.append("")

    _render_topic_evidence(lines, "Key Topics", summary.get("key_topics", []), transcript)
    _render_item_evidence(
        lines,
        "Decisions",
        summary.get("decisions", []),
        "decision",
        "rationale",
        transcript,
    )
    _render_item_evidence(
        lines,
        "Action Items",
        summary.get("action_items", []),
        "task",
        "deadline",
        transcript,
    )
    _render_next_meeting_evidence(lines, summary.get("next_meeting", {}), transcript)
    _render_item_evidence(
        lines,
        "Worth Noting",
        summary.get("worth_noting", []),
        "note",
        "why_it_matters",
        transcript,
    )
    _render_item_evidence(
        lines,
        "Open Questions",
        summary.get("open_questions", []),
        "question",
        "context",
        transcript,
    )
    _render_required_report_evidence(
        lines,
        "Required Search Report",
        summary.get("required_search_report", []),
    )
    return "\n".join(lines).rstrip() + "\n"


def _strip(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _strip(item)
            for key, item in value.items()
            if key not in EVIDENCE_KEYS
        }
    if isinstance(value, list):
        return [_strip(item) for item in value]
    return value


def _render_topic_evidence(
    lines: List[str],
    title: str,
    items: List[Dict[str, Any]],
    transcript: Dict[str, Any],
) -> None:
    _section(lines, title)
    if not items:
        lines.append("No topic evidence.")
        lines.append("")
        return
    lines.append("| Topic | Timestamp | Transcript |")
    lines.append("|---|---|---|")
    for item in items:
        timestamps = item.get("evidence_timestamps", [])
        lines.append(
            "| {0} | {1} | {2} |".format(
                _cell(item.get("title", "")),
                _cell(_timestamps(timestamps)),
                _cell(_snippets(transcript, timestamps)),
            )
        )
    lines.append("")


def _render_item_evidence(
    lines: List[str],
    title: str,
    items: List[Dict[str, Any]],
    text_key: str,
    context_key: str,
    transcript: Dict[str, Any],
) -> None:
    _section(lines, title)
    if not items:
        lines.append("No evidence.")
        lines.append("")
        return
    lines.append("| Claim | Context | Support | Timestamp | Transcript |")
    lines.append("|---|---|---|---|---|")
    for item in items:
        timestamps = item.get("evidence_timestamps", [])
        lines.append(
            "| {0} | {1} | {2} | {3} | {4} |".format(
                _cell(item.get(text_key, "")),
                _cell(item.get(context_key, "")),
                _cell(item.get("support", "")),
                _cell(_timestamps(timestamps)),
                _cell(_snippets(transcript, timestamps)),
            )
        )
    lines.append("")


def _render_next_meeting_evidence(
    lines: List[str], next_meeting: Dict[str, Any], transcript: Dict[str, Any]
) -> None:
    _section(lines, "Next Meeting")
    if not next_meeting:
        lines.append("No next meeting object.")
        lines.append("")
        return
    timestamps = next_meeting.get("evidence_timestamps", [])
    lines.append("| Status | Date | Time | Agenda | Support | Timestamp | Transcript |")
    lines.append("|---|---|---|---|---|---|---|")
    lines.append(
        "| {0} | {1} | {2} | {3} | {4} | {5} | {6} |".format(
            _cell(next_meeting.get("status", "")),
            _cell(next_meeting.get("date", "unknown")),
            _cell(next_meeting.get("time", "unknown")),
            _cell("; ".join(next_meeting.get("agenda", []))),
            _cell(next_meeting.get("support", "")),
            _cell(_timestamps(timestamps)),
            _cell(_snippets(transcript, timestamps)),
        )
    )
    lines.append("")


def _render_required_report_evidence(
    lines: List[str], title: str, report: List[Dict[str, Any]]
) -> None:
    _section(lines, title)
    if not report:
        lines.append("No required-search report.")
        lines.append("")
        return
    lines.append("| Item | Status | Summary | Timestamp | Snippets |")
    lines.append("|---|---|---|---|---|")
    for item in report:
        lines.append(
            "| {0} | {1} | {2} | {3} | {4} |".format(
                _cell(item.get("label", "")),
                _cell(item.get("status", "")),
                _cell(item.get("summary", "")),
                _cell(_timestamps(item.get("evidence_timestamps", []))),
                _cell(_required_snippets(item.get("evidence_snippets", []))),
            )
        )
    lines.append("")


def _section(lines: List[str], title: str) -> None:
    lines.append("## {0}".format(title))
    lines.append("")


def _timestamps(values: Iterable[str]) -> str:
    timestamps = [str(value) for value in values if value]
    return ", ".join(timestamps) if timestamps else "-"


def _snippets(transcript: Dict[str, Any], timestamps: Iterable[str]) -> str:
    values: List[str] = []
    segments = transcript.get("segments", [])
    for timestamp in list(timestamps)[:3]:
        text = _find_segment_text(segments, str(timestamp))
        values.append("{0}: {1}".format(timestamp, text or "-"))
    return " / ".join(values) if values else "-"


def _find_segment_text(segments: List[Dict[str, Any]], timestamp: str) -> str:
    target = _parse_timestamp(timestamp)
    if target is None:
        return ""
    best: Dict[str, Any] = {}
    best_delta = 9.0
    for segment in segments:
        start = float(segment.get("start", 0.0))
        delta = abs(start - target)
        if delta < best_delta:
            best_delta = delta
            best = segment
    if not best:
        return ""
    start = format_seconds(float(best.get("start", 0.0)))
    text = re.sub(r"^\d{2}:\d{2}:\d{2}\s+", "", str(best.get("text", "")).strip())
    return "{0} {1}".format(start, text)


def _parse_timestamp(timestamp: str) -> float | None:
    try:
        h, m, s = (int(part) for part in timestamp.split(":"))
    except ValueError:
        return None
    return float(h * 3600 + m * 60 + s)


def _required_snippets(snippets: Iterable[Dict[str, str]]) -> str:
    values = []
    for snippet in list(snippets)[:3]:
        timestamp = snippet.get("timestamp", "")
        text = snippet.get("text", "")
        if timestamp and text:
            values.append("{0}: {1}".format(timestamp, text))
    return " / ".join(values) if values else "-"


def _cell(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ").strip()
