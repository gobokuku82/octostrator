"""
Core Generic Models - 범용 모델

도메인에 구애받지 않는 범용 사용자 모델을 제공합니다.

⚠️ 현재 상태 (범용 시스템)
==========================================
User 모델은 모든 도메인에서 공통적으로 사용할 수 있는 최소한의 필드만 포함합니다:
- 기본 정보: name, email, phone
- 도메인 독립적 필드: user_type, metadata (JSON)

도메인 특화 필드는 포함하지 않습니다:
- ❌ PT 특화: goal (weight_loss, muscle_gain), level (beginner, intermediate)
- ❌ 의료 특화: blood_type, allergies, medical_history
- ❌ 법률 특화: client_type, company_name, business_number

🔮 도메인별 확장 방법
==========================================

## Option A: 별도 도메인 모델로 확장 (권장)

User를 외래키로 참조하는 도메인별 프로필 모델을 생성합니다.

### 예시 1: Fitness 도메인
```python
# backend/app/models/fitness_models.py
class FitnessMember(Base):
    \"\"\"Fitness 도메인 회원 프로필\"\"\"
    __tablename__ = "fitness_members"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    goal = Column(String(50))  # weight_loss, muscle_gain, endurance
    fitness_level = Column(String(20))  # beginner, intermediate, advanced
    preferred_workout_time = Column(String(50))
    membership_type = Column(String(50))
```

### 예시 2: Medical 도메인
```python
# backend/app/models/medical_models.py
class Patient(Base):
    \"\"\"Medical 도메인 환자 프로필\"\"\"
    __tablename__ = "medical_patients"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    patient_id = Column(String(50), unique=True)
    blood_type = Column(String(10))
    allergies = Column(Text)
    medical_history = Column(Text)
```

## Option B: user_type + extra_data로 확장

User의 user_type과 extra_data (JSON) 필드를 활용하여 도메인별 데이터를 저장합니다.

### 사용 예시
```python
# Fitness 회원 생성
user = User(
    name="홍길동",
    email="hong@example.com",
    user_type="fitness_member",
    extra_data=json.dumps({
        "goal": "weight_loss",
        "fitness_level": "beginner",
        "membership_type": "premium"
    })
)

# Medical 환자 생성
user = User(
    name="김환자",
    email="patient@example.com",
    user_type="medical_patient",
    extra_data=json.dumps({
        "patient_id": "P12345",
        "blood_type": "A+",
        "allergies": ["penicillin"]
    })
)
```

📚 See Also
==========================================
- DOMAIN_MODELS_GUIDE.md: 도메인별 모델 추가 가이드
- backend/app/models/archive/fitness/: PT 도메인 모델 예시
"""

from sqlalchemy import Column, Integer, String, DateTime, Text
from datetime import datetime
from .base import Base


class User(Base):
    """
    범용 사용자 모델

    모든 도메인에서 공통적으로 사용할 수 있는 사용자 기본 정보를 저장합니다.
    도메인 특화 필드는 별도의 프로필 모델(FitnessMember, Patient, LegalClient 등)로
    확장하거나 extra_data 필드에 JSON으로 저장합니다.

    Attributes:
        id: 사용자 고유 ID (Primary Key)
        name: 사용자 이름
        email: 이메일 (고유값)
        phone: 전화번호
        user_type: 사용자 유형 (예: "fitness_member", "medical_patient", "legal_client")
        extra_data: 도메인별 추가 정보 (JSON 형식)
        created_at: 계정 생성 시각
        updated_at: 최종 수정 시각

    Examples:
        >>> # Fitness 회원
        >>> user = User(
        ...     name="홍길동",
        ...     email="hong@example.com",
        ...     user_type="fitness_member"
        ... )

        >>> # Medical 환자
        >>> user = User(
        ...     name="김환자",
        ...     email="patient@example.com",
        ...     user_type="medical_patient"
        ... )
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True)
    phone = Column(String(20))
    user_type = Column(String(50))  # 도메인별 사용자 유형 (fitness_member, patient, client 등)
    extra_data = Column(Text)  # JSON 형식의 도메인별 추가 정보 (metadata는 SQLAlchemy 예약어)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
