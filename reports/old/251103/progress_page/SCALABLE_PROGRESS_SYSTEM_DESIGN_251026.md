# 확장 가능한 Progress System 설계 계획서

**작성일**: 2025-10-26
**목적**: Agent 수 증가에 대응하는 확장 가능한 Progress UI 아키텍처 설계
**핵심 질문**:
1. 각 Agent마다 다른 workflow를 어떻게 처리할 것인가?
2. Agent가 10개, 20개로 증가하면 어떻게 대응할 것인가?
3. 일반 답변 Progress 타이밍이 적절한가?

---

## 📋 목차

1. [문제 정의](#문제-정의)
2. [현재 시스템 분석](#현재-시스템-분석)
3. [확장성 문제](#확장성-문제)
4. [설계 방안 비교](#설계-방안-비교)
5. [권장 방안: 3-Layer Architecture](#권장-방안-3-layer-architecture)
6. [타이밍 분석 및 개선](#타이밍-분석-및-개선)
7. [구현 계획](#구현-계획)

---

## 문제 정의

### 핵심 질문

**Q1. 각 Agent마다 다른 workflow**
- Document Agent: Planning → Validation → FormInput(HITL) → Compliance → Generate → Review(HITL)
- Search Agent: Query → Search → Filter → Aggregate
- Analysis Agent: Load → Analyze → Validate → Report
- 향후 추가될 Agent들: 각각 다른 단계 수, 다른 HITL 지점

**Q2. Agent 수 증가**
```
현재 (3개)              향후 (10+개)
─────────────          ─────────────────────────
Search                 Search
Document               Document
Analysis               Analysis
                       ContractReview
                       LegalConsultation
                       PropertyInspection
                       LoanCalculation
                       TaxPlanning
                       MarketAnalysis
                       RiskAssessment
                       ...
```

**Q3. Progress 타이밍**
- 현재: dispatch → analysis → executing → generating
- 각 단계 전환 타이밍이 적절한가?
- 사용자가 진행 상황을 정확히 파악하는가?

### 문제점 요약

1. ❌ **확장성 없음**: 각 Agent마다 새 Progress 컴포넌트 만들면 유지보수 불가능
2. ❌ **일관성 부족**: Agent마다 다른 단계명, 다른 아이콘, 다른 진행률 계산
3. ❌ **중복 코드**: 비슷한 Progress 로직이 여러 곳에 산재
4. ❌ **타이밍 불명확**: "실행 중"이 구체적으로 무엇을 하는지 모호

---

## 현재 시스템 분석

### Agent별 Workflow 비교

| Agent | 단계 수 | 주요 단계 | HITL | 병렬/순차 |
|-------|--------|----------|------|----------|
| **Search** | 4-5단계 | Query → Search → Filter → Aggregate | 없음 | 병렬 가능 (여러 소스) |
| **Document** | 6단계 | Planning → Validation → FormInput → Compliance → Generate → Review | 2곳 | 순차 |
| **Analysis** | 4-5단계 | Load → Analyze → Validate → Report | 없음 | 순차 |

### 현재 Progress 구조 (General)

```
[출동 중 10%]
    ↓
[분석 중 25-40%]  ← Planning Agent 의도 분석
    ↓
[실행 중 40-75%]  ← 여러 Team 병렬 실행
    ↓              (Search, Document, Analysis)
[답변 작성 75-95%] ← LLM 최종 응답 생성
```

**문제점**:
1. "실행 중"이 구체적으로 뭘 하는지 모호
2. 병렬 실행 중 어느 Team이 진행 중인지만 표시
3. Document Team이 실행되면 6단계가 "실행 중" 하나에 뭉개짐

### 향후 Agent 추가 시나리오

```python
# team_supervisor.py
self.teams = {
    "search": SearchExecutor(),
    "document": DocumentExecutor(),
    "analysis": AnalysisExecutor(),
    "contract_review": ContractReviewExecutor(),      # 신규
    "legal_consult": LegalConsultationExecutor(),     # 신규
    "property_inspect": PropertyInspectionExecutor(), # 신규
    "loan_calc": LoanCalculationExecutor(),           # 신규
    "tax_plan": TaxPlanningExecutor(),                # 신규
    # ... 계속 증가
}
```

각 Agent가 다른 workflow를 가질 경우:
- ❌ Agent별 Progress 컴포넌트 10개 제작?
- ❌ ProgressContainer에 10개 분기?
- ❌ 유지보수 불가능

---

## 확장성 문제

### Scenario 1: Agent별 맞춤 Progress (현재 방식)

```typescript
// ❌ 확장 불가능한 방식
type WorkflowType =
  | "general"
  | "document"
  | "contract_review"      // 신규
  | "legal_consult"        // 신규
  | "property_inspect"     // 신규
  | "loan_calc"            // 신규
  // ... 10개 더 추가?

// progress-container.tsx
{workflowType === "general" && <GeneralContent />}
{workflowType === "document" && <DocumentContent />}
{workflowType === "contract_review" && <ContractReviewContent />}
{workflowType === "legal_consult" && <LegalConsultContent />}
{workflowType === "property_inspect" && <PropertyInspectContent />}
// ... 10개 더 분기?
```

**문제**:
- Agent 추가마다 새 컴포넌트 제작
- 분기 로직 계속 증가
- 일관성 없음 (각각 다른 디자인)
- 유지보수 복잡도 O(N)

### Scenario 2: 공통 Phase 강제 (너무 엄격)

```typescript
// ❌ 모든 Agent가 동일한 4단계 강제
const COMMON_PHASES = {
  prepare: "준비 중",
  execute: "실행 중",
  validate: "검증 중",
  finalize: "완료 중"
}

// Document Agent를 억지로 4단계에 맞춤
Planning → prepare
Validation, FormInput, Compliance → execute (3단계를 1단계에 우겨넣기)
Generate → validate
Review → finalize
```

**문제**:
- Agent의 고유한 workflow 무시
- 세부 진행 상태 손실
- HITL 지점 표시 불가
- 사용자 혼란

---

## 설계 방안 비교

### Option A: Agent별 맞춤 Progress (현재)

**구조**:
- 각 Agent마다 완전히 다른 Progress 컴포넌트
- WorkflowType enum에 Agent 이름 추가
- ProgressContainer에서 분기

**장점**:
✅ Agent별 최적화 가능
✅ 디자인 자유도 높음

**단점**:
❌ 확장성 0점
❌ Agent 10개면 컴포넌트 10개
❌ 중복 코드 대량 발생
❌ 일관성 없음

**평가**: ⭐☆☆☆☆ (현재 3개까지만 가능)

---

### Option B: Generic Phase System

**구조**:
- 모든 Agent가 따라야 하는 공통 Phase 정의
- 각 Agent는 자신의 workflow를 Phase에 매핑

**예시**:

```typescript
// 공통 Phase (모든 Agent 공통)
const UNIVERSAL_PHASES = {
  initialize: { title: "초기화", progress: 10 },
  prepare: { title: "준비", progress: 30 },
  execute: { title: "실행", progress: 60 },
  finalize: { title: "완료", progress: 90 }
}

// Agent별 매핑
DocumentAgent:
  Planning → initialize
  Validation, FormInput → prepare
  Compliance, Generate → execute
  Review → finalize

SearchAgent:
  Query → initialize
  Search, Filter → execute
  Aggregate → finalize
```

**장점**:
✅ 확장 가능 (Agent 무제한)
✅ 일관된 UI
✅ 단순한 구조

**단점**:
❌ Agent 고유 workflow 손실
❌ HITL 지점 표시 어려움
❌ 세부 진행 상태 부정확
❌ "실행" 단계가 여전히 모호

**평가**: ⭐⭐☆☆☆ (확장은 되지만 정보 손실)

---

### Option C: Flexible Step System

**구조**:
- Agent가 자신의 Step을 동적으로 정의
- Progress는 Step 목록과 현재 Step만 표시
- Generic하게 처리

**예시**:

```typescript
// Backend에서 전송
{
  "type": "agent_progress",
  "agent": "document",
  "steps": [
    { "id": "planning", "name": "계획 수립", "status": "completed" },
    { "id": "validation", "name": "정보 검증", "status": "completed" },
    { "id": "form_input", "name": "정보 입력", "status": "in_progress", "isHitl": true },
    { "id": "compliance", "name": "법률 검토", "status": "pending" },
    { "id": "generate", "name": "문서 생성", "status": "pending" },
    { "id": "review", "name": "최종 검토", "status": "pending", "isHitl": true }
  ],
  "currentStep": 2,
  "totalSteps": 6
}

// Frontend는 Generic하게 표시
<StepList steps={steps} currentStep={currentStep} />
```

**장점**:
✅ 완전한 확장성 (Agent가 자유롭게 정의)
✅ Agent 고유 workflow 보존
✅ HITL 지점 명확히 표시
✅ 세부 진행 상태 정확
✅ Agent 추가 시 코드 변경 불필요

**단점**:
⚠️ UI 디자인 제약 (Generic해야 함)
⚠️ Agent별 커스터마이징 어려움

**평가**: ⭐⭐⭐⭐☆ (확장성 우수, 약간의 제약)

---

### Option D: 3-Layer Architecture (권장 ⭐⭐⭐⭐⭐)

**구조**:
- **Layer 1 (Supervisor)**: 공통 Phase (4단계)
- **Layer 2 (Agent)**: Agent별 세부 Step (동적)
- **Layer 3 (Task)**: Step 내부 세부 작업 (선택)

**예시**:

```
┌─────────────────────────────────────────────────┐
│ Layer 1: Supervisor Phase (공통)                │
│ [분석 25%] → [실행 40-75%] → [완료 75-95%]      │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│ Layer 2: Agent Steps (동적)                     │
│ Document Agent의 "실행" Phase 내부:              │
│ [검증✓] → [입력⏸️] → [법률검토●] → [생성○] → [승인○] │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│ Layer 3: Task Details (선택)                    │
│ "법률검토" Step 내부:                            │
│ • 임대 기간 확인 ✓                               │
│ • 전월세 신고제 확인 ●                           │
│ • 불공정 조항 탐지 ○                             │
└─────────────────────────────────────────────────┘
```

**장점**:
✅ **확장성**: Agent 무제한 추가 가능
✅ **일관성**: Layer 1으로 전체 흐름 통일
✅ **유연성**: Layer 2로 Agent 고유성 보존
✅ **세밀함**: Layer 3으로 상세 진행 표시 가능
✅ **HITL 표시**: Layer 2에서 명확히 표시
✅ **기존 호환**: 현재 4-Stage를 Layer 1로 유지

**단점**:
⚠️ 구조 복잡도 증가 (3-Layer 관리)
⚠️ Backend-Frontend 연동 복잡

**평가**: ⭐⭐⭐⭐⭐ (최적 균형)

---

## 권장 방안: 3-Layer Architecture

### 설계 상세

#### Layer 1: Supervisor Phase (공통)

**목적**: 전체 프로세스의 큰 흐름 표시 (사용자에게 "지금 어디쯤인가" 감각 제공)

```typescript
// Supervisor Level - 모든 query 공통
const SUPERVISOR_PHASES = {
  dispatching: {
    title: "접수",
    range: [0, 10],
    description: "질문을 접수하고 있습니다"
  },
  analyzing: {
    title: "분석",
    range: [10, 30],
    description: "질문을 분석하고 계획을 수립하고 있습니다"
  },
  executing: {
    title: "실행",
    range: [30, 75],
    description: "작업을 실행하고 있습니다"  // ⭐ 여기서 Agent Step 표시
  },
  finalizing: {
    title: "완료",
    range: [75, 100],
    description: "결과를 정리하고 있습니다"
  }
}
```

**표시 방식**:
```
┌─────────────────────────────────────┐
│ 전체 진행률: ████████░░ 65%         │
│                                     │
│ [접수✓] → [분석✓] → [실행●] → [완료○] │
└─────────────────────────────────────┘
```

#### Layer 2: Agent Steps (동적)

**목적**: 현재 실행 중인 Agent의 세부 단계 표시

```typescript
// Backend가 동적으로 전송
interface AgentStep {
  id: string
  name: string
  status: "pending" | "in_progress" | "completed" | "failed"
  isHitl?: boolean
  hitlType?: "form_input" | "approval" | "review"
  progress?: number  // 0-100
  metadata?: any
}

// Document Agent 예시
const documentSteps: AgentStep[] = [
  { id: "planning", name: "계획 수립", status: "completed" },
  { id: "validation", name: "정보 검증", status: "completed" },
  { id: "form_input", name: "정보 입력", status: "in_progress", isHitl: true, hitlType: "form_input" },
  { id: "compliance", name: "법률 검토", status: "pending" },
  { id: "generate", name: "문서 생성", status: "pending" },
  { id: "review", name: "최종 검토", status: "pending", isHitl: true, hitlType: "approval" }
]

// Search Agent 예시 (다른 구조)
const searchSteps: AgentStep[] = [
  { id: "query", name: "검색 쿼리 생성", status: "completed" },
  { id: "search", name: "데이터 검색", status: "completed" },
  { id: "filter", name: "결과 필터링", status: "in_progress", progress: 60 },
  { id: "aggregate", name: "결과 집계", status: "pending" }
]
```

**표시 방식**:
```
┌─────────────────────────────────────┐
│ 실행 중: Document Agent             │
│                                     │
│ ✓ 계획 수립                         │
│ ✓ 정보 검증                         │
│ ● 정보 입력 (사용자 입력 대기) ⏸️   │
│ ○ 법률 검토                         │
│ ○ 문서 생성                         │
│ ○ 최종 검토 ⏸️                      │
│                                     │
│ Step 3/6 (50%)                      │
└─────────────────────────────────────┘
```

#### Layer 3: Task Details (선택)

**목적**: Step 내부의 세부 작업 표시 (필요시만)

```typescript
// Step이 복잡한 경우 내부 Task 표시
interface Task {
  id: string
  name: string
  status: "pending" | "in_progress" | "completed"
}

// "법률 검토" Step의 내부 Tasks
const complianceTasks: Task[] = [
  { id: "lease_period", name: "임대 기간 확인", status: "completed" },
  { id: "reporting", name: "전월세 신고제 확인", status: "in_progress" },
  { id: "unfair_terms", name: "불공정 조항 탐지", status: "pending" }
]
```

**표시 방식** (확장 가능한 Step):
```
┌─────────────────────────────────────┐
│ ● 법률 검토 (진행 중)                │
│   ├─ ✓ 임대 기간 확인                │
│   ├─ ● 전월세 신고제 확인 (60%)      │
│   └─ ○ 불공정 조항 탐지              │
└─────────────────────────────────────┘
```

### 통합 Progress UI

```
┌──────────────────────────────────────────────┐
│ 전체 진행률: ███████████░░ 65%               │
├──────────────────────────────────────────────┤
│ Layer 1: Supervisor Phase                   │
│ [접수✓] → [분석✓] → [실행●] → [완료○]        │
├──────────────────────────────────────────────┤
│ Layer 2: Agent Steps                        │
│ 실행 중: Document Agent                      │
│                                              │
│ ✓ 계획 수립                                  │
│ ✓ 정보 검증                                  │
│ ● 정보 입력 ⏸️                               │
│   ┌──────────────────────────────────┐      │
│   │ 🔴 사용자 입력 필요               │      │
│   │ 누락 필드 3개 입력해주세요         │      │
│   │ • 임대인 연락처                   │      │
│   │ • 전용면적                        │      │
│   │ • 계약 시작일                     │      │
│   └──────────────────────────────────┘      │
│ ○ 법률 검토                                  │
│ ○ 문서 생성                                  │
│ ○ 최종 검토 ⏸️                               │
│                                              │
│ Step 3/6 (50%)                               │
└──────────────────────────────────────────────┘
```

### Backend 데이터 구조

```python
# team_supervisor.py
async def execute_teams_node(self, state: MainSupervisorState):
    """Layer 1 Phase: executing"""

    # Layer 2: Agent별 Step 정보 전송
    if progress_callback:
        await progress_callback("agent_steps_update", {
            "supervisorPhase": "executing",
            "supervisorProgress": 50,
            "activeAgent": "document",
            "agentSteps": [
                {"id": "planning", "name": "계획 수립", "status": "completed"},
                {"id": "validation", "name": "정보 검증", "status": "completed"},
                {"id": "form_input", "name": "정보 입력", "status": "in_progress", "isHitl": True},
                {"id": "compliance", "name": "법률 검토", "status": "pending"},
                {"id": "generate", "name": "문서 생성", "status": "pending"},
                {"id": "review", "name": "최종 검토", "status": "pending", "isHitl": True}
            ],
            "currentStepIndex": 2,
            "totalSteps": 6
        })
```

```python
# document_executor.py
async def validation_node(self, state):
    """Agent Step 진행 시 Step 상태 업데이트 전송"""

    if progress_callback:
        await progress_callback("agent_step_progress", {
            "agent": "document",
            "stepId": "validation",
            "status": "in_progress",
            "progress": 50  # 선택적
        })

    # Validation 실행
    validation_result = self.validation_tool.validate(contract_data)

    if progress_callback:
        await progress_callback("agent_step_complete", {
            "agent": "document",
            "stepId": "validation",
            "status": "completed",
            "result": validation_result
        })
```

---

## 타이밍 분석 및 개선

### 현재 일반 답변 Progress 타이밍

```
사용자 질문 입력
    ↓
[출동 중 10%]              ← 즉시 표시 (0초)
    ↓
[분석 중 25%]              ← planning_start (0.5초)
    ↓
[분석 중 40%]              ← plan_ready (2-3초)
    ↓
[실행 중 40%]              ← execution_start (3초)
    ↓
[실행 중 50%]              ← todo_updated (4-8초, 실시간)
[실행 중 60%]
[실행 중 70%]
    ↓
[답변 작성 중 80%]         ← response_generating_start (8-10초)
    ↓
[답변 작성 중 90%]         ← response_generating_progress (10-18초)
    ↓
완료                       ← final_response (20초)
```

### 타이밍 평가

| Phase | 시작 타이밍 | 소요 시간 | 평가 |
|-------|-----------|----------|------|
| 출동 중 | 즉시 | <1초 | ✅ 적절 |
| 분석 중 | 0.5초 | 2-3초 | ✅ 적절 |
| 실행 중 | 3초 | 5-7초 | ⚠️ 너무 긴 구간 (40-75%) |
| 답변 작성 중 | 8-10초 | 8-10초 | ❌ 중간 진행 상태 부족 |

### 문제점

1. **"실행 중" 구간이 너무 길다** (5-7초)
   - 여러 Agent가 병렬 실행되지만 개별 진행 상태가 명확하지 않음
   - 40% → 75% 구간에서 변화가 적음

2. **"답변 작성 중" 구간 정체** (8-10초)
   - 이미 LLM_PROGRESS_UI_ENHANCEMENT_PLAN에서 다룸
   - 5단계로 세분화 필요

### 개선 방안 (3-Layer 적용)

```
[Layer 1: 출동 10%]
    ↓
[Layer 1: 분석 25-30%]
│ ├─ 의도 분석
│ └─ 계획 수립
    ↓
[Layer 1: 실행 30-75%] ⭐ 여기가 핵심
│ Layer 2: Search Agent
│ ├─ ● 검색 쿼리 생성 (35%)
│ ├─ ● 데이터 검색 (50%)
│ ├─ ● 결과 필터링 (60%)
│ └─ ○ 결과 집계
│
│ Layer 2: Document Agent
│ ├─ ✓ 계획 수립
│ ├─ ✓ 정보 검증
│ ├─ ● 정보 입력 ⏸️ (HITL)
│ └─ ○ ...
    ↓
[Layer 1: 완료 75-100%]
│ ├─ 정보 정리 (80%)
│ ├─ LLM 답변 생성 (85-90%)
│ └─ 대화 저장 (92-95%)
```

**개선 효과**:
- ✅ "실행 중" 구간에서 개별 Agent 진행 상태 표시
- ✅ 병렬 실행 시각화 (여러 Agent 카드 동시 표시)
- ✅ 사용자가 "지금 뭘 하고 있는지" 정확히 파악

---

## 구현 계획

### Phase 1: 3-Layer 기본 구조 (6시간)

#### Task 1.1: 타입 정의 (1.5시간)

```typescript
// types/progress.ts

// Layer 1: Supervisor Phase
export type SupervisorPhase = "dispatching" | "analyzing" | "executing" | "finalizing"

export interface SupervisorPhaseConfig {
  title: string
  range: [number, number]
  description: string
}

// Layer 2: Agent Step
export interface AgentStep {
  id: string
  name: string
  status: "pending" | "in_progress" | "completed" | "failed" | "skipped"
  isHitl?: boolean
  hitlType?: "form_input" | "approval" | "review"
  progress?: number  // 0-100
  estimatedTime?: number  // seconds
  metadata?: Record<string, any>
}

export interface AgentProgress {
  agentName: string
  agentType: string  // "search" | "document" | "analysis" | ...
  steps: AgentStep[]
  currentStepIndex: number
  totalSteps: number
  overallProgress: number  // 0-100
}

// Layer 3: Task Detail (선택적)
export interface TaskDetail {
  id: string
  name: string
  status: "pending" | "in_progress" | "completed"
  progress?: number
}

// 통합 Progress Data
export interface ThreeLayerProgressData {
  // Layer 1
  supervisorPhase: SupervisorPhase
  supervisorProgress: number  // 0-100

  // Layer 2
  activeAgents: AgentProgress[]  // 현재 실행 중인 Agent들

  // Layer 3 (선택)
  expandedStepId?: string
  taskDetails?: TaskDetail[]
}
```

#### Task 1.2: ProgressContainer 리팩토링 (2.5시간)

```typescript
// components/progress-container.tsx

export interface ProgressContainerProps {
  progressData: ThreeLayerProgressData
}

export function ProgressContainer({ progressData }: ProgressContainerProps) {
  const {
    supervisorPhase,
    supervisorProgress,
    activeAgents
  } = progressData

  return (
    <Card className="p-3">
      {/* Layer 1: Supervisor Progress Bar */}
      <SupervisorProgressBar
        phase={supervisorPhase}
        progress={supervisorProgress}
      />

      {/* Layer 2: Agent Steps (현재 실행 중인 Agent들) */}
      {activeAgents && activeAgents.length > 0 && (
        <div className="mt-3 space-y-2">
          {activeAgents.map(agent => (
            <AgentStepsCard key={agent.agentName} agentProgress={agent} />
          ))}
        </div>
      )}
    </Card>
  )
}
```

#### Task 1.3: Layer 1 컴포넌트 (1시간)

```typescript
// components/progress/SupervisorProgressBar.tsx

const SUPERVISOR_PHASES: Record<SupervisorPhase, SupervisorPhaseConfig> = {
  dispatching: {
    title: "접수",
    range: [0, 10],
    description: "질문을 접수하고 있습니다"
  },
  analyzing: {
    title: "분석",
    range: [10, 30],
    description: "질문을 분석하고 계획을 수립하고 있습니다"
  },
  executing: {
    title: "실행",
    range: [30, 75],
    description: "작업을 실행하고 있습니다"
  },
  finalizing: {
    title: "완료",
    range: [75, 100],
    description: "결과를 정리하고 있습니다"
  }
}

export function SupervisorProgressBar({
  phase,
  progress
}: {
  phase: SupervisorPhase
  progress: number
}) {
  const allPhases = Object.entries(SUPERVISOR_PHASES)
  const currentPhaseIndex = allPhases.findIndex(([key]) => key === phase)

  return (
    <div>
      {/* 전체 진행률 바 */}
      <div className="mb-3 p-2 bg-primary/5 rounded-lg">
        <div className="flex justify-between mb-1">
          <span className="text-xs font-semibold">전체 진행률</span>
          <span className="text-xs font-bold">{Math.round(progress)}%</span>
        </div>
        <ProgressBar value={progress} />
      </div>

      {/* 4-Phase Steps */}
      <div className="grid grid-cols-4 gap-2">
        {allPhases.map(([key, config], idx) => {
          const isCompleted = idx < currentPhaseIndex
          const isCurrent = idx === currentPhaseIndex
          const isPending = idx > currentPhaseIndex

          return (
            <div
              key={key}
              className={`
                p-2 rounded-lg border text-center
                ${isCompleted
                  ? "bg-green-50 border-green-200"
                  : isCurrent
                  ? "bg-primary/10 border-primary"
                  : "bg-muted border-muted-foreground/20"
                }
              `}
            >
              <div className="text-lg mb-1">
                {isCompleted ? "✓" : isCurrent ? "●" : "○"}
              </div>
              <div className="text-xs font-medium">{config.title}</div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
```

#### Task 1.4: Layer 2 컴포넌트 (1시간)

```typescript
// components/progress/AgentStepsCard.tsx

export function AgentStepsCard({ agentProgress }: { agentProgress: AgentProgress }) {
  const { agentName, agentType, steps, currentStepIndex } = agentProgress

  return (
    <Card className="p-3 bg-secondary/20">
      {/* Agent 헤더 */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <AgentIcon type={agentType} />
          <span className="font-semibold">{agentName}</span>
        </div>
        <span className="text-xs text-muted-foreground">
          Step {currentStepIndex + 1}/{steps.length}
        </span>
      </div>

      {/* Step 목록 */}
      <div className="space-y-1">
        {steps.map((step, idx) => (
          <StepRow
            key={step.id}
            step={step}
            isActive={idx === currentStepIndex}
          />
        ))}
      </div>
    </Card>
  )
}

function StepRow({ step, isActive }: { step: AgentStep; isActive: boolean }) {
  const statusIcon = {
    pending: "○",
    in_progress: "●",
    completed: "✓",
    failed: "✗",
    skipped: "⊘"
  }[step.status]

  return (
    <div
      className={`
        flex items-center gap-2 p-2 rounded
        ${isActive ? "bg-primary/10 border border-primary" : "bg-muted/50"}
      `}
    >
      <span className="text-lg">{statusIcon}</span>
      <span className="flex-1 text-sm">{step.name}</span>

      {/* HITL 표시 */}
      {step.isHitl && step.status === "in_progress" && (
        <div className="flex items-center gap-1">
          <div className="w-2 h-2 bg-orange-500 rounded-full animate-ping" />
          <span className="text-xs text-orange-600">입력 대기</span>
        </div>
      )}

      {/* 진행률 (있을 경우) */}
      {step.status === "in_progress" && step.progress !== undefined && (
        <div className="w-16">
          <ProgressBar value={step.progress} size="sm" showLabel={false} />
        </div>
      )}
    </div>
  )
}
```

---

### Phase 2: Backend 연동 (4시간)

#### Task 2.1: Supervisor Progress 전송 (1.5시간)

```python
# team_supervisor.py

async def execute_teams_node(self, state: MainSupervisorState):
    """Layer 1: executing phase"""

    session_id = state.get("session_id")
    progress_callback = self._progress_callbacks.get(session_id)

    if progress_callback:
        # Layer 1 Phase 전환
        await progress_callback("supervisor_phase_change", {
            "supervisorPhase": "executing",
            "supervisorProgress": 30
        })

    # 팀 실행
    active_teams = state.get("active_teams", [])

    # Layer 2: 각 Agent의 Step 정보 초기화
    for team_name in active_teams:
        agent_steps = self._get_agent_steps_definition(team_name)

        if progress_callback:
            await progress_callback("agent_steps_initialized", {
                "agentName": team_name,
                "agentType": team_name,
                "steps": agent_steps,
                "currentStepIndex": 0,
                "totalSteps": len(agent_steps)
            })

    # 팀 실행 (기존 로직)
    results = await self._execute_teams_parallel(active_teams, state)

    # ...
```

#### Task 2.2: Agent Step 정의 메서드 (1시간)

```python
# team_supervisor.py

def _get_agent_steps_definition(self, agent_name: str) -> List[Dict[str, Any]]:
    """Agent별 Step 정의 반환"""

    step_definitions = {
        "search": [
            {"id": "query", "name": "검색 쿼리 생성", "status": "pending"},
            {"id": "search", "name": "데이터 검색", "status": "pending"},
            {"id": "filter", "name": "결과 필터링", "status": "pending"},
            {"id": "aggregate", "name": "결과 집계", "status": "pending"}
        ],
        "document": [
            {"id": "planning", "name": "계획 수립", "status": "pending"},
            {"id": "validation", "name": "정보 검증", "status": "pending"},
            {"id": "form_input", "name": "정보 입력", "status": "pending", "isHitl": True, "hitlType": "form_input"},
            {"id": "compliance", "name": "법률 검토", "status": "pending"},
            {"id": "generate", "name": "문서 생성", "status": "pending"},
            {"id": "review", "name": "최종 검토", "status": "pending", "isHitl": True, "hitlType": "approval"}
        ],
        "analysis": [
            {"id": "load", "name": "데이터 로드", "status": "pending"},
            {"id": "analyze", "name": "분석 실행", "status": "pending"},
            {"id": "validate", "name": "결과 검증", "status": "pending"},
            {"id": "report", "name": "보고서 생성", "status": "pending"}
        ]
    }

    return step_definitions.get(agent_name, [])
```

#### Task 2.3: Agent Step Progress 전송 (1.5시간)

```python
# document_executor.py (예시)

async def planning_node(self, state):
    """Planning Step 시작"""

    # Step 시작 알림
    if progress_callback:
        await progress_callback("agent_step_progress", {
            "agentName": "document",
            "stepId": "planning",
            "status": "in_progress",
            "progress": 0
        })

    # Planning 실행
    planning_result = ...

    # Step 완료 알림
    if progress_callback:
        await progress_callback("agent_step_complete", {
            "agentName": "document",
            "stepId": "planning",
            "status": "completed"
        })

    return {"planning_result": planning_result}
```

---

### Phase 3: Frontend 메시지 핸들러 (2시간)

```typescript
// chat-interface.tsx

// State 정의
const [progressData, setProgressData] = useState<ThreeLayerProgressData>({
  supervisorPhase: "dispatching",
  supervisorProgress: 0,
  activeAgents: []
})

// WebSocket 메시지 핸들러
case 'supervisor_phase_change':
  setProgressData(prev => ({
    ...prev,
    supervisorPhase: message.supervisorPhase,
    supervisorProgress: message.supervisorProgress
  }))
  break

case 'agent_steps_initialized':
  setProgressData(prev => ({
    ...prev,
    activeAgents: [
      ...prev.activeAgents,
      {
        agentName: message.agentName,
        agentType: message.agentType,
        steps: message.steps,
        currentStepIndex: message.currentStepIndex,
        totalSteps: message.totalSteps,
        overallProgress: 0
      }
    ]
  }))
  break

case 'agent_step_progress':
  setProgressData(prev => ({
    ...prev,
    activeAgents: prev.activeAgents.map(agent =>
      agent.agentName === message.agentName
        ? {
            ...agent,
            steps: agent.steps.map(step =>
              step.id === message.stepId
                ? { ...step, status: message.status, progress: message.progress }
                : step
            )
          }
        : agent
    )
  }))
  break

case 'agent_step_complete':
  setProgressData(prev => ({
    ...prev,
    activeAgents: prev.activeAgents.map(agent =>
      agent.agentName === message.agentName
        ? {
            ...agent,
            steps: agent.steps.map(step =>
              step.id === message.stepId
                ? { ...step, status: "completed" }
                : step
            ),
            currentStepIndex: agent.currentStepIndex + 1
          }
        : agent
    )
  }))
  break
```

---

## 예상 효과

### 확장성

**Before** (Agent별 맞춤):
- Agent 10개 → Progress 컴포넌트 10개
- 유지보수 복잡도: O(N)

**After** (3-Layer):
- Agent 100개 → Progress 컴포넌트 1개
- 유지보수 복잡도: O(1)

### 사용자 경험

**Before**:
```
[실행 중 50%]  ← "뭘 하고 있는지 모르겠음"
```

**After**:
```
[실행 50%]
  Search Agent
    ✓ 쿼리 생성
    ● 데이터 검색 (60%)
    ○ 결과 필터링

  Document Agent
    ✓ 계획 수립
    ● 정보 검증
    ○ 입력 ⏸️
```

### 개발자 경험

**Before**:
- 새 Agent 추가 → 새 Progress 컴포넌트 제작 (8시간)

**After**:
- 새 Agent 추가 → Step 정의만 추가 (30분)

```python
# 새 Agent 추가 시
step_definitions["contract_review"] = [
    {"id": "load_contract", "name": "계약서 로드", "status": "pending"},
    {"id": "analyze_terms", "name": "조항 분석", "status": "pending"},
    {"id": "risk_check", "name": "위험 검토", "status": "pending"},
    {"id": "recommend", "name": "권장 사항", "status": "pending"}
]
# 끝!
```

---

## 구현 일정

| Phase | 작업 | 시간 | 우선순위 |
|-------|------|------|---------|
| Phase 1 | 3-Layer 기본 구조 | 6시간 | P1 |
| Phase 2 | Backend 연동 | 4시간 | P1 |
| Phase 3 | Frontend 핸들러 | 2시간 | P1 |
| **Total** | | **12시간** | |

---

## 결론

### 핵심 개선

1. ✅ **무한 확장 가능**: Agent가 100개 증가해도 코드 변경 없음
2. ✅ **일관된 UX**: 모든 Agent가 동일한 Progress UI 사용
3. ✅ **Agent 고유성 보존**: Layer 2로 각 Agent의 workflow 표현
4. ✅ **HITL 명확**: isHitl 플래그로 중단 지점 강조
5. ✅ **타이밍 개선**: "실행 중" 구간에서 세부 진행 상태 표시

### 권장 사항

**3-Layer Architecture 채택 이유**:
- Agent 수 증가에 완벽히 대응
- 기존 4-Stage를 Layer 1로 유지 (하위 호환)
- Agent별 세부 진행 상태를 Layer 2로 표현
- 향후 Task Detail(Layer 3) 추가 가능

**다음 단계**:
1. Phase 1 구현 (6시간)
2. Document Agent에 먼저 적용 (테스트)
3. Search, Analysis Agent 확장
4. 향후 Agent 추가 시 Step 정의만 추가

---

**작성자**: Holmes AI Team
**승인**: Pending
**관련 문서**:
- DOCUMENT_WORKFLOW_PROGRESS_DESIGN_251026.md
- LLM_PROGRESS_UI_ENHANCEMENT_PLAN_251026.md
