"""Replan Manager - LLM 기반 계획 수정 관리

사용자의 자연어 지시를 받아 LLM을 통해 todos를 수정합니다.

Usage:
    replan_manager = ReplanManager()
    result = await replan_manager.replan(
        session_id="abc123",
        user_instruction="2번 작업 삭제해줘",
        current_plan={"plan_description": "..."},
        current_todos=[...]
    )
"""

import json
from typing import Dict, Any, List, Optional
from datetime import datetime

from backend.app.core.logging import get_logger, LogContext
from backend.app.dream_agent.states import TodoItem
from backend.app.dream_agent.workflow_manager.todo_manager import create_todo, todo_store
from backend.app.dream_agent.llm_manager import (
    get_llm_client,
    REPLAN_SYSTEM_PROMPT,
    format_replan_prompt
)

logger = get_logger(__name__)


class ReplanResult:
    """Replan 결과"""

    def __init__(
        self,
        success: bool,
        modified_todos: List[TodoItem],
        modification_summary: str,
        changes: Dict[str, List[str]],
        error: Optional[str] = None
    ):
        self.success = success
        self.modified_todos = modified_todos
        self.modification_summary = modification_summary
        self.changes = changes  # {"added": [], "removed": [], "modified": []}
        self.error = error
        self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "modified_todos": [
                todo.model_dump(mode='json') if hasattr(todo, 'model_dump') else todo
                for todo in self.modified_todos
            ],
            "modification_summary": self.modification_summary,
            "changes": self.changes,
            "error": self.error,
            "timestamp": self.timestamp
        }


class ReplanManager:
    """
    계획 수정 관리자

    LLM을 사용하여 사용자의 자연어 지시에 따라 todos를 수정합니다.
    """

    def __init__(self):
        self.llm_client = None

    def _get_llm_client(self):
        """LLM 클라이언트 lazy loading"""
        if self.llm_client is None:
            self.llm_client = get_llm_client()
        return self.llm_client

    async def replan(
        self,
        session_id: str,
        user_instruction: str,
        current_plan: Optional[Dict[str, Any]] = None,
        current_todos: Optional[List[TodoItem]] = None,
        save_to_store: bool = True
    ) -> ReplanResult:
        """
        계획 수정 실행

        Args:
            session_id: 세션 ID
            user_instruction: 사용자의 수정 지시
            current_plan: 현재 계획 (없으면 빈 dict)
            current_todos: 현재 todos (없으면 TodoStore에서 로드)
            save_to_store: 수정 후 TodoStore에 저장 여부

        Returns:
            ReplanResult: 수정 결과
        """
        log = LogContext(logger, node="replan", session_id=session_id)
        log.info(f"Starting replan with instruction: {user_instruction[:100]}...")

        # 현재 todos 로드 (없으면 store에서)
        if current_todos is None:
            current_todos = todo_store.load_todos(session_id) or []
            log.info(f"Loaded {len(current_todos)} todos from store")

        if current_plan is None:
            current_plan = {}

        # LLM 호출
        try:
            llm_client = self._get_llm_client()
            prompt = format_replan_prompt(current_plan, current_todos, user_instruction)

            log.debug("Calling LLM for replan")
            response = await llm_client.chat_with_system(
                system_prompt=REPLAN_SYSTEM_PROMPT,
                user_message=prompt,
                max_tokens=2000
            )

            # JSON 파싱
            replan_data = json.loads(response)

            modification_summary = replan_data.get("modification_summary", "Plan modified")
            changes = replan_data.get("changes", {"added": [], "removed": [], "modified": []})
            modified_todos_data = replan_data.get("modified_todos", [])

            # TodoItem으로 변환
            modified_todos = self._convert_to_todo_items(modified_todos_data, current_todos)

            log.info(f"Replan completed: {modification_summary}")
            log.info(f"Changes - Added: {len(changes.get('added', []))}, "
                    f"Removed: {len(changes.get('removed', []))}, "
                    f"Modified: {len(changes.get('modified', []))}")

            # TodoStore에 저장
            if save_to_store and modified_todos:
                todo_store.save_todos(session_id, modified_todos, backup=True)
                log.info(f"Saved {len(modified_todos)} modified todos to store")

            return ReplanResult(
                success=True,
                modified_todos=modified_todos,
                modification_summary=modification_summary,
                changes=changes
            )

        except json.JSONDecodeError as e:
            log.error(f"Replan JSON parsing error: {e}")
            return ReplanResult(
                success=False,
                modified_todos=current_todos,
                modification_summary="JSON parsing error",
                changes={"added": [], "removed": [], "modified": []},
                error=f"Failed to parse LLM response: {str(e)}"
            )

        except Exception as e:
            log.error(f"Replan error: {e}", exc_info=True)
            return ReplanResult(
                success=False,
                modified_todos=current_todos,
                modification_summary="Replan failed",
                changes={"added": [], "removed": [], "modified": []},
                error=str(e)
            )

    def _convert_to_todo_items(
        self,
        todos_data: List[Dict[str, Any]],
        original_todos: List[TodoItem]
    ) -> List[TodoItem]:
        """
        LLM 응답을 TodoItem 리스트로 변환

        기존 todo는 ID로 매칭하여 업데이트하고,
        새로운 todo는 create_todo로 생성합니다.

        Args:
            todos_data: LLM이 반환한 todo dict 리스트
            original_todos: 원본 TodoItem 리스트

        Returns:
            List[TodoItem]: 변환된 TodoItem 리스트
        """
        # 원본 todo를 ID로 인덱싱
        original_map = {todo.id: todo for todo in original_todos}

        result = []
        for todo_dict in todos_data:
            todo_id = todo_dict.get("id")

            # 기존 todo인 경우 업데이트
            if todo_id and todo_id in original_map:
                original_todo = original_map[todo_id]

                # 업데이트 가능한 필드들
                update_data = {}
                if "task" in todo_dict:
                    update_data["task"] = todo_dict["task"]
                if "status" in todo_dict:
                    update_data["status"] = todo_dict["status"]
                if "priority" in todo_dict:
                    update_data["priority"] = todo_dict["priority"]

                if update_data:
                    updated_todo = original_todo.model_copy(update=update_data)
                    result.append(updated_todo)
                else:
                    result.append(original_todo)

            # 새로운 todo인 경우 생성
            else:
                metadata_dict = todo_dict.get("metadata", {})

                new_todo = create_todo(
                    task=todo_dict.get("task", "New task"),
                    layer=todo_dict.get("layer", "ml_execution"),
                    priority=todo_dict.get("priority", 5),
                    tool=metadata_dict.get("tool"),
                    tool_params=metadata_dict.get("tool_params", {}),
                    depends_on=metadata_dict.get("depends_on", []),
                    output_path=metadata_dict.get("output_path")
                )
                result.append(new_todo)

        return result

    async def load_and_replan(
        self,
        session_id: str,
        user_instruction: str
    ) -> ReplanResult:
        """
        TodoStore에서 로드하여 수정 (간편 메서드)

        Args:
            session_id: 세션 ID
            user_instruction: 사용자의 수정 지시

        Returns:
            ReplanResult: 수정 결과
        """
        return await self.replan(
            session_id=session_id,
            user_instruction=user_instruction,
            current_plan=None,
            current_todos=None,
            save_to_store=True
        )


# ============================================================
# Global Instance
# ============================================================

_replan_manager: Optional[ReplanManager] = None


def get_replan_manager() -> ReplanManager:
    """전역 ReplanManager 인스턴스 반환"""
    global _replan_manager
    if _replan_manager is None:
        _replan_manager = ReplanManager()
    return _replan_manager


# 편의를 위한 전역 인스턴스
replan_manager = get_replan_manager()
