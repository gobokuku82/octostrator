# API 상세 설계서

**작성일:** 2025-11-06
**버전:** 1.0

---

## 📋 목차

1. [API 개요](#api-개요)
2. [기존 API](#기존-api)
3. [신규 API](#신규-api)
4. [에러 처리](#에러-처리)
5. [사용 예시](#사용-예시)

---

## 🌐 API 개요

### Base URL

```
http://localhost:8000
```

### 인증

현재는 인증 없음 (향후 JWT 추가 예정)

### 응답 형식

모든 API는 JSON으로 응답

```json
{
  "success": true,
  "data": {...},
  "error": null
}
```

---

## 📌 기존 API

### 1. GET /api/sessions

세션 목록 조회

**요청**
```http
GET /api/sessions?user_id=abc123&status=in_progress
```

**응답**
```json
{
  "sessions": [
    {
      "thread_id": "session_001",
      "user_id": "abc123",
      "status": "in_progress",
      "created_at": "2025-11-06T09:30:00"
    }
  ],
  "total": 1
}
```

### 2. GET /api/sessions/{thread_id}

세션 상태 조회

**요청**
```http
GET /api/sessions/session_001
```

**응답**
```json
{
  "thread_id": "session_001",
  "status": "in_progress",
  "state": {
    "user_query": "점심 추천해줘",
    "plan": {...},
    "todos": [...],
    "execution_results": {...}
  },
  "checkpoint_id": "checkpoint_123"
}
```

### 3. POST /api/sessions/{thread_id}/resume

세션 재개

**요청**
```http
POST /api/sessions/session_001/resume
Content-Type: application/json

{
  "approve": true,
  "response": null
}
```

**응답**
```json
{
  "success": true,
  "message": "Session resumed with auto-approval",
  "state": {...}
}
```

### 4. GET /api/sessions/{thread_id}/history

세션 히스토리 조회

**요청**
```http
GET /api/sessions/session_001/history?limit=10
```

**응답**
```json
{
  "thread_id": "session_001",
  "plan": {...},
  "todos": [...],
  "total_todos": 10,
  "returned_todos": 10,
  "execution_results": {...},
  "final_response": "..."
}
```

---

## 🆕 신규 API

### 1. GET /api/sessions/{thread_id}/summary

**작업 내역 전체 요약**

**목적**: 사용자가 "지금까지 뭐 했어?" 질문에 답변

**요청**
```http
GET /api/sessions/session_001/summary
```

**응답**
```json
{
  "session_id": "session_001",
  "created_at": "2025-11-06T09:30:00",
  "duration": "0:05:23",
  "total_steps": 12,
  "todo_status": {
    "total": 10,
    "completed": 7,
    "failed": 1,
    "pending": 2,
    "in_progress": 0,
    "progress": 0.7
  },
  "plan_version": 2,
  "user_interactions": 3,
  "status": "in_progress",
  "actions_summary": "Step 1 [09:30:00] cognitive_layer_node (250ms)\nStep 2 [09:30:01] todo_layer_node (180ms)\n...",
  "user_interactions_summary": [
    "[09:32:00] 중단: 잠깐 멈춰",
    "[09:33:15] Todo delete",
    "[09:34:00] 재개"
  ]
}
```

**구현 위치**: `backend/app/api/sessions.py`

```python
@router.get("/{thread_id}/summary")
async def get_session_summary(thread_id: str):
    """작업 내역 전체 요약"""
    checkpointer = await create_checkpointer()
    graph = build_supervisor_graph(checkpointer=checkpointer)
    config = get_session_config(thread_id)

    state = await graph.aget_state(config)
    if not state.values:
        raise HTTPException(status_code=404, detail=f"Session not found")

    summary = StateHelpers.get_execution_summary(state.values)
    summary["actions_summary"] = StateHelpers.get_all_actions_summary(state.values)
    summary["user_interactions_summary"] = StateHelpers.get_user_interaction_summary(state.values)

    return summary
```

---

### 2. GET /api/sessions/{thread_id}/action/{step}

**특정 Step의 작업 조회**

**목적**: 사용자가 "4번 작업이 뭐였지?" 질문에 답변

**요청**
```http
GET /api/sessions/session_001/action/4
```

**응답**
```json
{
  "step": 4,
  "action": "execute_layer_node",
  "timestamp": "2025-11-06T09:31:45",
  "result": {
    "completed": 3,
    "failed": 0,
    "success_rate": 1.0
  },
  "duration_ms": 1250
}
```

**응답 (Not Found)**
```json
{
  "error": "Action not found at step 4"
}
```

**구현 위치**: `backend/app/api/sessions.py`

```python
@router.get("/{thread_id}/action/{step}")
async def get_action_at_step(thread_id: str, step: int):
    """특정 step의 작업 조회"""
    checkpointer = await create_checkpointer()
    graph = build_supervisor_graph(checkpointer=checkpointer)
    config = get_session_config(thread_id)

    state = await graph.aget_state(config)
    if not state.values:
        raise HTTPException(status_code=404, detail=f"Session not found")

    action = StateHelpers.get_action_at_step(state.values, step)
    if not action:
        raise HTTPException(status_code=404, detail=f"Action not found at step {step}")

    return action
```

---

### 3. PUT /api/sessions/{thread_id}/state

**State 직접 수정**

**목적**: Plan/Todos/Agent 등을 한 번에 수정

**요청**
```http
PUT /api/sessions/session_001/state
Content-Type: application/json

{
  "plan": {
    "goal": "운동 중심 건강 관리",
    "steps": ["체력 측정", "운동 프로그램 생성"]
  },
  "todos": [
    {"id": "todo_1", "task": "체력 측정", "agent": "WorkoutAgent"},
    {"id": "todo_2", "task": "운동 프로그램", "agent": "WorkoutAgent"}
  ]
}
```

**응답**
```json
{
  "success": true,
  "message": "State updated successfully",
  "updated_fields": ["plan", "todos"]
}
```

**구현 위치**: `backend/app/api/sessions.py`

```python
from pydantic import BaseModel
from typing import Optional, Dict, Any

class StateUpdateRequest(BaseModel):
    plan: Optional[Dict[str, Any]] = None
    todos: Optional[List[Dict]] = None
    context: Optional[Dict] = None

@router.put("/{thread_id}/state")
async def update_state(thread_id: str, request: StateUpdateRequest):
    """State 직접 수정"""
    checkpointer = await create_checkpointer()
    graph = build_supervisor_graph(checkpointer=checkpointer)
    config = get_session_config(thread_id)

    # 현재 상태 확인
    current_state = await graph.aget_state(config)
    if not current_state.values:
        raise HTTPException(status_code=404, detail=f"Session not found")

    # 업데이트할 필드 준비
    updates = {}
    updated_fields = []

    if request.plan is not None:
        updates["plan"] = request.plan
        # Plan history 기록
        updates["plan_history"] = [{
            "plan": request.plan,
            "reason": "user_modification",
            "modified_by": "api"  # 향후 user_id로 변경
        }]
        updated_fields.append("plan")

    if request.todos is not None:
        updates["todos"] = request.todos
        # User interaction 기록
        updates["user_interactions"] = [{
            "type": "modify_todo",
            "details": {
                "action": "bulk_update",
                "count": len(request.todos)
            }
        }]
        updated_fields.append("todos")

    if request.context is not None:
        updates["context"] = request.context
        updated_fields.append("context")

    # State 업데이트
    await graph.update_state(config, values=updates)

    return {
        "success": True,
        "message": "State updated successfully",
        "updated_fields": updated_fields
    }
```

---

### 4. POST /api/sessions/{thread_id}/todos

**Todo 추가**

**목적**: 런타임에 새 Todo 추가

**요청**
```http
POST /api/sessions/session_001/todos
Content-Type: application/json

{
  "task": "알레르기 체크",
  "agent": "DietAgent",
  "priority": 1
}
```

**응답**
```json
{
  "success": true,
  "todo": {
    "id": "uuid-generated",
    "task": "알레르기 체크",
    "agent": "DietAgent",
    "priority": 1,
    "status": "pending",
    "step": 11,
    "created_at": "2025-11-06T09:35:00",
    "updated_at": "2025-11-06T09:35:00"
  }
}
```

**구현 위치**: `backend/app/api/todos.py` (신규 파일)

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/api/sessions", tags=["todos"])

class TodoCreateRequest(BaseModel):
    task: str
    agent: str
    priority: Optional[int] = None
    details: Optional[dict] = None

@router.post("/{thread_id}/todos")
async def create_todo(thread_id: str, request: TodoCreateRequest):
    """Todo 추가"""
    checkpointer = await create_checkpointer()
    graph = build_supervisor_graph(checkpointer=checkpointer)
    config = get_session_config(thread_id)

    # 새 Todo 생성 (ID는 Reducer가 자동 생성)
    new_todo = {
        "task": request.task,
        "agent": request.agent,
        "status": "pending"
    }
    if request.priority is not None:
        new_todo["priority"] = request.priority
    if request.details is not None:
        new_todo["details"] = request.details

    # State 업데이트 (Reducer가 ID, timestamp, step 자동 추가)
    await graph.update_state(config, values={
        "todos": [new_todo],
        "user_interactions": [{
            "type": "modify_todo",
            "details": {
                "action": "add",
                "task": request.task
            }
        }]
    })

    # 업데이트된 상태 조회
    state = await graph.aget_state(config)
    # 방금 추가된 Todo 찾기 (마지막 항목)
    todos = state.values.get("todos", [])
    created_todo = todos[-1] if todos else None

    return {
        "success": True,
        "todo": created_todo
    }
```

---

### 5. DELETE /api/sessions/{thread_id}/todos/{todo_id}

**Todo 삭제**

**요청**
```http
DELETE /api/sessions/session_001/todos/uuid-123
```

**응답**
```json
{
  "success": true,
  "message": "Todo deleted successfully",
  "deleted_todo": {
    "id": "uuid-123",
    "task": "칼로리 계산"
  }
}
```

**구현 위치**: `backend/app/api/todos.py`

```python
@router.delete("/{thread_id}/todos/{todo_id}")
async def delete_todo(thread_id: str, todo_id: str):
    """Todo 삭제"""
    checkpointer = await create_checkpointer()
    graph = build_supervisor_graph(checkpointer=checkpointer)
    config = get_session_config(thread_id)

    # 현재 상태 조회
    state = await graph.aget_state(config)
    if not state.values:
        raise HTTPException(status_code=404, detail=f"Session not found")

    todos = state.values.get("todos", [])

    # 삭제할 Todo 찾기
    deleted_todo = None
    updated_todos = []
    for todo in todos:
        if todo.get("id") == todo_id:
            deleted_todo = todo
        else:
            updated_todos.append(todo)

    if not deleted_todo:
        raise HTTPException(status_code=404, detail=f"Todo not found: {todo_id}")

    # State 업데이트
    await graph.update_state(config, values={
        "todos": updated_todos,
        "user_interactions": [{
            "type": "modify_todo",
            "details": {
                "action": "delete",
                "todo_id": todo_id,
                "todo": deleted_todo
            }
        }]
    })

    return {
        "success": True,
        "message": "Todo deleted successfully",
        "deleted_todo": deleted_todo
    }
```

---

### 6. PUT /api/sessions/{thread_id}/todos/{todo_id}

**Todo 수정**

**요청**
```http
PUT /api/sessions/session_001/todos/uuid-123
Content-Type: application/json

{
  "task": "칼로리 계산 (수정됨)",
  "status": "completed",
  "agent": "DietAgent"
}
```

**응답**
```json
{
  "success": true,
  "todo": {
    "id": "uuid-123",
    "task": "칼로리 계산 (수정됨)",
    "status": "completed",
    "agent": "DietAgent",
    "step": 3,
    "updated_at": "2025-11-06T09:36:00"
  }
}
```

**구현 위치**: `backend/app/api/todos.py`

```python
class TodoUpdateRequest(BaseModel):
    task: Optional[str] = None
    agent: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[int] = None
    details: Optional[dict] = None

@router.put("/{thread_id}/todos/{todo_id}")
async def update_todo(thread_id: str, todo_id: str, request: TodoUpdateRequest):
    """Todo 수정"""
    checkpointer = await create_checkpointer()
    graph = build_supervisor_graph(checkpointer=checkpointer)
    config = get_session_config(thread_id)

    # 현재 상태 조회
    state = await graph.aget_state(config)
    if not state.values:
        raise HTTPException(status_code=404, detail=f"Session not found")

    todos = state.values.get("todos", [])

    # Todo 존재 확인
    todo_exists = any(todo.get("id") == todo_id for todo in todos)
    if not todo_exists:
        raise HTTPException(status_code=404, detail=f"Todo not found: {todo_id}")

    # 업데이트 데이터 준비
    updates = {"id": todo_id}
    if request.task is not None:
        updates["task"] = request.task
    if request.agent is not None:
        updates["agent"] = request.agent
    if request.status is not None:
        updates["status"] = request.status
    if request.priority is not None:
        updates["priority"] = request.priority
    if request.details is not None:
        updates["details"] = request.details

    # State 업데이트 (Reducer가 병합)
    await graph.update_state(config, values={
        "todos": [updates],
        "user_interactions": [{
            "type": "modify_todo",
            "details": {
                "action": "update",
                "todo_id": todo_id,
                "updates": updates
            }
        }]
    })

    # 업데이트된 Todo 조회
    state = await graph.aget_state(config)
    todos = state.values.get("todos", [])
    updated_todo = next((t for t in todos if t.get("id") == todo_id), None)

    return {
        "success": True,
        "todo": updated_todo
    }
```

---

### 7. PUT /api/sessions/{thread_id}/todos/reorder

**Todo 순서 변경**

**요청**
```http
PUT /api/sessions/session_001/todos/reorder
Content-Type: application/json

{
  "todo_ids": ["uuid-3", "uuid-1", "uuid-2"]
}
```

**응답**
```json
{
  "success": true,
  "todos": [
    {"id": "uuid-3", "task": "...", "step": 1},
    {"id": "uuid-1", "task": "...", "step": 2},
    {"id": "uuid-2", "task": "...", "step": 3}
  ]
}
```

**구현 위치**: `backend/app/api/todos.py`

```python
class TodoReorderRequest(BaseModel):
    todo_ids: List[str]

@router.put("/{thread_id}/todos/reorder")
async def reorder_todos(thread_id: str, request: TodoReorderRequest):
    """Todo 순서 변경"""
    checkpointer = await create_checkpointer()
    graph = build_supervisor_graph(checkpointer=checkpointer)
    config = get_session_config(thread_id)

    # 현재 상태 조회
    state = await graph.aget_state(config)
    if not state.values:
        raise HTTPException(status_code=404, detail=f"Session not found")

    todos = state.values.get("todos", [])

    # ID를 key로 하는 dict
    todo_dict = {todo["id"]: todo for todo in todos}

    # 새 순서대로 재정렬
    reordered = []
    for i, todo_id in enumerate(request.todo_ids, start=1):
        if todo_id not in todo_dict:
            raise HTTPException(status_code=400, detail=f"Invalid todo_id: {todo_id}")

        todo = todo_dict[todo_id].copy()
        todo["step"] = i  # step 재할당
        reordered.append(todo)

    # State 업데이트
    await graph.update_state(config, values={
        "todos": reordered,
        "user_interactions": [{
            "type": "modify_todo",
            "details": {
                "action": "reorder",
                "order": request.todo_ids
            }
        }]
    })

    return {
        "success": True,
        "todos": reordered
    }
```

---

### 8. POST /api/sessions/{thread_id}/interrupt

**실행 중단**

**목적**: 사용자가 "중단" 버튼 클릭 또는 "ESC" 키

**요청**
```http
POST /api/sessions/session_001/interrupt
Content-Type: application/json

{
  "reason": "user_requested",
  "message": "잠깐 멈춰"
}
```

**응답**
```json
{
  "success": true,
  "status": "interrupted",
  "message": "Execution interrupted successfully"
}
```

**구현 위치**: `backend/app/api/sessions.py`

```python
class InterruptRequest(BaseModel):
    reason: str = "user_requested"
    message: Optional[str] = None

@router.post("/{thread_id}/interrupt")
async def interrupt_session(thread_id: str, request: InterruptRequest):
    """실행 중단"""
    checkpointer = await create_checkpointer()
    graph = build_supervisor_graph(checkpointer=checkpointer)
    config = get_session_config(thread_id)

    # State 업데이트
    await graph.update_state(config, values={
        "requires_approval": True,
        "user_interactions": [{
            "type": "interrupt",
            "reason": request.reason,
            "details": {"message": request.message or "User requested to interrupt"}
        }]
    })

    return {
        "success": True,
        "status": "interrupted",
        "message": "Execution interrupted successfully"
    }
```

---

### 9. POST /api/sessions/{thread_id}/retry/{todo_id}

**Todo 재시도**

**목적**: 실패한 Todo 다시 실행

**요청**
```http
POST /api/sessions/session_001/retry/uuid-123
```

**응답**
```json
{
  "success": true,
  "message": "Todo retry initiated",
  "todo": {
    "id": "uuid-123",
    "task": "칼로리 계산",
    "status": "pending",
    "retry_count": 1
  }
}
```

**구현 위치**: `backend/app/api/todos.py`

```python
@router.post("/{thread_id}/retry/{todo_id}")
async def retry_todo(thread_id: str, todo_id: str):
    """Todo 재시도"""
    checkpointer = await create_checkpointer()
    graph = build_supervisor_graph(checkpointer=checkpointer)
    config = get_session_config(thread_id)

    # 현재 상태 조회
    state = await graph.aget_state(config)
    if not state.values:
        raise HTTPException(status_code=404, detail=f"Session not found")

    # Todo 찾기
    todos = state.values.get("todos", [])
    target_todo = next((t for t in todos if t.get("id") == todo_id), None)

    if not target_todo:
        raise HTTPException(status_code=404, detail=f"Todo not found: {todo_id}")

    # 재시도 카운트 증가
    retry_count = target_todo.get("retry_count", 0) + 1

    # State 업데이트
    await graph.update_state(config, values={
        "todos": [{
            "id": todo_id,
            "status": "pending",  # 다시 pending으로
            "retry_count": retry_count,
            "error": None  # 에러 초기화
        }],
        "user_interactions": [{
            "type": "retry",
            "details": {
                "todo_id": todo_id,
                "retry_count": retry_count
            }
        }]
    })

    # 업데이트된 Todo 조회
    state = await graph.aget_state(config)
    todos = state.values.get("todos", [])
    updated_todo = next((t for t in todos if t.get("id") == todo_id), None)

    return {
        "success": True,
        "message": "Todo retry initiated",
        "todo": updated_todo
    }
```

---

### 10. GET /api/agents

**사용 가능한 Agent 목록 조회**

**요청**
```http
GET /api/agents
```

**응답**
```json
{
  "agents": [
    {
      "name": "DietAgent",
      "capabilities": ["DIET_PLANNING", "NUTRITION_ANALYSIS"],
      "description": "식단 계획 및 영양 분석 Agent"
    },
    {
      "name": "WorkoutAgent",
      "capabilities": ["WORKOUT_PLANNING", "EXERCISE_TRACKING"],
      "description": "운동 계획 및 추적 Agent"
    }
  ],
  "total": 2
}
```

**구현 위치**: `backend/app/api/agents.py` (신규 파일)

```python
from fastapi import APIRouter
from backend.app.octostrator.agents.base.agent_registry import get_all_agents

router = APIRouter(prefix="/api/agents", tags=["agents"])

@router.get("")
async def list_agents():
    """사용 가능한 Agent 목록"""
    agents = get_all_agents()

    agent_list = []
    for name, agent_class in agents.items():
        agent_list.append({
            "name": name,
            "capabilities": [cap.value for cap in agent_class.capabilities],
            "description": agent_class.__doc__ or ""
        })

    return {
        "agents": agent_list,
        "total": len(agent_list)
    }
```

---

### 11. PUT /api/sessions/{thread_id}/todos/{todo_id}/agent

**Todo의 Agent 변경**

**요청**
```http
PUT /api/sessions/session_001/todos/uuid-123/agent
Content-Type: application/json

{
  "agent": "WorkoutAgent"
}
```

**응답**
```json
{
  "success": true,
  "todo": {
    "id": "uuid-123",
    "task": "칼로리 계산",
    "agent": "WorkoutAgent",
    "previous_agent": "DietAgent"
  }
}
```

**구현 위치**: `backend/app/api/todos.py`

```python
class AgentChangeRequest(BaseModel):
    agent: str

@router.put("/{thread_id}/todos/{todo_id}/agent")
async def change_todo_agent(thread_id: str, todo_id: str, request: AgentChangeRequest):
    """Todo의 Agent 변경"""
    checkpointer = await create_checkpointer()
    graph = build_supervisor_graph(checkpointer=checkpointer)
    config = get_session_config(thread_id)

    # Agent 존재 확인
    from backend.app.octostrator.agents.base.agent_registry import get_all_agents
    agents = get_all_agents()
    if request.agent not in agents:
        raise HTTPException(status_code=400, detail=f"Unknown agent: {request.agent}")

    # 현재 상태 조회
    state = await graph.aget_state(config)
    if not state.values:
        raise HTTPException(status_code=404, detail=f"Session not found")

    # Todo 찾기
    todos = state.values.get("todos", [])
    target_todo = next((t for t in todos if t.get("id") == todo_id), None)

    if not target_todo:
        raise HTTPException(status_code=404, detail=f"Todo not found: {todo_id}")

    previous_agent = target_todo.get("agent", "unknown")

    # State 업데이트
    await graph.update_state(config, values={
        "todos": [{
            "id": todo_id,
            "agent": request.agent
        }],
        "user_interactions": [{
            "type": "change_agent",
            "details": {
                "todo_id": todo_id,
                "from_agent": previous_agent,
                "to_agent": request.agent
            }
        }]
    })

    # 업데이트된 Todo 조회
    state = await graph.aget_state(config)
    todos = state.values.get("todos", [])
    updated_todo = next((t for t in todos if t.get("id") == todo_id), None)

    return {
        "success": True,
        "todo": {
            **updated_todo,
            "previous_agent": previous_agent
        }
    }
```

---

## ⚠️ 에러 처리

### 표준 에러 응답 형식

```json
{
  "detail": "Error message here"
}
```

### HTTP 상태 코드

- `200 OK`: 성공
- `400 Bad Request`: 잘못된 요청 (유효성 검증 실패)
- `404 Not Found`: 리소스를 찾을 수 없음
- `500 Internal Server Error`: 서버 에러

### 에러 예시

**세션을 찾을 수 없음**
```json
{
  "detail": "Session not found: session_001"
}
```

**Todo를 찾을 수 없음**
```json
{
  "detail": "Todo not found: uuid-123"
}
```

**잘못된 Agent 이름**
```json
{
  "detail": "Unknown agent: InvalidAgent"
}
```

---

## 💡 사용 예시

### 시나리오 1: 전체 작업 내역 확인

```python
import requests

# 1. 요약 조회
response = requests.get("http://localhost:8000/api/sessions/session_001/summary")
summary = response.json()

print(f"총 {summary['total_steps']}개 작업 수행")
print(f"Todo 진행률: {summary['todo_status']['progress'] * 100}%")
print("\n작업 내역:")
print(summary['actions_summary'])
```

### 시나리오 2: Todo 수정

```python
# 1. 새 Todo 추가
response = requests.post(
    "http://localhost:8000/api/sessions/session_001/todos",
    json={"task": "알레르기 체크", "agent": "DietAgent"}
)
new_todo = response.json()["todo"]
print(f"추가된 Todo ID: {new_todo['id']}")

# 2. Todo 수정
requests.put(
    f"http://localhost:8000/api/sessions/session_001/todos/{new_todo['id']}",
    json={"status": "completed"}
)

# 3. Todo 삭제
requests.delete(
    f"http://localhost:8000/api/sessions/session_001/todos/{new_todo['id']}"
)
```

### 시나리오 3: 실행 중단 및 재개

```python
# 1. 중단
requests.post(
    "http://localhost:8000/api/sessions/session_001/interrupt",
    json={"reason": "user_requested", "message": "잠깐 멈춰"}
)

# 2. 상태 확인
response = requests.get("http://localhost:8000/api/sessions/session_001")
state = response.json()
print(f"상태: {state['status']}")  # "waiting_human"

# 3. 재개
requests.post(
    "http://localhost:8000/api/sessions/session_001/resume",
    json={"approve": True}
)
```

---

**다음 단계**: `IMPLEMENTATION_STEPS_251106.md`에서 단계별 구현 가이드 확인
