# TODO + ProcessFlow 통합 구현 계획서 (수정판)

**작성일**: 2025-10-08
**기반**: TODO_PROCESSFLOW_CODE_REVIEW.md 분석 결과
**목적**: 코드 검토 결과를 반영한 정확한 구현 계획

---

## 🎯 핵심 원칙: TODO가 ProcessFlow의 데이터 소스

### 아키텍처 개념

```
┌─────────────────────────────────────────────────────────────────┐
│                         백엔드 (Data Source)                      │
│                                                                   │
│  LangGraph Workflow                                               │
│  ┌───────────┐    ┌──────────────┐    ┌────────────────┐        │
│  │ Planning  │ →  │ Execute Teams│ →  │  Aggregate     │         │
│  │   Node    │    │     Node     │    │  Results Node  │         │
│  └─────┬─────┘    └──────┬───────┘    └────────────────┘        │
│        │                  │                                        │
│        ↓                  ↓                                        │
│  execution_steps     status 업데이트                              │
│  (TODO List)         (pending → in_progress → completed)          │
│                                                                   │
│        │                                                          │
│        ↓                                                          │
│  ┌──────────────┐                                                │
│  │ StepMapper   │  ExecutionStep → ProcessFlowStep 변환          │
│  └──────┬───────┘                                                │
│         │                                                         │
│         ↓                                                         │
│  ┌──────────────┐                                                │
│  │ ChatResponse │  process_flow 필드로 프론트엔드에 전달          │
│  └──────┬───────┘                                                │
└─────────┼──────────────────────────────────────────────────────┘
          │
          ↓ API Response
┌─────────────────────────────────────────────────────────────────┐
│                       프론트엔드 (Viewer)                         │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ ProcessFlow Component                                      │   │
│  │                                                            │   │
│  │  계획 ───── 검색 ───── 분석 ───── 생성                     │   │
│  │   ✓         ●         ○         ○                         │   │
│  │                                                            │   │
│  │  (API response.process_flow 기반 동적 렌더링)              │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### 왜 TODO가 먼저인가?

**ProcessFlow는 TODO의 시각화 도구일 뿐입니다.**

1. **데이터 의존성**:
   - ProcessFlow는 `execution_steps`의 status를 읽어서 표시
   - execution_steps에 status가 없으면 → ProcessFlow가 뭘 표시할지 알 수 없음

2. **현재 문제**:
   - ❌ execution_steps에 status 필드 없음
   - ❌ Frontend는 hardcoded setTimeout으로 fake progress 표시
   - ❌ 백엔드 실제 진행 상황과 완전히 분리됨

3. **해결 순서**:
   1. **먼저**: execution_steps에 status 추적 기능 추가 (Phase 1-2)
   2. **그 다음**: StepMapper로 변환 (Phase 3)
   3. **마지막**: Frontend가 API 데이터 표시 (Phase 4-5)

---

## 📊 현황 요약

### ✅ 이미 구현됨
- LangGraph 워크플로우 (initialize → planning → execute_teams → aggregate → generate_response)
- ExecutionPlan 생성 (PlanningAgent)
- execution_steps 생성 (team_supervisor.py:planning_node)
- Frontend ProcessFlow UI 컴포넌트 (horizontal layout, 계획/검색/분석/생성)
- ProcessFlow를 chat message로 표시

### ❌ 미구현 (구현 필요)
- ❌ execution_steps에 status 필드 ("pending", "in_progress", "completed", "failed")
- ❌ execute_teams_node에서 status 업데이트 로직
- ❌ StepMapper (ExecutionStep → ProcessFlow 변환)
- ❌ ChatResponse.process_flow 필드
- ❌ Frontend에서 API response 기반 동적 step 생성

---

## 🎯 구현 계획 (3부 구성)

### Part 1: TODO 상태 추적 (Phase 1-2) ⭐ 최우선 필수
**목표**: execution_steps가 실시간으로 상태를 추적하도록 만들기
**의존성**: 없음 (가장 먼저 시작)
**완료 조건**: execution_steps에 status, progress_percentage, start_time, end_time 필드 추가 및 업데이트

### Part 2: ProcessFlow 연동 (Phase 3-5) 📡 필수
**목표**: TODO 데이터를 Frontend ProcessFlow로 전달
**의존성**: Part 1 완료 후 시작 (status 데이터가 있어야 함)
**완료 조건**: API response에 process_flow 필드 추가, Frontend에서 동적 렌더링

### Part 3: 실시간 스트리밍 (Phase 6) 🔮 Optional
**목표**: SSE로 실시간 진행 상황 업데이트
**의존성**: Part 2 완료 후
**완료 조건**: 현재는 완료 후 한 번에 전달 → 실시간으로 업데이트

---

## Part 1: TODO 상태 추적 (Phase 1-2) ⭐

### 왜 이 단계가 필요한가?

현재 execution_steps는 생성만 되고 상태 추적이 안 됩니다:

```python
# 현재 (문제)
execution_steps = [
    {
        "step_id": "step_0",
        "agent_name": "search_agent",
        "team": "search",
        # ❌ status 없음 - 실행 중인지 완료됐는지 알 수 없음
    }
]

# 필요 (해결)
execution_steps = [
    {
        "step_id": "step_0",
        "agent_name": "search_agent",
        "team": "search",
        "status": "completed",  # ✅ 추가
        "progress_percentage": 100,  # ✅ 추가
        "start_time": 1696800000.0,  # ✅ 추가
        "end_time": 1696800005.0  # ✅ 추가
    }
]
```

이 데이터가 있어야 ProcessFlow가 "어느 단계가 완료됐고, 어느 단계가 진행 중인지" 표시할 수 있습니다.

### Phase 1: ExecutionStepState 타입 표준화

#### 목표
`execution_steps`를 `List[Dict[str, Any]]`에서 표준화된 TypedDict로 변경

#### 1.1 ExecutionStepState 정의 추가

**파일**: `backend/app/service_agent/foundation/separated_states.py`

**위치**: Line 235 (PlanningState 정의 바로 위)

**추가 코드**:
```python
class ExecutionStepState(TypedDict):
    """실행 단계 상태 (표준화된 구조)"""
    # 기본 정보
    step_id: str
    agent_name: str
    team: str
    priority: int
    dependencies: List[str]

    # 상태 추적 (NEW)
    status: Literal["pending", "in_progress", "completed", "failed"]
    progress_percentage: int  # 0-100

    # 타이밍
    estimated_time: float
    start_time: Optional[float]
    end_time: Optional[float]

    # 기타
    required: bool
    error_message: Optional[str]
```

#### 1.2 PlanningState 타입 변경

**파일**: `backend/app/service_agent/foundation/separated_states.py`

**위치**: Line 243

**변경 전**:
```python
execution_steps: List[Dict[str, Any]]
```

**변경 후**:
```python
execution_steps: List[ExecutionStepState]
```

#### 1.3 planning_node에서 status 초기화

**파일**: `backend/app/service_agent/supervisor/team_supervisor.py`

**위치**: Lines 174-184

**변경 전**:
```python
execution_steps=[
    {
        "step_id": f"step_{i}",
        "agent_name": step.agent_name,
        "team": self._get_team_for_agent(step.agent_name),
        "priority": step.priority,
        "dependencies": step.dependencies,
        "estimated_time": step.timeout,
        "required": not step.optional
    }
    for i, step in enumerate(execution_plan.steps)
]
```

**변경 후**:
```python
execution_steps=[
    {
        "step_id": f"step_{i}",
        "agent_name": step.agent_name,
        "team": self._get_team_for_agent(step.agent_name),
        "priority": step.priority,
        "dependencies": step.dependencies,
        "estimated_time": step.timeout,
        "required": not step.optional,

        # 상태 추적 필드 추가
        "status": "pending",
        "progress_percentage": 0,
        "start_time": None,
        "end_time": None,
        "error_message": None
    }
    for i, step in enumerate(execution_plan.steps)
]
```

---

### Phase 2: Status 추적 로직 추가

#### 목표
execute_teams_node에서 실시간으로 execution_steps의 status를 업데이트

#### 2.1 Status 업데이트 헬퍼 메서드 추가

**파일**: `backend/app/service_agent/supervisor/team_supervisor.py`

**위치**: Line 237 (execute_teams_node 바로 위)

**추가 코드**:
```python
def _update_step_status(
    self,
    state: MainSupervisorState,
    team_name: str,
    status: str,
    error_message: Optional[str] = None
) -> None:
    """
    특정 팀에 속한 execution_steps의 status 업데이트

    Args:
        state: MainSupervisorState
        team_name: 팀 이름 (search, document, analysis)
        status: 새 상태 ("in_progress", "completed", "failed")
        error_message: 에러 메시지 (status="failed"일 때)
    """
    planning_state = state.get("planning_state")
    if not planning_state:
        return

    import time
    current_time = time.time()

    for step in planning_state.get("execution_steps", []):
        if step.get("team") == team_name:
            step["status"] = status

            if status == "in_progress":
                step["start_time"] = current_time
                step["progress_percentage"] = 50  # 실행 중일 때 50%

            elif status == "completed":
                step["end_time"] = current_time
                step["progress_percentage"] = 100

            elif status == "failed":
                step["end_time"] = current_time
                step["progress_percentage"] = 0
                step["error_message"] = error_message

            logger.debug(
                f"Updated step status: agent={step.get('agent_name')}, "
                f"team={team_name}, status={status}"
            )
```

#### 2.2 execute_teams_node 수정

**파일**: `backend/app/service_agent/supervisor/team_supervisor.py`

**위치**: Lines 238-268

**수정 내용**:

**AS-IS**:
```python
async def execute_teams_node(self, state: MainSupervisorState) -> MainSupervisorState:
    logger.info("[TeamSupervisor] Executing teams")
    state["current_phase"] = "executing"

    execution_strategy = state.get("execution_plan", {}).get("strategy", "sequential")
    active_teams = state.get("active_teams", [])

    # 팀별 실행
    if execution_strategy == "parallel" and len(active_teams) > 1:
        results = await self._execute_teams_parallel(active_teams, shared_state, state)
    else:
        results = await self._execute_teams_sequential(active_teams, shared_state, state)

    # 결과 저장
    for team_name, team_result in results.items():
        state = StateManager.merge_team_results(state, team_name, team_result)

    return state
```

**TO-BE** (status 업데이트 추가):
```python
async def execute_teams_node(self, state: MainSupervisorState) -> MainSupervisorState:
    logger.info("[TeamSupervisor] Executing teams")
    state["current_phase"] = "executing"

    execution_strategy = state.get("execution_plan", {}).get("strategy", "sequential")
    active_teams = state.get("active_teams", [])

    # 공유 상태 생성
    shared_state = StateManager.create_shared_state(
        query=state["query"],
        session_id=state["session_id"]
    )

    # 팀별 실행
    if execution_strategy == "parallel" and len(active_teams) > 1:
        # 병렬 실행
        results = await self._execute_teams_parallel(active_teams, shared_state, state)
    else:
        # 순차 실행 (status 업데이트 포함)
        results = {}
        for team_name in active_teams:
            if team_name in self.teams:
                # 1️⃣ 실행 전: status = "in_progress"
                self._update_step_status(state, team_name, "in_progress")

                try:
                    result = await self._execute_single_team(team_name, shared_state, state)
                    results[team_name] = result

                    # 2️⃣ 실행 성공: status = "completed"
                    self._update_step_status(state, team_name, "completed")

                    logger.info(f"[TeamSupervisor] Team '{team_name}' completed")

                    # 데이터 전달
                    if team_name == "search" and "analysis" in active_teams:
                        state["team_results"][team_name] = self._extract_team_data(result, team_name)

                except Exception as e:
                    # 3️⃣ 실행 실패: status = "failed"
                    logger.error(f"[TeamSupervisor] Team '{team_name}' failed: {e}")
                    self._update_step_status(state, team_name, "failed", str(e))
                    results[team_name] = {"status": "failed", "error": str(e)}

    # 결과 저장
    for team_name, team_result in results.items():
        state = StateManager.merge_team_results(state, team_name, team_result)

    return state
```

**주요 변경점**:
1. 팀 실행 전에 `_update_step_status(state, team_name, "in_progress")` 호출
2. 팀 실행 성공 시 `_update_step_status(state, team_name, "completed")` 호출
3. 팀 실행 실패 시 `_update_step_status(state, team_name, "failed", error_msg)` 호출

---

## Part 2: ProcessFlow 연동 (Phase 3-5) 📡

### 왜 이 단계가 필요한가?

Part 1에서 execution_steps에 status 데이터를 추가했습니다. 이제 이 데이터를:
1. **Frontend가 이해하는 형식으로 변환** (StepMapper)
2. **API response로 전달** (ChatResponse.process_flow)
3. **Frontend에서 표시** (ProcessFlow 컴포넌트)

해야 합니다.

```
execution_steps (백엔드)          →  StepMapper  →  process_flow (API)  →  ProcessFlow UI
[                                                    [                        계획 ─── 검색
  {                                                    {                       ✓       ●
    agent_name: "search_agent",                          step: "searching",
    status: "completed",                                 label: "검색",
    progress: 100                                        status: "completed"
  }                                                    }
]                                                    ]
```

**의존성**: Part 1 완료 필수 (execution_steps에 status가 있어야 변환 가능)

---

### Phase 3: StepMapper 구현

#### 목표
ExecutionStepState → ProcessFlow Step 변환

#### 3.1 StepMapper 파일 생성

**파일**: `backend/app/api/step_mapper.py` ✨ 신규 생성

**전체 코드**:
```python
"""
StepMapper: ExecutionStepState → ProcessFlow Step 변환
백엔드 TODO를 프론트엔드 시각화 단계로 매핑
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

    # Agent 이름 → ProcessFlow Step 매핑
    AGENT_TO_STEP = {
        # Planning agents
        "planning_agent": "planning",
        "intent_analyzer": "planning",

        # Search agents (SearchTeam)
        "search_agent": "searching",
        "legal_search": "searching",
        "market_search": "searching",
        "real_estate_search": "searching",
        "loan_search": "searching",
        "regulation_search": "searching",

        # Analysis agents (AnalysisTeam)
        "analysis_agent": "analyzing",
        "market_analysis": "analyzing",
        "risk_analysis": "analyzing",
        "contract_analyzer": "analyzing",
        "verification_agent": "analyzing",

        # Document agents (DocumentTeam) - 분석으로 매핑
        "document_agent": "analyzing",
        "contract_reviewer": "analyzing",
        "document_generator": "generating",

        # Response generation
        "response_generator": "generating",
        "answer_synthesizer": "generating",
        "final_response": "generating"
    }

    # Team 이름 → ProcessFlow Step 매핑 (fallback)
    TEAM_TO_STEP = {
        "search": "searching",
        "search_team": "searching",
        "analysis": "analyzing",
        "analysis_team": "analyzing",
        "document": "analyzing",
        "document_team": "analyzing"
    }

    STEP_LABELS = {
        "planning": "계획",
        "searching": "검색",
        "analyzing": "분석",
        "generating": "생성",
        "processing": "처리 중"  # fallback
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
            ProcessFlow용 단계 리스트 (중복 제거, 순서 정렬)
        """
        flow_steps_map = {}  # step → ProcessFlowStep

        for exec_step in execution_steps:
            agent_name = exec_step.get("agent_name", "")
            team_name = exec_step.get("team", "")

            # 1. Agent 이름으로 매핑
            process_step = cls.AGENT_TO_STEP.get(agent_name)

            # 2. Fallback: Team 이름으로 매핑
            if not process_step:
                process_step = cls.TEAM_TO_STEP.get(team_name)

            # 3. Fallback: "processing"
            if not process_step:
                process_step = "processing"

            # 중복 제거: 같은 step은 하나만 유지 (가장 진행도가 높은 것)
            if process_step in flow_steps_map:
                existing_step = flow_steps_map[process_step]
                # 현재 step이 더 진행되었으면 업데이트
                if cls._is_more_advanced(
                    exec_step.get("status", "pending"),
                    existing_step.status
                ):
                    flow_steps_map[process_step] = cls._create_flow_step(
                        process_step, agent_name, exec_step
                    )
            else:
                flow_steps_map[process_step] = cls._create_flow_step(
                    process_step, agent_name, exec_step
                )

        # 단계 순서 정렬
        step_order = ["planning", "searching", "analyzing", "generating", "processing"]
        sorted_steps = []
        for step_name in step_order:
            if step_name in flow_steps_map:
                sorted_steps.append(flow_steps_map[step_name])

        return sorted_steps

    @classmethod
    def _create_flow_step(
        cls,
        process_step: str,
        agent_name: str,
        exec_step: Dict[str, Any]
    ) -> ProcessFlowStep:
        """ProcessFlowStep 생성"""
        return ProcessFlowStep(
            step=process_step,
            label=cls.STEP_LABELS.get(process_step, process_step),
            agent=agent_name,
            status=exec_step.get("status", "pending"),
            progress=exec_step.get("progress_percentage", 0)
        )

    @staticmethod
    def _is_more_advanced(status1: str, status2: str) -> bool:
        """status1이 status2보다 더 진행된 상태인지 확인"""
        priority = {
            "pending": 0,
            "in_progress": 1,
            "completed": 2,
            "failed": 2  # failed도 진행된 것으로 간주
        }
        return priority.get(status1, 0) > priority.get(status2, 0)

    @classmethod
    def get_current_step(
        cls,
        execution_steps: List[Dict[str, Any]]
    ) -> str:
        """
        현재 실행 중인 단계 반환

        Returns:
            "planning", "searching", "analyzing", "generating" 중 하나
        """
        flow_steps = cls.map_execution_steps(execution_steps)

        # in_progress 상태인 step 찾기
        for step in flow_steps:
            if step.status == "in_progress":
                return step.step

        # in_progress가 없으면 마지막 completed step 반환
        for step in reversed(flow_steps):
            if step.status == "completed":
                return step.step

        # 아무것도 없으면 첫 번째 step
        return flow_steps[0].step if flow_steps else "planning"
```

---

### Phase 4: API Extension

#### 목표
ChatResponse에 process_flow 필드 추가하여 프론트엔드에 전달

#### 4.1 ProcessFlowStep Pydantic Model 추가

**파일**: `backend/app/api/schemas.py`

**위치**: Line 62 (ChatResponse 정의 바로 위)

**추가 코드**:
```python
class ProcessFlowStep(BaseModel):
    """
    프론트엔드 ProcessFlow용 단계
    StepMapper에서 생성됨
    """
    step: str  # "planning", "searching", "analyzing", "generating"
    label: str  # "계획", "검색", "분석", "생성"
    agent: str  # 담당 agent 이름
    status: str  # "pending", "in_progress", "completed", "failed"
    progress: int  # 0-100
```

#### 4.2 ChatResponse에 process_flow 필드 추가

**파일**: `backend/app/api/schemas.py`

**위치**: Line 100 (error 필드 바로 위)

**변경 전**:
```python
class ChatResponse(BaseModel):
    # 기본
    session_id: str
    request_id: str
    status: str

    # 최종 응답
    response: Dict[str, Any]

    # 상세 정보
    planning_info: Optional[Dict[str, Any]] = None
    team_results: Optional[Dict[str, Any]] = None
    search_results: Optional[List[Dict]] = None
    analysis_metrics: Optional[Dict[str, Any]] = None

    # 메타데이터
    execution_time_ms: Optional[int] = None
    teams_executed: List[str] = []
    execution_phases: List[str] = []

    # Checkpoint
    checkpoint_id: Optional[str] = None

    # 에러
    error: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None
```

**변경 후**:
```python
class ChatResponse(BaseModel):
    # 기본
    session_id: str
    request_id: str
    status: str

    # 최종 응답
    response: Dict[str, Any]

    # 상세 정보
    planning_info: Optional[Dict[str, Any]] = None
    team_results: Optional[Dict[str, Any]] = None
    search_results: Optional[List[Dict]] = None
    analysis_metrics: Optional[Dict[str, Any]] = None

    # ProcessFlow (NEW)
    process_flow: Optional[List[ProcessFlowStep]] = None

    # 메타데이터
    execution_time_ms: Optional[int] = None
    teams_executed: List[str] = []
    execution_phases: List[str] = []

    # Checkpoint
    checkpoint_id: Optional[str] = None

    # 에러
    error: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None
```

#### 4.3 converters.py에서 StepMapper 사용

**파일**: `backend/app/api/converters.py`

**위치**: Line 1 (import 추가), Line 108 (ChatResponse 생성 부분)

**변경 전**:
```python
from app.service_agent.foundation.separated_states import MainSupervisorState
from app.api.schemas import ChatResponse
```

**변경 후**:
```python
from app.service_agent.foundation.separated_states import MainSupervisorState
from app.api.schemas import ChatResponse
from app.api.step_mapper import StepMapper  # NEW
```

**변경 전** (Line 108):
```python
# ChatResponse 생성
response = ChatResponse(
    # 기본
    session_id=session_id,
    request_id=request_id,
    status=status,

    # 최종 응답
    response=final_response,

    # 상세 정보
    planning_info=planning_info,
    team_results=team_results,
    search_results=search_results,
    analysis_metrics=analysis_metrics,

    # 메타데이터
    execution_time_ms=execution_time_ms,
    teams_executed=state.get("completed_teams", []),
    execution_phases=execution_phases,

    # Checkpoint
    checkpoint_id=None,

    # 에러
    error=error,
    error_details=error_details
)
```

**변경 후**:
```python
# ProcessFlow 데이터 생성 (NEW)
process_flow_data = None
if planning_state and planning_state.get("execution_steps"):
    flow_steps = StepMapper.map_execution_steps(
        planning_state.get("execution_steps", [])
    )
    # dataclass → dict 변환
    process_flow_data = [
        {
            "step": step.step,
            "label": step.label,
            "agent": step.agent,
            "status": step.status,
            "progress": step.progress
        }
        for step in flow_steps
    ]

# ChatResponse 생성
response = ChatResponse(
    # 기본
    session_id=session_id,
    request_id=request_id,
    status=status,

    # 최종 응답
    response=final_response,

    # 상세 정보
    planning_info=planning_info,
    team_results=team_results,
    search_results=search_results,
    analysis_metrics=analysis_metrics,

    # ProcessFlow (NEW)
    process_flow=process_flow_data,

    # 메타데이터
    execution_time_ms=execution_time_ms,
    teams_executed=state.get("completed_teams", []),
    execution_phases=execution_phases,

    # Checkpoint
    checkpoint_id=None,

    # 에러
    error=error,
    error_details=error_details
)
```

---

### Phase 5: Frontend Dynamic Rendering

#### 목표
API response의 process_flow를 사용하여 동적으로 ProcessFlow 렌더링

#### 5.1 ChatResponse 타입 수정

**파일**: `frontend/types/chat.ts`

**위치**: ChatResponse interface

**변경 전**:
```typescript
export interface ChatResponse {
  session_id: string
  request_id: string
  status: string
  response: {
    type: string
    content: string
    data: Record<string, any>
  }
  planning_info?: {
    execution_steps?: Array<Record<string, any>>
    execution_strategy?: string
    estimated_total_time?: number
    plan_validated?: boolean
    intent?: string
    confidence?: number
  }
  team_results?: Record<string, any>
  search_results?: Array<Record<string, any>>
  analysis_metrics?: Record<string, any>
  execution_time_ms?: number
  teams_executed?: string[]
  error?: string
}
```

**변경 후**:
```typescript
export interface ProcessFlowStep {
  step: string  // "planning" | "searching" | "analyzing" | "generating"
  label: string  // "계획" | "검색" | "분석" | "생성"
  agent: string
  status: string  // "pending" | "in_progress" | "completed" | "failed"
  progress: number  // 0-100
}

export interface ChatResponse {
  session_id: string
  request_id: string
  status: string
  response: {
    type: string
    content: string
    data: Record<string, any>
  }
  planning_info?: {
    execution_steps?: Array<Record<string, any>>
    execution_strategy?: string
    estimated_total_time?: number
    plan_validated?: boolean
    intent?: string
    confidence?: number
  }
  process_flow?: ProcessFlowStep[]  // NEW
  team_results?: Record<string, any>
  search_results?: Array<Record<string, any>>
  analysis_metrics?: Record<string, any>
  execution_time_ms?: number
  teams_executed?: string[]
  error?: string
}
```

#### 5.2 process-flow.tsx 수정 (동적 steps)

**파일**: `frontend/components/process-flow.tsx`

**변경 전**:
```typescript
interface ProcessFlowProps {
  isVisible: boolean
  state: ProcessState
}

export function ProcessFlow({ isVisible, state }: ProcessFlowProps) {
  // Hardcoded steps
  return (
    <div className="flex items-center gap-1">
      <StepIndicator label="계획" ... />
      <StepConnector ... />
      <StepIndicator label="검색" ... />
      <StepConnector ... />
      <StepIndicator label="분석" ... />
      <StepConnector ... />
      <StepIndicator label="생성" ... />
    </div>
  )
}
```

**변경 후**:
```typescript
import type { ProcessFlowStep } from "@/types/chat"

interface ProcessFlowProps {
  isVisible: boolean
  state: ProcessState
  steps?: ProcessFlowStep[]  // NEW: API에서 받은 동적 steps
}

// Default steps (API response 없을 때 fallback)
const DEFAULT_STEPS: ProcessFlowStep[] = [
  { step: "planning", label: "계획", agent: "planning_agent", status: "pending", progress: 0 },
  { step: "searching", label: "검색", agent: "search_agent", status: "pending", progress: 0 },
  { step: "analyzing", label: "분석", agent: "analysis_agent", status: "pending", progress: 0 },
  { step: "generating", label: "생성", agent: "response_generator", status: "pending", progress: 0 }
]

export function ProcessFlow({ isVisible, state, steps }: ProcessFlowProps) {
  if (!isVisible) return null

  // Use API steps if available, otherwise use default
  const displaySteps = steps || DEFAULT_STEPS

  // Find current step
  const currentStepName = state.step
  const currentStepIndex = displaySteps.findIndex(s => s.step === currentStepName)

  return (
    <div className="flex justify-start mb-4">
      <div className="flex items-start gap-3 max-w-2xl w-full">
        <div className="rounded-full p-2 bg-muted text-muted-foreground flex-shrink-0">
          <Bot className="h-4 w-4" />
        </div>

        <Card className="p-3 bg-card border flex-1">
          {/* Header */}
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Loader2 className="w-5 h-5 text-primary animate-spin" />
              <div>
                <p className="text-sm font-medium">
                  {displaySteps[currentStepIndex]?.agent || "처리 중"}
                </p>
                <p className="text-xs text-muted-foreground">{state.message}</p>
              </div>
            </div>
            <div className="text-xs text-muted-foreground font-mono">
              {/* Elapsed time */}
            </div>
          </div>

          {/* Dynamic step indicators */}
          <div className="flex items-center gap-1">
            {displaySteps.map((step, index) => (
              <React.Fragment key={step.step}>
                <StepIndicator
                  label={step.label}
                  isComplete={step.status === "completed"}
                  isCurrent={step.status === "in_progress" || step.step === currentStepName}
                  isFailed={step.status === "failed"}
                />
                {index < displaySteps.length - 1 && (
                  <StepConnector
                    isComplete={step.status === "completed"}
                  />
                )}
              </React.Fragment>
            ))}
          </div>
        </Card>
      </div>
    </div>
  )
}
```

#### 5.3 chat-interface.tsx 수정 (API response 사용)

**파일**: `frontend/components/chat-interface.tsx`

**변경 전** (Lines 87-119):
```typescript
// 프로세스 시작
setProcessState({
  step: "planning",
  agentType,
  message: STEP_MESSAGES.planning,
  startTime: Date.now()
})

// ❌ Hardcoded setTimeout
setTimeout(() => {
  setProcessState(prev => ({
    ...prev,
    step: "searching",
    message: STEP_MESSAGES.searching
  }))
}, 800)

setTimeout(() => {
  setProcessState(prev => ({
    ...prev,
    step: "analyzing",
    message: STEP_MESSAGES.analyzing
  }))
}, 1600)

setTimeout(() => {
  setProcessState(prev => ({
    ...prev,
    step: "generating",
    message: STEP_MESSAGES.generating
  }))
}, 2400)
```

**변경 후**:
```typescript
// State 추가: API에서 받은 process_flow
const [currentProcessFlow, setCurrentProcessFlow] = useState<ProcessFlowStep[] | undefined>(undefined)

// ...

// 프로세스 시작
setProcessState({
  step: "planning",
  agentType,
  message: STEP_MESSAGES.planning,
  startTime: Date.now()
})

// ✅ API 호출 (setTimeout 제거)
try {
  const response = await chatAPI.sendMessage({
    query: content,
    session_id: sessionId,
  })

  // ✅ process_flow 저장
  setCurrentProcessFlow(response.process_flow)

  // ✅ process_flow가 있으면 current step 계산
  if (response.process_flow && response.process_flow.length > 0) {
    const currentStep = response.process_flow.find(s => s.status === "in_progress")
    if (currentStep) {
      setProcessState(prev => ({
        ...prev,
        step: currentStep.step as ProcessStep,
        message: STEP_MESSAGES[currentStep.step as ProcessStep] || "처리 중..."
      }))
    }
  }

  // ProcessFlow 제거
  setMessages(prev => prev.filter(m => m.id !== "process-flow-temp"))

  // Bot 메시지 추가
  const botMessage: Message = {
    id: Date.now().toString() + "-bot",
    type: "bot",
    content: response.response.content,
    timestamp: new Date(),
  }
  setMessages(prev => [...prev, botMessage])

  // Reset process state
  setProcessState({
    step: "idle",
    agentType: null,
    message: ""
  })
  setCurrentProcessFlow(undefined)

} catch (error) {
  // Error handling
}
```

**렌더링 부분 수정**:
```typescript
{messages.map((message) => (
  <div key={message.id}>
    {message.type === "process-flow" ? (
      <ProcessFlow
        isVisible={processState.step !== "idle"}
        state={processState}
        steps={currentProcessFlow}  // ✅ API에서 받은 steps 전달
      />
    ) : (
      // Regular message rendering
    )}
  </div>
))}
```

---

## Part 3: 실시간 스트리밍 (Phase 6) 🔮

### 왜 이 단계가 필요한가?

**현재 (Part 2 완료 후)**:
- 쿼리 완료 후 → API response에 process_flow 포함 → Frontend 한 번에 표시
- 문제: 실행 중에는 진행 상황을 볼 수 없음

**SSE 적용 후**:
- 팀 실행 시작 → SSE 이벤트 발행 → Frontend 실시간 업데이트
- 장점: 사용자가 "지금 무슨 단계인지" 실시간으로 확인 가능

**의존성**: Part 2 완료 필수

**중요**: 이 단계는 **Optional**입니다. Part 1-2만 완료해도 ProcessFlow 연동은 작동합니다.

---

### Phase 6 (Optional): SSE Real-time Streaming

#### 목표
실시간 진행 상황 업데이트 (현재는 완료 후 한 번에 전달)

**참고**: Phase 1-5 완료 후 필요 시 구현

#### 6.1 EventBroker 구현

**파일**: `backend/app/api/event_broker.py` ✨ 신규

```python
"""
EventBroker: SSE (Server-Sent Events) 브로커
LangGraph 노드에서 실시간 이벤트 전송
"""

import asyncio
import logging
from typing import Dict, List, Any
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class ProcessEvent:
    """프로세스 이벤트"""
    event_type: str  # "step_start", "step_progress", "step_complete", "step_failed"
    session_id: str
    step_id: str
    agent_name: str
    team: str
    status: str
    progress: int
    message: str
    timestamp: float


class EventBroker:
    """SSE 이벤트 브로커 (Pub/Sub)"""

    def __init__(self):
        self.listeners: Dict[str, List[asyncio.Queue]] = {}

    def subscribe(self, session_id: str) -> asyncio.Queue:
        """세션 구독"""
        queue = asyncio.Queue()
        if session_id not in self.listeners:
            self.listeners[session_id] = []
        self.listeners[session_id].append(queue)
        logger.debug(f"Subscribed to session {session_id}")
        return queue

    def unsubscribe(self, session_id: str, queue: asyncio.Queue):
        """세션 구독 해제"""
        if session_id in self.listeners:
            self.listeners[session_id].remove(queue)
            if not self.listeners[session_id]:
                del self.listeners[session_id]
        logger.debug(f"Unsubscribed from session {session_id}")

    async def publish(self, event: ProcessEvent):
        """이벤트 발행"""
        session_id = event.session_id
        if session_id not in self.listeners:
            return

        event_data = asdict(event)

        for queue in self.listeners[session_id]:
            try:
                await queue.put(event_data)
            except Exception as e:
                logger.error(f"Failed to publish event: {e}")


# Global singleton
_event_broker = EventBroker()

def get_event_broker() -> EventBroker:
    """EventBroker 싱글톤 반환"""
    return _event_broker
```

#### 6.2 SSE 엔드포인트 추가

**파일**: `backend/app/api/chat_api.py`

**위치**: Line 225 이후 추가

```python
from fastapi.responses import StreamingResponse
from app.api.event_broker import get_event_broker, EventBroker
import json

@router.get("/stream/{session_id}")
async def stream_process_flow(
    session_id: str,
    broker: EventBroker = Depends(get_event_broker)
):
    """
    SSE 엔드포인트: 실시간 ProcessFlow 업데이트

    Args:
        session_id: 세션 ID

    Returns:
        SSE stream
    """
    queue = broker.subscribe(session_id)

    async def event_generator():
        try:
            while True:
                event = await queue.get()
                yield f"data: {json.dumps(event)}\n\n"
        except asyncio.CancelledError:
            broker.unsubscribe(session_id, queue)
            raise

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive"
        }
    )
```

#### 6.3 team_supervisor.py에서 이벤트 emit

**파일**: `backend/app/service_agent/supervisor/team_supervisor.py`

**수정 위치**: `_update_step_status` 메서드

```python
def _update_step_status(
    self,
    state: MainSupervisorState,
    team_name: str,
    status: str,
    error_message: Optional[str] = None
) -> None:
    """Status 업데이트 + SSE 이벤트 emit"""
    planning_state = state.get("planning_state")
    if not planning_state:
        return

    import time
    from app.api.event_broker import get_event_broker, ProcessEvent

    current_time = time.time()
    broker = get_event_broker()

    for step in planning_state.get("execution_steps", []):
        if step.get("team") == team_name:
            step["status"] = status

            if status == "in_progress":
                step["start_time"] = current_time
                step["progress_percentage"] = 50
                event_type = "step_start"
            elif status == "completed":
                step["end_time"] = current_time
                step["progress_percentage"] = 100
                event_type = "step_complete"
            elif status == "failed":
                step["end_time"] = current_time
                step["progress_percentage"] = 0
                step["error_message"] = error_message
                event_type = "step_failed"

            # SSE 이벤트 발행
            asyncio.create_task(broker.publish(ProcessEvent(
                event_type=event_type,
                session_id=state["session_id"],
                step_id=step["step_id"],
                agent_name=step["agent_name"],
                team=team_name,
                status=status,
                progress=step["progress_percentage"],
                message=f"{team_name} {status}",
                timestamp=current_time
            )))
```

#### 6.4 Frontend SSE 구독

**파일**: `frontend/components/chat-interface.tsx`

```typescript
useEffect(() => {
  if (!sessionId || processState.step === "idle") return

  // SSE connection
  const eventSource = new EventSource(`/api/v1/chat/stream/${sessionId}`)

  eventSource.onmessage = (event) => {
    const data = JSON.parse(event.data)

    // Update ProcessFlow state
    if (data.event_type === "step_start") {
      setProcessState(prev => ({
        ...prev,
        step: data.team,  // or map team to step
        message: data.message
      }))
    }

    // Update process_flow steps
    setCurrentProcessFlow(prev => {
      if (!prev) return prev
      return prev.map(step => {
        if (step.agent === data.agent_name) {
          return {
            ...step,
            status: data.status,
            progress: data.progress
          }
        }
        return step
      })
    })
  }

  return () => {
    eventSource.close()
  }
}, [sessionId, processState.step])
```

---

## 🧪 테스트 계획

### Phase 1-2 테스트
```python
# test_status_tracking.py
import asyncio
from app.service_agent.supervisor.team_supervisor import TeamBasedSupervisor
from app.service_agent.foundation.context import create_default_llm_context

async def test_status_tracking():
    supervisor = TeamBasedSupervisor(
        llm_context=create_default_llm_context(),
        enable_checkpointing=False
    )

    result = await supervisor.process_query(
        query="강남구 아파트 시세 알려줘",
        session_id="test-session-123"
    )

    # execution_steps에 status가 있는지 확인
    planning_state = result.get("planning_state")
    if planning_state:
        for step in planning_state.get("execution_steps", []):
            print(f"Step: {step['agent_name']}, Status: {step['status']}, Progress: {step['progress_percentage']}%")
            assert "status" in step
            assert step["status"] in ["pending", "in_progress", "completed", "failed"]

asyncio.run(test_status_tracking())
```

### Phase 3-4 테스트
```python
# test_step_mapper.py
from app.api.step_mapper import StepMapper

def test_step_mapper():
    execution_steps = [
        {
            "step_id": "step_0",
            "agent_name": "search_agent",
            "team": "search",
            "status": "completed",
            "progress_percentage": 100
        },
        {
            "step_id": "step_1",
            "agent_name": "analysis_agent",
            "team": "analysis",
            "status": "in_progress",
            "progress_percentage": 50
        }
    ]

    flow_steps = StepMapper.map_execution_steps(execution_steps)

    print(flow_steps)
    # [
    #   ProcessFlowStep(step='searching', label='검색', status='completed', progress=100),
    #   ProcessFlowStep(step='analyzing', label='분석', status='in_progress', progress=50)
    # ]

test_step_mapper()
```

### Phase 5 테스트
```bash
# Frontend: API response 확인
# 1. npm run dev
# 2. 질문 입력
# 3. Network tab에서 /api/v1/chat/ response 확인
# 4. process_flow 필드 있는지 확인
```

---

## 📋 체크리스트

### ⭐ Part 1: TODO 상태 추적 (최우선 필수)

**Phase 1: ExecutionStepState 표준화**
- [ ] `separated_states.py`에 `ExecutionStepState` 추가
- [ ] `PlanningState.execution_steps` 타입 변경
- [ ] `team_supervisor.py:planning_node`에서 status="pending" 초기화
- [ ] 테스트: execution_steps에 status 필드 있는지 확인

**Phase 2: Status 추적 로직**
- [ ] `team_supervisor.py`에 `_update_step_status` 메서드 추가
- [ ] `execute_teams_node`에서 status 업데이트 호출
- [ ] 테스트: 실제 쿼리 실행하여 status 변화 확인

**Part 1 완료 조건**: execution_steps에 status가 실시간으로 업데이트됨

---

### 📡 Part 2: ProcessFlow 연동 (Part 1 완료 후)

**Phase 3: StepMapper 구현**
- [ ] `backend/app/api/step_mapper.py` 생성
- [ ] `ProcessFlowStep` dataclass 정의
- [ ] `StepMapper.map_execution_steps()` 구현
- [ ] 테스트: StepMapper 단위 테스트

**Phase 4: API Extension**
- [ ] `schemas.py`에 `ProcessFlowStep` Pydantic model 추가
- [ ] `ChatResponse.process_flow` 필드 추가
- [ ] `converters.py`에서 StepMapper import 및 사용
- [ ] 테스트: API response에 process_flow 있는지 확인

**Phase 5: Frontend Dynamic Rendering**
- [ ] `frontend/types/chat.ts`에 `ProcessFlowStep` interface 추가
- [ ] `ChatResponse.process_flow` 타입 추가
- [ ] `process-flow.tsx`에 `steps` prop 추가
- [ ] `chat-interface.tsx`에서 API response 사용 (setTimeout 제거)
- [ ] 테스트: 실제 브라우저에서 동적 steps 렌더링 확인

**Part 2 완료 조건**: Frontend ProcessFlow가 API response 기반으로 동적 렌더링됨

---

### 🔮 Part 3: 실시간 스트리밍 (Optional - Part 2 완료 후)

**Phase 6 (Optional): SSE**
- [ ] `backend/app/api/event_broker.py` 생성
- [ ] SSE 엔드포인트 추가 (`/api/v1/chat/stream/{session_id}`)
- [ ] `team_supervisor.py`에서 이벤트 emit
- [ ] Frontend에서 EventSource 구독
- [ ] 테스트: 실시간 업데이트 확인

**Part 3 완료 조건**: 실시간 진행 상황 스트리밍 (현재는 완료 후 한 번에 표시)

---

## 🚀 예상 결과

### Phase 1-2 완료 후
```json
{
  "planning_state": {
    "execution_steps": [
      {
        "step_id": "step_0",
        "agent_name": "search_agent",
        "team": "search",
        "status": "completed",  // ✅ 추가됨
        "progress_percentage": 100,  // ✅ 추가됨
        "start_time": 1696800000.0,  // ✅ 추가됨
        "end_time": 1696800005.0  // ✅ 추가됨
      }
    ]
  }
}
```

### Phase 3-4 완료 후
```json
{
  "process_flow": [  // ✅ 새 필드
    {
      "step": "searching",
      "label": "검색",
      "agent": "search_agent",
      "status": "completed",
      "progress": 100
    },
    {
      "step": "analyzing",
      "label": "분석",
      "agent": "analysis_agent",
      "status": "in_progress",
      "progress": 50
    }
  ]
}
```

### Phase 5 완료 후
```typescript
// Frontend: 동적 렌더링
<ProcessFlow
  isVisible={true}
  state={processState}
  steps={[
    { step: "searching", label: "검색", status: "completed", ... },
    { step: "analyzing", label: "분석", status: "in_progress", ... }
  ]}
/>

// 결과: ✓ 검색 ─── ● 분석 ─── ○ 생성
```

---

## 🔄 구현 순서 요약

### 올바른 순서 (데이터 → 연동 → UI)

```
1️⃣ Part 1: TODO 상태 추적 ⭐ 시작
   │
   ├─ Phase 1: ExecutionStepState에 status 필드 추가
   │  → execution_steps = [{ status: "pending", progress: 0, ... }]
   │
   └─ Phase 2: execute_teams_node에서 status 업데이트
      → 팀 실행 시 status: pending → in_progress → completed

   ✅ Part 1 완료: execution_steps가 실시간 상태 추적

2️⃣ Part 2: ProcessFlow 연동 (Part 1 완료 후)
   │
   ├─ Phase 3: StepMapper 구현
   │  → execution_steps → ProcessFlowStep 변환
   │
   ├─ Phase 4: API Extension
   │  → ChatResponse.process_flow 필드 추가
   │
   └─ Phase 5: Frontend Dynamic Rendering
      → ProcessFlow가 API response 표시

   ✅ Part 2 완료: ProcessFlow가 백엔드 데이터 기반으로 작동

3️⃣ Part 3: 실시간 스트리밍 (Optional)
   └─ Phase 6: SSE 구현
      → 실시간 진행 상황 업데이트

   ✅ Part 3 완료: 실시간 ProcessFlow 업데이트
```

### 잘못된 순서 (하면 안 됨)

```
❌ ProcessFlow 먼저 구현
   → execution_steps에 status 없음
   → ProcessFlow가 표시할 데이터 없음
   → hardcoded setTimeout으로 fake progress 만들 수밖에 없음
```

---

## 📚 참고

### 관련 문서
- [TODO_PROCESSFLOW_CODE_REVIEW.md](backend/app/service_agent/reports/TODO_PROCESSFLOW_CODE_REVIEW.md) - 코드 리뷰 결과 (이미 구현된 것 vs 미구현)
- [TODO_PROCESSFLOW_INTEGRATION_PLAN.md](backend/app/service_agent/reports/TODO_PROCESSFLOW_INTEGRATION_PLAN.md) - 원본 계획서

### 핵심 파일 위치
**백엔드**:
- [separated_states.py:236](backend/app/service_agent/foundation/separated_states.py#L236) - PlanningState 정의
- [team_supervisor.py:174](backend/app/service_agent/supervisor/team_supervisor.py#L174) - execution_steps 생성
- [team_supervisor.py:238](backend/app/service_agent/supervisor/team_supervisor.py#L238) - execute_teams_node
- [converters.py:48](backend/app/api/converters.py#L48) - state → ChatResponse 변환
- [schemas.py:63](backend/app/api/schemas.py#L63) - ChatResponse 정의

**프론트엔드**:
- [chat-interface.tsx:87](frontend/components/chat-interface.tsx#L87) - ProcessFlow 호출 (hardcoded setTimeout)
- [process-flow.tsx](frontend/components/process-flow.tsx) - ProcessFlow 컴포넌트
- [types/process.ts](frontend/types/process.ts) - ProcessStep 타입 정의
