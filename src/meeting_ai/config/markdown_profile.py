"""Parse user-editable Markdown profile files."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from meeting_ai.config.defaults import (
    ASR_PRESETS,
    default_extraction_keywords,
    default_models_config,
    default_pipeline_config,
    default_user_profile,
)


CHECKBOX_RE = re.compile(r"^-\s+\[(?P<checked>[xX ])\]\s+(?P<body>.+)$")
BULLET_RE = re.compile(r"^-\s+(?P<body>.+)$")

KEYWORD_SECTIONS: Dict[str, str] = {
    "decision keywords": "decision",
    "uncertain decision markers": "uncertain_decision",
    "action keywords": "action",
    "next meeting keywords": "next_meeting",
    "worth noting keywords": "worth_noting",
    "question keywords": "question",
}

RENDERING_TOGGLES = {
    "include_timestamps",
    "include_evidence_snippets",
    "include_skipped_chunk_stats",
    "write_evidence_report",
    "write_transcript_markdown",
    "write_chunk_analysis_jsonl",
}

RENDERING_NUMBERS = {
    "worth_noting_max",
    "key_topics_max",
    "max_per_slot_per_chunk",
    "max_items_per_slot",
    "single_pass_token_limit",
    "direct_summary_max_tokens",
}

RENDERING_BOOLS_FROM_SETTINGS = {
    "enable_critique",
}


def load_markdown_profile(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError("Markdown profile does not exist: {0}".format(path))

    sections = _split_sections(path.read_text(encoding="utf-8"))
    settings = _parse_settings(sections.get("settings", []))
    output_sections = _parse_output_sections(sections.get("output sections", []))
    required_items = _parse_required_items(sections.get("required search items", []))
    custom_topics = _parse_custom_topics(sections.get("custom topics", []))
    verification_terms = _parse_verification_terms(sections.get("verification terms", []))
    rendering_overrides = _parse_rendering_toggles(sections.get("rendering", []))
    keyword_overrides = _parse_keyword_sections(sections)

    profile = default_user_profile()
    profile["meeting_profile"] = {
        "default_title": settings.get("title") or "Auto Meeting Summary",
        "output_language": settings.get("output_language") or "ko",
        "tone": settings.get("tone") or "professional_research_notes",
    }
    if output_sections:
        profile["output_sections"] = output_sections
    if required_items:
        profile["required_search_items"] = required_items
    profile["custom_topics"] = custom_topics
    profile["verification_terms"] = verification_terms

    pipeline_config = default_pipeline_config()
    pipeline_config["chunking"]["target_minutes"] = _number(settings.get("chunk_target_minutes"), 6)
    pipeline_config["chunking"]["max_minutes"] = _number(settings.get("chunk_max_minutes"), 10)
    pipeline_config["chunking"]["overlap_seconds"] = int(_number(settings.get("chunk_overlap_seconds"), 30))
    if keyword_overrides:
        merged = default_extraction_keywords()
        merged.update(keyword_overrides)
        pipeline_config["extraction"]["keywords"] = merged
    pipeline_config["rendering"].update(rendering_overrides)
    for number_key in RENDERING_NUMBERS:
        if settings.get(number_key):
            pipeline_config["rendering"][number_key] = int(_number(settings[number_key], 0))
    for bool_key in RENDERING_BOOLS_FROM_SETTINGS:
        if settings.get(bool_key) is not None and settings.get(bool_key) != "":
            pipeline_config["rendering"][bool_key] = _bool(settings[bool_key], True)
    if settings.get("llm_summary_mode"):
        pipeline_config["rendering"]["llm_summary_mode"] = settings["llm_summary_mode"]

    models_config = default_models_config()
    asr_model = settings.get("asr_model")
    asr_preset = (settings.get("asr_preset") or "").lower().strip()
    if not asr_model and asr_preset in ASR_PRESETS:
        asr_model = ASR_PRESETS[asr_preset]
    if asr_model:
        models_config["asr"]["model"] = asr_model
    if settings.get("asr_language"):
        models_config["asr"]["language"] = settings["asr_language"]
    if settings.get("asr_device"):
        models_config["asr"]["device"] = settings["asr_device"]
    if settings.get("asr_condition_on_previous_text"):
        models_config["asr"]["condition_on_previous_text"] = _bool(
            settings["asr_condition_on_previous_text"],
            False,
        )
    for setting_key, config_key, fallback in [
        ("asr_temperature", "temperature", 0.0),
        ("asr_no_speech_threshold", "no_speech_threshold", 0.6),
        ("asr_logprob_threshold", "logprob_threshold", -1.0),
        ("asr_compression_ratio_threshold", "compression_ratio_threshold", 2.4),
    ]:
        if settings.get(setting_key):
            models_config["asr"][config_key] = _number(settings[setting_key], fallback)

    llm_provider = (settings.get("llm_provider") or "").strip()
    if llm_provider:
        models_config["llm"]["provider"] = llm_provider
    if settings.get("llm_model"):
        models_config["llm"]["model"] = settings["llm_model"]
    if settings.get("llm_base_url"):
        models_config["llm"]["base_url"] = settings["llm_base_url"]
    if settings.get("llm_temperature"):
        models_config["llm"]["temperature"] = _number(settings["llm_temperature"], 0.1)
    if settings.get("llm_request_timeout_seconds"):
        models_config["llm"]["request_timeout_seconds"] = _number(
            settings["llm_request_timeout_seconds"], 600
        )
    if settings.get("llm_num_ctx"):
        models_config["llm"]["num_ctx"] = int(_number(settings["llm_num_ctx"], 32768))
    if settings.get("llm_api_key_env"):
        models_config["llm"]["api_key_env"] = settings["llm_api_key_env"]

    automation = {
        "videos_dir": settings.get("videos_dir") or "videos",
        "run_id": settings.get("run_id") or "auto",
    }
    return {
        "profile": profile,
        "pipeline_config": pipeline_config,
        "models_config": models_config,
        "automation": automation,
    }


def _split_sections(text: str) -> Dict[str, List[str]]:
    current: Optional[str] = None
    sections: Dict[str, List[str]] = {}
    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        if stripped.startswith("## "):
            current = stripped[3:].strip().lower()
            sections.setdefault(current, [])
            continue
        if current:
            sections[current].append(raw_line.rstrip())
    return sections


def _parse_settings(lines: List[str]) -> Dict[str, str]:
    settings: Dict[str, str] = {}
    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("#") or line.startswith(">") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        # Strip inline `# ...` trailing comments so values like
        # `single_pass_token_limit: 60000   # ...` parse cleanly.
        value = _strip_inline_comment(value).strip()
        settings[key.strip()] = value
    return settings


def _strip_inline_comment(value: str) -> str:
    # Only treat `#` as comment when it follows whitespace; URLs like
    # http://host:11434 stay intact, and `#tag` style values keep working.
    for index in range(len(value) - 1):
        if value[index].isspace() and value[index + 1] == "#":
            return value[:index]
    return value


def _parse_output_sections(lines: List[str]) -> List[Dict[str, Any]]:
    sections: List[Dict[str, Any]] = []
    for checked, parts in _checkbox_parts(lines):
        if len(parts) < 2:
            continue
        sections.append(
            {
                "id": parts[0],
                "title": parts[1],
                "style": parts[2] if len(parts) > 2 else "default",
                "enabled": checked,
            }
        )
    return sections


def _parse_required_items(lines: List[str]) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for checked, parts in _checkbox_parts(lines):
        if not checked or len(parts) < 3:
            continue
        items.append(
            {
                "id": parts[0],
                "label": parts[1],
                "required": True,
                "priority": "high",
                "aliases": _comma_list(parts[2]),
                "description": parts[3] if len(parts) > 3 else "",
            }
        )
    return items


def _parse_custom_topics(lines: List[str]) -> List[Dict[str, Any]]:
    topics: List[Dict[str, Any]] = []
    for checked, parts in _checkbox_parts(lines):
        if not checked or len(parts) < 3:
            continue
        topics.append(
            {
                "id": parts[0],
                "label": parts[1],
                "aliases": _comma_list(parts[2]),
                "description": parts[3] if len(parts) > 3 else "",
                "must_search": True,
            }
        )
    return topics


def _parse_verification_terms(lines: List[str]) -> List[Dict[str, Any]]:
    terms: List[Dict[str, Any]] = []
    for checked, parts in _checkbox_parts(lines):
        if not checked or len(parts) < 3:
            continue
        terms.append(
            {
                "id": parts[0],
                "label": parts[1],
                "aliases": _comma_list(parts[2]),
                "description": parts[3] if len(parts) > 3 else "",
            }
        )
    return terms


def _parse_rendering_toggles(lines: List[str]) -> Dict[str, bool]:
    toggles: Dict[str, bool] = {}
    for checked, parts in _checkbox_parts(lines):
        if not parts:
            continue
        key = parts[0].strip().lower()
        if key in RENDERING_TOGGLES:
            toggles[key] = checked
    return toggles


def _parse_keyword_sections(sections: Dict[str, List[str]]) -> Dict[str, List[str]]:
    overrides: Dict[str, List[str]] = {}
    for section_name, target_key in KEYWORD_SECTIONS.items():
        lines = sections.get(section_name)
        if lines is None:
            continue
        keywords = _parse_keyword_lines(lines)
        if keywords:
            overrides[target_key] = keywords
    return overrides


def _parse_keyword_lines(lines: List[str]) -> List[str]:
    keywords: List[str] = []
    seen = set()
    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("#") or line.startswith(">"):
            continue
        bullet = BULLET_RE.match(line)
        body = bullet.group("body") if bullet else line
        for token in _comma_list(body):
            normalized = token.strip()
            if not normalized:
                continue
            key = normalized.lower()
            if key in seen:
                continue
            seen.add(key)
            keywords.append(normalized)
    return keywords


def _checkbox_parts(lines: List[str]) -> List[tuple]:
    rows = []
    for raw_line in lines:
        match = CHECKBOX_RE.match(raw_line.strip())
        if not match:
            continue
        checked = match.group("checked").lower() == "x"
        parts = [part.strip() for part in match.group("body").split("|")]
        rows.append((checked, parts))
    return rows


def _comma_list(value: str) -> List[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _number(value: Optional[str], fallback: float) -> float:
    if value in {None, ""}:
        return fallback
    try:
        return float(value)
    except ValueError:
        return fallback


def _bool(value: Optional[str], fallback: bool) -> bool:
    if value in {None, ""}:
        return fallback
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}
