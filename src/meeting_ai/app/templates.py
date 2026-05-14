"""Bilingual preset summary-guide templates for the Streamlit GUI.

Each template carries Korean and English variants of every user-facing
string. The active language is resolved by the caller via the i18n
module, so the GUI can swap templates without touching pipeline code.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from .i18n import LANG_EN, LANG_KO, Language


# A "localized field" is a mapping from a language code to the string for
# that language. Templates wrap their user-facing content in this shape so
# the GUI can pick the active language at render time.
Localized = Dict[Language, str]
LocalizedList = Dict[Language, List[str]]


@dataclass(frozen=True)
class Template:
    key: str
    label: Localized
    title: Localized
    custom_instruction: Localized
    topics: LocalizedList
    must_check: LocalizedList
    blurb: Localized

    def localized_label(self, lang: Language) -> str:
        return self.label.get(lang, self.label.get(LANG_KO, self.key))

    def localized_blurb(self, lang: Language) -> str:
        return self.blurb.get(lang, self.blurb.get(LANG_KO, ""))

    def localized_title(self, lang: Language) -> str:
        return self.title.get(lang, self.title.get(LANG_KO, ""))

    def localized_instruction(self, lang: Language) -> str:
        return self.custom_instruction.get(lang, self.custom_instruction.get(LANG_KO, ""))

    def localized_topics(self, lang: Language) -> List[str]:
        return list(self.topics.get(lang, self.topics.get(LANG_KO, [])))

    def localized_must_check(self, lang: Language) -> List[str]:
        return list(self.must_check.get(lang, self.must_check.get(LANG_KO, [])))


def _loc(ko: str, en: str) -> Localized:
    return {LANG_KO: ko, LANG_EN: en}


def _loc_list(ko: List[str], en: List[str]) -> LocalizedList:
    return {LANG_KO: ko, LANG_EN: en}


TEMPLATES: Tuple[Template, ...] = (
    Template(
        key="research",
        label=_loc("📚 연구 미팅", "📚 Research"),
        title=_loc("연구 미팅", "Research sync"),
        custom_instruction=_loc(
            "이번 주 진행 상황과 막힌 부분, 그리고 다음 회의 안건 중심으로 정리해 주세요. "
            "기술 논의는 결정으로 이어진 부분만 짧게 적어주세요.",
            "Focus on this week's progress, blockers, and next-meeting agenda. "
            "Keep technical discussion brief — only the parts that led to a decision.",
        ),
        topics=_loc_list(
            [
                "이번 주 진행 상황",
                "막힌 부분 / 의사결정이 필요한 부분",
                "다음 미팅 일정과 안건",
                "확정된 결정 사항",
            ],
            [
                "Progress this week",
                "Blockers / decisions needed",
                "Next meeting agenda and date",
                "Confirmed decisions",
            ],
        ),
        must_check=_loc_list(
            [
                "잠정 결정과 확정 결정을 구분한다",
                "담당자가 명시된 작업과 미정인 작업을 구분한다",
                "날짜와 시간을 혼동하지 않는다",
            ],
            [
                "Distinguish tentative vs. confirmed decisions",
                "Separate assigned tasks from unassigned ones",
                "Do not confuse dates and times",
            ],
        ),
        blurb=_loc(
            "진행 상황 + 막힌 부분 + 결정/다음 미팅 위주로 정리합니다.",
            "Progress, blockers, decisions, next meeting.",
        ),
    ),
    Template(
        key="one_on_one",
        label=_loc("👥 1:1 미팅", "👥 1:1"),
        title=_loc("1:1 미팅", "1:1 meeting"),
        custom_instruction=_loc(
            "대화의 톤은 부드럽게 유지하되, 구체적인 액션 아이템만 또렷이 뽑아 주세요. "
            "개인적 의견과 공식 결정을 섞지 마세요.",
            "Keep the tone soft, but pull out concrete action items clearly. "
            "Do not mix personal opinions with formal decisions.",
        ),
        topics=_loc_list(
            [
                "최근 잘된 일과 어려운 점",
                "성장 / 커리어 관련 대화",
                "다음 1:1 전까지 시도해 볼 것",
                "관리자가 도와줄 수 있는 부분",
            ],
            [
                "Recent wins and struggles",
                "Growth / career conversation",
                "What to try before the next 1:1",
                "Where the manager can help",
            ],
        ),
        must_check=_loc_list(
            [
                "개인적 의견과 공식 결정을 구분한다",
                "구체적 액션 아이템과 막연한 다짐을 구분한다",
            ],
            [
                "Distinguish personal opinion from formal decisions",
                "Distinguish concrete actions from vague intentions",
            ],
        ),
        blurb=_loc(
            "대화의 톤은 유지하고 액션 아이템만 또렷이 뽑습니다.",
            "Preserve tone, sharpen action items.",
        ),
    ),
    Template(
        key="client",
        label=_loc("🤝 외부 기업 미팅", "🤝 External meeting"),
        title=_loc("외부 기업 미팅", "External meeting"),
        custom_instruction=_loc(
            "약속한 후속 조치와 다음 접점 일정을 또렷이 정리해 주세요. "
            "금액·기한·수치는 발언 그대로 옮기고, 미정·검토 중인 사항은 결정 항목과 섞지 말고 따로 표시해 주세요.",
            "Pull out follow-up commitments and the next touch-point date clearly. "
            "Quote amounts, deadlines, and numbers verbatim, and keep TBD / under-review items "
            "in a separate section — never mixed with decisions.",
        ),
        topics=_loc_list(
            [
                "요구사항 / 우선순위",
                "제기된 우려 사항",
                "약속한 후속 조치",
                "다음 접점 일정",
            ],
            [
                "Requirements / priorities",
                "Concerns raised",
                "Follow-up commitments",
                "Next touch-point date",
            ],
        ),
        must_check=_loc_list(
            [
                "구두 약속과 미정·검토 중인 사항을 섞지 않는다",
                "금액·기한·수치는 발언 그대로 옮긴다",
            ],
            [
                "Never mix verbal commitments with TBDs or under-review items",
                "Quote amounts, deadlines, and numbers verbatim",
            ],
        ),
        blurb=_loc(
            "후속 조치·다음 일정·수치를 또렷이 잡고, 미정 사항을 따로 분리합니다.",
            "Sharpen follow-ups, next date, numbers; keep TBDs separate.",
        ),
    ),
)


EMPTY_TEMPLATE = Template(
    key="empty",
    label=_loc("✨ 비워두기", "✨ Clear"),
    title=_loc("", ""),
    custom_instruction=_loc("", ""),
    topics=_loc_list([], []),
    must_check=_loc_list([], []),
    blurb=_loc(
        "기본 프로필(meeting_profile.md)만 사용합니다.",
        "Use the meeting_profile.md defaults only.",
    ),
)


def by_key(key: str) -> Template:
    for template in TEMPLATES:
        if template.key == key:
            return template
    raise KeyError(key)


def find(key: str) -> Optional[Template]:
    try:
        return by_key(key)
    except KeyError:
        if key == EMPTY_TEMPLATE.key:
            return EMPTY_TEMPLATE
        return None
