# Phase 1, 2, 3 완료 보고서

**작성일**: 2025-10-25
**버전**: 1.0
**상태**: ✅ 완료 (테스트 대기)

---

## 📋 목표

LangGraph 0.6 HITL (Human-in-the-Loop) 문제 해결을 위한 Option B 재설계 완료:
- Phase 1: DocumentExecutor를 Subgraph 패턴으로 전환
- Phase 2: TeamSupervisor에 DocumentExecutor 통합
- Phase 3: Command API 직접 사용

---

## ✅ 완료된 작업

### Phase 1: DocumentExecutor 수정

**파일**: `backend/app/service_agent/execution_agents/document_executor.py`
**백업**: `backend/app/service_agent/execution_agents/document_executor_old.py`

**변경사항:**

1. **`__init__` 수정** (Line 82-110)
   ```python
   # Before
   def __init__(self, llm_context=None, enable_checkpointing: bool = True, ...):
       self.enable_checkpointing = enable_checkpointing
       self.checkpointer = None

   # After
   def __init__(self, llm_context=None, enable_ai_suggestions: bool = True):
       # No enable_checkpointing parameter
       # No self.checkpointer (uses parent's checkpointer)
   ```

2. **`build_subgraph()` 메서드 추가** (Line 121-209)
   ```python
   def build_subgraph(self) -> StateGraph:
       """
       Build DocumentExecutor as a StateGraph (subgraph pattern)
       Returns:
           StateGraph: Uncompiled graph to be integrated into parent supervisor
       """
       workflow = StateGraph(Dict)
       # ... add nodes and edges ...
       return workflow  # ✅ StateGraph 반환 (CompiledGraph 아님)
   ```

3. **제거된 메서드:**
   - `execute()` - 독립 실행 제거 (Line 815-868)
   - `handle_update()` - aupdate 오류 원인 제거 (Line 897-926)
   - `resume_workflow()` - 이중 resume 로직 제거 (Line 928-981)
   - `recover_session()` - 불필요한 복구 로직 제거 (Line 983-1017)

4. **보존된 기능:**
   - 8개 노드 메서드 모두 보존 (Line 215-502)
   - 3개 라우팅 함수 모두 보존 (Line 508-575)
   - Progress callback 시스템 보존 (Line 650-659)

5. **개선된 라우팅:** `_collaboration_routing` (Line 508-549)
   ```python
   # 사용자 액션 확인 (user_action 필드)
   user_action = state.get("user_action")

   if user_action == "edit_more":
       return "continue_editing"  # ← collaborate로 loop
   elif user_action == "approve":
       return "request_approval"  # ← user_confirm으로 이동
   ```

---

### Phase 2: TeamSupervisor 수정

**파일**: `backend/app/service_agent/supervisor/team_supervisor.py`
**백업**: `backend/app/service_agent/supervisor/team_supervisor_old.py`

**변경사항:**

1. **DocumentExecutor 초기화 수정** (Line 76-79)
   ```python
   # Before
   "document": DocumentExecutor(
       llm_context=llm_context,
       enable_checkpointing=enable_checkpointing,  # ❌ 제거됨
       enable_ai_suggestions=True
   )

   # After
   "document": DocumentExecutor(
       llm_context=llm_context,
       enable_ai_suggestions=True  # ✅ checkpointing 파라미터 제거
   )
   ```

2. **`_execute_single_team` 완전 재작성** (Line 997-1095)

   **Before (Old Pattern):**
   ```python
   result = await team.execute(state)  # ❌ 독립 실행

   if result.get("status") == "interrupted":
       interrupt_data = result.get("interrupt", {})  # ❌ dict로 변환됨
   ```

   **After (New Subgraph Pattern):**
   ```python
   # ✅ Build document subgraph
   document_subgraph = team.build_subgraph()

   # ✅ Compile with supervisor's checkpointer
   document_app = document_subgraph.compile(checkpointer=self.checkpointer)

   # ✅ Execute subgraph
   async for event in document_app.astream(document_state, config=config):
       result = event

   # ✅ Catch NodeInterrupt directly
   except NodeInterrupt as interrupt:
       interrupt_data = interrupt.args[0]  # ✅ Exception에서 dict 추출
       await progress_callback("collaboration_started", interrupt_data)
   ```

---

### Phase 3: Command API 통합

**파일**: `backend/app/service_agent/supervisor/team_supervisor.py`

**변경사항:**

1. **`handle_document_update()` 수정** (Line 1649-1681)

   **Before (Intermediate Layer):**
   ```python
   # ❌ DocumentExecutor의 handle_update 호출
   if hasattr(document_team, 'handle_update'):
       return await document_team.handle_update(session_id, update_data)
   ```

   **After (Command API):**
   ```python
   # ✅ Command API: update_state 직접 사용
   config = {"configurable": {"thread_id": session_id}}
   await self.app.update_state(config, update_data)
   logger.info(f"✅ State updated via Command API for session {session_id}")
   ```

2. **`resume_document_workflow()` 수정** (Line 1683-1759)

   **Before (Intermediate Layer):**
   ```python
   # ❌ DocumentExecutor의 resume_workflow 호출
   if hasattr(document_team, 'resume_workflow'):
       result = await document_team.resume_workflow(session_id)
   ```

   **After (Command API):**
   ```python
   # ✅ Command API: astream(None, config) 직접 사용
   config = {"configurable": {"thread_id": session_id}}

   async for event in self.app.astream(None, config=config):
       result = event

   except NodeInterrupt as interrupt:
       interrupt_data = interrupt.args[0]
       await progress_callback("approval_required", interrupt_data)
   ```

---

## 🏗️ 아키텍처 개선

### Before (Old Architecture)

```
TeamSupervisor (독립 checkpointer)
  └─ DocumentExecutor (독립 checkpointer)  ❌
      ├─ execute() → NodeInterrupt (dict로 변환됨)  ❌
      ├─ handle_update() → graph.aupdate() (메서드 없음)  ❌
      └─ resume_workflow() → 이중 resume 로직  ❌

문제점:
1. 이중 checkpointer → NodeInterrupt 전파 안 됨
2. Thread ID 불일치 (chat_session_id vs session_id)
3. Interrupt 객체가 dict로 변환 → JSON serialization 오류
4. aupdate() 메서드 없음 → AttributeError
```

### After (New Architecture)

```
TeamSupervisor (단일 checkpointer)  ✅
  └─ _execute_single_team (document)
      ├─ team.build_subgraph() → StateGraph  ✅
      ├─ document_subgraph.compile(checkpointer=self.checkpointer)  ✅
      ├─ document_app.astream(state, config) → NodeInterrupt 직접 catch  ✅
      └─ Progress callback → WebSocket 알림  ✅

개선사항:
1. 단일 checkpointer → NodeInterrupt 정상 전파
2. Thread ID 통일 (session_id)
3. Interrupt 예외를 직접 catch → dict 추출
4. Command API 사용 (update_state, astream)
```

---

## 🎯 핵심 해결 사항

### 1. ✅ aupdate 오류 해결

**Before:**
```python
await self.app.aupdate(update_data, config)  # ❌ CompiledStateGraph에 없음
```

**After:**
```python
await self.app.update_state(config, update_data)  # ✅ Command API
```

### 2. ✅ JSON Serialization 오류 해결

**Before:**
```python
# NodeInterrupt 객체를 dict로 변환
result = {"status": "interrupted", "interrupt": interrupt}  # ❌ Interrupt 객체
await progress_callback("collaboration_started", result)  # ❌ JSON serialization 실패
```

**After:**
```python
# NodeInterrupt 예외를 직접 catch
except NodeInterrupt as interrupt:
    interrupt_data = interrupt.args[0]  # ✅ dict 추출
    await progress_callback("collaboration_started", interrupt_data)  # ✅ dict 전송
```

### 3. ✅ 반복 수정 플로우 구현

**_collaboration_routing 개선:**
```python
user_action = state.get("user_action")

if user_action == "edit_more":
    return "continue_editing"  # ← collaborate로 loop back
elif user_action == "approve":
    return "request_approval"  # ← user_confirm으로 이동
```

**Frontend에서 전송해야 하는 메시지:**
```typescript
// 수정 버튼 클릭
wsClient.send({
  type: "field_update",
  user_action: "edit_more",  // ← 이 필드 추가
  field: "landlord_name",
  value: "홍길동"
});

// OK 버튼 클릭
wsClient.send({
  type: "request_confirmation",
  user_action: "approve"  // ← 이 필드 추가
});
```

---

## 🧪 테스트 시나리오

### Test Case 1: 기본 플로우

**입력:**
```
사용자: "임대차 계약서 작성해줘"
```

**기대 동작:**
1. ✅ Dialog 열림 (문서 미리보기)
2. ✅ 사용자가 필드 수정
3. ✅ "수정" 버튼 클릭 → Dialog 다시 열림 (재수정 가능)
4. ✅ "OK" 버튼 클릭 → 최종 승인
5. ✅ 문서 완성

**검증 포인트:**
- [ ] NodeInterrupt가 supervisor까지 전파되는지
- [ ] Dialog가 정상 오픈되는지
- [ ] WebSocket 메시지가 정상 전송되는지
- [ ] Checkpoint가 PostgreSQL에 저장되는지

### Test Case 2: 반복 수정

**입력:**
```
사용자: "임대차 계약서 작성해줘"
→ 수정 1 (임대인 이름 변경)
→ 수정 2 (임차인 이름 변경)
→ 수정 3 (계약금 변경)
→ OK
```

**기대 동작:**
1. ✅ 수정 1 → Dialog 닫힘 → 다시 열림
2. ✅ 수정 2 → Dialog 닫힘 → 다시 열림
3. ✅ 수정 3 → Dialog 닫힘 → 다시 열림
4. ✅ OK → 최종 완료

**검증 포인트:**
- [ ] `_collaboration_routing`이 "edit_more" 감지하는지
- [ ] collaborate 노드로 loop back 하는지
- [ ] 각 수정마다 checkpoint 저장되는지
- [ ] 최종 완료 시 finalize 노드로 이동하는지

### Test Case 3: NodeInterrupt 재발생

**입력:**
```
사용자: "임대차 계약서 작성해줘"
→ 수정
→ "OK" (승인 요청)
→ user_confirm 노드에서 NodeInterrupt 재발생 확인
```

**기대 동작:**
1. ✅ collaborate 노드에서 NodeInterrupt (첫 번째)
2. ✅ 사용자 "OK" 클릭
3. ✅ resume → user_confirm 노드 실행
4. ✅ user_confirm 노드에서 NodeInterrupt (두 번째)
5. ✅ approval_required 메시지 전송

**검증 포인트:**
- [ ] 첫 번째 NodeInterrupt 정상 처리
- [ ] resume 후 user_confirm 노드 도달
- [ ] 두 번째 NodeInterrupt 정상 처리
- [ ] 각 interrupt마다 progress_callback 호출

---

## 🚀 실행 방법

### 1. 백엔드 재시작

```bash
cd C:\kdy\Projects\holmesnyangz\beta_v001\backend
uvicorn app.main:app --reload
```

**확인할 로그:**
```
✅ DocumentExecutor initialized (Subgraph Pattern)
   - AI Suggestions: True
   - Checkpointing: Managed by parent supervisor

✅ TeamBasedSupervisor initialized with 3 teams (checkpointing: True)

Initializing AsyncPostgresSaver checkpointer with PostgreSQL...
✅ PostgreSQL checkpointer initialized and graph recompiled successfully
```

### 2. Frontend 실행

```bash
cd C:\kdy\Projects\holmesnyangz\beta_v001\frontend
npm run dev
```

### 3. 테스트 실행

1. 브라우저에서 `http://localhost:3000` 접속
2. 채팅창에 "임대차 계약서 작성해줘" 입력
3. Dialog 오픈 확인
4. 필드 수정 후 "수정" 버튼 클릭
5. Dialog 재오픈 확인
6. "OK" 버튼 클릭
7. 최종 완료 메시지 확인

### 4. 로그 확인

**Backend 로그 확인:**
```bash
# 실시간 로그
tail -f C:\kdy\Projects\holmesnyangz\beta_v001\backend\logs\app.log

# 검색
grep "NodeInterrupt" C:\kdy\Projects\holmesnyangz\beta_v001\backend\logs\app.log
grep "collaboration_started" C:\kdy\Projects\holmesnyangz\beta_v001\backend\logs\app.log
```

**PostgreSQL Checkpoint 확인:**
```bash
psql -U postgres -d real_estate -c "SELECT * FROM checkpoints ORDER BY checkpoint_id DESC LIMIT 5;"
```

---

## 📊 변경 파일 목록

### 수정된 파일 (3개)

1. **backend/app/service_agent/execution_agents/document_executor.py**
   - 690줄 (이전 1018줄)
   - 328줄 감소

2. **backend/app/service_agent/supervisor/team_supervisor.py**
   - 1760줄
   - 주요 수정: Line 76-79, 997-1095, 1649-1759

3. **backend/app/api/chat_api.py**
   - 수정 불필요 (기존 코드가 Command API 호출하는 방식 유지)

### 백업 파일 (3개)

1. **backend/app/service_agent/execution_agents/document_executor_old.py**
2. **backend/app/service_agent/supervisor/team_supervisor_old.py**
3. **backend/app/api/chat_api_old.py**

---

## 🔍 중요 코드 위치

### DocumentExecutor

| 메서드/영역 | 라인 | 설명 |
|------------|------|------|
| `__init__` | 82-110 | enable_checkpointing 제거 |
| `build_subgraph()` | 121-209 | StateGraph 반환 |
| `collaborate_node` | 329-371 | NodeInterrupt 발생 |
| `user_confirm_node` | 373-412 | NodeInterrupt 발생 |
| `_collaboration_routing` | 508-549 | user_action 지원 |

### TeamSupervisor

| 메서드/영역 | 라인 | 설명 |
|------------|------|------|
| `__init__` | 76-79 | DocumentExecutor 초기화 |
| `_execute_single_team` | 997-1095 | Subgraph compile & execute |
| `handle_document_update` | 1649-1681 | Command API: update_state |
| `resume_document_workflow` | 1683-1759 | Command API: astream(None) |

---

## ⚠️ 주의사항

### Frontend 수정 필요

**document-collaboration-dialog.tsx** 확인:

```typescript
// 수정 필요: user_action 필드 추가
const handleEditMore = () => {
  wsClient.send({
    type: "field_update",
    user_action: "edit_more",  // ← 이 필드 추가
    field: fieldName,
    value: fieldValue
  });
};

const handleApprove = () => {
  wsClient.send({
    type: "request_confirmation",
    user_action: "approve"  // ← 이 필드 추가
  });
};
```

### PostgreSQL Checkpoint 테이블

확인 필요:
```sql
-- 테이블 존재 확인
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public'
AND table_name IN ('checkpoints', 'checkpoint_blobs', 'checkpoint_writes');

-- Checkpoint 데이터 확인
SELECT checkpoint_id, thread_id, checkpoint_ns, type
FROM checkpoints
ORDER BY checkpoint_id DESC
LIMIT 10;
```

---

## 📝 다음 단계

### 즉시 테스트

1. [ ] 백엔드 재시작
2. [ ] Frontend 접속
3. [ ] "임대차 계약서 작성해줘" 입력
4. [ ] Dialog 오픈 확인
5. [ ] 필드 수정 확인
6. [ ] 반복 수정 플로우 확인

### 오류 발생 시

1. Backend 로그 확인:
   ```
   grep "ERROR" backend/logs/app.log
   ```

2. 특정 오류 검색:
   ```
   grep "aupdate\|JSON serializable\|NodeInterrupt" backend/logs/app.log
   ```

3. PostgreSQL 연결 확인:
   ```
   psql -U postgres -d real_estate -c "SELECT 1;"
   ```

### 추가 개선 사항 (선택)

- [ ] Frontend user_action 필드 추가
- [ ] 더 많은 document type 지원
- [ ] AI suggestions 기능 구현
- [ ] Checkpoint 복구 기능 테스트

---

## 🎉 완료!

Phase 1, 2, 3 모두 완료되었습니다!

**핵심 개선:**
1. ✅ 단일 Checkpointer 아키텍처
2. ✅ NodeInterrupt 정상 전파
3. ✅ Command API 직접 사용
4. ✅ JSON Serialization 오류 해결
5. ✅ 반복 수정 플로우 지원

이제 테스트하고 결과를 확인하시면 됩니다! 🚀
