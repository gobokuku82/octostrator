# 02. State Schema 설계

**문서 버전**: 1.0.0  
**작성일**: 2025-11-17  
**관련 문서**: [01_ARCHITECTURE_DESIGN.md](./01_ARCHITECTURE_DESIGN.md)

---

## 📋 목차

1. [State 설계 원칙](#1-state-설계-원칙)
2. [Main State Schema](#2-main-state-schema)
3. [Worker Subgraph State](#3-worker-subgraph-state)
4. [Interrupt Context Schema](#4-interrupt-context-schema)
5. [TODO Item Schema](#5-todo-item-schema)
6. [State 업데이트 전략](#6-state-업데이트-전략)
7. [Reducer 함수](#7-reducer-함수)

---

## 1. State 설계 원칙

### 1.1 핵심 원칙

| 원칙 | 설명 | 이유 |
|------|------|------|
| **최소성** | 필요한 데이터만 포함 | 체크포인터 저장 비용 최소화 |
| **불변성** | 가능한 불변 데이터 사용 | 상태 추적 및 디버깅 용이 |
| **타입 안전성** | TypedDict로 명시적 타입 정의 | 런타임 에러 방지 |
| **계층성** | Main State와 Subgraph State 분리 | 관심사 분리 |

### 1.2 LangGraph State 특징

**Annotation 기반 State**:
```python
from typing import TypedDict, Annotated
from langgraph.graph import add_messages

# LangGraph 1.0 권장 방식
class MainState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    # add_messages: 메시지 리스트에 자동으로 추가 (reducer)
```

**Reducer 함수**:
- State 업데이트 시 어떻게 병합할지 정의
- `add_messages`: 메시지 리스트 자동 병합
- 커스텀 reducer: 사용자 정의 병합 로직

---

## 2. Main State Schema

### 2.1 전체 구조

```python
from typing import TypedDict, Literal, Annotated, Optional, List
from langgraph.graph import add_messages
from langchain_core.messages import BaseMessage
from datetime import datetime

class TodoItem(TypedDict):
    """단일 TODO 항목"""
    id: str
    title: str
    description: str
    status: Literal["pending", "in_progress", "completed", "failed", "paused"]
    assigned_worker: Optional[str]
    result: Optional[dict]
    dependencies: List[str]
    created_at: str
    started_at: Optional[str]
    completed_at: Optional[str]
    error: Optional[str]

class InterruptContext(TypedDict):
    """Interrupt 발생 시 컨텍스트"""
    type: Literal["plan_approval", "todo_modification", "tool_approval", "user_question"]
    message: str
    data: dict
    interrupt_id: str
    timestamp: str

class MainState(TypedDict):
    """Main Graph의 전체 상태"""
    
    # 대화 컨텍스트
    messages: Annotated[List[BaseMessage], add_messages]
    
    # TODO 관리
    todos: List[TodoItem]
    active_todo_id: Optional[str]
    
    # 의도 분석
    current_intent: Optional[Literal["new_task", "modify_task", "continue_task", "simple_qa"]]
    intent_confidence: Optional[float]
    
    # Interrupt 관리
    interrupt_context: Optional[InterruptContext]
    user_interrupted: bool
    
    # 실행 상태
    conversation_mode: Literal["idle", "planning", "executing", "paused", "completed", "error"]
    
    # 메타데이터
    session_id: str
    user_id: Optional[str]
    created_at: str
    updated_at: str
    
    # 에러 처리
    error: Optional[str]
    error_count: int
```

### 2.2 필드별 상세 설명

#### 대화 컨텍스트
```python
messages: Annotated[List[BaseMessage], add_messages]
```
- **타입**: LangChain BaseMessage 리스트
- **Reducer**: `add_messages` (자동 병합)
- **용도**: 전체 대화 히스토리 유지
- **예시**:
  ```python
  [
      HumanMessage(content="AI 보고서 만들어줘"),
      AIMessage(content="TODO를 생성했습니다..."),
      HumanMessage(content="한국 시장도 추가해줘")
  ]
  ```

#### TODO 관리
```python
todos: List[TodoItem]
active_todo_id: Optional[str]
```
- **todos**: 전체 TODO 리스트
- **active_todo_id**: 현재 실행 중인 TODO의 id
- **업데이트**: `update_todos` reducer (커스텀)

#### 의도 분석
```python
current_intent: Optional[Literal[...]]
intent_confidence: Optional[float]
```
- **current_intent**: 분류된 의도
- **intent_confidence**: 확신도 (0.0-1.0)
- **사용**: Intent Analysis Agent에서 설정

#### Interrupt 관리
```python
interrupt_context: Optional[InterruptContext]
user_interrupted: bool
```
- **interrupt_context**: interrupt() 발생 시 컨텍스트
- **user_interrupted**: ESC로 중단 여부
- **사용**: Frontend ESC 감지 → True 설정

#### 실행 상태
```python
conversation_mode: Literal[...]
```
- **idle**: 대기 중
- **planning**: TODO 생성 중
- **executing**: TODO 실행 중
- **paused**: 사용자 중단
- **completed**: 모든 TODO 완료
- **error**: 에러 발생

---

## 3. Worker Subgraph State

### 3.1 전체 구조

```python
class ToolCall(TypedDict):
    """도구 호출 정보"""
    tool_name: str
    parameters: dict
    requires_approval: bool
    result: Optional[dict]
    error: Optional[str]

class WorkerState(TypedDict):
    """Worker Subgraph 상태"""
    
    # 현재 작업
    current_todo: TodoItem
    
    # 도구 실행
    tool_calls: List[ToolCall]
    
    # 중간 결과
    intermediate_results: List[dict]
    
    # 최종 결과
    final_result: Optional[dict]
    
    # 메시지 (Subgraph 내부용)
    worker_messages: Annotated[List[BaseMessage], add_messages]
    
    # 에러
    error: Optional[str]
```

### 3.2 필드별 설명

#### current_todo
```python
current_todo: TodoItem
```
- Main State의 `todos`에서 현재 TODO를 전달받음
- Worker는 이 TODO를 실행

#### tool_calls
```python
tool_calls: List[ToolCall]
```
- 실행할 도구 호출 리스트
- 각 도구 호출은 승인 필요 여부 포함

#### intermediate_results
```python
intermediate_results: List[dict]
```
- 도구 실행 결과들
- 최종 결과 생성 시 참고

#### final_result
```python
final_result: Optional[dict]
```
- Worker의 최종 출력
- Main State의 `completed_todo`로 반환

---

## 4. Interrupt Context Schema

### 4.1 전체 구조

```python
class InterruptContext(TypedDict):
    type: Literal["plan_approval", "todo_modification", "tool_approval", "user_question"]
    message: str
    data: dict
    interrupt_id: str
    timestamp: str
```

### 4.2 타입별 데이터 구조

#### Plan Approval
```python
{
    "type": "plan_approval",
    "message": "다음 계획으로 진행할까요?",
    "interrupt_id": "uuid-1234",
    "timestamp": "2025-11-17T10:30:00Z",
    "data": {
        "proposed_todos": [
            {
                "id": "todo_1",
                "title": "데이터 수집",
                "description": "웹 검색으로 최신 AI 트렌드 수집",
                "assigned_worker": "research",
                "dependencies": []
            },
            {
                "id": "todo_2",
                "title": "데이터 분석",
                "description": "수집된 데이터 분석",
                "assigned_worker": "analysis",
                "dependencies": ["todo_1"]
            }
        ]
    }
}
```

#### Tool Approval
```python
{
    "type": "tool_approval",
    "message": "웹 검색을 실행할까요?",
    "interrupt_id": "uuid-5678",
    "timestamp": "2025-11-17T10:35:00Z",
    "data": {
        "tool_name": "web_search",
        "parameters": {
            "query": "2025 AI trends",
            "num_results": 10
        },
        "estimated_cost": "$0.01"
    }
}
```

#### TODO Modification
```python
{
    "type": "todo_modification",
    "message": "어떻게 하시겠습니까?",
    "interrupt_id": "uuid-9012",
    "timestamp": "2025-11-17T10:40:00Z",
    "data": {
        "current_todos": [...],
        "options": ["수정", "계속", "중단"]
    }
}
```

---

## 5. TODO Item Schema

### 5.1 전체 구조

```python
class TodoItem(TypedDict):
    id: str
    title: str
    description: str
    status: Literal["pending", "in_progress", "completed", "failed", "paused"]
    assigned_worker: Optional[str]
    result: Optional[dict]
    dependencies: List[str]
    created_at: str
    started_at: Optional[str]
    completed_at: Optional[str]
    error: Optional[str]
```

### 5.2 필드별 상세

#### id
```python
id: str  # UUID
```
- 고유 식별자
- 생성: `str(uuid.uuid4())`

#### status
```python
status: Literal["pending", "in_progress", "completed", "failed", "paused"]
```
- **pending**: 대기 중 (의존성 미충족)
- **in_progress**: 실행 중
- **completed**: 완료
- **failed**: 실패
- **paused**: 일시 중지 (사용자 중단)

#### assigned_worker
```python
assigned_worker: Optional[str]
```
- Worker 타입: `"research"`, `"analysis"`, `"coding"`, `"writing"`
- Planning Agent가 자동 할당

#### dependencies
```python
dependencies: List[str]  # TODO id 리스트
```
- 선행 TODO의 id
- Supervisor가 의존성 체크
- 예시:
  ```python
  [
      {"id": "todo_1", "dependencies": []},
      {"id": "todo_2", "dependencies": ["todo_1"]},
      {"id": "todo_3", "dependencies": ["todo_1", "todo_2"]}
  ]
  ```

#### result
```python
result: Optional[dict]
```
- Worker의 최종 결과
- 구조:
  ```python
  {
      "summary": "100개의 AI 트렌드 기사 수집",
      "data": [...],
      "artifacts": ["file1.txt", "file2.json"]
  }
  ```

---

## 6. State 업데이트 전략

### 6.1 Command API 활용

```python
from langgraph.types import Command

# 상태 업데이트만
Command(update={"todos": updated_todos})

# 상태 업데이트 + 라우팅
Command(
    update={"todos": updated_todos, "conversation_mode": "executing"},
    goto="supervisor_agent"
)

# Interrupt 재개
Command(resume={"action": "approve"})
```

### 6.2 부분 업데이트

```python
def planning_agent(state):
    # 기존 todos 유지하고 새 TODO 추가
    new_todos = state["todos"] + [new_todo]
    
    return Command(
        update={"todos": new_todos}
    )
```

### 6.3 Overwrite 활용

```python
from langgraph.types import Overwrite

def reset_node(state):
    # Reducer 무시하고 완전히 새로운 값으로 설정
    return {
        "todos": Overwrite([]),
        "messages": Overwrite([])
    }
```

---

## 7. Reducer 함수

### 7.1 add_messages (기본 제공)

```python
from langgraph.graph import add_messages

# 자동으로 메시지 리스트에 추가
messages: Annotated[List[BaseMessage], add_messages]

# 동작 방식
# 기존: [msg1, msg2]
# 업데이트: [msg3]
# 결과: [msg1, msg2, msg3]
```

### 7.2 커스텀 Reducer: update_todos

```python
def update_todos(existing: List[TodoItem], updates: List[TodoItem]) -> List[TodoItem]:
    """
    TODO 리스트를 업데이트하는 커스텀 reducer
    - id가 같으면 병합
    - id가 없으면 추가
    """
    todo_dict = {todo["id"]: todo for todo in existing}
    
    for update in updates:
        todo_id = update["id"]
        if todo_id in todo_dict:
            # 기존 TODO 업데이트
            todo_dict[todo_id].update(update)
        else:
            # 새 TODO 추가
            todo_dict[todo_id] = update
    
    return list(todo_dict.values())

# 사용
class MainState(TypedDict):
    todos: Annotated[List[TodoItem], update_todos]
```

### 7.3 커스텀 Reducer: increment_error_count

```python
def increment_error_count(existing: int, increment: int) -> int:
    """에러 카운트 증가"""
    return existing + increment

# 사용
class MainState(TypedDict):
    error_count: Annotated[int, increment_error_count]

# 노드에서
def node(state):
    return {"error_count": 1}  # +1 증가
```

---

## 8. State 초기화

### 8.1 기본 State

```python
def create_initial_state(user_id: str, query: str) -> MainState:
    """초기 State 생성"""
    return {
        "messages": [HumanMessage(content=query)],
        "todos": [],
        "active_todo_id": None,
        "current_intent": None,
        "intent_confidence": None,
        "interrupt_context": None,
        "user_interrupted": False,
        "conversation_mode": "idle",
        "session_id": str(uuid.uuid4()),
        "user_id": user_id,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "error": None,
        "error_count": 0
    }
```

### 8.2 Checkpointer에서 복원

```python
# 기존 thread_id로 복원
config = {"configurable": {"thread_id": thread_id}}
state = await graph.aget_state(config)

# state.values에 전체 State 포함
current_state = state.values
```

---

## 9. State 검증

### 9.1 Pydantic 모델 활용 (선택)

```python
from pydantic import BaseModel, Field, validator

class TodoItemModel(BaseModel):
    id: str = Field(..., description="UUID")
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., max_length=1000)
    status: Literal["pending", "in_progress", "completed", "failed", "paused"]
    assigned_worker: Optional[str] = None
    result: Optional[dict] = None
    dependencies: List[str] = Field(default_factory=list)
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[str] = None
    
    @validator('dependencies')
    def validate_dependencies(cls, v):
        # 순환 의존성 체크
        return v

# 사용
def planning_agent(state):
    todos = [TodoItemModel(**todo) for todo in proposed_todos]
    # 검증 통과 시 State 업데이트
    return Command(update={"todos": [t.dict() for t in todos]})
```

---

## 10. State 디버깅

### 10.1 State 로깅

```python
import logging

logger = logging.getLogger(__name__)

def log_state(state: MainState, node_name: str):
    """State 변경 로깅"""
    logger.info(f"[{node_name}] State Update:")
    logger.info(f"  - Mode: {state['conversation_mode']}")
    logger.info(f"  - TODOs: {len(state['todos'])}")
    logger.info(f"  - Active TODO: {state['active_todo_id']}")
    logger.info(f"  - User Interrupted: {state['user_interrupted']}")
```

### 10.2 Checkpointer 히스토리

```python
# 모든 체크포인트 조회
config = {"configurable": {"thread_id": thread_id}}
history = await graph.aget_state_history(config)

for i, checkpoint in enumerate(history):
    print(f"Checkpoint {i}:")
    print(f"  - Mode: {checkpoint.values['conversation_mode']}")
    print(f"  - TODOs: {len(checkpoint.values['todos'])}")
```

---

## 11. 성능 최적화

### 11.1 UntrackedValue 활용

```python
from langgraph.types import UntrackedValue

def node(state):
    # API 키 등 민감 정보는 체크포인터에 저장 안 함
    api_key = UntrackedValue("sk-...")
    result = call_api(api_key)
    
    return {"result": result}
```

### 11.2 State 크기 최소화

```python
# ❌ 나쁜 예: 대용량 데이터를 State에 저장
def node(state):
    return {"large_data": [... 1GB ...]}

# ✅ 좋은 예: 참조만 저장, 실제 데이터는 외부 저장소
def node(state):
    s3_key = upload_to_s3(large_data)
    return {"result": {"s3_key": s3_key}}
```

---

## 12. 다음 단계

State Schema를 바탕으로 각 Phase 구현 문서를 참고하세요:

1. **[03_PHASE1_INTENT_ANALYSIS.md](./03_PHASE1_INTENT_ANALYSIS.md)**
2. **[04_PHASE2_PLANNING.md](./04_PHASE2_PLANNING.md)**
3. **[05_PHASE3_SUPERVISOR.md](./05_PHASE3_SUPERVISOR.md)**

---

**이전 문서**: [01_ARCHITECTURE_DESIGN.md](./01_ARCHITECTURE_DESIGN.md)  
**다음 문서**: [03_PHASE1_INTENT_ANALYSIS.md](./03_PHASE1_INTENT_ANALYSIS.md)
