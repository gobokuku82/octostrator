# Agent 시스템 구현 설계 문서

**작성일**: 2025-11-04
**버전**: 1.0

## 1. 개요

현재 에이전트가 없는 구조에서 **Supervisor - Agent - SubGraph - Tool** 구조로 전환하는 설계 문서입니다.

### 1.1 목표
- 각 Agent를 개별 폴더로 관리하여 독립성과 확장성 확보
- Singleton 패턴 기반 Registry를 통한 효율적인 리소스 관리
- SubGraph와 Tool의 공유 구조로 재사용성 극대화
- LangGraph 기반의 계층적 그래프 구조 구현

---

## 2. 시스템 아키텍처

### 2.1 계층 구조
```
┌─────────────────────────────────────────┐
│          Supervisor Graph               │
│  - 전체 워크플로우 조율                    │
│  - Agent 선택 및 라우팅                   │
│  - 결과 집계 및 응답 생성                  │
└──────────────┬──────────────────────────┘
               │
               ├──> Agent 1 (독립 폴더)
               │    ├─ SubGraph A
               │    ├─ SubGraph B
               │    └─ Tool 1, 2, 3
               │
               ├──> Agent 2 (독립 폴더)
               │    ├─ SubGraph A (공유)
               │    ├─ SubGraph C
               │    └─ Tool 2, 4, 5
               │
               └──> Agent N (독립 폴더)
                    └─ ...

┌─────────────────────────────────────────┐
│      Shared Resources (공유 자원)         │
│  - sub_graphs/ (모든 SubGraph)           │
│  - tools/ (모든 Tool)                    │
│  - Registry (싱글톤 관리)                │
└─────────────────────────────────────────┘
```

---

## 3. 디렉토리 구조 설계

### 3.1 전체 구조
```
backend/app/octostrator/
│
├── supervisor/                  # Supervisor 레이어
│   ├── __init__.py
│   ├── graph.py                # Supervisor 그래프 정의
│   ├── prompts.py              # Supervisor 프롬프트
│   └── nodes/                  # Supervisor 노드들
│       ├── __init__.py
│       ├── intent_understanding.py
│       ├── planning.py
│       ├── router.py           # Agent 라우팅
│       ├── executor.py         # Agent 실행
│       ├── aggregator.py       # 결과 집계
│       └── generators/
│
├── agents/                      # Agent 레이어 (각 Agent별 폴더)
│   ├── __init__.py
│   ├── registry.py             # Agent Registry (싱글톤)
│   │
│   ├── base/                   # Base Agent 클래스
│   │   ├── __init__.py
│   │   ├── agent_base.py       # Abstract Base Agent
│   │   └── agent_config.py     # Agent 설정 스키마
│   │
│   ├── contract_agent/         # 계약서 분석 Agent
│   │   ├── __init__.py
│   │   ├── agent.py            # Agent 구현
│   │   ├── graph.py            # Agent 그래프
│   │   ├── prompts.py          # Agent 프롬프트
│   │   ├── nodes/              # Agent 노드들
│   │   │   ├── __init__.py
│   │   │   ├── analyze.py
│   │   │   └── validate.py
│   │   └── state.py            # Agent State 정의
│   │
│   ├── law_agent/              # 법률 검색 Agent
│   │   ├── __init__.py
│   │   ├── agent.py
│   │   ├── graph.py
│   │   ├── prompts.py
│   │   ├── nodes/
│   │   │   ├── __init__.py
│   │   │   ├── search.py
│   │   │   └── summarize.py
│   │   └── state.py
│   │
│   ├── report_agent/           # 보고서 생성 Agent
│   │   ├── __init__.py
│   │   ├── agent.py
│   │   ├── graph.py
│   │   ├── prompts.py
│   │   ├── nodes/
│   │   │   ├── __init__.py
│   │   │   ├── structure.py
│   │   │   └── format.py
│   │   └── state.py
│   │
│   └── chat_agent/             # 대화형 Agent
│       ├── __init__.py
│       ├── agent.py
│       ├── graph.py
│       ├── prompts.py
│       ├── nodes/
│       │   ├── __init__.py
│       │   └── respond.py
│       └── state.py
│
├── sub_graphs/                  # 공유 SubGraph (폴더 없이 평면 구조)
│   ├── __init__.py
│   ├── registry.py             # SubGraph Registry (싱글톤)
│   ├── validation_graph.py     # 검증 서브그래프
│   ├── search_graph.py         # 검색 서브그래프
│   ├── formatting_graph.py     # 포맷팅 서브그래프
│   ├── rag_graph.py            # RAG 서브그래프
│   └── hitl_graph.py           # Human-in-the-Loop 서브그래프
│
├── tools/                       # 공유 Tool (폴더 없이 평면 구조)
│   ├── __init__.py
│   ├── registry.py             # Tool Registry (싱글톤)
│   ├── database_tool.py        # DB 접근 도구
│   ├── vector_search_tool.py   # 벡터 검색 도구
│   ├── llm_tool.py             # LLM 호출 도구
│   ├── text_processing_tool.py # 텍스트 처리 도구
│   ├── pdf_tool.py             # PDF 처리 도구
│   └── validation_tool.py      # 검증 도구
│
├── states/                      # State 정의
│   ├── __init__.py
│   ├── supervisor_state.py     # Supervisor State
│   └── common_state.py         # 공통 State 베이스
│
├── contexts/                    # Context 관리
│   ├── __init__.py
│   └── app_context.py
│
├── session/                     # 세션 관리
│   ├── __init__.py
│   └── session_manager.py
│
├── checkpointer/                # Checkpointing
│   ├── __init__.py
│   └── postgres_checkpointer.py
│
└── __init__.py
```

---

## 4. Registry 시스템 설계 (싱글톤 패턴)

### 4.1 Registry 구조

각 레이어(Agent, SubGraph, Tool)는 독립적인 Registry를 가지며, 싱글톤 패턴으로 구현됩니다.

```python
# agents/registry.py
from typing import Dict, Type, Optional
from threading import Lock
from .base.agent_base import BaseAgent

class AgentRegistry:
    """Agent Registry - Singleton Pattern"""

    _instance: Optional['AgentRegistry'] = None
    _lock: Lock = Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._agents: Dict[str, BaseAgent] = {}
        self._agent_classes: Dict[str, Type[BaseAgent]] = {}
        self._initialized = True

    def register(self, name: str, agent_class: Type[BaseAgent]) -> None:
        """Agent 클래스 등록"""
        self._agent_classes[name] = agent_class

    def get(self, name: str, **kwargs) -> BaseAgent:
        """Agent 인스턴스 가져오기 (Lazy Initialization)"""
        if name not in self._agents:
            if name not in self._agent_classes:
                raise ValueError(f"Agent '{name}' not registered")

            # 인스턴스 생성 (처음 호출 시에만)
            self._agents[name] = self._agent_classes[name](**kwargs)

        return self._agents[name]

    def list_agents(self) -> list[str]:
        """등록된 Agent 목록"""
        return list(self._agent_classes.keys())

    def clear(self) -> None:
        """Registry 초기화 (테스트용)"""
        self._agents.clear()
        self._agent_classes.clear()


# 전역 인스턴스
agent_registry = AgentRegistry()
```

### 4.2 SubGraph Registry

```python
# sub_graphs/registry.py
from typing import Dict, Callable, Optional
from threading import Lock
from langgraph.graph import StateGraph

class SubGraphRegistry:
    """SubGraph Registry - Singleton Pattern"""

    _instance: Optional['SubGraphRegistry'] = None
    _lock: Lock = Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._subgraph_builders: Dict[str, Callable] = {}
        self._subgraph_cache: Dict[str, StateGraph] = {}
        self._initialized = True

    def register(self, name: str, builder: Callable) -> None:
        """SubGraph Builder 등록"""
        self._subgraph_builders[name] = builder

    def get(self, name: str, **kwargs) -> StateGraph:
        """SubGraph 가져오기 (캐싱)"""
        cache_key = f"{name}_{hash(frozenset(kwargs.items()))}"

        if cache_key not in self._subgraph_cache:
            if name not in self._subgraph_builders:
                raise ValueError(f"SubGraph '{name}' not registered")

            # SubGraph 빌드
            self._subgraph_cache[cache_key] = self._subgraph_builders[name](**kwargs)

        return self._subgraph_cache[cache_key]

    def list_subgraphs(self) -> list[str]:
        """등록된 SubGraph 목록"""
        return list(self._subgraph_builders.keys())


# 전역 인스턴스
subgraph_registry = SubGraphRegistry()
```

### 4.3 Tool Registry

```python
# tools/registry.py
from typing import Dict, Callable, Optional, Any
from threading import Lock

class ToolRegistry:
    """Tool Registry - Singleton Pattern"""

    _instance: Optional['ToolRegistry'] = None
    _lock: Lock = Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._tools: Dict[str, Callable] = {}
        self._tool_metadata: Dict[str, Dict[str, Any]] = {}
        self._initialized = True

    def register(
        self,
        name: str,
        tool_func: Callable,
        description: str = "",
        parameters: Dict[str, Any] = None
    ) -> None:
        """Tool 함수 등록"""
        self._tools[name] = tool_func
        self._tool_metadata[name] = {
            "description": description,
            "parameters": parameters or {}
        }

    def get(self, name: str) -> Callable:
        """Tool 가져오기"""
        if name not in self._tools:
            raise ValueError(f"Tool '{name}' not registered")
        return self._tools[name]

    def get_metadata(self, name: str) -> Dict[str, Any]:
        """Tool 메타데이터 가져오기"""
        return self._tool_metadata.get(name, {})

    def list_tools(self) -> list[str]:
        """등록된 Tool 목록"""
        return list(self._tools.keys())


# 전역 인스턴스
tool_registry = ToolRegistry()
```

---

## 5. Base Agent 클래스 설계

### 5.1 Abstract Base Agent

```python
# agents/base/agent_base.py
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from langgraph.graph import StateGraph, END
from pydantic import BaseModel

class AgentConfig(BaseModel):
    """Agent 설정"""
    name: str
    description: str
    llm_model: str = "gpt-4"
    temperature: float = 0.7
    max_tokens: int = 2000
    tools: List[str] = []
    subgraphs: List[str] = []

class BaseAgent(ABC):
    """Base Agent 추상 클래스"""

    def __init__(self, config: AgentConfig):
        self.config = config
        self.graph: Optional[StateGraph] = None
        self._compiled_graph = None

    @abstractmethod
    def build_graph(self) -> StateGraph:
        """Agent Graph 구성 (각 Agent에서 구현)"""
        pass

    @abstractmethod
    def get_state_schema(self) -> type:
        """State Schema 반환"""
        pass

    def compile(self, checkpointer=None) -> Any:
        """Graph 컴파일"""
        if self._compiled_graph is None:
            self.graph = self.build_graph()
            self._compiled_graph = self.graph.compile(checkpointer=checkpointer)
        return self._compiled_graph

    async def invoke(self, input_data: Dict, config: Optional[Dict] = None):
        """Agent 실행"""
        compiled = self.compile()
        return await compiled.ainvoke(input_data, config=config)

    async def stream(self, input_data: Dict, config: Optional[Dict] = None):
        """Agent 스트림 실행"""
        compiled = self.compile()
        async for chunk in compiled.astream(input_data, config=config):
            yield chunk

    def get_tools(self) -> List[Callable]:
        """Agent가 사용하는 Tool 리스트"""
        from ...tools.registry import tool_registry
        return [tool_registry.get(tool_name) for tool_name in self.config.tools]

    def get_subgraphs(self) -> Dict[str, StateGraph]:
        """Agent가 사용하는 SubGraph 리스트"""
        from ...sub_graphs.registry import subgraph_registry
        return {
            name: subgraph_registry.get(name)
            for name in self.config.subgraphs
        }
```

---

## 6. Agent 구현 예시

### 6.1 Contract Agent (계약서 분석)

```python
# agents/contract_agent/agent.py
from typing import Dict
from langgraph.graph import StateGraph, END
from ..base.agent_base import BaseAgent, AgentConfig
from .state import ContractAgentState
from .nodes.analyze import analyze_contract
from .nodes.validate import validate_contract

class ContractAgent(BaseAgent):
    """계약서 분석 Agent"""

    def __init__(self):
        config = AgentConfig(
            name="contract_agent",
            description="계약서를 분석하고 주요 조항을 추출합니다",
            tools=["pdf_tool", "text_processing_tool", "validation_tool"],
            subgraphs=["validation_graph", "rag_graph"]
        )
        super().__init__(config)

    def get_state_schema(self) -> type:
        return ContractAgentState

    def build_graph(self) -> StateGraph:
        """Contract Agent Graph 구성"""
        graph = StateGraph(ContractAgentState)

        # Nodes 추가
        graph.add_node("analyze", analyze_contract)
        graph.add_node("validate", validate_contract)

        # SubGraph 통합
        subgraphs = self.get_subgraphs()
        graph.add_node("rag", subgraphs["rag_graph"])
        graph.add_node("validation", subgraphs["validation_graph"])

        # Edges 정의
        graph.set_entry_point("analyze")
        graph.add_edge("analyze", "rag")
        graph.add_edge("rag", "validate")
        graph.add_edge("validate", "validation")
        graph.add_edge("validation", END)

        return graph
```

### 6.2 Law Agent (법률 검색)

```python
# agents/law_agent/agent.py
from langgraph.graph import StateGraph, END
from ..base.agent_base import BaseAgent, AgentConfig
from .state import LawAgentState
from .nodes.search import search_laws
from .nodes.summarize import summarize_results

class LawAgent(BaseAgent):
    """법률 검색 및 분석 Agent"""

    def __init__(self):
        config = AgentConfig(
            name="law_agent",
            description="법률 정보를 검색하고 요약합니다",
            tools=["vector_search_tool", "llm_tool"],
            subgraphs=["search_graph", "rag_graph"]
        )
        super().__init__(config)

    def get_state_schema(self) -> type:
        return LawAgentState

    def build_graph(self) -> StateGraph:
        graph = StateGraph(LawAgentState)

        graph.add_node("search", search_laws)
        graph.add_node("summarize", summarize_results)

        subgraphs = self.get_subgraphs()
        graph.add_node("search_graph", subgraphs["search_graph"])
        graph.add_node("rag", subgraphs["rag_graph"])

        graph.set_entry_point("search")
        graph.add_edge("search", "search_graph")
        graph.add_edge("search_graph", "rag")
        graph.add_edge("rag", "summarize")
        graph.add_edge("summarize", END)

        return graph
```

---

## 7. SubGraph 구현 예시

### 7.1 Validation SubGraph

```python
# sub_graphs/validation_graph.py
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated
from operator import add

class ValidationState(TypedDict):
    """Validation State"""
    data: dict
    errors: Annotated[list, add]
    is_valid: bool

def validate_schema(state: ValidationState) -> ValidationState:
    """스키마 검증"""
    # 검증 로직
    return state

def validate_business_rules(state: ValidationState) -> ValidationState:
    """비즈니스 규칙 검증"""
    # 검증 로직
    return state

def decide_validity(state: ValidationState) -> str:
    """유효성 결정"""
    return "valid" if state["is_valid"] else "invalid"

def build_validation_graph() -> StateGraph:
    """Validation SubGraph 빌드"""
    graph = StateGraph(ValidationState)

    graph.add_node("schema_validation", validate_schema)
    graph.add_node("business_validation", validate_business_rules)
    graph.add_node("valid_handler", lambda s: s)
    graph.add_node("invalid_handler", lambda s: s)

    graph.set_entry_point("schema_validation")
    graph.add_edge("schema_validation", "business_validation")
    graph.add_conditional_edges(
        "business_validation",
        decide_validity,
        {
            "valid": "valid_handler",
            "invalid": "invalid_handler"
        }
    )
    graph.add_edge("valid_handler", END)
    graph.add_edge("invalid_handler", END)

    return graph

# SubGraph Registry에 등록
from .registry import subgraph_registry
subgraph_registry.register("validation_graph", build_validation_graph)
```

### 7.2 RAG SubGraph

```python
# sub_graphs/rag_graph.py
from langgraph.graph import StateGraph, END
from typing import TypedDict, List

class RAGState(TypedDict):
    """RAG State"""
    query: str
    documents: List[dict]
    context: str
    answer: str

def retrieve_documents(state: RAGState) -> RAGState:
    """문서 검색"""
    from ..tools.registry import tool_registry
    vector_search = tool_registry.get("vector_search_tool")
    state["documents"] = vector_search(state["query"])
    return state

def build_context(state: RAGState) -> RAGState:
    """컨텍스트 구성"""
    state["context"] = "\n\n".join([doc["content"] for doc in state["documents"]])
    return state

def generate_answer(state: RAGState) -> RAGState:
    """답변 생성"""
    from ..tools.registry import tool_registry
    llm = tool_registry.get("llm_tool")
    state["answer"] = llm(state["query"], state["context"])
    return state

def build_rag_graph() -> StateGraph:
    """RAG SubGraph 빌드"""
    graph = StateGraph(RAGState)

    graph.add_node("retrieve", retrieve_documents)
    graph.add_node("build_context", build_context)
    graph.add_node("generate", generate_answer)

    graph.set_entry_point("retrieve")
    graph.add_edge("retrieve", "build_context")
    graph.add_edge("build_context", "generate")
    graph.add_edge("generate", END)

    return graph

from .registry import subgraph_registry
subgraph_registry.register("rag_graph", build_rag_graph)
```

---

## 8. Tool 구현 예시

### 8.1 Vector Search Tool

```python
# tools/vector_search_tool.py
from typing import List, Dict
from ..contexts.app_context import get_app_context

def vector_search_tool(
    query: str,
    top_k: int = 5,
    filters: Dict = None
) -> List[Dict]:
    """
    벡터 검색 도구

    Args:
        query: 검색 쿼리
        top_k: 반환할 문서 수
        filters: 필터 조건

    Returns:
        검색된 문서 리스트
    """
    context = get_app_context()
    vector_store = context.vector_store

    results = vector_store.similarity_search(
        query=query,
        k=top_k,
        filter=filters
    )

    return [
        {
            "content": doc.page_content,
            "metadata": doc.metadata,
            "score": doc.score
        }
        for doc in results
    ]

# Tool Registry에 등록
from .registry import tool_registry
tool_registry.register(
    name="vector_search_tool",
    tool_func=vector_search_tool,
    description="벡터 DB에서 유사 문서를 검색합니다",
    parameters={
        "query": {"type": "string", "required": True},
        "top_k": {"type": "integer", "default": 5},
        "filters": {"type": "object", "required": False}
    }
)
```

### 8.2 LLM Tool

```python
# tools/llm_tool.py
from typing import Optional
from langchain_openai import ChatOpenAI
from ..contexts.app_context import get_app_context

def llm_tool(
    prompt: str,
    context: Optional[str] = None,
    model: str = "gpt-4",
    temperature: float = 0.7
) -> str:
    """
    LLM 호출 도구

    Args:
        prompt: 프롬프트
        context: 추가 컨텍스트
        model: 모델명
        temperature: 온도

    Returns:
        LLM 응답
    """
    app_context = get_app_context()

    llm = ChatOpenAI(
        model=model,
        temperature=temperature,
        api_key=app_context.config.openai_api_key
    )

    full_prompt = f"{context}\n\n{prompt}" if context else prompt

    response = llm.invoke(full_prompt)
    return response.content

from .registry import tool_registry
tool_registry.register(
    name="llm_tool",
    tool_func=llm_tool,
    description="LLM을 호출하여 텍스트를 생성합니다",
    parameters={
        "prompt": {"type": "string", "required": True},
        "context": {"type": "string", "required": False},
        "model": {"type": "string", "default": "gpt-4"},
        "temperature": {"type": "number", "default": 0.7}
    }
)
```

---

## 9. Supervisor 통합

### 9.1 Supervisor Router 수정

```python
# supervisor/nodes/router.py
from typing import Dict
from ...agents.registry import agent_registry

def route_to_agent(state: Dict) -> str:
    """
    요청에 따라 적절한 Agent로 라우팅

    Returns:
        선택된 Agent 이름
    """
    intent = state.get("intent", {})
    intent_type = intent.get("type")

    # Intent에 따른 Agent 선택
    agent_mapping = {
        "contract_analysis": "contract_agent",
        "law_search": "law_agent",
        "report_generation": "report_agent",
        "chat": "chat_agent"
    }

    selected_agent = agent_mapping.get(intent_type, "chat_agent")

    # Agent가 등록되어 있는지 확인
    available_agents = agent_registry.list_agents()
    if selected_agent not in available_agents:
        raise ValueError(f"Agent '{selected_agent}' not available")

    return selected_agent
```

### 9.2 Supervisor Executor 수정

```python
# supervisor/nodes/executor.py
from typing import Dict
from ...agents.registry import agent_registry

async def execute_agent(state: Dict) -> Dict:
    """
    선택된 Agent 실행
    """
    agent_name = state.get("selected_agent")

    if not agent_name:
        raise ValueError("No agent selected")

    # Registry에서 Agent 가져오기
    agent = agent_registry.get(agent_name)

    # Agent 실행
    agent_input = {
        "query": state.get("query"),
        "context": state.get("context", {}),
        "user_id": state.get("user_id")
    }

    result = await agent.invoke(agent_input)

    # 결과를 state에 저장
    state["agent_results"] = state.get("agent_results", [])
    state["agent_results"].append({
        "agent": agent_name,
        "result": result
    })

    return state
```

---

## 10. 초기화 및 등록 프로세스

### 10.1 Agent 자동 등록

```python
# agents/__init__.py
from .registry import agent_registry
from .contract_agent.agent import ContractAgent
from .law_agent.agent import LawAgent
from .report_agent.agent import ReportAgent
from .chat_agent.agent import ChatAgent

def register_all_agents():
    """모든 Agent 등록"""
    agents = [
        ("contract_agent", ContractAgent),
        ("law_agent", LawAgent),
        ("report_agent", ReportAgent),
        ("chat_agent", ChatAgent),
    ]

    for name, agent_class in agents:
        agent_registry.register(name, agent_class)

# 자동 등록
register_all_agents()
```

### 10.2 SubGraph 자동 등록

```python
# sub_graphs/__init__.py
from .registry import subgraph_registry

# 각 SubGraph 모듈에서 자동으로 Registry에 등록됨
from . import validation_graph
from . import search_graph
from . import formatting_graph
from . import rag_graph
from . import hitl_graph

def list_available_subgraphs():
    """사용 가능한 SubGraph 목록"""
    return subgraph_registry.list_subgraphs()
```

### 10.3 Tool 자동 등록

```python
# tools/__init__.py
from .registry import tool_registry

# 각 Tool 모듈에서 자동으로 Registry에 등록됨
from . import database_tool
from . import vector_search_tool
from . import llm_tool
from . import text_processing_tool
from . import pdf_tool
from . import validation_tool

def list_available_tools():
    """사용 가능한 Tool 목록"""
    return tool_registry.list_tools()
```

---

## 11. 구현 단계별 플랜

### Phase 1: Registry 및 Base 구조 구축 (Week 1)
1. Registry 시스템 구현 (Agent, SubGraph, Tool)
2. BaseAgent 추상 클래스 구현
3. 공통 State 스키마 정의
4. 디렉토리 구조 생성

### Phase 2: 공유 리소스 구현 (Week 2)
1. SubGraph 구현
   - validation_graph
   - rag_graph
   - search_graph
2. Tool 구현
   - vector_search_tool
   - llm_tool
   - pdf_tool
   - validation_tool

### Phase 3: Agent 구현 (Week 3-4)
1. ContractAgent 구현 및 테스트
2. LawAgent 구현 및 테스트
3. ReportAgent 구현 및 테스트
4. ChatAgent 구현 및 테스트

### Phase 4: Supervisor 통합 (Week 5)
1. Supervisor Router 수정
2. Supervisor Executor 수정
3. Agent 라우팅 로직 구현
4. 통합 테스트

### Phase 5: 최적화 및 문서화 (Week 6)
1. 성능 최적화
2. 에러 핸들링 강화
3. 로깅 및 모니터링
4. API 문서화

---

## 12. 장점 및 기대 효과

### 12.1 장점
1. **모듈화**: 각 Agent가 독립적으로 관리되어 개발 및 유지보수 용이
2. **재사용성**: SubGraph와 Tool을 여러 Agent가 공유하여 중복 최소화
3. **확장성**: 새로운 Agent 추가 시 기존 구조에 영향 없음
4. **성능**: 싱글톤 패턴으로 리소스 효율적 관리
5. **테스트 용이성**: 각 컴포넌트를 독립적으로 테스트 가능

### 12.2 기대 효과
- 개발 속도 향상 (새 Agent 추가 시간 50% 단축)
- 코드 중복 감소 (70% 이상)
- 메모리 사용량 최적화 (싱글톤 패턴)
- 유지보수 비용 절감

---

## 13. 고려사항 및 리스크

### 13.1 주의사항
1. **Registry 초기화**: 애플리케이션 시작 시 모든 Registry 초기화 필요
2. **순환 참조**: Agent ↔ SubGraph ↔ Tool 간 순환 참조 방지
3. **Thread Safety**: Registry의 스레드 안전성 보장
4. **State 전달**: Supervisor ↔ Agent 간 State 형식 일치 필요

### 13.2 리스크 완화
1. **의존성 관리**: 명확한 의존성 그래프 문서화
2. **테스트 커버리지**: 90% 이상 테스트 커버리지 유지
3. **모니터링**: Agent 실행 로그 및 메트릭 수집
4. **Fallback**: Agent 실패 시 Fallback 메커니즘 구현

---

## 14. 다음 단계

1. 현재 문서 검토 및 피드백
2. 상세 설계 문서 작성 (각 Agent별)
3. Phase 1 구현 시작
4. 프로토타입 개발 및 검증

---

## 부록: 참고 자료

- LangGraph 공식 문서: https://langchain-ai.github.io/langgraph/
- Singleton 패턴: https://refactoring.guru/design-patterns/singleton
- Agent 아키텍처 패턴: https://www.patterns.dev/posts/agent-pattern

---

**문서 끝**
