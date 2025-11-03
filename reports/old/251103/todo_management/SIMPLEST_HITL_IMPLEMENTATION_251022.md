# 가장 간단한 HITL 구현 방법 - Progress Container 활용

**작성일:** 2025-10-22
**작성자:** Claude Code
**목적:** 기존 Progress Container를 활용한 최소 변경 HITL 구현

---

## 🎯 핵심 아이디어

> **"이미 있는 Progress Container의 Stage 2 (Analysis)에서 승인 버튼만 추가하자"**

### 왜 이것이 가장 간단한가?

1. **이미 Planning 정보를 보여주고 있음** (135-177줄)
2. **WebSocket 통신 이미 구현됨**
3. **UI 컴포넌트 이미 존재**
4. **최소한의 코드 변경**

---

## 📝 구현 계획 (단 3개 파일만 수정)

### 1️⃣ Frontend: AnalysisContent에 승인 버튼 추가

**파일:** `frontend/components/progress-container.tsx`

```tsx
// Line 126-180 수정
function AnalysisContent({ plan }: { plan?: ExecutionPlan }) {
  // NEW: 승인 상태 관리
  const [requiresApproval, setRequiresApproval] = useState(false)
  const [isWaitingApproval, setIsWaitingApproval] = useState(false)

  // NEW: 고위험 작업 체크
  useEffect(() => {
    if (plan && !plan.isLoading) {
      const hasHighRiskTask = plan.execution_steps?.some(step =>
        step.task?.includes("계약") ||
        step.task?.includes("법률") ||
        step.task?.includes("거래")
      )
      setRequiresApproval(hasHighRiskTask || false)
    }
  }, [plan])

  // NEW: 승인/거부 핸들러
  const handleApprove = () => {
    window.dispatchEvent(new CustomEvent('hitl-decision', {
      detail: { action: 'approve' }
    }))
    setIsWaitingApproval(false)
  }

  const handleReject = () => {
    window.dispatchEvent(new CustomEvent('hitl-decision', {
      detail: { action: 'reject' }
    }))
    setIsWaitingApproval(false)
  }

  return (
    <div className="space-y-3">
      <div className="text-center">
        <div className="text-base font-semibold">질문을 분석하고 있습니다</div>
      </div>

      {plan && !plan.isLoading && plan.execution_steps && plan.execution_steps.length > 0 && (
        <div className="space-y-2">
          {/* 기존: 의도 분석 결과 */}
          <div className="p-3 bg-secondary/30 rounded-lg">
            {/* 기존 코드 유지 */}
          </div>

          {/* 기존: 작업 계획 */}
          <div className="space-y-2">
            <div className="font-medium">작업 계획:</div>
            {plan.execution_steps.map((step, idx) => (
              <div key={idx} className="flex items-center gap-3 p-2 bg-muted/50 rounded">
                {/* 기존 코드 유지 */}
              </div>
            ))}
          </div>

          {/* NEW: 승인 섹션 (고위험 작업일 때만) */}
          {requiresApproval && !isWaitingApproval && (
            <div className="pt-3 border-t border-border">
              <div className="p-3 bg-amber-50 dark:bg-amber-900/20 rounded-lg border border-amber-200 dark:border-amber-800">
                <p className="text-sm font-medium mb-3">
                  ⚠️ 이 작업은 승인이 필요합니다
                </p>
                <div className="flex gap-2">
                  <button
                    onClick={() => {
                      handleApprove()
                      setIsWaitingApproval(true)
                    }}
                    className="flex-1 px-3 py-2 bg-primary text-primary-foreground rounded hover:bg-primary/90"
                  >
                    승인
                  </button>
                  <button
                    onClick={handleReject}
                    className="flex-1 px-3 py-2 bg-secondary text-secondary-foreground rounded hover:bg-secondary/90"
                  >
                    거부
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* 기존: 자동 진행 메시지 (승인 불필요 시) */}
          {!requiresApproval && (
            <div className="pt-3 border-t border-border">
              <p className="text-xs text-muted-foreground text-center">
                곧 작업을 시작합니다...
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
```

---

### 2️⃣ Frontend: ChatInterface에서 이벤트 처리

**파일:** `frontend/components/chat-interface.tsx`

```tsx
// WebSocket 메시지 핸들러 부분에 추가

useEffect(() => {
  // HITL 결정 이벤트 리스너
  const handleHitlDecision = (event: CustomEvent) => {
    const { action } = event.detail

    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({
        type: 'hitl_decision',
        session_id: currentSessionId,
        action: action  // 'approve' or 'reject'
      }))
    }
  }

  window.addEventListener('hitl-decision', handleHitlDecision as any)

  return () => {
    window.removeEventListener('hitl-decision', handleHitlDecision as any)
  }
}, [ws, currentSessionId])
```

---

### 3️⃣ Backend: 간단한 조건부 실행

**파일:** `backend/app/service_agent/supervisor/team_supervisor.py`

```python
def _route_after_planning(self, state: MainSupervisorState) -> str:
    """계획 후 라우팅 (HITL 체크 추가)"""

    planning_state = state.get("planning_state")

    if planning_state:
        analyzed_intent = planning_state.get("analyzed_intent", {})
        intent_type = analyzed_intent.get("intent_type", "")

        # NEW: 고위험 작업 식별
        HIGH_RISK_KEYWORDS = ["contract", "legal", "transaction", "계약", "법률", "거래"]
        query = state.get("query", "").lower()

        is_high_risk = any(keyword in query for keyword in HIGH_RISK_KEYWORDS)

        # NEW: 고위험이면 승인 대기
        if is_high_risk:
            # WebSocket으로 승인 요청 전송
            session_id = state.get("session_id")
            if session_id and session_id in self._progress_callbacks:
                await self._progress_callbacks[session_id]("approval_required", {
                    "message": "이 작업은 승인이 필요합니다",
                    "plan": planning_state
                })

                # 승인 대기 (간단한 방법: 플래그 체크)
                approval_status = state.get("approval_status", "pending")

                if approval_status == "rejected":
                    logger.info("[TeamSupervisor] User rejected the plan")
                    return "respond"  # 실행하지 않고 바로 응답
                elif approval_status != "approved":
                    # 승인 대기 중 (실제로는 WebSocket 이벤트로 처리)
                    return "waiting"  # 새로운 상태 추가 필요

        # 기존 로직
        if intent_type == "irrelevant":
            return "respond"

        if execution_steps:
            return "execute"

    return "respond"
```

**WebSocket 핸들러 추가:**

```python
# backend/app/api/chat_api.py

@router.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    # 기존 코드...

    elif message_type == "hitl_decision":
        action = data.get("action")  # 'approve' or 'reject'

        # 간단한 처리: 상태 업데이트
        if action == "approve":
            # 실행 계속
            await supervisor.resume_execution(session_id)
        else:
            # 실행 취소, 기본 응답 생성
            await supervisor.cancel_and_respond(session_id)
```

---

## 🎯 핵심 장점

### 1. 최소 변경
- Frontend: 1개 컴포넌트만 수정
- Backend: 조건문 추가만
- 새 파일 생성 불필요

### 2. 즉시 테스트 가능
```bash
# 테스트 쿼리
"이 매물 계약서 작성해줘"  # → 승인 필요
"강남 아파트 시세 알려줘"  # → 자동 실행
```

### 3. 점진적 확장 가능
- Phase 1: 키워드 기반 (현재)
- Phase 2: Intent 기반
- Phase 3: 세밀한 제어

---

## 📋 구현 체크리스트 (30분 내 완료 가능)

### Step 1: UI 수정 (10분)
- [ ] progress-container.tsx의 AnalysisContent 수정
- [ ] 승인 버튼 스타일링
- [ ] 이벤트 디스패치

### Step 2: 이벤트 연결 (10분)
- [ ] chat-interface.tsx에 이벤트 리스너 추가
- [ ] WebSocket 메시지 전송

### Step 3: Backend 처리 (10분)
- [ ] _route_after_planning에 조건 추가
- [ ] WebSocket 핸들러에 hitl_decision 처리

---

## 🔧 테스트 시나리오

```typescript
// 1. 고위험 작업 테스트
user: "계약서 작성해줘"
→ Analysis 단계에서 승인 버튼 표시
→ 승인 클릭
→ 실행 진행

// 2. 일반 작업 테스트
user: "날씨 알려줘"
→ Analysis 단계에서 자동 진행
→ 승인 버튼 표시 안됨

// 3. 거부 테스트
user: "법률 검토 해줘"
→ Analysis 단계에서 승인 버튼 표시
→ 거부 클릭
→ "요청을 취소했습니다" 메시지
```

---

## 🚀 바로 시작하기

```bash
# 1. Frontend 수정
code frontend/components/progress-container.tsx
# AnalysisContent 함수에 위 코드 추가 (line 126)

# 2. Backend 수정
code backend/app/service_agent/supervisor/team_supervisor.py
# _route_after_planning 메서드에 HIGH_RISK_KEYWORDS 체크 추가

# 3. 테스트
npm run dev  # Frontend
python main.py  # Backend

# 브라우저에서 테스트
# "계약서 작성해줘" 입력
```

---

## 🎯 왜 이 방법이 최선인가?

### 기존 구조 최대 활용
- Progress Container **이미 planning 정보 표시**
- WebSocket **이미 연결됨**
- State 관리 **이미 구현됨**

### 사용자 경험
- **자연스러운 플로우**: 분석 → 승인 → 실행
- **시각적 피드백**: 이미 있는 UI 활용
- **빠른 응답**: 불필요한 승인 없음

### 확장성
- 나중에 interrupt() 추가 가능
- Command 패턴으로 전환 가능
- Todo Management로 발전 가능

---

## 📝 결론

> **"복잡하게 생각하지 마세요. 이미 있는 Progress Container의 Analysis 단계에 승인 버튼만 추가하면 됩니다."**

- 구현 시간: **30분**
- 수정 파일: **3개**
- 새 파일: **0개**
- 즉시 효과: **고위험 작업 통제**

이것이 가장 실용적이고 빠른 HITL 구현 방법입니다!

---

**작성 완료:** 2025-10-22
**예상 구현 시간:** 30분
**난이도:** ⭐⭐☆☆☆ (쉬움)