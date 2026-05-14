# Colab trial

Use the Colab notebook when someone wants to try MOMO without installing
Docker, Python, CUDA, ffmpeg, or Ollama on their own machine.

[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/jjunsss/MOMO/blob/main/notebooks/MOMO_Colab.ipynb)

## Who this is for

| User type | Recommended path | Why |
|---|---|---|
| First-time evaluator | **Colab trial** | Fastest way to upload one recording and inspect the summary quality. |
| Local/server user | **GUI install** | Better for repeated use, private files, long meetings, and stable model caches. |

Colab is intentionally a trial path. It uses a temporary Google-hosted
runtime, so model downloads and uploaded files disappear when the
runtime is reset. For confidential recordings, use the local/server GUI.

## Before you run it

1. Open the notebook from the badge above.
2. In Colab, choose **Runtime → Change runtime type → GPU**.
3. Run cells from top to bottom.
4. Upload one `.mp4`, `.mkv`, `.mov`, `.m4a`, `.mp3`, or `.wav`.
5. Edit the topic-details cell if you want meeting-specific focus terms.

The notebook fails early when `torch.cuda.is_available()` is false.
MOMO also configures Whisper with `MOMO_ASR_DEVICE=cuda`, so it does
not silently fall back to CPU transcription.

## Defaults

The Colab notebook uses quality-first defaults:

- Whisper `large-v3`
- Ollama `qwen3.5:9b`
- thorough LLM summary mode
- AI critique enabled
- Korean output by default

For a faster quick check, change these notebook variables before running
the pipeline cell:

```python
ASR_MODEL = "medium"
SUMMARY_MODE = "fast"
ENABLE_CRITIQUE = "false"
```

The output language is controlled by:

```python
OUTPUT_LANGUAGE = "ko"  # or "en"
```

## Outputs

The final cell displays
`/content/momo_workspace/runs/{run_id}/summaries/final_summary.md` and
downloads a zip with the most useful artifacts:

- final Markdown summary
- final JSON summary
- evidence report
- normalized transcript Markdown

These are the same artifacts produced by the local CLI and GUI.

## Troubleshooting

**GPU is OFF**

Use **Runtime → Change runtime type → GPU**, then run the notebook again.
Free Colab GPU availability varies by account and time.

**Ollama did not start**

Restart the Colab runtime and rerun from the top. If it fails again,
check `/tmp/momo_ollama.log` in the notebook.

**Model pull is slow**

The first run downloads several GB. Colab runtimes are temporary, so the
download may repeat after a reset. Local/server installs cache models
more reliably.

**Upload is slow or the meeting is very long**

Use the local/server GUI. Browser uploads and temporary Colab disks are
not ideal for large or repeated workloads.
