# MOMO

*Short for **M**eeting **MO**ments.* MOMO turns long Zoom recordings into
clean meeting recaps.

Drop a recording into `videos/`, write the few things you care about in
`topic_details.json`, and MOMO produces a Markdown recap plus a separate
evidence file.

## The Pipeline

Four stages, each with one job:

| Stage | Component | Role |
|---|---|---|
| **Speech → Text** | OpenAI Whisper `large-v3` (local, GPU) | the recording becomes a Korean transcript with per-segment timestamps |
| **Filter** | rule-based chunk salience (no LLM) | each 6–10 min chunk is marked *kept* or *skipped* before any LLM sees it |
| **Recap** | Qwen 3.5 9B via Ollama *(or any OpenAI-compatible endpoint)* | reads the kept chunks and produces the meeting summary |
| **Render** | deterministic Markdown renderer (no LLM) | turns the validated JSON into the public recap and the evidence file |

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
        ▼   LLM: CoVe critique  (evidence-anchored verification)
final_summary.json ── deterministic render ──▶ final_summary.md
                                                + summary_evidence.md
```

Defaults assume a 16 GB local GPU (RTX 4080-class): Whisper `large-v3` for
transcription, Qwen 3.5 9B with thinking for the recap. Swap any stage in
`meeting_profile.md`.

## Why MOMO

What I want from a meeting recap, in order:

- the shared summary should read clean — no timestamps, no audit metadata
- the evidence should still exist, just in a separate file
- I shouldn't edit prompts or YAML before every meeting
- long Korean meetings need date/time and repetition safeguards a raw
  transcript-to-summary pass does not give you

n8n-style video → Whisper → LLM templates handle the wiring fine; what they
miss is evidence separation, GPU-aware defaults, restartable runs, topic
steering, and a recap flow that doesn't just sort chunks by time.

## What It Does

MOMO turns this:

```text
videos/meeting.mp4
topic_details.json
```

into this:

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

## Quick Start

### 1. Create a Conda environment

Conda handles `ffmpeg`, CUDA, and PyTorch with less friction than `venv`,
especially on GPU machines.

```bash
conda create -n momo python=3.10 -y
conda activate momo
python -m pip install --upgrade pip setuptools wheel
```

`venv` works too if you already have ffmpeg + CUDA set up.

### 2. Install ffmpeg

With Conda:

```bash
conda install -c conda-forge ffmpeg -y
```

Or use your system package manager:

```bash
sudo apt-get update
sudo apt-get install -y ffmpeg
```

### 3. Install PyTorch

For CUDA 12.1:

```bash
conda install pytorch torchaudio pytorch-cuda=12.1 -c pytorch -c nvidia -y
```

CPU-only? Use the command from the official PyTorch installer page.

### 4. Install MOMO

```bash
python -m pip install openai-whisper PyYAML
python -m pip install -e .
```

> The Python import path is `meeting_ai` (the project's original name). The
> `momo` and `meeting-ai` commands point at the same entrypoint — a future
> release will rename the package itself.

### 5. Install the local LLM

Install Ollama and pull a model that fits your GPU.

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama serve
ollama pull qwen3.5:9b
```

Then set the model in `meeting_profile.md`:

```text
llm_provider: ollama
llm_model: qwen3.5:9b
llm_base_url: http://localhost:11434
```

## How To Use

### 1. Put a recording in `videos/`

```text
videos/
  Screen_Recording_20260429_172841_Zoom.mp4
```

The newest media file is picked automatically.

### 2. Edit `topic_details.json`

Plain strings are enough.

```json
{
  "title": "Research Meeting",
  "topics": [
    "main experiment result",
    "demo direction",
    "next meeting"
  ],
  "must_check": [
    "do not confuse dates and times",
    "separate visual features from text embeddings"
  ]
}
```

### 3. Run

```bash
momo
```

`meeting-ai` still works as an alias.

## Configuration

Most runs only need `topic_details.json`.

Advanced defaults live in `meeting_profile.md`:

- ASR model and decoding options
- LLM provider/model
- chunk sizes
- output sections
- evidence report toggles

ASR default is Whisper `large-v3`. The profile turns off previous-text
conditioning and keeps silence thresholds explicit, which cuts the
repetition artifacts long meetings tend to produce.

## Output

Two files, two jobs:

- `summaries/final_summary.md` — the public recap. No `owner: unknown`, no
  support labels, no raw timestamps.
- `evidence/summary_evidence.md` — every claim with its timestamp, support
  level, and the transcript line behind it. Open this when something in the
  recap looks wrong.

## References

- OpenAI Whisper: https://github.com/openai/whisper
- Whisper paper: https://cdn.openai.com/papers/whisper.pdf
- OpenAI Whisper announcement: https://openai.com/index/whisper/
- Ollama docs: https://docs.ollama.com/
- PyTorch install selector: https://pytorch.org/get-started/locally/
- Qwen model family: https://qwen.moe/

## Development

Run tests:

```bash
python -m unittest discover -s tests
python -m compileall -q src tests
```

Run a fixture without a video:

```bash
momo process tests/fixtures/sample_transcript.json --run-id sample
```

## Repository Hygiene

Large local artifacts are ignored:

- `.venv/`, `.conda/`, `env/`
- `videos/*`, `runs/*`
- media files (`*.mp4`, `*.wav`, `*.m4a`)

Only small examples and source live in the repo. Cloning shouldn't pull
private meeting data along.
