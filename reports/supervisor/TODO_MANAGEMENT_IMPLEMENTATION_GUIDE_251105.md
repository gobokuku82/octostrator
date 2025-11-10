# TODO Management Implementation Guide

**작성일**: 2025-11-05
**작성자**: AI Assistant
**목적**: TODO Management를 포함한 Dual Supervisor 구현 가이드

---

## 1. 실제 구현 코드

### 1.1 TODO Management State 구현

```python
# backend/app/octostrator/supervisor/states/todo_state.py
from typing import TypedDict, List, Optional, Dict, Any
from enum import Enum
import uuid
from datetime import datetime

class TodoStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    BLOCKED = "blocked"
    MODIFIED = "modified"  # 수정됨 표시

class TodoPriority(Enum):
    CRITICAL = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4

class TodoItem(TypedDict):
    """실행 가능한 TODO 항목"""
    # 기본 정보
    id: str
    title: str
    description: str

    # 실행 정보
    agent: str
    task_type: str
    params: Dict[str, Any]

    # 상태 관리
    status: str  # TodoStatus value
    priority: int  # TodoPriority value

    # 의존성
    dependencies: List[str]  # 다른 TODO ID들
    blocks: List[str]  # 이 TODO가 블록하는 TODO들

    # 시간 추적
    created_at: str
    started_at: Optional[str]
    completed_at: Optional[str]
    estimated_duration: Optional[int]  # seconds
    actual_duration: Optional[int]  # seconds

    # 결과
    result: Optional[Dict[str, Any]]
    error: Optional[str]
    retry_count: int
    max_retries: int

    # 수정 추적
    version: int
    original_version: Optional[Dict]  # 원본 저장
    modifications: List[Dict]  # 수정 이력
    is_user_modified: bool  # 사용자가 수정했는지

    # 메타데이터
    metadata: Dict[str, Any]

class TodoManagementState(TypedDict):
    """TODO 전체 관리 State"""
    # TODO 목록
    todos: List[TodoItem]

    # 실행 관리
    execution_plan: List[List[str]]  # 병렬 실행 그룹
    current_todo_id: Optional[str]
    current_group_index: int

    # 상태 추적
    completed_todos: List[str]
    failed_todos: List[str]
    skipped_todos: List[str]
    modified_todos: List[str]

    # 진행률
    total_count: int
    completed_count: int
    failed_count: int
    progress_percentage: float

    # 실시간 수정
    allow_modifications: bool
    pending_modifications: List[Dict]  # 대기 중인 수정

    # 실행 로그
    execution_log: List[Dict]

    # 메타데이터
    created_at: str
    updated_at: str
    session_id: str
    user_id: Optional[str]
```

### 1.2 TODO Manager 구현

```python
# backend/app/octostrator/supervisor/managers/todo_manager.py
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime

class TodoManager:
    """TODO 생성, 수정, 실행 관리"""

    def __init__(self):
        self.todos: Dict[str, TodoItem] = {}
        self.execution_plan: List[List[str]] = []
        self.dependency_graph = {}

    def create_todo(
        self,
        title: str,
        agent: str,
        task_type: str,
        params: Dict[str, Any] = None,
        dependencies: List[str] = None,
        priority: TodoPriority = TodoPriority.NORMAL,
        **kwargs
    ) -> TodoItem:
        """새 TODO 생성"""

        todo_id = f"todo_{uuid.uuid4().hex[:8]}"

        todo = TodoItem(
            id=todo_id,
            title=title,
            description=kwargs.get("description", ""),
            agent=agent,
            task_type=task_type,
            params=params or {},
            status=TodoStatus.PENDING.value,
            priority=priority.value,
            dependencies=dependencies or [],
            blocks=[],
            created_at=datetime.now().isoformat(),
            started_at=None,
            completed_at=None,
            estimated_duration=kwargs.get("estimated_duration"),
            actual_duration=None,
            result=None,
            error=None,
            retry_count=0,
            max_retries=kwargs.get("max_retries", 3),
            version=1,
            original_version=None,
            modifications=[],
            is_user_modified=False,
            metadata=kwargs.get("metadata", {})
        )

        self.todos[todo_id] = todo
        self._update_dependency_graph(todo_id, dependencies)

        return todo

    def modify_todo(
        self,
        todo_id: str,
        modifications: Dict[str, Any],
        reason: str = "User modification",
        allow_in_progress: bool = True
    ) -> TodoItem:
        """TODO 수정 (실행 중에도 가능)"""

        if todo_id not in self.todos:
            raise ValueError(f"TODO {todo_id} not found")

        todo = self.todos[todo_id]

        # 상태 확인
        if todo["status"] == TodoStatus.COMPLETED.value:
            raise ValueError("Cannot modify completed TODO")

        if todo["status"] == TodoStatus.IN_PROGRESS.value and not allow_in_progress:
            raise ValueError("Cannot modify TODO in progress")

        # 원본 저장 (첫 수정 시)
        if todo["version"] == 1:
            todo["original_version"] = todo.copy()

        # 수정 이력 저장
        modification_record = {
            "version": todo["version"],
            "timestamp": datetime.now().isoformat(),
            "reason": reason,
            "changes": {}
        }

        # 수정 적용
        for key, value in modifications.items():
            if key in todo and key not in ["id", "created_at", "version"]:
                modification_record["changes"][key] = {
                    "old": todo[key],
                    "new": value
                }
                todo[key] = value

        # 메타데이터 업데이트
        todo["version"] += 1
        todo["modifications"].append(modification_record)
        todo["is_user_modified"] = True
        todo["status"] = TodoStatus.MODIFIED.value

        # 의존성 업데이트 (필요 시)
        if "dependencies" in modifications:
            self._update_dependency_graph(todo_id, modifications["dependencies"])

        return todo

    def generate_execution_plan(self) -> List[List[str]]:
        """의존성 기반 병렬 실행 계획 생성"""

        # Topological sort with levels for parallel execution
        levels = {}
        in_degree = {tid: len(self.todos[tid]["dependencies"])
                    for tid in self.todos}

        # Level 0: TODOs without dependencies
        current_level = 0
        queue = [tid for tid, degree in in_degree.items() if degree == 0]

        for todo_id in queue:
            levels[todo_id] = current_level

        processed = set(queue)

        while queue:
            next_queue = []

            for current_id in queue:
                # Check todos that depend on current
                for dependent_id in self.todos[current_id]["blocks"]:
                    if dependent_id not in processed:
                        # Check if all dependencies are processed
                        deps = self.todos[dependent_id]["dependencies"]
                        if all(dep in processed for dep in deps):
                            next_queue.append(dependent_id)
                            processed.add(dependent_id)

                            # Calculate level
                            dep_levels = [levels[dep] for dep in deps]
                            levels[dependent_id] = max(dep_levels) + 1 if dep_levels else 0

            queue = next_queue

        # Group by level for parallel execution
        execution_groups = {}
        for todo_id, level in levels.items():
            if level not in execution_groups:
                execution_groups[level] = []
            execution_groups[level].append(todo_id)

        # Sort by level and return
        self.execution_plan = [execution_groups[level]
                               for level in sorted(execution_groups.keys())]

        return self.execution_plan

    def get_next_todos(self) -> List[str]:
        """다음 실행할 TODO들 반환 (병렬 가능)"""

        if not self.execution_plan:
            self.generate_execution_plan()

        for group in self.execution_plan:
            # Find first group with pending todos
            pending = [tid for tid in group
                      if self.todos[tid]["status"] == TodoStatus.PENDING.value]
            if pending:
                return pending

        return []

    def can_execute(self, todo_id: str) -> bool:
        """TODO 실행 가능 여부 확인"""

        todo = self.todos[todo_id]

        # Check status
        if todo["status"] != TodoStatus.PENDING.value:
            return False

        # Check dependencies
        for dep_id in todo["dependencies"]:
            dep_todo = self.todos.get(dep_id)
            if not dep_todo or dep_todo["status"] != TodoStatus.COMPLETED.value:
                return False

        return True

    def start_todo(self, todo_id: str):
        """TODO 실행 시작"""
        todo = self.todos[todo_id]
        todo["status"] = TodoStatus.IN_PROGRESS.value
        todo["started_at"] = datetime.now().isoformat()

    def complete_todo(self, todo_id: str, result: Dict[str, Any]):
        """TODO 완료 처리"""
        todo = self.todos[todo_id]
        todo["status"] = TodoStatus.COMPLETED.value
        todo["completed_at"] = datetime.now().isoformat()
        todo["result"] = result

        # Calculate actual duration
        if todo["started_at"]:
            start = datetime.fromisoformat(todo["started_at"])
            end = datetime.fromisoformat(todo["completed_at"])
            todo["actual_duration"] = int((end - start).total_seconds())

    def fail_todo(self, todo_id: str, error: str):
        """TODO 실패 처리"""
        todo = self.todos[todo_id]
        todo["status"] = TodoStatus.FAILED.value
        todo["error"] = error
        todo["retry_count"] += 1

        # Check retry
        if todo["retry_count"] < todo["max_retries"]:
            todo["status"] = TodoStatus.PENDING.value  # Retry

    def _update_dependency_graph(self, todo_id: str, dependencies: List[str]):
        """의존성 그래프 업데이트"""
        # Update blocks relationship
        for dep_id in dependencies:
            if dep_id in self.todos:
                if todo_id not in self.todos[dep_id]["blocks"]:
                    self.todos[dep_id]["blocks"].append(todo_id)
```

### 1.3 Cognitive Supervisor 구현

```python
# backend/app/octostrator/supervisor/cognitive_supervisor.py
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, END, START
from typing import Dict, Any, List

from .states.todo_state import TodoManagementState, TodoStatus
from .managers.todo_manager import TodoManager

class CognitiveState(TypedDict):
    """Cognitive Supervisor State"""
    # Input
    messages: List[BaseMessage]
    session_id: str

    # Intent & Context
    intent: Dict[str, Any]
    context: Dict[str, Any]
    memory_context: Dict[str, Any]

    # Planning
    analysis_result: Dict[str, Any]
    suggested_plan: Dict[str, Any]

    # TODO Management
    todo_management: TodoManagementState

    # Decision
    confidence_score: float
    requires_human_review: bool
    alternative_plans: List[Dict]

def build_cognitive_supervisor(checkpointer=None):
    """Cognitive Supervisor Graph 구축"""

    workflow = StateGraph(CognitiveState)

    # 노드 추가
    workflow.add_node("analyze_intent", analyze_intent_node)
    workflow.add_node("build_context", build_context_node)
    workflow.add_node("create_plan", create_plan_node)
    workflow.add_node("generate_todos", generate_todos_node)
    workflow.add_node("validate_plan", validate_plan_node)
    workflow.add_node("handle_modification", handle_modification_node)

    # 엣지 정의
    workflow.add_edge(START, "analyze_intent")
    workflow.add_edge("analyze_intent", "build_context")

    # 조건부 라우팅 (Intent 기반)
    workflow.add_conditional_edges(
        "build_context",
        route_by_intent,
        {
            "create": "create_plan",
            "modify": "handle_modification",
            "query": END  # Query는 바로 종료
        }
    )

    workflow.add_edge("create_plan", "generate_todos")
    workflow.add_edge("generate_todos", "validate_plan")
    workflow.add_edge("handle_modification", "validate_plan")
    workflow.add_edge("validate_plan", END)

    return workflow.compile(checkpointer=checkpointer)

async def analyze_intent_node(state: CognitiveState) -> Dict:
    """사용자 의도 분석"""

    last_message = state["messages"][-1].content

    # Intent Classifier 사용
    from ..intent.classifier import IntentClassifier
    classifier = IntentClassifier()

    intent_result = await classifier.classify(
        message=last_message,
        context=state.get("context", {}),
        history=state["messages"]
    )

    return {
        "intent": {
            "primary": intent_result[0].value,
            "sub": intent_result[1].value if intent_result[1] else None,
            "entities": intent_result[2]
        }
    }

async def create_plan_node(state: CognitiveState) -> Dict:
    """계획 수립"""

    intent = state["intent"]
    context = state["context"]

    # LLM을 사용한 계획 생성 (예시)
    plan = {
        "goal": "Create diet and workout plan",
        "steps": [
            {
                "title": "Analyze user health status",
                "agent": "diet_agent",
                "task_type": "analyze_health",
                "params": {"user_id": context.get("user_id")},
                "priority": 1,
                "estimated_duration": 30
            },
            {
                "title": "Create personalized meal plan",
                "agent": "diet_agent",
                "task_type": "create_meal_plan",
                "params": {"calories": 2000, "meals_per_day": 3},
                "dependencies": [],  # First step dependency
                "priority": 1,
                "estimated_duration": 60
            },
            {
                "title": "Design workout routine",
                "agent": "workout_agent",
                "task_type": "create_routine",
                "params": {"fitness_level": "intermediate"},
                "dependencies": [],  # Depends on first step
                "priority": 2,
                "estimated_duration": 45
            }
        ]
    }

    return {"suggested_plan": plan}

async def generate_todos_node(state: CognitiveState) -> Dict:
    """TODO 생성"""

    plan = state["suggested_plan"]
    todo_manager = TodoManager()

    # Create TODOs from plan
    todo_ids = []
    for idx, step in enumerate(plan["steps"]):
        # Resolve dependencies
        dependencies = []
        if "dependencies" in step:
            # Map step indices to TODO IDs
            for dep_idx in step["dependencies"]:
                if dep_idx < len(todo_ids):
                    dependencies.append(todo_ids[dep_idx])
        elif idx > 0:
            # Default: depend on previous step
            dependencies = [todo_ids[idx - 1]]

        todo = todo_manager.create_todo(
            title=step["title"],
            agent=step["agent"],
            task_type=step["task_type"],
            params=step.get("params", {}),
            dependencies=dependencies,
            priority=TodoPriority(step.get("priority", 3)),
            estimated_duration=step.get("estimated_duration"),
            description=step.get("description", "")
        )

        todo_ids.append(todo["id"])

    # Generate execution plan
    execution_plan = todo_manager.generate_execution_plan()

    # Create TodoManagementState
    todo_state = TodoManagementState(
        todos=list(todo_manager.todos.values()),
        execution_plan=execution_plan,
        current_todo_id=None,
        current_group_index=0,
        completed_todos=[],
        failed_todos=[],
        skipped_todos=[],
        modified_todos=[],
        total_count=len(todo_manager.todos),
        completed_count=0,
        failed_count=0,
        progress_percentage=0.0,
        allow_modifications=True,
        pending_modifications=[],
        execution_log=[],
        created_at=datetime.now().isoformat(),
        updated_at=datetime.now().isoformat(),
        session_id=state["session_id"],
        user_id=state.get("context", {}).get("user_id")
    )

    return {"todo_management": todo_state}

async def handle_modification_node(state: CognitiveState) -> Dict:
    """TODO 수정 처리"""

    intent = state["intent"]
    todo_mgmt = state.get("todo_management")

    if not todo_mgmt:
        return {"error": "No TODOs to modify"}

    # Find target TODO
    target = intent["entities"].get("target")

    if not target:
        # Modify the most recent or current TODO
        if todo_mgmt["current_todo_id"]:
            target = todo_mgmt["current_todo_id"]
        else:
            target = todo_mgmt["todos"][-1]["id"] if todo_mgmt["todos"] else None

    if not target:
        return {"error": "No TODO to modify"}

    # Apply modification
    modifications = intent["entities"].get("modifications", {})

    # Update TODO in state
    for todo in todo_mgmt["todos"]:
        if todo["id"] == target:
            # Record modification
            todo["version"] += 1
            todo["is_user_modified"] = True
            todo["modifications"].append({
                "timestamp": datetime.now().isoformat(),
                "changes": modifications
            })

            # Apply changes
            for key, value in modifications.items():
                if key in todo:
                    todo[key] = value

            # Add to modified list
            if target not in todo_mgmt["modified_todos"]:
                todo_mgmt["modified_todos"].append(target)

            break

    todo_mgmt["updated_at"] = datetime.now().isoformat()

    return {"todo_management": todo_mgmt}
```

### 1.4 Execute Supervisor 구현

```python
# backend/app/octostrator/supervisor/execute_supervisor.py
from langraph.graph import StateGraph, END, START
from typing import Dict, Any, List, Optional
import asyncio

from .states.todo_state import TodoManagementState, TodoStatus
from ..agents.base import agent_registry

class ExecuteState(TypedDict):
    """Execute Supervisor State"""
    # TODO Management
    todo_management: TodoManagementState

    # Execution
    current_agent: Optional[str]
    agent_states: Dict[str, Any]
    parallel_tasks: List[asyncio.Task]

    # Progress
    execution_log: List[Dict]
    performance_metrics: Dict[str, Any]

    # Results
    partial_results: Dict[str, Any]
    final_result: Optional[Dict]

    # Error handling
    errors: List[Dict]
    retry_queue: List[str]

def build_execute_supervisor(checkpointer=None):
    """Execute Supervisor Graph 구축"""

    workflow = StateGraph(ExecuteState)

    # 노드 추가
    workflow.add_node("prepare_execution", prepare_execution_node)
    workflow.add_node("execute_parallel_group", execute_parallel_group_node)
    workflow.add_node("execute_single_todo", execute_single_todo_node)
    workflow.add_node("track_progress", track_progress_node)
    workflow.add_node("handle_error", handle_error_node)
    workflow.add_node("check_modifications", check_modifications_node)
    workflow.add_node("aggregate_results", aggregate_results_node)

    # 엣지 정의
    workflow.add_edge(START, "prepare_execution")
    workflow.add_edge("prepare_execution", "execute_parallel_group")

    # 실행 루프
    workflow.add_conditional_edges(
        "execute_parallel_group",
        check_execution_status,
        {
            "continue": "track_progress",
            "complete": "aggregate_results",
            "error": "handle_error",
            "modified": "check_modifications"
        }
    )

    workflow.add_edge("track_progress", "execute_parallel_group")
    workflow.add_edge("check_modifications", "execute_parallel_group")

    workflow.add_conditional_edges(
        "handle_error",
        check_retry,
        {
            "retry": "execute_parallel_group",
            "skip": "track_progress",
            "abort": "aggregate_results"
        }
    )

    workflow.add_edge("aggregate_results", END)

    return workflow.compile(checkpointer=checkpointer)

async def prepare_execution_node(state: ExecuteState) -> Dict:
    """실행 준비"""

    todo_mgmt = state["todo_management"]

    # Initialize execution state
    return {
        "agent_states": {},
        "partial_results": {},
        "execution_log": [{
            "timestamp": datetime.now().isoformat(),
            "event": "execution_started",
            "total_todos": todo_mgmt["total_count"]
        }],
        "performance_metrics": {
            "start_time": datetime.now().isoformat(),
            "agent_execution_times": {}
        },
        "errors": [],
        "retry_queue": []
    }

async def execute_parallel_group_node(state: ExecuteState) -> Dict:
    """병렬 그룹 실행"""

    todo_mgmt = state["todo_management"]
    current_group_idx = todo_mgmt["current_group_index"]

    # Check if all groups completed
    if current_group_idx >= len(todo_mgmt["execution_plan"]):
        return {"status": "complete"}

    # Get current group
    current_group = todo_mgmt["execution_plan"][current_group_idx]

    # Filter executable TODOs
    executable_todos = []
    for todo_id in current_group:
        todo = next((t for t in todo_mgmt["todos"] if t["id"] == todo_id), None)

        if todo and todo["status"] in [TodoStatus.PENDING.value, TodoStatus.MODIFIED.value]:
            # Check dependencies
            deps_completed = all(
                dep_id in todo_mgmt["completed_todos"]
                for dep_id in todo["dependencies"]
            )

            if deps_completed:
                executable_todos.append(todo)

    if not executable_todos:
        # Move to next group
        todo_mgmt["current_group_index"] += 1
        return {"todo_management": todo_mgmt, "status": "continue"}

    # Execute TODOs in parallel
    tasks = []
    for todo in executable_todos:
        task = asyncio.create_task(execute_single_todo(todo, state))
        tasks.append(task)

    # Wait for all tasks
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Process results
    for todo, result in zip(executable_todos, results):
        if isinstance(result, Exception):
            # Handle error
            todo["status"] = TodoStatus.FAILED.value
            todo["error"] = str(result)
            todo_mgmt["failed_todos"].append(todo["id"])

            state["errors"].append({
                "todo_id": todo["id"],
                "error": str(result),
                "timestamp": datetime.now().isoformat()
            })
        else:
            # Success
            todo["status"] = TodoStatus.COMPLETED.value
            todo["result"] = result
            todo["completed_at"] = datetime.now().isoformat()

            todo_mgmt["completed_todos"].append(todo["id"])
            todo_mgmt["completed_count"] += 1

            # Store result
            state["partial_results"][todo["id"]] = result

    # Update progress
    todo_mgmt["progress_percentage"] = (
        todo_mgmt["completed_count"] / todo_mgmt["total_count"] * 100
    )

    # Check if group completed
    group_completed = all(
        todo_id in todo_mgmt["completed_todos"] + todo_mgmt["failed_todos"]
        for todo_id in current_group
    )

    if group_completed:
        todo_mgmt["current_group_index"] += 1

    return {
        "todo_management": todo_mgmt,
        "partial_results": state["partial_results"],
        "errors": state["errors"]
    }

async def execute_single_todo(todo: TodoItem, state: ExecuteState) -> Dict:
    """단일 TODO 실행"""

    # Update status
    todo["status"] = TodoStatus.IN_PROGRESS.value
    todo["started_at"] = datetime.now().isoformat()

    # Log execution start
    state["execution_log"].append({
        "timestamp": datetime.now().isoformat(),
        "event": "todo_started",
        "todo_id": todo["id"],
        "agent": todo["agent"]
    })

    try:
        # Get agent
        agent = agent_registry.get_agent_instance(todo["agent"])

        if not agent:
            # Create agent if not exists
            agent = agent_registry.create_agent(todo["agent"])

            # Initialize agent
            if agent.enable_checkpoint:
                # Use checkpoint for complex agents
                from ..checkpointer.postgres_checkpointer import create_checkpointer
                checkpointer = await create_checkpointer()
                await agent.initialize(llm=None, checkpointer=checkpointer)
            else:
                await agent.initialize(llm=None)

        # Execute task
        result = await agent.execute(
            task={
                "type": todo["task_type"],
                "params": todo["params"]
            },
            context={
                "todo_id": todo["id"],
                "session_id": state["todo_management"]["session_id"],
                "dependencies": todo.get("dependencies", [])
            },
            thread_id=f"{state['todo_management']['session_id']}_{todo['agent']}"
        )

        # Calculate duration
        start = datetime.fromisoformat(todo["started_at"])
        duration = (datetime.now() - start).total_seconds()

        # Update metrics
        if todo["agent"] not in state["performance_metrics"]["agent_execution_times"]:
            state["performance_metrics"]["agent_execution_times"][todo["agent"]] = []

        state["performance_metrics"]["agent_execution_times"][todo["agent"]].append(duration)

        # Log completion
        state["execution_log"].append({
            "timestamp": datetime.now().isoformat(),
            "event": "todo_completed",
            "todo_id": todo["id"],
            "duration": duration
        })

        return result

    except Exception as e:
        # Log error
        state["execution_log"].append({
            "timestamp": datetime.now().isoformat(),
            "event": "todo_failed",
            "todo_id": todo["id"],
            "error": str(e)
        })

        raise e

def check_execution_status(state: ExecuteState) -> str:
    """실행 상태 확인"""

    todo_mgmt = state["todo_management"]

    # Check for modifications
    if todo_mgmt["pending_modifications"]:
        return "modified"

    # Check for errors
    if state["errors"] and state.get("retry_queue"):
        return "error"

    # Check if all completed
    if todo_mgmt["current_group_index"] >= len(todo_mgmt["execution_plan"]):
        return "complete"

    return "continue"
```

---

## 2. 실제 사용 예시

### 2.1 시스템 초기화

```python
# backend/app/main.py
from app.octostrator.supervisor.cognitive_supervisor import build_cognitive_supervisor
from app.octostrator.supervisor.execute_supervisor import build_execute_supervisor

async def initialize_dual_supervisors():
    """Dual Supervisor 시스템 초기화"""

    # Checkpointer 생성
    from app.octostrator.checkpointer.postgres_checkpointer import create_checkpointer
    checkpointer = await create_checkpointer()

    # Cognitive Supervisor
    cognitive_supervisor = build_cognitive_supervisor(checkpointer)

    # Execute Supervisor
    execute_supervisor = build_execute_supervisor(checkpointer)

    return cognitive_supervisor, execute_supervisor

# WebSocket Handler
async def handle_message(websocket, message: str, session_id: str):
    """메시지 처리"""

    # 1. Cognitive Supervisor 실행
    cognitive_result = await cognitive_supervisor.ainvoke(
        {
            "messages": [HumanMessage(content=message)],
            "session_id": session_id
        },
        config={"configurable": {"thread_id": f"{session_id}_cognitive"}}
    )

    # 2. TODO가 생성되었으면 Execute Supervisor 실행
    if cognitive_result.get("todo_management"):
        # 즉시 응답 (TODO 생성 완료)
        await websocket.send_json({
            "type": "plan_created",
            "todos": len(cognitive_result["todo_management"]["todos"]),
            "message": "계획을 생성했습니다. 실행을 시작합니다."
        })

        # Execute Supervisor 실행 (비동기)
        asyncio.create_task(
            execute_with_progress(
                websocket,
                cognitive_result["todo_management"],
                session_id
            )
        )

async def execute_with_progress(websocket, todo_management, session_id):
    """실행 중 진행 상황 전송"""

    # Execute Supervisor 실행
    async for chunk in execute_supervisor.astream(
        {
            "todo_management": todo_management
        },
        config={"configurable": {"thread_id": f"{session_id}_execute"}}
    ):
        # 진행 상황 전송
        if "todo_management" in chunk:
            progress = chunk["todo_management"]["progress_percentage"]
            await websocket.send_json({
                "type": "progress_update",
                "progress": progress,
                "completed": chunk["todo_management"]["completed_count"],
                "total": chunk["todo_management"]["total_count"]
            })
```

### 2.2 실행 중 수정

```python
async def handle_modification(websocket, modification_request: Dict, session_id: str):
    """실행 중 TODO 수정"""

    # 1. 현재 Execute State 조회
    current_state = await get_current_execute_state(session_id)

    # 2. Modification을 pending에 추가
    current_state["todo_management"]["pending_modifications"].append({
        "request": modification_request,
        "timestamp": datetime.now().isoformat()
    })

    # 3. Cognitive Supervisor로 수정 처리
    cognitive_result = await cognitive_supervisor.ainvoke(
        {
            "messages": [HumanMessage(content=modification_request["message"])],
            "session_id": session_id,
            "todo_management": current_state["todo_management"],
            "intent": {"primary": "MODIFY"}
        },
        config={"configurable": {"thread_id": f"{session_id}_cognitive"}}
    )

    # 4. 수정된 TODO를 Execute Supervisor에 반영
    await update_execute_state(session_id, cognitive_result["todo_management"])

    # 5. 사용자에게 알림
    await websocket.send_json({
        "type": "modification_applied",
        "modified_todos": cognitive_result["todo_management"]["modified_todos"]
    })
```

---

## 3. 장점 요약

### ✅ **Two Graphs (Cognitive + Execute) 사용 권장**

1. **명확한 책임 분리**
   - Cognitive: 계획과 수정
   - Execute: 실행과 모니터링

2. **유연한 수정**
   - 실행 중에도 TODO 수정 가능
   - 버전 관리와 이력 추적

3. **향상된 사용자 경험**
   - 빠른 초기 응답 (계획 즉시 표시)
   - 실시간 진행률 업데이트

4. **확장 가능한 구조**
   - 새로운 Agent 쉽게 추가
   - 복잡한 워크플로우 지원

이 구조로 **"계획 수립 - 언제든 수정"** 이 가능한 유연한 시스템을 구현할 수 있습니다!

---

**작성 완료일**: 2025-11-05
**버전**: 1.0
**문서 위치**: `reports/supervisor/TODO_MANAGEMENT_IMPLEMENTATION_GUIDE_251105.md`