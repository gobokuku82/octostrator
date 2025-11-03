# 🚀 HITL 구현 시작 가이드
**날짜:** 2025-10-25
**읽기 시간:** 10분
**목적:** Git 되돌린 후 바로 구현 시작

---

## ⚡ 5분 요약

### 문제
- LangGraph 0.6에서 Subgraph HITL이 작동 안 함
- Interrupt에서 멈추지 않고 aggregate → generate_response로 계속 진행

### 해결 (공식 패턴 4가지)
```python
# 1. Compiled subgraph를 직접 node로 추가
workflow.add_node("document_team", compiled_subgraph)

# 2. interrupt() 함수 사용 (NodeInterrupt ❌)
from langgraph.types import interrupt
user_input = interrupt({"message": "..."})

# 3. State schema 공유
class MainState(TypedDict):
    # Subgraph fields 포함 필수!
    aggregated_content: str
    collaboration_result: dict

# 4. Main graph resume
async for event in app.astream(Command(resume=value), config):
    ...
```

### 테스트 결과
```
11/11 테스트 통과 (100%)
✅ 모든 기능 완벽 작동
```

### 🔴 CRITICAL: Windows 필수 설정
```python
# backend/main.py 최상단 추가
import asyncio, platform
if platform.system() == 'Windows':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
```

---

## 📋 구현 체크리스트 (1-2일)

### Phase 1: State 수정 (2시간)

**파일:** `backend/app/service_agent/foundation/separated_states.py`

```python
class MainSupervisorState(TypedDict):
    # 기존 fields
    query: str
    current_team: str

    # ✅ Document team fields 추가 (필수!)
    planning_result: Dict[str, Any]
    search_results: List[Dict]
    aggregated_content: str
    final_document: str
    collaboration_result: Optional[Dict]  # HITL resume 값

    # ✅ HITL fields 추가
    workflow_status: Optional[str]
    interrupted_by: Optional[str]
    interrupt_type: Optional[str]
    interrupt_data: Optional[Dict[str, Any]]
```

---

### Phase 2: Document Team 수정 (3시간)

**파일:** `backend/app/service_agent/teams/document_team/nodes/aggregate.py`

**Before (틀림):**
```python
from langgraph.errors import NodeInterrupt

def aggregate_node(state):
    if needs_collaboration:
        raise NodeInterrupt({"message": "..."})  # ❌ 작동 안 함
```

**After (올바름):**
```python
from langgraph.types import interrupt

def aggregate_node(state: DocumentTeamState) -> DocumentTeamState:
    # ... aggregation logic ...

    if needs_collaboration(aggregated_content):
        # ✅ interrupt() 함수 사용
        collaboration_result = interrupt({
            "type": "collaboration_required",
            "message": "검색 결과 검토가 필요합니다",
            "aggregated_content": aggregated_content,
            "search_results_count": len(state.get("search_results", []))
        })

        state["collaboration_result"] = collaboration_result
        state["aggregated_content"] = aggregated_content
        return state

    state["aggregated_content"] = aggregated_content
    return state
```

---

### Phase 3: TeamSupervisor 수정 (2시간)

**파일:** `backend/app/service_agent/supervisor/team_supervisor.py`

**Before (틀림):**
```python
# ❌ 삭제해야 할 함수들
async def execute_teams_node(self, state):
    # Node 내부에서 subgraph 실행 (잘못된 패턴!)
    document_app = subgraph.compile(checkpointer=self.checkpointer)
    async for event in document_app.astream(state, config):
        if "__interrupt__" in event:
            return {"status": "interrupted"}

async def _execute_single_team(self, team_name, shared_state, main_state):
    # ...
```

**After (올바름):**
```python
class TeamBasedSupervisor:
    def build_graph(self):
        workflow = StateGraph(MainSupervisorState)

        # Regular nodes
        workflow.add_node("planning", self.planning_node)
        workflow.add_node("aggregate", self.aggregate_node)
        workflow.add_node("generate_response", self.generate_response_node)

        # ✅ OFFICIAL PATTERN: Compiled subgraph를 직접 node로 추가
        from app.service_agent.teams.document_team.workflow import build_document_workflow

        document_subgraph = build_document_workflow()
        compiled_subgraph = document_subgraph.compile()  # NO checkpointer!

        workflow.add_node("document_team", compiled_subgraph)

        # Edges
        workflow.add_edge(START, "planning")
        workflow.add_edge("planning", "document_team")  # Direct to subgraph
        workflow.add_edge("document_team", "aggregate")
        workflow.add_edge("aggregate", "generate_response")
        workflow.add_edge("generate_response", END)

        # ✅ Compile with checkpointer (auto-propagates!)
        self.app = workflow.compile(checkpointer=self.checkpointer)
```

---

### Phase 4: Chat API 수정 (2시간)

**파일:** `backend/app/api/chat_api.py`

**Interrupt 감지:**
```python
async def process_query_streaming(session_id: str, query: str):
    config = {"configurable": {"thread_id": session_id}}

    async for event in supervisor.app.astream(initial_state, config):
        # ✅ Interrupt 감지
        if "__interrupt__" in event:
            interrupt_list = event["__interrupt__"]

            for interrupt_obj in interrupt_list:
                interrupt_data = interrupt_obj.value

                # WebSocket으로 frontend에 전송
                await websocket_manager.send_message(session_id, {
                    "type": "collaboration_started",
                    "interrupt_type": interrupt_data.get("type"),
                    "message": interrupt_data.get("message"),
                    "data": interrupt_data
                })

                return  # Workflow paused
```

**Resume API:**
```python
@router.post("/chat/{session_id}/resume")
async def resume_collaboration(session_id: str, user_decision: dict):
    config = {"configurable": {"thread_id": session_id}}

    # ✅ Main graph resume
    from langgraph.types import Command

    async for event in supervisor.app.astream(
        Command(resume=user_decision),  # Resume value
        config
    ):
        for node_name, node_output in event.items():
            if node_name == "generate_response":
                response = node_output.get("final_document", "")
                await websocket_manager.send_message(session_id, {
                    "type": "response",
                    "content": response
                })
```

---

### Phase 5: Frontend (선택, 2시간)

**파일:** `frontend/src/components/ChatInterface.tsx`

```typescript
// WebSocket message handler
const handleMessage = (data: any) => {
    if (data.type === 'collaboration_started') {
        setCollaborationData({
            type: data.interrupt_type,
            message: data.message,
            content: data.data.aggregated_content
        });
        setShowCollaborationDialog(true);
    }
};

// User decision
const handleCollaborationDecision = async (approved: boolean) => {
    const decision = {
        approved: approved,
        feedback: userFeedback,
        timestamp: new Date().toISOString()
    };

    await fetch(`/api/chat/${sessionId}/resume`, {
        method: 'POST',
        body: JSON.stringify(decision)
    });

    setShowCollaborationDialog(false);
};
```

---

## 🔴 Windows 환경 필수 설정

**파일:** `backend/main.py` (최상단)

```python
import asyncio
import platform

# CRITICAL: Windows compatibility for AsyncPostgresSaver
if platform.system() == 'Windows':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    print("✅ Windows EventLoop policy set")

# 이후 나머지 imports...
from fastapi import FastAPI
# ...
```

**이유:**
- Windows의 ProactorEventLoop는 psycopg (PostgreSQL 드라이버)와 호환 안 됨
- 이 설정 없으면 AsyncPostgresSaver 에러 발생
- Linux는 영향 없음

---

## 📊 테스트 방법

### 1. 기본 테스트 (백업 파일 사용)

```bash
# 백업된 테스트 파일 복사
cp BACKUP_HITL_251025/tests/test_supervisor.py backend/app/hitl_test_agent/
cp BACKUP_HITL_251025/tests/test_subgraph.py backend/app/hitl_test_agent/
cp BACKUP_HITL_251025/tests/test_runner.py backend/app/hitl_test_agent/

# 테스트 실행
cd backend
python app/hitl_test_agent/test_runner.py
```

**예상 결과:**
```
✅ TEST PASSED!
✅ CONCLUSION: Direct Subgraph Resume WORKS
  - step_count = 2 ✓
  - user_input = "user approved" ✓
```

### 2. Production 테스트

```bash
# Document workflow 실행
curl -X POST http://localhost:8000/api/chat/query \
  -H "Content-Type: application/json" \
  -d '{"session_id": "test-001", "query": "임대차계약서 작성해줘"}'

# Interrupt 발생 확인 (WebSocket)
# → collaboration_started 메시지 수신

# Resume 실행
curl -X POST http://localhost:8000/api/chat/test-001/resume \
  -H "Content-Type: application/json" \
  -d '{"approved": true, "feedback": "승인합니다"}'

# 최종 응답 확인
```

---

## 🎯 구현 우선순위

### 최소 구현 (HITL 작동만)
1. ✅ State 수정 (Phase 1)
2. ✅ Document Team 수정 (Phase 2)
3. ✅ TeamSupervisor 수정 (Phase 3)
4. ✅ Chat API 수정 (Phase 4)

**시간:** 1일 (9시간)

### 완전 구현 (Frontend 포함)
1-4 + Frontend (Phase 5)

**시간:** 1.5일 (11시간)

---

## ⚠️ 주의사항

### ❌ 하지 말아야 할 것

1. **NodeInterrupt 사용 금지**
   ```python
   # ❌ 작동 안 함
   raise NodeInterrupt({...})
   ```

2. **Node 내부 subgraph 실행 금지**
   ```python
   # ❌ Checkpoint 저장 안 됨
   async def execute_teams_node(state):
       app = subgraph.compile(checkpointer=...)
       async for event in app.astream(...):
           ...
   ```

3. **Subgraph 직접 resume 금지**
   ```python
   # ❌ 작동 안 함
   async for event in document_app.astream(None, config):
       ...
   ```

### ✅ 반드시 해야 할 것

1. **interrupt() 함수 사용**
2. **Compiled subgraph를 직접 node로 추가**
3. **Main graph resume with Command**
4. **Windows EventLoop 설정** (Windows 환경)

---

## 📚 추가 자료

백업 폴더에 상세 문서들이 있지만, **이 파일만으로 충분합니다.**

**필요시에만 참고:**
- `docs/SOLUTION_OFFICIAL_LANGGRAPH_PATTERN_251025.md` - 패턴 상세 설명
- `docs/PRODUCTION_INTEGRATION_TEST_RESULTS_251025.md` - Production 검증
- `tests/test_*.py` - 테스트 코드 예제

---

## 🚀 시작하기

```bash
# 1. Git 되돌리기
git log --oneline
git reset --hard <HITL-이전-커밋>

# 2. 새 브랜치
git checkout -b feature/hitl-official-pattern

# 3. 이 파일을 열고 체크리스트 따라 구현
# Phase 1 → Phase 2 → Phase 3 → Phase 4

# 4. 테스트
python backend/app/hitl_test_agent/test_runner.py

# 5. Commit
git add .
git commit -m "Implement HITL with official LangGraph pattern"
```

---

**읽기 완료! 이제 Phase 1부터 시작하세요.** ✅

**예상 시간:** 1-2일 (최소 구현: 1일, 완전 구현: 1.5일)
