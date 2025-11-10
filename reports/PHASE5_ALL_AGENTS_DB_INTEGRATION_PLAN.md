# Phase 5: All Agents DB Integration Plan

## Executive Summary

**Status**: Planning Complete
**Date**: 2025-11-07
**Completed**: Frontdesk Agent DB integration
**Remaining**: 6 Agents (Assessor, Program Designer, Manager, Marketing, Owner, Trainer)

This report provides a prioritized plan for integrating all remaining agents with PostgreSQL database.

---

## Current Status Analysis

### ✅ Completed: Frontdesk Agent

**Models**: Lead, Inquiry, Appointment
**CRUD Operations**: 15 functions in `frontdesk_crud.py`
**Tools**: 5 DB-integrated functions in `frontdesk_tools.py`
**State Schema**: Updated to use `int` IDs
**Tests**: All passed (7/7 workflow steps)

**Pattern Established**:
1. Create CRUD layer (`{agent}_crud.py`)
2. Update/Create tools to use CRUD operations
3. Update State schema (str → int for IDs)
4. Test integration workflow

---

## Agent Overview

### All Agents Summary

| Agent | Models | State IDs | Tools Exist | Complexity | Priority |
|-------|--------|-----------|-------------|------------|----------|
| Frontdesk | 3 | ✅ int | ✅ Yes | Medium | ✅ Done |
| Assessor | 2 | ❌ str | ❌ No | Low | **#1** |
| Program Designer | 3 | ❌ str | ❌ No | Medium | **#2** |
| Manager | 3 | ❌ str | ❌ No | Medium | **#3** |
| Marketing | 2 | N/A | ❌ No | Low | #4 |
| Owner | 2 | N/A | ❌ No | Low | #5 |
| Trainer | 1 | N/A | ❌ No | Very Low | #6 |

---

## Detailed Agent Analysis

### 1. Assessor Agent (Priority #1)

**Database Models**:
- `InBodyData` (11 fields) - InBody 측정 데이터
- `PostureAnalysis` (11 fields) - 자세 분석

**State Schema Issues**:
```python
# Current (assessor_state.py):
class AssessmentResult(TypedDict):
    assessment_id: str  # ❌ Should be int
    member_id: str  # ❌ Should be int (user_id)
    # ...
```

**Foreign Keys**:
- Both models → `users.id`

**Complexity**: Low
- Simple models with clear fields
- No complex relationships
- Similar to Frontdesk Inquiry model

**Why Priority #1**:
- Assessor provides data to Program Designer (dependency chain)
- Simple models = good next step after Frontdesk
- Clear business value (initial assessments)

**Estimated Work**:
- CRUD Operations: 10-12 functions (~2 hours)
- Tools Creation: 6-8 functions (~3 hours)
- State Schema Update: 1 TypedDict (~30 min)
- Testing: Workflow test (~1 hour)
- **Total**: ~6-7 hours

---

### 2. Program Designer Agent (Priority #2)

**Database Models**:
- `Program` (11 fields) - 운동/식단 프로그램
- `MealLog` (7 fields) - 식단 기록
- `WorkoutRoutine` (6 fields) - 운동 루틴

**State Schema Issues**:
```python
# Current (program_designer_state.py):
class WorkoutProgram(TypedDict):
    program_id: str  # ❌ Should be int
    member_id: str  # ❌ Should be int
    # ...

class DietPlan(TypedDict):
    plan_id: str  # ❌ Should be int
    member_id: str  # ❌ Should be int
    # ...
```

**Foreign Keys**:
- All 3 models → `users.id`

**Complexity**: Medium
- 3 models (most complex after Frontdesk)
- JSON fields (workout_plan, diet_plan, exercises)
- Need JSON parsing/serialization helpers

**Why Priority #2**:
- Depends on Assessor data (assessment_data field)
- Core business functionality
- More complex than Assessor (good progression)

**Estimated Work**:
- CRUD Operations: 15-18 functions (~3 hours)
- Tools Creation: 10-12 functions (~4 hours)
- State Schema Update: 2 TypedDicts (~1 hour)
- JSON Helpers: 3-4 functions (~1 hour)
- Testing: Workflow test (~1.5 hours)
- **Total**: ~10-11 hours

---

### 3. Manager Agent (Priority #3)

**Database Models**:
- `Attendance` (8 fields) - 출석 기록
- `ChurnRisk` (9 fields) - 이탈 위험도
- `Schedule` (8 fields) - PT 스케줄

**State Schema Issues**:
```python
# Current (manager_state.py):
class AttendanceRecord(TypedDict):
    member_id: str  # ❌ Should be int
    # ...

class ChurnRiskAnalysis(TypedDict):
    member_id: str  # ❌ Should be int
    risk_score: float  # ✓ Already correct
    # ...
```

**Foreign Keys**:
- All models → `users.id` (member)
- Attendance, Schedule → `users.id` (trainer)

**Complexity**: Medium
- 3 models with multiple foreign keys
- ChurnRisk has JSON fields (factors, recommended_actions)
- Schedule overlaps with Frontdesk Appointment (need coordination)

**Why Priority #3**:
- Important for retention
- Can leverage Attendance data from other agents
- Moderate complexity (good follow-up to Program Designer)

**Estimated Work**:
- CRUD Operations: 15-18 functions (~3 hours)
- Tools Creation: 10-12 functions (~4 hours)
- State Schema Update: 2 TypedDicts (~1 hour)
- Testing: Workflow test (~1.5 hours)
- **Total**: ~9-10 hours

---

### 4. Marketing Agent (Priority #4)

**Database Models**:
- `SocialMediaPost` (10 fields) - SNS 게시물
- `Event` (12 fields) - 이벤트

**State Schema**: No ID-related TypedDicts (simpler)

**Foreign Keys**: None (standalone tables)

**Complexity**: Low
- Simple models with no foreign keys
- JSON fields (media_urls, hashtags, participants)
- Mostly standalone operations

**Why Priority #4**:
- No dependencies on other agents
- Lower business priority than member-facing agents
- Simple models

**Estimated Work**:
- CRUD Operations: 10-12 functions (~2.5 hours)
- Tools Creation: 6-8 functions (~3 hours)
- State Schema Update: Minimal (~30 min)
- Testing: Workflow test (~1 hour)
- **Total**: ~7 hours

---

### 5. Owner Assistant Agent (Priority #5)

**Database Models**:
- `Revenue` (9 fields) - 매출 데이터
- `MemberProgress` (7 fields) - 회원 진행률

**State Schema**: No ID-related TypedDicts

**Foreign Keys**:
- Both models → `users.id` (member)
- Revenue → `users.id` (trainer)

**Complexity**: Low
- Simple financial/analytics models
- No JSON fields
- Mostly read operations (analytics)

**Why Priority #5**:
- Analytics/reporting functionality
- Depends on data from other agents
- Lower priority than operational agents

**Estimated Work**:
- CRUD Operations: 10-12 functions (~2.5 hours)
- Tools Creation: 6-8 functions (~3 hours)
- State Schema Update: Minimal (~30 min)
- Testing: Workflow test (~1 hour)
- **Total**: ~7 hours

---

### 6. Trainer Education Agent (Priority #6)

**Database Models**:
- `TrainerSkill` (9 fields) - 트레이너 스킬

**State Schema**: No review needed yet

**Foreign Keys**:
- TrainerSkill → `users.id` (trainer)

**Complexity**: Very Low
- Single model
- Simple CRUD operations
- No complex relationships

**Why Priority #6**:
- Single model (simplest agent)
- Trainer-focused (not member-facing)
- Lower business priority

**Estimated Work**:
- CRUD Operations: 6-8 functions (~1.5 hours)
- Tools Creation: 4-5 functions (~2 hours)
- State Schema Update: None needed (~0 hours)
- Testing: Workflow test (~1 hour)
- **Total**: ~4-5 hours

---

## Common Issues Across All Agents

### 1. ID Type Mismatches

**All state schemas use string IDs**:
```python
# Current pattern (WRONG):
member_id: str
assessment_id: str
program_id: str

# Should be (CORRECT):
member_id: int  # Foreign key to users.id
assessment_id: int  # Auto-increment primary key
program_id: int  # Auto-increment primary key
```

**Fix Required**: Update all TypedDict definitions

---

### 2. Missing Tools Files

**Current Status**: Only Frontdesk has `frontdesk_tools.py`

**Need to Create**:
- `backend/app/octostrator/agents/assessor/assessor_tools.py`
- `backend/app/octostrator/agents/program_designer/program_designer_tools.py`
- `backend/app/octostrator/agents/manager/manager_tools.py`
- `backend/app/octostrator/agents/marketing/marketing_tools.py`
- `backend/app/octostrator/agents/owner_assistant/owner_assistant_tools.py`
- `backend/app/octostrator/agents/trainer_education/trainer_education_tools.py`

**Pattern to Follow**: `frontdesk_tools.py` structure

---

### 3. JSON Field Handling

**Models with JSON fields** (need parsing helpers):

**Program Designer**:
- `Program.workout_plan` (Text/JSON)
- `Program.diet_plan` (Text/JSON)
- `MealLog.foods` (Text/JSON)
- `MealLog.nutrition` (Text/JSON)
- `WorkoutRoutine.exercises` (Text/JSON)

**Manager**:
- `ChurnRisk.factors` (Text/JSON)
- `ChurnRisk.recommended_actions` (Text/JSON)

**Marketing**:
- `SocialMediaPost.media_urls` (Text/JSON)
- `Event.participants` (Text/JSON)

**Assessor**:
- `PostureAnalysis.issues` (Text/JSON)
- `PostureAnalysis.recommendations` (Text/JSON)

**Helper Functions Needed**:
```python
def parse_json_field(value: Optional[str]) -> Optional[Dict]:
    if not value:
        return None
    try:
        return json.loads(value)
    except:
        return None

def serialize_json_field(value: Optional[Dict]) -> Optional[str]:
    if not value:
        return None
    return json.dumps(value, ensure_ascii=False)
```

---

## Prioritized Implementation Order

### Phase 5A: High Priority (Member Journey)
1. **Assessor Agent** (6-7 hours)
   - Initial assessment data collection
   - Foundation for Program Designer

2. **Program Designer Agent** (10-11 hours)
   - Depends on Assessor data
   - Core service delivery

3. **Manager Agent** (9-10 hours)
   - Retention and attendance
   - Critical for business continuity

**Subtotal**: 25-28 hours (~3-4 working days)

---

### Phase 5B: Medium Priority (Support Functions)
4. **Marketing Agent** (7 hours)
   - Lead generation
   - Event management

5. **Owner Assistant Agent** (7 hours)
   - Analytics and reporting
   - Business intelligence

**Subtotal**: 14 hours (~2 working days)

---

### Phase 5C: Low Priority (Trainer Support)
6. **Trainer Education Agent** (4-5 hours)
   - Trainer skill tracking
   - Internal operations

**Subtotal**: 4-5 hours (~1 working day)

---

**GRAND TOTAL**: 43-47 hours (~6-7 working days)

---

## Implementation Strategy

### Pattern Replication from Frontdesk

For each agent, follow this **4-step process**:

#### Step 1: Create CRUD Layer
```python
# backend/database/{agent}_crud.py

# Example structure (based on frontdesk_crud.py):

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.app.models.{agent} import Model1, Model2
import json
from typing import Dict, Any, Optional, List

# CREATE operations
async def create_model1(session: AsyncSession, data: Dict[str, Any]) -> Optional[Model1]:
    """Create new record"""
    model = Model1(
        user_id=data.get("user_id"),
        # ... map fields
    )
    session.add(model)
    await session.commit()
    await session.refresh(model)
    return model

# READ operations
async def get_model1_by_id(session: AsyncSession, model_id: int) -> Optional[Model1]:
    """Get by ID"""
    result = await session.execute(
        select(Model1).where(Model1.id == model_id)
    )
    return result.scalar_one_or_none()

async def get_models_by_user(session: AsyncSession, user_id: int) -> List[Model1]:
    """Get all records for user"""
    result = await session.execute(
        select(Model1).where(Model1.user_id == user_id)
    )
    return result.scalars().all()

# UPDATE operations
async def update_model1(session: AsyncSession, model_id: int, updates: Dict[str, Any]) -> bool:
    """Update record"""
    model = await get_model1_by_id(session, model_id)
    if not model:
        return False
    for key, value in updates.items():
        setattr(model, key, value)
    await session.commit()
    return True

# DELETE operations
async def delete_model1(session: AsyncSession, model_id: int) -> bool:
    """Delete record"""
    model = await get_model1_by_id(session, model_id)
    if not model:
        return False
    await session.delete(model)
    await session.commit()
    return True

# CONVERSION helpers
def model1_to_dict(model: Model1) -> Dict[str, Any]:
    """Convert to State-compatible dict"""
    return {
        "id": model.id,
        "user_id": model.user_id,
        # ... all fields
        "created_at": model.created_at.isoformat() if model.created_at else None
    }
```

---

#### Step 2: Create/Update Tools
```python
# backend/app/octostrator/agents/{agent}/{agent}_tools.py

from database import {agent}_crud
from database.session import get_db
from typing import Dict, Any

async def create_{model}_record(data: Dict[str, Any]) -> Dict[str, Any]:
    """Create new {model} record in database"""
    async with await get_db() as session:
        model = await {agent}_crud.create_{model}(session, data)
        if not model:
            raise Exception(f"Failed to save {model} to database")

        record = {agent}_crud.{model}_to_dict(model)
        return {"status": "success", "record": record}

async def get_{model}_by_id(model_id: int) -> Dict[str, Any]:
    """Get {model} by ID"""
    async with await get_db() as session:
        model = await {agent}_crud.get_{model}_by_id(session, model_id)
        if not model:
            return {"status": "not_found"}

        record = {agent}_crud.{model}_to_dict(model)
        return {"status": "success", "record": record}
```

---

#### Step 3: Update State Schema
```python
# backend/app/octostrator/states/{agent}_state.py

# BEFORE:
class ModelInfo(TypedDict):
    model_id: str  # ❌ UUID string
    member_id: str  # ❌ UUID string

# AFTER:
class ModelInfo(TypedDict):
    model_id: int  # ✅ PostgreSQL auto-increment
    member_id: int  # ✅ Foreign key to users.id (int)
```

---

#### Step 4: Create Integration Test
```python
# backend/test_{agent}_integration.py

import asyncio
from database import {agent}_crud
from database.session import get_db

async def test_full_workflow():
    """Test complete {agent} workflow"""
    async with await get_db() as session:
        # Step 1: Create primary record
        data = {...}
        model = await {agent}_crud.create_{model}(session, data)
        assert isinstance(model.id, int)

        # Step 2: Retrieve record
        retrieved = await {agent}_crud.get_{model}_by_id(session, model.id)
        assert retrieved.id == model.id

        # Step 3: Update record
        success = await {agent}_crud.update_{model}(session, model.id, {...})
        assert success

        # Step 4: Query related records
        records = await {agent}_crud.get_{models}_by_user(session, model.user_id)
        assert len(records) > 0

if __name__ == "__main__":
    asyncio.run(test_full_workflow())
```

---

## Database Session Management (Reuse Existing)

All agents will use the existing session management:

```python
# Already created: backend/database/session.py

from database.session import get_db

# Usage in tools:
async with await get_db() as session:
    # CRUD operations
    result = await {agent}_crud.create_model(session, data)
```

---

## Common Helpers (Create Once, Reuse)

### JSON Field Helpers
```python
# backend/database/utils.py (NEW FILE)

import json
from typing import Dict, Any, Optional, List

def parse_json_field(value: Optional[str]) -> Optional[Dict]:
    """Parse JSON string from database"""
    if not value:
        return None
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return None

def serialize_json_field(value: Optional[Dict]) -> Optional[str]:
    """Serialize dict to JSON string for database"""
    if not value:
        return None
    return json.dumps(value, ensure_ascii=False)

def parse_json_list(value: Optional[str]) -> Optional[List]:
    """Parse JSON array from database"""
    if not value:
        return None
    try:
        result = json.loads(value)
        return result if isinstance(result, list) else None
    except (json.JSONDecodeError, TypeError):
        return None
```

---

## Updated Database Package Exports

After each agent integration, update:

```python
# backend/database/__init__.py

"""Database Package

PostgreSQL (정형 데이터) CRUD operations
"""

from . import frontdesk_crud
from . import assessor_crud  # Add after Assessor integration
from . import program_designer_crud  # Add after Program Designer integration
from . import manager_crud  # Add after Manager integration
from . import marketing_crud  # Add after Marketing integration
from . import owner_crud  # Add after Owner integration
from . import trainer_crud  # Add after Trainer integration

from .session import get_db, get_db_session, AsyncSessionLocal

__all__ = [
    "frontdesk_crud",
    "assessor_crud",
    "program_designer_crud",
    "manager_crud",
    "marketing_crud",
    "owner_crud",
    "trainer_crud",
    "get_db",
    "get_db_session",
    "AsyncSessionLocal",
]
```

---

## Risk Mitigation

### 1. Import Path Issues
**Problem**: Agent files use `from backend.app...` imports
**Workaround**: Test CRUD layer directly (like Frontdesk)
**Long-term Fix**: Standardize to relative imports

### 2. Foreign Key Validation
**Problem**: Must ensure user_id exists before creating records
**Solution**: Add FK validation in CRUD layer:
```python
# Verify user exists
user = await session.get(User, user_id)
if not user:
    raise ValueError(f"User {user_id} not found")
```

### 3. JSON Field Migrations
**Problem**: Existing JSON data might be in different formats
**Solution**: Add migration validation and conversion in CRUD helpers

---

## Success Criteria

For each agent, verify:

1. ✅ CRUD operations work for all models
2. ✅ Tools use database (not in-memory)
3. ✅ State schema uses integer IDs
4. ✅ Foreign key relationships verified
5. ✅ Integration test passes (full workflow)
6. ✅ Type safety maintained (mypy/pyright clean)
7. ✅ Documentation updated

---

## Next Steps

### Immediate (Start with Assessor)
1. Create `backend/database/assessor_crud.py`
2. Create `backend/app/octostrator/agents/assessor/assessor_tools.py`
3. Update `backend/app/octostrator/states/assessor_state.py`
4. Create `backend/test_assessor_integration.py`
5. Test and validate

### Then Continue In Order
- Program Designer (after Assessor)
- Manager (after Program Designer)
- Marketing
- Owner Assistant
- Trainer Education

---

## Estimated Timeline

**Phase 5A** (Assessor + Program Designer + Manager): 3-4 days
**Phase 5B** (Marketing + Owner): 2 days
**Phase 5C** (Trainer): 1 day

**TOTAL**: 6-7 working days

If working 세분화 (granular) as requested: ~2-3 weeks with testing and documentation.

---

**Report Generated**: 2025-11-07
**Status**: Planning Complete
**Ready to Begin**: Assessor Agent Integration

---
