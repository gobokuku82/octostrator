# Database & Model 범용화 계획서

**작성일**: 2025-11-10
**목적**: PT 특화된 데이터 모델 및 데이터베이스 레이어 범용화 전략 수립
**작업 범위**: backend/app/models + backend/database

---

## 📋 현재 상태 분석

### 발견된 PT 특화 파일 (11개)

#### 1. **backend/app/models/** (7개 도메인별 모델)

| 파일 | PT 특화 내용 | 심각도 |
|-----|------------|-------|
| **frontdesk.py** | - `interest`: "weight_loss, muscle_gain, fitness"<br>- Lead, Inquiry, Appointment 모델 | ⚠️ 중간 |
| **assessor.py** | - `InBodyData`: 체성분 측정 (PT 전용 장비)<br>- `PostureAnalysis`: 자세 분석<br>- muscle_mass, body_fat, spine_curvature 등 | 🔴 높음 |
| **program_designer.py** | - `Program`: workout, diet<br>- `MealLog`: 식단 기록<br>- `WorkoutRoutine`: 운동 루틴<br>- muscle_group: legs, chest, back, shoulders, arms | 🔴 높음 |
| **manager.py** | - 회원 관리, 출석, 이탈 위험 분석 | ⚠️ 중간 |
| **marketing.py** | - SNS 포스트, 이벤트 관리 | 🟢 낮음 |
| **owner.py** | - 매출, 트레이너 성과 | ⚠️ 중간 |
| **trainer.py** | - 트레이너 스킬, 교육 계획 | ⚠️ 중간 |

#### 2. **backend/database/relation_db/models.py**

완전히 PT 특화된 통합 모델 파일:

```python
"""SQLite Database Models for Fitness PT Manager"""

class User:
    goal = "weight_loss, muscle_gain, fitness"  # PT 특화
    level = "beginner, intermediate, advanced"  # PT 특화

class MealLog:
    meal_type = "breakfast, lunch, dinner, pre_workout, post_workout"  # PT 특화
    nutrition = {...}  # PT 특화

class WorkoutRoutine:
    muscle_group = "legs, chest, back, shoulders, arms"  # PT 특화

class Schedule:
    """PT 스케줄 테이블"""  # PT 특화

class MemberProgress:
    weight, body_fat_percentage, muscle_mass  # PT 특화
```

#### 3. **backend/database/relation_db/nutrition_seed_data.py**

PT 도메인 시드 데이터 (운동, 식품 영양정보)

---

## 🎯 핵심 문제점

### 1. **Supervisor vs Models/Database 차이**

| 레이어 | 특성 | 범용화 난이도 |
|-------|------|-------------|
| **Supervisor** (완료) | - 로직 레이어<br>- 동적 Agent 선택<br>- 데이터 독립적 | 🟢 쉬움 (Docstring만 추가) |
| **Models/Database** (현재) | - 데이터 레이어<br>- 스키마 고정<br>- 도메인 의존적 | 🔴 어려움 (구조 변경 필요) |

### 2. **범용화 시 문제점**

#### 문제 1: 도메인별 스키마가 완전히 다름

```python
# PT 도메인
class MemberProgress:
    weight = Column(Float)
    muscle_mass = Column(Float)
    body_fat_percentage = Column(Float)

# 의료 도메인 (필요한 스키마)
class PatientRecord:
    blood_pressure = Column(String)
    diagnosis = Column(Text)
    medications = Column(Text)

# 법률 도메인 (필요한 스키마)
class LegalCase:
    case_number = Column(String)
    court = Column(String)
    case_status = Column(String)
```

**결론**: 하나의 범용 모델로 모든 도메인을 커버하기 **불가능**

#### 문제 2: 기존 데이터 마이그레이션

- 이미 생성된 SQLite 테이블 구조 변경 필요
- 기존 PT 데이터 손실 위험
- Alembic 마이그레이션 복잡도 증가

#### 문제 3: 하위 호환성

- 현재 PT 기능이 깨질 수 있음
- 7개 Agent (frontdesk, assessor, program_designer 등)가 모두 영향받음
- Tools (62개)도 모델에 의존

---

## 🔮 범용화 전략 (3가지 옵션)

### ✅ **Option A: 도메인별 분리 유지** (권장)

**전략**: PT 도메인 모델은 그대로 유지하고, 새 도메인은 별도 모델 생성

#### 구조

```
backend/app/models/
├── base.py                    # 공통 Base 클래스
├── core.py                    # 범용 core 모델 (User, Log 등)
├── shared.py                  # 공유 유틸리티
│
├── domains/                   # 도메인별 모델 (새 구조)
│   ├── fitness/               # PT 도메인 (기존 유지)
│   │   ├── frontdesk.py
│   │   ├── assessor.py
│   │   ├── program_designer.py
│   │   ├── manager.py
│   │   ├── marketing.py
│   │   ├── owner.py
│   │   └── trainer.py
│   │
│   ├── medical/               # 의료 도메인 (새로 추가)
│   │   ├── patient.py
│   │   ├── diagnosis.py
│   │   └── treatment.py
│   │
│   ├── legal/                 # 법률 도메인 (새로 추가)
│   │   ├── case.py
│   │   ├── document.py
│   │   └── client.py
│   │
│   └── education/             # 교육 도메인 (새로 추가)
│       ├── student.py
│       ├── course.py
│       └── assessment.py
```

#### 장점

- ✅ **기존 PT 기능 유지** (하위 호환성 100%)
- ✅ **데이터 마이그레이션 불필요**
- ✅ **도메인별 최적화 가능** (각 도메인에 맞는 스키마)
- ✅ **점진적 확장 가능** (새 도메인 추가 시)
- ✅ **낮은 위험도**

#### 단점

- ❌ 도메인별 중복 코드 가능
- ❌ 파일 구조 복잡해짐

#### 구현 예시

```python
# backend/app/models/domains/fitness/assessor.py (기존 유지)
class InBodyData(Base):
    """InBody 측정 데이터 (Fitness 도메인 전용)"""
    __tablename__ = "fitness_inbody_data"

    weight = Column(Float)
    muscle_mass = Column(Float)
    body_fat_percentage = Column(Float)

# backend/app/models/domains/medical/patient.py (새로 추가)
class PatientVitals(Base):
    """환자 바이탈 데이터 (Medical 도메인 전용)"""
    __tablename__ = "medical_patient_vitals"

    blood_pressure = Column(String)
    heart_rate = Column(Integer)
    temperature = Column(Float)

# backend/app/models/domains/legal/case.py (새로 추가)
class LegalCase(Base):
    """법률 사건 데이터 (Legal 도메인 전용)"""
    __tablename__ = "legal_cases"

    case_number = Column(String)
    court = Column(String)
    filing_date = Column(DateTime)
```

---

### ⚠️ **Option B: 추상화 레이어 추가** (중간)

**전략**: 범용 Base 모델 + 도메인별 확장 (상속)

#### 구조

```python
# backend/app/models/base.py
class GenericRecord(Base):
    """범용 레코드 (모든 도메인 공통)"""
    __abstract__ = True

    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    metadata = Column(Text)  # JSON: 도메인별 커스텀 필드

class GenericMeasurement(Base):
    """범용 측정 데이터"""
    __abstract__ = True

    user_id = Column(Integer, ForeignKey("users.id"))
    measurement_date = Column(DateTime)
    measurements = Column(Text)  # JSON: 도메인별 측정값

# backend/app/models/domains/fitness/assessor.py
class InBodyData(GenericMeasurement):
    """InBody 측정 데이터 (Fitness 특화)"""
    __tablename__ = "fitness_inbody_data"

    # Fitness 특화 필드 (명시적)
    weight = Column(Float)
    muscle_mass = Column(Float)

# backend/app/models/domains/medical/vitals.py
class PatientVitals(GenericMeasurement):
    """환자 바이탈 (Medical 특화)"""
    __tablename__ = "medical_vitals"

    # Medical 특화 필드
    blood_pressure = Column(String)
    heart_rate = Column(Integer)
```

#### 장점

- ✅ 공통 로직 재사용
- ✅ 도메인별 확장 가능
- ✅ 타입 안정성

#### 단점

- ❌ 추상화 복잡도 증가
- ❌ 여전히 도메인별 모델 필요
- ❌ 마이그레이션 필요 (기존 모델 → 상속 구조)

---

### 🔴 **Option C: 완전 범용 모델** (비권장)

**전략**: EAV (Entity-Attribute-Value) 패턴으로 완전 범용화

#### 구조

```python
class Entity(Base):
    """범용 엔티티"""
    __tablename__ = "entities"

    id = Column(Integer, primary_key=True)
    entity_type = Column(String(50))  # "patient", "member", "case"
    created_at = Column(DateTime)

class Attribute(Base):
    """범용 속성 정의"""
    __tablename__ = "attributes"

    id = Column(Integer, primary_key=True)
    entity_type = Column(String(50))
    attribute_name = Column(String(100))  # "weight", "blood_pressure"
    data_type = Column(String(20))  # "float", "string", "datetime"

class Value(Base):
    """범용 값 저장"""
    __tablename__ = "values"

    id = Column(Integer, primary_key=True)
    entity_id = Column(Integer, ForeignKey("entities.id"))
    attribute_id = Column(Integer, ForeignKey("attributes.id"))
    value = Column(Text)  # 모든 값을 Text로 저장
```

#### 장점

- ✅ 완전한 도메인 독립성
- ✅ 새 도메인 추가 시 스키마 변경 불필요

#### 단점

- ❌ **성능 심각하게 저하** (JOIN 폭발)
- ❌ **쿼리 복잡도 극대화**
- ❌ **타입 안정성 상실**
- ❌ **ORM 장점 상실**
- ❌ **디버깅 극도로 어려움**
- ❌ **완전한 재설계 및 마이그레이션 필요**

**결론**: ❌ **사용하지 않는 것을 강력히 권장**

---

## 📝 권장 사항: Option A (도메인별 분리 유지)

### 왜 Option A를 권장하는가?

1. **Supervisor는 이미 범용화 완료** (Docstring 가이드)
   - Agent 선택, Intent 분류, Planning이 동적
   - 어떤 도메인 Agent든 자동 탐지 및 사용

2. **데이터 모델은 도메인 특성 반영 필요**
   - PT: 체성분, 운동 루틴, 식단
   - 의료: 진단, 처방, 바이탈
   - 법률: 사건, 계약, 고객
   - **→ 하나의 스키마로 통합 불가능**

3. **현재 PT 기능 보존 중요**
   - 7개 Agent가 이미 구현됨
   - 62개 Tool이 모델에 의존
   - 데이터 손실 위험 없음

4. **새 도메인 추가 유연성**
   - `domains/medical/` 폴더 생성
   - 의료 도메인 모델만 추가
   - 기존 PT 코드와 완전히 독립

### 구현 계획 (5단계)

#### **Phase 1: 디렉토리 구조 재구성** (1일)

```bash
# 현재 구조
backend/app/models/
├── frontdesk.py
├── assessor.py
├── program_designer.py
├── manager.py
├── marketing.py
├── owner.py
└── trainer.py

# 새 구조
backend/app/models/
├── base.py                    # 공통 Base (유지)
├── core.py                    # 범용 core 모델 (유지)
├── shared.py                  # 공유 유틸리티 (유지)
└── domains/
    └── fitness/               # PT 도메인
        ├── __init__.py
        ├── frontdesk.py       # 기존 파일 이동
        ├── assessor.py        # 기존 파일 이동
        ├── program_designer.py
        ├── manager.py
        ├── marketing.py
        ├── owner.py
        └── trainer.py
```

**작업**:
1. `domains/fitness/` 디렉토리 생성
2. 기존 7개 파일을 `domains/fitness/`로 이동
3. `__init__.py`에서 import 경로 수정

#### **Phase 2: Import 경로 수정** (1-2일)

모든 참조 위치 수정:

```python
# Before
from backend.app.models.frontdesk import Lead, Inquiry

# After
from backend.app.models.domains.fitness.frontdesk import Lead, Inquiry
```

**영향받는 파일**:
- `backend/app/octostrator/tools/*.py` (62개 Tools)
- `backend/database/*.py` (CRUD 함수)
- `backend/app/octostrator/execution_agents/*/*.py` (7개 Agent)

#### **Phase 3: Docstring 업데이트** (1일)

각 모델 파일에 도메인 명시:

```python
"""Frontdesk Agent models - Lead, Inquiry, Appointment

⚠️ 도메인: Fitness (PT Manager)
==========================================
이 모델은 Fitness/PT 도메인에 특화되어 있습니다.

다른 도메인 구현 시:
- backend/app/models/domains/{domain_name}/ 디렉토리 생성
- 해당 도메인에 맞는 모델 정의
- Agent Registry에 등록하면 자동으로 Supervisor에서 사용 가능

예시:
- domains/medical/: 의료 도메인 모델
- domains/legal/: 법률 도메인 모델
- domains/education/: 교육 도메인 모델
"""
```

#### **Phase 4: 새 도메인 추가 가이드 작성** (1일)

**파일**: `backend/app/models/domains/README.md`

```markdown
# Domain Models Guide

## 새 도메인 추가 방법

### Step 1: 디렉토리 생성
```bash
mkdir -p backend/app/models/domains/{domain_name}
```

### Step 2: 모델 파일 작성
```python
# backend/app/models/domains/medical/patient.py
from backend.app.models.base import Base

class Patient(Base):
    __tablename__ = "medical_patients"

    # 의료 도메인 특화 필드
    patient_id = Column(String, unique=True)
    blood_type = Column(String)
    allergies = Column(Text)
```

### Step 3: Agent 구현
```python
# backend/app/octostrator/execution_agents/medical/patient_agent.py
from backend.app.octostrator.execution_agents.base import BaseAgent

class PatientAgent(BaseAgent):
    capabilities = [Capability.DATA_ANALYSIS, ...]
```

### Step 4: Agent Registry 등록
```python
agent_registry.register(PatientAgent, "patient_agent")
```

**완료!** Supervisor가 자동으로 인식하고 사용합니다.
```

#### **Phase 5: 테스트 및 검증** (2일)

1. **Import 경로 테스트**
   ```bash
   python -m pytest backend/test_*.py
   ```

2. **기존 PT Agent 동작 확인**
   - 7개 Agent 모두 정상 작동 확인
   - 62개 Tool 정상 작동 확인

3. **새 도메인 추가 시뮬레이션**
   - `domains/demo/` 생성
   - 간단한 모델 추가
   - Agent 등록 및 Supervisor 동작 확인

---

## 🔄 Option A vs 현재 Supervisor 범용화 비교

| 레이어 | 범용화 방식 | 결과 |
|-------|-----------|------|
| **Supervisor** | Docstring 가이드 + 동적 Agent 선택 | ✅ 어떤 도메인 Agent든 자동 지원 |
| **Models (Option A)** | 도메인별 디렉토리 분리 | ✅ 도메인별 최적화 + 독립성 |

**시너지 효과**:
1. Supervisor가 Agent Registry에서 동적으로 Agent 탐지
2. 새 도메인 모델 추가 → Agent 구현 → Registry 등록
3. Supervisor가 자동으로 새 Agent 인식 및 사용

**완전한 범용 시스템 달성!** 🎉

---

## ❌ 하지 말아야 할 것

### 1. 기존 PT 모델 삭제 또는 대폭 수정
- ❌ 7개 Agent가 의존
- ❌ 62개 Tool이 의존
- ❌ 데이터 손실 위험

### 2. 모든 도메인을 하나의 범용 모델로 통합
- ❌ 성능 저하
- ❌ 복잡도 증가
- ❌ 유지보수 악몽

### 3. 즉시 전체 리팩토링
- ❌ 높은 위험도
- ❌ 기존 기능 깨질 가능성

---

## ✅ 해야 할 것

### 1. 점진적 마이그레이션
- ✅ Phase별 진행
- ✅ 각 Phase 후 테스트
- ✅ 하위 호환성 유지

### 2. Docstring 가이드 추가
- ✅ 새 도메인 추가 방법 문서화
- ✅ 코드 예시 제공
- ✅ 베스트 프랙티스 명시

### 3. 테스트 강화
- ✅ 기존 PT 기능 회귀 테스트
- ✅ 새 도메인 통합 테스트
- ✅ Import 경로 변경 검증

---

## 📊 예상 소요 시간 (Option A)

| Phase | 작업 내용 | 소요 시간 | 위험도 |
|-------|---------|----------|-------|
| **Phase 1** | 디렉토리 구조 재구성 | 1일 | 🟢 낮음 |
| **Phase 2** | Import 경로 수정 | 1-2일 | ⚠️ 중간 |
| **Phase 3** | Docstring 업데이트 | 1일 | 🟢 낮음 |
| **Phase 4** | 가이드 문서 작성 | 1일 | 🟢 낮음 |
| **Phase 5** | 테스트 및 검증 | 2일 | ⚠️ 중간 |
| **총합** | | **6-7일** | ⚠️ 중간 |

**Option B 예상**: 10-15일 (높은 위험도)
**Option C 예상**: 30-60일 (매우 높은 위험도)

---

## 🎯 다음 단계 제안

### 즉시 가능한 작업 (코드 수정 없음)

1. **Docstring 가이드 추가** (이번 세션에서 가능)
   - 7개 모델 파일에 도메인 명시
   - 새 도메인 추가 방법 설명
   - 예시 코드 제공

2. **README 작성**
   - `backend/app/models/domains/README.md`
   - 도메인 구조 설명
   - 마이그레이션 계획 문서화

### 향후 구현 (사용자 결정 후)

3. **Phase 1-5 실행**
   - 사용자 승인 후 진행
   - 6-7일 소요 예상
   - 점진적 테스트

---

## 📋 결론

### Supervisor vs Models/Database 범용화 전략

| 레이어 | 전략 | 이유 |
|-------|------|-----|
| **Supervisor** | Docstring + 동적 선택 | 로직 레이어라서 데이터 독립적 |
| **Models/Database** | 도메인별 분리 (Option A) | 데이터 레이어라서 도메인 의존적 |

### 권장 사항

- ✅ **Option A: 도메인별 분리 유지** 선택
- ✅ **점진적 마이그레이션** (5-Phase)
- ✅ **기존 PT 기능 100% 보존**
- ✅ **새 도메인 추가 유연성 확보**

### 다음 액션

**사용자 결정 필요**:
1. Option A, B, C 중 선택
2. 즉시 Docstring 가이드만 추가할지, 아니면 전체 마이그레이션 진행할지
3. 마이그레이션 진행 시 시작 시점

---

**작성자**: Claude Code
**작성일**: 2025-11-10
**상태**: 사용자 결정 대기

**참고 문서**:
- [SUPERVISOR_GENERALIZATION_PLAN_251110.md](./SUPERVISOR_GENERALIZATION_PLAN_251110.md) - Supervisor 범용화 계획
- [DOCSTRING_IMPLEMENTATION_GUIDE_COMPLETION_251110.md](./DOCSTRING_IMPLEMENTATION_GUIDE_COMPLETION_251110.md) - Docstring 작업 완료 보고서
