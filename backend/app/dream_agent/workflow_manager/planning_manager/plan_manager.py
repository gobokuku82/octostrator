"""Plan Manager - 동적 계획 관리 시스템"""

from typing import Dict, List, Optional, Any, Callable
from backend.app.core.logging import get_logger
from backend.app.dream_agent.states import (
    Plan, PlanVersion, PlanChange,
    TodoItem,
    create_plan, create_plan_change, create_plan_version
)
from backend.app.dream_agent.workflow_manager.hitl_manager import (
    replan_manager, decision_manager
)
from backend.app.dream_agent.workflow_manager.todo_manager import (
    todo_dependency_manager, TodoValidator
)

logger = get_logger(__name__)


class PlanManager:
    """
    계획 관리 시스템

    기능:
    - 계획 CRUD
    - Todo 동적 추가/삭제/수정
    - 버전 관리 및 롤백
    - HITL 통합 (ReplanManager, DecisionManager)
    - Todo Manager 통합 (TodoValidator, TodoDependencyManager)
    """

    def __init__(self):
        """초기화"""
        self.plans: Dict[str, Plan] = {}  # plan_id -> Plan
        self.session_plans: Dict[str, str] = {}  # session_id -> plan_id

        logger.info("PlanManager initialized")

    # ============================================================
    # CRUD Operations
    # ============================================================

    def create_plan_for_session(
        self,
        session_id: str,
        todos: List[TodoItem],
        intent: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Plan:
        """
        세션에 대한 새 계획 생성

        Args:
            session_id: 세션 ID
            todos: 초기 todos
            intent: Cognitive layer 결과
            context: 추가 컨텍스트

        Returns:
            생성된 Plan
        """
        # 기존 계획이 있으면 로그 남기기
        if session_id in self.session_plans:
            old_plan_id = self.session_plans[session_id]
            logger.warning(
                f"Session {session_id} already has plan {old_plan_id}. "
                f"Creating new plan will replace it."
            )

        # 새 계획 생성
        plan = create_plan(
            session_id=session_id,
            todos=todos,
            intent=intent,
            context=context
        )

        # 저장
        self.plans[plan.plan_id] = plan
        self.session_plans[session_id] = plan.plan_id

        logger.info(
            f"Plan created: plan_id={plan.plan_id}, session_id={session_id}, "
            f"todos={len(todos)}"
        )

        return plan

    def get_plan(self, plan_id: str) -> Optional[Plan]:
        """계획 조회"""
        return self.plans.get(plan_id)

    def get_plan_by_session(self, session_id: str) -> Optional[Plan]:
        """세션으로 계획 조회"""
        plan_id = self.session_plans.get(session_id)
        if not plan_id:
            return None
        return self.plans.get(plan_id)

    def delete_plan(self, plan_id: str) -> bool:
        """
        계획 삭제

        Args:
            plan_id: 계획 ID

        Returns:
            성공 여부
        """
        if plan_id not in self.plans:
            logger.warning(f"Plan not found: {plan_id}")
            return False

        plan = self.plans[plan_id]
        session_id = plan.session_id

        # 삭제
        del self.plans[plan_id]
        if session_id in self.session_plans:
            del self.session_plans[session_id]

        logger.info(f"Plan deleted: {plan_id}")
        return True

    def list_plans(self) -> List[Plan]:
        """모든 계획 조회"""
        return list(self.plans.values())

    # ============================================================
    # Todo Operations
    # ============================================================

    def add_todo(
        self,
        plan_id: str,
        todo: TodoItem,
        reason: str,
        actor: str = "system"
    ) -> Optional[Plan]:
        """
        Todo 추가

        Args:
            plan_id: 계획 ID
            todo: 추가할 TodoItem
            reason: 추가 이유
            actor: 추가 주체 ("system", "user", "hitl_manager")

        Returns:
            업데이트된 Plan 또는 None
        """
        plan = self.plans.get(plan_id)
        if not plan:
            logger.warning(f"Plan not found: {plan_id}")
            return None

        # 변경 기록 생성
        change = create_plan_change(
            change_type="add_todo",
            reason=reason,
            actor=actor,
            affected_todo_ids=[todo.id],
            change_data={"todo_task": todo.task, "todo_layer": todo.layer}
        )

        # Todo 추가
        plan.todos.append(todo)
        plan.current_version += 1
        plan.changes.append(change)

        # 새 버전 생성
        version = create_plan_version(
            version=plan.current_version,
            todos=plan.todos,
            change=change,
            change_summary=f"Added todo: {todo.task}"
        )
        plan.versions.append(version)

        # 통계 업데이트
        plan.update_statistics()

        logger.info(
            f"Todo added to plan {plan_id}: todo_id={todo.id}, task={todo.task}"
        )

        return plan

    def remove_todo(
        self,
        plan_id: str,
        todo_id: str,
        reason: str,
        actor: str = "system"
    ) -> Optional[Plan]:
        """
        Todo 제거

        Args:
            plan_id: 계획 ID
            todo_id: 제거할 todo ID
            reason: 제거 이유
            actor: 제거 주체

        Returns:
            업데이트된 Plan 또는 None
        """
        plan = self.plans.get(plan_id)
        if not plan:
            logger.warning(f"Plan not found: {plan_id}")
            return None

        # Todo 찾기
        todo = next((t for t in plan.todos if t.id == todo_id), None)
        if not todo:
            logger.warning(f"Todo not found in plan: todo_id={todo_id}")
            return None

        # 변경 기록 생성
        change = create_plan_change(
            change_type="remove_todo",
            reason=reason,
            actor=actor,
            affected_todo_ids=[todo_id],
            change_data={"todo_task": todo.task, "todo_layer": todo.layer}
        )

        # Todo 제거
        plan.todos = [t for t in plan.todos if t.id != todo_id]
        plan.current_version += 1
        plan.changes.append(change)

        # 새 버전 생성
        version = create_plan_version(
            version=plan.current_version,
            todos=plan.todos,
            change=change,
            change_summary=f"Removed todo: {todo.task}"
        )
        plan.versions.append(version)

        # 통계 업데이트
        plan.update_statistics()

        logger.info(
            f"Todo removed from plan {plan_id}: todo_id={todo_id}, task={todo.task}"
        )

        return plan

    def modify_todo(
        self,
        plan_id: str,
        todo_id: str,
        updates: Dict[str, Any],
        reason: str,
        actor: str = "system"
    ) -> Optional[Plan]:
        """
        Todo 수정

        Args:
            plan_id: 계획 ID
            todo_id: 수정할 todo ID
            updates: 업데이트 dict (Pydantic model_copy update 형식)
            reason: 수정 이유
            actor: 수정 주체

        Returns:
            업데이트된 Plan 또는 None
        """
        plan = self.plans.get(plan_id)
        if not plan:
            logger.warning(f"Plan not found: {plan_id}")
            return None

        # Todo 찾기
        todo_index = next(
            (i for i, t in enumerate(plan.todos) if t.id == todo_id),
            None
        )
        if todo_index is None:
            logger.warning(f"Todo not found in plan: todo_id={todo_id}")
            return None

        old_todo = plan.todos[todo_index]

        # 변경 기록 생성
        change = create_plan_change(
            change_type="modify_todo",
            reason=reason,
            actor=actor,
            affected_todo_ids=[todo_id],
            change_data={
                "updates": updates,
                "old_values": {
                    key: getattr(old_todo, key, None)
                    for key in updates.keys()
                }
            }
        )

        # Todo 수정
        # version과 updated_at도 자동으로 업데이트
        updates_with_meta = {
            **updates,
            "version": old_todo.version + 1,
            "updated_at": change.timestamp
        }

        updated_todo = old_todo.model_copy(update=updates_with_meta)

        # History에 변경 기록 추가
        updated_todo.history.append({
            "timestamp": change.timestamp.isoformat(),
            "action": "modified_by_plan_manager",
            "reason": reason,
            "actor": actor,
            "updates": updates
        })

        # 교체
        plan.todos[todo_index] = updated_todo
        plan.current_version += 1
        plan.changes.append(change)

        # 새 버전 생성
        version = create_plan_version(
            version=plan.current_version,
            todos=plan.todos,
            change=change,
            change_summary=f"Modified todo: {updated_todo.task}"
        )
        plan.versions.append(version)

        # 통계 업데이트
        plan.update_statistics()

        logger.info(
            f"Todo modified in plan {plan_id}: todo_id={todo_id}, updates={updates}"
        )

        return plan

    def reorder_todos(
        self,
        plan_id: str,
        todo_ids: List[str],
        reason: str,
        actor: str = "system"
    ) -> Optional[Plan]:
        """
        Todo 순서 변경

        Args:
            plan_id: 계획 ID
            todo_ids: 새로운 순서의 todo IDs
            reason: 재정렬 이유
            actor: 재정렬 주체

        Returns:
            업데이트된 Plan 또는 None
        """
        plan = self.plans.get(plan_id)
        if not plan:
            logger.warning(f"Plan not found: {plan_id}")
            return None

        # 모든 todo_ids가 존재하는지 확인
        existing_ids = {t.id for t in plan.todos}
        if set(todo_ids) != existing_ids:
            logger.error(
                f"Todo IDs mismatch: provided={set(todo_ids)}, "
                f"existing={existing_ids}"
            )
            return None

        # 변경 기록 생성
        change = create_plan_change(
            change_type="reorder",
            reason=reason,
            actor=actor,
            affected_todo_ids=todo_ids,
            change_data={"new_order": todo_ids}
        )

        # 재정렬
        todo_map = {t.id: t for t in plan.todos}
        plan.todos = [todo_map[tid] for tid in todo_ids]
        plan.current_version += 1
        plan.changes.append(change)

        # 새 버전 생성
        version = create_plan_version(
            version=plan.current_version,
            todos=plan.todos,
            change=change,
            change_summary="Todos reordered"
        )
        plan.versions.append(version)

        # 통계 업데이트
        plan.update_statistics()

        logger.info(f"Todos reordered in plan {plan_id}")

        return plan

    # ============================================================
    # Version Management
    # ============================================================

    def get_version_history(self, plan_id: str) -> List[PlanVersion]:
        """
        버전 히스토리 조회

        Args:
            plan_id: 계획 ID

        Returns:
            PlanVersion 리스트 (최신순)
        """
        plan = self.plans.get(plan_id)
        if not plan:
            return []

        return sorted(plan.versions, key=lambda v: v.version, reverse=True)

    def get_change_history(
        self,
        plan_id: str,
        limit: Optional[int] = None
    ) -> List[PlanChange]:
        """
        변경 히스토리 조회

        Args:
            plan_id: 계획 ID
            limit: 최대 개수 (None이면 전체)

        Returns:
            PlanChange 리스트 (최신순)
        """
        plan = self.plans.get(plan_id)
        if not plan:
            return []

        if limit is None:
            return plan.get_recent_changes(limit=len(plan.changes))
        else:
            return plan.get_recent_changes(limit=limit)

    def rollback_to_version(
        self,
        plan_id: str,
        version: int,
        reason: str,
        actor: str = "user"
    ) -> Optional[Plan]:
        """
        특정 버전으로 롤백

        Args:
            plan_id: 계획 ID
            version: 롤백할 버전 번호
            reason: 롤백 이유
            actor: 롤백 주체

        Returns:
            업데이트된 Plan 또는 None
        """
        plan = self.plans.get(plan_id)
        if not plan:
            logger.warning(f"Plan not found: {plan_id}")
            return None

        # 버전 찾기
        target_version = plan.get_version(version)
        if not target_version:
            logger.warning(f"Version not found: {version}")
            return None

        # 변경 기록 생성
        change = create_plan_change(
            change_type="rollback",
            reason=reason,
            actor=actor,
            affected_todo_ids=[t.id for t in target_version.todos],
            change_data={
                "from_version": plan.current_version,
                "to_version": version
            }
        )

        # 롤백
        plan.todos = target_version.todos.copy()
        plan.current_version += 1  # 롤백도 새 버전으로 기록
        plan.changes.append(change)

        # 새 버전 생성
        new_version = create_plan_version(
            version=plan.current_version,
            todos=plan.todos,
            change=change,
            change_summary=f"Rolled back to version {version}"
        )
        plan.versions.append(new_version)

        # 통계 업데이트
        plan.update_statistics()

        logger.info(
            f"Plan {plan_id} rolled back from version {change.change_data['from_version']} "
            f"to version {version}"
        )

        return plan

    # ============================================================
    # Status Management
    # ============================================================

    def update_status(
        self,
        plan_id: str,
        status: str,
        reason: Optional[str] = None
    ) -> Optional[Plan]:
        """
        계획 상태 업데이트

        Args:
            plan_id: 계획 ID
            status: 새 상태
            reason: 변경 이유

        Returns:
            업데이트된 Plan 또는 None
        """
        plan = self.plans.get(plan_id)
        if not plan:
            logger.warning(f"Plan not found: {plan_id}")
            return None

        old_status = plan.status
        plan.status = status
        plan.updated_at = change.timestamp if 'change' in locals() else datetime.now()

        # 상태별 타임스탬프 업데이트
        from datetime import datetime
        now = datetime.now()

        if status == "approved" and not plan.approved_at:
            plan.approved_at = now
        elif status == "executing" and not plan.started_at:
            plan.started_at = now
        elif status in ["completed", "failed", "cancelled"] and not plan.completed_at:
            plan.completed_at = now

        logger.info(
            f"Plan {plan_id} status changed: {old_status} → {status}"
            + (f" (reason: {reason})" if reason else "")
        )

        return plan

    def pause_plan(
        self,
        plan_id: str,
        reason: str = "User requested pause"
    ) -> Optional[Plan]:
        """
        계획 일시중지 (Interrupt Type 2)

        Args:
            plan_id: 계획 ID
            reason: 일시중지 이유

        Returns:
            업데이트된 Plan 또는 None
        """
        plan = self.update_status(plan_id, "paused", reason)
        if plan:
            plan.current_interrupt_type = "manual"
        return plan

    def resume_plan(
        self,
        plan_id: str,
        reason: str = "User resumed execution"
    ) -> Optional[Plan]:
        """
        계획 재개 (Interrupt Type 2)

        Args:
            plan_id: 계획 ID
            reason: 재개 이유

        Returns:
            업데이트된 Plan 또는 None
        """
        plan = self.update_status(plan_id, "executing", reason)
        if plan:
            plan.current_interrupt_type = None
        return plan

    # ============================================================
    # HITL Integration (Human-in-the-Loop)
    # ============================================================

    async def replan_with_user_instruction(
        self,
        plan_id: str,
        user_instruction: str,
        actor: str = "user"
    ) -> Optional[Plan]:
        """
        사용자 지시에 따른 재계획 (Interrupt Type 2 - Manual)

        ReplanManager를 사용하여 자연어 지시를 todos 수정으로 변환

        Args:
            plan_id: 계획 ID
            user_instruction: 사용자 지시
                예: "쿠팡 말고 네이버 쇼핑으로 바꿔줘"
                예: "2번 작업 삭제해줘"
            actor: 재계획 주체

        Returns:
            업데이트된 Plan 또는 None
        """
        plan = self.plans.get(plan_id)
        if not plan:
            logger.warning(f"Plan not found: {plan_id}")
            return None

        try:
            # ReplanManager 호출
            replan_result = await replan_manager.replan(
                session_id=plan.session_id,
                user_instruction=user_instruction,
                current_plan=None,  # ReplanManager가 TodoStore에서 로드
                current_todos=plan.todos,
                save_to_store=False  # PlanManager가 직접 관리
            )

            if not replan_result.success:
                logger.error(
                    f"Replan failed: {replan_result.error}"
                )
                return None

            # 변경 기록 생성
            change = create_plan_change(
                change_type="replan",
                reason="User instruction",
                actor=actor,
                affected_todo_ids=[
                    t.id for t in replan_result.modified_todos
                ],
                change_data={
                    "changes": replan_result.changes
                },
                user_instruction=user_instruction,
                replan_summary=replan_result.modification_summary
            )

            # Todos 업데이트
            plan.todos = replan_result.modified_todos
            plan.current_version += 1
            plan.changes.append(change)

            # 새 버전 생성
            version = create_plan_version(
                version=plan.current_version,
                todos=plan.todos,
                change=change,
                change_summary=replan_result.modification_summary
            )
            plan.versions.append(version)

            # 통계 업데이트
            plan.update_statistics()

            logger.info(
                f"Plan {plan_id} replanned: {replan_result.modification_summary}"
            )

            return plan

        except Exception as e:
            logger.error(
                f"Error during replan: {e}",
                exc_info=True
            )
            return None

    async def request_user_decision(
        self,
        plan_id: str,
        context: Dict[str, Any],
        options: List[Dict[str, Any]],
        message: str,
        timeout: int = 300,
        websocket_callback: Optional[Callable] = None
    ) -> Optional[Dict[str, Any]]:
        """
        사용자 결정 요청 (Interrupt Type 1 - Auto)

        DecisionManager를 사용하여 사용자 의사결정 대기

        Args:
            plan_id: 계획 ID
            context: 결정 컨텍스트
                예: {"todo_id": "...", "error": "Data source not specified"}
            options: 선택 옵션
                예: [
                    {"value": "amazon", "label": "아마존", "description": "..."},
                    {"value": "coupang", "label": "쿠팡", "description": "..."}
                ]
            message: 사용자에게 표시할 메시지
            timeout: 타임아웃 (초)
            websocket_callback: WebSocket 알림 콜백

        Returns:
            사용자 결정 dict 또는 None (타임아웃)
            예: {"action": "amazon", "data": {...}}
        """
        plan = self.plans.get(plan_id)
        if not plan:
            logger.warning(f"Plan not found: {plan_id}")
            return None

        # 상태 업데이트: waiting
        plan.status = "waiting"
        plan.current_interrupt_type = "auto"

        # Request ID 생성
        request_id = f"{plan_id}_{context.get('todo_id', 'unknown')}"
        plan.pending_decision_request_id = request_id

        try:
            # DecisionManager 호출
            decision = await decision_manager.request_decision(
                request_id=request_id,
                session_id=plan.session_id,
                context=context,
                options=options,
                message=message,
                timeout=timeout,
                websocket_callback=websocket_callback
            )

            # 결정 기록
            change = create_plan_change(
                change_type="user_decision",
                reason="User decision requested",
                actor="system",
                affected_todo_ids=[context.get("todo_id", "unknown")],
                change_data={
                    "context": context,
                    "options": options,
                    "decision": decision
                },
                decision_request_id=request_id,
                decision_action=decision.get("action") if decision else None,
                decision_data=decision.get("data") if decision else None
            )

            plan.changes.append(change)
            plan.pending_decision_request_id = None

            # 상태 복원
            if decision:
                plan.status = "executing"
                plan.current_interrupt_type = None
                logger.info(
                    f"User decision received for plan {plan_id}: {decision}"
                )
            else:
                # 타임아웃
                plan.status = "failed"
                plan.current_interrupt_type = None
                logger.warning(
                    f"User decision timed out for plan {plan_id}"
                )

            return decision

        except Exception as e:
            logger.error(
                f"Error during request_user_decision: {e}",
                exc_info=True
            )
            plan.pending_decision_request_id = None
            plan.status = "failed"
            plan.current_interrupt_type = None
            return None

    # ============================================================
    # Todo Manager Integration
    # ============================================================

    def validate_plan_todos(
        self,
        plan_id: str,
        intent: Optional[Dict[str, Any]] = None,
        user_input: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        계획의 todos 검증

        TodoValidator를 사용하여 todos가 intent와 일치하는지 검증

        Args:
            plan_id: 계획 ID
            intent: Cognitive layer 결과 (None이면 plan.intent 사용)
            user_input: 사용자 입력 (None이면 plan.context에서 추출)

        Returns:
            검증 결과 dict
            {
                "valid": bool,
                "errors": List[str],
                "warnings": List[str],
                "suggestions": List[str],
                "total_todos": int,
                "ml_todos": int,
                "biz_todos": int
            }
        """
        plan = self.plans.get(plan_id)
        if not plan:
            logger.warning(f"Plan not found: {plan_id}")
            return {
                "valid": False,
                "errors": ["Plan not found"],
                "warnings": [],
                "suggestions": [],
                "total_todos": 0,
                "ml_todos": 0,
                "biz_todos": 0
            }

        # Intent와 user_input 결정
        intent_to_use = intent or plan.intent
        user_input_to_use = user_input or plan.context.get("user_input", "")

        # TodoValidator 호출
        validation_result = TodoValidator.validate_todos(
            todos=plan.todos,
            intent=intent_to_use,
            user_input=user_input_to_use
        )

        logger.info(
            f"Plan {plan_id} validation: valid={validation_result['valid']}, "
            f"errors={len(validation_result['errors'])}, "
            f"warnings={len(validation_result['warnings'])}"
        )

        return validation_result

    def get_ready_todos(self, plan_id: str) -> List[TodoItem]:
        """
        실행 가능한 todos 조회

        TodoDependencyManager를 사용하여 의존성이 충족된 todos 반환

        Args:
            plan_id: 계획 ID

        Returns:
            실행 가능한 todos (우선순위 순)
        """
        plan = self.plans.get(plan_id)
        if not plan:
            logger.warning(f"Plan not found: {plan_id}")
            return []

        ready_todos = todo_dependency_manager.get_ready_todos(plan.todos)

        logger.debug(
            f"Plan {plan_id} has {len(ready_todos)} ready todos"
        )

        return ready_todos

    def auto_unblock_todos(self, plan_id: str) -> Optional[Plan]:
        """
        자동 unblock - 의존성이 충족되면 pending으로 변경

        TodoDependencyManager를 사용하여 blocked todos 자동 해제

        Args:
            plan_id: 계획 ID

        Returns:
            업데이트된 Plan 또는 None
        """
        plan = self.plans.get(plan_id)
        if not plan:
            logger.warning(f"Plan not found: {plan_id}")
            return None

        # Auto unblock
        unblocked_todos = todo_dependency_manager.auto_unblock_todos(plan.todos)

        if not unblocked_todos:
            logger.debug(f"No todos unblocked for plan {plan_id}")
            return plan

        # Todo 업데이트 (ID 기반 교체)
        todo_map = {t.id: t for t in plan.todos}
        for unblocked in unblocked_todos:
            todo_map[unblocked.id] = unblocked

        plan.todos = list(todo_map.values())
        plan.update_statistics()

        logger.info(
            f"Plan {plan_id}: {len(unblocked_todos)} todos auto-unblocked"
        )

        return plan

    def check_circular_dependency(self, plan_id: str) -> List[str]:
        """
        순환 의존성 검사

        TodoDependencyManager를 사용하여 순환 의존성 검출

        Args:
            plan_id: 계획 ID

        Returns:
            순환이 발견된 todo IDs
        """
        plan = self.plans.get(plan_id)
        if not plan:
            logger.warning(f"Plan not found: {plan_id}")
            return []

        cycles = todo_dependency_manager.check_circular_dependency(plan.todos)

        if cycles:
            logger.error(
                f"Plan {plan_id} has circular dependencies: {cycles}"
            )
        else:
            logger.debug(f"Plan {plan_id} has no circular dependencies")

        return cycles

    def topological_sort_todos(
        self,
        plan_id: str,
        apply_to_plan: bool = False
    ) -> Optional[List[TodoItem]]:
        """
        위상 정렬 (Topological Sort)

        TodoDependencyManager를 사용하여 의존성 순서대로 todos 정렬

        Args:
            plan_id: 계획 ID
            apply_to_plan: True이면 정렬된 결과를 plan에 적용

        Returns:
            정렬된 todos 또는 None (순환 의존성 존재 시)
        """
        plan = self.plans.get(plan_id)
        if not plan:
            logger.warning(f"Plan not found: {plan_id}")
            return None

        sorted_todos, success = todo_dependency_manager.topological_sort(plan.todos)

        if not success:
            logger.error(
                f"Topological sort failed for plan {plan_id}: "
                f"circular dependency detected"
            )
            return None

        if apply_to_plan:
            # 변경 기록 생성
            change = create_plan_change(
                change_type="reorder",
                reason="Topological sort applied",
                actor="system",
                affected_todo_ids=[t.id for t in sorted_todos],
                change_data={"sort_type": "topological"}
            )

            # Todos 재정렬
            plan.todos = sorted_todos
            plan.current_version += 1
            plan.changes.append(change)

            # 새 버전 생성
            version = create_plan_version(
                version=plan.current_version,
                todos=plan.todos,
                change=change,
                change_summary="Todos sorted topologically"
            )
            plan.versions.append(version)

            # 통계 업데이트
            plan.update_statistics()

            logger.info(f"Plan {plan_id} todos sorted topologically")

        return sorted_todos


# ============================================================
# Global Instance (Singleton Pattern)
# ============================================================

_plan_manager_instance: Optional[PlanManager] = None


def get_plan_manager() -> PlanManager:
    """PlanManager 싱글톤 인스턴스 반환"""
    global _plan_manager_instance
    if _plan_manager_instance is None:
        _plan_manager_instance = PlanManager()
    return _plan_manager_instance


# 글로벌 인스턴스 (편의용)
plan_manager = get_plan_manager()
