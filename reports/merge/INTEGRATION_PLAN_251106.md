# 7개 비즈니스 에이전트와 Octostrator 통합 계획서 (Option A+)

**프로젝트**: AI PT Manager - 에이전트 통합 (Context API 확장 가능 구조)
**작성일**: 2025-11-06
**버전**: 2.0 (Option A+ - 확장 포인트 포함)
**상태**: 계획 수립

---

## 🎯 전략: Option A+ (추천)

**"에이전트 통합 먼저, Context API는 나중에 쉽게 추가"**

### 핵심 아이디어
1. **Phase 1**: 에이전트 통합 (2주) - Context API 없이 구현하되, 확장 포인트 설계
2. **Phase 2**: Context API 추가 (선택적, 1주) - 최소 수정으로 비용 최적화

### 장점
- ✅ 복잡도 낮음 (Context API 이해 불필요)
- ✅ 빠른 가치 확보 (2주 내 에이전트 사용 가능)
- ✅ 확장성 확보 (나중에 Context API 추가가 매우 쉬움)
- ✅ 유연성 (Context API를 안 해도 시스템 정상 동작)

---

## 📋 목차

1. [개요](#1-개요)
2. [현재 구조 분석](#2-현재-구조-분석)
3. [통합 목표](#3-통합-목표)
4. [통합 아키텍처 설계 (확장 포인트 포함)](#4-통합-아키텍처-설계-확장-포인트-포함)
5. [단계별 구현 계획](#5-단계별-구현-계획)
6. [State 통합 전략](#6-state-통합-전략)
7. [에이전트 수정 가이드](#7-에이전트-수정-가이드)
8. [테스트 전략](#8-테스트-전략)
9. [위험 요소 및 대응](#9-위험-요소-및-대응)
10. [타임라인](#10-타임라인)
11. [Context API 확장 전략](#11-context-api-확장-전략)

---

## 1. 개요

### 1.1 배경

현재 **7개의 비즈니스 역할 기반 에이전트**(62개 Tools)가 독립적으로 구현되어 있으나, **Octostrator Main Graph**의 Execute Layer에 통합되지 않은 상태입니다.

**새로운 에이전트**:
- FrontdeskAgent (12 tools)
- AssessorAgent (7 tools)
- ProgramDesignerAgent (10 tools)
- ManagerAgent (8 tools)
- MarketingAgent (9 tools)
- OwnerAssistantAgent (8 tools)
- TrainerEducationAgent (8 tools)

**기존 Octostrator 구조**:
```
START → Cognitive → [Todo Manager] → Execute → Response → END
```

### 1.2 통합 필요성

1. **Execute Layer가 비어있음**: 현재 Execute Layer는 시뮬레이션 코드만 존재
2. **State 불일치**: 각 에이전트는 자체 State를 가지나 OctostratorState와 통합 필요
3. **동적 에이전트 선택 필요**: Todo의 `agent` 필드에 따라 적절한 에이전트 실행
4. **Checkpoint 전략 부재**: 각 에이전트의 checkpoint를 Octostrator와 조율 필요

### 1.3 목표

✅ **7개 에이전트를 Octostrator Execute Layer에 통합**
✅ **Todo 기반 동적 에이전트 라우팅 구현**
✅ **State 통합 및 일관성 유지**
✅ **에이전트 최소 수정 원칙 준수**

---

## 2. 현재 구조 분석

### 2.1 Octostrator 구조

**파일 구조**:
```
backend/app/octostrator/
├── supervisors/
│   ├── octostrator/
│   │   ├── octostrator_graph.py      # Main graph builder
│   │   └── octostrator_nodes.py      # Layer nodes
│   ├── cognitive/                    # Cognitive Layer (Planning)
│   ├── todo/                         # Todo Manager Layer
│   ├── execute/                      # Execute Layer ⚠️ (현재 비어있음)
│   └── response/                     # Response Layer
├── agents/                           # ✅ 새로운 7개 에이전트
├── tools/                            # ✅ 62개 Tools
└── states/
    ├── octostrator_state.py          # Main State
    ├── frontdesk_state.py            # Frontdesk Agent State
    ├── assessor_state.py             # Assessor Agent State
    └── ... (각 에이전트별 State)
```

**OctostratorState 주요 필드**:
```python
class OctostratorState(TypedDict, total=False):
    # Input
    user_query: str
    session_id: str

    # Planning
    plan: dict
    todos: Annotated[List[Dict], merge_todos_smart]

    # Execution
    execution_results: dict  # ⚠️ 에이전트 결과를 여기에 저장

    # Flags
    plan_requires_todos: bool
    need_todo_update: bool
    user_requested_todo_update: bool

    # History
    action_history: Annotated[List[Dict], add_with_timestamp_and_step]
    user_interactions: Annotated[List[Dict], track_user_interactions]
```

### 2.2 새로운 에이전트 구조

**BaseAgent 특징**:
- 모든 에이전트는 `BaseAgent` 상속
- 자체 `build_graph()` 메서드로 독립 workflow 구축
- `enable_checkpoint=True` (각 에이전트가 자체 checkpoint 지원)
- `execute()` 메서드로 task 실행
- 자체 State 사용 (예: FrontdeskState, AssessorState)

**문제점**:
1. ❌ 각 에이전트의 State가 OctostratorState와 분리
2. ❌ Execute Layer에서 에이전트를 호출하는 로직 없음
3. ❌ Todo → Agent 매핑 로직 부재
4. ❌ 에이전트 실행 결과를 OctostratorState에 통합하는 로직 없음

### 2.3 Tools 구조

**Tools Registry**:
- 62개 tools가 `backend/app/octostrator/tools/__init__.py`에 등록
- 도메인별로 분류 (frontdesk, assessor, program_designer 등)
- 모든 tool은 async 함수
- SQLite DB와 직접 연동

**현재 문제점**:
- ❌ Tools가 에이전트와 연결되어 있으나, Octostrator에서 직접 호출 불가능
- ✅ Tools는 독립적으로 사용 가능 (잘 설계됨)

---

## 3. 통합 목표

### 3.1 최종 아키텍처

```
┌─────────────────────────────────────────────────────────────────┐
│                     Octostrator Main Graph                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  START                                                           │
│    ↓                                                             │
│  Cognitive Layer                                                 │
│    - User query 분석                                             │
│    - Plan 생성                                                   │
│    - plan_requires_todos = True 설정                            │
│    ↓                                                             │
│  [Conditional Edge: should_use_todo_manager()]                   │
│    ↓                                                             │
│  Todo Manager Layer (조건부)                                      │
│    - Plan → Todos 변환                                           │
│    - 각 Todo에 agent 할당                                        │
│    - todos = [                                                   │
│        {task: "...", agent: "frontdesk_agent", ...},            │
│        {task: "...", agent: "assessor_agent", ...}              │
│      ]                                                           │
│    ↓                                                             │
│  Execute Layer ⭐ (통합 지점)                                     │
│    - Todo별 Agent 라우팅                                         │
│    - Agent 초기화 및 실행                                        │
│    - 결과 수집 및 집계                                           │
│    ┌─────────────────────────────────────┐                      │
│    │  Agent Router                       │                      │
│    │  ├─> FrontdeskAgent.execute()       │                      │
│    │  ├─> AssessorAgent.execute()        │                      │
│    │  ├─> ProgramDesignerAgent.execute() │                      │
│    │  ├─> ManagerAgent.execute()         │                      │
│    │  ├─> MarketingAgent.execute()       │                      │
│    │  ├─> OwnerAssistantAgent.execute()  │                      │
│    │  └─> TrainerEducationAgent.execute()│                      │
│    └─────────────────────────────────────┘                      │
│    ↓                                                             │
│  Response Layer                                                  │
│    - 결과 종합                                                   │
│    - 최종 응답 생성                                              │
│    ↓                                                             │
│  END                                                             │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 핵심 요구사항

1. **동적 Agent 선택**: Todo의 `agent` 필드로 실행할 에이전트 결정
2. **State 통합**: 에이전트 결과를 `OctostratorState.execution_results`에 저장
3. **최소 수정**: 에이전트 코드는 최소한만 수정 (필수 경우만)
4. **Checkpoint 조율**: 각 에이전트의 checkpoint와 Octostrator checkpoint 동기화
5. **에러 처리**: 에이전트 실행 실패 시 graceful degradation

---

## 4. 통합 아키텍처 설계 (확장 포인트 포함)

### 4.1 Execute Layer 재설계 (Context API 확장 가능)

**핵심 설계 원칙**:
1. ⭐ **확장 포인트**: LLM 생성 로직을 별도 함수로 분리
2. ⭐ **유연한 시그니처**: `runtime=None` 파라미터 준비
3. ⭐ **최소 수정**: 나중에 Context API 추가 시 2-3줄만 수정

**새로운 Execute Layer 노드** (Phase 1 - Context API 없이, 확장 포인트 포함):

```python
# backend/app/octostrator/supervisors/execute/execute_nodes.py

from typing import Dict, Any, Optional
from langchain_openai import ChatOpenAI
from langgraph.types import Runtime  # Phase 2 준비
import logging

logger = logging.getLogger(__name__)


# ⭐⭐⭐ 확장 포인트 1: LLM 생성 헬퍼 함수 ⭐⭐⭐
def _create_llm_for_agents(runtime: Optional[Runtime] = None) -> ChatOpenAI:
    """
    Agent용 LLM 생성 (Context API 확장 포인트)

    [Phase 1] runtime=None: 기본 설정 사용
    [Phase 2] runtime 있음: Context API 설정 사용

    Args:
        runtime: LangGraph Runtime (Context API)

    Returns:
        ChatOpenAI instance
    """
    from backend.app.config.system import config as system_config

    if runtime is not None:
        # ⭐ Phase 2에서 활성화: Context API 사용
        try:
            from backend.app.octostrator.contexts.app_context import AppContext
            context: AppContext = runtime.context
            settings = context.llm_settings

            logger.info(f"[Execute] Using Context API settings (model={settings.agent_model})")

            return ChatOpenAI(
                model=settings.agent_model,              # Phase 2: "gpt-4o-mini"
                temperature=settings.agent_temperature,   # Phase 2: 0.5
                max_tokens=settings.agent_max_tokens,     # Phase 2: 4096
                api_key=system_config.openai_api_key
            )
        except Exception as e:
            logger.warning(f"[Execute] Failed to use Context API, falling back to default: {e}")

    # Phase 1: 기본 설정
    logger.info(f"[Execute] Using default LLM settings (model={system_config.openai_model})")

    return ChatOpenAI(
        model=system_config.openai_model,
        api_key=system_config.openai_api_key,
        temperature=0.7,
        max_tokens=4096
    )


# ⭐⭐⭐ 확장 포인트 2: runtime 파라미터 준비 ⭐⭐⭐
async def execute_layer_node(
    state: Dict[str, Any],
    runtime: Optional[Runtime] = None  # ⭐ Phase 2를 위한 확장 포인트
) -> Dict[str, Any]:
    """
    Execute Layer Node - 7개 에이전트 실행 및 결과 수집

    [Phase 1] runtime=None으로 동작 (Context API 없이)
    [Phase 2] runtime 자동 주입됨 (Context API 적용 시)

    Flow:
    1. State에서 todos 가져오기
    2. 각 Todo의 agent 필드로 Agent 라우팅
    3. Agent.execute() 호출
    4. 결과를 execution_results에 저장
    5. action_history에 기록
    """
    from backend.app.octostrator.agents import agent_registry

    todos = state.get("todos", [])
    checkpointer = state.get("checkpointer")
    session_id = state.get("session_id")

    execution_results = {}
    completed = 0
    failed = 0

    # ⭐ 확장 포인트 사용: LLM 생성 (Context API 대응)
    llm = _create_llm_for_agents(runtime)  # Phase 1: runtime=None, Phase 2: runtime 자동 주입

    for todo in todos:
        if todo.get("status") != "pending":
            continue

        agent_name = todo.get("agent")  # 예: "frontdesk_agent"
        task_description = todo.get("task")
        todo_id = todo.get("id")

        try:
            # 1. Agent 가져오기 (Registry에서)
            agent_class = agent_registry.get(agent_name)
            if not agent_class:
                raise ValueError(f"Agent '{agent_name}' not found in registry")

            # 2. Agent 인스턴스 생성
            agent = agent_class()

            # 3. Agent 초기화 (LLM + Checkpointer)
            await agent.initialize(llm=llm, checkpointer=checkpointer)

            # 4. Task 준비
            task = {
                "task_id": todo_id,
                "task_type": "todo_execution",
                "description": task_description,
                "todo_data": todo  # 전체 Todo 전달
            }

            context = {
                "user_id": state.get("user_id"),
                "session_id": session_id,
                "parent_state": "octostrator"
            }

            # 5. Agent 실행
            logger.info(f"[Execute] Running {agent_name} for task: {task_description}")
            result = await agent.execute(
                task=task,
                context=context,
                thread_id=session_id  # Checkpoint용
            )

            # 6. 결과 저장
            execution_results[todo_id] = {
                "todo_id": todo_id,
                "agent": agent_name,
                "status": result.get("status", "unknown"),
                "result": result.get("result", {}),
                "started_at": result.get("started_at"),
                "completed_at": result.get("completed_at"),
                "error": result.get("error")
            }

            # 7. Todo 상태 업데이트
            if result.get("status") == "completed":
                todo["status"] = "completed"
                todo["completed_at"] = result.get("completed_at")
                completed += 1
            else:
                todo["status"] = "failed"
                todo["error"] = result.get("error")
                failed += 1

        except Exception as e:
            logger.error(f"[Execute] Failed to execute {agent_name}: {e}")
            execution_results[todo_id] = {
                "todo_id": todo_id,
                "agent": agent_name,
                "status": "failed",
                "error": str(e)
            }
            todo["status"] = "failed"
            todo["error"] = str(e)
            failed += 1

    # 8. State 업데이트
    return {
        "execution_results": execution_results,
        "completed": completed,
        "failed": failed,
        "success_rate": completed / len(todos) if todos else 0,
        "todos": todos,  # 업데이트된 todos (merge_todos_smart가 자동 병합)
        "action_history": [{
            "action": "execute_layer_node",
            "result": {
                "total_todos": len(todos),
                "completed": completed,
                "failed": failed
            }
        }]
    }
```

### 4.2 Agent Registry 확인

**위치**: `backend/app/octostrator/agents/base/agent_registry.py`

현재 구조:
```python
class AgentRegistry:
    def __init__(self):
        self._agents: Dict[str, Type[BaseAgent]] = {}

    def register(self, agent_class: Type[BaseAgent], name: str):
        self._agents[name] = agent_class

    def get(self, name: str) -> Optional[Type[BaseAgent]]:
        return self._agents.get(name)

    def list_all(self) -> List[str]:
        return list(self._agents.keys())

agent_registry = AgentRegistry()
```

**문제 없음**: Registry는 이미 잘 설계되어 있음 ✅

### 4.3 Todo → Agent 매핑 전략

**Todo Manager에서 Agent 할당**:

```python
# backend/app/octostrator/supervisors/todo/todo_manager.py

async def todo_layer_node(state: OctostratorState) -> OctostratorState:
    """
    Todo Manager Layer Node

    Plan의 각 step을 Todo로 변환하고, 적절한 Agent 할당
    """
    plan = state.get("plan", {})
    steps = plan.get("steps", [])

    todos = []
    for idx, step in enumerate(steps, start=1):
        # LLM으로 Agent 선택
        agent_name = await select_agent_for_task(step, llm=state.get("llm"))

        todo = {
            "task": step.get("description"),
            "agent": agent_name,  # ⭐ Agent 할당
            "priority": step.get("priority", 3),
            "status": "pending",
            "dependencies": step.get("dependencies", [])
        }
        todos.append(todo)

    return {
        "todos": todos  # merge_todos_smart가 자동으로 id, step, timestamp 추가
    }


async def select_agent_for_task(step: dict, llm) -> str:
    """
    Task를 분석하여 적절한 Agent 선택

    LLM을 사용하여 다음 중 하나를 선택:
    - frontdesk_agent
    - assessor_agent
    - program_designer_agent
    - manager_agent
    - marketing_agent
    - owner_assistant_agent
    - trainer_education_agent
    """
    from langchain.prompts import ChatPromptTemplate

    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an AI agent router. Given a task description, select the most appropriate agent.

Available agents:
- frontdesk_agent: 신규 리드 관리, 상담 예약, 문의 응대
- assessor_agent: 체성분 분석, 자세 평가, 피트니스 점수
- program_designer_agent: 운동/식단 프로그램 설계
- manager_agent: 회원 출석 관리, 이탈 위험 분석
- marketing_agent: SNS 마케팅, 이벤트 운영
- owner_assistant_agent: 매출 분석, 트레이너 성과 관리
- trainer_education_agent: 트레이너 교육 및 스킬 평가

Return ONLY the agent name, nothing else."""),
        ("user", "Task: {task}")
    ])

    chain = prompt | llm
    result = await chain.ainvoke({"task": step.get("description")})

    agent_name = result.content.strip()

    # Validation
    valid_agents = [
        "frontdesk_agent", "assessor_agent", "program_designer_agent",
        "manager_agent", "marketing_agent", "owner_assistant_agent",
        "trainer_education_agent"
    ]

    if agent_name not in valid_agents:
        logger.warning(f"Invalid agent '{agent_name}', using frontdesk_agent as default")
        return "frontdesk_agent"

    return agent_name
```

---

## 5. 단계별 구현 계획

### Phase 1: Execute Layer 구현 (필수)

**목표**: Execute Layer가 7개 에이전트를 동적으로 실행

**작업**:
1. ✅ `execute_layer_node()` 함수 재작성
   - 파일: `backend/app/octostrator/supervisors/execute/execute_nodes.py`
   - Agent Registry 통합
   - Todo → Agent 라우팅 로직
   - 결과 수집 및 집계

2. ✅ `octostrator_nodes.py` 수정
   - 파일: `backend/app/octostrator/supervisors/octostrator/octostrator_nodes.py`
   - `execute_layer_node` import 및 호출

3. ✅ Todo Manager에 Agent 선택 로직 추가
   - 파일: `backend/app/octostrator/supervisors/todo/todo_manager.py`
   - `select_agent_for_task()` 함수 추가
   - LLM 기반 Agent 선택

**수정 파일**:
- `backend/app/octostrator/supervisors/execute/execute_nodes.py` (완전 재작성)
- `backend/app/octostrator/supervisors/octostrator/octostrator_nodes.py` (import 추가)
- `backend/app/octostrator/supervisors/todo/todo_manager.py` (Agent 선택 로직)

**에이전트 수정 필요**: ❌ **없음** (현재 구조 그대로 사용)

---

### Phase 2: State 통합 및 데이터 흐름 개선 (필수)

**목표**: 에이전트 실행 결과를 OctostratorState에 올바르게 통합

**작업**:
1. ✅ `execution_results` 구조 표준화
   - 각 에이전트 결과를 일관된 형식으로 저장
   - Schema:
     ```python
     {
       "todo_id_1": {
         "agent": "frontdesk_agent",
         "status": "completed",
         "result": {...},  # Agent의 반환 결과
         "started_at": "...",
         "completed_at": "...",
         "error": null
       }
     }
     ```

2. ✅ `action_history` 자동 기록
   - 각 에이전트 실행마다 자동으로 기록
   - Reducer `add_with_timestamp_and_step`이 자동 처리

**수정 파일**:
- 없음 (이미 OctostratorState에 정의되어 있음)

**에이전트 수정 필요**: ❌ **없음**

---

### Phase 3: Checkpoint 조율 (선택적)

**목표**: 에이전트별 Checkpoint와 Octostrator Checkpoint 동기화

**현재 상황**:
- Octostrator: `AsyncPostgresSaver` 사용
- 각 에이전트: `enable_checkpoint=True`로 설정

**전략**:

**Option 1: 에이전트별 독립 Checkpoint** (권장)
- 각 에이전트는 자체 thread_id 사용 (`{session_id}_{agent_id}`)
- Octostrator와 독립적으로 checkpoint 관리
- 장점: 에이전트 재실행 시 독립적으로 resume 가능
- 단점: Checkpoint 개수 증가

**Option 2: Octostrator만 Checkpoint**
- 각 에이전트는 `enable_checkpoint=False`로 변경
- Octostrator만 checkpoint 관리
- 장점: Checkpoint 단순화
- 단점: 에이전트 내부 상태 resume 불가능

**선택**: **Option 1** (에이전트별 독립 Checkpoint)

**작업**:
1. Execute Layer에서 각 에이전트에 고유 thread_id 전달
   - Format: `{session_id}_{agent_id}` (이미 구현됨)
2. 에이전트 실행 시 checkpointer 전달 (이미 구현됨)

**수정 파일**:
- 없음 (이미 구현됨)

**에이전트 수정 필요**: ❌ **없음**

---

### Phase 4: Todo Manager Agent 선택 개선 (선택적)

**목표**: LLM 기반 지능형 Agent 선택

**현재**:
- 간단한 키워드 매칭

**개선**:
- LLM을 사용한 의도 분석 및 Agent 선택
- 각 Agent의 capabilities 고려
- Few-shot learning으로 정확도 향상

**작업**:
1. `select_agent_for_task()` 함수 고도화
   - LangChain PromptTemplate 사용
   - Few-shot examples 추가
   - Agent capabilities 설명 추가

**수정 파일**:
- `backend/app/octostrator/supervisors/todo/todo_manager.py`

**에이전트 수정 필요**: ❌ **없음**

---

### Phase 5: API 통합 (선택적)

**목표**: Phase 2 API에서 에이전트를 직접 변경 가능

**작업**:
1. `PUT /api/sessions/{thread_id}/todos/{todo_id}/agent` 엔드포인트
   - 이미 구현되어 있음 ✅
2. Frontend에서 Todo의 Agent 변경 가능

**수정 파일**:
- 없음 (이미 구현됨)

---

### Phase 6: 테스트 및 검증 (필수)

**목표**: 통합된 시스템의 동작 검증

**작업**:
1. ✅ 단위 테스트 작성
   - `test_execute_layer.py`: Execute Layer 단독 테스트
   - `test_agent_routing.py`: Agent 선택 로직 테스트

2. ✅ 통합 테스트 작성
   - `test_full_workflow.py`: Cognitive → Todo → Execute → Response 전체 흐름
   - 각 Agent별 실행 검증

3. ✅ Mock 데이터로 검증
   - 이미 Mock 데이터 생성 스크립트 있음 (`create_all_mocks.py`)

**테스트 시나리오**:
1. 신규 회원 상담 요청 (Frontdesk Agent)
2. 체성분 분석 (Assessor Agent)
3. 운동 프로그램 생성 (Program Designer Agent)
4. 출석 관리 (Manager Agent)
5. SNS 게시물 생성 (Marketing Agent)
6. 매출 분석 (Owner Assistant Agent)
7. 트레이너 평가 (Trainer Education Agent)

**수정 파일**:
- `tests/test_execute_layer.py` (신규)
- `tests/test_agent_routing.py` (신규)
- `tests/test_full_workflow.py` (신규)

---

## 6. State 통합 전략

### 6.1 State 계층 구조

```
OctostratorState (Main State)
  │
  ├─ user_query, session_id, plan, todos
  ├─ execution_results                   ⭐ 모든 에이전트 결과 저장
  ├─ action_history                      ⭐ 모든 작업 내역
  │
  └─ (각 에이전트 실행 시)
      │
      ├─ FrontdeskAgent.execute(task, context)
      │    └─ FrontdeskState (임시)
      │         └─ 결과 → execution_results["todo_1"]
      │
      ├─ AssessorAgent.execute(task, context)
      │    └─ AssessorState (임시)
      │         └─ 결과 → execution_results["todo_2"]
      │
      └─ ... (나머지 에이전트)
```

### 6.2 데이터 매핑

**에이전트 → OctostratorState 매핑**:

| Agent State 필드 | OctostratorState 필드 | 매핑 방법 |
|------------------|----------------------|----------|
| `result` | `execution_results[todo_id]["result"]` | 직접 저장 |
| `status` | `todos[i]["status"]` | 업데이트 |
| `error` | `execution_results[todo_id]["error"]` | 오류 시 저장 |
| `messages` | `action_history` | 변환 후 추가 |

**변환 예시**:
```python
# Agent 실행 결과
agent_result = {
    "agent_id": "frontdesk_agent",
    "status": "completed",
    "result": {
        "lead_id": 123,
        "lead_score": 85,
        "appointment_scheduled": True
    }
}

# OctostratorState에 저장
state["execution_results"]["todo_1"] = {
    "todo_id": "todo_1",
    "agent": "frontdesk_agent",
    "status": "completed",
    "result": agent_result["result"],
    "started_at": "2025-11-06T12:00:00",
    "completed_at": "2025-11-06T12:00:05"
}

state["todos"][0]["status"] = "completed"
state["todos"][0]["completed_at"] = "2025-11-06T12:00:05"

state["action_history"].append({
    "action": "execute_frontdesk_agent",
    "result": {"lead_id": 123, "lead_score": 85}
    # add_with_timestamp_and_step가 자동으로 step, timestamp 추가
})
```

### 6.3 State 충돌 방지

**문제**: 각 에이전트가 자체 State를 가지므로, OctostratorState와 충돌 가능

**해결책**:
1. **에이전트는 OctostratorState를 직접 수정하지 않음**
2. **에이전트 실행은 독립적**: `agent.execute(task, context)` → 결과 반환
3. **Execute Layer가 결과를 OctostratorState에 통합**

**흐름**:
```
Execute Layer:
  1. Todo에서 agent 정보 가져오기
  2. Agent 인스턴스 생성 및 초기화
  3. agent.execute(task, context) 호출
     → 에이전트 내부에서 FrontdeskState 사용
     → 결과 반환
  4. 반환된 결과를 OctostratorState.execution_results에 저장
  5. Todo 상태 업데이트
```

**에이전트 수정 필요**: ❌ **없음** (각 에이전트는 독립적으로 동작)

---

## 7. 에이전트 수정 가이드

### 7.1 수정 필요 여부 판단

**원칙**: 에이전트는 **최소한만 수정**. 대부분의 통합은 Execute Layer에서 처리.

**수정 필요 시나리오**:
1. ❌ State 통합: **수정 불필요** (Execute Layer가 처리)
2. ❌ Checkpoint: **수정 불필요** (이미 지원됨)
3. ❌ Result 형식: **수정 불필요** (현재 반환 형식 유지)
4. ✅ **수정 필요한 경우**: Execute Layer와의 인터페이스 불일치

**현재 상태 검증**:
- ✅ 모든 에이전트가 `execute(task, context, thread_id)` 메서드 지원
- ✅ 모든 에이전트가 `initialize(llm, checkpointer)` 메서드 지원
- ✅ 모든 에이전트가 표준 결과 형식 반환

**결론**: **에이전트 수정 불필요** ✅

### 7.2 만약 수정이 필요하다면

**수정 대상**:
- `backend/app/octostrator/agents/{agent_name}/{agent_name}_agent.py`

**수정 사항**:
1. `execute()` 메서드의 반환 형식 표준화
2. `task` 파라미터에서 `todo_data` 필드 활용
3. `context` 파라미터에서 `parent_state` 필드 확인

**수정 예시** (필요 시):
```python
# before
async def process_task(self, task: Dict[str, Any], context: Dict[str, Any]):
    # Custom logic
    return {"custom_field": "value"}

# after (표준화)
async def process_task(self, task: Dict[str, Any], context: Dict[str, Any]):
    # Custom logic
    result = {"custom_field": "value"}

    # 표준 형식으로 반환
    return {
        "agent_id": self.agent_id,
        "status": "completed",  # or "failed"
        "result": result,
        "error": None
    }
```

**현재 확인 결과**: 모든 에이전트가 이미 표준 형식을 따름 ✅

---

## 8. 테스트 전략

### 8.1 단위 테스트

**테스트 파일**: `tests/test_execute_layer.py`

**테스트 케이스**:
```python
import pytest
from backend.app.octostrator.supervisors.execute.execute_nodes import execute_layer_node
from backend.app.octostrator.states import OctostratorState

@pytest.mark.asyncio
async def test_execute_single_agent():
    """단일 Agent 실행 테스트"""
    state = {
        "session_id": "test-123",
        "todos": [
            {
                "id": "todo-1",
                "task": "신규 리드 생성",
                "agent": "frontdesk_agent",
                "status": "pending"
            }
        ],
        "checkpointer": mock_checkpointer,
        "llm": mock_llm
    }

    result = await execute_layer_node(state)

    assert result["completed"] == 1
    assert result["failed"] == 0
    assert "todo-1" in result["execution_results"]
    assert result["execution_results"]["todo-1"]["status"] == "completed"


@pytest.mark.asyncio
async def test_execute_multiple_agents():
    """복수 Agent 실행 테스트"""
    state = {
        "session_id": "test-123",
        "todos": [
            {"id": "todo-1", "task": "리드 생성", "agent": "frontdesk_agent", "status": "pending"},
            {"id": "todo-2", "task": "InBody 분석", "agent": "assessor_agent", "status": "pending"},
            {"id": "todo-3", "task": "프로그램 생성", "agent": "program_designer_agent", "status": "pending"}
        ],
        "checkpointer": mock_checkpointer,
        "llm": mock_llm
    }

    result = await execute_layer_node(state)

    assert result["completed"] == 3
    assert len(result["execution_results"]) == 3


@pytest.mark.asyncio
async def test_execute_agent_failure():
    """Agent 실패 처리 테스트"""
    state = {
        "session_id": "test-123",
        "todos": [
            {"id": "todo-1", "task": "Invalid task", "agent": "invalid_agent", "status": "pending"}
        ],
        "checkpointer": mock_checkpointer,
        "llm": mock_llm
    }

    result = await execute_layer_node(state)

    assert result["completed"] == 0
    assert result["failed"] == 1
    assert result["execution_results"]["todo-1"]["status"] == "failed"
```

### 8.2 통합 테스트

**테스트 파일**: `tests/test_full_workflow.py`

**테스트 시나리오**:
```python
@pytest.mark.asyncio
async def test_full_workflow_frontdesk():
    """Cognitive → Todo → Execute (Frontdesk) → Response 전체 흐름"""
    from backend.app.octostrator.supervisors.octostrator.octostrator_graph import build_octostrator_graph

    # Graph 빌드
    graph = build_octostrator_graph(checkpointer=mock_checkpointer)

    # Input
    input_state = {
        "user_query": "새로운 고객이 PT 상담을 요청했습니다. 이름: 김철수, 전화: 010-1234-5678",
        "session_id": "test-session-1",
        "output_format": "chat"
    }

    # 실행
    result = await graph.ainvoke(input_state)

    # 검증
    assert result["plan"] is not None
    assert len(result["todos"]) > 0
    assert "frontdesk_agent" in [t["agent"] for t in result["todos"]]
    assert result["execution_results"] is not None
    assert result["final_response"] is not None
```

### 8.3 Agent별 개별 테스트

**각 Agent의 기존 테스트 활용**:
- `tests/test_agent_tools.py`에 이미 각 Agent의 Tool 테스트 존재 ✅
- 통합 후에도 동일한 테스트로 검증 가능

---

## 9. 위험 요소 및 대응

### 9.1 위험 요소

| 위험 | 발생 가능성 | 영향도 | 대응 방안 |
|-----|-----------|-------|----------|
| State 충돌 | 중 | 높음 | Execute Layer가 State 통합 전담 |
| Checkpoint 불일치 | 중 | 중 | Agent별 독립 thread_id 사용 |
| Agent 선택 오류 | 중 | 중 | LLM + Validation + Fallback |
| 성능 저하 | 낮 | 중 | Agent 병렬 실행 (Phase 2) |
| Tool 호출 실패 | 중 | 중 | Graceful degradation + Retry |

### 9.2 Rollback 전략

**문제 발생 시**:
1. Execute Layer 변경사항만 롤백
2. 에이전트 코드는 수정하지 않았으므로 영향 없음
3. 기존 시뮬레이션 코드로 복원 가능

### 9.3 점진적 배포

**단계적 통합**:
1. **Phase 1**: Execute Layer 기본 구현 (단일 Agent)
2. **Phase 2**: 전체 Agent 통합
3. **Phase 3**: LLM 기반 Agent 선택
4. **Phase 4**: 병렬 실행 최적화

---

## 10. 타임라인

### 10.1 Phase 1: 핵심 통합 (3-4시간)

**Day 1**:
- ✅ Execute Layer 재작성 (2시간)
  - `execute_layer_node()` 구현
  - Agent Registry 통합
  - 결과 수집 로직

- ✅ Todo Manager Agent 선택 (1시간)
  - `select_agent_for_task()` 구현
  - LLM 기반 선택 로직

- ✅ 기본 테스트 (1시간)
  - 단위 테스트 작성
  - Mock 데이터로 검증

### 10.2 Phase 2: 고도화 (2-3시간)

**Day 2**:
- ✅ Agent 선택 개선 (1시간)
  - Few-shot learning
  - Capabilities 기반 선택

- ✅ 통합 테스트 (1시간)
  - 전체 워크플로우 테스트
  - 각 Agent별 시나리오 테스트

- ✅ 문서화 (1시간)
  - API 문서 업데이트
  - Agent 사용 가이드

### 10.3 Phase 3: 최적화 (선택적, 2-3시간)

**Day 3**:
- 병렬 실행 구현
- 캐싱 전략
- 성능 모니터링

**총 예상 시간**: **5-7시간** (Phase 1 - 에이전트 통합)

---

## 11. Context API 확장 전략 (Phase 2 - 선택적)

### 11.1 Phase 2 개요

**목적**: 노드별 LLM 최적화로 비용 47% 절감 (선택적)

**시기**: Phase 1 완료 후, 비용 최적화가 필요할 때

**예상 시간**: 2-3시간 (확장 포인트가 이미 준비되어 있어서 빠름)

### 11.2 Phase 2 작업 내용

#### Step 1: Graph Builder 수정 (1줄 추가)

**파일**: `backend/app/octostrator/supervisors/execute/execute_graph.py`

**Before** (Phase 1):
```python
def build_execute_graph(state_class=None):
    """Build execute layer graph"""
    if state_class is None:
        state_class = dict

    graph = StateGraph(state_class)  # ❌ context_schema 없음

    graph.add_node("execute", execute_layer_node)
    graph.add_node("aggregator", aggregator_node)
    # ...

    return graph.compile()
```

**After** (Phase 2 - 1줄 추가):
```python
from backend.app.octostrator.contexts.app_context import AppContext
from backend.app.config.llm_settings import get_llm_settings_from_env

def build_execute_graph(
    state_class=None,
    context: Optional[AppContext] = None
):
    """Build execute layer graph with Context API support"""

    # State 기본값
    if state_class is None:
        state_class = dict

    # Context 자동 생성 (Phase 2)
    if context is None:
        llm_settings = get_llm_settings_from_env()
        context = AppContext(
            user_id="default_user",
            session_id="default_session",
            llm_settings=llm_settings
        )

    # ⭐ 이것만 추가하면 됨!
    graph = StateGraph(
        state_class,
        context_schema=AppContext  # ⭐ Context API 활성화
    )

    # 나머지는 동일
    graph.add_node("execute", execute_layer_node)
    graph.add_node("aggregator", aggregator_node)
    # ...

    return graph.compile()
```

**수정 범위**: `context_schema=AppContext` 1줄 추가

#### Step 2: Octostrator Graph 수정 (1줄 추가)

**파일**: `backend/app/octostrator/supervisors/octostrator/octostrator_graph.py`

**수정 내용**: execute_graph.py와 동일하게 `context_schema=AppContext` 추가

#### Step 3: 환경 변수 설정

```bash
# Production 환경 (비용 최적화)
export SYSTEM_ENV=production

# Development 환경 (기본값)
export SYSTEM_ENV=development
```

**끝!** 이제 `_create_llm_for_agents(runtime)` 함수가 자동으로 Context API 설정을 사용합니다.

### 11.3 Phase 2 효과

**비용 절감** (Production 환경):
- Before: 모든 노드 `max_tokens=4096` 균일 사용
- After: Agent 노드 `max_tokens=4096`, 기타 노드 최적화
- **예상 절감**: 47% (Context API 계획서 기준)

**환경별 전환**:
- `SYSTEM_ENV=production`: 비용 최적화 (낮은 temp, 적은 tokens)
- `SYSTEM_ENV=development`: 품질 우선 (높은 temp, 넉넉한 tokens)
- `SYSTEM_ENV=testing`: 재현성 (temp=0, 최소 tokens)

### 11.4 Phase 1 vs Phase 2 비교

| 항목 | Phase 1 (현재) | Phase 2 (Context API) | 변경량 |
|------|----------------|---------------------|--------|
| **execute_nodes.py** | `runtime=None`으로 동작 | `runtime` 자동 주입 | 0줄 (이미 준비됨) |
| **execute_graph.py** | context_schema 없음 | `context_schema=AppContext` | 1줄 추가 |
| **LLM 생성** | 기본 설정 사용 | Context API 설정 사용 | 0줄 (자동 전환) |
| **비용** | 기준 (100%) | 47% 절감 | -47% |
| **작업 시간** | - | 2-3시간 | - |

**핵심**: Phase 1에서 확장 포인트를 설계했기 때문에, Phase 2는 **2-3줄만 수정**하면 됩니다!

### 11.5 Phase 2 진행 여부 판단

**Phase 2를 진행해야 하는 경우**:
- ✅ 월 LLM 비용이 부담스러울 때
- ✅ Production 환경에서 비용 최적화가 필요할 때
- ✅ 환경별(Prod/Dev/Test) 설정을 분리하고 싶을 때

**Phase 2를 안 해도 되는 경우**:
- ✅ 비용이 부담스럽지 않을 때
- ✅ 개발 초기 단계 (품질이 우선)
- ✅ 시스템이 정상 동작하는 것이 더 중요할 때

**권장**: Phase 1 완료 후 **1-2개월 사용해보고** 비용을 측정한 뒤 결정

---

## 12. 결론

### 12.1 핵심 요약 (Option A+ 전략)

✅ **에이전트 수정 불필요**: 모든 통합 로직은 Execute Layer에서 처리
✅ **State 통합 명확**: execution_results로 모든 결과 수집
✅ **Checkpoint 독립**: 각 에이전트가 독립적으로 checkpoint 관리
✅ **확장 포인트 설계**: Context API를 나중에 쉽게 추가 가능
✅ **단계적 접근**: Phase 1 (에이전트) → Phase 2 (Context API, 선택적)

### 12.2 Option A+ 장점 요약

| 장점 | 설명 |
|------|------|
| **낮은 복잡도** | Context API 이해 없이도 구현 가능 |
| **빠른 가치** | 2주 내 7개 에이전트 사용 가능 |
| **확장성** | Phase 2에서 2-3줄만 수정하면 Context API 적용 |
| **유연성** | Context API를 안 해도 시스템 정상 동작 |
| **점진적** | 에이전트 먼저, 최적화는 나중에 |

### 12.3 다음 단계

#### Phase 1: 에이전트 통합 (필수, 5-7시간)

1. **Execute Layer 구현**
   - `_create_llm_for_agents()` 헬퍼 함수 작성
   - `execute_layer_node()` 재작성 (runtime=None 파라미터 포함)
   - Agent Registry 통합

2. **Todo Manager 개선**
   - `select_agent_for_task()` LLM 기반 선택 로직
   - Agent 할당 자동화

3. **테스트 및 검증**
   - 단위 테스트 작성
   - 7개 에이전트 모두 동작 확인
   - Mock 데이터로 통합 테스트

#### Phase 2: Context API (선택적, 2-3시간)

**진행 시기**: Phase 1 완료 후 1-2개월 사용 후, 비용 최적화가 필요할 때

1. **Graph Builder 수정**
   - `context_schema=AppContext` 1줄 추가
   - 환경 변수 설정 (`SYSTEM_ENV`)

2. **테스트**
   - 환경별 전환 테스트 (Prod/Dev/Test)
   - 토큰 사용량 측정 (47% 절감 확인)

### 12.4 성공 기준

#### Phase 1 성공 기준
- ✅ 7개 에이전트 모두 Execute Layer에서 실행 가능
- ✅ Todo → Agent 자동 매핑 동작
- ✅ State 일관성 유지
- ✅ 기존 에이전트 코드 변경 없음
- ✅ 모든 테스트 통과

#### Phase 2 성공 기준 (선택적)
- ✅ 환경별 설정 전환 동작 (Prod/Dev/Test)
- ✅ Production 환경에서 비용 47% 절감 달성
- ✅ `_create_llm_for_agents(runtime)` 자동 Context API 사용
- ✅ Phase 1 기능 모두 정상 동작

### 12.5 최종 권장사항

**지금 바로 시작**: Phase 1 (에이전트 통합)
- 복잡도 낮음
- 빠른 가치 확보
- Context API 확장 포인트 포함

**나중에 결정**: Phase 2 (Context API)
- 비용이 부담스러울 때
- 2-3줄만 수정하면 적용 가능
- 안 해도 시스템은 정상 동작

**핵심**: Option A+는 "일단 동작하게 하고, 나중에 최적화"하는 현실적인 접근입니다! 🚀

---

**작성자**: AI Development Team
**검토자**: -
**승인자**: -
**버전**: 2.0 (Option A+ - 확장 포인트 포함)
**날짜**: 2025-11-06
**수정일**: 2025-11-06 (Option A+ 전략 반영)
