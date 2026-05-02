"""Transcript chunking."""

from __future__ import annotations

from typing import Any, Dict, List


def _chunk_text(segments: List[Dict[str, Any]]) -> str:
    return "\n".join("[{0}] {1}".format(segment["id"], segment["text"]) for segment in segments)


def build_chunks(transcript: Dict[str, Any], chunking_config: Dict[str, Any]) -> List[Dict[str, Any]]:
    target_seconds = int(chunking_config.get("target_minutes", 6) * 60)
    max_seconds = int(chunking_config.get("max_minutes", 10) * 60)
    overlap_seconds = int(chunking_config.get("overlap_seconds", 30))
    segments = transcript.get("segments", [])
    chunks: List[Dict[str, Any]] = []
    current: List[Dict[str, Any]] = []
    chunk_start = None

    for segment in segments:
        if chunk_start is None:
            chunk_start = segment["start"]
        current.append(segment)
        elapsed = segment["end"] - chunk_start
        should_cut = elapsed >= target_seconds or elapsed >= max_seconds
        if should_cut:
            chunks.append(_make_chunk(len(chunks) + 1, current))
            current = [
                item for item in current if segment["end"] - item["start"] <= overlap_seconds
            ]
            chunk_start = current[0]["start"] if current else None

    if current:
        chunks.append(_make_chunk(len(chunks) + 1, current))

    for index, chunk in enumerate(chunks):
        if index > 0:
            chunk["prev_context"] = chunks[index - 1]["text"][-500:]
        if index + 1 < len(chunks):
            chunk["next_context"] = chunks[index + 1]["text"][:500]
    return chunks


def _make_chunk(index: int, segments: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "chunk_id": "c{0:04d}".format(index),
        "start": segments[0]["start"],
        "end": segments[-1]["end"],
        "text": _chunk_text(segments),
        "segment_ids": [segment["id"] for segment in segments],
        "segments": [
            {
                "id": segment["id"],
                "start": segment["start"],
                "end": segment["end"],
                "text": segment["text"],
            }
            for segment in segments
        ],
        "prev_context": None,
        "next_context": None,
        "rough_topic_hint": None,
    }
