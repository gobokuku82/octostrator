# 시스템 아키텍처 메뉴얼

**작성일**: 2025-11-05
**버전**: 2.0
**시스템**: AI PT Manager - 3-Layer Architecture

---

## 목차

1. [시스템 개요](#1-시스템-개요)
2. [3-Layer 아키텍처](#2-3-layer-아키텍처)
3. [Layer 1: Planning Layer](#3-layer-1-planning-layer)
4. [Layer 2: Management Layer](#4-layer-2-management-layer)
5. [Layer 3: Execution Layer](#5-layer-3-execution-layer)
6. [데이터 흐름](#6-데이터-흐름)
7. [시스템 초기화](#7-시스템-초기화)
8. [에러 처리](#8-에러-처리)

---

## 1. 시스템 개요

### 1.1 핵심 특징

- **완전한 플러그인 아키텍처**: Agent를 런타임에 추가/삭제/교체 가능
- **LangGraph 기반**: 모든 컴포넌트가 StateGraph로 구현
- **Checkpoint 지원**: PostgreSQL 기반 상태 저장 및 복원
- **HITL Integration**: Human-in-the-Loop 워크플로우 내장
- **병렬 실행**: 의존성 기반 자동 병렬화

### 1.2 시스템 구성

```
┌─────────────────────────────────────────┐
│         Main Orchestrator               │
│  (전체 시스템 조율 및 관리)              │
└────────────────┬───────────────────────┘
                 │
    ┌────────────┼────────────┐
    │            │            │
    ▼            ▼            ▼
┌─────────┐ ┌─────────┐ ┌──────────┐
│Cognitive│ │  TODO   │ │ Execute  │
│Supervisor│ │ Agent   │ │Supervisor│
└─────────┘ └─────────┘ └──────────┘
                              │
                     ┌────────┼────────┐
                     │        │        │
                     ▼        ▼        ▼
                [Domain Agents Pool]
```

### 1.3 주요 컴포넌트

| 컴포넌트 | 역할 | 파일 위치 |
|---------|------|-----------|
| **Main Orchestrator** | 전체 시스템 조율 | `main_orchestrator.py` |
| **Cognitive Supervisor** | 계획 수립 | `supervisor/cognitive_supervisor.py` |
| **TodoAgent** | TODO 관리 및 HITL | `agents/todo/todo_agent.py` |
| **Execute Supervisor** | 실행 관리 | `supervisor/execute_supervisor.py` |
| **Domain Agents** | 실제 작업 수행 | `agents/{domain}/` |

---

## 2. 3-Layer 아키텍처

### 2.1 Layer 구조

```python
# Layer 1: Planning (계획)
Cognitive Supervisor → Intent → Context → Plan → Validation

# Layer 2: Management (관리)
TodoAgent → Convert → Dependencies → HITL → Finalize

# Layer 3: Execution (실행)
Execute Supervisor → Order → Select → Execute → Aggregate
```

### 2.2 Layer 간 통신

각 Layer는 명확한 인터페이스를 통해 통신:

```python
# Layer 1 → Layer 2
plan = {
    "goal": str,
    "priority": str,
    "steps": List[Dict],
    "expected_outcome": str
}

# Layer 2 → Layer 3
todos = [
    {
        "id": str,
        "agent": str,
        "task": str,
        "capability": str,
        "params": Dict,
        "dependencies": List[str]
    }
]

# Layer 3 → Response
result = {
    "success": bool,
    "completed": int,
    "failed": int,
    "results": Dict[str, Any]
}
```

---

## 3. Layer 1: Planning Layer

### 3.1 Cognitive Supervisor

**목적**: 사용자 요청을 분석하고 실행 계획 수립

#### 3.1.1 노드 구성

```python
# cognitive_supervisor.py

class CognitiveSupervisor:
    nodes = [
        "analyze_intent",      # 의도 분석
        "retrieve_context",    # 컨텍스트 조회
        "generate_plan",       # 계획 생성
        "validate_plan",       # 계획 검증
        "finalize_plan"        # 계획 확정
    ]
```

#### 3.1.2 Intent Classification

```python
INTENT_PATTERNS = {
    "CREATE_DIET_PLAN": ["다이어트", "식단", "meal"],
    "CREATE_WORKOUT_PLAN": ["운동", "workout", "exercise"],
    "SCHEDULE_MANAGEMENT": ["일정", "스케줄", "schedule"],
    "HEALTH_ANALYSIS": ["건강", "분석", "체중"],
    "PROGRESS_TRACKING": ["진행", "progress", "추적"]
}
```

#### 3.1.3 Plan 구조

```json
{
    "goal": "다이어트 계획 수립",
    "priority": "high",
    "steps": [
        {
            "step_id": "step_001",
            "action": "analyze_health",
            "agent": "diet_agent",
            "capability": "health_tracking",
            "params": {
                "user_id": "user123",
                "period": "1_month"
            },
            "dependencies": [],
            "estimated_time": "2분"
        }
    ],
    "expected_outcome": "개인 맞춤 다이어트 계획"
}
```

### 3.2 Context Management

메모리와 이전 대화를 활용한 컨텍스트 구축:

```python
async def retrieve_context_node(state, memory_manager):
    context = {
        "user_profile": await memory_manager.get_user_profile(),
        "similar_conversations": await memory_manager.search_similar(),
        "current_time": datetime.now().isoformat(),
        "intent": state.user_intent
    }
    return {"context": context}
```

---

## 4. Layer 2: Management Layer

### 4.1 TodoAgent

**목적**: Plan을 실행 가능한 TODO로 변환하고 사용자 승인 처리

#### 4.1.1 주요 기능

1. **Plan → TODO 변환**
2. **의존성 분석**
3. **순환 의존성 감지**
4. **HITL 처리**
5. **TODO 수정 관리**

#### 4.1.2 워크플로우

```python
# todo_agent.py

def build_graph(self):
    workflow = StateGraph(TodoAgentState)

    # 노드 추가
    workflow.add_node("analyze_plan", self.analyze_plan_node)
    workflow.add_node("generate_todos", self.generate_todos_node)
    workflow.add_node("analyze_dependencies", self.analyze_dependencies_node)
    workflow.add_node("request_human_approval", self.request_human_approval_node)
    workflow.add_node("wait_for_human", self.wait_for_human_node)
    workflow.add_node("apply_modifications", self.apply_modifications_node)
    workflow.add_node("finalize_todos", self.finalize_todos_node)

    # 조건부 엣지
    workflow.add_conditional_edges(
        "request_human_approval",
        self.check_approval_required,
        {
            "need_approval": "wait_for_human",
            "auto_approve": "finalize_todos"
        }
    )

    return workflow
```

#### 4.1.3 HITL (Human-in-the-Loop)

```python
# HITL 승인 요청 구조
approval_request = {
    "type": "todo_approval_request",
    "session_id": "session_123",
    "todos": [...],
    "plan_goal": "다이어트 계획",
    "total_todos": 5,
    "estimated_time": "10 minutes"
}

# Human 응답 처리
human_feedback = {
    "action": "modified",  # approved | modified | rejected
    "modifications": [
        {
            "todo_id": "todo_001",
            "changes": {"params": {"calories": 1800}}
        }
    ]
}
```

#### 4.1.4 의존성 분석

```python
def _calculate_execution_levels(todos):
    """병렬 실행 가능한 그룹 계산"""
    levels = []
    completed = set()

    while len(completed) < len(todos):
        level = []
        for todo in todos:
            if todo["id"] in completed:
                continue

            # 모든 의존성이 완료되었는지 확인
            deps = todo.get("dependencies", [])
            if all(d in completed for d in deps):
                level.append(todo["id"])

        levels.append(level)
        completed.update(level)

    return levels
```

---

## 5. Layer 3: Execution Layer

### 5.1 Execute Supervisor

**목적**: TODO를 기반으로 Agent 실행 관리

#### 5.1.1 노드 구성

```python
nodes = [
    "calculate_execution_order",  # 실행 순서 계산
    "select_next_todos",          # 다음 TODO 선택
    "execute_agents",             # Agent 실행
    "handle_failures",            # 실패 처리
    "aggregate_results"           # 결과 종합
]
```

#### 5.1.2 병렬 실행

```python
async def execute_parallel_group(todos, context):
    """병렬 실행 가능한 TODO 그룹 실행"""
    tasks = []

    for todo in todos:
        task = asyncio.create_task(
            execute_single_agent(
                todo=todo,
                context=context,
                dependencies=get_dependencies_results(todo)
            )
        )
        tasks.append(task)

    # 모든 태스크 완료 대기
    results = await asyncio.gather(*tasks, return_exceptions=True)

    return process_results(results)
```

#### 5.1.3 Agent 실행

```python
async def execute_single_agent(todo, context):
    # 1. Agent 인스턴스 가져오기
    agent = agent_registry.get_agent_instance(todo["agent"])

    # 2. 없으면 생성
    if not agent:
        agent = agent_registry.create_agent(todo["agent"])

    # 3. 대체 Agent 찾기 (필요시)
    if not agent:
        alternative = capability_router.find_best_agent(todo["capability"])
        agent = agent_registry.create_agent(alternative)

    # 4. 실행
    result = await agent.execute(
        task={"type": todo["task"], "params": todo["params"]},
        context=context,
        thread_id=context["session_id"]
    )

    return result
```

### 5.2 Domain Agents

각 도메인별 실제 작업 수행:

| Agent | 역할 | Capabilities |
|-------|------|-------------|
| **DietAgent** | 식단 관리 | meal_planning, nutrition_analysis |
| **WorkoutAgent** | 운동 관리 | exercise_planning, fitness_assessment |
| **ScheduleAgent** | 일정 관리 | scheduling, calendar_management |
| **HealthAgent** | 건강 분석 | health_tracking, data_analysis |
| **CoachingAgent** | 코칭 | coaching, motivation, feedback |

---

## 6. 데이터 흐름

### 6.1 전체 흐름

```
User Request
    ↓
[Main Orchestrator]
    ↓
[Cognitive Supervisor] → Plan
    ↓
[TodoAgent] → TODOs + HITL
    ↓
[Execute Supervisor] → Parallel Execution
    ↓
[Domain Agents] → Results
    ↓
[Aggregation] → Final Response
    ↓
User
```

### 6.2 State 전달

```python
# 1. User → Cognitive
state = {
    "messages": [HumanMessage(content="다이어트 계획 만들어줘")],
    "session_id": "session_123",
    "context": {}
}

# 2. Cognitive → TodoAgent
state = {
    "plan": {...},
    "user_context": {...},
    "task": {"type": "convert_plan", "plan": plan}
}

# 3. TodoAgent → Execute
state = {
    "todos": [...],
    "session_id": "session_123",
    "context": {...}
}

# 4. Execute → Agents
state = {
    "todo": {...},
    "context": {...},
    "dependencies": {...}
}
```

### 6.3 Checkpoint 저장

```python
# PostgreSQL 기반 상태 저장
if checkpointer:
    config = {
        "configurable": {
            "thread_id": f"{session_id}_{component_id}"
        }
    }
    result = await graph.ainvoke(state, config=config)
```

---

## 7. 시스템 초기화

### 7.1 Main Orchestrator 초기화

```python
# main_orchestrator.py

orchestrator = MainOrchestrator(
    llm=ChatOpenAI(model="gpt-4o-mini"),
    checkpointer=AsyncPostgresSaver.from_conn_string(db_url),
    memory_manager=memory_manager,
    auto_approve_todos=False  # HITL 활성화
)
```

### 7.2 Agent Registry 초기화

```python
# 자동 Agent 발견
discovered = agent_registry.discover_agents("backend/app/octostrator/agents")

# 수동 Agent 등록
agent_registry.register(DietAgent, "diet_agent")

# Agent 인스턴스 생성
diet_agent = agent_registry.create_agent("diet_agent")
await diet_agent.initialize(llm, checkpointer)
```

### 7.3 시스템 사용

```python
# 방법 1: 직접 orchestrator 사용 (권장)
result = await orchestrator.process_request(
    user_message="다이어트 계획 만들어줘",
    session_id="session_123",
    user_id="user456",
    context={"age": 30, "weight": 70}
)

# 방법 2: 래퍼 함수 사용
from backend.app.octostrator.supervisor.main_graph import process_user_request

result = await process_user_request(
    message="다이어트 계획 만들어줘",
    session_id="session_123"
)

# 방법 3: Legacy 그래프 사용 (호환성)
graph = build_supervisor_graph(context, checkpointer)
result = await graph.ainvoke(state)
```

---

## 8. 에러 처리

### 8.1 Layer별 에러 처리

```python
# Layer 1: Planning 에러
try:
    plan = await cognitive_supervisor.plan(message, session_id)
except PlanningError as e:
    return {"error": "Failed to create plan", "details": str(e)}

# Layer 2: TODO 에러
try:
    todos = await todo_agent.execute(task, context)
except TodoConversionError as e:
    return {"error": "Failed to convert plan", "details": str(e)}

# Layer 3: Execution 에러
try:
    result = await execute_supervisor.execute(todos, session_id)
except ExecutionError as e:
    # 부분 실패 허용
    return {"partial_success": True, "completed": e.completed, "failed": e.failed}
```

### 8.2 Agent 에러 처리

```python
async def handle_agent_error(error, todo, state):
    """Agent 실행 에러 처리"""

    # 1. TodoAgent에 에러 알림
    retry_decision = await todo_agent.handle_error(error_info)

    if retry_decision["action"] == "retry":
        # 재시도
        return await execute_single_agent(todo, context)

    elif retry_decision["action"] == "skip":
        # 건너뛰기 - 의존 Agent들에 알림
        for dep_todo in get_dependent_todos(todo["id"]):
            await adjust_dependency(dep_todo, todo["id"])

    elif retry_decision["action"] == "ask_user":
        # 사용자 개입 요청
        return await request_user_intervention(error_info)
```

### 8.3 복구 전략

1. **Checkpoint 복원**: 실패 시 이전 상태로 복원
2. **대체 Agent**: Capability 기반 대체 Agent 자동 선택
3. **부분 실행**: 실패한 TODO만 재실행
4. **Graceful Degradation**: 핵심 기능만 실행

---

## 부록

### A. 파일 구조

```
backend/app/octostrator/
├── main_orchestrator.py         # 메인 오케스트레이터
├── supervisor/
│   ├── cognitive_supervisor.py  # 계획 수립
│   └── execute_supervisor.py    # 실행 관리
├── agents/
│   ├── base/
│   │   ├── base_agent.py       # Agent 베이스 클래스
│   │   ├── agent_registry.py   # Agent 레지스트리
│   │   └── capabilities.py     # 능력 정의
│   ├── todo/
│   │   └── todo_agent.py       # TODO 관리
│   └── {domain}/
│       └── {domain}_agent.py   # 도메인 Agent
└── states/
    └── supervisor_state.py      # State 정의
```

### B. 환경 변수

```bash
# PostgreSQL (Checkpoint용)
POSTGRES_URL=postgresql://user:pass@localhost/ptmanager

# OpenAI API
OPENAI_API_KEY=sk-...

# 시스템 설정
AUTO_APPROVE_TODOS=false
LLM_MODEL=gpt-4o-mini
MAX_RETRIES=3
```

### C. 로깅

```python
import logging

# 로거 설정
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# 로그 레벨
# DEBUG: 상세 디버그 정보
# INFO: 일반 정보
# WARNING: 경고 (대체 Agent 사용 등)
# ERROR: 에러 (복구 가능)
# CRITICAL: 치명적 에러 (시스템 중단)
```

---

**작성 완료일**: 2025-11-05
**다음 문서**: [Agent 개발 가이드](./AGENT_DEVELOPMENT_GUIDE_251105.md)