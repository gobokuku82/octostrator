# Data Models Specification
**Version**: 2.1 | **Date**: 2026-02-05 | **Status**: Draft (Synced with Code)

## 1. Overview

시스템 전반에서 사용되는 Pydantic 모델 정의서입니다. 4-Layer 아키텍처의 각 레이어에서 사용되는 데이터 구조를 정의합니다.

> **Note**: 이 문서는 실제 코드 (`backend/app/dream_agent/models/`)와 동기화되었습니다.

---

## 2. Core Enums

### 2.1 Intent Domain & Category

```python
class IntentDomain(str, Enum):
    """최상위 의도 도메인"""
    ANALYSIS = "analysis"        # 분석 요청
    CONTENT = "content"          # 콘텐츠 생성
    OPERATION = "operation"      # 운영 작업
    INQUIRY = "inquiry"          # 정보 조회

class IntentCategory(str, Enum):
    """도메인 하위 카테고리"""
    # Analysis
    SENTIMENT = "sentiment"
    KEYWORD = "keyword"
    TREND = "trend"
    COMPETITOR = "competitor"

    # Content
    REPORT = "report"
    VIDEO = "video"
    AD = "ad"

    # Operation
    SALES = "sales"
    INVENTORY = "inventory"
    DASHBOARD = "dashboard"
```

### 2.2 Layer & Executor Type (4-Layer Architecture)

```python
class Layer(str, Enum):
    """4-Layer 아키텍처 레이어"""
    COGNITIVE = "cognitive"      # 의도 분석
    PLANNING = "planning"        # 계획 수립
    EXECUTION = "execution"      # 실행
    RESPONSE = "response"        # 응답 생성

class ExecutorType(str, Enum):
    """Execution Layer 하위 실행기 타입"""
    ML = "ml"                    # ML 분석 (sentiment, keyword, etc.)
    BIZ = "biz"                  # 비즈니스 (report, video, etc.)
    DATA = "data"                # 데이터 (collector, preprocessor)
```

**Layer 구조:**
```
┌─────────────────────────────────────────────────────────────┐
│                    4-Layer Architecture                      │
├─────────────────────────────────────────────────────────────┤
│  cognitive  →  planning  →  execution  →  response          │
│                              ↓                              │
│                    ┌─────────┴─────────┐                    │
│                    │   executor_type   │                    │
│                    ├───────────────────┤                    │
│                    │  ml   biz   data  │                    │
│                    └───────────────────┘                    │
└─────────────────────────────────────────────────────────────┘
```

### 2.3 Todo Status

```python
class TodoStatus(str, Literal):
    """Todo 상태"""
    PENDING = "pending"              # 대기 중
    IN_PROGRESS = "in_progress"      # 실행 중
    COMPLETED = "completed"          # 완료
    FAILED = "failed"                # 실패
    BLOCKED = "blocked"              # 의존성 대기
    SKIPPED = "skipped"              # 건너뜀
    NEEDS_APPROVAL = "needs_approval"# 승인 대기
    CANCELLED = "cancelled"          # 취소됨
```

### 2.4 Plan & Execution Status

```python
class PlanStatus(str, Literal):
    """Plan 상태"""
    DRAFT = "draft"
    APPROVED = "approved"
    EXECUTING = "executing"
    PAUSED = "paused"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class ExecutionStatus(str, Enum):
    """실행 상태"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class HITLMode(str, Literal):
    """Human-in-the-Loop 모드"""
    RUNNING = "running"
    PAUSED = "paused"
    PLAN_EDIT = "plan_edit"
    INPUT_REQUEST = "input_request"
    APPROVAL_WAIT = "approval_wait"
```

### 2.5 Tool Types

```python
class ToolType(str, Enum):
    DATA = "data"
    ANALYSIS = "analysis"
    CONTENT = "content"
    BUSINESS = "business"

class ToolParameterType(str, Enum):
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"
```

---

## 3. Intent Models

### 3.1 Entity

```python
class Entity(BaseModel):
    """추출된 엔티티"""
    type: str                        # brand, product, date, etc.
    value: str
    confidence: float                # 0.0 ~ 1.0 (validated)
    metadata: Dict[str, Any] = {}
```

### 3.2 Intent

```python
class Intent(BaseModel):
    """분류된 의도"""
    domain: IntentDomain
    category: Optional[IntentCategory] = None
    subcategory: Optional[str] = None
    confidence: float                # 0.0 ~ 1.0

    # Execution Hints (실제 코드에 존재)
    requires_ml: bool = False        # ML 실행 필요 여부
    requires_biz: bool = False       # Biz 실행 필요 여부

    # Context
    entities: List[Entity] = []
    summary: str = ""                # 의도 요약
    raw_input: str = ""              # 원본 입력
    language: str = "ko"             # 언어 코드
```

### 3.3 IntentClassificationResult

```python
class IntentClassificationResult(BaseModel):
    """의도 분류 결과"""
    intent: Intent
    alternatives: List[Intent] = []
    processing_time_ms: float = 0.0
```

---

## 4. Todo Models

### 4.1 TodoItem 구조 개요

> **결정 필요**: Metadata 구조 (Nested vs Flat)
> 현재 코드는 **Nested** 구조입니다. 아래 4.5절에서 비교 분석을 확인하세요.

### 4.2 Todo Configuration Models (현재: Nested)

```python
class TodoExecutionConfig(BaseModel):
    """실행 설정"""
    tool: Optional[str] = None       # 사용할 도구명
    tool_params: Dict[str, Any] = {}
    timeout: Optional[int] = None    # 타임아웃 (초)
    max_retries: int = 3
    retry_count: int = 0

class TodoDataConfig(BaseModel):
    """데이터 설정"""
    input_data: Optional[Dict[str, Any]] = None
    output_path: Optional[str] = None
    expected_result: Optional[Dict[str, Any]] = None

class TodoDependencyConfig(BaseModel):
    """의존성 설정"""
    depends_on: List[str] = []       # 선행 Todo ID들
    blocks: List[str] = []           # 후행 Todo ID들

class TodoProgress(BaseModel):
    """진행 상황"""
    progress_percentage: int = 0     # 0-100
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None

class TodoApproval(BaseModel):
    """승인 정보"""
    requires_approval: bool = False
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    user_notes: Optional[str] = None
```

### 4.3 TodoMetadata (Nested Container)

```python
class TodoMetadata(BaseModel):
    """중첩 메타데이터 컨테이너"""
    execution: TodoExecutionConfig
    data: TodoDataConfig = TodoDataConfig()
    dependency: TodoDependencyConfig = TodoDependencyConfig()
    progress: TodoProgress = TodoProgress()
    approval: TodoApproval = TodoApproval()
    context: Dict[str, Any] = {}
```

### 4.4 TodoItem (Core Model)

```python
class TodoItem(BaseModel):
    """Todo 아이템"""
    # Identity
    id: str = Field(default_factory=lambda: str(uuid4()))

    # Basic Info (title로 변경 예정, 현재 코드는 task)
    title: str                       # 작업 제목
    task_type: str = "general"       # 작업 타입
    description: Optional[str] = None

    # 4-Layer Classification
    layer: Literal["cognitive", "planning", "execution", "response"]
    executor_type: Optional[Literal["ml", "biz", "data"]] = None  # execution일 때만

    # Status
    status: Literal[
        "pending", "in_progress", "completed", "failed",
        "blocked", "skipped", "needs_approval", "cancelled"
    ] = "pending"
    priority: int = 5                # 0-10

    # Hierarchy
    parent_id: Optional[str] = None

    # Metadata (Nested)
    metadata: TodoMetadata

    # Audit
    created_by: str = "system"
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    version: int = 1
    history: List[Dict[str, Any]] = []
```

### 4.5 Metadata 구조 비교 (결정 필요)

#### Option A: Nested (현재 코드)

**장점:**
- 그룹별 관심사 분리
- 그룹 단위 검증 가능
- 확장 시 새 그룹 추가 용이

**단점:**
- 접근 코드가 길어짐: `todo.metadata.execution.tool`
- 중첩 구조로 JSON 크기 증가

**접근 예시:**
```python
# 도구명
tool = todo.metadata.execution.tool

# 의존성
deps = todo.metadata.dependency.depends_on

# 진행률 업데이트
todo.metadata.progress.progress_percentage = 50
```

---

#### Option B: Flat (대안)

**장점:**
- 직관적 접근: `todo.tool_name`
- 단순한 JSON 구조
- 타이핑 감소

**단점:**
- 필드 수가 많아짐 (30+)
- 관심사 분리 어려움

**접근 예시:**
```python
# 도구명
tool = todo.tool_name

# 의존성
deps = todo.depends_on

# 진행률 업데이트
todo.progress_percentage = 50
```

---

#### 비교 표

| 구분 | Nested | Flat |
|------|--------|------|
| 접근 코드 | `todo.metadata.execution.tool` | `todo.tool_name` |
| 클래스 수 | 6개 | 1개 |
| JSON depth | 3 | 1 |
| 그룹 검증 | 가능 | 어려움 |
| 변경 시 영향 | 30~50 파일 | - |

**현재 결정**: Nested 유지 (변경 시 영향 범위 큼)

---

## 5. Plan Models

### 5.1 PlanChange

```python
class PlanChange(BaseModel):
    """플랜 변경 이력"""
    change_id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = Field(default_factory=datetime.now)
    change_type: Literal[
        "create", "add_todo", "remove_todo", "modify_todo",
        "reorder", "replan", "rollback", "user_decision"
    ]
    reason: str
    actor: str = "system"            # system | user | hitl_manager
    affected_todo_ids: List[str] = []
    change_data: Dict[str, Any] = {}

    # HITL Related
    decision_request_id: Optional[str] = None
    decision_action: Optional[str] = None
    decision_data: Optional[Dict[str, Any]] = None
    user_instruction: Optional[str] = None
    replan_summary: Optional[str] = None
```

### 5.2 PlanVersion

```python
class PlanVersion(BaseModel):
    """플랜 버전"""
    version: int
    timestamp: datetime = Field(default_factory=datetime.now)
    todos: List[TodoItem]
    change_id: str
    change_summary: str
    total_todos: int = 0
    ml_todos: int = 0
    biz_todos: int = 0
    estimated_duration_sec: int = 0
```

### 5.3 Plan

```python
class Plan(BaseModel):
    """플랜 (중앙 관리 객체)"""
    plan_id: str = Field(default_factory=lambda: str(uuid4()))
    session_id: str
    current_version: int = 1
    status: Literal[
        "draft", "approved", "executing", "paused",
        "waiting", "completed", "failed", "cancelled"
    ] = "draft"

    # Todo Management
    todos: List[TodoItem] = []
    versions: List[PlanVersion] = []
    changes: List[PlanChange] = []

    # Context
    intent: Dict[str, Any] = {}
    context: Dict[str, Any] = {}

    # Statistics
    total_todos: int = 0
    completed_todos: int = 0
    failed_todos: int = 0

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    approved_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # HITL State
    current_interrupt_type: Optional[Literal["auto", "manual"]] = None
    pending_decision_request_id: Optional[str] = None

    # Methods
    def get_current_version(self) -> Optional[PlanVersion]: ...
    def get_ready_todos(self) -> List[TodoItem]: ...
    def get_todo_statistics(self) -> Dict[str, int]: ...
    def get_progress_percentage(self) -> float: ...
```

---

## 6. Execution Models

### 6.1 ExecutionResult

```python
class ExecutionResult(BaseModel):
    """실행 결과"""
    success: bool
    data: Dict[str, Any] = {}
    error: Optional[str] = None
    todo_id: Optional[str] = None
    tool_name: Optional[str] = None
    executor_name: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    execution_time_ms: float = 0.0
    metadata: Dict[str, Any] = {}
```

### 6.2 ExecutionContext

```python
class ExecutionContext(BaseModel):
    """실행 컨텍스트"""
    session_id: str
    language: str = "ko"
    previous_results: Dict[str, Any] = {}
    reviews: List[Dict] = []
    keywords: List[str] = []
    insights: List[str] = []
    metadata: Dict[str, Any] = {}
```

---

## 7. Resource Models

### 7.1 AgentResource

```python
class AgentResource(BaseModel):
    """에이전트 리소스"""
    agent_id: str = Field(default_factory=lambda: str(uuid4()))
    agent_name: str
    agent_type: Literal["ml", "biz", "utility"]
    hierarchy_level: Literal["worker", "supervisor", "orchestrator"] = "worker"
    parent_supervisor: Optional[str] = None
    status: Literal["idle", "busy", "error", "maintenance"] = "idle"

    # Capacity
    max_concurrent_tasks: int = 1
    current_tasks: List[str] = []

    # Performance
    average_execution_time_sec: float = 60.0
    success_rate: float = 1.0
    total_executions: int = 0
    total_failures: int = 0

    # Cost
    has_cost: bool = False
    cost_per_execution: float = 0.0
    cost_per_second: float = 0.0

    # Metadata
    dependencies: List[str] = []
    required_resources: Dict[str, Any] = {}
    last_execution_at: Optional[datetime] = None
    last_error: Optional[str] = None
    metadata: Dict[str, Any] = {}
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    # Methods
    def is_available(self) -> bool: ...
    def can_accept_task(self) -> bool: ...
    def assign_task(self, todo_id: str): ...
    def release_task(self, todo_id: str, success: bool = True): ...
```

### 7.2 ResourceAllocation & ResourcePlan

```python
class ResourceAllocation(BaseModel):
    """리소스 할당"""
    allocation_id: str = Field(default_factory=lambda: str(uuid4()))
    todo_id: str
    agent_id: str
    agent_name: str
    allocated_at: datetime = Field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    estimated_duration_sec: float = 60.0
    estimated_cost: float = 0.0
    actual_duration_sec: Optional[float] = None
    actual_cost: Optional[float] = None
    status: Literal["allocated", "running", "completed", "failed", "cancelled"] = "allocated"
    success: bool = False
    error: Optional[str] = None

class ResourceConstraints(BaseModel):
    """리소스 제약"""
    max_parallel_ml_agents: int = 3
    max_parallel_biz_agents: int = 2
    max_total_parallel: int = 5
    max_total_cost: Optional[float] = None
    max_total_duration_sec: Optional[int] = None
    timeout_per_agent_sec: int = 300
    optimize_for: Literal["speed", "cost", "balanced"] = "balanced"

class ResourcePlan(BaseModel):
    """리소스 계획"""
    resource_plan_id: str = Field(default_factory=lambda: str(uuid4()))
    plan_id: str
    allocations: List[ResourceAllocation] = []
    constraints: ResourceConstraints
    estimated_total_duration_sec: float = 0.0
    estimated_total_cost: float = 0.0
    status: Literal["draft", "approved", "executing", "completed", "failed"] = "draft"
    optimization_score: float = 0.0
    optimization_notes: List[str] = []
```

---

## 8. Execution Graph Models

### 8.1 ExecutionNode & ExecutionGroup

```python
class ExecutionNode(BaseModel):
    """DAG 노드"""
    node_id: str = Field(default_factory=lambda: str(uuid4()))
    todo_id: str
    task: str
    dependencies: List[str] = []
    dependents: List[str] = []
    layer: str
    agent_name: Optional[str] = None
    estimated_duration_sec: float = 60.0
    parallel_group: int = 0
    depth: int = 0
    status: str = "pending"
    is_critical: bool = False

class ExecutionGroup(BaseModel):
    """병렬 실행 그룹"""
    group_id: int
    nodes: List[ExecutionNode] = []
    total_nodes: int = 0
    ml_nodes: int = 0
    biz_nodes: int = 0
    estimated_duration_sec: float = 0.0
    estimated_cost: float = 0.0
    command_type: str = "parallel"
```

### 8.2 ExecutionGraph

```python
class ExecutionGraph(BaseModel):
    """실행 DAG"""
    graph_id: str = Field(default_factory=lambda: str(uuid4()))
    plan_id: str
    nodes: List[ExecutionNode] = []
    groups: List[ExecutionGroup] = []
    total_nodes: int = 0
    total_groups: int = 0
    max_depth: int = 0
    critical_path: List[str] = []
    critical_path_duration: float = 0.0
    parallelization_factor: float = 1.0
    supports_parallel_execution: bool = False
    mermaid_diagram: str = ""

    # Methods
    def get_node(self, node_id: str) -> Optional[ExecutionNode]: ...
    def get_root_nodes(self) -> List[ExecutionNode]: ...
    def get_leaf_nodes(self) -> List[ExecutionNode]: ...
```

---

## 9. Tool Models

### 9.1 ToolParameter & ToolSpec

```python
class ToolParameter(BaseModel):
    """도구 파라미터"""
    name: str                        # validated, non-empty
    type: ToolParameterType
    required: bool = False
    default: Optional[Any] = None
    description: str = ""

class ToolSpec(BaseModel):
    """도구 명세"""
    name: str                        # validated, normalized
    description: str
    tool_type: ToolType
    version: str = "1.0.0"
    parameters: List[ToolParameter] = []
    executor: str                    # validated, non-empty
    timeout_sec: int = 300
    max_retries: int = 3
    dependencies: List[str] = []
    produces: List[str] = []
    layer: str = "execution"
    tags: List[str] = []
    has_cost: bool = False
    estimated_cost: float = 0.0

    # Methods
    def get_required_params(self) -> List[ToolParameter]: ...
    def to_langchain_schema(self) -> Dict[str, Any]: ...

class ToolRegistry(BaseModel):
    """도구 레지스트리"""
    version: str = "1.0.0"
    tools: Dict[str, ToolSpec] = {}
    last_updated: Optional[str] = None
```

---

## 10. LangGraph State (Critical Section)

> **주의**: LangGraph State는 **TypedDict** 입니다 (Pydantic BaseModel 아님!)
> Reducer를 통해 상태가 자동 병합됩니다.

### 10.1 State vs Pydantic 차이

```
┌─────────────────────────────────────────────────────────────────┐
│                    두 가지 "모델" 개념                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. LangGraph State (AgentState) - TypedDict                    │
│     ├── 그래프 전체에서 공유되는 "상태 컨테이너"                   │
│     ├── Reducer로 자동 병합                                      │
│     └── checkpointer로 저장/복구                                 │
│                                                                  │
│  2. Pydantic Models (TodoItem, Plan, etc.) - BaseModel          │
│     ├── 데이터 검증 & 직렬화                                     │
│     └── State 내부에 저장되는 "데이터 객체"                       │
│                                                                  │
│  관계:                                                           │
│  ┌──────────────────────────────────────────┐                   │
│  │  AgentState (TypedDict)                   │                   │
│  │  ┌────────────────────────────────────┐  │                   │
│  │  │  todos: List[TodoItem]  ← Pydantic │  │                   │
│  │  │  plan_obj: Plan         ← Pydantic │  │                   │
│  │  └────────────────────────────────────┘  │                   │
│  └──────────────────────────────────────────┘                   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 10.2 AgentState (TypedDict)

```python
from typing import TypedDict, Annotated, Optional, List

class AgentState(TypedDict):
    """LangGraph 에이전트 상태 (TypedDict!)"""

    # ===== User Input =====
    user_input: str
    language: str                    # "KOR" | "EN" | "JP"

    # ===== Context =====
    current_context: str
    target_context: str

    # ===== Todo (with Reducer!) =====
    todos: Annotated[List[TodoItem], todo_reducer]

    # ===== Layer Results (with Reducers!) =====
    intent: dict
    plan: dict
    ml_result: Annotated[dict, ml_result_reducer]
    biz_result: Annotated[dict, biz_result_reducer]
    response: str

    # ===== Workflow Control =====
    next_layer: Optional[str]
    requires_hitl: bool
    error: Optional[str]

    # ===== Subgraph Execution =====
    current_ml_todo_id: Optional[str]
    current_biz_todo_id: Optional[str]
    next_ml_tool: Optional[str]
    next_biz_tool: Optional[str]

    # ===== Plan Objects =====
    session_id: Optional[str]
    plan_obj: Optional[Plan]
    plan_id: Optional[str]
    resource_plan: Optional[ResourcePlan]
    execution_graph: Optional[ExecutionGraph]
    cost_estimate: Optional[dict]
    langgraph_commands: Optional[list]
    mermaid_diagram: Optional[str]

    # ===== Intermediate Results =====
    intermediate_results: Optional[dict]

    # ===== HITL Fields =====
    hitl_mode: Optional[str]         # running | paused | plan_edit | input_request | approval_wait
    hitl_requested_field: Optional[str]
    hitl_message: Optional[str]
    hitl_timestamp: Optional[str]
    hitl_pause_reason: Optional[str] # user_request | input_required | approval_required | error_recovery
    hitl_pending_input: Optional[dict]
```

### 10.3 Reducer 동작 원리

```python
# 1. 노드가 반환할 때 - 변경된 것만 반환
def some_node(state: AgentState) -> dict:
    updated_todo = state["todos"][0]
    updated_todo.status = "completed"
    return {"todos": [updated_todo]}  # ← 변경된 것만!

# 2. LangGraph 내부에서 자동 병합
state["todos"] = todo_reducer(
    state["todos"],      # 기존 목록
    [updated_todo]       # 새로운/업데이트 항목
)
```

**todo_reducer 동작:**
```python
def todo_reducer(current: List[TodoItem], updates: List[TodoItem]) -> List[TodoItem]:
    """
    1. ID 기반 병합
       - 같은 ID → 업데이트
       - 새 ID → 추가

    2. 상태 보존
       - completed/failed/skipped → 덮어쓰기 방지

    3. 히스토리 관리
       - 변경 이력 기록
       - 버전 증가
    """
```

**ml_result_reducer / biz_result_reducer:**
```python
def ml_result_reducer(current: dict, update: dict) -> dict:
    """
    1. 재귀적 딕셔너리 병합
    2. 히스토리 관리 (_history 키)
    3. 중복 제거
    """
```

---

## 11. 수정 예정 사항

| 항목 | 현재 코드 | 변경 예정 | 상태 |
|------|----------|----------|------|
| TodoItem.task | `task` | `title` | 코드 수정 예정 |
| layer 값 | 5개 | 4개 + executor_type | 코드 수정 예정 |
| Metadata 구조 | Nested | TBD | 결정 필요 |

---

## Related Documents
- [SYNC_REPORT_260205.md](SYNC_REPORT_260205.md) - 코드/문서 동기화 보고서
- [TODO_METADATA_REPORT_260205.md](TODO_METADATA_REPORT_260205.md) - Metadata 구조 분석
- [DB_SCHEMA_260205.md](DB_SCHEMA_260205.md) - Database schema
- [LAYER_SPEC_260205.md](LAYER_SPEC_260205.md) - 4-Layer specifications
- [TODO_SYSTEM_260205.md](TODO_SYSTEM_260205.md) - Todo & HITL system
