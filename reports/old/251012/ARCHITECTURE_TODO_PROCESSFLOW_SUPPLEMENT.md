# TODO + ProcessFlow Integration Supplement
## ARCHITECTURE_COMPLETE.md Part 13 추가 내용

**작성일**: 2025-10-08
**버전**: 1.0
**상태**: Production Ready

---

## 🔄 Part 13: TODO Management + ProcessFlow Integration

### 13.1 개요

**목적**: 백엔드 실행 상태를 실시간으로 추적하고 프론트엔드에서 시각화하는 통합 시스템 구축

**핵심 원칙**:
```
TODO (execution_steps) = 데이터 소스 (백엔드 상태 추적)
ProcessFlow = 데이터 뷰어 (프론트엔드 시각화)
```

### 13.2 아키텍처 다이어그램

```
┌─────────────────────────────────────────────────────────────────┐
│                    Backend: TODO Management                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. planning_node (team_supervisor.py)                          │
│     └─> ExecutionStepState[] 생성 (status="pending")           │
│                                                                  │
│  2. execute_teams_node (team_supervisor.py)                     │
│     ├─> StateManager.update_step_status(step_id, "in_progress")│
│     ├─> 팀 실행 (search/analysis/document)                     │
│     └─> StateManager.update_step_status(step_id, "completed")  │
│                                                                  │
│  3. PlanningState.execution_steps                               │
│     └─> List[ExecutionStepState] (status, progress, timing 포함)│
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│                    API Layer: Data Conversion                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  4. StepMapper (step_mapper.py)                                 │
│     └─> ExecutionStepState → ProcessFlowStep 변환              │
│         ├─ Agent/Team 이름 → step 타입 매핑                     │
│         ├─ 중복 제거 (같은 step은 가장 진행도 높은 것만)        │
│         └─ 순서 정렬 (planning→searching→analyzing→generating) │
│                                                                  │
│  5. converters.py                                                │
│     └─> ChatResponse.process_flow 필드 생성                     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│                   Frontend: ProcessFlow UI                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  6. ChatInterface (chat-interface.tsx)                          │
│     ├─> API 호출 후 response.process_flow 추출                 │
│     └─> Message.processFlowSteps에 저장                        │
│                                                                  │
│  7. ProcessFlow Component (process-flow.tsx)                    │
│     ├─> dynamicSteps prop 수신                                  │
│     └─> 동적 단계 렌더링 (계획→검색→분석→생성)                 │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 13.3 핵심 데이터 구조

#### ExecutionStepState (Backend)
```python
class ExecutionStepState(TypedDict):
    step_id: str
    agent_name: str
    team: str
    status: Literal["pending", "in_progress", "completed", "failed", ...]
    progress_percentage: int  # 0-100
    started_at: Optional[str]
    completed_at: Optional[str]
    execution_time_ms: Optional[int]
    result: Optional[Dict[str, Any]]
    error: Optional[str]
```

#### ProcessFlowStep (API & Frontend)
```python
# Backend (Pydantic)
class ProcessFlowStep(BaseModel):
    step: str       # "planning", "searching", "analyzing", "generating"
    label: str      # "계획", "검색", "분석", "생성"
    agent: str
    status: str
    progress: int   # 0-100

# Frontend (TypeScript)
interface ProcessFlowStep {
  step: "planning" | "searching" | "analyzing" | "generating" | "processing"
  label: string
  agent: string
  status: "pending" | "in_progress" | "completed" | "failed" | ...
  progress: number
}
```

### 13.4 수정된 파일

#### Backend (7개)
1. `separated_states.py` - ExecutionStepState, StateManager.update_step_status()
2. `team_supervisor.py` - status tracking 통합
3. `step_mapper.py` - NEW: 데이터 변환 레이어
4. `schemas.py` - ProcessFlowStep 모델 추가
5. `converters.py` - process_flow 생성 로직
6. `test_status_tracking.py` - NEW: Phase 1-3 테스트
7. `test_process_flow_api.py` - NEW: Phase 4-5 테스트

#### Frontend (3개)
1. `types/chat.ts` - ProcessFlowStep 인터페이스
2. `process-flow.tsx` - dynamicSteps 지원
3. `chat-interface.tsx` - API 데이터 통합

### 13.5 테스트 결과

**Phase 1-3 (TODO Status Tracking)**: ✅ PASS
- execution_time_ms: 2603ms (실제 실행 시간 기록)
- status, progress, timing 필드 정상 작동

**Phase 4-5 (ProcessFlow API)**: ✅ PASS
- process_flow 필드 정상 생성
- 1개 step: "검색 (searching) - completed - 100%"

### 13.6 API 응답 예시

```json
{
  "process_flow": [
    {
      "step": "searching",
      "label": "검색",
      "agent": "search_team",
      "status": "completed",
      "progress": 100
    }
  ],
  "planning_info": {
    "execution_steps": [
      {
        "step_id": "step_0",
        "status": "completed",
        "execution_time_ms": 2603
      }
    ]
  }
}
```

### 13.7 관련 문서

- `TODO_PROCESSFLOW_IMPLEMENTATION_COMPLETE.md` - 상세 구현 보고서
- `BROWSER_TEST_GUIDE.md` - 브라우저 테스트 가이드
- `TODO_PROCESSFLOW_CORRECTED_PLAN.md` - 구현 계획서

### 13.8 배포 상태 (2025-10-08)

- ✅ Backend: 완료 (http://localhost:8000)
- ✅ Frontend: 완료 (http://localhost:3001)
- ✅ Part 1-2: TODO tracking + ProcessFlow integration 완료
- ⏳ Part 3: SSE 실시간 스트리밍 (선택사항, 미구현)

---

**이 내용은 ARCHITECTURE_COMPLETE.md의 Part 13으로 통합되어야 합니다.**
