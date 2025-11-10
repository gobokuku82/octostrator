# Cognitive-Execute Supervisor Separation Architecture

**작성일**: 2025-11-05
**작성자**: AI Assistant
**목적**: Cognitive(인지/계획)와 Execute(실행) Supervisor 분리 설계

---

## 1. 핵심 개념

### 1.1 왜 분리가 필요한가?

**현재 문제점 (단일 Supervisor)**
```python
# 모든 것을 하나의 Graph에서 처리
- 계획 수립
- 의도 파악
- 실행 관리
- 상태 추적
- 결과 종합
→ 복잡도 폭발, 유지보수 어려움
```

**분리의 장점**
```python
Cognitive Supervisor:
- 의도 파악과 계획에 집중
- LLM 호출 최적화
- 빠른 응답

Execute Supervisor:
- 실행과 모니터링에 집중
- Agent 오케스트레이션
- State 관리 최적화
```

### 1.2 역할 분담

```
User Request
     │
     ▼
┌─────────────────────────┐
│  COGNITIVE SUPERVISOR   │ ← 생각하는 역할
│  - Intent Analysis      │
│  - Planning             │
│  - TODO Generation      │
│  - Decision Making      │
└───────────┬─────────────┘
            │ TODO List
            ▼
┌─────────────────────────┐
│   EXECUTE SUPERVISOR    │ ← 실행하는 역할
│  - Task Execution       │
│  - Agent Management     │
│  - Progress Tracking    │
│  - Error Handling       │
└─────────────────────────┘
```

---

## 2. Dual Graph Architecture

### 2.1 Two Graphs vs One Graph

**✅ Two Graphs 권장 (분리 추천)**

```python
# 장점
1. 명확한 책임 분리
2. 독립적 확장 가능
3. 각각 최적화 가능
4. 재사용성 높음
5. 테스트 용이

# 단점
1. Graph 간 통신 오버헤드
2. State 동기화 필요
```

**❌ Single Graph (비추천)**
```python
# 장점
1. 단순한 State 관리
2. 직접적인 노드 연결

# 단점
1. 복잡도 증가
2. 유지보수 어려움
3. 재사용 불가능
```

### 2.2 Dual Graph 구현

```python
# backend/app/octostrator/supervisor/cognitive_supervisor.py
def build_cognitive_supervisor(checkpointer):
    """인지/계획 Supervisor Graph"""
    workflow = StateGraph(CognitiveState)

    # Cognitive 노드들
    workflow.add_node("intent_analyzer", analyze_intent_node)
    workflow.add_node("context_builder", build_context_node)
    workflow.add_node("planner", create_plan_node)
    workflow.add_node("todo_generator", generate_todos_node)
    workflow.add_node("validator", validate_plan_node)

    # 흐름 정의
    workflow.add_edge(START, "intent_analyzer")
    workflow.add_edge("intent_analyzer", "context_builder")
    workflow.add_edge("context_builder", "planner")
    workflow.add_edge("planner", "todo_generator")
    workflow.add_edge("todo_generator", "validator")
    workflow.add_edge("validator", END)

    return workflow.compile(checkpointer=checkpointer)

# backend/app/octostrator/supervisor/execute_supervisor.py
def build_execute_supervisor(checkpointer):
    """실행 Supervisor Graph"""
    workflow = StateGraph(ExecuteState)

    # Execute 노드들
    workflow.add_node("todo_executor", execute_todo_node)
    workflow.add_node("agent_runner", run_agent_node)
    workflow.add_node("progress_tracker", track_progress_node)
    workflow.add_node("error_handler", handle_error_node)
    workflow.add_node("result_aggregator", aggregate_results_node)

    # 조건부 흐름
    workflow.add_conditional_edges(
        "todo_executor",
        check_todo_status,
        {
            "execute": "agent_runner",
            "skip": "todo_executor",
            "complete": "result_aggregator",
            "error": "error_handler"
        }
    )

    return workflow.compile(checkpointer=checkpointer)
```

---

## 3. TODO Management State

### 3.1 TODO State 정의

```python
from enum import Enum
from typing import TypedDict, List, Optional, Dict, Any
from datetime import datetime

class TodoStatus(Enum):
    """TODO 상태"""
    PENDING = "pending"      # 대기 중
    IN_PROGRESS = "in_progress"  # 실행 중
    COMPLETED = "completed"  # 완료
    FAILED = "failed"       # 실패
    SKIPPED = "skipped"     # 건너뜀
    BLOCKED = "blocked"     # 의존성 대기

class TodoPriority(Enum):
    """TODO 우선순위"""
    CRITICAL = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4

class TodoItem(TypedDict):
    """개별 TODO 항목"""
    id: str                          # 고유 ID
    title: str                       # 제목
    description: str                 # 상세 설명
    agent: str                       # 실행할 Agent
    task_type: str                   # 작업 유형
    params: Dict[str, Any]          # 파라미터
    dependencies: List[str]          # 의존하는 TODO ID들
    status: TodoStatus              # 상태
    priority: TodoPriority          # 우선순위

    # 실행 정보
    created_at: str
    started_at: Optional[str]
    completed_at: Optional[str]

    # 결과
    result: Optional[Dict[str, Any]]
    error: Optional[str]

    # 수정 추적
    version: int                    # 수정 버전
    modified_by: Optional[str]      # 수정자 (user/system)
    modification_reason: Optional[str]

class TodoManagementState(TypedDict):
    """TODO 관리 State"""
    todos: List[TodoItem]           # TODO 목록
    execution_order: List[str]      # 실행 순서 (TODO ID)
    current_todo_id: Optional[str]  # 현재 실행 중인 TODO
    completed_todos: List[str]      # 완료된 TODO ID
    failed_todos: List[str]         # 실패한 TODO ID

    # 진행률
    total_count: int
    completed_count: int
    progress_percentage: float

    # 수정 관리
    modification_history: List[Dict]  # 수정 이력
    allow_modifications: bool         # 실행 중 수정 허용 여부
```

### 3.2 TODO 관리 기능

```python
class TodoManager:
    """TODO 생성, 수정, 실행 관리"""

    def create_todos_from_plan(self, plan: Dict) -> List[TodoItem]:
        """계획에서 TODO 생성"""
        todos = []
        for idx, step in enumerate(plan["steps"]):
            todo = TodoItem(
                id=f"todo_{uuid.uuid4().hex[:8]}",
                title=step["title"],
                description=step["description"],
                agent=step["agent"],
                task_type=step["task_type"],
                params=step.get("params", {}),
                dependencies=step.get("dependencies", []),
                status=TodoStatus.PENDING,
                priority=TodoPriority(step.get("priority", 3)),
                created_at=datetime.now().isoformat(),
                version=1
            )
            todos.append(todo)
        return todos

    def modify_todo(
        self,
        todo_id: str,
        modifications: Dict,
        reason: str = "User requested"
    ) -> TodoItem:
        """TODO 수정 (실행 중에도 가능)"""
        todo = self.get_todo(todo_id)

        # 수정 가능 여부 확인
        if todo["status"] == TodoStatus.COMPLETED:
            raise ValueError("Cannot modify completed TODO")

        # 수정 적용
        for key, value in modifications.items():
            if key in todo:
                todo[key] = value

        # 버전 증가
        todo["version"] += 1
        todo["modified_by"] = "user"
        todo["modification_reason"] = reason

        # 수정 이력 저장
        self.save_modification_history(todo_id, modifications, reason)

        return todo

    def reorder_todos(self, new_order: List[str]):
        """TODO 순서 변경"""
        # 의존성 검증
        if not self.validate_dependencies(new_order):
            raise ValueError("Invalid order: dependency violation")

        self.execution_order = new_order

    def insert_todo(self, todo: TodoItem, position: int):
        """TODO 중간 삽입"""
        self.todos.insert(position, todo)
        self.recalculate_dependencies()

    def remove_todo(self, todo_id: str):
        """TODO 제거"""
        todo = self.get_todo(todo_id)

        # 의존성 업데이트
        for other_todo in self.todos:
            if todo_id in other_todo["dependencies"]:
                other_todo["dependencies"].remove(todo_id)

        self.todos.remove(todo)
```

---

## 4. State 연결 구조

### 4.1 Cognitive State

```python
class CognitiveState(TypedDict):
    """인지/계획 Supervisor State"""
    # Input
    messages: List[BaseMessage]
    intent: Dict[str, Any]
    context: Dict[str, Any]

    # Planning
    analysis_result: Dict[str, Any]
    suggested_plan: Dict[str, Any]

    # TODO Management
    todo_management: TodoManagementState

    # Decision
    confidence_score: float
    requires_human_review: bool
    alternative_plans: List[Dict]
```

### 4.2 Execute State

```python
class ExecuteState(TypedDict):
    """실행 Supervisor State"""
    # TODO Management (from Cognitive)
    todo_management: TodoManagementState

    # Execution
    current_agent: Optional[str]
    agent_states: Dict[str, Any]

    # Progress
    execution_log: List[Dict]
    performance_metrics: Dict

    # Results
    partial_results: Dict[str, Any]
    final_result: Optional[Dict]
```

### 4.3 State 전달 메커니즘

```python
async def handoff_to_execute_supervisor(cognitive_state: CognitiveState):
    """Cognitive → Execute 전달"""

    # TODO Management State 전달
    execute_input = {
        "todo_management": cognitive_state["todo_management"],
        "context": cognitive_state["context"],
        "session_id": cognitive_state.get("session_id")
    }

    # Execute Supervisor 실행
    execute_supervisor = build_execute_supervisor(checkpointer)
    result = await execute_supervisor.ainvoke(
        execute_input,
        config={"configurable": {"thread_id": f"{session_id}_execute"}}
    )

    return result
```

---

## 5. 실행 시나리오

### 5.1 초기 계획 수립

```
User: "다이어트와 운동 계획 만들어줘"
         │
         ▼
[Cognitive Supervisor]
    ├─ Intent: CREATE_MULTIPLE_PLANS
    ├─ Context: user_profile, preferences
    │
    └─ Generate TODOs:
        1. TODO_001: Analyze user health status (diet_agent)
        2. TODO_002: Create meal plan (diet_agent)
        3. TODO_003: Design workout routine (workout_agent)
        4. TODO_004: Integrate schedule (schedule_agent)
        5. TODO_005: Send notification (notification_agent)
         │
         ▼ Handoff
[Execute Supervisor]
    └─ Execute TODOs sequentially/parallel
        ├─ TODO_001 ✓
        ├─ TODO_002 ✓
        └─ ...
```

### 5.2 실행 중 수정

```
User: "운동 강도 좀 낮춰줘" (TODO_003 실행 중)
         │
         ▼
[Cognitive Supervisor]
    ├─ Intent: MODIFY_IN_PROGRESS
    ├─ Target: TODO_003
    │
    └─ Modify TODO:
        TODO_003.params.intensity = "low"
        TODO_003.version = 2
         │
         ▼ Update Signal
[Execute Supervisor]
    └─ Reload TODO_003 with new params
        └─ Continue execution with modified params
```

### 5.3 동적 TODO 추가

```
User: "영양제 추천도 추가해줘" (실행 중)
         │
         ▼
[Cognitive Supervisor]
    └─ Create new TODO:
        TODO_006: Recommend supplements (diet_agent)
        Insert after TODO_002
         │
         ▼ Update Signal
[Execute Supervisor]
    └─ Update execution queue
        └─ Execute TODO_006 after TODO_002
```

---

## 6. 통신 패턴

### 6.1 Bidirectional Communication

```python
class SupervisorCommunicator:
    """두 Supervisor 간 통신"""

    def __init__(self):
        self.message_queue = asyncio.Queue()
        self.state_sync = {}

    async def cognitive_to_execute(self, message: Dict):
        """Cognitive → Execute 메시지"""
        await self.message_queue.put({
            "from": "cognitive",
            "to": "execute",
            "type": message["type"],
            "payload": message["payload"],
            "timestamp": datetime.now().isoformat()
        })

    async def execute_to_cognitive(self, message: Dict):
        """Execute → Cognitive 피드백"""
        # 실행 중 문제 발생 시 Cognitive에 알림
        if message["type"] == "ERROR":
            await self.cognitive_supervisor.handle_execution_error(
                message["payload"]
            )
        elif message["type"] == "REQUIRES_DECISION":
            decision = await self.cognitive_supervisor.make_decision(
                message["payload"]
            )
            return decision
```

### 6.2 Event-Driven Updates

```python
class TodoEventEmitter:
    """TODO 상태 변경 이벤트"""

    @event.on("todo.status.changed")
    async def on_status_change(self, todo_id: str, new_status: TodoStatus):
        # UI 업데이트
        await self.notify_ui({
            "event": "todo_status_update",
            "todo_id": todo_id,
            "status": new_status.value
        })

        # Cognitive Supervisor 알림
        if new_status == TodoStatus.FAILED:
            await self.cognitive_supervisor.handle_todo_failure(todo_id)

    @event.on("todo.modified")
    async def on_modification(self, todo_id: str, changes: Dict):
        # Execute Supervisor에 변경 사항 전달
        await self.execute_supervisor.apply_todo_changes(todo_id, changes)
```

---

## 7. 구현 예시

### 7.1 Cognitive Supervisor 노드

```python
async def generate_todos_node(state: CognitiveState) -> Dict:
    """TODO 생성 노드"""

    plan = state["suggested_plan"]
    todo_manager = TodoManager()

    # Plan → TODOs 변환
    todos = todo_manager.create_todos_from_plan(plan)

    # 의존성 분석
    dependency_resolver = DependencyResolver()
    for todo in todos:
        dependency_resolver.add_agent(todo["id"], todo["dependencies"])

    # 실행 순서 결정
    execution_order = dependency_resolver.topological_sort()

    # TodoManagementState 생성
    todo_state = TodoManagementState(
        todos=todos,
        execution_order=execution_order,
        current_todo_id=None,
        completed_todos=[],
        failed_todos=[],
        total_count=len(todos),
        completed_count=0,
        progress_percentage=0.0,
        modification_history=[],
        allow_modifications=True
    )

    return {"todo_management": todo_state}
```

### 7.2 Execute Supervisor 노드

```python
async def execute_todo_node(state: ExecuteState) -> Dict:
    """TODO 실행 노드"""

    todo_mgmt = state["todo_management"]
    current_idx = todo_mgmt.get("current_index", 0)

    if current_idx >= len(todo_mgmt["execution_order"]):
        return {"status": "complete"}

    # 현재 TODO 가져오기
    todo_id = todo_mgmt["execution_order"][current_idx]
    todo = next(t for t in todo_mgmt["todos"] if t["id"] == todo_id)

    # 수정 사항 확인
    if todo["version"] > 1:
        logger.info(f"Executing modified TODO: {todo_id} (v{todo['version']})")

    # Agent 실행
    agent = agent_registry.get_agent(todo["agent"])
    result = await agent.execute(
        task=todo["task_type"],
        params=todo["params"],
        context=state.get("context", {})
    )

    # TODO 상태 업데이트
    todo["status"] = TodoStatus.COMPLETED
    todo["completed_at"] = datetime.now().isoformat()
    todo["result"] = result

    # 진행률 업데이트
    todo_mgmt["completed_count"] += 1
    todo_mgmt["progress_percentage"] = (
        todo_mgmt["completed_count"] / todo_mgmt["total_count"] * 100
    )

    return {
        "todo_management": todo_mgmt,
        "current_index": current_idx + 1
    }
```

---

## 8. 장점과 트레이드오프

### 8.1 장점

1. **명확한 관심사 분리**
   - Cognitive: 생각과 계획
   - Execute: 실행과 모니터링

2. **유연한 수정**
   - 실행 중 TODO 수정 가능
   - 동적 TODO 추가/제거

3. **향상된 사용자 경험**
   - 빠른 초기 응답 (Cognitive)
   - 실시간 진행 상황 (Execute)

4. **확장성**
   - 각 Supervisor 독립 확장
   - 새로운 기능 쉽게 추가

### 8.2 트레이드오프

1. **복잡도 증가**
   - 두 개의 Graph 관리
   - State 동기화 필요

2. **통신 오버헤드**
   - Graph 간 메시지 전달
   - 이벤트 처리

3. **디버깅 복잡성**
   - 분산된 로직
   - State 추적 어려움

---

## 9. 권장 사항

### ✅ 이런 경우 분리 추천

- 복잡한 계획 수립 필요
- 실행 중 수정 빈번
- 다양한 Agent 관리
- 긴 실행 시간

### ❌ 이런 경우 단일 Graph 유지

- 단순한 작업
- 수정 불필요
- Agent 수 적음
- 빠른 실행

---

## 10. 마이그레이션 계획

### Phase 1: TODO Management 구현
- TodoItem, TodoManagementState 정의
- TodoManager 클래스 구현

### Phase 2: Cognitive Supervisor 구현
- Intent 분석 강화
- TODO 생성 로직
- 수정 처리

### Phase 3: Execute Supervisor 구현
- TODO 실행 엔진
- 진행 상황 추적
- 에러 처리

### Phase 4: 통합 및 최적화
- Graph 간 통신
- 이벤트 시스템
- 성능 최적화

---

**작성 완료일**: 2025-11-05
**버전**: 1.0
**문서 위치**: `reports/supervisor/COGNITIVE_EXECUTE_SEPARATION_251105.md`