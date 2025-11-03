# ExecutionProgressPage Spinner 작동 안 함 - 면밀한 분석

**작성일**: 2025-10-21
**문제**: 복합 질문 시 2개 에이전트 선택되면 spinner 작동 안 함
**기준점**: 단일 에이전트는 정상 작동

---

## 🎯 기준점 설정

### 명확한 비교 기준

| 항목 | 단일 에이전트 (✅ 정상) | 복합 에이전트 (❌ 문제) |
|------|------------------------|------------------------|
| **쿼리 예시** | "전세금 인상기준은?" | "강남구 아파트 시세 확인하고 투자 분석해줘" |
| **execution_steps** | 1개 (search) | 2개 (search, analysis) |
| **Spinner 상태** | 회전함 | 회전 안 함 (또는 멈춤) |
| **ExecutionProgressPage** | 생성됨 | 생성됨 |
| **DOM 렌더링** | 정상 | 정상 |

---

## 📊 세부 흐름 추적 (WebSocket 메시지 기준)

### 1. 단일 에이전트 흐름 (✅ 정상)

```
[사용자] "전세금 인상기준은?" 입력
   ↓
[Frontend - handleSendMessage] Line 204-255
   ├─ userMessage 생성
   ├─ planMessage 생성 (ExecutionPlanPage - 로딩 상태)
   ├─ setMessages([...prev, userMessage, planMessage])
   ├─ setProcessState({ step: "planning" })
   └─ wsClient.send({ type: "query", query: "..." })
   ↓
[Backend - planning_node] Line 174-408
   ├─ Intent Analysis (LLM #1)
   ├─ Agent Selection (LLM #2) → ["search_team"]
   ├─ execution_steps = [{ step_id: "step_0", team: "search", status: "pending", priority: 0 }]
   ├─ await progress_callback("plan_ready", { execution_steps: [...] })
   └─ return state
   ↓
[WebSocket] plan_ready 전송
   ↓
[Frontend - handleWSMessage] Line 101-131 (plan_ready)
   ├─ setMessages(prev => prev.map(m =>
   │    m.type === "execution-plan" && m.executionPlan?.isLoading
   │      ? { ...m, executionPlan: { ...message, isLoading: false } }
   │      : m
   │  ))
   └─ setTodos(message.execution_steps)  // [{ step_id: "step_0", status: "pending" }]
   ↓
[Backend - execute_teams_node] Line 558-609
   ├─ await progress_callback("execution_start", {
   │    execution_steps: [{ step_id: "step_0", team: "search", status: "pending", priority: 0 }],
   │    intent, confidence, ...
   │  })
   └─ start sequential execution
   ↓
[WebSocket] execution_start 전송
   ↓
[Frontend - handleWSMessage] Line 133-169 (execution_start)  ⬅️ 핵심!
   ├─ const progressMessage = {
   │    id: `execution-progress-${Date.now()}`,
   │    type: "execution-progress",
   │    executionPlan: { intent, confidence, execution_steps, ... },
   │    executionSteps: message.execution_steps.map(step => ({
   │      ...step,
   │      status: step.status || "pending"  // ⬅️ "pending"
   │    }))
   │  }
   ├─ setMessages(prev => prev
   │    .filter(m => m.type !== "execution-plan")  // ExecutionPlanPage 제거
   │    .concat(progressMessage)  // ExecutionProgressPage 추가
   │  )
   └─ setProcessState({ step: "executing", agentType: null, message: "..." })
   ↓
[React Render] ExecutionProgressPage 생성
   ├─ steps = [{ step_id: "step_0", status: "pending", priority: 0 }]
   ├─ currentStep = steps.find(s => s.status === "in_progress")  // ⬅️ undefined (아직 pending)
   └─ <Settings className="... animate-spin-slow" />  // ⬅️ 애니메이션 시작
   ↓
[Backend - _execute_teams_sequential] Line 656-676
   ├─ planning_state = StateManager.update_step_status(planning_state, "step_0", "in_progress", progress=0)
   ├─ await progress_callback("todo_updated", { execution_steps: [...] })
   └─ execute search team
   ↓
[WebSocket] todo_updated (step_0: in_progress)
   ↓
[Frontend - handleWSMessage] Line 171-191 (todo_updated)
   ├─ setTodos(message.execution_steps)
   └─ setMessages(prev => prev.map(msg =>
        msg.type === "execution-progress"
          ? { ...msg, executionSteps: message.execution_steps }  // ⬅️ steps 업데이트
          : msg
      ))
   ↓
[React Render] ExecutionProgressPage 리렌더링
   ├─ steps = [{ step_id: "step_0", status: "in_progress", priority: 0 }]
   ├─ currentStep = steps.find(s => s.status === "in_progress")  // ⬅️ step_0 찾음
   └─ <Settings className="... animate-spin-slow" />  // ⬅️ 애니메이션 계속
   ↓
[Backend] Search team 완료
   ├─ planning_state = StateManager.update_step_status(planning_state, "step_0", "completed", progress=100)
   ├─ await progress_callback("todo_updated", { execution_steps: [...] })
   ↓
[WebSocket] todo_updated (step_0: completed)
   ↓
[Frontend] ExecutionProgressPage 리렌더링
   ├─ steps = [{ step_id: "step_0", status: "completed", priority: 0 }]
   ├─ currentStep = undefined (no in_progress)
   └─ <Settings className="... animate-spin-slow" />  // ⬅️ 애니메이션 계속
   ↓
[Backend] generate_response_node
   ├─ await progress_callback("final_response", { response: {...} })
   ↓
[Frontend] ExecutionProgressPage 제거, 답변 표시
```

### 2. 복합 에이전트 흐름 (❌ 문제)

```
[사용자] "강남구 아파트 시세 확인하고 투자 분석해줘" 입력
   ↓
[Frontend - handleSendMessage] Line 204-255
   ├─ userMessage 생성
   ├─ planMessage 생성 (ExecutionPlanPage - 로딩 상태)
   ├─ setMessages([...prev, userMessage, planMessage])
   ├─ setProcessState({ step: "planning" })
   └─ wsClient.send({ type: "query", query: "..." })
   ↓
[Backend - planning_node] Line 174-408
   ├─ Intent Analysis (LLM #1)
   ├─ Agent Selection (LLM #2) → ["search_team", "analysis_team"]
   ├─ execution_steps = [
   │    { step_id: "step_0", team: "search", status: "pending", priority: 0 },
   │    { step_id: "step_1", team: "analysis", status: "pending", priority: 1 }
   │  ]
   ├─ await progress_callback("plan_ready", { execution_steps: [...] })
   └─ return state
   ↓
[WebSocket] plan_ready 전송
   ↓
[Frontend - handleWSMessage] Line 101-131 (plan_ready)
   ├─ setMessages(prev => prev.map(m =>
   │    m.type === "execution-plan" && m.executionPlan?.isLoading
   │      ? { ...m, executionPlan: { ...message, isLoading: false } }
   │      : m
   │  ))
   └─ setTodos(message.execution_steps)  // [step_0, step_1]
   ↓
[Backend - execute_teams_node] Line 558-609
   ├─ await progress_callback("execution_start", {
   │    execution_steps: [
   │      { step_id: "step_0", team: "search", status: "pending", priority: 0 },
   │      { step_id: "step_1", team: "analysis", status: "pending", priority: 1 }
   │    ],
   │    intent, confidence, ...
   │  })
   └─ start sequential execution
   ↓
[WebSocket] execution_start 전송
   ↓
[Frontend - handleWSMessage] Line 133-169 (execution_start)  ⬅️ 핵심!
   ├─ const progressMessage = {
   │    id: `execution-progress-${Date.now()}`,
   │    type: "execution-progress",
   │    executionPlan: { intent, confidence, execution_steps, ... },
   │    executionSteps: message.execution_steps.map(step => ({
   │      ...step,
   │      status: step.status || "pending"  // ⬅️ "pending", "pending"
   │    }))
   │  }
   ├─ setMessages(prev => prev
   │    .filter(m => m.type !== "execution-plan")  // ExecutionPlanPage 제거
   │    .concat(progressMessage)  // ExecutionProgressPage 추가
   │  )
   └─ setProcessState({ step: "executing", agentType: null, message: "..." })
   ↓
[React Render] ExecutionProgressPage 생성  ⬅️ 여기서 문제 발생 가능
   ├─ steps = [
   │    { step_id: "step_0", status: "pending", priority: 0 },
   │    { step_id: "step_1", status: "pending", priority: 1 }
   │  ]
   ├─ currentStep = steps.find(s => s.status === "in_progress")  // ⬅️ undefined (둘 다 pending)
   └─ <Settings className="... animate-spin-slow" />  // ⬅️ 애니메이션 시작... 해야 하는데?
   ↓
[Backend - _execute_teams_sequential] Line 656-676
   ├─ planning_state = StateManager.update_step_status(planning_state, "step_0", "in_progress", progress=0)
   ├─ await progress_callback("todo_updated", { execution_steps: [
   │      { step_id: "step_0", status: "in_progress", priority: 0 },  // ⬅️ 변경
   │      { step_id: "step_1", status: "pending", priority: 1 }
   │    ]})
   └─ execute search team
   ↓
[WebSocket] todo_updated (step_0: in_progress)  ⬅️ 빠르게 도착 (<100ms)
   ↓
[Frontend - handleWSMessage] Line 171-191 (todo_updated)
   ├─ setTodos(message.execution_steps)
   └─ setMessages(prev => prev.map(msg =>
        msg.type === "execution-progress"
          ? { ...msg, executionSteps: message.execution_steps }  // ⬅️ steps 업데이트
          : msg
      ))
   ↓
[React Render] ExecutionProgressPage 리렌더링  ⬅️ 문제 발생 지점!
   ├─ steps = [
   │    { step_id: "step_0", status: "in_progress", priority: 0 },
   │    { step_id: "step_1", status: "pending", priority: 1 }
   │  ]
   ├─ currentStep = steps.find(s => s.status === "in_progress")  // ⬅️ step_0 찾음
   └─ <Settings className="... animate-spin-slow" />  // ⬅️ 애니메이션... 멈춤?
```

---

## 🔬 근본 원인 재분석

### 가설 재검토

#### ❌ 기각: "React 18 Automatic Batching" 가설

**이전 가설**:
- execution_start와 todo_updated가 빠르게 도착하면서 배치 처리됨
- CSS 애니메이션이 재적용되지 않음

**기각 이유**:
1. **execution_start와 todo_updated는 다른 백엔드 노드에서 전송됨**
   - execution_start: execute_teams_node 시작 시 (Line 574)
   - todo_updated: _execute_teams_sequential 내부 (Line 671)
   - 두 메시지 사이에는 백엔드 로직 실행 시간이 있음 (최소 수백 ms)

2. **단일 에이전트도 동일한 구조**
   - 단일 에이전트도 execution_start → todo_updated 순서로 메시지 수신
   - 단일 에이전트는 정상 작동함

3. **React 18 배치는 동기 이벤트만 해당**
   - WebSocket 메시지는 비동기 이벤트
   - 각 WebSocket 메시지는 별도의 이벤트 루프 태스크
   - 배치 처리 가능성 낮음

#### ⚠️ 검토 필요: "CSS 애니메이션 재시작 문제" 가설

**가능성 1**: 컴포넌트가 실제로 생성되지 않음

```tsx
// chat-interface.tsx Line 313-318
{message.type === "execution-progress" && message.executionSteps && message.executionPlan && (
  <ExecutionProgressPage
    steps={message.executionSteps}  // ⬅️ 여기가 문제?
    plan={message.executionPlan}
  />
)}
```

**검증 필요**:
- `message.executionSteps`가 실제로 존재하는가?
- `message.executionPlan`이 실제로 존재하는가?
- 복합 에이전트의 경우 조건이 false가 되는가?

**가능성 2**: DOM이 렌더링되지만 CSS가 적용 안 됨

```tsx
// execution-progress-page.tsx Line 42
<Settings className="w-5 h-5 text-primary animate-spin-slow" />
```

**검증 필요**:
- 복합 에이전트의 경우 Settings 아이콘이 실제로 DOM에 존재하는가?
- `animate-spin-slow` 클래스가 실제로 적용되어 있는가?
- CSS 애니메이션이 정의되어 있는가?

#### ⭐ 새로운 가설: "execution_start 메시지 데이터 누락"

**핵심 의심 지점**:

[Backend - team_supervisor.py:574-583](backend/app/service_agent/supervisor/team_supervisor.py#L574-L583)

```python
await progress_callback("execution_start", {
    "message": "작업 실행을 시작합니다...",
    "execution_steps": planning_state.get("execution_steps", []),  # ⬅️ 이것이 올바른가?
    # Complete ExecutionPlan data for Frontend
    "intent": analyzed_intent.get("intent_type", "unknown"),
    "confidence": analyzed_intent.get("confidence", 0.0),
    "execution_strategy": planning_state.get("execution_strategy", "sequential"),
    "estimated_total_time": planning_state.get("estimated_total_time", 0),
    "keywords": analyzed_intent.get("keywords", [])
})
```

**문제 분석**:

1. **execution_steps의 상태가 맞는가?**
   - planning_state.get("execution_steps", [])는 **pending 상태**
   - 복합 에이전트의 경우 2개의 pending steps

2. **Frontend가 이 데이터를 제대로 받는가?**
   - [chat-interface.tsx:136-154](frontend/components/chat-interface.tsx#L136-L154)
   - `message.execution_steps`를 그대로 사용
   - `executionSteps: message.execution_steps.map(step => ({ ...step, status: step.status || "pending" }))`

3. **렌더링 조건 확인**:
   - [chat-interface.tsx:313-318](frontend/components/chat-interface.tsx#L313-L318)
   - `message.executionSteps && message.executionPlan` 조건
   - 복합 에이전트의 경우 이 조건이 false가 될 수 있는가?

---

## 🎯 실제 문제 재정의

### 현재까지의 분석 요약

| 확인 사항 | 단일 에이전트 | 복합 에이전트 |
|-----------|--------------|--------------|
| execution_start 전송 | ✅ 확인됨 | ❓ 미확인 |
| ExecutionProgressPage 생성 | ✅ 확인됨 | ❓ 미확인 |
| steps 배열 | [1개] | [2개] |
| DOM 렌더링 | ✅ 정상 | ❓ 미확인 |
| animate-spin-slow 클래스 | ✅ 적용됨 | ❓ 미확인 |
| CSS 애니메이션 | ✅ 작동함 | ❌ 작동 안 함 |

### 필요한 디버깅

#### 1. 백엔드 로그 확인

**복합 질문 입력 후 확인할 로그**:

```bash
# 검색 패턴
grep "execution_start" backend/logs/app.log
grep "todo_updated" backend/logs/app.log
grep "Active teams (priority order)" backend/logs/app.log
```

**기대 로그**:
```
[TeamSupervisor] Active teams (priority order): ['search', 'analysis']
[TeamSupervisor] Sent execution_start via WebSocket
[TeamSupervisor] Team 'search' started
[TeamSupervisor] Failed to send todo_updated (in_progress): ...  # ⬅️ 에러?
```

#### 2. 프론트엔드 콘솔 확인

**복합 질문 입력 후 확인할 로그**:

```javascript
// chat-interface.tsx Line 92
console.log('[ChatInterface] Received WS message:', message.type)

// 추가 디버깅 필요 (execution_start 수신 확인)
case 'execution_start':
  console.log('[ChatInterface] execution_start received:', message)
  console.log('  - execution_steps:', message.execution_steps)
  console.log('  - execution_steps length:', message.execution_steps?.length)
  console.log('  - intent:', message.intent)
  console.log('  - executionPlan:', message.executionPlan)
  ...
```

**기대 로그**:
```
[ChatInterface] Received WS message: execution_start
[ChatInterface] execution_start received: { execution_steps: [...], intent: "...", ... }
  - execution_steps: [{ step_id: "step_0", ... }, { step_id: "step_1", ... }]
  - execution_steps length: 2
  - intent: "market_inquiry"
  - executionPlan: undefined  # ⬅️ 문제?
```

#### 3. DOM 검사

**복합 질문 입력 후 브라우저 개발자 도구**:

```
F12 → Elements 탭
검색: "execution-progress" 또는 "작업 실행 중"

확인 사항:
1. ExecutionProgressPage 컴포넌트가 DOM에 존재하는가?
2. Settings 아이콘 (<svg>)이 존재하는가?
3. animate-spin-slow 클래스가 적용되어 있는가?
4. CSS 애니메이션이 실제로 실행되고 있는가? (Animations 탭)
```

---

## 💡 추정되는 실제 원인 (3가지 시나리오)

### 시나리오 1: ExecutionProgressPage가 아예 생성 안 됨 ⭐⭐⭐

**원인**:
- execution_start 메시지의 `execution_steps` 또는 `executionPlan` 데이터가 누락
- [chat-interface.tsx:313](frontend/components/chat-interface.tsx#L313) 조건 false

**증상**:
- DOM에 ExecutionProgressPage가 없음
- spinner도 당연히 안 보임

**검증 방법**:
```javascript
// chat-interface.tsx Line 136 추가
console.log('[DEBUG] execution_start - executionSteps:', message.execution_steps)
console.log('[DEBUG] execution_start - executionPlan keys:', Object.keys(progressMessage.executionPlan))
```

**해결 방법**:
- Backend의 execution_start 메시지 payload 확인
- Frontend의 progressMessage 생성 로직 확인

---

### 시나리오 2: ExecutionProgressPage는 생성되지만 즉시 제거됨 ⭐⭐

**원인**:
- todo_updated 메시지가 너무 빠르게 도착
- setMessages가 execution_start와 todo_updated를 거의 동시에 처리
- 어떤 이유로 ExecutionProgressPage가 제거됨

**증상**:
- DOM에 ExecutionProgressPage가 깜빡 나타났다가 사라짐
- spinner가 순간 보였다가 사라짐

**검증 방법**:
```javascript
// chat-interface.tsx Line 179 추가
console.log('[DEBUG] todo_updated - current messages:', prev.length)
console.log('[DEBUG] todo_updated - execution-progress count:',
  prev.filter(m => m.type === "execution-progress").length)
```

**해결 방법**:
- todo_updated에서 ExecutionProgressPage를 제거하지 않도록 확인

---

### 시나리오 3: ExecutionProgressPage는 존재하지만 CSS 애니메이션만 안 됨 ⭐

**원인**:
- DOM은 정상적으로 렌더링됨
- `animate-spin-slow` 클래스는 적용되어 있음
- 하지만 CSS 애니메이션 정의가 없거나 재생 안 됨

**증상**:
- DOM에 ExecutionProgressPage 존재
- Settings 아이콘 존재
- animate-spin-slow 클래스 적용됨
- 하지만 회전 안 함

**검증 방법**:
```bash
# Frontend에서 animate-spin-slow 정의 찾기
cd frontend
grep -r "animate-spin-slow" .
grep -r "@keyframes spin" .
```

**해결 방법**:
- `tw-animate-css` 또는 `tailwindcss-animate` 플러그인 확인
- CSS 애니메이션 정의 확인

---

## 📋 단계별 디버깅 플랜

### Step 1: 백엔드 로그 확인 (5분)

```bash
# 복합 질문 입력 후
tail -n 100 backend/logs/app.log | grep -E "execution_start|todo_updated|Active teams"
```

**확인 사항**:
- execution_start가 전송되는가?
- execution_steps 배열이 올바른가?
- todo_updated가 전송되는가?

---

### Step 2: 프론트엔드 콘솔 확인 (5분)

**추가 디버깅 코드**:

```typescript
// chat-interface.tsx Line 133-169에 추가
case 'execution_start':
  console.log('[DEBUG] ========== execution_start ==========')
  console.log('  message:', message)
  console.log('  execution_steps:', message.execution_steps)
  console.log('  execution_steps.length:', message.execution_steps?.length)
  console.log('  intent:', message.intent)
  console.log('  confidence:', message.confidence)
  console.log('  execution_strategy:', message.execution_strategy)

  if (message.execution_steps) {
    const progressMessage: Message = {
      // ... 기존 코드
    }

    console.log('  progressMessage created:', progressMessage)
    console.log('  progressMessage.executionSteps:', progressMessage.executionSteps)
    console.log('  progressMessage.executionPlan:', progressMessage.executionPlan)

    setMessages((prev) => {
      const filtered = prev.filter(m => m.type !== "execution-plan")
      const newMessages = filtered.concat(progressMessage)
      console.log('  prev messages:', prev.length)
      console.log('  filtered messages:', filtered.length)
      console.log('  new messages:', newMessages.length)
      console.log('  execution-progress count:', newMessages.filter(m => m.type === "execution-progress").length)
      return newMessages
    })

    // ... 기존 코드
  }
  console.log('[DEBUG] ========================================')
  break
```

**확인 사항**:
- execution_start 메시지가 수신되는가?
- execution_steps 배열이 2개인가?
- progressMessage가 정상 생성되는가?
- setMessages가 정상 실행되는가?

---

### Step 3: DOM 검사 (5분)

**복합 질문 입력 후**:

1. F12 → Elements 탭
2. Ctrl+F → "작업 실행 중" 검색
3. 찾은 요소 확인:
   - 존재하는가?
   - Settings 아이콘이 있는가?
   - animate-spin-slow 클래스가 있는가?
4. F12 → Animations 탭
   - 애니메이션이 실행 중인가?

---

### Step 4: CSS 애니메이션 확인 (5분)

```bash
cd frontend
grep -r "animate-spin-slow" .
grep -r "@keyframes spin" .
grep -r "tailwindcss-animate" .
```

**확인 사항**:
- animate-spin-slow가 어디서 정의되는가?
- CSS 애니메이션이 존재하는가?

---

## 🎯 결론 및 다음 단계

### 현재 상태

1. **근본 원인 미확인**: 추측만 가능, 실제 확인 필요
2. **디버깅 필요**: 백엔드 로그 + 프론트엔드 콘솔 + DOM 검사
3. **3가지 시나리오**: 생성 안 됨 vs 제거됨 vs CSS만 문제

### 다음 단계

#### 1단계: 사용자 디버깅 요청

**사용자에게 요청**:
```
복합 질문 ("강남구 아파트 시세 확인하고 투자 분석해줘") 입력 후:

1. 백엔드 로그 확인:
   tail -n 100 backend/logs/app.log | grep -E "execution_start|todo_updated"

2. 프론트엔드 콘솔 확인 (F12 → Console):
   - [ChatInterface] Received WS message: execution_start 있는가?
   - execution_steps: [...] 2개인가?

3. DOM 확인 (F12 → Elements → Ctrl+F "작업 실행 중"):
   - ExecutionProgressPage 컴포넌트가 보이는가?
   - Settings 아이콘 (<svg>)이 있는가?
   - animate-spin-slow 클래스가 적용되어 있는가?
```

#### 2단계: 디버깅 결과에 따른 해결책

**시나리오 A**: ExecutionProgressPage가 생성 안 됨
→ execution_start 메시지 payload 수정

**시나리오 B**: ExecutionProgressPage가 제거됨
→ todo_updated 로직 수정

**시나리오 C**: CSS 애니메이션만 문제
→ CSS 정의 확인 또는 key prop 추가

---

## 🚨 중요한 깨달음

### 이전 분석의 문제점

1. **추측에 기반한 해결책**: 실제 로그 없이 "React 18 Batching"이라고 단정
2. **코드만 보고 판단**: 실제 런타임 동작 확인 안 함
3. **단순한 해결책 제시**: key prop 추가 - 근본 원인 해결 안 될 수 있음

### 올바른 접근 방식

1. **실제 현상 확인**: 로그 + 콘솔 + DOM
2. **정확한 원인 파악**: 어느 지점에서 문제가 생기는가?
3. **최소 수정**: 근본 원인에 맞는 해결책

---

**작성 완료**: 2025-10-21
**상태**: 디버깅 플랜 제시
**다음 단계**: 사용자 디버깅 결과 대기

---

## 📌 사용자에게 전달할 요청사항

### 즉시 실행 가능한 디버깅 (선택 1개)

#### 옵션 A: 프론트엔드 콘솔 로그만 보기 (가장 빠름)

**chat-interface.tsx Line 133 수정**:

```typescript
case 'execution_start':
  console.log('[DEBUG-SPINNER] execution_start received')
  console.log('  steps count:', message.execution_steps?.length)
  console.log('  has executionPlan?:', !!message.executionPlan)

  if (message.execution_steps) {
    // 기존 코드
  } else {
    console.log('  [ERROR] execution_steps is missing!')
  }
  break
```

→ 복합 질문 입력 후 F12 콘솔 확인

#### 옵션 B: DOM만 확인 (코드 수정 없음)

→ 복합 질문 입력 후 F12 → Elements → "작업 실행 중" 검색

#### 옵션 C: 백엔드 로그만 확인 (코드 수정 없음)

```bash
tail -f backend/logs/app.log | grep -E "execution_start|Active teams"
```

→ 복합 질문 입력

---

이 분석 결과를 바탕으로 **정확한 디버깅 후** 해결책을 제시하는 것이 맞습니다.
