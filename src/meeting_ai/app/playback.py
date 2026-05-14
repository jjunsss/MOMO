"""Helpers for evidence-anchored playback in the result view.

The pipeline already records `evidence_timestamps` (HH:MM:SS strings) on
every key topic, decision, action, worth-noting item, and the
next-meeting block. This module pulls them out of
`evidence/final_summary.with_evidence.json` and translates them into
something the Streamlit UI can render with `st.video(start_time=…)`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ─── HH:MM:SS parsing ────────────────────────────────────────────────────


def hms_to_seconds(value: Any) -> Optional[int]:
    """Parse "HH:MM:SS" / "MM:SS" / numeric seconds into integer seconds.

    Returns ``None`` if the input cannot be interpreted. We accept some
    flexibility because earlier pipeline versions emitted slightly
    different formats and we don't want a single bad row to crash the
    whole result view.
    """
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return max(0, int(value))
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    parts = text.split(":")
    try:
        if len(parts) == 3:
            h, m, s = (int(p) for p in parts)
            return max(0, h * 3600 + m * 60 + s)
        if len(parts) == 2:
            m, s = (int(p) for p in parts)
            return max(0, m * 60 + s)
        return max(0, int(float(text)))
    except (TypeError, ValueError):
        return None


# ─── Anchored items extracted from final_summary.with_evidence.json ─────


@dataclass(frozen=True)
class TimestampRef:
    label: str  # what to show on the button, e.g. "00:12:34"
    seconds: int  # where to seek to in the media player


@dataclass(frozen=True)
class AnchoredItem:
    section: str  # i18n key suffix: "key_topics" | "decisions" | "actions" | "worth_noting" | "next_meeting"
    primary_text: str  # main text shown to the user
    secondary_text: str = ""  # subtitle / context line (optional)
    support: str = ""  # "strong" | "weak" | "inferred" | ""
    timestamps: Tuple[TimestampRef, ...] = field(default_factory=tuple)


def _make_refs(raw_list: Any) -> Tuple[TimestampRef, ...]:
    if not isinstance(raw_list, list):
        return tuple()
    out: List[TimestampRef] = []
    seen: set = set()
    for raw in raw_list:
        seconds = hms_to_seconds(raw)
        if seconds is None:
            continue
        label = str(raw).strip() if isinstance(raw, str) else format_seconds(seconds)
        key = (label, seconds)
        if key in seen:
            continue
        seen.add(key)
        out.append(TimestampRef(label=label, seconds=seconds))
    return tuple(out)


def format_seconds(seconds: int) -> str:
    seconds = max(0, int(seconds))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return "{0:02d}:{1:02d}:{2:02d}".format(h, m, s)


def extract_anchored_items(summary: Dict[str, Any]) -> List[AnchoredItem]:
    """Walk the with-evidence summary dict and return a flat anchored list.

    Sections are returned in display order: key_topics → decisions →
    action_items → worth_noting → next_meeting. Items with no usable
    timestamp are still returned (they just have an empty `timestamps`
    tuple) so the UI can show them without a jump button.
    """
    items: List[AnchoredItem] = []

    for topic in summary.get("key_topics", []) or []:
        if not isinstance(topic, dict):
            continue
        title = str(topic.get("title", "")).strip()
        body = str(topic.get("summary", "")).strip()
        items.append(
            AnchoredItem(
                section="key_topics",
                primary_text=title or body[:60] or "(제목 없음)",
                secondary_text=body if title else "",
                support="",
                timestamps=_make_refs(topic.get("evidence_timestamps")),
            )
        )

    for decision in summary.get("decisions", []) or []:
        if not isinstance(decision, dict):
            continue
        items.append(
            AnchoredItem(
                section="decisions",
                primary_text=str(decision.get("decision", "")).strip(),
                secondary_text=str(decision.get("rationale", "")).strip(),
                support=str(decision.get("support", "")).strip(),
                timestamps=_make_refs(decision.get("evidence_timestamps")),
            )
        )

    for action in summary.get("action_items", []) or []:
        if not isinstance(action, dict):
            continue
        owner = str(action.get("owner", "")).strip()
        deadline = str(action.get("deadline", "")).strip()
        meta_bits = [bit for bit in (owner, deadline) if bit and bit.lower() != "unknown"]
        items.append(
            AnchoredItem(
                section="actions",
                primary_text=str(action.get("task") or action.get("description", "")).strip(),
                secondary_text=" · ".join(meta_bits),
                support=str(action.get("support", "")).strip(),
                timestamps=_make_refs(action.get("evidence_timestamps")),
            )
        )

    for note in summary.get("worth_noting", []) or []:
        if not isinstance(note, dict):
            continue
        items.append(
            AnchoredItem(
                section="worth_noting",
                primary_text=str(note.get("note", "")).strip(),
                secondary_text=str(note.get("why_it_matters", "")).strip(),
                support=str(note.get("support", "")).strip(),
                timestamps=_make_refs(note.get("evidence_timestamps")),
            )
        )

    next_meeting = summary.get("next_meeting")
    if isinstance(next_meeting, dict) and next_meeting.get("status") not in {None, "not_found"}:
        agenda = next_meeting.get("agenda") or []
        agenda_text = "\n".join("• {0}".format(a) for a in agenda if a)
        date = str(next_meeting.get("date", "")).strip()
        time = str(next_meeting.get("time", "")).strip()
        meta_bits = [
            "📅 {0}".format(date) if date and date.lower() != "unknown" else "",
            "🕒 {0}".format(time) if time and time.lower() != "unknown" else "",
        ]
        meta_line = "  ".join(bit for bit in meta_bits if bit)
        items.append(
            AnchoredItem(
                section="next_meeting",
                primary_text=meta_line or "(일정 미정)",
                secondary_text=agenda_text,
                support=str(next_meeting.get("support", "")).strip(),
                timestamps=_make_refs(next_meeting.get("evidence_timestamps")),
            )
        )

    return items


# ─── Media file resolution ──────────────────────────────────────────────

# Suffixes Streamlit's HTML5 player will accept out of the box. We pick a
# liberal set and let st.video / st.audio decide what to do.
PLAYABLE_VIDEO_SUFFIXES = {".mp4", ".mkv", ".mov", ".webm", ".m4v"}
PLAYABLE_AUDIO_SUFFIXES = {".mp3", ".m4a", ".wav", ".ogg"}


def find_run_media(
    summary: Dict[str, Any], run_dir: Path, videos_dir: Path
) -> Optional[Path]:
    """Locate the original media file for a run.

    We try, in order:
    1. ``summary["source_file"]`` exactly as recorded.
    2. The same basename inside ``videos_dir``.
    3. The cached ``source/audio.wav`` inside the run directory (so even
       runs whose original recording was deleted can still play audio).

    Returns ``None`` if nothing playable exists.
    """
    source = summary.get("source_file")
    if isinstance(source, str) and source:
        path = Path(source)
        if path.exists() and _is_playable(path):
            return path
        # Try the same basename under videos_dir
        candidate = videos_dir / path.name
        if candidate.exists() and _is_playable(candidate):
            return candidate

    cached_audio = run_dir / "source" / "audio.wav"
    if cached_audio.exists():
        return cached_audio
    return None


def _is_playable(path: Path) -> bool:
    suffix = path.suffix.lower()
    return suffix in PLAYABLE_VIDEO_SUFFIXES or suffix in PLAYABLE_AUDIO_SUFFIXES


def is_audio_only(path: Path) -> bool:
    return path.suffix.lower() in PLAYABLE_AUDIO_SUFFIXES


# ─── Convenience loader ────────────────────────────────────────────────


def load_with_evidence(run_dir: Path) -> Optional[Dict[str, Any]]:
    """Read the with-evidence summary from a run directory, if present."""
    path = run_dir / "evidence" / "final_summary.with_evidence.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
