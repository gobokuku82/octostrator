# Database Implementation Guide
**AI PT Manager - DB Schema 구현 가이드**

작성일: 2025-11-07

---

## 1. 현재 데이터베이스 구조

### 1.1 실제 PostgreSQL 테이블 (현재 존재)

#### LangGraph Infrastructure (자동 생성됨)
```sql
-- AsyncPostgresSaver.setup()이 자동으로 생성
CREATE TABLE checkpoints (
    thread_id VARCHAR NOT NULL,
    checkpoint_ns VARCHAR NOT NULL DEFAULT '',
    checkpoint_id VARCHAR NOT NULL,
    parent_checkpoint_id VARCHAR,
    checkpoint BYTEA NOT NULL,        -- msgpack serialized OctostratorState
    metadata JSONB,
    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id)
);

CREATE TABLE checkpoint_writes (
    thread_id VARCHAR NOT NULL,
    checkpoint_ns VARCHAR NOT NULL DEFAULT '',
    checkpoint_id VARCHAR NOT NULL,
    task_id VARCHAR NOT NULL,
    idx INTEGER NOT NULL,
    channel VARCHAR NOT NULL,
    type VARCHAR,
    value BYTEA,
    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id, task_id, idx)
);
```

**중요**: 이 테이블들은 `checkpointer.setup()`을 호출하면 LangGraph가 **자동으로 생성**합니다!

### 1.2 애플리케이션 State (Python TypedDict)

현재는 **PostgreSQL 테이블이 아니라** Python 코드에만 존재:
- `OctostratorState` (TypedDict)
- `CognitiveState`, `TodoState`, `ExecuteState`, `ResponseState` (TypedDict)
- `FrontdeskState`, `AssessorState`, etc. (TypedDict)

**저장 방식**: `checkpoints.checkpoint` 필드에 msgpack으로 직렬화되어 저장됨

### 1.3 비즈니스 데이터 테이블 (SQLAlchemy 모델만 정의됨)

`backend/database/relation_db/models.py`에 정의되어 있지만 **아직 DB에 생성되지 않음**:
- Lead, Inquiry, Appointment (Frontdesk Agent)
- InBodyData, PostureAnalysis (Assessor Agent)
- Program (Program Designer Agent)
- Attendance, ChurnRisk (Manager Agent)
- SocialMediaPost, Event (Marketing Agent)
- Revenue (Owner Assistant)
- TrainerSkill (Trainer Education)

---

## 2. 데이터 저장 전략 비교

### Phase 3 현재: State 중심 저장 (일시적)

```
checkpoints 테이블
├── thread_id: "session-123"
├── checkpoint: (msgpack serialized)
    └── OctostratorState
        ├── todos: [{"id": "1", "title": "리드 등록", ...}]  ← JSON으로 State 안에 저장
        ├── execution_results: {"frontdesk": {...}}
        └── final_response: "..."
```

**문제점**:
- State가 계속 커짐 (모든 데이터를 담고 있음)
- 데이터 검색 불가 (bytea에 직렬화되어 있음)
- 데이터 분석 불가
- 중복 저장 (매 checkpoint마다 전체 State 저장)

### Phase 5 목표: DB 정규화 + State는 참조만

```
leads 테이블
├── id: 1
├── name: "홍길동"
├── phone: "010-1234-5678"
└── ...

checkpoints 테이블
├── thread_id: "session-123"
├── checkpoint: (msgpack serialized)
    └── OctostratorState
        ├── todos: [{"id": "1", "lead_id": 1, ...}]  ← lead_id만 저장 (FK)
        └── execution_results: {"frontdesk": {"lead_id": 1}}
```

**장점**:
- State 크기 최소화 (ID만 저장)
- 데이터 검색/분석 가능 (SQL 쿼리)
- 중복 제거
- 데이터 무결성 보장 (FK 제약)

---

## 3. DBML Schema의 역할

### 3.1 SCHEMA_DBML.dbml의 현재 역할

**목적**: 전체 시스템 아키텍처 **시각화 및 설계 문서**

포함 내용:
1. **Infrastructure Tables** (실제 존재): checkpoints, checkpoint_writes
2. **Application States** (TypedDict): OctostratorState, Supervisor/Agent States
3. **Business Tables** (SQLAlchemy 모델만 존재): Lead, Appointment, InBodyData 등

**주의**: DBML은 **설계도**일 뿐, 실제 DB를 만들지 않습니다!

### 3.2 DBML → 실제 DB로 변환하는 방법

2가지 옵션:

#### 옵션 1: Alembic Migration (권장)

```bash
# 1. Alembic 초기화
cd backend
alembic init alembic

# 2. models.py에서 자동으로 migration 생성
alembic revision --autogenerate -m "Create business tables"

# 3. Migration 실행
alembic upgrade head
```

#### 옵션 2: DBML → SQL 변환 (수동)

dbdiagram.io에서 Export → PostgreSQL SQL 선택

---

## 4. 실제 구현 단계별 가이드

### Phase 3 (현재): Checkpointer만 사용

```python
# backend/app/octostrator/checkpointer/postgres_checkpointer.py
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

# 1. Checkpointer 생성 (자동으로 테이블 생성됨)
checkpointer = await AsyncPostgresSaver.from_conn_string(POSTGRES_URL)
await checkpointer.setup()  # checkpoints, checkpoint_writes 테이블 생성

# 2. State는 checkpoint에 저장
state = {
    "session_id": "session-123",
    "user_query": "신규 회원 등록",
    "todos": [
        {
            "id": "todo-1",
            "title": "리드 정보 저장",
            "lead_data": {  # ← 모든 데이터를 State에 저장 (임시)
                "name": "홍길동",
                "phone": "010-1234-5678",
                "email": "hong@example.com"
            }
        }
    ]
}
# checkpoint에 msgpack으로 직렬화되어 저장됨
```

### Phase 4 (전환기): SQLAlchemy 모델 정의

```python
# backend/database/relation_db/models.py
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Lead(Base):
    """리드 정보 테이블"""
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    phone = Column(String(20))
    email = Column(String(255))
    # ... (이미 정의되어 있음!)
```

### Phase 5 (목표): DB 통합

#### Step 1: Alembic 설정

```python
# backend/alembic/env.py (새로 생성)
from database.relation_db.models import Base
target_metadata = Base.metadata

# alembic.ini 설정
# sqlalchemy.url = postgresql://user:pass@localhost/dbname
```

#### Step 2: Migration 생성 및 실행

```bash
# 비즈니스 테이블 생성
alembic revision --autogenerate -m "Create leads, appointments, inbody tables"
alembic upgrade head
```

#### Step 3: Agent 코드 수정 (State → DB 저장)

```python
# Before (Phase 3) - State에 모든 데이터 저장
@frontdesk_node
async def handle_inquiry(state: OctostratorState, config: RunnableConfig):
    lead_data = {
        "name": "홍길동",
        "phone": "010-1234-5678",
        "email": "hong@example.com"
    }

    # State에 직접 저장 (문제!)
    return {
        "todos": [
            {
                "id": "todo-1",
                "lead_data": lead_data  # ← State가 비대해짐
            }
        ]
    }

# After (Phase 5) - DB에 저장, State는 ID만 저장
@frontdesk_node
async def handle_inquiry(state: OctostratorState, config: RunnableConfig):
    # 1. DB에 저장
    lead = Lead(
        name="홍길동",
        phone="010-1234-5678",
        email="hong@example.com"
    )
    session.add(lead)
    await session.commit()

    # 2. State에는 ID만 저장 (가볍게!)
    return {
        "todos": [
            {
                "id": "todo-1",
                "lead_id": lead.id  # ← ID만 저장
            }
        ]
    }

# 3. 나중에 데이터 필요 시 DB에서 조회
@another_node
async def use_lead_data(state: OctostratorState):
    lead_id = state["todos"][0]["lead_id"]
    lead = await session.get(Lead, lead_id)
    print(f"Lead: {lead.name}, {lead.phone}")
```

---

## 5. 현재 해야 할 작업

### 5.1 즉시 실행 가능 (Phase 3 완료)

✅ **이미 완료된 것**:
- checkpoints, checkpoint_writes 테이블 (LangGraph 자동 생성)
- SQLAlchemy 모델 정의 (models.py)
- DBML 설계 문서 (SCHEMA_DBML.dbml)

### 5.2 Phase 5로 전환하기 위한 TODO

#### Task 1: Alembic 설정 (우선순위: 높음)

```bash
cd backend
alembic init alembic
```

파일 생성:
- `alembic/env.py`: Base.metadata 연결
- `alembic.ini`: POSTGRES_URL 설정
- `alembic/versions/xxx_create_business_tables.py`: Migration 파일

#### Task 2: Migration 실행

```bash
# 1. 자동 감지로 migration 생성
alembic revision --autogenerate -m "Create business tables from models.py"

# 2. Migration 파일 확인
# alembic/versions/xxx_create_business_tables.py 검토

# 3. 실행
alembic upgrade head

# 4. 확인
psql -d ai_pt_manager -c "\dt"  # 테이블 목록 확인
```

#### Task 3: Agent 코드 리팩토링 (단계적)

**우선순위**:
1. Frontdesk Agent (Lead, Inquiry, Appointment)
2. Assessor Agent (InBodyData, PostureAnalysis)
3. Program Designer Agent (Program)
4. Manager Agent (Attendance, ChurnRisk)
5. Marketing Agent (SocialMediaPost, Event)
6. Owner Assistant (Revenue)
7. Trainer Education (TrainerSkill)

각 Agent별로:
```python
# 1. DB session 주입
from sqlalchemy.ext.asyncio import AsyncSession

@frontdesk_node
async def handle_inquiry(
    state: OctostratorState,
    config: RunnableConfig,
    db: AsyncSession  # ← DB session 추가
):
    # 2. DB 저장
    lead = Lead(...)
    db.add(lead)
    await db.commit()

    # 3. State에 ID만 저장
    return {"todos": [{"lead_id": lead.id}]}
```

#### Task 4: DB Session 관리

```python
# backend/database/relation_db/session.py (새로 생성)
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

engine = create_async_engine(POSTGRES_URL)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Context에서 session 제공
from langgraph.prebuilt import InjectedState

@frontdesk_node
async def handle_inquiry(state: OctostratorState, config: RunnableConfig):
    # config나 Context에서 DB session 가져오기
    async with async_session() as session:
        lead = Lead(...)
        session.add(lead)
        await session.commit()
        # ...
```

---

## 6. 실행 계획 요약

### 단기 (Phase 4 → 5 전환)

1. **Alembic 설정** (1-2시간)
   - `alembic init`
   - `env.py` 설정
   - `alembic.ini` 수정

2. **Migration 생성 및 실행** (30분)
   - `alembic revision --autogenerate`
   - `alembic upgrade head`
   - PostgreSQL에서 테이블 확인

3. **DB Session 관리 구현** (2-3시간)
   - AsyncSession factory 생성
   - Context/Config에서 session 제공 방법 결정
   - Connection pooling 설정

4. **Frontdesk Agent 리팩토링** (테스트) (3-4시간)
   - Lead, Inquiry, Appointment DB 저장
   - State는 ID만 저장
   - 기존 테스트 통과 확인

### 중기 (나머지 Agent 리팩토링)

5. **나머지 6개 Agent DB 통합** (1주일)
   - Assessor → InBodyData, PostureAnalysis
   - ProgramDesigner → Program
   - Manager → Attendance, ChurnRisk
   - Marketing → SocialMediaPost, Event
   - OwnerAssistant → Revenue
   - TrainerEducation → TrainerSkill

6. **State Schema 최적화** (2-3일)
   - State에서 불필요한 필드 제거
   - ID 참조로 변경
   - State 크기 50% 이상 감소 목표

### 장기 (고급 기능)

7. **데이터 분석 대시보드** (2주)
   - DB에서 직접 쿼리
   - 리드 전환율 분석
   - 회원 이탈 예측
   - 매출 리포트

8. **Migration 관리 체계** (계속)
   - Schema 변경 시 Alembic migration 생성
   - Rollback 전략
   - Production 배포 절차

---

## 7. 주요 참고 자료

### 파일 위치

- **Checkpointer**: `backend/app/octostrator/checkpointer/postgres_checkpointer.py`
- **SQLAlchemy Models**: `backend/database/relation_db/models.py`
- **DBML Schema**: `reports/sys/SCHEMA_DBML.dbml`
- **State Definitions**: `backend/app/octostrator/states/state.py`

### 명령어 치트시트

```bash
# Checkpointer 테이블 생성 (자동)
# Python에서 await checkpointer.setup() 실행

# Alembic 설정
cd backend
alembic init alembic

# Migration 생성
alembic revision --autogenerate -m "Create business tables"

# Migration 실행
alembic upgrade head

# Migration 롤백
alembic downgrade -1

# 현재 버전 확인
alembic current

# PostgreSQL 확인
psql -d ai_pt_manager -c "\dt"  # 테이블 목록
psql -d ai_pt_manager -c "\d leads"  # 테이블 구조
```

---

## 8. FAQ

### Q1: DBML의 State 테이블들도 실제로 만들어야 하나요?

**A**: 아니요! `OctostratorState`, `CognitiveState` 등은 Python TypedDict이고, `checkpoints.checkpoint` 필드에 msgpack으로 저장됩니다. 별도 테이블로 만들 필요 없습니다.

### Q2: 언제 Alembic을 써야 하나요?

**A**: **비즈니스 데이터 테이블** (Lead, Appointment, InBodyData 등)을 실제로 PostgreSQL에 만들 때 사용합니다. Checkpointer 테이블은 LangGraph가 자동으로 만들어줍니다.

### Q3: 현재 State에 저장된 데이터는 어떻게 마이그레이션하나요?

**A**:
1. Alembic으로 비즈니스 테이블 생성
2. 기존 checkpoint에서 데이터 읽기
3. SQLAlchemy로 새 테이블에 삽입
4. State를 ID 참조로 업데이트
5. 새 checkpoint 저장

### Q4: DBML을 직접 SQL로 변환할 수 있나요?

**A**: 가능하지만 권장하지 않습니다. dbdiagram.io에서 Export → PostgreSQL SQL 가능하지만, Alembic을 사용하면:
- Migration 버전 관리
- 자동 롤백
- 팀 협업 용이

### Q5: thread_id = session_id 매핑은 어떻게 관리하나요?

**A**:
```python
# Graph 실행 시
thread_id = state["session_id"]
config = {"configurable": {"thread_id": thread_id}}
await graph.ainvoke(state, config, checkpointer=checkpointer)
```

LangGraph는 자동으로 `config["configurable"]["thread_id"]`를 `checkpoints.thread_id`로 매핑합니다.

---

## 9. 다음 단계 실행 가이드

**지금 바로 시작하려면**:

```bash
# 1. Alembic 설치 (이미 설치되어 있을 수 있음)
pip install alembic

# 2. Backend 디렉토리로 이동
cd C:\kdy\Projects\AI_PTmanager\beta_v001\backend

# 3. Alembic 초기화
alembic init alembic

# 4. alembic/env.py 수정
# - from database.relation_db.models import Base 추가
# - target_metadata = Base.metadata 설정

# 5. alembic.ini 수정
# - sqlalchemy.url = POSTGRES_URL로 설정

# 6. Migration 생성
alembic revision --autogenerate -m "Create business tables"

# 7. Migration 실행
alembic upgrade head

# 8. 확인
# PostgreSQL에 접속해서 테이블 목록 확인
```

**도움이 필요하면**:
- "Alembic 설정 도와줘"
- "Frontdesk Agent DB 통합 시작하자"
- "Migration 파일 검토해줘"

라고 요청하세요!
