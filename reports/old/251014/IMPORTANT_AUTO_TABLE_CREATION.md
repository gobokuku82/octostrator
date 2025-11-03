# ⚠️ 중요: 테이블 자동 생성 여부 (다른 개발자용)

**작성일**: 2025-10-14
**대상**: 새로 프로젝트에 참여하는 개발자

---

## 🎯 핵심 질문

**Q: PostgreSQL 테이블을 따로 생성해야 하나요?**

**A: 부분적으로 YES (자동 + 수동 혼합)**

---

## 📊 테이블 자동 생성 여부

| 테이블 그룹 | 테이블 수 | 자동 생성? | 필요 작업 |
|------------|----------|----------|----------|
| **비즈니스 데이터** | 10개 | ❌ **수동 필수** | `init_db.py` + CSV import 실행 |
| **Checkpointer** | 3개 | ✅ **자동** | 서버 첫 실행 시 자동 생성 |
| **SessionManager** | 1개 | ⚠️ **수동 권장** | SQL 파일 실행 권장 |
| **Long-term Memory** (예정) | 3개 | ✅ **자동** | SQLAlchemy 모델 존재 시 |

---

## 1. Checkpointer 테이블 (자동 생성 ✅)

### 테이블 목록
- `checkpoints`
- `checkpoint_blobs`
- `checkpoint_writes`

### 자동 생성 시점
**서버 첫 실행 시 자동 생성됩니다!**

```python
# app/service_agent/foundation/checkpointer.py (Line 79)
await actual_checkpointer.setup()  # ← 여기서 자동 생성!
```

### 자동 생성 트리거
1. FastAPI 서버 시작 (`uvicorn app.main:app`)
2. Lifespan 이벤트에서 Supervisor pre-warming
3. `get_supervisor()` 호출
4. `create_checkpointer()` 호출
5. `actual_checkpointer.setup()` 자동 실행 → **테이블 생성!**

### 검증 방법
```bash
# 서버 시작 후
psql "postgresql://postgres:root1234@localhost:5432/real_estate" \
  -c "\dt" | grep checkpoints

# 예상 출력:
# public | checkpoints       | table | postgres
# public | checkpoint_blobs  | table | postgres
# public | checkpoint_writes | table | postgres
```

---

## 2. SessionManager 테이블 (수동 권장 ⚠️)

### 테이블 목록
- `sessions`

### 자동 생성 여부
**❌ 자동 생성되지 않습니다!**

**이유**:
- SQLAlchemy 모델만 정의되어 있음 (`app/models/session.py`)
- `Base.metadata.create_all()` 호출 코드 없음
- 명시적 SQL 실행 필요

### 수동 생성 방법

**옵션 1: SQL 파일 실행 (권장)**
```bash
psql "postgresql://postgres:root1234@localhost:5432/real_estate" \
  -f backend/migrations/create_sessions_table.sql
```

**옵션 2: Python 스크립트**
```python
from app.db.postgre_db import engine, Base
from app.models.session import Session  # Import to register

# Sync 방식으로 테이블 생성
Base.metadata.create_all(engine, tables=[Session.__table__])
```

### 테이블이 없을 때 증상
```python
# SessionManager 사용 시 오류 발생
sqlalchemy.exc.ProgrammingError: (psycopg.errors.UndefinedTable)
relation "sessions" does not exist
```

---

## 3. 비즈니스 데이터 테이블 (수동 필수 ❌)

### 테이블 목록 (10개)
- `real_estates` (9,738개 매물)
- `regions`
- `transactions`
- `real_estate_agents`
- `trust_scores`
- `users`
- `user_profiles`
- `user_favorites`
- `chat_sessions`
- `chat_messages`

### 생성 방법
```bash
cd backend

# 1. 테이블 생성
python scripts/init_db.py

# 2. 데이터 삽입
python scripts/import_apt_ofst.py
python scripts/import_villa_house_oneroom.py
python scripts/generate_trust_scores.py
```

**소요 시간**: 10-15분

---

## 🚀 새 개발자 최소 작업 순서

### Step 1: 데이터베이스 생성
```bash
psql -U postgres
CREATE DATABASE real_estate;
\q
```

### Step 2: 환경변수 설정
```bash
# backend/.env
DATABASE_URL=postgresql+psycopg://postgres:root1234@localhost:5432/real_estate
```

### Step 3: 패키지 설치
```bash
cd backend
pip install -r requirements.txt
```

### Step 4: 비즈니스 데이터 (수동 필수)
```bash
python scripts/init_db.py                      # 10개 테이블 생성
python scripts/import_apt_ofst.py              # 매물 7,000개
python scripts/import_villa_house_oneroom.py   # 매물 2,700개
python scripts/generate_trust_scores.py        # 신뢰도 점수
```

### Step 5: SessionManager 테이블 (수동 권장)
```bash
psql "postgresql://postgres:root1234@localhost:5432/real_estate" \
  -f migrations/create_sessions_table.sql
```

### Step 6: 서버 시작 (Checkpointer 자동 생성)
```bash
uvicorn app.main:app --reload
```

**결과**:
- ✅ 비즈니스 데이터 (10개) - 수동 생성됨
- ✅ SessionManager (1개) - 수동 생성됨
- ✅ Checkpointer (3개) - **자동 생성됨!**
- **총 14개 테이블 준비 완료**

---

## 🔍 테이블 생성 확인

### 전체 테이블 확인
```bash
psql "postgresql://postgres:root1234@localhost:5432/real_estate" -c "\dt"
```

**예상 출력** (14개 테이블):
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
 public | sessions              | table | postgres  ← SessionManager (수동)
 public | checkpoints           | table | postgres  ← Checkpointer (자동!)
 public | checkpoint_blobs      | table | postgres  ← Checkpointer (자동!)
 public | checkpoint_writes     | table | postgres  ← Checkpointer (자동!)
```

### 테스트 스크립트
```bash
# 자동 생성 여부 확인
cd backend
python test_auto_table_creation.py
```

---

## ⚠️ 주의사항

### 1. SessionManager는 왜 자동 생성 안 하나요?

**이유**:
- SQLAlchemy의 `create_all()` 호출이 없음
- 명시적 테이블 생성이 더 안전 (스키마 버전 관리)
- Migration 파일로 스키마 변경 이력 관리

**장점**:
- 개발자가 스키마를 명시적으로 확인 가능
- Git으로 스키마 변경 이력 추적
- 롤백 시나리오 명확

### 2. Checkpointer는 왜 자동 생성하나요?

**이유**:
- LangGraph 라이브러리가 자동 생성 지원
- 내부적으로 `setup()` 메서드 제공
- 스키마가 LangGraph 버전에 종속

**장점**:
- 개발자가 신경 쓸 필요 없음
- LangGraph 업데이트 시 자동으로 스키마 동기화

### 3. 서버를 재시작하면 테이블이 삭제되나요?

**아니요!**
- PostgreSQL은 **영구 저장소**
- 서버 재시작해도 데이터 유지
- 테이블 삭제는 `DROP TABLE` 명령으로만 가능

### 4. 테이블 생성이 실패하면?

**Checkpointer 실패 시**:
```
❌ Failed to create checkpointer: ...
```
→ 서버는 시작되지만 대화 상태 저장 안 됨
→ 로그 확인 후 PostgreSQL 연결 정보 확인

**SessionManager 실패 시**:
```
❌ relation "sessions" does not exist
```
→ WebSocket 연결 실패
→ `migrations/create_sessions_table.sql` 실행

---

## 📚 관련 문서

1. [완전한 DB 설정 가이드](DATABASE_SETUP_COMPLETE_GUIDE.md)
2. [SessionManager 마이그레이션 보고서](app/reports/migration_analysis_sessionmanager_sqlite_to_postgres.md)
3. [마이그레이션 완료 요약](MIGRATION_COMPLETE.md)

---

## ✅ 요약

### 자동 생성되는 테이블 (3개)
- ✅ `checkpoints` - 서버 첫 실행 시
- ✅ `checkpoint_blobs` - 서버 첫 실행 시
- ✅ `checkpoint_writes` - 서버 첫 실행 시

### 수동 생성 필요 테이블 (11개)
- ❌ 비즈니스 데이터 (10개) - `init_db.py` 실행
- ⚠️ `sessions` (1개) - SQL 파일 실행 권장

### 다른 개발자가 할 일
```bash
# 1. 비즈니스 데이터 생성 (필수)
python scripts/init_db.py
python scripts/import_apt_ofst.py
python scripts/import_villa_house_oneroom.py
python scripts/generate_trust_scores.py

# 2. SessionManager 테이블 생성 (권장)
psql "postgresql://..." -f migrations/create_sessions_table.sql

# 3. 서버 시작 (Checkpointer 자동 생성)
uvicorn app.main:app --reload

# ✅ 완료! 14개 테이블 모두 준비됨
```

---

**작성자**: Claude Code
**최종 업데이트**: 2025-10-14
**문의**: 프로젝트 담당자
