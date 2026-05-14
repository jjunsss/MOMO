"""MOMO Streamlit GUI entry point.

Run with:

    streamlit run src/meeting_ai/app/streamlit_app.py

The UI keeps the surface minimal on purpose: a video upload, a free-form
instruction + topics form, and a single 분석 시작 button. Advanced knobs
live in a collapsed sidebar expander.
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import streamlit as st

# Allow running via `streamlit run src/meeting_ai/app/streamlit_app.py` even
# when the project hasn't been installed as a package.
_HERE = Path(__file__).resolve()
_PROJECT_ROOT = _HERE.parents[3]
_SRC_ROOT = _PROJECT_ROOT / "src"
if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

from meeting_ai.config.markdown_profile import load_markdown_profile  # noqa: E402
from meeting_ai.config.topic_details import apply_topic_details  # noqa: E402
from meeting_ai.nodes.ingest import SUPPORTED_MEDIA_SUFFIXES  # noqa: E402
from meeting_ai.nodes.source_discovery import derive_run_id  # noqa: E402

# NOTE: absolute imports are required here because Streamlit executes this
# file as a top-level script ("__main__"), not as part of the
# meeting_ai.app package — relative imports would fail with
# "attempted relative import with no known parent package".
from meeting_ai.app.history import RunRecord, list_runs  # noqa: E402
from meeting_ai.app.i18n import (  # noqa: E402
    LANG_KO,
    SUPPORTED_LANGUAGES,
    Language,
    language_label,
    t as _t,
)
from meeting_ai.app.playback import (  # noqa: E402
    AnchoredItem,
    extract_anchored_items,
    find_run_media,
    is_audio_only,
    load_with_evidence,
)
from meeting_ai.app.quality import (  # noqa: E402
    LLMQualityIssue,
    check_gpu_status,
    check_llm_ready,
)
from meeting_ai.app.runner import PipelineRunner  # noqa: E402
from meeting_ai.app.stages import (  # noqa: E402
    hint as stage_hint,
    label as stage_label,
    visible_stages,
)
from meeting_ai.app.templates import EMPTY_TEMPLATE, TEMPLATES, Template  # noqa: E402
from meeting_ai.app.topics import (  # noqa: E402
    archive_topic_details,
    build_payload,
    parse_lines,
    write_temp_topic_details,
)


PROFILE_PATH = _PROJECT_ROOT / "meeting_profile.md"
DEFAULT_VIDEOS_DIR = _PROJECT_ROOT / "videos"
DEFAULT_RUNS_DIR = _PROJECT_ROOT / "runs"


# ─── i18n helpers ────────────────────────────────────────────────────────


def _lang() -> Language:
    return st.session_state.get("ui_lang", LANG_KO)


def t(key: str, *args: object) -> str:
    text = _t(key, _lang())
    if args:
        return text.format(*args)
    return text


# ─── Page setup ─────────────────────────────────────────────────────────


def _configure_page() -> None:
    # We must call set_page_config before any other Streamlit primitive, so
    # we set a static title here and update the browser tab via JS-free
    # markdown after the language is known. (Streamlit recommends only one
    # set_page_config call per session.)
    st.set_page_config(
        page_title="MOMO · Meeting Recap",
        page_icon="🎙️",
        layout="wide",
        initial_sidebar_state="expanded",
    )


def _inject_css() -> None:
    st.markdown(
        """
        <style>
          .momo-step-title { font-size: 1.05rem; font-weight: 600; margin-bottom: 0.25rem; }
          .momo-step-help  { color: #6b7280; font-size: 0.85rem; margin-bottom: 0.75rem; }
          .momo-core-badge {
            display: inline-block;
            background: #2563eb;
            color: #fff;
            font-size: 0.72rem;
            font-weight: 700;
            letter-spacing: 0.04em;
            padding: 0.15rem 0.5rem;
            border-radius: 999px;
            margin-left: 0.5rem;
            vertical-align: middle;
          }
          .momo-core-title {
            font-size: 1.35rem;
            font-weight: 700;
            margin-bottom: 0.25rem;
          }
          .momo-core-sub {
            color: #4b5563;
            font-size: 0.92rem;
            line-height: 1.55;
            margin-bottom: 0.75rem;
          }
          .momo-field-label {
            font-size: 0.95rem;
            font-weight: 600;
            margin: 0.25rem 0 0.15rem 0;
          }
          .momo-field-label-strong {
            font-size: 1.0rem;
            font-weight: 700;
            color: #1d4ed8;
            margin: 0.25rem 0 0.15rem 0;
          }
          .momo-field-help {
            color: #6b7280;
            font-size: 0.82rem;
            margin-bottom: 0.4rem;
          }
          .momo-count-pill {
            display: inline-block;
            background: #eff6ff;
            color: #1d4ed8;
            font-size: 0.78rem;
            padding: 0.1rem 0.55rem;
            border-radius: 999px;
            margin-top: 0.25rem;
          }
          .momo-cta button { font-size: 1.1rem !important; padding: 0.75rem 1.5rem !important; }
          .momo-stage-row  { padding: 0.15rem 0; font-size: 0.95rem; }
          .momo-stage-done { color: #16a34a; }
          .momo-stage-active { color: #2563eb; font-weight: 600; }
          .momo-stage-todo { color: #9ca3af; }
        </style>
        """,
        unsafe_allow_html=True,
    )


# ─── Session helpers ─────────────────────────────────────────────────────


def _state_defaults() -> None:
    st.session_state.setdefault("ui_lang", LANG_KO)
    st.session_state.setdefault("view", "new")  # 'new' | 'viewing'
    st.session_state.setdefault("runner", None)
    st.session_state.setdefault("selected_run_id", None)
    st.session_state.setdefault("temp_topic_path", None)
    st.session_state.setdefault("settings", _initial_settings())


def _initial_settings() -> dict:
    runtime = load_markdown_profile(PROFILE_PATH)
    rendering = runtime.get("pipeline_config", {}).get("rendering", {})
    profile = runtime.get("profile", {}).get("meeting_profile", {})
    models = runtime.get("models_config", {})
    asr_model = str(models.get("asr", {}).get("model") or "large-v3")
    model_to_preset = {"small": "fast", "medium": "balanced", "large-v3": "best"}
    return {
        "asr_preset": model_to_preset.get(asr_model, "best"),
        "llm_summary_mode": str(rendering.get("llm_summary_mode") or "thorough"),
        "enable_critique": bool(rendering.get("enable_critique", True)),
        "output_language": str(
            rendering.get("output_language")
            or profile.get("output_language")
            or "ko"
        ),
    }


# ─── Sidebar ────────────────────────────────────────────────────────────


def _render_sidebar() -> None:
    with st.sidebar:
        st.markdown("## " + t("brand.title"))
        st.caption(t("brand.tagline"))
        _render_gpu_status_panel()
        st.divider()
        _render_language_toggle()
        st.divider()

        if st.button(t("sidebar.new_run"), use_container_width=True, type="primary"):
            st.session_state.view = "new"
            st.session_state.selected_run_id = None
            st.session_state.runner = None
            st.rerun()

        st.markdown("### " + t("sidebar.history_heading"))
        records = list_runs(DEFAULT_RUNS_DIR)
        if not records:
            st.caption(t("sidebar.history_empty"))
        else:
            for record in records[:30]:
                if st.button(
                    record.display_label,
                    key="run_{0}".format(record.run_id),
                    use_container_width=True,
                ):
                    st.session_state.view = "viewing"
                    st.session_state.selected_run_id = record.run_id
                    st.session_state.runner = None
                    st.rerun()

        st.divider()
        with st.expander(t("sidebar.advanced"), expanded=False):
            _render_advanced_settings()


def _render_gpu_status_panel() -> None:
    status = check_gpu_status()
    st.session_state["gpu_status_ok"] = status.ok
    label = "{0}: {1}".format(t("gpu.label"), t("gpu.on") if status.ok else t("gpu.off"))
    if status.ok:
        st.success(label)
        st.caption(t("gpu.on_detail", status.name or "CUDA"))
        return

    st.error(label)
    st.warning(t("gpu.off_warning", status.detail or status.code))


def _render_language_toggle() -> None:
    current = _lang()
    options = list(SUPPORTED_LANGUAGES)
    selected = st.radio(
        t("sidebar.language"),
        options=options,
        index=options.index(current) if current in options else 0,
        format_func=language_label,
        horizontal=True,
        key="ui_lang_radio",
    )
    if selected != current:
        st.session_state.ui_lang = selected
        # Default the summary output language to match the UI mode. Users
        # can still override in 고급 설정 / Advanced afterwards — the next
        # toggle will re-sync. Technical terms and proper nouns are
        # preserved verbatim by the LLM prompts regardless of this choice.
        settings = st.session_state.get("settings")
        if isinstance(settings, dict):
            settings["output_language"] = selected
        st.rerun()


def _render_advanced_settings() -> None:
    settings = st.session_state.settings
    asr_options = ["fast", "balanced", "best"]
    if settings["asr_preset"] not in asr_options:
        settings["asr_preset"] = "best"
    settings["asr_preset"] = st.radio(
        t("sidebar.asr_label"),
        options=asr_options,
        index=asr_options.index(settings["asr_preset"]),
        format_func={
            "fast": t("sidebar.asr_fast"),
            "balanced": t("sidebar.asr_balanced"),
            "best": t("sidebar.asr_best"),
        }.get,
        horizontal=False,
        help=t("sidebar.asr_help"),
    )
    summary_options = ["fast", "thorough"]
    if settings["llm_summary_mode"] not in summary_options:
        settings["llm_summary_mode"] = "thorough"
    settings["llm_summary_mode"] = st.radio(
        t("sidebar.summary_mode"),
        options=summary_options,
        index=summary_options.index(settings["llm_summary_mode"]),
        format_func={
            "fast": t("sidebar.mode_fast"),
            "thorough": t("sidebar.mode_thorough"),
        }.get,
        help=t("sidebar.mode_help"),
    )
    settings["enable_critique"] = st.toggle(
        t("sidebar.critique"),
        value=settings["enable_critique"],
        help=t("sidebar.critique_help"),
    )
    output_options = ["ko", "en"]
    if settings["output_language"] not in output_options:
        settings["output_language"] = "ko"
    settings["output_language"] = st.selectbox(
        t("sidebar.output_language"),
        options=output_options,
        index=output_options.index(settings["output_language"]),
        format_func={"ko": t("sidebar.output_ko"), "en": t("sidebar.output_en")}.get,
        help=t("sidebar.output_language_help"),
    )


# ─── Main views ─────────────────────────────────────────────────────────


def _render_main() -> None:
    runner: Optional[PipelineRunner] = st.session_state.runner
    if runner is not None and runner.state.is_running:
        _render_progress(runner)
        return
    if runner is not None and runner.state.stage == "failed":
        _render_failed(runner)
        return
    if runner is not None and runner.state.stage == "done":
        _render_result_from_runner(runner)
        return
    if st.session_state.view == "viewing" and st.session_state.selected_run_id:
        _render_existing_run(st.session_state.selected_run_id)
        return
    _render_new_run_form()


# ── New run form ────────────────────────────────────────────────────────


def _render_new_run_form() -> None:
    st.markdown("# " + t("new.heading"))
    st.caption(t("new.caption"))

    st.markdown(
        '<div class="momo-step-title">' + t("new.step1_title") + "</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="momo-step-help">' + t("new.step1_help") + "</div>",
        unsafe_allow_html=True,
    )

    upload_tab, existing_tab = st.tabs([t("new.upload_tab"), t("new.existing_tab")])
    source_path: Optional[Path] = None
    with upload_tab:
        uploaded = st.file_uploader(
            t("new.upload_label"),
            type=[s.lstrip(".") for s in SUPPORTED_MEDIA_SUFFIXES],
            accept_multiple_files=False,
            label_visibility="collapsed",
            key="uploader",
        )
        if uploaded is not None:
            source_path = _persist_upload(uploaded)
            st.success(t("new.upload_success", source_path.name))
    with existing_tab:
        existing = _list_existing_media()
        if not existing:
            st.info(t("new.existing_empty"))
        else:
            choice = st.selectbox(
                t("new.existing_label"),
                options=existing,
                format_func=lambda p: p.name,
                index=None,
                placeholder=t("new.existing_placeholder"),
                key="existing_pick",
            )
            if choice is not None and uploaded is None:
                source_path = choice

    st.markdown("---")
    title, instruction_text, topics_text, must_check_text = _render_summary_guide_section()

    st.markdown("---")
    gpu_ok = bool(st.session_state.get("gpu_status_ok"))
    disabled = source_path is None or not gpu_ok
    disabled_help = None
    if source_path is None:
        disabled_help = t("cta.start_disabled_help")
    elif not gpu_ok:
        disabled_help = t("cta.gpu_disabled_help")
    st.markdown('<div class="momo-cta">', unsafe_allow_html=True)
    if st.button(
        t("cta.start"),
        type="primary",
        use_container_width=True,
        disabled=disabled,
        help=disabled_help,
    ):
        _kickoff_run(
            source_path=source_path,  # type: ignore[arg-type]
            title=title,
            custom_instruction=instruction_text,
            topics=parse_lines(topics_text),
            must_check=parse_lines(must_check_text),
        )
    st.markdown("</div>", unsafe_allow_html=True)


def _render_summary_guide_section() -> tuple:
    """Render the (visually-promoted) summary-guide section.

    Returns ``(title, instruction_text, topics_text, must_check_text)``
    straight from the form widgets. The free-form instruction is the most
    prominent field because what the user writes there flows directly
    into the LLM synthesis prompt.
    """
    _consume_pending_template()

    with st.container(border=True):
        st.markdown(
            '<div class="momo-core-title">'
            + t("guide.title")
            + '<span class="momo-core-badge">'
            + t("guide.core_badge")
            + "</span>"
            "</div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div class="momo-core-sub">' + t("guide.intro") + "</div>",
            unsafe_allow_html=True,
        )

        _render_template_row()

        # 🗣️ Free-form instruction — the most direct way for the user to
        # tell the AI what kind of summary they want. We promote it to
        # the top of the form because it has the highest priority in
        # the LLM prompt.
        st.markdown(
            '<div class="momo-field-label-strong">'
            + t("guide.instruction_label")
            + ' <span style="color:#9ca3af;font-weight:400;font-size:0.85rem;">'
            + t("guide.optional_suffix")
            + "</span></div>"
            '<div class="momo-field-help">' + t("guide.instruction_help") + "</div>",
            unsafe_allow_html=True,
        )
        instruction_text = st.text_area(
            t("guide.instruction_label"),
            placeholder=t("guide.instruction_placeholder"),
            height=110,
            key="form_instruction",
            label_visibility="collapsed",
        )

        st.markdown(
            '<div class="momo-field-label">'
            + t("guide.title_label")
            + ' <span style="color:#9ca3af;font-weight:400;">'
            + t("guide.optional_suffix")
            + "</span></div>",
            unsafe_allow_html=True,
        )
        title = st.text_input(
            t("guide.title_label"),
            placeholder=t("guide.title_placeholder"),
            key="form_title",
            label_visibility="collapsed",
        )

        col_topics, col_check = st.columns(2)
        with col_topics:
            st.markdown(
                '<div class="momo-field-label">' + t("guide.topics_label") + "</div>"
                '<div class="momo-field-help">' + t("guide.topics_help") + "</div>",
                unsafe_allow_html=True,
            )
            topics_text = st.text_area(
                t("guide.topics_label"),
                placeholder=t("guide.topics_placeholder"),
                height=170,
                key="form_topics",
                label_visibility="collapsed",
            )
            _render_count_pill(topics_text, count_key="guide.count_topics")
        with col_check:
            st.markdown(
                '<div class="momo-field-label">'
                + t("guide.must_check_label")
                + ' <span style="color:#9ca3af;font-weight:400;">'
                + t("guide.optional_suffix")
                + "</span></div>"
                '<div class="momo-field-help">' + t("guide.must_check_help") + "</div>",
                unsafe_allow_html=True,
            )
            must_check_text = st.text_area(
                t("guide.must_check_label"),
                placeholder=t("guide.must_check_placeholder"),
                height=170,
                key="form_must_check",
                label_visibility="collapsed",
            )
            _render_count_pill(must_check_text, count_key="guide.count_must_check")

        with st.expander(t("guide.examples_expander")):
            _render_template_examples()

    return title, instruction_text, topics_text, must_check_text


def _render_template_row() -> None:
    """Show one-click meeting-type presets."""
    st.markdown(
        '<div class="momo-field-help">' + t("guide.template_help") + "</div>",
        unsafe_allow_html=True,
    )
    lang = _lang()
    presets = list(TEMPLATES) + [EMPTY_TEMPLATE]
    cols = st.columns(len(presets))
    for col, template in zip(cols, presets):
        with col:
            if st.button(
                template.localized_label(lang),
                key="tpl_{0}".format(template.key),
                use_container_width=True,
                help=template.localized_blurb(lang),
            ):
                st.session_state["_pending_template"] = template.key
                st.rerun()


def _consume_pending_template() -> None:
    pending = st.session_state.pop("_pending_template", None)
    if pending is None:
        return
    template = _find_template(pending)
    if template is None:
        return
    lang = _lang()
    st.session_state["form_title"] = template.localized_title(lang)
    st.session_state["form_instruction"] = template.localized_instruction(lang)
    st.session_state["form_topics"] = "\n".join(template.localized_topics(lang))
    st.session_state["form_must_check"] = "\n".join(template.localized_must_check(lang))


def _find_template(key: str) -> Optional[Template]:
    if key == EMPTY_TEMPLATE.key:
        return EMPTY_TEMPLATE
    for template in TEMPLATES:
        if template.key == key:
            return template
    return None


def _render_count_pill(text: str, *, count_key: str) -> None:
    count = len(parse_lines(text))
    if count == 0:
        return
    st.markdown(
        '<span class="momo-count-pill">' + t(count_key, count) + "</span>",
        unsafe_allow_html=True,
    )


def _render_template_examples() -> None:
    st.caption(t("guide.examples_intro"))
    lang = _lang()
    for template in TEMPLATES:
        st.markdown(
            "**{0}** — {1}".format(
                template.localized_label(lang), template.localized_blurb(lang)
            )
        )
        instruction = template.localized_instruction(lang)
        if instruction:
            st.markdown("{0} `{1}`".format(t("guide.example_instruction"), instruction))
        topics = template.localized_topics(lang)
        if topics:
            st.markdown(
                "{0} {1}".format(
                    t("guide.example_topics"),
                    ", ".join("`{0}`".format(item) for item in topics),
                )
            )
        must_check = template.localized_must_check(lang)
        if must_check:
            st.markdown(
                "{0} {1}".format(
                    t("guide.example_must_check"),
                    ", ".join("`{0}`".format(item) for item in must_check),
                )
            )
        st.markdown("")


def _persist_upload(uploaded) -> Path:
    DEFAULT_VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = uploaded.name.replace(" ", "_")
    target = DEFAULT_VIDEOS_DIR / "gui_{0}_{1}".format(stamp, safe_name)
    with target.open("wb") as fh:
        fh.write(uploaded.getbuffer())
    return target


def _list_existing_media() -> List[Path]:
    if not DEFAULT_VIDEOS_DIR.exists():
        return []
    items = [
        p
        for p in DEFAULT_VIDEOS_DIR.iterdir()
        if p.is_file() and p.suffix.lower() in SUPPORTED_MEDIA_SUFFIXES
    ]
    return sorted(items, key=lambda p: p.stat().st_mtime, reverse=True)


# ── Kickoff ─────────────────────────────────────────────────────────────


def _kickoff_run(
    *,
    source_path: Path,
    title: str,
    custom_instruction: str,
    topics: List[str],
    must_check: List[str],
) -> None:
    settings = st.session_state.settings
    runtime = load_markdown_profile(PROFILE_PATH)

    pipeline_config = runtime["pipeline_config"]
    models_config = runtime["models_config"]
    profile = runtime["profile"]
    automation = runtime.get("automation", {})

    pipeline_config.setdefault("rendering", {})
    pipeline_config["rendering"]["llm_summary_mode"] = settings["llm_summary_mode"]
    pipeline_config["rendering"]["enable_critique"] = bool(settings["enable_critique"])
    pipeline_config["rendering"]["output_language"] = settings["output_language"]
    profile.setdefault("meeting_profile", {})["output_language"] = settings["output_language"]

    preset_to_model = {"fast": "small", "balanced": "medium", "best": "large-v3"}
    models_config.setdefault("asr", {})["model"] = preset_to_model[settings["asr_preset"]]

    quality_issue = check_llm_ready(models_config)
    if quality_issue is not None:
        st.error(_quality_issue_message(quality_issue))
        return

    payload = build_payload(title, topics, must_check, custom_instruction)
    temp_topic_path = write_temp_topic_details(payload)
    runtime = apply_topic_details(runtime, temp_topic_path)
    profile = runtime["profile"]
    profile.setdefault("meeting_profile", {})["output_language"] = settings["output_language"]

    run_id = derive_run_id(source_path, automation.get("run_id", "auto"))

    runner = PipelineRunner(
        source_path=source_path,
        runs_dir=DEFAULT_RUNS_DIR,
        run_id=run_id,
        profile=profile,
        pipeline_config=pipeline_config,
        models_config=models_config,
    )
    runner.start()
    st.session_state.runner = runner
    st.session_state.temp_topic_path = str(temp_topic_path) if temp_topic_path else None
    st.session_state.view = "running"
    st.rerun()


def _quality_issue_message(issue: LLMQualityIssue) -> str:
    if issue.code == "missing_provider":
        return t("quality.missing_provider")
    if issue.code == "disabled_stub_provider":
        return t("quality.disabled_stub_provider", issue.provider)
    if issue.code == "unsupported_provider":
        return t("quality.unsupported_provider", issue.provider)
    if issue.code == "missing_model":
        return t("quality.missing_model", issue.provider)
    if issue.code == "ollama_unreachable":
        return t("quality.ollama_unreachable", issue.model, issue.detail)
    if issue.code == "ollama_model_missing":
        return t("quality.ollama_model_missing", issue.model, issue.detail)
    return t("quality.generic", issue.provider, issue.detail)


# ── Progress ───────────────────────────────────────────────────────────


@st.fragment(run_every="1s")
def _render_progress_fragment() -> None:
    runner: Optional[PipelineRunner] = st.session_state.get("runner")
    if runner is None:
        return
    state = runner.state
    settings = st.session_state.settings
    stages = visible_stages(bool(settings["enable_critique"]))
    lang = _lang()

    elapsed = _format_elapsed(state.elapsed)
    st.markdown("# " + t("progress.heading"))
    st.caption(t("progress.caption", elapsed))

    current = state.stage
    done_set = set(state.completed)
    for stage in stages:
        if stage in done_set:
            line = '✅ <span class="momo-stage-done">{0}</span>'.format(
                stage_label(stage, lang)
            )
        elif stage == current:
            line = '🔵 <span class="momo-stage-active">{0}</span> — {1}'.format(
                stage_label(stage, lang), stage_hint(stage, lang)
            )
        else:
            line = '⬜ <span class="momo-stage-todo">{0}</span>'.format(
                stage_label(stage, lang)
            )
        st.markdown(
            '<div class="momo-stage-row">{0}</div>'.format(line),
            unsafe_allow_html=True,
        )

    if state.is_done:
        st.rerun()


def _render_progress(runner: PipelineRunner) -> None:
    _render_progress_fragment()


def _format_elapsed(seconds: float) -> str:
    seconds = int(max(0, seconds))
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    if h:
        return t("elapsed.hours", h, m, s)
    if m:
        return t("elapsed.minutes", m, s)
    return t("elapsed.seconds", s)


# ── Failure ─────────────────────────────────────────────────────────────


def _render_failed(runner: PipelineRunner) -> None:
    st.markdown("# " + t("fail.heading"))
    st.error(runner.state.error or t("fail.unknown"))
    if runner.state.error_trace:
        with st.expander(t("fail.trace")):
            st.code(runner.state.error_trace)
    if st.button(t("fail.retry"), type="primary"):
        st.session_state.runner = None
        st.session_state.view = "new"
        st.rerun()


# ── Result (just finished) ──────────────────────────────────────────────


def _render_result_from_runner(runner: PipelineRunner) -> None:
    result = runner.state.result
    if result is None:  # pragma: no cover - defensive
        st.warning(t("result.missing"))
        return

    temp_path_value = st.session_state.get("temp_topic_path")
    if temp_path_value:
        archive_topic_details(Path(temp_path_value), result.run_dir)
        st.session_state.temp_topic_path = None

    elapsed = _format_elapsed(runner.state.elapsed)
    st.success(t("result.success", elapsed))
    _render_run_results(
        run_id=result.run_id,
        run_dir=result.run_dir,
        summary_md=result.markdown_path,
        evidence_md=result.evidence_path,
        transcript_md=result.run_dir / "transcript" / "normalized_transcript.md",
        summary_json=result.final_summary_path,
    )


# ── Result (existing run) ───────────────────────────────────────────────


def _render_existing_run(run_id: str) -> None:
    run_dir = DEFAULT_RUNS_DIR / run_id
    if not run_dir.exists():
        st.warning(t("result.run_missing", run_id))
        return
    record_list = [r for r in list_runs(DEFAULT_RUNS_DIR) if r.run_id == run_id]
    if not record_list:
        st.warning(t("result.run_incomplete"))
        return
    record: RunRecord = record_list[0]
    st.markdown("# 📄 {0}".format(record.title or run_id))
    if record.finished_at:
        st.caption(t("result.completed_at", record.finished_at.strftime("%Y-%m-%d %H:%M")))
    _render_run_results(
        run_id=run_id,
        run_dir=run_dir,
        summary_md=record.final_summary_md,
        evidence_md=record.evidence_md,
        transcript_md=record.transcript_md,
        summary_json=record.final_summary_json,
    )


def _render_run_results(
    *,
    run_id: str,
    run_dir: Path,
    summary_md: Optional[Path],
    evidence_md: Optional[Path],
    transcript_md: Optional[Path],
    summary_json: Optional[Path],
) -> None:
    summary_tab, playback_tab, evidence_tab, transcript_tab, files_tab = st.tabs(
        [
            t("result.tab_summary"),
            t("result.tab_playback"),
            t("result.tab_evidence"),
            t("result.tab_transcript"),
            t("result.tab_files"),
        ]
    )
    with summary_tab:
        _render_markdown_file(summary_md, t("result.summary_missing"))
    with playback_tab:
        _render_playback_panel(run_id=run_id, run_dir=run_dir)
    with evidence_tab:
        if evidence_md is None:
            st.info(t("result.evidence_missing"))
        else:
            _render_markdown_file(evidence_md, t("result.evidence_missing"))
    with transcript_tab:
        if transcript_md is None:
            st.info(t("result.transcript_missing"))
        else:
            _render_markdown_file(transcript_md, t("result.transcript_missing"))
    with files_tab:
        _render_files_panel(run_dir, summary_md, evidence_md, summary_json)


# ── Playback tab ───────────────────────────────────────────────────────


_PLAYBACK_SECTION_ORDER = (
    "key_topics",
    "decisions",
    "actions",
    "worth_noting",
    "next_meeting",
)


def _render_playback_panel(*, run_id: str, run_dir: Path) -> None:
    """Render the interactive 'jump to moment' tab."""
    summary = load_with_evidence(run_dir)
    if summary is None:
        st.info(t("result.playback_no_evidence_json"))
        return

    items = extract_anchored_items(summary)
    if not items:
        st.info(t("result.playback_no_items"))
        return

    media_path = find_run_media(summary, run_dir, DEFAULT_VIDEOS_DIR)
    seek_state_key = "video_seek_{0}".format(run_id)
    seek_seconds = int(st.session_state.get(seek_state_key, 0))

    if media_path is None:
        recorded = summary.get("source_file") or "?"
        st.warning(t("result.playback_no_media", recorded))
    else:
        try:
            if is_audio_only(media_path):
                st.audio(str(media_path), start_time=seek_seconds)
            else:
                st.video(str(media_path), start_time=seek_seconds)
        except Exception as exc:  # pragma: no cover - st.video is fairly forgiving
            st.error(t("result.read_error", exc))

    st.caption(t("result.playback_help"))

    grouped: dict = {section: [] for section in _PLAYBACK_SECTION_ORDER}
    for item in items:
        grouped.setdefault(item.section, []).append(item)

    for section in _PLAYBACK_SECTION_ORDER:
        section_items = grouped.get(section) or []
        if not section_items:
            continue
        st.markdown("### " + t("result.playback_section_" + section))
        for idx, item in enumerate(section_items):
            _render_anchored_item(
                item,
                run_id=run_id,
                section=section,
                idx=idx,
                seek_state_key=seek_state_key,
                media_available=media_path is not None,
            )
        st.markdown("")


def _render_anchored_item(
    item: AnchoredItem,
    *,
    run_id: str,
    section: str,
    idx: int,
    seek_state_key: str,
    media_available: bool,
) -> None:
    primary = item.primary_text or ""
    if primary:
        st.markdown("**{0}**".format(primary))
    if item.secondary_text:
        st.caption(item.secondary_text)
    if item.support:
        support_key = "result.playback_support_" + item.support.lower()
        st.caption("· " + t(support_key))

    if not item.timestamps:
        st.caption(t("result.playback_no_timestamps"))
        return

    button_cols = st.columns(min(len(item.timestamps), 6))
    for col_idx, ts in enumerate(item.timestamps):
        col = button_cols[col_idx % len(button_cols)]
        key = "seek_{0}_{1}_{2}_{3}".format(run_id, section, idx, ts.seconds)
        if col.button(
            "▶ {0}".format(ts.label),
            key=key,
            use_container_width=True,
            disabled=not media_available,
            help=None if media_available else t("result.playback_no_media", "?"),
        ):
            st.session_state[seek_state_key] = ts.seconds
            st.rerun()


def _render_markdown_file(path: Optional[Path], not_found_msg: str) -> None:
    if path is None or not path.exists():
        st.info(not_found_msg)
        return
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        st.error(t("result.read_error", exc))
        return
    st.markdown(text)


def _render_files_panel(
    run_dir: Path,
    summary_md: Optional[Path],
    evidence_md: Optional[Path],
    summary_json: Optional[Path],
) -> None:
    st.caption(t("result.files_caption", run_dir))
    cols = st.columns(3)
    items = [
        (t("result.download_summary"), summary_md),
        (t("result.download_evidence"), evidence_md),
        (t("result.download_json"), summary_json),
    ]
    for col, (caption, path) in zip(cols, items):
        with col:
            if path is None or not path.exists():
                st.caption("{0}\n{1}".format(caption, t("result.download_missing")))
                continue
            data = path.read_bytes()
            col.download_button(
                caption,
                data=data,
                file_name=path.name,
                use_container_width=True,
            )


# ─── Entry point ────────────────────────────────────────────────────────


def main() -> None:
    _configure_page()
    _inject_css()
    _state_defaults()
    _render_sidebar()
    _render_main()


main()
