"""Synthesize chunk analyses into a final summary draft."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from meeting_ai.utils.time import format_duration, format_seconds


TOPIC_KEYWORDS = [
    "가우션",
    "gaussian",
    "smpl",
    "segmentation",
    "세그멘테이션",
    "컨시스텐",
    "consistency",
    "텍스트",
    "레이블",
    "registration",
    "레지스트",
    "업리프팅",
    "feature",
    "피처",
    "sds",
    "loss",
    "로스",
    "에디팅",
    "편집",
    "데모",
    "선호",
    "중요",
    "결정",
    "다음 주",
]


def synthesize_summary(
    transcript: Dict[str, Any],
    chunks: List[Dict[str, Any]],
    chunk_analyses: List[Dict[str, Any]],
    required_search_report: List[Dict[str, Any]],
    profile: Dict[str, Any],
    run_id: str,
    source_file: str,
    rendering: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    kept = [analysis for analysis in chunk_analyses if analysis.get("classification") == "kept"]
    decisions = [item for analysis in kept for item in analysis.get("decisions", [])]
    actions = [item for analysis in kept for item in analysis.get("action_items", [])]
    next_mentions = [item for analysis in kept for item in analysis.get("next_meeting_mentions", [])]
    worth_noting = _dedupe_items(
        [item for analysis in kept for item in analysis.get("worth_noting_candidates", [])],
        "note",
    )
    questions = _dedupe_items(
        [item for analysis in kept for item in analysis.get("open_questions", [])],
        "question",
    )

    title = transcript.get("title") or profile.get("meeting_profile", {}).get("default_title", "Zoom Meeting Summary")
    key_topics = _build_key_topics(chunks, kept, profile.get("custom_topics", []))

    return {
        "meeting_id": transcript.get("meeting_id", run_id),
        "title": title,
        "date": "unknown",
        "source_file": source_file,
        "duration": format_duration(float(transcript.get("duration_sec", 0.0))),
        "tldr": _build_tldr(decisions, actions, next_mentions, worth_noting),
        "executive_summary": _build_executive_summary(key_topics, decisions, actions),
        "key_topics": key_topics,
        "decisions": [_decision(item) for item in decisions],
        "action_items": [_action(item) for item in actions],
        "next_meeting": _next_meeting(next_mentions),
        "worth_noting": [_worth_note(item) for item in worth_noting],
        "open_questions": [_question(item) for item in questions],
        "required_search_report": required_search_report,
        "metadata": {
            "model_info": {"provider": "deterministic_mvp", "model": "rule_based"},
            "pipeline_version": "0.1.0",
            "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "chunk_count": len(chunks),
            "kept_chunk_count": len(kept),
            "skipped_chunk_count": len(chunks) - len(kept),
            "output_sections": profile.get("output_sections", []),
            "rendering": rendering or {},
        },
    }


def _build_key_topics(
    chunks: List[Dict[str, Any]], kept: List[Dict[str, Any]], custom_topics: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    kept_ids = {analysis["chunk_id"] for analysis in kept}
    topics: List[Dict[str, Any]] = []
    for index, chunk in enumerate(chunks, start=1):
        if chunk["chunk_id"] not in kept_ids:
            continue
        selected = _representative_segments(chunk.get("segments", []), custom_topics)
        if not selected:
            continue
        supporting_points = [segment["text"] for segment in selected]
        evidence = [format_seconds(float(segment["start"])) for segment in selected]
        title, description = _topic_title(chunk.get("text", ""), index, custom_topics)
        topics.append(
            {
                "topic_id": "topic_{0:03d}".format(index),
                "title": title,
                "summary": " ".join(supporting_points[:3]),
                "why_it_matters": description or _why_it_matters(title),
                "supporting_points": supporting_points,
                "evidence_timestamps": evidence,
                "source_chunks": [chunk["chunk_id"]],
            }
        )
    return topics


def _representative_segments(
    segments: List[Dict[str, Any]], custom_topics: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    scored = []
    for order, segment in enumerate(segments):
        text = str(segment.get("text", "")).strip()
        if len(text) < 12:
            continue
        score = _segment_score(text, custom_topics)
        scored.append((score, order, segment))

    strong = [item for item in scored if item[0] > 0]
    if strong:
        picked = sorted(sorted(strong, key=lambda item: (-item[0], item[1]))[:4], key=lambda item: item[1])
        return [item[2] for item in picked]

    fallback = sorted(scored[:3], key=lambda item: item[1])
    return [item[2] for item in fallback]


def _segment_score(text: str, custom_topics: List[Dict[str, Any]]) -> int:
    lowered = text.lower()
    score = 0
    topic_keywords = list(TOPIC_KEYWORDS)
    for topic in custom_topics:
        topic_keywords.extend(topic.get("aliases", []))
    for keyword in topic_keywords:
        if keyword.lower() in lowered:
            score += 2
    if "?" in text or "까요" in text or "나요" in text:
        score += 1
    if "했습니다" in text or "됩니다" in text or "같습니다" in text:
        score += 1
    return score


def _topic_title(
    chunk_text: str, index: int, custom_topics: List[Dict[str, Any]]
) -> tuple:
    lowered = chunk_text.lower()
    for topic in custom_topics:
        aliases = [str(alias).lower() for alias in topic.get("aliases", [])]
        if any(alias and alias in lowered for alias in aliases):
            return topic.get("label", "사용자 지정 토픽"), topic.get("description", "")
    if ("smpl" in lowered or "가우션" in lowered) and index <= 2:
        return "Human Gaussian / SMPL-X 구성", ""
    if "세그멘테이션" in lowered or "레이블" in lowered:
        return "2D 세그멘테이션과 텍스트 레이블", ""
    if "레지스트" in lowered or "registration" in lowered:
        return "3D Gaussian 레지스트레이션", ""
    if "업리프팅" in lowered or "피처" in lowered or "feature" in lowered:
        return "피처 업리프팅과 컨시스턴시", ""
    if "sds" in lowered or "로스" in lowered or "편집" in lowered or "에디팅" in lowered:
        return "편집 범위와 SDS 기반 접근", ""
    if "데모" in lowered or "선호" in lowered or "다음 주" in lowered:
        return "데모 방향과 후속 미팅", ""
    return "논의 구간 {0}".format(index), ""


def _why_it_matters(title: str) -> str:
    if "Gaussian" in title or "SMPL" in title:
        return "3D human representation의 입력 품질과 이후 semantic registration 품질을 좌우합니다."
    if "세그멘테이션" in title:
        return "여러 view에서 semantic label을 일관되게 유지해야 3D로 올린 뒤 의미가 깨지지 않습니다."
    if "레지스트" in title:
        return "2D label을 3D Gaussian으로 옮기는 핵심 연결 단계입니다."
    if "업리프팅" in title:
        return "2D/3D feature consistency와 편집 가능성을 판단하는 기준입니다."
    if "편집" in title:
        return "방법의 contribution을 어느 범위까지 주장할 수 있는지와 직접 연결됩니다."
    if "데모" in title:
        return "다음 실험과 발표에서 보여줄 결과물의 형태를 정하는 데 필요합니다."
    return "회의 후속 작업과 판단 기준을 정리하는 데 필요합니다."


def _build_tldr(
    decisions: List[Dict[str, Any]],
    actions: List[Dict[str, Any]],
    next_mentions: List[Dict[str, Any]],
    worth_noting: List[Dict[str, Any]],
) -> str:
    parts: List[str] = []
    if decisions:
        parts.append("결정사항 {0}건".format(len(decisions)))
    if actions:
        parts.append("액션아이템 {0}건".format(len(actions)))
    if next_mentions:
        parts.append("다음 미팅 언급 있음")
    if worth_noting:
        parts.append("주의 깊게 볼 맥락 {0}건".format(len(worth_noting)))
    return ", ".join(parts) if parts else "명확한 결정사항이나 액션아이템은 감지되지 않았습니다."


def _build_executive_summary(
    key_topics: List[Dict[str, Any]], decisions: List[Dict[str, Any]], actions: List[Dict[str, Any]]
) -> str:
    if key_topics:
        return key_topics[0]["summary"]
    if decisions:
        return decisions[0].get("decision", "")
    if actions:
        return actions[0].get("task", "")
    return "요약할 핵심 논의가 충분히 감지되지 않았습니다."


def _decision(item: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "decision": item.get("decision", ""),
        "rationale": "chunk-level evidence",
        "evidence_timestamps": item.get("evidence_timestamps", []),
        "support": "weak",
    }


def _action(item: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "task": item.get("task", ""),
        "owner": item.get("owner", "unknown"),
        "deadline": item.get("deadline", "unknown"),
        "priority": item.get("priority", "unknown"),
        "evidence_timestamps": item.get("evidence_timestamps", []),
        "support": "weak",
    }


def _next_meeting(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not items:
        return {
            "status": "not_found",
            "date": "unknown",
            "time": "unknown",
            "agenda": [],
            "preparation": [],
            "evidence_timestamps": [],
            "support": "none",
        }
    evidence = sorted({ts for item in items for ts in item.get("evidence_timestamps", [])})
    return {
        "status": "found",
        "date": items[0].get("date", "unknown"),
        "time": items[0].get("time", "unknown"),
        "agenda": [item.get("agenda", "") for item in items if item.get("agenda")],
        "preparation": [item.get("preparation", "") for item in items if item.get("preparation") not in {None, "unknown"}],
        "evidence_timestamps": evidence,
        "support": "weak",
    }


def _worth_note(item: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "note": item.get("note", ""),
        "why_it_matters": item.get("why_it_matters", ""),
        "related_topic": item.get("related_topic", "general"),
        "importance": "medium",
        "evidence_timestamps": item.get("evidence_timestamps", []),
        "support": "weak",
    }


def _question(item: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "question": item.get("question", ""),
        "context": item.get("context", ""),
        "evidence_timestamps": item.get("evidence_timestamps", []),
        "support": "weak",
    }


def _dedupe_items(items: List[Dict[str, Any]], text_key: str) -> List[Dict[str, Any]]:
    seen = {}
    ordered: List[Dict[str, Any]] = []
    for item in items:
        key = _normalize_text(item.get(text_key, ""))
        if not key:
            continue
        if key in seen:
            existing = seen[key]
            existing["evidence_timestamps"] = sorted(
                set(existing.get("evidence_timestamps", []) + item.get("evidence_timestamps", []))
            )
            continue
        seen[key] = item
        ordered.append(item)
    return ordered


def _normalize_text(value: str) -> str:
    return " ".join(str(value).lower().split())
