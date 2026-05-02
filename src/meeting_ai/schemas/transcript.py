"""Validation for transcript dictionaries."""

from __future__ import annotations

from typing import Any, Dict


def validate_transcript(transcript: Dict[str, Any]) -> None:
    if not isinstance(transcript, dict):
        raise ValueError("transcript must be an object")
    segments = transcript.get("segments")
    if not isinstance(segments, list):
        raise ValueError("transcript.segments must be a list")

    for index, segment in enumerate(segments):
        if not isinstance(segment, dict):
            raise ValueError("transcript.segments[{0}] must be an object".format(index))
        if "text" not in segment:
            raise ValueError("transcript.segments[{0}] missing text".format(index))
        if "start" not in segment or "end" not in segment:
            raise ValueError("transcript.segments[{0}] missing start/end".format(index))
        start = float(segment["start"])
        end = float(segment["end"])
        if end < start:
            raise ValueError("transcript.segments[{0}] end is before start".format(index))

