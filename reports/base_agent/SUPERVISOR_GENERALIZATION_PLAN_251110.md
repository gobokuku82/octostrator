# Supervisor 범용화 계획서

**작성일**: 2025-11-10
**목적**: PT 특화 Supervisor를 실행 에이전트 미정의 범용 기본 틀로 전환
**상태**: 계획 단계

---

## 📋 Executive Summary

현재 Supervisor 계층이 PT 관련 특정 기능(frontdesk, assessor 등)에 맞춰져 있어, 실행 에이전트가 없거나 아직 기능이 결정되지 않은 초기 상태로 되돌려야 합니다.

**핵심 목표**:
- ✅ Supervisor 계층은 범용적으로 동작
- ✅ 실행 에이전트 구현을 기다리는 초기 상태
- ✅ 어떤 도메인(PT, 교육, 비즈니스 등)에도 적용 가능한 기본 틀

---

## 🔍 현재 상태 분석

### 1. Supervisor 계층 구조 (5개)

```
backend/app/octostrator/supervisors/
├── octostrator/          ✅ 범용 (메인 오케스트레이터)
├── cognitive/            ⚠️ 일부 PT 특화
├── todo/                 ⚠️ 일부 PT 특화
├── execute/              ⚠️ PT Agent 참조
└── response/             ✅ 범용
```

### 2. PT 특화 요소 식별

#### 🔴 High Priority (실행 로직에 영향)

##### **A. todo_manager.py** (Line 567-633)
**문제**: 7개 PT Agent가 하드코딩됨

```python
async def select_agent_for_task(step: dict, llm) -> str:
    """
    Available agents:
    - frontdesk_agent: 신규 리드 관리, 상담 예약, 문의 응대
    - assessor_agent: 체성분 분석, 자세 평가, 피트니스 점수
    - program_designer_agent: 운동/식단 프로그램 설계
    - manager_agent: 회원 출석 관리, 이탈 위험 분석
    - marketing_agent: SNS 마케팅, 이벤트 운영
    - owner_assistant_agent: 매출 분석, 트레이너 성과 관리
    - trainer_education_agent: 트레이너 교육 및 스킬 평가
    """

    prompt = f"""You are an AI agent router...

Available agents:
- frontdesk_agent: 신규 리드 관리, 상담 예약, 문의 응대, 고객 정보 수집
- assessor_agent: 체성분 분석(InBody), 자세 평가, 피트니스 점수 계산
... (7개 agent 설명)
"""

    valid_agents = [
        "frontdesk_agent",
        "assessor_agent",
        "program_designer_agent",
        "manager_agent",
        "marketing_agent",
        "owner_assistant_agent",
        "trainer_education_agent"
    ]
```

**영향**: Agent 선택 실패 → Fallback만 동작

---

##### **B. cognitive_nodes.py** (Line 97-116)
**문제**: Capability 설명이 PT 특화

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
"""
```

**영향**: PT 외 도메인에서 Capability 인식 실패

---

##### **C. cognitive_helpers.py** (Line 88-129)
**문제**: Capability → Agent 매핑이 하드코딩됨

```python
CAPABILITY_TO_AGENTS = {
    "customer_intake": ["frontdesk_agent"],
    "inquiry_handling": ["frontdesk_agent"],
    "appointment_scheduling": ["frontdesk_agent"],

    "fitness_assessment": ["assessor_agent"],
    "posture_analysis": ["assessor_agent"],

    "workout_design": ["program_designer_agent"],
    "diet_planning": ["program_designer_agent"],

    "attendance_tracking": ["manager_agent"],
    "churn_prevention": ["manager_agent"],

    "social_media": ["marketing_agent"],
    "event_management": ["marketing_agent"],

    "revenue_analysis": ["owner_assistant_agent"],
    "performance_tracking": ["owner_assistant_agent"],

    "trainer_development": ["trainer_education_agent"],
    "skill_assessment": ["trainer_education_agent"],
}
```

**영향**: 존재하지 않는 Agent 참조 → 라우팅 실패

---

#### 🟡 Medium Priority (Intent 분류)

##### **D. cognitive_helpers.py - IntentClassifier** (Line 24-33)
**문제**: Intent 패턴이 PT 도메인 특화

```python
INTENT_PATTERNS = {
    "diet_query": ["다이어트", "식단", "칼로리", "영양", "meal", "diet"],
    "workout_query": ["운동", "workout", "exercise", "training", "헬스"],
    "schedule_query": ["일정", "스케줄", "예약", "schedule", "appointment"],
    "member_report": ["보고서", "리포트", "report", "분석", "통계"],
    "coaching_search": ["코칭", "조언", "팁", "coaching", "advice"],
    "progress_comparison": ["진행", "비교", "progress", "compare", "변화"],
    "multi_step_task": ["만들어", "생성", "계획", "create", "plan", "build"]
}
```

**영향**: PT 외 도메인 의도 파악 어려움

---

#### 🟢 Low Priority (이미 범용적)

##### **E. capabilities.py**
**상태**: ✅ 이미 범용적 Capability 정의

```python
class Capability(Enum):
    # 범용 능력들
    TODO_MANAGEMENT = "todo_management"
    TASK_PRIORITIZATION = "task_prioritization"
    DATA_ANALYSIS = "data_analysis"
    REPORT_GENERATION = "report_generation"
    NOTIFICATION = "notification"
    USER_INTERACTION = "user_interaction"
    COACHING = "coaching"
    PLANNING = "planning"
    ORCHESTRATION = "orchestration"

    # PT 특화 (제거 대상)
    MEAL_PLANNING = "meal_planning"
    NUTRITION_ANALYSIS = "nutrition_analysis"
    EXERCISE_PLANNING = "exercise_planning"
    FITNESS_ASSESSMENT = "fitness_assessment"
```

**영향**: 없음 (Capability Enum은 확장 가능)

---

## 🎯 목표 상태 정의

### Vision: "Zero-Agent Ready" State

```
┌─────────────────────────────────────────────────┐
│         Supervisor 계층 (범용 기본 틀)            │
│                                                 │
│  ✅ Agent Registry: 빈 상태 (agent_registry = {})│
│  ✅ Capability Router: 동적 탐색                 │
│  ✅ Agent Selection: Registry 기반               │
│  ✅ Intent Classification: 범용 패턴             │
│                                                 │
│  → 어떤 Agent든 추가하면 자동으로 통합 가능      │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│      Execution Agents (비어 있음)                │
│                                                 │
│  📂 execution_agents/                           │
│      ├── base/          ✅ BaseAgent 클래스      │
│      └── README.md      ✅ 구현 가이드           │
│                                                 │
│  🔜 미래에 추가될 Agent:                         │
│      - PT Agent (frontdesk, assessor, ...)     │
│      - 교육 Agent (student, teacher, ...)       │
│      - 비즈니스 Agent (sales, support, ...)     │
└─────────────────────────────────────────────────┘
```

---

## 🔧 범용화 전략

### Strategy 1: Dynamic Agent Discovery (동적 탐색)

**As-Is (하드코딩)**:
```python
valid_agents = [
    "frontdesk_agent",
    "assessor_agent",
    # ... 7개 agent
]
```

**To-Be (동적 탐색)**:
```python
# Agent Registry에서 자동 탐색
available_agents = agent_registry.list_agents()

# 또는 Capability 기반
router = CapabilityBasedRouter(agent_registry)
agent = router.find_best_agent(required_capability)
```

---

### Strategy 2: Capability-Driven Architecture (능력 주도)

**As-Is (Agent 중심)**:
```python
CAPABILITY_TO_AGENTS = {
    "fitness_assessment": ["assessor_agent"],  # 고정
}
```

**To-Be (동적 매핑)**:
```python
# Agent가 자신의 Capability를 선언
class MyAgent(BaseAgent):
    def __init__(self):
        self.capabilities = [
            Capability.DATA_ANALYSIS,
            Capability.REPORT_GENERATION
        ]

# Router가 자동으로 매핑 생성
router.find_agents_for_capability("data_analysis")
# → MyAgent 자동 발견
```

---

### Strategy 3: Fallback to Generic Intent (범용 의도)

**As-Is (도메인 특화)**:
```python
INTENT_PATTERNS = {
    "diet_query": ["식단", "칼로리"],
    "workout_query": ["운동", "헬스"]
}
```

**To-Be (범용 의도)**:
```python
INTENT_PATTERNS = {
    "information_query": ["정보", "알려줘", "뭐", "what"],
    "action_request": ["만들어", "생성", "create", "build"],
    "analysis_request": ["분석", "비교", "통계", "analyze"],
    "schedule_request": ["일정", "예약", "schedule"],
    "multi_step_task": ["계획", "진행", "plan", "process"]
}
```

---

### Strategy 4: LLM-Based Flexible Routing (유연한 라우팅)

**As-Is (고정 프롬프트)**:
```python
prompt = """
Available agents:
- frontdesk_agent: 신규 리드 관리
- assessor_agent: 체성분 분석
(하드코딩된 7개)
"""
```

**To-Be (동적 프롬프트)**:
```python
# Registry에서 Agent 정보 가져오기
agents_info = []
for agent_id in agent_registry.list_agents():
    agent = agent_registry.get_agent_instance(agent_id)
    agents_info.append({
        "id": agent_id,
        "name": agent.agent_name,
        "description": agent.description,
        "capabilities": agent.capabilities
    })

# 동적 프롬프트 생성
agent_descriptions = "\n".join([
    f"- {a['id']}: {a['description']} (Capabilities: {a['capabilities']})"
    for a in agents_info
])

prompt = f"""
Available agents:
{agent_descriptions}

Task: {task_description}
Select the most appropriate agent.
"""
```

---

## 📝 단계별 실행 계획

### Phase 1: Agent Selection 동적화 (High Priority) ⭐⭐⭐

**파일**: `todo_manager.py`

**작업**:
1. ❌ 하드코딩된 7개 Agent 설명 제거
2. ✅ Agent Registry 기반 동적 Agent 목록 생성
3. ✅ LLM 프롬프트를 동적으로 생성
4. ✅ Fallback 동작 개선 (Agent 없을 때)

**Before**:
```python
valid_agents = [
    "frontdesk_agent",
    "assessor_agent",
    ...
]

if agent_name not in valid_agents:
    return "frontdesk_agent"  # 하드코딩 fallback
```

**After**:
```python
from backend.app.octostrator.execution_agents import agent_registry

# 동적 Agent 목록
available_agents = agent_registry.list_agents()

if not available_agents:
    logger.warning("[TodoManager] No agents registered, skipping agent selection")
    return None  # Agent 없음 명시

# LLM 프롬프트 동적 생성
agent_descriptions = []
for agent_id in available_agents:
    agent = agent_registry.get_agent_instance(agent_id)
    if agent:
        agent_descriptions.append(
            f"- {agent_id}: {agent.description}"
        )

prompt = f"""You are an AI agent router.

Available agents:
{chr(10).join(agent_descriptions) if agent_descriptions else "No agents available"}

Task: {task_description}

Return ONLY the agent name, or 'none' if no agents are available.
"""
```

---

### Phase 2: Capability 동적 매핑 (High Priority) ⭐⭐⭐

**파일**: `cognitive_helpers.py`

**작업**:
1. ❌ `CAPABILITY_TO_AGENTS` 딕셔너리 제거
2. ✅ `CapabilityBasedRouter` 사용 (capabilities.py)
3. ✅ Agent Registry 기반 동적 매핑

**Before**:
```python
CAPABILITY_TO_AGENTS = {
    "fitness_assessment": ["assessor_agent"],
    "workout_design": ["program_designer_agent"],
    # 하드코딩...
}

def get_agent_for_capability(cap):
    return CAPABILITY_TO_AGENTS.get(cap, [])
```

**After**:
```python
from backend.app.octostrator.execution_agents.base.capabilities import CapabilityBasedRouter
from backend.app.octostrator.execution_agents import agent_registry

# 동적 Router 생성
router = CapabilityBasedRouter(agent_registry)

def get_agent_for_capability(capability: str) -> Optional[str]:
    """동적으로 Capability에 맞는 Agent 찾기"""
    return router.find_best_agent(capability)

def get_all_agents_for_capability(capability: str) -> List[str]:
    """Capability를 가진 모든 Agent 조회"""
    return router.find_agents_for_capability(capability)
```

---

### Phase 3: Capability 설명 범용화 (Medium Priority) ⭐⭐

**파일**: `cognitive_nodes.py`

**작업**:
1. ❌ PT 특화 Capability 설명 제거
2. ✅ 범용적 설명으로 변경
3. ✅ 동적 Capability 목록 생성 (선택적)

**Before**:
```python
Available capabilities:
- fitness_assessment: 체성분(InBody) 분석
- workout_design: 운동 프로그램 설계
- diet_planning: 식단 계획
```

**After (Option A: 범용 설명)**:
```python
Available capabilities:
- data_analysis: 데이터 수집 및 분석
- report_generation: 보고서 작성
- task_management: 작업 관리 및 실행
- user_interaction: 사용자 상호작용
- planning: 계획 수립
```

**After (Option B: 동적 생성)**:
```python
from backend.app.octostrator.execution_agents.base.capabilities import Capability

# Enum에서 자동 생성
capabilities_list = [
    f"- {cap.value}: {cap.name.replace('_', ' ').title()}"
    for cap in Capability
]

prompt = f"""
Available capabilities:
{chr(10).join(capabilities_list)}

User message: {user_input}
"""
```

---

### Phase 4: Intent 패턴 범용화 (Medium Priority) ⭐⭐

**파일**: `cognitive_helpers.py - IntentClassifier`

**작업**:
1. ❌ PT 특화 Intent 제거 (diet_query, workout_query)
2. ✅ 범용 Intent 추가

**Before**:
```python
INTENT_PATTERNS = {
    "diet_query": ["식단", "칼로리", "meal", "diet"],
    "workout_query": ["운동", "workout", "exercise"],
    "member_report": ["보고서", "리포트"],
}
```

**After**:
```python
INTENT_PATTERNS = {
    # 범용 의도
    "information_query": ["정보", "알려줘", "뭐야", "what", "tell me"],
    "action_request": ["만들어", "생성", "추가", "create", "add", "build"],
    "analysis_request": ["분석", "비교", "통계", "리포트", "analyze", "compare"],
    "schedule_request": ["일정", "예약", "스케줄", "schedule", "book"],
    "delete_request": ["삭제", "제거", "delete", "remove"],
    "update_request": ["수정", "변경", "업데이트", "update", "modify"],
    "search_request": ["찾아", "검색", "조회", "search", "find", "lookup"],
    "multi_step_task": ["계획", "진행", "처리", "plan", "process", "handle"]
}
```

---

### Phase 5: Capability Enum 정리 (Low Priority) ⭐

**파일**: `capabilities.py`

**작업**:
1. ⚠️ PT 특화 Capability 유지 (삭제 X, 주석 처리)
2. ✅ 범용 Capability 우선 배치

**Before**:
```python
class Capability(Enum):
    # Health & Fitness (PT 특화)
    MEAL_PLANNING = "meal_planning"
    NUTRITION_ANALYSIS = "nutrition_analysis"
    EXERCISE_PLANNING = "exercise_planning"
    FITNESS_ASSESSMENT = "fitness_assessment"

    # 범용
    TODO_MANAGEMENT = "todo_management"
    DATA_ANALYSIS = "data_analysis"
```

**After**:
```python
class Capability(Enum):
    """시스템에서 사용하는 표준 능력

    범용 Capability를 우선 정의하고,
    도메인 특화 Capability는 필요시 추가합니다.
    """

    # ==========================================
    # Core Capabilities (범용)
    # ==========================================

    # Task & Planning
    TODO_MANAGEMENT = "todo_management"
    TASK_MANAGEMENT = "task_management"
    TASK_PRIORITIZATION = "task_prioritization"
    PLANNING = "planning"

    # Data & Analysis
    DATA_ANALYSIS = "data_analysis"
    REPORT_GENERATION = "report_generation"
    PROGRESS_TRACKING = "progress_tracking"

    # Communication
    NOTIFICATION = "notification"
    USER_INTERACTION = "user_interaction"
    MESSAGING = "messaging"

    # System
    ORCHESTRATION = "orchestration"
    MONITORING = "monitoring"
    ERROR_HANDLING = "error_handling"

    # ==========================================
    # Domain-Specific Capabilities (확장 예시)
    # ==========================================

    # Health & Fitness (PT 도메인)
    MEAL_PLANNING = "meal_planning"
    NUTRITION_ANALYSIS = "nutrition_analysis"
    EXERCISE_PLANNING = "exercise_planning"
    FITNESS_ASSESSMENT = "fitness_assessment"

    # Education (교육 도메인 예시)
    # STUDENT_ASSESSMENT = "student_assessment"
    # CURRICULUM_PLANNING = "curriculum_planning"

    # Business (비즈니스 도메인 예시)
    # SALES_ANALYSIS = "sales_analysis"
    # CUSTOMER_SUPPORT = "customer_support"

    # Custom (사용자 정의)
    CUSTOM = "custom"
```

---

## 🔍 검증 시나리오

### Scenario 1: Zero Agent (Agent 없음)

**상태**: Agent Registry 비어 있음

**기대 동작**:
```python
# Agent 선택 시
agent = select_agent_for_task(task)
# → None 반환 (fallback 없음)

# Capability 라우팅 시
agents = router.find_agents_for_capability("data_analysis")
# → [] 빈 리스트 반환

# 로그
logger.warning("[TodoManager] No agents registered")
```

---

### Scenario 2: Single Generic Agent (범용 Agent 1개)

**상태**:
```python
class GenericAgent(BaseAgent):
    def __init__(self):
        self.capabilities = [
            Capability.DATA_ANALYSIS,
            Capability.TASK_MANAGEMENT
        ]

agent_registry.register(GenericAgent, "generic_agent")
```

**기대 동작**:
```python
# Agent 선택 시
agent = select_agent_for_task("분석해줘")
# → "generic_agent" 반환

# Capability 라우팅
agents = router.find_agents_for_capability("data_analysis")
# → ["generic_agent"]
```

---

### Scenario 3: Multiple Domain Agents (여러 도메인)

**상태**:
```python
# PT Agent
class PTAgent(BaseAgent):
    capabilities = [Capability.FITNESS_ASSESSMENT]

# 교육 Agent
class EducationAgent(BaseAgent):
    capabilities = [Capability.DATA_ANALYSIS]

# 비즈니스 Agent
class BusinessAgent(BaseAgent):
    capabilities = [Capability.REPORT_GENERATION]
```

**기대 동작**:
```python
# Capability 커버리지 확인
coverage = router.get_capability_coverage()
# → {
#     "fitness_assessment": ["pt_agent"],
#     "data_analysis": ["education_agent"],
#     "report_generation": ["business_agent"]
# }

# Task 라우팅
agent = select_agent_for_task("체력 평가")
# → "pt_agent" (LLM이 fitness_assessment 매핑)

agent = select_agent_for_task("학생 성적 분석")
# → "education_agent" (LLM이 data_analysis 매핑)
```

---

## 📊 변경 영향도 분석

### High Risk (실행 로직 변경)

| 파일 | 변경 범위 | 영향도 | 테스트 필요 |
|-----|----------|--------|------------|
| `todo_manager.py` | Agent 선택 로직 | ⭐⭐⭐ 높음 | ✅ 필수 |
| `cognitive_helpers.py` | Capability 매핑 | ⭐⭐⭐ 높음 | ✅ 필수 |

### Medium Risk (프롬프트 변경)

| 파일 | 변경 범위 | 영향도 | 테스트 필요 |
|-----|----------|--------|------------|
| `cognitive_nodes.py` | Capability 설명 | ⭐⭐ 중간 | ✅ 권장 |
| `cognitive_helpers.py` | Intent 패턴 | ⭐⭐ 중간 | ⚠️ 선택 |

### Low Risk (정의만 변경)

| 파일 | 변경 범위 | 영향도 | 테스트 필요 |
|-----|----------|--------|------------|
| `capabilities.py` | Enum 순서 | ⭐ 낮음 | ❌ 불필요 |

---

## ✅ 성공 기준

### Criterion 1: Zero Hardcoded Agents
```bash
# 하드코딩된 Agent 이름 없음
grep -r "frontdesk_agent\|assessor_agent" backend/app/octostrator/supervisors
# → 0 results (주석 제외)
```

### Criterion 2: Dynamic Agent Discovery
```python
# Agent Registry가 비어 있어도 에러 없음
assert len(agent_registry.list_agents()) == 0
result = select_agent_for_task("test task")
assert result is None  # Fallback 대신 None
```

### Criterion 3: Capability-Based Routing
```python
# Capability Router 동작 확인
router = CapabilityBasedRouter(agent_registry)
agents = router.find_agents_for_capability("data_analysis")
assert isinstance(agents, list)
```

### Criterion 4: Generic Intent Classification
```python
# PT 특화 Intent 없음
assert "diet_query" not in IntentClassifier.INTENT_PATTERNS
assert "workout_query" not in IntentClassifier.INTENT_PATTERNS

# 범용 Intent 존재
assert "information_query" in IntentClassifier.INTENT_PATTERNS
assert "action_request" in IntentClassifier.INTENT_PATTERNS
```

---

## 🚀 실행 순서 요약

### Step 1: Phase 1 (Agent Selection 동적화)
```bash
1. todo_manager.py 수정
2. Agent Registry 기반 동적 목록 생성
3. 테스트: Agent 없을 때 / 있을 때
```

### Step 2: Phase 2 (Capability 매핑 동적화)
```bash
1. cognitive_helpers.py 수정
2. CAPABILITY_TO_AGENTS 제거
3. CapabilityBasedRouter 사용
4. 테스트: Capability 라우팅
```

### Step 3: Phase 3 (Capability 설명 범용화)
```bash
1. cognitive_nodes.py 수정
2. PT 특화 설명 제거
3. 범용 설명으로 변경
```

### Step 4: Phase 4 (Intent 범용화)
```bash
1. cognitive_helpers.py - IntentClassifier 수정
2. PT Intent 제거
3. 범용 Intent 추가
```

### Step 5: Phase 5 (Capability Enum 정리)
```bash
1. capabilities.py 정리
2. 범용 Capability 우선 배치
3. PT Capability는 주석과 함께 유지
```

---

## 📋 체크리스트

### Pre-Execution Checklist
- [ ] 현재 코드 백업 (Git commit)
- [ ] 기존 테스트 실행 (baseline)
- [ ] Agent Registry 구조 확인

### Phase 1 Checklist
- [ ] `select_agent_for_task` 동적화
- [ ] Agent 없을 때 동작 확인
- [ ] LLM 프롬프트 동적 생성 확인

### Phase 2 Checklist
- [ ] `CAPABILITY_TO_AGENTS` 제거
- [ ] `CapabilityBasedRouter` 적용
- [ ] Capability 라우팅 테스트

### Phase 3 Checklist
- [ ] Capability 설명 범용화
- [ ] LLM 프롬프트 검증

### Phase 4 Checklist
- [ ] Intent 패턴 범용화
- [ ] Intent 분류 테스트

### Phase 5 Checklist
- [ ] Capability Enum 재정렬
- [ ] 주석 추가

### Post-Execution Checklist
- [ ] 전체 테스트 실행
- [ ] Zero Agent 시나리오 확인
- [ ] 문서 업데이트 (README)

---

## 🎯 예상 결과

### Before (현재)
```
❌ PT Agent 7개 하드코딩
❌ Agent 없으면 "frontdesk_agent" fallback
❌ PT 외 도메인 사용 불가
❌ Capability 매핑 고정
```

### After (목표)
```
✅ Agent Registry 기반 동적 탐색
✅ Agent 없어도 에러 없이 동작
✅ 어떤 도메인 Agent든 추가 가능
✅ Capability 자동 매핑
✅ 범용 Intent 분류
```

---

## 📝 참고 문서

- [Agent Registry 구조](../execution_agents/base/agent_registry.py)
- [Capability 정의](../execution_agents/base/capabilities.py)
- [BaseAgent 추상 클래스](../execution_agents/base/base_agent.py)
- [Supervisor 아키텍처](../architecture/SUPERVISOR_ARCHITECTURE.md)

---

**작성자**: Claude Code
**검토 필요**: Phase별 실행 순서, 테스트 시나리오
**다음 단계**: 사용자 승인 → Phase 1 실행
