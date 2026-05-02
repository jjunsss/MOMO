"""Validation for final summary dictionaries."""

from __future__ import annotations

from typing import Any, Dict, Iterable


REQUIRED_SUMMARY_KEYS = [
    "meeting_id",
    "title",
    "tldr",
    "executive_summary",
    "key_topics",
    "decisions",
    "action_items",
    "next_meeting",
    "worth_noting",
    "open_questions",
    "required_search_report",
    "metadata",
]


def validate_final_summary(summary: Dict[str, Any]) -> None:
    _require_keys(summary, REQUIRED_SUMMARY_KEYS, "final_summary")
    for field in ["key_topics", "decisions", "action_items", "worth_noting", "open_questions", "required_search_report"]:
        if not isinstance(summary.get(field), list):
            raise ValueError("final_summary.{0} must be a list".format(field))

    for field in ["decisions", "action_items", "worth_noting", "open_questions"]:
        for item in summary.get(field, []):
            if not item.get("evidence_timestamps"):
                raise ValueError("final_summary.{0} item missing evidence_timestamps".format(field))
            if not item.get("support"):
                raise ValueError("final_summary.{0} item missing support".format(field))

    next_meeting = summary.get("next_meeting")
    if not isinstance(next_meeting, dict):
        raise ValueError("final_summary.next_meeting must be an object")
    if next_meeting.get("status") == "found" and not next_meeting.get("evidence_timestamps"):
        raise ValueError("found next_meeting must include evidence_timestamps")


def _require_keys(data: Dict[str, Any], keys: Iterable[str], label: str) -> None:
    for key in keys:
        if key not in data:
            raise ValueError("{0} missing required key: {1}".format(label, key))

