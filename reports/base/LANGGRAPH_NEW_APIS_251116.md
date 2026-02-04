# LangGraph 1.0 신규 API 및 개념 정리

**작성일**: 2025-11-16
**버전**: LangGraph 1.0 Alpha (2025년 출시 예정: 10월)
**목적**: 새롭게 도입된 API 및 개념의 이름과 기능만 간결하게 정리

---

## 📋 목차

1. [Command API](#1-command-api)
2. [Context API (Runtime)](#2-context-api-runtime)
3. [Send API](#3-send-api)
4. [interrupt() Function](#4-interrupt-function)
5. [Store API](#5-store-api)
6. [Streaming Modes](#6-streaming-modes)
7. [Functional API](#7-functional-api)
8. [기타 새로운 개념](#8-기타-새로운-개념)

---

## 1. Command API

### 기능
- **상태 업데이트 + 라우팅을 한 번에 처리**
- 조건부 엣지 없이도 노드에서 직접 다음 노드 지정 가능
- 멀티 에이전트 핸드오프의 핵심

### 주요 메서드

| 메서드/속성 | 기능 |
|------------|------|
| `Command(update={...})` | 상태 업데이트만 |
| `Command(goto="node_name")` | 특정 노드로 이동 |
| `Command(update={...}, goto="node")` | 상태 업데이트 + 노드 이동 |
| `Command.PARENT` | Subgraph에서 부모 그래프로 이동 |
| `Command(resume=value)` | Interrupt 이후 재개 시 사용 |

### 사용 예시
```python
def my_node(state):
    return Command(
        update={"todos": [...]},
        goto="next_node"
    )
```

---

## 2. Context API (Runtime)

### 기능
- **불변 컨텍스트를 그래프 실행에 전달**
- 기존 `config["configurable"]` 중첩 구조를 직관적으로 개선
- LangGraph v1.0의 핵심 API

### 주요 객체

| 객체 | 기능 |
|------|------|
| `Runtime` | 런타임 컨텍스트 접근 객체 |
| `runtime.context` | 사용자 정의 컨텍스트 (예: user_id, org_id) |
| `runtime.config` | LangGraph 설정 (thread_id 등) |
| `runtime.store` | Store API 접근 |

### 변경 사항 (제안)

**Before (기존)**:
```python
def node(state, config):
    user_id = config["configurable"]["user_id"]
    thread_id = config["configurable"]["thread_id"]
```

**After (신규)**:
```python
def node(state, runtime):
    user_id = runtime.context.user_id
    thread_id = runtime.config.thread_id
```

---

## 3. Send API

### 기능
- **Map-Reduce 워크플로우 구현**
- 동적 병렬 실행 (노드 수를 미리 알 수 없을 때)
- 여러 노드 인스턴스에 상태를 동적으로 분배

### 주요 메서드

| 메서드 | 기능 |
|--------|------|
| `Send(node="target", arg={...})` | 특정 노드에 데이터 전송 (병렬 실행) |
| `Send` 리스트 반환 | 여러 노드를 병렬로 실행 |

### 사용 예시
```python
def distribute_todos(state):
    # TODO 항목마다 병렬 실행
    return [
        Send("process_todo", {"todo": todo})
        for todo in state["todos"]
    ]
```

### 특징
- 각 Send는 개별 노드 인스턴스로 실행
- 모든 결과가 수집된 후 다음 노드로 진행
- 동적 워크로드에 최적화

---

## 4. interrupt() Function

### 기능
- **Human-in-the-Loop 구현의 핵심**
- 노드 실행 중 언제든지 중단하고 사용자 입력 대기
- NodeInterrupt (구 방식)를 대체하는 권장 방법

### 주요 메서드

| 메서드 | 기능 |
|--------|------|
| `interrupt(data)` | 그래프 중단 + 데이터 전달 |
| `Command(resume=value)` | 중단 이후 재개 (interrupt의 반환값) |

### 특징
- **동적 조건부 중단** 가능 (if 문 사용)
- 체크포인터에 자동으로 상태 저장
- 재개 시 노드는 처음부터 재실행 (이전 노드는 스킵)

### Interrupt 관련 개념

| 개념 | 기능 |
|------|------|
| `interrupt()` | 함수 호출 방식 (권장) |
| `NodeInterrupt` | 예외 방식 (구 방식, 비권장) |
| `__interrupt__` 이벤트 | 스트림에서 중단 감지 |
| Static Breakpoints | `interrupt_before`, `interrupt_after` (노드 단위) |
| Dynamic Breakpoints | `interrupt()` (코드 내 조건부) |

---

## 5. Store API

### 기능
- **장기 메모리 (Long-term Memory) 구현**
- Thread를 넘어서 영속적으로 데이터 저장
- 계층적 네임스페이스 지원
- 벡터 검색 가능 (선택)

### 주요 컴포넌트

| 컴포넌트 | 기능 |
|----------|------|
| `Store` | 추상 베이스 클래스 |
| `InMemoryStore` | 메모리 기반 (비영속) |
| `RedisStore` | Redis 기반 영속 저장 + 벡터 검색 |
| `MongoDBStore` | MongoDB 기반 영속 저장 + 벡터 검색 |

### 주요 메서드

| 메서드 | 기능 |
|--------|------|
| `store.put(namespace, key, value)` | 데이터 저장 |
| `store.get(namespace, key)` | 데이터 조회 |
| `store.search(namespace, query)` | 벡터 검색 (지원 시) |
| `store.delete(namespace, key)` | 데이터 삭제 |

### 네임스페이스
- **계층적 구조**: `(user_id, "memories")` 또는 `(org_id, user_id, "preferences")`
- 임의의 길이 가능
- 데이터 격리 및 조직화

---

## 6. Streaming Modes

### 기능
- **실시간 진행 상황 스트리밍**
- 토큰, 상태, 이벤트 등 다양한 수준의 스트리밍 지원

### Streaming Modes

| 모드 | 스트리밍 대상 | 사용 사례 |
|------|--------------|----------|
| `values` | 각 노드 실행 후 전체 상태 | 전체 상태 모니터링 |
| `updates` | 각 노드의 상태 업데이트만 | 변경 사항만 추적 |
| `messages` | 메시지만 (LLM 응답 등) | 채팅 인터페이스 |
| `events` | 모든 이벤트 (LLM 토큰 포함) | 상세 디버깅, 토큰 단위 스트리밍 |
| `debug` | 디버깅 정보 | 개발 중 |

### 스트리밍 메서드

| 메서드 | 기능 |
|--------|------|
| `graph.stream(input, stream_mode="values")` | 스트리밍 실행 |
| `graph.astream(input, stream_mode="events")` | 비동기 스트리밍 |
| `graph.astream_events(input)` | 모든 이벤트 스트리밍 (토큰 단위) |

### 특징
- **LangGraph v0.4+**: `invoke()`에서도 자동으로 interrupt 감지
- **Job Queue 기반**: 안정성 향상 (스트리밍 중단 없음)

---

## 7. Functional API

### 기능
- **함수형 프로그래밍 스타일로 그래프 정의**
- 그래프 기반 API의 대안
- 더 간결한 코드 작성 가능

### 특징
- 데코레이터 기반
- 암시적 그래프 구성
- 노드와 엣지를 함수로 표현

### 비교

| 특징 | Graph API (기존) | Functional API (신규) |
|------|-----------------|---------------------|
| 스타일 | 명시적 그래프 구성 | 함수형, 데코레이터 기반 |
| 코드량 | 많음 | 적음 |
| 제어 | 세밀함 | 간결함 |
| 사용 | 복잡한 워크플로우 | 간단한 체인 |

---

## 8. 기타 새로운 개념

### 8.1 Managed Values (LangGraph Cloud)

| 개념 | 기능 |
|------|------|
| Managed Storage | LangGraph API가 자동으로 저장소 관리 |
| Managed Checkpointer | 체크포인터 자동 구성 |
| Managed Store | Store API 자동 구성 |

### 8.2 Job Queue

| 개념 | 기능 |
|------|------|
| Background Runs | 백그라운드 작업 실행 |
| Streaming Reliability | 스트리밍 안정성 향상 |
| Job Scheduling | 작업 스케줄링 |

### 8.3 Multiple Interrupt Resume (v0.4+)

| 기능 | 설명 |
|------|------|
| **병렬 Interrupt 재개** | 여러 interrupt를 한 번에 재개 |
| **Out-of-order Resume** | 순서와 관계없이 재개 가능 |
| **Interrupt ID 매핑** | `{interrupt_id: resume_value}` 형태 |

**사용 사례**: 병렬 도구 호출에서 여러 승인이 필요할 때

### 8.4 Error Tracking in Checkpointer

| 기능 | 설명 |
|------|------|
| **에러 정보 저장** | 체크포인터에 에러 저장 |
| **에러 복구** | 이전 체크포인트에서 재개 |
| **디버깅 지원** | 에러 히스토리 조회 |

### 8.5 Custom Config

| 기능 | 설명 |
|------|------|
| **커스텀 설정** | 그래프 실행 시 임의의 설정 전달 |
| **설정 검증** | Pydantic으로 타입 안전성 |
| **런타임 오버라이드** | 실행 시 설정 변경 |

---

## 9. 버전별 주요 변경사항

### v0.2 (2024)
- Store API 도입
- 장기 메모리 지원

### v0.4 (2025년 4월)
- **interrupt() 자동 감지** (.invoke()에서)
- **Multiple Interrupt Resume** (병렬 재개)
- 스트리밍 안정성 향상 (Job Queue)

### v1.0 Alpha (2025년 진행 중)
- **Context API (Runtime)** 도입
- **Functional API** 추가
- **create_agent** 표준화
- Middleware 시스템 정식 출시
- 10월 정식 출시 예정

---

## 10. 주요 API 우선순위 (Octostrator 프로젝트용)

### 필수 (Must Have)
1. ✅ **Command API** - Subgraph 라우팅, 멀티 에이전트 핸드오프
2. ✅ **interrupt() Function** - Human-in-the-Loop
3. ✅ **Streaming Modes** - 실시간 진행 상황 (updates, events)
4. ✅ **AsyncPostgresSaver** - 체크포인터 (영속성)

### 권장 (Should Have)
5. ✅ **Context API (Runtime)** - v1.0 출시 시 마이그레이션
6. ✅ **Store API** - 장기 메모리 (사용자별 TODO 히스토리)
7. ✅ **Send API** - 병렬 TODO 처리

### 선택 (Nice to Have)
8. ⭐ **Functional API** - 간단한 서브그래프용
9. ⭐ **Multiple Interrupt Resume** - 병렬 도구 승인

---

## 11. 빠른 참조 테이블

### API별 주요 사용 사례

| API | 주요 사용 사례 | Octostrator 적용 |
|-----|---------------|------------------|
| **Command** | 멀티 에이전트 라우팅 | Subgraph 간 이동, 핸드오프 |
| **Context (Runtime)** | 불변 컨텍스트 전달 | user_id, session_id 전달 |
| **Send** | 병렬 처리 | TODO 병렬 실행 |
| **interrupt()** | 사용자 승인 | TODO 수정, 도구 실행 승인 |
| **Store** | 장기 메모리 | 사용자별 TODO 히스토리 |
| **Streaming** | 실시간 업데이트 | 진행 상황 표시, 토큰 스트리밍 |

---

## 12. 마이그레이션 가이드

### NodeInterrupt → interrupt()
```python
# Before (비권장)
from langgraph.errors import NodeInterrupt
raise NodeInterrupt("message")

# After (권장)
from langgraph.types import interrupt
user_input = interrupt("message")
```

### config → Runtime (v1.0)
```python
# Before
def node(state, config):
    user_id = config["configurable"]["user_id"]

# After
def node(state, runtime):
    user_id = runtime.context.user_id
```

### Static Breakpoints → Dynamic interrupt()
```python
# Before
graph.compile(interrupt_before=["node_name"])

# After
def node(state):
    if condition:
        interrupt("reason")
```

---

## 요약

LangGraph 1.0은 다음 **7가지 핵심 API**를 중심으로 구성:

1. **Command** - 라우팅 + 상태 업데이트
2. **Context (Runtime)** - 직관적 컨텍스트
3. **Send** - 동적 병렬 실행
4. **interrupt()** - Human-in-the-Loop
5. **Store** - 장기 메모리
6. **Streaming** - 실시간 업데이트
7. **Functional API** - 간결한 코드

모두 **이름-기능** 중심으로 간결하게 정리되었습니다.
