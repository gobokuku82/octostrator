# 협동 메커니즘 실제 예시 코드

**작성일**: 2025-11-05
**작성자**: AI Assistant
**목적**: 실제 코드로 보는 컴포넌트 간 협동

---

## 1. 전체 실행 예시

### 1.1 Main Orchestration

```python
# backend/app/main_orchestrator.py

async def handle_user_request(user_message: str, session_id: str):
    """사용자 요청 처리 - 전체 오케스트레이션"""

    # ═══════════════════════════════════════════════
    # STEP 1: Cognitive Supervisor - 계획 수립
    # ═══════════════════════════════════════════════

    cognitive_supervisor = build_cognitive_supervisor(checkpointer)

    cognitive_result = await cognitive_supervisor.ainvoke(
        {
            "messages": [HumanMessage(content=user_message)],
            "session_id": session_id
        },
        config={"configurable": {"thread_id": f"{session_id}_cognitive"}}
    )

    plan = cognitive_result["plan"]
    # plan = {
    #     "goal": "다이어트와 운동 계획",
    #     "steps": [
    #         {"action": "analyze_health", "agent": "diet"},
    #         {"action": "create_meal_plan", "agent": "diet"},
    #         {"action": "design_workout", "agent": "workout"}
    #     ]
    # }

    # ═══════════════════════════════════════════════
    # STEP 2: TodoAgent - TODO 변환 및 HITL
    # ═══════════════════════════════════════════════

    todo_agent = agent_registry.get_agent("todo_agent")

    todo_result = await todo_agent.execute(
        task={"type": "convert_plan", "plan": plan},
        context={"session_id": session_id, "user_id": user_id}
    )

    # HITL - Human Approval
    if todo_result["requires_approval"]:
        # WebSocket으로 사용자에게 TODO 표시
        await websocket.send_json({
            "type": "todo_review",
            "todos": todo_result["todos"]
        })

        # 사용자 응답 대기
        user_response = await wait_for_user_response(timeout=300)

        # 수정사항 적용
        if user_response["action"] == "modify":
            todo_result = await todo_agent.execute(
                task={"type": "apply_modifications", "modifications": user_response["changes"]},
                context={"session_id": session_id}
            )

    todos = todo_result["todos"]
    # todos = [
    #     TodoItem(id="todo_001", agent="diet_agent", task="analyze_health"),
    #     TodoItem(id="todo_002", agent="diet_agent", task="create_meal_plan"),
    #     TodoItem(id="todo_003", agent="workout_agent", task="design_workout")
    # ]

    # ═══════════════════════════════════════════════
    # STEP 3: Execute Supervisor - 실행 관리
    # ═══════════════════════════════════════════════

    execute_supervisor = build_execute_supervisor(checkpointer)

    execute_result = await execute_supervisor.ainvoke(
        {
            "todos": todos,
            "session_id": session_id
        },
        config={"configurable": {"thread_id": f"{session_id}_execute"}}
    )

    return execute_result["final_result"]
```

---

## 2. Execute Supervisor의 Agent 실행

### 2.1 Agent 오케스트레이션 상세

```python
# backend/app/octostrator/supervisor/execute_supervisor.py

async def execute_agents_node(state: ExecuteState) -> Dict:
    """Agent들을 오케스트레이션하여 실행"""

    todos = state["todos"]
    completed_results = {}

    # ═══════════════════════════════════════════════
    # 의존성 기반 실행 그룹 생성
    # ═══════════════════════════════════════════════

    execution_groups = calculate_execution_groups(todos)
    # execution_groups = [
    #     ["todo_001"],  # Level 0: 의존성 없음
    #     ["todo_002"],  # Level 1: todo_001에 의존
    #     ["todo_003"]   # Level 2: todo_002에 의존
    # ]

    # ═══════════════════════════════════════════════
    # 그룹별 순차 실행 (그룹 내에서는 병렬)
    # ═══════════════════════════════════════════════

    for group_level, todo_ids in enumerate(execution_groups):
        print(f"\n=== Executing Level {group_level} ===")

        # 같은 레벨의 TODO들은 병렬 실행
        parallel_tasks = []

        for todo_id in todo_ids:
            todo = get_todo_by_id(todos, todo_id)

            # 실행할 Agent 준비
            agent_id = todo["agent"]
            task = todo["task"]
            params = todo["params"]

            # 의존성 데이터 수집
            dependency_data = {}
            for dep_id in todo.get("dependencies", []):
                if dep_id in completed_results:
                    dependency_data[dep_id] = completed_results[dep_id]

            # Agent 실행 태스크 생성
            execution_task = asyncio.create_task(
                execute_single_agent(
                    agent_id=agent_id,
                    task=task,
                    params=params,
                    context={
                        "session_id": state["session_id"],
                        "dependencies": dependency_data
                    }
                )
            )

            parallel_tasks.append((todo_id, execution_task))

        # 병렬 실행 대기
        for todo_id, task in parallel_tasks:
            result = await task
            completed_results[todo_id] = result
            print(f"✓ Completed: {todo_id}")

    return {"completed_results": completed_results}
```

### 2.2 단일 Agent 실행

```python
async def execute_single_agent(agent_id: str, task: str, params: Dict, context: Dict) -> Dict:
    """단일 Agent 실행"""

    print(f"Executing {agent_id}.{task}")

    # ═══════════════════════════════════════════════
    # Agent 인스턴스 가져오기
    # ═══════════════════════════════════════════════

    agent = agent_registry.get_agent(agent_id)

    if not agent:
        # Agent가 없으면 생성
        agent = agent_registry.create_agent(agent_id)

        # Checkpoint 전략에 따라 초기화
        if checkpoint_strategy.should_use_checkpoint(agent_id):
            checkpointer = await create_checkpointer()
            await agent.initialize(llm, checkpointer)
        else:
            await agent.initialize(llm, None)

    # ═══════════════════════════════════════════════
    # Agent 실행
    # ═══════════════════════════════════════════════

    result = await agent.execute(
        task={"type": task, "params": params},
        context=context,
        thread_id=f"{context['session_id']}_{agent_id}"
    )

    return result
```

---

## 3. Agent 간 데이터 전달

### 3.1 DietAgent → WorkoutAgent 협동

```python
# DietAgent 결과
diet_result = {
    "todo_id": "todo_002",
    "agent": "diet_agent",
    "task": "create_meal_plan",
    "result": {
        "daily_calories": 2000,
        "protein_grams": 150,
        "meal_schedule": ["8am", "12pm", "6pm"],
        "energy_distribution": {
            "morning": 0.3,
            "afternoon": 0.4,
            "evening": 0.3
        }
    }
}

# WorkoutAgent가 DietAgent 결과를 활용
workout_context = {
    "dependencies": {
        "todo_002": diet_result  # DietAgent 결과 전달
    }
}

# WorkoutAgent 실행 시
class WorkoutAgent(BaseAgent):
    async def execute(self, task, context):
        # DietAgent 결과 참조
        diet_data = context["dependencies"].get("todo_002")

        if diet_data:
            calories = diet_data["result"]["daily_calories"]
            energy_dist = diet_data["result"]["energy_distribution"]

            # 칼로리와 에너지 분포에 맞춰 운동 계획
            workout_plan = self.design_workout_based_on_diet(
                target_calories_burn=calories * 0.2,  # 20% 소모 목표
                energy_levels=energy_dist
            )
        else:
            # 기본 운동 계획
            workout_plan = self.design_default_workout()

        return {"workout_plan": workout_plan}
```

### 3.2 Multiple Agent 협동

```python
# ScheduleAgent가 Diet과 Workout 결과 모두 활용

schedule_context = {
    "dependencies": {
        "todo_002": diet_result,    # DietAgent 결과
        "todo_003": workout_result   # WorkoutAgent 결과
    }
}

class ScheduleAgent(BaseAgent):
    async def execute(self, task, context):
        diet_data = context["dependencies"].get("todo_002")
        workout_data = context["dependencies"].get("todo_003")

        # 식사 시간
        meal_times = diet_data["result"]["meal_schedule"]

        # 운동 시간 (식사 2시간 후)
        workout_times = []
        for meal_time in meal_times[:-1]:  # 저녁 제외
            workout_time = add_hours(meal_time, 2)
            workout_times.append(workout_time)

        # 통합 일정
        integrated_schedule = {
            "meals": meal_times,
            "workouts": workout_times,
            "reminders": generate_reminders(meal_times, workout_times)
        }

        return {"schedule": integrated_schedule}
```

---

## 4. 실시간 진행 상황 공유

### 4.1 Progress Broadcasting

```python
# Execute Supervisor가 진행 상황을 브로드캐스트

async def broadcast_progress(state: ExecuteState):
    """모든 관련 컴포넌트에 진행 상황 전달"""

    progress = {
        "total_todos": len(state["todos"]),
        "completed": len(state["completed_results"]),
        "current": state.get("current_todo_id"),
        "percentage": (len(state["completed_results"]) / len(state["todos"])) * 100
    }

    # TodoAgent에 알림 (모니터링용)
    await todo_agent.update_progress(progress)

    # WebSocket으로 사용자에게 전송
    await websocket.send_json({
        "type": "progress_update",
        "data": progress
    })

    # Memory에 저장 (히스토리용)
    await memory_manager.save_progress(state["session_id"], progress)
```

### 4.2 Error Handling 협동

```python
async def handle_agent_error(error: Exception, todo: TodoItem, state: ExecuteState):
    """Agent 실행 에러 시 협동 처리"""

    error_info = {
        "todo_id": todo["id"],
        "agent": todo["agent"],
        "error": str(error),
        "timestamp": datetime.now().isoformat()
    }

    # 1. TodoAgent에 에러 알림 (재시도 결정)
    retry_decision = await todo_agent.handle_error(error_info)

    if retry_decision["action"] == "retry":
        # 2. 재시도
        return await execute_single_agent(
            todo["agent"],
            todo["task"],
            todo["params"],
            state["context"]
        )

    elif retry_decision["action"] == "skip":
        # 3. 건너뛰기 - 의존 Agent들에 알림
        dependent_todos = get_dependent_todos(todo["id"], state["todos"])

        for dep_todo in dependent_todos:
            # 의존성 제거 또는 대체 처리
            await adjust_dependency(dep_todo, todo["id"])

    elif retry_decision["action"] == "ask_user":
        # 4. 사용자에게 물어보기
        user_decision = await request_user_intervention(error_info)
        return await handle_user_decision(user_decision)
```

---

## 5. 실제 실행 로그 예시

```
=== User Request: "다이어트와 운동 계획 만들어줘" ===

[10:00:00] Cognitive Supervisor Started
[10:00:02] Plan Generated: 3 steps

[10:00:02] TodoAgent Started
[10:00:03] TODOs Created: 5 items
[10:00:03] HITL: Requesting user approval...
[10:00:15] HITL: User approved with 1 modification
[10:00:16] TODOs Finalized

[10:00:16] Execute Supervisor Started

=== Executing Level 0 (No dependencies) ===
[10:00:16] Executing diet_agent.analyze_health
[10:00:16] Executing user_agent.get_preferences
[10:00:18] ✓ Completed: todo_001
[10:00:18] ✓ Completed: todo_004

=== Executing Level 1 (Depends on Level 0) ===
[10:00:18] Executing diet_agent.create_meal_plan
    → Using: todo_001 results (health analysis)
[10:00:20] ✓ Completed: todo_002

=== Executing Level 2 (Depends on Level 1) ===
[10:00:20] Executing workout_agent.design_workout
    → Using: todo_002 results (meal plan)
[10:00:22] ✓ Completed: todo_003

=== Executing Level 3 (Depends on Level 2) ===
[10:00:22] Executing schedule_agent.integrate
    → Using: todo_002 results (meal plan)
    → Using: todo_003 results (workout plan)
[10:00:23] ✓ Completed: todo_005

[10:00:23] Execute Supervisor Completed
[10:00:23] Final Result Sent to User

=== Summary ===
Total Time: 23 seconds
TODOs Executed: 5
Success Rate: 100%
```

---

## 6. 핵심 포인트

### 협동의 3가지 패턴

1. **Sequential Handoff (순차 전달)**
   ```
   Cognitive → TodoAgent → Execute
   ```

2. **Parallel Coordination (병렬 조율)**
   ```
   Execute → [DietAgent, UserAgent] (동시 실행)
   ```

3. **Dependency Chain (의존성 체인)**
   ```
   DietAgent → WorkoutAgent → ScheduleAgent
   ```

### 데이터 공유 방식

- **Direct**: State를 통한 직접 전달
- **Indirect**: Execute Supervisor를 통한 간접 전달
- **Broadcast**: WebSocket/Event를 통한 브로드캐스트

### 에러 처리 협동

- **Local**: Agent 내부에서 처리
- **Escalate**: 상위 Supervisor로 전달
- **Coordinate**: 관련 Agent들과 조율

---

**작성 완료일**: 2025-11-05
**버전**: 1.0
**문서 위치**: `reports/supervisor/COLLABORATION_EXAMPLE_251105.md`