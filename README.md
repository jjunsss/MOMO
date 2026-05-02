# MOMO

**Meetings go in. Decisions come out.**

MOMO turns long Zoom recordings into crisp, evidence-backed Markdown recaps.
Drop a recording into `videos/`, add the few things you care about to
`topic_details.json`, and get a clean summary plus a separate evidence report.

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

## Example

Real MOMO output from a 52-second CC-BY Korean clip:
[`examples/demo_korean_speech/`](examples/demo_korean_speech/)

- [`final_summary.md`](examples/demo_korean_speech/final_summary.md) — the recap
- [`summary_evidence.md`](examples/demo_korean_speech/summary_evidence.md) — every claim with its transcript line and timestamp
- [`normalized_transcript.md`](examples/demo_korean_speech/normalized_transcript.md) — the full Whisper transcript
- [`SOURCE.md`](examples/demo_korean_speech/SOURCE.md) — source attribution + reproduce command

End-to-end on RTX 4080: ~70 seconds.

## Quick Start

### 1. Create a Conda environment

Conda handles `ffmpeg`, CUDA, and PyTorch with less friction than `venv`,
especially on GPU machines.

```bash
# Recent conda (≥ 26.x) requires accepting Terms of Service once.
# Skip these two lines if you've already accepted them.
conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/main
conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/r

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

### 4. Get the source and install MOMO

```bash
conda install -c conda-forge git -y    # skip if git is already on PATH
git clone https://github.com/jjunsss/MOMO.git
cd MOMO
python -m pip install openai-whisper PyYAML
python -m pip install -e .
```

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

### 4. What you get

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

To tune ASR decoding, LLM provider/model, chunk sizes, output sections, or
evidence toggles, edit `meeting_profile.md`.

## Output

- `summaries/final_summary.md` — **Final recap.** TL;DR, key topics, decisions,
  action items, next meeting, worth-noting. Prose and tables.
- `evidence/summary_evidence.md` — **Evidence file.** Each item from the recap
  with the transcript snippet it came from, the timestamp range, and a
  confidence label (`strong` = direct quote, `weak` = paraphrase,
  `inferred` = reasoned from context).

## References

- OpenAI Whisper: https://github.com/openai/whisper
- Whisper paper: https://cdn.openai.com/papers/whisper.pdf
- OpenAI Whisper announcement: https://openai.com/index/whisper/
- Ollama docs: https://docs.ollama.com/
- PyTorch install selector: https://pytorch.org/get-started/locally/
- Qwen model family: https://qwen.moe/

Thanks to the teams behind Whisper, Ollama, PyTorch, and Qwen — MOMO would
not exist without these projects.
