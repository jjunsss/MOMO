"""Pipeline orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Optional


from meeting_ai.nodes.analyze_chunk import analyze_chunks
from meeting_ai.nodes.audio import extract_audio
from meeting_ai.nodes.chunk import build_chunks
from meeting_ai.nodes.ingest import is_media_source, is_transcript_source, load_source_transcript
from meeting_ai.nodes.llm_critique import critique_summary
from meeting_ai.nodes.llm_direct_synthesize import synthesize_direct_with_llm
from meeting_ai.nodes.llm_extract import extract_per_slot
from meeting_ai.nodes.llm_synthesize import synthesize_with_llm
from meeting_ai.nodes.normalize import normalize_transcript
from meeting_ai.nodes.required_search import build_required_search_report
from meeting_ai.nodes.verify import verify_summary
from meeting_ai.providers.asr.openai_whisper import transcribe_audio
from meeting_ai.providers.llm import LLMError, build_llm_provider
from meeting_ai.renderers.evidence import (
    render_summary_evidence_markdown,
    strip_evidence_fields,
)
from meeting_ai.renderers.markdown import render_summary_markdown
from meeting_ai.renderers.transcript import render_transcript_markdown
from meeting_ai.schemas.summary import validate_final_summary
from meeting_ai.utils.io import ensure_dir, read_json, write_json, write_jsonl, write_text


StageCallback = Optional[Callable[[str], None]]


@dataclass(frozen=True)
class PipelineResult:
    run_id: str
    run_dir: Path
    final_summary_path: Path
    markdown_path: Path
    evidence_path: Path


def _default_run_id(source_path: Path) -> str:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return "{0}_{1}".format(stamp, source_path.stem)


def _prepare_run_dirs(runs_dir: Path, run_id: str) -> Dict[str, Path]:
    run_dir = runs_dir / run_id
    paths = {
        "run": run_dir,
        "source": run_dir / "source",
        "transcript": run_dir / "transcript",
        "chunks": run_dir / "chunks",
        "summaries": run_dir / "summaries",
        "evidence": run_dir / "evidence",
        "logs": run_dir / "logs",
    }
    for path in paths.values():
        ensure_dir(path)
    return paths


def process_transcript_source(
    source_path: Path,
    runs_dir: Path,
    run_id: Optional[str],
    profile: Dict[str, Any],
    pipeline_config: Dict[str, Any],
    models_config: Optional[Dict[str, Any]] = None,
    on_stage: StageCallback = None,
) -> PipelineResult:
    def emit(stage: str) -> None:
        if on_stage is not None:
            on_stage(stage)

    emit("prepare")
    actual_run_id = run_id or _default_run_id(source_path)
    paths = _prepare_run_dirs(runs_dir, actual_run_id)
    models = models_config or {}
    rendering = pipeline_config.get("rendering", {})
    extraction_keywords = pipeline_config.get("extraction", {}).get("keywords")

    raw_transcript = _load_or_create_transcript(
        source_path, paths, models.get("asr", {}), on_stage=on_stage
    )
    emit("chunk")
    normalized = normalize_transcript(raw_transcript)
    chunks = build_chunks(normalized, pipeline_config.get("chunking", {}))
    analyses = analyze_chunks(
        chunks,
        profile.get("required_search_items", []),
        keywords=extraction_keywords,
    )
    required_report = build_required_search_report(
        required_items=profile.get("required_search_items", []),
        transcript=normalized,
        chunk_analyses=analyses,
    )

    llm_config = models.get("llm", {})
    try:
        llm_provider = build_llm_provider(llm_config)
    except ValueError as exc:
        raise LLMError(str(exc)) from exc
    llm_summary_mode = str(rendering.get("llm_summary_mode", "fast")).lower().strip()
    slot_extracts: list = []
    extraction_meta: dict = {}
    emit("synthesize")
    try:
        if llm_summary_mode in {"fast", "direct", "direct_json", "one_pass"}:
            draft_summary = synthesize_direct_with_llm(
                transcript=normalized,
                chunks=chunks,
                required_search_report=required_report,
                profile=profile,
                rendering=rendering,
                llm=llm_provider,
                run_id=actual_run_id,
                source_file=str(source_path),
                chunk_analyses=analyses,
                model_info={"provider": llm_provider.name, "model": llm_config.get("model")},
            )
        else:
            slot_extracts, extraction_meta = extract_per_slot(
                transcript=normalized,
                chunks=chunks,
                profile=profile,
                llm=llm_provider,
                single_pass_token_limit=int(rendering.get("single_pass_token_limit", 60_000)),
                max_items_per_slot=int(rendering.get("max_items_per_slot", 8)),
                meeting_id=str(normalized.get("meeting_id", actual_run_id)),
            )
            draft_summary = synthesize_with_llm(
                transcript=normalized,
                chunks=chunks,
                slot_extracts=slot_extracts,
                required_search_report=required_report,
                profile=profile,
                rendering=rendering,
                llm=llm_provider,
                run_id=actual_run_id,
                source_file=str(source_path),
                extraction_meta=extraction_meta,
                model_info={"provider": llm_provider.name, "model": llm_config.get("model")},
            )
        if rendering.get("enable_critique", True):
            emit("critique")
            draft_summary = critique_summary(draft_summary, normalized, llm_provider)
    except LLMError as exc:
        raise LLMError("LLM synthesis failed: {0}".format(exc)) from exc
    emit("verify")
    verification_report, final_summary = verify_summary(draft_summary)
    validate_final_summary(final_summary)
    public_summary = strip_evidence_fields(final_summary)
    emit("render")
    markdown = render_summary_markdown(public_summary)

    write_json(paths["transcript"] / "raw_transcript.json", raw_transcript)
    write_json(paths["transcript"] / "normalized_transcript.json", normalized)
    if rendering.get("write_transcript_markdown", True):
        transcript_markdown = render_transcript_markdown(normalized)
        write_text(paths["transcript"] / "normalized_transcript.md", transcript_markdown)
    write_json(paths["chunks"] / "chunks.json", chunks)
    if rendering.get("write_chunk_analysis_jsonl", True):
        write_jsonl(paths["chunks"] / "chunk_analysis.jsonl", analyses)
    slot_extracts_path = paths["chunks"] / "slot_extracts.jsonl"
    if slot_extracts:
        write_jsonl(slot_extracts_path, slot_extracts)
    elif slot_extracts_path.exists():
        slot_extracts_path.unlink()
    _clean_summary_artifacts(paths["summaries"], paths["evidence"])
    evidence_path = paths["evidence"] / "summary_evidence.md"
    if rendering.get("write_evidence_report", True):
        write_json(paths["evidence"] / "required_search_report.json", required_report)
        write_json(paths["evidence"] / "final_summary.draft.json", draft_summary)
        write_json(paths["evidence"] / "verification_report.json", verification_report)
        write_json(paths["evidence"] / "final_summary.with_evidence.json", final_summary)
        write_text(evidence_path, render_summary_evidence_markdown(final_summary, normalized))
    final_summary_path = paths["summaries"] / "final_summary.json"
    markdown_path = paths["summaries"] / "final_summary.md"
    write_json(final_summary_path, public_summary)
    write_text(markdown_path, markdown)

    emit("done")
    return PipelineResult(
        run_id=actual_run_id,
        run_dir=paths["run"],
        final_summary_path=final_summary_path,
        markdown_path=markdown_path,
        evidence_path=evidence_path,
    )


def _clean_summary_artifacts(summary_dir: Path, evidence_dir: Path) -> None:
    for filename in [
        "required_search_report.json",
        "final_summary.draft.json",
        "verification_report.json",
        "final_summary.with_evidence.json",
        "summary_evidence.md",
    ]:
        path = summary_dir / filename
        if path.exists():
            path.unlink()
    legacy_dir = evidence_dir / "legacy_summaries"
    for path in summary_dir.glob("*.bak"):
        ensure_dir(legacy_dir)
        destination = legacy_dir / path.name
        if destination.exists():
            destination.unlink()
        path.replace(destination)


def _load_or_create_transcript(
    source_path: Path,
    paths: Dict[str, Path],
    asr_config: Dict[str, Any],
    on_stage: StageCallback = None,
) -> Dict[str, Any]:
    raw_transcript_path = paths["transcript"] / "raw_transcript.json"
    if raw_transcript_path.exists() and is_transcript_source(source_path):
        return read_json(raw_transcript_path)

    if is_transcript_source(source_path):
        return load_source_transcript(source_path)

    if is_media_source(source_path):
        if raw_transcript_path.exists():
            cached = read_json(raw_transcript_path)
            if _cached_transcript_matches(cached, asr_config):
                return cached
        if on_stage is not None:
            on_stage("audio")
        audio_path = extract_audio(source_path, paths["source"] / "audio.wav")
        provider = asr_config.get("provider", "openai_whisper")
        if provider != "openai_whisper":
            raise ValueError("unsupported ASR provider: {0}".format(provider))
        if on_stage is not None:
            on_stage("transcribe")
        return transcribe_audio(audio_path, source_path, asr_config)

    return load_source_transcript(source_path)


def _cached_transcript_matches(transcript: Dict[str, Any], asr_config: Dict[str, Any]) -> bool:
    metadata = transcript.get("metadata") or {}
    expected_provider = asr_config.get("provider", "openai_whisper")
    expected_model = asr_config.get("model", "large-v3")
    expected_language = asr_config.get("language", "auto")
    actual_language = transcript.get("language") or metadata.get("language")

    if metadata.get("asr_provider") != expected_provider:
        return False
    if metadata.get("asr_model") != expected_model:
        return False
    if expected_language not in {None, "", "auto"} and actual_language != expected_language:
        return False
    if not _decode_options_match(metadata.get("decode_options"), asr_config):
        return False
    return True


def _decode_options_match(actual: Any, asr_config: Dict[str, Any]) -> bool:
    if not isinstance(actual, dict):
        return False
    expected = {
        "temperature": float(asr_config.get("temperature", 0.0)),
        "condition_on_previous_text": _bool_config(
            asr_config.get("condition_on_previous_text", False)
        ),
        "no_speech_threshold": float(asr_config.get("no_speech_threshold", 0.6)),
        "logprob_threshold": float(asr_config.get("logprob_threshold", -1.0)),
        "compression_ratio_threshold": float(
            asr_config.get("compression_ratio_threshold", 2.4)
        ),
    }
    for key, expected_value in expected.items():
        actual_value = actual.get(key)
        if isinstance(expected_value, bool):
            if _bool_config(actual_value) != expected_value:
                return False
            continue
        try:
            if float(actual_value) != expected_value:
                return False
        except (TypeError, ValueError):
            return False
    return True


def _bool_config(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}
    return bool(value)
