# LangGraph 0.6~1.0 & LangChain 1.0 신규 기능 종합 보고서

**작성일**: 2025-11-17
**버전**: LangGraph 1.0 (2025년 10월 정식 출시), LangChain 1.0
**목적**: LangGraph와 LangChain 생태계의 최신 기능 및 변경사항 종합 정리

---

## 📋 목차

1. [LangGraph 1.0 핵심 변경사항](#1-langgraph-10-핵심-변경사항)
2. [LangChain 1.0 핵심 변경사항](#2-langchain-10-핵심-변경사항)
3. [Command API](#3-command-api)
4. [Context API (Runtime)](#4-context-api-runtime)
5. [Send API](#5-send-api)
6. [interrupt() Function](#6-interrupt-function)
7. [Store API](#7-store-api)
8. [Streaming Modes](#8-streaming-modes)
9. [Functional API](#9-functional-api)
10. [Node Caching](#10-node-caching)
11. [Deferred Nodes](#11-deferred-nodes)
12. [Middleware System](#12-middleware-system)
13. [Content Blocks](#13-content-blocks)
14. [Overwrite & UntrackedValue](#14-overwrite--untrackedvalue)
15. [Multiple Interrupt Resume](#15-multiple-interrupt-resume)
16. [Checkpointer 3.0](#16-checkpointer-30)
17. [기타 개선사항](#17-기타-개선사항)
18. [마이그레이션 가이드](#18-마이그레이션-가이드)

---

## 1. LangGraph 1.0 핵심 변경사항

### 1.1 개요

LangGraph 1.0은 프로덕션 준비가 완료된 에이전트 프레임워크 공간에서 첫 번째 안정적인 주요 릴리스로, Uber, LinkedIn, Klarna와 같은 기업들이 이미 프로덕션에서 사용하고 있습니다.

### 1.2 주요 특징

| 특징 | 설명 |
|------|------|
| **Breaking Changes 없음** | 0.6.6에서 1.0으로 업그레이드 시 호환성 유지 |
| **Durable Execution** | 체크포인팅을 통한 내구성 있는 실행 |
| **Built-in Runtime** | 단기 메모리, HITL 패턴, 스트리밍 기본 제공 |
| **Python 3.10+** | Python 3.9 지원 중단, 3.14 지원 추가 |
| **Production Ready** | 대규모 기업 검증 완료 |

### 1.3 Deprecated 기능

LangGraph의 create_react_agent 사전 빌드가 LangChain의 create_agent를 위해 deprecated되었으며, 더 간단한 인터페이스와 미들웨어를 통한 더 큰 커스터마이징 가능성을 제공합니다.

---

## 2. LangChain 1.0 핵심 변경사항

### 2.1 개요

LangChain 1.0은 3년간의 피드백을 바탕으로 코어 에이전트 루프에 집중하고, 미들웨어 개념을 통한 유연성을 제공하며, 2.0까지 breaking changes가 없을 것을 약속합니다.

### 2.2 주요 변경사항

| 변경사항 | 설명 |
|---------|------|
| **단일 에이전트 추상화** | `create_agent`로 통합 (LCEL 체인 제거) |
| **LangGraph 기반** | LangGraph 런타임 위에 구축 |
| **Package 축소** | 핵심 기능만 남기고 legacy는 `langchain-classic`으로 이동 |
| **Content Blocks** | 표준화된 메시지 구조 (.content_blocks 속성) |
| **Middleware 시스템** | 컨텍스트 엔지니어링을 위한 훅 제공 |

### 2.3 철학적 변화

LCEL (LangChain Expression Language)의 파이프("|") 연산자가 제거되었으며, 많은 "|" 연산자가 포함된 앱은 더 이상 존재하지 않습니다.

---

## 3. Command API

### 3.1 기능

**상태 업데이트 + 라우팅을 한 번에 처리**하는 API로, 멀티 에이전트 핸드오프의 핵심입니다.

### 3.2 주요 메서드

```python
# 상태 업데이트만
Command(update={"todos": [...]})

# 특정 노드로 이동
Command(goto="node_name")

# 상태 업데이트 + 노드 이동
Command(update={"todos": [...]}, goto="next_node")

# Subgraph에서 부모로 이동
Command.PARENT

# Interrupt 이후 재개
Command(resume=value)
```

### 3.3 사용 사례

- Subgraph 간 라우팅
- 조건부 엣지 없이 동적 라우팅
- 멀티 에이전트 시스템에서 에이전트 간 핸드오프

---

## 4. Context API (Runtime)

### 4.1 기능

LangGraph의 런타임 컨텍스트를 더 직관적으로 접근할 수 있게 하며, 기존의 config["configurable"] 중첩 구조를 개선했습니다.

### 4.2 주요 객체

```python
# Before (기존)
def node(state, config):
    user_id = config["configurable"]["user_id"]
    thread_id = config["configurable"]["thread_id"]

# After (신규)
def node(state, runtime):
    user_id = runtime.context.user_id
    thread_id = runtime.config.thread_id
    store = runtime.store  # Store API 접근
```

### 4.3 특징

- **불변 컨텍스트**: 실행 중 변경되지 않는 컨텍스트 전달
- **직관적 접근**: 점 표기법으로 간결하게 접근
- **Store 통합**: Store API와 자연스럽게 통합

---

## 5. Send API

### 5.1 기능

**Map-Reduce 워크플로우 구현**을 위한 API로, 동적 병렬 실행을 지원합니다.

### 5.2 사용 예시

```python
def distribute_todos(state):
    # TODO 항목마다 병렬 실행
    return [
        Send("process_todo", {"todo": todo})
        for todo in state["todos"]
    ]
```

### 5.3 특징

- 노드 수를 미리 알 수 없을 때 사용
- 각 Send는 개별 노드 인스턴스로 실행
- 모든 결과 수집 후 다음 단계 진행

---

## 6. interrupt() Function

### 6.1 기능

Human-in-the-Loop 구현의 핵심으로, NodeInterrupt를 대체하는 권장 방법입니다.

### 6.2 주요 특징

```python
# 동적 조건부 중단
def node(state):
    if needs_approval:
        user_input = interrupt("Please approve this action")
    # 계속 실행
```

### 6.3 Interrupt 관련 개념

| 개념 | 설명 |
|------|------|
| **interrupt()** | 함수 호출 방식 (권장) |
| **NodeInterrupt** | 예외 방식 (비권장, deprecated) |
| **Static Breakpoints** | `interrupt_before`, `interrupt_after` |
| **Dynamic Breakpoints** | 코드 내 조건부 `interrupt()` |
| **__interrupt__ 이벤트** | 스트림에서 중단 감지 |

### 6.4 LangGraph v0.4+ 개선사항

Interrupt는 이제 .invoke() 및 "values" 스트림 모드에서 제대로 전파되며, 상태에 interrupt가 포함되어 있는지 확인할 수 있는 isInterrupted() 메서드가 추가되었습니다.

---

## 7. Store API

### 7.1 기능

**장기 메모리 (Long-term Memory) 구현**을 위한 API로, Thread를 넘어서 영속적으로 데이터를 저장합니다.

### 7.2 주요 컴포넌트

| 컴포넌트 | 설명 |
|----------|------|
| `InMemoryStore` | 메모리 기반 (개발용) |
| `RedisStore` | Redis 기반 + 벡터 검색 |
| `MongoDBStore` | MongoDB 기반 + 벡터 검색 |

### 7.3 주요 메서드

```python
# 데이터 저장
store.put(namespace, key, value)

# 데이터 조회
store.get(namespace, key)

# 벡터 검색
store.search(namespace, query)

# 데이터 삭제
store.delete(namespace, key)
```

### 7.4 네임스페이스

- 계층적 구조: `(user_id, "memories")` 또는 `(org_id, user_id, "preferences")`
- 데이터 격리 및 조직화

---

## 8. Streaming Modes

### 8.1 기능

**실시간 진행 상황 스트리밍**을 지원하며, 다양한 수준의 스트리밍을 제공합니다.

### 8.2 Streaming Modes

| 모드 | 스트리밍 대상 | 사용 사례 |
|------|--------------|----------|
| `values` | 각 노드 실행 후 전체 상태 | 전체 상태 모니터링 |
| `updates` | 각 노드의 상태 업데이트만 | 변경 사항만 추적 |
| `messages` | 메시지만 (LLM 응답 등) | 채팅 인터페이스 |
| `events` | 모든 이벤트 (LLM 토큰 포함) | 토큰 단위 스트리밍 |
| `debug` | 디버깅 정보 | 개발 중 |

### 8.3 주요 메서드

```python
# 스트리밍 실행
graph.stream(input, stream_mode="values")

# 비동기 스트리밍
graph.astream(input, stream_mode="events")

# 이벤트 스트리밍 (토큰 단위)
graph.astream_events(input)
```

---

## 9. Functional API

### 9.1 기능

**함수형 프로그래밍 스타일**로 그래프를 정의하는 새로운 API입니다.

### 9.2 특징

- 데코레이터 기반
- 암시적 그래프 구성
- 더 간결한 코드

### 9.3 비교

| 특징 | Graph API | Functional API |
|------|-----------|----------------|
| 스타일 | 명시적 | 함수형, 데코레이터 |
| 코드량 | 많음 | 적음 |
| 제어 | 세밀함 | 간결함 |

---

## 10. Node Caching

### 10.1 기능

이제 LangGraph 워크플로우에서 개별 노드의 결과를 캐싱할 수 있어, 중복 계산을 줄이고 실행 속도를 높일 수 있습니다. 노드 캐싱은 특히 개발 주기를 가속화하는 데 유용합니다.

### 10.2 사용 방법

```python
from langgraph import StateGraph
from langgraph.checkpoint import InMemoryCache

cache = InMemoryCache()

graph = StateGraph(StateAnnotation)
    .addNode(
        "expensive_node",
        expensive_function,
        {
            "cachePolicy": {
                "ttl": 120,  # 120초 TTL
                "keyFunc": custom_key_function  # 선택적
            }
        }
    )
    .compile(cache=cache)
```

### 10.3 지원 캐시 백엔드

| 백엔드 | 설명 |
|--------|------|
| `InMemoryCache` | 메모리 기반 (개발용) |
| `SqliteCache` | SQLite 기반 |
| `RedisCache` | Redis 기반 (프로덕션) |

### 10.4 캐시 키 커스터마이징

```python
def custom_key_func(state):
    # 메시지 내용과 위치만 기반으로 캐시
    return JSON.stringify(
        state["messages"].map((m, idx) => [idx, m.content])
    )
```

---

## 11. Deferred Nodes

### 11.1 기능

LangGraph는 이제 deferred node 실행을 지원하여, 모든 병렬 브랜치가 완료될 때까지 노드 실행을 연기할 수 있습니다. 이는 map-reduce, 합의 기반 결정, 에이전트 협업 워크플로우에 이상적입니다.

### 11.2 사용 사례

- **Map-Reduce 흐름**: Fan-out, 독립적 처리, 적절한 시점에 fan-in
- **합의 기반 결정**: 계속하기 전에 여러 경로의 입력 대기
- **멀티 에이전트 협업**: 다양한 런타임을 가진 에이전트 간 워크플로우 조정

### 11.3 구현 방법

```python
# Deferred node 정의
graph.addNode("aggregate", aggregate_function, {"defer": True})
```

---

## 12. Middleware System

### 12.1 개요

LangChain 1.0에서 가장 큰 새로운 부분으로, 컨텍스트 엔지니어링에 대한 세밀한 제어를 제공합니다. 미들웨어는 모델 호출 전후, 도구 호출 전후에 로직을 주입할 수 있게 합니다.

### 12.2 핵심 훅

| 훅 | 실행 시점 | 용도 |
|----|----------|------|
| `before_model` | 모델 호출 전 | 상태 업데이트, 다른 노드로 점프 |
| `after_model` | 모델 호출 후 | 상태 업데이트, 라우팅 결정 |
| `modify_model_request` | 모델 호출 직전 | 도구, 프롬프트, 메시지 리스트 수정 |

### 12.3 사전 빌드 미들웨어

| 미들웨어 | 기능 |
|---------|------|
| **SummarizationMiddleware** | 토큰 제한 도달 시 자동 요약 |
| **HumanInTheLoopMiddleware** | 도구 실행 전 승인 요청 |
| **Custom Middleware** | 로깅, 검증, 캐싱 등 |

### 12.4 미들웨어 구현 예시

```python
from langchain.agents.middleware import AgentMiddleware

class LoggingMiddleware(AgentMiddleware):
    def before_model(self, state, runtime):
        print(f"Calling model with {len(state['messages'])} messages")
        return None
    
    def after_model(self, state, runtime):
        print(f"Model returned: {state['messages'][-1].content}")
        return None

# 에이전트 생성 시 미들웨어 적용
agent = create_agent(
    model="gpt-4o",
    tools=[...],
    middleware=[
        LoggingMiddleware(),
        SummarizationMiddleware(...),
        HumanInTheLoopMiddleware(...)
    ]
)
```

### 12.5 미들웨어 vs 훅

| 특징 | 데코레이터 (@) | 미들웨어 클래스 |
|------|---------------|----------------|
| 사용 시기 | 단일 훅, 간단한 설정 | 여러 훅, 복잡한 설정 |
| 재사용성 | 낮음 | 높음 (프로젝트 간) |
| 설정 | 런타임 | 초기화 시 |
| 실행 순서 | 순차적 | 순차적 (inbound), 역순 (outbound) |

### 12.6 preModelHook & postModelHook

사전 빌드 ReAct 에이전트는 이제 pre/post 모델 훅으로 더 커스터마이징 가능한 메시지 흐름을 지원합니다. Pre 모델 훅은 메시지 히스토리 요약(컨텍스트 팽창 제어)에 유용하고, post 모델 훅은 가드레일 및 human-in-the-loop 상호작용에 이상적입니다.

---

## 13. Content Blocks

### 13.1 개요

LangChain 1.0은 모든 LLM 공급자에서 작동하는 메시지 콘텐츠의 표준 표현을 도입했습니다. 메시지 객체는 기존 content 속성을 표준화된 타입 안전 표현으로 지연 파싱하는 content_blocks 속성을 구현합니다.

### 13.2 표준 Content Block 타입

| 타입 | 설명 |
|------|------|
| `TextContentBlock` | 텍스트 출력 (인용 포함) |
| `ReasoningContentBlock` | 추론 과정 (thinking) |
| `ToolContentBlock` | 서버 사이드 도구 호출 |
| `DataContentBlock` | 이미지, 오디오, 파일 등 멀티모달 |
| `InvalidToolCall` | 유효하지 않은 도구 호출 |
| `CitationAnnotation` | 인용 정보 |

### 13.3 사용 예시

```python
from langchain.chat_models import init_chat_model

llm = init_chat_model("openai:gpt-5-nano")
response = llm.invoke("When was LangChain created?")

# 기존 content (공급자별로 다름)
response.content  

# 표준화된 content_blocks (모든 공급자 동일)
response.content_blocks  # [
#     {"type": "reasoning", "reasoning": "..."},
#     {"type": "text", "text": "...", "annotations": [...]}
# ]
```

### 13.4 장점

- **공급자 독립성**: OpenAI, Anthropic, Google 등 일관된 인터페이스
- **타입 안전성**: TypedDict로 타입 체크
- **하위 호환성**: 기존 `.content` 속성 유지
- **최신 기능 지원**: 추론, 인용, 멀티모달 등

---

## 14. Overwrite & UntrackedValue

### 14.1 Overwrite

Overwrite를 추가하여 reducer를 우회할 수 있게 되었습니다. 노드가 Overwrite로 래핑된 값을 반환하면, reducer가 무시되고 채널이 해당 값으로 직접 설정됩니다.

#### 사용 사례

```python
from langgraph.types import Overwrite

def reset_node(state):
    # Reducer 무시하고 직접 설정
    return {"messages": Overwrite([])}
```

- 누적된 상태를 병합이 아닌 **재설정 또는 교체**하고 싶을 때
- 기존 값과 병합하지 않고 완전히 새로운 값으로 덮어쓰기

### 14.2 UntrackedValue

UntrackedValue는 체크포인터에 저장되지 않도록 개선되었습니다.

#### 특징

- 일시적인 값으로, 체크포인트에 포함되지 않음
- 메모리 효율성 향상
- 민감한 정보나 대용량 임시 데이터에 유용

---

## 15. Multiple Interrupt Resume

### 15.1 기능

LangGraph v0.4+에서는 병렬 interrupt를 한 번에 재개할 수 있으며, 순서와 관계없이 재개가 가능합니다.

### 15.2 특징

- **병렬 Interrupt 재개**: 여러 interrupt를 동시에 처리
- **Out-of-order Resume**: 순서 무관하게 재개
- **Interrupt ID 매핑**: `{interrupt_id: resume_value}` 형태로 제공

### 15.3 사용 사례

```python
# 병렬 도구 호출에서 여러 승인 필요
interrupts = {
    "tool_call_1": approved_value_1,
    "tool_call_2": approved_value_2,
    "tool_call_3": approved_value_3
}
graph.invoke(None, config, interrupts=interrupts)
```

---

## 16. Checkpointer 3.0

### 16.1 주요 변경사항

Checkpointers 3.0이 릴리스되었으며, 체크포인터 패키지 업그레이드가 필요합니다.

### 16.2 개선사항

| 개선사항 | 설명 |
|---------|------|
| **비동기 Serialization** | 체크포인터에서 비동기 직렬화/역직렬화 지원 |
| **Writes 제거** | 체크포인트에서 writes 제거 (성능 향상) |
| **에러 추적** | 체크포인터에 에러 정보 저장 |
| **Namespace 지원** | Subgraph용 네임스페이스 지원 |
| **Pending Writes** | Pending writes 구조 개선 |

### 16.3 에러 복구

- 체크포인터에 에러 히스토리 저장
- 이전 체크포인트에서 재개 가능
- 디버깅 지원 강화

---

## 17. 기타 개선사항

### 17.1 reconnectOnMount (JS)

페이지 새로고침이나 네트워크 문제에 대한 복원력을 제공합니다. 스트림이 자동으로 재개되어 토큰 손실이나 추가 코드가 필요하지 않습니다.

### 17.2 Type Safety 개선 (JS v0.3)

.stream() 메서드가 이제 완전히 타입 안전하며, streamMode에 따라 상태 업데이트와 값을 반환합니다.

### 17.3 Shorthand Syntax (JS)

```javascript
// addNode shorthand
.addNode({node1, node2, node3})

// addSequence shorthand
.addSequence({node1, node2, node3})
```

### 17.4 Job Queue

- 백그라운드 작업 실행
- 스트리밍 안정성 향상
- 작업 스케줄링

### 17.5 Python 3.14 Support

Python 3.14 지원이 추가되었습니다.

### 17.6 Checkpoint 쓰기 최적화

작은 값(null, numeric, str 등)을 인라인으로 처리하여 checkpoint_blobs 테이블에 대한 쓰기를 줄였습니다. 이는 업데이트되지 않은 채널에 대해 추가 값을 저장할 필요가 없음을 의미합니다.

### 17.7 비동기 내구성 모드

LangGraph는 기본적으로 백그라운드에서 체크포인트를 작성하므로(비동기 내구성 모드), 그래프가 체크포인트 완료를 기다리지 않고 계속 실행됩니다.

### 17.8 Separate Input/Output Schema

입력과 출력에 대한 별도의 스키마 지원이 추가되었습니다.

### 17.9 Dynamic Model Choice

createReactAgent에서 동적 모델 선택 지원이 추가되었습니다.

### 17.10 Provider Tools & MCP

이제 사전 빌드 ReAct 에이전트와 함께 웹 검색과 같은 내장 공급자 도구 및 원격 MCP 도구를 사용할 수 있습니다.

---

## 18. 마이그레이션 가이드

### 18.1 NodeInterrupt → interrupt()

```python
# Before (비권장)
from langgraph.errors import NodeInterrupt
raise NodeInterrupt("message")

# After (권장)
from langgraph.types import interrupt
user_input = interrupt("message")
```

### 18.2 config → Runtime (v1.0)

```python
# Before
def node(state, config):
    user_id = config["configurable"]["user_id"]

# After
def node(state, runtime):
    user_id = runtime.context.user_id
```

### 18.3 create_react_agent → create_agent

```python
# Before (LangGraph)
from langgraph.prebuilt import create_react_agent

agent = create_react_agent(model, tools)

# After (LangChain 1.0)
from langchain.agents import create_agent

agent = create_agent(model=model, tools=tools)
```

### 18.4 LCEL Chains → create_agent

```python
# Before (LCEL)
chain = prompt | llm | StrOutputParser()

# After (LangChain 1.0)
agent = create_agent(
    model=llm,
    tools=[...],
    middleware=[...]
)
```

### 18.5 Legacy 패키지 사용

```python
# Python
pip install langchain-classic

# JavaScript
npm install @langchain/classic
```

### 18.6 Checkpoint 형식 변경

체크포인트 표현이 subgraph용 네임스페이싱과 pending writes를 지원하도록 변경되었습니다. 이전에 저장된 체크포인트는 더 이상 유효하지 않으며, 새로운 사전 빌드 checkpointer를 사용하도록 업데이트해야 합니다.

### 18.7 MessagesState → MessagesAnnotation

MessagesState가 MessagesAnnotation으로 변경되었습니다. 상태를 선언할 때 새로운 Annotation 구문을 사용하는 것이 권장됩니다.

```python
# Before
from langgraph.graph import MessagesState

# After
from langgraph import MessagesAnnotation
```

---

## 19. 버전별 타임라인

### v0.6 (2024년 후반)
- Store API 도입
- 장기 메모리 지원
- Context API 초기 도입

### v0.7-0.8 (2025년 초)
- Node Caching 추가
- Deferred Nodes 추가
- preModelHook/postModelHook 지원

### v0.4 (2025년 4월)
- interrupt() 자동 감지 (.invoke()에서)
- Multiple Interrupt Resume
- 스트리밍 안정성 향상

### v1.0 Alpha (2025년 9월)
- Context API (Runtime) 공식화
- Functional API 추가
- Middleware 시스템 정식 출시

### v1.0 GA (2025년 10월)
- 프로덕션 준비 완료
- Breaking changes 없음 약속
- Checkpointer 3.0
- Python 3.14 지원

---

## 20. 우선순위 매트릭스

### 20.1 필수 (Must Have)

| 기능 | 적용 사례 |
|------|----------|
| Command API | Subgraph 라우팅, 멀티 에이전트 핸드오프 |
| interrupt() | Human-in-the-Loop |
| Streaming Modes | 실시간 진행 상황 (updates, events) |
| Checkpointer | 영속성, 내구성 있는 실행 |

### 20.2 권장 (Should Have)

| 기능 | 적용 사례 |
|------|----------|
| Context API (Runtime) | v1.0 마이그레이션 준비 |
| Store API | 장기 메모리, 사용자별 히스토리 |
| Send API | 병렬 처리 워크플로우 |
| Middleware | 컨텍스트 제어, 로깅, 검증 |
| Content Blocks | 공급자 독립적 메시지 처리 |

### 20.3 선택 (Nice to Have)

| 기능 | 적용 사례 |
|------|----------|
| Functional API | 간단한 서브그래프 |
| Node Caching | 개발 속도 향상 |
| Deferred Nodes | Map-Reduce 패턴 |
| Multiple Interrupt Resume | 병렬 도구 승인 |
| Overwrite | 상태 재설정 |

---

## 21. 참고 자료

### 21.1 공식 문서

- [LangGraph 1.0 Docs](https://docs.langchain.com/oss/python/langgraph)
- [LangChain 1.0 Docs](https://docs.langchain.com/oss/python/langchain)
- [LangGraph Release Notes](https://github.com/langchain-ai/langgraph/releases)
- [LangChain Changelog](https://changelog.langchain.com/)

### 21.2 주요 블로그 포스트

- [LangChain & LangGraph 1.0 Alpha Releases](https://blog.langchain.com/langchain-langchain-1-0-alpha-releases/)
- [LangChain/LangGraph 1.0 Release](https://blog.langchain.com/langchain-langgraph-1dot0/)
- [Agent Middleware](https://blog.langchain.com/agent-middleware/)
- [Standard Message Content](https://blog.langchain.com/standard-message-content/)
- [LangGraph Release Week Recap](https://blog.langchain.com/langgraph-release-week-recap/)

---

## 22. 요약

LangGraph 1.0과 LangChain 1.0은 다음과 같은 핵심 개선사항을 제공합니다:

### 22.1 LangGraph 1.0 핵심

1. **Production Ready**: Breaking changes 없이 안정적인 1.0 릴리스
2. **Command API**: 상태 업데이트 + 라우팅 통합
3. **Advanced Control**: interrupt(), Send API, Deferred Nodes
4. **Performance**: Node Caching, 비동기 체크포인팅
5. **Persistence**: Store API, Checkpointer 3.0

### 22.2 LangChain 1.0 핵심

1. **Simplified**: 단일 에이전트 추상화 (create_agent)
2. **Middleware System**: 세밀한 컨텍스트 제어
3. **Content Blocks**: 공급자 독립적 메시지 구조
4. **LangGraph-based**: 강력한 런타임 위에 구축
5. **Backward Compatible**: langchain-classic 패키지 제공

### 22.3 생태계 통합

- LangGraph = 저수준 런타임 + 세밀한 제어
- LangChain = 고수준 API + 빠른 프로토타이핑
- 둘 다 함께 사용 가능 (Lock-in 없음)

---

**문서 끝**
