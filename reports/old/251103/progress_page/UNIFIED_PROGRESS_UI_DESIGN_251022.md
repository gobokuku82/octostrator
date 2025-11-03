# 통합 Progress UI 설계 계획서

**작성일**: 2025-10-22
**목적**: 3개의 Progress 페이지를 1개의 통합 Progress UI로 재설계
**타입**: 동적 에이전트 표시 시스템
**대상**: ExecutionPlanPage, ExecutionProgressPage, ResponseGeneratingPage

---

## 🎯 목표 UI 구조

### 시각적 레이아웃

```
┌─────────────────────────────────────────────────────────────┐ ← 빨간 네모 (전체 Card)
│                                                             │
│  ┌───────┐  ┌───────┐  ┌───────┐  ┌───────┐               │
│  │       │  │       │  │       │  │       │               │
│  │ Step1 │  │ Step2 │  │ Step3 │  │ Step4 │  ← 파란 네모  │
│  │       │  │       │  │       │  │       │  (스피너들)   │
│  └───────┘  └───────┘  └───────┘  └───────┘               │
│                                                             │
│  ┌────────────────────────────────────────────────────┐    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────┐ │    │
│  │  │              │  │              │  │          │ │    │
│  │  │  정보검색    │  │    분석      │  │   문서   │ │    │ ← 녹색 네모
│  │  │   Agent      │  │   Agent      │  │  Agent   │ │    │  (작업 표시 영역)
│  │  │              │  │              │  │          │ │    │
│  │  └──────────────┘  └──────────────┘  └──────────┘ │    │
│  │                                                    │    │
│  │            ← 노란 네모 (개별 Agent Card)           │    │
│  └────────────────────────────────────────────────────┘    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 📐 레이아웃 분석

### 1. 빨간 네모 - 전체 컨테이너
- **역할**: Progress 전체를 감싸는 Card
- **클래스**: `Card`, `max-w-5xl`, `p-0`
- **구성**:
  - 상단: 제목 영역
  - 중단: 스피너 영역 (수평 배치)
  - 하단: Agent 작업 표시 영역

### 2. 파란 네모 - 스피너 영역
- **역할**: 단계별 진행 상태 시각화
- **개수**: 동적 (1~4개, 또는 그 이상)
- **형태**: 정사각형
- **배치**: 수평 (flex-row)
- **크기**: 고정 또는 균등 분할

### 3. 녹색 네모 - 작업 표시 영역 컨테이너
- **역할**: Agent Card들을 감싸는 영역
- **배치**: 수평 스크롤 가능 (많을 경우)
- **패딩**: `px-6 pb-6`

### 4. 노란 네모 - 개별 Agent Card
- **역할**: 각 에이전트의 작업 상태 표시
- **개수**: 동적 (1~3개 또는 그 이상)
- **내용**:
  - 에이전트 이름 (정보검색, 분석, 문서)
  - 상태 (대기중, 실행중, 완료, 실패)
  - 진행률 또는 결과

---

## 🔧 컴포넌트 구조

### 계층 구조

```
ProgressContainer (통합 컨테이너)
├─ ProgressHeader (제목, 전체 진행률)
├─ ProgressSteps (스피너 영역 - 파란 네모)
│  └─ StepIndicator[] (개별 스피너)
└─ ProgressContent (작업 표시 영역 - 녹색 네모)
   └─ AgentCard[] (동적 에이전트 카드 - 노란 네모)
```

### 파일 구조

```
frontend/components/
├─ progress/
│  ├─ ProgressContainer.tsx        (메인 통합 컨테이너)
│  ├─ ProgressHeader.tsx           (공통 헤더)
│  ├─ ProgressSteps.tsx            (스피너 영역)
│  ├─ StepIndicator.tsx            (개별 스피너)
│  ├─ ProgressContent.tsx          (작업 표시 영역)
│  └─ AgentCard.tsx                (에이전트 카드)
│
├─ _old/                            (백업 폴더 - Progress 관련만)
│  ├─ execution-plan-page_old.tsx
│  ├─ execution-progress-page_old.tsx
│  └─ response-generating-page_old.tsx
│
└─ guidance-page.tsx                (유지 - Progress 무관)
```

---

## 📊 데이터 구조

### ProgressData 인터페이스

```typescript
interface ProgressData {
  // 전체 상태
  status: "plan" | "executing" | "generating" | "guidance" | "completed"
  title: string
  description: string

  // 스피너 영역 데이터
  steps: ProgressStep[]

  // Agent 영역 데이터
  agents: AgentInfo[]
}

interface ProgressStep {
  id: string
  label: string                      // "1단계", "2단계", "3단계"
  status: "pending" | "active" | "completed" | "failed"
  spinnerUrl?: string                // GIF 경로 (옵션)
}

interface AgentInfo {
  id: string
  name: string                       // "정보검색", "분석", "문서"
  type: "search" | "analysis" | "document"
  status: "waiting" | "running" | "completed" | "failed"
  progress?: number                  // 0-100
  message?: string                   // 현재 작업 메시지
  result?: {
    success: boolean
    data?: any
    error?: string
  }
}
```

---

## 🎨 상세 설계

### 1. ProgressContainer.tsx (메인)

```tsx
interface ProgressContainerProps {
  data: ProgressData
}

export function ProgressContainer({ data }: ProgressContainerProps) {
  return (
    <Card className="p-0 bg-card border flex-1 overflow-hidden max-w-5xl">
      {/* 헤더: 제목, 전체 진행률 */}
      <ProgressHeader
        title={data.title}
        description={data.description}
        totalProgress={calculateProgress(data.steps)}
      />

      {/* 스피너 영역 - 수평 배치 */}
      <ProgressSteps steps={data.steps} />

      {/* Agent 작업 표시 영역 */}
      <ProgressContent agents={data.agents} />
    </Card>
  )
}
```

---

### 2. ProgressSteps.tsx (파란 네모 영역)

```tsx
interface ProgressStepsProps {
  steps: ProgressStep[]
}

export function ProgressSteps({ steps }: ProgressStepsProps) {
  return (
    <div className="px-6 pt-4 pb-4">
      {/* 수평 스피너 배치 */}
      <div className="flex justify-center items-center gap-4">
        {steps.map((step, index) => (
          <StepIndicator
            key={step.id}
            step={step}
            index={index}
          />
        ))}
      </div>
    </div>
  )
}
```

---

### 3. StepIndicator.tsx (개별 스피너)

```tsx
interface StepIndicatorProps {
  step: ProgressStep
  index: number
}

export function StepIndicator({ step, index }: StepIndicatorProps) {
  // 상태별 스타일
  const getStatusStyle = () => {
    switch (step.status) {
      case "active":
        return "border-primary bg-primary/10"
      case "completed":
        return "border-green-500 bg-green-50"
      case "failed":
        return "border-red-500 bg-red-50"
      default:
        return "border-muted bg-muted/30"
    }
  }

  return (
    <div className="flex flex-col items-center gap-2">
      {/* 정사각형 스피너 */}
      <div className={`
        w-20 h-20
        rounded-lg
        border-2
        flex items-center justify-center
        transition-all
        ${getStatusStyle()}
      `}>
        {step.status === "active" && step.spinnerUrl ? (
          <img
            src={step.spinnerUrl}
            alt={step.label}
            className="w-16 h-16 object-contain"
          />
        ) : step.status === "completed" ? (
          <svg className="w-10 h-10 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        ) : (
          <div className="text-2xl font-bold text-muted-foreground">
            {index + 1}
          </div>
        )}
      </div>

      {/* 단계 레이블 */}
      <div className="text-xs text-center text-muted-foreground">
        {step.label}
      </div>
    </div>
  )
}
```

---

### 4. ProgressContent.tsx (녹색 네모 영역)

```tsx
interface ProgressContentProps {
  agents: AgentInfo[]
}

export function ProgressContent({ agents }: ProgressContentProps) {
  return (
    <div className="px-6 pb-6">
      {/* Agent 카드들 - 수평 배치 */}
      <div className="flex gap-4 overflow-x-auto">
        {agents.map((agent) => (
          <AgentCard key={agent.id} agent={agent} />
        ))}
      </div>

      {/* 에이전트가 없을 때 */}
      {agents.length === 0 && (
        <div className="text-center py-8 text-muted-foreground">
          <p className="text-sm">작업 준비 중...</p>
        </div>
      )}
    </div>
  )
}
```

---

### 5. AgentCard.tsx (노란 네모 - 개별 에이전트)

```tsx
interface AgentCardProps {
  agent: AgentInfo
}

export function AgentCard({ agent }: AgentCardProps) {
  // 상태별 스타일
  const getStatusColor = () => {
    switch (agent.status) {
      case "running": return "border-blue-500 bg-blue-50"
      case "completed": return "border-green-500 bg-green-50"
      case "failed": return "border-red-500 bg-red-50"
      default: return "border-muted bg-muted/30"
    }
  }

  const getStatusIcon = () => {
    switch (agent.status) {
      case "running": return "⚙️"
      case "completed": return "✅"
      case "failed": return "❌"
      default: return "⏳"
    }
  }

  return (
    <div className={`
      min-w-[200px]
      flex-1
      border-2
      rounded-lg
      p-4
      transition-all
      ${getStatusColor()}
    `}>
      {/* 헤더: 에이전트 이름 + 상태 */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-lg">{getStatusIcon()}</span>
          <h4 className="font-semibold text-sm">{agent.name}</h4>
        </div>
        <Badge variant={agent.status === "running" ? "default" : "secondary"}>
          {agent.status}
        </Badge>
      </div>

      {/* 진행률 (실행중일 때) */}
      {agent.status === "running" && agent.progress !== undefined && (
        <div className="mb-3">
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs text-muted-foreground">진행률</span>
            <span className="text-xs font-medium">{agent.progress}%</span>
          </div>
          <ProgressBar value={agent.progress} size="sm" />
        </div>
      )}

      {/* 메시지 */}
      {agent.message && (
        <p className="text-xs text-muted-foreground mb-2">
          {agent.message}
        </p>
      )}

      {/* 결과 (완료/실패 시) */}
      {agent.result && (
        <div className="mt-3 pt-3 border-t">
          {agent.result.success ? (
            <p className="text-xs text-green-700">✓ 완료</p>
          ) : (
            <p className="text-xs text-red-700">✗ {agent.result.error}</p>
          )}
        </div>
      )}
    </div>
  )
}
```

---

## 🔄 상태 전환 시나리오

### 시나리오 1: 계획 수립 중

```typescript
{
  status: "plan",
  title: "작업 계획 분석 중",
  description: "질문을 분석하고 실행 계획을 수립하고 있습니다",
  steps: [
    { id: "1", label: "계획 수립", status: "active", spinnerUrl: "/spinner/1_plan.gif" },
    { id: "2", label: "작업 실행", status: "pending" },
    { id: "3", label: "결과 생성", status: "pending" }
  ],
  agents: []  // 아직 에이전트 없음
}
```

**UI**:
- 스피너 1개만 활성화
- Agent 영역 비어있음 ("작업 준비 중...")

---

### 시나리오 2: 작업 실행 중 (3개 에이전트)

```typescript
{
  status: "executing",
  title: "작업 실행 중",
  description: "3개의 에이전트가 병렬로 작업을 수행하고 있습니다",
  steps: [
    { id: "1", label: "계획 수립", status: "completed" },
    { id: "2", label: "작업 실행", status: "active", spinnerUrl: "/spinner/2_execute.gif" },
    { id: "3", label: "결과 생성", status: "pending" }
  ],
  agents: [
    {
      id: "search",
      name: "정보검색",
      type: "search",
      status: "completed",
      progress: 100,
      message: "5건의 관련 법령 검색 완료",
      result: { success: true }
    },
    {
      id: "analysis",
      name: "분석",
      type: "analysis",
      status: "running",
      progress: 65,
      message: "계약서 조항 분석 중..."
    },
    {
      id: "document",
      name: "문서",
      type: "document",
      status: "waiting",
      message: "분석 완료 대기 중"
    }
  ]
}
```

**UI**:
- 스피너 2개 완료, 1개 활성화
- Agent 3개 표시:
  - 정보검색: 녹색 (완료)
  - 분석: 파란색 (실행중, 65%)
  - 문서: 회색 (대기중)

---

### 시나리오 3: 응답 생성 중

```typescript
{
  status: "generating",
  title: "AI 응답 생성 중",
  description: "수집된 정보를 바탕으로 최종 답변을 생성하고 있습니다",
  steps: [
    { id: "1", label: "계획 수립", status: "completed" },
    { id: "2", label: "작업 실행", status: "completed" },
    { id: "3", label: "결과 생성", status: "active", spinnerUrl: "/spinner/3_generate.gif" }
  ],
  agents: [
    {
      id: "aggregation",
      name: "정보 정리",
      type: "analysis",
      status: "completed",
      result: { success: true }
    },
    {
      id: "response",
      name: "답변 생성",
      type: "document",
      status: "running",
      progress: 80,
      message: "최종 답변을 작성하고 있습니다..."
    }
  ]
}
```

---

## 📂 구현 순서

### Phase 1: 기존 파일 백업 (5분)

1. **백업 폴더 생성**
   ```bash
   mkdir frontend/components/_old
   ```

2. **Progress 관련 파일만 이동** (3개)
   ```bash
   mv execution-plan-page.tsx _old/execution-plan-page_old.tsx
   mv execution-progress-page.tsx _old/execution-progress-page_old.tsx
   mv response-generating-page.tsx _old/response-generating-page_old.tsx
   ```

3. **guidance-page.tsx는 유지** (Progress 무관)

---

### Phase 2: 새 컴포넌트 생성 (30분)

1. **progress 폴더 생성**
   ```
   frontend/components/progress/
   ```

2. **컴포넌트 파일 생성** (순서대로)
   - `ProgressContainer.tsx` (메인)
   - `ProgressHeader.tsx`
   - `ProgressSteps.tsx`
   - `StepIndicator.tsx`
   - `ProgressContent.tsx`
   - `AgentCard.tsx`

3. **타입 정의**
   - `types/progress.ts` (ProgressData, AgentInfo 등)

---

### Phase 3: chat-interface.tsx 수정 (15분)

**변경 전** (3개 독립 컴포넌트):
```tsx
{message.type === "execution-plan" && <ExecutionPlanPage />}
{message.type === "execution-progress" && <ExecutionProgressPage />}
{message.type === "response-generating" && <ResponseGeneratingPage />}
{message.type === "guidance" && <GuidancePage />}  // ← 유지
```

**변경 후** (1개 통합 컨테이너):
```tsx
{(message.type === "execution-plan" ||
  message.type === "execution-progress" ||
  message.type === "response-generating") && (
  <ProgressContainer data={convertToProgressData(message)} />
)}
{message.type === "guidance" && <GuidancePage />}  // ← 그대로 유지
```

---

### Phase 4: 데이터 변환 로직 (20분)

```typescript
function convertToProgressData(message: Message): ProgressData {
  switch (message.type) {
    case "execution-plan":
      return {
        status: "plan",
        title: "작업 계획 분석 중",
        description: "질문을 분석하고 실행 계획을 수립하고 있습니다",
        steps: [
          { id: "1", label: "계획", status: "active", spinnerUrl: "/spinner/1.gif" },
          { id: "2", label: "실행", status: "pending" },
          { id: "3", label: "생성", status: "pending" }
        ],
        agents: []
      }

    case "execution-progress":
      return {
        status: "executing",
        title: "작업 실행 중",
        steps: [...],
        agents: message.executionSteps.map(step => ({
          id: step.step_id,
          name: getAgentName(step.team),
          type: step.team,
          status: mapStatus(step.status),
          message: step.description
        }))
      }

    // ...
  }
}
```

---

### Phase 5: 빌드 및 테스트 (10분)

```bash
npm run build
```

---

## ✅ 체크리스트

### 백업 (Progress 관련 3개만)
- [ ] `_old` 폴더 생성
- [ ] execution-plan-page.tsx → _old로 이동
- [ ] execution-progress-page.tsx → _old로 이동
- [ ] response-generating-page.tsx → _old로 이동
- [ ] ~~guidance-page.tsx~~ → **유지** (Progress 무관)

### 새 컴포넌트
- [ ] progress 폴더 생성
- [ ] ProgressContainer.tsx 생성
- [ ] ProgressHeader.tsx 생성
- [ ] ProgressSteps.tsx 생성
- [ ] StepIndicator.tsx 생성
- [ ] ProgressContent.tsx 생성
- [ ] AgentCard.tsx 생성
- [ ] types/progress.ts 생성

### 통합
- [ ] chat-interface.tsx 수정
- [ ] 데이터 변환 로직 구현
- [ ] import 경로 수정

### 검증
- [ ] TypeScript 컴파일 성공
- [ ] 빌드 성공
- [ ] 시각적 확인 (3가지 시나리오)

---

## 🎨 디자인 스펙

### 색상
- **Active**: `border-blue-500 bg-blue-50`
- **Completed**: `border-green-500 bg-green-50`
- **Failed**: `border-red-500 bg-red-50`
- **Pending**: `border-muted bg-muted/30`

### 크기
- **스피너 정사각형**: `w-20 h-20` (80px)
- **스피너 GIF**: `w-16 h-16` (64px)
- **Agent Card 최소 너비**: `min-w-[200px]`
- **간격**: `gap-4` (16px)

### 애니메이션
- 상태 전환: `transition-all duration-300`
- 스피너: `animate-spin` (활성 시)
- Agent Card 등장: `fade-in` (추후)

---

## 📊 예상 효과

### 정량적
- **파일 수**: 3개 독립 → 6개 구조화 (통합 컨테이너)
- **코드 중복 제거**: 공통 로직 통합
- **유지보수성**: 1개 진입점으로 관리 용이
- **guidance-page.tsx**: 영향 없음 (독립 유지)

### 정성적
- ✅ 완벽한 통일감 (하나의 프레임)
- ✅ 동적 에이전트 표시 (1~N개 자동 대응)
- ✅ 직관적인 진행 상황 시각화
- ✅ 확장성 (새 에이전트 추가 용이)

---

## 🚨 주의사항

### 1. 에이전트 동적 개수
- 최소 1개 ~ 최대 제한 없음
- 3개 초과 시 수평 스크롤 (`overflow-x-auto`)

### 2. 스피너 개수
- 현재: 3단계 고정 (계획 → 실행 → 생성)
- 필요 시 동적 확장 가능

### 3. 반응형
- 현재: 데스크톱 전용
- 모바일: Phase 2에서 세로 레이아웃 고려

---

## 🎯 다음 단계

사용자 승인 후:
1. Phase 1 실행 (백업)
2. Phase 2 실행 (새 컴포넌트 생성)
3. Phase 3-4 실행 (통합)
4. Phase 5 실행 (테스트)

**예상 총 소요 시간**: 60-90분

---

**승인 여부**: 이 계획대로 진행할까요?
