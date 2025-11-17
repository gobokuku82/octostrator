# 01. 시스템 아키텍처 설계

**문서 버전**: 1.0.0  
**작성일**: 2025-11-17  
**관련 문서**: [00_PROJECT_OVERVIEW.md](./00_PROJECT_OVERVIEW.md)

---

## 📋 목차

1. [전체 시스템 아키텍처](#1-전체-시스템-아키텍처)
2. [LangGraph Main Graph 구조](#2-langgraph-main-graph-구조)
3. [컴포넌트 다이어그램](#3-컴포넌트-다이어그램)
4. [데이터 플로우](#4-데이터-플로우)
5. [통신 프로토콜](#5-통신-프로토콜)
6. [확장성 고려사항](#6-확장성-고려사항)

---

## 1. 전체 시스템 아키텍처

### 1.1 3-Tier 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                    Presentation Layer                       │
│                   (Frontend - Next.js)                      │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │     TODO     │  │   Interrupt  │  │   Streaming  │    │
│  │  Dashboard   │  │    Modal     │  │    Client    │    │
│  └──────────────┘  └──────────────┘  └──────────────┘    │
└────────────────────────┬────────────────────────────────────┘
                         ↓ HTTP / SSE
┌─────────────────────────────────────────────────────────────┐
│                    Application Layer                        │
│                     (Backend - FastAPI)                     │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │   Streaming  │  │   Interrupt  │  │    Resume    │    │
│  │   Endpoint   │  │   Handler    │  │    Handler   │    │
│  └──────────────┘  └──────────────┘  └──────────────┘    │
└────────────────────────┬────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                      Agent Layer                            │
│                    (LangGraph 1.0)                          │
│                                                             │
│  ┌────────────────────────────────────────────────────┐   │
│  │              Main Graph (StateGraph)               │   │
│  │                                                     │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐        │   │
│  │  │ Intent   │  │ Planning │  │Supervisor│        │   │
│  │  │ Analysis │→ │  Agent   │→ │  Agent   │        │   │
│  │  └──────────┘  └──────────┘  └────┬─────┘        │   │
│  │                                    ↓               │   │
│  │                           ┌────────────────┐      │   │
│  │                           │Worker Subgraph │      │   │
│  │                           │  (StateGraph)  │      │   │
│  │                           └────────────────┘      │   │
│  └────────────────────────────────────────────────────┘   │
└────────────────────────┬────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                   Persistence Layer                         │
│                                                             │
│  ┌────────────────────────┐  ┌────────────────────────┐   │
│  │   AsyncPostgresSaver   │  │    RedisStore          │   │
│  │   (Checkpointer)       │  │  (Optional - Store)    │   │
│  └────────────────────────┘  └────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 계층별 책임

| 계층 | 책임 | 기술 스택 |
|------|------|----------|
| **Presentation** | UI/UX, 사용자 입력 처리, 실시간 표시 | Next.js, React, Tailwind |
| **Application** | API 라우팅, 스트리밍, 세션 관리 | FastAPI, Uvicorn |
| **Agent** | 의도 분석, TODO 관리, 작업 실행 | LangGraph, LangChain |
| **Persistence** | 상태 저장, 체크포인팅, 히스토리 | PostgreSQL, Redis |

---

## 2. LangGraph Main Graph 구조

### 2.1 Main Graph 노드 구성

```python
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

# Main Graph 정의
graph = StateGraph(MainState)

# 노드 추가
graph.add_node("intent_analysis", intent_analysis_agent)
graph.add_node("planning_agent", planning_agent)
graph.add_node("supervisor_agent", supervisor_agent)
graph.add_node("handle_user_interrupt", handle_user_interrupt)
graph.add_node("simple_qa_agent", simple_qa_agent)
graph.add_node("worker_subgraph", worker_subgraph_compiled)

# 엣지 정의
graph.add_edge(START, "intent_analysis")
graph.add_conditional_edges(
    "intent_analysis",
    route_by_intent,
    {
        "new_task": "planning_agent",
        "modify_task": "planning_agent",
        "continue_task": "supervisor_agent",
        "simple_qa": "simple_qa_agent"
    }
)
graph.add_edge("planning_agent", "supervisor_agent")
graph.add_conditional_edges(
    "supervisor_agent",
    check_user_interrupted,
    {
        "interrupted": "handle_user_interrupt",
        "continue": "worker_subgraph"
    }
)
graph.add_edge("worker_subgraph", "supervisor_agent")
graph.add_edge("simple_qa_agent", END)

# Checkpointer 연결
checkpointer = AsyncPostgresSaver.from_conn_string(
    "postgresql://user:pass@localhost/db"
)
compiled_graph = graph.compile(checkpointer=checkpointer)
```

### 2.2 노드별 역할

| 노드 | 역할 | 입력 | 출력 | interrupt 발생 |
|------|------|------|------|---------------|
| **intent_analysis** | 의도 분류 | messages | current_intent | ❌ |
| **planning_agent** | TODO 생성/수정 | current_intent, messages | todos | ✅ (승인) |
| **supervisor_agent** | TODO 실행 관리 | todos | active_todo_id | ❌ |
| **handle_user_interrupt** | ESC 중단 처리 | user_interrupted | - | ✅ (수정/계속) |
| **simple_qa_agent** | 단순 질문 답변 | messages | messages | ❌ |
| **worker_subgraph** | 작업 실행 | active_todo_id | completed_todo | ✅ (도구 승인) |

### 2.3 Worker Subgraph 구조

```python
# Worker Subgraph 정의
worker_graph = StateGraph(WorkerState)

# 노드 추가
worker_graph.add_node("router", worker_router)
worker_graph.add_node("research_worker", research_worker)
worker_graph.add_node("analysis_worker", analysis_worker)
worker_graph.add_node("coding_worker", coding_worker)
worker_graph.add_node("writing_worker", writing_worker)
worker_graph.add_node("finalize", finalize_worker)

# 엣지 정의
worker_graph.add_edge(START, "router")
worker_graph.add_conditional_edges(
    "router",
    lambda s: s["current_todo"]["assigned_worker"],
    {
        "research": "research_worker",
        "analysis": "analysis_worker",
        "coding": "coding_worker",
        "writing": "writing_worker"
    }
)
worker_graph.add_edge("research_worker", "finalize")
worker_graph.add_edge("analysis_worker", "finalize")
worker_graph.add_edge("coding_worker", "finalize")
worker_graph.add_edge("writing_worker", "finalize")

# finalize에서는 Command.PARENT로 Main Graph로 복귀
worker_graph.add_edge("finalize", END)

worker_subgraph_compiled = worker_graph.compile()
```

---

## 3. 컴포넌트 다이어그램

### 3.1 Frontend 컴포넌트 구조

```
┌──────────────────────────────────────────┐
│         App (page.tsx)                   │
│                                          │
│  ┌────────────────────────────────────┐ │
│  │   ChatInterface                    │ │
│  │                                    │ │
│  │  ┌──────────────────────────────┐ │ │
│  │  │   MessageList                │ │ │
│  │  │  - 대화 히스토리 표시         │ │ │
│  │  └──────────────────────────────┘ │ │
│  │                                    │ │
│  │  ┌──────────────────────────────┐ │ │
│  │  │   TodoDashboard              │ │ │
│  │  │  - 실시간 TODO 표시          │ │ │
│  │  │  - 진행률 바                 │ │ │
│  │  │  - ESC 버튼                  │ │ │
│  │  └──────────────────────────────┘ │ │
│  │                                    │ │
│  │  ┌──────────────────────────────┐ │ │
│  │  │   InputBox                   │ │ │
│  │  │  - 메시지 입력               │ │ │
│  │  │  - 전송 버튼                 │ │ │
│  │  └──────────────────────────────┘ │ │
│  └────────────────────────────────────┘ │
│                                          │
│  ┌────────────────────────────────────┐ │
│  │   InterruptModal (Portal)          │ │
│  │  - 승인 모달                       │ │
│  │  - 수정 모달                       │ │
│  │  - 도구 승인 모달                  │ │
│  └────────────────────────────────────┘ │
│                                          │
│  ┌────────────────────────────────────┐ │
│  │   StreamingClient (Hook)           │ │
│  │  - SSE 연결 관리                   │ │
│  │  - 상태 업데이트 처리              │ │
│  └────────────────────────────────────┘ │
└──────────────────────────────────────────┘
```

### 3.2 Backend API 구조

```
┌──────────────────────────────────────────┐
│         FastAPI App (main.py)            │
│                                          │
│  ┌────────────────────────────────────┐ │
│  │   API Router (routes.py)           │ │
│  │                                    │ │
│  │  POST /api/stream                  │ │
│  │  └─> stream_agent()                │ │
│  │                                    │ │
│  │  POST /api/interrupt/{thread_id}   │ │
│  │  └─> user_interrupt()              │ │
│  │                                    │ │
│  │  POST /api/resume/{thread_id}      │ │
│  │  └─> resume_agent()                │ │
│  │                                    │ │
│  │  GET /api/state/{thread_id}        │ │
│  │  └─> get_state()                   │ │
│  └────────────────────────────────────┘ │
│                                          │
│  ┌────────────────────────────────────┐ │
│  │   Graph Manager                    │ │
│  │  - compiled_graph 인스턴스         │ │
│  │  - Checkpointer 관리               │ │
│  └────────────────────────────────────┘ │
│                                          │
│  ┌────────────────────────────────────┐ │
│  │   Middleware                       │ │
│  │  - CORS                            │ │
│  │  - Logging                         │ │
│  │  - Error Handling                  │ │
│  └────────────────────────────────────┘ │
└──────────────────────────────────────────┘
```

---

## 4. 데이터 플로우

### 4.1 새 작업 요청 플로우

```
[User Input] "AI 트렌드 보고서 만들어줘"
    ↓
[Frontend] 메시지 전송 → /api/stream
    ↓
[Backend] SSE 스트리밍 시작
    ↓
[LangGraph] Main Graph 실행
    ↓
┌─────────────────────────────────────────┐
│ 1. intent_analysis                      │
│    - LLM 호출: 의도 분석                │
│    - 결과: "new_task"                   │
│    - Command(goto="planning_agent")     │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│ 2. planning_agent                       │
│    - LLM 호출: TODO 생성                │
│    - TODO 1: 데이터 수집                │
│    - TODO 2: 데이터 분석                │
│    - TODO 3: 보고서 작성                │
│    - interrupt() 발생 📍                │
└─────────────────────────────────────────┘
    ↓
[Backend] __interrupt__ 이벤트 감지
    ↓
[Backend] SSE로 interrupt 데이터 전송
    ↓
[Frontend] InterruptModal 표시
    ↓
[User] "승인" 클릭
    ↓
[Frontend] /api/resume 호출
    ↓
[Backend] Command(resume={"action": "approve"})
    ↓
┌─────────────────────────────────────────┐
│ 3. supervisor_agent                     │
│    - TODO 1 실행 가능 확인              │
│    - Command(goto="worker_subgraph")    │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│ 4. worker_subgraph                      │
│    - router → research_worker           │
│    - 웹 검색 실행                       │
│    - finalize → Command.PARENT          │
└─────────────────────────────────────────┘
    ↓
[Backend] TODO 1 완료 스트리밍
    ↓
[Frontend] TODO 상태 업데이트 (✅ 완료)
    ↓
┌─────────────────────────────────────────┐
│ 5. supervisor_agent (재귀)              │
│    - TODO 2 실행...                     │
└─────────────────────────────────────────┘
```

### 4.2 ESC 중단 플로우

```
[User] ESC 키 누름
    ↓
[Frontend] keydown 이벤트 감지
    ↓
[Frontend] /api/interrupt 호출
    ↓
[Backend] user_interrupted = True 설정
    ↓
[LangGraph] supervisor_agent
    - check_user_interrupted() 감지
    - Command(goto="handle_user_interrupt")
    ↓
┌─────────────────────────────────────────┐
│ handle_user_interrupt                   │
│    - interrupt() 발생 📍                │
│    - 옵션: 수정/계속/중단               │
└─────────────────────────────────────────┘
    ↓
[Backend] __interrupt__ 이벤트 전송
    ↓
[Frontend] InterruptModal 표시
    ↓
[User] "수정" 선택
    ↓
[Frontend] /api/resume 호출
    ↓
[Backend] Command(resume={"action": "modify"})
    ↓
[LangGraph] Command(goto="planning_agent")
    ↓
[Planning Agent] TODO 수정 모드...
```

---

## 5. 통신 프로토콜

### 5.1 Frontend ↔ Backend 통신

#### HTTP POST (요청)
```typescript
// 새 작업 시작
POST /api/stream
Content-Type: application/json

{
  "query": "AI 트렌드 보고서 만들어줘",
  "thread_id": "uuid-or-null"
}
```

#### Server-Sent Events (응답)
```
// 스트리밍 응답
event: update
data: {"todos": [{"id": "todo_1", "status": "in_progress", ...}]}

event: interrupt
data: {"type": "plan_approval", "message": "...", "data": {...}}

event: complete
data: {"status": "completed"}
```

### 5.2 Interrupt 데이터 형식

#### Plan Approval
```json
{
  "type": "plan_approval",
  "message": "다음 계획으로 진행할까요?",
  "interrupt_id": "uuid",
  "data": {
    "proposed_todos": [
      {
        "id": "todo_1",
        "title": "데이터 수집",
        "description": "...",
        "assigned_worker": "research"
      }
    ]
  }
}
```

#### Tool Approval
```json
{
  "type": "tool_approval",
  "message": "웹 검색을 실행할까요?",
  "interrupt_id": "uuid",
  "data": {
    "tool_name": "web_search",
    "parameters": {
      "query": "2025 AI trends"
    }
  }
}
```

#### User Interrupt (ESC)
```json
{
  "type": "todo_modification",
  "message": "어떻게 하시겠습니까?",
  "interrupt_id": "uuid",
  "data": {
    "current_todos": [...],
    "options": ["수정", "계속", "중단"]
  }
}
```

### 5.3 Resume 데이터 형식

```json
// Plan Approval 응답
{
  "action": "approve" | "modify" | "cancel",
  "changes": [...] // modify인 경우
}

// Tool Approval 응답
{
  "approved": true | false
}

// User Interrupt 응답
{
  "action": "modify" | "continue" | "stop"
}
```

---

## 6. 확장성 고려사항

### 6.1 수평 확장 (Horizontal Scaling)

**Backend 다중 인스턴스**:
```
┌─────────┐   ┌─────────┐   ┌─────────┐
│FastAPI 1│   │FastAPI 2│   │FastAPI 3│
└────┬────┘   └────┬────┘   └────┬────┘
     └─────────────┼─────────────┘
                   ↓
            ┌─────────────┐
            │ Load Balancer│
            └──────┬──────┘
                   ↓
          ┌────────────────┐
          │   PostgreSQL   │
          │ (Checkpointer) │
          └────────────────┘
```

**장점**:
- 여러 사용자 동시 처리
- 부하 분산
- 고가용성

**고려사항**:
- Checkpointer는 공유 PostgreSQL 사용
- thread_id로 세션 격리
- Stateless Backend 설계

### 6.2 Worker 확장

**새 Worker 추가**:
```python
# 새 Worker 추가는 간단
worker_graph.add_node("translation_worker", translation_worker)
worker_graph.add_edge("translation_worker", "finalize")

# Router에 조건 추가
def worker_router(state):
    worker_type = state["current_todo"]["assigned_worker"]
    return Command(goto=worker_type)
```

**병렬 처리 확장**:
```python
# Send API로 무제한 병렬 처리
def supervisor_agent(state):
    return [
        Send("worker_subgraph", {"current_todo": todo})
        for todo in ready_todos  # 100개든 1000개든 가능
    ]
```

### 6.3 Store API 활용 (선택)

**장기 메모리 저장**:
```python
from langgraph.store import RedisStore

store = RedisStore(redis_url="redis://localhost:6379")

# 사용자별 히스토리 저장
namespace = (user_id, "todo_history")
store.put(namespace, session_id, {
    "query": query,
    "todos": todos,
    "completed_at": datetime.now()
})

# 벡터 검색 (유사 작업 찾기)
similar_todos = store.search(
    namespace=namespace,
    query=query,
    limit=5
)
```

### 6.4 모니터링 및 로깅

**Middleware 활용**:
```python
from langchain.agents.middleware import AgentMiddleware

class LoggingMiddleware(AgentMiddleware):
    def before_model(self, state, runtime):
        logger.info(f"Model call: {len(state['messages'])} messages")
        return None
    
    def after_model(self, state, runtime):
        logger.info(f"Model response: {state['messages'][-1]}")
        return None

# 적용
agent = create_agent(
    model=model,
    tools=tools,
    middleware=[LoggingMiddleware()]
)
```

**Prometheus 메트릭**:
```python
from prometheus_client import Counter, Histogram

todo_created = Counter('todo_created_total', 'Total TODOs created')
interrupt_occurred = Counter('interrupt_occurred_total', 'Total interrupts')
execution_time = Histogram('execution_time_seconds', 'Execution time')

@execution_time.time()
def execute_todo(todo):
    # ...
    todo_created.inc()
```

---

## 7. 보안 고려사항

### 7.1 인증/인가

**JWT 토큰 기반**:
```python
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer

security = HTTPBearer()

async def get_current_user(token: str = Depends(security)):
    try:
        payload = jwt.decode(token, SECRET_KEY)
        user_id = payload["user_id"]
        return user_id
    except:
        raise HTTPException(status_code=401)

@app.post("/api/stream")
async def stream_agent(
    request: StreamRequest,
    user_id: str = Depends(get_current_user)
):
    # user_id를 context에 포함
    config = {
        "configurable": {
            "thread_id": thread_id,
            "user_id": user_id
        }
    }
```

### 7.2 Thread 격리

```python
# thread_id는 user_id와 결합
thread_id = f"{user_id}_{session_id}"

# 다른 사용자의 thread 접근 불가
if not thread_id.startswith(user_id):
    raise HTTPException(status_code=403)
```

### 7.3 민감 데이터 처리

```python
from langgraph.types import UntrackedValue

# 민감 데이터는 체크포인터에 저장하지 않음
def node(state):
    api_key = UntrackedValue("sk-...")  # 저장 안 됨
    result = call_api(api_key)
    return {"result": result}
```

---

## 8. 에러 처리 전략

### 8.1 Checkpointer 기반 복구

```python
try:
    async for chunk in graph.astream(...):
        yield chunk
except Exception as e:
    # 에러 발생 시 체크포인터에 저장
    logger.error(f"Error: {e}")
    
    # 마지막 체크포인트에서 재개
    state = await graph.aget_state(config)
    # state에는 에러 정보 포함
```

### 8.2 재시도 로직

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10)
)
async def call_llm(prompt):
    return await llm.ainvoke(prompt)
```

### 8.3 Graceful Degradation

```python
def supervisor_agent(state):
    try:
        # 병렬 처리 시도
        return [Send(...) for todo in todos]
    except:
        # 실패 시 순차 처리로 fallback
        return Command(goto="worker_subgraph")
```

---

## 9. 성능 최적화

### 9.1 Node Caching (선택)

```python
from langgraph.cache import RedisCache

cache = RedisCache(redis_url="redis://localhost:6379")

graph.add_node(
    "expensive_node",
    expensive_function,
    {
        "cachePolicy": {
            "ttl": 3600,  # 1시간 캐싱
            "keyFunc": lambda state: state["query"]
        }
    }
)

compiled_graph = graph.compile(cache=cache)
```

### 9.2 비동기 체크포인팅

```python
# LangGraph 1.0은 기본적으로 비동기 모드
# 그래프는 체크포인트 완료를 기다리지 않고 계속 실행
compiled_graph = graph.compile(
    checkpointer=checkpointer,
    # 비동기 내구성 모드 (기본값)
)
```

### 9.3 스트리밍 최적화

```python
# updates 모드: 변경 사항만 스트리밍 (효율적)
async for chunk in graph.astream(
    input,
    config=config,
    stream_mode="updates"  # values보다 효율적
):
    # 변경된 필드만 전송
    if "todos" in chunk:
        yield chunk["todos"]
```

---

## 10. 다음 단계

이 아키텍처 문서를 바탕으로 다음 문서들을 참고하세요:

1. **[02_STATE_SCHEMA.md](./02_STATE_SCHEMA.md)**: State 설계 상세
2. **[03_PHASE1_INTENT_ANALYSIS.md](./03_PHASE1_INTENT_ANALYSIS.md)**: Intent Analysis 구현
3. **[04_PHASE2_PLANNING.md](./04_PHASE2_PLANNING.md)**: Planning Agent 구현

---

**이전 문서**: [00_PROJECT_OVERVIEW.md](./00_PROJECT_OVERVIEW.md)  
**다음 문서**: [02_STATE_SCHEMA.md](./02_STATE_SCHEMA.md)
