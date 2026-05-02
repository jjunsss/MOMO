"""Time formatting helpers."""

from __future__ import annotations


def format_seconds(seconds: float) -> str:
    total = max(0, int(seconds))
    hours = total // 3600
    minutes = (total % 3600) // 60
    secs = total % 60
    return "{0:02d}:{1:02d}:{2:02d}".format(hours, minutes, secs)


def format_duration(seconds: float) -> str:
    return format_seconds(seconds)

