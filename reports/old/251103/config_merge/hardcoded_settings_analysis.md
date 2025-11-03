# 하드코딩된 설정 분석 및 마이그레이션 권장사항

**작성일**: 2025-10-14
**작성자**: Claude Code
**목적**: 코드베이스 전체를 스캔하여 하드코딩된 설정을 찾고 config 파일로 이동 권장

---

## 📋 Executive Summary

### 발견된 하드코딩 설정:

| 설정 항목 | 현재 위치 | 현재 값 | 이동 권장 | 우선순위 |
|----------|---------|---------|----------|----------|
| **user_id (임시)** | chat_api.py:345 | `1` | ❌ 로그인 구현 시 제거 | Low |
| **session_ttl_hours** | session_manager.py:261 | `24` | ✅ core/config | High |
| **MEMORY_LOAD_LIMIT** | team_supervisor.py:212 | `5` | ✅ core/config | Medium |
| **ENTITY_HISTORY_LIMIT** | long_term_memory_service.py:239 | `10` | ✅ core/config | Low |

### 권장 조치:

✅ **즉시 수행 (High Priority)**:
- session_ttl_hours 하드코딩 제거

⚠️ **선택적 수행 (Medium Priority)**:
- Memory 로드 limit 설정 추가

❌ **수행 불필요 (Low Priority)**:
- user_id=1은 로그인 구현 시 자동 제거됨
- Entity history limit은 내부 메서드에서만 사용

---

## 1. 발견된 하드코딩 설정 상세

### 1.1 session_ttl_hours (High Priority) ⚠️

**파일**: `backend/app/api/session_manager.py`
**라인**: 261

#### 현재 코드:
```python
def get_session_manager() -> SessionManager:
    global _session_manager

    if _session_manager is None:
        _session_manager = SessionManager(session_ttl_hours=24)  # ⚠️ 하드코딩

    return _session_manager
```

#### 문제점:
- ❌ 세션 만료 시간이 코드에 하드코딩됨
- ❌ 환경별 (개발/프로덕션) 다른 TTL 설정 불가능
- ❌ .env 파일로 관리 불가능

#### 해결 방법:
```python
# backend/app/api/session_manager.py
from app.core.config import settings

def get_session_manager() -> SessionManager:
    global _session_manager

    if _session_manager is None:
        _session_manager = SessionManager(
            session_ttl_hours=settings.SESSION_TTL_HOURS  # ✅ 중앙화된 설정 사용
        )

    return _session_manager
```

#### 장점:
- ✅ .env 파일로 TTL 제어 가능
- ✅ 환경별 설정 분리 용이
- ✅ 프로덕션 환경에서 48시간 등으로 쉽게 변경

#### 현재 상태:
- **core/config.py**: `SESSION_TTL_HOURS: int = 24` 이미 정의됨 ✅
- **session_manager.py**: 하드코딩 사용 중 ❌

**우선순위**: High ⚠️
**추정 작업 시간**: 2분
**변경 범위**: 1개 파일, 1줄 수정

---

### 1.2 Memory Load Limit (Medium Priority)

**파일**: `backend/app/service_agent/supervisor/team_supervisor.py`
**라인**: 212

#### 현재 코드:
```python
# 최근 대화 기록 로드 (RELEVANT만)
loaded_memories = await memory_service.load_recent_memories(
    user_id=user_id,
    limit=5,  # ⚠️ 하드코딩
    relevance_filter="RELEVANT"
)
```

#### 문제점:
- ⚠️ Memory 로드 개수가 코드에 하드코딩됨
- ⚠️ 사용자 경험 조정 시 코드 수정 필요

#### 해결 방법:
```python
# core/config.py에 추가
class Settings(BaseSettings):
    # ...
    MEMORY_LOAD_LIMIT: int = 5  # 기본값 5개
```

```python
# team_supervisor.py 수정
from app.core.config import settings

loaded_memories = await memory_service.load_recent_memories(
    user_id=user_id,
    limit=settings.MEMORY_LOAD_LIMIT,  # ✅ 설정 사용
    relevance_filter="RELEVANT"
)
```

#### 장점:
- ✅ .env 파일로 Memory 로드 개수 제어
- ✅ 서버 리소스에 맞춰 조정 가능

#### 현재 상태:
- **core/config.py**: 아직 정의 안 됨 ❌
- **team_supervisor.py**: 하드코딩 사용 중 ❌

**우선순위**: Medium
**추정 작업 시간**: 3분
**변경 범위**: 2개 파일, 2줄 추가/수정

---

### 1.3 user_id 임시 하드코딩 (Low Priority - 제거 예정)

**파일**: `backend/app/api/chat_api.py`
**라인**: 345

#### 현재 코드:
```python
# 세션에서 user_id 추출 (Long-term Memory용)
user_id = 1  # 🔧 임시: 테스트용 하드코딩
session_data = await session_mgr.get_session(session_id)
if session_data:
    if user_id:
        logger.info(f"User ID {user_id} extracted from session {session_id}")
```

#### 상태:
- ✅ **의도적인 임시 하드코딩** (테스트용)
- ✅ 로그인 기능 구현 시 자동으로 제거 예정
- ✅ 주석으로 명시되어 있음

#### 조치:
- ❌ 지금 수정 불필요
- ✅ 로그인 구현 시 자연스럽게 제거됨

**우선순위**: Low (현재 조치 불필요)
**추정 작업 시간**: 로그인 구현 시 자동 해결

---

### 1.4 Entity History Limit (Low Priority)

**파일**: `backend/app/services/long_term_memory_service.py`
**라인**: 239

#### 현재 코드:
```python
async def get_entity_history(
    self,
    user_id: int,
    entity_type: Optional[str] = None,
    limit: int = 10  # ⚠️ 하드코딩 (파라미터 기본값)
) -> List[Dict[str, Any]]:
```

#### 상태:
- ✅ **함수 파라미터 기본값** (유연함)
- ✅ 호출 시 다른 값으로 오버라이드 가능
- ✅ 내부 메서드로 사용 빈도 낮음

#### 판단:
- ❌ 이동 불필요 (함수 시그니처가 더 직관적)
- ✅ 파라미터로 충분히 유연함

**우선순위**: Low (현재 조치 불필요)

---

## 2. 이미 올바르게 중앙화된 설정 ✅

### 2.1 PostgreSQL 연결 (완료) ✅

**파일**: `backend/app/service_agent/supervisor/team_supervisor.py:784-785`

```python
from app.core.config import settings

DB_URI = settings.postgres_url  # ✅ 중앙화 완료 (2025-10-14)
```

**상태**: ✅ 완료 (2025-10-14)

---

### 2.2 Session/Memory 설정 (완료) ✅

**파일**: `backend/app/core/config.py:24-26`

```python
SESSION_TTL_HOURS: int = 24  # ✅ 정의됨
MEMORY_RETENTION_DAYS: int = 90  # ✅ 정의됨
MEMORY_LIMIT_PER_USER: int = 100  # ✅ 정의됨
```

**상태**: ✅ 정의 완료 (사용 대기 중)

---

## 3. 마이그레이션 로드맵

### Phase 1: High Priority (즉시 수행) ⚠️

#### Task 1.1: session_ttl_hours 하드코딩 제거

**파일**: `backend/app/api/session_manager.py:261`

**변경 전**:
```python
_session_manager = SessionManager(session_ttl_hours=24)
```

**변경 후**:
```python
from app.core.config import settings

_session_manager = SessionManager(session_ttl_hours=settings.SESSION_TTL_HOURS)
```

**추정 시간**: 2분
**테스트**: 백엔드 재시작 후 세션 생성 확인

---

### Phase 2: Medium Priority (선택사항)

#### Task 2.1: MEMORY_LOAD_LIMIT 추가

**파일 1**: `backend/app/core/config.py`

**추가**:
```python
# Session & Memory Configuration
SESSION_TTL_HOURS: int = 24
MEMORY_RETENTION_DAYS: int = 90
MEMORY_LIMIT_PER_USER: int = 100
MEMORY_LOAD_LIMIT: int = 5  # NEW: 로드할 최근 대화 개수
```

**파일 2**: `backend/app/service_agent/supervisor/team_supervisor.py:212`

**변경 전**:
```python
loaded_memories = await memory_service.load_recent_memories(
    user_id=user_id,
    limit=5,
    relevance_filter="RELEVANT"
)
```

**변경 후**:
```python
from app.core.config import settings

loaded_memories = await memory_service.load_recent_memories(
    user_id=user_id,
    limit=settings.MEMORY_LOAD_LIMIT,
    relevance_filter="RELEVANT"
)
```

**추정 시간**: 3분
**테스트**: Memory 로딩 동작 확인

---

### Phase 3: Low Priority (조치 불필요) ✅

- ❌ user_id=1 임시 하드코딩: 로그인 구현 시 자동 제거
- ❌ Entity history limit: 파라미터 기본값으로 충분

---

## 4. 액션 아이템 체크리스트

### 즉시 수행 (High Priority):

- [ ] **Task 1.1**: session_manager.py의 session_ttl_hours 하드코딩 제거
  - File: `backend/app/api/session_manager.py:261`
  - Change: `session_ttl_hours=24` → `session_ttl_hours=settings.SESSION_TTL_HOURS`
  - Time: 2분

### 선택적 수행 (Medium Priority):

- [ ] **Task 2.1**: MEMORY_LOAD_LIMIT 설정 추가
  - File 1: `backend/app/core/config.py` - 설정 추가
  - File 2: `backend/app/service_agent/supervisor/team_supervisor.py:212` - 사용
  - Time: 3분

### 수행 불필요 (Low Priority):

- [x] user_id=1 임시 하드코딩: 로그인 구현 시 자동 제거 예정
- [x] Entity history limit: 파라미터 기본값으로 충분

---

## 5. 변경 후 예상 효과

### High Priority 변경 후:

**장점**:
- ✅ 세션 TTL을 .env 파일로 제어 가능
- ✅ 개발 환경: 1시간, 프로덕션: 48시간 등 환경별 설정 가능
- ✅ 코드 수정 없이 세션 정책 변경 가능

**예시**:
```bash
# .env 파일
SESSION_TTL_HOURS=48  # 프로덕션: 48시간
# SESSION_TTL_HOURS=1  # 개발: 1시간 (테스트 용이)
```

---

### Medium Priority 변경 후:

**장점**:
- ✅ Memory 로드 개수를 .env 파일로 제어
- ✅ 서버 리소스에 따라 조정 가능 (저사양: 3개, 고사양: 10개)

**예시**:
```bash
# .env 파일
MEMORY_LOAD_LIMIT=10  # 고사양 서버
# MEMORY_LOAD_LIMIT=3  # 저사양 서버
```

---

## 6. 트레이드오프 분석

### High Priority (session_ttl_hours)

#### 변경하는 경우:
- ✅ 환경별 설정 가능
- ✅ 유지보수 용이
- ⚠️ 1개 파일 수정 필요 (2분)

#### 변경하지 않는 경우:
- ❌ 환경별 설정 불가능
- ❌ TTL 변경 시 코드 수정 필수
- ✅ 현재 동작에는 문제 없음

**권장**: ✅ 변경 권장 (2분 투자로 큰 유연성 확보)

---

### Medium Priority (MEMORY_LOAD_LIMIT)

#### 변경하는 경우:
- ✅ Memory 로드 개수 조정 가능
- ✅ 서버 리소스 최적화
- ⚠️ 2개 파일 수정 필요 (3분)

#### 변경하지 않는 경우:
- ⚠️ Memory 로드 개수 고정 (5개)
- ⚠️ 조정 시 코드 수정 필요
- ✅ 현재 동작에는 문제 없음

**권장**: ⚠️ 선택사항 (현재 5개로 충분하다면 불필요)

---

## 7. 최종 권장사항

### ✅ 즉시 수행 (High Priority):

**Task 1.1: session_ttl_hours 하드코딩 제거**
- **이유**: 환경별 설정 필요성 높음
- **시간**: 2분
- **위험도**: 낮음 (기존 동작 유지)

---

### ⚠️ 선택적 수행 (Medium Priority):

**Task 2.1: MEMORY_LOAD_LIMIT 추가**
- **이유**: 추후 최적화 가능성
- **시간**: 3분
- **위험도**: 낮음
- **판단 기준**:
  - ✅ 수행: 추후 Memory 로드 개수 조정 가능성 있음
  - ❌ 생략: 현재 5개로 충분함

---

### ❌ 수행 불필요 (Low Priority):

- user_id=1 임시 하드코딩
- Entity history limit

---

## 8. 구현 예시

### 최종 core/config.py (권장):

```python
class Settings(BaseSettings):
    # FastAPI 설정
    PROJECT_NAME: str = "HolmesNyangz"
    SECRET_KEY: str = ""
    # ...

    # PostgreSQL Configuration
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "root1234"
    POSTGRES_DB: str = "real_estate"

    # Session & Memory Configuration
    SESSION_TTL_HOURS: int = 24  # ✅ 이미 존재
    MEMORY_RETENTION_DAYS: int = 90  # ✅ 이미 존재
    MEMORY_LIMIT_PER_USER: int = 100  # ✅ 이미 존재
    MEMORY_LOAD_LIMIT: int = 5  # ⚠️ NEW (선택사항)

    @property
    def postgres_url(self) -> str:
        ...

    @property
    def sqlalchemy_url(self) -> str:
        ...
```

---

### 최종 .env 파일 (권장):

```bash
# Database
DATABASE_URL=postgresql+psycopg://postgres:root1234@localhost:5432/real_estate

# PostgreSQL (DATABASE_URL 우선 사용, 없으면 아래 개별 설정 사용)
# POSTGRES_HOST=localhost
# POSTGRES_PORT=5432
# POSTGRES_USER=postgres
# POSTGRES_PASSWORD=root1234
# POSTGRES_DB=real_estate

# Session & Memory
SESSION_TTL_HOURS=24  # 세션 만료 시간 (시간 단위)
MEMORY_RETENTION_DAYS=90  # Memory 보관 기간 (일 단위)
MEMORY_LIMIT_PER_USER=100  # 사용자당 최대 Memory 개수
MEMORY_LOAD_LIMIT=5  # 한 번에 로드할 Memory 개수 (선택사항)
```

---

## 9. 참고: 하드코딩 스캔 방법

이 보고서는 다음 방법으로 하드코딩된 설정을 찾았습니다:

### 스캔 패턴:
```bash
# 1. 숫자 하드코딩
grep -rn "= [0-9]" backend/app --include="*.py"

# 2. TTL, LIMIT, TIMEOUT 등
grep -rn "TTL.*=\|LIMIT.*=\|TIMEOUT.*=" backend/app --include="*.py"

# 3. limit 파라미터
grep -rn "limit.*=.*[0-9]" backend/app --include="*.py"

# 4. PostgreSQL 연결 문자열
grep -rn "postgresql://" backend/app --include="*.py"
```

### 발견된 항목 필터링:
- ✅ 포함: 설정으로 옮길 수 있는 값
- ❌ 제외: 비즈니스 로직 상수, 함수 파라미터 기본값

---

**작성 완료**: 2025-10-14
**마지막 업데이트**: 2025-10-14
**상태**: ✅ 분석 완료 및 권장 사항 제시됨
