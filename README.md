# MOMO

MOMO is a local-first meeting recap tool for long Zoom/video recordings.

Drop a recording into `videos/`, write the few things you care about in
`topic_details.json`, and MOMO produces a clean Markdown summary plus a separate
evidence report you can inspect when something looks important.

## Why MOMO?

I tried to keep this close to the way I actually review research meetings:

- the shared summary should be clean, not full of timestamps and audit metadata
- the evidence should still exist, just in a separate place
- the user should not edit prompts or complicated YAML before every meeting
- Korean long-form meetings need better date/time and repetition safeguards than
  a raw transcript-to-summary pass
- local video and transcript data should stay local unless the user explicitly
  chooses a cloud LLM endpoint

Existing workflow templates are useful, especially n8n-style video to Whisper to
LLM automation, but they were not quite enough for this use case. The missing
parts were evidence separation, local GPU-aware defaults, restartable run
artifacts, user-friendly topic steering, and a summary flow that avoids simply
sorting chunks chronologically.

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
    final_summary.md       # clean human-facing recap
    final_summary.json     # public structured output
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

MOMO is easiest to run in a Conda environment, especially on GPU machines.

```bash
conda create -n momo python=3.10 -y
conda activate momo
python -m pip install --upgrade pip setuptools wheel
```

`venv` also works, but Conda is the recommended path because it handles native
packages such as `ffmpeg`, CUDA, and PyTorch more comfortably.

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

For CPU-only machines, use the command recommended by the official PyTorch
installer page.

### 4. Install MOMO

```bash
python -m pip install openai-whisper PyYAML
python -m pip install -e .
```

### 5. Optional: enable local LLM summaries

Install Ollama and pull a model that fits your GPU.

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama serve
ollama pull qwen2.5:14b
```

Then set the model in `meeting_profile.md`:

```text
llm_provider: ollama
llm_model: qwen2.5:14b
llm_base_url: http://localhost:11434
```

If you do not run an LLM provider, MOMO falls back to deterministic extraction.

## How To Use

### 1. Put a recording in `videos/`

```text
videos/
  Screen_Recording_20260429_172841_Zoom.mp4
```

The newest media file is selected automatically.

### 2. Edit `topic_details.json`

Keep it simple. Strings are enough.

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

`meeting-ai` is kept as a compatibility alias:

```bash
meeting-ai
```

## Configuration

Most users only edit `topic_details.json`.

Advanced defaults live in `meeting_profile.md`:

- ASR model and decoding options
- LLM provider/model
- chunk sizes
- output sections
- evidence report toggles

The current local-first default is Whisper `large-v3` for ASR. The profile also
turns off previous-text conditioning and keeps silence thresholds explicit to
reduce long-meeting repetition artifacts.

## Output Philosophy

MOMO writes two kinds of output:

- `summaries/final_summary.md`: clean enough to share
- `evidence/summary_evidence.md`: detailed enough to verify

That means final summaries avoid noisy text such as `owner: unknown`, support
labels, raw timestamps, or transcript snippets. Those details are still
preserved in `evidence/`.

## Tech Stack

- Python package with a `src/` layout
- OpenAI Whisper for local ASR
- PyTorch/CUDA for GPU transcription when available
- Ollama or OpenAI-compatible endpoints for optional LLM synthesis
- deterministic chunk salience analysis before the LLM pass
- JSON artifacts for restartability and debugging
- Markdown renderers for clean public output and separate evidence output

## Design Notes

The pipeline is intentionally staged:

```text
media -> audio -> raw transcript -> normalized transcript -> chunks
-> deterministic chunk analysis -> required search report
-> LLM or deterministic synthesis -> validation -> Markdown
```

The intermediate files are not clutter. They make long runs restartable, easier
to debug, and safer to review when the summary looks suspicious.

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

- `.venv/`
- `.conda/`
- `env/`
- `videos/*`
- `runs/*`
- media files such as `*.mp4`, `*.wav`, `*.m4a`

Keep only small examples and source files in GitHub. MOMO should be easy to
clone, install, and try without dragging private meeting data along for the
ride.
