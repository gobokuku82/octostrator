# Registry 시스템 구현 계획서 (속도 최적화 통합)

**프로젝트**: AI PTmanager - Beta v0.01
**작성일**: 2025-11-04
**버전**: 2.0 (레퍼런스 분석 반영)
**대상**: Tools & SubGraphs 공유 메커니즘 + Agent 메타데이터 레이어 구현

---

## 📋 Executive Summary

### 목표

**명시적 싱글톤 Registry 대신, LangGraph 철학에 맞는 경량 공유 메커니즘 + 속도 최적화를 위한 메타데이터 레이어 구현**

### 핵심 방침

| 항목 | 기존 계획 | 수정된 계획 (v2.0) | 근거 |
|------|----------|------------|------|
| **Agent Registry** | 싱글톤 클래스 | ❌ 구현 안 함 | LangGraph가 이미 제공 |
| **Agent Metadata** | 없음 | ⭐ Dict 기반 메타데이터 (신규) | 속도 최적화 (레퍼런스) |
| **Tool Registry** | 싱글톤 클래스 | 📦 단순 Dict | 함수 등록만 필요 |
| **SubGraph Registry** | 싱글톤 클래스 | 📦 단순 Dict | 그래프 빌더 함수 등록 |
| **등록 방식** | `registry.register()` | Python 모듈 시스템 | Import로 충분 |
| **Agent 검색** | 없음 | ⭐ Capability 기반 검색 (신규) | Planning 최적화 |
| **Priority 관리** | 없음 | ⭐ 우선순위 정렬 (신규) | 실행 순서 최적화 |
| **Enabled 플래그** | 없음 | ⭐ 활성화/비활성화 (신규) | 불필요한 실행 스킵 |

### 레퍼런스 비교 결과

**service_agent 레퍼런스 구조 분석 결과** (REFERENCE_COMPARISON_251104.md 참고):

| 속도 향상 메커니즘 | 레퍼런스 방식 | 현재 구조 적용 | 효과 |
|------------------|-------------|--------------|------|
| **Agent 인스턴스 캐싱** | `initialize_all()` | ❌ 불필요 (Stateless 함수) | - |
| **메타데이터 기반 검색** | Capabilities Dict | ✅ **채택** (Phase 1) | ⚡⚡ O(1) 검색 |
| **Priority 정렬** | Registry 정렬 | ✅ **채택** (Phase 1) | ⚡ 중요 Agent 우선 |
| **Enabled 플래그** | Registry 체크 | ✅ **채택** (Phase 2) | ⚡ 불필요한 실행 스킵 |
| **Team 분류** | Team Dict | ✅ **채택** (Phase 1) | ⚡ 검색 범위 축소 |
| **Adapter 패턴** | 동적 실행 | ⚠️ **선택적** (Phase 5) | ⚡ 런타임 유연성 |

### 구현 범위 (v2.0 업데이트)

```
Phase 0: Agent 메타데이터 레이어 (신규, 3일) ⭐
  ├── agents/metadata.py (Capabilities, Priority, Team)
  ├── find_agents_by_capability() 구현
  ├── list_agents() 구현
  └── 5개 Agent 메타데이터 정의

Phase 1: Tools 구현 (1주)
  ├── vector_search_tool
  ├── db_query_tool
  ├── llm_call_tool
  ├── calculate_nutrition_tool
  └── tools/__init__.py (단순 Dict)

Phase 2: SubGraphs 구현 (1주)
  ├── rag_subgraph
  ├── validation_subgraph
  ├── nutrition_calculation_subgraph
  └── sub_graphs/__init__.py (단순 Dict)

Phase 3: Metadata 통합 (신규, 2일) ⭐
  ├── Planning 노드에 Capability 검색 통합
  ├── Executor에 Enabled 체크 추가
  └── Priority 순 Task 정렬

Phase 4: Agent 리팩토링 (1주)
  └── Mock → Tools 사용으로 변경

Phase 5: 테스트 및 문서화 (1주)
  ├── 단위/통합 테스트
  └── API 문서 작성

Phase 6: Adapter 패턴 (선택적, 2일) ⭐
  ├── agents/adapter.py (동적 실행)
  └── 의존성 관리
```

**총 기간**: 5주 (기존 4주 → 메타데이터 레이어 +1주)

---

## 1. 설계 원칙

### 1.1 LangGraph 철학 준수

**핵심 원칙**:
1. **Stateless Functions**: 모든 Tool과 SubGraph는 순수 함수
2. **Explicit Dependencies**: 의존성을 함수 파라미터로 명시
3. **Simple is Better**: 복잡한 Registry보다 단순한 Dict
4. **No Global State**: 상태는 SupervisorState에만

### 1.2 Registry 대신 사용할 패턴

```python
# ❌ 기존 계획 (복잡한 싱글톤)
class ToolRegistry:
    _instance = None
    _lock = threading.Lock()
    # ... 100줄 이상의 복잡한 코드

    def register(self, name, func):
        self._tools[name] = func

# ✅ 수정된 계획 (단순 Dict)
TOOLS = {
    "vector_search": vector_search_tool,
    "db_query": db_query_tool,
    "llm_call": llm_call_tool,
}

def get_tool(name: str):
    """Tool 함수 가져오기"""
    if name not in TOOLS:
        raise ValueError(f"Tool '{name}' not found")
    return TOOLS[name]
```

**장점**:
- ✅ 간단함 (10줄 vs 100줄)
- ✅ 타입 안전성 (IDE 자동완성)
- ✅ 테스트 용이 (Mock 주입 쉬움)
- ✅ 스레드 안전 (불변 Dict)
- ✅ 디버깅 쉬움 (복잡한 메타클래스 없음)

---

## 2. Agent 메타데이터 레이어 구현 (Phase 0) ⭐ 신규

### 2.1 개요

**목적**: 레퍼런스 구조의 속도 최적화 메커니즘을 현재 구조에 통합

**핵심 전략**:
- ✅ 메타데이터 레이어만 채택 (싱글톤 Registry는 거부)
- ✅ LangGraph Node 방식 유지
- ✅ Stateless 함수 유지 (인스턴스 캐싱 불필요)

### 2.2 디렉토리 구조

```
backend/app/octostrator/agents/
├── __init__.py                      # 기존 Agent exports
├── metadata.py                      # ⭐ 신규: Agent 메타데이터
├── diet/
├── workout/
├── schedule/
├── member_care/
└── coaching/
```

### 2.3 AgentMetadata 구조 설계

**파일**: `backend/app/octostrator/agents/metadata.py` (신규)

```python
"""Agent 메타데이터 레이어

레퍼런스 service_agent 구조의 속도 최적화 메커니즘 통합
- Capabilities: Agent 능력 정의 (input/output types, required tools)
- Priority: 실행 우선순위
- Team: 팀 분류
- Enabled: 활성화/비활성화 플래그
"""

from typing import TypedDict, List


class AgentCapabilities(TypedDict):
    """Agent 능력 정의

    레퍼런스의 AgentCapabilities 구조 채택
    """
    input_types: List[str]        # Agent가 처리 가능한 입력 타입
    output_types: List[str]       # Agent가 생성하는 출력 타입
    required_tools: List[str]     # Agent가 필요로 하는 Tool 목록


class AgentMetadata(TypedDict):
    """Agent 메타데이터

    레퍼런스의 AgentMetadata 구조 단순화
    (agent_class 필드 제외 - Stateless 함수이므로 불필요)
    """
    name: str                     # Agent 표시 이름
    description: str              # 설명
    team: str                     # 소속 팀 (fitness, search, analysis 등)
    capabilities: AgentCapabilities
    priority: int                 # 실행 우선순위 (높을수록 먼저)
    enabled: bool                 # 활성화 여부


# 5개 Fitness Agent 메타데이터
AGENT_METADATA: dict[str, AgentMetadata] = {
    "diet": {
        "name": "DietAgent",
        "description": "식단 기록 조회 및 영양 분석 (DB + 계산)",
        "team": "fitness",
        "capabilities": {
            "input_types": ["meal_query", "nutrition_query", "diet_history"],
            "output_types": ["meal_analysis", "nutrition_recommendation", "diet_report"],
            "required_tools": ["db_query", "calculate_nutrition", "llm_call"]
        },
        "priority": 5,
        "enabled": True
    },
    "workout": {
        "name": "WorkoutAgent",
        "description": "운동 루틴 생성 및 추천 (ExerciseDB + LLM)",
        "team": "fitness",
        "capabilities": {
            "input_types": ["workout_query", "exercise_request", "routine_query"],
            "output_types": ["workout_plan", "exercise_recommendation", "routine_analysis"],
            "required_tools": ["db_query", "llm_call"]
        },
        "priority": 8,  # ⭐ 운동이 식단보다 우선순위 높음
        "enabled": True
    },
    "schedule": {
        "name": "ScheduleAgent",
        "description": "PT 스케줄 관리 (CRUD)",
        "team": "fitness",
        "capabilities": {
            "input_types": ["schedule_query", "booking_request", "availability_check"],
            "output_types": ["schedule_info", "booking_confirmation", "available_slots"],
            "required_tools": ["db_query"]
        },
        "priority": 3,
        "enabled": True
    },
    "member_care": {
        "name": "MemberCareAgent",
        "description": "회원 진행률 분석 및 리포트 생성",
        "team": "fitness",
        "capabilities": {
            "input_types": ["progress_query", "report_request", "member_stats"],
            "output_types": ["progress_report", "insights", "member_analysis"],
            "required_tools": ["db_query", "llm_call"]
        },
        "priority": 4,
        "enabled": True
    },
    "coaching": {
        "name": "CoachingAgent",
        "description": "전문 자료 검색 및 코칭 조언 (RAG)",
        "team": "fitness",
        "capabilities": {
            "input_types": ["knowledge_query", "research_request", "expert_question"],
            "output_types": ["search_results", "expert_answer", "coaching_advice"],
            "required_tools": ["vector_search", "llm_call"]
        },
        "priority": 6,
        "enabled": True
    }
}


# ===== 레퍼런스 방식 채택: 검색 및 관리 함수 =====

def get_metadata(agent_name: str) -> AgentMetadata:
    """Agent 메타데이터 조회

    Args:
        agent_name: Agent 이름

    Returns:
        AgentMetadata

    Raises:
        ValueError: 존재하지 않는 Agent
    """
    if agent_name not in AGENT_METADATA:
        raise ValueError(f"Unknown agent: {agent_name}")
    return AGENT_METADATA[agent_name]


def list_agents(team: str = None, enabled_only: bool = True) -> list[str]:
    """Agent 목록 조회 (레퍼런스 방식)

    Args:
        team: 팀 필터 (None이면 전체)
        enabled_only: enabled=True인 Agent만 반환

    Returns:
        Agent 이름 리스트 (Priority 내림차순 정렬)

    Example:
        >>> list_agents(team="fitness")
        ["workout", "coaching", "diet", "member_care", "schedule"]
        # Priority: 8, 6, 5, 4, 3 순
    """
    agents = []

    for name, metadata in AGENT_METADATA.items():
        # Team 필터
        if team and metadata["team"] != team:
            continue

        # Enabled 필터
        if enabled_only and not metadata["enabled"]:
            continue

        agents.append(name)

    # Priority 내림차순 정렬 (레퍼런스 방식)
    agents.sort(key=lambda n: AGENT_METADATA[n]["priority"], reverse=True)

    return agents


def find_agents_by_capability(
    input_type: str = None,
    output_type: str = None,
    required_tool: str = None
) -> list[str]:
    """Capability 기반 Agent 검색 (레퍼런스 방식)

    ⚡ 속도 최적화: O(n) 검색 (n=5~10개로 매우 작음)

    Args:
        input_type: 입력 타입 필터
        output_type: 출력 타입 필터
        required_tool: 필수 Tool 필터

    Returns:
        매칭되는 Agent 리스트 (Priority 내림차순)

    Example:
        >>> find_agents_by_capability(input_type="meal_query")
        ["diet"]  # meal_query를 처리 가능한 Agent

        >>> find_agents_by_capability(required_tool="vector_search")
        ["coaching"]  # vector_search Tool 필요한 Agent
    """
    matching = []

    for name, metadata in AGENT_METADATA.items():
        # Enabled 체크
        if not metadata["enabled"]:
            continue

        caps = metadata["capabilities"]

        # 조건 검사 (모든 조건 AND)
        if input_type and input_type not in caps["input_types"]:
            continue
        if output_type and output_type not in caps["output_types"]:
            continue
        if required_tool and required_tool not in caps["required_tools"]:
            continue

        matching.append(name)

    # Priority 내림차순 정렬
    matching.sort(key=lambda n: AGENT_METADATA[n]["priority"], reverse=True)

    return matching


def set_enabled(agent_name: str, enabled: bool) -> bool:
    """Agent 활성화/비활성화 (레퍼런스 방식)

    ⚡ 속도 최적화: 불필요한 Agent 스킵

    Args:
        agent_name: Agent 이름
        enabled: 활성화 여부

    Returns:
        성공 여부

    Example:
        >>> set_enabled("schedule", False)
        True
        >>> list_agents()
        ["workout", "coaching", "diet", "member_care"]
        # "schedule"는 제외됨
    """
    if agent_name not in AGENT_METADATA:
        return False

    AGENT_METADATA[agent_name]["enabled"] = enabled
    return True


def get_team_agents(team: str) -> dict[str, AgentMetadata]:
    """특정 팀의 모든 Agent 조회 (레퍼런스 _teams 개념)

    Args:
        team: 팀 이름

    Returns:
        {agent_name: metadata} Dict
    """
    return {
        name: metadata
        for name, metadata in AGENT_METADATA.items()
        if metadata["team"] == team
    }


__all__ = [
    "AgentCapabilities",
    "AgentMetadata",
    "AGENT_METADATA",
    "get_metadata",
    "list_agents",
    "find_agents_by_capability",
    "set_enabled",
    "get_team_agents",
]
```

### 2.4 구현 체크리스트 (Phase 0)

**Day 1**:
- [ ] `agents/metadata.py` 파일 생성
- [ ] AgentCapabilities TypedDict 정의
- [ ] AgentMetadata TypedDict 정의
- [ ] AGENT_METADATA Dict에 5개 Agent 정의

**Day 2**:
- [ ] `get_metadata()` 구현
- [ ] `list_agents()` 구현 (Priority 정렬)
- [ ] `find_agents_by_capability()` 구현
- [ ] `set_enabled()` 구현
- [ ] `get_team_agents()` 구현

**Day 3**:
- [ ] 메타데이터 단위 테스트 작성
- [ ] 검색 함수 테스트
- [ ] Priority 정렬 테스트

### 2.5 메타데이터 테스트 예시

**파일**: `tests/test_agents/test_metadata.py` (신규)

```python
import pytest
from backend.app.octostrator.agents.metadata import (
    AGENT_METADATA,
    get_metadata,
    list_agents,
    find_agents_by_capability,
    set_enabled
)


def test_list_agents_priority_order():
    """Priority 순으로 정렬 확인"""
    agents = list_agents()

    # Priority: workout(8) > coaching(6) > diet(5) > member_care(4) > schedule(3)
    assert agents == ["workout", "coaching", "diet", "member_care", "schedule"]


def test_find_agents_by_input_type():
    """Input type 기반 검색"""
    agents = find_agents_by_capability(input_type="meal_query")

    # "diet"만 meal_query 처리 가능
    assert agents == ["diet"]


def test_find_agents_by_required_tool():
    """Required tool 기반 검색"""
    agents = find_agents_by_capability(required_tool="vector_search")

    # "coaching"만 vector_search 필요
    assert agents == ["coaching"]


def test_set_enabled():
    """Agent 비활성화 테스트"""
    # 원래는 5개
    assert len(list_agents()) == 5

    # workout 비활성화
    set_enabled("workout", False)

    # 4개로 감소
    agents = list_agents(enabled_only=True)
    assert len(agents) == 4
    assert "workout" not in agents

    # 복원
    set_enabled("workout", True)


def test_get_team_agents():
    """팀별 Agent 조회"""
    from backend.app.octostrator.agents.metadata import get_team_agents

    fitness_agents = get_team_agents("fitness")

    assert len(fitness_agents) == 5
    assert "diet" in fitness_agents
    assert "workout" in fitness_agents
```

---

## 3. Tools 구현 계획 (Phase 1)

### 2.1 디렉토리 구조

```
backend/app/octostrator/tools/
├── __init__.py                      # TOOLS Dict 및 get_tool()
├── vector_search_tool.py            # 벡터 검색
├── db_query_tool.py                 # DB 조회 (범용)
├── llm_call_tool.py                 # LLM 호출 (범용)
├── calculate_nutrition_tool.py      # 영양소 계산
├── parse_meal_input_tool.py         # 식단 입력 파싱
└── generate_workout_tool.py         # 운동 루틴 생성
```

### 2.2 Tool 인터페이스 설계

**공통 시그니처**:
```python
from typing import Any, Dict, Optional

async def tool_function(
    *,  # Keyword-only arguments
    param1: Type1,
    param2: Type2,
    context: Optional[Dict[str, Any]] = None  # LLM, DB 등 주입
) -> ResultType:
    """Tool 함수

    Args:
        param1: 설명
        param2: 설명
        context: AppContext에서 주입되는 리소스
            - llm: ChatOpenAI 인스턴스
            - db: Database Session
            - config: 환경 설정

    Returns:
        결과

    Raises:
        ValueError: 입력 오류
        RuntimeError: 실행 오류
    """
    pass
```

**특징**:
- ✅ Keyword-only arguments (실수 방지)
- ✅ 타입 힌트 (mypy 검사)
- ✅ Context 주입 (의존성 명시적)
- ✅ Async (I/O 비동기)
- ✅ Docstring (자동 문서화)

### 2.3 Tool 구현 예시

#### Tool 1: vector_search_tool

**파일**: `backend/app/octostrator/tools/vector_search_tool.py`

```python
"""벡터 검색 Tool

FAISSManager를 사용한 유사도 검색
"""
from typing import List, Dict, Optional, Any
from backend.database.vector_db.faiss_manager import FAISSManager


async def vector_search_tool(
    *,
    query: str,
    k: int = 3,
    filter_metadata: Optional[Dict[str, Any]] = None,
    context: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """벡터 검색 Tool

    Args:
        query: 검색 쿼리
        k: 반환할 문서 개수
        filter_metadata: 메타데이터 필터 (예: {"category": "법률"})
        context: (미사용)

    Returns:
        검색 결과 리스트
        [
            {
                "content": "문서 내용",
                "metadata": {"source": "...", "page": 1},
                "score": 0.95
            },
            ...
        ]

    Raises:
        RuntimeError: FAISS 검색 실패
    """
    try:
        faiss_manager = FAISSManager()

        # 검색 수행
        results = faiss_manager.similarity_search(
            query=query,
            k=k,
            filter=filter_metadata
        )

        # 결과 포맷팅
        formatted_results = []
        for doc in results:
            formatted_results.append({
                "content": doc.page_content,
                "metadata": doc.metadata,
                "score": getattr(doc, "score", None)
            })

        return formatted_results

    except Exception as e:
        raise RuntimeError(f"벡터 검색 실패: {str(e)}")
```

#### Tool 2: db_query_tool

**파일**: `backend/app/octostrator/tools/db_query_tool.py`

```python
"""DB 조회 Tool

SQLAlchemy ORM을 사용한 범용 DB 조회
"""
from typing import List, Dict, Any, Optional, Type
from backend.database.relation_db.session import get_db
from backend.database.relation_db.models import (
    User, MealLog, WorkoutRoutine, Schedule, MemberProgress, ExerciseDB
)

# 테이블 매핑
MODELS = {
    "users": User,
    "meal_logs": MealLog,
    "workout_routines": WorkoutRoutine,
    "schedules": Schedule,
    "member_progress": MemberProgress,
    "exercise_db": ExerciseDB,
}


async def db_query_tool(
    *,
    table: str,
    filters: Optional[Dict[str, Any]] = None,
    order_by: Optional[str] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    context: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """DB 조회 Tool

    Args:
        table: 테이블 이름 ("users", "meal_logs", 등)
        filters: 필터 조건 {"user_id": 1, "status": "active"}
        order_by: 정렬 필드 ("date" 또는 "-date" for DESC)
        limit: 최대 결과 개수
        offset: 시작 위치
        context: (미사용)

    Returns:
        조회 결과 리스트 (dict로 변환)

    Raises:
        ValueError: 잘못된 테이블 이름
        RuntimeError: DB 조회 실패

    Example:
        # 최근 식단 기록 3개
        results = await db_query_tool(
            table="meal_logs",
            filters={"user_id": 1},
            order_by="-date",
            limit=3
        )
    """
    if table not in MODELS:
        raise ValueError(f"Unknown table: {table}")

    try:
        model = MODELS[table]

        with get_db() as db:
            # 쿼리 시작
            query = db.query(model)

            # 필터 적용
            if filters:
                for key, value in filters.items():
                    if hasattr(model, key):
                        query = query.filter(getattr(model, key) == value)
                    else:
                        raise ValueError(f"Invalid filter field: {key}")

            # 정렬
            if order_by:
                if order_by.startswith("-"):
                    field = order_by[1:]
                    query = query.order_by(getattr(model, field).desc())
                else:
                    query = query.order_by(getattr(model, order_by))

            # 페이지네이션
            if offset:
                query = query.offset(offset)
            if limit:
                query = query.limit(limit)

            # 실행
            results = query.all()

            # Dict로 변환
            return [row_to_dict(row) for row in results]

    except Exception as e:
        raise RuntimeError(f"DB 조회 실패: {str(e)}")


def row_to_dict(row) -> Dict[str, Any]:
    """SQLAlchemy Row를 Dict로 변환"""
    return {
        column.name: getattr(row, column.name)
        for column in row.__table__.columns
    }
```

#### Tool 3: llm_call_tool

**파일**: `backend/app/octostrator/tools/llm_call_tool.py`

```python
"""LLM 호출 Tool

ChatOpenAI를 사용한 범용 LLM 호출
"""
from typing import Optional, Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage


async def llm_call_tool(
    *,
    prompt: str,
    model: str = "gpt-4o-mini",
    temperature: float = 0.7,
    max_tokens: Optional[int] = None,
    context: Optional[Dict[str, Any]] = None
) -> str:
    """LLM 호출 Tool

    Args:
        prompt: 입력 프롬프트
        model: 모델 이름
        temperature: 생성 온도
        max_tokens: 최대 토큰 수
        context: AppContext에서 llm 주입 시 사용

    Returns:
        LLM 응답 텍스트

    Raises:
        RuntimeError: LLM 호출 실패
    """
    try:
        # Context에서 LLM 가져오기 (있으면)
        if context and "llm" in context:
            llm = context["llm"]
        else:
            # 없으면 새로 생성
            llm = ChatOpenAI(
                model=model,
                temperature=temperature,
                max_tokens=max_tokens
            )

        # 호출
        message = HumanMessage(content=prompt)
        response = await llm.ainvoke([message])

        return response.content

    except Exception as e:
        raise RuntimeError(f"LLM 호출 실패: {str(e)}")
```

#### Tool 4: calculate_nutrition_tool

**파일**: `backend/app/octostrator/tools/calculate_nutrition_tool.py`

```python
"""영양소 계산 Tool

식품 이름과 양으로 영양소 계산
"""
from typing import List, Dict, Any, Optional


# 간단한 영양소 DB (실제로는 외부 API 또는 DB 사용)
NUTRITION_DB = {
    "계란": {"calories": 70, "protein": 6, "carbs": 0.5, "fat": 5},  # per 개
    "닭가슴살": {"calories": 165, "protein": 31, "carbs": 0, "fat": 3.6},  # per 100g
    "현미밥": {"calories": 350, "protein": 7, "carbs": 73, "fat": 2.5},  # per 공기
    "바나나": {"calories": 105, "protein": 1.3, "carbs": 27, "fat": 0.4},  # per 개
    "샐러드": {"calories": 50, "protein": 2, "carbs": 10, "fat": 0.5},  # per 접시
}


async def calculate_nutrition_tool(
    *,
    foods: List[Dict[str, Any]],
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, float]:
    """영양소 계산 Tool

    Args:
        foods: 식품 리스트
            [
                {"name": "계란", "quantity": 2, "unit": "개"},
                {"name": "현미밥", "quantity": 1, "unit": "공기"}
            ]
        context: (미사용)

    Returns:
        총 영양소
        {
            "calories": 450,
            "protein": 30,
            "carbs": 45,
            "fat": 15
        }

    Raises:
        ValueError: 알 수 없는 식품
    """
    total_nutrition = {
        "calories": 0.0,
        "protein": 0.0,
        "carbs": 0.0,
        "fat": 0.0
    }

    for food in foods:
        name = food["name"]
        quantity = food["quantity"]

        if name not in NUTRITION_DB:
            # LLM으로 추정 또는 외부 API 호출
            # 현재는 기본값 사용
            nutrition = {"calories": 100, "protein": 5, "carbs": 15, "fat": 3}
        else:
            nutrition = NUTRITION_DB[name]

        # 영양소 누적
        for key in total_nutrition:
            total_nutrition[key] += nutrition[key] * quantity

    # 소수점 1자리로 반올림
    return {k: round(v, 1) for k, v in total_nutrition.items()}
```

### 2.4 Tools Registry

**파일**: `backend/app/octostrator/tools/__init__.py`

```python
"""Tools Registry

모든 Tool 함수를 등록하는 단순 Dict
"""
from .vector_search_tool import vector_search_tool
from .db_query_tool import db_query_tool
from .llm_call_tool import llm_call_tool
from .calculate_nutrition_tool import calculate_nutrition_tool

# Tools Dict
TOOLS = {
    "vector_search": vector_search_tool,
    "db_query": db_query_tool,
    "llm_call": llm_call_tool,
    "calculate_nutrition": calculate_nutrition_tool,
}


def get_tool(name: str):
    """Tool 함수 가져오기

    Args:
        name: Tool 이름

    Returns:
        Tool 함수

    Raises:
        ValueError: 존재하지 않는 Tool

    Example:
        tool = get_tool("vector_search")
        results = await tool(query="운동", k=5)
    """
    if name not in TOOLS:
        raise ValueError(f"Tool '{name}' not found. Available: {list(TOOLS.keys())}")
    return TOOLS[name]


def list_tools() -> list[str]:
    """사용 가능한 Tool 목록 반환"""
    return list(TOOLS.keys())


__all__ = [
    "TOOLS",
    "get_tool",
    "list_tools",
    # 개별 Tool
    "vector_search_tool",
    "db_query_tool",
    "llm_call_tool",
    "calculate_nutrition_tool",
]
```

### 2.5 Tool 사용 예시

#### Agent에서 Tool 사용

```python
# agents/diet/agent.py (리팩토링 후)

from backend.app.octostrator.tools import get_tool

async def diet_agent_node(state: SupervisorState) -> Dict:
    """식단 에이전트"""

    step = state["plan"][state["current_step"]]

    # ✅ Tool 사용 (DB 직접 접근 대신)
    db_query = get_tool("db_query")
    meal_logs = await db_query(
        table="meal_logs",
        filters={"user_id": 1},
        order_by="-date",
        limit=3
    )

    # ✅ 영양소 계산 Tool 사용
    if meal_logs:
        calculate_nutrition = get_tool("calculate_nutrition")
        for log in meal_logs:
            nutrition = await calculate_nutrition(
                foods=log["foods"]  # JSON 파싱 후
            )
            log["nutrition"] = nutrition

    # 결과 포맷팅
    result_text = format_meal_logs(meal_logs)

    return {
        "messages": [AIMessage(content=result_text)],
        "plan": update_plan_status(state["plan"], state["current_step"], result_text)
    }
```

---

## 3. SubGraphs 구현 계획

### 3.1 디렉토리 구조

```
backend/app/octostrator/sub_graphs/
├── __init__.py                      # SUBGRAPHS Dict 및 get_subgraph()
├── rag_subgraph.py                  # RAG (검색 + 요약)
├── validation_subgraph.py           # 입력 검증
└── nutrition_calculation_subgraph.py # 영양소 계산 (복잡한 로직)
```

### 3.2 SubGraph 인터페이스 설계

**SubGraph Builder 함수**:
```python
from langgraph.graph import StateGraph

def build_<subgraph_name>() -> StateGraph:
    """SubGraph 빌더 함수

    Returns:
        CompiledGraph: 컴파일된 서브그래프
    """
    graph = StateGraph(SubGraphState)

    # 노드 추가
    graph.add_node("node1", node1_func)
    graph.add_node("node2", node2_func)

    # 엣지 정의
    graph.add_edge("node1", "node2")

    return graph.compile()
```

### 3.3 SubGraph 구현 예시

#### SubGraph 1: rag_subgraph

**파일**: `backend/app/octostrator/sub_graphs/rag_subgraph.py`

```python
"""RAG SubGraph

벡터 검색 + LLM 요약을 하나의 서브그래프로 구성
"""
from typing import TypedDict, Annotated, Sequence
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import BaseMessage, AIMessage
from langgraph.graph.message import add_messages
from backend.app.octostrator.tools import get_tool


class RAGState(TypedDict):
    """RAG SubGraph State"""
    messages: Annotated[Sequence[BaseMessage], add_messages]
    query: str
    search_results: list[dict]
    summary: str


async def search_node(state: RAGState) -> dict:
    """벡터 검색 노드"""
    vector_search = get_tool("vector_search")

    results = await vector_search(
        query=state["query"],
        k=5
    )

    return {"search_results": results}


async def summarize_node(state: RAGState) -> dict:
    """요약 노드"""
    llm_call = get_tool("llm_call")

    # 검색 결과를 텍스트로 변환
    context = "\n\n".join([
        f"[{i+1}] {result['content']}"
        for i, result in enumerate(state["search_results"])
    ])

    prompt = f"""
다음 검색 결과를 바탕으로 질문에 답변하세요.

질문: {state['query']}

검색 결과:
{context}

답변:
"""

    summary = await llm_call(prompt=prompt)

    return {
        "summary": summary,
        "messages": [AIMessage(content=summary)]
    }


def build_rag_subgraph() -> StateGraph:
    """RAG SubGraph 빌더

    플로우:
    START → search → summarize → END

    Returns:
        CompiledGraph
    """
    graph = StateGraph(RAGState)

    # 노드 추가
    graph.add_node("search", search_node)
    graph.add_node("summarize", summarize_node)

    # 엣지 정의
    graph.add_edge(START, "search")
    graph.add_edge("search", "summarize")
    graph.add_edge("summarize", END)

    return graph.compile()
```

#### SubGraph 2: validation_subgraph

**파일**: `backend/app/octostrator/sub_graphs/validation_subgraph.py`

```python
"""Validation SubGraph

사용자 입력 검증 및 정규화
"""
from typing import TypedDict, Literal
from langgraph.graph import StateGraph, START, END
from backend.app.octostrator.tools import get_tool


class ValidationState(TypedDict):
    """Validation SubGraph State"""
    input_data: dict
    validation_result: Literal["valid", "invalid"]
    errors: list[str]
    normalized_data: dict


async def validate_node(state: ValidationState) -> dict:
    """검증 노드"""
    input_data = state["input_data"]
    errors = []

    # 검증 로직 (예: 식단 입력 검증)
    if "foods" not in input_data:
        errors.append("식품 정보가 없습니다.")
    elif not input_data["foods"]:
        errors.append("식품 목록이 비어있습니다.")

    for food in input_data.get("foods", []):
        if "name" not in food:
            errors.append(f"식품 이름이 없습니다: {food}")
        if "quantity" not in food:
            errors.append(f"수량이 없습니다: {food}")

    validation_result = "valid" if not errors else "invalid"

    return {
        "validation_result": validation_result,
        "errors": errors
    }


async def normalize_node(state: ValidationState) -> dict:
    """정규화 노드"""
    if state["validation_result"] == "invalid":
        return {"normalized_data": {}}

    input_data = state["input_data"]

    # 정규화 (예: 단위 통일)
    normalized_foods = []
    for food in input_data.get("foods", []):
        normalized_foods.append({
            "name": food["name"].strip(),
            "quantity": float(food["quantity"]),
            "unit": food.get("unit", "개")
        })

    return {
        "normalized_data": {
            "foods": normalized_foods
        }
    }


def build_validation_subgraph() -> StateGraph:
    """Validation SubGraph 빌더"""
    graph = StateGraph(ValidationState)

    graph.add_node("validate", validate_node)
    graph.add_node("normalize", normalize_node)

    graph.add_edge(START, "validate")
    graph.add_edge("validate", "normalize")
    graph.add_edge("normalize", END)

    return graph.compile()
```

### 3.4 SubGraphs Registry

**파일**: `backend/app/octostrator/sub_graphs/__init__.py`

```python
"""SubGraphs Registry

모든 SubGraph 빌더 함수를 등록하는 단순 Dict
"""
from .rag_subgraph import build_rag_subgraph
from .validation_subgraph import build_validation_subgraph

# SubGraphs Dict (빌더 함수 저장)
SUBGRAPHS = {
    "rag": build_rag_subgraph,
    "validation": build_validation_subgraph,
}


def get_subgraph(name: str):
    """SubGraph 가져오기

    Args:
        name: SubGraph 이름

    Returns:
        CompiledGraph

    Example:
        rag_graph = get_subgraph("rag")
        result = await rag_graph.ainvoke({"query": "..."})
    """
    if name not in SUBGRAPHS:
        raise ValueError(f"SubGraph '{name}' not found. Available: {list(SUBGRAPHS.keys())}")

    builder = SUBGRAPHS[name]
    return builder()  # 빌더 함수 호출하여 그래프 생성


__all__ = [
    "SUBGRAPHS",
    "get_subgraph",
    "build_rag_subgraph",
    "validation_subgraph",
]
```

### 3.5 SubGraph 사용 예시

#### Agent에서 SubGraph 사용

```python
# agents/coaching/agent.py (리팩토링 후)

from backend.app.octostrator.sub_graphs import get_subgraph

async def coaching_agent_node(state: SupervisorState) -> Dict:
    """코칭 에이전트 - RAG SubGraph 사용"""

    step = state["plan"][state["current_step"]]
    query = step["description"]

    # ✅ RAG SubGraph 사용
    rag_graph = get_subgraph("rag")

    rag_result = await rag_graph.ainvoke({
        "query": query,
        "messages": []
    })

    result_text = rag_result["summary"]

    return {
        "messages": [AIMessage(content=result_text)],
        "plan": update_plan_status(state["plan"], state["current_step"], result_text)
    }
```

---

## 4. Metadata 통합 계획 (Phase 3) ⭐ 신규

### 4.1 개요

**목적**: Agent 메타데이터를 Planning 및 Executor 노드에 통합하여 속도 최적화

**핵심 통합 포인트**:
1. **Planning 노드**: Capability 기반 Agent 검색 + Priority 정렬
2. **Executor 노드**: Enabled 플래그 체크
3. **Task 스케줄링**: Priority 순 실행 순서 결정

### 4.2 Planning 노드 개선

**파일**: `backend/app/octostrator/supervisor/nodes/planning.py` (수정)

**Before (현재)**:
```python
# 하드코딩된 Agent 선택
async def planning_node(state: SupervisorState, llm) -> Dict:
    user_intent = state["user_intent"]

    # ❌ 수동 if-else 분기
    if "식단" in user_intent:
        agent = "diet"
    elif "운동" in user_intent:
        agent = "workout"
    # ...

    plan = [{"agent": agent, "description": "..."}]
    return {"plan": plan}
```

**After (메타데이터 통합)**:
```python
from backend.app.octostrator.agents.metadata import (
    AGENT_METADATA,
    find_agents_by_capability,
    list_agents
)

async def planning_node(state: SupervisorState, llm) -> Dict:
    """Planning Agent (메타데이터 기반 개선)

    ⚡ 속도 최적화:
    - Capability 기반 Agent 자동 검색
    - Priority 순 정렬
    - Enabled 체크
    """
    user_intent = state["user_intent"]

    # ⭐ Step 1: Capability 기반 Agent 후보 검색
    candidate_agents = None

    # 키워드 기반 입력 타입 매핑
    if "식단" in user_intent or "영양" in user_intent or "먹" in user_intent:
        candidate_agents = find_agents_by_capability(input_type="meal_query")
    elif "운동" in user_intent or "루틴" in user_intent:
        candidate_agents = find_agents_by_capability(input_type="workout_query")
    elif "스케줄" in user_intent or "예약" in user_intent:
        candidate_agents = find_agents_by_capability(input_type="schedule_query")
    elif "진행" in user_intent or "리포트" in user_intent:
        candidate_agents = find_agents_by_capability(input_type="progress_query")
    elif "검색" in user_intent or "자료" in user_intent or "조언" in user_intent:
        candidate_agents = find_agents_by_capability(input_type="knowledge_query")
    else:
        # 전체 Agent 목록 (Priority 순, Enabled만)
        candidate_agents = list_agents(enabled_only=True)

    # ⭐ Step 2: LLM에게 메타데이터 정보 제공
    agent_descriptions = []
    for agent_name in candidate_agents:
        metadata = AGENT_METADATA[agent_name]
        agent_descriptions.append(
            f"- **{agent_name}** ({metadata['description']})\n"
            f"  Priority: {metadata['priority']}, "
            f"  입력: {', '.join(metadata['capabilities']['input_types'])}, "
            f"  출력: {', '.join(metadata['capabilities']['output_types'])}"
        )

    # ⭐ Step 3: Structured Output으로 Plan 생성
    prompt = f"""
사용자 의도: {user_intent}

사용 가능한 Agents (우선순위 순으로 정렬됨):
{chr(10).join(agent_descriptions)}

다음 형식으로 작업 계획을 생성하세요:
1. 사용자 의도를 달성하기 위한 Task 리스트
2. 각 Task에 적절한 Agent 선택
3. Task 간 의존성 고려

출력: TaskPlan (tasks 필드에 TaskStep 리스트)
"""

    # Structured Output
    from backend.app.octostrator.supervisor.schemas import TaskPlan

    structured_llm = llm.with_structured_output(TaskPlan)
    plan_response = await structured_llm.ainvoke(prompt)

    # ⭐ Step 4: Plan에 메타데이터 추가 및 Priority 정렬
    tasks_with_metadata = []
    for task in plan_response.tasks:
        task_dict = task.model_dump()

        # 메타데이터 추가
        if task.agent in AGENT_METADATA:
            metadata = AGENT_METADATA[task.agent]
            task_dict["priority"] = metadata["priority"]
            task_dict["enabled"] = metadata["enabled"]
            task_dict["required_tools"] = metadata["capabilities"]["required_tools"]

        tasks_with_metadata.append(task_dict)

    # ⭐ Priority 내림차순 정렬 (중요한 Agent 먼저 실행)
    tasks_with_metadata.sort(key=lambda t: t.get("priority", 0), reverse=True)

    return {
        "plan": tasks_with_metadata,
        "current_step": 0,
        "is_planning": False,
        "is_executing": True
    }
```

**개선 효과**:
- ⚡ **자동 Agent 검색**: 수동 if-else 제거
- ⚡ **Priority 정렬**: 중요한 Agent 우선 실행
- ⚡ **메타데이터 활용**: LLM이 더 나은 선택 가능

### 4.3 Executor 노드 개선

**파일**: `backend/app/octostrator/supervisor/nodes/executor.py` (수정)

**Before (현재)**:
```python
async def executor_node(state: SupervisorState) -> Command:
    """Executor - Task 실행"""

    step = state["plan"][state["current_step"]]
    agent_name = step["agent"]

    # ❌ Enabled 체크 없음
    return Command(
        update={"plan": updated_plan},
        goto=agent_name
    )
```

**After (메타데이터 통합)**:
```python
from backend.app.octostrator.agents.metadata import AGENT_METADATA

async def executor_node(state: SupervisorState) -> Command:
    """Executor (Enabled 체크 + 메타데이터 활용)

    ⚡ 속도 최적화:
    - Enabled=False인 Agent 스킵
    - Tool 의존성 검증
    """

    if state["current_step"] >= len(state["plan"]):
        # 모든 Task 완료
        return Command(goto="aggregator")

    step = state["plan"][state["current_step"]]
    agent_name = step["agent"]

    # ⭐ Step 1: Enabled 체크
    if agent_name in AGENT_METADATA:
        metadata = AGENT_METADATA[agent_name]

        if not metadata["enabled"]:
            # ⚡ 비활성화된 Agent 스킵
            print(f"⏭️  Skipping disabled agent: {agent_name}")

            # Plan 업데이트
            updated_plan = list(state["plan"])
            updated_plan[state["current_step"]]["status"] = "skipped"
            updated_plan[state["current_step"]]["result"] = f"Agent '{agent_name}' is disabled"

            # 다음 Task로
            return Command(
                update={
                    "plan": updated_plan,
                    "current_step": state["current_step"] + 1
                },
                goto="executor"  # 재귀 호출
            )

        # ⭐ Step 2: Tool 의존성 검증 (선택적)
        required_tools = metadata["capabilities"]["required_tools"]
        from backend.app.octostrator.tools import TOOLS

        missing_tools = [tool for tool in required_tools if tool not in TOOLS]
        if missing_tools:
            # Tool 누락 경고
            print(f"⚠️  Agent '{agent_name}' requires missing tools: {missing_tools}")

    # ⭐ Step 3: 정상 실행
    print(f"▶️  Executing agent: {agent_name} (Priority: {step.get('priority', 'N/A')})")

    # Plan 업데이트
    updated_plan = list(state["plan"])
    updated_plan[state["current_step"]]["status"] = "running"

    return Command(
        update={"plan": updated_plan},
        goto=agent_name  # Agent 노드로 라우팅
    )
```

**개선 효과**:
- ⚡ **불필요한 실행 스킵**: Enabled=False 체크
- ⚡ **Tool 의존성 검증**: 누락된 Tool 사전 감지
- ⚡ **명확한 로깅**: Priority 정보 출력

### 4.4 구현 체크리스트 (Phase 3)

**Day 1: Planning 노드 개선**
- [ ] `planning.py`에 metadata import 추가
- [ ] `find_agents_by_capability()` 통합
- [ ] LLM 프롬프트에 Agent 메타데이터 포함
- [ ] Priority 순 Task 정렬 로직 추가
- [ ] 테스트 업데이트

**Day 2: Executor 노드 개선**
- [ ] `executor.py`에 metadata import 추가
- [ ] Enabled 체크 로직 추가
- [ ] Tool 의존성 검증 추가
- [ ] 로깅 개선 (Priority 표시)
- [ ] 테스트 업데이트

**Day 3: 통합 테스트**
- [ ] Planning → Executor 플로우 테스트
- [ ] Enabled=False Agent 스킵 테스트
- [ ] Priority 순 실행 확인
- [ ] End-to-End 시나리오 테스트

### 4.5 통합 테스트 예시

**파일**: `tests/test_supervisor/test_metadata_integration.py` (신규)

```python
import pytest
from backend.app.octostrator.supervisor.graph import build_supervisor_graph
from backend.app.octostrator.agents.metadata import set_enabled


@pytest.mark.asyncio
async def test_planning_with_capability_search():
    """Planning이 Capability 기반으로 Agent 검색하는지 확인"""
    graph = build_supervisor_graph()

    result = await graph.ainvoke(
        {
            "messages": [HumanMessage(content="최근 식단 조회해줘")],
            "user_query": "최근 식단 조회해줘"
        },
        config={"configurable": {"thread_id": "test-capability"}}
    )

    # Plan에 "diet" Agent 포함 확인
    assert "plan" in result
    assert len(result["plan"]) > 0
    assert result["plan"][0]["agent"] == "diet"


@pytest.mark.asyncio
async def test_executor_skips_disabled_agent():
    """Executor가 disabled Agent를 스킵하는지 확인"""

    # "schedule" Agent 비활성화
    set_enabled("schedule", False)

    graph = build_supervisor_graph()

    result = await graph.ainvoke(
        {
            "messages": [HumanMessage(content="내일 스케줄 확인해줘")],
            "user_query": "내일 스케줄 확인해줘"
        },
        config={"configurable": {"thread_id": "test-disabled"}}
    )

    # Plan에 schedule이 있지만 status가 "skipped"인지 확인
    schedule_task = next(
        (task for task in result["plan"] if task["agent"] == "schedule"),
        None
    )

    if schedule_task:
        assert schedule_task["status"] == "skipped"
        assert "disabled" in schedule_task.get("result", "").lower()

    # 복원
    set_enabled("schedule", True)


@pytest.mark.asyncio
async def test_priority_based_task_ordering():
    """Priority 순으로 Task가 정렬되는지 확인"""

    graph = build_supervisor_graph()

    result = await graph.ainvoke(
        {
            "messages": [HumanMessage(content="식단과 운동 루틴 조회해줘")],
            "user_query": "식단과 운동 루틴 조회해줘"
        },
        config={"configurable": {"thread_id": "test-priority"}}
    )

    plan = result["plan"]

    # "workout" (priority=8)이 "diet" (priority=5)보다 먼저 나와야 함
    workout_idx = next((i for i, t in enumerate(plan) if t["agent"] == "workout"), -1)
    diet_idx = next((i for i, t in enumerate(plan) if t["agent"] == "diet"), -1)

    if workout_idx >= 0 and diet_idx >= 0:
        assert workout_idx < diet_idx, "Workout should be executed before diet (higher priority)"
```

### 4.6 예상 성능 개선

**Before (메타데이터 없음)**:
```
Planning: 수동 if-else 분기 (유지보수 어려움)
Executor: 모든 Agent 무조건 실행
결과: 불필요한 Agent도 실행, 순서 최적화 없음
```

**After (메타데이터 통합)**:
```
Planning: Capability 자동 검색 (10ms)
Executor: Enabled 체크로 스킵 (1ms)
결과: ⚡ 불필요한 Agent 제거, Priority 순 실행
```

**속도 향상**:
- 비활성화 Agent 3개 스킵 → 약 600ms 절약 (Agent당 200ms 가정)
- Priority 정렬 → 중요 Task 먼저 → 사용자 체감 속도 향상

---

## 5. Agent 리팩토링 계획 (Phase 4)

### 4.1 리팩토링 전략

**목표**: Mock 데이터 조회 → Tools 사용으로 변경

**원칙**:
1. DB 직접 접근 금지 → `db_query` Tool 사용
2. LLM 직접 호출 금지 → `llm_call` Tool 사용
3. 복잡한 로직 → SubGraph로 분리

### 4.2 DietAgent 리팩토링 예시

#### Before (현재)

```python
# agents/diet/agent.py (현재)

async def diet_agent_node(state: SupervisorState) -> Dict:
    # ❌ DB 직접 접근
    with get_db() as db:
        meal_logs = db.query(MealLog).order_by(MealLog.date.desc()).limit(3).all()

    # ❌ 수동 포맷팅
    result_text = "최근 식단:\n"
    for log in meal_logs:
        result_text += f"- {log.date} ..."

    return {"messages": [...], "plan": ...}
```

#### After (리팩토링 후)

```python
# agents/diet/agent.py (리팩토링 후)

from backend.app.octostrator.tools import get_tool
from backend.app.octostrator.sub_graphs import get_subgraph

async def diet_agent_node(state: SupervisorState) -> Dict:
    step = state["plan"][state["current_step"]]

    # ✅ Tool 사용
    db_query = get_tool("db_query")
    calculate_nutrition = get_tool("calculate_nutrition")

    # 1. DB 조회
    meal_logs = await db_query(
        table="meal_logs",
        filters={"user_id": 1},
        order_by="-date",
        limit=3
    )

    # 2. 영양소 계산
    for log in meal_logs:
        nutrition = await calculate_nutrition(foods=log["foods"])
        log["nutrition"] = nutrition

    # 3. LLM으로 피드백 생성
    llm_call = get_tool("llm_call")

    prompt = f"""
    사용자의 최근 식단 기록:
    {format_meal_logs(meal_logs)}

    일일 목표 대비 피드백을 생성하세요.
    """

    feedback = await llm_call(prompt=prompt)

    return {
        "messages": [AIMessage(content=feedback)],
        "plan": update_plan_status(state["plan"], state["current_step"], feedback)
    }
```

### 4.3 리팩토링 체크리스트

**각 Agent별 작업**:

- [ ] DietAgent
  - [ ] `db_query` Tool로 DB 조회
  - [ ] `calculate_nutrition` Tool로 영양소 계산
  - [ ] `llm_call` Tool로 피드백 생성

- [ ] WorkoutAgent
  - [ ] `db_query` Tool로 ExerciseDB 조회
  - [ ] `db_query` Tool로 User 프로필 조회
  - [ ] `llm_call` Tool로 루틴 생성
  - [ ] `db_query` Tool로 WorkoutRoutine 저장

- [ ] ScheduleAgent
  - [ ] `db_query` Tool로 Schedule CRUD
  - [ ] `llm_call` Tool로 일정 추천

- [ ] MemberCareAgent
  - [ ] `db_query` Tool로 MemberProgress 조회
  - [ ] `llm_call` Tool로 리포트 생성

- [ ] CoachingAgent
  - [ ] `rag` SubGraph 사용 (벡터 검색 + 요약)

---

## 6. Adapter 패턴 구현 (Phase 6) ⭐ 선택적

### 6.1 개요

**목적**: 레퍼런스 AgentAdapter 패턴 채택 (동적 Agent 실행 지원)

**우선순위**: Low (Phase 0-5 완료 후 검토)

**효과**:
- ⚡ 런타임에 Agent 선택 및 실행 가능
- ⚡ 의존성 정보 조회
- ⚡ 다형성 지원 (LangGraph, Async, Sync)

### 6.2 Adapter 구조 설계

**파일**: `backend/app/octostrator/agents/adapter.py` (신규)

```python
"""Agent Adapter - 동적 Agent 실행 지원

레퍼런스 AgentAdapter 구조 채택 (단순화)
- 동적 Agent 실행
- 의존성 정보 조회
- LangGraph Node 방식과 호환
"""

from typing import Dict, Any, Callable
from backend.app.octostrator.agents.metadata import AGENT_METADATA
from backend.app.octostrator.agents import (
    diet_agent_node,
    workout_agent_node,
    schedule_agent_node,
    member_care_agent_node,
    coaching_agent_node,
)
from backend.app.octostrator.states.supervisor_state import SupervisorState


# Node 함수 매핑 (레퍼런스의 agent_class 대신 함수 사용)
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
    """동적 Agent 실행 (레퍼런스 방식)

    ⚡ 속도 최적화:
    - Enabled 체크
    - Tool 의존성 검증

    Args:
        agent_name: Agent 이름
        state: SupervisorState

    Returns:
        Agent 실행 결과

    Raises:
        ValueError: 존재하지 않는 Agent
        RuntimeError: Agent 실행 오류
    """

    # Step 1: 메타데이터 확인
    if agent_name not in AGENT_METADATA:
        return {"error": f"Unknown agent: {agent_name}"}

    metadata = AGENT_METADATA[agent_name]

    # Step 2: Enabled 체크
    if not metadata["enabled"]:
        return {
            "status": "skipped",
            "reason": f"Agent '{agent_name}' is disabled"
        }

    # Step 3: 노드 함수 가져오기
    node_func = AGENT_NODES.get(agent_name)
    if not node_func:
        return {"error": f"Node function not found: {agent_name}"}

    # Step 4: 실행
    try:
        result = await node_func(state)
        return result
    except Exception as e:
        return {
            "error": str(e),
            "agent": agent_name,
            "status": "failed"
        }


def get_agent_dependencies(agent_name: str) -> Dict[str, Any]:
    """Agent 의존성 정보 조회 (레퍼런스 방식)

    Args:
        agent_name: Agent 이름

    Returns:
        의존성 정보 Dict

    Example:
        >>> get_agent_dependencies("diet")
        {
            "requires": ["meal_query", "nutrition_query"],
            "provides": ["meal_analysis", "nutrition_recommendation"],
            "tools": ["db_query", "calculate_nutrition", "llm_call"],
            "team": "fitness",
            "priority": 5
        }
    """
    metadata = AGENT_METADATA.get(agent_name)
    if not metadata:
        return {}

    caps = metadata["capabilities"]

    return {
        "requires": caps["input_types"],
        "provides": caps["output_types"],
        "tools": caps["required_tools"],
        "team": metadata["team"],
        "priority": metadata["priority"],
        "enabled": metadata["enabled"],
    }


def validate_agent_chain(agent_names: list[str]) -> Dict[str, Any]:
    """Agent 체인 검증 (선택적)

    여러 Agent를 순차 실행할 때 의존성 검증

    Args:
        agent_names: Agent 이름 리스트 (실행 순서)

    Returns:
        검증 결과
        {
            "valid": bool,
            "errors": list[str],
            "warnings": list[str]
        }

    Example:
        >>> validate_agent_chain(["diet", "member_care"])
        {
            "valid": True,
            "errors": [],
            "warnings": []
        }
    """
    errors = []
    warnings = []

    # Agent 존재 확인
    for agent_name in agent_names:
        if agent_name not in AGENT_METADATA:
            errors.append(f"Unknown agent: {agent_name}")

    # Enabled 체크
    for agent_name in agent_names:
        if agent_name in AGENT_METADATA:
            if not AGENT_METADATA[agent_name]["enabled"]:
                warnings.append(f"Agent '{agent_name}' is disabled")

    # Tool 의존성 체크
    from backend.app.octostrator.tools import TOOLS

    for agent_name in agent_names:
        if agent_name in AGENT_METADATA:
            deps = get_agent_dependencies(agent_name)
            missing_tools = [tool for tool in deps["tools"] if tool not in TOOLS]
            if missing_tools:
                errors.append(f"Agent '{agent_name}' requires missing tools: {missing_tools}")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings
    }


__all__ = [
    "AGENT_NODES",
    "execute_agent_dynamic",
    "get_agent_dependencies",
    "validate_agent_chain",
]
```

### 6.3 Adapter 사용 예시

**예시 1: 동적 Agent 실행**

```python
from backend.app.octostrator.agents.adapter import execute_agent_dynamic

async def custom_executor(state: SupervisorState):
    """커스텀 Executor (Adapter 사용)"""

    # 런타임에 Agent 선택
    agent_name = determine_agent_from_context(state)

    # 동적 실행
    result = await execute_agent_dynamic(agent_name, state)

    return result
```

**예시 2: 의존성 조회**

```python
from backend.app.octostrator.agents.adapter import get_agent_dependencies

# Agent 정보 조회
deps = get_agent_dependencies("diet")
print(f"Required tools: {deps['tools']}")
# → ["db_query", "calculate_nutrition", "llm_call"]
```

**예시 3: Agent 체인 검증**

```python
from backend.app.octostrator.agents.adapter import validate_agent_chain

# Planning에서 생성한 Agent 체인 검증
agent_chain = ["diet", "workout", "member_care"]
validation = validate_agent_chain(agent_chain)

if not validation["valid"]:
    print(f"Errors: {validation['errors']}")
```

### 6.4 구현 체크리스트 (Phase 6)

**Day 1**:
- [ ] `agents/adapter.py` 파일 생성
- [ ] AGENT_NODES Dict 정의
- [ ] `execute_agent_dynamic()` 구현

**Day 2**:
- [ ] `get_agent_dependencies()` 구현
- [ ] `validate_agent_chain()` 구현
- [ ] 단위 테스트 작성

**산출물**:
- `backend/app/octostrator/agents/adapter.py`
- `tests/test_agents/test_adapter.py`

---

## 7. 구현 Phase별 계획 (전체 통합)

### Phase 0: Agent 메타데이터 레이어 (3일) ⭐ 최우선

**Day 1**:
- [ ] `agents/metadata.py` 파일 생성
- [ ] AgentCapabilities, AgentMetadata TypedDict 정의
- [ ] AGENT_METADATA Dict에 5개 Agent 정의

**Day 2**:
- [ ] `get_metadata()`, `list_agents()` 구현
- [ ] `find_agents_by_capability()` 구현
- [ ] `set_enabled()`, `get_team_agents()` 구현

**Day 3**:
- [ ] 메타데이터 단위 테스트 작성
- [ ] 검색 함수 테스트
- [ ] Priority 정렬 테스트

**산출물**:
- `backend/app/octostrator/agents/metadata.py`
- `tests/test_agents/test_metadata.py`

### Phase 1: Tools 구현 (1주)

**Day 1-2**: Core Tools
- [ ] `vector_search_tool.py` 구현
- [ ] `db_query_tool.py` 구현
- [ ] `llm_call_tool.py` 구현
- [ ] `tools/__init__.py` (TOOLS Dict)

**Day 3-4**: Domain Tools
- [ ] `calculate_nutrition_tool.py` 구현
- [ ] `parse_meal_input_tool.py` 구현
- [ ] `generate_workout_tool.py` 구현

**Day 5**: 테스트
- [ ] 각 Tool 단위 테스트
- [ ] Integration 테스트

**산출물**:
- `backend/app/octostrator/tools/` (6개 파일)
- `tests/test_tools/` (6개 테스트 파일)

### Phase 2: SubGraphs 구현 (1주)

**Day 1-2**: RAG SubGraph
- [ ] `rag_subgraph.py` 구현
- [ ] State 정의 (RAGState)
- [ ] 노드 구현 (search, summarize)

**Day 3-4**: Validation SubGraph
- [ ] `validation_subgraph.py` 구현
- [ ] State 정의 (ValidationState)
- [ ] 노드 구현 (validate, normalize)

**Day 5**: Registry 및 테스트
- [ ] `sub_graphs/__init__.py` (SUBGRAPHS Dict)
- [ ] SubGraph 테스트

**산출물**:
- `backend/app/octostrator/sub_graphs/` (3개 파일)
- `tests/test_sub_graphs/` (2개 테스트 파일)

### Phase 3: Agent 리팩토링 (1주)

**Day 1**: DietAgent
- [ ] Mock → Tools 사용으로 변경
- [ ] 테스트 업데이트

**Day 2**: WorkoutAgent
- [ ] Mock → Tools 사용으로 변경
- [ ] 테스트 업데이트

**Day 3**: ScheduleAgent + MemberCareAgent
- [ ] Mock → Tools 사용으로 변경
- [ ] 테스트 업데이트

**Day 4**: CoachingAgent
- [ ] Mock → RAG SubGraph 사용으로 변경
- [ ] 테스트 업데이트

**Day 5**: 통합 테스트
- [ ] End-to-End 플로우 테스트
- [ ] 성능 테스트

**산출물**:
- 리팩토링된 5개 Agent
- 업데이트된 테스트

### Phase 4: 테스트 및 문서화 (1주)

**Day 1-3**: 테스트
- [ ] 모든 Tool 단위 테스트
- [ ] 모든 SubGraph 통합 테스트
- [ ] 모든 Agent End-to-End 테스트
- [ ] 커버리지 80% 이상

**Day 4-5**: 문서화
- [ ] Tools API 문서
- [ ] SubGraphs 사용 가이드
- [ ] Agent 리팩토링 가이드
- [ ] README 업데이트

**산출물**:
- `tests/` (완전한 테스트 스위트)
- `docs/TOOLS_GUIDE.md`
- `docs/SUBGRAPHS_GUIDE.md`

---

## 6. 디렉토리 최종 구조

```
backend/app/
├── registry/                        # ❌ 비움 (사용 안 함)
│   └── __init__.py                  # (빈 파일 유지)
│
├── octostrator/
│   ├── agents/                      # ✅ 5개 Agent (리팩토링)
│   │   ├── diet/
│   │   │   └── agent.py             # Tools 사용
│   │   ├── workout/
│   │   │   └── agent.py             # Tools 사용
│   │   ├── schedule/
│   │   │   └── agent.py             # Tools 사용
│   │   ├── member_care/
│   │   │   └── agent.py             # Tools 사용
│   │   └── coaching/
│   │       └── agent.py             # RAG SubGraph 사용
│   │
│   ├── tools/                       # ✅ 신규 구현
│   │   ├── __init__.py              # TOOLS Dict + get_tool()
│   │   ├── vector_search_tool.py
│   │   ├── db_query_tool.py
│   │   ├── llm_call_tool.py
│   │   ├── calculate_nutrition_tool.py
│   │   ├── parse_meal_input_tool.py
│   │   └── generate_workout_tool.py
│   │
│   ├── sub_graphs/                  # ✅ 신규 구현
│   │   ├── __init__.py              # SUBGRAPHS Dict + get_subgraph()
│   │   ├── rag_subgraph.py
│   │   ├── validation_subgraph.py
│   │   └── nutrition_calculation_subgraph.py
│   │
│   ├── supervisor/                  # ✅ 기존 유지
│   ├── states/                      # ✅ 기존 유지
│   ├── contexts/                    # ✅ 기존 유지
│   ├── session/                     # ✅ 기존 유지
│   └── checkpointer/                # ✅ 기존 유지
│
└── config/                          # ✅ 기존 유지
```

---

## 7. 테스트 전략

### 7.1 Tool 테스트

```python
# tests/test_tools/test_db_query_tool.py

import pytest
from backend.app.octostrator.tools import get_tool

@pytest.mark.asyncio
async def test_db_query_tool_basic():
    """기본 DB 조회 테스트"""
    db_query = get_tool("db_query")

    results = await db_query(
        table="users",
        filters={"id": 1}
    )

    assert len(results) > 0
    assert results[0]["name"] == "김철수"

@pytest.mark.asyncio
async def test_db_query_tool_with_order():
    """정렬 테스트"""
    db_query = get_tool("db_query")

    results = await db_query(
        table="meal_logs",
        order_by="-date",
        limit=3
    )

    assert len(results) <= 3
    # 날짜 내림차순 확인
    assert results[0]["date"] >= results[1]["date"]

@pytest.mark.asyncio
async def test_db_query_tool_invalid_table():
    """잘못된 테이블 이름 테스트"""
    db_query = get_tool("db_query")

    with pytest.raises(ValueError, match="Unknown table"):
        await db_query(table="invalid_table")
```

### 7.2 SubGraph 테스트

```python
# tests/test_sub_graphs/test_rag_subgraph.py

import pytest
from backend.app.octostrator.sub_graphs import get_subgraph

@pytest.mark.asyncio
async def test_rag_subgraph():
    """RAG SubGraph 전체 플로우 테스트"""
    rag_graph = get_subgraph("rag")

    result = await rag_graph.ainvoke({
        "query": "운동 전 스트레칭",
        "messages": []
    })

    assert "search_results" in result
    assert len(result["search_results"]) > 0
    assert "summary" in result
    assert len(result["summary"]) > 0
    assert len(result["messages"]) > 0
```

### 7.3 Agent 통합 테스트

```python
# tests/test_agents/test_diet_agent_integration.py

import pytest
from backend.app.octostrator.supervisor.graph import build_supervisor_graph

@pytest.mark.asyncio
async def test_diet_agent_full_flow():
    """DietAgent 전체 플로우 테스트 (Tools 사용)"""

    graph = build_supervisor_graph()

    result = await graph.ainvoke(
        {
            "messages": [HumanMessage(content="최근 식단 조회해줘")],
            "user_query": "최근 식단 조회해줘"
        },
        config={"configurable": {"thread_id": "test-123"}}
    )

    # Planning 확인
    assert "plan" in result
    assert len(result["plan"]) > 0
    assert result["plan"][0]["agent"] == "diet"

    # 실행 결과 확인
    assert result["plan"][0]["status"] == "completed"
    assert result["plan"][0]["result"] is not None

    # 메시지 확인
    assert len(result["messages"]) > 0
```

---

## 8. 마이그레이션 가이드

### 8.1 기존 코드 → 새 코드

#### 예시 1: DB 조회

```python
# ❌ Before
from backend.database.relation_db.session import get_db
from backend.database.relation_db.models import MealLog

with get_db() as db:
    meal_logs = db.query(MealLog).filter(MealLog.user_id == 1).all()

# ✅ After
from backend.app.octostrator.tools import get_tool

db_query = get_tool("db_query")
meal_logs = await db_query(
    table="meal_logs",
    filters={"user_id": 1}
)
```

#### 예시 2: 벡터 검색

```python
# ❌ Before
from backend.database.vector_db.faiss_manager import FAISSManager

faiss_manager = FAISSManager()
results = faiss_manager.similarity_search(query, k=3)

# ✅ After
from backend.app.octostrator.tools import get_tool

vector_search = get_tool("vector_search")
results = await vector_search(query=query, k=3)
```

#### 예시 3: LLM 호출

```python
# ❌ Before
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4o-mini")
response = await llm.ainvoke([HumanMessage(content=prompt)])
text = response.content

# ✅ After
from backend.app.octostrator.tools import get_tool

llm_call = get_tool("llm_call")
text = await llm_call(prompt=prompt)
```

---

## 9. 성능 고려사항

### 9.1 Tool 캐싱

**문제**: 같은 Tool을 여러 번 호출 시 오버헤드

**해결**:
```python
# tools/__init__.py

# Tool 인스턴스 캐싱 (필요한 경우)
_TOOL_CACHE = {}

def get_tool_cached(name: str, context: dict = None):
    """Tool 캐싱 (선택적)"""
    cache_key = (name, id(context))

    if cache_key not in _TOOL_CACHE:
        tool = TOOLS[name]
        # 필요하면 partial 적용
        if context:
            tool = lambda **kwargs: TOOLS[name](context=context, **kwargs)
        _TOOL_CACHE[cache_key] = tool

    return _TOOL_CACHE[cache_key]
```

### 9.2 SubGraph 재사용

**문제**: SubGraph를 매번 compile하면 느림

**해결**:
```python
# sub_graphs/__init__.py

# 컴파일된 그래프 캐싱
_COMPILED_GRAPHS = {}

def get_subgraph(name: str):
    """SubGraph 캐싱"""
    if name not in _COMPILED_GRAPHS:
        builder = SUBGRAPHS[name]
        _COMPILED_GRAPHS[name] = builder()

    return _COMPILED_GRAPHS[name]
```

---

## 10. 에러 처리

### 10.1 Tool 에러

```python
# tools/base.py (공통)

class ToolError(Exception):
    """Tool 실행 오류"""
    pass

class ToolNotFoundError(ToolError):
    """Tool을 찾을 수 없음"""
    pass

class ToolExecutionError(ToolError):
    """Tool 실행 중 오류"""
    pass


# 사용 예시
try:
    tool = get_tool("db_query")
    results = await tool(table="users")
except ToolNotFoundError as e:
    # Tool 없음
    print(f"Tool not found: {e}")
except ToolExecutionError as e:
    # 실행 오류
    print(f"Execution error: {e}")
```

### 10.2 Agent에서 에러 처리

```python
async def agent_node(state: SupervisorState) -> Dict:
    try:
        # Tool 사용
        db_query = get_tool("db_query")
        results = await db_query(...)

    except ToolError as e:
        # Tool 오류 → State에 기록
        return {
            "plan": update_plan_error(state["plan"], state["current_step"], str(e)),
            "messages": [AIMessage(content=f"오류 발생: {str(e)}")]
        }
```

---

## 11. 문서화 계획

### 11.1 Tools API 문서

**파일**: `docs/TOOLS_API.md`

```markdown
# Tools API Reference

## vector_search_tool

벡터 검색 Tool

### Parameters
- `query` (str): 검색 쿼리
- `k` (int): 반환 개수
- `filter_metadata` (dict): 메타데이터 필터

### Returns
- `list[dict]`: 검색 결과

### Example
```python
tool = get_tool("vector_search")
results = await tool(query="운동", k=5)
```

## db_query_tool

...
```

### 11.2 SubGraphs 가이드

**파일**: `docs/SUBGRAPHS_GUIDE.md`

```markdown
# SubGraphs 사용 가이드

## RAG SubGraph

### 사용 시나리오
- 전문 자료 검색 + 요약
- FAQ 자동 응답

### 예시
```python
rag_graph = get_subgraph("rag")
result = await rag_graph.ainvoke({"query": "..."})
print(result["summary"])
```

## Validation SubGraph

...
```

---

## 12. 체크리스트

### Phase 1: Tools (1주)
- [ ] `vector_search_tool.py` 구현
- [ ] `db_query_tool.py` 구현
- [ ] `llm_call_tool.py` 구현
- [ ] `calculate_nutrition_tool.py` 구현
- [ ] `parse_meal_input_tool.py` 구현
- [ ] `generate_workout_tool.py` 구현
- [ ] `tools/__init__.py` (TOOLS Dict)
- [ ] Tool 단위 테스트 (6개)

### Phase 2: SubGraphs (1주)
- [ ] `rag_subgraph.py` 구현
- [ ] `validation_subgraph.py` 구현
- [ ] `nutrition_calculation_subgraph.py` 구현
- [ ] `sub_graphs/__init__.py` (SUBGRAPHS Dict)
- [ ] SubGraph 통합 테스트 (3개)

### Phase 3: Agent 리팩토링 (1주)
- [ ] DietAgent 리팩토링 (Tools 사용)
- [ ] WorkoutAgent 리팩토링 (Tools 사용)
- [ ] ScheduleAgent 리팩토링 (Tools 사용)
- [ ] MemberCareAgent 리팩토링 (Tools 사용)
- [ ] CoachingAgent 리팩토링 (RAG SubGraph)
- [ ] Agent 테스트 업데이트 (5개)

### Phase 4: 테스트 및 문서화 (1주)
- [ ] 모든 Tool 테스트 (커버리지 80%+)
- [ ] 모든 SubGraph 테스트 (커버리지 80%+)
- [ ] End-to-End 플로우 테스트
- [ ] `docs/TOOLS_API.md` 작성
- [ ] `docs/SUBGRAPHS_GUIDE.md` 작성
- [ ] `README.md` 업데이트

---

## 13. 마일스톤

| 주차 | 마일스톤 | 완료 조건 |
|------|---------|----------|
| Week 1 | Tools 구현 완료 | 6개 Tool + 테스트 |
| Week 2 | SubGraphs 구현 완료 | 3개 SubGraph + 테스트 |
| Week 3 | Agent 리팩토링 완료 | 5개 Agent Tools 사용 |
| Week 4 | 테스트 및 문서화 완료 | 커버리지 80%+ |

---

## 14. 최종 요약 (v2.0 업데이트)

### 핵심 결정사항

**✅ 구현함 (v1.0 기존)**:
1. Tools (6개) - 단순 Dict Registry
2. SubGraphs (3개) - 단순 Dict Registry
3. Agent 리팩토링 (5개) - Tools 사용

**✅ 신규 추가 (v2.0 - 레퍼런스 반영)**:
4. **Agent 메타데이터 레이어** (Phase 0) ⭐
   - Capabilities (input/output types, required tools)
   - Priority (실행 우선순위)
   - Team (팀 분류)
   - Enabled (활성화/비활성화)

5. **Metadata 통합** (Phase 3) ⭐
   - Planning: Capability 기반 Agent 검색
   - Executor: Enabled 체크
   - Priority 순 Task 정렬

6. **Adapter 패턴** (Phase 6) ⚠️ 선택적
   - 동적 Agent 실행
   - 의존성 정보 조회
   - Agent 체인 검증

**❌ 구현 안 함**:
1. 명시적 싱글톤 Registry 클래스 (레퍼런스 거부)
2. Agent 클래스 인스턴스화 (Stateless 유지)
3. `initialize_all()` 캐싱 (함수는 캐시 불필요)
4. BaseAgent 추상 클래스

**근거**:
- LangGraph 1.0 철학 준수
- 간단하고 명확한 구조
- Stateless 함수가 클래스보다 빠름
- 테스트 용이성
- 유지보수 편의성

### 레퍼런스 비교 결과 요약

| 메커니즘 | 레퍼런스 방식 | 채택 여부 | 이유 |
|---------|-------------|----------|------|
| **Agent 인스턴스 캐싱** | `initialize_all()` | ❌ 거부 | Stateless 함수는 캐시 불필요 |
| **메타데이터 시스템** | AgentMetadata + Capabilities | ✅ **채택** | 속도 최적화 필수 |
| **Capability 검색** | `find_agents_by_capability()` | ✅ **채택** | Planning 자동화 |
| **Priority 정렬** | Registry 정렬 | ✅ **채택** | 실행 순서 최적화 |
| **Enabled 플래그** | Registry 체크 | ✅ **채택** | 불필요한 실행 스킵 |
| **Team 분류** | Team Dict | ✅ **채택** | 검색 범위 축소 |
| **Adapter 패턴** | 동적 실행 | ⚠️ **선택적** | 런타임 유연성 (필요시) |
| **싱글톤 Registry** | `__new__` 싱글톤 | ❌ **거부** | LangGraph 철학 위배 |

### 예상 효과

**개선 효과 (v1.0 기존)**:
- ✅ 코드 중복 제거 (각 Agent가 DB 접근 로직 공유)
- ✅ 테스트 용이 (Tool Mock 주입)
- ✅ 재사용성 향상 (Tool/SubGraph 공유)
- ✅ 확장성 증대 (새 Tool/SubGraph 추가 용이)
- ✅ 문서화 개선 (Tool API 문서)

**속도 향상 (v2.0 신규)** ⚡:
- ⚡⚡ **Capability 검색**: O(n) 자동 검색 (수동 if-else 제거)
- ⚡ **Priority 정렬**: 중요 Agent 우선 실행 (사용자 체감 속도 ↑)
- ⚡ **Enabled 스킵**: 비활성화 Agent 3개 → 약 600ms 절약
- ⚡ **Tool 의존성 검증**: 누락 Tool 사전 감지 (오류 방지)
- ⚡ **메타데이터 기반 LLM**: Agent 선택 정확도 향상

**예상 성과**:
- 코드 라인 수: 30% 감소
- 테스트 커버리지: 80% 이상
- 개발 속도: 2배 향상 (재사용 증가)
- 버그 감소: 50% (중복 제거)
- **응답 속도: 10-30% 향상** (메타데이터 최적화) ⭐

### 구현 우선순위

**High Priority** 🔴 (즉시 시작):
1. **Phase 0**: Agent 메타데이터 레이어 (3일)
2. **Phase 1**: Tools 구현 (1주)
3. **Phase 2**: SubGraphs 구현 (1주)

**Medium Priority** 🟡 (2주 내):
4. **Phase 3**: Metadata 통합 (Planning/Executor) (2일)
5. **Phase 4**: Agent 리팩토링 (1주)
6. **Phase 5**: 테스트 및 문서화 (1주)

**Low Priority** 🟢 (선택적):
7. **Phase 6**: Adapter 패턴 (2일)

### 최종 디렉토리 구조 (v2.0)

```
backend/app/octostrator/
├── agents/
│   ├── __init__.py
│   ├── metadata.py                  # ⭐ 신규 (Phase 0)
│   ├── adapter.py                   # ⚠️ 선택적 (Phase 6)
│   ├── diet/
│   ├── workout/
│   ├── schedule/
│   ├── member_care/
│   └── coaching/
│
├── tools/                           # ✅ Phase 1
│   ├── __init__.py                  # TOOLS Dict
│   ├── vector_search_tool.py
│   ├── db_query_tool.py
│   ├── llm_call_tool.py
│   ├── calculate_nutrition_tool.py
│   ├── parse_meal_input_tool.py
│   └── generate_workout_tool.py
│
├── sub_graphs/                      # ✅ Phase 2
│   ├── __init__.py                  # SUBGRAPHS Dict
│   ├── rag_subgraph.py
│   ├── validation_subgraph.py
│   └── nutrition_calculation_subgraph.py
│
└── supervisor/
    ├── graph.py
    └── nodes/
        ├── planning.py              # ⭐ 수정 (Phase 3)
        ├── executor.py              # ⭐ 수정 (Phase 3)
        └── ...
```

---

**문서 버전**: 2.0
**작성**: Claude (AI Assistant)
**참고 문서**:
- [REFERENCE_COMPARISON_251104.md](./REFERENCE_COMPARISON_251104.md) - 레퍼런스 비교 분석
- [REGISTRY_ANALYSIS_REPORT_251104.md](./REGISTRY_ANALYSIS_REPORT_251104.md) - 현재 구조 분석

**다음 단계**: Phase 0 시작 (Agent 메타데이터 레이어 구현) ⭐

**총 기간**: 5주 (메타데이터 레이어 포함)

---

**변경 이력**:
- v1.0 (2025-11-04): 초기 문서 작성 (Tools/SubGraphs 계획)
- v2.0 (2025-11-04): 레퍼런스 분석 반영 (메타데이터 레이어 추가) ⭐

---

**문서 끝**
