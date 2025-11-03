# 4-Stage Progress UI - 깔끔한 구현 계획서 (기존 방식 완전 제거)

**작성일**: 2025-10-23
**버전**: v3.0 (Clean)
**목표**: 기존 3개 페이지 방식 완전 제거 + 새로운 4-stage 시스템으로 완전 교체

---

## 🎯 핵심 원칙

**❌ 절대 하지 않을 것**:
- 기존 타입과 새로운 타입 혼용
- 기존 핸들러 로직 재사용
- 기존 렌더링 조건문 유지

**✅ 반드시 할 것**:
- 기존 코드 완전 삭제
- 새로운 코드만 작성
- 깔끔한 구조

---

## 📋 삭제할 기존 코드 목록

### 1. Message 타입에서 삭제
```typescript
// ❌ 완전 삭제
type: "execution-plan" | "execution-progress" | "response-generating"
executionPlan?: ExecutionPlan
executionSteps?: ExecutionStep[]
responseGenerating?: { message?: string; phase?: string }
```

### 2. Import에서 삭제
```typescript
// ❌ 완전 삭제
import { ExecutionPlanPage } from "@/components/execution-plan-page"
import { ExecutionProgressPage } from "@/components/execution-progress-page"
import { ResponseGeneratingPage } from "@/components/response-generating-page"
```

### 3. WebSocket 핸들러에서 삭제
```typescript
// ❌ 완전 삭제
case 'plan_ready': {
  // ExecutionPlanPage 업데이트 로직 전부
}

case 'execution_start': {
  // ExecutionProgressPage 생성 로직 전부
}

case 'response_generating_start':
case 'response_generating_progress': {
  // ResponseGeneratingPage 생성/업데이트 로직 전부
}
```

### 4. 렌더링에서 삭제
```tsx
{/* ❌ 완전 삭제 */}
{message.type === "execution-plan" && message.executionPlan && (
  <ExecutionPlanPage plan={message.executionPlan} />
)}
{message.type === "execution-progress" && message.executionSteps && message.executionPlan && (
  <ExecutionProgressPage steps={message.executionSteps} plan={message.executionPlan} />
)}
{message.type === "response-generating" && message.responseGenerating && (
  <ResponseGeneratingPage ... />
)}
```

### 5. handleSendMessage에서 삭제
```typescript
// ❌ 완전 삭제
const planMessage: Message = {
  type: "execution-plan",
  executionPlan: { ... }
}
```

---

## ✅ 새로 추가할 깔끔한 코드

### 1. 새로운 Message 타입 (깔끔)
```typescript
interface Message {
  id: string
  type: "user" | "bot" | "progress" | "guidance"  // ← 4개만
  content: string
  timestamp: Date

  // Progress 전용 (하나의 객체로 통합)
  progressData?: {
    stage: "dispatch" | "analysis" | "executing" | "generating"
    plan?: ExecutionPlan
    steps?: ExecutionStep[]
    responsePhase?: "aggregation" | "response_generation"
  }

  // 기타
  structuredData?: { ... }
  guidanceData?: { ... }
}
```

### 2. 새로운 Import (깔끔)
```typescript
import { ProgressContainer } from "@/components/progress-container"
// 기존 3개 Import 완전 제거
```

### 3. 새로운 WebSocket 핸들러 (깔끔)

#### 3-1. analysis_start (신규)
```typescript
case 'analysis_start':
  // Stage 1 → 2 전환
  setMessages(prev =>
    prev.map(m =>
      m.type === "progress" && m.progressData?.stage === "dispatch"
        ? { ...m, progressData: { ...m.progressData, stage: "analysis" } }
        : m
    )
  )
  break
```

#### 3-2. plan_ready (완전 새로 작성)
```typescript
case 'plan_ready':
  if (message.execution_steps?.length > 0) {
    // ✅ plan 데이터만 추가 (stage는 "analysis" 유지)
    setMessages(prev =>
      prev.map(m =>
        m.type === "progress" && m.progressData?.stage === "analysis"
          ? {
              ...m,
              progressData: {
                ...m.progressData,
                plan: {
                  intent: message.intent,
                  confidence: message.confidence || 0,
                  execution_steps: message.execution_steps,
                  execution_strategy: message.execution_strategy || "sequential",
                  estimated_total_time: message.estimated_total_time || 5,
                  keywords: message.keywords,
                  isLoading: false
                }
              }
            }
          : m
      )
    )
  } else {
    // IRRELEVANT/UNCLEAR: progress 제거
    setMessages(prev => prev.filter(m => m.type !== "progress"))
  }
  break
```

#### 3-3. execution_start (완전 새로 작성)
```typescript
case 'execution_start':
  if (message.execution_steps) {
    // ✅ Stage 2 → 3 전환 + steps 추가
    setMessages(prev =>
      prev.map(m =>
        m.type === "progress"
          ? {
              ...m,
              progressData: {
                stage: "executing",
                plan: {
                  intent: message.intent,
                  confidence: message.confidence,
                  execution_steps: message.execution_steps,
                  execution_strategy: message.execution_strategy,
                  estimated_total_time: message.estimated_total_time,
                  keywords: message.keywords,
                  isLoading: false
                },
                steps: message.execution_steps.map(step => ({
                  ...step,
                  status: step.status || "pending"
                }))
              }
            }
          : m
      )
    )
  }
  break
```

#### 3-4. todo_updated (완전 새로 작성)
```typescript
case 'todo_updated':
  if (message.execution_steps) {
    // ✅ steps만 업데이트
    setMessages(prev =>
      prev.map(m =>
        m.type === "progress" && m.progressData?.stage === "executing"
          ? {
              ...m,
              progressData: {
                ...m.progressData,
                steps: message.execution_steps
              }
            }
          : m
      )
    )
  }
  break
```

#### 3-5. response_generating_start (완전 새로 작성)
```typescript
case 'response_generating_start':
  // ✅ Stage 3 → 4 전환
  setMessages(prev =>
    prev.map(m =>
      m.type === "progress"
        ? {
            ...m,
            progressData: {
              ...m.progressData,
              stage: "generating",
              responsePhase: message.phase || "aggregation"
            }
          }
        : m
    )
  )
  break
```

#### 3-6. response_generating_progress (완전 새로 작성)
```typescript
case 'response_generating_progress':
  // ✅ responsePhase만 업데이트
  setMessages(prev =>
    prev.map(m =>
      m.type === "progress" && m.progressData?.stage === "generating"
        ? {
            ...m,
            progressData: {
              ...m.progressData,
              responsePhase: message.phase || "response_generation"
            }
          }
        : m
    )
  )
  break
```

#### 3-7. final_response (완전 새로 작성)
```typescript
case 'final_response':
  // ✅ progress 제거 (기존 3개 타입 참조 완전 제거)
  setMessages(prev => prev.filter(m => m.type !== "progress"))

  // 봇 메시지 추가 로직은 기존과 동일
  break
```

### 4. 새로운 handleSendMessage (깔끔)
```typescript
const handleSendMessage = async (content: string) => {
  const activeSessionId = currentSessionId || sessionId
  if (!content.trim() || !activeSessionId || !wsClientRef.current) return

  const userMessage: Message = {
    id: Date.now().toString(),
    type: "user",
    content,
    timestamp: new Date()
  }

  // ✅ Stage 1: Dispatch 즉시 표시
  const progressMessage: Message = {
    id: `progress-${Date.now()}`,
    type: "progress",
    content: "",
    timestamp: new Date(),
    progressData: {
      stage: "dispatch",
      plan: {
        intent: "분석 중...",
        confidence: 0,
        execution_steps: [],
        execution_strategy: "sequential",
        estimated_total_time: 0,
        keywords: [],
        isLoading: true
      }
    }
  }

  setMessages(prev => [...prev, userMessage, progressMessage])
  setInputValue("")

  // WebSocket 전송
  wsClientRef.current.send({
    type: "query",
    query: content,
    enable_checkpointing: true
  })
}
```

### 5. 새로운 렌더링 (깔끔)
```tsx
{messages.map((message) => (
  <div key={message.id} className="space-y-2">
    {/* ✅ progress만 처리 */}
    {message.type === "progress" && message.progressData && (
      <ProgressContainer
        stage={message.progressData.stage}
        plan={message.progressData.plan}
        steps={message.progressData.steps}
        responsePhase={message.progressData.responsePhase}
      />
    )}

    {/* guidance는 기존과 동일 */}
    {message.type === "guidance" && message.guidanceData && (
      <GuidancePage guidance={message.guidanceData} />
    )}

    {/* user/bot 메시지는 기존과 동일 */}
    {(message.type === "user" || message.type === "bot") && (
      <div className={...}>...</div>
    )}
  </div>
))}
```

---

## 🔧 Backend 변경사항

### team_supervisor.py

**Line 209 (Intent 분석 직전) - analysis_start 신호 추가**:
```python
# WebSocket: 분석 시작 알림 (Stage 2: Analysis)
if progress_callback:
    try:
        await progress_callback("analysis_start", {
            "message": "질문을 분석하고 있습니다...",
            "stage": "analysis"
        })
        logger.debug("[TeamSupervisor] Sent analysis_start via WebSocket")
    except Exception as e:
        logger.error(f"[TeamSupervisor] Failed to send analysis_start: {e}")

# Intent 분석 (context 전달)
intent_result = await self.planning_agent.analyze_intent(query, context)
```

---

## 📦 구현 단계 (깔끔한 순서)

### Phase 1: 파일 준비
1. ✅ 기존 3개 파일 `_old/` 백업
2. ✅ `progress-container.tsx` 생성

### Phase 2: chat-interface.tsx 수정 (순서 중요!)

**Step 1**: Import 교체
```typescript
// ❌ 삭제
- import { ExecutionPlanPage } from "@/components/execution-plan-page"
- import { ExecutionProgressPage } from "@/components/execution-progress-page"
- import { ResponseGeneratingPage } from "@/components/response-generating-page"

// ✅ 추가
+ import { ProgressContainer, type ProgressStage } from "@/components/progress-container"
```

**Step 2**: Message 타입 교체
```typescript
// ❌ 삭제
- type: "execution-plan" | "execution-progress" | "response-generating"
- executionPlan?: ExecutionPlan
- executionSteps?: ExecutionStep[]
- responseGenerating?: { ... }

// ✅ 추가
+ type: "progress"
+ progressData?: { stage, plan, steps, responsePhase }
```

**Step 3**: WebSocket 핸들러 교체
- ❌ 기존 `plan_ready`, `execution_start`, `response_generating_start/progress` 핸들러 **완전 삭제**
- ✅ 새로운 핸들러 **완전히 새로 작성**

**Step 4**: handleSendMessage 교체
- ❌ `ExecutionPlanPage` 생성 로직 **완전 삭제**
- ✅ `ProgressContainer` 생성 로직 **새로 작성**

**Step 5**: 렌더링 교체
- ❌ 3개 조건문 **완전 삭제**
- ✅ 1개 조건문 **새로 작성**

### Phase 3: Backend 수정
1. ✅ `team_supervisor.py` Line 209에 `analysis_start` 신호 추가

### Phase 4: 빌드 테스트
1. ✅ `npm run build` 성공 확인
2. ✅ TypeScript 에러 없음 확인

---

## 🎨 ProgressContainer 구조 (참고)

```tsx
export function ProgressContainer({ stage, plan, steps, responsePhase }) {
  return (
    <Card>
      {/* 상단: 4개 스피너 */}
      <div className="flex justify-center gap-8">
        {["dispatch", "analysis", "executing", "generating"].map((s, idx) => (
          <div key={s}>
            <img
              src={SPINNERS[s]}
              className={`
                transition-all duration-150
                ${stage === s ? 'w-[100px] opacity-100' : 'w-[60px] opacity-40 grayscale'}
              `}
            />
            <div>{TITLES[s]}</div>
          </div>
        ))}
      </div>

      {/* 하단: Stage별 콘텐츠 */}
      <div>
        {stage === "dispatch" && <DispatchContent />}
        {stage === "analysis" && <AnalysisContent plan={plan} />}
        {stage === "executing" && <ExecutingContent steps={steps} />}
        {stage === "generating" && <GeneratingContent phase={responsePhase} />}
      </div>
    </Card>
  )
}
```

---

## ✅ 검증 체크리스트

구현 후 확인:

**1. 기존 코드 완전 제거 확인**:
- [ ] `execution-plan` 타입 검색 → 0건
- [ ] `execution-progress` 타입 검색 → 0건
- [ ] `response-generating` 타입 검색 → 0건
- [ ] `ExecutionPlanPage` import 검색 → 0건
- [ ] `ExecutionProgressPage` import 검색 → 0건
- [ ] `ResponseGeneratingPage` import 검색 → 0건

**2. 새로운 코드만 존재 확인**:
- [ ] `type: "progress"` 만 존재
- [ ] `progressData` 필드만 존재
- [ ] `ProgressContainer` 컴포넌트만 사용

**3. 동작 확인**:
- [ ] Stage 1 → 2 → 3 → 4 순차 전환
- [ ] 스피너 애니메이션 (크기/색상 변경)
- [ ] Stage별 콘텐츠 표시

---

## 🔍 사용자 확인 필요 사항

**이 계획서가 명확한가요?**

1. **기존 코드 완전 삭제**: 혼용 없이 깔끔하게 제거 → OK?
2. **새로운 코드만 작성**: 기존 로직 재사용 없음 → OK?
3. **구현 순서**: Phase 1 → 2 → 3 → 4 → OK?

---

**확인해주시면 바로 구현 시작하겠습니다!**

이번엔 기존 코드와 완전히 분리해서 깔끔하게 구현하겠습니다.
