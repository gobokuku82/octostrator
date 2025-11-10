# State 관리 가이드 (State Management Guide)

**작성일**: 2025-11-06
**목적**: State 관리 베스트 프랙티스 및 실전 가이드
**대상**: Backend 개발자, System Architect

---

## 📑 목차 (Table of Contents)

1. [개요 (Overview)](#개요-overview)
2. [Phase 3 원칙: State/Context 분리](#phase-3-원칙-statecontext-분리)
3. [State 설계 원칙](#state-설계-원칙)
4. [Custom Reducers 가이드](#custom-reducers-가이드)
5. [State 업데이트 패턴](#state-업데이트-패턴)
6. [Context API 사용법](#context-api-사용법)
7. [Checkpoint 관리](#checkpoint-관리)
8. [안티패턴 (Anti-Patterns)](#안티패턴-anti-patterns)
9. [트러블슈팅](#트러블슈팅)
10. [마이그레이션 가이드](#마이그레이션-가이드)

---

## 개요 (Overview)

### 문서 목적

이 문서는 AI PT Manager 시스템에서 State를 올바르게 관리하는 방법을 제공합니다. Phase 3에서 도입된 State/Context 분리 원칙을 준수하면서 효율적으로 State를 다루는 베스트 프랙티스를 다룹니다.

### State란?

**State**는 LangGraph 워크플로우의 실행 상태를 나타내는 데이터 구조입니다.

```python
# State의 특징
- 직렬화 가능 (msgpack)
- Checkpoint에 저장됨
- 변경 가능 (mutable)
- 노드 간 전달됨
```

### State vs Context vs Config

```
┌─────────────────────────────────────────────────────────────┐
│              State / Context / Config 비교                 │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  State               Context              Config           │
│  ━━━━━━━━━━━━━       ━━━━━━━━━━━━━       ━━━━━━━━━━━━━    │
│  • 가변 데이터        • 불변 런타임        • 환경 설정       │
│  • 직렬화 가능        • 요청별 생성        • .env 파일       │
│  • Checkpoint         • Runtime 주입       • 싱글톤         │
│  • 노드 간 전달       • 모든 노드 접근     • 전역 접근       │
│                                                             │
│  예시:                예시:                예시:            │
│  - user_query         - llm_settings       - openai_api_key │
│  - plan               - user_tier          - postgres_url   │
│  - todos              - trace_id           - system_debug   │
│  - final_response     - debug              - api_port       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Phase 3 원칙: State/Context 분리

### 원칙 1: State는 직렬화 가능한 데이터만

**✅ Good**:
```python
class OctostratorState(TypedDict, total=False):
    user_query: str                     # ✅ 기본 타입
    plan: dict                          # ✅ 직렬화 가능
    todos: List[Dict]                   # ✅ 컬렉션
    final_response: str                 # ✅ 기본 타입
```

**❌ Bad**:
```python
class OctostratorState(TypedDict, total=False):
    llm: ChatOpenAI                     # ❌ 객체 인스턴스
    checkpointer: AsyncPostgresSaver    # ❌ 객체 인스턴스
    db_conn: Connection                 # ❌ DB 연결
```

### 원칙 2: Context는 Runtime을 통해 접근

**✅ Good**:
```python
async def my_node(
    state: OctostratorState,
    runtime: Optional[Runtime] = None  # ✅ Runtime 파라미터
) -> OctostratorState:
    if runtime is not None:
        context: AppContext = runtime.context  # ✅ Context 접근
        llm_settings = context.llm_settings
        # ...
```

**❌ Bad**:
```python
async def my_node(state: OctostratorState) -> OctostratorState:
    context = state.get("context")  # ❌ State에서 context 접근
    llm_settings = context["llm_settings"]
```

### 원칙 3: Config는 환경 변수 또는 싱글톤

**✅ Good**:
```python
from backend.app.config.system import config

async def my_node(state: OctostratorState) -> OctostratorState:
    api_key = config.openai_api_key  # ✅ Config 싱글톤
```

**❌ Bad**:
```python
async def my_node(state: OctostratorState) -> OctostratorState:
    api_key = state.get("openai_api_key")  # ❌ State에서 Config 접근
```

---

## State 설계 원칙

### 1. 최소 필수 원칙 (Minimal Required Fields)

State에는 필요한 필드만 포함하세요.

**✅ Good**:
```python
class MyState(TypedDict, total=False):
    # 필수 필드만
    user_query: str
    result: str
```

**❌ Bad**:
```python
class MyState(TypedDict, total=False):
    # 불필요한 필드들
    user_query: str
    result: str
    temp_var_1: str  # 임시 변수 (불필요)
    debug_info: str  # 디버그 정보 (Context로 이동)
```

### 2. 명확한 네이밍 (Clear Naming)

필드 이름은 명확하고 일관성 있게 작성하세요.

**✅ Good**:
```python
user_query: str              # 명확한 의미
execution_results: dict      # 구체적
requires_approval: bool      # boolean은 is_/has_/requires_ 접두사
```

**❌ Bad**:
```python
q: str                       # 축약형
data: dict                   # 모호함
flag: bool                   # 의미 불명확
```

### 3. Optional vs Required

**total=False**를 사용하면 모든 필드가 Optional입니다.

```python
class MyState(TypedDict, total=False):
    # total=False: 모든 필드 Optional
    user_query: str              # Optional
    plan: dict                   # Optional
    error: Optional[str]         # 명시적 Optional (권장)
```

**Best Practice**:
- 항상 존재해야 하는 필드: 초기화 시 빈 값으로 설정
- 조건부 존재 필드: Optional 타입 힌트 추가

```python
# 초기화 예시
def create_initial_state(user_query: str) -> OctostratorState:
    return {
        "user_query": user_query,       # 필수
        "session_id": str(uuid.uuid4()),  # 필수
        "plan": {},                     # 항상 존재 (빈 dict)
        "todos": [],                    # 항상 존재 (빈 list)
        "error": None,                  # 조건부 (None 초기화)
        "final_response": "",           # 항상 존재 (빈 str)
    }
```

### 4. 불변 vs 가변 필드

State의 필드는 일반적으로 가변(mutable)이지만, 일부는 불변으로 취급해야 합니다.

**불변 취급 권장** (초기화 후 변경 안함):
```python
user_query: str          # 사용자 질의 (초기화 후 불변)
session_id: str          # 세션 ID (초기화 후 불변)
created_at: str          # 생성 시각 (초기화 후 불변)
```

**가변 (자주 업데이트)**:
```python
plan: dict               # Cognitive에서 업데이트
todos: List[Dict]        # Todo Manager에서 업데이트
execution_results: dict  # Execute Layer에서 업데이트
final_response: str      # Response Layer에서 설정
```

---

## Custom Reducers 가이드

### Reducer란?

Reducer는 State 업데이트 시 여러 값을 병합하는 방법을 정의합니다.

```python
from typing import Annotated

class MyState(TypedDict):
    # Reducer 없음: 마지막 값으로 덮어씀
    simple_field: str

    # Reducer 있음: 병합 로직 적용
    todos: Annotated[List[Dict], merge_todos_smart]
```

### Built-in Reducer: add_messages

LangChain의 기본 Reducer입니다.

```python
from langgraph.graph.message import add_messages

class ChatState(TypedDict):
    messages: Annotated[list, add_messages]
```

**동작**:
- 새 메시지를 기존 리스트에 추가
- ID 기반 업데이트 지원

### Custom Reducer 작성

**1. merge_todos_smart**

```python
def merge_todos_smart(existing: List[Dict], new: List[Dict]) -> List[Dict]:
    """
    Smart Todo 병합
    - ID 기반 업데이트
    - 새 Todo 추가
    - 중복 제거
    """
    if not existing:
        return new

    # ID -> Todo 매핑
    merged = {todo["id"]: todo for todo in existing}

    # 새 Todo 병합
    for todo in new:
        todo_id = todo.get("id")
        if todo_id:
            if todo_id in merged:
                # 기존 Todo 업데이트
                merged[todo_id].update(todo)
            else:
                # 새 Todo 추가
                merged[todo_id] = todo

    return list(merged.values())
```

**사용 예시**:
```python
from typing import Annotated

class OctostratorState(TypedDict, total=False):
    todos: Annotated[List[Dict], merge_todos_smart]

# 노드에서 업데이트
async def my_node(state: OctostratorState) -> OctostratorState:
    return {
        "todos": [
            {"id": "todo_1", "status": "completed"}  # 기존 Todo 업데이트
        ]
    }
```

**2. add_with_timestamp_and_step**

```python
def add_with_timestamp_and_step(existing: List[Dict], new: List[Dict]) -> List[Dict]:
    """
    타임스탬프 및 스텝 번호 자동 추가
    """
    if not existing:
        existing = []

    result = existing.copy()
    next_step = len(existing)

    for item in new:
        enriched_item = {
            **item,
            "timestamp": datetime.utcnow().isoformat(),
            "step_number": next_step
        }
        result.append(enriched_item)
        next_step += 1

    return result
```

**사용 예시**:
```python
class OctostratorState(TypedDict, total=False):
    action_history: Annotated[List[Dict], add_with_timestamp_and_step]

# 노드에서 추가
async def my_node(state: OctostratorState) -> OctostratorState:
    return {
        "action_history": [
            {"action": "plan_created", "details": "..."}
        ]
    }
    # → timestamp, step_number 자동 추가됨
```

### Reducer 작성 가이드라인

1. **순수 함수**: 부작용(side-effects) 없이 작성
2. **타입 안정성**: 입력과 출력 타입 명확히
3. **Null 처리**: existing이 None이거나 빈 리스트 처리
4. **성능 고려**: 대용량 데이터 처리 시 효율적 알고리즘 사용
5. **테스트 작성**: 다양한 병합 시나리오 테스트

---

## State 업데이트 패턴

### 패턴 1: 부분 업데이트 (Partial Update)

가장 일반적인 패턴. 변경된 필드만 반환합니다.

```python
async def my_node(state: OctostratorState) -> OctostratorState:
    # 일부 필드만 업데이트
    return {
        "plan": {"goal": "...", "steps": [...]},
        "plan_valid": True
    }
    # 다른 필드들은 그대로 유지됨
```

### 패턴 2: 조건부 업데이트 (Conditional Update)

조건에 따라 다른 필드를 업데이트합니다.

```python
async def my_node(state: OctostratorState) -> OctostratorState:
    if state.get("plan_valid"):
        return {"todos": [...]}  # 계획 유효 시 Todo 생성
    else:
        return {"error": "Invalid plan"}  # 계획 무효 시 에러
```

### 패턴 3: 누적 업데이트 (Accumulative Update)

기존 값에 추가합니다.

```python
async def my_node(state: OctostratorState) -> OctostratorState:
    # Reducer 없이 수동 누적
    existing_history = state.get("action_history", [])
    new_action = {"action": "step_completed", "timestamp": "..."}

    return {
        "action_history": existing_history + [new_action]
    }

    # 또는 Reducer 사용 (권장)
    return {
        "action_history": [new_action]
    }  # Reducer가 자동으로 누적
```

### 패턴 4: 전체 교체 (Full Replacement)

```python
async def my_node(state: OctostratorState) -> OctostratorState:
    # 전체 교체 (주의: 기존 값 손실)
    return {
        "execution_results": {
            "agent_1": {...},
            "agent_2": {...}
        }
    }
```

### 패턴 5: Nested 업데이트 (중첩 구조)

```python
async def my_node(state: OctostratorState) -> OctostratorState:
    # 중첩 dict 업데이트
    existing_plan = state.get("plan", {})

    return {
        "plan": {
            **existing_plan,
            "steps": [...]  # steps만 업데이트
        }
    }
```

### 패턴 6: Flag 설정 (Boolean Flags)

```python
async def cognitive_node(state: OctostratorState) -> OctostratorState:
    plan = create_plan(state["user_query"])

    return {
        "plan": plan,
        "plan_valid": True,
        "plan_requires_todos": True,  # Conditional edge를 위한 flag
    }
```

---

## Context API 사용법

### 기본 사용법

**1. Graph 정의 시 context_schema 추가**

```python
from langgraph.graph import StateGraph
from backend.app.octostrator.contexts.app_context import AppContext

# Context API 활성화
graph = StateGraph(
    OctostratorState,
    context_schema=AppContext  # ✅ 이 한 줄 추가!
)
```

**2. 노드에서 runtime 파라미터 추가**

```python
from langgraph.types import Runtime
from typing import Optional

async def my_node(
    state: OctostratorState,
    runtime: Optional[Runtime] = None  # ✅ Runtime 파라미터
) -> OctostratorState:
    # Context 접근
    if runtime is not None:
        context: AppContext = runtime.context
        # ...
```

**3. Context로부터 LLM 생성**

```python
from langchain_openai import ChatOpenAI

async def my_node(
    state: OctostratorState,
    runtime: Optional[Runtime] = None
) -> OctostratorState:
    llm = None

    if runtime is not None:
        context: AppContext = runtime.context
        settings = context.llm_settings

        llm = ChatOpenAI(
            model=settings.agent_model,
            temperature=settings.agent_temperature,
            max_tokens=settings.agent_max_tokens,
            api_key=config.openai_api_key
        )
    else:
        # Fallback: Context 없을 때
        llm = ChatOpenAI(model="gpt-4o-mini")

    # LLM 사용
    response = await llm.ainvoke("...")
    return {"result": response.content}
```

### 고급 사용법

**1. UserTier별 동작 변경**

```python
async def my_node(
    state: OctostratorState,
    runtime: Optional[Runtime] = None
) -> OctostratorState:
    if runtime is not None:
        context: AppContext = runtime.context

        if context.user_tier == UserTier.PREMIUM:
            # Premium 사용자: 상세한 분석
            result = perform_detailed_analysis(...)
        elif context.user_tier == UserTier.TRIAL:
            # Trial 사용자: 기본 분석
            result = perform_basic_analysis(...)
        else:
            # Standard 사용자: 균형잡힌 분석
            result = perform_standard_analysis(...)

        return {"result": result}
```

**2. Debug 모드 활용**

```python
async def my_node(
    state: OctostratorState,
    runtime: Optional[Runtime] = None
) -> OctostratorState:
    if runtime is not None:
        context: AppContext = runtime.context

        if context.debug:
            logger.debug(f"[DEBUG] Trace ID: {context.trace_id}")
            logger.debug(f"[DEBUG] State: {state}")

    # 노드 로직
    result = process_data(...)
    return {"result": result}
```

**3. Metrics 수집**

```python
async def my_node(
    state: OctostratorState,
    runtime: Optional[Runtime] = None
) -> OctostratorState:
    start_time = time.time()

    # 노드 로직 실행
    result = process_data(...)

    # Metrics 업데이트
    if runtime is not None:
        context: AppContext = runtime.context
        context.metrics["my_node_duration"] = time.time() - start_time
        context.metrics["my_node_calls"] = context.metrics.get("my_node_calls", 0) + 1

    return {"result": result}
```

---

## Checkpoint 관리

### Checkpoint란?

Checkpoint는 State를 데이터베이스에 저장하여 중단된 워크플로우를 재개할 수 있게 합니다.

```python
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

# Checkpointer 생성
checkpointer = AsyncPostgresSaver(conn_string=config.postgres_url)

# Graph compile 시 전달
graph = graph.compile(checkpointer=checkpointer)
```

### Thread ID (세션 관리)

```python
# Graph 실행 시 thread_id 지정
result = await graph.ainvoke(
    state,
    config={
        "configurable": {
            "thread_id": "session_001"  # 세션 ID
        }
    }
)

# 같은 thread_id로 재실행 → 이전 State 복원
result2 = await graph.ainvoke(
    {"user_query": "다음 질문"},
    config={
        "configurable": {
            "thread_id": "session_001"  # 동일 세션
        }
    }
)
```

### Checkpoint 주의사항

1. **직렬화 필수**: State의 모든 필드는 msgpack 직렬화 가능해야 함
2. **크기 제한**: 너무 큰 State는 성능 저하 (수 MB 이하 권장)
3. **정리 정책**: 오래된 Checkpoint 정기적으로 삭제 필요
4. **보안**: 민감 정보는 State에 포함하지 말 것

---

## 안티패턴 (Anti-Patterns)

### 🚫 Anti-Pattern 1: State에 객체 인스턴스 저장

**❌ Bad**:
```python
class MyState(TypedDict):
    llm: ChatOpenAI  # ❌ 객체 인스턴스
    db: Connection   # ❌ DB 연결

async def my_node(state: MyState) -> MyState:
    llm = ChatOpenAI(...)
    return {"llm": llm}  # ❌ msgpack 직렬화 실패
```

**✅ Good**:
```python
# LLM은 Context에서 가져옴
async def my_node(
    state: MyState,
    runtime: Optional[Runtime] = None
) -> MyState:
    llm = create_llm_from_context(runtime)
    response = await llm.ainvoke("...")
    return {"response": response.content}  # ✅ 문자열만 저장
```

---

### 🚫 Anti-Pattern 2: State를 로그로 사용

**❌ Bad**:
```python
class MyState(TypedDict):
    logs: List[str]  # ❌ 로그를 State에 저장

async def my_node(state: MyState) -> MyState:
    logs = state.get("logs", [])
    logs.append("Step 1 completed")
    logs.append("Step 2 started")
    return {"logs": logs}  # ❌ State 크기 증가
```

**✅ Good**:
```python
import logging

logger = logging.getLogger(__name__)

async def my_node(state: MyState) -> MyState:
    logger.info("Step 1 completed")  # ✅ 로깅 시스템 사용
    logger.info("Step 2 started")
    return {"result": "..."}
```

---

### 🚫 Anti-Pattern 3: State에서 Config 접근

**❌ Bad**:
```python
async def my_node(state: MyState) -> MyState:
    api_key = state.get("openai_api_key")  # ❌ Config를 State에
```

**✅ Good**:
```python
from backend.app.config.system import config

async def my_node(state: MyState) -> MyState:
    api_key = config.openai_api_key  # ✅ Config 싱글톤
```

---

### 🚫 Anti-Pattern 4: 임시 변수를 State에 저장

**❌ Bad**:
```python
async def my_node(state: MyState) -> MyState:
    temp_data = compute_something()

    return {
        "result": process(temp_data),
        "temp_data": temp_data  # ❌ 임시 변수를 State에
    }
```

**✅ Good**:
```python
async def my_node(state: MyState) -> MyState:
    temp_data = compute_something()  # 지역 변수로만 사용

    return {
        "result": process(temp_data)  # ✅ 최종 결과만 반환
    }
```

---

### 🚫 Anti-Pattern 5: State를 과도하게 분리

**❌ Bad**:
```python
# 너무 많은 State 타입
class State1(TypedDict):
    field1: str

class State2(TypedDict):
    field2: str

# ... State10까지
```

**✅ Good**:
```python
# 적절한 그루핑
class MyState(TypedDict):
    # 관련 필드들을 함께
    user_input: str
    processing_result: dict
    final_output: str
```

---

## 트러블슈팅

### 문제 1: msgpack 직렬화 오류

**증상**:
```
TypeError: Type is not msgpack serializable: <class 'ChatOpenAI'>
```

**원인**: State에 직렬화 불가능한 객체가 포함됨

**해결**:
1. State 정의 확인
2. 객체 인스턴스 제거
3. Context API 사용

```python
# ❌ Before
class MyState(TypedDict):
    llm: ChatOpenAI

# ✅ After
class MyState(TypedDict):
    # llm 필드 제거, Runtime에서 접근
    pass
```

---

### 문제 2: State 필드가 사라짐

**증상**: 노드에서 설정한 필드가 다음 노드에서 None

**원인 1**: TypedDict의 total=False

```python
# total=False → 모든 필드 Optional
class MyState(TypedDict, total=False):
    my_field: str  # Optional

# 해결: 초기화 시 빈 값으로 설정
def create_state():
    return {"my_field": ""}  # 빈 문자열로 초기화
```

**원인 2**: Reducer가 필드를 덮어씀

```python
# Reducer 확인
class MyState(TypedDict):
    todos: Annotated[List[Dict], my_reducer]

# my_reducer가 올바르게 병합하는지 확인
```

---

### 문제 3: Context가 None

**증상**: runtime.context가 None

**원인**: context_schema를 설정하지 않음

**해결**:
```python
# Graph 정의 시
graph = StateGraph(
    MyState,
    context_schema=AppContext  # ✅ 추가
)
```

---

### 문제 4: Checkpoint 복원 실패

**증상**: 같은 thread_id로 재실행해도 State가 초기화됨

**원인**: checkpointer가 제대로 설정되지 않음

**해결**:
```python
# 1. Checkpointer 생성 확인
checkpointer = AsyncPostgresSaver(...)

# 2. Graph compile 시 전달 확인
graph = graph.compile(checkpointer=checkpointer)

# 3. DB 연결 확인
# PostgreSQL이 실행 중이고 연결 가능한지 확인
```

---

## 마이그레이션 가이드

### Phase 2 → Phase 3 마이그레이션

#### 변경 사항

1. **State에서 제거된 필드**:
   - `llm: Any`
   - `checkpointer: Any`
   - `context: Dict[str, Any]`

2. **노드 시그니처 변경**:
   ```python
   # ❌ Before
   async def my_node(state: MyState) -> MyState:
       pass

   # ✅ After
   async def my_node(
       state: MyState,
       runtime: Optional[Runtime] = None
   ) -> MyState:
       pass
   ```

#### 마이그레이션 스텝

**Step 1**: State 정의 업데이트

```python
# backend/app/octostrator/states/my_state.py

# ❌ Before
class MyState(TypedDict, total=False):
    llm: Any
    context: Dict[str, Any]
    user_query: str

# ✅ After
class MyState(TypedDict, total=False):
    # llm, context 제거
    user_query: str
```

**Step 2**: 노드 함수 업데이트

```python
# ❌ Before
async def my_node(state: MyState) -> MyState:
    llm = state.get("llm")
    context = state.get("context", {})
    user_id = context.get("user_id")

    response = await llm.ainvoke("...")
    return {"result": response.content}

# ✅ After
async def my_node(
    state: MyState,
    runtime: Optional[Runtime] = None
) -> MyState:
    # LLM 생성
    llm = _create_llm_from_context(runtime)

    # Context 접근
    user_id = "default"
    if runtime is not None:
        context: AppContext = runtime.context
        user_id = context.user_id

    response = await llm.ainvoke("...")
    return {"result": response.content}
```

**Step 3**: Helper 함수 작성

```python
def _create_llm_from_context(runtime: Optional[Runtime]) -> ChatOpenAI:
    """Context API를 사용하여 LLM 생성"""
    if runtime is not None:
        context: AppContext = runtime.context
        settings = context.llm_settings

        return ChatOpenAI(
            model=settings.agent_model,
            temperature=settings.agent_temperature,
            max_tokens=settings.agent_max_tokens,
            api_key=config.openai_api_key
        )

    # Fallback
    return ChatOpenAI(model="gpt-4o-mini")
```

**Step 4**: Graph 정의 업데이트

```python
# ❌ Before
graph = StateGraph(MyState)

# ✅ After
graph = StateGraph(
    MyState,
    context_schema=AppContext  # Context API 활성화
)
```

**Step 5**: 테스트

```python
# Python 문법 검증
python -m py_compile my_nodes.py

# 단위 테스트
pytest tests/test_my_nodes.py

# 통합 테스트
pytest tests/integration/
```

---

## 부록: 체크리스트

### State 설계 체크리스트

- [ ] 모든 필드가 직렬화 가능한가?
- [ ] 필드 이름이 명확한가?
- [ ] Optional 필드에 타입 힌트가 있는가?
- [ ] Reducer가 필요한 필드를 식별했는가?
- [ ] 불필요한 임시 변수가 없는가?

### Context API 체크리스트

- [ ] Graph에 context_schema를 설정했는가?
- [ ] 노드에 runtime 파라미터를 추가했는가?
- [ ] runtime is not None 체크를 하는가?
- [ ] Fallback 로직이 있는가? (runtime이 None일 때)

### Checkpoint 체크리스트

- [ ] Checkpointer가 제대로 생성되었는가?
- [ ] Graph compile 시 checkpointer를 전달했는가?
- [ ] thread_id를 일관성 있게 사용하는가?
- [ ] PostgreSQL이 실행 중인가?

---

**작성자**: Claude Code Agent
**검토자**: -
**버전**: 1.0
**마지막 업데이트**: 2025-11-06
**관련 문서**: [SCHEMA_SPECIFICATIONS.md](SCHEMA_SPECIFICATIONS.md), [MASTER_CHECKLIST.md](MASTER_CHECKLIST.md)
