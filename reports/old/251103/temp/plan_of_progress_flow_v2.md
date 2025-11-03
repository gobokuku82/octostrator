# Progress Flow 실시간 스트리밍 구현 계획서 (v3 - WebSocket)

**작성일**: 2025-10-09 (수정: v3 2025-10-09)
**목표**: 사용자 질문 입력 시 즉시 Progress Flow 표시 및 실시간 업데이트

**v3 변경사항:**
- **SSE → WebSocket 전환**: 양방향 통신 지원 (진행상황 스트리밍 + interrupt 응답)
- **추후 확장성 확보**: Human-in-the-Loop, TodoList 관리에 WebSocket 활용
- FastAPI WebSocket endpoint 구현
- Frontend WebSocket 클라이언트 구현
- 단일 연결로 모든 통신 처리

---

## 📋 목차

1. [현재 구조 분석](#1-현재-구조-분석)
2. [WebSocket 구현 방안](#2-websocket-구현-방안)
3. [Backend 구현 상세](#3-backend-구현-상세)
4. [Frontend 구현 상세](#4-frontend-구현-상세)
5. [구현 단계](#5-구현-단계)
6. [3단계 구현 옵션](#6-3단계-구현-옵션)
7. [테스트 시나리오](#7-테스트-시나리오)
8. [추후 확장 계획](#8-추후-확장-계획)
9. [주의사항 및 제약](#9-주의사항-및-제약)

---

## 1. 현재 구조 분석

### 1.1 Frontend 현재 플로우

**파일**: `frontend/components/chat-interface.tsx`

```typescript
// 현재 플로우
const handleSendMessage = async (content: string) => {
  // 1. 사용자 메시지 추가
  setMessages([...messages, userMessage])

  // 2. ProcessState "planning" 설정
  setProcessState({step: "planning", ...})

  // 3. API 호출 (동기 대기 - 문제 지점!)
  const response = await chatAPI.sendMessage({...})  // 2-5초 소요

  // 4. 응답 받은 후에야 ExecutionPlanPage 생성
  if (response.planning_info.execution_steps) {
    setMessages([...planMessage])  // ExecutionPlanPage 추가

    setTimeout(() => {
      setMessages([...progressMessage])  // 800ms 후 ExecutionProgressPage
    }, 800)
  }

  // 5. 500ms 후 Progress 제거, 답변 표시
  setTimeout(() => {
    setMessages([...botMessage])
  }, 500)
}
```

**타이밍 다이어그램:**
```
질문입력 ────────────[2-5초 대기]────────────▶ 답변표시
                        ↑
                  API 응답 대기 중
                  (아무것도 안 보임)

응답도착 ──▶ PlanPage ──800ms──▶ ProgressPage ──500ms──▶ 답변
           (잠깐 표시)          (잠깐 표시)
```

**문제점:**
- `await chatAPI.sendMessage()` 완료까지 사용자에게 아무 피드백 없음
- 백엔드 처리 완료 후에야 progress 표시되고, 바로 사라짐
- Progress 의미 상실 (이미 완료된 작업을 보여줌)


### 1.2 Backend 현재 플로우

**LangGraph 워크플로우 구조:**
```
initialize_node (즉시)
    ↓
planning_node (LLM 호출 ~800ms)  ← execution_steps 생성 시점
    ↓
execution_node (팀별 실행 2-4초)  ← ⚠️ 문제: 전체 완료까지 블로킹
    ↓
aggregation_node (~200ms)
    ↓
response_node (~200ms)
    ↓
[ainvoke() 반환]  ← 이때서야 Frontend로 응답
```

**execution_node 내부 구조:**
```python
async def execute_teams_node(self, state: MainSupervisorState):
    """현재 구조"""
    execution_steps = state["planning_state"]["execution_steps"]

    for step in execution_steps:  # ⚠️ for loop 내부
        team = step["team"]
        if team == "search_team":
            result = await self._execute_search_team(...)
        elif team == "analysis_team":
            result = await self._execute_analysis_team(...)
        # Step 완료 후에도 중간 이벤트 전송 불가

    return state  # ⚠️ 모든 step 완료 후 한번에 반환
```

**핵심 문제:**
- `execution_node`는 **모든 step 완료까지** 반환하지 않음
- LangGraph `astream()`은 **노드 단위**로만 스트리밍 가능
- Step별 진행 상황을 중간에 전송할 방법 없음

---

## 2. WebSocket 구현 방안

### 2.1 WebSocket vs SSE 비교

| 기능 | WebSocket | SSE (이전 방식) |
|------|-----------|-----------------|
| 통신 방향 | 양방향 (Full-duplex) | 단방향 (Server → Client) |
| 프로토콜 | ws:// 또는 wss:// | HTTP |
| Interrupt 지원 | ✅ 가능 (Client → Server) | ❌ 불가능 (별도 POST 필요) |
| TodoList 관리 | ✅ 실시간 동기화 가능 | ❌ Polling 필요 |
| Plan 수정 | ✅ WebSocket으로 전송 | ❌ 별도 HTTP 요청 |
| 구현 복잡도 | 중간 (Connection 관리) | 낮음 |
| 재연결 처리 | 수동 구현 필요 | 브라우저 자동 지원 |

**WebSocket 선택 이유:**
1. **Human-in-the-Loop 필수**: Interrupt 발생 시 사용자 응답 필요 (양방향 통신)
2. **TodoList 관리**: 실시간 todo 추가/수정/삭제 (양방향 통신)
3. **단일 프로토콜**: SSE + HTTP POST 대신 WebSocket 하나로 모든 통신
4. **확장성**: 추후 기능 추가 시 프로토콜 변경 불필요

### 2.2 아키텍처 설계

**핵심 아이디어:**
- FastAPI WebSocket으로 진행 상황을 **실시간 스트리밍**
- Planning 완료 시점에 즉시 `plan_ready` 메시지 전송
- Execution 진행 중 각 step 상태 업데이트 전송 (**Callback 방식**)
- 최종 완료 시 `complete` 메시지 전송
- **추후**: Interrupt 발생 시 `interrupt_request`, 사용자 응답은 `interrupt_response`

**새로운 플로우:**
```
[Frontend]                          [Backend]

질문입력
  ├─ "분석 중..." Placeholder 표시
  └─ WebSocket 메시지 전송 ──────────▶ /ws/chat/{session_id}
     {"type": "query", "query": "..."}
                                      │
                                      ├─ status 메시지: "Planning 시작"
                                      │
                                      ├─ planning_node 실행 (~800ms)
                                      │
  ◀──────── plan_ready 메시지 ─────────┤  execution_steps 생성 완료
  │  {"type": "plan_ready", "data": {...}}
  │                                   │
  ├─ ExecutionPlanPage 표시           │
  │                                   │
  └─ 800ms 후 ExecutionProgressPage   ├─ execution_node 실행 시작
                                      │  (Callback으로 진행 상황 전송)
  ◀──────── step_update 메시지 ────────┤  Step 1 시작
  │  {"type": "step_update", "data": {
  │    "step_id": "...", "status": "in_progress"
  │  }}
  ├─ Progress UI 업데이트             │
  │                                   │
  ◀──────── step_update 메시지 ────────┤  Step 1 완료
  │  {"type": "step_update", "data": {
  │    "step_id": "...", "status": "completed"
  │  }}
  ├─ Progress UI 업데이트             │
  │                                   │
  │                                   ├─ ... (다른 step들)
  │                                   │
  ◀──────── complete 메시지 ───────────┤  최종 응답 생성 완료
  │  {"type": "complete", "data": {
  │    "response": {...}, "execution_time_ms": ...
  │  }}
  │
  ├─ Progress 제거
  └─ 최종 답변 표시
```

**타이밍 개선:**
```
[현재]
질문 ──────[2-5초 블로킹]──────▶ 답변 (Progress 의미 없음)

[WebSocket 후]
질문 ──▶ PlanPage ──▶ ProgressPage (실시간 업데이트) ──▶ 답변
       (즉시)       (Step별 실시간)
```

---

## 3. Backend 구현 상세

### 3.1 ConnectionManager 구현

**파일**: `backend/app/api/ws_manager.py` ⭐ **신규 생성**

```python
"""
WebSocket Connection Manager
세션별 WebSocket 연결 관리
"""

import logging
from typing import Dict, Optional
from fastapi import WebSocket
import json
import asyncio

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    WebSocket 연결 관리자

    - 세션별 WebSocket 연결 저장
    - 진행 상황 브로드캐스트
    - 연결 해제 처리
    """

    def __init__(self):
        # session_id -> WebSocket 매핑
        self.active_connections: Dict[str, WebSocket] = {}
        self._lock = asyncio.Lock()

    async def connect(self, session_id: str, websocket: WebSocket):
        """
        새 WebSocket 연결 등록

        Args:
            session_id: 세션 ID
            websocket: WebSocket 연결
        """
        await websocket.accept()

        async with self._lock:
            # 기존 연결이 있으면 종료
            if session_id in self.active_connections:
                try:
                    await self.active_connections[session_id].close()
                except:
                    pass

            self.active_connections[session_id] = websocket

        logger.info(f"WebSocket connected: session={session_id}")

    async def disconnect(self, session_id: str):
        """
        WebSocket 연결 해제

        Args:
            session_id: 세션 ID
        """
        async with self._lock:
            if session_id in self.active_connections:
                del self.active_connections[session_id]
                logger.info(f"WebSocket disconnected: session={session_id}")

    async def send_message(self, session_id: str, message: dict) -> bool:
        """
        특정 세션에 메시지 전송

        Args:
            session_id: 세션 ID
            message: 전송할 메시지 (dict)

        Returns:
            bool: 전송 성공 여부
        """
        websocket = self.active_connections.get(session_id)

        if not websocket:
            logger.warning(f"No active WebSocket for session {session_id}")
            return False

        try:
            await websocket.send_json(message)
            return True
        except Exception as e:
            logger.error(f"Failed to send message to {session_id}: {e}")
            await self.disconnect(session_id)
            return False

    def get_connection(self, session_id: str) -> Optional[WebSocket]:
        """
        세션의 WebSocket 연결 반환

        Args:
            session_id: 세션 ID

        Returns:
            WebSocket 또는 None
        """
        return self.active_connections.get(session_id)


# 싱글톤 인스턴스
_connection_manager = ConnectionManager()


def get_connection_manager() -> ConnectionManager:
    """ConnectionManager 싱글톤 인스턴스 반환"""
    return _connection_manager
```

### 3.2 WebSocket Endpoint 추가

**파일**: `backend/app/api/chat_api.py` (기존 파일 수정)

```python
from fastapi import APIRouter, HTTPException, Depends, WebSocket, WebSocketDisconnect
from app.api.ws_manager import get_connection_manager, ConnectionManager
import json

# ... 기존 코드 ...

# ============================================================================
# WebSocket Endpoint (NEW)
# ============================================================================

@router.websocket("/ws/{session_id}")
async def websocket_chat(
    websocket: WebSocket,
    session_id: str,
    session_mgr: SessionManager = Depends(get_session_manager)
):
    """
    WebSocket 채팅 엔드포인트

    실시간 진행 상황 스트리밍 및 양방향 통신 지원

    Client → Server 메시지 타입:
        - query: 사용자 질문
        - interrupt_response: Interrupt 응답 (추후)
        - plan_modify: 계획 수정 (추후)

    Server → Client 메시지 타입:
        - status: 상태 업데이트
        - plan_ready: 계획 수립 완료
        - step_update: Step 진행 상황 업데이트
        - complete: 최종 응답 완료
        - error: 오류 발생

    Args:
        websocket: WebSocket 연결
        session_id: 세션 ID
    """
    connection_manager = get_connection_manager()

    # 1. 세션 검증
    if not session_mgr.validate_session(session_id):
        await websocket.close(code=4004, reason="Session not found or expired")
        logger.warning(f"WebSocket rejected: invalid session {session_id}")
        return

    # 2. 연결 등록
    await connection_manager.connect(session_id, websocket)

    try:
        # 3. 메시지 수신 루프
        while True:
            # Client로부터 메시지 수신
            data = await websocket.receive_json()
            message_type = data.get("type")

            if message_type == "query":
                # 질문 처리
                query = data.get("query")
                enable_checkpointing = data.get("enable_checkpointing", True)

                logger.info(f"WebSocket query from {session_id}: {query[:100]}")

                # Supervisor 가져오기
                supervisor = await get_supervisor(enable_checkpointing=enable_checkpointing)

                # ⭐ Callback 함수 생성 (진행 상황 전송)
                async def progress_callback(event_type: str, event_data: dict):
                    """진행 상황을 WebSocket으로 전송"""
                    await connection_manager.send_message(session_id, {
                        "type": event_type,
                        "data": event_data
                    })

                # 상태 전송: Planning 시작
                await connection_manager.send_message(session_id, {
                    "type": "status",
                    "data": {"message": "질문을 분석하고 있습니다..."}
                })

                # 쿼리 처리 (callback 전달)
                start_time = datetime.now()

                result = await supervisor.process_query_streaming(
                    query=query,
                    session_id=session_id,
                    progress_callback=progress_callback  # ⭐ Callback 전달
                )

                execution_time = (datetime.now() - start_time).total_seconds() * 1000

                # Cleanup
                await supervisor.cleanup()

                # 최종 응답 전송
                response = state_to_chat_response(result, int(execution_time))

                await connection_manager.send_message(session_id, {
                    "type": "complete",
                    "data": {
                        "response": response.response,
                        "planning_info": response.planning_info,
                        "team_results": response.team_results,
                        "search_results": response.search_results,
                        "analysis_metrics": response.analysis_metrics,
                        "execution_time_ms": response.execution_time_ms,
                        "teams_executed": response.teams_executed
                    }
                })

                logger.info(f"WebSocket query completed for {session_id}: {execution_time:.0f}ms")

            elif message_type == "interrupt_response":
                # 추후 구현: Interrupt 응답 처리
                logger.info(f"Interrupt response from {session_id}: {data}")
                pass

            elif message_type == "plan_modify":
                # 추후 구현: 계획 수정 처리
                logger.info(f"Plan modification from {session_id}: {data}")
                pass

            else:
                logger.warning(f"Unknown message type from {session_id}: {message_type}")

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected normally: {session_id}")
        await connection_manager.disconnect(session_id)

    except Exception as e:
        logger.error(f"WebSocket error for {session_id}: {e}", exc_info=True)

        # 에러 메시지 전송 시도
        try:
            await connection_manager.send_message(session_id, {
                "type": "error",
                "data": {
                    "message": "처리 중 오류가 발생했습니다.",
                    "error": str(e)
                }
            })
        except:
            pass

        await connection_manager.disconnect(session_id)
```

### 3.3 TeamBasedSupervisor 수정

**파일**: `backend/app/service_agent/supervisor/team_supervisor.py`

#### Step 1: process_query_streaming() 메서드 추가

```python
async def process_query_streaming(
    self,
    query: str,
    session_id: str,
    progress_callback: Optional[Callable[[str, dict], Awaitable[None]]] = None
) -> MainSupervisorState:
    """
    쿼리 처리 (스트리밍 모드)

    progress_callback을 통해 실시간 진행 상황 전송

    Args:
        query: 사용자 질문
        session_id: 세션 ID
        progress_callback: 진행 상황 콜백 함수
            - 호출: await progress_callback(event_type, event_data)
            - event_type: "plan_ready", "step_update" 등

    Returns:
        MainSupervisorState: 최종 실행 결과
    """
    request_id = f"req_{datetime.now().timestamp()}"

    initial_state: MainSupervisorState = {
        "query": query,
        "session_id": session_id,
        "request_id": request_id,
        "status": "processing",
        "current_phase": "initialize",

        # ⭐ Callback 저장
        "_progress_callback": progress_callback,

        # ... 기존 필드들 ...
    }

    config = {
        "configurable": {
            "thread_id": session_id,
            "checkpoint_ns": session_id
        }
    }

    # LangGraph 실행
    final_state = await self.app.ainvoke(initial_state, config=config)

    return final_state
```

#### Step 2: planning_node 수정 ⭐ **핵심 수정**

```python
async def planning_node(self, state: MainSupervisorState) -> MainSupervisorState:
    """
    계획 수립 노드 (Callback 지원)
    """
    logger.info("[TeamSupervisor] Planning phase")

    state["current_phase"] = "planning"

    # Planning Agent 실행
    planning_agent = PlanningAgent(self.llm_context)

    analyzed_intent = await planning_agent.analyze_intent(state["query"])
    state["planning_state"] = {"analyzed_intent": analyzed_intent}

    # Intent에 따라 분기
    if analyzed_intent["intent_type"] in ["unclear", "irrelevant"]:
        # Guidance 생성
        guidance = await planning_agent.generate_guidance(analyzed_intent)
        state["final_response"] = {
            "type": "guidance",
            "content": guidance,
            "data": {}
        }
        state["status"] = "completed"
        return state

    # 실행 계획 수립
    execution_plan = await planning_agent.create_execution_plan(
        query=state["query"],
        analyzed_intent=analyzed_intent
    )

    state["planning_state"]["execution_steps"] = execution_plan["execution_steps"]
    state["planning_state"]["execution_strategy"] = execution_plan["execution_strategy"]
    state["planning_state"]["estimated_total_time"] = execution_plan["estimated_total_time"]
    state["planning_state"]["plan_validated"] = True

    # ⭐ Callback: plan_ready 이벤트 전송
    callback = state.get("_progress_callback")
    if callback:
        await callback("plan_ready", {
            "intent": analyzed_intent["intent_type"],
            "confidence": analyzed_intent.get("confidence", 0.0),
            "execution_steps": execution_plan["execution_steps"],
            "execution_strategy": execution_plan["execution_strategy"],
            "estimated_total_time": execution_plan["estimated_total_time"],
            "keywords": analyzed_intent.get("keywords", [])
        })

    return state
```

#### Step 3: execute_teams_node 수정 ⭐ **핵심 수정**

```python
async def execute_teams_node(self, state: MainSupervisorState) -> MainSupervisorState:
    """
    팀 실행 노드 (Step별 callback 지원)
    """
    logger.info("[TeamSupervisor] Execution phase")

    state["current_phase"] = "execution"

    planning_state = state.get("planning_state")
    if not planning_state or not planning_state.get("execution_steps"):
        logger.warning("No execution steps found")
        return state

    execution_steps = planning_state["execution_steps"]

    # ⭐ Callback 함수 가져오기
    callback = state.get("_progress_callback")

    # ⭐ 각 Step 실행하면서 callback 호출
    for step in execution_steps:
        step_id = step["step_id"]
        team = step.get("team")

        # Step 시작 콜백
        if callback:
            await callback("step_update", {
                "step_id": step_id,
                "team": team,
                "description": step.get("description", ""),
                "status": "in_progress",
                "progress_percentage": 0
            })

        # 실제 팀 실행
        step_start_time = datetime.now()
        try:
            result = None

            if team == "search_team":
                result = await self._execute_search_team(state, step)
            elif team == "analysis_team":
                result = await self._execute_analysis_team(state, step)
            elif team == "document_team":
                result = await self._execute_document_team(state, step)

            # Step 결과 저장
            state["team_results"][step_id] = result

            # Step 완료 콜백
            step_time = (datetime.now() - step_start_time).total_seconds() * 1000

            if callback:
                await callback("step_update", {
                    "step_id": step_id,
                    "team": team,
                    "description": step.get("description", ""),
                    "status": "completed",
                    "progress_percentage": 100,
                    "execution_time_ms": int(step_time)
                })

        except Exception as e:
            logger.error(f"Step {step_id} failed: {e}")

            # Step 실패 콜백
            if callback:
                await callback("step_update", {
                    "step_id": step_id,
                    "team": team,
                    "description": step.get("description", ""),
                    "status": "failed",
                    "error": str(e)
                })

    return state
```

### 3.4 MainSupervisorState 타입 수정

**파일**: `backend/app/service_agent/foundation/separated_states.py`

```python
from typing import TypedDict, Optional, Callable, Awaitable

class MainSupervisorState(TypedDict, total=False):
    """Main supervisor state schema"""
    # 기존 필드들...
    query: str
    session_id: str
    request_id: str
    status: str
    current_phase: str

    planning_state: Optional[dict]
    search_team_state: Optional[dict]
    analysis_team_state: Optional[dict]
    document_team_state: Optional[dict]

    team_results: dict
    final_response: dict

    completed_teams: list
    failed_teams: list
    error: Optional[str]
    error_log: list

    # ⭐ Callback 함수 추가 (스트리밍용)
    _progress_callback: Optional[Callable[[str, dict], Awaitable[None]]]
```

### 3.5 LangGraph astream() 한계 설명 ⭐ **중요**

**왜 astream()을 사용하지 않는가?**

```python
# ❌ astream()으로는 step별 진행 상황 전송 불가
async for chunk in self.app.astream(initial_state, config=config):
    node_name = list(chunk.keys())[0]
    node_output = chunk[node_name]

    if node_name == "planning_node":
        # ✅ Planning 완료 → OK
        await callback("plan_ready", {...})

    elif node_name == "execution_node":
        # ❌ execution_node가 **완료**될 때만 이벤트 발생
        # 내부의 step별 진행은 감지 불가!
        pass
```

**astream()의 한계:**
- **노드 단위**로만 스트리밍 가능
- `execution_node` **내부**의 for loop은 감지 불가
- Step 시작/완료 이벤트를 중간에 전송할 수 없음

**해결책: Callback 방식 (위에서 구현)**
- State에 callback 함수 저장
- `execution_node` 내부에서 직접 callback 호출
- Step별 진행 상황 실시간 전송 가능

---

## 4. Frontend 구현 상세

### 4.1 WebSocket Client 생성

**파일**: `frontend/lib/ws.ts` ⭐ **신규 생성**

```typescript
/**
 * WebSocket Client for real-time chat communication
 */

const WS_BASE_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000"

export type WSMessageType =
  | "status"
  | "plan_ready"
  | "step_update"
  | "complete"
  | "error"

export interface WSMessage {
  type: WSMessageType
  data: any
}

export interface WSClientConfig {
  sessionId: string
  onMessage: (message: WSMessage) => void
  onConnect?: () => void
  onDisconnect?: () => void
  onError?: (error: Event) => void
}

export class ChatWSClient {
  private ws: WebSocket | null = null
  private sessionId: string
  private config: WSClientConfig
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5
  private reconnectDelay = 1000 // 1초

  constructor(config: WSClientConfig) {
    this.sessionId = config.sessionId
    this.config = config
  }

  /**
   * WebSocket 연결
   */
  connect(): void {
    const wsUrl = `${WS_BASE_URL}/api/v1/chat/ws/${this.sessionId}`

    console.log(`[WS] Connecting to ${wsUrl}`)

    this.ws = new WebSocket(wsUrl)

    this.ws.onopen = () => {
      console.log(`[WS] Connected: session=${this.sessionId}`)
      this.reconnectAttempts = 0
      this.config.onConnect?.()
    }

    this.ws.onmessage = (event) => {
      try {
        const message: WSMessage = JSON.parse(event.data)
        console.log(`[WS] Message received:`, message.type, message.data)
        this.config.onMessage(message)
      } catch (e) {
        console.error("[WS] Failed to parse message:", e)
      }
    }

    this.ws.onerror = (error) => {
      console.error("[WS] Error:", error)
      this.config.onError?.(error)
    }

    this.ws.onclose = (event) => {
      console.log(`[WS] Disconnected: code=${event.code}, reason=${event.reason}`)
      this.ws = null
      this.config.onDisconnect?.()

      // 비정상 종료 시 재연결 시도
      if (event.code !== 1000 && this.reconnectAttempts < this.maxReconnectAttempts) {
        this.reconnectAttempts++
        console.log(`[WS] Reconnecting... (attempt ${this.reconnectAttempts})`)
        setTimeout(() => this.connect(), this.reconnectDelay * this.reconnectAttempts)
      }
    }
  }

  /**
   * 메시지 전송
   */
  send(message: any): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      console.warn("[WS] Cannot send message: not connected")
      return
    }

    this.ws.send(JSON.stringify(message))
    console.log("[WS] Message sent:", message)
  }

  /**
   * 질문 전송
   */
  sendQuery(query: string, enableCheckpointing: boolean = true): void {
    this.send({
      type: "query",
      query,
      enable_checkpointing: enableCheckpointing,
    })
  }

  /**
   * Interrupt 응답 전송 (추후)
   */
  sendInterruptResponse(response: any): void {
    this.send({
      type: "interrupt_response",
      response,
    })
  }

  /**
   * Plan 수정 전송 (추후)
   */
  sendPlanModification(modifiedPlan: any): void {
    this.send({
      type: "plan_modify",
      plan: modifiedPlan,
    })
  }

  /**
   * 연결 해제
   */
  disconnect(): void {
    if (this.ws) {
      console.log("[WS] Disconnecting...")
      this.ws.close(1000, "Client closed")
      this.ws = null
    }
  }

  /**
   * 연결 상태 확인
   */
  isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN
  }
}
```

### 4.2 chat-interface.tsx 수정 개요

**주요 변경사항:**
1. WebSocket 연결 관리
2. 메시지 핸들러 추가 (`plan_ready`, `step_update`, `complete`)
3. 실시간 progress 업데이트

### 4.3 타입 정의 업데이트

**파일**: `frontend/types/execution.ts`

```typescript
export interface ExecutionStep {
  step_id: string
  team: string
  description: string
  dependencies: string[]
  estimated_time: number

  // 실시간 업데이트 필드
  status?: "pending" | "in_progress" | "completed" | "failed"
  progress_percentage?: number
  execution_time_ms?: number
  error?: string
}

export interface ExecutionPlan {
  intent: string
  confidence: number
  execution_steps: ExecutionStep[]
  execution_strategy: string
  estimated_total_time: number
  keywords: string[]
}
```

---

## 5. 구현 단계

### Phase 1: Backend 기반 구축 (3-4시간)

1. **ConnectionManager 구현** (1시간)
   - [ ] `ws_manager.py` 생성
   - [ ] 세션별 연결 관리
   - [ ] 메시지 전송 함수

2. **WebSocket Endpoint** (1-1.5시간)
   - [ ] `/ws/{session_id}` 엔드포인트 추가
   - [ ] 메시지 수신 처리
   - [ ] 에러 핸들링

3. **MainSupervisorState 수정** (0.5시간)
   - [ ] `_progress_callback` 필드 추가
   - [ ] 타입 정의 업데이트

4. **process_query_streaming() 구현** (0.5-1시간)
   - [ ] Callback 전달
   - [ ] LangGraph 실행

### Phase 2: LangGraph 노드 수정 (3-4시간)

1. **planning_node 수정** (1-1.5시간)
   - [ ] `plan_ready` 이벤트 전송
   - [ ] ExecutionPlan 데이터 구조 확인

2. **execute_teams_node 수정** (2-2.5시간) ⭐ **핵심**
   - [ ] Step별 `step_update` 이벤트 전송
   - [ ] 각 팀 실행 전후 callback 호출
   - [ ] 에러 처리 및 failed 상태 전송

### Phase 3: Frontend 구현 (4-6시간)

1. **WebSocket Client** (1.5-2시간)
   - [ ] `lib/ws.ts` 생성
   - [ ] 연결/해제 관리
   - [ ] 재연결 로직
   - [ ] 메시지 송수신

2. **chat-interface.tsx 수정** (2-3시간)
   - [ ] WebSocket 연결 관리
   - [ ] 메시지 핸들러 구현
   - [ ] ExecutionPlanPage 즉시 표시
   - [ ] ExecutionProgressPage 실시간 업데이트
   - [ ] 최종 응답 표시

3. **타입 정의** (0.5-1시간)
   - [ ] ExecutionStep 타입 업데이트
   - [ ] ExecutionPlan 타입 정의
   - [ ] Message 타입 확장

### Phase 4: 테스트 및 디버깅 (2-3시간)

1. **기본 기능 테스트** (1시간)
   - [ ] 질문 입력 → 즉시 Progress 표시 확인
   - [ ] Step별 실시간 업데이트 확인
   - [ ] 최종 답변 표시 확인

2. **에러 시나리오** (0.5-1시간)
   - [ ] 연결 끊김 → 재연결 확인
   - [ ] Step 실패 → failed 상태 표시 확인
   - [ ] 네트워크 오류 처리

3. **UI/UX 개선** (0.5-1시간)
   - [ ] 타이밍 조정 (PlanPage → ProgressPage 전환)
   - [ ] 애니메이션 확인
   - [ ] 로딩 상태 표시

---

## 6. 3단계 구현 옵션

### Option A: 간단한 Placeholder (6-8시간) ❌ **사용 안 함**

**범위:**
- Planning 완료 시 ExecutionPlanPage만 표시
- ExecutionProgressPage는 "작업 실행 중..." Placeholder만 표시
- Step별 실시간 업데이트 없음

**장점:**
- 빠른 구현

**단점:**
- 실시간 진행 상황 없음 (의미 없음)

### Option B: Planning 실시간 + Progress Placeholder (12-15시간) ✅ **권장**

**범위:**
- ✅ Planning 완료 시 즉시 ExecutionPlanPage 표시
- ✅ ExecutionProgressPage 표시 (Step별 상태는 업데이트)
- ✅ `plan_ready` 이벤트 전송
- ✅ `step_update` 이벤트 전송 (Step 시작/완료)
- ❌ Step 내부 진행률 없음 (0% → 100%)

**장점:**
- 사용자에게 즉각적인 피드백
- Step별 완료 상황 확인 가능
- 구현 복잡도 적정

**단점:**
- Step 내부 진행률 없음 (팀 실행 중 0%로 고정)

**구현 범위:**
- Backend: `plan_ready`, `step_update` (시작/완료만)
- Frontend: ExecutionPlanPage, ExecutionProgressPage 실시간 업데이트

### Option C: 완전한 실시간 스트리밍 (18-25시간) ⭐ **최종 목표**

**범위:**
- ✅ Option B 전체
- ✅ Step 내부 진행률 업데이트 (0% → 30% → 60% → 100%)
- ✅ Search 결과 개수 실시간 표시
- ✅ Analysis 진행 상황 표시

**추가 구현:**
- SearchExecutor 내부에서 callback 호출
- AnalysisAgent 내부에서 callback 호출
- DocumentAgent 내부에서 callback 호출

**예시:**
```python
# SearchExecutor 수정
async def execute(self, ...):
    callback = state.get("_progress_callback")

    for i, source in enumerate(sources):
        # 검색 진행률
        if callback:
            await callback("step_progress", {
                "step_id": step_id,
                "progress_percentage": int((i / len(sources)) * 100),
                "message": f"{source} 검색 중..."
            })

        results = await self._search_source(source)
```

**장점:**
- 완벽한 실시간 피드백
- 사용자 경험 최상

**단점:**
- 구현 시간 많이 소요
- 각 Agent 내부 수정 필요

---

## 7. 테스트 시나리오

### 7.1 정상 플로우

**시나리오 1: 시세 조회**
```
입력: "강남구 아파트 시세 알려줘"

[Frontend]
1. 사용자 메시지 표시
2. WebSocket으로 query 전송
3. (즉시) "분석 중..." Placeholder 표시

[Backend]
4. planning_node 실행 (~800ms)
5. plan_ready 전송

[Frontend]
6. ExecutionPlanPage 표시
   - 의도: 시세 조회
   - 예정 작업: 검색팀 → 분석팀
   - 예상 시간: 3.5초

7. (800ms 후) ExecutionProgressPage 표시

[Backend]
8. execute_teams_node 실행
   - step_update: search_team 시작
   - step_update: search_team 완료
   - step_update: analysis_team 시작
   - step_update: analysis_team 완료

[Frontend]
9. Progress 실시간 업데이트
   - Step 1: 검색팀 (in_progress → completed)
   - Step 2: 분석팀 (in_progress → completed)

[Backend]
10. complete 전송

[Frontend]
11. (500ms 후) Progress 제거, 답변 표시
```

**예상 타이밍:**
```
0ms: 질문 입력
0ms: "분석 중..." 표시
800ms: ExecutionPlanPage 표시
1600ms: ExecutionProgressPage 표시 + Step 1 시작
2800ms: Step 1 완료, Step 2 시작
4500ms: Step 2 완료
5000ms: 답변 표시
```

### 7.2 에러 시나리오

**시나리오 2: Step 실패**
```
[Backend]
1. step_update: search_team 시작
2. (에러 발생)
3. step_update: search_team failed (error 메시지 포함)
4. step_update: analysis_team skipped

[Frontend]
5. Step 1: 검색팀 (failed, 빨간색 표시)
6. Step 2: 분석팀 (skipped)
7. 최종 답변: "일부 정보를 가져오지 못했습니다."
```

**시나리오 3: WebSocket 연결 끊김**
```
[Frontend]
1. WebSocket 연결 해제 감지
2. 재연결 시도 (5회까지)
3. 재연결 성공 → 메시지 계속 수신
4. 재연결 실패 → 에러 메시지 표시
```

### 7.3 Unclear/Irrelevant Intent

**시나리오 4: 명확화 필요**
```
입력: "ㄴㅁㅇㄹ"

[Backend]
1. planning_node: intent = "unclear"
2. (execute_teams_node 실행 안 함)
3. complete 전송 (guidance 응답)

[Frontend]
4. ExecutionPlanPage 표시 안 함
5. 바로 답변 표시: "질문을 명확히 해주세요."
```

---

## 8. 추후 확장 계획

### 8.1 Human-in-the-Loop (Interrupt) ⭐ **LangGraph 0.6.6+ 핵심 기능**

#### 8.1.1 Interrupt 동작 원리

**LangGraph의 Interrupt는 실행 중간에 사용자 입력을 받는 메커니즘입니다.**

```python
# team_supervisor.py
from langgraph.types import interrupt, Command

async def planning_node(self, state: MainSupervisorState):
    # 1. 계획 수립
    execution_plan = await self.planning_agent.create_execution_plan(...)
    state["planning_state"]["execution_steps"] = execution_plan["execution_steps"]
    state["todo_list"] = [...]  # TODO 생성

    # 2. ⭐ Interrupt 발생: 여기서 실행 멈춤!
    user_response = interrupt({
        "type": "plan_approval",
        "plan": execution_plan,
        "todos": state["todo_list"],
        "message": "이 계획대로 진행할까요? TODO를 수정하시려면 변경해주세요."
    })

    # ⭐ Checkpoint 저장되고 사용자 응답 대기...
    # Frontend에서 interrupt_response를 보내면 여기서부터 재개됨

    # 3. 사용자 응답 처리
    if user_response.get("action") == "modify":
        # TODO 수정 반영
        state["todo_list"] = user_response["modified_todos"]
        state["todo_modified_by_user"] = True

        # execution_steps도 수정
        state["planning_state"]["execution_steps"] = user_response["modified_plan"]

    return state
```

**Interrupt 재개 (Backend):**
```python
# chat_api.py
elif message_type == "interrupt_response":
    interrupt_id = data.get("interrupt_id")
    response = data.get("response")

    # ⭐ LangGraph Command로 실행 재개
    from langgraph.types import Command

    result = await supervisor.app.ainvoke(
        Command(resume=response),  # 사용자 응답 전달
        config={
            "configurable": {
                "thread_id": session_id,
                "checkpoint_ns": session_id
            }
        }
    )

    # 재개된 실행 계속 진행...
```

#### 8.1.2 WebSocket 메시지 프로토콜

```typescript
// Server → Client: Interrupt 요청
{
  type: "interrupt_request",
  interrupt_id: "int_1633024800_abc123",  // 고유 ID
  data: {
    interrupt_type: "plan_approval" | "todo_modification",
    plan: ExecutionPlan,
    todos: TodoItem[],
    message: "이 계획대로 진행할까요?"
  }
}

// Client → Server: Interrupt 응답
{
  type: "interrupt_response",
  interrupt_id: "int_1633024800_abc123",
  response: {
    action: "approve" | "modify" | "cancel",
    modified_plan?: ExecutionStep[],  // action === "modify" 시
    modified_todos?: TodoItem[]       // TODO 수정 시
  }
}

// Server → Client: 재개 확인
{
  type: "execution_resumed",
  data: {
    message: "수정된 계획으로 진행합니다",
    updated_plan: ExecutionPlan,
    updated_todos: TodoItem[]
  }
}
```

#### 8.1.3 작업 중 Interrupt (실시간 수정)

**시나리오: Step 실행 중 사용자가 TODO 수정**

```
[Timeline]
0ms:     질문 입력
800ms:   Planning 완료 → Interrupt 발생
         TODO: [검색, 분석, 문서생성]
1000ms:  사용자가 "분석" 제거 → interrupt_response 전송
1050ms:  Backend가 Command로 재개
         TODO: [검색, 문서생성]  ← 수정됨
1100ms:  검색 시작 (step_update)
2000ms:  검색 완료
2050ms:  ⚠️ 사용자가 "문서생성 취소" 요청
         → 어떻게 처리?
```

**해결책: 작업 중 Interrupt는 불가, 대신 Skip 기능 제공**

```python
# execute_teams_node
async def execute_teams_node(self, state: MainSupervisorState):
    todos = state["todo_list"]
    callback = state.get("_progress_callback")

    for todo in todos:
        if todo["status"] == "skipped":  # ⭐ 사용자가 skip 요청
            if callback:
                await callback("todo_skipped", {"todo": todo})
            continue

        # TODO 실행...
```

**Frontend에서 Skip 요청:**
```typescript
// 사용자가 "문서생성 건너뛰기" 클릭
ws.send({
  type: "todo_skip",
  todo_id: "step_3"
})

// Backend에서 State 업데이트 (Interrupt 없이)
// → 다음 루프에서 자동 스킵
```

### 8.2 TodoList 관리 (State 기반)

#### 8.2.1 TodoList는 MainSupervisorState에 저장

**저장 위치:**
- ✅ **State (`todo_list` 필드)**: LangGraph Checkpoint에 저장
- ❌ **별도 DB**: State와 동기화 복잡, 비권장

**이유:**
1. **Checkpoint와 함께 저장** → 브라우저 새로고침 시에도 복원
2. **노드에서 직접 접근** → 실행 중 TODO 상태 업데이트 가능
3. **Interrupt에서 수정 가능** → 사용자가 TODO 수정 시 State에 반영

#### 8.2.2 TodoList 생성 및 업데이트 플로우

```
[Planning Node]
  ├─ execution_plan 생성
  ├─ TODO 리스트 생성 (execution_steps 기반)
  │  └─ state["todo_list"] = [...]
  │
  ├─ WebSocket 전송: todo_created
  │  └─ Frontend: TodoListUI 표시
  │
  ├─ (선택) Interrupt: 사용자에게 TODO 수정 요청
  │  └─ user_response = interrupt({"type": "todo_approval", ...})
  │
  └─ 사용자 수정 반영
     └─ state["todo_list"] = user_response["modified_todos"]

[Execution Node]
  ├─ todos = state["todo_list"]
  │
  └─ for todo in todos:
       ├─ todo["status"] = "in_progress"
       ├─ WebSocket 전송: todo_progress
       ├─ 팀 실행
       ├─ todo["status"] = "completed"
       └─ WebSocket 전송: todo_progress
```

#### 8.2.3 WebSocket 메시지 프로토콜

```typescript
// Server → Client: TODO 생성
{
  type: "todo_created",
  data: {
    todos: [
      {
        todo_id: "step_1",
        task: "법률 정보 검색",
        description: "관련 법률 조항 검색",
        status: "pending",
        agent_type: "search_team",
        estimated_time: 2.5,
        created_at: "2025-10-09T10:30:00"
      },
      // ...
    ]
  }
}

// Server → Client: TODO 진행 상황
{
  type: "todo_progress",
  data: {
    todo_id: "step_1",
    status: "in_progress" | "completed" | "failed",
    actual_time: 2.3,  // 완료 시
    error: "...",       // 실패 시
    updated_at: "2025-10-09T10:30:02.3"
  }
}

// Client → Server: TODO Skip 요청 (작업 중)
{
  type: "todo_skip",
  todo_id: "step_2"
}

// Server → Client: TODO Skip 확인
{
  type: "todo_skipped",
  data: {
    todo_id: "step_2",
    status: "skipped"
  }
}
```

#### 8.2.4 실시간 TODO 수정 시나리오

**시나리오 1: Planning 단계에서 수정 (Interrupt 사용)**
```
1. Planning 완료 → TODO 생성
2. Interrupt 발생 → 사용자에게 TODO 보여줌
3. 사용자가 TODO 수정 (추가/삭제/순서변경)
4. interrupt_response로 수정된 TODO 전송
5. Backend가 state["todo_list"] 업데이트
6. 수정된 TODO로 실행 시작
```

**시나리오 2: 실행 중 Skip 요청 (Interrupt 없이)**
```
1. Step 1 실행 중
2. 사용자가 "Step 3 건너뛰기" 클릭
3. Frontend가 todo_skip 메시지 전송
4. Backend가 state["todo_list"][2]["status"] = "skipped" 업데이트
5. Step 3 차례가 되면 자동 스킵
```

**시나리오 3: 브라우저 새로고침 (Checkpoint 복원)**
```
1. 사용자가 Step 2 진행 중 브라우저 새로고침
2. Frontend가 /api/chat/restore?session_id=xxx 호출
3. Backend가 Checkpoint에서 State 복원
   - state["todo_list"] 포함
4. WebSocket 재연결
5. Backend가 복원된 TODO 전송: todo_restored
6. Frontend가 TodoListUI 복원
7. 실행 재개 (Step 2부터)
```

### 8.3 Plan 수정 기능

**사용자가 실행 계획 수정:**
- ExecutionPlanPage에서 step 추가/삭제/순서 변경
- WebSocket으로 수정된 계획 전송
- Backend에서 수정된 계획으로 실행

---

## 9. 주의사항 및 제약

### 9.1 LangGraph astream() 제약

**문제:**
- `astream()`은 **노드 단위**로만 이벤트 발생
- `execution_node` **내부** for loop은 감지 불가

**해결:**
- Callback 방식 사용
- State에 `_progress_callback` 저장
- 노드 내부에서 직접 callback 호출

### 9.2 WebSocket 연결 관리

**주의사항:**
1. **세션당 1개 연결**: 동일 세션에서 여러 연결 방지
2. **연결 해제 처리**: 정상/비정상 종료 구분
3. **재연결 로직**: 네트워크 끊김 시 자동 재연결
4. **메시지 손실 방지**: ⚠️ **Phase 1에서 반드시 구현 필요**

**메시지 큐잉 구현 (필수):**

```python
# ws_manager.py
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.message_queues: Dict[str, asyncio.Queue] = {}  # ⭐ 추가
        self._lock = asyncio.Lock()

    async def send_message(self, session_id: str, message: dict) -> bool:
        websocket = self.active_connections.get(session_id)

        if not websocket:
            # ⭐ 연결 없으면 큐에 저장
            if session_id not in self.message_queues:
                self.message_queues[session_id] = asyncio.Queue()
            await self.message_queues[session_id].put(message)
            logger.warning(f"WebSocket not connected, queued message for {session_id}")
            return False

        try:
            await websocket.send_json(message)
            return True
        except Exception as e:
            # ⭐ 전송 실패 시 재큐잉
            logger.error(f"Failed to send message to {session_id}: {e}")
            await self.disconnect(session_id)
            if session_id not in self.message_queues:
                self.message_queues[session_id] = asyncio.Queue()
            await self.message_queues[session_id].put(message)
            return False
```

**재연결 시 State 동기화:**

```python
# chat_api.py WebSocket endpoint
@router.websocket("/ws/{session_id}")
async def websocket_chat(websocket: WebSocket, session_id: str):
    await connection_manager.connect(session_id, websocket)

    # ⭐ 큐에 저장된 메시지 flush
    if session_id in connection_manager.message_queues:
        queue = connection_manager.message_queues[session_id]
        while not queue.empty():
            msg = await queue.get()
            await websocket.send_json(msg)
        logger.info(f"Flushed {queue.qsize()} queued messages for {session_id}")

    # 이후 정상 메시지 수신 루프...
```

### 9.3 State 크기 제한 및 TodoList 저장

**문제 1: Callback 함수 직렬화**
- Callback 함수는 직렬화 불가
- Checkpoint에 저장되면 Exception 발생

**해결:**
```python
# team_supervisor.py
async def process_query_streaming(...):
    initial_state = MainSupervisorState(...)
    initial_state["_progress_callback"] = progress_callback

    final_state = await self.app.ainvoke(initial_state, config=config)

    # ⭐ Checkpoint 저장 전에 callback 제거
    if "_progress_callback" in final_state:
        del final_state["_progress_callback"]

    return final_state
```

**문제 2: TodoList 저장 위치**

✅ **TodoList는 MainSupervisorState에 저장해야 함**

**이유:**
1. **Checkpoint와 함께 저장** → 브라우저 새로고침 시에도 복원
2. **LangGraph 노드에서 직접 접근** → 실행 중 TODO 상태 업데이트
3. **Interrupt에서 수정 가능** → 사용자가 TODO 수정 시 State 업데이트

```python
# separated_states.py

class TodoItem(TypedDict):
    """TODO 아이템 구조"""
    todo_id: str
    task: str
    description: str
    status: Literal["pending", "in_progress", "completed", "failed", "skipped"]
    agent_type: str  # "search_team", "analysis_team", "document_team"
    estimated_time: float
    actual_time: Optional[float]
    created_at: str
    updated_at: str
    error: Optional[str]

class MainSupervisorState(TypedDict, total=False):
    """메인 Supervisor의 State"""
    # 기존 필드들...
    query: str
    session_id: str
    planning_state: Optional[PlanningState]

    # ⭐ TodoList 추가
    todo_list: List[TodoItem]
    todo_modified_by_user: bool

    # ⭐ Callback (runtime only, Checkpoint에서 제외됨)
    _progress_callback: Optional[Callable[[str, dict], Awaitable[None]]]
```

**TodoList 동작 플로우:**

```python
# planning_node
async def planning_node(self, state: MainSupervisorState):
    # 1. 실행 계획 생성
    execution_plan = await self.planning_agent.create_execution_plan(...)

    # 2. TODO 리스트 생성
    todos = [
        TodoItem(
            todo_id=step["step_id"],
            task=step["description"],
            status="pending",
            agent_type=step["team"],
            estimated_time=step["estimated_time"],
            created_at=datetime.now().isoformat()
        )
        for step in execution_plan["execution_steps"]
    ]
    state["todo_list"] = todos

    # 3. Callback으로 Frontend에 전송
    callback = state.get("_progress_callback")
    if callback:
        await callback("todo_created", {"todos": todos})

    # 4. (선택) Interrupt로 사용자 승인/수정 요청
    from langgraph.types import interrupt
    user_response = interrupt({
        "type": "todo_approval",
        "todos": todos,
        "message": "이 작업들을 진행할까요?"
    })

    # 5. 사용자가 수정했으면 반영
    if user_response.get("action") == "modify":
        state["todo_list"] = user_response["modified_todos"]
        state["todo_modified_by_user"] = True

    return state

# execute_teams_node
async def execute_teams_node(self, state: MainSupervisorState):
    todos = state.get("todo_list", [])
    callback = state.get("_progress_callback")

    for todo in todos:
        if todo["status"] != "pending":
            continue

        # TODO 시작
        todo["status"] = "in_progress"
        if callback:
            await callback("todo_progress", {"todo": todo})

        # 실제 팀 실행
        try:
            result = await self._execute_team(todo["agent_type"], state)
            todo["status"] = "completed"
            todo["actual_time"] = ...
        except Exception as e:
            todo["status"] = "failed"
            todo["error"] = str(e)

        # TODO 완료
        if callback:
            await callback("todo_progress", {"todo": todo})

    state["todo_list"] = todos
    return state
```

### 9.4 성능 고려사항

**Callback 빈도:**
- Step 시작/완료만 전송: 적정 (5-10회/쿼리)
- Step 내부 진행률 전송: 빈번 (50-100회/쿼리)
- 네트워크 부하 고려

**권장:**
- Option B: Step 시작/완료만 (적정)
- Option C: 진행률은 100-200ms throttle 적용

### 9.5 Frontend 상태 관리

**주의:**
- ExecutionProgressPage는 **메시지로 저장**하되 **실시간 업데이트**
- `step_update` 수신 시 해당 메시지의 executionSteps 업데이트
- React state 불변성 유지

---

## 10. 예상 시간 (Option B 기준, 수정됨)

| 단계 | 세부 작업 | 예상 시간 | 비고 |
|------|-----------|----------|------|
| **Backend** | ConnectionManager (메시지 큐잉 포함) | 2시간 | ⬆️ +1시간 |
| | WebSocket Endpoint (resync 포함) | 2시간 | ⬆️ +0.5시간 |
| | MainSupervisorState 수정 (todo_list 추가) | 1시간 | ⬆️ +0.5시간 |
| | process_query_streaming() | 1시간 | 동일 |
| | planning_node 수정 (Interrupt 포함) | 2-3시간 | ⬆️ +1-1.5시간 |
| | execute_teams_node 수정 (TODO 연동) | 2-3시간 | ⬆️ +0.5시간 |
| **Frontend** | WebSocket Client (재연결 강화) | 2-3시간 | ⬆️ +1시간 |
| | chat-interface.tsx 수정 | 2-3시간 | 동일 |
| | TodoListUI 컴포넌트 | 1-2시간 | ⭐ 신규 |
| | 타입 정의 | 1시간 | ⬆️ +0.5시간 |
| **테스트** | 기본 기능 테스트 | 1시간 | 동일 |
| | Interrupt + TODO 수정 테스트 | 2시간 | ⭐ 신규 |
| | 재연결 + State 복원 테스트 | 1-2시간 | ⭐ 신규 |
| | 에러 시나리오 | 1시간 | 동일 |
| **총계** | | **20-27시간** | ⬆️ +8-12시간 |

### 추가 시간 이유:

1. **메시지 큐잉 (+1-2시간)**: 연결 끊김 시 메시지 손실 방지
2. **Interrupt 구현 (+2-3시간)**: LangGraph interrupt + Command 연동
3. **TodoList State 관리 (+1-2시간)**: State 구조 설계 및 노드 수정
4. **TodoListUI (+1-2시간)**: Frontend TODO 표시 및 수정 UI
5. **재연결 State 동기화 (+1-2시간)**: resync 로직 및 테스트
6. **추가 테스트 (+3-4시간)**: Interrupt, TODO, 재연결 시나리오

---

## 11. 체크리스트 (수정됨)

### Backend

#### Phase 1: 기반 구축
- [ ] `ws_manager.py` 생성 (ConnectionManager)
  - [ ] 메시지 큐잉 구현
  - [ ] 재연결 시 큐 flush
- [ ] `chat_api.py`에 `/ws/{session_id}` 엔드포인트 추가
  - [ ] 메시지 수신 루프
  - [ ] interrupt_response 처리
  - [ ] todo_skip 처리
- [ ] `separated_states.py` 수정
  - [ ] `TodoItem` TypedDict 추가
  - [ ] `MainSupervisorState`에 `todo_list` 필드 추가
  - [ ] `_progress_callback` 필드 추가 (total=False)
- [ ] `team_supervisor.py`에 `process_query_streaming()` 추가
  - [ ] Callback 전달
  - [ ] Checkpoint 저장 전 callback 제거

#### Phase 2: LangGraph 노드 수정
- [ ] `planning_node` 수정
  - [ ] `plan_ready` 이벤트 전송
  - [ ] `todo_created` 이벤트 전송
  - [ ] Interrupt 구현 (선택적)
  - [ ] 사용자 수정 반영 로직
- [ ] `execute_teams_node` 수정
  - [ ] `step_update` 이벤트 전송
  - [ ] `todo_progress` 이벤트 전송
  - [ ] TODO 상태 업데이트
  - [ ] Skip 처리
- [ ] 에러 핸들링
  - [ ] WebSocket 연결 해제
  - [ ] Step 실패
  - [ ] Callback Exception

### Frontend

#### Phase 3: WebSocket 클라이언트
- [ ] `lib/ws.ts` 생성 (ChatWSClient)
  - [ ] 연결/해제 관리
  - [ ] 재연결 로직 (exponential backoff)
  - [ ] 메시지 송수신
  - [ ] Interrupt 응답 전송
  - [ ] TODO Skip 요청 전송
- [ ] `types/execution.ts` 업데이트
  - [ ] `TodoItem` 타입 정의
  - [ ] `ExecutionStep` 타입 업데이트
  - [ ] `WSMessage` 타입 확장

#### Phase 4: UI 구현
- [ ] `chat-interface.tsx` 수정
  - [ ] WebSocket 연결 관리
  - [ ] `handleWSMessage` 구현
    - [ ] plan_ready 처리
    - [ ] step_update 처리
    - [ ] todo_created 처리
    - [ ] todo_progress 처리
    - [ ] interrupt_request 처리
  - [ ] ExecutionPlanPage 즉시 표시
  - [ ] ExecutionProgressPage 실시간 업데이트
  - [ ] Interrupt UI (사용자 승인/수정)
- [ ] `components/todo-list.tsx` 생성 (신규)
  - [ ] TODO 리스트 표시
  - [ ] TODO 상태별 색상
  - [ ] Skip 버튼
  - [ ] 진행률 표시

### 테스트

#### Phase 5: 기능 테스트
- [ ] 정상 플로우 (시세 조회)
  - [ ] ExecutionPlanPage 즉시 표시
  - [ ] Step별 실시간 업데이트
  - [ ] TODO 생성 및 진행 상황
- [ ] Interrupt 시나리오
  - [ ] Planning 후 사용자 승인
  - [ ] TODO 수정 (추가/삭제)
  - [ ] 수정된 계획으로 실행
- [ ] TODO Skip 시나리오
  - [ ] 실행 중 Skip 요청
  - [ ] Skip된 TODO 표시
- [ ] 에러 시나리오
  - [ ] Step 실패 처리
  - [ ] WebSocket 연결 끊김 → 재연결
  - [ ] 메시지 큐잉 검증
- [ ] State 복원 시나리오
  - [ ] 브라우저 새로고침
  - [ ] TODO 복원 확인
- [ ] Unclear/Irrelevant intent
- [ ] UI/UX 타이밍 확인

---

---

## 12. SSE vs WebSocket 최종 비교 (사용자 질문 반영)

### 질문: "SSE + HTTP POST 방식도 사용자와 실시간으로 대화하면서 todo list를 수정할 수 있는가?"

#### ✅ **답변: 가능하지만 WebSocket보다 제약이 많음**

| 항목 | SSE + HTTP POST | WebSocket | 결론 |
|------|-----------------|-----------|------|
| **진행 상황 스트리밍** | ✅ SSE로 가능 | ✅ WebSocket으로 가능 | 동일 |
| **Interrupt 응답** | ✅ HTTP POST로 가능 | ✅ WebSocket으로 가능 | 동일 |
| **TODO 실시간 수정** | ⚠️ 가능하지만 지연 (+100-200ms) | ✅ 즉시 가능 | **WebSocket 우세** |
| **작업 중 Skip 요청** | ⚠️ HTTP POST (별도 요청) | ✅ 같은 연결 | **WebSocket 우세** |
| **재연결 자동 처리** | ✅ 브라우저 자동 | ❌ 수동 구현 필요 | SSE 우세 |
| **메시지 순서 보장** | ⚠️ POST는 별도 연결 | ✅ 단일 연결 | **WebSocket 우세** |
| **구현 복잡도** | **낮음** | **중간** | SSE 우세 |
| **Race Condition 위험** | ⚠️ 존재 (동일) | ⚠️ 존재 (동일) | 동일 |

### TodoList 저장 위치에 대한 답변

#### ✅ **TodoList는 MainSupervisorState에 저장해야 함**

**이유:**
1. **LangGraph Checkpoint와 함께 저장**
   - 브라우저 새로고침 시에도 TODO 복원
   - Session 복구 가능

2. **노드에서 직접 접근 가능**
   ```python
   async def execute_teams_node(self, state):
       todos = state["todo_list"]  # State에서 직접 읽기
       for todo in todos:
           if todo["status"] == "pending":
               # 실행
   ```

3. **Interrupt에서 수정 가능**
   ```python
   async def planning_node(self, state):
       state["todo_list"] = [...]  # TODO 생성

       # Interrupt로 사용자에게 수정 요청
       user_response = interrupt({"todos": state["todo_list"]})

       # 수정 반영
       if user_response["action"] == "modify":
           state["todo_list"] = user_response["modified_todos"]
   ```

4. **별도 DB 저장은 비권장**
   - State와 DB 동기화 복잡
   - Checkpoint 복원 시 불일치 가능
   - 실시간 업데이트 어려움

### 최종 권장: WebSocket 방식

**결론:**
- ✅ **WebSocket 유지**
- ✅ **메시지 큐잉 반드시 구현** (연결 끊김 대비)
- ✅ **TodoList는 State에 저장**
- ✅ **LangGraph Interrupt 활용** (사용자 승인/수정)

**이유:**
1. TODO 실시간 수정의 latency가 중요 (100ms vs 200-400ms)
2. 단일 연결로 모든 통신 (진행 상황 + Interrupt + TODO)
3. 메시지 순서 보장 쉬움
4. 추후 확장성 (실시간 협업, 알림)

---

**다음 단계**: Phase 1 Backend 기반 구축 (ConnectionManager 메시지 큐잉부터 시작)
