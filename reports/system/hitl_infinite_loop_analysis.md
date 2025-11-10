# HITL 무한루프 문제 분석 및 해결 방안

**작성일**: 2025-11-04
**상태**: 🔴 Critical Bug
**영향 범위**: HITL 기능 전체

---

## 📋 목차
1. [시스템 전체 흐름도](#1-시스템-전체-흐름도)
2. [Agent 실행 흐름](#2-agent-실행-흐름)
3. [HITL 흐름 (현재 구현)](#3-hitl-흐름-현재-구현)
4. [근본 원인 분석](#4-근본-원인-분석)
5. [해결 방안](#5-해결-방안)

---

## 1. 시스템 전체 흐름도

### LangGraph 노드 구조
```
START
  ↓
Intent Understanding Node
  ↓
Planning Node (LLM)
  ↓
Executor Node ←──────────┐
  ↓                      │
  ├→ Diet Agent ─────────┤
  ├→ Workout Agent ──────┤
  ├→ Schedule Agent ─────┤
  ├→ Member Care Agent ──┤
  ├→ Coaching Agent ─────┤
  └→ HITL Handler ───────┤  (무한루프 발생!)
                         │
  ↓ (모든 단계 완료)      │
Aggregator Node          │
  ↓                      │
Output Router Node       │
  ↓                      │
  ├→ Chat Generator      │
  ├→ Graph Generator     │
  └→ Report Generator    │
     ↓                   │
    END                  │
                         │
  (각 Agent/HITL은 Executor로 복귀) ─┘
```

### 주요 컴포넌트

#### 1.1 Supervisor State
```python
class SupervisorState(TypedDict):
    messages: Sequence[BaseMessage]      # 대화 히스토리
    user_query: Optional[str]            # 사용자 질문
    user_intent: Optional[str]           # 파악된 의도
    plan: List[dict]                     # TaskStep 리스트
    current_step: int                    # 현재 실행 중인 단계
    is_planning: bool                    # 계획 수립 중?
    is_executing: bool                   # 실행 중?
    is_waiting_human: bool               # HITL 대기 중?
    aggregated_data: Optional[dict]      # Aggregator 결과
    output_format: str                   # "chat", "graph", "report"
    final_result: Optional[str]          # 최종 결과
```

#### 1.2 TaskStep 구조
```python
class TaskStep(BaseModel):
    step_id: int
    agent: str                           # "diet", "workout", "hitl" 등
    status: str                          # "pending", "running", "completed", "failed", "waiting_human"
    tool: Optional[str]                  # 사용할 Tool
    description: str                     # 작업 설명
    result: Optional[str]                # 실행 결과
    error: Optional[str]                 # 에러 메시지
    hitl_question: Optional[str]         # HITL 질문
    hitl_response: Optional[str]         # 사용자 응답
```

---

## 2. Agent 실행 흐름

### 2.1 정상 Agent 실행 (예: Diet Agent)

```
┌─────────────────────────────────────────────────────────────┐
│ Executor Node                                               │
│                                                             │
│ 1. plan = state["plan"]                                     │
│ 2. current_step = state["current_step"]  # 예: 0          │
│                                                             │
│ 3. if current_step >= len(plan):                           │
│       → Aggregator로 이동 (모든 단계 완료)                    │
│                                                             │
│ 4. step = plan[current_step]                               │
│    agent_name = step["agent"]  # "diet"                    │
│                                                             │
│ 5. return Command(                                          │
│       update={"plan": updated_plan},                        │
│       goto="diet"  # Diet Agent로 라우팅                    │
│    )                                                        │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Diet Agent Node                                             │
│                                                             │
│ 1. plan = state["plan"]                                     │
│ 2. current_step = state["current_step"]  # 0              │
│ 3. step = plan[current_step]                               │
│                                                             │
│ 4. # Tool 호출 (예: get_meal_logs)                          │
│    meal_logs = get_meal_logs(user_id=1, limit=3)          │
│                                                             │
│ 5. # 결과 포맷팅                                            │
│    result = "[DietAgent] 최근 식단: ..."                    │
│                                                             │
│ 6. # State 업데이트                                         │
│    plan[current_step]["status"] = "completed"              │
│    plan[current_step]["result"] = result                   │
│                                                             │
│ 7. return {                                                 │
│       "plan": plan,                                         │
│       "current_step": current_step + 1,  # 0 → 1 ✅        │
│       "messages": [AIMessage(content=result)]              │
│    }                                                        │
└─────────────────────────────────────────────────────────────┘
                            ↓
                   (Executor로 자동 복귀)
                            ↓
                   다음 step (step 1) 실행
```

### 2.2 주요 특징
- **Executor**: 현재 step 확인 → Agent로 Command 반환
- **Agent**: 작업 수행 → `current_step + 1` 반환 → **다음 단계로 진행**
- **Loop**: Agent → Executor → Agent → ... (모든 단계 완료 시까지)

---

## 3. HITL 흐름 (현재 구현)

### 3.1 현재 구현 흐름

```
┌─────────────────────────────────────────────────────────────┐
│ Executor Node                                               │
│                                                             │
│ step = plan[current_step]                                   │
│                                                             │
│ if step["agent"] == "hitl":                                │
│     return Command(                                         │
│         update={                                            │
│             "is_waiting_human": True,                       │
│             "plan": update_step_status(plan, current_step,  │
│                                       "waiting_human")      │
│         },                                                  │
│         goto="hitl_handler"                                │
│     )                                                       │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ HITL Handler Node                                           │
│                                                             │
│ 1. plan = state["plan"]                                     │
│ 2. current_step = state["current_step"]                    │
│ 3. step = plan[current_step]                               │
│ 4. question = step.get("hitl_question", "승인해주세요")      │
│                                                             │
│ 5. print("[HITL] 사용자 승인 대기: {question}")              │
│                                                             │
│ 6. # LangGraph interrupt() 호출                             │
│    user_response = interrupt(question)                      │
│    # ↑ 여기서 그래프 실행 중단! Checkpoint에 저장            │
│    # ↓ 재개될 때까지 아래 코드는 실행되지 않음               │
│                                                             │
│ 7. print("[HITL] 사용자 응답 수신: {user_response}")        │
│                                                             │
│ 8. if user_response is None:                               │
│        plan[current_step]["hitl_response"] = "[Auto]"      │
│    else:                                                    │
│        plan[current_step]["hitl_response"] = str(...)      │
│                                                             │
│ 9. plan[current_step]["status"] = "completed"              │
│                                                             │
│ 10. return {                                                │
│        "plan": plan,                                        │
│        "current_step": current_step + 1,  # ✅ 증가        │
│        "is_waiting_human": False,                          │
│        "messages": [AIMessage(...)]                        │
│     }                                                       │
└─────────────────────────────────────────────────────────────┘
                            ↓
                   (Executor로 자동 복귀)
```

### 3.2 WebSocket에서의 처리 (현재 구현)

```python
# 1. 최초 실행
async for event in graph.astream_events(initial_input, config=config, version="v2"):
    # 이벤트 처리...
    pass

# 2. 루프 종료 후 State 확인
final_state = await graph.aget_state(config)

# 3. Interrupt 감지
if final_state.next:  # next가 비어있지 않으면 interrupt 상태
    print(f"[WebSocket] Interrupt 감지: {final_state.next}")

    # 현재 HITL 질문 추출
    plan = final_state.values.get("plan", [])
    current_step = final_state.values.get("current_step", 0)
    step = plan[current_step]
    question = step.get("hitl_question", "승인해주세요")

    # 프론트엔드로 전송
    await manager.send_message(session_id, {
        "type": "hitl_waiting",
        "data": {"question": question, ...}
    })
```

```python
# 4. 사용자 승인/거부 수신
data = await websocket.receive_json()
hitl_response = data.get("hitl_response")  # "approved" or "rejected"

# 5. ❌ 문제: astream_events(None, config)로 재개
if hitl_response:
    initial_input = None  # 재개 신호

async for event in graph.astream_events(None, config=config, version="v2"):
    # ❌ 그래프가 재개되지 않고 처음부터 다시 시작!
    pass
```

---

## 4. 근본 원인 분석

### 4.1 무한루프 발생 원인

#### 🔴 **핵심 문제**: `astream_events()` vs `astream()`

LangGraph에서:
- ✅ **`astream()` / `ainvoke()`**: checkpoint에서 재개 (resume)
- ❌ **`astream_events()`**: 처음부터 새로 시작 (restart with events)

**현재 코드**:
```python
# ❌ 잘못된 재개 방식
async for event in graph.astream_events(None, config=config, version="v2"):
    ...
```

**실제 동작**:
1. `astream_events(None, config)` 호출
2. Checkpointer에서 State 로드
3. **그래프가 처음부터 다시 시작** (Intent → Planning → Executor → HITL → ...)
4. HITL Handler 다시 실행 → `interrupt()` 다시 호출
5. 무한 루프!

### 4.2 백엔드 로그 분석

```
[WebSocket] HITL 재개: approved
[HITL] 사용자 승인 대기: 김철수의 진행 상황을 확인해주세요  ← interrupt() 재호출!
[WebSocket] Interrupt 감지: ('hitl_handler',)
[WebSocket] HITL 대기 메시지 전송: 김철수의 진행 상황을 확인해주세요
```

**패턴**:
1. HITL 재개 시도
2. `interrupt()` 다시 호출 (hitl_handler가 처음부터 재실행)
3. Interrupt 감지
4. 프론트엔드로 다시 전송
5. 사용자 승인
6. **1번으로 돌아감 → 무한 루프**

### 4.3 추가 문제점

#### 문제 1: `astream_events()`는 재개용이 아님
- `astream_events()`는 **이벤트 모니터링용** 도구
- Interrupt 재개는 `astream()` 또는 `ainvoke()`를 사용해야 함

#### 문제 2: 이벤트 기반 HITL 감지의 한계
```python
# WebSocket에서 시도한 방법 (작동하지 않음)
elif event_type == "on_chain_stream":
    chunk = event_data.get("chunk", {})
    if isinstance(chunk, dict) and chunk.get("is_waiting_human"):
        # ❌ interrupt() 발생 시 이 이벤트는 생성되지 않음!
```

**이유**: `interrupt()`가 호출되면 그래프 실행이 **즉시 중단**되므로, 이후 이벤트는 생성되지 않음

#### 문제 3: State 기반 감지만 가능
```python
# ✅ 유일한 방법: aget_state()로 interrupt 확인
final_state = await graph.aget_state(config)
if final_state.next:  # Interrupt 발생!
    # HITL 처리
```

---

## 5. 해결 방안

### 5.1 올바른 재개 방식

#### ✅ **방법 1: `astream()` 사용 (권장)**

```python
# WebSocket 코드 수정

# 1. 최초 실행
if hitl_response:
    # HITL 재개
    async for chunk in graph.astream(None, config=config):
        # chunk는 state 업데이트
        # 노드별 상세 이벤트는 없지만 빠르고 안정적

        # State 확인
        current_state = await graph.aget_state(config)
        if current_state.next:
            # 다시 interrupt 발생 (다른 HITL이 있을 수 있음)
            break
else:
    # 새로운 요청
    async for chunk in graph.astream(initial_input, config=config):
        # 처리...
        pass

# 2. 최종 State 확인
final_state = await graph.aget_state(config)

if final_state.next:
    # HITL 대기
    # 프론트엔드로 전송
else:
    # 완료
    # 최종 결과 전송
```

#### ✅ **방법 2: `ainvoke()` 사용**

```python
# 단순한 요청-응답 방식
if hitl_response:
    # HITL 재개
    final_state = await graph.ainvoke(None, config=config)
else:
    # 새로운 요청
    final_state = await graph.ainvoke(initial_input, config=config)

# Interrupt 확인
current_state = await graph.aget_state(config)
if current_state.next:
    # HITL 대기
    pass
else:
    # 완료
    pass
```

### 5.2 실시간 이벤트 스트리밍 유지 방법

문제: `astream()`은 state chunk만 제공하고, 노드별 이벤트(`on_chain_start`, `on_chain_end`)를 제공하지 않음

#### ✅ **해결책: 하이브리드 접근**

```python
# 1. 최초 실행 시에만 astream_events() 사용
if not hitl_response:
    # 새로운 요청: 상세 이벤트 필요
    async for event in graph.astream_events(initial_input, config=config, version="v2"):
        event_type = event.get("event")

        if event_type == "on_chain_start":
            await manager.send_message(session_id, {
                "type": "node_started",
                "data": {"node": event.get("name")}
            })
        # ... 기타 이벤트 처리

    # 루프 종료 후 interrupt 체크
    final_state = await graph.aget_state(config)
    if final_state.next:
        # HITL 대기
        await send_hitl_message(...)

else:
    # HITL 재개: astream() 사용 (빠르고 안정적)
    async for chunk in graph.astream(None, config=config):
        # State 업데이트만 처리
        await manager.send_message(session_id, {
            "type": "state_updated",
            "data": {"chunk": chunk}
        })

        # Interrupt 재확인 (다른 HITL이 있을 수 있음)
        current_state = await graph.aget_state(config)
        if current_state.next:
            break

    # 최종 확인
    final_state = await graph.aget_state(config)
    if final_state.next:
        # 다시 HITL 대기
        await send_hitl_message(...)
    else:
        # 완료
        await send_final_result(...)
```

### 5.3 WebSocket 코드 수정안

#### 전체 흐름

```python
@router.websocket("/ws/chat/{session_id}")
async def websocket_chat(websocket: WebSocket, session_id: str):
    await manager.connect(session_id, websocket)

    # Graph 빌드
    checkpointer = await create_checkpointer()
    graph = build_supervisor_graph(checkpointer=checkpointer)

    await manager.send_message(session_id, {
        "type": "connected",
        "data": {"message": "WebSocket 연결 성공"}
    })

    while True:
        # 메시지 수신
        data = await websocket.receive_json()

        user_message = data["message"]
        hitl_response = data.get("hitl_response")  # "approved" or "rejected"
        output_format = data.get("output_format", "chat")

        config = get_session_config(session_id)

        try:
            await manager.send_message(session_id, {
                "type": "execution_started",
                "data": {"message": "처리 중..."}
            })

            # ===== 핵심 수정 =====
            if hitl_response:
                # HITL 재개: astream() 사용
                print(f"[WebSocket] HITL 재개: {hitl_response}")

                async for chunk in graph.astream(None, config=config):
                    # State 업데이트만 처리 (간단)
                    pass

            else:
                # 새로운 요청: astream_events() 사용 (상세 이벤트)
                initial_input = {
                    "messages": [HumanMessage(content=user_message)],
                    "output_format": output_format
                }

                async for event in graph.astream_events(initial_input, config=config, version="v2"):
                    event_type = event.get("event")
                    event_name = event.get("name")

                    if event_type == "on_chain_start":
                        if event_name and not event_name.startswith("__"):
                            await manager.send_message(session_id, {
                                "type": "node_started",
                                "data": {"node": event_name}
                            })

                    elif event_type == "on_chain_end":
                        if event_name and not event_name.startswith("__"):
                            await manager.send_message(session_id, {
                                "type": "node_completed",
                                "data": {"node": event_name}
                            })

            # 최종 State 확인
            final_state = await graph.aget_state(config)

            if final_state.next:
                # Interrupt 발생: HITL 대기
                print(f"[WebSocket] Interrupt 감지: {final_state.next}")

                state_values = final_state.values
                plan = state_values.get("plan", [])
                current_step = state_values.get("current_step", 0)

                if current_step < len(plan):
                    step = plan[current_step]
                    question = step.get("hitl_question", "승인해주세요")

                    await manager.send_message(session_id, {
                        "type": "hitl_waiting",
                        "data": {
                            "question": question,
                            "plan": plan,
                            "current_step": current_step
                        }
                    })
                    print(f"[WebSocket] HITL 대기 메시지 전송: {question}")

                # ✅ continue (다음 메시지 대기)

            else:
                # 정상 완료
                final_result = final_state.values.get("final_result", "")
                messages = final_state.values.get("messages", [])

                await manager.send_message(session_id, {
                    "type": "final_result",
                    "data": {
                        "result": final_result,
                        "message_count": len(messages)
                    }
                })

                await manager.send_message(session_id, {
                    "type": "execution_completed",
                    "data": {"message": "처리 완료"}
                })

        except Exception as e:
            print(f"[WebSocket] Error: {e}")
            traceback.print_exc()

            await manager.send_message(session_id, {
                "type": "error",
                "data": {"error": str(e)}
            })
```

### 5.4 수정 요약

| 항목 | 변경 전 | 변경 후 |
|------|---------|---------|
| **새로운 요청** | `astream_events()` | `astream_events()` ✅ (유지) |
| **HITL 재개** | `astream_events(None, ...)` ❌ | `astream(None, ...)` ✅ |
| **Interrupt 감지** | `on_chain_stream` 이벤트 ❌ | `aget_state().next` ✅ |
| **재개 시 이벤트** | 상세 이벤트 시도 ❌ | State 업데이트만 ✅ |

---

## 6. 추가 개선 사항

### 6.1 로그 개선

```python
# HITL 재개 시 더 명확한 로그
print(f"[WebSocket] HITL 재개 요청")
print(f"[WebSocket] - session_id: {session_id}")
print(f"[WebSocket] - hitl_response: {hitl_response}")
print(f"[WebSocket] - current_step before resume: {final_state.values.get('current_step')}")

# 재개 완료 후
print(f"[WebSocket] HITL 재개 완료")
print(f"[WebSocket] - current_step after resume: {new_state.values.get('current_step')}")
```

### 6.2 에러 핸들링

```python
# HITL 재개 시 타임아웃 설정
import asyncio

try:
    async with asyncio.timeout(30):  # 30초 타임아웃
        async for chunk in graph.astream(None, config=config):
            pass
except asyncio.TimeoutError:
    print(f"[WebSocket] HITL 재개 타임아웃")
    await manager.send_message(session_id, {
        "type": "error",
        "data": {"error": "HITL 재개 타임아웃"}
    })
```

### 6.3 프론트엔드 개선

```typescript
// HITL 승인 시 재시도 로직
const handleHITLApprove = async () => {
  if (!hitlState.isWaiting) return;

  setHitlState({ isWaiting: false, ... });
  setIsLoading(true);

  // 재시도 로직 (최대 3회)
  for (let i = 0; i < 3; i++) {
    try {
      wsRef.current.send(JSON.stringify({
        message: '승인',
        hitl_response: 'approved',
      }));

      // 5초 대기 (재개 완료 확인)
      await new Promise(resolve => setTimeout(resolve, 5000));

      // 여전히 HITL 상태면 재시도
      if (hitlState.isWaiting) {
        console.log(`[HITL] 재시도 ${i + 1}/3`);
        continue;
      }

      break;
    } catch (error) {
      console.error('[HITL] 승인 실패:', error);
    }
  }
};
```

---

## 7. 결론

### 7.1 핵심 문제
- **`astream_events()`는 재개용이 아님**: 이벤트 모니터링 전용
- **HITL 재개 시 `astream()` 또는 `ainvoke()` 사용 필수**

### 7.2 해결 방법
1. **HITL 재개**: `graph.astream(None, config)` 사용
2. **새로운 요청**: `graph.astream_events(input, config)` 사용 (상세 이벤트)
3. **Interrupt 감지**: `aget_state().next` 확인

### 7.3 다음 단계
1. ✅ WebSocket 코드 수정 (`websocket.py`)
2. ✅ 테스트: 단일 HITL 승인/거부
3. ✅ 테스트: 다중 HITL (2개 이상의 HITL step)
4. ✅ 프론트엔드 재시도 로직 추가
5. ✅ 로그 개선 및 모니터링

---

**작성자**: Claude Code
**참고 문서**:
- [LangGraph Interrupt Documentation](https://langchain-ai.github.io/langgraph/how-tos/human-in-the-loop/)
- `backend/app/octostrator/supervisor/main_graph.py`
- `backend/app/octostrator/supervisor/response_nodes.py`
- `backend/app/api/websocket.py`
