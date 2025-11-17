"""TODO API endpoints"""

from typing import List, Optional, Dict
from uuid import UUID, uuid4
from fastapi import APIRouter, HTTPException, Query
from loguru import logger

from backend.schema.todo import (
    TodoCreate,
    TodoUpdate,
    TodoItem,
    TodoResponse,
    TodoListResponse,
    TodoStatus,
    TodoPriority
)
from backend.schema.response import SuccessResponse, ErrorResponse

router = APIRouter()

# In-memory storage for now (replace with database later)
todos_storage: Dict[str, TodoItem] = {}


@router.get("/todos", response_model=TodoListResponse)
async def get_todos(
    thread_id: Optional[str] = Query(None),
    status: Optional[TodoStatus] = Query(None),
    priority: Optional[TodoPriority] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100)
):
    """Get todos with filtering and pagination"""
    try:
        # Filter todos
        filtered_todos = list(todos_storage.values())

        if thread_id:
            filtered_todos = [t for t in filtered_todos if t.thread_id == thread_id]
        if status:
            filtered_todos = [t for t in filtered_todos if t.status == status]
        if priority:
            filtered_todos = [t for t in filtered_todos if t.priority == priority]

        # Pagination
        total = len(filtered_todos)
        start = (page - 1) * page_size
        end = start + page_size
        paginated_todos = filtered_todos[start:end]

        return TodoListResponse(
            todos=paginated_todos,
            total=total,
            page=page,
            page_size=page_size
        )

    except Exception as e:
        logger.error(f"Get todos error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/todos/{todo_id}", response_model=TodoResponse)
async def get_todo(todo_id: UUID):
    """Get a specific todo"""
    try:
        todo_key = str(todo_id)
        if todo_key not in todos_storage:
            raise HTTPException(status_code=404, detail="Todo not found")

        todo = todos_storage[todo_key]

        # Get children and dependencies
        children = [t for t in todos_storage.values() if t.parent_todo_id == todo_id]
        dependencies = [
            todos_storage[str(dep_id)]
            for dep_id in todo.dependencies
            if str(dep_id) in todos_storage
        ]

        return TodoResponse(
            todo=todo,
            children=children,
            dependencies=dependencies
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get todo error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/todos", response_model=TodoResponse)
async def create_todo(todo_create: TodoCreate):
    """Create a new todo"""
    try:
        # Create todo item
        todo = TodoItem(
            **todo_create.model_dump(),
            id=uuid4()
        )

        # Store todo
        todos_storage[str(todo.id)] = todo

        return TodoResponse(todo=todo)

    except Exception as e:
        logger.error(f"Create todo error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/todos/{todo_id}", response_model=TodoResponse)
async def update_todo(todo_id: UUID, todo_update: TodoUpdate):
    """Update a todo"""
    try:
        todo_key = str(todo_id)
        if todo_key not in todos_storage:
            raise HTTPException(status_code=404, detail="Todo not found")

        todo = todos_storage[todo_key]

        # Update fields
        update_data = todo_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(todo, field, value)

        # Update timestamps
        from datetime import datetime
        todo.updated_at = datetime.now()

        if todo_update.status == TodoStatus.IN_PROGRESS and not todo.started_at:
            todo.started_at = datetime.now()
        elif todo_update.status == TodoStatus.COMPLETED and not todo.completed_at:
            todo.completed_at = datetime.now()

        todos_storage[todo_key] = todo

        return TodoResponse(todo=todo)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update todo error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/todos/{todo_id}", response_model=SuccessResponse)
async def delete_todo(todo_id: UUID):
    """Delete a todo"""
    try:
        todo_key = str(todo_id)
        if todo_key not in todos_storage:
            raise HTTPException(status_code=404, detail="Todo not found")

        del todos_storage[todo_key]

        return SuccessResponse(message="Todo deleted successfully")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete todo error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/todos/{todo_id}/natural-edit", response_model=TodoResponse)
async def edit_todo_natural(todo_id: UUID, command: str):
    """Edit todo using natural language"""
    try:
        todo_key = str(todo_id)
        if todo_key not in todos_storage:
            raise HTTPException(status_code=404, detail="Todo not found")

        todo = todos_storage[todo_key]

        # Parse natural language command (simplified mock)
        command_lower = command.lower()

        if "우선순위" in command_lower or "priority" in command_lower:
            if "높" in command_lower or "high" in command_lower:
                todo.priority = TodoPriority.HIGH
            elif "낮" in command_lower or "low" in command_lower:
                todo.priority = TodoPriority.LOW
            else:
                todo.priority = TodoPriority.MEDIUM

        if "완료" in command_lower or "complete" in command_lower:
            todo.status = TodoStatus.COMPLETED
            from datetime import datetime
            todo.completed_at = datetime.now()

        if "취소" in command_lower or "cancel" in command_lower:
            todo.status = TodoStatus.CANCELLED

        # Update timestamp
        from datetime import datetime
        todo.updated_at = datetime.now()

        todos_storage[todo_key] = todo

        return TodoResponse(todo=todo)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Natural edit error: {e}")
        raise HTTPException(status_code=500, detail=str(e))