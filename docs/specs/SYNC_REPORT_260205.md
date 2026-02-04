# 코드 vs 문서 동기화 보고서
**Date**: 2026-02-05 | **Status**: Review Required

## 1. Executive Summary

| 구분 | 불일치 수 | Critical | Medium | Low |
|------|----------|----------|--------|-----|
| TodoItem | 3 | 2 | 1 | 0 |
| Plan | 1 | 0 | 1 | 0 |
| LangGraph State | 5 | 1 | 3 | 1 |
| Intent | 2 | 0 | 1 | 1 |
| **Total** | **11** | **3** | **6** | **2** |

---

## 2. TodoItem 불일치 (Critical)

### 2.1 필드명: title vs task

| 항목 | 문서 | 실제 코드 | 영향도 |
|------|------|----------|--------|
| 제목 필드 | `title: str` | `task: str` | **Critical** |

**문서 (DATA_MODELS_260205.md):**
```python
class TodoItem(BaseModel):
    title: str                       # Todo 제목
    description: Optional[str]       # 상세 설명
```

**실제 코드 (models/todo.py):**
```python
class TodoItem(BaseModel):
    task: str                        # 작업 내용
    task_type: str = "general"       # 작업 타입
```

**권장**:
- **옵션 A**: 문서 수정 (title → task) - 코드 변경 없음
- **옵션 B**: 코드 수정 (task → title) - 더 직관적이지만 전체 코드 수정 필요

---

### 2.2 layer 값 차이

| 항목 | 문서 | 실제 코드 | 영향도 |
|------|------|----------|--------|
| layer 값 | `"ml"`, `"biz"`, `"data"` | `Literal["cognitive", "planning", "ml_execution", "biz_execution", "response"]` | **Critical** |

**문서:**
```python
layer: str  # 실행 레이어 (ml, biz, data)
```

**실제 코드:**
```python
layer: Literal["cognitive", "planning", "ml_execution", "biz_execution", "response"]
```

**권장**:
- **옵션 A**: 문서 수정 - 실제 5개 레이어로 업데이트
- **옵션 B**: 코드 단순화 - `"data"`, `"ml"`, `"biz"` 3개로 축소 (대규모 수정)

---

### 2.3 Metadata 구조 차이

| 항목 | 문서 | 실제 코드 | 영향도 |
|------|------|----------|--------|
| Flat vs Nested | Flat 구조 제안 | **Nested** (TodoMetadata) | **Medium** |

**문서** (평탄화된 구조):
```python
class TodoItem:
    tool_name: Optional[str]
    tool_params: Dict[str, Any] = {}
    depends_on: List[str] = []
    timeout_seconds: int = 300
    # ... 직접 필드로 정의
```

**실제 코드** (중첩 구조):
```python
class TodoItem:
    metadata: TodoMetadata  # ← 중첩!

class TodoMetadata:
    execution: TodoExecutionConfig   # tool, tool_params, timeout...
    data: TodoDataConfig             # input_data, output_path...
    dependency: TodoDependencyConfig # depends_on, blocks...
    progress: TodoProgress           # started_at, completed_at...
    approval: TodoApproval           # requires_approval...
    context: Dict[str, Any] = {}
```

**권장**: 문서를 실제 중첩 구조로 수정 (실제 코드가 더 체계적)

---

## 3. Plan 불일치

### 3.1 status 값

| 항목 | 문서 | 실제 코드 | 영향도 |
|------|------|----------|--------|
| status | ✅ 일치 | ✅ 일치 | - |

**둘 다 동일:**
```python
Literal["draft", "approved", "executing", "paused", "waiting", "completed", "failed", "cancelled"]
```

### 3.2 추가 필드 누락

| 누락 필드 | 실제 코드 | 영향도 |
|----------|----------|--------|
| `current_interrupt_type` | `Optional[Literal["auto", "manual"]]` | Medium |
| `pending_decision_request_id` | `Optional[str]` | Medium |

---

## 4. LangGraph State 불일치 (Critical)

### 4.1 타입 정의 방식

| 항목 | 문서 | 실제 코드 | 영향도 |
|------|------|----------|--------|
| 기본 타입 | `class AgentState(BaseModel)` | `class AgentState(TypedDict)` | **Critical** |

**이유**: LangGraph는 **TypedDict**를 사용해야 함 (Pydantic 아님)

---

### 4.2 Reducer 누락 (문서에 미설명)

**실제 코드:**
```python
class AgentState(TypedDict):
    todos: Annotated[list[TodoItem], todo_reducer]      # ← Reducer!
    ml_result: Annotated[dict, ml_result_reducer]       # ← Reducer!
    biz_result: Annotated[dict, biz_result_reducer]     # ← Reducer!
```

**Reducer 역할** (문서에 추가 필요):
```python
def todo_reducer(current: List, updates: List) -> List:
    """
    1. ID 기반 병합 (같은 ID = 업데이트)
    2. 새 ID = 추가
    3. completed/failed/skipped 상태 보존
    4. 히스토리 관리 (중복 제거)
    """
```

---

### 4.3 누락된 State 필드들

| 필드 | 용도 | 문서 상태 |
|------|------|----------|
| `current_ml_todo_id` | 현재 실행 중인 ML Todo | ❌ 누락 |
| `current_biz_todo_id` | 현재 실행 중인 Biz Todo | ❌ 누락 |
| `next_ml_tool` | 다음 ML 도구 | ❌ 누락 |
| `next_biz_tool` | 다음 Biz 도구 | ❌ 누락 |
| `intermediate_results` | 중간 결과 | ❌ 누락 |
| `hitl_requested_field` | HITL 요청 필드 | ❌ 누락 |
| `hitl_timestamp` | HITL 타임스탬프 | ❌ 누락 |
| `hitl_pause_reason` | 일시정지 사유 | ❌ 누락 |

---

## 5. Intent 불일치

### 5.1 추가 필드

| 필드 | 실제 코드 | 문서 상태 |
|------|----------|----------|
| `requires_ml` | `bool = False` | ❌ 누락 |
| `requires_biz` | `bool = False` | ❌ 누락 |
| `summary` | `str = ""` | ❌ 누락 |
| `raw_input` | `str = ""` | ❌ 누락 |
| `language` | `str = "ko"` | ❌ 누락 |

---

## 6. 수정 권장 사항

### Option A: 문서 수정 (권장)
- **장점**: 코드 변경 없음, 작동 중인 시스템 유지
- **단점**: 문서가 코드를 따라가야 함
- **작업량**: 문서 1개 수정 (DATA_MODELS_260205.md)

### Option B: 코드 리팩토링
- **장점**: 더 직관적인 네이밍 (task → title)
- **단점**: 전체 코드베이스 수정 필요, 버그 발생 가능
- **작업량**: 약 50+ 파일 수정

### Option C: 하이브리드
- 일부는 문서 수정, 일부는 코드 수정
- 예: `task → title` (코드 수정), layer 값은 유지 (문서 수정)

---

## 7. 우선순위 수정 항목

| 순위 | 항목 | 방향 | 이유 |
|------|------|------|------|
| 1 | **LangGraph State TypedDict** | 문서 수정 | 개념 오류 |
| 2 | **Reducer 설명 추가** | 문서 수정 | 핵심 개념 누락 |
| 3 | **TodoItem.metadata 중첩 구조** | 문서 수정 | 실제 구조 반영 |
| 4 | **layer 값** | 문서 수정 | 5개 레이어 명시 |
| 5 | **task vs title** | 선택 필요 | 네이밍 일관성 |
| 6 | **State 추가 필드들** | 문서 수정 | 완전성 |
| 7 | **Intent 추가 필드들** | 문서 수정 | 완전성 |

---

## 8. LangGraph 개념 보충 (문서 추가 필요)

### 8.1 State vs Pydantic Model

```
┌─────────────────────────────────────────────────────────────────┐
│                    두 가지 "State" 개념                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. LangGraph State (AgentState)                                │
│     ├── TypedDict 기반                                          │
│     ├── 그래프 전체에서 공유되는 "상태 컨테이너"                   │
│     ├── Reducer로 병합 (Annotated[..., reducer])                 │
│     └── checkpointer로 저장/복구                                 │
│                                                                  │
│  2. Pydantic Models (TodoItem, Plan, etc.)                      │
│     ├── BaseModel 기반                                          │
│     ├── 데이터 검증 & 직렬화                                     │
│     └── State 내부에 저장되는 "데이터 객체"                       │
│                                                                  │
│  관계:                                                           │
│  ┌──────────────────────────────────────────┐                   │
│  │  AgentState (TypedDict)                   │                   │
│  │  ┌────────────────────────────────────┐  │                   │
│  │  │  todos: List[TodoItem]  ← Pydantic │  │                   │
│  │  │  plan_obj: Plan         ← Pydantic │  │                   │
│  │  │  ml_result: dict                    │  │                   │
│  │  └────────────────────────────────────┘  │                   │
│  └──────────────────────────────────────────┘                   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 8.2 Reducer 동작 원리

```python
# 노드가 반환할 때:
return {"todos": [updated_todo]}  # 변경된 것만 반환

# LangGraph 내부에서:
state["todos"] = todo_reducer(
    state["todos"],      # 기존 목록
    [updated_todo]       # 새로운 항목
)
# → ID가 같으면 업데이트, 다르면 추가
```

---

## 9. 결정 필요 항목

| # | 항목 | 선택지 |
|---|------|--------|
| 1 | task vs title | A: 문서 수정 (task 유지) / B: 코드 수정 (title로 변경) |
| 2 | layer 값 | A: 5개 유지 / B: 3개로 단순화 |
| 3 | Metadata 구조 | A: 중첩 유지 (현재) / B: 평탄화 |

---

## 다음 단계

1. 위 결정 항목 선택
2. DATA_MODELS_260205.md 수정
3. LangGraph State 개념 문서 추가 (STATE_GUIDE_260205.md)
