"""Transcript Markdown renderer."""

from __future__ import annotations

from typing import Any, Dict, List

from meeting_ai.utils.time import format_seconds


def render_transcript_markdown(transcript: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append("# Transcript")
    lines.append("")
    lines.append("- **Meeting ID**: {0}".format(transcript.get("meeting_id", "unknown")))
    lines.append("- **Language**: {0}".format(transcript.get("language", "unknown")))
    lines.append("- **Duration**: {0}".format(format_seconds(float(transcript.get("duration_sec", 0.0)))))
    lines.append("")
    for segment in transcript.get("segments", []):
        start = format_seconds(float(segment.get("start", 0.0)))
        end = format_seconds(float(segment.get("end", 0.0)))
        lines.append("- **{0}-{1}** {2}".format(start, end, segment.get("text", "")))
    return "\n".join(lines).rstrip() + "\n"
