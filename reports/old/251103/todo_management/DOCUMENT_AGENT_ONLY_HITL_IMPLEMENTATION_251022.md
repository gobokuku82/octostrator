# Document Agent 단독 HITL 구현 계획

**작성일:** 2025-10-22
**작성자:** Claude Code
**목적:** Document Executor에만 HITL 구현하여 최소 범위로 시작

---

## 🎯 핵심 전략

> **"3개 Agent 중 Document Agent 하나에만 HITL 구현"**

### 왜 이 방법이 최적인가?

1. **가장 위험한 Agent**
   - 계약서 생성 = 법적 책임
   - 실수 허용 안됨
   - 사용자 확인 필수

2. **명확한 중단 지점**
   - prepare → generate → review → finalize
   - 각 단계가 명확히 구분됨

3. **다른 Agent는 자동 실행**
   - SearchAgent: 조회만 하므로 안전
   - MarketAgent: 분석만 하므로 안전
   - DocumentAgent: **위험하므로 HITL 필요**

---

## 📋 구현 위치 분석

### 현재 Document Executor 구조

```python
# 노드 흐름 (Line 121-137)
START → prepare → generate → review_check → review → finalize → END
                                    ↓
                               (skip review)
```

### HITL 추가 지점

```python
START → prepare → [INTERRUPT POINT] → generate → review → finalize → END
                         ↑
                   사용자 승인 필요
```

---

## 💻 구현 계획

### 1️⃣ Document Executor 수정 (최소 변경)

**파일:** `backend/app/service_agent/execution_agents/document_executor.py`

#### A. Interrupt 지점 추가 (prepare 노드 후)

```python
# Line 148-176 수정
async def prepare_document_node(self, state: DocumentTeamState) -> DocumentTeamState:
    """문서 준비 노드 - HITL 추가"""
    logger.info("[DocumentTeam] Preparing document")

    state["team_name"] = self.team_name
    state["status"] = "in_progress"
    state["start_time"] = datetime.now()

    # 문서 타입 확인
    doc_type = state.get("document_type", "lease_contract")

    # 템플릿 선택
    template = self.templates.get(doc_type)
    if template:
        state["template"] = template
        logger.info(f"[DocumentTeam] Selected template: {template['template_name']}")

    # NEW: HITL - 고위험 문서는 승인 필요
    HIGH_RISK_DOCS = ["lease_contract", "sales_contract", "loan_application"]

    if doc_type in HIGH_RISK_DOCS:
        # 승인 요청 상태 설정
        state["requires_approval"] = True
        state["approval_status"] = "pending"

        # WebSocket으로 승인 요청 전송
        await self._request_approval(state)

        # 승인 대기 (간단한 구현)
        max_wait = 30  # 30초 대기
        wait_time = 0

        while wait_time < max_wait:
            if state.get("approval_status") == "approved":
                logger.info("[DocumentTeam] User approved document generation")
                break
            elif state.get("approval_status") == "rejected":
                logger.info("[DocumentTeam] User rejected document generation")
                state["status"] = "cancelled"
                state["error"] = "사용자가 문서 생성을 거부했습니다"
                return state  # 여기서 중단

            await asyncio.sleep(1)
            wait_time += 1

        if wait_time >= max_wait:
            # 타임아웃 - 자동 거부
            state["approval_status"] = "timeout"
            state["status"] = "cancelled"
            state["error"] = "승인 대기 시간 초과"
            return state

    # 파라미터 검증 (기존 코드)
    if not state.get("document_params"):
        state["document_params"] = self._extract_params_from_context(state)

    state["generation_status"] = "ready"
    return state

async def _request_approval(self, state: DocumentTeamState):
    """승인 요청 전송"""
    # WebSocket 이벤트 발생
    shared_context = state.get("shared_context", {})
    session_id = shared_context.get("session_id")

    if session_id and hasattr(self, '_approval_callback'):
        await self._approval_callback(session_id, {
            "type": "document_approval_required",
            "document_type": state.get("document_type"),
            "template_name": state.get("template", {}).get("template_name"),
            "message": f"{state.get('template', {}).get('template_name', '문서')}를 생성하려고 합니다. 승인하시겠습니까?"
        })
```

#### B. 승인 처리 메서드 추가

```python
# 새로운 메서드 추가 (Line 520 이후)
def set_approval_callback(self, callback):
    """승인 콜백 설정"""
    self._approval_callback = callback

async def handle_user_decision(self, session_id: str, decision: str):
    """사용자 결정 처리"""
    # 현재 실행 중인 상태 찾기
    # 간단한 구현: 전역 상태 저장소 사용
    if hasattr(self, '_current_states'):
        state = self._current_states.get(session_id)
        if state:
            state["approval_status"] = decision
            logger.info(f"[DocumentTeam] Received user decision: {decision}")
```

---

### 2️⃣ TeamSupervisor 연동

**파일:** `backend/app/service_agent/supervisor/team_supervisor.py`

```python
# DocumentExecutor 초기화 시 콜백 설정
def _initialize_teams(self):
    """팀 초기화"""

    # Document Executor 생성
    from app.service_agent.execution_agents.document_executor import DocumentExecutor
    self.document_executor = DocumentExecutor(self.llm_context)

    # HITL 콜백 설정
    self.document_executor.set_approval_callback(self._send_approval_request)

async def _send_approval_request(self, session_id: str, data: dict):
    """승인 요청 전송"""
    if session_id in self._progress_callbacks:
        await self._progress_callbacks[session_id]("document_approval", data)
```

---

### 3️⃣ Frontend 수정 (간단한 모달)

**파일:** `frontend/components/chat-interface.tsx`

```tsx
// Document 승인 모달 추가
const [documentApproval, setDocumentApproval] = useState(null);

useEffect(() => {
  if (!ws) return;

  ws.onmessage = (event) => {
    const message = JSON.parse(event.data);

    if (message.type === 'progress') {
      const { event_type, data } = message;

      if (event_type === 'document_approval') {
        // Document 승인 요청 표시
        setDocumentApproval({
          documentType: data.document_type,
          templateName: data.template_name,
          message: data.message
        });
      }
    }
  };
}, [ws]);

// 승인/거부 처리
const handleDocumentDecision = (decision: 'approved' | 'rejected') => {
  if (ws && documentApproval) {
    ws.send(JSON.stringify({
      type: 'document_decision',
      session_id: currentSessionId,
      decision: decision
    }));
    setDocumentApproval(null);
  }
};

// UI 렌더링
{documentApproval && (
  <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
    <div className="bg-white dark:bg-gray-800 p-6 rounded-lg max-w-md">
      <h3 className="text-lg font-bold mb-4">📄 문서 생성 승인</h3>
      <p className="mb-4">{documentApproval.message}</p>
      <div className="bg-gray-100 dark:bg-gray-700 p-3 rounded mb-4">
        <p className="text-sm">문서 유형: {documentApproval.templateName}</p>
      </div>
      <div className="flex gap-3">
        <button
          onClick={() => handleDocumentDecision('approved')}
          className="flex-1 px-4 py-2 bg-primary text-white rounded hover:bg-primary/90"
        >
          승인
        </button>
        <button
          onClick={() => handleDocumentDecision('rejected')}
          className="flex-1 px-4 py-2 bg-gray-300 text-gray-700 rounded hover:bg-gray-400"
        >
          거부
        </button>
      </div>
    </div>
  </div>
)}
```

---

## 🔄 작동 플로우

### 1. 일반 질문 (SearchAgent)
```
User: "강남 아파트 시세 알려줘"
→ SearchAgent 자동 실행
→ 승인 불필요
→ 바로 결과 표시
```

### 2. 문서 생성 (DocumentAgent)
```
User: "임대차 계약서 작성해줘"
→ DocumentAgent prepare 노드
→ [INTERRUPT] 승인 요청 모달
→ 사용자 승인
→ generate 노드 실행
→ 문서 생성 완료
```

### 3. 거부 시나리오
```
User: "대출 신청서 작성해줘"
→ DocumentAgent prepare 노드
→ [INTERRUPT] 승인 요청 모달
→ 사용자 거부
→ "요청이 취소되었습니다" 메시지
→ 종료
```

---

## 📊 장단점 분석

### 장점 ✅

1. **최소 범위**
   - 1개 Agent만 수정
   - 다른 Agent는 그대로

2. **명확한 테스트**
   - Document 생성만 승인 필요
   - 나머지는 자동 실행

3. **점진적 확장**
   - 성공하면 다른 Agent에도 적용
   - 실패해도 영향 최소화

4. **실용적**
   - 가장 위험한 작업만 통제
   - UX 부담 최소화

### 단점 ❌

1. **일관성 부족**
   - Agent마다 다른 동작
   - 사용자 혼란 가능

2. **제한적 제어**
   - Document만 중단 가능
   - 다른 작업은 통제 불가

---

## 📋 구현 체크리스트

### Backend (30분)
- [ ] document_executor.py의 prepare_node 수정
- [ ] 승인 대기 로직 추가
- [ ] 승인 콜백 메서드 구현
- [ ] TeamSupervisor 연동

### Frontend (20분)
- [ ] 승인 모달 컴포넌트 추가
- [ ] WebSocket 메시지 처리
- [ ] 승인/거부 이벤트 전송

### 테스트 (10분)
- [ ] "계약서 작성" → 승인 필요
- [ ] "시세 조회" → 자동 실행
- [ ] 승인/거부 동작 확인

---

## 🚀 즉시 시작 명령

```bash
# 1. Backend 수정
code backend/app/service_agent/execution_agents/document_executor.py
# Line 148 prepare_document_node에 HITL 로직 추가

# 2. Frontend 수정
code frontend/components/chat-interface.tsx
# Document 승인 모달 추가

# 3. 테스트
# Terminal 1
cd backend && python main.py

# Terminal 2
cd frontend && npm run dev

# Browser
# "임대차 계약서 작성해줘" 입력
```

---

## 🎯 핵심 요약

**Document Agent 하나만 수정하여:**
- ✅ 가장 위험한 작업(문서 생성)만 통제
- ✅ 다른 Agent는 그대로 유지
- ✅ 1시간 내 구현 가능
- ✅ 실패해도 영향 최소화

**이것이 가장 현실적인 HITL 시작점입니다!**

---

**작성 완료:** 2025-10-22
**예상 구현 시간:** 1시간
**난이도:** ⭐⭐⭐☆☆ (보통)