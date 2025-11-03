# session_id vs user_id 명확한 구분

**Date**: 2025-10-14
**Purpose**: session_id와 user_id의 차이점과 타입 설정 명확화

---

## 핵심 질문

> **"세션 ID는 UUID로 저장하려고 했는데, 이것과 user_id 타입 불일치가 관련있는가?"**

---

## 짧은 답변

**아니요, 전혀 관련 없습니다!**

- **session_id**: UUID 기반 문자열 (현재 `String(100)`)
  → **변경 불필요**, 그대로 유지 ✅

- **user_id**: 사용자 ID 정수 (현재 `String(100)`)
  → **변경 필요**, `Integer`로 수정 ⚠️

**두 개는 완전히 다른 개념입니다!**

---

## 1. session_id vs user_id 비교

### 현재 sessions 테이블 구조

```python
class Session(Base):
    __tablename__ = "sessions"

    # Primary Key
    session_id = Column(String(100), primary_key=True, index=True)  # ← UUID 문자열

    # User & Metadata
    user_id = Column(String(100), nullable=True)  # ← 사용자 ID (문자열)
```

| 필드 | 현재 타입 | 용도 | 예시 값 | 변경 여부 |
|------|-----------|------|---------|-----------|
| **session_id** | String(100) | WebSocket 세션 식별자 | `"session-abc123-def456-..."` | ❌ **변경 불필요** |
| **user_id** | String(100) | 사용자 식별자 | `"123"` (현재) → `123` (수정 후) | ✅ **변경 필요** |

---

## 2. session_id 상세 설명

### session_id란?

**WebSocket 연결의 고유 식별자**입니다.

```python
# session_manager.py Line 57
session_id = f"session-{uuid.uuid4()}"

# 실제 예시:
# "session-550e8400-e29b-41d4-a716-446655440000"
```

**특징**:
- ✅ UUID v4 기반 생성
- ✅ 각 WebSocket 연결마다 고유
- ✅ 24시간 TTL 후 자동 삭제
- ✅ Primary Key (테이블의 기본 키)

**타입**: `String(100)` (UUID는 36자 + 접두사 "session-" = 44자)

**변경 필요 여부**: **❌ 변경 불필요!**

현재 `String(100)`이 올바른 타입입니다:
```python
session_id = Column(String(100), primary_key=True, index=True)  # ✅ 올바름
```

---

## 3. user_id 상세 설명

### user_id란?

**로그인한 사용자의 고유 식별자**입니다.

```python
# users 테이블의 id (Integer)
class User(Base):
    id = Column(Integer, primary_key=True, index=True)  # 1, 2, 3, ...

# 세션 생성 시 user_id 전달
await session_mgr.create_session(user_id=123)  # ← Integer로 전달해야 함
```

**특징**:
- ✅ users 테이블의 `id` (Integer 타입)
- ✅ 로그인 시에만 존재 (비로그인 시 NULL)
- ✅ Foreign Key는 설정하지 않음 (세션의 독립성 유지)
- ✅ Long-term Memory에서 과거 대화 조회 시 사용

**현재 타입**: `String(100)` ⚠️ **잘못됨!**

**올바른 타입**: `Integer`

**변경해야 하는 이유**:
```python
# 현재 (잘못됨)
sessions.user_id = Column(String(100), nullable=True)  # ❌ 문자열
users.id = Column(Integer, primary_key=True)  # ← Integer

# 수정 후 (올바름)
sessions.user_id = Column(Integer, nullable=True)  # ✅ 정수
users.id = Column(Integer, primary_key=True)  # ✅ 일치!
```

---

## 4. 실제 사용 예시

### 시나리오: 사용자 로그인 후 채팅 시작

```python
# 1. 사용자 로그인 (user_id=123)
user = await authenticate(email, password)
# user.id = 123 (Integer)

# 2. 세션 생성
session_id, expires_at = await session_mgr.create_session(
    user_id=user.id  # 123 (Integer)
)
# session_id = "session-550e8400-e29b-41d4-a716-446655440000" (String)

# 3. PostgreSQL에 저장
# sessions 테이블:
# | session_id                                   | user_id |
# |----------------------------------------------|---------|
# | "session-550e8400-e29b-41d4-a716-446655..." | 123     |  ← Integer로 저장!
```

**현재 문제**:
```sql
-- 현재 (잘못된 저장)
INSERT INTO sessions (session_id, user_id)
VALUES ('session-550e8400-...', '123');  -- user_id가 문자열 '123'으로 저장됨!

-- 수정 후 (올바른 저장)
INSERT INTO sessions (session_id, user_id)
VALUES ('session-550e8400-...', 123);  -- user_id가 정수 123으로 저장됨!
```

---

## 5. UUID로 session_id를 저장하는 것은 올바른가?

### 질문
> "session_id를 UUID로 저장하려고 했는데, 이게 맞나요?"

### 답변

**네, 완전히 올바릅니다!**

**UUID 사용 이유**:
1. ✅ **고유성 보장**: 충돌 가능성 거의 0
2. ✅ **예측 불가능**: 보안상 안전 (세션 하이재킹 방지)
3. ✅ **분산 환경**: 여러 서버에서 동시 생성해도 충돌 없음

**현재 구현 (올바름)**:
```python
# session_manager.py Line 57
session_id = f"session-{uuid.uuid4()}"
# 결과: "session-550e8400-e29b-41d4-a716-446655440000"

# 모델
session_id = Column(String(100), primary_key=True)  # ✅ 올바름
```

**대안 (PostgreSQL UUID 타입 사용)**:
```python
from sqlalchemy.dialects.postgresql import UUID
import uuid

class Session(Base):
    session_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
```

**차이점**:
- `String(100)`: 문자열 "session-550e8400-..."
- `UUID(as_uuid=True)`: 네이티브 UUID (16바이트)

**현재 방식을 유지하는 이유**:
- ✅ 접두사 "session-" 포함 가능 (가독성)
- ✅ 문자열 비교 더 직관적
- ✅ 로깅/디버깅 편리

---

## 6. 타입 불일치 요약

### ❌ 변경 불필요한 것

```python
# session_id는 그대로 유지!
session_id = Column(String(100), primary_key=True, index=True)  # ✅ 올바름
```

### ✅ 변경 필요한 것

```python
# user_id만 변경!
# BEFORE
user_id = Column(String(100), nullable=True)  # ❌ 잘못됨

# AFTER
user_id = Column(Integer, nullable=True, index=True)  # ✅ 올바름
```

---

## 7. 혼동하기 쉬운 이유

### 왜 혼동했는가?

둘 다 "ID"라는 이름이 들어가지만 **완전히 다른 개념**입니다:

| | **session_id** | **user_id** |
|---|---|---|
| **의미** | WebSocket 연결 식별자 | 사용자 식별자 |
| **생명주기** | 24시간 (일회성) | 영구 (계정 삭제 전까지) |
| **생성 방식** | UUID v4 자동 생성 | 회원가입 시 자동 증가 |
| **타입** | String (UUID) | Integer |
| **Primary Key** | sessions 테이블 | users 테이블 |
| **예시** | `"session-abc123..."` | `123` |
| **변경 여부** | ❌ 변경 불필요 | ✅ 변경 필요 |

---

## 8. 다른 테이블과의 비교

### 비슷한 ID 필드들

| 테이블 | ID 필드 | 타입 | 생성 방식 |
|--------|---------|------|-----------|
| **sessions** | session_id | String(100) | UUID v4 + 접두사 |
| **sessions** | user_id | ~~String(100)~~ → Integer | users.id 참조 |
| **users** | id | Integer | Auto Increment |
| **chat_sessions** | id | UUID | uuid.uuid4() |
| **chat_sessions** | user_id | Integer | users.id FK |
| **chat_messages** | id | UUID | uuid.uuid4() |

**패턴**:
- **Primary Key ID**: UUID 또는 Integer (테이블마다 다름)
- **user_id (FK)**: **항상 Integer** (users.id 참조)

---

## 9. 수정 체크리스트

### ✅ 수정할 곳 (user_id만)

- [ ] `backend/app/models/session.py` Line 26
  ```python
  # BEFORE
  user_id = Column(String(100), nullable=True)

  # AFTER
  user_id = Column(Integer, nullable=True, index=True)
  ```

- [ ] `backend/migrations/create_sessions_table.sql` Line 8
  ```sql
  -- BEFORE
  user_id VARCHAR(100),

  -- AFTER
  user_id INTEGER,
  ```

### ❌ 수정하지 않을 곳 (session_id)

- [ ] `session_id = Column(String(100), ...)` ← **그대로 유지!**
- [ ] `session_id = f"session-{uuid.uuid4()}"` ← **그대로 유지!**

---

## 10. 최종 올바른 테이블 구조

```python
class Session(Base):
    __tablename__ = "sessions"

    # Primary Key (UUID 기반 문자열)
    session_id = Column(String(100), primary_key=True, index=True)  # ✅ 올바름

    # User ID (정수)
    user_id = Column(Integer, nullable=True, index=True)  # ✅ 수정 후 올바름

    # Metadata
    session_metadata = Column("metadata", Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    last_activity = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Statistics
    request_count = Column(Integer, default=0, nullable=False)
```

**SQL 테이블**:
```sql
CREATE TABLE sessions (
    session_id VARCHAR(100) PRIMARY KEY,     -- ✅ UUID 문자열 (변경 불필요)
    user_id INTEGER,                         -- ✅ 정수 (수정 필요)
    metadata TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    last_activity TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    request_count INTEGER NOT NULL DEFAULT 0
);
```

---

## 요약

### 핵심 포인트

1. **session_id와 user_id는 완전히 다른 것입니다**
   - session_id: WebSocket 연결 ID (UUID 문자열)
   - user_id: 사용자 계정 ID (정수)

2. **UUID로 session_id 저장은 올바릅니다**
   - ✅ 보안성, 고유성, 분산 환경 지원
   - ✅ `String(100)` 타입 유지 권장

3. **user_id만 타입 변경이 필요합니다**
   - ❌ `String(100)` → ✅ `Integer`
   - 다른 테이블의 user_id와 일치시키기 위함

4. **session_id는 변경하지 않습니다**
   - 현재 구현이 이미 올바름

---

**다음 단계**: user_id 타입만 수정하고, session_id는 그대로 유지!

---

**Document End**
