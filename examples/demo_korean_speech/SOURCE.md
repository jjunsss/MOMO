# Demo source

- **Title**: 발표잘하는 방법! 발표잘하는 방법 3가지
- **Uploader**: 김지혜TV리스피치
- **URL**: https://youtu.be/pYnVm6QM8fo
- **Duration**: 52 seconds
- **License**: Creative Commons Attribution (reuse allowed)
- **Upload date**: 2023-05-26

The output files in this folder are MOMO's actual end-to-end run on the clip
above, on a single RTX 4080 in ~70 seconds (Whisper `large-v3` + Qwen 3.5 9B
+ render).

## Reproduce

```bash
yt-dlp -f 'best[height<=480]/best' -o 'videos/demo.mp4' https://youtu.be/pYnVm6QM8fo
cp examples/demo_korean_speech/topic_details.json .
momo
```

The third line is the part that matters for matching this folder's output.
The repo's default `topic_details.json` is tuned for a different domain, so
without that copy, your recap will look correct but it will be focused on
different topics.

## How `topic_details.json` shapes the recap

`topic_details.json` is the small file an end user is expected to edit per
meeting. Everything else (model picks, chunking, prompts) lives in
`meeting_profile.md` as advanced defaults. The pipeline reads `topic_details`
and overlays its fields onto the runtime profile (see
`src/meeting_ai/config/topic_details.py:apply_topic_details`).

| Field in `topic_details.json` | Where it lands | Effect on the recap |
|---|---|---|
| `title` | `meeting_profile.default_title` | Recap title fallback when the source filename has no usable title. |
| `topics` *(or `custom_topics` / `focus`)* | `profile.custom_topics` | Each entry becomes a **slot** the LLM is asked to search for. The recap's `key_topics` table and prose are seeded by these. |
| `must_check` *(or `verification_terms` / `verify`)* | `profile.verification_terms` | Items the synthesis and critique prompts treat as "do not be loose here." Used to push hard claims into `open_questions` when ambiguous, and to enforce date/time and similar disambiguations. |
| `required_items` *(or `required_search_items`)* | `profile.required_search_items` | Overrides the default required slots (`next_meeting`, `action_items`, `worth_noting`). Anything you list here must appear in the recap with `found` / `not_found` status. |
| `output_language` | `meeting_profile.output_language` | Forces prose language (default `ko`). |

### Walk-through with the values in this folder's `topic_details.json`

```json
{
  "title": "Korean Speaking Demo",
  "topics": ["presentation skills", "speech tips", "communication"],
  "must_check": [
    "actionable tips listed by the speaker",
    "any concrete numbers or examples"
  ]
}
```

What this caused:

1. **`topics`** became three custom slots (`presentation skills`, `speech tips`,
   `communication`). The LLM extractor scanned the transcript for evidence
   matching each slot. The recap's `key_topics` row "발표 불안 해소 및 핵심 전략"
   is the merged answer.
2. **`must_check`** became hints for the synthesis pass. That is why the recap
   surfaces concrete tips ("오프닝/크로징 준비", "순서 단순화", "마치겠습니다 멘트")
   instead of vague paraphrase, and why nothing about non-existent dates or
   numbers was invented.
3. **`title`** was used as a fallback — but here Whisper produced a usable
   filename, so the recap title shows the source filename instead.

### What if you skip `topic_details.json`?

The pipeline still runs. It uses the defaults from `meeting_profile.md`:

- `required_search_items`: `next_meeting`, `action_items`, `worth_noting`.
- `custom_topics`: empty, so the LLM has no domain hints — the recap is more
  generic.
- `verification_terms`: only the built-in date/time disambiguation rule.

In other words: skipping `topic_details.json` gives a competent generic recap;
adding it tells MOMO what *you* care about so the recap is shaped around it.
