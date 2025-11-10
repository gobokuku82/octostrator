"""Database Package - Domain-Agnostic Database Layer

⚠️  CURRENT STATE: Generic Database Layer (Domain-Independent)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

This package provides generic database infrastructure that works across all domains
(Fitness, Medical, Legal, Education, etc.).

3가지 데이터베이스 타입:
- relation_db: PostgreSQL (정형 데이터 - SQLAlchemy ORM)
- vector_db: FAISS (벡터 데이터 - 임베딩, 유사도 검색)
- unstructured_db: Files (비정형 데이터 - 이미지, PDF, 문서)

AVAILABLE COMPONENTS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Session Management (session.py):
   - get_db(): Dependency for FastAPI routes
   - get_db_session(): Async context manager for database sessions
   - AsyncSessionLocal: SQLAlchemy async session factory

2. Utility Functions (utils.py):
   - JSON handling: parse_json_field(), serialize_json_field()
   - Datetime handling: datetime_to_str(), parse_datetime()
   - Safe type casting: safe_get_int(), safe_get_float(), safe_get_str()

3. Archived PT-Specific Files (relation_db/archive_fitness/):
   - fitness.db: SQLite database with PT data
   - models.py: PT-specific SQLAlchemy models
   - mock_data.py: PT test data
   - nutrition_seed_data.py: PT nutrition data

🔮 HOW TO ADD DOMAIN-SPECIFIC CRUD OPERATIONS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

See CRUD_PATTERNS_GUIDE.md for comprehensive examples.

Option A: Separate CRUD Modules (Recommended for Complex Domains)
────────────────────────────────────────────────────────────────────────
Create domain-specific CRUD files:

    backend/database/
    ├── __init__.py           (this file)
    ├── session.py            (generic session management)
    ├── utils.py              (generic utilities)
    ├── fitness_crud.py       (Fitness domain CRUD)
    ├── medical_crud.py       (Medical domain CRUD)
    ├── legal_crud.py         (Legal domain CRUD)
    └── education_crud.py     (Education domain CRUD)

Example fitness_crud.py:
    '''
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession
    from app.models.fitness_models import MemberProgress, WorkoutProgram
    from .utils import parse_json_field, serialize_json_field

    async def create_member_progress(
        db: AsyncSession,
        user_id: int,
        date: str,
        metrics: dict
    ) -> MemberProgress:
        progress = MemberProgress(
            user_id=user_id,
            date=date,
            metrics=serialize_json_field(metrics)
        )
        db.add(progress)
        await db.commit()
        await db.refresh(progress)
        return progress

    async def get_member_progress_history(
        db: AsyncSession,
        user_id: int,
        limit: int = 10
    ) -> List[MemberProgress]:
        result = await db.execute(
            select(MemberProgress)
            .filter(MemberProgress.user_id == user_id)
            .order_by(MemberProgress.date.desc())
            .limit(limit)
        )
        return result.scalars().all()
    '''

Then import in __init__.py:
    from . import fitness_crud
    __all__ = [..., "fitness_crud"]

Option B: Inline in Agent Nodes (Recommended for Simple Domains)
────────────────────────────────────────────────────────────────────────
Write CRUD operations directly in agent nodes:

    # In backend/app/octostrator/agents/medical/medical_nodes.py
    from sqlalchemy import select
    from app.models.medical_models import Patient, MedicalRecord
    from backend.database import get_db_session

    async def patient_assessment_node(state):
        async with get_db_session() as db:
            # Inline CRUD
            result = await db.execute(
                select(Patient).filter(Patient.id == state["patient_id"])
            )
            patient = result.scalar_one_or_none()

            # Process...

            # Save record
            record = MedicalRecord(
                patient_id=patient.id,
                diagnosis=state["diagnosis"],
                notes=state["notes"]
            )
            db.add(record)
            await db.commit()

Option C: Generic Repository Pattern (Advanced)
────────────────────────────────────────────────────────────────────────
Create a generic repository class:

    # backend/database/repository.py
    from typing import TypeVar, Generic, Type, List, Optional
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession

    T = TypeVar('T')

    class GenericRepository(Generic[T]):
        def __init__(self, model: Type[T], db: AsyncSession):
            self.model = model
            self.db = db

        async def create(self, **kwargs) -> T:
            instance = self.model(**kwargs)
            self.db.add(instance)
            await self.db.commit()
            await self.db.refresh(instance)
            return instance

        async def get_by_id(self, id: int) -> Optional[T]:
            result = await self.db.execute(
                select(self.model).filter(self.model.id == id)
            )
            return result.scalar_one_or_none()

        async def get_all(self, limit: int = 100) -> List[T]:
            result = await self.db.execute(
                select(self.model).limit(limit)
            )
            return result.scalars().all()

Usage:
    from backend.database.repository import GenericRepository
    from app.models.legal_models import LegalCase

    async with get_db_session() as db:
        case_repo = GenericRepository(LegalCase, db)
        case = await case_repo.create(
            title="Contract Dispute",
            client_id=123,
            status="open"
        )

DOMAIN EXAMPLES:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Fitness Domain CRUD:
   - create_member_progress()
   - get_workout_program()
   - update_nutrition_plan()
   - delete_inbody_record()

2. Medical Domain CRUD:
   - create_patient_record()
   - get_medical_history()
   - update_prescription()
   - search_diagnoses()

3. Legal Domain CRUD:
   - create_legal_case()
   - get_contract_by_id()
   - update_case_status()
   - search_precedents()

4. Education Domain CRUD:
   - create_assignment()
   - get_student_submissions()
   - update_grade()
   - get_course_analytics()

TESTING CRUD OPERATIONS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# backend/test_your_domain_crud.py
import asyncio
from backend.database import get_db_session
from app.models.your_domain_models import YourModel

async def test_crud():
    async with get_db_session() as db:
        # Create
        instance = YourModel(field1="value1", field2="value2")
        db.add(instance)
        await db.commit()
        await db.refresh(instance)
        print(f"Created: {instance.id}")

        # Read
        from sqlalchemy import select
        result = await db.execute(
            select(YourModel).filter(YourModel.id == instance.id)
        )
        retrieved = result.scalar_one()
        print(f"Retrieved: {retrieved}")

        # Update
        retrieved.field1 = "new_value"
        await db.commit()
        print("Updated")

        # Delete
        await db.delete(retrieved)
        await db.commit()
        print("Deleted")

if __name__ == "__main__":
    asyncio.run(test_crud())

MIGRATION FROM PT-SPECIFIC TO DOMAIN-SPECIFIC:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Previously, this system had PT-specific CRUD modules (frontdesk_crud, assessor_crud).
These have been removed during the generalization to domain-agnostic architecture.

Archived PT files are available in:
    backend/database/relation_db/archive_fitness/

You can reference these archived files when implementing your domain-specific CRUD,
but note that the models they reference have also been archived/generalized.

For detailed patterns and examples, see:
    backend/database/CRUD_PATTERNS_GUIDE.md
"""
from . import utils
from .session import get_db, get_db_session, AsyncSessionLocal

__all__ = [
    "utils",
    "get_db",
    "get_db_session",
    "AsyncSessionLocal",
    # 🔮 Add your domain-specific CRUD imports here:
    # "fitness_crud",
    # "medical_crud",
    # "legal_crud",
    # "education_crud",
]
