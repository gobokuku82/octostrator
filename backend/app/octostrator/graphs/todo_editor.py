"""TODO Editor - Natural Language TODO Editing"""

from typing import List, Dict, Any, Optional
from uuid import UUID
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from loguru import logger
import json
import re

from backend.schema.todo import TodoItem, TodoStatus, TodoPriority


class TodoEditor:
    """자연어로 TODO 편집"""

    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.1,  # 정확한 편집을 위해 매우 낮은 temperature
        )

    async def edit_todos(
        self,
        todos: List[TodoItem],
        edit_command: str
    ) -> Dict[str, Any]:
        """자연어 명령으로 TODO 편집

        Args:
            todos: 현재 TODO 리스트
            edit_command: 자연어 편집 명령

        Returns:
            편집 결과 딕셔너리
        """

        # TODO 리스트를 텍스트로 변환
        todos_text = self._todos_to_text(todos)

        system_prompt = f"""당신은 TODO 리스트 편집 전문가입니다.

현재 TODO 리스트:
{todos_text}

사용자의 편집 명령을 분석하여 다음 작업을 수행하세요:
1. 어떤 TODO를 편집해야 하는지 식별
2. 어떤 속성을 변경해야 하는지 파악
3. 변경 내용을 정확히 적용

편집 가능한 속성:
- title: TODO 제목
- description: 설명
- priority: 우선순위 (high, medium, low)
- estimated_time_minutes: 예상 소요 시간 (분)
- status: 상태 (pending, in_progress, completed, failed)

응답 형식 (JSON):
{{
    "action": "edit" | "delete" | "add" | "reorder",
    "target_indices": [편집할 TODO의 인덱스들 (0부터 시작)],
    "changes": {{
        "title": "새 제목" (선택),
        "description": "새 설명" (선택),
        "priority": "high|medium|low" (선택),
        "estimated_time_minutes": 숫자 (선택),
        "status": "pending|in_progress|completed|failed" (선택)
    }},
    "reason": "변경 사유 설명"
}}

예시:
- "첫 번째 TODO 삭제" → {{"action": "delete", "target_indices": [0]}}
- "데이터 수집 우선순위를 높여줘" → {{"action": "edit", "target_indices": [해당 인덱스], "changes": {{"priority": "high"}}}}
- "보고서 작성 시간을 2시간으로 변경" → {{"action": "edit", "target_indices": [해당 인덱스], "changes": {{"estimated_time_minutes": 120}}}}
"""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=edit_command)
        ]

        try:
            response = await self.llm.ainvoke(messages)
            logger.debug(f"Edit command parsed: {response.content}")

            # JSON 추출
            json_match = re.search(r'\{[\s\S]*\}', response.content)
            if not json_match:
                return {
                    "success": False,
                    "error": "Could not parse edit command",
                    "todos": todos
                }

            edit_info = json.loads(json_match.group())

            # 편집 수행
            edited_todos = self._apply_edits(todos, edit_info)

            return {
                "success": True,
                "action": edit_info.get("action"),
                "todos": edited_todos,
                "reason": edit_info.get("reason", ""),
                "changes_count": len(edit_info.get("target_indices", []))
            }

        except Exception as e:
            logger.error(f"Error editing TODOs: {e}")
            return {
                "success": False,
                "error": str(e),
                "todos": todos
            }

    def _todos_to_text(self, todos: List[TodoItem]) -> str:
        """TODO 리스트를 읽기 쉬운 텍스트로 변환"""
        if not todos:
            return "TODO 리스트가 비어있습니다."

        text = []
        for i, todo in enumerate(todos):
            text.append(f"{i}. [{todo.priority.value.upper()}] {todo.title}")
            text.append(f"   설명: {todo.description}")
            text.append(f"   예상 시간: {todo.estimated_time_minutes}분")
            text.append(f"   상태: {todo.status.value}")
            if todo.dependencies:
                deps = [str(dep) for dep in todo.dependencies]
                text.append(f"   의존성: {', '.join(deps)}")
            text.append("")

        return "\n".join(text)

    def _apply_edits(
        self,
        todos: List[TodoItem],
        edit_info: Dict[str, Any]
    ) -> List[TodoItem]:
        """편집 정보를 실제 TODO에 적용"""
        action = edit_info.get("action")
        target_indices = edit_info.get("target_indices", [])
        changes = edit_info.get("changes", {})

        # 원본 복사
        edited_todos = todos.copy()

        if action == "delete":
            # 삭제 (역순으로 삭제하여 인덱스 문제 방지)
            for idx in sorted(target_indices, reverse=True):
                if 0 <= idx < len(edited_todos):
                    deleted = edited_todos.pop(idx)
                    logger.info(f"Deleted TODO: {deleted.title}")

        elif action == "edit":
            # 편집
            for idx in target_indices:
                if 0 <= idx < len(edited_todos):
                    todo = edited_todos[idx]

                    if "title" in changes:
                        todo.title = changes["title"]
                    if "description" in changes:
                        todo.description = changes["description"]
                    if "priority" in changes:
                        priority_map = {
                            "high": TodoPriority.HIGH,
                            "medium": TodoPriority.MEDIUM,
                            "low": TodoPriority.LOW
                        }
                        todo.priority = priority_map.get(
                            changes["priority"].lower(),
                            todo.priority
                        )
                    if "estimated_time_minutes" in changes:
                        todo.estimated_time_minutes = int(changes["estimated_time_minutes"])
                    if "status" in changes:
                        status_map = {
                            "pending": TodoStatus.PENDING,
                            "in_progress": TodoStatus.IN_PROGRESS,
                            "completed": TodoStatus.COMPLETED,
                            "failed": TodoStatus.FAILED
                        }
                        todo.status = status_map.get(
                            changes["status"].lower(),
                            todo.status
                        )

                    logger.info(f"Edited TODO: {todo.title}")

        elif action == "add":
            # 새 TODO 추가
            if changes:
                new_todo = TodoItem(
                    title=changes.get("title", "New Task"),
                    description=changes.get("description", ""),
                    priority=self._parse_priority(changes.get("priority", "medium")),
                    estimated_time_minutes=changes.get("estimated_time_minutes", 30),
                    status=TodoStatus.PENDING
                )
                edited_todos.append(new_todo)
                logger.info(f"Added new TODO: {new_todo.title}")

        elif action == "reorder":
            # TODO 순서 변경 (간단한 구현)
            if len(target_indices) == 2:
                idx1, idx2 = target_indices
                if 0 <= idx1 < len(edited_todos) and 0 <= idx2 < len(edited_todos):
                    edited_todos[idx1], edited_todos[idx2] = \
                        edited_todos[idx2], edited_todos[idx1]
                    logger.info(f"Reordered TODOs: {idx1} <-> {idx2}")

        return edited_todos

    def _parse_priority(self, priority_str: str) -> TodoPriority:
        """우선순위 문자열을 TodoPriority로 변환"""
        priority_map = {
            "high": TodoPriority.HIGH,
            "medium": TodoPriority.MEDIUM,
            "low": TodoPriority.LOW
        }
        return priority_map.get(priority_str.lower(), TodoPriority.MEDIUM)


# 편의 함수
async def edit_todos_with_natural_language(
    todos: List[TodoItem],
    command: str
) -> Dict[str, Any]:
    """자연어로 TODO 편집 (편의 함수)"""
    editor = TodoEditor()
    return await editor.edit_todos(todos, command)
