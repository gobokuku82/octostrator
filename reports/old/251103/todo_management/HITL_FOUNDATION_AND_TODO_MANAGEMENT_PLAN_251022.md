# HITL 기초 구축 및 Todo Management 구현 계획서

**작성일:** 2025-10-22
**목적:** Human-in-the-Loop (HITL) 기초 틀 구축 후 Todo Management 순차 구현
**예상 소요 시간:** 20-28시간 (4-5일)

---

## 🎯 핵심 인사이트

### 문제 인식
**Todo Management는 HITL의 상위 레이어 기능이다.**

```
[현재 상황]
❌ Checkpointer만 존재
❌ HITL 기초 틀 없음
❌ Todo Management 불가

[올바른 구현 순서]
1. ✅ Checkpointer (완료)
2. ⚠️ HITL 기초 틀 (필수 - 현재 없음!)
3. 🎯 Todo Management (HITL 기반)
```

### 의존성 관계

```
Layer 3: Todo Management (Time Travel)
         └── execute_rollback()
         └── RollbackModal
         └── Checkpoint 선택 UI
              ↓ 의존
Layer 2: HITL 기초 틀 (필수!)
         └── interrupt() - 그래프 일시정지
         └── Command - 그래프 재개
         └── WebSocket interrupt_response
              ↓ 의존
Layer 1: Checkpointer (완료)
         └── AsyncPostgresSaver
         └── get_state_history()
         └── update_state()
```

**현재 문제:**
- Layer 1 ✅ 완료
- Layer 2 ❌ **없음** (치명적!)
- Layer 3 ❌ 구현 불가

---

## 📋 재구성된 구현 계획

### Phase 1: HITL 기초 틀 구축 (필수 선행)
**목표:** interrupt() 및 Command 기반 HITL 인프라 구축
**소요 시간:** 8-10시간 (1.5-2일)
**중요도:** ⭐⭐⭐⭐⭐ (Todo Management의 전제 조건)

### Phase 2: HITL WebSocket 통합
**목표:** Frontend와 HITL 통신 구현
**소요 시간:** 4-6시간 (0.5-1일)
**중요도:** ⭐⭐⭐⭐

### Phase 3: Todo Management (Time Travel)
**목표:** Rollback 기능 및 UI 구현
**소요 시간:** 8-12시간 (1.5-2일)
**중요도:** ⭐⭐⭐

---

## 🔧 Phase 1: HITL 기초 틀 구축 (필수)

**목표:** LangGraph의 `interrupt()` 및 `Command` 기반 HITL 구현
**소요 시간:** 8-10시간 (1.5-2일)

### 1.1 LangGraph HITL 개념 이해

**핵심 Primitives:**

```python
from langgraph.types import interrupt, Command

# 1. interrupt() - 그래프 일시정지 및 사용자 입력 요청
user_input = interrupt(
    value={
        "type": "plan_approval",
        "message": "이 계획을 승인하시겠습니까?",
        "plan": execution_plan
    }
)

# 2. Command - 그래프 재개 및 상태 업데이트
# Frontend에서 전송:
# Command(resume=value, update={"approved": True})
```

**작동 방식:**

```
1. Graph 실행 중 interrupt() 호출
   ↓
2. Graph 일시정지 (checkpoint 자동 생성)
   ↓
3. Backend → Frontend: interrupt 이벤트 전송
   ↓
4. 사용자 입력 대기...
   ↓
5. Frontend → Backend: Command 전송
   ↓
6. Graph 재개 (사용자 입력 포함)
```

---

### 1.2 State Schema 수정

**파일:** `backend/app/service_agent/foundation/separated_states.py`
**위치:** 라인 287-349 (MainSupervisorState)

**추가할 필드:**

```python
class MainSupervisorState(TypedDict, total=False):
    # ========== 기존 필드들 (그대로 유지) ==========
    messages: List[BaseMessage]
    planning_state: Optional[PlanningState]
    execution_plan: Optional[Dict[str, Any]]
    # ... (기타 필드들)

    # ========== HITL 필드 추가 ==========
    interrupt_requested: bool                       # Interrupt 요청 플래그
    interrupt_type: Optional[str]                   # Interrupt 타입 (plan_approval, rollback_request 등)
    interrupt_data: Optional[Dict[str, Any]]        # Interrupt 데이터
    user_response: Optional[Dict[str, Any]]         # 사용자 응답
    hitl_pending: bool                              # HITL 대기 상태
```

---

### 1.3 Planning Node에 HITL 추가

**파일:** `backend/app/service_agent/supervisor/team_supervisor.py`
**수정 위치:** Planning 노드 (추정 라인 800-900)

**현재 코드 (추정):**

```python
async def planning_node(state: MainSupervisorState) -> MainSupervisorState:
    """계획 수립 노드"""

    # 1. 쿼리 분석
    query = state.get("messages", [])[-1].content

    # 2. 실행 계획 수립
    execution_plan = await _create_execution_plan(query)

    # 3. State 업데이트
    return {
        "execution_plan": execution_plan,
        "planning_state": {
            "status": "completed",
            "execution_steps": execution_plan["steps"]
        }
    }
```

**수정 후 (HITL 추가):**

```python
from langgraph.types import interrupt

async def planning_node(state: MainSupervisorState) -> MainSupervisorState:
    """계획 수립 노드 (HITL 포함)"""

    # 1. 쿼리 분석
    query = state.get("messages", [])[-1].content

    # 2. 실행 계획 수립
    execution_plan = await _create_execution_plan(query)

    # ========== HITL: 계획 승인 요청 ==========
    logger.info("⏸️ Requesting plan approval from user")

    # interrupt()로 그래프 일시정지 및 사용자 입력 요청
    user_response = interrupt(
        value={
            "type": "plan_approval",
            "message": "다음 실행 계획을 승인하시겠습니까?",
            "execution_plan": execution_plan,
            "execution_steps": execution_plan["steps"],
            "estimated_time": execution_plan.get("estimated_total_time", 0)
        }
    )

    logger.info(f"✅ User response received: {user_response.get('action')}")

    # 3. 사용자 응답 처리
    if user_response.get("action") == "modify":
        # 사용자가 수정한 경우
        modified_steps = user_response.get("modified_steps", execution_plan["steps"])
        execution_plan["steps"] = modified_steps
        logger.info(f"🔧 Plan modified: {len(modified_steps)} steps")
    elif user_response.get("action") == "approve":
        # 승인
        logger.info("✅ Plan approved")
    else:
        # 거부 (현재는 승인으로 처리)
        logger.warning("⚠️ Unknown action, proceeding with original plan")

    # 4. State 업데이트
    return {
        "execution_plan": execution_plan,
        "planning_state": {
            "status": "completed",
            "execution_steps": execution_plan["steps"]
        },
        "user_response": user_response
    }
```

**핵심 변경점:**
1. `interrupt()` 호출 추가
2. 사용자 응답 대기
3. 응답에 따라 계획 수정 가능

---

### 1.4 Graph에 Interrupt 설정

**파일:** `backend/app/service_agent/supervisor/team_supervisor.py`
**위치:** Graph 컴파일 부분 (추정 라인 1200-1250)

**현재 코드 (추정):**

```python
# Graph 컴파일
self.app = workflow.compile(
    checkpointer=self.checkpointer
)
```

**수정 후:**

```python
# Graph 컴파일 (interrupt 활성화)
self.app = workflow.compile(
    checkpointer=self.checkpointer,
    interrupt_before=[],  # 특정 노드 전에 자동 interrupt (필요시)
    interrupt_after=[]    # 특정 노드 후에 자동 interrupt (필요시)
)

logger.info("✅ Graph compiled with HITL support (interrupt enabled)")
```

**참고:**
- `interrupt_before`, `interrupt_after`는 선택 사항
- `interrupt()` 함수로 동적으로 중단 가능 (권장)

---

### 1.5 Command 처리 로직 추가

**파일:** `backend/app/service_agent/supervisor/team_supervisor.py`
**새 메서드 추가:**

```python
async def resume_with_command(
    self,
    session_id: str,
    command_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Command를 사용하여 interrupt된 그래프 재개

    Args:
        session_id: 세션 ID
        command_data: Command 데이터
            {
                "action": "approve" | "modify" | "reject",
                "modified_steps": [...],  # action=modify인 경우
                ...
            }

    Returns:
        그래프 실행 결과

    Example:
        >>> result = await supervisor.resume_with_command(
        ...     session_id="session-123",
        ...     command_data={"action": "approve"}
        ... )
    """
    if not self.checkpointer:
        raise RuntimeError("Checkpointer not initialized")

    logger.info(f"▶️ Resuming graph with command for session {session_id}")

    # 1. Config 생성
    config = {
        "configurable": {
            "thread_id": session_id
        }
    }

    # 2. Command 생성
    from langgraph.types import Command

    # interrupt()가 반환할 값 설정
    resume_value = command_data

    command = Command(
        resume=resume_value,
        update={}  # 필요시 State 업데이트
    )

    # 3. Command를 input으로 전달하여 그래프 재개
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

**핵심:**
- `Command(resume=value)`: interrupt()가 반환할 값
- `ainvoke(input=command)`: Command를 input으로 전달

---

### 1.6 Phase 1 테스트

**테스트 스크립트:** `tests/manual/test_hitl_phase1.py`

```python
"""
Phase 1 테스트: HITL 기초 틀
"""
import asyncio
from app.service_agent.supervisor.team_supervisor import TeamBasedSupervisor

async def test_hitl_basic():
    """HITL 기본 기능 테스트"""

    # 1. Supervisor 초기화
    supervisor = TeamBasedSupervisor()
    await supervisor.setup()

    # 2. 세션 ID
    test_session_id = "test-hitl-001"

    # 3. Config 생성
    config = {
        "configurable": {
            "thread_id": test_session_id
        }
    }

    # 4. 쿼리 시작 (별도 태스크)
    async def run_query():
        """쿼리 실행 (interrupt에서 중단됨)"""
        try:
            result = await supervisor.app.ainvoke(
                input={"messages": [{"role": "user", "content": "서울 강남구 아파트 추천"}]},
                config=config
            )
            print(f"✅ Query completed: {result}")
            return result
        except Exception as e:
            print(f"⏸️ Query interrupted: {e}")
            return None

    # 쿼리 시작 (백그라운드)
    query_task = asyncio.create_task(run_query())

    # 5. Interrupt 대기 (3초)
    await asyncio.sleep(3)

    print("\n📋 Checking for interrupts...")

    # 6. State 확인 (interrupt 발생 확인)
    state_snapshot = supervisor.app.get_state(config)
    print(f"Current node: {state_snapshot.next}")  # ('__interrupt__',) 예상
    print(f"Interrupt tasks: {state_snapshot.tasks}")

    # 7. Command로 재개
    print("\n▶️ Resuming with Command...")

    from langgraph.types import Command

    result = await supervisor.resume_with_command(
        session_id=test_session_id,
        command_data={
            "action": "approve"
        }
    )

    print(f"\n✅ Final result: {result.get('final_response', 'N/A')}")

    # 8. 백그라운드 태스크 정리
    await query_task

if __name__ == "__main__":
    asyncio.run(test_hitl_basic())
```

**실행:**
```bash
cd backend
python -m tests.manual.test_hitl_phase1
```

**기대 결과:**
```
⏸️ Query interrupted: ...
📋 Checking for interrupts...
Current node: ('__interrupt__',)
Interrupt tasks: [...]

▶️ Resuming with Command...
✅ Plan approved
✅ Final result: {...}
```

---

## 🔌 Phase 2: HITL WebSocket 통합

**목표:** Frontend와 HITL 통신 구현
**소요 시간:** 4-6시간 (0.5-1일)

### 2.1 WebSocket interrupt_response 핸들러 완성

**파일:** `backend/app/api/chat_api.py`
**위치:** 라인 700-706 (현재 TODO 상태)

**현재 코드:**
```python
elif message_type == "interrupt_response":
    # TODO: LangGraph interrupt 처리 (추후 구현)
    action = data.get("action")  # "approve" or "modify"
    modified_todos = data.get("modified_todos", [])

    logger.info(f"Interrupt response: {action}")
    # 현재는 로그만, 추후 LangGraph Command로 전달
```

**수정 후:**
```python
elif message_type == "interrupt_response":
    """
    HITL: 사용자의 Interrupt 응답 처리

    Expected message:
    {
        "type": "interrupt_response",
        "data": {
            "action": "approve" | "modify" | "reject",
            "modified_steps": [...],  # action=modify인 경우
            "session_id": "session-xxx"
        }
    }
    """
    action = data.get("action")
    modified_steps = data.get("modified_steps", [])
    session_id_from_msg = data.get("session_id", session_id)

    logger.info(f"📨 HITL Interrupt response: {action} for session {session_id_from_msg}")

    try:
        # Command 데이터 구성
        command_data = {
            "action": action
        }

        if action == "modify" and modified_steps:
            command_data["modified_steps"] = modified_steps
            logger.info(f"🔧 User modified {len(modified_steps)} steps")

        # Supervisor의 resume_with_command() 호출
        result = await supervisor.resume_with_command(
            session_id=session_id_from_msg,
            command_data=command_data
        )

        # 성공 응답 전송
        await conn_mgr.send_message(session_id, {
            "type": "interrupt_acknowledged",
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

### 2.2 Interrupt 이벤트 자동 전송

**문제:** `interrupt()`가 호출될 때 Frontend에 자동으로 알려야 함

**해결책:** Progress callback 활용

**파일:** `backend/app/service_agent/supervisor/team_supervisor.py`
**수정 위치:** planning_node 또는 progress callback 등록 부분

**Interrupt 발생 시 이벤트 전송:**

```python
async def planning_node(state: MainSupervisorState) -> MainSupervisorState:
    """계획 수립 노드 (HITL + WebSocket 이벤트)"""

    # ... (기존 코드) ...

    # Progress callback을 통해 Frontend에 알림
    progress_callback = state.get("_progress_callback")
    if progress_callback:
        await progress_callback("plan_ready", {
            "execution_plan": execution_plan,
            "execution_steps": execution_plan["steps"],
            "requires_approval": True  # HITL 플래그
        })

    # interrupt() 호출
    user_response = interrupt(value={
        "type": "plan_approval",
        "message": "다음 실행 계획을 승인하시겠습니까?",
        "execution_plan": execution_plan,
        "execution_steps": execution_plan["steps"]
    })

    # ... (나머지 코드) ...
```

**또는 별도 이벤트 전송:**

```python
# interrupt() 호출 직전
if progress_callback:
    await progress_callback("interrupt_requested", {
        "type": "plan_approval",
        "interrupt_data": {
            "execution_plan": execution_plan,
            "execution_steps": execution_plan["steps"]
        }
    })
```

---

### 2.3 WebSocket Protocol 업데이트

**파일:** `backend/app/api/chat_api.py`
**위치:** 라인 605-622 (WebSocket docstring)

**추가할 Protocol:**

```python
"""
실시간 채팅 WebSocket 엔드포인트

Protocol:
    Client → Server:
        - {"type": "query", "query": "...", "enable_checkpointing": true}
        - {"type": "interrupt_response", "action": "approve|modify|reject", "modified_steps": [...]}  # 추가
        - {"type": "get_checkpoints", "limit": 20}
        - {"type": "rollback_request", "target_checkpoint_id": "..."}

    Server → Client:
        - {"type": "connected", "session_id": "..."}
        - {"type": "planning_start", ...}
        - {"type": "plan_ready", "execution_steps": [...], "requires_approval": true}  # 수정
        - {"type": "interrupt_requested", "interrupt_data": {...}}                    # 추가
        - {"type": "interrupt_acknowledged", "action": "...", "status": "resumed"}    # 추가
        - {"type": "checkpoints_list", "checkpoints": [...]}
        - {"type": "rollback_start", ...}
        - {"type": "rollback_complete", ...}
        - {"type": "final_response", "response": {...}}
        - {"type": "error", "error": "..."}
"""
```

---

### 2.4 Phase 2 테스트

**테스트:** `tests/manual/test_hitl_websocket_phase2.py`

```python
"""
Phase 2 테스트: HITL WebSocket 통합
"""
import asyncio
import websockets
import json

async def test_hitl_websocket():
    """HITL WebSocket 테스트"""

    uri = "ws://localhost:8000/api/v1/chat/ws/test-hitl-002"

    async with websockets.connect(uri) as websocket:
        # 1. 연결 확인
        response = await websocket.recv()
        print(f"📡 Connected: {json.loads(response).get('type')}")

        # 2. 쿼리 전송
        await websocket.send(json.dumps({
            "type": "query",
            "query": "서울 강남구 아파트 추천",
            "enable_checkpointing": True
        }))

        print("\n⏳ Waiting for interrupt...")

        # 3. 메시지 수신 루프
        interrupt_received = False

        while True:
            response = await websocket.recv()
            message = json.loads(response)
            msg_type = message.get("type")

            print(f"📨 Received: {msg_type}")

            if msg_type == "plan_ready" and message.get("requires_approval"):
                print("\n⏸️ Plan approval required!")
                print(f"Steps: {len(message.get('execution_steps', []))}")

                # 4. Interrupt 응답 전송 (승인)
                print("✅ Sending approval...")
                await websocket.send(json.dumps({
                    "type": "interrupt_response",
                    "data": {
                        "action": "approve",
                        "session_id": "test-hitl-002"
                    }
                }))

                interrupt_received = True

            elif msg_type == "interrupt_acknowledged":
                print(f"✅ Interrupt acknowledged: {message.get('status')}")

            elif msg_type == "final_response":
                print(f"\n✅ Final response received!")
                break

            elif msg_type == "error":
                print(f"❌ Error: {message.get('error')}")
                break

        if not interrupt_received:
            print("⚠️ Warning: Interrupt was not triggered")

if __name__ == "__main__":
    asyncio.run(test_hitl_websocket())
```

**실행:**
```bash
# 1. Backend 시작
cd backend
uvicorn app.main:app --reload

# 2. 테스트 실행
python -m tests.manual.test_hitl_websocket_phase2
```

**기대 결과:**
```
📡 Connected: connected

⏳ Waiting for interrupt...
📨 Received: planning_start
📨 Received: plan_ready

⏸️ Plan approval required!
Steps: 3
✅ Sending approval...

📨 Received: interrupt_acknowledged
✅ Interrupt acknowledged: resumed

📨 Received: execution_start
📨 Received: step_start
📨 Received: step_complete
...
📨 Received: final_response

✅ Final response received!
```

---

## 🎯 Phase 3: Todo Management (Time Travel)

**목표:** HITL 기반 Rollback 기능 구현
**소요 시간:** 8-12시간 (1.5-2일)
**전제 조건:** Phase 1, 2 완료 필수

### 3.1 RollbackManager 생성

**(이전 계획서의 1.2절과 동일)**

**파일:** `backend/app/service_agent/cognitive_agents/rollback_manager.py`

```python
"""
Rollback Manager - Time Travel 및 Checkpoint 관리
"""
# ... (이전 계획서의 코드 사용)
```

---

### 3.2 Rollback with HITL

**개념:** Rollback 시에도 HITL 활용

```python
async def rollback_node(state: MainSupervisorState) -> MainSupervisorState:
    """
    Rollback 노드 (HITL 포함)

    사용자가 Rollback 요청 시:
    1. 사용 가능한 Checkpoint 목록 표시 (interrupt)
    2. 사용자가 Checkpoint 선택
    3. 해당 Checkpoint로 되돌아가서 재실행
    """

    # 1. Checkpoint 목록 조회
    rollback_manager = RollbackManager(checkpointer)
    checkpoints = await rollback_manager.get_available_checkpoints(
        session_id=state["session_id"]
    )

    # 2. interrupt()로 사용자에게 선택 요청
    user_choice = interrupt(
        value={
            "type": "rollback_selection",
            "message": "어느 단계로 돌아가시겠습니까?",
            "available_checkpoints": checkpoints
        }
    )

    # 3. 선택된 Checkpoint로 Rollback
    target_checkpoint_id = user_choice.get("checkpoint_id")

    # ... Rollback 실행 ...
```

---

### 3.3 Frontend: RollbackModal + HITL 통합

**(이전 계획서의 3.1~3.3절 코드 사용, 단 HITL 통합 강조)**

**핵심 변경:**
- RollbackModal이 `interrupt_requested` (type=rollback_selection) 수신 시 자동 열림
- 사용자 선택 → `interrupt_response` 전송

---

### 3.4 Phase 3 통합 테스트

**E2E 테스트:**
1. 쿼리 전송
2. 계획 승인 (HITL)
3. 실행 완료
4. Rollback 요청
5. Checkpoint 선택 (HITL)
6. Rollback 실행
7. 최종 결과 확인

---

## 📊 전체 구현 체크리스트

### ✅ Phase 1: HITL 기초 틀 (8-10시간)
- [ ] `separated_states.py`: HITL 필드 추가 (10분)
- [ ] `team_supervisor.py`: planning_node에 interrupt() 추가 (2-3시간)
- [ ] `team_supervisor.py`: resume_with_command() 메서드 추가 (1-2시간)
- [ ] Graph interrupt 설정 (30분)
- [ ] Phase 1 테스트: interrupt() 및 Command 검증 (1-2시간)
- [ ] 문서화: HITL 사용 가이드 작성 (1시간)

### ✅ Phase 2: HITL WebSocket 통합 (4-6시간)
- [ ] `chat_api.py`: interrupt_response 핸들러 완성 (2시간)
- [ ] `team_supervisor.py`: Interrupt 이벤트 자동 전송 로직 (1-2시간)
- [ ] WebSocket Protocol 문서 업데이트 (30분)
- [ ] Phase 2 테스트: WebSocket HITL 검증 (1-2시간)

### ✅ Phase 3: Todo Management (8-12시간)
- [ ] `rollback_manager.py`: RollbackManager 클래스 생성 (2-3시간)
- [ ] `team_supervisor.py`: execute_rollback() 메서드 추가 (1-2시간)
- [ ] `chat_api.py`: get_checkpoints, rollback_request 핸들러 (2시간)
- [ ] Frontend: RollbackModal 컴포넌트 (2-3시간)
- [ ] Frontend: useRollback Hook (1시간)
- [ ] Frontend: ChatInterface 통합 (1시간)
- [ ] Phase 3 E2E 테스트 (2시간)

### ✅ 최종 검증 (2-3시간)
- [ ] 전체 HITL 흐름 E2E 테스트
- [ ] Rollback + HITL 통합 테스트
- [ ] 에러 시나리오 테스트 (네트워크 끊김, timeout 등)
- [ ] 성능 테스트 (checkpoint 조회 속도 등)
- [ ] 문서 최종 업데이트

---

## 🚀 구현 시작하기

### 순서 (반드시 순차 진행!)

```
Day 1 (8-10시간):
├── 09:00-10:00  Phase 1.1-1.2: State 수정 + interrupt() 개념 이해
├── 10:00-13:00  Phase 1.3: planning_node에 interrupt() 추가
├── 14:00-16:00  Phase 1.4-1.5: resume_with_command() 구현
└── 16:00-18:00  Phase 1.6: 테스트 및 디버깅

Day 2 (4-6시간):
├── 09:00-11:00  Phase 2.1: interrupt_response 핸들러 완성
├── 11:00-13:00  Phase 2.2: Interrupt 이벤트 자동 전송
└── 14:00-16:00  Phase 2.4: WebSocket 테스트

Day 3 (4-6시간):
├── 09:00-12:00  Phase 3.1: RollbackManager 구현
└── 14:00-17:00  Phase 3.2: execute_rollback() + WebSocket

Day 4 (4-6시간):
├── 09:00-12:00  Phase 3.3: Frontend 구현
└── 14:00-17:00  Phase 3.4: E2E 테스트

Day 5 (2-3시간):
└── 09:00-12:00  최종 검증 및 문서화
```

### 주의사항

⚠️ **절대 Phase를 건너뛰지 마세요!**

```
❌ 잘못된 순서:
Phase 1 건너뛰고 Phase 3 구현
→ Rollback은 되지만 HITL 없어서 사용자 입력 불가

✅ 올바른 순서:
Phase 1 (HITL 기초) → Phase 2 (WebSocket) → Phase 3 (Rollback)
→ 모든 기능 정상 작동
```

---

## 📚 참고 문서

### LangGraph 공식 문서
- **Human-in-the-Loop**: https://langchain-ai.github.io/langgraph/concepts/human_in_the_loop/
- **interrupt()**: https://langchain-ai.github.io/langgraph/how-tos/human_in_the_loop/add-human-in-the-loop/
- **Command**: https://langchain-ai.github.io/langgraph/reference/types/#command
- **Time Travel**: https://langchain-ai.github.io/langgraph/how-tos/time-travel/

### 내부 문서
- **Checkpointer 가이드**: `../human_in_the_loop/CHECKPOINTER_COMPLETE_GUIDE.md`
- **LangGraph History**: `../human_in_the_loop/LANGGRAPH_CHECKPOINTER_HISTORY.md`
- **이전 계획**: `IMPLEMENTATION_GAP_ANALYSIS_251022.md`

---

## 🎓 핵심 개념 정리

### HITL (Human-in-the-Loop) 이란?

**정의:**
AI 시스템이 자동으로 실행되는 중간에 사람의 입력/승인을 받는 메커니즘

**LangGraph에서의 구현:**
```python
# 1. interrupt() - 그래프 멈춤
user_input = interrupt(value={"message": "승인하시겠습니까?"})

# 2. 사용자 입력 대기...

# 3. Command - 그래프 재개
# Command(resume=user_input)
```

**실제 사용 예:**
1. **계획 승인**: AI가 수립한 계획을 사용자가 검토/수정
2. **Rollback 선택**: 되돌아갈 체크포인트를 사용자가 선택
3. **중요 결정**: 금융 거래, 의료 진단 등 사람의 판단 필요

### Todo Management vs HITL

| 구분 | HITL (기초 틀) | Todo Management (상위 기능) |
|-----|---------------|---------------------------|
| **역할** | 그래프 일시정지/재개 | 특정 시점으로 되돌아가기 |
| **Primitives** | `interrupt()`, `Command` | `get_state_history()`, `update_state()` |
| **사용 예** | 계획 승인, 확인 요청 | 이전 단계 재실행 |
| **의존성** | Checkpointer | Checkpointer + HITL |

---

**작성 완료.** Phase 1 (HITL 기초 틀)부터 시작하세요!
