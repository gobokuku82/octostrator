# 계획서 세부 검토: 간과된 중요 사항 및 수정 필요 항목

**작성일:** 2025-10-22
**목적:** HITL 및 Todo Management 계획서 검토 후 발견된 치명적 갭 및 수정 필요 사항 분석
**심각도:** 🔴 HIGH - 구현 시작 전 반드시 해결 필요

---

## 🚨 발견된 치명적 문제점

### 1. 현재 Planning Node는 이미 WebSocket 이벤트를 전송하고 있다

**문제:**
- 계획서는 "planning_node에 interrupt() 추가" 제안
- **실제 코드:** 이미 복잡한 Planning Node 로직 존재
- **충돌 가능성:** interrupt()가 기존 WebSocket 흐름을 방해할 수 있음

**현재 코드 분석:** ([team_supervisor.py:174-417](backend/app/service_agent/supervisor/team_supervisor.py#L174-L417))

```python
async def planning_node(self, state: MainSupervisorState) -> MainSupervisorState:
    # 1. WebSocket: Planning 시작 알림 (라인 184-194)
    await progress_callback("planning_start", {...})

    # 2. Chat history 조회 (라인 200-207)
    chat_history = await self._get_chat_history(session_id, limit=3)

    # 3. Intent 분석 (라인 210)
    intent_result = await self.planning_agent.analyze_intent(query, context)

    # 4. Long-term Memory 로딩 (라인 235-271)
    tiered_memories = await memory_service.load_tiered_memories(user_id, session_id)

    # 5. IRRELEVANT/UNCLEAR 조기 종료 (라인 273-314)
    if intent_result.intent_type == IntentType.IRRELEVANT:
        # 바로 return (execution_steps = [])

    # 6. 실행 계획 생성 (라인 317)
    execution_plan = await self.planning_agent.create_execution_plan(intent_result)

    # 7. WebSocket: 계획 완료 알림 (라인 400-415)
    await progress_callback("plan_ready", {
        "execution_steps": planning_state["execution_steps"],
        "estimated_total_time": execution_plan.estimated_time,
        ...
    })

    # 8. State 업데이트 및 return
    return state
```

**치명적 문제:**

1. **interrupt() 추가 시 기존 흐름 파괴**
   ```python
   # 계획서 제안 (라인 185):
   user_response = interrupt(value={...})  # ⚠️ 여기서 멈춤!

   # 문제점:
   # - interrupt() 호출 시 그래프가 일시정지
   # - 라인 400-415의 "plan_ready" WebSocket 이벤트가 전송 안 됨
   # - Frontend가 계획을 받지 못함 → UI 업데이트 불가
   ```

2. **Progress Callback 아키텍처 충돌**
   ```python
   # 현재 구조:
   planning_node → progress_callback("plan_ready") → Frontend 즉시 표시

   # 계획서 제안:
   planning_node → interrupt() → 중단 → ... 대기 ... → Command → 재개
                   ↑
                   plan_ready 이벤트 전송 안 됨!
   ```

3. **State 복잡도**
   - 현재 Planning Node는 이미 10+ 필드 업데이트
   - HITL 필드 5개 추가 → 총 15+ 필드 관리 필요
   - State 크기 폭증 → Checkpointer 성능 저하 가능

---

### 2. Progress Callback은 State에 포함되지 않는다

**문제:**
- 계획서: "progress_callback을 State에서 가져온다" 가정
- **실제 코드:** Callback은 **별도 딕셔너리에 관리** (State와 분리)

**현재 아키텍처:** ([team_supervisor.py:65-68](backend/app/service_agent/supervisor/team_supervisor.py#L65-L68))

```python
class TeamBasedSupervisor:
    def __init__(self, ...):
        # ✅ Progress Callbacks - WebSocket 실시간 통신용 (State와 분리)
        # session_id → callback 매핑
        # Callable은 직렬화 불가능하므로 State에 포함하지 않음
        self._progress_callbacks: Dict[str, Callable[[str, dict], Awaitable[None]]] = {}
```

**왜 State와 분리하는가?**

1. **Callback은 직렬화 불가능**
   ```python
   # Checkpoint 저장 시:
   state = {"progress_callback": <function object>}  # ❌ JSON 직렬화 불가!
   checkpointer.save(state)  # TypeError!
   ```

2. **Checkpointer 요구사항**
   - State는 JSON 직렬화 가능해야 함
   - Callback 함수는 직렬화 불가
   - 따라서 State에 포함 불가

3. **현재 해결책**
   ```python
   # 라인 1288-1291
   # Progress Callback 별도 저장 (State와 분리)
   if progress_callback:
       self._progress_callbacks[session_id] = progress_callback

   # 사용 시:
   progress_callback = self._progress_callbacks.get(session_id)
   if progress_callback:
       await progress_callback("plan_ready", {...})
   ```

**계획서 수정 필요:**

```python
# ❌ 계획서 제안 (잘못됨):
progress_callback = state.get("_progress_callback")  # State에 없음!

# ✅ 올바른 방식:
session_id = state.get("session_id")
progress_callback = self._progress_callbacks.get(session_id)
```

---

### 3. Checkpointer는 이미 PostgreSQL AsyncPostgresSaver를 사용한다

**문제:**
- 계획서: Checkpointer 초기화 방법 설명 부족
- **실제 코드:** 복잡한 비동기 컨텍스트 매니저 구조

**현재 구현:** ([team_supervisor.py:1190-1224](backend/app/service_agent/supervisor/team_supervisor.py#L1190-L1224))

```python
async def _ensure_checkpointer(self):
    """Checkpointer 초기화 및 graph 재컴파일 (최초 1회만)"""
    if not self._checkpointer_initialized:
        # 1. AsyncPostgresSaver 생성 (Async Context Manager)
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

        # 2. Context Manager 생성 및 진입
        self._checkpoint_cm = AsyncPostgresSaver.from_conn_string(DB_URI)
        self.checkpointer = await self._checkpoint_cm.__aenter__()

        # 3. 테이블 생성 (checkpoints, checkpoint_blobs, checkpoint_writes)
        await self.checkpointer.setup()

        # 4. Graph 재컴파일 (Checkpointer 포함)
        self._build_graph_with_checkpointer()

        # 5. 플래그 설정
        self._checkpointer_initialized = True
```

**계획서에서 간과한 사항:**

1. **Async Context Manager 필수**
   - `AsyncPostgresSaver`는 일반 객체가 아님
   - `__aenter__()`, `__aexit__()` 호출 필요
   - Cleanup 시 `__aexit__()` 호출 필수 (라인 1376-1390)

2. **Graph 재컴파일 필요**
   - Checkpointer 초기화 후 Graph를 다시 컴파일해야 함
   - 이미 `_build_graph_with_checkpointer()` 메서드 존재 (라인 1225-1255)

3. **Session 관리 복잡도**
   - `session_id` (HTTP/WebSocket ID) vs `chat_session_id` (Chat History ID)
   - `thread_id` = `chat_session_id` (우선) 또는 `session_id` (하위 호환)
   - 계획서는 이 구분 없음

```python
# 라인 1326-1336
if self.checkpointer:
    # ✅ chat_session_id를 thread_id로 사용 (Chat History & State Endpoints)
    # chat_session_id가 없으면 session_id (HTTP) 사용 (하위 호환성)
    thread_id = chat_session_id if chat_session_id else session_id

    config = {
        "configurable": {
            "thread_id": thread_id
        }
    }
```

---

### 4. Graph 구조 변경 시 기존 노드 흐름 파괴

**문제:**
- 계획서: "planning_node에 interrupt() 추가" 제안
- **실제 영향:** 전체 Graph 흐름 변경 필요

**현재 Graph 구조:** ([team_supervisor.py:96-128](backend/app/service_agent/supervisor/team_supervisor.py#L96-L128))

```python
def _build_graph(self):
    workflow = StateGraph(MainSupervisorState)

    # 노드 추가
    workflow.add_node("initialize", self.initialize_node)
    workflow.add_node("planning", self.planning_node)
    workflow.add_node("execute_teams", self.execute_teams_node)
    workflow.add_node("aggregate", self.aggregate_results_node)
    workflow.add_node("generate_response", self.generate_response_node)

    # 엣지 구성
    workflow.add_edge(START, "initialize")
    workflow.add_edge("initialize", "planning")

    # 계획 후 라우팅
    workflow.add_conditional_edges(
        "planning",
        self._route_after_planning,  # ← Intent에 따라 분기
        {
            "execute": "execute_teams",  # RELEVANT 쿼리
            "respond": "generate_response"  # IRRELEVANT/UNCLEAR
        }
    )

    workflow.add_edge("execute_teams", "aggregate")
    workflow.add_edge("aggregate", "generate_response")
    workflow.add_edge("generate_response", END)
```

**interrupt() 추가 시 발생하는 문제:**

1. **Conditional Edge 로직 충돌**
   ```python
   # 현재:
   planning → _route_after_planning() → "execute" or "respond"

   # interrupt() 추가 후:
   planning → interrupt() → 중단
           ↓ (사용자 입력 대기)
   Command → 재개 → _route_after_planning() → ...
           ↑
           어떤 노드에서 재개? (planning? execute_teams?)
   ```

2. **IRRELEVANT 쿼리 처리 불가**
   ```python
   # 현재: IRRELEVANT는 planning에서 조기 종료 → generate_response로 즉시 이동
   if intent_type == "irrelevant":
       # execution_steps = []
       return state  # → _route_after_planning() → "respond"

   # interrupt() 추가 시:
   # IRRELEVANT 쿼리에도 interrupt() 호출?
   # → 사용자에게 "승인하시겠습니까?" 물어봄 (의미 없음!)
   ```

3. **State 복원 문제**
   ```python
   # interrupt() 호출 시 State는 checkpoint에 저장됨
   # Command로 재개 시:
   # - State가 복원됨
   # - 하지만 _progress_callbacks는 복원 안 됨 (별도 딕셔너리)
   # - WebSocket 이벤트 전송 불가!
   ```

---

### 5. WebSocket 핸들러 interrupt_response의 실제 구현 난이도

**문제:**
- 계획서: 간단히 `resume_with_command()` 호출하면 된다고 가정
- **실제 필요 작업:** 훨씬 복잡

**현재 WebSocket 구조:** ([chat_api.py:595-743](backend/app/api/chat_api.py#L595-L743))

```python
@router.websocket("/ws/{session_id}")
async def websocket_chat(
    websocket: WebSocket,
    session_id: str,
    session_mgr: SessionManager = Depends(get_session_manager),
    conn_mgr: ConnectionManager = Depends(get_connection_manager)
):
    # 1. 연결 (라인 642)
    await conn_mgr.connect(session_id, websocket)

    # 2. Supervisor 가져오기 (라인 652)
    supervisor = await get_supervisor(enable_checkpointing=True)

    # 3. 메시지 수신 루프 (라인 656-743)
    while True:
        data = await websocket.receive_json()
        message_type = data.get("type")

        if message_type == "query":
            # 비동기 쿼리 처리 시작 (라인 687-697)
            asyncio.create_task(
                _process_query_async(
                    supervisor=supervisor,
                    query=query,
                    session_id=session_id,
                    ...
                )
            )

        elif message_type == "interrupt_response":
            # TODO: LangGraph interrupt 처리 (추후 구현)  ← 여기!
```

**실제 필요한 복잡도:**

1. **백그라운드 태스크와의 동기화**
   ```python
   # 쿼리 처리는 백그라운드에서 실행 중 (asyncio.create_task)
   # interrupt_response는 메인 루프에서 수신

   # 문제:
   # - 백그라운드 태스크가 interrupt에서 대기 중
   # - interrupt_response를 받으면 어떻게 전달?
   # - asyncio.Queue? asyncio.Event?
   ```

2. **Supervisor 인스턴스 공유**
   ```python
   # 각 WebSocket 연결마다 get_supervisor() 호출
   # → Supervisor 인스턴스가 여러 개?
   # → Checkpointer는 공유되지만 _progress_callbacks는?
   ```

3. **Session ID vs Thread ID 혼동**
   ```python
   # WebSocket session_id (연결 ID) vs
   # LangGraph thread_id (chat_session_id)
   #
   # interrupt_response는 어느 session_id를 사용?
   ```

4. **에러 처리**
   ```python
   # interrupt() 호출 후 사용자가 응답 안 하면?
   # → Timeout 필요
   # → 현재 계획서에 Timeout 로직 없음
   ```

---

### 6. Frontend에서 HITL 통합의 복잡도

**문제:**
- 계획서: Frontend에 RollbackModal만 추가하면 된다고 가정
- **실제 필요:** 계획 승인 UI + Rollback UI 두 가지 모두 필요

**필요한 UI 컴포넌트:**

1. **PlanApprovalModal** (계획서에 누락!)
   ```typescript
   // HITL Phase 1~2에서 필요
   interface PlanApprovalModalProps {
     isOpen: boolean
     executionPlan: ExecutionPlan
     onApprove: () => void
     onModify: (modifiedSteps: ExecutionStep[]) => void
     onReject: () => void
   }
   ```

2. **RollbackModal** (계획서에 포함)
   ```typescript
   // HITL Phase 3에서 필요
   interface RollbackModalProps {
     isOpen: boolean
     checkpoints: Checkpoint[]
     onRollback: (checkpointId: string) => void
     onClose: () => void
   }
   ```

3. **ExecutionStepEditor** (계획서에 누락!)
   ```typescript
   // 계획 수정 시 필요 (action=modify)
   interface ExecutionStepEditorProps {
     steps: ExecutionStep[]
     onChange: (steps: ExecutionStep[]) => void
   }
   ```

**WebSocket 메시지 핸들러 복잡도:**

```typescript
// 현재 Frontend (추정)
ws.onmessage = (event) => {
  const message = JSON.parse(event.data)

  switch (message.type) {
    case "planning_start":
      // ...
    case "plan_ready":
      // ✅ 계획 표시 (현재 구현됨)
    case "execution_start":
      // ...

    // ❌ 계획서에 누락된 핸들러들:
    case "interrupt_requested":
      // PlanApprovalModal 열기?
    case "plan_approval_required":
      // 또 다른 이벤트?
    case "interrupt_acknowledged":
      // Modal 닫기?
  }
}
```

---

## 🔧 수정된 구현 계획

### 수정 원칙

1. **기존 코드 흐름 최대한 보존**
2. **Progress Callback 아키텍처 유지**
3. **IRRELEVANT 조기 종료 로직 보존**
4. **WebSocket 이벤트 구조 일관성 유지**

---

### 수정된 Phase 1: HITL 기초 틀 (현실적 접근)

**목표:** 기존 planning_node 흐름을 유지하면서 HITL 추가

#### 1.1 Planning Node HITL 통합 (수정됨)

**전략:** interrupt()를 별도 노드로 분리

```python
def _build_graph_with_checkpointer(self):
    workflow = StateGraph(MainSupervisorState)

    # 노드 추가
    workflow.add_node("initialize", self.initialize_node)
    workflow.add_node("planning", self.planning_node)
    workflow.add_node("plan_approval", self.plan_approval_node)  # ← 새로 추가!
    workflow.add_node("execute_teams", self.execute_teams_node)
    workflow.add_node("aggregate", self.aggregate_results_node)
    workflow.add_node("generate_response", self.generate_response_node)

    # 엣지 구성
    workflow.add_edge(START, "initialize")
    workflow.add_edge("initialize", "planning")

    # ✅ Planning 후 무조건 plan_approval로 (HITL 적용)
    workflow.add_edge("planning", "plan_approval")

    # ✅ plan_approval 후 라우팅 (기존 로직 이동)
    workflow.add_conditional_edges(
        "plan_approval",
        self._route_after_approval,  # ← 새 라우팅 함수
        {
            "execute": "execute_teams",
            "respond": "generate_response"
        }
    )

    workflow.add_edge("execute_teams", "aggregate")
    workflow.add_edge("aggregate", "generate_response")
    workflow.add_edge("generate_response", END)

    # Compile with checkpointer
    self.app = workflow.compile(checkpointer=self.checkpointer)
```

**새 노드: plan_approval_node**

```python
async def plan_approval_node(self, state: MainSupervisorState) -> MainSupervisorState:
    """
    계획 승인 노드 (HITL)

    Planning Node의 결과를 받아 사용자 승인 요청
    IRRELEVANT/UNCLEAR는 자동 승인 (interrupt 건너뜀)
    """
    logger.info("[TeamSupervisor] Plan approval phase")

    planning_state = state.get("planning_state", {})
    analyzed_intent = planning_state.get("analyzed_intent", {})
    intent_type = analyzed_intent.get("intent_type", "")
    confidence = analyzed_intent.get("confidence", 0.0)

    # ========== IRRELEVANT/UNCLEAR 자동 승인 (interrupt 건너뜀) ==========
    if intent_type == "irrelevant" or (intent_type == "unclear" and confidence < 0.3):
        logger.info(f"⚡ Auto-approving {intent_type} query (no HITL needed)")
        state["hitl_approved"] = True
        state["hitl_action"] = "auto_approve"
        return state

    # ========== RELEVANT 쿼리: 사용자 승인 요청 ==========

    # 1. WebSocket: Interrupt 이벤트 전송
    session_id = state.get("session_id")
    progress_callback = self._progress_callbacks.get(session_id)
    if progress_callback:
        try:
            await progress_callback("plan_approval_required", {
                "message": "다음 실행 계획을 승인하시겠습니까?",
                "execution_plan": state.get("execution_plan", {}),
                "execution_steps": planning_state.get("execution_steps", []),
                "estimated_total_time": planning_state.get("estimated_total_time", 0)
            })
            logger.info("[TeamSupervisor] Sent plan_approval_required via WebSocket")
        except Exception as e:
            logger.error(f"[TeamSupervisor] Failed to send plan_approval_required: {e}")

    # 2. interrupt() 호출 (그래프 일시정지)
    logger.info("⏸️ Requesting plan approval from user (HITL interrupt)")

    user_response = interrupt(
        value={
            "type": "plan_approval",
            "execution_plan": state.get("execution_plan", {}),
            "execution_steps": planning_state.get("execution_steps", [])
        }
    )

    logger.info(f"✅ User response received: {user_response.get('action')}")

    # 3. 사용자 응답 처리
    action = user_response.get("action", "approve")

    if action == "modify":
        # 계획 수정
        modified_steps = user_response.get("modified_steps", [])
        if modified_steps:
            # PlanningState 업데이트
            planning_state["execution_steps"] = modified_steps
            state["planning_state"] = planning_state

            # ExecutionPlan도 업데이트
            if state.get("execution_plan"):
                state["execution_plan"]["steps"] = modified_steps

            logger.info(f"🔧 Plan modified: {len(modified_steps)} steps")

    elif action == "reject":
        # 거부 → 실행 건너뛰고 응답만 생성
        logger.info("❌ Plan rejected by user")
        state["hitl_approved"] = False
        state["hitl_action"] = "reject"
        return state

    # 승인 (approve 또는 modify)
    state["hitl_approved"] = True
    state["hitl_action"] = action
    state["user_response"] = user_response

    return state
```

**새 라우팅 함수: _route_after_approval**

```python
def _route_after_approval(self, state: MainSupervisorState) -> str:
    """Plan approval 후 라우팅"""

    # 거부된 경우 → 바로 응답 생성
    if not state.get("hitl_approved", True):
        logger.info("[TeamSupervisor] Plan rejected, routing to respond")
        return "respond"

    # 기존 로직 재사용
    planning_state = state.get("planning_state")

    # IRRELEVANT/UNCLEAR
    if planning_state:
        analyzed_intent = planning_state.get("analyzed_intent", {})
        intent_type = analyzed_intent.get("intent_type", "")
        confidence = analyzed_intent.get("confidence", 0.0)

        if intent_type == "irrelevant":
            return "respond"

        if intent_type == "unclear" and confidence < 0.3:
            return "respond"

    # 실행 계획 있으면 실행
    if planning_state and planning_state.get("execution_steps"):
        logger.info(f"[TeamSupervisor] Routing to execute - {len(planning_state['execution_steps'])} steps")
        return "execute"

    logger.info("[TeamSupervisor] No execution steps, routing to respond")
    return "respond"
```

**장점:**

1. ✅ **기존 Planning Node 보존** - 수정 최소화
2. ✅ **WebSocket 흐름 유지** - plan_ready 이벤트 정상 전송
3. ✅ **IRRELEVANT 조기 종료 보존** - 자동 승인으로 처리
4. ✅ **Graph 구조 명확** - 각 노드의 책임 분리

---

#### 1.2 State Schema 수정 (간소화)

```python
class MainSupervisorState(TypedDict, total=False):
    # ========== 기존 필드들 (그대로 유지) ==========
    messages: List[BaseMessage]
    planning_state: Optional[PlanningState]
    execution_plan: Optional[Dict[str, Any]]
    # ... (기타 필드들)

    # ========== HITL 필드 추가 (최소화) ==========
    hitl_approved: bool                             # HITL 승인 여부
    hitl_action: Optional[str]                      # "approve" | "modify" | "reject" | "auto_approve"
    user_response: Optional[Dict[str, Any]]         # 사용자 응답 (전체)
```

**변경점:**
- 5개 필드 → 3개 필드로 축소
- `interrupt_requested`, `interrupt_type`, `interrupt_data` 제거 (불필요)

---

#### 1.3 WebSocket Protocol 수정

**추가할 이벤트:**

```python
"""
Server → Client:
    - {"type": "plan_approval_required", "execution_plan": {...}, "execution_steps": [...]}  # 새로 추가
    - {"type": "plan_approved", "action": "approve|modify"}  # 새로 추가 (resume 후)

Client → Server:
    - {"type": "plan_response", "action": "approve|modify|reject", "modified_steps": [...]}  # 새로 추가
"""
```

---

### 수정된 Phase 2: WebSocket 통합 (현실적 접근)

#### 2.1 interrupt_response → plan_response 핸들러

**파일:** `backend/app/api/chat_api.py`

```python
elif message_type == "plan_response":  # ← 이름 변경 (더 명확)
    """
    HITL: 계획 승인/거부/수정 응답 처리

    Expected message:
    {
        "type": "plan_response",
        "data": {
            "action": "approve" | "modify" | "reject",
            "modified_steps": [...],  # action=modify인 경우만
            "session_id": "session-xxx"
        }
    }
    """
    action = data.get("action")
    modified_steps = data.get("modified_steps", [])
    session_id_from_msg = data.get("session_id", session_id)

    logger.info(f"📨 HITL Plan response: {action} for session {session_id_from_msg}")

    try:
        # Command 데이터 구성
        command_data = {
            "action": action
        }

        if action == "modify" and modified_steps:
            command_data["modified_steps"] = modified_steps
            logger.info(f"🔧 User modified {len(modified_steps)} steps")

        # ========== 핵심: resume_with_command() 호출 ==========
        # Supervisor의 resume_with_command() 메서드 필요
        result = await supervisor.resume_with_command(
            session_id=session_id_from_msg,
            command_data=command_data
        )

        # 성공 응답 전송
        await conn_mgr.send_message(session_id, {
            "type": "plan_approved",
            "action": action,
            "status": "resumed",
            "timestamp": datetime.now().isoformat()
        })

        logger.info(f"✅ Graph resumed for session {session_id_from_msg}")

    except Exception as e:
        logger.error(f"❌ Failed to resume graph: {e}", exc_info=True)
        await conn_mgr.send_message(session_id, {
            "type": "error",
            "error": f"Failed to resume: {str(e)}",
            "timestamp": datetime.now().isoformat()
        })
```

---

#### 2.2 resume_with_command() 메서드 (팀 Supervisor에 추가)

**파일:** `backend/app/service_agent/supervisor/team_supervisor.py`
**위치:** 라인 1400 이후 (test 코드 전)

```python
async def resume_with_command(
    self,
    session_id: str,
    command_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Command를 사용하여 interrupt된 그래프 재개

    Args:
        session_id: 세션 ID (HTTP/WebSocket)
        command_data: Command 데이터
            {
                "action": "approve" | "modify" | "reject",
                "modified_steps": [...],  # action=modify인 경우
            }

    Returns:
        그래프 실행 결과

    Raises:
        RuntimeError: Checkpointer 미초기화

    Example:
        >>> result = await supervisor.resume_with_command(
        ...     session_id="session-123",
        ...     command_data={"action": "approve"}
        ... )
    """
    if not self.checkpointer:
        raise RuntimeError("Checkpointer not initialized")

    logger.info(f"▶️ Resuming graph with command for session {session_id}")

    # ========== 중요: chat_session_id 처리 ==========
    # session_id는 HTTP/WebSocket ID일 수 있음
    # LangGraph thread_id는 chat_session_id여야 함
    #
    # 해결책: 현재는 session_id를 thread_id로 사용 (간소화)
    # 추후 chat_session_id 매핑 필요 시 SessionManager 사용

    # 1. Config 생성
    config = {
        "configurable": {
            "thread_id": session_id
        }
    }

    # 2. Command 생성
    from langgraph.types import Command

    # interrupt()가 반환할 값 = command_data
    resume_value = command_data

    command = Command(
        resume=resume_value,
        update={}  # State 업데이트 불필요 (plan_approval_node에서 처리)
    )

    # 3. Progress Callback 재등록 (필수!)
    # interrupt 후 재개 시 callback이 없을 수 있음
    # WebSocket에서 재등록 필요
    #
    # 주의: 여기서는 callback이 없으므로 경고만 출력
    if session_id not in self._progress_callbacks:
        logger.warning(f"⚠️ No progress callback for session {session_id} during resume")

    # 4. Command를 input으로 전달하여 그래프 재개
    try:
        result = await self.app.ainvoke(
            input=command,
            config=config
        )

        logger.info(f"✅ Graph resumed successfully for session {session_id}")
        return result

    except Exception as e:
        logger.error(f"❌ Failed to resume graph: {e}", exc_info=True)
        raise
```

---

### 수정된 Phase 3: Todo Management (Rollback)

**변경 없음** - 이전 계획서 그대로 사용 가능
- RollbackManager 생성
- execute_rollback() 메서드
- RollbackModal UI

**이유:** Phase 1, 2가 제대로 구현되면 Phase 3는 원래 계획대로 진행 가능

---

## 🎯 추가로 고려해야 할 사항

### 1. Progress Callback 재등록 문제

**문제:**
```python
# 쿼리 시작 (WebSocket):
supervisor.process_query_streaming(..., progress_callback=callback)
→ self._progress_callbacks[session_id] = callback

# interrupt() 발생:
→ 그래프 일시정지

# 사용자 응답 (WebSocket):
supervisor.resume_with_command(session_id, command_data)
→ self._progress_callbacks[session_id]가 아직 존재?
```

**해결책:**

```python
# chat_api.py:
# WebSocket 핸들러에서 progress_callback을 한 번 등록하고 계속 유지

async def websocket_chat(...):
    # Supervisor 가져오기
    supervisor = await get_supervisor(enable_checkpointing=True)

    # Progress callback 정의 (한 번만)
    async def progress_callback(event_type: str, event_data: dict):
        await conn_mgr.send_message(session_id, {
            "type": event_type,
            **event_data,
            "timestamp": datetime.now().isoformat()
        })

    # ✅ Callback 등록 (WebSocket 연결 시)
    supervisor._progress_callbacks[session_id] = progress_callback

    try:
        # 메시지 수신 루프
        while True:
            message = await websocket.receive_json()

            if message_type == "query":
                # 쿼리 처리 (callback은 이미 등록됨)
                asyncio.create_task(_process_query_async(...))

            elif message_type == "plan_response":
                # Resume (callback은 여전히 유효)
                await supervisor.resume_with_command(...)

    finally:
        # ✅ Callback 정리 (WebSocket 연결 종료 시)
        if session_id in supervisor._progress_callbacks:
            del supervisor._progress_callbacks[session_id]
```

---

### 2. Session ID vs Thread ID 명확화

**현재 혼동:**
- `session_id` (WebSocket 연결 ID)
- `chat_session_id` (Chat History ID)
- `thread_id` (LangGraph Checkpointer ID)

**권장 해결책:**

```python
# team_supervisor.py:
async def process_query_streaming(
    self,
    query: str,
    http_session_id: str = "default",  # ← 이름 변경
    chat_session_id: Optional[str] = None,
    user_id: Optional[int] = None,
    progress_callback: Optional[Callable] = None
):
    """
    Args:
        http_session_id: HTTP/WebSocket 세션 ID
        chat_session_id: Chat History 세션 ID (thread_id로 사용)
    """

    # thread_id = chat_session_id (우선) or http_session_id (하위 호환)
    thread_id = chat_session_id if chat_session_id else http_session_id

    # Progress callback 저장 (http_session_id 사용)
    if progress_callback:
        self._progress_callbacks[http_session_id] = progress_callback

    # Graph 실행 (thread_id 사용)
    config = {
        "configurable": {
            "thread_id": thread_id
        }
    }

    result = await self.app.ainvoke(initial_state, config=config)
```

---

### 3. Timeout 처리

**문제:** interrupt() 후 사용자가 응답 안 하면?

**해결책:**

```python
# Option 1: LangGraph의 timeout 파라미터 사용 (공식 지원 확인 필요)
config = {
    "configurable": {
        "thread_id": session_id,
        "timeout": 300  # 5분
    }
}

# Option 2: Application 레벨 Timeout
async def plan_approval_node(self, state):
    # ...

    try:
        user_response = interrupt(value={...})
    except asyncio.TimeoutError:
        # 자동 승인 처리
        logger.warning("⏱️ Plan approval timeout, auto-approving")
        user_response = {"action": "approve"}

    # ...
```

---

### 4. Frontend PlanApprovalModal 구현

**필수 컴포넌트 (계획서에 누락):**

```typescript
// frontend/components/ui/plan-approval-modal.tsx
interface PlanApprovalModalProps {
  isOpen: boolean
  executionPlan: ExecutionPlan
  onApprove: () => void
  onModify: (modifiedSteps: ExecutionStep[]) => void
  onReject: () => void
  onClose: () => void
}

export function PlanApprovalModal({...}: PlanApprovalModalProps) {
  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>실행 계획 승인</DialogTitle>
          <DialogDescription>
            다음 단계들을 실행하시겠습니까?
          </DialogDescription>
        </DialogHeader>

        {/* 실행 단계 목록 표시 */}
        <ExecutionStepsList steps={executionPlan.steps} />

        <DialogFooter>
          <Button variant="outline" onClick={onReject}>거부</Button>
          <Button variant="secondary" onClick={() => {
            // 수정 모드 활성화
            setEditMode(true)
          }}>수정</Button>
          <Button onClick={onApprove}>승인</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
```

---

## 📊 수정된 구현 체크리스트

### ✅ Phase 1: HITL 기초 틀 (수정됨, 10-12시간)
- [ ] `separated_states.py`: HITL 필드 3개 추가 (10분)
- [ ] `team_supervisor.py`: plan_approval_node 추가 (3-4시간)
- [ ] `team_supervisor.py`: _route_after_approval() 추가 (30분)
- [ ] `team_supervisor.py`: _build_graph_with_checkpointer() 수정 (1시간)
- [ ] `team_supervisor.py`: resume_with_command() 메서드 추가 (2시간)
- [ ] Phase 1 테스트: interrupt() 및 Command 검증 (2-3시간)
- [ ] 문서화: HITL 아키텍처 문서 작성 (1시간)

### ✅ Phase 2: WebSocket 통합 (수정됨, 5-7시간)
- [ ] `chat_api.py`: plan_response 핸들러 추가 (2시간)
- [ ] `chat_api.py`: Progress callback 재등록 로직 (1-2시간)
- [ ] WebSocket Protocol 문서 업데이트 (30분)
- [ ] Phase 2 테스트: WebSocket HITL 검증 (2-3시간)

### ✅ Phase 3: Frontend (수정됨, 8-10시간)
- [ ] `plan-approval-modal.tsx`: PlanApprovalModal 생성 (3-4시간)
- [ ] `execution-step-editor.tsx`: ExecutionStepEditor 생성 (2-3시간)
- [ ] `chat-interface.tsx`: PlanApprovalModal 통합 (1시간)
- [ ] `usePlanApproval.ts`: Hook 생성 (1시간)
- [ ] Phase 3 테스트: UI 테스트 (1-2시간)

### ✅ Phase 4: Todo Management (변경 없음, 8-12시간)
- [ ] `rollback_manager.py`: RollbackManager 생성 (2-3시간)
- [ ] `team_supervisor.py`: execute_rollback() 추가 (1-2시간)
- [ ] `chat_api.py`: rollback 핸들러 추가 (2시간)
- [ ] `rollback-modal.tsx`: RollbackModal 생성 (2-3시간)
- [ ] `useRollback.ts`: Hook 생성 (1시간)
- [ ] Phase 4 E2E 테스트 (2시간)

**총 예상 시간:** 31-41시간 (5-7일)

---

## 🚀 최종 권장 사항

### 1. 계획서 재작성 필요 여부

**권장:** ✅ **재작성 강력 권장**

**이유:**
1. 현재 계획서는 실제 코드베이스와 괴리가 큼
2. Planning Node 수정 불가 (복잡도 너무 높음)
3. Progress Callback 아키텍처 이해 부족
4. Frontend 필요 컴포넌트 누락

---

### 2. 최우선 해결 과제

1. **Planning Node를 수정하지 말고 별도 노드 추가**
2. **Progress Callback 재등록 문제 해결**
3. **Session ID vs Thread ID 명확화**
4. **Frontend PlanApprovalModal 설계**

---

### 3. 구현 전 반드시 확인할 사항

- [ ] LangGraph `interrupt()` 공식 문서 재확인
- [ ] AsyncPostgresSaver Context Manager 수명 확인
- [ ] Progress Callback Lifecycle 테스트
- [ ] WebSocket 백그라운드 태스크 동기화 방법 검토
- [ ] Frontend 컴포넌트 설계 검토

---

**작성 완료.** 계획서 재작성 후 구현을 시작하세요!
