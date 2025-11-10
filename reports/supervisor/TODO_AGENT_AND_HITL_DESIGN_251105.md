# TodoAgent & HITL (Human-in-the-Loop) Design

**작성일**: 2025-11-05
**작성자**: AI Assistant
**목적**: TODO 관리 전담 Agent와 Human-in-the-Loop 설계

---

## 1. 핵심 통찰

### 1.1 왜 TodoAgent가 필요한가?

**현재 문제점**
```
Cognitive Supervisor가 TODO 생성 + 수정 + 관리
Execute Supervisor가 TODO 실행 + 추적
→ Supervisor에 너무 많은 책임이 집중
```

**TodoAgent 도입 시 장점**
```
1. 단일 책임 원칙: TODO 관리만 전담
2. HITL 자연스러운 통합: 사용자 개입 지점 명확
3. 복잡도 감소: Supervisor는 조율만
4. 확장성: TODO 관련 기능 독립적 확장
```

### 1.2 TodoAgent의 역할

```
┌─────────────────────────────────────────┐
│              TodoAgent                   │
├─────────────────────────────────────────┤
│ • TODO CRUD (Create, Read, Update, Delete) │
│ • Priority Management                    │
│ • Dependency Resolution                  │
│ • Human Approval Workflow               │
│ • Progress Tracking                      │
│ • History Management                     │
│ • Notification & Alerts                  │
└─────────────────────────────────────────┘
```

---

## 2. 개선된 아키텍처

### 2.1 새로운 시스템 구조

```
User Request
     │
     ▼
┌────────────────────┐
│ COGNITIVE SUPERVISOR│
│ (계획 수립)         │
└────────┬───────────┘
         │ Plan
         ▼
┌────────────────────┐
│    TodoAgent       │ ← NEW! TODO 전담 관리
│  (LangGraph)       │
│                    │
│ - Generate TODOs   │
│ - Manage TODOs     │
│ - HITL Interface   │
└────────┬───────────┘
         │ TODOs
         ▼
┌────────────────────┐     ┌──────────────┐
│ EXECUTE SUPERVISOR │◄────│ Human Review │
│ (실행)             │     │ (Optional)   │
└────────────────────┘     └──────────────┘
```

### 2.2 TodoAgent의 LangGraph Workflow

```python
def build_todo_agent_graph():
    """TodoAgent의 LangGraph workflow"""

    workflow = StateGraph(TodoAgentState)

    # 노드 정의
    workflow.add_node("receive_plan", receive_plan_node)
    workflow.add_node("generate_todos", generate_todos_node)
    workflow.add_node("analyze_dependencies", analyze_dependencies_node)
    workflow.add_node("prioritize", prioritize_todos_node)
    workflow.add_node("human_review", human_review_node)  # HITL
    workflow.add_node("apply_modifications", apply_modifications_node)
    workflow.add_node("finalize", finalize_todos_node)
    workflow.add_node("monitor", monitor_progress_node)

    # 조건부 흐름
    workflow.add_conditional_edges(
        "prioritize",
        requires_human_approval,
        {
            "yes": "human_review",
            "no": "finalize"
        }
    )

    return workflow.compile()
```

---

## 3. TodoAgent 구현

### 3.1 TodoAgent State

```python
from typing import TypedDict, List, Optional, Dict, Any
from enum import Enum

class HumanApprovalStatus(Enum):
    """Human 승인 상태"""
    NOT_REQUIRED = "not_required"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    MODIFIED = "modified"

class TodoAgentState(TypedDict):
    """TodoAgent의 State"""

    # Input
    plan: Dict[str, Any]                    # Cognitive Supervisor의 계획
    user_preferences: Dict[str, Any]        # 사용자 선호도

    # TODO Management
    todos: List[TodoItem]                   # 생성된 TODO 목록
    todo_tree: Dict[str, List[str]]        # 의존성 트리
    execution_order: List[List[str]]        # 실행 순서
    priority_matrix: Dict[str, int]         # 우선순위 매트릭스

    # HITL (Human-in-the-Loop)
    requires_human_approval: bool           # 승인 필요 여부
    human_approval_status: str              # HumanApprovalStatus
    human_feedback: Optional[str]           # 사용자 피드백
    human_modifications: List[Dict]         # 사용자 수정사항
    approval_timeout: Optional[int]         # 승인 타임아웃 (초)

    # Monitoring
    active_todos: List[str]                 # 실행 중인 TODO
    completed_todos: List[str]              # 완료된 TODO
    failed_todos: List[str]                 # 실패한 TODO
    progress_percentage: float               # 진행률

    # History
    modification_history: List[Dict]        # 수정 이력
    execution_history: List[Dict]           # 실행 이력

    # Metadata
    created_at: str
    updated_at: str
    agent_id: str
    session_id: str
```

### 3.2 TodoAgent 클래스

```python
@register_agent("todo_agent")
class TodoAgent(BaseAgent):
    """TODO 관리 전담 Agent"""

    def __init__(self, **kwargs):
        super().__init__(
            agent_id="todo_agent",
            agent_name="TODO Management Agent",
            description="Manages TODOs with HITL support",
            enable_checkpoint=True,  # 상태 저장 필요
            priority=AgentPriority.CRITICAL,  # 최우선
            dependencies=[],  # 독립적
            metadata={
                "supports_hitl": True,
                "max_todos": 100,
                "default_approval_timeout": 300  # 5분
            },
            **kwargs
        )

    def build_graph(self, llm=None) -> StateGraph:
        """TodoAgent workflow 구축"""

        workflow = StateGraph(TodoAgentState)

        # Core nodes
        workflow.add_node("receive_plan", self._receive_plan_node)
        workflow.add_node("generate_todos", self._generate_todos_node)
        workflow.add_node("analyze_dependencies", self._analyze_dependencies_node)
        workflow.add_node("prioritize", self._prioritize_node)

        # HITL nodes
        workflow.add_node("check_approval", self._check_approval_requirement_node)
        workflow.add_node("wait_human", self._wait_for_human_node)
        workflow.add_node("process_feedback", self._process_human_feedback_node)

        # Management nodes
        workflow.add_node("apply_modifications", self._apply_modifications_node)
        workflow.add_node("validate", self._validate_todos_node)
        workflow.add_node("finalize", self._finalize_node)

        # Monitoring node
        workflow.add_node("monitor", self._monitor_progress_node)

        # Edge definitions
        workflow.add_edge(START, "receive_plan")
        workflow.add_edge("receive_plan", "generate_todos")
        workflow.add_edge("generate_todos", "analyze_dependencies")
        workflow.add_edge("analyze_dependencies", "prioritize")
        workflow.add_edge("prioritize", "check_approval")

        # HITL conditional routing
        workflow.add_conditional_edges(
            "check_approval",
            self._route_by_approval_requirement,
            {
                "needs_approval": "wait_human",
                "auto_approve": "finalize",
                "has_modifications": "apply_modifications"
            }
        )

        workflow.add_edge("wait_human", "process_feedback")
        workflow.add_conditional_edges(
            "process_feedback",
            self._route_by_human_feedback,
            {
                "approved": "finalize",
                "rejected": "generate_todos",  # Regenerate
                "modified": "apply_modifications"
            }
        )

        workflow.add_edge("apply_modifications", "validate")
        workflow.add_edge("validate", "finalize")
        workflow.add_edge("finalize", "monitor")
        workflow.add_edge("monitor", END)

        return workflow
```

---

## 4. HITL (Human-in-the-Loop) 구현

### 4.1 Human Approval Workflow

```python
async def _check_approval_requirement_node(self, state: TodoAgentState) -> Dict:
    """승인 필요 여부 판단"""

    todos = state["todos"]

    # 승인이 필요한 조건
    requires_approval = False

    # 1. 고위험 작업 포함
    high_risk_agents = ["payment_agent", "delete_agent", "modify_critical_agent"]
    for todo in todos:
        if todo["agent"] in high_risk_agents:
            requires_approval = True
            break

    # 2. 사용자가 명시적으로 요청
    if state.get("user_preferences", {}).get("always_review", False):
        requires_approval = True

    # 3. TODO 수가 임계값 초과
    if len(todos) > 10:
        requires_approval = True

    # 4. 예상 시간이 임계값 초과
    total_duration = sum(t.get("estimated_duration", 0) for t in todos)
    if total_duration > 600:  # 10분 초과
        requires_approval = True

    return {
        "requires_human_approval": requires_approval,
        "human_approval_status": HumanApprovalStatus.PENDING.value if requires_approval
                                 else HumanApprovalStatus.NOT_REQUIRED.value
    }

async def _wait_for_human_node(self, state: TodoAgentState) -> Dict:
    """Human 입력 대기"""

    # WebSocket으로 사용자에게 알림
    await notify_user_for_approval({
        "session_id": state["session_id"],
        "todos": state["todos"],
        "message": "TODO 목록을 검토해주세요.",
        "timeout": state.get("approval_timeout", 300)
    })

    # Human 입력 대기 (타임아웃 있음)
    human_response = await wait_for_human_input(
        session_id=state["session_id"],
        timeout=state.get("approval_timeout", 300)
    )

    if not human_response:
        # 타임아웃 시 자동 승인
        return {
            "human_approval_status": HumanApprovalStatus.APPROVED.value,
            "human_feedback": "Auto-approved due to timeout"
        }

    return {
        "human_approval_status": human_response["status"],
        "human_feedback": human_response.get("feedback"),
        "human_modifications": human_response.get("modifications", [])
    }
```

### 4.2 Human Interface

```python
class TodoHumanInterface:
    """사용자와 TODO 상호작용 인터페이스"""

    async def present_todos_for_review(self, todos: List[TodoItem]) -> Dict:
        """TODO 목록을 사용자에게 표시"""

        formatted_todos = {
            "todos": [
                {
                    "id": todo["id"],
                    "title": todo["title"],
                    "agent": todo["agent"],
                    "estimated_time": todo.get("estimated_duration"),
                    "dependencies": todo.get("dependencies", []),
                    "can_modify": True,
                    "can_delete": True,
                    "can_reorder": True
                }
                for todo in todos
            ],
            "actions": [
                {"type": "approve", "label": "승인"},
                {"type": "reject", "label": "거절"},
                {"type": "modify", "label": "수정"},
                {"type": "add", "label": "TODO 추가"},
                {"type": "remove", "label": "TODO 삭제"},
                {"type": "reorder", "label": "순서 변경"}
            ],
            "visualization": self.generate_todo_visualization(todos)
        }

        return formatted_todos

    def generate_todo_visualization(self, todos: List[TodoItem]) -> str:
        """TODO 시각화 (Gantt chart style)"""

        visualization = """
        TODO Timeline:
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

        [TODO_001] Diet Analysis     ████░░░░░░ (5 min)
        [TODO_002] Meal Planning      ░░████░░░░ (5 min)
        [TODO_003] Workout Design     ░░░░████░░ (5 min)
        [TODO_004] Schedule           ░░░░░░████ (5 min)

        Total: 20 minutes
        Dependencies: TODO_002 → TODO_001
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        """

        return visualization
```

### 4.3 Modification Handler

```python
async def _apply_modifications_node(self, state: TodoAgentState) -> Dict:
    """사용자 수정사항 적용"""

    modifications = state.get("human_modifications", [])
    todos = state["todos"]

    for mod in modifications:
        action = mod["action"]

        if action == "add":
            # 새 TODO 추가
            new_todo = self._create_todo_from_user_input(mod["data"])
            todos.append(new_todo)

        elif action == "remove":
            # TODO 삭제
            todo_id = mod["todo_id"]
            todos = [t for t in todos if t["id"] != todo_id]

        elif action == "modify":
            # TODO 수정
            todo_id = mod["todo_id"]
            changes = mod["changes"]
            for todo in todos:
                if todo["id"] == todo_id:
                    todo.update(changes)
                    todo["version"] += 1
                    todo["is_user_modified"] = True

        elif action == "reorder":
            # 순서 변경
            new_order = mod["new_order"]
            todos = self._reorder_todos(todos, new_order)

    # 의존성 재분석
    todo_tree = self._rebuild_dependency_tree(todos)
    execution_order = self._recalculate_execution_order(todos, todo_tree)

    # 수정 이력 저장
    modification_record = {
        "timestamp": datetime.now().isoformat(),
        "modifications": modifications,
        "modified_by": "human",
        "todo_count_before": len(state["todos"]),
        "todo_count_after": len(todos)
    }

    state["modification_history"].append(modification_record)

    return {
        "todos": todos,
        "todo_tree": todo_tree,
        "execution_order": execution_order,
        "human_approval_status": HumanApprovalStatus.MODIFIED.value
    }
```

---

## 5. 통합 플로우

### 5.1 전체 시스템 플로우

```
1. User: "다이어트 계획 만들어줘"
         ↓
2. Cognitive Supervisor: 계획 수립
         ↓
3. TodoAgent: TODO 생성
         ↓
4. [HITL] 사용자 검토 요청
         ↓
5. User: TODO 수정/승인
         ↓
6. TodoAgent: 수정 적용 & 검증
         ↓
7. Execute Supervisor: 실행
         ↓
8. TodoAgent: 진행 상황 모니터링
         ↓
9. User: 실시간 진행률 확인
```

### 5.2 WebSocket 통신

```python
# backend/app/api/websocket_handler.py

async def handle_todo_events(websocket: WebSocket, session_id: str):
    """TODO 관련 WebSocket 이벤트 처리"""

    @websocket.on("todo.review.request")
    async def on_review_request(data):
        """TODO 검토 요청 수신"""
        todos = data["todos"]

        # 사용자에게 TODO 표시
        await websocket.send_json({
            "type": "todo.review.present",
            "data": {
                "todos": todos,
                "actions": ["approve", "reject", "modify"],
                "timeout": 300
            }
        })

    @websocket.on("todo.review.response")
    async def on_review_response(data):
        """사용자 응답 처리"""
        response = data["response"]

        # TodoAgent에 전달
        await todo_agent.process_human_feedback(response)

        # 확인 메시지
        await websocket.send_json({
            "type": "todo.review.confirmed",
            "message": f"TODO를 {response['action']}했습니다."
        })

    @websocket.on("todo.progress.subscribe")
    async def on_progress_subscribe(data):
        """진행 상황 구독"""
        # 실시간 업데이트 시작
        asyncio.create_task(
            stream_todo_progress(websocket, session_id)
        )

async def stream_todo_progress(websocket: WebSocket, session_id: str):
    """TODO 진행 상황 스트리밍"""

    while True:
        progress = await todo_agent.get_progress(session_id)

        await websocket.send_json({
            "type": "todo.progress.update",
            "data": {
                "total": progress["total"],
                "completed": progress["completed"],
                "failed": progress["failed"],
                "percentage": progress["percentage"],
                "current_todo": progress["current"],
                "estimated_remaining": progress["eta"]
            }
        })

        await asyncio.sleep(1)  # 1초마다 업데이트
```

---

## 6. Frontend Integration

### 6.1 React Component

```typescript
// frontend/src/components/TodoReview.tsx

interface Todo {
  id: string;
  title: string;
  agent: string;
  estimatedDuration: number;
  dependencies: string[];
}

const TodoReviewComponent: React.FC = () => {
  const [todos, setTodos] = useState<Todo[]>([]);
  const [isReviewing, setIsReviewing] = useState(false);

  // WebSocket 연결
  useEffect(() => {
    socket.on('todo.review.present', (data) => {
      setTodos(data.todos);
      setIsReviewing(true);
    });
  }, []);

  const handleApprove = () => {
    socket.emit('todo.review.response', {
      response: {
        action: 'approve',
        todos: todos
      }
    });
    setIsReviewing(false);
  };

  const handleModify = (todoId: string, changes: Partial<Todo>) => {
    const updatedTodos = todos.map(todo =>
      todo.id === todoId ? { ...todo, ...changes } : todo
    );
    setTodos(updatedTodos);
  };

  const handleReorder = (dragIndex: number, dropIndex: number) => {
    const reordered = arrayMove(todos, dragIndex, dropIndex);
    setTodos(reordered);
  };

  return (
    <Dialog open={isReviewing}>
      <DialogTitle>TODO 검토</DialogTitle>
      <DialogContent>
        <DragDropContext onDragEnd={handleReorder}>
          <Droppable droppableId="todos">
            {(provided) => (
              <List {...provided.droppableProps} ref={provided.innerRef}>
                {todos.map((todo, index) => (
                  <Draggable key={todo.id} draggableId={todo.id} index={index}>
                    {(provided) => (
                      <TodoItem
                        todo={todo}
                        onModify={handleModify}
                        provided={provided}
                      />
                    )}
                  </Draggable>
                ))}
              </List>
            )}
          </Droppable>
        </DragDropContext>
      </DialogContent>
      <DialogActions>
        <Button onClick={handleApprove}>승인</Button>
        <Button onClick={handleReject}>거절</Button>
        <Button onClick={handleSaveModifications}>수정 저장</Button>
      </DialogActions>
    </Dialog>
  );
};
```

---

## 7. 장점 및 기대효과

### 7.1 TodoAgent 도입 효과

1. **책임 분리**
   - Supervisor: 전략적 결정
   - TodoAgent: TODO 관리
   - Execute: 실행

2. **HITL 자연스러운 통합**
   - 명확한 Human 개입 지점
   - 직관적인 수정 인터페이스

3. **투명성**
   - 사용자가 모든 TODO 확인 가능
   - 실시간 진행 상황 추적

4. **제어권**
   - 사용자가 TODO 수정/삭제/재정렬
   - 실행 전 승인 프로세스

### 7.2 사용자 경험 개선

```
Before: "AI가 알아서 하는데 뭘 하는지 모르겠어"
After: "내가 TODO를 검토하고 수정할 수 있어서 안심돼"
```

---

## 8. 구현 계획

### Phase 1: TodoAgent Core (Day 1-2)
- [ ] TodoAgentState 정의
- [ ] TodoAgent 클래스 구현
- [ ] LangGraph workflow 구축

### Phase 2: HITL Integration (Day 3-4)
- [ ] Human approval workflow
- [ ] Modification handler
- [ ] WebSocket 통신

### Phase 3: Frontend (Day 5-6)
- [ ] TODO Review UI
- [ ] Progress Tracker
- [ ] Modification Interface

### Phase 4: Testing (Day 7)
- [ ] End-to-end 테스트
- [ ] User acceptance 테스트
- [ ] Performance 테스트

---

## 9. 코드 구조

```
backend/app/octostrator/
├── agents/
│   ├── todo/                    # NEW!
│   │   ├── __init__.py
│   │   ├── todo_agent.py        # TodoAgent 구현
│   │   ├── hitl_handler.py      # HITL 처리
│   │   └── todo_interface.py    # User Interface
│   └── base/
│       └── base_agent.py
├── supervisor/
│   ├── cognitive_supervisor.py  # 계획만 수립
│   └── execute_supervisor.py    # 실행만 담당
```

---

## 10. 결론

### TodoAgent를 도입하면:

✅ **Supervisor 복잡도 감소**: TODO 관리를 분리
✅ **HITL 자연스러운 통합**: 사용자 제어권 강화
✅ **투명성 증가**: TODO 가시성 확보
✅ **확장성 개선**: TODO 기능 독립적 확장

### 최종 아키텍처:

```
Cognitive Supervisor (계획)
         ↓
    TodoAgent (관리 + HITL)
         ↓
Execute Supervisor (실행)
```

이제 사용자가 **TODO를 직접 확인하고 수정**할 수 있는 진정한 Human-in-the-Loop 시스템이 됩니다!

---

**작성 완료일**: 2025-11-05
**버전**: 1.0
**문서 위치**: `reports/supervisor/TODO_AGENT_AND_HITL_DESIGN_251105.md`