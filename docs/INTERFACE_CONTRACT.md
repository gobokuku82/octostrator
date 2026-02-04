# Interface Contract (인터페이스 계약)

> **문서 상태 범례**
> - ✅ 구현 완료 / 검증됨
> - ⚠️ 부분 구현 / 검토 필요
> - ❌ 미구현
> - 🔧 사용자 결정 필요

## 1. 개요

이 문서는 Dream Agent 시스템의 모든 레이어 간 인터페이스 계약을 정의합니다.
모든 개발자는 이 계약을 준수해야 합니다.

---

## 2. 레이어 간 인터페이스

> ### ⚠️ 스키마 사용 현황 알림
>
> **현재 상태**: `schemas/` 디렉토리의 I/O 스키마들은 **문서화/명세 목적**으로 정의되어 있으며,
> 실제 노드 코드에서는 사용되지 않습니다. 런타임 검증은 각 노드에서 직접 수행됩니다.
>
> **이중 Intent 시스템**:
> - **레거시 (dict)**: `cognitive_node.py` 출력 → `AgentState["intent"]` → `intent.get("intent_type")`
> - **신규 (Pydantic)**: `models/intent.py` → `Intent.domain` (IntentDomain Enum)
>
> 🔧 **설계 결정 필요**: 스키마 실제 적용 및 Intent 시스템 통일 여부 검토 필요

### 2.1 Cognitive Layer I/O ✅

> 실제 파일: `schemas/cognitive.py`

```python
# 입력
class CognitiveInput(BaseModel):
    user_input: str                         # 필수: 사용자 입력 (빈 문자열 불가)
    language: str = "ko"                    # 선택: 응답 언어
    session_id: Optional[str] = None        # 선택: 세션 ID (자동 생성 가능)
    context: Dict[str, Any] = {}            # 선택: 이전 컨텍스트

# 출력
class CognitiveOutput(BaseModel):
    intent: Intent                          # 필수: 파싱된 Intent
    entities: List[Entity] = []             # 선택: 추출된 엔티티
    requires_clarification: bool = False    # 선택: 추가 질문 필요 여부
    clarification_message: Optional[str]    # 선택: 명확화 메시지
    confidence: float                       # 필수: 0.0-1.0 (Intent.confidence ≥ 0.3)
```

**검증 규칙:**
- `user_input`: 빈 문자열 불가 (strip 후 검사)
- `intent.confidence`: 0.3 미만 시 ValidationError

### 2.2 Planning Layer I/O ✅

> 실제 파일: `schemas/planning.py`

```python
# 입력
class PlanningInput(BaseModel):
    intent: Intent                          # 필수: Cognitive에서 전달
    session_id: str                         # 필수: 빈 문자열 불가
    context: Dict[str, Any] = {}            # 선택: 컨텍스트
    constraints: Dict[str, Any] = {}        # 선택: 제약 조건
    existing_plan: Optional[Plan] = None    # 선택: 재계획 시 기존 Plan
    replan_instruction: Optional[str]       # 선택: 재계획 지시

# 출력
class PlanningOutput(BaseModel):
    plan: Plan                              # 필수: 생성된 Plan
    todos: List[TodoItem]                   # 필수: 최소 1개 이상
    estimated_duration_sec: int = 0         # 선택: ≥ 0
    estimated_cost: float = 0.0             # 선택: ≥ 0.0
    requires_approval: bool = False         # 선택: 사용자 승인 필요
    approval_message: Optional[str]         # 선택: 승인 요청 메시지
    mermaid_diagram: Optional[str]          # 선택: 시각화
```

**검증 규칙:**
- `session_id`: 빈 문자열 불가
- `intent.domain`: None 불가 (IntentDomain Enum)
- `todos`: 최소 1개 이상

> ⚠️ **중요**: 이 스키마는 문서화/명세 목적입니다. 실제 런타임에서는 `planning_node.py`가
> `AgentState["intent"]` (dict 타입)을 직접 접근하며, `intent.get("intent_type")` 키를 사용합니다.
> (이중 Intent 시스템 - 레거시 dict vs Pydantic 모델 공존)

### 2.3 Execution Layer I/O ✅

> 실제 파일: `schemas/execution.py`

```python
# 입력
class ExecutionInput(BaseModel):
    todo: TodoItem                          # 필수: 실행할 Todo
    context: ExecutionContext               # 필수: 실행 컨텍스트
    previous_results: Dict[str, Any] = {}   # 선택: 이전 결과
    use_mock: bool = False                  # 선택: Mock 실행

# 출력
class ExecutionOutput(BaseModel):
    result: ExecutionResult                 # 필수: 실행 결과
    updated_todo: TodoItem                  # 필수: 상태 업데이트된 Todo
    intermediate_data: Dict[str, Any] = {}  # 선택: 중간 데이터
    next_todos: List[str] = []              # 선택: 다음 Todo IDs
    requires_user_input: bool = False       # 선택: 사용자 입력 필요
    user_input_message: Optional[str]       # 선택: 입력 요청 메시지
```

**검증 규칙:**
- `todo.status`: 'pending' 또는 'in_progress'만 허용
- `todo.metadata.execution.tool` 또는 `todo.task_type` 필수
- 실행 실패 시 `updated_todo.status`는 'completed' 불가

> ⚠️ **중요**: 이 스키마는 문서화/명세 목적입니다. 실제 런타임에서는 `execution_node.py`가
> TodoItem Pydantic 모델을 직접 처리하며, 도구 정보는 `todo.metadata.execution.tool` 경로로 접근합니다.

### 2.4 Response Layer I/O ✅

> 실제 파일: `schemas/response.py`

```python
# 입력
class ResponseInput(BaseModel):
    user_input: str                         # 필수: 원본 입력
    language: str = "ko"                    # 선택: ko, en, ja, zh만 허용
    intent_summary: str = ""                # 선택: Intent 요약
    ml_result: Optional[MLResult]           # 선택: ML 분석 결과
    biz_result: Optional[BizResult]         # 선택: 비즈니스 결과
    execution_results: Dict[str, Any] = {}  # 선택: 실행 결과
    error: Optional[str]                    # 선택: 에러 메시지

# 출력
class ResponseOutput(BaseModel):
    response_text: str                      # 필수: 빈 문자열 불가
    summary: str = ""                       # 선택: 요약
    attachments: List[str] = []             # 선택: 첨부 파일
    next_actions: List[str] = []            # 선택: 다음 액션
    metadata: Dict[str, Any] = {}           # 선택: 메타데이터
```

**검증 규칙:**
- `language`: 'ko', 'en', 'ja', 'zh' 중 하나
- `response_text`: 빈 문자열 불가 (strip 후 검사)

---

## 3. 데이터 모델 계약

### 3.1 Intent ✅

> 실제 파일: `models/intent.py`

```python
class IntentDomain(str, Enum):
    """의도 도메인"""
    ANALYSIS = "analysis"       # 분석
    CONTENT = "content"         # 콘텐츠 생성
    OPERATION = "operation"     # 운영
    INQUIRY = "inquiry"         # 질문/문의

class IntentCategory(str, Enum):
    """의도 카테고리"""
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

class Intent(BaseModel):
    domain: IntentDomain                    # 필수: 도메인
    category: Optional[IntentCategory]      # 선택: 카테고리
    subcategory: Optional[str]              # 선택: 세부 카테고리
    confidence: float                       # 필수: 0.0-1.0
    requires_ml: bool = False               # ML 실행 필요 여부
    requires_biz: bool = False              # 비즈니스 로직 필요 여부
    entities: List[Entity] = []             # 추출된 엔티티
    summary: str = ""                       # 요약
    raw_input: str = ""                     # 원본 입력
    language: str = "ko"                    # 언어
```

### 3.2 TodoItem ✅

> 실제 파일: `models/todo.py`

```python
class TodoItem(BaseModel):
    # 기본 정보
    id: str                     # UUID (자동 생성)
    task: str                   # 필수: 작업 내용
    task_type: str = "general"  # 작업 타입

    # 실행 정보
    layer: Literal[             # 필수: 레이어
        "cognitive",
        "planning",
        "ml_execution",
        "biz_execution",
        "response"
    ]
    status: Literal[            # 기본: "pending"
        "pending",
        "in_progress",
        "completed",
        "failed",
        "blocked",
        "skipped",
        "needs_approval",
        "cancelled"
    ]
    priority: int               # 0-10 (기본: 5)

    # 계층 구조
    parent_id: Optional[str]    # 부모 Todo ID

    # 메타데이터 (계층적)
    metadata: TodoMetadata      # 실행/데이터/의존성/진행/승인 정보

    # 타임스탬프
    created_at: datetime
    updated_at: datetime
    version: int = 1
    history: List[Dict] = []
```

**TodoMetadata 구조:**
```python
class TodoMetadata(BaseModel):
    execution: TodoExecutionConfig    # tool, tool_params, timeout, retries
    data: TodoDataConfig              # input_data, output_path
    dependency: TodoDependencyConfig  # depends_on, blocks
    progress: TodoProgress            # percentage, started_at, completed_at
    approval: TodoApproval            # requires_approval, approved_by
    context: Dict[str, Any] = {}      # 추가 컨텍스트
```

### 3.3 ExecutionResult ✅

> 실제 파일: `models/execution.py`

```python
class ExecutionResult(BaseModel):
    success: bool                           # 필수: 성공 여부
    data: Dict[str, Any] = {}               # 실행 결과 데이터
    error: Optional[str]                    # 에러 메시지
    todo_id: Optional[str]                  # Todo ID
    tool_name: Optional[str]                # 실행된 도구
    executor_name: Optional[str]            # 실행자
    started_at: Optional[datetime]          # 시작 시간
    completed_at: Optional[datetime]        # 완료 시간
    execution_time_ms: float = 0.0          # 실행 시간 (ms)
    metadata: Dict[str, Any] = {}           # 메타데이터
```

### 3.4 Entity ✅

> 실제 파일: `models/intent.py`

```python
class Entity(BaseModel):
    type: str                               # 엔티티 타입
    value: str                              # 값
    confidence: float                       # 0.0-1.0
    metadata: Dict[str, Any] = {}           # 추가 정보
```

---

## 4. API 인터페이스

### 4.1 REST API ✅

> 실제 파일: `backend/api/routes/agent.py`

```
POST /api/agent/run
─────────────────────────────────
Request:
{
    "user_input": string,         // 필수
    "session_id": string,         // 선택 (자동 생성)
    "language": string            // 선택 (기본: "ko")
}

Response:
{
    "session_id": string,
    "status": "completed" | "running" | "failed",
    "response": string | null,
    "todos": TodoItem[]
}

POST /api/agent/run-async
─────────────────────────────────
비동기 실행 (WebSocket으로 업데이트 수신)
Response: 즉시 반환, status: "running"

GET /api/agent/status/{session_id}
─────────────────────────────────
Response:
{
    "session_id": string,
    "status": string,
    "response": string | null,
    "error": string | null
}

POST /api/agent/stop/{session_id}
─────────────────────────────────
실행 중지 (HITL)
```

### 4.2 WebSocket API ✅

> 실제 파일: `backend/api/routes/websocket.py`

```
# 연결
ws://localhost:8000/ws/{session_id}

# Server → Client 메시지
{
    "type": "todo_update" | "complete" | "error",
    "data": {
        "todos": TodoItem[],        // todo_update
        "response": string,         // complete
        "error": string             // error
    }
}
```

---

## 5. 도구 인터페이스

### 5.1 ToolSpec (YAML 정의) ✅

> 실제 형식: `tools/definitions/*.yaml`

```yaml
name: tool_name                 # 필수: 고유 식별자
description: "도구 설명"        # 필수
tool_type: analysis             # 필수: 도구 타입
version: "1.0.0"                # 필수: 시맨틱 버전
layer: ml_execution             # 필수: 실행 레이어

executor: ml_agent.sentiment    # 필수: 실행자

parameters:                     # 필수: 파라미터 목록
  - name: param_name
    type: string | array | object
    required: true | false
    default: "기본값"
    description: "설명"

timeout_sec: 120                # 선택: 타임아웃
max_retries: 3                  # 선택: 재시도

dependencies: []                # 선택: 의존 도구
produces: []                    # 선택: 생성 데이터

tags: []                        # 선택: 검색 태그
examples: []                    # 선택: 사용 예시
```

### 5.2 BaseTool 인터페이스 ✅

> 실제 파일: `tools/base_tool.py`

```python
class BaseTool(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """도구 이름"""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """도구 설명"""
        pass

    @abstractmethod
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """도구 실행"""
        pass
```

### 5.3 BaseDomainAgent 인터페이스 ✅

> 실제 파일: `execution/domain/base_agent.py`

```python
class BaseDomainAgent(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """에이전트 이름 (ToolSpec name과 일치)"""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """에이전트 설명"""
        pass

    @property
    def input_schema(self) -> Type[BaseModel]:
        """입력 스키마 (기본: ToolInput)"""
        return ToolInput

    @property
    def output_schema(self) -> Type[BaseModel]:
        """출력 스키마 (기본: ToolOutput)"""
        return ToolOutput

    @abstractmethod
    async def execute(self, input: ToolInput) -> ToolOutput:
        """에이전트 실행"""
        pass
```

---

## 6. 에러 코드 ⚠️

> 🔧 사용자 결정 필요: 에러 코드 체계 확정

| 코드 | 이름 | 설명 | 상태 |
|------|------|------|------|
| E001 | INVALID_INPUT | 입력 검증 실패 | 🔧 |
| E002 | INTENT_PARSE_FAILED | Intent 파싱 실패 | 🔧 |
| E003 | PLAN_GENERATION_FAILED | Plan 생성 실패 | 🔧 |
| E004 | TOOL_NOT_FOUND | 도구 없음 | 🔧 |
| E005 | EXECUTION_FAILED | 실행 실패 | 🔧 |
| E006 | RESPONSE_GENERATION_FAILED | 응답 생성 실패 | 🔧 |
| E007 | VALIDATION_FAILED | 스키마 검증 실패 | 🔧 |
| E008 | DEPENDENCY_CYCLE | 순환 의존성 | 🔧 |

---

## 7. 버전 관리 규칙 ✅

- **Major (x.0.0)**: 기존 계약을 깨는 변경 (필수 필드 추가/제거)
- **Minor (0.x.0)**: 하위 호환 기능 추가 (선택 필드 추가)
- **Patch (0.0.x)**: 버그 수정, 문서 개선

---

## 🔧 사용자 결정 필요 사항

| 항목 | 설명 | 현재 상태 |
|------|------|-----------|
| 에러 코드 체계 | 표준 에러 코드 사용 여부 | 미정의 |
| 지원 언어 | ko, en, ja, zh 외 추가 | 4개 언어 |
| confidence 임계값 | Intent 신뢰도 최소값 | 0.3 |
| 세션 만료 시간 | 세션 유지 기간 | 미정의 |
