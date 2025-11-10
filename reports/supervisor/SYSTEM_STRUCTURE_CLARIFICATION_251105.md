# System Structure Clarification - 명확한 시스템 구조

**작성일**: 2025-11-05
**작성자**: AI Assistant
**목적**: Supervisor와 Agent 구조 명확화 및 협동 메커니즘 설명

---

## 1. 핵심 답변

### ❓ "Supervisor가 3개로 나뉘는가?"
**답: NO, Supervisor는 2개입니다.**

```
Supervisor (2개):
1. Cognitive Supervisor - 계획 수립
2. Execute Supervisor - 실행 관리

Agent (N개):
1. TodoAgent - TODO 관리 (특별한 Agent)
2. DietAgent - 식단 담당
3. WorkoutAgent - 운동 담당
... 10+ Domain Agents
```

### 📌 중요: TodoAgent는 Supervisor가 아닙니다!
- TodoAgent = 특별한 역할을 가진 **Agent**
- Supervisor = 전체 흐름을 **조율**하는 관제탑
- Agent = 특정 작업을 **수행**하는 실행자

---

## 2. 시스템 계층 구조

### 2.1 3-Layer Architecture

```
┌────────────────────────────────────────────┐
│         Layer 1: Planning Layer            │
│                                            │
│         [Cognitive Supervisor]             │
│         - 의도 파악                        │
│         - 계획 수립                        │
│         - 의사 결정                        │
└────────────────┬───────────────────────────┘
                 │ Plan
                 ▼
┌────────────────────────────────────────────┐
│       Layer 2: Management Layer            │
│                                            │
│            [TodoAgent]                     │
│         - TODO 생성                        │
│         - HITL 처리                        │
│         - 수정 관리                        │
└────────────────┬───────────────────────────┘
                 │ TODOs
                 ▼
┌────────────────────────────────────────────┐
│        Layer 3: Execution Layer            │
│                                            │
│         [Execute Supervisor]               │
│         - Agent 오케스트레이션             │
│         - 실행 관리                        │
│         - 에러 처리                        │
│                │                           │
│    ┌──────────┼──────────┐                │
│    ▼          ▼          ▼                │
│ [DietAgent] [WorkoutAgent] [ScheduleAgent] │
└────────────────────────────────────────────┘
```

### 2.2 실제 컴포넌트 관계

```python
# 계층별 역할

1. Cognitive Supervisor (LangGraph)
   - Role: Planner (계획자)
   - Input: User Message
   - Output: Plan

2. TodoAgent (LangGraph Agent)
   - Role: Manager (관리자)
   - Input: Plan from Cognitive
   - Output: Executable TODOs

3. Execute Supervisor (LangGraph)
   - Role: Orchestrator (지휘자)
   - Input: TODOs
   - Output: Execution Results

4. Domain Agents (LangGraph Agents)
   - Role: Executors (실행자)
   - Input: Individual TODO
   - Output: Task Result
```

---

## 3. 각 컴포넌트 구조화

### 3.1 Cognitive Supervisor 구조

```python
def build_cognitive_supervisor():
    workflow = StateGraph(CognitiveState)

    # Cognitive만의 노드
    workflow.add_node("analyze_intent", ...)    # 의도 분석
    workflow.add_node("retrieve_context", ...)   # 컨텍스트 조회
    workflow.add_node("generate_plan", ...)      # 계획 생성
    workflow.add_node("validate_plan", ...)      # 계획 검증

    # 흐름
    START → analyze_intent → retrieve_context → generate_plan → validate_plan → END

    return workflow.compile(checkpointer)
```

**Output:**
```python
plan = {
    "goal": "다이어트와 운동 계획",
    "steps": [
        {"action": "analyze_health", "agent": "diet"},
        {"action": "create_meal_plan", "agent": "diet"},
        {"action": "design_workout", "agent": "workout"}
    ]
}
```

### 3.2 TodoAgent 구조

```python
@register_agent("todo_agent")
class TodoAgent(BaseAgent):
    def build_graph(self):
        workflow = StateGraph(TodoAgentState)

        # TodoAgent만의 노드
        workflow.add_node("convert_plan_to_todos", ...)  # Plan → TODOs
        workflow.add_node("analyze_dependencies", ...)     # 의존성 분석
        workflow.add_node("request_human_approval", ...)   # HITL
        workflow.add_node("apply_modifications", ...)      # 수정 적용
        workflow.add_node("finalize_todos", ...)          # TODO 확정

        # HITL 조건부 흐름
        workflow.add_conditional_edges(
            "request_human_approval",
            check_approval,
            {
                "approved": "finalize_todos",
                "modified": "apply_modifications"
            }
        )

        return workflow.compile()
```

**Output:**
```python
todos = [
    TodoItem(id="todo_001", agent="diet_agent", task="analyze_health", ...),
    TodoItem(id="todo_002", agent="diet_agent", task="create_meal_plan", ...),
    TodoItem(id="todo_003", agent="workout_agent", task="design_workout", ...)
]
```

### 3.3 Execute Supervisor 구조

```python
def build_execute_supervisor():
    workflow = StateGraph(ExecuteState)

    # Execute만의 노드
    workflow.add_node("select_next_todos", ...)      # 다음 TODO 선택
    workflow.add_node("assign_to_agents", ...)       # Agent 할당
    workflow.add_node("monitor_execution", ...)      # 실행 모니터링
    workflow.add_node("handle_results", ...)         # 결과 처리
    workflow.add_node("aggregate_results", ...)      # 결과 종합

    # 실행 루프
    workflow.add_conditional_edges(
        "monitor_execution",
        check_completion,
        {
            "continue": "select_next_todos",
            "complete": "aggregate_results"
        }
    )

    return workflow.compile(checkpointer)
```

---

## 4. 실행 Agent들의 구동 방식

### 4.1 Agent 실행 메커니즘

```python
# Execute Supervisor의 agent 실행 노드

async def assign_to_agents_node(state: ExecuteState):
    """TODO를 해당 Agent에 할당하고 실행"""

    current_todos = state["current_todos"]
    results = []

    # 병렬 실행 가능한 TODO들 그룹화
    parallel_groups = group_by_dependencies(current_todos)

    for group in parallel_groups:
        # 같은 그룹 내 TODO들은 병렬 실행
        tasks = []
        for todo in group:
            agent_id = todo["agent"]

            # Agent 가져오기
            agent = agent_registry.get_agent(agent_id)

            # Agent 실행 (비동기)
            task = asyncio.create_task(
                agent.execute(
                    task=todo["task"],
                    params=todo["params"],
                    context=state["context"]
                )
            )
            tasks.append(task)

        # 병렬 실행 대기
        group_results = await asyncio.gather(*tasks)
        results.extend(group_results)

    return {"results": results}
```

### 4.2 개별 Agent 실행

```python
# DietAgent 예시
class DietAgent(BaseAgent):
    async def execute(self, task, params, context):
        """단일 작업 실행"""

        if task == "analyze_health":
            # 건강 분석 LangGraph 실행
            result = await self.health_analysis_graph.ainvoke({
                "user_data": params["user_data"]
            })

        elif task == "create_meal_plan":
            # 식단 생성 LangGraph 실행
            result = await self.meal_planning_graph.ainvoke({
                "calories": params["calories"],
                "preferences": params["preferences"]
            })

        return result
```

---

## 5. 협동 메커니즘

### 5.1 State 공유를 통한 협동

```python
# 공유 State 구조
SharedContext = {
    "session_id": "session_123",
    "user_profile": {...},

    # Cognitive → TodoAgent
    "plan": {...},

    # TodoAgent → Execute
    "todos": [...],
    "execution_order": [...],

    # Execute → Agents
    "current_task": {...},
    "previous_results": {...},

    # Agents → Execute
    "agent_results": {...},

    # 전체 공유
    "memory": {...},
    "progress": {...}
}
```

### 5.2 메시지 전달 패턴

```python
# 1. Cognitive → TodoAgent
cognitive_output = {
    "plan": plan,
    "context": context
}
todo_agent_input = cognitive_output

# 2. TodoAgent → Execute
todo_output = {
    "todos": todos,
    "execution_plan": execution_plan,
    "human_approved": True
}
execute_input = todo_output

# 3. Execute → Domain Agents
execute_dispatch = {
    "todo": current_todo,
    "context": shared_context,
    "dependencies": previous_results
}
agent_input = execute_dispatch

# 4. Domain Agents → Execute
agent_output = {
    "result": task_result,
    "status": "completed",
    "metadata": {...}
}
execute_receives = agent_output
```

### 5.3 Agent 간 협동

```python
# 의존성 기반 협동
dependencies = {
    "workout_agent": ["diet_agent"],  # workout은 diet 결과 필요
    "schedule_agent": ["diet_agent", "workout_agent"],  # 둘 다 필요
    "notification_agent": ["schedule_agent"]  # schedule 완료 후
}

# 데이터 전달
async def execute_with_dependencies(todo, completed_results):
    """의존성 있는 Agent 실행"""

    # 필요한 이전 결과 수집
    required_data = {}
    for dep in todo["dependencies"]:
        required_data[dep] = completed_results[dep]

    # Agent 실행 시 전달
    agent = agent_registry.get_agent(todo["agent"])
    result = await agent.execute(
        task=todo["task"],
        params=todo["params"],
        context={
            "dependencies": required_data,  # 이전 Agent 결과
            "shared": shared_context
        }
    )

    return result
```

---

## 6. 실제 실행 시나리오

### 6.1 전체 플로우

```
User: "다이어트와 운동 계획 만들어줘"
         │
         ▼
[1] Cognitive Supervisor
    - Intent: CREATE_MULTIPLE_PLANS
    - Plan: 3 steps (diet analysis, meal plan, workout)
         │
         ▼
[2] TodoAgent
    - Convert: Plan → 5 TODOs
    - HITL: User approves with modifications
    - Output: Final TODO list
         │
         ▼
[3] Execute Supervisor
    - TODO_001 → DietAgent (analyze_health)
    - TODO_002 → DietAgent (create_meal_plan)
    - TODO_003 → WorkoutAgent (design_workout) [waits for TODO_002]
    - TODO_004 → ScheduleAgent (integrate) [waits for TODO_003]
    - TODO_005 → NotificationAgent (notify) [waits for all]
         │
         ▼
[4] Results Aggregation
    - Combine all agent results
    - Generate final response
```

### 6.2 병렬 실행 예시

```python
# Execute Supervisor의 병렬 실행 관리

Execution Timeline:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

T0: Start
T1: [Parallel Group 1]
    - DietAgent.analyze_health()     ████░░░░
    - UserAgent.get_preferences()    ████░░░░

T2: [Parallel Group 2]
    - DietAgent.create_meal_plan()    ░░████░░
    - WorkoutAgent.analyze_fitness()  ░░████░░

T3: [Parallel Group 3]
    - WorkoutAgent.design_workout()   ░░░░████
    - ScheduleAgent.check_calendar()  ░░░░████

T4: [Sequential]
    - ScheduleAgent.integrate()       ░░░░░░██
    - NotificationAgent.send()        ░░░░░░░█

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 7. 핵심 정리

### 7.1 컴포넌트 역할

| 컴포넌트 | 유형 | 역할 | 책임 |
|----------|------|------|------|
| **Cognitive Supervisor** | LangGraph | 계획자 | 의도 파악, 계획 수립 |
| **TodoAgent** | LangGraph Agent | 관리자 | TODO 생성, HITL, 수정 |
| **Execute Supervisor** | LangGraph | 지휘자 | Agent 오케스트레이션 |
| **Domain Agents** | LangGraph Agents | 실행자 | 실제 작업 수행 |

### 7.2 데이터 흐름

```
User Message
    → Cognitive (Plan)
    → TodoAgent (TODOs)
    → Execute (Orchestration)
    → Agents (Execution)
    → Results
```

### 7.3 협동 방식

1. **수직적 협동**: Layer 간 State/Message 전달
2. **수평적 협동**: Agent 간 의존성 관리
3. **비동기 협동**: 병렬 실행과 동기화

---

## 8. FAQ

### Q: TodoAgent는 왜 Supervisor가 아닌가?
**A**: TodoAgent는 특정 작업(TODO 관리)을 수행하는 Agent입니다. Supervisor는 전체 흐름을 조율하는 역할이고, Agent는 특정 작업을 수행합니다.

### Q: Agent들이 서로 직접 통신하나?
**A**: 아닙니다. Execute Supervisor를 통해 간접적으로 통신합니다. Execute Supervisor가 의존성을 관리하고 결과를 전달합니다.

### Q: 왜 3개 Layer로 나누나?
**A**: 책임 분리와 확장성을 위해서입니다:
- Planning Layer: 전략적 결정
- Management Layer: 작업 관리와 사용자 상호작용
- Execution Layer: 실제 작업 수행

---

**작성 완료일**: 2025-11-05
**버전**: 1.0
**문서 위치**: `reports/supervisor/SYSTEM_STRUCTURE_CLARIFICATION_251105.md`