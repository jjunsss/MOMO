"""Transcript normalization."""

from __future__ import annotations

import re
from typing import Any, Dict, List

from meeting_ai.schemas.transcript import validate_transcript


_SPACE_RE = re.compile(r"\s+")
_MIN_REPEATED_CANONICAL_LENGTH = 12
_MIN_REPEATED_RUN_LENGTH = 4
_SILENCE_NO_SPEECH_THRESHOLD = 0.80
_SILENCE_LOGPROB_THRESHOLD = -0.40
_HIGH_COMPRESSION_RATIO = 3.0


def _clean_text(text: str) -> str:
    return _SPACE_RE.sub(" ", text).strip()


def _canonical_repetition_text(text: str) -> str:
    return "".join(char for char in text.lower() if char.isalnum())


def _optional_float(value: Any) -> float | None:
    if value in {None, ""}:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _is_probable_silence_hallucination(segment: Dict[str, Any]) -> bool:
    no_speech_prob = _optional_float(segment.get("no_speech_prob"))
    avg_logprob = _optional_float(segment.get("avg_logprob"))
    compression_ratio = _optional_float(segment.get("compression_ratio"))

    if no_speech_prob is not None and no_speech_prob >= _SILENCE_NO_SPEECH_THRESHOLD:
        if avg_logprob is None or avg_logprob <= _SILENCE_LOGPROB_THRESHOLD:
            return True
    if compression_ratio is not None and compression_ratio >= _HIGH_COMPRESSION_RATIO:
        text = str(segment.get("text", ""))
        return len(_canonical_repetition_text(text)) >= _MIN_REPEATED_CANONICAL_LENGTH
    return False


def _collapse_repeated_hallucination_runs(
    segments: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    collapsed: List[Dict[str, Any]] = []
    index = 0
    while index < len(segments):
        current = segments[index]
        canonical = _canonical_repetition_text(current["text"])
        end = index + 1
        while end < len(segments):
            if _canonical_repetition_text(segments[end]["text"]) != canonical:
                break
            end += 1

        run = segments[index:end]
        if (
            canonical
            and len(canonical) >= _MIN_REPEATED_CANONICAL_LENGTH
            and len(run) >= _MIN_REPEATED_RUN_LENGTH
        ):
            collapsed.append(run[0])
        else:
            collapsed.extend(run)
        index = end
    return collapsed


def normalize_transcript(transcript: Dict[str, Any]) -> Dict[str, Any]:
    validate_transcript(transcript)
    segments: List[Dict[str, Any]] = []
    for index, segment in enumerate(transcript.get("segments", []), start=1):
        if _is_probable_silence_hallucination(segment):
            continue
        text = _clean_text(str(segment.get("text", "")))
        if not text:
            continue
        start = float(segment.get("start", 0.0))
        end = float(segment.get("end", start))
        if end < start:
            raise ValueError("segment end is before start: {0}".format(segment))
        segments.append(
            {
                "id": str(segment.get("id") or "t{0:06d}".format(index)),
                "start": start,
                "end": end,
                "text": text,
                "speaker": segment.get("speaker"),
                "confidence": segment.get("confidence"),
            }
        )

    segments.sort(key=lambda item: (item["start"], item["end"]))
    segments = _collapse_repeated_hallucination_runs(segments)
    duration = float(transcript.get("duration_sec") or (segments[-1]["end"] if segments else 0.0))
    normalized = {
        "meeting_id": str(transcript.get("meeting_id") or "unknown_meeting"),
        "title": transcript.get("title"),
        "source_file": transcript.get("source_file"),
        "language": transcript.get("language", "unknown"),
        "duration_sec": duration,
        "segments": segments,
    }
    validate_transcript(normalized)
    return normalized
