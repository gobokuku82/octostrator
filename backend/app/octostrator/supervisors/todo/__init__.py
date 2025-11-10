"""
TODO Layer Module

Layer 2 of the 3-Layer Architecture
Manages TODO list creation, HITL interactions, and dependency resolution.

This is a core system component, not a domain agent.

Author: Specialist Agent Development Team
Date: 2025-11-05
Version: 1.0
"""

from .todo_manager import TodoAgent
from ...states.todo_state import (
    TodoAgentState,
    TodoItem,
    TodoBatch,
    TodoFilter
)

__all__ = [
    "TodoAgent",
    "TodoAgentState",
    "TodoItem",
    "TodoBatch",
    "TodoFilter",
]