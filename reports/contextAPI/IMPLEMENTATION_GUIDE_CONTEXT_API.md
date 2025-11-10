# LangGraph Context API 구현 가이드

**작성일**: 2025-11-05
**대상 프로젝트**: AI PT Manager Beta v001
**목적**: Context API를 사용한 노드별 LLM 설정 관리 구현

---

## 📋 구현 개요

현재 프로젝트의 문제점과 Context API를 통한 해결 방안을 제시합니다.

### 현재 상태 (Phase 1 완료)

```python
# main_graph.py (현재)
llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.7,
    max_tokens=4096,  # 전역 설정
    api_key=config.openai_api_key
)

# cognitive_nodes.py (현재)
plan_result = await structured_llm.ainvoke(
    [...],
    config={"max_tokens": 2048}  # 노드별 임시 설정
)
```

**문제점**:
- ❌ 전역 max_tokens=4096이 모든 노드에 적용
- ❌ 노드별 설정이 하드코딩됨 (config={"max_tokens": 2048})
- ❌ temperature, top_p 등 다른 파라미터 조정 불가
- ❌ 환경별 설정 분리 없음 (dev/prod 동일)

### 목표 상태 (Phase 2 적용 후)

```python
# contexts/app_context.py (목표)
class LLMSettings(BaseModel):
    planning_temperature: float = 0.3
    planning_max_tokens: int = 2048
    intent_temperature: float = 0.7
    # ... 노드별 설정

# nodes/cognitive_nodes.py (목표)
async def planning_node(state, runtime: Runtime):
    settings = runtime.context.llm_settings
    llm = ChatOpenAI(
        temperature=settings.planning_temperature,
        max_tokens=settings.planning_max_tokens
    )
```

**장점**:
- ✅ 노드별 맞춤 설정
- ✅ 환경별 설정 분리 (production, dev, test)
- ✅ 중앙 관리 (contexts/app_context.py)
- ✅ 타입 검증 (Pydantic)

---

## 🏗️ 구현 단계

### Step 1: LLMSettings 스키마 정의

**파일**: `backend/app/octostrator/contexts/app_context.py`

```python
"""Application Context - 런타임 불변 정보

LangGraph 1.0 Context API 사용
- Context는 State와 별도로 관리되는 불변 런타임 정보
- Checkpoint에 저장되지 않음
- 모든 노드에서 접근 가능
"""
from pydantic import BaseModel, Field
from typing import Optional, Literal


class LLMSettings(BaseModel):
    """노드별 LLM 설정

    각 노드마다 최적화된 LLM 파라미터를 정의합니다.
    """

    # ==================== Cognitive Nodes ====================

    # Intent Understanding Node
    intent_model: str = "gpt-4o-mini"
    intent_temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="의도 파악 시 창의적 해석을 위해 높은 temperature"
    )
    intent_max_tokens: int = Field(
        default=1024,
        ge=1,
        le=16384,
        description="간단한 의도 분류라 1024 토큰이면 충분"
    )

    # Planning Node
    planning_model: str = "gpt-4o-mini"
    planning_temperature: float = Field(
        default=0.3,
        ge=0.0,
        le=2.0,
        description="계획 수립은 정확성 우선, 낮은 temperature"
    )
    planning_max_tokens: int = Field(
        default=2048,
        ge=1,
        le=16384,
        description="Structured Output으로 JSON 생성, 2048 토큰 제한"
    )

    # Aggregator Node
    aggregator_model: str = "gpt-4o-mini"
    aggregator_temperature: float = Field(
        default=0.5,
        ge=0.0,
        le=2.0,
        description="결과 종합 시 균형잡힌 temperature"
    )
    aggregator_max_tokens: int = Field(
        default=3072,
        ge=1,
        le=16384,
        description="여러 결과 종합하므로 3072 토큰"
    )

    # ==================== Response Nodes ====================

    # Chat Generator Node
    chat_model: str = "gpt-4o-mini"
    chat_temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="자연스러운 대화 생성을 위해 높은 temperature"
    )
    chat_max_tokens: int = Field(
        default=4096,
        ge=1,
        le=16384,
        description="긴 답변 생성 가능하도록 4096 토큰"
    )

    # Graph Generator Node
    graph_model: str = "gpt-4o-mini"
    graph_temperature: float = Field(
        default=0.2,
        ge=0.0,
        le=2.0,
        description="JSON 정확성 우선, 매우 낮은 temperature"
    )
    graph_max_tokens: int = Field(
        default=2048,
        ge=1,
        le=16384,
        description="그래프 데이터는 구조화되어 2048 토큰이면 충분"
    )

    # Report Generator Node
    report_model: str = "gpt-4o-mini"
    report_temperature: float = Field(
        default=0.5,
        ge=0.0,
        le=2.0,
        description="보고서 생성 시 균형잡힌 temperature"
    )
    report_max_tokens: int = Field(
        default=8192,
        ge=1,
        le=16384,
        description="긴 Markdown 보고서 생성을 위해 8192 토큰"
    )

    # ==================== Advanced Settings ====================

    # Top-p (nucleus sampling)
    top_p: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Top-p sampling (기본값 1.0 = 비활성화)"
    )

    # Frequency penalty
    frequency_penalty: float = Field(
        default=0.0,
        ge=-2.0,
        le=2.0,
        description="반복 억제 (0.0 = 비활성화)"
    )

    # Presence penalty
    presence_penalty: float = Field(
        default=0.0,
        ge=-2.0,
        le=2.0,
        description="새로운 주제 장려 (0.0 = 비활성화)"
    )


class AppContext(BaseModel):
    """Application 런타임 Context

    불변 정보만 포함:
    - user_id: 사용자 ID
    - session_id: 세션 ID
    - llm_settings: 노드별 LLM 설정
    - environment: 실행 환경 (production, development, testing)
    - db_conn: DB 연결 (Phase 5에서 추가 예정)
    """

    # 사용자 정보
    user_id: str
    session_id: str

    # LLM 설정 (노드별 세분화)
    llm_settings: LLMSettings = Field(default_factory=LLMSettings)

    # 실행 환경
    environment: Literal["production", "development", "testing"] = "production"

    # DB 연결 (Phase 5에서 활성화)
    db_conn: Optional[str] = None

    # 디버그 모드
    debug: bool = False

    class Config:
        """Pydantic 설정"""
        arbitrary_types_allowed = True
```

---

### Step 2: 환경별 설정 팩토리 생성

**파일**: `backend/app/config/llm_settings.py` (신규)

```python
"""LLM Settings Factory - 환경별 설정 생성

환경별로 최적화된 LLM 설정을 제공합니다.
"""
from backend.app.octostrator.contexts.app_context import LLMSettings


def get_llm_settings(environment: str = "production") -> LLMSettings:
    """환경별 LLM 설정 반환

    Args:
        environment: 실행 환경 (production, development, testing)

    Returns:
        LLMSettings: 환경에 맞는 LLM 설정
    """

    if environment == "production":
        # 프로덕션: 비용 절감 + 안정성 우선
        return LLMSettings(
            # 낮은 temperature로 일관성 확보
            intent_temperature=0.6,
            planning_temperature=0.2,
            aggregator_temperature=0.4,
            chat_temperature=0.6,
            graph_temperature=0.1,
            report_temperature=0.4,

            # 토큰 제한 엄격
            intent_max_tokens=1024,
            planning_max_tokens=2048,
            aggregator_max_tokens=2048,
            chat_max_tokens=3000,  # 비용 절감
            graph_max_tokens=2048,
            report_max_tokens=6000,  # 보고서는 좀 더 길게
        )

    elif environment == "development":
        # 개발: 다양한 출력 테스트
        return LLMSettings(
            # 더 높은 temperature로 다양성 확보
            intent_temperature=0.7,
            planning_temperature=0.5,
            aggregator_temperature=0.6,
            chat_temperature=0.8,
            graph_temperature=0.3,
            report_temperature=0.6,

            # 토큰 제한 완화
            intent_max_tokens=2048,
            planning_max_tokens=4096,
            aggregator_max_tokens=4096,
            chat_max_tokens=6000,
            graph_max_tokens=4096,
            report_max_tokens=10000,
        )

    elif environment == "testing":
        # 테스트: 결정론적 출력 + 빠른 실행
        return LLMSettings(
            # 0에 가까운 temperature로 동일한 출력 보장
            intent_temperature=0.0,
            planning_temperature=0.0,
            aggregator_temperature=0.0,
            chat_temperature=0.0,
            graph_temperature=0.0,
            report_temperature=0.0,

            # 최소 토큰으로 빠른 실행
            intent_max_tokens=512,
            planning_max_tokens=1024,
            aggregator_max_tokens=1024,
            chat_max_tokens=1024,
            graph_max_tokens=1024,
            report_max_tokens=2048,
        )

    else:
        # 기본값
        return LLMSettings()
```

---

### Step 3: 노드 함수 수정

**파일**: `backend/app/octostrator/nodes/cognitive_nodes.py`

```python
"""Cognitive Nodes - Context API 사용"""
from typing import Dict
from langchain_core.runnables import Runtime  # ⭐ Runtime import
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from backend.app.octostrator.states.supervisor_state import SupervisorState
from backend.app.octostrator.prompts.cognitive_prompts import (
    INTENT_UNDERSTANDING_PROMPT,
    PLANNING_SYSTEM_PROMPT
)


async def intent_understanding_node(
    state: SupervisorState,
    runtime: Runtime  # ⭐ Runtime 객체
) -> Dict:
    """Intent Understanding 노드 - Context API 사용

    Args:
        state: 현재 SupervisorState
        runtime: Runtime 객체 (context 포함)

    Returns:
        Dict: user_intent 업데이트
    """
    # Runtime Context에서 LLM 설정 가져오기
    llm_settings = runtime.context.llm_settings

    # Intent 노드용 LLM 생성
    llm = ChatOpenAI(
        model=llm_settings.intent_model,
        temperature=llm_settings.intent_temperature,
        max_tokens=llm_settings.intent_max_tokens,
        api_key=config.openai_api_key
    )

    # Intent 분석
    user_message = state["messages"][-1].content

    intent_prompt = SystemMessage(content=INTENT_UNDERSTANDING_PROMPT)
    response = await llm.ainvoke([
        intent_prompt,
        HumanMessage(content=user_message)
    ])

    user_intent = response.content.strip()

    return {
        "user_intent": user_intent,
        "is_understanding_intent": False,
        "is_planning": True
    }


async def planning_node(
    state: SupervisorState,
    runtime: Runtime  # ⭐ Runtime 객체
) -> Dict:
    """Planning 노드 - Context API 사용

    Args:
        state: 현재 SupervisorState
        runtime: Runtime 객체 (context 포함)

    Returns:
        Dict: plan, current_step 업데이트
    """
    # Runtime Context에서 LLM 설정 가져오기
    llm_settings = runtime.context.llm_settings

    # Planning 노드용 LLM 생성 (낮은 temperature)
    llm = ChatOpenAI(
        model=llm_settings.planning_model,
        temperature=llm_settings.planning_temperature,
        max_tokens=llm_settings.planning_max_tokens,
        api_key=config.openai_api_key
    )

    # Structured Output 설정
    structured_llm = llm.with_structured_output(Plan)

    # Planning 실행
    plan_result = await structured_llm.ainvoke([
        SystemMessage(content=PLANNING_SYSTEM_PROMPT),
        HumanMessage(content=f"User Intent:\n{state['user_intent']}")
    ])

    plan_as_dicts = [step.model_dump() for step in plan_result.steps]

    return {
        "plan": plan_as_dicts,
        "current_step": 0,
        "is_planning": False,
        "is_executing": True
    }


async def aggregator_node(
    state: SupervisorState,
    runtime: Runtime  # ⭐ Runtime 객체
) -> Dict:
    """Aggregator 노드 - Context API 사용"""

    llm_settings = runtime.context.llm_settings

    # Aggregator 노드용 LLM 생성 (중간 temperature)
    llm = ChatOpenAI(
        model=llm_settings.aggregator_model,
        temperature=llm_settings.aggregator_temperature,
        max_tokens=llm_settings.aggregator_max_tokens,
        api_key=config.openai_api_key
    )

    # ... 결과 집계 로직 ...

    return {
        "aggregated_data": aggregated_data,
        "is_executing": False,
        "is_generating_output": True
    }
```

---

### Step 4: Graph 빌드 시 Context Schema 등록

**파일**: `backend/app/octostrator/graphs/main_graph.py`

```python
"""Main Graph - Context API 사용"""
from typing import Optional
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from backend.app.octostrator.states.supervisor_state import SupervisorState
from backend.app.octostrator.contexts.app_context import AppContext  # ⭐ Context Schema

# Nodes
from backend.app.octostrator.nodes.cognitive_nodes import (
    intent_understanding_node,
    planning_node,
    executor_node,
    aggregator_node,
)

# ... (나머지 imports)


def build_supervisor_graph(
    checkpointer: Optional[AsyncPostgresSaver] = None
):
    """Supervisor Graph 생성 - Context API 사용

    Args:
        checkpointer: AsyncPostgresSaver (선택적)

    Returns:
        CompiledGraph: 컴파일된 LangGraph 그래프
    """

    # StateGraph 생성 with Context Schema
    workflow = StateGraph(
        SupervisorState,
        context_schema=AppContext  # ⭐ Context Schema 등록
    )

    # === 노드 추가 ===
    # Runtime 객체가 자동으로 전달됨

    workflow.add_node("intent", intent_understanding_node)
    workflow.add_node("planning", planning_node)
    workflow.add_node("executor", executor_node, ends=[...])
    workflow.add_node("aggregator", aggregator_node)

    # ... Agents, Response Nodes ...

    # === 엣지 정의 ===
    workflow.add_edge(START, "intent")
    workflow.add_edge("intent", "planning")
    # ... (나머지 엣지)

    # 컴파일
    if checkpointer is not None:
        return workflow.compile(checkpointer=checkpointer)
    else:
        return workflow.compile()
```

---

### Step 5: API에서 Context 전달

**파일**: `backend/app/api/sessions.py`

```python
"""Sessions API - Context 전달"""
from backend.app.octostrator.supervisor import build_supervisor_graph
from backend.app.octostrator.contexts.app_context import AppContext
from backend.app.config.llm_settings import get_llm_settings
from backend.app.config.system import config


@router.post("/sessions/{session_id}/invoke")
async def invoke_session(
    session_id: str,
    request: InvokeRequest,
    db: AsyncSession = Depends(get_db)
):
    """세션 실행 - Context 전달"""

    # 환경 결정 (환경변수 또는 설정에서)
    environment = config.environment  # "production", "development", "testing"

    # Context 생성
    context = AppContext(
        user_id=request.user_id or "anonymous",
        session_id=session_id,
        llm_settings=get_llm_settings(environment=environment),  # ⭐ 환경별 설정
        environment=environment,
        debug=config.debug
    )

    # Checkpointer 생성
    checkpointer = await get_checkpointer()

    # Graph 빌드
    graph = build_supervisor_graph(checkpointer=checkpointer)

    # Graph 실행 (Context 전달)
    result = await graph.ainvoke(
        {"messages": [HumanMessage(content=request.message)]},
        config={"configurable": {"thread_id": session_id}},
        context=context  # ⭐ Context 전달
    )

    return {"result": result["final_result"]}
```

---

## 🧪 테스트 방법

### 단위 테스트: LLMSettings 검증

```python
# tests/test_llm_settings.py
import pytest
from backend.app.config.llm_settings import get_llm_settings


def test_production_settings():
    """프로덕션 설정 검증"""
    settings = get_llm_settings("production")

    # 낮은 temperature 확인
    assert settings.planning_temperature == 0.2
    assert settings.graph_temperature == 0.1

    # 토큰 제한 확인
    assert settings.chat_max_tokens == 3000
    assert settings.planning_max_tokens == 2048


def test_testing_settings():
    """테스트 설정 검증 (결정론적)"""
    settings = get_llm_settings("testing")

    # 모든 temperature가 0
    assert settings.intent_temperature == 0.0
    assert settings.planning_temperature == 0.0
    assert settings.chat_temperature == 0.0

    # 최소 토큰
    assert settings.intent_max_tokens == 512


def test_settings_validation():
    """설정 범위 검증"""
    from backend.app.octostrator.contexts.app_context import LLMSettings
    import pytest

    # temperature 범위 초과 시 에러
    with pytest.raises(ValueError):
        LLMSettings(planning_temperature=3.0)  # max=2.0

    # max_tokens 범위 초과 시 에러
    with pytest.raises(ValueError):
        LLMSettings(planning_max_tokens=20000)  # max=16384
```

### 통합 테스트: Context 전달 확인

```python
# tests/test_context_api.py
import pytest
from backend.app.octostrator.supervisor import build_supervisor_graph
from backend.app.octostrator.contexts.app_context import AppContext, LLMSettings


@pytest.mark.asyncio
async def test_context_propagation():
    """Context가 노드까지 제대로 전달되는지 테스트"""

    # 커스텀 설정
    custom_settings = LLMSettings(
        planning_temperature=0.1,
        planning_max_tokens=512
    )

    context = AppContext(
        user_id="test_user",
        session_id="test_session",
        llm_settings=custom_settings
    )

    # Graph 실행
    graph = build_supervisor_graph()

    result = await graph.ainvoke(
        {"messages": [{"role": "user", "content": "테스트"}]},
        context=context
    )

    # 결과 확인 (실제로는 노드 내부에서 설정 사용 확인)
    assert result is not None
```

---

## 📊 비용 최적화 효과

### Before (Phase 1):
```
전체 노드: max_tokens=4096 (고정)
- Intent: 4096 토큰 허용 (과다)
- Planning: 2048 토큰 필요 (config로 임시 제한)
- Chat: 4096 토큰 허용 (적절)
- Report: 4096 토큰 허용 (부족할 수 있음)

→ 불필요한 토큰 사용 발생
```

### After (Phase 2):
```
노드별 최적화:
- Intent: 1024 토큰 (간단한 분류)
- Planning: 2048 토큰 (Structured Output)
- Chat: 3000 토큰 (프로덕션 비용 절감)
- Report: 6000 토큰 (충분한 길이)

→ 평균 30-40% 토큰 절감 예상
```

---

## 🚀 마이그레이션 체크리스트

- [ ] Step 1: `contexts/app_context.py`에 LLMSettings 정의
- [ ] Step 2: `config/llm_settings.py` 환경별 팩토리 생성
- [ ] Step 3: `nodes/cognitive_nodes.py` Runtime 객체 사용 변경
- [ ] Step 4: `nodes/response_nodes.py` Runtime 객체 사용 변경
- [ ] Step 5: `graphs/main_graph.py`에 context_schema 등록
- [ ] Step 6: `api/sessions.py`에서 Context 전달
- [ ] Step 7: 단위 테스트 작성 (LLMSettings)
- [ ] Step 8: 통합 테스트 작성 (Context 전달)
- [ ] Step 9: 전체 에이전트 테스트 재실행 (100% 성공 확인)
- [ ] Step 10: 문서 업데이트

---

## ⚠️ 주의사항

1. **LangGraph 버전 확인**
   - Context API는 v1.0+에서만 사용 가능
   - `pip show langgraph`로 버전 확인

2. **점진적 마이그레이션**
   - 모든 노드를 한번에 변경하지 말 것
   - Cognitive Nodes → Response Nodes 순으로 진행

3. **하위 호환성 유지**
   - 기존 `config["configurable"]` 패턴도 계속 작동
   - 테스트 통과 후 단계적 제거

4. **환경변수 설정**
   - `config.environment`를 설정 파일에 추가
   - 배포 환경별로 다르게 설정

---

**다음 문서**: [Phase 2 프롬프트 최적화 계획](../system/OPTIMIZATION_PLAN_251105.md)
