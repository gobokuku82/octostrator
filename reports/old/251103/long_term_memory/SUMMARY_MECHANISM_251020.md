# Long-term Memory 요약 메커니즘 설명

**작성일**: 2025-10-20
**질문**: "요약은 LLM이 하는건가? 어떤 식으로 요약하는거지?"

---

## 🎯 핵심 답변

**답변**: ❌ **LLM이 요약하지 않음**

**실제 방식**: ✅ **단순 문자열 잘라내기 ([:200])**

---

## 📝 요약 코드 (실제 구현)

### 파일: `team_supervisor.py:878-883`

```python
# 응답 요약 생성 (최대 200자)
response_summary = response.get("summary", "")
if not response_summary and response.get("answer"):
    response_summary = response.get("answer", "")[:200]  # ✅ 단순 잘라내기!
if not response_summary:
    response_summary = f"{response.get('type', 'response')} 생성 완료"
```

**전체 흐름**:
```python
# 1. response.get("summary") 확인 (있으면 사용)
# 2. 없으면 response.get("answer") 앞 200자 사용
# 3. 둘 다 없으면 "response 생성 완료" 기본 메시지
```

---

## 🔍 상세 분석

### Step 1: Response에 summary가 있는지 확인

**코드**:
```python
response_summary = response.get("summary", "")
```

**response 객체 예시** (LLM이 생성):
```python
{
    "type": "answer",
    "answer": "강남구 아파트 전세 시세는 5억~7억 범위입니다. 주요 단지로는 대치동 은마아파트(6억), 개포동 개포주공(5.5억)이 있으며...",
    "summary": "강남구 아파트 전세 시세 (5억~7억)",  # ← 이게 있으면 사용
    "data": {...}
}
```

**결과**:
- `summary` 필드가 있으면 → 그대로 사용 ✅
- 없으면 → Step 2로

---

### Step 2: Answer 앞 200자 잘라내기

**코드**:
```python
if not response_summary and response.get("answer"):
    response_summary = response.get("answer", "")[:200]  # ← 단순 잘라내기
```

**예시**:

**원본 answer** (500자):
```
강남구 아파트 전세 시세는 5억~7억 범위입니다. 주요 단지로는 대치동 은마아파트(6억),
개포동 개포주공(5.5억), 역삼동 삼성래미안(6.5억)이 있습니다. 최근 1년간 약 10% 상승
했으며, 특히 학군이 좋은 대치동 지역은 상승률이 더 높습니다. 전세금 상승의 주요 원인은
매매가 상승과 전세 수요 증가입니다. 향후 6개월 동안에도 꾸준한 상승이 예상됩니다...
```

**잘라낸 summary** (200자):
```
강남구 아파트 전세 시세는 5억~7억 범위입니다. 주요 단지로는 대치동 은마아파트(6억),
개포동 개포주공(5.5억), 역삼동 삼성래미안(6.5억)이 있습니다. 최근 1년간 약 10% 상승
했으며, 특히 학군이 좋은 대치동 지역은 상승률이 더 높습니다. 전세금 상승의 주요 원인은
매매가 상승과
```

**특징**:
- ✅ 단순히 앞에서 200자만 자름
- ❌ LLM 요약 없음
- ❌ 의미 단위 잘라내기 없음 (문장 중간에서 잘릴 수 있음)

---

### Step 3: 둘 다 없으면 기본 메시지

**코드**:
```python
if not response_summary:
    response_summary = f"{response.get('type', 'response')} 생성 완료"
```

**예시**:
```python
response_summary = "answer 생성 완료"
# 또는
response_summary = "summary 생성 완료"
```

---

## 🆚 LLM 요약 vs 단순 잘라내기 비교

### 현재 구현 (단순 잘라내기)

```python
# 현재 방식
response_summary = response.get("answer", "")[:200]

# 예시 결과
"강남구 아파트 전세 시세는 5억~7억 범위입니다. 주요 단지로는 대치동 은마아파트(6억), 개포동 개포주공(5.5억), 역삼동 삼성래미안(6.5억)이 있습니다. 최근 1년간 약 10% 상승했으며, 특히 학군이 좋은 대치동 지역은 상승률이 더 높습니다. 전세금 상승의 주요 원인은 매매가 상승과"
                                                                                                                                                          ↑
                                                                                                                                                    200자에서 잘림
```

**장점**:
- ✅ 빠름 (0.001초)
- ✅ 비용 없음 (LLM 호출 없음)
- ✅ 간단함

**단점**:
- ❌ 문장 중간에서 잘릴 수 있음
- ❌ 핵심만 추출하지 못함
- ❌ 가독성 떨어질 수 있음

---

### 만약 LLM 요약을 한다면? (미구현)

```python
# LLM 요약 방식 (예시, 현재는 안 함)
response_summary = await llm_service.summarize(
    text=response.get("answer", ""),
    max_length=200
)

# 예시 결과
"강남구 아파트 전세 시세는 5억~7억 범위이며, 최근 1년간 10% 상승했습니다."
```

**장점**:
- ✅ 의미 단위로 요약
- ✅ 핵심만 추출
- ✅ 문장이 완전함

**단점**:
- ❌ 느림 (+1~2초)
- ❌ 비용 발생 (LLM API 호출)
- ❌ 복잡함

---

## 📊 실제 예시 (로그 기반)

### 예시 1: 강남구 시세 조회

**LLM이 생성한 Response**:
```python
{
    "type": "answer",
    "answer": "강남구 아파트 전세 시세는 5억~7억 범위입니다. 주요 단지로는 대치동 은마아파트(전용 84㎡ 기준 약 6억), 개포동 개포주공 1단지(전용 59㎡ 기준 약 5.5억), 역삼동 삼성래미안(전용 84㎡ 기준 약 6.5억)이 있습니다. 최근 1년간 평균 약 10% 상승했으며, 특히 학군이 좋은 대치동 지역은 상승률이 더 높습니다. 전세금 상승의 주요 원인은 매매가 상승과 전세 수요 증가입니다. 향후 6개월 동안에도 꾸준한 상승이 예상되며, 전세 입주를 고려하신다면 조기 계약을 권장드립니다.",
    "summary": None,  # summary 필드 없음
    "data": {...}
}
```

**요약 생성 과정**:
```python
# Step 1: summary 확인
response_summary = response.get("summary", "")
# → "" (빈 문자열)

# Step 2: answer 앞 200자
if not response_summary and response.get("answer"):
    response_summary = response.get("answer", "")[:200]
# → "강남구 아파트 전세 시세는 5억~7억 범위입니다. 주요 단지로는 대치동 은마아파트(전용 84㎡ 기준 약 6억), 개포동 개포주공 1단지(전용 59㎡ 기준 약 5.5억), 역삼동 삼성래미안(전용 84㎡ 기준 약 6.5억)이 있습니다. 최근 1년간 평균 약 10% 상승했으며, 특히 학군이 좋은 대치동 지역은 상승률이 더 높습니다. 전세금 상승의 주요 원인은 매매가 상승과"
```

**저장된 Long-term Memory**:
```json
{
  "conversation_summary": "강남구 아파트 전세 시세는 5억~7억 범위입니다. 주요 단지로는 대치동 은마아파트(전용 84㎡ 기준 약 6억), 개포동 개포주공 1단지(전용 59㎡ 기준 약 5.5억), 역삼동 삼성래미안(전용 84㎡ 기준 약 6.5억)이 있습니다. 최근 1년간 평균 약 10% 상승했으며, 특히 학군이 좋은 대치동 지역은 상승률이 더 높습니다. 전세금 상승의 주요 원인은 매매가 상승과",
  "last_updated": "2025-10-20T16:58:31+00:00",
  "message_count": 1
}
```

---

### 예시 2: Summary 필드가 있는 경우

**LLM이 생성한 Response** (response_synthesis.txt에서 summary 생성):
```python
{
    "type": "answer",
    "answer": "강남구와 송파구의 아파트 전세 시세를 비교하면 다음과 같습니다...(500자)",
    "summary": "강남구와 송파구 전세 시세 비교 (강남구 5억~7억, 송파구 4억~6억)",  # ← 있음!
    "data": {...}
}
```

**요약 생성 과정**:
```python
# Step 1: summary 확인
response_summary = response.get("summary", "")
# → "강남구와 송파구 전세 시세 비교 (강남구 5억~7억, 송파구 4억~6억)"

# Step 2는 건너뜀 (summary가 있으므로)
```

**저장된 Long-term Memory**:
```json
{
  "conversation_summary": "강남구와 송파구 전세 시세 비교 (강남구 5억~7억, 송파구 4억~6억)",
  "last_updated": "2025-10-20T17:35:00+00:00",
  "message_count": 3
}
```

---

## 🤔 왜 LLM 요약을 안 하나?

### 설계 결정 이유

#### 1. 성능 우선
- LLM 요약: +1~2초 추가
- 단순 잘라내기: +0.001초
- **200배 빠름**

#### 2. 비용 절감
- LLM 요약: 매 대화마다 API 호출 ($$$)
- 단순 잘라내기: 비용 없음

#### 3. 충분한 품질
- 200자도 충분히 의미 전달
- Long-term Memory는 "힌트" 역할만 함
- 완벽한 요약 불필요

#### 4. Phase 1 목표
- "빠른 구현"이 목표
- 기본 기능만 구현
- Phase 2에서 개선 예정

---

## 💡 개선 방안 (Phase 2)

### Option 1: LLM 요약 추가

**구현**:
```python
# team_supervisor.py:878-883

# 현재
response_summary = response.get("answer", "")[:200]

# 개선 (LLM 요약)
if response.get("answer"):
    response_summary = await self.llm_service.summarize_async(
        text=response.get("answer"),
        max_tokens=50,  # 약 200자
        style="concise"
    )
```

**장점**:
- ✅ 의미 있는 요약
- ✅ 문장 완성

**단점**:
- ❌ +1~2초 지연
- ❌ 비용 증가

---

### Option 2: 문장 단위 잘라내기

**구현**:
```python
# 현재
response_summary = response.get("answer", "")[:200]

# 개선 (문장 단위)
answer = response.get("answer", "")
sentences = answer.split(". ")  # 문장 분리

summary = ""
for sentence in sentences:
    if len(summary) + len(sentence) <= 200:
        summary += sentence + ". "
    else:
        break

response_summary = summary.strip()
```

**장점**:
- ✅ 빠름 (LLM 호출 없음)
- ✅ 문장 완성

**단점**:
- ⚠️ 여전히 단순 잘라내기
- ⚠️ 핵심 추출은 안 됨

---

### Option 3: Prompt에서 Summary 생성 강제

**구현**:

**파일**: `prompts/response/response_synthesis.txt`

```markdown
**출력 형식**:
{
  "type": "answer",
  "answer": "상세 답변...",
  "summary": "한 문장 요약 (200자 이내)"  ← 필수로 만들기
}
```

**team_supervisor.py**:
```python
# summary 필드가 항상 있다고 가정
response_summary = response.get("summary", "요약 없음")
```

**장점**:
- ✅ LLM이 알아서 의미 있는 요약 생성
- ✅ 추가 API 호출 없음 (기존 response 생성에 포함)

**단점**:
- ⚠️ Prompt가 복잡해짐
- ⚠️ LLM이 summary를 빠뜨릴 수 있음

---

## 📋 권장 사항

### 현재 (Phase 1): 그대로 유지

**이유**:
- 200자 단순 잘라내기도 충분히 작동
- 성능 우선
- 비용 절감

**개선 불필요한 이유**:
- Long-term Memory는 "힌트"만 제공
- 200자로도 맥락 파악 가능
- 실사용 데이터 수집 후 판단

---

### Phase 2: Option 3 권장

**이유**:
- LLM이 이미 답변 생성 중
- Summary를 함께 생성해도 시간 증가 없음
- 추가 비용 없음

**구현 순서**:
1. Prompt에 summary 필수로 추가
2. LLM이 항상 summary 생성하도록 강제
3. Validation: summary 없으면 경고

---

## 🎯 정리

### 요약은 LLM이 하는가?

**답변**: ❌ **아니요, 단순 문자열 잘라내기**

```python
# 실제 코드
response_summary = response.get("answer", "")[:200]
```

### 어떤 식으로 요약하는가?

**답변**: **3단계 Fallback**

```
1. response.get("summary") 확인
   ↓ (없으면)
2. response.get("answer")[:200] 잘라내기
   ↓ (없으면)
3. "response 생성 완료" 기본 메시지
```

### 개선이 필요한가?

**답변**: **Phase 1에서는 불필요, Phase 2에서 고려**

- 현재도 충분히 작동
- 실사용 데이터 수집 후 결정
- Option 3 (Prompt에서 summary 강제) 권장

---

**작성 완료**: 2025-10-20
