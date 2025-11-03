# HITL Progress 지속 표시 구현 계획서

**작성일**: 2025-10-28
**버전**: 1.0
**목적**: Document Executor HITL 워크플로우에서 "승인" 후 Progress Page 지속 표시

---

## 📋 목차

1. [문제 분석](#1-문제-분석)
2. [현재 흐름 상세 분석](#2-현재-흐름-상세-분석)
3. [근본 원인 분석](#3-근본-원인-분석)
4. [해결 방안](#4-해결-방안)
5. [구현 계획](#5-구현-계획)
6. [테스트 시나리오](#6-테스트-시나리오)
7. [예상 결과](#7-예상-결과)

---

## 1. 문제 분석

### 1.1 현재 증상

**정상 작동 부분:**
- ✅ Document Executor 실행 시 Interrupt 발생
- ✅ 팝업창 (LeaseContractPage) 표시
- ✅ "승인" 버튼 클릭 시 팝업 닫힘
- ✅ `interrupt_response` 메시지 전송
- ✅ Workflow 재개 및 완료 (Backend에서 정상 작동)

**문제 발생 부분:**
- ❌ "승인" 후 Progress Page가 사라짐
- ❌ 답변 생성 과정 (Aggregate → Generate Response → LLM 호출) 진행 상황이 표시되지 않음
- ❌ 사용자는 약 7초간 아무 피드백 없이 대기
- ❌ 최종 답변이 갑자기 나타남 (UX 저하)

### 1.2 로그 분석 (Backend - 정상 작동 확인)

```
10:41:53 - interrupt_response 수신 (approve)
10:41:53 - Workflow 재개
10:41:53 - Document Executor: aggregate_node 실행
10:41:53 - Document Executor: generate_node 실행
10:41:53 - TeamSupervisor: aggregate_results_node 실행
10:41:53 - TeamSupervisor: generate_response_node 실행
10:42:00 - LLM 호출 완료 (7초 소요)
10:42:00 - Conversation 저장
10:42:00 - final_response 전송
```

**Backend는 정상 작동** - 문제는 Frontend UI에서 발생

---

## 2. 현재 흐름 상세 분석

### 2.1 전체 흐름 다이어그램

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. 사용자: "임대차 계약서 작성해줘" 입력                          │
└────────────────────────┬────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│ 2. Frontend: Progress Message 생성                              │
│    - type: "progress"                                           │
│    - progressData: { stage: "dispatch" }                        │
└────────────────────────┬────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│ 3. Backend: Document Executor 실행                               │
│    - plan_node → search_node → aggregate_node                   │
│    - aggregate_node에서 interrupt() 호출                         │
└────────────────────────┬────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│ 4. WebSocket: workflow_interrupted 메시지 전송                   │
│    {                                                            │
│      type: "workflow_interrupted",                              │
│      interrupt_data: {...},                                     │
│      message: "계약서 작성을 위해 승인이 필요합니다"             │
│    }                                                            │
└────────────────────────┬────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│ 5. Frontend: handleWSMessage                                    │
│    case 'workflow_interrupted':                                 │
│      setShowLeaseContract(true)  ← 팝업 표시                    │
│      setProcessState({ step: "idle" })  ← ⚠️ 주의!              │
└────────────────────────┬────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│ 6. 사용자: "승인" 버튼 클릭                                       │
└────────────────────────┬────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│ 7. LeaseContractPage: handleApprove()                           │
│    onApprove()  → interrupt_response 전송                       │
│    onClose()    → 🔴 문제 발생 지점!                             │
└────────────────────────┬────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│ 8. ChatInterface: onClose 핸들러                                │
│    setShowLeaseContract(false)                                  │
│    setLeaseContractData(null)                                   │
│    setMessages(prev => prev.filter(m => m.type !== "progress")) │
│    ↑ 🔴 Progress 메시지 삭제!                                    │
└────────────────────────┬────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│ 9. Backend: Workflow 재개 (사용자는 볼 수 없음)                   │
│    - Document Executor: generate_node 실행                      │
│    - TeamSupervisor: aggregate_results_node 실행                │
│    - TeamSupervisor: generate_response_node 실행                │
│    - LLM 호출 (7초 소요)                                         │
│    - 💡 progress_callback 호출하지만 Frontend에서 무시           │
└────────────────────────┬────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│ 10. WebSocket: final_response 전송                               │
└────────────────────────┬────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│ 11. Frontend: 최종 답변 표시                                      │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 코드 레벨 흐름

**파일 1: `chat-interface.tsx`**

```typescript
// Line 410-427: workflow_interrupted 처리
case 'workflow_interrupted':
  console.log('[ChatInterface] Workflow interrupted:', message)
  setLeaseContractData({
    interrupt_data: message.interrupt_data,
    interrupted_by: message.interrupted_by,
    interrupt_type: message.interrupt_type,
    message: message.message
  })
  setShowLeaseContract(true)  // 팝업 표시

  // Progress 상태는 유지 (사용자가 페이지를 닫을 때까지)
  setProcessState({
    step: "idle",  // ⚠️ 실제로는 idle이 아님! 여전히 processing 중
    agentType: null,
    message: ""
  })
  break

// Line 972-977: onClose 핸들러 (🔴 문제 발생)
onClose={() => {
  setShowLeaseContract(false)
  setLeaseContractData(null)
  // Progress 메시지 제거 ← 여기가 문제!
  setMessages((prev) => prev.filter(m => m.type !== "progress"))
}
```

**파일 2: `lease_contract_page.tsx`**

```typescript
// Line 49-52: handleApprove (🔴 문제 발생)
const handleApprove = () => {
  onApprove()   // interrupt_response 전송 (정상)
  onClose()     // 🔴 Progress 메시지 삭제하는 onClose 호출!
}

// Line 54-64: handleModify (동일한 문제)
const handleModify = () => {
  if (!showModifyInput) {
    setShowModifyInput(true)
    return
  }

  if (modifications.trim()) {
    onModify(modifications)
    onClose()  // 🔴 Progress 메시지 삭제
  }
}

// Line 66-69: handleReject (동일한 문제)
const handleReject = () => {
  onReject()
  onClose()  // 🔴 Progress 메시지 삭제
}
```

---

## 3. 근본 원인 분석

### 3.1 설계 오류

**잘못된 가정:**
- "승인" 버튼 클릭 = 작업 완료
- 팝업 닫기 = Progress 제거

**실제 상황:**
- "승인" 버튼 클릭 = 작업 재개 시작
- 팝업 닫기 후에도 7초간 작업 진행 (Aggregate → Generate → LLM)

### 3.2 타이밍 문제

```
┌──────────────────────────────────────────────────────────────┐
│ 시간축 (10:41:32 ~ 10:42:00)                                 │
└──────────────────────────────────────────────────────────────┘

10:41:32  ━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
          │ Progress 표시 (정상)      │
          │                           │
          │ plan → search → aggregate │
10:41:32  ━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
          ┃ Interrupt 발생
          ┃
10:41:32  ┏━━━━━━━━━━━━━━━━━━━━━━━━┓
          ┃ 팝업 표시               ┃
          ┃ (Progress 유지됨)       ┃
10:41:53  ┃                         ┃  ← 사용자가 21초 후 "승인" 클릭
          ┗━━━━━━━━━━━━━━━━━━━━━━━━┛
          │
10:41:53  ╳  팝업 닫힘 + Progress 삭제 (🔴 문제!)
          │
          ├─ Backend: generate_node 실행
          ├─ Backend: aggregate_results_node 실행
          ├─ Backend: generate_response_node 실행
          ├─ Backend: LLM 호출 시작
          │
          │  🕐 7초간 사용자는 아무것도 볼 수 없음!
          │
10:42:00  ├─ Backend: LLM 호출 완료
          ├─ Backend: Conversation 저장
          └─ final_response 전송

10:42:00  ━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
          │ 최종 답변 표시             │
          └────────────────────────────┘
```

### 3.3 Progress Callback 손실

**Backend에서 전송되는 Progress 메시지들 (무시됨):**

```
10:41:53 - supervisor_phase_change: finalizing (75%)
10:41:53 - supervisor_phase_change: finalizing (85%) - LLM start
10:41:53 - supervisor_phase_change: finalizing (87%) - content writing
10:42:00 - supervisor_phase_change: finalizing (90%) - validation
10:42:00 - supervisor_phase_change: finalizing (95%) - LLM complete
```

**Frontend 상태:**
- Progress 메시지가 이미 삭제되어 있어서 표시할 곳이 없음
- WebSocket 메시지는 수신되지만 처리되지 않음

---

## 4. 해결 방안

### 4.1 핵심 아이디어

**"승인" ≠ "작업 완료"**
- "승인" = 팝업만 닫기 + Progress 유지
- "작업 완료" = `final_response` 수신 시 Progress 제거

### 4.2 변경 사항 요약

| 컴포넌트 | 변경 전 | 변경 후 |
|---------|--------|--------|
| **LeaseContractPage** | `handleApprove()` → `onClose()` 호출 | `handleApprove()` → 팝업만 닫기 (Progress 유지) |
| **ChatInterface** | `onClose()` → Progress 삭제 | `onClose()` → 팝업만 닫기, Progress는 final_response 시 삭제 |
| **Progress Message** | Interrupt 후 삭제됨 | Interrupt 후에도 유지, 진행 상황 업데이트 |

### 4.3 UI/UX 흐름 개선

**변경 전:**
```
사용자 입력 → Progress 표시 → Interrupt 팝업 → [승인] → ❌ 7초 대기 (아무것도 안 보임) → 최종 답변
```

**변경 후:**
```
사용자 입력 → Progress 표시 → Interrupt 팝업 → [승인] → ✅ Progress 계속 표시 (75% → 85% → 95%) → 최종 답변
```

---

## 5. 구현 계획

### 5.1 Phase 1: LeaseContractPage 수정 ⭐ 우선순위 1

**파일**: `frontend/components/lease_contract/lease_contract_page.tsx`

**변경 사항:**

```typescript
// ❌ 변경 전
const handleApprove = () => {
  onApprove()
  onClose()  // Progress 삭제됨
}

const handleModify = () => {
  if (!showModifyInput) {
    setShowModifyInput(true)
    return
  }

  if (modifications.trim()) {
    onModify(modifications)
    onClose()  // Progress 삭제됨
  }
}

const handleReject = () => {
  onReject()
  onClose()  // Progress 삭제됨
}
```

```typescript
// ✅ 변경 후
const handleApprove = () => {
  onApprove()
  // 팝업만 닫기 (Progress는 유지)
  setShowLeaseContract(false)
  setLeaseContractData(null)
  // onClose()를 호출하지 않음!
}

const handleModify = () => {
  if (!showModifyInput) {
    setShowModifyInput(true)
    return
  }

  if (modifications.trim()) {
    onModify(modifications)
    // 팝업만 닫기 (Progress는 유지)
    setShowLeaseContract(false)
    setLeaseContractData(null)
  }
}

const handleReject = () => {
  onReject()
  // 팝업만 닫기 (Progress는 유지)
  setShowLeaseContract(false)
  setLeaseContractData(null)
}
```

**문제:** `setShowLeaseContract`는 ChatInterface의 state인데 LeaseContractPage에서 직접 접근 불가

**해결책 1 (권장):** Props에 `onClosePopup` 추가 (Progress 유지)

```typescript
// LeaseContractPageProps 수정
interface LeaseContractPageProps {
  interruptData?: {...}
  onApprove: () => void
  onModify: (modifications: string) => void
  onReject: () => void
  onClose: () => void  // 기존: X 버튼용 (Progress 삭제)
  onClosePopup: () => void  // 🆕 추가: 승인/거부 후 팝업만 닫기 (Progress 유지)
}

// 핸들러 수정
const handleApprove = () => {
  onApprove()
  onClosePopup()  // Progress 유지하면서 팝업만 닫기
}

const handleModify = () => {
  if (!showModifyInput) {
    setShowModifyInput(true)
    return
  }

  if (modifications.trim()) {
    onModify(modifications)
    onClosePopup()  // Progress 유지하면서 팝업만 닫기
  }
}

const handleReject = () => {
  onReject()
  onClosePopup()  // Progress 유지하면서 팝업만 닫기
}
```

**해결책 2 (간단):** `onClose` 동작 변경

```typescript
// LeaseContractPage는 그대로 두고
// ChatInterface의 onClose만 수정 (아래 Phase 2 참고)
```

### 5.2 Phase 2: ChatInterface 수정 ⭐ 우선순위 1

**파일**: `frontend/components/chat-interface.tsx`

**Option A: onClosePopup 추가 (권장)**

```typescript
// Line 938-979: LeaseContractPage 호출 부분 수정
{showLeaseContract && (
  <LeaseContractPage
    interruptData={leaseContractData?.interrupt_data}

    onApprove={() => {
      if (wsClientRef.current) {
        console.log('[ChatInterface] Sending approve response')
        wsClientRef.current.send({
          type: "interrupt_response",
          action: "approve",
          feedback: null
        })
      }
    }}

    onModify={(modifications: string) => {
      if (wsClientRef.current) {
        console.log('[ChatInterface] Sending modify response:', modifications)
        wsClientRef.current.send({
          type: "interrupt_response",
          action: "modify",
          feedback: modifications,
          modifications: modifications
        })
      }
    }}

    onReject={() => {
      if (wsClientRef.current) {
        console.log('[ChatInterface] Sending reject response')
        wsClientRef.current.send({
          type: "interrupt_response",
          action: "reject",
          feedback: null
        })
      }
    }}

    // 🆕 새로 추가: 승인/거부 후 팝업만 닫기 (Progress 유지)
    onClosePopup={() => {
      console.log('[ChatInterface] Closing popup only (keeping progress)')
      setShowLeaseContract(false)
      setLeaseContractData(null)
      // Progress는 삭제하지 않음!
    }}

    // 기존: X 버튼용 (Progress 삭제)
    onClose={() => {
      console.log('[ChatInterface] Force closing popup (removing progress)')
      setShowLeaseContract(false)
      setLeaseContractData(null)
      // X 버튼으로 닫을 때만 Progress 삭제
      setMessages((prev) => prev.filter(m => m.type !== "progress"))
    }}
  />
)}
```

**Option B: onClose 동작 변경 (간단)**

```typescript
// 🆕 새로운 onClose (Progress 유지)
onClose={() => {
  console.log('[ChatInterface] Closing popup (keeping progress)')
  setShowLeaseContract(false)
  setLeaseContractData(null)
  // Progress는 final_response 수신 시에만 삭제됨 (Line 325-327)
  // 여기서는 삭제하지 않음!
}}
```

**권장:** Option A (명확한 의도 구분)

### 5.3 Phase 3: Progress 업데이트 확인 ⭐ 우선순위 2

**파일**: `frontend/components/chat-interface.tsx`

**확인 사항:**

Interrupt 이후에도 `supervisor_phase_change` 메시지를 정상적으로 처리하는지 확인

```typescript
// Line 429-500: supervisor_phase_change 처리 (기존 코드 확인)
case 'supervisor_phase_change':
  const { supervisorPhase, supervisorProgress, message: phaseMessage } = message

  // 3-Layer Progress 업데이트
  setThreeLayerProgress(prev => {
    if (!prev) {
      return {
        supervisorPhase,
        supervisorProgress,
        activeAgents: []
      }
    }

    return {
      ...prev,
      supervisorPhase,
      supervisorProgress
    }
  })

  // Animated progress 업데이트
  setAnimatedSupervisorProgress(supervisorProgress)
  break
```

**✅ 이미 정상 작동 중** - 추가 수정 불필요

**단, 확인 필요:**
- Progress 메시지가 없으면 `supervisor_phase_change`가 무시되는지 확인
- 없다면 Progress 메시지가 없어도 threeLayerProgress를 생성하도록 수정

### 5.4 Phase 4: Progress 재생성 로직 추가 ⭐ 우선순위 3 (선택)

**목적:** Interrupt 재개 시 Progress 메시지가 없으면 자동 생성

**파일**: `frontend/components/chat-interface.tsx`

**추가 코드:**

```typescript
// handleWSMessage 내부에 추가
case 'supervisor_phase_change':
  const { supervisorPhase, supervisorProgress, message: phaseMessage } = message

  // 🆕 Progress 메시지가 없으면 자동 생성 (Interrupt 재개 대응)
  const hasProgressMessage = messages.some(m => m.type === "progress")
  if (!hasProgressMessage && supervisorPhase === "finalizing") {
    console.log('[ChatInterface] Recreating progress message after interrupt')

    const newProgressMessage: Message = {
      id: Date.now().toString(),
      type: "progress",
      content: "답변을 생성하고 있습니다...",
      timestamp: new Date(),
      progressData: {
        stage: "generating",  // Legacy stage
        responsePhase: "response_generation"
      }
    }

    setMessages(prev => [...prev, newProgressMessage])
  }

  // 기존 3-Layer Progress 업데이트
  setThreeLayerProgress(prev => {
    if (!prev) {
      return {
        supervisorPhase,
        supervisorProgress,
        activeAgents: []
      }
    }

    return {
      ...prev,
      supervisorPhase,
      supervisorProgress
    }
  })

  setAnimatedSupervisorProgress(supervisorProgress)
  break
```

---

## 6. 테스트 시나리오

### 6.1 시나리오 1: 정상 승인 플로우

**테스트 케이스:** "임대차 계약서 작성해줘"

**예상 동작:**

```
1. 사용자 입력
   ✅ Progress 표시 (dispatch → analyzing → executing)

2. Interrupt 발생
   ✅ 팝업 표시
   ✅ Progress는 유지됨

3. 사용자 "승인" 클릭
   ✅ 팝업 닫힘
   ✅ Progress 유지됨 ← 핵심!
   ✅ Progress 업데이트: finalizing (75% → 85% → 95%)

4. 최종 답변 수신
   ✅ Progress 제거
   ✅ 답변 표시
```

### 6.2 시나리오 2: X 버튼으로 강제 종료

**테스트 케이스:** "임대차 계약서 작성해줘" → Interrupt → X 버튼 클릭

**예상 동작:**

```
1. 사용자 입력
   ✅ Progress 표시

2. Interrupt 발생
   ✅ 팝업 표시

3. 사용자 X 버튼 클릭 (강제 종료)
   ✅ 팝업 닫힘
   ✅ Progress 제거됨 (Option A인 경우)
   ✅ Workflow는 Backend에서 계속 실행되지만 UI에서는 표시 안 함
```

### 6.3 시나리오 3: "수정" 요청

**테스트 케이스:** "임대차 계약서 작성해줘" → Interrupt → "수정" → 수정 사항 입력 → "수정 제출"

**예상 동작:**

```
1. 사용자 입력
   ✅ Progress 표시

2. Interrupt 발생
   ✅ 팝업 표시

3. 사용자 "수정" 버튼 클릭
   ✅ 수정 입력창 표시

4. 수정 사항 입력 후 "수정 제출"
   ✅ 팝업 닫힘
   ✅ Progress 유지됨 ← 핵심!
   ✅ Progress 업데이트: finalizing (75% → 85% → 95%)

5. 최종 답변 수신 (수정 반영됨)
   ✅ Progress 제거
   ✅ 답변 표시
```

### 6.4 시나리오 4: "거부"

**테스트 케이스:** "임대차 계약서 작성해줘" → Interrupt → "거부"

**예상 동작:**

```
1. 사용자 입력
   ✅ Progress 표시

2. Interrupt 발생
   ✅ 팝업 표시

3. 사용자 "거부" 버튼 클릭
   ✅ 팝업 닫힘
   ✅ Progress 유지됨 (Backend에서 처리)
   ✅ Backend에서 reject 처리 후 에러 응답 반환

4. 에러 응답 수신
   ✅ Progress 제거
   ✅ 에러 메시지 표시
```

---

## 7. 예상 결과

### 7.1 사용자 경험 개선

**변경 전:**
```
사용자: "임대차 계약서 작성해줘" 입력
  ↓ (5초)
팝업: "계약서 작성을 위해 승인이 필요합니다"
  ↓ [승인] 클릭
❌ 7초간 아무것도 보이지 않음 (답답함)
  ↓
최종 답변 표시 (갑자기 나타남)
```

**변경 후:**
```
사용자: "임대차 계약서 작성해줘" 입력
  ↓ (5초)
팝업: "계약서 작성을 위해 승인이 필요합니다"
  ↓ [승인] 클릭
✅ Progress 표시:
   "결과를 정리하고 있습니다" (75%)
   ↓ (0.1초)
   "최종 답변을 생성하고 있습니다" (85%)
   ↓ (0.1초)
   "답변 내용을 작성하고 있습니다" (87%)
   ↓ (6.8초 - LLM 작업)
   "답변을 검증하고 있습니다" (90%)
   ↓ (0.1초)
   "답변 생성 완료" (95%)
  ↓
최종 답변 표시 (자연스러운 전환)
```

### 7.2 타이밍 다이어그램 (개선 후)

```
┌──────────────────────────────────────────────────────────────┐
│ 시간축 (10:41:32 ~ 10:42:00)                                 │
└──────────────────────────────────────────────────────────────┘

10:41:32  ━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
          │ Progress 표시 (정상)      │
          │                           │
          │ plan → search → aggregate │
10:41:32  ━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
          ┃ Interrupt 발생
          ┃
10:41:32  ┏━━━━━━━━━━━━━━━━━━━━━━━━┓
          ┃ 팝업 표시               ┃
          ┃ (Progress 배경에 유지)  ┃
10:41:53  ┃                         ┃  ← 사용자가 21초 후 "승인" 클릭
          ┗━━━━━━━━━━━━━━━━━━━━━━━━┛
          │
10:41:53  ✅ 팝업 닫힘 (Progress 유지!)
          │
          ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
          ┃ Progress 계속 표시          ┃
          ┃                             ┃
          ┃ "결과를 정리하고 있습니다"   ┃ (75%)
10:41:53  ┃ "최종 답변을 생성..."        ┃ (85%)
          ┃ "답변 내용을 작성..."        ┃ (87%)
          ┃                             ┃
          ┃  🕐 LLM 작업 중 (7초)       ┃
          ┃  (사용자는 진행 상황 확인!)  ┃
          ┃                             ┃
10:42:00  ┃ "답변을 검증..."            ┃ (90%)
          ┃ "답변 생성 완료"            ┃ (95%)
          ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

10:42:00  ━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
          │ 최종 답변 표시             │
          └────────────────────────────┘
```

### 7.3 Progress 메시지 상세

Backend에서 전송되는 실제 Progress 메시지들이 모두 표시됨:

| 시간 | Event | Progress | 메시지 |
|-----|-------|---------|-------|
| 10:41:53.0s | supervisor_phase_change | 75% | "결과를 정리하고 있습니다" |
| 10:41:53.1s | supervisor_phase_change | 85% | "최종 답변을 생성하고 있습니다" |
| 10:41:53.2s | supervisor_phase_change | 87% | "답변 내용을 작성하고 있습니다" |
| 10:42:00.0s | supervisor_phase_change | 90% | "답변을 검증하고 있습니다" |
| 10:42:00.1s | supervisor_phase_change | 95% | "답변 생성 완료" |
| 10:42:00.2s | final_response | 100% | (답변 표시) |

---

## 8. 구현 우선순위

### Phase 1 (필수) ⭐⭐⭐

1. **LeaseContractPage 수정**
   - `handleApprove`, `handleModify`, `handleReject`에서 `onClosePopup` 호출
   - Props에 `onClosePopup` 추가

2. **ChatInterface 수정**
   - `onClosePopup` 핸들러 추가 (팝업만 닫기, Progress 유지)
   - `onClose` 핸들러는 X 버튼용으로 유지 (Progress 삭제)

### Phase 2 (권장) ⭐⭐

3. **Progress 업데이트 확인**
   - Interrupt 후 `supervisor_phase_change` 메시지 정상 처리 확인
   - threeLayerProgress 상태 업데이트 확인

### Phase 3 (선택) ⭐

4. **Progress 재생성 로직 추가**
   - Interrupt 재개 시 Progress 메시지 자동 생성
   - Edge case 처리

---

## 9. 리스크 및 대응 방안

### 9.1 리스크 1: X 버튼으로 닫을 때 Progress가 유지됨 (Option B)

**문제:**
- Option B를 선택하면 X 버튼으로 닫아도 Progress가 유지됨
- 사용자가 강제 종료했는데도 Progress가 계속 표시

**대응:**
- Option A 사용 (권장): `onClose`와 `onClosePopup` 분리

### 9.2 리스크 2: Progress 메시지가 삭제된 상태에서 재개

**문제:**
- 다른 로직에서 Progress 메시지가 삭제되었을 수 있음
- Interrupt 재개 시 업데이트할 대상이 없음

**대응:**
- Phase 4 구현: Progress 자동 재생성 로직 추가

### 9.3 리스크 3: Backend에서 Progress 메시지를 전송하지 않음

**문제:**
- Interrupt 재개 후 `supervisor_phase_change` 메시지가 전송되지 않을 수 있음

**대응:**
- Backend 로그 확인 (이미 전송됨 확인)
- 필요 시 Backend 수정 (progress_callback 호출 확인)

---

## 10. 테스트 체크리스트

### Frontend 테스트

- [ ] "임대차 계약서 작성해줘" 입력 시 Progress 표시
- [ ] Interrupt 발생 시 팝업 표시 + Progress 유지
- [ ] "승인" 클릭 시 팝업 닫힘 + Progress 유지
- [ ] "승인" 후 Progress 업데이트 (75% → 85% → 95%)
- [ ] final_response 수신 시 Progress 제거 + 답변 표시
- [ ] X 버튼 클릭 시 Progress 제거 (Option A)
- [ ] "수정" 클릭 시 동작 확인
- [ ] "거부" 클릭 시 동작 확인

### Backend 테스트

- [ ] Interrupt 재개 후 `supervisor_phase_change` 전송 확인
- [ ] progress_callback 정상 호출 확인
- [ ] final_response 전송 확인

### 통합 테스트

- [ ] 전체 플로우 end-to-end 테스트
- [ ] 타이밍 확인 (7초 동안 Progress 표시)
- [ ] WebSocket 메시지 순서 확인

---

## 11. 결론

### 11.1 문제 요약

Document Executor HITL 워크플로우에서 "승인" 후 Progress가 사라져서 사용자가 7초간 진행 상황을 볼 수 없었습니다.

### 11.2 해결 방안

1. **LeaseContractPage**: `onClosePopup` 사용 (Progress 유지)
2. **ChatInterface**: `onClosePopup` 핸들러 추가
3. **Progress 유지**: final_response 수신 시에만 제거

### 11.3 기대 효과

- ✅ 사용자 경험 대폭 개선 (7초 대기 시간 투명화)
- ✅ Progress 연속성 유지 (0% → 100% 자연스러운 흐름)
- ✅ Backend 작업 진행 상황 실시간 표시
- ✅ 사용자 신뢰도 향상

### 11.4 구현 난이도

- **난이도:** 하 (Low)
- **예상 소요 시간:** 1-2시간
- **리스크:** 낮음
- **영향 범위:** LeaseContractPage, ChatInterface (2개 파일)

---

**끝.**
