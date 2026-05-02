당신은 회의 transcript의 한 chunk만 보고, **하나의 슬롯에 해당하는 사실만** 추출합니다. 본 chunk는 회의 전체의 일부입니다.

# 슬롯
- ID: `{{ slot_id }}`
- 라벨: {{ slot_label }}
- 종류: {{ slot_kind }}
- 설명: {{ slot_description }}
- 별칭: {{ slot_aliases }}

# 규칙
1. chunk 안에서 직접 근거가 있는 것만 추출합니다. 없으면 `{"items": []}`.
2. evidence_timestamps는 chunk의 `[segment_id | HH:MM:SS]` 시작 시각만 사용합니다.
3. 추측 금지. 모르면 `"unknown"`.
4. 날짜 vs 시간 구분: "13일"=date, "13시"=time. (혼동 금지)
5. 최대 {{ max_items }}개.

# Chunk 메타
- 회의 ID: {{ meeting_id }}
- Chunk ID: {{ chunk_id }}
- Chunk 시간 범위: {{ chunk_time_range }}

# Chunk 발언
{{ chunk_text }}

# 응답 (JSON 객체 한 개만)
```json
{"items": [{"summary": "...", "importance": 1-5, "owner": "unknown|...", "deadline": "unknown|...", "date": "unknown|...", "time": "unknown|...", "evidence_timestamps": ["HH:MM:SS"], "evidence_quote": "..."}]}
```
