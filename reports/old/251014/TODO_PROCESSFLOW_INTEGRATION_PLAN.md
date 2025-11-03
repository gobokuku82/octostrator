# TODO 관리 시스템 + ProcessFlow 연동 구현 계획서 (통합판)

**작성일**: 2025-10-08
**작성자**: Claude Code
**목적**: ExecutionPlan을 ProcessFlow와 연동하여 실시간 진행 상황 시각화

---

## 📌 요구사항

### 기존 (백엔드 중심)
- LLM 기반 TODO 리스트 생성
- 사용자 개입 가능
- 진행 상황 추적
- Checkpoint 복원

### 신규 (프론트엔드 연동)
- **ProcessFlow 동적 생성**: ExecutionPlan → 프론트엔드 시각화 단계
- **실시간 동기화**: 백엔드 실행 상황을 ProcessFlow에 반영
- **정확한 매핑**: Agent 이름 → ProcessFlow 단계 자동 변환

---

## 🔗 ProcessFlow 연동 전략

### 핵심 아이디어
**`ExecutionStepState` (백엔드 TODO) → ProcessFlow Step (프론트엔드 시각화)**

```
[백엔드 ExecutionPlan]
steps = [
  ExecutionStepState(agent_name="search_agent", ...),
  ExecutionStepState(agent_name="analysis_agent", ...),
  ExecutionStepState(agent_name="response_generator", ...)
]

        ↓ StepMapper

[프론트엔드 ProcessFlow]
계획 ─── 검색 ─── 분석 ─── 생성
 ✓       ●        ○       ○
```

---

## 📐 Phase 0: StepMapper 추가 (최우선)

### 파일: `backend/app/api/step_mapper.py` ✨ 신규

```python
"""
ExecutionStep → ProcessFlow Step 매핑
백엔드 TODO를 프론트엔드 시각화 단계로 변환
"""

from typing import List, Dict, Any
from dataclasses import dataclass


@dataclass
class ProcessFlowStep:
    """프론트엔드 ProcessFlow 단계"""
    step: str  # "planning", "searching", "analyzing", "generating"
    label: str  # "계획", "검색", "분석", "생성"
    agent: str  # 담당 agent 이름
    status: str  # "pending", "in_progress", "completed", "failed"
    progress: int  # 0-100


class StepMapper:
    """ExecutionStepState → ProcessFlow 매핑"""

    # Agent → ProcessFlow Step 매핑 테이블
    AGENT_TO_STEP = {
        # Cognitive agents
        "planning_agent": "planning",
        "intent_analyzer": "planning",

        # Search agents
        "search_agent": "searching",
        "legal_search": "searching",
        "market_search": "searching",
        "real_estate_search": "searching",
        "loan_search": "searching",

        # Analysis agents
        "analysis_agent": "analyzing",
        "market_analysis": "analyzing",
        "risk_analysis": "analyzing",
        "contract_analyzer": "analyzing",

        # Document agents
        "document_agent": "analyzing",  # 문서 검토도 분석 단계
        "contract_reviewer": "analyzing",

        # Response generation
        "response_generator": "generating",
        "answer_synthesizer": "generating",
        "final_response": "generating"
    }

    STEP_LABELS = {
        "planning": "계획",
        "searching": "검색",
        "analyzing": "분석",
        "generating": "생성"
    }

    @classmethod
    def map_execution_steps(
        cls,
        execution_steps: List[Dict[str, Any]]
    ) -> List[ProcessFlowStep]:
        """
        ExecutionStepState[] → ProcessFlowStep[] 변환

        Args:
            execution_steps: PlanningState의 execution_steps

        Returns:
            ProcessFlow용 단계 리스트 (중복 제거됨)
        """
        flow_steps = []
        seen_steps = set()

        for exec_step in execution_steps:
            agent_name = exec_step.get("agent_name", "")

            # Agent → Step 매핑
            process_step = cls.AGENT_TO_STEP.get(
                agent_name,
                "processing"  # fallback
            )

            # 중복 제거 (같은 step이 여러 agent에서 나올 수 있음)
            if process_step in seen_steps:
                continue

            seen_steps.add(process_step)

            flow_steps.append(ProcessFlowStep(
                step=process_step,
                label=cls.STEP_LABELS.get(process_step, process_step),
                agent=agent_name,
                status=exec_step.get("status", "pending"),
                progress=exec_step.get("progress_percentage", 0)
            ))

        # 단계 순서 정렬 (planning → searching → analyzing → generating)
        step_order = ["planning", "searching", "analyzing", "generating"]
        flow_steps.sort(key=lambda x: step_order.index(x.step) if x.step in step_order else 999)

        return flow_steps

    @classmethod
    def get_current_step(cls, execution_steps: List[Dict[str, Any]]) -> str:
        """
        현재 실행 중인 ProcessFlow 단계 반환

        Returns:
            "planning", "searching", "analyzing", "generating" 중 하나
        """
        # in_progress인 step 찾기
        for exec_step in execution_steps:
            if exec_step.get("status") == "in_progress":
                agent_name = exec_step.get("agent_name", "")
                return cls.AGENT_TO_STEP.get(agent_name, "processing")

        # 없으면 다음 pending step
        for exec_step in execution_steps:
            if exec_step.get("status") == "pending":
                agent_name = exec_step.get("agent_name", "")
                return cls.AGENT_TO_STEP.get(agent_name, "processing")

        return "complete"
```

---

## 📐 Phase 6: API 응답 확장 (ChatResponse)

### 파일: `backend/app/api/schemas.py` 수정

```python
class ChatResponse(BaseModel):
    # 기존 필드들...
    session_id: str
    request_id: str
    status: str
    response: Dict[str, Any]
    planning_info: Optional[Dict[str, Any]] = None
    team_results: Optional[Dict[str, Any]] = None
    # ...

    # ✨ 신규: ProcessFlow 정보
    process_flow: Optional[Dict[str, Any]] = Field(
        default=None,
        description="프론트엔드 ProcessFlow용 단계 정보"
    )
    # {
    #   "steps": [
    #     {"step": "searching", "label": "검색", "status": "completed", "progress": 100},
    #     {"step": "analyzing", "label": "분석", "status": "in_progress", "progress": 50}
    #   ],
    #   "current_step": "analyzing",
    #   "overall_progress": 60,
    #   "total_steps": 3
    # }
```

### 파일: `backend/app/api/chat_api.py` 수정

```python
from app.api.step_mapper import StepMapper

@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest, ...):
    # ... 기존 로직 ...

    result = await supervisor.process_query(...)

    # ✨ ExecutionStepState → ProcessFlow 변환
    process_flow_info = None
    if result.get("planning_state"):
        execution_steps = result["planning_state"].get("execution_steps", [])

        if execution_steps:
            # Step 매핑
            flow_steps = StepMapper.map_execution_steps(execution_steps)
            current_step = StepMapper.get_current_step(execution_steps)

            # 전체 진행률 계산
            if flow_steps:
                total_progress = sum(s.progress for s in flow_steps) // len(flow_steps)
            else:
                total_progress = 0

            process_flow_info = {
                "steps": [
                    {
                        "step": s.step,
                        "label": s.label,
                        "agent": s.agent,
                        "status": s.status,
                        "progress": s.progress
                    }
                    for s in flow_steps
                ],
                "current_step": current_step,
                "overall_progress": total_progress,
                "total_steps": len(flow_steps)
            }

    # Response 생성
    chat_response = state_to_chat_response(result)
    chat_response.process_flow = process_flow_info  # ✨ 추가

    return chat_response
```

---

## 📐 Phase 7: SSE 실시간 동기화 (선택적)

### 파일: `backend/app/api/event_broker.py` ✨ 신규

```python
"""
Server-Sent Events (SSE) 브로커
실시간 ProcessFlow 상태 전송
"""

import asyncio
from typing import Dict
import logging

logger = logging.getLogger(__name__)


class EventBroker:
    """SSE 이벤트 브로커 (메모리 기반 - 단일 서버용)"""

    def __init__(self):
        self.queues: Dict[str, asyncio.Queue] = {}

    async def emit(self, session_id: str, event: Dict):
        """
        이벤트 발행

        Args:
            session_id: 세션 ID
            event: 이벤트 데이터
                {
                    "type": "step_start" | "step_complete" | "step_error",
                    "step": "searching" | "analyzing" | ...,
                    "message": str,
                    "progress": int
                }
        """
        if session_id in self.queues:
            try:
                await self.queues[session_id].put(event)
                logger.debug(f"Event emitted to {session_id}: {event.get('type')}")
            except Exception as e:
                logger.error(f"Failed to emit event: {e}")

    async def subscribe(self, session_id: str) -> asyncio.Queue:
        """
        이벤트 구독 (Queue 반환)

        Args:
            session_id: 세션 ID

        Returns:
            이벤트 Queue
        """
        queue = asyncio.Queue(maxsize=100)
        self.queues[session_id] = queue
        logger.info(f"Client subscribed to session: {session_id}")
        return queue

    def cleanup(self, session_id: str):
        """세션 정리"""
        if session_id in self.queues:
            del self.queues[session_id]
            logger.info(f"Session cleaned up: {session_id}")


# Singleton instance
event_broker = EventBroker()
```

### 파일: `backend/app/api/chat_api.py` - SSE 엔드포인트 추가

```python
from fastapi.responses import StreamingResponse
from app.api.event_broker import event_broker
import json

@router.get("/stream/{session_id}")
async def stream_process_flow(session_id: str):
    """
    SSE로 ProcessFlow 진행 상황 스트리밍

    프론트엔드에서 EventSource로 연결
    """

    async def event_generator():
        """이벤트 생성기"""
        queue = await event_broker.subscribe(session_id)

        try:
            while True:
                # 60초 타임아웃 (keep-alive)
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=60.0)

                    # SSE 포맷으로 전송
                    yield f"data: {json.dumps(event)}\n\n"

                    # 완료 이벤트 수신 시 종료
                    if event.get("type") == "complete":
                        break

                except asyncio.TimeoutError:
                    # Keep-alive
                    yield f"data: {json.dumps({'type': 'keepalive'})}\n\n"

        except Exception as e:
            logger.error(f"SSE stream error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

        finally:
            event_broker.cleanup(session_id)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Nginx용
        }
    )
```

### 파일: `backend/app/service_agent/supervisor/team_supervisor.py` - 이벤트 발생

```python
from app.api.event_broker import event_broker
from app.api.step_mapper import StepMapper

class TeamBasedSupervisor:

    async def planning_node(self, state: MainSupervisorState):
        session_id = state.get("session_id")

        # ✨ Planning 단계 시작 이벤트
        await event_broker.emit(session_id, {
            "type": "step_start",
            "step": "planning",
            "message": "계획을 수립하고 있습니다...",
            "progress": 0
        })

        # ... 기존 planning 로직 ...

        # ✨ Planning 단계 완료 이벤트
        await event_broker.emit(session_id, {
            "type": "step_complete",
            "step": "planning",
            "progress": 100
        })

        return state

    async def execute_teams_node(self, state: MainSupervisorState):
        session_id = state.get("session_id")
        active_teams = state.get("active_teams", [])

        for team_name in active_teams:
            # Agent → ProcessFlow step 변환
            process_step = StepMapper.AGENT_TO_STEP.get(team_name, "processing")

            # ✨ 팀 시작 이벤트
            await event_broker.emit(session_id, {
                "type": "step_start",
                "step": process_step,
                "message": f"{team_name} 실행 중...",
                "progress": 0
            })

            try:
                # 팀 실행 (기존 로직)
                result = await self._execute_single_team(team_name, ...)

                # ✨ 팀 완료 이벤트
                await event_broker.emit(session_id, {
                    "type": "step_complete",
                    "step": process_step,
                    "progress": 100
                })

            except Exception as e:
                # ✨ 에러 이벤트
                await event_broker.emit(session_id, {
                    "type": "step_error",
                    "step": process_step,
                    "message": str(e)
                })

        return state
```

---

## 📐 Phase 8: Frontend ProcessFlow 동적 렌더링

### 파일: `frontend/components/chat-interface.tsx` 수정

```typescript
const handleSendMessage = async (content: string) => {
  // 사용자 메시지 추가
  setMessages([...messages, userMessage])

  // ProcessFlow 메시지 추가 (임시)
  const processFlowMessage: Message = {
    id: "process-flow-temp",
    type: "process-flow",
    content: "",
    timestamp: new Date(),
  }
  setMessages(prev => [...prev, processFlowMessage])

  // ✨ SSE 연결 (선택적 - 실시간 동기화용)
  const eventSource = new EventSource(
    `${API_URL}/api/v1/chat/stream/${sessionId}`
  )

  eventSource.onmessage = (event) => {
    const data = JSON.parse(event.data)

    if (data.type === "step_start") {
      // 실시간 단계 업데이트
      setProcessState({
        step: data.step,
        message: data.message,
        agentType: mapStepToAgentType(data.step),
        startTime: Date.now()
      })
    } else if (data.type === "step_complete") {
      // 단계 완료 처리
    }
  }

  try {
    // API 호출
    const response = await chatAPI.sendMessage({
      query: content,
      session_id: sessionId
    })

    // ✨ ProcessFlow 단계 정보 활용
    if (response.process_flow) {
      // 동적으로 단계 생성 (현재는 하드코딩이었으나 이제 동적)
      const steps = response.process_flow.steps

      // 마지막 단계를 현재 진행 상태로 설정
      const lastStep = steps[steps.length - 1]
      setProcessState({
        step: lastStep.step,
        message: lastStep.label + " 완료",
        agentType: mapStepToAgentType(lastStep.step),
        startTime: Date.now()
      })
    }

    // ProcessFlow 메시지 제거
    setMessages(prev => prev.filter(m => m.id !== "process-flow-temp"))

    // 봇 응답 추가
    setMessages(prev => [...prev, botMessage])

  } finally {
    eventSource.close()
  }
}

// ✨ Step → AgentType 매핑
function mapStepToAgentType(step: string): AgentType | null {
  switch(step) {
    case "searching": return "search"
    case "analyzing": return "analysis"
    case "generating": return "consultation"
    default: return null
  }
}
```

### 파일: `frontend/components/process-flow.tsx` - 동적 단계 렌더링

```typescript
export function ProcessFlow({ isVisible, state }: ProcessFlowProps) {
  // ✨ API 응답에서 받은 steps로 동적 렌더링
  const [processSteps, setProcessSteps] = useState([
    { step: "planning", label: "계획" },
    { step: "searching", label: "검색" },
    { step: "analyzing", label: "분석" },
    { step: "generating", label: "생성" }
  ])

  // TODO: API 응답의 process_flow.steps를 받아서 동적 생성
  // useEffect(() => {
  //   if (apiResponse?.process_flow?.steps) {
  //     setProcessSteps(apiResponse.process_flow.steps)
  //   }
  // }, [apiResponse])

  return (
    <Card className="p-3">
      {/* 상단 헤더 */}
      <div className="flex items-center justify-between mb-3">
        ...
      </div>

      {/* 진행 단계 표시 (동적 생성) */}
      <div className="flex items-center gap-1">
        {processSteps.map((step, index) => (
          <React.Fragment key={step.step}>
            <StepIndicator
              label={step.label}
              isActive={state.step === step.step}
              isComplete={isStepBefore(state.step, step.step)}
            />
            {index < processSteps.length - 1 && (
              <StepConnector
                isComplete={isStepBefore(state.step, step.step)}
              />
            )}
          </React.Fragment>
        ))}
      </div>
    </Card>
  )
}
```

---

## 📊 통합 데이터 흐름

```
1. 사용자 질문: "전세금 인상 한도는?"
   ↓
2. PlanningAgent → ExecutionPlan 생성
   steps = [
     ExecutionStep(agent_name="legal_search"),
     ExecutionStep(agent_name="market_analysis"),
     ExecutionStep(agent_name="response_generator")
   ]
   ↓
3. ExecutionStep → ExecutionStepState 변환 (Phase 1)
   execution_steps = [
     {step_id: "step_0", agent_name: "legal_search", status: "pending", ...},
     {step_id: "step_1", agent_name: "market_analysis", status: "pending", ...},
     {step_id: "step_2", agent_name: "response_generator", status: "pending", ...}
   ]
   ↓
4. ✨ StepMapper → ProcessFlow steps 생성 (Phase 0)
   process_flow = {
     steps: [
       {step: "searching", label: "검색", status: "pending"},
       {step: "analyzing", label: "분석", status: "pending"},
       {step: "generating", label: "생성", status: "pending"}
     ]
   }
   ↓
5. ChatResponse에 process_flow 포함하여 Frontend로 전송
   ↓
6. Frontend: ProcessFlow 동적 렌더링
   계획 ─── 검색 ─── 분석 ─── 생성
    ✓       ●        ○       ○
   ↓
7. (선택적) SSE로 실시간 진행 상황 업데이트
   - planning_node 시작 → {"step": "planning", "progress": 0}
   - planning_node 완료 → {"step": "planning", "progress": 100}
   - execute_teams_node 시작 → {"step": "searching", "progress": 0}
   - ...
```

---

## 🗂️ 수정된 파일 구조

```
backend/app/
├── api/
│   ├── step_mapper.py              # ✨ 신규: ExecutionStep → ProcessFlow 매핑
│   ├── event_broker.py             # ✨ 신규: SSE 이벤트 브로커
│   ├── chat_api.py                 # ✨ 수정: process_flow 필드 추가, SSE 엔드포인트
│   ├── schemas.py                  # ✨ 수정: ChatResponse에 process_flow 추가
│   └── todo_api.py                 # ✨ 신규: TODO 관리 API (기존 계획)
│
├── service_agent/
│   ├── foundation/
│   │   ├── separated_states.py    # ✨ 확장: ExecutionStepState 표준화 (기존 계획)
│   │   └── checkpointer.py         # ✨ 확장: get_state(), list_checkpoints() (기존 계획)
│   │
│   └── supervisor/
│       └── team_supervisor.py      # ✨ 수정:
│                                   #   - ExecutionStep 상태 업데이트 (기존 계획)
│                                   #   - SSE 이벤트 발생 (신규)

frontend/
├── components/
│   ├── chat-interface.tsx          # ✨ 수정:
│   │                               #   - SSE 연결
│   │                               #   - process_flow 데이터 활용
│   └── process-flow.tsx            # ✨ 수정: 동적 단계 렌더링
│
└── types/
    └── process.ts                  # 기존 유지
```

---

## ⚡ 수정된 구현 순서

### Week 1: StepMapper + ProcessFlow 연동 (즉시)
- **Day 1**: `step_mapper.py` 구현
  - AGENT_TO_STEP 매핑 테이블
  - map_execution_steps() 메서드
  - get_current_step() 메서드

- **Day 2**: ChatResponse 확장
  - schemas.py에 process_flow 필드 추가
  - chat_api.py에서 StepMapper 호출
  - API 응답 테스트

- **Day 3**: Frontend 동적 렌더링
  - chat-interface.tsx 수정 (API 응답 활용)
  - process-flow.tsx 동적 단계 생성
  - 통합 테스트

### Week 2: SSE 실시간 동기화 (선택적)
- **Day 4-5**: EventBroker 구현
  - event_broker.py 작성
  - SSE 엔드포인트 추가
  - Frontend EventSource 연결

- **Day 6**: TeamSupervisor 이벤트 발생
  - planning_node, execute_teams_node 수정
  - 각 단계별 이벤트 emit

### Week 3-4: TODO 관리 시스템 (기존 계획 유지)
- **Day 7-14**: 기존 계획서대로 진행
  - ExecutionStepState 표준화
  - StateTransition 확장
  - TODO API 구현
  - Checkpoint 통합

---

## ✅ 신규 체크리스트

### Phase 0: StepMapper (신규)
- [ ] step_mapper.py 생성
- [ ] AGENT_TO_STEP 매핑 테이블 정의
- [ ] map_execution_steps() 구현
- [ ] get_current_step() 구현
- [ ] 단위 테스트

### Phase 6: API 확장 (신규)
- [ ] ChatResponse에 process_flow 필드 추가
- [ ] chat_api.py에서 StepMapper 호출
- [ ] process_flow 데이터 생성 로직
- [ ] API 응답 검증

### Phase 7: SSE (선택적)
- [ ] EventBroker 구현
- [ ] SSE 엔드포인트 추가
- [ ] TeamSupervisor 이벤트 발생
- [ ] Frontend EventSource 연결

### Phase 8: Frontend 동적 렌더링
- [ ] chat-interface.tsx - API 응답 활용
- [ ] process-flow.tsx - 동적 단계 생성
- [ ] Step 매핑 함수 구현
- [ ] 통합 테스트

---

## 📝 최종 요약

### 기존 계획 유지
- ExecutionStepState 표준화
- TODO 관리 API
- Checkpoint 통합
- 사용자 개입 메커니즘

### 신규 추가
1. **StepMapper**: ExecutionStep → ProcessFlow 자동 매핑
2. **ChatResponse 확장**: process_flow 필드 추가
3. **SSE 실시간 동기화** (선택적): 진행 상황 실시간 전송
4. **Frontend 동적 렌더링**: API 데이터 기반 ProcessFlow 생성

### 핵심 장점
✅ **정확한 매핑**: 백엔드 ExecutionPlan이 프론트 ProcessFlow에 정확히 반영
✅ **동적 단계**: 사용자 질문에 따라 ProcessFlow 단계가 자동 생성
✅ **실시간 동기화**: SSE로 백엔드 실제 진행 상황 전송
✅ **TODO 관리**: 사용자가 ExecutionStep 수정 가능
✅ **Checkpoint 복원**: 과거 상태로 롤백 가능

**예상 개발 기간**:
- ProcessFlow 연동만: **3-5일**
- TODO 관리 시스템 포함: **2-3주**
