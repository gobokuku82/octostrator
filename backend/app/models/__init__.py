"""
SQLAlchemy Models for Specialist Agent System

범용 데이터 모델만 제공합니다. 도메인 특화 모델은 별도로 추가하세요.

⚠️ 현재 상태 (범용 시스템)
==========================================
이 패키지는 모든 도메인에서 사용할 수 있는 범용 모델만 제공합니다:

**Generic Models**:
- Base: SQLAlchemy Base 클래스
- User: 범용 사용자 모델 (모든 도메인 공통)
- Bookmark: 범용 북마크 모델 (URL 기반 자료 저장)

**Archived Models** (참고용):
PT 도메인 특화 모델은 backend/app/models/archive/fitness/에 보관되어 있습니다:
- frontdesk.py: Lead, Inquiry, Appointment
- assessor.py: InBodyData, PostureAnalysis
- program_designer.py: Program, MealLog, WorkoutRoutine
- manager.py: Attendance, ChurnRisk, Schedule
- marketing.py: SocialMediaPost, Event
- owner.py: Revenue, MemberProgress
- trainer.py: TrainerSkill

🔮 도메인 모델 추가 방법
==========================================

## Step 1: 도메인 모델 파일 생성

새로운 도메인의 모델을 추가하려면 도메인별 모델 파일을 생성하세요.

### 예시: Fitness 도메인
```python
# backend/app/models/fitness_models.py
from .base import Base
from sqlalchemy import Column, Integer, String, ForeignKey

class FitnessMember(Base):
    \"\"\"Fitness 도메인 회원 프로필\"\"\"
    __tablename__ = "fitness_members"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    goal = Column(String(50))  # weight_loss, muscle_gain
    fitness_level = Column(String(20))
```

### 예시: Medical 도메인
```python
# backend/app/models/medical_models.py
from .base import Base
from sqlalchemy import Column, Integer, String, ForeignKey

class Patient(Base):
    \"\"\"Medical 도메인 환자 프로필\"\"\"
    __tablename__ = "medical_patients"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    patient_id = Column(String(50), unique=True)
    blood_type = Column(String(10))
```

## Step 2: __init__.py에 모델 등록

도메인 모델을 생성한 후, 이 파일에서 import하여 등록하세요.

```python
# backend/app/models/__init__.py

# Fitness 도메인 모델 추가 예시
from .fitness_models import FitnessMember, WorkoutProgram

__all__ = [
    "Base",
    "User",
    "Bookmark",
    # Fitness Domain
    "FitnessMember",
    "WorkoutProgram",
]
```

## Step 3: Alembic 마이그레이션

```bash
cd backend
alembic revision --autogenerate -m "Add fitness domain models"
alembic upgrade head
```

📚 See Also
==========================================
- DOMAIN_MODELS_GUIDE.md: 도메인별 모델 추가 상세 가이드
- backend/app/models/archive/fitness/: PT 도메인 모델 참고 자료
- backend/app/octostrator/supervisors/: Supervisor 일반화 패턴
- backend/app/octostrator/execution_agents/base/: Base Agent 일반화 패턴
"""

from .base import Base

# Generic Core Models
from .core import User

# Generic Shared Models
from .shared import Bookmark

__all__ = [
    # Base
    "Base",
    # Generic Models
    "User",
    "Bookmark",
    # 🔮 도메인 모델을 추가할 때는 여기에 import 및 export 추가
    # 예시:
    # "FitnessMember",
    # "Patient",
    # "LegalClient",
]
