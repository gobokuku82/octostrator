# LangGraph Context API 분석 (2025년 최신)

**작성일**: 2025-11-05
**LangGraph 버전**: v1.0 (Context API 도입)
**목적**: LLM 설정(max_tokens, temperature 등)을 노드별로 관리하는 최선의 방법 분석

---

## 📋 Executive Summary

LangGraph v1.0에서는 **Context API**를 도입하여 기존의 `config["configurable"]` 패턴을 대체합니다. 이를 통해:

- ✅ **타입 안정성**: Pydantic 스키마로 컨텍스트 검증
- ✅ **개발자 경험**: 중첩된 딕셔너리 제거, 깔끔한 `runtime.context` 접근
- ✅ **노드별 설정**: LLM 파라미터를 노드별로 동적 구성 가능
- ✅ **하위 호환성**: 기존 코드 그대로 작동 (점진적 마이그레이션)

**핵심 질문에 대한 답변:**
> "프롬프트마다 max_tokens/temperature 설정을 코드에 하드코딩하는가, 아니면 Context API를 활용하는가?"

**답변**: **Context API + ConfigurableField 조합**을 사용하는 것이 LangGraph의 최신 권장사항입니다.

---

## 🔄 기존 방식 vs 새로운 Context API

### 1. 기존 방식 (LangGraph 0.6 이전)

#### 방법 1-A: 하드코딩 (비권장)
```python
# cognitive_nodes.py
async def planning_node(state, llm):
    # LLM 설정 하드코딩
    llm_with_settings = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.3,      # 하드코딩
        max_tokens=2048       # 하드코딩
    )

    structured_llm = llm_with_settings.with_structured_output(Plan)
    result = await structured_llm.ainvoke([...])
```

**문제점**:
- ❌ 설정 변경 시 코드 수정 필요
- ❌ 노드마다 설정이 흩어져 있음
- ❌ 테스트/프로덕션 환경 분리 어려움

#### 방법 1-B: config["configurable"] (복잡함)
```python
# main_graph.py
async def planning_node_wrapper(state, config):
    # 깊은 중첩 구조
    max_tokens = config["configurable"].get("planning_max_tokens", 2048)
    temperature = config["configurable"].get("planning_temperature", 0.3)

    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=temperature,
        max_tokens=max_tokens
    )
    ...

# 사용 시
graph.ainvoke(
    initial_state,
    config={
        "configurable": {
            "planning_max_tokens": 1024,
            "planning_temperature": 0.5
        }
    }
)
```

**문제점**:
- ❌ 중첩된 딕셔너리 구조 (`.get().get()...`)
- ❌ 타입 검증 없음
- ❌ IDE 자동완성 불가
- ❌ 오타 발견 어려움

---

### 2. 새로운 방식 (LangGraph v1.0 Context API)

#### 방법 2-A: Context Schema 정의

```python
# contexts/app_context.py
from pydantic import BaseModel, Field
from typing import Optional

class LLMSettings(BaseModel):
    """노드별 LLM 설정"""

    # Planning Node용
    planning_model: str = "gpt-4o-mini"
    planning_temperature: float = Field(default=0.3, ge=0.0, le=2.0)
    planning_max_tokens: int = Field(default=2048, ge=1, le=16384)

    # Intent Node용
    intent_model: str = "gpt-4o-mini"
    intent_temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    intent_max_tokens: int = Field(default=1024, ge=1, le=16384)

    # Aggregator Node용
    aggregator_model: str = "gpt-4o-mini"
    aggregator_temperature: float = Field(default=0.5, ge=0.0, le=2.0)
    aggregator_max_tokens: int = Field(default=3072, ge=1, le=16384)

    # Chat Generator용
    chat_model: str = "gpt-4o-mini"
    chat_temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    chat_max_tokens: int = Field(default=4096, ge=1, le=16384)


class AppContext(BaseModel):
    """Application 런타임 Context"""

    # 사용자 정보
    user_id: str
    session_id: str

    # LLM 설정 (노드별 세분화)
    llm_settings: LLMSettings = Field(default_factory=LLMSettings)

    # DB 연결
    db_conn: Optional[str] = None

    # 디버그 모드
    debug: bool = False
```

#### 방법 2-B: 노드에서 Context 사용

```python
# nodes/cognitive_nodes.py
from langchain_core.runnables import Runtime
from langchain_openai import ChatOpenAI

async def planning_node(state: SupervisorState, runtime: Runtime) -> Dict:
    """Planning 노드 - Context API 사용"""

    # Runtime Context에서 LLM 설정 가져오기
    llm_settings = runtime.context.llm_settings

    # 노드별 맞춤 LLM 생성
    llm = ChatOpenAI(
        model=llm_settings.planning_model,
        temperature=llm_settings.planning_temperature,
        max_tokens=llm_settings.planning_max_tokens
    )

    # Structured Output 사용
    structured_llm = llm.with_structured_output(Plan)

    plan_result = await structured_llm.ainvoke([
        planning_prompt,
        HumanMessage(content=f"User Intent:\n{state.user_intent}")
    ])

    return {"plan": plan_as_dicts}


async def intent_understanding_node(state: SupervisorState, runtime: Runtime) -> Dict:
    """Intent 노드 - 다른 설정 사용"""

    llm_settings = runtime.context.llm_settings

    # Intent는 더 높은 temperature 사용
    llm = ChatOpenAI(
        model=llm_settings.intent_model,
        temperature=llm_settings.intent_temperature,  # 0.7
        max_tokens=llm_settings.intent_max_tokens      # 1024
    )

    response = await llm.ainvoke([...])
    ...
```

#### 방법 2-C: Graph 빌드 시 Context Schema 등록

```python
# graphs/main_graph.py
from backend.app.octostrator.contexts.app_context import AppContext, LLMSettings

def build_supervisor_graph(
    context_schema=AppContext,  # ⭐ Context Schema 등록
    checkpointer: Optional[AsyncPostgresSaver] = None
):
    """Supervisor Graph 생성 (Context API 사용)"""

    # StateGraph with Context Schema
    workflow = StateGraph(
        SupervisorState,
        context_schema=AppContext  # ⭐ Context Schema 지정
    )

    # 노드 추가 (Runtime 객체 자동 전달)
    workflow.add_node("intent", intent_understanding_node)
    workflow.add_node("planning", planning_node)
    workflow.add_node("aggregator", aggregator_node)

    # ... 엣지 정의 ...

    return workflow.compile(checkpointer=checkpointer)
```

#### 방법 2-D: Graph 실행 시 Context 전달

```python
# API 또는 테스트에서 호출
from backend.app.octostrator.contexts.app_context import AppContext, LLMSettings

async def process_user_request(user_message: str, session_id: str):
    # Context 생성 (환경별 설정 가능)
    context = AppContext(
        user_id="user_123",
        session_id=session_id,
        llm_settings=LLMSettings(
            # 프로덕션 환경: 보수적 설정
            planning_temperature=0.3,
            planning_max_tokens=2048,

            # Intent는 창의적으로
            intent_temperature=0.7,
            intent_max_tokens=1024,

            # 비용 절감: Chat은 더 짧게
            chat_max_tokens=3000
        ),
        debug=False
    )

    # Graph 빌드
    graph = build_supervisor_graph(checkpointer=checkpointer)

    # Context와 함께 실행 (새 API)
    result = await graph.ainvoke(
        {"messages": [HumanMessage(content=user_message)]},
        config={"thread_id": session_id},
        context=context  # ⭐ Context 전달
    )

    return result
```

---

## 🎯 노드별 LLM 설정 권장 전략

### Phase 1: 현재 프로젝트 (5개 에이전트)

| 노드 | Model | Temperature | Max Tokens | 이유 |
|------|-------|-------------|------------|------|
| **intent** | gpt-4o-mini | 0.7 | 1024 | 의도 파악은 창의적 해석 필요 |
| **planning** | gpt-4o-mini | 0.3 | 2048 | 계획은 정확성 우선 |
| **executor** | (Agent별 설정) | - | - | Agent 내부에서 결정 |
| **aggregator** | gpt-4o-mini | 0.5 | 3072 | 결과 종합은 균형 필요 |
| **chat_generator** | gpt-4o-mini | 0.7 | 4096 | 자연스러운 대화 생성 |
| **graph_generator** | gpt-4o-mini | 0.2 | 2048 | JSON 정확성 우선 |
| **report_generator** | gpt-4o-mini | 0.5 | 8192 | 긴 보고서 생성 |

### Phase 2: 환경별 분리

```python
# config/llm_settings.py
def get_llm_settings(env: str = "production") -> LLMSettings:
    """환경별 LLM 설정"""

    if env == "production":
        return LLMSettings(
            # 프로덕션: 비용 절감 + 안정성
            planning_max_tokens=2048,
            chat_max_tokens=3000,
            planning_temperature=0.3
        )

    elif env == "development":
        return LLMSettings(
            # 개발: 더 긴 출력 허용
            planning_max_tokens=4096,
            chat_max_tokens=6000,
            planning_temperature=0.5  # 다양한 시나리오 테스트
        )

    elif env == "testing":
        return LLMSettings(
            # 테스트: 짧고 빠르게
            planning_max_tokens=512,
            chat_max_tokens=1024,
            planning_temperature=0.0  # 결정론적 출력
        )
```

---

## 🔧 ConfigurableField를 사용한 고급 패턴

### 패턴 1: 런타임 모델 교체

```python
from langchain_core.runnables import ConfigurableField

# LLM을 런타임에 교체 가능하게 설정
base_llm = ChatOpenAI(temperature=0.7).configurable_fields(
    temperature=ConfigurableField(
        id="llm_temperature",
        name="LLM Temperature",
        description="The temperature of the LLM",
    ),
    max_tokens=ConfigurableField(
        id="max_tokens",
        name="Max Tokens",
        description="Maximum tokens to generate",
    )
)

# 노드에서 사용
async def my_node(state, runtime: Runtime):
    # Context에서 설정 가져오기
    llm = runtime.context.base_llm.configurable(
        llm_temperature=0.3,
        max_tokens=2048
    )

    response = await llm.ainvoke([...])
```

### 패턴 2: 모델 선택 (gpt-4 vs gpt-4o-mini)

```python
from langchain_core.runnables import ConfigurableField
from langchain_openai import ChatOpenAI

# 모델을 런타임에 교체 가능하게
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0).configurable_alternatives(
    ConfigurableField(id="llm_model"),
    default_key="mini",
    expensive=ChatOpenAI(model="gpt-4", temperature=0),
)

# 사용
cheap_response = llm.invoke("simple question")  # gpt-4o-mini
expensive_response = llm.with_config(
    configurable={"llm_model": "expensive"}
).invoke("complex question")  # gpt-4
```

---

## 🏗️ 프로젝트 적용 계획

### Step 1: AppContext 확장 (contexts/app_context.py)

```python
@dataclass
class AppContext:
    """Application 런타임 Context (확장)"""

    # 기존 필드
    user_id: str
    session_id: str

    # ⭐ 추가: LLM 설정
    llm_settings: LLMSettings = field(default_factory=LLMSettings)

    # ⭐ 추가: 환경 정보
    environment: str = "production"  # production, development, testing

    # DB 연결
    db_conn: Optional[str] = None

    # 디버그 모드
    debug: bool = False
```

### Step 2: 노드 함수 시그니처 변경

```python
# Before (현재)
async def planning_node(state: SupervisorState, llm: ChatOpenAI) -> Dict:
    ...

# After (Context API)
async def planning_node(state: SupervisorState, runtime: Runtime) -> Dict:
    llm_settings = runtime.context.llm_settings
    llm = ChatOpenAI(
        model=llm_settings.planning_model,
        temperature=llm_settings.planning_temperature,
        max_tokens=llm_settings.planning_max_tokens
    )
    ...
```

### Step 3: Graph 빌드 시 Context Schema 등록

```python
# graphs/main_graph.py
workflow = StateGraph(
    SupervisorState,
    context_schema=AppContext  # ⭐ Context Schema 등록
)
```

### Step 4: 호출 시 Context 전달

```python
# API에서 호출
context = AppContext(
    user_id="user_123",
    session_id=session_id,
    llm_settings=get_llm_settings(env="production")
)

result = await graph.ainvoke(
    initial_state,
    config={"thread_id": session_id},
    context=context  # ⭐ Context 전달
)
```

---

## ⚠️ 주의사항 및 제한사항

### 1. 현재 LangGraph 버전 확인 필요
- Context API는 **LangGraph v1.0+**에서만 사용 가능
- 현재 프로젝트가 v0.6 이하라면 점진적 업그레이드 필요

### 2. 하위 호환성
- 기존 `config["configurable"]` 패턴도 계속 작동
- 점진적으로 마이그레이션 가능

### 3. Subgraph에서 Context 전파 이슈
- 초기 v1.0에서 subgraph로 context 전파 안되는 버그 있었음
- 최신 버전에서 해결됨 (Issue #5700 참조)

### 4. ConfigurableField vs Context
- **ConfigurableField**: 런타임에 모델/설정 교체
- **Context**: 불변 런타임 정보 전달
- 두 가지를 **조합**해서 사용하는 것이 Best Practice

---

## 📚 참고 자료

### 공식 문서
- [LangGraph Context API Proposal (Issue #5023)](https://github.com/langchain-ai/langgraph/issues/5023)
- [LangGraph v1.0 Release Notes](https://blog.langchain.com/langchain-langgraph-1dot0/)
- [Context Engineering for Agents](https://blog.langchain.com/context-engineering-for-agents/)

### 관련 Discussions
- [Best Practice for Initializing LLM and Config (#4405)](https://github.com/langchain-ai/langgraph/discussions/4405)
- [Runtime Context Subgraph Issue (#5700)](https://github.com/langchain-ai/langgraph/issues/5700)

### 유용한 가이드
- [How to Configure Runtime Chain Internals](https://python.langchain.com/docs/how_to/configure/)
- [LangGraph Configuration Guide](https://www.baihezi.com/mirrors/langgraph/how-tos/configuration/)

---

## 🎯 결론 및 권장사항

### 질문에 대한 최종 답변

**Q**: "프롬프트마다 max_tokens/temperature를 코드에 하드코딩하는가, Context API를 활용하는가?"

**A**: **Context API + LLMSettings 스키마**를 사용하는 것이 최선입니다.

### 이유:

1. ✅ **타입 안정성**: Pydantic으로 검증
2. ✅ **환경 분리**: production/dev/test 설정 관리 용이
3. ✅ **중앙 관리**: 모든 LLM 설정이 `contexts/app_context.py`에 집중
4. ✅ **테스트 용이**: 설정만 바꿔서 다양한 시나리오 테스트
5. ✅ **비용 최적화**: 노드별로 적절한 max_tokens 설정

### 다음 단계 (Phase 2 프롬프트 최적화와 함께):

1. **Day 1**: AppContext 확장 + LLMSettings 정의
2. **Day 2**: 노드 함수들 Runtime 객체 사용하도록 변경
3. **Day 3**: 환경별 설정 파일 생성 (config/llm_settings.py)
4. **Day 4**: 테스트 + 문서화

---

**작성**: Claude (Anthropic)
**검토 필요**: LangGraph 버전 확인 후 적용
