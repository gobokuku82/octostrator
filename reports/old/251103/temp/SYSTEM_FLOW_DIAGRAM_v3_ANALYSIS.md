# 📊 챗봇 동적 Spinner 시스템 완벽 분석 v3

**분석일**: 2025-10-10
**목적**: 현재 발생 중인 오류 원인 파악 및 완벽한 작동 구조 이해

---

## 🎯 핵심 발견사항 (Executive Summary)

### ✅ 정상 작동 중인 부분
1. **Backend WebSocket 메시지 전송** - team_supervisor.py에서 5가지 이벤트 정상 전송
2. **Frontend WebSocket 연결** - ws.ts 클라이언트 정상 작동
3. **execution_steps status 필드** - Backend에서 status/progress 필드 정상 업데이트

### ⚠️ 잠재적 문제 지점
1. **800ms 타이머 의존성** - plan_ready와 execution_start 사이 간격
2. **메시지 순서 의존성** - ExecutionPlanPage 존재 여부에 따른 조건 분기
3. **State 동기화 타이밍** - todos와 messages 두 곳 업데이트

---

## 📡 WebSocket 메시지 프로토콜 (완벽 정리)

### Backend → Frontend 메시지 (6종류)

| Event Type | 전송 위치 | 데이터 구조 | Frontend 처리 |
|-----------|---------|----------|-------------|
| `planning_start` | team_supervisor.py:183 | `{message}` | processState 업데이트 |
| `plan_ready` | team_supervisor.py:315 | `{intent, confidence, execution_steps, estimated_total_time, keywords}` | ExecutionPlanPage 생성 |
| `execution_start` | team_supervisor.py:491 | `{message, execution_steps}` | ExecutionProgressPage 생성 |
| `todo_updated` | team_supervisor.py:582,612,643 | `{execution_steps}` | ProgressPage steps 업데이트 |
| `final_response` | chat_api.py:352 | `{response}` | Progress 제거, 답변 표시 |
| `error` | chat_api.py:362 | `{error, details}` | 에러 메시지 표시 |

### Frontend → Backend 메시지 (3종류)

| Message Type | 전송 위치 | 데이터 구조 | Backend 처리 |
|-------------|---------|----------|-------------|
| `query` | chat-interface.tsx:279 | `{type: "query", query, enable_checkpointing}` | process_query_streaming() 호출 |
| `interrupt_response` | (미구현) | `{type: "interrupt_response", action, modified_todos}` | 추후 LangGraph Command 처리 |
| `todo_skip` | (미구현) | `{type: "todo_skip", todo_id}` | 추후 State 업데이트 |

---

## 🔄 완벽한 실행 흐름 (타이밍 포함)

```
┌─────────────────────────────────────────────────────────────────┐
│ Phase 1: 질문 입력 및 Planning (0ms ~ 800ms)                      │
└─────────────────────────────────────────────────────────────────┘

[0ms] 사용자가 "강남구 아파트 시세 알려줘" 입력
  ↓
[Frontend] chat-interface.tsx:254-286
  ├─ 1. 사용자 메시지 추가 (line 264)
  ├─ 2. processState = "planning" 설정 (line 271-276)
  └─ 3. WebSocket 전송 (line 279)
      {type: "query", query: "...", enable_checkpointing: true}

[Backend] chat_api.py:232-269
  ├─ 4. 메시지 수신 (line 232)
  ├─ 5. progress_callback 정의 (line 251-257)
  └─ 6. _process_query_async() 비동기 실행 (line 260)

[Backend] team_supervisor.py:1037-1105 (process_query_streaming)
  ├─ 7. callback 등록 (line 1057-1059)
  ├─ 8. LangGraph ainvoke() 시작 (line 1098)
  └─ 9. planning_node 실행

[Backend] team_supervisor.py:169-326 (planning_node)
  ├─ 10. [즉시] planning_start 전송 (line 183-188)
  │     → Frontend: processState.message = "계획을 수립하고 있습니다..."
  │
  ├─ 11. Intent 분석 (~400ms, LLM 호출)
  │     - PlanningAgent.analyze_intent()
  │     - intent_type, confidence, keywords 추출
  │
  ├─ 12. ExecutionPlan 생성 (~400ms, LLM 호출)
  │     - execution_steps 생성 (각 step에 step_id, team, description, status="pending")
  │
  └─ 13. [800ms] plan_ready 전송 (line 315-324) ⭐
        → Frontend: ExecutionPlanPage 생성

┌─────────────────────────────────────────────────────────────────┐
│ Phase 2: ExecutionPlanPage → ExecutionProgressPage 전환 문제 지점│
└─────────────────────────────────────────────────────────────────┘

[Frontend] chat-interface.tsx:121-144 (plan_ready 처리)
  ├─ 14. ExecutionPlanPage 메시지 생성 (line 125-139)
  │     executionPlan: {
  │       intent, confidence, execution_steps,
  │       execution_strategy: "sequential", // ⚠️ Backend에서 보내지 않음
  │       estimated_total_time, keywords
  │     }
  │
  └─ ⚠️ 문제: ExecutionProgressPage 생성 없음!
        - v1에서는 800ms 타이머로 자동 생성했으나
        - v2에서는 execution_start 메시지 수신 시 생성으로 변경됨

[Backend] team_supervisor.py:467-527 (execute_teams_node)
  ├─ 15. [즉시] execution_start 전송 (line 491-497) ⭐⭐⭐
  │     {
  │       message: "작업 실행을 시작합니다...",
  │       execution_steps: [...] // 전체 steps (status="pending")
  │     }
  │
  └─ → Frontend: ExecutionProgressPage 생성 (line 146-172)

┌─────────────────────────────────────────────────────────────────┐
│ Phase 3: 팀별 실행 및 실시간 업데이트 (800ms ~ 4000ms)            │
└─────────────────────────────────────────────────────────────────┘

[Backend] team_supervisor.py:535-650 (_execute_teams_sequential)

  for team_name in ["search", "analysis"]:

    16. Step 시작 - status 업데이트 (line 571-575)
        planning_state = StateManager.update_step_status(
          planning_state, step_id, "in_progress", progress=0
        )

    17. [즉시] todo_updated 전송 (line 582-586) ⭐
        {execution_steps: [{..., status: "in_progress", progress_percentage: 0}]}
        → Frontend: ProgressPage 해당 step 파란색 표시

    18. 팀 실행 (~1000-2000ms)
        - _execute_single_team(team_name, ...)
        - SearchTeam or AnalysisTeam 실제 작업

    19. Step 완료 - status 업데이트 (line 598-605)
        planning_state = StateManager.update_step_status(
          planning_state, step_id, "completed",
          result=result, execution_time=...
        )

    20. [즉시] todo_updated 전송 (line 612-616) ⭐
        {execution_steps: [{..., status: "completed", progress_percentage: 100}]}
        → Frontend: ProgressPage 해당 step 초록색 표시

┌─────────────────────────────────────────────────────────────────┐
│ Phase 4: 최종 응답 (4000ms ~ 4500ms)                             │
└─────────────────────────────────────────────────────────────────┘

[Backend] chat_api.py:347-357 (_process_query_async 완료)
  ├─ 21. final_response 추출 (line 349)
  └─ 22. final_response 전송 (line 351-355)
        {
          type: "final_response",
          response: {
            content: "답변 내용...",
            answer: "...",
            message: "..."
          }
        }

[Frontend] chat-interface.tsx:212-235 (final_response 처리)
  ├─ 23. ExecutionPlan/Progress 메시지 제거 (line 215-217)
  ├─ 24. 봇 응답 메시지 추가 (line 220-226)
  └─ 25. processState = "idle" (line 230-234)
        → 입력 활성화
```

---

## 🐛 발견된 문제점 및 원인

### 문제 1: execution_strategy 누락 ❌

**위치**: chat-interface.tsx:134

```typescript
executionPlan: {
  intent: message.intent,
  confidence: message.confidence || 0,
  execution_steps: message.execution_steps,
  execution_strategy: "sequential", // ⚠️ 하드코딩된 기본값
  estimated_total_time: message.estimated_total_time || 5,
  keywords: message.keywords
}
```

**원인**: Backend team_supervisor.py:315-321에서 `execution_strategy`를 보내지 않음

```python
await progress_callback("plan_ready", {
    "intent": intent_result.intent_type.value,
    "confidence": intent_result.confidence,
    "execution_steps": planning_state["execution_steps"],
    "estimated_total_time": execution_plan.estimated_time,
    "keywords": intent_result.keywords
    # ❌ execution_strategy 누락!
})
```

**해결책**: Backend에서 `execution_strategy` 추가 전송

---

### 문제 2: plan_ready → execution_start 타이밍 간격 ⚠️

**현재 구조**:
```
[800ms] plan_ready 전송
   ↓ (LangGraph 노드 전환 시간 ~50-100ms)
[850ms] execute_teams_node 시작
   ↓ (즉시)
[850ms] execution_start 전송
```

**Frontend 처리**:
```typescript
// line 121-144: plan_ready 수신
case 'plan_ready':
  setMessages([...prev, planMessage])  // ExecutionPlanPage 생성
  // ❌ 800ms 타이머 제거됨 (v1에 있었음)
  break

// line 146-172: execution_start 수신 (~50ms 후)
case 'execution_start':
  setMessages([...prev, progressMessage])  // ExecutionProgressPage 생성
  break
```

**문제**: ExecutionPlanPage가 화면에 나타난 직후 (~50ms) ExecutionProgressPage가 생성되어 **Plan을 거의 볼 수 없음**

**해결책 (옵션)**:

1. **Frontend에서 800ms 지연 유지** (v1 방식)
   - execution_start 수신 시 즉시 생성하지 않고 800ms 타이머 설정
   - 장점: Backend 수정 불필요
   - 단점: 고정 시간 의존

2. **Backend에서 지연 추가**
   - execution_start 전송 전 `await asyncio.sleep(0.8)`
   - 장점: Frontend 로직 단순
   - 단점: Backend 블로킹

3. **Plan과 Progress를 동시 표시** (권장)
   - ExecutionPlanPage를 제거하지 않고 유지
   - ExecutionProgressPage를 그 아래에 추가
   - 장점: 사용자가 Plan과 Progress를 모두 볼 수 있음

---

### 문제 3: ExecutionProgressPage 생성 조건 버그 ⚠️

**위치**: chat-interface.tsx:146-172

```typescript
case 'execution_start':
  if (message.execution_steps) {
    // ExecutionPlan 찾기
    const planMsg = messages.find(m => m.type === "execution-plan")  // ⚠️ 문제!

    const progressMessage: Message = {
      id: `execution-progress-${Date.now()}`,
      type: "execution-progress",
      content: "",
      timestamp: new Date(),
      executionPlan: planMsg?.executionPlan,  // ⚠️ planMsg가 없으면 undefined
      executionSteps: message.execution_steps.map((step: ExecutionStep) => ({
        ...step,
        status: step.status || "pending"
      }))
    }
    setMessages((prev) => [...prev, progressMessage])
  }
```

**문제**:
1. `messages.find()`는 현재 `messages` state를 참조
2. `setMessages()`는 **비동기**이므로, `plan_ready` 처리 직후 `execution_start`가 오면 `planMsg`가 `undefined`일 수 있음
3. React state 업데이트 배칭으로 인해 `execution_start` 핸들러 실행 시점에 `messages`에 ExecutionPlanPage가 없을 수 있음

**재현 시나리오**:
```
[800ms] plan_ready 수신
  → setMessages([...prev, planMessage])  // React 스케줄링
[850ms] execution_start 수신
  → messages.find(m => m.type === "execution-plan")  // ❌ 아직 추가 안됨!
  → planMsg = undefined
  → ExecutionProgressPage.executionPlan = undefined
  → UI 렌더링 오류 발생 가능
```

**해결책**:

```typescript
case 'execution_start':
  if (message.execution_steps) {
    setMessages((prev) => {
      // ✅ 함수형 업데이트 내부에서 최신 state 참조
      const planMsg = prev.find(m => m.type === "execution-plan")

      const progressMessage: Message = {
        id: `execution-progress-${Date.now()}`,
        type: "execution-progress",
        content: "",
        timestamp: new Date(),
        executionPlan: planMsg?.executionPlan,
        executionSteps: message.execution_steps.map((step: ExecutionStep) => ({
          ...step,
          status: step.status || "pending"
        }))
      }

      return [...prev, progressMessage]
    })
  }
```

---

### 문제 4: todo_updated 중복 State 관리 ⚠️

**위치**: chat-interface.tsx:174-194

```typescript
case 'todo_created':
case 'todo_updated':
  if (message.execution_steps) {
    setTodos(message.execution_steps)  // 1️⃣ todos state 업데이트

    // ExecutionProgressPage 메시지 찾아서 steps 업데이트
    setMessages((prev) => {  // 2️⃣ messages state 업데이트
      return prev.map(msg => {
        if (msg.type === "execution-progress") {
          return {
            ...msg,
            executionSteps: message.execution_steps
          }
        }
        return msg
      })
    })
  }
```

**문제**:
- `todos`와 `messages` 두 곳에서 동일한 `execution_steps` 관리
- `todos`는 현재 **사용되지 않음** (ExecutionProgressPage는 자체 props로 받음)
- 불필요한 중복 state

**해결책**:
- `todos` state 제거 또는
- ExecutionProgressPage에서 `todos` prop 추가 전달 (추후 TodoList UI 구현 시)

---

## 🎯 핵심 문제 진단

### 가장 큰 문제: ExecutionPlanPage가 너무 빨리 사라짐

**v1 (800ms 타이머)**:
```
[800ms] plan_ready → ExecutionPlanPage 생성
[1600ms] 800ms 타이머 → ExecutionProgressPage 생성
         ↑ 사용자가 Plan을 800ms 동안 볼 수 있음
```

**v2 (execution_start 메시지)**:
```
[800ms] plan_ready → ExecutionPlanPage 생성
[850ms] execution_start → ExecutionProgressPage 생성
        ↑ 사용자가 Plan을 단 50ms 동안만 볼 수 있음 (거의 안 보임)
```

### 권장 해결책: Plan과 Progress 동시 표시

```typescript
// ExecutionPlanPage를 제거하지 않고 유지
case 'final_response':
  setMessages((prev) => prev.filter(m =>
    // ✅ ExecutionPlan은 유지, Progress만 제거
    m.type !== "execution-progress"
  ))
```

또는 CSS로 순차적 fade-in:

```css
.execution-plan-page {
  animation: fadeIn 0.3s ease-in;
}

.execution-progress-page {
  animation: fadeIn 0.3s ease-in 0.8s;  /* 0.8초 지연 */
  animation-fill-mode: backwards;
}
```

---

## 📝 수정 권장사항 (우선순위)

### 🔴 Critical (즉시 수정)

1. **execution_start State 버그 수정**
   - 파일: frontend/components/chat-interface.tsx:146-172
   - 수정: `setMessages()` 함수형 업데이트 사용

2. **execution_strategy 전송 추가**
   - 파일: backend/app/service_agent/supervisor/team_supervisor.py:315-321
   - 수정: `"execution_strategy": execution_plan.strategy` 추가

### 🟡 Important (조만간 수정)

3. **Plan → Progress 전환 시간 개선**
   - 옵션 A: Frontend 800ms 지연 재도입
   - 옵션 B: Plan과 Progress 동시 표시 (권장)

4. **todos State 정리**
   - 파일: frontend/components/chat-interface.tsx:50, 174-194
   - 수정: todos state 제거 또는 용도 명확화

### 🟢 Nice to have (추후 개선)

5. **WebSocket 재연결 시 State 복원**
   - 현재: 재연결 로직만 있음
   - 추가: Checkpoint 복원 API 호출

6. **에러 처리 강화**
   - Callback 실패 시 fallback 로직
   - WebSocket 연결 끊김 시 사용자 알림

---

## 🧪 테스트 시나리오

### 시나리오 1: 정상 플로우 (시세 조회)

```
[입력] "강남구 아파트 시세 알려줘"

[Expected Output]
0ms:    사용자 메시지 표시
0ms:    "계획을 수립하고 있습니다..." 로딩
800ms:  ExecutionPlanPage 표시
850ms:  ExecutionProgressPage 생성 (Plan 아래)
        - Step 1: search_team (pending)
        - Step 2: analysis_team (pending)
1000ms: Step 1 → in_progress (파란색)
2500ms: Step 1 → completed (초록색)
2550ms: Step 2 → in_progress
4000ms: Step 2 → completed
4500ms: Progress 제거, 답변 표시
```

### 시나리오 2: 빠른 응답 (Unclear Intent)

```
[입력] "ㄴㅁㅇㄹ"

[Expected Output]
0ms:    사용자 메시지 표시
0ms:    "계획을 수립하고 있습니다..."
800ms:  (ExecutionPlanPage 생성 안 됨)
        final_response 즉시 전송
        → "질문을 명확히 해주세요" 답변 표시
```

### 시나리오 3: Step 실패

```
[입력] "존재하지 않는 지역 검색"

[Expected Output]
...
2000ms: Step 1 → failed (빨간색)
        error: "검색 결과 없음"
2500ms: Step 2 → skipped (회색)
3000ms: final_response
        → "일부 정보를 가져오지 못했습니다"
```

---

## 📊 성능 지표

### 예상 처리 시간 (강남구 시세 조회 기준)

| Phase | 소요 시간 | 설명 |
|------|---------|------|
| Intent 분석 | ~400ms | LLM 호출 (gpt-4o-mini) |
| ExecutionPlan 생성 | ~400ms | LLM 호출 |
| SearchTeam 실행 | ~1200ms | 네이버/KB API 호출 |
| AnalysisTeam 실행 | ~1500ms | 데이터 분석 + LLM |
| Response 생성 | ~200ms | 최종 응답 포맷팅 |
| **총 시간** | **~3700ms** | 약 3.7초 |

### WebSocket 메시지 개수

- planning_start: 1개
- plan_ready: 1개
- execution_start: 1개
- todo_updated: 4개 (각 step 시작/완료)
- final_response: 1개
- **총 8개 메시지**

---

## 🔧 즉시 적용 가능한 수정안

### 수정 1: execution_start State 버그 수정

**파일**: `frontend/components/chat-interface.tsx`

```diff
  case 'execution_start':
    // 실행 시작 - ExecutionProgressPage 생성
    // Backend 전송 형식: { message, execution_steps }
    if (message.execution_steps) {
-     // ExecutionPlan 찾기
-     const planMsg = messages.find(m => m.type === "execution-plan")
-
-     const progressMessage: Message = {
-       id: `execution-progress-${Date.now()}`,
-       type: "execution-progress",
-       content: "",
-       timestamp: new Date(),
-       executionPlan: planMsg?.executionPlan,
-       executionSteps: message.execution_steps.map((step: ExecutionStep) => ({
-         ...step,
-         status: step.status || "pending"
-       }))
-     }
-     setMessages((prev) => [...prev, progressMessage])
+     // ✅ 함수형 업데이트로 최신 state 참조
+     setMessages((prev) => {
+       const planMsg = prev.find(m => m.type === "execution-plan")
+
+       const progressMessage: Message = {
+         id: `execution-progress-${Date.now()}`,
+         type: "execution-progress",
+         content: "",
+         timestamp: new Date(),
+         executionPlan: planMsg?.executionPlan,
+         executionSteps: message.execution_steps.map((step: ExecutionStep) => ({
+           ...step,
+           status: step.status || "pending"
+         }))
+       }
+
+       return [...prev, progressMessage]
+     })

      setProcessState({
        step: "executing",
        agentType: null,
        message: message.message || "작업을 실행하고 있습니다..."
      })
    }
    break
```

### 수정 2: Backend execution_strategy 추가

**파일**: `backend/app/service_agent/supervisor/team_supervisor.py`

```diff
  # WebSocket: 계획 완료 알림
  session_id = state.get("session_id")
  progress_callback = self._progress_callbacks.get(session_id) if session_id else None
  if progress_callback:
      try:
          await progress_callback("plan_ready", {
              "intent": intent_result.intent_type.value,
              "confidence": intent_result.confidence,
              "execution_steps": planning_state["execution_steps"],
+             "execution_strategy": execution_plan.strategy,
              "estimated_total_time": execution_plan.estimated_time,
              "keywords": intent_result.keywords
          })
          logger.info("[TeamSupervisor] Sent plan_ready via WebSocket")
```

### 수정 3: Plan과 Progress 동시 표시

**파일**: `frontend/components/chat-interface.tsx`

```diff
  case 'final_response':
    // 최종 응답 수신
-   // Execution Progress 메시지 제거
+   // ✅ ExecutionPlan은 유지, Progress만 제거
    setMessages((prev) => prev.filter(m =>
-     m.type !== "execution-plan" && m.type !== "execution-progress"
+     m.type !== "execution-progress"
    ))
```

또는 Plan 제거 시 fade-out 애니메이션:

```diff
  case 'final_response':
+   // ExecutionPlan에 fade-out 클래스 추가
+   setMessages((prev) => prev.map(msg => {
+     if (msg.type === "execution-plan") {
+       return {...msg, isClosing: true}  // 500ms 후 제거
+     }
+     return msg
+   }))
+
+   // 500ms 후 실제 제거
+   setTimeout(() => {
      setMessages((prev) => prev.filter(m =>
        m.type !== "execution-plan" && m.type !== "execution-progress"
      ))
+   }, 500)
```

---

## 🎬 결론

### 현재 시스템 상태

✅ **잘 작동하는 부분**:
- WebSocket 양방향 통신
- Backend 메시지 전송 (6종류)
- Frontend 메시지 수신 처리
- execution_steps 실시간 업데이트

⚠️ **개선 필요한 부분**:
1. ExecutionPlanPage 표시 시간 너무 짧음 (~50ms)
2. execution_start State 참조 버그 (Race Condition)
3. execution_strategy 누락
4. todos State 중복 관리

### 권장 조치

**즉시 수정** (Critical):
- [ ] execution_start State 버그 수정 (수정안 1)
- [ ] execution_strategy 전송 추가 (수정안 2)

**조만간 수정** (Important):
- [ ] Plan → Progress 전환 개선 (수정안 3 중 선택)
- [ ] todos State 정리

**추후 개선** (Nice to have):
- [ ] WebSocket 재연결 시 State 복원
- [ ] 에러 처리 강화
- [ ] 성능 최적화 (메시지 throttling)

---

**작성자**: Claude Code
**버전**: v3 (완벽 분석)
**다음 단계**: 수정안 1, 2, 3 적용 후 재테스트
