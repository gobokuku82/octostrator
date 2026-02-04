# LangGraph 1.0 기반 TODO 관리 시스템 구현 계획서

**작성일**: 2025-11-16
**프로젝트**: Octostrator Beta v001
**기술 스택**: FastAPI, React/Next.js, LangGraph 1.0.x, PostgreSQL, OpenAI GPT-4o-mini

---

## 목차

1. [시스템 개요](#1-시스템-개요)
2. [핵심 요구사항 분석](#2-핵심-요구사항-분석)
3. [아키텍처 설계](#3-아키텍처-설계)
4. [데이터베이스 스키마](#4-데이터베이스-스키마)
5. [LangGraph 구현 상세](#5-langgraph-구현-상세)
6. [Human-in-the-Loop 구현](#6-human-in-the-loop-구현)
7. [FastAPI 백엔드 구현](#7-fastapi-백엔드-구현)
8. [Frontend 구현](#8-frontend-구현)
9. [구현 순서](#9-구현-순서)
10. [테스트 전략](#10-테스트-전략)

---

## 1. 시스템 개요

### 1.1 프로젝트 구조

```
backend/
├── app/
│   ├── api/              # FastAPI 라우터 및 엔드포인트
│   │   ├── __init__.py
│   │   ├── sessions.py   # 세션 관리 API
│   │   ├── todos.py      # TODO 관리 API
│   │   └── websocket.py  # 실시간 통신
│   └── octostrator/      # LangGraph 1.0 에이전트
│       ├── __init__.py
│       ├── graph.py      # 메인 그래프 정의
│       ├── nodes.py      # 노드 함수들
│       ├── state.py      # 상태 정의
│       └── checkpointer.py # PostgreSQL 체크포인터
├── db/                   # 데이터베이스 관련
│   ├── __init__.py
│   ├── session.py        # DB 세션 관리
│   └── init_db.py        # DB 초기화 스크립트
├── schema/               # Pydantic 스키마
│   ├── __init__.py
│   ├── todo.py
│   └── session.py
└── models/               # SQLAlchemy 모델
    ├── __init__.py
    ├── todo.py
    └── session.py

frontend/
├── app/                  # Next.js 앱 디렉토리
│   ├── layout.tsx
│   ├── page.tsx
│   └── todos/
│       ├── page.tsx
│       └── [id]/page.tsx
├── components/
│   ├── TodoList.tsx
│   ├── TodoEditor.tsx
│   └── InterruptModal.tsx
└── lib/
    ├── api.ts            # API 클라이언트
    └── websocket.ts      # WebSocket 클라이언트

data/                     # 데이터 저장소 (옵션)
```

### 1.2 시스템 목표

- 사용자 질의 기반 자동 TODO 생성
- 언제든지 가능한 사용자 개입 (Human-in-the-Loop)
- 조건부 에이전트 중단 및 사용자 확인 요청
- PostgreSQL 기반 영구 상태 저장 및 복구

---

## 2. 핵심 요구사항 분석

### 2.1 요구사항 매핑

| 요구사항 | LangGraph 1.0 기능 | 구현 방법 |
|---------|-------------------|----------|
| 1. 사용자 질의 → TODO 생성 | State Management | TypedDict 기반 상태에 todos 리스트 관리 |
| 2. Human-in-the-Loop | `interrupt()` 함수 | 사용자가 수동으로 그래프 실행 중단 및 TODO 수정 |
| 3. AsyncPostgresSaver | Checkpointer | `langgraph-checkpoint-postgres` 사용 |
| 4. 조건부 에이전트 중단 | Dynamic Interrupts | 조건문 + `interrupt()` 호출 |

### 2.2 LangGraph 1.0.x 핵심 개념

#### A. Interrupt 함수

```python
from langgraph.types import interrupt, Command

def node_with_interrupt(state):
    # 조건부 중단
    if needs_confirmation(state):
        user_input = interrupt("사용자 확인이 필요합니다.")
        # user_input은 Command(resume=...)로 전달된 값
    return state
```

**특징**:
- 그래프 실행을 일시 중지하고 외부 입력 대기
- 체크포인터에 현재 상태 저장
- `Command(resume=값)` 으로 재개 시 해당 값이 interrupt()의 반환값이 됨
- 노드는 처음부터 다시 실행되지만, 이전 노드들은 재실행되지 않음

#### B. Static Breakpoints vs Dynamic Interrupts

| 구분 | Static Breakpoints | Dynamic Interrupts |
|------|-------------------|-------------------|
| 설정 위치 | 컴파일 시 또는 런타임 (interrupt_before/after) | 노드 내부 코드 |
| 조건부 실행 | 불가능 | 가능 (if 문 사용) |
| 유연성 | 낮음 | 높음 |
| 사용 사례 | 디버깅, 단계별 실행 | 조건부 승인, 동적 검증 |

#### C. Command 객체

```python
# 그래프 재개
for event in graph.stream(
    Command(resume="사용자 입력값"),
    thread,
    stream_mode="updates"
):
    print(event)
```

### 2.3 AsyncPostgresSaver 요구사항

**설치**:
```bash
pip install langgraph-checkpoint-postgres
```

**필수 설정**:
1. `autocommit=True`: setup() 메서드가 테이블 생성을 커밋하도록 함
2. `row_factory=dict_row`: 딕셔너리 스타일 행 접근 지원

**초기화**:
```python
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

async with AsyncPostgresSaver.from_conn_string(DB_URI) as checkpointer:
    await checkpointer.setup()  # 테이블 생성
```

---

## 3. 아키텍처 설계

### 3.1 전체 시스템 플로우

```mermaid
sequenceDiagram
    participant U as User (Frontend)
    participant API as FastAPI
    participant G as LangGraph
    participant DB as PostgreSQL
    participant LLM as OpenAI GPT-4o-mini

    U->>API: 질의 전송
    API->>G: 그래프 실행 시작
    G->>LLM: 질의 분석 요청
    LLM-->>G: TODO 항목 제안
    G->>DB: 상태 저장 (checkpointer)

    alt 조건부 중단
        G->>G: interrupt() 호출
        G->>DB: 현재 상태 저장
        G-->>API: interrupted 상태 반환
        API-->>U: 중단 알림 + TODO 표시
        U->>API: TODO 수정 + 재개 요청
        API->>G: Command(resume=수정된TODO)
        G->>DB: 상태 복구
    end

    G->>DB: 최종 상태 저장
    G-->>API: 완료
    API-->>U: 결과 반환
```

### 3.2 LangGraph 구조

```mermaid
graph TD
    START([START]) --> PARSE[질의 파싱 노드]
    PARSE --> GENERATE[TODO 생성 노드]
    GENERATE --> VALIDATE{검증 필요?}
    VALIDATE -->|Yes| INTERRUPT[사용자 확인 요청]
    VALIDATE -->|No| SAVE[TODO 저장 노드]
    INTERRUPT --> RESUME[사용자 입력 처리]
    RESUME --> SAVE
    SAVE --> END([END])
```

### 3.3 상태 관리

**State 정의**:
```python
from typing import TypedDict, List, Annotated, Literal
from langgraph.graph import add_messages
from langchain_core.messages import BaseMessage

class TodoItem(TypedDict):
    id: str
    title: str
    description: str
    status: Literal["pending", "in_progress", "completed"]
    priority: Literal["low", "medium", "high"]
    created_at: str

class GraphState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    user_query: str
    todos: List[TodoItem]
    current_todo_index: int
    requires_confirmation: bool
    user_feedback: str | None
    session_id: str
```

---

## 4. 데이터베이스 스키마

### 4.1 LangGraph Checkpointer 테이블

AsyncPostgresSaver가 자동 생성:

```sql
-- 체크포인트 저장
CREATE TABLE checkpoints (
    thread_id TEXT NOT NULL,
    checkpoint_ns TEXT NOT NULL DEFAULT '',
    checkpoint_id TEXT NOT NULL,
    parent_checkpoint_id TEXT,
    type TEXT,
    checkpoint JSONB NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}',
    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id)
);

-- 체크포인트 쓰기 작업
CREATE TABLE checkpoint_writes (
    thread_id TEXT NOT NULL,
    checkpoint_ns TEXT NOT NULL DEFAULT '',
    checkpoint_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    idx INTEGER NOT NULL,
    channel TEXT NOT NULL,
    type TEXT,
    value JSONB,
    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id, task_id, idx)
);
```

### 4.2 애플리케이션 테이블

```sql
-- 세션 관리
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255),
    thread_id TEXT UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(50) DEFAULT 'active',
    metadata JSONB DEFAULT '{}'
);

-- TODO 항목 (옵션 - 그래프 상태와 별도 저장)
CREATE TABLE todos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES sessions(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT,
    status VARCHAR(50) DEFAULT 'pending',
    priority VARCHAR(50) DEFAULT 'medium',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'
);

-- 인덱스
CREATE INDEX idx_sessions_thread_id ON sessions(thread_id);
CREATE INDEX idx_sessions_status ON sessions(status);
CREATE INDEX idx_todos_session_id ON todos(session_id);
CREATE INDEX idx_todos_status ON todos(status);
```

---

## 5. LangGraph 구현 상세

### 5.1 체크포인터 설정

**파일**: `backend/app/octostrator/checkpointer.py`

```python
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg import AsyncConnection
from psycopg.rows import dict_row
from typing import Optional
import os

class CheckpointerManager:
    """AsyncPostgresSaver 관리 클래스"""

    _instance: Optional[AsyncPostgresSaver] = None
    _connection: Optional[AsyncConnection] = None

    @classmethod
    async def get_checkpointer(cls) -> AsyncPostgresSaver:
        """싱글톤 체크포인터 인스턴스 반환"""
        if cls._instance is None:
            await cls.initialize()
        return cls._instance

    @classmethod
    async def initialize(cls):
        """체크포인터 초기화"""
        db_uri = os.getenv("DATABASE_URL")

        # 방법 1: from_conn_string 사용 (권장)
        cls._instance = AsyncPostgresSaver.from_conn_string(db_uri)
        await cls._instance.setup()  # 테이블 생성

        # 방법 2: 수동 연결 (세밀한 제어 필요 시)
        # cls._connection = await AsyncConnection.connect(
        #     db_uri,
        #     autocommit=True,
        #     row_factory=dict_row
        # )
        # cls._instance = AsyncPostgresSaver(cls._connection)
        # await cls._instance.setup()

    @classmethod
    async def close(cls):
        """연결 종료"""
        if cls._connection:
            await cls._connection.close()
```

### 5.2 상태 정의

**파일**: `backend/app/octostrator/state.py`

```python
from typing import TypedDict, List, Annotated, Literal
from langgraph.graph import add_messages
from langchain_core.messages import BaseMessage, AIMessage, HumanMessage
import uuid
from datetime import datetime

class TodoItem(TypedDict):
    """개별 TODO 항목"""
    id: str
    title: str
    description: str
    status: Literal["pending", "in_progress", "completed"]
    priority: Literal["low", "medium", "high"]
    created_at: str
    metadata: dict

class GraphState(TypedDict):
    """LangGraph 상태"""
    # 메시지 히스토리 (자동 누적)
    messages: Annotated[List[BaseMessage], add_messages]

    # 사용자 입력
    user_query: str

    # TODO 관리
    todos: List[TodoItem]
    current_todo_index: int

    # 제어 플래그
    requires_confirmation: bool
    needs_user_edit: bool

    # 사용자 피드백
    user_feedback: str | None

    # 세션 정보
    session_id: str
    thread_id: str

def create_initial_state(user_query: str, session_id: str, thread_id: str) -> GraphState:
    """초기 상태 생성"""
    return GraphState(
        messages=[HumanMessage(content=user_query)],
        user_query=user_query,
        todos=[],
        current_todo_index=0,
        requires_confirmation=False,
        needs_user_edit=False,
        user_feedback=None,
        session_id=session_id,
        thread_id=thread_id
    )
```

### 5.3 노드 구현

**파일**: `backend/app/octostrator/nodes.py`

```python
from typing import Any
from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage, SystemMessage
from langgraph.types import interrupt, Command
from .state import GraphState, TodoItem
import json
import uuid
from datetime import datetime

# LLM 초기화
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

async def parse_query_node(state: GraphState) -> GraphState:
    """사용자 질의 파싱 및 의도 분석"""
    print("--- 질의 파싱 노드 ---")

    system_prompt = """당신은 사용자의 질의를 분석하여 TODO 항목을 추출하는 전문가입니다.
사용자의 요청에서 실행 가능한 작업들을 식별하고 구조화하세요."""

    messages = [
        SystemMessage(content=system_prompt),
        *state["messages"]
    ]

    response = await llm.ainvoke(messages)

    return {
        "messages": [response]
    }

async def generate_todos_node(state: GraphState) -> GraphState:
    """LLM을 사용하여 TODO 항목 생성"""
    print("--- TODO 생성 노드 ---")

    system_prompt = """사용자의 질의를 기반으로 구체적인 TODO 항목들을 생성하세요.
각 TODO는 다음 형식의 JSON 배열로 반환하세요:

[
  {
    "title": "TODO 제목",
    "description": "상세 설명",
    "priority": "low|medium|high"
  }
]

실행 가능하고 명확한 항목들로 나누세요."""

    messages = [
        SystemMessage(content=system_prompt),
        *state["messages"]
    ]

    response = await llm.ainvoke(messages)

    # LLM 응답에서 JSON 추출 (실제로는 더 견고한 파싱 필요)
    try:
        # JSON 추출 로직
        content = response.content
        if "```json" in content:
            json_str = content.split("```json")[1].split("```")[0].strip()
        else:
            json_str = content

        todo_data = json.loads(json_str)

        # TodoItem 형식으로 변환
        todos = []
        for item in todo_data:
            todos.append(TodoItem(
                id=str(uuid.uuid4()),
                title=item["title"],
                description=item.get("description", ""),
                status="pending",
                priority=item.get("priority", "medium"),
                created_at=datetime.utcnow().isoformat(),
                metadata={}
            ))

        return {
            "todos": todos,
            "messages": [AIMessage(content=f"{len(todos)}개의 TODO 항목을 생성했습니다.")],
            "requires_confirmation": len(todos) > 5  # 5개 이상이면 확인 요청
        }

    except Exception as e:
        print(f"TODO 파싱 오류: {e}")
        return {
            "messages": [AIMessage(content="TODO 생성 중 오류가 발생했습니다.")],
            "requires_confirmation": True
        }

async def validation_node(state: GraphState) -> GraphState:
    """조건부 검증 및 interrupt 발동"""
    print("--- 검증 노드 ---")

    # 조건 1: TODO가 너무 많음
    if len(state["todos"]) > 5:
        state["requires_confirmation"] = True

    # 조건 2: 높은 우선순위 항목이 있음
    high_priority_count = sum(1 for todo in state["todos"] if todo["priority"] == "high")
    if high_priority_count > 0:
        state["requires_confirmation"] = True

    # Human-in-the-Loop: interrupt 호출
    if state["requires_confirmation"]:
        print("사용자 확인이 필요합니다. interrupt() 호출...")

        # 사용자에게 현재 TODO 목록 전달
        interrupt_data = {
            "message": "생성된 TODO 목록을 확인해주세요.",
            "todos": state["todos"],
            "action_required": "approve_or_edit"
        }

        # interrupt 호출 - 실행 중단 및 사용자 입력 대기
        user_response = interrupt(interrupt_data)

        # user_response는 Command(resume=...)로 전달된 값
        # 예: {"action": "edit", "todos": [...수정된 TODO들...]}

        if user_response.get("action") == "edit":
            return {
                "todos": user_response["todos"],
                "user_feedback": "사용자가 TODO를 수정했습니다.",
                "requires_confirmation": False
            }
        elif user_response.get("action") == "approve":
            return {
                "user_feedback": "사용자가 TODO를 승인했습니다.",
                "requires_confirmation": False
            }
        else:
            # 거부된 경우
            return {
                "todos": [],
                "user_feedback": "사용자가 TODO를 거부했습니다.",
                "requires_confirmation": False
            }

    return {
        "requires_confirmation": False
    }

async def save_todos_node(state: GraphState) -> GraphState:
    """TODO를 데이터베이스에 저장 (옵션)"""
    print("--- TODO 저장 노드 ---")

    # 실제 구현에서는 DB에 저장
    # await save_todos_to_db(state["session_id"], state["todos"])

    return {
        "messages": [AIMessage(content=f"{len(state['todos'])}개의 TODO가 저장되었습니다.")]
    }

def should_validate(state: GraphState) -> bool:
    """검증 필요 여부 판단"""
    return state.get("requires_confirmation", False) or len(state["todos"]) > 0
```

### 5.4 그래프 구성

**파일**: `backend/app/octostrator/graph.py`

```python
from langgraph.graph import StateGraph, END
from .state import GraphState
from .nodes import (
    parse_query_node,
    generate_todos_node,
    validation_node,
    save_todos_node,
    should_validate
)
from .checkpointer import CheckpointerManager

async def create_todo_graph():
    """TODO 관리 그래프 생성"""

    # 체크포인터 초기화
    checkpointer = await CheckpointerManager.get_checkpointer()

    # 그래프 빌더
    builder = StateGraph(GraphState)

    # 노드 추가
    builder.add_node("parse_query", parse_query_node)
    builder.add_node("generate_todos", generate_todos_node)
    builder.add_node("validate", validation_node)
    builder.add_node("save_todos", save_todos_node)

    # 엣지 정의
    builder.set_entry_point("parse_query")
    builder.add_edge("parse_query", "generate_todos")
    builder.add_edge("generate_todos", "validate")

    # 조건부 엣지
    builder.add_conditional_edges(
        "validate",
        lambda state: "save" if not state.get("requires_confirmation") else "save",
        {
            "save": "save_todos"
        }
    )

    builder.add_edge("save_todos", END)

    # 체크포인터와 함께 컴파일
    graph = builder.compile(checkpointer=checkpointer)

    return graph

# 그래프 인스턴스 (싱글톤)
_graph_instance = None

async def get_graph():
    """그래프 인스턴스 반환"""
    global _graph_instance
    if _graph_instance is None:
        _graph_instance = await create_todo_graph()
    return _graph_instance
```

---

## 6. Human-in-the-Loop 구현

### 6.1 Interrupt 처리 플로우

```mermaid
sequenceDiagram
    participant API as FastAPI Endpoint
    participant G as LangGraph
    participant CP as Checkpointer
    participant Client as Frontend

    Client->>API: POST /sessions/{id}/invoke
    API->>G: graph.ainvoke(input, config)
    G->>G: 노드 실행

    alt interrupt() 호출됨
        G->>CP: 현재 상태 저장
        G-->>API: __interrupt__ 이벤트 반환
        API-->>Client: {status: "interrupted", data: {...}}

        Client->>Client: 사용자 TODO 수정
        Client->>API: POST /sessions/{id}/resume
        API->>G: graph.ainvoke(Command(resume=수정데이터), config)
        G->>CP: 상태 복구
        G->>G: 중단된 노드 재실행
        G-->>API: 최종 결과
    else 정상 완료
        G-->>API: 최종 상태
    end

    API-->>Client: {status: "completed", data: {...}}
```

### 6.2 Thread Configuration

```python
from langgraph.checkpoint.base import CheckpointMetadata
from typing import Dict, Any

def create_thread_config(session_id: str, thread_id: str) -> Dict[str, Any]:
    """스레드 설정 생성"""
    return {
        "configurable": {
            "thread_id": thread_id,
            "checkpoint_ns": "",  # 기본 네임스페이스
            "checkpoint_id": None  # 최신 체크포인트 사용
        },
        "metadata": {
            "session_id": session_id,
            "created_at": datetime.utcnow().isoformat()
        }
    }

def create_resume_config(session_id: str, thread_id: str, checkpoint_id: str = None) -> Dict[str, Any]:
    """재개용 설정 생성"""
    config = create_thread_config(session_id, thread_id)
    if checkpoint_id:
        config["configurable"]["checkpoint_id"] = checkpoint_id
    return config
```

### 6.3 Interrupt 감지 및 처리

```python
from langgraph.types import Command, Interrupt
from typing import AsyncIterator

async def invoke_with_interrupt_handling(
    graph,
    input_data: GraphState,
    config: dict
) -> dict:
    """Interrupt를 처리하는 그래프 실행"""

    try:
        # 스트리밍 방식으로 실행
        events = []
        async for event in graph.astream(input_data, config, stream_mode="updates"):
            events.append(event)

            # Interrupt 이벤트 감지
            if "__interrupt__" in event:
                interrupt_info = event["__interrupt__"]
                return {
                    "status": "interrupted",
                    "interrupt_data": interrupt_info,
                    "events": events,
                    "thread_id": config["configurable"]["thread_id"]
                }

        # 정상 완료
        return {
            "status": "completed",
            "events": events,
            "final_state": await graph.aget_state(config)
        }

    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

async def resume_after_interrupt(
    graph,
    resume_data: Any,
    config: dict
) -> dict:
    """Interrupt 이후 재개"""

    # Command 객체로 재개
    command = Command(resume=resume_data)

    return await invoke_with_interrupt_handling(graph, command, config)
```

---

## 7. FastAPI 백엔드 구현

### 7.1 세션 관리 API

**파일**: `backend/app/api/sessions.py`

```python
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
import uuid

from ..models.session import Session as SessionModel
from ..schema.session import SessionCreate, SessionResponse
from ..db.session import get_db

router = APIRouter(prefix="/sessions", tags=["sessions"])

@router.post("/", response_model=SessionResponse)
async def create_session(
    session_data: SessionCreate,
    db: AsyncSession = Depends(get_db)
):
    """새 세션 생성"""
    thread_id = f"thread_{uuid.uuid4().hex}"

    new_session = SessionModel(
        user_id=session_data.user_id,
        thread_id=thread_id,
        status="active"
    )

    db.add(new_session)
    await db.commit()
    await db.refresh(new_session)

    return new_session

@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """세션 조회"""
    result = await db.execute(
        select(SessionModel).where(SessionModel.id == session_id)
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return session

@router.get("/", response_model=List[SessionResponse])
async def list_sessions(
    user_id: str = None,
    db: AsyncSession = Depends(get_db)
):
    """세션 목록 조회"""
    query = select(SessionModel)
    if user_id:
        query = query.where(SessionModel.user_id == user_id)

    result = await db.execute(query.order_by(SessionModel.created_at.desc()))
    sessions = result.scalars().all()

    return sessions

@router.delete("/{session_id}")
async def delete_session(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """세션 삭제"""
    result = await db.execute(
        select(SessionModel).where(SessionModel.id == session_id)
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    await db.delete(session)
    await db.commit()

    return {"message": "Session deleted successfully"}
```

### 7.2 TODO 관리 API

**파일**: `backend/app/api/todos.py`

```python
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any, Dict

from ..octostrator.graph import get_graph
from ..octostrator.state import create_initial_state
from ..schema.todo import (
    TodoInvokeRequest,
    TodoResumeRequest,
    TodoResponse,
    TodoInterruptResponse
)
from ..db.session import get_db
from ..models.session import Session as SessionModel

router = APIRouter(prefix="/todos", tags=["todos"])

@router.post("/invoke", response_model=TodoResponse)
async def invoke_todo_generation(
    request: TodoInvokeRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    사용자 질의를 받아 TODO 생성 프로세스 시작
    Interrupt 발생 시 중단 상태 반환
    """
    from ..octostrator.graph import invoke_with_interrupt_handling, create_thread_config

    # 세션 조회
    session = await db.get(SessionModel, request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # 그래프 가져오기
    graph = await get_graph()

    # 초기 상태 생성
    initial_state = create_initial_state(
        user_query=request.query,
        session_id=str(session.id),
        thread_id=session.thread_id
    )

    # 스레드 설정
    config = create_thread_config(str(session.id), session.thread_id)

    # 그래프 실행
    result = await invoke_with_interrupt_handling(graph, initial_state, config)

    if result["status"] == "interrupted":
        # Interrupt 발생
        return TodoInterruptResponse(
            status="interrupted",
            session_id=str(session.id),
            thread_id=session.thread_id,
            interrupt_data=result["interrupt_data"],
            message="사용자 확인이 필요합니다."
        )

    elif result["status"] == "completed":
        # 정상 완료
        final_state = result["final_state"].values
        return TodoResponse(
            status="completed",
            session_id=str(session.id),
            thread_id=session.thread_id,
            todos=final_state.get("todos", []),
            message="TODO 생성이 완료되었습니다."
        )

    else:
        # 오류
        raise HTTPException(status_code=500, detail=result.get("error"))

@router.post("/resume", response_model=TodoResponse)
async def resume_todo_generation(
    request: TodoResumeRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Interrupt 이후 사용자 입력으로 재개
    """
    from ..octostrator.graph import resume_after_interrupt, create_resume_config

    # 세션 조회
    session = await db.get(SessionModel, request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # 그래프 가져오기
    graph = await get_graph()

    # 재개 설정
    config = create_resume_config(str(session.id), session.thread_id)

    # 재개 데이터 (사용자가 수정한 TODO 등)
    resume_data = request.resume_data

    # 그래프 재개
    result = await resume_after_interrupt(graph, resume_data, config)

    if result["status"] == "interrupted":
        # 다시 중단됨 (드물지만 가능)
        return TodoInterruptResponse(
            status="interrupted",
            session_id=str(session.id),
            thread_id=session.thread_id,
            interrupt_data=result["interrupt_data"],
            message="추가 확인이 필요합니다."
        )

    elif result["status"] == "completed":
        final_state = result["final_state"].values
        return TodoResponse(
            status="completed",
            session_id=str(session.id),
            thread_id=session.thread_id,
            todos=final_state.get("todos", []),
            message="TODO 처리가 완료되었습니다."
        )

    else:
        raise HTTPException(status_code=500, detail=result.get("error"))

@router.get("/state/{session_id}")
async def get_current_state(
    session_id: str,
    db: AsyncSession = Depends(get_db)
):
    """현재 그래프 상태 조회"""
    session = await db.get(SessionModel, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    graph = await get_graph()
    config = {"configurable": {"thread_id": session.thread_id}}

    state = await graph.aget_state(config)

    return {
        "session_id": session_id,
        "thread_id": session.thread_id,
        "state": state.values if state else None,
        "next_node": state.next if state else None
    }
```

### 7.3 WebSocket 실시간 통신 (옵션)

**파일**: `backend/app/api/websocket.py`

```python
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict
import json

router = APIRouter()

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, session_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[session_id] = websocket

    def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]

    async def send_message(self, session_id: str, message: dict):
        if session_id in self.active_connections:
            await self.active_connections[session_id].send_json(message)

manager = ConnectionManager()

@router.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await manager.connect(session_id, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # 클라이언트로부터 메시지 수신 처리
            message = json.loads(data)

            # 예: interrupt 재개 요청
            if message.get("type") == "resume":
                # 재개 로직 호출
                pass

    except WebSocketDisconnect:
        manager.disconnect(session_id)
```

### 7.4 메인 앱 설정

**파일**: `backend/app/main.py`

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from .api import sessions, todos, websocket
from .octostrator.checkpointer import CheckpointerManager
from .db.session import init_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    """앱 생명주기 관리"""
    # 시작 시
    await init_db()  # DB 테이블 생성
    await CheckpointerManager.initialize()  # 체크포인터 초기화

    yield

    # 종료 시
    await CheckpointerManager.close()

app = FastAPI(
    title="Octostrator TODO Management API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js 개발 서버
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(sessions.router, prefix="/api")
app.include_router(todos.router, prefix="/api")
app.include_router(websocket.router, prefix="/api")

@app.get("/")
async def root():
    return {"message": "Octostrator API v1.0"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
```

---

## 8. Frontend 구현

### 8.1 API 클라이언트

**파일**: `frontend/lib/api.ts`

```typescript
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';

export interface TodoItem {
  id: string;
  title: string;
  description: string;
  status: 'pending' | 'in_progress' | 'completed';
  priority: 'low' | 'medium' | 'high';
  created_at: string;
}

export interface Session {
  id: string;
  user_id: string;
  thread_id: string;
  status: string;
  created_at: string;
}

export interface TodoInvokeResponse {
  status: 'completed' | 'interrupted';
  session_id: string;
  thread_id: string;
  todos?: TodoItem[];
  interrupt_data?: any;
  message: string;
}

export class APIClient {
  // 세션 생성
  async createSession(userId: string): Promise<Session> {
    const response = await fetch(`${API_BASE_URL}/sessions/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: userId })
    });
    return response.json();
  }

  // TODO 생성 시작
  async invokeTodoGeneration(sessionId: string, query: string): Promise<TodoInvokeResponse> {
    const response = await fetch(`${API_BASE_URL}/todos/invoke`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId, query })
    });
    return response.json();
  }

  // Interrupt 이후 재개
  async resumeTodoGeneration(
    sessionId: string,
    resumeData: any
  ): Promise<TodoInvokeResponse> {
    const response = await fetch(`${API_BASE_URL}/todos/resume`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId, resume_data: resumeData })
    });
    return response.json();
  }

  // 현재 상태 조회
  async getCurrentState(sessionId: string): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/todos/state/${sessionId}`);
    return response.json();
  }

  // 세션 목록
  async listSessions(userId?: string): Promise<Session[]> {
    const url = userId
      ? `${API_BASE_URL}/sessions/?user_id=${userId}`
      : `${API_BASE_URL}/sessions/`;
    const response = await fetch(url);
    return response.json();
  }
}

export const apiClient = new APIClient();
```

### 8.2 TODO 관리 페이지

**파일**: `frontend/app/todos/page.tsx`

```typescript
'use client';

import { useState } from 'react';
import { apiClient, TodoItem, TodoInvokeResponse } from '@/lib/api';
import TodoList from '@/components/TodoList';
import InterruptModal from '@/components/InterruptModal';

export default function TodoPage() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [query, setQuery] = useState('');
  const [todos, setTodos] = useState<TodoItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [interruptData, setInterruptData] = useState<any>(null);
  const [showInterruptModal, setShowInterruptModal] = useState(false);

  // 새 세션 시작
  const startNewSession = async () => {
    const session = await apiClient.createSession('user123');
    setSessionId(session.id);
  };

  // TODO 생성 시작
  const handleSubmitQuery = async () => {
    if (!sessionId) {
      await startNewSession();
    }

    setIsLoading(true);
    try {
      const response = await apiClient.invokeTodoGeneration(sessionId!, query);

      if (response.status === 'interrupted') {
        // Interrupt 발생 - 모달 표시
        setInterruptData(response.interrupt_data);
        setShowInterruptModal(true);

        // interrupt_data에 포함된 TODO 미리보기
        if (response.interrupt_data?.todos) {
          setTodos(response.interrupt_data.todos);
        }
      } else if (response.status === 'completed') {
        // 정상 완료
        setTodos(response.todos || []);
      }
    } catch (error) {
      console.error('Error:', error);
    } finally {
      setIsLoading(false);
    }
  };

  // Interrupt 승인
  const handleApprove = async () => {
    setIsLoading(true);
    try {
      const response = await apiClient.resumeTodoGeneration(sessionId!, {
        action: 'approve'
      });

      if (response.status === 'completed') {
        setTodos(response.todos || []);
        setShowInterruptModal(false);
      }
    } catch (error) {
      console.error('Error:', error);
    } finally {
      setIsLoading(false);
    }
  };

  // Interrupt 수정
  const handleEdit = async (editedTodos: TodoItem[]) => {
    setIsLoading(true);
    try {
      const response = await apiClient.resumeTodoGeneration(sessionId!, {
        action: 'edit',
        todos: editedTodos
      });

      if (response.status === 'completed') {
        setTodos(response.todos || []);
        setShowInterruptModal(false);
      }
    } catch (error) {
      console.error('Error:', error);
    } finally {
      setIsLoading(false);
    }
  };

  // Interrupt 거부
  const handleReject = async () => {
    setIsLoading(true);
    try {
      await apiClient.resumeTodoGeneration(sessionId!, {
        action: 'reject'
      });

      setTodos([]);
      setShowInterruptModal(false);
    } catch (error) {
      console.error('Error:', error);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="container mx-auto p-8">
      <h1 className="text-3xl font-bold mb-8">TODO 관리 시스템</h1>

      {/* 질의 입력 */}
      <div className="mb-8">
        <textarea
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="무엇을 도와드릴까요? (예: 신규 프로젝트 준비하기)"
          className="w-full p-4 border rounded-lg"
          rows={4}
        />
        <button
          onClick={handleSubmitQuery}
          disabled={isLoading || !query}
          className="mt-4 px-6 py-2 bg-blue-600 text-white rounded-lg disabled:bg-gray-400"
        >
          {isLoading ? '처리 중...' : 'TODO 생성'}
        </button>
      </div>

      {/* TODO 목록 */}
      <TodoList todos={todos} onUpdate={setTodos} />

      {/* Interrupt 모달 */}
      {showInterruptModal && (
        <InterruptModal
          todos={todos}
          interruptData={interruptData}
          onApprove={handleApprove}
          onEdit={handleEdit}
          onReject={handleReject}
          isLoading={isLoading}
        />
      )}
    </div>
  );
}
```

### 8.3 Interrupt 모달 컴포넌트

**파일**: `frontend/components/InterruptModal.tsx`

```typescript
'use client';

import { useState } from 'react';
import { TodoItem } from '@/lib/api';
import TodoEditor from './TodoEditor';

interface InterruptModalProps {
  todos: TodoItem[];
  interruptData: any;
  onApprove: () => void;
  onEdit: (todos: TodoItem[]) => void;
  onReject: () => void;
  isLoading: boolean;
}

export default function InterruptModal({
  todos,
  interruptData,
  onApprove,
  onEdit,
  onReject,
  isLoading
}: InterruptModalProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [editedTodos, setEditedTodos] = useState(todos);

  const handleSaveEdit = () => {
    onEdit(editedTodos);
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-8 max-w-4xl w-full max-h-[90vh] overflow-y-auto">
        <h2 className="text-2xl font-bold mb-4">사용자 확인 필요</h2>

        <p className="mb-4 text-gray-700">
          {interruptData?.message || '생성된 TODO 목록을 확인해주세요.'}
        </p>

        {/* TODO 미리보기/편집 */}
        {isEditing ? (
          <TodoEditor todos={editedTodos} onChange={setEditedTodos} />
        ) : (
          <div className="mb-6">
            <h3 className="font-semibold mb-2">생성된 TODO ({todos.length}개):</h3>
            <ul className="space-y-2">
              {todos.map((todo) => (
                <li key={todo.id} className="border p-3 rounded">
                  <div className="font-medium">{todo.title}</div>
                  <div className="text-sm text-gray-600">{todo.description}</div>
                  <div className="text-xs text-gray-500 mt-1">
                    우선순위: {todo.priority}
                  </div>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* 액션 버튼 */}
        <div className="flex gap-4">
          {isEditing ? (
            <>
              <button
                onClick={handleSaveEdit}
                disabled={isLoading}
                className="px-6 py-2 bg-blue-600 text-white rounded-lg disabled:bg-gray-400"
              >
                {isLoading ? '저장 중...' : '저장하고 계속'}
              </button>
              <button
                onClick={() => setIsEditing(false)}
                disabled={isLoading}
                className="px-6 py-2 bg-gray-300 rounded-lg"
              >
                취소
              </button>
            </>
          ) : (
            <>
              <button
                onClick={onApprove}
                disabled={isLoading}
                className="px-6 py-2 bg-green-600 text-white rounded-lg disabled:bg-gray-400"
              >
                {isLoading ? '처리 중...' : '승인'}
              </button>
              <button
                onClick={() => setIsEditing(true)}
                disabled={isLoading}
                className="px-6 py-2 bg-blue-600 text-white rounded-lg disabled:bg-gray-400"
              >
                수정
              </button>
              <button
                onClick={onReject}
                disabled={isLoading}
                className="px-6 py-2 bg-red-600 text-white rounded-lg disabled:bg-gray-400"
              >
                거부
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
```

---

## 9. 구현 순서

### Phase 1: 기반 구축 (1-2일)

1. **프로젝트 구조 생성**
   ```bash
   mkdir -p backend/app/{api,octostrator,db,schema,models}
   mkdir -p frontend/{app,components,lib}
   mkdir -p data
   ```

2. **의존성 설치**
   ```bash
   # Backend
   pip install fastapi uvicorn sqlalchemy asyncpg psycopg langgraph langgraph-checkpoint-postgres langchain-openai python-dotenv

   # Frontend
   npx create-next-app@latest frontend --typescript --tailwind --app
   ```

3. **환경 변수 설정**
   ```env
   # .env
   DATABASE_URL=postgresql://user:password@localhost:5432/octostrator
   OPENAI_API_KEY=sk-...
   ```

4. **데이터베이스 초기화**
   - PostgreSQL 설치 및 실행
   - 테이블 생성 스크립트 실행

### Phase 2: LangGraph 핵심 구현 (2-3일)

1. **체크포인터 설정** (`checkpointer.py`)
2. **상태 정의** (`state.py`)
3. **기본 노드 구현** (`nodes.py`)
   - parse_query_node
   - generate_todos_node
   - save_todos_node
4. **그래프 구성** (`graph.py`)
5. **기본 동작 테스트** (CLI 스크립트)

### Phase 3: Human-in-the-Loop 구현 (2-3일)

1. **Interrupt 노드 추가** (`validation_node`)
2. **Interrupt 처리 로직** (`invoke_with_interrupt_handling`)
3. **재개 로직** (`resume_after_interrupt`)
4. **조건부 중단 테스트**

### Phase 4: FastAPI 백엔드 (2-3일)

1. **SQLAlchemy 모델** (`models/`)
2. **Pydantic 스키마** (`schema/`)
3. **데이터베이스 세션** (`db/session.py`)
4. **API 엔드포인트**
   - sessions.py
   - todos.py
5. **메인 앱** (`main.py`)

### Phase 5: Frontend 구현 (3-4일)

1. **API 클라이언트** (`lib/api.ts`)
2. **기본 컴포넌트**
   - TodoList
   - TodoEditor
3. **메인 페이지** (`app/todos/page.tsx`)
4. **Interrupt 모달** (`InterruptModal.tsx`)
5. **WebSocket 통합** (옵션)

### Phase 6: 통합 테스트 및 최적화 (2-3일)

1. **E2E 테스트**
2. **성능 최적화**
3. **오류 처리 개선**
4. **문서화**

**총 예상 기간**: 12-18일

---

## 10. 테스트 전략

### 10.1 단위 테스트

**파일**: `backend/tests/test_nodes.py`

```python
import pytest
from app.octostrator.nodes import parse_query_node, generate_todos_node
from app.octostrator.state import create_initial_state

@pytest.mark.asyncio
async def test_parse_query_node():
    """질의 파싱 노드 테스트"""
    state = create_initial_state(
        user_query="프로젝트 준비하기",
        session_id="test-session",
        thread_id="test-thread"
    )

    result = await parse_query_node(state)

    assert "messages" in result
    assert len(result["messages"]) > 0

@pytest.mark.asyncio
async def test_generate_todos_node():
    """TODO 생성 노드 테스트"""
    state = create_initial_state(
        user_query="회의 준비: 자료 만들기, 발표 연습하기",
        session_id="test-session",
        thread_id="test-thread"
    )

    # 먼저 파싱
    state = await parse_query_node(state)
    # TODO 생성
    result = await generate_todos_node(state)

    assert "todos" in result
    assert len(result["todos"]) >= 2  # 최소 2개 TODO
    assert result["todos"][0]["title"] is not None
```

### 10.2 통합 테스트

**파일**: `backend/tests/test_graph_integration.py`

```python
import pytest
from app.octostrator.graph import create_todo_graph
from app.octostrator.state import create_initial_state

@pytest.mark.asyncio
async def test_full_graph_execution():
    """전체 그래프 실행 테스트"""
    graph = await create_todo_graph()

    initial_state = create_initial_state(
        user_query="신규 서비스 런칭 준비",
        session_id="test-session",
        thread_id="test-thread"
    )

    config = {
        "configurable": {
            "thread_id": "test-thread"
        }
    }

    # 실행
    result = await graph.ainvoke(initial_state, config)

    # 검증
    assert "todos" in result
    assert len(result["todos"]) > 0
    assert result["todos"][0]["id"] is not None

@pytest.mark.asyncio
async def test_interrupt_and_resume():
    """Interrupt 및 재개 테스트"""
    from langgraph.types import Command

    graph = await create_todo_graph()

    # 많은 TODO 생성 -> interrupt 트리거
    initial_state = create_initial_state(
        user_query="10가지 작업: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10",
        session_id="test-session",
        thread_id="test-thread-interrupt"
    )

    config = {
        "configurable": {
            "thread_id": "test-thread-interrupt"
        }
    }

    # 첫 실행 - interrupt 발생 예상
    events = []
    interrupted = False
    async for event in graph.astream(initial_state, config, stream_mode="updates"):
        events.append(event)
        if "__interrupt__" in event:
            interrupted = True
            break

    assert interrupted, "Interrupt가 발생해야 합니다"

    # 재개
    resume_data = {"action": "approve"}
    command = Command(resume=resume_data)

    final_result = await graph.ainvoke(command, config)

    assert "todos" in final_result
    assert len(final_result["todos"]) > 0
```

### 10.3 API 테스트

**파일**: `backend/tests/test_api.py`

```python
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_create_session():
    """세션 생성 API 테스트"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/sessions/",
            json={"user_id": "test-user"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == "test-user"
        assert "thread_id" in data

@pytest.mark.asyncio
async def test_invoke_todo_generation():
    """TODO 생성 API 테스트"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # 세션 생성
        session_response = await client.post(
            "/api/sessions/",
            json={"user_id": "test-user"}
        )
        session_id = session_response.json()["id"]

        # TODO 생성 시작
        invoke_response = await client.post(
            "/api/todos/invoke",
            json={
                "session_id": session_id,
                "query": "프로젝트 준비하기"
            }
        )

        assert invoke_response.status_code == 200
        data = invoke_response.json()
        assert data["status"] in ["completed", "interrupted"]
```

### 10.4 Frontend 테스트

**파일**: `frontend/__tests__/TodoPage.test.tsx`

```typescript
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import TodoPage from '@/app/todos/page';
import { apiClient } from '@/lib/api';

jest.mock('@/lib/api');

describe('TodoPage', () => {
  it('사용자 질의 입력 및 제출', async () => {
    const mockInvoke = jest.fn().mockResolvedValue({
      status: 'completed',
      todos: [
        { id: '1', title: 'Task 1', description: '', status: 'pending', priority: 'medium', created_at: '' }
      ]
    });

    (apiClient.invokeTodoGeneration as jest.Mock) = mockInvoke;

    render(<TodoPage />);

    const textarea = screen.getByPlaceholderText(/무엇을 도와드릴까요/);
    const button = screen.getByText('TODO 생성');

    fireEvent.change(textarea, { target: { value: '테스트 작업' } });
    fireEvent.click(button);

    await waitFor(() => {
      expect(mockInvoke).toHaveBeenCalledWith(expect.any(String), '테스트 작업');
    });
  });

  it('Interrupt 발생 시 모달 표시', async () => {
    const mockInvoke = jest.fn().mockResolvedValue({
      status: 'interrupted',
      interrupt_data: {
        message: '확인 필요',
        todos: []
      }
    });

    (apiClient.invokeTodoGeneration as jest.Mock) = mockInvoke;

    render(<TodoPage />);

    // ... (테스트 로직)
  });
});
```

---

## 11. 추가 고려사항

### 11.1 보안

1. **인증/인가**
   - JWT 토큰 기반 인증
   - 세션별 접근 권한 제어

2. **입력 검증**
   - Pydantic 스키마로 입력 검증
   - SQL Injection 방지 (SQLAlchemy ORM 사용)

3. **API Rate Limiting**
   - FastAPI의 slowapi 사용

### 11.2 성능 최적화

1. **데이터베이스 인덱싱**
   - thread_id, session_id에 인덱스 생성
   - 체크포인트 조회 최적화

2. **캐싱**
   - Redis를 사용한 세션 캐싱
   - LLM 응답 캐싱 (동일 질의)

3. **비동기 처리**
   - 모든 I/O 작업 비동기화
   - 백그라운드 작업 (Celery 등)

### 11.3 모니터링

1. **로깅**
   - 구조화된 로깅 (structlog)
   - 체크포인트 상태 로깅

2. **메트릭**
   - Prometheus + Grafana
   - LangSmith 통합 (LangChain 모니터링)

3. **오류 추적**
   - Sentry 통합

### 11.4 확장성

1. **수평 확장**
   - FastAPI 인스턴스 다중화
   - PostgreSQL 읽기 복제본

2. **그래프 확장**
   - 추가 노드 (우선순위 분석, 자동 일정 생성 등)
   - Subgraph 패턴 활용

---

## 12. 참고 자료

### 공식 문서

1. **LangGraph**
   - [Human-in-the-Loop 가이드](https://langchain-ai.github.io/langgraph/how-tos/human_in_the_loop/wait-user-input/)
   - [Interrupt 함수 설명](https://blog.langchain.com/making-it-easier-to-build-human-in-the-loop-agents-with-interrupt/)
   - [Dynamic Breakpoints](https://changelog.langchain.com/announcements/langgraph-python-dynamic-breakpoints-error-tracking-in-checkpointer-and-custom-configs)

2. **Checkpointer**
   - [AsyncPostgresSaver 문서](https://pypi.org/project/langgraph-checkpoint-postgres/)
   - [Persistence 가이드](https://docs.langchain.com/oss/python/langgraph/persistence)

3. **FastAPI**
   - [FastAPI 공식 문서](https://fastapi.tiangolo.com/)
   - [WebSocket 가이드](https://fastapi.tiangolo.com/advanced/websockets/)

4. **Next.js**
   - [Next.js 공식 문서](https://nextjs.org/docs)
   - [App Router 가이드](https://nextjs.org/docs/app)

### 예제 저장소

- [LangGraph Interrupt Workflow Template](https://github.com/KirtiJha/langgraph-interrupt-workflow-template)

---

## 부록 A: 핵심 코드 스니펫

### A.1 Interrupt 패턴

```python
# 조건부 중단
def conditional_interrupt_node(state):
    if state["needs_approval"]:
        user_input = interrupt({
            "type": "approval_request",
            "data": state["pending_action"]
        })

        if user_input["approved"]:
            # 승인됨 - 계속 진행
            pass
        else:
            # 거부됨 - 다른 경로
            return {"status": "rejected"}

    return state
```

### A.2 체크포인트 상태 조회

```python
async def get_checkpoint_history(thread_id: str):
    """특정 스레드의 체크포인트 히스토리 조회"""
    checkpointer = await CheckpointerManager.get_checkpointer()

    config = {"configurable": {"thread_id": thread_id}}

    checkpoints = []
    async for checkpoint in checkpointer.alist(config):
        checkpoints.append(checkpoint)

    return checkpoints
```

### A.3 타임 트래블 (과거 상태로 복원)

```python
async def restore_to_checkpoint(thread_id: str, checkpoint_id: str):
    """특정 체크포인트로 복원"""
    graph = await get_graph()

    config = {
        "configurable": {
            "thread_id": thread_id,
            "checkpoint_id": checkpoint_id
        }
    }

    state = await graph.aget_state(config)
    return state.values
```

---

## 요약

이 계획서는 LangGraph 1.0.x를 기반으로 한 **Human-in-the-Loop TODO 관리 시스템**의 완전한 구현 가이드를 제공합니다.

**핵심 특징**:
1. ✅ 사용자 질의 기반 자동 TODO 생성
2. ✅ `interrupt()` 함수를 통한 동적 사용자 개입
3. ✅ AsyncPostgresSaver를 통한 영구 상태 저장
4. ✅ 조건부 에이전트 중단 및 재개
5. ✅ FastAPI + Next.js 풀스택 구현

**다음 단계**: Phase 1부터 순차적으로 구현을 시작하세요.
