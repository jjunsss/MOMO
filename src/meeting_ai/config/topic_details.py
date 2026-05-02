"""Load the small user-facing topic details JSON file."""

from __future__ import annotations

import re
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from meeting_ai.utils.io import read_json


def apply_topic_details(loaded: Dict[str, Any], path: Optional[Path]) -> Dict[str, Any]:
    """Overlay user-facing topic details onto the advanced runtime profile.

    The Markdown profile remains the advanced system/defaults file. This JSON is
    intentionally small so non-technical users only provide meeting-specific
    topics and verification hints.
    """
    if path is None or not path.exists():
        return loaded

    details = read_json(path)
    if not isinstance(details, dict):
        raise ValueError("topic details JSON must be an object: {0}".format(path))

    merged = deepcopy(loaded)
    profile = merged.setdefault("profile", {})
    meeting_profile = profile.setdefault("meeting_profile", {})
    meeting = _object(details.get("meeting"))

    title = details.get("title") or meeting.get("title")
    if title:
        meeting_profile["default_title"] = str(title)
    output_language = details.get("output_language") or meeting.get("output_language")
    if output_language:
        meeting_profile["output_language"] = str(output_language)

    topics = details.get("topics", details.get("custom_topics"))
    if topics is None:
        topics = details.get("focus")
    if topics is None:
        topics = details.get("summary_focus")
    if topics is not None:
        profile["custom_topics"] = _normalize_entries(topics, default_prefix="topic")

    verification_terms = details.get("verification_terms", details.get("verify"))
    if verification_terms is None:
        verification_terms = details.get("must_check")
    if verification_terms is None:
        verification_terms = details.get("careful_with")
    if verification_terms is not None:
        profile["verification_terms"] = _merge_by_id(
            profile.get("verification_terms", []),
            _normalize_entries(
                verification_terms,
                default_prefix="verify",
                description_keys=("description", "check", "rule"),
            ),
        )

    required_items = details.get("required_items", details.get("required_search_items"))
    if required_items is not None:
        profile["required_search_items"] = _normalize_required_items(required_items)

    profile["topic_details"] = {"path": str(path), "loaded": True}
    return merged


def _normalize_entries(
    entries: Any,
    *,
    default_prefix: str,
    description_keys: Iterable[str] = ("description",),
) -> List[Dict[str, Any]]:
    if not isinstance(entries, list):
        raise ValueError("{0}s must be a list".format(default_prefix))
    normalized: List[Dict[str, Any]] = []
    for index, raw in enumerate(entries, start=1):
        item = _entry_object(raw)
        if item.get("enabled") is False:
            continue
        label = str(item.get("label") or item.get("title") or "").strip()
        if not label:
            raise ValueError("{0} #{1} is missing label".format(default_prefix, index))
        aliases = _string_list(item.get("aliases", []))
        description = ""
        for key in description_keys:
            if item.get(key):
                description = str(item[key]).strip()
                break
        normalized.append(
            {
                "id": str(item.get("id") or _slug(label) or "{0}_{1}".format(default_prefix, index)),
                "label": label,
                "aliases": aliases,
                "description": description,
                "must_search": bool(item.get("must_search", True)),
            }
        )
    return normalized


def _normalize_required_items(entries: Any) -> List[Dict[str, Any]]:
    items = _normalize_entries(entries, default_prefix="required")
    for item in items:
        item["required"] = True
        item["priority"] = item.get("priority", "high")
    return items


def _merge_by_id(base: Any, overrides: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    merged: List[Dict[str, Any]] = []
    positions: Dict[str, int] = {}
    for item in base if isinstance(base, list) else []:
        if not isinstance(item, dict):
            continue
        key = str(item.get("id") or item.get("label") or "").strip()
        if not key:
            continue
        positions[key] = len(merged)
        merged.append(dict(item))
    for item in overrides:
        key = str(item.get("id") or item.get("label") or "").strip()
        if key in positions:
            merged[positions[key]] = item
        else:
            positions[key] = len(merged)
            merged.append(item)
    return merged


def _object(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _entry_object(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        return {"label": value}
    return {}


def _string_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [str(value).strip()] if str(value).strip() else []


def _slug(value: str) -> str:
    text = re.sub(r"[^0-9a-zA-Z가-힣]+", "_", value.strip().lower())
    return text.strip("_")
