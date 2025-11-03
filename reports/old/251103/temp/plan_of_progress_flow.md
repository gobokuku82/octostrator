# Progress Flow 실시간 스트리밍 구현 계획서

**작성일**: 2025-10-09
**목표**: 사용자 질문 입력 시 즉시 Progress Flow 표시 및 실시간 업데이트

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

**파일**: `backend/app/api/chat_api.py`

```python
@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest, ...):
    # 1. 세션 검증
    validate_session(request.session_id)

    # 2. Supervisor 싱글톤 가져오기
    supervisor = await get_supervisor(...)

    # 3. 쿼리 처리 (전체 완료까지 대기)
    result = await supervisor.process_query(
        query=request.query,
        session_id=request.session_id
    )  # ← 여기서 모든 작업 완료까지 블로킹 (2-5초)

    # 4. State → Response 변환
    response = state_to_chat_response(result, execution_time)

    # 5. 응답 반환 (모든 작업 완료 후)
    return response
```

**파일**: `backend/app/service_agent/supervisor/team_supervisor.py`

```python
async def process_query(self, query: str, session_id: str) -> Dict[str, Any]:
    # 초기 상태 생성
    initial_state = MainSupervisorState(...)

    # 워크플로우 실행 (전체 완료까지 대기)
    final_state = await self.app.ainvoke(initial_state, config=config)
    #                    ↑
    # LangGraph의 ainvoke()는 모든 노드 실행 완료까지 반환 안 함
    # initialize_node → planning_node → execution_node → aggregation_node
    #                                                      → response_node

    return final_state
```

**LangGraph 워크플로우:**
```
initialize_node (즉시)
    ↓
planning_node (LLM 호출 ~800ms)  ← Planning 완료 시점에 execution_steps 생성
    ↓
execution_node (팀별 실행 2-4초)  ← SearchExecutor, AnalysisExecutor 등 실행
    ↓
aggregation_node (~200ms)
    ↓
response_node (~200ms)
    ↓
[ainvoke() 반환]  ← 이때서야 Frontend로 응답
```

**문제점:**
- `ainvoke()`는 전체 워크플로우 완료까지 반환하지 않음
- Planning 완료 시점(`planning_node` 완료)에 `execution_steps`가 생성되지만, Frontend로 전달 안 됨
- Execution 진행 중 상태를 Frontend로 전달할 방법 없음

---

## 2. SSE 구현 방안

### 2.1 아키텍처 설계

**핵심 아이디어:**
- FastAPI SSE (Server-Sent Events)로 진행 상황을 **스트리밍**
- Planning 완료 시점에 즉시 `plan_ready` 이벤트 전송
- Execution 진행 중 각 step 상태 업데이트 전송
- 최종 완료 시 `complete` 이벤트 전송

**새로운 플로우:**
```
[Frontend]                          [Backend]

질문입력
  ├─ "분석 중..." Placeholder 표시
  └─ SSE 연결 시작 ──────────────▶ /api/v1/chat/stream
                                      │
                                      ├─ status 이벤트: "Planning 시작"
                                      │
                                      ├─ planning_node 실행 (~800ms)
                                      │
  ◀──────── plan_ready 이벤트 ───────┤  execution_steps 생성 완료
  │                                   │
  ├─ ExecutionPlanPage 표시           │
  │                                   │
  └─ 800ms 후 ExecutionProgressPage   ├─ execution_node 실행 시작
                                      │
  ◀──────── step_update 이벤트 ───────┤  Step 1 시작
  │  (step_id: "...", status: "in_progress")
  ├─ Progress UI 업데이트             │
  │                                   │
  ◀──────── step_update 이벤트 ───────┤  Step 1 완료
  │  (step_id: "...", status: "completed")
  ├─ Progress UI 업데이트             │
  │                                   ├─ Step 2 시작...
  │                                   │
  ◀──────── complete 이벤트 ──────────┤  모든 작업 완료
  │  (response: {...})                │
  ├─ Progress 제거                    │
  └─ 답변 표시                        └─ SSE 연결 종료
```

**장점:**
- 사용자는 질문 입력 즉시 피드백 받음 (10ms 이내)
- Planning 완료되면 실제 계획 즉시 표시 (~800ms)
- Execution 진행 중 실시간 상태 확인 가능
- 백엔드 실제 상태와 완벽히 동기화


### 2.2 이벤트 프로토콜 정의

**SSE 이벤트 타입:**

```typescript
// 1. Status 이벤트 (Phase 변경)
{
  event: "status",
  data: {
    phase: "planning" | "executing" | "aggregating" | "responding",
    message: string
  }
}

// 2. Plan Ready 이벤트 (Planning 완료)
{
  event: "plan_ready",
  data: {
    planning_info: {
      intent: string,
      confidence: number,
      execution_steps: ExecutionStep[],
      execution_strategy: string,
      estimated_total_time: number
    }
  }
}

// 3. Step Update 이벤트 (Step 상태 변경)
{
  event: "step_update",
  data: {
    step_id: string,
    status: "pending" | "in_progress" | "completed" | "failed",
    progress_percentage?: number,
    execution_time_ms?: number,
    error?: string
  }
}

// 4. Complete 이벤트 (최종 완료)
{
  event: "complete",
  data: {
    response: {
      type: "answer" | "guidance" | "error",
      answer?: string,
      message?: string
    },
    execution_time_ms: number,
    teams_executed: string[]
  }
}

// 5. Error 이벤트 (에러 발생)
{
  event: "error",
  data: {
    error_code: string,
    message: string,
    details: any
  }
}
```

---

## 3. Backend 구현 상세

### 3.1 의존성 추가

**파일**: `backend/requirements.txt`

```txt
# 기존 의존성...
sse-starlette==2.1.0  # SSE 지원
```

**설치:**
```bash
cd backend
pip install sse-starlette
```


### 3.2 SSE 엔드포인트 생성

**파일**: `backend/app/api/chat_api.py`

```python
from sse_starlette.sse import EventSourceResponse
import json
import asyncio
from typing import AsyncGenerator

# 기존 /api/v1/chat/ 엔드포인트는 유지 (하위 호환성)

@router.post("/stream")
async def chat_stream(
    request: ChatRequest,
    session_mgr: SessionManager = Depends(get_session_manager)
) -> EventSourceResponse:
    """
    채팅 메시지 처리 (SSE 스트리밍)

    실시간으로 진행 상황을 클라이언트로 전송:
    1. status: Planning 시작
    2. plan_ready: Planning 완료 (execution_steps 포함)
    3. step_update: 각 Step 진행 상황
    4. complete: 최종 완료

    Args:
        request: ChatRequest

    Returns:
        EventSourceResponse: SSE 스트림
    """
    # 1. 세션 검증
    if not session_mgr.validate_session(request.session_id):
        logger.warning(f"Invalid or expired session: {request.session_id}")

        async def error_generator():
            yield {
                "event": "error",
                "data": json.dumps({
                    "error_code": "SESSION_NOT_FOUND",
                    "message": f"Session not found: {request.session_id}"
                })
            }

        return EventSourceResponse(error_generator())

    # 2. Supervisor 가져오기
    supervisor = await get_supervisor(enable_checkpointing=request.enable_checkpointing)

    # 3. 이벤트 생성기 정의
    async def event_generator() -> AsyncGenerator[dict, None]:
        try:
            # Step 상태 추적용
            step_status = {}

            # 콜백 함수: Supervisor에서 호출
            async def progress_callback(event_type: str, data: dict):
                if event_type == "status":
                    yield {
                        "event": "status",
                        "data": json.dumps(data)
                    }
                elif event_type == "plan_ready":
                    yield {
                        "event": "plan_ready",
                        "data": json.dumps({"planning_info": data})
                    }
                elif event_type == "step_update":
                    yield {
                        "event": "step_update",
                        "data": json.dumps(data)
                    }

            # Planning 시작 알림
            yield {
                "event": "status",
                "data": json.dumps({
                    "phase": "planning",
                    "message": "질문을 분석하고 실행 계획을 수립하고 있습니다..."
                })
            }

            # Supervisor 스트리밍 실행
            start_time = datetime.now()
            result = await supervisor.process_query_streaming(
                query=request.query,
                session_id=request.session_id,
                callback=progress_callback
            )
            execution_time = (datetime.now() - start_time).total_seconds() * 1000

            # Cleanup
            await supervisor.cleanup()

            # 최종 완료 이벤트
            response_content = result.get("final_response", {})
            yield {
                "event": "complete",
                "data": json.dumps({
                    "response": response_content,
                    "execution_time_ms": int(execution_time),
                    "teams_executed": result.get("completed_teams", [])
                })
            }

        except Exception as e:
            logger.error(f"Streaming error: {e}", exc_info=True)

            # 에러 이벤트
            yield {
                "event": "error",
                "data": json.dumps({
                    "error_code": "PROCESSING_FAILED",
                    "message": "Query processing failed",
                    "details": {"error": str(e)}
                })
            }

            # Cleanup
            try:
                await supervisor.cleanup()
            except:
                pass

    return EventSourceResponse(event_generator())
```


### 3.3 Supervisor 스트리밍 지원

**파일**: `backend/app/service_agent/supervisor/team_supervisor.py`

```python
async def process_query_streaming(
    self,
    query: str,
    session_id: str,
    callback: Callable[[str, dict], Awaitable[None]]
) -> Dict[str, Any]:
    """
    쿼리 처리 (스트리밍 모드)

    진행 상황을 callback으로 실시간 전송:
    - plan_ready: Planning 완료
    - step_update: Step 상태 변경

    Args:
        query: 사용자 쿼리
        session_id: 세션 ID
        callback: 진행 상황 콜백 async 함수

    Returns:
        처리 결과
    """
    logger.info(f"[TeamSupervisor] Streaming query: {query[:100]}...")

    # Checkpointer 초기화
    await self._ensure_checkpointer()

    # 초기 상태 생성
    initial_state = MainSupervisorState(
        query=query,
        session_id=session_id,
        request_id=f"req_{datetime.now().timestamp()}",
        planning_state=None,
        execution_plan=None,
        search_team_state=None,
        document_team_state=None,
        analysis_team_state=None,
        current_phase="",
        active_teams=[],
        completed_teams=[],
        failed_teams=[],
        team_results={},
        aggregated_results={},
        final_response=None,
        start_time=datetime.now(),
        end_time=None,
        total_execution_time=None,
        error_log=[],
        status="initialized"
    )

    # 1. Planning만 먼저 실행
    state = self.initialize_node(initial_state)
    state = await self.planning_node(state)

    # Planning 완료 콜백
    if state.get("planning_state"):
        await callback("plan_ready", {
            "intent": state["planning_state"].get("analyzed_intent", {}).get("intent_type"),
            "confidence": state["planning_state"].get("intent_confidence", 0),
            "execution_steps": state["planning_state"].get("execution_steps", []),
            "execution_strategy": state.get("execution_plan", {}).get("strategy", "sequential"),
            "estimated_total_time": state["planning_state"].get("estimated_total_time", 5)
        })

    # 2. IRRELEVANT/UNCLEAR는 즉시 종료
    intent_type = state.get("planning_state", {}).get("analyzed_intent", {}).get("intent_type")
    if intent_type in ["irrelevant", "unclear"]:
        # 최종 응답만 생성
        state = self.response_node(state)
        return state

    # 3. Execution 단계별 실행
    execution_steps = state.get("planning_state", {}).get("execution_steps", [])

    for step in execution_steps:
        # Step 시작 콜백
        await callback("step_update", {
            "step_id": step["step_id"],
            "status": "in_progress",
            "progress_percentage": 0
        })

        # Step 실행 (실제 로직은 execution_node에서)
        # 여기서는 시뮬레이션
        await asyncio.sleep(0.5)  # 실제로는 팀 실행

        # Step 완료 콜백
        await callback("step_update", {
            "step_id": step["step_id"],
            "status": "completed",
            "progress_percentage": 100
        })

    # 4. 나머지 노드 실행 (aggregation, response)
    state = self.aggregation_node(state)
    state = self.response_node(state)

    return state
```

**참고:** 위 코드는 **간소화된 버전**입니다. 실제로는 `execution_node`를 step별로 분리하거나, LangGraph의 `astream()` API를 활용해야 합니다.


### 3.4 LangGraph astream() 활용 (대안)

**더 나은 방법:** LangGraph의 `astream()` API 사용

```python
async def process_query_streaming(
    self,
    query: str,
    session_id: str,
    callback: Callable[[str, dict], Awaitable[None]]
) -> Dict[str, Any]:
    """LangGraph astream() 사용"""

    initial_state = MainSupervisorState(...)

    config = {
        "configurable": {"thread_id": session_id}
    } if self.checkpointer else {}

    # astream()으로 노드별 결과 스트리밍
    async for chunk in self.app.astream(initial_state, config=config):
        node_name = list(chunk.keys())[0]
        node_output = chunk[node_name]

        # Planning 노드 완료
        if node_name == "planning_node":
            if node_output.get("planning_state"):
                await callback("plan_ready", {
                    "intent": node_output["planning_state"].get("analyzed_intent", {}).get("intent_type"),
                    "execution_steps": node_output["planning_state"].get("execution_steps", []),
                    ...
                })

        # Execution 노드 진행 (각 step)
        elif node_name == "execution_node":
            # execution_node 내부에서 step별 콜백 필요
            pass

    # 최종 상태 반환
    final_state = await self.app.aget_state(config)
    return final_state.values
```

**장점:**
- LangGraph의 기본 스트리밍 메커니즘 활용
- 각 노드 완료 시점마다 자동으로 이벤트 발생
- 코드 간결

**단점:**
- `execution_node` 내부의 step별 진행 상황은 별도 처리 필요

---

## 4. Frontend 구현 상세

### 4.1 SSE Client 생성

**파일**: `frontend/lib/api.ts`

```typescript
// 기존 ChatRequest/ChatResponse 타입 유지

// SSE 이벤트 타입 정의
export interface StreamEvent {
  event: "status" | "plan_ready" | "step_update" | "complete" | "error"
  data: any
}

export const chatAPI = {
  // 기존 함수 유지 (하위 호환성)
  sendMessage: async (data: ChatRequest): Promise<ChatResponse> => {
    const response = await fetch(`${API_BASE_URL}/chat/`, {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(data),
    })

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`)
    }

    return await response.json()
  },

  // 새로운 SSE 스트리밍 함수
  sendMessageStream: async (
    data: ChatRequest,
    onProgress: (event: StreamEvent) => void
  ): Promise<void> => {
    const response = await fetch(`${API_BASE_URL}/chat/stream`, {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(data),
    })

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`)
    }

    const reader = response.body!.getReader()
    const decoder = new TextDecoder()
    let buffer = ""

    try {
      while (true) {
        const {value, done} = await reader.read()
        if (done) break

        buffer += decoder.decode(value, {stream: true})

        // SSE 형식 파싱: "event: xxx\ndata: {...}\n\n"
        const lines = buffer.split("\n\n")
        buffer = lines.pop() || ""  // 마지막 불완전한 줄은 buffer에 유지

        for (const chunk of lines) {
          if (!chunk.trim()) continue

          const eventMatch = chunk.match(/^event:\s*(.+)$/m)
          const dataMatch = chunk.match(/^data:\s*(.+)$/m)

          if (eventMatch && dataMatch) {
            const event = eventMatch[1].trim()
            const data = JSON.parse(dataMatch[1])

            onProgress({
              event: event as StreamEvent["event"],
              data
            })
          }
        }
      }
    } finally {
      reader.releaseLock()
    }
  }
}
```


### 4.2 Chat Interface 수정

**파일**: `frontend/components/chat-interface.tsx`

```typescript
const handleSendMessage = async (content: string) => {
  if (!content.trim() || !sessionId) return

  // 1. 사용자 메시지 추가
  const userMessage: Message = {
    id: Date.now().toString(),
    type: "user",
    content,
    timestamp: new Date(),
  }
  setMessages((prev) => [...prev, userMessage])
  setInputValue("")

  const agentType = detectAgentType(content) as AgentType | null
  const startTime = Date.now()

  // 2. 프로세스 시작
  setProcessState({
    step: "planning",
    agentType,
    message: STEP_MESSAGES.planning,
    startTime
  })

  // 3. 즉시 Placeholder 표시
  const placeholderId = `placeholder-${Date.now()}`
  const placeholderPlan: Message = {
    id: placeholderId,
    type: "execution-plan",
    content: "",
    timestamp: new Date(),
    executionPlan: {
      intent: "분석 중",
      confidence: 0,
      execution_steps: [
        {
          step_id: "placeholder-1",
          agent_name: "planning",
          team: "planning_team",
          description: "AI가 질문을 분석하고 있습니다...",
          priority: 1,
          dependencies: [],
          status: "in_progress",
          progress_percentage: 0
        }
      ],
      execution_strategy: "sequential",
      estimated_total_time: 5
    }
  }
  setMessages((prev) => [...prev, placeholderPlan])

  try {
    let planMessageId: string | null = null
    let progressMessageId: string | null = null
    let isGuidanceResponse = false

    // 4. SSE 스트리밍 시작
    await chatAPI.sendMessageStream(
      {
        query: content,
        session_id: sessionId,
        enable_checkpointing: true
      },
      (event) => {
        // Event: plan_ready (Planning 완료)
        if (event.event === "plan_ready") {
          const planningInfo = event.data.planning_info

          // Placeholder 제거
          setMessages((prev) => prev.filter(m => m.id !== placeholderId))

          // 실제 ExecutionPlanPage 표시
          planMessageId = `execution-plan-${Date.now()}`
          const planMessage: Message = {
            id: planMessageId,
            type: "execution-plan",
            content: "",
            timestamp: new Date(),
            executionPlan: {
              intent: planningInfo.intent || "unknown",
              confidence: planningInfo.confidence || 0,
              execution_steps: planningInfo.execution_steps,
              execution_strategy: planningInfo.execution_strategy || "sequential",
              estimated_total_time: planningInfo.estimated_total_time || 5
            }
          }
          setMessages((prev) => [...prev, planMessage])

          // 800ms 후 ExecutionProgressPage로 전환
          setTimeout(() => {
            progressMessageId = `execution-progress-${Date.now()}`
            const progressMessage: Message = {
              id: progressMessageId,
              type: "execution-progress",
              content: "",
              timestamp: new Date(),
              executionSteps: planningInfo.execution_steps,
              executionPlan: {
                intent: planningInfo.intent || "unknown",
                confidence: planningInfo.confidence || 0,
                execution_steps: planningInfo.execution_steps,
                execution_strategy: planningInfo.execution_strategy || "sequential",
                estimated_total_time: planningInfo.estimated_total_time || 5
              }
            }

            // ExecutionPlan → ExecutionProgress 전환
            setMessages((prev) =>
              prev.filter(m => m.type !== "execution-plan").concat(progressMessage)
            )
          }, 800)
        }

        // Event: step_update (Step 상태 변경)
        else if (event.event === "step_update") {
          const {step_id, status, progress_percentage} = event.data

          // ExecutionProgressPage의 step 상태 업데이트
          setMessages((prev) =>
            prev.map((m) => {
              if (m.type === "execution-progress" && m.executionSteps) {
                return {
                  ...m,
                  executionSteps: m.executionSteps.map((step) =>
                    step.step_id === step_id
                      ? {
                          ...step,
                          status,
                          progress_percentage: progress_percentage || step.progress_percentage
                        }
                      : step
                  )
                }
              }
              return m
            })
          )
        }

        // Event: complete (최종 완료)
        else if (event.event === "complete") {
          const {response, execution_time_ms, teams_executed} = event.data

          isGuidanceResponse = response.type === "guidance"

          // Progress 제거
          setProcessState({
            step: "complete",
            agentType: agentType,
            message: STEP_MESSAGES.complete
          })

          setMessages((prev) =>
            prev.filter(m =>
              m.type !== "execution-plan" && m.type !== "execution-progress"
            )
          )

          // 봇 응답 추가
          const responseContent = response.type === "guidance"
            ? response.message
            : response.answer || response.message || "응답을 받지 못했습니다."

          const botMessage: Message = {
            id: (Date.now() + 1).toString(),
            type: "bot",
            content: responseContent,
            timestamp: new Date(),
          }
          setMessages((prev) => [...prev, botMessage])

          // Agent 타입 감지 후 팝업 표시 (생략 가능)
          // ...

          // Idle 복귀
          const idleDelay = isGuidanceResponse ? 300 : 1500
          setTimeout(() => {
            setProcessState({
              step: "idle",
              agentType: null,
              message: ""
            })
          }, idleDelay)
        }

        // Event: error (에러 발생)
        else if (event.event === "error") {
          // Placeholder 제거
          setMessages((prev) => prev.filter(m => m.id !== placeholderId))

          // 에러 상태 설정
          setProcessState({
            step: "error",
            agentType: agentType,
            message: "오류가 발생했습니다",
            error: event.data.message
          })

          // 에러 메시지 표시
          const errorMessage: Message = {
            id: (Date.now() + 1).toString(),
            type: "bot",
            content: `오류가 발생했습니다: ${event.data.message}`,
            timestamp: new Date(),
          }
          setMessages((prev) => [...prev, errorMessage])

          // 3초 후 idle 복귀
          setTimeout(() => {
            setProcessState({
              step: "idle",
              agentType: null,
              message: ""
            })
          }, 3000)
        }
      }
    )
  } catch (error) {
    // 네트워크 에러 등 처리
    logger.error("SSE error:", error)

    // Placeholder 제거
    setMessages((prev) => prev.filter(m => m.id !== placeholderId))

    // 에러 메시지 표시
    const errorMessage: Message = {
      id: (Date.now() + 1).toString(),
      type: "bot",
      content: `오류가 발생했습니다: ${error instanceof Error ? error.message : "알 수 없는 오류"}`,
      timestamp: new Date(),
    }
    setMessages((prev) => [...prev, errorMessage])

    // idle 복귀
    setTimeout(() => {
      setProcessState({
        step: "idle",
        agentType: null,
        message: ""
      })
    }, 3000)
  }
}
```

---

## 5. 구현 단계

### Step 1: Backend SSE 엔드포인트 (2-3시간)

1. `requirements.txt`에 `sse-starlette` 추가
2. `pip install sse-starlette`
3. `backend/app/api/chat_api.py`에 `/stream` 엔드포인트 추가
4. 간단한 테스트: `curl` 또는 Postman으로 SSE 응답 확인

```bash
# 테스트
curl -N -H "Content-Type: application/json" \
  -d '{"query":"test","session_id":"test-session"}' \
  http://localhost:8000/api/v1/chat/stream
```

### Step 2: Supervisor Streaming 지원 (4-5시간)

1. `team_supervisor.py`에 `process_query_streaming()` 메서드 추가
2. Planning 노드만 먼저 실행하는 로직 구현
3. Callback 방식으로 진행 상황 전달
4. 로그로 각 이벤트 시점 확인

### Step 3: Frontend SSE Client (2-3시간)

1. `frontend/lib/api.ts`에 `sendMessageStream()` 함수 추가
2. SSE 파싱 로직 구현
3. 이벤트 타입별 처리 로직 추가
4. 에러 처리 (네트워크 끊김, 타임아웃 등)

### Step 4: UI 실시간 업데이트 (3-4시간)

1. `chat-interface.tsx`의 `handleSendMessage()` 수정
2. Placeholder 즉시 표시 로직
3. `plan_ready` 이벤트 처리 → ExecutionPlanPage
4. `step_update` 이벤트 처리 → ExecutionProgressPage 업데이트
5. `complete` 이벤트 처리 → 답변 표시

### Step 5: 테스트 및 검증 (2-3시간)

1. 정상 쿼리 플로우 테스트
2. IRRELEVANT 쿼리 플로우 테스트
3. 에러 케이스 테스트 (세션 만료, 네트워크 에러 등)
4. 성능 측정 (응답 시간, 이벤트 지연 등)

**총 예상 시간: 13-18시간**

---

## 6. 코드 예시 (Before/After)

### 6.1 Frontend: Before

```typescript
// Before: 동기 대기
const response = await chatAPI.sendMessage({...})  // 2-5초 블로킹

if (response.planning_info.execution_steps) {
  setMessages([...planMessage])  // 응답 받은 후에야 표시
}
```

### 6.2 Frontend: After

```typescript
// After: 즉시 Placeholder, SSE 스트리밍
setMessages([...placeholderPlan])  // 즉시 표시

await chatAPI.sendMessageStream({...}, (event) => {
  if (event.event === "plan_ready") {
    setMessages([...realPlanMessage])  // Planning 완료 즉시 업데이트
  }
  else if (event.event === "step_update") {
    // 실시간 progress 업데이트
  }
})
```

### 6.3 Backend: Before

```python
# Before: 전체 완료까지 대기
result = await supervisor.process_query(query, session_id)  # 전체 완료까지
response = state_to_chat_response(result)
return response  # 한 번에 반환
```

### 6.4 Backend: After

```python
# After: SSE 스트리밍
async def event_generator():
    # Planning 완료 즉시 전송
    yield {"event": "plan_ready", "data": {...}}

    # Step별 진행 상황 전송
    yield {"event": "step_update", "data": {...}}

    # 최종 완료 전송
    yield {"event": "complete", "data": {...}}

return EventSourceResponse(event_generator())
```

---

## 7. 타임라인 다이어그램

### 7.1 Before (현재)

```
T=0ms     사용자 질문 입력
T=10ms    Frontend: ProcessState "planning" 설정
T=20ms    Frontend: API 호출 시작 (블로킹)

          [2-5초 대기 - 사용자는 아무것도 못 봄]

T=3000ms  Backend: 모든 작업 완료, 응답 반환
T=3010ms  Frontend: 응답 수신
T=3020ms  Frontend: ExecutionPlanPage 표시
T=3820ms  Frontend: ExecutionProgressPage 표시 (800ms 후)
T=4320ms  Frontend: Progress 제거, 답변 표시 (500ms 후)
```

### 7.2 After (SSE)

```
T=0ms     사용자 질문 입력
T=10ms    Frontend: "분석 중..." Placeholder 표시 ✓
T=20ms    Frontend: SSE 연결 시작
T=50ms    Backend: status 이벤트 전송 (Planning 시작)
T=60ms    Frontend: (이미 Placeholder 표시 중)
T=800ms   Backend: Planning 완료, plan_ready 이벤트 전송 ✓
T=820ms   Frontend: Placeholder 제거, ExecutionPlanPage 표시 ✓
T=1620ms  Frontend: ExecutionProgressPage로 전환 (800ms 후) ✓
T=1800ms  Backend: Step 1 시작, step_update 이벤트 전송
T=1820ms  Frontend: Step 1 "in_progress" 표시 ✓
T=3000ms  Backend: Step 1 완료, step_update 이벤트 전송
T=3020ms  Frontend: Step 1 "completed" 표시 ✓
T=3100ms  Backend: Step 2 시작...
...
T=5000ms  Backend: 모든 작업 완료, complete 이벤트 전송
T=5020ms  Frontend: Progress 제거, 답변 표시 ✓
```

**핵심 차이:**
- **Before**: T=10ms ~ T=3010ms (3초) 동안 아무 피드백 없음
- **After**: T=10ms부터 즉시 피드백, T=820ms에 실제 plan 표시

---

## 8. 테스트 시나리오

### 8.1 정상 쿼리 플로우

**입력:** "강남구 아파트 시세 알려줘"

**예상 동작:**
1. T=10ms: "분석 중..." Placeholder
2. T=820ms: ExecutionPlanPage (실제 plan)
   - Intent: "부동산 정보 조회"
   - Confidence: 0.95
   - Steps: [검색, 분석, 응답]
3. T=1620ms: ExecutionProgressPage
   - Step 1 "검색 수행" → in_progress
   - Step 2 "데이터 분석" → pending
4. T=3020ms: Step 1 완료
   - Step 1 → completed
   - Step 2 → in_progress
5. T=5020ms: 답변 표시
   - "강남구 아파트 평균 시세는 10억원입니다..."

### 8.2 IRRELEVANT 쿼리 플로우

**입력:** "ㅁㄴㅇㄹ"

**예상 동작:**
1. T=10ms: "분석 중..." Placeholder
2. T=820ms: Placeholder 제거 (plan_ready 없음)
3. T=1000ms: 답변 즉시 표시
   - "죄송합니다. 질문을 이해하지 못했습니다..."

### 8.3 에러 케이스

**시나리오 1: 세션 만료**
1. T=10ms: Placeholder
2. T=50ms: error 이벤트 수신
3. T=60ms: Placeholder 제거, 에러 메시지
   - "세션이 만료되었습니다. 새로 고침해주세요."

**시나리오 2: 네트워크 에러**
1. T=10ms: Placeholder
2. T=2000ms: SSE 연결 타임아웃
3. T=2010ms: catch 블록 실행, 에러 메시지
   - "네트워크 오류가 발생했습니다."

---

## 9. 성능 목표

### 9.1 현재 성능 (Before)

| 항목 | 시간 | 비고 |
|------|------|------|
| 첫 피드백 | 3000ms | 응답 받을 때까지 대기 |
| Progress 표시 시간 | 1300ms | Plan 800ms + Progress 500ms |
| 총 체감 시간 | 4300ms | 3000 + 1300 |

### 9.2 목표 성능 (After)

| 항목 | 시간 | 개선율 |
|------|------|--------|
| 첫 피드백 | 10ms | **99.7%** ↓ |
| 실제 Plan 표시 | 820ms | Planning 완료 시점 |
| Progress 실시간 업데이트 | N/A | 백엔드와 동기화 |
| 총 체감 시간 | 820ms | **81%** ↓ |

---

## 10. 주의사항 및 제약

### 10.1 SSE 제약

- **단방향 통신**: Server → Client만 가능 (Client → Server는 별도 API 필요)
- **브라우저 지원**: IE 미지원 (Edge, Chrome, Firefox, Safari OK)
- **재연결**: 네트워크 끊김 시 자동 재연결 메커니즘 필요
- **타임아웃**: 일정 시간 후 연결 종료 (보통 30-60초)

### 10.2 Backend 고려사항

- **LangGraph astream() 활용**: 노드별 스트리밍 가능
- **Execution Node 분리**: Step별 실행을 위해 로직 재구성 필요
- **에러 처리**: 각 이벤트마다 try-catch 필요
- **성능**: SSE 연결당 리소스 소비 (동시 접속자 제한 고려)

### 10.3 Frontend 고려사항

- **상태 동기화**: 여러 이벤트가 빠르게 도착할 경우 상태 충돌 가능
- **메모리 관리**: Reader 해제 (`reader.releaseLock()`) 필수
- **재연결 로직**: 네트워크 끊김 시 자동 재시도
- **타임아웃 처리**: 일정 시간 응답 없으면 에러 처리

---

## 11. 대안 (Polling 방식)

SSE 구현이 복잡하다면, **Polling** 방식도 가능:

### Polling 방식

**Backend:**
```python
# 진행 상황 저장용 (Redis 또는 메모리)
progress_store = {}

@router.post("/")
async def chat(request: ChatRequest):
    # 비동기 작업 시작
    task_id = str(uuid4())
    asyncio.create_task(process_in_background(request, task_id))
    return {"task_id": task_id}

@router.get("/status/{task_id}")
async def get_status(task_id: str):
    progress = progress_store.get(task_id, {})
    return progress
```

**Frontend:**
```typescript
const taskId = await chatAPI.sendMessage({...})

const interval = setInterval(async () => {
  const status = await chatAPI.getStatus(taskId)

  if (status.event === "plan_ready") {
    setMessages([...planMessage])
  }

  if (status.event === "complete") {
    clearInterval(interval)
  }
}, 500)  // 500ms마다 polling
```

**장점:**
- 구현 간단
- 브라우저 호환성 높음

**단점:**
- 서버 부하 증가 (500ms마다 요청)
- 실시간성 떨어짐 (최대 500ms 지연)
- 불필요한 요청 많음

---

## 12. 결론

**SSE 방식 권장 이유:**
1. 실시간 피드백으로 사용자 경험 대폭 개선
2. 백엔드 실제 상태와 완벽 동기화
3. 서버 리소스 효율적 (Polling 대비)
4. 현대적인 웹 표준 (WebSocket보다 간단)

**구현 우선순위:**
1. **Phase 1 (필수)**: Backend SSE 엔드포인트 + Frontend SSE Client
2. **Phase 2 (중요)**: Planning 즉시 전송 (`plan_ready` 이벤트)
3. **Phase 3 (선택)**: Step별 실시간 업데이트 (`step_update` 이벤트)

**총 예상 시간: 13-18시간**

구현 시작 전에 이 계획서를 검토하고, 필요 시 수정하겠습니다.
