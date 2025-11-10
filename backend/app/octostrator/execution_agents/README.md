# AI PT Manager - 7개 비즈니스 역할 기반 에이전트 매뉴얼

**프로젝트**: AI PTmanager - Beta v0.01
**작성일**: 2025-11-06
**버전**: 2.0 (7 Business Role Agents)

---

## 📋 목차

1. [개요](#개요)
2. [전체 아키텍처](#전체-아키텍처)
3. [7개 에이전트 상세](#7개-에이전트-상세)
4. [Supervisor 통합 가이드](#supervisor-통합-가이드) ⭐
5. [데이터베이스 스키마](#데이터베이스-스키마)
6. [Mock 데이터 및 테스트](#mock-데이터-및-테스트)
7. [API 사용 가이드](#api-사용-가이드)
8. [문제 해결](#문제-해결)

---

## 개요

### 시스템 특징

이 시스템은 **피트니스 센터 운영을 위한 7개 비즈니스 역할 기반 AI 에이전트**로 구성되어 있습니다.

**총 62개 Tools**가 7개 도메인으로 분산되어 있으며, 각 에이전트는 특정 비즈니스 역할을 수행합니다.

### 7개 에이전트 목록

| 에이전트 | 역할 | Tools 개수 | 주요 기능 |
|---------|------|-----------|----------|
| **Frontdesk** | 접수/상담 | 12 | 리드 관리, 문의 응답, 상담 예약 |
| **Assessor** | 체성분/자세 분석 | 7 | InBody 분석, 자세 평가, 피트니스 점수 |
| **Program Designer** | 운동/식단 설계 | 10 | 프로그램 생성, 템플릿 관리, 운동 검색 |
| **Manager** | 회원 관리 | 8 | 출석 관리, 이탈 위험 분석, 재등록 관리 |
| **Marketing** | 마케팅/이벤트 | 9 | SNS 관리, 이벤트 운영, 참여도 분석 |
| **Owner Assistant** | 경영 지원 | 8 | 매출 분석, 트레이너 성과, 비즈니스 지표 |
| **Trainer Education** | 트레이너 교육 | 8 | 스킬 평가, 교육 계획, 성장 관리 |

### 기술 스택

- **LangGraph 1.0**: 멀티 에이전트 오케스트레이션
- **SQLAlchemy**: ORM (11개 새 테이블)
- **Async/Await**: 모든 Tool이 비동기 구조
- **SQLite**: 로컬 개발용 DB
- **Dict-based Registry**: Tool 중앙 관리

---

## 전체 아키텍처

### 계층 구조

```
Supervisor (Orchestration Layer)
    │
    ├─── Router Node (Intent Classification & Agent Selection)
    │
    ├─── Agent Executor Nodes (7개 에이전트 실행)
    │     │
    │     ├─── Frontdesk Agent ───> Frontdesk Tools (12개)
    │     ├─── Assessor Agent ───> Assessor Tools (7개)
    │     ├─── Program Designer Agent ───> Program Designer Tools (10개)
    │     ├─── Manager Agent ───> Manager Tools (8개)
    │     ├─── Marketing Agent ───> Marketing Tools (9개)
    │     ├─── Owner Assistant Agent ───> Owner Assistant Tools (8개)
    │     └─── Trainer Education Agent ───> Trainer Education Tools (8개)
    │
    └─── Response Node (결과 취합 및 응답 생성)
```

### 디렉토리 구조

```
backend/app/octostrator/
├── agents/                    # 에이전트 디렉토리
│   ├── __init__.py           # 에이전트 레지스트리
│   ├── README.md             # 이 문서
│   ├── frontdesk/            # Frontdesk Agent
│   ├── assessor/             # Assessor Agent
│   ├── program_designer/     # Program Designer Agent
│   ├── manager/              # Manager Agent
│   ├── marketing/            # Marketing Agent
│   ├── owner_assistant/      # Owner Assistant Agent
│   └── trainer_education/    # Trainer Education Agent
│
├── tools/                     # Tools 디렉토리
│   ├── __init__.py           # Tools Registry (62개 등록)
│   ├── frontdesk_tools.py    # 12 tools
│   ├── assessor_tools.py     # 7 tools
│   ├── program_designer_tools.py  # 10 tools
│   ├── manager_tools.py      # 8 tools
│   ├── marketing_tools.py    # 9 tools
│   ├── owner_assistant_tools.py   # 8 tools
│   └── trainer_education_tools.py # 8 tools
│
├── supervisor/               # Supervisor
│   ├── nodes/
│   │   ├── router.py        # Agent 선택 라우터
│   │   └── executor.py      # Agent 실행기
│   └── graph.py             # Supervisor Graph
│
└── states/                   # State 정의
    └── supervisor_state.py   # SupervisorState TypedDict
```

### 데이터 흐름

1. **User Input** → Supervisor
2. **Router Node** → Intent 분석 및 Agent 선택
3. **Executor Node** → 선택된 Agent의 Tools 실행
4. **Database** ↔ Tools (SQLite CRUD)
5. **Response Node** → 결과 취합 및 응답 생성
6. **User Output** ← Supervisor

---

## 7개 에이전트 상세

### 1. Frontdesk Agent

**역할**: 리드 관리, 고객 문의 응답, 상담 예약

**Tools (12개)**:

| Tool 이름 | 기능 | 주요 파라미터 |
|----------|------|--------------|
| `create_lead` | 신규 리드 생성 | name, phone, email, source, interest |
| `get_lead` | 리드 정보 조회 | lead_id |
| `get_all_leads` | 전체 리드 목록 | status, limit |
| `update_lead_status` | 리드 상태 변경 | lead_id, new_status, notes |
| `calculate_lead_score` | 리드 점수 계산 | lead_id |
| `create_inquiry` | 문의 생성 | lead_id, inquiry_text, inquiry_type |
| `get_inquiries` | 문의 내역 조회 | lead_id, limit |
| `get_available_slots` | 상담 가능 시간 조회 | date, duration_minutes |
| `create_appointment` | 상담 예약 생성 | lead_id, appointment_date, appointment_type |
| `update_appointment_status` | 예약 상태 변경 | appointment_id, new_status |
| `send_notification` | 알림 발송 | user_id, notification_type, message |
| `classify_inquiry_intent` | 문의 의도 분류 | inquiry_text |

**데이터베이스 테이블**:
- `leads`: 리드 정보
- `inquiries`: 문의 내역
- `appointments`: 상담 예약

**사용 예시**:
```python
from backend.app.octostrator.tools import create_lead, get_inquiries

# 신규 리드 생성
result = await create_lead(
    name="김철수",
    phone="010-1234-5678",
    email="chulsoo@example.com",
    source="website",
    interest="weight_loss"
)

# 문의 내역 조회
inquiries = await get_inquiries(lead_id=1, limit=10)
```

---

### 2. Assessor Agent

**역할**: 체성분 분석, 자세 평가, 피트니스 점수 계산

**Tools (7개)**:

| Tool 이름 | 기능 | 주요 파라미터 |
|----------|------|--------------|
| `save_inbody_data` | InBody 데이터 저장 | user_id, weight, muscle_mass, body_fat_percentage, 기타 |
| `get_inbody_data` | InBody 기록 조회 | user_id, limit |
| `analyze_inbody_trend` | InBody 트렌드 분석 | user_id, days |
| `save_posture_analysis` | 자세 분석 저장 | user_id, front_image_url, issues, recommendations |
| `get_posture_analysis` | 자세 분석 조회 | user_id |
| `get_member_assessment_summary` | 회원 평가 요약 | user_id |
| `calculate_fitness_score` | 피트니스 점수 계산 | user_id |

**데이터베이스 테이블**:
- `inbody_data`: InBody 측정 데이터
- `posture_analysis`: 자세 분석

**사용 예시**:
```python
from backend.app.octostrator.tools import save_inbody_data, analyze_inbody_trend

# InBody 데이터 저장
result = await save_inbody_data(
    user_id=1,
    weight=75.5,
    muscle_mass=32.5,
    body_fat_percentage=20.1,
    bmr=1650
)

# 30일 트렌드 분석
trend = await analyze_inbody_trend(user_id=1, days=30)
```

---

### 3. Program Designer Agent

**역할**: 운동/식단 프로그램 설계 및 맞춤화

**Tools (10개)**:

| Tool 이름 | 기능 | 주요 파라미터 |
|----------|------|--------------|
| `create_program` | 프로그램 생성 | user_id, program_type, goal, duration_weeks, workout_plan, diet_plan |
| `get_program` | 프로그램 조회 | program_id |
| `get_user_programs` | 회원 프로그램 목록 | user_id, status |
| `update_program_status` | 프로그램 상태 변경 | program_id, new_status |
| `get_workout_templates` | 운동 템플릿 조회 | goal, level |
| `get_diet_templates` | 식단 템플릿 조회 | goal, calories_range |
| `customize_program` | 프로그램 맞춤화 | program_id, customizations |
| `search_exercises` | 운동 검색 | muscle_group, difficulty, equipment |
| `get_exercise` | 운동 상세 정보 | exercise_id |
| `get_program_summary` | 프로그램 요약 | user_id |

**데이터베이스 테이블**:
- `programs`: 운동/식단 프로그램
- `exercise_db`: 운동 데이터베이스

**사용 예시**:
```python
from backend.app.octostrator.tools import create_program, search_exercises

# 프로그램 생성
program = await create_program(
    user_id=1,
    program_type="combined",
    goal="muscle_gain",
    duration_weeks=12,
    workout_plan={"frequency": "3x per week"},
    diet_plan={"calories": 2500}
)

# 하체 운동 검색
exercises = await search_exercises(muscle_group="legs", difficulty="intermediate")
```

---

### 4. Manager Agent

**역할**: 회원 출석 관리, 이탈 위험 분석, 재등록 관리

**Tools (8개)**:

| Tool 이름 | 기능 | 주요 파라미터 |
|----------|------|--------------|
| `record_attendance` | 출석 체크인 | user_id, workout_type, trainer_id |
| `checkout_attendance` | 출석 체크아웃 | attendance_id, notes |
| `get_attendance_records` | 출석 기록 조회 | user_id, start_date, end_date |
| `calculate_attendance_rate` | 출석률 계산 | user_id, days |
| `calculate_churn_risk` | 이탈 위험도 계산 | user_id |
| `get_churn_risks` | 이탈 위험 회원 목록 | risk_level, limit |
| `get_renewal_candidates` | 재등록 대상 조회 | days_before_expiry |
| `update_churn_risk_actions` | 이탈 방지 조치 업데이트 | user_id, actions |

**데이터베이스 테이블**:
- `attendance`: 출석 기록
- `churn_risks`: 이탈 위험도

**사용 예시**:
```python
from backend.app.octostrator.tools import record_attendance, calculate_churn_risk

# 출석 체크인
attendance = await record_attendance(
    user_id=1,
    workout_type="pt_session",
    trainer_id=100
)

# 이탈 위험도 분석
risk = await calculate_churn_risk(user_id=2)
```

---

### 5. Marketing Agent

**역할**: SNS 마케팅, 이벤트 운영, 참여도 분석

**Tools (9개)**:

| Tool 이름 | 기능 | 주요 파라미터 |
|----------|------|--------------|
| `create_social_post` | SNS 게시물 생성 | platform, content, media_urls, hashtags |
| `schedule_post` | 게시물 스케줄링 | post_id, scheduled_time |
| `publish_post` | 게시물 발행 | post_id |
| `get_posts` | 게시물 목록 조회 | platform, status, limit |
| `update_post_engagement` | 참여도 업데이트 | post_id, likes, comments, shares |
| `create_event` | 이벤트 생성 | title, description, event_type, start_date, end_date |
| `get_events` | 이벤트 목록 조회 | status, limit |
| `update_event_status` | 이벤트 상태 변경 | event_id, new_status |
| `add_event_participant` | 이벤트 참여자 추가 | event_id, user_id |

**데이터베이스 테이블**:
- `social_media_posts`: SNS 게시물
- `events`: 이벤트

**사용 예시**:
```python
from backend.app.octostrator.tools import create_social_post, create_event

# SNS 게시물 생성
post = await create_social_post(
    platform="instagram",
    content="PT 성공 사례! 3개월 만에 체지방 5% 감소!",
    hashtags="#다이어트 #PT"
)

# 이벤트 생성
event = await create_event(
    title="신규 회원 환영 이벤트",
    description="첫 달 20% 할인",
    event_type="promotion",
    start_date=datetime.now(),
    end_date=datetime.now() + timedelta(days=30)
)
```

---

### 6. Owner Assistant Agent

**역할**: 매출 분석, 트레이너 성과 관리, 비즈니스 지표 제공

**Tools (8개)**:

| Tool 이름 | 기능 | 주요 파라미터 |
|----------|------|--------------|
| `record_revenue` | 매출 기록 | date, revenue_type, amount, user_id, trainer_id, payment_method |
| `get_revenue_records` | 매출 기록 조회 | start_date, end_date, revenue_type, limit |
| `get_revenue_analysis` | 매출 분석 | start_date, end_date |
| `calculate_monthly_revenue` | 월별 매출 계산 | year, month |
| `get_trainer_performance` | 트레이너 성과 조회 | trainer_id, start_date, end_date |
| `get_all_trainers_performance` | 전체 트레이너 비교 | start_date, end_date |
| `calculate_program_roi` | 프로그램 ROI 계산 | program_type, start_date, end_date |
| `get_key_business_metrics` | 핵심 비즈니스 지표 | days |

**데이터베이스 테이블**:
- `revenue`: 매출 데이터

**사용 예시**:
```python
from backend.app.octostrator.tools import record_revenue, get_revenue_analysis

# 매출 기록
revenue = await record_revenue(
    date=datetime.now(),
    revenue_type="pt_session",
    amount=80000,
    user_id=1,
    trainer_id=100,
    payment_method="card"
)

# 30일 매출 분석
analysis = await get_revenue_analysis(
    start_date=datetime.now() - timedelta(days=30),
    end_date=datetime.now()
)
```

---

### 7. Trainer Education Agent

**역할**: 트레이너 스킬 평가, 교육 계획, 성장 관리

**Tools (8개)**:

| Tool 이름 | 기능 | 주요 파라미터 |
|----------|------|--------------|
| `record_trainer_skill` | 트레이너 스킬 기록 | trainer_id, skill_category, skill_name, proficiency_level |
| `get_trainer_skills` | 트레이너 스킬 조회 | trainer_id, limit |
| `assess_skill_level` | 스킬 레벨 평가 | trainer_id, skill_name, new_level, assessor |
| `get_skill_gap_analysis` | 스킬 갭 분석 | trainer_id, target_level |
| `create_development_plan` | 교육 계획 생성 | trainer_id, target_skills |
| `get_training_modules` | 교육 모듈 조회 | category, difficulty |
| `track_training_progress` | 교육 진행 추적 | trainer_id, module_id |
| `get_all_trainers_overview` | 전체 트레이너 현황 | - |

**데이터베이스 테이블**:
- `trainer_skills`: 트레이너 스킬

**사용 예시**:
```python
from backend.app.octostrator.tools import record_trainer_skill, get_skill_gap_analysis

# 스킬 기록
skill = await record_trainer_skill(
    trainer_id=100,
    skill_category="technique",
    skill_name="스쿼트 지도",
    proficiency_level=5
)

# 스킬 갭 분석
gap = await get_skill_gap_analysis(trainer_id=100, target_level=4)
```

---

## Supervisor 통합 가이드

### 1. Agent 등록

**위치**: `backend/app/octostrator/agents/__init__.py`

```python
"""Agent Registry"""
from typing import Dict, Any, Callable

# Agent 클래스 import
from .frontdesk.agent import FrontdeskAgent
from .assessor.agent import AssessorAgent
from .program_designer.agent import ProgramDesignerAgent
from .manager.agent import ManagerAgent
from .marketing.agent import MarketingAgent
from .owner_assistant.agent import OwnerAssistantAgent
from .trainer_education.agent import TrainerEducationAgent

# Agent Registry
AGENTS: Dict[str, Any] = {
    "frontdesk": FrontdeskAgent,
    "assessor": AssessorAgent,
    "program_designer": ProgramDesignerAgent,
    "manager": ManagerAgent,
    "marketing": MarketingAgent,
    "owner_assistant": OwnerAssistantAgent,
    "trainer_education": TrainerEducationAgent,
}

def get_agent(agent_name: str):
    """Agent 인스턴스 가져오기"""
    if agent_name not in AGENTS:
        raise ValueError(f"Agent '{agent_name}' not found")
    return AGENTS[agent_name]()
```

---

### 2. Supervisor State 정의

**위치**: `backend/app/octostrator/states/supervisor_state.py`

```python
"""Supervisor State 정의"""
from typing import TypedDict, List, Annotated, Optional
from operator import add

class SupervisorState(TypedDict):
    """Supervisor State Schema"""
    # 기본 필드
    user_id: int
    query: str
    intent: Optional[str]  # 분류된 의도
    selected_agent: Optional[str]  # 선택된 에이전트

    # 누적 필드
    messages: Annotated[List[str], add]
    tool_results: Annotated[List[dict], add]

    # 결과 필드
    response: Optional[str]
    error: Optional[str]
    metadata: Optional[dict]
```

---

### 3. Router Node 구현

**위치**: `backend/app/octostrator/supervisor/nodes/router.py`

```python
"""Router Node - Intent 분석 및 Agent 선택"""
from backend.app.octostrator.states.supervisor_state import SupervisorState
from typing import Dict

# Intent → Agent 매핑
INTENT_TO_AGENT: Dict[str, str] = {
    # Frontdesk
    "lead_inquiry": "frontdesk",
    "appointment_booking": "frontdesk",
    "general_inquiry": "frontdesk",

    # Assessor
    "body_analysis": "assessor",
    "posture_check": "assessor",
    "fitness_assessment": "assessor",

    # Program Designer
    "create_workout": "program_designer",
    "diet_plan": "program_designer",
    "exercise_search": "program_designer",

    # Manager
    "attendance": "manager",
    "member_retention": "manager",
    "churn_analysis": "manager",

    # Marketing
    "social_media": "marketing",
    "event_management": "marketing",
    "promotion": "marketing",

    # Owner Assistant
    "revenue_analysis": "owner_assistant",
    "business_metrics": "owner_assistant",
    "trainer_performance": "owner_assistant",

    # Trainer Education
    "trainer_assessment": "trainer_education",
    "skill_development": "trainer_education",
    "training_plan": "trainer_education",
}

async def router_node(state: SupervisorState) -> SupervisorState:
    """
    사용자 쿼리를 분석하여 적절한 Agent 선택

    Args:
        state: Supervisor State

    Returns:
        업데이트된 State (selected_agent 추가)
    """
    query = state["query"]

    # LLM을 사용한 Intent 분류 (실제 구현)
    # intent = await classify_intent_with_llm(query)

    # 간단한 키워드 기반 분류 (예시)
    intent = classify_intent_simple(query)

    # Intent에 따른 Agent 선택
    selected_agent = INTENT_TO_AGENT.get(intent, "frontdesk")  # 기본값: frontdesk

    state["intent"] = intent
    state["selected_agent"] = selected_agent
    state["messages"].append(f"[Router] Intent: {intent}, Agent: {selected_agent}")

    return state

def classify_intent_simple(query: str) -> str:
    """간단한 키워드 기반 Intent 분류"""
    query_lower = query.lower()

    # Frontdesk
    if any(word in query_lower for word in ["상담", "예약", "문의", "등록"]):
        return "appointment_booking"

    # Assessor
    if any(word in query_lower for word in ["인바디", "체성분", "자세", "측정"]):
        return "body_analysis"

    # Program Designer
    if any(word in query_lower for word in ["운동", "프로그램", "식단", "다이어트"]):
        return "create_workout"

    # Manager
    if any(word in query_lower for word in ["출석", "이탈", "재등록"]):
        return "attendance"

    # Marketing
    if any(word in query_lower for word in ["sns", "이벤트", "홍보", "마케팅"]):
        return "social_media"

    # Owner Assistant
    if any(word in query_lower for word in ["매출", "수익", "성과", "분석"]):
        return "revenue_analysis"

    # Trainer Education
    if any(word in query_lower for word in ["트레이너", "교육", "스킬", "평가"]):
        return "trainer_assessment"

    return "general_inquiry"
```

---

### 4. Executor Node 구현

**위치**: `backend/app/octostrator/supervisor/nodes/executor.py`

```python
"""Executor Node - Agent 실행"""
from backend.app.octostrator.states.supervisor_state import SupervisorState
from backend.app.octostrator.agents import get_agent
from backend.app.octostrator.tools import TOOLS

async def executor_node(state: SupervisorState) -> SupervisorState:
    """
    선택된 Agent 실행

    Args:
        state: Supervisor State

    Returns:
        업데이트된 State (tool_results 추가)
    """
    selected_agent = state["selected_agent"]
    user_id = state["user_id"]
    query = state["query"]

    try:
        # Agent 가져오기
        agent = get_agent(selected_agent)

        # Agent 실행
        # Option 1: Agent가 자체 Graph를 가지고 있는 경우
        # result = await agent.invoke({"user_id": user_id, "query": query})

        # Option 2: 직접 Tool 호출 (현재 구조)
        result = await execute_agent_tools(selected_agent, user_id, query)

        state["tool_results"].append(result)
        state["messages"].append(f"[Executor] Agent '{selected_agent}' executed successfully")

    except Exception as e:
        state["error"] = f"Agent execution failed: {str(e)}"
        state["messages"].append(f"[Executor] Error: {str(e)}")

    return state

async def execute_agent_tools(agent_name: str, user_id: int, query: str) -> dict:
    """
    Agent별 Tool 실행 로직

    Args:
        agent_name: Agent 이름
        user_id: 사용자 ID
        query: 사용자 쿼리

    Returns:
        Tool 실행 결과
    """
    # Agent별 처리 로직
    if agent_name == "frontdesk":
        # 예시: 리드 생성 또는 문의 응답
        from backend.app.octostrator.tools import get_all_leads, classify_inquiry_intent

        intent_result = await classify_inquiry_intent(query)
        leads = await get_all_leads(status="new", limit=5)

        return {
            "agent": agent_name,
            "intent": intent_result,
            "data": leads
        }

    elif agent_name == "assessor":
        # 예시: InBody 데이터 조회
        from backend.app.octostrator.tools import get_inbody_data, calculate_fitness_score

        inbody = await get_inbody_data(user_id=user_id, limit=1)
        score = await calculate_fitness_score(user_id=user_id)

        return {
            "agent": agent_name,
            "inbody": inbody,
            "fitness_score": score
        }

    elif agent_name == "program_designer":
        # 예시: 프로그램 조회
        from backend.app.octostrator.tools import get_user_programs, get_workout_templates

        programs = await get_user_programs(user_id=user_id)
        templates = await get_workout_templates()

        return {
            "agent": agent_name,
            "programs": programs,
            "templates": templates
        }

    # ... 나머지 Agent 처리 로직

    return {"agent": agent_name, "message": "Agent executed"}
```

---

### 5. Supervisor Graph 구성

**위치**: `backend/app/octostrator/supervisor/graph.py`

```python
"""Supervisor Graph"""
from langgraph.graph import StateGraph, END
from backend.app.octostrator.states.supervisor_state import SupervisorState
from backend.app.octostrator.supervisor.nodes.router import router_node
from backend.app.octostrator.supervisor.nodes.executor import executor_node

def create_supervisor_graph():
    """Supervisor Graph 생성"""

    # StateGraph 생성
    graph = StateGraph(SupervisorState)

    # 노드 추가
    graph.add_node("router", router_node)
    graph.add_node("executor", executor_node)
    graph.add_node("response", response_node)

    # 엣지 추가
    graph.set_entry_point("router")
    graph.add_edge("router", "executor")
    graph.add_edge("executor", "response")
    graph.add_edge("response", END)

    # Graph 컴파일
    compiled_graph = graph.compile()

    return compiled_graph

async def response_node(state: SupervisorState) -> SupervisorState:
    """응답 생성 노드"""
    tool_results = state.get("tool_results", [])

    # Tool 결과를 바탕으로 응답 생성
    if tool_results:
        latest_result = tool_results[-1]
        state["response"] = f"Agent '{latest_result.get('agent')}' 실행 완료. 결과: {latest_result}"
    else:
        state["response"] = "처리 중 오류가 발생했습니다."

    return state
```

---

### 6. Supervisor 실행 예시

**위치**: `backend/app/octostrator/test_supervisor.py`

```python
"""Supervisor 테스트"""
import asyncio
from backend.app.octostrator.supervisor.graph import create_supervisor_graph

async def test_supervisor():
    """Supervisor 실행 테스트"""

    # Graph 생성
    graph = create_supervisor_graph()

    # 테스트 케이스 1: Frontdesk Agent
    print("\n=== Test 1: Frontdesk Agent ===")
    result1 = await graph.ainvoke({
        "user_id": 1,
        "query": "PT 상담 예약하고 싶어요",
        "messages": [],
        "tool_results": []
    })
    print(f"Response: {result1['response']}")

    # 테스트 케이스 2: Assessor Agent
    print("\n=== Test 2: Assessor Agent ===")
    result2 = await graph.ainvoke({
        "user_id": 1,
        "query": "인바디 측정 결과 보여줘",
        "messages": [],
        "tool_results": []
    })
    print(f"Response: {result2['response']}")

    # 테스트 케이스 3: Program Designer Agent
    print("\n=== Test 3: Program Designer Agent ===")
    result3 = await graph.ainvoke({
        "user_id": 1,
        "query": "근육 증가 운동 프로그램 만들어줘",
        "messages": [],
        "tool_results": []
    })
    print(f"Response: {result3['response']}")

if __name__ == "__main__":
    asyncio.run(test_supervisor())
```

---

### 7. Tool 직접 호출 방식 (현재 구조)

현재 구조는 **Agent 클래스 없이 Tools만 존재**합니다. Supervisor에서 직접 Tools를 호출하는 방식입니다.

```python
"""Tool 직접 호출 예시"""
from backend.app.octostrator.tools import (
    get_all_leads,
    get_inbody_data,
    get_user_programs,
    # ... 필요한 Tool import
)

async def execute_frontdesk_agent(user_id: int, query: str):
    """Frontdesk Agent 실행 (Tool 직접 호출)"""

    # Intent 분류
    intent = classify_intent(query)

    # Intent에 따른 Tool 선택 및 실행
    if intent == "lead_inquiry":
        result = await get_all_leads(status="new", limit=5)
    elif intent == "appointment_booking":
        result = await create_appointment(...)
    # ...

    return result
```

---

## 데이터베이스 스키마

### 11개 새 테이블

| 테이블 | 에이전트 | 주요 컬럼 |
|-------|---------|----------|
| `leads` | Frontdesk | name, phone, email, source, interest, score, status |
| `inquiries` | Frontdesk | lead_id, inquiry_text, response_text, inquiry_type |
| `appointments` | Frontdesk | lead_id, appointment_date, appointment_type, status |
| `inbody_data` | Assessor | user_id, weight, muscle_mass, body_fat_percentage, bmr |
| `posture_analysis` | Assessor | user_id, shoulder_alignment, hip_alignment, spine_curvature, issues |
| `programs` | Program Designer | user_id, program_type, goal, duration_weeks, workout_plan, diet_plan |
| `attendance` | Manager | user_id, check_in_time, check_out_time, workout_type, trainer_id |
| `churn_risks` | Manager | user_id, risk_score, risk_level, factors, recommended_actions |
| `social_media_posts` | Marketing | platform, content, hashtags, scheduled_time, engagement_metrics |
| `events` | Marketing | title, event_type, start_date, end_date, budget, revenue, participants |
| `revenue` | Owner Assistant | date, revenue_type, amount, user_id, trainer_id, payment_method |
| `trainer_skills` | Trainer Education | trainer_id, skill_category, skill_name, proficiency_level, improvement_plan |

### ER Diagram

```
User (기존)
  │
  ├──< InBodyData (Assessor)
  ├──< PostureAnalysis (Assessor)
  ├──< Program (Program Designer)
  ├──< Attendance (Manager)
  ├──< ChurnRisk (Manager)
  ├──< Revenue (Owner Assistant)
  └──< TrainerSkill (Trainer Education)

Lead (Frontdesk)
  │
  ├──< Inquiry (Frontdesk)
  └──< Appointment (Frontdesk)

(독립 테이블)
- SocialMediaPost (Marketing)
- Event (Marketing)
```

---

## Mock 데이터 및 테스트

### Mock 데이터 생성

**위치**: `backend/database/create_all_mocks.py`

```bash
# Mock 데이터 생성
cd backend/database
python create_all_mocks.py
```

생성되는 Mock 데이터:
- Leads: 4개
- Inquiries: 3개
- Appointments: 2개
- InBody Data: 3개
- Posture Analysis: 1개
- Programs: 1개
- Attendance: 3개
- Churn Risks: 1개
- Social Posts: 2개
- Events: 1개
- Revenue: 3개
- Trainer Skills: 3개

---

### 테스트 실행

**위치**: `backend/tests/test_agent_tools.py`

```bash
# 전체 테스트 실행
cd backend/tests
python test_agent_tools.py
```

테스트 내용:
- 7개 에이전트별 Tool 테스트
- 62개 Tool 실행 검증
- Mock 데이터 기반 통합 테스트

---

## API 사용 가이드

### Tool 가져오기

```python
# 방법 1: 직접 import
from backend.app.octostrator.tools import create_lead, get_inbody_data

# 방법 2: Registry에서 가져오기
from backend.app.octostrator.tools import get_tool

create_lead_func = get_tool("create_lead")
```

### Tool 목록 조회

```python
from backend.app.octostrator.tools import list_tools, list_tools_by_domain

# 전체 Tool 목록
all_tools = list_tools()
print(f"Total tools: {len(all_tools)}")

# 도메인별 Tool 목록
frontdesk_tools = list_tools_by_domain("frontdesk")
print(f"Frontdesk tools: {frontdesk_tools}")
```

### Tool 실행

```python
import asyncio
from backend.app.octostrator.tools import create_lead

async def main():
    result = await create_lead(
        name="김철수",
        phone="010-1234-5678",
        email="test@example.com",
        source="website",
        interest="weight_loss"
    )
    print(result)

asyncio.run(main())
```

---

## 문제 해결

### FAQ

**Q1: Tool이 실행되지 않습니다.**

```python
# 해결책 1: async 함수로 실행 확인
import asyncio
result = asyncio.run(your_tool(...))

# 해결책 2: DB 초기화 확인
from backend.database.relation_db.session import init_db
init_db()
```

**Q2: Agent를 Supervisor에 어떻게 연결하나요?**

→ [Supervisor 통합 가이드](#supervisor-통합-가이드) 섹션 참조

**Q3: Mock 데이터가 생성되지 않습니다.**

```bash
# DB 파일 삭제 후 재생성
rm backend/database/relation_db/fitness.db
python backend/database/create_all_mocks.py
```

---

## 참고 자료

### 파일 위치

- **Tools**: [backend/app/octostrator/tools/](../tools/)
- **Agent 클래스**: [backend/app/octostrator/agents/](.)
- **테스트**: [backend/tests/test_agent_tools.py](../../../tests/test_agent_tools.py)
- **Mock 데이터**: [backend/database/](../../../database/)
- **DB 모델**: [backend/database/relation_db/models.py](../../../database/relation_db/models.py)

### 관련 문서

- LangGraph: https://langchain-ai.github.io/langgraph/
- SQLAlchemy: https://docs.sqlalchemy.org/

---

## 변경 이력

| 날짜 | 버전 | 변경 내용 |
|------|------|----------|
| 2025-11-06 | 2.0 | 7개 비즈니스 역할 기반 에이전트 구조로 재설계 |
| 2025-11-06 | 2.1 | Supervisor 통합 가이드 추가 |

---

**문의**: 프로젝트 이슈 트래커

**작성자**: AI Development Team
