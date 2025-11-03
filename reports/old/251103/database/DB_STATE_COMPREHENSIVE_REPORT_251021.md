# Database State Comprehensive Report - Checkpoint Tables

**Date:** 2025-10-21
**Issue:** Understanding how checkpoint tables were created
**Status:** 🔍 Complete Analysis

---

## 핵심 발견 사항

### LangGraph가 자동으로 테이블을 생성했습니다! ✅

**증거:**
1. ✅ `AsyncPostgresSaver.from_conn_string()` 호출 시 **자동으로 테이블 생성**
2. ✅ `checkpoint_migrations` 테이블에 10개 마이그레이션 기록
3. ✅ LangGraph 기본 스키마는 `thread_id` 사용 (session_id 아님!)
4. ✅ 애플리케이션 첫 실행 시 자동으로 setup 실행됨

---

## 타임라인 재구성

### 1단계: 사용자가 chat_sessions 테이블 생성
```sql
-- 사용자가 만든 테이블
CREATE TABLE chat_sessions (
    session_id VARCHAR(100) PRIMARY KEY,
    user_id INTEGER NOT NULL,
    ...
);
```
**컬럼명:** `session_id` ✅

### 2단계: LangGraph가 checkpoint 테이블 자동 생성

**언제:** 애플리케이션 첫 실행 시
**어디서:** `team_supervisor.py` Line 1182

```python
# team_supervisor.py:1182
self._checkpoint_cm = AsyncPostgresSaver.from_conn_string(DB_URI)
self.checkpointer = await self._checkpoint_cm.__aenter__()
```

**결과:** LangGraph가 자동으로 다음 테이블 생성
- `checkpoints` (thread_id)
- `checkpoint_writes` (thread_id)
- `checkpoint_blobs` (thread_id)
- `checkpoint_migrations` (버전 관리)

**컬럼명:** `thread_id` ❌ (LangGraph 기본값)

### 3단계: 마이그레이션 실행

```sql
SELECT * FROM checkpoint_migrations;

v
---
0   -- 초기 스키마
1   -- 마이그레이션 1
2   -- 마이그레이션 2
...
9   -- 마이그레이션 9
```

**총 10개 마이그레이션 자동 실행됨**

---

## 현재 DB 상태 정리

### Chat 관련 테이블 (사용자가 생성)
```
✅ chat_sessions      -> session_id (컬럼)
✅ chat_messages      -> session_id (외래키)
✅ users              -> id
```

### Checkpoint 테이블 (LangGraph 자동 생성)
```
❌ checkpoints        -> thread_id (컬럼)  ⚠️ session_id가 아님!
❌ checkpoint_writes  -> thread_id (컬럼)  ⚠️ session_id가 아님!
❌ checkpoint_blobs   -> thread_id (컬럼)  ⚠️ session_id가 아님!
✅ checkpoint_migrations -> v (버전)
```

### 데이터 저장 형식

```sql
-- checkpoints 테이블 샘플
SELECT thread_id FROM checkpoints LIMIT 3;

thread_id
-------------------------------------------
session-ad7e7fe3-dccf-4c56-b87f-628dda96485f  ⭐ session-xxx 형식
session-ad7e7fe3-dccf-4c56-b87f-628dda96485f
session-e20538b9-57c0-4ac9-abbe-a075da9e8266
```

**중요:** `thread_id` 값은 `session-xxx` 형식으로 저장됨
→ **값은 session_id와 동일, 컬럼명만 다름!**

---

## LangGraph 초기화 코드 위치

### 위치 1: team_supervisor.py (메인)

**File:** `backend/app/service_agent/supervisor/team_supervisor.py`

**Lines 1168-1186:**
```python
if not self._checkpointer_initialized:
    try:
        logger.info("Initializing AsyncPostgresSaver checkpointer with PostgreSQL...")

        # Use AsyncPostgresSaver for PostgreSQL
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
        from app.core.config import settings

        # PostgreSQL 연결 문자열 (중앙화된 설정 사용)
        DB_URI = settings.get_postgres_uri()
        logger.info(f"Using PostgreSQL URL from centralized config: {DB_URI.replace(settings.POSTGRES_PASSWORD, '***')}")

        # Create and enter async context manager
        self._checkpoint_cm = AsyncPostgresSaver.from_conn_string(DB_URI)  # ⭐ 여기서 자동 생성!
        self.checkpointer = await self._checkpoint_cm.__aenter__()

        # 최초 테이블 생성 (checkpoints, checkpoint_blobs, checkpoint_writes)
        self._checkpointer_initialized = True
        logger.info("Checkpointer initialized successfully")
```

**핵심:** `AsyncPostgresSaver.from_conn_string()`이 호출되면:
1. DB 연결
2. checkpoint 테이블 존재 확인
3. **없으면 자동으로 생성** (thread_id 사용)
4. migrations 실행

### 위치 2: checkpointer.py (헬퍼)

**File:** `backend/app/service_agent/foundation/checkpointer.py`

**Lines 68-86:**
```python
logger.info(f"Creating AsyncPostgresSaver checkpointer")

try:
    # AsyncPostgresSaver.from_conn_string returns an async context manager
    # We need to enter the context and keep it alive
    context_manager = AsyncPostgresSaver.from_conn_string(conn_string)  # ⭐ 여기도!

    # Enter the async context manager
    actual_checkpointer = await context_manager.__aenter__()

    # Setup tables (creates if not exists)
    await actual_checkpointer.setup()  # ⭐ setup()이 테이블 생성!
```

### 위치 3: init_chat_tables.py (초기화 스크립트)

**File:** `backend/scripts/init_chat_tables.py`

**Lines 72-82:**
```python
async def create_checkpoint_tables():
    """LangGraph checkpoint 테이블 생성 (AsyncPostgresSaver.setup() 사용)"""
    print("\n📦 LangGraph checkpoint 테이블 생성 중...")

    try:
        from app.service_agent.foundation.checkpointer import create_checkpointer

        # AsyncPostgresSaver 인스턴스 생성 및 setup 호출
        checkpointer = await create_checkpointer()  # ⭐ 여기도!
        print("   ✓ checkpoints")
        print("   ✓ checkpoint_blobs")
        print("   ✓ checkpoint_writes")
```

---

## LangGraph 동작 방식

### AsyncPostgresSaver.from_conn_string() 내부 동작

```python
# LangGraph 내부 코드 (추정)
class AsyncPostgresSaver:
    @classmethod
    async def from_conn_string(cls, conn_string: str):
        # 1. DB 연결
        conn = await create_connection(conn_string)

        # 2. 마이그레이션 테이블 확인
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS checkpoint_migrations (
                v INTEGER PRIMARY KEY
            )
        """)

        # 3. 현재 버전 확인
        current_version = await get_current_version(conn)

        # 4. 필요한 마이그레이션 실행
        for migration in MIGRATIONS[current_version:]:
            await migration.run(conn)  # ⭐ thread_id 컬럼으로 테이블 생성!
            await record_migration(conn, migration.version)

        return cls(conn)
```

### Migrations 내용 (추정)

```python
# Migration 0: 기본 테이블 생성
CREATE TABLE checkpoints (
    thread_id TEXT NOT NULL,      -- ⚠️ LangGraph 기본값
    checkpoint_ns TEXT NOT NULL DEFAULT '',
    checkpoint_id TEXT NOT NULL,
    ...
);

# Migration 1-9: 스키마 업데이트
ALTER TABLE checkpoints ADD COLUMN metadata JSONB;
CREATE INDEX checkpoints_thread_id_idx ON checkpoints(thread_id);
...
```

---

## 왜 session_id가 아닌 thread_id인가?

### LangGraph 용어 정리

**LangGraph 관점:**
- `thread` = 대화 스레드
- `thread_id` = 스레드 고유 식별자
- Checkpoint는 "thread" 단위로 저장됨

**우리 애플리케이션 관점:**
- `session` = 채팅 세션
- `session_id` = 세션 고유 식별자
- Session ID 형식: `session-xxx`

**매핑:**
```
LangGraph thread_id  ←→  Our session_id
(컬럼명 다름, 값은 동일)
```

---

## 문제 발생 원인

### 코드 작성 시 가정

```python
# chat_api.py:483 (잘못된 가정)
await db.execute(
    "DELETE FROM checkpoints WHERE session_id = :session_id",  # ❌
    {"session_id": session_id}
)
```

**개발자 생각:**
- "checkpoint 테이블에도 session_id 컬럼이 있겠지"
- "chat_sessions와 같은 컬럼명을 사용하겠지"

**실제 DB:**
- LangGraph가 `thread_id` 컬럼으로 생성
- `session_id` 컬럼은 존재하지 않음

### 에러 발생

```sql
DELETE FROM checkpoints WHERE session_id = 'session-xxx'
                              ^
ERROR: column "session_id" does not exist
```

---

## 해결 방법 비교

### 옵션 A: 코드 수정 (thread_id 사용) ⭐ 추천

**장점:**
- ✅ 간단 (코드 2줄만 수정)
- ✅ LangGraph 기본 스키마 유지
- ✅ 미래 업그레이드 호환성
- ✅ 데이터 손실 없음

**단점:**
- ⚠️ 컬럼명이 직관적이지 않음

**구현:**
```python
# session_id → thread_id 변경
await db.execute(
    text("DELETE FROM checkpoints WHERE thread_id = :thread_id"),
    {"thread_id": session_id}  # 값은 동일
)
```

### 옵션 B: DB 수정 (session_id로 변경)

**장점:**
- ✅ 직관적인 컬럼명
- ✅ 일관성 (chat_sessions와 동일)

**단점:**
- ❌ DB 마이그레이션 필요
- ❌ LangGraph 자동 마이그레이션과 충돌 가능
- ❌ 인덱스 재생성 필요
- ❌ 위험도 높음

**구현:**
```sql
ALTER TABLE checkpoints RENAME COLUMN thread_id TO session_id;
ALTER TABLE checkpoint_writes RENAME COLUMN thread_id TO session_id;
ALTER TABLE checkpoint_blobs RENAME COLUMN thread_id TO session_id;

-- 인덱스 재생성
DROP INDEX checkpoints_thread_id_idx;
CREATE INDEX checkpoints_session_id_idx ON checkpoints(session_id);
...
```

**추가 작업:**
```python
# LangGraph 자동 마이그레이션 비활성화 필요
# 그렇지 않으면 다시 thread_id로 되돌아갈 수 있음
```

### 옵션 C: LangGraph 설정 변경 (불가능)

**이유:**
- LangGraph는 `thread_id`를 하드코딩으로 사용
- 컬럼명 변경 옵션 없음
- 소스 코드 수정 필요 (비현실적)

---

## 최종 권장 사항

### ✅ 옵션 A 채택 (코드 수정)

**이유:**
1. 가장 간단하고 안전
2. LangGraph 표준 스키마 준수
3. 미래 호환성 보장
4. 데이터 손실 위험 없음

**수정할 코드:**

#### File 1: chat_api.py
```python
# Line 12: Import 추가
from sqlalchemy import func, text

# Lines 482-493: 수정
await db.execute(
    text("DELETE FROM checkpoints WHERE thread_id = :thread_id"),
    {"thread_id": session_id}
)
await db.execute(
    text("DELETE FROM checkpoint_writes WHERE thread_id = :thread_id"),
    {"thread_id": session_id}
)
await db.execute(
    text("DELETE FROM checkpoint_blobs WHERE thread_id = :thread_id"),
    {"thread_id": session_id}
)
```

#### File 2: postgres_session_manager.py
```python
# Line 9: Import 추가
from sqlalchemy import select, delete, update, func, text

# Lines 216-228: 수정
await db_session.execute(
    text("DELETE FROM checkpoints WHERE thread_id = :thread_id"),
    {"thread_id": session_id}
)
await db_session.execute(
    text("DELETE FROM checkpoint_writes WHERE thread_id = :thread_id"),
    {"thread_id": session_id}
)
await db_session.execute(
    text("DELETE FROM checkpoint_blobs WHERE thread_id = :thread_id"),
    {"thread_id": session_id}
)
```

**변경 사항:**
1. `session_id` → `thread_id` (컬럼명)
2. raw SQL → `text()` wrapper (SQLAlchemy 2.0)
3. `:session_id` → `:thread_id` (파라미터명도 변경)

---

## 추가 문서화 필요 사항

### 코드 주석 추가

```python
# checkpoints 관련 테이블 정리
# Note: LangGraph uses 'thread_id' column (not 'session_id')
# thread_id value = session_id value (e.g., 'session-xxx')
await db.execute(
    text("DELETE FROM checkpoints WHERE thread_id = :thread_id"),
    {"thread_id": session_id}  # session_id as value for thread_id
)
```

### README 추가

```markdown
## Database Schema Notes

### Checkpoint Tables (LangGraph)

LangGraph automatically manages these tables:
- `checkpoints`
- `checkpoint_writes`
- `checkpoint_blobs`
- `checkpoint_migrations`

**Important:** These tables use `thread_id` column (LangGraph standard)
- `thread_id` in DB = `session_id` in our code
- Values are identical (e.g., `session-ad7e7fe3...`)
- Column names are different!

When deleting checkpoints, use:
```python
DELETE FROM checkpoints WHERE thread_id = :thread_id
```
```

---

## 테스트 계획

### 1. 현재 데이터 확인
```sql
-- session_id와 thread_id 일치 확인
SELECT cs.session_id, c.thread_id, COUNT(*) as checkpoint_count
FROM chat_sessions cs
LEFT JOIN checkpoints c ON cs.session_id = c.thread_id
WHERE cs.user_id = 1
GROUP BY cs.session_id, c.thread_id
LIMIT 10;
```

### 2. 삭제 테스트 (수정 후)
```sql
-- 테스트용 세션 선택
SELECT session_id FROM chat_sessions WHERE user_id = 1 LIMIT 1;

-- 삭제 전 checkpoint 수 확인
SELECT COUNT(*) FROM checkpoints WHERE thread_id = 'session-xxx';

-- 삭제 실행 (API 호출)
DELETE /api/v1/chat/sessions/session-xxx?hard_delete=true

-- 삭제 후 확인
SELECT COUNT(*) FROM checkpoints WHERE thread_id = 'session-xxx';  -- 0이어야 함
```

---

## 결론

### 발견 사항
1. ✅ LangGraph가 자동으로 checkpoint 테이블 생성
2. ✅ `thread_id` 컬럼 사용 (LangGraph 표준)
3. ✅ 10개 마이그레이션 자동 실행됨
4. ✅ `session_id` 값과 `thread_id` 값은 동일

### 문제 원인
- 코드가 존재하지 않는 `session_id` 컬럼 참조
- 실제 컬럼명은 `thread_id`

### 해결 방법
- `session_id` → `thread_id` 변경 (코드 2개 파일)
- `text()` wrapper 추가 (SQLAlchemy 2.0)

### 예상 소요 시간
- 코드 수정: 5분
- 테스트: 10분
- 문서화: 5분
- **총 20분**

---

**Status:** ✅ Analysis Complete - Ready for Implementation
**Created by:** Claude Code
**Date:** 2025-10-21
**Next Step:** 사용자 승인 후 수정 진행
