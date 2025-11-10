# Domain Models Implementation Guide

이 문서는 Specialist Agent System의 도메인별 데이터 모델 구현 가이드입니다.

## ⚠️ 현재 상태 (범용 시스템)

현재 backend/app/models/에는 도메인에 구애받지 않는 범용 모델만 제공됩니다:

```
backend/app/models/
├── base.py                    # SQLAlchemy Base 선언
├── core.py                    # 범용 User 모델
├── shared.py                  # 범용 Bookmark 모델
├── __init__.py                # 모델 Export
└── DOMAIN_MODELS_GUIDE.md     # 📖 이 가이드
```

**제공되는 범용 모델**:
- `User`: 사용자/회원 정보 (도메인 독립적)
- `Bookmark`: 자료 북마크 (도메인 독립적)

**제공되지 않는 것**:
- PT 특화 모델 (InBody, Workout, Diet 등)
- 의료 특화 모델 (Patient, Diagnosis, Prescription 등)
- 법률 특화 모델 (Case, Contract, Client 등)
- 기타 도메인 특화 모델

## 📦 아카이브된 PT 도메인 모델

기존 PT Manager 시스템의 모델은 참고용으로 보관되어 있습니다:

```
backend/app/models/archive/fitness/
├── frontdesk.py              # Lead, Inquiry, Appointment
├── assessor.py               # InBodyData, PostureAnalysis
├── program_designer.py       # Program, MealLog, WorkoutRoutine
├── manager.py                # Attendance, ChurnRisk, Schedule
├── marketing.py              # SocialMediaPost, Event
├── owner.py                  # Revenue, MemberProgress
└── trainer.py                # TrainerSkill

backend/database/relation_db/archive_fitness/
├── models.py                 # 통합 PT 모델
├── nutrition_seed_data.py    # 영양 데이터
├── mock_data.py              # 테스트 데이터
└── fitness.db                # PT 데이터베이스
```

이 파일들은 새로운 도메인 모델을 구현할 때 **참고 자료**로 활용할 수 있습니다.

---

## 🔮 도메인 모델 추가 방법

새로운 도메인의 Agent를 추가할 때, 해당 도메인에 특화된 데이터 모델이 필요합니다.

### Option A: 도메인별 모델 파일 생성 (권장)

각 도메인별로 별도의 모델 파일을 생성하여 관리합니다.

#### Step 1: 도메인 모델 파일 생성

```python
# backend/app/models/fitness_models.py
"""
Fitness 도메인 특화 모델

Fitness PT Manager를 위한 데이터 모델들입니다.
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Date
from datetime import datetime
from .base import Base


class MemberProgress(Base):
    """회원 진행 상황 추적"""
    __tablename__ = "fitness_member_progress"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    measurement_date = Column(Date, nullable=False)
    weight = Column(Float)
    body_fat_percentage = Column(Float)
    muscle_mass = Column(Float)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class WorkoutProgram(Base):
    """운동 프로그램"""
    __tablename__ = "fitness_workout_programs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(200), nullable=False)
    goal = Column(String(100))  # weight_loss, muscle_gain, endurance
    difficulty = Column(String(50))  # beginner, intermediate, advanced
    duration_weeks = Column(Integer)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class NutritionPlan(Base):
    """식단 계획"""
    __tablename__ = "fitness_nutrition_plans"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(200), nullable=False)
    daily_calories = Column(Integer)
    protein_grams = Column(Float)
    carbs_grams = Column(Float)
    fat_grams = Column(Float)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class InBodyMeasurement(Base):
    """InBody 측정 데이터"""
    __tablename__ = "fitness_inbody_measurements"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    measurement_date = Column(Date, nullable=False)
    weight = Column(Float)
    muscle_mass = Column(Float)
    body_fat_mass = Column(Float)
    body_fat_percentage = Column(Float)
    visceral_fat_level = Column(Integer)
    bmr = Column(Integer)  # Basal Metabolic Rate
    created_at = Column(DateTime, default=datetime.utcnow)
```

#### Step 2: 모델 등록 (__init__.py 업데이트)

```python
# backend/app/models/__init__.py

from .base import Base
from .core import User
from .shared import Bookmark

# Fitness 도메인 모델
from .fitness_models import (
    MemberProgress,
    WorkoutProgram,
    NutritionPlan,
    InBodyMeasurement,
)

__all__ = [
    # Base
    "Base",
    # Core
    "User",
    # Shared
    "Bookmark",
    # Fitness Domain
    "MemberProgress",
    "WorkoutProgram",
    "NutritionPlan",
    "InBodyMeasurement",
]
```

#### Step 3: 데이터베이스 마이그레이션

```bash
# Alembic 마이그레이션 생성
cd backend
alembic revision --autogenerate -m "Add fitness domain models"

# 마이그레이션 적용
alembic upgrade head
```

---

### 예시 2: Medical 도메인 (의료 관리 시스템)

```python
# backend/app/models/medical_models.py
"""
Medical 도메인 특화 모델

의료 기록 관리 시스템을 위한 데이터 모델들입니다.
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Date, Boolean
from datetime import datetime
from .base import Base


class Patient(Base):
    """환자 정보"""
    __tablename__ = "medical_patients"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    patient_id = Column(String(50), unique=True, nullable=False)  # 환자번호
    date_of_birth = Column(Date)
    blood_type = Column(String(10))
    allergies = Column(Text)
    medical_history = Column(Text)
    emergency_contact = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)


class MedicalRecord(Base):
    """진료 기록"""
    __tablename__ = "medical_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    patient_id = Column(Integer, ForeignKey("medical_patients.id"), nullable=False)
    visit_date = Column(DateTime, nullable=False)
    chief_complaint = Column(Text)  # 주 증상
    diagnosis = Column(Text)
    treatment_plan = Column(Text)
    notes = Column(Text)
    doctor_name = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)


class Prescription(Base):
    """처방전"""
    __tablename__ = "medical_prescriptions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    medical_record_id = Column(Integer, ForeignKey("medical_records.id"), nullable=False)
    medication_name = Column(String(200), nullable=False)
    dosage = Column(String(100))
    frequency = Column(String(100))  # 1일 3회 등
    duration_days = Column(Integer)
    instructions = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class VitalSigns(Base):
    """활력 징후"""
    __tablename__ = "medical_vital_signs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    patient_id = Column(Integer, ForeignKey("medical_patients.id"), nullable=False)
    measurement_date = Column(DateTime, nullable=False)
    blood_pressure_systolic = Column(Integer)  # 수축기 혈압
    blood_pressure_diastolic = Column(Integer)  # 이완기 혈압
    heart_rate = Column(Integer)  # 심박수
    temperature = Column(Float)  # 체온
    respiratory_rate = Column(Integer)  # 호흡수
    oxygen_saturation = Column(Float)  # 산소포화도
    created_at = Column(DateTime, default=datetime.utcnow)
```

---

### 예시 3: Legal 도메인 (법률 사무소 관리)

```python
# backend/app/models/legal_models.py
"""
Legal 도메인 특화 모델

법률 사무소 관리 시스템을 위한 데이터 모델들입니다.
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Date, Numeric
from datetime import datetime
from .base import Base


class LegalClient(Base):
    """고객 정보"""
    __tablename__ = "legal_clients"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    client_id = Column(String(50), unique=True, nullable=False)
    company_name = Column(String(200))  # 법인 고객일 경우
    business_number = Column(String(50))
    industry = Column(String(100))
    address = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class LegalCase(Base):
    """법률 사건"""
    __tablename__ = "legal_cases"

    id = Column(Integer, primary_key=True, autoincrement=True)
    client_id = Column(Integer, ForeignKey("legal_clients.id"), nullable=False)
    case_number = Column(String(100), unique=True, nullable=False)
    case_type = Column(String(100))  # civil, criminal, corporate, etc.
    case_title = Column(String(300), nullable=False)
    filing_date = Column(Date)
    court_name = Column(String(200))
    status = Column(String(50))  # pending, active, closed
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class Contract(Base):
    """계약서"""
    __tablename__ = "legal_contracts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    client_id = Column(Integer, ForeignKey("legal_clients.id"), nullable=False)
    contract_number = Column(String(100), unique=True)
    contract_type = Column(String(100))  # employment, partnership, service, etc.
    title = Column(String(300), nullable=False)
    effective_date = Column(Date)
    expiration_date = Column(Date)
    contract_value = Column(Numeric(15, 2))
    status = Column(String(50))  # draft, active, expired, terminated
    document_url = Column(String(500))
    summary = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class CaseNote(Base):
    """사건 노트"""
    __tablename__ = "legal_case_notes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    case_id = Column(Integer, ForeignKey("legal_cases.id"), nullable=False)
    note_date = Column(DateTime, nullable=False)
    note_type = Column(String(50))  # meeting, research, filing, hearing
    title = Column(String(300))
    content = Column(Text, nullable=False)
    billable_hours = Column(Numeric(5, 2))
    attorney_name = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
```

---

### 예시 4: Education 도메인 (교육 관리 시스템)

```python
# backend/app/models/education_models.py
"""
Education 도메인 특화 모델

온라인 교육 플랫폼을 위한 데이터 모델들입니다.
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean
from datetime import datetime
from .base import Base


class Course(Base):
    """강좌"""
    __tablename__ = "education_courses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    course_code = Column(String(50), unique=True, nullable=False)
    title = Column(String(300), nullable=False)
    description = Column(Text)
    instructor_name = Column(String(100))
    category = Column(String(100))
    difficulty_level = Column(String(50))  # beginner, intermediate, advanced
    duration_hours = Column(Integer)
    is_published = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Enrollment(Base):
    """수강 신청"""
    __tablename__ = "education_enrollments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("education_courses.id"), nullable=False)
    enrollment_date = Column(DateTime, nullable=False)
    completion_status = Column(String(50))  # enrolled, in_progress, completed, dropped
    progress_percentage = Column(Integer, default=0)
    final_grade = Column(String(10))
    certificate_issued = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Assignment(Base):
    """과제"""
    __tablename__ = "education_assignments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    course_id = Column(Integer, ForeignKey("education_courses.id"), nullable=False)
    title = Column(String(300), nullable=False)
    description = Column(Text)
    due_date = Column(DateTime)
    max_score = Column(Integer, default=100)
    created_at = Column(DateTime, default=datetime.utcnow)


class Submission(Base):
    """과제 제출"""
    __tablename__ = "education_submissions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    assignment_id = Column(Integer, ForeignKey("education_assignments.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    submission_date = Column(DateTime, nullable=False)
    content = Column(Text)
    file_url = Column(String(500))
    score = Column(Integer)
    feedback = Column(Text)
    graded_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
```

---

## Option B: 단일 도메인 모델 파일 (간단한 경우)

도메인이 하나만 필요한 경우, domain_models.py 하나로 관리할 수 있습니다.

```python
# backend/app/models/domain_models.py
"""
도메인 특화 모델

프로젝트의 도메인에 맞는 모델들을 이 파일에 정의합니다.
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from datetime import datetime
from .base import Base


# 여기에 도메인 특화 모델 추가
class DomainSpecificModel(Base):
    """도메인별 모델 예시"""
    __tablename__ = "domain_specific_table"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    # ... 필드 정의
    created_at = Column(DateTime, default=datetime.utcnow)
```

---

## Option C: 하위 패키지로 관리 (대규모 프로젝트)

도메인이 많고 각 도메인의 모델이 많은 경우, 하위 패키지로 구조화합니다.

```
backend/app/models/
├── __init__.py
├── base.py
├── core.py
├── shared.py
├── fitness/
│   ├── __init__.py
│   ├── member.py          # Member, MemberProgress
│   ├── program.py         # WorkoutProgram, NutritionPlan
│   └── assessment.py      # InBodyMeasurement, PostureAnalysis
├── medical/
│   ├── __init__.py
│   ├── patient.py         # Patient, VitalSigns
│   ├── record.py          # MedicalRecord, Prescription
│   └── billing.py         # Invoice, Payment
└── legal/
    ├── __init__.py
    ├── client.py          # LegalClient
    ├── case.py            # LegalCase, CaseNote
    └── document.py        # Contract, Agreement
```

```python
# backend/app/models/fitness/__init__.py
from .member import Member, MemberProgress
from .program import WorkoutProgram, NutritionPlan
from .assessment import InBodyMeasurement, PostureAnalysis

__all__ = [
    "Member",
    "MemberProgress",
    "WorkoutProgram",
    "NutritionPlan",
    "InBodyMeasurement",
    "PostureAnalysis",
]
```

```python
# backend/app/models/__init__.py
from .base import Base
from .core import User
from .shared import Bookmark

# Import domain packages
from .fitness import (
    Member,
    MemberProgress,
    WorkoutProgram,
    NutritionPlan,
)

__all__ = [
    "Base",
    "User",
    "Bookmark",
    "Member",
    "MemberProgress",
    "WorkoutProgram",
    "NutritionPlan",
]
```

---

## 🗄️ Database 설정

### 도메인별 데이터베이스 분리

각 도메인별로 별도의 데이터베이스를 사용할 수 있습니다.

```python
# backend/database/config.py
"""
Database Configuration

도메인별 데이터베이스 연결 설정
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Fitness 도메인
FITNESS_DB_URL = "sqlite:///./backend/database/relation_db/fitness.db"
fitness_engine = create_engine(FITNESS_DB_URL, echo=True)
FitnessSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=fitness_engine)

# Medical 도메인
MEDICAL_DB_URL = "sqlite:///./backend/database/relation_db/medical.db"
medical_engine = create_engine(MEDICAL_DB_URL, echo=True)
MedicalSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=medical_engine)

# Legal 도메인
LEGAL_DB_URL = "sqlite:///./backend/database/relation_db/legal.db"
legal_engine = create_engine(LEGAL_DB_URL, echo=True)
LegalSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=legal_engine)
```

### 단일 데이터베이스 사용

모든 도메인을 하나의 데이터베이스에서 관리할 수도 있습니다.

```python
# backend/database/session.py
"""
Database Session Management

단일 데이터베이스 연결
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "sqlite:///./backend/database/relation_db/app.db"

engine = create_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """Database session generator"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

---

## 📋 체크리스트

도메인 모델을 추가할 때 다음 사항을 확인하세요:

### 1. 모델 설계
- [ ] 도메인의 핵심 엔티티 파악
- [ ] 엔티티 간 관계 정의 (1:N, N:M)
- [ ] 필수 필드와 선택 필드 구분
- [ ] 데이터 타입 선택 (String, Integer, Float, Date, DateTime, Text 등)

### 2. 파일 구조
- [ ] 도메인 모델 파일 생성 (예: fitness_models.py)
- [ ] __init__.py에 모델 등록
- [ ] __all__에 export할 모델 추가

### 3. 데이터베이스
- [ ] Alembic 마이그레이션 생성
- [ ] 마이그레이션 검토 및 수정
- [ ] 마이그레이션 적용
- [ ] 데이터베이스 테이블 확인

### 4. CRUD Operations
- [ ] database/ 디렉토리에 CRUD 함수 생성
- [ ] Create, Read, Update, Delete 구현
- [ ] 트랜잭션 처리 고려

### 5. 테스트
- [ ] 단위 테스트 작성
- [ ] 통합 테스트 작성
- [ ] 마이그레이션 롤백 테스트

---

## 🔗 관련 문서

- **Alembic 마이그레이션**: `backend/alembic/`
- **CRUD Operations**: `backend/database/`
- **Agent State Schemas**: `backend/app/octostrator/states/`
- **Base Agent Guide**: `reports/base_agent/DOCSTRING_IMPLEMENTATION_GUIDE_COMPLETION_251110.md`
- **Supervisor Guide**: `reports/base_agent/SUPERVISOR_GENERALIZATION_PLAN_251110.md`

---

## ✅ 마이그레이션 전략

### 기존 PT 시스템을 다른 도메인으로 전환하는 경우

1. **데이터 백업**
   ```bash
   cp backend/database/relation_db/fitness.db backend/database/relation_db/fitness.db.backup
   ```

2. **새 도메인 모델 생성**
   - 위 예시를 참고하여 도메인 모델 작성

3. **마이그레이션 생성**
   ```bash
   cd backend
   alembic revision --autogenerate -m "Migrate from fitness to medical domain"
   ```

4. **데이터 마이그레이션 스크립트 작성**
   ```python
   # alembic/versions/xxxx_migrate_domains.py
   from alembic import op

   def upgrade():
       # 기존 데이터를 새 스키마로 마이그레이션
       pass

   def downgrade():
       # 롤백 로직
       pass
   ```

5. **적용 및 검증**
   ```bash
   alembic upgrade head
   # 데이터 검증
   ```

---

## 📚 Best Practices

1. **명명 규칙**
   - 테이블명: `{domain}_{entity}` (예: `fitness_members`, `medical_patients`)
   - 모델 클래스: PascalCase (예: `MemberProgress`, `MedicalRecord`)
   - 필드명: snake_case (예: `created_at`, `body_fat_percentage`)

2. **외래키 사용**
   - 항상 `ForeignKey` 제약 조건 설정
   - `nullable=False`로 필수 관계 명시
   - 필요시 `ondelete="CASCADE"` 설정

3. **Timestamp 필드**
   - 모든 테이블에 `created_at`, `updated_at` 추가 권장
   - `default=datetime.utcnow` 사용

4. **인덱스 최적화**
   - 자주 검색하는 필드에 `index=True` 설정
   - 복합 인덱스 고려

5. **문서화**
   - 각 모델에 명확한 docstring 작성
   - 필드에 주석으로 설명 추가

---

## 🎯 Summary

이 가이드는 Specialist Agent System에 새로운 도메인의 데이터 모델을 추가하는 방법을 제공합니다.

**핵심 원칙**:
- 도메인별로 모델 분리 (fitness_models.py, medical_models.py 등)
- 범용 User, Bookmark 모델 재사용
- 명확한 네이밍과 문서화
- Alembic으로 마이그레이션 관리

**참고 자료**:
- `backend/app/models/archive/fitness/`: PT 도메인 모델 예시
- 위 예시들: Medical, Legal, Education 도메인 구현 샘플

새로운 도메인을 추가할 때 이 가이드를 참고하여 일관된 구조로 개발하세요.
