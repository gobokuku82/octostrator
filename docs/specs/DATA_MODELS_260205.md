# Data Models Specification
**Version**: 2.0 | **Date**: 2026-02-05 | **Status**: Draft

## 1. Overview

시스템 전반에서 사용되는 Pydantic 모델 정의서입니다. 4-Layer 아키텍처의 각 레이어에서 사용되는 데이터 구조를 정의합니다.

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
    SENTIMENT = "sentiment"          # 감성 분석
    KEYWORD = "keyword"              # 키워드 분석
    TREND = "trend"                  # 트렌드 분석
    COMPETITOR = "competitor"        # 경쟁사 분석

    # Content
    REPORT = "report"                # 리포트 생성
    VIDEO = "video"                  # 영상 생성
    AD = "ad"                        # 광고 제작

    # Operation
    SALES = "sales"                  # 영업 자료
    INVENTORY = "inventory"          # 재고 관리
    DASHBOARD = "dashboard"          # 대시보드
```

### 2.2 Todo Status

```python
class TodoStatus(str, Enum):
    """Todo 상태"""
    PENDING = "pending"              # 대기 중
    IN_PROGRESS = "in_progress"      # 실행 중
    COMPLETED = "completed"          # 완료
    FAILED = "failed"                # 실패
    BLOCKED = "blocked"              # 의존성 대기
    SKIPPED = "skipped"              # 건너뜀
    NEEDS_APPROVAL = "needs_approval"# 승인 대기
    CANCELLED = "cancelled"          # 취소됨

class TodoPriority(int, Enum):
    """Todo 우선순위 (0-10, 높을수록 중요)"""
    LOWEST = 0
    LOW = 2
    NORMAL = 5
    HIGH = 7
    CRITICAL = 10
```

### 2.3 Plan & Execution Status

```python
class PlanStatus(str, Enum):
    """Plan 상태"""
    DRAFT = "draft"                  # 초안
    APPROVED = "approved"            # 승인됨
    EXECUTING = "executing"          # 실행 중
    PAUSED = "paused"                # 일시정지
    WAITING = "waiting"              # 사용자 입력 대기
    COMPLETED = "completed"          # 완료
    FAILED = "failed"                # 실패
    CANCELLED = "cancelled"          # 취소

class ExecutionStatus(str, Enum):
    """실행 상태"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class HITLMode(str, Enum):
    """Human-in-the-Loop 모드"""
    RUNNING = "running"              # 정상 실행 중
    PAUSED = "paused"                # 일시정지
    PLAN_EDIT = "plan_edit"          # 플랜 수정 중
    INPUT_REQUEST = "input_request"  # 입력 요청 중
    APPROVAL_WAIT = "approval_wait"  # 승인 대기
```

### 2.4 Tool Types

```python
class ToolType(str, Enum):
    """도구 타입"""
    DATA = "data"                    # 데이터 수집/처리
    ANALYSIS = "analysis"            # 분석
    CONTENT = "content"              # 콘텐츠 생성
    BUSINESS = "business"            # 비즈니스 운영

class ToolParameterType(str, Enum):
    """도구 파라미터 타입"""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"
```

## 3. Intent Models

### 3.1 Entity

```python
class Entity(BaseModel):
    """추출된 엔티티"""
    type: str                        # 엔티티 타입 (brand, product, date, etc.)
    value: str                       # 엔티티 값
    confidence: float                # 신뢰도 (0.0 ~ 1.0)
    metadata: Optional[Dict] = None  # 추가 메타데이터

    # Examples:
    # Entity(type="brand", value="라네즈", confidence=0.95)
    # Entity(type="date_range", value="최근 3개월", confidence=0.88)
```

### 3.2 Intent

```python
class Intent(BaseModel):
    """분류된 의도"""
    domain: IntentDomain             # 최상위 도메인
    category: IntentCategory         # 카테고리
    subcategory: Optional[str]       # 세부 카테고리
    confidence: float                # 신뢰도

    # Example:
    # Intent(domain="analysis", category="sentiment", subcategory="review_analysis", confidence=0.92)

class IntentClassificationResult(BaseModel):
    """의도 분류 결과"""
    intent: Intent                   # 주요 의도
    entities: List[Entity]           # 추출된 엔티티들
    alternatives: List[Intent]       # 대안 의도들
    processing_time_ms: float        # 처리 시간
    requires_clarification: bool     # 명확화 필요 여부
    clarification_question: Optional[str]  # 명확화 질문
```

## 4. Todo Models (v2.0)

### 4.1 Todo Configuration Models

```python
class TodoExecutionConfig(BaseModel):
    """Todo 실행 설정"""
    tool: str                        # 사용할 도구명
    tool_params: Dict[str, Any] = {} # 도구 파라미터
    timeout: int = 300               # 타임아웃 (초)
    max_retries: int = 3             # 최대 재시도
    retry_count: int = 0             # 현재 재시도 횟수

class TodoDataConfig(BaseModel):
    """Todo 데이터 설정"""
    input_data: Optional[Dict] = None    # 입력 데이터
    output_path: Optional[str] = None    # 결과 저장 경로
    expected_result: Optional[str] = None # 기대 결과 설명

class TodoDependencyConfig(BaseModel):
    """Todo 의존성 설정"""
    depends_on: List[str] = []       # 의존하는 Todo ID들
    blocks: List[str] = []           # 이 Todo가 블로킹하는 Todo ID들

class TodoProgress(BaseModel):
    """Todo 진행 상황"""
    percentage: int = 0              # 진행률 (0-100)
    started_at: Optional[datetime]   # 시작 시간
    completed_at: Optional[datetime] # 완료 시간
    error_message: Optional[str]     # 에러 메시지

class TodoApproval(BaseModel):
    """Todo 승인 정보"""
    requires_approval: bool = False  # 승인 필요 여부
    approved_by: Optional[str]       # 승인자
    approved_at: Optional[datetime]  # 승인 시간
    rejection_reason: Optional[str]  # 거부 사유
```

### 4.2 TodoMetadata

```python
class TodoMetadata(BaseModel):
    """Todo 메타데이터 (계층적 구조)"""
    execution: TodoExecutionConfig
    data: TodoDataConfig = TodoDataConfig()
    dependency: TodoDependencyConfig = TodoDependencyConfig()
    progress: TodoProgress = TodoProgress()
    approval: TodoApproval = TodoApproval()
    context: Dict[str, Any] = {}     # 레이어별 추가 컨텍스트
```

### 4.3 TodoItem (Core Model)

```python
class TodoItem(BaseModel):
    """Todo 아이템 (v2.0)"""
    id: str = Field(default_factory=lambda: str(uuid4()))
    title: str                       # Todo 제목
    description: Optional[str]       # 상세 설명
    status: TodoStatus = TodoStatus.PENDING
    priority: int = 5                # 우선순위 (0-10)
    layer: str                       # 실행 레이어 (ml, biz, etc.)
    metadata: TodoMetadata           # 메타데이터

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Methods
    def is_ready(self) -> bool:
        """의존성이 모두 해결되어 실행 가능한지"""
        pass

    def can_execute(self) -> bool:
        """실행 가능 상태인지 (ready + pending)"""
        pass

    def mark_in_progress(self) -> None:
        """실행 시작으로 상태 변경"""
        pass

    def mark_completed(self, result: Dict) -> None:
        """완료로 상태 변경"""
        pass

    def mark_failed(self, error: str) -> None:
        """실패로 상태 변경"""
        pass
```

## 5. Plan Models

### 5.1 PlanChange

```python
class PlanChangeType(str, Enum):
    CREATE = "create"                # 생성
    REPLAN = "replan"                # 재계획
    USER_EDIT = "user_edit"          # 사용자 수정
    AUTO_ADJUST = "auto_adjust"      # 자동 조정

class PlanChange(BaseModel):
    """플랜 변경 이력"""
    id: str = Field(default_factory=lambda: str(uuid4()))
    change_type: PlanChangeType
    description: str                 # 변경 설명
    changed_by: str                  # 변경 주체 (user, system)
    changed_at: datetime = Field(default_factory=datetime.utcnow)
    before_snapshot: Optional[Dict]  # 변경 전 스냅샷
    after_snapshot: Optional[Dict]   # 변경 후 스냅샷
```

### 5.2 PlanVersion

```python
class PlanVersion(BaseModel):
    """플랜 버전"""
    version: str                     # 버전 번호 (v1, v2, ...)
    todos: List[TodoItem]            # 해당 버전의 Todo 목록
    created_at: datetime
    created_by: str                  # user | system
    change_reason: Optional[str]     # 변경 사유
```

### 5.3 Plan

```python
class Plan(BaseModel):
    """플랜 (중앙 관리 객체)"""
    id: str = Field(default_factory=lambda: str(uuid4()))
    session_id: str                  # 세션 ID
    status: PlanStatus = PlanStatus.DRAFT

    # Todo Management
    todos: List[TodoItem] = []       # 현재 Todo 목록
    versions: List[PlanVersion] = [] # 버전 히스토리
    changes: List[PlanChange] = []   # 변경 이력

    # Metadata
    intent: Optional[Dict]           # 원본 의도
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Statistics Methods
    def get_statistics(self) -> Dict:
        """완료/진행/대기 통계 반환"""
        pass

    def get_ready_todos(self) -> List[TodoItem]:
        """실행 가능한 Todo 목록 반환"""
        pass

    def get_current_version(self) -> str:
        """현재 버전 번호 반환"""
        pass
```

## 6. Execution Models

### 6.1 ExecutionResult

```python
class ExecutionResult(BaseModel):
    """실행 결과"""
    success: bool                    # 성공 여부
    data: Optional[Dict]             # 결과 데이터
    error: Optional[str]             # 에러 메시지
    execution_time_ms: float         # 실행 시간 (ms)
    todo_id: str                     # 실행된 Todo ID
    tool_name: str                   # 사용된 도구명
```

### 6.2 ExecutionContext

```python
class ExecutionContext(BaseModel):
    """실행 컨텍스트"""
    session_id: str                  # 세션 ID
    language: str = "KOR"            # 언어 (KOR, EN, JP)
    user_id: Optional[str]           # 사용자 ID

    # Previous Results
    previous_results: Dict[str, Any] = {}  # 이전 Todo 결과들
    collected_reviews: Optional[List] = None
    preprocessed_data: Optional[Dict] = None

    # Insights
    insights: Dict[str, Any] = {}    # 누적 인사이트
```

## 7. Resource Models

### 7.1 AgentResource

```python
class AgentResource(BaseModel):
    """에이전트 리소스"""
    agent_id: str                    # 에이전트 ID
    agent_type: str                  # 에이전트 타입
    capabilities: List[str]          # 처리 가능한 작업 유형

    # Availability
    max_concurrent_tasks: int = 1    # 최대 동시 작업 수
    current_tasks: int = 0           # 현재 작업 수

    # Performance
    avg_execution_time: float        # 평균 실행 시간
    success_rate: float              # 성공률

    # Cost
    cost_per_execution: float        # 실행당 비용

    def is_available(self) -> bool:
        """가용 상태인지"""
        return self.current_tasks < self.max_concurrent_tasks

    def can_handle(self, task_type: str) -> bool:
        """해당 작업 처리 가능한지"""
        return task_type in self.capabilities
```

### 7.2 ResourceAllocation

```python
class ResourceAllocation(BaseModel):
    """리소스 할당"""
    todo_id: str                     # 할당된 Todo ID
    agent_id: str                    # 할당된 에이전트 ID
    allocated_at: datetime           # 할당 시간
    estimated_start: datetime        # 예상 시작 시간
    estimated_end: datetime          # 예상 종료 시간
    estimated_cost: float            # 예상 비용

class ResourcePlan(BaseModel):
    """리소스 계획"""
    plan_id: str                     # Plan ID
    allocations: List[ResourceAllocation]  # 할당 목록
    total_estimated_cost: float      # 총 예상 비용
    total_estimated_time: float      # 총 예상 시간
    parallelization_factor: float    # 병렬화 정도
```

## 8. Execution Graph Models

### 8.1 ExecutionNode

```python
class ExecutionNode(BaseModel):
    """실행 그래프 노드"""
    todo_id: str                     # Todo ID
    dependencies: List[str]          # 의존 노드들
    estimated_duration: float        # 예상 소요 시간
    layer: str                       # 실행 레이어

    # Runtime
    actual_start: Optional[datetime]
    actual_end: Optional[datetime]
    status: ExecutionStatus = ExecutionStatus.PENDING
```

### 8.2 ExecutionGroup

```python
class ExecutionGroup(BaseModel):
    """병렬 실행 그룹"""
    group_id: str                    # 그룹 ID
    nodes: List[ExecutionNode]       # 병렬 실행 가능 노드들
    order: int                       # 실행 순서
```

### 8.3 ExecutionGraph

```python
class ExecutionGraph(BaseModel):
    """실행 DAG"""
    plan_id: str                     # Plan ID
    nodes: Dict[str, ExecutionNode]  # 모든 노드
    groups: List[ExecutionGroup]     # 실행 그룹들
    critical_path: List[str]         # 크리티컬 패스

    def get_critical_path_duration(self) -> float:
        """크리티컬 패스 총 소요 시간"""
        pass

    def get_parallelization_factor(self) -> float:
        """병렬화 정도 (1.0 = 순차, >1 = 병렬)"""
        pass

    def to_mermaid(self) -> str:
        """Mermaid 다이어그램 생성"""
        pass
```

## 9. Tool Models

### 9.1 ToolParameter

```python
class ToolParameter(BaseModel):
    """도구 파라미터"""
    name: str                        # 파라미터명
    type: ToolParameterType          # 타입
    required: bool = False           # 필수 여부
    default: Optional[Any]           # 기본값
    description: str                 # 설명
    validation: Optional[Dict]       # 검증 규칙
```

### 9.2 ToolSpec

```python
class ToolSpec(BaseModel):
    """도구 명세"""
    name: str                        # 도구명 (unique)
    display_name: str                # 표시명
    description: str                 # 설명
    type: ToolType                   # 도구 타입
    layer: str                       # 실행 레이어

    # Parameters
    parameters: List[ToolParameter]  # 입력 파라미터
    output_schema: Optional[Dict]    # 출력 스키마

    # Execution
    executor: str                    # 실행기 클래스 경로
    timeout: int = 300               # 기본 타임아웃

    # Metadata
    tags: List[str] = []             # 태그
    version: str = "1.0.0"           # 버전
    dependencies: List[str] = []     # 의존 도구들
```

## 10. LangGraph State

### 10.1 AgentState

```python
class AgentState(TypedDict):
    """LangGraph 에이전트 상태"""

    # Input
    user_input: str                  # 사용자 입력
    language: str                    # 언어
    current_context: str             # 현재 상황
    target_context: str              # 목표/의도

    # Layer Results
    intent: dict                     # Cognitive 결과
    plan: dict                       # Planning 결과
    todos: Annotated[List[TodoItem], todo_reducer]  # Todo 목록
    ml_result: Annotated[dict, ml_result_reducer]   # ML 실행 결과
    biz_result: Annotated[dict, biz_result_reducer] # 비즈니스 실행 결과
    response: str                    # 최종 응답

    # Control Flow
    next_layer: Optional[str]        # 다음 레이어
    requires_hitl: bool              # HITL 필요 여부
    error: Optional[str]             # 에러 메시지

    # Session & Plan
    session_id: Optional[str]        # 세션 ID
    plan_obj: Optional[Plan]         # Plan 객체
    plan_id: Optional[str]           # Plan ID
    resource_plan: Optional[ResourcePlan]      # 리소스 계획
    execution_graph: Optional[ExecutionGraph]  # 실행 그래프

    # HITL State
    hitl_mode: HITLMode              # HITL 모드
    hitl_message: str                # HITL 메시지
    hitl_pending_input: dict         # 대기 중인 입력 정보
```

---

## Related Documents
- [DB_SCHEMA_260205.md](DB_SCHEMA_260205.md) - Database schema
- [LAYER_SPEC_260205.md](LAYER_SPEC_260205.md) - 4-Layer specifications
- [TODO_SYSTEM_260205.md](TODO_SYSTEM_260205.md) - Todo & HITL system
