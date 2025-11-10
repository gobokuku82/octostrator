# LangChain 1.0 & LangGraph 1.0 유용한 기능 가이드

**작성일**: 2025-01-03
**LangChain 버전**: 1.0.3
**LangGraph 버전**: 1.0.2

---

## 개요

LangChain 1.0과 LangGraph 1.0은 2025년 안정화 버전으로, **2.0 전까지 breaking changes 없음**을 보장합니다.
이 문서는 Octostrator 프로젝트에서 활용할 수 있는 유용한 기능들을 정리합니다.

---

## LangGraph 1.0 - 필수 유틸리티

### 1. **START, END 상수 (필수)**

**구형 문법 (Deprecated)**:
```python
from langgraph.graph import StateGraph, END

workflow = StateGraph(State)
workflow.set_entry_point("node_name")  # ❌ 구형
workflow.add_edge("node", END)
```

**신형 문법 (LangGraph 1.0)**:
```python
from langgraph.graph import StateGraph, START, END

workflow = StateGraph(State)
workflow.add_edge(START, "node_name")  # ✅ 신형
workflow.add_edge("node", END)
```

**변경 사항**:
- `set_entry_point()` → `add_edge(START, "node_name")`
- START는 명시적인 시작 노드를 나타냄
- 더 직관적이고 일관된 API

---

### 2. **ToolNode - 툴 실행 노드**

**용도**: ReAct 패턴에서 툴 실행을 자동화

```python
from langgraph.prebuilt import ToolNode

# 툴 정의
tools = [search_tool, calculator_tool]

# ToolNode 생성
tool_node = ToolNode(tools)

# Graph에 추가
workflow.add_node("tools", tool_node)
```

**장점**:
- ✅ 병렬 툴 실행 자동 처리
- ✅ 에러 핸들링 내장
- ✅ 툴 호출 결과를 자동으로 State에 추가

**Octostrator 적용 시점**: Phase 2 (Search Agent)

---

### 3. **tools_condition - 조건부 라우팅 헬퍼**

**용도**: ReAct 패턴의 표준 조건부 로직

```python
from langgraph.prebuilt import tools_condition

# 조건부 엣지: 툴 호출이 있으면 tools 노드로, 없으면 종료
workflow.add_conditional_edges(
    "agent",
    tools_condition,
    {
        "tools": "tools",  # 툴 호출 시
        END: END           # 종료 시
    }
)
```

**동작 원리**:
- 마지막 AIMessage에 tool_calls가 있으면 → "tools" 반환
- 없으면 → END 반환

**Octostrator 적용 시점**: Phase 2 (Search Agent)

---

### 4. **create_react_agent - ReAct 에이전트 빌더**

**용도**: ReAct 패턴 에이전트를 한 줄로 생성

```python
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI

agent = create_react_agent(
    model=ChatOpenAI(model="gpt-4o-mini"),
    tools=[search_tool],
    state_modifier="You are a helpful assistant"  # 시스템 프롬프트
)

# 실행
result = await agent.ainvoke({"messages": [HumanMessage(content="Search for X")]})
```

**장점**:
- ✅ 노드, 엣지, 조건부 로직 자동 생성
- ✅ ToolNode + tools_condition 내장
- ✅ 빠른 프로토타이핑

**주의사항**:
- ⚠️ 커스터마이징이 제한적
- ⚠️ Octostrator는 커스텀 Graph를 직접 만들어야 함 (Supervisor 패턴)

**Octostrator 적용**: Phase 2에서 개별 Agent 구현 시 참고용

---

### 5. **Command - 동적 라우팅 (LangGraph 1.0 신기능)**

**용도**: Edgeless Graph - 노드에서 다음 노드를 동적으로 결정

```python
from langgraph.types import Command

async def supervisor_node(state: State):
    # 라우팅 결정
    next_node = decide_next_agent(state)

    # State 업데이트 + 라우팅을 한 번에
    return Command(
        update={"messages": [response]},
        goto=next_node  # "search" or "rag" or "base"
    )

# 노드 추가 시 ends 지정 필수
workflow.add_node("supervisor", supervisor_node, ends=["search", "rag", "base"])
```

**장점**:
- ✅ add_conditional_edges 불필요
- ✅ 노드 내부에서 State 업데이트 + 라우팅을 한 번에 처리
- ✅ 복잡한 조건부 로직을 노드 내부로 캡슐화

**Octostrator 적용 시점**: Phase 2 (Supervisor 라우팅 로직)

**예시 (Octostrator Supervisor)**:
```python
async def supervisor_node(state: SupervisorState, context: AppContext):
    messages = state["messages"]
    response = await context.llm.ainvoke(messages)

    # 라우팅 결정 (LLM 응답 분석)
    if "search" in response.content.lower():
        next_agent = "search"
    elif "document" in response.content.lower():
        next_agent = "rag"
    else:
        next_agent = END

    return Command(
        update={"messages": [response]},
        goto=next_agent
    )
```

---

### 6. **Node-level Caching (LangGraph 1.0 신기능)**

**용도**: 개별 노드의 결과를 캐싱하여 중복 실행 방지

```python
workflow.add_node(
    "expensive_node",
    expensive_function,
    cache=True  # 캐싱 활성화
)
```

**장점**:
- ✅ 동일한 입력에 대해 재실행 방지
- ✅ 비용 절감 (LLM 호출 감소)
- ✅ 응답 속도 향상

**Octostrator 적용 시점**: Phase 3+ (RAG Agent - 문서 검색 결과 캐싱)

---

### 7. **Cross-thread Memory (LangGraph 1.0 신기능)**

**용도**: 여러 세션(thread) 간 정보 공유

```python
# Thread A에서 저장
await graph.ainvoke(
    {"messages": [...]},
    config={
        "configurable": {
            "thread_id": "thread-a",
            "shared_memory": {"user_preferences": {...}}
        }
    }
)

# Thread B에서 접근
await graph.ainvoke(
    {"messages": [...]},
    config={
        "configurable": {
            "thread_id": "thread-b",
            "shared_memory": {"user_preferences": {...}}  # 동일 데이터 접근
        }
    }
)
```

**Octostrator 적용 시점**: Phase 5+ (사용자별 설정 공유)

---

## LangChain 1.0 - 유용한 유틸리티

### 1. **create_agent - 표준 에이전트 빌더**

**용도**: LangChain의 고수준 에이전트 API

```python
from langchain.agents import create_agent

agent = create_agent(
    model="openai:gpt-4o-mini",
    tools=[get_weather],
    system_prompt="Help the user by fetching the weather in their city."
)
```

**Octostrator 적용**:
- ⚠️ LangGraph를 사용하므로 직접 사용 X
- 개념만 참고 (Supervisor 패턴 설계 시)

---

### 2. **Middleware 시스템 (LangChain 1.0 신기능)**

**용도**: 에이전트 실행 중 Hook 삽입

#### 2.1 **HumanInTheLoopMiddleware**
```python
from langchain.agents.middleware import HumanInTheLoopMiddleware

middleware = HumanInTheLoopMiddleware(
    approval_required=["delete_file", "send_email"]  # 승인 필요 툴
)

agent = create_agent(
    model="openai:gpt-4o-mini",
    tools=[delete_file, send_email],
    middleware=[middleware]
)
```

**Octostrator 적용**: Phase 6 (위험한 작업 승인 로직)

#### 2.2 **PIIMiddleware**
```python
from langchain.agents.middleware import PIIMiddleware

middleware = PIIMiddleware(
    patterns={
        "email": r"[\w\.-]+@[\w\.-]+\.\w+",
        "phone": r"\d{3}-\d{3,4}-\d{4}"
    },
    redaction="***"
)
```

**Octostrator 적용**: Phase 3+ (개인정보 보호)

#### 2.3 **SummarizationMiddleware**
```python
from langchain.agents.middleware import SummarizationMiddleware

middleware = SummarizationMiddleware(
    max_tokens=2000,
    summarize_after=10  # 10개 메시지마다 요약
)
```

**Octostrator 적용**: Phase 5+ (긴 대화 관리)

**주의**:
- ⚠️ Middleware는 LangChain의 create_agent에서만 동작
- ⚠️ LangGraph에서는 직접 구현 필요
- ⚠️ 개념만 참고하여 노드 내부에서 구현

---

### 3. **Structured Output (LangChain 1.0)**

**용도**: Pydantic 모델로 구조화된 출력 강제

```python
from langchain.agents.structured_output import ToolStrategy
from pydantic import BaseModel

class WeatherReport(BaseModel):
    temperature: float
    condition: str
    humidity: int

agent = create_agent(
    model="openai:gpt-4o-mini",
    tools=[weather_tool],
    response_format=ToolStrategy(WeatherReport)
)

# 응답이 자동으로 WeatherReport 인스턴스로 변환됨
```

**LangGraph에서 사용 (with_structured_output)**:
```python
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

class RouterDecision(BaseModel):
    next_agent: str  # "search" | "rag" | "base"
    confidence: float

llm = ChatOpenAI(model="gpt-4o-mini")
structured_llm = llm.with_structured_output(RouterDecision)

# Supervisor 노드에서 사용
async def supervisor_node(state: State):
    decision = await structured_llm.ainvoke(state["messages"])
    # decision.next_agent, decision.confidence 사용
```

**Octostrator 적용 시점**: Phase 2 (Supervisor 라우팅 결정)

---

### 4. **Standard Content Blocks (LangChain 1.0)**

**용도**: 모든 LLM 제공자에서 동일한 메시지 구조

```python
from langchain_core.messages import HumanMessage, AIMessage

# OpenAI, Anthropic, Google 등 모든 제공자에서 동일하게 동작
message = HumanMessage(
    content=[
        {"type": "text", "text": "Describe this image"},
        {"type": "image_url", "image_url": "https://..."}
    ]
)
```

**지원 타입**:
- `text`: 텍스트
- `image_url`: 이미지
- `tool_call`: 툴 호출
- `tool_result`: 툴 결과

**Octostrator 적용**: Phase 2+ (멀티모달 지원 시)

---

## Octostrator 프로젝트 적용 계획

### Phase 2: Search Agent

**사용할 기능**:
1. ✅ **START, END** - 이미 적용 완료
2. ✅ **ToolNode** - 검색 툴 실행
3. ✅ **tools_condition** - 툴 호출 여부 판단
4. ✅ **Command** - Supervisor 라우팅 로직
5. ✅ **with_structured_output** - 라우팅 결정 구조화

**구현 예시**:
```python
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.types import Command

# Supervisor에서 Command로 라우팅
async def supervisor_node(state: State, context: AppContext):
    decision = await structured_llm.ainvoke(state["messages"])
    return Command(
        update={"messages": [...]},
        goto=decision.next_agent
    )

# Search Agent에서 ToolNode 사용
workflow.add_node("search_agent", search_agent_node)
workflow.add_node("search_tools", ToolNode([tavily_search]))
workflow.add_conditional_edges("search_agent", tools_condition)
```

---

### Phase 3+: RAG Agent

**사용할 기능**:
1. ✅ **Node-level Caching** - 문서 검색 결과 캐싱
2. ✅ **PIIMiddleware 개념** - 개인정보 마스킹 (직접 구현)

---

### Phase 5: Checkpointer

**사용할 기능**:
1. ✅ **AsyncPostgresSaver** - 이미 계획됨
2. ✅ **Cross-thread Memory** - 사용자 설정 공유

---

### Phase 6: 추가 Agent

**사용할 기능**:
1. ✅ **HumanInTheLoopMiddleware 개념** - 위험한 작업 승인 (직접 구현)
2. ✅ **SummarizationMiddleware 개념** - 긴 대화 요약 (직접 구현)

---

## 코드 마이그레이션 체크리스트

### ✅ 완료된 항목
- [x] `set_entry_point()` → `add_edge(START, "node_name")`
- [x] `from langgraph.graph import START, END` import 추가

### ⏸️ Phase 2에서 추가할 항목
- [ ] `ToolNode` 추가
- [ ] `tools_condition` 추가
- [ ] `Command` 사용하여 동적 라우팅
- [ ] `with_structured_output` 사용하여 라우팅 결정

### ⏸️ Phase 3+에서 추가할 항목
- [ ] Node-level caching
- [ ] 개인정보 마스킹 로직
- [ ] Cross-thread memory

---

## 참고 자료

- [LangGraph 1.0 Release Notes](https://blog.langchain.com/langchain-langgraph-1dot0/)
- [Command 공식 문서](https://langchain-ai.github.io/langgraphjs/how-tos/command/)
- [LangGraph Prebuilt Components](https://python.langchain.com/docs/langgraph/reference/prebuilt/)
- [LangChain 1.0 What's New](https://docs.langchain.com/oss/python/releases/langchain-v1)

---

## 결론

LangGraph 1.0과 LangChain 1.0은 **프로덕션 환경**을 위한 안정적인 API를 제공합니다.

**Octostrator에서 우선 적용할 기능**:
1. ✅ **START, END** (완료)
2. 🔜 **Command** (Phase 2 - Supervisor 라우팅)
3. 🔜 **ToolNode + tools_condition** (Phase 2 - Search Agent)
4. 🔜 **with_structured_output** (Phase 2 - 라우팅 결정)

**나머지 기능**은 필요 시점에 단계적으로 도입합니다.
