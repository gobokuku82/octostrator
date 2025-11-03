# 4단계 Progress 타이밍 분석 (수정)

**작성일**: 2025-10-22
**목적**: 프론트엔드 표시 타이밍과 백엔드 신호 타이밍 정확히 매칭

---

## 🔍 현재 타이밍 (3단계)

### 프론트엔드 표시

```
질문 입력 (Send 버튼 클릭)
  ↓ [즉시 0ms] - Line 466-483
┌─────────────────────────┐
│ 1. ExecutionPlanPage    │ ← 프론트엔드에서 즉시 생성 (isLoading: true)
│    "분석 중..."         │
└─────────────────────────┘
  ↓ [백엔드 처리 중...]
  ↓ plan_ready 신호 받음
┌─────────────────────────┐
│ 1. ExecutionPlanPage    │ ← isLoading: false로 업데이트
│    실제 계획 표시       │
└─────────────────────────┘
  ↓ execution_start 신호
┌─────────────────────────┐
│ 2. ExecutionProgressPage│ ← ExecutionPlanPage 제거, Progress 생성
│    실행 중...           │
└─────────────────────────┘
  ↓ response_generating_start 신호
┌─────────────────────────┐
│ 3. ResponseGeneratingPage│ ← ExecutionProgressPage 제거
│    답변 작성 중...      │
└─────────────────────────┘
```

---

## 🎯 목표 타이밍 (4단계)

### 단계 구분

1. **출동 중** (Dispatch) - 질문 입력 즉시 표시
2. **분석 중** (Analysis) - Intent 분석 중
3. **실행 중** (Executing) - Agent 팀 실행
4. **답변 작성 중** (Generating) - 최종 응답 생성

---

## 📊 타이밍 매칭

### 방법 A: 백엔드 신호 추가 (✅ 추천)

```
┌──────────────────┐          ┌──────────────────┐
│   프론트엔드     │          │    백엔드        │
└──────────────────┘          └──────────────────┘

질문 입력
  ↓ [0ms]
[즉시 표시]
┌─────────────────────┐
│ 1. 출동 중          │ ← 프론트엔드에서 즉시 생성
│    stage: "dispatch"│
└─────────────────────┘
  ↓ [Send WebSocket]
                              쿼리 수신
                              planning_node 시작
                                ↓ [50-100ms]
                              dispatch_start 신호 전송 (🆕)
                                ↓
  ↓ dispatch_start 수신
[업데이트]
┌─────────────────────┐
│ 1. 출동 중          │ ← 신호 받아서 확인만
│    stage: "dispatch"│   (이미 표시중이므로 변화 없음)
└─────────────────────┘
                              Intent 분석 시작
                                ↓ [500-2000ms]
                              analysis_start 신호 전송 (🆕)
                                ↓
  ↓ analysis_start 수신
[전환]
┌─────────────────────┐
│ 2. 분석 중          │ ← stage: "analysis"로 전환
│    질문 분석 중...  │
└─────────────────────┘
                              계획 생성 완료
                                ↓ [200-500ms]
                              plan_ready 신호 전송
                                ↓
  ↓ plan_ready 수신
[업데이트]
┌─────────────────────┐
│ 2. 분석 중          │ ← 실행 계획 데이터 표시
│    계획: [...]      │   (stage는 그대로 "analysis")
└─────────────────────┘
                              execution_start 신호 전송
                                ↓
  ↓ execution_start 수신
[전환]
┌─────────────────────┐
│ 3. 실행 중          │ ← stage: "executing"
│    Agent 실행...    │
└─────────────────────┘
                              Agent 실행
                                ↓ [3000-10000ms]
                              response_generating_start
                                ↓
  ↓ response_generating_start 수신
[전환]
┌─────────────────────┐
│ 4. 답변 작성 중     │ ← stage: "generating"
│    최종 답변...     │
└─────────────────────┘
```

---

## 🔧 구현 방안

### 옵션 1: 신호 추가 + stage 필드 (추천)

**백엔드 수정**:
```python
# team_supervisor.py planning_node

async def planning_node(self, state):
    # ❌ dispatch_start는 불필요 (프론트에서 이미 표시중)
    # 하지만 보내도 무방 (확인용)

    # 🆕 Intent 분석 시작 전
    await progress_callback("analysis_start", {
        "message": "질문을 분석하고 있습니다...",
        "stage": "analysis"
    })

    # Intent 분석 (시간 소요)
    intent_result = await self.planning_agent.analyze_intent(query)

    # 계획 생성
    execution_plan = await self.planning_agent.create_execution_plan(intent_result)

    # plan_ready (분석 완료)
    await progress_callback("plan_ready", {
        "intent": intent_result.intent_type.value,
        "execution_steps": planning_state["execution_steps"],
        "stage": "analysis"  # 🆕 stage 추가
        # ...
    })
```

**프론트엔드 수정**:
```typescript
// chat-interface.tsx handleSendMessage

const handleSendMessage = async (content: string) => {
  // ...

  // 🆕 1단계: 출동 중 (즉시 표시)
  const dispatchMessage: Message = {
    id: `progress-${Date.now()}`,
    type: "progress",  // 🆕 통합 타입
    content: "",
    timestamp: new Date(),
    progressData: {
      stage: "dispatch",
      title: "AI 에이전트 출동 중",
      message: "질문을 접수했습니다...",
      steps: [
        { id: "1", status: "active", label: "출동" },
        { id: "2", status: "pending", label: "분석" },
        { id: "3", status: "pending", label: "실행" },
        { id: "4", status: "pending", label: "작성" }
      ],
      agents: []
    }
  }

  setMessages((prev) => [...prev, userMessage, dispatchMessage])

  // WebSocket 전송
  wsClientRef.current.send({ type: "query", query: content })
}
```

```typescript
// handleWSMessage

case 'analysis_start':
  // 🆕 2단계: 분석 중으로 전환
  setMessages((prev) =>
    prev.map(m =>
      m.type === "progress"
        ? {
            ...m,
            progressData: {
              ...m.progressData,
              stage: "analysis",
              title: "질문 분석 중",
              message: message.message || "질문을 분석하고 있습니다...",
              steps: [
                { id: "1", status: "completed", label: "출동" },
                { id: "2", status: "active", label: "분석" },
                { id: "3", status: "pending", label: "실행" },
                { id: "4", status: "pending", label: "작성" }
              ]
            }
          }
        : m
    )
  )
  break

case 'plan_ready':
  // 🆕 분석 완료 - 계획 데이터만 업데이트 (stage는 그대로)
  setMessages((prev) =>
    prev.map(m =>
      m.type === "progress" && m.progressData.stage === "analysis"
        ? {
            ...m,
            progressData: {
              ...m.progressData,
              message: "실행 계획 수립 완료",
              planData: {  // 🆕 계획 데이터 추가
                intent: message.intent,
                confidence: message.confidence,
                execution_steps: message.execution_steps
              }
            }
          }
        : m
    )
  )
  break

case 'execution_start':
  // 🆕 3단계: 실행 중으로 전환
  setMessages((prev) =>
    prev.map(m =>
      m.type === "progress"
        ? {
            ...m,
            progressData: {
              ...m.progressData,
              stage: "executing",
              title: "작업 실행 중",
              message: "AI 에이전트가 작업을 수행하고 있습니다...",
              steps: [
                { id: "1", status: "completed", label: "출동" },
                { id: "2", status: "completed", label: "분석" },
                { id: "3", status: "active", label: "실행" },
                { id: "4", status: "pending", label: "작성" }
              ],
              agents: message.execution_steps.map(step => ({
                id: step.step_id,
                name: step.description,
                type: step.team,
                status: "waiting"
              }))
            }
          }
        : m
    )
  )
  break

case 'response_generating_start':
  // 🆕 4단계: 답변 작성 중으로 전환
  setMessages((prev) =>
    prev.map(m =>
      m.type === "progress"
        ? {
            ...m,
            progressData: {
              ...m.progressData,
              stage: "generating",
              title: "AI 답변 작성 중",
              message: "최종 답변을 생성하고 있습니다...",
              steps: [
                { id: "1", status: "completed", label: "출동" },
                { id: "2", status: "completed", label: "분석" },
                { id: "3", status: "completed", label: "실행" },
                { id: "4", status: "active", label: "작성" }
              ],
              agents: [
                { id: "agg", name: "정보 정리", type: "analysis", status: "completed" },
                { id: "gen", name: "답변 생성", type: "document", status: "running" }
              ]
            }
          }
        : m
    )
  )
  break
```

---

### 옵션 2: 신호 없이 프론트에서 타이머 (비추천)

```typescript
// chat-interface.tsx

const handleSendMessage = async (content: string) => {
  // 1단계: 출동 중 (즉시)
  const dispatchMessage = createProgressMessage("dispatch")
  setMessages((prev) => [...prev, userMessage, dispatchMessage])

  // 2단계: 분석 중 (0.6초 후)
  setTimeout(() => {
    setMessages((prev) =>
      prev.map(m =>
        m.type === "progress" && m.progressData.stage === "dispatch"
          ? updateStage(m, "analysis")
          : m
      )
    )
  }, 600)

  // WebSocket 전송
  wsClientRef.current.send({ type: "query", query: content })
}
```

**문제점**:
- ❌ 백엔드가 0.6초보다 빠르게 `plan_ready`를 보내면? → 분석 단계를 못 봄
- ❌ 백엔드가 2초 걸리면? → 출동 중에서 1.4초 멈춤
- ❌ 유지보수 어려움

---

## ✅ 최종 추천

### 방법: **백엔드 신호 1개 추가 + 프론트 즉시 표시**

**백엔드**:
```python
# analysis_start 신호만 추가 (1개)
await progress_callback("analysis_start", {
    "message": "질문을 분석하고 있습니다...",
    "stage": "analysis"
})
```

**프론트엔드**:
```typescript
// 1. 질문 입력 즉시 "출동 중" 표시
handleSendMessage() {
  const msg = createProgressMessage("dispatch")
  setMessages([...prev, msg])
}

// 2. analysis_start 받으면 "분석 중"으로 전환
case 'analysis_start':
  updateProgressStage("analysis")

// 3. execution_start 받으면 "실행 중"으로 전환
case 'execution_start':
  updateProgressStage("executing")

// 4. response_generating_start 받으면 "작성 중"으로 전환
case 'response_generating_start':
  updateProgressStage("generating")
```

---

## 📊 타이밍 요약

| 단계 | 트리거 | 소요 시간 | 누적 |
|------|--------|----------|------|
| 1. 출동 중 | 프론트엔드 즉시 | 0ms | 0ms |
| 2. 분석 중 | `analysis_start` | 500-2000ms | 0.5-2s |
| 3. 실행 중 | `execution_start` | 3000-10000ms | 3.5-12s |
| 4. 작성 중 | `response_generating_start` | 2000-5000ms | 5.5-17s |

**장점**:
- ✅ 1단계는 즉시 표시 (사용자 피드백)
- ✅ 2-4단계는 백엔드 신호로 정확한 타이밍
- ✅ 백엔드 수정 최소화 (신호 1개만 추가)

---

## 🔄 기존 코드 영향

### 기존 3개 페이지 → 1개 통합 컨테이너

**Before**:
- ExecutionPlanPage (출동 + 분석 혼재)
- ExecutionProgressPage (실행)
- ResponseGeneratingPage (작성)

**After**:
- ProgressContainer (4단계 통합)
  - stage: "dispatch" | "analysis" | "executing" | "generating"

---

## 📝 구현 순서

1. **백엔드**: `analysis_start` 신호 1개 추가
2. **프론트**: 통합 ProgressContainer 구현
3. **프론트**: stage별 렌더링 로직
4. **프론트**: 신호 핸들러 수정

**예상 시간**: 60분

---

## 🎯 결론

**추천**: 백엔드 신호 1개 추가 (`analysis_start`)

**이유**:
1. ✅ 1단계는 이미 프론트에서 즉시 표시중
2. ✅ 2단계 진입 타이밍만 백엔드 신호 필요
3. ✅ 3-4단계는 기존 신호 활용
4. ✅ 최소한의 백엔드 수정

---

**승인 여부**: 이 방식으로 진행할까요?
