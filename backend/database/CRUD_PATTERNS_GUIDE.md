# CRUD Patterns Guide for Domain-Specific Database Operations

**Last Updated**: 2025-11-10
**System**: Specialist Agent System (Domain-Agnostic)
**Purpose**: Comprehensive guide for implementing domain-specific CRUD operations

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Three Implementation Strategies](#three-implementation-strategies)
3. [Complete Domain Examples](#complete-domain-examples)
   - [Fitness Domain](#fitness-domain-complete-example)
   - [Medical Domain](#medical-domain-complete-example)
   - [Legal Domain](#legal-domain-complete-example)
   - [Education Domain](#education-domain-complete-example)
4. [Common CRUD Patterns](#common-crud-patterns)
5. [Testing Strategies](#testing-strategies)
6. [Best Practices](#best-practices)
7. [Migration Guide](#migration-guide)

---

## Overview

### Current State

The Specialist Agent System provides a **domain-agnostic database layer** with:

- **Generic session management** (`session.py`)
- **Generic utility functions** (`utils.py`)
- **No domain-specific CRUD** (clean slate for any domain)

### Available Generic Tools

```python
from backend.database import (
    get_db,              # FastAPI dependency
    get_db_session,      # Async context manager
    AsyncSessionLocal,   # Session factory
    utils,               # JSON/datetime/type utilities
)
```

### Your Task

Implement domain-specific CRUD operations using one of three strategies:

1. **Separate CRUD Modules** - Best for complex domains with many operations
2. **Inline in Agent Nodes** - Best for simple domains with few operations
3. **Generic Repository Pattern** - Best for standardized CRUD across multiple domains

---

## Three Implementation Strategies

### Strategy A: Separate CRUD Modules (Recommended for Complex Domains)

**When to Use**:
- Complex domain with 10+ CRUD operations
- Shared CRUD logic across multiple agents
- Need for comprehensive testing of database operations
- Domain examples: Fitness (many workout/nutrition operations), Medical (complex patient records)

**Structure**:
```
backend/database/
├── __init__.py
├── session.py
├── utils.py
├── fitness_crud.py      ← Your domain CRUD
├── medical_crud.py      ← Your domain CRUD
└── legal_crud.py        ← Your domain CRUD
```

**Pros**:
- ✅ Clear separation of concerns
- ✅ Easy to test in isolation
- ✅ Reusable across multiple agents
- ✅ Comprehensive error handling in one place

**Cons**:
- ❌ Extra file to maintain
- ❌ Need to update `__init__.py` exports

---

### Strategy B: Inline in Agent Nodes (Recommended for Simple Domains)

**When to Use**:
- Simple domain with <5 CRUD operations
- CRUD operations specific to one agent
- Rapid prototyping
- Domain examples: Simple Education assignments, Legal document storage

**Structure**:
```python
# In backend/app/octostrator/agents/your_domain/your_agent_nodes.py
from sqlalchemy import select
from backend.database import get_db_session
from app.models.your_domain_models import YourModel

async def your_processing_node(state):
    async with get_db_session() as db:
        # Inline CRUD - no separate file
        result = await db.execute(
            select(YourModel).filter(YourModel.id == state["id"])
        )
        instance = result.scalar_one_or_none()

        # Process...

        # Save
        instance.status = "processed"
        await db.commit()

        return {"processed": True}
```

**Pros**:
- ✅ Fast to implement
- ✅ No extra files
- ✅ Easy to see CRUD in context

**Cons**:
- ❌ Harder to reuse across agents
- ❌ Can make node functions long
- ❌ Harder to test database logic separately

---

### Strategy C: Generic Repository Pattern (Advanced)

**When to Use**:
- Multiple domains with similar CRUD needs
- Standardized operations across all domains
- DRY principle (Don't Repeat Yourself)
- Domain examples: Multi-tenant systems, SaaS platforms

**Structure**:
```
backend/database/
├── __init__.py
├── session.py
├── utils.py
└── repository.py        ← Generic repository
```

**Implementation**:
```python
# backend/database/repository.py
from typing import TypeVar, Generic, Type, List, Optional
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar('T')

class GenericRepository(Generic[T]):
    """Generic repository for CRUD operations on any SQLAlchemy model"""

    def __init__(self, model: Type[T], db: AsyncSession):
        self.model = model
        self.db = db

    async def create(self, **kwargs) -> T:
        """Create a new instance"""
        instance = self.model(**kwargs)
        self.db.add(instance)
        await self.db.commit()
        await self.db.refresh(instance)
        return instance

    async def get_by_id(self, id: int) -> Optional[T]:
        """Get instance by ID"""
        result = await self.db.execute(
            select(self.model).filter(self.model.id == id)
        )
        return result.scalar_one_or_none()

    async def get_all(self, limit: int = 100, offset: int = 0) -> List[T]:
        """Get all instances with pagination"""
        result = await self.db.execute(
            select(self.model).limit(limit).offset(offset)
        )
        return result.scalars().all()

    async def update(self, id: int, **kwargs) -> Optional[T]:
        """Update instance by ID"""
        await self.db.execute(
            update(self.model)
            .where(self.model.id == id)
            .values(**kwargs)
        )
        await self.db.commit()
        return await self.get_by_id(id)

    async def delete(self, id: int) -> bool:
        """Delete instance by ID"""
        result = await self.db.execute(
            delete(self.model).where(self.model.id == id)
        )
        await self.db.commit()
        return result.rowcount > 0
```

**Usage**:
```python
from backend.database.repository import GenericRepository
from app.models.fitness_models import WorkoutProgram

async with get_db_session() as db:
    workout_repo = GenericRepository(WorkoutProgram, db)

    # Create
    program = await workout_repo.create(
        name="Beginner Strength",
        user_id=123,
        duration_weeks=8
    )

    # Read
    retrieved = await workout_repo.get_by_id(program.id)

    # Update
    updated = await workout_repo.update(
        program.id,
        status="active"
    )

    # Delete
    deleted = await workout_repo.delete(program.id)
```

**Pros**:
- ✅ DRY - write once, use everywhere
- ✅ Consistent interface across all models
- ✅ Easy to add new models

**Cons**:
- ❌ Less flexible for complex queries
- ❌ Requires understanding of generics
- ❌ May need extension for domain-specific operations

---

## Complete Domain Examples

### Fitness Domain Complete Example

**Models** (in `backend/app/models/fitness_models.py`):
```python
from sqlalchemy import Column, Integer, String, Float, Date, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.models.base import Base

class MemberProgress(Base):
    """Fitness member progress tracking"""
    __tablename__ = "member_progress"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(Date, nullable=False)
    weight_kg = Column(Float)
    body_fat_percentage = Column(Float)
    muscle_mass_kg = Column(Float)
    notes = Column(Text)
    measurements = Column(Text)  # JSON: chest, waist, hips, etc.
    created_at = Column(DateTime, default=datetime.utcnow)

class WorkoutProgram(Base):
    """Workout program for members"""
    __tablename__ = "workout_programs"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(200), nullable=False)
    goal = Column(String(100))  # muscle_gain, weight_loss, endurance
    duration_weeks = Column(Integer)
    exercises = Column(Text)  # JSON: list of exercises
    status = Column(String(50), default="draft")  # draft, active, completed
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

class NutritionPlan(Base):
    """Nutrition plan for members"""
    __tablename__ = "nutrition_plans"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(200), nullable=False)
    daily_calories = Column(Integer)
    macro_ratio = Column(Text)  # JSON: protein, carbs, fat percentages
    meal_plan = Column(Text)  # JSON: meals per day
    status = Column(String(50), default="draft")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

class InBodyMeasurement(Base):
    """InBody measurement records"""
    __tablename__ = "inbody_measurements"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    measurement_date = Column(DateTime, nullable=False)
    weight_kg = Column(Float)
    body_fat_percentage = Column(Float)
    muscle_mass_kg = Column(Float)
    bmr = Column(Integer)  # Basal Metabolic Rate
    visceral_fat_level = Column(Integer)
    body_water_percentage = Column(Float)
    raw_data = Column(Text)  # JSON: complete InBody data
    created_at = Column(DateTime, default=datetime.utcnow)
```

**CRUD Operations** (in `backend/database/fitness_crud.py`):
```python
"""Fitness Domain CRUD Operations"""
from typing import List, Optional, Dict, Any
from datetime import date, datetime
from sqlalchemy import select, update, delete, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.fitness_models import (
    MemberProgress,
    WorkoutProgram,
    NutritionPlan,
    InBodyMeasurement,
)
from .utils import (
    parse_json_field,
    serialize_json_field,
    datetime_to_str,
    parse_datetime,
)


# ============================================================
# MemberProgress CRUD
# ============================================================

async def create_member_progress(
    db: AsyncSession,
    user_id: int,
    date: date,
    weight_kg: Optional[float] = None,
    body_fat_percentage: Optional[float] = None,
    muscle_mass_kg: Optional[float] = None,
    notes: Optional[str] = None,
    measurements: Optional[Dict[str, Any]] = None,
) -> MemberProgress:
    """Create a new member progress record"""
    progress = MemberProgress(
        user_id=user_id,
        date=date,
        weight_kg=weight_kg,
        body_fat_percentage=body_fat_percentage,
        muscle_mass_kg=muscle_mass_kg,
        notes=notes,
        measurements=serialize_json_field(measurements),
    )
    db.add(progress)
    await db.commit()
    await db.refresh(progress)
    return progress


async def get_member_progress_history(
    db: AsyncSession,
    user_id: int,
    limit: int = 10,
    offset: int = 0,
) -> List[MemberProgress]:
    """Get member progress history with pagination"""
    result = await db.execute(
        select(MemberProgress)
        .filter(MemberProgress.user_id == user_id)
        .order_by(MemberProgress.date.desc())
        .limit(limit)
        .offset(offset)
    )
    return result.scalars().all()


async def get_latest_progress(
    db: AsyncSession,
    user_id: int,
) -> Optional[MemberProgress]:
    """Get the most recent progress record for a member"""
    result = await db.execute(
        select(MemberProgress)
        .filter(MemberProgress.user_id == user_id)
        .order_by(MemberProgress.date.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def get_progress_by_date_range(
    db: AsyncSession,
    user_id: int,
    start_date: date,
    end_date: date,
) -> List[MemberProgress]:
    """Get progress records within a date range"""
    result = await db.execute(
        select(MemberProgress)
        .filter(
            and_(
                MemberProgress.user_id == user_id,
                MemberProgress.date >= start_date,
                MemberProgress.date <= end_date,
            )
        )
        .order_by(MemberProgress.date.asc())
    )
    return result.scalars().all()


# ============================================================
# WorkoutProgram CRUD
# ============================================================

async def create_workout_program(
    db: AsyncSession,
    user_id: int,
    name: str,
    goal: Optional[str] = None,
    duration_weeks: Optional[int] = None,
    exercises: Optional[List[Dict[str, Any]]] = None,
) -> WorkoutProgram:
    """Create a new workout program"""
    program = WorkoutProgram(
        user_id=user_id,
        name=name,
        goal=goal,
        duration_weeks=duration_weeks,
        exercises=serialize_json_field(exercises),
        status="draft",
    )
    db.add(program)
    await db.commit()
    await db.refresh(program)
    return program


async def get_workout_program(
    db: AsyncSession,
    program_id: int,
) -> Optional[WorkoutProgram]:
    """Get workout program by ID"""
    result = await db.execute(
        select(WorkoutProgram).filter(WorkoutProgram.id == program_id)
    )
    return result.scalar_one_or_none()


async def get_user_workout_programs(
    db: AsyncSession,
    user_id: int,
    status: Optional[str] = None,
) -> List[WorkoutProgram]:
    """Get all workout programs for a user, optionally filtered by status"""
    query = select(WorkoutProgram).filter(WorkoutProgram.user_id == user_id)

    if status:
        query = query.filter(WorkoutProgram.status == status)

    query = query.order_by(WorkoutProgram.created_at.desc())

    result = await db.execute(query)
    return result.scalars().all()


async def update_workout_program(
    db: AsyncSession,
    program_id: int,
    **kwargs,
) -> Optional[WorkoutProgram]:
    """Update workout program fields"""
    # Serialize JSON fields if present
    if "exercises" in kwargs and kwargs["exercises"] is not None:
        kwargs["exercises"] = serialize_json_field(kwargs["exercises"])

    await db.execute(
        update(WorkoutProgram)
        .where(WorkoutProgram.id == program_id)
        .values(**kwargs)
    )
    await db.commit()

    return await get_workout_program(db, program_id)


async def activate_workout_program(
    db: AsyncSession,
    program_id: int,
) -> Optional[WorkoutProgram]:
    """Activate a workout program and deactivate others for the same user"""
    # Get the program
    program = await get_workout_program(db, program_id)
    if not program:
        return None

    # Deactivate other active programs for this user
    await db.execute(
        update(WorkoutProgram)
        .where(
            and_(
                WorkoutProgram.user_id == program.user_id,
                WorkoutProgram.status == "active",
                WorkoutProgram.id != program_id,
            )
        )
        .values(status="completed")
    )

    # Activate this program
    program.status = "active"
    await db.commit()
    await db.refresh(program)

    return program


async def delete_workout_program(
    db: AsyncSession,
    program_id: int,
) -> bool:
    """Delete a workout program"""
    result = await db.execute(
        delete(WorkoutProgram).where(WorkoutProgram.id == program_id)
    )
    await db.commit()
    return result.rowcount > 0


# ============================================================
# NutritionPlan CRUD
# ============================================================

async def create_nutrition_plan(
    db: AsyncSession,
    user_id: int,
    name: str,
    daily_calories: Optional[int] = None,
    macro_ratio: Optional[Dict[str, float]] = None,
    meal_plan: Optional[Dict[str, Any]] = None,
) -> NutritionPlan:
    """Create a new nutrition plan"""
    plan = NutritionPlan(
        user_id=user_id,
        name=name,
        daily_calories=daily_calories,
        macro_ratio=serialize_json_field(macro_ratio),
        meal_plan=serialize_json_field(meal_plan),
        status="draft",
    )
    db.add(plan)
    await db.commit()
    await db.refresh(plan)
    return plan


async def get_nutrition_plan(
    db: AsyncSession,
    plan_id: int,
) -> Optional[NutritionPlan]:
    """Get nutrition plan by ID"""
    result = await db.execute(
        select(NutritionPlan).filter(NutritionPlan.id == plan_id)
    )
    return result.scalar_one_or_none()


async def get_user_nutrition_plans(
    db: AsyncSession,
    user_id: int,
    status: Optional[str] = None,
) -> List[NutritionPlan]:
    """Get all nutrition plans for a user"""
    query = select(NutritionPlan).filter(NutritionPlan.user_id == user_id)

    if status:
        query = query.filter(NutritionPlan.status == status)

    query = query.order_by(NutritionPlan.created_at.desc())

    result = await db.execute(query)
    return result.scalars().all()


async def update_nutrition_plan(
    db: AsyncSession,
    plan_id: int,
    **kwargs,
) -> Optional[NutritionPlan]:
    """Update nutrition plan fields"""
    # Serialize JSON fields if present
    if "macro_ratio" in kwargs and kwargs["macro_ratio"] is not None:
        kwargs["macro_ratio"] = serialize_json_field(kwargs["macro_ratio"])
    if "meal_plan" in kwargs and kwargs["meal_plan"] is not None:
        kwargs["meal_plan"] = serialize_json_field(kwargs["meal_plan"])

    await db.execute(
        update(NutritionPlan)
        .where(NutritionPlan.id == plan_id)
        .values(**kwargs)
    )
    await db.commit()

    return await get_nutrition_plan(db, plan_id)


async def delete_nutrition_plan(
    db: AsyncSession,
    plan_id: int,
) -> bool:
    """Delete a nutrition plan"""
    result = await db.execute(
        delete(NutritionPlan).where(NutritionPlan.id == plan_id)
    )
    await db.commit()
    return result.rowcount > 0


# ============================================================
# InBodyMeasurement CRUD
# ============================================================

async def create_inbody_measurement(
    db: AsyncSession,
    user_id: int,
    measurement_date: datetime,
    weight_kg: Optional[float] = None,
    body_fat_percentage: Optional[float] = None,
    muscle_mass_kg: Optional[float] = None,
    bmr: Optional[int] = None,
    visceral_fat_level: Optional[int] = None,
    body_water_percentage: Optional[float] = None,
    raw_data: Optional[Dict[str, Any]] = None,
) -> InBodyMeasurement:
    """Create a new InBody measurement record"""
    measurement = InBodyMeasurement(
        user_id=user_id,
        measurement_date=measurement_date,
        weight_kg=weight_kg,
        body_fat_percentage=body_fat_percentage,
        muscle_mass_kg=muscle_mass_kg,
        bmr=bmr,
        visceral_fat_level=visceral_fat_level,
        body_water_percentage=body_water_percentage,
        raw_data=serialize_json_field(raw_data),
    )
    db.add(measurement)
    await db.commit()
    await db.refresh(measurement)
    return measurement


async def get_inbody_measurement(
    db: AsyncSession,
    measurement_id: int,
) -> Optional[InBodyMeasurement]:
    """Get InBody measurement by ID"""
    result = await db.execute(
        select(InBodyMeasurement).filter(InBodyMeasurement.id == measurement_id)
    )
    return result.scalar_one_or_none()


async def get_user_inbody_history(
    db: AsyncSession,
    user_id: int,
    limit: int = 10,
) -> List[InBodyMeasurement]:
    """Get InBody measurement history for a user"""
    result = await db.execute(
        select(InBodyMeasurement)
        .filter(InBodyMeasurement.user_id == user_id)
        .order_by(InBodyMeasurement.measurement_date.desc())
        .limit(limit)
    )
    return result.scalars().all()


async def get_latest_inbody_measurement(
    db: AsyncSession,
    user_id: int,
) -> Optional[InBodyMeasurement]:
    """Get the most recent InBody measurement for a user"""
    result = await db.execute(
        select(InBodyMeasurement)
        .filter(InBodyMeasurement.user_id == user_id)
        .order_by(InBodyMeasurement.measurement_date.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()
```

**Update `__init__.py`**:
```python
from . import utils
from . import fitness_crud  # Add this
from .session import get_db, get_db_session, AsyncSessionLocal

__all__ = [
    "utils",
    "fitness_crud",  # Add this
    "get_db",
    "get_db_session",
    "AsyncSessionLocal",
]
```

**Usage in Agent Nodes**:
```python
# In backend/app/octostrator/agents/assessor/assessor_nodes.py
from backend.database import get_db_session, fitness_crud

async def inbody_analysis_node(state):
    """Analyze InBody measurement and update member progress"""
    user_id = state["user_id"]
    inbody_data = state["inbody_data"]

    async with get_db_session() as db:
        # Create InBody measurement
        measurement = await fitness_crud.create_inbody_measurement(
            db=db,
            user_id=user_id,
            measurement_date=inbody_data["measurement_date"],
            weight_kg=inbody_data["weight_kg"],
            body_fat_percentage=inbody_data["body_fat_percentage"],
            muscle_mass_kg=inbody_data["muscle_mass_kg"],
            bmr=inbody_data["bmr"],
            raw_data=inbody_data,
        )

        # Get previous measurement for comparison
        previous = await fitness_crud.get_user_inbody_history(
            db=db,
            user_id=user_id,
            limit=2,
        )

        # Analyze changes
        if len(previous) > 1:
            weight_change = measurement.weight_kg - previous[1].weight_kg
            bf_change = measurement.body_fat_percentage - previous[1].body_fat_percentage

            analysis = {
                "weight_change_kg": round(weight_change, 2),
                "body_fat_change_percent": round(bf_change, 2),
                "progress": "improving" if weight_change < 0 and bf_change < 0 else "stable",
            }
        else:
            analysis = {"message": "First measurement - no comparison available"}

        return {
            "measurement_id": measurement.id,
            "analysis": analysis,
        }
```

---

### Medical Domain Complete Example

**Models** (in `backend/app/models/medical_models.py`):
```python
from sqlalchemy import Column, Integer, String, Text, Date, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from app.models.base import Base

class Patient(Base):
    """Medical patient record"""
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    patient_id = Column(String(50), unique=True, nullable=False)  # Hospital patient ID
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    date_of_birth = Column(Date, nullable=False)
    gender = Column(String(20))
    blood_type = Column(String(10))
    allergies = Column(Text)  # JSON: list of allergies
    emergency_contact = Column(Text)  # JSON: contact info
    insurance_info = Column(Text)  # JSON: insurance details
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

class MedicalRecord(Base):
    """Medical record for patient visits"""
    __tablename__ = "medical_records"

    id = Column(Integer, primary_key=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    visit_date = Column(DateTime, nullable=False)
    chief_complaint = Column(Text)
    diagnosis = Column(Text)
    treatment = Column(Text)
    notes = Column(Text)
    doctor_id = Column(Integer)  # Reference to doctor/user
    status = Column(String(50), default="draft")  # draft, reviewed, finalized
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

class Prescription(Base):
    """Prescription for medications"""
    __tablename__ = "prescriptions"

    id = Column(Integer, primary_key=True)
    medical_record_id = Column(Integer, ForeignKey("medical_records.id"), nullable=False)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    medication_name = Column(String(200), nullable=False)
    dosage = Column(String(100))
    frequency = Column(String(100))
    duration_days = Column(Integer)
    instructions = Column(Text)
    prescribed_date = Column(Date, nullable=False)
    status = Column(String(50), default="active")  # active, completed, cancelled
    created_at = Column(DateTime, default=datetime.utcnow)

class VitalSigns(Base):
    """Patient vital signs measurements"""
    __tablename__ = "vital_signs"

    id = Column(Integer, primary_key=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    measurement_time = Column(DateTime, nullable=False)
    temperature_c = Column(Float)
    blood_pressure_systolic = Column(Integer)
    blood_pressure_diastolic = Column(Integer)
    heart_rate_bpm = Column(Integer)
    respiratory_rate = Column(Integer)
    oxygen_saturation = Column(Float)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
```

**CRUD Operations** (in `backend/database/medical_crud.py`):
```python
"""Medical Domain CRUD Operations"""
from typing import List, Optional, Dict, Any
from datetime import date, datetime
from sqlalchemy import select, update, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.medical_models import Patient, MedicalRecord, Prescription, VitalSigns
from .utils import serialize_json_field, parse_json_field


# ============================================================
# Patient CRUD
# ============================================================

async def create_patient(
    db: AsyncSession,
    user_id: int,
    patient_id: str,
    first_name: str,
    last_name: str,
    date_of_birth: date,
    gender: Optional[str] = None,
    blood_type: Optional[str] = None,
    allergies: Optional[List[str]] = None,
    emergency_contact: Optional[Dict[str, Any]] = None,
    insurance_info: Optional[Dict[str, Any]] = None,
) -> Patient:
    """Create a new patient record"""
    patient = Patient(
        user_id=user_id,
        patient_id=patient_id,
        first_name=first_name,
        last_name=last_name,
        date_of_birth=date_of_birth,
        gender=gender,
        blood_type=blood_type,
        allergies=serialize_json_field(allergies),
        emergency_contact=serialize_json_field(emergency_contact),
        insurance_info=serialize_json_field(insurance_info),
    )
    db.add(patient)
    await db.commit()
    await db.refresh(patient)
    return patient


async def get_patient_by_id(
    db: AsyncSession,
    patient_id: int,
) -> Optional[Patient]:
    """Get patient by database ID"""
    result = await db.execute(
        select(Patient).filter(Patient.id == patient_id)
    )
    return result.scalar_one_or_none()


async def get_patient_by_patient_id(
    db: AsyncSession,
    patient_id: str,
) -> Optional[Patient]:
    """Get patient by hospital patient ID"""
    result = await db.execute(
        select(Patient).filter(Patient.patient_id == patient_id)
    )
    return result.scalar_one_or_none()


async def search_patients(
    db: AsyncSession,
    query: str,
    limit: int = 20,
) -> List[Patient]:
    """Search patients by name or patient ID"""
    search_term = f"%{query}%"
    result = await db.execute(
        select(Patient).filter(
            or_(
                Patient.first_name.ilike(search_term),
                Patient.last_name.ilike(search_term),
                Patient.patient_id.ilike(search_term),
            )
        ).limit(limit)
    )
    return result.scalars().all()


# ============================================================
# MedicalRecord CRUD
# ============================================================

async def create_medical_record(
    db: AsyncSession,
    patient_id: int,
    visit_date: datetime,
    chief_complaint: Optional[str] = None,
    diagnosis: Optional[str] = None,
    treatment: Optional[str] = None,
    notes: Optional[str] = None,
    doctor_id: Optional[int] = None,
) -> MedicalRecord:
    """Create a new medical record"""
    record = MedicalRecord(
        patient_id=patient_id,
        visit_date=visit_date,
        chief_complaint=chief_complaint,
        diagnosis=diagnosis,
        treatment=treatment,
        notes=notes,
        doctor_id=doctor_id,
        status="draft",
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


async def get_medical_record(
    db: AsyncSession,
    record_id: int,
) -> Optional[MedicalRecord]:
    """Get medical record by ID"""
    result = await db.execute(
        select(MedicalRecord).filter(MedicalRecord.id == record_id)
    )
    return result.scalar_one_or_none()


async def get_patient_medical_history(
    db: AsyncSession,
    patient_id: int,
    limit: int = 50,
) -> List[MedicalRecord]:
    """Get complete medical history for a patient"""
    result = await db.execute(
        select(MedicalRecord)
        .filter(MedicalRecord.patient_id == patient_id)
        .order_by(MedicalRecord.visit_date.desc())
        .limit(limit)
    )
    return result.scalars().all()


async def update_medical_record(
    db: AsyncSession,
    record_id: int,
    **kwargs,
) -> Optional[MedicalRecord]:
    """Update medical record fields"""
    await db.execute(
        update(MedicalRecord)
        .where(MedicalRecord.id == record_id)
        .values(**kwargs)
    )
    await db.commit()
    return await get_medical_record(db, record_id)


# ============================================================
# Prescription CRUD
# ============================================================

async def create_prescription(
    db: AsyncSession,
    medical_record_id: int,
    patient_id: int,
    medication_name: str,
    dosage: str,
    frequency: str,
    duration_days: int,
    prescribed_date: date,
    instructions: Optional[str] = None,
) -> Prescription:
    """Create a new prescription"""
    prescription = Prescription(
        medical_record_id=medical_record_id,
        patient_id=patient_id,
        medication_name=medication_name,
        dosage=dosage,
        frequency=frequency,
        duration_days=duration_days,
        prescribed_date=prescribed_date,
        instructions=instructions,
        status="active",
    )
    db.add(prescription)
    await db.commit()
    await db.refresh(prescription)
    return prescription


async def get_active_prescriptions(
    db: AsyncSession,
    patient_id: int,
) -> List[Prescription]:
    """Get all active prescriptions for a patient"""
    result = await db.execute(
        select(Prescription)
        .filter(
            and_(
                Prescription.patient_id == patient_id,
                Prescription.status == "active",
            )
        )
        .order_by(Prescription.prescribed_date.desc())
    )
    return result.scalars().all()


# ============================================================
# VitalSigns CRUD
# ============================================================

async def record_vital_signs(
    db: AsyncSession,
    patient_id: int,
    measurement_time: datetime,
    temperature_c: Optional[float] = None,
    blood_pressure_systolic: Optional[int] = None,
    blood_pressure_diastolic: Optional[int] = None,
    heart_rate_bpm: Optional[int] = None,
    respiratory_rate: Optional[int] = None,
    oxygen_saturation: Optional[float] = None,
    notes: Optional[str] = None,
) -> VitalSigns:
    """Record vital signs for a patient"""
    vitals = VitalSigns(
        patient_id=patient_id,
        measurement_time=measurement_time,
        temperature_c=temperature_c,
        blood_pressure_systolic=blood_pressure_systolic,
        blood_pressure_diastolic=blood_pressure_diastolic,
        heart_rate_bpm=heart_rate_bpm,
        respiratory_rate=respiratory_rate,
        oxygen_saturation=oxygen_saturation,
        notes=notes,
    )
    db.add(vitals)
    await db.commit()
    await db.refresh(vitals)
    return vitals


async def get_recent_vital_signs(
    db: AsyncSession,
    patient_id: int,
    limit: int = 10,
) -> List[VitalSigns]:
    """Get recent vital signs for a patient"""
    result = await db.execute(
        select(VitalSigns)
        .filter(VitalSigns.patient_id == patient_id)
        .order_by(VitalSigns.measurement_time.desc())
        .limit(limit)
    )
    return result.scalars().all()
```

---

### Legal Domain Complete Example

**Models** (in `backend/app/models/legal_models.py`):
```python
from sqlalchemy import Column, Integer, String, Text, Date, DateTime, ForeignKey, Numeric
from datetime import datetime
from app.models.base import Base

class LegalClient(Base):
    """Legal client information"""
    __tablename__ = "legal_clients"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    client_id = Column(String(50), unique=True, nullable=False)
    company_name = Column(String(200))
    contact_person = Column(String(100))
    email = Column(String(200))
    phone = Column(String(50))
    address = Column(Text)
    client_type = Column(String(50))  # individual, corporate
    status = Column(String(50), default="active")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

class LegalCase(Base):
    """Legal case management"""
    __tablename__ = "legal_cases"

    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey("legal_clients.id"), nullable=False)
    case_number = Column(String(100), unique=True, nullable=False)
    title = Column(String(300), nullable=False)
    case_type = Column(String(100))  # contract, litigation, advisory, etc.
    description = Column(Text)
    status = Column(String(50), default="open")  # open, in_progress, closed, archived
    priority = Column(String(20))  # low, medium, high, urgent
    assigned_lawyer_id = Column(Integer)
    opened_date = Column(Date, nullable=False)
    closed_date = Column(Date)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

class Contract(Base):
    """Contract documents"""
    __tablename__ = "contracts"

    id = Column(Integer, primary_key=True)
    case_id = Column(Integer, ForeignKey("legal_cases.id"))
    client_id = Column(Integer, ForeignKey("legal_clients.id"), nullable=False)
    contract_number = Column(String(100), unique=True)
    title = Column(String(300), nullable=False)
    contract_type = Column(String(100))
    parties = Column(Text)  # JSON: list of parties
    effective_date = Column(Date)
    expiration_date = Column(Date)
    value = Column(Numeric(15, 2))
    status = Column(String(50), default="draft")  # draft, review, signed, expired
    document_path = Column(String(500))
    terms = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

class CaseNote(Base):
    """Notes and updates for legal cases"""
    __tablename__ = "case_notes"

    id = Column(Integer, primary_key=True)
    case_id = Column(Integer, ForeignKey("legal_cases.id"), nullable=False)
    author_id = Column(Integer)  # User who wrote the note
    note_type = Column(String(50))  # meeting, research, correspondence, court_filing
    title = Column(String(200))
    content = Column(Text, nullable=False)
    note_date = Column(DateTime, nullable=False)
    attachments = Column(Text)  # JSON: list of file paths
    created_at = Column(DateTime, default=datetime.utcnow)
```

**CRUD Operations** (in `backend/database/legal_crud.py`):
```python
"""Legal Domain CRUD Operations"""
from typing import List, Optional, Dict, Any
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import select, update, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.legal_models import LegalClient, LegalCase, Contract, CaseNote
from .utils import serialize_json_field, parse_json_field


# ============================================================
# LegalClient CRUD
# ============================================================

async def create_legal_client(
    db: AsyncSession,
    user_id: int,
    client_id: str,
    company_name: Optional[str] = None,
    contact_person: Optional[str] = None,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    address: Optional[str] = None,
    client_type: str = "individual",
) -> LegalClient:
    """Create a new legal client"""
    client = LegalClient(
        user_id=user_id,
        client_id=client_id,
        company_name=company_name,
        contact_person=contact_person,
        email=email,
        phone=phone,
        address=address,
        client_type=client_type,
        status="active",
    )
    db.add(client)
    await db.commit()
    await db.refresh(client)
    return client


async def get_legal_client(
    db: AsyncSession,
    client_id: int,
) -> Optional[LegalClient]:
    """Get legal client by database ID"""
    result = await db.execute(
        select(LegalClient).filter(LegalClient.id == client_id)
    )
    return result.scalar_one_or_none()


async def search_legal_clients(
    db: AsyncSession,
    query: str,
    limit: int = 20,
) -> List[LegalClient]:
    """Search clients by name, company, or client ID"""
    search_term = f"%{query}%"
    result = await db.execute(
        select(LegalClient).filter(
            or_(
                LegalClient.company_name.ilike(search_term),
                LegalClient.contact_person.ilike(search_term),
                LegalClient.client_id.ilike(search_term),
            )
        ).limit(limit)
    )
    return result.scalars().all()


# ============================================================
# LegalCase CRUD
# ============================================================

async def create_legal_case(
    db: AsyncSession,
    client_id: int,
    case_number: str,
    title: str,
    case_type: str,
    opened_date: date,
    description: Optional[str] = None,
    priority: str = "medium",
    assigned_lawyer_id: Optional[int] = None,
) -> LegalCase:
    """Create a new legal case"""
    case = LegalCase(
        client_id=client_id,
        case_number=case_number,
        title=title,
        case_type=case_type,
        description=description,
        status="open",
        priority=priority,
        assigned_lawyer_id=assigned_lawyer_id,
        opened_date=opened_date,
    )
    db.add(case)
    await db.commit()
    await db.refresh(case)
    return case


async def get_legal_case(
    db: AsyncSession,
    case_id: int,
) -> Optional[LegalCase]:
    """Get legal case by ID"""
    result = await db.execute(
        select(LegalCase).filter(LegalCase.id == case_id)
    )
    return result.scalar_one_or_none()


async def get_client_cases(
    db: AsyncSession,
    client_id: int,
    status: Optional[str] = None,
) -> List[LegalCase]:
    """Get all cases for a client"""
    query = select(LegalCase).filter(LegalCase.client_id == client_id)

    if status:
        query = query.filter(LegalCase.status == status)

    query = query.order_by(LegalCase.opened_date.desc())

    result = await db.execute(query)
    return result.scalars().all()


async def update_case_status(
    db: AsyncSession,
    case_id: int,
    status: str,
    closed_date: Optional[date] = None,
) -> Optional[LegalCase]:
    """Update case status"""
    updates = {"status": status}
    if status == "closed" and closed_date:
        updates["closed_date"] = closed_date

    await db.execute(
        update(LegalCase)
        .where(LegalCase.id == case_id)
        .values(**updates)
    )
    await db.commit()
    return await get_legal_case(db, case_id)


# ============================================================
# Contract CRUD
# ============================================================

async def create_contract(
    db: AsyncSession,
    client_id: int,
    title: str,
    contract_type: str,
    case_id: Optional[int] = None,
    contract_number: Optional[str] = None,
    parties: Optional[List[Dict[str, Any]]] = None,
    effective_date: Optional[date] = None,
    expiration_date: Optional[date] = None,
    value: Optional[Decimal] = None,
    terms: Optional[str] = None,
    document_path: Optional[str] = None,
) -> Contract:
    """Create a new contract"""
    contract = Contract(
        case_id=case_id,
        client_id=client_id,
        contract_number=contract_number,
        title=title,
        contract_type=contract_type,
        parties=serialize_json_field(parties),
        effective_date=effective_date,
        expiration_date=expiration_date,
        value=value,
        status="draft",
        document_path=document_path,
        terms=terms,
    )
    db.add(contract)
    await db.commit()
    await db.refresh(contract)
    return contract


async def get_contract_by_id(
    db: AsyncSession,
    contract_id: int,
) -> Optional[Contract]:
    """Get contract by ID"""
    result = await db.execute(
        select(Contract).filter(Contract.id == contract_id)
    )
    return result.scalar_one_or_none()


async def get_client_contracts(
    db: AsyncSession,
    client_id: int,
    status: Optional[str] = None,
) -> List[Contract]:
    """Get all contracts for a client"""
    query = select(Contract).filter(Contract.client_id == client_id)

    if status:
        query = query.filter(Contract.status == status)

    query = query.order_by(Contract.created_at.desc())

    result = await db.execute(query)
    return result.scalars().all()


async def update_contract_status(
    db: AsyncSession,
    contract_id: int,
    status: str,
) -> Optional[Contract]:
    """Update contract status"""
    await db.execute(
        update(Contract)
        .where(Contract.id == contract_id)
        .values(status=status)
    )
    await db.commit()
    return await get_contract_by_id(db, contract_id)


# ============================================================
# CaseNote CRUD
# ============================================================

async def create_case_note(
    db: AsyncSession,
    case_id: int,
    author_id: int,
    content: str,
    note_date: datetime,
    note_type: str = "general",
    title: Optional[str] = None,
    attachments: Optional[List[str]] = None,
) -> CaseNote:
    """Create a new case note"""
    note = CaseNote(
        case_id=case_id,
        author_id=author_id,
        note_type=note_type,
        title=title,
        content=content,
        note_date=note_date,
        attachments=serialize_json_field(attachments),
    )
    db.add(note)
    await db.commit()
    await db.refresh(note)
    return note


async def get_case_notes(
    db: AsyncSession,
    case_id: int,
    note_type: Optional[str] = None,
    limit: int = 50,
) -> List[CaseNote]:
    """Get notes for a case"""
    query = select(CaseNote).filter(CaseNote.case_id == case_id)

    if note_type:
        query = query.filter(CaseNote.note_type == note_type)

    query = query.order_by(CaseNote.note_date.desc()).limit(limit)

    result = await db.execute(query)
    return result.scalars().all()
```

---

### Education Domain Complete Example

**Models** (in `backend/app/models/education_models.py`):
```python
from sqlalchemy import Column, Integer, String, Text, Date, DateTime, ForeignKey, Float
from datetime import datetime
from app.models.base import Base

class Course(Base):
    """Course information"""
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True)
    course_code = Column(String(50), unique=True, nullable=False)
    title = Column(String(300), nullable=False)
    description = Column(Text)
    instructor_id = Column(Integer, ForeignKey("users.id"))
    semester = Column(String(50))
    year = Column(Integer)
    credits = Column(Integer)
    max_students = Column(Integer)
    status = Column(String(50), default="active")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

class Enrollment(Base):
    """Student course enrollment"""
    __tablename__ = "enrollments"

    id = Column(Integer, primary_key=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    enrollment_date = Column(Date, nullable=False)
    status = Column(String(50), default="enrolled")  # enrolled, completed, dropped, failed
    final_grade = Column(String(5))  # A+, A, B+, etc.
    final_score = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

class Assignment(Base):
    """Course assignment"""
    __tablename__ = "assignments"

    id = Column(Integer, primary_key=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    title = Column(String(300), nullable=False)
    description = Column(Text)
    assignment_type = Column(String(50))  # homework, project, exam, quiz
    max_score = Column(Float, default=100.0)
    weight = Column(Float)  # Weight in final grade (e.g., 0.3 for 30%)
    due_date = Column(DateTime)
    status = Column(String(50), default="active")
    instructions = Column(Text)
    attachments = Column(Text)  # JSON: list of file paths
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

class Submission(Base):
    """Student assignment submission"""
    __tablename__ = "submissions"

    id = Column(Integer, primary_key=True)
    assignment_id = Column(Integer, ForeignKey("assignments.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    submission_date = Column(DateTime, nullable=False)
    content = Column(Text)
    attachments = Column(Text)  # JSON: list of file paths
    score = Column(Float)
    feedback = Column(Text)
    status = Column(String(50), default="submitted")  # submitted, graded, late
    graded_by = Column(Integer)  # Teacher/TA user ID
    graded_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
```

**CRUD Operations** (inline in agent nodes - Option B example):
```python
# In backend/app/octostrator/agents/education/education_nodes.py
from sqlalchemy import select, and_
from backend.database import get_db_session
from app.models.education_models import Course, Assignment, Submission, Enrollment


async def assignment_grading_node(state):
    """Grade student assignments"""
    assignment_id = state["assignment_id"]

    async with get_db_session() as db:
        # Get assignment details
        assignment_result = await db.execute(
            select(Assignment).filter(Assignment.id == assignment_id)
        )
        assignment = assignment_result.scalar_one_or_none()

        if not assignment:
            return {"error": "Assignment not found"}

        # Get all submissions for this assignment
        submissions_result = await db.execute(
            select(Submission)
            .filter(
                and_(
                    Submission.assignment_id == assignment_id,
                    Submission.status == "submitted"
                )
            )
        )
        submissions = submissions_result.scalars().all()

        graded_count = 0
        for submission in submissions:
            # AI grading logic here (simplified)
            score = state.get("ai_grader_function")(submission.content)

            # Update submission with grade
            submission.score = score
            submission.status = "graded"
            submission.graded_by = state["grader_id"]
            submission.graded_at = datetime.utcnow()
            submission.feedback = state.get("feedback", "Good work!")

            graded_count += 1

        await db.commit()

        return {
            "graded_count": graded_count,
            "assignment_title": assignment.title,
        }


async def student_progress_node(state):
    """Track student progress in a course"""
    course_id = state["course_id"]
    student_id = state["student_id"]

    async with get_db_session() as db:
        # Get enrollment
        enrollment_result = await db.execute(
            select(Enrollment).filter(
                and_(
                    Enrollment.course_id == course_id,
                    Enrollment.student_id == student_id
                )
            )
        )
        enrollment = enrollment_result.scalar_one_or_none()

        if not enrollment:
            return {"error": "Student not enrolled in course"}

        # Get all assignments for the course
        assignments_result = await db.execute(
            select(Assignment).filter(Assignment.course_id == course_id)
        )
        assignments = assignments_result.scalars().all()

        # Get student submissions
        submissions_result = await db.execute(
            select(Submission).filter(
                and_(
                    Submission.student_id == student_id,
                    Submission.assignment_id.in_([a.id for a in assignments])
                )
            )
        )
        submissions = submissions_result.scalars().all()

        # Calculate progress
        total_assignments = len(assignments)
        completed_assignments = len([s for s in submissions if s.score is not None])
        average_score = sum([s.score for s in submissions if s.score]) / len(submissions) if submissions else 0

        return {
            "total_assignments": total_assignments,
            "completed_assignments": completed_assignments,
            "completion_rate": completed_assignments / total_assignments if total_assignments > 0 else 0,
            "average_score": round(average_score, 2),
        }
```

---

## Common CRUD Patterns

### Pagination
```python
async def get_items_paginated(
    db: AsyncSession,
    model: Type,
    page: int = 1,
    page_size: int = 20,
) -> Dict[str, Any]:
    """Generic pagination pattern"""
    offset = (page - 1) * page_size

    # Get total count
    count_result = await db.execute(select(func.count(model.id)))
    total_count = count_result.scalar()

    # Get page items
    result = await db.execute(
        select(model)
        .limit(page_size)
        .offset(offset)
        .order_by(model.created_at.desc())
    )
    items = result.scalars().all()

    return {
        "items": items,
        "total_count": total_count,
        "page": page,
        "page_size": page_size,
        "total_pages": (total_count + page_size - 1) // page_size,
    }
```

### Filtering and Sorting
```python
async def get_items_filtered(
    db: AsyncSession,
    model: Type,
    filters: Dict[str, Any],
    sort_by: str = "created_at",
    sort_order: str = "desc",
    limit: int = 100,
) -> List:
    """Generic filtering and sorting pattern"""
    query = select(model)

    # Apply filters
    for field, value in filters.items():
        if hasattr(model, field) and value is not None:
            query = query.filter(getattr(model, field) == value)

    # Apply sorting
    if hasattr(model, sort_by):
        sort_column = getattr(model, sort_by)
        if sort_order == "desc":
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())

    query = query.limit(limit)

    result = await db.execute(query)
    return result.scalars().all()
```

### Bulk Operations
```python
async def bulk_create(
    db: AsyncSession,
    model: Type,
    items: List[Dict[str, Any]],
) -> List:
    """Bulk create multiple records"""
    instances = [model(**item) for item in items]
    db.add_all(instances)
    await db.commit()

    # Refresh all instances to get IDs
    for instance in instances:
        await db.refresh(instance)

    return instances

async def bulk_update(
    db: AsyncSession,
    model: Type,
    updates: List[Dict[str, Any]],  # Each dict must have 'id' key
) -> int:
    """Bulk update multiple records"""
    updated_count = 0
    for update_data in updates:
        record_id = update_data.pop("id")
        result = await db.execute(
            update(model)
            .where(model.id == record_id)
            .values(**update_data)
        )
        updated_count += result.rowcount

    await db.commit()
    return updated_count
```

### Soft Delete
```python
# Add to your model:
class YourModel(Base):
    # ... other fields ...
    deleted_at = Column(DateTime, nullable=True)

async def soft_delete(
    db: AsyncSession,
    model_instance,
) -> bool:
    """Soft delete by setting deleted_at timestamp"""
    model_instance.deleted_at = datetime.utcnow()
    await db.commit()
    return True

async def get_active_items(
    db: AsyncSession,
    model: Type,
) -> List:
    """Get only non-deleted items"""
    result = await db.execute(
        select(model).filter(model.deleted_at.is_(None))
    )
    return result.scalars().all()
```

---

## Testing Strategies

### Unit Testing CRUD Functions

```python
# backend/tests/test_fitness_crud.py
import pytest
from datetime import date
from backend.database import get_db_session
from backend.database import fitness_crud
from app.models.fitness_models import MemberProgress

@pytest.mark.asyncio
async def test_create_member_progress():
    """Test creating member progress record"""
    async with get_db_session() as db:
        progress = await fitness_crud.create_member_progress(
            db=db,
            user_id=1,
            date=date.today(),
            weight_kg=75.5,
            body_fat_percentage=18.5,
            muscle_mass_kg=60.2,
        )

        assert progress.id is not None
        assert progress.user_id == 1
        assert progress.weight_kg == 75.5

@pytest.mark.asyncio
async def test_get_member_progress_history():
    """Test retrieving progress history"""
    async with get_db_session() as db:
        # Create test data
        await fitness_crud.create_member_progress(db, 1, date.today(), 75.0)
        await fitness_crud.create_member_progress(db, 1, date.today(), 74.5)

        # Retrieve history
        history = await fitness_crud.get_member_progress_history(db, user_id=1, limit=10)

        assert len(history) >= 2
        assert history[0].weight_kg == 74.5  # Most recent first
```

### Integration Testing with Agents

```python
# backend/tests/test_assessor_agent_integration.py
import pytest
from datetime import datetime
from backend.app.octostrator.agents.assessor.assessor_nodes import inbody_analysis_node
from backend.database import get_db_session, fitness_crud

@pytest.mark.asyncio
async def test_inbody_analysis_integration():
    """Test InBody analysis node with database"""
    state = {
        "user_id": 1,
        "inbody_data": {
            "measurement_date": datetime.utcnow(),
            "weight_kg": 75.5,
            "body_fat_percentage": 18.5,
            "muscle_mass_kg": 60.2,
            "bmr": 1850,
        }
    }

    result = await inbody_analysis_node(state)

    assert "measurement_id" in result
    assert "analysis" in result

    # Verify data was saved
    async with get_db_session() as db:
        measurement = await fitness_crud.get_latest_inbody_measurement(db, user_id=1)
        assert measurement is not None
        assert measurement.weight_kg == 75.5
```

### Test Fixtures

```python
# backend/tests/conftest.py
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.models.base import Base

@pytest.fixture
async def test_db():
    """Create test database"""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        yield session

    await engine.dispose()

@pytest.fixture
async def sample_user(test_db):
    """Create sample user for testing"""
    from app.models.core import User

    user = User(
        name="Test User",
        email="test@example.com",
        phone="123-456-7890",
        user_type="member"
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)

    return user
```

---

## Best Practices

### 1. Always Use Async Context Manager
```python
# ✅ Good
async with get_db_session() as db:
    result = await crud_function(db, ...)
    # Session automatically commits and closes

# ❌ Bad
db = AsyncSessionLocal()
result = await crud_function(db, ...)
# Session not properly closed, potential memory leak
```

### 2. Handle None Results Gracefully
```python
# ✅ Good
user = await get_user(db, user_id)
if user is None:
    return {"error": "User not found"}

# ❌ Bad
user = await get_user(db, user_id)
return {"name": user.name}  # Crashes if user is None
```

### 3. Use Transactions for Related Operations
```python
# ✅ Good
async with get_db_session() as db:
    user = await create_user(db, ...)
    profile = await create_profile(db, user.id, ...)
    await db.commit()  # Both or neither

# ❌ Bad
async with get_db_session() as db1:
    user = await create_user(db1, ...)
async with get_db_session() as db2:
    profile = await create_profile(db2, user.id, ...)
    # User created but profile fails - inconsistent state
```

### 4. Serialize/Deserialize JSON Fields
```python
from backend.database import utils

# ✅ Good - when creating
measurements = {"chest": 100, "waist": 80}
instance.measurements = utils.serialize_json_field(measurements)

# ✅ Good - when reading
measurements = utils.parse_json_field(instance.measurements)

# ❌ Bad - storing dict directly
instance.measurements = {"chest": 100}  # Will fail
```

### 5. Use Type Hints
```python
# ✅ Good
async def get_user(db: AsyncSession, user_id: int) -> Optional[User]:
    ...

# ❌ Bad
async def get_user(db, user_id):
    ...
```

### 6. Separate Read and Write Operations
```python
# ✅ Good - clear intent
async def get_user(db: AsyncSession, user_id: int) -> Optional[User]:
    """Read operation"""
    ...

async def create_user(db: AsyncSession, name: str, email: str) -> User:
    """Write operation"""
    ...

# ❌ Bad - unclear intent
async def user_operation(db, action, user_id=None, name=None):
    if action == "read":
        ...
    elif action == "create":
        ...
```

### 7. Log Database Operations
```python
import logging

logger = logging.getLogger(__name__)

async def create_user(db: AsyncSession, name: str, email: str) -> User:
    logger.info(f"Creating user: {name} ({email})")
    user = User(name=name, email=email)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    logger.info(f"User created with ID: {user.id}")
    return user
```

### 8. Handle Database Errors
```python
from sqlalchemy.exc import IntegrityError

async def create_user(db: AsyncSession, email: str) -> Dict[str, Any]:
    try:
        user = User(email=email)
        db.add(user)
        await db.commit()
        return {"success": True, "user_id": user.id}
    except IntegrityError:
        await db.rollback()
        return {"success": False, "error": "Email already exists"}
    except Exception as e:
        await db.rollback()
        logger.error(f"Database error: {e}")
        return {"success": False, "error": "Database error"}
```

---

## Migration Guide

### Migrating from PT-Specific to Domain-Specific

If you previously had PT-specific CRUD (like `frontdesk_crud.py`), here's how to migrate:

**Step 1: Identify Your Domain**
- Fitness, Medical, Legal, Education, or Custom?

**Step 2: Review Archived PT Code**
- Check `backend/database/relation_db/archive_fitness/`
- Review models and CRUD patterns

**Step 3: Create Domain Models**
- Follow examples in this guide
- Adapt PT models to your domain

**Step 4: Implement CRUD Operations**
- Choose Strategy A, B, or C
- Use patterns from this guide

**Step 5: Update Imports**
```python
# Before (PT-specific)
from backend.database import frontdesk_crud

# After (Domain-specific)
from backend.database import fitness_crud
# or
from backend.database import medical_crud
```

**Step 6: Update Agent Nodes**
```python
# Before
async def frontdesk_node(state):
    result = await frontdesk_crud.create_lead(...)

# After
async def intake_node(state):
    result = await medical_crud.create_patient(...)
```

**Step 7: Test Thoroughly**
- Write unit tests for CRUD functions
- Write integration tests with agent nodes
- Verify data integrity

---

## Summary

This guide provides three implementation strategies for domain-specific CRUD operations:

1. **Strategy A: Separate CRUD Modules** - Best for complex domains
2. **Strategy B: Inline in Agent Nodes** - Best for simple domains
3. **Strategy C: Generic Repository Pattern** - Best for standardized operations

Complete examples are provided for:
- **Fitness Domain**: Member progress, workout programs, nutrition plans, InBody measurements
- **Medical Domain**: Patients, medical records, prescriptions, vital signs
- **Legal Domain**: Clients, cases, contracts, case notes
- **Education Domain**: Courses, enrollments, assignments, submissions

Choose the strategy that best fits your domain complexity and implementation style.

For questions or issues, refer to:
- `backend/database/__init__.py` (package docstring)
- `backend/app/models/DOMAIN_MODELS_GUIDE.md` (model implementation guide)
- `backend/database/relation_db/archive_fitness/` (archived PT reference)

---

**Document Version**: 1.0
**Last Updated**: 2025-11-10
**Maintainer**: Specialist Agent System Team
