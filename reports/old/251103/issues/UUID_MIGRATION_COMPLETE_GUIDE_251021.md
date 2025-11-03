# user_id UUID 전환 완벽 가이드

**작성일**: 2025-10-21
**목적**: 추후 UUID 전환 시 이 문서만 보고 전체 마이그레이션 수행
**예상 소요 시간**: 4-6시간 (테스트 포함)

---

## 📋 Executive Summary

### 현재 상태 (Integer)
- **users.id**: Integer (Primary Key)
- **모든 user_id**: Integer (Foreign Key)
- **하드코딩**: 1 (개발용)

### 목표 상태 (UUID)
- **users.id**: VARCHAR(36) 또는 UUID (Primary Key)
- **모든 user_id**: VARCHAR(36) 또는 UUID (Foreign Key)
- **형식**: `550e8400-e29b-41d4-a716-446655440000`

### 전환 범위
- **DB 테이블**: 5개
- **Model 파일**: 4개
- **Service 코드**: 15개 파일
- **Schema 정의**: 3개 파일
- **State 정의**: 2개 파일
- **API 엔드포인트**: 2개 파일

---

## 🎯 Phase 1: DB Schema 마이그레이션 (2시간)

### 1-1. 영향받는 테이블 목록

| 테이블명 | 컬럼명 | 현재 타입 | 변경 타입 | 관계 |
|---------|--------|-----------|----------|------|
| **users** | id | Integer PK | VARCHAR(36) PK | Primary |
| **chat_sessions** | user_id | Integer FK | VARCHAR(36) FK | → users.id |
| **user_profiles** | user_id | Integer FK | VARCHAR(36) FK | → users.id |
| **local_auths** | user_id | Integer PK FK | VARCHAR(36) PK FK | → users.id |
| **social_auths** | user_id | Integer FK | VARCHAR(36) FK | → users.id |
| **user_favorites** | user_id | Integer FK | VARCHAR(36) FK | → users.id |

**총 6개 테이블, 6개 컬럼 변경**

### 1-2. DB 마이그레이션 스크립트

```sql
-- ============================================================================
-- user_id UUID 전환 마이그레이션 스크립트
-- 실행 전 반드시 백업!
-- ============================================================================

-- Step 1: 백업 테이블 생성
CREATE TABLE users_backup AS SELECT * FROM users;
CREATE TABLE chat_sessions_backup AS SELECT * FROM chat_sessions;
CREATE TABLE user_profiles_backup AS SELECT * FROM user_profiles;
CREATE TABLE local_auths_backup AS SELECT * FROM local_auths;
CREATE TABLE social_auths_backup AS SELECT * FROM social_auths;
CREATE TABLE user_favorites_backup AS SELECT * FROM user_favorites;

-- Step 2: Foreign Key 제약 조건 제거
ALTER TABLE chat_sessions DROP CONSTRAINT IF EXISTS chat_sessions_user_id_fkey;
ALTER TABLE user_profiles DROP CONSTRAINT IF EXISTS user_profiles_user_id_fkey;
ALTER TABLE local_auths DROP CONSTRAINT IF EXISTS local_auths_user_id_fkey;
ALTER TABLE social_auths DROP CONSTRAINT IF EXISTS social_auths_user_id_fkey;
ALTER TABLE user_favorites DROP CONSTRAINT IF EXISTS user_favorites_user_id_fkey;

-- Step 3: 임시 매핑 테이블 생성 (Integer → UUID)
CREATE TABLE user_id_mapping (
    old_id INTEGER PRIMARY KEY,
    new_id VARCHAR(36) NOT NULL UNIQUE
);

-- 기존 데이터를 UUID로 매핑
INSERT INTO user_id_mapping (old_id, new_id)
SELECT id, gen_random_uuid()::VARCHAR(36)
FROM users;

-- Step 4: users 테이블 변경
-- 4-1. 새 컬럼 추가
ALTER TABLE users ADD COLUMN new_id VARCHAR(36);

-- 4-2. UUID 값 채우기
UPDATE users u
SET new_id = m.new_id
FROM user_id_mapping m
WHERE u.id = m.old_id;

-- 4-3. 기존 PK 제거
ALTER TABLE users DROP CONSTRAINT users_pkey;

-- 4-4. 기존 id 컬럼 삭제 및 new_id를 id로 변경
ALTER TABLE users DROP COLUMN id;
ALTER TABLE users RENAME COLUMN new_id TO id;

-- 4-5. 새 PK 설정
ALTER TABLE users ADD PRIMARY KEY (id);

-- Step 5: chat_sessions 테이블 변경
ALTER TABLE chat_sessions ADD COLUMN new_user_id VARCHAR(36);

UPDATE chat_sessions cs
SET new_user_id = m.new_id
FROM user_id_mapping m
WHERE cs.user_id = m.old_id;

ALTER TABLE chat_sessions DROP COLUMN user_id;
ALTER TABLE chat_sessions RENAME COLUMN new_user_id TO user_id;
ALTER TABLE chat_sessions ALTER COLUMN user_id SET NOT NULL;

-- Step 6: user_profiles 테이블 변경
ALTER TABLE user_profiles ADD COLUMN new_user_id VARCHAR(36);

UPDATE user_profiles up
SET new_user_id = m.new_id
FROM user_id_mapping m
WHERE up.user_id = m.old_id;

ALTER TABLE user_profiles DROP COLUMN user_id;
ALTER TABLE user_profiles RENAME COLUMN new_user_id TO user_id;
ALTER TABLE user_profiles ALTER COLUMN user_id SET NOT NULL;

-- Step 7: local_auths 테이블 변경
ALTER TABLE local_auths ADD COLUMN new_user_id VARCHAR(36);

UPDATE local_auths la
SET new_user_id = m.new_id
FROM user_id_mapping m
WHERE la.user_id = m.old_id;

ALTER TABLE local_auths DROP CONSTRAINT local_auths_pkey;
ALTER TABLE local_auths DROP COLUMN user_id;
ALTER TABLE local_auths RENAME COLUMN new_user_id TO user_id;
ALTER TABLE local_auths ADD PRIMARY KEY (user_id);

-- Step 8: social_auths 테이블 변경
ALTER TABLE social_auths ADD COLUMN new_user_id VARCHAR(36);

UPDATE social_auths sa
SET new_user_id = m.new_id
FROM user_id_mapping m
WHERE sa.user_id = m.old_id;

ALTER TABLE social_auths DROP COLUMN user_id;
ALTER TABLE social_auths RENAME COLUMN new_user_id TO user_id;
ALTER TABLE social_auths ALTER COLUMN user_id SET NOT NULL;

-- Step 9: user_favorites 테이블 변경
ALTER TABLE user_favorites ADD COLUMN new_user_id VARCHAR(36);

UPDATE user_favorites uf
SET new_user_id = m.new_id
FROM user_id_mapping m
WHERE uf.user_id = m.old_id;

ALTER TABLE user_favorites DROP COLUMN user_id;
ALTER TABLE user_favorites RENAME COLUMN new_user_id TO user_id;
ALTER TABLE user_favorites ALTER COLUMN user_id SET NOT NULL;

-- Step 10: Foreign Key 재생성
ALTER TABLE chat_sessions
ADD CONSTRAINT chat_sessions_user_id_fkey
FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

ALTER TABLE user_profiles
ADD CONSTRAINT user_profiles_user_id_fkey
FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

ALTER TABLE local_auths
ADD CONSTRAINT local_auths_user_id_fkey
FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

ALTER TABLE social_auths
ADD CONSTRAINT social_auths_user_id_fkey
FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

ALTER TABLE user_favorites
ADD CONSTRAINT user_favorites_user_id_fkey
FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

-- Step 11: 인덱스 재생성
CREATE INDEX IF NOT EXISTS idx_chat_sessions_user_id ON chat_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_user_profiles_user_id ON user_profiles(user_id);
CREATE INDEX IF NOT EXISTS idx_social_auths_user_id ON social_auths(user_id);
CREATE INDEX IF NOT EXISTS idx_user_favorites_user_id ON user_favorites(user_id);

-- Step 12: 검증
SELECT
    'users' as table_name,
    pg_typeof(id) as id_type,
    COUNT(*) as row_count
FROM users
UNION ALL
SELECT
    'chat_sessions',
    pg_typeof(user_id),
    COUNT(*)
FROM chat_sessions
UNION ALL
SELECT
    'user_profiles',
    pg_typeof(user_id),
    COUNT(*)
FROM user_profiles;

-- 모든 타입이 "character varying"으로 나와야 함

-- Step 13: 매핑 테이블 보관 (롤백용)
-- DROP TABLE user_id_mapping; -- 나중에 삭제

-- 롤백 시:
-- 1. 백업 테이블에서 원본 복원
-- 2. 애플리케이션 재시작
```

### 1-3. 롤백 스크립트

```sql
-- ============================================================================
-- 롤백 스크립트 (문제 발생 시)
-- ============================================================================

-- 모든 테이블을 백업에서 복원
DROP TABLE IF EXISTS users CASCADE;
DROP TABLE IF EXISTS chat_sessions CASCADE;
DROP TABLE IF EXISTS user_profiles CASCADE;
DROP TABLE IF EXISTS local_auths CASCADE;
DROP TABLE IF EXISTS social_auths CASCADE;
DROP TABLE IF EXISTS user_favorites CASCADE;

CREATE TABLE users AS SELECT * FROM users_backup;
CREATE TABLE chat_sessions AS SELECT * FROM chat_sessions_backup;
CREATE TABLE user_profiles AS SELECT * FROM user_profiles_backup;
CREATE TABLE local_auths AS SELECT * FROM local_auths_backup;
CREATE TABLE social_auths AS SELECT * FROM social_auths_backup;
CREATE TABLE user_favorites AS SELECT * FROM user_favorites_backup;

-- PK/FK 재생성
ALTER TABLE users ADD PRIMARY KEY (id);
ALTER TABLE chat_sessions ADD CONSTRAINT chat_sessions_user_id_fkey
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
-- ... (나머지 FK들)
```

---

## 🔧 Phase 2: Model 파일 수정 (30분)

### 2-1. app/models/users.py

**변경 전**:
```python
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)  # ← 변경
    email = Column(String(200), unique=True, nullable=False, index=True)
    # ...

class LocalAuth(Base):
    __tablename__ = "local_auths"
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)  # ← 변경
    # ...

class UserProfile(Base):
    __tablename__ = "user_profiles"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)  # ← 변경
    # ...

class SocialAuth(Base):
    __tablename__ = "social_auths"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # ← 변경
    # ...

class UserFavorite(Base):
    __tablename__ = "user_favorites"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # ← 변경
    # ...
```

**변경 후**:
```python
class User(Base):
    __tablename__ = "users"
    id = Column(String(36), primary_key=True, index=True)  # ✅ Integer → String(36)
    email = Column(String(200), unique=True, nullable=False, index=True)
    # ...

class LocalAuth(Base):
    __tablename__ = "local_auths"
    user_id = Column(String(36), ForeignKey("users.id"), primary_key=True)  # ✅ Integer → String(36)
    # ...

class UserProfile(Base):
    __tablename__ = "user_profiles"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), unique=True, nullable=False)  # ✅ Integer → String(36)
    # ...

class SocialAuth(Base):
    __tablename__ = "social_auths"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)  # ✅ Integer → String(36)
    # ...

class UserFavorite(Base):
    __tablename__ = "user_favorites"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)  # ✅ Integer → String(36)
    # ...
```

### 2-2. app/models/chat.py

**변경 전**:
```python
class ChatSession(Base):
    __tablename__ = "chat_sessions"

    session_id = Column(String(100), primary_key=True)
    user_id = Column(
        Integer,  # ← 변경
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
```

**변경 후**:
```python
class ChatSession(Base):
    __tablename__ = "chat_sessions"

    session_id = Column(String(100), primary_key=True)
    user_id = Column(
        String(36),  # ✅ Integer → String(36)
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
```

---

## 💻 Phase 3: Service 코드 수정 (1시간 30분)

### 3-1. app/service_agent/foundation/separated_states.py

**변경 전**:
```python
class SharedState(TypedDict):
    user_query: str
    session_id: str
    user_id: Optional[int]  # ← 변경
    timestamp: str
    # ...

class MainSupervisorState(TypedDict, total=False):
    # ...
    user_id: Optional[int]  # ← 변경
    # ...

def create_main_supervisor_state(
    # ...
    user_id: Optional[int] = None,  # ← 변경
    # ...
) -> MainSupervisorState:
```

**변경 후**:
```python
class SharedState(TypedDict):
    user_query: str
    session_id: str
    user_id: Optional[str]  # ✅ int → str
    timestamp: str
    # ...

class MainSupervisorState(TypedDict, total=False):
    # ...
    user_id: Optional[str]  # ✅ int → str
    # ...

def create_main_supervisor_state(
    # ...
    user_id: Optional[str] = None,  # ✅ int → str
    # ...
) -> MainSupervisorState:
```

### 3-2. app/service_agent/foundation/simple_memory_service.py

**변경 전**:
```python
async def load_recent_memories(
    self,
    user_id: str,  # 현재 이미 str (일관성 없음)
    limit: int = 5,
    relevance_filter: str = "ALL",
    session_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """최근 메모리 로드"""
    # 타입 변환 로직 제거 가능
    query = select(ChatSession).where(
        ChatSession.user_id == user_id,  # String 비교
        # ...
    )
```

**변경 후**:
```python
async def load_recent_memories(
    self,
    user_id: str,  # ✅ 그대로 유지 (이미 str)
    limit: int = 5,
    relevance_filter: str = "ALL",
    session_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """최근 메모리 로드"""
    # UUID 형식 검증 추가 (선택)
    if not is_valid_uuid(user_id):
        logger.warning(f"Invalid UUID format: {user_id}")
        return []

    query = select(ChatSession).where(
        ChatSession.user_id == user_id,  # UUID String 비교
        # ...
    )
```

### 3-3. app/service_agent/foundation/context.py

**변경 전**:
```python
class AgentContext(TypedDict):
    # ...
    db_user_id: Optional[int]  # ← 변경
    # ...

class ExecutionContext(TypedDict, total=False):
    # ...
    db_user_id: Optional[int]  # ← 변경
    # ...

async def create_execution_context(
    # ...
    db_user_id: int = None,  # ← 변경
    # ...
) -> ExecutionContext:

def validate_agent_context(
    context: AgentContext,
    db_user_id: int,  # ← 변경
    # ...
):
    if not isinstance(context["db_user_id"], int):  # ← 변경
        raise ValueError(f"db_user_id must be integer, got {type(context['db_user_id'])}")
```

**변경 후**:
```python
class AgentContext(TypedDict):
    # ...
    db_user_id: Optional[str]  # ✅ int → str
    # ...

class ExecutionContext(TypedDict, total=False):
    # ...
    db_user_id: Optional[str]  # ✅ int → str
    # ...

async def create_execution_context(
    # ...
    db_user_id: str = None,  # ✅ int → str
    # ...
) -> ExecutionContext:

def validate_agent_context(
    context: AgentContext,
    db_user_id: str,  # ✅ int → str
    # ...
):
    if not isinstance(context["db_user_id"], str):  # ✅ int → str
        raise ValueError(f"db_user_id must be string UUID, got {type(context['db_user_id'])}")
```

### 3-4. app/service_agent/cognitive_agents/execution_orchestrator.py

**변경 전**:
```python
async def _load_user_patterns(self, user_id: int):  # ← 변경
    """사용자 패턴 로드"""
    pass

async def execute(
    # ...
    user_id: int,  # ← 변경
    # ...
):
```

**변경 후**:
```python
async def _load_user_patterns(self, user_id: str):  # ✅ int → str
    """사용자 패턴 로드"""
    pass

async def execute(
    # ...
    user_id: str,  # ✅ int → str
    # ...
):
```

### 3-5. app/service_agent/supervisor/team_supervisor.py

**변경 전**:
```python
async def run_supervisor(
    # ...
    user_id: Optional[int] = None,  # ← 변경
    # ...
):
```

**변경 후**:
```python
async def run_supervisor(
    # ...
    user_id: Optional[str] = None,  # ✅ int → str
    # ...
):
```

---

## 📄 Phase 4: Schema 파일 수정 (20분)

### 4-1. app/schemas/users.py

**변경 전**:
```python
class LocalAuthCreate(BaseModel):
    user_id: int  # ← 변경
    hashed_password: str

class UserProfileCreate(BaseModel):
    user_id: int  # ← 변경
    nickname: str
    # ...

class SocialAuthCreate(BaseModel):
    user_id: int  # ← 변경
    provider: str
    # ...

class UserFavoriteCreate(BaseModel):
    user_id: int  # ← 변경
    real_estate_id: int
```

**변경 후**:
```python
class LocalAuthCreate(BaseModel):
    user_id: str  # ✅ int → str (UUID)
    hashed_password: str

class UserProfileCreate(BaseModel):
    user_id: str  # ✅ int → str (UUID)
    nickname: str
    # ...

class SocialAuthCreate(BaseModel):
    user_id: str  # ✅ int → str (UUID)
    provider: str
    # ...

class UserFavoriteCreate(BaseModel):
    user_id: str  # ✅ int → str (UUID)
    real_estate_id: int
```

### 4-2. app/schemas/chat.py

**변경 전**:
```python
class CreateChatSessionRequest(BaseModel):
    user_id: int = Field(..., description="사용자 ID")  # ← 변경
    # ...

class ChatRequest(BaseModel):
    user_id: int = Field(..., description="사용자 ID")  # ← 변경
    # ...
```

**변경 후**:
```python
class CreateChatSessionRequest(BaseModel):
    user_id: str = Field(..., description="사용자 ID (UUID)")  # ✅ int → str
    # ...

class ChatRequest(BaseModel):
    user_id: str = Field(..., description="사용자 ID (UUID)")  # ✅ int → str
    # ...
```

---

## 🌐 Phase 5: API 엔드포인트 수정 (30분)

### 5-1. app/api/chat_api.py

**변경 전**:
```python
# Line 141
user_id=request.user_id or 1,  # ← Integer

# Line 235
user_id = 1  # 임시 하드코딩  # ← Integer

# Line 299
user_id = 1  # 임시 하드코딩  # ← Integer

# Line 772
user_id = 1  # 테스트용 하드코딩  # ← Integer

# Line 885
user_id = 1  # 테스트용 하드코딩  # ← Integer
```

**변경 후**:
```python
import uuid
from app.core.config import settings

# 설정 파일에 DEFAULT_USER_UUID 추가
# config.py:
# DEFAULT_USER_UUID: str = "00000000-0000-0000-0000-000000000001"

# Line 141
user_id=request.user_id or settings.DEFAULT_USER_UUID,  # ✅ UUID String

# Line 235
user_id = settings.DEFAULT_USER_UUID  # ✅ UUID String

# Line 299
user_id = settings.DEFAULT_USER_UUID  # ✅ UUID String

# Line 772
user_id = settings.DEFAULT_USER_UUID  # ✅ UUID String

# Line 885
user_id = settings.DEFAULT_USER_UUID  # ✅ UUID String

# 또는 JWT에서 추출
def get_current_user_id(request: Request) -> str:
    """JWT에서 user_id 추출"""
    if hasattr(request.state, "user_id"):
        return request.state.user_id  # UUID String
    return settings.DEFAULT_USER_UUID
```

### 5-2. app/api/postgres_session_manager.py

**변경 전**:
```python
async def create_postgres_saver(
    user_id: Optional[int] = None,  # ← 변경
    session_id: Optional[str] = None,
):
    user_id = user_id or 1  # 기본값: 1  # ← Integer
```

**변경 후**:
```python
from app.core.config import settings

async def create_postgres_saver(
    user_id: Optional[str] = None,  # ✅ int → str
    session_id: Optional[str] = None,
):
    user_id = user_id or settings.DEFAULT_USER_UUID  # ✅ UUID String
```

---

## ⚙️ Phase 6: 설정 파일 수정 (10분)

### 6-1. app/core/config.py

**추가**:
```python
class Settings(BaseSettings):
    # ... 기존 설정들 ...

    # UUID 기본값 (인증 미구현 시)
    DEFAULT_USER_UUID: str = Field(
        default="00000000-0000-0000-0000-000000000001",
        description="인증 미구현 시 사용할 기본 user_id (UUID 형식)"
    )
```

### 6-2. .env

**추가**:
```bash
# User ID 설정 (UUID 형식)
DEFAULT_USER_UUID=00000000-0000-0000-0000-000000000001
```

---

## 🧪 Phase 7: 테스트 (1시간)

### 7-1. 단위 테스트

```python
# tests/test_uuid_migration.py
import pytest
import uuid

def test_user_id_is_valid_uuid():
    """user_id가 유효한 UUID인지 확인"""
    from app.core.config import settings

    user_id = settings.DEFAULT_USER_UUID
    assert isinstance(user_id, str)
    assert len(user_id) == 36

    # UUID 형식 검증
    try:
        uuid.UUID(user_id)
    except ValueError:
        pytest.fail("Invalid UUID format")

@pytest.mark.asyncio
async def test_load_memories_with_uuid():
    """UUID user_id로 메모리 로드 테스트"""
    from app.service_agent.foundation.simple_memory_service import SimpleMemoryService

    service = SimpleMemoryService(db_session)

    # UUID로 조회
    user_id = "550e8400-e29b-41d4-a716-446655440000"
    memories = await service.load_recent_memories(user_id=user_id, limit=5)

    assert isinstance(memories, list)

@pytest.mark.asyncio
async def test_db_user_id_type():
    """DB에 저장된 user_id 타입 확인"""
    from sqlalchemy import select, text

    # users 테이블 타입 확인
    result = await db_session.execute(
        text("SELECT pg_typeof(id) FROM users LIMIT 1")
    )
    type_name = result.scalar()
    assert type_name == "character varying"  # VARCHAR

    # chat_sessions 테이블 타입 확인
    result = await db_session.execute(
        text("SELECT pg_typeof(user_id) FROM chat_sessions LIMIT 1")
    )
    type_name = result.scalar()
    assert type_name == "character varying"  # VARCHAR
```

### 7-2. 통합 테스트 체크리스트

- [ ] **DB 마이그레이션 성공 확인**
  ```sql
  SELECT table_name, column_name, data_type
  FROM information_schema.columns
  WHERE column_name = 'user_id' OR column_name = 'id' AND table_name IN ('users', 'chat_sessions', 'user_profiles', 'local_auths', 'social_auths', 'user_favorites');
  ```

- [ ] **Foreign Key 제약 확인**
  ```sql
  SELECT * FROM information_schema.table_constraints
  WHERE constraint_type = 'FOREIGN KEY'
  AND table_name IN ('chat_sessions', 'user_profiles', 'local_auths', 'social_auths', 'user_favorites');
  ```

- [ ] **인덱스 확인**
  ```sql
  SELECT * FROM pg_indexes
  WHERE tablename IN ('users', 'chat_sessions', 'user_profiles');
  ```

- [ ] **API 테스트 - 세션 생성**
  ```bash
  curl -X POST http://localhost:8000/chat/sessions \
    -H "Content-Type: application/json" \
    -d '{
      "user_id": "550e8400-e29b-41d4-a716-446655440000",
      "title": "테스트 세션"
    }'
  ```

- [ ] **API 테스트 - 메모리 로드**
  ```bash
  curl -X GET "http://localhost:8000/chat/memories?user_id=550e8400-e29b-41d4-a716-446655440000"
  ```

- [ ] **Long-term Memory 동작 확인**
  - 이전 대화 로드 정상 작동
  - UUID로 세션 필터링 정상
  - 메모리 요약 저장/로드 정상

- [ ] **성능 테스트**
  - UUID 인덱스 활용 확인
  - 쿼리 실행 계획 검증
  - 응답 시간 측정

---

## 📋 전체 체크리스트

### Phase 1: DB Schema (2시간)
- [ ] DB 백업 생성
- [ ] 마이그레이션 스크립트 실행
- [ ] users 테이블 변경 확인
- [ ] chat_sessions 테이블 변경 확인
- [ ] user_profiles 테이블 변경 확인
- [ ] local_auths 테이블 변경 확인
- [ ] social_auths 테이블 변경 확인
- [ ] user_favorites 테이블 변경 확인
- [ ] Foreign Key 재생성 확인
- [ ] 인덱스 재생성 확인
- [ ] 데이터 무결성 검증

### Phase 2: Models (30분)
- [ ] app/models/users.py (5곳 수정)
- [ ] app/models/chat.py (1곳 수정)

### Phase 3: Services (1시간 30분)
- [ ] app/service_agent/foundation/separated_states.py (4곳 수정)
- [ ] app/service_agent/foundation/simple_memory_service.py (검증 추가)
- [ ] app/service_agent/foundation/context.py (6곳 수정)
- [ ] app/service_agent/cognitive_agents/execution_orchestrator.py (2곳 수정)
- [ ] app/service_agent/supervisor/team_supervisor.py (1곳 수정)

### Phase 4: Schemas (20분)
- [ ] app/schemas/users.py (4곳 수정)
- [ ] app/schemas/chat.py (2곳 수정)

### Phase 5: API (30분)
- [ ] app/api/chat_api.py (5곳 수정)
- [ ] app/api/postgres_session_manager.py (2곳 수정)

### Phase 6: Config (10분)
- [ ] app/core/config.py (DEFAULT_USER_UUID 추가)
- [ ] .env (DEFAULT_USER_UUID 추가)

### Phase 7: 테스트 (1시간)
- [ ] 단위 테스트 작성 및 실행
- [ ] DB 타입 검증
- [ ] API 엔드포인트 테스트
- [ ] Long-term Memory 테스트
- [ ] 성능 테스트

### Phase 8: 배포 (30분)
- [ ] 스테이징 환경 배포
- [ ] 통합 테스트
- [ ] 롤백 계획 검증
- [ ] 프로덕션 배포

---

## ⚠️ 주의사항

### 1. 데이터 손실 방지
- **반드시 백업 생성**: 모든 테이블 백업 후 진행
- **롤백 계획 준비**: 문제 발생 시 즉시 롤백 가능하도록
- **트랜잭션 사용**: 가능한 모든 작업을 단일 트랜잭션으로

### 2. 다운타임 최소화
- **점검 시간 공지**: 사용자에게 사전 공지
- **예상 시간**: 2-3시간 (테스트 포함)
- **빠른 롤백**: 문제 발생 시 5분 내 롤백

### 3. 성능 검증
- **인덱스 재생성**: VARCHAR 컬럼도 인덱스 효율적
- **쿼리 플랜 확인**: EXPLAIN ANALYZE로 성능 검증
- **부하 테스트**: 실제 트래픽 시뮬레이션

### 4. 호환성
- **하위 호환성 없음**: Integer user_id는 작동 안 함
- **일괄 전환 필요**: 모든 시스템을 동시에 전환
- **JWT 토큰 갱신**: 기존 토큰 무효화 필요

---

## 🔄 롤백 절차

### 문제 발생 시 즉시 실행

```bash
# Step 1: 애플리케이션 중지
sudo systemctl stop holmesnyangz-backend

# Step 2: DB 롤백 (위의 롤백 스크립트 실행)
psql -U postgres -d real_estate -f rollback.sql

# Step 3: 코드 롤백
git checkout <이전_커밋>

# Step 4: 애플리케이션 재시작
sudo systemctl start holmesnyangz-backend

# Step 5: 검증
curl http://localhost:8000/health
```

---

## 📊 예상 소요 시간

| Phase | 작업 | 예상 시간 | 누적 시간 |
|-------|------|-----------|-----------|
| 1 | DB Schema 마이그레이션 | 2시간 | 2시간 |
| 2 | Models 수정 | 30분 | 2시간 30분 |
| 3 | Services 수정 | 1시간 30분 | 4시간 |
| 4 | Schemas 수정 | 20분 | 4시간 20분 |
| 5 | API 수정 | 30분 | 4시간 50분 |
| 6 | Config 수정 | 10분 | 5시간 |
| 7 | 테스트 | 1시간 | 6시간 |
| 8 | 배포 | 30분 | 6시간 30분 |

**총 예상 시간**: 6시간 30분

---

## 📝 마이그레이션 완료 후 확인 사항

### ✅ 성공 기준

1. **DB 검증**
   - [ ] 모든 user_id 컬럼이 VARCHAR(36)
   - [ ] Foreign Key 정상 작동
   - [ ] 데이터 손실 없음

2. **코드 검증**
   - [ ] 모든 타입이 `str`로 통일
   - [ ] 컴파일 에러 없음
   - [ ] 타입 체크 통과

3. **기능 검증**
   - [ ] 새 사용자 생성 (UUID)
   - [ ] 세션 생성/조회 정상
   - [ ] Long-term Memory 정상 작동
   - [ ] API 모든 엔드포인트 정상

4. **성능 검증**
   - [ ] 쿼리 성능 저하 없음
   - [ ] 인덱스 활용 확인
   - [ ] 응답 시간 동일

---

## 🎯 결론

이 문서를 따라 진행하면:
- ✅ **Integer → UUID 완벽 전환**
- ✅ **데이터 손실 없음**
- ✅ **롤백 가능**
- ✅ **예상 시간: 6시간 30분**

**다음 단계**:
1. 이 문서를 버전 관리 시스템에 커밋
2. UUID 전환 필요 시 이 문서만 참고
3. 단계별로 체크하며 진행

---

**작성 완료**: 2025-10-21
**업데이트 필요 시**: UUID 전환 직전