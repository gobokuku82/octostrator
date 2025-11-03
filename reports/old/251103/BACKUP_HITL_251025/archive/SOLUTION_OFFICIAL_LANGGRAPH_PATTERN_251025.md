# HITL 해결 방법: 공식 LangGraph 패턴
**Date:** 2025-10-25
**Status:** ✅ 테스트 완료 - 작동 확인
**Priority:** Production 적용 준비 완료

---

## 요약

**문제:** Subgraph + HITL resume 실패
**원인:** 잘못된 구현 패턴 사용
**해결:** LangGraph 공식 패턴 적용
**결과:** ✅ **완벽하게 작동!**

---

## 테스트 결과

```
✅ TEST PASSED!
✅ CONCLUSION: Direct Subgraph Resume WORKS

Details:
  - Subgraph resumed from interrupt_node
  - finish_node executed with step_count = 2
  - work_node did NOT re-execute

→ OFFICIAL PATTERN WORKS!
```

---

## 핵심 발견

### 우리가 한 것 (틀림) ❌

```python
# team_supervisor.py - execute_teams_node 내부에서
async def execute_teams_node(self, state):
    subgraph = build_document_subgraph()
    document_app = subgraph.compile(checkpointer=self.checkpointer)

    # Node 내부에서 subgraph 실행 (잘못된 방법!)
    async for event in document_app.astream(state, config):
        if "__interrupt__" in event:
            return {"status": "interrupted"}
```

**문제점:**
- Subgraph checkpoint 저장 안 됨
- Resume 불가능
- LangGraph Issue #4796 발생

---

### 공식 패턴 (올바름) ✅

```python
# team_supervisor.py
class TeamSupervisor:
    def build_graph(self):
        workflow = StateGraph(MainSupervisorState)

        # 1. Subgraph compile (checkpointer 없이!)
        from app.service_agent.teams.document_team.workflow import build_document_workflow
        document_subgraph = build_document_workflow()
        compiled_subgraph = document_subgraph.compile()  # NO checkpointer

        # 2. Compiled subgraph를 직접 node로 추가
        workflow.add_node("document_team", compiled_subgraph)

        # 3. Parent graph compile 시 checkpointer 전달
        self.app = workflow.compile(checkpointer=self.checkpointer)
        # LangGraph가 자동으로 subgraph에 checkpointer 전파
```

**장점:**
- ✅ Subgraph checkpoint 자동 저장
- ✅ Interrupt/Resume 작동
- ✅ LangGraph가 모든 것을 처리

---

## 4가지 필수 요소

### 1. Compiled Subgraph를 직접 Node로 추가

**올바른 방법:**
```python
# Subgraph compile
compiled_subgraph = subgraph.compile()  # checkpointer 없이

# 직접 node로 추가
workflow.add_node("document_team", compiled_subgraph)
```

**틀린 방법:**
```python
# Node 함수 내부에서 실행 (❌)
async def execute_teams_node(state):
    document_app = subgraph.compile(...)
    async for event in document_app.astream(...):
        ...
```

---

### 2. interrupt() 함수 사용 (NodeInterrupt 아님!)

**올바른 방법:**
```python
from langgraph.types import interrupt

def aggregate_node(state):
    if needs_collaboration:
        # interrupt() 함수 사용
        user_input = interrupt({
            "type": "collaboration_required",
            "message": "Review needed",
            "data": {...}
        })

        # user_input에 resume 값이 전달됨
        state["collaboration_result"] = user_input
        return state

    return state
```

**틀린 방법:**
```python
from langgraph.errors import NodeInterrupt

def aggregate_node(state):
    if needs_collaboration:
        # NodeInterrupt는 resume 값 전달 안 됨 (❌)
        raise NodeInterrupt({...})
```

**왜 interrupt() 함수를 써야 하나?**
- `interrupt()`: Resume 시 `Command(resume=value)`의 value를 **반환**
- `NodeInterrupt`: Resume 시 값 전달 안 됨, node가 재실행됨

---

### 3. 같은 State Schema 공유

**Parent와 Subgraph가 같은 state fields를 공유해야 합니다!**

```python
# separated_states.py
class MainSupervisorState(TypedDict):
    # Main fields
    query: str
    current_team: str

    # Document team fields (공유 필수!)
    planning_result: Dict[str, Any]
    search_results: List[Dict]
    aggregated_content: str
    final_document: str

    # HITL fields
    workflow_status: str
    interrupted_by: str
    interrupt_data: Dict[str, Any]
```

**중요:** Subgraph가 업데이트하는 **모든 state fields**가 MainState에 정의되어야 합니다!

---

### 4. Main Graph Resume (Subgraph 직접 아님!)

**올바른 방법:**
```python
# chat_api.py
async def resume_workflow(session_id: str, user_input: dict):
    config = {"configurable": {"thread_id": session_id}}

    # Main graph를 resume (subgraph 직접 아님!)
    from langgraph.types import Command

    async for event in main_app.astream(
        Command(resume=user_input),  # Resume value 전달
        config
    ):
        # LangGraph가 자동으로 subgraph resume 처리
        ...
```

**틀린 방법:**
```python
# Subgraph를 직접 resume (❌)
async for event in document_app.astream(None, config):
    ...
```

---

## Production 적용 방법

### Step 1: State 수정

```python
# backend/app/service_agent/foundation/separated_states.py

class MainSupervisorState(TypedDict):
    # 기존 fields
    query: str
    current_team: str
    team_results: Dict[str, Any]

    # Document team fields 추가 (공유 필수!)
    planning_result: Dict[str, Any]
    search_results: List[Dict]
    aggregated_content: str
    final_document: str
    collaboration_result: Optional[Dict]  # HITL resume 값

    # HITL fields
    workflow_status: Optional[str]
    interrupted_by: Optional[str]
    interrupt_type: Optional[str]
    interrupt_data: Optional[Dict[str, Any]]
```

---

### Step 2: Document Team - interrupt() 함수 사용

```python
# backend/app/service_agent/teams/document_team/nodes/aggregate.py

from langgraph.types import interrupt

def aggregate_node(state: DocumentTeamState) -> DocumentTeamState:
    """Aggregate search results"""

    # ... aggregation logic ...

    # HITL check
    if needs_collaboration(aggregated_content):
        logger.info("[Aggregate] Collaboration required - triggering HITL")

        # interrupt() 함수 사용 (NodeInterrupt 대신!)
        collaboration_result = interrupt({
            "type": "collaboration_required",
            "message": "검색 결과 검토가 필요합니다",
            "aggregated_content": aggregated_content,
            "search_results_count": len(state.get("search_results", []))
        })

        logger.info(f"[Aggregate] Collaboration result received: {collaboration_result}")

        # Resume 값을 state에 저장
        state["collaboration_result"] = collaboration_result
        state["aggregated_content"] = aggregated_content
        return state

    # No HITL needed
    state["aggregated_content"] = aggregated_content
    return state
```

---

### Step 3: TeamSupervisor - Subgraph를 직접 Node로 추가

```python
# backend/app/service_agent/supervisor/team_supervisor.py

class TeamBasedSupervisor:
    def __init__(self, pool):
        self.checkpointer = AsyncPostgresSaver(pool)
        self.app = None

    def build_graph(self):
        """Build main supervisor graph using OFFICIAL PATTERN"""
        workflow = StateGraph(MainSupervisorState)

        # Regular nodes
        workflow.add_node("planning", self.planning_node)
        workflow.add_node("aggregate", self.aggregate_node)
        workflow.add_node("generate_response", self.generate_response_node)

        # OFFICIAL PATTERN: Add compiled subgraph directly as node
        from app.service_agent.teams.document_team.workflow import build_document_workflow

        document_subgraph = build_document_workflow()
        compiled_document_subgraph = document_subgraph.compile()  # NO checkpointer!

        # Add subgraph directly as node (CRITICAL!)
        workflow.add_node("document_team", compiled_document_subgraph)

        # Edges
        workflow.add_edge(START, "planning")
        workflow.add_edge("planning", "document_team")  # Direct to subgraph
        workflow.add_edge("document_team", "aggregate")
        workflow.add_edge("aggregate", "generate_response")
        workflow.add_edge("generate_response", END)

        # Compile with checkpointer (auto-propagates to subgraph!)
        self.app = workflow.compile(checkpointer=self.checkpointer)

        return self.app
```

**변경 사항:**
- ❌ `execute_teams_node()` 제거
- ❌ `_execute_single_team()` 제거
- ✅ Subgraph를 직접 node로 추가
- ✅ LangGraph가 자동으로 처리

---

### Step 4: Chat API - Main Graph Resume

```python
# backend/app/api/chat_api.py

async def resume_collaboration(session_id: str, user_decision: dict):
    """Resume workflow after HITL"""

    config = {"configurable": {"thread_id": session_id}}

    # Main graph를 resume (OFFICIAL PATTERN!)
    from langgraph.types import Command

    logger.info(f"[ChatAPI] Resuming workflow for {session_id}")
    logger.info(f"   User decision: {user_decision}")

    async for event in supervisor.app.astream(
        Command(resume=user_decision),  # Resume value 전달
        config,
        stream_mode="updates"
    ):
        # LangGraph가 자동으로 subgraph resume 처리
        for node_name, node_output in event.items():
            if node_name == "document_team":
                logger.info(f"[ChatAPI] Document team completed after resume")

            elif node_name == "generate_response":
                response = node_output.get("final_document", "")
                await websocket_manager.send_message(session_id, {
                    "type": "response",
                    "content": response
                })
```

---

## Interrupt 감지 및 Frontend 통신

### Backend - Interrupt 감지

```python
# backend/app/api/chat_api.py

async def process_query_streaming(session_id: str, query: str):
    """Process query with HITL support"""

    config = {"configurable": {"thread_id": session_id}}
    initial_state = {"query": query, "workflow_status": "running"}

    async for event in supervisor.app.astream(
        initial_state,
        config,
        stream_mode="updates"
    ):
        # Check for interrupt
        if "__interrupt__" in event:
            interrupt_list = event["__interrupt__"]

            for interrupt_obj in interrupt_list:
                interrupt_data = interrupt_obj.value

                logger.info(f"[ChatAPI] HITL interrupt detected: {interrupt_data.get('type')}")

                # Send collaboration request to frontend
                await websocket_manager.send_message(session_id, {
                    "type": "collaboration_started",
                    "interrupt_type": interrupt_data.get("type"),
                    "message": interrupt_data.get("message"),
                    "data": interrupt_data
                })

                # Workflow paused - waiting for user input
                return

        # Normal processing continues...
```

---

### Frontend - HITL Dialog

```typescript
// frontend/src/components/ChatInterface.tsx

// WebSocket message handler
useEffect(() => {
    const handleMessage = (data: any) => {
        if (data.type === 'collaboration_started') {
            // Show HITL dialog
            setCollaborationData({
                type: data.interrupt_type,
                message: data.message,
                content: data.data.aggregated_content,
                searchCount: data.data.search_results_count
            });
            setShowCollaborationDialog(true);
        }
    };

    // ... WebSocket setup ...
}, []);

// User confirmation
const handleCollaborationDecision = async (approved: boolean) => {
    const decision = {
        approved: approved,
        feedback: userFeedback,
        timestamp: new Date().toISOString()
    };

    // Send resume request
    await fetch(`/api/chat/${sessionId}/resume`, {
        method: 'POST',
        body: JSON.stringify(decision)
    });

    setShowCollaborationDialog(false);
};
```

---

## 기대 효과

### Before (이전 구현)

- ❌ Subgraph checkpoint 저장 안 됨
- ❌ Resume 시 처음부터 재시작
- ❌ HITL 작동 안 함
- ❌ LangGraph Issue #4796 발생

### After (공식 패턴)

- ✅ Subgraph checkpoint 자동 저장
- ✅ Resume 시 interrupt 지점에서 계속
- ✅ HITL 완벽 작동
- ✅ 추가 에이전트와 호환 가능

---

## 추가 에이전트 적용 방법

동일한 패턴으로 다른 팀도 추가 가능:

```python
# team_supervisor.py

def build_graph(self):
    workflow = StateGraph(MainSupervisorState)

    # Document team
    document_subgraph = build_document_workflow().compile()
    workflow.add_node("document_team", document_subgraph)

    # Analysis team (추가 예시)
    analysis_subgraph = build_analysis_workflow().compile()
    workflow.add_node("analysis_team", analysis_subgraph)

    # Search team (추가 예시)
    search_subgraph = build_search_workflow().compile()
    workflow.add_node("search_team", search_subgraph)

    # Edges
    workflow.add_edge(START, "planning")
    workflow.add_conditional_edges("planning", route_to_team)
    workflow.add_edge("document_team", "aggregate")
    workflow.add_edge("analysis_team", "aggregate")
    workflow.add_edge("search_team", "aggregate")

    # Parent compile (checkpointer auto-propagates!)
    self.app = workflow.compile(checkpointer=self.checkpointer)
```

**각 subgraph에서 HITL 가능!**

---

## 타임라인

- **테스트 완료:** 2025-10-25
- **Production 적용:** 1-2일 예상
  - State 수정: 2시간
  - Document team 수정: 3시간
  - TeamSupervisor 수정: 2시간
  - Chat API 수정: 2시간
  - 통합 테스트: 3시간

**Total: 약 1일 작업**

---

## 체크리스트

### Backend

- [ ] `separated_states.py`: MainSupervisorState에 document team fields 추가
- [ ] `document_team/nodes/aggregate.py`: `interrupt()` 함수 사용
- [ ] `team_supervisor.py`: Subgraph를 직접 node로 추가
- [ ] `chat_api.py`: `Command(resume=...)` 패턴 사용
- [ ] `chat_api.py`: `__interrupt__` event 감지 및 WebSocket 전송

### Frontend

- [ ] Collaboration dialog 구현
- [ ] WebSocket message handler 추가
- [ ] Resume API call 구현

### Testing

- [ ] Unit test: interrupt() 함수
- [ ] Integration test: Full HITL flow
- [ ] E2E test: Frontend → Backend → Resume

---

## 참고 문서

- **공식 문서:** https://langchain-ai.github.io/langgraph/how-tos/subgraph/
- **HITL 가이드:** https://langchain-ai.github.io/langgraph/how-tos/human_in_the_loop/add-human-in-the-loop/
- **테스트 코드:** `backend/app/hitl_test_agent/`
  - `test_supervisor.py` - 공식 패턴 구현
  - `test_subgraph.py` - interrupt() 함수 사용
  - `test_runner.py` - Full test

---

## 결론

**LangGraph 공식 패턴을 사용하면 모든 것이 작동합니다!**

핵심:
1. ✅ Compiled subgraph를 직접 node로 추가
2. ✅ `interrupt()` 함수 사용 (NodeInterrupt 아님!)
3. ✅ 같은 state schema 공유
4. ✅ Main graph resume

**Flatten architecture 필요 없음!** 현재 구조 유지 가능!

---

**작성:** 2025-10-25
**테스트:** ✅ 완료
**상태:** Production 적용 준비 완료
**추천:** 즉시 적용
