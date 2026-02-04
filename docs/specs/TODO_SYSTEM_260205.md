# Todo System & HITL Specification
**Version**: 2.0 | **Date**: 2026-02-05 | **Status**: Draft

## 1. Overview

기업용 에이전트의 핵심인 Todo 시스템과 Human-in-the-Loop(HITL) 워크플로우 명세입니다.

### 1.1 Core Principles

1. **사용자 개입 우선**: 모든 주요 결정 지점에서 사용자 개입 가능
2. **투명한 진행상황**: 실시간 WebSocket을 통한 상태 업데이트
3. **유연한 수정**: 실행 전/중에 Plan 수정 가능
4. **복구 가능**: 실패 시 재시도 및 대안 경로 제공

---

## 2. Todo Lifecycle

### 2.1 State Machine

```
                                    ┌─────────────┐
                                    │   CREATED   │
                                    └──────┬──────┘
                                           │
                                           ▼
                              ┌────────────────────────┐
                              │        PENDING         │
                              └────────────┬───────────┘
                                           │
                    ┌──────────────────────┼──────────────────────┐
                    │                      │                      │
                    ▼                      ▼                      ▼
           ┌───────────────┐     ┌─────────────────┐     ┌───────────────┐
           │    BLOCKED    │     │   IN_PROGRESS   │     │NEEDS_APPROVAL │
           │ (의존성 대기)  │     │    (실행 중)     │     │  (승인 대기)   │
           └───────┬───────┘     └────────┬────────┘     └───────┬───────┘
                   │                      │                      │
                   │                      │                      │
                   └──────────┬───────────┴───────────┬──────────┘
                              │                       │
                              ▼                       ▼
                     ┌───────────────┐       ┌───────────────┐
                     │   COMPLETED   │       │    FAILED     │
                     │    (완료)      │       │    (실패)      │
                     └───────────────┘       └───────┬───────┘
                                                     │
                                                     ▼
                                            ┌───────────────┐
                                            │   SKIPPED     │
                                            │   CANCELLED   │
                                            └───────────────┘
```

### 2.2 Status Definitions

| Status | Description | Transitions To |
|--------|-------------|----------------|
| `pending` | 실행 대기 중 | `in_progress`, `blocked`, `needs_approval` |
| `blocked` | 의존성 해결 대기 | `pending` (의존성 해결 시) |
| `needs_approval` | 사용자 승인 대기 | `pending`, `cancelled` |
| `in_progress` | 실행 중 | `completed`, `failed` |
| `completed` | 성공적으로 완료 | - (final) |
| `failed` | 실행 실패 | `pending` (재시도), `skipped` |
| `skipped` | 건너뜀 | - (final) |
| `cancelled` | 취소됨 | - (final) |

### 2.3 Status Transition Rules

```python
VALID_TRANSITIONS = {
    "pending": ["in_progress", "blocked", "needs_approval", "cancelled"],
    "blocked": ["pending", "cancelled"],
    "needs_approval": ["pending", "cancelled"],
    "in_progress": ["completed", "failed"],
    "completed": [],  # final state
    "failed": ["pending", "skipped", "cancelled"],
    "skipped": [],  # final state
    "cancelled": [],  # final state
}

def validate_transition(current: str, target: str) -> bool:
    return target in VALID_TRANSITIONS.get(current, [])
```

---

## 3. Todo Structure (v2.0)

### 3.1 Complete TodoItem Schema

```python
class TodoItem(BaseModel):
    """Todo 아이템 v2.0"""

    # === Identity ===
    id: str = Field(default_factory=lambda: str(uuid4()))
    plan_id: Optional[str] = None

    # === Basic Info ===
    title: str                           # 작업 제목
    description: Optional[str] = None    # 상세 설명
    status: TodoStatus = TodoStatus.PENDING
    priority: int = Field(default=5, ge=0, le=10)  # 우선순위 (높을수록 중요)

    # === Execution ===
    layer: str                           # 실행 레이어 (ml, biz, data)
    tool_name: Optional[str] = None      # 사용 도구
    tool_params: Dict[str, Any] = {}     # 도구 파라미터

    # === Dependencies ===
    depends_on: List[str] = []           # 의존하는 Todo ID
    blocks: List[str] = []               # 이 Todo를 기다리는 ID

    # === Execution Config ===
    timeout_seconds: int = 300           # 타임아웃
    max_retries: int = 3                 # 최대 재시도
    retry_count: int = 0                 # 현재 재시도 횟수

    # === Progress ===
    progress_percentage: int = 0         # 진행률 (0-100)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None

    # === Approval ===
    requires_approval: bool = False      # 승인 필요 여부
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None

    # === Data ===
    input_data: Optional[Dict] = None    # 입력 데이터 (이전 Todo 결과 참조)
    output_path: Optional[str] = None    # 결과 저장 경로
    result_data: Optional[Dict] = None   # 실행 결과

    # === Timestamps ===
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # === Metadata ===
    tags: List[str] = []                 # 태그
    context: Dict[str, Any] = {}         # 추가 컨텍스트
```

### 3.2 Example Todo

```json
{
  "id": "todo_001",
  "plan_id": "plan_abc123",
  "title": "라네즈 리뷰 수집",
  "description": "올리브영에서 라네즈 제품 리뷰 수집",
  "status": "pending",
  "priority": 10,

  "layer": "data",
  "tool_name": "data_collector",
  "tool_params": {
    "brand": "라네즈",
    "platform": "oliveyoung",
    "limit": 1000
  },

  "depends_on": [],
  "blocks": ["todo_002", "todo_003"],

  "timeout_seconds": 300,
  "max_retries": 3,
  "retry_count": 0,

  "progress_percentage": 0,
  "requires_approval": false,

  "created_at": "2026-02-05T10:00:00Z",
  "updated_at": "2026-02-05T10:00:00Z"
}
```

---

## 4. Todo Manager

### 4.1 Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        TodoManager                               │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │ TodoCreator │  │ TodoUpdater │  │     TodoValidator       │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
│                                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │ TodoQueries │  │  TodoStore  │  │ TodoFailureRecovery     │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 Core Operations

```python
class TodoManager:
    """Todo 관리자"""

    # === CRUD ===
    async def create(self, todo_data: Dict) -> TodoItem:
        """Todo 생성"""

    async def update(self, todo_id: str, updates: Dict) -> TodoItem:
        """Todo 업데이트"""

    async def delete(self, todo_id: str) -> bool:
        """Todo 삭제"""

    async def get(self, todo_id: str) -> Optional[TodoItem]:
        """Todo 조회"""

    # === Queries ===
    async def get_by_plan(self, plan_id: str) -> List[TodoItem]:
        """Plan의 모든 Todo 조회"""

    async def get_ready_todos(self, plan_id: str) -> List[TodoItem]:
        """실행 가능한 Todo 목록"""

    async def get_pending_approvals(self, plan_id: str) -> List[TodoItem]:
        """승인 대기 중인 Todo 목록"""

    # === Status Management ===
    async def mark_in_progress(self, todo_id: str) -> TodoItem:
        """실행 시작"""

    async def mark_completed(self, todo_id: str, result: Dict) -> TodoItem:
        """완료 처리"""

    async def mark_failed(self, todo_id: str, error: str) -> TodoItem:
        """실패 처리"""

    # === Dependency Management ===
    async def check_dependencies(self, todo_id: str) -> bool:
        """의존성 충족 여부 확인"""

    async def resolve_blocked(self, completed_todo_id: str) -> List[str]:
        """완료된 Todo로 인해 해제되는 blocked Todo들"""

    # === Reordering ===
    async def reorder(self, plan_id: str, todo_ids: List[str]) -> List[TodoItem]:
        """Todo 순서 변경"""

    async def insert_after(
        self, plan_id: str, target_id: str, new_todo: TodoItem
    ) -> TodoItem:
        """특정 Todo 뒤에 삽입"""
```

### 4.3 TodoStore

```python
class TodoStore:
    """Todo 저장소 (In-Memory + Persistence)"""

    def __init__(self):
        self._cache: Dict[str, TodoItem] = {}  # In-memory cache
        self._db: AsyncSession = None           # DB session

    async def save(self, todo: TodoItem) -> None:
        """저장 (캐시 + DB)"""
        self._cache[todo.id] = todo
        await self._persist(todo)

    async def load(self, todo_id: str) -> Optional[TodoItem]:
        """로드 (캐시 우선)"""
        if todo_id in self._cache:
            return self._cache[todo_id]
        return await self._load_from_db(todo_id)

    async def batch_save(self, todos: List[TodoItem]) -> None:
        """배치 저장"""

    async def sync_to_db(self) -> None:
        """캐시를 DB에 동기화"""
```

---

## 5. Human-in-the-Loop (HITL) System

### 5.1 HITL Modes

```python
class HITLMode(str, Enum):
    """HITL 모드"""
    RUNNING = "running"              # 정상 실행 중
    PAUSED = "paused"                # 사용자 일시정지
    PLAN_EDIT = "plan_edit"          # 플랜 수정 중
    INPUT_REQUEST = "input_request"  # 추가 입력 요청 중
    APPROVAL_WAIT = "approval_wait"  # 승인 대기 중
```

### 5.2 HITL Intervention Points

```
User Input → Cognitive → Planning ──┬──→ Execution → Response
                                    │
                              ◆ HITL Gate ◆
                                    │
                        ┌───────────┴───────────┐
                        │   Intervention Types  │
                        ├───────────────────────┤
                        │ 1. Plan Review        │
                        │ 2. Plan Edit          │
                        │ 3. Todo Approval      │
                        │ 4. Input Request      │
                        │ 5. Pause/Resume       │
                        │ 6. Cancel             │
                        └───────────────────────┘
```

### 5.3 HITL Components

#### 5.3.1 Plan Editor

```python
class PlanEditor:
    """플랜 편집기"""

    async def add_todo(
        self,
        plan_id: str,
        todo_data: Dict,
        position: Optional[int] = None
    ) -> TodoItem:
        """Todo 추가"""

    async def remove_todo(self, plan_id: str, todo_id: str) -> bool:
        """Todo 삭제"""

    async def modify_todo(
        self,
        plan_id: str,
        todo_id: str,
        updates: Dict
    ) -> TodoItem:
        """Todo 수정"""

    async def reorder_todos(
        self,
        plan_id: str,
        new_order: List[str]
    ) -> List[TodoItem]:
        """순서 변경"""

    async def apply_nl_edit(
        self,
        plan_id: str,
        natural_language_instruction: str
    ) -> Plan:
        """
        자연어로 플랜 수정
        예: "리뷰 수집 후에 경쟁사 분석도 추가해줘"
        """
```

#### 5.3.2 Approval Manager

```python
class ApprovalManager:
    """승인 관리자"""

    async def request_approval(
        self,
        todo: TodoItem,
        message: str,
        timeout_seconds: int = 3600
    ) -> str:
        """승인 요청"""

    async def approve(
        self,
        todo_id: str,
        approver: str,
        comment: Optional[str] = None
    ) -> TodoItem:
        """승인 처리"""

    async def reject(
        self,
        todo_id: str,
        rejector: str,
        reason: str
    ) -> TodoItem:
        """거부 처리"""

    async def get_pending_approvals(self, session_id: str) -> List[Dict]:
        """대기 중인 승인 목록"""
```

#### 5.3.3 Input Requester

```python
class InputRequester:
    """입력 요청 관리자"""

    async def request_input(
        self,
        session_id: str,
        question: str,
        input_type: str,  # text, choice, file, etc.
        options: Optional[List[str]] = None,
        required: bool = True
    ) -> str:
        """사용자 입력 요청"""

    async def receive_input(
        self,
        request_id: str,
        user_input: Any
    ) -> Dict:
        """입력 수신 처리"""
```

#### 5.3.4 Pause Controller

```python
class PauseController:
    """일시정지 관리자"""

    async def pause(self, session_id: str, reason: Optional[str] = None) -> bool:
        """실행 일시정지"""

    async def resume(self, session_id: str) -> bool:
        """실행 재개"""

    async def cancel(self, session_id: str, reason: str) -> bool:
        """실행 취소"""

    def is_paused(self, session_id: str) -> bool:
        """일시정지 상태 확인"""
```

### 5.4 HITL Event Flow

```
┌──────────────────────────────────────────────────────────────────────┐
│                         HITL Event Flow                               │
└──────────────────────────────────────────────────────────────────────┘

1. Plan Review (플랜 검토)
   ┌─────────┐      ┌─────────────┐      ┌─────────────┐
   │ Planning│ ──→  │ Send Plan   │ ──→  │ User Review │
   │ Complete│      │ via WebSocket│      │             │
   └─────────┘      └─────────────┘      └──────┬──────┘
                                                │
                    ┌───────────────────────────┼──────────────────────┐
                    │                           │                      │
                    ▼                           ▼                      ▼
           ┌───────────────┐          ┌───────────────┐      ┌───────────────┐
           │    Approve    │          │     Edit      │      │    Cancel     │
           └───────┬───────┘          └───────┬───────┘      └───────────────┘
                   │                          │
                   ▼                          ▼
           ┌───────────────┐          ┌───────────────┐
           │   Execution   │          │  Plan Editor  │
           │    Starts     │          │   Opens       │
           └───────────────┘          └───────────────┘

2. Todo Approval (작업 승인)
   ┌─────────┐      ┌─────────────┐      ┌─────────────┐
   │Execution│ ──→  │ requires_   │ ──→  │ Wait for    │
   │  Node   │      │ approval=   │      │ Approval    │
   └─────────┘      │ True        │      └──────┬──────┘
                    └─────────────┘             │
                                               │
                    ┌──────────────────────────┼──────────────┐
                    │                          │              │
                    ▼                          ▼              ▼
           ┌───────────────┐          ┌───────────────┐  ┌─────────┐
           │   Approved    │          │   Rejected    │  │ Timeout │
           └───────┬───────┘          └───────┬───────┘  └────┬────┘
                   │                          │               │
                   ▼                          ▼               ▼
           ┌───────────────┐          ┌───────────────┐  ┌─────────┐
           │   Continue    │          │    Skip or    │  │  Fail   │
           │   Execution   │          │    Replan     │  │  Todo   │
           └───────────────┘          └───────────────┘  └─────────┘

3. Input Request (입력 요청)
   ┌─────────┐      ┌─────────────┐      ┌─────────────┐
   │Execution│ ──→  │ Need More   │ ──→  │ Send Input  │
   │  Node   │      │ Information │      │ Request     │
   └─────────┘      └─────────────┘      └──────┬──────┘
                                                │
                                                ▼
                                       ┌───────────────┐
                                       │ User Provides │
                                       │    Input      │
                                       └───────┬───────┘
                                               │
                                               ▼
                                       ┌───────────────┐
                                       │   Continue    │
                                       │  with Input   │
                                       └───────────────┘
```

### 5.5 WebSocket HITL Messages

```typescript
// HITL WebSocket Message Types

// Plan Review Request
interface PlanReviewMessage {
  type: "hitl_plan_review";
  session_id: string;
  plan_id: string;
  plan: {
    todos: TodoItem[];
    execution_graph: ExecutionGraph;
    estimated_time: number;
    estimated_cost: number;
  };
  message: string;
}

// Approval Request
interface ApprovalRequestMessage {
  type: "hitl_approval_request";
  session_id: string;
  todo_id: string;
  todo: TodoItem;
  message: string;
  timeout_at: string;
}

// Input Request
interface InputRequestMessage {
  type: "hitl_input_request";
  session_id: string;
  request_id: string;
  question: string;
  input_type: "text" | "choice" | "file" | "number";
  options?: string[];
  required: boolean;
}

// Status Update
interface HITLStatusMessage {
  type: "hitl_status_update";
  session_id: string;
  mode: HITLMode;
  message: string;
  data?: any;
}
```

### 5.6 Client-Side HITL Responses

```typescript
// Plan Review Response
interface PlanReviewResponse {
  type: "hitl_plan_response";
  session_id: string;
  plan_id: string;
  action: "approve" | "edit" | "cancel";
  edits?: PlanEdit[];  // if action is "edit"
}

// Approval Response
interface ApprovalResponse {
  type: "hitl_approval_response";
  session_id: string;
  todo_id: string;
  action: "approve" | "reject";
  comment?: string;
  reason?: string;  // if rejected
}

// Input Response
interface InputResponse {
  type: "hitl_input_response";
  session_id: string;
  request_id: string;
  value: any;
}

// Control Commands
interface ControlCommand {
  type: "hitl_control";
  session_id: string;
  command: "pause" | "resume" | "cancel";
  reason?: string;
}
```

---

## 6. Natural Language Plan Modification

### 6.1 NL Plan Modifier

```python
class NLPlanModifier:
    """자연어 플랜 수정기"""

    async def modify(
        self,
        plan: Plan,
        user_instruction: str
    ) -> Plan:
        """
        자연어 명령으로 플랜 수정

        Examples:
            - "리뷰 수집 다음에 경쟁사 분석도 추가해줘"
            - "영상 생성은 빼줘"
            - "감성분석 전에 키워드 분석을 먼저 해줘"
            - "모든 작업의 우선순위를 높여줘"
        """

    async def _parse_instruction(
        self,
        instruction: str,
        current_todos: List[TodoItem]
    ) -> List[PlanEdit]:
        """명령어 파싱"""

    async def _apply_edits(
        self,
        plan: Plan,
        edits: List[PlanEdit]
    ) -> Plan:
        """수정 사항 적용"""
```

### 6.2 Plan Edit Types

```python
class PlanEditType(str, Enum):
    ADD_TODO = "add_todo"
    REMOVE_TODO = "remove_todo"
    MODIFY_TODO = "modify_todo"
    REORDER = "reorder"
    CHANGE_PRIORITY = "change_priority"
    ADD_DEPENDENCY = "add_dependency"
    REMOVE_DEPENDENCY = "remove_dependency"

class PlanEdit(BaseModel):
    """플랜 수정 단위"""
    edit_type: PlanEditType
    target_id: Optional[str]     # 대상 Todo ID
    params: Dict[str, Any]       # 수정 파라미터
    description: str             # 수정 설명
```

---

## 7. Failure Recovery

### 7.1 TodoFailureRecovery

```python
class TodoFailureRecovery:
    """Todo 실패 복구 관리자"""

    async def handle_failure(
        self,
        todo: TodoItem,
        error: Exception
    ) -> RecoveryAction:
        """
        실패 처리 및 복구 액션 결정

        Recovery Actions:
            - RETRY: 재시도
            - SKIP: 건너뛰기
            - REPLAN: 재계획
            - MANUAL: 수동 개입 요청
            - ABORT: 전체 중단
        """

    async def retry(self, todo_id: str) -> TodoItem:
        """재시도"""

    async def skip(self, todo_id: str, reason: str) -> TodoItem:
        """건너뛰기"""

    async def request_manual_intervention(
        self,
        todo: TodoItem,
        error: str
    ) -> None:
        """수동 개입 요청"""
```

### 7.2 Recovery Strategy

```python
RECOVERY_STRATEGIES = {
    "timeout": {
        "max_retries": 2,
        "action": "RETRY",
        "fallback": "SKIP"
    },
    "api_error": {
        "max_retries": 3,
        "action": "RETRY",
        "retry_delay": 5,  # seconds
        "fallback": "MANUAL"
    },
    "validation_error": {
        "action": "MANUAL",
        "request_input": True
    },
    "dependency_failed": {
        "action": "REPLAN",
        "exclude_failed": True
    },
    "critical_error": {
        "action": "ABORT",
        "notify_user": True
    }
}
```

---

## 8. Todo Execution Order

### 8.1 Priority-based Scheduling

```python
def get_next_todo(todos: List[TodoItem]) -> Optional[TodoItem]:
    """
    다음 실행할 Todo 선택

    Selection Criteria (우선순위):
        1. status == 'pending' (필수)
        2. all dependencies completed (필수)
        3. priority (높을수록 먼저)
        4. created_at (오래된 것 먼저, 동점일 때)
    """
    ready_todos = [
        t for t in todos
        if t.status == "pending" and all_deps_completed(t, todos)
    ]

    if not ready_todos:
        return None

    return max(ready_todos, key=lambda t: (t.priority, -t.created_at.timestamp()))
```

### 8.2 Dependency Resolution

```python
def all_deps_completed(todo: TodoItem, all_todos: List[TodoItem]) -> bool:
    """의존성 충족 확인"""
    todo_map = {t.id: t for t in all_todos}

    for dep_id in todo.depends_on:
        dep_todo = todo_map.get(dep_id)
        if not dep_todo:
            continue  # 없는 의존성은 무시
        if dep_todo.status != "completed":
            return False

    return True

def update_blocked_status(todos: List[TodoItem]) -> List[TodoItem]:
    """blocked 상태 업데이트"""
    for todo in todos:
        if todo.status == "pending":
            if not all_deps_completed(todo, todos):
                todo.status = "blocked"
        elif todo.status == "blocked":
            if all_deps_completed(todo, todos):
                todo.status = "pending"
    return todos
```

---

## 9. Plan Versioning

### 9.1 Version Management

```python
class PlanVersionManager:
    """플랜 버전 관리자"""

    async def create_version(
        self,
        plan: Plan,
        change_type: str,
        changed_by: str,
        reason: Optional[str] = None
    ) -> PlanVersion:
        """새 버전 생성"""

    async def get_version(
        self,
        plan_id: str,
        version: str
    ) -> PlanVersion:
        """특정 버전 조회"""

    async def rollback(
        self,
        plan_id: str,
        target_version: str
    ) -> Plan:
        """특정 버전으로 롤백"""

    async def compare_versions(
        self,
        plan_id: str,
        v1: str,
        v2: str
    ) -> Dict:
        """버전 비교"""
```

### 9.2 Change Logging

```python
class PlanChangeLogger:
    """플랜 변경 로거"""

    async def log_change(
        self,
        plan_id: str,
        change: PlanChange
    ) -> None:
        """변경 기록"""

    async def get_change_history(
        self,
        plan_id: str
    ) -> List[PlanChange]:
        """변경 이력 조회"""
```

---

## Related Documents
- [DATA_MODELS_260205.md](DATA_MODELS_260205.md) - Data model definitions
- [LAYER_SPEC_260205.md](LAYER_SPEC_260205.md) - 4-Layer specifications
- [API_SPEC_260205.md](API_SPEC_260205.md) - API specifications
