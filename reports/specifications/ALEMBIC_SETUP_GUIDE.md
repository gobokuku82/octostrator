# Alembic 설정 완전 가이드
**AI PT Manager - Database Migration 설정**

작성일: 2025-11-07

---

## 1. Alembic이란?

**Alembic**: SQLAlchemy용 데이터베이스 마이그레이션 도구

### 왜 필요한가?

```python
# 문제: Python 코드에만 모델 정의
class Lead(Base):
    __tablename__ = "leads"
    id = Column(Integer, primary_key=True)
    name = Column(String(100))

# PostgreSQL에는 테이블이 없음!
# psql -c "\dt" → 테이블 없음
```

**Alembic의 역할**:
1. Python 모델 → SQL 테이블 생성
2. 스키마 변경 이력 관리
3. 롤백 가능
4. 팀 협업 (migration 파일 공유)

### Git과 유사한 개념

```
Git                    Alembic
────────────────────────────────────
commit                 migration
git log                alembic history
git checkout           alembic downgrade
git push               alembic upgrade
```

---

## 2. Alembic 설치

### Step 1: 패키지 설치

```bash
# Backend 디렉토리로 이동
cd C:\kdy\Projects\AI_PTmanager\beta_v001\backend

# Alembic 설치
pip install alembic

# 또는 requirements.txt에 추가
echo alembic==1.13.1 >> requirements.txt
pip install -r requirements.txt
```

### Step 2: 설치 확인

```bash
alembic --version
# 출력: alembic 1.13.1
```

---

## 3. Alembic 초기화

### Step 1: 프로젝트 구조 확인

```
backend/
├── app/
│   └── octostrator/
├── database/
│   └── relation_db/
│       └── models.py         ← SQLAlchemy 모델
├── .env                       ← POSTGRES_URL 확인
└── (alembic/ 생성 예정)
```

### Step 2: Alembic 초기화

```bash
cd backend
alembic init alembic
```

**생성되는 파일**:
```
backend/
├── alembic/                   ← 새로 생성됨
│   ├── env.py                 ← 설정 파일 (수정 필요!)
│   ├── script.py.mako         ← Migration 템플릿
│   ├── README
│   └── versions/              ← Migration 파일들
└── alembic.ini                ← 메인 설정 (수정 필요!)
```

---

## 4. Alembic 설정

### 4.1 alembic.ini 수정

**파일 경로**: `backend/alembic.ini`

#### Before (초기 상태):
```ini
# line 58 근처
sqlalchemy.url = driver://user:pass@localhost/dbname
```

#### After (수정):

**옵션 1: 환경변수 사용 (권장)**
```ini
# sqlalchemy.url을 주석 처리하거나 삭제
# sqlalchemy.url = driver://user:pass@localhost/dbname

# env.py에서 환경변수로 설정하므로 여기서는 비워둠
```

**옵션 2: 직접 입력** (테스트용, 보안 위험)
```ini
sqlalchemy.url = postgresql://username:password@localhost:5432/ai_pt_manager
```

### 4.2 alembic/env.py 수정

**파일 경로**: `backend/alembic/env.py`

#### 수정 포인트 1: Import 추가

```python
# Line 1-10 근처에 추가
import os
import sys
from pathlib import Path

# Backend 디렉토리를 Python path에 추가
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

# ===== 여기부터 추가! =====
from database.relation_db.models import Base  # SQLAlchemy Base import
from dotenv import load_dotenv

# .env 파일 로드
env_path = backend_path / ".env"
load_dotenv(dotenv_path=env_path)
# ===== 여기까지 추가! =====
```

#### 수정 포인트 2: target_metadata 설정

```python
# Line 20 근처 (기본값)
# target_metadata = None

# ===== 수정! =====
target_metadata = Base.metadata
# ===== 수정 완료! =====
```

#### 수정 포인트 3: PostgreSQL URL 설정

```python
# Line 50-60 근처, run_migrations_offline() 함수 내부
def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    # ===== 기존 코드 =====
    # url = config.get_main_option("sqlalchemy.url")

    # ===== 수정! =====
    url = os.getenv("POSTGRES_URL")
    if not url:
        raise ValueError("POSTGRES_URL 환경 변수가 설정되지 않았습니다.")
    # ===== 수정 완료! =====

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    # ... 나머지 코드
```

```python
# Line 70-80 근처, run_migrations_online() 함수 내부
def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    # ===== 기존 코드 수정 =====
    # connectable = engine_from_config(
    #     config.get_section(config.config_ini_section, {}),
    #     prefix="sqlalchemy.",
    #     poolclass=pool.NullPool,
    # )

    # ===== 새 코드! =====
    from sqlalchemy import create_engine

    url = os.getenv("POSTGRES_URL")
    if not url:
        raise ValueError("POSTGRES_URL 환경 변수가 설정되지 않았습니다.")

    connectable = create_engine(url, poolclass=pool.NullPool)
    # ===== 수정 완료! =====

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata
        )
        # ... 나머지 코드
```

### 4.3 전체 env.py 예시

**완성된 env.py**:

```python
import os
import sys
from pathlib import Path
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool, create_engine
from alembic import context

# Backend path 추가
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

# 환경변수 로드
from dotenv import load_dotenv
env_path = backend_path / ".env"
load_dotenv(dotenv_path=env_path)

# SQLAlchemy models import
from database.relation_db.models import Base

# Alembic Config object
config = context.config

# Logging 설정
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadata 설정
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = os.getenv("POSTGRES_URL")
    if not url:
        raise ValueError("POSTGRES_URL 환경 변수가 설정되지 않았습니다.")

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    url = os.getenv("POSTGRES_URL")
    if not url:
        raise ValueError("POSTGRES_URL 환경 변수가 설정되지 않았습니다.")

    connectable = create_engine(url, poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

---

## 5. 환경변수 확인

### .env 파일 확인

**파일 경로**: `backend/.env`

```bash
# PostgreSQL 연결 문자열 확인
POSTGRES_URL=postgresql://username:password@localhost:5432/ai_pt_manager
```

**형식**:
```
postgresql://[username]:[password]@[host]:[port]/[database_name]
```

**예시**:
```bash
# Local PostgreSQL
POSTGRES_URL=postgresql://postgres:mypassword@localhost:5432/ai_pt_manager

# Docker PostgreSQL
POSTGRES_URL=postgresql://postgres:postgres@localhost:5432/fitness_db

# Remote PostgreSQL
POSTGRES_URL=postgresql://user:pass@192.168.1.100:5432/ai_pt_manager
```

### 연결 테스트

```bash
# Python에서 테스트
python -c "
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv()
url = os.getenv('POSTGRES_URL')
print(f'URL: {url}')

engine = create_engine(url)
conn = engine.connect()
print('✓ PostgreSQL 연결 성공!')
conn.close()
"
```

---

## 6. 설정 검증

### Step 1: Alembic 버전 확인

```bash
cd backend
alembic current
```

**예상 출력**:
```
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
```

에러가 없으면 설정 성공!

### Step 2: Migration 디렉토리 확인

```bash
ls alembic/versions/
# 아직 비어있음 (정상)
```

---

## 7. 첫 Migration 생성 (테스트)

### Step 1: 자동 감지

```bash
cd backend
alembic revision --autogenerate -m "Initial migration - create all tables"
```

**예상 출력**:
```
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.autogenerate.compare] Detected added table 'users'
INFO  [alembic.autogenerate.compare] Detected added table 'leads'
INFO  [alembic.autogenerate.compare] Detected added table 'inquiries'
...
  Generating C:\kdy\Projects\AI_PTmanager\beta_v001\backend\alembic\versions\abc123_initial_migration_create_all_tables.py ... done
```

### Step 2: Migration 파일 확인

**파일 경로**: `backend/alembic/versions/abc123_initial_migration_create_all_tables.py`

```python
"""Initial migration - create all tables

Revision ID: abc123
Revises:
Create Date: 2025-11-07 10:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'abc123'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('users',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('email', sa.String(length=255), nullable=True),
    sa.Column('phone', sa.String(length=20), nullable=True),
    sa.Column('goal', sa.String(length=50), nullable=True),
    sa.Column('level', sa.String(length=20), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('email')
    )

    op.create_table('leads',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    # ... 나머지 컬럼
    )
    # ... 나머지 테이블
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('leads')
    op.drop_table('users')
    # ...
    # ### end Alembic commands ###
```

---

## 8. Migration 실행 (아직 실행 X!)

**주의**: 실제로 실행하면 PostgreSQL에 테이블이 생성됩니다!

### 실행 전 확인사항

- [ ] PostgreSQL 서버 실행 중
- [ ] POSTGRES_URL 올바르게 설정
- [ ] Migration 파일 검토 완료
- [ ] 백업 완료 (프로덕션인 경우)

### 실행 명령어

```bash
# Dry-run (SQL만 출력, 실행 안함)
alembic upgrade head --sql

# 실제 실행
alembic upgrade head
```

**예상 출력**:
```
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> abc123, Initial migration - create all tables
```

### 확인

```bash
# PostgreSQL에서 테이블 확인
psql -U postgres -d ai_pt_manager -c "\dt"
```

---

## 9. 주요 명령어 치트시트

```bash
# 1. 현재 버전 확인
alembic current

# 2. Migration 히스토리
alembic history --verbose

# 3. Migration 생성 (자동 감지)
alembic revision --autogenerate -m "설명"

# 4. Migration 생성 (수동)
alembic revision -m "설명"

# 5. Migration 실행 (최신)
alembic upgrade head

# 6. Migration 실행 (특정 버전)
alembic upgrade abc123

# 7. Migration 롤백 (1단계)
alembic downgrade -1

# 8. Migration 롤백 (특정 버전)
alembic downgrade abc123

# 9. Migration 롤백 (전체)
alembic downgrade base

# 10. SQL만 출력 (실행 안함)
alembic upgrade head --sql

# 11. 미래 버전과 비교
alembic check

# 12. Migration 병합
alembic merge rev1 rev2 -m "Merge migrations"
```

---

## 10. 자주 발생하는 에러

### 에러 1: "No module named 'database'"

**원인**: sys.path 설정 문제

**해결**:
```python
# alembic/env.py
import sys
from pathlib import Path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))
```

### 에러 2: "POSTGRES_URL 환경 변수가 설정되지 않았습니다"

**원인**: .env 파일 로드 안됨

**해결**:
```python
# alembic/env.py
from dotenv import load_dotenv
load_dotenv()
```

### 에러 3: "Target database is not up to date"

**원인**: DB에 적용 안된 migration 있음

**해결**:
```bash
alembic upgrade head
```

### 에러 4: "Can't locate revision identified by 'abc123'"

**원인**: Migration 파일 삭제됨

**해결**:
```bash
# alembic_version 테이블 확인
psql -c "SELECT * FROM alembic_version;"

# 강제로 버전 초기화 (주의!)
psql -c "DELETE FROM alembic_version;"
```

---

## 11. 다음 단계

1. ✅ Alembic 설치 완료
2. ✅ alembic.ini 설정 완료
3. ✅ alembic/env.py 설정 완료
4. ⏸️ Migration 생성 (다음 가이드)
5. ⏸️ Migration 실행 (다음 가이드)
6. ⏸️ Frontdesk Agent DB 통합 (다음 가이드)

**다음**: [MIGRATION_CREATION_GUIDE.md](./MIGRATION_CREATION_GUIDE.md)
