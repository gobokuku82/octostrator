# TODO 관리 시스템 구현 계획서 (수정판)
**기존 State 구조 활용 + 최소 확장 전략**

---

## 📋 요구사항

1. **LLM 기반 계획 수립**: 질문 입력 → LLM이 작업 계획(TODO 리스트) 생성
2. **사용자 개입**: 중간에 언제든 TODO 수정 가능
3. **진행 상황 모니터링**: 실시간 작업 내역 확인
4. **과거 이력 복원**: Checkpoint를 통한 롤백

---

## 🔍 기존 구현 분석 결과

### ✅ 이미 존재하는 것들

#### 1. **TODO 리스트 구조** - `PlanningState.execution_steps`
```python
class PlanningState(TypedDict):
    execution_steps: List[Dict[str, Any]]  # 👈 이것이 TODO 리스트!
    execution_strategy: str                # 실행 전략 (sequential/parallel)
    parallel_groups: Optional[List[List[str]]]
```

**실제 생성 위치**: `planning_agent.py`
```python
@dataclass
class ExecutionStep:
    agent_name: str          # 담당 에이전트
    priority: int            # 우선순위
    dependencies: List[str]  # 의존성
    timeout: int
    retry_count: int
    optional: bool           # 선택적 작업
    input_mapping: Dict[str, str]
```

#### 2. **진행 상태 추적** - 각 TeamState
```python
SearchTeamState:
    search_progress: Dict[str, str]      # 검색 진행 상황
    current_search: Optional[str]        # 현재 검색

MainSupervisorState:
    current_phase: str                   # 현재 단계
    active_teams: List[str]              # 실행 중인 팀
    completed_teams: List[str]           # 완료된 팀
    failed_teams: List[str]              # 실패한 팀
```

#### 3. **Checkpoint 시스템** - 과거 복원 가능
- **AsyncSqliteSaver**: 각 노드 실행 후 자동 저장
- **Thread 기반 이력**: session_id로 과거 상태 추적
- **검증 완료**: 112 checkpoints, 1936 writes 저장 확인

#### 4. **Decision Logging** - LLM 결정 기록
- 도구 선택 로깅
- 실행 결과 업데이트
- 통계 조회

### ❌ 부족한 것들

1. **개별 TODO 상태 추적 표준화**
   - `execution_steps`는 리스트일 뿐, 각 항목의 실시간 상태(pending/in_progress/completed) 없음

2. **사용자 수정 메커니즘**
   - TODO 수정 인터페이스 없음
   - 수정 이력 저장 없음

3. **승인/대기 플로우**
   - 계획 생성 후 사용자 확인/승인 단계 없음

4. **표준화된 진행률**
   - `progress`가 Dict[str, str]로 자유 형식
   - 전체 진행률(%) 계산 없음

---

## 🎯 구현 전략: **기존 구조 확장 (최소 침습)**

### 원칙
1. **기존 State 구조 최대한 유지**
2. **PlanningState와 execution_steps 중심 확장**
3. **새 파일은 최소화, 기존 파일 확장 우선**

---

## 📐 Phase 1: State 확장 (표준화)

### 파일: `foundation/separated_states.py`

#### 1-1. ExecutionStepState 표준 정의

**현재 문제**: `execution_steps: List[Dict[str, Any]]` - 형식이 자유로움

**해결책**: TypedDict로 표준화

```python
class ExecutionStepState(TypedDict):
    """execution_steps의 표준 형식 - TODO 아이템"""

    # 기본 정보
    step_id: str                    # 고유 ID (예: "step_0", "step_1")
    agent_name: str                 # 담당 에이전트/팀
    description: str                # 작업 설명 (사용자에게 표시)
    priority: int                   # 우선순위
    dependencies: List[str]         # 선행 작업 ID들

    # 실행 설정
    timeout: int
    retry_count: int
    optional: bool
    input_mapping: Dict[str, str]

    # ✨ 새로 추가: 상태 추적
    status: Literal["pending", "in_progress", "completed", "failed", "skipped", "cancelled"]
    progress_percentage: int        # 0-100

    # ✨ 새로 추가: 시간 추적
    started_at: Optional[str]       # ISO format datetime
    completed_at: Optional[str]
    execution_time_ms: Optional[int]

    # ✨ 새로 추가: 결과
    result: Optional[Dict[str, Any]]
    error: Optional[str]
    error_details: Optional[str]

    # ✨ 새로 추가: 사용자 수정
    modified_by_user: bool
    original_values: Optional[Dict[str, Any]]  # 수정 전 원본
```

#### 1-2. PlanningState 확장

```python
class PlanningState(TypedDict):
    # 기존 필드들
    raw_query: str
    analyzed_intent: Dict[str, Any]
    intent_confidence: float
    available_agents: List[str]
    available_teams: List[str]
    execution_steps: List[ExecutionStepState]  # ✨ 타입 명시
    execution_strategy: str
    parallel_groups: Optional[List[List[str]]]
    plan_validated: bool
    validation_errors: List[str]
    estimated_total_time: float

    # ✨ 새로 추가: 사용자 개입
    awaiting_user_approval: bool
    user_approved: bool
    user_modifications: List[Dict[str, Any]]  # 수정 이력

    # ✨ 새로 추가: 전체 진행률
    overall_progress_percentage: int  # 0-100
    completed_step_count: int
    failed_step_count: int
    total_step_count: int
```

#### 1-3. UserModification 타입 정의

```python
class UserModification(TypedDict):
    """사용자의 TODO 수정 기록"""
    modification_id: str
    timestamp: str                  # ISO format
    step_id: str                    # 수정된 step
    modification_type: Literal["add", "remove", "modify", "reorder"]
    field_changed: Optional[str]    # 수정된 필드명
    old_value: Optional[Any]
    new_value: Optional[Any]
    reason: Optional[str]           # 수정 이유 (사용자 입력)
```

---

## 📐 Phase 2: StateTransition 확장 (기존 클래스 활용)

### 파일: `foundation/separated_states.py` (기존 파일)

`StateTransition` 클래스에 메서드 추가:

```python
class StateTransition:
    """State 전환 관리 (기존 클래스 확장)"""

    # === 기존 메서드들 ===
    # - update_status()
    # - record_error()
    # - mark_completed()

    # === ✨ 새로 추가: ExecutionStep 관리 ===

    @staticmethod
    def update_step_status(
        planning_state: PlanningState,
        step_id: str,
        new_status: Literal["pending", "in_progress", "completed", "failed", "skipped", "cancelled"],
        progress: Optional[int] = None,
        error: Optional[str] = None
    ) -> PlanningState:
        """
        개별 execution_step의 상태 업데이트

        Args:
            planning_state: Planning State
            step_id: 업데이트할 step ID
            new_status: 새로운 상태
            progress: 진행률 (0-100)
            error: 에러 메시지 (실패 시)
        """
        for step in planning_state["execution_steps"]:
            if step["step_id"] == step_id:
                old_status = step["status"]
                step["status"] = new_status

                if progress is not None:
                    step["progress_percentage"] = progress

                if new_status == "in_progress" and not step.get("started_at"):
                    step["started_at"] = datetime.now().isoformat()

                if new_status in ["completed", "failed", "skipped"]:
                    step["completed_at"] = datetime.now().isoformat()
                    if step.get("started_at"):
                        start = datetime.fromisoformat(step["started_at"])
                        delta = datetime.now() - start
                        step["execution_time_ms"] = int(delta.total_seconds() * 1000)

                if error:
                    step["error"] = error

                logger.info(f"Step {step_id} status: {old_status} -> {new_status}")
                break

        # 전체 진행률 재계산
        planning_state = StateTransition._recalculate_overall_progress(planning_state)

        return planning_state

    @staticmethod
    def modify_step_by_user(
        planning_state: PlanningState,
        step_id: str,
        modifications: Dict[str, Any],
        reason: Optional[str] = None
    ) -> PlanningState:
        """
        사용자에 의한 step 수정

        Args:
            planning_state: Planning State
            step_id: 수정할 step ID
            modifications: 수정할 필드들 {"field": new_value}
            reason: 수정 이유
        """
        for step in planning_state["execution_steps"]:
            if step["step_id"] == step_id:
                # 원본 값 저장 (최초 수정 시)
                if not step.get("modified_by_user"):
                    step["original_values"] = {
                        k: step[k] for k in modifications.keys() if k in step
                    }

                # 수정 적용
                for field, new_value in modifications.items():
                    old_value = step.get(field)
                    step[field] = new_value

                    # 수정 이력 기록
                    modification = UserModification(
                        modification_id=f"mod_{datetime.now().timestamp()}",
                        timestamp=datetime.now().isoformat(),
                        step_id=step_id,
                        modification_type="modify",
                        field_changed=field,
                        old_value=old_value,
                        new_value=new_value,
                        reason=reason
                    )
                    planning_state["user_modifications"].append(modification)

                step["modified_by_user"] = True
                logger.info(f"Step {step_id} modified by user: {list(modifications.keys())}")
                break

        return planning_state

    @staticmethod
    def add_step_by_user(
        planning_state: PlanningState,
        step_data: ExecutionStepState,
        reason: Optional[str] = None
    ) -> PlanningState:
        """사용자가 새 TODO 추가"""
        planning_state["execution_steps"].append(step_data)
        planning_state["total_step_count"] += 1

        # 수정 이력
        modification = UserModification(
            modification_id=f"mod_{datetime.now().timestamp()}",
            timestamp=datetime.now().isoformat(),
            step_id=step_data["step_id"],
            modification_type="add",
            field_changed=None,
            old_value=None,
            new_value=step_data,
            reason=reason
        )
        planning_state["user_modifications"].append(modification)

        logger.info(f"New step added by user: {step_data['step_id']}")
        return planning_state

    @staticmethod
    def remove_step_by_user(
        planning_state: PlanningState,
        step_id: str,
        reason: Optional[str] = None
    ) -> PlanningState:
        """사용자가 TODO 제거"""
        removed_step = None
        for i, step in enumerate(planning_state["execution_steps"]):
            if step["step_id"] == step_id:
                removed_step = planning_state["execution_steps"].pop(i)
                planning_state["total_step_count"] -= 1
                break

        if removed_step:
            # 수정 이력
            modification = UserModification(
                modification_id=f"mod_{datetime.now().timestamp()}",
                timestamp=datetime.now().isoformat(),
                step_id=step_id,
                modification_type="remove",
                field_changed=None,
                old_value=removed_step,
                new_value=None,
                reason=reason
            )
            planning_state["user_modifications"].append(modification)

            logger.info(f"Step removed by user: {step_id}")

        return planning_state

    @staticmethod
    def approve_plan(planning_state: PlanningState) -> PlanningState:
        """사용자가 계획 승인"""
        planning_state["awaiting_user_approval"] = False
        planning_state["user_approved"] = True
        logger.info("Plan approved by user")
        return planning_state

    @staticmethod
    def _recalculate_overall_progress(planning_state: PlanningState) -> PlanningState:
        """전체 진행률 재계산"""
        steps = planning_state["execution_steps"]
        total = len(steps)

        if total == 0:
            planning_state["overall_progress_percentage"] = 0
            return planning_state

        completed = sum(1 for s in steps if s["status"] == "completed")
        failed = sum(1 for s in steps if s["status"] == "failed")
        in_progress_sum = sum(
            s.get("progress_percentage", 0)
            for s in steps
            if s["status"] == "in_progress"
        )

        # 전체 진행률 = (완료 100% + 진행중 부분% + 실패 0%) / 전체
        overall = ((completed * 100) + in_progress_sum) / total

        planning_state["overall_progress_percentage"] = int(overall)
        planning_state["completed_step_count"] = completed
        planning_state["failed_step_count"] = failed
        planning_state["total_step_count"] = total

        return planning_state
```

---

## 📐 Phase 3: Supervisor 통합

### 파일: `supervisor/team_supervisor.py`

#### 3-1. Planning Node 수정

```python
async def planning_node(self, state: MainSupervisorState) -> MainSupervisorState:
    """계획 수립 노드"""
    logger.info("[TeamSupervisor] Planning phase")

    state["current_phase"] = "planning"

    # 의도 분석 및 실행 계획 생성 (기존 로직)
    query = state.get("query", "")
    intent_result = await self.planning_agent.analyze_intent(query)
    execution_plan = await self.planning_agent.create_execution_plan(intent_result)

    # ✨ NEW: ExecutionStep → ExecutionStepState 변환
    execution_steps = self._convert_to_step_states(execution_plan.steps)

    # Planning State 생성
    planning_state = PlanningState(
        raw_query=query,
        analyzed_intent={
            "intent_type": intent_result.intent_type.value,
            "confidence": intent_result.confidence,
            "keywords": intent_result.keywords,
            "entities": intent_result.entities
        },
        intent_confidence=intent_result.confidence,
        available_agents=AgentRegistry.list_agents(enabled_only=True),
        available_teams=list(self.teams.keys()),
        execution_steps=execution_steps,  # ✨ 표준화된 형식
        execution_strategy=execution_plan.strategy.value,
        parallel_groups=execution_plan.parallel_groups,
        plan_validated=True,
        validation_errors=[],
        estimated_total_time=execution_plan.estimated_time,

        # ✨ NEW: 사용자 개입 관련
        awaiting_user_approval=False,  # TODO: 설정으로 제어 가능하게
        user_approved=False,
        user_modifications=[],

        # ✨ NEW: 진행률
        overall_progress_percentage=0,
        completed_step_count=0,
        failed_step_count=0,
        total_step_count=len(execution_steps)
    )

    state["planning_state"] = planning_state

    # ✨ NEW: 사용자 승인 대기 (옵션)
    if planning_state["awaiting_user_approval"]:
        logger.info("[TeamSupervisor] Awaiting user approval...")
        # 여기서 interrupt 또는 사용자 입력 대기
        # LangGraph의 interrupt() 기능 활용 가능

    return state

def _convert_to_step_states(
    self,
    execution_steps: List[ExecutionStep]
) -> List[ExecutionStepState]:
    """ExecutionStep → ExecutionStepState 변환"""
    step_states = []

    for i, step in enumerate(execution_steps):
        step_state = ExecutionStepState(
            step_id=f"step_{i}",
            agent_name=step.agent_name,
            description=f"{step.agent_name} 실행",  # TODO: 더 나은 설명
            priority=step.priority,
            dependencies=step.dependencies,
            timeout=step.timeout,
            retry_count=step.retry_count,
            optional=step.optional,
            input_mapping=step.input_mapping,

            # 초기 상태
            status="pending",
            progress_percentage=0,
            started_at=None,
            completed_at=None,
            execution_time_ms=None,
            result=None,
            error=None,
            error_details=None,
            modified_by_user=False,
            original_values=None
        )
        step_states.append(step_state)

    return step_states
```

#### 3-2. Execute Teams Node 수정

```python
async def execute_teams_node(self, state: MainSupervisorState) -> MainSupervisorState:
    """팀 실행 노드"""
    logger.info("[TeamSupervisor] Executing teams")

    state["current_phase"] = "executing"

    execution_strategy = state.get("execution_plan", {}).get("strategy", "sequential")
    active_teams = state.get("active_teams", [])
    planning_state = state.get("planning_state")

    # 공유 상태 생성
    shared_state = StateManager.create_shared_state(
        query=state["query"],
        session_id=state["session_id"]
    )

    # ✨ NEW: 각 팀 실행 전/후 step 상태 업데이트
    for team_name in active_teams:
        # Step ID 찾기
        step_id = self._find_step_id_for_team(team_name, planning_state)

        if step_id:
            # ✨ 시작 전: 상태 업데이트
            planning_state = StateTransition.update_step_status(
                planning_state,
                step_id,
                "in_progress",
                progress=0
            )
            state["planning_state"] = planning_state

        # 팀 실행 (기존 로직)
        try:
            result = await self._execute_single_team(team_name, shared_state, state)

            # ✨ 완료 후: 상태 업데이트
            if step_id:
                status = "completed" if result.get("status") == "completed" else "failed"
                planning_state = StateTransition.update_step_status(
                    planning_state,
                    step_id,
                    status,
                    progress=100,
                    error=result.get("error")
                )
                # 결과 저장
                for step in planning_state["execution_steps"]:
                    if step["step_id"] == step_id:
                        step["result"] = result
                        break

                state["planning_state"] = planning_state

            # 결과 병합 (기존 로직)
            state = StateManager.merge_team_results(state, team_name, result)

        except Exception as e:
            logger.error(f"[TeamSupervisor] Team '{team_name}' failed: {e}")

            # ✨ 실패 시: 상태 업데이트
            if step_id:
                planning_state = StateTransition.update_step_status(
                    planning_state,
                    step_id,
                    "failed",
                    error=str(e)
                )
                state["planning_state"] = planning_state

    return state

def _find_step_id_for_team(
    self,
    team_name: str,
    planning_state: Optional[PlanningState]
) -> Optional[str]:
    """팀 이름으로 step_id 찾기"""
    if not planning_state:
        return None

    for step in planning_state["execution_steps"]:
        if step["agent_name"] == team_name:
            return step["step_id"]

    return None
```

---

## 📐 Phase 4: API 추가 (사용자 개입)

### 파일: `api/todo_api.py` (신규 생성)

```python
"""
TODO 관리 API
사용자가 TODO 조회/수정/승인할 수 있는 REST API
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional, Literal

router = APIRouter(prefix="/api/todos", tags=["todos"])


# === Request/Response Models ===

class StepModificationRequest(BaseModel):
    """Step 수정 요청"""
    step_id: str
    modifications: Dict[str, Any]
    reason: Optional[str] = None


class AddStepRequest(BaseModel):
    """Step 추가 요청"""
    agent_name: str
    description: str
    priority: int
    dependencies: List[str] = []
    optional: bool = False
    reason: Optional[str] = None


class RemoveStepRequest(BaseModel):
    """Step 제거 요청"""
    step_id: str
    reason: Optional[str] = None


# === API Endpoints ===

@router.get("/{session_id}")
async def get_todos(session_id: str):
    """
    TODO 리스트 조회

    Returns:
        {
            "session_id": str,
            "execution_steps": List[ExecutionStepState],
            "overall_progress": int,
            "completed_count": int,
            "total_count": int,
            "awaiting_approval": bool,
            "user_approved": bool
        }
    """
    # Checkpoint에서 최신 state 로드
    state = await _load_latest_state(session_id)

    if not state:
        raise HTTPException(status_code=404, detail="Session not found")

    planning_state = state.get("planning_state")

    if not planning_state:
        raise HTTPException(status_code=404, detail="No planning state found")

    return {
        "session_id": session_id,
        "execution_steps": planning_state["execution_steps"],
        "overall_progress": planning_state["overall_progress_percentage"],
        "completed_count": planning_state["completed_step_count"],
        "total_count": planning_state["total_step_count"],
        "awaiting_approval": planning_state["awaiting_user_approval"],
        "user_approved": planning_state["user_approved"]
    }


@router.get("/{session_id}/progress")
async def get_progress(session_id: str):
    """
    진행률만 조회 (가벼운 API)

    Returns:
        {
            "overall_progress": int,
            "completed_count": int,
            "failed_count": int,
            "total_count": int,
            "current_step": str
        }
    """
    state = await _load_latest_state(session_id)

    if not state:
        raise HTTPException(status_code=404, detail="Session not found")

    planning_state = state.get("planning_state")

    # 현재 실행 중인 step 찾기
    current_step = None
    for step in planning_state["execution_steps"]:
        if step["status"] == "in_progress":
            current_step = step["description"]
            break

    return {
        "overall_progress": planning_state["overall_progress_percentage"],
        "completed_count": planning_state["completed_step_count"],
        "failed_count": planning_state["failed_step_count"],
        "total_count": planning_state["total_step_count"],
        "current_step": current_step
    }


@router.post("/{session_id}/modify")
async def modify_step(session_id: str, request: StepModificationRequest):
    """
    Step 수정

    Example:
        {
            "step_id": "step_0",
            "modifications": {
                "priority": 10,
                "optional": true
            },
            "reason": "우선순위 변경"
        }
    """
    state = await _load_latest_state(session_id)
    planning_state = state.get("planning_state")

    # 수정 적용
    planning_state = StateTransition.modify_step_by_user(
        planning_state,
        request.step_id,
        request.modifications,
        request.reason
    )

    state["planning_state"] = planning_state

    # State 저장 (checkpoint)
    await _save_state(session_id, state)

    return {"success": True, "modified_step_id": request.step_id}


@router.post("/{session_id}/add")
async def add_step(session_id: str, request: AddStepRequest):
    """Step 추가"""
    state = await _load_latest_state(session_id)
    planning_state = state.get("planning_state")

    # 새 step 생성
    new_step_id = f"step_{len(planning_state['execution_steps'])}"
    new_step = ExecutionStepState(
        step_id=new_step_id,
        agent_name=request.agent_name,
        description=request.description,
        priority=request.priority,
        dependencies=request.dependencies,
        timeout=30,
        retry_count=1,
        optional=request.optional,
        input_mapping={},
        status="pending",
        progress_percentage=0,
        # ... 나머지 필드 초기화
    )

    # 추가
    planning_state = StateTransition.add_step_by_user(
        planning_state,
        new_step,
        request.reason
    )

    state["planning_state"] = planning_state
    await _save_state(session_id, state)

    return {"success": True, "new_step_id": new_step_id}


@router.delete("/{session_id}/{step_id}")
async def remove_step(session_id: str, step_id: str, reason: Optional[str] = None):
    """Step 제거"""
    state = await _load_latest_state(session_id)
    planning_state = state.get("planning_state")

    planning_state = StateTransition.remove_step_by_user(
        planning_state,
        step_id,
        reason
    )

    state["planning_state"] = planning_state
    await _save_state(session_id, state)

    return {"success": True, "removed_step_id": step_id}


@router.post("/{session_id}/approve")
async def approve_plan(session_id: str):
    """계획 승인"""
    state = await _load_latest_state(session_id)
    planning_state = state.get("planning_state")

    planning_state = StateTransition.approve_plan(planning_state)

    state["planning_state"] = planning_state
    await _save_state(session_id, state)

    return {"success": True, "approved": True}


@router.get("/{session_id}/history")
async def get_modification_history(session_id: str):
    """수정 이력 조회"""
    state = await _load_latest_state(session_id)
    planning_state = state.get("planning_state")

    return {
        "modifications": planning_state["user_modifications"],
        "total_count": len(planning_state["user_modifications"])
    }


@router.get("/{session_id}/checkpoints")
async def list_checkpoints(session_id: str):
    """
    복원 가능한 checkpoint 목록

    Returns:
        {
            "checkpoints": [
                {
                    "checkpoint_id": str,
                    "timestamp": str,
                    "phase": str,
                    "overall_progress": int
                }
            ]
        }
    """
    # AsyncSqliteSaver에서 checkpoint 목록 조회
    checkpoints = await _get_checkpoints_for_session(session_id)

    return {"checkpoints": checkpoints}


@router.post("/{session_id}/rollback")
async def rollback_to_checkpoint(session_id: str, checkpoint_id: str):
    """특정 checkpoint로 롤백"""
    # Checkpoint 복원
    state = await _restore_from_checkpoint(session_id, checkpoint_id)

    if not state:
        raise HTTPException(status_code=404, detail="Checkpoint not found")

    return {
        "success": True,
        "checkpoint_id": checkpoint_id,
        "restored_state": {
            "current_phase": state.get("current_phase"),
            "overall_progress": state.get("planning_state", {}).get("overall_progress_percentage", 0)
        }
    }


# === Helper Functions ===

async def _load_latest_state(session_id: str) -> Optional[MainSupervisorState]:
    """최신 state 로드 (checkpoint에서)"""
    # TODO: AsyncSqliteSaver에서 로드
    # checkpointer.get_state({"configurable": {"thread_id": session_id}})
    pass


async def _save_state(session_id: str, state: MainSupervisorState):
    """State 저장 (checkpoint)"""
    # TODO: AsyncSqliteSaver에 저장
    pass


async def _get_checkpoints_for_session(session_id: str) -> List[Dict]:
    """Session의 checkpoint 목록"""
    # TODO: SQLite query
    # SELECT checkpoint_id, metadata FROM checkpoints WHERE thread_id = ?
    pass


async def _restore_from_checkpoint(session_id: str, checkpoint_id: str) -> Optional[MainSupervisorState]:
    """Checkpoint 복원"""
    # TODO: AsyncSqliteSaver.get_state()
    pass
```

---

## 📐 Phase 5: Checkpoint 통합 강화

### 파일: `foundation/checkpointer.py` (기존 파일 확장)

```python
class CheckpointerManager:
    # 기존 메서드들...

    async def get_state(
        self,
        session_id: str,
        checkpoint_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        State 조회

        Args:
            session_id: Session ID (thread_id)
            checkpoint_id: 특정 checkpoint ID (None이면 최신)

        Returns:
            복원된 state
        """
        checkpointer = await self.create_checkpointer()

        config = {"configurable": {"thread_id": session_id}}

        if checkpoint_id:
            # 특정 checkpoint 복원
            config["configurable"]["checkpoint_id"] = checkpoint_id

        # LangGraph의 get_state() 사용
        state_snapshot = await checkpointer.aget_tuple(config)

        if state_snapshot:
            return state_snapshot.values  # State dict

        return None

    async def list_checkpoints(
        self,
        session_id: str
    ) -> List[Dict[str, Any]]:
        """
        Session의 모든 checkpoint 목록

        Returns:
            [
                {
                    "checkpoint_id": str,
                    "parent_id": str,
                    "timestamp": str,
                    "metadata": dict
                }
            ]
        """
        import sqlite3

        db_path = self.checkpoint_dir / "default_checkpoint.db"
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT checkpoint_id, parent_checkpoint_id, metadata
            FROM checkpoints
            WHERE thread_id = ?
            ORDER BY checkpoint_id DESC
        """, (session_id,))

        checkpoints = []
        for row in cursor.fetchall():
            # metadata는 BLOB이므로 파싱 필요
            import pickle
            metadata = pickle.loads(row["metadata"]) if row["metadata"] else {}

            checkpoints.append({
                "checkpoint_id": row["checkpoint_id"],
                "parent_id": row["parent_checkpoint_id"],
                "metadata": metadata
            })

        conn.close()
        return checkpoints
```

---

## 📊 데이터 흐름 (최종)

```
1. 사용자 질문
   ↓
2. PlanningAgent.analyze_intent() + create_execution_plan()
   ↓
3. ExecutionStep[] → ExecutionStepState[] 변환
   ↓
4. PlanningState 생성 (execution_steps 포함)
   ↓
5. [Checkpoint 1 저장: "planning 완료"]
   ↓
6. (옵션) 사용자 승인 대기
   ├─ GET /api/todos/{session_id} → TODO 리스트 조회
   ├─ POST /api/todos/{session_id}/modify → TODO 수정
   └─ POST /api/todos/{session_id}/approve → 승인
   ↓
7. [Checkpoint 2 저장: "사용자 수정 후"]
   ↓
8. TeamSupervisor.execute_teams_node()
   ├─ 각 팀 시작 전: StateTransition.update_step_status("in_progress")
   ├─ [Checkpoint 3 저장]
   ├─ 팀 실행
   ├─ 완료 후: StateTransition.update_step_status("completed")
   └─ [Checkpoint 4 저장]
   ↓
9. 최종 응답 생성
   ↓
10. (언제든) GET /api/todos/{session_id}/progress → 진행률 조회
11. (언제든) POST /api/todos/{session_id}/rollback → 과거로 복원
```

---

## 🗂️ 파일 구조

```
backend/app/service_agent/
├── foundation/
│   ├── separated_states.py         # ✨ 확장: ExecutionStepState, UserModification 추가
│   │                                #        StateTransition 메서드 추가
│   ├── checkpointer.py             # ✨ 확장: get_state(), list_checkpoints() 추가
│   └── (기타 기존 파일들)
│
├── supervisor/
│   └── team_supervisor.py          # ✨ 수정: planning_node, execute_teams_node 확장
│
├── api/
│   └── todo_api.py                 # ✨ 신규: TODO 관리 REST API
│
└── tests/
    ├── test_todo_state.py          # ✨ 신규: State 확장 테스트
    ├── test_todo_api.py            # ✨ 신규: API 테스트
    └── test_todo_checkpoint.py     # ✨ 신규: Checkpoint 통합 테스트
```

---

## ⚡ 구현 순서 (수정판)

### Week 1: State 확장 및 핵심 로직
- **Day 1-2**: `separated_states.py` 확장
  - ExecutionStepState 정의
  - PlanningState 확장
  - UserModification 정의

- **Day 3-4**: `StateTransition` 메서드 추가
  - update_step_status()
  - modify_step_by_user()
  - add_step_by_user()
  - remove_step_by_user()
  - approve_plan()

- **Day 5**: 테스트 작성 및 검증
  - test_todo_state.py

### Week 2: Supervisor 통합 및 API
- **Day 6-7**: `team_supervisor.py` 수정
  - planning_node 확장
  - execute_teams_node 확장
  - _convert_to_step_states() 추가

- **Day 8-9**: API 구현
  - todo_api.py 작성
  - helper 함수 구현

- **Day 10**: Checkpointer 확장
  - get_state() 구현
  - list_checkpoints() 구현

### Week 3: 테스트 및 문서화
- **Day 11-12**: 통합 테스트
  - End-to-end 시나리오 테스트
  - API 테스트

- **Day 13**: 문서화
  - API 문서
  - 사용 가이드

---

## ✅ 체크리스트

### Phase 1: State 확장
- [ ] ExecutionStepState TypedDict 정의
- [ ] PlanningState 확장 (필드 추가)
- [ ] UserModification TypedDict 정의
- [ ] StateValidator에 새 필드 검증 추가

### Phase 2: StateTransition 확장
- [ ] update_step_status() 구현
- [ ] modify_step_by_user() 구현
- [ ] add_step_by_user() 구현
- [ ] remove_step_by_user() 구현
- [ ] approve_plan() 구현
- [ ] _recalculate_overall_progress() 구현

### Phase 3: Supervisor 통합
- [ ] planning_node 수정
- [ ] _convert_to_step_states() 구현
- [ ] execute_teams_node 수정
- [ ] _find_step_id_for_team() 구현

### Phase 4: API 구현
- [ ] FastAPI router 생성
- [ ] GET /todos/{session_id}
- [ ] GET /todos/{session_id}/progress
- [ ] POST /todos/{session_id}/modify
- [ ] POST /todos/{session_id}/add
- [ ] DELETE /todos/{session_id}/{step_id}
- [ ] POST /todos/{session_id}/approve
- [ ] GET /todos/{session_id}/history
- [ ] GET /todos/{session_id}/checkpoints
- [ ] POST /todos/{session_id}/rollback

### Phase 5: Checkpoint 강화
- [ ] CheckpointerManager.get_state() 구현
- [ ] CheckpointerManager.list_checkpoints() 구현
- [ ] API helper 함수 구현

### Testing
- [ ] State 확장 단위 테스트
- [ ] StateTransition 단위 테스트
- [ ] API 통합 테스트
- [ ] Checkpoint 복원 테스트
- [ ] End-to-end 시나리오 테스트

---

## 📝 요약

### 핵심 전략
1. **기존 구조 최대한 활용** - 새 파일 최소화
2. **PlanningState.execution_steps가 곧 TODO 리스트** - 표준화만 추가
3. **StateTransition 확장** - 기존 클래스에 메서드만 추가
4. **Checkpoint는 이미 완성** - 조회 API만 추가
5. **최소 침습 수정** - 기존 로직 유지, 확장만

### 새로 추가되는 것
- **TypedDict**: ExecutionStepState, UserModification
- **State 필드**: PlanningState에 승인/수정 관련 필드
- **메서드**: StateTransition에 TODO 관리 메서드
- **API**: todo_api.py (신규)
- **Helper**: Checkpointer 조회 메서드

**예상 개발 기간**: 2-3주
