# 05. Phase 3: Supervisor Agent

**문서 버전**: 1.0.0  
**작성일**: 2025-11-17  
**관련 문서**: [04_PHASE2_PLANNING.md](./04_PHASE2_PLANNING.md)

---

## 📋 목차

1. [Supervisor Agent 개요](#1-supervisor-agent-개요)
2. [TODO 실행 전략](#2-todo-실행-전략)
3. [의존성 체크](#3-의존성-체크)
4. [병렬 처리 (Send API)](#4-병렬-처리-send-api)
5. [ESC 중단 처리](#5-esc-중단-처리)
6. [에러 복구](#6-에러-복구)
7. [상태 업데이트](#7-상태-업데이트)

---

## 1. Supervisor Agent 개요

### 1.1 역할

**Supervisor Agent**는 TODO 리스트를 관리하고 Worker에게 작업을 할당하는 오케스트레이터입니다.

```
Planning Agent (TODO 생성)
    ↓
Supervisor Agent
    ├─ 실행 가능한 TODO 찾기
    ├─ 의존성 체크
    ├─ Worker 할당
    └─ 병렬/순차 실행 결정
    ↓
Worker Subgraph
    ↓
Supervisor Agent (재귀)
```

### 1.2 입력/출력

| 항목 | 설명 |
|------|------|
| **입력** | `todos`, `active_todo_id` |
| **처리** | 의존성 체크, 실행 순서 결정 |
| **출력** | `active_todo_id` 업데이트 |
| **라우팅** | `worker_subgraph` (Send 또는 Command) |

### 1.3 핵심 책임

1. **의존성 관리**: 선행 TODO 완료 여부 확인
2. **병렬 처리**: 독립적인 TODO 동시 실행
3. **상태 추적**: TODO status 업데이트
4. **중단 감지**: `user_interrupted` 플래그 체크
5. **완료 판단**: 모든 TODO 완료 시 종료

---

## 2. TODO 실행 전략

### 2.1 기본 알고리즘

```python
from langgraph.types import Command, Send

def supervisor_agent(state: MainState) -> Command | List[Send]:
    """
    Supervisor Agent
    TODO 실행 순서 관리
    """
    
    # 1. 사용자 중단 체크
    if state.get("user_interrupted"):
        return Command(
            update={"conversation_mode": "paused"},
            goto="handle_user_interrupt"
        )
    
    # 2. 실행 가능한 TODO 찾기
    ready_todos = find_ready_todos(state["todos"])
    
    # 3. 모든 TODO 완료 확인
    if not ready_todos:
        if all_todos_completed(state["todos"]):
            return Command(
                update={"conversation_mode": "completed"},
                goto=END
            )
        else:
            # 대기 중인 TODO가 있지만 의존성 미충족
            return Command(
                update={"conversation_mode": "waiting"},
                goto=END  # 일시 중지
            )
    
    # 4. 병렬/순차 실행 결정
    if can_run_in_parallel(ready_todos):
        # Send API로 병렬 실행
        return [
            Send("worker_subgraph", {"current_todo": todo})
            for todo in ready_todos
        ]
    else:
        # 순차 실행 (첫 번째 TODO)
        todo = ready_todos[0]
        return Command(
            update={
                "active_todo_id": todo["id"],
                "todos": update_todo_status(state["todos"], todo["id"], "in_progress")
            },
            goto="worker_subgraph"
        )
```

### 2.2 실행 가능 TODO 찾기

```python
def find_ready_todos(todos: List[TodoItem]) -> List[TodoItem]:
    """
    실행 가능한 TODO 찾기
    - status == "pending"
    - 모든 dependencies 완료됨
    """
    pending_todos = [t for t in todos if t["status"] == "pending"]
    
    ready = []
    for todo in pending_todos:
        if are_dependencies_met(todo, todos):
            ready.append(todo)
    
    return ready

def are_dependencies_met(todo: TodoItem, all_todos: List[TodoItem]) -> bool:
    """의존성 체크"""
    if not todo.get("dependencies"):
        return True
    
    # 모든 의존 TODO가 완료되었는지 확인
    todo_dict = {t["id"]: t for t in all_todos}
    
    for dep_id in todo["dependencies"]:
        if dep_id not in todo_dict:
            return False  # 의존 TODO가 없음 (에러)
        
        if todo_dict[dep_id]["status"] != "completed":
            return False  # 아직 완료 안 됨
    
    return True
```

### 2.3 완료 여부 확인

```python
def all_todos_completed(todos: List[TodoItem]) -> bool:
    """모든 TODO가 완료되었는지 확인"""
    return all(
        t["status"] in ["completed", "failed"]
        for t in todos
    )
```

---

## 3. 의존성 체크

### 3.1 의존성 그래프

```python
class DependencyGraph:
    """TODO 의존성 그래프 관리"""
    
    def __init__(self, todos: List[TodoItem]):
        self.todos = {t["id"]: t for t in todos}
        self.graph = self._build_graph()
    
    def _build_graph(self) -> dict:
        """인접 리스트 생성"""
        graph = {todo_id: [] for todo_id in self.todos}
        
        for todo_id, todo in self.todos.items():
            for dep_id in todo.get("dependencies", []):
                # dep_id → todo_id 엣지
                graph[dep_id].append(todo_id)
        
        return graph
    
    def get_ready_todos(self) -> List[TodoItem]:
        """실행 가능한 TODO 반환"""
        ready = []
        
        for todo_id, todo in self.todos.items():
            if todo["status"] != "pending":
                continue
            
            # 모든 의존성 완료?
            deps_completed = all(
                self.todos[dep_id]["status"] == "completed"
                for dep_id in todo.get("dependencies", [])
            )
            
            if deps_completed:
                ready.append(todo)
        
        return ready
    
    def get_execution_order(self) -> List[List[TodoItem]]:
        """
        실행 순서 반환 (레벨별)
        레벨 0: 의존성 없는 TODO
        레벨 1: 레벨 0 완료 후 실행 가능한 TODO
        ...
        """
        levels = []
        remaining = set(self.todos.keys())
        
        while remaining:
            # 현재 레벨: 의존성이 모두 완료된 TODO
            current_level = []
            for todo_id in remaining:
                todo = self.todos[todo_id]
                deps = set(todo.get("dependencies", []))
                
                if deps.issubset(set(self.todos.keys()) - remaining):
                    current_level.append(todo)
            
            if not current_level:
                # 순환 의존성 또는 에러
                break
            
            levels.append(current_level)
            remaining -= {t["id"] for t in current_level}
        
        return levels
```

### 3.2 의존성 시각화

```python
def visualize_dependencies(todos: List[TodoItem]) -> str:
    """
    Mermaid 형식으로 의존성 그래프 생성
    Frontend에서 표시 가능
    """
    lines = ["graph TD"]
    
    for todo in todos:
        # 노드 정의
        status_style = {
            "pending": "[⏸️]",
            "in_progress": "[🔄]",
            "completed": "[✅]",
            "failed": "[❌]"
        }
        
        node_label = f"{todo['id']}{status_style.get(todo['status'], '[]')} {todo['title']}"
        lines.append(f'    {todo["id"]}("{node_label}")')
        
        # 엣지 정의
        for dep_id in todo.get("dependencies", []):
            lines.append(f'    {dep_id} --> {todo["id"]}')
    
    return "\n".join(lines)
```

---

## 4. 병렬 처리 (Send API)

### 4.1 병렬 실행 조건

```python
def can_run_in_parallel(todos: List[TodoItem]) -> bool:
    """
    병렬 실행 가능 여부 판단
    """
    # 2개 이상의 독립적인 TODO
    if len(todos) < 2:
        return False
    
    # 모두 parallel 플래그가 True
    if not all(t.get("parallel", True) for t in todos):
        return False
    
    # Worker 리소스 제한 (선택)
    # 예: 동시에 5개까지만
    MAX_PARALLEL = 5
    if len(todos) > MAX_PARALLEL:
        return False
    
    return True
```

### 4.2 Send API 활용

```python
def supervisor_agent(state: MainState):
    ready_todos = find_ready_todos(state["todos"])
    
    if can_run_in_parallel(ready_todos):
        # Send API로 병렬 실행
        return [
            Send(
                "worker_subgraph",
                {
                    "current_todo": todo,
                    "tool_calls": [],
                    "intermediate_results": [],
                    "final_result": None,
                    "worker_messages": []
                }
            )
            for todo in ready_todos
        ]
```

**Send API 동작**:
1. 각 TODO마다 독립적인 `worker_subgraph` 인스턴스 실행
2. 모든 인스턴스가 완료될 때까지 대기
3. 완료 후 Main Graph로 복귀 (Supervisor Agent 재귀 호출)

### 4.3 병렬 실행 결과 수집

```python
# Worker Subgraph의 finalize 노드에서
def finalize_worker(state: WorkerState) -> Command:
    completed_todo = {
        **state["current_todo"],
        "status": "completed",
        "result": state["final_result"],
        "completed_at": datetime.now().isoformat()
    }
    
    # Main Graph로 복귀
    return Command(
        update={"completed_todo": completed_todo},
        goto=Command.PARENT
    )

# Main Graph의 Supervisor Agent에서 자동 수집
def supervisor_agent(state: MainState):
    # state["todos"]가 자동으로 업데이트됨
    # (Send로 실행된 모든 TODO의 결과 반영)
    ...
```

---

## 5. ESC 중단 처리

### 5.1 중단 감지

```python
def supervisor_agent(state: MainState):
    # 최우선 체크: 사용자 중단
    if state.get("user_interrupted"):
        return Command(
            update={
                "conversation_mode": "paused",
                # 현재 진행 중인 TODO를 "paused"로 변경
                "todos": pause_active_todos(state["todos"])
            },
            goto="handle_user_interrupt"
        )
    
    # ... 나머지 로직 ...

def pause_active_todos(todos: List[TodoItem]) -> List[TodoItem]:
    """진행 중인 TODO를 paused 상태로 변경"""
    return [
        {**t, "status": "paused"} if t["status"] == "in_progress" else t
        for t in todos
    ]
```

### 5.2 handle_user_interrupt 노드

```python
def handle_user_interrupt(state: MainState) -> Command:
    """
    사용자 중단 처리
    """
    # interrupt() 발생 - 사용자에게 선택지 제공
    user_decision = interrupt({
        "type": "todo_modification",
        "message": "작업이 중단되었습니다. 어떻게 하시겠습니까?",
        "data": {
            "current_todos": state["todos"],
            "paused_count": sum(1 for t in state["todos"] if t["status"] == "paused"),
            "options": [
                {"label": "TODO 수정", "value": "modify"},
                {"label": "계속 진행", "value": "continue"},
                {"label": "작업 중단", "value": "stop"}
            ]
        }
    })
    
    if user_decision["action"] == "modify":
        # Planning Agent로 이동 (TODO 수정)
        return Command(
            update={
                "user_interrupted": False,
                "current_intent": "modify_task"
            },
            goto="planning_agent"
        )
    
    elif user_decision["action"] == "continue":
        # Paused TODO를 다시 Pending으로
        resumed_todos = [
            {**t, "status": "pending"} if t["status"] == "paused" else t
            for t in state["todos"]
        ]
        
        return Command(
            update={
                "user_interrupted": False,
                "todos": resumed_todos,
                "conversation_mode": "executing"
            },
            goto="supervisor_agent"
        )
    
    else:  # stop
        return Command(
            update={"conversation_mode": "completed"},
            goto=END
        )
```

---

## 6. 에러 복구

### 6.1 TODO 실패 처리

```python
def supervisor_agent(state: MainState):
    # 실패한 TODO 확인
    failed_todos = [t for t in state["todos"] if t["status"] == "failed"]
    
    if failed_todos:
        # 사용자에게 알림
        user_decision = interrupt({
            "type": "error_handling",
            "message": f"{len(failed_todos)}개의 TODO가 실패했습니다.",
            "data": {
                "failed_todos": failed_todos,
                "options": [
                    {"label": "재시도", "value": "retry"},
                    {"label": "건너뛰기", "value": "skip"},
                    {"label": "중단", "value": "stop"}
                ]
            }
        })
        
        if user_decision["action"] == "retry":
            # 실패한 TODO를 다시 pending으로
            retried_todos = [
                {**t, "status": "pending", "error": None}
                if t["status"] == "failed" else t
                for t in state["todos"]
            ]
            
            return Command(
                update={"todos": retried_todos},
                goto="supervisor_agent"
            )
        
        elif user_decision["action"] == "skip":
            # 실패한 TODO의 의존자들도 실패 처리
            todos = mark_dependent_todos_failed(state["todos"], failed_todos)
            
            return Command(
                update={"todos": todos},
                goto="supervisor_agent"
            )
```

### 6.2 Checkpointer 기반 복구

```python
# 에러 발생 시 Checkpointer에 자동 저장
# 마지막 성공 지점에서 재개 가능

async def recover_from_error(thread_id: str):
    """에러 복구"""
    config = {"configurable": {"thread_id": thread_id}}
    
    # 마지막 체크포인트에서 상태 가져오기
    state = await graph.aget_state(config)
    
    # 에러가 있는지 확인
    if state.values.get("error"):
        # 이전 체크포인트로 롤백
        history = await graph.aget_state_history(config)
        previous_checkpoint = next(
            (c for c in history if not c.values.get("error")),
            None
        )
        
        if previous_checkpoint:
            # 이전 체크포인트에서 재개
            await graph.aupdate_state(
                config,
                previous_checkpoint.values
            )
```

---

## 7. 상태 업데이트

### 7.1 TODO Status 업데이트

```python
def update_todo_status(
    todos: List[TodoItem],
    todo_id: str,
    new_status: str
) -> List[TodoItem]:
    """특정 TODO의 status 업데이트"""
    return [
        {
            **t,
            "status": new_status,
            "started_at": datetime.now().isoformat() if new_status == "in_progress" else t.get("started_at"),
            "completed_at": datetime.now().isoformat() if new_status == "completed" else t.get("completed_at")
        } if t["id"] == todo_id else t
        for t in todos
    ]
```

### 7.2 Worker 결과 병합

```python
def merge_worker_result(
    todos: List[TodoItem],
    completed_todo: TodoItem
) -> List[TodoItem]:
    """Worker에서 완료된 TODO 병합"""
    return [
        completed_todo if t["id"] == completed_todo["id"] else t
        for t in todos
    ]
```

### 7.3 진행률 계산

```python
def calculate_progress(todos: List[TodoItem]) -> dict:
    """진행률 계산"""
    total = len(todos)
    completed = sum(1 for t in todos if t["status"] == "completed")
    in_progress = sum(1 for t in todos if t["status"] == "in_progress")
    failed = sum(1 for t in todos if t["status"] == "failed")
    
    return {
        "total": total,
        "completed": completed,
        "in_progress": in_progress,
        "failed": failed,
        "percentage": int(completed / total * 100) if total > 0 else 0
    }
```

---

## 8. 최적화 전략

### 8.1 캐싱

```python
from functools import lru_cache

@lru_cache(maxsize=1000)
def are_dependencies_met_cached(
    todo_id: str,
    todos_hash: str
) -> bool:
    """의존성 체크 캐싱"""
    # todos_hash = hash(frozenset([(t["id"], t["status"]) for t in todos]))
    ...
```

### 8.2 배치 처리

```python
def supervisor_agent(state: MainState):
    ready_todos = find_ready_todos(state["todos"])
    
    # 배치 크기 설정
    BATCH_SIZE = 3
    
    if len(ready_todos) > BATCH_SIZE:
        # 첫 BATCH_SIZE개만 실행
        batch = ready_todos[:BATCH_SIZE]
        
        return [
            Send("worker_subgraph", {"current_todo": todo})
            for todo in batch
        ]
```

---

## 9. 테스트 케이스

### 9.1 순차 실행 테스트

```python
def test_supervisor_sequential_execution():
    state = {
        "todos": [
            {"id": "todo_1", "status": "pending", "dependencies": []},
            {"id": "todo_2", "status": "pending", "dependencies": ["todo_1"]}
        ],
        "user_interrupted": False
    }
    
    result = supervisor_agent(state)
    
    # todo_1만 실행
    assert result.update["active_todo_id"] == "todo_1"
    assert result.goto == "worker_subgraph"
```

### 9.2 병렬 실행 테스트

```python
def test_supervisor_parallel_execution():
    state = {
        "todos": [
            {"id": "todo_1", "status": "pending", "dependencies": []},
            {"id": "todo_2", "status": "pending", "dependencies": []},
            {"id": "todo_3", "status": "pending", "dependencies": []}
        ],
        "user_interrupted": False
    }
    
    result = supervisor_agent(state)
    
    # Send 리스트 반환
    assert isinstance(result, list)
    assert len(result) == 3
    assert all(isinstance(s, Send) for s in result)
```

### 9.3 ESC 중단 테스트

```python
def test_supervisor_user_interrupt():
    state = {
        "todos": [
            {"id": "todo_1", "status": "in_progress"}
        ],
        "user_interrupted": True
    }
    
    result = supervisor_agent(state)
    
    assert result.goto == "handle_user_interrupt"
    assert result.update["conversation_mode"] == "paused"
```

---

## 10. 다음 단계

Supervisor Agent 이후 실제 작업 실행은 다음 문서를 참고하세요:

1. **[06_PHASE4_WORKERS.md](./06_PHASE4_WORKERS.md)**: Worker Subgraph 구현
2. **[07_INTERRUPT_SCENARIOS.md](./07_INTERRUPT_SCENARIOS.md)**: 전체 Interrupt 시나리오

---

**이전 문서**: [04_PHASE2_PLANNING.md](./04_PHASE2_PLANNING.md)  
**다음 문서**: [06_PHASE4_WORKERS.md](./06_PHASE4_WORKERS.md)
