"""Todo Manager - Todo 생성, 검증, 의존성 관리, 실패 복구"""

# Dependency Management
from .todo_manager import TodoDependencyManager, todo_dependency_manager

# Validation
from .todo_validator import TodoValidator

# Creation
from .todo_creator import (
    create_todo,
    create_ml_todo,
    create_biz_todo,
    create_todo_legacy
)

# Update (reducer moved to states.reducers to avoid circular import)
from backend.app.dream_agent.states.reducers import todo_reducer
from .todo_updater import update_todo_status

# Queries
from .todo_queries import (
    get_pending_todos,
    get_in_progress_todos,
    get_completed_todos,
    get_failed_todos
)

# Failure Recovery
from .todo_failure_recovery import (
    TodoFailureRecovery,
    todo_failure_recovery
)

# Storage
from .todo_store import TodoStore, todo_store

__all__ = [
    # Dependency Management
    "TodoDependencyManager",
    "todo_dependency_manager",
    # Validation
    "TodoValidator",
    # Creation
    "create_todo",
    "create_ml_todo",
    "create_biz_todo",
    "create_todo_legacy",
    # Update & Reducer
    "todo_reducer",
    "update_todo_status",
    # Queries
    "get_pending_todos",
    "get_in_progress_todos",
    "get_completed_todos",
    "get_failed_todos",
    # Failure Recovery
    "TodoFailureRecovery",
    "todo_failure_recovery",
    # Storage
    "TodoStore",
    "todo_store",
]
