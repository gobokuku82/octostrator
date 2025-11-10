# Frontdesk Agent DB 통합 완전 가이드
**AI PT Manager - Phase 3 → Phase 5 전환**

작성일: 2025-11-07

---

## 1. 개요

### 목표

**Before (Phase 3)**: State에 모든 데이터 저장
```python
state["todos"] = [{
    "lead_data": {  # ← State에 전체 데이터 저장 (문제!)
        "name": "홍길동",
        "phone": "010-1234-5678",
        "email": "hong@example.com"
    }
}]
```

**After (Phase 5)**: DB에 저장, State는 ID만
```python
# 1. DB에 저장
lead = Lead(name="홍길동", phone="010-1234-5678", email="hong@example.com")
session.add(lead)
await session.commit()

# 2. State에는 ID만
state["todos"] = [{
    "lead_id": lead.id  # ← ID만 저장 (가볍게!)
}]
```

### 장점

1. **State 크기 50% 이상 감소**
2. **데이터 영속성** (checkpoint와 별도로 저장)
3. **검색/분석 가능** (SQL 쿼리)
4. **중복 제거** (매 checkpoint마다 같은 데이터 저장 안함)

---

## 2. 사전 준비

### 체크리스트

- [ ] Alembic 설정 완료
- [ ] Migration 실행 완료 (leads, inquiries, appointments 테이블 생성)
- [ ] PostgreSQL 테이블 확인 (`\dt`)

### 확인 명령어

```bash
# 테이블 확인
psql -U postgres -d ai_pt_manager -c "\dt"

# leads 테이블 구조 확인
psql -U postgres -d ai_pt_manager -c "\d leads"

# 예상 출력:
                                     Table "public.leads"
   Column   |          Type          | Nullable |              Default
------------+------------------------+----------+-----------------------------------
 id         | integer                | not null | nextval('leads_id_seq'::regclass)
 name       | character varying(100) | not null |
 phone      | character varying(20)  |          |
 email      | character varying(255) |          |
 ...
```

---

## 3. 파일 구조

### 변경할 파일들

```
backend/app/octostrator/
├── agents/
│   └── frontdesk/
│       └── frontdesk_agent.py    ← 수정 필요
├── database/
│   └── session.py                ← 새로 생성
└── states/
    └── state.py                  ← State 스키마 수정
```

---

## 4. Step 1: Database Session 관리

### 4.1 session.py 생성

**파일 경로**: `backend/database/session.py`

```python
"""Database Session Management
Phase 5: Async SQLAlchemy session factory
"""
import os
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker
)
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()

# PostgreSQL URL
POSTGRES_URL = os.getenv("POSTGRES_URL")
if not POSTGRES_URL:
    raise ValueError("POSTGRES_URL 환경 변수가 설정되지 않았습니다.")

# Async Engine 생성
# postgresql:// → postgresql+asyncpg://
async_url = POSTGRES_URL.replace("postgresql://", "postgresql+asyncpg://")

engine = create_async_engine(
    async_url,
    echo=False,  # SQL 로깅 (개발 시 True로 설정)
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,  # 연결 유효성 검사
)

# Session Factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,  # 중요! commit 후에도 객체 사용 가능
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Database session generator

    Usage:
        async with get_db() as session:
            lead = Lead(name="홍길동")
            session.add(lead)
            await session.commit()
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_db_session() -> AsyncSession:
    """단일 session 생성 (간단한 사용)

    Usage:
        session = await get_db_session()
        try:
            lead = Lead(name="홍길동")
            session.add(lead)
            await session.commit()
        finally:
            await session.close()
    """
    return AsyncSessionLocal()
```

### 4.2 asyncpg 설치

```bash
pip install asyncpg
# 또는
pip install sqlalchemy[asyncio]
```

---

## 5. Step 2: State Schema 수정

### 5.1 현재 State 구조

**파일**: `backend/app/octostrator/states/state.py`

```python
class OctostratorState(TypedDict):
    session_id: str
    user_query: str

    # ===== 현재 방식 (Phase 3) =====
    todos: List[Dict[str, Any]]  # 전체 데이터 포함
    # 예: [{"id": "1", "lead_data": {"name": "홍길동", ...}}]
```

### 5.2 수정된 State 구조

```python
class OctostratorState(TypedDict):
    session_id: str
    user_query: str

    # ===== 새 방식 (Phase 5) =====
    todos: List[Dict[str, Any]]  # ID만 포함
    # 예: [{"id": "1", "lead_id": 123}]

    # 옵션: DB IDs 추적 (명시적)
    lead_ids: NotRequired[List[int]]
    appointment_ids: NotRequired[List[int]]
    inquiry_ids: NotRequired[List[int]]
```

### 5.3 Todo 스키마 예시

```python
# Before
todo_item = {
    "id": "todo-1",
    "title": "리드 등록",
    "lead_data": {  # ← 모든 데이터
        "name": "홍길동",
        "phone": "010-1234-5678",
        "email": "hong@example.com",
        "source": "website"
    }
}

# After
todo_item = {
    "id": "todo-1",
    "title": "리드 등록",
    "lead_id": 123,  # ← ID만
    "status": "completed"
}
```

---

## 6. Step 3: Frontdesk Agent 코드 수정

### 6.1 현재 코드 구조

**파일**: `backend/app/octostrator/agents/frontdesk/frontdesk_agent.py`

```python
# 현재 방식 (Phase 3)
@frontdesk_node
async def handle_inquiry(
    state: OctostratorState,
    config: RunnableConfig
) -> Dict[str, Any]:
    """문의 처리"""

    # 1. LLM으로 리드 정보 추출
    lead_data = {
        "name": "홍길동",
        "phone": "010-1234-5678",
        "email": "hong@example.com"
    }

    # 2. State에 직접 저장 (문제!)
    return {
        "todos": [
            {
                "id": "todo-1",
                "title": "리드 등록",
                "lead_data": lead_data  # ← State가 비대해짐
            }
        ]
    }
```

### 6.2 수정된 코드

```python
# 새 방식 (Phase 5)
from database.session import get_db_session
from database.relation_db.models import Lead, Inquiry

@frontdesk_node
async def handle_inquiry(
    state: OctostratorState,
    config: RunnableConfig
) -> Dict[str, Any]:
    """문의 처리 - DB 통합"""

    # 1. LLM으로 리드 정보 추출 (동일)
    lead_data = {
        "name": "홍길동",
        "phone": "010-1234-5678",
        "email": "hong@example.com",
        "source": "website",
        "interest": "weight_loss",
        "score": 75,
        "status": "new"
    }

    # 2. DB에 저장
    session = await get_db_session()
    try:
        # Lead 생성
        lead = Lead(**lead_data)
        session.add(lead)
        await session.flush()  # ID 할당받기 (commit 전)

        lead_id = lead.id  # ← DB에서 자동 생성된 ID

        # Commit
        await session.commit()

        print(f"[Frontdesk] ✓ Lead 저장 완료: ID={lead_id}, Name={lead.name}")

    except Exception as e:
        await session.rollback()
        print(f"[Frontdesk] ✗ Lead 저장 실패: {e}")
        raise
    finally:
        await session.close()

    # 3. State에는 ID만 저장 (가볍게!)
    return {
        "todos": [
            {
                "id": "todo-1",
                "title": "리드 등록",
                "lead_id": lead_id,  # ← ID만!
                "status": "completed"
            }
        ],
        "lead_ids": [lead_id]  # 옵션: 명시적 추적
    }
```

---

## 7. Step 4: DB 데이터 조회

### 7.1 다른 노드에서 Lead 데이터 사용

```python
@another_node
async def use_lead_data(
    state: OctostratorState,
    config: RunnableConfig
) -> Dict[str, Any]:
    """Lead 데이터를 사용하는 노드"""

    # 1. State에서 lead_id 가져오기
    lead_id = state["todos"][0].get("lead_id")

    if not lead_id:
        raise ValueError("Lead ID not found in state")

    # 2. DB에서 조회
    session = await get_db_session()
    try:
        from sqlalchemy import select

        stmt = select(Lead).where(Lead.id == lead_id)
        result = await session.execute(stmt)
        lead = result.scalar_one_or_none()

        if not lead:
            raise ValueError(f"Lead not found: {lead_id}")

        print(f"[Node] Lead 조회: {lead.name} ({lead.phone})")

        # 3. Lead 데이터 사용
        message = f"안녕하세요 {lead.name}님! {lead.interest}에 관심이 있으시군요."

    finally:
        await session.close()

    return {"final_response": message}
```

### 7.2 조회 패턴

#### 패턴 1: ID로 단일 조회

```python
from sqlalchemy import select

session = await get_db_session()
stmt = select(Lead).where(Lead.id == lead_id)
result = await session.execute(stmt)
lead = result.scalar_one_or_none()  # None or Lead object
```

#### 패턴 2: 다중 조회

```python
stmt = select(Lead).where(Lead.status == "new").limit(10)
result = await session.execute(stmt)
leads = result.scalars().all()  # List[Lead]
```

#### 패턴 3: JOIN (Lead + Inquiry)

```python
from sqlalchemy.orm import selectinload

stmt = select(Lead).options(
    selectinload(Lead.inquiries)  # FK 관계 로드
).where(Lead.id == lead_id)

result = await session.execute(stmt)
lead = result.scalar_one()

# Lead의 모든 Inquiry 접근
for inquiry in lead.inquiries:
    print(inquiry.inquiry_text)
```

---

## 8. Step 5: 전체 워크플로우 예시

### 시나리오: 리드 등록 → 상담 예약

```python
# ===== Node 1: 리드 등록 =====
@frontdesk_node
async def register_lead(state: OctostratorState, config: RunnableConfig):
    """리드 등록"""
    session = await get_db_session()
    try:
        lead = Lead(
            name="홍길동",
            phone="010-1234-5678",
            email="hong@example.com",
            source="website",
            interest="weight_loss",
            score=85,
            status="new"
        )
        session.add(lead)
        await session.flush()
        lead_id = lead.id
        await session.commit()
    finally:
        await session.close()

    return {"lead_ids": [lead_id]}


# ===== Node 2: 문의 기록 =====
@frontdesk_node
async def record_inquiry(state: OctostratorState, config: RunnableConfig):
    """문의 내역 저장"""
    lead_id = state["lead_ids"][0]

    session = await get_db_session()
    try:
        inquiry = Inquiry(
            lead_id=lead_id,
            inquiry_text="PT 프로그램에 대해 문의합니다.",
            response_text="안녕하세요! 맞춤형 PT 프로그램을 제공해드립니다.",
            inquiry_type="program",
            handled_by="AI Agent"
        )
        session.add(inquiry)
        await session.flush()
        inquiry_id = inquiry.id
        await session.commit()
    finally:
        await session.close()

    return {"inquiry_ids": [inquiry_id]}


# ===== Node 3: 예약 생성 =====
@frontdesk_node
async def schedule_appointment(state: OctostratorState, config: RunnableConfig):
    """상담 예약"""
    lead_id = state["lead_ids"][0]

    from datetime import datetime, timedelta

    session = await get_db_session()
    try:
        appointment = Appointment(
            lead_id=lead_id,
            appointment_date=datetime.now() + timedelta(days=2),
            appointment_type="consultation",
            status="scheduled",
            notes="첫 상담"
        )
        session.add(appointment)
        await session.flush()
        appointment_id = appointment.id
        await session.commit()
    finally:
        await session.close()

    return {
        "appointment_ids": [appointment_id],
        "final_response": f"상담이 예약되었습니다. (Appointment ID: {appointment_id})"
    }


# ===== Node 4: 최종 응답 =====
@response_node
async def generate_response(state: OctostratorState, config: RunnableConfig):
    """최종 응답 생성 (DB 데이터 조회)"""
    lead_id = state["lead_ids"][0]
    appointment_id = state["appointment_ids"][0]

    session = await get_db_session()
    try:
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        # Lead + Appointment JOIN
        stmt = select(Lead).options(
            selectinload(Lead.appointments)
        ).where(Lead.id == lead_id)

        result = await session.execute(stmt)
        lead = result.scalar_one()

        appointment = lead.appointments[0]

        response = f"""
안녕하세요 {lead.name}님!

{lead.interest} 프로그램 상담이 예약되었습니다.

📅 예약 일시: {appointment.appointment_date.strftime('%Y-%m-%d %H:%M')}
📞 연락처: {lead.phone}
📧 이메일: {lead.email}

감사합니다!
        """.strip()

    finally:
        await session.close()

    return {"final_response": response}
```

---

## 9. Step 6: 에러 처리

### 9.1 DB 저장 실패

```python
session = await get_db_session()
try:
    lead = Lead(name="홍길동", ...)
    session.add(lead)
    await session.commit()

except IntegrityError as e:
    # FK 제약 위반, UNIQUE 제약 위반 등
    await session.rollback()
    print(f"[DB Error] Integrity Error: {e}")
    return {"error": "이미 존재하는 이메일입니다."}

except Exception as e:
    await session.rollback()
    print(f"[DB Error] {type(e).__name__}: {e}")
    return {"error": "데이터 저장에 실패했습니다."}

finally:
    await session.close()
```

### 9.2 조회 실패

```python
stmt = select(Lead).where(Lead.id == lead_id)
result = await session.execute(stmt)
lead = result.scalar_one_or_none()

if not lead:
    return {"error": f"Lead not found: {lead_id}"}
```

---

## 10. Step 7: 테스트

### 10.1 수동 테스트

```python
# backend/test_frontdesk_db.py
import asyncio
from database.session import get_db_session
from database.relation_db.models import Lead, Inquiry, Appointment
from datetime import datetime, timedelta


async def test_frontdesk_workflow():
    """Frontdesk DB 통합 테스트"""
    print("=== Frontdesk DB Integration Test ===\n")

    # 1. Lead 생성
    print("1. Creating Lead...")
    session = await get_db_session()
    try:
        lead = Lead(
            name="테스트 회원",
            phone="010-9999-8888",
            email="test@example.com",
            source="test",
            interest="muscle_gain",
            score=90,
            status="new"
        )
        session.add(lead)
        await session.commit()
        lead_id = lead.id
        print(f"   ✓ Lead created: ID={lead_id}\n")
    finally:
        await session.close()

    # 2. Inquiry 생성
    print("2. Creating Inquiry...")
    session = await get_db_session()
    try:
        inquiry = Inquiry(
            lead_id=lead_id,
            inquiry_text="PT 프로그램이 궁금합니다.",
            response_text="맞춤형 프로그램을 제공해드립니다.",
            inquiry_type="program",
            handled_by="AI Agent"
        )
        session.add(inquiry)
        await session.commit()
        inquiry_id = inquiry.id
        print(f"   ✓ Inquiry created: ID={inquiry_id}\n")
    finally:
        await session.close()

    # 3. Appointment 생성
    print("3. Creating Appointment...")
    session = await get_db_session()
    try:
        appointment = Appointment(
            lead_id=lead_id,
            appointment_date=datetime.now() + timedelta(days=3),
            appointment_type="consultation",
            status="scheduled",
            notes="첫 상담 예약"
        )
        session.add(appointment)
        await session.commit()
        appointment_id = appointment.id
        print(f"   ✓ Appointment created: ID={appointment_id}\n")
    finally:
        await session.close()

    # 4. 조회 테스트
    print("4. Querying Lead with relationships...")
    session = await get_db_session()
    try:
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        stmt = select(Lead).options(
            selectinload(Lead.inquiries),
            selectinload(Lead.appointments)
        ).where(Lead.id == lead_id)

        result = await session.execute(stmt)
        lead = result.scalar_one()

        print(f"   Lead: {lead.name} ({lead.phone})")
        print(f"   Inquiries: {len(lead.inquiries)}")
        print(f"   Appointments: {len(lead.appointments)}")
        print(f"   ✓ Query successful\n")
    finally:
        await session.close()

    # 5. 정리
    print("5. Cleanup...")
    session = await get_db_session()
    try:
        # Cascade delete (FK 설정되어 있으면 자동 삭제)
        await session.execute(delete(Lead).where(Lead.id == lead_id))
        await session.commit()
        print("   ✓ Test data cleaned up\n")
    finally:
        await session.close()

    print("=== Test Complete ===")


if __name__ == "__main__":
    asyncio.run(test_frontdesk_workflow())
```

### 10.2 실행

```bash
cd backend
python test_frontdesk_db.py
```

**예상 출력**:
```
=== Frontdesk DB Integration Test ===

1. Creating Lead...
   ✓ Lead created: ID=1

2. Creating Inquiry...
   ✓ Inquiry created: ID=1

3. Creating Appointment...
   ✓ Appointment created: ID=1

4. Querying Lead with relationships...
   Lead: 테스트 회원 (010-9999-8888)
   Inquiries: 1
   Appointments: 1
   ✓ Query successful

5. Cleanup...
   ✓ Test data cleaned up

=== Test Complete ===
```

---

## 11. 체크리스트

### 구현 전

- [ ] Alembic migration 완료
- [ ] PostgreSQL 테이블 생성 확인
- [ ] asyncpg 설치
- [ ] session.py 생성

### 구현 중

- [ ] frontdesk_agent.py 수정 (DB 저장)
- [ ] State schema 업데이트
- [ ] 에러 처리 추가
- [ ] 로깅 추가

### 구현 후

- [ ] 수동 테스트 실행
- [ ] DB 데이터 확인 (psql)
- [ ] State 크기 확인 (checkpoint)
- [ ] 기존 테스트 통과 확인

---

## 12. 다음 Agent 통합

Frontdesk 완료 후 다음 순서:

1. ✅ Frontdesk (Lead, Inquiry, Appointment)
2. ⏭️ Assessor (InBodyData, PostureAnalysis)
3. ⏭️ ProgramDesigner (Program, MealLog, WorkoutRoutine)
4. ⏭️ Manager (Attendance, ChurnRisk, Schedule)
5. ⏭️ Marketing (SocialMediaPost, Event)
6. ⏭️ OwnerAssistant (Revenue)
7. ⏭️ TrainerEducation (TrainerSkill)

같은 패턴으로 진행!

---

## 13. 참고 자료

- [ALEMBIC_SETUP_GUIDE.md](./ALEMBIC_SETUP_GUIDE.md)
- [MIGRATION_CREATION_GUIDE.md](./MIGRATION_CREATION_GUIDE.md)
- [DATABASE_IMPLEMENTATION_GUIDE.md](./DATABASE_IMPLEMENTATION_GUIDE.md)
- SQLAlchemy Async: https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html
