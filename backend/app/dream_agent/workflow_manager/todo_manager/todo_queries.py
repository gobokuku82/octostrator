"""Todo Queries - Todo 조회 헬퍼 함수들"""

from typing import List, Optional
from backend.app.dream_agent.models.todo import TodoItem


def get_pending_todos(todos: List[TodoItem], layer: Optional[str] = None) -> List[TodoItem]:
    """
    대기 중인 Todo 조회

    Args:
        todos: Todo 리스트
        layer: 필터링할 레이어 (None이면 전체)

    Returns:
        pending 상태의 todos (우선순위 순)
    """
    result = [t for t in todos if t.status == "pending"]
    if layer:
        result = [t for t in result if t.layer == layer]
    return sorted(result, key=lambda x: -x.priority)


def get_in_progress_todos(todos: List[TodoItem], layer: Optional[str] = None) -> List[TodoItem]:
    """진행 중인 Todo 조회"""
    result = [t for t in todos if t.status == "in_progress"]
    if layer:
        result = [t for t in result if t.layer == layer]
    return result


def get_completed_todos(todos: List[TodoItem], layer: Optional[str] = None) -> List[TodoItem]:
    """완료된 Todo 조회"""
    result = [t for t in todos if t.status == "completed"]
    if layer:
        result = [t for t in result if t.layer == layer]
    return result


def get_failed_todos(todos: List[TodoItem], layer: Optional[str] = None) -> List[TodoItem]:
    """실패한 Todo 조회"""
    result = [t for t in todos if t.status == "failed"]
    if layer:
        result = [t for t in result if t.layer == layer]
    return result
