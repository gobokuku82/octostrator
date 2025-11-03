# 다음 단계 계획서 (Next Steps Plan)

**작성일**: 2025-10-20
**현재 상태**: Option A 구현 및 기본 테스트 완료
**목적**: 향후 개선 및 고도화 방향 제시

---

## 📋 목차

1. [현재까지 완료된 작업](#1-현재까지-완료된-작업)
2. [현재 시스템 상태 평가](#2-현재-시스템-상태-평가)
3. [다음 단계 옵션](#3-다음-단계-옵션)
4. [권장 진행 방향](#4-권장-진행-방향)
5. [고도화 테스트 시나리오](#5-고도화-테스트-시나리오)
6. [Option B/C 구현 계획 (선택)](#6-option-bc-구현-계획-선택)
7. [Phase 2 준비 사항](#7-phase-2-준비-사항)

---

## 1. 현재까지 완료된 작업

### ✅ Phase 0: 기본 구조 개선 (완료)
- IRRELEVANT 필터 제거 (모든 쿼리에서 Long-term Memory 접근)
- Memory Configuration 문서화
- `.env` 설정 추가 (`MEMORY_LOAD_LIMIT=5`)

### ✅ Phase 1: Long-term Memory 기본 구현 (완료)
- `load_recent_memories()` 메서드 구현
- `save_conversation()` 메서드 구현
- `chat_sessions.metadata` 활용한 메모리 저장/로드
- 현재 세션 제외 로직 구현

### ✅ Option A: Chat History 기반 Intent 분석 개선 (완료)
- `_get_chat_history()` 메서드 추가
- `planning_node`에서 Chat History 조회 및 Context 전달
- `_analyze_with_llm()` 수정 (Chat History 포맷팅)
- `intent_analysis.txt` Prompt 수정 (Chat History 섹션 추가)

### ✅ 기본 테스트 완료 (4/4 성공)
| # | 질문 | Intent | 결과 |
|---|------|--------|------|
| 1 | "강남구 아파트 전세 시세 알려줘" | MARKET_INQUIRY | ✅ |
| 2 | "그럼 송파구는?" | MARKET_INQUIRY | ✅ |
| 3 | "2개 비교해줘" | MARKET_INQUIRY | ✅ |
| 4 | "멍청아" | IRRELEVANT | ✅ |

---

## 2. 현재 시스템 상태 평가

### ✅ 장점 (Strengths)

#### 1. 문맥 참조 질문 처리
- **성능**: "그럼 송파구는?" 같은 질문을 정확히 처리 (100% 성공)
- **이유**: Chat History가 이전 대화 맥락 제공
- **증거**: LLM reasoning에 "지시어로 이전 질문과 연결" 명시

#### 2. IRRELEVANT 정확도 유지
- **성능**: 부적절한 질문을 정확히 필터링 (100% 정확)
- **증거**: "멍청아" → IRRELEVANT (0.0 confidence)
- **장점**: False Positive 없음 (Chat History로 인한 오분류 없음)

#### 3. 성능 최적화
- **조기 종료**: IRRELEVANT 질문은 1.48s에 처리 (90% 시간 절약)
- **RELEVANT 영향**: +150ms (1.6% 증가, 허용 범위)
- **토큰 효율**: Chat History limit=3, content 500자 제한

#### 4. Long-term Memory 기본 기능
- **저장**: 대화 요약을 `chat_sessions.metadata`에 저장
- **로드**: 최근 N개 세션의 메모리 로드 (`MEMORY_LOAD_LIMIT` 설정)
- **격리**: 현재 진행 중인 세션 제외 (불완전한 데이터 방지)

---

### ⚠️ 제한 사항 (Limitations)

#### 1. Chat History 범위 제한
**현황**:
- 최근 3쌍 (6개 메시지)만 로드
- 매우 긴 대화에서 초기 맥락 손실 가능

**예시**:
```
대화 1: 강남구 시세 (8분 전)
대화 2-7: 다른 주제 (6분 전 ~ 1분 전)
대화 8: "아까 강남구 얼마라고 했지?" (현재)

결과: 대화 1이 범위 밖 → 참조 실패 가능
```

**영향도**: 낮음 (대부분 대화는 3쌍 내에서 해결)

---

#### 2. Long-term Memory vs Chat History 중복
**현황**:
- Long-term Memory: 세션 간 메모리 공유
- Chat History: 현재 세션 내 대화 기록

**문제**:
- Intent 분석에는 Chat History만 사용
- Long-term Memory는 Response 생성에만 사용
- 두 메커니즘이 분리되어 있음

**예시**:
```
[이전 세션 (2일 전)]
사용자: "강남구 아파트 전세 시세 알려줘"
AI: "5억~7억 범위입니다"

[현재 세션 (새 대화창)]
사용자: "그럼 송파구는?"

결과:
- Chat History 없음 (새 세션)
- Long-term Memory 있음 (2일 전 대화)
- Intent 분석: IRRELEVANT (Chat History만 참조)
```

**영향도**: 중간 (새 대화창에서 이전 주제 참조 시 발생)

---

#### 3. Long-term Memory 상세 정보 부족
**현황**:
- 현재: `conversation_summary`만 저장 (200자)
- 누락: query, intent, entities, metadata 등

**한계**:
- 상세한 검색 불가 (예: "강남구 관련 대화만")
- 시간 기반 필터링만 가능
- 의미 기반 검색 불가

**영향도**: 중간 (Phase 2에서 해결 예정)

---

#### 4. 문맥 참조의 모호성
**현황**:
- "그거", "그건", "아까" 같은 지시어는 처리 가능
- 하지만 여러 주제가 섞인 대화에서 혼란 가능

**예시**:
```
대화 1: 강남구 시세
대화 2: 송파구 시세
대화 3: 전세자금대출
사용자: "그거 얼마였지?"

문제: "그거"가 무엇을 가리키는지 불명확
- 강남구? 송파구? 대출 한도?
```

**영향도**: 낮음 (사용자가 명확히 질문하면 해결)

---

## 3. 다음 단계 옵션

### 옵션 1: 프로덕션 배포 (권장) ⭐
**설명**: 현재 상태로 프로덕션 배포 후 실사용 데이터 수집

**근거**:
- ✅ 핵심 문제 해결됨 (문맥 참조 질문 처리)
- ✅ 테스트 통과 (4/4 시나리오 성공)
- ✅ 성능 영향 최소화 (+1.6%)
- ✅ 안정성 확인 (에러 없음)

**장점**:
- 실제 사용자 피드백 수집 가능
- 실사용 패턴 분석 가능
- 데이터 기반 다음 개선 방향 결정

**다음 작업**:
1. 모니터링 대시보드 설정
2. Intent 분류 정확도 추적
3. 사용자 만족도 조사
4. 2주 후 데이터 분석

**예상 기간**: 2주 (모니터링 기간)

---

### 옵션 2: 고도화 테스트 진행 (선택)
**설명**: 더 복잡한 시나리오로 추가 테스트 수행

**목적**:
- Edge case 발견
- 시스템 한계 파악
- 개선 포인트 식별

**테스트 시나리오** (섹션 5 참조):
1. 긴 대화 후 초기 주제 참조 (limit=3 초과)
2. 여러 주제 섞인 대화에서 모호한 참조
3. 새 세션에서 이전 세션 주제 참조 (Long-term Memory vs Chat History)
4. 복잡한 복합 질문 (3개 이상 주제)
5. 연속된 문맥 참조 (3단계 이상)

**장점**:
- 배포 전 더 많은 검증
- 잠재적 문제 조기 발견

**단점**:
- 시간 소요 (1-2일)
- 실사용 데이터가 아님 (테스트 데이터)

**예상 기간**: 1-2일

---

### 옵션 3: Option B/C 구현 (선택)
**설명**: IRRELEVANT 개선 계획서의 Option B 또는 C 추가 구현

#### Option B: LLM Prompt 강화 (간단)
- Prompt에 추가 예시 및 가이드라인
- Few-shot learning 예시 추가
- 예상 시간: 2-3시간
- 예상 효과: +5%p 정확도

#### Option C: 앙상블 검증 (복잡)
- 패턴 매칭 + LLM 결합
- Confidence threshold 조정
- 예상 시간: 1일
- 예상 효과: +10%p 정확도

**근거**:
- 현재 정확도 이미 높음 (100% 테스트 통과)
- 추가 개선 효과 대비 비용 높음
- 우선순위 낮음

**예상 기간**: 2시간 ~ 1일

---

### 옵션 4: Phase 2 준비 (중장기)
**설명**: Long-term Memory 고도화 준비

**주요 작업**:
1. `conversation_memories` 테이블 설계
2. 상세 메타데이터 저장 구조 설계
3. 의미 기반 검색 (Vector DB) 설계
4. 크로스 세션 메모리 참조 로직 설계

**예상 기간**: 3-5일 (설계 + 구현)

---

## 4. 권장 진행 방향

### 🎯 권장: **옵션 1 (프로덕션 배포) + 옵션 2 (고도화 테스트 일부)**

#### 단계 1: 선택적 고도화 테스트 (0.5일)
**목적**: 배포 전 핵심 Edge case만 빠르게 검증

**우선순위 높은 테스트**:
1. ✅ **긴 대화 후 초기 주제 참조** (limit=3 초과)
   - 가장 발생 가능성 높음
   - 현재 제한사항의 실제 영향도 파악

2. ✅ **새 세션에서 이전 세션 주제 참조**
   - Long-term Memory와 Chat History 상호작용 검증
   - 크로스 세션 참조 동작 확인

3. ⏭️ **여러 주제 섞인 대화** (Skip 가능)
   - 사용자가 명확히 질문하면 해결됨
   - 우선순위 낮음

**예상 시간**: 반나절 (4-5시간)

---

#### 단계 2: 프로덕션 배포 (즉시)
**배포 체크리스트**:
- [x] 코드 구현 완료
- [x] 기본 테스트 통과 (4/4)
- [ ] 고도화 테스트 통과 (선택, 2/3)
- [x] 에러 핸들링 검증
- [ ] 모니터링 설정 (배포 후)

**배포 후 모니터링** (2주):
```
주요 지표:
1. Intent 분류 정확도
   - IRRELEVANT 오분류율
   - RELEVANT 정확도

2. 응답 시간
   - P50, P95, P99
   - Chat History 로드 시간

3. Chat History 활용률
   - Chat History가 있는 질문 비율
   - Chat History로 Intent 변경된 비율

4. 사용자 만족도
   - 문맥 참조 질문 성공률
   - "부동산과 관련 없음" 응답 비율
```

---

#### 단계 3: 데이터 분석 및 다음 단계 결정 (2주 후)
**수집할 데이터**:
1. 실사용 문맥 참조 질문 패턴
2. IRRELEVANT 오분류 사례
3. Chat History limit=3 초과 케이스
4. Long-term Memory 활용 사례

**의사결정 기준**:
```
If (IRRELEVANT 오분류율 > 10%):
    → Option B/C 구현 고려

If (Chat History limit=3 부족 사례 > 5%):
    → limit=5로 증가 고려

If (크로스 세션 참조 요구 > 20%):
    → Phase 2 조기 시작 고려

Else:
    → 현재 상태 유지, 다른 기능 개선
```

---

## 5. 고도화 테스트 시나리오

### 🔬 테스트 1: 긴 대화 후 초기 주제 참조 ⭐ 우선순위 높음

**목적**: Chat History limit=3 제한 검증

**시나리오**:
```
대화 1 (10분 전): "강남구 아파트 전세 시세 알려줘"
대화 2 (9분 전):  "송파구는?"
대화 3 (8분 전):  "서초구는?"
대화 4 (7분 전):  "전세자금대출 한도 알려줘"
대화 5 (6분 전):  "LTV가 뭐야?"
대화 6 (5분 전):  "DTI는?"
대화 7 (4분 전):  "금리 비교해줘"
대화 8 (현재):    "아까 강남구 시세 얼마라고 했지?" ← 테스트 대상
```

**Chat History 상태**:
- 로드됨: 대화 6, 7 (최근 3쌍 = 6메시지)
- 범위 밖: 대화 1 (강남구 관련)

**예상 결과**:
- **Option A**: Intent 분류 실패 가능 (Chat History에 강남구 없음)
- **Option B**: "강남구" 키워드로 MARKET_INQUIRY 추론 가능

**검증 포인트**:
1. Intent 분류 결과 (MARKET_INQUIRY vs IRRELEVANT)
2. LLM Reasoning 내용
3. 응답 품질 (강남구 시세 제공 여부)

**예상 결과**:
- 시나리오 A: Intent = MARKET_INQUIRY (키워드 "강남구", "시세"로 추론) ✅
- 시나리오 B: Intent = IRRELEVANT (Chat History에 강남구 없음) ❌

**개선 방안** (실패 시):
- limit=3 → limit=5로 증가
- 또는 Long-term Memory를 Intent 분석에도 활용

---

### 🔬 테스트 2: 새 세션에서 이전 세션 주제 참조 ⭐ 우선순위 높음

**목적**: Long-term Memory vs Chat History 상호작용 검증

**시나리오**:
```
[이전 세션 - 2일 전]
사용자: "강남구 아파트 전세 시세 알려줘"
AI: "5억~7억 범위입니다"
→ Long-term Memory 저장: "강남구 아파트 전세 시세 조회"

[현재 세션 - 새 대화창]
사용자: "그럼 송파구는?" ← 테스트 대상
```

**시스템 상태**:
- Chat History: 없음 (새 세션)
- Long-term Memory: 있음 (2일 전 대화)

**예상 결과**:
- **현재 구현**: IRRELEVANT (Chat History만 참조)
- **이상적**: MARKET_INQUIRY (Long-term Memory 참조)

**검증 포인트**:
1. Intent 분류 결과
2. Chat History 로드 결과 (빈 리스트 예상)
3. Long-term Memory 로드 결과 (2일 전 대화 포함)
4. LLM이 Long-term Memory를 활용했는지 여부

**예상 결과**:
- Intent = IRRELEVANT (Chat History 없음) ❌

**개선 방안** (실패 시):
- Intent 분석에 Long-term Memory도 Context로 전달
- `_analyze_with_llm()`에서 `context["long_term_memory"]` 추가

---

### 🔬 테스트 3: 여러 주제 섞인 대화에서 모호한 참조

**목적**: 지시어 모호성 처리 검증

**시나리오**:
```
대화 1: "강남구 아파트 전세 시세 알려줘"
대화 2: "송파구 전세 시세는?"
대화 3: "전세자금대출 한도는?"
대화 4: "그거 얼마였지?" ← 테스트 대상
```

**모호성**:
- "그거"가 무엇을 가리키는지 불명확
- 강남구? 송파구? 대출 한도?

**예상 결과**:
- LLM이 가장 최근 주제(대출 한도)로 추론
- 또는 UNCLEAR로 분류하여 명확화 요청

**검증 포인트**:
1. Intent 분류 결과
2. LLM Reasoning (어떤 주제로 판단했는지)
3. Entities 추출 결과

**우선순위**: 낮음 (사용자가 명확히 질문하면 해결됨)

---

### 🔬 테스트 4: 복잡한 복합 질문

**목적**: 여러 의도가 섞인 질문 처리 검증

**시나리오**:
```
대화 1: "강남구 전세 시세 알려줘"
대화 2: "거기 전세자금대출 한도랑 법률 상담도 해줘"
```

**복합 의도**:
- MARKET_INQUIRY (강남구 시세)
- LOAN_CONSULT (대출 한도)
- LEGAL_CONSULT (법률 상담)

**예상 결과**:
- Intent = COMPREHENSIVE
- Query Decomposer가 3개 서브 태스크로 분리

**우선순위**: 중간 (Query Decomposer 기능 검증)

---

### 🔬 테스트 5: 연속된 문맥 참조 (3단계 이상)

**목적**: 깊은 문맥 추적 검증

**시나리오**:
```
대화 1: "강남구 아파트 전세 시세 알려줘"
대화 2: "그거 작년보다 올랐어?"
대화 3: "그럼 그 추세가 계속될까?"
대화 4: "그거 때문에 지금 계약하는 게 나을까?" ← 테스트 대상
```

**복잡도**:
- 대화 4의 "그거"는 대화 3의 "추세"를 가리킴
- 대화 3의 "그 추세"는 대화 2의 "작년 대비 상승"을 가리킴
- 대화 2의 "그거"는 대화 1의 "강남구 시세"를 가리킴

**예상 결과**:
- Chat History (3쌍)로 추적 가능
- Intent = COMPREHENSIVE (복합 분석 필요)

**우선순위**: 낮음 (실제 발생 빈도 낮음)

---

## 6. Option B/C 구현 계획 (선택)

### Option B: LLM Prompt 강화

**목적**: Few-shot learning으로 정확도 향상

**구현 계획**:

#### 1. Prompt 개선 (2시간)

**파일**: `backend/app/service_agent/llm_manager/prompts/cognitive/intent_analysis.txt`

**추가 섹션**:
```
---

## 🔹 추가 예시 (Few-shot Learning)

### 예시 1: 문맥 참조 질문
**Chat History**:
사용자: 강남구 아파트 전세 시세 알려줘
AI: 5억~7억 범위입니다

**현재 질문**: 그럼 송파구는?

**올바른 분석**:
{
  "intent": "MARKET_INQUIRY",
  "confidence": 0.9,
  "keywords": ["송파구", "시세", "아파트", "전세"],
  "reasoning": "지시어 '그럼'으로 이전 대화와 연결. 이전 대화가 강남구 아파트 전세 시세였으므로, 현재 질문은 송파구 아파트 전세 시세를 묻는 것."
}

### 예시 2: 명확히 관련 없는 질문
**Chat History**:
사용자: 강남구 아파트 전세 시세 알려줘
AI: 5억~7억 범위입니다

**현재 질문**: 오늘 날씨 어때?

**올바른 분석**:
{
  "intent": "IRRELEVANT",
  "confidence": 0.0,
  "keywords": [],
  "reasoning": "날씨는 부동산과 무관. Chat History에 부동산 대화가 있어도, 현재 질문이 명백히 다른 주제."
}

### 예시 3: 모호한 참조
**Chat History**:
사용자: 강남구 전세 시세는?
AI: 5억~7억입니다
사용자: 송파구는?
AI: 4억~6억입니다
사용자: 전세자금대출 한도는?
AI: 최대 3억입니다

**현재 질문**: 그거 얼마였지?

**올바른 분석**:
{
  "intent": "UNCLEAR",
  "confidence": 0.0,
  "keywords": ["그거"],
  "reasoning": "'그거'가 가리키는 대상이 불명확. 강남구? 송파구? 대출 한도? 사용자에게 명확화 요청 필요."
}
```

**예상 효과**:
- +5%p 정확도 향상
- Edge case 처리 개선

---

### Option C: 앙상블 검증 (고급)

**목적**: 패턴 매칭 + LLM 결합으로 정확도 극대화

**구현 계획**:

#### 1. 패턴 매칭 강화 (3시간)

**파일**: `backend/app/service_agent/cognitive_agents/planning_agent.py`

**추가 로직**:
```python
def _analyze_with_patterns(self, query: str, context: Optional[Dict]) -> IntentResult:
    """패턴 매칭 기반 분석 (fallback + 앙상블)"""

    # Chat History에서 최근 주제 추출
    recent_topics = []
    if context and context.get("chat_history"):
        for msg in context["chat_history"]:
            if msg["role"] == "user":
                # 주제 키워드 추출 (지역명, 계약 타입 등)
                topics = self._extract_topics(msg["content"])
                recent_topics.extend(topics)

    # 지시어 패턴 감지
    context_reference_patterns = [
        r"그럼", r"그거", r"그건", r"그게", r"아까",
        r"위에", r"앞에서", r"이전에", r"전에"
    ]

    has_reference = any(
        re.search(pattern, query)
        for pattern in context_reference_patterns
    )

    # 앙상블 로직
    if has_reference and recent_topics:
        # 지시어 + 최근 주제 있음 → 문맥 참조 질문
        # LLM 판단과 관계없이 RELEVANT 처리
        return IntentResult(
            intent_type=self._infer_intent_from_topics(recent_topics),
            confidence=0.8,
            keywords=recent_topics,
            reasoning="지시어 감지 + 최근 대화 주제 참조"
        )

    # 기존 패턴 매칭 로직...
```

#### 2. Confidence Threshold 조정 (1시간)

**파일**: `backend/app/service_agent/cognitive_agents/planning_agent.py`

**추가 로직**:
```python
async def analyze_intent(self, query: str, context: Optional[Dict] = None) -> IntentResult:
    """의도 분석 (앙상블 검증 포함)"""

    # LLM 분석
    llm_result = await self._analyze_with_llm(query, context)

    # 패턴 분석
    pattern_result = self._analyze_with_patterns(query, context)

    # 앙상블 검증
    if llm_result.intent_type != pattern_result.intent_type:
        # 불일치 시 더 높은 confidence 채택
        if pattern_result.confidence > llm_result.confidence:
            logger.warning(
                f"Intent mismatch: LLM={llm_result.intent_type}, "
                f"Pattern={pattern_result.intent_type}. "
                f"Using Pattern result (higher confidence)"
            )
            return pattern_result

    return llm_result
```

**예상 효과**:
- +10%p 정확도 향상
- Edge case 대부분 처리

**단점**:
- 복잡도 증가
- 유지보수 부담

---

## 7. Phase 2 준비 사항

### Phase 2 목표: Long-term Memory 고도화

**주요 개선 사항**:
1. 상세 메타데이터 저장 (query, intent, entities)
2. 의미 기반 검색 (Vector DB)
3. 크로스 세션 메모리 참조
4. 메모리 검색 API

---

### 7.1 `conversation_memories` 테이블 설계

**테이블 구조**:
```sql
CREATE TABLE conversation_memories (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(100) NOT NULL,
    user_id INTEGER NOT NULL,

    -- 대화 내용
    query TEXT NOT NULL,
    response_summary TEXT NOT NULL,

    -- 의도 분석 결과
    intent_detected VARCHAR(50),
    confidence FLOAT,

    -- 엔티티 추출
    entities JSONB,  -- {"location": "강남구", "contract_type": "전세"}
    keywords TEXT[],

    -- 메타데이터
    conversation_metadata JSONB,  -- 기존 8개 파라미터

    -- Vector Embedding (의미 검색용)
    query_embedding VECTOR(384),  -- KURE_v1 모델 차원

    -- 타임스탬프
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- 인덱스
    FOREIGN KEY (session_id) REFERENCES chat_sessions(session_id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- 인덱스
CREATE INDEX idx_conv_mem_user_id ON conversation_memories(user_id);
CREATE INDEX idx_conv_mem_session_id ON conversation_memories(session_id);
CREATE INDEX idx_conv_mem_intent ON conversation_memories(intent_detected);
CREATE INDEX idx_conv_mem_created_at ON conversation_memories(created_at DESC);

-- Vector 인덱스 (의미 검색)
CREATE INDEX idx_conv_mem_embedding ON conversation_memories
USING ivfflat (query_embedding vector_cosine_ops);
```

---

### 7.2 의미 기반 검색 설계

**목적**: "강남구 관련 대화 찾기" 같은 의미 검색

**구현 방안**:

#### Option A: PostgreSQL pgvector 확장 (권장)
- 이미 PostgreSQL 사용 중
- 추가 인프라 불필요
- 중소 규모 충분

#### Option B: FAISS 별도 저장
- 현재 Legal Search에서 사용 중
- 대규모 검색 성능 우수
- 추가 유지보수 필요

**권장**: Option A (PostgreSQL pgvector)

---

### 7.3 크로스 세션 메모리 참조 설계

**목적**: 새 세션에서도 이전 세션 대화 참조

**구현 계획**:

#### 1. Intent 분석에 Long-term Memory 추가

**파일**: `backend/app/service_agent/supervisor/team_supervisor.py`

**수정**:
```python
# 의도 분석
query = state.get("query", "")
chat_session_id = state.get("chat_session_id")

# 1. Chat History 조회 (현재 세션)
chat_history = await self._get_chat_history(
    session_id=chat_session_id,
    limit=3
)

# 2. Long-term Memory 조회 (이전 세션들)
long_term_memory = await self._get_long_term_memory(
    user_id=state.get("user_id"),
    limit=5
)

# Context 생성 (Chat History + Long-term Memory)
context = {
    "chat_history": chat_history,
    "long_term_memory": long_term_memory
}

# Intent 분석 (확장된 context 전달)
intent_result = await self.planning_agent.analyze_intent(query, context)
```

#### 2. Prompt 수정

**파일**: `backend/app/service_agent/llm_manager/prompts/cognitive/intent_analysis.txt`

**추가 섹션**:
```
---

## 🔹 이전 대화 요약 (Long-term Memory)

다른 대화창에서 나눈 대화 요약입니다.

{long_term_memory}

---

**분석 지침 (Long-term Memory)**:
1. Long-term Memory에서 관련 주제를 찾으세요
2. 현재 질문이 이전 대화 주제를 참조하면, 해당 의도로 분류하세요
3. 단, Chat History가 더 최근이므로 우선순위가 높습니다
```

**예상 효과**:
- 새 세션에서도 이전 주제 참조 가능
- "그럼 송파구는?" 같은 질문을 새 대화창에서도 처리

---

### 7.4 Phase 2 구현 순서

#### 단계 1: 테이블 생성 (0.5일)
- `conversation_memories` 테이블 생성
- pgvector 확장 설치
- 인덱스 생성

#### 단계 2: 저장 로직 구현 (1일)
- `save_conversation()` 확장 (8개 파라미터 저장)
- Embedding 생성 및 저장
- Migration 스크립트

#### 단계 3: 검색 로직 구현 (1일)
- 의미 기반 검색 API
- 크로스 세션 메모리 로드
- Intent 분석에 Long-term Memory 통합

#### 단계 4: 테스트 및 검증 (1일)
- 크로스 세션 참조 테스트
- 의미 검색 테스트
- 성능 테스트

**예상 총 기간**: 3.5일

---

## 📊 의사결정 매트릭스

| 옵션 | 소요 시간 | 우선순위 | 즉시 효과 | 장기 가치 | 권장도 |
|------|-----------|----------|-----------|-----------|--------|
| **옵션 1: 프로덕션 배포** | 즉시 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ✅ **강력 권장** |
| **옵션 2: 고도화 테스트 (일부)** | 0.5일 | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ✅ 권장 |
| **옵션 2: 고도화 테스트 (전체)** | 1-2일 | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ | △ 선택 |
| **옵션 3: Option B** | 2시간 | ⭐⭐ | ⭐⭐ | ⭐⭐ | △ 선택 |
| **옵션 3: Option C** | 1일 | ⭐⭐ | ⭐⭐ | ⭐ | ✖️ 비권장 |
| **옵션 4: Phase 2** | 3.5일 | ⭐⭐⭐ | ⭐ | ⭐⭐⭐⭐⭐ | ⏰ 중장기 |

---

## 🎯 최종 권장사항

### ✅ 즉시 진행 (오늘)

**1. 고도화 테스트 2개 실행 (0.5일)**
- ✅ 테스트 1: 긴 대화 후 초기 주제 참조
- ✅ 테스트 2: 새 세션에서 이전 세션 주제 참조

**2. 프로덕션 배포 (즉시)**
- 현재 코드 프로덕션 배포
- 모니터링 대시보드 설정
- 실사용 데이터 수집 시작

---

### ⏰ 단기 (2주 내)

**1. 모니터링 및 데이터 분석**
- Intent 분류 정확도 추적
- 사용자 피드백 수집
- Edge case 발견

**2. 데이터 기반 의사결정**
- IRRELEVANT 오분류율 확인
- Chat History limit=3 충분한지 확인
- 다음 개선 방향 결정

---

### 📅 중장기 (1개월 내)

**Phase 2 준비 및 구현**
- `conversation_memories` 테이블 설계
- 의미 기반 검색 구현
- 크로스 세션 메모리 참조 구현

---

## 📝 체크리스트

### 배포 전 체크리스트
- [x] 코드 구현 완료 (Option A)
- [x] 기본 테스트 통과 (4/4)
- [ ] 고도화 테스트 통과 (선택, 2개)
- [x] 에러 핸들링 검증
- [x] 문서화 완료

### 배포 후 체크리스트
- [ ] 모니터링 대시보드 설정
- [ ] 알림 설정 (에러율 > 5%)
- [ ] 주간 리포트 자동화
- [ ] 2주 후 데이터 분석 일정

---

## 📚 관련 문서

- [IRRELEVANT_IMPROVEMENT_PLAN_251020.md](./IRRELEVANT_IMPROVEMENT_PLAN_251020.md): 전체 개선 계획
- [OPTION_A_DETAILED_ANALYSIS_251020.md](./OPTION_A_DETAILED_ANALYSIS_251020.md): Option A 상세 분석
- [OPTION_A_IMPLEMENTATION_COMPLETE_251020.md](./OPTION_A_IMPLEMENTATION_COMPLETE_251020.md): Option A 구현 완료
- [PHASE_1_COMPLETION_SUMMARY_251020.md](./PHASE_1_COMPLETION_SUMMARY_251020.md): Phase 1 완료 요약

---

**작성 완료**: 2025-10-20
**다음 검토**: 프로덕션 배포 후 2주 (2025-11-03)
