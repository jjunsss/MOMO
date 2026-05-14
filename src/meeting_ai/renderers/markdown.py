"""Deterministic Markdown rendering."""

from __future__ import annotations

from typing import Any, Dict, List


SECTION_TITLES = {
    "ko": {
        "tldr": "TL;DR",
        "executive_summary": "핵심 요약",
        "key_topics": "핵심 논의",
        "decisions": "결정사항",
        "action_items": "Action Items",
        "next_meeting": "다음 미팅 / Follow-up",
        "worth_noting": "Worth Noting",
        "open_questions": "Open Questions",
        "required_search_report": "사용자 필수 탐색 항목 결과",
        "appendix": "Appendix",
    },
    "en": {
        "tldr": "TL;DR",
        "executive_summary": "Executive Summary",
        "key_topics": "Key Topics",
        "decisions": "Decisions",
        "action_items": "Action Items",
        "next_meeting": "Next Meeting / Follow-up",
        "worth_noting": "Worth Noting",
        "open_questions": "Open Questions",
        "required_search_report": "Required Search Results",
        "appendix": "Appendix",
    },
}

LABELS = {
    "ko": {
        "date": "날짜",
        "source": "원본",
        "duration": "길이",
        "pipeline": "파이프라인",
        "no_key_topics": "명확한 핵심 논의가 감지되지 않았습니다.",
        "key_topic_headers": ["주제", "요약", "왜 중요한가"],
        "no_decisions": "명시적으로 확인된 결정사항은 없습니다.",
        "decision_headers": ["결정", "맥락"],
        "no_actions": "명시적으로 확인된 액션아이템은 없습니다.",
        "owner": "담당",
        "deadline": "마감",
        "no_next_meeting": "다음 미팅 일정이나 agenda는 명시적으로 언급되지 않았습니다.",
        "next_meeting_headers": ["상태", "날짜", "시간", "Agenda"],
        "no_worth_noting": "별도 보존할 만한 맥락은 감지되지 않았습니다.",
        "no_questions": "열린 질문은 감지되지 않았습니다.",
        "required_headers": ["항목", "상태", "요약"],
    },
    "en": {
        "date": "Date",
        "source": "Source",
        "duration": "Duration",
        "pipeline": "Pipeline",
        "no_key_topics": "No clear key topics were detected.",
        "key_topic_headers": ["Topic", "Summary", "Why it matters"],
        "no_decisions": "No explicit decisions were identified.",
        "decision_headers": ["Decision", "Context"],
        "no_actions": "No explicit action items were identified.",
        "owner": "owner",
        "deadline": "deadline",
        "no_next_meeting": "No next meeting schedule or agenda was explicitly mentioned.",
        "next_meeting_headers": ["Status", "Date", "Time", "Agenda"],
        "no_worth_noting": "No additional worth-noting context was detected.",
        "no_questions": "No open questions were detected.",
        "required_headers": ["Item", "Status", "Summary"],
    },
}


def render_summary_markdown(summary: Dict[str, Any]) -> str:
    lines: List[str] = []
    metadata = summary.get("metadata", {})
    rendering = metadata.get("rendering", {}) or {}
    lang = _language(metadata)
    labels = LABELS[lang]
    show_skipped_stats = bool(rendering.get("include_skipped_chunk_stats", True))

    lines.append("# {0}".format(summary.get("title", "Meeting Summary")))
    lines.append("")
    lines.append("- **{0}**: {1}".format(labels["date"], summary.get("date", "unknown")))
    lines.append("- **{0}**: {1}".format(labels["source"], summary.get("source_file", "unknown")))
    lines.append("- **{0}**: {1}".format(labels["duration"], summary.get("duration", "unknown")))
    lines.append("- **{0}**: {1}".format(labels["pipeline"], metadata.get("pipeline_version", "unknown")))
    lines.append("")

    if _enabled(metadata, "tldr"):
        _section(lines, _title(metadata, "tldr", lang))
        lines.append(summary.get("tldr", ""))
        lines.append("")

    if _enabled(metadata, "executive_summary"):
        _section(lines, _title(metadata, "executive_summary", lang))
        lines.append(summary.get("executive_summary", ""))
        lines.append("")

    if _enabled(metadata, "key_topics"):
        _render_key_topics(lines, summary.get("key_topics", []), _title(metadata, "key_topics", lang), labels)
    if _enabled(metadata, "decisions"):
        _render_decisions(lines, summary.get("decisions", []), _title(metadata, "decisions", lang), labels)
    if _enabled(metadata, "action_items"):
        _render_actions(lines, summary.get("action_items", []), _title(metadata, "action_items", lang), labels)
    if _enabled(metadata, "next_meeting"):
        _render_next_meeting(lines, summary.get("next_meeting", {}), _title(metadata, "next_meeting", lang), labels)
    if _enabled(metadata, "worth_noting"):
        _render_worth_noting(lines, summary.get("worth_noting", []), _title(metadata, "worth_noting", lang), labels)
    if _enabled(metadata, "open_questions"):
        _render_questions(lines, summary.get("open_questions", []), _title(metadata, "open_questions", lang), labels)
    if _enabled(metadata, "required_search_report"):
        _render_required_report(
            lines,
            summary.get("required_search_report", []),
            _title(metadata, "required_search_report", lang),
            labels,
        )
    if _enabled(metadata, "appendix"):
        _render_appendix(lines, metadata, _title(metadata, "appendix", lang), show_skipped_stats)
    return "\n".join(lines).rstrip() + "\n"


def _section(lines: List[str], title: str) -> None:
    lines.append("## {0}".format(title))
    lines.append("")


def _render_key_topics(
    lines: List[str],
    topics: List[Dict[str, Any]],
    title: str,
    labels: Dict[str, Any],
) -> None:
    _section(lines, title)
    if not topics:
        lines.append(labels["no_key_topics"])
        lines.append("")
        return
    headers = labels["key_topic_headers"]
    _table_header(lines, headers)
    for topic in topics:
        lines.append(
            "| {0} | {1} | {2} |".format(
                _cell(topic.get("title", "")),
                _cell(topic.get("summary", "")),
                _cell(topic.get("why_it_matters", "")),
            )
        )
    lines.append("")


def _render_decisions(
    lines: List[str],
    decisions: List[Dict[str, Any]],
    title: str,
    labels: Dict[str, Any],
) -> None:
    _section(lines, title)
    if not decisions:
        lines.append(labels["no_decisions"])
        lines.append("")
        return
    _table_header(lines, labels["decision_headers"])
    for item in decisions:
        lines.append(
            "| {0} | {1} |".format(
                _cell(item.get("decision", "")),
                _cell(item.get("rationale", "")),
            )
        )
    lines.append("")


def _render_actions(
    lines: List[str],
    actions: List[Dict[str, Any]],
    title: str,
    labels: Dict[str, Any],
) -> None:
    _section(lines, title)
    if not actions:
        lines.append(labels["no_actions"])
        lines.append("")
        return
    for item in actions:
        suffix_parts = []
        owner = _known_text(item.get("owner"))
        deadline = _known_text(item.get("deadline"))
        if owner:
            suffix_parts.append("{0}: {1}".format(labels["owner"], owner))
        if deadline:
            suffix_parts.append("{0}: {1}".format(labels["deadline"], deadline))
        suffix = " ({0})".format(", ".join(suffix_parts)) if suffix_parts else ""
        lines.append("- [ ] {0}{1}".format(item.get("task", ""), suffix))
    lines.append("")


def _render_next_meeting(
    lines: List[str],
    next_meeting: Dict[str, Any],
    title: str,
    labels: Dict[str, Any],
) -> None:
    _section(lines, title)
    if next_meeting.get("status") != "found":
        lines.append(labels["no_next_meeting"])
        lines.append("")
        return
    _table_header(lines, labels["next_meeting_headers"])
    lines.append(
        "| {0} | {1} | {2} | {3} |".format(
            _cell(next_meeting.get("status", "")),
            _cell(next_meeting.get("date", "unknown")),
            _cell(next_meeting.get("time", "unknown")),
            _cell("; ".join(next_meeting.get("agenda", []))),
        )
    )
    lines.append("")


def _render_worth_noting(
    lines: List[str],
    notes: List[Dict[str, Any]],
    title: str,
    labels: Dict[str, Any],
) -> None:
    _section(lines, title)
    if not notes:
        lines.append(labels["no_worth_noting"])
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


def _render_questions(
    lines: List[str],
    questions: List[Dict[str, Any]],
    title: str,
    labels: Dict[str, Any],
) -> None:
    _section(lines, title)
    if not questions:
        lines.append(labels["no_questions"])
        lines.append("")
        return
    for item in questions:
        lines.append("- {0}".format(item.get("question", "")))
    lines.append("")


def _render_required_report(
    lines: List[str],
    report: List[Dict[str, Any]],
    title: str,
    labels: Dict[str, Any],
) -> None:
    _section(lines, title)
    headers = labels["required_headers"]
    _table_header(lines, headers)
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


def _table_header(lines: List[str], headers: List[str]) -> None:
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("|" + "|".join("---" for _ in headers) + "|")


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


def _language(metadata: Dict[str, Any]) -> str:
    rendering = metadata.get("rendering") or {}
    value = str(rendering.get("output_language") or "ko").lower().strip()
    return "en" if value.startswith("en") else "ko"


def _title(metadata: Dict[str, Any], section_id: str, lang: str) -> str:
    if lang == "en":
        return SECTION_TITLES["en"].get(section_id, section_id.replace("_", " ").title())
    for section in metadata.get("output_sections") or []:
        if section.get("id") == section_id and section.get("title"):
            return str(section["title"])
    return SECTION_TITLES["ko"].get(section_id, section_id)
