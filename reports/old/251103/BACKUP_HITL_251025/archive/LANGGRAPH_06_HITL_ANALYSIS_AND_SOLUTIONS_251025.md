# LangGraph 0.6 HITL 분석 및 해결방안

**작성일**: 2025-10-25
**작성자**: AI Assistant
**문서 버전**: 1.0
**대상**: Document Executor HITL 구현 개선

---

## 📋 Executive Summary

### 분석 목적
LangGraph 0.6 기반으로 구현된 Document Executor의 HITL(Human-in-the-Loop) 패턴을 분석하고, 현재 구현에서 발견된 문제점을 파악하여 해결 방안을 제시합니다.

### 주요 발견사항

| 항목 | 현재 상태 | 문제점 | 영향도 |
|------|----------|--------|--------|
| **Graph 구조** | 이중 그래프 (Supervisor + DocumentExecutor) | NodeInterrupt가 Supervisor로 전파 안 됨 | 🔴 Critical |
| **Checkpointer** | 각자 독립적인 checkpointer 보유 | Thread ID 불일치로 재개 불가능 | 🔴 Critical |
| **Interrupt 처리** | 딕셔너리로 반환 | 워크플로우가 실제로 중단되지 않음 | 🔴 Critical |
| **재개 로직** | 이중 재개 구조 | 복잡성 증가, 동기화 이슈 | 🟡 High |
| **API 통합** | 중간 레이어 함수 사용 | LangGraph Command API 미사용 | 🟡 High |

### 권장 해결 방안
**방안 A: 서브그래프 통합** (추천 ⭐⭐⭐⭐⭐)
- DocumentExecutor를 TeamSupervisor의 서브그래프로 통합
- 단일 checkpointer로 전체 워크플로우 관리
- LangGraph 0.6 정석 패턴 준수

---

## 🎯 LangGraph 0.6 HITL 핵심 개념

### 1. NodeInterrupt

**목적**: 워크플로우를 중단하고 사용자 입력을 대기합니다.

**사용법**:
```python
from langgraph.errors import NodeInterrupt

# 노드 내부에서 발생
async def collaborate_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
    # ... 작업 진행 ...

    # 사용자 입력이 필요한 시점
    raise NodeInterrupt({
        "type": "collaboration_required",
        "session_id": state.get("session_id"),
        "document_id": state.get("document_id"),
        "editable_fields": ["tenant_name", "landlord_name", "rent_amount"],
        "preview": state.get("document_preview"),
        "message": "Please edit the document fields."
    })
```

**특징**:
- Exception 기반이므로 **자동으로 호출 스택을 따라 전파됨**
- Checkpointer가 활성화된 경우 **현재 상태를 자동 저장**
- `config`의 `thread_id`로 세션을 식별

---

### 2. AsyncPostgresSaver (Checkpointer)

**목적**: 워크플로우 상태를 PostgreSQL에 저장하여 재개를 가능하게 합니다.

**초기화**:
```python
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

# 연결 문자열로 생성
conn_string = "postgresql://user:password@localhost:5432/dbname"
context_manager = AsyncPostgresSaver.from_conn_string(conn_string)

# Async context manager 진입
checkpointer = await context_manager.__aenter__()

# 테이블 생성 (checkpoints, checkpoint_blobs, checkpoint_writes)
await checkpointer.setup()
```

**그래프 컴파일**:
```python
from langgraph.graph import StateGraph

workflow = StateGraph(StateType)
workflow.add_node("node1", node1_func)
workflow.add_node("node2", node2_func)
# ... edges ...

# Checkpointer와 함께 컴파일
app = workflow.compile(checkpointer=checkpointer)
```

**특징**:
- `thread_id`로 세션 구분 (config에 전달)
- NodeInterrupt 발생 시 **자동으로 상태 저장**
- 재개 시 **마지막 체크포인트부터 실행**

---

### 3. Command API (aupdate + astream)

**목적**: 중단된 워크플로우의 상태를 업데이트하고 재개합니다.

#### **3.1. aupdate() - 상태 업데이트**

```python
# NodeInterrupt 발생 후 사용자가 데이터 제공
user_input = {
    "tenant_name": "홍길동",
    "landlord_name": "김철수",
    "rent_amount": 50000000
}

# Config (thread_id 필수)
config = {
    "configurable": {
        "thread_id": "session-abc123"
    }
}

# 상태 업데이트 (그래프는 아직 실행되지 않음)
await app.aupdate(user_input, config)
```

**동작**:
- 마지막 체크포인트의 상태에 `user_input`을 **병합**
- 그래프는 실행되지 않고 **상태만 업데이트**

#### **3.2. astream(None, config) - 워크플로우 재개**

```python
# 워크플로우 재개 (None을 전달 - 새로운 초기 상태 없음)
async for event in app.astream(None, config):
    print(f"Event: {event}")

    # event 구조:
    # {
    #     "node_name": {
    #         "state_field1": value1,
    #         "state_field2": value2,
    #         ...
    #     }
    # }
```

**동작**:
- `thread_id`로 마지막 체크포인트를 로드
- **중단된 노드의 다음 노드부터 실행 재개**
- 또 다른 NodeInterrupt 발생 가능 (반복 가능)

---

### 4. 정석 HITL 패턴 예제

```python
from langgraph.graph import StateGraph, START, END
from langgraph.errors import NodeInterrupt
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

# 1. State 정의
class DocumentState(TypedDict):
    session_id: str
    document_id: str
    content: str
    user_approved: bool

# 2. 노드 정의
async def generate_draft(state: DocumentState) -> DocumentState:
    state["content"] = "초안 내용..."
    return state

async def wait_for_user(state: DocumentState) -> DocumentState:
    # 사용자 입력 대기
    raise NodeInterrupt({
        "type": "approval_required",
        "content": state["content"]
    })

async def finalize(state: DocumentState) -> DocumentState:
    state["status"] = "completed"
    return state

# 3. 그래프 구성
workflow = StateGraph(DocumentState)
workflow.add_node("generate", generate_draft)
workflow.add_node("approve", wait_for_user)
workflow.add_node("finalize", finalize)

workflow.add_edge(START, "generate")
workflow.add_edge("generate", "approve")
workflow.add_edge("approve", "finalize")
workflow.add_edge("finalize", END)

# 4. Checkpointer와 함께 컴파일
checkpointer = await AsyncPostgresSaver.from_conn_string(conn_string).__aenter__()
await checkpointer.setup()
app = workflow.compile(checkpointer=checkpointer)

# 5. 실행
config = {"configurable": {"thread_id": "session-123"}}

# 첫 실행 (NodeInterrupt 발생)
try:
    result = await app.ainvoke({"session_id": "session-123"}, config)
except NodeInterrupt as e:
    print(f"Interrupted: {e.args[0]}")
    # {"type": "approval_required", "content": "초안 내용..."}

# 6. 사용자 입력 후 재개
await app.aupdate({"user_approved": True}, config)
result = await app.ainvoke(None, config)  # 재개
print(result["status"])  # "completed"
```

---

## 📊 현재 구현 상태 분석

### 구현 현황 테이블

| 구성 요소 | 파일 위치 | 구현 상태 | 코드 라인 | 비고 |
|----------|----------|----------|----------|------|
| **NodeInterrupt 발생** | `document_executor.py` | ✅ 정상 구현 | L428, L554 | collaborate_node, user_confirm_node |
| **AsyncPostgresSaver** | `checkpointer.py` | ✅ 정상 구현 | L46-96 | create_checkpointer() |
| **graph.aupdate()** | `document_executor.py` | ✅ 구현됨 | L911 | handle_update() 내부 |
| **graph.astream()** | `document_executor.py` | ✅ 구현됨 | L946 | resume_workflow() 내부 |
| **Supervisor 통합** | `team_supervisor.py` | ❌ 미구현 | L996-1005 | execute() 직접 호출 |
| **API WebSocket** | `chat_api.py` | ⚠️ 부분 구현 | L717-807 | 중간 레이어 사용 |

### 아키텍처 다이어그램 (현재)

```
┌─────────────────────────────────────────────────────────────────┐
│                    TeamBasedSupervisor                          │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  MainSupervisorState                                     │   │
│  │                                                          │   │
│  │  initialize → planning → execute_teams                  │   │
│  │                              ↓                           │   │
│  │                      _execute_single_team()             │   │
│  │                              ↓                           │   │
│  │                    team.execute(state) ←─────────────────┼───┼─── 일반 함수 호출
│  │                              ↓                           │   │
│  │                 {"status": "interrupted"}  ⚠️ 딕셔너리    │   │
│  │                              ↓                           │   │
│  │                aggregate → generate_response             │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  Checkpointer: AsyncPostgresSaver (thread_id: chat_session_id)  │
└──────────────────────────────────────────────────────────────────┘
                                   ║
                                   ║ ⚠️ 분리된 그래프
                                   ║
┌──────────────────────────────────────────────────────────────────┐
│                    DocumentExecutor                              │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  DocumentState                                           │   │
│  │                                                          │   │
│  │  initialize → collect_context → generate_draft          │   │
│  │       ↓                                                  │   │
│  │  collaborate (raise NodeInterrupt) ← ⚠️ 전파 안 됨        │   │
│  │       ↓                                                  │   │
│  │  user_confirm → ai_review → finalize                    │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  Checkpointer: AsyncPostgresSaver (thread_id: session_id) ⚠️    │
└──────────────────────────────────────────────────────────────────┘
                                   ↓
                        catch NodeInterrupt
                                   ↓
                    return {"status": "interrupted"}
                                   ↓
┌──────────────────────────────────────────────────────────────────┐
│                    FastAPI (chat_api.py)                         │
│                                                                  │
│  WebSocket Handler:                                              │
│  - field_update → supervisor.handle_document_update()  ⚠️        │
│  - request_confirmation → supervisor.resume_document_workflow()  │
│                                                                  │
│  ⚠️ LangGraph Command API 직접 사용 안 함                         │
└──────────────────────────────────────────────────────────────────┘
```

**문제점 시각화**:
- 🔴 **이중 그래프**: Supervisor와 DocumentExecutor가 각자의 그래프 보유
- 🔴 **Thread ID 불일치**: `chat_session_id` vs `session_id`
- 🔴 **Interrupt 미전파**: NodeInterrupt가 딕셔너리로 변환되어 반환
- 🟡 **중간 레이어**: API가 Command API를 직접 사용하지 않음

---

## 🔍 문제점 상세 분석

### 문제점 1: Graph 구조 불일치

#### **문제 설명**
DocumentExecutor가 독립적인 서브그래프를 가지고 있지만, TeamSupervisor의 메인 그래프와 **통합되지 않음**.

#### **코드 위치**
- **DocumentExecutor 그래프 생성**: [document_executor.py:191](document_executor.py#L191)
  ```python
  workflow = StateGraph(Dict)  # DocumentExecutor의 독립 그래프
  self.app = workflow.compile(checkpointer=self.checkpointer)
  ```

- **Supervisor의 팀 실행**: [team_supervisor.py:996-1005](team_supervisor.py#L996-1005)
  ```python
  elif team_name == "document":
      # ... 상태 준비 ...

      # ⚠️ DocumentExecutor를 일반 async 함수처럼 호출
      result = await team.execute(state)
  ```

#### **문제의 영향**
1. **NodeInterrupt가 Supervisor로 전파 안 됨**
   - DocumentExecutor 내부에서 `raise NodeInterrupt`
   - DocumentExecutor의 `execute()`가 이를 catch하여 딕셔너리로 변환
   - Supervisor는 딕셔너리를 일반 결과값으로 처리

2. **Checkpointer 분리**
   - Supervisor: `chat_session_id`를 thread_id로 사용
   - DocumentExecutor: `session_id`를 thread_id로 사용
   - 두 그래프의 checkpoint가 **별도로 저장됨**

#### **재현 시나리오**
```
1. 사용자 쿼리: "임대차계약서 작성해줘"
2. Supervisor → Planning → execute_teams
3. execute_teams → _execute_single_team("document")
4. DocumentExecutor.execute() 호출
5. DocumentExecutor 내부: collaborate_node → raise NodeInterrupt
6. DocumentExecutor.execute() 내부에서 catch:
   except NodeInterrupt as e:
       return {"status": "interrupted", "interrupt": e.args[0]}
7. Supervisor: result = {"status": "interrupted", ...}
8. Supervisor는 다음 노드(aggregate)로 진행 ⚠️ (중단되지 않음)
9. 최종 응답 생성 (문서가 완성되지 않았는데 응답 전송)
```

---

### 문제점 2: Config 전달 누락

#### **문제 설명**
DocumentExecutor의 `execute()` 메서드가 config 파라미터를 받지 않아서 **Supervisor의 thread_id와 연결 불가능**.

#### **코드 위치**
- **Supervisor의 thread_id 설정**: [team_supervisor.py:1546-1552](team_supervisor.py#L1546-L1552)
  ```python
  # ✅ Supervisor는 chat_session_id를 thread_id로 사용
  thread_id = chat_session_id if chat_session_id else session_id

  config = {
      "configurable": {
          "thread_id": thread_id
      }
  }
  final_state = await self.app.ainvoke(initial_state, config=config)
  ```

- **DocumentExecutor의 thread_id 설정**: [document_executor.py:826-830](document_executor.py#L826-L830)
  ```python
  # ⚠️ state에서 session_id 추출 (chat_session_id와 다를 수 있음)
  config = {
      "configurable": {
          "thread_id": state.get("session_id")
      }
  }
  ```

- **Supervisor의 팀 실행**: [team_supervisor.py:1016](team_supervisor.py#L1016)
  ```python
  # ⚠️ config를 전달하지 않음
  result = await team.execute(state)
  ```

#### **문제의 영향**
1. **Checkpoint 불일치**
   - Supervisor: `thread_id = "chat-session-abc123"`
   - DocumentExecutor: `thread_id = "session-xyz789"` (HTTP WebSocket session)
   - PostgreSQL의 `checkpoints` 테이블에 **별도의 레코드로 저장**

2. **재개 불가능**
   - API에서 `chat_session_id`로 재개 시도
   - DocumentExecutor는 다른 `session_id`의 checkpoint 찾음
   - 상태 복원 실패

#### **재현 시나리오**
```
1. WebSocket 연결: session_id = "ws-12345"
2. 채팅 세션 생성: chat_session_id = "chat-abc123"
3. Supervisor 실행:
   - config = {"configurable": {"thread_id": "chat-abc123"}}
   - Checkpoint 저장: thread_id = "chat-abc123"
4. DocumentExecutor 실행:
   - state.get("session_id") = "ws-12345"
   - config = {"configurable": {"thread_id": "ws-12345"}}
   - Checkpoint 저장: thread_id = "ws-12345"
5. NodeInterrupt 발생
6. API 재개 시도:
   - config = {"configurable": {"thread_id": "chat-abc123"}}
   - DocumentExecutor는 "ws-12345" checkpoint만 가지고 있음
   - 재개 실패 ❌
```

---

### 문제점 3: Interrupt 전파 메커니즘 부재

#### **문제 설명**
DocumentExecutor의 NodeInterrupt를 catch하여 딕셔너리로 변환하므로, **Supervisor의 워크플로우가 실제로 중단되지 않음**.

#### **코드 위치**
- **NodeInterrupt 발생**: [document_executor.py:428-435](document_executor.py#L428-L435)
  ```python
  async def collaborate_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
      # ... 협업 준비 ...

      # NodeInterrupt 발생 - 사용자 입력 대기
      raise NodeInterrupt({
          "type": "collaboration_required",
          "session_id": session_id,
          "document_id": state.get("document_id"),
          "editable_fields": list(state.get("document_fields", {}).keys()),
          "preview": state.get("document_preview", ""),
          "message": "Document collaboration mode activated."
      })
  ```

- **Interrupt 처리**: [document_executor.py:843-860](document_executor.py#L843-L860)
  ```python
  async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
      try:
          # 워크플로우 실행
          result = None
          async for event in self.app.astream(state, config=config):
              result = event

          return result if result else state

      except NodeInterrupt as interrupt:
          # ⚠️ NodeInterrupt를 catch하여 딕셔너리로 변환
          logger.info(f"🛑 NodeInterrupt caught: {interrupt}")

          return {
              "status": "interrupted",
              "interrupt": interrupt.args[0] if interrupt.args else {},
              "session_id": state["session_id"]
          }
  ```

- **Supervisor의 결과 처리**: [team_supervisor.py:1015-1050](team_supervisor.py#L1015-L1050)
  ```python
  try:
      result = await team.execute(state)

      # ⚠️ interrupt를 딕셔너리로 받음 (Exception이 아님)
      if isinstance(result, dict) and result.get("status") == "interrupted":
          interrupt_data = result.get("interrupt", {})

          # WebSocket으로 알림 전송
          if progress_callback:
              await progress_callback("collaboration_started", {...})

          # ⚠️ 딕셔너리를 반환 - Supervisor 워크플로우는 계속 진행됨
          return {
              "status": "paused",
              "team": team_name,
              "interrupt": interrupt_data,
              "message": f"Document workflow paused"
          }
  ```

#### **문제의 영향**
1. **워크플로우가 중단되지 않음**
   - Supervisor의 `execute_teams_node`는 정상적으로 완료
   - 다음 노드(`aggregate_results_node`)로 진행
   - 최종적으로 `generate_response_node`까지 실행
   - **사용자 입력을 받지 않고 응답 생성**

2. **Checkpoint 미활용**
   - NodeInterrupt가 Exception이 아니므로 Supervisor의 checkpointer가 **자동 저장 안 함**
   - 재개 시 Supervisor의 상태를 복원할 수 없음

#### **올바른 패턴**
```python
# Supervisor의 팀 실행
async def _execute_single_team(self, team_name, shared_state, main_state):
    if team_name == "document":
        # ✅ NodeInterrupt를 그대로 전파
        result = await team.execute(state)
        # NodeInterrupt 발생 시 자동으로 호출 스택 전파
        return result
```

---

### 문제점 4: 재개 로직의 분리

#### **문제 설명**
Supervisor와 DocumentExecutor가 각자의 재개 함수를 가져서 **이중 재개 구조** 발생.

#### **코드 위치**
- **Supervisor 재개**: [team_supervisor.py:1631-1670](team_supervisor.py#L1631-L1670)
  ```python
  async def resume_document_workflow(self, session_id: str) -> Dict:
      """Document workflow 재개"""
      try:
          document_team = self.teams.get("document")
          if not document_team:
              return {"error": "Document team not found"}

          # ⚠️ DocumentExecutor의 resume_workflow 호출
          if hasattr(document_team, 'resume_workflow'):
              result = await document_team.resume_workflow(session_id)

              # 재개 결과 처리
              if result.get("status") == "interrupted":
                  # ... progress callback ...

              return result
  ```

- **DocumentExecutor 재개**: [document_executor.py:928-981](document_executor.py#L928-L981)
  ```python
  async def resume_workflow(self, session_id: str) -> Dict:
      """NodeInterrupt 후 워크플로우 재개"""
      try:
          if session_id not in self.active_sessions:
              return {"error": "Session not found"}

          session = self.active_sessions[session_id]
          config = session.get("config", {"configurable": {"thread_id": session_id}})

          # ⚠️ DocumentExecutor의 app.astream 호출
          if self.app:
              result = None
              async for event in self.app.astream(None, config):
                  result = event

              return result if result else {"status": "resumed"}
  ```

- **API 재개**: [chat_api.py:759-773](chat_api.py#L759-L773)
  ```python
  elif message_type == "request_confirmation":
      supervisor = await get_supervisor()
      if supervisor:
          # 상태 업데이트
          update_data = {
              "request_approval": True,
              "collaboration_active": False
          }

          await supervisor.handle_document_update(session_id, update_data)

          # ⚠️ Supervisor의 resume 함수 호출
          result = await supervisor.resume_document_workflow(session_id)
  ```

#### **문제의 영향**
1. **복잡한 호출 체인**
   ```
   API → Supervisor.resume_document_workflow()
       → DocumentExecutor.resume_workflow()
           → DocumentExecutor.app.astream()
   ```

2. **동기화 이슈**
   - Supervisor의 메인 워크플로우는 이미 종료됨
   - DocumentExecutor만 재개됨
   - Supervisor의 `aggregate` → `generate_response` 노드는 **실행되지 않음**

3. **상태 불일치**
   - DocumentExecutor의 상태만 업데이트됨
   - Supervisor의 `MainSupervisorState`는 **업데이트되지 않음**

#### **올바른 패턴**
```python
# API에서 직접 Supervisor의 그래프 재개
async def handle_websocket_message(message_type, data):
    if message_type == "field_update":
        # 상태 업데이트
        await supervisor.app.aupdate(data, config)

        # 워크플로우 재개
        async for event in supervisor.app.astream(None, config):
            await send_progress(event)
```

---

### 문제점 5: API 통합의 불완전성

#### **문제 설명**
chat_api.py의 WebSocket 핸들러가 Supervisor를 건너뛰고 **DocumentExecutor의 특정 메서드를 직접 호출**.

#### **코드 위치**
- **field_update 처리**: [chat_api.py:717-745](chat_api.py#L717-L745)
  ```python
  elif message_type == "field_update":
      supervisor = await get_supervisor()
      if supervisor:
          # ⚠️ 중간 레이어 함수 사용
          update_data = {
              "pending_edits": [{
                  "field": data.get("field"),
                  "value": data.get("value"),
                  "editor_id": session_id,
                  "timestamp": datetime.now().isoformat()
              }]
          }

          # ⚠️ handle_document_update 호출 (LangGraph Command API 아님)
          success = await supervisor.handle_document_update(session_id, update_data)
  ```

- **handle_document_update**: [team_supervisor.py:1609-1629](team_supervisor.py#L1609-L1629)
  ```python
  async def handle_document_update(self, session_id: str, update_data: Dict) -> bool:
      """Document workflow의 상태 업데이트 처리"""
      try:
          document_team = self.teams.get("document")
          if not document_team:
              return False

          # ⚠️ DocumentExecutor의 handle_update 호출
          if hasattr(document_team, 'handle_update'):
              return await document_team.handle_update(session_id, update_data)
  ```

- **DocumentExecutor.handle_update**: [document_executor.py:897-926](document_executor.py#L897-L926)
  ```python
  async def handle_update(self, session_id: str, update_data: Dict) -> bool:
      """LangGraph 0.6 상태 업데이트 처리"""
      try:
          if session_id not in self.active_sessions:
              return False

          session = self.active_sessions[session_id]
          config = session.get("config", {"configurable": {"thread_id": session_id}})

          # ✅ graph.aupdate()는 사용함
          if self.app and self.checkpointer:
              await self.app.aupdate(update_data, config)
              return True
  ```

#### **문제의 영향**
1. **Supervisor의 checkpointer와 동기화 안 됨**
   - DocumentExecutor의 checkpointer만 업데이트됨
   - Supervisor의 `MainSupervisorState`는 **업데이트되지 않음**

2. **LangGraph 패턴 위반**
   - 정석 패턴: `app.aupdate(data, config)` 직접 호출
   - 현재: `supervisor.handle_document_update() → document_team.handle_update() → app.aupdate()`

3. **추가 레이어로 인한 복잡성**
   - 디버깅 어려움
   - 오류 추적 복잡

#### **올바른 패턴**
```python
# API에서 직접 Supervisor의 app.aupdate 호출
elif message_type == "field_update":
    supervisor = await get_supervisor()

    # Config 생성
    config = {
        "configurable": {
            "thread_id": chat_session_id  # Supervisor와 동일한 thread_id
        }
    }

    # 상태 업데이트 (LangGraph Command API 직접 사용)
    update_data = {
        "document_team_state": {
            "pending_edits": [{
                "field": data.get("field"),
                "value": data.get("value")
            }]
        }
    }

    await supervisor.app.aupdate(update_data, config)
```

---

## ✅ 올바른 LangGraph 0.6 패턴

### 정석 아키텍처 다이어그램

```
┌─────────────────────────────────────────────────────────────────┐
│                TeamBasedSupervisor (메인 그래프)                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  MainSupervisorState                                     │   │
│  │                                                          │   │
│  │  initialize → planning → execute_teams                  │   │
│  │                              ↓                           │   │
│  │                      ┌──────────────┐                    │   │
│  │                      │ document 노드 │ ← 서브그래프        │   │
│  │                      │  (서브그래프)  │                   │   │
│  │                      │               │                   │   │
│  │                      │  collaborate  │                   │   │
│  │                      │  (NodeInterrupt)                  │   │
│  │                      │      ↓        │                   │   │
│  │                      │ user_confirm  │                   │   │
│  │                      │  (NodeInterrupt)                  │   │
│  │                      └──────────────┘                    │   │
│  │                              ↓                           │   │
│  │                aggregate → generate_response             │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ✅ 단일 Checkpointer (AsyncPostgresSaver)                       │
│  ✅ 단일 thread_id: chat_session_id                             │
└──────────────────────────────────────────────────────────────────┘
           ↓ NodeInterrupt 자동 전파          ↑ aupdate + astream
           ↓                                  ↑
┌──────────────────────────────────────────────────────────────────┐
│                    FastAPI (chat_api.py)                         │
│                                                                  │
│  WebSocket Handler:                                              │
│  ✅ field_update:                                                │
│     await supervisor.app.aupdate(data, config)                   │
│                                                                  │
│  ✅ 워크플로우 재개:                                              │
│     async for event in supervisor.app.astream(None, config):     │
│         await send_to_websocket(event)                           │
│                                                                  │
│  ✅ LangGraph Command API 직접 사용                               │
└──────────────────────────────────────────────────────────────────┘
```

### 권장 구조 설명

#### **1. 서브그래프 통합**
```python
# team_supervisor.py

class TeamBasedSupervisor:
    def __init__(self, llm_context=None, enable_checkpointing=True):
        # DocumentExecutor를 checkpointer 없이 생성
        self.document_executor = DocumentExecutor(
            llm_context=llm_context,
            enable_checkpointing=False  # ✅ Supervisor의 checkpointer 사용
        )

        # 워크플로우 구성
        self._build_graph()

    def _build_graph(self):
        workflow = StateGraph(MainSupervisorState)

        # 일반 노드
        workflow.add_node("initialize", self.initialize_node)
        workflow.add_node("planning", self.planning_node)

        # ✅ DocumentExecutor를 서브그래프로 추가
        workflow.add_node("document_team", self.document_executor.app)

        workflow.add_node("aggregate", self.aggregate_results_node)
        workflow.add_node("generate_response", self.generate_response_node)

        # 엣지 구성
        workflow.add_edge(START, "initialize")
        workflow.add_edge("initialize", "planning")

        # Conditional routing
        workflow.add_conditional_edges(
            "planning",
            self._route_after_planning,
            {
                "document": "document_team",  # ✅ 서브그래프로 라우팅
                "other": "execute_teams"
            }
        )

        workflow.add_edge("document_team", "aggregate")
        workflow.add_edge("aggregate", "generate_response")
        workflow.add_edge("generate_response", END)

        # ✅ 단일 checkpointer로 컴파일
        self.app = workflow.compile(checkpointer=self.checkpointer)
```

#### **2. State 변환**
```python
# MainSupervisorState와 DocumentState 간 변환

class StateAdapter:
    @staticmethod
    def to_document_state(main_state: MainSupervisorState) -> DocumentState:
        """MainSupervisorState → DocumentState"""
        return {
            "session_id": main_state["session_id"],
            "chat_session_id": main_state["chat_session_id"],
            "document_type": main_state.get("document_type"),
            "chat_context": {
                "user_query": main_state.get("query"),
                "history": []
            }
        }

    @staticmethod
    def from_document_state(doc_state: DocumentState, main_state: MainSupervisorState) -> MainSupervisorState:
        """DocumentState → MainSupervisorState (병합)"""
        main_state["team_results"]["document"] = {
            "document_id": doc_state.get("document_id"),
            "document_path": doc_state.get("document_path"),
            "status": doc_state.get("status")
        }
        return main_state
```

#### **3. API 통합 (단순화)**
```python
# chat_api.py

@router.websocket("/ws/{session_id}")
async def websocket_chat(websocket: WebSocket, session_id: str):
    supervisor = await get_supervisor()

    # Config 생성 (단일 thread_id)
    config = {
        "configurable": {
            "thread_id": session_id  # chat_session_id 사용
        }
    }

    while True:
        data = await websocket.receive_json()
        message_type = data.get("type")

        if message_type == "query":
            # 초기 실행
            try:
                async for event in supervisor.app.astream(
                    {"query": data.get("query"), "session_id": session_id},
                    config
                ):
                    await websocket.send_json(event)

            except Exception as e:
                # NodeInterrupt는 자동으로 checkpoint 저장됨
                await websocket.send_json({
                    "type": "interrupted",
                    "message": "사용자 입력 대기 중"
                })

        elif message_type == "field_update":
            # ✅ 상태 업데이트 (LangGraph Command API 직접 사용)
            await supervisor.app.aupdate({
                "document_fields": {
                    data.get("field"): data.get("value")
                }
            }, config)

            await websocket.send_json({"type": "update_success"})

        elif message_type == "resume":
            # ✅ 워크플로우 재개
            async for event in supervisor.app.astream(None, config):
                await websocket.send_json(event)
```

---

## 🔧 해결 방안 상세

### 방안 A: 서브그래프 통합 (추천 ⭐⭐⭐⭐⭐)

#### **개요**
DocumentExecutor의 그래프를 TeamSupervisor의 서브그래프로 통합하여 단일 checkpointer로 전체 워크플로우를 관리합니다.

#### **장점**
- ✅ **LangGraph 0.6 정석 패턴** 준수
- ✅ **단일 checkpointer**로 상태 관리 단순화
- ✅ **NodeInterrupt 자동 전파** (Exception 기반)
- ✅ **재개 로직 단순화** (supervisor.app.astream만 사용)
- ✅ **확장성**: 다른 팀(Analysis, Search)도 동일 패턴 적용 가능

#### **단점**
- ⚠️ State 변환 로직 필요 (MainSupervisorState ↔ DocumentState)
- ⚠️ 중간 수준의 코드 변경 (3개 파일)

#### **난이도**: 중간
**코드 변경량**: 중간 (3개 파일)
**LangGraph 정석도**: ⭐⭐⭐⭐⭐

---

#### **구현 단계**

##### **Step 1: DocumentExecutor 수정**

**파일**: `document_executor.py`

**변경 사항**:
1. `__init__`에서 checkpointer 생성 제거
2. `_build_workflow`에서 checkpointer 파라미터 받기
3. `execute` 메서드를 일반 노드 함수로 변경

**코드**:
```python
# document_executor.py

class DocumentExecutor:
    def __init__(
        self,
        llm_context=None,
        enable_checkpointing: bool = False,  # ✅ 기본값 False
        enable_ai_suggestions: bool = True
    ):
        self.llm_context = llm_context
        self.enable_ai_suggestions = enable_ai_suggestions

        # ✅ checkpointer는 Supervisor에서 받음
        self.checkpointer = None
        self.app = None
        self.workflow_built = False

        # Tools 초기화
        self.tools = self._initialize_tools()

        logger.info("DocumentExecutor initialized (will be integrated as subgraph)")

    async def build_workflow(self, checkpointer=None):
        """
        워크플로우 구성 (Supervisor에서 호출)

        Args:
            checkpointer: Supervisor의 checkpointer (optional)
        """
        workflow = StateGraph(Dict)

        # 노드 추가
        workflow.add_node("initialize", self.initialize_node)
        workflow.add_node("collect_context", self.collect_context_node)
        workflow.add_node("generate_draft", self.generate_draft_node)
        workflow.add_node("collaborate", self.collaborate_node)
        workflow.add_node("user_confirm", self.user_confirm_node)
        workflow.add_node("ai_review", self.ai_review_node)
        workflow.add_node("finalize", self.finalize_node)
        workflow.add_node("error_handler", self.error_handler_node)

        # 엣지 구성 (기존과 동일)
        workflow.add_edge(START, "initialize")
        workflow.add_edge("initialize", "collect_context")
        # ... (나머지 엣지)

        # ✅ Checkpointer 없이 컴파일 (Supervisor가 제공)
        if checkpointer:
            self.checkpointer = checkpointer
            self.app = workflow.compile(checkpointer=checkpointer)
            logger.info("✅ DocumentExecutor workflow compiled with Supervisor's checkpointer")
        else:
            self.app = workflow.compile()
            logger.info("✅ DocumentExecutor workflow compiled without checkpointer")

        self.workflow_built = True
        return self.app

    # ❌ execute() 메서드 제거 - Supervisor가 app을 직접 사용
```

---

##### **Step 2: TeamSupervisor 수정**

**파일**: `team_supervisor.py`

**변경 사항**:
1. DocumentExecutor를 서브그래프로 추가
2. State 변환 로직 추가
3. `_execute_single_team` 제거 (서브그래프로 대체)

**코드**:
```python
# team_supervisor.py

class TeamBasedSupervisor:
    def __init__(self, llm_context: LLMContext = None, enable_checkpointing: bool = True):
        self.llm_context = llm_context or create_default_llm_context()
        self.enable_checkpointing = enable_checkpointing

        # Agent 시스템 초기화
        initialize_agent_system(auto_register=True)

        # Checkpointer
        self.checkpointer = None
        self._checkpointer_initialized = False
        self._checkpoint_cm = None

        # Progress Callbacks
        self._progress_callbacks: Dict[str, Callable] = {}

        # Planning Agent
        self.planning_agent = PlanningAgent(llm_context=llm_context)

        # ✅ DocumentExecutor 생성 (checkpointer 없이)
        self.document_executor = DocumentExecutor(
            llm_context=llm_context,
            enable_checkpointing=False,  # Supervisor의 checkpointer 사용
            enable_ai_suggestions=True
        )

        # 다른 팀 (기존 방식)
        self.teams = {
            "search": SearchExecutor(llm_context=llm_context),
            "analysis": AnalysisExecutor(llm_context=llm_context)
        }

        # 워크플로우는 나중에 빌드 (checkpointer 초기화 후)
        self.app = None

        logger.info("TeamBasedSupervisor initialized")

    async def _ensure_checkpointer(self):
        """Checkpointer 초기화 및 graph 빌드"""
        if not self.enable_checkpointing:
            # Checkpointer 없이 빌드
            await self._build_graph_with_document_subgraph(checkpointer=None)
            return

        if not self._checkpointer_initialized:
            try:
                from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
                from app.core.config import settings

                DB_URI = settings.postgres_url

                # AsyncPostgresSaver 초기화
                self._checkpoint_cm = AsyncPostgresSaver.from_conn_string(DB_URI)
                self.checkpointer = await self._checkpoint_cm.__aenter__()
                await self.checkpointer.setup()

                self._checkpointer_initialized = True

                # ✅ Checkpointer와 함께 graph 빌드
                await self._build_graph_with_document_subgraph(checkpointer=self.checkpointer)

                logger.info("✅ PostgreSQL checkpointer initialized and graph built")
            except Exception as e:
                logger.error(f"Failed to initialize checkpointer: {e}")
                self.enable_checkpointing = False
                await self._build_graph_with_document_subgraph(checkpointer=None)

    async def _build_graph_with_document_subgraph(self, checkpointer=None):
        """
        DocumentExecutor를 서브그래프로 통합한 워크플로우 구성

        Args:
            checkpointer: AsyncPostgresSaver 인스턴스 (optional)
        """
        # ✅ DocumentExecutor의 워크플로우 빌드 (Supervisor의 checkpointer 전달)
        await self.document_executor.build_workflow(checkpointer=checkpointer)

        # MainSupervisor 워크플로우
        workflow = StateGraph(MainSupervisorState)

        # 일반 노드
        workflow.add_node("initialize", self.initialize_node)
        workflow.add_node("planning", self.planning_node)
        workflow.add_node("execute_teams", self.execute_teams_node)

        # ✅ DocumentExecutor를 서브그래프로 추가
        workflow.add_node("document_subgraph", self._document_subgraph_wrapper)

        workflow.add_node("aggregate", self.aggregate_results_node)
        workflow.add_node("generate_response", self.generate_response_node)

        # 엣지 구성
        workflow.add_edge(START, "initialize")
        workflow.add_edge("initialize", "planning")

        # Conditional routing
        workflow.add_conditional_edges(
            "planning",
            self._route_after_planning,
            {
                "execute": "execute_teams",
                "respond": "generate_response"
            }
        )

        # execute_teams 후 라우팅
        workflow.add_conditional_edges(
            "execute_teams",
            self._route_after_execute_teams,
            {
                "document": "document_subgraph",  # ✅ Document 팀 → 서브그래프
                "aggregate": "aggregate"
            }
        )

        workflow.add_edge("document_subgraph", "aggregate")
        workflow.add_edge("aggregate", "generate_response")
        workflow.add_edge("generate_response", END)

        # ✅ Checkpointer와 함께 컴파일
        if checkpointer:
            self.app = workflow.compile(checkpointer=checkpointer)
            logger.info("✅ Supervisor workflow compiled with checkpointer (Document subgraph integrated)")
        else:
            self.app = workflow.compile()
            logger.info("✅ Supervisor workflow compiled without checkpointer")

    def _route_after_execute_teams(self, state: MainSupervisorState) -> str:
        """execute_teams 후 라우팅"""
        active_teams = state.get("active_teams", [])

        if "document" in active_teams:
            return "document"
        else:
            return "aggregate"

    async def _document_subgraph_wrapper(self, state: MainSupervisorState) -> MainSupervisorState:
        """
        DocumentExecutor 서브그래프 Wrapper
        MainSupervisorState ↔ DocumentState 변환
        """
        logger.info("[Supervisor] Entering document subgraph")

        # ✅ State 변환: MainSupervisorState → DocumentState
        doc_state = {
            "session_id": state.get("session_id"),
            "chat_session_id": state.get("chat_session_id"),
            "document_type": self._extract_document_type(state),
            "chat_context": {
                "user_query": state.get("query", ""),
                "history": []
            }
        }

        # ✅ DocumentExecutor의 app 실행 (서브그래프)
        # NodeInterrupt 발생 시 자동으로 Supervisor로 전파됨
        result_state = await self.document_executor.app.ainvoke(doc_state)

        # ✅ State 변환: DocumentState → MainSupervisorState (병합)
        state["team_results"]["document"] = {
            "document_id": result_state.get("document_id"),
            "document_path": result_state.get("document_path"),
            "document_preview": result_state.get("document_preview"),
            "status": result_state.get("status"),
            "version": result_state.get("version")
        }

        logger.info("[Supervisor] Document subgraph completed")
        return state
```

---

##### **Step 3: API 통합 간소화**

**파일**: `chat_api.py`

**변경 사항**:
1. 중간 레이어 함수 제거 (`handle_document_update`, `resume_document_workflow`)
2. LangGraph Command API 직접 사용
3. WebSocket 메시지 핸들러 단순화

**코드**:
```python
# chat_api.py

@router.websocket("/ws/{session_id}")
async def websocket_chat(
    websocket: WebSocket,
    session_id: str,
    session_mgr: SessionManager = Depends(get_session_manager),
    conn_mgr: ConnectionManager = Depends(get_connection_manager)
):
    """실시간 채팅 WebSocket 엔드포인트"""

    # 세션 검증
    validation_result = await session_mgr.validate_session(session_id)
    if not validation_result:
        await websocket.close(code=4004, reason="Session not found")
        return

    # WebSocket 연결
    await conn_mgr.connect(session_id, websocket)
    await conn_mgr.send_message(session_id, {
        "type": "connected",
        "session_id": session_id,
        "timestamp": datetime.now().isoformat()
    })

    # Supervisor 인스턴스
    supervisor = await get_supervisor(enable_checkpointing=True)

    # ✅ Config 생성 (단일 thread_id)
    config = {
        "configurable": {
            "thread_id": session_id  # chat_session_id 사용
        }
    }

    try:
        while True:
            data = await websocket.receive_json()
            message_type = data.get("type")

            logger.info(f"📥 Received: {message_type}")

            # === Query 처리 ===
            if message_type == "query":
                query = data.get("query")

                if not query:
                    await conn_mgr.send_message(session_id, {
                        "type": "error",
                        "error": "Query cannot be empty"
                    })
                    continue

                # 초기 State
                initial_state = {
                    "query": query,
                    "session_id": session_id,
                    "chat_session_id": session_id,
                    "user_id": 1  # TODO: 실제 user_id
                }

                # ✅ Supervisor 워크플로우 실행
                try:
                    async for event in supervisor.app.astream(initial_state, config):
                        # Progress 이벤트 전송
                        await conn_mgr.send_message(session_id, {
                            "type": "progress",
                            "event": event,
                            "timestamp": datetime.now().isoformat()
                        })

                except Exception as e:
                    # NodeInterrupt는 여기서 catch되지 않음 (자동 checkpoint 저장)
                    logger.error(f"Workflow error: {e}")
                    await conn_mgr.send_message(session_id, {
                        "type": "error",
                        "error": str(e)
                    })

            # === Document Field Update ===
            elif message_type == "field_update":
                # ✅ LangGraph Command API 직접 사용
                field = data.get("field")
                value = data.get("value")

                update_data = {
                    "document_team_state": {
                        "document_fields": {
                            field: value
                        }
                    }
                }

                try:
                    # ✅ graph.aupdate() 직접 호출
                    await supervisor.app.aupdate(update_data, config)

                    await conn_mgr.send_message(session_id, {
                        "type": "field_update_success",
                        "field": field,
                        "timestamp": datetime.now().isoformat()
                    })

                except Exception as e:
                    logger.error(f"Update failed: {e}")
                    await conn_mgr.send_message(session_id, {
                        "type": "field_update_failed",
                        "field": field,
                        "error": str(e)
                    })

            # === Document Approval Request ===
            elif message_type == "request_confirmation":
                # ✅ 상태 업데이트 후 재개
                update_data = {
                    "document_team_state": {
                        "request_approval": True,
                        "collaboration_active": False
                    }
                }

                try:
                    # 1. 상태 업데이트
                    await supervisor.app.aupdate(update_data, config)

                    # 2. 워크플로우 재개
                    async for event in supervisor.app.astream(None, config):
                        await conn_mgr.send_message(session_id, {
                            "type": "progress",
                            "event": event,
                            "timestamp": datetime.now().isoformat()
                        })

                except Exception as e:
                    logger.error(f"Resume failed: {e}")
                    await conn_mgr.send_message(session_id, {
                        "type": "error",
                        "error": str(e)
                    })

            # === Document Approval ===
            elif message_type == "document_approval":
                decision = data.get("decision")  # "approve", "reject", "revision"
                feedback = data.get("feedback", "")

                update_data = {
                    "document_team_state": {
                        "approval_status": decision,
                        "approval_feedback": feedback,
                        "approver_id": session_id
                    }
                }

                try:
                    # 1. 승인 상태 업데이트
                    await supervisor.app.aupdate(update_data, config)

                    # 2. 워크플로우 재개 (finalize 또는 재편집)
                    async for event in supervisor.app.astream(None, config):
                        await conn_mgr.send_message(session_id, {
                            "type": "progress",
                            "event": event,
                            "timestamp": datetime.now().isoformat()
                        })

                except Exception as e:
                    logger.error(f"Approval processing failed: {e}")
                    await conn_mgr.send_message(session_id, {
                        "type": "error",
                        "error": str(e)
                    })

            # === 기타 메시지 ===
            else:
                await conn_mgr.send_message(session_id, {
                    "type": "error",
                    "error": f"Unknown message type: {message_type}"
                })

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {session_id}")

    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)

    finally:
        conn_mgr.disconnect(session_id)
        logger.info(f"WebSocket closed: {session_id}")
```

---

#### **변경 파일 요약**

| 파일 | 변경 내용 | 난이도 |
|------|----------|--------|
| **document_executor.py** | - `__init__`: checkpointer 생성 제거<br>- `build_workflow`: checkpointer 파라미터 받기<br>- `execute`: 제거 (서브그래프로 대체) | 중간 |
| **team_supervisor.py** | - `_build_graph_with_document_subgraph`: 새로 추가<br>- `_document_subgraph_wrapper`: State 변환<br>- `_route_after_execute_teams`: 라우팅 로직<br>- `handle_document_update`, `resume_document_workflow`: 제거 | 중간 |
| **chat_api.py** | - WebSocket 핸들러 간소화<br>- LangGraph Command API 직접 사용<br>- `field_update`, `request_confirmation`, `document_approval` 핸들러 수정 | 낮음 |

---

### 방안 B: Interrupt 전파 메커니즘

#### **개요**
현재 구조를 유지하면서 Supervisor에서 NodeInterrupt를 다시 raise하여 전파합니다.

#### **장점**
- ✅ 기존 코드 최소 수정
- ✅ 독립적인 서브그래프 유지
- ✅ 빠른 구현 가능

#### **단점**
- ⚠️ Thread ID 불일치 문제 여전히 존재
- ⚠️ 이중 checkpointer 유지
- ⚠️ LangGraph 정석 패턴은 아님

#### **난이도**: 낮음
**코드 변경량**: 낮음 (2개 파일)
**LangGraph 정석도**: ⭐⭐⭐

---

#### **구현 단계**

##### **Step 1: Supervisor에서 NodeInterrupt 재발생**

**파일**: `team_supervisor.py`

**변경 위치**: `_execute_single_team` ([L1015-1050](team_supervisor.py#L1015-L1050))

**코드**:
```python
# team_supervisor.py

async def _execute_single_team(
    self,
    team_name: str,
    shared_state: SharedState,
    main_state: MainSupervisorState
) -> Any:
    """단일 팀 실행"""
    team = self.teams[team_name]

    if team_name == "document":
        # 문서 타입 추출
        doc_type = self._extract_document_type(main_state)

        # DocumentExecutor 상태 준비
        state = {
            **shared_state,
            "document_type": doc_type,
            "chat_context": {
                "user_query": main_state.get("query", ""),
                "history": []
            }
        }

        # Progress callback 등록
        session_id = main_state.get("session_id")
        if session_id and hasattr(team, 'set_progress_callback'):
            progress_callback = self._progress_callbacks.get(session_id)
            if progress_callback:
                team.set_progress_callback(session_id, progress_callback)

        # DocumentExecutor 실행
        try:
            result = await team.execute(state)

            # ✅ NodeInterrupt 확인 후 재발생
            if isinstance(result, dict) and result.get("status") == "interrupted":
                interrupt_data = result.get("interrupt", {})
                interrupt_type = interrupt_data.get("type")

                logger.info(f"🛑 Document team interrupted: {interrupt_type}")

                # WebSocket 알림은 여기서 전송
                if progress_callback:
                    if interrupt_type == "collaboration_required":
                        await progress_callback("collaboration_started", {
                            "session_id": session_id,
                            "document_id": interrupt_data.get("document_id"),
                            "editable_fields": interrupt_data.get("editable_fields", []),
                            "preview": interrupt_data.get("preview", ""),
                            "message": interrupt_data.get("message", "")
                        })
                    elif interrupt_type == "approval_required":
                        await progress_callback("approval_required", {
                            "session_id": session_id,
                            "document_id": interrupt_data.get("document_id"),
                            "preview": interrupt_data.get("preview", ""),
                            "message": interrupt_data.get("message", "")
                        })

                # ✅ NodeInterrupt를 Supervisor 레벨에서 다시 raise
                raise NodeInterrupt(interrupt_data)

            return result

        except NodeInterrupt:
            # ✅ 그대로 전파 (Supervisor의 app.ainvoke가 catch)
            raise

        except Exception as e:
            logger.error(f"Document team execution error: {e}")
            return {"status": "failed", "error": str(e)}

    # 다른 팀 처리 (기존과 동일)
    # ...
```

##### **Step 2: Supervisor의 process_query_streaming에서 catch**

**파일**: `team_supervisor.py`

**변경 위치**: `process_query_streaming` ([L1542-1557](team_supervisor.py#L1542-L1557))

**코드**:
```python
# team_supervisor.py

async def process_query_streaming(
    self,
    query: str,
    session_id: str = "default",
    chat_session_id: Optional[str] = None,
    user_id: Optional[int] = None,
    progress_callback: Optional[Callable[[str, dict], Awaitable[None]]] = None
) -> Dict[str, Any]:
    """실시간 스트리밍 쿼리 처리"""

    logger.info(f"[TeamSupervisor] Processing query: {query[:100]}...")

    # Checkpointer 초기화
    await self._ensure_checkpointer()

    # Progress Callback 등록
    if progress_callback:
        self._progress_callbacks[session_id] = progress_callback

    # 초기 상태
    initial_state = MainSupervisorState(
        query=query,
        session_id=session_id,
        chat_session_id=chat_session_id,
        user_id=user_id,
        # ... (기존 필드들)
    )

    # Config
    thread_id = chat_session_id if chat_session_id else session_id
    config = {
        "configurable": {
            "thread_id": thread_id
        }
    }

    try:
        if self.checkpointer:
            logger.info(f"Running with checkpointer (thread_id: {thread_id})")
            final_state = await self.app.ainvoke(initial_state, config=config)
        else:
            final_state = await self.app.ainvoke(initial_state)

        # Callback 정리
        if session_id in self._progress_callbacks:
            del self._progress_callbacks[session_id]

        return final_state

    # ✅ NodeInterrupt 처리
    except NodeInterrupt as interrupt:
        logger.info(f"🛑 Supervisor caught NodeInterrupt: {interrupt.args[0] if interrupt.args else {}}")

        # Callback 정리하지 않음 (재개 시 필요)

        # Interrupt 정보 반환
        interrupt_data = interrupt.args[0] if interrupt.args else {}
        return {
            "status": "interrupted",
            "interrupt": interrupt_data,
            "session_id": session_id,
            "chat_session_id": chat_session_id
        }

    except Exception as e:
        logger.error(f"Query processing failed: {e}", exc_info=True)

        # 에러 콜백
        callback = self._progress_callbacks.get(session_id)
        if callback:
            try:
                await callback("error", {
                    "error": str(e),
                    "message": "처리 중 오류가 발생했습니다."
                })
            except:
                pass

        # Callback 정리
        if session_id in self._progress_callbacks:
            del self._progress_callbacks[session_id]

        return {
            "status": "error",
            "error": str(e),
            "final_response": {
                "type": "error",
                "message": "처리 중 오류가 발생했습니다.",
                "error": str(e)
            }
        }
```

---

#### **변경 파일 요약**

| 파일 | 변경 내용 | 난이도 |
|------|----------|--------|
| **team_supervisor.py** | - `_execute_single_team`: NodeInterrupt 재발생<br>- `process_query_streaming`: NodeInterrupt catch 추가 | 낮음 |

---

### 방안 C: 하이브리드 접근

#### **개요**
Document 워크플로우를 Supervisor와 완전히 분리하여 독립 실행합니다.

#### **장점**
- ✅ Document 생성은 긴 작업이므로 독립 관리가 합리적
- ✅ Supervisor는 트리거만 수행

#### **단점**
- ⚠️ API 재설계 필요 (별도 엔드포인트)
- ⚠️ Supervisor와 DocumentExecutor 간 데이터 동기화 복잡
- ⚠️ 높은 구현 난이도

#### **난이도**: 높음
**코드 변경량**: 높음 (API 재설계)
**LangGraph 정석도**: ⭐⭐

---

#### **구현 단계**

##### **Step 1: Document 전용 WebSocket 엔드포인트**

**파일**: `chat_api.py`

**코드**:
```python
# chat_api.py

@router.websocket("/ws/document/{session_id}")
async def websocket_document(
    websocket: WebSocket,
    session_id: str
):
    """Document 생성 전용 WebSocket"""

    # DocumentExecutor 직접 생성
    from app.service_agent.foundation.context import create_default_llm_context

    llm_context = create_default_llm_context()
    doc_executor = DocumentExecutor(
        llm_context=llm_context,
        enable_checkpointing=True,
        enable_ai_suggestions=True
    )

    await doc_executor._build_workflow()

    # WebSocket 연결
    await websocket.accept()

    # Config
    config = {
        "configurable": {
            "thread_id": session_id
        }
    }

    try:
        while True:
            data = await websocket.receive_json()
            message_type = data.get("type")

            if message_type == "start_document":
                # Document 생성 시작
                initial_state = {
                    "session_id": session_id,
                    "document_type": data.get("document_type"),
                    "chat_context": data.get("chat_context")
                }

                try:
                    async for event in doc_executor.app.astream(initial_state, config):
                        await websocket.send_json({"type": "progress", "event": event})

                except Exception as e:
                    await websocket.send_json({"type": "interrupted"})

            elif message_type == "field_update":
                # 상태 업데이트
                await doc_executor.app.aupdate({
                    "document_fields": {
                        data.get("field"): data.get("value")
                    }
                }, config)

                await websocket.send_json({"type": "update_success"})

            elif message_type == "resume":
                # 워크플로우 재개
                async for event in doc_executor.app.astream(None, config):
                    await websocket.send_json({"type": "progress", "event": event})

    except WebSocketDisconnect:
        logger.info(f"Document WebSocket disconnected: {session_id}")

    finally:
        await websocket.close()
```

##### **Step 2: Supervisor는 Document 작업 위임**

**파일**: `team_supervisor.py`

**코드**:
```python
# team_supervisor.py

async def _execute_single_team(
    self,
    team_name: str,
    shared_state: SharedState,
    main_state: MainSupervisorState
) -> Any:
    """단일 팀 실행"""

    if team_name == "document":
        # Document 작업은 위임 (별도 WebSocket으로 처리)
        document_session_id = f"doc-{uuid.uuid4()}"

        logger.info(f"Document task delegated to session: {document_session_id}")

        return {
            "status": "delegated",
            "document_session_id": document_session_id,
            "message": "Document generation started in separate session"
        }

    # 다른 팀 처리
    # ...
```

---

#### **변경 파일 요약**

| 파일 | 변경 내용 | 난이도 |
|------|----------|--------|
| **chat_api.py** | - `/ws/document/{session_id}` 엔드포인트 추가<br>- DocumentExecutor 직접 관리 | 중간 |
| **team_supervisor.py** | - `_execute_single_team`: Document 작업 위임 | 낮음 |
| **Frontend** | - Document 요청 시 별도 WebSocket 연결<br>- 두 WebSocket 동시 관리 | 높음 |

---

## 🎯 구현 우선순위 및 로드맵

### Phase 1: 긴급 수정 (Quick Fixes)

**목표**: NodeInterrupt가 최소한 작동하도록 수정

**작업**:
1. **Thread ID 통일** (1일)
   - DocumentExecutor가 `chat_session_id`를 thread_id로 사용하도록 수정
   - [document_executor.py:828](document_executor.py#L828) 수정

2. **NodeInterrupt 전파** (1일)
   - Supervisor에서 NodeInterrupt 재발생
   - [team_supervisor.py:1015-1050](team_supervisor.py#L1015-L1050) 수정

**기대 효과**:
- ✅ HITL이 작동 (Interrupt 발생 시 워크플로우 중단)
- ✅ 재개 가능 (같은 thread_id 사용)

**구현**: **방안 B (Interrupt 전파)**

---

### Phase 2: 구조 개선 (Recommended) - 추천 ⭐

**목표**: LangGraph 0.6 정석 패턴 적용

**작업**:
1. **서브그래프 통합** (3일)
   - DocumentExecutor를 Supervisor의 서브그래프로 통합
   - State 변환 로직 추가
   - [document_executor.py](document_executor.py), [team_supervisor.py](team_supervisor.py) 수정

2. **API 간소화** (2일)
   - LangGraph Command API 직접 사용
   - 중간 레이어 제거
   - [chat_api.py](chat_api.py) 수정

3. **테스트 및 검증** (2일)
   - 전체 플로우 테스트
   - Interrupt → Update → Resume 시나리오 검증

**기대 효과**:
- ✅ 단일 checkpointer로 전체 상태 관리
- ✅ 유지보수성 향상
- ✅ 다른 팀에도 HITL 적용 용이

**구현**: **방안 A (서브그래프 통합)**

---

### Phase 3: 고도화 (Optional)

**목표**: 고급 HITL 패턴 적용

**작업**:
1. **Multi-step HITL**
   - 여러 단계에서 사용자 입력 대기
   - 조건부 Interrupt

2. **Timeout 처리**
   - 사용자 응답 시간 제한
   - 자동 복구 로직

3. **Rollback 기능**
   - 사용자가 이전 단계로 되돌리기
   - Checkpoint 히스토리 관리

**기대 효과**:
- ✅ 더 유연한 HITL 워크플로우
- ✅ 사용자 경험 향상

---

## 📚 참고자료 및 코드 레퍼런스

### 관련 파일 목록

| 파일 | 경로 | 역할 |
|------|------|------|
| **DocumentExecutor** | `backend/app/service_agent/execution_agents/document_executor.py` | Document 생성 워크플로우 |
| **TeamSupervisor** | `backend/app/service_agent/supervisor/team_supervisor.py` | 메인 Supervisor |
| **Checkpointer** | `backend/app/service_agent/foundation/checkpointer.py` | AsyncPostgresSaver 관리 |
| **Chat API** | `backend/app/api/chat_api.py` | FastAPI WebSocket 엔드포인트 |
| **States** | `backend/app/service_agent/foundation/separated_states.py` | State 정의 |

### LangGraph 공식 문서

1. **Human-in-the-Loop**
   - [LangGraph HITL Guide](https://langchain-ai.github.io/langgraph/how-tos/human-in-the-loop/)

2. **Persistence (Checkpointer)**
   - [LangGraph Persistence](https://langchain-ai.github.io/langgraph/concepts/persistence/)

3. **Command API**
   - [aupdate()](https://langchain-ai.github.io/langgraph/reference/graphs/#langgraph.graph.graph.CompiledGraph.aupdate)
   - [astream()](https://langchain-ai.github.io/langgraph/reference/graphs/#langgraph.graph.graph.CompiledGraph.astream)

4. **Subgraphs**
   - [LangGraph Subgraphs](https://langchain-ai.github.io/langgraph/how-tos/subgraph/)

### 이전 HITL 관련 문서

1. `HITL_Final_Solution_Report.md`
2. `HITL_Debug_Implementation_Plan.md`
3. `HITL_Complete_System_Review.md`
4. `HITL_Final_Implementation_Plan_v3.md`

---

## 🔍 디버깅 체크리스트

HITL 구현 시 확인해야 할 항목들:

### 1. Checkpointer 설정
- [ ] AsyncPostgresSaver가 정상 초기화되었는가?
- [ ] `setup()` 메서드가 호출되었는가? (테이블 생성)
- [ ] Context manager가 정상적으로 entered 되었는가?

### 2. Thread ID
- [ ] Supervisor와 DocumentExecutor가 **같은 thread_id**를 사용하는가?
- [ ] `chat_session_id`를 thread_id로 사용하는가? (HTTP `session_id`가 아닌)
- [ ] Config의 `configurable.thread_id`가 올바르게 설정되었는가?

### 3. NodeInterrupt
- [ ] `raise NodeInterrupt({...})`가 호출되는가?
- [ ] Interrupt가 딕셔너리로 변환되지 않고 **Exception으로 전파**되는가?
- [ ] Supervisor 레벨에서 catch되는가?

### 4. State 관리
- [ ] MainSupervisorState와 DocumentState 간 변환이 올바른가?
- [ ] Interrupt 발생 시 현재 상태가 **checkpoint에 저장**되는가?
- [ ] 재개 시 마지막 checkpoint에서 **정확히 복원**되는가?

### 5. API 통합
- [ ] WebSocket에서 `graph.aupdate()`를 직접 호출하는가?
- [ ] 재개 시 `graph.astream(None, config)`를 사용하는가?
- [ ] Progress 이벤트가 올바르게 전송되는가?

### 6. 로그 확인
```python
# 확인해야 할 로그 메시지들
logger.info("🛑 Raising NodeInterrupt for collaboration")
logger.info("🛑 NodeInterrupt caught: ...")
logger.info("✅ State updated for session ...")
logger.info("📢 Resuming workflow for session ...")
logger.info("✅ Workflow completed for session ...")
```

---

## 📝 결론 및 권장사항

### 최종 권장 방안

**단기 (1주일)**: **방안 B (Interrupt 전파)**
- NodeInterrupt가 작동하도록 긴급 수정
- Thread ID 통일
- 최소한의 코드 변경

**중장기 (2-3주)**: **방안 A (서브그래프 통합)**
- LangGraph 0.6 정석 패턴 적용
- 단일 checkpointer로 전체 상태 관리
- 확장성 및 유지보수성 향상

### 구현 순서

```
Week 1: 방안 B 구현 (긴급 수정)
  Day 1-2: Thread ID 통일 + NodeInterrupt 전파
  Day 3-4: 테스트 및 디버깅
  Day 5: 배포 및 모니터링

Week 2-3: 방안 A 구현 (구조 개선)
  Day 1-3: DocumentExecutor 서브그래프화
  Day 4-6: TeamSupervisor 그래프 통합
  Day 7-9: API 간소화 (LangGraph Command API 직접 사용)
  Day 10-12: 전체 테스트 및 검증
  Day 13-14: 문서화 및 배포
```

### 성공 기준

1. **기능 테스트**
   - [ ] Document 생성 요청 시 collaborate 노드에서 Interrupt 발생
   - [ ] WebSocket으로 `collaboration_started` 이벤트 수신
   - [ ] 사용자가 필드 수정 시 상태 업데이트
   - [ ] 워크플로우 재개 시 다음 노드(user_confirm)로 진행
   - [ ] Approval 후 최종 문서 생성 완료

2. **성능 테스트**
   - [ ] Interrupt → Update → Resume 사이클이 1초 이내
   - [ ] Checkpoint 저장/복원이 500ms 이내
   - [ ] 동시 세션 100개 처리 가능

3. **안정성 테스트**
   - [ ] 서버 재시작 후 세션 복원 가능
   - [ ] 네트워크 단절 후 재연결 시 상태 유지
   - [ ] 에러 발생 시 graceful degradation

---

**문서 끝**

---

## 부록: 코드 스니펫 모음

### A. NodeInterrupt 발생
```python
from langgraph.errors import NodeInterrupt

async def my_node(state):
    # ... 작업 진행 ...

    # 사용자 입력 필요
    raise NodeInterrupt({
        "type": "user_input_required",
        "prompt": "Please provide input",
        "options": ["A", "B", "C"]
    })
```

### B. Checkpointer 초기화
```python
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

# Async context manager 사용
cm = AsyncPostgresSaver.from_conn_string("postgresql://...")
checkpointer = await cm.__aenter__()
await checkpointer.setup()

# 그래프 컴파일
app = workflow.compile(checkpointer=checkpointer)
```

### C. 상태 업데이트 및 재개
```python
# Config
config = {"configurable": {"thread_id": "session-123"}}

# 1. 초기 실행 (Interrupt 발생)
try:
    result = await app.ainvoke(initial_state, config)
except NodeInterrupt as e:
    print(f"Interrupted: {e.args[0]}")

# 2. 사용자 입력 후 상태 업데이트
await app.aupdate({"user_input": "value"}, config)

# 3. 워크플로우 재개
result = await app.ainvoke(None, config)
```

### D. 서브그래프 통합
```python
# 서브그래프 생성
sub_workflow = StateGraph(SubState)
sub_workflow.add_node("node1", node1_func)
sub_app = sub_workflow.compile()

# 메인 그래프에 통합
main_workflow = StateGraph(MainState)
main_workflow.add_node("subgraph", sub_app)
main_workflow.add_edge(START, "subgraph")

# 단일 checkpointer로 컴파일
main_app = main_workflow.compile(checkpointer=checkpointer)
```

---

**작성 완료일**: 2025-10-25
**문서 버전**: 1.0
**다음 업데이트 예정**: 구현 완료 후 실제 결과 반영
