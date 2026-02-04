"""
State-Plan Todo 동기화 관리자 (P0-2.1, P0-2.2)

문제:
- state["todos"]와 plan_obj.todos가 독립적으로 관리됨
- ML/Biz 실행 후 state["todos"]만 업데이트
- HITL에서 plan_obj.todos만 수정

해결:
- 양방향 동기화 함수 제공
- SyncManager 클래스로 통합 관리
"""

from typing import Dict, List, Optional, Tuple, Any, TYPE_CHECKING
from enum import Enum
from datetime import datetime
import logging

if TYPE_CHECKING:
    from ...states.base import AgentState
    from ...models.plan import Plan
    from ...models.todo import TodoItem

logger = logging.getLogger(__name__)


# ============================================================
# Enums
# ============================================================

class SyncDirection(Enum):
    """동기화 방향"""
    STATE_TO_PLAN = "state_to_plan"
    PLAN_TO_STATE = "plan_to_state"
    BIDIRECTIONAL = "bidirectional"


class SyncTrigger(Enum):
    """동기화 트리거 이벤트"""
    TODO_STATUS_CHANGE = "todo_status_change"
    PLAN_MODIFICATION = "plan_modification"
    HITL_REPLAN = "hitl_replan"
    MANUAL = "manual"


# ============================================================
# SyncResult
# ============================================================

class SyncResult:
    """동기화 결과"""

    def __init__(self):
        self.synced: bool = False
        self.direction: Optional[SyncDirection] = None
        self.trigger: Optional[SyncTrigger] = None
        self.updated_ids: List[str] = []
        self.added_ids: List[str] = []
        self.removed_ids: List[str] = []
        self.conflicts: List[Dict[str, Any]] = []
        self.errors: List[str] = []
        self.timestamp: datetime = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리 변환"""
        return {
            "synced": self.synced,
            "direction": self.direction.value if self.direction else None,
            "trigger": self.trigger.value if self.trigger else None,
            "updated_ids": self.updated_ids,
            "added_ids": self.added_ids,
            "removed_ids": self.removed_ids,
            "conflicts": self.conflicts,
            "errors": self.errors,
            "timestamp": self.timestamp.isoformat(),
        }

    def __repr__(self) -> str:
        return (
            f"SyncResult(synced={self.synced}, "
            f"direction={self.direction}, "
            f"updated={len(self.updated_ids)}, "
            f"added={len(self.added_ids)}, "
            f"removed={len(self.removed_ids)}, "
            f"conflicts={len(self.conflicts)}, "
            f"errors={len(self.errors)})"
        )


# ============================================================
# SyncManager
# ============================================================

class SyncManager:
    """
    State-Plan 동기화 관리자

    역할:
    - state["todos"]와 plan_obj.todos 간 동기화
    - 양방향 동기화 지원
    - 충돌 감지 및 해결
    """

    # ============================================================
    # 비교 메서드
    # ============================================================

    @staticmethod
    def compare_todos(
        state_todos: List["TodoItem"],
        plan_todos: List["TodoItem"]
    ) -> Dict[str, Any]:
        """
        두 todo 목록 비교

        Args:
            state_todos: state["todos"]의 todo 목록
            plan_todos: plan_obj.todos의 todo 목록

        Returns:
            비교 결과 딕셔너리
        """
        state_map = {t.id: t for t in state_todos}
        plan_map = {t.id: t for t in plan_todos}

        state_ids = set(state_map.keys())
        plan_ids = set(plan_map.keys())

        # 공통 ID 중 내용이 다른 것 찾기
        different = []
        for tid in state_ids & plan_ids:
            if not SyncManager._todos_equal(state_map[tid], plan_map[tid]):
                different.append(tid)

        return {
            "in_sync": (
                state_ids == plan_ids and
                len(different) == 0
            ),
            "state_only": list(state_ids - plan_ids),
            "plan_only": list(plan_ids - state_ids),
            "different": different,
            "common": list(state_ids & plan_ids),
            "state_count": len(state_todos),
            "plan_count": len(plan_todos),
        }

    @staticmethod
    def _todos_equal(todo1: "TodoItem", todo2: "TodoItem") -> bool:
        """
        두 todo의 동등성 비교

        비교 대상:
        - status (상태)
        - task (내용)
        - layer (레이어)
        - error_message (에러 메시지)
        """
        return (
            todo1.status == todo2.status and
            todo1.task == todo2.task and
            todo1.layer == todo2.layer and
            getattr(todo1, 'error_message', None) == getattr(todo2, 'error_message', None)
        )

    @staticmethod
    def get_todo_diff(todo1: "TodoItem", todo2: "TodoItem") -> Dict[str, Any]:
        """
        두 todo의 차이점 반환

        Args:
            todo1: 첫 번째 todo
            todo2: 두 번째 todo

        Returns:
            차이점 딕셔너리
        """
        diff = {}

        if todo1.status != todo2.status:
            diff["status"] = {"from": str(todo1.status), "to": str(todo2.status)}
        if todo1.task != todo2.task:
            diff["task"] = {"from": todo1.task, "to": todo2.task}
        if todo1.layer != todo2.layer:
            diff["layer"] = {"from": todo1.layer, "to": todo2.layer}

        return diff

    # ============================================================
    # 동기화 메서드
    # ============================================================

    @staticmethod
    def sync_state_to_plan(
        state: "AgentState",
        trigger: SyncTrigger = SyncTrigger.MANUAL
    ) -> Tuple["AgentState", SyncResult]:
        """
        State의 todos를 Plan에 동기화

        사용처:
        - ML/Biz 실행 후 todo 상태 변경 시

        Args:
            state: 현재 AgentState
            trigger: 동기화 트리거

        Returns:
            (업데이트된 state, SyncResult)
        """
        result = SyncResult()
        result.direction = SyncDirection.STATE_TO_PLAN
        result.trigger = trigger

        plan_obj = state.get("plan_obj")
        if not plan_obj:
            result.errors.append("plan_obj not found in state")
            logger.warning("sync_state_to_plan: plan_obj not found")
            return state, result

        state_todos = state.get("todos", [])
        if not state_todos:
            result.errors.append("No todos in state to sync")
            return state, result

        # 변경 전 비교
        comparison = SyncManager.compare_todos(state_todos, plan_obj.todos)

        # Plan의 todos를 State 기준으로 업데이트
        plan_obj.todos = [t.model_copy(deep=True) for t in state_todos]
        plan_obj.current_version += 1
        plan_obj.updated_at = datetime.now()

        # 결과 기록
        result.synced = True
        result.updated_ids = comparison["different"]
        result.added_ids = comparison["state_only"]
        result.removed_ids = comparison["plan_only"]

        logger.info(
            f"sync_state_to_plan: synced {len(state_todos)} todos, "
            f"updated={len(result.updated_ids)}, "
            f"added={len(result.added_ids)}, "
            f"removed={len(result.removed_ids)}"
        )

        return state, result

    @staticmethod
    def sync_plan_to_state(
        state: "AgentState",
        trigger: SyncTrigger = SyncTrigger.MANUAL
    ) -> Tuple[Dict[str, Any], SyncResult]:
        """
        Plan의 todos를 State에 동기화

        사용처:
        - HITL에서 plan 수정 후

        Args:
            state: 현재 AgentState
            trigger: 동기화 트리거

        Returns:
            (state 업데이트용 딕셔너리, SyncResult)
        """
        result = SyncResult()
        result.direction = SyncDirection.PLAN_TO_STATE
        result.trigger = trigger

        plan_obj = state.get("plan_obj")
        if not plan_obj:
            result.errors.append("plan_obj not found in state")
            logger.warning("sync_plan_to_state: plan_obj not found")
            return {}, result

        state_todos = state.get("todos", [])

        # 변경 전 비교
        comparison = SyncManager.compare_todos(state_todos, plan_obj.todos)

        # State의 todos를 Plan 기준으로 업데이트
        new_todos = [t.model_copy(deep=True) for t in plan_obj.todos]

        # 결과 기록
        result.synced = True
        result.updated_ids = comparison["different"]
        result.added_ids = comparison["plan_only"]
        result.removed_ids = comparison["state_only"]

        logger.info(
            f"sync_plan_to_state: synced {len(new_todos)} todos, "
            f"updated={len(result.updated_ids)}, "
            f"added={len(result.added_ids)}, "
            f"removed={len(result.removed_ids)}"
        )

        return {"todos": new_todos}, result

    @staticmethod
    def sync_on_todo_update(
        state: "AgentState",
        updated_todos: List["TodoItem"],
        trigger: SyncTrigger = SyncTrigger.TODO_STATUS_CHANGE
    ) -> Tuple[Dict[str, Any], Optional["Plan"]]:
        """
        Todo 업데이트 후 양방향 동기화

        ML/Biz executor 노드에서 사용하는 핵심 메서드.
        updated_todos를 state와 plan_obj 모두에 동기화.

        사용 예시:
            updated_todos = update_todo_status(todos, todo_id, "completed")
            sync_update, _ = SyncManager.sync_on_todo_update(state, updated_todos)
            return {**state, **sync_update}

        Args:
            state: 현재 AgentState
            updated_todos: 업데이트된 todo 리스트
            trigger: 동기화 트리거

        Returns:
            (state 업데이트용 딕셔너리, 업데이트된 Plan 객체)
        """
        plan_obj = state.get("plan_obj")

        if plan_obj:
            # Plan 객체 업데이트
            plan_obj.todos = [t.model_copy(deep=True) for t in updated_todos]
            plan_obj.current_version += 1
            plan_obj.updated_at = datetime.now()
            plan_obj.update_statistics()

            logger.debug(
                f"sync_on_todo_update: synced {len(updated_todos)} todos to plan "
                f"(trigger={trigger.value})"
            )

        # State 업데이트용 딕셔너리 반환
        return {
            "todos": updated_todos,
            "plan_obj": plan_obj
        }, plan_obj

    # ============================================================
    # 검증 메서드
    # ============================================================

    @staticmethod
    def validate_sync(state: "AgentState") -> Dict[str, Any]:
        """
        동기화 상태 검증

        Args:
            state: 현재 AgentState

        Returns:
            검증 결과 딕셔너리
        """
        plan_obj = state.get("plan_obj")

        if not plan_obj:
            return {
                "synced": False,
                "has_plan": False,
                "issues": ["plan_obj not found in state"],
                "comparison": None
            }

        state_todos = state.get("todos", [])
        comparison = SyncManager.compare_todos(state_todos, plan_obj.todos)

        issues = []
        if comparison["state_only"]:
            issues.append(f"State에만 있는 todos: {comparison['state_only']}")
        if comparison["plan_only"]:
            issues.append(f"Plan에만 있는 todos: {comparison['plan_only']}")
        if comparison["different"]:
            issues.append(f"불일치 todos: {comparison['different']}")

        return {
            "synced": comparison["in_sync"],
            "has_plan": True,
            "issues": issues,
            "comparison": comparison,
            "state_count": len(state_todos),
            "plan_count": len(plan_obj.todos),
        }

    @staticmethod
    def auto_sync(state: "AgentState") -> Tuple[Dict[str, Any], SyncResult]:
        """
        자동 동기화

        동기화 상태를 확인하고 불일치 시 자동으로 동기화.
        기본 전략: State → Plan (State가 더 최신이라고 가정)

        Args:
            state: 현재 AgentState

        Returns:
            (state 업데이트용 딕셔너리, SyncResult)
        """
        validation = SyncManager.validate_sync(state)

        if validation["synced"]:
            result = SyncResult()
            result.synced = True
            return {}, result

        # State → Plan 동기화
        _, result = SyncManager.sync_state_to_plan(
            state,
            trigger=SyncTrigger.MANUAL
        )

        return {}, result

    # ============================================================
    # 충돌 해결
    # ============================================================

    @staticmethod
    def resolve_conflict(
        state: "AgentState",
        conflict_ids: List[str],
        prefer: SyncDirection = SyncDirection.STATE_TO_PLAN
    ) -> Tuple[Dict[str, Any], SyncResult]:
        """
        충돌 해결

        Args:
            state: 현재 AgentState
            conflict_ids: 충돌 todo IDs
            prefer: 우선 방향 (기본: State 우선)

        Returns:
            (state 업데이트용 딕셔너리, SyncResult)
        """
        result = SyncResult()
        result.direction = prefer

        plan_obj = state.get("plan_obj")
        if not plan_obj:
            result.errors.append("plan_obj not found")
            return {}, result

        state_todos = state.get("todos", [])
        state_map = {t.id: t for t in state_todos}
        plan_map = {t.id: t for t in plan_obj.todos}

        resolved_todos = []

        for tid in conflict_ids:
            if prefer == SyncDirection.STATE_TO_PLAN:
                # State 우선
                if tid in state_map:
                    resolved_todos.append(state_map[tid])
                    result.updated_ids.append(tid)
            else:
                # Plan 우선
                if tid in plan_map:
                    resolved_todos.append(plan_map[tid])
                    result.updated_ids.append(tid)

        result.synced = True
        result.conflicts = [{"id": tid, "resolved": prefer.value} for tid in conflict_ids]

        logger.info(f"resolve_conflict: resolved {len(conflict_ids)} conflicts using {prefer.value}")

        # 전체 동기화 수행
        if prefer == SyncDirection.STATE_TO_PLAN:
            return SyncManager.sync_state_to_plan(state, SyncTrigger.MANUAL)
        else:
            return SyncManager.sync_plan_to_state(state, SyncTrigger.MANUAL)


# ============================================================
# 편의 함수
# ============================================================

def sync_todos_on_update(
    state: "AgentState",
    updated_todos: List["TodoItem"]
) -> Dict[str, Any]:
    """
    Todo 업데이트 후 동기화 (간편 함수)

    Usage:
        updated_todos = update_todo_status(todos, todo_id, "completed")
        sync_update = sync_todos_on_update(state, updated_todos)
        return {**state, **sync_update}

    Args:
        state: 현재 AgentState
        updated_todos: 업데이트된 todo 리스트

    Returns:
        state 업데이트용 딕셔너리
    """
    update_dict, _ = SyncManager.sync_on_todo_update(state, updated_todos)
    return update_dict


def validate_state_plan_sync(state: "AgentState") -> bool:
    """
    동기화 상태 빠른 검증

    Args:
        state: 현재 AgentState

    Returns:
        동기화 여부 (True/False)
    """
    result = SyncManager.validate_sync(state)
    return result["synced"]


# ============================================================
# Singleton Instance
# ============================================================

# 글로벌 인스턴스 (선택적 사용)
sync_manager = SyncManager()


def get_sync_manager() -> SyncManager:
    """SyncManager 인스턴스 반환"""
    return sync_manager


__all__ = [
    # Enums
    "SyncDirection",
    "SyncTrigger",
    # Classes
    "SyncResult",
    "SyncManager",
    # Convenience functions
    "sync_todos_on_update",
    "validate_state_plan_sync",
    # Instance
    "sync_manager",
    "get_sync_manager",
]
