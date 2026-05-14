"""Convert simple GUI topic form input into a topic_details JSON file."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import List, Optional


def parse_lines(text: str) -> List[str]:
    """Split a textarea value into stripped, non-empty lines."""
    if not text:
        return []
    items: List[str] = []
    seen: set = set()
    for raw in text.replace("\r", "").split("\n"):
        item = raw.strip()
        if not item:
            continue
        key = item.lower()
        if key in seen:
            continue
        seen.add(key)
        items.append(item)
    return items


def build_payload(
    title: str,
    topics: List[str],
    must_check: List[str],
    custom_instruction: str = "",
) -> Optional[dict]:
    """Return a topic_details payload, or None if every field is empty."""
    title = (title or "").strip()
    instruction = (custom_instruction or "").strip()
    has_any = bool(title) or bool(topics) or bool(must_check) or bool(instruction)
    if not has_any:
        return None
    payload: dict = {}
    if title:
        payload["title"] = title
    if instruction:
        payload["custom_instruction"] = instruction
    if topics:
        payload["topics"] = topics
    if must_check:
        payload["must_check"] = must_check
    return payload


def write_temp_topic_details(payload: Optional[dict]) -> Optional[Path]:
    """Persist the payload to a temp file and return its path.

    Returns None when payload is None so callers fall through to the
    advanced `meeting_profile.md` defaults.
    """
    if payload is None:
        return None
    handle = tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        suffix="_topic_details.json",
        prefix="momo_",
        delete=False,
    )
    try:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
    finally:
        handle.close()
    return Path(handle.name)


def archive_topic_details(temp_path: Optional[Path], run_dir: Path) -> None:
    """Copy the temp topic details into the run directory and clean up."""
    if temp_path is None or not temp_path.exists():
        return
    target_dir = run_dir / "source"
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / "topic_details.used.json"
    target.write_text(temp_path.read_text(encoding="utf-8"), encoding="utf-8")
    try:
        temp_path.unlink()
    except FileNotFoundError:  # pragma: no cover - best-effort cleanup
        pass
