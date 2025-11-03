# 부동산 챗봇 전체 흐름 매뉴얼

**작성일**: 2025-01-27
**버전**: 1.0
**대상**: 개발자, 시스템 분석가
**목적**: 사용자 질문 입력부터 최종 답변까지 전체 처리 과정 이해

---

## 📋 목차

1. [전체 흐름 개요](#1-전체-흐름-개요)
2. [Layer 0: FastAPI WebSocket](#2-layer-0-fastapi-websocket)
3. [Layer 1: Supervisor Level](#3-layer-1-supervisor-level)
4. [Layer 2: LangGraph Workflow](#4-layer-2-langgraph-workflow)
5. [Layer 3: Planning & Intent Analysis](#5-layer-3-planning--intent-analysis)
6. [Layer 4: Agent Selection](#6-layer-4-agent-selection)
7. [Layer 5: Execution](#7-layer-5-execution)
8. [Layer 6: Response Generation](#8-layer-6-response-generation)
9. [실제 예시 (전체 추적)](#9-실제-예시-전체-추적)
10. [트러블슈팅](#10-트러블슈팅)

---

## 1. 전체 흐름 개요

### 1.1 처리 단계 (8단계)

```
┌─────────────────────────────────────────────────────────────────┐
│                    사용자 질문 입력                               │
│              "전세금 5% 인상 가능한가요?"                         │
└────────────────────────┬────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│ Layer 0: FastAPI WebSocket Endpoint                            │
│ - WebSocket 연결 수립                                           │
│ - 메시지 수신 및 검증                                           │
│ - 백그라운드 Task 생성                                          │
└────────────────────────┬────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│ Layer 1: Supervisor Level                                       │
│ - Supervisor 싱글톤 가져오기                                    │
│ - 초기 State 생성                                               │
│ - LangGraph 워크플로우 시작                                     │
└────────────────────────┬────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│ Layer 2: LangGraph Workflow                                     │
│ - initialize_node: State 초기화                                 │
│ - planning_node: 계획 수립                                      │
│ - _route_after_planning: 조건 분기                              │
└────────────────────────┬────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│ Layer 3: Planning & Intent Analysis                            │
│ - Chat History 조회                                             │
│ - analyze_intent: 의도 분석 (LLM 호출)                          │
│   └─ intent_analysis.txt 프롬프트 사용                          │
│ - IntentType 결정: LEGAL_CONSULT                                │
└────────────────────────┬────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│ Layer 4: Agent Selection                                        │
│ - suggest_agents: Agent 선택                                    │
│   ├─ 0차: 하드코딩 키워드 필터                                  │
│   ├─ 1차: LLM Agent 선택 (agent_selection.txt)                 │
│   ├─ 2차: Simplified LLM                                        │
│   └─ 3차: Safe Defaults                                         │
│ - 선택 결과: ["search_team"]                                    │
└────────────────────────┬────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│ Layer 5: Execution                                              │
│ - execute_teams_node: 팀 실행                                   │
│ - SearchExecutor 실행                                           │
│   └─ HybridLegalSearch (FAISS + SQLite)                        │
│ - 검색 결과 수집                                                │
└────────────────────────┬────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│ Layer 6: Response Generation                                    │
│ - aggregate_results_node: 결과 집계                             │
│ - generate_response_node: 최종 답변 생성                        │
│   └─ response_synthesis.txt 프롬프트 사용                       │
│ - WebSocket 전송: {"type": "final_response", ...}              │
└────────────────────────┬────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│                    최종 답변 반환                                 │
│    "주택임대차보호법에 따라 전세금 증액은..."                    │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 핵심 컴포넌트

| 컴포넌트 | 파일 | 역할 |
|---------|------|------|
| **WebSocket Endpoint** | chat_api.py | 사용자 입력 수신, 실시간 통신 |
| **TeamSupervisor** | team_supervisor.py | 워크플로우 관리, Agent 조정 |
| **PlanningAgent** | planning_agent.py | 의도 분석, Agent 선택 |
| **SearchExecutor** | search_executor.py | 검색 실행 (법률, 시세, 대출) |
| **HybridLegalSearch** | hybrid_legal_search.py | 벡터DB 검색 (FAISS + SQLite) |
| **LLMService** | llm_service.py | LLM 호출 관리 |
| **PromptManager** | prompt_manager.py | 프롬프트 로드 및 변수 치환 |

### 1.3 State 흐름

```python
MainSupervisorState (최상위 State)
├─ query: str                    # "전세금 5% 인상 가능?"
├─ session_id: str               # "session-9b050480-..."
├─ current_phase: str            # "initialization" → "planning" → "executing"
├─ planning_state: dict          # Intent 분석 결과
│   ├─ analyzed_intent
│   │   ├─ intent_type: str      # "LEGAL_CONSULT"
│   │   ├─ confidence: float     # 0.95
│   │   └─ keywords: List[str]   # ["전세금", "인상"]
│   ├─ suggested_agents: List    # ["search_team"]
│   └─ execution_steps: List     # [ExecutionStep(...)]
├─ team_results: dict            # 팀별 실행 결과
│   └─ search: dict
│       └─ data: List            # 검색 결과
├─ aggregated_results: dict      # 집계된 결과
└─ final_response: dict          # 최종 답변
    ├─ type: str                 # "answer"
    ├─ answer: str               # "주택임대차보호법에 따라..."
    └─ structured_data: dict     # UI용 구조화 데이터
```

---

## 2. Layer 0: FastAPI WebSocket

### 2.1 WebSocket 연결 수립

**파일**: `backend/app/api/chat_api.py`

```python
@router.websocket("/ws/{session_id}")
async def websocket_chat(
    websocket: WebSocket,
    session_id: str,  # ← URL 파라미터
    session_mgr: SessionManager = Depends(get_session_manager),
    conn_mgr: ConnectionManager = Depends(get_connection_manager)
):
```

#### 단계 1: 세션 검증 [라인 642]

```python
validation_result = await session_mgr.validate_session(session_id)

if not validation_result:
    await websocket.close(code=4004, reason="Session not found or expired")
    return
```

**처리 내용**:
- `chat_sessions` 테이블에서 `session_id` 조회
- 존재하지 않으면 → WebSocket 연결 거부 (4004 에러)
- 존재하면 → 다음 단계 진행

#### 단계 2: WebSocket 연결 [라인 653]

```python
await conn_mgr.connect(session_id, websocket)
```

**처리 내용**:
- `ConnectionManager`에 `session_id`와 `WebSocket` 객체 매핑 저장
- 내부 딕셔너리: `{session_id: websocket}`

#### 단계 3: 연결 확인 메시지 전송 [라인 656]

```python
await conn_mgr.send_message(session_id, {
    "type": "connected",
    "session_id": session_id,
    "timestamp": datetime.now().isoformat()
})
```

**클라이언트 수신 메시지**:
```json
{
  "type": "connected",
  "session_id": "session-9b050480-...",
  "timestamp": "2025-01-27T10:30:00.000Z"
}
```

#### 단계 4: Supervisor 싱글톤 가져오기 [라인 663]

```python
supervisor = await get_supervisor(enable_checkpointing=True)
```

**`get_supervisor()` 함수 [라인 85]**:

```python
_supervisor_instance = None  # 전역 변수
_supervisor_lock = asyncio.Lock()

async def get_supervisor(enable_checkpointing: bool = True):
    global _supervisor_instance

    async with _supervisor_lock:  # ← 동시성 제어
        if _supervisor_instance is None:
            llm_context = create_default_llm_context()

            _supervisor_instance = TeamBasedSupervisor(
                llm_context=llm_context,
                enable_checkpointing=True
            )

        return _supervisor_instance
```

**싱글톤 패턴 이유**:
- ✅ **메모리 절약**: LLM 클라이언트, Agent, Tool 재사용
- ✅ **성능**: 매 요청마다 초기화 불필요 (0.5초 절약)
- ✅ **상태 공유**: 모든 세션이 동일한 Supervisor 사용

**Supervisor 초기화 과정 [team_supervisor.py:49]**:

```python
def __init__(self, llm_context, enable_checkpointing=True):
    # 1. Agent 시스템 초기화
    initialize_agent_system(auto_register=True)

    # 2. PlanningAgent 생성
    self.planning_agent = PlanningAgent(llm_context=llm_context)

    # 3. 3개 팀 초기화
    self.teams = {
        "search": SearchExecutor(llm_context, progress_callback=None),
        "document": DocumentExecutor(llm_context, progress_callback=None),
        "analysis": AnalysisExecutor(llm_context, progress_callback=None)
    }

    # 4. LangGraph 워크플로우 구성
    self._build_graph()
```

#### 단계 5: 메시지 수신 무한 루프 [라인 667]

```python
while True:
    # 메시지 수신 (JSON)
    data = await websocket.receive_json()
    message_type = data.get("type")

    if message_type == "query":
        query = data.get("query")
        enable_checkpointing = data.get("enable_checkpointing", True)

        # Progress callback 정의
        async def progress_callback(event_type: str, event_data: dict):
            await conn_mgr.send_message(session_id, {
                "type": event_type,
                **event_data,
                "timestamp": datetime.now().isoformat()
            })

        # 🔥 백그라운드 Task 생성 (비동기 실행)
        asyncio.create_task(
            _process_query_async(
                supervisor=supervisor,
                query=query,
                session_id=session_id,
                enable_checkpointing=enable_checkpointing,
                progress_callback=progress_callback,
                conn_mgr=conn_mgr,
                session_mgr=session_mgr
            )
        )
```

**핵심 포인트**:
- ✅ **비동기 처리**: `asyncio.create_task()`로 쿼리 처리를 백그라운드에서 실행
- ✅ **즉시 응답**: 메시지 수신 루프는 블로킹되지 않고 계속 실행
- ✅ **실시간 통신**: `progress_callback`으로 진행 상황 실시간 전송

**클라이언트 송신 메시지 예시**:
```json
{
  "type": "query",
  "query": "전세금 5% 인상 가능한가요?",
  "enable_checkpointing": true
}
```

---

## 3. Layer 1: Supervisor Level

### 3.1 `_process_query_async()` [chat_api.py:871]

**역할**: 백그라운드에서 쿼리 처리

```python
async def _process_query_async(
    supervisor: TeamBasedSupervisor,
    query: str,
    session_id: str,
    enable_checkpointing: bool,
    progress_callback,
    conn_mgr: ConnectionManager,
    session_mgr: SessionManager
):
```

#### 단계 1: 사용자 메시지 DB 저장 [라인 901]

```python
await _save_message_to_db(session_id, "user", query)
```

**처리 내용**:
- `chat_messages` 테이블에 INSERT
- `role = "user"`, `content = query`, `session_id = session_id`

#### 단계 2: user_id 추출 [라인 904]

```python
user_id = 1  # 임시 하드코딩
session_data = await session_mgr.get_session(session_id)
if session_data:
    # user_id 추출 (Long-term Memory용)
    pass
```

#### 단계 3: 🔥 Supervisor 쿼리 처리 시작 [라인 911]

```python
result = await supervisor.process_query_streaming(
    query=query,
    session_id=session_id,
    chat_session_id=session_id,
    user_id=user_id,
    progress_callback=progress_callback
)
```

**`process_query_streaming()` 함수 [team_supervisor.py:1707]**:

```python
async def process_query_streaming(
    self,
    query: str,
    session_id: str,
    chat_session_id: Optional[str],
    user_id: Optional[int],
    progress_callback: Optional[Callable]
):
```

#### 단계 3-1: Checkpointer 초기화 [라인 1736]

```python
await self._ensure_checkpointer()
```

**처리 내용**:
- PostgreSQL 기반 Checkpointer 생성 (최초 1회)
- LangGraph 0.6의 상태 저장/복원 기능
- 대화 히스토리 관리 및 HITL (Human-in-the-Loop) 지원

#### 단계 3-2: Progress Callback 등록 [라인 1739]

```python
if progress_callback:
    self._progress_callbacks[session_id] = progress_callback
```

**처리 내용**:
- `session_id`와 `callback` 함수 매핑 저장
- 각 노드에서 `self._progress_callbacks.get(session_id)`로 호출
- WebSocket으로 실시간 진행 상황 전송

#### 단계 3-3: 초기 State 생성 [라인 1744]

```python
initial_state = MainSupervisorState(
    query=query,
    session_id=session_id,
    chat_session_id=chat_session_id,
    user_id=user_id,
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
    status="initialized"
)
```

**State 구조**:
```python
MainSupervisorState = TypedDict('MainSupervisorState', {
    # 기본 정보
    'query': str,
    'session_id': str,
    'chat_session_id': Optional[str],
    'user_id': Optional[int],
    'request_id': str,

    # 계획 및 실행
    'planning_state': Optional[Dict],
    'execution_plan': Optional[List],
    'current_phase': str,
    'active_teams': List[str],
    'completed_teams': List[str],
    'failed_teams': List[str],

    # 결과
    'team_results': Dict[str, Any],
    'aggregated_results': Dict[str, Any],
    'final_response': Optional[Dict],

    # 팀별 State
    'search_team_state': Optional[Dict],
    'document_team_state': Optional[Dict],
    'analysis_team_state': Optional[Dict],

    # 시간 및 상태
    'start_time': datetime,
    'end_time': Optional[datetime],
    'status': str,
    'error_log': List[str]
})
```

#### 단계 3-4: 🔥 LangGraph 워크플로우 실행 [라인 1787]

```python
if self.checkpointer:
    config = {
        "configurable": {
            "thread_id": chat_session_id or session_id
        }
    }
    final_state = await self.app.ainvoke(initial_state, config=config)
else:
    final_state = await self.app.ainvoke(initial_state)
```

**핵심: `app.ainvoke()`**
- `self.app`은 `_build_graph()`에서 컴파일된 LangGraph 실행 그래프
- `ainvoke()`는 비동기로 그래프의 모든 노드를 순차 실행
- `config`에 `thread_id`를 전달하여 대화 히스토리 관리

#### 단계 3-5: Callback 정리 [라인 1793]

```python
if session_id in self._progress_callbacks:
    del self._progress_callbacks[session_id]
```

#### 단계 4: 최종 응답 전송 [_process_query_async 라인 1039]

```python
await conn_mgr.send_message(session_id, {
    "type": "final_response",
    "response": result["final_response"],
    "timestamp": datetime.now().isoformat()
})
```

**클라이언트 수신 메시지**:
```json
{
  "type": "final_response",
  "response": {
    "type": "answer",
    "answer": "주택임대차보호법 제7조에 따라...",
    "structured_data": {
      "sections": [
        {
          "title": "핵심 답변",
          "content": "전세금 증액은 5% 이내로 제한됩니다.",
          "icon": "target"
        }
      ]
    }
  },
  "timestamp": "2025-01-27T10:30:05.123Z"
}
```

---

## 4. Layer 2: LangGraph Workflow

### 4.1 워크플로우 그래프 구조

**파일**: `team_supervisor.py`

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

    # 조건부 라우팅
    workflow.add_conditional_edges(
        "planning",
        self._route_after_planning,
        {
            "execute": "execute_teams",
            "respond": "generate_response"
        }
    )

    workflow.add_edge("execute_teams", "aggregate")
    workflow.add_edge("aggregate", "generate_response")
    workflow.add_edge("generate_response", END)

    self.app = workflow.compile()
```

**그래프 다이어그램**:

```
┌─────────┐
│  START  │
└────┬────┘
     ↓
┌────────────────┐
│  initialize    │  ← State 초기화
│  [라인 209]    │
└────┬───────────┘
     ↓
┌────────────────┐
│  planning      │  ← 의도 분석 & Agent 선택
│  [라인 240]    │
└────┬───────────┘
     ↓
┌────────────────────┐
│ _route_after_      │  ← 조건 분기
│ planning [라인 133]│
└────┬───────────────┘
     │
     ├─────────────┬─────────────┐
     ↓             ↓             ↓
if irrelevant  if unclear   else
     ↓             ↓             ↓
   respond      respond      execute
     ↓             ↓             ↓
     └─────────────┴─────────────┤
                                 ↓
                        ┌────────────────┐
                        │ execute_teams  │
                        │ [라인 650]     │
                        └────┬───────────┘
                             ↓
                        ┌────────────────┐
                        │   aggregate    │
                        │ [라인 1259]    │
                        └────┬───────────┘
                             ↓
┌────────────────────────────┴────────────────────────┐
│                 generate_response                    │
│                 [라인 1321]                          │
└─────────────────────────┬───────────────────────────┘
                          ↓
                    ┌─────────┐
                    │   END   │
                    └─────────┘
```

### 4.2 노드별 실행 순서

#### 노드 1: `initialize_node` [라인 209]

**역할**: State 초기화 및 시작 알림

```python
async def initialize_node(self, state: MainSupervisorState):
    state["start_time"] = datetime.now()
    state["status"] = "initialized"
    state["current_phase"] = "initialization"
    state["active_teams"] = []
    state["completed_teams"] = []
    state["failed_teams"] = []
    state["team_results"] = {}
    state["error_log"] = []

    # WebSocket 전송
    session_id = state.get("session_id")
    progress_callback = self._progress_callbacks.get(session_id)
    if progress_callback:
        await progress_callback("supervisor_phase_change", {
            "supervisorPhase": "dispatching",
            "supervisorProgress": 5,
            "message": "질문을 접수하고 있습니다"
        })

    return state
```

**WebSocket 메시지**:
```json
{
  "type": "supervisor_phase_change",
  "supervisorPhase": "dispatching",
  "supervisorProgress": 5,
  "message": "질문을 접수하고 있습니다",
  "timestamp": "2025-01-27T10:30:00.500Z"
}
```

#### 노드 2: `planning_node` [라인 240]

**역할**: 의도 분석 및 실행 계획 수립 (다음 섹션에서 상세 설명)

#### 노드 3: `_route_after_planning` [라인 133]

**역할**: 조건에 따라 다음 노드 결정

```python
def _route_after_planning(self, state: MainSupervisorState) -> str:
    planning_state = state.get("planning_state")

    if planning_state:
        analyzed_intent = planning_state.get("analyzed_intent", {})
        intent_type = analyzed_intent.get("intent_type", "")
        confidence = analyzed_intent.get("confidence", 0.0)

        # 🔴 필터링 조건 1: IRRELEVANT
        if intent_type == "irrelevant":
            logger.info("Detected IRRELEVANT query, routing to respond")
            return "respond"  # → generate_response_node

        # 🔴 필터링 조건 2: UNCLEAR (낮은 confidence)
        if intent_type == "unclear" and confidence < 0.3:
            logger.info(f"Low confidence UNCLEAR query ({confidence})")
            return "respond"  # → generate_response_node

    # ✅ 정상 실행
    if planning_state and planning_state.get("execution_steps"):
        logger.info(f"Routing to execute - {len(planning_state['execution_steps'])} steps")
        return "execute"  # → execute_teams_node

    return "respond"
```

**라우팅 로직**:

| 조건 | 반환값 | 다음 노드 | 설명 |
|------|--------|----------|------|
| `intent_type == "irrelevant"` | `"respond"` | generate_response | 부동산 무관 질문 |
| `intent_type == "unclear" and confidence < 0.3` | `"respond"` | generate_response | 불분명한 질문 |
| `execution_steps` 존재 | `"execute"` | execute_teams | 정상 실행 |
| 기타 | `"respond"` | generate_response | 기본값 |

---

## 5. Layer 3: Planning & Intent Analysis

### 5.1 `planning_node` 전체 흐름

**파일**: `team_supervisor.py:240`

```python
async def planning_node(self, state: MainSupervisorState):
    logger.info("[TeamSupervisor] Planning phase")

    state["current_phase"] = "planning"

    # 1. WebSocket: Planning 시작 알림
    # 2. Chat History 조회
    # 3. Intent 분석
    # 4. Agent 선택
    # 5. 실행 계획 생성
    # 6. WebSocket: Plan 완료 알림

    return state
```

### 5.2 단계별 상세 분석

#### 단계 1: WebSocket 알림 [라인 254]

```python
progress_callback = self._progress_callbacks.get(session_id)
if progress_callback:
    await progress_callback("supervisor_phase_change", {
        "supervisorPhase": "analyzing",
        "supervisorProgress": 10,
        "message": "질문을 분석하고 계획을 수립하고 있습니다"
    })
```

**클라이언트 수신**:
```json
{
  "type": "supervisor_phase_change",
  "supervisorPhase": "analyzing",
  "supervisorProgress": 10,
  "message": "질문을 분석하고 계획을 수립하고 있습니다",
  "timestamp": "2025-01-27T10:30:01.000Z"
}
```

#### 단계 2: Chat History 조회 [라인 279]

```python
chat_history = await self._get_chat_history(
    session_id=chat_session_id,
    limit=3  # 최근 3개 대화 쌍 (6개 메시지)
)
```

**`_get_chat_history()` 함수**:
```python
async def _get_chat_history(self, session_id: str, limit: int = 3):
    if not session_id:
        return []

    async for db in get_async_db():
        query = (
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(desc(ChatMessage.created_at))
            .limit(limit * 2)  # user + assistant 쌍
        )
        result = await db.execute(query)
        messages = result.scalars().all()

        return [
            {
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.created_at.isoformat()
            }
            for msg in reversed(messages)
        ]
```

**반환 예시**:
```python
[
    {"role": "user", "content": "전세 계약이란?", "timestamp": "..."},
    {"role": "assistant", "content": "전세 계약은...", "timestamp": "..."},
    {"role": "user", "content": "전세금 인상 한도는?", "timestamp": "..."},
    {"role": "assistant", "content": "5% 이내입니다.", "timestamp": "..."},
    # 현재 질문
    {"role": "user", "content": "전세금 5% 인상 가능?", "timestamp": "..."}
]
```

#### 단계 3: Context 생성 [라인 285]

```python
context = {"chat_history": chat_history} if chat_history else None
```

#### 단계 4: Intent 분석 시작 알림 [라인 290]

```python
await progress_callback("analysis_start", {
    "message": "질문을 분석하고 있습니다...",
    "stage": "analysis"
})
```

#### 단계 5: 🔥 Intent 분석 [라인 299]

```python
intent_result = await self.planning_agent.analyze_intent(query, context)
```

**`analyze_intent()` 함수 [planning_agent.py:160]**:

```python
async def analyze_intent(self, query: str, context: Optional[Dict] = None):
    # 1차 시도: LLM 분석
    if self.llm_service:
        try:
            return await self._analyze_with_llm(query, context)
        except Exception as e:
            logger.warning(f"LLM analysis failed: {e}")

    # 2차 시도: 패턴 매칭 (Fallback)
    return self._analyze_with_patterns(query, context)
```

**`_analyze_with_patterns()` 함수 [planning_agent.py:258]** (Fallback):

**역할**: LLM 실패 시 패턴 매칭 기반 의도 분석

```python
def _analyze_with_patterns(self, query: str, context: Optional[Dict]) -> IntentResult:
    """패턴 매칭 기반 의도 분석"""
    detected_intents = {}
    found_keywords = []

    # 각 의도 타입별 점수 계산
    for intent_type, patterns in self.intent_patterns.items():
        score = 0
        for pattern in patterns:
            if pattern in query.lower():
                score += 1
                found_keywords.append(pattern)
        if score > 0:
            detected_intents[intent_type] = score

    # 가장 높은 점수의 의도 선택
    if detected_intents:
        best_intent = max(detected_intents.items(), key=lambda x: x[1])
        intent_type = best_intent[0]
        confidence = min(best_intent[1] * 0.3, 1.0)
    else:
        intent_type = IntentType.UNCLEAR
        confidence = 0.0

    # Agent 선택 (패턴 매칭 - fallback에서는 기본 Agent 사용)
    intent_to_agent = {
        IntentType.LEGAL_CONSULT: ["search_team"],
        IntentType.MARKET_INQUIRY: ["search_team"],
        IntentType.LOAN_CONSULT: ["search_team"],
        IntentType.CONTRACT_CREATION: ["document_team"],
        IntentType.CONTRACT_REVIEW: ["search_team", "analysis_team"],
        IntentType.COMPREHENSIVE: ["search_team", "analysis_team"],
        IntentType.RISK_ANALYSIS: ["analysis_team"],
        IntentType.UNCLEAR: ["search_team"],
    }
    suggested_agents = intent_to_agent.get(intent_type, ["search_team"])

    return IntentResult(
        intent_type=intent_type,
        confidence=confidence,
        keywords=found_keywords,
        reasoning="Pattern-based analysis",
        suggested_agents=suggested_agents,
        fallback=True
    )
```

**`intent_patterns` 딕셔너리 [planning_agent.py:108]**:

```python
{
    IntentType.LEGAL_CONSULT: [
        # 기존 키워드
        "법", "전세", "임대", "보증금", "계약", "권리", "의무", "갱신",
        # 자연스러운 표현 추가
        "살다", "거주", "세입자", "집주인", "임차인", "임대인", "해지", "계약서",
        "대항력", "확정일자", "우선변제", "임차권"
    ],
    IntentType.MARKET_INQUIRY: [
        "시세", "가격", "매매가", "전세가", "시장", "동향", "평균",
        "얼마", "비싸", "싸", "오르다", "내리다", "올랐", "떨어졌"
    ],
    IntentType.LOAN_CONSULT: [
        "대출", "금리", "한도", "조건", "상환", "LTV", "DTI",
        "DSR", "담보대출", "전세자금", "빌리다", "이자"
    ],
    # ... 기타
}
```

**처리 방식**:
1. 쿼리에서 각 Intent 패턴 키워드 검색
2. 키워드 매칭 개수로 점수 계산
3. 가장 높은 점수의 Intent 선택
4. confidence = score * 0.3 (최대 1.0)

**예시**:
```python
질문: "전세 계약 갱신 가능한가요?"
→ 매칭: "전세"(1) + "계약"(1) + "갱신"(1) = 3개
→ Intent: LEGAL_CONSULT
→ confidence: 0.9 (3 * 0.3)
→ suggested_agents: ["search_team"]
```

---

### 📌 보충 설명 2: LLM 재시도 로직

**역할**: OpenAI API 호출 실패 시 Exponential Backoff 전략으로 자동 재시도

**위치**: `llm_service.py:259` (_call_with_retry), `llm_service.py:288` (_call_async_with_retry)

---

**`_call_with_retry()` 함수 [llm_service.py:259]** (동기 버전):

```python
def _call_with_retry(self, params: Dict[str, Any]) -> ChatCompletion:
    """재시도 로직이 포함된 동기 LLM 호출"""

    # 1. Config에서 재시도 설정 가져오기
    retry_config = Config.LLM_DEFAULTS.get("retry", {})
    max_attempts = retry_config.get("max_attempts", 3)          # 기본값: 3회
    backoff_seconds = retry_config.get("backoff_seconds", 1.0)  # 기본값: 1.0초

    last_error = None

    # 2. 최대 3회 재시도
    for attempt in range(max_attempts):
        try:
            # 3. OpenAI API 호출
            return self.client.chat.completions.create(**params)

        except Exception as e:
            last_error = e
            logger.warning(f"LLM call attempt {attempt + 1}/{max_attempts} failed: {e}")

            # 4. Exponential Backoff (마지막 시도가 아니면 대기)
            if attempt < max_attempts - 1:
                import time
                wait_time = backoff_seconds * (2 ** attempt)  # 1초 → 2초 → 4초
                time.sleep(wait_time)

    # 5. 모든 시도 실패 시 예외 발생
    raise last_error
```

**`_call_async_with_retry()` 함수 [llm_service.py:288]** (비동기 버전):

```python
async def _call_async_with_retry(self, params: Dict[str, Any]) -> ChatCompletion:
    """재시도 로직이 포함된 비동기 LLM 호출"""

    retry_config = Config.LLM_DEFAULTS.get("retry", {})
    max_attempts = retry_config.get("max_attempts", 3)
    backoff_seconds = retry_config.get("backoff_seconds", 1.0)

    last_error = None

    for attempt in range(max_attempts):
        try:
            # 비동기 클라이언트 사용
            return await self.async_client.chat.completions.create(**params)

        except Exception as e:
            last_error = e
            logger.warning(f"Async LLM call attempt {attempt + 1}/{max_attempts} failed: {e}")

            if attempt < max_attempts - 1:
                # 비동기 sleep 사용
                await asyncio.sleep(backoff_seconds * (2 ** attempt))

    raise last_error
```

---

**재시도 설정 [config.py:126]**:

```python
Config.LLM_DEFAULTS = {
    "retry": {
        "max_attempts": 3,        # 최대 3회 시도
        "backoff_seconds": 1.0    # 초기 대기 시간 1.0초
    }
}
```

**Exponential Backoff 계산식**:
```
대기 시간 = backoff_seconds * (2 ** attempt)

1차 시도 실패 → 1.0 * (2^0) = 1.0초 대기
2차 시도 실패 → 1.0 * (2^1) = 2.0초 대기
3차 시도 실패 → 예외 발생 (더 이상 재시도 안 함)
```

---

**처리 과정**:

1. **정상 케이스**:
   ```
   시도 1 → 성공 → 즉시 반환 (0.3초)
   ```

2. **일시적 오류 (네트워크 문제)**:
   ```
   시도 1 → 실패 → 1초 대기
   시도 2 → 성공 → 반환 (1.3초)
   ```

3. **지속적 오류 (API 키 문제)**:
   ```
   시도 1 → 실패 → 1초 대기
   시도 2 → 실패 → 2초 대기
   시도 3 → 실패 → Exception 발생
   총 소요: 3초 + (API 호출 시간)
   ```

---

**호출 지점**:

1. **동기 호출** [llm_service.py:133]:
   ```python
   response = self._call_with_retry(params)
   ```

2. **비동기 호출** [llm_service.py:187]:
   ```python
   response = await self._call_async_with_retry(params)
   ```

---

**예외 처리**:

LLM 호출 실패 시 상위 레이어에서 Fallback 처리:
- **planning_agent.py**: LLM 실패 → 패턴 매칭 (`_analyze_with_patterns`)
- **search_executor.py**: LLM 실패 → 기본 키워드 반환

---

**`_analyze_with_llm()` 함수 [planning_agent.py:183]**:

```python
async def _analyze_with_llm(self, query: str, context: Optional[Dict]):
    # 1. Chat history 포맷팅
    chat_history_text = ""
    if context and context.get("chat_history"):
        chat_history = context["chat_history"]
        formatted_history = []
        for msg in chat_history:
            role = msg.get("role")
            content = msg.get("content")
            if role == "user":
                formatted_history.append(f"사용자: {content}")
            elif role == "assistant":
                formatted_history.append(f"AI: {content}")
        chat_history_text = "\n".join(formatted_history)

    # 2. 🔥 LLM 호출 (JSON 모드)
    result = await self.llm_service.complete_json_async(
        prompt_name="intent_analysis",
        variables={
            "query": query,
            "chat_history": chat_history_text
        },
        temperature=0.0,
        max_tokens=500
    )

    # 3. IntentType 파싱
    intent_str = result.get("intent", "UNCLEAR").upper()
    try:
        intent_type = IntentType[intent_str]
    except KeyError:
        intent_type = IntentType.UNCLEAR

    # 4. Entity 추출
    entities = self._extract_entities(result)

    # 5. IntentResult 반환
    return IntentResult(
        intent_type=intent_type,
        confidence=result.get("confidence", 0.5),
        keywords=result.get("keywords", []),
        reasoning=result.get("reasoning", ""),
        sub_intents=result.get("sub_intents", []),
        is_compound=result.get("is_compound", False),
        entities=entities,
        suggested_agents=[],
        fallback=False
    )
```

**LLM 호출 상세 [llm_service.py:228]**:

```python
async def complete_json_async(self, prompt_name: str, variables: Dict, **kwargs):
    # 1. 프롬프트 로드
    prompt = self.prompt_manager.get(prompt_name, variables)

    # 2. 모델 선택
    model = Config.LLM_DEFAULTS["models"].get(prompt_name, "gpt-4o-mini")

    # 3. API 파라미터 구성
    params = {
        "model": model,
        "messages": [{"role": "system", "content": prompt}],
        "temperature": kwargs.get("temperature", 0.7),
        "max_tokens": kwargs.get("max_tokens", 500),
        "response_format": {"type": "json_object"}
    }

    # 4. OpenAI API 호출
    response = await self.async_client.chat.completions.create(**params)

    # 5. JSON 파싱
    return json.loads(response.choices[0].message.content)
```

**프롬프트 로드 [prompt_manager.py:42]**:

```python
def get(self, prompt_name: str, variables: Dict):
    # 1. 템플릿 로드 (캐싱)
    template = self._load_template(prompt_name, category=None)

    # 2. 변수 치환 (코드 블록 보호)
    prompt = self._safe_format(template, variables)

    return prompt
```

**프롬프트 파일 위치**:
- `backend/app/service_agent/llm_manager/prompts/cognitive/intent_analysis.txt`

**LLM 응답 예시**:
```json
{
  "intent": "LEGAL_CONSULT",
  "confidence": 0.95,
  "keywords": ["전세금", "인상", "5%", "가능"],
  "sub_intents": [],
  "is_compound": false,
  "decomposed_tasks": [],
  "entities": {
    "location": null,
    "price": null,
    "contract_type": "전세",
    "date": null,
    "area": null,
    "action_verbs": ["인상"]
  },
  "reuse_previous_data": false,
  "reasoning": "1단계(유형): 정보 확인형 - '가능한가요?' 포함. 2단계(복잡도): 저 - 단일 개념 확인. 3단계(의도): 법률 정보 확인 → LEGAL_CONSULT"
}
```

**`IntentResult` 객체**:
```python
IntentResult(
    intent_type=IntentType.LEGAL_CONSULT,
    confidence=0.95,
    keywords=["전세금", "인상", "5%", "가능"],
    reasoning="1단계(유형): 정보 확인형...",
    sub_intents=[],
    is_compound=False,
    entities={
        "contract_type": "전세",
        "action_verbs": ["인상"]
    },
    suggested_agents=[],  # 아직 선택 안됨
    fallback=False
)
```

#### 단계 6: 데이터 재사용 로직 [라인 302-353]

**생략** (복잡하므로 필요 시 별도 설명)

#### 단계 7: 🔥 Agent 선택 [라인 459]

```python
suggested_agents = await self.planning_agent.suggest_agents(
    intent_type=intent_result.intent_type,
    query=query,
    keywords=intent_result.keywords
)
```

**다음 섹션에서 상세 설명**

---

## 6. Layer 4: Agent Selection

### 6.1 `suggest_agents()` 전체 흐름

**파일**: `planning_agent.py:459`

```python
async def suggest_agents(
    self,
    intent_type: IntentType,
    query: str,
    keywords: List[str]
) -> List[str]:
    return await self._suggest_agents(intent_type, query, keywords)
```

### 6.2 `_suggest_agents()` 다층 Fallback 구조

**파일**: `planning_agent.py:305`

```python
async def _suggest_agents(
    self,
    intent_type: IntentType,
    query: str,
    keywords: List[str]
) -> List[str]:
```

**처리 흐름**:

```
┌─────────────────────────────────────────────┐
│ 0차: 하드코딩 키워드 필터 (빠른 판단)        │
│ [라인 322-349]                              │
└─────────────┬───────────────────────────────┘
              ↓
        키워드 있음? → Yes → 즉시 반환
              ↓ No
┌─────────────────────────────────────────────┐
│ 1차: LLM Agent 선택 (Primary)               │
│ _select_agents_with_llm()                   │
│ [라인 350-363]                              │
└─────────────┬───────────────────────────────┘
              ↓
        성공? → Yes → 반환
              ↓ No
┌─────────────────────────────────────────────┐
│ 2차: Simplified LLM (Retry)                 │
│ _select_agents_with_llm_simple()            │
│ [라인 365-376]                              │
└─────────────┬───────────────────────────────┘
              ↓
        성공? → Yes → 반환
              ↓ No
┌─────────────────────────────────────────────┐
│ 3차: Safe Defaults (하드코딩 매핑)          │
│ safe_defaults 딕셔너리                      │
│ [라인 378-397]                              │
└─────────────────────────────────────────────┘
```

### 6.3 0차: 하드코딩 키워드 필터

**코드 [라인 322-349]**:

```python
# === 0차: 키워드 기반 필터 (경계 케이스 해결) ===
if intent_type == IntentType.LEGAL_CONSULT:
    # 분석이 필요한 키워드
    analysis_keywords = [
        "비교", "분석", "계산", "평가", "추천", "검토",
        "어떻게", "방법", "차이", "장단점", "괜찮아",
        "해야", "대응", "해결", "조치", "문제"
    ]

    needs_analysis = any(kw in query for kw in analysis_keywords)

    if not needs_analysis:
        logger.info("✅ LEGAL_CONSULT without analysis keywords → search_team only")
        return ["search_team"]  # 🔥 즉시 반환 (LLM 호출 X)
    else:
        logger.info("✅ LEGAL_CONSULT with analysis keywords → search + analysis")
        return ["search_team", "analysis_team"]

if intent_type == IntentType.MARKET_INQUIRY:
    analysis_keywords = ["비교", "분석", "평가", "추천", "차이", "장단점"]
    needs_analysis = any(kw in query for kw in analysis_keywords)

    if not needs_analysis:
        return ["search_team"]
```

**예시**:

| 질문 | Intent | 키워드 검사 | 반환 | LLM 호출 |
|------|--------|------------|------|---------|
| "전세금 5% 인상 가능?" | LEGAL_CONSULT | ❌ (없음) | ["search_team"] | **X** |
| "전세금 3억→10억, 어떻게 해야 해?" | LEGAL_CONSULT | ✅ ("어떻게", "해야") | ["search_team", "analysis_team"] | **X** |
| "강남구 시세 알려줘" | MARKET_INQUIRY | ❌ (없음) | ["search_team"] | **X** |

**목적**:
- ✅ **성능**: LLM 호출 없이 0.01초 내 판단
- ✅ **비용 절감**: API 호출 비용 절약
- ✅ **정확성**: 명확한 케이스는 하드코딩이 더 안정적

### 6.4 1차: LLM Agent 선택

**코드 [라인 350-363]**:

```python
# === 1차: Primary LLM으로 Agent 선택 ===
if self.llm_service:
    try:
        agents = await self._select_agents_with_llm(
            intent_type=intent_type,
            query=query,
            keywords=keywords,
            attempt=1
        )
        if agents:
            logger.info(f"✅ Primary LLM selected agents: {agents}")
            return agents
    except Exception as e:
        logger.warning(f"⚠️ Primary LLM agent selection failed: {e}")
```

**`_select_agents_with_llm()` 함수 [라인 399]**:

```python
async def _select_agents_with_llm(
    self,
    intent_type: IntentType,
    query: str,
    keywords: List[str],
    attempt: int = 1
):
    # 1. 사용 가능한 Agent 정보 수집
    available_agents_info = self._format_available_agents()

    # 2. LLM 호출
    result = await self.llm_service.complete_json_async(
        prompt_name="agent_selection",
        variables={
            "query": query,
            "intent_type": intent_type.value,
            "keywords": ", ".join(keywords),
            "available_agents": available_agents_info
        },
        temperature=0.1,
        max_tokens=500
    )

    # 3. Agent 목록 추출
    selected_agents = result.get("selected_agents", [])

    # 4. 검증
    validated_agents = self._validate_agents(selected_agents)

    return validated_agents
```

**프롬프트 파일**:
- `backend/app/service_agent/llm_manager/prompts/cognitive/agent_selection.txt`

**LLM 응답 예시**:
```json
{
  "selected_agents": ["search_team"],
  "reasoning": "1단계: 단순 정보 조회. 2단계: 저복잡도. 3단계: 독립적. 4단계: 법률 검색만으로 답변 가능",
  "coordination": "single",
  "dependencies": {},
  "estimated_time": 10,
  "confidence": 0.95
}
```

### 6.5 2차: Simplified LLM

**코드 [라인 365-376]**:

```python
# === 2차: Simplified prompt retry ===
if self.llm_service:
    try:
        agents = await self._select_agents_with_llm_simple(
            intent_type=intent_type,
            query=query
        )
        if agents:
            logger.info(f"✅ Simplified LLM selected agents: {agents}")
            return agents
    except Exception as e:
        logger.warning(f"⚠️ Simplified LLM agent selection failed: {e}")
```

**차이점**:
- 프롬프트가 더 간단함 (`agent_selection_simple.txt`)
- 변수가 적음 (query, intent_type만)
- 빠른 응답 우선

### 6.6 3차: Safe Defaults

**코드 [라인 378-397]**:

```python
# === 3차: Safe default agents ===
logger.error("⚠️ All LLM attempts failed, using safe default agents")

safe_defaults = {
    IntentType.LEGAL_CONSULT: ["search_team"],
    IntentType.MARKET_INQUIRY: ["search_team", "analysis_team"],
    IntentType.LOAN_CONSULT: ["search_team", "analysis_team"],
    IntentType.CONTRACT_CREATION: ["document_team"],
    IntentType.CONTRACT_REVIEW: ["search_team", "analysis_team"],
    IntentType.COMPREHENSIVE: ["search_team", "analysis_team"],
    IntentType.RISK_ANALYSIS: ["search_team", "analysis_team"],
    IntentType.UNCLEAR: ["search_team", "analysis_team"],
    IntentType.IRRELEVANT: ["search_team"],
    IntentType.ERROR: ["search_team", "analysis_team"]
}

result = safe_defaults.get(intent_type, ["search_team", "analysis_team"])
logger.info(f"Safe default agents for {intent_type.value}: {result}")
return result
```

**목적**:
- ✅ **안전망**: LLM이 모두 실패해도 기본 동작 보장
- ✅ **가용성**: 시스템이 중단되지 않음

### 6.7 Agent 선택 결과

**예시 질문**: "전세금 5% 인상 가능한가요?"

```python
suggested_agents = ["search_team"]  # 0차 필터에서 결정
```

**State 업데이트**:
```python
intent_result.suggested_agents = ["search_team"]
```

---

## 7. Layer 5: Execution

### 7.1 실행 계획 생성

**파일**: `team_supervisor.py:537`

**코드 [planning_node 라인 537]**:

```python
execution_steps = self._create_execution_plan(
    suggested_agents=intent_result.suggested_agents,
    query=query,
    intent_info=intent_result
)

state["execution_plan"] = execution_steps
state["active_teams"] = [
    self._map_agent_to_team(agent) for agent in intent_result.suggested_agents
]
```

**`_create_execution_plan()` 함수 [라인 537]**:

```python
def _create_execution_plan(
    self,
    suggested_agents: List[str],
    query: str,
    intent_info: IntentResult
) -> List[ExecutionStep]:

    execution_steps = []

    for i, agent_name in enumerate(suggested_agents):
        team_name = self._map_agent_to_team(agent_name)

        step = ExecutionStep(
            step_id=f"step_{i+1}",
            team_name=team_name,
            agent_name=agent_name,
            task_description=f"{team_name} 작업 수행",
            status="pending",
            estimated_time=self._estimate_execution_time(team_name),
            dependencies=[],
            start_time=None,
            end_time=None,
            result=None
        )

        execution_steps.append(step)

    return execution_steps
```

**생성된 ExecutionStep**:
```python
[
    ExecutionStep(
        step_id="step_1",
        team_name="search",
        agent_name="search_team",
        task_description="search 작업 수행",
        status="pending",
        estimated_time=15,
        dependencies=[],
        start_time=None,
        end_time=None,
        result=None
    )
]
```

### 7.2 Plan Ready 알림

**코드 [planning_node 라인 621]**:

```python
await progress_callback("plan_ready", {
    "intent": intent_result.intent_type.value,
    "confidence": intent_result.confidence,
    "keywords": intent_result.keywords,
    "execution_steps": [
        {
            "step_id": step.step_id,
            "team_name": step.team_name,
            "task_description": step.task_description,
            "estimated_time": step.estimated_time,
            "status": step.status
        }
        for step in execution_steps
    ],
    "estimated_total_time": sum(step.estimated_time for step in execution_steps)
})
```

**WebSocket 메시지**:
```json
{
  "type": "plan_ready",
  "intent": "법률상담",
  "confidence": 0.95,
  "keywords": ["전세금", "인상", "5%", "가능"],
  "execution_steps": [
    {
      "step_id": "step_1",
      "team_name": "search",
      "task_description": "search 작업 수행",
      "estimated_time": 15,
      "status": "pending"
    }
  ],
  "estimated_total_time": 15,
  "timestamp": "2025-01-27T10:30:02.000Z"
}
```

### 7.3 `execute_teams_node` 실행

**파일**: `team_supervisor.py:650`

```python
async def execute_teams_node(self, state: MainSupervisorState):
    state["current_phase"] = "executing"

    active_teams = state.get("active_teams", [])
    execution_plan = state.get("execution_plan", [])

    # WebSocket: 실행 시작 알림
    await progress_callback("execution_start", {
        "message": "작업 실행을 시작합니다...",
        "execution_steps": [...]
    })

    # 팀별 실행
    for team_name in active_teams:
        if team_name == "search":
            await self._execute_search_team(state)
        elif team_name == "analysis":
            await self._execute_analysis_team(state)
        elif team_name == "document":
            await self._execute_document_team(state)

    return state
```

### 7.4 SearchExecutor 실행

**`_execute_search_team()` 함수 [라인 774]**:

```python
async def _execute_search_team(self, state: MainSupervisorState):
    team_name = "search"
    state["completed_teams"].append(team_name)

    try:
        # SearchExecutor 가져오기
        search_executor = self.teams[team_name]

        # Progress Callback 설정
        session_id = state.get("session_id")
        progress_callback = self._progress_callbacks.get(session_id)
        search_executor.progress_callback = progress_callback

        # 초기 State 생성
        search_team_state = SearchTeamState(
            query=state["query"],
            keywords=state.get("planning_state", {}).get("analyzed_intent", {}).get("keywords", []),
            search_scope=None,  # SearchExecutor가 자동 결정
            shared_context={
                "query": state["query"],
                "intent_type": state.get("planning_state", {}).get("analyzed_intent", {}).get("intent_type")
            },
            team_name="search",
            status="pending",
            start_time=None,
            end_time=None
        )

        # 🔥 SearchExecutor 실행 (LangGraph 서브그래프)
        final_search_state = await search_executor.app.ainvoke(search_team_state)

        # 결과 저장
        state["search_team_state"] = final_search_state
        state["team_results"]["search"] = final_search_state

    except Exception as e:
        logger.error(f"Search team failed: {e}")
        state["failed_teams"].append(team_name)
        state["error_log"].append(f"Search team error: {str(e)}")
```

### 7.5 SearchExecutor 내부 흐름

**파일**: `search_executor.py`

**서브그래프 구조**:
```
START
  ↓
prepare_search_node  ← 키워드 추출 & 검색 범위 결정
  ↓
route_search_node    ← 검색 실행 여부 판단
  ↓
execute_search_node  ← 실제 검색 (HybridLegalSearch)
  ↓
aggregate_results_node ← 결과 집계
  ↓
finalize_node        ← 최종 정리
  ↓
END
```

**`execute_search_node()` 함수**:

```python
async def execute_search_node(self, state: SearchTeamState):
    # 검색 범위에 따라 Tool 선택
    search_scope = state.get("search_scope", {})

    results = {}

    # Legal Search
    if search_scope.get("legal_search"):
        legal_results = await self._search_legal(state)
        results["legal"] = legal_results

    # Market Data
    if search_scope.get("market_data"):
        market_results = await self._search_market(state)
        results["market"] = market_results

    # Real Estate
    if search_scope.get("real_estate_search"):
        estate_results = await self._search_real_estate(state)
        results["real_estate"] = estate_results

    state["results"] = results
    return state
```

**`_search_legal()` 함수**:

```python
async def _search_legal(self, state: SearchTeamState):
    query = state["query"]
    keywords = state.get("keywords", {})

    # HybridLegalSearch 호출
    search_results = await self.legal_search_tool.search(
        query=query,
        params={
            "mode": "hybrid",
            "limit": 10
        }
    )

    return search_results
```

### 7.6 HybridLegalSearch 실행

**파일**: `hybrid_legal_search.py:620`

```python
async def search(self, query: str, params: Dict[str, Any] = None):
    params = params or {}
    mode = params.get('mode', 'hybrid')

    # Hybrid 검색
    if mode == 'hybrid':
        results = self.hybrid_search(
            query=query,
            limit=params.get('limit', 10),
            doc_type=params.get('doc_type'),
            category=params.get('category')
        )

    return {
        "status": "success",
        "data": results,
        "count": len(results),
        "query": query,
        "mode": mode
    }
```

**`hybrid_search()` 함수 [라인 429]**:

```python
def hybrid_search(
    self,
    query: str,
    limit: int = 10,
    doc_type: Optional[str] = None,
    category: Optional[str] = None
):
    # 1. 쿼리 전처리
    enhanced_query = self._enhance_query_for_search(query)

    # 2. FAISS 벡터 검색
    where_filters = {}
    if doc_type:
        where_filters["doc_type"] = doc_type

    vector_results = self.vector_search(
        enhanced_query,
        n_results=limit * 2,
        where_filters=where_filters
    )

    # 3. SQLite로 메타데이터 보강
    enriched_results = []

    for i, doc_id in enumerate(vector_results["ids"]):
        metadata = vector_results["metadatas"][i]
        document = vector_results["documents"][i]
        distance = vector_results["distances"][i]

        # 법령 정보 조회
        law_title = metadata.get("law_title")
        article_number = metadata.get("article_number")

        article = self.get_article_by_number(law_title, article_number)

        if article:
            enriched_results.append({
                "chunk_id": doc_id,
                "law_title": law_title,
                "article_number": article_number,
                "article_title": article.get("article_title", ""),
                "content": document,
                "relevance_score": 1 - distance
            })

    return enriched_results
```

**검색 결과 예시**:
```python
[
    {
        "chunk_id": "chunk_12345",
        "law_title": "주택임대차보호법",
        "article_number": "제7조",
        "article_title": "차임 등의 증액 청구",
        "content": "제7조(차임 등의 증액 청구) ① 당사자는 약정한 차임이나 보증금이 임차주택에 관한 조세, 공과금, 그 밖의 부담의 증감이나 경제 사정의 변동으로 인하여 적절하지 아니하게 된 경우에는 장래의 차임이나 보증금에 대하여 증감을 청구할 수 있다. 그러나 증액의 경우에는 대통령령으로 정하는 기준에 따른 비율을 초과하지 못한다.",
        "relevance_score": 0.92
    },
    {
        "chunk_id": "chunk_12346",
        "law_title": "주택임대차보호법 시행령",
        "article_number": "제2조",
        "article_title": "차임 등의 증액 청구의 기준",
        "content": "제2조(차임 등의 증액 청구의 기준) 법 제7조 단서에 따른 차임이나 보증금의 증액 청구는 청구 당시의 차임 또는 보증금의 20분의 1의 금액을 초과하지 못한다.",
        "relevance_score": 0.88
    }
]
```

---

## 8. Layer 6: Response Generation

### 8.1 `aggregate_results_node` [라인 1259]

**역할**: 팀별 결과 집계

```python
async def aggregate_results_node(self, state: MainSupervisorState):
    state["current_phase"] = "aggregating"

    team_results = state.get("team_results", {})
    aggregated_results = {}

    # Search Team 결과 집계
    if "search" in team_results:
        search_data = team_results["search"].get("results", {})
        aggregated_results["search_data"] = {
            "legal": search_data.get("legal", []),
            "market": search_data.get("market", []),
            "real_estate": search_data.get("real_estate", [])
        }

    # Analysis Team 결과 집계
    if "analysis" in team_results:
        analysis_data = team_results["analysis"].get("analysis_result", {})
        aggregated_results["analysis_data"] = analysis_data

    state["aggregated_results"] = aggregated_results

    return state
```

### 8.2 `generate_response_node` [라인 1347]

**역할**: 최종 답변 생성 (5단계 Progress 전송)

#### 전체 흐름 (85% → 87% → 90% → 92% → 95%)

```python
async def generate_response_node(self, state: MainSupervisorState):
    state["current_phase"] = "response_generation"

    session_id = state.get("session_id")
    progress_callback = self._progress_callbacks.get(session_id)

    # 🆕 Step 1: 85% - 최종 답변 생성 시작
    if progress_callback:
        await progress_callback("supervisor_phase_change", {
            "supervisorPhase": "finalizing",
            "supervisorProgress": 85,
            "message": "최종 답변을 생성하고 있습니다"
        })

    # Intent 체크 (IRRELEVANT / UNCLEAR 처리)
    planning_state = state.get("planning_state", {})
    intent_type = planning_state.get("analyzed_intent", {}).get("intent_type", "")

    if intent_type == "irrelevant" or (intent_type == "unclear" and confidence < 0.3):
        response = self._generate_out_of_scope_response(state)
    else:
        aggregated_results = state.get("aggregated_results", {})

        # 🆕 Step 2: 87% - 답변 내용 작성 시작
        if progress_callback:
            await progress_callback("supervisor_phase_change", {
                "supervisorPhase": "finalizing",
                "supervisorProgress": 87,
                "message": "답변 내용을 작성하고 있습니다"
            })

        # 🔥 LLM 호출 (6-9초 소요)
        if self.planning_agent.llm_service:
            response = await self._generate_llm_response(state)
        else:
            response = self._generate_simple_response(state)

    # 🆕 Step 3: 90% - 답변 검증
    if progress_callback:
        await progress_callback("supervisor_phase_change", {
            "supervisorPhase": "finalizing",
            "supervisorProgress": 90,
            "message": "답변을 검증하고 있습니다"
        })

    # 🆕 Step 4: 95% - 답변 생성 완료
    if progress_callback:
        await progress_callback("supervisor_phase_change", {
            "supervisorPhase": "finalizing",
            "supervisorProgress": 95,
            "message": "답변 생성 완료"
        })

    state["final_response"] = response
    state["status"] = "completed"

    # 🆕 Step 5: 92% - Long-term Memory 저장 (RELEVANT만)
    user_id = state.get("user_id")
    if user_id and intent_type not in ["irrelevant", "unclear"]:
        if progress_callback:
            await progress_callback("supervisor_phase_change", {
                "supervisorPhase": "finalizing",
                "supervisorProgress": 92,
                "message": "대화를 저장하고 있습니다"
            })

        # Memory 저장 (3초 소요)
        async for db_session in get_async_db():
            memory_service = LongTermMemoryService(db_session)
            await memory_service.save_conversation(...)
            break

    # 실행 시간 계산
    if state.get("start_time"):
        state["end_time"] = datetime.now()
        state["total_execution_time"] = (state["end_time"] - state["start_time"]).total_seconds()

    return state
```

**Progress 전송 순서**:

| Step | Progress | 메시지 | 소요 시간 | 설명 |
|------|----------|--------|----------|------|
| 1 | 85% | "최종 답변을 생성하고 있습니다" | 0ms | LLM 호출 전 |
| 2 | 87% | "답변 내용을 작성하고 있습니다" | 6-9초 | LLM 작업 중 |
| 3 | 90% | "답변을 검증하고 있습니다" | 0ms | LLM 완료 후 |
| 4 | 95% | "답변 생성 완료" | 0ms | Response 객체 생성 |
| 5 | 92% | "대화를 저장하고 있습니다" | 3초 | Memory 저장 (선택적) |

**💡 핵심 개선사항 (v1.2)**:
- **Before**: 85% → [11초 멈춤] → 95%
- **After**: 85% → 87% → 90% → 92% → 95% (연속적 진행)

**`generate_final_response()` 함수 [llm_service.py:332]**:

```python
async def generate_final_response(
    self,
    query: str,
    aggregated_results: Dict[str, Any],
    intent_info: Dict[str, Any]
) -> Dict[str, Any]:

    # 변수 준비
    intent_type = intent_info.get("intent_type", "알 수 없음")
    keywords = intent_info.get("keywords", [])
    aggregated_json = self._safe_json_dumps(aggregated_results)[:4000]

    variables = {
        "query": query,
        "intent_type": intent_type,
        "keywords": ", ".join(keywords),
        "aggregated_results": aggregated_json
    }

    # LLM 호출 (response_synthesis 프롬프트)
    response_json = await self.complete_json_async(
        prompt_name="response_synthesis",
        variables=variables,
        temperature=0.3,
        max_tokens=1000
    )

    return {
        "type": "answer",
        "answer": response_json.get("answer", ""),
        "structured_data": {
            "sections": self._create_sections(response_json, intent_info),
            "metadata": {
                "confidence": response_json.get("confidence", 0.8),
                "sources": response_json.get("sources", [])
            }
        },
        "teams_used": list(aggregated_results.keys()),
        "data": aggregated_results
    }
```

**프롬프트 파일**:
- `backend/app/service_agent/llm_manager/prompts/execution/response_synthesis.txt`

**LLM 응답 예시**:
```json
{
  "answer": "주택임대차보호법 제7조 및 동법 시행령 제2조에 따라, 전세금 증액은 청구 당시 전세금의 5% 이내로 제한됩니다. 따라서 5% 인상은 법적으로 가능합니다.",
  "confidence": 0.95,
  "sources": [
    "주택임대차보호법 제7조",
    "주택임대차보호법 시행령 제2조"
  ],
  "details": {
    "legal_basis": "주택임대차보호법 제7조 단서 및 시행령 제2조에서 차임이나 보증금의 증액은 청구 당시 금액의 20분의 1(5%)을 초과할 수 없다고 규정하고 있습니다."
  }
}
```

**최종 응답 객체**:
```python
{
    "type": "answer",
    "answer": "주택임대차보호법 제7조 및 동법 시행령 제2조에 따라...",
    "structured_data": {
        "sections": [
            {
                "title": "핵심 답변",
                "content": "전세금 증액은 5% 이내로 제한됩니다.",
                "icon": "target",
                "priority": "high"
            },
            {
                "title": "법적 근거",
                "content": "주택임대차보호법 제7조 단서...",
                "icon": "scale",
                "priority": "medium"
            }
        ],
        "metadata": {
            "confidence": 0.95,
            "sources": ["주택임대차보호법 제7조", "..."]
        }
    },
    "teams_used": ["search"],
    "data": {
        "search_data": {
            "legal": [...]
        }
    }
}
```

---

### 📌 보충 설명 3: UI 섹션 생성 로직

**역할**: LLM이 생성한 JSON 응답을 UI 컴포넌트용 섹션 배열로 변환

**위치**: `llm_service.py:446` (_create_sections)

---

**`_create_sections()` 함수 [llm_service.py:446]**:

```python
def _create_sections(self, response_json: Dict[str, Any], intent_info: Dict[str, Any]) -> List[Dict[str, Any]]:
    """JSON 응답을 UI 섹션으로 변환"""
    sections = []

    # 1. 핵심 답변 섹션 (최우선 표시)
    if response_json.get("answer"):
        sections.append({
            "title": "핵심 답변",
            "content": response_json["answer"],
            "icon": "target",               # UI 아이콘
            "priority": "high",              # 표시 우선순위
            "expandable": False              # 접기/펼치기 불가 (항상 표시)
        })

    # 2. 세부 정보 섹션들 (details 객체에서 추출)
    details = response_json.get("details", {})

    # 2-1. 법적 근거 섹션
    if details.get("legal_basis"):
        sections.append({
            "title": "법적 근거",
            "content": details["legal_basis"],
            "icon": "scale",                 # 저울 아이콘
            "priority": "medium",
            "expandable": True               # 접기/펼치기 가능
        })

    # 2-2. 데이터 분석 섹션
    if details.get("data_analysis"):
        sections.append({
            "title": "데이터 분석",
            "content": details["data_analysis"],
            "icon": "chart",                 # 차트 아이콘
            "priority": "medium",
            "expandable": True
        })

    # 2-3. 고려사항 섹션
    if details.get("considerations"):
        sections.append({
            "title": "고려사항",
            "content": details["considerations"],
            "icon": "alert",                 # 경고 아이콘
            "type": "checklist",             # 체크리스트 형식
            "priority": "medium",
            "expandable": True
        })

    # 3. 추천사항 섹션
    if response_json.get("recommendations"):
        sections.append({
            "title": "추천사항",
            "content": response_json["recommendations"],
            "icon": "lightbulb",             # 전구 아이콘
            "type": "checklist",
            "priority": "high",
            "expandable": True
        })

    # 4. 추가 정보 섹션
    if response_json.get("additional_info"):
        sections.append({
            "title": "참고사항",
            "content": response_json["additional_info"],
            "icon": "info",                  # 정보 아이콘
            "priority": "low",               # 낮은 우선순위
            "expandable": True
        })

    # 5. Fallback: 섹션이 없으면 기본 답변 섹션 생성
    if not sections and response_json.get("answer"):
        sections.append({
            "title": "답변",
            "content": response_json.get("answer", "답변을 생성할 수 없습니다."),
            "icon": "message",
            "priority": "high",
            "expandable": False
        })

    return sections
```

---

**변환 예시**:

**입력 (LLM JSON 응답)**:
```json
{
  "answer": "전세금 증액은 5% 이내로 제한됩니다.",
  "confidence": 0.95,
  "sources": ["주택임대차보호법 제7조"],
  "details": {
    "legal_basis": "주택임대차보호법 제7조 단서 및 시행령 제2조에서 차임이나 보증금의 증액은 청구 당시 금액의 20분의 1(5%)을 초과할 수 없다고 규정하고 있습니다.",
    "considerations": "단, 양 당사자가 합의하면 5%를 초과하는 증액도 가능합니다."
  },
  "recommendations": "계약 갱신 시 증액률을 사전에 확인하고, 부당한 증액 요구는 거부할 수 있습니다."
}
```

**출력 (UI 섹션 배열)**:
```json
[
  {
    "title": "핵심 답변",
    "content": "전세금 증액은 5% 이내로 제한됩니다.",
    "icon": "target",
    "priority": "high",
    "expandable": false
  },
  {
    "title": "법적 근거",
    "content": "주택임대차보호법 제7조 단서 및 시행령 제2조에서...",
    "icon": "scale",
    "priority": "medium",
    "expandable": true
  },
  {
    "title": "고려사항",
    "content": "단, 양 당사자가 합의하면 5%를 초과하는 증액도 가능합니다.",
    "icon": "alert",
    "type": "checklist",
    "priority": "medium",
    "expandable": true
  },
  {
    "title": "추천사항",
    "content": "계약 갱신 시 증액률을 사전에 확인하고...",
    "icon": "lightbulb",
    "type": "checklist",
    "priority": "high",
    "expandable": true
  }
]
```

---

**섹션 우선순위 정렬**:

프론트엔드에서는 `priority` 값에 따라 표시 순서를 조정:
- **high**: 핵심 답변, 추천사항 → 상단 표시
- **medium**: 법적 근거, 데이터 분석, 고려사항 → 중간 표시
- **low**: 참고사항 → 하단 표시

---

**호출 지점** [llm_service.py:403]:

```python
return {
    "type": "answer",
    "answer": response_json.get("answer", ""),
    "structured_data": {
        "sections": self._create_sections(response_json, intent_info),  # ← 여기서 호출
        "metadata": {
            "confidence": response_json.get("confidence", 0.8),
            "sources": response_json.get("sources", [])
        }
    }
}
```

---

### 8.3 WebSocket 최종 전송

**코드 [_process_query_async 라인 1039]**:

```python
await conn_mgr.send_message(session_id, {
    "type": "final_response",
    "response": final_state["final_response"],
    "timestamp": datetime.now().isoformat()
})
```

**클라이언트 수신**:
```json
{
  "type": "final_response",
  "response": {
    "type": "answer",
    "answer": "주택임대차보호법 제7조 및 동법 시행령 제2조에 따라, 전세금 증액은 청구 당시 전세금의 5% 이내로 제한됩니다. 따라서 5% 인상은 법적으로 가능합니다.",
    "structured_data": {
      "sections": [...]
    }
  },
  "timestamp": "2025-01-27T10:30:05.500Z"
}
```

---

### 📌 보충 설명 4: Progress Callback 흐름 전체 다이어그램

**역할**: WebSocket을 통해 실시간 진행 상황을 클라이언트에 전달하는 메커니즘

**위치**:
- 등록: `chat_api.py:689` (progress_callback 함수 정의)
- 전달: `chat_api.py:704` → `team_supervisor.py:1796` (등록)
- 사용: `team_supervisor.py` 전체 노드에서 호출

---

**전체 흐름 다이어그램**:

```
┌─────────────────────────────────────────────────────────────────────┐
│ Layer 0: WebSocket 연결                                             │
│ [chat_api.py:689]                                                   │
└────────────────────────┬────────────────────────────────────────────┘
                         ↓
          ┌──────────────────────────────┐
          │ progress_callback 함수 정의  │ [chat_api.py:689]
          │                              │
          │ async def progress_callback( │
          │     event_type: str,         │
          │     event_data: dict         │
          │ ):                           │
          │     await conn_mgr.send_message(session_id, {
          │         "type": event_type,  │
          │         **event_data,        │
          │         "timestamp": ...     │
          │     })                       │
          └──────────────┬───────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────────────┐
│ Layer 1: Supervisor에 Callback 등록                                 │
│ [chat_api.py:704 → team_supervisor.py:1796]                        │
└────────────────────────┬────────────────────────────────────────────┘
                         ↓
          ┌──────────────────────────────┐
          │ Supervisor.process_query()   │ [team_supervisor.py:1769]
          │                              │
          │ if progress_callback:        │
          │     self._progress_callbacks[session_id] = progress_callback
          └──────────────┬───────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────────────┐
│ Layer 2: LangGraph 노드들에서 Callback 호출                          │
│ [team_supervisor.py 각 노드]                                         │
└────────────────────────┬────────────────────────────────────────────┘
                         ↓
          ┌──────────────────────────────────────────────┐
          │  progress_callback = self._progress_callbacks.get(session_id)
          │  if progress_callback:                       │
          │      await progress_callback(event_type, event_data)
          └──────────────┬───────────────────────────────┘
                         ↓
          ┌─────────────────────────────────────────────────────────┐
          │ 실제 호출 예시들 (event_type별)                          │
          │                                                          │
          │ 1. supervisor_phase_change [line 229, 255, 1000, ...]   │
          │    → {"supervisorPhase": "analyzing", ...}              │
          │                                                          │
          │ 2. planning_start [line 267]                            │
          │    → {"message": "계획을 수립하고 있습니다..."}          │
          │                                                          │
          │ 3. analysis_start [line 290]                            │
          │    → {"message": "질문을 분석하고 있습니다..."}          │
          │                                                          │
          │ 4. plan_ready [line 589]                                │
          │    → {"intent": "LEGAL_CONSULT", ...}                   │
          │                                                          │
          │ 5. agent_steps_initialized [line 610]                   │
          │    → {"agentName": "search_team", "steps": [...]}       │
          │                                                          │
          │ 6. agent_step_progress [line 627]                       │
          │    → {"stepId": "search_step_1", "status": "completed"} │
          │                                                          │
          │ 7. todo_updated [line 1086, 1114, 1137, ...]            │
          │    → {"execution_steps": [...]}                         │
          │                                                          │
          │ 8. data_reuse_notification [line 376]                   │
          │    → {"reused_teams": ["search"], ...}                  │
          │                                                          │
          │ 9. execution_start [line 1014]                          │
          │    → {"execution_steps": [...]}                         │
          │                                                          │
          │ 10. error [line 1861]                                   │
          │     → {"error": "...", "message": "..."}                │
          └──────────────┬──────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────────────┐
│ Layer 3: WebSocket 메시지 전송                                       │
│ [chat_api.py:691]                                                   │
└────────────────────────┬────────────────────────────────────────────┘
                         ↓
          ┌──────────────────────────────┐
          │ conn_mgr.send_message()      │
          │                              │
          │ await websocket.send_json({  │
          │     "type": event_type,      │
          │     **event_data,            │
          │     "timestamp": "..."       │
          │ })                           │
          └──────────────┬───────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────────────┐
│ 클라이언트 수신                                                       │
│ Frontend (React/TypeScript)                                         │
└─────────────────────────────────────────────────────────────────────┘
```

---

**타임라인 예시 (실제 메시지 순서)**:

```
시간          Event Type                     Progress   메시지
────────────────────────────────────────────────────────────────────
0.00s      supervisor_phase_change          5%        "질문을 접수하고 있습니다"
                                                       (dispatching)

0.10s      supervisor_phase_change          10%       "질문을 분석하고 계획을 수립하고 있습니다"
                                                       (analyzing)

0.12s      planning_start                   -         "계획을 수립하고 있습니다..."

0.15s      analysis_start                   -         "질문을 분석하고 있습니다..."

0.80s      plan_ready                       -         {intent: "LEGAL_CONSULT", ...}

0.82s      agent_steps_initialized          -         {agentName: "search_team", ...}

0.85s      supervisor_phase_change          30%       "작업을 실행하고 있습니다"
                                                       (executing)

0.88s      execution_start                  -         "작업 실행을 시작합니다..."

0.90s      todo_updated                     -         {execution_steps: [...]}
                                                       (search_team → in_progress)

0.95s      agent_step_progress              -         {stepId: "search_step_1", status: "completed"}

1.50s      agent_step_progress              -         {stepId: "search_step_2", status: "completed"}

2.30s      todo_updated                     -         {execution_steps: [...]}
                                                       (search_team → completed)

2.35s      supervisor_phase_change          75%       "결과를 정리하고 있습니다"
                                                       (finalizing)

2.40s      supervisor_phase_change          85%       "최종 답변을 생성하고 있습니다"
                                                       (finalizing - LLM start)

2.42s      supervisor_phase_change          87%       "답변 내용을 작성하고 있습니다"
                                                       (finalizing - content writing)

6.50s      supervisor_phase_change          90%       "답변을 검증하고 있습니다"
                                                       (finalizing - validation)

6.52s      supervisor_phase_change          95%       "답변 생성 완료"
                                                       (finalizing - LLM complete)

6.75s      final_response                   100%      {type: "answer", answer: "..."}
```

---

**Callback 등록 및 정리**:

**등록** [team_supervisor.py:1796]:
```python
if progress_callback:
    self._progress_callbacks[session_id] = progress_callback
    logger.debug(f"Progress callback registered for session: {session_id}")
```

**사용** [team_supervisor.py:227 예시]:
```python
progress_callback = self._progress_callbacks.get(session_id) if session_id else None
if progress_callback:
    try:
        await progress_callback("supervisor_phase_change", {
            "supervisorPhase": "dispatching",
            "supervisorProgress": 5,
            "message": "질문을 접수하고 있습니다"
        })
    except Exception as e:
        logger.error(f"Failed to send progress update: {e}")
```

**정리** [team_supervisor.py:1849]:
```python
if session_id in self._progress_callbacks:
    del self._progress_callbacks[session_id]
    logger.debug(f"Progress callback cleaned up for session: {session_id}")
```

---

**Team 실행 시 Callback 전달**:

각 Team Executor는 Supervisor로부터 progress_callback을 받아서 내부 작업 진행 상황을 보고합니다.

**전달** [team_supervisor.py:1264]:
```python
team.progress_callback = progress_callback
```

**Team 내부 사용 예시** [search_executor.py]:
```python
if self.progress_callback:
    await self.progress_callback("agent_step_progress", {
        "agentName": "search_team",
        "stepId": "search_step_2",
        "status": "in_progress",
        "message": "법률 데이터를 검색하고 있습니다..."
    })
```

---

**에러 처리**:

Callback 호출 중 에러가 발생해도 워크플로우는 계속 진행됩니다.

```python
try:
    await progress_callback(event_type, event_data)
except Exception as e:
    logger.error(f"Failed to send progress update: {e}")
    # 워크플로우는 계속 진행 (WebSocket 문제로 멈추면 안 됨)
```

---

**주요 Event Type 10가지**:

| Event Type | 발생 시점 | 데이터 |
|-----------|---------|-------|
| `supervisor_phase_change` | 각 Phase 전환 시 | supervisorPhase, supervisorProgress, message |
| `planning_start` | 계획 수립 시작 | message |
| `analysis_start` | 의도 분석 시작 | message, stage |
| `plan_ready` | 계획 수립 완료 | intent, confidence, execution_steps, ... |
| `agent_steps_initialized` | Agent 작업 단계 초기화 | agentName, steps, totalSteps |
| `agent_step_progress` | Agent 작업 단계 진행 | stepId, stepIndex, status, message |
| `todo_updated` | 실행 작업 상태 변경 | execution_steps |
| `data_reuse_notification` | 이전 데이터 재사용 | reused_teams, reused_from_message |
| `execution_start` | 실행 시작 | execution_steps, intent, confidence |
| `error` | 에러 발생 | error, message |

---

### 📌 보충 설명 5: PostgreSQL Checkpointer (상태 저장 메커니즘)

**역할**: LangGraph 워크플로우의 상태를 PostgreSQL에 저장하여 대화 이력 및 중단-재개 기능 제공

**위치**:
- Checkpointer 관리: `checkpointer.py`
- Supervisor 초기화: `team_supervisor.py:1680` (_ensure_checkpointer)
- 실제 사용: `team_supervisor.py:1843` (ainvoke 호출 시 config 전달)

---

**Checkpointer 개념**:

LangGraph의 Checkpointer는 워크플로우 실행 중 각 노드의 State를 자동으로 저장합니다.
이를 통해 다음 기능들을 제공합니다:

1. **대화 이력 관리**: 사용자-챗봇 간 대화를 thread_id별로 저장
2. **중단-재개 (HITL)**: 사용자 확인이 필요한 시점에서 interrupt() 호출 후 나중에 재개
3. **타임 트래블**: 과거 특정 시점의 State로 돌아가기
4. **상태 검사**: 현재 워크플로우 진행 상태 확인

---

**초기화 흐름**:

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. Supervisor 생성 (enable_checkpointing=True)                  │
│    [team_supervisor.py:57]                                      │
│                                                                  │
│    self.enable_checkpointing = enable_checkpointing             │
│    self.checkpointer = None                                     │
│    self._checkpointer_initialized = False                       │
└────────────────────────┬────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│ 2. 첫 번째 쿼리 처리 시 _ensure_checkpointer() 호출              │
│    [team_supervisor.py:1792]                                    │
│                                                                  │
│    await self._ensure_checkpointer()                            │
└────────────────────────┬────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│ 3. PostgreSQL 연결 및 Checkpointer 생성                          │
│    [team_supervisor.py:1680-1714]                               │
│                                                                  │
│    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
│    from app.core.config import settings                         │
│                                                                  │
│    # PostgreSQL 연결 문자열                                      │
│    DB_URI = settings.postgres_url                               │
│    # "postgresql://postgres:password@localhost:5432/real_estate"
│                                                                  │
│    # Async context manager 생성 및 진입                          │
│    self._checkpoint_cm = AsyncPostgresSaver.from_conn_string(DB_URI)
│    self.checkpointer = await self._checkpoint_cm.__aenter__()   │
│                                                                  │
│    # PostgreSQL 테이블 생성 (최초 1회)                           │
│    await self.checkpointer.setup()                              │
└────────────────────────┬────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│ 4. 생성된 테이블 (PostgreSQL)                                    │
│                                                                  │
│    - checkpoints: 각 노드 실행 후 State 스냅샷 저장              │
│    - checkpoint_blobs: 대용량 State 데이터 (blob 형태)           │
│    - checkpoint_writes: State 변경 사항 기록                     │
└────────────────────────┬────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│ 5. Graph 재컴파일 (Checkpointer와 함께)                          │
│    [team_supervisor.py:1708, 1760]                              │
│                                                                  │
│    self._build_graph_with_checkpointer()                        │
│    self.app = workflow.compile(checkpointer=self.checkpointer)  │
└─────────────────────────────────────────────────────────────────┘
```

---

**Checkpointer 사용 (ainvoke 시)**:

**코드** [team_supervisor.py:1832-1846]:

```python
# Checkpointing이 활성화되어 있으면 config에 thread_id 전달
if self.checkpointer:
    # chat_session_id를 thread_id로 사용 (Chat History & State Endpoints)
    # chat_session_id가 없으면 session_id (HTTP) 사용 (하위 호환성)
    thread_id = chat_session_id if chat_session_id else session_id

    config = {
        "configurable": {
            "thread_id": thread_id  # PostgreSQL에 이 ID로 상태 저장
        }
    }

    logger.info(f"Running with checkpointer (thread_id: {thread_id})")
    final_state = await self.app.ainvoke(initial_state, config=config)
else:
    logger.info("Running without checkpointer")
    final_state = await self.app.ainvoke(initial_state)
```

**thread_id의 의미**:
- **chat_session_id**: PostgreSQL `chat_sessions` 테이블의 session_id (대화 세션)
- **session_id**: WebSocket 세션 ID (HTTP 요청 시 사용)

같은 `thread_id`로 여러 번 쿼리를 실행하면, 이전 대화 이력을 불러와서 Context에 포함시킵니다.

---

**State 저장 과정** (자동):

```
사용자 쿼리 입력
    ↓
┌─────────────────────────────────────────┐
│ LangGraph 워크플로우 실행               │
└──────────┬──────────────────────────────┘
           ↓
┌──────────────────────────────────────────────────────────────┐
│ 각 노드 실행 후 Checkpointer가 자동으로 State 저장           │
│                                                               │
│ initialize_node 완료                                          │
│   → checkpoints 테이블에 INSERT                               │
│   → thread_id: "session-abc123"                              │
│   → checkpoint_ns: ""                                        │
│   → checkpoint_id: "uuid-1"                                  │
│   → parent_checkpoint_id: NULL                               │
│   → values: {query: "...", planning_state: None, ...}       │
│                                                               │
│ planning_node 완료                                            │
│   → checkpoints 테이블에 INSERT                               │
│   → checkpoint_id: "uuid-2"                                  │
│   → parent_checkpoint_id: "uuid-1"                           │
│   → values: {query: "...", planning_state: {...}, ...}      │
│                                                               │
│ execute_teams_node 완료                                       │
│   → checkpoints 테이블에 INSERT                               │
│   → checkpoint_id: "uuid-3"                                  │
│   → parent_checkpoint_id: "uuid-2"                           │
│   → values: {query: "...", team_results: {...}, ...}        │
│                                                               │
│ ... (모든 노드마다 자동 저장)                                 │
└──────────────────────────────────────────────────────────────┘
```

---

**Chat History 불러오기 과정**:

**코드** [team_supervisor.py:202-224]:

```python
async def initialize_node(self, state: MainSupervisorState):
    """초기화 노드 - Chat History 불러오기"""

    # Checkpointer를 통해 현재 thread_id의 State History 조회
    if self.checkpointer:
        session_id = state.get("session_id")
        config = {"configurable": {"thread_id": session_id}}

        # get_state_history()로 이전 State들 가져오기
        state_history = await self.checkpointer.aget_state_history(config)

        # State History에서 chat messages 추출
        chat_history = []
        async for checkpoint in state_history:
            # checkpoint.values에 이전 State가 저장되어 있음
            if checkpoint.values.get("final_response"):
                chat_history.append({
                    "role": "assistant",
                    "content": checkpoint.values["final_response"]["answer"]
                })
            if checkpoint.values.get("query"):
                chat_history.append({
                    "role": "user",
                    "content": checkpoint.values["query"]
                })

        # planning_state에 chat_history 포함
        state["planning_state"]["chat_history"] = chat_history
```

**효과**:
- 이전 대화를 Intent Analysis 및 Agent Selection에 활용
- "그거" "아까" 같은 지시어 해석 가능

---

**HITL (Human-in-the-Loop) 지원**:

**중단** [document_executor.py - aggregate_node]:
```python
from langgraph.types import interrupt

# 사용자 승인이 필요한 시점
approval_data = {
    "contract_draft": contract_draft,
    "risk_analysis": risk_analysis
}

# 워크플로우 중단 및 사용자에게 데이터 전송
user_response = interrupt(approval_data)

# 사용자가 approve/modify/reject 응답하면 여기서 재개됨
if user_response["action"] == "approve":
    # 계속 진행
    ...
```

**재개** [chat_api.py:797]:
```python
from langgraph.types import Command

# 사용자 피드백과 함께 워크플로우 재개
result = await supervisor.app.ainvoke(
    Command(resume=user_feedback),  # 중단된 interrupt()로 전달
    config={"configurable": {"thread_id": session_id}}
)
```

**흐름**:
```
Client → interrupt_response → Command(resume=feedback)
→ 중단된 interrupt() 지점에서 재개 → 워크플로우 계속 실행
```

---

**PostgreSQL 테이블 구조**:

**checkpoints** 테이블:
```sql
CREATE TABLE checkpoints (
    thread_id TEXT,             -- 대화 세션 ID
    checkpoint_ns TEXT,         -- Namespace (subgraph용)
    checkpoint_id UUID,         -- 고유 Checkpoint ID
    parent_checkpoint_id UUID,  -- 이전 Checkpoint ID (연결 리스트)
    type TEXT,                  -- "checkpoint" 타입
    checkpoint JSONB,           -- State 데이터 (compressed)
    metadata JSONB,             -- 메타데이터
    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id)
);
```

**checkpoint_writes** 테이블:
```sql
CREATE TABLE checkpoint_writes (
    thread_id TEXT,
    checkpoint_ns TEXT,
    checkpoint_id UUID,
    task_id UUID,
    idx INTEGER,
    channel TEXT,              -- State key 이름
    type TEXT,                 -- "write" 타입
    value JSONB,               -- 변경된 값
    FOREIGN KEY (thread_id, checkpoint_ns, checkpoint_id)
        REFERENCES checkpoints
);
```

---

**Checkpointer 정리**:

**정리 시점**: 애플리케이션 종료 시 (일반적으로 자동 처리)

```python
# Context manager 종료
if self._checkpoint_cm:
    await self._checkpoint_cm.__aexit__(None, None, None)
```

**주의사항**:
- Checkpointer는 Connection Pool을 사용하므로 명시적 종료 필요
- FastAPI shutdown event에서 처리

---

**Checkpointer vs Chat History DB**:

| 특징 | Checkpointer (PostgreSQL) | Chat History DB (chat_messages) |
|-----|---------------------------|--------------------------------|
| **목적** | 워크플로우 State 전체 저장 | 사용자-챗봇 메시지만 저장 |
| **데이터** | planning_state, team_results, execution_steps 등 | query, response만 |
| **사용** | LangGraph 내부 (자동) | UI 표시용, 수동 저장 |
| **검색** | thread_id로 State History 조회 | session_id로 메시지 조회 |
| **보관 기간** | 중단-재개에 필요한 기간 | 영구 보관 (사용자 히스토리) |

---

**Checkpointer 비활성화**:

```python
supervisor = TeamBasedSupervisor(
    llm_context=llm_context,
    enable_checkpointing=False  # Checkpointing 비활성화
)
```

**비활성화 시**:
- Chat History 불가 (매 쿼리가 독립적)
- HITL (중단-재개) 불가
- State는 메모리에만 존재 (휘발성)

---

**디버깅 팁**:

PostgreSQL에서 직접 Checkpoint 조회:

```sql
-- 특정 thread_id의 모든 Checkpoint 조회
SELECT checkpoint_id, parent_checkpoint_id,
       checkpoint->'v'->'query' as query,
       checkpoint->'v'->'planning_state'->'analyzed_intent'->'intent_type' as intent
FROM checkpoints
WHERE thread_id = 'session-abc123'
ORDER BY checkpoint_id;

-- 최신 Checkpoint 조회
SELECT *
FROM checkpoints
WHERE thread_id = 'session-abc123'
ORDER BY checkpoint_id DESC
LIMIT 1;
```

---

## 9. 실제 예시 (전체 추적)

### 9.1 사용자 질문

```
"전세금 5% 인상 가능한가요?"
```

### 9.2 전체 처리 로그 (시간 순)

```
[10:30:00.000] 📥 WebSocket 메시지 수신
                type: "query"
                query: "전세금 5% 인상 가능한가요?"

[10:30:00.100] ✅ 세션 검증 완료
                session_id: "session-9b050480-..."

[10:30:00.150] 🚀 Supervisor 싱글톤 가져오기
                (이미 생성됨, 재사용)

[10:30:00.200] 📤 WebSocket 전송
                {"type": "connected", "session_id": "..."}

[10:30:00.250] 🔥 백그라운드 Task 생성
                _process_query_async() 시작

[10:30:00.300] 💾 사용자 메시지 DB 저장
                chat_messages 테이블 INSERT

[10:30:00.350] 🔥 LangGraph 워크플로우 시작
                app.ainvoke(initial_state, config)

[10:30:00.400] 📤 WebSocket 전송
                {"type": "supervisor_phase_change", "supervisorPhase": "dispatching"}

[10:30:00.450] ⚙️  initialize_node 실행
                State 초기화

[10:30:00.500] 📤 WebSocket 전송
                {"type": "supervisor_phase_change", "supervisorPhase": "analyzing"}

[10:30:00.550] ⚙️  planning_node 실행 시작

[10:30:00.600] 🔍 Chat History 조회
                최근 3개 대화 쌍 (6개 메시지)

[10:30:00.650] 📤 WebSocket 전송
                {"type": "analysis_start", "message": "질문을 분석하고 있습니다..."}

[10:30:00.700] 🤖 Intent 분석 시작
                planning_agent.analyze_intent()

[10:30:00.750] 📄 프롬프트 로드
                intent_analysis.txt

[10:30:00.800] 🔄 프롬프트 변수 치환
                query: "전세금 5% 인상 가능한가요?"
                chat_history: "사용자: 전세 계약이란?\nAI: ..."

[10:30:01.000] 🌐 OpenAI API 호출
                POST https://api.openai.com/v1/chat/completions
                model: "gpt-4o-mini"
                temperature: 0.0

[10:30:02.500] ✅ LLM 응답 수신
                {
                  "intent": "LEGAL_CONSULT",
                  "confidence": 0.95,
                  "keywords": ["전세금", "인상", "5%"],
                  "reasoning": "1단계: 정보 확인형..."
                }

[10:30:02.550] ✅ IntentType 파싱
                IntentType.LEGAL_CONSULT

[10:30:02.600] 🔍 Agent 선택 시작
                planning_agent.suggest_agents()

[10:30:02.650] 🔍 0차 하드코딩 키워드 필터
                intent_type: LEGAL_CONSULT
                analysis_keywords 체크: ❌ (없음)
                → 즉시 반환: ["search_team"]

[10:30:02.700] ✅ Agent 선택 완료
                suggested_agents: ["search_team"]

[10:30:02.750] 📝 실행 계획 생성
                execution_steps: [
                  {
                    "step_id": "step_1",
                    "team_name": "search",
                    "estimated_time": 15
                  }
                ]

[10:30:02.800] 📤 WebSocket 전송
                {"type": "plan_ready", "intent": "법률상담", ...}

[10:30:02.850] ⚙️  _route_after_planning 실행
                intent_type: "legal_consult"
                confidence: 0.95
                → 반환: "execute"

[10:30:02.900] 📤 WebSocket 전송
                {"type": "supervisor_phase_change", "supervisorPhase": "executing"}

[10:30:02.950] ⚙️  execute_teams_node 실행 시작

[10:30:03.000] 📤 WebSocket 전송
                {"type": "execution_start", "message": "작업 실행을 시작합니다..."}

[10:30:03.050] 🔍 SearchExecutor 실행 시작
                _execute_search_team()

[10:30:03.100] 📤 WebSocket 전송
                {"type": "step_start", "agent": "search_team"}

[10:30:03.150] ⚙️  SearchExecutor 서브그래프 실행
                prepare_search_node

[10:30:03.200] 📤 WebSocket 전송
                {"type": "step_progress", "agent": "search_team", "progress": 0}

[10:30:03.250] 🔍 키워드 추출
                legal: ["전세금", "인상"]

[10:30:03.300] 🔍 검색 범위 결정
                {"legal_search": true}

[10:30:03.350] 📤 WebSocket 전송
                {"type": "step_progress", "agent": "search_team", "progress": 30}

[10:30:03.400] ⚙️  execute_search_node 실행

[10:30:03.450] 🔍 HybridLegalSearch 호출
                hybrid_search(query="전세금 5% 인상 가능한가요?", limit=10)

[10:30:03.500] 🔍 쿼리 전처리
                enhanced_query: "전세금 인상\n전세금 5% 인상 가능한가요?"

[10:30:03.550] 🔍 쿼리 임베딩
                embedding_model.encode()

[10:30:03.800] 🔍 FAISS 벡터 검색
                search(embedding, k=30)

[10:30:04.000] 🔍 법률 계층 재정렬
                doc_type 가중치 적용

[10:30:04.100] 🔍 SQLite 메타데이터 보강
                get_article_by_number()

[10:30:04.500] ✅ 검색 완료
                2개 결과 반환

[10:30:04.550] 📤 WebSocket 전송
                {"type": "step_progress", "agent": "search_team", "progress": 80}

[10:30:04.600] ⚙️  aggregate_results_node (SearchExecutor)

[10:30:04.650] ⚙️  finalize_node (SearchExecutor)

[10:30:04.700] 📤 WebSocket 전송
                {"type": "step_complete", "agent": "search_team", "result": {...}}

[10:30:04.750] ✅ SearchExecutor 완료

[10:30:04.800] ⚙️  aggregate_results_node (Supervisor)

[10:30:04.850] 📝 팀별 결과 집계
                aggregated_results: {
                  "search_data": {
                    "legal": [...]
                  }
                }

[10:30:04.900] 📤 WebSocket 전송
                {"type": "supervisor_phase_change", "supervisorPhase": "finalizing"}

[10:30:04.950] ⚙️  generate_response_node 실행

[10:30:04.960] 📤 WebSocket 전송 (🆕 Step 1)
                {"type": "supervisor_phase_change", "supervisorProgress": 85, "message": "최종 답변을 생성하고 있습니다"}

[10:30:04.970] 📝 Intent 체크
                intent_type: "legal_consult", confidence: 0.95

[10:30:04.980] 📤 WebSocket 전송 (🆕 Step 2)
                {"type": "supervisor_phase_change", "supervisorProgress": 87, "message": "답변 내용을 작성하고 있습니다"}

[10:30:05.000] 📄 프롬프트 로드
                response_synthesis.txt

[10:30:05.050] 🔄 프롬프트 변수 치환
                query: "전세금 5% 인상 가능한가요?"
                aggregated_results: "{"search_data": {...}}"

[10:30:05.100] 🌐 OpenAI API 호출 (LLM 작업 시작)
                POST https://api.openai.com/v1/chat/completions
                model: "gpt-4o-mini"
                temperature: 0.3

                ⏱️  [6-9초 대기] - 85% → 86% → 87% → 88% (Frontend smooth animation)

[10:30:11.500] ✅ LLM 응답 수신
                {
                  "answer": "주택임대차보호법 제7조...",
                  "confidence": 0.95,
                  "sources": [...]
                }

[10:30:11.550] 📤 WebSocket 전송 (🆕 Step 3)
                {"type": "supervisor_phase_change", "supervisorProgress": 90, "message": "답변을 검증하고 있습니다"}

[10:30:11.600] 📤 WebSocket 전송 (🆕 Step 4)
                {"type": "supervisor_phase_change", "supervisorProgress": 95, "message": "답변 생성 완료"}

[10:30:11.650] 📝 최종 응답 구성
                final_response: {
                  "type": "answer",
                  "answer": "...",
                  "structured_data": {...}
                }

[10:30:11.700] 📤 WebSocket 전송 (🆕 Step 5)
                {"type": "supervisor_phase_change", "supervisorProgress": 92, "message": "대화를 저장하고 있습니다"}

[10:30:11.750] 💾 Long-term Memory 저장 시작
                memory_service.save_conversation()

                ⏱️  [3초 대기] - Background summarization

[10:30:14.750] ✅ Memory 저장 완료

[10:30:14.800] 📤 WebSocket 전송
                {"type": "final_response", "response": {...}}

[10:30:14.850] ✅ 워크플로우 완료
                final_state 반환

[10:30:14.900] 💾 AI 메시지 DB 저장
                chat_messages 테이블 INSERT

[10:30:14.950] 🎉 처리 완료
                총 소요 시간: 14.95초
```

### 9.3 State 변화 추적

**초기 State [10:30:00.350]**:
```python
{
    "query": "전세금 5% 인상 가능한가요?",
    "session_id": "session-9b050480-...",
    "current_phase": "",
    "planning_state": None,
    "execution_plan": None,
    "active_teams": [],
    "team_results": {},
    "aggregated_results": {},
    "final_response": None,
    "status": "initialized"
}
```

**initialize_node 후 [10:30:00.450]**:
```python
{
    "query": "전세금 5% 인상 가능한가요?",
    "session_id": "session-9b050480-...",
    "current_phase": "initialization",
    "planning_state": None,
    "execution_plan": None,
    "active_teams": [],
    "completed_teams": [],
    "failed_teams": [],
    "team_results": {},
    "error_log": [],
    "status": "initialized"
}
```

**planning_node 후 [10:30:02.800]**:
```python
{
    "query": "전세금 5% 인상 가능한가요?",
    "session_id": "session-9b050480-...",
    "current_phase": "planning",
    "planning_state": {
        "analyzed_intent": {
            "intent_type": "legal_consult",
            "confidence": 0.95,
            "keywords": ["전세금", "인상", "5%"],
            "reasoning": "1단계: 정보 확인형...",
            "suggested_agents": ["search_team"]
        },
        "execution_steps": [
            {
                "step_id": "step_1",
                "team_name": "search",
                "status": "pending",
                "estimated_time": 15
            }
        ]
    },
    "execution_plan": [...],
    "active_teams": ["search"],
    "team_results": {},
    "status": "initialized"
}
```

**execute_teams_node 후 [10:30:04.750]**:
```python
{
    "current_phase": "executing",
    "active_teams": ["search"],
    "completed_teams": ["search"],
    "team_results": {
        "search": {
            "results": {
                "legal": [
                    {
                        "law_title": "주택임대차보호법",
                        "article_number": "제7조",
                        "content": "...",
                        "relevance_score": 0.92
                    },
                    {
                        "law_title": "주택임대차보호법 시행령",
                        "article_number": "제2조",
                        "content": "...",
                        "relevance_score": 0.88
                    }
                ]
            },
            "status": "completed"
        }
    },
    "status": "initialized"
}
```

**aggregate_results_node 후 [10:30:04.850]**:
```python
{
    "current_phase": "aggregating",
    "aggregated_results": {
        "search_data": {
            "legal": [...]
        }
    },
    "status": "initialized"
}
```

**generate_response_node 후 [10:30:06.550]**:
```python
{
    "current_phase": "responding",
    "aggregated_results": {...},
    "final_response": {
        "type": "answer",
        "answer": "주택임대차보호법 제7조 및 동법 시행령 제2조에 따라, 전세금 증액은 청구 당시 전세금의 5% 이내로 제한됩니다. 따라서 5% 인상은 법적으로 가능합니다.",
        "structured_data": {
            "sections": [...]
        },
        "teams_used": ["search"],
        "data": {...}
    },
    "status": "completed",
    "end_time": "2025-01-27T10:30:06.550000"
}
```

---

## 10. 트러블슈팅

### 10.1 일반적인 문제

#### 문제 1: "IRRELEVANT로 잘못 분류됨"

**증상**:
```
사용자: "대항력이 뭐야?"
시스템: "부동산 관련 질문을 해주세요."
```

**원인**:
- `intent_analysis.txt` 프롬프트에 용어 설명 예시 부족
- LLM이 "일반상식"으로 오인

**해결**:
1. `IntentType` Enum에 `TERM_EXPLANATION` 추가
2. `intent_analysis.txt`에 용어 설명 카테고리 및 예시 추가
3. `agent_selection.txt`에 용어 검색 → search_team 매핑 추가

**자세한 내용**: `CHATBOT_FILTERING_ISSUE_ANALYSIS_251027.md` 참조

#### 문제 2: "Agent 선택이 부적절함"

**증상**:
```
사용자: "전세금 3억을 10억으로 올려달래. 어떻게 해야 해?"
Intent: LEGAL_CONSULT
Agent: ["search_team"]  ← 분석이 필요한데 search만 선택
```

**원인**:
- 0차 하드코딩 필터의 `analysis_keywords`에 누락
- LLM Agent 선택 실패

**해결**:
1. `analysis_keywords`에 키워드 추가 [planning_agent.py:326]
   ```python
   analysis_keywords = [
       "비교", "분석", "계산", "평가", "추천", "검토",
       "어떻게", "방법", "차이", "장단점", "괜찮아",
       "해야", "대응", "해결", "조치", "문제"
   ]
   ```

2. `agent_selection.txt` 프롬프트 개선
   - Few-shot 예시 추가
   - Chain-of-Thought 강화

#### 문제 3: "검색 결과가 없음"

**증상**:
```
사용자: "주택임대차보호법 제7조"
검색 결과: 0개
```

**원인**:
- FAISS 인덱스에 해당 조문이 없음
- SQLite DB와 FAISS 불일치

**해결**:
1. FAISS DB 재생성
2. `hybrid_legal_search.py`의 쿼리 전처리 개선
3. 법률 용어 키워드 확장 [라인 236]

#### 문제 4: "WebSocket 연결 끊김"

**증상**:
```
ERROR: WebSocket disconnected unexpectedly
```

**원인**:
- 세션 만료
- 네트워크 불안정
- 서버 오류

**해결**:
1. 세션 TTL 연장 (기본 60분)
2. WebSocket 재연결 로직 추가 (클라이언트)
3. 에러 로그 확인 (`error_log` State 필드)

### 10.2 디버깅 방법

#### 방법 1: 로그 추적

```python
# team_supervisor.py에서 로깅 활성화
import logging
logging.basicConfig(level=logging.DEBUG)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
```

**주요 로그**:
- `[TeamSupervisor] Planning phase`
- `[PlanningAgent] Analyzing intent for query: ...`
- `✅ Primary LLM selected agents: ...`
- `[SearchExecutor] Preparing search`

#### 방법 2: State 덤프

```python
# planning_node 끝에 추가
logger.debug(f"State dump: {json.dumps(state, indent=2, default=str)}")
```

#### 방법 3: WebSocket 메시지 모니터링

**브라우저 개발자 도구 → Network → WS**:
```
← {"type": "connected", "session_id": "..."}
→ {"type": "query", "query": "..."}
← {"type": "supervisor_phase_change", "supervisorPhase": "analyzing"}
← {"type": "plan_ready", "intent": "법률상담", ...}
← {"type": "final_response", "response": {...}}
```

---

## 11. 참고 자료

### 11.1 주요 파일 위치

| 파일 | 경로 | 설명 |
|------|------|------|
| **chat_api.py** | `backend/app/api/chat_api.py` | WebSocket Endpoint |
| **team_supervisor.py** | `backend/app/service_agent/supervisor/team_supervisor.py` | LangGraph 워크플로우 |
| **planning_agent.py** | `backend/app/service_agent/cognitive_agents/planning_agent.py` | 의도 분석 & Agent 선택 |
| **search_executor.py** | `backend/app/service_agent/execution_agents/search_executor.py` | 검색 실행 |
| **hybrid_legal_search.py** | `backend/app/service_agent/tools/hybrid_legal_search.py` | 벡터DB 검색 |
| **llm_service.py** | `backend/app/service_agent/llm_manager/llm_service.py` | LLM 호출 관리 |
| **prompt_manager.py** | `backend/app/service_agent/llm_manager/prompt_manager.py` | 프롬프트 관리 |
| **intent_analysis.txt** | `backend/app/service_agent/llm_manager/prompts/cognitive/intent_analysis.txt` | 의도 분석 프롬프트 |
| **agent_selection.txt** | `backend/app/service_agent/llm_manager/prompts/cognitive/agent_selection.txt` | Agent 선택 프롬프트 |
| **response_synthesis.txt** | `backend/app/service_agent/llm_manager/prompts/execution/response_synthesis.txt` | 답변 생성 프롬프트 |

### 11.2 관련 문서

- [필터링 문제 분석 보고서](../Implementation/CHATBOT_FILTERING_ISSUE_ANALYSIS_251027.md)
- [LangGraph 0.6 공식 문서](https://langchain-ai.github.io/langgraph/)
- [FastAPI WebSocket 문서](https://fastapi.tiangolo.com/advanced/websockets/)

---

## 12. 버전 히스토리

| 버전 | 날짜 | 변경 사항 |
|------|------|----------|
| 1.0 | 2025-01-27 | 초기 작성 |

---

**End of Manual**
