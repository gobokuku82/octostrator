"""Plan Editor - HITL 중 계획 편집 기능

Todo CRUD 작업 및 의존성 관리
"""

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import logging
import uuid

from ...models.plan import Plan, PlanChange, PlanVersion, create_plan_change
from ...models.todo import TodoItem, TodoMetadata, TodoDependencyConfig

logger = logging.getLogger(__name__)


class EditOperation(str, Enum):
    """편집 작업 유형"""
    ADD = "add"
    UPDATE = "update"
    DELETE = "delete"
    REORDER = "reorder"
    SKIP = "skip"


@dataclass
class PlanEdit:
    """계획 편집 요청"""
    operation: EditOperation
    todo_id: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    position: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리 변환"""
        return {
            "operation": self.operation.value,
            "todo_id": self.todo_id,
            "data": self.data,
            "position": self.position,
        }


@dataclass
class EditResult:
    """편집 결과"""
    success: bool
    operation: EditOperation
    todo_id: Optional[str] = None
    error: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리 변환"""
        return {
            "success": self.success,
            "operation": self.operation.value,
            "todo_id": self.todo_id,
            "error": self.error,
            "details": self.details,
        }


class PlanEditor:
    """
    계획 편집기

    HITL 모드에서 Plan의 Todos를 CRUD하는 기능 제공
    - Todo 추가 (ADD)
    - Todo 수정 (UPDATE)
    - Todo 삭제 (DELETE)
    - Todo 순서 변경 (REORDER)
    - Todo 건너뛰기 (SKIP)
    """

    def __init__(self, session_id: str):
        self.session_id = session_id
        self._edit_history: List[Dict[str, Any]] = []
        self._created_at = datetime.now()

    async def apply_edits(
        self,
        plan_obj: Plan,
        edits: List[PlanEdit],
        actor: str = "user"
    ) -> Tuple[Plan, Dict[str, Any]]:
        """
        편집 적용

        Args:
            plan_obj: Plan 객체
            edits: 편집 목록
            actor: 편집 주체

        Returns:
            (updated_plan, state_update_dict)
        """
        results: List[EditResult] = []
        applied_edits: List[PlanEdit] = []

        for edit in edits:
            result = await self._apply_single_edit(plan_obj, edit, actor)
            results.append(result)

            if result.success:
                applied_edits.append(edit)
                self._edit_history.append({
                    "edit": edit.to_dict(),
                    "result": result.to_dict(),
                    "timestamp": datetime.now().isoformat(),
                })

        # State 업데이트 생성
        state_update = {
            "todos": plan_obj.todos,
            "plan_obj": plan_obj,
        }

        # 요약 로그
        success_count = sum(1 for r in results if r.success)
        logger.info(
            f"[PlanEditor] Session {self.session_id}: "
            f"{success_count}/{len(edits)} edits applied"
        )

        return plan_obj, state_update

    async def _apply_single_edit(
        self,
        plan_obj: Plan,
        edit: PlanEdit,
        actor: str
    ) -> EditResult:
        """단일 편집 적용"""
        try:
            if edit.operation == EditOperation.ADD:
                return await self._add_todo(plan_obj, edit.data, edit.position, actor)

            elif edit.operation == EditOperation.UPDATE:
                return await self._update_todo(plan_obj, edit.todo_id, edit.data, actor)

            elif edit.operation == EditOperation.DELETE:
                return await self._delete_todo(plan_obj, edit.todo_id, actor)

            elif edit.operation == EditOperation.REORDER:
                return await self._reorder_todo(plan_obj, edit.todo_id, edit.position, actor)

            elif edit.operation == EditOperation.SKIP:
                return await self._skip_todo(plan_obj, edit.todo_id, actor)

            else:
                return EditResult(
                    success=False,
                    operation=edit.operation,
                    error=f"Unknown operation: {edit.operation}"
                )

        except Exception as e:
            logger.error(f"Edit failed: {e}")
            return EditResult(
                success=False,
                operation=edit.operation,
                todo_id=edit.todo_id,
                error=str(e)
            )

    async def _add_todo(
        self,
        plan_obj: Plan,
        data: Dict[str, Any],
        position: Optional[int],
        actor: str
    ) -> EditResult:
        """
        Todo 추가

        Args:
            plan_obj: Plan 객체
            data: Todo 데이터
                - task: 작업 설명 (필수)
                - layer: 레이어 (기본: "ml_execution")
                - tool: 도구
                - depends_on: 의존 IDs
                - priority: 우선순위
            position: 삽입 위치 (None이면 끝)
            actor: 작업 주체
        """
        if not data:
            return EditResult(
                success=False,
                operation=EditOperation.ADD,
                error="No data provided"
            )

        task = data.get("task", data.get("content", ""))
        if not task:
            return EditResult(
                success=False,
                operation=EditOperation.ADD,
                error="Task/content is required"
            )

        # TodoItem 생성
        todo_id = str(uuid.uuid4())
        metadata = TodoMetadata()

        # 메타데이터 설정
        if data.get("tool"):
            metadata.execution.tool = data["tool"]

        if data.get("tool_params"):
            metadata.execution.tool_params = data["tool_params"]

        if data.get("depends_on"):
            metadata.dependency.depends_on = data["depends_on"]

        todo = TodoItem(
            id=todo_id,
            task=task,
            task_type=data.get("task_type", "general"),
            layer=data.get("layer", "ml_execution"),
            priority=data.get("priority", 5),
            metadata=metadata,
            created_by=actor,
        )

        # 위치에 삽입
        if position is not None and 0 <= position <= len(plan_obj.todos):
            plan_obj.todos.insert(position, todo)
        else:
            plan_obj.todos.append(todo)

        # 버전 증가
        plan_obj.current_version += 1
        plan_obj.updated_at = datetime.now()

        # 변경 이력 기록
        change = create_plan_change(
            change_type="add_todo",
            reason=f"Todo added by {actor}",
            actor=actor,
            affected_todo_ids=[todo_id],
            change_data={"todo_data": data, "position": position}
        )
        plan_obj.changes.append(change)

        logger.info(f"[PlanEditor] Added todo: {todo_id} - {task[:30]}")

        return EditResult(
            success=True,
            operation=EditOperation.ADD,
            todo_id=todo_id,
            details={"task": task, "position": position}
        )

    async def _update_todo(
        self,
        plan_obj: Plan,
        todo_id: str,
        data: Dict[str, Any],
        actor: str
    ) -> EditResult:
        """
        Todo 수정

        Args:
            plan_obj: Plan 객체
            todo_id: 수정할 Todo ID
            data: 수정 데이터
                - task: 작업 설명
                - status: 상태
                - priority: 우선순위
                - depends_on: 의존 IDs
                - tool: 도구
            actor: 작업 주체
        """
        if not todo_id:
            return EditResult(
                success=False,
                operation=EditOperation.UPDATE,
                error="todo_id is required"
            )

        todo = plan_obj.get_todo_by_id(todo_id)
        if not todo:
            return EditResult(
                success=False,
                operation=EditOperation.UPDATE,
                todo_id=todo_id,
                error=f"Todo not found: {todo_id}"
            )

        # 변경 이전 상태 저장
        previous_state = {
            "task": todo.task,
            "status": todo.status,
            "priority": todo.priority,
        }

        # 필드 업데이트
        updated_fields = []

        if "task" in data or "content" in data:
            todo.task = data.get("task", data.get("content", todo.task))
            updated_fields.append("task")

        if "status" in data:
            todo.status = data["status"]
            updated_fields.append("status")

        if "priority" in data:
            todo.priority = data["priority"]
            updated_fields.append("priority")

        if "depends_on" in data:
            if todo.metadata and todo.metadata.dependency:
                todo.metadata.dependency.depends_on = data["depends_on"]
                updated_fields.append("depends_on")

        if "tool" in data:
            if todo.metadata and todo.metadata.execution:
                todo.metadata.execution.tool = data["tool"]
                updated_fields.append("tool")

        if "tool_params" in data:
            if todo.metadata and todo.metadata.execution:
                todo.metadata.execution.tool_params = data["tool_params"]
                updated_fields.append("tool_params")

        # 버전 증가
        todo.version += 1
        todo.updated_at = datetime.now()
        plan_obj.current_version += 1
        plan_obj.updated_at = datetime.now()

        # 변경 이력 기록
        change = create_plan_change(
            change_type="modify_todo",
            reason=f"Todo modified by {actor}",
            actor=actor,
            affected_todo_ids=[todo_id],
            change_data={
                "previous": previous_state,
                "updated_fields": updated_fields,
                "new_data": data
            }
        )
        plan_obj.changes.append(change)

        logger.info(f"[PlanEditor] Updated todo: {todo_id} - fields: {updated_fields}")

        return EditResult(
            success=True,
            operation=EditOperation.UPDATE,
            todo_id=todo_id,
            details={"updated_fields": updated_fields}
        )

    async def _delete_todo(
        self,
        plan_obj: Plan,
        todo_id: str,
        actor: str
    ) -> EditResult:
        """
        Todo 삭제

        Args:
            plan_obj: Plan 객체
            todo_id: 삭제할 Todo ID
            actor: 작업 주체
        """
        if not todo_id:
            return EditResult(
                success=False,
                operation=EditOperation.DELETE,
                error="todo_id is required"
            )

        todo = plan_obj.get_todo_by_id(todo_id)
        if not todo:
            return EditResult(
                success=False,
                operation=EditOperation.DELETE,
                todo_id=todo_id,
                error=f"Todo not found: {todo_id}"
            )

        # 삭제 전 정보 저장
        deleted_task = todo.task

        # Todo 삭제
        plan_obj.todos = [t for t in plan_obj.todos if t.id != todo_id]

        # 의존성 정리 - 삭제된 todo에 의존하는 다른 todos 업데이트
        affected_todos = []
        for t in plan_obj.todos:
            if t.metadata and t.metadata.dependency:
                if todo_id in t.metadata.dependency.depends_on:
                    t.metadata.dependency.depends_on.remove(todo_id)
                    affected_todos.append(t.id)

        # 버전 증가
        plan_obj.current_version += 1
        plan_obj.updated_at = datetime.now()

        # 변경 이력 기록
        change = create_plan_change(
            change_type="remove_todo",
            reason=f"Todo deleted by {actor}",
            actor=actor,
            affected_todo_ids=[todo_id] + affected_todos,
            change_data={
                "deleted_task": deleted_task,
                "dependency_updated_todos": affected_todos
            }
        )
        plan_obj.changes.append(change)

        logger.info(
            f"[PlanEditor] Deleted todo: {todo_id} - {deleted_task[:30]}, "
            f"dependency updated: {len(affected_todos)} todos"
        )

        return EditResult(
            success=True,
            operation=EditOperation.DELETE,
            todo_id=todo_id,
            details={
                "deleted_task": deleted_task,
                "dependency_updated": affected_todos
            }
        )

    async def _reorder_todo(
        self,
        plan_obj: Plan,
        todo_id: str,
        new_position: int,
        actor: str
    ) -> EditResult:
        """
        Todo 순서 변경

        Args:
            plan_obj: Plan 객체
            todo_id: 이동할 Todo ID
            new_position: 새 위치
            actor: 작업 주체
        """
        if not todo_id:
            return EditResult(
                success=False,
                operation=EditOperation.REORDER,
                error="todo_id is required"
            )

        if new_position is None:
            return EditResult(
                success=False,
                operation=EditOperation.REORDER,
                todo_id=todo_id,
                error="new_position is required"
            )

        todo = plan_obj.get_todo_by_id(todo_id)
        if not todo:
            return EditResult(
                success=False,
                operation=EditOperation.REORDER,
                todo_id=todo_id,
                error=f"Todo not found: {todo_id}"
            )

        # 현재 위치 찾기
        old_position = next(
            (i for i, t in enumerate(plan_obj.todos) if t.id == todo_id),
            None
        )

        if old_position is None:
            return EditResult(
                success=False,
                operation=EditOperation.REORDER,
                todo_id=todo_id,
                error="Could not find todo position"
            )

        # 위치 유효성 검사
        new_position = max(0, min(new_position, len(plan_obj.todos) - 1))

        # 순서 변경
        plan_obj.todos.pop(old_position)
        plan_obj.todos.insert(new_position, todo)

        # 버전 증가
        plan_obj.current_version += 1
        plan_obj.updated_at = datetime.now()

        # 변경 이력 기록
        change = create_plan_change(
            change_type="reorder",
            reason=f"Todo reordered by {actor}",
            actor=actor,
            affected_todo_ids=[todo_id],
            change_data={
                "old_position": old_position,
                "new_position": new_position
            }
        )
        plan_obj.changes.append(change)

        logger.info(
            f"[PlanEditor] Reordered todo: {todo_id} - "
            f"from {old_position} to {new_position}"
        )

        return EditResult(
            success=True,
            operation=EditOperation.REORDER,
            todo_id=todo_id,
            details={
                "old_position": old_position,
                "new_position": new_position
            }
        )

    async def _skip_todo(
        self,
        plan_obj: Plan,
        todo_id: str,
        actor: str
    ) -> EditResult:
        """
        Todo 건너뛰기

        Args:
            plan_obj: Plan 객체
            todo_id: 건너뛸 Todo ID
            actor: 작업 주체
        """
        if not todo_id:
            return EditResult(
                success=False,
                operation=EditOperation.SKIP,
                error="todo_id is required"
            )

        todo = plan_obj.get_todo_by_id(todo_id)
        if not todo:
            return EditResult(
                success=False,
                operation=EditOperation.SKIP,
                todo_id=todo_id,
                error=f"Todo not found: {todo_id}"
            )

        # 이미 완료/스킵된 경우
        if todo.status in ["completed", "skipped"]:
            return EditResult(
                success=False,
                operation=EditOperation.SKIP,
                todo_id=todo_id,
                error=f"Todo already {todo.status}"
            )

        previous_status = todo.status

        # 상태를 skipped로 변경
        todo.status = "skipped"
        todo.version += 1
        todo.updated_at = datetime.now()

        # 버전 증가
        plan_obj.current_version += 1
        plan_obj.updated_at = datetime.now()

        # 변경 이력 기록
        change = create_plan_change(
            change_type="modify_todo",
            reason=f"Todo skipped by {actor}",
            actor=actor,
            affected_todo_ids=[todo_id],
            change_data={
                "previous_status": previous_status,
                "new_status": "skipped"
            }
        )
        plan_obj.changes.append(change)

        logger.info(f"[PlanEditor] Skipped todo: {todo_id} - {todo.task[:30]}")

        return EditResult(
            success=True,
            operation=EditOperation.SKIP,
            todo_id=todo_id,
            details={"previous_status": previous_status}
        )

    def get_edit_history(self) -> List[Dict[str, Any]]:
        """편집 히스토리 반환"""
        return self._edit_history.copy()

    def get_summary(self) -> Dict[str, Any]:
        """편집기 요약 정보"""
        operations = {}
        for entry in self._edit_history:
            op = entry.get("edit", {}).get("operation", "unknown")
            operations[op] = operations.get(op, 0) + 1

        return {
            "session_id": self.session_id,
            "created_at": self._created_at.isoformat(),
            "total_edits": len(self._edit_history),
            "operations_summary": operations,
        }


# ============================================================
# Session별 Editor 관리
# ============================================================

_editors: Dict[str, PlanEditor] = {}


def get_plan_editor(session_id: str) -> PlanEditor:
    """
    Session별 PlanEditor 반환

    Args:
        session_id: 세션 ID

    Returns:
        PlanEditor 인스턴스
    """
    if session_id not in _editors:
        _editors[session_id] = PlanEditor(session_id)
    return _editors[session_id]


def remove_plan_editor(session_id: str) -> bool:
    """
    PlanEditor 제거

    Args:
        session_id: 세션 ID

    Returns:
        제거 여부
    """
    if session_id in _editors:
        del _editors[session_id]
        return True
    return False
