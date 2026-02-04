# TodoItem & Metadata 구조 분석 보고서
**Date**: 2026-02-05 | **Status**: Decision Required

## 1. 현재 코드 구조 (Nested)

```python
class TodoItem(BaseModel):
    id: str
    task: str                    # ← 제목 (title로 변경 예정)
    task_type: str = "general"
    layer: Literal[...]          # ← 수정 필요
    status: Literal[...]
    priority: int = 5
    parent_id: Optional[str]
    metadata: TodoMetadata       # ← 중첩 구조
    created_by: str = "system"
    created_at: datetime
    updated_at: datetime
    version: int = 1
    history: List[Dict] = []
```

### 1.1 TodoMetadata 내부 구조

```
TodoMetadata
├── execution: TodoExecutionConfig
│   ├── tool: Optional[str]
│   ├── tool_params: Dict[str, Any] = {}
│   ├── timeout: Optional[int]
│   ├── max_retries: int = 3
│   └── retry_count: int = 0
│
├── data: TodoDataConfig
│   ├── input_data: Optional[Dict]
│   ├── output_path: Optional[str]
│   └── expected_result: Optional[Dict]
│
├── dependency: TodoDependencyConfig
│   ├── depends_on: List[str] = []
│   └── blocks: List[str] = []
│
├── progress: TodoProgress
│   ├── progress_percentage: int = 0
│   ├── started_at: Optional[datetime]
│   ├── completed_at: Optional[datetime]
│   └── error_message: Optional[str]
│
├── approval: TodoApproval
│   ├── requires_approval: bool = False
│   ├── approved_by: Optional[str]
│   ├── approved_at: Optional[datetime]
│   └── user_notes: Optional[str]
│
└── context: Dict[str, Any] = {}
```

---

## 2. 대안: Flat 구조

```python
class TodoItem(BaseModel):
    # Identity
    id: str
    title: str                           # ← task → title
    description: Optional[str]

    # Classification
    layer: Literal["cognitive", "planning", "execution", "response"]
    executor_type: Optional[Literal["ml", "biz"]]  # ← execution 하위 구분
    status: Literal[...]
    priority: int = 5

    # Execution
    tool_name: Optional[str]
    tool_params: Dict[str, Any] = {}
    timeout_seconds: int = 300
    max_retries: int = 3
    retry_count: int = 0

    # Dependencies
    depends_on: List[str] = []
    blocks: List[str] = []

    # Progress
    progress_percentage: int = 0
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    error_message: Optional[str]

    # Approval
    requires_approval: bool = False
    approved_by: Optional[str]
    approved_at: Optional[datetime]

    # Data
    input_data: Optional[Dict]
    output_path: Optional[str]
    result_data: Optional[Dict]

    # Timestamps
    created_at: datetime
    updated_at: datetime
```

---

## 3. 비교 분석

### 3.1 접근 방식 비교

| 구분 | Nested (현재) | Flat (대안) |
|------|--------------|-------------|
| **접근성** | `todo.metadata.execution.tool` | `todo.tool_name` |
| **타이핑** | 많음 | 적음 |
| **코드량** | 6개 클래스 | 1개 클래스 |
| **검증** | 그룹별 검증 가능 | 전체 한번에 검증 |
| **확장성** | 그룹 추가 용이 | 필드 추가 용이 |
| **직렬화** | 중첩 JSON | 평탄 JSON |

### 3.2 사용 예시

**Nested (현재):**
```python
# 도구명 접근
tool = todo.metadata.execution.tool

# 의존성 확인
deps = todo.metadata.dependency.depends_on

# 진행률 업데이트
todo.metadata.progress.progress_percentage = 50
todo.metadata.progress.started_at = datetime.now()
```

**Flat (대안):**
```python
# 도구명 접근
tool = todo.tool_name

# 의존성 확인
deps = todo.depends_on

# 진행률 업데이트
todo.progress_percentage = 50
todo.started_at = datetime.now()
```

### 3.3 JSON 직렬화 비교

**Nested:**
```json
{
  "id": "todo_001",
  "task": "감성 분석",
  "layer": "ml_execution",
  "status": "pending",
  "metadata": {
    "execution": {
      "tool": "sentiment_analyzer",
      "tool_params": {"model": "gpt-4o"},
      "timeout": 300
    },
    "dependency": {
      "depends_on": ["todo_000"],
      "blocks": ["todo_002"]
    },
    "progress": {
      "progress_percentage": 0,
      "started_at": null
    },
    "approval": {
      "requires_approval": false
    }
  }
}
```

**Flat:**
```json
{
  "id": "todo_001",
  "title": "감성 분석",
  "layer": "execution",
  "executor_type": "ml",
  "status": "pending",
  "tool_name": "sentiment_analyzer",
  "tool_params": {"model": "gpt-4o"},
  "timeout_seconds": 300,
  "depends_on": ["todo_000"],
  "blocks": ["todo_002"],
  "progress_percentage": 0,
  "started_at": null,
  "requires_approval": false
}
```

---

## 4. Layer 구조 수정 제안

### 4.1 현재 문제점

```python
# 현재 코드
layer: Literal["cognitive", "planning", "ml_execution", "biz_execution", "response"]
                                   ↑              ↑
                                   └──────────────┴── 이건 execution의 하위!
```

### 4.2 4-Layer 컨셉에 맞는 수정

**Option A: layer + executor_type 분리**
```python
layer: Literal["cognitive", "planning", "execution", "response"]
executor_type: Optional[Literal["ml", "biz", "data"]] = None  # execution일 때만 사용
```

**Option B: layer만 사용 (현재 구조 유지하되 값 변경)**
```python
layer: Literal["cognitive", "planning", "execution", "response"]
# ml/biz 구분은 tool_type 또는 다른 필드로
```

### 4.3 권장안: Option A

```python
class TodoItem(BaseModel):
    # Layer 정보
    layer: Literal["cognitive", "planning", "execution", "response"]

    # Execution Layer 세부 구분 (layer가 "execution"일 때만 유효)
    executor_type: Optional[Literal["ml", "biz", "data"]] = None
```

**사용 예시:**
```python
# 데이터 수집 Todo
TodoItem(
    title="리뷰 수집",
    layer="execution",
    executor_type="data",
    tool_name="data_collector"
)

# ML 분석 Todo
TodoItem(
    title="감성 분석",
    layer="execution",
    executor_type="ml",
    tool_name="sentiment_analyzer"
)

# 응답 생성 Todo
TodoItem(
    title="응답 생성",
    layer="response",
    executor_type=None,  # response layer에선 불필요
    tool_name=None
)
```

---

## 5. 수정 영향도 분석

### 5.1 Nested → Flat 수정 시

| 파일 | 수정 내용 | 영향도 |
|------|----------|--------|
| `models/todo.py` | 구조 변경 | High |
| `planning/planning_node.py` | Todo 생성 코드 | High |
| `execution/*.py` | metadata 접근 | High |
| `workflow_manager/*.py` | Todo 조회/수정 | High |
| `states/reducers.py` | todo_reducer | Medium |
| API schemas | 응답 구조 | Medium |

**예상 수정 파일 수**: 30~50개

### 5.2 layer 값 수정 시

| 파일 | 수정 내용 | 영향도 |
|------|----------|--------|
| `models/todo.py` | Literal 값 변경 | Low |
| `execution/supervisor.py` | 라우팅 로직 | Medium |
| `planning/planning_node.py` | layer 할당 | Medium |

**예상 수정 파일 수**: 10~15개

---

## 6. 결정 포인트

### Q1: Metadata 구조

| 선택지 | 설명 | 수정 규모 |
|--------|------|----------|
| **A. Nested 유지** | 현재 구조 유지, 문서만 수정 | 문서 1개 |
| **B. Flat으로 변경** | 더 간단한 접근, 코드 전면 수정 | 30~50 파일 |
| **C. Hybrid** | 핵심만 flat, 나머지 nested | 15~20 파일 |

### Q2: Layer 구조

| 선택지 | 설명 | 수정 규모 |
|--------|------|----------|
| **A. layer + executor_type 분리 (권장)** | 4-layer 컨셉 유지 | 10~15 파일 |
| **B. 5개 layer 유지** | 현재 구조, 문서 수정 | 문서만 |

---

## 7. 권장 조합

**최소 변경 조합:**
- Metadata: **Nested 유지** (문서 수정)
- Layer: **4개 + executor_type** (코드 수정, 10~15 파일)
- title: **task → title** (코드 수정, 기존 결정)

**이상적 조합 (장기):**
- Metadata: **Flat** (전면 리팩토링)
- Layer: **4개 + executor_type**
- title: **task → title**

→ 단, Flat 전환은 별도 마일스톤으로 진행 권장
