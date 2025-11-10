"""Todo Management API

Phase 2: Todo 관리 API (2025-11-06)
런타임에 Todo를 추가/수정/삭제하는 API
"""
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.app.octostrator.checkpointer import create_checkpointer
from backend.app.octostrator.session import get_session_config
from backend.app.octostrator.supervisors.octostrator.octostrator_graph import build_octostrator_graph as build_supervisor_graph


router = APIRouter(prefix="/api/sessions", tags=["todos"])


# === Request/Response Models ===

class TodoCreateRequest(BaseModel):
    """Todo 생성 요청"""
    task: str
    agent: str
    priority: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None


class TodoUpdateRequest(BaseModel):
    """Todo 업데이트 요청"""
    task: Optional[str] = None
    agent: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None


class TodoReorderRequest(BaseModel):
    """Todo 순서 변경 요청"""
    todo_ids: List[str]  # 새로운 순서대로 나열된 todo_id 리스트


class AgentChangeRequest(BaseModel):
    """Agent 변경 요청"""
    new_agent: str
    reason: Optional[str] = None


# === Todo Management Endpoints ===

@router.post("/{thread_id}/todos")
async def add_todo(thread_id: str, request: TodoCreateRequest):
    """Todo 추가 (Phase 2)

    런타임에 새로운 Todo를 추가합니다.

    Args:
        thread_id: 세션 thread_id
        request: Todo 생성 정보

    Returns:
        dict: 생성된 Todo 정보

    Raises:
        HTTPException: 세션을 찾을 수 없거나 생성 실패 시
    """
    try:
        # Checkpointer 생성
        checkpointer = await create_checkpointer()

        # Graph 빌드
        graph = build_supervisor_graph(checkpointer=checkpointer)

        # Config 생성
        config = get_session_config(thread_id)

        # 현재 상태 조회
        current_state = await graph.aget_state(config)

        if not current_state.values:
            raise HTTPException(status_code=404, detail=f"Session not found: {thread_id}")

        # 새 Todo 생성 (merge_todos_smart reducer가 ID, step 등 자동 처리)
        new_todo = {
            "task": request.task,
            "agent": request.agent,
            "status": "pending"
        }

        if request.priority is not None:
            new_todo["priority"] = request.priority

        if request.metadata is not None:
            new_todo["metadata"] = request.metadata

        # State 업데이트 (reducer가 자동으로 ID, step, created_at 등 추가)
        await graph.aupdate_state(config, {"todos": [new_todo]})

        # user_interactions에 기록
        interaction = {
            "type": "modify_todo",
            "details": {
                "action": "add",
                "task": request.task,
                "agent": request.agent
            }
        }
        await graph.aupdate_state(config, {"user_interactions": [interaction]})

        # 업데이트된 상태 조회하여 생성된 Todo 반환
        updated_state = await graph.aget_state(config)
        todos = updated_state.values.get("todos", [])
        created_todo = todos[-1] if todos else new_todo  # 마지막에 추가된 todo

        return {
            "success": True,
            "todo": created_todo
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to add todo: {str(e)}"
        )


@router.delete("/{thread_id}/todos/{todo_id}")
async def delete_todo(thread_id: str, todo_id: str):
    """Todo 삭제 (Phase 2)

    Args:
        thread_id: 세션 thread_id
        todo_id: 삭제할 todo의 ID

    Returns:
        dict: 삭제 결과

    Raises:
        HTTPException: Todo를 찾을 수 없거나 삭제 실패 시
    """
    try:
        # Checkpointer 생성
        checkpointer = await create_checkpointer()

        # Graph 빌드
        graph = build_supervisor_graph(checkpointer=checkpointer)

        # Config 생성
        config = get_session_config(thread_id)

        # 현재 상태 조회
        current_state = await graph.aget_state(config)

        if not current_state.values:
            raise HTTPException(status_code=404, detail=f"Session not found: {thread_id}")

        # 현재 todos 가져오기
        todos = current_state.values.get("todos", [])

        # 삭제할 todo 찾기
        todo_to_delete = None
        filtered_todos = []
        for todo in todos:
            if todo.get("id") == todo_id:
                todo_to_delete = todo
            else:
                filtered_todos.append(todo)

        if not todo_to_delete:
            raise HTTPException(status_code=404, detail=f"Todo not found: {todo_id}")

        # State 업데이트 (필터링된 todos로 교체)
        await graph.aupdate_state(config, {"todos": filtered_todos})

        # user_interactions에 기록
        interaction = {
            "type": "modify_todo",
            "details": {
                "action": "delete",
                "todo_id": todo_id,
                "task": todo_to_delete.get("task", "")
            }
        }
        await graph.aupdate_state(config, {"user_interactions": [interaction]})

        return {
            "success": True,
            "message": f"Todo {todo_id} deleted successfully",
            "deleted_todo": todo_to_delete
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete todo: {str(e)}"
        )


@router.put("/{thread_id}/todos/{todo_id}")
async def update_todo(thread_id: str, todo_id: str, request: TodoUpdateRequest):
    """Todo 수정 (Phase 2)

    Args:
        thread_id: 세션 thread_id
        todo_id: 수정할 todo의 ID
        request: 수정할 내용

    Returns:
        dict: 수정된 Todo 정보

    Raises:
        HTTPException: Todo를 찾을 수 없거나 수정 실패 시
    """
    try:
        # Checkpointer 생성
        checkpointer = await create_checkpointer()

        # Graph 빌드
        graph = build_supervisor_graph(checkpointer=checkpointer)

        # Config 생성
        config = get_session_config(thread_id)

        # 현재 상태 조회
        current_state = await graph.aget_state(config)

        if not current_state.values:
            raise HTTPException(status_code=404, detail=f"Session not found: {thread_id}")

        # 수정할 todo 생성 (merge_todos_smart가 기존 todo와 병합)
        todo_update = {"id": todo_id}

        if request.task is not None:
            todo_update["task"] = request.task
        if request.agent is not None:
            todo_update["agent"] = request.agent
        if request.status is not None:
            todo_update["status"] = request.status
        if request.priority is not None:
            todo_update["priority"] = request.priority
        if request.metadata is not None:
            todo_update["metadata"] = request.metadata

        # State 업데이트 (reducer가 자동 병합)
        await graph.aupdate_state(config, {"todos": [todo_update]})

        # user_interactions에 기록
        interaction = {
            "type": "modify_todo",
            "details": {
                "action": "update",
                "todo_id": todo_id,
                "updates": todo_update
            }
        }
        await graph.aupdate_state(config, {"user_interactions": [interaction]})

        # 업데이트된 todo 조회
        updated_state = await graph.aget_state(config)
        todos = updated_state.values.get("todos", [])
        updated_todo = next((t for t in todos if t.get("id") == todo_id), None)

        if not updated_todo:
            raise HTTPException(status_code=404, detail=f"Todo not found after update: {todo_id}")

        return {
            "success": True,
            "todo": updated_todo
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update todo: {str(e)}"
        )


@router.put("/{thread_id}/todos/reorder")
async def reorder_todos(thread_id: str, request: TodoReorderRequest):
    """Todo 순서 변경 (Phase 2)

    Args:
        thread_id: 세션 thread_id
        request: 새로운 순서의 todo_id 리스트

    Returns:
        dict: 재정렬된 Todo 리스트

    Raises:
        HTTPException: 세션을 찾을 수 없거나 재정렬 실패 시
    """
    try:
        # Checkpointer 생성
        checkpointer = await create_checkpointer()

        # Graph 빌드
        graph = build_supervisor_graph(checkpointer=checkpointer)

        # Config 생성
        config = get_session_config(thread_id)

        # 현재 상태 조회
        current_state = await graph.aget_state(config)

        if not current_state.values:
            raise HTTPException(status_code=404, detail=f"Session not found: {thread_id}")

        # 현재 todos 가져오기
        current_todos = current_state.values.get("todos", [])

        # todo_id로 인덱싱
        todo_dict = {todo["id"]: todo for todo in current_todos if "id" in todo}

        # 새 순서대로 재정렬 및 step 재할당
        reordered_todos = []
        for new_step, todo_id in enumerate(request.todo_ids, start=1):
            if todo_id not in todo_dict:
                raise HTTPException(status_code=404, detail=f"Todo not found: {todo_id}")

            todo = todo_dict[todo_id].copy()
            todo["step"] = new_step
            reordered_todos.append(todo)

        # State 업데이트 (전체 todos 교체)
        await graph.aupdate_state(config, {"todos": reordered_todos})

        # user_interactions에 기록
        interaction = {
            "type": "modify_todo",
            "details": {
                "action": "reorder",
                "count": len(reordered_todos)
            }
        }
        await graph.aupdate_state(config, {"user_interactions": [interaction]})

        return {
            "success": True,
            "message": f"Reordered {len(reordered_todos)} todos",
            "todos": reordered_todos
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to reorder todos: {str(e)}"
        )


@router.post("/{thread_id}/retry/{todo_id}")
async def retry_todo(thread_id: str, todo_id: str):
    """Todo 재시도 (Phase 2)

    실패한 Todo를 pending 상태로 되돌려 재시도합니다.

    Args:
        thread_id: 세션 thread_id
        todo_id: 재시도할 todo의 ID

    Returns:
        dict: 재시도된 Todo 정보

    Raises:
        HTTPException: Todo를 찾을 수 없거나 재시도 불가 시
    """
    try:
        # Checkpointer 생성
        checkpointer = await create_checkpointer()

        # Graph 빌드
        graph = build_supervisor_graph(checkpointer=checkpointer)

        # Config 생성
        config = get_session_config(thread_id)

        # 현재 상태 조회
        current_state = await graph.aget_state(config)

        if not current_state.values:
            raise HTTPException(status_code=404, detail=f"Session not found: {thread_id}")

        # 현재 todos에서 해당 todo 찾기
        todos = current_state.values.get("todos", [])
        target_todo = next((t for t in todos if t.get("id") == todo_id), None)

        if not target_todo:
            raise HTTPException(status_code=404, detail=f"Todo not found: {todo_id}")

        # failed 또는 skipped 상태만 재시도 가능
        current_status = target_todo.get("status", "")
        if current_status not in ["failed", "skipped"]:
            raise HTTPException(
                status_code=400,
                detail=f"Todo cannot be retried (current status: {current_status})"
            )

        # retry_count 증가 및 상태 변경
        retry_count = target_todo.get("retry_count", 0) + 1
        todo_update = {
            "id": todo_id,
            "status": "pending",
            "retry_count": retry_count,
            "error": None  # 이전 에러 메시지 제거
        }

        # State 업데이트
        await graph.aupdate_state(config, {"todos": [todo_update]})

        # user_interactions에 기록
        interaction = {
            "type": "retry",
            "details": {
                "todo_id": todo_id,
                "task": target_todo.get("task", ""),
                "retry_count": retry_count
            }
        }
        await graph.aupdate_state(config, {"user_interactions": [interaction]})

        # 업데이트된 todo 조회
        updated_state = await graph.aget_state(config)
        todos = updated_state.values.get("todos", [])
        retried_todo = next((t for t in todos if t.get("id") == todo_id), None)

        return {
            "success": True,
            "message": f"Todo {todo_id} reset to pending for retry",
            "todo": retried_todo,
            "retry_count": retry_count
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retry todo: {str(e)}"
        )


@router.put("/{thread_id}/todos/{todo_id}/agent")
async def change_todo_agent(thread_id: str, todo_id: str, request: AgentChangeRequest):
    """Todo의 Agent 변경 (Phase 2)

    Args:
        thread_id: 세션 thread_id
        todo_id: Agent를 변경할 todo의 ID
        request: 새로운 Agent 정보

    Returns:
        dict: 변경된 Todo 정보

    Raises:
        HTTPException: Todo를 찾을 수 없거나 변경 실패 시
    """
    try:
        # Checkpointer 생성
        checkpointer = await create_checkpointer()

        # Graph 빌드
        graph = build_supervisor_graph(checkpointer=checkpointer)

        # Config 생성
        config = get_session_config(thread_id)

        # 현재 상태 조회
        current_state = await graph.aget_state(config)

        if not current_state.values:
            raise HTTPException(status_code=404, detail=f"Session not found: {thread_id}")

        # 현재 todos에서 해당 todo 찾기
        todos = current_state.values.get("todos", [])
        target_todo = next((t for t in todos if t.get("id") == todo_id), None)

        if not target_todo:
            raise HTTPException(status_code=404, detail=f"Todo not found: {todo_id}")

        old_agent = target_todo.get("agent", "")

        # Agent 변경
        todo_update = {
            "id": todo_id,
            "agent": request.new_agent
        }

        # State 업데이트
        await graph.aupdate_state(config, {"todos": [todo_update]})

        # user_interactions에 기록
        interaction = {
            "type": "change_agent",
            "details": {
                "todo_id": todo_id,
                "task": target_todo.get("task", ""),
                "old_agent": old_agent,
                "new_agent": request.new_agent,
                "reason": request.reason
            }
        }
        await graph.aupdate_state(config, {"user_interactions": [interaction]})

        # 업데이트된 todo 조회
        updated_state = await graph.aget_state(config)
        todos = updated_state.values.get("todos", [])
        updated_todo = next((t for t in todos if t.get("id") == todo_id), None)

        return {
            "success": True,
            "message": f"Agent changed from {old_agent} to {request.new_agent}",
            "todo": updated_todo
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to change agent: {str(e)}"
        )
