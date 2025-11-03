# 완전한 데이터베이스 설정 가이드 (Updated 2025-10-14)

**프로젝트**: HolmesNyangz Beta v0.01
**작성일**: 2025-10-14
**목적**: 다른 개발자가 동일한 데이터베이스 환경을 완전히 재현

---

## 📋 목차

1. [시스템 아키텍처 개요](#시스템-아키텍처-개요)
2. [PostgreSQL 테이블 구조](#postgresql-테이블-구조)
3. [초기 설정 가이드](#초기-설정-가이드)
4. [자동 vs 수동 테이블 생성](#자동-vs-수동-테이블-생성)
5. [데이터 삽입](#데이터-삽입)
6. [검증 및 테스트](#검증-및-테스트)
7. [트러블슈팅](#트러블슈팅)

---

## 1. 시스템 아키텍처 개요

### 데이터베이스 사용 현황

```
PostgreSQL (real_estate DB)
├── [비즈니스 데이터] (수동 생성 필요)
│   ├── real_estates        → 매물 정보 (9,738개)
│   ├── regions             → 지역 정보
│   ├── transactions        → 거래 내역
│   ├── real_estate_agents  → 중개사 정보
│   ├── trust_scores        → 신뢰도 점수
│   ├── users               → 사용자
│   ├── user_profiles       → 사용자 프로필
│   ├── user_favorites      → 찜 목록
│   ├── chat_sessions       → 채팅 세션
│   └── chat_messages       → 채팅 메시지
│
├── [시스템 데이터]
│   ├── sessions            → SessionManager (WebSocket 세션) ⚠️ 수동 권장
│   ├── checkpoints         → LangGraph Checkpointer ✅ 자동
│   ├── checkpoint_blobs    → Checkpoint 데이터 ✅ 자동
│   └── checkpoint_writes   → Checkpoint 쓰기 ✅ 자동
│
└── [Long-term Memory] (Phase 5 예정)
    ├── conversation_memories → 대화 기록 🔜 자동
    ├── user_preferences      → 사용자 선호도 🔜 자동
    └── entity_memories       → 엔티티 추적 🔜 자동
```

### 핵심 질문 답변

**Q: 다른 개발자가 PostgreSQL 테이블을 따로 생성해야 하나요?**

**A: 상황에 따라 다릅니다:**

| 테이블 그룹 | 자동 생성? | 필요 작업 |
|------------|----------|----------|
| **비즈니스 데이터** (real_estates 등) | ❌ 수동 | `init_db.py` + CSV import 스크립트 실행 |
| **Checkpointer** (checkpoints 등 3개) | ✅ **자동** | 서버 첫 실행 시 자동 생성 |
| **SessionManager** (sessions) | ⚠️ **수동 권장** | SQL 파일 실행 권장 |
| **Long-term Memory** (Phase 5) | ✅ **자동** | SQLAlchemy 모델 존재 시 자동 생성 |

---

## 2. PostgreSQL 테이블 구조

### 2.1 비즈니스 데이터 테이블 (10개) - 수동 생성 필요

```sql
-- 매물 관련
CREATE TABLE real_estates (...);         -- 9,738개 매물
CREATE TABLE regions (...);              -- 지역 정보
CREATE TABLE transactions (...);         -- 거래 내역
CREATE TABLE real_estate_agents (...);   -- 중개사

-- 신뢰도
CREATE TABLE trust_scores (...);         -- 신뢰도 점수

-- 사용자
CREATE TABLE users (...);                -- 사용자 계정
CREATE TABLE user_profiles (...);        -- 프로필
CREATE TABLE user_favorites (...);       -- 찜 목록

-- 채팅
CREATE TABLE chat_sessions (...);        -- 채팅 세션
CREATE TABLE chat_messages (...);        -- 메시지
```

**생성 방법**: `python scripts/init_db.py`

### 2.2 시스템 데이터 테이블 (4개) - 자동 생성

#### A. SessionManager 테이블

```sql
-- backend/migrations/create_sessions_table.sql
CREATE TABLE IF NOT EXISTS sessions (
    session_id VARCHAR(100) PRIMARY KEY,
    user_id VARCHAR(100),
    metadata TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    last_activity TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    request_count INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_expires_at ON sessions(expires_at);
```

**자동 생성 방법**:
1. **옵션 1**: FastAPI 서버 첫 실행 시 SQLAlchemy가 자동 생성
2. **옵션 2**: SQL 파일 수동 실행
   ```bash
   psql "postgresql://..." -f backend/migrations/create_sessions_table.sql
   ```

**모델 위치**: `backend/app/models/session.py`

#### B. Checkpointer 테이블 (3개)

```sql
-- LangGraph가 자동으로 생성
CREATE TABLE checkpoints (
    thread_id TEXT NOT NULL,
    checkpoint_ns TEXT NOT NULL DEFAULT '',
    checkpoint_id TEXT NOT NULL,
    parent_checkpoint_id TEXT,
    type TEXT,
    checkpoint JSONB NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}',
    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id)
);

CREATE TABLE checkpoint_blobs (
    thread_id TEXT NOT NULL,
    checkpoint_ns TEXT NOT NULL DEFAULT '',
    checkpoint_id TEXT NOT NULL,
    channel TEXT NOT NULL,
    type TEXT NOT NULL,
    blob BYTEA,
    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id, channel)
);

CREATE TABLE checkpoint_writes (
    thread_id TEXT NOT NULL,
    checkpoint_ns TEXT NOT NULL DEFAULT '',
    checkpoint_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    idx INTEGER NOT NULL,
    channel TEXT NOT NULL,
    type TEXT,
    blob BYTEA,
    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id, task_id, idx)
);
```

**자동 생성 방법**:
- FastAPI 서버 시작 시 `AsyncPostgresSaver.setup()` 호출로 자동 생성
- 코드 위치: `backend/app/service_agent/foundation/checkpointer.py`

### 2.3 Long-term Memory 테이블 (Phase 5 예정)

```sql
-- Phase 5에서 구현 예정
CREATE TABLE conversation_memories (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(100),
    session_id VARCHAR(100),
    message TEXT,
    intent_type VARCHAR(50),
    teams_used JSONB,
    created_at TIMESTAMP WITH TIME ZONE
);

CREATE TABLE user_preferences (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(100) UNIQUE,
    preferred_regions JSONB,
    preferred_property_types JSONB,
    price_range JSONB,
    search_history JSONB
);

CREATE TABLE entity_memories (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(100),
    entity_type VARCHAR(50),
    entity_id VARCHAR(100),
    last_mentioned TIMESTAMP WITH TIME ZONE,
    mention_count INTEGER
);
```

**자동 생성**: SQLAlchemy 모델 작성 후 서버 첫 실행 시 자동 생성

---

## 3. 초기 설정 가이드

### Step 1: PostgreSQL 설치 및 DB 생성

```bash
# PostgreSQL 설치 확인
psql --version

# 데이터베이스 생성
psql -U postgres
CREATE DATABASE real_estate;
\q
```

### Step 2: 환경변수 설정

**파일**: `backend/.env`

```env
# PostgreSQL 연결 정보
DATABASE_URL=postgresql+psycopg://postgres:root1234@localhost:5432/real_estate

# 또는 AsyncPG 드라이버 (SessionManager용)
# DATABASE_URL=postgresql+asyncpg://postgres:root1234@localhost:5432/real_estate
```

**중요**:
- Sync 작업 (scripts): `postgresql+psycopg://...`
- Async 작업 (SessionManager): 자동으로 `postgresql+asyncpg://...`로 변환됨

### Step 3: Python 패키지 설치

```bash
cd backend
pip install -r requirements.txt

# 필수 패키지 확인
pip list | grep -E "sqlalchemy|psycopg|asyncpg|langgraph"
```

**주요 패키지**:
```
sqlalchemy>=2.0.0
psycopg>=3.1.0        # Sync PostgreSQL 드라이버
asyncpg>=0.30.0       # Async PostgreSQL 드라이버 (SessionManager용)
langgraph>=0.2.0      # Checkpointer용
python-dotenv
```

---

## 4. 자동 vs 수동 테이블 생성

### 옵션 A: 완전 자동 (권장)

**장점**:
- 간편함
- 코드와 스키마 동기화 보장
- 실수 방지

**단점**:
- 첫 실행 시 약간의 지연
- 테이블 구조를 사전에 확인 불가

**실행 방법**:

```bash
# 1. 비즈니스 데이터 테이블 생성 (수동)
cd backend
python scripts/init_db.py

# 2. 데이터 삽입 (수동)
python scripts/import_apt_ofst.py
python scripts/import_villa_house_oneroom.py
python scripts/generate_trust_scores.py

# 3. FastAPI 서버 시작 (시스템 테이블 자동 생성)
uvicorn app.main:app --reload
```

**서버 시작 시 자동 생성되는 테이블**:
- ✅ `sessions` (SessionManager)
- ✅ `checkpoints` (Checkpointer)
- ✅ `checkpoint_blobs`
- ✅ `checkpoint_writes`

### 옵션 B: 수동 생성 (명시적)

**장점**:
- 테이블 구조 사전 확인 가능
- 스키마 버전 관리 용이
- CI/CD 파이프라인에 적합

**단점**:
- 수동 작업 필요
- 코드 변경 시 수동 동기화 필요

**실행 방법**:

```bash
# 1. 비즈니스 데이터 테이블 (필수)
cd backend
python scripts/init_db.py

# 2. SessionManager 테이블 (선택)
psql "postgresql://postgres:root1234@localhost:5432/real_estate" \
  -f migrations/create_sessions_table.sql

# 3. Checkpointer 테이블 (선택 - 권장 안 함, 자동 생성 사용)
# LangGraph가 자동으로 생성하므로 수동 생성 불필요

# 4. 데이터 삽입
python scripts/import_apt_ofst.py
python scripts/import_villa_house_oneroom.py
python scripts/generate_trust_scores.py

# 5. 서버 시작
uvicorn app.main:app --reload
```

---

## 5. 데이터 삽입

### Step 1: 비즈니스 데이터 (필수)

```bash
cd backend

# 아파트/오피스텔 (~7,000개)
python scripts/import_apt_ofst.py

# 빌라/원룸/단독 (~2,700개)
python scripts/import_villa_house_oneroom.py

# 신뢰도 점수 생성 (~9,700개)
python scripts/generate_trust_scores.py
```

### Step 2: 시스템 데이터 (자동)

**SessionManager 데이터**:
- 세션은 **런타임 시 자동 생성**됨
- WebSocket 연결 시 자동으로 `sessions` 테이블에 삽입
- 24시간 TTL, 만료 시 자동 삭제

**Checkpointer 데이터**:
- LangGraph 워크플로우 실행 시 자동 생성
- 대화 상태 자동 저장

---

## 6. 검증 및 테스트

### 6.1 전체 테이블 확인

```bash
psql "postgresql://postgres:root1234@localhost:5432/real_estate" -c "\dt"
```

**예상 출력** (17개 테이블):
```
 Schema |         Name          | Type  |  Owner
--------+-----------------------+-------+----------
 public | real_estates          | table | postgres
 public | regions               | table | postgres
 public | transactions          | table | postgres
 public | real_estate_agents    | table | postgres
 public | trust_scores          | table | postgres
 public | users                 | table | postgres
 public | user_profiles         | table | postgres
 public | user_favorites        | table | postgres
 public | chat_sessions         | table | postgres
 public | chat_messages         | table | postgres
 public | sessions              | table | postgres  ← SessionManager
 public | checkpoints           | table | postgres  ← Checkpointer
 public | checkpoint_blobs      | table | postgres  ← Checkpointer
 public | checkpoint_writes     | table | postgres  ← Checkpointer
```

### 6.2 비즈니스 데이터 검증

```bash
cd backend
python scripts/check_db_data.py
```

**예상 출력**:
```
=== PostgreSQL 데이터 확인 ===
RealEstate: 9,738개
TrustScore: 9,738개
Transaction: 10,772개
RealEstateAgent: 7,634개
```

### 6.3 SessionManager 테스트

```bash
cd backend
python test_session_migration.py
```

**예상 출력**:
```
======================================================================
SessionManager PostgreSQL 마이그레이션 테스트
======================================================================
[1/6] PostgreSQL 연결: ✅ PASS
[2/6] sessions 테이블 확인: ✅ PASS
[3/6] 세션 생성: ✅ PASS
[4/6] 세션 검증: ✅ PASS
[5/6] 세션 조회: ✅ PASS
[6/6] 활성 세션 수 조회: ✅ PASS

결과: 6/6 테스트 통과
🎉 모든 테스트 통과!
```

### 6.4 Checkpointer 확인

```bash
# Checkpointer 테이블 확인
psql "postgresql://postgres:root1234@localhost:5432/real_estate" \
  -c "SELECT COUNT(*) FROM checkpoints"

# 예상: 0 (아직 대화 없음)
```

---

## 7. 트러블슈팅

### 문제 1: "Table 'sessions' does not exist"

**증상**: SessionManager 사용 시 테이블 없음 오류

**해결**:
```bash
# 옵션 1: SQL 파일 실행
psql "postgresql://postgres:root1234@localhost:5432/real_estate" \
  -f backend/migrations/create_sessions_table.sql

# 옵션 2: 서버 재시작 (자동 생성)
cd backend
uvicorn app.main:app --reload
```

### 문제 2: "asyncpg is not installed"

**증상**:
```
ModuleNotFoundError: No module named 'asyncpg'
```

**해결**:
```bash
pip install asyncpg
```

### 문제 3: Checkpointer 테이블이 자동 생성되지 않음

**증상**: `checkpoints` 테이블 없음

**원인**: `checkpointer.setup()` 호출 안 됨

**해결**:
1. 코드 확인: `backend/app/service_agent/foundation/checkpointer.py`
   ```python
   async def create_checkpointer(...):
       # ...
       await actual_checkpointer.setup()  # ← 이 줄 확인
   ```

2. 수동 실행:
   ```python
   # Python 콘솔에서
   from app.service_agent.foundation.checkpointer import CheckpointerManager
   import asyncio

   async def setup():
       mgr = CheckpointerManager()
       cp = await mgr.create_checkpointer()
       print("✅ Checkpointer setup complete!")

   asyncio.run(setup())
   ```

### 문제 4: "can't compare offset-naive and offset-aware datetimes"

**증상**: SessionManager에서 datetime 비교 오류

**해결**: 이미 수정됨 (2025-10-14)
- `datetime.now()` → `datetime.now(timezone.utc)`

---

## 8. 빠른 시작 (모든 단계)

### 완전 자동 설정 (추천)

```bash
#!/bin/bash

# 1. 환경변수 설정
cat > backend/.env << EOF
DATABASE_URL=postgresql+psycopg://postgres:root1234@localhost:5432/real_estate
EOF

# 2. DB 생성
psql -U postgres -c "CREATE DATABASE real_estate;"

# 3. 패키지 설치
cd backend
pip install -r requirements.txt

# 4. 비즈니스 데이터 테이블 생성 및 삽입
python scripts/init_db.py
python scripts/import_apt_ofst.py
python scripts/import_villa_house_oneroom.py
python scripts/generate_trust_scores.py

# 5. 검증
python scripts/check_db_data.py

# 6. 서버 시작 (시스템 테이블 자동 생성)
uvicorn app.main:app --reload

# 7. SessionManager 테스트 (별도 터미널)
python test_session_migration.py
```

**소요 시간**: 15-20분

---

## 9. 테이블 생성 체크리스트

### 새 개발자 온보딩용

- [ ] PostgreSQL 설치 및 실행 확인
- [ ] `real_estate` 데이터베이스 생성
- [ ] `.env` 파일 설정 (`DATABASE_URL`)
- [ ] Python 패키지 설치 (`pip install -r requirements.txt`)
- [ ] **비즈니스 데이터** 테이블 생성 (`python scripts/init_db.py`)
- [ ] 매물 데이터 삽입 (`import_apt_ofst.py`, `import_villa_house_oneroom.py`)
- [ ] 신뢰도 점수 생성 (`generate_trust_scores.py`)
- [ ] 데이터 검증 (`check_db_data.py`)
- [ ] FastAPI 서버 시작 (시스템 테이블 자동 생성)
- [ ] `\dt` 명령으로 17개 테이블 확인
- [ ] SessionManager 테스트 실행 (`test_session_migration.py`)
- [ ] WebSocket 연결 테스트

---

## 10. 데이터 저장 위치 요약

| 데이터 | AS-IS (Old) | TO-BE (Current) |
|--------|-------------|-----------------|
| **매물 데이터** | - | PostgreSQL `real_estates` |
| **세션 데이터** | `data/system/sessions/sessions.db` (SQLite) ❌ | PostgreSQL `sessions` ✅ |
| **체크포인트** | `data/system/checkpoints/*.db` (SQLite) ❌ | PostgreSQL `checkpoints` ✅ |
| **Long-term Memory** | - | PostgreSQL (Phase 5 예정) 🔜 |

**결론**:
- ✅ **모든 데이터는 PostgreSQL에 저장**
- ✅ **SQLite 파일 불필요** (백업만 보관)
- ✅ **자동 테이블 생성** (SessionManager, Checkpointer)

---

## 11. 관련 문서

### 마이그레이션 보고서
- [SessionManager 마이그레이션](app/reports/migration_analysis_sessionmanager_sqlite_to_postgres.md)
- [Checkpointer 마이그레이션](app/reports/migration_analysis_sqlite_to_postgres_checkpointer.md)
- [아키텍처 계획서 v1.1](app/reports/plan_of_architecture_session_memory_v1.1.md)

### 비즈니스 데이터 가이드
- [데이터베이스 구축 가이드](app/reports/readme/DATABASE_SETUP_README.md)
- [Phase 1-2 완료 보고서](app/reports/complete_phase_1_2_completion_report_v3.md)

---

**작성자**: Claude Code
**최종 업데이트**: 2025-10-14
**다음 검토**: Phase 5 (Long-term Memory) 구현 후

---

## 요약

### 핵심 답변

**Q: 다른 사용자가 PostgreSQL 테이블을 따로 생성해야 하나요?**

**A: 부분적으로 YES**

1. ✅ **비즈니스 데이터 (10개 테이블)**: 반드시 수동 생성 필요
   - `python scripts/init_db.py`
   - CSV 데이터 import 스크립트 실행

2. ✅ **시스템 데이터 (4개 테이블)**: 자동 생성 가능
   - `sessions` - 서버 첫 실행 시 자동 or SQL 파일 실행
   - `checkpoints` 등 - LangGraph가 자동 생성

3. 🔜 **Long-term Memory (3개 테이블)**: 자동 생성 예정 (Phase 5)
   - SQLAlchemy 모델 작성 후 자동 생성

**최소 작업**:
```bash
# 1. DB 생성
psql -U postgres -c "CREATE DATABASE real_estate;"

# 2. 비즈니스 데이터 (필수)
python scripts/init_db.py
python scripts/import_apt_ofst.py
python scripts/import_villa_house_oneroom.py
python scripts/generate_trust_scores.py

# 3. 서버 시작 (시스템 테이블 자동 생성)
uvicorn app.main:app --reload

# 완료! 17개 테이블 모두 준비됨
```
