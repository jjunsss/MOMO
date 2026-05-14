# Pipeline

How MOMO turns a video into an evidence-anchored recap.

## Stages

Four stages, each with one job:

| Stage | Component | Role |
|---|---|---|
| **Speech → Text** | OpenAI Whisper `large-v3` (local, GPU) | the recording becomes a Korean transcript with per-segment timestamps |
| **Filter** | rule-based chunk salience (no LLM) | each 6–10 min chunk is marked *kept* or *skipped* before any LLM sees it |
| **Recap** | Qwen 3.5 9B via Ollama *(or any powerful LLM you can use)* | reads the kept chunks and produces the meeting summary |
| **Render** | deterministic Markdown renderer (no LLM) | turns the validated JSON into the public recap and the evidence file |

## Flow

```text
videos/meeting.mp4
        │
        ▼   ffmpeg
audio.wav  (16 kHz mono)
        │
        ▼   Whisper large-v3
raw_transcript.json ── normalize ──▶ normalized_transcript.json
        │
        ▼   chunk (6–10 min, 30 s overlap)
chunks.json
        │
        ▼   rule-based salience pre-pass
chunk_analysis.jsonl   (kept / skipped)
        │
        ▼   LLM: per-slot extraction
        │   (thinking on, JSON schema enforced)
slot_extracts.jsonl
        │
        ▼   LLM: 2-pass summary write  (prose → strict JSON)
final_summary.draft.json
        │
        ▼   LLM: CoVe-style critique  (evidence-anchored verification)
final_summary.json ── deterministic render ──▶ final_summary.md
                                                + summary_evidence.md
```

## Defaults

Defaults assume a 16 GB local GPU (RTX 4080-class): Whisper `large-v3`
for transcription, Qwen 3.5 9B with thinking for the recap. Swap any
stage by editing `meeting_profile.md`.

## Output artifacts

Every run produces:

```text
runs/{run_id}/
  summaries/
    final_summary.md       # the recap you share
    final_summary.json     # structured output
  evidence/
    summary_evidence.md    # timestamps, support levels, transcript snippets
    final_summary.with_evidence.json
  transcript/
    normalized_transcript.md
    raw_transcript.json
  chunks/
    chunk_analysis.jsonl
```

Two user-facing files:

- `summaries/final_summary.md` — **Final recap.** TL;DR, key topics,
  decisions, action items, next meeting, worth-noting. Prose and tables.
- `evidence/summary_evidence.md` — **Evidence file.** Each item from
  the recap with the transcript snippet it came from, the timestamp
  range, and a confidence label (`strong` = direct quote, `weak` =
  paraphrase, `inferred` = reasoned from context).

To tune ASR decoding, LLM provider/model, chunk sizes, output sections,
or evidence toggles, edit `meeting_profile.md`.
