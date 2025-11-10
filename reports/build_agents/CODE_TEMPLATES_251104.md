# Agent 시스템 코드 템플릿

**작성일**: 2025-11-04
**용도**: 복사하여 바로 사용 가능한 코드 템플릿 모음

---

## 1. Registry 템플릿

### 1.1 Agent Registry

```python
# backend/app/octostrator/agents/registry.py

from typing import Dict, Type, Optional
from threading import Lock
from .base.agent_base import BaseAgent

class AgentRegistry:
    """
    Agent Registry - Singleton Pattern

    모든 Agent를 중앙에서 관리하며, Lazy Initialization을 통해
    필요할 때만 Agent 인스턴스를 생성합니다.
    """

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
        """
        Agent 클래스 등록

        Args:
            name: Agent 식별자
            agent_class: Agent 클래스 (BaseAgent 상속)
        """
        if not issubclass(agent_class, BaseAgent):
            raise TypeError(f"{agent_class} must inherit from BaseAgent")

        self._agent_classes[name] = agent_class
        print(f"[Registry] Agent '{name}' registered")

    def get(self, name: str, **kwargs) -> BaseAgent:
        """
        Agent 인스턴스 가져오기

        Args:
            name: Agent 식별자
            **kwargs: Agent 초기화 파라미터

        Returns:
            Agent 인스턴스
        """
        if name not in self._agents:
            if name not in self._agent_classes:
                raise ValueError(
                    f"Agent '{name}' not registered. "
                    f"Available agents: {self.list_agents()}"
                )

            # Lazy Initialization
            self._agents[name] = self._agent_classes[name](**kwargs)
            print(f"[Registry] Agent '{name}' instantiated")

        return self._agents[name]

    def list_agents(self) -> list[str]:
        """등록된 Agent 목록 반환"""
        return list(self._agent_classes.keys())

    def is_registered(self, name: str) -> bool:
        """Agent 등록 여부 확인"""
        return name in self._agent_classes

    def clear(self) -> None:
        """Registry 초기화 (테스트용)"""
        self._agents.clear()
        self._agent_classes.clear()


# 전역 싱글톤 인스턴스
agent_registry = AgentRegistry()
```

### 1.2 SubGraph Registry

```python
# backend/app/octostrator/sub_graphs/registry.py

from typing import Dict, Callable, Optional, Any
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

    def register(self, name: str, builder: Callable[..., StateGraph]) -> None:
        """
        SubGraph Builder 등록

        Args:
            name: SubGraph 식별자
            builder: SubGraph를 생성하는 함수
        """
        self._subgraph_builders[name] = builder
        print(f"[Registry] SubGraph '{name}' registered")

    def get(self, name: str, use_cache: bool = True, **kwargs) -> StateGraph:
        """
        SubGraph 가져오기

        Args:
            name: SubGraph 식별자
            use_cache: 캐시 사용 여부
            **kwargs: SubGraph Builder 파라미터

        Returns:
            StateGraph 인스턴스
        """
        cache_key = f"{name}_{hash(frozenset(kwargs.items()))}"

        if use_cache and cache_key in self._subgraph_cache:
            return self._subgraph_cache[cache_key]

        if name not in self._subgraph_builders:
            raise ValueError(
                f"SubGraph '{name}' not registered. "
                f"Available subgraphs: {self.list_subgraphs()}"
            )

        # SubGraph 빌드
        subgraph = self._subgraph_builders[name](**kwargs)

        if use_cache:
            self._subgraph_cache[cache_key] = subgraph

        return subgraph

    def list_subgraphs(self) -> list[str]:
        """등록된 SubGraph 목록"""
        return list(self._subgraph_builders.keys())

    def clear_cache(self) -> None:
        """캐시 초기화"""
        self._subgraph_cache.clear()


# 전역 인스턴스
subgraph_registry = SubGraphRegistry()
```

### 1.3 Tool Registry

```python
# backend/app/octostrator/tools/registry.py

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
        """
        Tool 함수 등록

        Args:
            name: Tool 식별자
            tool_func: Tool 함수
            description: Tool 설명
            parameters: Tool 파라미터 스키마
        """
        self._tools[name] = tool_func
        self._tool_metadata[name] = {
            "description": description,
            "parameters": parameters or {},
            "function": tool_func.__name__
        }
        print(f"[Registry] Tool '{name}' registered")

    def get(self, name: str) -> Callable:
        """
        Tool 함수 가져오기

        Args:
            name: Tool 식별자

        Returns:
            Tool 함수
        """
        if name not in self._tools:
            raise ValueError(
                f"Tool '{name}' not registered. "
                f"Available tools: {self.list_tools()}"
            )
        return self._tools[name]

    def get_metadata(self, name: str) -> Dict[str, Any]:
        """Tool 메타데이터 가져오기"""
        return self._tool_metadata.get(name, {})

    def list_tools(self) -> list[str]:
        """등록된 Tool 목록"""
        return list(self._tools.keys())

    def get_all_metadata(self) -> Dict[str, Dict[str, Any]]:
        """모든 Tool의 메타데이터"""
        return self._tool_metadata.copy()


# 전역 인스턴스
tool_registry = ToolRegistry()
```

---

## 2. Base Agent 템플릿

### 2.1 Agent Config

```python
# backend/app/octostrator/agents/base/agent_config.py

from pydantic import BaseModel, Field
from typing import List, Optional

class AgentConfig(BaseModel):
    """Agent 설정 스키마"""

    name: str = Field(..., description="Agent 이름")
    description: str = Field(..., description="Agent 설명")

    # LLM 설정
    llm_model: str = Field(default="gpt-4", description="사용할 LLM 모델")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="LLM temperature")
    max_tokens: int = Field(default=2000, gt=0, description="최대 토큰 수")

    # 의존성
    tools: List[str] = Field(default_factory=list, description="사용할 Tool 목록")
    subgraphs: List[str] = Field(default_factory=list, description="사용할 SubGraph 목록")

    # 선택적 설정
    timeout: Optional[int] = Field(default=300, description="실행 타임아웃 (초)")
    retry_count: int = Field(default=3, ge=0, description="재시도 횟수")

    class Config:
        frozen = True  # Immutable
```

### 2.2 Base Agent

```python
# backend/app/octostrator/agents/base/agent_base.py

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Callable
from langgraph.graph import StateGraph
from .agent_config import AgentConfig

class BaseAgent(ABC):
    """
    Base Agent 추상 클래스

    모든 Agent는 이 클래스를 상속받아야 합니다.
    """

    def __init__(self, config: AgentConfig):
        self.config = config
        self.graph: Optional[StateGraph] = None
        self._compiled_graph = None

    @abstractmethod
    def build_graph(self) -> StateGraph:
        """
        Agent Graph 구성 (각 Agent에서 구현 필요)

        Returns:
            StateGraph 인스턴스
        """
        pass

    @abstractmethod
    def get_state_schema(self) -> type:
        """
        State Schema 반환 (각 Agent에서 구현 필요)

        Returns:
            State TypedDict 클래스
        """
        pass

    def compile(self, checkpointer=None) -> Any:
        """
        Graph 컴파일

        Args:
            checkpointer: Checkpointer 인스턴스 (선택)

        Returns:
            컴파일된 Graph
        """
        if self._compiled_graph is None:
            self.graph = self.build_graph()
            self._compiled_graph = self.graph.compile(checkpointer=checkpointer)
        return self._compiled_graph

    async def invoke(self, input_data: Dict, config: Optional[Dict] = None):
        """
        Agent 실행 (단일 호출)

        Args:
            input_data: 입력 데이터
            config: 실행 설정

        Returns:
            실행 결과
        """
        compiled = self.compile()
        return await compiled.ainvoke(input_data, config=config)

    async def stream(self, input_data: Dict, config: Optional[Dict] = None):
        """
        Agent 스트림 실행

        Args:
            input_data: 입력 데이터
            config: 실행 설정

        Yields:
            실행 결과 청크
        """
        compiled = self.compile()
        async for chunk in compiled.astream(input_data, config=config):
            yield chunk

    def get_tools(self) -> List[Callable]:
        """
        Agent가 사용하는 Tool 리스트

        Returns:
            Tool 함수 리스트
        """
        from ...tools.registry import tool_registry
        return [tool_registry.get(tool_name) for tool_name in self.config.tools]

    def get_subgraphs(self) -> Dict[str, StateGraph]:
        """
        Agent가 사용하는 SubGraph 리스트

        Returns:
            SubGraph 딕셔너리
        """
        from ...sub_graphs.registry import subgraph_registry
        return {
            name: subgraph_registry.get(name)
            for name in self.config.subgraphs
        }

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(name='{self.config.name}')>"
```

---

## 3. Agent 구현 템플릿

### 3.1 Agent State 템플릿

```python
# backend/app/octostrator/agents/<agent_name>/state.py

from typing import TypedDict, Annotated, List
from operator import add

class <AgentName>State(TypedDict):
    """
    <AgentName> State Schema

    Attributes:
        query: 사용자 질의
        result: 처리 결과
        metadata: 메타데이터
        errors: 에러 목록 (누적)
    """
    # 필수 필드
    query: str
    result: dict

    # 선택 필드
    metadata: dict

    # 누적 필드 (Annotated with add operator)
    errors: Annotated[List[str], add]
```

### 3.2 Agent Node 템플릿

```python
# backend/app/octostrator/agents/<agent_name>/nodes/<node_name>.py

from typing import Dict
from ..state import <AgentName>State
from ....tools.registry import tool_registry

def <node_name>(state: <AgentName>State) -> <AgentName>State:
    """
    노드 설명

    Args:
        state: 현재 State

    Returns:
        업데이트된 State
    """
    try:
        # Tool 가져오기 (필요 시)
        tool = tool_registry.get("<tool_name>")

        # 로직 구현
        result = tool(state["query"])

        # State 업데이트
        state["result"] = result

        return state

    except Exception as e:
        # 에러 처리
        state["errors"].append(str(e))
        return state
```

### 3.3 Agent 클래스 템플릿

```python
# backend/app/octostrator/agents/<agent_name>/agent.py

from typing import Dict
from langgraph.graph import StateGraph, END
from ..base.agent_base import BaseAgent, AgentConfig
from .state import <AgentName>State
from .nodes.<node1> import <node1_func>
from .nodes.<node2> import <node2_func>

class <AgentName>Agent(BaseAgent):
    """
    <AgentName> Agent

    목적: [Agent의 역할 설명]
    """

    def __init__(self):
        config = AgentConfig(
            name="<agent_name>",
            description="[Agent 설명]",
            llm_model="gpt-4",
            temperature=0.7,
            tools=["<tool1>", "<tool2>"],
            subgraphs=["<subgraph1>"]
        )
        super().__init__(config)

    def get_state_schema(self) -> type:
        return <AgentName>State

    def build_graph(self) -> StateGraph:
        """Agent Graph 구성"""

        # Graph 초기화
        graph = StateGraph(<AgentName>State)

        # Nodes 추가
        graph.add_node("<node1>", <node1_func>)
        graph.add_node("<node2>", <node2_func>)

        # SubGraph 통합 (필요 시)
        subgraphs = self.get_subgraphs()
        if "<subgraph1>" in subgraphs:
            graph.add_node("<subgraph1>", subgraphs["<subgraph1>"])

        # Edges 정의
        graph.set_entry_point("<node1>")
        graph.add_edge("<node1>", "<node2>")
        graph.add_edge("<node2>", END)

        # 조건부 라우팅 (필요 시)
        # graph.add_conditional_edges(
        #     "<node>",
        #     self._decide_next,
        #     {
        #         "option1": "<next_node1>",
        #         "option2": "<next_node2>"
        #     }
        # )

        return graph

    def _decide_next(self, state: <AgentName>State) -> str:
        """조건부 라우팅 로직 (필요 시)"""
        # 로직 구현
        return "option1"
```

### 3.4 Agent 등록 템플릿

```python
# backend/app/octostrator/agents/__init__.py

from .registry import agent_registry

# Agent Import
from .contract_agent.agent import ContractAgent
from .law_agent.agent import LawAgent
from .report_agent.agent import ReportAgent
from .chat_agent.agent import ChatAgent

def register_all_agents():
    """모든 Agent 자동 등록"""

    agents = [
        ("contract_agent", ContractAgent),
        ("law_agent", LawAgent),
        ("report_agent", ReportAgent),
        ("chat_agent", ChatAgent),
    ]

    for name, agent_class in agents:
        agent_registry.register(name, agent_class)

# 모듈 임포트 시 자동 등록
register_all_agents()

__all__ = [
    "agent_registry",
    "register_all_agents",
    "ContractAgent",
    "LawAgent",
    "ReportAgent",
    "ChatAgent",
]
```

---

## 4. SubGraph 구현 템플릿

```python
# backend/app/octostrator/sub_graphs/<subgraph_name>.py

from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated
from operator import add

# State 정의
class <SubGraphName>State(TypedDict):
    """<SubGraphName> State"""
    input_data: dict
    output_data: dict
    errors: Annotated[list, add]

# 노드 함수들
def <node1>(state: <SubGraphName>State) -> <SubGraphName>State:
    """노드 1 로직"""
    # 구현
    return state

def <node2>(state: <SubGraphName>State) -> <SubGraphName>State:
    """노드 2 로직"""
    # 구현
    return state

# 조건부 라우팅 (필요 시)
def decide_next(state: <SubGraphName>State) -> str:
    """다음 노드 결정"""
    # 로직
    return "next_node"

# SubGraph Builder
def build_<subgraph_name>_graph(**kwargs) -> StateGraph:
    """
    <SubGraphName> SubGraph 빌드

    Args:
        **kwargs: 설정 파라미터

    Returns:
        StateGraph 인스턴스
    """
    graph = StateGraph(<SubGraphName>State)

    # Nodes
    graph.add_node("<node1>", <node1>)
    graph.add_node("<node2>", <node2>)

    # Edges
    graph.set_entry_point("<node1>")
    graph.add_edge("<node1>", "<node2>")
    graph.add_edge("<node2>", END)

    return graph

# Registry 등록
from .registry import subgraph_registry
subgraph_registry.register(
    "<subgraph_name>",
    build_<subgraph_name>_graph
)
```

---

## 5. Tool 구현 템플릿

```python
# backend/app/octostrator/tools/<tool_name>_tool.py

from typing import Dict, Any, Optional
from ..contexts.app_context import get_app_context

def <tool_name>_tool(
    param1: str,
    param2: Optional[int] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Tool 설명

    Args:
        param1: 파라미터 1 설명
        param2: 파라미터 2 설명 (선택)
        **kwargs: 추가 파라미터

    Returns:
        처리 결과 딕셔너리

    Raises:
        ValueError: 유효하지 않은 입력
        RuntimeError: 실행 오류
    """
    try:
        # App Context 가져오기 (필요 시)
        context = get_app_context()

        # 로직 구현
        result = {
            "status": "success",
            "data": {},
            "metadata": {}
        }

        return result

    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "data": None
        }

# Registry 등록
from .registry import tool_registry

tool_registry.register(
    name="<tool_name>",
    tool_func=<tool_name>_tool,
    description="Tool 설명",
    parameters={
        "param1": {
            "type": "string",
            "required": True,
            "description": "파라미터 1 설명"
        },
        "param2": {
            "type": "integer",
            "required": False,
            "default": None,
            "description": "파라미터 2 설명"
        }
    }
)
```

---

## 6. Supervisor 통합 템플릿

### 6.1 Router 수정

```python
# backend/app/octostrator/supervisor/nodes/router.py

from typing import Dict
from ...agents.registry import agent_registry

def route_to_agent(state: Dict) -> str:
    """
    Intent에 따라 Agent 선택

    Args:
        state: Supervisor State

    Returns:
        선택된 Agent 이름
    """
    intent = state.get("intent", {})
    intent_type = intent.get("type")

    # Intent → Agent 매핑
    agent_mapping = {
        "contract_analysis": "contract_agent",
        "law_search": "law_agent",
        "report_generation": "report_agent",
        "chat": "chat_agent"
    }

    selected_agent = agent_mapping.get(intent_type, "chat_agent")

    # 유효성 검증
    if not agent_registry.is_registered(selected_agent):
        available = agent_registry.list_agents()
        raise ValueError(
            f"Agent '{selected_agent}' not registered. "
            f"Available: {available}"
        )

    # State 업데이트
    state["selected_agent"] = selected_agent

    return selected_agent
```

### 6.2 Executor 수정

```python
# backend/app/octostrator/supervisor/nodes/executor.py

from typing import Dict
from ...agents.registry import agent_registry
import asyncio

async def execute_agent(state: Dict) -> Dict:
    """
    선택된 Agent 실행

    Args:
        state: Supervisor State

    Returns:
        업데이트된 State
    """
    agent_name = state.get("selected_agent")

    if not agent_name:
        raise ValueError("No agent selected")

    try:
        # Registry에서 Agent 가져오기
        agent = agent_registry.get(agent_name)

        # Agent 입력 데이터 구성
        agent_input = {
            "query": state.get("query"),
            "context": state.get("context", {}),
            "user_id": state.get("user_id"),
            "session_id": state.get("session_id")
        }

        # Agent 실행 (타임아웃 설정)
        timeout = agent.config.timeout or 300
        result = await asyncio.wait_for(
            agent.invoke(agent_input),
            timeout=timeout
        )

        # 결과 저장
        agent_results = state.get("agent_results", [])
        agent_results.append({
            "agent": agent_name,
            "result": result,
            "status": "success"
        })
        state["agent_results"] = agent_results

    except asyncio.TimeoutError:
        state.setdefault("errors", []).append(
            f"Agent '{agent_name}' timed out"
        )
    except Exception as e:
        state.setdefault("errors", []).append(
            f"Agent '{agent_name}' error: {str(e)}"
        )

    return state
```

---

## 7. 테스트 템플릿

### 7.1 Agent 단위 테스트

```python
# tests/test_agents/test_<agent_name>.py

import pytest
from backend.app.octostrator.agents.<agent_name>.agent import <AgentName>Agent
from backend.app.octostrator.agents.<agent_name>.state import <AgentName>State

@pytest.fixture
def agent():
    """Agent fixture"""
    return <AgentName>Agent()

@pytest.mark.asyncio
async def test_agent_invoke(agent):
    """Agent invoke 테스트"""

    input_data = {
        "query": "테스트 쿼리",
        "metadata": {}
    }

    result = await agent.invoke(input_data)

    assert result is not None
    assert "result" in result
    assert isinstance(result["errors"], list)

@pytest.mark.asyncio
async def test_agent_error_handling(agent):
    """Agent 에러 처리 테스트"""

    input_data = {
        "query": "",  # 잘못된 입력
        "metadata": {}
    }

    result = await agent.invoke(input_data)

    assert len(result["errors"]) > 0
```

### 7.2 Registry 테스트

```python
# tests/test_registry.py

import pytest
from backend.app.octostrator.agents.registry import AgentRegistry, agent_registry

def test_singleton_pattern():
    """Singleton 패턴 검증"""
    registry1 = AgentRegistry()
    registry2 = AgentRegistry()

    assert registry1 is registry2
    assert registry1 is agent_registry

def test_register_and_get():
    """등록 및 조회 테스트"""
    from backend.app.octostrator.agents.chat_agent.agent import ChatAgent

    agent_registry.clear()
    agent_registry.register("test_agent", ChatAgent)

    assert "test_agent" in agent_registry.list_agents()

    agent = agent_registry.get("test_agent")
    assert isinstance(agent, ChatAgent)
```

---

## 8. 사용 예시

### 8.1 새 Agent 추가 프로세스

```bash
# 1. 디렉토리 생성
mkdir -p backend/app/octostrator/agents/my_agent/nodes

# 2. 파일 생성
touch backend/app/octostrator/agents/my_agent/__init__.py
touch backend/app/octostrator/agents/my_agent/agent.py
touch backend/app/octostrator/agents/my_agent/state.py
touch backend/app/octostrator/agents/my_agent/prompts.py
touch backend/app/octostrator/agents/my_agent/nodes/__init__.py
touch backend/app/octostrator/agents/my_agent/nodes/process.py

# 3. 템플릿 코드 복사 후 수정

# 4. agents/__init__.py에 등록 추가
```

### 8.2 Agent 사용 예시

```python
# 애플리케이션 코드에서 Agent 사용

from backend.app.octostrator.agents.registry import agent_registry

async def process_user_request(user_query: str):
    """사용자 요청 처리"""

    # Agent 가져오기
    agent = agent_registry.get("contract_agent")

    # 입력 데이터 구성
    input_data = {
        "query": user_query,
        "metadata": {"user_id": "123"}
    }

    # Agent 실행
    result = await agent.invoke(input_data)

    return result
```

---

**템플릿 사용 가이드**

1. 필요한 템플릿을 복사하여 사용
2. `<placeholder>` 부분을 실제 이름으로 변경
3. 주석을 참고하여 로직 구현
4. 테스트 코드 작성
5. Registry에 등록

**문서 끝**
