# Context API 계층형 슈퍼바이저 마이그레이션 계획서
## LangGraph Context API 적용을 위한 시스템 재구조화

**작성일**: 2025-11-06
**대상 시스템**: AI PT Manager - Octostrator v2.0
**작업 범위**: Phase 2 Context API 적용을 계층형 슈퍼바이저 아키텍처로 확장

---

## 📋 Executive Summary

### 현재 상황
시스템이 **단일 슈퍼바이저 구조**에서 **계층형 슈퍼바이저 아키텍처**로 재편되었습니다.

**기존 구조** (Phase 2에서 작업):
```
octostrator/supervisor/
└── 단일 슈퍼바이저 (main_graph.py, cognitive_nodes.py)
```

**새로운 구조** (현재):
```
octostrator/supervisors/
├── octostrator/     # Layer 0: 최상위 오케스트레이터
├── cognitive/       # Layer 1: 인지 계층
├── execute/         # Layer 2: 실행 계층
├── response/        # Layer 3: 응답 계층
└── todo/           # TODO 관리
```

### 핵심 이슈
✅ **Phase 2 완료된 작업**:
- `app_context.py`: LLMSettings 스키마 정의 완료
- `llm_settings.py`: 환경별 설정 팩토리 완료

⚠️ **적용 필요**:
- 4개 계층 × 3~5개 노드 = 총 15+ 노드에 Context API 적용 필요
- 각 계층 그래프에 context_schema 등록 필요
- 계층 간 Context 전달 메커니즘 구축 필요

### 목표
1. **계층형 아키텍처에 Context API 전면 적용**
2. **노드별 LLM 최적화 설정 활성화**
3. **환경별 비용 최적화 달성** (Production: 36.9% 절감)
4. **확장 가능한 구조 확립**

---

## 🏗️ 시스템 구조 분석

### 1. 계층형 슈퍼바이저 아키텍처

```
┌─────────────────────────────────────────────────────────┐
│                  Octostrator Layer                      │
│  (최상위 오케스트레이터 - 전체 워크플로우 조정)           │
│                                                          │
│  Nodes:                                                  │
│  - cognitive_layer_node                                  │
│  - todo_layer_node                                       │
│  - execute_layer_node                                    │
│  - response_layer_node                                   │
└────────┬────────────┬────────────┬────────────┬─────────┘
         │            │            │            │
         ▼            ▼            ▼            ▼
    ┌────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐
    │Cognitive│  │  Todo   │  │ Execute │  │Response │
    │ Layer  │  │ Layer   │  │ Layer   │  │ Layer   │
    └────────┘  └─────────┘  └─────────┘  └─────────┘
         │            │            │            │
    ┌────▼─────┐ ┌───▼─────┐ ┌───▼─────┐ ┌───▼─────┐
    │ Intent   │ │Plan→    │ │Executor │ │HITL     │
    │ Planning │ │ Todo    │ │Error    │ │Router   │
    │Validator │ │ HITL    │ │Handler  │ │Chat Gen │
    │          │ │         │ │Aggreg.  │ │Graph Gen│
    │          │ │         │ │         │ │Report Gen│
    └──────────┘ └─────────┘ └─────────┘ └─────────┘
```

**워크플로우**:
```
START
  → Cognitive Layer (의도 파악 → 계획 수립 → 검증)
    → Todo Layer (계획을 TODO로 변환 → HITL 승인)
      → Execute Layer (에이전트 실행 → 에러 처리 → 결과 집계)
        → Response Layer (HITL 확인 → 라우팅 → 응답 생성)
          → END
```

### 2. 폴더 구조 상세

```
backend/app/octostrator/
│
├── supervisors/                    # 계층형 슈퍼바이저 (신규 구조)
│   │
│   ├── octostrator/               # Layer 0: 최상위 오케스트레이터
│   │   ├── octostrator_graph.py       # 전체 워크플로우 그래프
│   │   ├── octostrator_nodes.py       # 계층 실행 노드 (4개)
│   │   └── octostrator_helpers.py     # 헬퍼 함수
│   │
│   ├── cognitive/                 # Layer 1: 인지 계층
│   │   ├── cognitive_graph.py         # 인지 처리 그래프
│   │   ├── cognitive_nodes.py         # 노드 (3개)
│   │   │   ├─ intent_understanding_node    ← LLM 필요 ✅
│   │   │   ├─ planning_node                ← LLM 필요 ✅
│   │   │   └─ validator_node               ← LLM 필요 ✅
│   │   ├── cognitive_helpers.py       # CognitiveSupervisor 클래스
│   │   └── cognitive_prompts.py       # 프롬프트 템플릿
│   │
│   ├── execute/                   # Layer 2: 실행 계층
│   │   ├── execute_graph.py           # 실행 처리 그래프
│   │   ├── execute_nodes.py           # 노드 (3개)
│   │   │   ├─ executor_node                ← LLM 불필요
│   │   │   ├─ error_handler_node           ← LLM 선택적
│   │   │   └─ aggregator_node              ← LLM 필요 ✅
│   │   ├── execute_helpers.py         # 실행 헬퍼
│   │   └── execute_prompts.py         # 프롬프트 템플릿
│   │
│   ├── response/                  # Layer 3: 응답 계층
│   │   ├── response_graph.py          # 응답 생성 그래프
│   │   ├── response_nodes.py          # 노드 (5개)
│   │   │   ├─ hitl_handler_node            ← LLM 불필요
│   │   │   ├─ output_router_node           ← LLM 불필요
│   │   │   ├─ chat_generator_node          ← LLM 필요 ✅
│   │   │   ├─ graph_generator_node         ← LLM 필요 ✅
│   │   │   └─ report_generator_node        ← LLM 필요 ✅
│   │   ├── response_helpers.py        # 응답 헬퍼
│   │   └── response_prompts.py        # 프롬프트 템플릿
│   │
│   └── todo/                      # TODO 관리
│       ├── todo_manager.py            # TodoAgent 클래스
│       └── __init__.py
│
├── contexts/                      # Context API (Phase 2 완료)
│   ├── app_context.py                 # AppContext + LLMSettings ✅
│   └── __init__.py
│
├── states/                        # 상태 정의
│   ├── base.py                        # BaseState
│   ├── supervisors.py                 # 슈퍼바이저 State들
│   ├── cognitive_state.py             # Cognitive Layer State
│   ├── execute_state.py               # Execute Layer State
│   └── response_state.py              # Response Layer State
│
├── agents/                        # 개별 에이전트 (기존)
│   ├── base/                          # 기본 프레임워크
│   ├── diet/                          # 식단 에이전트
│   ├── workout/                       # 운동 에이전트
│   ├── schedule/                      # 일정 에이전트
│   ├── member_care/                   # 회원 관리 에이전트
│   └── coaching/                      # 코칭 에이전트
│
├── tools/                         # 에이전트 도구
│   ├── diet_tools.py
│   ├── workout_tools.py
│   └── ...
│
├── checkpointer/                  # 체크포인터
│   └── postgres_checkpointer.py
│
└── session/                       # 세션 관리
    └── session_manager.py
```

### 3. LLM 사용 노드 분석

| 계층 | 노드명 | LLM 필요 | 현재 상태 | Phase 2 설정 | 우선순위 |
|------|--------|----------|-----------|-------------|---------|
| **Cognitive** | intent_understanding_node | ✅ 필수 | TODO 주석 | intent_* | **P0** |
| **Cognitive** | planning_node | ✅ 필수 | TODO 주석 | planning_* | **P0** |
| **Cognitive** | validator_node | ✅ 필수 | TODO 주석 | planning_* | **P0** |
| **Execute** | executor_node | ❌ 불필요 | - | - | - |
| **Execute** | error_handler_node | 🔶 선택 | - | aggregator_* | P2 |
| **Execute** | aggregator_node | ✅ 필수 | TODO 주석 | aggregator_* | **P0** |
| **Response** | hitl_handler_node | ❌ 불필요 | - | - | - |
| **Response** | output_router_node | ❌ 불필요 | - | - | - |
| **Response** | chat_generator_node | ✅ 필수 | TODO 주석 | chat_* | **P1** |
| **Response** | graph_generator_node | ✅ 필수 | TODO 주석 | graph_* | **P1** |
| **Response** | report_generator_node | ✅ 필수 | TODO 주석 | report_* | **P1** |

**우선순위**:
- **P0 (Critical)**: Cognitive 계층 3개 + Execute aggregator (시스템 동작에 필수)
- **P1 (High)**: Response 계층 3개 (사용자 경험에 중요)
- **P2 (Medium)**: error_handler (추가 개선)

**총 LLM 노드**: 7개 (P0: 4개, P1: 3개)

---

## 🔍 Phase 2 작업 분석

### Phase 2에서 완료된 작업

#### 1. AppContext 확장 ([app_context.py](../../backend/app/octostrator/contexts/app_context.py))

```python
from dataclasses import dataclass
from typing import Optional
from pydantic import BaseModel, Field

class LLMSettings(BaseModel):
    """노드별 LLM 설정 - Pydantic 검증"""

    # Intent Understanding Node
    intent_temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    intent_max_tokens: int = Field(default=1024, ge=1, le=16384)
    intent_model: str = Field(default="gpt-4o-mini")

    # Planning Node
    planning_temperature: float = Field(default=0.3, ge=0.0, le=2.0)
    planning_max_tokens: int = Field(default=2048, ge=1, le=16384)
    planning_model: str = Field(default="gpt-4o-mini")

    # Aggregator Node
    aggregator_temperature: float = Field(default=0.5, ge=0.0, le=2.0)
    aggregator_max_tokens: int = Field(default=3072, ge=1, le=16384)
    aggregator_model: str = Field(default="gpt-4o-mini")

    # Chat/Graph/Report Generator Nodes
    chat_temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    chat_max_tokens: int = Field(default=4096, ge=1, le=16384)
    chat_model: str = Field(default="gpt-4o-mini")

    graph_temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    graph_max_tokens: int = Field(default=2048, ge=1, le=16384)
    graph_model: str = Field(default="gpt-4o-mini")

    report_temperature: float = Field(default=0.5, ge=0.0, le=2.0)
    report_max_tokens: int = Field(default=8192, ge=1, le=16384)
    report_model: str = Field(default="gpt-4o-mini")

    # Agent Nodes (준비됨, 미사용)
    agent_temperature: float = Field(default=0.5, ge=0.0, le=2.0)
    agent_max_tokens: int = Field(default=4096, ge=1, le=16384)
    agent_model: str = Field(default="gpt-4o-mini")

@dataclass
class AppContext:
    """Application 런타임 Context"""
    user_id: str
    session_id: str
    llm_settings: LLMSettings  # ✅ 준비 완료
    db_conn: Optional[str] = None
    debug: bool = False
```

**상태**: ✅ **완료** - 새 구조에서도 그대로 사용 가능

#### 2. 환경별 설정 팩토리 ([llm_settings.py](../../backend/app/config/llm_settings.py))

```python
from enum import Enum
from backend.app.octostrator.contexts.app_context import LLMSettings

class Environment(str, Enum):
    PRODUCTION = "production"
    DEVELOPMENT = "development"
    TESTING = "testing"

# 3개 프리셋 정의
PRODUCTION_PRESET = {
    "intent_temperature": 0.5,      # 비용 최적화
    "intent_max_tokens": 800,
    "planning_temperature": 0.2,    # 정확성
    "planning_max_tokens": 2048,
    # ...
}

DEVELOPMENT_PRESET = {
    "intent_temperature": 0.7,      # 다양성
    "intent_max_tokens": 1024,
    # ...
}

TESTING_PRESET = {
    "intent_temperature": 0.0,      # 재현성
    "intent_max_tokens": 512,
    # ...
}

def get_llm_settings(
    environment: Environment = Environment.DEVELOPMENT,
    overrides: Optional[Dict[str, Any]] = None
) -> LLMSettings:
    """환경별 LLM 설정 생성"""
    # ...

def get_llm_settings_from_env() -> LLMSettings:
    """SYSTEM_ENV 환경 변수에서 자동 감지"""
    # ...
```

**상태**: ✅ **완료** - 새 구조에서도 그대로 사용 가능

### Phase 2에서 미완료된 작업

❌ **노드 적용**: 단일 슈퍼바이저 구조를 가정했으나 실제로는 계층형 구조
- `supervisor/nodes/cognitive_nodes.py` 수정함 → 실제로는 `supervisors/cognitive/cognitive_nodes.py` 수정 필요
- `supervisor/graphs/main_graph.py` 수정함 → 실제로는 4개 계층 그래프 모두 수정 필요

❌ **Context Schema 등록**: 미적용
- 각 계층 그래프 빌더에 `context_schema=AppContext` 등록 필요

❌ **계층 간 Context 전달**: 미설계
- Octostrator → Cognitive → Execute → Response 계층 간 Context 전달 메커니즘 필요

---

## 🎯 마이그레이션 계획

### Phase 2.1: Cognitive Layer Context API 적용 (P0 - 최우선)

**목표**: 핵심 인지 계층에 Context API 적용하여 시스템 동작 활성화

#### Task 1.1: cognitive_nodes.py 수정

**파일**: `backend/app/octostrator/supervisors/cognitive/cognitive_nodes.py`

**Before**:
```python
async def intent_understanding_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Intent Understanding Node - TODO: Implement with LLM"""
    try:
        user_query = state.get("user_query", "")
        # TODO: Implement with LLM or classifier
        return {
            "user_intent": "multi_step_task",
            "intent_confidence": 0.8
        }
    except Exception as e:
        return {"error": str(e)}
```

**After**:
```python
from langgraph.types import Runtime
from backend.app.octostrator.contexts.app_context import AppContext
from langchain_openai import ChatOpenAI
from backend.app.config.system import config as system_config

async def intent_understanding_node(
    state: Dict[str, Any],
    runtime: Runtime  # ✅ Context API
) -> Dict[str, Any]:
    """Intent Understanding Node - LLM으로 의도 분석"""
    try:
        # 1. Context에서 설정 추출
        context: AppContext = runtime.context
        settings = context.llm_settings

        # 2. 노드별 LLM 생성
        llm = ChatOpenAI(
            model=settings.intent_model,
            temperature=settings.intent_temperature,  # 0.7 (창의적)
            max_tokens=settings.intent_max_tokens,    # 1024
            api_key=system_config.openai_api_key
        )

        # 3. 프롬프트 생성 및 실행
        from .cognitive_prompts import create_intent_prompt
        user_query = state.get("user_query", "")
        prompt = create_intent_prompt(user_query)

        response = await llm.ainvoke([SystemMessage(content=prompt)])

        # 4. 결과 파싱
        intent_data = parse_intent_response(response.content)

        return {
            "user_intent": intent_data.get("intent"),
            "intent_confidence": intent_data.get("confidence", 0.8)
        }

    except Exception as e:
        logger.error(f"[Intent] Error: {e}")
        return {"error": str(e)}
```

**동일 패턴 적용**:
- `planning_node`: temp=0.3, tokens=2048 (정확성 우선)
- `validator_node`: temp=0.3, tokens=2048 (검증 엄격)

#### Task 1.2: cognitive_graph.py 수정

**파일**: `backend/app/octostrator/supervisors/cognitive/cognitive_graph.py`

**Before**:
```python
def build_cognitive_graph(state_class=None):
    """Build the cognitive layer workflow graph."""
    if state_class is None:
        state_class = dict

    graph = StateGraph(state_class)  # ❌ context_schema 없음

    graph.add_node("intent", intent_understanding_node)
    graph.add_node("planning", planning_node)
    graph.add_node("validator", validator_node)
    # ...
```

**After**:
```python
from backend.app.octostrator.contexts.app_context import AppContext
from backend.app.config.llm_settings import get_llm_settings_from_env

def build_cognitive_graph(
    state_class=None,
    context: Optional[AppContext] = None,
    user_id: str = "default_user",
    session_id: str = "default_session"
):
    """Build the cognitive layer workflow graph with Context API."""

    # 1. State 기본값
    if state_class is None:
        state_class = dict

    # 2. AppContext 자동 생성
    if context is None:
        llm_settings = get_llm_settings_from_env()
        context = AppContext(
            user_id=user_id,
            session_id=session_id,
            llm_settings=llm_settings,
            debug=False
        )
        logger.info(f"[CognitiveGraph] AppContext 자동 생성")

    # 3. StateGraph에 context_schema 등록
    graph = StateGraph(
        state_class,
        context_schema=AppContext  # ✅ Context API 활성화
    )

    # 4. 노드 등록 (Runtime 자동 주입됨)
    graph.add_node("intent", intent_understanding_node)
    graph.add_node("planning", planning_node)
    graph.add_node("validator", validator_node)

    # 5. 엣지 설정
    graph.add_edge(START, "intent")
    graph.add_edge("intent", "planning")
    graph.add_edge("planning", "validator")
    graph.add_edge("validator", END)

    return graph.compile()
```

#### Task 1.3: cognitive_prompts.py 작성

**파일**: `backend/app/octostrator/supervisors/cognitive/cognitive_prompts.py`

**현재 상태**: 파일 존재하지만 프롬프트 템플릿 미작성

**작성 필요**:
```python
def create_intent_prompt(user_query: str) -> str:
    """Intent Understanding 프롬프트 생성"""
    return f"""
당신은 PT 관리 시스템의 의도 분석 전문가입니다.

사용자 요청: {user_query}

다음 카테고리 중 하나로 분류하세요:
- diet_query: 식단 관련 질문
- workout_query: 운동 관련 질문
- schedule_query: 일정 관련 질문
- member_report: 회원 보고서
- coaching_search: 코칭 정보 검색
- multi_step_task: 복합 작업
- progress_comparison: 진행도 비교

JSON 형식으로 응답:
{{"intent": "카테고리", "confidence": 0.0-1.0, "reasoning": "이유"}}
    """

def create_planning_prompt(user_query: str, intent: str) -> str:
    """Planning 프롬프트 생성"""
    # ...

def create_validation_prompt(plan: Dict) -> str:
    """Validation 프롬프트 생성"""
    # ...
```

**예상 작업량**: 3-4시간

---

### Phase 2.2: Execute Layer Context API 적용 (P0)

**목표**: Aggregator 노드에 Context API 적용

#### Task 2.1: execute_nodes.py - aggregator_node 수정

**파일**: `backend/app/octostrator/supervisors/execute/execute_nodes.py`

**Before**:
```python
async def aggregator_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Aggregator Node - TODO: Implement with LLM"""
    execution_results = state.get("execution_results", [])

    # Simple aggregation
    aggregated = {
        "total_steps": len(execution_results),
        "completed_steps": sum(1 for r in execution_results if r.get("status") == "completed"),
        "summary": "All tasks completed successfully"
    }
    return {"aggregated_data": aggregated}
```

**After**:
```python
from langgraph.types import Runtime
from backend.app.octostrator.contexts.app_context import AppContext

async def aggregator_node(
    state: Dict[str, Any],
    runtime: Runtime  # ✅ Context API
) -> Dict[str, Any]:
    """Aggregator Node - LLM으로 결과 집계 및 인사이트 생성"""
    try:
        # 1. Context에서 설정 추출
        context: AppContext = runtime.context
        settings = context.llm_settings

        # 2. 노드별 LLM 생성
        llm = ChatOpenAI(
            model=settings.aggregator_model,
            temperature=settings.aggregator_temperature,  # 0.5 (균형)
            max_tokens=settings.aggregator_max_tokens,    # 3072
            api_key=system_config.openai_api_key
        )

        # 3. 실행 결과 수집
        execution_results = state.get("execution_results", [])

        # 4. LLM으로 인사이트 생성
        from .execute_prompts import create_aggregation_prompt
        prompt = create_aggregation_prompt(execution_results)

        response = await llm.ainvoke([SystemMessage(content=prompt)])

        # 5. 구조화된 결과 반환
        aggregated = {
            "total_steps": len(execution_results),
            "completed_steps": sum(1 for r in execution_results if r.get("status") == "completed"),
            "failed_steps": sum(1 for r in execution_results if r.get("status") == "failed"),
            "results": execution_results,
            "summary": response.content,
            "insights": extract_insights(response.content)
        }

        return {"aggregated_data": aggregated}

    except Exception as e:
        logger.error(f"[Aggregator] Error: {e}")
        return {"error": str(e)}
```

#### Task 2.2: execute_graph.py 수정

**파일**: `backend/app/octostrator/supervisors/execute/execute_graph.py`

**수정 내용**: cognitive_graph.py와 동일한 패턴으로 context_schema 등록

```python
def build_execute_graph(
    state_class=None,
    context: Optional[AppContext] = None,
    user_id: str = "default_user",
    session_id: str = "default_session"
):
    """Build the execute layer workflow graph with Context API."""

    # Context 자동 생성
    if context is None:
        llm_settings = get_llm_settings_from_env()
        context = AppContext(
            user_id=user_id,
            session_id=session_id,
            llm_settings=llm_settings
        )

    # context_schema 등록
    graph = StateGraph(state_class, context_schema=AppContext)

    # 노드 등록
    graph.add_node("executor", executor_node)
    graph.add_node("error_handler", error_handler_node)
    graph.add_node("aggregator", aggregator_node)

    # ...
    return graph.compile()
```

**예상 작업량**: 2-3시간

---

### Phase 2.3: Response Layer Context API 적용 (P1)

**목표**: 응답 생성 노드들에 Context API 적용

#### Task 3.1: response_nodes.py 수정

**파일**: `backend/app/octostrator/supervisors/response/response_nodes.py`

**수정 대상 노드**:
1. `chat_generator_node`: temp=0.7, tokens=4096 (자연스러운 대화)
2. `graph_generator_node`: temp=0.2, tokens=2048 (JSON 정확성)
3. `report_generator_node`: temp=0.5, tokens=8192 (긴 보고서)

**Before (chat_generator_node)**:
```python
async def chat_generator_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Chat Generator - TODO: Implement with LLM"""
    aggregated_data = state.get("aggregated_data", {})

    # Template-based response
    response = f"""
작업이 완료되었습니다!
- 총 작업: {aggregated_data.get('total_steps', 0)}개
- 완료: {aggregated_data.get('completed_steps', 0)}개
    """

    return {"final_result": response, "response_type": "chat"}
```

**After**:
```python
async def chat_generator_node(
    state: Dict[str, Any],
    runtime: Runtime  # ✅ Context API
) -> Dict[str, Any]:
    """Chat Generator - LLM으로 자연어 응답 생성"""
    try:
        # Context에서 설정 추출
        context: AppContext = runtime.context
        settings = context.llm_settings

        # LLM 생성 (chat 특화 설정)
        llm = ChatOpenAI(
            model=settings.chat_model,
            temperature=settings.chat_temperature,  # 0.7 (자연스러움)
            max_tokens=settings.chat_max_tokens,    # 4096
            api_key=system_config.openai_api_key
        )

        # 프롬프트 생성
        aggregated_data = state.get("aggregated_data", {})
        from .response_prompts import create_chat_prompt
        prompt = create_chat_prompt(aggregated_data)

        # LLM 실행
        response = await llm.ainvoke([SystemMessage(content=prompt)])

        return {
            "final_result": response.content,
            "response_type": "chat"
        }

    except Exception as e:
        logger.error(f"[ChatGen] Error: {e}")
        return {"error": str(e)}
```

**동일 패턴 적용**:
- `graph_generator_node`: Structured Output으로 JSON 생성
- `report_generator_node`: 긴 마크다운 보고서 생성

#### Task 3.2: response_graph.py 수정

**파일**: `backend/app/octostrator/supervisors/response/response_graph.py`

**수정 내용**: context_schema 등록 (동일 패턴)

**예상 작업량**: 3-4시간

---

### Phase 2.4: Octostrator Layer Context 통합 (P0)

**목표**: 최상위 계층에서 하위 계층으로 Context 전달

#### Task 4.1: octostrator_nodes.py 수정

**파일**: `backend/app/octostrator/supervisors/octostrator/octostrator_nodes.py`

**Before**:
```python
async def cognitive_layer_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Execute Cognitive Layer"""
    from ..cognitive.cognitive_helpers import CognitiveSupervisor

    supervisor = CognitiveSupervisor(
        llm=state.get("llm"),  # ❌ 글로벌 LLM 전달
        checkpointer=state.get("checkpointer")
    )

    plan = await supervisor.plan(
        user_message=state.get("user_query", ""),
        session_id=state.get("session_id", "default"),
        context=state.get("context", {})
    )

    state["plan"] = plan
    return state
```

**After**:
```python
from langgraph.types import Runtime
from backend.app.octostrator.contexts.app_context import AppContext

async def cognitive_layer_node(
    state: Dict[str, Any],
    runtime: Runtime  # ✅ Context API
) -> Dict[str, Any]:
    """Execute Cognitive Layer with Context"""
    try:
        # 1. Runtime에서 AppContext 추출
        context: AppContext = runtime.context

        # 2. Cognitive Supervisor 생성 (Context 전달)
        from ..cognitive.cognitive_helpers import CognitiveSupervisor

        supervisor = CognitiveSupervisor(
            context=context,  # ✅ AppContext 전달
            checkpointer=state.get("checkpointer")
        )

        # 3. Planning 실행
        plan = await supervisor.plan(
            user_message=state.get("user_query", ""),
            session_id=context.session_id,  # Context에서 가져옴
            user_id=context.user_id
        )

        # 4. State 업데이트
        state["plan"] = plan
        state["plan_valid"] = plan is not None

        return state

    except Exception as e:
        logger.error(f"[Octostrator] Cognitive Layer failed: {e}")
        state["error"] = str(e)
        return state
```

**동일 패턴 적용**:
- `todo_layer_node`: TodoAgent에 Context 전달
- `execute_layer_node`: ExecuteSupervisor에 Context 전달
- `response_layer_node`: ResponseSupervisor에 Context 전달

#### Task 4.2: octostrator_graph.py 수정

**파일**: `backend/app/octostrator/supervisors/octostrator/octostrator_graph.py`

**Before**:
```python
def build_octostrator_graph(state_class=None):
    """Build the main orchestrator graph."""
    if state_class is None:
        state_class = dict

    graph = StateGraph(state_class)  # ❌ context_schema 없음

    graph.add_node("cognitive", cognitive_layer_node)
    graph.add_node("todo", todo_layer_node)
    graph.add_node("execute", execute_layer_node)
    graph.add_node("response", response_layer_node)
    # ...
```

**After**:
```python
from backend.app.octostrator.contexts.app_context import AppContext
from backend.app.config.llm_settings import get_llm_settings_from_env
from langgraph.store.postgres import AsyncPostgresSaver

def build_octostrator_graph(
    state_class=None,
    context: Optional[AppContext] = None,
    checkpointer: Optional[AsyncPostgresSaver] = None,
    user_id: str = "default_user",
    session_id: str = "default_session"
):
    """
    Build the main orchestrator graph with Context API.

    Args:
        state_class: State schema (defaults to dict)
        context: AppContext instance (auto-created if None)
        checkpointer: Postgres checkpointer for persistence
        user_id: User ID for context
        session_id: Session ID for context

    Returns:
        Compiled LangGraph workflow
    """

    # 1. State 기본값
    if state_class is None:
        state_class = dict

    # 2. AppContext 자동 생성
    if context is None:
        llm_settings = get_llm_settings_from_env()
        context = AppContext(
            user_id=user_id,
            session_id=session_id,
            llm_settings=llm_settings,
            debug=False
        )
        logger.info(f"[Octostrator] AppContext 자동 생성 (env={os.getenv('SYSTEM_ENV', 'development')})")

    # 3. StateGraph에 context_schema 등록
    graph = StateGraph(
        state_class,
        context_schema=AppContext  # ✅ 모든 하위 노드에 Runtime 주입
    )

    # 4. 계층 노드 등록
    graph.add_node("cognitive", cognitive_layer_node)
    graph.add_node("todo", todo_layer_node)
    graph.add_node("execute", execute_layer_node)
    graph.add_node("response", response_layer_node)

    # 5. 엣지 설정 (순차 실행)
    graph.add_edge(START, "cognitive")
    graph.add_edge("cognitive", "todo")
    graph.add_edge("todo", "execute")
    graph.add_edge("execute", "response")
    graph.add_edge("response", END)

    # 6. 컴파일 (Checkpointer 포함)
    return graph.compile(checkpointer=checkpointer)
```

**예상 작업량**: 4-5시간

---

### Phase 2.5: Supervisor Helper 클래스 수정 (P1)

**목표**: 각 계층의 Supervisor 클래스가 Context를 받도록 수정

#### Task 5.1: cognitive_helpers.py 수정

**파일**: `backend/app/octostrator/supervisors/cognitive/cognitive_helpers.py`

**수정 필요**:
```python
class CognitiveSupervisor:
    """Cognitive Layer Supervisor"""

    def __init__(
        self,
        context: AppContext,  # ✅ AppContext 받기
        checkpointer: Optional[AsyncPostgresSaver] = None
    ):
        self.context = context
        self.checkpointer = checkpointer
        self.graph = None

    async def plan(
        self,
        user_message: str,
        session_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """Generate plan using cognitive graph"""

        # Graph 빌드 (Context 전달)
        if self.graph is None:
            from .cognitive_graph import build_cognitive_graph
            self.graph = build_cognitive_graph(
                context=self.context,
                checkpointer=self.checkpointer
            )

        # 실행
        result = await self.graph.ainvoke({
            "user_query": user_message,
            "messages": []
        })

        return result.get("plan")
```

**동일 패턴 적용**:
- `execute_helpers.py`: ExecuteSupervisor 클래스
- `response_helpers.py`: ResponseSupervisor 클래스

**예상 작업량**: 2-3시간

---

## 📋 전체 작업 로드맵

### Sprint 1: Cognitive Layer 활성화 (Week 1)

**목표**: 시스템 핵심 동작 활성화

| Task | 파일 | 예상 시간 | 우선순위 | 의존성 |
|------|------|----------|---------|--------|
| 1.1 | cognitive_nodes.py 수정 | 3h | **P0** | - |
| 1.2 | cognitive_graph.py 수정 | 2h | **P0** | Task 1.1 |
| 1.3 | cognitive_prompts.py 작성 | 4h | **P0** | - |
| 1.4 | cognitive_helpers.py 수정 | 3h | P1 | Task 1.2 |
| 테스트 | Cognitive Layer 단위 테스트 | 3h | **P0** | All |

**예상 총 시간**: 15시간 (2일)

**완료 기준**:
- ✅ Intent/Planning/Validator 노드가 LLM으로 동작
- ✅ 환경별 설정 (Production/Development/Testing) 동작 확인
- ✅ 단위 테스트 통과

---

### Sprint 2: Execute & Response Layer (Week 2)

**목표**: 결과 집계 및 응답 생성 활성화

| Task | 파일 | 예상 시간 | 우선순위 | 의존성 |
|------|------|----------|---------|--------|
| 2.1 | execute_nodes.py 수정 | 2h | **P0** | - |
| 2.2 | execute_graph.py 수정 | 1h | **P0** | Task 2.1 |
| 2.3 | execute_prompts.py 작성 | 2h | **P0** | - |
| 3.1 | response_nodes.py 수정 | 4h | P1 | - |
| 3.2 | response_graph.py 수정 | 1h | P1 | Task 3.1 |
| 3.3 | response_prompts.py 작성 | 3h | P1 | - |
| 테스트 | Execute/Response 테스트 | 4h | P1 | All |

**예상 총 시간**: 17시간 (2-3일)

**완료 기준**:
- ✅ Aggregator 노드가 LLM으로 인사이트 생성
- ✅ Chat/Graph/Report Generator 노드 동작
- ✅ 통합 테스트 통과

---

### Sprint 3: Octostrator Integration (Week 3)

**목표**: 전체 계층 통합 및 Context 전달

| Task | 파일 | 예상 시간 | 우선순위 | 의존성 |
|------|------|----------|---------|--------|
| 4.1 | octostrator_nodes.py 수정 | 4h | **P0** | Sprint 1, 2 |
| 4.2 | octostrator_graph.py 수정 | 3h | **P0** | Task 4.1 |
| 5.1 | Helper 클래스 수정 | 3h | P1 | Task 4.2 |
| 통합 테스트 | End-to-end 테스트 | 5h | **P0** | All |
| 성능 측정 | 토큰 사용량 측정 | 2h | P1 | 통합 테스트 |

**예상 총 시간**: 17시간 (2-3일)

**완료 기준**:
- ✅ 4개 계층이 순차적으로 동작
- ✅ Context가 모든 계층에 전달됨
- ✅ End-to-end 워크플로우 성공
- ✅ 토큰 사용량 예상치(36.9%) 달성

---

### Sprint 4: Optimization & Documentation (Week 4)

**목표**: 최적화 및 문서화

| Task | 내용 | 예상 시간 | 우선순위 |
|------|------|----------|---------|
| 최적화 | 프롬프트 압축 (Phase 3) | 6h | P2 |
| 최적화 | State 크기 최소화 | 4h | P2 |
| 문서화 | API 사용 가이드 | 4h | P1 |
| 문서화 | 마이그레이션 가이드 | 3h | P1 |
| 리팩토링 | 코드 정리 및 주석 | 3h | P2 |

**예상 총 시간**: 20시간 (3일)

**완료 기준**:
- ✅ Production 환경에서 안정적 동작
- ✅ 문서화 완료
- ✅ 코드 리뷰 통과

---

## 📊 예상 효과

### 1. 토큰 사용량 감소

**시나리오**: "다이어트 계획 작성해줘" 요청 (Cognitive → Execute → Response 전체 플로우)

| 계층 | 노드 | Before (균일) | After (최적화) | 절감 |
|------|------|--------------|---------------|------|
| **Cognitive** | Intent | 4096 | 1024 | **-75%** |
| **Cognitive** | Planning | 4096 | 2048 | **-50%** |
| **Cognitive** | Validator | 4096 | 2048 | **-50%** |
| **Execute** | Aggregator | 4096 | 3072 | **-25%** |
| **Response** | Chat Gen | 4096 | 4096 | 0% |
| **합계** | | 20480 | 12288 | **-40%** |

**Production 환경 (더 공격적 최적화)**:
- Intent: 4096 → 800 (**-80%**)
- Planning: 4096 → 2048 (**-50%**)
- Validator: 4096 → 2048 (**-50%**)
- Aggregator: 4096 → 3000 (**-27%**)
- Chat: 4096 → 3000 (**-27%**)
- **합계**: 20480 → 10848 (**-47%**)

### 2. 비용 절감

**가정**: gpt-4o-mini 가격 ($0.15/1M input, $0.60/1M output)

| 환경 | 월 요청 수 | Before 비용 | After 비용 | 절감액 | 절감률 |
|------|-----------|-------------|-----------|--------|--------|
| Production | 10,000 | $8.19 | $4.34 | **$3.85** | **47%** |
| Production | 100,000 | $81.92 | $43.39 | **$38.53** | **47%** |
| Production | 1,000,000 | $819.20 | $433.92 | **$385.28** | **47%** |

**연간 절감액** (100K 요청/월): **$462.36**

### 3. 환경별 특화

| 환경 | 목적 | 주요 최적화 | 예상 효과 |
|------|------|------------|----------|
| **Production** | 비용 절감 | 낮은 temp, 적은 tokens | **47% 절감** |
| **Development** | 품질 향상 | 높은 temp, 넉넉한 tokens | 다양한 응답 |
| **Testing** | 재현성 | temp=0, 최소 tokens | 빠른 테스트 |

---

## 🔒 주의사항 및 리스크

### 1. 계층 간 State 전달

**이슈**: 각 계층이 독립적인 State를 사용할 경우 데이터 손실 가능

**해결책**:
- Octostrator State를 모든 하위 계층에서 공유
- 각 계층이 State의 특정 부분만 업데이트
- State 스키마 일관성 유지

```python
# 예시: 공통 State 구조
class OctostratorState(TypedDict):
    # Common
    user_query: str
    session_id: str
    user_id: str

    # Cognitive Layer
    user_intent: Optional[str]
    plan: Optional[Dict]
    plan_valid: bool

    # Execute Layer
    execution_results: List[Dict]
    aggregated_data: Optional[Dict]

    # Response Layer
    final_result: Optional[str]
    response_type: str
```

### 2. Context 직렬화

**이슈**: AppContext가 Checkpoint에 저장되면 안됨 (Phase 2 설계)

**확인 필요**:
```python
# context_schema로 등록하면 Checkpoint에 저장되지 않음
graph = StateGraph(state_class, context_schema=AppContext)
```

**검증 방법**: Checkpoint 크기 측정 (Context 포함 여부 확인)

### 3. LLM API 키 관리

**이슈**: 각 노드에서 API 키를 반복해서 가져옴

**개선안**:
```python
# AppContext에 API 키 캐싱
@dataclass
class AppContext:
    user_id: str
    session_id: str
    llm_settings: LLMSettings
    _api_key: Optional[str] = None  # 캐시

    @property
    def api_key(self) -> str:
        if self._api_key is None:
            from backend.app.config.system import config
            self._api_key = config.openai_api_key
        return self._api_key
```

### 4. 환경 변수 감지

**이슈**: `SYSTEM_ENV` 환경 변수가 설정되지 않으면 기본값 사용

**권장 설정**:
```bash
# Production
export SYSTEM_ENV=production

# Development (기본값)
export SYSTEM_ENV=development

# Testing
export SYSTEM_ENV=testing
```

**코드 검증**:
```python
import os
env = os.getenv("SYSTEM_ENV", "development")
logger.info(f"Running in {env} mode")
```

---

## 🧪 테스트 계획

### 1. 단위 테스트 (Layer별)

#### Cognitive Layer

**파일**: `tests/octostrator/supervisors/cognitive/test_cognitive_nodes.py`

```python
import pytest
from backend.app.octostrator.supervisors.cognitive.cognitive_nodes import (
    intent_understanding_node,
    planning_node,
    validator_node
)
from backend.app.octostrator.contexts.app_context import AppContext
from backend.app.config.llm_settings import get_llm_settings, Environment

@pytest.fixture
def test_context():
    """테스트용 Context"""
    settings = get_llm_settings(Environment.TESTING)
    return AppContext(
        user_id="test_user",
        session_id="test_session",
        llm_settings=settings
    )

@pytest.mark.asyncio
async def test_intent_understanding_node(test_context):
    """Intent Understanding 노드 테스트"""
    state = {"user_query": "다이어트 계획 작성해줘"}

    # Runtime 모킹
    from unittest.mock import Mock
    runtime = Mock()
    runtime.context = test_context

    result = await intent_understanding_node(state, runtime)

    assert "user_intent" in result
    assert "intent_confidence" in result
    assert result["intent_confidence"] >= 0.0

@pytest.mark.asyncio
async def test_planning_node(test_context):
    """Planning 노드 테스트"""
    state = {
        "user_query": "다이어트 계획 작성해줘",
        "user_intent": "diet_query"
    }

    runtime = Mock()
    runtime.context = test_context

    result = await planning_node(state, runtime)

    assert "plan" in result
    assert result["plan"] is not None
    assert "steps" in result["plan"]
```

#### Execute Layer

**파일**: `tests/octostrator/supervisors/execute/test_execute_nodes.py`

```python
@pytest.mark.asyncio
async def test_aggregator_node(test_context):
    """Aggregator 노드 테스트"""
    state = {
        "execution_results": [
            {"step_id": "step_1", "status": "completed", "result": "Done"},
            {"step_id": "step_2", "status": "completed", "result": "Done"}
        ]
    }

    runtime = Mock()
    runtime.context = test_context

    result = await aggregator_node(state, runtime)

    assert "aggregated_data" in result
    assert result["aggregated_data"]["total_steps"] == 2
    assert result["aggregated_data"]["completed_steps"] == 2
```

#### Response Layer

**파일**: `tests/octostrator/supervisors/response/test_response_nodes.py`

```python
@pytest.mark.asyncio
async def test_chat_generator_node(test_context):
    """Chat Generator 노드 테스트"""
    state = {
        "aggregated_data": {
            "total_steps": 2,
            "completed_steps": 2,
            "summary": "All tasks completed"
        }
    }

    runtime = Mock()
    runtime.context = test_context

    result = await chat_generator_node(state, runtime)

    assert "final_result" in result
    assert "response_type" in result
    assert result["response_type"] == "chat"
```

### 2. 통합 테스트 (End-to-End)

**파일**: `tests/octostrator/supervisors/test_octostrator_integration.py`

```python
import pytest
from backend.app.octostrator.supervisors.octostrator.octostrator_graph import (
    build_octostrator_graph
)
from backend.app.config.llm_settings import get_llm_settings, Environment

@pytest.mark.asyncio
async def test_full_workflow():
    """전체 워크플로우 테스트"""

    # 1. Graph 빌드
    graph = build_octostrator_graph(
        user_id="test_user",
        session_id="test_session"
    )

    # 2. 실행
    result = await graph.ainvoke({
        "user_query": "다이어트 계획 작성해줘",
        "output_format": "chat"
    })

    # 3. 검증
    assert "plan" in result
    assert "aggregated_data" in result
    assert "final_result" in result
    assert result.get("plan_valid") == True

@pytest.mark.asyncio
async def test_environment_switching():
    """환경별 설정 전환 테스트"""

    # Production
    os.environ["SYSTEM_ENV"] = "production"
    graph_prod = build_octostrator_graph()
    # ... 토큰 사용량 측정

    # Development
    os.environ["SYSTEM_ENV"] = "development"
    graph_dev = build_octostrator_graph()
    # ... 토큰 사용량 측정

    # 비교
    # assert prod_tokens < dev_tokens
```

### 3. 성능 테스트

**파일**: `tests/octostrator/supervisors/test_performance.py`

```python
@pytest.mark.asyncio
async def test_token_usage():
    """토큰 사용량 측정"""

    from langchain.callbacks import get_openai_callback

    graph = build_octostrator_graph()

    with get_openai_callback() as cb:
        result = await graph.ainvoke({
            "user_query": "다이어트 계획 작성해줘",
            "output_format": "chat"
        })

        total_tokens = cb.total_tokens
        logger.info(f"Total tokens: {total_tokens}")

        # 예상치와 비교
        assert total_tokens < 15000  # Production 환경 기준
```

---

## 📚 참고 자료

### 1. 관련 문서

- [Phase 2 완료 보고서](./PHASE2_COMPLETION_REPORT_251105.md)
- [Phase 2 Day 1 보고서](../phase2/PHASE2_DAY1_COMPLETION_251105.md)
- [Context API Implementation Guide](./IMPLEMENTATION_GUIDE_CONTEXT_API.md)
- [LangGraph Context Analysis](./LANGGRAPH_CONTEXT_ANALYSIS.md)

### 2. LangGraph 공식 문서

- [Context API](https://langchain-ai.github.io/langgraph/concepts/low_level/#context)
- [StateGraph Schema](https://langchain-ai.github.io/langgraph/reference/graphs/#langgraph.graph.StateGraph)
- [Runtime Object](https://langchain-ai.github.io/langgraph/reference/runtime/)
- [Subgraphs](https://langchain-ai.github.io/langgraph/how-tos/subgraph/)

### 3. 코드 참조

#### 현재 구조 (계층형)
```
backend/app/octostrator/
├── supervisors/octostrator/octostrator_graph.py
├── supervisors/cognitive/cognitive_graph.py
├── supervisors/execute/execute_graph.py
├── supervisors/response/response_graph.py
├── contexts/app_context.py  (✅ Phase 2 완료)
└── config/llm_settings.py   (✅ Phase 2 완료)
```

#### Phase 2 구조 (이전)
```
backend/app/octostrator/
├── supervisor/nodes/cognitive_nodes.py  (참고용)
└── supervisor/graphs/main_graph.py      (참고용)
```

---

## ✅ 체크리스트

### Phase 2.1: Cognitive Layer (P0)
- [ ] cognitive_nodes.py 수정 (3개 노드)
- [ ] cognitive_graph.py context_schema 등록
- [ ] cognitive_prompts.py 작성
- [ ] cognitive_helpers.py CognitiveSupervisor 수정
- [ ] 단위 테스트 작성 및 통과

### Phase 2.2: Execute Layer (P0)
- [ ] execute_nodes.py aggregator_node 수정
- [ ] execute_graph.py context_schema 등록
- [ ] execute_prompts.py 작성
- [ ] 단위 테스트 작성 및 통과

### Phase 2.3: Response Layer (P1)
- [ ] response_nodes.py 수정 (3개 generator)
- [ ] response_graph.py context_schema 등록
- [ ] response_prompts.py 작성
- [ ] 단위 테스트 작성 및 통과

### Phase 2.4: Octostrator Integration (P0)
- [ ] octostrator_nodes.py 수정 (4개 layer 노드)
- [ ] octostrator_graph.py context_schema 등록
- [ ] 통합 테스트 작성 및 통과

### Phase 2.5: Helper Classes (P1)
- [ ] CognitiveSupervisor Context 지원
- [ ] ExecuteSupervisor Context 지원
- [ ] ResponseSupervisor Context 지원
- [ ] TodoAgent Context 지원

### Testing & Validation
- [ ] 모든 단위 테스트 통과
- [ ] 통합 테스트 (E2E) 통과
- [ ] 환경별 전환 테스트 (Prod/Dev/Test)
- [ ] 토큰 사용량 측정 (예상치 47% 절감 확인)
- [ ] 성능 테스트 (응답 시간, 메모리 사용량)

### Documentation
- [ ] API 사용 가이드 작성
- [ ] 마이그레이션 가이드 작성
- [ ] 코드 주석 보완
- [ ] 예제 코드 작성

### Production Readiness
- [ ] 환경 변수 설정 가이드
- [ ] 에러 핸들링 강화
- [ ] 로깅 및 모니터링 설정
- [ ] 보안 검토 (API 키 관리 등)

---

## 🎯 최종 목표

**3주 내 완료**:
1. ✅ **계층형 슈퍼바이저에 Context API 전면 적용**
2. ✅ **7개 LLM 노드 활성화** (Cognitive 3개 + Aggregator 1개 + Response 3개)
3. ✅ **Production 환경에서 47% 비용 절감 달성**
4. ✅ **환경별 최적화** (Production/Development/Testing)
5. ✅ **확장 가능한 구조 확립** (향후 Agent 추가 용이)

**성공 지표**:
- 모든 테스트 통과 (단위 + 통합 + E2E)
- Production 환경에서 토큰 사용량 47% 감소
- 개발자 경험 향상 (Context API로 코드 간결화)
- 시스템 안정성 유지 (에러율 1% 미만)

---

**작성자**: Claude (Anthropic)
**검토 필요**: 시스템 아키텍처 팀, 개발 팀
**승인 대기**: 마이그레이션 계획 승인 후 작업 시작

---

**END OF MIGRATION PLAN**
