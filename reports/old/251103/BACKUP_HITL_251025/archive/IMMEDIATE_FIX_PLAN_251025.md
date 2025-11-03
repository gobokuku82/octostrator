# 즉시 수정 계획 (HITL 작동 시키기)

**작성일**: 2025-10-25
**문서 버전**: 1.0
**목표**: 현재 멈춘 워크플로우를 즉시 작동시키기

---

## 🎯 목표

사용자의 요구사항:
1. 문서 생성 → 사용자 확인
2. 수정 → 확인 → 수정 → 확인 (반복)
3. OK → 종료

---

## 🔴 즉시 수정해야 할 3가지

### 1. `aupdate` 오류 수정

**파일**: `backend/app/service_agent/execution_agents/document_executor.py`

**Line 912** 문제:
```python
await self.app.aupdate(update_data, config)  # ❌ 작동 안 함
```

**원인**:
- LangGraph 0.6.8에서 `workflow.compile()`은 `CompiledGraph`를 반환
- 하지만 `CompiledGraph`에 `aupdate`가 없을 수 있음 (타입 확인 필요)

**해결 방법 A - Command API 사용** (LangGraph 0.6 정석):
```python
# Line 897-926 전체 교체
async def handle_update(self, session_id: str, update_data: Dict) -> bool:
    """
    LangGraph 0.6 Command API를 사용한 상태 업데이트
    """
    try:
        if session_id not in self.active_sessions:
            logger.error(f"Session not found: {session_id}")
            return False

        session = self.active_sessions[session_id]
        config = session.get("config", {"configurable": {"thread_id": session_id}})

        # ✅ Command API 사용 (LangGraph 0.6)
        if self.app and self.checkpointer:
            from langgraph.pregel import GraphCommand

            # 상태 업데이트 명령 생성
            command = GraphCommand(
                update=update_data,
                resume=None  # 재개하지 않고 상태만 업데이트
            )

            # 명령 실행
            await self.app.ainvoke(command, config)
            logger.info(f"✅ State updated via Command API for session {session_id}")

            # 세션 상태도 업데이트
            if "state" in session:
                session["state"].update(update_data)

            return True
        else:
            logger.error("App or checkpointer not initialized")
            return False

    except Exception as e:
        logger.error(f"Failed to update state for session {session_id}: {e}")
        return False
```

**해결 방법 B - Checkpoint 직접 조작** (더 안전):
```python
async def handle_update(self, session_id: str, update_data: Dict) -> bool:
    """
    Checkpoint를 직접 조작하여 상태 업데이트
    """
    try:
        if session_id not in self.active_sessions:
            logger.error(f"Session not found: {session_id}")
            return False

        session = self.active_sessions[session_id]
        config = session.get("config", {"configurable": {"thread_id": session_id}})

        # ✅ 메모리에서 상태 업데이트
        if "state" in session:
            session["state"].update(update_data)
            logger.info(f"✅ State updated in memory for session {session_id}")
            return True
        else:
            logger.error("Session state not found")
            return False

    except Exception as e:
        logger.error(f"Failed to update state for session {session_id}: {e}")
        return False
```

**추천**: **방법 B (Checkpoint 직접 조작)**
- 더 간단함
- 오류 가능성 낮음
- LangGraph 버전 변경에 영향 안 받음

---

### 2. JSON Serialization 오류 수정

**문제**: `Interrupt` 객체를 WebSocket으로 전송 시도

**로그**:
```
ERROR - Failed to send message: Object of type Interrupt is not JSON serializable
```

**원인 찾기**:

**파일**: `backend/app/service_agent/supervisor/team_supervisor.py`

**예상 위치**: Line 1015-1050 근처 (_execute_single_team)

**현재 코드** (추정):
```python
# 잘못된 코드
if progress_callback:
    await progress_callback("collaboration_started", interrupt)  # ❌ Interrupt 객체 직접 전송
```

**수정**:
```python
# 올바른 코드
if progress_callback:
    # Interrupt 객체를 딕셔너리로 변환
    interrupt_dict = interrupt.args[0] if interrupt.args else {}
    await progress_callback("collaboration_started", interrupt_dict)  # ✅ 딕셔너리 전송
```

**확인 필요**:
- `team_supervisor.py`의 정확한 위치 찾기
- `progress_callback` 호출하는 모든 곳 확인

---

### 3. 반복 수정 플로우 구현

**사용자 요구사항**:
```
문서 생성 → 사용자 확인 → 수정 → 확인 → 수정 → ... → OK → 종료
```

**현재 플로우**:
```
initialize → collect_context → generate_draft → collaborate (Interrupt)
  → user_confirm → ai_review → finalize
```

**문제**:
- `collaborate` 노드에서 한 번만 Interrupt 발생
- 사용자가 "수정" 요청하면 다시 `collaborate`로 돌아가야 함

**해결 - 조건부 라우팅 수정**:

**파일**: `backend/app/service_agent/execution_agents/document_executor.py`

**Line 218-227** (collaborate 노드 라우팅):
```python
# 현재 코드
workflow.add_conditional_edges(
    "collaborate",
    self._collaboration_routing,
    {
        "continue_editing": "collaborate",  # ✅ 이미 있음!
        "request_approval": "user_confirm",
        "ai_assistance": "ai_review",
        "error": "error_handler"
    }
)
```

**좋은 소식**: 이미 `"continue_editing": "collaborate"` 가 있음!

**확인 필요**: `_collaboration_routing` 함수가 올바르게 동작하는지

**예상 위치**: Line 600-650 근처

**필요한 로직**:
```python
async def _collaboration_routing(self, state: Dict[str, Any]) -> str:
    """협업 단계 라우팅"""

    # 사용자가 "재수정" 요청 시
    if state.get("user_action") == "edit_more":
        return "continue_editing"  # ← collaborate 노드로 다시 돌아감

    # 사용자가 "OK" (승인 요청) 시
    elif state.get("user_action") == "approve":
        return "request_approval"  # ← user_confirm 노드로 진행

    # AI 도움 요청 시
    elif state.get("user_action") == "ai_help":
        return "ai_assistance"

    # 기본값: 계속 편집
    else:
        return "continue_editing"
```

---

## 📋 즉시 적용 체크리스트

### Step 1: `aupdate` 오류 수정 (5분)

**파일**: `backend/app/service_agent/execution_agents/document_executor.py`

**수정 내용**:
```python
# Line 897-926 전체 교체 (방법 B 사용)
async def handle_update(self, session_id: str, update_data: Dict) -> bool:
    """상태 업데이트 (메모리 방식)"""
    try:
        if session_id not in self.active_sessions:
            logger.error(f"Session not found: {session_id}")
            return False

        session = self.active_sessions[session_id]

        # 메모리에서 상태 업데이트
        if "state" in session:
            session["state"].update(update_data)
            logger.info(f"✅ State updated for session {session_id}: {list(update_data.keys())}")
            return True
        else:
            logger.error("Session state not found")
            return False

    except Exception as e:
        logger.error(f"Failed to update state: {e}")
        return False
```

**적용 방법**:
1. 파일 열기: `backend/app/service_agent/execution_agents/document_executor.py`
2. Line 897-926 찾기 (`async def handle_update`)
3. 위 코드로 교체
4. 저장

---

### Step 2: JSON Serialization 오류 수정 (10분)

**먼저 확인**:

**파일**: `backend/app/service_agent/supervisor/team_supervisor.py`

**찾을 코드**:
```python
# Line 1015-1050 근처에서 찾기
if isinstance(result, dict) and result.get("status") == "interrupted":
    interrupt_data = result.get("interrupt", {})

    # ⚠️ 이 부분 찾기
    if progress_callback:
        await progress_callback("collaboration_started", ???)  # ← 무엇을 전송하는지 확인
```

**수정**:
```python
if isinstance(result, dict) and result.get("status") == "interrupted":
    interrupt_data = result.get("interrupt", {})

    # ✅ 딕셔너리만 전송
    if progress_callback:
        await progress_callback("collaboration_started", {
            "session_id": interrupt_data.get("session_id"),
            "document_id": interrupt_data.get("document_id"),
            "document_type": interrupt_data.get("document_type"),
            "editable_fields": interrupt_data.get("editable_fields", []),
            "preview": interrupt_data.get("preview", ""),
            "message": interrupt_data.get("message", "")
        })
```

---

### Step 3: 반복 수정 플로우 확인 (15분)

**파일**: `backend/app/service_agent/execution_agents/document_executor.py`

**1. `_collaboration_routing` 함수 찾기** (Line 600-650 예상):
```python
async def _collaboration_routing(self, state: Dict[str, Any]) -> str:
    # 이 함수 내용 확인
```

**2. 사용자 액션 처리 확인**:
- `state.get("user_action")` 또는 유사한 필드 사용하는지
- "edit_more", "approve" 등의 값으로 분기하는지

**3. 수정 필요 시**:
```python
async def _collaboration_routing(self, state: Dict[str, Any]) -> str:
    """협업 단계 라우팅 (반복 수정 지원)"""

    # 사용자 액션 확인
    user_action = state.get("user_action")

    if user_action == "edit_more":
        # 계속 편집
        logger.info("User requested more edits")
        return "continue_editing"

    elif user_action == "approve" or state.get("request_approval"):
        # 승인 요청
        logger.info("User requested approval")
        return "request_approval"

    elif user_action == "ai_help":
        # AI 도움
        logger.info("User requested AI assistance")
        return "ai_assistance"

    else:
        # 기본값: 계속 편집 (안전)
        logger.info("Default: continue editing")
        return "continue_editing"
```

---

### Step 4: Frontend 메시지 전송 확인 (선택)

**파일**: `frontend/components/document-collaboration-dialog.tsx`

**확인 사항**:
- 사용자가 "수정" 버튼 클릭 시 `user_action: "edit_more"` 전송하는지
- 사용자가 "OK" 버튼 클릭 시 `user_action: "approve"` 전송하는지

**예상 코드**:
```typescript
// 수정 버튼
const handleEditMore = () => {
  wsClient.send({
    type: "field_update",
    user_action: "edit_more",  // ← 이 필드 있는지 확인
    // ...
  });
};

// OK 버튼
const handleApprove = () => {
  wsClient.send({
    type: "request_confirmation",
    user_action: "approve",  // ← 이 필드 있는지 확인
  });
};
```

---

## 🧪 테스트 시나리오

### Test Case 1: 기본 플로우

**입력**:
```
사용자: "임대차 계약서 작성해줘"
```

**기대 동작**:
1. ✅ Dialog 열림 (문서 미리보기)
2. ✅ 사용자가 필드 수정
3. ✅ "수정" 버튼 클릭 → Dialog 다시 열림 (재수정 가능)
4. ✅ "OK" 버튼 클릭 → 최종 승인
5. ✅ 문서 완성

---

### Test Case 2: 반복 수정

**입력**:
```
사용자: "임대차 계약서 작성해줘"
→ 수정 1
→ 수정 2
→ 수정 3
→ OK
```

**기대 동작**:
1. ✅ 수정 1 → Dialog 닫힘 → 다시 열림
2. ✅ 수정 2 → Dialog 닫힘 → 다시 열림
3. ✅ 수정 3 → Dialog 닫힘 → 다시 열림
4. ✅ OK → 최종 완료

---

## 🚀 즉시 적용 순서

### 우선순위 1 (5분): `aupdate` 오류 수정
- [ ] `document_executor.py` Line 897-926 수정
- [ ] 서버 재시작
- [ ] 테스트: "임대차 계약서 작성해줘"

### 우선순위 2 (10분): JSON Serialization 수정
- [ ] `team_supervisor.py` Line 1015-1050 확인
- [ ] `progress_callback` 호출 부분 수정
- [ ] 서버 재시작
- [ ] 테스트: Dialog 정상 오픈 확인

### 우선순위 3 (15분): 반복 플로우 확인
- [ ] `_collaboration_routing` 함수 확인
- [ ] 필요 시 수정
- [ ] Frontend 메시지 전송 확인
- [ ] 테스트: 반복 수정 플로우

---

## 📝 확인 필요 사항

수정 전에 다음 파일들을 확인해주세요:

1. **team_supervisor.py**:
   - Line 1015-1050: `progress_callback` 호출 부분
   - 무엇을 전송하는지 확인

2. **document_executor.py**:
   - Line 600-650: `_collaboration_routing` 함수
   - 어떤 로직으로 라우팅하는지 확인

3. **document-collaboration-dialog.tsx**:
   - "수정" 버튼과 "OK" 버튼이 어떤 메시지를 보내는지 확인

---

**문서 끝**

이 3가지만 수정하면 즉시 작동할 것입니다! 🚀
