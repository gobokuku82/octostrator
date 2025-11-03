# LangGraph 1.0 기반 챗봇 아키텍처 설계 계획서

**작성일**: 2025-11-03
**프로젝트**: Octo_worker Beta v0.02
**목적**: LangGraph Supervisor 패턴 기반 멀티 에이전트 챗봇 시스템 구축

---

## 1. 프로젝트 개요

### 1.1 목표
- LangGraph 1.0 기반의 확장 가능한 **범용 멀티 에이전트 챗봇** 시스템 구축
- Supervisor 패턴을 활용한 계층적 에이전트 구조 구현
- Human-in-the-Loop을 통한 안전하고 제어 가능한 AI 시스템 구현
- WebSocket 기반 실시간 양방향 통신 지원
- **도메인에 구애받지 않는 범용 구조**로 설계하여 점진적 기능 확장 가능

### 1.2 초기 구현 범위
- **Phase 1 목표**: 전체 아키텍처 구조 및 인프라 구축
- **기본 Agent 3종**: 검색(Search), 분석(Analysis), 문서생성(Document) - 구조만 구현
- **데이터베이스**: 연결 설정만 (초기 데이터 없음)
- **인증/권한**: 추후 구현 (현재는 제외)

### 1.2 기술 스택

#### Backend
- **Framework**: FastAPI (비동기 웹 프레임워크)
- **Python Version**: 3.12.7
- **Package Manager**: uv

#### Frontend
- **Framework**: Create React App
- **Communication**: WebSocket (실시간 양방향 통신)

#### AI/LLM
**현재 설치된 버전 (0.x):**
- langchain==0.3.27
- langchain-core==0.3.75
- langchain-openai==0.3.32
- langgraph==0.6.8
- langgraph-checkpoint==2.1.2

**업그레이드 대상 (1.0 - 2025년 10월 17-29일 출시):**
- **LangChain 1.0.3** (메인 패키지)
- **langchain-core 1.0.2** (핵심 추상화)
- **langchain-openai 1.0.1** (OpenAI 통합)
- **langchain-community 0.4.1** (커뮤니티 통합, 아직 1.0 미출시)
- **LangGraph 1.0.2** (에이전트 오케스트레이션)
- **langgraph-checkpoint 3.0.0** (체크포인터 - Major 업데이트)
- **langgraph-checkpoint-postgres 3.0.0** (추정)

**호환성 및 주요 변경사항**:
- ✅ LangChain 1.0과 LangGraph 1.0은 **완전 호환** (동시 출시)
- ✅ LangChain agents가 LangGraph 위에 구축되어 **seamless 통합**
- ⚠️ langgraph.prebuilt 모듈 deprecated → langchain.agents로 이동
- ✅ 완전한 하위 호환성 보장 (2.0까지 breaking changes 없음)
- ✅ Durable state 및 HITL 기능 강화
- ⚠️ Checkpointer 2.x → 3.0 (Major 업데이트)

#### Database
**초기 단계: 연결 설정만, 데이터 없음**

- **PostgreSQL**:
  - Checkpointer (AsyncPostgresSaver) - Thread 기반 대화 이력
  - 세션 메타데이터 관리
- **FAISS**: Vector DB (향후 RAG 구현용, 현재는 연결만)
- **MongoDB**: 로그, 분석 데이터 저장용 (향후 구현, 현재는 연결만)

#### Checkpointer
- **Library**: langgraph-checkpoint-postgres 2.0.25
- **Class**: AsyncPostgresSaver
- **Features**:
  - 비동기 체크포인트 저장
  - Thread 기반 대화 이력 관리
  - Human-in-the-loop 지원

---

## 2. LangGraph 아키텍처 설계

### 2.1 계층 구조

```
┌─────────────────────────────────────────────────────────────┐
│                     Main Graph (Supervisor)                  │
│  - Human-in-the-Loop (Level 1)                              │
│  - Thread ID 기반 세션 관리                                  │
│  - AsyncPostgresSaver Checkpointer                          │
└────────────┬────────────────────────────────────────────────┘
             │
             ├──> Search Agent (검색 에이전트)
             │    ├─ Human-in-the-Loop (Level 2)
             │    ├─ Vector Search Sub_Agent (Sub-SubGraph)
             │    │  ├─ HITL (Level 3)
             │    │  └─ FAISS Search Tool
             │    ├─ Web Search Sub_Agent (Sub-SubGraph)
             │    │  └─ Web API Tool
             │    └─ Database Search Sub_Agent (Sub-SubGraph)
             │       └─ PostgreSQL/MongoDB Query Tool
             │
             ├──> Analysis Agent (분석 에이전트)
             │    ├─ Human-in-the-Loop (Level 2)
             │    ├─ Data Analysis Sub_Agent (Sub-SubGraph)
             │    │  └─ Analysis Tool
             │    └─ Insight Generation Sub_Agent (Sub-SubGraph)
             │       └─ LLM Chain Tool
             │
             └──> Document Agent (문서 생성 에이전트)
                  ├─ Human-in-the-Loop (Level 2)
                  ├─ Content Generation Sub_Agent (Sub-SubGraph)
                  │  └─ LLM Generation Tool
                  └─ Formatting Sub_Agent (Sub-SubGraph)
                     └─ Document Formatter Tool
```

### 2.2 초기 구현 Agent 상세

#### Search Agent (검색 에이전트)
**목적**: 다양한 소스에서 정보 검색

**Sub_Agents** (초기 구조만):
1. **Vector Search Sub_Agent**: FAISS 벡터 검색 (향후 RAG 구현)
2. **Web Search Sub_Agent**: 웹 검색 (향후 구현)
3. **Database Search Sub_Agent**: DB 쿼리 (구조만)

**Tools**:
- FAISS similarity search (연결만)
- PostgreSQL query executor (연결만)
- MongoDB query executor (연결만)

#### Analysis Agent (분석 에이전트)
**목적**: 데이터 분석 및 인사이트 생성

**Sub_Agents** (초기 구조만):
1. **Data Analysis Sub_Agent**: 데이터 처리 및 분석
2. **Insight Generation Sub_Agent**: LLM 기반 인사이트 추출

**Tools**:
- Data processing tool (기본 구조)
- LLM chain tool (OpenAI API)

#### Document Agent (문서 생성 에이전트)
**목적**: 다양한 형식의 문서 생성

**Sub_Agents** (초기 구조만):
1. **Content Generation Sub_Agent**: LLM 기반 콘텐츠 생성
2. **Formatting Sub_Agent**: 문서 포맷팅

**Tools**:
- LLM generation tool (OpenAI API)
- Document formatter (기본 텍스트 포맷)

> **Note**: 모든 Agent/Sub_Agent는 초기 단계에서 구조만 구현하며, 실제 기능은 점진적으로 추가됩니다.

### 2.3 Graph 레벨별 역할

#### Level 1: Main Graph (Supervisor)
- **역할**: 최상위 의사결정 및 라우팅
- **패턴**: Supervisor Pattern
- **기능**:
  - 사용자 요청 분석
  - 적절한 Agent 선택 및 위임
  - 전체 워크플로우 조율
  - 최종 응답 생성
- **State Schema**:
  ```python
  class SupervisorState(TypedDict):
      messages: Annotated[Sequence[BaseMessage], add_messages]
      next: str  # 다음 실행할 agent
      thread_id: str
      user_id: str
      context: Dict[str, Any]
      final_response: Optional[str]
  ```

#### Level 2: Agent (SubGraph)
- **역할**: 특정 도메인/기능 담당
- **패턴**: Specialized SubGraph
- **기능**:
  - 도메인별 작업 처리
  - Sub_Agent 조율
  - 결과 취합 및 반환
- **State Schema**:
  ```python
  class AgentState(TypedDict):
      messages: Annotated[Sequence[BaseMessage], add_messages]
      task: str
      sub_results: List[Dict[str, Any]]
      agent_name: str
  ```

#### Level 3: Sub_Agent (Sub-SubGraph)
- **역할**: 세부 작업 실행
- **패턴**: Task-Specific SubGraph
- **기능**:
  - 특정 작업 실행
  - Tool 호출 및 결과 처리
  - 에러 핸들링
- **State Schema**:
  ```python
  class SubAgentState(TypedDict):
      messages: Annotated[Sequence[BaseMessage], add_messages]
      task: str
      tool_calls: List[ToolCall]
      result: Optional[Dict[str, Any]]
  ```

#### Tools
- **역할**: 실제 액션 수행
- **특징**: 모든 Graph 레벨에서 사용 가능
- **예시**:
  - 데이터베이스 조회
  - API 호출
  - 문서 검색 (RAG)
  - 계산/분석

---

## 3. Registry 패턴 설계

### 3.1 싱글톤 레지스트리 아키텍처

```python
# registry/base_registry.py
from typing import Dict, Type, Callable, Optional
from abc import ABC, abstractmethod
import threading

class BaseRegistry(ABC):
    """싱글톤 레지스트리 베이스 클래스"""
    _instances: Dict[Type, 'BaseRegistry'] = {}
    _lock = threading.Lock()

    def __new__(cls):
        if cls not in cls._instances:
            with cls._lock:
                if cls not in cls._instances:
                    cls._instances[cls] = super().__new__(cls)
        return cls._instances[cls]

    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._registry: Dict[str, Any] = {}
            self._initialized = True

    @abstractmethod
    def register(self, name: str, item: Any) -> None:
        """아이템 등록"""
        pass

    @abstractmethod
    def get(self, name: str) -> Optional[Any]:
        """아이템 조회"""
        pass
```

### 3.2 Agent Registry

```python
# registry/agent_registry.py
from typing import Callable, Optional
from langchain_core.runnables import Runnable

class AgentRegistry(BaseRegistry):
    """Agent 등록 및 관리"""

    def register(self, name: str, graph_builder: Callable[[], Runnable]) -> None:
        """
        Agent SubGraph 등록

        Args:
            name: Agent 이름 (고유 식별자)
            graph_builder: Graph를 생성하는 팩토리 함수
        """
        self._registry[name] = {
            'builder': graph_builder,
            'description': getattr(graph_builder, '__doc__', ''),
            'compiled': None  # Lazy compilation
        }

    def get(self, name: str) -> Optional[Runnable]:
        """컴파일된 Agent Graph 조회"""
        if name not in self._registry:
            return None

        # Lazy compilation
        if self._registry[name]['compiled'] is None:
            self._registry[name]['compiled'] = self._registry[name]['builder']()

        return self._registry[name]['compiled']

    def list_agents(self) -> List[Dict[str, str]]:
        """등록된 Agent 목록"""
        return [
            {'name': name, 'description': info['description']}
            for name, info in self._registry.items()
        ]
```

### 3.3 Tool Registry

```python
# registry/tool_registry.py
from typing import List, Optional
from langchain_core.tools import BaseTool

class ToolRegistry(BaseRegistry):
    """Tool 등록 및 관리"""

    def register(self, tool: BaseTool) -> None:
        """
        Tool 등록

        Args:
            tool: LangChain BaseTool 인스턴스
        """
        self._registry[tool.name] = tool

    def get(self, name: str) -> Optional[BaseTool]:
        """Tool 조회"""
        return self._registry.get(name)

    def get_tools_by_category(self, category: str) -> List[BaseTool]:
        """카테고리별 Tool 목록"""
        return [
            tool for tool in self._registry.values()
            if getattr(tool, 'category', None) == category
        ]

    def get_all_tools(self) -> List[BaseTool]:
        """전체 Tool 목록"""
        return list(self._registry.values())
```

### 3.4 Sub_Agent Registry

```python
# registry/sub_agent_registry.py

class SubAgentRegistry(BaseRegistry):
    """Sub_Agent 등록 및 관리"""

    def register(self, name: str, graph_builder: Callable[[], Runnable],
                 parent_agent: str) -> None:
        """
        Sub_Agent 등록

        Args:
            name: Sub_Agent 이름
            graph_builder: Graph 빌더 함수
            parent_agent: 부모 Agent 이름
        """
        self._registry[name] = {
            'builder': graph_builder,
            'parent': parent_agent,
            'compiled': None
        }

    def get_by_parent(self, parent_agent: str) -> List[Runnable]:
        """특정 Agent의 Sub_Agent 목록"""
        return [
            self.get(name)
            for name, info in self._registry.items()
            if info['parent'] == parent_agent
        ]
```

---

## 4. Checkpointer 설계

### 4.1 AsyncPostgresSaver 설정

```python
# checkpointer/postgres_checkpointer.py
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from contextlib import asynccontextmanager
from psycopg_pool import AsyncConnectionPool

class CheckpointerManager:
    """AsyncPostgresSaver 관리"""

    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.pool: Optional[AsyncConnectionPool] = None
        self.checkpointer: Optional[AsyncPostgresSaver] = None

    async def initialize(self):
        """Connection Pool 및 Checkpointer 초기화"""
        self.pool = AsyncConnectionPool(
            conninfo=self.connection_string,
            max_size=20,
            min_size=5
        )

        async with self.pool.connection() as conn:
            self.checkpointer = AsyncPostgresSaver(conn)
            await self.checkpointer.setup()  # 테이블 생성

    async def close(self):
        """리소스 정리"""
        if self.pool:
            await self.pool.close()

    @asynccontextmanager
    async def get_checkpointer(self):
        """요청별 checkpointer 제공"""
        async with self.pool.connection() as conn:
            checkpointer = AsyncPostgresSaver(conn)
            yield checkpointer
```

### 4.2 Thread ID 기반 스키마

```sql
-- PostgreSQL 스키마 (AsyncPostgresSaver가 자동 생성)
-- checkpoints 테이블
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

CREATE INDEX idx_checkpoints_thread_id ON checkpoints(thread_id);
CREATE INDEX idx_checkpoints_parent_id ON checkpoints(parent_checkpoint_id);

-- writes 테이블 (pending writes)
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

**Thread ID 구조 설계**:
```python
# thread_id 포맷: {user_id}_{session_id}_{timestamp}
# 예: user123_session456_1699012345

class ThreadIDManager:
    @staticmethod
    def generate_thread_id(user_id: str, session_id: Optional[str] = None) -> str:
        """Thread ID 생성"""
        import uuid
        from datetime import datetime

        session = session_id or str(uuid.uuid4())[:8]
        timestamp = int(datetime.now().timestamp())
        return f"{user_id}_{session}_{timestamp}"

    @staticmethod
    def parse_thread_id(thread_id: str) -> Dict[str, str]:
        """Thread ID 파싱"""
        parts = thread_id.split('_')
        return {
            'user_id': parts[0],
            'session_id': parts[1],
            'timestamp': parts[2]
        }
```

---

## 5. Human-in-the-Loop 설계

### 5.1 멀티 레벨 HITL 구조

```python
# hitl/interrupt_handler.py
from typing import Literal, Optional
from langgraph.types import Interrupt

InterruptLevel = Literal["supervisor", "agent", "sub_agent"]

class HITLHandler:
    """Human-in-the-Loop 핸들러"""

    @staticmethod
    def should_interrupt(
        level: InterruptLevel,
        action: str,
        confidence: float,
        threshold: float = 0.7
    ) -> bool:
        """
        중단 여부 결정

        Args:
            level: Graph 레벨
            action: 수행하려는 액션
            confidence: LLM 신뢰도
            threshold: 중단 임계값

        Returns:
            True if human review needed
        """
        # 레벨별 다른 임계값 적용
        thresholds = {
            "supervisor": 0.8,
            "agent": 0.7,
            "sub_agent": 0.6
        }

        return confidence < thresholds.get(level, threshold)

    @staticmethod
    def create_interrupt(
        message: str,
        context: Dict[str, Any],
        level: InterruptLevel
    ) -> Interrupt:
        """중단 생성"""
        return Interrupt(
            value={
                "message": message,
                "context": context,
                "level": level,
                "timestamp": datetime.now().isoformat()
            }
        )
```

### 5.2 HITL 적용 지점

#### Main Graph (Supervisor)
- 민감한 작업 승인 (예: 데이터 삭제, 외부 API 호출)
- 높은 비용 작업 확인
- 최종 응답 검토 (옵션)

#### Agent (SubGraph)
- 도메인별 중요 결정
- 복수 Sub_Agent 조율 시 사용자 선택
- 예외 상황 처리

#### Sub_Agent (Sub-SubGraph)
- 위험한 Tool 실행 전 확인
- 낮은 신뢰도 결과 검토
- 데이터 품질 검증

### 5.3 WebSocket을 통한 HITL 구현

```python
# api/websocket_hitl.py
from fastapi import WebSocket

class WebSocketHITLManager:
    """WebSocket을 통한 HITL 관리"""

    async def request_approval(
        self,
        websocket: WebSocket,
        interrupt: Interrupt,
        timeout: int = 300  # 5분
    ) -> bool:
        """
        사용자 승인 요청

        Returns:
            True if approved, False if rejected
        """
        # 클라이언트에 승인 요청 전송
        await websocket.send_json({
            "type": "approval_request",
            "data": interrupt.value,
            "timeout": timeout
        })

        # 사용자 응답 대기 (타임아웃 포함)
        try:
            response = await asyncio.wait_for(
                websocket.receive_json(),
                timeout=timeout
            )
            return response.get("approved", False)
        except asyncio.TimeoutError:
            return False  # 타임아웃 시 거부
```

---

## 6. 데이터베이스 설계

### 6.1 PostgreSQL

#### 용도
1. **Checkpointer**: AsyncPostgresSaver 전용 테이블
2. **Users**: 사용자 정보 (인증 필요 시)
3. **Sessions**: 세션 메타데이터
4. **Audit Logs**: HITL 승인/거부 이력

#### 스키마 (예시)
```sql
-- 사용자 테이블
CREATE TABLE users (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 세션 메타데이터
CREATE TABLE sessions (
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(user_id),
    thread_id TEXT UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    last_active TIMESTAMP DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'
);

-- HITL 승인 로그
CREATE TABLE hitl_approvals (
    approval_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_id TEXT NOT NULL,
    checkpoint_id TEXT NOT NULL,
    level VARCHAR(50) NOT NULL,
    action TEXT NOT NULL,
    approved BOOLEAN NOT NULL,
    user_id UUID REFERENCES users(user_id),
    approved_at TIMESTAMP DEFAULT NOW(),
    context JSONB
);
```

### 6.2 FAISS Vector DB

#### 용도
- **RAG (Retrieval-Augmented Generation)**
- 문서/지식 임베딩 저장
- 시맨틱 검색

#### 구조
```python
# vector_db/faiss_manager.py
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings

class FAISSManager:
    """FAISS Vector DB 관리"""

    def __init__(self, index_path: str):
        self.index_path = index_path
        self.embeddings = OpenAIEmbeddings()
        self.vectorstore: Optional[FAISS] = None

    async def initialize(self):
        """인덱스 로드 또는 생성"""
        try:
            self.vectorstore = FAISS.load_local(
                self.index_path,
                self.embeddings,
                allow_dangerous_deserialization=True  # 주의: 신뢰할 수 있는 소스만
            )
        except:
            # 새 인덱스 생성
            self.vectorstore = FAISS.from_texts(
                ["Initial document"],
                self.embeddings
            )

    async def add_documents(self, documents: List[Document]):
        """문서 추가"""
        await self.vectorstore.aadd_documents(documents)
        self.vectorstore.save_local(self.index_path)

    async def similarity_search(
        self,
        query: str,
        k: int = 4
    ) -> List[Document]:
        """유사도 검색"""
        return await self.vectorstore.asimilarity_search(query, k=k)
```

### 6.3 MongoDB

#### 용도 (확인 필요)
**질문**: MongoDB는 어떤 데이터를 저장할 예정인가요?

**제안 용도**:
1. **분석 데이터**: 사용자 인터랙션, 메트릭
2. **로그 저장**: 구조화되지 않은 로그
3. **캐시**: 중간 결과 캐싱
4. **문서 저장**: 원본 문서 (FAISS는 임베딩만)

#### 스키마 예시 (분석 데이터)
```javascript
// analytics 컬렉션
{
    _id: ObjectId(),
    user_id: "user123",
    thread_id: "user123_session456_1699012345",
    event_type: "message_sent",
    timestamp: ISODate(),
    metadata: {
        agent_used: "search_agent",
        response_time_ms: 1234,
        token_count: 567
    }
}

// documents 컬렉션
{
    _id: ObjectId(),
    doc_id: "doc123",
    title: "문서 제목",
    content: "원본 텍스트...",
    metadata: {
        source: "upload",
        uploaded_by: "user123",
        uploaded_at: ISODate()
    },
    faiss_indexed: true
}
```

---

## 7. FastAPI Backend 설계

### 7.1 프로젝트 구조 (개선안)

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                      # FastAPI 앱 엔트리포인트
│   ├── dependencies.py              # 의존성 주입
│   │
│   ├── config/                      # 설정 관리 (계층적)
│   │   ├── __init__.py
│   │   ├── base.py                 # 기본 설정 (BaseSettings)
│   │   ├── system.py               # 시스템 공통 설정
│   │   ├── agents/                 # Agent별 설정
│   │   │   ├── __init__.py
│   │   │   ├── search_agent.py    # Search Agent 설정
│   │   │   ├── analysis_agent.py  # Analysis Agent 설정
│   │   │   └── document_agent.py  # Document Agent 설정
│   │   ├── database.py             # DB 설정
│   │   └── llm.py                  # LLM 설정 (OpenAI API 등)
│   │
│   ├── api/                         # API 엔드포인트
│   │   ├── __init__.py
│   │   ├── websocket.py            # WebSocket 핸들러
│   │   ├── chat.py                 # REST API (필요시)
│   │   └── admin.py                # 관리 API
│   │
│   ├── core/                        # 핵심 비즈니스 로직
│   │   ├── __init__.py
│   │   ├── checkpointer.py         # Checkpointer 관리
│   │   ├── thread_manager.py       # Thread ID 관리
│   │   ├── websocket_manager.py    # WebSocket 연결 관리
│   │   ├── context/                # Context 관리
│   │   │   ├── __init__.py
│   │   │   ├── manager.py          # Context Manager
│   │   │   ├── runtime_context.py  # 런타임 Context
│   │   │   └── session_context.py  # 세션 Context
│   │   └── state/                  # State 관리 (읽기 전용)
│   │       ├── __init__.py
│   │       └── state_validator.py  # State 유효성 검사
│   │
│   ├── states/                      # Graph State 정의 (타입)
│   │   ├── __init__.py
│   │   ├── base_state.py           # 기본 State 인터페이스
│   │   ├── supervisor_state.py     # Supervisor State
│   │   ├── agent_states.py         # Agent State들
│   │   ├── sub_agent_states.py     # Sub_Agent State들
│   │   └── shared_state.py         # 공유 State 필드
│   │
│   ├── graphs/                      # Graph 정의만 (조합/오케스트레이션)
│   │   ├── __init__.py
│   │   ├── supervisor.py           # Supervisor Graph
│   │   └── builder.py              # Graph 빌더 유틸
│   │
│   ├── agents/                      # Agent 모듈 (독립적)
│   │   ├── __init__.py
│   │   ├── base/                   # 기본 Agent 추상화
│   │   │   ├── __init__.py
│   │   │   ├── base_agent.py      # BaseAgent 클래스
│   │   │   └── agent_interface.py # Agent 인터페이스
│   │   │
│   │   ├── search_agent/           # Search Agent
│   │   │   ├── __init__.py
│   │   │   ├── agent.py           # Agent Graph 정의
│   │   │   ├── config.py          # Agent 전용 설정
│   │   │   ├── prompts.py         # Agent 프롬프트
│   │   │   └── sub_agents/        # Sub_Agent들
│   │   │       ├── __init__.py
│   │   │       ├── vector_search.py
│   │   │       ├── web_search.py
│   │   │       └── db_search.py
│   │   │
│   │   ├── analysis_agent/         # Analysis Agent
│   │   │   ├── __init__.py
│   │   │   ├── agent.py
│   │   │   ├── config.py
│   │   │   ├── prompts.py
│   │   │   └── sub_agents/
│   │   │       ├── __init__.py
│   │   │       ├── data_analysis.py
│   │   │       └── insight_generation.py
│   │   │
│   │   └── document_agent/         # Document Agent
│   │       ├── __init__.py
│   │       ├── agent.py
│   │       ├── config.py
│   │       ├── prompts.py
│   │       └── sub_agents/
│   │           ├── __init__.py
│   │           ├── content_generation.py
│   │           └── formatting.py
│   │
│   ├── tools/                       # LangChain Tools
│   │   ├── __init__.py
│   │   ├── base/                   # 기본 Tool 추상화
│   │   │   ├── __init__.py
│   │   │   └── base_tool.py
│   │   ├── database/               # DB Tools
│   │   │   ├── __init__.py
│   │   │   ├── postgres_tool.py
│   │   │   ├── mongodb_tool.py
│   │   │   └── faiss_tool.py
│   │   ├── search/                 # Search Tools
│   │   │   ├── __init__.py
│   │   │   └── web_search_tool.py
│   │   └── llm/                    # LLM Tools
│   │       ├── __init__.py
│   │       └── generation_tool.py
│   │
│   ├── registry/                    # Registry 패턴
│   │   ├── __init__.py
│   │   ├── base_registry.py
│   │   ├── agent_registry.py
│   │   ├── sub_agent_registry.py
│   │   ├── tool_registry.py
│   │   └── config_registry.py      # Config Registry (새로 추가)
│   │
│   ├── db/                          # 데이터베이스
│   │   ├── __init__.py
│   │   ├── postgres.py             # PostgreSQL 연결
│   │   ├── mongodb.py              # MongoDB 연결
│   │   └── faiss_manager.py        # FAISS 관리
│   │
│   ├── models/                      # Pydantic/SQLAlchemy 모델
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── session.py
│   │   └── checkpoint.py           # Checkpoint 모델
│   │
│   ├── schemas/                     # API 스키마
│   │   ├── __init__.py
│   │   ├── websocket.py
│   │   ├── chat.py
│   │   └── context.py              # Context 스키마
│   │
│   └── utils/                       # 유틸리티
│       ├── __init__.py
│       ├── logging.py
│       └── exceptions.py
│
├── tests/                           # 테스트
│   ├── unit/                       # 단위 테스트
│   │   ├── agents/
│   │   ├── tools/
│   │   └── states/
│   ├── integration/                # 통합 테스트
│   └── e2e/                        # E2E 테스트
│
├── configs/                         # 설정 파일 (런타임)
│   ├── agents/                     # Agent별 설정 파일
│   │   ├── search_agent.yaml
│   │   ├── analysis_agent.yaml
│   │   └── document_agent.yaml
│   └── system.yaml                 # 시스템 설정
│
├── .env                             # 환경 변수 (SECRET!)
├── .env.example                     # 환경 변수 예시
├── requirements.txt
├── pyproject.toml                   # uv 설정
└── README.md
```

### 7.1.1 개선된 구조의 핵심 특징

#### 1. **Agent 독립성**
- ✅ `agents/` 디렉토리로 분리
- ✅ 각 Agent가 독립적인 모듈 (패키지)
- ✅ Agent 추가/삭제가 다른 코드에 영향 없음
- ✅ Sub_Agent도 각 Agent 내부에서 관리

#### 2. **State 관리**
- ✅ `states/` 디렉토리에서 타입 정의
- ✅ `core/state/`에서 런타임 관리
- ✅ Supervisor, Agent, Sub_Agent별 State 분리
- ✅ 공유 State 필드는 shared_state.py에서 관리

#### 3. **Context 관리**
- ✅ `core/context/`에서 전담 관리
- ✅ RuntimeContext: 실행 중 데이터 (임시)
- ✅ SessionContext: 세션 범위 데이터 (Thread 기반)
- ✅ Context Manager로 생명주기 관리

#### 4. **Config 계층 관리**
- ✅ `config/` 디렉토리에서 계층적 관리
- ✅ 시스템 공통 config (database, llm, api)
- ✅ Agent별 config (각 Agent의 파라미터)
- ✅ YAML 파일로 런타임 설정 (configs/)
- ✅ ConfigRegistry로 중앙 관리

#### 5. **관심사 분리**
- ✅ `graphs/`: Graph 조합/오케스트레이션만
- ✅ `agents/`: Agent 비즈니스 로직
- ✅ `tools/`: 재사용 가능한 도구
- ✅ `states/`: 타입 정의
- ✅ `config/`: 설정

---

### 7.1.2 주요 모듈 코드 예시

#### Config 계층 관리

**config/base.py** - 기본 설정
```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class BaseConfig(BaseSettings):
    """모든 설정의 기본 클래스"""
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

class SystemConfig(BaseSettings):
    """시스템 공통 설정"""
    # App
    app_name: str = "LangGraph Chatbot"
    app_version: str = "1.0.0"
    debug: bool = False

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # CORS
    allowed_origins: list[str] = ["http://localhost:3000"]

    model_config = SettingsConfigDict(
        env_prefix="SYSTEM_",
        env_file=".env"
    )
```

**config/agents/search_agent.py** - Agent 전용 설정
```python
from pydantic import BaseModel, Field

class SearchAgentConfig(BaseModel):
    """Search Agent 전용 설정"""
    # LLM 설정
    model_name: str = "gpt-4o-mini"
    temperature: float = 0.7
    max_tokens: int = 1000

    # Search 설정
    max_search_results: int = 5
    search_timeout: int = 30  # seconds

    # Sub_Agent 활성화
    enable_vector_search: bool = True
    enable_web_search: bool = False  # 초기에는 비활성화
    enable_db_search: bool = True

    # Retry 설정
    max_retries: int = 3
    retry_delay: float = 1.0  # seconds

    class Config:
        # configs/agents/search_agent.yaml에서 로드 가능
        json_schema_extra = {
            "example": {
                "model_name": "gpt-4o-mini",
                "temperature": 0.7,
                "max_search_results": 5
            }
        }
```

**registry/config_registry.py** - Config 중앙 관리
```python
from typing import Dict, Type, Any
from pathlib import Path
import yaml
from app.config.base import BaseConfig

class ConfigRegistry:
    """Config 중앙 관리 Registry (싱글톤)"""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._configs: Dict[str, Any] = {}
            cls._instance._initialized = False
        return cls._instance

    def register(self, name: str, config: BaseConfig):
        """설정 등록"""
        self._configs[name] = config

    def get(self, name: str) -> BaseConfig:
        """설정 조회"""
        return self._configs.get(name)

    def load_from_yaml(self, config_path: Path):
        """YAML 파일에서 설정 로드"""
        with open(config_path) as f:
            return yaml.safe_load(f)

    def merge_configs(self, base: BaseConfig, override: dict) -> BaseConfig:
        """설정 병합 (YAML 오버라이드)"""
        data = base.model_dump()
        data.update(override)
        return base.__class__(**data)
```

#### State 관리

**states/base_state.py** - 기본 State
```python
from typing import TypedDict, Annotated, Sequence
from langchain_core.messages import BaseMessage, add_messages

class BaseGraphState(TypedDict):
    """모든 Graph State의 기본"""
    messages: Annotated[Sequence[BaseMessage], add_messages]
```

**states/supervisor_state.py** - Supervisor State
```python
from typing import Optional, Dict, Any
from app.states.base_state import BaseGraphState

class SupervisorState(BaseGraphState):
    """Supervisor Main Graph State"""
    # 라우팅
    next: str  # 다음 실행할 agent 이름 또는 END

    # 세션 정보
    thread_id: str
    user_id: Optional[str]

    # Context
    context: Dict[str, Any]  # 런타임 Context
    session_context: Dict[str, Any]  # 세션 Context

    # 실행 결과
    agent_results: Dict[str, Any]  # Agent별 결과 저장
    final_response: Optional[str]

    # 메타데이터
    metadata: Dict[str, Any]
```

**states/agent_states.py** - Agent State들
```python
from typing import List, Dict, Any, Optional
from app.states.base_state import BaseGraphState

class SearchAgentState(BaseGraphState):
    """Search Agent State"""
    # 검색 쿼리
    query: str
    search_type: str  # "vector" | "web" | "db"

    # Sub_Agent 결과
    vector_results: Optional[List[Dict[str, Any]]]
    web_results: Optional[List[Dict[str, Any]]]
    db_results: Optional[List[Dict[str, Any]]]

    # 최종 결과
    synthesized_results: Optional[str]
    confidence: float

class AnalysisAgentState(BaseGraphState):
    """Analysis Agent State"""
    data: Any
    analysis_type: str
    analysis_results: Optional[Dict[str, Any]]
    insights: Optional[List[str]]

class DocumentAgentState(BaseGraphState):
    """Document Agent State"""
    content_type: str  # "report" | "summary" | "email"
    generated_content: Optional[str]
    formatted_document: Optional[str]
```

**states/shared_state.py** - 공유 State 필드
```python
from typing import TypedDict, Optional, Dict, Any
from datetime import datetime

class SharedStateFields:
    """여러 State에서 공유되는 필드들"""

    @staticmethod
    def timestamp_field() -> datetime:
        return datetime.now()

    @staticmethod
    def error_field() -> Optional[str]:
        return None

    @staticmethod
    def retry_count_field() -> int:
        return 0

class TimestampMixin(TypedDict):
    """타임스탬프 Mixin"""
    created_at: datetime
    updated_at: datetime

class ErrorHandlingMixin(TypedDict):
    """에러 핸들링 Mixin"""
    error: Optional[str]
    error_stack: Optional[str]
    retry_count: int
```

#### Context 관리

**core/context/runtime_context.py** - 런타임 Context
```python
from typing import Any, Dict, Optional
from datetime import datetime
from contextvars import ContextVar

# Thread-safe context variables
current_thread_id: ContextVar[Optional[str]] = ContextVar('thread_id', default=None)
current_user_id: ContextVar[Optional[str]] = ContextVar('user_id', default=None)

class RuntimeContext:
    """실행 중 임시 Context"""

    def __init__(self):
        self._data: Dict[str, Any] = {}
        self._created_at = datetime.now()

    def set(self, key: str, value: Any):
        """Context 값 설정"""
        self._data[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        """Context 값 조회"""
        return self._data.get(key, default)

    def clear(self):
        """Context 초기화"""
        self._data.clear()

    def to_dict(self) -> Dict[str, Any]:
        """Dict로 변환"""
        return {
            **self._data,
            "_created_at": self._created_at.isoformat()
        }
```

**core/context/session_context.py** - 세션 Context
```python
from typing import Any, Dict, Optional
from datetime import datetime

class SessionContext:
    """세션 범위 Context (Thread 기반)"""

    def __init__(self, thread_id: str, user_id: Optional[str] = None):
        self.thread_id = thread_id
        self.user_id = user_id
        self.created_at = datetime.now()
        self.last_active = datetime.now()

        # 세션 데이터
        self._metadata: Dict[str, Any] = {}
        self._conversation_history: list = []

    def update_activity(self):
        """마지막 활동 시간 갱신"""
        self.last_active = datetime.now()

    def add_metadata(self, key: str, value: Any):
        """세션 메타데이터 추가"""
        self._metadata[key] = value
        self.update_activity()

    def get_metadata(self, key: str, default: Any = None) -> Any:
        """세션 메타데이터 조회"""
        return self._metadata.get(key, default)

    def to_dict(self) -> Dict[str, Any]:
        """Dict로 변환"""
        return {
            "thread_id": self.thread_id,
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat(),
            "last_active": self.last_active.isoformat(),
            "metadata": self._metadata
        }
```

**core/context/manager.py** - Context Manager
```python
from typing import Optional
from app.core.context.runtime_context import RuntimeContext, current_thread_id, current_user_id
from app.core.context.session_context import SessionContext

class ContextManager:
    """Context 생명주기 관리"""

    def __init__(self):
        self._runtime_context: Optional[RuntimeContext] = None
        self._session_context: Optional[SessionContext] = None

    def create_runtime_context(self) -> RuntimeContext:
        """런타임 Context 생성"""
        self._runtime_context = RuntimeContext()
        return self._runtime_context

    def create_session_context(self, thread_id: str, user_id: Optional[str] = None) -> SessionContext:
        """세션 Context 생성"""
        self._session_context = SessionContext(thread_id, user_id)

        # ContextVar 설정
        current_thread_id.set(thread_id)
        current_user_id.set(user_id)

        return self._session_context

    def get_runtime_context(self) -> Optional[RuntimeContext]:
        """현재 런타임 Context 조회"""
        return self._runtime_context

    def get_session_context(self) -> Optional[SessionContext]:
        """현재 세션 Context 조회"""
        return self._session_context

    def clear_runtime_context(self):
        """런타임 Context 정리"""
        if self._runtime_context:
            self._runtime_context.clear()
        self._runtime_context = None

    def cleanup(self):
        """모든 Context 정리"""
        self.clear_runtime_context()
        self._session_context = None
        current_thread_id.set(None)
        current_user_id.set(None)
```

#### Agent 독립 모듈

**agents/search_agent/agent.py** - Search Agent
```python
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from app.states.agent_states import SearchAgentState
from app.config.agents.search_agent import SearchAgentConfig
from app.registry.config_registry import ConfigRegistry

def create_search_agent(config: SearchAgentConfig):
    """Search Agent Graph 생성"""

    # LLM 초기화
    llm = ChatOpenAI(
        model=config.model_name,
        temperature=config.temperature,
        max_tokens=config.max_tokens
    )

    # State Graph
    workflow = StateGraph(SearchAgentState)

    # 노드 정의
    async def analyze_query(state: SearchAgentState):
        """쿼리 분석 및 검색 타입 결정"""
        query = state["query"]
        # LLM으로 검색 타입 결정
        # ...
        return {"search_type": "vector"}

    async def route_to_sub_agent(state: SearchAgentState):
        """Sub_Agent로 라우팅"""
        search_type = state["search_type"]
        if search_type == "vector" and config.enable_vector_search:
            return "vector_search"
        elif search_type == "web" and config.enable_web_search:
            return "web_search"
        elif search_type == "db" and config.enable_db_search:
            return "db_search"
        return END

    # 노드 추가
    workflow.add_node("analyze", analyze_query)

    # 엣지
    workflow.set_entry_point("analyze")
    workflow.add_conditional_edges(
        "analyze",
        route_to_sub_agent,
        {
            "vector_search": "vector_search",
            "web_search": "web_search",
            "db_search": "db_search",
            END: END
        }
    )

    return workflow.compile()

# Registry 등록
def register_search_agent():
    """Search Agent를 Registry에 등록"""
    from app.registry.agent_registry import AgentRegistry

    # Config 로드
    config_registry = ConfigRegistry()
    config = config_registry.get("search_agent")

    # Agent 등록
    agent_registry = AgentRegistry()
    agent_registry.register(
        name="search_agent",
        graph_builder=lambda: create_search_agent(config),
        description="다양한 소스에서 정보를 검색하는 Agent"
    )
```

**agents/search_agent/config.py** - Agent Config 로더
```python
from pathlib import Path
from app.config.agents.search_agent import SearchAgentConfig
from app.registry.config_registry import ConfigRegistry

def load_search_agent_config() -> SearchAgentConfig:
    """Search Agent 설정 로드 및 병합"""
    # 기본 설정
    base_config = SearchAgentConfig()

    # YAML 오버라이드 (선택적)
    yaml_path = Path("configs/agents/search_agent.yaml")
    if yaml_path.exists():
        config_registry = ConfigRegistry()
        yaml_data = config_registry.load_from_yaml(yaml_path)
        return config_registry.merge_configs(base_config, yaml_data)

    return base_config
```

**agents/search_agent/prompts.py** - Agent 프롬프트
```python
SEARCH_QUERY_ANALYSIS_PROMPT = """
You are a query analyzer for a search system.

Analyze the following query and determine the best search strategy:
- "vector": For semantic/conceptual searches
- "web": For recent information from the web
- "db": For structured data queries

Query: {query}

Respond with just the search type.
"""

SEARCH_RESULT_SYNTHESIS_PROMPT = """
You are a search result synthesizer.

Synthesize the following search results into a coherent response:

Vector Search Results:
{vector_results}

Database Results:
{db_results}

Provide a comprehensive answer based on these results.
"""
```

---

### 7.1.3 구조 개선의 장점 요약

| 항목 | 기존 구조 | 개선된 구조 | 장점 |
|------|----------|-----------|------|
| **Agent 관리** | `graphs/agents/` 하위 | `agents/` 독립 디렉토리 | 독립성, 재사용성, 확장성 |
| **State 관리** | `models/graph_state.py` 하나 | `states/` 디렉토리로 분리 | 타입 안정성, 명확한 계약 |
| **Context 관리** | 없음 | `core/context/` 전담 | 런타임/세션 구분, 생명주기 관리 |
| **Config 관리** | `config.py` 하나 | `config/` 계층적 구조 | 시스템/Agent 분리, YAML 지원 |
| **관심사 분리** | Graph 안에 Agent 로직 | Graph는 조합만, Agent는 독립 | 유지보수성, 테스트 용이성 |

**핵심 개선 사항:**
1. **Agent 독립성**: 새 Agent 추가 시 다른 코드 수정 불필요
2. **Type Safety**: State를 타입으로 명시적 정의
3. **Config 유연성**: 코드 변경 없이 YAML로 설정 변경
4. **Context 관리**: 런타임/세션 데이터 명확히 분리
5. **테스트 용이성**: 각 모듈이 독립적으로 테스트 가능

---

### 7.2 main.py 구조 (개선)

```python
# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from pathlib import Path

# Config
from app.config.system import SystemConfig
from app.config.database import DatabaseConfig
from app.config.llm import LLMConfig
from app.registry.config_registry import ConfigRegistry

# Core
from app.core.checkpointer import CheckpointerManager
from app.core.context.manager import ContextManager
from app.db.postgres import init_postgres
from app.db.mongodb import init_mongodb
from app.db.faiss_manager import FAISSManager

# Registry
from app.registry.agent_registry import AgentRegistry
from app.registry.tool_registry import ToolRegistry

# API
from app.api import websocket, chat

# Lifespan 이벤트 관리
@asynccontextmanager
async def lifespan(app: FastAPI):
    """앱 생명주기 관리"""

    # 1. Config 로드 및 등록
    config_registry = ConfigRegistry()
    system_config = SystemConfig()
    db_config = DatabaseConfig()
    llm_config = LLMConfig()

    config_registry.register("system", system_config)
    config_registry.register("database", db_config)
    config_registry.register("llm", llm_config)

    # Agent별 Config 로드 (YAML 병합)
    from app.agents.search_agent.config import load_search_agent_config
    from app.agents.analysis_agent.config import load_analysis_agent_config
    from app.agents.document_agent.config import load_document_agent_config

    config_registry.register("search_agent", load_search_agent_config())
    config_registry.register("analysis_agent", load_analysis_agent_config())
    config_registry.register("document_agent", load_document_agent_config())

    # 2. 데이터베이스 초기화
    await init_postgres(db_config.postgres_url)
    await init_mongodb(db_config.mongodb_url)

    # 3. Checkpointer 초기화
    checkpointer_manager = CheckpointerManager(db_config.postgres_url)
    await checkpointer_manager.initialize()
    app.state.checkpointer_manager = checkpointer_manager

    # 4. FAISS 초기화
    faiss_manager = FAISSManager(db_config.faiss_index_path)
    await faiss_manager.initialize()
    app.state.faiss_manager = faiss_manager

    # 5. Context Manager 초기화
    context_manager = ContextManager()
    app.state.context_manager = context_manager

    # 6. Registry 초기화 (Agent, Tool 등록)
    from app.agents.search_agent.agent import register_search_agent
    from app.agents.analysis_agent.agent import register_analysis_agent
    from app.agents.document_agent.agent import register_document_agent
    from app.tools import register_all_tools

    # Agent 등록
    register_search_agent()
    register_analysis_agent()
    register_document_agent()

    # Tool 등록
    register_all_tools()

    # 7. Supervisor Graph 빌드
    from app.graphs.supervisor import build_supervisor_graph
    supervisor_graph = build_supervisor_graph()
    app.state.supervisor_graph = supervisor_graph

    print(f"✅ {system_config.app_name} v{system_config.app_version} started")
    print(f"   - Agents registered: {len(AgentRegistry().list_agents())}")
    print(f"   - Tools registered: {len(ToolRegistry().get_all_tools())}")

    yield

    # Shutdown
    print("🛑 Shutting down...")
    await checkpointer_manager.close()
    context_manager.cleanup()

# FastAPI 앱 생성
system_config = SystemConfig()

app = FastAPI(
    title=system_config.app_name,
    version=system_config.app_version,
    debug=system_config.debug,
    lifespan=lifespan
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=system_config.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(websocket.router, prefix="/ws", tags=["websocket"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])

# 헬스체크
@app.get("/health")
async def health_check():
    """헬스체크 엔드포인트"""
    return {
        "status": "healthy",
        "app": system_config.app_name,
        "version": system_config.app_version
    }
```

### 7.3 WebSocket 엔드포인트

```python
# app/api/websocket.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from app.core.websocket_manager import ConnectionManager
from app.core.thread_manager import ThreadIDManager
from app.graphs.supervisor import create_supervisor_graph

router = APIRouter()
manager = ConnectionManager()

@router.websocket("/chat/{user_id}")
async def websocket_chat(
    websocket: WebSocket,
    user_id: str,
    checkpointer_manager = Depends(get_checkpointer_manager)
):
    """WebSocket 채팅 엔드포인트"""
    await manager.connect(websocket, user_id)

    try:
        # Thread ID 생성
        thread_id = ThreadIDManager.generate_thread_id(user_id)

        # Supervisor Graph 생성
        async with checkpointer_manager.get_checkpointer() as checkpointer:
            graph = create_supervisor_graph(checkpointer)
            config = {"configurable": {"thread_id": thread_id}}

            while True:
                # 메시지 수신
                data = await websocket.receive_json()
                message = data.get("message")

                # Graph 실행 (스트리밍)
                async for event in graph.astream(
                    {"messages": [("user", message)]},
                    config=config,
                    stream_mode="values"
                ):
                    # 진행 상황 전송
                    await websocket.send_json({
                        "type": "update",
                        "data": event
                    })

                    # HITL 체크
                    if event.get("interrupt"):
                        approved = await request_approval(websocket, event["interrupt"])
                        # 승인 결과로 재개
                        # graph.update_state(config, ...)

    except WebSocketDisconnect:
        manager.disconnect(user_id)
```

---

## 8. React Frontend 설계

### 8.1 프로젝트 구조

```
frontend/
├── public/
├── src/
│   ├── components/
│   │   ├── Chat/
│   │   │   ├── ChatWindow.tsx
│   │   │   ├── MessageList.tsx
│   │   │   ├── MessageInput.tsx
│   │   │   └── ApprovalModal.tsx      # HITL UI
│   │   ├── Layout/
│   │   └── Common/
│   │
│   ├── hooks/
│   │   ├── useWebSocket.ts             # WebSocket 훅
│   │   └── useChat.ts                  # 채팅 로직
│   │
│   ├── services/
│   │   └── websocket.service.ts        # WebSocket 클라이언트
│   │
│   ├── types/
│   │   └── chat.types.ts
│   │
│   ├── utils/
│   └── App.tsx
│
├── package.json
└── tsconfig.json
```

### 8.2 WebSocket Hook

```typescript
// hooks/useWebSocket.ts
import { useEffect, useRef, useState } from 'react';

interface Message {
  type: 'message' | 'update' | 'approval_request';
  data: any;
}

export const useWebSocket = (userId: string) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const ws = useRef<WebSocket | null>(null);

  useEffect(() => {
    // WebSocket 연결
    ws.current = new WebSocket(`ws://localhost:8000/ws/chat/${userId}`);

    ws.current.onopen = () => setIsConnected(true);
    ws.current.onclose = () => setIsConnected(false);

    ws.current.onmessage = (event) => {
      const message = JSON.parse(event.data);

      if (message.type === 'approval_request') {
        // HITL 승인 모달 표시
        handleApprovalRequest(message.data);
      } else {
        setMessages((prev) => [...prev, message]);
      }
    };

    return () => {
      ws.current?.close();
    };
  }, [userId]);

  const sendMessage = (message: string) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify({ message }));
    }
  };

  const sendApproval = (approved: boolean) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify({ approved }));
    }
  };

  return { messages, isConnected, sendMessage, sendApproval };
};
```

---

## 9. 구현 단계 (Phase)

### Phase 1: 기반 인프라 구축 (1-2주)
**목표**: 개발 환경 및 핵심 인프라 설정

1. **환경 설정**
   - [ ] LangGraph 1.0으로 업그레이드 (requirements.txt 수정)
   - [ ] uv를 사용한 의존성 관리 설정
   - [ ] 개발 환경 변수 설정 (.env)

2. **데이터베이스 설정**
   - [ ] PostgreSQL 설치 및 스키마 생성
   - [ ] MongoDB 설치 및 컬렉션 설계
   - [ ] FAISS 인덱스 초기화

3. **기본 FastAPI 구조**
   - [ ] 프로젝트 폴더 구조 생성
   - [ ] FastAPI 앱 및 lifespan 이벤트 구현
   - [ ] CORS, 미들웨어 설정

4. **Checkpointer 구현**
   - [ ] AsyncPostgresSaver 설정
   - [ ] Connection Pool 관리
   - [ ] Thread ID 관리자 구현

### Phase 2: Registry 및 Tool 구현 (1-2주)
**목표**: 재사용 가능한 Tool 및 Registry 시스템 구축

1. **Registry 패턴 구현**
   - [ ] BaseRegistry 추상 클래스
   - [ ] AgentRegistry, SubAgentRegistry, ToolRegistry
   - [ ] 싱글톤 패턴 테스트

2. **기본 Tool 개발**
   - [ ] FAISS 검색 Tool (RAG)
   - [ ] PostgreSQL 조회 Tool
   - [ ] MongoDB 조회 Tool
   - [ ] 외부 API Tool (예시)

3. **Tool Registry 등록**
   - [ ] Tool 등록 함수 작성
   - [ ] 카테고리별 분류

### Phase 3: LangGraph 구조 구현 (2-3주)
**목표**: Main Graph, Agent, Sub_Agent 계층 구조 완성

1. **Main Graph (Supervisor)**
   - [ ] SupervisorState 정의
   - [ ] Supervisor 노드 구현
   - [ ] Agent 라우팅 로직
   - [ ] Graph 컴파일

2. **Agent SubGraphs**
   - [ ] AgentState 정의
   - [ ] 최소 2-3개 Agent 구현
   - [ ] Sub_Agent 조율 로직
   - [ ] Agent Registry 등록

3. **Sub_Agent SubGraphs**
   - [ ] SubAgentState 정의
   - [ ] Tool 호출 로직
   - [ ] 에러 핸들링
   - [ ] SubAgent Registry 등록

4. **Graph 통합 테스트**
   - [ ] Main → Agent → Sub_Agent 플로우 테스트
   - [ ] State 전달 확인
   - [ ] Checkpointer 동작 확인

### Phase 4: Human-in-the-Loop 구현 (1주)
**목표**: 멀티 레벨 HITL 기능 완성

1. **HITL 핸들러**
   - [ ] HITLHandler 구현
   - [ ] 레벨별 interrupt 로직
   - [ ] 신뢰도 기반 중단 결정

2. **WebSocket HITL**
   - [ ] 승인 요청 메시지 구조
   - [ ] 타임아웃 처리
   - [ ] 승인/거부 후 재개 로직

3. **HITL 로깅**
   - [ ] PostgreSQL 승인 로그 저장
   - [ ] 분석 대시보드 (옵션)

### Phase 5: WebSocket API 구현 (1-2주)
**목표**: 실시간 양방향 통신 구현

1. **WebSocket 서버**
   - [ ] ConnectionManager 구현
   - [ ] 채팅 엔드포인트
   - [ ] 스트리밍 응답
   - [ ] HITL 통합

2. **세션 관리**
   - [ ] Thread ID 기반 세션
   - [ ] 재연결 처리
   - [ ] 세션 만료 처리

3. **에러 핸들링**
   - [ ] WebSocket 에러 처리
   - [ ] 재연결 로직
   - [ ] 에러 메시지 전송

### Phase 6: React Frontend 구현 (1-2주)
**목표**: 사용자 인터페이스 완성

1. **기본 UI 구조**
   - [ ] Create React App 설정
   - [ ] 컴포넌트 구조 생성
   - [ ] 라우팅 (필요시)

2. **WebSocket 클라이언트**
   - [ ] useWebSocket 훅
   - [ ] 메시지 송수신
   - [ ] 연결 상태 표시

3. **채팅 UI**
   - [ ] ChatWindow 컴포넌트
   - [ ] MessageList (메시지 표시)
   - [ ] MessageInput (입력)
   - [ ] 스트리밍 응답 표시

4. **HITL UI**
   - [ ] ApprovalModal 컴포넌트
   - [ ] 승인/거부 버튼
   - [ ] 컨텍스트 정보 표시

### Phase 7: 통합 테스트 및 최적화 (1-2주)
**목표**: End-to-End 테스트 및 성능 최적화

1. **통합 테스트**
   - [ ] E2E 시나리오 테스트
   - [ ] HITL 플로우 테스트
   - [ ] 에러 시나리오 테스트

2. **성능 최적화**
   - [ ] 데이터베이스 쿼리 최적화
   - [ ] Graph 실행 속도 개선
   - [ ] WebSocket 동시 연결 테스트

3. **모니터링**
   - [ ] 로깅 시스템
   - [ ] 메트릭 수집
   - [ ] 에러 추적

### Phase 8: 배포 준비 (1주)
**목표**: 프로덕션 배포 준비

1. **환경 설정**
   - [ ] Production 환경 변수
   - [ ] 시크릿 관리
   - [ ] HTTPS 설정

2. **Docker 컨테이너화** (옵션)
   - [ ] Dockerfile 작성
   - [ ] docker-compose.yml
   - [ ] 컨테이너 테스트

3. **문서화**
   - [ ] API 문서 (OpenAPI/Swagger)
   - [ ] 배포 가이드
   - [ ] 운영 매뉴얼

---

## 10. 주요 코드 예시

### 10.1 Supervisor Graph 구현

```python
# graphs/supervisor.py
from typing import Literal, Annotated, Sequence
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_openai import ChatOpenAI

from app.registry.agent_registry import AgentRegistry
from app.models.graph_state import SupervisorState

def create_supervisor_graph(checkpointer: AsyncPostgresSaver):
    """Supervisor Main Graph 생성"""

    # State 정의
    class State(TypedDict):
        messages: Annotated[Sequence[BaseMessage], add_messages]
        next: str
        thread_id: str
        final_response: str | None

    # LLM
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    # Registry에서 Agent 목록 가져오기
    registry = AgentRegistry()
    available_agents = registry.list_agents()

    # Supervisor 노드
    async def supervisor_node(state: State):
        """Supervisor: Agent 선택 및 라우팅"""
        messages = state["messages"]

        # Agent 선택 프롬프트
        system_prompt = f"""You are a supervisor managing these agents:
        {chr(10).join(f"- {a['name']}: {a['description']}" for a in available_agents)}

        Given the user request, decide which agent should handle it next.
        Respond with the agent name or 'FINISH' if done.
        """

        response = await llm.ainvoke([
            {"role": "system", "content": system_prompt},
            *messages
        ])

        # 다음 Agent 결정
        next_agent = response.content.strip()

        return {
            "next": next_agent if next_agent != "FINISH" else END,
            "messages": [response]
        }

    # Agent 실행 노드들 동적 생성
    async def create_agent_node(agent_name: str):
        """Agent SubGraph 실행"""
        async def agent_node(state: State):
            agent_graph = registry.get(agent_name)

            # SubGraph 실행
            result = await agent_graph.ainvoke(
                {"messages": state["messages"], "task": agent_name}
            )

            return {
                "messages": result["messages"],
                "next": "supervisor"  # Supervisor로 돌아감
            }
        return agent_node

    # Graph 구축
    workflow = StateGraph(State)

    # Supervisor 노드
    workflow.add_node("supervisor", supervisor_node)

    # Agent 노드들 추가
    for agent in available_agents:
        workflow.add_node(
            agent["name"],
            await create_agent_node(agent["name"])
        )

    # 엣지 설정
    workflow.set_entry_point("supervisor")

    # Conditional edges from supervisor
    workflow.add_conditional_edges(
        "supervisor",
        lambda s: s["next"],
        {agent["name"]: agent["name"] for agent in available_agents} | {END: END}
    )

    # All agents return to supervisor
    for agent in available_agents:
        workflow.add_edge(agent["name"], "supervisor")

    # 컴파일 (with checkpointer)
    return workflow.compile(checkpointer=checkpointer)
```

### 10.2 Agent SubGraph 예시

```python
# graphs/agents/search_agent.py
from langgraph.graph import StateGraph
from langchain_core.messages import BaseMessage

from app.registry.tool_registry import ToolRegistry
from app.models.graph_state import AgentState

def create_search_agent():
    """검색 Agent SubGraph"""

    class State(TypedDict):
        messages: Annotated[Sequence[BaseMessage], add_messages]
        task: str
        search_results: List[Dict] | None

    llm = ChatOpenAI(model="gpt-4o-mini")

    # Tool 가져오기
    tool_registry = ToolRegistry()
    search_tool = tool_registry.get("faiss_search")

    # Agent 노드
    async def search_node(state: State):
        """검색 수행"""
        query = state["messages"][-1].content

        # Tool 실행
        results = await search_tool.ainvoke({"query": query})

        return {
            "search_results": results,
            "messages": [AIMessage(content=f"Found {len(results)} results")]
        }

    async def synthesize_node(state: State):
        """결과 종합"""
        results = state["search_results"]
        query = state["messages"][-1].content

        prompt = f"Query: {query}\n\nResults: {results}\n\nSynthesize answer:"
        response = await llm.ainvoke([{"role": "user", "content": prompt}])

        return {"messages": [response]}

    # Graph 구축
    workflow = StateGraph(State)
    workflow.add_node("search", search_node)
    workflow.add_node("synthesize", synthesize_node)

    workflow.set_entry_point("search")
    workflow.add_edge("search", "synthesize")
    workflow.add_edge("synthesize", END)

    return workflow.compile()

# Registry 등록
def register_search_agent():
    registry = AgentRegistry()
    registry.register(
        name="search_agent",
        graph_builder=create_search_agent
    )
```

---

## 11. 주요 결정 사항 (확정)

### 11.1 기술적 결정

1. **LangChain & LangGraph 1.0으로 업그레이드**: ✅ **필수**
   - **LangChain 1.0.3** + **LangGraph 1.0.2** (2025년 10월 동시 출시)
   - 두 프레임워크가 함께 작동하도록 설계됨 (완전 호환)
   - 주요 변경:
     - `langgraph.prebuilt` → `langchain.agents`
     - Checkpointer 2.x → 3.0.0 (Major 업데이트)
   - requirements.txt 전체 업데이트 필요

2. **챗봇 도메인**: ✅ **범용 에이전트**
   - 특정 도메인에 종속되지 않는 범용 구조
   - 점진적 기능 확장 가능한 아키텍처

3. **초기 Agent 구성**: ✅ **3개 Agent (구조만)**
   - **Search Agent**: 검색 기능
   - **Analysis Agent**: 분석 기능
   - **Document Agent**: 문서 생성 기능
   - 각 Agent는 기본 구조만 구현, 구체적 기능은 향후 추가

4. **데이터베이스**: ✅ **연결만 설정**
   - PostgreSQL: Checkpointer 및 세션 관리
   - FAISS: 벡터 DB (향후 RAG용)
   - MongoDB: 로그/분석 데이터 (향후 사용)
   - **초기에는 데이터 없이 연결만 구현**

5. **인증 시스템**: ✅ **추후 구현**
   - Phase 1에서는 제외
   - WebSocket user_id만 사용 (인증 없음)

### 11.2 추후 논의 필요 사항

다음 항목들은 Phase 2 이후 구체화 예정:

1. **구체적 Agent 기능**
   - Search Agent의 실제 검색 로직
   - Analysis Agent의 분석 알고리즘
   - Document Agent의 문서 포맷

2. **Tool 구체화**
   - 외부 API 연동 여부
   - 특화된 Tool 목록

3. **HITL 정책**
   - 승인이 필요한 작업 목록
   - 신뢰도 임계값

4. **운영 환경**
   - 배포 인프라 (클라우드/온프레미스)
   - Docker/Kubernetes 사용 여부
   - 모니터링/로깅 도구

---

## 11.3 LangChain & LangGraph 1.0 마이그레이션 가이드

### 주요 Breaking Changes 및 대응

#### 1. langgraph.prebuilt → langchain.agents
**Before (0.6.x):**
```python
from langgraph.prebuilt import create_react_agent

agent = create_react_agent(llm, tools)
```

**After (1.0):**
```python
from langchain.agents import create_react_agent
# 또는
from langchain_core.agents import create_react_agent

agent = create_react_agent(llm, tools)
```

#### 2. Checkpointer 2.x → 3.0
**Before (2.x):**
```python
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

checkpointer = AsyncPostgresSaver.from_conn_string(DB_URI)
await checkpointer.setup()
```

**After (3.0):**
```python
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

# API는 동일하지만 내부 스키마가 변경될 수 있음
# 공식 문서에서 마이그레이션 가이드 확인 필요
checkpointer = AsyncPostgresSaver.from_conn_string(DB_URI)
await checkpointer.setup()
```

> **⚠️ 주의**: Checkpointer 3.0은 기존 2.x 데이터베이스 스키마와 호환되지 않을 수 있습니다. 프로덕션 환경에서는 데이터 마이그레이션 계획 필요.

#### 3. StateGraph import 경로 (변경 없음)
```python
# 1.0에서도 동일
from langgraph.graph import StateGraph, END
```

#### 4. 권장 업그레이드 순서

```bash
# 1. 백업 생성
cp requirements.txt requirements.txt.backup

# 2. 코어 패키지 업그레이드
uv pip install --upgrade langchain-core==1.0.2

# 3. LangChain 및 통합 패키지 업그레이드
uv pip install --upgrade \
  langchain==1.0.3 \
  langchain-openai==1.0.1 \
  langchain-community==0.4.1

# 4. LangGraph 업그레이드
uv pip install --upgrade \
  langgraph==1.0.2 \
  langgraph-checkpoint==3.0.0 \
  langgraph-checkpoint-postgres==3.0.0

# 5. 버전 확인
uv pip list | grep -E "(langchain|langgraph)"

# 6. 테스트 실행
pytest tests/
```

#### 5. 마이그레이션 체크리스트

- [ ] requirements.txt 백업 완료
- [ ] `langgraph.prebuilt` 사용 코드 검색 및 수정
- [ ] Checkpointer 초기화 코드 확인
- [ ] 기존 체크포인트 데이터베이스 백업 (프로덕션인 경우)
- [ ] 테스트 환경에서 업그레이드 테스트
- [ ] 모든 테스트 통과 확인
- [ ] 문서 업데이트

#### 6. 호환성 확인 명령

```python
# version_check.py
import langchain
import langgraph
import langchain_core
import langchain_openai

print(f"LangChain: {langchain.__version__}")
print(f"LangGraph: {langgraph.__version__}")
print(f"LangChain Core: {langchain_core.__version__}")
print(f"LangChain OpenAI: {langchain_openai.__version__}")

# 예상 출력:
# LangChain: 1.0.3
# LangGraph: 1.0.2
# LangChain Core: 1.0.2
# LangChain OpenAI: 1.0.1
```

---

## 12. 참고 자료

### 12.1 공식 문서
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [LangGraph Supervisor Pattern](https://langchain-ai.github.io/langgraphjs/tutorials/multi_agent/agent_supervisor/)
- [AsyncPostgresSaver](https://langchain-ai.github.io/langgraph/how-tos/persistence_postgres/)
- [Human-in-the-Loop Guide](https://docs.langchain.com/oss/python/langchain/human-in-the-loop)

### 12.2 예제 코드
- [langgraph-supervisor-py](https://github.com/langchain-ai/langgraph-supervisor-py)
- [LangGraph Multi-Agent Examples](https://github.com/langchain-ai/langgraph/tree/main/examples)

### 12.3 관련 블로그/튜토리얼
- [Building Multi-Agents Supervisor System](https://medium.com/@anuragmishra_27746/building-multi-agents-supervisor-system-from-scratch-with-langgraph-langsmith-b602e8c2c95d)
- [LangGraph Subgraph Architecture](https://dev.to/jamesli/building-complex-ai-workflows-with-langgraph-a-detailed-explanation-of-subgraph-architecture-1dj5)

---

## 13. 다음 단계 (Next Steps)

### 13.1 즉시 실행 항목

1. **환경 업그레이드** (LangChain & LangGraph 1.0)
   ```bash
   # requirements.txt에서 다음 라인들을 업데이트:

   # LangChain 1.0 (동시 출시, 완전 호환)
   langchain==1.0.3
   langchain-core==1.0.2
   langchain-openai==1.0.1
   langchain-community==0.4.1  # 아직 1.0 미출시

   # LangGraph 1.0
   langgraph==1.0.2
   langgraph-checkpoint==3.0.0  # Major 업데이트
   langgraph-checkpoint-postgres==3.0.0

   # 기타 LangGraph 패키지도 확인 필요
   langgraph-prebuilt==1.0.2  # deprecated, langchain.agents 사용 권장

   # uv를 사용하여 의존성 업데이트
   uv pip install -r requirements.txt

   # 또는 직접 업그레이드
   uv pip install --upgrade langchain langgraph langchain-core langchain-openai
   ```

   **⚠️ 주의사항:**
   - Checkpointer가 2.x → 3.0으로 Major 업데이트되므로 API 변경 가능
   - 기존 코드에서 `langgraph.prebuilt` 사용 시 `langchain.agents`로 마이그레이션 필요

2. **Phase 1 시작 준비**
   - 프로젝트 폴더 구조 생성
   - 데이터베이스 연결 설정
   - 기본 FastAPI 앱 구조 구축

3. **초기 PoC 개발**
   - Main Graph (Supervisor) 기본 구조
   - 1개 Agent (Search Agent) 기본 구조로 전체 플로우 검증
   - WebSocket 기본 통신 테스트

### 13.2 단계별 진행 계획

```
Week 1-2:  Phase 1 (환경 및 인프라)
Week 3-4:  Phase 2 (Registry 및 Tool)
Week 5-7:  Phase 3 (LangGraph 구조)
Week 8:    Phase 4 (HITL)
Week 9-10: Phase 5-6 (WebSocket + Frontend)
Week 11-12: Phase 7-8 (테스트 및 최적화)
```

### 13.3 성공 지표

Phase 1 완료 기준:
- ✅ **LangChain 1.0.3 + LangGraph 1.0.2 업그레이드 완료**
- ✅ Checkpointer 3.0.0 마이그레이션 및 PostgreSQL 연결 확인
- ✅ langgraph.prebuilt → langchain.agents 전환 (deprecated 제거)
- ✅ 기본 Supervisor → Search Agent → Sub_Agent 플로우 실행 성공
- ✅ WebSocket을 통한 메시지 송수신 확인
- ✅ Thread ID 기반 세션 관리 동작 확인

---

## 14. 요약

### 14.1 핵심 아키텍처

- **패턴**: LangGraph 1.0 Supervisor Pattern
- **구조**: Main Graph → Agent (3종) → Sub_Agent → Tools
- **관리**: Registry 기반 싱글톤 패턴
- **영속성**: AsyncPostgresSaver (Thread ID 기반)
- **제어**: Multi-level Human-in-the-Loop
- **통신**: WebSocket (FastAPI ↔ React)

### 14.2 초기 구현 범위

**구현**:
- 3개 Agent 구조: Search, Analysis, Document
- 데이터베이스 연결: PostgreSQL, MongoDB, FAISS
- Registry 시스템
- WebSocket 통신
- 기본 HITL 구조

**미구현 (추후)**:
- 구체적 Agent 기능
- 실제 데이터 및 Tool
- 인증/권한 시스템
- 배포 인프라

### 14.3 기술 스택 요약

| 분류 | 기술 | 버전/설명 |
|------|------|-----------|
| AI Framework | **LangChain** | **1.0.3** |
|  | **LangGraph** | **1.0.2** |
|  | langchain-core | 1.0.2 |
|  | langchain-openai | 1.0.1 |
|  | langchain-community | 0.4.1 |
| LLM | OpenAI | API |
| Backend | FastAPI | 0.115.0 |
| Frontend | React | Create React App |
| Communication | WebSocket | - |
| Checkpointer | langgraph-checkpoint | **3.0.0** (Major) |
|  | langgraph-checkpoint-postgres | 3.0.0 |
| Database | PostgreSQL | 3.2.10 (psycopg) |
|  | MongoDB | - |
|  | FAISS | 1.9.0.post1 (faiss-cpu) |
| Language | Python | 3.12.7 |
| Package Manager | uv | - |

---

**작성자**: Claude
**버전**: 3.0 (LangChain & LangGraph 1.0 반영)
**최종 수정**: 2025-11-03
**문서 상태**: ✅ 확정 (Phase 1 시작 준비 완료)

---

## 부록: 추가 정보

### A. LangChain & LangGraph 1.0 출시 정보

- **출시일**: 2025년 10월 17-29일
- **주요 마일스톤**:
  - 첫 stable major release (production-ready)
  - Uber, LinkedIn, Klarna 등에서 1년 이상 프로덕션 사용
  - 2.0까지 breaking changes 없음 보장
- **공식 발표**: [LangChain and LangGraph Agent Frameworks Reach v1.0 Milestones](https://blog.langchain.com/langchain-langgraph-1dot0/)

### B. Python 버전 요구사항

| 패키지 | Python 버전 요구사항 |
|--------|---------------------|
| LangChain 1.0 | >=3.10 |
| LangGraph 1.0 | >=3.10, <4.0 (3.13 지원) |
| langgraph-checkpoint | >=3.9.0, <4.0.0 |
| LangGraph CLI | >=3.11 |
| **현재 프로젝트** | **3.12.7** ✅ |

### C. 유용한 커맨드

```bash
# 현재 설치된 LangChain/LangGraph 패키지 확인
uv pip list | grep -E "(langchain|langgraph)"

# 모든 LangChain 관련 패키지를 최신 1.0으로 업그레이드
uv pip install --upgrade langchain langchain-core langchain-openai langchain-community

# 모든 LangGraph 관련 패키지를 최신 1.0으로 업그레이드
uv pip install --upgrade langgraph langgraph-checkpoint langgraph-checkpoint-postgres

# deprecated 패키지 확인
uv pip list --outdated

# requirements.txt 재생성
uv pip freeze > requirements_new.txt
```
