# Zombie Code Detection 리포트 - Phase 0.3

**생성일시:** 2025-10-20
**목적:** 사용되지 않는 코드, old 디렉토리, stub 메서드 등 Zombie Code 탐지

---

## 1. old/ 디렉토리 Zombie Code

### 발견된 old 디렉토리 파일 (5개)

1. **backend/app/models/old/session.py**
   - 상태: Zombie (사용 안 됨)
   - 이유: ChatSession 모델이 backend/app/models/chat.py로 이동
   - 액션: 삭제 가능

2. **backend/app/models/old/unified_schema.py**
   - 상태: Zombie (사용 안 됨)
   - 이유: 통합 스키마 실험용 파일
   - 액션: 삭제 가능

3. **backend/app/models/old/memory.py**
   - 상태: Zombie (사용 안 됨)
   - 이유: ConversationMemory, EntityMemory, UserPreference 모델
   - 현황: 해당 테이블들이 DB에 존재하지 않음 (Phase 0.1 Step 3 확인)
   - 액션: Phase 2에서 참고 후 삭제 또는 재활용

4. **backend/app/api/old/session_manager.py**
   - 상태: Zombie (사용 안 됨)
   - 이유: 세션 관리 로직이 다른 곳으로 이동
   - 액션: 삭제 가능

5. **backend/app/service_agent/foundation/old/memory_service.py**
   - 상태: Zombie (사용 안 됨)
   - 이유: SimpleMemoryService로 대체됨
   - 액션: Phase 2에서 참고 후 삭제

---

## 2. SimpleMemoryService Stub 메서드 분석

**파일:** `backend/app/service_agent/foundation/simple_memory_service.py`

### 실제 구현된 메서드 (2개)

✅ **load_recent_messages** (Lines 34-67)
- 상태: ✅ 완전히 구현됨
- 기능: chat_messages에서 최근 메시지 로드
- 사용: get_conversation_history에서 호출됨

✅ **get_conversation_history** (Lines 69-93)
- 상태: ✅ 완전히 구현됨
- 기능: 대화 히스토리를 텍스트로 변환
- 사용: team_supervisor.py에서 호출 가능

### 호환성 Stub 메서드 (6개) - Zombie 또는 No-Op

❌ **save_conversation_memory** (Lines 97-120)
- 상태: ⚠️ No-Op (아무것도 안 함)
- 코멘트: "호환성용 - 실제로는 아무것도 안함"
- 반환: 항상 True
- 문제: 호출되지만 실제로 저장되지 않음
- 액션: Phase 1에서 실제 구현 필요

❌ **get_recent_memories** (Lines 122-138)
- 상태: ⚠️ 빈 리스트 반환
- 코멘트: "호환성용 - 빈 리스트 반환"
- 반환: [] (항상 비어있음)
- 문제: team_supervisor.py에서 호출되지만 항상 빈 결과
- 액션: Phase 1에서 실제 구현 필요

❌ **update_user_preference** (Lines 140-156)
- 상태: ⚠️ No-Op
- 코멘트: "UserPreference 테이블이 없으므로 저장 안됨"
- 반환: 항상 True
- 문제: 호출되어도 저장되지 않음
- 액션: Phase 2에서 구현 (UserPreference 테이블 생성 후)

❌ **get_user_preferences** (Lines 158-172)
- 상태: ⚠️ 빈 dict 반환
- 코멘트: "UserPreference 테이블이 없으므로 빈 dict 반환"
- 반환: {} (항상 비어있음)
- 액션: Phase 2에서 구현

❌ **save_entity_memory** (Lines 174-194)
- 상태: ⚠️ No-Op
- 코멘트: "EntityMemory 테이블이 없으므로 저장 안됨"
- 반환: 항상 True
- 액션: Phase 2에서 구현 (EntityMemory 테이블 생성 후)

❌ **get_entity_memories** (Lines 196-211)
- 상태: ⚠️ 빈 리스트 반환
- 코멘트: "EntityMemory 테이블이 없으므로 빈 리스트 반환"
- 반환: [] (항상 비어있음)
- 액션: Phase 2에서 구현

### 호환성 Alias (Line 217)
```python
LongTermMemoryService = SimpleMemoryService
```
- 상태: ✅ 유지 필요
- 이유: 기존 import 문 호환성
- 액션: 유지

---

## 3. 누락된 핵심 메서드 (Critical!)

### ⛔ **load_recent_memories** - 없음!
- 상태: ❌ **구현되지 않음**
- 호출 위치: `team_supervisor.py:211` (planning_node)
- 문제: **이것이 ROOT CAUSE ANALYSIS에서 발견한 session_id 누락 문제의 원인!**
- 현재 상황:
  ```python
  # team_supervisor.py:211-214
  loaded_memories = await memory_service.load_recent_memories(
      user_id=user_id,
      limit=settings.MEMORY_LOAD_LIMIT,
      relevance_filter="RELEVANT"
      # ❌ session_id 파라미터 없음!
  )
  ```
- 문제점:
  1. `load_recent_memories` 메서드 자체가 simple_memory_service.py에 없음
  2. `get_recent_memories`는 있지만 항상 빈 리스트 반환 (호환성 stub)
  3. team_supervisor.py는 존재하지 않는 메서드를 호출함
  4. **AttributeError 또는 빈 결과 반환으로 메모리 기능 완전 비활성화**

### ⛔ **save_conversation** - 없음!
- 상태: ❌ **구현되지 않음**
- 호출 위치: `team_supervisor.py:855` (generate_response_node 후)
- 현재 상황:
  ```python
  # team_supervisor.py:855-859 (예상)
  await memory_service.save_conversation(
      user_id=user_id,
      session_id=session_id,
      messages=[...],
      summary="..."
  )
  ```
- 문제점:
  1. `save_conversation` 메서드 자체가 simple_memory_service.py에 없음
  2. `save_conversation_memory`는 있지만 no-op (아무것도 안 함)
  3. 대화가 저장되지 않아 메모리가 축적되지 않음

---

## 4. team_supervisor.py와의 불일치

### 호출되는 메서드 vs 실제 구현

| 호출 메서드 (team_supervisor.py) | 존재 여부 | 구현 상태 | 문제 |
|----------------------------------|----------|----------|------|
| `load_recent_memories()` | ❌ 없음 | - | **Critical!** AttributeError 발생 가능 |
| `save_conversation()` | ❌ 없음 | - | **Critical!** 대화 저장 안 됨 |
| `get_recent_memories()` | ✅ 있음 | ⚠️ 빈 리스트 반환 | 동작하지만 무용 |
| `save_conversation_memory()` | ✅ 있음 | ⚠️ No-Op | 동작하지만 저장 안 됨 |

---

## 5. Import 구조 분석

### simple_memory_service.py의 Import (Lines 5-10)
```python
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.chat import ChatMessage
```

### 문제점:
1. ❌ `ChatSession` import 없음
   - load_recent_memories 구현 시 필요
   - chat_sessions.metadata 접근 시 필요

2. ❌ `flag_modified` import 없음
   - JSONB 업데이트 시 필요
   - Phase 1 구현 시 추가 필요

3. ❌ `datetime` import 없음
   - timestamp 기록 시 필요

---

## 6. Zombie Code 요약

### 즉시 삭제 가능 (4개 파일)
1. ✅ backend/app/models/old/session.py
2. ✅ backend/app/models/old/unified_schema.py
3. ✅ backend/app/api/old/session_manager.py
4. ⚠️ backend/app/service_agent/foundation/old/memory_service.py (Phase 2 참고 후)

### 참고 후 삭제 (1개 파일)
1. ⚠️ backend/app/models/old/memory.py
   - Phase 2에서 ConversationMemory, EntityMemory, UserPreference 모델 재활용 가능
   - 테이블 생성 시 참고
   - 참고 완료 후 삭제

### Stub 메서드 (6개)
1. ⚠️ save_conversation_memory - No-Op
2. ⚠️ get_recent_memories - 빈 리스트
3. ⚠️ update_user_preference - No-Op
4. ⚠️ get_user_preferences - 빈 dict
5. ⚠️ save_entity_memory - No-Op
6. ⚠️ get_entity_memories - 빈 리스트

### **CRITICAL 누락 메서드 (2개)** ⚠️⚠️⚠️
1. ❌ **load_recent_memories** - team_supervisor.py에서 호출되지만 구현 없음
2. ❌ **save_conversation** - team_supervisor.py에서 호출되지만 구현 없음

---

## 7. Phase 1에서 해야 할 작업

### 1단계: Import 추가
```python
from app.models.chat import ChatMessage, ChatSession  # ChatSession 추가
from sqlalchemy.orm import flag_modified  # JSONB 업데이트용
from datetime import datetime  # timestamp용
```

### 2단계: load_recent_memories 구현
```python
async def load_recent_memories(
    self,
    user_id: str,
    limit: int = 5,
    relevance_filter: str = "ALL",
    session_id: Optional[str] = None  # ⭐ 추가!
) -> List[Dict[str, Any]]:
    """
    최근 세션의 메모리 로드 (chat_sessions.metadata 기반)

    Args:
        user_id: 사용자 ID
        limit: 조회할 세션 개수
        relevance_filter: 필터 (현재 미사용)
        session_id: 제외할 세션 ID (현재 진행 중인 세션)

    Returns:
        메모리 리스트
    """
    try:
        query = select(ChatSession).where(
            ChatSession.user_id == user_id,
            ChatSession.session_metadata.isnot(None)
        )

        # 현재 세션 제외
        if session_id:
            query = query.where(ChatSession.session_id != session_id)

        query = query.order_by(ChatSession.updated_at.desc()).limit(limit)

        result = await self.db.execute(query)
        sessions = result.scalars().all()

        memories = []
        for session in sessions:
            metadata = session.session_metadata
            if metadata and "conversation_summary" in metadata:
                memories.append({
                    "session_id": session.session_id,
                    "summary": metadata["conversation_summary"],
                    "timestamp": session.updated_at.isoformat()
                })

        return memories

    except Exception as e:
        logger.error(f"Failed to load recent memories: {e}")
        return []
```

### 3단계: save_conversation 구현
```python
async def save_conversation(
    self,
    user_id: str,
    session_id: str,
    messages: List[dict],
    summary: str
) -> None:
    """
    대화 요약을 chat_sessions.metadata에 저장

    Args:
        user_id: 사용자 ID
        session_id: 세션 ID
        messages: 메시지 리스트
        summary: 대화 요약
    """
    try:
        # 세션 조회
        query = select(ChatSession).where(
            ChatSession.session_id == session_id,
            ChatSession.user_id == user_id
        )
        result = await self.db.execute(query)
        session = result.scalar_one_or_none()

        if not session:
            logger.warning(
                f"Session not found: session_id={session_id}, user_id={user_id}"
            )
            return

        # metadata 업데이트
        if session.session_metadata is None:
            session.session_metadata = {}

        session.session_metadata["conversation_summary"] = summary
        session.session_metadata["last_updated"] = datetime.now().isoformat()
        session.session_metadata["message_count"] = len(messages)

        # JSONB 변경 플래그 설정
        flag_modified(session, "session_metadata")

        await self.db.commit()
        logger.info(f"Conversation saved: session_id={session_id}")

    except Exception as e:
        logger.error(f"Failed to save conversation: {e}")
        await self.db.rollback()
        raise
```

### 4단계: team_supervisor.py 수정
```python
# planning_node (Line 211)
loaded_memories = await memory_service.load_recent_memories(
    user_id=user_id,
    limit=settings.MEMORY_LOAD_LIMIT,
    relevance_filter="RELEVANT",
    session_id=session_id  # ⭐ 추가!
)
```

---

## 8. Phase 0.3 완료 체크리스트

✅ old/ 디렉토리 파일 탐지 (5개)
✅ SimpleMemoryService stub 메서드 분석 (6개)
✅ **CRITICAL 누락 메서드 발견 (2개)**
✅ Import 불일치 확인 (3개)
✅ team_supervisor.py 호출 불일치 확인

**Phase 0.3 결론:**
- ⚠️ **심각한 문제 발견: load_recent_memories, save_conversation 메서드 구현 없음**
- ⚠️ team_supervisor.py에서 호출되지만 동작하지 않음
- ⚠️ 이것이 메모리 기능이 완전히 비활성화된 근본 원인

---

## 다음 단계: Phase 0.4

**Mismatch Itemization:**
- team_supervisor.py의 모든 memory_service 호출 위치 파악
- 각 호출의 기대값 vs 실제 동작 비교
- 불일치 항목 상세 문서화
