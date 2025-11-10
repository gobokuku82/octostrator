# System Architecture Overview - Supervisor + LangGraph Agents

**작성일**: 2025-11-05
**작성자**: AI Assistant
**목적**: Supervisor 패턴과 LangGraph Agent의 통합 구조 설명

---

## 1. 전체 시스템 구조

### 1.1 아키텍처 개요

```
┌──────────────────────────────────────────────────┐
│                   Frontend                        │
│              (React + WebSocket)                  │
└──────────────────────────────────────────────────┘
                        │
                    WebSocket
                        │
┌──────────────────────────────────────────────────┐
│                FastAPI Server                     │
│            /ws/chat/{session_id}                  │
└──────────────────────────────────────────────────┘
                        │
                        ▼
┌──────────────────────────────────────────────────┐
│         SUPERVISOR (LangGraph)                    │ ← 중앙 관제탑
│  - State: SupervisorState                         │
│  - Checkpointer: AsyncPostgresSaver              │
│  - Session: thread_id = session_id               │
│  - Role: 전체 작업 조율 및 Agent 실행           │
└──────────────────────────────────────────────────┘
         │              │              │
         ▼              ▼              ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│  DietAgent   │ │ WorkoutAgent │ │ScheduleAgent │
│ (LangGraph)  │ │ (LangGraph)  │ │ (LangGraph)  │
│ +Checkpoint  │ │ +Checkpoint  │ │ No Checkpoint│
└──────────────┘ └──────────────┘ └──────────────┘
         │              │              │
         ▼              ▼              ▼
┌──────────────────────────────────────────────────┐
│              PostgreSQL Database                  │
│        (Checkpoints + Application Data)           │
└──────────────────────────────────────────────────┘
```

### 1.2 핵심 포인트

**YES, Supervisor 패턴은 계속 사용됩니다!**

- **Supervisor**: 전체 작업의 지휘자 (Orchestrator)
- **Agents**: 각 전문 분야의 실행자 (Executors)
- **LangGraph**: Supervisor와 Agent 모두에서 사용
- **Checkpoint**: Supervisor는 항상, Agent는 선택적

---

## 2. Supervisor의 역할

### 2.1 기존 역할 (유지)

```python
class SupervisorState(TypedDict):
    messages: Sequence[BaseMessage]
    plan: List[dict]  # Agent 실행 계획
    current_step: int
    is_waiting_human: bool
    aggregated_data: dict
    final_result: str
```

**Supervisor는 여전히:**
1. 사용자 요청을 분석
2. 실행 계획(plan) 수립
3. Agent 순서 결정
4. Agent 실행 및 모니터링
5. 결과 종합 및 반환

### 2.2 강화된 기능 (NEW)

```python
# Supervisor가 Agent를 관리하는 새로운 방식
class EnhancedSupervisor:
    def __init__(self):
        self.agent_registry = AgentRegistry()
        self.dependency_resolver = DependencyResolver()
        self.checkpoint_strategy = CheckpointStrategy()

    async def execute_agents(self, plan):
        # 1. Agent 의존성 분석
        execution_plan = self.dependency_resolver.create_execution_plan()

        # 2. 병렬 실행 가능한 그룹 확인
        for agent_group in execution_plan.parallel_groups:
            # 3. 그룹 내 Agent들 병렬 실행
            await asyncio.gather(*[
                self.run_agent(agent_id) for agent_id in agent_group
            ])
```

---

## 3. 구동 구조 상세

### 3.1 시작: 사용자 요청

```python
# 1. WebSocket으로 메시지 수신
async def websocket_endpoint(websocket, session_id):
    message = await websocket.receive_text()

    # 2. Supervisor Graph 실행
    supervisor = build_supervisor_graph(checkpointer)
    result = await supervisor.ainvoke(
        {"messages": [HumanMessage(content=message)]},
        config={"configurable": {"thread_id": session_id}}
    )
```

### 3.2 Supervisor 작동 흐름

```python
# backend/app/octostrator/supervisor/main_graph.py

def build_supervisor_graph(checkpointer):
    workflow = StateGraph(SupervisorState)

    # Supervisor 노드들
    workflow.add_node("planner", planner_node)        # 계획 수립
    workflow.add_node("router", router_node)          # Agent 라우팅
    workflow.add_node("executor", executor_node)      # Agent 실행
    workflow.add_node("aggregator", aggregator_node)  # 결과 종합

    # Agent 노드들 (새로운 방식)
    workflow.add_node("diet_agent", diet_agent_wrapper)
    workflow.add_node("workout_agent", workout_agent_wrapper)

    # 조건부 라우팅
    workflow.add_conditional_edges(
        "router",
        route_to_agent,
        {
            "diet": "diet_agent",
            "workout": "workout_agent",
            "complete": "aggregator"
        }
    )

    return workflow.compile(checkpointer=checkpointer)
```

### 3.3 Agent 실행 방식

#### 방식 1: Wrapper를 통한 실행 (권장)

```python
async def diet_agent_wrapper(state: SupervisorState) -> dict:
    """Supervisor State를 Agent에 맞게 변환하여 실행"""

    # 1. Agent 가져오기 (Registry에서)
    agent = agent_registry.get_agent_instance("diet_agent")
    if not agent:
        agent = agent_registry.create_agent("diet_agent")

        # 2. Agent 초기화 (Checkpoint 전략에 따라)
        if checkpoint_strategy.should_use_checkpoint("diet_agent"):
            checkpointer = await checkpoint_strategy.get_checkpointer("diet_agent")
            await agent.initialize(llm, checkpointer)
        else:
            await agent.initialize(llm, None)  # Stateless

    # 3. SupervisorState → Agent Input 변환
    task = state["plan"][state["current_step"]]
    context = {
        "user_id": state.get("user_id"),
        "session_id": state.get("thread_id")
    }

    # 4. Agent 실행
    thread_id = f"{state['thread_id']}_{agent.agent_id}"  # 고유 thread_id
    result = await agent.execute(task, context, thread_id)

    # 5. Agent Result → SupervisorState 변환
    updated_plan = state["plan"].copy()
    updated_plan[state["current_step"]]["result"] = result
    updated_plan[state["current_step"]]["status"] = "completed"

    return {
        "plan": updated_plan,
        "current_step": state["current_step"] + 1,
        "aggregated_data": {
            **state.get("aggregated_data", {}),
            agent.agent_id: result
        }
    }
```

#### 방식 2: Direct Integration (대안)

```python
# Agent를 Supervisor의 서브그래프로 직접 통합
def build_supervisor_with_subgraphs():
    supervisor = StateGraph(SupervisorState)

    # Agent를 서브그래프로 추가
    diet_agent = DietAgent()
    diet_graph = diet_agent.build_graph(llm)

    # 서브그래프를 노드로 추가
    supervisor.add_node("diet_subgraph", diet_graph.compile())

    return supervisor.compile(checkpointer=checkpointer)
```

---

## 4. 실행 시나리오 예시

### 시나리오: "다이어트 계획 만들어줘"

```
1. User → WebSocket → "다이어트 계획 만들어줘"

2. Supervisor (Planner Node)
   → Plan 생성: [
       {"agent": "diet_agent", "task": "analyze_user"},
       {"agent": "diet_agent", "task": "create_meal_plan"},
       {"agent": "workout_agent", "task": "create_exercise_plan"},
       {"agent": "schedule_agent", "task": "integrate_schedule"}
     ]

3. Supervisor (Router Node)
   → current_step: 0
   → route: "diet_agent"

4. DietAgent 실행
   → build_graph() 로 LangGraph 생성
   → 노드 실행: analyze → plan → nutrition → output
   → Checkpoint 저장 (AUTO mode)
   → 결과 반환

5. Supervisor (State Update)
   → plan[0]["status"] = "completed"
   → current_step: 1
   → route: "diet_agent" (continue)

6. DietAgent 실행 (이어서)
   → 기존 checkpoint에서 재개
   → create_meal_plan 실행
   → 결과 반환

7. Supervisor (Router Node)
   → current_step: 2
   → route: "workout_agent"

8. WorkoutAgent 실행
   → 새로운 LangGraph 인스턴스
   → diet 결과 참조
   → 운동 계획 생성

9. Supervisor (Aggregator Node)
   → 모든 Agent 결과 종합
   → final_result 생성

10. WebSocket → User
    → "다이어트와 운동 계획이 완성되었습니다..."
```

---

## 5. State 관리 구조

### 5.1 계층적 State 관리

```
┌─────────────────────────────────┐
│      SupervisorState            │ ← PostgreSQL에 저장
│  thread_id: "session_123"       │
│  - messages: [...]              │
│  - plan: [...]                  │
│  - aggregated_data: {}          │
└─────────────────────────────────┘
         │ 참조
         ▼
┌─────────────────────────────────┐
│      DietAgentState             │ ← 선택적 PostgreSQL 저장
│  thread_id: "session_123_diet"  │
│  - user_profile: {}             │
│  - meal_plan: {}                │
│  - nutritional_summary: {}      │
└─────────────────────────────────┘
```

### 5.2 Checkpoint 저장 패턴

```python
# Supervisor Checkpoint (항상)
supervisor_checkpoint = {
    "thread_id": "session_123",
    "checkpoint": SupervisorState,
    "saved_at": "2025-11-05T10:00:00"
}

# Agent Checkpoint (선택적)
diet_checkpoint = {
    "thread_id": "session_123_diet",
    "checkpoint": DietAgentState,
    "saved_at": "2025-11-05T10:00:05"
}

# Stateless Agent (저장 안 함)
notification_agent = No checkpoint
```

---

## 6. 의존성 관리 및 병렬 실행

### 6.1 의존성 정의

```python
# Agent 의존성 등록
dependency_resolver.add_agent("diet_agent", [])
dependency_resolver.add_agent("workout_agent", ["diet_agent"])
dependency_resolver.add_agent("schedule_agent", ["diet_agent", "workout_agent"])
dependency_resolver.add_agent("notification_agent", ["schedule_agent"])
```

### 6.2 실행 계획 생성

```python
execution_plan = dependency_resolver.create_execution_plan()
# 결과:
# parallel_groups: [
#     ["diet_agent"],                    # Level 0: 독립 실행
#     ["workout_agent"],                 # Level 1: diet 완료 후
#     ["schedule_agent"],                # Level 2: workout 완료 후
#     ["notification_agent"]             # Level 3: schedule 완료 후
# ]
```

### 6.3 Supervisor의 병렬 실행

```python
async def executor_node(state: SupervisorState):
    """의존성을 고려한 병렬 Agent 실행"""

    plan = state["plan"]
    execution_plan = dependency_resolver.create_execution_plan(
        [task["agent"] for task in plan]
    )

    for parallel_group in execution_plan.parallel_groups:
        # 같은 레벨의 Agent들은 병렬 실행
        tasks = []
        for agent_id in parallel_group:
            wrapper = get_agent_wrapper(agent_id)
            tasks.append(wrapper(state))

        results = await asyncio.gather(*tasks)

        # State 업데이트
        for result in results:
            state = merge_state(state, result)

    return state
```

---

## 7. 핵심 차이점 정리

### 7.1 이전 (Simple Function)

```python
# Agent = 단순 함수
async def diet_agent_node(state):
    # 단순 로직
    return {"plan": updated_plan}

# Supervisor가 모든 것을 관리
workflow.add_node("diet_agent", diet_agent_node)
```

### 7.2 현재 (LangGraph Agent)

```python
# Agent = 복잡한 LangGraph
class DietAgent(BaseAgent):
    def build_graph(self):
        # 복잡한 workflow
        workflow = StateGraph(DietAgentState)
        workflow.add_node("analyze", ...)
        workflow.add_node("plan", ...)
        return workflow

# Supervisor는 조율만, Agent가 자체 workflow 실행
async def diet_agent_wrapper(state):
    agent = DietAgent()
    return await agent.execute(...)
```

---

## 8. 장점

1. **확장성**: 10+ Agent 쉽게 추가
2. **복잡성 관리**: 각 Agent가 독립적 복잡도 관리
3. **재사용성**: Agent를 다른 시스템에서도 사용 가능
4. **유연성**: Agent별 Checkpoint 전략
5. **병렬성**: 의존성 기반 자동 병렬 실행
6. **유지보수성**: Agent별 독립적 테스트/배포

---

## 9. 구현 로드맵

### Phase 1: 기반 구조 (완료 ✅)
- BaseAgent 클래스
- AgentRegistry
- CheckpointStrategy
- DependencyResolver

### Phase 2: Supervisor 통합 (다음 단계)
- Agent Wrapper 구현
- Supervisor Graph 수정
- Executor Node 업그레이드

### Phase 3: Agent 마이그레이션
- 각 Agent를 BaseAgent 기반으로 변환
- LangGraph workflow 구현
- 테스트 및 검증

### Phase 4: 최적화
- 병렬 실행 구현
- Checkpoint 전략 튜닝
- 모니터링 추가

---

## 10. FAQ

**Q: Supervisor 없이 Agent만으로 동작 가능한가?**
A: 가능하지만 권장하지 않음. Supervisor가 전체 조율을 담당해야 일관성 유지.

**Q: Agent가 다른 Agent를 직접 호출할 수 있나?**
A: 가능하지만 의존성은 Supervisor를 통해 관리하는 것이 좋음.

**Q: 모든 Agent가 LangGraph를 사용해야 하나?**
A: 아님. 단순한 Agent는 기존 함수 방식 유지 가능.

**Q: Checkpoint가 너무 많아지지 않나?**
A: CheckpointStrategy로 관리. 대부분 Agent는 Stateless로 운영.

---

**작성 완료일**: 2025-11-05
**버전**: 1.0
**문서 위치**: `reports/supervisor/SYSTEM_ARCHITECTURE_OVERVIEW_251105.md`