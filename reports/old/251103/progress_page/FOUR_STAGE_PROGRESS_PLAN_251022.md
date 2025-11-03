# 4단계 Progress UI 설계 계획서

**작성일**: 2025-10-22
**목적**: 3단계 → 4단계 Progress 확장 (분석 중 단계 추가)
**방법**: 백엔드 WebSocket 신호 추가 (정확한 타이밍)

---

## 🎯 4단계 구조

### 기존 (3단계)

1. **계획 중** (execution-plan-page) - `plan_ready`
2. **실행 중** (execution-progress-page) - `execution_start`
3. **답변 작성 중** (response-generating-page) - `response_generating_start`

### 신규 (4단계)

1. **출동 중** - `dispatch_start` (신규)
2. **분석 중** - `analysis_start` (신규)
3. **실행 중** - `execution_start` (기존)
4. **답변 작성 중** - `response_generating_start` (기존)

---

## 📊 신호 타이밍 분석

### 현재 team_supervisor.py 흐름

```python
async def planning_node(state):
    # 📍 여기: dispatch_start 추가
    await progress_callback("dispatch_start", {
        "message": "AI 에이전트가 출동 중입니다..."
    })

    # 의도 분석 시작
    intent_result = await self.planning_agent.analyze_intent(query)

    # 📍 여기: analysis_start 추가
    await progress_callback("analysis_start", {
        "message": "질문을 분석하고 실행 계획을 수립하고 있습니다...",
        "intent": intent_result.intent_type
    })

    # 실행 계획 생성
    execution_plan = await self.planning_agent.create_execution_plan(intent_result)

    # 기존: plan_ready
    await progress_callback("plan_ready", {
        "intent": intent_result.intent_type.value,
        "execution_steps": planning_state["execution_steps"],
        ...
    })
```

---

## 🔧 백엔드 수정 사항

### 1. team_supervisor.py - planning_node 수정

**파일**: `backend/app/service_agent/supervisor/team_supervisor.py`

**Line 174-501 수정**:

```python
async def planning_node(self, state: MainSupervisorState) -> MainSupervisorState:
    """
    계획 수립 노드 (4단계 진행 표시)
    """
    logger.info("[TeamSupervisor] Planning phase")

    state["current_phase"] = "planning"

    # ============================================================================
    # 🆕 1단계: 출동 중 (Dispatch)
    # ============================================================================
    session_id = state.get("session_id")
    progress_callback = self._progress_callbacks.get(session_id) if session_id else None

    if progress_callback:
        try:
            await progress_callback("dispatch_start", {
                "message": "AI 에이전트가 출동 중입니다...",
                "stage": "dispatch"
            })
            logger.info("[TeamSupervisor] Sent dispatch_start via WebSocket")
        except Exception as e:
            logger.error(f"[TeamSupervisor] Failed to send dispatch_start: {e}")

    # 의도 분석 준비
    query = state.get("query", "")
    chat_session_id = state.get("chat_session_id")

    # Chat history 조회
    chat_history = await self._get_chat_history(
        session_id=chat_session_id,
        limit=3
    )

    context = {"chat_history": chat_history} if chat_history else None

    # ============================================================================
    # 🆕 2단계: 분석 중 (Analysis)
    # ============================================================================
    if progress_callback:
        try:
            await progress_callback("analysis_start", {
                "message": "질문을 분석하고 실행 계획을 수립하고 있습니다...",
                "stage": "analysis"
            })
            logger.info("[TeamSupervisor] Sent analysis_start via WebSocket")
        except Exception as e:
            logger.error(f"[TeamSupervisor] Failed to send analysis_start: {e}")

    # Intent 분석 (시간이 걸리는 작업)
    intent_result = await self.planning_agent.analyze_intent(query, context)

    # 데이터 재사용 로직
    reuse_intent = intent_result.entities.get("reuse_previous_data", False) if intent_result.entities else False
    state["reuse_intent"] = reuse_intent

    # ... (기존 데이터 재사용 로직)

    # Long-term Memory 로딩
    # ... (기존 메모리 로딩 로직)

    # IRRELEVANT/UNCLEAR 조기 종료
    if intent_result.intent_type == IntentType.IRRELEVANT:
        # ... (기존 로직)
        pass

    if intent_result.intent_type == IntentType.UNCLEAR and intent_result.confidence < 0.3:
        # ... (기존 로직)
        pass

    # 실행 계획 생성
    execution_plan = await self.planning_agent.create_execution_plan(intent_result)

    # Planning State 생성
    planning_state = PlanningState(
        # ... (기존 로직)
    )

    state["planning_state"] = planning_state
    state["execution_plan"] = {
        "intent": intent_result.intent_type.value,
        "strategy": execution_plan.strategy.value,
        "steps": planning_state["execution_steps"]
    }

    # 활성화할 팀 결정
    active_teams = []
    # ... (기존 로직)

    state["active_teams"] = active_teams

    # ============================================================================
    # 기존: plan_ready (이제 분석 완료를 의미)
    # ============================================================================
    if progress_callback:
        try:
            await progress_callback("plan_ready", {
                "intent": intent_result.intent_type.value,
                "confidence": intent_result.confidence,
                "execution_steps": planning_state["execution_steps"],
                "execution_strategy": execution_plan.strategy.value,
                "estimated_total_time": execution_plan.estimated_time,
                "keywords": intent_result.keywords
            })
            logger.info("[TeamSupervisor] Sent plan_ready via WebSocket")
        except Exception as e:
            logger.error(f"[TeamSupervisor] Failed to send plan_ready: {e}")

    return state
```

---

## 📱 프론트엔드 수정 사항

### 1. chat-interface.tsx - 신호 핸들러 추가

**파일**: `frontend/components/chat-interface.tsx`

**handleWSMessage 함수에 추가**:

```typescript
const handleWSMessage = useCallback((message: WSMessage) => {
  console.log('[ChatInterface] Received WS message:', message.type)

  switch (message.type) {
    // ... (기존 코드)

    // 🆕 1단계: 출동 중
    case 'dispatch_start':
      console.log('[ChatInterface] Dispatch started')
      setMessages((prev) => {
        const newMessages = [...prev]
        const lastMsg = newMessages[newMessages.length - 1]

        if (lastMsg?.type === "execution-plan") {
          // 기존 execution-plan 메시지 업데이트
          lastMsg.executionPlan = {
            ...lastMsg.executionPlan,
            stage: "dispatch",
            message: message.message || "AI 에이전트가 출동 중입니다..."
          }
        }

        return newMessages
      })
      break

    // 🆕 2단계: 분석 중
    case 'analysis_start':
      console.log('[ChatInterface] Analysis started')
      setMessages((prev) => {
        const newMessages = [...prev]
        const lastMsg = newMessages[newMessages.length - 1]

        if (lastMsg?.type === "execution-plan") {
          lastMsg.executionPlan = {
            ...lastMsg.executionPlan,
            stage: "analysis",
            message: message.message || "질문을 분석하고 있습니다..."
          }
        }

        return newMessages
      })
      break

    // 기존: plan_ready (이제 3단계로 사용 안 함, 분석 완료만 표시)
    case 'plan_ready':
      // ... (기존 로직 유지)
      break

    // 🆕 3단계: 실행 중
    case 'execution_start':
      // ... (기존 로직 - execution-progress 메시지 생성)
      break

    // 🆕 4단계: 답변 작성 중
    case 'response_generating_start':
      // ... (기존 로직 - response-generating 메시지 생성)
      break

    // ...
  }
}, [])
```

---

### 2. ExecutionPlanPage 수정 - stage 처리

**파일**: `frontend/components/execution-plan-page.tsx` (또는 통합 ProgressContainer)

```tsx
interface ExecutionPlan {
  // 기존 필드
  intent: string
  confidence: number
  execution_steps: ExecutionStep[]
  // ...

  // 🆕 신규 필드
  stage?: "dispatch" | "analysis" | "plan_ready"
  message?: string
}

export function ExecutionPlanPage({ plan }: ExecutionPlanPageProps) {
  const { stage = "dispatch", message, isLoading } = plan

  // Stage별 제목
  const titles = {
    dispatch: "AI 에이전트 출동 중",
    analysis: "질문 분석 중",
    plan_ready: "작업 계획 수립 완료"
  }

  // Stage별 스피너
  const spinners = {
    dispatch: "/animation/spinner/1_dispatch_spinner.gif",
    analysis: "/animation/spinner/2_analysis_spinner.gif",
    plan_ready: "/animation/spinner/1_execution-plan_spinner.gif"
  }

  return (
    <Card>
      <h3>{titles[stage]}</h3>
      <p>{message}</p>

      <img src={spinners[stage]} alt={stage} />

      {stage === "plan_ready" && (
        <div>
          {/* 실행 계획 표시 */}
        </div>
      )}
    </Card>
  )
}
```

---

## 🎨 통합 ProgressContainer로 구현

**4단계를 하나의 컨테이너로 관리**:

```tsx
interface ProgressData {
  stage: "dispatch" | "analysis" | "executing" | "generating"
  message: string
  steps?: ProgressStep[]
  agents?: AgentInfo[]
}

export function ProgressContainer({ data }: { data: ProgressData }) {
  // Stage별 스피너
  const spinners = {
    dispatch: [
      { id: "1", status: "active", label: "출동" }
    ],
    analysis: [
      { id: "1", status: "completed", label: "출동" },
      { id: "2", status: "active", label: "분석" }
    ],
    executing: [
      { id: "1", status: "completed", label: "출동" },
      { id: "2", status: "completed", label: "분석" },
      { id: "3", status: "active", label: "실행" }
    ],
    generating: [
      { id: "1", status: "completed", label: "출동" },
      { id: "2", status: "completed", label: "분석" },
      { id: "3", status: "completed", label: "실행" },
      { id: "4", status: "active", label: "작성" }
    ]
  }

  return (
    <Card>
      {/* 상단: 스피너들 */}
      <ProgressSteps steps={spinners[data.stage]} />

      {/* 하단: Agent 카드들 (executing 단계만) */}
      {data.stage === "executing" && data.agents && (
        <ProgressContent agents={data.agents} />
      )}
    </Card>
  )
}
```

---

## ✅ 구현 체크리스트

### 백엔드 수정
- [ ] team_supervisor.py Line 189: `dispatch_start` 신호 추가
- [ ] team_supervisor.py Line 250: `analysis_start` 신호 추가
- [ ] 신호 데이터에 `stage` 필드 포함

### 프론트엔드 수정
- [ ] chat-interface.tsx: `dispatch_start` 핸들러 추가
- [ ] chat-interface.tsx: `analysis_start` 핸들러 추가
- [ ] ExecutionPlan 인터페이스에 `stage` 필드 추가
- [ ] ProgressContainer에서 4단계 처리

### 테스트
- [ ] 백엔드 빌드 성공
- [ ] 프론트엔드 빌드 성공
- [ ] WebSocket 신호 전송 확인
- [ ] 4단계 전환 시각적 확인

---

## 📊 타이밍 예상

| 단계 | 신호 | 소요 시간 (예상) | 누적 시간 |
|------|------|---------------|----------|
| 1. 출동 중 | `dispatch_start` | 즉시 | 0.1초 |
| 2. 분석 중 | `analysis_start` | 0.5-2초 | 0.6-2.1초 |
| 3. 실행 중 | `execution_start` | 3-10초 | 3.6-12.1초 |
| 4. 답변 작성 중 | `response_generating_start` | 2-5초 | 5.6-17.1초 |

**장점**: 백엔드 처리 시간에 따라 자동으로 타이밍 조절

---

## 🚀 다음 단계

1. **백엔드 먼저 수정** → 신호 2개 추가
2. **프론트엔드 핸들러 추가** → 신호 받기
3. **통합 ProgressContainer 구현** → 4단계 표시
4. **테스트** → 실제 동작 확인

---

## 🎯 결론

**추천: 백엔드 신호 추가 방식**

**이유**:
1. ✅ 정확한 타이밍 (백엔드 로직과 동기화)
2. ✅ 확장 가능 (5단계, 6단계도 쉽게 추가)
3. ✅ 유지보수 용이 (프론트엔드는 신호만 받으면 됨)
4. ✅ 사용자 경험 향상 (실제 진행 상황 반영)

**프론트엔드 타이머는 비추천**:
- 백엔드와 타이밍 불일치
- 유지보수 어려움
- 사용자에게 부정확한 정보 제공

---

**승인 여부**: 이 방식으로 진행할까요?
