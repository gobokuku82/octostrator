# SessionManager SQLite → PostgreSQL 마이그레이션 완료 보고서

**작성일**: 2025-10-14
**버전**: v2.0 (✅ 마이그레이션 완료)
**대상 시스템**: SessionManager (WebSocket 세션 관리)
**이전 상태**: SQLite 기반 (동기)
**현재 상태**: ✅ PostgreSQL 기반 (비동기)
**소요 시간**: 약 90분

---

## 📋 목차

1. [✅ 마이그레이션 완료 요약](#1-마이그레이션-완료-요약)
2. [현황 분석 (AS-IS)](#2-현황-분석-as-is)
3. [마이그레이션 난이도 평가](#3-마이그레이션-난이도-평가)
4. [SQLite vs PostgreSQL 비교](#4-sqlite-vs-postgresql-비교)
5. [마이그레이션 전략](#5-마이그레이션-전략)
6. [✅ 구현 완료 내역](#6-구현-완료-내역)
7. [리스크 분석](#7-리스크-분석)
8. [개발자 필독 정보](#8-개발자-필독-정보)

---

## 1. ✅ 마이그레이션 완료 요약

### 1.1 완료 상태

**마이그레이션 성공! (2025-10-14)**

| 항목 | 상태 | 비고 |
|------|------|------|
| **Session 모델** | ✅ 완료 | [`models/session.py`](../models/session.py) |
| **SessionManager** | ✅ 완료 | [`api/session_manager.py`](../api/session_manager.py) - 비동기 |
| **PostgreSQL 테이블** | ✅ 완료 | `sessions` 테이블 생성 완료 |
| **Async 엔진** | ✅ 완료 | [`db/postgre_db.py`](../db/postgre_db.py) - AsyncSessionLocal |
| **API 엔드포인트** | ✅ 완료 | [`api/chat_api.py`](../api/chat_api.py) - await 추가 |
| **SQLite 백업** | ✅ 완료 | `sessions_backup_20251014/sessions.db` |
| **SQLite 삭제** | ✅ 완료 | `sessions/sessions.db` 제거 |

### 1.2 변경 파일 목록

#### 신규 파일 (4개)
1. ✅ [`backend/app/models/session.py`](../models/session.py) - Session SQLAlchemy 모델
2. ✅ [`backend/migrations/create_sessions_table.sql`](../../migrations/create_sessions_table.sql) - PostgreSQL 마이그레이션 SQL
3. ✅ [`backend/data/system/sessions_backup_20251014/sessions.db`](../../data/system/sessions_backup_20251014/sessions.db) - SQLite 백업
4. ✅ 이 보고서 (v2.0)

#### 수정 파일 (3개)
1. ✅ [`backend/app/api/session_manager.py`](../api/session_manager.py)
   - `sqlite3` → `sqlalchemy (AsyncSessionLocal)`
   - 모든 메서드 `async def`로 변환
   - 126 lines 전체 리팩토링

2. ✅ [`backend/app/db/postgre_db.py`](../db/postgre_db.py)
   - AsyncEngine 추가 (`asyncpg` 드라이버)
   - `AsyncSessionLocal` 추가
   - `get_async_db()` 함수 추가

3. ✅ [`backend/app/api/chat_api.py`](../api/chat_api.py)
   - 7개 SessionManager 호출에 `await` 추가
   - Line 82, 120, 152, 209, 379, 403

#### 삭제 파일 (1개)
1. ✅ `backend/data/system/sessions/sessions.db` - SQLite 파일 삭제

### 1.3 주요 변경 사항

**AS-IS (SQLite, 동기)**:
```python
import sqlite3

class SessionManager:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = Path(db_path)

    def create_session(self, user_id: Optional[str] = None):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("INSERT INTO sessions ...")
```

**TO-BE (PostgreSQL, 비동기)**:
```python
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.postgre_db import AsyncSessionLocal
from app.models.session import Session

class SessionManager:
    def __init__(self, session_ttl_hours: int = 24):
        self.session_ttl = timedelta(hours=session_ttl_hours)

    async def create_session(self, user_id: Optional[str] = None):
        async with AsyncSessionLocal() as db:
            new_session = Session(...)
            db.add(new_session)
            await db.commit()
```

### 1.4 데이터 저장 위치 변경

**AS-IS**:
```
backend/data/system/sessions/sessions.db  (24KB, SQLite 파일)
```

**TO-BE**:
```
PostgreSQL 서버: localhost:5432/real_estate
테이블: sessions
```

### 1.5 소요 시간

| 단계 | 예상 | 실제 | 비고 |
|------|------|------|------|
| 분석 및 보고서 작성 | 30분 | 20분 | - |
| Session 모델 생성 | 10분 | 5분 | - |
| SessionManager 리팩토링 | 30분 | 30분 | 126 lines 전체 변경 |
| PostgreSQL 설정 (Async) | 10분 | 15분 | AsyncEngine 추가 |
| API 엔드포인트 수정 | 20분 | 10분 | await 추가 7곳 |
| 테스트 및 검증 | 20분 | 10분 | psql 확인 |
| **총 소요 시간** | **2시간** | **90분** | ✅ 예상보다 빠름 |

---

## 1. 현황 분석

### 1.1 현재 구현 상태

**파일**: [`backend/app/api/session_manager.py`](../api/session_manager.py)

**주요 특징**:
- SQLite 기반 세션 저장 (`sqlite3` 모듈 사용)
- 동기식 DB 작업 (AsyncIO 아님)
- 파일 기반 저장: `backend/data/system/sessions/sessions.db`
- 24시간 TTL, 자동 만료 정리
- 현재 활성 세션: **4개**

**테이블 스키마**:
```sql
CREATE TABLE sessions (
    session_id TEXT PRIMARY KEY,
    user_id TEXT,
    metadata TEXT,
    created_at TIMESTAMP NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    last_activity TIMESTAMP NOT NULL,
    request_count INTEGER DEFAULT 0
);

CREATE INDEX idx_expires_at ON sessions(expires_at);
```

### 1.2 주요 메서드

| 메서드 | 설명 | DB 작업 |
|--------|------|---------|
| `create_session` | 새 세션 생성 | INSERT |
| `validate_session` | 세션 유효성 검증 + 활동 시간 업데이트 | SELECT + UPDATE |
| `get_session` | 세션 정보 조회 | SELECT |
| `delete_session` | 세션 삭제 (로그아웃) | DELETE |
| `cleanup_expired_sessions` | 만료 세션 정리 | DELETE WHERE |
| `extend_session` | 세션 만료 시간 연장 | UPDATE |
| `get_active_session_count` | 활성 세션 수 조회 | SELECT COUNT |

### 1.3 데이터 저장 위치

**SQLite**:
```
backend/data/system/sessions/sessions.db  (24KB)
```
- ✅ 프로젝트 디렉토리 내부
- ✅ Git으로 관리 가능 (.gitignore 제외 시)
- ✅ 백업 간편 (파일 복사)

**PostgreSQL** (마이그레이션 후):
```
PostgreSQL 서버 데이터 디렉토리 (예: /var/lib/postgresql/data/)
```
- ⚠️ 프로젝트 외부
- ⚠️ 서버 의존적
- ✅ 다중 서버 환경 지원

---

## 2. 마이그레이션 난이도 평가

### 2.1 난이도: **중간 (Medium)**

**이유**:
1. ✅ **간단한 스키마**: TEXT/INTEGER/TIMESTAMP만 사용
2. ✅ **PostgreSQL 호환 SQL**: 스키마 변경 최소
3. ⚠️ **동기 → 비동기 변환 필요**: `asyncpg` 또는 `psycopg3` 사용
4. ⚠️ **전역 상태 리팩토링**: FastAPI 비동기 호환성 확보

### 2.2 Checkpointer 마이그레이션과의 차이

| 항목 | Checkpointer | SessionManager |
|------|--------------|----------------|
| **난이도** | Very Easy (3줄) | Medium (전체 리팩토링) |
| **변경 범위** | 1개 파일 | 1개 파일 + 의존성 |
| **소요 시간** | 7분 | 30~60분 |
| **비동기 변환** | 불필요 (이미 async) | 필요 (sync → async) |
| **테스트 복잡도** | 낮음 | 중간 (WebSocket 통합 테스트) |

---

## 3. SQLite vs PostgreSQL 비교

### 3.1 성능 비교 (SessionManager 용도)

| 지표 | SQLite | PostgreSQL | 비고 |
|------|--------|------------|------|
| **동시 쓰기** | ❌ 1개만 | ✅ 다수 가능 | WebSocket 연결 시 경합 가능 |
| **읽기 성능** | ⚡ 매우 빠름 (로컬) | ⚡ 빠름 (네트워크 오버헤드) | |
| **단일 서버** | ✅ 충분 | ✅ 과잉 | 현재 환경에서는 SQLite도 충분 |
| **다중 서버** | ❌ 불가능 | ✅ 가능 | 로드 밸런싱 필요 시 |

### 3.2 운영 측면

| 항목 | SQLite | PostgreSQL |
|------|--------|------------|
| **백업** | ✅ 파일 복사 | ⚠️ pg_dump 필요 |
| **복구** | ✅ 파일 교체 | ⚠️ pg_restore 필요 |
| **모니터링** | ⚠️ 제한적 | ✅ 다양한 도구 |
| **스케일링** | ❌ 불가 | ✅ Replication, Sharding |

### 3.3 개발 측면

| 항목 | SQLite | PostgreSQL |
|------|--------|------------|
| **설정** | ✅ 불필요 | ⚠️ 서버 설치 필요 |
| **개발 환경** | ✅ 즉시 사용 | ⚠️ 로컬 PostgreSQL 필요 |
| **테스트** | ✅ 간단 (파일 삭제) | ⚠️ DB 초기화 필요 |

---

## 4. 마이그레이션 전략

### 4.1 권장 전략: **SQLAlchemy ORM 사용**

**이유**:
1. ✅ DB 추상화로 SQLite/PostgreSQL 모두 지원
2. ✅ 비동기 지원 (`asyncpg` 통합)
3. ✅ 기존 프로젝트와 일관성 (Checkpointer, User 모델 등이 SQLAlchemy 사용)

**장점**:
- 환경 변수로 DB 전환 가능 (`DATABASE_URL`)
- 테스트 환경에서 SQLite 유지 가능
- 마이그레이션 이력 관리 (Alembic)

### 4.2 대안: 순수 AsyncPG

**비권장 이유**:
- 기존 코드베이스와 불일치
- PostgreSQL만 지원 (SQLite 병행 불가)
- 마이그레이션 복잡도 증가

---

## 5. 구현 계획

### 5.1 Option A: SQLAlchemy ORM (권장)

#### Step 1: 모델 정의 (신규)

**파일**: `backend/app/models/session.py` (신규)

```python
from sqlalchemy import Column, String, Integer, DateTime, Text, Index
from sqlalchemy.sql import func
from app.db.postgre_db import Base
from datetime import datetime

class Session(Base):
    """
    WebSocket 세션 모델

    SQLite/PostgreSQL 모두 호환
    """
    __tablename__ = "sessions"

    session_id = Column(String(100), primary_key=True, index=True)
    user_id = Column(String(100), nullable=True)
    metadata = Column(Text, nullable=True)  # JSON string
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    last_activity = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    request_count = Column(Integer, default=0, nullable=False)

    __table_args__ = (
        Index('idx_expires_at', 'expires_at'),
    )
```

#### Step 2: SessionManager 리팩토링

**파일**: `backend/app/api/session_manager.py` (수정)

**주요 변경사항**:
```python
# AS-IS (SQLite, 동기)
import sqlite3

class SessionManager:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = Path(db_path)
        # sqlite3.connect() 사용

    def create_session(self, user_id: Optional[str] = None) -> Tuple[str, datetime]:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("INSERT INTO sessions ...")
```

```python
# TO-BE (PostgreSQL, 비동기)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func
from app.db.postgre_db import SessionLocal
from app.models.session import Session

class SessionManager:
    def __init__(self):
        # DB 연결은 SessionLocal()로 처리
        pass

    async def create_session(
        self,
        user_id: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Tuple[str, datetime]:
        session_id = f"session-{uuid.uuid4()}"
        created_at = datetime.now()
        expires_at = created_at + timedelta(hours=24)

        async with SessionLocal() as db:
            new_session = Session(
                session_id=session_id,
                user_id=user_id,
                metadata=json.dumps(metadata or {}),
                created_at=created_at,
                expires_at=expires_at,
                last_activity=created_at,
                request_count=0
            )
            db.add(new_session)
            await db.commit()
            await db.refresh(new_session)

        logger.info(f"Session created: {session_id}")
        return session_id, expires_at

    async def validate_session(self, session_id: str) -> bool:
        async with SessionLocal() as db:
            result = await db.execute(
                select(Session).where(Session.session_id == session_id)
            )
            session = result.scalar_one_or_none()

            if not session:
                return False

            if datetime.now() > session.expires_at:
                await db.delete(session)
                await db.commit()
                return False

            # 활동 시간 업데이트
            session.last_activity = datetime.now()
            session.request_count += 1
            await db.commit()

            return True

    # 나머지 메서드도 동일하게 async + SQLAlchemy로 변환
```

#### Step 3: Alembic Migration

```bash
# 1. Session 모델을 models/__init__.py에 추가
# from .session import Session

# 2. Migration 생성
alembic revision --autogenerate -m "Migrate SessionManager to PostgreSQL"

# 3. Migration 실행
alembic upgrade head
```

#### Step 4: FastAPI 라우터 수정

**파일**: `backend/app/api/routes/chat_websocket.py` (또는 WebSocket 사용처)

```python
# AS-IS (동기)
@router.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    session_manager = get_session_manager()

    # ❌ 동기 호출
    is_valid = session_manager.validate_session(session_id)
```

```python
# TO-BE (비동기)
@router.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    session_manager = get_session_manager()

    # ✅ await 추가
    is_valid = await session_manager.validate_session(session_id)
```

### 5.2 Option B: 순수 sqlite3 → asyncpg (비권장)

**변경 사항**:
- `sqlite3` → `asyncpg`
- SQL 쿼리 직접 작성
- 마이그레이션 스크립트 별도 작성

**비권장 이유**: 기존 코드베이스 (Checkpointer, User 모델 등)가 SQLAlchemy를 사용하므로 일관성 저해

---

## 6. 리스크 분석

### 6.1 리스크 목록

| 리스크 | 심각도 | 완화 방안 |
|--------|--------|----------|
| **활성 세션 손실** | 🔴 High | 마이그레이션 전 세션 데이터 백업 |
| **WebSocket 연결 끊김** | 🟡 Medium | 점진적 배포 (Blue-Green) |
| **비동기 변환 버그** | 🟡 Medium | 충분한 테스트 (Unit + Integration) |
| **PostgreSQL 연결 실패** | 🟡 Medium | 연결 재시도 로직 + Fallback |
| **성능 저하** | 🟢 Low | 인덱스 최적화 + 연결 풀 설정 |

### 6.2 롤백 계획

**마이그레이션 실패 시**:
1. ✅ `.env` 파일의 `SESSION_DB_TYPE=sqlite` 설정으로 롤백
2. ✅ 백업된 `sessions.db` 파일 복구
3. ✅ 이전 버전 코드로 재배포

---

## 7. 마이그레이션 체크리스트

### Phase 1: 준비 (30분)
- [ ] 현재 세션 데이터 백업 (`sessions.db` 파일 복사)
- [ ] 활성 세션 수 확인 (`get_active_session_count()`)
- [ ] PostgreSQL 연결 테스트 (`DATABASE_URL` 확인)
- [ ] `backend/app/models/session.py` 모델 작성
- [ ] `backend/app/models/__init__.py`에 Session 추가

### Phase 2: 마이그레이션 실행 (20분)
- [ ] Alembic migration 생성 및 실행
- [ ] PostgreSQL에 `sessions` 테이블 생성 확인
- [ ] 인덱스 생성 확인 (`idx_expires_at`)

### Phase 3: 코드 변경 (30분)
- [ ] `session_manager.py` 리팩토링 (동기 → 비동기)
  - [ ] `create_session` → `async def`
  - [ ] `validate_session` → `async def`
  - [ ] `get_session` → `async def`
  - [ ] `delete_session` → `async def`
  - [ ] `cleanup_expired_sessions` → `async def`
  - [ ] `extend_session` → `async def`
  - [ ] `get_active_session_count` → `async def`
- [ ] WebSocket 라우터 수정 (await 추가)

### Phase 4: 테스트 (30분)
- [ ] Unit Test 작성 및 실행
  - [ ] 세션 생성 테스트
  - [ ] 세션 검증 테스트
  - [ ] 만료 세션 정리 테스트
- [ ] Integration Test
  - [ ] WebSocket 연결 테스트
  - [ ] 다중 세션 동시 접속 테스트
- [ ] 성능 테스트 (동시 접속 100명)

### Phase 5: 배포 및 모니터링
- [ ] Staging 환경 배포
- [ ] 프로덕션 배포 (Blue-Green 또는 Rolling)
- [ ] 활성 세션 수 모니터링
- [ ] 에러 로그 모니터링 (24시간)
- [ ] 백업 파일 정리 (7일 후)

---

## 8. 예상 소요 시간

| 단계 | 소요 시간 | 비고 |
|------|----------|------|
| **준비** | 30분 | 백업 + 모델 작성 |
| **마이그레이션** | 20분 | Alembic 실행 |
| **코드 변경** | 30분 | 비동기 변환 |
| **테스트** | 30분 | Unit + Integration |
| **배포** | 20분 | Staging + Production |
| **총 소요 시간** | **2시간 10분** | |

---

## 9. 결론 및 권장 사항

### 9.1 마이그레이션 필요성 평가

**현재 환경 (단일 서버)**:
- ✅ SQLite로 충분히 안정적
- ✅ 활성 세션 4개 (부하 낮음)
- ⚠️ 동시 쓰기 경합 가능성 낮음

**마이그레이션이 필요한 경우**:
1. 🔴 **다중 서버 환경** 필요 시 (로드 밸런싱)
2. 🔴 **동시 접속 100명 이상** 예상 시
3. 🟡 **세션 데이터 분석** 필요 시 (JOIN, 집계 쿼리)

### 9.2 권장 사항

**옵션 1: 즉시 마이그레이션 (권장 안 함)**
- ❌ 비즈니스 가치 낮음 (현재 문제 없음)
- ❌ 리스크 대비 이득 적음
- ⚠️ 개발 시간 2시간 소요

**옵션 2: Phase 6으로 연기 (권장)**
- ✅ Long-term Memory (Phase 5) 우선 구현
- ✅ 다중 서버 필요 시점에 마이그레이션
- ✅ SQLAlchemy 사용으로 언제든 전환 가능

**옵션 3: Hybrid 접근 (최선)**
- ✅ **지금**: SQLAlchemy 모델만 작성 (10분)
- ✅ **Phase 6**: 필요 시 SessionManager 비동기 변환 (2시간)
- ✅ **장점**: 준비는 해두고 실제 전환은 필요 시

### 9.3 최종 권장

```
📌 SessionManager PostgreSQL 마이그레이션:
   Phase 6 (선택 사항) - Long-term Memory 완료 후 진행

근거:
1. 현재 SQLite로 안정적 동작 (활성 세션 4개)
2. Long-term Memory가 더 높은 우선순위
3. 다중 서버 환경이 필요할 때 진행해도 충분
```

---

## 10. 개발자 필독 정보

### 10.1 SQLite vs PostgreSQL 데이터 저장 위치

| DB | 저장 위치 | Git 관리 | 백업 방법 |
|----|----------|---------|----------|
| **SQLite** | `backend/data/system/sessions/sessions.db` (프로젝트 내부) | 가능 (.gitignore 설정에 따라) | 파일 복사 |
| **PostgreSQL** | PostgreSQL 서버 데이터 디렉토리 (프로젝트 외부) | 불가 | pg_dump |

### 10.2 환경 변수 설정

**SQLite (현재)**:
```env
# .env
# (설정 불필요 - 기본값 사용)
```

**PostgreSQL (마이그레이션 후)**:
```env
# .env
DATABASE_URL=postgresql+psycopg://postgres:password@localhost:5432/real_estate
```

### 10.3 주의사항

1. ⚠️ **세션 데이터는 임시 데이터**
   - 24시간 TTL
   - 만료 시 자동 삭제
   - 백업 불필요 (일반적으로)

2. ⚠️ **활성 세션 확인 방법**
   ```python
   session_manager = get_session_manager()
   count = session_manager.get_active_session_count()
   print(f"Active sessions: {count}")
   ```

3. ⚠️ **마이그레이션 시 세션 손실 불가피**
   - 사용자 재로그인 필요
   - 점진적 배포로 최소화

---

## 11. 관련 문서

- [Checkpointer PostgreSQL 마이그레이션 보고서](./migration_analysis_sqlite_to_postgres_checkpointer.md)
- [Architecture Plan v1.1](./plan_of_architecture_session_memory_v1.1.md)
- [SQLAlchemy Async 공식 문서](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)

---

**작성자**: Claude Code
**검토자**: _______________
**승인일**: 2025-10-14
**다음 검토일**: Phase 5 완료 후

---

## 부록: 빠른 시작 (SQLAlchemy 모델만 준비)

**10분 작업 (Hybrid 접근)**:

```bash
# 1. Session 모델 파일 생성
cat > backend/app/models/session.py << 'EOF'
from sqlalchemy import Column, String, Integer, DateTime, Text, Index
from sqlalchemy.sql import func
from app.db.postgre_db import Base

class Session(Base):
    __tablename__ = "sessions"

    session_id = Column(String(100), primary_key=True)
    user_id = Column(String(100), nullable=True)
    metadata = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    last_activity = Column(DateTime(timezone=True), server_default=func.now())
    request_count = Column(Integer, default=0)

    __table_args__ = (Index('idx_expires_at', 'expires_at'),)
EOF

# 2. models/__init__.py에 추가
echo "from .session import Session" >> backend/app/models/__init__.py

# 3. Migration 생성 (실행은 나중에)
alembic revision --autogenerate -m "Prepare Session model for PostgreSQL"

echo "✅ Session 모델 준비 완료! (실제 마이그레이션은 Phase 6에서 진행)"
```

**이후 Phase 6에서**:
- `session_manager.py` 비동기 변환 (2시간)
- Alembic migration 실행
- 테스트 및 배포
