# Agent 구현 계획서 - Phase 2

**작성일**: 2025-11-04
**버전**: 2.0
**프로젝트**: Octo Worker - LangGraph 멀티 에이전트 시스템

---

## 목차

1. [현황 분석](#현황-분석)
2. [구현 목표](#구현-목표)
3. [Phase 1: 레지스트리 시스템 구현](#phase-1-레지스트리-시스템-구현)
4. [Phase 2: 서브그래프 구조 설계](#phase-2-서브그래프-구조-설계)
5. [Phase 3: Swarm 패턴 통합](#phase-3-swarm-패턴-통합)
6. [Phase 4: Context API 완전 통합](#phase-4-context-api-완전-통합)
7. [Phase 5: 실제 Agent 구현](#phase-5-실제-agent-구현)
8. [타임라인 및 우선순위](#타임라인-및-우선순위)
9. [위험 관리](#위험-관리)

---

## 현황 분석

### ✅ 구현 완료

1. **기본 Supervisor Pattern**
   - Intent Understanding → Planning → Executor → Agents → Aggregator
   - Command 기반 동적 라우팅

2. **HITL (Human-in-the-Loop)**
   - `interrupt()` 기반 사용자 승인
   - 완전 구현 완료

3. **AsyncPostgresSaver Checkpointer**
   - CheckpointerManager 싱글톤 패턴
   - 연결 풀링 및 생명주기 관리

4. **State 관리**
   - SupervisorState (TypedDict)
   - TaskStep 구조

5. **Context API (부분)**
   - AppContext 정의
   - 선택적 파라미터로만 사용

### ❌ 미구현 또는 부분 구현

1. **Swarm 패턴**
   - 현재: 단순 Supervisor 패턴만
   - 필요: 에이전트 간 협업 및 동적 전환

2. **서브그래프**
   - 현재: 각 Agent는 단일 노드
   - 필요: Agent별 내부 워크플로우 (StateGraph)

3. **레지스트리 시스템**
   - 현재: registry/ 디렉토리 비어있음
   - 필요: 툴/에이전트 동적 등록 관리

4. **공유 툴/서브에이전트**
   - 현재: tools/, sub_agents/ 비어있음
   - 필요: 공유 컴포넌트 구현

---

## 구현 목표

### 최종 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                    Supervisor (Main Graph)                   │
│                                                               │
│  Intent → Planning → Executor → [Swarm Router] → Aggregator │
│                                        │                      │
└────────────────────────────────────────┼──────────────────────┘
                                         │
                    ┌────────────────────┼─────────────────────┐
                    │                    │                     │
            ┌───────▼──────┐    ┌───────▼──────┐    ┌────────▼──────┐
            │ Search Agent │    │Analysis Agent│    │Document Agent │
            │  (SubGraph)  │    │  (SubGraph)  │    │  (SubGraph)   │
            └───────┬──────┘    └───────┬──────┘    └────────┬──────┘
                    │                   │                     │
         ┌──────────▼──────────┐ ┌──────▼──────┐   ┌─────────▼──────┐
         │ • Retriever (Sub)   │ │ • Validator │   │ • Generator    │
         │ • Reranker (Sub)    │ │ • Analyzer  │   │ • Formatter    │
         │ Tools:              │ │ Tools:      │   │ Tools:         │
         │  - VectorDB         │ │  - Stats    │   │  - Template    │
         │  - WebSearch        │ │  - Chart    │   │  - PDF Export  │
         └─────────────────────┘ └─────────────┘   └────────────────┘
```

### 핵심 기능

1. **레지스트리 패턴**
   - 툴 레지스트리 (싱글톤)
   - 에이전트 레지스트리 (싱글톤)
   - 서브에이전트 레지스트리 (싱글톤)

2. **서브그래프 구조**
   - 각 Agent를 StateGraph로 구현
   - Agent 내부에 다중 노드/엣지
   - 독립적인 State 관리

3. **Swarm 패턴**
   - 에이전트 간 상태 공유
   - 동적 에이전트 전환
   - 협업 메커니즘

4. **Context API**
   - 모든 노드에서 Context 접근
   - LLM, DB 연결 공유
   - 불변 런타임 정보

---

## Phase 1: 레지스트리 시스템 구현

### 목표
에이전트, 툴, 서브에이전트를 동적으로 등록/관리하는 레지스트리 구현

### 구조

```
backend/app/registry/
├── __init__.py
├── base_registry.py          # 기본 레지스트리 클래스
├── tool_registry.py          # 툴 레지스트리 (싱글톤)
├── agent_registry.py         # 에이전트 레지스트리 (싱글톤)
└── sub_agent_registry.py    # 서브에이전트 레지스트리 (싱글톤)
```

### 1.1 기본 레지스트리 클래스

**파일**: `backend/app/registry/base_registry.py`

```python
"""기본 레지스트리 클래스

모든 레지스트리의 부모 클래스
싱글톤 패턴 구현
"""
from typing import Dict, Any, Callable, Optional, TypeVar, Generic
from abc import ABC, abstractmethod


T = TypeVar('T')


class BaseRegistry(ABC, Generic[T]):
    """기본 레지스트리 (싱글톤)

    모든 레지스트리는 이 클래스를 상속받습니다.
    """

    _instances: Dict[str, 'BaseRegistry'] = {}

    def __new__(cls):
        """싱글톤 패턴 구현"""
        if cls.__name__ not in cls._instances:
            instance = super().__new__(cls)
            cls._instances[cls.__name__] = instance
        return cls._instances[cls.__name__]

    def __init__(self):
        """레지스트리 초기화"""
        if not hasattr(self, '_registry'):
            self._registry: Dict[str, T] = {}

    def register(self, name: str, item: T, override: bool = False) -> None:
        """아이템 등록

        Args:
            name: 등록할 이름
            item: 등록할 아이템
            override: 기존 아이템 덮어쓰기 여부

        Raises:
            ValueError: 이미 등록된 이름인 경우 (override=False)
        """
        if name in self._registry and not override:
            raise ValueError(f"'{name}'은 이미 등록되어 있습니다. override=True로 덮어쓰세요.")

        self._registry[name] = item
        print(f"[{self.__class__.__name__}] ✓ '{name}' 등록 완료")

    def get(self, name: str) -> Optional[T]:
        """아이템 조회

        Args:
            name: 조회할 이름

        Returns:
            등록된 아이템 (없으면 None)
        """
        return self._registry.get(name)

    def list_all(self) -> Dict[str, T]:
        """전체 아이템 목록 반환"""
        return self._registry.copy()

    def exists(self, name: str) -> bool:
        """아이템 존재 여부 확인"""
        return name in self._registry

    def unregister(self, name: str) -> bool:
        """아이템 등록 해제

        Args:
            name: 해제할 이름

        Returns:
            성공 여부
        """
        if name in self._registry:
            del self._registry[name]
            print(f"[{self.__class__.__name__}] ✓ '{name}' 등록 해제")
            return True
        return False

    def clear(self) -> None:
        """전체 아이템 삭제"""
        self._registry.clear()
        print(f"[{self.__class__.__name__}] ✓ 전체 아이템 삭제")
```

### 1.2 툴 레지스트리

**파일**: `backend/app/registry/tool_registry.py`

```python
"""Tool Registry

모든 공유 툴을 등록/관리하는 레지스트리
"""
from typing import Callable, Any, Dict
from langchain_core.tools import BaseTool
from backend.app.registry.base_registry import BaseRegistry


class ToolRegistry(BaseRegistry[BaseTool]):
    """툴 레지스트리 (싱글톤)

    사용 예시:
        registry = ToolRegistry()
        registry.register("web_search", web_search_tool)
        tool = registry.get("web_search")
    """

    def register_function(
        self,
        name: str,
        func: Callable,
        description: str = "",
        **kwargs
    ) -> None:
        """함수를 툴로 변환하여 등록

        Args:
            name: 툴 이름
            func: 실행할 함수
            description: 툴 설명
            **kwargs: StructuredTool 추가 인자
        """
        from langchain_core.tools import StructuredTool

        tool = StructuredTool.from_function(
            func=func,
            name=name,
            description=description,
            **kwargs
        )

        self.register(name, tool)


# 전역 인스턴스 (편의 함수)
_tool_registry = ToolRegistry()


def get_tool_registry() -> ToolRegistry:
    """툴 레지스트리 인스턴스 가져오기"""
    return _tool_registry


def register_tool(name: str, tool: BaseTool, override: bool = False) -> None:
    """툴 등록 (편의 함수)"""
    _tool_registry.register(name, tool, override)


def get_tool(name: str) -> BaseTool:
    """툴 조회 (편의 함수)"""
    return _tool_registry.get(name)
```

### 1.3 에이전트 레지스트리

**파일**: `backend/app/registry/agent_registry.py`

```python
"""Agent Registry

모든 에이전트 SubGraph를 등록/관리하는 레지스트리
"""
from typing import Callable, Any
from langgraph.graph import CompiledGraph
from backend.app.registry.base_registry import BaseRegistry


class AgentRegistry(BaseRegistry[CompiledGraph]):
    """에이전트 레지스트리 (싱글톤)

    각 에이전트는 CompiledGraph로 등록됩니다.

    사용 예시:
        registry = AgentRegistry()
        registry.register("search_agent", search_graph)
        agent = registry.get("search_agent")
    """
    pass


# 전역 인스턴스
_agent_registry = AgentRegistry()


def get_agent_registry() -> AgentRegistry:
    """에이전트 레지스트리 인스턴스 가져오기"""
    return _agent_registry


def register_agent(name: str, graph: CompiledGraph, override: bool = False) -> None:
    """에이전트 등록 (편의 함수)"""
    _agent_registry.register(name, graph, override)


def get_agent(name: str) -> CompiledGraph:
    """에이전트 조회 (편의 함수)"""
    return _agent_registry.get(name)
```

### 1.4 서브에이전트 레지스트리

**파일**: `backend/app/registry/sub_agent_registry.py`

```python
"""Sub-Agent Registry

공유 서브에이전트 (Retriever, Reranker 등)를 등록/관리
"""
from typing import Callable, Any
from backend.app.registry.base_registry import BaseRegistry


class SubAgentRegistry(BaseRegistry[Callable]):
    """서브에이전트 레지스트리 (싱글톤)

    서브에이전트는 async 함수로 등록됩니다.

    사용 예시:
        registry = SubAgentRegistry()
        registry.register("retriever", retriever_func)
        sub_agent = registry.get("retriever")
    """
    pass


# 전역 인스턴스
_sub_agent_registry = SubAgentRegistry()


def get_sub_agent_registry() -> SubAgentRegistry:
    """서브에이전트 레지스트리 인스턴스 가져오기"""
    return _sub_agent_registry


def register_sub_agent(name: str, func: Callable, override: bool = False) -> None:
    """서브에이전트 등록 (편의 함수)"""
    _sub_agent_registry.register(name, func, override)


def get_sub_agent(name: str) -> Callable:
    """서브에이전트 조회 (편의 함수)"""
    return _sub_agent_registry.get(name)
```

### 1.5 통합 __init__.py

**파일**: `backend/app/registry/__init__.py`

```python
"""Registry 패키지

에이전트, 툴, 서브에이전트를 동적으로 등록/관리
"""
from backend.app.registry.base_registry import BaseRegistry
from backend.app.registry.tool_registry import (
    ToolRegistry,
    get_tool_registry,
    register_tool,
    get_tool,
)
from backend.app.registry.agent_registry import (
    AgentRegistry,
    get_agent_registry,
    register_agent,
    get_agent,
)
from backend.app.registry.sub_agent_registry import (
    SubAgentRegistry,
    get_sub_agent_registry,
    register_sub_agent,
    get_sub_agent,
)

__all__ = [
    # Base
    "BaseRegistry",

    # Tool
    "ToolRegistry",
    "get_tool_registry",
    "register_tool",
    "get_tool",

    # Agent
    "AgentRegistry",
    "get_agent_registry",
    "register_agent",
    "get_agent",

    # Sub-Agent
    "SubAgentRegistry",
    "get_sub_agent_registry",
    "register_sub_agent",
    "get_sub_agent",
]
```

### 1.6 테스트

**파일**: `tests/test_registry.py`

```python
"""레지스트리 테스트"""
import pytest
from backend.app.registry import (
    get_tool_registry,
    get_agent_registry,
    get_sub_agent_registry,
    register_tool,
    get_tool,
)
from langchain_core.tools import tool


@tool
def dummy_tool(query: str) -> str:
    """더미 툴"""
    return f"Result: {query}"


def test_tool_registry_singleton():
    """툴 레지스트리 싱글톤 테스트"""
    registry1 = get_tool_registry()
    registry2 = get_tool_registry()

    assert registry1 is registry2


def test_tool_registration():
    """툴 등록 테스트"""
    registry = get_tool_registry()
    registry.clear()  # 테스트 격리

    register_tool("dummy", dummy_tool)

    assert registry.exists("dummy")
    retrieved_tool = get_tool("dummy")
    assert retrieved_tool is not None
    assert retrieved_tool.name == "dummy_tool"


def test_duplicate_registration():
    """중복 등록 테스트"""
    registry = get_tool_registry()
    registry.clear()

    register_tool("dummy", dummy_tool)

    # override=False로 중복 등록 시 에러
    with pytest.raises(ValueError):
        register_tool("dummy", dummy_tool, override=False)

    # override=True로 중복 등록 성공
    register_tool("dummy", dummy_tool, override=True)
```

### 소요 시간: 1일

---

## Phase 2: 서브그래프 구조 설계

### 목표
각 Agent를 StateGraph로 구현하여 내부 워크플로우 지원

### 2.1 Agent 서브그래프 구조

```
backend/app/octostrator/agents/
├── __init__.py
├── base_agent.py             # 기본 Agent 클래스
├── search/
│   ├── __init__.py
│   ├── graph.py              # Search Agent SubGraph
│   ├── state.py              # SearchAgentState
│   └── nodes/
│       ├── retriever_node.py
│       └── reranker_node.py
├── analysis/
│   ├── __init__.py
│   ├── graph.py
│   ├── state.py
│   └── nodes/
│       ├── validator_node.py
│       └── analyzer_node.py
└── document/
    ├── __init__.py
    ├── graph.py
    ├── state.py
    └── nodes/
        ├── generator_node.py
        └── formatter_node.py
```

### 2.2 기본 Agent 클래스

**파일**: `backend/app/octostrator/agents/base_agent.py`

```python
"""Base Agent

모든 Agent의 부모 클래스
"""
from abc import ABC, abstractmethod
from typing import Dict, Any
from langgraph.graph import StateGraph, CompiledGraph
from backend.app.octostrator.states.supervisor_state import SupervisorState


class BaseAgent(ABC):
    """기본 Agent 클래스

    모든 Agent는 이 클래스를 상속받습니다.
    """

    def __init__(self, agent_name: str):
        """Agent 초기화

        Args:
            agent_name: Agent 이름
        """
        self.agent_name = agent_name
        self._graph: CompiledGraph = None

    @abstractmethod
    def build_graph(self) -> CompiledGraph:
        """Agent SubGraph 빌드

        각 Agent는 자신의 내부 워크플로우를 정의합니다.

        Returns:
            CompiledGraph: 컴파일된 SubGraph
        """
        pass

    def get_graph(self) -> CompiledGraph:
        """빌드된 그래프 반환

        Returns:
            CompiledGraph: 컴파일된 그래프
        """
        if self._graph is None:
            self._graph = self.build_graph()
        return self._graph

    async def execute(self, state: SupervisorState) -> Dict[str, Any]:
        """Agent 실행 (Supervisor에서 호출)

        Args:
            state: Supervisor State

        Returns:
            업데이트할 state
        """
        graph = self.get_graph()

        # SubGraph 실행
        # Supervisor의 state를 Agent의 state로 변환
        agent_input = self.prepare_input(state)
        result = await graph.ainvoke(agent_input)

        # Agent의 결과를 Supervisor state로 변환
        return self.prepare_output(state, result)

    @abstractmethod
    def prepare_input(self, supervisor_state: SupervisorState) -> Dict[str, Any]:
        """Supervisor State → Agent State 변환

        Args:
            supervisor_state: Supervisor State

        Returns:
            Agent Input
        """
        pass

    @abstractmethod
    def prepare_output(
        self,
        supervisor_state: SupervisorState,
        agent_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Agent 결과 → Supervisor State 변환

        Args:
            supervisor_state: 원본 Supervisor State
            agent_result: Agent 실행 결과

        Returns:
            업데이트할 Supervisor State
        """
        pass
```

### 2.3 Search Agent SubGraph 예시

**파일**: `backend/app/octostrator/agents/search/state.py`

```python
"""Search Agent State"""
from typing import TypedDict, Optional, List


class SearchAgentState(TypedDict, total=False):
    """Search Agent 내부 State

    Attributes:
        query: 검색 쿼리
        raw_results: 원본 검색 결과
        reranked_results: 재정렬된 결과
        final_answer: 최종 답변
    """
    query: str
    raw_results: Optional[List[dict]]
    reranked_results: Optional[List[dict]]
    final_answer: Optional[str]
```

**파일**: `backend/app/octostrator/agents/search/graph.py`

```python
"""Search Agent SubGraph"""
from langgraph.graph import StateGraph, START, END
from backend.app.octostrator.agents.base_agent import BaseAgent
from backend.app.octostrator.agents.search.state import SearchAgentState
from backend.app.octostrator.agents.search.nodes import (
    retriever_node,
    reranker_node,
)


class SearchAgent(BaseAgent):
    """Search Agent

    내부 워크플로우:
    START → retriever → reranker → END
    """

    def __init__(self):
        super().__init__("search")

    def build_graph(self):
        """SubGraph 빌드"""
        workflow = StateGraph(SearchAgentState)

        # 노드 추가
        workflow.add_node("retriever", retriever_node)
        workflow.add_node("reranker", reranker_node)

        # 엣지 추가
        workflow.add_edge(START, "retriever")
        workflow.add_edge("retriever", "reranker")
        workflow.add_edge("reranker", END)

        return workflow.compile()

    def prepare_input(self, supervisor_state):
        """Supervisor State → Search State"""
        plan = supervisor_state["plan"]
        current_step = supervisor_state["current_step"]
        task = plan[current_step]

        return {
            "query": task["description"]
        }

    def prepare_output(self, supervisor_state, agent_result):
        """Search 결과 → Supervisor State"""
        plan = supervisor_state["plan"]
        current_step = supervisor_state["current_step"]

        # 현재 Task 업데이트
        plan[current_step]["status"] = "completed"
        plan[current_step]["result"] = agent_result.get("final_answer", "")

        from langchain_core.messages import AIMessage

        return {
            "plan": plan,
            "current_step": current_step + 1,
            "messages": [AIMessage(content=f"[Search Agent] {agent_result['final_answer']}")]
        }
```

**파일**: `backend/app/octostrator/agents/search/nodes/retriever_node.py`

```python
"""Retriever Node"""
from typing import Dict
from backend.app.octostrator.agents.search.state import SearchAgentState


async def retriever_node(state: SearchAgentState) -> Dict:
    """문서 검색 노드

    TODO: 실제 벡터DB/검색 엔진 연동
    """
    query = state["query"]

    # TODO: 실제 검색 로직 (VectorDB, SQL, Web Search 등)
    raw_results = [
        {"content": f"Search result 1 for: {query}", "score": 0.95},
        {"content": f"Search result 2 for: {query}", "score": 0.87},
        {"content": f"Search result 3 for: {query}", "score": 0.75},
    ]

    return {
        "raw_results": raw_results
    }
```

**파일**: `backend/app/octostrator/agents/search/nodes/reranker_node.py`

```python
"""Reranker Node"""
from typing import Dict
from backend.app.octostrator.agents.search.state import SearchAgentState


async def reranker_node(state: SearchAgentState) -> Dict:
    """검색 결과 재정렬 노드

    TODO: 실제 Reranking 모델 연동 (Cohere, Cross-Encoder 등)
    """
    raw_results = state["raw_results"]

    # TODO: 실제 Reranking 로직
    # 현재는 단순히 score 기준 정렬
    reranked = sorted(raw_results, key=lambda x: x["score"], reverse=True)

    # 최종 답변 생성
    top_result = reranked[0]
    final_answer = f"검색 결과: {top_result['content']} (신뢰도: {top_result['score']:.2f})"

    return {
        "reranked_results": reranked,
        "final_answer": final_answer
    }
```

### 2.4 Agent 등록

**파일**: `backend/app/octostrator/agents/__init__.py`

```python
"""Agents 패키지

모든 Agent SubGraph를 정의하고 레지스트리에 등록
"""
from backend.app.octostrator.agents.search.graph import SearchAgent
from backend.app.registry import register_agent


def register_all_agents():
    """모든 Agent를 레지스트리에 등록"""

    # Search Agent
    search_agent = SearchAgent()
    register_agent("search", search_agent.get_graph(), override=True)

    print("[Agents] ✓ 모든 Agent 등록 완료")


# 자동 등록
register_all_agents()
```

### 2.5 Supervisor에서 SubGraph 호출

**파일**: `backend/app/octostrator/supervisor/nodes/executor.py` (수정)

```python
"""Executor Node (수정)

레지스트리에서 Agent SubGraph를 가져와서 실행
"""
from langgraph.types import Command
from backend.app.registry import get_agent


async def executor_node(state: SupervisorState) -> Command:
    """계획에 따라 Agent 실행"""
    plan = state.get("plan", [])
    current_step = state.get("current_step", 0)

    if current_step >= len(plan):
        return Command(
            update={"is_executing": False},
            goto="aggregator"
        )

    step = plan[current_step]

    # HITL 체크
    if step["agent"] == "hitl":
        return Command(
            update={"is_waiting_human": True},
            goto="hitl_handler"
        )

    # Agent SubGraph 가져오기
    agent_name = step["agent"]
    agent_graph = get_agent(agent_name)

    if agent_graph is None:
        # 등록되지 않은 Agent → 에러
        return Command(
            update={
                "plan": update_step_status(plan, current_step, "failed"),
                "current_step": current_step + 1
            },
            goto="executor"  # 다음 단계로
        )

    # Agent SubGraph 실행
    agent_input = {
        "query": step["description"]
    }

    try:
        result = await agent_graph.ainvoke(agent_input)

        # 성공
        plan[current_step]["status"] = "completed"
        plan[current_step]["result"] = result.get("final_answer", "")

    except Exception as e:
        # 실패
        plan[current_step]["status"] = "failed"
        plan[current_step]["error"] = str(e)

    return Command(
        update={
            "plan": plan,
            "current_step": current_step + 1
        },
        goto="executor"
    )
```

### 소요 시간: 3일

---

## Phase 3: Swarm 패턴 통합

### 목표
에이전트 간 협업 및 동적 전환 메커니즘 구현

### 3.1 Swarm 개념

**Swarm 패턴**은 에이전트가 다른 에이전트에게 작업을 위임하거나 협업하는 패턴입니다.

```
┌──────────────┐
│ Search Agent │ ──► "분석이 필요해요" ──► ┌────────────────┐
└──────────────┘                          │ Analysis Agent │
                                          └────────────────┘
                                                  │
                                                  ▼
                                          "문서 생성해줘"
                                                  │
                                                  ▼
                                          ┌────────────────┐
                                          │ Document Agent │
                                          └────────────────┘
```

### 3.2 Swarm State 확장

**파일**: `backend/app/octostrator/states/swarm_state.py`

```python
"""Swarm State

에이전트 간 협업을 위한 확장 State
"""
from typing import TypedDict, Optional, List, Literal
from backend.app.octostrator.states.supervisor_state import SupervisorState


class SwarmMessage(TypedDict):
    """에이전트 간 메시지

    Attributes:
        from_agent: 발신 에이전트
        to_agent: 수신 에이전트
        message_type: 메시지 타입 (handoff, request, response)
        content: 메시지 내용
    """
    from_agent: str
    to_agent: str
    message_type: Literal["handoff", "request", "response"]
    content: str


class SwarmState(SupervisorState, total=False):
    """Swarm 확장 State

    Attributes:
        swarm_messages: 에이전트 간 메시지 큐
        active_agents: 현재 활성화된 에이전트 목록
        handoff_context: 작업 위임 시 전달할 컨텍스트
    """
    swarm_messages: List[SwarmMessage]
    active_agents: List[str]
    handoff_context: Optional[dict]
```

### 3.3 Swarm Router

**파일**: `backend/app/octostrator/supervisor/nodes/swarm_router.py`

```python
"""Swarm Router

에이전트 간 동적 전환을 관리하는 라우터
"""
from typing import Dict
from langgraph.types import Command
from backend.app.octostrator.states.swarm_state import SwarmState


async def swarm_router_node(state: SwarmState) -> Command:
    """Swarm 라우터

    에이전트 간 메시지를 확인하고 다음 에이전트를 결정합니다.
    """
    swarm_messages = state.get("swarm_messages", [])

    # 처리되지 않은 메시지 확인
    if swarm_messages:
        next_message = swarm_messages[0]

        if next_message["message_type"] == "handoff":
            # 작업 위임
            target_agent = next_message["to_agent"]

            return Command(
                update={
                    "swarm_messages": swarm_messages[1:],  # 메시지 제거
                    "handoff_context": {"reason": next_message["content"]}
                },
                goto=target_agent
            )

    # 기본 플로우: Executor로 복귀
    return Command(goto="executor")
```

### 3.4 Agent에서 Handoff 구현

**파일**: `backend/app/octostrator/agents/base_agent.py` (수정)

```python
"""Base Agent (Handoff 추가)"""

class BaseAgent(ABC):

    def handoff_to(self, target_agent: str, reason: str) -> Dict:
        """다른 에이전트에게 작업 위임

        Args:
            target_agent: 대상 에이전트 이름
            reason: 위임 이유

        Returns:
            SwarmMessage 추가
        """
        return {
            "swarm_messages": [{
                "from_agent": self.agent_name,
                "to_agent": target_agent,
                "message_type": "handoff",
                "content": reason
            }]
        }
```

**사용 예시**: Search Agent가 Analysis Agent에게 위임

```python
# backend/app/octostrator/agents/search/nodes/reranker_node.py

async def reranker_node(state: SearchAgentState) -> Dict:
    # ... 검색 완료 ...

    # 복잡한 분석이 필요하면 Analysis Agent에게 위임
    if needs_analysis:
        return {
            "final_answer": "검색 완료. 분석 에이전트에게 위임합니다.",
            "swarm_handoff": {
                "to_agent": "analysis",
                "reason": "검색 결과에 대한 심층 분석 필요"
            }
        }
```

### 3.5 Supervisor Graph 수정

**파일**: `backend/app/octostrator/supervisor/graph.py` (수정)

```python
# Swarm Router 노드 추가
workflow.add_node("swarm_router", swarm_router_node, ends=["executor", "search", "analysis", "document"])

# Executor → Swarm Router → Agent
workflow.add_edge("executor", "swarm_router")
workflow.add_edge("search", "swarm_router")
workflow.add_edge("analysis", "swarm_router")
workflow.add_edge("document", "swarm_router")
```

### 소요 시간: 2일

---

## Phase 4: Context API 완전 통합

### 목표
모든 노드에서 AppContext 접근 가능하도록 통합

### 4.1 LangGraph 1.0 Context 전파

LangGraph 1.0에서는 `graph.compile(context=...)`로 Context를 전달합니다.

**파일**: `backend/app/octostrator/supervisor/graph.py` (수정)

```python
def build_supervisor_graph(
    context: AppContext,  # 필수로 변경
    checkpointer: Optional[AsyncPostgresSaver] = None
):
    """Supervisor Graph 생성

    Args:
        context: AppContext (필수)
        checkpointer: AsyncPostgresSaver (선택적)
    """
    # Context에서 LLM 가져오기
    llm = context.llm

    # ... 그래프 빌드 ...

    # Context와 함께 컴파일
    if checkpointer is not None:
        return workflow.compile(checkpointer=checkpointer)
    else:
        return workflow.compile()
```

### 4.2 노드에서 Context 접근

**방법 1: LangGraph Context Store (권장)**

```python
# LangGraph 1.0의 Context Store 사용
from langgraph.store import InMemoryStore

# Graph 빌드 시
store = InMemoryStore()
store.put("app_context", context)

graph = workflow.compile(store=store)

# 노드에서 접근
async def some_node(state: State, *, store: BaseStore):
    context = store.get("app_context")
    llm = context.llm
    # ...
```

**방법 2: State에 포함 (간단)**

```python
# SupervisorState에 context 추가
class SupervisorState(TypedDict, total=False):
    # ... 기존 필드 ...
    context: Optional[AppContext]

# 초기 입력 시 전달
result = await graph.ainvoke({
    "messages": [HumanMessage(content="...")],
    "context": context
})

# 노드에서 접근
async def some_node(state: SupervisorState):
    context = state["context"]
    llm = context.llm
    # ...
```

### 4.3 Agent SubGraph에 Context 전파

**파일**: `backend/app/octostrator/agents/base_agent.py` (수정)

```python
class BaseAgent(ABC):

    def __init__(self, agent_name: str, context: AppContext):
        self.agent_name = agent_name
        self.context = context  # Context 저장
        self._graph: CompiledGraph = None

    async def execute(self, state: SupervisorState) -> Dict[str, Any]:
        graph = self.get_graph()

        agent_input = self.prepare_input(state)

        # Context를 Agent State에 전달
        agent_input["context"] = self.context

        result = await graph.ainvoke(agent_input)
        return self.prepare_output(state, result)
```

### 소요 시간: 1일

---

## Phase 5: 실제 Agent 구현

### 목표
실제 비즈니스 로직을 가진 Agent 구현

### 5.1 우선순위 Agent

1. **Search Agent** (가장 자주 사용)
   - VectorDB 연동 (Pinecone, Chroma, Qdrant)
   - Web Search (Tavily, SerpAPI)
   - SQL 검색

2. **Analysis Agent**
   - 데이터 분석
   - 통계 계산
   - 인사이트 추출

3. **Document Agent**
   - 보고서 생성
   - Markdown/PDF 변환
   - 템플릿 기반 문서 생성

### 5.2 공유 툴 구현

**파일**: `backend/app/octostrator/tools/web_search_tool.py`

```python
"""Web Search Tool"""
from langchain_core.tools import tool
from backend.app.registry import register_tool


@tool
async def web_search(query: str, num_results: int = 5) -> list:
    """웹 검색 툴

    Args:
        query: 검색 쿼리
        num_results: 결과 개수

    Returns:
        검색 결과 리스트
    """
    # TODO: Tavily, SerpAPI 등 실제 검색 API 연동
    return [
        {"title": f"Result {i+1}", "url": f"https://example.com/{i}", "snippet": query}
        for i in range(num_results)
    ]


# 자동 등록
register_tool("web_search", web_search)
```

### 5.3 공유 서브에이전트 구현

**파일**: `backend/app/octostrator/sub_agents/retriever.py`

```python
"""Retriever Sub-Agent"""
from typing import List, Dict
from backend.app.registry import register_sub_agent


async def retriever_sub_agent(query: str, top_k: int = 5) -> List[Dict]:
    """문서 검색 서브에이전트

    Args:
        query: 검색 쿼리
        top_k: 상위 K개 결과

    Returns:
        검색 결과
    """
    # TODO: VectorDB 연동 (Pinecone, Chroma, Qdrant)
    return [
        {"content": f"Document {i+1}: {query}", "score": 0.9 - i*0.1}
        for i in range(top_k)
    ]


# 자동 등록
register_sub_agent("retriever", retriever_sub_agent)
```

### 소요 시간: 5일 (Agent당 1-2일)

---

## 타임라인 및 우선순위

### 전체 일정: 약 12일

| Phase | 작업 | 소요 시간 | 우선순위 |
|-------|------|-----------|----------|
| Phase 1 | 레지스트리 시스템 구현 | 1일 | 최우선 |
| Phase 2 | 서브그래프 구조 설계 | 3일 | 높음 |
| Phase 3 | Swarm 패턴 통합 | 2일 | 중간 |
| Phase 4 | Context API 완전 통합 | 1일 | 높음 |
| Phase 5 | 실제 Agent 구현 | 5일 | 중간 |

### 권장 순서

1. **Week 1**
   - Day 1: Phase 1 (레지스트리)
   - Day 2-4: Phase 2 (서브그래프)
   - Day 5: Phase 4 (Context API)

2. **Week 2**
   - Day 6-7: Phase 3 (Swarm 패턴)
   - Day 8-12: Phase 5 (실제 Agent 구현)

---

## 위험 관리

### 기술적 위험

1. **LangGraph 1.0 호환성**
   - **위험**: 버전 업데이트 시 API 변경
   - **완화**: 공식 문서 참조, 테스트 작성

2. **서브그래프 성능**
   - **위험**: 중첩 그래프로 인한 성능 저하
   - **완화**: 벤치마크 테스트, 최적화

3. **Swarm 무한 루프**
   - **위험**: Agent 간 순환 위임
   - **완화**: 최대 depth 제한, 순환 감지

### 구현 위험

1. **복잡도 증가**
   - **위험**: 코드베이스가 너무 복잡해질 수 있음
   - **완화**: 단계별 구현, 문서화 철저

2. **테스트 부족**
   - **위험**: 통합 테스트 없이 진행
   - **완화**: 각 Phase마다 테스트 작성

---

## 검증 체크리스트

### Phase 1 완료 기준
- [ ] ToolRegistry 싱글톤 동작
- [ ] AgentRegistry 싱글톤 동작
- [ ] SubAgentRegistry 싱글톤 동작
- [ ] 테스트 통과 (test_registry.py)

### Phase 2 완료 기준
- [ ] SearchAgent SubGraph 동작
- [ ] Agent별 State 정의
- [ ] Supervisor에서 SubGraph 호출 가능
- [ ] 테스트 통과 (test_search_agent.py)

### Phase 3 완료 기준
- [ ] SwarmState 정의
- [ ] SwarmRouter 동작
- [ ] Agent 간 handoff 가능
- [ ] 순환 위임 방지 로직

### Phase 4 완료 기준
- [ ] 모든 노드에서 Context 접근 가능
- [ ] Context가 SubGraph에 전파됨
- [ ] LLM, DB 연결 공유

### Phase 5 완료 기준
- [ ] 최소 3개 Agent 구현 (Search, Analysis, Document)
- [ ] 최소 3개 공유 툴 구현
- [ ] 최소 2개 서브에이전트 구현
- [ ] E2E 테스트 통과

---

## 참고 문서

- [LangGraph 1.0 Documentation](https://python.langchain.com/docs/langgraph)
- [LangGraph Supervisor Pattern](https://langchain-ai.github.io/langgraph/tutorials/multi_agent/multi-agent-collaboration/)
- [LangGraph Swarm Pattern](https://langchain-ai.github.io/langgraph/tutorials/multi_agent/agent-swarm/)
- [Context Management Report](../context_management/langgraph_context_analysis.md)

---

## 다음 단계

계획서 승인 후:
1. Phase 1부터 순차적으로 구현 시작
2. 각 Phase마다 리뷰 및 테스트
3. 완료 후 다음 Phase로 진행

**시작 준비 완료!**
