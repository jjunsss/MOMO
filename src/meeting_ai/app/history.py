"""Scan the runs/ directory to surface past meeting results."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional


@dataclass(frozen=True)
class RunRecord:
    run_id: str
    run_dir: Path
    title: str
    finished_at: Optional[datetime]
    final_summary_md: Optional[Path]
    evidence_md: Optional[Path]
    transcript_md: Optional[Path]
    final_summary_json: Optional[Path]

    @property
    def display_label(self) -> str:
        when = self.finished_at.strftime("%Y-%m-%d %H:%M") if self.finished_at else "—"
        return "{0}  ·  {1}".format(when, self.title or self.run_id)


def list_runs(runs_dir: Path) -> List[RunRecord]:
    if not runs_dir.exists():
        return []
    records: List[RunRecord] = []
    for entry in sorted(runs_dir.iterdir()):
        if not entry.is_dir():
            continue
        record = _load_record(entry)
        if record is not None:
            records.append(record)
    records.sort(
        key=lambda r: (r.finished_at or datetime.fromtimestamp(0), r.run_id),
        reverse=True,
    )
    return records


def _load_record(run_dir: Path) -> Optional[RunRecord]:
    summary_md = run_dir / "summaries" / "final_summary.md"
    summary_json = run_dir / "summaries" / "final_summary.json"
    evidence_md = run_dir / "evidence" / "summary_evidence.md"
    transcript_md = run_dir / "transcript" / "normalized_transcript.md"

    if not summary_md.exists():
        return None

    title = _extract_title(summary_json) or run_dir.name
    finished_at = _safe_mtime(summary_md)

    return RunRecord(
        run_id=run_dir.name,
        run_dir=run_dir,
        title=title,
        finished_at=finished_at,
        final_summary_md=summary_md,
        evidence_md=evidence_md if evidence_md.exists() else None,
        transcript_md=transcript_md if transcript_md.exists() else None,
        final_summary_json=summary_json if summary_json.exists() else None,
    )


def _extract_title(summary_json: Path) -> Optional[str]:
    if not summary_json.exists():
        return None
    try:
        data = json.loads(summary_json.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    title = data.get("title")
    if isinstance(title, str) and title.strip():
        return title.strip()
    metadata = data.get("metadata")
    if isinstance(metadata, dict):
        candidate = metadata.get("meeting_title") or metadata.get("title")
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
    return None


def _safe_mtime(path: Path) -> Optional[datetime]:
    try:
        return datetime.fromtimestamp(path.stat().st_mtime)
    except OSError:
        return None
