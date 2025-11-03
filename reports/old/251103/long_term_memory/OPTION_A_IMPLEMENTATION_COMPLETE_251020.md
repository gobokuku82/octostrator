# Option A 구현 완료 - Chat History 기반 Intent 분석 개선

**날짜**: 2025-10-20
**목적**: 문맥 참조 질문의 IRRELEVANT 오분류 문제 해결
**상태**: ✅ 구현 완료

---

## 🎯 구현 개요

**문제**:
- "그럼 송파구는?" 같은 문맥 참조 질문이 IRRELEVANT로 오분류됨
- Intent 분석 시점에 이전 대화 맥락이 없어서 LLM이 판단할 수 없음

**해결책 (Option A)**:
- Intent 분석 전에 Chat History를 조회
- LLM Prompt에 Chat History 포함
- 문맥을 고려한 Intent 분석 가능

**예상 효과**:
- Intent 분류 정확도: 60% → 95% (+35%p)
- IRRELEVANT 오분류율: 40% → 5% (-35%p)
- 응답 시간 증가: +100ms (허용 가능)

---

## ✅ 구현 내역

### Step 1: ChatMessage 모델 확인 ✅

**파일**: `backend/app/models/chat.py`
**작업**: 기존 모델 구조 확인

**확인 사항**:
- `chat_messages` 테이블 존재
- 필드: id, session_id, role, content, structured_data, created_at
- Index 존재: session_id (성능 최적화)
- Foreign Key: chat_sessions 테이블과 연결

---

### Step 2: _get_chat_history() 메서드 추가 ✅

**파일**: `backend/app/service_agent/supervisor/team_supervisor.py`
**라인**: 807-864 (58줄 추가)

**추가된 메서드**:
```python
async def _get_chat_history(
    self,
    session_id: Optional[str],
    limit: int = 3
) -> List[Dict[str, str]]:
    """
    Chat history 조회 (최근 N개 대화 쌍)

    Args:
        session_id: 세션 ID
        limit: 조회할 대화 쌍 개수 (기본 3개 = 6개 메시지)

    Returns:
        Chat history 리스트:
        [
            {"role": "user", "content": "..."},
            {"role": "assistant", "content": "..."},
            ...
        ]
    """
    if not session_id:
        return []

    try:
        async for db_session in get_async_db():
            # Import
            from app.models.chat import ChatMessage
            from sqlalchemy import select

            # Query 구성
            query = (
                select(ChatMessage)
                .where(ChatMessage.session_id == session_id)
                .order_by(ChatMessage.created_at.desc())
                .limit(limit * 2)  # user + assistant 쌍
            )

            # 실행
            result = await db_session.execute(query)
            messages = result.scalars().all()

            # 시간순 정렬 (최신순 → 시간순)
            messages = sorted(messages, key=lambda m: m.created_at)

            # 포맷팅
            chat_history = [
                {
                    "role": msg.role,
                    "content": msg.content[:500]  # 길이 제한
                }
                for msg in messages
            ]

            return chat_history[-limit * 2:]  # 최근 N개 쌍만

    except Exception as e:
        logger.warning(f"Failed to load chat history: {e}")
        return []
```

**주요 특징**:
- Async 데이터베이스 접근 (`get_async_db()` 사용)
- 최근 N개 대화 쌍 조회 (기본 3쌍 = 6메시지)
- Content 길이 제한 (500자, 토큰 관리)
- 에러 발생 시 빈 리스트 반환 (Graceful degradation)

---

### Step 3: planning_node 수정 ✅

**파일**: `backend/app/service_agent/supervisor/team_supervisor.py`
**라인**: 196-210

**수정 전**:
```python
# 의도 분석
query = state.get("query", "")
intent_result = await self.planning_agent.analyze_intent(query)
```

**수정 후**:
```python
# 의도 분석
query = state.get("query", "")
chat_session_id = state.get("chat_session_id")

# Chat history 조회 (문맥 이해를 위해)
chat_history = await self._get_chat_history(
    session_id=chat_session_id,
    limit=3  # 최근 3개 대화 쌍 (6개 메시지)
)

# Context 생성
context = {"chat_history": chat_history} if chat_history else None

# Intent 분석 (context 전달)
intent_result = await self.planning_agent.analyze_intent(query, context)
```

**주요 변경점**:
- `chat_session_id` 추출
- `_get_chat_history()` 호출
- `context` 딕셔너리 생성 (chat_history 포함)
- `analyze_intent()`에 context 전달

---

### Step 4: _analyze_with_llm() 수정 ✅

**파일**: `backend/app/service_agent/cognitive_agents/planning_agent.py`
**라인**: 183-213

**수정 전**:
```python
async def _analyze_with_llm(self, query: str, context: Optional[Dict]) -> IntentResult:
    """LLM을 사용한 의도 분석 (LLMService 사용)"""
    try:
        # LLMService를 통한 의도 분석
        result = await self.llm_service.complete_json_async(
            prompt_name="intent_analysis",
            variables={"query": query},
            temperature=0.0,
            max_tokens=500
        )
```

**수정 후**:
```python
async def _analyze_with_llm(self, query: str, context: Optional[Dict]) -> IntentResult:
    """LLM을 사용한 의도 분석 (LLMService 사용)"""
    try:
        # Context에서 chat_history 추출
        chat_history = context.get("chat_history", []) if context else []

        # Chat history를 문자열로 포맷팅
        chat_history_text = ""
        if chat_history:
            formatted_history = []
            for msg in chat_history:
                role = msg.get("role", "unknown")
                content = msg.get("content", "")
                if role == "user":
                    formatted_history.append(f"사용자: {content}")
                elif role == "assistant":
                    formatted_history.append(f"AI: {content}")

            if formatted_history:
                chat_history_text = "\n".join(formatted_history)

        # LLMService를 통한 의도 분석
        result = await self.llm_service.complete_json_async(
            prompt_name="intent_analysis",
            variables={
                "query": query,
                "chat_history": chat_history_text
            },
            temperature=0.0,
            max_tokens=500
        )
```

**주요 변경점**:
- Context에서 `chat_history` 추출
- Chat history를 한글 형식으로 포맷팅 ("사용자:", "AI:")
- Variables에 `chat_history` 추가

---

### Step 5: intent_analysis.txt Prompt 수정 ✅

**파일**: `backend/app/service_agent/llm_manager/prompts/cognitive/intent_analysis.txt`
**라인**: 203-218 (16줄 추가)

**추가된 섹션**:
```
---

## 🔹 최근 대화 기록 (Chat History)

이전 대화 맥락을 참고하여 의도를 더 정확히 파악하세요.

{chat_history}

---

**현재 질문**: {query}

**분석 지침**:
1. 위 대화 기록을 참고하여 현재 질문의 맥락을 이해하세요
2. "그럼", "그거", "그건", "아까" 등의 지시어가 있으면 이전 대화에서 언급된 내용을 찾으세요
3. 이전 대화와 연결되는 질문이면 부동산 관련 질문으로 처리하세요

---
```

**기존 마지막 섹션 위치 변경**:
- 기존: `분석할 질문: {query}`
- 변경: Chat History 섹션 → 현재 질문 → 분석 지침

**주요 특징**:
- LLM에게 Chat History를 명시적으로 제공
- 지시어("그럼", "그거" 등) 처리 가이드
- 문맥 연결 질문을 부동산 관련으로 인식하도록 지시

---

## 📊 데이터 흐름

```
┌─────────────────────────────────────────────────────────────────┐
│                    Option A 데이터 흐름                           │
└─────────────────────────────────────────────────────────────────┘

1. 사용자 질문: "그럼 송파구는?"
   ↓
2. planning_node (team_supervisor.py:196-210)
   - chat_session_id 추출
   - _get_chat_history() 호출
   ↓
3. _get_chat_history() (team_supervisor.py:807-864)
   - DB에서 최근 3쌍 (6메시지) 조회
   - chat_messages 테이블 쿼리
   - 시간순 정렬 + 포맷팅
   ↓
4. context 생성
   - {"chat_history": [{"role": "user", "content": "..."}, ...]}
   ↓
5. analyze_intent(query, context) (planning_agent.py:160-181)
   - context를 _analyze_with_llm에 전달
   ↓
6. _analyze_with_llm() (planning_agent.py:183-213)
   - chat_history 추출
   - 한글 포맷으로 변환 ("사용자:", "AI:")
   - variables에 포함
   ↓
7. LLM Prompt (intent_analysis.txt:203-218)
   - Chat History 섹션 표시
   - 현재 질문과 분석 지침 제공
   ↓
8. LLM 분석
   - 이전 대화: "강남구 아파트 전세 시세 5억~7억"
   - 현재 질문: "그럼 송파구는?"
   - 판단: MARKET_INQUIRY (시세조회)
   ↓
9. IntentResult 반환
   - intent_type: MARKET_INQUIRY
   - confidence: 0.9
   - keywords: ["송파구", "시세"]
```

---

## 🧪 테스트 시나리오

### 시나리오 1: 기본 문맥 참조 질문

**세션 1 (초기 대화)**:
```
사용자: "강남구 아파트 전세 시세 알려줘"
AI: "강남구 아파트 전세 시세는 5억~7억 범위입니다..."
```

**세션 1 (후속 질문)**:
```
사용자: "그럼 송파구는?"

기대 결과:
- Chat History 로드: ✅ (1쌍, 2메시지)
- Intent 분석: MARKET_INQUIRY (confidence: 0.9+)
- 응답: "송파구 아파트 전세 시세는 4억~6억 범위입니다..."
```

**기존 문제 (수정 전)**:
- Intent: IRRELEVANT (confidence: 0.95)
- 응답: "무엇에 대해 질문하신 건가요?"

**수정 후 (Option A 적용)**:
- Intent: MARKET_INQUIRY (confidence: 0.9)
- 응답: 송파구 시세 정보 제공

---

### 시나리오 2: 복잡한 문맥 참조

**세션 2 (초기 대화)**:
```
사용자: "전세금 5% 인상이 가능한가요?"
AI: "네, 임대차보호법상 5% 인상이 가능합니다..."

사용자: "그럼 계약 갱신 거부는 가능해?"
AI: "임대인이 계약 갱신을 거부하려면..."
```

**세션 2 (후속 질문)**:
```
사용자: "아까 말한 5% 인상이랑 갱신 거부 관계는?"

기대 결과:
- Chat History 로드: ✅ (3쌍, 6메시지 - limit 도달)
- Intent 분석: LEGAL_CONSULT (confidence: 0.85+)
- 응답: 두 제도의 관계 설명
```

---

### 시나리오 3: 긴 대화 후 참조

**세션 3 (7번의 대화 후)**:
```
대화 1: 강남구 시세
대화 2: 송파구 시세
대화 3: 서초구 시세
대화 4: 전세자금대출
대화 5: LTV/DTI
대화 6: 대출 한도
대화 7: 금리 비교

사용자: "아까 강남구 시세 얼마라고 했지?"

기대 결과:
- Chat History 로드: ✅ (최근 3쌍만, 6메시지)
  - 대화 5, 6, 7만 로드 (대화 1은 범위 밖)
- Intent 분석: MARKET_INQUIRY (confidence: 0.7+)
  - "강남구" 키워드로 시세 질문임을 파악
- 응답: "이전 대화에서 강남구 시세는 5억~7억으로 안내드렸습니다"
```

**Note**: limit=3으로 제한하므로 매우 오래된 대화는 로드되지 않음
- 성능 최적화 (토큰 절약)
- 최근 맥락에 집중

---

## 📈 예상 성능 영향

### 응답 시간 분석

**추가된 처리 단계**:
1. `_get_chat_history()`: DB 쿼리 1회
   - PostgreSQL index 사용 (session_id)
   - 예상 시간: ~50ms
2. Chat history 포맷팅: 문자열 변환
   - 예상 시간: ~10ms
3. LLM Prompt 토큰 증가: 최대 ~500 토큰
   - GPT-4o-mini 처리 시간 증가: ~40ms

**총 예상 증가**: ~100ms

**기존 응답 시간**:
- IRRELEVANT 질문: ~600ms (조기 종료)
- RELEVANT 질문: ~3000ms (전체 실행)

**수정 후 응답 시간**:
- 문맥 참조 질문: ~3100ms (+100ms, 3.3% 증가)
- 허용 가능한 범위 (사용자 체감 불가)

---

## 🔍 성능 최적화 포인트

### 1. Chat History Limit 제한
- 기본값: 3쌍 (6메시지)
- 토큰 관리: 최대 ~500 토큰
- Content 길이 제한: 각 메시지 500자

### 2. DB 쿼리 최적화
- `session_id` Index 활용 (이미 존재)
- `ORDER BY created_at DESC` + `LIMIT` 사용
- 불필요한 JOIN 없음

### 3. Graceful Degradation
- Chat history 로드 실패 시 빈 리스트 반환
- Intent 분석은 계속 진행 (에러 전파 방지)
- 로그만 warning 레벨로 기록

### 4. 조기 종료 유지
- IRRELEVANT 판단 후에도 조기 종료 유지
- Chat history는 Intent 분석 정확도만 향상
- 전체 실행 흐름은 변경 없음

---

## 🎯 구현 완료 확인

### ✅ 코드 변경사항
- [x] `team_supervisor.py`: `_get_chat_history()` 메서드 추가 (58줄)
- [x] `team_supervisor.py`: `planning_node` 수정 (14줄 → 15줄)
- [x] `planning_agent.py`: `_analyze_with_llm()` 수정 (11줄 → 31줄)
- [x] `intent_analysis.txt`: Chat History 섹션 추가 (16줄)

### ✅ 기능 검증 사항
- [x] ChatMessage 모델 구조 확인
- [x] Async DB 접근 패턴 구현
- [x] Context 파라미터 전달 체인 구현
- [x] LLM Prompt 변수 추가
- [x] 에러 핸들링 구현

### ⏳ 남은 작업 (테스트)
- [ ] 프론트엔드 테스트 (실제 대화 흐름)
- [ ] 성능 측정 (응답 시간 증가 확인)
- [ ] 로그 분석 (Intent 분류 정확도 확인)

---

## 📝 사용 가이드

### 개발자를 위한 참고사항

**1. Chat History 범위 조정**:
```python
# team_supervisor.py:201-204
chat_history = await self._get_chat_history(
    session_id=chat_session_id,
    limit=3  # ← 이 값을 조정하여 범위 변경 가능
)
```
- `limit=1`: 최근 1쌍 (2메시지, ~100 토큰)
- `limit=3`: 최근 3쌍 (6메시지, ~500 토큰) ← **기본값**
- `limit=5`: 최근 5쌍 (10메시지, ~800 토큰)

**2. Content 길이 제한 조정**:
```python
# team_supervisor.py:855
"content": msg.content[:500]  # ← 이 값을 조정
```

**3. Chat History가 없는 경우**:
- `context`는 `None`으로 전달됨
- LLM Prompt에서 `{chat_history}`는 빈 문자열
- 기존 방식과 동일하게 동작 (하위 호환성)

---

## 🔗 관련 문서

- [IRRELEVANT_IMPROVEMENT_PLAN_251020.md](./IRRELEVANT_IMPROVEMENT_PLAN_251020.md): 전체 계획서
- [OPTION_A_DETAILED_ANALYSIS_251020.md](./OPTION_A_DETAILED_ANALYSIS_251020.md): 상세 분석
- [PHASE_1_FINAL_FIX_251020.md](./PHASE_1_FINAL_FIX_251020.md): Phase 1 수정 기록

---

**구현 완료 시각**: 2025-10-20
**다음 단계**: 프론트엔드 테스트 및 성능 검증
