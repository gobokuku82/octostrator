# 📋 Dynamic Execution Control System 구현 계획서

**작성일**: 2025-10-05
**작성자**: Claude Code
**목적**: ExecutionPlan을 실시간 조회·수정 가능한 동적 TODO 시스템으로 업그레이드

---

## 🎯 개요

### 현재 상황
- **ExecutionPlan**: 정적 계획서 (생성 후 수정 불가)
- **문제점**:
  - ❌ 실행 중 계획 변경 불가능
  - ❌ 사용자 개입 불가능
  - ❌ 실패 시 재시도/스킵 로직 없음
  - ❌ 실행 중단 후 재개 불가능
  - ❌ 진행 상황 실시간 모니터링 불가

### 목표
ExecutionPlan을 **Dynamic Execution Control System**으로 업그레이드:
1. **Checkpointer**: SQLite 기반 상태 영구 저장 및 복원
2. **TODO System**: 실시간 상태 추적 및 관리
3. **Human-in-the-Loop**: 사용자 승인 및 개입 가능
4. **Command Interface**: 명령어 기반 조회·수정
5. **Interrupt**: 특정 시점에서 실행 중단·재개

---

## 🏗️ 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────────────┐
│                   Dynamic Execution Control System                │
└─────────────────────────────────────────────────────────────────┘

[사용자 쿼리]
    ↓
┌────────────────────────────────┐
│ PlanningAgent                  │
│ - Intent 분석 (LLM)            │
│ - Agent 선택 (LLM)             │
│ - ExecutionPlan 생성           │
└────────────────────────────────┘
    ↓
┌────────────────────────────────┐
│ ExecutionPlanConverter         │
│ - ExecutionPlan → TODO 변환    │
│ - 의존성 자동 매핑             │
└────────────────────────────────┘
    ↓
┌────────────────────────────────────────────────────────────────┐
│                        LangGraph Workflow                       │
│                                                                 │
│  [planning] → [approval] → [execute] → [approval] → ...        │
│                   ↑ INTERRUPT      ↑ INTERRUPT                 │
│                   사용자 개입      사용자 개입                  │
└────────────────────────────────────────────────────────────────┘
    ↓
┌────────────────────────────────┐
│ AsyncSqliteSaver (Checkpointer)│
│ - State 자동 저장              │
│ - Checkpoint 생성              │
│ - 복원/롤백 지원               │
└────────────────────────────────┘
    ↓
┌────────────────────────────────┐
│ CommandHandler                 │
│ - /todos: 목록 조회            │
│ - /todo approve: 승인          │
│ - /todo skip: 건너뛰기         │
│ - /todo add: 추가              │
│ - /checkpoint list: 목록       │
│ - /checkpoint restore: 복원    │
└────────────────────────────────┘
```

---

## 📦 Phase 1: Checkpointer 통합

### 목표
모든 State를 SQLite에 영구 저장하여 실행 중단/재개 가능하도록 구현

### 1.1 AsyncSqliteSaver 초기화

**파일**: `backend/app/service_agent/foundation/checkpointer.py` (신규)

```python
"""
Checkpointer 관리 모듈
AsyncSqliteSaver를 사용하여 LangGraph State를 SQLite에 저장
"""

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


async def create_checkpointer(
    db_path: str = "backend/checkpoints/service_agent.db"
) -> AsyncSqliteSaver:
    """
    AsyncSqliteSaver 생성 및 초기화

    Args:
        db_path: SQLite DB 파일 경로

    Returns:
        AsyncSqliteSaver 인스턴스

    저장 내용:
        - MainSupervisorState 전체
        - PlanningState (todos, completed_ids 등)
        - 각 팀의 실행 결과
        - 실행 히스토리 (checkpoint 리스트)

    특징:
        - 각 노드 실행 후 자동 checkpoint 생성
        - thread_id로 세션별 관리
        - checkpoint_id로 특정 시점 복원 가능
    """
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    # AsyncSqliteSaver 생성
    checkpointer = AsyncSqliteSaver.from_conn_string(str(path))

    # 테이블 초기화
    await checkpointer.setup()

    logger.info(f"AsyncSqliteSaver initialized at {path}")

    return checkpointer


async def get_checkpointer_instance():
    """
    싱글톤 패턴으로 Checkpointer 인스턴스 반환
    """
    if not hasattr(get_checkpointer_instance, "_instance"):
        get_checkpointer_instance._instance = await create_checkpointer()

    return get_checkpointer_instance._instance
```

### 1.2 TeamSupervisor에 Checkpointer 적용

**파일**: `backend/app/service_agent/supervisor/team_supervisor.py` (수정)

```python
# 기존 코드 수정

from app.service_agent.foundation.checkpointer import get_checkpointer_instance

class TeamSupervisor:
    def __init__(
        self,
        planning_agent: PlanningAgent,
        teams: Dict[str, Any],
        enable_checkpointing: bool = True  # 🔥 Checkpointing 활성화 옵션
    ):
        self.planning_agent = planning_agent
        self.teams = teams
        self.enable_checkpointing = enable_checkpointing
        self.checkpointer = None

        # Workflow 구성
        self._build_workflow()

    async def initialize(self):
        """비동기 초기화 (Checkpointer 생성)"""
        if self.enable_checkpointing:
            self.checkpointer = await get_checkpointer_instance()
            # Workflow 재컴파일 (Checkpointer 포함)
            self.app = self.workflow.compile(checkpointer=self.checkpointer)

    def _build_workflow(self):
        workflow = StateGraph(MainSupervisorState)

        # 기존 노드들...
        workflow.add_node("planning", self.planning_node)
        workflow.add_node("execute_teams", self.execute_teams_node)
        workflow.add_node("aggregate", self.aggregate_node)
        workflow.add_node("generate_response", self.generate_response_node)

        # Edge 설정
        workflow.set_entry_point("planning")
        workflow.add_conditional_edges("planning", ...)
        workflow.add_edge("execute_teams", "aggregate")
        workflow.add_edge("aggregate", "generate_response")
        workflow.add_edge("generate_response", END)

        # 임시 컴파일 (Checkpointer 없이)
        self.workflow = workflow
        self.app = workflow.compile()

    async def execute(
        self,
        query: str,
        session_id: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        쿼리 실행 (Checkpointer 사용)

        Args:
            query: 사용자 쿼리
            session_id: 세션 ID (thread_id로 사용)

        Returns:
            실행 결과
        """
        # 초기 State 생성
        initial_state = MainSupervisorState(
            query=query,
            session_id=session_id,
            request_id=f"req_{session_id}_{datetime.now().timestamp()}",
            # ... 기타 필드
        )

        # 🔥 Checkpointer 사용 설정
        config = {
            "configurable": {
                "thread_id": f"session_{session_id}"
            }
        }

        # LangGraph 실행
        result = await self.app.ainvoke(initial_state, config=config)

        return result
```

### 1.3 각 Executor에 Checkpointer 적용

**파일**: `backend/app/service_agent/execution_agents/analysis_executor.py` (수정)

```python
class AnalysisExecutor:
    def __init__(self, llm_context=None, checkpointer=None):
        self.llm_context = llm_context
        self.checkpointer = checkpointer  # 🔥 Checkpointer 받기
        self.team_name = "AnalysisTeam"

        # Workflow 구성
        self._build_workflow()

    def _build_workflow(self):
        workflow = StateGraph(AnalysisTeamState)

        # 노드 추가
        workflow.add_node("prepare", self.prepare_analysis_node)
        workflow.add_node("preprocess", self.preprocess_data_node)
        workflow.add_node("analyze", self.analyze_data_node)
        workflow.add_node("generate_insights", self.generate_insights_node)
        workflow.add_node("create_report", self.create_report_node)
        workflow.add_node("finalize", self.finalize_node)

        # Edge 설정
        workflow.set_entry_point("prepare")
        workflow.add_edge("prepare", "preprocess")
        workflow.add_edge("preprocess", "analyze")
        workflow.add_edge("analyze", "generate_insights")
        workflow.add_edge("generate_insights", "create_report")
        workflow.add_edge("create_report", "finalize")
        workflow.add_edge("finalize", END)

        # 🔥 Checkpointer 적용
        if self.checkpointer:
            self.app = workflow.compile(checkpointer=self.checkpointer)
        else:
            self.app = workflow.compile()

    async def execute(
        self,
        shared_state: SharedState,
        analysis_type: str = "comprehensive",
        input_data: Optional[Dict] = None
    ) -> AnalysisTeamState:
        """
        AnalysisTeam 실행

        Args:
            shared_state: 공유 상태
            analysis_type: 분석 타입
            input_data: 입력 데이터

        Returns:
            분석 결과 State
        """
        # 초기 상태 생성
        initial_state = AnalysisTeamState(
            team_name=self.team_name,
            status="pending",
            shared_context=shared_state,
            analysis_type=analysis_type,
            input_data=input_data or {},
            raw_analysis={},
            # ... 기타 필드
        )

        # 🔥 Checkpointer 사용 (thread_id는 shared_state.session_id 사용)
        if self.checkpointer:
            config = {
                "configurable": {
                    "thread_id": f"analysis_{shared_state.get('session_id', 'default')}"
                }
            }
            result = await self.app.ainvoke(initial_state, config=config)
        else:
            result = await self.app.ainvoke(initial_state)

        return result
```

**동일하게 적용할 파일**:
- `search_executor.py`
- `document_executor.py`

---

## 📦 Phase 2: TODO 시스템 구현

### 목표
ExecutionPlan을 상태 추적 가능한 TODO 리스트로 변환

### 2.1 TODO 타입 정의

**파일**: `backend/app/service_agent/foundation/todo_types.py` (신규)

```python
"""
TODO 관리 시스템
ExecutionPlan을 동적으로 관리 가능한 TODO 리스트로 변환
"""

from typing import Dict, Any, List, Optional
from enum import Enum
from datetime import datetime
from dataclasses import dataclass, field


class TodoStatus(Enum):
    """TODO 상태"""
    PENDING = "pending"              # 대기 중
    IN_PROGRESS = "in_progress"      # 진행 중
    COMPLETED = "completed"          # 완료
    FAILED = "failed"                # 실패
    SKIPPED = "skipped"              # 건너뜀
    BLOCKED = "blocked"              # 차단됨 (의존성 미충족)
    WAITING_APPROVAL = "waiting_approval"  # 사용자 승인 대기


class TodoPriority(Enum):
    """TODO 우선순위"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class SupervisorTodo:
    """
    Supervisor 레벨 TODO
    ExecutionStep을 TODO로 변환한 형태
    """
    # 기본 정보
    id: str
    name: str
    description: str = ""

    # Agent 정보
    agent_name: str = ""
    agent_purpose: str = ""
    expected_output: str = ""

    # 상태 관리
    status: TodoStatus = TodoStatus.PENDING
    priority: TodoPriority = TodoPriority.MEDIUM

    # 의존성
    dependencies: List[str] = field(default_factory=list)  # 다른 TODO ID 리스트

    # 시간 추적
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # 메타데이터
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

    # 재시도
    retry_count: int = 0
    max_retries: int = 3

    def can_start(self, completed_todo_ids: List[str]) -> bool:
        """
        실행 가능 여부 확인

        Args:
            completed_todo_ids: 완료된 TODO ID 리스트

        Returns:
            실행 가능 여부
        """
        # 의존성 체크
        return all(dep_id in completed_todo_ids for dep_id in self.dependencies)

    def start(self):
        """작업 시작"""
        self.status = TodoStatus.IN_PROGRESS
        self.started_at = datetime.now()

    def complete(self):
        """작업 완료"""
        self.status = TodoStatus.COMPLETED
        self.completed_at = datetime.now()

    def fail(self, error: str):
        """작업 실패"""
        self.status = TodoStatus.FAILED
        self.error = error
        self.completed_at = datetime.now()

    def skip(self, reason: str = ""):
        """작업 건너뛰기"""
        self.status = TodoStatus.SKIPPED
        if reason:
            self.error = f"Skipped: {reason}"
        self.completed_at = datetime.now()

    def block(self, reason: str):
        """작업 차단"""
        self.status = TodoStatus.BLOCKED
        self.error = f"Blocked: {reason}"

    def should_retry(self) -> bool:
        """재시도 필요 여부"""
        return (
            self.status == TodoStatus.FAILED and
            self.retry_count < self.max_retries
        )

    def retry(self):
        """재시도"""
        self.retry_count += 1
        self.status = TodoStatus.PENDING
        self.error = None

    @property
    def duration(self) -> Optional[float]:
        """작업 소요 시간 (초)"""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    def to_dict(self) -> Dict[str, Any]:
        """
        딕셔너리로 변환 (State에 저장 가능한 형태)
        """
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "agent_name": self.agent_name,
            "agent_purpose": self.agent_purpose,
            "expected_output": self.expected_output,
            "status": self.status.value,
            "priority": self.priority.value,
            "dependencies": self.dependencies,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration": self.duration,
            "metadata": self.metadata,
            "error": self.error,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SupervisorTodo":
        """
        딕셔너리에서 객체 생성 (State에서 복원)
        """
        return cls(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            agent_name=data.get("agent_name", ""),
            agent_purpose=data.get("agent_purpose", ""),
            expected_output=data.get("expected_output", ""),
            status=TodoStatus(data["status"]),
            priority=TodoPriority(data.get("priority", "medium")),
            dependencies=data.get("dependencies", []),
            created_at=datetime.fromisoformat(data["created_at"]),
            started_at=datetime.fromisoformat(data["started_at"]) if data.get("started_at") else None,
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
            metadata=data.get("metadata", {}),
            error=data.get("error"),
            retry_count=data.get("retry_count", 0),
            max_retries=data.get("max_retries", 3)
        )


class TodoManager:
    """
    TODO 관리자
    TODO 리스트를 관리하고 다음 실행 가능한 TODO를 찾는 유틸리티
    """

    def __init__(self):
        self.todos: List[SupervisorTodo] = []
        self.completed_ids: List[str] = []
        self.failed_ids: List[str] = []
        self.skipped_ids: List[str] = []

    def add_todo(self, todo: SupervisorTodo):
        """TODO 추가"""
        self.todos.append(todo)

    def get_todo(self, todo_id: str) -> Optional[SupervisorTodo]:
        """TODO 조회"""
        for todo in self.todos:
            if todo.id == todo_id:
                return todo
        return None

    def find_next_executable(self) -> Optional[SupervisorTodo]:
        """
        다음 실행 가능한 TODO 찾기

        조건:
        1. status == PENDING
        2. dependencies가 모두 완료됨

        Returns:
            실행 가능한 TODO (없으면 None)
        """
        for todo in self.todos:
            if todo.status == TodoStatus.PENDING:
                if todo.can_start(self.completed_ids):
                    return todo

        return None

    def update_status(
        self,
        todo_id: str,
        status: TodoStatus,
        error: str = None
    ):
        """TODO 상태 업데이트"""
        todo = self.get_todo(todo_id)
        if not todo:
            return

        if status == TodoStatus.IN_PROGRESS:
            todo.start()
        elif status == TodoStatus.COMPLETED:
            todo.complete()
            self.completed_ids.append(todo_id)
        elif status == TodoStatus.FAILED:
            todo.fail(error or "Unknown error")
            self.failed_ids.append(todo_id)
        elif status == TodoStatus.SKIPPED:
            todo.skip(error or "")
            self.skipped_ids.append(todo_id)
        elif status == TodoStatus.BLOCKED:
            todo.block(error or "Dependencies not met")
        else:
            todo.status = status

    def get_summary(self) -> Dict[str, Any]:
        """TODO 목록 요약"""
        return {
            "total": len(self.todos),
            "pending": sum(1 for t in self.todos if t.status == TodoStatus.PENDING),
            "in_progress": sum(1 for t in self.todos if t.status == TodoStatus.IN_PROGRESS),
            "completed": len(self.completed_ids),
            "failed": len(self.failed_ids),
            "skipped": len(self.skipped_ids),
            "todos": [todo.to_dict() for todo in self.todos]
        }
```

### 2.2 ExecutionPlan → TODO 변환기

**파일**: `backend/app/service_agent/cognitive_agents/plan_converter.py` (신규)

```python
"""
ExecutionPlan을 SupervisorTodo 리스트로 변환
"""

from typing import List
from app.service_agent.cognitive_agents.planning_agent import ExecutionPlan, ExecutionStep
from app.service_agent.foundation.todo_types import SupervisorTodo, TodoPriority


class ExecutionPlanConverter:
    """ExecutionPlan → SupervisorTodo 변환기"""

    @staticmethod
    def convert(execution_plan: ExecutionPlan) -> List[SupervisorTodo]:
        """
        ExecutionPlan을 SupervisorTodo 리스트로 변환

        Args:
            execution_plan: PlanningAgent가 생성한 ExecutionPlan

        Returns:
            SupervisorTodo 리스트

        변환 로직:
        1. ExecutionStep → SupervisorTodo
        2. agent_name 기반 의존성 매핑
        3. priority, timeout 등 메타데이터 저장
        """
        todos = []
        agent_to_id = {}  # agent_name → todo_id 매핑

        for i, step in enumerate(execution_plan.steps):
            todo_id = f"todo_{i+1:03d}"
            agent_to_id[step.agent_name] = todo_id

            # dependencies 변환: agent_name → todo_id
            dep_ids = []
            for dep_agent in step.dependencies:
                if dep_agent in agent_to_id:
                    dep_ids.append(agent_to_id[dep_agent])

            # Priority 변환
            if step.priority == 0:
                priority = TodoPriority.HIGH
            elif step.priority == 1:
                priority = TodoPriority.MEDIUM
            else:
                priority = TodoPriority.LOW

            # SupervisorTodo 생성
            todo = SupervisorTodo(
                id=todo_id,
                name=f"{step.agent_name} 실행",
                description=f"{step.agent_name}을(를) 실행하여 데이터 수집/분석 수행",
                agent_name=step.agent_name,
                agent_purpose=step.input_mapping.get("purpose", ""),
                priority=priority,
                dependencies=dep_ids,
                max_retries=step.retry_count,
                metadata={
                    "timeout": step.timeout,
                    "optional": step.optional,
                    "input_mapping": step.input_mapping,
                    "original_priority": step.priority
                }
            )

            todos.append(todo)

        return todos

    @staticmethod
    def convert_with_strategy(
        execution_plan: ExecutionPlan
    ) -> tuple[List[SupervisorTodo], str]:
        """
        ExecutionPlan을 TODO로 변환하고 실행 전략도 반환

        Returns:
            (todos, strategy)
        """
        todos = ExecutionPlanConverter.convert(execution_plan)
        strategy = execution_plan.strategy.value  # "sequential", "parallel" 등

        return todos, strategy
```

### 2.3 State 확장 (TODO 필드 추가)

**파일**: `backend/app/service_agent/foundation/separated_states.py` (수정)

```python
# PlanningState 수정

class PlanningState(TypedDict):
    """계획 수립 전용 State"""
    raw_query: str
    analyzed_intent: Dict[str, Any]
    intent_confidence: float
    available_agents: List[str]
    available_teams: List[str]

    # 🔥 TODO 시스템 필드 추가
    todos: List[Dict[str, Any]]  # SupervisorTodo.to_dict() 리스트
    completed_todo_ids: List[str]
    failed_todo_ids: List[str]
    skipped_todo_ids: List[str]
    current_todo_id: Optional[str]

    # 기존 필드 (하위 호환성)
    execution_steps: List[Dict[str, Any]]
    execution_strategy: str
    parallel_groups: Optional[List[List[str]]]
    plan_validated: bool
    validation_errors: List[str]
    estimated_total_time: float
```

---

## 📦 Phase 3: Human-in-the-Loop 구현

### 목표
사용자가 실행 중 개입하여 계획을 수정하고 승인할 수 있도록 구현

### 3.1 Approval 노드 추가

**파일**: `backend/app/service_agent/supervisor/team_supervisor.py` (수정)

```python
class TeamSupervisor:
    def _build_workflow(self):
        """
        Workflow 구성 (Human-in-the-Loop 포함)
        """
        workflow = StateGraph(MainSupervisorState)

        # 노드 추가
        workflow.add_node("planning", self.planning_node)
        workflow.add_node("approval", self.approval_node)  # 🔥 승인 노드
        workflow.add_node("execute_teams", self.execute_teams_node)
        workflow.add_node("aggregate", self.aggregate_node)
        workflow.add_node("generate_response", self.generate_response_node)

        # Edge 설정
        workflow.set_entry_point("planning")
        workflow.add_edge("planning", "approval")

        # 🔥 approval → execute_teams (조건부)
        workflow.add_conditional_edges(
            "approval",
            self._check_approval_status,
            {
                "execute": "execute_teams",  # 승인됨 → 실행
                "wait": END,  # 승인 대기 → 중단
                "completed": "aggregate"  # 모든 TODO 완료 → 집계
            }
        )

        # execute_teams → approval (다음 TODO 승인)
        workflow.add_edge("execute_teams", "approval")

        workflow.add_edge("aggregate", "generate_response")
        workflow.add_edge("generate_response", END)

        # 🔥 Checkpointer + Interrupt 설정
        if self.checkpointer:
            self.app = workflow.compile(
                checkpointer=self.checkpointer,
                interrupt_before=["approval"]  # approval 전에 중단
            )
        else:
            self.app = workflow.compile()

    async def approval_node(self, state: MainSupervisorState):
        """
        사용자 승인 노드

        기능:
        1. 다음 실행 가능한 TODO 찾기
        2. 사용자에게 승인 요청 메시지 생성
        3. INTERRUPT 발생 → 사용자 개입 대기

        사용자가 할 수 있는 작업:
        - /todo approve: 승인 (다음 TODO 실행)
        - /todo skip <id>: TODO 건너뛰기
        - /todo add <agent>: 새 TODO 추가
        - /todos: TODO 목록 조회
        """
        from app.service_agent.foundation.todo_types import SupervisorTodo, TodoStatus

        # TODO 리스트 가져오기
        todos = [
            SupervisorTodo.from_dict(t)
            for t in state["planning_state"]["todos"]
        ]
        completed_ids = state["planning_state"]["completed_todo_ids"]

        # 다음 실행 가능한 TODO 찾기
        next_todo = None
        for todo in todos:
            if todo.status == TodoStatus.PENDING and todo.can_start(completed_ids):
                next_todo = todo
                break

        if not next_todo:
            # 모든 TODO 완료
            state["approval_status"] = "completed"
            state["approval_message"] = "✅ 모든 작업이 완료되었습니다."
            return state

        # 🔥 사용자 승인 대기 상태
        state["approval_status"] = "waiting"
        state["planning_state"]["current_todo_id"] = next_todo.id
        state["approval_message"] = (
            f"📋 다음 작업을 실행하시겠습니까?\n\n"
            f"- TODO ID: {next_todo.id}\n"
            f"- 작업명: {next_todo.name}\n"
            f"- Agent: {next_todo.agent_name}\n"
            f"- 우선순위: {next_todo.priority.value}\n"
            f"- 의존성: {', '.join(next_todo.dependencies) if next_todo.dependencies else '없음'}\n\n"
            f"명령어:\n"
            f"  /todo approve    - 승인\n"
            f"  /todo skip {next_todo.id}  - 건너뛰기\n"
            f"  /todos           - TODO 목록 조회"
        )

        # 여기서 INTERRUPT 발생 → 사용자 개입 가능
        return state

    def _check_approval_status(self, state: MainSupervisorState) -> str:
        """
        승인 상태 확인 (라우팅 함수)

        Returns:
            "execute": 승인됨 → 실행
            "wait": 승인 대기 → 중단
            "completed": 모든 TODO 완료 → 집계
        """
        status = state.get("approval_status", "waiting")

        if status == "approved":
            return "execute"
        elif status == "completed":
            return "completed"
        else:
            return "wait"

    async def execute_teams_node(self, state: MainSupervisorState):
        """
        팀 실행 노드 (TODO 기반)

        기능:
        1. current_todo_id로 실행할 TODO 가져오기
        2. TODO 상태 업데이트: PENDING → IN_PROGRESS
        3. 해당 Agent 실행
        4. TODO 상태 업데이트: IN_PROGRESS → COMPLETED/FAILED
        """
        from app.service_agent.foundation.todo_types import SupervisorTodo, TodoStatus

        current_todo_id = state["planning_state"]["current_todo_id"]

        # TODO 가져오기
        todos = [SupervisorTodo.from_dict(t) for t in state["planning_state"]["todos"]]
        current_todo = next((t for t in todos if t.id == current_todo_id), None)

        if not current_todo:
            logger.error(f"TODO {current_todo_id} not found")
            return state

        # 🔥 TODO 상태 업데이트: PENDING → IN_PROGRESS
        current_todo.start()
        self._update_todo_in_state(state, current_todo)

        logger.info(f"[TODO {current_todo.id}] Starting: {current_todo.name}")

        try:
            # Agent 실행
            team_name = self._get_team_for_agent(current_todo.agent_name)
            result = await self._execute_team(team_name, state)

            # 결과 저장
            state[f"{team_name}_state"] = result

            # 🔥 TODO 상태 업데이트: IN_PROGRESS → COMPLETED
            current_todo.complete()
            state["planning_state"]["completed_todo_ids"].append(current_todo.id)
            self._update_todo_in_state(state, current_todo)

            logger.info(f"[TODO {current_todo.id}] Completed in {current_todo.duration:.2f}s")

        except Exception as e:
            logger.error(f"[TODO {current_todo.id}] Failed: {e}")

            # 🔥 에러 처리
            if current_todo.should_retry():
                # 재시도
                current_todo.retry()
                logger.info(f"[TODO {current_todo.id}] Retrying ({current_todo.retry_count}/{current_todo.max_retries})")
                self._update_todo_in_state(state, current_todo)
            else:
                # 실패 처리
                current_todo.fail(str(e))
                state["planning_state"]["failed_todo_ids"].append(current_todo.id)
                self._update_todo_in_state(state, current_todo)

                # Optional이면 스킵, 아니면 중단
                if current_todo.metadata.get("optional", False):
                    logger.warning(f"[TODO {current_todo.id}] Failed but optional, skipping")
                    current_todo.skip(f"Failed but optional: {e}")
                    state["planning_state"]["skipped_todo_ids"].append(current_todo.id)
                else:
                    logger.error(f"[TODO {current_todo.id}] Failed and required, stopping")
                    raise

        # 다음 승인으로
        state["approval_status"] = "waiting"

        return state

    def _update_todo_in_state(self, state: MainSupervisorState, todo: SupervisorTodo):
        """State의 TODO 업데이트"""
        for i, t_dict in enumerate(state["planning_state"]["todos"]):
            if t_dict["id"] == todo.id:
                state["planning_state"]["todos"][i] = todo.to_dict()
                break
```

### 3.2 Planning 노드 수정 (TODO 생성)

**파일**: `backend/app/service_agent/supervisor/team_supervisor.py` (수정)

```python
async def planning_node(self, state: MainSupervisorState):
    """
    계획 수립 노드 (TODO 생성 포함)
    """
    from app.service_agent.cognitive_agents.plan_converter import ExecutionPlanConverter

    logger.info("[TeamSupervisor] Planning phase")

    state["current_phase"] = "planning"

    # 의도 분석
    query = state.get("query", "")
    intent_result = await self.planning_agent.analyze_intent(query)

    # 실행 계획 생성
    execution_plan = await self.planning_agent.create_execution_plan(intent_result)

    # 🔥 ExecutionPlan → SupervisorTodo 변환
    todos, strategy = ExecutionPlanConverter.convert_with_strategy(execution_plan)

    # PlanningState 생성
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

        # 🔥 TODO 리스트 저장
        todos=[todo.to_dict() for todo in todos],
        completed_todo_ids=[],
        failed_todo_ids=[],
        skipped_todo_ids=[],
        current_todo_id=None,

        # 기존 필드 (호환성)
        execution_steps=[
            {
                "step_id": f"step_{i}",
                "agent_name": todo.agent_name,
                "team": self._get_team_for_agent(todo.agent_name),
                "priority": todo.priority.value,
                "dependencies": todo.dependencies,
            }
            for i, todo in enumerate(todos)
        ],
        execution_strategy=strategy,
        parallel_groups=execution_plan.parallel_groups,
        plan_validated=True,
        validation_errors=[],
        estimated_total_time=execution_plan.estimated_time
    )

    state["planning_state"] = planning_state

    logger.info(f"[TeamSupervisor] Plan created: {len(todos)} TODOs")
    for todo in todos:
        logger.debug(f"  TODO {todo.id}: {todo.name} (deps: {todo.dependencies})")

    return state
```

---

## 📦 Phase 4: Command Interface 구현

### 목표
사용자가 명령어로 TODO 조회·수정할 수 있는 인터페이스 구현

### 4.1 CommandHandler 구현

**파일**: `backend/app/service_agent/supervisor/command_handler.py` (신규)

```python
"""
사용자 명령어 처리 핸들러
LangGraph의 Checkpointer와 통합하여 실시간 조회·수정 지원
"""

import logging
from typing import Dict, Any, Optional
from app.service_agent.foundation.todo_types import SupervisorTodo, TodoStatus

logger = logging.getLogger(__name__)


class CommandHandler:
    """
    사용자 명령어 처리

    지원 명령어:
    - /todos: TODO 목록 조회
    - /todo approve: 다음 TODO 승인
    - /todo skip <id>: TODO 건너뛰기
    - /todo add <agent_name>: 새 TODO 추가
    - /todo update <id> <status>: TODO 상태 변경
    - /checkpoint list: checkpoint 목록 조회
    - /checkpoint restore <id>: checkpoint 복원
    """

    def __init__(self, app, checkpointer):
        """
        Args:
            app: LangGraph 앱 (CompiledGraph)
            checkpointer: AsyncSqliteSaver 인스턴스
        """
        self.app = app
        self.checkpointer = checkpointer

    async def handle_command(
        self,
        command: str,
        thread_id: str
    ) -> Dict[str, Any]:
        """
        명령어 처리

        Args:
            command: 사용자 명령어
            thread_id: 세션 ID

        Returns:
            실행 결과
        """
        parts = command.strip().split()

        if not parts:
            return {"error": "Empty command"}

        cmd = parts[0]

        # /todos: TODO 목록 조회
        if cmd == "/todos":
            return await self._list_todos(thread_id)

        # /todo approve: 승인
        elif cmd == "/todo" and len(parts) > 1 and parts[1] == "approve":
            return await self._approve_next_todo(thread_id)

        # /todo skip <id>: 건너뛰기
        elif cmd == "/todo" and len(parts) > 2 and parts[1] == "skip":
            todo_id = parts[2]
            reason = " ".join(parts[3:]) if len(parts) > 3 else "User skipped"
            return await self._skip_todo(thread_id, todo_id, reason)

        # /todo add <agent_name>: TODO 추가
        elif cmd == "/todo" and len(parts) > 2 and parts[1] == "add":
            agent_name = parts[2]
            return await self._add_todo(thread_id, agent_name)

        # /todo update <id> <status>: 상태 변경
        elif cmd == "/todo" and len(parts) > 3 and parts[1] == "update":
            todo_id = parts[2]
            status = parts[3]
            return await self._update_todo_status(thread_id, todo_id, status)

        # /checkpoint list: checkpoint 목록
        elif cmd == "/checkpoint" and len(parts) > 1 and parts[1] == "list":
            return await self._list_checkpoints(thread_id)

        # /checkpoint restore <id>: checkpoint 복원
        elif cmd == "/checkpoint" and len(parts) > 2 and parts[1] == "restore":
            checkpoint_id = parts[2]
            return await self._restore_checkpoint(thread_id, checkpoint_id)

        else:
            return {
                "error": "Unknown command",
                "help": self._get_help()
            }

    async def _list_todos(self, thread_id: str) -> Dict[str, Any]:
        """
        TODO 목록 조회

        Returns:
            {
                "todos": [...],
                "summary": {...},
                "current_todo_id": "todo_002"
            }
        """
        config = {"configurable": {"thread_id": thread_id}}

        # 현재 State 가져오기
        state_snapshot = await self.app.aget_state(config)

        if not state_snapshot.values:
            return {"error": "No state found"}

        planning_state = state_snapshot.values.get("planning_state", {})
        todos = planning_state.get("todos", [])
        completed_ids = planning_state.get("completed_todo_ids", [])
        failed_ids = planning_state.get("failed_todo_ids", [])
        skipped_ids = planning_state.get("skipped_todo_ids", [])
        current_todo_id = planning_state.get("current_todo_id")

        # 요약 생성
        summary = {
            "total": len(todos),
            "pending": sum(1 for t in todos if t["status"] == "pending"),
            "in_progress": sum(1 for t in todos if t["status"] == "in_progress"),
            "completed": len(completed_ids),
            "failed": len(failed_ids),
            "skipped": len(skipped_ids)
        }

        return {
            "todos": todos,
            "summary": summary,
            "current_todo_id": current_todo_id,
            "checkpoint_id": state_snapshot.config["configurable"].get("checkpoint_id")
        }

    async def _approve_next_todo(self, thread_id: str) -> Dict[str, Any]:
        """
        다음 TODO 승인 (실행 재개)

        Returns:
            {
                "status": "resumed",
                "todo_id": "todo_002"
            }
        """
        config = {"configurable": {"thread_id": thread_id}}

        # 현재 State 가져오기
        state_snapshot = await self.app.aget_state(config)

        # approval_status를 "approved"로 변경
        state_snapshot.values["approval_status"] = "approved"

        # State 업데이트
        await self.app.aupdate_state(config, state_snapshot.values)

        # 🔥 실행 재개
        result = await self.app.ainvoke(None, config=config)

        current_todo_id = state_snapshot.values["planning_state"].get("current_todo_id")

        return {
            "status": "resumed",
            "todo_id": current_todo_id,
            "message": f"TODO {current_todo_id} 실행이 승인되었습니다."
        }

    async def _skip_todo(
        self,
        thread_id: str,
        todo_id: str,
        reason: str
    ) -> Dict[str, Any]:
        """
        TODO 건너뛰기

        Returns:
            {
                "status": "skipped",
                "todo_id": "todo_002"
            }
        """
        config = {"configurable": {"thread_id": thread_id}}

        # State 가져오기
        state_snapshot = await self.app.aget_state(config)

        # TODO 찾기
        todos = state_snapshot.values["planning_state"]["todos"]
        todo_dict = next((t for t in todos if t["id"] == todo_id), None)

        if not todo_dict:
            return {"error": f"TODO {todo_id} not found"}

        # TODO 객체로 변환
        todo = SupervisorTodo.from_dict(todo_dict)

        # 건너뛰기
        todo.skip(reason)

        # State 업데이트
        for i, t in enumerate(todos):
            if t["id"] == todo_id:
                todos[i] = todo.to_dict()
                break

        # skipped_todo_ids에 추가
        state_snapshot.values["planning_state"]["skipped_todo_ids"].append(todo_id)

        # State 저장
        await self.app.aupdate_state(config, state_snapshot.values)

        return {
            "status": "skipped",
            "todo_id": todo_id,
            "message": f"TODO {todo_id}가 건너뛰어졌습니다. ({reason})"
        }

    async def _add_todo(
        self,
        thread_id: str,
        agent_name: str
    ) -> Dict[str, Any]:
        """
        새 TODO 추가

        Returns:
            {
                "status": "added",
                "todo": {...}
            }
        """
        config = {"configurable": {"thread_id": thread_id}}

        # State 가져오기
        state_snapshot = await self.app.aget_state(config)

        todos = state_snapshot.values["planning_state"]["todos"]

        # 새 TODO 생성
        new_todo = SupervisorTodo(
            id=f"todo_{len(todos)+1:03d}",
            name=f"{agent_name} 추가 실행",
            description=f"사용자가 추가한 {agent_name} 실행 작업",
            agent_name=agent_name,
            status=TodoStatus.PENDING,
            dependencies=[],  # 사용자가 추가 지정 가능
            metadata={"added_by": "user", "manual": True}
        )

        # TODO 리스트에 추가
        todos.append(new_todo.to_dict())

        # State 저장
        await self.app.aupdate_state(config, state_snapshot.values)

        return {
            "status": "added",
            "todo": new_todo.to_dict(),
            "message": f"새 TODO {new_todo.id}가 추가되었습니다."
        }

    async def _update_todo_status(
        self,
        thread_id: str,
        todo_id: str,
        status: str
    ) -> Dict[str, Any]:
        """
        TODO 상태 변경

        Returns:
            {
                "status": "updated",
                "todo_id": "todo_002",
                "new_status": "completed"
            }
        """
        config = {"configurable": {"thread_id": thread_id}}

        # State 가져오기
        state_snapshot = await self.app.aget_state(config)

        # TODO 찾기
        todos = state_snapshot.values["planning_state"]["todos"]
        todo_dict = next((t for t in todos if t["id"] == todo_id), None)

        if not todo_dict:
            return {"error": f"TODO {todo_id} not found"}

        # 상태 변경
        try:
            new_status = TodoStatus(status)
        except ValueError:
            return {"error": f"Invalid status: {status}"}

        # TODO 객체로 변환
        todo = SupervisorTodo.from_dict(todo_dict)

        # 상태 업데이트
        if new_status == TodoStatus.COMPLETED:
            todo.complete()
        elif new_status == TodoStatus.FAILED:
            todo.fail("User marked as failed")
        elif new_status == TodoStatus.SKIPPED:
            todo.skip("User skipped")
        else:
            todo.status = new_status

        # State 업데이트
        for i, t in enumerate(todos):
            if t["id"] == todo_id:
                todos[i] = todo.to_dict()
                break

        # State 저장
        await self.app.aupdate_state(config, state_snapshot.values)

        return {
            "status": "updated",
            "todo_id": todo_id,
            "new_status": new_status.value,
            "message": f"TODO {todo_id} 상태가 {new_status.value}로 변경되었습니다."
        }

    async def _list_checkpoints(self, thread_id: str) -> Dict[str, Any]:
        """
        Checkpoint 목록 조회

        Returns:
            {
                "checkpoints": [
                    {
                        "checkpoint_id": "...",
                        "timestamp": "...",
                        "node": "approval",
                        "todos_completed": 2
                    },
                    ...
                ]
            }
        """
        config = {"configurable": {"thread_id": thread_id}}

        # Checkpoint 히스토리 가져오기
        history = self.app.aget_state_history(config)

        checkpoints = []
        async for state_snapshot in history:
            checkpoint_info = {
                "checkpoint_id": state_snapshot.config["configurable"].get("checkpoint_id"),
                "timestamp": state_snapshot.metadata.get("created_at"),
                "node": state_snapshot.metadata.get("source"),
                "todos_completed": len(
                    state_snapshot.values.get("planning_state", {}).get("completed_todo_ids", [])
                )
            }
            checkpoints.append(checkpoint_info)

        return {"checkpoints": checkpoints}

    async def _restore_checkpoint(
        self,
        thread_id: str,
        checkpoint_id: str
    ) -> Dict[str, Any]:
        """
        특정 Checkpoint로 복원

        Returns:
            {
                "status": "restored",
                "checkpoint_id": "..."
            }
        """
        config = {
            "configurable": {
                "thread_id": thread_id,
                "checkpoint_id": checkpoint_id
            }
        }

        # 해당 checkpoint에서 재개
        result = await self.app.ainvoke(None, config=config)

        return {
            "status": "restored",
            "checkpoint_id": checkpoint_id,
            "message": f"Checkpoint {checkpoint_id}로 복원되었습니다."
        }

    def _get_help(self) -> str:
        """명령어 도움말"""
        return """
사용 가능한 명령어:

📋 TODO 관리:
  /todos                      - TODO 목록 조회
  /todo approve               - 다음 TODO 승인 (실행 재개)
  /todo skip <id>             - TODO 건너뛰기
  /todo add <agent_name>      - 새 TODO 추가
  /todo update <id> <status>  - TODO 상태 변경

💾 Checkpoint 관리:
  /checkpoint list            - Checkpoint 목록 조회
  /checkpoint restore <id>    - 특정 Checkpoint로 복원
"""
```

---

## 📦 Phase 5: 사용 시나리오

### 시나리오 1: 정상 실행 (사용자 승인)

```
[사용자]
쿼리: "집주인이 전세금 3억을 10억으로 올려달래. 법적으로 해결방법 알려줘"

[시스템]
1. PlanningAgent: Intent 분석 → COMPREHENSIVE
2. ExecutionPlan 생성:
   - search_team (priority=1)
   - analysis_team (priority=2, deps=[search_team])

3. TODO 변환:
   - todo_001: search_team (PENDING)
   - todo_002: analysis_team (PENDING, deps=[todo_001])

4. State 저장 (Checkpointer)

5. [INTERRUPT] Approval 노드:
   "📋 다음 작업을 실행하시겠습니까?
    - TODO ID: todo_001
    - 작업명: search_team 실행
    - Agent: search_team"

[사용자]
/todos

[시스템 응답]
{
  "summary": {
    "total": 2,
    "pending": 2,
    "completed": 0
  },
  "todos": [
    {"id": "todo_001", "name": "search_team 실행", "status": "pending"},
    {"id": "todo_002", "name": "analysis_team 실행", "status": "pending", "dependencies": ["todo_001"]}
  ],
  "current_todo_id": "todo_001"
}

[사용자]
/todo approve

[시스템]
6. todo_001 실행:
   - 상태: PENDING → IN_PROGRESS → COMPLETED
   - 검색 결과 수집
   - State 저장 (Checkpointer)

7. [INTERRUPT] Approval 노드:
   "📋 다음 작업을 실행하시겠습니까?
    - TODO ID: todo_002
    - 작업명: analysis_team 실행
    - Agent: analysis_team"

[사용자]
/todos

[시스템 응답]
{
  "summary": {
    "total": 2,
    "pending": 1,
    "completed": 1
  },
  "todos": [
    {"id": "todo_001", "status": "completed", "duration": 8.5},
    {"id": "todo_002", "status": "pending", "dependencies": ["todo_001"]}  ← 실행 가능
  ],
  "current_todo_id": "todo_002"
}

[사용자]
/todo approve

[시스템]
8. todo_002 실행:
   - 전세금 인상률 분석 (233.3%)
   - 법정 한도 초과 판정
   - State 저장

9. 모든 TODO 완료
10. 최종 응답 생성
```

---

### 시나리오 2: 사용자 계획 수정

```
[사용자]
쿼리: "강남구 아파트 시세 조회"

[시스템]
1. TODO 생성:
   - todo_001: search_team (PENDING)

2. [INTERRUPT] Approval 노드

[사용자]
/todos

[시스템]
{
  "todos": [
    {"id": "todo_001", "name": "search_team 실행", "status": "pending"}
  ]
}

[사용자]
검색만으로 부족할 것 같아. 분석도 추가해줘.
/todo add analysis_team

[시스템]
{
  "status": "added",
  "todo": {
    "id": "todo_002",
    "name": "analysis_team 추가 실행",
    "agent_name": "analysis_team",
    "status": "pending"
  }
}

[사용자]
/todo approve

[시스템]
3. todo_001 실행 (search_team)
4. [INTERRUPT] Approval 노드

[사용자]
/todo approve

[시스템]
5. todo_002 실행 (analysis_team)
6. 최종 응답
```

---

### 시나리오 3: Checkpoint 복원

```
[상황]
search_team 완료 후 시스템 크래시 발생

[사용자]
시스템 재시작 후...
/checkpoint list

[시스템]
{
  "checkpoints": [
    {
      "checkpoint_id": "cp_001",
      "timestamp": "2025-10-05 10:00:00",
      "node": "planning",
      "todos_completed": 0
    },
    {
      "checkpoint_id": "cp_002",
      "timestamp": "2025-10-05 10:00:15",
      "node": "approval",
      "todos_completed": 0
    },
    {
      "checkpoint_id": "cp_003",
      "timestamp": "2025-10-05 10:00:30",
      "node": "execute_teams",
      "todos_completed": 1  ← search_team 완료
    },
    {
      "checkpoint_id": "cp_004",
      "timestamp": "2025-10-05 10:00:35",
      "node": "approval",
      "todos_completed": 1
    }
  ]
}

[사용자]
/checkpoint restore cp_004

[시스템]
1. cp_004 시점으로 복원:
   - todos: [todo_001 (완료), todo_002 (대기)]
   - current_todo_id: "todo_002"

2. [INTERRUPT] Approval 노드:
   "📋 다음 작업을 실행하시겠습니까?
    - TODO ID: todo_002
    - 작업명: analysis_team 실행"

[사용자]
/todo approve

[시스템]
3. todo_002 실행 (analysis_team)
4. 정상 완료

결과: 크래시 시점부터 정확히 복원됨!
```

---

## 📁 파일 구조

```
backend/app/service_agent/
├── foundation/
│   ├── checkpointer.py              # 🔥 신규: AsyncSqliteSaver 관리
│   ├── todo_types.py                 # 🔥 신규: TODO 타입 정의
│   ├── separated_states.py           # 수정: todos 필드 추가
│   └── context.py                    # 기존
│
├── cognitive_agents/
│   ├── planning_agent.py             # 기존
│   ├── query_decomposer.py           # 기존
│   └── plan_converter.py             # 🔥 신규: ExecutionPlan → TODO 변환
│
├── supervisor/
│   ├── team_supervisor.py            # 수정: Checkpointer, Interrupt, Approval
│   └── command_handler.py            # 🔥 신규: 사용자 명령어 처리
│
├── execution_agents/
│   ├── analysis_executor.py          # 수정: Checkpointer 적용
│   ├── search_executor.py            # 수정: Checkpointer 적용
│   └── document_executor.py          # 수정: Checkpointer 적용
│
├── checkpoints/
│   └── service_agent.db              # 🔥 SQLite checkpoint DB
│
└── reports/
    └── plan_of_dynamic_execution_control_system.md  # 본 문서
```

---

## 🎯 기대 효과

### 1. 사용자 경험
- ✅ **실시간 조회**: `/todos` 명령어로 언제든 진행 상황 확인
- ✅ **계획 수정**: 실행 중 TODO 추가/삭제/건너뛰기 가능
- ✅ **단계별 승인**: 각 Agent 실행 전 승인 요청
- ✅ **시점 복원**: 특정 checkpoint로 롤백 후 재실행

### 2. 시스템 안정성
- ✅ **크래시 복구**: Checkpointer로 중단 시점에서 재개
- ✅ **에러 처리**: 실패 시 재시도 또는 스킵 선택
- ✅ **의존성 관리**: 자동으로 실행 순서 보장
- ✅ **상태 추적**: 모든 TODO 상태 변화 SQLite에 기록

### 3. 개발자 편의성
- ✅ **디버깅**: Checkpoint 목록으로 실행 흐름 추적
- ✅ **테스트**: 특정 단계부터 실행 가능
- ✅ **모니터링**: TODO 상태로 진행률 파악
- ✅ **확장성**: 새로운 Agent 추가 시 TODO만 추가하면 됨

---

## 🚀 향후 확장 가능성

### Phase 6: LLM 기반 동적 계획 조정
- 실행 결과를 보고 LLM이 TODO 추가/수정
- 예: "검색 결과 부족" → LLM이 `additional_search` TODO 추가

### Phase 7: TODO 우선순위 동적 조정
- 사용자 피드백 기반 우선순위 재조정
- 예: 중요한 TODO를 HIGH로 변경

### Phase 8: Parallel Execution 지원
- 의존성 없는 TODO 동시 실행
- 예: search_team과 document_team 병렬 실행

### Phase 9: Web UI 통합
- 웹 인터페이스로 TODO 시각화
- 드래그&드롭으로 순서 변경

### Phase 10: TODO 템플릿
- 자주 사용하는 패턴을 템플릿으로 저장
- 예: "부동산 종합 분석" 템플릿

---

## 📚 참고 자료

- [LangGraph Checkpointer 문서](https://langchain-ai.github.io/langgraph/how-tos/persistence/)
- [LangGraph Interrupt 문서](https://langchain-ai.github.io/langgraph/how-tos/human_in_the_loop/)
- [AsyncSqliteSaver API](https://langchain-ai.github.io/langgraph/reference/checkpoints/)

---

**작성 완료일**: 2025-10-05
**다음 단계**: 구현 시작 (Phase 1: Checkpointer 통합부터)
