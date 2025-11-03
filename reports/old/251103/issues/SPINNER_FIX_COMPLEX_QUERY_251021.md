# ExecutionProgressPage Spinner 문제 해결 방안

**작성일**: 2025-10-21
**문제**: 복합 질문 시 2개 에이전트 선택되면 spinner(Settings 아이콘) 작동 안 함
**증상**: 단일 에이전트(정보검색만)는 정상 작동, 복합 에이전트(search + analysis)는 spinner 멈춤

---

## 📋 문제 현상

### ✅ 정상 작동 케이스 (단일 에이전트)

```
사용자: "전세금 인상기준은?"
  ↓
planning_node → execution_steps: [step_0: search]
  ↓
execution_start (WebSocket) → ExecutionProgressPage 생성
  ↓
Settings 아이콘 animate-spin-slow ✅ 정상 회전
  ↓
todo_updated (step_0: in_progress) → 회전 계속
  ↓
todo_updated (step_0: completed) → 회전 계속
  ↓
final_response → ExecutionProgressPage 제거
```

### ❌ 문제 발생 케이스 (복합 에이전트)

```
사용자: "강남구 아파트 시세 확인하고 투자 분석해줘"
  ↓
planning_node → execution_steps: [step_0: search, step_1: analysis]
  ↓
execution_start (WebSocket) → ExecutionProgressPage 생성
  ↓
Settings 아이콘 animate-spin-slow ❌ 회전 멈춤 (또는 시작도 안 함)
  ↓
todo_updated (step_0: in_progress) → 여전히 멈춤
  ↓
...
```

---

## 🔍 근본 원인 분석

### 1. execution-progress-page.tsx 코드 분석

[execution-progress-page.tsx:21-95](frontend/components/execution-progress-page.tsx#L21-L95)

```tsx
export function ExecutionProgressPage({
  steps,
  plan
}: ExecutionProgressPageProps) {
  // 진행 상황 계산
  const totalSteps = steps.length
  const completedSteps = steps.filter(s => s.status === "completed").length
  const failedSteps = steps.filter(s => s.status === "failed").length
  const currentStep = steps.find(s => s.status === "in_progress")

  // 전체 진행률 (0-100)
  const overallProgress = totalSteps > 0 ? (completedSteps / totalSteps) * 100 : 0

  return (
    <div className="flex justify-start mb-4">
      <div className="flex items-start gap-3 max-w-2xl w-full">
        <Card className="p-4 bg-card border flex-1">
          {/* 헤더 */}
          <div className="flex items-start justify-between mb-4">
            <div>
              <h3 className="text-lg font-semibold flex items-center gap-2">
                <Settings className="w-5 h-5 text-primary animate-spin-slow" />  {/* ⬅️ SPINNER */}
                작업 실행 중
                <span className="text-sm font-normal text-muted-foreground">
                  ({completedSteps}/{totalSteps} 완료)
                </span>
              </h3>
              {currentStep && (
                <p className="text-sm text-muted-foreground mt-1">
                  현재: {currentStep.description}
                </p>
              )}
            </div>
          </div>
          ...
```

**핵심 포인트:**
- Settings 아이콘에 `animate-spin-slow` 클래스가 **항상** 적용되어 있음
- 조건부 렌더링 없음, props에도 변경 사항 없음
- 즉, **코드 자체는 문제없음**

### 2. chat-interface.tsx 메시지 흐름 분석

[chat-interface.tsx:133-169](frontend/components/chat-interface.tsx#L133-L169)

```tsx
case 'execution_start':
  // 실행 시작 - ExecutionProgressPage 생성
  if (message.execution_steps) {
    const progressMessage: Message = {
      id: `execution-progress-${Date.now()}`,
      type: "execution-progress",
      content: "",
      timestamp: new Date(),
      // ✅ Use complete ExecutionPlan data from Backend (no dependency on Plan message)
      executionPlan: {
        intent: message.intent,
        confidence: message.confidence,
        execution_steps: message.execution_steps,
        execution_strategy: message.execution_strategy,
        estimated_total_time: message.estimated_total_time,
        keywords: message.keywords
      },
      executionSteps: message.execution_steps.map((step: ExecutionStep) => ({
        ...step,
        status: step.status || "pending"
      }))
    }

    // ✅ Remove ExecutionPlanPage and add ExecutionProgressPage
    setMessages((prev) => prev
      .filter(m => m.type !== "execution-plan")
      .concat(progressMessage)
    )
    ...
```

[chat-interface.tsx:171-191](frontend/components/chat-interface.tsx#L171-L191)

```tsx
case 'todo_updated':
  // TODO 리스트 업데이트
  if (message.execution_steps) {
    setTodos(message.execution_steps)

    // ExecutionProgressPage 메시지 찾아서 steps 업데이트
    setMessages((prev) => {
      return prev.map(msg => {
        if (msg.type === "execution-progress") {
          return {
            ...msg,
            executionSteps: message.execution_steps  // ⬅️ steps 업데이트
          }
        }
        return msg
      })
    })
  }
  break
```

**핵심 포인트:**
- `execution_start`에서 ExecutionProgressPage 생성
- `todo_updated`에서 steps만 업데이트
- React의 상태 업데이트가 정상적으로 이루어지면 리렌더링 발생
- 리렌더링 시 Settings 아이콘의 `animate-spin-slow`가 **재적용**되어야 함

### 3. 백엔드 WebSocket 메시지 전송 분석

[team_supervisor.py:558-617](backend/app/service_agent/supervisor/team_supervisor.py#L558-L617)

```python
async def execute_teams_node(self, state: MainSupervisorState) -> MainSupervisorState:
    """
    팀 실행 노드
    계획에 따라 팀들을 실행
    """
    logger.info("[TeamSupervisor] Executing teams")

    state["current_phase"] = "executing"

    # WebSocket: 실행 시작 알림
    session_id = state.get("session_id")
    progress_callback = self._progress_callbacks.get(session_id) if session_id else None
    planning_state = state.get("planning_state")
    if progress_callback and planning_state:
        try:
            analyzed_intent = planning_state.get("analyzed_intent", {})
            await progress_callback("execution_start", {  # ⬅️ execution_start 전송
                "message": "작업 실행을 시작합니다...",
                "execution_steps": planning_state.get("execution_steps", []),
                # Complete ExecutionPlan data for Frontend
                "intent": analyzed_intent.get("intent_type", "unknown"),
                "confidence": analyzed_intent.get("confidence", 0.0),
                "execution_strategy": planning_state.get("execution_strategy", "sequential"),
                "estimated_total_time": planning_state.get("estimated_total_time", 0),
                "keywords": analyzed_intent.get("keywords", [])
            })
            logger.info("[TeamSupervisor] Sent execution_start via WebSocket")
        except Exception as e:
            logger.error(f"[TeamSupervisor] Failed to send execution_start: {e}")
    ...
```

[team_supervisor.py:619-671](backend/app/service_agent/supervisor/team_supervisor.py#L619-L671)

```python
async def _execute_teams_sequential(
    self,
    teams: List[str],
    shared_state: SharedState,
    main_state: MainSupervisorState
) -> Dict[str, Any]:
    """팀 순차 실행 + execution_steps status 업데이트"""
    logger.info(f"[TeamSupervisor] Executing {len(teams)} teams sequentially")

    results = {}
    planning_state = main_state.get("planning_state")

    for team_name in teams:
        if team_name in self.teams:
            # Step ID 찾기
            step_id = self._find_step_id_for_team(team_name, planning_state)

            try:
                # ✅ 실행 전: status = "in_progress"
                if step_id and planning_state:
                    planning_state = StateManager.update_step_status(
                        planning_state,
                        step_id,
                        "in_progress",
                        progress=0
                    )
                    main_state["planning_state"] = planning_state

                    # WebSocket: TODO 상태 변경 알림 (in_progress)
                    session_id = main_state.get("session_id")
                    progress_callback = self._progress_callbacks.get(session_id) if session_id else None
                    if progress_callback:
                        try:
                            await progress_callback("todo_updated", {  # ⬅️ todo_updated 전송
                                "execution_steps": planning_state["execution_steps"]
                            })
                        except Exception as ws_error:
                            logger.error(f"[TeamSupervisor] Failed to send todo_updated (in_progress): {ws_error}")
                ...
```

**핵심 포인트:**
- 백엔드는 정상적으로 `execution_start` → `todo_updated` 메시지 전송
- 단일 에이전트와 복합 에이전트의 메시지 전송 방식은 **동일**
- 차이점은 **execution_steps 배열의 길이**뿐

---

## 🧪 가설 및 검증

### 가설 1: React 리렌더링 문제 ❓

**가설**: execution_steps가 2개일 때 React가 리렌더링을 건너뛰거나 최적화로 인해 애니메이션이 멈춤

**검증 방법**:
1. `console.log`로 `ExecutionProgressPage` 컴포넌트가 리렌더링되는지 확인
2. `steps.length` 출력해서 업데이트 확인

**가능성**: 중간

### 가설 2: CSS 애니메이션 충돌 ❓

**가설**: DOM 업데이트가 빠르게 일어나면서 `animate-spin-slow` 클래스가 제거되거나 충돌 발생

**검증 방법**:
1. 브라우저 개발자 도구에서 Settings 아이콘의 클래스 변화 관찰
2. 복합 질문 시 `animate-spin-slow` 클래스가 실제로 적용되어 있는지 확인

**가능성**: 높음 (Tailwind CSS 애니메이션 재적용 문제)

### 가설 3: execution_start 타이밍 문제 ❓

**가설**: 복합 에이전트의 경우 `execution_start` 메시지가 늦게 도착하거나 누락됨

**검증 방법**:
1. 백엔드 로그에서 `execution_start` 전송 시각 확인
2. 프론트엔드 콘솔에서 WebSocket 메시지 수신 시각 확인
3. `plan_ready` → `execution_start` 간 시간차 측정

**가능성**: 낮음 (코드상 동일한 경로)

### 가설 4: 상태 업데이트 배치 문제 (⭐ 최유력) ✅

**가설**: React 18의 Automatic Batching으로 인해 여러 상태 업데이트가 하나로 합쳐지면서 중간 상태가 건너뛰어짐

**시나리오**:
```tsx
// 단일 에이전트 (1개)
execution_start → ExecutionProgressPage 생성 (steps: [pending])
  ↓ 리렌더링 (애니메이션 시작)
todo_updated → steps: [in_progress]
  ↓ 리렌더링 (애니메이션 계속)
todo_updated → steps: [completed]
  ↓ 리렌더링 (애니메이션 계속)

// 복합 에이전트 (2개)
execution_start → ExecutionProgressPage 생성 (steps: [pending, pending])
  ↓ 리렌더링 시작 (애니메이션 시작)
todo_updated (빠르게 도착) → steps: [in_progress, pending]
  ↓ 배치로 인해 이전 리렌더링과 합쳐짐
  ↓ 애니메이션 CSS가 재적용되지 않음 ❌
```

**근거**:
1. React 18에서 `setState`는 자동으로 배치 처리됨
2. WebSocket 메시지가 빠르게 도착하면 하나의 렌더링 사이클로 합쳐질 수 있음
3. CSS 애니메이션은 클래스가 제거 후 재적용되어야 **재시작**됨
4. 복합 에이전트는 실행 시간이 길어서 메시지 간격이 더 짧을 수 있음

**검증 방법**:
1. `useEffect`로 `steps` 변경 시마다 로그 출력
2. 애니메이션 재시작 강제 트리거 (key prop 변경)

**가능성**: 매우 높음 ⭐

---

## 💡 해결 방안

### 방안 1: Key Prop으로 강제 리마운트 (⭐ 추천)

**원리**: React의 `key` prop을 변경하면 컴포넌트가 완전히 제거 후 재생성됨 → CSS 애니메이션도 처음부터 시작

**수정 파일**: [chat-interface.tsx:512-517](frontend/components/chat-interface.tsx#L512-L517)

**변경 전**:
```tsx
{message.type === "execution-progress" && message.executionSteps && message.executionPlan && (
  <ExecutionProgressPage
    steps={message.executionSteps}
    plan={message.executionPlan}
  />
)}
```

**변경 후**:
```tsx
{message.type === "execution-progress" && message.executionSteps && message.executionPlan && (
  <ExecutionProgressPage
    key={message.executionSteps.map(s => s.status).join('-')}  // ⬅️ 추가: status 변경 시 리마운트
    steps={message.executionSteps}
    plan={message.executionPlan}
  />
)}
```

**장점**:
- ✅ 간단한 1줄 수정
- ✅ 애니메이션 100% 재시작 보장
- ✅ 다른 코드 영향 없음

**단점**:
- ⚠️ 컴포넌트 전체가 재생성되므로 약간의 성능 오버헤드

---

### 방안 2: useEffect로 애니메이션 재시작

**원리**: `steps` 변경을 감지하여 Settings 아이콘의 클래스를 강제로 재적용

**수정 파일**: [execution-progress-page.tsx](frontend/components/execution-progress-page.tsx)

**변경**:
```tsx
export function ExecutionProgressPage({
  steps,
  plan
}: ExecutionProgressPageProps) {
  const [animationKey, setAnimationKey] = useState(0)

  // steps 변경 시 애니메이션 재시작
  useEffect(() => {
    setAnimationKey(prev => prev + 1)
  }, [steps])

  return (
    <div className="flex justify-start mb-4">
      <div className="flex items-start gap-3 max-w-2xl w-full">
        <Card className="p-4 bg-card border flex-1">
          <div className="flex items-start justify-between mb-4">
            <div>
              <h3 className="text-lg font-semibold flex items-center gap-2">
                <Settings
                  key={animationKey}  // ⬅️ key 변경으로 애니메이션 재시작
                  className="w-5 h-5 text-primary animate-spin-slow"
                />
                작업 실행 중
                ...
```

**장점**:
- ✅ 정확한 타이밍 제어 가능
- ✅ 나머지 컴포넌트는 유지 (성능 우수)

**단점**:
- ⚠️ 코드 복잡도 증가
- ⚠️ useState, useEffect 추가 필요

---

### 방안 3: 조건부 클래스 토글

**원리**: `status`가 "in_progress"인 step이 있을 때만 애니메이션 적용

**수정 파일**: [execution-progress-page.tsx](frontend/components/execution-progress-page.tsx)

**변경**:
```tsx
const hasActiveStep = steps.some(s => s.status === "in_progress")

return (
  ...
  <Settings
    className={`w-5 h-5 text-primary ${hasActiveStep ? 'animate-spin-slow' : ''}`}
  />
  ...
)
```

**장점**:
- ✅ 명확한 의미 (실행 중일 때만 회전)
- ✅ 가장 간단한 로직

**단점**:
- ❌ **근본 원인 해결 안 됨** (클래스 토글 시점 문제)
- ❌ 모든 step이 pending일 때 회전 안 함 (사용자 혼란)

---

## 🎯 최종 권장 방안

### ⭐ 방안 1 (Key Prop) 채택 이유

1. **최소 수정**: 1줄만 변경
2. **확실한 해결**: React의 key 메커니즘으로 100% 리마운트 보장
3. **안정성**: 기존 로직 변경 없음
4. **성능**: ExecutionProgressPage는 가벼운 컴포넌트 (렌더링 비용 낮음)

### 수정 파일

**파일**: [chat-interface.tsx:512-517](frontend/components/chat-interface.tsx#L512-L517)

**수정 내용**:
```tsx
{message.type === "execution-progress" && message.executionSteps && message.executionPlan && (
  <ExecutionProgressPage
    key={message.executionSteps.map(s => s.status).join('-')}  // ✅ 추가
    steps={message.executionSteps}
    plan={message.executionPlan}
  />
)}
```

**동작 방식**:
```
단일 에이전트:
  key: "pending"
  → "in_progress"  (리마운트 ✅)
  → "completed"   (리마운트 ✅)

복합 에이전트:
  key: "pending-pending"
  → "in_progress-pending"  (리마운트 ✅)
  → "completed-pending"    (리마운트 ✅)
  → "completed-in_progress" (리마운트 ✅)
  → "completed-completed"   (리마운트 ✅)
```

---

## 📊 수정 영향 분석

### 변경 범위
- **수정 파일**: 1개 ([chat-interface.tsx](frontend/components/chat-interface.tsx))
- **수정 라인**: 1줄 추가
- **영향 범위**: ExecutionProgressPage 렌더링만

### 리스크
- **없음**: key prop 추가는 React 표준 패턴
- **호환성**: 모든 React 버전 지원
- **성능**: ExecutionProgressPage는 가벼운 UI 컴포넌트 (리마운트 비용 무시 가능)

### 테스트 방법

#### 테스트 1: 단일 에이전트
```
질문: "전세금 인상기준은?"
기대: Settings 아이콘이 계속 회전 ✅
확인: execution_start → todo_updated (in_progress) → todo_updated (completed) 동안 회전
```

#### 테스트 2: 복합 에이전트
```
질문: "강남구 아파트 시세 확인하고 투자 분석해줘"
기대: Settings 아이콘이 계속 회전 ✅
확인:
  - execution_start → 회전 시작
  - todo_updated (step_0: in_progress) → 회전 계속
  - todo_updated (step_0: completed, step_1: pending) → 회전 계속
  - todo_updated (step_1: in_progress) → 회전 계속
  - todo_updated (step_1: completed) → 회전 계속
  - final_response → ExecutionProgressPage 제거
```

#### 테스트 3: 브라우저 개발자 도구
```
1. F12 → Elements 탭
2. Settings 아이콘 선택 (<svg class="... animate-spin-slow">)
3. 복합 질문 입력
4. todo_updated 수신 시마다 DOM이 재생성되는지 확인 (깜빡임)
5. animate-spin-slow 클래스가 계속 유지되는지 확인
```

---

## 🔄 대안 방안 (필요 시)

만약 방안 1로 해결되지 않는다면:

### 대안 A: CSS 애니메이션 재시작

[execution-progress-page.tsx](frontend/components/execution-progress-page.tsx)에서:

```tsx
const [spinKey, setSpinKey] = useState(0)

useEffect(() => {
  // steps가 변경될 때마다 애니메이션 재시작
  setSpinKey(prev => prev + 1)
}, [steps.map(s => s.status).join('-')])

return (
  ...
  <Settings
    key={spinKey}
    className="w-5 h-5 text-primary animate-spin-slow"
  />
  ...
)
```

### 대안 B: Framer Motion으로 애니메이션 제어

```tsx
import { motion } from 'framer-motion'

<motion.div
  animate={{ rotate: 360 }}
  transition={{ repeat: Infinity, duration: 2, ease: "linear" }}
>
  <Settings className="w-5 h-5 text-primary" />
</motion.div>
```

---

## ✅ 체크리스트

### 구현 전
- [ ] 현재 문제 재현 확인
  - [ ] 단일 에이전트: 회전 정상
  - [ ] 복합 에이전트: 회전 멈춤
- [ ] 백업
  ```bash
  git add frontend/components/chat-interface.tsx
  git commit -m "Backup before spinner fix"
  ```

### 구현 중
- [ ] chat-interface.tsx Line 512-517 수정
  - [ ] `key` prop 추가: `key={message.executionSteps.map(s => s.status).join('-')}`
- [ ] 문법 검증
  ```bash
  cd frontend
  npm run lint
  ```

### 구현 후
- [ ] 테스트 1: 단일 에이전트 회전 확인
- [ ] 테스트 2: 복합 에이전트 회전 확인
- [ ] 테스트 3: 브라우저 개발자 도구 DOM 확인
- [ ] Git 커밋
  ```bash
  git add frontend/components/chat-interface.tsx
  git commit -m "Fix spinner: Add key prop to ExecutionProgressPage for animation restart"
  ```

---

## 📝 추가 조사 사항 (선택)

만약 방안 1로 해결되지 않는다면 추가 조사:

1. **브라우저 콘솔 로그 확인**
   ```tsx
   useEffect(() => {
     console.log('[ExecutionProgressPage] Rendered with steps:', steps.map(s => s.status))
   }, [steps])
   ```

2. **WebSocket 메시지 타이밍 확인**
   ```tsx
   case 'execution_start':
     console.log('[WS] execution_start received at', Date.now())
     ...

   case 'todo_updated':
     console.log('[WS] todo_updated received at', Date.now(), message.execution_steps)
     ...
   ```

3. **CSS 애니메이션 상태 확인**
   - 브라우저 개발자 도구 → Elements → Computed
   - `animation-name`, `animation-duration` 확인

---

## 🎯 최종 정리

### 근본 원인 (추정)
- React 18의 Automatic Batching으로 인해 빠르게 도착하는 `todo_updated` 메시지가 하나의 렌더링 사이클로 합쳐짐
- CSS 애니메이션이 재적용되지 않아 회전이 멈춤 (특히 복합 에이전트의 경우)

### 해결 방법
- ExecutionProgressPage에 `key` prop 추가
- status 변경 시마다 컴포넌트 리마운트 → 애니메이션 재시작 보장

### 수정량
- **1개 파일, 1줄 추가**
- **소요 시간**: 5분 (수정) + 5분 (테스트)

### 예상 효과
- ✅ 단일/복합 에이전트 모두 spinner 정상 작동
- ✅ 사용자 경험 개선 (진행 중임을 명확히 인지)
- ✅ 기존 기능 영향 없음

---

**작성 완료**: 2025-10-21
**검증 상태**: 로직 분석 완료
**구현 준비**: 즉시 적용 가능
**예상 소요 시간**: 10분 (수정 + 테스트)
