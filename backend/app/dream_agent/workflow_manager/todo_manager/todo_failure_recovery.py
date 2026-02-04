"""Todo Failure Recovery - 실패 복구 및 사용자 개입"""

import asyncio
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

from backend.app.core.logging import get_logger
from backend.app.dream_agent.models.todo import TodoItem
from .todo_updater import update_todo_status

logger = get_logger(__name__)


class TodoFailureRecovery:
    """Todo 실패 복구 관리자"""

    def __init__(self):
        self._pending_decisions: Dict[str, asyncio.Event] = {}
        self._decision_results: Dict[str, Dict[str, Any]] = {}

    async def handle_todo_failure(
        self,
        failed_todo: TodoItem,
        error: Exception,
        todos: List[TodoItem],
        session_id: str,
        websocket_callback=None
    ) -> Dict[str, Any]:
        """
        Todo 실패 처리

        Process:
        1. 에러 분석 (자동 복구 가능한가?)
        2. 자동 복구 시도
        3. 실패 시 사용자 개입 요청
        4. 사용자 결정에 따라 처리

        Args:
            failed_todo: 실패한 todo
            error: 발생한 에러
            todos: 전체 todo 리스트
            session_id: 세션 ID
            websocket_callback: WebSocket 콜백 (선택)

        Returns:
            복구 결과
            {
                "action": "retry" | "modify_and_retry" | "skip" | "abort",
                "updated_todo": TodoItem,
                "updated_todos": List[TodoItem],  # 의존 todos 업데이트
                "message": str
            }
        """
        logger.info(f"Handling failure for todo {failed_todo.id}: {error}")

        # Step 1: 에러 분류
        error_type = self._classify_error(error)
        logger.debug(f"Error classified as: {error_type}")

        # Step 2: 자동 복구 가능 여부 판단
        if error_type in ["temporary_network", "rate_limit", "timeout"]:
            # 자동 재시도
            result = await self._auto_retry(failed_todo, error)

            if result["action"] == "retry":
                return result

        elif error_type in ["invalid_input", "missing_data"]:
            # 입력 수정 후 재시도 (LLM이 수정)
            result = await self._auto_fix_and_retry(failed_todo, error)

            if result["action"] == "retry_with_fix":
                return result

        # Step 3: 자동 복구 실패 또는 불가능 → 사용자 개입
        logger.info(f"Requesting user intervention for todo {failed_todo.id}")

        if websocket_callback:
            user_decision = await self._request_user_intervention(
                failed_todo=failed_todo,
                error=error,
                session_id=session_id,
                websocket_callback=websocket_callback
            )
        else:
            # WebSocket 없으면 자동 skip
            logger.warning("No websocket callback - auto-skipping failed todo")
            user_decision = {
                "action": "skip",
                "reason": "No websocket available for user intervention"
            }

        # Step 4: 사용자 결정 처리
        return await self._handle_user_decision(
            failed_todo=failed_todo,
            todos=todos,
            decision=user_decision
        )

    def _classify_error(self, error: Exception) -> str:
        """에러 분류"""
        error_msg = str(error).lower()

        if "timeout" in error_msg or "timed out" in error_msg:
            return "timeout"

        if "network" in error_msg or "connection" in error_msg:
            return "temporary_network"

        if "rate limit" in error_msg or "429" in error_msg:
            return "rate_limit"

        if "invalid" in error_msg or "validation" in error_msg:
            return "invalid_input"

        if "not found" in error_msg or "missing" in error_msg:
            return "missing_data"

        if "permission" in error_msg or "forbidden" in error_msg or "403" in error_msg:
            return "permission_denied"

        if "quota" in error_msg or "limit exceeded" in error_msg:
            return "quota_exceeded"

        return "unknown"

    async def _auto_retry(
        self,
        todo: TodoItem,
        error: Exception
    ) -> Dict[str, Any]:
        """
        자동 재시도

        Args:
            todo: 실패한 todo
            error: 에러

        Returns:
            재시도 결과
        """
        # 재시도 횟수 체크
        if todo.metadata.execution.retry_count >= todo.metadata.execution.max_retries:
            logger.warning(f"Max retries exceeded for todo {todo.id}")
            return {
                "action": "escalate_to_user",
                "reason": "Max retries exceeded"
            }

        # 지수 백오프
        wait_time = 2 ** todo.metadata.execution.retry_count
        logger.info(f"Auto-retry todo {todo.id} after {wait_time}s (attempt {todo.metadata.execution.retry_count + 1}/{todo.metadata.execution.max_retries})")

        await asyncio.sleep(wait_time)

        # Todo 업데이트 (pending으로, retry_count 증가)
        updated_todo = todo.model_copy(update={
            "status": "pending",
            "version": todo.version + 1,
            "updated_at": datetime.now()
        })

        updated_todo.metadata.execution.retry_count += 1
        updated_todo.metadata.progress.error_message = None  # 에러 클리어

        updated_todo.history.append({
            "timestamp": datetime.now().isoformat(),
            "action": "auto_retry",
            "error": str(error),
            "retry_count": updated_todo.metadata.execution.retry_count,
            "wait_time": wait_time
        })

        return {
            "action": "retry",
            "updated_todo": updated_todo,
            "updated_todos": [],
            "message": f"Auto-retrying after {wait_time}s (attempt {updated_todo.metadata.execution.retry_count})"
        }

    async def _auto_fix_and_retry(
        self,
        todo: TodoItem,
        error: Exception
    ) -> Dict[str, Any]:
        """
        자동 수정 후 재시도

        LLM에게 에러 메시지를 주고 입력 수정 요청

        Args:
            todo: 실패한 todo
            error: 에러

        Returns:
            수정 후 재시도 결과
        """
        try:
            from backend.app.dream_agent.llm_manager import get_llm_client

            llm_client = get_llm_client()

            fix_prompt = f"""
Todo 실행 중 에러가 발생했습니다.

**Todo**:
- Task: {todo.task}
- Tool: {todo.metadata.execution.tool}
- Parameters: {json.dumps(todo.metadata.execution.tool_params, indent=2)}

**Error**:
{error}

**요청**:
1. 에러 원인을 분석하세요.
2. tool_params를 수정하여 에러를 해결하세요.
3. 수정된 tool_params를 JSON으로 반환하세요.

출력 형식:
{{
  "analysis": "에러 원인 분석",
  "fixed_params": {{}},
  "explanation": "수정 사항 설명"
}}
"""

            response = await llm_client.chat_with_system(
                system_prompt="You are a helpful assistant that fixes errors.",
                user_message=fix_prompt,
                max_tokens=500
            )

            fix_data = json.loads(response)

            # Todo 업데이트
            updated_todo = todo.model_copy(update={
                "status": "pending",
                "version": todo.version + 1,
                "updated_at": datetime.now()
            })

            updated_todo.metadata.execution.tool_params = fix_data["fixed_params"]
            updated_todo.metadata.execution.retry_count += 1
            updated_todo.metadata.progress.error_message = None

            updated_todo.history.append({
                "timestamp": datetime.now().isoformat(),
                "action": "auto_fix",
                "error": str(error),
                "fix_explanation": fix_data["explanation"],
                "old_params": todo.metadata.execution.tool_params,
                "new_params": fix_data["fixed_params"]
            })

            logger.info(f"Auto-fixed todo {todo.id}: {fix_data['explanation']}")

            return {
                "action": "retry_with_fix",
                "updated_todo": updated_todo,
                "updated_todos": [],
                "message": f"Auto-fixed: {fix_data['explanation']}"
            }

        except Exception as e:
            logger.error(f"Auto-fix failed: {e}")
            return {
                "action": "escalate_to_user",
                "reason": f"Auto-fix failed: {e}"
            }

    async def _request_user_intervention(
        self,
        failed_todo: TodoItem,
        error: Exception,
        session_id: str,
        websocket_callback
    ) -> Dict[str, Any]:
        """
        사용자 개입 요청

        WebSocket을 통해 사용자에게 알림
        사용자 결정 대기

        Args:
            failed_todo: 실패한 todo
            error: 에러
            session_id: 세션 ID
            websocket_callback: WebSocket 콜백

        Returns:
            사용자 결정
        """
        # WebSocket으로 사용자에게 알림
        await self._send_failure_notification(
            websocket_callback=websocket_callback,
            session_id=session_id,
            todo=failed_todo,
            error=error
        )

        # 사용자 결정 대기 (최대 5분)
        user_decision = await self._wait_for_user_decision(
            session_id=session_id,
            todo_id=failed_todo.id,
            timeout=300
        )

        return user_decision

    async def _send_failure_notification(
        self,
        websocket_callback,
        session_id: str,
        todo: TodoItem,
        error: Exception
    ):
        """사용자에게 실패 알림"""
        if hasattr(websocket_callback, 'on_todo_failure'):
            await websocket_callback.on_todo_failure(
                todo=todo,
                error=error
            )
        else:
            # 직접 WebSocket 메시지 전송
            await websocket_callback.websocket.send_json({
                "type": "todo_failure",
                "session_id": session_id,
                "todo": {
                    "id": todo.id,
                    "task": todo.task,
                    "layer": todo.layer,
                    "tool": todo.metadata.execution.tool,
                    "params": todo.metadata.execution.tool_params
                },
                "error": {
                    "type": type(error).__name__,
                    "message": str(error),
                    "retry_count": todo.metadata.execution.retry_count
                },
                "options": [
                    {
                        "id": "retry",
                        "label": "재시도",
                        "description": "동일한 설정으로 다시 시도"
                    },
                    {
                        "id": "modify_and_retry",
                        "label": "수정 후 재시도",
                        "description": "파라미터를 수정한 후 재시도",
                        "requires_input": True
                    },
                    {
                        "id": "skip",
                        "label": "건너뛰기",
                        "description": "이 todo를 건너뛰고 다음으로 진행"
                    },
                    {
                        "id": "skip_dependent",
                        "label": "의존 todos도 건너뛰기",
                        "description": "이 todo와 의존하는 모든 todos 건너뛰기"
                    },
                    {
                        "id": "abort",
                        "label": "중단",
                        "description": "전체 작업 중단"
                    }
                ],
                "timestamp": datetime.now().isoformat()
            })

    async def _wait_for_user_decision(
        self,
        session_id: str,
        todo_id: str,
        timeout: int
    ) -> Dict[str, Any]:
        """
        사용자 결정 대기

        Args:
            session_id: 세션 ID
            todo_id: todo ID
            timeout: 타임아웃 (초)

        Returns:
            사용자 결정
        """
        decision_key = f"{session_id}:{todo_id}"

        # 이벤트 생성
        event = asyncio.Event()
        self._pending_decisions[decision_key] = event

        try:
            # 대기
            await asyncio.wait_for(event.wait(), timeout=timeout)

            # 결과 반환
            result = self._decision_results.get(decision_key, {
                "action": "skip",
                "reason": "No decision received"
            })

            return result

        except asyncio.TimeoutError:
            # 타임아웃 시 자동 skip
            logger.warning(f"User decision timeout for {decision_key} - auto-skipping")
            return {
                "action": "skip",
                "reason": "Timeout - auto-skipped"
            }

        finally:
            # 정리
            self._pending_decisions.pop(decision_key, None)
            self._decision_results.pop(decision_key, None)

    def submit_user_decision(
        self,
        session_id: str,
        todo_id: str,
        action: str,
        data: Optional[Dict[str, Any]] = None
    ):
        """
        사용자 결정 제출

        Args:
            session_id: 세션 ID
            todo_id: todo ID
            action: 액션 (retry, modify_and_retry, skip, skip_dependent, abort)
            data: 추가 데이터 (modify_and_retry 시 modified_params)
        """
        decision_key = f"{session_id}:{todo_id}"

        if decision_key not in self._pending_decisions:
            logger.warning(f"No pending decision for {decision_key}")
            return

        # 결과 저장
        self._decision_results[decision_key] = {
            "action": action,
            "data": data or {},
            "timestamp": datetime.now().isoformat()
        }

        # 이벤트 발동
        self._pending_decisions[decision_key].set()

        logger.info(f"User decision received for {decision_key}: {action}")

    async def _handle_user_decision(
        self,
        failed_todo: TodoItem,
        todos: List[TodoItem],
        decision: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        사용자 결정 처리

        Args:
            failed_todo: 실패한 todo
            todos: 전체 todo 리스트
            decision: 사용자 결정

        Returns:
            처리 결과
        """
        action = decision["action"]

        if action == "retry":
            # 재시도
            updated_todo = failed_todo.model_copy(update={
                "status": "pending",
                "version": failed_todo.version + 1
            })

            updated_todo.metadata.progress.error_message = None
            updated_todo.history.append({
                "timestamp": datetime.now().isoformat(),
                "action": "user_retry",
                "reason": decision.get("reason", "User requested retry")
            })

            return {
                "action": "retry",
                "updated_todo": updated_todo,
                "updated_todos": [],
                "message": "사용자가 재시도를 선택했습니다"
            }

        elif action == "modify_and_retry":
            # 수정 후 재시도
            modified_params = decision.get("data", {}).get("modified_params", {})

            updated_todo = failed_todo.model_copy(update={
                "status": "pending",
                "version": failed_todo.version + 1
            })

            updated_todo.metadata.execution.tool_params = modified_params
            updated_todo.metadata.progress.error_message = None

            updated_todo.history.append({
                "timestamp": datetime.now().isoformat(),
                "action": "user_modify_and_retry",
                "old_params": failed_todo.metadata.execution.tool_params,
                "new_params": modified_params
            })

            return {
                "action": "retry",
                "updated_todo": updated_todo,
                "updated_todos": [],
                "message": "파라미터를 수정하여 재시도합니다"
            }

        elif action == "skip":
            # 건너뛰기
            updated_todo = failed_todo.model_copy(update={
                "status": "skipped",
                "version": failed_todo.version + 1
            })

            updated_todo.history.append({
                "timestamp": datetime.now().isoformat(),
                "action": "user_skip",
                "reason": decision.get("reason", "User skipped")
            })

            return {
                "action": "skip",
                "updated_todo": updated_todo,
                "updated_todos": [],
                "message": "이 todo를 건너뛰었습니다"
            }

        elif action == "skip_dependent":
            # Import at function scope to avoid circular dependency
            from backend.app.dream_agent.workflow_manager import TodoDependencyManager

            # 의존 todos도 건너뛰기
            updated_todo = failed_todo.model_copy(update={
                "status": "skipped",
                "version": failed_todo.version + 1
            })

            # 의존하는 todos 찾기 (순환 import 방지를 위해 지연 import)
            from backend.app.dream_agent.workflow_manager import TodoDependencyManager
            dependent_todos = TodoDependencyManager.get_dependent_todos(
                todos, failed_todo.id
            )

            # 모두 skipped로 변경
            updated_todos = []
            for dep_todo in dependent_todos:
                updated_dep = dep_todo.model_copy(update={
                    "status": "skipped",
                    "version": dep_todo.version + 1
                })

                updated_dep.metadata.progress.error_message = (
                    f"Skipped: dependency {failed_todo.id} was skipped"
                )

                updated_dep.history.append({
                    "timestamp": datetime.now().isoformat(),
                    "action": "auto_skip_dependent",
                    "reason": f"Dependency {failed_todo.id} was skipped by user"
                })

                updated_todos.append(updated_dep)

            return {
                "action": "skip",
                "updated_todo": updated_todo,
                "updated_todos": updated_todos,
                "message": f"이 todo와 의존하는 {len(updated_todos)}개 todos를 건너뛰었습니다"
            }

        elif action == "abort":
            # 전체 중단
            return {
                "action": "abort",
                "updated_todo": failed_todo,
                "updated_todos": [],
                "message": "사용자가 전체 작업을 중단했습니다"
            }

        else:
            # 알 수 없는 액션
            logger.error(f"Unknown action: {action}")
            return {
                "action": "skip",
                "updated_todo": failed_todo,
                "updated_todos": [],
                "message": f"알 수 없는 액션: {action}"
            }


# 글로벌 인스턴스
todo_failure_recovery = TodoFailureRecovery()
