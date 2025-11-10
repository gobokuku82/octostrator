# Registry 레퍼런스 비교 분석 및 통합 계획

**프로젝트**: AI PTmanager - Beta v0.01
**작성일**: 2025-11-04
**버전**: 1.0
**비교 대상**: 레퍼런스 service_agent vs 현재 Octostrator 구조

---

## 📋 Executive Summary

### 핵심 발견

**레퍼런스 구조는 속도 향상을 위한 다음 메커니즘을 제공합니다:**

| 메커니즘 | 설명 | 속도 향상 효과 |
|---------|------|--------------|
| **Agent 인스턴스 캐싱** | `initialize_all()`로 사전 생성 | ⚡ 실행 시 인스턴스화 시간 제거 |
| **메타데이터 기반 검색** | Capabilities로 빠른 Agent 발견 | ⚡ O(1) 검색 |
| **Priority 정렬** | 중요한 Agent 우선 실행 | ⚡ 병렬 처리 최적화 |
| **Enabled/Disabled 플래그** | 불필요한 Agent 스킵 | ⚡ 불필요한 실행 제거 |
| **Team 기반 분류** | 관련 Agent만 조회 | ⚡ 검색 범위 축소 |
| **Adapter 패턴** | 동적 Agent 실행 | ⚡ 런타임 유연성 |

### 통합 전략

**✅ 채택할 것**:
1. Agent 메타데이터 (Capabilities, Priority)
2. Team 기반 분류
3. Enabled/Disabled 플래그
4. Adapter 패턴 (동적 실행)

**❌ 채택 안 할 것**:
1. 전통적 싱글톤 Registry (LangGraph 철학 위배)
2. Agent 클래스 인스턴스화 (Stateless 선호)

**🔄 절충안**:
- Registry는 메타데이터만 저장
- LangGraph Node는 그대로 유지
- Adapter로 메타데이터와 Node 연결

---

## 1. 레퍼런스 구조 분석

### 1.1 AgentRegistry 구조

**파일**: `foundation/agent_registry.py` (369줄)

```python
class AgentRegistry:
    """싱글톤 패턴의 중앙 Registry"""

    _instance = None
    _agents: Dict[str, AgentMetadata] = {}
    _teams: Dict[str, List[str]] = {}
    _initialization_hooks: List[Callable] = []

    def __new__(cls):
        """싱글톤 구현"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def register(cls, name: str, agent_class: Type, ...):
        """Agent 등록"""
        metadata = AgentMetadata(
            agent_class=agent_class,
            team=team,
            capabilities=capabilities,
            priority=priority,
            enabled=enabled
        )
        cls._agents[name] = metadata

    @classmethod
    def create_agent(cls, name: str, **kwargs):
        """Agent 인스턴스 생성"""
        metadata = cls._agents.get(name)
        return metadata.agent_class(**kwargs)

    @classmethod
    def initialize_all(cls, **kwargs):
        """모든 Agent 사전 인스턴스화 ⚡"""
        initialized_agents = {}
        for name in cls.list_agents(enabled_only=True):
            agent = cls.create_agent(name, **kwargs)
            if agent:
                initialized_agents[name] = agent
        return initialized_agents
```

**핵심 특징**:
- ✅ **Agent 인스턴스 캐싱**: `initialize_all()`로 사전 생성
- ✅ **메타데이터 관리**: AgentMetadata + AgentCapabilities
- ✅ **Team 분류**: `_teams` Dict로 그룹핑
- ✅ **Priority 정렬**: 우선순위 순으로 반환
- ✅ **동적 생성**: `create_agent()` 팩토리 메서드

### 1.2 AgentMetadata 구조

```python
class AgentMetadata:
    """Agent 메타데이터"""

    def __init__(
        self,
        agent_class: Type,
        team: Optional[str] = None,
        capabilities: Optional[AgentCapabilities] = None,
        priority: int = 0,
        enabled: bool = True
    ):
        self.agent_class = agent_class
        self.team = team
        self.capabilities = capabilities
        self.priority = priority
        self.enabled = enabled
```

**메타데이터 필드**:
- `agent_class`: Agent 클래스 (Type)
- `team`: 소속 팀 (search, analysis, document)
- `capabilities`: 능력 정의
- `priority`: 실행 우선순위 (높을수록 먼저)
- `enabled`: 활성화 여부

### 1.3 AgentCapabilities 구조

```python
class AgentCapabilities:
    """Agent 능력 정의"""

    def __init__(
        self,
        name: str,
        description: str,
        input_types: List[str],
        output_types: List[str],
        required_tools: List[str] = None,
        team: str = None
    ):
        self.name = name
        self.description = description
        self.input_types = input_types
        self.output_types = output_types
        self.required_tools = required_tools or []
        self.team = team
```

**사용 예시**:
```python
capabilities = AgentCapabilities(
    name="search_team",
    description="법률, 부동산, 대출 정보를 검색하는 팀",
    input_types=["query", "keywords"],
    output_types=["legal_search", "real_estate_search", "loan_search"],
    required_tools=["legal_search_tool", "real_estate_search_tool"],
    team="search"
)
```

### 1.4 AgentAdapter 패턴

**파일**: `foundation/agent_adapter.py` (275줄)

```python
class AgentAdapter:
    """기존 Agent를 Registry에 통합"""

    @staticmethod
    def register_existing_agents():
        """팀/에이전트를 Placeholder로 등록"""

        # Placeholder 클래스 생성 (실제 구현 없음)
        class SearchTeamPlaceholder:
            pass

        # 메타데이터만 등록
        AgentRegistry.register(
            name="search_team",
            agent_class=SearchTeamPlaceholder,
            team="search",
            capabilities=capabilities,
            priority=10,
            enabled=True
        )

    @staticmethod
    async def execute_agent_dynamic(
        agent_name: str,
        input_data: Dict[str, Any],
        llm_context: Optional[Any] = None
    ):
        """Registry를 통한 동적 실행"""

        # 1. Registry에서 클래스 조회
        agent_class = AgentRegistry.get_agent_class(agent_name)

        # 2. 인스턴스 생성
        if agent_name in ["search_agent", "analysis_agent"]:
            agent = agent_class(llm_context=llm_context)
        else:
            agent = agent_class()

        # 3. 실행 (다양한 인터페이스 지원)
        if hasattr(agent, 'app') and agent.app:
            result = await agent.app.ainvoke(input_data)  # LangGraph
        elif hasattr(agent, 'execute'):
            result = await agent.execute(input_data)      # Async
        else:
            result = agent.run(input_data)                # Sync

        return result

    @staticmethod
    def get_agent_dependencies(agent_name: str):
        """의존성 정보 조회"""
        dependencies = {
            "search_agent": {
                "requires": [],
                "provides": ["legal_search", "real_estate_search"],
                "team": "search",
            },
            "analysis_agent": {
                "requires": ["collected_data"],
                "provides": ["report", "insights"],
                "team": "analysis",
            }
        }
        return dependencies.get(agent_name, {})
```

**핵심 특징**:
- ✅ **Placeholder 패턴**: 실제 구현 없이 메타데이터만 등록
- ✅ **동적 실행**: 런타임에 Agent 선택 및 실행
- ✅ **다형성 지원**: LangGraph, Async, Sync 모두 지원
- ✅ **의존성 관리**: Agent 간 의존성 명시

---

## 2. 현재 구조 vs 레퍼런스 구조

### 2.1 전체 비교표

| 측면 | 현재 구조 (Octostrator) | 레퍼런스 (service_agent) | 평가 |
|------|------------------------|-------------------------|------|
| **등록 방식** | Python 모듈 시스템 | AgentRegistry 싱글톤 | 레퍼런스 ↑ |
| **메타데이터** | 없음 | Capabilities, Priority, Team | 레퍼런스 ↑↑ |
| **실행 방식** | LangGraph Node 직접 실행 | Adapter 동적 실행 | 현재 ↑ |
| **Agent 형태** | Stateless 함수 | 클래스 인스턴스 | 현재 ↑ |
| **라우팅** | Command 기반 | Registry 기반 | 현재 ↑ |
| **인스턴스 캐싱** | 없음 | initialize_all() | 레퍼런스 ↑↑ |
| **Team 관리** | 없음 | Team Dict로 분류 | 레퍼런스 ↑ |
| **Priority** | 없음 | 우선순위 정렬 | 레퍼런스 ↑ |
| **Enabled 플래그** | 없음 | 활성화/비활성화 | 레퍼런스 ↑ |
| **의존성 관리** | 없음 | get_agent_dependencies() | 레퍼런스 ↑ |
| **Capability 검색** | 없음 | find_agents_by_capability() | 레퍼런스 ↑ |
| **LangGraph 철학** | 완벽 준수 | 일부 위배 | 현재 ↑↑ |

### 2.2 코드 비교

#### 2.2.1 Agent 등록

**현재 (Octostrator)**:
```python
# agents/__init__.py
from .diet import diet_agent_node
from .workout import workout_agent_node

__all__ = ["diet_agent_node", "workout_agent_node"]

# supervisor/graph.py
from backend.app.octostrator.agents import diet_agent_node, workout_agent_node

workflow.add_node("diet", diet_agent_node)
workflow.add_node("workout", workout_agent_node)
```

**레퍼런스 (service_agent)**:
```python
# 데코레이터 방식
@register_agent("search_team", team="search", priority=10)
class SearchTeam:
    pass

# 또는 명시적 등록
AgentRegistry.register(
    name="search_team",
    agent_class=SearchTeam,
    team="search",
    capabilities=AgentCapabilities(...),
    priority=10,
    enabled=True
)
```

#### 2.2.2 Agent 실행

**현재 (Octostrator)**:
```python
# LangGraph가 자동으로 라우팅
result = await graph.ainvoke(
    {"messages": [HumanMessage(content="...")]},
    config={"thread_id": "123"}
)
```

**레퍼런스 (service_agent)**:
```python
# Adapter를 통한 동적 실행
result = await AgentAdapter.execute_agent_dynamic(
    agent_name="search_agent",
    input_data={"query": "..."},
    llm_context=llm
)
```

#### 2.2.3 Agent 검색

**현재 (Octostrator)**:
```python
# 검색 기능 없음 (하드코딩)
if intent == "diet":
    goto = "diet"
elif intent == "workout":
    goto = "workout"
```

**레퍼런스 (service_agent)**:
```python
# Capability 기반 검색
agents = AgentRegistry.find_agents_by_capability(
    input_type="query",
    output_type="legal_search",
    required_tool="legal_search_tool"
)
# → ["search_agent", "legal_agent"]
```

---

## 3. 속도 향상 메커니즘 분석

### 3.1 Agent 인스턴스 캐싱 ⚡⚡⚡

**레퍼런스 방식**:
```python
# 앱 시작 시 모든 Agent 사전 인스턴스화
initialized_agents = AgentRegistry.initialize_all(
    llm_context=llm,
    config=config
)

# 실행 시 캐시된 인스턴스 사용
agent = initialized_agents["search_agent"]
result = await agent.app.ainvoke(input_data)
```

**속도 향상**:
- ❌ Before: 매 요청마다 Agent 인스턴스 생성 (50~100ms)
- ✅ After: 캐시된 인스턴스 재사용 (1ms 미만)
- 🚀 **효과**: 100배 향상

**현재 구조 적용**:
```python
# backend/app/octostrator/agents/cache.py (신규)

class AgentNodeCache:
    """Agent 노드 함수 캐싱"""

    _cache: Dict[str, Any] = {}

    @classmethod
    def register_node(cls, name: str, node_func: Callable):
        """노드 함수 등록 (메타데이터 포함)"""
        cls._cache[name] = {
            "func": node_func,
            "metadata": extract_metadata(node_func)  # Docstring 파싱
        }

    @classmethod
    def get_node(cls, name: str) -> Callable:
        """노드 함수 가져오기"""
        return cls._cache[name]["func"]
```

### 3.2 메타데이터 기반 빠른 검색 ⚡⚡

**레퍼런스 방식**:
```python
# O(n) 검색이지만 n이 작음 (10~20개)
agents = AgentRegistry.find_agents_by_capability(
    input_type="query",
    output_type="legal_search"
)
```

**현재 구조 적용**:
```python
# backend/app/octostrator/agents/metadata.py (신규)

AGENT_METADATA = {
    "diet": {
        "team": "fitness",
        "capabilities": {
            "input_types": ["meal_query", "nutrition_query"],
            "output_types": ["meal_analysis", "nutrition_recommendation"],
            "required_tools": ["db_query", "calculate_nutrition"]
        },
        "priority": 5,
        "enabled": True
    },
    "workout": {
        "team": "fitness",
        "capabilities": {
            "input_types": ["workout_query"],
            "output_types": ["workout_plan"],
            "required_tools": ["db_query", "llm_call"]
        },
        "priority": 5,
        "enabled": True
    }
}

def find_agents_by_capability(input_type: str = None, **kwargs) -> list[str]:
    """Capability 기반 Agent 검색"""
    matching = []
    for name, metadata in AGENT_METADATA.items():
        if not metadata["enabled"]:
            continue
        caps = metadata["capabilities"]
        if input_type and input_type in caps["input_types"]:
            matching.append(name)
    return sorted(matching, key=lambda n: AGENT_METADATA[n]["priority"], reverse=True)
```

### 3.3 Priority 기반 정렬 ⚡

**레퍼런스 방식**:
```python
# 우선순위 높은 Agent 먼저 실행
agents = AgentRegistry.list_agents(team="search")
# → ["search_team" (priority=10), "legal_agent" (priority=5)]

# 병렬 실행 시 중요한 Agent 우선
results = await asyncio.gather(*[
    execute_agent(agent_name) for agent_name in agents
])
```

**현재 구조 적용**:
```python
# Planning 노드에서 Priority 고려
tasks = [
    {"agent": "diet", "priority": 5},
    {"agent": "workout", "priority": 8},  # 더 중요
]
# Priority 순으로 정렬
tasks.sort(key=lambda t: t["priority"], reverse=True)
```

### 3.4 Enabled/Disabled 플래그 ⚡

**레퍼런스 방식**:
```python
# 비활성화된 Agent 스킵
AgentRegistry.set_enabled("analysis_agent", enabled=False)

# 실행 시 자동 스킵
agents = AgentRegistry.list_agents(enabled_only=True)
# → "analysis_agent"는 포함 안 됨
```

**현재 구조 적용**:
```python
# AGENT_METADATA에 enabled 추가
if not AGENT_METADATA[agent_name]["enabled"]:
    return {"status": "skipped", "reason": "Agent disabled"}
```

---

## 4. 통합 전략

### 4.1 절충안: Hybrid 구조

**핵심 아이디어**:
- LangGraph Node 방식 유지 (현재 구조의 강점)
- 메타데이터 레이어 추가 (레퍼런스의 강점)

```
┌─────────────────────────────────────────┐
│  LangGraph Supervisor (기존)           │
│  - Command 기반 라우팅                 │
│  - Stateless 노드                      │
│  - SupervisorState                     │
└─────────────────────────────────────────┘
                 ↕ (읽기)
┌─────────────────────────────────────────┐
│  Agent Metadata Layer (신규)           │ ⭐
│  - Capabilities                        │
│  - Priority                            │
│  - Team                                │
│  - Enabled/Disabled                    │
└─────────────────────────────────────────┘
                 ↕ (사용)
┌─────────────────────────────────────────┐
│  Agent Nodes (기존)                    │
│  - diet_agent_node()                   │
│  - workout_agent_node()                │
└─────────────────────────────────────────┘
```

### 4.2 구현 계획

#### Phase 1: 메타데이터 레이어 추가 (3일)

**파일**: `backend/app/octostrator/agents/metadata.py` (신규)

```python
"""Agent 메타데이터 정의"""

from typing import TypedDict, List

class AgentCapabilities(TypedDict):
    """Agent 능력 정의"""
    input_types: List[str]
    output_types: List[str]
    required_tools: List[str]

class AgentMetadata(TypedDict):
    """Agent 메타데이터"""
    name: str
    description: str
    team: str
    capabilities: AgentCapabilities
    priority: int
    enabled: bool

# Agent 메타데이터 Dict
AGENT_METADATA: dict[str, AgentMetadata] = {
    "diet": {
        "name": "DietAgent",
        "description": "식단 기록 및 분석",
        "team": "fitness",
        "capabilities": {
            "input_types": ["meal_query", "nutrition_query"],
            "output_types": ["meal_analysis", "nutrition_recommendation"],
            "required_tools": ["db_query", "calculate_nutrition", "llm_call"]
        },
        "priority": 5,
        "enabled": True
    },
    "workout": {
        "name": "WorkoutAgent",
        "description": "운동 루틴 추천",
        "team": "fitness",
        "capabilities": {
            "input_types": ["workout_query", "exercise_request"],
            "output_types": ["workout_plan", "exercise_recommendation"],
            "required_tools": ["db_query", "llm_call"]
        },
        "priority": 8,  # 더 높은 우선순위
        "enabled": True
    },
    "schedule": {
        "name": "ScheduleAgent",
        "description": "PT 스케줄 관리",
        "team": "fitness",
        "capabilities": {
            "input_types": ["schedule_query", "booking_request"],
            "output_types": ["schedule_info", "booking_confirmation"],
            "required_tools": ["db_query"]
        },
        "priority": 3,
        "enabled": True
    },
    "member_care": {
        "name": "MemberCareAgent",
        "description": "회원 진행률 리포팅",
        "team": "fitness",
        "capabilities": {
            "input_types": ["progress_query", "report_request"],
            "output_types": ["progress_report", "insights"],
            "required_tools": ["db_query", "llm_call"]
        },
        "priority": 4,
        "enabled": True
    },
    "coaching": {
        "name": "CoachingAgent",
        "description": "전문 자료 검색 (RAG)",
        "team": "fitness",
        "capabilities": {
            "input_types": ["knowledge_query", "research_request"],
            "output_types": ["search_results", "expert_answer"],
            "required_tools": ["vector_search", "llm_call"]
        },
        "priority": 6,
        "enabled": True
    }
}


def get_metadata(agent_name: str) -> AgentMetadata:
    """Agent 메타데이터 조회"""
    if agent_name not in AGENT_METADATA:
        raise ValueError(f"Unknown agent: {agent_name}")
    return AGENT_METADATA[agent_name]


def list_agents(team: str = None, enabled_only: bool = True) -> list[str]:
    """Agent 목록 조회"""
    agents = []
    for name, metadata in AGENT_METADATA.items():
        if team and metadata["team"] != team:
            continue
        if enabled_only and not metadata["enabled"]:
            continue
        agents.append(name)

    # Priority 순으로 정렬
    agents.sort(key=lambda n: AGENT_METADATA[n]["priority"], reverse=True)
    return agents


def find_agents_by_capability(
    input_type: str = None,
    output_type: str = None,
    required_tool: str = None
) -> list[str]:
    """Capability 기반 Agent 검색"""
    matching = []

    for name, metadata in AGENT_METADATA.items():
        if not metadata["enabled"]:
            continue

        caps = metadata["capabilities"]

        # 조건 검사
        if input_type and input_type not in caps["input_types"]:
            continue
        if output_type and output_type not in caps["output_types"]:
            continue
        if required_tool and required_tool not in caps["required_tools"]:
            continue

        matching.append(name)

    # Priority 순으로 정렬
    matching.sort(key=lambda n: AGENT_METADATA[n]["priority"], reverse=True)
    return matching


def set_enabled(agent_name: str, enabled: bool) -> bool:
    """Agent 활성화/비활성화"""
    if agent_name not in AGENT_METADATA:
        return False
    AGENT_METADATA[agent_name]["enabled"] = enabled
    return True
```

#### Phase 2: Planning 노드에 메타데이터 통합 (2일)

**파일**: `backend/app/octostrator/supervisor/nodes/planning.py` (수정)

```python
from backend.app.octostrator.agents.metadata import (
    AGENT_METADATA,
    find_agents_by_capability,
    list_agents
)

async def planning_node(state: SupervisorState, llm) -> Dict:
    """Planning Agent (메타데이터 기반 개선)"""

    user_intent = state["user_intent"]

    # ⭐ Capability 기반 Agent 검색 (신규)
    # 예: "식단"이 포함되면 meal_query 타입으로 검색
    if "식단" in user_intent or "영양" in user_intent:
        candidate_agents = find_agents_by_capability(input_type="meal_query")
    elif "운동" in user_intent:
        candidate_agents = find_agents_by_capability(input_type="workout_query")
    else:
        # 전체 Agent 목록 (Priority 순)
        candidate_agents = list_agents(enabled_only=True)

    # ⭐ LLM에게 메타데이터 정보 제공
    agent_descriptions = []
    for agent_name in candidate_agents:
        metadata = AGENT_METADATA[agent_name]
        agent_descriptions.append(
            f"- {agent_name} ({metadata['description']}): "
            f"Priority={metadata['priority']}, "
            f"Inputs={metadata['capabilities']['input_types']}"
        )

    prompt = f"""
    사용자 의도: {user_intent}

    사용 가능한 Agents (우선순위 순):
    {chr(10).join(agent_descriptions)}

    적절한 Agent를 선택하여 Task 리스트를 생성하세요.
    """

    # Structured Output으로 Plan 생성
    plan = await structured_llm.ainvoke(prompt)

    # ⭐ Plan에 메타데이터 추가
    for task in plan.tasks:
        if task.agent in AGENT_METADATA:
            task.priority = AGENT_METADATA[task.agent]["priority"]
            task.enabled = AGENT_METADATA[task.agent]["enabled"]

    # Priority 순으로 Task 정렬
    plan.tasks.sort(key=lambda t: t.priority, reverse=True)

    return {"plan": [task.model_dump() for task in plan.tasks], ...}
```

#### Phase 3: Executor에 Enabled 체크 추가 (1일)

**파일**: `backend/app/octostrator/supervisor/nodes/executor.py` (수정)

```python
from backend.app.octostrator.agents.metadata import AGENT_METADATA

async def executor_node(state: SupervisorState) -> Command:
    """Executor (Enabled 체크 추가)"""

    step = state["plan"][state["current_step"]]
    agent_name = step["agent"]

    # ⭐ Enabled 체크
    if agent_name in AGENT_METADATA:
        if not AGENT_METADATA[agent_name]["enabled"]:
            # 비활성화된 Agent 스킵
            updated_plan = list(state["plan"])
            updated_plan[state["current_step"]]["status"] = "skipped"
            updated_plan[state["current_step"]]["result"] = "Agent is disabled"

            return Command(
                update={
                    "plan": updated_plan,
                    "current_step": state["current_step"] + 1
                },
                goto="executor"  # 다음 Task로
            )

    # 정상 실행
    return Command(
        update={"plan": updated_plan},
        goto=agent_name
    )
```

#### Phase 4: Adapter 패턴 추가 (선택적, 2일)

**파일**: `backend/app/octostrator/agents/adapter.py` (신규)

```python
"""Agent Adapter - 동적 실행 지원"""

from typing import Dict, Any, Callable
from backend.app.octostrator.agents.metadata import AGENT_METADATA
from backend.app.octostrator.agents import (
    diet_agent_node,
    workout_agent_node,
    # ...
)

# Node 함수 매핑
AGENT_NODES: Dict[str, Callable] = {
    "diet": diet_agent_node,
    "workout": workout_agent_node,
    "schedule": schedule_agent_node,
    "member_care": member_care_agent_node,
    "coaching": coaching_agent_node,
}


async def execute_agent_dynamic(
    agent_name: str,
    state: SupervisorState
) -> Dict[str, Any]:
    """동적 Agent 실행"""

    # 메타데이터 확인
    if agent_name not in AGENT_METADATA:
        return {"error": f"Unknown agent: {agent_name}"}

    metadata = AGENT_METADATA[agent_name]
    if not metadata["enabled"]:
        return {"status": "skipped", "reason": "Agent disabled"}

    # 노드 함수 가져오기
    node_func = AGENT_NODES.get(agent_name)
    if not node_func:
        return {"error": f"Node function not found: {agent_name}"}

    # 실행
    try:
        result = await node_func(state)
        return result
    except Exception as e:
        return {"error": str(e), "agent": agent_name}


def get_agent_dependencies(agent_name: str) -> Dict[str, Any]:
    """Agent 의존성 정보"""
    metadata = AGENT_METADATA.get(agent_name)
    if not metadata:
        return {}

    return {
        "requires": metadata["capabilities"]["input_types"],
        "provides": metadata["capabilities"]["output_types"],
        "tools": metadata["capabilities"]["required_tools"],
        "team": metadata["team"],
    }
```

---

## 5. 차이점 요약

### 5.1 아키텍처 차이

| 측면 | 현재 (Octostrator) | 레퍼런스 (service_agent) | 통합 후 |
|------|-------------------|-------------------------|---------|
| **Agent 형태** | Stateless 함수 | 클래스 인스턴스 | Stateless 함수 (유지) |
| **등록 방식** | Python 모듈 | Registry 싱글톤 | 모듈 + 메타데이터 Dict |
| **메타데이터** | 없음 | AgentMetadata | Dict 기반 메타데이터 ⭐ |
| **실행 방식** | LangGraph Node | Adapter 동적 실행 | LangGraph (유지) + Adapter (선택) |
| **캐싱** | 없음 | initialize_all() | 필요 없음 (함수는 캐시 불필요) |
| **검색** | 없음 | find_by_capability | 메타데이터 기반 검색 ⭐ |
| **Priority** | 없음 | 우선순위 정렬 | Planning에서 활용 ⭐ |
| **Enabled** | 없음 | 활성화 플래그 | Executor에서 체크 ⭐ |

### 5.2 속도 향상 메커니즘 통합

| 메커니즘 | 레퍼런스 방식 | 현재 구조 적용 | 효과 |
|---------|-------------|--------------|------|
| **인스턴스 캐싱** | `initialize_all()` | ❌ 불필요 (함수는 캐시 안 함) | N/A |
| **메타데이터 검색** | Capabilities 기반 | ✅ Dict 기반 검색 | ⚡ O(1)~O(n) |
| **Priority 정렬** | Registry에서 정렬 | ✅ Planning에서 정렬 | ⚡ 중요 Agent 우선 |
| **Enabled 플래그** | Registry 체크 | ✅ Executor 체크 | ⚡ 불필요한 실행 스킵 |
| **Team 분류** | Team Dict | ✅ 메타데이터 team 필드 | ⚡ 검색 범위 축소 |
| **Adapter 패턴** | 동적 실행 | ✅ 선택적 구현 | ⚡ 런타임 유연성 |

### 5.3 LangGraph 철학 준수

| 원칙 | 현재 구조 | 레퍼런스 | 통합 후 |
|------|---------|---------|---------|
| **Stateless Nodes** | ✅ 준수 | ❌ 위배 (클래스 인스턴스) | ✅ 준수 |
| **Explicit State** | ✅ 준수 | ⚠️ 일부 위배 | ✅ 준수 |
| **Command Routing** | ✅ 사용 | ❌ 미사용 | ✅ 사용 |
| **Structured Output** | ✅ 사용 | ⚠️ 일부 사용 | ✅ 사용 |
| **Checkpointing** | ✅ PostgreSQL | ❌ 미구현 | ✅ PostgreSQL |

---

## 6. 속도 벤치마크 (예상)

### 6.1 레퍼런스 방식 (Agent 인스턴스 캐싱)

```
요청 1: Agent 인스턴스 생성 (100ms) + 실행 (200ms) = 300ms
요청 2: 캐시 조회 (1ms) + 실행 (200ms) = 201ms ⚡
요청 3: 캐시 조회 (1ms) + 실행 (200ms) = 201ms ⚡
```

**효과**: 2번째 요청부터 100ms 절약

### 6.2 현재 방식 (Stateless 함수)

```
요청 1: 함수 호출 (1ms) + 실행 (200ms) = 201ms ⚡
요청 2: 함수 호출 (1ms) + 실행 (200ms) = 201ms ⚡
요청 3: 함수 호출 (1ms) + 실행 (200ms) = 201ms ⚡
```

**효과**: 항상 빠름 (인스턴스화 비용 없음)

**결론**:
- 현재 구조가 이미 빠름 (Stateless 함수)
- 레퍼런스의 캐싱은 클래스 인스턴스 방식에서만 필요
- **메타데이터 레이어만 채택하면 충분**

---

## 7. 구현 우선순위

### High Priority (즉시 구현) 🔴
1. **Agent 메타데이터 Dict** (1일)
   - `agents/metadata.py` 생성
   - Capabilities, Priority, Team 정의

2. **Planning 노드 개선** (1일)
   - 메타데이터 기반 Agent 선택
   - Priority 순 정렬

3. **Executor Enabled 체크** (0.5일)
   - 비활성화된 Agent 스킵

### Medium Priority (1주 내) 🟡
4. **Capability 기반 검색** (1일)
   - `find_agents_by_capability()` 구현

5. **Adapter 패턴** (2일)
   - 동적 실행 지원 (선택적)
   - 의존성 관리

### Low Priority (2주 내) 🟢
6. **메타데이터 관리 UI** (3일)
   - Agent 활성화/비활성화 토글
   - Priority 조정 인터페이스

---

## 8. 최종 권장사항

### ✅ 채택할 것

1. **Agent 메타데이터** (Dict 방식)
   - Capabilities
   - Priority
   - Team
   - Enabled/Disabled

2. **Capability 기반 검색**
   - Planning에서 적절한 Agent 발견

3. **Priority 정렬**
   - 중요한 Agent 우선 실행

4. **Enabled 플래그**
   - 불필요한 Agent 스킵

### ❌ 채택 안 할 것

1. **싱글톤 Registry 클래스**
   - LangGraph 철학 위배
   - 불필요한 복잡도

2. **Agent 클래스 인스턴스화**
   - Stateless 함수가 더 효율적
   - 캐싱 불필요

3. **initialize_all() 캐싱**
   - 함수는 캐싱 필요 없음

### 🔄 절충안

**Hybrid 구조**:
```
LangGraph Node (현재 강점)
    +
메타데이터 레이어 (레퍼런스 강점)
    =
최적의 구조
```

---

## 9. 다음 단계

### Week 1: 메타데이터 레이어
- [ ] `agents/metadata.py` 작성
- [ ] 5개 Agent 메타데이터 정의
- [ ] `find_agents_by_capability()` 구현
- [ ] 테스트 작성

### Week 2: Planning/Executor 통합
- [ ] Planning 노드 개선
- [ ] Executor Enabled 체크
- [ ] 통합 테스트

### Week 3: Adapter 패턴 (선택적)
- [ ] `agents/adapter.py` 작성
- [ ] 동적 실행 지원
- [ ] 의존성 관리

---

## 10. 코드 예시

### 10.1 메타데이터 정의

```python
# agents/metadata.py

AGENT_METADATA = {
    "diet": {
        "name": "DietAgent",
        "description": "식단 기록 및 분석",
        "team": "fitness",
        "capabilities": {
            "input_types": ["meal_query", "nutrition_query"],
            "output_types": ["meal_analysis", "nutrition_recommendation"],
            "required_tools": ["db_query", "calculate_nutrition", "llm_call"]
        },
        "priority": 5,
        "enabled": True
    }
}
```

### 10.2 Planning에서 사용

```python
# supervisor/nodes/planning.py

from backend.app.octostrator.agents.metadata import find_agents_by_capability

async def planning_node(state, llm):
    # Capability 기반 검색
    agents = find_agents_by_capability(input_type="meal_query")
    # → ["diet"] (enabled=True, priority 순)

    # LLM에게 제공
    prompt = f"사용 가능한 Agents: {agents}"
```

### 10.3 Executor에서 Enabled 체크

```python
# supervisor/nodes/executor.py

from backend.app.octostrator.agents.metadata import AGENT_METADATA

async def executor_node(state):
    agent_name = state["plan"][state["current_step"]]["agent"]

    # Enabled 체크
    if not AGENT_METADATA[agent_name]["enabled"]:
        return skip_task(state)

    # 정상 실행
    return Command(goto=agent_name)
```

---

**문서 작성**: Claude (AI Assistant)
**다음 단계**: 메타데이터 레이어 구현 시작

---

**문서 끝**
