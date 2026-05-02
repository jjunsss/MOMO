"""Chain-of-Verification (CoVe) style critique pass over the final summary.

After 2-pass synthesis we ask the LLM to look at every important claim and
check whether the cited evidence_timestamp's transcript line actually
supports it. Failed claims are downgraded (support -> "weak"/"inferred") or
removed. Specifically catches the "13일 -> 13:00" date/time confusion.
"""

from __future__ import annotations

import json
from copy import deepcopy
from typing import Any, Dict, List, Optional

from meeting_ai.prompts import render_named
from meeting_ai.providers.llm.base import LLMError, LLMProvider
from meeting_ai.utils.time import format_seconds


def _evidence_window(transcript: Dict[str, Any], timestamp: str, window: int = 30) -> str:
    """Return the transcript lines around a timestamp (HH:MM:SS)."""
    try:
        h, m, s = (int(part) for part in timestamp.split(":"))
        target = h * 3600 + m * 60 + s
    except (ValueError, AttributeError):
        return ""
    lines: List[str] = []
    for segment in transcript.get("segments", []):
        start = float(segment.get("start", 0.0))
        if start < target - window or start > target + window:
            continue
        ts_label = format_seconds(start)
        lines.append("[{0}] {1}".format(ts_label, segment.get("text", "")))
    return "\n".join(lines)


def _claims_to_check(summary: Dict[str, Any], transcript: Dict[str, Any]) -> List[Dict[str, Any]]:
    claims: List[Dict[str, Any]] = []
    for kind, items in [
        ("decisions", summary.get("decisions", [])),
        ("action_items", summary.get("action_items", [])),
        ("worth_noting", summary.get("worth_noting", [])),
    ]:
        for index, item in enumerate(items or []):
            text = item.get("decision") or item.get("task") or item.get("note") or ""
            evidence = item.get("evidence_timestamps") or []
            window = "\n".join(
                _evidence_window(transcript, ts, window=30) for ts in evidence
            )
            claims.append(
                {
                    "field": kind,
                    "index": index,
                    "text": text,
                    "owner": item.get("owner", ""),
                    "deadline": item.get("deadline", ""),
                    "evidence_timestamps": evidence,
                    "evidence_window": window,
                }
            )
    next_meeting = summary.get("next_meeting", {}) or {}
    if next_meeting.get("status") in {"found", "uncertain"}:
        evidence = next_meeting.get("evidence_timestamps") or []
        window = "\n".join(
            _evidence_window(transcript, ts, window=45) for ts in evidence
        )
        claims.append(
            {
                "field": "next_meeting",
                "index": 0,
                "text": "date={0}, time={1}, agenda={2}".format(
                    next_meeting.get("date", "unknown"),
                    next_meeting.get("time", "unknown"),
                    "; ".join(next_meeting.get("agenda", []) or []),
                ),
                "owner": "",
                "deadline": "",
                "evidence_timestamps": evidence,
                "evidence_window": window,
            }
        )
    return claims


def critique_summary(
    summary: Dict[str, Any],
    transcript: Dict[str, Any],
    llm: LLMProvider,
) -> Dict[str, Any]:
    """Return a (possibly) corrected copy of ``summary`` and a critique report
    embedded under ``metadata.critique``.
    """
    claims = _claims_to_check(summary, transcript)
    if not claims:
        summary.setdefault("metadata", {})["critique"] = {
            "claims_checked": 0,
            "verdicts": [],
        }
        return summary

    prompt = render_named(
        "critique",
        {
            "claims_jsonl": "\n".join(
                json.dumps(claim, ensure_ascii=False, sort_keys=True) for claim in claims
            ),
        },
    )
    try:
        response = llm.call(
            prompt,
            max_tokens=4096,
            think=True,
            json_schema=_critique_schema(),
        )
    except LLMError as exc:
        summary.setdefault("metadata", {})["critique"] = {
            "claims_checked": len(claims),
            "error": str(exc),
        }
        return summary

    parsed = _parse_json_response(response.text)
    if not parsed or not isinstance(parsed.get("verdicts"), list):
        summary.setdefault("metadata", {})["critique"] = {
            "claims_checked": len(claims),
            "verdicts": [],
            "error": "unparsable critique output",
        }
        return summary

    verdicts = parsed["verdicts"]
    final = deepcopy(summary)
    applied = []
    for verdict in verdicts:
        field = verdict.get("field")
        index = verdict.get("index")
        action = (verdict.get("action") or "").lower()
        if not field:
            continue
        if field == "next_meeting":
            nm = final.get("next_meeting", {}) or {}
            if action == "remove":
                nm["status"] = "not_found"
                nm["support"] = "none"
                nm["date"] = "unknown"
                nm["time"] = "unknown"
                nm["agenda"] = []
                nm["preparation"] = []
            elif action == "fix":
                nm["date"] = str(verdict.get("fixed_date") or nm.get("date", "unknown"))
                nm["time"] = str(verdict.get("fixed_time") or nm.get("time", "unknown"))
                nm["support"] = str(verdict.get("fixed_support") or "weak")
                if "fixed_agenda" in verdict:
                    nm["agenda"] = list(verdict["fixed_agenda"]) or nm.get("agenda", [])
            elif action == "downgrade":
                nm["support"] = "weak"
            final["next_meeting"] = nm
            applied.append({"field": field, "action": action, "reason": verdict.get("reason", "")})
            continue

        items = final.get(field) or []
        if not isinstance(items, list) or index is None or not (0 <= int(index) < len(items)):
            continue
        i = int(index)
        if action == "remove":
            items[i] = None
            applied.append({"field": field, "action": action, "index": i, "reason": verdict.get("reason", "")})
        elif action == "fix":
            target = items[i]
            for src_key, dst_key in [
                ("fixed_text", "decision" if field == "decisions" else "task" if field == "action_items" else "note"),
                ("fixed_owner", "owner"),
                ("fixed_deadline", "deadline"),
                ("fixed_support", "support"),
            ]:
                if src_key in verdict and dst_key in target:
                    target[dst_key] = verdict[src_key]
            applied.append({"field": field, "action": action, "index": i, "reason": verdict.get("reason", "")})
        elif action == "downgrade":
            items[i]["support"] = "weak"
            applied.append({"field": field, "action": action, "index": i, "reason": verdict.get("reason", "")})
        final[field] = items
    # drop None entries from removals
    for field in ["decisions", "action_items", "worth_noting"]:
        final[field] = [item for item in final.get(field, []) if item is not None]

    final.setdefault("metadata", {})["critique"] = {
        "claims_checked": len(claims),
        "verdicts": applied,
    }
    return final


def _critique_schema() -> Dict[str, Any]:
    return {
        "type": "object",
        "required": ["verdicts"],
        "properties": {
            "verdicts": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["field", "action"],
                    "properties": {
                        "field": {"type": "string"},
                        "index": {"type": "integer"},
                        "action": {"type": "string"},
                        "reason": {"type": "string"},
                        "fixed_text": {"type": "string"},
                        "fixed_owner": {"type": "string"},
                        "fixed_deadline": {"type": "string"},
                        "fixed_date": {"type": "string"},
                        "fixed_time": {"type": "string"},
                        "fixed_agenda": {"type": "array", "items": {"type": "string"}},
                        "fixed_support": {"type": "string"},
                    },
                },
            }
        },
    }


def _parse_json_response(raw_text: str) -> Optional[Dict[str, Any]]:
    text = (raw_text or "").strip()
    if not text:
        return None
    if text.startswith("```"):
        text = text.strip("`")
        if "\n" in text:
            head, body = text.split("\n", 1)
            text = body if head.lower().startswith("json") else text
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if 0 <= start < end:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                return None
    return None
