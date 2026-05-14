# References

## Research Context And Implementation Mapping

These references are not all one-to-one implementations. MOMO uses some
ideas directly, adapts others, and keeps a few as background context.
Pointers to where each idea lives in the codebase are in parentheses.

- **Chain-of-Verification (CoVe)-style verification** — Dhuliawala et
  al., 2023. MOMO uses a simplified claim-checking pass: it drafts a
  summary, collects important claims with evidence windows, asks the LLM
  for keep/downgrade/fix/remove verdicts, then renders the corrected
  result. This is inspired by CoVe's draft-then-verify structure, but it
  is not the full factored CoVe pipeline with independently answered
  verification questions.
  ([`prompts/critique.md`](../src/meeting_ai/prompts/critique.md),
  [`nodes/llm_critique.py`](../src/meeting_ai/nodes/llm_critique.py),
  paper: https://arxiv.org/abs/2309.11495)

- **Chain-of-Thought / reasoning-prompting inspiration** — Wei et al.,
  2022. The slot extractor enables the model's thinking mode while
  locating evidence in long transcripts, then constrains the response to
  JSON. This is a practical reasoning-prompting use, not a reproduction
  of the paper's few-shot CoT experiments.
  ([`nodes/llm_extract.py`](../src/meeting_ai/nodes/llm_extract.py),
  paper: https://arxiv.org/abs/2201.11903)

- **Recursive decomposition for long-document summarization** — Wu et
  al. (OpenAI), 2021. MOMO borrows the decomposition idea: if a
  transcript is too large for a single per-slot pass, it extracts facts
  per chunk, merges per slot, then synthesizes prose → JSON. It does not
  use the paper's human-feedback training setup.
  ([`nodes/llm_extract.py`](../src/meeting_ai/nodes/llm_extract.py),
  [`nodes/llm_synthesize.py`](../src/meeting_ai/nodes/llm_synthesize.py),
  paper: https://arxiv.org/abs/2109.10862)

- **Lexical extractive salience pre-filter** — TextRank is relevant
  background for extractive keyword/sentence ranking (Mihalcea & Tarau,
  2004), but MOMO does **not** implement TextRank's graph-based ranking.
  The current filter is a simpler deterministic lexical gate: each
  6–10 min chunk is marked *kept* or *skipped* using configured keyword
  matches, required-item hits, and evidence density before synthesis.
  ([`nodes/analyze_chunk.py`](../src/meeting_ai/nodes/analyze_chunk.py),
  paper: https://aclanthology.org/W04-3252/)

- **Meeting summarization benchmark context** — QMSum (Zhong et al.,
  2021) is background context, not an implementation dependency. It
  motivates MOMO's user-directed summarization shape: user topics and
  free-form instructions act like queries that steer what spans of a
  long meeting should be located and summarized.
  (paper: https://arxiv.org/abs/2104.05938)

## Tools and models

- OpenAI Whisper runtime: https://github.com/openai/whisper
- Whisper paper, **Robust Speech Recognition via Large-Scale Weak
  Supervision**: https://cdn.openai.com/papers/whisper.pdf
- OpenAI Whisper announcement: https://openai.com/index/whisper/
- Ollama docs: https://docs.ollama.com/
- PyTorch install selector: https://pytorch.org/get-started/locally/
- Qwen model family: https://qwen.moe/

Thanks to the teams behind Whisper, Ollama, PyTorch, and Qwen — MOMO
would not exist without these projects.
