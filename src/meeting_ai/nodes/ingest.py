"""Input loading."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from meeting_ai.schemas.transcript import validate_transcript
from meeting_ai.utils.io import read_json


SUPPORTED_TRANSCRIPT_SUFFIXES = {".json"}
SUPPORTED_MEDIA_SUFFIXES = {".mp4", ".mkv", ".mov", ".m4a", ".mp3", ".wav"}


def is_transcript_source(source_path: Path) -> bool:
    return source_path.suffix.lower() in SUPPORTED_TRANSCRIPT_SUFFIXES


def is_media_source(source_path: Path) -> bool:
    return source_path.suffix.lower() in SUPPORTED_MEDIA_SUFFIXES


def load_source_transcript(source_path: Path) -> Dict[str, Any]:
    if not source_path.exists():
        raise FileNotFoundError("source does not exist: {0}".format(source_path))

    suffix = source_path.suffix.lower()
    if suffix in SUPPORTED_TRANSCRIPT_SUFFIXES:
        transcript = read_json(source_path)
        if not isinstance(transcript, dict):
            raise ValueError("transcript JSON must contain an object")
        if "segments" not in transcript:
            raise ValueError("transcript JSON must include segments")
        validate_transcript(transcript)
        return transcript

    if suffix in SUPPORTED_MEDIA_SUFFIXES:
        raise NotImplementedError(
            "media ASR is not wired yet. Provide transcript JSON for this MVP."
        )

    raise ValueError("unsupported source type: {0}".format(source_path))
