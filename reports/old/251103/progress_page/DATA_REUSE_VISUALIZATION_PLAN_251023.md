# Data Reuse Visualization Implementation Plan

**작성일**: 2025년 10월 23일
**작성자**: Claude (AI Assistant)
**목표**: 데이터 재사용된 팀을 Progress UI에 시각적으로 표시

---

## 📋 목차

1. [문제 정의](#문제-정의)
2. [현재 동작 분석](#현재-동작-분석)
3. [해결 방안 (Option C)](#해결-방안-option-c)
4. [구현 단계](#구현-단계)
5. [파일 수정 목록](#파일-수정-목록)
6. [테스트 계획](#테스트-계획)
7. [예상 결과](#예상-결과)

---

## 문제 정의

### 현상
- **백엔드**: Search + Analysis 두 팀이 작동 (Search는 데이터 재사용)
- **프론트엔드**: Analysis 팀만 표시됨
- **사용자 혼란**: 실제로는 두 팀의 데이터가 사용되었지만, 하나만 보임

### 원인
```
백엔드 로직:
1. LLM이 ['search_team', 'analysis_team'] 선택
2. 데이터 재사용 감지 → search_team 제거
3. execution_steps = [{ agent: 'analysis_team' }] 만 전송
4. 하지만 search 데이터는 실제로 사용됨

프론트엔드 로직:
1. execution_steps만 받아서 표시
2. search_team이 없으니 표시 안함
```

### 목표
✅ 데이터 재사용된 팀도 UI에 표시
✅ "재사용됨" 표시로 구분
✅ 사용자가 어떤 데이터가 사용되었는지 명확히 인지

---

## 현재 동작 분석

### 백엔드 WebSocket 신호 흐름

```python
# team_supervisor.py

# 1. Planning 단계
await progress_callback("planning_start", {...})
await progress_callback("analysis_start", {...})

# 2. 데이터 재사용 감지
if reuse_detected:
    await progress_callback("data_reuse_notification", {
        "message": "이전 검색 결과를 재사용합니다"
        # ⚠️ 문제: 어떤 팀이 재사용되었는지 정보 없음
    })

# 3. 실행 시작
await progress_callback("plan_ready", {
    "execution_steps": [
        {"agent": "analysis_team", ...}
        # ⚠️ 문제: search_team이 빠져있음
    ]
})

await progress_callback("execution_start", {
    "execution_steps": [
        {"agent": "analysis_team", ...}
        # ⚠️ 문제: search_team이 빠져있음
    ]
})
```

### 프론트엔드 처리

```tsx
// chat-interface.tsx

case 'data_reuse_notification':
  // ⚠️ 현재: 아무 처리도 하지 않음
  break

case 'plan_ready':
  // execution_steps만 저장
  progressData.plan.execution_steps = message.execution_steps
  // ⚠️ 문제: reused 팀 정보 없음

case 'execution_start':
  // execution_steps만 steps로 저장
  progressData.steps = message.execution_steps
  // ⚠️ 문제: reused 팀 정보 없음
```

---

## 해결 방안 (Option C)

### 핵심 아이디어
1. **백엔드**: `data_reuse_notification` 신호에 재사용된 팀 정보 추가
2. **프론트엔드**: 재사용된 팀을 steps에 포함 (완료 상태로)
3. **UI**: AgentCard에 "재사용됨" 배지 표시

### 데이터 흐름

```
백엔드
  ↓
data_reuse_notification: { reused_teams: ['search'], ... }
  ↓
프론트엔드 (chat-interface.tsx)
  ↓
progressData.reusedTeams = ['search']
  ↓
ProgressContainer (progress-container.tsx)
  ↓
allSteps = [...reusedSteps, ...actualSteps]
  ↓
AgentCard 렌더링
  ↓
[✓ Search 법률 검색 ♻️재사용됨] [✓ Analysis 종합 분석]
```

---

## 구현 단계

### Phase 1: 백엔드 수정 (team_supervisor.py)

#### Step 1.1: data_reuse_notification 신호 강화

**파일**: `backend/app/service_agent/supervisor/team_supervisor.py`
**위치**: 데이터 재사용 감지 로직 부분 (약 200-250번 줄 예상)

**현재 코드 (검색 필요):**
```python
# 데이터 재사용 감지 후
await progress_callback("data_reuse_notification", {
    "message": "이전 검색 결과를 재사용합니다"
})
```

**수정 후:**
```python
# 데이터 재사용 감지 후
reused_teams_list = []
if "search_team" in original_agents and "search_team" not in modified_agents:
    reused_teams_list.append("search")

if reused_teams_list:
    await progress_callback("data_reuse_notification", {
        "message": f"{', '.join(reused_teams_list)} 데이터를 재사용합니다",
        "reused_teams": reused_teams_list,
        "reused_from_message": message_index_to_reuse,
        "timestamp": datetime.now().isoformat()
    })
    logger.info(f"[TeamSupervisor] Sent data_reuse_notification with teams: {reused_teams_list}")
```

**변경 사항:**
- ✅ `reused_teams`: 재사용된 팀 리스트 (예: `["search"]`)
- ✅ `reused_from_message`: 몇 번째 전 메시지에서 재사용했는지
- ✅ 로깅 추가

**검증 방법:**
```bash
# 백엔드 로그에서 확인
grep "Sent data_reuse_notification with teams" backend/logs/app.log
```

---

### Phase 2: 프론트엔드 수정 (chat-interface.tsx)

#### Step 2.1: Message Type에 reusedTeams 필드 추가

**파일**: `frontend/components/chat-interface.tsx`
**위치**: 40-64번 줄 (Message interface)

**수정 전:**
```tsx
interface Message {
  id: string
  type: "user" | "bot" | "progress" | "guidance"
  content: string
  timestamp: Date
  progressData?: {
    stage: ProgressStage
    plan?: ExecutionPlan
    steps?: ExecutionStep[]
    responsePhase?: "aggregation" | "response_generation"
  }
}
```

**수정 후:**
```tsx
interface Message {
  id: string
  type: "user" | "bot" | "progress" | "guidance"
  content: string
  timestamp: Date
  progressData?: {
    stage: ProgressStage
    plan?: ExecutionPlan
    steps?: ExecutionStep[]
    responsePhase?: "aggregation" | "response_generation"
    reusedTeams?: string[]  // 🆕 추가: 재사용된 팀 리스트
  }
}
```

---

#### Step 2.2: data_reuse_notification Handler 구현

**파일**: `frontend/components/chat-interface.tsx`
**위치**: WebSocket message handler 부분 (약 100-270번 줄)

**추가할 코드:**
```tsx
case 'data_reuse_notification':
  // 재사용된 팀 정보를 progressData에 저장
  if (message.reused_teams && Array.isArray(message.reused_teams)) {
    console.log('[DEBUG] data_reuse_notification received:', message.reused_teams)

    setMessages((prev) =>
      prev.map(m =>
        m.type === "progress" && m.progressData
          ? {
              ...m,
              progressData: {
                ...m.progressData,
                reusedTeams: message.reused_teams
              }
            }
          : m
      )
    )
  }
  break
```

**설명:**
- `data_reuse_notification` 신호를 받으면
- 현재 progress 메시지의 `reusedTeams` 필드에 저장
- 나중에 execution_start에서 사용

---

### Phase 3: 프론트엔드 UI 수정 (progress-container.tsx)

#### Step 3.1: ExecutionContent에서 reused steps 병합

**파일**: `frontend/components/progress-container.tsx`
**위치**: ExecutingContent 함수 (약 185-225번 줄)

**현재 코드:**
```tsx
function ExecutingContent({ steps }: { steps: ExecutionStep[] }) {
  const totalSteps = steps.length
  const completedSteps = steps.filter((s) => s.status === "completed").length
  const failedSteps = steps.filter((s) => s.status === "failed").length
  const overallProgress = totalSteps > 0 ? (completedSteps / totalSteps) * 100 : 0

  return (
    <div className="space-y-3">
      {/* 전체 진행률 */}
      ...

      {/* 에이전트 카드들 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        {steps.map((step) => (
          <AgentCard key={step.step_id} step={step} />
        ))}
      </div>
    </div>
  )
}
```

**수정 후:**
```tsx
function ExecutingContent({
  steps,
  reusedTeams
}: {
  steps: ExecutionStep[]
  reusedTeams?: string[]  // 🆕 추가
}) {
  // 재사용된 팀을 가상 steps로 생성
  const reusedSteps: ExecutionStep[] = (reusedTeams || []).map(team => ({
    step_id: `reused-${team}`,
    task: team === 'search' ? '법률 검색' : `${team} 작업`,
    description: '이전 데이터 재사용',
    status: 'completed' as const,
    agent: `${team}_team`,
    progress: 100,
    isReused: true  // 🆕 재사용 플래그
  }))

  // 재사용 + 실제 steps 병합
  const allSteps = [...reusedSteps, ...steps]

  const totalSteps = allSteps.length
  const completedSteps = allSteps.filter((s) => s.status === "completed").length
  const failedSteps = allSteps.filter((s) => s.status === "failed").length
  const overallProgress = totalSteps > 0 ? (completedSteps / totalSteps) * 100 : 0

  return (
    <div className="space-y-3">
      {/* 전체 진행률 */}
      ...

      {/* 에이전트 카드들 (재사용 + 실제) */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        {allSteps.map((step) => (
          <AgentCard key={step.step_id} step={step} />
        ))}
      </div>
    </div>
  )
}
```

**설명:**
- `reusedTeams` prop 추가
- 재사용된 팀을 `completed` 상태의 가상 steps로 생성
- 실제 steps와 병합하여 표시

---

#### Step 3.2: ProgressContainer에서 reusedTeams 전달

**파일**: `frontend/components/progress-container.tsx`
**위치**: ProgressContainer 함수 (약 95-99번 줄)

**현재 코드:**
```tsx
{/* 하단: Content Area (Stage별 변경) */}
<div className="min-h-[120px]">
  {stage === "dispatch" && <DispatchContent />}
  {stage === "analysis" && <AnalysisContent plan={plan} />}
  {stage === "executing" && <ExecutingContent steps={steps} />}
  {stage === "generating" && <GeneratingContent phase={responsePhase} />}
</div>
```

**수정 후:**
```tsx
{/* 하단: Content Area (Stage별 변경) */}
<div className="min-h-[120px]">
  {stage === "dispatch" && <DispatchContent />}
  {stage === "analysis" && <AnalysisContent plan={plan} />}
  {stage === "executing" && (
    <ExecutingContent
      steps={steps}
      reusedTeams={reusedTeams}  // 🆕 전달
    />
  )}
  {stage === "generating" && <GeneratingContent phase={responsePhase} />}
</div>
```

---

#### Step 3.3: Props에 reusedTeams 추가

**파일**: `frontend/components/progress-container.tsx`
**위치**: ProgressContainerProps interface (약 10-15번 줄)

**현재 코드:**
```tsx
export interface ProgressContainerProps {
  stage: ProgressStage
  plan?: ExecutionPlan
  steps?: ExecutionStep[]
  responsePhase?: "aggregation" | "response_generation"
}
```

**수정 후:**
```tsx
export interface ProgressContainerProps {
  stage: ProgressStage
  plan?: ExecutionPlan
  steps?: ExecutionStep[]
  responsePhase?: "aggregation" | "response_generation"
  reusedTeams?: string[]  // 🆕 추가
}
```

---

#### Step 3.4: chat-interface에서 reusedTeams 전달

**파일**: `frontend/components/chat-interface.tsx`
**위치**: ProgressContainer 렌더링 부분 (약 573-583번 줄)

**현재 코드:**
```tsx
{message.type === "progress" && message.progressData && (
  <ProgressContainer
    stage={message.progressData.stage}
    plan={message.progressData.plan}
    steps={message.progressData.steps}
    responsePhase={message.progressData.responsePhase}
  />
)}
```

**수정 후:**
```tsx
{message.type === "progress" && message.progressData && (
  <ProgressContainer
    stage={message.progressData.stage}
    plan={message.progressData.plan}
    steps={message.progressData.steps}
    responsePhase={message.progressData.responsePhase}
    reusedTeams={message.progressData.reusedTeams}  // 🆕 전달
  />
)}
```

---

### Phase 4: AgentCard 재사용 표시 추가

#### Step 4.1: ExecutionStep type 확장

**파일**: `frontend/types/execution.ts` (또는 progress-container.tsx 내부)

**추가:**
```tsx
export interface ExecutionStep {
  step_id: string
  task: string
  description: string
  status: "pending" | "in_progress" | "completed" | "failed" | "skipped"
  agent?: string
  progress?: number
  isReused?: boolean  // 🆕 추가: 재사용 여부
}
```

---

#### Step 4.2: AgentCard에 재사용 배지 추가

**파일**: `frontend/components/progress-container.tsx`
**위치**: AgentCard 함수 (약 228-290번 줄)

**현재 코드:**
```tsx
function AgentCard({ step }: { step: ExecutionStep }) {
  const statusConfig = { ... }
  const config = statusConfig[step.status] || statusConfig.pending

  return (
    <div className={`p-3 rounded-lg border ${config.bg} ${config.borderColor}`}>
      <div className="flex items-center gap-2 mb-2">
        <span className={`text-xl ${config.color}`}>{config.icon}</span>
        <span className="font-medium text-sm">{step.task}</span>
      </div>
      <div className="text-xs text-muted-foreground mb-2">{step.description}</div>

      {/* 진행 중일 때 진행률 BAR */}
      {step.status === "in_progress" && step.progress !== undefined && (
        ...
      )}
    </div>
  )
}
```

**수정 후:**
```tsx
function AgentCard({ step }: { step: ExecutionStep }) {
  const statusConfig = { ... }
  const config = statusConfig[step.status] || statusConfig.pending

  return (
    <div className={`p-3 rounded-lg border ${config.bg} ${config.borderColor}`}>
      <div className="flex items-center gap-2 mb-2">
        <span className={`text-xl ${config.color}`}>{config.icon}</span>
        <span className="font-medium text-sm">{step.task}</span>

        {/* 🆕 재사용 배지 */}
        {step.isReused && (
          <span className="ml-auto text-xs px-2 py-0.5 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded-full border border-blue-200 dark:border-blue-800 flex items-center gap-1">
            <span>♻️</span>
            <span>재사용</span>
          </span>
        )}
      </div>

      <div className="text-xs text-muted-foreground mb-2">{step.description}</div>

      {/* 진행 중일 때 진행률 BAR (재사용은 제외) */}
      {!step.isReused && step.status === "in_progress" && step.progress !== undefined && (
        ...
      )}
    </div>
  )
}
```

**설명:**
- `isReused` 플래그가 true면 "♻️ 재사용" 배지 표시
- 파란색 배지로 시각적 구분
- 재사용된 카드는 진행률 BAR 표시 안함 (이미 100% 완료)

---

## 파일 수정 목록

### 백엔드 (1개 파일)

| 파일 | 위치 | 수정 내용 | 예상 라인 |
|------|------|----------|----------|
| `backend/app/service_agent/supervisor/team_supervisor.py` | 데이터 재사용 감지 로직 | `data_reuse_notification` 신호에 `reused_teams`, `reused_from_message` 추가 | 약 200-250번 줄 |

### 프론트엔드 (3개 파일)

| 파일 | 위치 | 수정 내용 | 예상 라인 |
|------|------|----------|----------|
| `frontend/components/chat-interface.tsx` | Message interface | `progressData`에 `reusedTeams?: string[]` 추가 | 40-64번 줄 |
| `frontend/components/chat-interface.tsx` | WebSocket handler | `data_reuse_notification` case 추가 | 100-270번 줄 |
| `frontend/components/chat-interface.tsx` | ProgressContainer 렌더링 | `reusedTeams` prop 전달 | 573-583번 줄 |
| `frontend/components/progress-container.tsx` | ProgressContainerProps | `reusedTeams?: string[]` prop 추가 | 10-15번 줄 |
| `frontend/components/progress-container.tsx` | ExecutingContent | `reusedTeams` 받아서 가상 steps 생성 | 185-225번 줄 |
| `frontend/components/progress-container.tsx` | ProgressContainer 렌더링 | `reusedTeams` 전달 | 95-99번 줄 |
| `frontend/components/progress-container.tsx` | AgentCard | 재사용 배지 UI 추가 | 228-290번 줄 |
| `frontend/types/execution.ts` | ExecutionStep type | `isReused?: boolean` 필드 추가 | 타입 정의 부분 |

**총 수정 파일**: 4개 (백엔드 1, 프론트엔드 3)
**총 수정 위치**: 8곳
**예상 작업 시간**: 30-40분

---

## 테스트 계획

### 테스트 시나리오

#### Scenario 1: 첫 번째 질문 (데이터 재사용 없음)

**입력:**
```
사용자: "전세계약 만료 후 4년이 지나면 어떻게 되나요?"
```

**예상 동작:**
1. Search + Analysis 두 팀 모두 실행
2. UI에 두 카드 모두 표시
3. 재사용 배지 없음

**백엔드 로그:**
```
[TeamSupervisor] Primary LLM selected agents: ['search_team', 'analysis_team']
[TeamSupervisor] Plan created: 2 steps, 2 teams
```

**프론트엔드 UI:**
```
[✓ Search 법률 검색]  [✓ Analysis 종합 분석]
```

---

#### Scenario 2: 두 번째 질문 (데이터 재사용 있음)

**입력:**
```
사용자: "전세계약 4년 경과 시 어떻게 대응해야 해?"
```

**예상 동작:**
1. Search 재사용, Analysis만 실행
2. `data_reuse_notification` 신호 수신
3. UI에 두 카드 모두 표시 (Search는 "재사용" 배지)

**백엔드 로그:**
```
[TeamSupervisor] Primary LLM selected agents: ['search_team', 'analysis_team']
[TeamSupervisor] Reusing data from 2 messages ago
[TeamSupervisor] Removed search_team from suggested_agents
[TeamSupervisor] Sent data_reuse_notification with teams: ['search']
[TeamSupervisor] Plan created: 1 steps, 1 teams
```

**프론트엔드 콘솔:**
```
[DEBUG] data_reuse_notification received: ['search']
```

**프론트엔드 UI:**
```
[✓ Search 법률 검색 ♻️재사용]  [✓ Analysis 종합 분석]
```

---

#### Scenario 3: 여러 팀 재사용

**입력:**
```
사용자: "앞의 분석 결과를 요약해줘"
```

**예상 동작:**
1. Search + Analysis 모두 재사용
2. UI에 두 카드 모두 "재사용" 배지

**프론트엔드 UI:**
```
[✓ Search 법률 검색 ♻️재사용]  [✓ Analysis 종합 분석 ♻️재사용]
```

---

### 검증 체크리스트

#### 백엔드 검증

- [ ] `data_reuse_notification` 신호에 `reused_teams` 필드 포함
- [ ] `reused_teams` 배열이 정확한 팀 이름 포함
- [ ] 로그에 "Sent data_reuse_notification with teams: ['search']" 출력
- [ ] WebSocket을 통해 프론트엔드로 정상 전송

#### 프론트엔드 검증

- [ ] `data_reuse_notification` 메시지 수신 확인 (콘솔 로그)
- [ ] `progressData.reusedTeams` 필드에 정상 저장
- [ ] ExecutingContent에 reusedSteps + actualSteps 병합
- [ ] 재사용 카드에 "♻️ 재사용" 배지 표시
- [ ] 재사용 카드 스타일이 파란색으로 구분됨
- [ ] 전체 진행률에 재사용 카드도 포함됨

#### UI 검증

- [ ] 재사용 배지가 오른쪽 끝에 정렬
- [ ] 재사용 카드도 "완료됨" 상태 아이콘 (✓)
- [ ] 재사용 카드에는 진행률 BAR 표시 안됨
- [ ] 다크 모드에서도 배지 색상 정상 표시

---

## 예상 결과

### Before (현재)
```
┌────────────────────────────────────────────┐
│ 전체 작업 진행률                     1/1 완료│
│ ████████████████████████████████████  100% │
└────────────────────────────────────────────┘

┌──────────────┐
│ ✓ Analysis   │
│ 종합 분석    │
│ 완료됨       │
└──────────────┘
```

**문제점:**
- Search가 실제로 사용되었지만 표시 안됨
- 사용자가 1개 팀만 작동했다고 오해

---

### After (개선 후)
```
┌────────────────────────────────────────────┐
│ 전체 작업 진행률                     2/2 완료│
│ ████████████████████████████████████  100% │
└────────────────────────────────────────────┘

┌──────────────────┐ ┌──────────────┐
│ ✓ Search         │ │ ✓ Analysis   │
│ 법률 검색        │ │ 종합 분석    │
│ 이전 데이터 재사용│ │ 완료됨       │
│ ♻️ 재사용        │ │              │
└──────────────────┘ └──────────────┘
```

**개선점:**
- ✅ 두 팀 모두 표시
- ✅ Search가 재사용되었음을 명확히 표시
- ✅ 전체 진행률이 2/2로 정확함

---

## 추가 고려사항

### 다크 모드 스타일

**재사용 배지 색상:**
```tsx
// 라이트 모드
bg-blue-100 text-blue-700 border-blue-200

// 다크 모드
dark:bg-blue-900/30 dark:text-blue-300 dark:border-blue-800
```

### 접근성 (Accessibility)

**ARIA 속성 추가:**
```tsx
{step.isReused && (
  <span
    className="..."
    role="status"
    aria-label="이 작업은 이전 데이터를 재사용했습니다"
  >
    <span aria-hidden="true">♻️</span>
    <span>재사용</span>
  </span>
)}
```

### 다국어 지원 (향후)

**재사용 텍스트:**
- 한국어: "재사용"
- 영어: "Reused"
- 일본어: "再利用"

---

## 롤백 계획

### 문제 발생 시

#### 백엔드 롤백
```bash
git checkout backend/app/service_agent/supervisor/team_supervisor.py
```

#### 프론트엔드 롤백
```bash
git checkout frontend/components/chat-interface.tsx
git checkout frontend/components/progress-container.tsx
git checkout frontend/types/execution.ts
```

### 부분 롤백 (UI만)

프론트엔드만 문제 시:
- 백엔드 변경 유지
- 프론트엔드에서 `data_reuse_notification` 핸들러만 주석 처리
- 기존 동작으로 복구

---

## 타임라인

### 예상 일정

| Phase | 작업 내용 | 예상 시간 | 담당 |
|-------|----------|----------|------|
| Phase 1 | 백엔드 수정 (team_supervisor.py) | 10분 | Backend |
| Phase 2 | 프론트엔드 타입 & 핸들러 (chat-interface.tsx) | 10분 | Frontend |
| Phase 3 | UI 수정 (progress-container.tsx) | 15분 | Frontend |
| Phase 4 | AgentCard 재사용 배지 추가 | 5분 | Frontend |
| **테스트** | 3가지 시나리오 테스트 | 10분 | QA |
| **총계** | | **50분** | |

---

## 성공 기준

### Minimum Viable Product (MVP)

- ✅ 재사용된 팀이 UI에 표시됨
- ✅ "재사용" 배지로 구분 가능
- ✅ 백엔드 로그와 프론트엔드 UI가 일치

### Nice to Have

- ✅ 다크 모드 지원
- ✅ 접근성 (ARIA)
- ✅ 애니메이션 효과
- ⚠️ 다국어 지원 (향후)

---

## 참고 자료

### 관련 파일

- Backend: `backend/app/service_agent/supervisor/team_supervisor.py`
- Frontend: `frontend/components/chat-interface.tsx`
- Frontend: `frontend/components/progress-container.tsx`
- Types: `frontend/types/execution.ts`

### 관련 이슈

- 데이터 재사용 로직: `team_supervisor.py` Line 200-250
- Progress UI 4-Stage 시스템: `progress-container.tsx`

---

**작성 완료**: 2025년 10월 23일
**문서 버전**: 1.0.0
**상태**: 검토 완료, 구현 대기
