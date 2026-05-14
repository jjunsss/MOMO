# Meeting AI Profile

이 파일은 고급 기본값입니다. 일반 사용자는 보통 수정하지 않습니다.
회의마다 바뀌는 입력은 `videos/` 폴더의 비디오와 `topic_details.json`만 수정하세요.

```bash
.venv/bin/momo auto
```

기본 실행은 `meeting_profile.md` 기본값 위에 `topic_details.json`을 덮어씁니다.
명시적으로 다른 토픽 파일을 쓰려면 `--topic-details path/to/topic_details.json` 를 추가합니다.

규칙:
- `## 헤더`로 구분된 섹션만 인식됩니다. 헤더 이름은 바꾸지 마세요.
- `- [x]`는 켜짐, `- [ ]`는 꺼짐을 뜻합니다.
- 검색용 단어 목록은 쉼표로 구분합니다. 줄을 여러 개 써도 됩니다.
- 한 줄짜리 설명/주석은 자유롭게 추가해도 무시됩니다.

---

## Settings

> 자동화 기본값입니다. 빈 값은 기본 동작을 사용합니다.

title: Auto Meeting Summary
videos_dir: videos
run_id: auto
output_language: ko

# ASR 모델 선택: asr_preset (fast | balanced | best) 만 지정하거나
# asr_model 에 whisper 모델명을 직접 적습니다. asr_model 이 우선합니다.
# fast=small, balanced=medium, best=large-v3
# 품질 우선 기본값은 16GB RTX 4080 기준 large-v3 + 무음 환각 억제 옵션입니다.
asr_preset: best
asr_model: large-v3
asr_language: ko
asr_device: cuda
asr_temperature: 0.0
asr_condition_on_previous_text: false
asr_no_speech_threshold: 0.6
asr_logprob_threshold: -1.0
asr_compression_ratio_threshold: 2.4

chunk_target_minutes: 6
chunk_max_minutes: 10
chunk_overlap_seconds: 30

# LLM 합성기 설정 (요약 품질을 좌우합니다)
# llm_provider: ollama | openai_compatible
#   - ollama = 로컬 Ollama 서버 (예: ollama serve + ollama pull qwen2.5:14b)
#   - openai_compatible = OpenAI/OpenRouter/vLLM 등 OpenAI 호환 엔드포인트
# llm_base_url: ollama 는 http://localhost:11434, openai 는 https://api.openai.com/v1
# llm_api_key_env: openai_compatible 일 때 키를 읽어올 환경변수 이름 (기본 OPENAI_API_KEY)
llm_provider: ollama
llm_model: qwen3.5:9b
llm_base_url: http://localhost:11434
llm_temperature: 0.0
llm_num_ctx: 65536
llm_request_timeout_seconds: 1800
llm_api_key_env: OPENAI_API_KEY

# 출력 한도 (LLM 합성기에서만 적용됩니다)
llm_summary_mode: thorough         # fast=1회 호출, thorough=슬롯별 추출+2-pass 합성
worth_noting_max: 8
key_topics_max: 8
max_items_per_slot: 8
single_pass_token_limit: 60000   # transcript가 이보다 작으면 슬롯별 single-pass, 크면 hierarchical
direct_summary_max_tokens: 8192
enable_critique: true             # true면 요약 초안을 한 번 더 검토

---

## Output Sections

> 최종 Markdown 에 포함할 섹션과 표시 방식.
> 형식: `id | 제목 | 스타일`
> 근거/timestamp/support는 최종 Markdown에 표시하지 않고 `runs/{run_id}/evidence/`에 따로 저장됩니다.

- [x] tldr | TL;DR | paragraph
- [x] executive_summary | 핵심 요약 | paragraph
- [x] key_topics | 핵심 논의 | table
- [x] decisions | 결정사항 | table
- [x] action_items | Action Items | checklist
- [x] next_meeting | 다음 미팅 / Follow-up | table
- [x] worth_noting | Worth Noting | bullets
- [ ] open_questions | Open Questions | bullets
- [ ] required_search_report | 사용자 필수 탐색 항목 결과 | table
- [ ] appendix | Appendix | metadata

---

## Rendering

> 부수 산출물 토글. 최종 Markdown은 공유용으로 깔끔하게 유지합니다.

- [x] include_skipped_chunk_stats
- [x] write_evidence_report
- [x] write_transcript_markdown
- [x] write_chunk_analysis_jsonl

---

## Required Search Items

> 회의 전체에서 반드시 찾아야 할 항목. 못 찾으면 `not_found` 로 표시됩니다.
> 형식: `id | 라벨 | 별칭들 | 설명`

- [x] next_meeting | 다음 미팅 | 다음 미팅, 다음 회의, 다음 주, next meeting, follow-up meeting | 다음 회의 일정, agenda, 준비할 일을 찾는다.
- [x] action_items | 해야 할 일 | 해야 할 일, 액션 아이템, TODO, action item, next step, 확인해 주세요, 정리해 주세요, 준비해 주세요 | 회의 후 해야 할 일을 찾는다.
- [x] worth_noting | Worth Noting | 중요, 참고, 리스크, 우려, 기억, worth noting | 결정이나 액션은 아니지만 나중에 중요한 맥락을 찾는다.

---

## Custom Topics

> 고급 호환용 섹션입니다. 일반 사용자는 `topic_details.json`의 `topics`를 수정하세요.
> 형식: `id | 라벨 | 별칭들 | 설명`

---

## Verification Terms

> 반드시 구분/확인해야 하는 용어와 주제입니다.
> 형식: `id | 라벨 | 별칭들 | 확인 기준`

- [x] date_time | 날짜와 시간 구분 | 13일, 13시, 13:00, 같은 시간, 다음 주 | 날짜/시간을 혼동하지 말고 명시 근거가 없으면 unknown으로 둔다.

---

## Decision Keywords

> 청크에서 "결정"으로 인식할 단어. 비워두면 기본값을 사용합니다.

- 결정, 하기로, 가기로, 확정, 채택, decided, decision

## Uncertain Decision Markers

> "결정해야 한다"처럼 미확정 결정으로 분류해 Open Questions 로 옮길 표현.

- 결정해야, 결정을 좀 내봐야, 결정해야 될, 정해야, 확인 필요, 논의 필요

## Action Keywords

> "해야 할 일"로 인식할 표현. 도메인 별 표현을 자유롭게 추가하세요.

- 해야 할 일, 액션 아이템, 해주세요, 해 주세요
- 확인해 주세요, 정리해 주세요, 준비해 주세요, 공유해 주세요, 작성해 주세요, 보내주세요
- todo, action item, next step

## Next Meeting Keywords

> 다음 미팅 언급으로 잡을 표현.

- 다음 미팅, 다음 회의, 다음 주, follow-up, next meeting

## Worth Noting Keywords

> 결정/액션은 아니지만 보존할 맥락을 잡는 표현.

- 중요, 참고, 리스크, 우려, 기억, 주의, worth noting

## Question Keywords

> 열린 질문으로 분류할 표현. `?` 도 그대로 쓰면 됩니다.

- ?, 질문, 확인 필요, 논의 필요, open question
