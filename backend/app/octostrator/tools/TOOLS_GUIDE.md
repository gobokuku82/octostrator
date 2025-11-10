# Tools Development Guide

**Version**: 2.0
**Date**: 2025-11-10
**Status**: Domain-Agnostic Tools Layer

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Tool Implementation Patterns](#tool-implementation-patterns)
3. [Complete Examples by Domain](#complete-examples-by-domain)
4. [LangChain Integration](#langchain-integration)
5. [Testing Tools](#testing-tools)
6. [Best Practices](#best-practices)
7. [Archived PT Tools Reference](#archived-pt-tools-reference)

---

## Overview

### What are Tools?

Tools are **async functions** that agents can call to interact with:
- **Databases** (CRUD operations)
- **External APIs** (third-party services)
- **File systems** (read/write files)
- **Computations** (analysis, calculations)
- **Integrations** (email, SMS, webhooks)

### Key Principles

1. **Async/Await**: All tools must be async functions
2. **Type Hints**: Use proper typing for parameters and return values
3. **Error Handling**: Use try/except and return structured errors
4. **Stateless**: Tools should not maintain internal state
5. **Database Sessions**: Always use context managers for DB operations

---

## Tool Implementation Patterns

### Pattern A: Separate Tool Modules (Recommended)

**Best for**: Complex domains with many tools (10+ tools)

```
backend/app/octostrator/tools/
├── __init__.py              # Tools registry
├── TOOLS_GUIDE.md           # This guide
├── fitness_tools.py         # Fitness domain tools
├── medical_tools.py         # Medical domain tools
├── legal_tools.py           # Legal domain tools
└── education_tools.py       # Education domain tools
```

**Example Structure**:

```python
# backend/app/octostrator/tools/fitness_tools.py
from typing import Dict, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.database import get_db_session
from app.models import WorkoutProgram, MemberProgress

async def create_workout_program(
    user_id: int,
    program_name: str,
    exercises: List[Dict],
    duration_weeks: int
) -> Dict:
    """Create a new workout program for a user

    Args:
        user_id: User ID
        program_name: Name of the program
        exercises: List of exercises with sets/reps
        duration_weeks: Program duration in weeks

    Returns:
        Dict with program_id and status

    Example:
        >>> result = await create_workout_program(
        ...     user_id=1,
        ...     program_name="Beginner Strength",
        ...     exercises=[{"name": "Squat", "sets": 3, "reps": 10}],
        ...     duration_weeks=12
        ... )
        >>> print(result)
        {"program_id": 42, "status": "created"}
    """
    try:
        async with get_db_session() as db:
            program = WorkoutProgram(
                user_id=user_id,
                name=program_name,
                exercises=json.dumps(exercises),
                duration_weeks=duration_weeks
            )
            db.add(program)
            await db.commit()
            await db.refresh(program)

            return {
                "program_id": program.id,
                "status": "created",
                "name": program.name
            }
    except Exception as e:
        return {
            "error": str(e),
            "status": "failed"
        }


async def get_member_progress(
    user_id: int,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 10
) -> Dict:
    """Get member progress records

    Args:
        user_id: User ID
        start_date: Start date (YYYY-MM-DD format)
        end_date: End date (YYYY-MM-DD format)
        limit: Maximum number of records

    Returns:
        Dict with progress records
    """
    try:
        async with get_db_session() as db:
            query = select(MemberProgress).filter(
                MemberProgress.user_id == user_id
            )

            if start_date:
                query = query.filter(MemberProgress.date >= start_date)
            if end_date:
                query = query.filter(MemberProgress.date <= end_date)

            query = query.order_by(MemberProgress.date.desc()).limit(limit)

            result = await db.execute(query)
            records = result.scalars().all()

            return {
                "user_id": user_id,
                "count": len(records),
                "records": [
                    {
                        "date": r.date,
                        "weight": r.weight,
                        "body_fat": r.body_fat_percentage
                    }
                    for r in records
                ]
            }
    except Exception as e:
        return {"error": str(e), "status": "failed"}
```

**Then register in `__init__.py`**:

```python
# backend/app/octostrator/tools/__init__.py
from .fitness_tools import (
    create_workout_program,
    get_member_progress,
    analyze_body_composition,
)

TOOLS = {
    "create_workout_program": create_workout_program,
    "get_member_progress": get_member_progress,
    "analyze_body_composition": analyze_body_composition,
}
```

---

### Pattern B: Inline Tools (Simple Domains)

**Best for**: Simple domains with few tools (< 10 tools)

```python
# In backend/app/octostrator/execution_agents/medical/medical_agent.py
from langchain.tools import tool
from backend.database import get_db_session
from app.models import Patient, Prescription

@tool
async def get_patient_records(patient_id: int) -> Dict:
    """Get all medical records for a patient"""
    async with get_db_session() as db:
        result = await db.execute(
            select(Patient).filter(Patient.id == patient_id)
        )
        patient = result.scalar_one_or_none()

        if not patient:
            return {"error": "Patient not found"}

        return {
            "patient_id": patient.id,
            "name": patient.name,
            "records": patient.medical_records
        }

@tool
async def create_prescription(
    patient_id: int,
    medication: str,
    dosage: str,
    duration_days: int
) -> Dict:
    """Create a new prescription for a patient"""
    async with get_db_session() as db:
        prescription = Prescription(
            patient_id=patient_id,
            medication=medication,
            dosage=dosage,
            duration_days=duration_days
        )
        db.add(prescription)
        await db.commit()
        await db.refresh(prescription)

        return {
            "prescription_id": prescription.id,
            "status": "created"
        }

# Use in agent
class MedicalAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            agent_id="medical_agent",
            tools=[get_patient_records, create_prescription]
        )
```

---

### Pattern C: LangChain Tool Decorators (Advanced)

**Best for**: Tools that integrate with LangChain agents

```python
from langchain.tools import tool
from langchain_core.tools import ToolException
from typing import Annotated

@tool
async def search_legal_cases(
    query: Annotated[str, "Search query for legal cases"],
    jurisdiction: Annotated[str, "Legal jurisdiction (federal, state, local)"],
    date_from: Annotated[str, "Start date YYYY-MM-DD"] = None,
    date_to: Annotated[str, "End date YYYY-MM-DD"] = None,
    limit: Annotated[int, "Maximum number of results"] = 10
) -> Dict:
    """Search legal cases database by query and jurisdiction

    This tool searches through legal cases and returns matching results
    based on the search criteria.
    """
    try:
        async with get_db_session() as db:
            query_builder = select(LegalCase).filter(
                LegalCase.jurisdiction == jurisdiction
            )

            # Full-text search on case description
            if query:
                query_builder = query_builder.filter(
                    LegalCase.description.ilike(f"%{query}%")
                )

            # Date filtering
            if date_from:
                query_builder = query_builder.filter(
                    LegalCase.filing_date >= date_from
                )
            if date_to:
                query_builder = query_builder.filter(
                    LegalCase.filing_date <= date_to
                )

            query_builder = query_builder.limit(limit)

            result = await db.execute(query_builder)
            cases = result.scalars().all()

            return {
                "query": query,
                "jurisdiction": jurisdiction,
                "count": len(cases),
                "cases": [
                    {
                        "case_id": c.id,
                        "title": c.title,
                        "filing_date": c.filing_date.isoformat(),
                        "status": c.status
                    }
                    for c in cases
                ]
            }
    except Exception as e:
        raise ToolException(f"Error searching legal cases: {str(e)}")
```

---

## Complete Examples by Domain

### 1. Fitness Domain

```python
# backend/app/octostrator/tools/fitness_tools.py
from typing import Dict, List, Optional
from sqlalchemy import select
from backend.database import get_db_session
from app.models import WorkoutProgram, NutritionPlan, MemberProgress

async def create_nutrition_plan(
    user_id: int,
    plan_name: str,
    daily_calories: int,
    macros: Dict[str, int],  # {"protein": 150, "carbs": 200, "fats": 60}
    meal_schedule: List[Dict]
) -> Dict:
    """Create a nutrition plan for a user"""
    async with get_db_session() as db:
        plan = NutritionPlan(
            user_id=user_id,
            name=plan_name,
            daily_calories=daily_calories,
            protein_grams=macros["protein"],
            carbs_grams=macros["carbs"],
            fats_grams=macros["fats"],
            meal_schedule=json.dumps(meal_schedule)
        )
        db.add(plan)
        await db.commit()
        await db.refresh(plan)

        return {
            "plan_id": plan.id,
            "status": "created",
            "daily_calories": daily_calories
        }

async def track_workout_session(
    user_id: int,
    program_id: int,
    exercises_completed: List[Dict],
    duration_minutes: int,
    notes: Optional[str] = None
) -> Dict:
    """Track a completed workout session"""
    async with get_db_session() as db:
        session = WorkoutSession(
            user_id=user_id,
            program_id=program_id,
            exercises=json.dumps(exercises_completed),
            duration_minutes=duration_minutes,
            notes=notes,
            completed_at=datetime.utcnow()
        )
        db.add(session)
        await db.commit()

        return {
            "session_id": session.id,
            "status": "logged",
            "duration_minutes": duration_minutes
        }

async def analyze_body_composition(
    user_id: int,
    inbody_data: Dict
) -> Dict:
    """Analyze InBody data and provide insights"""
    # Implementation with analysis logic
    weight = inbody_data.get("weight")
    body_fat = inbody_data.get("body_fat_percentage")
    muscle_mass = inbody_data.get("muscle_mass")

    # Calculate metrics
    fat_mass = (weight * body_fat) / 100
    lean_mass = weight - fat_mass

    # Provide recommendations
    recommendations = []
    if body_fat > 25:
        recommendations.append("Consider increasing cardio sessions")
    if muscle_mass < 40:
        recommendations.append("Focus on strength training")

    return {
        "user_id": user_id,
        "metrics": {
            "fat_mass_kg": round(fat_mass, 2),
            "lean_mass_kg": round(lean_mass, 2),
            "body_fat_percentage": body_fat
        },
        "recommendations": recommendations
    }
```

---

### 2. Medical Domain

```python
# backend/app/octostrator/tools/medical_tools.py
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from backend.database import get_db_session
from app.models import Patient, MedicalRecord, Prescription, Appointment

async def create_patient_record(
    patient_id: int,
    visit_type: str,
    symptoms: List[str],
    diagnosis: str,
    treatment_plan: str,
    doctor_notes: Optional[str] = None
) -> Dict:
    """Create a new medical record for a patient visit"""
    async with get_db_session() as db:
        record = MedicalRecord(
            patient_id=patient_id,
            visit_type=visit_type,
            symptoms=json.dumps(symptoms),
            diagnosis=diagnosis,
            treatment_plan=treatment_plan,
            doctor_notes=doctor_notes,
            visit_date=datetime.utcnow()
        )
        db.add(record)
        await db.commit()
        await db.refresh(record)

        return {
            "record_id": record.id,
            "patient_id": patient_id,
            "visit_date": record.visit_date.isoformat(),
            "status": "created"
        }

async def schedule_medical_appointment(
    patient_id: int,
    doctor_id: int,
    appointment_type: str,
    requested_date: str,
    duration_minutes: int = 30
) -> Dict:
    """Schedule a medical appointment"""
    async with get_db_session() as db:
        # Check availability
        appointment_datetime = datetime.fromisoformat(requested_date)

        # Check for conflicts
        conflicts = await db.execute(
            select(Appointment).filter(
                Appointment.doctor_id == doctor_id,
                Appointment.scheduled_time == appointment_datetime
            )
        )

        if conflicts.scalar_one_or_none():
            return {
                "status": "failed",
                "error": "Time slot not available"
            }

        # Create appointment
        appointment = Appointment(
            patient_id=patient_id,
            doctor_id=doctor_id,
            appointment_type=appointment_type,
            scheduled_time=appointment_datetime,
            duration_minutes=duration_minutes,
            status="scheduled"
        )
        db.add(appointment)
        await db.commit()

        return {
            "appointment_id": appointment.id,
            "scheduled_time": appointment_datetime.isoformat(),
            "status": "scheduled"
        }

async def analyze_vital_signs(
    patient_id: int,
    vital_signs: Dict
) -> Dict:
    """Analyze patient vital signs and flag abnormalities"""
    # Normal ranges
    NORMAL_RANGES = {
        "blood_pressure_systolic": (90, 120),
        "blood_pressure_diastolic": (60, 80),
        "heart_rate": (60, 100),
        "temperature_celsius": (36.1, 37.2),
        "oxygen_saturation": (95, 100)
    }

    alerts = []
    for vital, value in vital_signs.items():
        if vital in NORMAL_RANGES:
            min_val, max_val = NORMAL_RANGES[vital]
            if value < min_val:
                alerts.append(f"{vital} is below normal range: {value}")
            elif value > max_val:
                alerts.append(f"{vital} is above normal range: {value}")

    return {
        "patient_id": patient_id,
        "vital_signs": vital_signs,
        "alerts": alerts,
        "requires_immediate_attention": len(alerts) > 0
    }
```

---

### 3. Legal Domain

```python
# backend/app/octostrator/tools/legal_tools.py
from typing import Dict, List, Optional
from backend.database import get_db_session
from app.models import LegalCase, Contract, LegalDocument

async def create_legal_case(
    client_id: int,
    case_type: str,
    description: str,
    jurisdiction: str,
    assigned_attorney_id: int
) -> Dict:
    """Create a new legal case"""
    async with get_db_session() as db:
        case = LegalCase(
            client_id=client_id,
            case_type=case_type,
            description=description,
            jurisdiction=jurisdiction,
            assigned_attorney_id=assigned_attorney_id,
            filing_date=datetime.utcnow(),
            status="open"
        )
        db.add(case)
        await db.commit()
        await db.refresh(case)

        return {
            "case_id": case.id,
            "case_number": case.case_number,
            "status": "created"
        }

async def draft_contract(
    contract_type: str,
    parties: List[Dict],  # [{"name": "...", "role": "..."}]
    terms: Dict,
    effective_date: str,
    expiration_date: Optional[str] = None
) -> Dict:
    """Draft a new contract"""
    async with get_db_session() as db:
        contract = Contract(
            contract_type=contract_type,
            parties=json.dumps(parties),
            terms=json.dumps(terms),
            effective_date=datetime.fromisoformat(effective_date),
            expiration_date=datetime.fromisoformat(expiration_date) if expiration_date else None,
            status="draft"
        )
        db.add(contract)
        await db.commit()
        await db.refresh(contract)

        return {
            "contract_id": contract.id,
            "status": "draft",
            "parties_count": len(parties)
        }

async def search_legal_precedents(
    keywords: List[str],
    jurisdiction: str,
    case_type: Optional[str] = None,
    date_from: Optional[str] = None,
    limit: int = 20
) -> Dict:
    """Search for legal precedents based on keywords and filters"""
    async with get_db_session() as db:
        query = select(LegalCase).filter(
            LegalCase.jurisdiction == jurisdiction
        )

        # Keyword search
        for keyword in keywords:
            query = query.filter(
                LegalCase.description.ilike(f"%{keyword}%")
            )

        if case_type:
            query = query.filter(LegalCase.case_type == case_type)

        if date_from:
            query = query.filter(
                LegalCase.filing_date >= datetime.fromisoformat(date_from)
            )

        query = query.order_by(LegalCase.filing_date.desc()).limit(limit)

        result = await db.execute(query)
        cases = result.scalars().all()

        return {
            "keywords": keywords,
            "jurisdiction": jurisdiction,
            "count": len(cases),
            "precedents": [
                {
                    "case_id": c.id,
                    "case_number": c.case_number,
                    "title": c.title,
                    "filing_date": c.filing_date.isoformat(),
                    "outcome": c.outcome
                }
                for c in cases
            ]
        }
```

---

### 4. Education Domain

```python
# backend/app/octostrator/tools/education_tools.py
from typing import Dict, List, Optional
from backend.database import get_db_session
from app.models import Course, Assignment, Submission, Grade

async def create_assignment(
    course_id: int,
    title: str,
    description: str,
    due_date: str,
    max_points: int,
    assignment_type: str  # "homework", "quiz", "project", "exam"
) -> Dict:
    """Create a new assignment for a course"""
    async with get_db_session() as db:
        assignment = Assignment(
            course_id=course_id,
            title=title,
            description=description,
            due_date=datetime.fromisoformat(due_date),
            max_points=max_points,
            assignment_type=assignment_type,
            status="published"
        )
        db.add(assignment)
        await db.commit()
        await db.refresh(assignment)

        return {
            "assignment_id": assignment.id,
            "title": title,
            "due_date": due_date,
            "status": "published"
        }

async def grade_submission(
    submission_id: int,
    points_earned: int,
    feedback: str,
    graded_by: int
) -> Dict:
    """Grade a student submission"""
    async with get_db_session() as db:
        # Get submission
        result = await db.execute(
            select(Submission).filter(Submission.id == submission_id)
        )
        submission = result.scalar_one_or_none()

        if not submission:
            return {"error": "Submission not found"}

        # Get assignment to check max points
        assignment = await db.get(Assignment, submission.assignment_id)

        if points_earned > assignment.max_points:
            return {"error": f"Points exceed maximum ({assignment.max_points})"}

        # Create grade
        grade = Grade(
            submission_id=submission_id,
            student_id=submission.student_id,
            assignment_id=submission.assignment_id,
            points_earned=points_earned,
            max_points=assignment.max_points,
            feedback=feedback,
            graded_by=graded_by,
            graded_at=datetime.utcnow()
        )
        db.add(grade)

        # Update submission status
        submission.status = "graded"

        await db.commit()

        return {
            "grade_id": grade.id,
            "points_earned": points_earned,
            "max_points": assignment.max_points,
            "percentage": round((points_earned / assignment.max_points) * 100, 2),
            "status": "graded"
        }

async def get_student_progress(
    student_id: int,
    course_id: Optional[int] = None
) -> Dict:
    """Get comprehensive student progress analytics"""
    async with get_db_session() as db:
        query = select(Grade).filter(Grade.student_id == student_id)

        if course_id:
            query = query.join(Assignment).filter(
                Assignment.course_id == course_id
            )

        result = await db.execute(query)
        grades = result.scalars().all()

        if not grades:
            return {
                "student_id": student_id,
                "total_assignments": 0,
                "average_score": 0
            }

        total_points = sum(g.points_earned for g in grades)
        max_points = sum(g.max_points for g in grades)
        average_percentage = (total_points / max_points * 100) if max_points > 0 else 0

        return {
            "student_id": student_id,
            "total_assignments": len(grades),
            "total_points_earned": total_points,
            "total_max_points": max_points,
            "average_percentage": round(average_percentage, 2),
            "letter_grade": _calculate_letter_grade(average_percentage)
        }

def _calculate_letter_grade(percentage: float) -> str:
    """Helper function to calculate letter grade"""
    if percentage >= 90:
        return "A"
    elif percentage >= 80:
        return "B"
    elif percentage >= 70:
        return "C"
    elif percentage >= 60:
        return "D"
    else:
        return "F"
```

---

## LangChain Integration

### Using Tools with LangChain Agents

```python
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain_openai import ChatOpenAI
from langchain.tools import tool
from backend.app.octostrator.tools import TOOLS

# Convert async functions to LangChain tools
@tool
async def fitness_create_program(user_id: int, program_name: str) -> Dict:
    """Create a workout program for a user"""
    tool_func = TOOLS["create_workout_program"]
    return await tool_func(user_id=user_id, program_name=program_name)

# Create agent
llm = ChatOpenAI(model="gpt-4")
tools = [fitness_create_program, ...]

agent = create_openai_functions_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools)

# Run
result = await agent_executor.ainvoke({"input": "Create a beginner program for user 123"})
```

---

## Testing Tools

### Unit Testing

```python
# backend/tests/test_fitness_tools.py
import pytest
from backend.app.octostrator.tools.fitness_tools import (
    create_workout_program,
    get_member_progress
)

@pytest.mark.asyncio
async def test_create_workout_program():
    """Test creating a workout program"""
    result = await create_workout_program(
        user_id=1,
        program_name="Test Program",
        exercises=[{"name": "Squat", "sets": 3, "reps": 10}],
        duration_weeks=12
    )

    assert result["status"] == "created"
    assert "program_id" in result
    assert result["name"] == "Test Program"

@pytest.mark.asyncio
async def test_get_member_progress():
    """Test retrieving member progress"""
    result = await get_member_progress(user_id=1, limit=5)

    assert "user_id" in result
    assert "records" in result
    assert isinstance(result["records"], list)
```

### Integration Testing

```python
# backend/tests/integration/test_medical_workflow.py
import pytest
from backend.app.octostrator.tools.medical_tools import (
    create_patient_record,
    schedule_medical_appointment,
    analyze_vital_signs
)

@pytest.mark.asyncio
async def test_patient_workflow():
    """Test complete patient workflow"""
    # Step 1: Create patient record
    record_result = await create_patient_record(
        patient_id=1,
        visit_type="checkup",
        symptoms=["headache", "fatigue"],
        diagnosis="Common cold",
        treatment_plan="Rest and hydration"
    )
    assert record_result["status"] == "created"

    # Step 2: Analyze vitals
    vitals_result = await analyze_vital_signs(
        patient_id=1,
        vital_signs={
            "blood_pressure_systolic": 120,
            "blood_pressure_diastolic": 80,
            "heart_rate": 75,
            "temperature_celsius": 36.8
        }
    )
    assert len(vitals_result["alerts"]) == 0

    # Step 3: Schedule follow-up
    appointment_result = await schedule_medical_appointment(
        patient_id=1,
        doctor_id=5,
        appointment_type="follow-up",
        requested_date="2025-11-15T10:00:00"
    )
    assert appointment_result["status"] == "scheduled"
```

---

## Best Practices

### 1. Error Handling

```python
async def safe_tool_function(param: str) -> Dict:
    """Always use try/except and return structured errors"""
    try:
        async with get_db_session() as db:
            # Your logic here
            pass
    except ValueError as e:
        return {
            "error": f"Invalid input: {str(e)}",
            "error_type": "validation_error",
            "status": "failed"
        }
    except Exception as e:
        return {
            "error": f"Unexpected error: {str(e)}",
            "error_type": "internal_error",
            "status": "failed"
        }
```

### 2. Type Hints

```python
from typing import Dict, List, Optional

async def well_typed_function(
    user_id: int,
    tags: List[str],
    metadata: Optional[Dict] = None
) -> Dict[str, Any]:
    """Always provide complete type hints"""
    pass
```

### 3. Documentation

```python
async def well_documented_function(param: str) -> Dict:
    """One-line summary

    Detailed description of what this function does,
    when to use it, and any important notes.

    Args:
        param: Description of parameter

    Returns:
        Dict containing:
        - field1: Description
        - field2: Description

    Raises:
        ValueError: When param is invalid

    Example:
        >>> result = await well_documented_function("test")
        >>> print(result["field1"])
        'value'
    """
    pass
```

### 4. Database Sessions

```python
# ✅ GOOD: Use context manager
async def good_example():
    async with get_db_session() as db:
        # Use db here
        pass

# ❌ BAD: Manual session management
async def bad_example():
    db = await get_db()
    try:
        # Use db
        pass
    finally:
        await db.close()
```

### 5. Async/Await

```python
# ✅ GOOD: All tools are async
async def async_tool() -> Dict:
    async with get_db_session() as db:
        result = await db.execute(query)
        return result

# ❌ BAD: Sync functions
def sync_tool() -> Dict:  # Don't do this
    # sync code
    pass
```

---

## Archived PT Tools Reference

The original PT-specific tools (62 tools across 7 modules) have been archived to:

```
backend/app/octostrator/tools/archive_fitness/
├── frontdesk_tools.py           (12 tools)
├── assessor_tools.py            (7 tools)
├── program_designer_tools.py    (10 tools)
├── manager_tools.py             (8 tools)
├── marketing_tools.py           (9 tools)
├── owner_assistant_tools.py     (8 tools)
└── trainer_education_tools.py   (8 tools)
```

### How to Reference Archived Tools

When implementing your domain-specific tools, you can reference these archived files as examples:

1. **Similar functionality**: If your domain needs similar features (e.g., appointments, analytics, progress tracking)
2. **Code structure**: Follow the same patterns (async/await, error handling, database sessions)
3. **Naming conventions**: Use similar naming patterns for consistency

**Note**: The archived tools reference PT-specific models that have also been archived. You'll need to adapt them to your domain-specific models.

---

## Summary

- **3 Implementation Patterns**: Separate modules (complex), Inline (simple), LangChain decorators (advanced)
- **4 Domain Examples**: Complete, production-ready code for Fitness, Medical, Legal, Education
- **Best Practices**: Error handling, type hints, documentation, async/await
- **Testing**: Unit tests and integration tests
- **Reference**: 62 archived PT tools available for inspiration

**Ready to implement your domain-specific tools!** 🚀

---

**Questions?** Refer to:
- `backend/app/octostrator/tools/__init__.py` - Tools registry
- `backend/database/CRUD_PATTERNS_GUIDE.md` - Database patterns
- `backend/app/octostrator/states/__init__.py` - State management
