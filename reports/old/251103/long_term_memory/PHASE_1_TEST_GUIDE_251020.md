# Phase 1 테스트 가이드 - 2025-10-20

## 📋 현재 구현 상태

### ✅ 구현 완료된 기능
1. **load_recent_memories** - 최근 대화 요약 로드
2. **save_conversation** - 대화 요약 저장
3. **team_supervisor.py 연동** - planning_node, generate_response_node에서 호출

### 🔍 테스트 목적
- Phase 1 구현이 실제로 작동하는지 확인
- 메모리 로드/저장이 제대로 되는지 검증
- AttributeError가 발생하지 않는지 확인

---

## 🧪 테스트 방법 3가지

### 방법 1: 간단한 DB 확인 테스트 (추천 ⭐)
**난이도:** ⭐ (가장 쉬움)
**시간:** 5분
**필요사항:** PostgreSQL 접근만 필요

**목적:**
- 코드 실행 없이 DB 상태만 확인
- chat_sessions.metadata 구조 확인
- 기존 데이터로 메모리 로드 가능 여부 확인

**실행 방법:**
```sql
-- 1. chat_sessions 테이블에 metadata가 있는지 확인
SELECT
    session_id,
    user_id,
    title,
    metadata,
    created_at,
    updated_at
FROM chat_sessions
WHERE metadata IS NOT NULL
ORDER BY updated_at DESC
LIMIT 5;

-- 2. metadata 구조 확인 (conversation_summary가 있는지)
SELECT
    session_id,
    metadata->>'conversation_summary' as summary,
    metadata->>'last_updated' as last_updated,
    metadata->>'message_count' as message_count
FROM chat_sessions
WHERE metadata ? 'conversation_summary'
ORDER BY updated_at DESC
LIMIT 3;

-- 3. 특정 사용자의 세션 개수 확인
SELECT
    user_id,
    COUNT(*) as session_count,
    COUNT(CASE WHEN metadata ? 'conversation_summary' THEN 1 END) as with_summary
FROM chat_sessions
GROUP BY user_id
ORDER BY session_count DESC;
```

**예상 결과:**
- 현재는 `conversation_summary`가 없을 가능성이 높음 (아직 대화 저장 안됨)
- 이 경우 → **방법 2 또는 3**으로 진행하여 실제 대화 후 다시 확인

---

### 방법 2: 백엔드 단독 테스트 (Python 스크립트)
**난이도:** ⭐⭐ (중간)
**시간:** 10-15분
**필요사항:** Python 환경, DB 연결

**목적:**
- 프론트엔드 없이 백엔드 메모리 기능만 테스트
- save_conversation, load_recent_memories 직접 호출
- DB에 실제로 저장/로드되는지 확인

**테스트 스크립트 작성:**

```python
# test_phase1_memory.py
"""
Phase 1 메모리 서비스 테스트 스크립트
"""
import asyncio
import sys
from pathlib import Path

# 프로젝트 루트를 Python path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.db.postgre_db import get_async_db
from app.service_agent.foundation.simple_memory_service import LongTermMemoryService


async def test_save_and_load():
    """대화 저장 및 로드 테스트"""

    print("=" * 60)
    print("Phase 1 메모리 서비스 테스트 시작")
    print("=" * 60)

    # 테스트 데이터
    test_user_id = "1"  # 실제 DB에 있는 user_id 사용
    test_session_id = "test-session-251020-001"
    test_summary = "테스트: 사용자가 강남구 아파트 전세 시세를 문의하였고, 5억~7억 범위로 안내함"

    async for db_session in get_async_db():
        try:
            memory_service = LongTermMemoryService(db_session)

            # === 테스트 1: 대화 저장 ===
            print("\n[테스트 1] save_conversation 호출")
            print(f"  - user_id: {test_user_id}")
            print(f"  - session_id: {test_session_id}")
            print(f"  - summary: {test_summary[:50]}...")

            await memory_service.save_conversation(
                user_id=test_user_id,
                session_id=test_session_id,
                messages=[],
                summary=test_summary
            )
            print("  ✅ 저장 성공!")

            # === 테스트 2: 메모리 로드 (현재 세션 제외) ===
            print("\n[테스트 2] load_recent_memories 호출 (현재 세션 제외)")
            memories = await memory_service.load_recent_memories(
                user_id=test_user_id,
                limit=5,
                relevance_filter="ALL",
                session_id=test_session_id  # 방금 저장한 세션 제외
            )
            print(f"  ✅ 로드 성공! 찾은 메모리: {len(memories)}개")

            for i, mem in enumerate(memories, 1):
                print(f"\n  메모리 #{i}:")
                print(f"    - session_id: {mem['session_id']}")
                print(f"    - summary: {mem['summary'][:60]}...")
                print(f"    - timestamp: {mem['timestamp']}")

            # === 테스트 3: 메모리 로드 (현재 세션 포함) ===
            print("\n[테스트 3] load_recent_memories 호출 (현재 세션 포함)")
            memories_with_current = await memory_service.load_recent_memories(
                user_id=test_user_id,
                limit=5,
                relevance_filter="ALL",
                session_id=None  # 현재 세션도 포함
            )
            print(f"  ✅ 로드 성공! 찾은 메모리: {len(memories_with_current)}개")

            # 방금 저장한 세션이 포함되었는지 확인
            test_session_found = any(
                mem['session_id'] == test_session_id
                for mem in memories_with_current
            )

            if test_session_found:
                print(f"  ✅ 방금 저장한 세션({test_session_id})이 포함되어 있음")
            else:
                print(f"  ⚠️ 방금 저장한 세션이 없음 (metadata가 아직 커밋 안됨?)")

            print("\n" + "=" * 60)
            print("테스트 완료!")
            print("=" * 60)

        except Exception as e:
            print(f"\n❌ 테스트 실패: {e}")
            import traceback
            traceback.print_exc()

        finally:
            break  # 첫 번째 세션만 사용


if __name__ == "__main__":
    asyncio.run(test_save_and_load())
```

**실행 방법:**
```bash
# backend 디렉토리에서 실행
cd C:\kdy\Projects\holmesnyangz\beta_v001\backend
python test_phase1_memory.py
```

**예상 결과:**
```
============================================================
Phase 1 메모리 서비스 테스트 시작
============================================================

[테스트 1] save_conversation 호출
  - user_id: 1
  - session_id: test-session-251020-001
  - summary: 테스트: 사용자가 강남구 아파트 전세 시세를 문의하였고...
  ✅ 저장 성공!

[테스트 2] load_recent_memories 호출 (현재 세션 제외)
  ✅ 로드 성공! 찾은 메모리: 0개

[테스트 3] load_recent_memories 호출 (현재 세션 포함)
  ✅ 로드 성공! 찾은 메모리: 1개

  메모리 #1:
    - session_id: test-session-251020-001
    - summary: 테스트: 사용자가 강남구 아파트 전세 시세를 문의하였고...
    - timestamp: 2025-10-20T10:30:00

  ✅ 방금 저장한 세션(test-session-251020-001)이 포함되어 있음

============================================================
테스트 완료!
============================================================
```

---

### 방법 3: 프론트엔드 + 백엔드 통합 테스트 (실제 사용 시나리오)
**난이도:** ⭐⭐⭐ (가장 복잡)
**시간:** 20-30분
**필요사항:** 프론트엔드 + 백엔드 실행

**목적:**
- 실제 사용자 시나리오로 테스트
- 대화 흐름에서 메모리가 자동으로 저장/로드되는지 확인
- AttributeError 발생 여부 확인

**테스트 시나리오:**

#### Step 1: 백엔드 실행
```bash
cd C:\kdy\Projects\holmesnyangz\beta_v001\backend
uvicorn app.main:app --reload --port 8000
```

#### Step 2: 프론트엔드 실행
```bash
cd C:\kdy\Projects\holmesnyangz\beta_v001\frontend
npm run dev
```

#### Step 3: 브라우저에서 테스트
1. **첫 번째 대화 시작** (Session A)
   - 사용자 로그인 (user_id 확인 필요)
   - 질문: "강남구 아파트 전세 시세 알려줘"
   - 응답 확인
   - **중요:** 이 대화가 끝나면 `save_conversation`이 호출되어 metadata에 저장됨

2. **두 번째 대화 시작** (Session B - 새 세션)
   - 새로고침 또는 새 세션 시작
   - 질문: "서초구 아파트 매매가 궁금해"
   - **확인사항:**
     - 백엔드 로그에서 `[TeamSupervisor] Loading Long-term Memory` 메시지 확인
     - 이전 대화(Session A) 요약이 로드되었는지 로그 확인
   - 응답 확인

3. **세 번째 대화** (Session C - 새 세션)
   - 새로고침 또는 새 세션 시작
   - 질문: "송파구 빌라 전세 정보 주세요"
   - **확인사항:**
     - 백엔드 로그에서 `Loaded 2 memories` 메시지 확인 (Session A, B)
     - 현재 세션(Session C)은 제외되고 있는지 확인

#### Step 4: 백엔드 로그 확인
**찾아야 할 로그 메시지:**
```
✅ 메모리 로드 로그:
[TeamSupervisor] Loading Long-term Memory for user {user_id}
Loaded {N} memories for user {user_id}
[TeamSupervisor] Loaded {N} memories and preferences for user {user_id}

✅ 메모리 저장 로그:
Conversation saved: session_id={session_id}, summary_length={length}
[TeamSupervisor] Conversation saved to Long-term Memory

❌ 에러 로그 (이게 나오면 안됨):
AttributeError: 'SimpleMemoryService' object has no attribute 'load_recent_memories'
AttributeError: 'SimpleMemoryService' object has no attribute 'save_conversation'
[TeamSupervisor] Failed to load Long-term Memory: {error}
[TeamSupervisor] Failed to save Long-term Memory: {error}
```

#### Step 5: DB에서 확인
```sql
-- 저장된 메모리 확인
SELECT
    session_id,
    user_id,
    title,
    metadata->'conversation_summary' as summary,
    metadata->'last_updated' as last_updated,
    created_at
FROM chat_sessions
WHERE user_id = 1  -- 테스트한 user_id
  AND metadata ? 'conversation_summary'
ORDER BY updated_at DESC
LIMIT 10;
```

---

## 🎯 각 방법의 장단점 비교

| 방법 | 난이도 | 시간 | 장점 | 단점 | 추천 순서 |
|------|--------|------|------|------|-----------|
| **1. DB 확인** | ⭐ | 5분 | 빠르고 간단, 코드 실행 불필요 | 실제 동작 확인 불가 | **1번째** |
| **2. 백엔드 스크립트** | ⭐⭐ | 15분 | 메모리 기능만 집중 테스트, 에러 디버깅 쉬움 | 전체 흐름 확인 불가 | **2번째** |
| **3. 통합 테스트** | ⭐⭐⭐ | 30분 | 실제 사용 시나리오, 전체 흐름 확인 | 시간 오래 걸림, 디버깅 어려움 | **3번째** |

---

## 📊 테스트 체크리스트

### Phase 1 검증 항목

#### ✅ 기본 동작 확인
- [ ] `save_conversation` 메서드 존재 확인
- [ ] `load_recent_memories` 메서드 존재 확인
- [ ] `team_supervisor.py`에서 두 메서드 호출 확인

#### ✅ 메모리 저장 테스트
- [ ] `chat_sessions.metadata`에 `conversation_summary` 저장됨
- [ ] `last_updated` 타임스탬프 저장됨
- [ ] `message_count` 저장됨
- [ ] DB commit 후 데이터 확인 가능

#### ✅ 메모리 로드 테스트
- [ ] 사용자별로 최근 N개 세션 로드
- [ ] `session_id` 파라미터로 현재 세션 제외
- [ ] `updated_at` 기준 내림차순 정렬
- [ ] `conversation_summary`가 있는 세션만 반환

#### ✅ 에러 처리 확인
- [ ] AttributeError 발생하지 않음
- [ ] DB 에러 시 rollback 동작
- [ ] 세션 없을 때 warning 로그만 출력 (프로그램 중단 안됨)

#### ✅ 통합 테스트 확인
- [ ] 대화 종료 시 자동 저장
- [ ] 새 대화 시작 시 자동 로드
- [ ] 프론트엔드 정상 작동
- [ ] 백엔드 로그에 정상 메시지 출력

---

## 🚀 추천 테스트 순서

### 초보자용 (안전하고 단계적)

1. **먼저 방법 1 (DB 확인)** - 5분
   - 현재 DB 상태 확인
   - 기존 데이터로 메모리 로드 가능한지 파악

2. **다음 방법 2 (백엔드 스크립트)** - 15분
   - 메모리 저장/로드 기능만 집중 테스트
   - 에러 발생 시 즉시 확인 및 수정

3. **마지막 방법 3 (통합 테스트)** - 30분
   - 실제 사용 시나리오로 전체 흐름 확인
   - 최종 검증

### 시간 부족한 경우

1. **방법 2만 실행** - 15분
   - 백엔드 스크립트로 핵심 기능만 빠르게 테스트
   - 통과하면 → 구현 완료로 간주

2. **나중에 방법 3** - 여유 있을 때
   - 실제 사용하면서 자연스럽게 검증

---

## 🐛 예상 문제 및 해결 방법

### 문제 1: `test_session_id`로 세션을 찾을 수 없음
**증상:**
```
Session not found or user mismatch: session_id=test-session-251020-001, user_id=1
```

**원인:**
- 테스트 스크립트에서 사용한 `test_session_id`가 실제 DB에 없음

**해결:**
```python
# 방법 A: 먼저 세션 생성
from app.models.chat import ChatSession
session = ChatSession(
    session_id=test_session_id,
    user_id=test_user_id,
    title="테스트 세션",
    session_metadata={}
)
db_session.add(session)
await db_session.commit()

# 방법 B: 기존 세션 ID 사용
query = select(ChatSession).where(ChatSession.user_id == test_user_id).limit(1)
result = await db_session.execute(query)
existing_session = result.scalar_one_or_none()
if existing_session:
    test_session_id = existing_session.session_id
```

### 문제 2: `load_recent_memories`가 빈 리스트 반환
**증상:**
```
Loaded 0 memories for user 1
```

**원인:**
- 해당 user_id의 세션에 `conversation_summary`가 없음

**해결:**
1. 먼저 `save_conversation`으로 메모리 저장
2. 또는 DB에 직접 추가:
```sql
UPDATE chat_sessions
SET metadata = '{"conversation_summary": "테스트 요약"}'::jsonb
WHERE user_id = 1
  AND session_id = 'some-session-id';
```

### 문제 3: AttributeError 여전히 발생
**증상:**
```
AttributeError: 'SimpleMemoryService' object has no attribute 'load_recent_memories'
```

**원인:**
- 파일이 제대로 저장되지 않았거나 import cache 문제

**해결:**
```bash
# 1. 백엔드 재시작
# Ctrl+C로 중지 후 다시 실행

# 2. Python cache 삭제
find backend -name "__pycache__" -type d -exec rm -rf {} +
find backend -name "*.pyc" -delete

# 3. 파일 확인
grep -n "def load_recent_memories" backend/app/service_agent/foundation/simple_memory_service.py
grep -n "def save_conversation" backend/app/service_agent/foundation/simple_memory_service.py
```

---

## 📝 테스트 결과 기록 템플릿

```markdown
## Phase 1 테스트 결과 - 2025-10-20

### 테스트 환경
- OS: Windows 11
- Python: 3.x
- PostgreSQL: 14.x
- 테스트 방법: [방법 1/2/3]

### 테스트 결과
- [ ] ✅ save_conversation 정상 동작
- [ ] ✅ load_recent_memories 정상 동작
- [ ] ✅ session_id 제외 로직 정상 동작
- [ ] ✅ AttributeError 발생하지 않음
- [ ] ✅ DB에 메타데이터 정상 저장

### 발견된 문제
1. [문제 설명]
   - 원인: [원인 분석]
   - 해결: [해결 방법]

### 스크린샷
[백엔드 로그 스크린샷]
[DB 쿼리 결과 스크린샷]

### 결론
- [ ] Phase 1 구현 성공
- [ ] Phase 2로 진행 가능
```

---

## 🎉 성공 기준

다음 항목이 모두 만족되면 **Phase 1 성공**:

1. ✅ `save_conversation` 호출 시 에러 없이 DB에 저장됨
2. ✅ `load_recent_memories` 호출 시 에러 없이 데이터 반환됨
3. ✅ `session_id` 파라미터로 현재 세션이 제외됨
4. ✅ AttributeError가 발생하지 않음
5. ✅ 백엔드 로그에 정상 메시지 출력됨

**→ 모두 통과하면 Phase 2 (Enhanced Memory) 진행 가능!**

---

## 🔜 다음 단계 (Phase 2)

Phase 1 테스트 통과 후:
1. `conversation_memories` 테이블 생성
2. `entity_memories` 테이블 생성
3. `user_preferences` 테이블 생성
4. 상세 메타데이터 저장 기능 추가
5. Phase 1 → Phase 2 마이그레이션 스크립트 작성
