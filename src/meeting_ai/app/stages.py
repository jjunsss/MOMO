"""Stage identifiers and bilingual labels shared with the Streamlit UI."""

from __future__ import annotations

from typing import List, Tuple

from .i18n import Language, t as _t


STAGE_ORDER: Tuple[str, ...] = (
    "prepare",
    "audio",
    "transcribe",
    "chunk",
    "synthesize",
    "critique",
    "verify",
    "render",
    "done",
)


def visible_stages(enable_critique: bool) -> List[str]:
    """Return the linear set of stages shown in the progress UI."""
    base = [
        "prepare",
        "audio",
        "transcribe",
        "chunk",
        "synthesize",
    ]
    if enable_critique:
        base.append("critique")
    base.extend(["verify", "render"])
    return base


def label(stage: str, lang: Language) -> str:
    return _t("stage.{0}".format(stage), lang)


def hint(stage: str, lang: Language) -> str:
    return _t("hint.{0}".format(stage), lang)
