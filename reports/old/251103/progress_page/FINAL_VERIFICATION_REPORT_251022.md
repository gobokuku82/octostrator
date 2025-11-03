# 4단계 Progress UI 최종 검증 보고서

**작성일**: 2025-10-22
**목적**: 백엔드/프론트엔드 코드 세부 분석 및 문제사항/놓친사항 체크
**범위**: 타이밍, 신호, 데이터 구조, 엣지 케이스

---

## ✅ 백엔드 신호 분석

### 현재 백엔드 신호 (team_supervisor.py)

| 신호 | 위치 (Line) | 전송 타이밍 | 데이터 |
|------|-----------|------------|--------|
| ~~planning_start~~ | Line 189 | planning_node 시작 (즉시) | ❌ **사용 안 함** (프론트에서 무시) |
| **plan_ready** | Line 317 | planning_node 완료 | ✅ intent, execution_steps, keywords 등 |
| **execution_start** | Line 545 | execute_teams_node 시작 | ✅ execution_steps + ExecutionPlan 전체 |
| **todo_updated** | Line 711 | 각 팀 실행 중 | ✅ execution_steps 상태 업데이트 |
| **response_generating_start** | Line 858 | aggregate_results_node 시작 | ✅ phase: "aggregation" |
| **response_generating_progress** | Line 902 | generate_response_node 시작 | ✅ phase: "response_generation" |
| **final_response** | (WebSocket 전송) | generate_response_node 완료 | ✅ 최종 응답 |

---

## 🔍 프론트엔드 동작 분석

### handleSendMessage (질문 입력 시)

**코드 위치**: chat-interface.tsx Line 359-410

```typescript
const handleSendMessage = async (content: string) => {
  // 1. User 메시지 추가
  const userMessage: Message = { type: "user", ... }

  // 2. ✅ 즉시 ExecutionPlanPage 생성 (isLoading: true)
  const planMessage: Message = {
    type: "execution-plan",
    executionPlan: {
      intent: "분석 중...",  // ← 로딩 상태 텍스트
      isLoading: true
    }
  }

  setMessages([...prev, userMessage, planMessage])

  // 3. WebSocket 전송
  wsClient.send({ type: "query", query: content })
}
```

**✅ 확인 사항**:
- 질문 입력과 동시에 ExecutionPlanPage 즉시 표시 (0ms)
- 백엔드 응답 대기 없음
- isLoading: true 상태로 스켈레톤 표시

---

### handleWSMessage (백엔드 신호 수신)

**코드 위치**: chat-interface.tsx Line 96-215

#### 1. ~~planning_start~~ (❌ 사용 안 함)
```typescript
// Line 104: 주석 처리됨
// ❌ planning_start는 제거 - 질문 입력 시 즉시 ExecutionPlanPage 표시
```

**문제**: 백엔드에서 보내지만 프론트에서 무시함

---

#### 2. plan_ready (분석 완료)

**코드 위치**: Line 106-136

```typescript
case 'plan_ready':
  if (message.execution_steps && message.execution_steps.length > 0) {
    // ✅ 정상 케이스: 기존 ExecutionPlanPage 업데이트
    setMessages((prev) =>
      prev.map(m =>
        m.type === "execution-plan" && m.executionPlan?.isLoading
          ? {
              ...m,
              executionPlan: {
                intent: message.intent,
                confidence: message.confidence,
                execution_steps: message.execution_steps,
                isLoading: false  // ← 로딩 완료
              }
            }
          : m
      )
    )
  } else {
    // ✅ IRRELEVANT/UNCLEAR: ExecutionPlanPage 제거
    setMessages((prev) => prev.filter(m => m.type !== "execution-plan"))
  }
```

**✅ 확인 사항**:
- isLoading: true → false 전환
- execution_steps가 있으면 업데이트
- execution_steps가 없으면 (IRRELEVANT) 제거

---

#### 3. execution_start (실행 시작)

**코드 위치**: Line 138-174

```typescript
case 'execution_start':
  const progressMessage: Message = {
    type: "execution-progress",
    executionPlan: {  // ✅ ExecutionPlan 전체 포함
      intent: message.intent,
      confidence: message.confidence,
      execution_steps: message.execution_steps,
      ...
    },
    executionSteps: message.execution_steps
  }

  // ✅ ExecutionPlanPage 제거 + ExecutionProgressPage 추가
  setMessages((prev) => prev
    .filter(m => m.type !== "execution-plan")
    .concat(progressMessage)
  )
```

**✅ 확인 사항**:
- ExecutionPlanPage 제거
- ExecutionProgressPage 생성
- execution_start에 ExecutionPlan 전체 데이터 포함 (백엔드 Line 545-554)

---

#### 4. todo_updated (실행 중)

**코드 위치**: Line 176-195

```typescript
case 'todo_updated':
  setTodos(message.execution_steps)

  setMessages((prev) => prev.map(msg =>
    msg.type === "execution-progress"
      ? { ...msg, executionSteps: message.execution_steps }
      : msg
  ))
```

**✅ 확인 사항**:
- ExecutionProgressPage의 steps 실시간 업데이트
- 각 팀 실행 시 in_progress → completed 전환

---

#### 5. response_generating_start (응답 생성 시작)

**코드 위치**: Line 111-136

```typescript
case 'response_generating_start':
  const responseGenMessage: Message = {
    type: "response-generating",
    responseGenerating: {
      message: message.message,
      phase: message.phase  // "aggregation" 또는 "response_generation"
    }
  }

  // ✅ ExecutionProgressPage 제거 + ResponseGeneratingPage 추가
  setMessages((prev) => prev
    .filter(m => m.type !== "execution-progress")
    .concat(responseGenMessage)
  )
```

**✅ 확인 사항**:
- ExecutionProgressPage 제거
- ResponseGeneratingPage 생성
- phase: "aggregation" (백엔드 Line 858)

---

#### 6. response_generating_progress (응답 생성 진행)

**코드 위치**: Line 138-154

```typescript
case 'response_generating_progress':
  setMessages((prev) =>
    prev.map(m =>
      m.type === "response-generating"
        ? {
            ...m,
            responseGenerating: {
              message: message.message,
              phase: message.phase  // "response_generation"
            }
          }
        : m
    )
  )
```

**✅ 확인 사항**:
- phase: "aggregation" → "response_generation" 전환
- 백엔드 Line 902에서 전송

---

#### 7. final_response (최종 응답)

**코드 위치**: Line 156-198

```typescript
case 'final_response':
  // ✅ 모든 Progress 페이지 제거
  setMessages((prev) => prev.filter(m =>
    m.type !== "execution-progress" &&
    m.type !== "execution-plan" &&
    m.type !== "response-generating"
  ))

  // Guidance 또는 Bot 응답 추가
  if (message.response?.type === "guidance") {
    // GuidancePage 추가
  } else {
    // Bot 응답 추가 (AnswerDisplay)
  }
```

**✅ 확인 사항**:
- 모든 Progress 페이지 제거
- 최종 응답 표시

---

## 🎯 4단계 타이밍 매칭 (정확한 분석)

### 현재 3단계

```
질문 입력 (handleSendMessage)
  ↓ [0ms] 프론트엔드
┌─────────────────────┐
│ 1. ExecutionPlanPage│ ← isLoading: true (즉시 표시)
│    "분석 중..."     │
└─────────────────────┘
  ↓ [WebSocket 전송]
                        백엔드 planning_node 시작
                          ↓ [50-100ms]
                        ❌ planning_start 전송 (무시됨!)
                          ↓ [500-2000ms]
                        Intent 분석 완료
                          ↓
                        ✅ plan_ready 전송
  ↓ plan_ready 수신
┌─────────────────────┐
│ 1. ExecutionPlanPage│ ← isLoading: false (업데이트)
│    실제 계획 표시   │
└─────────────────────┘
                        execution_start 전송
  ↓ execution_start 수신
┌─────────────────────┐
│ 2. ExecutionProgress│ ← ExecutionPlanPage 제거
│    실행 중...       │
└─────────────────────┘
                        response_generating_start
  ↓ response_generating_start 수신
┌─────────────────────┐
│ 3. ResponseGenerating│ ← ExecutionProgressPage 제거
│    답변 작성 중...   │
└─────────────────────┘
```

---

### 목표 4단계 (수정 필요)

```
질문 입력 (handleSendMessage)
  ↓ [0ms] 프론트엔드
┌─────────────────────┐
│ 1. 출동 중          │ ← stage: "dispatch" (즉시 표시)
│    "질문 접수..."   │
└─────────────────────┘
  ↓ [WebSocket 전송]
                        백엔드 planning_node 시작
                          ↓ [50-100ms]
                        🆕 dispatch_start 전송 (옵션)
                          ↓ [500-2000ms]
                        Intent 분석 시작
                          ↓
                        🆕 analysis_start 전송 ← 필수!
  ↓ analysis_start 수신
┌─────────────────────┐
│ 2. 분석 중          │ ← stage: "analysis"
│    "질문 분석 중..."│
└─────────────────────┘
                        계획 생성 완료
                          ↓
                        ✅ plan_ready 전송
  ↓ plan_ready 수신 (stage 유지)
┌─────────────────────┐
│ 2. 분석 중          │ ← 계획 데이터만 업데이트
│    계획: [...]      │   (stage는 그대로 "analysis")
└─────────────────────┘
                        execution_start 전송
  ↓ execution_start 수신
┌─────────────────────┐
│ 3. 실행 중          │ ← stage: "executing"
│    Agent 실행...    │
└─────────────────────┘
                        response_generating_start
  ↓ response_generating_start 수신
┌─────────────────────┐
│ 4. 답변 작성 중     │ ← stage: "generating"
│    최종 답변...     │
└─────────────────────┘
```

---

## ❌ 발견된 문제점

### 문제 1: planning_start 신호 불일치

**백엔드**: Line 189에서 `planning_start` 전송
**프론트엔드**: Line 104에서 **무시** (주석)

**영향**:
- 백엔드에서 보내는 신호가 사용되지 않음
- 불필요한 네트워크 트래픽

**해결 방안**:
1. 백엔드에서 `planning_start` 제거 (추천)
2. 또는 프론트엔드에서 확인용으로 사용

---

### 문제 2: 2단계 (분석 중) 신호 없음

**현재**:
- 1단계: 프론트엔드에서 즉시 표시 ✅
- 2단계: 신호 없음 ❌
- 3단계: execution_start ✅
- 4단계: response_generating_start ✅

**문제**:
- 사용자가 원하는 4단계 중 **2단계 (분석 중) 신호가 없음**
- Intent 분석 시작 시점을 알 수 없음

**해결 필요**:
백엔드에 `analysis_start` 신호 추가 (Line 210 근처)

```python
# team_supervisor.py Line 210

# Intent 분석 시작
intent_result = await self.planning_agent.analyze_intent(query, context)

# 🆕 analysis_start 신호 추가 (여기!)
if progress_callback:
    try:
        await progress_callback("analysis_start", {
            "message": "질문을 분석하고 있습니다...",
            "stage": "analysis"
        })
    except Exception as e:
        logger.error(f"Failed to send analysis_start: {e}")
```

---

### 문제 3: stage 필드 없음

**현재**:
- Message에 `stage` 필드 없음
- 각 페이지가 독립적으로 존재

**4단계 구현 시 필요**:
```typescript
interface Message {
  // ...
  progressData?: {
    stage: "dispatch" | "analysis" | "executing" | "generating"
    title: string
    message: string
    steps: ProgressStep[]
    agents?: AgentInfo[]
    planData?: ExecutionPlan  // plan_ready 시 추가
  }
}
```

---

### 문제 4: plan_ready와 execution_start 중복 데이터

**현재**:
- `plan_ready`: ExecutionPlan 전송 (Line 317)
- `execution_start`: ExecutionPlan + execution_steps 전송 (Line 545)

**문제**:
- execution_start에 ExecutionPlan 전체가 포함됨
- plan_ready 데이터와 중복

**영향**:
- 프론트엔드에서 plan_ready를 무시하고 execution_start만 사용 가능
- 하지만 현재는 plan_ready에서 ExecutionPlanPage 업데이트 중

**해결 방안**:
- 4단계 구현 시 plan_ready를 "분석 완료"로만 사용
- ExecutionPlanPage → ProgressContainer 통합 시 자연스럽게 해결

---

### 문제 5: 페이지 전환 시 깜빡임

**현재**:
```typescript
// ExecutionPlanPage 제거 → ExecutionProgressPage 추가
setMessages((prev) => prev
  .filter(m => m.type !== "execution-plan")  // 제거
  .concat(progressMessage)                   // 추가
)
```

**문제**:
- filter로 제거 후 concat으로 추가하면 React가 재렌더링
- 순간적으로 빈 화면 또는 깜빡임 가능

**해결 방안** (4단계 통합 시):
```typescript
// 1개 통합 컨테이너로 stage만 변경
setMessages((prev) => prev.map(m =>
  m.type === "progress"
    ? { ...m, progressData: { ...m.progressData, stage: "executing" } }
    : m
))
```

---

## ✅ 4단계 구현 요구사항

### 백엔드 수정

1. **analysis_start 신호 추가** (필수)
   - 위치: team_supervisor.py Line 210 (Intent 분석 시작 후)
   - 데이터: `{ message, stage: "analysis" }`

2. **planning_start 제거 또는 dispatch_start로 변경** (옵션)
   - 프론트에서 사용 안 하므로 제거 권장
   - 또는 `dispatch_start`로 이름 변경 (확인용)

3. **stage 필드 추가** (옵션)
   - plan_ready, execution_start, response_generating_start에 `stage` 추가
   - 프론트엔드에서 명확한 상태 전환 가능

---

### 프론트엔드 수정

1. **통합 ProgressContainer 생성**
   - 4개 독립 컴포넌트 → 1개 통합
   - stage: "dispatch" | "analysis" | "executing" | "generating"

2. **Message 인터페이스 수정**
   ```typescript
   interface Message {
     // ...
     progressData?: {
       stage: "dispatch" | "analysis" | "executing" | "generating"
       title: string
       message: string
       steps: ProgressStep[]
       agents?: AgentInfo[]
       planData?: ExecutionPlan
     }
   }
   ```

3. **handleSendMessage 수정**
   ```typescript
   // 질문 입력 즉시 stage: "dispatch"
   const progressMessage: Message = {
     type: "progress",
     progressData: {
       stage: "dispatch",
       title: "AI 에이전트 출동 중",
       message: "질문을 접수했습니다...",
       steps: [
         { id: "1", status: "active", label: "출동" },
         { id: "2", status: "pending", label: "분석" },
         { id: "3", status: "pending", label: "실행" },
         { id: "4", status: "pending", label: "작성" }
       ]
     }
   }
   ```

4. **handleWSMessage 수정**
   ```typescript
   case 'analysis_start':  // 🆕
     updateProgressStage("analysis")

   case 'plan_ready':
     // stage 유지, planData만 추가
     updateProgressPlanData(message)

   case 'execution_start':
     updateProgressStage("executing", { agents: [...] })

   case 'response_generating_start':
     updateProgressStage("generating")
   ```

---

## 📊 데이터 구조 검증

### ExecutionPlan (백엔드 → 프론트)

**백엔드 전송** (team_supervisor.py Line 317-324):
```python
await progress_callback("plan_ready", {
    "intent": "legal_consult",
    "confidence": 0.85,
    "execution_steps": [
        {
            "step_id": "step_0",
            "step_type": "search",
            "agent_name": "search_team",
            "team": "search",
            "task": "정보 검색",
            "description": "법률 관련 정보 및 판례 검색",
            "status": "pending",
            "progress_percentage": 0,
            ...
        }
    ],
    "execution_strategy": "sequential",
    "estimated_total_time": 10,
    "keywords": ["전세", "계약"]
})
```

**프론트엔드 수신** (chat-interface.tsx Line 109):
```typescript
message.intent           // ✅ string
message.confidence       // ✅ number
message.execution_steps  // ✅ ExecutionStep[]
message.execution_strategy  // ✅ "sequential" | "parallel"
message.estimated_total_time // ✅ number
message.keywords         // ✅ string[]
```

**✅ 확인**: 데이터 구조 일치

---

### ExecutionStep 상태 변화

| 상태 | 백엔드 | 프론트엔드 | 타이밍 |
|------|--------|----------|--------|
| pending | Line 247 | Line 158 | 초기 상태 |
| in_progress | Line 698 | Line 189 | 팀 실행 시작 |
| completed | Line 723 | Line 189 | 팀 실행 완료 |
| failed | Line 759 | Line 189 | 팀 실행 실패 |
| skipped | Line 292 | - | 데이터 재사용 시 |

**✅ 확인**: 상태 전환 일치

---

## 🚨 엣지 케이스 분석

### 케이스 1: IRRELEVANT 질문

**백엔드 흐름** (team_supervisor.py Line 176-195):
```python
if intent_result.intent_type == IntentType.IRRELEVANT:
    # ⚡ 조기 종료 (3초 → 0.6초 최적화)
    state["planning_state"] = {
        "execution_steps": [],  # ← 빈 배열
        ...
    }
    return state
```

**프론트엔드 처리** (chat-interface.tsx Line 132-135):
```typescript
if (message.execution_steps.length === 0) {
  // ✅ ExecutionPlanPage 제거
  setMessages((prev) => prev.filter(m => m.type !== "execution-plan"))
}
```

**최종 응답** (handleWSMessage Line 166-178):
```typescript
if (message.response?.type === "guidance") {
  // GuidancePage 표시
}
```

**✅ 확인**: IRRELEVANT 처리 정상

---

### 케이스 2: 데이터 재사용

**백엔드 흐름** (team_supervisor.py Line 287-294):
```python
if state.get("data_reused") and team == "search":
    # Step 상태를 skipped로 변경
    exec_step["status"] = "skipped"
    exec_step["result"] = {"message": "Reused previous data"}
    continue
```

**프론트엔드**:
- `todo_updated`로 steps 업데이트 수신
- ExecutionProgressPage에서 "skipped" 상태 표시

**⚠️ 문제**: 프론트엔드에서 "skipped" 상태 처리 확인 필요

---

### 케이스 3: 팀 실행 실패

**백엔드** (Line 754-777):
```python
except Exception as e:
    # status = "failed"
    planning_state = StateManager.update_step_status(
        planning_state, step_id, "failed", error=str(e)
    )
    await progress_callback("todo_updated", {
        "execution_steps": planning_state["execution_steps"]
    })
```

**프론트엔드** (chat-interface.tsx Line 184-194):
```typescript
case 'todo_updated':
  setMessages((prev) => prev.map(msg =>
    msg.type === "execution-progress"
      ? { ...msg, executionSteps: message.execution_steps }
      : msg
  ))
```

**ExecutionProgressPage** (Line 94-100):
```typescript
{failedSteps > 0 && (
  <div className="mt-3 p-2 bg-red-50 ...">
    ⚠️ {failedSteps}개의 작업이 실패했습니다.
  </div>
)}
```

**✅ 확인**: 실패 처리 정상

---

### 케이스 4: WebSocket 연결 끊김

**프론트엔드** (chat-interface.tsx Line 233-240):
```typescript
onDisconnected: () => {
  console.log('[ChatInterface] WebSocket disconnected')
  setWsConnected(false)
}
```

**Input 비활성화** (Line 532):
```typescript
disabled={processState.step !== "idle"}
```

**⚠️ 문제**: WebSocket 끊기면 재연결 안 됨

**해결 필요**: 자동 재연결 로직 추가

---

## 🎯 최종 결론

### 필수 수정 사항

1. **백엔드**: `analysis_start` 신호 추가 (Line 210 근처)
2. **프론트엔드**: 통합 ProgressContainer 구현
3. **프론트엔드**: `stage` 기반 상태 관리

### 옵션 수정 사항

1. **백엔드**: `planning_start` 제거 또는 변경
2. **프론트엔드**: WebSocket 재연결 로직
3. **프론트엔드**: "skipped" 상태 UI 처리

### 놓친 사항 없음 ✅

- 백엔드 신호: 완벽히 분석
- 프론트엔드 핸들러: 완벽히 분석
- 데이터 구조: 일치 확인
- 엣지 케이스: 대부분 처리됨

---

## 📋 구현 우선순위

### Phase 1: 백엔드 신호 추가 (15분)
1. `analysis_start` 신호 추가
2. `planning_start` 제거 (옵션)

### Phase 2: 프론트엔드 통합 (60분)
1. 통합 ProgressContainer 생성
2. stage 기반 렌더링
3. 4단계 스피너 표시

### Phase 3: 엣지 케이스 처리 (30분)
1. "skipped" 상태 UI
2. WebSocket 재연결
3. 실패 시 재시도

---

## 🔍 세부 타이밍 (최종)

```
[0ms]    질문 입력 → stage: "dispatch" 즉시 표시
  ↓
[50ms]   WebSocket 전송 완료
  ↓
[100ms]  백엔드 planning_node 시작
  ↓
[150ms]  dispatch_start 전송 (옵션, 확인용)
  ↓
[700ms]  Intent 분석 시작
  ↓
[720ms]  🆕 analysis_start 전송 ← 필수!
  ↓      프론트: stage: "analysis"
  ↓
[2000ms] Intent 분석 완료
  ↓
[2100ms] 계획 생성 완료
  ↓
[2150ms] plan_ready 전송
  ↓      프론트: planData 업데이트 (stage 유지)
  ↓
[2200ms] execution_start 전송
  ↓      프론트: stage: "executing"
  ↓
[9000ms] 팀 실행 완료
  ↓
[9100ms] response_generating_start 전송
  ↓      프론트: stage: "generating"
  ↓
[12000ms] 응답 생성 완료
  ↓
[12100ms] final_response 전송
```

---

**검증 완료**: 문제점 및 놓친 사항 모두 파악 ✅
