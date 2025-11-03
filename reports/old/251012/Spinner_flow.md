📊 챗봇 동적 Spinner 작동 구조 분석
🔄 전체 플로우
[사용자] 질문 입력
   ↓
[Frontend] 사용자 메시지 추가 + 스피너 시작
   ↓
[Backend] WebSocket 메시지 수신
   ↓
[Backend] Planning 시작 → "planning_start" 전송
   ↓
[Frontend] "계획을 수립하고 있습니다..." 표시 (1단계)
   ↓
[Backend] Planning 완료 → "plan_ready" 전송
   ↓
[Frontend] ExecutionPlanPage 표시 (2단계)
   ↓
[Frontend] 800ms 후 ExecutionProgressPage 자동 생성 (3단계)
   ↓
[Backend] 팀 실행 → "todo_updated" 반복 전송
   ↓
[Frontend] ExecutionProgressPage 실시간 업데이트
   ↓
[Backend] 완료 → "final_response" 전송
   ↓
[Frontend] Progress 제거 + 답변 표시
1️⃣ "계획을 수립하고 있습니다..." (첫 번째 메시지)
Frontend: chat-interface.tsx
위치: handleSendMessage 함수 (240-272줄)
// 257-262줄: 프로세스 상태 설정
setProcessState({
  step: "planning",
  agentType,
  message: STEP_MESSAGES.planning,  // "계획을 수립하고 있습니다..."
  startTime: Date.now()
})
표시 위치: 357-364줄
// ExecutionProgressPage가 없을 때만 스피너 표시
{processState.step !== "idle" && !messages.some(m => m.type === "execution-progress") && (
  <div className="flex items-center gap-2 p-4 bg-muted/50 rounded-lg animate-pulse">
    <Loader2 className="w-4 h-4 animate-spin" />
    <span className="text-sm text-muted-foreground">
      {processState.message || "처리 중..."}  // "계획을 수립하고 있습니다..."
    </span>
  </div>
)}
Backend: team_supervisor.py
위치: planning_node 함수 (169-326줄)
# 178-188줄: Planning 시작 알림 전송
progress_callback = self._progress_callbacks.get(session_id)
if progress_callback:
    await progress_callback("planning_start", {
        "message": "계획을 수립하고 있습니다..."
    })
처리: chat_api.py → 249-255줄에서 WebSocket으로 전송
2️⃣ "작업 계획이 수립되었습니다" 페이지 (두 번째)
Frontend: ExecutionPlanPage 생성
위치: chat-interface.tsx 121-141줄
case 'plan_ready':
  // Backend에서 plan_ready 수신
  const planMessage: Message = {
    id: `execution-plan-${Date.now()}`,
    type: "execution-plan",  // ExecutionPlanPage 생성
    content: "",
    timestamp: new Date(),
    executionPlan: {
      intent: message.intent,
      confidence: message.confidence || 0,
      execution_steps: message.execution_steps,
      estimated_total_time: message.estimated_total_time || 5,
      keywords: message.keywords
    }
  }
  setMessages((prev) => [...prev, planMessage])
컴포넌트: execution-plan-page.tsx
구조:
48-133줄: 전체 컴포넌트
55-63줄: 헤더 ("작업 계획이 수립되었습니다")
65-89줄: 의도 정보 (감지된 의도, 신뢰도, 키워드)
91-117줄: 예정 작업 리스트
119-129줄: 예상 소요 시간 + 시작 안내
Backend: plan_ready 전송
위치: team_supervisor.py 310-325줄
# 계획 완료 알림
await progress_callback("plan_ready", {
    "intent": intent_result.intent_type.value,
    "confidence": intent_result.confidence,
    "execution_steps": planning_state["execution_steps"],
    "estimated_total_time": execution_plan.estimated_time,
    "keywords": intent_result.keywords
})
3️⃣ "작업 실행 중 (0/2 완료)" 페이지 (세 번째)
Frontend: ExecutionProgressPage 자동 생성
위치: chat-interface.tsx 142-157줄
// 800ms 후 ExecutionProgressPage 자동 생성 ⭐
setTimeout(() => {
  const progressMessage: Message = {
    id: `execution-progress-${Date.now()}`,
    type: "execution-progress",  // ExecutionProgressPage 생성
    content: "",
    timestamp: new Date(),
    executionPlan: planMessage.executionPlan,
    executionSteps: message.execution_steps.map((step: ExecutionStep) => ({
      ...step,
      status: step.status || "pending"
    }))
  }
  setMessages((prev) => [...prev, progressMessage])
}, 800)
핵심: plan_ready 수신 시 800ms 타이머 설정 → 자동으로 ExecutionProgressPage 생성
컴포넌트: execution-progress-page.tsx
구조:
25-163줄: 전체 컴포넌트
76-91줄: 헤더 ("작업 실행 중 (0/2 완료)")
93-106줄: 전체 진행률 바
108-118줄: 작업 리스트 (StepItem 반복)
120-149줄: 타이머 (경과/예상/남은 시간)
StepItem 컴포넌트: step-item.tsx
상태별 표시 (54-93줄):
pending: 🕐 대기 중 (회색)
in_progress: ⏳ 진행 중 (파란색 + 진행률 바)
completed: ✅ 완료 (초록색)
failed: ❌ 실패 (빨간색 + 에러 메시지)
🔄 실시간 업데이트: todo_updated
Frontend: ExecutionProgressPage Steps 업데이트
위치: chat-interface.tsx 160-180줄
case 'todo_updated':
  if (message.execution_steps) {
    setTodos(message.execution_steps)
    
    // ExecutionProgressPage 메시지 찾아서 steps 업데이트 ⭐
    setMessages((prev) => {
      return prev.map(msg => {
        if (msg.type === "execution-progress") {
          return {
            ...msg,
            executionSteps: message.execution_steps  // Steps 실시간 업데이트
          }
        }
        return msg
      })
    })
  }
Backend: todo_updated 전송
위치: team_supervisor.py 535-579줄
async def _execute_teams_sequential(...):
    for team_name in teams:
        # ✅ 실행 전: status = "in_progress"
        planning_state = StateManager.update_step_status(
            planning_state, step_id, "in_progress", progress=0
        )
        
        # WebSocket 전송
        await progress_callback("todo_updated", {
            "execution_steps": planning_state["execution_steps"]
        })
        
        # 팀 실행
        result = await self._execute_single_team(...)
        
        # ✅ 실행 완료: status = "completed"
        planning_state = StateManager.update_step_status(
            planning_state, step_id, "completed", result=result
        )
        
        # WebSocket 전송
        await progress_callback("todo_updated", {
            "execution_steps": planning_state["execution_steps"]
        })
🎯 핵심 메커니즘
1. 스피너 표시 조건
위치: chat-interface.tsx 357줄
processState.step !== "idle" && !messages.some(m => m.type === "execution-progress")
ExecutionProgressPage가 없을 때만 스피너 표시
ExecutionProgressPage가 생성되면 자동으로 스피너 제거
2. 800ms 타이머의 역할
문제: plan_ready와 첫 번째 todo_updated 사이 시간차
해결: ExecutionPlanPage 표시 후 800ms 기다림 → ExecutionProgressPage 생성
효과: 부드러운 전환 + 백엔드 수정 불필요
3. 타입 구조
ExecutionStep: types/execution.ts 15-37줄
interface ExecutionStep {
  step_id: string
  step_type: StepType
  agent_name: string
  team: string
  task: string           // 짧은 제목 (예: "정보 검색")
  description: string    // 상세 설명
  status: StepStatus     // pending | in_progress | completed | failed
  progress_percentage: number
  started_at: string | null
  completed_at: string | null
  result: Record<string, any> | null
  error: string | null
}
ProcessState: types/process.ts 20-38줄
interface ProcessState {
  step: ProcessStep           // idle | planning | executing | complete
  agentType: AgentType | null
  message: string             // 표시할 메시지
  progress?: number
  startTime?: number          // 타임스탬프
  error?: string
}
🔍 문제 발생 가능 지점
800ms 타이머 의존성
ExecutionProgressPage 생성이 고정 시간에 의존
Backend에서 execution_start 메시지 추가 시 개선 가능
스피너 중복 표시
조건: !messages.some(m => m.type === "execution-progress")
만약 ExecutionProgressPage가 제거되면 다시 스피너 표시
WebSocket 메시지 순서
planning_start → plan_ready → todo_updated (여러 번) → final_response
순서가 바뀌면 UI 깨짐
State 동기화
setMessages와 setTodos가 분리되어 있음
todo_updated 시 두 곳 모두 업데이트 필요