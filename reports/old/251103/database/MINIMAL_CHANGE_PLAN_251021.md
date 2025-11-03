# Minimal Change Plan - Session Deletion Fix

**Date:** 2025-10-21
**Scope:** 2개 파일, 6줄만 수정
**Risk:** 매우 낮음 (로직 변경 없음, 컬럼명만 수정)

---

## ⚠️ 핵심 원칙

### 바꾸는 것: checkpoint 테이블 쿼리의 컬럼명만

```sql
-- Before
WHERE session_id = :session_id

-- After
WHERE thread_id = :thread_id
```

### 안 바꾸는 것: 나머지 전부!

- ✅ 변수명 `session_id` → 그대로
- ✅ 테이블 `chat_sessions.session_id` → 그대로
- ✅ 테이블 `chat_messages.session_id` → 그대로
- ✅ scripts/ → 그대로
- ✅ models/ → 그대로
- ✅ schemas/ → 그대로

---

## 변경 대상 파일 (2개)

### File 1: chat_api.py

**Path:** `backend/app/api/chat_api.py`

**Line 12: Import 추가**
```python
# Before
from sqlalchemy import func

# After
from sqlalchemy import func, text
```

**Lines 482-493: 컬럼명 변경 (3곳)**
```python
# Before
await db.execute(
    "DELETE FROM checkpoints WHERE session_id = :session_id",
    {"session_id": session_id}
)
await db.execute(
    "DELETE FROM checkpoint_writes WHERE session_id = :session_id",
    {"session_id": session_id}
)
await db.execute(
    "DELETE FROM checkpoint_blobs WHERE session_id = :session_id",
    {"session_id": session_id}
)

# After
await db.execute(
    text("DELETE FROM checkpoints WHERE thread_id = :thread_id"),
    {"thread_id": session_id}  # 값은 동일!
)
await db.execute(
    text("DELETE FROM checkpoint_writes WHERE thread_id = :thread_id"),
    {"thread_id": session_id}  # 값은 동일!
)
await db.execute(
    text("DELETE FROM checkpoint_blobs WHERE thread_id = :thread_id"),
    {"thread_id": session_id}  # 값은 동일!
)
```

**변경 내용:**
1. `session_id` → `thread_id` (컬럼명)
2. `:session_id` → `:thread_id` (파라미터명)
3. `{"session_id": session_id}` → `{"thread_id": session_id}` (딕셔너리 키)
4. raw SQL → `text()` wrapper

**중요:** `session_id` 변수명은 그대로!

### File 2: postgres_session_manager.py

**Path:** `backend/app/api/postgres_session_manager.py`

**Line 9: Import 추가**
```python
# Before
from sqlalchemy import select, delete, update, func

# After
from sqlalchemy import select, delete, update, func, text
```

**Lines 216-228: 컬럼명 변경 (3곳)**
```python
# Before
await db_session.execute(
    "DELETE FROM checkpoints WHERE session_id = :session_id",
    {"session_id": session_id}
)
await db_session.execute(
    "DELETE FROM checkpoint_writes WHERE session_id = :session_id",
    {"session_id": session_id}
)
await db_session.execute(
    "DELETE FROM checkpoint_blobs WHERE session_id = :session_id",
    {"session_id": session_id}
)

# After
await db_session.execute(
    text("DELETE FROM checkpoints WHERE thread_id = :thread_id"),
    {"thread_id": session_id}  # 값은 동일!
)
await db_session.execute(
    text("DELETE FROM checkpoint_writes WHERE thread_id = :thread_id"),
    {"thread_id": session_id}  # 값은 동일!
)
await db_session.execute(
    text("DELETE FROM checkpoint_blobs WHERE thread_id = :thread_id"),
    {"thread_id": session_id}  # 값은 동일!
)
```

---

## 변경하지 않는 파일 (확인용)

### ❌ scripts/ - 변경 안 함!

**이유:** LangGraph가 자동으로 checkpoint 테이블 생성

```bash
# 확인
ls backend/scripts/
init_chat_tables.py  # ← 이 파일은 수정 안 함!
```

**init_chat_tables.py 내용:**
```python
# 이 부분은 그대로 둠!
async def create_checkpoint_tables():
    """LangGraph checkpoint 테이블 생성 (AsyncPostgresSaver.setup() 사용)"""
    from app.service_agent.foundation.checkpointer import create_checkpointer
    checkpointer = await create_checkpointer()  # ← LangGraph가 알아서 함!
```

### ❌ models/ - 변경 안 함!

**이유:** checkpoint 테이블은 LangGraph가 관리, 모델 정의 불필요

```bash
# 확인
ls backend/app/models/
chat.py           # ← ChatSession, ChatMessage만 있음 (그대로!)
user.py           # ← User 모델 (그대로!)
real_estate.py    # ← RealEstate 모델 (그대로!)
old/unified_schema.py  # ← 구 버전 (사용 안 함)
```

**chat.py 내용:**
```python
# 이것들은 전부 그대로!
class ChatSession(Base):
    __tablename__ = "chat_sessions"
    session_id = Column(String(100), primary_key=True)  # ✅ 그대로!
    ...

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    session_id = Column(String(100), ForeignKey(...))  # ✅ 그대로!
    ...

# Checkpoint 모델은 없음 (LangGraph가 관리)
```

### ❌ schemas/ - 변경 안 함!

**이유:** API 스키마는 session_id 사용

```bash
# 확인
ls backend/app/api/schemas.py
```

**schemas.py 내용:**
```python
# 이것들은 전부 그대로!
class SessionStartRequest(BaseModel):
    session_id: Optional[str] = None  # ✅ 그대로!

class SessionInfo(BaseModel):
    session_id: str  # ✅ 그대로!
    ...
```

### ❌ 기타 모든 코드 - 변경 안 함!

```python
# team_supervisor.py
chat_session_id = state.get("chat_session_id")  # ✅ 그대로!

# chat_api.py (다른 부분)
session_id = request.session_id  # ✅ 그대로!

# ws_manager.py
session_id: str  # ✅ 그대로!

# 등등... 전부 그대로!
```

---

## 변경 요약표

| 항목 | 변경 여부 | 이유 |
|------|----------|------|
| chat_api.py (Line 12) | ✅ 변경 | text import 추가 |
| chat_api.py (Lines 482-493) | ✅ 변경 | checkpoint 쿼리 컬럼명 |
| postgres_session_manager.py (Line 9) | ✅ 변경 | text import 추가 |
| postgres_session_manager.py (Lines 216-228) | ✅ 변경 | checkpoint 쿼리 컬럼명 |
| scripts/ | ❌ 유지 | LangGraph 자동 생성 |
| models/chat.py | ❌ 유지 | session_id 사용 |
| schemas/ | ❌ 유지 | session_id 사용 |
| 기타 모든 코드 | ❌ 유지 | session_id 사용 |

**Total:** 2개 파일만 수정

---

## 검증 방법

### 1. 수정 전 확인

```bash
# checkpoint 테이블 컬럼 확인
psql -U postgres -d real_estate -c "\d checkpoints"
# thread_id 컬럼이 있어야 함!

# chat_sessions 테이블 컬럼 확인
psql -U postgres -d real_estate -c "\d chat_sessions"
# session_id 컬럼이 있어야 함!
```

### 2. 수정 후 테스트

```bash
# 백엔드 재시작
cd backend
python -m uvicorn app.main:app --reload

# 프론트엔드에서 세션 삭제 테스트
# DELETE /api/v1/chat/sessions/session-xxx?hard_delete=true
# → 200 OK 응답 기대
```

### 3. DB 확인

```sql
-- 삭제 전 데이터 확인
SELECT thread_id FROM checkpoints WHERE thread_id = 'session-xxx';

-- 삭제 실행 (API 호출)

-- 삭제 후 확인
SELECT thread_id FROM checkpoints WHERE thread_id = 'session-xxx';
-- 0 rows (삭제 성공!)
```

---

## 위험 분석

### 매우 낮은 위험 ✅

**이유:**
1. 로직 변경 없음 (컬럼명만 수정)
2. 값은 동일 (session-xxx)
3. 2개 파일만 수정
4. 6줄만 변경
5. 쉬운 롤백 (git restore)

### 영향 범위

```
✅ 영향 있음: 세션 삭제 기능 (수정 목적)
❌ 영향 없음:
  - 세션 생성
  - 메시지 저장
  - 메시지 로드
  - WebSocket 통신
  - 모든 다른 기능
```

---

## 롤백 계획

### Git으로 즉시 복구 가능

```bash
# 문제 발생 시
cd C:\kdy\Projects\holmesnyangz\beta_v001
git restore backend/app/api/chat_api.py
git restore backend/app/api/postgres_session_manager.py

# 백엔드 재시작
cd backend
python -m uvicorn app.main:app --reload
```

**롤백 시간:** < 1분

---

## 주석 추가 (권장)

### chat_api.py

```python
# Line 481
# ⚠️ Important: LangGraph checkpoint tables use 'thread_id' column
# Our session_id value is stored in their thread_id column
# Example: checkpoints.thread_id = "session-abc123"
await db.execute(
    text("DELETE FROM checkpoints WHERE thread_id = :thread_id"),
    {"thread_id": session_id}  # session_id value → thread_id column
)
```

### postgres_session_manager.py

```python
# Line 215
# Note: LangGraph uses 'thread_id' as column name (not 'session_id')
# The session_id value is stored in thread_id column
await db_session.execute(
    text("DELETE FROM checkpoints WHERE thread_id = :thread_id"),
    {"thread_id": session_id}
)
```

---

## 체크리스트

### 구현 전
- [ ] 현재 DB 스키마 확인 (`\d checkpoints`)
- [ ] 백업 생성 (선택사항)
- [ ] Git 상태 확인 (`git status`)

### 구현 중
- [ ] chat_api.py import 추가
- [ ] chat_api.py 3개 쿼리 수정
- [ ] postgres_session_manager.py import 추가
- [ ] postgres_session_manager.py 3개 쿼리 수정
- [ ] 주석 추가 (권장)

### 테스트
- [ ] 백엔드 재시작
- [ ] 세션 삭제 테스트
- [ ] 200 OK 응답 확인
- [ ] DB에서 삭제 확인
- [ ] 프론트엔드 UI 확인

### 완료
- [ ] 에러 로그 없음
- [ ] 기능 정상 동작
- [ ] Git commit (선택)

---

## 예상 소요 시간

- **코드 수정:** 5분
- **테스트:** 5분
- **검증:** 5분
- **Total:** 15분

---

## 결론

### 변경 최소화 원칙

```
"최소한의 변경으로 최대 효과"

변경: 2개 파일, 6줄
효과: 세션 삭제 기능 복구
```

### 왜 이렇게 적게 바꾸나?

```
checkpoint 테이블 = LangGraph 영역
→ 우리가 맞출 수밖에 없음

chat_sessions 테이블 = 우리 영역
→ 우리 마음대로 (session_id 유지)
```

### 핵심 메시지

**"session_id를 thread_id로 전면 교체하는 것이 아닙니다!"**
**"checkpoint 쿼리의 컬럼명만 맞추는 것입니다!"**

---

**Status:** ✅ Ready to Implement
**Risk Level:** Very Low
**Time:** 15 minutes
**Rollback:** Easy (< 1 minute)

---

**Created by:** Claude Code
**Date:** 2025-10-21
