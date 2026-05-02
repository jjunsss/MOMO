당신은 chunk별로 추출된 슬롯 항목을 **회의 전체 단위로 합치는** 작업을 합니다.

# 슬롯
- ID: `{{ slot_id }}`
- 라벨: {{ slot_label }}
- 설명: {{ slot_description }}

# 작업
1. 같은 의미를 가진 항목을 하나로 합칩니다. evidence_timestamps는 합치고 정렬합니다.
2. 정말 다른 항목은 분리해서 보존합니다.
3. 추측해서 새 사실을 만들지 않습니다. 입력에 없는 owner/deadline/date/time은 모두 `"unknown"`.
4. importance를 다시 매기고(1-5) 내림차순으로 정렬합니다.
5. 최대 {{ max_items }}개로 제한합니다.

# 입력 (각 줄 = chunk 단위 추출 결과 JSON)
{{ chunk_items_jsonl }}

# 응답
```json
{"items": [{"summary": "...", "importance": 1-5, "owner": "...", "deadline": "...", "date": "...", "time": "...", "evidence_timestamps": ["HH:MM:SS", ...], "evidence_quote": "..."}]}
```
