# LangGraph Chatbot 구현 계획서

**프로젝트**: Octo_worker Beta v0.02
**목적**: Supervisor 메인 그래프 중심의 점진적 구현
**작성일**: 2025-11-03
**버전**: 1.0

---

## 구현 전략

### 핵심 원칙
1. **Supervisor 우선**: 메인 그래프부터 구축
2. **점진적 확장**: 복잡한 기능은 나중에 추가
3. **동작하는 최소 버전**: 각 Phase마다 실행 가능한 상태 유지
4. **테스트 우선**: 각 Phase 완료 후 동작 확인

### 전체 흐름
```
Phase 0: 환경 설정
    ↓
Phase 1: Supervisor 기본 구조 (단일 노드)
    ↓
Phase 2: Agent 1개 연결 (Search Agent 간단 버전)
    ↓
Phase 3: State + Context 관리
    ↓
Phase 4: WebSocket 기본 통신
    ↓
Phase 5: Checkpointer 연결
    ↓
Phase 6: 나머지 Agent 추가
    ↓
Phase 7: Sub-Agent 구조 추가
    ↓
Phase 8: HITL 구조 추가
```

---

## Phase 0: 환경 설정 및 업그레이드

### 목표
- LangChain 1.0 + LangGraph 1.0 환경 구축
- 기본 프로젝트 구조 생성
- DB 연결 테스트 (PostgreSQL만)

### 구현 항목

#### 1. requirements.txt 업데이트
```txt
# LangChain 1.0
langchain==1.0.3
langchain-core==1.0.2
langchain-openai==1.0.1
langchain-community==0.4.1

# LangGraph 1.0
langgraph==1.0.2
langgraph-checkpoint==3.0.0
langgraph-checkpoint-postgres==3.0.0

# FastAPI
fastapi==0.115.0
uvicorn==0.32.0
websockets==12.0

# Database
psycopg==3.2.10
asyncpg==0.30.0

# Utils
python-dotenv==1.0.1
pydantic==2.9.0
pydantic-settings==2.4.0
```

#### 2. .env 파일 생성
```bash
# .env
OPENAI_API_KEY=your_key_here
POSTGRES_URL=postgresql://user:password@localhost:5432/octo_chatbot
```

#### 3. 기본 디렉토리 구조
```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI 엔트리포인트
│   ├── config/
│   │   ├── __init__.py
│   │   └── system.py
│   ├── core/
│   │   └── __init__.py
│   ├── states/
│   │   └── __init__.py
│   └── graphs/
│       └── __init__.py
├── .env
└── requirements.txt
```

#### 4. 완료 조건
- ✅ `uv pip install -r requirements.txt` 성공
- ✅ PostgreSQL 연결 테스트 성공
- ✅ FastAPI 기본 앱 실행 (`uvicorn app.main:app --reload`)

---

## Phase 1: Supervisor 기본 구조 (최소 버전)

### 목표
- Supervisor Graph 단일 노드로 실행
- LLM 호출 테스트
- 기본 State 정의

### 구현 파일

#### 1. `app/states/supervisor_state.py`
```python
from typing import TypedDict, Annotated, Sequence
from langchain_core.messages import BaseMessage, add_messages

class SupervisorState(TypedDict):
    """Supervisor 기본 State (최소 버전)"""
    messages: Annotated[Sequence[BaseMessage], add_messages]
```

#### 2. `app/config/system.py`
```python
from pydantic_settings import BaseSettings

class SystemConfig(BaseSettings):
    """시스템 설정 (최소 버전)"""
    openai_api_key: str

    class Config:
        env_file = ".env"
```

#### 3. `app/graphs/supervisor.py`
```python
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from app.states.supervisor_state import SupervisorState
from app.config.system import SystemConfig

def build_supervisor_graph():
    """Supervisor Graph 생성 (최소 버전)"""

    config = SystemConfig()
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.7,
        api_key=config.openai_api_key
    )

    # StateGraph 생성
    workflow = StateGraph(SupervisorState)

    # 노드: LLM 호출만
    async def supervisor_node(state: SupervisorState):
        """Supervisor 노드 - 단순 LLM 호출"""
        messages = state["messages"]
        response = await llm.ainvoke(messages)
        return {"messages": [response]}

    # 노드 추가
    workflow.add_node("supervisor", supervisor_node)

    # 엣지: 시작 -> supervisor -> 종료
    workflow.set_entry_point("supervisor")
    workflow.add_edge("supervisor", END)

    return workflow.compile()
```

#### 4. `app/main.py`
```python
from fastapi import FastAPI
from app.graphs.supervisor import build_supervisor_graph
from langchain_core.messages import HumanMessage

app = FastAPI(title="LangGraph Chatbot", version="0.1.0")

# Supervisor Graph
supervisor_graph = build_supervisor_graph()

@app.get("/")
async def root():
    return {"message": "LangGraph Chatbot API"}

@app.post("/chat")
async def chat(message: str):
    """간단한 채팅 엔드포인트 (테스트용)"""
    result = await supervisor_graph.ainvoke({
        "messages": [HumanMessage(content=message)]
    })
    return {"response": result["messages"][-1].content}
```

#### 5. 테스트
```bash
# 서버 실행
uvicorn app.main:app --reload

# 테스트 (다른 터미널)
curl -X POST "http://localhost:8000/chat?message=Hello"
```

#### 6. 완료 조건
- ✅ Supervisor Graph 컴파일 성공
- ✅ LLM 호출 및 응답 받기 성공
- ✅ `/chat` 엔드포인트에서 응답 확인

---

## Phase 2: Agent 1개 연결 (Search Agent 간단 버전)

### 목표
- Supervisor가 Agent를 호출하는 구조
- 조건부 라우팅 추가
- Agent는 단순 문자열 반환 (실제 검색 기능 없음)

### 구현 파일

#### 1. `app/states/supervisor_state.py` (업데이트)
```python
from typing import TypedDict, Annotated, Sequence, Optional
from langchain_core.messages import BaseMessage, add_messages

class SupervisorState(TypedDict):
    """Supervisor State"""
    messages: Annotated[Sequence[BaseMessage], add_messages]
    next: str  # 다음 실행할 노드 이름
```

#### 2. `app/agents/search_agent/agent.py`
```python
from langchain_core.messages import AIMessage

async def search_agent_node(state):
    """Search Agent 노드 (간단 버전 - 실제 검색 없음)"""
    last_message = state["messages"][-1]

    # 단순 응답
    response = AIMessage(
        content=f"[Search Agent] '{last_message.content}'에 대한 검색 결과입니다."
    )

    return {"messages": [response]}
```

#### 3. `app/graphs/supervisor.py` (업데이트)
```python
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage
from app.states.supervisor_state import SupervisorState
from app.config.system import SystemConfig
from app.agents.search_agent.agent import search_agent_node

def build_supervisor_graph():
    """Supervisor Graph 생성 (Agent 라우팅 버전)"""

    config = SystemConfig()
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.7,
        api_key=config.openai_api_key
    )

    workflow = StateGraph(SupervisorState)

    # Supervisor 노드: Agent 선택
    async def supervisor_node(state: SupervisorState):
        """어떤 Agent를 실행할지 결정"""
        messages = state["messages"]

        # LLM에게 Agent 선택 요청
        system_prompt = SystemMessage(content="""
        You are a supervisor. Analyze the user's request and choose:
        - "search" if the user wants to search for information
        - "finish" if you can answer directly without search

        Respond with just one word: "search" or "finish"
        """)

        response = await llm.ainvoke([system_prompt] + list(messages))
        next_node = response.content.strip().lower()

        # 유효성 검사
        if next_node not in ["search", "finish"]:
            next_node = "finish"

        return {"next": next_node}

    # Finish 노드: 최종 응답
    async def finish_node(state: SupervisorState):
        """최종 응답 생성"""
        messages = state["messages"]
        response = await llm.ainvoke(messages)
        return {"messages": [response]}

    # 조건부 라우팅
    def route_supervisor(state: SupervisorState):
        """Supervisor의 결정에 따라 라우팅"""
        return state.get("next", "finish")

    # 노드 추가
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("search_agent", search_agent_node)
    workflow.add_node("finish", finish_node)

    # 엣지
    workflow.set_entry_point("supervisor")

    # Supervisor -> Agent or Finish
    workflow.add_conditional_edges(
        "supervisor",
        route_supervisor,
        {
            "search": "search_agent",
            "finish": "finish"
        }
    )

    # Agent -> Finish
    workflow.add_edge("search_agent", "finish")

    # Finish -> END
    workflow.add_edge("finish", END)

    return workflow.compile()
```

#### 4. 테스트
```bash
# 검색이 필요한 요청
curl -X POST "http://localhost:8000/chat?message=What is LangGraph?"

# 직접 답변 가능한 요청
curl -X POST "http://localhost:8000/chat?message=Hello!"
```

#### 5. 완료 조건
- ✅ Supervisor가 Agent를 선택하는 로직 동작
- ✅ Search Agent 실행 확인
- ✅ Finish 노드에서 최종 응답 생성

---

## Phase 3: State + Context 관리

### 목표
- RuntimeContext 추가
- SessionContext 기본 구조
- ContextManager 연결

### 구현 파일

#### 1. `app/core/context/runtime_context.py`
```python
from typing import Any, Dict
from datetime import datetime

class RuntimeContext:
    """실행 중 임시 Context (간단 버전)"""

    def __init__(self):
        self._data: Dict[str, Any] = {}
        self._created_at = datetime.now()

    def set(self, key: str, value: Any):
        self._data[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def to_dict(self) -> Dict[str, Any]:
        return {
            **self._data,
            "_created_at": self._created_at.isoformat()
        }
```

#### 2. `app/core/context/manager.py`
```python
from app.core.context.runtime_context import RuntimeContext

class ContextManager:
    """Context 생명주기 관리 (간단 버전)"""

    def __init__(self):
        self._runtime_context = None

    def create_runtime_context(self) -> RuntimeContext:
        self._runtime_context = RuntimeContext()
        return self._runtime_context

    def get_runtime_context(self) -> RuntimeContext:
        if not self._runtime_context:
            return self.create_runtime_context()
        return self._runtime_context

    def cleanup(self):
        self._runtime_context = None
```

#### 3. `app/main.py` (업데이트)
```python
from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.graphs.supervisor import build_supervisor_graph
from app.core.context.manager import ContextManager
from langchain_core.messages import HumanMessage

# Lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    app.state.context_manager = ContextManager()
    app.state.supervisor_graph = build_supervisor_graph()
    print("✅ LangGraph Chatbot started")

    yield

    # Shutdown
    app.state.context_manager.cleanup()
    print("🛑 LangGraph Chatbot stopped")

app = FastAPI(
    title="LangGraph Chatbot",
    version="0.2.0",
    lifespan=lifespan
)

@app.post("/chat")
async def chat(message: str):
    """채팅 엔드포인트 (Context 포함)"""
    # Context 생성
    ctx = app.state.context_manager.create_runtime_context()
    ctx.set("request_time", "2025-11-03")

    # Graph 실행
    result = await app.state.supervisor_graph.ainvoke({
        "messages": [HumanMessage(content=message)]
    })

    # Context 정리
    app.state.context_manager.cleanup()

    return {
        "response": result["messages"][-1].content,
        "context": ctx.to_dict()
    }
```

#### 4. 완료 조건
- ✅ RuntimeContext 생성 및 조회 가능
- ✅ ContextManager가 생명주기 관리
- ✅ `/chat` 응답에 context 정보 포함

---

## Phase 4: WebSocket 기본 통신

### 목표
- WebSocket 엔드포인트 추가
- 실시간 메시지 송수신
- 간단한 연결 관리

### 구현 파일

#### 1. `app/core/websocket_manager.py`
```python
from typing import Dict
from fastapi import WebSocket

class ConnectionManager:
    """WebSocket 연결 관리 (간단 버전)"""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, client_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[client_id] = websocket

    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]

    async def send_message(self, client_id: str, message: dict):
        if client_id in self.active_connections:
            await self.active_connections[client_id].send_json(message)
```

#### 2. `app/api/websocket.py`
```python
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.core.websocket_manager import ConnectionManager
from langchain_core.messages import HumanMessage
import uuid

router = APIRouter()
manager = ConnectionManager()

@router.websocket("/chat")
async def websocket_chat(websocket: WebSocket):
    """WebSocket 채팅 엔드포인트"""
    client_id = str(uuid.uuid4())

    await manager.connect(client_id, websocket)

    try:
        while True:
            # 클라이언트로부터 메시지 수신
            data = await websocket.receive_json()
            message = data.get("message", "")

            # Graph 실행 (app.state에서 가져오기)
            from app.main import app
            result = await app.state.supervisor_graph.ainvoke({
                "messages": [HumanMessage(content=message)]
            })

            # 응답 전송
            await manager.send_message(client_id, {
                "response": result["messages"][-1].content,
                "client_id": client_id
            })

    except WebSocketDisconnect:
        manager.disconnect(client_id)
        print(f"Client {client_id} disconnected")
```

#### 3. `app/main.py` (업데이트)
```python
from app.api import websocket

# ... 기존 코드 ...

# WebSocket 라우터 등록
app.include_router(websocket.router, prefix="/ws", tags=["websocket"])
```

#### 4. 테스트 (Python 클라이언트)
```python
# test_websocket.py
import asyncio
import websockets
import json

async def test_chat():
    uri = "ws://localhost:8000/ws/chat"
    async with websockets.connect(uri) as websocket:
        # 메시지 전송
        await websocket.send(json.dumps({"message": "Hello from WebSocket!"}))

        # 응답 수신
        response = await websocket.recv()
        print(f"Received: {response}")

asyncio.run(test_chat())
```

#### 5. 완료 조건
- ✅ WebSocket 연결 및 통신 성공
- ✅ 실시간 메시지 송수신 확인
- ✅ 클라이언트 연결/해제 관리

---

## Phase 5: Checkpointer 연결 (Thread ID 기반)

### 목표
- PostgreSQL Checkpointer 연결
- Thread ID 기반 대화 이력 저장
- 대화 복원 기능

### 구현 파일

#### 1. PostgreSQL 테이블 생성
```sql
-- checkpointer 테이블 자동 생성 (setup() 메서드 호출 시)
```

#### 2. `app/core/checkpointer.py`
```python
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from app.config.system import SystemConfig

class CheckpointerManager:
    """Checkpointer 관리 (간단 버전)"""

    def __init__(self):
        self.checkpointer = None

    async def initialize(self, db_url: str):
        """Checkpointer 초기화"""
        self.checkpointer = AsyncPostgresSaver.from_conn_string(db_url)
        await self.checkpointer.setup()
        print("✅ Checkpointer initialized")

    async def close(self):
        """Checkpointer 종료"""
        if self.checkpointer:
            # AsyncPostgresSaver의 cleanup 메서드 호출 (있다면)
            pass
```

#### 3. `app/config/system.py` (업데이트)
```python
from pydantic_settings import BaseSettings

class SystemConfig(BaseSettings):
    """시스템 설정"""
    openai_api_key: str
    postgres_url: str  # 추가

    class Config:
        env_file = ".env"
```

#### 4. `app/main.py` (업데이트)
```python
from app.core.checkpointer import CheckpointerManager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    config = SystemConfig()

    # Checkpointer 초기화
    app.state.checkpointer_manager = CheckpointerManager()
    await app.state.checkpointer_manager.initialize(config.postgres_url)

    # Context Manager
    app.state.context_manager = ContextManager()

    # Supervisor Graph (Checkpointer 포함)
    app.state.supervisor_graph = build_supervisor_graph(
        checkpointer=app.state.checkpointer_manager.checkpointer
    )

    print("✅ LangGraph Chatbot started")

    yield

    # Shutdown
    await app.state.checkpointer_manager.close()
    app.state.context_manager.cleanup()
    print("🛑 LangGraph Chatbot stopped")
```

#### 5. `app/graphs/supervisor.py` (업데이트)
```python
def build_supervisor_graph(checkpointer=None):
    """Supervisor Graph 생성 (Checkpointer 포함)"""

    # ... 기존 코드 ...

    # Checkpointer와 함께 컴파일
    return workflow.compile(checkpointer=checkpointer)
```

#### 6. `app/api/websocket.py` (업데이트)
```python
@router.websocket("/chat/{user_id}")
async def websocket_chat(websocket: WebSocket, user_id: str):
    """WebSocket 채팅 (Thread ID 포함)"""
    client_id = str(uuid.uuid4())
    thread_id = f"{user_id}_{client_id}"  # Thread ID 생성

    await manager.connect(client_id, websocket)

    try:
        while True:
            data = await websocket.receive_json()
            message = data.get("message", "")

            # Graph 실행 (Thread ID 포함)
            from app.main import app
            config = {"configurable": {"thread_id": thread_id}}

            result = await app.state.supervisor_graph.ainvoke(
                {"messages": [HumanMessage(content=message)]},
                config=config
            )

            await manager.send_message(client_id, {
                "response": result["messages"][-1].content,
                "thread_id": thread_id
            })

    except WebSocketDisconnect:
        manager.disconnect(client_id)
```

#### 7. 테스트
```python
# 같은 user_id로 재연결 시 이전 대화 이력 유지 확인
async def test_checkpoint():
    uri = "ws://localhost:8000/ws/chat/user123"
    async with websockets.connect(uri) as ws:
        # 첫 번째 메시지
        await ws.send(json.dumps({"message": "My name is Alice"}))
        resp1 = await ws.recv()
        print(resp1)

        # 두 번째 메시지 (이름 기억하는지 테스트)
        await ws.send(json.dumps({"message": "What is my name?"}))
        resp2 = await ws.recv()
        print(resp2)  # "Alice"를 포함해야 함
```

#### 8. 완료 조건
- ✅ PostgreSQL에 checkpoint 테이블 생성
- ✅ Thread ID 기반 대화 저장
- ✅ 재연결 시 대화 이력 복원

---

## Phase 6: 나머지 Agent 추가

### 목표
- Analysis Agent 추가
- Document Agent 추가
- Supervisor가 3개 Agent 중 선택

### 구현 파일

#### 1. `app/agents/analysis_agent/agent.py`
```python
from langchain_core.messages import AIMessage

async def analysis_agent_node(state):
    """Analysis Agent 노드 (간단 버전)"""
    last_message = state["messages"][-1]

    response = AIMessage(
        content=f"[Analysis Agent] '{last_message.content}'를 분석한 결과입니다."
    )

    return {"messages": [response]}
```

#### 2. `app/agents/document_agent/agent.py`
```python
from langchain_core.messages import AIMessage

async def document_agent_node(state):
    """Document Agent 노드 (간단 버전)"""
    last_message = state["messages"][-1]

    response = AIMessage(
        content=f"[Document Agent] '{last_message.content}'에 대한 문서를 생성했습니다."
    )

    return {"messages": [response]}
```

#### 3. `app/graphs/supervisor.py` (업데이트)
```python
from app.agents.analysis_agent.agent import analysis_agent_node
from app.agents.document_agent.agent import document_agent_node

def build_supervisor_graph(checkpointer=None):
    """Supervisor Graph (3개 Agent)"""

    # ... 기존 코드 ...

    # Supervisor 노드: 3개 Agent 중 선택
    async def supervisor_node(state: SupervisorState):
        messages = state["messages"]

        system_prompt = SystemMessage(content="""
        You are a supervisor. Choose the best agent:
        - "search": for information search
        - "analysis": for data analysis
        - "document": for document generation
        - "finish": if you can answer directly

        Respond with just one word.
        """)

        response = await llm.ainvoke([system_prompt] + list(messages))
        next_node = response.content.strip().lower()

        if next_node not in ["search", "analysis", "document", "finish"]:
            next_node = "finish"

        return {"next": next_node}

    # 노드 추가
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("search_agent", search_agent_node)
    workflow.add_node("analysis_agent", analysis_agent_node)
    workflow.add_node("document_agent", document_agent_node)
    workflow.add_node("finish", finish_node)

    # 엣지
    workflow.set_entry_point("supervisor")

    workflow.add_conditional_edges(
        "supervisor",
        route_supervisor,
        {
            "search": "search_agent",
            "analysis": "analysis_agent",
            "document": "document_agent",
            "finish": "finish"
        }
    )

    # 모든 Agent -> Finish
    workflow.add_edge("search_agent", "finish")
    workflow.add_edge("analysis_agent", "finish")
    workflow.add_edge("document_agent", "finish")
    workflow.add_edge("finish", END)

    return workflow.compile(checkpointer=checkpointer)
```

#### 4. 완료 조건
- ✅ Supervisor가 3개 Agent 중 선택
- ✅ 각 Agent 실행 확인
- ✅ Finish 노드에서 최종 응답

---

## Phase 7: Sub-Agent 구조 추가

### 목표
- Search Agent에 Sub-Agent 추가 (Vector Search만)
- Sub-Agent를 SubGraph로 구현
- Supervisor → Agent → Sub-Agent 흐름 확인

### 구현 파일

#### 1. `app/agents/search_agent/sub_agents/vector_search.py`
```python
from langgraph.graph import StateGraph, END
from typing import TypedDict, List, Dict, Any
from langchain_core.messages import AIMessage

class VectorSearchState(TypedDict):
    """Vector Search Sub-Agent State"""
    query: str
    results: List[Dict[str, Any]]

async def search_node(state: VectorSearchState):
    """벡터 검색 (간단 버전 - 실제 FAISS 없음)"""
    query = state["query"]

    # 가짜 결과
    fake_results = [
        {"content": f"Result 1 for '{query}'", "score": 0.9},
        {"content": f"Result 2 for '{query}'", "score": 0.8},
    ]

    return {"results": fake_results}

def create_vector_search_subgraph():
    """Vector Search Sub-Graph"""
    workflow = StateGraph(VectorSearchState)

    workflow.add_node("search", search_node)
    workflow.set_entry_point("search")
    workflow.add_edge("search", END)

    return workflow.compile()
```

#### 2. `app/agents/search_agent/agent.py` (업데이트)
```python
from langgraph.graph import StateGraph, END
from typing import TypedDict, Optional, List, Dict, Any
from langchain_core.messages import AIMessage
from app.agents.search_agent.sub_agents.vector_search import create_vector_search_subgraph

class SearchAgentState(TypedDict):
    """Search Agent State"""
    query: str
    vector_results: Optional[List[Dict[str, Any]]]
    final_response: Optional[str]

def create_search_agent_graph():
    """Search Agent Graph (Sub-Agent 포함)"""

    workflow = StateGraph(SearchAgentState)

    # Vector Search Sub-Graph
    vector_subgraph = create_vector_search_subgraph()

    # 노드: Vector Search 실행
    async def run_vector_search(state: SearchAgentState):
        query = state["query"]

        # Sub-Graph 실행
        result = await vector_subgraph.ainvoke({"query": query})

        return {"vector_results": result["results"]}

    # 노드: 결과 종합
    async def synthesize_results(state: SearchAgentState):
        results = state["vector_results"]

        # 간단한 종합
        response = f"검색 결과: {len(results)}개 발견\n"
        for i, r in enumerate(results, 1):
            response += f"{i}. {r['content']} (score: {r['score']})\n"

        return {"final_response": response}

    workflow.add_node("vector_search", run_vector_search)
    workflow.add_node("synthesize", synthesize_results)

    workflow.set_entry_point("vector_search")
    workflow.add_edge("vector_search", "synthesize")
    workflow.add_edge("synthesize", END)

    return workflow.compile()

# Supervisor에서 사용할 노드
async def search_agent_node(state):
    """Search Agent 노드 (SubGraph 버전)"""
    last_message = state["messages"][-1]

    # Search Agent Graph 실행
    search_graph = create_search_agent_graph()
    result = await search_graph.ainvoke({"query": last_message.content})

    response = AIMessage(content=result["final_response"])
    return {"messages": [response]}
```

#### 3. 완료 조건
- ✅ Search Agent가 Vector Search Sub-Agent 호출
- ✅ Sub-Graph 실행 및 결과 반환
- ✅ Supervisor → Search Agent → Vector Search 흐름 확인

---

## Phase 8: HITL 구조 추가

### 목표
- Supervisor 레벨 HITL 추가
- Interrupt 및 승인 메커니즘
- 승인 후 재개

### 구현 파일

#### 1. `app/graphs/supervisor.py` (HITL 추가)
```python
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

def build_supervisor_graph(checkpointer=None):
    """Supervisor Graph (HITL 포함)"""

    # ... 기존 코드 ...

    # Human 노드 (승인 대기)
    async def human_approval_node(state: SupervisorState):
        """Human 승인 대기"""
        # 이 노드는 interrupt로 인해 실행이 일시 중지됨
        # 실제로는 아무것도 하지 않고, 외부에서 승인 후 재개
        return state

    workflow.add_node("human_approval", human_approval_node)

    # Supervisor -> Human Approval -> Agent
    workflow.add_edge("supervisor", "human_approval")

    workflow.add_conditional_edges(
        "human_approval",
        route_supervisor,
        {
            "search": "search_agent",
            "analysis": "analysis_agent",
            "document": "document_agent",
            "finish": "finish"
        }
    )

    # 컴파일 (interrupt 설정)
    return workflow.compile(
        checkpointer=checkpointer,
        interrupt_before=["human_approval"]  # HITL 지점
    )
```

#### 2. `app/api/websocket.py` (HITL 처리)
```python
@router.websocket("/chat/{user_id}")
async def websocket_chat(websocket: WebSocket, user_id: str):
    """WebSocket 채팅 (HITL 포함)"""
    client_id = str(uuid.uuid4())
    thread_id = f"{user_id}_{client_id}"

    await manager.connect(client_id, websocket)

    try:
        while True:
            data = await websocket.receive_json()
            action = data.get("action", "chat")

            from app.main import app
            config = {"configurable": {"thread_id": thread_id}}

            if action == "chat":
                # 일반 채팅
                message = data.get("message", "")
                result = await app.state.supervisor_graph.ainvoke(
                    {"messages": [HumanMessage(content=message)]},
                    config=config
                )

                # Interrupt 확인
                state = await app.state.supervisor_graph.aget_state(config)
                if state.next:  # Interrupt 발생
                    await manager.send_message(client_id, {
                        "type": "approval_required",
                        "next_node": state.next[0],
                        "thread_id": thread_id
                    })
                else:
                    await manager.send_message(client_id, {
                        "type": "response",
                        "response": result["messages"][-1].content
                    })

            elif action == "approve":
                # 승인 후 재개
                result = await app.state.supervisor_graph.ainvoke(
                    None,  # 기존 state 사용
                    config=config
                )

                await manager.send_message(client_id, {
                    "type": "response",
                    "response": result["messages"][-1].content
                })

            elif action == "reject":
                # 거부
                await manager.send_message(client_id, {
                    "type": "rejected",
                    "message": "요청이 거부되었습니다."
                })

    except WebSocketDisconnect:
        manager.disconnect(client_id)
```

#### 3. 테스트
```python
# 1. 메시지 전송
await ws.send(json.dumps({"action": "chat", "message": "Search for LangGraph"}))

# 2. 승인 요청 수신
# {"type": "approval_required", "next_node": "human_approval"}

# 3. 승인
await ws.send(json.dumps({"action": "approve"}))

# 4. 최종 응답 수신
```

#### 4. 완료 조건
- ✅ Interrupt 지점에서 실행 일시 중지
- ✅ 승인 요청 메시지 전송
- ✅ 승인 후 재개 및 최종 응답

---

## 구현 순서 요약

```
Phase 0: 환경 설정 (1일)
   ↓
Phase 1: Supervisor 기본 (1일)
   ↓
Phase 2: Agent 1개 연결 (1-2일)
   ↓
Phase 3: Context 관리 (1일)
   ↓
Phase 4: WebSocket (1-2일)
   ↓
Phase 5: Checkpointer (2-3일)
   ↓
Phase 6: 나머지 Agent (1일)
   ↓
Phase 7: Sub-Agent (2-3일)
   ↓
Phase 8: HITL (2-3일)
```

**총 예상 기간**: 약 2-3주

---

## 각 Phase별 성공 기준

| Phase | 핵심 기능 | 테스트 방법 |
|-------|---------|-----------|
| 0 | LangChain 1.0 설치 | `python -c "import langgraph; print(langgraph.__version__)"` |
| 1 | Supervisor 실행 | `/chat` 엔드포인트 호출 |
| 2 | Agent 라우팅 | 검색 요청 시 Search Agent 실행 확인 |
| 3 | Context 생성 | 응답에 context 정보 포함 |
| 4 | WebSocket 통신 | WebSocket 클라이언트로 메시지 송수신 |
| 5 | 대화 저장 | 재연결 시 이전 대화 복원 |
| 6 | 3개 Agent | 각 Agent 선택 테스트 |
| 7 | Sub-Agent | Search Agent → Vector Search 실행 |
| 8 | HITL | 승인 요청 및 재개 |

---

## 다음 단계

Phase 8 완료 후:
- Registry 패턴 적용 (Agent, Tool, Config)
- 실제 Tool 구현 (FAISS, PostgreSQL, MongoDB)
- Frontend (React) 구현
- 추가 Sub-Agent 및 기능 확장

---

**작성자**: Claude
**버전**: 1.0
**최종 수정**: 2025-11-03
**문서 상태**: ✅ 준비 완료
