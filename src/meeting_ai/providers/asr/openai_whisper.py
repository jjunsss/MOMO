"""OpenAI Whisper local ASR provider."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional


def transcribe_audio(audio_path: Path, source_path: Path, asr_config: Dict[str, Any]) -> Dict[str, Any]:
    try:
        import torch
        import whisper
    except ImportError as exc:
        raise RuntimeError(
            "openai-whisper runtime is not installed. Use the project .venv or install ASR dependencies."
        ) from exc

    model_name = str(asr_config.get("model", "small"))
    configured_device = str(asr_config.get("device", "auto"))
    if configured_device == "auto":
        device = "cuda" if torch.cuda.is_available() else "cpu"
    else:
        device = configured_device

    language = _language_value(asr_config.get("language", "auto"))
    fp16 = bool(asr_config.get("fp16", device == "cuda")) and device == "cuda"
    decode_options = _decode_options(asr_config)

    model = whisper.load_model(model_name, device=device)
    result = model.transcribe(
        str(audio_path),
        language=language,
        fp16=fp16,
        verbose=False,
        **decode_options,
    )

    segments = []
    for index, segment in enumerate(result.get("segments", []), start=1):
        segments.append(
            {
                "id": "t{0:06d}".format(index),
                "start": float(segment.get("start", 0.0)),
                "end": float(segment.get("end", 0.0)),
                "text": str(segment.get("text", "")).strip(),
                "speaker": None,
                "confidence": None,
                "avg_logprob": _optional_float(segment.get("avg_logprob")),
                "compression_ratio": _optional_float(segment.get("compression_ratio")),
                "no_speech_prob": _optional_float(segment.get("no_speech_prob")),
            }
        )

    duration = segments[-1]["end"] if segments else 0.0
    return {
        "meeting_id": source_path.stem,
        "title": source_path.stem,
        "source_file": str(source_path),
        "language": result.get("language", language or "unknown"),
        "duration_sec": duration,
        "segments": segments,
        "metadata": {
            "asr_provider": "openai_whisper",
            "asr_model": model_name,
            "device": device,
            "fp16": fp16,
            "decode_options": decode_options,
        },
    }


def _language_value(value: Any) -> Optional[str]:
    if value in {None, "", "auto"}:
        return None
    return str(value)


def _decode_options(asr_config: Dict[str, Any]) -> Dict[str, Any]:
    return {
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


def _bool_config(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}
    return bool(value)


def _optional_float(value: Any) -> Optional[float]:
    if value in {None, ""}:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
