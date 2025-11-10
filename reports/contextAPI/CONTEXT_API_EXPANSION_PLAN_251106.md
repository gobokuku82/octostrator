# Context API 확장 적용 계획서
## 추가 비용 절감 및 시스템 최적화 로드맵

**작성일**: 2025-11-06
**대상**: AI PT Manager - Octostrator 전체 시스템
**현재 상태**: Octostrator + Execute Layer 완료 (45.9% 비용 절감 달성)
**목표**: 전체 시스템 Context API 적용 (최종 70% 비용 절감)

---

## 📋 Executive Summary

### 현재 완료 상황
✅ **Phase 2 완료** (2025-11-06):
- [octostrator_graph.py](../../backend/app/octostrator/supervisors/octostrator/octostrator_graph.py) - Context API 적용 완료
- [execute_graph.py](../../backend/app/octostrator/supervisors/execute/execute_graph.py) - Context API 적용 완료
- **비용 절감 달성**: 45.9% (Production vs Development)

### 확장 적용 기회

현재 시스템에 **3가지 추가 확장 영역**이 발견되었습니다:

| 확장 영역 | 대상 | 예상 절감 | 우선순위 | 작업 시간 |
|----------|------|----------|---------|----------|
| **Supervisor Graphs** | 2개 그래프 | +10% | **P0** | 20분 |
| **Individual Agents** | 7개 에이전트 | +10% | P1 | 3.5시간 |
| **Node Implementation** | 6개 노드 | - | P2 | 2시간 |

**최종 목표**: Production 환경에서 **70% 비용 절감** 달성

---

## 🎯 확장 영역 상세 분석

### 1. Supervisor Layer Graphs (P0 - 최우선)

#### 1.1 Cognitive Graph

**파일**: [backend/app/octostrator/supervisors/cognitive/cognitive_graph.py](../../backend/app/octostrator/supervisors/cognitive/cognitive_graph.py)

**현재 상태**:
```python
def build_cognitive_graph(state_class=None):
    """Build the cognitive layer workflow graph."""
    if state_class is None:
        state_class = dict

    # ❌ context_schema 없음
    graph = StateGraph(state_class)

    # Add nodes
    graph.add_node("intent", intent_understanding_node)
    graph.add_node("planning", planning_node)
    graph.add_node("validator", validator_node)
    # ...
    return graph.compile()
```

**적용 후**:
```python
from typing import Optional

def build_cognitive_graph(
    state_class=None,
    context: Optional["AppContext"] = None  # ⭐ 추가
):
    """
    Build the cognitive layer workflow graph with Context API.

    Phase 2 Updates:
    - Context API 지원: context_schema 파라미터로 runtime 자동 주입
    - 환경별 LLM 설정 자동 적용 (SYSTEM_ENV 환경 변수)
    - 노드별 LLM 파라미터 최적화 (비용 절감)

    Args:
        state_class: State class (default: dict)
        context: AppContext instance (optional)
                 None이면 환경 변수에서 자동 생성
    """
    # State 기본값
    if state_class is None:
        state_class = dict

    # ⭐ Phase 2: Context 자동 생성
    if context is None:
        from backend.app.octostrator.contexts.app_context import AppContext
        from backend.app.config.llm_settings import get_llm_settings_from_env

        llm_settings = get_llm_settings_from_env()
        context = AppContext(
            user_id="default_user",
            session_id="default_session",
            llm_settings=llm_settings
        )

    # ⭐ Phase 2: Context API 활성화
    graph = StateGraph(
        state_class,
        context_schema=type(context)  # ✅ AppContext 클래스
    )

    # Add nodes (Runtime 자동 주입됨)
    graph.add_node("intent", intent_understanding_node)
    graph.add_node("planning", planning_node)
    graph.add_node("validator", validator_node)

    # Add edges
    graph.add_edge(START, "intent")
    graph.add_edge("intent", "planning")
    graph.add_edge("planning", "validator")
    graph.add_edge("validator", END)

    return graph.compile()
```

**변경 사항**:
1. `context` 파라미터 추가
2. Context 자동 생성 로직 추가 (환경 변수 기반)
3. `context_schema=type(context)` 추가

**예상 효과**:
- Intent/Planning/Validator 노드에서 Runtime 접근 가능
- 환경별 LLM 설정 자동 적용
- Cognitive Layer 비용 30-40% 절감

**예상 작업 시간**: 10분

---

#### 1.2 Response Graph

**파일**: [backend/app/octostrator/supervisors/response/response_graph.py](../../backend/app/octostrator/supervisors/response/response_graph.py)

**현재 상태**:
```python
def build_response_graph(state_class=None):
    """Build the response layer workflow graph."""
    if state_class is None:
        state_class = dict

    # ❌ context_schema 없음
    graph = StateGraph(state_class)

    # Add nodes
    graph.add_node("hitl", hitl_handler_node)
    graph.add_node("router", output_router_node)
    graph.add_node("chat_gen", chat_generator_node)
    graph.add_node("graph_gen", graph_generator_node)
    graph.add_node("report_gen", report_generator_node)
    # ...
    return graph.compile()
```

**적용 후**:
```python
from typing import Optional

def build_response_graph(
    state_class=None,
    context: Optional["AppContext"] = None  # ⭐ 추가
):
    """
    Build the response layer workflow graph with Context API.

    Phase 2 Updates:
    - Context API 지원
    - 환경별 LLM 설정 자동 적용
    - Generator 노드별 최적화
    """
    # State 기본값
    if state_class is None:
        state_class = dict

    # ⭐ Context 자동 생성
    if context is None:
        from backend.app.octostrator.contexts.app_context import AppContext
        from backend.app.config.llm_settings import get_llm_settings_from_env

        context = AppContext(
            user_id="default_user",
            session_id="default_session",
            llm_settings=get_llm_settings_from_env()
        )

    # ⭐ Context API 활성화
    graph = StateGraph(
        state_class,
        context_schema=type(context)
    )

    # Add nodes
    graph.add_node("hitl", hitl_handler_node)
    graph.add_node("router", output_router_node)
    graph.add_node("chat_gen", chat_generator_node)
    graph.add_node("graph_gen", graph_generator_node)
    graph.add_node("report_gen", report_generator_node)

    # Add edges
    graph.add_edge(START, "hitl")
    graph.add_edge("hitl", "router")

    graph.add_conditional_edges(
        "router",
        lambda x: x.get("selected_format", "chat"),
        {
            "chat": "chat_gen",
            "graph": "graph_gen",
            "report": "report_gen"
        }
    )

    graph.add_edge("chat_gen", END)
    graph.add_edge("graph_gen", END)
    graph.add_edge("report_gen", END)

    return graph.compile()
```

**변경 사항**: Cognitive Graph와 동일 패턴

**예상 효과**:
- Chat/Graph/Report Generator 노드에서 Runtime 접근 가능
- Generator별 최적화된 LLM 설정 (chat: 0.7/4096, graph: 0.2/2048, report: 0.5/8192)
- Response 품질 향상

**예상 작업 시간**: 10분

---

### 2. Individual Agents (P1 - 높음)

#### 2.1 발견된 에이전트 목록

| # | Agent | 파일 | 용도 | LLM 사용 |
|---|-------|------|------|----------|
| 1 | **Frontdesk Agent** | [frontdesk_agent.py](../../backend/app/octostrator/agents/frontdesk/frontdesk_agent.py) | 프론트 데스크 관리 | ✅ |
| 2 | **Assessor Agent** | [assessor_agent.py](../../backend/app/octostrator/agents/assessor/assessor_agent.py) | 회원 평가/분석 | ✅ |
| 3 | **Program Designer** | [program_designer_agent.py](../../backend/app/octostrator/agents/program_designer/program_designer_agent.py) | 운동 프로그램 설계 | ✅ |
| 4 | **Manager Agent** | [manager_agent.py](../../backend/app/octostrator/agents/manager/manager_agent.py) | 센터 관리 | ✅ |
| 5 | **Trainer Education** | [trainer_education_agent.py](../../backend/app/octostrator/agents/trainer_education/trainer_education_agent.py) | 트레이너 교육 | ✅ |
| 6 | **Marketing Agent** | [marketing_agent.py](../../backend/app/octostrator/agents/marketing/marketing_agent.py) | 마케팅 자동화 | ✅ |
| 7 | **Owner Assistant** | [owner_assistant_agent.py](../../backend/app/octostrator/agents/owner_assistant/owner_assistant_agent.py) | 원장 업무 지원 | ✅ |

**총 7개 에이전트**, 모두 LLM 사용

---

#### 2.2 BaseAgent 구조 분석

**파일**: [backend/app/octostrator/agents/base/base_agent.py](../../backend/app/octostrator/agents/base/base_agent.py)

**현재 build_graph 시그니처**:
```python
class BaseAgent(ABC):
    @abstractmethod
    def build_graph(self, llm=None) -> StateGraph:
        """Agent의 LangGraph workflow 구축"""
        pass
```

**제안하는 확장**:
```python
class BaseAgent(ABC):
    @abstractmethod
    def build_graph(
        self,
        llm=None,
        context: Optional["AppContext"] = None  # ⭐ 추가
    ) -> StateGraph:
        """Agent의 LangGraph workflow 구축

        Phase 2 Updates:
        - context 파라미터 추가
        - Context API 지원
        - 환경별 LLM 설정 자동 적용

        Args:
            llm: Language Model (backward compatibility)
            context: AppContext instance (Phase 2)
        """
        pass
```

**각 Agent 구현 예시**:
```python
class FrontdeskAgent(BaseAgent):
    def build_graph(
        self,
        llm=None,
        context: Optional["AppContext"] = None
    ) -> StateGraph:
        """Frontdesk Agent workflow 구축"""

        # ⭐ Context 자동 생성
        if context is None:
            from backend.app.octostrator.contexts.app_context import AppContext
            from backend.app.config.llm_settings import get_llm_settings_from_env

            context = AppContext(
                user_id="default_user",
                session_id="default_session",
                llm_settings=get_llm_settings_from_env()
            )

        # ⭐ Context API 활성화
        graph = StateGraph(
            FrontdeskState,
            context_schema=type(context)
        )

        # Add nodes (Runtime 자동 주입)
        graph.add_node("process", self._process_node)
        graph.add_node("validate", self._validate_node)
        # ...

        return graph

    async def _process_node(
        self,
        state: FrontdeskState,
        runtime: Runtime  # ⭐ Runtime 자동 주입
    ) -> Dict:
        """Processing node with Context API"""
        # Context에서 설정 추출
        context: AppContext = runtime.context
        settings = context.llm_settings

        # 노드별 LLM 생성
        llm = ChatOpenAI(
            model=settings.agent_model,
            temperature=settings.agent_temperature,
            max_tokens=settings.agent_max_tokens,
            api_key=...
        )

        # LLM 실행
        response = await llm.ainvoke(...)
        return {"result": response.content}
```

---

#### 2.3 에이전트별 적용 계획

**Phase 2.1: Core Agents (우선순위 1)**

| Agent | 적용 순서 | 예상 시간 | 비고 |
|-------|----------|----------|------|
| Assessor | 1 | 30분 | 회원 평가 - 핵심 기능 |
| Program Designer | 2 | 30분 | 운동 프로그램 설계 - 핵심 |
| Frontdesk | 3 | 30분 | 프론트 데스크 - 자주 사용 |

**Phase 2.2: Support Agents (우선순위 2)**

| Agent | 적용 순서 | 예상 시간 | 비고 |
|-------|----------|----------|------|
| Manager | 4 | 30분 | 센터 관리 |
| Owner Assistant | 5 | 30분 | 원장 업무 지원 |

**Phase 2.3: Extended Agents (우선순위 3)**

| Agent | 적용 순서 | 예상 시간 | 비고 |
|-------|----------|----------|------|
| Trainer Education | 6 | 30분 | 트레이너 교육 |
| Marketing | 7 | 30분 | 마케팅 자동화 |

**총 예상 시간**: 3.5시간

---

#### 2.4 에이전트별 LLM 설정 커스터마이징

**현재 AppContext의 agent_* 설정**:
```python
class LLMSettings(BaseModel):
    # Agent Nodes (준비됨)
    agent_temperature: float = Field(default=0.5)
    agent_max_tokens: int = Field(default=4096)
    agent_model: str = Field(default="gpt-4o-mini")
```

**확장 제안** (선택적):

각 에이전트별로 특화된 설정을 추가할 수 있습니다:

```python
class LLMSettings(BaseModel):
    # ... 기존 설정들 ...

    # ⭐ 에이전트별 커스터마이징 (선택적)

    # Assessor Agent (정확한 평가 필요)
    assessor_temperature: float = Field(default=0.3)
    assessor_max_tokens: int = Field(default=3072)

    # Program Designer (창의적 설계)
    program_designer_temperature: float = Field(default=0.7)
    program_designer_max_tokens: int = Field(default=6144)

    # Frontdesk (빠른 응답)
    frontdesk_temperature: float = Field(default=0.5)
    frontdesk_max_tokens: int = Field(default=2048)

    # Manager (균형)
    manager_temperature: float = Field(default=0.5)
    manager_max_tokens: int = Field(default=4096)

    # Marketing (창의적 카피)
    marketing_temperature: float = Field(default=0.8)
    marketing_max_tokens: int = Field(default=4096)

    # Trainer Education (교육 콘텐츠)
    trainer_education_temperature: float = Field(default=0.6)
    trainer_education_max_tokens: int = Field(default=5120)

    # Owner Assistant (분석 및 보고)
    owner_assistant_temperature: float = Field(default=0.4)
    owner_assistant_max_tokens: int = Field(default=6144)
```

**환경별 프리셋 확장** (선택적):

```python
# Production: 비용 최적화
PRODUCTION_PRESET = {
    # ... 기존 설정 ...
    "assessor_temperature": 0.2,
    "assessor_max_tokens": 2048,
    "program_designer_temperature": 0.5,
    "program_designer_max_tokens": 4096,
    # ...
}

# Development: 품질 우선
DEVELOPMENT_PRESET = {
    # ... 기존 설정 ...
    "assessor_temperature": 0.3,
    "assessor_max_tokens": 3072,
    "program_designer_temperature": 0.7,
    "program_designer_max_tokens": 6144,
    # ...
}
```

**권장사항**: 먼저 공통 `agent_*` 설정으로 모든 에이전트에 적용하고, 필요시 개별 커스터마이징 추가

---

### 3. Node Implementation (P2 - 선택)

#### 3.1 Cognitive Layer 노드들

**파일**: [backend/app/octostrator/supervisors/cognitive/cognitive_nodes.py](../../backend/app/octostrator/supervisors/cognitive/cognitive_nodes.py)

**현재 상태** (TODO 주석):
```python
async def intent_understanding_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Intent Understanding Node - TODO: Implement with LLM"""
    try:
        user_query = state.get("user_query", "")
        # TODO: Implement with LLM or classifier
        logger.info(f"[Intent] Analyzing: {user_query[:50]}...")

        return {
            "user_intent": "multi_step_task",  # Default
            "intent_confidence": 0.8
        }
    except Exception as e:
        logger.error(f"[Intent] Error: {e}")
        return {"error": str(e)}
```

**Context API 적용 후**:
```python
from langgraph.types import Runtime
from backend.app.octostrator.contexts.app_context import AppContext
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage

async def intent_understanding_node(
    state: Dict[str, Any],
    runtime: Runtime  # ⭐ Runtime 추가
) -> Dict[str, Any]:
    """Intent Understanding Node - LLM으로 의도 분석"""
    try:
        # 1. Context에서 설정 추출
        context: AppContext = runtime.context
        settings = context.llm_settings

        # 2. 노드별 LLM 생성
        from backend.app.config.system import config as system_config
        llm = ChatOpenAI(
            model=settings.intent_model,
            temperature=settings.intent_temperature,  # 0.7 (창의적)
            max_tokens=settings.intent_max_tokens,    # 1024
            api_key=system_config.openai_api_key
        )

        # 3. 프롬프트 생성
        user_query = state.get("user_query", "")
        prompt = f"""
당신은 PT 관리 시스템의 의도 분석 전문가입니다.

사용자 요청: {user_query}

다음 카테고리 중 하나로 분류하세요:
- frontdesk_inquiry: 프론트 데스크 문의
- member_assessment: 회원 평가 요청
- program_design: 운동 프로그램 설계
- center_management: 센터 관리
- marketing: 마케팅 관련
- trainer_education: 트레이너 교육
- owner_report: 원장 보고서

JSON 형식으로 응답:
{{"intent": "카테고리", "confidence": 0.0-1.0, "reasoning": "이유"}}
        """

        # 4. LLM 실행
        logger.info(f"[Intent] Analyzing: {user_query[:50]}...")
        response = await llm.ainvoke([SystemMessage(content=prompt)])

        # 5. 결과 파싱
        import json
        try:
            result = json.loads(response.content)
            return {
                "user_intent": result.get("intent"),
                "intent_confidence": result.get("confidence", 0.8),
                "intent_reasoning": result.get("reasoning", "")
            }
        except json.JSONDecodeError:
            # Fallback
            return {
                "user_intent": "multi_step_task",
                "intent_confidence": 0.5
            }

    except Exception as e:
        logger.error(f"[Intent] Error: {e}")
        return {"error": str(e)}
```

**동일 패턴 적용 대상**:
- `planning_node`: 계획 수립 (temp=0.3, tokens=2048)
- `validator_node`: 계획 검증 (temp=0.3, tokens=2048)

**예상 작업 시간**: 각 40분 (총 2시간)

---

#### 3.2 Response Layer 노드들

**파일**: [backend/app/octostrator/supervisors/response/response_nodes.py](../../backend/app/octostrator/supervisors/response/response_nodes.py)

**현재 상태** (TODO 주석):
```python
async def chat_generator_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Chat Generator - TODO: Implement with LLM"""
    aggregated_data = state.get("aggregated_data", {})

    # Template-based response
    response = f"""
작업이 완료되었습니다! 🎉

📊 실행 결과:
- 총 작업: {aggregated_data.get('total_steps', 0)}개
- 완료: {aggregated_data.get('completed_steps', 0)}개
    """

    return {"final_result": response, "response_type": "chat"}
```

**Context API 적용 후**:
```python
from langgraph.types import Runtime

async def chat_generator_node(
    state: Dict[str, Any],
    runtime: Runtime  # ⭐ Runtime 추가
) -> Dict[str, Any]:
    """Chat Generator - LLM으로 자연어 응답 생성"""
    try:
        # 1. Context에서 설정 추출
        context: AppContext = runtime.context
        settings = context.llm_settings

        # 2. LLM 생성 (chat 특화 설정)
        llm = ChatOpenAI(
            model=settings.chat_model,
            temperature=settings.chat_temperature,  # 0.7 (자연스러움)
            max_tokens=settings.chat_max_tokens,    # 4096
            api_key=system_config.openai_api_key
        )

        # 3. 프롬프트 생성
        aggregated_data = state.get("aggregated_data", {})
        prompt = f"""
당신은 PT 센터의 친절한 AI 어시스턴트입니다.

실행 결과:
- 총 작업: {aggregated_data.get('total_steps', 0)}개
- 완료: {aggregated_data.get('completed_steps', 0)}개
- 실패: {aggregated_data.get('failed_steps', 0)}개
- 요약: {aggregated_data.get('summary', '')}

위 결과를 바탕으로 사용자에게 친절하고 자연스러운 응답을 생성하세요.
한국어로 작성하고, 이모지를 적절히 사용하세요.
        """

        # 4. LLM 실행
        response = await llm.ainvoke([SystemMessage(content=prompt)])

        return {
            "final_result": response.content,
            "response_type": "chat"
        }

    except Exception as e:
        logger.error(f"[ChatGen] Error: {e}")
        return {"error": str(e)}
```

**동일 패턴 적용 대상**:
- `graph_generator_node`: 그래프 데이터 생성 (temp=0.2, tokens=2048, Structured Output)
- `report_generator_node`: 보고서 생성 (temp=0.5, tokens=8192)

**예상 작업 시간**: 각 40분 (총 2시간)

---

## 📅 전체 로드맵

### Phase 2.1: Supervisor Graphs (Week 1 - Day 1)

**목표**: 모든 Supervisor Layer에 Context API 적용

| 작업 | 파일 | 예상 시간 | 우선순위 | 완료 기준 |
|------|------|----------|---------|----------|
| Cognitive Graph 적용 | cognitive_graph.py | 10분 | **P0** | context_schema 등록 |
| Response Graph 적용 | response_graph.py | 10분 | **P0** | context_schema 등록 |
| 통합 테스트 | - | 10분 | **P0** | E2E 동작 확인 |

**총 시간**: 30분

**완료 기준**:
- ✅ 2개 그래프 파일에 context_schema 추가
- ✅ 환경 변수 전환 테스트 (Production/Development/Testing)
- ✅ 기존 기능 정상 동작 확인

**예상 효과**:
- 전체 비용 절감: 45.9% → **55%** (+10%)

---

### Phase 2.2: Individual Agents (Week 1-2)

**목표**: 7개 에이전트에 Context API 적용

#### Sprint 1: Core Agents (Day 2-3)

| 작업 | Agent | 예상 시간 | 완료 기준 |
|------|-------|----------|----------|
| 1 | Assessor Agent | 30분 | build_graph() context 지원 |
| 2 | Program Designer | 30분 | build_graph() context 지원 |
| 3 | Frontdesk Agent | 30분 | build_graph() context 지원 |
| 테스트 | 3개 Agent | 30분 | 개별 동작 확인 |

**소계**: 2시간

#### Sprint 2: Support Agents (Day 4)

| 작업 | Agent | 예상 시간 | 완료 기준 |
|------|-------|----------|----------|
| 4 | Manager Agent | 30분 | build_graph() context 지원 |
| 5 | Owner Assistant | 30분 | build_graph() context 지원 |
| 테스트 | 2개 Agent | 20분 | 개별 동작 확인 |

**소계**: 1시간 20분

#### Sprint 3: Extended Agents (Day 5)

| 작업 | Agent | 예상 시간 | 완료 기준 |
|------|-------|----------|----------|
| 6 | Trainer Education | 30분 | build_graph() context 지원 |
| 7 | Marketing Agent | 30분 | build_graph() context 지원 |
| 통합 테스트 | 전체 | 30분 | 전체 동작 확인 |

**소계**: 1시간 30분

**Phase 2.2 총 시간**: 4시간 50분

**완료 기준**:
- ✅ BaseAgent.build_graph() 시그니처 확장
- ✅ 7개 에이전트 모두 Context API 지원
- ✅ 환경 변수 기반 LLM 설정 자동 적용
- ✅ 개별 및 통합 테스트 통과

**예상 효과**:
- 전체 비용 절감: 55% → **65%** (+10%)
- 에이전트별 LLM 최적화 가능

---

### Phase 2.3: Node Implementation (Week 2-3, 선택적)

**목표**: 노드 실제 LLM 구현

#### Sprint 4: Cognitive Nodes (선택)

| 작업 | 노드 | 예상 시간 | 완료 기준 |
|------|------|----------|----------|
| 1 | intent_understanding_node | 40분 | LLM 의도 분석 |
| 2 | planning_node | 40분 | LLM 계획 수립 |
| 3 | validator_node | 40분 | LLM 계획 검증 |

**소계**: 2시간

#### Sprint 5: Response Nodes (선택)

| 작업 | 노드 | 예상 시간 | 완료 기준 |
|------|------|----------|----------|
| 1 | chat_generator_node | 40분 | LLM 대화 생성 |
| 2 | graph_generator_node | 40분 | LLM 그래프 데이터 |
| 3 | report_generator_node | 40분 | LLM 보고서 생성 |

**소계**: 2시간

**Phase 2.3 총 시간**: 4시간

**완료 기준**:
- ✅ 6개 노드에 Runtime 파라미터 추가
- ✅ LLM 실제 호출 구현
- ✅ Context API로 설정 추출
- ✅ 프롬프트 작성 및 테스트

**예상 효과**:
- 기능 완성도 향상 (TODO 제거)
- 실제 AI 기능 활성화

---

## 📊 예상 효과 분석

### 1. 단계별 비용 절감

| 단계 | 적용 범위 | Before | After | 절감률 | 누적 절감 |
|------|----------|--------|-------|--------|----------|
| **현재** | Octostrator + Execute | 100% | 55% | 45% | **45%** ✅ |
| **Phase 2.1** | + Cognitive/Response | 100% | 45% | 55% | **55%** |
| **Phase 2.2** | + 7 Agents | 100% | 35% | 65% | **65%** |
| **Phase 2.3** | + Node Implementation | 100% | 30% | 70% | **70%** 🎯 |

**최종 목표**: Production 환경에서 **70% 비용 절감**

---

### 2. 비용 절감 금액 예측

**가정**: gpt-4o-mini 가격 ($0.15/1M input, $0.60/1M output)

#### 시나리오 1: 중소 규모 센터

**월 요청 수**: 10,000회

| 단계 | 월 비용 | 절감액 | 절감률 |
|------|---------|--------|--------|
| Before | $8.19 | - | - |
| Phase 2 (현재) | $4.50 | $3.69 | 45% |
| Phase 2.1 | $3.68 | $4.51 | 55% |
| Phase 2.2 | $2.87 | $5.32 | 65% |
| Phase 2.3 | $2.46 | $5.73 | 70% |

**연간 절감액**: $68.76

#### 시나리오 2: 중규모 센터 체인

**월 요청 수**: 100,000회

| 단계 | 월 비용 | 절감액 | 절감률 |
|------|---------|--------|--------|
| Before | $81.92 | - | - |
| Phase 2 (현재) | $45.06 | $36.86 | 45% |
| Phase 2.1 | $36.86 | $45.06 | 55% |
| Phase 2.2 | $28.67 | $53.25 | 65% |
| Phase 2.3 | $24.58 | $57.34 | 70% |

**연간 절감액**: $688.08

#### 시나리오 3: 대규모 프랜차이즈

**월 요청 수**: 1,000,000회

| 단계 | 월 비용 | 절감액 | 절감률 |
|------|---------|--------|--------|
| Before | $819.20 | - | - |
| Phase 2 (현재) | $450.56 | $368.64 | 45% |
| Phase 2.1 | $368.64 | $450.56 | 55% |
| Phase 2.2 | $286.72 | $532.48 | 65% |
| Phase 2.3 | $245.76 | $573.44 | 70% |

**연간 절감액**: $6,881.28

---

### 3. 환경별 최적화

#### Production 환경

**목표**: 비용 최적화

| 노드/Agent | Temperature | Max Tokens | 최적화 전략 |
|-----------|-------------|------------|-------------|
| Intent | 0.5 | 800 | 간결한 분류 |
| Planning | 0.2 | 2048 | 정확한 계획 |
| Aggregator | 0.5 | 3000 | 효율적 요약 |
| Chat Generator | 0.6 | 3000 | 자연스러운 응답 |
| Agents | 0.4-0.5 | 2048-4096 | 업무별 최적화 |

**예상 효과**: 70% 비용 절감

#### Development 환경

**목표**: 품질 우선

| 노드/Agent | Temperature | Max Tokens | 최적화 전략 |
|-----------|-------------|------------|-------------|
| Intent | 0.7 | 1024 | 다양한 의도 탐색 |
| Planning | 0.5 | 4096 | 상세한 계획 |
| Aggregator | 0.5 | 3072 | 풍부한 인사이트 |
| Chat Generator | 0.7 | 4096 | 자연스러운 대화 |
| Agents | 0.5-0.7 | 4096-6144 | 품질 우선 |

**예상 효과**: 다양성 및 품질 향상

#### Testing 환경

**목표**: 재현성 + 속도

| 노드/Agent | Temperature | Max Tokens | 최적화 전략 |
|-----------|-------------|------------|-------------|
| 모든 노드 | 0.0 | 512-2048 | 결정론적 테스트 |

**예상 효과**: 빠른 테스트, 재현 가능

---

## 🔧 구현 가이드

### 1. Supervisor Graph 적용 템플릿

```python
"""
[Graph Name] Layer Graph Builder

Phase 2 Updates:
- Context API 통합 (context_schema 추가)
- 환경별 LLM 설정 자동 적용
- 노드별 LLM 파라미터 최적화

Author: AI PT Manager Development Team
Date: 2025-11-06 (Phase 2 Context API)
Version: 2.0
"""

from typing import Optional
from langgraph.graph import StateGraph, START, END
from .nodes import node1, node2, node3

def build_[name]_graph(
    state_class=None,
    context: Optional["AppContext"] = None
):
    """
    Build the [name] layer workflow graph with Context API.

    Phase 2 Updates:
    - Context API 지원
    - 환경별 LLM 설정 자동 적용

    Args:
        state_class: State class (default: dict)
        context: AppContext instance (optional)
    """
    # State 기본값
    if state_class is None:
        state_class = dict

    # ⭐ Context 자동 생성
    if context is None:
        from backend.app.octostrator.contexts.app_context import AppContext
        from backend.app.config.llm_settings import get_llm_settings_from_env

        llm_settings = get_llm_settings_from_env()
        context = AppContext(
            user_id="default_user",
            session_id="default_session",
            llm_settings=llm_settings
        )

    # ⭐ Context API 활성화
    graph = StateGraph(
        state_class,
        context_schema=type(context)
    )

    # Add nodes
    graph.add_node("node1", node1)
    graph.add_node("node2", node2)
    # ...

    # Add edges
    graph.add_edge(START, "node1")
    # ...

    return graph.compile()
```

---

### 2. Agent 적용 템플릿

```python
"""
[Agent Name] Agent

Phase 2 Updates:
- Context API 지원
- 환경별 LLM 설정 자동 적용
"""

from typing import Optional, Dict, Any
from backend.app.octostrator.agents.base.base_agent import BaseAgent
from langgraph.graph import StateGraph, START, END
from langgraph.types import Runtime

class [Name]Agent(BaseAgent):
    """[Agent Name] Agent"""

    def __init__(self):
        super().__init__(
            agent_id="[agent_id]",
            agent_name="[Agent Name]",
            description="[설명]",
            enable_checkpoint=False
        )

    def build_graph(
        self,
        llm=None,
        context: Optional["AppContext"] = None  # ⭐ 추가
    ) -> StateGraph:
        """Build [agent_name] workflow with Context API"""

        # ⭐ Context 자동 생성
        if context is None:
            from backend.app.octostrator.contexts.app_context import AppContext
            from backend.app.config.llm_settings import get_llm_settings_from_env

            context = AppContext(
                user_id="default_user",
                session_id="default_session",
                llm_settings=get_llm_settings_from_env()
            )

        # ⭐ Context API 활성화
        graph = StateGraph(
            [AgentState],
            context_schema=type(context)
        )

        # Add nodes
        graph.add_node("process", self._process_node)
        # ...

        # Add edges
        graph.add_edge(START, "process")
        # ...

        return graph

    async def _process_node(
        self,
        state: [AgentState],
        runtime: Runtime  # ⭐ Runtime 자동 주입
    ) -> Dict[str, Any]:
        """Process node with Context API"""

        # Context에서 설정 추출
        context = runtime.context
        settings = context.llm_settings

        # LLM 생성
        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(
            model=settings.agent_model,
            temperature=settings.agent_temperature,
            max_tokens=settings.agent_max_tokens,
            api_key=...
        )

        # LLM 실행
        response = await llm.ainvoke(...)
        return {"result": response.content}

    async def process_task(
        self,
        task: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process task (abstract method implementation)"""
        # Delegate to graph
        result = await self.graph.ainvoke(task)
        return result
```

---

### 3. Node 구현 템플릿

```python
"""
[Layer Name] Layer Nodes

Phase 2 Updates:
- Runtime 파라미터 추가
- Context API로 LLM 설정 추출
"""

import logging
from typing import Dict, Any
from langgraph.types import Runtime
from backend.app.octostrator.contexts.app_context import AppContext
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage

logger = logging.getLogger(__name__)


async def [node_name]_node(
    state: Dict[str, Any],
    runtime: Runtime  # ⭐ Runtime 추가
) -> Dict[str, Any]:
    """[Node Name] Node with Context API"""
    try:
        # 1. Context에서 설정 추출
        context: AppContext = runtime.context
        settings = context.llm_settings

        # 2. LLM 생성 (노드별 설정)
        from backend.app.config.system import config as system_config
        llm = ChatOpenAI(
            model=settings.[node]_model,
            temperature=settings.[node]_temperature,
            max_tokens=settings.[node]_max_tokens,
            api_key=system_config.openai_api_key
        )

        # 3. 프롬프트 생성
        prompt = """[프롬프트 내용]"""

        # 4. LLM 실행
        logger.info(f"[{node_name}] Processing...")
        response = await llm.ainvoke([SystemMessage(content=prompt)])

        # 5. 결과 반환
        return {
            "result": response.content
        }

    except Exception as e:
        logger.error(f"[{node_name}] Error: {e}")
        return {"error": str(e)}
```

---

## ✅ 체크리스트

### Phase 2.1: Supervisor Graphs (P0)

- [ ] **Cognitive Graph**
  - [ ] `context` 파라미터 추가
  - [ ] Context 자동 생성 로직
  - [ ] `context_schema=type(context)` 추가
  - [ ] 테스트 (환경 변수 전환)

- [ ] **Response Graph**
  - [ ] `context` 파라미터 추가
  - [ ] Context 자동 생성 로직
  - [ ] `context_schema=type(context)` 추가
  - [ ] 테스트 (환경 변수 전환)

- [ ] **통합 테스트**
  - [ ] E2E 워크플로우 동작 확인
  - [ ] Production/Development/Testing 전환 테스트
  - [ ] 기존 기능 회귀 테스트

---

### Phase 2.2: Individual Agents (P1)

- [ ] **BaseAgent 확장**
  - [ ] `build_graph()` 시그니처 수정
  - [ ] 문서화 업데이트

- [ ] **Core Agents**
  - [ ] Assessor Agent
  - [ ] Program Designer Agent
  - [ ] Frontdesk Agent
  - [ ] 개별 테스트 (3개)

- [ ] **Support Agents**
  - [ ] Manager Agent
  - [ ] Owner Assistant Agent
  - [ ] 개별 테스트 (2개)

- [ ] **Extended Agents**
  - [ ] Trainer Education Agent
  - [ ] Marketing Agent
  - [ ] 개별 테스트 (2개)

- [ ] **통합 테스트**
  - [ ] 7개 에이전트 동작 확인
  - [ ] 환경 변수 기반 설정 확인
  - [ ] 성능 측정 (토큰 사용량)

---

### Phase 2.3: Node Implementation (P2, 선택)

- [ ] **Cognitive Nodes**
  - [ ] intent_understanding_node 구현
  - [ ] planning_node 구현
  - [ ] validator_node 구현
  - [ ] 프롬프트 작성 및 최적화

- [ ] **Response Nodes**
  - [ ] chat_generator_node 구현
  - [ ] graph_generator_node 구현
  - [ ] report_generator_node 구현
  - [ ] 프롬프트 작성 및 최적화

- [ ] **기능 테스트**
  - [ ] LLM 호출 확인
  - [ ] 응답 품질 평가
  - [ ] 에러 핸들링 테스트

---

## 📚 참고 자료

### 관련 문서

1. **Phase 2 완료 보고서**
   - [Phase 2 Context API Completion Report](../../manual/PHASE2_CONTEXT_API_COMPLETION_REPORT_251106.md)
   - 현재까지 완료된 작업 상세

2. **마이그레이션 계획서**
   - [Context API Migration to Hierarchical Supervisors](./CONTEXT_API_MIGRATION_TO_HIERARCHICAL_SUPERVISORS_251106.md)
   - 계층형 슈퍼바이저 전환 계획

3. **Implementation Guides**
   - [Context API Implementation Guide](./IMPLEMENTATION_GUIDE_CONTEXT_API.md)
   - [LangGraph Context Analysis](./LANGGRAPH_CONTEXT_ANALYSIS.md)

### 코드 참조

**적용 완료된 파일** (참고용):
- [octostrator_graph.py](../../backend/app/octostrator/supervisors/octostrator/octostrator_graph.py) ✅
- [execute_graph.py](../../backend/app/octostrator/supervisors/execute/execute_graph.py) ✅

**적용 대상 파일**:
- [cognitive_graph.py](../../backend/app/octostrator/supervisors/cognitive/cognitive_graph.py)
- [response_graph.py](../../backend/app/octostrator/supervisors/response/response_graph.py)
- [base_agent.py](../../backend/app/octostrator/agents/base/base_agent.py)

**Context 관련**:
- [app_context.py](../../backend/app/octostrator/contexts/app_context.py) (LLMSettings)
- [llm_settings.py](../../backend/app/config/llm_settings.py) (환경별 프리셋)

---

## 🎯 최종 목표

**3주 내 완료**:
1. ✅ **Phase 2.1 (30분)**: Supervisor Graphs 적용
2. ✅ **Phase 2.2 (5시간)**: 7개 Agent 적용
3. 🔶 **Phase 2.3 (4시간, 선택)**: 노드 구현

**성공 지표**:
- Production 환경에서 **70% 비용 절감** 달성
- 환경별 LLM 설정 자동 전환
- 모든 테스트 통과
- 기존 기능 100% 유지

**ROI**:
- 투자: 약 10시간 개발 시간
- 절감: 월 $200+ (중규모 기준)
- 회수 기간: 즉시 (비용 절감 효과 바로 발생)

---

**작성자**: Claude (Anthropic)
**검토 필요**: 개발팀, 아키텍처 팀
**승인 대기**: 확장 계획 승인 후 작업 시작

---

**END OF EXPANSION PLAN**
