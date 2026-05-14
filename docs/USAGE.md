# Using MOMO

The interface speaks **Korean and English** — toggle in the sidebar.
The whole flow is three steps: drop a recording, tell the AI what to
focus on, hit start.

## Step 1 — Drop a recording

![home page](screenshots/01-home.png)

Upload an `.mp4 / .mkv / .mov / .m4a / .mp3 / .wav` (up to 4 GB), or
pick an existing file from `videos/` in the second tab. The sidebar
lists past runs so you can re-open them without re-running.

## Step 2 — Tell the AI what to focus on (this is the important part)

![summary guide section](screenshots/02-summary-guide.png)

The bordered "MOST IMPORTANT" panel is where you steer the summary.
All four fields are optional — the free-form instruction has the
biggest impact on quality:

| Field | What it does |
|---|---|
| 🗣️ **Free-form instruction** | One or two sentences in your own words. Goes directly into the LLM prompt and steers the recap. |
| 📝 **Meeting title** | Cosmetic label for the report. |
| ⭐ **Topics** | One per line. The AI looks for these and structures the summary around them. |
| ⚠️ **Confusion watch** | One per line. Things the AI must not mix up (e.g. "tentative vs. confirmed decisions"). |

Don't know what to write? Pick a meeting-type preset and it fills
sensible defaults you can edit:

![template applied](screenshots/03-template-applied.png)

Three presets are intentionally narrow because speaker diarization is
off — the pipeline doesn't promise per-speaker attribution:

- **📚 Research** — progress, blockers, decisions, next meeting
- **👥 1:1** — wins, struggles, things to try, where the manager can help
- **🤝 External meeting** — requirements, follow-up commitments, numbers/dates verbatim, TBDs kept separate

Click **🚀 Start summarizing**. The pipeline runs locally and the page
shows a step-by-step progress card while the work is happening:

![progress card](screenshots/06-progress.png)

Each stage flips from ⬜ to 🔵 (in progress, with a short hint) to ✅
(done) as the runner emits its events.

Wall-clock times on an RTX 4080 for a 45-minute meeting (Whisper
transcript re-used from a previous run; numbers are dominated by the
LLM passes):

| Summary mode | AI critique | Roughly |
|---|---|---|
| Fast (1-pass) | off | 2–3 min |
| Fast (1-pass) | on | 4–5 min |
| Thorough (slot extraction) — **default** | on — **default** | 10+ min |

The defaults trade speed for accuracy. Switch to Fast in **Advanced**
if you'd rather have a quick first pass.

## Step 3 — Read the result

![summary tab](screenshots/04-result-summary.png)

The result view has five tabs:

- **📄 Summary** — the user-facing recap (Markdown rendered inline)
- **▶ Watch with evidence** — interactive: video player + timestamp chips, see below
- **🔎 Evidence** — same recap but with timestamps, supporting quotes, and `strong / weak / inferred` labels per claim
- **📜 Transcript** — the full normalized Whisper transcript
- **📦 Files** — direct downloads for `.md` and `.json` artifacts

### Jumping to evidence in the recording

![playback chips](screenshots/05-playback-chips.png)

Each topic, decision, and worth-noting item carries the timestamp
range where it appeared in the meeting. Click any ▶ HH:MM:SS chip and
the video player re-anchors to that moment — useful for
double-checking the AI's call before pasting the recap into Slack.

## Language mode

Flip the sidebar **Display language** radio between 한국어 / English
and every label, template, and section heading translates. The
summary output language follows the UI by default; override in
**Advanced** if you want a different combination. Technical English
terms inside Korean recordings ("3D Gaussian", "SDS", "Whisper") are
preserved verbatim by the LLM regardless of which output language you
pick.

## Notes

- MOMO requires the configured local LLM. If Ollama is not running or
  the model isn't pulled, the run **fails fast** instead of silently
  producing a low-quality rule-based summary. Start it with `ollama
  serve` and `ollama pull qwen3.5:9b`.
- The GUI calls the same `process_transcript_source` pipeline as the
  CLI, so both paths produce identical artifacts under `runs/{run_id}/`.

---

<details>
<summary><strong>I'd rather use the CLI</strong></summary>

<br>

```bash
momo                   # auto-pick newest media in videos/
```

The CLI picks the newest media file in `videos/` automatically. Drop a
recording in:

```text
videos/
  Screen_Recording_20260429_172841_Zoom.mp4
```

Edit `topic_details.json` to steer the summary (same semantics as the
GUI form):

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

The CLI writes the same artifacts to `runs/{run_id}/` as the GUI.

</details>
