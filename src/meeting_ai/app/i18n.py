"""Simple translation tables for the Streamlit GUI.

Two languages: ``ko`` (default) and ``en``. The active language is kept on
``st.session_state['ui_lang']`` and read by :func:`t`.

We deliberately avoid an external i18n framework — a flat dict is enough
at this scale and keeps the lookup zero-overhead.
"""

from __future__ import annotations

from typing import Dict, Iterable, List, Tuple


Language = str  # "ko" | "en"

LANG_KO: Language = "ko"
LANG_EN: Language = "en"
SUPPORTED_LANGUAGES: Tuple[Language, ...] = (LANG_KO, LANG_EN)


LANGUAGE_LABELS: Dict[Language, str] = {
    "ko": "한국어",
    "en": "English",
}


_STRINGS: Dict[str, Dict[Language, str]] = {
    # ─── Page / branding ──────────────────────────────────────────
    "page.title": {
        "ko": "MOMO · 회의 요약",
        "en": "MOMO · Meeting Recap",
    },
    "brand.title": {
        "ko": "🎙️ MOMO",
        "en": "🎙️ MOMO",
    },
    "brand.tagline": {
        "ko": "회의 영상을 끌어다 놓으면 요약과 근거를 자동으로 만듭니다.",
        "en": "Drop in a recording and get a summary with evidence.",
    },

    # ─── Sidebar ──────────────────────────────────────────────────
    "sidebar.new_run": {"ko": "➕ 새 회의 분석", "en": "➕ New meeting"},
    "sidebar.history_heading": {"ko": "📚 지난 회의", "en": "📚 Past meetings"},
    "sidebar.history_empty": {
        "ko": "아직 분석한 회의가 없습니다.",
        "en": "No past meetings yet.",
    },
    "sidebar.language": {"ko": "표시 언어", "en": "Display language"},
    "sidebar.advanced": {"ko": "⚙️ 고급 설정", "en": "⚙️ Advanced"},
    "sidebar.asr_label": {"ko": "음성 인식 품질", "en": "Speech-to-text quality"},
    "sidebar.asr_fast": {"ko": "빠름 (small)", "en": "Fast (small)"},
    "sidebar.asr_balanced": {"ko": "균형 (medium)", "en": "Balanced (medium)"},
    "sidebar.asr_best": {"ko": "최고 품질 (large-v3)", "en": "Best (large-v3)"},
    "sidebar.asr_help": {
        "ko": "회의가 길고 시간이 부족하면 '빠름', 정확도가 가장 중요하면 '최고 품질'.",
        "en": "Pick Fast for long meetings under time pressure, Best for accuracy.",
    },
    "sidebar.summary_mode": {"ko": "요약 방식", "en": "Summary mode"},
    "sidebar.mode_fast": {"ko": "빠른 요약 (1-pass)", "en": "Fast (single pass)"},
    "sidebar.mode_thorough": {"ko": "꼼꼼한 요약 (slot 추출)", "en": "Thorough (slot extraction)"},
    "sidebar.mode_help": {
        "ko": "기본은 최고품질을 위해 꼼꼼한 요약입니다. 빠른 요약은 시간이 급할 때만 사용하세요.",
        "en": "Default is Thorough for best quality. Use Fast only when time matters more.",
    },
    "sidebar.critique": {"ko": "AI 비평 검토 추가", "en": "Add AI critique review"},
    "sidebar.critique_help": {
        "ko": "요약 초안을 한 번 더 검토합니다. 시간이 더 걸리지만 품질이 안정적입니다.",
        "en": "Re-review the draft once. Slower but more stable quality.",
    },
    "sidebar.output_language": {"ko": "출력 언어", "en": "Summary output language"},
    "sidebar.output_ko": {"ko": "한국어", "en": "Korean"},
    "sidebar.output_en": {"ko": "English", "en": "English"},
    "sidebar.output_language_help": {
        "ko": (
            "표시 언어를 바꾸면 자동으로 같이 바뀝니다. 회의에 등장한 영어 약어·"
            "기술 용어·고유명사(예: 3D Gaussian, SDS, Whisper)는 어느 쪽을 골라도 "
            "원문 그대로 보존됩니다."
        ),
        "en": (
            "Follows the UI language by default — change here to override. "
            "Technical terms, acronyms, and proper nouns from the meeting "
            "(e.g. 3D Gaussian, SDS, Whisper) are preserved verbatim either way."
        ),
    },
    "gpu.label": {"ko": "GPU", "en": "GPU"},
    "gpu.on": {"ko": "ON", "en": "ON"},
    "gpu.off": {"ko": "OFF", "en": "OFF"},
    "gpu.on_detail": {
        "ko": "{0} 사용 가능",
        "en": "{0} available",
    },
    "gpu.off_warning": {
        "ko": "주의: CUDA GPU를 사용할 수 없습니다. MOMO는 CPU fallback 없이 중단됩니다. 상세: {0}",
        "en": "Warning: CUDA GPU is not available. MOMO stops instead of using CPU fallback. Detail: {0}",
    },

    # ─── LLM readiness ────────────────────────────────────────────
    "quality.missing_provider": {
        "ko": "LLM provider가 설정되어 있지 않습니다. `meeting_profile.md`에서 Ollama 또는 OpenAI 호환 LLM을 설정해 주세요.",
        "en": "No LLM provider is configured. Configure Ollama or an OpenAI-compatible LLM in `meeting_profile.md`.",
    },
    "quality.disabled_stub_provider": {
        "ko": "현재 LLM provider가 `{0}`입니다. 실제 회의 요약은 규칙 기반 대체 provider를 사용할 수 없습니다. Ollama 또는 OpenAI 호환 LLM을 설정해 주세요.",
        "en": "The current LLM provider is `{0}`. Real meeting summaries cannot use a rule-based replacement provider. Configure Ollama or an OpenAI-compatible LLM.",
    },
    "quality.unsupported_provider": {
        "ko": "지원하지 않는 LLM provider `{0}`입니다. Ollama 또는 OpenAI 호환 LLM을 설정해 주세요.",
        "en": "Unsupported LLM provider `{0}`. Configure Ollama or an OpenAI-compatible LLM.",
    },
    "quality.missing_model": {
        "ko": "`{0}` provider에 사용할 LLM 모델명이 비어 있습니다. `meeting_profile.md` 또는 환경변수에 모델을 설정해 주세요.",
        "en": "No model is configured for provider `{0}`. Set the model in `meeting_profile.md` or an environment variable.",
    },
    "quality.ollama_unreachable": {
        "ko": "Ollama에 연결할 수 없습니다. 터미널에서 `ollama serve`를 실행하고, 필요하면 `ollama pull {0}`을 먼저 실행해 주세요. 상세: {1}",
        "en": "Cannot reach Ollama. Run `ollama serve` in a terminal, and run `ollama pull {0}` first if needed. Detail: {1}",
    },
    "quality.ollama_model_missing": {
        "ko": "Ollama는 켜져 있지만 `{0}` 모델을 찾지 못했습니다. `ollama pull {0}`을 실행해 주세요. 현재 보이는 모델: {1}",
        "en": "Ollama is running, but model `{0}` was not found. Run `ollama pull {0}`. Visible models: {1}",
    },
    "quality.generic": {
        "ko": "LLM 품질 점검에 실패했습니다. provider={0}, 상세={1}",
        "en": "LLM quality check failed. provider={0}, detail={1}",
    },

    # ─── New-run page ─────────────────────────────────────────────
    "new.heading": {"ko": "🎙️ 새 회의 요약하기", "en": "🎙️ Summarize a new meeting"},
    "new.caption": {
        "ko": "영상 파일을 올리고 시작 버튼을 누르면 끝입니다. 주제 입력은 비워두어도 됩니다.",
        "en": "Upload a recording and hit Start. Topic inputs are optional.",
    },
    "new.step1_title": {"ko": "1️⃣ 회의 영상 선택", "en": "1️⃣ Pick a recording"},
    "new.step1_help": {
        "ko": ".mp4 · .mkv · .mov · .m4a · .mp3 · .wav · 최대 4 GB 까지 업로드할 수 있어요.",
        "en": ".mp4 · .mkv · .mov · .m4a · .mp3 · .wav — up to 4 GB.",
    },
    "new.upload_tab": {"ko": "📤 새 파일 업로드", "en": "📤 Upload new file"},
    "new.existing_tab": {"ko": "📁 기존 videos/ 에서 고르기", "en": "📁 Pick from videos/"},
    "new.upload_label": {"ko": "회의 영상이나 오디오 파일", "en": "Meeting video or audio"},
    "new.upload_success": {"ko": "업로드 완료: {0}", "en": "Uploaded: {0}"},
    "new.existing_empty": {
        "ko": "videos/ 폴더에 영상이 없습니다. 위 탭에서 업로드하거나 videos/ 폴더에 파일을 넣어 주세요.",
        "en": "No files in videos/. Upload above or drop a file into videos/.",
    },
    "new.existing_label": {"ko": "분석할 파일", "en": "Select a file"},
    "new.existing_placeholder": {"ko": "파일을 고르세요", "en": "Choose a file"},

    # ─── Summary guide section (the core) ─────────────────────────
    "guide.title": {
        "ko": "2️⃣ 무엇을 요약하면 좋을지 알려주세요",
        "en": "2️⃣ Tell the AI what to focus on",
    },
    "guide.core_badge": {"ko": "가장 중요", "en": "MOST IMPORTANT"},
    "guide.intro": {
        "ko": "AI 는 여기에 적은 내용을 중심으로 회의를 정리합니다. 비워두어도 동작하지만, 두세 줄만 적어주면 요약 품질이 훨씬 좋아집니다.",
        "en": "The AI uses what you write here to drive the summary. It works empty, but two or three lines lift quality noticeably.",
    },
    "guide.template_help": {
        "ko": "회의 유형을 고르면 예시가 자동으로 채워집니다.",
        "en": "Pick a meeting type to auto-fill an example.",
    },
    "guide.title_label": {"ko": "📝 회의 제목", "en": "📝 Meeting title"},
    "guide.optional_suffix": {"ko": "(선택)", "en": "(optional)"},
    "guide.title_placeholder": {
        "ko": "예: 4월 둘째 주 연구 미팅",
        "en": "e.g. Research sync — week of Apr 15",
    },
    "guide.instruction_label": {
        "ko": "🗣️ 자유 지시 — AI 에게 하고 싶은 말",
        "en": "🗣️ Free-form instruction — what to tell the AI",
    },
    "guide.instruction_help": {
        "ko": "한두 문장으로 자유롭게. 이 문장이 가장 우선순위가 높습니다.",
        "en": "One or two sentences in your own words. This takes the highest priority.",
    },
    "guide.instruction_placeholder": {
        "ko": (
            "예: 이번 회의는 결정사항과 다음 미팅 안건만 뽑아주세요. "
            "기술 토론은 짧게 한 줄씩 요약해도 됩니다."
        ),
        "en": (
            "e.g. Focus on decisions and next-meeting agenda. "
            "Tech discussion can be one short line each."
        ),
    },
    "guide.topics_label": {
        "ko": "⭐ 요약에 꼭 들어갔으면 하는 주제",
        "en": "⭐ Topics to make sure are covered",
    },
    "guide.topics_help": {
        "ko": "한 줄에 하나. 회의에서 어떤 이야기가 나왔는지 이 주제 위주로 찾아 정리합니다.",
        "en": "One per line. The AI will look for these and structure the summary around them.",
    },
    "guide.topics_placeholder": {
        "ko": (
            "이번 주 진행 상황\n"
            "막힌 부분 / 결정이 필요한 부분\n"
            "다음 미팅 일정"
        ),
        "en": (
            "Progress this week\n"
            "Blockers / decisions needed\n"
            "Next meeting schedule"
        ),
    },
    "guide.must_check_label": {
        "ko": "⚠️ AI 가 혼동하지 말아야 할 점",
        "en": "⚠️ Things the AI should not confuse",
    },
    "guide.must_check_help": {
        "ko": (
            "한 줄에 하나. 헷갈리기 쉬운 항목을 미리 알려두면 더 정확하게 정리합니다. "
            "기술명·논문명처럼 보통 영어로 말하는 단어는 영어 원문 표기로 적어주세요."
        ),
        "en": "One per line. Telling the AI in advance prevents common confusions.",
    },
    "guide.must_check_placeholder": {
        "ko": (
            "잠정 결정과 확정 결정을 구분한다\n"
            "날짜와 시간을 헷갈리지 않는다\n"
            "기술명·논문명은 영어 원문 표기를 우선한다 (예: Chain-of-Thought, Gaussian Splatting)"
        ),
        "en": (
            "Distinguish tentative vs. confirmed decisions\n"
            "Do not confuse dates and times"
        ),
    },
    "guide.count_topics": {"ko": "📌 {0}개 주제", "en": "📌 {0} topics"},
    "guide.count_must_check": {"ko": "📌 {0}개 확인 항목", "en": "📌 {0} checks"},
    "guide.examples_expander": {
        "ko": "💡 어떻게 적으면 좋을지 예시 보기",
        "en": "💡 See examples",
    },
    "guide.examples_intro": {
        "ko": "회의 유형마다 자주 쓰는 입력 예시입니다. 그대로 써도 되고, 한두 줄만 골라 써도 됩니다.",
        "en": "Common inputs by meeting type. Copy as-is, or pick a line or two.",
    },
    "guide.example_topics": {"ko": "_주제 예시:_", "en": "_Topic examples:_"},
    "guide.example_must_check": {
        "ko": "_혼동 주의 예시:_",
        "en": "_Confusion-watch examples:_",
    },
    "guide.example_instruction": {
        "ko": "_자유 지시 예시:_",
        "en": "_Instruction example:_",
    },

    # ─── CTA ──────────────────────────────────────────────────────
    "cta.start": {"ko": "🚀 회의 분석 시작", "en": "🚀 Start summarizing"},
    "cta.start_disabled_help": {
        "ko": "영상을 먼저 선택해 주세요.",
        "en": "Pick a recording first.",
    },
    "cta.gpu_disabled_help": {
        "ko": "GPU OFF 상태에서는 분석을 시작할 수 없습니다.",
        "en": "Cannot start while GPU is OFF.",
    },

    # ─── Progress ─────────────────────────────────────────────────
    "progress.heading": {
        "ko": "⏳ 회의를 분석 중입니다…",
        "en": "⏳ Analyzing the meeting…",
    },
    "progress.caption": {
        "ko": "창을 닫지 말고 잠시만 기다려 주세요. 경과 시간: **{0}**",
        "en": "Don't close this tab. Elapsed: **{0}**",
    },
    "elapsed.hours": {"ko": "{0}시간 {1}분 {2}초", "en": "{0}h {1}m {2}s"},
    "elapsed.minutes": {"ko": "{0}분 {1}초", "en": "{0}m {1}s"},
    "elapsed.seconds": {"ko": "{0}초", "en": "{0}s"},

    # ─── Failure ──────────────────────────────────────────────────
    "fail.heading": {
        "ko": "❌ 분석 중 오류가 발생했습니다",
        "en": "❌ Something went wrong",
    },
    "fail.unknown": {"ko": "알 수 없는 오류", "en": "Unknown error"},
    "fail.trace": {"ko": "자세한 오류 메시지 (개발자용)", "en": "Stack trace (for developers)"},
    "fail.retry": {"ko": "다시 시도", "en": "Try again"},

    # ─── Result ───────────────────────────────────────────────────
    "result.success": {"ko": "✅ 완료! ({0} 소요)", "en": "✅ Done! ({0} elapsed)"},
    "result.missing": {
        "ko": "결과를 찾지 못했습니다. 사이드바에서 지난 회의를 선택해 주세요.",
        "en": "Result not found. Pick a past meeting from the sidebar.",
    },
    "result.run_missing": {
        "ko": "이 회의 폴더를 찾을 수 없습니다: {0}",
        "en": "Run folder not found: {0}",
    },
    "result.run_incomplete": {
        "ko": "최종 요약 파일을 찾지 못했습니다. 이 회의는 아직 완료되지 않았을 수 있어요.",
        "en": "No final summary file. This run may be incomplete.",
    },
    "result.tab_summary": {"ko": "📄 요약", "en": "📄 Summary"},
    "result.tab_evidence": {"ko": "🔎 근거", "en": "🔎 Evidence"},
    "result.tab_transcript": {"ko": "📜 원본 대본", "en": "📜 Transcript"},
    "result.tab_files": {"ko": "📦 파일", "en": "📦 Files"},
    "result.summary_missing": {"ko": "최종 요약을 찾지 못했습니다.", "en": "Final summary not found."},
    "result.evidence_missing": {
        "ko": "이 회의는 근거 보고서가 저장되지 않았습니다.",
        "en": "No evidence report for this run.",
    },
    "result.transcript_missing": {
        "ko": "대본 Markdown 이 저장되지 않았습니다.",
        "en": "No transcript Markdown saved.",
    },
    "result.read_error": {
        "ko": "파일을 읽지 못했습니다: {0}",
        "en": "Failed to read file: {0}",
    },
    "result.files_caption": {"ko": "결과 폴더: `{0}`", "en": "Run folder: `{0}`"},
    "result.completed_at": {"ko": "완료: {0}", "en": "Finished: {0}"},
    "result.download_summary": {"ko": "📄 요약 (.md)", "en": "📄 Summary (.md)"},
    "result.download_evidence": {"ko": "🔎 근거 (.md)", "en": "🔎 Evidence (.md)"},
    "result.download_json": {
        "ko": "🧱 요약 데이터 (.json)",
        "en": "🧱 Summary data (.json)",
    },
    "result.download_missing": {"ko": "— 없음", "en": "— not available"},
    "result.tab_playback": {
        "ko": "▶ 영상으로 듣기",
        "en": "▶ Watch with evidence",
    },
    "result.playback_help": {
        "ko": "시간 칩을 누르면 영상이 그 부분부터 재생됩니다. 요약된 항목이 회의에서 어디서 나왔는지 빠르게 확인해 보세요.",
        "en": "Click a timestamp chip to jump to that moment. Useful to double-check where each summary point came from.",
    },
    "result.playback_no_media": {
        "ko": "원본 영상/오디오 파일을 찾을 수 없어 재생 패널은 숨겨졌습니다. (`{0}`)",
        "en": "Original media file not found — the player is hidden. (`{0}`)",
    },
    "result.playback_no_items": {
        "ko": "이 회의에는 시간 근거가 함께 저장된 항목이 없습니다.",
        "en": "This run has no timestamped items to anchor.",
    },
    "result.playback_no_evidence_json": {
        "ko": "근거 데이터(`evidence/final_summary.with_evidence.json`)가 없어 시간 이동 기능을 사용할 수 없습니다.",
        "en": "No evidence data (`evidence/final_summary.with_evidence.json`) — jump-to-moment is unavailable for this run.",
    },
    "result.playback_section_key_topics": {"ko": "📚 핵심 논의 흐름", "en": "📚 Key topics"},
    "result.playback_section_decisions": {"ko": "✅ 결정 사항", "en": "✅ Decisions"},
    "result.playback_section_actions": {"ko": "📌 액션 아이템", "en": "📌 Action items"},
    "result.playback_section_worth_noting": {
        "ko": "💡 주의 깊게 볼 맥락",
        "en": "💡 Worth noting",
    },
    "result.playback_section_next_meeting": {"ko": "📅 다음 미팅", "en": "📅 Next meeting"},
    "result.playback_no_timestamps": {
        "ko": "— 시간 근거 없음",
        "en": "— no timestamp",
    },
    "result.playback_support_strong": {"ko": "근거 강함", "en": "strong evidence"},
    "result.playback_support_weak": {"ko": "근거 약함", "en": "weak evidence"},
    "result.playback_support_inferred": {"ko": "추론", "en": "inferred"},

    # ─── Stages ───────────────────────────────────────────────────
    "stage.queued": {"ko": "대기 중", "en": "Queued"},
    "stage.prepare": {"ko": "분석 폴더 준비", "en": "Preparing run folder"},
    "stage.audio": {"ko": "오디오 추출", "en": "Extracting audio"},
    "stage.transcribe": {
        "ko": "음성 인식 (가장 오래 걸려요)",
        "en": "Transcribing (this is the slow step)",
    },
    "stage.chunk": {"ko": "회의 구간 나누기", "en": "Chunking the meeting"},
    "stage.synthesize": {"ko": "AI 요약 작성", "en": "Drafting AI summary"},
    "stage.critique": {"ko": "AI 비평 검토", "en": "AI critique review"},
    "stage.verify": {"ko": "근거 확인", "en": "Verifying evidence"},
    "stage.render": {"ko": "결과 파일 정리", "en": "Rendering files"},
    "stage.done": {"ko": "완료", "en": "Done"},
    "stage.failed": {"ko": "오류 발생", "en": "Error"},

    "hint.queued": {"ko": "곧 시작합니다.", "en": "Starting up..."},
    "hint.prepare": {
        "ko": "결과 폴더를 만드는 중입니다.",
        "en": "Creating the run folder.",
    },
    "hint.audio": {
        "ko": "영상에서 음성만 추출 중입니다.",
        "en": "Pulling audio out of the video.",
    },
    "hint.transcribe": {
        "ko": "Whisper 가 한 줄씩 받아쓰기를 합니다. 회의 길이의 1/3 ~ 1/5 정도 걸려요.",
        "en": "Whisper writes the transcript. Typically 1/5 to 1/3 of the meeting length.",
    },
    "hint.chunk": {
        "ko": "긴 회의를 6 ~ 10 분 구간으로 나누고 키워드를 살펴봅니다.",
        "en": "Splitting into 6–10 min chunks and scanning for keywords.",
    },
    "hint.synthesize": {
        "ko": "AI 가 회의 흐름을 읽고 요약 초안을 작성합니다.",
        "en": "The AI reads the meeting flow and drafts the summary.",
    },
    "hint.critique": {
        "ko": "AI 가 초안을 다시 검토합니다.",
        "en": "The AI re-reviews its own draft.",
    },
    "hint.verify": {
        "ko": "근거 타임스탬프를 다시 맞춰봅니다.",
        "en": "Re-aligning evidence timestamps.",
    },
    "hint.render": {
        "ko": "Markdown 보고서를 저장 중입니다.",
        "en": "Writing the Markdown report.",
    },
    "hint.done": {"ko": "결과가 준비되었습니다.", "en": "Result is ready."},
    "hint.failed": {
        "ko": "도중에 문제가 생겼습니다. 상세 메시지를 확인해 주세요.",
        "en": "Something failed mid-run. Check the message below.",
    },
}


def supported_languages() -> Iterable[Language]:
    return SUPPORTED_LANGUAGES


def language_label(lang: Language) -> str:
    return LANGUAGE_LABELS.get(lang, lang)


def t(key: str, lang: Language) -> str:
    """Return the translation for ``key`` in ``lang``.

    Falls back to Korean, then English, then the key itself so missing
    strings are visible but never crash the UI.
    """
    bucket = _STRINGS.get(key)
    if bucket is None:
        return key
    if lang in bucket:
        return bucket[lang]
    if LANG_KO in bucket:
        return bucket[LANG_KO]
    if LANG_EN in bucket:
        return bucket[LANG_EN]
    return key


def known_keys() -> List[str]:
    return list(_STRINGS.keys())
