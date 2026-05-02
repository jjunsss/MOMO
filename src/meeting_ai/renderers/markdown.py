"""Deterministic Markdown rendering."""

from __future__ import annotations

from typing import Any, Dict, List


def render_summary_markdown(summary: Dict[str, Any]) -> str:
    lines: List[str] = []
    metadata = summary.get("metadata", {})
    rendering = metadata.get("rendering", {}) or {}
    show_skipped_stats = bool(rendering.get("include_skipped_chunk_stats", True))

    lines.append("# {0}".format(summary.get("title", "Meeting Summary")))
    lines.append("")
    lines.append("- **Date**: {0}".format(summary.get("date", "unknown")))
    lines.append("- **Source**: {0}".format(summary.get("source_file", "unknown")))
    lines.append("- **Duration**: {0}".format(summary.get("duration", "unknown")))
    lines.append("- **Pipeline**: {0}".format(metadata.get("pipeline_version", "unknown")))
    lines.append("")

    if _enabled(metadata, "tldr"):
        _section(lines, _title(metadata, "tldr", "TL;DR"))
        lines.append(summary.get("tldr", ""))
        lines.append("")

    if _enabled(metadata, "executive_summary"):
        _section(lines, _title(metadata, "executive_summary", "핵심 요약"))
        lines.append(summary.get("executive_summary", ""))
        lines.append("")

    if _enabled(metadata, "key_topics"):
        _render_key_topics(lines, summary.get("key_topics", []), _title(metadata, "key_topics", "핵심 논의"))
    if _enabled(metadata, "decisions"):
        _render_decisions(lines, summary.get("decisions", []), _title(metadata, "decisions", "결정사항"))
    if _enabled(metadata, "action_items"):
        _render_actions(lines, summary.get("action_items", []), _title(metadata, "action_items", "Action Items"))
    if _enabled(metadata, "next_meeting"):
        _render_next_meeting(lines, summary.get("next_meeting", {}), _title(metadata, "next_meeting", "다음 미팅 / Follow-up"))
    if _enabled(metadata, "worth_noting"):
        _render_worth_noting(lines, summary.get("worth_noting", []), _title(metadata, "worth_noting", "Worth Noting"))
    if _enabled(metadata, "open_questions"):
        _render_questions(lines, summary.get("open_questions", []), _title(metadata, "open_questions", "Open Questions"))
    if _enabled(metadata, "required_search_report"):
        _render_required_report(
            lines,
            summary.get("required_search_report", []),
            _title(metadata, "required_search_report", "사용자 필수 탐색 항목 결과"),
        )
    if _enabled(metadata, "appendix"):
        _render_appendix(lines, metadata, _title(metadata, "appendix", "Appendix"), show_skipped_stats)
    return "\n".join(lines).rstrip() + "\n"


def _section(lines: List[str], title: str) -> None:
    lines.append("## {0}".format(title))
    lines.append("")


def _render_key_topics(lines: List[str], topics: List[Dict[str, Any]], title: str) -> None:
    _section(lines, title)
    if not topics:
        lines.append("명확한 핵심 논의가 감지되지 않았습니다.")
        lines.append("")
        return
    lines.append("| 주제 | 요약 | 왜 중요한가 |")
    lines.append("|---|---|---|")
    for topic in topics:
        lines.append(
            "| {0} | {1} | {2} |".format(
                _cell(topic.get("title", "")),
                _cell(topic.get("summary", "")),
                _cell(topic.get("why_it_matters", "")),
            )
        )
    lines.append("")


def _render_decisions(lines: List[str], decisions: List[Dict[str, Any]], title: str) -> None:
    _section(lines, title)
    if not decisions:
        lines.append("명시적으로 확인된 결정사항은 없습니다.")
        lines.append("")
        return
    lines.append("| 결정 | 맥락 |")
    lines.append("|---|---|")
    for item in decisions:
        lines.append(
            "| {0} | {1} |".format(
                _cell(item.get("decision", "")),
                _cell(item.get("rationale", "")),
            )
        )
    lines.append("")


def _render_actions(
    lines: List[str], actions: List[Dict[str, Any]], title: str
) -> None:
    _section(lines, title)
    if not actions:
        lines.append("명시적으로 확인된 액션아이템은 없습니다.")
        lines.append("")
        return
    for item in actions:
        suffix_parts = []
        owner = _known_text(item.get("owner"))
        deadline = _known_text(item.get("deadline"))
        if owner:
            suffix_parts.append("owner: {0}".format(owner))
        if deadline:
            suffix_parts.append("deadline: {0}".format(deadline))
        suffix = " ({0})".format(", ".join(suffix_parts)) if suffix_parts else ""
        lines.append("- [ ] {0}{1}".format(item.get("task", ""), suffix))
    lines.append("")


def _render_next_meeting(
    lines: List[str], next_meeting: Dict[str, Any], title: str
) -> None:
    _section(lines, title)
    if next_meeting.get("status") != "found":
        lines.append("다음 미팅 일정이나 agenda는 명시적으로 언급되지 않았습니다.")
        lines.append("")
        return
    lines.append("| 상태 | 날짜 | 시간 | Agenda |")
    lines.append("|---|---|---|---|")
    lines.append(
        "| {0} | {1} | {2} | {3} |".format(
            _cell(next_meeting.get("status", "")),
            _cell(next_meeting.get("date", "unknown")),
            _cell(next_meeting.get("time", "unknown")),
            _cell("; ".join(next_meeting.get("agenda", []))),
        )
    )
    lines.append("")


def _render_worth_noting(lines: List[str], notes: List[Dict[str, Any]], title: str) -> None:
    _section(lines, title)
    if not notes:
        lines.append("별도 보존할 만한 맥락은 감지되지 않았습니다.")
        lines.append("")
        return
    for item in notes:
        lines.append(
            "- {0} - {1}".format(
                item.get("note", ""),
                item.get("why_it_matters", ""),
            )
        )
    lines.append("")


def _render_questions(lines: List[str], questions: List[Dict[str, Any]], title: str) -> None:
    _section(lines, title)
    if not questions:
        lines.append("열린 질문은 감지되지 않았습니다.")
        lines.append("")
        return
    for item in questions:
        lines.append("- {0}".format(item.get("question", "")))
    lines.append("")


def _render_required_report(
    lines: List[str],
    report: List[Dict[str, Any]],
    title: str,
) -> None:
    _section(lines, title)
    headers = ["항목", "상태", "요약"]
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("|" + "|".join("---" for _ in headers) + "|")
    for item in report:
        cells = [
            _cell(item.get("label", "")),
            _cell(item.get("status", "")),
            _cell(item.get("summary", "")),
        ]
        lines.append("| " + " | ".join(cells) + " |")
    lines.append("")


def _render_appendix(
    lines: List[str], metadata: Dict[str, Any], title: str, show_skipped_stats: bool
) -> None:
    _section(lines, title)
    lines.append("- Chunk count: {0}".format(metadata.get("chunk_count", 0)))
    if show_skipped_stats:
        lines.append("- Kept chunks: {0}".format(metadata.get("kept_chunk_count", 0)))
        lines.append("- Skipped chunks: {0}".format(metadata.get("skipped_chunk_count", 0)))


def _cell(value: str) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ").strip()


def _known_text(value: Any) -> str:
    text = str(value or "").strip()
    if text.lower() in {"", "unknown", "none", "null", "n/a", "na", "-"}:
        return ""
    if text in {"미정", "미지정", "알 수 없음", "없음"}:
        return ""
    return text


def _enabled(metadata: Dict[str, Any], section_id: str) -> bool:
    sections = metadata.get("output_sections") or []
    if not sections:
        return True
    for section in sections:
        if section.get("id") == section_id:
            return bool(section.get("enabled", True))
    return True


def _title(metadata: Dict[str, Any], section_id: str, fallback: str) -> str:
    for section in metadata.get("output_sections") or []:
        if section.get("id") == section_id and section.get("title"):
            return str(section["title"])
    return fallback
