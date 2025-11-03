# Session vs Long-term Memory 관계 설명

**Version**: 1.0
**Date**: 2025-10-14
**Purpose**: sessions 테이블과 Long-term Memory의 역할과 관계 명확화

---

## 1. Executive Summary

### 핵심 질문
> **"지금 sessions 테이블이 있는데, 이것과 Long-term Memory는 어떤 관계인가?"**

### 짧은 답변
**sessions는 "단기 기억", Long-term Memory는 "장기 기억"입니다.**

- **sessions**: WebSocket 연결 중에만 유지 (24시간 TTL, 일회성)
- **Long-term Memory**: 사용자별 영구 저장 (과거 대화 기록, 선호도)

**둘은 협력 관계**입니다:
1. sessions가 **현재 대화**를 관리
2. sessions에서 **user_id를 추출**
3. Long-term Memory가 **과거 대화**를 로드
4. 두 정보를 합쳐서 **맥락 있는 응답** 제공

---

## 2. 현재 시스템: sessions 테이블

### 2.1 sessions의 역할 (단기 기억)

```sql
-- 현재 sessions 테이블 구조
CREATE TABLE sessions (
    session_id VARCHAR(100) PRIMARY KEY,     -- "session-uuid-1234"
    user_id VARCHAR(100),                    -- "123" (사용자 ID)
    metadata TEXT,                           -- 세션 메타데이터
    created_at TIMESTAMP WITH TIME ZONE,     -- 생성 시각
    expires_at TIMESTAMP WITH TIME ZONE,     -- 만료 시각 (24시간 후)
    last_activity TIMESTAMP WITH TIME ZONE,  -- 마지막 활동
    request_count INTEGER                    -- 요청 횟수
);
```

### 2.2 sessions의 생명주기

```
사용자가 채팅 시작
    ↓
POST /api/v1/chat/start (user_id=123)
    ↓
SessionManager.create_session(user_id=123)
    ↓
sessions 테이블에 저장
    session_id: "session-abc123"
    user_id: 123
    created_at: 2025-10-14 10:00:00
    expires_at: 2025-10-15 10:00:00  ← 24시간 후
    ↓
WebSocket 연결: ws://host/ws/session-abc123
    ↓ 대화 진행 (실시간)
    ↓
24시간 후 또는 로그아웃
    ↓
sessions 테이블에서 삭제 ← 단기 기억 소멸!
```

**특징**:
- ✅ **일시적**: 24시간 TTL (Time To Live)
- ✅ **연결 추적**: WebSocket 상태 관리
- ✅ **user_id 보관**: 누가 접속했는지 기록
- ❌ **대화 내용 없음**: 메시지는 `chat_messages` 테이블에 저장
- ❌ **만료 시 삭제**: 과거 세션은 자동 정리

### 2.3 sessions로 할 수 없는 것

```python
# 불가능: 과거 대화 기록 조회
sessions = await get_all_sessions_for_user(user_id=123)
# → ❌ 24시간 지난 세션은 삭제됨!

# 불가능: 사용자 선호도 추적
preferences = await get_user_preferences(user_id=123)
# → ❌ sessions는 선호도를 저장하지 않음!

# 불가능: 여러 대화의 맥락 이해
past_conversations = await load_recent_conversations(user_id=123, limit=5)
# → ❌ sessions는 현재 세션만 관리!
```

---

## 3. Long-term Memory (구현 예정)

### 3.1 Long-term Memory의 역할 (장기 기억)

```sql
-- Long-term Memory 테이블들 (Phase 5 예정)

-- 1. 대화 기록 (영구 저장)
CREATE TABLE conversation_memories (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,                -- users.id (FK)
    session_id VARCHAR(100),                 -- 원본 세션 ID (참조용)
    conversation_summary TEXT,               -- 대화 요약
    user_query TEXT,                         -- 사용자 질문
    assistant_response TEXT,                 -- AI 응답
    intent_type VARCHAR(50),                 -- 의도 분류
    teams_used JSONB,                        -- 사용된 팀
    entities_mentioned JSONB,                -- 언급된 엔티티
    created_at TIMESTAMP WITH TIME ZONE,     -- 생성 시각

    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- 2. 사용자 선호도 (축적된 패턴)
CREATE TABLE user_preferences (
    id SERIAL PRIMARY KEY,
    user_id INTEGER UNIQUE NOT NULL,         -- users.id (FK)
    preferred_regions JSONB,                 -- ["강남구", "서초구"]
    preferred_property_types JSONB,          -- ["아파트", "오피스텔"]
    price_range JSONB,                       -- {"min": 300000000, "max": 500000000}
    area_range JSONB,                        -- {"min": 60, "max": 100}
    search_history JSONB,                    -- 검색 패턴
    interaction_count INTEGER,               -- 상호작용 횟수
    last_updated TIMESTAMP WITH TIME ZONE,

    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- 3. 엔티티 추적 (언급된 매물/지역)
CREATE TABLE entity_memories (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,                -- users.id (FK)
    entity_type VARCHAR(50),                 -- "real_estate", "region", "agent"
    entity_id VARCHAR(100),                  -- 엔티티 ID
    entity_name VARCHAR(200),                -- 엔티티 이름
    last_mentioned TIMESTAMP WITH TIME ZONE, -- 마지막 언급 시각
    mention_count INTEGER,                   -- 언급 횟수
    context TEXT,                            -- 언급 맥락

    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

### 3.2 Long-term Memory의 생명주기

```
사용자가 대화 시작 (user_id=123)
    ↓
sessions 테이블에서 user_id 추출
    ↓
LongTermMemoryService.load_recent_memories(user_id=123, limit=5)
    ↓
conversation_memories에서 최근 5개 대화 로드
    ↓ 예시 데이터:
    [
        {
            "created_at": "2025-10-10 14:30:00",
            "query": "강남구 아파트 3억~5억 추천해줘",
            "intent": "search_real_estate",
            "teams_used": ["SearchTeam", "RecommendationTeam"]
        },
        {
            "created_at": "2025-10-12 09:15:00",
            "query": "이전에 본 아파트 재계약 가능한가?",
            "intent": "contract_inquiry"
        }
    ]
    ↓
user_preferences에서 선호도 로드
    ↓ 예시 데이터:
    {
        "preferred_regions": ["강남구", "서초구"],
        "price_range": {"min": 300000000, "max": 500000000}
    }
    ↓
MainSupervisorState에 로드
    state["user_id"] = 123
    state["loaded_memories"] = [...]
    state["user_preferences"] = {...}
    ↓
Planning Node에서 활용
    - "사용자가 이전에 강남구 아파트를 찾았네요"
    - "3억~5억 가격대를 선호하는 것 같습니다"
    - "재계약 관련 질문을 한 적이 있네요"
    ↓
대화 완료 후 저장
    ↓
LongTermMemoryService.save_conversation(user_id=123, ...)
    ↓
conversation_memories에 영구 저장 ← 장기 기억 축적!
```

**특징**:
- ✅ **영구적**: 삭제하지 않는 한 계속 유지
- ✅ **사용자별 추적**: user_id로 모든 대화 연결
- ✅ **맥락 제공**: 과거 대화를 현재 대화에 활용
- ✅ **선호도 학습**: 반복 패턴 감지
- ✅ **엔티티 추적**: 특정 매물/지역 재언급 감지

---

## 4. sessions vs Long-term Memory 비교

### 4.1 핵심 차이점

| 항목 | **sessions** (단기) | **Long-term Memory** (장기) |
|------|---------------------|------------------------------|
| **목적** | WebSocket 연결 관리 | 과거 대화 기록 저장 |
| **생명주기** | 24시간 TTL | 영구 (사용자가 삭제할 때까지) |
| **데이터** | session_id, user_id, 메타데이터 | 대화 내용, 선호도, 엔티티 |
| **자동 삭제** | ✅ (24시간 후) | ❌ (수동 삭제만) |
| **사용 시점** | WebSocket 연결 중 | 대화 시작 시 + 종료 시 |
| **user_id 의존** | 선택적 (익명 가능) | 필수 (user_id 없으면 저장 안 함) |
| **테이블 수** | 1개 | 3개 |
| **저장 내용** | 연결 상태 | 대화 요약, 선호도, 엔티티 |

### 4.2 비유로 이해하기

#### 예시: 카페에서 손님 응대

**sessions (단기 기억)**:
- 손님이 **지금** 앉아 있는 테이블 번호: `session-abc123`
- 손님이 누구인지 확인: `user_id=123` (멤버십 카드)
- 주문 진행 상태: `request_count=5`
- 퇴장 시 테이블 정리: **24시간 후 자동 삭제**

**Long-term Memory (장기 기억)**:
- 손님이 **과거에** 주문한 메뉴: "아메리카노 3번, 라떼 2번"
- 손님 선호도: "설탕 없이, 얼음 많이"
- 단골 손님 정보: "매주 화요일 오전 10시에 방문"
- **영구 저장**: 다음에 방문해도 기억함

---

## 5. 둘의 협력 관계

### 5.1 데이터 흐름

```
[Frontend]
    ↓ POST /chat/start (user_id=123)
    ↓
[SessionManager]
    → sessions 테이블에 저장
    session_id: "session-abc123"
    user_id: 123  ← 중요: user_id를 저장!
    ↓
[WebSocket Connection]
    ws://host/ws/session-abc123
    ↓
[chat_api.websocket_chat()]
    session_info = await session_mgr.get_session(session_id)
    user_id = session_info["user_id"]  ← sessions에서 user_id 추출!
    ↓
[TeamBasedSupervisor.process_query_streaming()]
    state["user_id"] = user_id  ← State에 user_id 전달
    ↓
[planning_node]
    if state["user_id"]:
        memories = await LongTermMemoryService.load_recent_memories(
            user_id=state["user_id"],  ← sessions에서 받은 user_id 사용!
            limit=5
        )
        state["loaded_memories"] = memories  ← 장기 기억 로드!
    ↓
[대화 진행]
    - 단기 기억: 현재 세션의 실시간 대화
    - 장기 기억: 과거 5개 대화 맥락
    → 두 기억을 합쳐서 응답 생성!
    ↓
[response_node (대화 종료 시)]
    await LongTermMemoryService.save_conversation(
        user_id=state["user_id"],  ← sessions에서 받은 user_id 사용!
        query=state["user_query"],
        response=state["final_response"]
    )
    → conversation_memories에 영구 저장!
```

### 5.2 핵심 포인트

**sessions의 역할**:
1. WebSocket 연결 상태 추적
2. **user_id를 Long-term Memory에 전달** ← 가장 중요!
3. 세션 만료 관리

**Long-term Memory의 역할**:
1. **sessions에서 받은 user_id로 과거 대화 로드**
2. 현재 대화에 맥락 제공
3. 대화 종료 후 영구 저장

**협력 지점**:
```python
# sessions → Long-term Memory 연결고리
session_info = await session_mgr.get_session(session_id)
user_id = session_info["user_id"]  # ← sessions가 제공

memories = await LongTermMemoryService.load_recent_memories(
    user_id=user_id  # ← Long-term Memory가 사용
)
```

---

## 6. 실제 사용 예시

### 6.1 시나리오: 재방문 사용자

#### Day 1 (2025-10-10)
```
사용자 접속 (user_id=123)
    ↓
sessions 생성
    session_id: "session-001"
    user_id: 123
    created_at: 2025-10-10 14:00
    expires_at: 2025-10-11 14:00  ← 24시간 후 만료
    ↓
대화: "강남구 아파트 3억~5억 추천해줘"
    ↓
응답 생성 및 Long-term Memory 저장
    conversation_memories에 저장:
    - user_id: 123
    - query: "강남구 아파트..."
    - intent: "search_real_estate"
    - created_at: 2025-10-10 14:00
    ↓
사용자 로그아웃
    ↓
24시간 후: sessions 테이블에서 "session-001" 삭제 ← 단기 기억 소멸
    BUT conversation_memories는 유지! ← 장기 기억 보존
```

#### Day 2 (2025-10-12)
```
동일 사용자 재접속 (user_id=123)
    ↓
sessions 생성 (새로운 세션!)
    session_id: "session-002"  ← 새 세션 ID
    user_id: 123  ← 동일한 user_id
    created_at: 2025-10-12 09:00
    expires_at: 2025-10-13 09:00
    ↓
planning_node에서 Long-term Memory 로드
    memories = load_recent_memories(user_id=123, limit=5)
    → 2025-10-10 대화 기록 로드! ← 2일 전 대화 기억함!
    ↓
대화: "이전에 본 아파트 재계약 가능한가?"
    ↓
AI 응답 (맥락 있는 응답!)
    "네, 2일 전에 문의하신 강남구 아파트 3억~5억 매물 중에서
     재계약 가능한 매물은 5개가 있습니다..."
    ← Long-term Memory 덕분에 과거 대화를 기억!
```

### 6.2 sessions 없이는 불가능한 이유

```python
# 잘못된 접근 (sessions 없이 직접 user_id 전달)
# ❌ 문제: WebSocket 연결과 user_id 연결이 끊어짐

websocket_chat(websocket, user_id):  # ← 직접 user_id 전달?
    # 문제 1: WebSocket 연결 상태 추적 불가
    # 문제 2: 만료 관리 불가
    # 문제 3: 동일 사용자의 여러 연결 구분 불가

# 올바른 접근 (sessions 활용)
# ✅ 해결: sessions가 연결과 user_id를 함께 관리

websocket_chat(websocket, session_id):  # ← session_id로 연결
    session_info = await get_session(session_id)
    user_id = session_info["user_id"]  # ← sessions에서 user_id 추출

    # 장점 1: WebSocket 연결 상태 추적 가능 (session_id)
    # 장점 2: 만료 관리 가능 (expires_at)
    # 장점 3: 동일 사용자의 여러 연결 구분 (session_id가 다름)
    # 장점 4: user_id로 Long-term Memory 로드 가능
```

---

## 7. 타입 불일치 문제의 중요성

### 7.1 현재 문제

```sql
-- sessions 테이블
user_id VARCHAR(100)  ← 문자열

-- users 테이블
id INTEGER  ← 정수

-- chat_sessions 테이블
user_id INTEGER  ← 정수

-- conversation_memories 테이블 (예정)
user_id INTEGER  ← 정수 (users.id FK)
```

### 7.2 문제가 발생하는 지점

```python
# Long-term Memory 로드 시
session_info = await session_mgr.get_session(session_id)
user_id = session_info["user_id"]  # "123" (문자열)

memories = await LongTermMemoryService.load_recent_memories(
    user_id=user_id  # "123" (문자열)
)

# SQL 쿼리
SELECT * FROM conversation_memories
WHERE user_id = '123'  -- VARCHAR vs INTEGER 비교!
                       -- PostgreSQL은 자동 변환하지만 비효율적
```

**문제점**:
- ❌ 타입 불일치로 인한 성능 저하
- ❌ Foreign Key 관계 설정 불가
- ❌ 인덱스 최적화 불가
- ❌ 타입 변환 오류 가능성

**해결책**:
```sql
-- sessions.user_id를 INTEGER로 변경
ALTER TABLE sessions ALTER COLUMN user_id TYPE INTEGER;

-- 이제 모든 테이블이 동일 타입
sessions.user_id         INTEGER ✅
users.id                 INTEGER ✅
chat_sessions.user_id    INTEGER ✅
conversation_memories.user_id INTEGER ✅
```

---

## 8. 구현 체크리스트

### Phase 1: sessions 타입 수정 (선행 작업)
- [ ] `backend/app/models/session.py` Line 26 수정 (String → Integer)
- [ ] `backend/migrations/create_sessions_table.sql` Line 8 수정 (VARCHAR → INTEGER)
- [ ] 기존 sessions 테이블 삭제 및 재생성
- [ ] SessionManager 테스트 (user_id가 Integer로 저장되는지 확인)

### Phase 2: Long-term Memory 모델 생성
- [ ] `backend/app/models/memory.py` 생성
- [ ] ConversationMemory 모델 (user_id INTEGER FK to users.id)
- [ ] UserPreference 모델 (user_id INTEGER FK to users.id)
- [ ] EntityMemory 모델 (user_id INTEGER FK to users.id)

### Phase 3: Memory Service 구현
- [ ] `backend/app/services/long_term_memory_service.py` 생성
- [ ] `load_recent_memories(user_id: int, limit: int)` 메서드
- [ ] `save_conversation(user_id: int, ...)` 메서드
- [ ] `get_user_preferences(user_id: int)` 메서드

### Phase 4: sessions → Long-term Memory 연결
- [ ] `chat_api.py`: session에서 user_id 추출
- [ ] `separated_states.py`: MainSupervisorState에 memory 필드 추가
- [ ] `team_supervisor.py:planning_node()`: Memory 로드
- [ ] `team_supervisor.py:response_node()`: Memory 저장

---

## 9. 핵심 요약

### sessions (단기 기억)
```
역할: WebSocket 연결 관리
생명: 24시간 TTL
데이터: session_id, user_id, 메타데이터
기능: user_id를 Long-term Memory에 전달
```

### Long-term Memory (장기 기억)
```
역할: 과거 대화 기록 저장
생명: 영구 (삭제 전까지)
데이터: 대화 내용, 선호도, 엔티티
기능: sessions에서 받은 user_id로 과거 대화 로드
```

### 협력 관계
```
sessions → user_id 제공 → Long-term Memory
         ↓
   현재 대화 관리
         ↓
   Long-term Memory → 과거 대화 맥락 제공
         ↓
   맥락 있는 AI 응답 생성
```

**결론**: sessions와 Long-term Memory는 **협력 관계**이며, sessions가 제공하는 **user_id가 연결고리**입니다!

---

**Document End**
