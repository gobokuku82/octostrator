"""Plan Models - 계획 관리 및 버전 관리 모델

이 파일은 states/plan.py에서 models/로 이동됨.
Pydantic 모델만 포함하며, workflow_manager 의존성 제거.

NOTE: get_ready_todos()는 단순히 pending 상태만 반환.
      의존성 기반 필터링은 workflow_manager.todo_manager에서 처리.
"""

from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field
from datetime import datetime
import uuid

from .todo import TodoItem


# ============================================================
# Plan Change Models
# ============================================================

class PlanChange(BaseModel):
    """계획 변경 이력"""

    change_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.now)
    change_type: Literal[
        "create", "add_todo", "remove_todo", "modify_todo",
        "reorder", "replan", "rollback", "user_decision"
    ]
    reason: str  # 변경 이유
    actor: str = "system"  # "system", "user", "hitl_manager"

    # 변경 상세
    affected_todo_ids: List[str] = Field(default_factory=list)
    change_data: Dict[str, Any] = Field(default_factory=dict)

    # 의사결정 기록 (Interrupt Type 1)
    decision_request_id: Optional[str] = None
    decision_action: Optional[str] = None
    decision_data: Optional[Dict[str, Any]] = None

    # 재계획 기록 (Interrupt Type 2)
    user_instruction: Optional[str] = None
    replan_summary: Optional[str] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# ============================================================
# Plan Version Models
# ============================================================

class PlanVersion(BaseModel):
    """계획 버전"""

    version: int
    timestamp: datetime = Field(default_factory=datetime.now)
    todos: List[TodoItem]  # 이 버전의 todos 스냅샷
    change_id: str  # 이 버전을 만든 변경 ID
    change_summary: str  # 변경 요약

    # 메타데이터
    total_todos: int = 0
    ml_todos: int = 0
    biz_todos: int = 0
    estimated_duration_sec: int = 0

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# ============================================================
# Plan Model
# ============================================================

class Plan(BaseModel):
    """
    계획 관리 모델

    - 동적 수정 가능
    - 버전 관리
    - 변경 이력 추적
    - HITL 통합
    """

    # 기본 정보
    plan_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str

    # 현재 상태
    current_version: int = 1
    status: Literal[
        "draft",        # 초안 (계획 수립 중)
        "approved",     # 승인됨 (사용자 승인)
        "executing",    # 실행 중
        "paused",       # 일시중지 (Interrupt Type 2)
        "waiting",      # 대기 중 (Interrupt Type 1 - 사용자 결정 대기)
        "completed",    # 완료
        "failed",       # 실패
        "cancelled"     # 취소
    ] = "draft"

    # Todos (현재 버전)
    todos: List[TodoItem] = Field(default_factory=list)

    # 버전 히스토리
    versions: List[PlanVersion] = Field(default_factory=list)

    # 변경 히스토리
    changes: List[PlanChange] = Field(default_factory=list)

    # 계획 메타데이터
    intent: Dict[str, Any] = Field(default_factory=dict)  # Cognitive layer 결과
    context: Dict[str, Any] = Field(default_factory=dict)  # 추가 컨텍스트

    # 실행 통계
    total_todos: int = 0
    completed_todos: int = 0
    failed_todos: int = 0

    # 타임스탬프
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    approved_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # HITL 관련
    current_interrupt_type: Optional[Literal["auto", "manual"]] = None
    pending_decision_request_id: Optional[str] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

    def get_current_version(self) -> Optional[PlanVersion]:
        """현재 버전 반환"""
        if not self.versions:
            return None
        return next(
            (v for v in self.versions if v.version == self.current_version),
            None
        )

    def get_version(self, version: int) -> Optional[PlanVersion]:
        """특정 버전 반환"""
        return next(
            (v for v in self.versions if v.version == version),
            None
        )

    def get_change(self, change_id: str) -> Optional[PlanChange]:
        """특정 변경 이력 반환"""
        return next(
            (c for c in self.changes if c.change_id == change_id),
            None
        )

    def get_recent_changes(self, limit: int = 10) -> List[PlanChange]:
        """최근 변경 이력 반환 (최신순)"""
        return sorted(self.changes, key=lambda c: c.timestamp, reverse=True)[:limit]

    def update_statistics(self):
        """통계 업데이트"""
        self.total_todos = len(self.todos)
        self.completed_todos = len([t for t in self.todos if t.status == "completed"])
        self.failed_todos = len([t for t in self.todos if t.status == "failed"])
        self.updated_at = datetime.now()

    # ============================================================
    # Todo Accessor Methods
    # ============================================================

    def get_todos(self) -> List[TodoItem]:
        """모든 todos 반환"""
        return self.todos

    def get_todo_by_id(self, todo_id: str) -> Optional[TodoItem]:
        """ID로 todo 조회"""
        for todo in self.todos:
            if todo.id == todo_id:
                return todo
        return None

    def get_todos_by_status(self, status: str) -> List[TodoItem]:
        """상태별 todos 조회"""
        return [todo for todo in self.todos if todo.status == status]

    def get_ready_todos(self) -> List[TodoItem]:
        """
        실행 가능한 todos 반환 (pending 상태)

        NOTE: 의존성 기반 필터링은 workflow_manager.todo_manager.TodoDependencyManager에서 처리.
              이 메서드는 단순히 pending 상태만 반환합니다.
        """
        return self.get_todos_by_status("pending")

    def get_completed_todos(self) -> List[TodoItem]:
        """완료된 todos"""
        return self.get_todos_by_status("completed")

    def get_failed_todos(self) -> List[TodoItem]:
        """실패한 todos"""
        return self.get_todos_by_status("failed")

    def get_pending_todos(self) -> List[TodoItem]:
        """대기중인 todos"""
        return self.get_todos_by_status("pending")

    def get_in_progress_todos(self) -> List[TodoItem]:
        """진행중인 todos"""
        return self.get_todos_by_status("in_progress")

    def get_todos_by_layer(self, layer: str) -> List[TodoItem]:
        """레이어별 todos"""
        return [todo for todo in self.todos if todo.layer == layer]

    def get_todo_statistics(self) -> Dict[str, int]:
        """
        Todo 통계 반환

        Returns:
            Dict with status counts and total
        """
        stats = {
            "pending": 0,
            "in_progress": 0,
            "completed": 0,
            "failed": 0,
            "blocked": 0,
            "skipped": 0,
            "needs_approval": 0,
            "cancelled": 0,
        }
        for todo in self.todos:
            status_key = str(todo.status.value) if hasattr(todo.status, 'value') else str(todo.status)
            if status_key in stats:
                stats[status_key] += 1
        stats["total"] = len(self.todos)
        stats["ml_todos"] = len(self.get_todos_by_layer("ml_execution"))
        stats["biz_todos"] = len(self.get_todos_by_layer("biz_execution"))
        return stats

    def get_progress_percentage(self) -> float:
        """
        완료 진행률 반환 (0.0 ~ 100.0)

        Returns:
            Progress percentage (completed / total * 100)
        """
        if not self.todos:
            return 0.0
        completed = len(self.get_completed_todos())
        return (completed / len(self.todos)) * 100.0


# ============================================================
# Helper Functions
# ============================================================

def create_plan(
    session_id: str,
    todos: List[TodoItem],
    intent: Dict[str, Any],
    context: Optional[Dict[str, Any]] = None
) -> Plan:
    """
    새 계획 생성

    Args:
        session_id: 세션 ID
        todos: 초기 todos
        intent: Cognitive layer 결과
        context: 추가 컨텍스트

    Returns:
        Plan 인스턴스
    """
    plan = Plan(
        session_id=session_id,
        todos=todos,
        intent=intent,
        context=context or {},
        status="draft"
    )

    # 초기 버전 생성
    initial_change = PlanChange(
        change_type="create",
        reason="Initial plan creation",
        actor="system",
        affected_todo_ids=[t.id for t in todos]
    )

    initial_version = PlanVersion(
        version=1,
        todos=todos.copy(),
        change_id=initial_change.change_id,
        change_summary="Initial plan created",
        total_todos=len(todos),
        ml_todos=len([t for t in todos if t.layer == "ml_execution"]),
        biz_todos=len([t for t in todos if t.layer == "biz_execution"])
    )

    plan.changes.append(initial_change)
    plan.versions.append(initial_version)
    plan.update_statistics()

    return plan


def create_plan_change(
    change_type: Literal[
        "create", "add_todo", "remove_todo", "modify_todo",
        "reorder", "replan", "rollback", "user_decision"
    ],
    reason: str,
    actor: str = "system",
    affected_todo_ids: Optional[List[str]] = None,
    change_data: Optional[Dict[str, Any]] = None,
    # Interrupt Type 1
    decision_request_id: Optional[str] = None,
    decision_action: Optional[str] = None,
    decision_data: Optional[Dict[str, Any]] = None,
    # Interrupt Type 2
    user_instruction: Optional[str] = None,
    replan_summary: Optional[str] = None
) -> PlanChange:
    """
    계획 변경 생성 헬퍼

    Args:
        change_type: 변경 타입
        reason: 변경 이유
        actor: 변경 주체
        affected_todo_ids: 영향받은 todo IDs
        change_data: 변경 상세 데이터
        decision_request_id: 의사결정 요청 ID (Type 1)
        decision_action: 의사결정 액션 (Type 1)
        decision_data: 의사결정 데이터 (Type 1)
        user_instruction: 사용자 지시 (Type 2)
        replan_summary: 재계획 요약 (Type 2)

    Returns:
        PlanChange 인스턴스
    """
    return PlanChange(
        change_type=change_type,
        reason=reason,
        actor=actor,
        affected_todo_ids=affected_todo_ids or [],
        change_data=change_data or {},
        decision_request_id=decision_request_id,
        decision_action=decision_action,
        decision_data=decision_data,
        user_instruction=user_instruction,
        replan_summary=replan_summary
    )


def create_plan_version(
    version: int,
    todos: List[TodoItem],
    change: PlanChange,
    change_summary: str
) -> PlanVersion:
    """
    계획 버전 생성 헬퍼

    Args:
        version: 버전 번호
        todos: 이 버전의 todos
        change: 이 버전을 만든 변경
        change_summary: 변경 요약

    Returns:
        PlanVersion 인스턴스
    """
    # 통계 계산
    ml_todos = len([t for t in todos if t.layer == "ml_execution"])
    biz_todos = len([t for t in todos if t.layer == "biz_execution"])

    # 예상 실행 시간 계산 (간단한 추정)
    estimated_duration = sum(
        t.metadata.execution.timeout or 60
        for t in todos
        if t.status in ["pending", "blocked"]
    )

    return PlanVersion(
        version=version,
        timestamp=datetime.now(),
        todos=todos.copy(),
        change_id=change.change_id,
        change_summary=change_summary,
        total_todos=len(todos),
        ml_todos=ml_todos,
        biz_todos=biz_todos,
        estimated_duration_sec=estimated_duration
    )
