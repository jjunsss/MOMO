"""Evidence verification for final summary drafts."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List, Tuple


CLAIM_FIELDS = ["decisions", "action_items", "worth_noting", "open_questions"]


def verify_summary(draft: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    final = deepcopy(draft)
    corrections: List[Dict[str, Any]] = []

    for field in CLAIM_FIELDS:
        verified_items = []
        for item in final.get(field, []):
            if item.get("evidence_timestamps"):
                item.setdefault("support", "weak")
                verified_items.append(item)
            else:
                corrections.append(
                    {
                        "field": field,
                        "action": "removed",
                        "reason": "missing evidence_timestamps",
                        "item": item,
                    }
                )
        final[field] = verified_items

    next_meeting = final.get("next_meeting", {})
    if next_meeting.get("status") == "found" and next_meeting.get("evidence_timestamps"):
        next_meeting.setdefault("support", "weak")
    elif next_meeting.get("status") == "found":
        next_meeting["status"] = "uncertain"
        next_meeting["support"] = "weak"
        corrections.append(
            {
                "field": "next_meeting",
                "action": "downgraded",
                "reason": "missing evidence_timestamps",
            }
        )
    final["next_meeting"] = next_meeting

    return {
        "status": "verified",
        "corrections": corrections,
        "checked_claim_fields": CLAIM_FIELDS + ["next_meeting"],
    }, final

