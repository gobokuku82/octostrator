"""Todo Updater - Todo 상태 업데이트"""

from typing import List, Literal, Optional
from datetime import datetime
from backend.app.dream_agent.models.todo import TodoItem


def update_todo_status(
    todos: List[TodoItem],
    todo_id: str,
    status: Literal["pending", "in_progress", "completed", "failed", "blocked", "skipped", "needs_approval", "cancelled"],
    error_message: Optional[str] = None
) -> List[TodoItem]:
    """
    Todo 상태 업데이트 헬퍼 함수 V2.1

    Args:
        todos: Todo 리스트
        todo_id: 업데이트할 todo ID
        status: 새 상태
        error_message: 에러 메시지 (failed 상태일 때)

    Returns:
        전체 todo 리스트 (업데이트된 todo 포함)
    """
    result = []
    for todo in todos:
        if todo.id == todo_id:
            # History 추가
            history_entry = {
                "timestamp": datetime.now().isoformat(),
                "action": "status_change",
                "old_status": todo.status,
                "new_status": status
            }

            if error_message:
                history_entry["error"] = error_message

            updated = todo.model_copy(update={
                "status": status,
                "version": todo.version + 1,
                "updated_at": datetime.now()
            })

            updated.history.append(history_entry)

            # Progress 업데이트
            if status == "in_progress":
                updated.metadata.progress.started_at = datetime.now()
            elif status == "completed":
                updated.metadata.progress.completed_at = datetime.now()
                updated.metadata.progress.progress_percentage = 100
            elif status == "failed":
                updated.metadata.progress.error_message = error_message
            elif status == "needs_approval":
                # 승인 대기 상태 - approval 메타데이터 업데이트
                updated.metadata.approval.requires_approval = True
            elif status == "cancelled":
                # 취소 상태 - 완료 시간 기록
                updated.metadata.progress.completed_at = datetime.now()

            result.append(updated)
        else:
            # 변경되지 않은 todo는 그대로 유지
            result.append(todo)

    return result
