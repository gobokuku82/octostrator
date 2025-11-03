# 사용자 요구사항 확정 및 상세 답변

**작성일**: 2025-10-22
**목적**: 사용자 질문에 대한 명확한 답변 및 구현 방향 확정

---

## ✅ Q1. Checkpointer 정상 작동 확인됨

**상태**: 확인 완료 ✅

---

## 🔍 Q2. entities 추출 어떻게 확인할까?

### 확인 방법 1: 로그 확인 (가장 간단)

```bash
# backend 실행 중 로그 확인
# planning_node에서 Intent 분석 결과 로깅됨

# 예상 로그:
[TeamSupervisor] Intent analysis result: {
  "intent_type": "market_inquiry",
  "confidence": 0.95,
  "keywords": ["강남구", "아파트", "시세"],
  "entities": {
    "region": "강남구",
    "property_type": "아파트"
  }
}
```

**확인 순서**:
1. 프론트엔드에서 질문: "강남구 아파트 시세"
2. 백엔드 로그 확인 (console 또는 app.log)
3. `entities` 필드가 있는지 확인

---

### 확인 방법 2: Checkpointer에서 직접 확인

```sql
-- PostgreSQL 접속
psql -U postgres -d real_estate

-- 최근 checkpoint 확인
SELECT
    thread_id,
    checkpoint->'channel_values'->'planning_state'->'analyzed_intent'->>'intent_type' as intent,
    checkpoint->'channel_values'->'planning_state'->'analyzed_intent'->'entities' as entities
FROM checkpoints
ORDER BY (checkpoint->'channel_values'->>'start_time')::timestamp DESC
LIMIT 3;
```

**예상 결과**:
```
thread_id       | intent         | entities
----------------|----------------|--------------------------------
session-abc123  | market_inquiry | {"region": "강남구", "property_type": "아파트"}
```

---

### 확인 방법 3: 간단한 테스트 스크립트

```python
# test_entity_extraction.py
import asyncio
from app.service_agent.cognitive_agents.planning_agent import PlanningAgent

async def test():
    agent = PlanningAgent()
    result = await agent.analyze_intent("강남구 아파트 시세")

    print("Intent:", result.intent_type)
    print("Entities:", result.entities)

    # 확인
    assert result.entities.get("region") == "강남구"
    assert result.entities.get("property_type") == "아파트"
    print("✅ Entities extraction working!")

asyncio.run(test())
```

---

### 만약 entities가 없거나 비어있다면?

**현재 프롬프트 확인 필요**:
```
backend/app/service_agent/llm_manager/prompts/cognitive/intent_analysis.txt
```

**Line 169-177 확인**:
```
"entities": {
    "region": "강남구",
    "property_type": "아파트",
    ...
}
```

**만약 프롬프트에 entities 설명이 부족하면**:
→ 10줄 추가 필요 (이전에 작성했던 내용)

---

## ❌ Q8. 에러 시 fallback 구현 여부 - **아직 구현 안 됨!**

### 현재 상태

**team_supervisor.py**에는 **fallback 로직이 없습니다!**

이번 구현에서 추가해야 함:

```python
# 🆕 추가할 코드
try:
    # 이전 State 로드
    prev_state = await self.checkpointer.aget(config)

    # 비교 로직
    if can_skip:
        state["search_skipped"] = True

except Exception as e:
    # 🔥 Fallback (에러 시 안전하게 SearchTeam 실행)
    logger.error(f"Skip check error: {e}")
    state["search_skipped"] = False  # ← 중요!
```

**중요**: try-catch 필수!

---

## ❓ Q3. 신선도 기준 질문 - 명확히 설명

### 질문의 의도

**"Intent별 신선도 기준"**이란:
> "이전 검색 데이터가 얼마나 오래되면 다시 검색할 것인가?"

### 구체적 예시

#### 시나리오 1: 시세 조회 (MARKET_INQUIRY)

```
대화1 (월요일): "강남구 아파트 시세" → SearchTeam 실행, 결과 저장
대화2 (화요일): "강남구 아파트 시세" → 1일 전 데이터, 재사용? 새로 검색?
대화3 (다음주 월요일): "강남구 아파트 시세" → 7일 전 데이터, 재사용? 새로 검색?
```

**질문**: 며칠 전 데이터까지 재사용할 것인가?

**제안**:
- **7일**: 일주일 전 시세까지 OK (약간 관대)
- **3일**: 3일 전 시세까지 OK (보수적)
- **1일**: 어제 시세까지만 OK (매우 보수적)

**사용자 선택**: ___일?

---

#### 시나리오 2: 법률 정보 (LEGAL_CONSULT)

```
대화1 (1월): "전세금 인상 한도는?" → SearchTeam 실행
대화2 (2월): "전세금 인상 한도는?" → 30일 전 데이터, 재사용? 새로 검색?
```

법률은 자주 바뀌지 않으므로:
- **30일**: 한 달 전 법률 정보도 OK (권장)
- **90일**: 3개월 전 법률 정보도 OK (관대)

**사용자 선택**: ___일?

---

#### 시나리오 3: 대출 정보 (LOAN_CONSULT)

```
대화1 (어제): "5억 대출 금리" → SearchTeam 실행
대화2 (오늘): "5억 대출 금리" → 1일 전 데이터, 재사용? 새로 검색?
```

금리는 매일 바뀌므로:
- **1일**: 어제 금리까지만 OK (권장)
- **0.5일**: 12시간 전 금리까지만 OK (엄격)

**사용자 선택**: ___일?

---

### 정리

| Intent | 데이터 특성 | 권장 기준 | 사용자 선택 |
|--------|-----------|---------|-----------|
| MARKET_INQUIRY (시세) | 자주 변동 | 7일 | ___일 |
| LEGAL_CONSULT (법률) | 안정적 | 30일 | ___일 |
| LOAN_CONSULT (대출) | 매일 변동 | 1일 | ___일 |

**또는**: "일단 권장 기준으로 하고, 2주 후 데이터 보고 조정" 가능!

---

## 🎯 Q4. 모든 데이터 + 다른 Agent 정보도 확인

### 사용자 요구사항 이해

```
"데이터는 모든 데이터로 하고 싶다.
다른 에이전트가 정보가 있다면 이전 대화에서의 정보를 확인하고
바로 분석에이전트를 사용한다"
```

### 해석

#### 현재 설계 (좁은 범위)
```
이전 대화: SearchTeam 실행 → 시세 데이터 저장
현재 대화: 같은 시세 질문 → SearchTeam 건너뛰기
```

#### 사용자 원하는 것 (넓은 범위)
```
이전 대화: SearchTeam 실행 → 여러 데이터 저장
            ├─ 법률 데이터
            ├─ 시세 데이터
            └─ 대출 데이터

현재 대화: 법률 질문 (LEGAL_CONSULT)
→ 이전 대화에 법률 데이터 있음?
  → YES: SearchTeam 건너뛰고 AnalysisTeam 바로 실행
  → NO: SearchTeam 실행
```

### 구현 방향

#### 1단계: SearchTeam 전체 결과 확인

```python
# planning_node()

# 이전 State 로드
prev_state = await self.checkpointer.aget(config)

# SearchTeam 결과 확인
prev_search_results = prev_state.values.get("team_results", {}).get("search", {})

# ✅ 여러 데이터 확인 가능!
has_legal = bool(prev_search_results.get("legal_search"))
has_market = bool(prev_search_results.get("real_estate_search"))
has_loan = bool(prev_search_results.get("loan_search"))
```

#### 2단계: Intent별 필요 데이터 매칭

```python
# 현재 Intent에 필요한 데이터가 이전 대화에 있는지 확인

if current_intent == "legal_consult":
    # 법률 데이터 필요
    if has_legal and is_fresh(prev_time):
        skip_search = True

elif current_intent == "market_inquiry":
    # 시세 데이터 필요
    if has_market and is_fresh(prev_time):
        skip_search = True

elif current_intent == "loan_consult":
    # 대출 데이터 필요
    if has_loan and is_fresh(prev_time):
        skip_search = True
```

#### 3단계: 다른 Agent 정보도 확인 (DocumentTeam, AnalysisTeam)

```python
# DocumentTeam 결과 확인
prev_document = prev_state.values.get("team_results", {}).get("document", {})

# AnalysisTeam 결과 확인
prev_analysis = prev_state.values.get("team_results", {}).get("analysis", {})

# 예: 계약서 검토 Intent인데 이전에 DocumentTeam 결과 있으면
if current_intent == "contract_review":
    if prev_document.get("review_result"):
        skip_document = True  # DocumentTeam도 건너뛰기!
```

### 정리

**사용자 원하는 것 = "똑똑한 재사용"**

| 이전 대화 | 현재 질문 | 건너뛸 팀 | 실행할 팀 |
|----------|---------|---------|---------|
| 시세 검색 | "시세는?" | Search ✅ | Analysis만 |
| 시세 검색 | "법률은?" | (없음) | Search + Analysis |
| 시세+법률 검색 | "법률은?" | Search ✅ | Analysis만 |
| 계약서 검토 | "다시 검토해줘" | Document ✅ | Analysis만 |

**구현**: Intent별로 필요한 데이터 타입을 매칭하는 로직 추가!

---

## 🤔 Q5. Entity 정확 일치 vs 유사도 - 현재 구조로 가능한가?

### 현재 구조 확인

**planning_agent.py - analyze_intent() 결과**:
```python
{
  "intent_type": "market_inquiry",
  "entities": {
    "region": "강남구",           # ← 문자열 그대로
    "property_type": "아파트"      # ← 문자열 그대로
  }
}
```

### 정확 일치 (Phase 1) - **현재 구조로 바로 가능!**

```python
# 비교 로직
current_region = "강남구"
prev_region = "강남구"

if current_region == prev_region:  # ✅ 그대로 비교
    match = True
```

**결론**: **설정 변경 불필요!** 바로 구현 가능!

---

### 유사도 매칭 (Phase 2) - **새로 설정 필요**

#### Case 1: "강남" vs "강남구"

**문제**:
```python
"강남" == "강남구"  # ❌ False
```

**해결책 (정규화)**:
```python
def normalize_region(region: str) -> str:
    """지역명 정규화"""
    if not region:
        return region

    # "구/시/군" 제거
    region = region.rstrip("구시군동읍면리")

    # "강남" → "강남구" 매핑 테이블
    region_mapping = {
        "강남": "강남구",
        "서초": "서초구",
        "송파": "송파구",
        # ... 더 추가
    }

    return region_mapping.get(region, region + "구")

# 사용
normalize_region("강남") == normalize_region("강남구")  # ✅ True
```

**필요한 것**:
- 정규화 함수 추가 (30줄)
- 지역 매핑 테이블 (서울 25개 구)

---

#### Case 2: "5억" vs "5.5억" (금액 범위)

**문제**:
```python
500000000 == 550000000  # ❌ False
```

**해결책 (범위 허용)**:
```python
def amount_within_range(current: int, prev: int, threshold: float = 0.2) -> bool:
    """금액 ±20% 이내 매칭"""
    if prev == 0:
        return False

    diff_ratio = abs(current - prev) / prev
    return diff_ratio <= threshold

# 사용
amount_within_range(550000000, 500000000)  # ✅ True (10% 차이)
amount_within_range(700000000, 500000000)  # ❌ False (40% 차이)
```

**필요한 것**:
- 범위 비교 함수 (10줄)
- threshold 설정 (±20%? ±30%?)

---

### 정리

| 기능 | 현재 구조 | 추가 설정 | Phase |
|------|---------|---------|-------|
| **정확 일치** | ✅ 바로 가능 | 불필요 | Phase 1 (지금) |
| **정규화** | ❌ 불가능 | 함수 30줄 + 매핑 테이블 | Phase 2 (나중) |
| **범위 허용** | ❌ 불가능 | 함수 10줄 + threshold 설정 | Phase 2 (나중) |

**권장**: Phase 1은 정확 일치만, Phase 2에서 유사도 추가!

---

## 💬 Q6. "재사용 중" 알림 - 의도 명확화

### 제 의도 (기존)

```
프론트엔드 화면:
┌─────────────────────────────────────┐
│ 💡 최근 검색 결과를 재사용하여      │
│    빠르게 응답합니다 (2분 전 데이터) │
└─────────────────────────────────────┘

사용자 질문: "강남구 아파트 시세"
AI 답변: (빠르게 응답)
```

→ 사용자에게 "왜 빠른지" 설명

---

### 사용자 제안 (개선)

```
프론트엔드 화면:
┌─────────────────────────────────────┐
│ 🔄 이전 대화의 정보를 반영하여       │
│    분석 중입니다...                 │
└─────────────────────────────────────┘
```

→ **더 자연스럽고 긍정적!** ✅

---

### 구현 위치

#### Option A: WebSocket 메시지

```python
# team_supervisor.py - planning_node()

if can_skip_search:
    state["search_skipped"] = True

    # 🆕 WebSocket 메시지
    if progress_callback:
        await progress_callback("data_reuse", {
            "message": "이전 대화의 정보를 반영하여 분석 중입니다...",
            "data_age": "2분 전"
        })
```

**프론트엔드 수정 필요**: WebSocket 메시지 핸들러 추가

---

#### Option B: 응답 생성 시 포함

```python
# generate_response_node()

if state.get("search_skipped"):
    response["note"] = "이전 대화의 정보를 반영하여 분석했습니다."
```

**프론트엔드 수정**: 응답에 note 필드 표시

---

### 질문

**어느 방식을 선호하시나요?**
- [ ] Option A (실시간 알림) - WebSocket 수정 필요
- [ ] Option B (응답에 포함) - 간단, 수정 최소
- [ ] Option C (둘 다)
- [ ] Option D (알림 없이 조용히 처리)

---

## ⏰ Q7. 오래된 데이터 처리

### 사용자 의견

> "오래된 데이터는 사용하지 않는 게 좋을 것 같다.
> 혹은 '데이터가 과거에 진행되었습니다' 이런 형태면 어떤가?"

### 해석

**Option A: 오래된 데이터 아예 안 씀** (엄격)
```python
if age > 7_days:
    skip = False  # 무조건 새로 검색
```

**Option B: 오래된 데이터 쓰되, 사용자에게 알림** (유연)
```python
if age > 7_days:
    skip = False  # 새로 검색

elif age > 5_days:  # 5~7일 사이 (경계선)
    skip = True
    # 응답에 경고 추가
    response["warning"] = "⚠️ 6일 전 데이터 기반입니다. 최신 정보가 필요하면 다시 요청해주세요."
```

---

### 구현 제안

```python
# planning_node()

MAX_AGE = {
    "market_inquiry": 7 * 24 * 3600,   # 7일
    "legal_consult": 30 * 24 * 3600,   # 30일
    "loan_consult": 1 * 24 * 3600      # 1일
}

age_seconds = (datetime.now() - prev_time).total_seconds()
max_age = MAX_AGE.get(intent_type, 7 * 24 * 3600)

if age_seconds > max_age:
    # 🔴 너무 오래됨 → 새로 검색
    skip = False
    logger.info(f"Data too old: {age_seconds/3600:.1f} hours")

elif age_seconds > max_age * 0.7:  # 70% 지점
    # 🟡 경계선 → 재사용하되 경고
    skip = True
    state["data_age_warning"] = f"{age_seconds/86400:.1f}일 전 데이터입니다"

else:
    # 🟢 신선함 → 안전하게 재사용
    skip = True
```

**프론트엔드 표시**:
```
┌─────────────────────────────────────┐
│ ⚠️ 5일 전 데이터 기반 분석입니다.    │
│    최신 정보가 필요하면 다시 요청해주세요 │
└─────────────────────────────────────┘
```

---

### 질문

**어느 방식을 선호하시나요?**
- [ ] Option A (오래된 데이터 무조건 새로 검색)
- [ ] Option B (재사용하되 경고 표시) - **추천!**
- [ ] 경계선 비율: 70%? 80%? ____%

---

## 📋 최종 확정 사항 정리

### 확정된 것 ✅

1. **Q1**: Checkpointer 작동 ✅
2. **Q4**: 모든 Intent 적용 + 다른 Agent 정보도 확인 ✅
3. **Q6**: "이전 대화 정보 반영하여 분석 중" 메시지 ✅
4. **Q7**: 오래된 데이터 경고 표시 방식 ✅

---

### 아직 답변 필요 ⏳

1. **Q2**: entities 확인 방법 선택
   - [ ] 로그 확인
   - [ ] SQL 쿼리
   - [ ] 테스트 스크립트
   - [ ] 모두

2. **Q3**: Intent별 신선도 기준 (일수)
   - MARKET_INQUIRY: ___일 (권장 7일)
   - LEGAL_CONSULT: ___일 (권장 30일)
   - LOAN_CONSULT: ___일 (권장 1일)
   - [ ] 또는 "권장대로"

3. **Q5**: Phase 1은 정확 일치만?
   - [ ] Yes (권장)
   - [ ] No, 유사도도 지금 구현

4. **Q6**: 알림 방식
   - [ ] WebSocket 실시간
   - [ ] 응답에 포함
   - [ ] 둘 다
   - [ ] 없음

5. **Q7**: 경계선 비율
   - [ ] 70% (권장)
   - [ ] 80%
   - [ ] 기타: ___%

---

## 🚀 다음 단계

**답변 받은 후**:
1. 최종 구현 계획 작성 (10분)
2. 코드 작성 (15~30분)
3. 테스트 (10분)

**예상 총 시간**: 35~50분

---

**작성**: Claude Code
**상태**: 사용자 추가 답변 대기 중
