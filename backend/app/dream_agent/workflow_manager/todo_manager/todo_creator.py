"""Todo Creator - Todo 생성 로직"""

from typing import Literal, Optional, List, Dict, Any
from backend.app.dream_agent.models.todo import (
    TodoItem,
    TodoMetadata
)


def create_todo(
    task: str,
    layer: Literal["cognitive", "planning", "ml_execution", "biz_execution", "response"],
    task_type: str = "general",
    priority: int = 5,
    parent_id: Optional[str] = None,
    metadata: Optional[TodoMetadata] = None,
    tool: Optional[str] = None,
    tool_params: Optional[Dict[str, Any]] = None,
    depends_on: Optional[List[str]] = None,
    output_path: Optional[str] = None
) -> TodoItem:
    """
    Todo 생성 헬퍼 함수 V2.0

    Args:
        task: 작업 설명
        layer: 실행 레이어
        task_type: 작업 타입
        priority: 우선순위 (0-10)
        parent_id: 상위 todo ID
        metadata: TodoMetadata (제공되면 사용)
        tool: 실행 도구 (metadata가 없을 때)
        tool_params: 도구 파라미터
        depends_on: 의존하는 todo IDs
        output_path: 출력 경로

    Returns:
        TodoItem
    """
    if metadata is None:
        # metadata 자동 생성
        metadata = TodoMetadata()

        if tool:
            metadata.execution.tool = tool

        if tool_params:
            metadata.execution.tool_params = tool_params

        if depends_on:
            metadata.dependency.depends_on = depends_on

        if output_path:
            metadata.data.output_path = output_path

    return TodoItem(
        task=task,
        task_type=task_type,
        layer=layer,
        priority=priority,
        parent_id=parent_id,
        metadata=metadata
    )


def create_ml_todo(
    task: str,
    tool: str,
    priority: int = 5,
    tool_params: Optional[Dict[str, Any]] = None,
    output_path: Optional[str] = None,
    depends_on: Optional[List[str]] = None
) -> TodoItem:
    """ML Execution Todo 생성 헬퍼"""
    return create_todo(
        task=task,
        task_type=f"ml_{tool}",
        layer="ml_execution",
        priority=priority,
        tool=tool,
        tool_params=tool_params or {},
        output_path=output_path,
        depends_on=depends_on or []
    )


def create_biz_todo(
    task: str,
    tool: str,
    priority: int = 5,
    input_data: Optional[Dict[str, Any]] = None,
    requires_approval: bool = False,
    depends_on: Optional[List[str]] = None
) -> TodoItem:
    """Biz Execution Todo 생성 헬퍼"""
    metadata = TodoMetadata()
    metadata.execution.tool = tool
    metadata.approval.requires_approval = requires_approval
    metadata.dependency.depends_on = depends_on or []

    if input_data:
        metadata.data.input_data = input_data

    return TodoItem(
        task=task,
        task_type=f"biz_{tool}",
        layer="biz_execution",
        priority=priority,
        metadata=metadata
    )


def create_todo_legacy(
    task: str,
    layer: Literal["cognitive", "planning", "ml_execution", "biz_execution", "response"],
    priority: int = 0,
    parent_id: Optional[str] = None,
    metadata: Optional[dict] = None
) -> TodoItem:
    """
    기존 create_todo 호환 함수

    metadata dict를 TodoMetadata로 변환
    """
    todo_metadata = TodoMetadata()

    if metadata:
        # dict에서 TodoMetadata 필드 추출
        if "tool" in metadata:
            todo_metadata.execution.tool = metadata["tool"]

        if "tool_params" in metadata:
            todo_metadata.execution.tool_params = metadata["tool_params"]

        if "source" in metadata:
            # collector 등에서 사용하는 source
            todo_metadata.execution.tool_params["source"] = metadata["source"]

        if "depends_on" in metadata:
            todo_metadata.dependency.depends_on = metadata["depends_on"]

        if "output_path" in metadata:
            todo_metadata.data.output_path = metadata["output_path"]

        # 기타 필드는 context에 저장
        for key, value in metadata.items():
            if key not in ["tool", "tool_params", "source", "depends_on", "output_path"]:
                todo_metadata.context[key] = value

    return TodoItem(
        task=task,
        layer=layer,
        priority=priority,
        parent_id=parent_id,
        metadata=todo_metadata
    )
