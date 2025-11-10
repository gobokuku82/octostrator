# Agent 설명 위치 가이드

**작성일**: 2025-11-10
**목적**: Agent 예시 설명이 포함된 파일 위치와 내용 정리
**상태**: PT 관련 용어가 남아있음 (범용화 대기)

---

## 📋 개요

이 문서는 Agent 설명 (예시, 역할, 기능 등)이 하드코딩되어 있는 파일들의 위치를 정리합니다.
사용자가 검토 후 범용화 여부를 결정할 수 있도록 코드 위치와 내용을 제공합니다.

---

## 🎯 Agent 설명이 포함된 파일 (7개)

### 1. **todo_manager.py** (Agent 선택 로직)

**파일**: `backend/app/octostrator/supervisors/todo/todo_manager.py`

**위치**: Line 567-633

**내용**: LLM 기반 Agent 선택 함수 (`select_agent_for_task`)

**PT 관련 설명**:
```python
async def select_agent_for_task(step: dict, llm) -> str:
    """
    Task를 분석하여 적절한 Agent 선택 (LLM 기반)

    Available agents:
    - frontdesk_agent: 신규 리드 관리, 상담 예약, 문의 응대
    - assessor_agent: 체성분 분석, 자세 평가, 피트니스 점수
    - program_designer_agent: 운동/식단 프로그램 설계
    - manager_agent: 회원 출석 관리, 이탈 위험 분석
    - marketing_agent: SNS 마케팅, 이벤트 운영
    - owner_assistant_agent: 매출 분석, 트레이너 성과 관리
    - trainer_education_agent: 트레이너 교육 및 스킬 평가
    ...
    """
```

**LLM 프롬프트 (Line 594-608)**:
```python
prompt = f"""You are an AI agent router. Given a task description, select the most appropriate agent.

Available agents:
- frontdesk_agent: 신규 리드 관리, 상담 예약, 문의 응대, 고객 정보 수집
- assessor_agent: 체성분 분석(InBody), 자세 평가, 피트니스 점수 계산
- program_designer_agent: 운동 프로그램 설계, 식단 프로그램 작성
- manager_agent: 회원 출석 관리, 이탈 위험 분석, PT 세션 관리
- marketing_agent: SNS 콘텐츠 생성, 이벤트 기획, 마케팅 캠페인
- owner_assistant_agent: 매출 분석, 트레이너 성과 분석, 비즈니스 리포트
- trainer_education_agent: 트레이너 교육 자료 생성, 스킬 평가

Task: {task_description}

Return ONLY the agent name (e.g., "frontdesk_agent"), nothing else."""
```

**범용화 제안**:
- "신규 리드 관리" → "고객 접수 관리"
- "체성분 분석(InBody)" → "데이터 분석 및 평가"
- "운동 프로그램" → "서비스 프로그램"
- "회원" → "고객"
- "PT 세션" → "서비스 세션"
- "트레이너" → "전문가/스태프"

---

### 2. **cognitive_helpers.py** (Agent 매핑)

**파일**: `backend/app/octostrator/supervisors/cognitive/cognitive_helpers.py`

**위치**: Line 88-129

**내용**: Capability → Agent 매핑 딕셔너리

**PT 관련 설명**:
```python
CAPABILITY_TO_AGENTS = {
    "customer_intake": ["frontdesk_agent"],  # 신규 고객 접수
    "inquiry_handling": ["frontdesk_agent"],  # 문의 응답
    "appointment_scheduling": ["frontdesk_agent"],  # 상담 예약

    "fitness_assessment": ["assessor_agent"],  # 체성분 분석
    "posture_analysis": ["assessor_agent"],  # 자세 평가

    "workout_design": ["program_designer_agent"],  # 운동 프로그램 설계
    "diet_planning": ["program_designer_agent"],  # 식단 계획

    "attendance_tracking": ["manager_agent"],  # 출석 관리
    "churn_prevention": ["manager_agent"],  # 이탈 방지

    "social_media": ["marketing_agent"],  # SNS 관리
    "event_management": ["marketing_agent"],  # 이벤트 운영

    "revenue_analysis": ["owner_assistant_agent"],  # 매출 분석
    "performance_tracking": ["owner_assistant_agent"],  # 성과 추적

    "trainer_development": ["trainer_education_agent"],  # 트레이너 교육
    "skill_assessment": ["trainer_education_agent"],  # 스킬 평가
}
```

**주석 설명 (한글)**:
- "신규 고객 접수" → 범용화 가능
- "체성분 분석" → "데이터 분석"
- "운동 프로그램" → "프로그램"
- "출석 관리" → 범용화 가능
- "트레이너 교육" → "전문가 교육"

---

### 3. **cognitive_nodes.py** (Capability 추출 로직)

**파일**: `backend/app/octostrator/supervisors/cognitive/cognitive_nodes.py`

**위치**: Line 67-130

**내용**: LLM 프롬프트로 Capability 추출

**PT 관련 설명** (Line 97-116):
```python
prompt = f"""Given the user's message, identify which capabilities are needed.

Available capabilities:
- customer_intake: 신규 고객 등록, 리드 생성
- inquiry_handling: 고객 문의 응답
- appointment_scheduling: 상담 예약
- fitness_assessment: 체성분(InBody) 분석
- posture_analysis: 자세 평가
- workout_design: 운동 프로그램 설계
- diet_planning: 식단 계획
- attendance_tracking: 출석 관리
- churn_prevention: 이탈 위험 분석
- social_media: SNS 콘텐츠 관리
- event_management: 이벤트 기획/운영
- revenue_analysis: 매출 분석
- performance_tracking: 트레이너 성과 추적
- trainer_development: 트레이너 교육
- skill_assessment: 스킬 평가

User message: {user_input}

Return a JSON array of capability names (e.g., ["customer_intake", "appointment_scheduling"])"""
```

**범용화 제안**:
- "체성분(InBody) 분석" → "상태 분석"
- "운동 프로그램" → "서비스 프로그램"
- "식단 계획" → "계획 수립"
- "트레이너" → "전문가"

---

### 4. **execution_agents/README.md** (전체 시스템 문서)

**파일**: `backend/app/octostrator/execution_agents/README.md`

**위치**: 전체 (1022 lines)

**PT 관련 내용**:
- Line 1: `# AI PT Manager - 7개 비즈니스 역할 기반 에이전트 매뉴얼`
- Line 3: `**프로젝트**: AI PTmanager - Beta v0.01`
- Line 25-28: "피트니스 센터 운영을 위한 7개 비즈니스 역할 기반 AI 에이전트"
- Line 32-40: Agent 목록 테이블 (PT 관련 설명 포함)

**Agent 설명 예시** (Line 32-40):
```markdown
| 에이전트 | 역할 | Tools 개수 | 주요 기능 |
|---------|------|-----------|----------|
| **Frontdesk** | 접수/상담 | 12 | 리드 관리, 문의 응답, 상담 예약 |
| **Assessor** | 체성분/자세 분석 | 7 | InBody 분석, 자세 평가, 피트니스 점수 |
| **Program Designer** | 운동/식단 설계 | 10 | 프로그램 생성, 템플릿 관리, 운동 검색 |
| **Manager** | 회원 관리 | 8 | 출석 관리, 이탈 위험 분석, 재등록 관리 |
| **Marketing** | 마케팅/이벤트 | 9 | SNS 관리, 이벤트 운영, 참여도 분석 |
| **Owner Assistant** | 경영 지원 | 8 | 매출 분석, 트레이너 성과, 비즈니스 지표 |
| **Trainer Education** | 트레이너 교육 | 8 | 스킬 평가, 교육 계획, 성장 관리 |
```

**범용화 제안**:
- "체성분/자세 분석" → "데이터 분석 및 평가"
- "운동/식단 설계" → "서비스 프로그램 설계"
- "회원 관리" → "고객 관리"
- "트레이너" → "전문가"

**참고**: 이 파일은 사용자가 보류 결정

---

### 5. **tools/__init__.py** (Tools Registry 주석)

**파일**: `backend/app/octostrator/tools/__init__.py`

**위치**: Line 1-4

**PT 관련 설명**:
```python
"""Specialist Agent Tools Registry

모든 Tool을 중앙에서 관리하는 단순 Dict 방식
Phase 2: 7개 비즈니스 역할 기반 에이전트 Tools (62개 Tools)
```

**상태**: 이미 "Specialist Agent"로 변경됨 ✅

---

### 6. **Tools 파일들** (각 Agent별 도구)

**위치**: `backend/app/octostrator/tools/`

**파일 목록**:
1. `frontdesk_tools.py` (12 tools)
2. `assessor_tools.py` (7 tools)
3. `program_designer_tools.py` (10 tools)
4. `manager_tools.py` (8 tools)
5. `marketing_tools.py` (9 tools)
6. `owner_assistant_tools.py` (8 tools)
7. `trainer_education_tools.py` (8 tools)

**PT 관련 용어 예시**:
- **assessor_tools.py**: `save_inbody_data`, `analyze_inbody_trend`, `calculate_fitness_score`
  - Docstring에 "InBody 데이터", "체성분", "피트니스 점수" 등

- **program_designer_tools.py**: `get_workout_templates`, `get_diet_templates`, `search_exercises`
  - Docstring에 "운동", "식단", "루틴" 등

- **manager_tools.py**: `record_attendance`, `calculate_churn_risk`
  - Docstring에 "출석", "회원", "PT 세션" 등

- **owner_assistant_tools.py**: `get_trainer_performance`
  - Docstring에 "트레이너", "PT 매출" 등

- **trainer_education_tools.py**: `assess_skill_level`, `create_development_plan`
  - Docstring에 "트레이너 스킬", "교육" 등

**범용화 영향**:
- Tool 함수명은 유지 (기능 명확)
- Docstring 설명만 범용화 검토

---

### 7. **capabilities.py** (Capability Enum)

**파일**: `backend/app/octostrator/execution_agents/base/capabilities.py`

**위치**: Line 9-47

**PT 관련 설명**:
```python
class Capability(str, Enum):
    """Agent Capabilities Enum

    7개 비즈니스 역할 기반 Capabilities
    """

    # Frontdesk (접수/상담)
    CUSTOMER_INTAKE = "customer_intake"
    INQUIRY_HANDLING = "inquiry_handling"
    APPOINTMENT_SCHEDULING = "appointment_scheduling"

    # Assessor (평가)
    FITNESS_ASSESSMENT = "fitness_assessment"
    POSTURE_ANALYSIS = "posture_analysis"

    # Program Designer (프로그램 설계)
    WORKOUT_DESIGN = "workout_design"
    DIET_PLANNING = "diet_planning"

    # Manager (회원 관리)
    ATTENDANCE_TRACKING = "attendance_tracking"
    CHURN_PREVENTION = "churn_prevention"

    # Marketing (마케팅)
    SOCIAL_MEDIA = "social_media"
    EVENT_MANAGEMENT = "event_management"

    # Owner Assistant (경영 지원)
    REVENUE_ANALYSIS = "revenue_analysis"
    PERFORMANCE_TRACKING = "performance_tracking"

    # Trainer Education (트레이너 교육)
    TRAINER_DEVELOPMENT = "trainer_development"
    SKILL_ASSESSMENT = "skill_assessment"
```

**주석 설명 (한글)**:
- "접수/상담" → 범용화 가능
- "평가" → 유지 가능
- "프로그램 설계" → 유지 가능
- "회원 관리" → "고객 관리"
- "트레이너 교육" → "전문가 교육"

**범용화 제안**:
- `FITNESS_ASSESSMENT` → `DATA_ASSESSMENT` 또는 `STATE_ASSESSMENT`
- `WORKOUT_DESIGN` → `PROGRAM_DESIGN`
- `DIET_PLANNING` → `SERVICE_PLANNING`
- `TRAINER_DEVELOPMENT` → `STAFF_DEVELOPMENT`

---

## 📊 요약

### 변경 필요 파일 (코드 수정)

| 파일 | 위치 | 변경 대상 | 우선순위 |
|-----|------|----------|---------|
| `todo_manager.py` | Line 567-633 | Agent 설명 (docstring + 프롬프트) | ⭐⭐⭐ 높음 |
| `cognitive_helpers.py` | Line 88-129 | 주석 (한글) | ⭐⭐ 중간 |
| `cognitive_nodes.py` | Line 97-116 | LLM 프롬프트 | ⭐⭐⭐ 높음 |
| `capabilities.py` | Line 9-47 | Enum 주석 (한글) | ⭐ 낮음 |

### 변경 검토 파일 (선택적)

| 파일 | 변경 범위 | 영향도 |
|-----|----------|--------|
| `execution_agents/README.md` | 전체 문서 | 높음 (사용자 보류) |
| `tools/*.py` (7개) | Docstring 설명 | 중간 |

---

## 🎯 범용화 전략 제안

### Option A: 최소 변경 (실행 로직만)
- `todo_manager.py` + `cognitive_nodes.py`의 LLM 프롬프트만 변경
- Enum/주석은 유지
- **장점**: 빠른 적용, 최소 영향
- **단점**: 일관성 부족

### Option B: 중간 변경 (주석 포함)
- LLM 프롬프트 + 한글 주석 변경
- Enum 상수명은 유지
- **장점**: 코드 가독성 향상
- **단점**: 일부 PT 용어 잔존

### Option C: 완전 변경 (Enum 상수명까지)
- Enum 상수명 변경 (`FITNESS_ASSESSMENT` → `DATA_ASSESSMENT`)
- 모든 참조 위치 수정 필요
- **장점**: 완전 범용화
- **단점**: 높은 작업량, 테스트 필요

---

## 📋 다음 단계

1. ✅ **1단계 완료**: PT Manager → Specialist Agent (Author 필드)
2. ⏸️ **2단계 대기**: Agent 설명 범용화 (사용자 결정)
3. ⏸️ **3단계 보류**: README 전체 수정 (사용자 결정)

---

**작성자**: Claude Code
**작성일**: 2025-11-10
**상태**: 검토 대기 중
