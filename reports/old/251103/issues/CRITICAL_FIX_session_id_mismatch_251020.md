# 🚨 CRITICAL: session_id 불일치 수정 가이드

**작성일**: 2025-10-20
**우선순위**: 최우선 (Phase 1 시작 전 필수)
**영향도**: Memory Service 전체 동작 실패

---

## 문제 요약

`team_supervisor.py`와 `simple_memory_service.py` 사이에 **session_id 파라미터 혼동**이 발생하고 있습니다.

### 현재 상황

**2가지 다른 session_id가 혼용됨**:

1. **HTTP/WebSocket session_id**
   - 타입: `str` (예: `"ws_12345"`)
   - 용도: HTTP 요청 또는 WebSocket 연결 추적
   - 위치: `state["session_id"]`

2. **Chat Database session_id**
   - 타입: `str` (예: `"session-9b050480..."`)
   - 용도: ChatSession 테이블의 session_id (FK)
   - 위치: `state["chat_session_id"]`

### 문제 코드

#### team_supervisor.py:211-228 (planning_node)

```python
# ❌ 문제: load_recent_memories에 session_id를 전달하지 않음!
loaded_memories = await memory_service.load_recent_memories(
    user_id=user_id,
    limit=settings.MEMORY_LOAD_LIMIT,
    relevance_filter="RELEVANT"
    # session_id 누락!
)
```

#### team_supervisor.py:222-239 (generate_response_node)

```python
# ✅ 정상: chat_session_id를 추출해서 전달
chat_session_id = state.get("chat_session_id")

await memory_service.save_conversation(
    user_id=user_id,
    query=state.get("query", ""),
    response_summary=response_summary,
    relevance="RELEVANT",
    session_id=chat_session_id,  # ✅ 올바른 session_id
    intent_detected=intent_type,
    entities_mentioned=analyzed_intent.get("entities", {}),
    ...
)
```

#### simple_memory_service.py (Phase 1 구현)

```python
async def save_conversation(
    self,
    user_id: int,
    query: str,
    response_summary: str,
    relevance: str = "RELEVANT",
    session_id: Optional[str] = None,  # ← Chat DB의 session_id 기대
    ...
) -> bool:
    if not session_id:  # ❌ 없으면 실패
        logger.warning("save_conversation called without session_id")
        return False  # 저장 안 됨!

    # ChatSession 조회
    query_obj = select(ChatSession).filter(
        ChatSession.session_id == session_id  # ← chat_session_id로 조회
    )
```

---

## 🔧 해결책

### Option A: team_supervisor.py 수정 (권장)

**파일**: `backend/app/service_agent/supervisor/team_supervisor.py`

#### 수정 1: planning_node (Line 211-228)

```python
# Before (❌ 불완전)
loaded_memories = await memory_service.load_recent_memories(
    user_id=user_id,
    limit=settings.MEMORY_LOAD_LIMIT,
    relevance_filter="RELEVANT"
)

# After (✅ 완전)
loaded_memories = await memory_service.load_recent_memories(
    user_id=user_id,
    limit=settings.MEMORY_LOAD_LIMIT,
    relevance_filter="RELEVANT",
    session_id=state.get("chat_session_id")  # ← 추가
)
```

#### 수정 2: simple_memory_service.py도 업데이트 필요

**파일**: `backend/app/service_agent/foundation/simple_memory_service.py`

```python
async def load_recent_memories(
    self,
    user_id: int,
    limit: int = 5,
    relevance_filter: Optional[str] = "RELEVANT",
    session_id: Optional[str] = None  # ← 추가 (선택적)
) -> List[Dict[str, Any]]:
    """
    최근 대화 기억 로드

    Args:
        user_id: 사용자 ID
        limit: 로드할 개수
        relevance_filter: 관련성 필터
        session_id: 현재 세션 ID (선택, 현재 세션 제외용)

    Returns:
        메모리 리스트
    """
    try:
        query = select(ChatSession).filter(
            ChatSession.user_id == user_id,
            ChatSession.is_active == True
        )

        # ✅ 현재 세션 제외 (자기 자신의 메모리는 아직 저장 안 됨)
        if session_id:
            query = query.filter(ChatSession.session_id != session_id)

        query = query.order_by(ChatSession.updated_at.desc()).limit(3)

        # ... 나머지 코드 동일
```

### Option B: 파라미터 이름 명확화 (더 근본적)

**모든 파일에서 명확한 이름 사용**:

```python
# team_supervisor.py
await memory_service.save_conversation(
    user_id=user_id,
    chat_session_id=state.get("chat_session_id"),  # ← 명확한 이름
    ...
)

# simple_memory_service.py
async def save_conversation(
    self,
    user_id: int,
    query: str,
    response_summary: str,
    chat_session_id: Optional[str] = None,  # ← 명확한 이름
    ...
):
    if not chat_session_id:
        logger.warning("save_conversation called without chat_session_id")
        return False

    query_obj = select(ChatSession).filter(
        ChatSession.session_id == chat_session_id
    )
```

---

## 📋 수정 체크리스트

### 즉시 수정 (Phase 1 시작 전)

```
[ ] team_supervisor.py:211-228 수정 (load_recent_memories에 session_id 추가)
[ ] simple_memory_service.py:load_recent_memories 시그니처 수정
[ ] simple_memory_service.py:load_recent_memories 로직 업데이트 (현재 세션 제외)
[ ] FINAL_IMPLEMENTATION_GUIDE_251020.md 업데이트
```

### 선택 사항 (더 나은 구조)

```
[ ] 파라미터 이름을 chat_session_id로 통일 (Breaking change)
[ ] Type hints 추가 (session_id: str vs chat_session_id: str)
[ ] Docstring 명확화
```

---

## 🔍 검증 방법

### 1. 로그 확인

```python
# team_supervisor.py에 로그 추가
logger.info(f"[Memory] Loading with session_id={state.get('chat_session_id')}")
logger.info(f"[Memory] Saving with session_id={chat_session_id}")

# simple_memory_service.py에 로그 추가
logger.info(f"[Memory] save_conversation called with session_id={session_id}")
logger.info(f"[Memory] load_recent_memories called with session_id={session_id}")
```

### 2. 테스트 코드

```python
# tests/test_session_id_consistency.py
import pytest
from app.service_agent.supervisor.team_supervisor import TeamBasedSupervisor

@pytest.mark.asyncio
async def test_session_id_consistency():
    """session_id vs chat_session_id 일관성 테스트"""
    supervisor = TeamBasedSupervisor()

    result = await supervisor.process_query_streaming(
        query="강남역 원룸 추천해줘",
        session_id="ws_12345",  # WebSocket session
        chat_session_id="session-9b050480...",  # Chat DB session
        user_id=1
    )

    # Memory 로딩/저장이 성공했는지 확인
    assert result.get("loaded_memories") is not None
    # (save_conversation은 로그로만 확인 가능)
```

---

## 💡 권장 수정 순서

### Step 1: 최소 수정 (즉시 적용 가능)

1. `team_supervisor.py:211-228` 수정
   ```python
   session_id=state.get("chat_session_id")  # 추가
   ```

2. `simple_memory_service.py:load_recent_memories` 시그니처 수정
   ```python
   session_id: Optional[str] = None  # 파라미터 추가
   ```

3. `simple_memory_service.py:load_recent_memories` 로직 수정
   ```python
   if session_id:
       query = query.filter(ChatSession.session_id != session_id)
   ```

### Step 2: FINAL_IMPLEMENTATION_GUIDE 업데이트

**파일**: `reports/issues/FINAL_IMPLEMENTATION_GUIDE_251020.md`

**Line 133-140 부분 수정**:

```python
# Phase 1 수정 반영
async def load_recent_memories(
    self,
    user_id: int,
    limit: int = 5,
    relevance_filter: Optional[str] = "RELEVANT",
    session_id: Optional[str] = None  # ✅ 추가
) -> List[Dict[str, Any]]:
```

**Line 69-76 부분 수정**:

```python
query = select(ChatSession).filter(
    ChatSession.user_id == user_id,
    ChatSession.is_active == True
)

# ✅ 현재 세션 제외
if session_id:
    query = query.filter(ChatSession.session_id != session_id)

query = query.order_by(ChatSession.updated_at.desc()).limit(3)
```

### Step 3: team_supervisor.py 수정

**파일**: `backend/app/service_agent/supervisor/team_supervisor.py`

**Line 211 수정**:

```python
# Before
loaded_memories = await memory_service.load_recent_memories(
    user_id=user_id,
    limit=settings.MEMORY_LOAD_LIMIT,
    relevance_filter="RELEVANT"
)

# After
loaded_memories = await memory_service.load_recent_memories(
    user_id=user_id,
    limit=settings.MEMORY_LOAD_LIMIT,
    relevance_filter="RELEVANT",
    session_id=state.get("chat_session_id")  # ✅ 추가
)
```

---

## 🎯 예상 결과

### Before (현재 상태)

```
[TeamSupervisor] Loading Long-term Memory for user 1
[Memory] load_recent_memories called (no session_id)
[Memory] Loaded 5 memories from last 3 sessions
  - Including current session's incomplete memories! ❌
```

### After (수정 후)

```
[TeamSupervisor] Loading Long-term Memory for user 1
[Memory] load_recent_memories called with session_id=session-9b050480...
[Memory] Excluding current session
[Memory] Loaded 5 memories from last 3 sessions (excluding current)
  - Only completed past conversations ✅
```

---

## 📌 중요 노트

1. **현재 세션 제외가 중요한 이유**:
   - planning_node에서 로드할 때는 아직 현재 대화가 저장 안 됨
   - 현재 세션의 session_metadata는 비어있거나 불완전함
   - 과거 완료된 대화만 로드해야 정확한 컨텍스트 제공

2. **chat_session_id는 언제 생성되나?**:
   - Frontend에서 새 채팅 시작 시 생성
   - 또는 Backend API에서 자동 생성
   - `state["chat_session_id"]`에 저장됨

3. **Null 체크 필요**:
   ```python
   chat_session_id = state.get("chat_session_id")
   if not chat_session_id:
       logger.warning("No chat_session_id in state, memory disabled")
       return  # Memory 기능 스킵
   ```

---

**작성일**: 2025-10-20
**우선순위**: P0 (최우선)
**상태**: 수정 필요

