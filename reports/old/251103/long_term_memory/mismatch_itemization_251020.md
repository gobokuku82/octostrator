# Mismatch Itemization 리포트 - Phase 0.4

**생성일시:** 2025-10-20
**목적:** team_supervisor.py와 simple_memory_service.py 간 불일치 항목 상세 문서화

---

## 1. Critical Mismatch: load_recent_memories

### 호출 위치: team_supervisor.py:211-215

```python
# Long-term Memory 로딩 (조기 단계 - RELEVANT 쿼리만)
loaded_memories = await memory_service.load_recent_memories(
    user_id=user_id,
    limit=settings.MEMORY_LOAD_LIMIT,
    relevance_filter="RELEVANT"
    # ❌ session_id 파라미터 없음!
)
```

### 기대 동작
1. `user_id`의 최근 대화 기록 로드
2. `limit` 개수만큼 제한
3. `relevance_filter`로 필터링
4. **현재 진행 중인 세션 제외** ← 누락!

### 실제 동작
- **❌ AttributeError 발생 가능**
- `load_recent_memories` 메서드가 simple_memory_service.py에 없음
- 대신 `get_recent_memories`가 있지만:
  - 시그니처가 다름: `get_recent_memories(user_id, limit)`
  - 항상 빈 리스트 반환 (호환성 stub)

### 문제점
| 항목 | 기대값 | 실제값 | 영향 |
|------|--------|--------|------|
| 메서드 존재 | `load_recent_memories()` | ❌ 없음 | AttributeError |
| 파라미터 | `user_id, limit, relevance_filter, session_id` | ❌ - | 호출 불가 |
| 반환값 | `List[Dict]` (메모리 리스트) | ❌ - | 메모리 로딩 실패 |
| session_id 제외 | 현재 세션 제외 | ❌ 구현 없음 | 불완전한 데이터 로드 |

### Root Cause
- **설계 단계부터 누락됨** (ROOT_CAUSE_ANALYSIS_251020.md 참조)
- `plan_of_memory_service_error_fix_251019.md`에서도 누락
- team_supervisor.py는 존재하지 않는 메서드를 호출

---

## 2. Critical Mismatch: save_conversation

### 호출 위치: team_supervisor.py:656-669

```python
# 대화 저장
await memory_service.save_conversation(
    user_id=user_id,
    query=state.get("query", ""),
    response_summary=response_summary,
    relevance="RELEVANT",
    session_id=chat_session_id,  # ✅ chat_session_id 사용
    intent_detected=intent_type,
    entities_mentioned=analyzed_intent.get("entities", {}),
    conversation_metadata={
        "teams_used": state.get("active_teams", []),
        "response_time": state.get("total_execution_time"),
        "confidence": confidence
    }
)
```

### 기대 동작
1. 대화 요약을 chat_sessions.metadata에 저장
2. 파라미터:
   - `user_id`: 사용자 ID
   - `query`: 사용자 질문
   - `response_summary`: 응답 요약
   - `relevance`: "RELEVANT"
   - `session_id`: chat_session_id (ChatSession.session_id)
   - `intent_detected`: Intent 타입
   - `entities_mentioned`: 추출된 엔티티
   - `conversation_metadata`: 추가 메타데이터

### 실제 동작
- **❌ AttributeError 발생 가능**
- `save_conversation` 메서드가 simple_memory_service.py에 없음
- 대신 `save_conversation_memory`가 있지만:
  - 시그니처가 완전히 다름
  - No-Op (아무것도 저장하지 않음)
  - 항상 True 반환

### 문제점
| 항목 | 기대값 | 실제값 | 영향 |
|------|--------|--------|------|
| 메서드 존재 | `save_conversation()` | ❌ 없음 | AttributeError |
| 파라미터 수 | 8개 | ❌ - | 호출 불가 |
| 저장 위치 | chat_sessions.metadata | ❌ - | 저장 안 됨 |
| 반환값 | None | ❌ - | 저장 실패 |

### Root Cause
- team_supervisor.py는 존재하지 않는 메서드를 호출
- simple_memory_service.py의 `save_conversation_memory`는 호환성 stub일 뿐
- 실제 저장 로직 구현 없음

---

## 3. Compatibility Stub Mismatch: save_conversation_memory

### 존재 위치: simple_memory_service.py:97-120

```python
async def save_conversation_memory(
    self,
    session_id: str,
    user_id: str,
    user_message: str,
    ai_response: str,
    metadata: Optional[Dict[str, Any]] = None
) -> bool:
    """대화 메모리 저장 (호환성용 - 실제로는 아무것도 안함)"""
    logger.debug(
        f"save_conversation_memory called (no-op): "
        f"session_id={session_id}, user_id={user_id}"
    )
    return True
```

### 문제점
| 항목 | 상태 | 설명 |
|------|------|------|
| 호출됨 | ❓ 불확실 | team_supervisor.py에서 호출되지 않음 |
| 동작 | ⚠️ No-Op | 로그만 출력, 저장 안 됨 |
| 반환값 | ✅ True | 항상 성공으로 반환 (거짓 성공) |
| 호환성 | ⚠️ 제한적 | 기존 코드 호환성만 제공 |

### 판단
- 호환성 stub이지만 team_supervisor.py에서는 사용하지 않음
- `save_conversation`과 시그니처가 다름
- Phase 1에서 삭제 또는 `save_conversation`으로 통합 필요

---

## 4. Compatibility Stub Mismatch: get_recent_memories

### 존재 위치: simple_memory_service.py:122-138

```python
async def get_recent_memories(
    self,
    user_id: str,
    limit: int = 5
) -> List[Dict[str, Any]]:
    """최근 메모리 조회 (호환성용 - 빈 리스트 반환)"""
    logger.debug(f"get_recent_memories called (returns empty): user_id={user_id}")
    return []
```

### 문제점
| 항목 | 기대값 | 실제값 | 영향 |
|------|--------|--------|------|
| 메서드 이름 | `load_recent_memories` | ⚠️ `get_recent_memories` | 이름 불일치 |
| 파라미터 | `user_id, limit, relevance_filter, session_id` | ⚠️ `user_id, limit` | 파라미터 누락 |
| 반환값 | 실제 메모리 리스트 | ⚠️ [] (빈 리스트) | 항상 비어있음 |
| 호출됨 | team_supervisor.py:211 | ❌ 호출 안 됨 | 메서드 이름 다름 |

### 판단
- team_supervisor.py는 `load_recent_memories`를 호출
- simple_memory_service.py에는 `get_recent_memories`만 있음
- **메서드 이름 불일치로 AttributeError 발생**

---

## 5. 파라미터 불일치 종합

### load_recent_memories 파라미터 비교

| 파라미터 | team_supervisor.py 호출 | simple_memory_service.py 구현 | 상태 |
|---------|------------------------|-------------------------------|------|
| `user_id` | ✅ 제공 | ❌ 메서드 없음 | - |
| `limit` | ✅ 제공 (settings.MEMORY_LOAD_LIMIT) | ❌ 메서드 없음 | - |
| `relevance_filter` | ✅ 제공 ("RELEVANT") | ❌ 메서드 없음 | - |
| `session_id` | ❌ **누락** | ❌ 메서드 없음 | **Critical!** |

### save_conversation 파라미터 비교

| 파라미터 | team_supervisor.py 호출 | simple_memory_service.py 구현 | 상태 |
|---------|------------------------|-------------------------------|------|
| `user_id` | ✅ 제공 | ❌ 메서드 없음 | - |
| `query` | ✅ 제공 | ❌ 메서드 없음 | - |
| `response_summary` | ✅ 제공 | ❌ 메서드 없음 | - |
| `relevance` | ✅ 제공 ("RELEVANT") | ❌ 메서드 없음 | - |
| `session_id` | ✅ 제공 (chat_session_id) | ❌ 메서드 없음 | - |
| `intent_detected` | ✅ 제공 | ❌ 메서드 없음 | - |
| `entities_mentioned` | ✅ 제공 | ❌ 메서드 없음 | - |
| `conversation_metadata` | ✅ 제공 | ❌ 메서드 없음 | - |

---

## 6. Import 불일치

### simple_memory_service.py 현재 Imports (Lines 5-10)

```python
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.chat import ChatMessage
```

### Phase 1 구현 시 필요한 Imports

```python
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime  # ⭐ 추가 필요
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import flag_modified  # ⭐ 추가 필요
from app.models.chat import ChatMessage, ChatSession  # ⭐ ChatSession 추가 필요
```

| Import | 현재 상태 | 필요 여부 | 용도 |
|--------|----------|-----------|------|
| `datetime` | ❌ 없음 | ✅ 필요 | timestamp 기록 |
| `flag_modified` | ❌ 없음 | ✅ 필요 | JSONB 업데이트 추적 |
| `ChatSession` | ❌ 없음 | ✅ 필요 | chat_sessions 테이블 접근 |

---

## 7. 설정(Settings) 불일치

### team_supervisor.py에서 사용하는 설정

```python
# Line 213
limit=settings.MEMORY_LOAD_LIMIT
```

### backend/app/core/config.py 현재 상태

**확인 필요:** `MEMORY_LOAD_LIMIT` 존재 여부

Phase 0.2에서 config.py를 확인한 결과:
- `MEMORY_LOAD_LIMIT = 5` ✅ 존재 (Lines 1-62 확인)

---

## 8. session_id vs chat_session_id 구분

### team_supervisor.py의 ID 사용

```python
# Line 889: HTTP/WebSocket session_id
session_id=session_id,

# Line 890: Chat History & State Endpoints ID
chat_session_id=chat_session_id,

# Line 653: save_conversation 호출 시
session_id=chat_session_id,  # ✅ chat_session_id 사용!
```

### 구분의 의미

| ID 종류 | 타입 | 용도 | 예시 |
|---------|------|------|------|
| `session_id` | HTTP/WebSocket ID | 요청 추적, Progress Callback | "ws-12345" |
| `chat_session_id` | ChatSession.session_id | DB 저장, 대화 기록 | "session-9b050480..." |

### load_recent_memories 호출 시 누락

```python
# Line 211-215 (planning_node)
loaded_memories = await memory_service.load_recent_memories(
    user_id=user_id,
    limit=settings.MEMORY_LOAD_LIMIT,
    relevance_filter="RELEVANT"
    # ❌ session_id 파라미터 없음!
)
```

**문제:**
- `chat_session_id`를 전달해야 현재 세션을 제외할 수 있음
- 전달하지 않으면 진행 중인 세션의 불완전한 데이터도 로드될 수 있음

**수정 필요:**
```python
# ✅ 수정 후
chat_session_id = state.get("chat_session_id")
loaded_memories = await memory_service.load_recent_memories(
    user_id=user_id,
    limit=settings.MEMORY_LOAD_LIMIT,
    relevance_filter="RELEVANT",
    session_id=chat_session_id  # ⭐ 추가!
)
```

---

## 9. 메서드 호출 흐름 분석

### 정상 흐름 (기대)

```
team_supervisor.py:211 (planning_node)
  ↓ load_recent_memories 호출
simple_memory_service.py:load_recent_memories
  ↓ chat_sessions 조회
  ↓ metadata 추출
  ↓ List[Dict] 반환
team_supervisor.py:220
  ↓ state["loaded_memories"] = loaded_memories
  ↓ Planning에서 메모리 활용
```

### 실제 흐름 (현재)

```
team_supervisor.py:211 (planning_node)
  ↓ load_recent_memories 호출
  ❌ AttributeError: 'SimpleMemoryService' object has no attribute 'load_recent_memories'
  ↓ Exception 발생
team_supervisor.py:226-228 (except Exception)
  ↓ logger.error("Failed to load Long-term Memory")
  ↓ 계속 진행 (비필수 기능)
  ↓ loaded_memories = None
```

### save_conversation 흐름

```
team_supervisor.py:656 (generate_response_node)
  ↓ save_conversation 호출
  ❌ AttributeError: 'SimpleMemoryService' object has no attribute 'save_conversation'
  ↓ Exception 발생
team_supervisor.py:673-675 (except Exception)
  ↓ logger.error("Failed to save Long-term Memory")
  ↓ 계속 진행 (비필수 기능)
  ↓ 저장 안 됨
```

---

## 10. 영향 분석

### 사용자 경험 영향

| 기능 | 기대 | 실제 | 사용자 경험 영향 |
|------|------|------|----------------|
| 메모리 로딩 | 이전 대화 기반 맥락 제공 | ❌ 실패 | 매번 새로운 대화처럼 응답 |
| 메모리 저장 | 대화 요약 축적 | ❌ 실패 | 대화 기록이 쌓이지 않음 |
| 개인화 | 사용자별 맞춤 응답 | ❌ 불가 | 일반적인 응답만 제공 |
| 연속성 | 대화 맥락 유지 | ❌ 불가 | 맥락 끊김 |

### 시스템 안정성 영향

| 항목 | 상태 | 설명 |
|------|------|------|
| AttributeError 발생 | ⚠️ 가능 | 메서드 없음으로 인한 에러 |
| Exception 처리 | ✅ 안전 | try-except로 감싸져 있음 |
| 기능 우아한 실패 | ✅ 가능 | "비필수 기능"으로 처리 |
| 로그 기록 | ✅ 있음 | logger.error로 기록됨 |

**결론:** 시스템은 계속 동작하지만 메모리 기능이 완전히 비활성화됨

---

## 11. Phase 0 Ground Truth 종합

### DB Schema (Phase 0.1)
✅ 검증 완료:
- chat_sessions.metadata (JSONB) 존재
- chat_messages.structured_data (JSONB) 존재
- Foreign Keys: CASCADE DELETE
- Memory 테이블 없음 (conversation_memories, entity_memories, user_preferences)

### Models (Phase 0.2)
✅ 검증 완료:
- ChatSession, ChatMessage 모델 → DB Schema와 100% 일치
- session_metadata → DB "metadata" 컬럼 매핑
- User 모델 → DB Schema와 100% 일치

### Zombie Code (Phase 0.3)
✅ 탐지 완료:
- old/ 디렉토리 5개 파일
- Stub 메서드 6개 (no-op 또는 빈 반환)
- **CRITICAL 누락 메서드 2개: load_recent_memories, save_conversation**

### Mismatch (Phase 0.4)
✅ 문서화 완료:
- load_recent_memories: 메서드 없음, session_id 파라미터 누락
- save_conversation: 메서드 없음, 8개 파라미터 불일치
- Import 3개 누락: datetime, flag_modified, ChatSession
- 메서드 이름 불일치: load_recent_memories vs get_recent_memories

---

## 12. Phase 1 구현 우선순위

### P0 (Critical - 메모리 기능 활성화)
1. ✅ **load_recent_memories 구현** (session_id 파라미터 포함)
2. ✅ **save_conversation 구현** (chat_sessions.metadata 활용)
3. ✅ Import 추가 (datetime, flag_modified, ChatSession)

### P1 (High - 코드 정리)
4. ✅ team_supervisor.py:211 수정 (session_id 파라미터 추가)
5. ✅ Stub 메서드 정리 (get_recent_memories, save_conversation_memory)
6. ✅ old/ 디렉토리 삭제 (4개 파일)

### P2 (Medium - 문서화)
7. ✅ 메서드 docstring 작성
8. ✅ 에러 처리 강화
9. ✅ 로깅 추가

---

## Phase 0 완료

✅ **Phase 0.1:** DB Schema extraction → 5개 파일 생성
✅ **Phase 0.2:** Models validation → 100% 일치 확인
✅ **Phase 0.3:** Zombie code detection → 5개 old 파일, 6개 stub, 2개 CRITICAL 누락
✅ **Phase 0.4:** Mismatch itemization → 2개 메서드 불일치, 파라미터 불일치 문서화

**Ground Truth 확립 완료!**

---

## 다음 단계: Phase 1 구현

**사용자 승인 후 진행:**
1. Import 추가
2. load_recent_memories 메서드 구현
3. save_conversation 메서드 구현
4. team_supervisor.py 수정 (session_id 파라미터 추가)
5. Stub 메서드 정리
6. 테스트 및 검증
