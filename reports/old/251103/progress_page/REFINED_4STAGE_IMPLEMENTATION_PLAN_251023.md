# 4-Stage Unified Progress UI - 보완된 구현 계획서

**작성일**: 2025-10-23
**버전**: v2.0 (Refined)
**상태**: 사용자 검토 대기

---

## 📋 최종 확정 사항

### ✅ 사용자 요구사항 정리

| 항목 | 확정 내용 |
|------|----------|
| **파일 구조** | 기존 3개 파일 완전 삭제 + 새로운 1개 파일<br>백업: `_old/` 폴더에 보관 |
| **레이아웃** | 상단: 4개 스피너 (수평 배치)<br>하단: 에이전트 카드들 (동적 1~N개) |
| **스피너 파일** | `1_execution-plan_spinner.gif`<br>`2_execution-progress_spinner.gif`<br>`3_execution-progress_spinner.gif`<br>`4_response-generating_spinner.gif` |
| **전환 방식** | Option A + 개선: 비활성 스피너는 작고 회색, 활성 스피너는 크고 원래 색상 |
| **콘텐츠 영역** | 각 stage별로 적절한 내용 표시 (아이디어 기반) |

---

## 🎨 최종 디자인 사양

### 전체 레이아웃

```
┌─────────────────────────────────────────────────────────────┐
│                    Progress Container                        │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         4-Stage Spinner Bar (상단)                   │  │
│  │                                                        │  │
│  │  [①]      [②]      [③]      [④]                    │  │
│  │  출동중    분석중    실행중    답변작성중             │  │
│  │   ↑                                                    │  │
│  │  활성 = 크고 컬러 / 비활성 = 작고 회색               │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         Content Area (하단 - Stage별 변경)          │  │
│  │                                                        │  │
│  │  Stage 1: "질문을 접수했습니다..."                   │  │
│  │  Stage 2: 작업 계획 리스트                           │  │
│  │  Stage 3: [Agent1] [Agent2] [Agent3] 카드들         │  │
│  │  Stage 4: "최종 답변 생성 중..." + 3-step           │  │
│  │                                                        │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

---

## 🎯 4-Stage 세부 사양

### Stage 1: 출동 중 (Dispatch)

**타이밍**: 질문 입력 즉시 (0ms)

**스피너 상태**:
```
[●●● 1번 크고 컬러] [○ 2번 작고 회색] [○ 3번 작고 회색] [○ 4번 작고 회색]
```

**하단 콘텐츠**:
```tsx
<div className="text-center py-8">
  <div className="animate-pulse">
    <div className="text-lg font-semibold">질문을 접수했습니다</div>
    <div className="text-sm text-muted-foreground mt-2">
      잠시만 기다려주세요...
    </div>
  </div>
</div>
```

**스피너 GIF**: `1_execution-plan_spinner.gif`

---

### Stage 2: 분석 중 (Analysis)

**타이밍**: `analysis_start` 신호 수신 시 (~700ms)

**스피너 상태**:
```
[○ 1번 작고 회색] [●●● 2번 크고 컬러] [○ 3번 작고 회색] [○ 4번 작고 회색]
```

**하단 콘텐츠**:
```tsx
<div className="space-y-4">
  <div className="text-center">
    <div className="text-lg font-semibold">질문을 분석하고 있습니다</div>
  </div>

  {/* plan_ready 신호 수신 후 표시 */}
  {plan && (
    <div className="space-y-3">
      {/* 의도 분석 결과 */}
      <div className="p-4 bg-secondary/30 rounded-lg">
        <div className="font-medium">분석 완료: {plan.intent}</div>
        <div className="text-sm text-muted-foreground">
          신뢰도: {(plan.confidence * 100).toFixed(0)}%
        </div>
      </div>

      {/* 작업 계획 */}
      <div className="space-y-2">
        <div className="font-medium">작업 계획:</div>
        {plan.execution_steps.map((step, idx) => (
          <div key={idx} className="flex items-center gap-2 p-2 bg-muted/50 rounded">
            <div className="w-6 h-6 rounded-full bg-primary/20 flex items-center justify-center text-xs">
              {idx + 1}
            </div>
            <div className="text-sm">{step.task}</div>
          </div>
        ))}
      </div>
    </div>
  )}
</div>
```

**스피너 GIF**: `2_execution-progress_spinner.gif`

---

### Stage 3: 실행 중 (Executing)

**타이밍**: `execution_start` 신호 수신 시 (~2200ms)

**스피너 상태**:
```
[○ 1번 작고 회색] [○ 2번 작고 회색] [●●● 3번 크고 컬러] [○ 4번 작고 회색]
```

**하단 콘텐츠**:
```tsx
<div className="space-y-4">
  {/* 전체 진행률 */}
  <div>
    <div className="flex justify-between mb-2">
      <span className="font-medium">전체 진행률</span>
      <span className="text-sm text-muted-foreground">
        {completedSteps}/{totalSteps} 완료
      </span>
    </div>
    <ProgressBar value={overallProgress} />
  </div>

  {/* 에이전트 카드들 (동적 1~N개) */}
  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
    {steps.map((step) => (
      <AgentCard key={step.step_id} step={step} />
    ))}
  </div>
</div>

// AgentCard 컴포넌트
function AgentCard({ step }) {
  const statusConfig = {
    pending: { icon: "○", color: "text-muted-foreground", bg: "bg-muted" },
    in_progress: { icon: "●", color: "text-primary", bg: "bg-primary/10" },
    completed: { icon: "✓", color: "text-green-600", bg: "bg-green-50" },
    failed: { icon: "✗", color: "text-red-600", bg: "bg-red-50" },
    skipped: { icon: "⊘", color: "text-yellow-600", bg: "bg-yellow-50" }
  }

  const config = statusConfig[step.status]

  return (
    <div className={`p-3 rounded-lg border ${config.bg}`}>
      <div className="flex items-center gap-2 mb-2">
        <span className={`text-xl ${config.color}`}>{config.icon}</span>
        <span className="font-medium text-sm">{step.task}</span>
      </div>
      <div className="text-xs text-muted-foreground">
        {step.description}
      </div>
      {step.status === "in_progress" && (
        <ProgressBar value={step.progress} size="sm" className="mt-2" />
      )}
    </div>
  )
}
```

**스피너 GIF**: `3_execution-progress_spinner.gif`

---

### Stage 4: 답변 작성 중 (Generating)

**타이밍**: `response_generating_start` 신호 수신 시 (~9100ms)

**스피너 상태**:
```
[○ 1번 작고 회색] [○ 2번 작고 회색] [○ 3번 작고 회색] [●●● 4번 크고 컬러]
```

**하단 콘텐츠**:
```tsx
<div className="space-y-6">
  {/* 3-step 프로세스 */}
  <div className="space-y-4">
    {[
      { id: "collect", label: "데이터 수집 완료", status: "completed" },
      {
        id: "organize",
        label: "정보 정리 중",
        status: responsePhase === "aggregation" ? "in_progress" : "completed"
      },
      {
        id: "generate",
        label: "최종 답변 생성 중",
        status: responsePhase === "response_generation" ? "in_progress" : "pending"
      }
    ].map((step, idx) => (
      <div key={step.id} className="flex items-center gap-4">
        {/* 상태 아이콘 */}
        <div className={`
          w-10 h-10 rounded-full flex items-center justify-center border-2
          ${step.status === "completed"
            ? "bg-primary border-primary text-primary-foreground"
            : step.status === "in_progress"
            ? "bg-primary/20 border-primary text-primary animate-pulse"
            : "bg-muted border-muted-foreground/20 text-muted-foreground"
          }
        `}>
          {step.status === "completed" ? "✓" : idx + 1}
        </div>

        {/* 레이블 */}
        <div className="flex-1">
          <div className={`font-medium ${
            step.status === "completed" || step.status === "in_progress"
              ? "text-foreground"
              : "text-muted-foreground"
          }`}>
            {step.label}
          </div>
        </div>
      </div>
    ))}
  </div>

  {/* 안내 메시지 */}
  <div className="text-center text-sm text-muted-foreground pt-4 border-t">
    잠시만 기다려주세요. 최적의 답변을 준비하고 있습니다.
  </div>
</div>
```

**스피너 GIF**: `4_response-generating_spinner.gif`

---

## 🎭 스피너 애니메이션 사양

### 크기 및 스타일

**비활성 상태** (작고 회색):
```css
width: 60px;
height: 60px;
opacity: 0.4;
filter: grayscale(100%);
transition: all 0.15s ease;
```

**활성 상태** (크고 컬러):
```css
width: 100px;
height: 100px;
opacity: 1;
filter: grayscale(0%);
transition: all 0.15s ease;
```

### 전환 애니메이션

```tsx
<div className={`
  transition-all duration-150 ease-in-out
  ${isActive
    ? 'w-[100px] h-[100px] opacity-100 grayscale-0'
    : 'w-[60px] h-[60px] opacity-40 grayscale'
  }
`}>
  <img src={spinnerGif} className="w-full h-full object-contain" />
</div>
```

---

## 🏗️ 컴포넌트 구조

### 파일: `progress-container.tsx`

```tsx
export type ProgressStage = "dispatch" | "analysis" | "executing" | "generating"

export interface ProgressContainerProps {
  stage: ProgressStage
  plan?: ExecutionPlan
  steps?: ExecutionStep[]
  responsePhase?: "aggregation" | "response_generation"
}

export function ProgressContainer({
  stage,
  plan,
  steps = [],
  responsePhase = "aggregation"
}: ProgressContainerProps) {

  // Stage 설정
  const stageConfig = {
    dispatch: {
      index: 0,
      title: "출동 중",
      spinner: "/animation/spinner/1_execution-plan_spinner.gif"
    },
    analysis: {
      index: 1,
      title: "분석 중",
      spinner: "/animation/spinner/2_execution-progress_spinner.gif"
    },
    executing: {
      index: 2,
      title: "실행 중",
      spinner: "/animation/spinner/3_execution-progress_spinner.gif"
    },
    generating: {
      index: 3,
      title: "답변 작성 중",
      spinner: "/animation/spinner/4_response-generating_spinner.gif"
    }
  }

  const currentStage = stageConfig[stage]
  const allStages = Object.values(stageConfig)

  return (
    <Card className="p-6">
      {/* 상단: 4-Stage Spinner Bar */}
      <div className="flex justify-center items-center gap-8 mb-8">
        {allStages.map((s, idx) => (
          <div key={idx} className="flex flex-col items-center gap-2">
            {/* 스피너 */}
            <div className={`
              transition-all duration-150 ease-in-out
              ${idx === currentStage.index
                ? 'w-[100px] h-[100px] opacity-100 grayscale-0'
                : 'w-[60px] h-[60px] opacity-40 grayscale'
              }
            `}>
              <img
                src={s.spinner}
                alt={s.title}
                className="w-full h-full object-contain"
              />
            </div>

            {/* 레이블 */}
            <div className={`
              text-sm font-medium transition-colors
              ${idx === currentStage.index
                ? 'text-foreground'
                : 'text-muted-foreground'
              }
            `}>
              {s.title}
            </div>
          </div>
        ))}
      </div>

      {/* 하단: Content Area (Stage별 변경) */}
      <div className="min-h-[200px]">
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

## 🔄 Message 흐름

### Message 타입 (간소화)

```typescript
interface Message {
  id: string
  type: "user" | "bot" | "progress" | "guidance"
  content: string
  timestamp: Date

  // Progress 전용 데이터
  progressData?: {
    stage: ProgressStage
    plan?: ExecutionPlan
    steps?: ExecutionStep[]
    responsePhase?: "aggregation" | "response_generation"
  }

  // Bot/Guidance 데이터
  structuredData?: { ... }
  guidanceData?: { ... }
}
```

### WebSocket 핸들러 흐름

```typescript
// 1. 질문 입력 즉시 (handleSendMessage)
const progressMsg: Message = {
  type: "progress",
  progressData: { stage: "dispatch" }
}
setMessages([...messages, userMsg, progressMsg])

// 2. analysis_start 수신
case 'analysis_start':
  updateProgress({ stage: "analysis" })
  break

// 3. plan_ready 수신
case 'plan_ready':
  updateProgress({
    stage: "analysis",  // stage 유지
    plan: message.plan  // plan 데이터 추가
  })
  break

// 4. execution_start 수신
case 'execution_start':
  updateProgress({
    stage: "executing",
    plan: message.plan,
    steps: message.execution_steps
  })
  break

// 5. todo_updated 수신
case 'todo_updated':
  updateProgress({
    stage: "executing",  // stage 유지
    steps: message.execution_steps  // steps만 업데이트
  })
  break

// 6. response_generating_start 수신
case 'response_generating_start':
  updateProgress({
    stage: "generating",
    responsePhase: "aggregation"
  })
  break

// 7. response_generating_progress 수신
case 'response_generating_progress':
  updateProgress({
    stage: "generating",  // stage 유지
    responsePhase: "response_generation"  // phase만 업데이트
  })
  break

// 8. final_response 수신
case 'final_response':
  removeProgress()  // progress 제거
  addBotMessage(message)  // 봇 메시지 추가
  break
```

---

## 📦 구현 단계

### Phase 1: 준비 작업
1. ✅ 기존 3개 파일을 `_old/` 폴더로 백업
2. ✅ 스피너 GIF 경로 확인 (1~4번)
3. ✅ Message 타입 정의

### Phase 2: 컴포넌트 생성
1. `progress-container.tsx` 생성
2. 4개 서브 컴포넌트 생성:
   - `DispatchContent.tsx`
   - `AnalysisContent.tsx`
   - `ExecutingContent.tsx`
   - `GeneratingContent.tsx`
3. `AgentCard.tsx` 생성 (Stage 3용)

### Phase 3: 통합
1. `chat-interface.tsx` Message 타입 수정
2. WebSocket 핸들러 수정 (8개 case)
3. 렌더링 로직 수정

### Phase 4: Backend 신호 추가
1. `team_supervisor.py`에 `analysis_start` 추가
2. WebSocket 메시지 타입에 `analysis_start` 등록

### Phase 5: 테스트
1. 빌드 검증
2. 4-stage 순차 전환 확인
3. 스피너 애니메이션 확인
4. Edge case 테스트 (IRRELEVANT, 데이터 재사용)

---

## ✅ 체크리스트

구현 전 확인 사항:

- [ ] 스피너 GIF 4개 파일 경로 확인
- [ ] 비활성/활성 스피너 크기 및 스타일 확정 (60px/100px)
- [ ] 각 Stage별 콘텐츠 내용 확정
- [ ] Message 타입 변경 범위 확정
- [ ] 기존 파일 백업 완료

---

## 🚀 예상 결과

### Before (현재)
```
질문 입력 → ExecutionPlanPage 표시
  ↓
plan_ready → ExecutionPlanPage 업데이트
  ↓
execution_start → ExecutionProgressPage로 교체 (깜빡임)
  ↓
response_generating_start → ResponseGeneratingPage로 교체 (깜빡임)
```

### After (구현 후)
```
질문 입력 → ProgressContainer (stage: dispatch)
            [●●● 크고 컬러] [○ 작고 회색] [○] [○]
  ↓
analysis_start → stage: analysis로 전환 (부드럽게)
                 [○ 작고 회색] [●●● 크고 컬러] [○] [○]
  ↓
execution_start → stage: executing으로 전환 (부드럽게)
                  [○] [○] [●●● 크고 컬러] [○]
  ↓
response_generating_start → stage: generating으로 전환 (부드럽게)
                             [○] [○] [○] [●●● 크고 컬러]
```

**개선점**:
- ✅ 페이지 교체 없음 (깜빡임 제거)
- ✅ 시각적 진행 표시 (4개 스피너)
- ✅ 부드러운 전환 애니메이션
- ✅ 일관된 레이아웃

---

## 📝 사용자 확인 필요 사항

구현 전 최종 확인:

1. **스피너 크기**: 비활성 60px / 활성 100px → OK?
2. **회색 톤**: grayscale(100%) + opacity 0.4 → OK?
3. **전환 속도**: 0.15초 (시각 효과만) → OK?
4. **콘텐츠 높이**: 최소 200px → OK?

---

**이 계획서로 구현을 시작해도 될까요?**
확인해주시면 바로 구현 시작하겠습니다.
