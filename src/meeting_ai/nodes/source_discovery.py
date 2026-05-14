"""Discover media sources for automated runs."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from meeting_ai.nodes.ingest import SUPPORTED_MEDIA_SUFFIXES


FILENAME_TIMESTAMP_RE = re.compile(r"(20\d{6})[_-]?(\d{6})")


def find_latest_media(videos_dir: Path) -> Path:
    if not videos_dir.exists():
        raise FileNotFoundError("videos directory does not exist: {0}".format(videos_dir))
    candidates = [
        path
        for path in videos_dir.iterdir()
        if path.is_file() and path.suffix.lower() in SUPPORTED_MEDIA_SUFFIXES
    ]
    if not candidates:
        raise FileNotFoundError("no media files found in: {0}".format(videos_dir))
    return sorted(candidates, key=_media_sort_key, reverse=True)[0]


def derive_run_id(source_path: Path, configured: str) -> str:
    if configured and configured != "auto":
        return configured
    timestamp = _timestamp_token_from_name(source_path.name)
    if timestamp:
        return "zoom_{0}".format(timestamp)
    return source_path.stem


def _media_sort_key(path: Path) -> tuple:
    timestamp = _timestamp_from_name(path.name)
    if timestamp is None:
        timestamp = datetime.fromtimestamp(path.stat().st_mtime)
    return timestamp, path.name


def _timestamp_from_name(name: str) -> Optional[datetime]:
    match = FILENAME_TIMESTAMP_RE.search(name)
    if not match:
        return None
    try:
        return datetime.strptime("{0}{1}".format(match.group(1), match.group(2)), "%Y%m%d%H%M%S")
    except ValueError:
        return None


def _timestamp_token_from_name(name: str) -> Optional[str]:
    match = FILENAME_TIMESTAMP_RE.search(name)
    if not match:
        return None
    date_part = match.group(1)
    time_part = match.group(2)
    try:
        datetime.strptime("{0}{1}".format(date_part, time_part), "%Y%m%d%H%M%S")
    except ValueError:
        return None
    return "{0}_{1}".format(date_part, time_part)
