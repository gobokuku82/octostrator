# LangGraph Context 관리 분석 보고서

**작성일**: 2025-11-03
**버전**: LangGraph 0.6+ / 1.0
**목적**: LangGraph의 Context 관리 방식 이해 및 아키텍처 설계

---

## 1. 개요

LangGraph 0.6부터 **Context API**가 도입되어 기존 `config["configurable"]` 방식을 대체했습니다. 이는 그래프 실행 시 불변 컨텍스트를 전달하는 더 직관적이고 타입 안전한 방법을 제공합니다.

---

## 2. State vs Context 개념 정리

### State (상태)
- **정의**: 노드 간 전달되는 **변경 가능한** 데이터
- **용도**: 대화 메시지, 중간 결과, 실행 흐름 등
- **특징**:
  - 노드가 반환하면 자동으로 병합됨
  - Checkpoint로 저장됨
  - 그래프 실행 중 변경됨

```python
class State(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    next: str  # 다음 노드
```

### Context (컨텍스트)
- **정의**: 그래프 실행 시 제공되는 **불변** 런타임 정보
- **용도**: user_id, db_conn, API key, 설정값 등
- **특징**:
  - 그래프 실행 중 변경 불가
  - Checkpoint에 저장 안 됨
  - 모든 노드에서 접근 가능

```python
@dataclass
class Context:
    user_id: str
    db_conn: Any
    llm_provider: str = "openai"
```

### 비교표

| 구분 | State | Context |
|------|-------|---------|
| 변경 가능성 | ✅ 변경 가능 | ❌ 불변 |
| Checkpoint 저장 | ✅ 저장됨 | ❌ 저장 안 됨 |
| 노드 간 전달 | ✅ 자동 전달 | ✅ Runtime으로 접근 |
| 용도 | 대화 내용, 중간 결과 | 사용자 정보, 설정, DB 연결 |
| 예시 | messages, next, result | user_id, session_id, api_key |

---

## 3. API 변경 내역 (0.6 이전 → 0.6+)

### 3.1 Graph 초기화

#### 이전 방식 (0.5 이하)
```python
from langgraph.graph import StateGraph

builder = StateGraph(state_schema, config_schema)
```

#### 신규 방식 (0.6+, 권장)
```python
from langgraph.graph import StateGraph

builder = StateGraph(state_schema, context_schema=ContextSchema)
```

### 3.2 Graph 실행

#### 이전 방식
```python
result = agent.invoke(
    {"messages": [HumanMessage(content="Hello")]},
    config={"configurable": {"user_id": "user_123", "db_conn": db}}
)
```

**문제점**:
- `config["configurable"]` 깊은 중첩
- 타입 안전성 없음
- IDE 자동완성 불가

#### 신규 방식
```python
result = agent.invoke(
    {"messages": [HumanMessage(content="Hello")]},
    config={"thread_id": "thread_123"},  # Checkpoint 설정
    context={"user_id": "user_123", "db_conn": db}  # 런타임 컨텍스트
)
```

**개선점**:
- Context와 Config 명확히 분리
- 타입 안전성 (dataclass)
- 더 직관적인 API

### 3.3 노드 함수 시그니처

#### 이전 방식
```python
from langchain_core.runnables import RunnableConfig

def my_node(state: State, config: RunnableConfig):
    # 깊은 중첩 접근
    user_id = config["configurable"]["user_id"]
    db_conn = config["configurable"]["db_conn"]

    # 타입 체크 없음
    # IDE 자동완성 없음
    return {"messages": [...]}
```

#### 신규 방식
```python
from langgraph.runtime import Runtime
from dataclasses import dataclass

@dataclass
class Context:
    user_id: str
    db_conn: Any

def my_node(state: State, runtime: Runtime[Context]):
    # 타입 안전한 접근
    user_id = runtime.context.user_id
    db_conn = runtime.context.db_conn
    thread_id = runtime.config.thread_id

    # IDE 자동완성 ✅
    # 타입 체크 ✅
    return {"messages": [...]}
```

---

## 4. 실전 사용 예시

### 4.1 Context Schema 정의

```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class AppContext:
    """애플리케이션 런타임 컨텍스트"""

    # 필수 필드
    user_id: str
    session_id: str

    # 선택 필드 (기본값)
    llm_provider: str = "openai"
    llm_model: str = "gpt-4o-mini"
    temperature: float = 0.7

    # DB 연결 (런타임에 주입)
    db_conn: Optional[Any] = None
```

### 4.2 Graph 생성

```python
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated, Sequence
from langchain_core.messages import BaseMessage, add_messages

class State(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]

# Context Schema와 함께 Graph 생성
workflow = StateGraph(State, context_schema=AppContext)
```

### 4.3 노드에서 Context 사용

```python
from langgraph.runtime import Runtime
from langchain_openai import ChatOpenAI

def supervisor_node(state: State, runtime: Runtime[AppContext]) -> dict:
    """Supervisor 노드 - Context 활용"""

    # Context에서 설정 가져오기
    ctx = runtime.context

    # LLM 초기화 (Context의 설정 사용)
    llm = ChatOpenAI(
        model=ctx.llm_model,
        temperature=ctx.temperature
    )

    # DB에서 사용자 정보 조회
    if ctx.db_conn:
        user_info = ctx.db_conn.get_user(ctx.user_id)

    # 메시지 처리
    messages = state["messages"]
    response = await llm.ainvoke(messages)

    return {"messages": [response]}

workflow.add_node("supervisor", supervisor_node)
```

### 4.4 Graph 실행

```python
from langchain_core.messages import HumanMessage

# DB 연결 준비
db_conn = connect_to_database()

# Graph 실행 (Context 전달)
result = await graph.ainvoke(
    # State 입력
    {"messages": [HumanMessage(content="안녕하세요")]},

    # Config (Checkpoint 설정)
    config={
        "thread_id": "thread_abc123",  # 대화 스레드 ID
    },

    # Context (런타임 불변 정보)
    context={
        "user_id": "user_456",
        "session_id": "session_789",
        "llm_model": "gpt-4o",
        "temperature": 0.5,
        "db_conn": db_conn
    }
)
```

---

## 5. Context 관리 전략

### 5.1 Context의 적절한 용도

#### ✅ Context에 포함해야 할 것
- 사용자 식별 정보 (user_id, session_id)
- DB 연결, API 클라이언트 등 외부 의존성
- LLM 설정 (model, temperature 등)
- 권한/인증 정보
- 환경 설정 (dev/prod)

#### ❌ State에 포함해야 할 것
- 대화 메시지 (messages)
- 중간 처리 결과
- 다음 실행할 노드 정보 (next)
- 에이전트 간 전달할 데이터

### 5.2 Context vs Environment Variable

| 구분 | Context | Environment Variable |
|------|---------|----------------------|
| 변경 시점 | 런타임 (요청마다) | 앱 시작 시 |
| 스코프 | 각 그래프 실행 | 전체 애플리케이션 |
| 예시 | user_id, session_id | OPENAI_API_KEY, DB_URL |

**권장 패턴**:
```python
# config/system.py - 환경 변수
class SystemConfig(BaseSettings):
    openai_api_key: str
    postgres_url: str

# Context - 런타임 정보
@dataclass
class AppContext:
    user_id: str
    session_id: str
```

---

## 6. 마이그레이션 가이드

### 6.1 하위 호환성

LangGraph는 **완전한 하위 호환성**을 제공합니다:
- 기존 `config["configurable"]` 방식 계속 작동
- 점진적 마이그레이션 가능

### 6.2 단계별 마이그레이션

#### Step 1: Context Schema 정의
```python
@dataclass
class Context:
    user_id: str
    # 기존 config["configurable"]에서 사용하던 필드들
```

#### Step 2: StateGraph에 context_schema 추가
```python
# 기존
workflow = StateGraph(State)

# 신규
workflow = StateGraph(State, context_schema=Context)
```

#### Step 3: 노드 함수 시그니처 변경
```python
# 기존
def node(state: State, config: RunnableConfig):
    user_id = config["configurable"]["user_id"]

# 신규
def node(state: State, runtime: Runtime[Context]):
    user_id = runtime.context.user_id
```

#### Step 4: 호출 방식 변경
```python
# 기존
graph.invoke(state, config={"configurable": {"user_id": "123"}})

# 신규
graph.invoke(state, context={"user_id": "123"})
```

---

## 7. 우리 프로젝트 적용 방안

### 7.1 현재 상황
- LangGraph 1.0.2 사용 중
- Supervisor 기본 구조 완성 (Phase 1)
- Context 미사용 (State만 사용)

### 7.2 권장 구조

```
backend/app/
├── config/
│   └── system.py              # 환경 변수 (SystemConfig)
│
└── octochestrator/            # 제안 폴더명
    ├── contexts/              # Context Schema 정의
    │   ├── __init__.py
    │   ├── app_context.py     # AppContext (공통)
    │   └── agent_context.py   # AgentContext (에이전트별)
    │
    ├── states/                # State 정의
    │   ├── __init__.py
    │   ├── supervisor_state.py
    │   └── agent_state.py
    │
    ├── supervisor/            # Supervisor
    └── agents/                # Worker Agents
```

### 7.3 구현 예시

#### contexts/app_context.py
```python
from dataclasses import dataclass
from typing import Optional
import asyncpg

@dataclass
class AppContext:
    """애플리케이션 런타임 컨텍스트"""

    # 세션 정보
    user_id: str
    session_id: str
    thread_id: str

    # LLM 설정
    llm_model: str = "gpt-4o-mini"
    temperature: float = 0.7

    # DB 연결 (런타임 주입)
    db_pool: Optional[asyncpg.Pool] = None
```

#### supervisor/graph.py
```python
from langgraph.graph import StateGraph
from langgraph.runtime import Runtime
from backend.app.octochestrator.contexts.app_context import AppContext
from backend.app.octochestrator.states.supervisor_state import SupervisorState

def build_supervisor_graph():
    # Context Schema 포함
    workflow = StateGraph(
        SupervisorState,
        context_schema=AppContext
    )

    async def supervisor_node(
        state: SupervisorState,
        runtime: Runtime[AppContext]
    ) -> dict:
        # Context 사용
        ctx = runtime.context

        llm = ChatOpenAI(
            model=ctx.llm_model,
            temperature=ctx.temperature
        )

        # DB 조회 (필요시)
        if ctx.db_pool:
            user_prefs = await ctx.db_pool.fetchrow(
                "SELECT * FROM user_preferences WHERE user_id = $1",
                ctx.user_id
            )

        messages = state["messages"]
        response = await llm.ainvoke(messages)
        return {"messages": [response]}

    workflow.add_node("supervisor", supervisor_node)
    workflow.set_entry_point("supervisor")
    workflow.add_edge("supervisor", END)

    return workflow.compile()
```

#### main.py
```python
from fastapi import FastAPI, Request
from backend.app.octochestrator.contexts.app_context import AppContext

@app.post("/chat")
async def chat(request: ChatRequest, req: Request):
    # DB pool 가져오기
    db_pool = req.app.state.db_pool

    # Context 생성
    context = AppContext(
        user_id=req.headers.get("X-User-ID", "anonymous"),
        session_id=req.headers.get("X-Session-ID", "default"),
        thread_id=f"thread_{request.message[:10]}",
        llm_model="gpt-4o-mini",
        temperature=0.7,
        db_pool=db_pool
    )

    # Graph 실행
    result = await supervisor_graph.ainvoke(
        {"messages": [HumanMessage(content=request.message)]},
        config={"thread_id": context.thread_id},
        context=context  # Context 전달
    )

    return {"response": result["messages"][-1].content}
```

---

## 8. 결론 및 권장사항

### 8.1 Context 사용의 이점
1. **타입 안전성**: dataclass로 IDE 자동완성 및 타입 체크
2. **명확한 분리**: State(변경)와 Context(불변) 역할 구분
3. **코드 가독성**: 깔끔한 접근 패턴
4. **유지보수성**: 중앙집중식 Context Schema 관리

### 8.2 우리 프로젝트 적용 단계

**Phase 1.5 (현재 단계)**:
1. `contexts/` 폴더 생성
2. `AppContext` 정의
3. Supervisor Graph에 context_schema 추가
4. 기본 테스트

**Phase 2 이후**:
1. Agent별 Context 확장 (필요시)
2. DB 연결 Context에 주입
3. 사용자별 설정 Context로 관리

### 8.3 최종 권장사항

✅ **Context를 적극 활용하세요**
- user_id, session_id → Context
- LLM 설정 → Context
- DB 연결 → Context

✅ **폴더 구조**
```
octochestrator/
├── contexts/      # Context Schema (불변 런타임 정보)
├── states/        # State Schema (변경 가능한 상태)
├── supervisor/
└── agents/
```

✅ **점진적 도입**
- Phase 1.5: 기본 AppContext 도입
- Phase 2+: Agent별 확장

---

## 9. 참고 자료

- [LangGraph Context API Issue](https://github.com/langchain-ai/langgraph/issues/5023)
- [LangGraph Runtime Documentation](https://reference.langchain.com/python/langgraph/runtime/)
- [Context Engineering Blog](https://blog.langchain.com/context-engineering-for-agents/)
- [LangGraph State Management Guide](https://docs.langchain.com/oss/python/langgraph/graph-api)
