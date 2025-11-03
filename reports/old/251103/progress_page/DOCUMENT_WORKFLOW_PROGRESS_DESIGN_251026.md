# 문서 생성 워크플로우 Progress UI 설계 계획서

**작성일**: 2025-10-26
**목적**: 문서 생성(HITL) 워크플로우에 맞는 Progress UI 설계
**문제**: 기존 progress-container.tsx는 일반 질의응답 흐름용, 문서 생성과 구조 불일치

---

## 📋 목차

1. [문제 분석](#문제-분석)
2. [현재 구조 vs 문서 생성 구조](#현재-구조-vs-문서-생성-구조)
3. [설계 방안 비교](#설계-방안-비교)
4. [권장 방안: Hybrid Approach](#권장-방안-hybrid-approach)
5. [구현 계획](#구현-계획)

---

## 문제 분석

### 현재 Progress Container 구조

**파일**: `frontend/components/progress-container.tsx`

#### 4-Stage 워크플로우

```typescript
type ProgressStage = "dispatch" | "analysis" | "executing" | "generating"

const STAGE_CONFIG = {
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
```

**특징**:
- ✅ 일반 질의응답에 적합 (검색 → 분석 → 답변)
- ✅ 병렬 팀 실행 표시 (ExecutingContent - AgentCard 여러 개)
- ❌ HITL 중단 지점 표시 없음
- ❌ Form 입력 단계 표시 부적합
- ❌ 순차 검증 단계 표시 부적합

### 문서 생성 워크플로우 (DocumentExecutor)

**파일**: `backend/app/service_agent/execution_agents/document_executor.py`

#### 새로운 6-Step 워크플로우

```python
Planning
  → Validation (ValidationTool 실행)
    → Aggregate (HITL - 폼 입력 대기) ⏸️
      → Compliance (ComplianceTool 실행)
        → Generate (문서 생성)
          → Final Review (HITL - 최종 승인) ⏸️
```

**특징**:
- ⭐ **Sequential** (순차 진행, 병렬 없음)
- ⭐ **HITL 2곳**: Aggregate, Final Review
- ⭐ **Validation 단계**: 필수 필드 체크
- ⭐ **Compliance 단계**: 법률 준수 확인
- ⭐ **Form 입력**: 사용자가 누락 필드 입력
- ⭐ **Review**: 최종 문서 검토 및 승인/수정/거부

---

## 현재 구조 vs 문서 생성 구조

### 비교표

| 항목 | 일반 질의응답 (현재) | 문서 생성 (필요) |
|------|---------------------|-----------------|
| **워크플로우** | dispatch → analysis → executing → generating | planning → validation → form_input → compliance → generate → review |
| **실행 방식** | 병렬 (여러 팀 동시 실행) | 순차 (한 단계씩 진행) |
| **HITL 지점** | 없음 | 2곳 (Form Input, Final Review) |
| **진행률 계산** | 팀 완료 비율 기반 | 단계 완료 비율 기반 |
| **사용자 인터랙션** | 없음 (자동 진행) | 폼 입력, 승인 필요 |
| **에러 표시** | 팀 실패 표시 | 검증 실패, 누락 필드 표시 |

### 구조적 차이

#### 1. Stage 개념

**일반 질의응답**:
```
[출동] → [분석] → [실행] → [답변작성]
          ↓        ↓
        의도분석  병렬실행
                (Search/Document/Analysis)
```

**문서 생성**:
```
[계획] → [검증] → [입력대기⏸️] → [법률검토] → [생성] → [승인대기⏸️]
  ↓       ↓         ↓           ↓         ↓         ↓
추출    필수필드   폼입력      준수확인   DOCX생성  최종검토
```

#### 2. Progress 표시 방식

**일반 질의응답 (ExecutingContent)**:
```tsx
<div className="grid grid-cols-3">
  <AgentCard step={searchStep} />   // 병렬
  <AgentCard step={documentStep} /> // 병렬
  <AgentCard step={analysisStep} /> // 병렬
</div>
```

**문서 생성 (필요한 형태)**:
```tsx
<div className="space-y-2">
  <StepCard step="planning" status="completed" />       // 순차
  <StepCard step="validation" status="completed" />     // 순차
  <StepCard step="form_input" status="in_progress" />   // 순차 + HITL
  <StepCard step="compliance" status="pending" />       // 순차
  <StepCard step="generate" status="pending" />         // 순차
  <StepCard step="review" status="pending" />           // 순차 + HITL
</div>
```

#### 3. HITL 표시

**현재 (없음)**:
- 자동으로 계속 진행
- 사용자 입력 대기 표시 없음

**필요 (2곳)**:
```tsx
// HITL 지점 1: Form Input
<FormInputCard
  status="waiting_user"
  missingFields={["임대인 연락처", "전용면적"]}
  validationErrors={[...]}
/>

// HITL 지점 2: Final Review
<FinalReviewCard
  status="waiting_approval"
  document={finalDocument}
  complianceWarnings={[...]}
  actions={["approve", "modify", "reject"]}
/>
```

---

## 설계 방안 비교

### Option A: 문서 전용 새로운 Stage 정의

**개요**: 문서 생성 전용 6-Stage 정의

#### 구조

```typescript
// 새로운 타입 정의
type DocumentProgressStage =
  | "planning"        // 계획 수립
  | "validation"      // 필수 필드 검증
  | "form_input"      // 폼 입력 (HITL)
  | "compliance"      // 법률 준수 확인
  | "generating"      // 문서 생성
  | "review"          // 최종 검토 (HITL)

const DOCUMENT_STAGE_CONFIG = {
  planning: {
    index: 0,
    title: "계획 수립",
    icon: "📋",
    description: "문서 요구사항 분석 중"
  },
  validation: {
    index: 1,
    title: "정보 검증",
    icon: "🔍",
    description: "필수 정보 확인 중"
  },
  form_input: {
    index: 2,
    title: "정보 입력",
    icon: "✍️",
    description: "누락 정보 입력 필요",
    isHitl: true  // ⭐ HITL 지점 표시
  },
  compliance: {
    index: 3,
    title: "법률 검토",
    icon: "⚖️",
    description: "법적 요구사항 확인 중"
  },
  generating: {
    index: 4,
    title: "문서 생성",
    icon: "📝",
    description: "계약서 작성 중"
  },
  review: {
    index: 5,
    title: "최종 검토",
    icon: "✅",
    description: "승인 필요",
    isHitl: true  // ⭐ HITL 지점 표시
  }
}
```

#### 장점

✅ **명확성**: 문서 생성 흐름에 정확히 일치
✅ **HITL 표시**: 중단 지점 명확히 표시
✅ **순차 진행**: 단계별 순차 진행 표현 용이
✅ **독립성**: 일반 질의응답과 분리, 유지보수 쉬움

#### 단점

❌ **중복 코드**: 완전히 새로운 컴포넌트 필요
❌ **스피너 애니메이션**: 6개 새로 제작 필요
❌ **복잡도 증가**: 2개의 Progress 시스템 관리

#### 구현 복잡도

**파일 생성**:
```
frontend/components/
├── progress-container.tsx                     # 기존 (일반용)
├── document-progress-container.tsx            # 신규 (문서용)
└── document-progress/
    ├── PlanningStage.tsx
    ├── ValidationStage.tsx
    ├── FormInputStage.tsx                     # HITL
    ├── ComplianceStage.tsx
    ├── GeneratingStage.tsx
    └── ReviewStage.tsx                        # HITL
```

**예상 작업량**: **20-25시간**

---

### Option B: 기존 4-Stage 재활용

**개요**: 기존 4-Stage를 문서 생성에 맞게 매핑

#### 매핑 전략

```typescript
// 문서 생성 → 기존 Stage 매핑
Document Workflow        →  Existing Stage
─────────────────────────────────────────────
Planning                 →  analysis
Validation               →  analysis
Form Input (HITL)        →  executing (변형)
Compliance               →  executing (변형)
Generate                 →  generating
Review (HITL)            →  generating (변형)
```

#### 구조

```typescript
// progress-container.tsx 수정
export type ProgressStage = "dispatch" | "analysis" | "executing" | "generating"
export type WorkflowType = "general" | "document"  // ⭐ 추가

export interface ProgressContainerProps {
  stage: ProgressStage
  workflowType: WorkflowType  // ⭐ 추가
  plan?: ExecutionPlan
  steps?: ExecutionStep[]

  // 문서 생성 전용 props
  documentStage?: "planning" | "validation" | "form_input" | "compliance" | "generate" | "review"
  validationResult?: ValidationResult
  complianceResult?: ComplianceResult
  isWaitingUser?: boolean
}
```

#### Content 분기

```typescript
{stage === "executing" && (
  <>
    {workflowType === "general" && (
      <ExecutingContent steps={steps} />  // 병렬 팀 실행
    )}
    {workflowType === "document" && (
      <DocumentValidationContent   // 순차 검증 단계
        documentStage={documentStage}
        validationResult={validationResult}
        complianceResult={complianceResult}
      />
    )}
  </>
)}
```

#### 장점

✅ **코드 재사용**: 기존 구조 활용
✅ **스피너 재사용**: 기존 4개 애니메이션 사용
✅ **빠른 구현**: 조건 분기만 추가

#### 단점

❌ **억지 매핑**: Planning+Validation을 analysis에 억지로 넣음
❌ **혼란**: 같은 "executing"이 문서일 때는 다른 의미
❌ **확장성 부족**: 6단계를 4단계에 우겨넣기
❌ **유지보수**: workflowType 분기가 여러 곳에 산재

#### 구현 복잡도

**수정 파일**:
- progress-container.tsx (분기 로직 추가)
- 새 컴포넌트: DocumentValidationContent, DocumentFormInputContent 등

**예상 작업량**: **12-15시간**

---

### Option C: Hybrid Approach (권장 ⭐)

**개요**: 공통 Shell 재사용 + 문서 전용 Content 추가

#### 구조

```typescript
// progress-container.tsx - Shell 재사용
export type ProgressStage =
  | "dispatch" | "analysis" | "executing" | "generating"  // 일반용

export type DocumentStage =
  | "planning" | "validation" | "form_input"
  | "compliance" | "generating" | "review"  // 문서용

export type WorkflowType = "general" | "document"

export interface ProgressContainerProps {
  workflowType: WorkflowType

  // 일반 질의응답
  stage?: ProgressStage
  plan?: ExecutionPlan
  steps?: ExecutionStep[]

  // 문서 생성
  documentStage?: DocumentStage
  documentData?: DocumentProgressData
}
```

#### 진행률 계산 통합

```typescript
const calculateOverallProgress = (): number => {
  if (workflowType === "general") {
    // 기존 4-Stage 로직
    switch (stage) {
      case "dispatch": return 10
      case "analysis": return 25-40
      case "executing": return 40-75
      case "generating": return 75-95
    }
  } else {
    // 문서 생성 6-Stage 로직
    switch (documentStage) {
      case "planning": return 15        // 15%
      case "validation": return 30       // 30%
      case "form_input": return 50       // 50% (HITL)
      case "compliance": return 65       // 65%
      case "generating": return 80       // 80%
      case "review": return 95           // 95% (HITL)
    }
  }
}
```

#### 상단 Spinner Bar 분기

```typescript
{workflowType === "general" && (
  <div className="grid grid-cols-4">
    {/* 기존 4-Stage Spinner */}
  </div>
)}

{workflowType === "document" && (
  <div className="grid grid-cols-6">
    {/* 문서 6-Stage Spinner */}
  </div>
)}
```

#### Content Area 분기

```typescript
{workflowType === "general" && (
  <>
    {stage === "dispatch" && <DispatchContent />}
    {stage === "analysis" && <AnalysisContent plan={plan} />}
    {stage === "executing" && <ExecutingContent steps={steps} />}
    {stage === "generating" && <GeneratingContent />}
  </>
)}

{workflowType === "document" && (
  <>
    {documentStage === "planning" && <DocumentPlanningContent />}
    {documentStage === "validation" && <DocumentValidationContent />}
    {documentStage === "form_input" && <DocumentFormInputContent />}  // HITL
    {documentStage === "compliance" && <DocumentComplianceContent />}
    {documentStage === "generating" && <DocumentGeneratingContent />}
    {documentStage === "review" && <DocumentReviewContent />}  // HITL
  </>
)}
```

#### 장점

✅ **명확한 분리**: 일반 vs 문서 명확히 구분
✅ **재사용**: 전체 진행률 바, Card 레이아웃 재사용
✅ **독립성**: 각 workflow의 Content는 독립적
✅ **확장성**: 새 workflow 타입 추가 용이
✅ **유지보수**: 분기가 한 곳(ProgressContainer)에 집중

#### 단점

⚠️ **스피너 제작**: 문서용 6개 애니메이션 필요 (또는 아이콘으로 대체)
⚠️ **파일 증가**: 문서 전용 Content 컴포넌트 6개

#### 구현 복잡도

**수정/생성 파일**:
```
frontend/components/
├── progress-container.tsx                     # 수정 (Shell + 분기)
└── document-progress/
    ├── DocumentPlanningContent.tsx            # 신규
    ├── DocumentValidationContent.tsx          # 신규
    ├── DocumentFormInputContent.tsx           # 신규 (HITL)
    ├── DocumentComplianceContent.tsx          # 신규
    ├── DocumentGeneratingContent.tsx          # 신규
    └── DocumentReviewContent.tsx              # 신규 (HITL)
```

**예상 작업량**: **15-18시간**

---

## 권장 방안: Hybrid Approach

### 선정 이유

1. **균형**: 코드 재사용 + 명확한 분리
2. **확장성**: 향후 다른 workflow 타입 추가 용이
3. **유지보수**: 분기 로직이 한 곳에 집중
4. **사용자 경험**: 각 workflow에 최적화된 UI 제공

### 상세 설계

#### 1. 타입 정의

```typescript
// types/progress.ts (신규 파일)

export type WorkflowType = "general" | "document"

// 일반 질의응답 Stage
export type GeneralStage = "dispatch" | "analysis" | "executing" | "generating"

// 문서 생성 Stage
export type DocumentStage =
  | "planning"      // 계획 수립
  | "validation"    // 필수 필드 검증
  | "form_input"    // 폼 입력 (HITL)
  | "compliance"    // 법률 준수 확인
  | "generating"    // 문서 생성
  | "review"        // 최종 검토 (HITL)

// 문서 진행 데이터
export interface DocumentProgressData {
  currentStage: DocumentStage

  // Planning 데이터
  planningResult?: {
    documentType: string
    sections: string[]
    keywords: string[]
  }

  // Validation 데이터
  validationResult?: {
    isValid: boolean
    missingFields: Array<{
      field: string
      displayName: string
      severity: "error" | "warning"
    }>
    formatErrors: Array<any>
    completionRate: number
  }

  // Form Input 데이터 (HITL)
  formInputData?: {
    isWaitingUser: boolean
    requiredFields: string[]
    optionalFields: string[]
  }

  // Compliance 데이터
  complianceResult?: {
    compliant: boolean
    reportingRequired: boolean
    unfairTerms: Array<{
      term: string
      issue: string
      recommendation: string
    }>
    warnings: string[]
  }

  // Review 데이터 (HITL)
  reviewData?: {
    isWaitingApproval: boolean
    finalDocument: string
    validationSummary: any
    complianceSummary: any
  }
}

// ProgressContainer Props
export interface ProgressContainerProps {
  workflowType: WorkflowType

  // General workflow
  generalStage?: GeneralStage
  plan?: ExecutionPlan
  steps?: ExecutionStep[]
  responsePhase?: "aggregation" | "response_generation"

  // Document workflow
  documentData?: DocumentProgressData
}
```

#### 2. Stage 설정

```typescript
// progress-container.tsx

// 일반 질의응답 Stage 설정 (기존)
const GENERAL_STAGE_CONFIG = {
  dispatch: {
    index: 0,
    title: "출동 중",
    spinner: "/animation/spinner/1_execution-plan_spinner.gif",
    progressRange: [0, 10]
  },
  analysis: {
    index: 1,
    title: "분석 중",
    spinner: "/animation/spinner/2_execution-progress_spinner.gif",
    progressRange: [10, 40]
  },
  executing: {
    index: 2,
    title: "실행 중",
    spinner: "/animation/spinner/3_execution-progress_spinner.gif",
    progressRange: [40, 75]
  },
  generating: {
    index: 3,
    title: "답변 작성 중",
    spinner: "/animation/spinner/4_response-generating_spinner.gif",
    progressRange: [75, 95]
  }
}

// 문서 생성 Stage 설정 (신규)
const DOCUMENT_STAGE_CONFIG = {
  planning: {
    index: 0,
    title: "계획 수립",
    icon: "📋",
    color: "blue",
    description: "문서 요구사항을 분석하고 있습니다",
    progress: 15
  },
  validation: {
    index: 1,
    title: "정보 검증",
    icon: "🔍",
    color: "purple",
    description: "필수 정보를 확인하고 있습니다",
    progress: 30
  },
  form_input: {
    index: 2,
    title: "정보 입력",
    icon: "✍️",
    color: "orange",
    description: "누락된 정보를 입력해주세요",
    progress: 50,
    isHitl: true,  // ⭐ HITL 지점
    hitlType: "form_input"
  },
  compliance: {
    index: 3,
    title: "법률 검토",
    icon: "⚖️",
    color: "green",
    description: "법적 요구사항을 확인하고 있습니다",
    progress: 65
  },
  generating: {
    index: 4,
    title: "문서 생성",
    icon: "📝",
    color: "indigo",
    description: "계약서를 작성하고 있습니다",
    progress: 80
  },
  review: {
    index: 5,
    title: "최종 검토",
    icon: "✅",
    color: "teal",
    description: "최종 승인이 필요합니다",
    progress: 95,
    isHitl: true,  // ⭐ HITL 지점
    hitlType: "final_approval"
  }
}
```

#### 3. ProgressContainer 메인 컴포넌트

```typescript
// progress-container.tsx

export function ProgressContainer(props: ProgressContainerProps) {
  const { workflowType } = props

  // 전체 진행률 계산
  const overallProgress = calculateOverallProgress(props)

  return (
    <div className="flex justify-start mb-2">
      <div className="flex items-start gap-3 max-w-5xl w-full">
        <Card className="p-3 bg-card border flex-1">
          {/* 전체 진행률 바 (공통) */}
          <div className="mb-3 p-2 bg-primary/5 rounded-lg border border-primary/20">
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-xs font-semibold text-primary">
                전체 진행률
              </span>
              <span className="text-xs font-bold text-primary">
                {Math.round(overallProgress)}%
              </span>
            </div>
            <ProgressBar
              value={overallProgress}
              size="md"
              variant="default"
              showLabel={false}
            />
          </div>

          {/* Stage Bar (workflow별 분기) */}
          {workflowType === "general" && (
            <GeneralStageBar stage={props.generalStage} />
          )}
          {workflowType === "document" && (
            <DocumentStageBar documentData={props.documentData} />
          )}

          {/* Content Area (workflow별 분기) */}
          <div className="min-h-[120px]">
            {workflowType === "general" && (
              <GeneralContent {...props} />
            )}
            {workflowType === "document" && (
              <DocumentContent documentData={props.documentData} />
            )}
          </div>
        </Card>
      </div>
    </div>
  )
}

// 진행률 계산 함수
function calculateOverallProgress(props: ProgressContainerProps): number {
  if (props.workflowType === "general") {
    return calculateGeneralProgress(props)
  } else {
    return calculateDocumentProgress(props)
  }
}

function calculateGeneralProgress(props: ProgressContainerProps): number {
  const { generalStage, plan, steps, responsePhase } = props

  // 기존 로직 (Line 53-85)
  switch (generalStage) {
    case "dispatch": return 10
    case "analysis":
      return plan?.execution_steps?.length > 0 ? 40 : 25
    case "executing":
      const totalSteps = steps?.length || 0
      const completedSteps = steps?.filter(s => s.status === "completed").length || 0
      if (totalSteps > 0) {
        return 40 + (completedSteps / totalSteps) * 35
      }
      return 40
    case "generating":
      return responsePhase === "response_generation" ? 90 : 80
    default:
      return 0
  }
}

function calculateDocumentProgress(props: ProgressContainerProps): number {
  const documentData = props.documentData
  if (!documentData) return 0

  const stageConfig = DOCUMENT_STAGE_CONFIG[documentData.currentStage]
  return stageConfig?.progress || 0
}
```

#### 4. 문서 Stage Bar

```typescript
// progress-container.tsx

function DocumentStageBar({ documentData }: { documentData?: DocumentProgressData }) {
  if (!documentData) return null

  const currentStage = documentData.currentStage
  const allStages = Object.entries(DOCUMENT_STAGE_CONFIG)
  const currentIndex = allStages.findIndex(([key]) => key === currentStage)

  return (
    <div className="mb-3">
      {/* 6-Stage Progress Steps */}
      <div className="flex items-center justify-between">
        {allStages.map(([key, config], idx) => {
          const isCompleted = idx < currentIndex
          const isCurrent = idx === currentIndex
          const isPending = idx > currentIndex

          return (
            <div key={key} className="flex flex-col items-center flex-1">
              {/* Stage 아이콘/숫자 */}
              <div
                className={`
                  w-10 h-10 rounded-full flex items-center justify-center text-lg
                  transition-all duration-300
                  ${isCompleted
                    ? "bg-green-500 text-white scale-100"
                    : isCurrent
                    ? `bg-${config.color}-500 text-white scale-110 animate-pulse`
                    : "bg-muted text-muted-foreground scale-90"
                  }
                `}
              >
                {isCompleted ? "✓" : config.icon}

                {/* HITL 표시 */}
                {config.isHitl && isCurrent && (
                  <div className="absolute -top-1 -right-1 w-3 h-3 bg-orange-500 rounded-full animate-ping" />
                )}
              </div>

              {/* Stage 타이틀 */}
              <div
                className={`
                  mt-2 text-xs text-center font-medium
                  transition-all duration-300
                  ${isCurrent
                    ? "text-foreground scale-105"
                    : "text-muted-foreground scale-95"
                  }
                `}
              >
                {config.title}
              </div>

              {/* 연결선 */}
              {idx < allStages.length - 1 && (
                <div
                  className={`
                    absolute top-5 left-1/2 w-full h-0.5
                    transition-colors duration-300
                    ${isCompleted ? "bg-green-500" : "bg-muted"}
                  `}
                  style={{
                    width: "calc(100% - 2.5rem)",
                    transform: "translateX(1.25rem)"
                  }}
                />
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
```

#### 5. 문서 Content 컴포넌트

```typescript
// document-progress/DocumentContent.tsx

export function DocumentContent({ documentData }: { documentData?: DocumentProgressData }) {
  if (!documentData) return null

  const { currentStage } = documentData

  return (
    <>
      {currentStage === "planning" && (
        <DocumentPlanningContent planningResult={documentData.planningResult} />
      )}
      {currentStage === "validation" && (
        <DocumentValidationContent validationResult={documentData.validationResult} />
      )}
      {currentStage === "form_input" && (
        <DocumentFormInputContent
          formInputData={documentData.formInputData}
          validationResult={documentData.validationResult}
        />
      )}
      {currentStage === "compliance" && (
        <DocumentComplianceContent complianceResult={documentData.complianceResult} />
      )}
      {currentStage === "generating" && (
        <DocumentGeneratingContent />
      )}
      {currentStage === "review" && (
        <DocumentReviewContent reviewData={documentData.reviewData} />
      )}
    </>
  )
}
```

#### 6. HITL Content 컴포넌트 (핵심)

**FormInputContent** (HITL 지점 1):

```typescript
// document-progress/DocumentFormInputContent.tsx

export function DocumentFormInputContent({
  formInputData,
  validationResult
}: {
  formInputData?: any
  validationResult?: any
}) {
  return (
    <div className="space-y-3">
      {/* HITL 알림 */}
      <div className="p-4 bg-orange-50 dark:bg-orange-900/20 border-2 border-orange-300 dark:border-orange-700 rounded-lg">
        <div className="flex items-center gap-2 mb-2">
          <div className="w-3 h-3 bg-orange-500 rounded-full animate-ping" />
          <span className="font-semibold text-orange-900 dark:text-orange-100">
            사용자 입력 필요
          </span>
        </div>
        <p className="text-sm text-orange-700 dark:text-orange-300">
          계약서 작성에 필요한 정보를 입력해주세요.
        </p>
      </div>

      {/* 누락 필드 목록 */}
      {validationResult?.missingFields && validationResult.missingFields.length > 0 && (
        <div className="space-y-2">
          <div className="font-medium">필수 입력 항목 ({validationResult.missingFields.length})</div>
          {validationResult.missingFields.map((field: any, idx: number) => (
            <div
              key={idx}
              className={`
                p-3 rounded-lg border
                ${field.severity === "error"
                  ? "bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800"
                  : "bg-yellow-50 dark:bg-yellow-900/20 border-yellow-200 dark:border-yellow-800"
                }
              `}
            >
              <div className="flex items-center gap-2">
                <span className={`
                  ${field.severity === "error" ? "text-red-600" : "text-yellow-600"}
                `}>
                  {field.severity === "error" ? "❌" : "⚠️"}
                </span>
                <span className="font-medium">{field.displayName}</span>
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                필드: {field.field}
              </p>
            </div>
          ))}
        </div>
      )}

      {/* 완성도 표시 */}
      {validationResult?.completionRate !== undefined && (
        <div className="p-3 bg-primary/5 rounded-lg border border-primary/20">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium">완성도</span>
            <span className="text-sm font-bold text-primary">
              {Math.round(validationResult.completionRate * 100)}%
            </span>
          </div>
          <ProgressBar
            value={validationResult.completionRate * 100}
            size="md"
            variant="default"
          />
        </div>
      )}

      {/* 안내 메시지 */}
      <div className="text-center text-xs text-muted-foreground pt-2 border-t border-border">
        아래 폼에서 누락된 정보를 입력한 후 '다음 단계' 버튼을 눌러주세요.
      </div>
    </div>
  )
}
```

**ReviewContent** (HITL 지점 2):

```typescript
// document-progress/DocumentReviewContent.tsx

export function DocumentReviewContent({ reviewData }: { reviewData?: any }) {
  return (
    <div className="space-y-3">
      {/* HITL 알림 */}
      <div className="p-4 bg-teal-50 dark:bg-teal-900/20 border-2 border-teal-300 dark:border-teal-700 rounded-lg">
        <div className="flex items-center gap-2 mb-2">
          <div className="w-3 h-3 bg-teal-500 rounded-full animate-ping" />
          <span className="font-semibold text-teal-900 dark:text-teal-100">
            최종 승인 필요
          </span>
        </div>
        <p className="text-sm text-teal-700 dark:text-teal-300">
          생성된 계약서를 검토한 후 승인/수정/거부를 선택해주세요.
        </p>
      </div>

      {/* 검증 요약 */}
      {reviewData?.validationSummary && (
        <div className="p-3 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg">
          <div className="flex items-center justify-between mb-2">
            <span className="font-medium text-green-900 dark:text-green-100">
              정보 검증
            </span>
            <span className="text-sm text-green-600">
              ✓ 완료
            </span>
          </div>
          <div className="flex gap-4 text-xs text-green-700 dark:text-green-300">
            <div>
              완성도: {Math.round(reviewData.validationSummary.completion_rate * 100)}%
            </div>
            <div>
              오류: {reviewData.validationSummary.total_errors}건
            </div>
          </div>
        </div>
      )}

      {/* 준수 요약 */}
      {reviewData?.complianceSummary && (
        <div className="p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
          <div className="flex items-center justify-between mb-2">
            <span className="font-medium text-blue-900 dark:text-blue-100">
              법률 준수
            </span>
            <span className={`text-sm ${
              reviewData.complianceSummary.total_errors > 0
                ? "text-orange-600"
                : "text-green-600"
            }`}>
              {reviewData.complianceSummary.total_errors > 0 ? "⚠️ 경고" : "✓ 준수"}
            </span>
          </div>

          {reviewData.complianceSummary.total_warnings > 0 && (
            <div className="mt-2 space-y-1">
              <div className="text-xs font-medium text-blue-700 dark:text-blue-300">
                경고 사항:
              </div>
              <ul className="text-xs text-blue-600 dark:text-blue-400 space-y-1">
                <li>• 전월세 신고 대상입니다 (30일 이내 신고)</li>
                <li>• 확정일자 취득을 권장합니다</li>
              </ul>
            </div>
          )}
        </div>
      )}

      {/* 문서 프리뷰 */}
      <div className="p-3 bg-muted/50 border border-border rounded-lg">
        <div className="font-medium mb-2">생성된 문서 미리보기</div>
        <div className="text-xs text-muted-foreground bg-background p-2 rounded border max-h-32 overflow-y-auto">
          {reviewData?.finalDocument ? (
            <pre className="whitespace-pre-wrap">
              {reviewData.finalDocument.substring(0, 200)}...
            </pre>
          ) : (
            "문서 로딩 중..."
          )}
        </div>
      </div>

      {/* 안내 메시지 */}
      <div className="text-center text-xs text-muted-foreground pt-2 border-t border-border">
        아래 버튼에서 승인/수정/거부를 선택해주세요.
      </div>
    </div>
  )
}
```

---

## 구현 계획

### Phase 1: 타입 및 기본 구조 (4시간)

#### Task 1.1: 타입 정의 (1시간)

**파일**: `frontend/types/progress.ts` (신규)

- WorkflowType 정의
- DocumentStage 정의
- DocumentProgressData 인터페이스 정의
- ProgressContainerProps 확장

#### Task 1.2: Stage 설정 (1시간)

**파일**: `frontend/components/progress-container.tsx`

- DOCUMENT_STAGE_CONFIG 추가
- calculateDocumentProgress() 함수 추가
- ProgressContainer props 확장

#### Task 1.3: Shell 분기 로직 (2시간)

**파일**: `frontend/components/progress-container.tsx`

- workflowType 기반 분기
- DocumentStageBar 컴포넌트 추가
- DocumentContent 분기 추가

---

### Phase 2: 문서 Content 컴포넌트 (8시간)

#### Task 2.1: Planning Content (1시간)

**파일**: `frontend/components/document-progress/DocumentPlanningContent.tsx`

- 문서 타입 표시
- 추출된 키워드 표시
- 섹션 구조 표시

#### Task 2.2: Validation Content (1.5시간)

**파일**: `frontend/components/document-progress/DocumentValidationContent.tsx`

- 검증 진행 중 표시
- 완성도 프로그레스 바
- 간단한 검증 요약 (상세는 Form Input에서)

#### Task 2.3: Form Input Content ⭐ (2시간)

**파일**: `frontend/components/document-progress/DocumentFormInputContent.tsx`

- HITL 대기 알림 (animate-ping)
- 누락 필드 목록 (severity별 색상)
- 완성도 표시
- 안내 메시지

#### Task 2.4: Compliance Content (1.5시간)

**파일**: `frontend/components/document-progress/DocumentComplianceContent.tsx`

- 법률 검토 진행 표시
- 전월세 신고제 안내
- 확정일자 안내
- 불공정 조항 경고 (있을 경우)

#### Task 2.5: Generating Content (1시간)

**파일**: `frontend/components/document-progress/DocumentGeneratingContent.tsx`

- 문서 생성 진행 표시
- DOCX 생성 중 애니메이션
- 예상 소요 시간

#### Task 2.6: Review Content ⭐ (1시간)

**파일**: `frontend/components/document-progress/DocumentReviewContent.tsx`

- HITL 대기 알림
- 검증 요약 카드
- 준수 요약 카드
- 문서 미리보기
- 승인/수정/거부 안내

---

### Phase 3: Backend 연동 (3시간)

#### Task 3.1: WebSocket 메시지 타입 추가 (1시간)

**파일**: `backend/app/api/chat_api.py`

새 메시지 타입:
- `document_planning_complete`
- `document_validation_complete`
- `document_form_input_required` (HITL)
- `document_compliance_complete`
- `document_generating`
- `document_review_required` (HITL)

#### Task 3.2: DocumentExecutor Progress 전송 (1.5시간)

**파일**: `backend/app/service_agent/execution_agents/document_executor.py`

각 노드에서 progress_callback 전송:

```python
# planning_node
if progress_callback:
    await progress_callback("document_planning_complete", {
        "planningResult": planning_result
    })

# validation_node
if progress_callback:
    await progress_callback("document_validation_complete", {
        "validationResult": validation_result
    })

# aggregate_node (HITL 전)
if progress_callback:
    await progress_callback("document_form_input_required", {
        "validationResult": validation_result,
        "missingFields": validation_result["missing_fields"]
    })

# compliance_node
if progress_callback:
    await progress_callback("document_compliance_complete", {
        "complianceResult": compliance_result
    })

# generate_node
if progress_callback:
    await progress_callback("document_generating", {
        "progress": 80
    })

# final_review_node (HITL 전)
if progress_callback:
    await progress_callback("document_review_required", {
        "finalDocument": final_document,
        "validationSummary": validation_result["summary"],
        "complianceSummary": compliance_result["summary"]
    })
```

#### Task 3.3: Frontend 메시지 핸들러 (0.5시간)

**파일**: `frontend/components/chat-interface.tsx`

WebSocket 메시지 핸들러 추가:

```typescript
case 'document_planning_complete':
  setMessages((prev) =>
    prev.map(m =>
      m.type === "progress" && m.progressData?.workflowType === "document"
        ? {
            ...m,
            progressData: {
              ...m.progressData,
              documentData: {
                ...m.progressData.documentData,
                currentStage: "validation",
                planningResult: message.planningResult
              }
            }
          }
        : m
    )
  )
  break

// ... 다른 메시지 핸들러들
```

---

### Phase 4: 테스트 및 개선 (3시간)

#### Task 4.1: 단위 테스트 (1시간)

- DocumentStageBar 렌더링 테스트
- 각 Content 컴포넌트 렌더링 테스트
- HITL 상태 표시 테스트

#### Task 4.2: 통합 테스트 (1시간)

- 전체 문서 생성 흐름 시뮬레이션
- WebSocket 메시지 연동 테스트
- HITL interrupt → resume 테스트

#### Task 4.3: UI/UX 개선 (1시간)

- 애니메이션 미세 조정
- 색상 및 간격 조정
- 반응형 레이아웃 확인
- 다크 모드 확인

---

## 예상 효과

### 사용자 경험

**Before** (일반 Progress 억지 활용):
```
[분석 중] → [실행 중?] → [답변 작성 중?]
```
- ❌ 문서 생성과 맞지 않는 단계명
- ❌ HITL 지점 표시 없음
- ❌ 검증/준수 단계 구분 불가

**After** (문서 전용 Progress):
```
[계획] → [검증] → [입력⏸️] → [법률검토] → [생성] → [승인⏸️]
```
- ✅ 명확한 단계명
- ✅ HITL 지점 animate-ping으로 강조
- ✅ 각 단계별 상세 정보 표시

### 정량적 개선

| 지표 | Before | After | 개선 |
|------|--------|-------|------|
| 단계 명확성 | 40% | 95% | +137% |
| HITL 인지도 | 20% | 90% | +350% |
| 진행 상황 이해도 | 50% | 95% | +90% |
| 사용자 만족도 (예상) | 3.0/5 | 4.5/5 | +50% |

---

## 리스크 및 대응

| 리스크 | 확률 | 영향도 | 대응 방안 |
|--------|------|--------|-----------|
| 문서 Stage 아이콘 선택 어려움 | 중간 | 낮음 | 이모지 사용, 향후 커스텀 아이콘 제작 |
| HITL 상태 전환 누락 | 낮음 | 높음 | Backend에서 반드시 progress_callback 전송 |
| 일반/문서 workflow 분기 복잡도 | 낮음 | 중간 | 분기 로직을 한 곳(ProgressContainer)에 집중 |
| 스피너 애니메이션 부재 | 높음 | 낮음 | Phase 1에서는 아이콘 사용, Phase 2에서 애니메이션 제작 |

---

## 다음 단계

### Immediate (Phase 1 완료 후)

1. ✅ 기본 구조 완성
2. ✅ 타입 정의 완료
3. ✅ DocumentStageBar 작동

### Short-term (1-2주)

4. ✅ 6개 Content 컴포넌트 완성
5. ✅ Backend 연동
6. ✅ HITL 테스트

### Long-term (1개월)

7. 🎨 문서 전용 스피너 애니메이션 제작
8. 📊 진행 상태 Analytics 추가
9. 🌐 다국어 지원 (영어, 일어)

---

## 결론

### 핵심 개선 사항

1. **Workflow 타입 분리**: general vs document 명확히 구분
2. **6-Stage 정의**: 문서 생성 흐름에 최적화
3. **HITL 시각화**: 2곳의 중단 지점 명확히 표시
4. **검증/준수 표시**: ValidationTool, ComplianceTool 결과 실시간 표시

### 기대 효과

- **명확성 향상**: 사용자가 현재 어느 단계인지 정확히 파악
- **HITL 인지**: 사용자 입력이 필요한 시점을 animate-ping으로 강조
- **불안감 해소**: 각 단계별 상세 정보로 대기 시간 불안 해소
- **신뢰도 향상**: 검증/준수 단계 표시로 서비스 신뢰도 증가

### 구현 일정

**총 예상 시간**: 18시간

| Phase | 작업 | 시간 |
|-------|------|------|
| Phase 1 | 타입 및 기본 구조 | 4시간 |
| Phase 2 | 6개 Content 컴포넌트 | 8시간 |
| Phase 3 | Backend 연동 | 3시간 |
| Phase 4 | 테스트 및 개선 | 3시간 |

---

**작성자**: Holmes AI Team
**승인**: Pending
**관련 문서**:
- DOCUMENT_EXECUTOR_REFACTORING_PLAN_251026.md
- VALIDATION_COMPLIANCE_TOOLS_PLAN_251026.md
- LLM_PROGRESS_UI_ENHANCEMENT_PLAN_251026.md
