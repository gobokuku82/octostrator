# Long-term Memory Service 오류 수정 계획
**Issue Report & Fix Plan**

---

## 📋 요약 (Executive Summary)

**발생 오류:** `SimpleMemoryService` 객체에 `save_conversation` 및 `load_recent_memories` 메서드가 없음

**발생 일자:** 2025-10-16 ~ 현재 (지속적 발생)

**영향도:** 중간 (Long-term Memory 기능 완전 비활성화)

**우선순위:** High

**예상 수정 시간:** 1-2시간

---

## 🔍 문제 분석 (Root Cause Analysis)

### 1. 오류 로그 분석

```
2025-10-19 11:31:50 - app.service_agent.supervisor.team_supervisor - ERROR -
[TeamSupervisor] Failed to save Long-term Memory:
'SimpleMemoryService' object has no attribute 'save_conversation'
```

**발생 위치:**
- 파일: `backend/app/service_agent/supervisor/team_supervisor.py`
- 라인: 855 (planning_node), 873 (generate_response_node)

**발생 빈도:**
- 모든 사용자 쿼리마다 2번씩 발생 (로드 + 저장)
- 로그 분석 결과: 10월 16일부터 현재까지 약 100회 이상 발생

---

### 2. 원인 (Root Cause)

#### 2.1 코드 불일치 (Interface Mismatch)

**team_supervisor.py가 호출하는 메서드:**
```python
# planning_node (line 211-214)
loaded_memories = await memory_service.load_recent_memories(
    user_id=user_id,
    limit=settings.MEMORY_LOAD_LIMIT,
    relevance_filter="RELEVANT"
)

# generate_response_node (line 855)
await memory_service.save_conversation(
    user_id=user_id,
    query=state.get("query", ""),
    response_summary=response_summary,
    relevance="RELEVANT",
    session_id=chat_session_id,
    intent_detected=intent_type,
    entities_mentioned=analyzed_intent.get("entities", {}),
    conversation_metadata={...}
)
```

**SimpleMemoryService가 실제로 제공하는 메서드:**
```python
# simple_memory_service.py (line 97-120)
async def save_conversation_memory(...)  # ❌ 이름이 다름
    # 실제로는 아무것도 안하고 True만 반환

# load_recent_memories 메서드 자체가 없음 ❌
```

#### 2.2 설계 불일치

**SimpleMemoryService의 설계 의도:**
- ConversationMemory, EntityMemory, UserPreference 테이블 제거
- chat_messages 테이블만 사용하는 간소화된 구조
- 호환성 메서드들은 **no-op**(아무것도 안함)으로 구현

**문제점:**
1. `load_recent_memories` 메서드가 완전히 누락됨
2. `save_conversation` 대신 `save_conversation_memory`로 이름이 다름
3. TeamSupervisor는 old/memory_service.py의 인터페이스를 기대함

---

### 3. 영향 범위 (Impact Analysis)

#### 3.1 기능적 영향

**비활성화된 기능:**
- ✅ Long-term Memory 로딩 (Planning 단계)
- ✅ Long-term Memory 저장 (Response 생성 후)
- ✅ 사용자 대화 컨텍스트 추적
- ✅ 엔티티 추적 (properties, regions, agents)

**정상 작동하는 기능:**
- ✅ 실시간 채팅 (chat_messages 테이블)
- ✅ 세션별 대화 기록 (chat_sessions)
- ✅ 쿼리 처리 및 응답 생성 (에러는 무시됨)

#### 3.2 사용자 경험 영향

**현재 상태:**
- 사용자는 오류를 직접 보지 않음 (백엔드 로그만)
- 대화는 정상적으로 진행됨
- **BUT**: 이전 대화 컨텍스트가 활용되지 않음
  - 예: "아까 말한 강남 아파트" → AI가 기억 못함
  - 예: 사용자 선호도 학습 안됨

**잠재적 문제:**
- 개인화 기능 완전 비활성화
- 장기적 대화 품질 저하
- 데이터 기반 인사이트 수집 불가

---

## 🛠️ 수정 계획 (Fix Plan)

### Option 1: SimpleMemoryService에 누락된 메서드 추가 (권장)

**장점:**
- 최소한의 변경
- 기존 설계 유지 (chat_messages 기반)
- SimpleMemoryService의 간소화된 구조 유지

**단점:**
- Long-term Memory 기능이 실제로는 작동 안함 (no-op)
- 호환성만 제공, 실질적 가치 없음

**구현 방법:**

```python
# simple_memory_service.py에 추가

async def load_recent_memories(
    self,
    user_id: str,
    limit: int = 5,
    relevance_filter: Optional[str] = "RELEVANT"
) -> List[Dict[str, Any]]:
    """
    최근 대화 기록 로드 (호환성용 - chat_messages 기반)

    Note:
        - ConversationMemory 테이블 대신 chat_messages 사용
        - relevance_filter는 무시됨 (chat_messages에 relevance 필드 없음)

    Returns:
        최근 대화 메시지 리스트 (user_id로 필터링 불가능한 경우 빈 리스트)
    """
    logger.debug(f"load_recent_memories called: user_id={user_id}, limit={limit}")
    # chat_messages는 user_id가 없으므로 빈 리스트 반환
    # 필요시 session_id 기반 조회로 변경 가능
    return []


async def save_conversation(
    self,
    user_id: str,
    query: str,
    response_summary: str,
    relevance: str,
    session_id: Optional[str] = None,
    intent_detected: Optional[str] = None,
    entities_mentioned: Optional[Dict[str, Any]] = None,
    conversation_metadata: Optional[Dict[str, Any]] = None
) -> bool:
    """
    대화 저장 (호환성용 - 실제로는 no-op)

    Note:
        - ConversationMemory 테이블이 없으므로 저장 안됨
        - chat_messages에 자동으로 저장되므로 추가 작업 불필요
        - save_conversation_memory와 달리 old 인터페이스 호환

    Returns:
        항상 True (호환성)
    """
    logger.debug(
        f"save_conversation called (no-op): "
        f"user_id={user_id}, session_id={session_id}, intent={intent_detected}"
    )
    return True
```

---

### Option 2: old/memory_service.py로 복구 (완전한 기능)

**장점:**
- Long-term Memory 기능 완전 복구
- ConversationMemory, EntityMemory, UserPreference 활용
- 실질적인 대화 컨텍스트 추적

**단점:**
- 데이터베이스 마이그레이션 필요
- 테이블 추가 필요 (conversation_memories, entity_memories, user_preferences)
- 복잡도 증가

**필요 작업:**
1. DB 마이그레이션 생성 및 실행
2. `simple_memory_service.py` → `old/memory_service.py`로 교체
3. 관련 import 수정

---

### Option 3: Hybrid 접근 (중간 방안)

**개념:**
- SimpleMemoryService 유지
- `load_recent_memories`와 `save_conversation`는 **chat_messages 기반**으로 실제 구현
- ConversationMemory 테이블 없이 chat_messages로 대체

**구현:**

```python
async def load_recent_memories(
    self,
    user_id: str,
    limit: int = 5,
    relevance_filter: Optional[str] = "RELEVANT"
) -> List[Dict[str, Any]]:
    """
    최근 대화 기록 로드 (chat_messages 기반)
    """
    try:
        # user_id 기반 세션 조회 (chat_sessions 테이블)
        from app.models.chat import ChatSession

        session_query = select(ChatSession).where(
            ChatSession.user_id == user_id
        ).order_by(desc(ChatSession.created_at)).limit(3)

        session_result = await self.db.execute(session_query)
        sessions = session_result.scalars().all()

        if not sessions:
            return []

        # 최근 세션들의 메시지 조회
        session_ids = [s.session_id for s in sessions]

        messages_query = select(ChatMessage).where(
            ChatMessage.session_id.in_(session_ids),
            ChatMessage.role == "user"  # 사용자 쿼리만
        ).order_by(desc(ChatMessage.created_at)).limit(limit)

        messages_result = await self.db.execute(messages_query)
        messages = messages_result.scalars().all()

        # ConversationMemory 형식으로 변환
        return [
            {
                "query": msg.content,
                "response_summary": "",  # chat_messages에는 없음
                "relevance": "RELEVANT",  # 기본값
                "created_at": msg.created_at.isoformat(),
                "session_id": msg.session_id
            }
            for msg in messages
        ]

    except Exception as e:
        logger.error(f"Failed to load recent memories: {e}")
        return []
```

---

## 📝 권장 수정 방안 (Recommended Solution)

**선택:** **Option 1 + Option 3 혼합**

**이유:**
1. **즉각적 오류 해결:** Option 1로 AttributeError 즉시 제거
2. **점진적 기능 개선:** Option 3로 실제 기능 구현 (chat_messages 활용)
3. **DB 마이그레이션 불필요:** 기존 테이블 활용
4. **SimpleMemoryService 설계 유지:** 간소화된 구조 유지

---

## 🔧 구현 단계 (Implementation Steps)

### Step 1: 긴급 패치 (Emergency Fix) - 5분

**목표:** AttributeError 제거

**파일:** `backend/app/service_agent/foundation/simple_memory_service.py`

**추가할 코드:**

```python
async def load_recent_memories(
    self,
    user_id: str,
    limit: int = 5,
    relevance_filter: Optional[str] = "RELEVANT"
) -> List[Dict[str, Any]]:
    """
    최근 대화 기록 로드 (호환성용 - 빈 리스트 반환)

    Note:
        - ConversationMemory 테이블이 없으므로 빈 리스트 반환
        - 향후 chat_messages 기반으로 구현 예정
    """
    logger.debug(f"load_recent_memories called (returns empty): user_id={user_id}")
    return []


async def save_conversation(
    self,
    user_id: str,
    query: str,
    response_summary: str,
    relevance: str,
    session_id: Optional[str] = None,
    intent_detected: Optional[str] = None,
    entities_mentioned: Optional[Dict[str, Any]] = None,
    conversation_metadata: Optional[Dict[str, Any]] = None
) -> bool:
    """
    대화 저장 (호환성용 - no-op)

    Note:
        - ConversationMemory 테이블이 없으므로 저장 안됨
        - chat_messages에 자동으로 저장되므로 추가 작업 불필요
    """
    logger.debug(
        f"save_conversation called (no-op): user_id={user_id}, session_id={session_id}"
    )
    return True
```

**위치:** Line 173 다음 (기존 호환성 메서드들 아래)

---

### Step 2: 기능 구현 (Feature Implementation) - 1시간

**목표:** chat_messages 기반 실제 Long-term Memory 구현

**파일:** 동일 (`simple_memory_service.py`)

**구현 내용:**
1. `load_recent_memories`: ChatSession + ChatMessage 조인하여 사용자별 최근 대화 조회
2. `save_conversation`: chat_messages에 메타데이터 추가 (JSON 컬럼 활용)
3. 테스트 코드 작성

**상세 구현:** (위 Option 3 참고)

---

### Step 3: 테스트 (Testing) - 30분

**테스트 시나리오:**

1. **AttributeError 해결 확인**
   ```bash
   # 백엔드 재시작 후 쿼리 전송
   # 로그에서 "Failed to save Long-term Memory" 오류 없는지 확인
   ```

2. **load_recent_memories 동작 확인**
   ```python
   # 수동 테스트
   async with get_async_db() as db:
       service = LongTermMemoryService(db)
       memories = await service.load_recent_memories(user_id=1, limit=5)
       print(memories)
   ```

3. **save_conversation 동작 확인**
   ```python
   # 통합 테스트 (team_supervisor 실행)
   # 로그에서 "Saved conversation to Long-term Memory" 확인
   ```

---

### Step 4: 모니터링 및 검증 (Monitoring) - 지속

**모니터링 포인트:**

1. **에러 로그 확인**
   ```bash
   # 24시간 모니터링
   grep "Failed to save Long-term Memory" backend/logs/app.log
   # 결과: 빈 출력 (오류 없음)
   ```

2. **기능 검증**
   - 사용자 대화 컨텍스트 활용 여부
   - 개인화 기능 작동 여부

3. **성능 측정**
   - Long-term Memory 로딩 시간 (< 100ms 목표)
   - 저장 시간 (< 50ms 목표)

---

## 📊 예상 결과 (Expected Outcome)

### 즉시 효과 (Immediate)
- ✅ AttributeError 완전 제거
- ✅ 깨끗한 로그 (에러 메시지 없음)
- ✅ 코드 안정성 향상

### 단기 효과 (1-2주)
- ✅ Long-term Memory 기능 부분 복구 (chat_messages 기반)
- ✅ 사용자 대화 컨텍스트 일부 활용 가능
- ✅ 개인화 기능 초기 구현

### 장기 효과 (1개월+)
- ✅ 대화 품질 향상 (컨텍스트 활용)
- ✅ 사용자 선호도 학습
- ✅ 데이터 기반 인사이트 수집

---

## ⚠️ 리스크 및 주의사항 (Risks & Considerations)

### 1. chat_messages 테이블 구조

**현재 구조:**
```sql
CREATE TABLE chat_messages (
    id UUID PRIMARY KEY,
    session_id VARCHAR NOT NULL,
    role VARCHAR NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP,
    -- user_id 컬럼 없음 ⚠️
);
```

**문제점:**
- user_id가 없어서 사용자별 직접 조회 불가능
- chat_sessions를 통해 간접 조회 필요 (JOIN 필요)

**해결 방안:**
- chat_sessions.user_id 활용 (세션 → 메시지 조회)
- 필요시 chat_messages에 user_id 컬럼 추가 (마이그레이션)

---

### 2. 메타데이터 저장 제한

**SimpleMemoryService의 제약:**
- `conversation_metadata`, `entities_mentioned` 등이 저장 안됨
- chat_messages는 단순 대화 내용만 저장

**해결 방안:**
- chat_messages에 JSON 컬럼 추가 (metadata)
- 또는 별도 테이블 생성 (conversation_metadata)

---

### 3. 성능 고려사항

**잠재적 병목:**
- 사용자별 최근 세션 조회 시 JOIN 연산
- 대량 메시지 조회 시 성능 저하

**최적화 방안:**
- 인덱스 추가: `chat_sessions.user_id`, `chat_messages.session_id`
- 캐싱 도입 (Redis)
- 조회 limit 제한 (기본 5개)

---

## 📚 참고 자료 (References)

### 관련 파일
1. `backend/app/service_agent/supervisor/team_supervisor.py` (line 211, 855)
2. `backend/app/service_agent/foundation/simple_memory_service.py`
3. `backend/app/service_agent/foundation/old/memory_service.py` (참고용)
4. `backend/app/models/chat.py` (ChatSession, ChatMessage)

### 관련 이슈
- `reports/long_term_memory/Fix_Plan_Chat_Message_Persistence_251016.md`

### 로그 파일
- `backend/logs/app.log` (line 9112, 9192, ... 10-16 ~ 10-19)

---

## ✅ 체크리스트 (Checklist)

### 긴급 패치 (Step 1)
- [ ] `load_recent_memories` 메서드 추가
- [ ] `save_conversation` 메서드 추가
- [ ] 타입 힌트 및 docstring 작성
- [ ] 로컬 테스트 (import 오류 없는지 확인)
- [ ] 커밋 및 배포

### 기능 구현 (Step 2)
- [ ] ChatSession 조인 로직 구현
- [ ] chat_messages 기반 메모리 로딩
- [ ] 메타데이터 저장 방안 결정
- [ ] 단위 테스트 작성
- [ ] 통합 테스트 실행

### 테스트 및 검증 (Step 3)
- [ ] AttributeError 해결 확인
- [ ] 로그 모니터링 (24시간)
- [ ] 기능 동작 확인 (사용자 시나리오)
- [ ] 성능 측정 (로딩/저장 시간)

### 문서화
- [x] 이슈 보고서 작성
- [ ] 수정 내역 문서화
- [ ] API 문서 업데이트 (필요시)
- [ ] 팀 공유

---

## 📅 일정 (Timeline)

| 단계 | 예상 시간 | 담당자 | 완료 여부 |
|------|----------|--------|----------|
| Step 1: 긴급 패치 | 5분 | - | ⏳ |
| Step 2: 기능 구현 | 1시간 | - | ⏳ |
| Step 3: 테스트 | 30분 | - | ⏳ |
| Step 4: 모니터링 | 지속 | - | ⏳ |

**총 예상 시간:** 1.5 ~ 2시간

**목표 완료일:** 2025-10-19 (오늘)

---

## 📞 연락처 (Contact)

**이슈 담당자:** -

**관련 팀:** Backend Team, AI Team

**우선순위:** High

**상태:** 🔴 진행 중

---

**작성일:** 2025-10-19
**작성자:** Claude Code
**문서 버전:** 1.0
